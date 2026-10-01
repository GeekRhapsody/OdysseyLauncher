using System.Globalization;
using System.Net;
using System.Text.Json;
using System.Text.Json.Nodes;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Media;

namespace Launcher.Core.Scraping;

/// <summary>
/// The Steam store's own Web API (no key): Steam's official library art (the 600×900 capsule as the cover, the library
/// hero, the logo, a screenshot) and its store metadata. Games are found by a title search
/// (<c>IStoreQueryService/SearchSuggestions</c>, which returns each hit's store item, assets and all, in one request),
/// never by the app id in a shortcut; a stored match is fetched by its app id (<c>IStoreBrowseService/GetItems</c>),
/// which still answers for a game since taken off the store. Only systems with <c>steam_store = true</c> are looked
/// up, so a console ROM can't match a PC re-release. The API has no logo, so <c>logo.png</c> is checked with a HEAD
/// request. Its limits aren't documented, so it's paced gently: 2 requests in flight, 1 a second.
/// </summary>
public sealed class SteamStoreScraper : IScraper
{
    public const string BaseUrl = "https://api.steampowered.com/";

    /// <summary>Where the store's images are served (the Cloudflare host redirects).</summary>
    public const string ImageHost = "shared.akamai.steamstatic.com";

    public const string ImageBaseUrl = "https://" + ImageHost + "/store_item_assets/";

    /// <summary>The country the store is asked as: it decides which games a search can see.</summary>
    public const string Country = "US";

    /// <summary>Our language codes to Steam's language names.</summary>
    private static readonly Dictionary<string, string> SteamLanguages = new(StringComparer.Ordinal)
    {
        ["en"] = "english", ["fr"] = "french", ["de"] = "german", ["es"] = "spanish", ["it"] = "italian",
        ["pt"] = "portuguese", ["ja"] = "japanese", ["ko"] = "koreana", ["zh"] = "schinese", ["ru"] = "russian",
        ["pl"] = "polish", ["nl"] = "dutch",
    };

    private readonly ScraperHttp _http;
    private readonly ILog _log;
    private readonly string _language;
    private readonly ProviderGate _gate;
    private readonly ProviderGate _cdn;

    public SteamStoreScraper(ScraperHttp http, ScrapingSettings settings, ILog log)
    {
        ArgumentNullException.ThrowIfNull(settings);
        _http = http;
        _log = log;
        _language = LanguageFor(settings);
        _gate = new ProviderGate(Id, 2, 1, null, http.Clock, http.Delay);
        _cdn = new ProviderGate(Id + " images", 4, null, null, http.Clock, http.Delay);
    }

    public string Id => ScraperIds.Steam;

    public string DisplayName => "Steam store";

    public ScraperCapabilities Capabilities => Supplies;

    /// <summary>What this provider can supply (its capability map). No genre (tag ids only) and no players.</summary>
    public static ScraperCapabilities Supplies { get; } = new(
        new HashSet<MetadataField>([MetadataField.Title, MetadataField.Description, MetadataField.ReleaseDate,
            MetadataField.Developer, MetadataField.Publisher, MetadataField.Rating]),
        new HashSet<string>([MediaKinds.Cover, MediaKinds.Hero, MediaKinds.Logo, MediaKinds.Screenshot], StringComparer.Ordinal));

    public int MaxConcurrency => _gate.MaxConcurrency;

    /// <summary>Always available: the store's API needs no credentials.</summary>
    public string? Unavailable => null;

    public string? Unsupported(SystemConfig system)
    {
        ArgumentNullException.ThrowIfNull(system);
        return system.SteamStore ? null : $"{system.Name} has no steam_store in systems.toml";
    }

    public Task PrepareAsync(CancellationToken cancellationToken) => Task.CompletedTask;

    /// <summary>Steam's name for the first of <c>[scraping] languages</c> it has; English otherwise.</summary>
    public static string LanguageFor(ScrapingSettings settings)
    {
        ArgumentNullException.ThrowIfNull(settings);
        foreach (var code in settings.Languages)
        {
            if (SteamLanguages.TryGetValue(code, out var language))
            {
                return language;
            }
        }

        return "english";
    }

    public async Task<ProviderResult> LookupAsync(ScrapeQuery query, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(query);
        var term = TitleMatcher.SearchTerm(query.Title);
        if (term.Length == 0)
        {
            return ProviderResult.NotFound;
        }

        var text = await GetAsync("IStoreQueryService/SearchSuggestions", Search(term, withItems: true), "search", cancellationToken).ConfigureAwait(false);
        using var document = text is null ? null : LenientJson.Parse(text);
        if (document is null || Best(term, StoreItems(document.RootElement)) is not { } best)
        {
            return ProviderResult.NotFound;
        }

        var result = await ResultAsync(best, query, cancellationToken).ConfigureAwait(false);
        return result with { Method = MatchMethods.Search };
    }

    public async Task<ProviderResult> FetchAsync(string providerGameId, ScrapeQuery query, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(query);
        if (!uint.TryParse(providerGameId, NumberStyles.None, CultureInfo.InvariantCulture, out var appId) || appId == 0)
        {
            return ProviderResult.NotFound;
        }

        var input = new JsonObject
        {
            ["ids"] = new JsonArray(new JsonObject { ["appid"] = appId }),
            ["context"] = Context(),
            ["data_request"] = DataRequest(),
        };
        var text = await GetAsync("IStoreBrowseService/GetItems", input, "fetch", cancellationToken).ConfigureAwait(false);
        using var document = text is null ? null : LenientJson.Parse(text);
        var item = document is null ? default : StoreItems(document.RootElement).FirstOrDefault(i => i.Str("appid") == providerGameId);
        return item.ValueKind == JsonValueKind.Object
            ? await ResultAsync(item, query, cancellationToken).ConfigureAwait(false)
            : ProviderResult.NotFound;
    }

    public async Task<string> TestConnectionAsync(CancellationToken cancellationToken)
    {
        var text = await GetAsync("IStoreQueryService/SearchSuggestions", Search("Portal 2", withItems: false), "connection test", cancellationToken).ConfigureAwait(false);
        using var document = text is null ? null : LenientJson.Parse(text);
        return document?.RootElement.Obj("response")?.Arr("ids").Any() == true
            ? "The Steam store answered."
            : throw new ProviderException(Id, ProviderFailure.Rejected, "The Steam store didn't answer the test search as expected");
    }

    public async Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(string title, SystemConfig system, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(title);
        var candidates = new List<ScrapeCandidate>();
        if (title.Length == 0)
        {
            return candidates;
        }

        var text = await GetAsync("IStoreQueryService/SearchSuggestions", Search(title, withItems: true), "search", cancellationToken).ConfigureAwait(false);
        using var document = text is null ? null : LenientJson.Parse(text);
        if (document is null)
        {
            return candidates;
        }

        foreach (var item in StoreItems(document.RootElement))
        {
            if (item.Str("appid") is { } id && item.Str("name") is { } name)
            {
                candidates.Add(new ScrapeCandidate(id, name, ReleaseDate(item)?[..4]));
            }
        }

        return candidates;
    }

    public async Task<byte[]> DownloadAsync(ScrapedMedia media, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(media);
        if (!Uri.TryCreate(media.Url, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps || uri.Host != ImageHost)
        {
            throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the image URL isn't on {ImageHost}");
        }

        var (reply, kind) = await _http.SendAsync(Id, _cdn, () => new HttpRequestMessage(HttpMethod.Get, uri), Classify,
            media.Kind + " download", cancellationToken).ConfigureAwait(false);
        return kind == ReplyKind.NotFound
            ? throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the image is gone")
            : reply.Body;
    }

    /// <summary>
    /// Reads a saved response (<c>{"id": app id, "item": the store item, "logo": whether logo.png exists}</c>): the
    /// metadata and the media URLs. Offline and pure.
    /// </summary>
    public static ScrapedGame? Parse(string response)
    {
        ArgumentNullException.ThrowIfNull(response);
        using var document = LenientJson.Parse(response);
        if (document is null || document.RootElement.Str("id") is not { } id || document.RootElement.Obj("item") is not { } item)
        {
            return null;
        }

        var media = new List<ScrapedMedia>();
        var assets = item.Obj("assets");
        if (assets is { } a && a.Str("asset_url_format") is { } format && format.Contains("${FILENAME}", StringComparison.Ordinal))
        {
            foreach (var (kind, names) in (ReadOnlySpan<(string, string[])>)
                [(MediaKinds.Cover, ["library_capsule_2x", "library_capsule"]), (MediaKinds.Hero, ["library_hero_2x", "library_hero"])])
            {
                if (names.Select(n => a.Str(n)).FirstOrDefault(n => n is not null) is { } file)
                {
                    media.Add(new ScrapedMedia(kind, ImageBaseUrl + format.Replace("${FILENAME}", file, StringComparison.Ordinal)));
                }
            }
        }

        if (document.RootElement.Str("logo") == "true")
        {
            media.Add(new ScrapedMedia(MediaKinds.Logo, LogoUrl(id)));
        }

        var screenshot = item.Obj("screenshots")?.Arr("all_ages_screenshots")
            .Where(s => s.Str("filename") is not null)
            .OrderBy(s => s.Num("ordinal") ?? double.MaxValue)
            .FirstOrDefault();
        if (screenshot is { ValueKind: JsonValueKind.Object } shot && shot.Str("filename") is { } path)
        {
            media.Add(new ScrapedMedia(MediaKinds.Screenshot, ImageBaseUrl + path.TrimStart('/')));
        }

        var basics = item.Obj("basic_info");
        var reviews = item.Obj("reviews")?.Obj("summary_filtered");
        double? rating = reviews is { } r && r.Num("review_count") > 0 && r.Num("percent_positive") is { } percent
            ? Math.Clamp(percent / 100.0, 0, 1)
            : null;
        var description = basics?.Str("short_description") is { } summary ? WebUtility.HtmlDecode(summary).Trim() : null;

        return new ScrapedGame(
            id,
            item.Str("name"),
            string.IsNullOrEmpty(description) ? null : description,
            ReleaseDate(item),
            Names(basics, "developers"),
            Names(basics, "publishers"),
            Rating: rating,
            Media: media);
    }

    /// <summary>The store item a search answer holds whose name is closest to <paramref name="term"/>, Steam's order breaking ties.</summary>
    public static JsonElement? Best(string term, IEnumerable<JsonElement> items)
    {
        ArgumentNullException.ThrowIfNull(items);
        JsonElement? best = null;
        var bestScore = 0.0;
        foreach (var item in items)
        {
            var score = item.Str("name") is { } name ? TitleMatcher.Similarity(term, name) : 0;
            if (score > bestScore)
            {
                (best, bestScore) = (item, score);
            }
        }

        return bestScore >= TitleMatcher.Threshold ? best : null;
    }

    /// <summary>The store items in an answer that Steam found (<c>success</c> 1), in its order.</summary>
    public static IEnumerable<JsonElement> StoreItems(JsonElement root) =>
        (root.Obj("response") ?? default).Arr("store_items").Where(i => i.Num("success") == 1 && i.Str("appid") is not null);

    private static string LogoUrl(string appId) => ImageBaseUrl + "steam/apps/" + appId + "/logo.png";

    /// <summary>
    /// The original release date when Steam has one (a game sold elsewhere first), else its Steam release; none for a
    /// game still to come, whose date is a placeholder.
    /// </summary>
    private static string? ReleaseDate(JsonElement item)
    {
        var release = item.Obj("release");
        if (release is not { } r || r.Str("is_coming_soon") == "true")
        {
            return null;
        }

        return (r.Num("original_release_date") ?? r.Num("steam_release_date")) is { } seconds and > 0
            ? DateTimeOffset.FromUnixTimeSeconds((long)seconds).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)
            : null;
    }

    private static string? Names(JsonElement? basics, string role)
    {
        var list = (basics ?? default).Arr(role)
            .Select(c => c.Str("name")?.Trim())
            .OfType<string>()
            .Where(n => n.Length > 0)
            .Distinct(StringComparer.Ordinal)
            .ToList();
        return list.Count == 0 ? null : string.Join(", ", list);
    }

    /// <summary>The saved response for a store item, after checking for its logo when one is wanted.</summary>
    private async Task<ProviderResult> ResultAsync(JsonElement item, ScrapeQuery query, CancellationToken cancellationToken)
    {
        var id = item.Str("appid")!;
        var saved = new JsonObject { ["id"] = id, ["item"] = LenientJson.ToNode(item) };
        if (query.WantedMedia.Contains(MediaKinds.Logo) && await HasLogoAsync(id, query, cancellationToken).ConfigureAwait(false) is { } logo)
        {
            saved["logo"] = logo;
        }

        var response = saved.ToJsonString();
        return new ProviderResult(Parse(response), null, response);
    }

    /// <summary>
    /// Whether the game has a logo: the API doesn't say, and offering a missing one would keep the fallbacks from
    /// being asked for it. Null when the check failed, which is treated as no logo.
    /// </summary>
    private async Task<bool?> HasLogoAsync(string appId, ScrapeQuery query, CancellationToken cancellationToken)
    {
        try
        {
            var (_, kind) = await _http.SendAsync(Id, _cdn, () => new HttpRequestMessage(HttpMethod.Head, LogoUrl(appId)), Classify,
                "logo check", cancellationToken).ConfigureAwait(false);
            return kind == ReplyKind.Ok;
        }
        catch (ProviderException e) when (e.Failure is ProviderFailure.Transient or ProviderFailure.Rejected)
        {
            _log.Write(LogLevel.Warning, $"{Id}: {query.Game.SystemId}/{query.Game.PathKey}: {e.Message}");
            return null;
        }
    }

    /// <summary>GETs a service method with its <c>input_json</c>; null when it answered with nothing to read.</summary>
    private async Task<string?> GetAsync(string method, JsonObject input, string what, CancellationToken cancellationToken)
    {
        var url = BaseUrl + method + "/v1/?input_json=" + Uri.EscapeDataString(input.ToJsonString());
        var (reply, kind) = await _http.SendAsync(Id, _gate, () => new HttpRequestMessage(HttpMethod.Get, url), Classify, what, cancellationToken).ConfigureAwait(false);
        return kind == ReplyKind.Ok ? reply.Text : null;
    }

    private JsonObject Search(string term, bool withItems)
    {
        var input = new JsonObject
        {
            ["context"] = Context(),
            ["search_term"] = term,
            ["max_results"] = 10,
            ["filters"] = new JsonObject { ["type_filters"] = new JsonObject { ["include_games"] = true } },
        };
        if (withItems)
        {
            input["data_request"] = DataRequest();
        }

        return input;
    }

    /// <summary>The country is required: without it Steam answers with an empty response.</summary>
    private JsonObject Context() => new() { ["language"] = _language, ["country_code"] = Country };

    private static JsonObject DataRequest() => new()
    {
        ["include_assets"] = true,
        ["include_basic_info"] = true,
        ["include_release"] = true,
        ["include_reviews"] = true,
        ["include_screenshots"] = true,
    };

    /// <summary>The common mapping, except that a refusal isn't about credentials (there are none): this game only.</summary>
    private static Classification Classify(HttpReply reply) => reply.Status is 401 or 403
        ? new Classification(ReplyKind.Rejected, $"the Steam store refused the request (HTTP {reply.Status})")
        : ScraperHttp.ClassifyCommon(reply, string.Empty);
}
