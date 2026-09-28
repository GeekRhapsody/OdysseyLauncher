using System.Collections.Concurrent;
using System.Net;
using System.Text;
using System.Web;

namespace Launcher.Core.Tests.TestSupport;

/// <summary>A request the fake handler saw.</summary>
public sealed record RecordedRequest(string Method, Uri Uri, string? Body, string? Authorization, string? ClientId)
{
    public string? Query(string name) => HttpUtility.ParseQueryString(Uri.Query)[name];
}

/// <summary>
/// An <see cref="HttpMessageHandler"/> that answers from routes the test registers, and records every request. No test
/// touches the network: a request no route matches fails the test (<see cref="Unmatched"/>), and <see cref="Offline"/>
/// makes every request throw, as a disconnected machine would.
/// </summary>
public sealed class FakeHttpHandler : HttpMessageHandler
{
    private readonly List<(string Method, Func<Uri, bool> Match, Func<RecordedRequest, CancellationToken, Task<HttpResponseMessage>> Respond)> _routes = [];
    private readonly object _lock = new();

    public ConcurrentQueue<RecordedRequest> Requests { get; } = new();

    public ConcurrentQueue<string> Unmatched { get; } = new();

    /// <summary>Every request throws <see cref="HttpRequestException"/>.</summary>
    public bool Offline { get; set; }

    /// <summary>Later routes win, so a test can override a default.</summary>
    public FakeHttpHandler On(string method, Func<Uri, bool> match, Func<RecordedRequest, HttpResponseMessage> respond) =>
        OnAsync(method, match, (r, _) => Task.FromResult(respond(r)));

    /// <param name="respond">Gets the request's cancellation token, so a route that waits can be abandoned.</param>
    public FakeHttpHandler OnAsync(string method, Func<Uri, bool> match, Func<RecordedRequest, CancellationToken, Task<HttpResponseMessage>> respond)
    {
        lock (_lock)
        {
            _routes.Insert(0, (method, match, respond));
        }

        return this;
    }

    /// <summary>Requests whose URL contains <paramref name="fragment"/>.</summary>
    public int Count(string fragment) => Requests.Count(r => r.Uri.AbsoluteUri.Contains(fragment, StringComparison.Ordinal));

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var body = request.Content is null ? null : await request.Content.ReadAsStringAsync(cancellationToken);
        var recorded = new RecordedRequest(
            request.Method.Method,
            request.RequestUri!,
            body,
            request.Headers.Authorization?.ToString(),
            request.Headers.TryGetValues("Client-ID", out var ids) ? ids.FirstOrDefault() : null);
        Requests.Enqueue(recorded);
        if (Offline)
        {
            throw new HttpRequestException("offline (test)");
        }

        (string Method, Func<Uri, bool> Match, Func<RecordedRequest, CancellationToken, Task<HttpResponseMessage>> Respond)[] routes;
        lock (_lock)
        {
            routes = [.. _routes];
        }

        foreach (var (method, match, respond) in routes)
        {
            if (method == request.Method.Method && match(request.RequestUri!))
            {
                return await respond(recorded, cancellationToken);
            }
        }

        Unmatched.Enqueue($"{request.Method} {request.RequestUri}");
        return new HttpResponseMessage(HttpStatusCode.NotImplemented) { Content = new StringContent("no route in the test") };
    }

    public static HttpResponseMessage Json(string json, HttpStatusCode status = HttpStatusCode.OK, TimeSpan? retryAfter = null)
    {
        var response = new HttpResponseMessage(status) { Content = new StringContent(json, Encoding.UTF8, "application/json") };
        if (retryAfter is { } after)
        {
            response.Headers.RetryAfter = new System.Net.Http.Headers.RetryConditionHeaderValue(after);
        }

        return response;
    }

    public static HttpResponseMessage Text(string text, HttpStatusCode status) =>
        new(status) { Content = new StringContent(text, Encoding.UTF8, "text/plain") };

    public static HttpResponseMessage Bytes(byte[] bytes, string mediaType = "image/png")
    {
        var content = new ByteArrayContent(bytes);
        content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(mediaType);
        return new HttpResponseMessage(HttpStatusCode.OK) { Content = content };
    }
}
