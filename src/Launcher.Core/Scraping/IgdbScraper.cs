using System.Globalization;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Media;

namespace Launcher.Core.Scraping;

/// <summary>
/// A Twitch app access token for IGDB (client-credentials grant), cached in memory and in
/// <c>DataDir/tokens/igdb.json</c>. App tokens last about 60 days and can't be refreshed: a new one is requested when the
/// cached one is within a day of expiry, or when IGDB refuses it. Caching matters: an app may only have 25 active
/// tokens, and asking for more silently revokes the oldest. The file is keyed by a hash of the client id, so
/// changing the id discards it. The token is a credential: it's never logged.
/// </summary>
public sealed class TwitchAppToken
{
    public const string TokenUrl = "https://id.twitch.tv/oauth2/token";

    private readonly ScraperHttp _http;
    private readonly ProviderAccounts _accounts;
    private readonly string _file;
    private readonly SemaphoreSlim _lock = new(1, 1);
    private readonly ProviderGate _gate;
    private string? _token;
    private DateTimeOffset _expiresAt;

    public TwitchAppToken(ScraperHttp http, ProviderAccounts accounts, string file)
    {
        _http = http;
        _accounts = accounts;
        _file = file;
        _gate = new ProviderGate("twitch", 1, null, null, http.Clock, http.Delay);
    }

    /// <summary>How many tokens this instance has requested from Twitch: tests check the cache is used.</summary>
    public int Requested { get; private set; }

    /// <summary>A valid token: the cached one unless it's missing, near expiry, or <paramref name="refused"/>.</summary>
    /// <param name="refused">The token IGDB just refused, so it isn't handed out again.</param>
    public async Task<string> GetAsync(string? refused, CancellationToken cancellationToken)
    {
        await _lock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var now = _http.Clock.GetUtcNow();
            if (_token is null)
            {
                ReadFile();
            }

            if (_token is not null && _token != refused && _expiresAt - now > TimeSpan.FromDays(1))
            {
                return _token;
            }

            return await RequestAsync(cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _lock.Release();
        }
    }

    private async Task<string> RequestAsync(CancellationToken cancellationToken)
    {
        Requested++;
        HttpRequestMessage Make() => new(HttpMethod.Post, TokenUrl)
        {
            // A form body rather than the query string, so the secret never appears in a URL.
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["client_id"] = _accounts.IgdbClientId!,
                ["client_secret"] = _accounts.IgdbClientSecret!,
                ["grant_type"] = "client_credentials",
            }),
        };

        var (reply, _) = await _http.SendAsync(ScraperIds.Igdb, _gate, Make,
            r => r.Status is 400 or 401 or 403
                ? new Classification(ReplyKind.AuthFailed, "Twitch refused the IGDB client_id or client_secret in secrets.toml")
                : ScraperHttp.ClassifyCommon(r, "Twitch refused the IGDB client_id or client_secret in secrets.toml"),
            "access token", cancellationToken).ConfigureAwait(false);
        using var document = LenientJson.Parse(reply.Text);
        var token = document?.RootElement.Str("access_token");
        var lifetime = document?.RootElement.Num("expires_in") ?? 0;
        if (token is null || lifetime <= 0)
        {
            throw new ProviderException(ScraperIds.Igdb, ProviderFailure.Transient, "Twitch's token response had no access token");
        }

        _token = token;
        _expiresAt = _http.Clock.GetUtcNow().AddSeconds(lifetime);
        WriteFile();
        return token;
    }

    private string ClientKey() =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(_accounts.IgdbClientId ?? string.Empty)));

    private void ReadFile()
    {
        try
        {
            if (!File.Exists(_file))
            {
                return;
            }

            using var document = LenientJson.Parse(File.ReadAllText(_file));
            if (document is null || document.RootElement.Str("client") != ClientKey())
            {
                return;
            }

            _token = document.RootElement.Str("access_token");
            _expiresAt = DateTimeOffset.FromUnixTimeSeconds((long)(document.RootElement.Num("expires_at") ?? 0));
        }
        catch (IOException)
        {
            _token = null;
        }
    }

    private void WriteFile()
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(_file)!);
            var json = new JsonObject
            {
                ["client"] = ClientKey(),
                ["access_token"] = _token,
                ["expires_at"] = _expiresAt.ToUnixTimeSeconds(),
            }.ToJsonString();
            var temp = _file + ".tmp";
            File.WriteAllText(temp, json);
            File.Move(temp, _file, overwrite: true);
        }
        catch (IOException)
        {
            // Only a cache: the next run asks Twitch again.
        }
    }
}

/// <summary>
/// IGDB API v4 (https://api-docs.igdb.com): metadata, front covers, screenshots and artworks (as the hero image). It
/// has no back, spine or box texture, and no game logos. Games are found by a name search limited to the system's
/// IGDB platforms (<c>igdb_platforms</c> in systems.toml). Authenticates with the user's own Twitch application
/// (<see cref="TwitchAppToken"/>). Limits: 4 requests a second and 8 open at once; this stays at 4 open.
/// </summary>
public sealed class IgdbScraper : IScraper
{
    public const string BaseUrl = "https://api.igdb.com/v4/";
    public const string ImageBaseUrl = "https://images.igdb.com/igdb/image/upload/";

    private const string Fields =
        "name,alternative_names.name,summary,first_release_date," +
        "release_dates.date,release_dates.date_format,release_dates.platform,release_dates.release_region,release_dates.y,release_dates.m,release_dates.d," +
        "involved_companies.company.name,involved_companies.developer,involved_companies.publisher," +
        "genres.name,game_modes.name,multiplayer_modes.offlinemax,multiplayer_modes.offlinecoopmax,multiplayer_modes.platform," +
        "total_rating,aggregated_rating,rating,cover.image_id,screenshots.image_id,artworks.image_id,platforms";

    /// <summary>Our region codes (ScreenScraper's) to IGDB's release regions.</summary>
    private static readonly Dictionary<string, int> ReleaseRegions = new(StringComparer.Ordinal)
    {
        ["eu"] = 1, ["fr"] = 1, ["de"] = 1, ["uk"] = 1, ["sp"] = 1, ["it"] = 1,
        ["us"] = 2, ["au"] = 3, ["nz"] = 4, ["jp"] = 5, ["cn"] = 6, ["asi"] = 7, ["wor"] = 8, ["kr"] = 9, ["br"] = 10,
    };

    private readonly ScraperHttp _http;
    private readonly ProviderAccounts _accounts;
    private readonly ScrapingSettings _settings;
    private readonly string _accountsFile;
    private readonly ProviderGate _gate;
    private readonly ProviderGate _images;

    public IgdbScraper(ScraperHttp http, ProviderAccounts accounts, ScrapingSettings settings, ILog log, string accountsFile, string tokenFile)
    {
        _ = log;
        _http = http;
        _accounts = accounts;
        _settings = settings;
        _accountsFile = accountsFile;
        _gate = new ProviderGate(Id, 4, 4, null, http.Clock, http.Delay);
        _images = new ProviderGate(Id + " images", 4, null, null, http.Clock, http.Delay);
        Token = new TwitchAppToken(http, accounts, tokenFile);
    }

    public string Id => ScraperIds.Igdb;

    public string DisplayName => "IGDB";

    public TwitchAppToken Token { get; }

    public ScraperCapabilities Capabilities => Supplies;

    /// <summary>What this provider can supply (its capability map).</summary>
    public static ScraperCapabilities Supplies { get; } = new(
        new HashSet<MetadataField>(Enum.GetValues<MetadataField>()),
        new HashSet<string>([MediaKinds.Cover, MediaKinds.Screenshot, MediaKinds.Hero], StringComparer.Ordinal));

    public int MaxConcurrency => _gate.MaxConcurrency;

    public string? Unavailable => _accounts.IgdbClientId is null || _accounts.IgdbClientSecret is null
        ? $"IGDB has no Twitch application credentials: set client_id and client_secret under [igdb] in {_accountsFile}, " +
          "or ODYSSEY_IGDB_CLIENT_ID and ODYSSEY_IGDB_CLIENT_SECRET (register a confidential application at https://dev.twitch.tv/console)"
        : null;

    public string? Unsupported(SystemConfig system) =>
        system.IgdbPlatforms is null or { Count: 0 } ? $"{system.Name} has no igdb_platforms in systems.toml" : null;

    /// <summary>Nothing: the token is fetched on first use, so a batch IGDB never gets asked about costs no token.</summary>
    public Task PrepareAsync(CancellationToken cancellationToken) => Task.CompletedTask;

    public async Task<ProviderResult> LookupAsync(ScrapeQuery query, CancellationToken cancellationToken)
    {
        var term = TitleMatcher.SearchTerm(query.Title);
        var body = $"fields {Fields}; search \"{Escape(term)}\"; where platforms = ({Platforms(query.System)}) & version_parent = null; limit 10;";
        var text = await QueryAsync(body, "search", cancellationToken).ConfigureAwait(false);
        using var document = LenientJson.Parse(text);
        if (document?.RootElement.ValueKind != JsonValueKind.Array)
        {
            return ProviderResult.NotFound;
        }

        JsonElement? best = null;
        var bestScore = 0.0;
        foreach (var game in document.RootElement.EnumerateArray())
        {
            var score = game.Str("name") is { } name ? TitleMatcher.Similarity(term, name) : 0;
            foreach (var alternative in game.Arr("alternative_names"))
            {
                if (alternative.Str("name") is { } other)
                {
                    score = Math.Max(score, TitleMatcher.Similarity(term, other) - 0.01);
                }
            }

            if (score > bestScore)
            {
                (best, bestScore) = (game, score);
            }
        }

        if (best is not { } chosen || bestScore < TitleMatcher.Threshold)
        {
            return ProviderResult.NotFound;
        }

        // The search already returned every field: save the chosen game alone, as a fetch would.
        var response = "[" + chosen.GetRawText() + "]";
        return new ProviderResult(Parse(response, _settings, query.System), MatchMethods.Search, response);
    }

    public async Task<ProviderResult> FetchAsync(string providerGameId, ScrapeQuery query, CancellationToken cancellationToken)
    {
        if (!long.TryParse(providerGameId, NumberStyles.None, CultureInfo.InvariantCulture, out var id))
        {
            return ProviderResult.NotFound;
        }

        var text = await QueryAsync($"fields {Fields}; where id = {id};", "fetch", cancellationToken).ConfigureAwait(false);
        return Parse(text, _settings, query.System) is { } game ? new ProviderResult(game, null, text) : ProviderResult.NotFound;
    }

    public async Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(string title, SystemConfig system, CancellationToken cancellationToken)
    {
        var text = await QueryAsync(
            $"fields name,first_release_date; search \"{Escape(title)}\"; where platforms = ({Platforms(system)}); limit 20;",
            "search", cancellationToken).ConfigureAwait(false);
        using var document = LenientJson.Parse(text);
        var candidates = new List<ScrapeCandidate>();
        if (document?.RootElement.ValueKind == JsonValueKind.Array)
        {
            foreach (var game in document.RootElement.EnumerateArray())
            {
                if (game.Str("id") is { } id && game.Str("name") is { } name)
                {
                    var year = game.Num("first_release_date") is { } seconds
                        ? DateTimeOffset.FromUnixTimeSeconds((long)seconds).Year.ToString(CultureInfo.InvariantCulture)
                        : null;
                    candidates.Add(new ScrapeCandidate(id, name, year));
                }
            }
        }

        return candidates;
    }

    public async Task<byte[]> DownloadAsync(ScrapedMedia media, CancellationToken cancellationToken)
    {
        if (!media.Url.StartsWith(ImageBaseUrl, StringComparison.Ordinal))
        {
            throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the image URL isn't on images.igdb.com");
        }

        var (reply, kind) = await _http.SendAsync(Id, _images, () => new HttpRequestMessage(HttpMethod.Get, media.Url),
            r => ScraperHttp.ClassifyCommon(r, "IGDB's image server refused the download"), media.Kind + " download", cancellationToken).ConfigureAwait(false);
        return kind == ReplyKind.NotFound
            ? throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the image is gone")
            : reply.Body;
    }

    /// <summary>Reads a saved or live games response (an array; the first game is used). Offline and pure.</summary>
    public static ScrapedGame? Parse(string response, ScrapingSettings settings, SystemConfig system)
    {
        ArgumentNullException.ThrowIfNull(response);
        ArgumentNullException.ThrowIfNull(settings);
        ArgumentNullException.ThrowIfNull(system);
        using var document = LenientJson.Parse(response);
        if (document?.RootElement.ValueKind != JsonValueKind.Array || document.RootElement.GetArrayLength() == 0)
        {
            return null;
        }

        var game = document.RootElement[0];
        if (game.Str("id") is not { } id)
        {
            return null;
        }

        var platforms = system.IgdbPlatforms ?? [];
        var companies = game.Arr("involved_companies").ToList();
        string? Companies(string role) => Join(companies
            .Where(c => c.Str(role) == "true")
            .Select(c => c.Obj("company")?.Str("name")));

        double? rating = (game.Num("total_rating") ?? game.Num("aggregated_rating") ?? game.Num("rating")) is { } r
            ? Math.Clamp(r / 100.0, 0, 1)
            : null;

        var media = new List<ScrapedMedia>();
        if (game.Obj("cover")?.Str("image_id") is { } cover)
        {
            media.Add(new ScrapedMedia(MediaKinds.Cover, Image(cover)));
        }

        if (game.Arr("screenshots").FirstOrDefault().Str("image_id") is { } screenshot)
        {
            media.Add(new ScrapedMedia(MediaKinds.Screenshot, Image(screenshot)));
        }

        if (game.Arr("artworks").FirstOrDefault().Str("image_id") is { } artwork)
        {
            media.Add(new ScrapedMedia(MediaKinds.Hero, Image(artwork)));
        }

        return new ScrapedGame(
            id,
            game.Str("name"),
            game.Str("summary")?.Trim(),
            ReleaseDate(game, settings, platforms),
            Companies("developer"),
            Companies("publisher"),
            Join(game.Arr("genres").Select(g => g.Str("name"))),
            Players(game, platforms),
            rating,
            media);
    }

    /// <summary>
    /// The system's release in the most wanted region, as precise as IGDB knows it (<c>date_format</c>: 0 a full date,
    /// 1 year and month, 2 year only, 3-6 a quarter, 7 unknown). Falls back to <c>first_release_date</c>, a full date.
    /// </summary>
    private static string? ReleaseDate(JsonElement game, ScrapingSettings settings, IReadOnlyList<int> platforms)
    {
        var wanted = settings.Regions.Select(r => ReleaseRegions.TryGetValue(r, out var id) ? id : -1).Where(id => id > 0).ToList();
        JsonElement? best = null;
        var bestRank = int.MaxValue;
        long bestDate = long.MaxValue;
        foreach (var release in game.Arr("release_dates"))
        {
            if (release.Num("platform") is not { } platform || !platforms.Contains((int)platform) || release.Num("date_format") is 7)
            {
                continue;
            }

            var region = (int)(release.Num("release_region") ?? 0);
            var rank = wanted.IndexOf(region) is var i and >= 0 ? i : wanted.Count;
            var date = (long)(release.Num("date") ?? long.MaxValue);
            if (rank < bestRank || (rank == bestRank && date < bestDate))
            {
                (best, bestRank, bestDate) = (release, rank, date);
            }
        }

        if (best is { } chosen && chosen.Num("y") is { } y)
        {
            var year = ((int)y).ToString("D4", CultureInfo.InvariantCulture);
            return chosen.Num("date_format") switch
            {
                0 when chosen.Num("m") is { } m && chosen.Num("d") is { } d => string.Create(CultureInfo.InvariantCulture, $"{year}-{(int)m:D2}-{(int)d:D2}"),
                0 or 1 when chosen.Num("m") is { } m => string.Create(CultureInfo.InvariantCulture, $"{year}-{(int)m:D2}"),
                _ => year,
            };
        }

        return game.Num("first_release_date") is { } seconds
            ? DateTimeOffset.FromUnixTimeSeconds((long)seconds).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)
            : null;
    }

    /// <summary>"1-4" from the system's multiplayer modes; "1" for a game whose only mode is single player.</summary>
    private static string? Players(JsonElement game, IReadOnlyList<int> platforms)
    {
        var most = 0;
        foreach (var mode in game.Arr("multiplayer_modes"))
        {
            if (mode.Num("platform") is { } platform && !platforms.Contains((int)platform))
            {
                continue;
            }

            most = Math.Max(most, (int)Math.Max(mode.Num("offlinemax") ?? 0, mode.Num("offlinecoopmax") ?? 0));
        }

        if (most > 1)
        {
            return string.Create(CultureInfo.InvariantCulture, $"1-{most}");
        }

        var modes = game.Arr("game_modes").Select(m => m.Str("name")).OfType<string>().ToList();
        return modes.Count == 1 && modes[0].Equals("Single player", StringComparison.OrdinalIgnoreCase) ? "1" : null;
    }

    private static string? Join(IEnumerable<string?> names)
    {
        var list = names.OfType<string>().Select(n => n.Trim()).Where(n => n.Length > 0).Distinct(StringComparer.Ordinal).ToList();
        return list.Count == 0 ? null : string.Join(", ", list);
    }

    private static string Image(string imageId) => ImageBaseUrl + "t_1080p/" + imageId + ".jpg";

    private static string Platforms(SystemConfig system) =>
        string.Join(',', (system.IgdbPlatforms ?? []).Select(p => p.ToString(CultureInfo.InvariantCulture)));

    private static string Escape(string text) => text.Replace("\\", "\\\\", StringComparison.Ordinal).Replace("\"", "\\\"", StringComparison.Ordinal);

    /// <summary>POSTs an Apicalypse query to the games endpoint; on a refused token, gets a new one and tries once more.</summary>
    private async Task<string> QueryAsync(string body, string what, CancellationToken cancellationToken)
    {
        string? refused = null;
        for (var attempt = 0; attempt < 2; attempt++)
        {
            var token = await Token.GetAsync(refused, cancellationToken).ConfigureAwait(false);
            HttpRequestMessage Make()
            {
                var request = new HttpRequestMessage(HttpMethod.Post, BaseUrl + "games") { Content = new StringContent(body, Encoding.UTF8, "text/plain") };
                request.Headers.Add("Client-ID", _accounts.IgdbClientId);
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
                request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
                return request;
            }

            var (reply, kind) = await _http.SendAsync(Id, _gate, Make, Classify, what, cancellationToken).ConfigureAwait(false);
            if (kind != ReplyKind.TokenExpired)
            {
                return kind == ReplyKind.NotFound ? "[]" : reply.Text;
            }

            refused = token;
        }

        throw new ProviderException(Id, ProviderFailure.AuthFailed, "IGDB refused a fresh access token: check the IGDB client_id in secrets.toml");
    }

    private static Classification Classify(HttpReply reply) => reply.Status switch
    {
        401 => new Classification(ReplyKind.TokenExpired),
        403 => new Classification(ReplyKind.AuthFailed, "IGDB refused the client_id in secrets.toml"),
        400 => new Classification(ReplyKind.Rejected, "IGDB refused the query"),
        _ => ScraperHttp.ClassifyCommon(reply, "IGDB refused the credentials in secrets.toml"),
    };
}
