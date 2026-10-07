using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Nodes;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Media;

namespace Launcher.Core.Scraping;

/// <summary>
/// SteamGridDB API v2 (https://www.steamgriddb.com/api/v2): community art only, no metadata. Its grids are Steam and
/// GOG Galaxy library capsules rather than box scans; the portrait sizes are the cover (660×930 and 342×482 first,
/// the ratio of a DVD case, then 600×900), heroes are wide banners, and logos are transparent. Games are found by
/// a name search, since it has no console, hash or serial lookup. Its rate limits aren't documented, so it's paced
/// gently: 2 requests in flight, 4 a second.
/// </summary>
public sealed class SteamGridDbScraper : IScraper
{
    public const string BaseUrl = "https://www.steamgriddb.com/api/v2/";

    private static readonly string[] CoverDimensions = ["660x930", "342x482", "600x900"];

    private readonly ScraperHttp _http;
    private readonly ProviderAccounts _accounts;
    private readonly string _accountsFile;
    private readonly ProviderGate _gate;
    private readonly ProviderGate _cdn;

    public SteamGridDbScraper(ScraperHttp http, ProviderAccounts accounts, ILog log, string accountsFile)
    {
        _ = log;
        _http = http;
        _accounts = accounts;
        _accountsFile = accountsFile;
        _gate = new ProviderGate(Id, 2, 4, null, http.Clock, http.Delay);
        _cdn = new ProviderGate(Id + " images", 4, null, null, http.Clock, http.Delay);
    }

    public string Id => ScraperIds.SteamGridDb;

    public string DisplayName => "SteamGridDB";

    public ScraperCapabilities Capabilities => Supplies;

    /// <summary>What this provider can supply (its capability map).</summary>
    public static ScraperCapabilities Supplies { get; } = new(
        new HashSet<MetadataField>(),
        new HashSet<string>([MediaKinds.Cover, MediaKinds.Hero, MediaKinds.Logo], StringComparer.Ordinal));

    public int MaxConcurrency => _gate.MaxConcurrency;

    public string? Unavailable => _accounts.SteamGridDbApiKey is null
        ? $"SteamGridDB has no API key: set api_key under [steamgriddb] in {_accountsFile}, or ODYSSEY_STEAMGRIDDB_API_KEY " +
          "(generate one at https://www.steamgriddb.com/profile/preferences)"
        : null;

    public string? Unsupported(SystemConfig system) => null;

    public Task PrepareAsync(CancellationToken cancellationToken) => Task.CompletedTask;

    public async Task<ProviderResult> LookupAsync(ScrapeQuery query, CancellationToken cancellationToken)
    {
        var term = TitleMatcher.SearchTerm(query.Title);
        var candidates = await SearchAsync(term, query.System, cancellationToken).ConfigureAwait(false);
        var best = candidates
            .Select((c, index) => (Candidate: c, Score: TitleMatcher.Similarity(term, c.Name), Index: index))
            .Where(c => c.Score >= TitleMatcher.Threshold)
            .OrderByDescending(c => c.Score)
            .ThenBy(c => c.Index)
            .FirstOrDefault();
        if (best.Candidate is null)
        {
            return ProviderResult.NotFound;
        }

        var fetched = await FetchAsync(best.Candidate.ProviderGameId, query, cancellationToken).ConfigureAwait(false);
        return fetched with { Method = MatchMethods.Search };
    }

    public async Task<ProviderResult> FetchAsync(string providerGameId, ScrapeQuery query, CancellationToken cancellationToken)
    {
        // One saved response holds each art list asked for, so a rebuild can read it back.
        var saved = new JsonObject { ["id"] = providerGameId };
        var game = Uri.EscapeDataString(providerGameId);
        (string Kind, string Path)[] lists =
        [
            (MediaKinds.Cover, $"grids/game/{game}?dimensions={string.Join(',', CoverDimensions)}&types=static&nsfw=false&humor=false"),
            (MediaKinds.Hero, $"heroes/game/{game}?types=static&nsfw=false&humor=false"),
            (MediaKinds.Logo, $"logos/game/{game}?types=static&nsfw=false&humor=false"),
        ];
        foreach (var (kind, path) in lists)
        {
            if (!query.WantedMedia.Contains(kind))
            {
                continue;
            }

            var (reply, replyKind) = await _http.SendAsync(Id, _gate, () => Get(path), Classify, kind + " list", cancellationToken).ConfigureAwait(false);
            if (replyKind == ReplyKind.NotFound)
            {
                // The game is gone (or never existed): a stale match.
                return ProviderResult.NotFound;
            }

            using var document = LenientJson.Parse(reply.Text);
            if (document?.RootElement.TryGetProperty("data", out var data) == true && data.ValueKind == JsonValueKind.Array)
            {
                saved[kind] = LenientJson.ToNode(data);
            }
        }

        var response = saved.ToJsonString();
        return new ProviderResult(Parse(response), null, response);
    }

    public async Task<string> TestConnectionAsync(CancellationToken cancellationToken)
    {
        if (Unavailable is { } missing)
        {
            throw new ProviderException(Id, ProviderFailure.AuthFailed, missing);
        }

        var (_, kind) = await _http.SendAsync(Id, _gate, () => Get("search/autocomplete/sonic"), Classify, "connection test", cancellationToken).ConfigureAwait(false);
        return kind == ReplyKind.Ok
            ? "SteamGridDB accepted the API key."
            : throw new ProviderException(Id, ProviderFailure.Rejected, "SteamGridDB didn't answer the test search as expected");
    }

    /// <summary>SteamGridDB has no ROM index.</summary>
    public Task<ScrapeCandidate?> IdentifyFileAsync(ScrapeQuery query, CancellationToken cancellationToken) => Task.FromResult<ScrapeCandidate?>(null);

    public async Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(string title, SystemConfig system, CancellationToken cancellationToken)
    {
        var candidates = new List<ScrapeCandidate>();
        if (title.Length == 0)
        {
            return candidates;
        }

        var path = "search/autocomplete/" + Uri.EscapeDataString(title);
        var (reply, kind) = await _http.SendAsync(Id, _gate, () => Get(path), Classify, "search", cancellationToken).ConfigureAwait(false);
        if (kind != ReplyKind.Ok)
        {
            return candidates;
        }

        using var document = LenientJson.Parse(reply.Text);
        if (document?.RootElement.TryGetProperty("data", out var data) != true || data.ValueKind != JsonValueKind.Array)
        {
            return candidates;
        }

        foreach (var game in data.EnumerateArray())
        {
            if (game.Str("id") is { } id && game.Str("name") is { } name)
            {
                string? year = game.Num("release_date") is { } seconds
                    ? DateTimeOffset.FromUnixTimeSeconds((long)seconds).Year.ToString(System.Globalization.CultureInfo.InvariantCulture)
                    : null;
                candidates.Add(new ScrapeCandidate(id, name, year));
            }
        }

        return candidates;
    }

    /// <summary>
    /// Its search has no art, so this asks for the game's grids (one request) and takes the cover a scrape would
    /// (<see cref="CoverDimensions"/>), at the size SteamGridDB shows in its own lists (<c>thumb</c>). Null when it has none.
    /// </summary>
    public async Task<ScrapedMedia?> SearchCoverAsync(ScrapeCandidate candidate, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(candidate);
        var path = $"grids/game/{Uri.EscapeDataString(candidate.ProviderGameId)}?dimensions={string.Join(',', CoverDimensions)}&types=static&nsfw=false&humor=false";
        var (reply, kind) = await _http.SendAsync(Id, _gate, () => Get(path), Classify, "cover list", cancellationToken).ConfigureAwait(false);
        if (kind != ReplyKind.Ok)
        {
            return null;
        }

        using var document = LenientJson.Parse(reply.Text);
        if (document?.RootElement.TryGetProperty("data", out var data) != true || data.ValueKind != JsonValueKind.Array)
        {
            return null;
        }

        var grids = data.EnumerateArray().ToList();
        var cover = CoverDimensions
            .Select(d => grids.FirstOrDefault(g => $"{g.Str("width")}x{g.Str("height")}" == d))
            .FirstOrDefault(g => g.ValueKind == JsonValueKind.Object);
        return cover.ValueKind == JsonValueKind.Object && (cover.Str("thumb") ?? cover.Str("url")) is { } url
            ? new ScrapedMedia(MediaKinds.Cover, url)
            : null;
    }

    public async Task<byte[]> DownloadAsync(ScrapedMedia media, CancellationToken cancellationToken)
    {
        if (!Uri.TryCreate(media.Url, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps
            || !(uri.Host == "steamgriddb.com" || uri.Host.EndsWith(".steamgriddb.com", StringComparison.OrdinalIgnoreCase)))
        {
            throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the image URL isn't on steamgriddb.com");
        }

        var (reply, kind) = await _http.SendAsync(Id, _cdn, () => new HttpRequestMessage(HttpMethod.Get, uri),
            r => ScraperHttp.ClassifyCommon(r, "SteamGridDB's image server refused the download"), media.Kind + " download", cancellationToken).ConfigureAwait(false);
        return kind == ReplyKind.NotFound
            ? throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the image is gone")
            : reply.Body;
    }

    /// <summary>Reads a saved response (<see cref="FetchAsync"/>'s): the first item of each art list. Offline and pure.</summary>
    public static ScrapedGame? Parse(string response)
    {
        ArgumentNullException.ThrowIfNull(response);
        using var document = LenientJson.Parse(response);
        if (document is null || document.RootElement.Str("id") is not { } id)
        {
            return null;
        }

        var root = document.RootElement;
        var media = new List<ScrapedMedia>();
        var covers = root.Arr(MediaKinds.Cover).ToList();
        var cover = CoverDimensions
            .Select(d => covers.FirstOrDefault(g => $"{g.Str("width")}x{g.Str("height")}" == d))
            .FirstOrDefault(g => g.ValueKind == JsonValueKind.Object);
        if (cover.ValueKind == JsonValueKind.Object && cover.Str("url") is { } coverUrl)
        {
            media.Add(new ScrapedMedia(MediaKinds.Cover, coverUrl));
        }
        else if (covers.FirstOrDefault().Str("url") is { } anyCover)
        {
            media.Add(new ScrapedMedia(MediaKinds.Cover, anyCover));
        }

        foreach (var kind in (ReadOnlySpan<string>)[MediaKinds.Hero, MediaKinds.Logo])
        {
            if (root.Arr(kind).FirstOrDefault().Str("url") is { } url)
            {
                media.Add(new ScrapedMedia(kind, url));
            }
        }

        return new ScrapedGame(id, Media: media);
    }

    private HttpRequestMessage Get(string path)
    {
        var request = new HttpRequestMessage(HttpMethod.Get, BaseUrl + path);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accounts.SteamGridDbApiKey);
        return request;
    }

    private static Classification Classify(HttpReply reply) =>
        ScraperHttp.ClassifyCommon(reply, "SteamGridDB refused the API key in secrets.toml");
}
