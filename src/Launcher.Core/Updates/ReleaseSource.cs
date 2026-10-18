using System.Globalization;
using System.Net;
using System.Net.Http.Headers;

namespace Launcher.Core.Updates;

/// <summary>Where releases are listed and downloaded from: GitHub, or a local folder for tests and captures.</summary>
public interface IReleaseSource
{
    /// <summary>For the user: "GitHub", or the folder.</summary>
    string Name { get; }

    /// <summary>Resolves relative download URLs in the list (a local feed's file names); null for GitHub's absolute ones.</summary>
    Uri? BaseUri { get; }

    /// <summary>The releases list, as JSON. Throws <see cref="UpdateException"/> with a reason for the user.</summary>
    Task<string> ReadReleasesAsync(CancellationToken token);

    /// <summary>Opens a release's file for reading, with its length when known. Throws <see cref="UpdateException"/>.</summary>
    Task<(Stream Stream, long? Length)> OpenAsync(Uri url, CancellationToken token);
}

/// <summary>A failure written for the user.</summary>
public sealed class UpdateException(string message, Exception? inner = null) : Exception(message, inner);

/// <summary>
/// The launcher's GitHub releases (<c>GeekRhapsody/OdysseyLauncher</c>), through GitHub's REST API without credentials:
/// 60 requests an hour per address, and a check is one.
/// </summary>
public sealed class GitHubReleaseSource(HttpClient client, string repository = GitHubReleaseSource.Repository) : IReleaseSource
{
    public const string Repository = "GeekRhapsody/OdysseyLauncher";

    /// <summary>How long a request may wait for an answer, and a download for its next bytes.</summary>
    public static readonly TimeSpan Timeout = TimeSpan.FromSeconds(30);

    public string Name => "GitHub";

    public Uri? BaseUri => null;

    public async Task<string> ReadReleasesAsync(CancellationToken token)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, new Uri($"https://api.github.com/repos/{repository}/releases?per_page=30"));
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/vnd.github+json"));
        request.Headers.Add("X-GitHub-Api-Version", "2022-11-28");
        using var response = await SendAsync(request, token).ConfigureAwait(false);
        return await response.Content.ReadAsStringAsync(token).ConfigureAwait(false);
    }

    public async Task<(Stream Stream, long? Length)> OpenAsync(Uri url, CancellationToken token)
    {
        ArgumentNullException.ThrowIfNull(url);
        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        var response = await SendAsync(request, token).ConfigureAwait(false);
        try
        {
            var stream = await response.Content.ReadAsStreamAsync(token).ConfigureAwait(false);
            return (new OwningStream(stream, response), response.Content.Headers.ContentLength);
        }
        catch
        {
            response.Dispose();
            throw;
        }
    }

    /// <summary>Sends, waiting <see cref="Timeout"/> at most for the headers, and throws <see cref="UpdateException"/> for a failure.</summary>
    private async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(token);
        timeout.CancelAfter(Timeout);
        HttpResponseMessage response;
        try
        {
            response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested)
        {
            throw new UpdateException($"GitHub didn't answer within {Timeout.TotalSeconds:0} seconds. Check the network, then try again.");
        }
        catch (HttpRequestException e)
        {
            throw new UpdateException($"GitHub couldn't be reached ({e.Message}). Check the network, then try again.", e);
        }

        if (response.IsSuccessStatusCode)
        {
            return response;
        }

        using (response)
        {
            throw new UpdateException(Refusal(response));
        }
    }

    private static string Refusal(HttpResponseMessage response)
    {
        if (response.StatusCode is HttpStatusCode.Forbidden or HttpStatusCode.TooManyRequests
            && response.Headers.TryGetValues("X-RateLimit-Remaining", out var remaining) && remaining.FirstOrDefault() == "0")
        {
            var reset = response.Headers.TryGetValues("X-RateLimit-Reset", out var resets)
                && long.TryParse(resets.FirstOrDefault(), NumberStyles.None, CultureInfo.InvariantCulture, out var seconds)
                    ? $" after {DateTimeOffset.FromUnixTimeSeconds(seconds).ToLocalTime():HH:mm}"
                    : " in an hour";
            return $"GitHub allows 60 checks an hour from one network, and they're used up. Try again{reset}.";
        }

        return response.StatusCode == HttpStatusCode.NotFound
            ? "GitHub has no releases of Odyssey Launcher to offer."
            : $"GitHub answered {(int)response.StatusCode} ({response.ReasonPhrase}). Try again later.";
    }

    /// <summary>A response's body that disposes the response with it.</summary>
    private sealed class OwningStream(Stream inner, IDisposable owner) : Stream
    {
        public override bool CanRead => true;

        public override bool CanSeek => false;

        public override bool CanWrite => false;

        public override long Length => throw new NotSupportedException();

        public override long Position
        {
            get => throw new NotSupportedException();
            set => throw new NotSupportedException();
        }

        public override int Read(byte[] buffer, int offset, int count) => inner.Read(buffer, offset, count);

        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default) =>
            inner.ReadAsync(buffer, cancellationToken);

        public override Task<int> ReadAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken) =>
            inner.ReadAsync(buffer, offset, count, cancellationToken);

        public override void Flush()
        {
        }

        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();

        public override void SetLength(long value) => throw new NotSupportedException();

        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                inner.Dispose();
                owner.Dispose();
            }

            base.Dispose(disposing);
        }
    }
}

/// <summary>
/// <c>--update-feed=&lt;folder&gt;</c>: a folder holding <c>releases.json</c> (GitHub's shape) and the files it names by
/// relative URL, read instead of GitHub, for testing an update end to end without publishing one.
/// </summary>
public sealed class LocalReleaseSource(string folder) : IReleaseSource
{
    public const string ListFileName = "releases.json";

    public string Name => folder;

    public Uri? BaseUri { get; } = new(Path.TrimEndingDirectorySeparator(Path.GetFullPath(folder)) + Path.DirectorySeparatorChar);

    public async Task<string> ReadReleasesAsync(CancellationToken token)
    {
        try
        {
            return await File.ReadAllTextAsync(Path.Combine(folder, ListFileName), token).ConfigureAwait(false);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            throw new UpdateException($"{Path.Combine(folder, ListFileName)} couldn't be read: {e.Message}", e);
        }
    }

    public Task<(Stream Stream, long? Length)> OpenAsync(Uri url, CancellationToken token)
    {
        ArgumentNullException.ThrowIfNull(url);
        if (!url.IsFile)
        {
            throw new UpdateException($"A local feed's files are in its folder, not at {url}.");
        }

        try
        {
            var stream = new FileStream(url.LocalPath, FileMode.Open, FileAccess.Read, FileShare.Read, 1, useAsync: true);
            return Task.FromResult<(Stream, long?)>((stream, stream.Length));
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            throw new UpdateException($"{url.LocalPath} couldn't be read: {e.Message}", e);
        }
    }
}
