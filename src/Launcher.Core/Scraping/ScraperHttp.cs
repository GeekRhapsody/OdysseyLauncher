using System.Globalization;
using System.Net;
using Launcher.Core.Diagnostics;

namespace Launcher.Core.Scraping;

/// <summary>What a provider makes of a response.</summary>
public enum ReplyKind
{
    Ok,
    NotFound,

    /// <summary>Too many requests: retried after a pause that holds every request to the provider.</summary>
    RateLimited,

    /// <summary>A server or network problem: retried with backoff.</summary>
    Transient,

    Rejected,
    QuotaExhausted,
    Closed,
    AuthFailed,

    /// <summary>The access token was refused (IGDB): the caller gets a new one and tries once more.</summary>
    TokenExpired,
}

/// <param name="Message">For the user and the log; never contains credentials.</param>
/// <param name="Until">For <see cref="ReplyKind.QuotaExhausted"/> and <see cref="ReplyKind.Closed"/>: when to try again.</param>
public sealed record Classification(ReplyKind Kind, string? Message = null, DateTimeOffset? Until = null)
{
    public static Classification Ok { get; } = new(ReplyKind.Ok);

    public static Classification NotFound { get; } = new(ReplyKind.NotFound);
}

/// <summary>A response, read in full.</summary>
public sealed record HttpReply(int Status, byte[] Body, TimeSpan? RetryAfter, string? MediaType)
{
    public string Text => System.Text.Encoding.UTF8.GetString(Body);
}

/// <param name="MaxAttempts">Tries per request, the first included.</param>
/// <param name="BaseDelay">The first backoff; each retry doubles it, plus up to 25% jitter.</param>
public sealed record RetryPolicy(int MaxAttempts, TimeSpan BaseDelay, TimeSpan MaxDelay)
{
    public static RetryPolicy Default { get; } = new(5, TimeSpan.FromSeconds(2), TimeSpan.FromMinutes(2));
}

/// <summary>
/// Sends provider requests through their <see cref="ProviderGate"/>, and retries rate limits and transient failures
/// with exponential backoff (honouring Retry-After). Quota, closure, credential and malformed-request failures
/// aren't retried: they become a <see cref="ProviderException"/> the queue acts on.
/// </summary>
public sealed class ScraperHttp(HttpClient client, TimeProvider clock, Delay delay, RetryPolicy policy, ILog log)
{
    public HttpClient Client { get; } = client;

    public TimeProvider Clock { get; } = clock;

    public Delay Delay { get; } = delay;

    /// <summary>How long one attempt may take, from leaving the gate to the whole body read, unless the caller says otherwise.</summary>
    public static readonly TimeSpan DefaultTimeout = TimeSpan.FromSeconds(30);

    /// <param name="request">Makes a fresh request for each attempt.</param>
    /// <param name="what">Names the request in messages ("lookup", "cover download").</param>
    /// <param name="timeout">How long one attempt may take (default <see cref="DefaultTimeout"/>): longer for a video.</param>
    public async Task<(HttpReply Reply, ReplyKind Kind)> SendAsync(
        string provider,
        ProviderGate gate,
        Func<HttpRequestMessage> request,
        Func<HttpReply, Classification> classify,
        string what,
        CancellationToken cancellationToken,
        TimeSpan? timeout = null)
    {
        for (var attempt = 1; ; attempt++)
        {
            HttpReply? reply = null;
            Classification verdict;
            var wait = TimeSpan.Zero;
            ProviderException? closing = null;
            try
            {
                using (await gate.EnterAsync(cancellationToken).ConfigureAwait(false))
                {
                    // Timed from here, so waiting for the gate doesn't count. Real time, as HttpClient.Timeout was.
                    using var attemptTimeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
                    attemptTimeout.CancelAfter(timeout ?? DefaultTimeout);
                    using var message = request();
                    using var response = await Client.SendAsync(message, HttpCompletionOption.ResponseContentRead, attemptTimeout.Token).ConfigureAwait(false);
                    var body = await response.Content.ReadAsByteArrayAsync(attemptTimeout.Token).ConfigureAwait(false);
                    reply = new HttpReply((int)response.StatusCode, body, RetryAfter(response), response.Content.Headers.ContentType?.MediaType);

                    // Decided while this request still holds its slot, so a pause or closure reaches every request
                    // queued behind it before any of them goes out.
                    verdict = classify(reply);
                    (wait, closing) = Consequences(provider, gate, verdict, reply, attempt);
                }
            }
            catch (HttpRequestException e)
            {
                verdict = new Classification(ReplyKind.Transient, "network error: " + e.Message);
                wait = Backoff(attempt);
            }
            catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
            {
                verdict = new Classification(ReplyKind.Transient, "the request timed out");
                wait = Backoff(attempt);
            }

            if (closing is not null)
            {
                throw closing;
            }

            switch (verdict.Kind)
            {
                case ReplyKind.Ok or ReplyKind.NotFound or ReplyKind.TokenExpired:
                    return (reply!, verdict.Kind);
                case ReplyKind.RateLimited or ReplyKind.Transient:
                    var reason = verdict.Message ?? (reply is null ? "failed" : $"HTTP {reply.Status}");
                    if (attempt >= policy.MaxAttempts)
                    {
                        throw new ProviderException(provider, ProviderFailure.Transient,
                            $"{what}: {reason} (gave up after {attempt} attempts)");
                    }

                    log.Write(LogLevel.Warning, string.Create(CultureInfo.InvariantCulture,
                        $"{provider}: {what}: {reason}; retrying in {wait.TotalSeconds:0.#} s (attempt {attempt + 1} of {policy.MaxAttempts})"));
                    await Delay(wait, cancellationToken).ConfigureAwait(false);
                    break;
                default:
                    throw new ProviderException(provider, ProviderFailure.Rejected, $"{what}: {verdict.Message ?? $"HTTP {reply?.Status}"}");
            }
        }
    }

    /// <summary>
    /// What a verdict means for everyone using the provider: a rate limit pauses the gate for the wait; a used-up
    /// quota, closure or refused credentials shut it, so queued requests fail without going out.
    /// </summary>
    private (TimeSpan Wait, ProviderException? Closing) Consequences(string provider, ProviderGate gate, Classification verdict, HttpReply reply, int attempt)
    {
        switch (verdict.Kind)
        {
            case ReplyKind.RateLimited or ReplyKind.Transient:
                var wait = reply.RetryAfter is { } after && after > TimeSpan.Zero ? Min(after, policy.MaxDelay) : Backoff(attempt);
                if (verdict.Kind == ReplyKind.RateLimited)
                {
                    gate.PauseUntil(Clock.GetUtcNow() + wait);
                }

                return (wait, null);
            case ReplyKind.QuotaExhausted or ReplyKind.Closed or ReplyKind.AuthFailed:
                var failure = new ProviderException(
                    provider,
                    verdict.Kind switch
                    {
                        ReplyKind.QuotaExhausted => ProviderFailure.QuotaExhausted,
                        ReplyKind.Closed => ProviderFailure.Closed,
                        _ => ProviderFailure.AuthFailed,
                    },
                    verdict.Message ?? "refused",
                    verdict.Kind == ReplyKind.AuthFailed ? null : verdict.Until);
                gate.Close(failure);
                return (TimeSpan.Zero, failure);
            default:
                return (TimeSpan.Zero, null);
        }
    }

    /// <summary>The standard mapping most providers share: 404 not found, 429 rate limited, 5xx and 408 transient, 401/403 refused.</summary>
    public static Classification ClassifyCommon(HttpReply reply, string authMessage) => reply.Status switch
    {
        >= 200 and < 300 => Classification.Ok,
        404 => Classification.NotFound,
        429 => new Classification(ReplyKind.RateLimited, "rate limited (HTTP 429)"),
        408 or >= 500 => new Classification(ReplyKind.Transient, $"server error (HTTP {reply.Status})"),
        401 or 403 => new Classification(ReplyKind.AuthFailed, authMessage),
        _ => new Classification(ReplyKind.Rejected, $"refused (HTTP {reply.Status})"),
    };

    private TimeSpan Backoff(int attempt)
    {
        var baseMs = policy.BaseDelay.TotalMilliseconds * Math.Pow(2, attempt - 1);
        var jitter = baseMs * 0.25 * Random.Shared.NextDouble();
        return Min(TimeSpan.FromMilliseconds(baseMs + jitter), policy.MaxDelay);
    }

    private static TimeSpan Min(TimeSpan a, TimeSpan b) => a < b ? a : b;

    private TimeSpan? RetryAfter(HttpResponseMessage response)
    {
        if (response.Headers.RetryAfter is not { } header)
        {
            return null;
        }

        if (header.Delta is { } delta)
        {
            return delta;
        }

        return header.Date is { } date ? date - Clock.GetUtcNow() : null;
    }

    /// <summary>The default <see cref="Scraping.Delay"/>, on <paramref name="clock"/>.</summary>
    public static Delay RealDelay(TimeProvider clock) => (duration, token) => Task.Delay(duration, clock, token);

    /// <summary>
    /// An HttpClient for the providers: our user agent, gzip and Brotli. No timeout of its own: <see cref="SendAsync"/>
    /// times each attempt (30 s, or longer for a video).
    /// </summary>
    public static HttpClient CreateClient(HttpMessageHandler? handler = null)
    {
        var client = handler is null
            ? new HttpClient(new SocketsHttpHandler { AutomaticDecompression = DecompressionMethods.All, PooledConnectionLifetime = TimeSpan.FromMinutes(5) })
            : new HttpClient(handler, disposeHandler: false);
        client.Timeout = Timeout.InfiniteTimeSpan;
        client.DefaultRequestHeaders.UserAgent.ParseAdd("OdysseyLauncher/" + CoreInfo.Version.Split('+')[0]);
        return client;
    }
}
