using System.Globalization;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Media;

namespace Launcher.Core.Scraping;

/// <summary>The account limits ScreenScraper reports with each response (<c>ssuser</c>). Null where it didn't say.</summary>
/// <param name="MaxThreads">Requests allowed in flight at once.</param>
/// <param name="KoToday">Lookups today that found nothing, which have their own, smaller quota.</param>
public sealed record ScreenScraperLimits(
    int MaxThreads,
    int? PerMinute,
    int? PerDay,
    int? Today,
    int? KoPerDay,
    int? KoToday);

/// <summary>
/// ScreenScraper Web API v2 (https://www.screenscraper.fr/webapi2.php). Looks a game up by its file name, size and
/// system id, plus its hashes when the file is small enough (ScreenScraper asks for a hash); if that finds nothing,
/// by a title search. Respects the limits the account reports: requests in flight, per minute, and the daily
/// quotas (all requests, and lookups that find nothing), which reset at midnight French time.
/// <para>
/// Credentials travel in every URL, and ScreenScraper echoes them back (<c>header.commandRequested</c>, every media
/// URL): the service redacts responses before saving them, and nothing here logs a URL.
/// </para>
/// </summary>
public sealed partial class ScreenScraperScraper : IScraper
{
    public const string BaseUrl = "https://api.screenscraper.fr/api2/";

    /// <summary>
    /// ScreenScraper's media types for each of our kinds, most wanted first. Box textures (<c>box-texture</c>) aren't
    /// scraped any more; the support texture (a disc's or cartridge's art) fills the label slot.
    /// </summary>
    private static readonly Dictionary<string, string[]> MediaTypes = new(StringComparer.Ordinal)
    {
        [MediaKinds.Cover] = ["box-2D"],
        [MediaKinds.Back] = ["box-2D-back"],
        [MediaKinds.Spine] = ["box-2D-side"],
        [MediaKinds.Screenshot] = ["ss", "sstitle"],
        [MediaKinds.Logo] = ["wheel-hd", "wheel"],
        [MediaKinds.Hero] = ["fanart"],
        [MediaKinds.Label] = ["support-texture"],
        [MediaKinds.Video] = ["video-normalized", "video"],
    };

    /// <summary>How long a video's download may take: they're megabytes, and ScreenScraper's servers can be slow.</summary>
    private static readonly TimeSpan VideoTimeout = TimeSpan.FromMinutes(5);

    private static readonly string[] FallbackRegions = ["wor", "us", "eu", "ss", "jp"];

    private readonly ScraperHttp _http;
    private readonly ProviderAccounts _accounts;
    private readonly ScrapingSettings _settings;
    private readonly ILog _log;
    private readonly string _accountsFile;
    private readonly string _softName = "OdysseyLauncher-" + CoreInfo.Version.Split('+')[0];
    private readonly object _limitsLock = new();
    private ScreenScraperLimits? _limits;

    public ScreenScraperScraper(ScraperHttp http, ProviderAccounts accounts, ScrapingSettings settings, ILog log, string accountsFile)
    {
        _http = http;
        _accounts = accounts;
        _settings = settings;
        _log = log;
        _accountsFile = accountsFile;

        // One thread and 30 a minute until the account says otherwise.
        Gate = new ProviderGate(Id, 1, null, 30, http.Clock, http.Delay);
    }

    public string Id => ScraperIds.ScreenScraper;

    public string DisplayName => "ScreenScraper";

    public ScraperCapabilities Capabilities => Supplies;

    /// <summary>What this provider can supply (its capability map).</summary>
    public static ScraperCapabilities Supplies { get; } = new(
        new HashSet<MetadataField>(Enum.GetValues<MetadataField>()),
        new HashSet<string>(MediaKinds.Scrapable, StringComparer.Ordinal));

    public ProviderGate Gate { get; }

    public int MaxConcurrency => Gate.MaxConcurrency;

    /// <summary>The last limits the account reported; null before the first response.</summary>
    public ScreenScraperLimits? Limits
    {
        get
        {
            lock (_limitsLock)
            {
                return _limits;
            }
        }
    }

    public string? Unavailable =>
        _accounts.ScreenScraperDevId is null || _accounts.ScreenScraperDevPassword is null
            ? $"ScreenScraper has no developer credentials: set dev_id and dev_password under [screenscraper] in {_accountsFile}, " +
              "or ODYSSEY_SCREENSCRAPER_DEV_ID and ODYSSEY_SCREENSCRAPER_DEV_PASSWORD (ScreenScraper issues them on its forum)"
            : null;

    private bool HasUser => _accounts.ScreenScraperUsername is not null && _accounts.ScreenScraperPassword is not null;

    public string? Unsupported(SystemConfig system) =>
        system.ScreenScraperId is null ? $"{system.Name} has no screenscraper_id in systems.toml" : null;

    public async Task PrepareAsync(CancellationToken cancellationToken)
    {
        if (!HasUser)
        {
            _log.Write(LogLevel.Info, "screenscraper: no username in secrets.toml, so anonymous limits apply (one thread, and closed to anonymous users when busy)");
            return;
        }

        // ssuserInfos.php reports the account's limits and doesn't count towards the quota.
        var (reply, _) = await _http.SendAsync(Id, Gate, () => Get(Url("ssuserInfos.php")), Classify, "account check", cancellationToken).ConfigureAwait(false);
        using var document = LenientJson.Parse(reply.Text);
        if (document is not null)
        {
            UpdateLimits(document.RootElement);
        }
    }

    public async Task<string> TestConnectionAsync(CancellationToken cancellationToken)
    {
        if (Unavailable is { } missing)
        {
            throw new ProviderException(Id, ProviderFailure.AuthFailed, missing);
        }

        if (!HasUser)
        {
            // ssinfraInfos.php needs only the developer credentials, and says whether anonymous users are let in.
            var (infra, _) = await _http.SendAsync(Id, Gate, () => Get(Url("ssinfraInfos.php")), Classify, "connection test", cancellationToken).ConfigureAwait(false);
            using var servers = LenientJson.Parse(infra.Text);
            var closed = servers?.RootElement.Obj("response")?.Obj("serveurs")?.Str("closefornomember") == "1";
            return "ScreenScraper accepted the developer credentials. With no username and password, anonymous limits apply (one thread)" +
                (closed ? ", and it's closed to anonymous users right now because it's busy." : ".");
        }

        // ssuserInfos.php checks the account too, and doesn't count towards the quota.
        var (reply, _) = await _http.SendAsync(Id, Gate, () => Get(Url("ssuserInfos.php")), Classify, "connection test", cancellationToken).ConfigureAwait(false);
        using (var document = LenientJson.Parse(reply.Text))
        {
            if (document is not null)
            {
                UpdateLimits(document.RootElement);
            }
        }

        if (Limits is not { } limits)
        {
            return "ScreenScraper accepted the credentials.";
        }

        var today = limits.PerDay is { } perDay
            ? string.Create(CultureInfo.InvariantCulture, $"{limits.Today ?? 0:N0} of {perDay:N0} requests used today")
            : "no daily limit reported";
        return string.Create(CultureInfo.InvariantCulture, $"Signed in to ScreenScraper: {today}, up to {limits.MaxThreads} at once.");
    }

    public async Task<ProviderResult> LookupAsync(ScrapeQuery query, CancellationToken cancellationToken)
    {
        ThrowIfQuotaUsed();
        var (game, method, text) = await FileLookupAsync(query, cancellationToken).ConfigureAwait(false);
        if (game is not null)
        {
            return new ProviderResult(game, method, text);
        }

        // Not recognised by file: search by title, and take a hit only if its name matches. What ScreenScraper said
        // goes back with the not-found result, for --save-responses.
        var diagnosis = new StringBuilder("jeuInfos.php, romnom=").Append(query.FileName).Append(": ").Append(text.Trim());
        var term = TitleMatcher.SearchTerm(query.Title);
        if (term.Length < 4)
        {
            diagnosis.Append("\njeuRecherche.php not asked: '").Append(term).Append("' is too short to search for");
            return new ProviderResult(null, null, diagnosis.ToString());
        }

        var candidates = await SearchAsync(term, query.System, cancellationToken).ConfigureAwait(false);
        var ranked = candidates
            .Select(c => (Candidate: c, Score: TitleMatcher.Similarity(term, c.Name)))
            .OrderByDescending(c => c.Score)
            .ToList();
        var best = ranked.FirstOrDefault(c => c.Score >= TitleMatcher.Threshold);
        if (best.Candidate is null)
        {
            diagnosis.Append(CultureInfo.InvariantCulture, $"\njeuRecherche.php, recherche={term}: {candidates.Count} results");
            if (ranked.Count > 0)
            {
                diagnosis.Append(CultureInfo.InvariantCulture, $", the closest '{ranked[0].Candidate.Name}' ({ranked[0].Candidate.ProviderGameId}) at {ranked[0].Score:P0}, under {TitleMatcher.Threshold:P0}");
            }

            return new ProviderResult(null, null, diagnosis.ToString());
        }

        var fetched = await FetchAsync(best.Candidate.ProviderGameId, query, cancellationToken).ConfigureAwait(false);
        return fetched.Found ? fetched with { Method = MatchMethods.Search } : fetched;
    }

    public async Task<ScrapeCandidate?> IdentifyFileAsync(ScrapeQuery query, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(query);
        ThrowIfQuotaUsed();
        var (game, method, _) = await FileLookupAsync(query, cancellationToken).ConfigureAwait(false);
        return game is null
            ? null
            : new ScrapeCandidate(game.ProviderGameId, game.Title ?? query.FileName, game.ReleaseDate is { Length: >= 4 } date ? date[..4] : null, method);
    }

    /// <summary>
    /// ScreenScraper's ROM index: the file's name, size and hashes. For arcade sets the name is the MAME short name
    /// (<c>sf2.zip</c>), which ScreenScraper knows, though its title search doesn't.
    /// </summary>
    private async Task<(ScrapedGame? Game, string? Method, string Text)> FileLookupAsync(ScrapeQuery query, CancellationToken cancellationToken)
    {
        var system = query.System.ScreenScraperId!.Value.ToString(CultureInfo.InvariantCulture);
        var url = Url("jeuInfos.php",
            ("systemeid", system),
            ("romtype", "rom"),
            ("romnom", query.FileName),
            ("romtaille", query.SizeBytes.ToString(CultureInfo.InvariantCulture)),
            ("crc", query.Hashes?.Crc32),
            ("md5", query.Hashes?.Md5),
            ("sha1", query.Hashes?.Sha1));
        var (reply, kind) = await _http.SendAsync(Id, Gate, () => Get(url), Classify, "lookup", cancellationToken).ConfigureAwait(false);
        if (kind == ReplyKind.Ok && ParseReply(reply.Text) is { } game)
        {
            var method = query.Hashes is not null && RomCrc(reply.Text) is { } crc
                && crc.Equals(query.Hashes.Crc32, StringComparison.OrdinalIgnoreCase)
                ? MatchMethods.Hash
                : MatchMethods.Filename;
            return (game, method, reply.Text);
        }

        return (null, null, reply.Text);
    }

    public async Task<ProviderResult> FetchAsync(string providerGameId, ScrapeQuery query, CancellationToken cancellationToken)
    {
        ThrowIfQuotaUsed();
        var url = Url("jeuInfos.php",
            ("systemeid", query.System.ScreenScraperId?.ToString(CultureInfo.InvariantCulture)),
            ("gameid", providerGameId));
        var (reply, kind) = await _http.SendAsync(Id, Gate, () => Get(url), Classify, "fetch", cancellationToken).ConfigureAwait(false);
        return kind == ReplyKind.Ok && ParseReply(reply.Text) is { } game
            ? new ProviderResult(game, null, reply.Text)
            : ProviderResult.NotFound;
    }

    public async Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(string title, SystemConfig system, CancellationToken cancellationToken)
    {
        ThrowIfQuotaUsed();
        var url = Url("jeuRecherche.php",
            ("systemeid", system.ScreenScraperId?.ToString(CultureInfo.InvariantCulture)),
            ("recherche", title));
        var (reply, kind) = await _http.SendAsync(Id, Gate, () => Get(url), Classify, "search", cancellationToken).ConfigureAwait(false);
        var candidates = new List<ScrapeCandidate>();
        if (kind != ReplyKind.Ok)
        {
            return candidates;
        }

        using var document = LenientJson.Parse(reply.Text);
        if (document is null || document.RootElement.Obj("response") is not { } response)
        {
            return candidates;
        }

        UpdateLimits(document.RootElement);
        foreach (var jeu in response.Arr("jeux"))
        {
            // No hits come back as a list holding one empty object.
            if (jeu.Str("id") is not { } id)
            {
                continue;
            }

            var name = Pick(jeu.Arr("noms"), "region", Regions()) ?? string.Empty;
            var date = Pick(jeu.Arr("dates"), "region", Regions());
            candidates.Add(new ScrapeCandidate(id, WebUtility.HtmlDecode(name), date is { Length: >= 4 } ? date[..4] : null));
        }

        return candidates;
    }

    /// <summary>
    /// ScreenScraper's system list (<c>systemesListe.php</c>, which needs developer credentials): id → every name it
    /// gives. For checking the built-in <c>screenscraper_id</c> values (a carry-over from M2).
    /// </summary>
    public async Task<IReadOnlyDictionary<int, IReadOnlyList<string>>> ListSystemsAsync(CancellationToken cancellationToken)
    {
        var (reply, _) = await _http.SendAsync(Id, Gate, () => Get(Url("systemesListe.php")), Classify, "system list", cancellationToken).ConfigureAwait(false);
        var systems = new SortedDictionary<int, IReadOnlyList<string>>();
        using var document = LenientJson.Parse(reply.Text);
        if (document?.RootElement.Obj("response") is not { } response)
        {
            return systems;
        }

        foreach (var system in response.Arr("systemes"))
        {
            if (system.Num("id") is not { } id)
            {
                continue;
            }

            var names = new List<string>();
            if (system.Obj("noms") is { } noms)
            {
                foreach (var name in noms.EnumerateObject())
                {
                    if (name.Value.ValueKind == JsonValueKind.String && name.Value.GetString() is { Length: > 0 } text && !names.Contains(text))
                    {
                        names.Add(text);
                    }
                }
            }

            systems[(int)id] = names;
        }

        return systems;
    }

    public async Task<byte[]> DownloadAsync(ScrapedMedia media, CancellationToken cancellationToken)
    {
        if (!Uri.TryCreate(media.Url, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps
            || !(uri.Host == "screenscraper.fr" || uri.Host.EndsWith(".screenscraper.fr", StringComparison.OrdinalIgnoreCase)))
        {
            throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the media URL isn't on screenscraper.fr");
        }

        var timeout = media.Kind == MediaKinds.Video ? VideoTimeout : (TimeSpan?)null;
        var (reply, kind) = await _http.SendAsync(Id, Gate, () => Get(uri.AbsoluteUri), ClassifyMedia, media.Kind + " download", cancellationToken, timeout).ConfigureAwait(false);
        if (kind == ReplyKind.NotFound)
        {
            throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: ScreenScraper has no file for it");
        }

        return reply.Body;
    }

    /// <summary>Reads a saved or live <c>jeuInfos.php</c> response. Offline and pure: rebuilds use it.</summary>
    public static ScrapedGame? Parse(string response, ScrapingSettings settings)
    {
        ArgumentNullException.ThrowIfNull(response);
        ArgumentNullException.ThrowIfNull(settings);
        using var document = LenientJson.Parse(response);
        if (document?.RootElement.Obj("response") is not { } body || body.Obj("jeu") is not { } jeu)
        {
            return null;
        }

        return ParseGame(jeu, settings);
    }

    private ScrapedGame? ParseReply(string text)
    {
        using var document = LenientJson.Parse(text);
        if (document is null)
        {
            return null;
        }

        UpdateLimits(document.RootElement);
        return document.RootElement.Obj("response")?.Obj("jeu") is { } jeu ? ParseGame(jeu, _settings) : null;
    }

    private static ScrapedGame? ParseGame(JsonElement jeu, ScrapingSettings settings)
    {
        var id = jeu.Str("id");
        if (id is null || jeu.Str("notgame") == "true")
        {
            return null;
        }

        var regions = RegionOrder(settings);
        var languages = LanguageOrder(settings);
        var title = Decode(Pick(jeu.Arr("noms"), "region", regions));
        var description = Decode(Pick(jeu.Arr("synopsis"), "langue", languages));
        var date = Pick(jeu.Arr("dates"), "region", regions);
        var releaseDate = date is not null && IsoDate().IsMatch(date) ? date : null;
        double? rating = jeu.Obj("note")?.Num("text") is { } note ? Math.Clamp(note / 20.0, 0, 1) : null;

        var genres = jeu.Arr("genres").ToList();
        var primary = genres.Where(g => g.Str("principale") == "1").ToList();
        var genreNames = (primary.Count > 0 ? primary : genres.Take(1))
            .Select(g => Decode(Pick(g.Arr("noms"), "langue", languages)))
            .OfType<string>()
            .Distinct(StringComparer.Ordinal)
            .ToList();

        var media = new List<ScrapedMedia>();
        var gameMedia = jeu.Arr("medias").Where(m => m.Str("parent") == "jeu" && m.Str("url") is not null).ToList();
        foreach (var (kind, types) in MediaTypes)
        {
            foreach (var type in types)
            {
                var offered = gameMedia.Where(m => m.Str("type") == type).ToList();
                if (offered.Count == 0)
                {
                    continue;
                }

                var chosen = offered
                    .OrderBy(m => m.Str("region") is { } r && Array.IndexOf(regions, r) is var i and >= 0 ? i : regions.Length)
                    .First();
                media.Add(new ScrapedMedia(kind, chosen.Str("url")!, chosen.Str("region")));
                break;
            }
        }

        return new ScrapedGame(
            id,
            title,
            description,
            releaseDate,
            Decode(jeu.Obj("developpeur")?.Str("text")),
            Decode(jeu.Obj("editeur")?.Str("text")),
            genreNames.Count == 0 ? null : string.Join(", ", genreNames),
            jeu.Obj("joueurs")?.Str("text"),
            rating,
            media);
    }

    private string[] Regions() => RegionOrder(_settings);

    private static string[] RegionOrder(ScrapingSettings settings) => [.. settings.Regions.Concat(FallbackRegions).Distinct(StringComparer.Ordinal)];

    private static string[] LanguageOrder(ScrapingSettings settings) => [.. settings.Languages.Append("en").Distinct(StringComparer.Ordinal)];

    /// <summary>The text of the entry whose <paramref name="key"/> comes first in <paramref name="order"/>, else the first entry's.</summary>
    private static string? Pick(IEnumerable<JsonElement> entries, string key, string[] order)
    {
        string? best = null;
        var bestRank = int.MaxValue;
        foreach (var entry in entries)
        {
            if (entry.Str("text") is not { } text)
            {
                continue;
            }

            var rank = entry.Str(key) is { } code && Array.IndexOf(order, code) is var i and >= 0 ? i : order.Length;
            if (rank < bestRank)
            {
                (best, bestRank) = (text, rank);
            }
        }

        return best;
    }

    private static string? Decode(string? text) => text is null ? null : WebUtility.HtmlDecode(text).Trim() is { Length: > 0 } t ? t : null;

    private static string? RomCrc(string text)
    {
        using var document = LenientJson.Parse(text);
        return document?.RootElement.Obj("response")?.Obj("jeu")?.Obj("rom")?.Str("romcrc");
    }

    private void UpdateLimits(JsonElement root)
    {
        if (root.Obj("response")?.Obj("ssuser") is not { } user)
        {
            return;
        }

        static int? Int(JsonElement e, string name) => e.Num(name) is { } v ? (int)v : null;
        var limits = new ScreenScraperLimits(
            Math.Max(1, Int(user, "maxthreads") ?? 1),
            Int(user, "maxrequestspermin"),
            Int(user, "maxrequestsperday"),
            Int(user, "requeststoday"),
            Int(user, "maxrequestskoperday"),
            Int(user, "requestskotoday"));
        lock (_limitsLock)
        {
            _limits = limits;
        }

        Gate.SetLimits(limits.MaxThreads, limits.PerMinute);
    }

    private void ThrowIfQuotaUsed()
    {
        var limits = Limits;
        if (limits is null)
        {
            return;
        }

        if (limits.PerDay is { } perDay && limits.Today >= perDay)
        {
            throw new ProviderException(Id, ProviderFailure.QuotaExhausted,
                $"ScreenScraper's daily quota is used up ({limits.Today} of {perDay} requests)", NextReset());
        }

        if (limits.KoPerDay is { } koPerDay && limits.KoToday >= koPerDay)
        {
            throw new ProviderException(Id, ProviderFailure.QuotaExhausted,
                $"ScreenScraper's daily quota of lookups that find nothing is used up ({limits.KoToday} of {koPerDay})", NextReset());
        }
    }

    /// <summary>ScreenScraper's day ends at midnight in France.</summary>
    private DateTimeOffset NextReset()
    {
        var now = _http.Clock.GetUtcNow();
        TimeZoneInfo zone;
        try
        {
            zone = TimeZoneInfo.FindSystemTimeZoneById("Europe/Paris");
        }
        catch (TimeZoneNotFoundException)
        {
            return now.Date.AddDays(1);
        }

        var local = TimeZoneInfo.ConvertTime(now, zone);
        var midnight = new DateTime(local.Year, local.Month, local.Day, 0, 0, 0, DateTimeKind.Unspecified).AddDays(1);
        return new DateTimeOffset(midnight, zone.GetUtcOffset(midnight));
    }

    private Classification Classify(HttpReply reply)
    {
        var text = reply.Status is >= 200 and < 300 || reply.Body.Length < 2048 ? reply.Text : string.Empty;
        if (reply.Status is >= 200 and < 300)
        {
            if (text.Contains("Erreur de login", StringComparison.OrdinalIgnoreCase))
            {
                return new Classification(ReplyKind.AuthFailed, "ScreenScraper refused the username or password in secrets.toml");
            }

            return text.TrimStart().StartsWith('{')
                ? Classification.Ok
                : new Classification(ReplyKind.Transient, "ScreenScraper sent something that isn't JSON");
        }

        return reply.Status switch
        {
            404 => Classification.NotFound,
            400 => new Classification(ReplyKind.Rejected, "ScreenScraper refused the request: " + FirstLine(text)),
            401 => new Classification(ReplyKind.Closed, "ScreenScraper is closed to anonymous and inactive accounts while it's busy", _http.Clock.GetUtcNow().AddMinutes(15)),
            403 => new Classification(ReplyKind.AuthFailed, "ScreenScraper refused the developer credentials in secrets.toml"),
            423 => new Classification(ReplyKind.Closed, "ScreenScraper's API is closed", _http.Clock.GetUtcNow().AddHours(1)),
            426 => new Classification(ReplyKind.AuthFailed, "ScreenScraper has blacklisted this version of the launcher"),
            429 => new Classification(ReplyKind.RateLimited, "ScreenScraper's thread or per-minute limit was reached"),
            430 => new Classification(ReplyKind.QuotaExhausted, "ScreenScraper's daily quota is used up", NextReset()),
            431 => new Classification(ReplyKind.QuotaExhausted, "ScreenScraper's daily quota of lookups that find nothing is used up", NextReset()),
            408 or >= 500 => new Classification(ReplyKind.Transient, $"ScreenScraper server error (HTTP {reply.Status})"),
            _ => new Classification(ReplyKind.Rejected, $"ScreenScraper refused the request (HTTP {reply.Status})"),
        };
    }

    private Classification ClassifyMedia(HttpReply reply)
    {
        if (reply.Status is >= 200 and < 300)
        {
            return reply.Body.AsSpan().StartsWith("NOMEDIA"u8) ? Classification.NotFound : Classification.Ok;
        }

        return Classify(reply);
    }

    private static string FirstLine(string text)
    {
        var line = text.Split('\n', 2)[0].Trim();
        return line.Length > 160 ? line[..160] : line;
    }

    private string Url(string endpoint, params (string Name, string? Value)[] parameters)
    {
        var builder = new StringBuilder(BaseUrl).Append(endpoint).Append('?');
        void Add(string name, string? value)
        {
            if (value is null)
            {
                return;
            }

            if (builder[^1] != '?')
            {
                builder.Append('&');
            }

            builder.Append(name).Append('=').Append(Uri.EscapeDataString(value));
        }

        Add("devid", _accounts.ScreenScraperDevId);
        Add("devpassword", _accounts.ScreenScraperDevPassword);
        Add("softname", _softName);
        Add("output", "json");
        if (HasUser)
        {
            Add("ssid", _accounts.ScreenScraperUsername);
            Add("sspassword", _accounts.ScreenScraperPassword);
        }

        foreach (var (name, value) in parameters)
        {
            Add(name, value);
        }

        return builder.ToString();
    }

    private static HttpRequestMessage Get(string url) => new(HttpMethod.Get, url);

    [GeneratedRegex(@"^\d{4}(-\d{2}(-\d{2})?)?$")]
    private static partial Regex IsoDate();
}
