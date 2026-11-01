using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Media;

namespace Launcher.Core.Scraping;

/// <summary>
/// LaunchBox's Games DB (https://gamesdb.launchbox-app.com; ARCHITECTURE.md A5, "LaunchBox Games DB"): metadata, and
/// covers, backs, spines, screenshots, logos, fan art and cartridge or disc art, with no credentials. Games are looked
/// up offline in the local copy of LaunchBox's database (<see cref="LaunchBoxDatabase"/>), only among the system's
/// LaunchBox platforms (<c>launchbox_platforms</c> in systems.toml): by the file's name in LaunchBox's file list
/// (<c>Files.xml</c>, for WHDLoad and arcade sets named nothing like their games) or a MAME set's short name
/// (<c>Mame.xml</c>), else by title. Names and images are picked by ScreenScraper's region order (<c>[scraping]
/// regions</c>, then <see cref="ScreenScraperScraper.FallbackRegions"/>), LaunchBox's region names mapped to its codes.
/// Only images are downloaded, 4 at a time.
/// </summary>
public sealed partial class LaunchBoxScraper : IScraper
{
    public const string ImageBaseUrl = "https://images.launchbox-app.com/";

    /// <summary>The platform whose games <c>Mame.xml</c>'s short names are.</summary>
    public const string ArcadePlatform = "Arcade";

    /// <summary>How many hits a title search offers.</summary>
    private const int SearchLimit = 20;

    /// <summary>How long a provider with no copy of the database rests after the download failed.</summary>
    private static readonly TimeSpan DownloadRetry = TimeSpan.FromHours(1);

    /// <summary>
    /// LaunchBox's region names to ScreenScraper's region codes (<see cref="ScreenScraperScraper.KnownRegions"/>). A
    /// region with no code here (South America, Hong Kong) ranks after every wanted one; an image with no region ranks
    /// as World.
    /// </summary>
    private static readonly Dictionary<string, string> RegionCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        ["World"] = "wor", ["North America"] = "us", ["United States"] = "us", ["Canada"] = "ca", ["Europe"] = "eu",
        ["United Kingdom"] = "uk", ["Germany"] = "de", ["France"] = "fr", ["Spain"] = "sp", ["Italy"] = "it",
        ["The Netherlands"] = "nl", ["Sweden"] = "se", ["Finland"] = "fi", ["Norway"] = "no", ["Greece"] = "gr",
        ["Russia"] = "ru", ["Japan"] = "jp", ["Asia"] = "asi", ["China"] = "cn", ["Korea"] = "kr",
        ["Australia"] = "au", ["Oceania"] = "oce", ["Brazil"] = "br",
    };

    /// <summary>Each media kind's LaunchBox image types, most wanted first: the first type the game has wins, then its best region.</summary>
    private static readonly (string Kind, string[] Types)[] MediaTypes =
    [
        (MediaKinds.Cover, ["Box - Front", "Box - Front - Reconstructed", "Fanart - Box - Front"]),
        (MediaKinds.Back, ["Box - Back", "Box - Back - Reconstructed"]),
        (MediaKinds.Spine, ["Box - Spine"]),
        (MediaKinds.Screenshot, ["Screenshot - Gameplay", "Screenshot - Game Title"]),
        (MediaKinds.Logo, ["Clear Logo"]),
        (MediaKinds.Hero, ["Fanart - Background"]),
        (MediaKinds.Label, ["Cart - Front", "Disc"]),
    ];

    /// <summary>The image types the index keeps: the dump's others (flyers, banners, 3D boxes, ...) aren't used.</summary>
    public static IReadOnlySet<string> ImageTypes { get; } = new HashSet<string>(MediaTypes.SelectMany(m => m.Types), StringComparer.Ordinal);

    private readonly LaunchBoxDatabase _database;
    private readonly ScraperHttp _http;
    private readonly ScrapingSettings _settings;
    private readonly ILog _log;
    private readonly ProviderGate _site;
    private readonly ProviderGate _images;

    public LaunchBoxScraper(LaunchBoxDatabase database, ScraperHttp http, ScrapingSettings settings, ILog log)
    {
        ArgumentNullException.ThrowIfNull(database);
        ArgumentNullException.ThrowIfNull(http);
        _database = database;
        _http = http;
        _settings = settings;
        _log = log;
        _site = new ProviderGate(Id, 1, null, null, http.Clock, http.Delay);
        _images = new ProviderGate(Id + " images", 4, null, null, http.Clock, http.Delay);
    }

    public string Id => ScraperIds.LaunchBox;

    public string DisplayName => "LaunchBox Games DB";

    public ScraperCapabilities Capabilities => Supplies;

    /// <summary>What this provider can supply (its capability map). No video (LaunchBox links YouTube) and no manual.</summary>
    public static ScraperCapabilities Supplies { get; } = new(
        new HashSet<MetadataField>(Enum.GetValues<MetadataField>()),
        new HashSet<string>(MediaTypes.Select(m => m.Kind), StringComparer.Ordinal));

    public int MaxConcurrency => _images.MaxConcurrency;

    /// <summary>Always available: LaunchBox's database is a public download.</summary>
    public string? Unavailable => null;

    public string? Unsupported(SystemConfig system)
    {
        ArgumentNullException.ThrowIfNull(system);
        return system.LaunchBoxPlatforms is null or { Count: 0 } ? $"{system.Name} has no launchbox_platforms in systems.toml" : null;
    }

    /// <summary>
    /// Brings the local copy up to date when it's missing or a week old. A failed update keeps an old copy in use; with
    /// none, the provider rests for an hour and the batch carries on with the others.
    /// </summary>
    public async Task PrepareAsync(CancellationToken cancellationToken)
    {
        if (!_database.NeedsCheck)
        {
            return;
        }

        try
        {
            await _database.UpdateAsync(force: false, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception e) when (e is ProviderException || (e is OperationCanceledException && !cancellationToken.IsCancellationRequested))
        {
            if (!_database.IsReady)
            {
                throw Unreachable(e);
            }

            _log.Write(LogLevel.Warning, $"{Id}: couldn't update the database ({e.Message}); using the copy there is");
        }
    }

    public async Task<ProviderResult> LookupAsync(ScrapeQuery query, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(query);
        await ReadyAsync(cancellationToken).ConfigureAwait(false);
        if (query.System.LaunchBoxPlatforms is not { Count: > 0 } platforms)
        {
            return ProviderResult.NotFound;
        }

        var (id, method) = FindByFile(platforms, query.FileName) is { } byFile
            ? (byFile, MatchMethods.Filename)
            : (Best(platforms, TitleMatcher.SearchTerm(query.Title)), MatchMethods.Search);
        if (id is not { } found || _database.Load(found) is not { } response)
        {
            return ProviderResult.NotFound;
        }

        return Parse(response, _settings) is { } game ? new ProviderResult(game, method, response) : ProviderResult.NotFound;
    }

    public async Task<ProviderResult> FetchAsync(string providerGameId, ScrapeQuery query, CancellationToken cancellationToken)
    {
        await ReadyAsync(cancellationToken).ConfigureAwait(false);
        if (!long.TryParse(providerGameId, NumberStyles.None, CultureInfo.InvariantCulture, out var id) || _database.Load(id) is not { } response)
        {
            return ProviderResult.NotFound;
        }

        return Parse(response, _settings) is { } game ? new ProviderResult(game, null, response) : ProviderResult.NotFound;
    }

    /// <summary>A HEAD request for the dump (it needs no credentials), and the state of the local copy.</summary>
    public async Task<string> TestConnectionAsync(CancellationToken cancellationToken)
    {
        await _http.SendAsync(Id, _site, () => new HttpRequestMessage(HttpMethod.Head, LaunchBoxDatabase.DumpUrl), Classify,
            "connection test", cancellationToken).ConfigureAwait(false);
        return _database.Info is { } info
            ? string.Create(CultureInfo.InvariantCulture, $"LaunchBox's database is reachable. The local copy has {info.Games:N0} games{Published(info)}.")
            : "LaunchBox's database is reachable. It's downloaded (about 110 MB) the first time a scrape needs it.";
    }

    /// <summary>The game LaunchBox's file list or MAME list names the file as; null when neither knows it.</summary>
    public Task<ScrapeCandidate?> IdentifyFileAsync(ScrapeQuery query, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(query);
        if (!_database.IsReady || query.System.LaunchBoxPlatforms is not { Count: > 0 } platforms
            || FindByFile(platforms, query.FileName) is not { } id || _database.Load(id) is not { } response)
        {
            return Task.FromResult<ScrapeCandidate?>(null);
        }

        return Task.FromResult(Candidate(response, MatchMethods.Filename));
    }

    /// <summary>The hits carry their covers, so no request.</summary>
    public Task<ScrapedMedia?> SearchCoverAsync(ScrapeCandidate candidate, CancellationToken cancellationToken) =>
        Task.FromResult(candidate?.Cover);

    /// <summary>
    /// The games of the system's platforms whose names are closest to <paramref name="title"/>, a name that holds it as
    /// whole words counting as close. While the database is still to be downloaded, starts the download and says so.
    /// </summary>
    public Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(string title, SystemConfig system, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(title);
        ArgumentNullException.ThrowIfNull(system);
        if (!_database.IsReady)
        {
            _ = _database.UpdateAsync(force: false, CancellationToken.None).ContinueWith(
                t => _log.Write(LogLevel.Warning, $"{Id}: {t.Exception?.InnerException?.Message}"),
                CancellationToken.None, TaskContinuationOptions.OnlyOnFaulted, TaskScheduler.Default);
            throw new ProviderException(Id, ProviderFailure.Transient,
                "LaunchBox's database is downloading (about 110 MB, once): search again when it's done");
        }

        var term = TitleMatcher.Normalise(title);
        if (term.Length == 0 || system.LaunchBoxPlatforms is not { Count: > 0 } platforms)
        {
            return Task.FromResult<IReadOnlyList<ScrapeCandidate>>([]);
        }

        var best = new Dictionary<long, double>();
        foreach (var name in _database.Titles(platforms))
        {
            var score = SearchScore(term, name.Norm);
            if (score > 0.3 && (!best.TryGetValue(name.Id, out var previous) || score > previous))
            {
                best[name.Id] = score;
            }
        }

        var candidates = new List<ScrapeCandidate>();
        foreach (var (id, _) in best.OrderByDescending(b => b.Value).ThenBy(b => b.Key).Take(SearchLimit))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (_database.Load(id) is { } response && Candidate(response, null) is { } candidate)
            {
                candidates.Add(candidate);
            }
        }

        return Task.FromResult<IReadOnlyList<ScrapeCandidate>>(candidates);
    }

    public async Task<byte[]> DownloadAsync(ScrapedMedia media, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(media);
        if (!media.Url.StartsWith(ImageBaseUrl, StringComparison.Ordinal))
        {
            throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the image URL isn't on images.launchbox-app.com");
        }

        var (reply, kind) = await _http.SendAsync(Id, _images, () => new HttpRequestMessage(HttpMethod.Get, media.Url), Classify,
            media.Kind + " download", cancellationToken).ConfigureAwait(false);
        return kind == ReplyKind.NotFound
            ? throw new ProviderException(Id, ProviderFailure.Rejected, $"{media.Kind}: the image is gone")
            : reply.Body;
    }

    /// <summary>
    /// Reads a game as <see cref="LaunchBoxDatabase.Load"/> writes it (and a scrape saves it): its metadata, its name and
    /// its images in the most wanted region. Offline and pure.
    /// </summary>
    public static ScrapedGame? Parse(string response, ScrapingSettings settings)
    {
        ArgumentNullException.ThrowIfNull(response);
        ArgumentNullException.ThrowIfNull(settings);
        using var document = LenientJson.Parse(response);
        if (document?.RootElement is not { ValueKind: JsonValueKind.Object } game || game.Str("id") is not { } id)
        {
            return null;
        }

        var regions = ScreenScraperScraper.RegionOrder(settings);

        // The game's own name is its main one, ranked as World's; an alternate name in a region wanted before that wins.
        var title = game.Str("name");
        var titleRank = Rank(null, regions);
        foreach (var alternate in game.Arr("alternate_names"))
        {
            if (alternate.Str("region") is { } region && alternate.Str("name") is { } name && Rank(region, regions) is var rank && rank < titleRank)
            {
                (title, titleRank) = (name, rank);
            }
        }

        var images = game.Arr("images").ToList();
        var media = new List<ScrapedMedia>();
        foreach (var (kind, types) in MediaTypes)
        {
            foreach (var type in types)
            {
                if (PickImage(images, type, regions) is { } chosen)
                {
                    media.Add(new ScrapedMedia(kind, ImageUrl(chosen.Str("file")!), chosen.Str("region")));
                    break;
                }
            }
        }

        var players = game.Num("players") is { } most and >= 1
            ? most > 1 ? string.Create(CultureInfo.InvariantCulture, $"1-{(int)most}") : "1"
            : null;
        double? rating = game.Num("rating") is { } stars ? Math.Clamp(stars / 5.0, 0, 1) : null;
        var description = game.Str("overview")?.Trim();

        return new ScrapedGame(
            id,
            title,
            string.IsNullOrEmpty(description) ? null : description,
            game.Str("release") ?? game.Str("year"),
            List(game.Str("developer")),
            List(game.Str("publisher")),
            List(game.Str("genres")),
            players,
            rating,
            media);
    }

    /// <summary>LaunchBox's lists ("Action; Platform") as the other providers write them ("Action, Platform").</summary>
    private static string? List(string? text)
    {
        var items = text?.Split(';', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries).Distinct(StringComparer.Ordinal).ToList();
        return items is { Count: > 0 } ? string.Join(", ", items) : null;
    }

    /// <summary>Where a region comes in <paramref name="regions"/>; a region it lacks (or LaunchBox's with no code) after all of them; none as World.</summary>
    private static int Rank(string? region, string[] regions)
    {
        var code = region is null ? "wor" : RegionCodes.GetValueOrDefault(region);
        return code is not null && Array.IndexOf(regions, code) is var i and >= 0 ? i : regions.Length;
    }

    /// <summary>The game's image of <paramref name="type"/> in the best-ranked region, the first one breaking ties; null when it has none.</summary>
    private static JsonElement? PickImage(List<JsonElement> images, string type, string[] regions)
    {
        JsonElement? best = null;
        var bestRank = int.MaxValue;
        foreach (var image in images)
        {
            if (image.Str("type") != type || image.Str("file") is null)
            {
                continue;
            }

            var rank = Rank(image.Str("region"), regions);
            if (rank < bestRank)
            {
                (best, bestRank) = (image, rank);
            }
        }

        return best;
    }

    private static string ImageUrl(string file) => ImageBaseUrl + Uri.EscapeDataString(file);

    /// <summary>
    /// A file LaunchBox lists under another name: by its file list on the system's platforms, or, on Arcade, by MAME's
    /// short name. The name it gives is then looked up as a title, its tags dropped ("Pac-Man (Midway)" is Pac-Man).
    /// </summary>
    private long? FindByFile(IReadOnlyList<string> platforms, string fileName)
    {
        var stem = Path.GetFileNameWithoutExtension(fileName);
        if (stem.Length == 0)
        {
            return null;
        }

        if (_database.FindFile(platforms, stem) is { } listed && Best(platforms, Untagged(listed)) is { } byList)
        {
            return byList;
        }

        return platforms.Contains(ArcadePlatform, StringComparer.Ordinal) && _database.FindMame(stem) is { } mame
            ? Best(platforms, Untagged(mame))
            : null;
    }

    /// <summary>
    /// The game whose name (or, a little behind, an alternate name) is closest to <paramref name="title"/>, if close
    /// enough (<see cref="TitleMatcher.Threshold"/>); a name written exactly as the title, then the lowest id (the
    /// entry LaunchBox had first: the original, not a hack named like it), break ties.
    /// </summary>
    private long? Best(IReadOnlyList<string> platforms, string title)
    {
        var term = TitleMatcher.Normalise(title);
        if (term.Length == 0)
        {
            return null;
        }

        long? best = null;
        var bestScore = 0.0;
        foreach (var name in _database.Titles(platforms))
        {
            // An edit distance alone can't reach the threshold across this difference in length, and a missing
            // subtitle needs one name to start the other.
            var longest = Math.Max(term.Length, name.Norm.Length);
            if (Math.Abs(term.Length - name.Norm.Length) > (1 - TitleMatcher.Threshold) * longest
                && !name.Norm.StartsWith(term, StringComparison.Ordinal) && !term.StartsWith(name.Norm, StringComparison.Ordinal))
            {
                continue;
            }

            // Normalising makes "Chrono Trigger+" (a hack) the same as Chrono Trigger: the name as written breaks the tie.
            var score = TitleMatcher.SimilarityOfNormalised(term, name.Norm) - (name.Alternate ? 0.01 : 0)
                + (string.Equals(name.Name, title, StringComparison.OrdinalIgnoreCase) ? 0.001 : 0);
            if (score > bestScore)
            {
                (best, bestScore) = (name.Id, score);
            }
        }

        return bestScore >= TitleMatcher.Threshold ? best : null;
    }

    /// <summary>How well a name answers a typed search: its similarity, or better when it holds the search as whole words.</summary>
    private static double SearchScore(string term, string name)
    {
        var score = TitleMatcher.SimilarityOfNormalised(term, name);
        var words = name == term
            || name.StartsWith(term + " ", StringComparison.Ordinal)
            || name.EndsWith(" " + term, StringComparison.Ordinal)
            || name.Contains(" " + term + " ", StringComparison.Ordinal);
        return words ? Math.Max(score, 0.7 + (0.3 * term.Length / name.Length)) : score;
    }

    private ScrapeCandidate? Candidate(string response, string? method)
    {
        using var document = LenientJson.Parse(response);
        if (document?.RootElement is not { ValueKind: JsonValueKind.Object } game || game.Str("id") is not { } id || game.Str("name") is not { } name)
        {
            return null;
        }

        var year = game.Str("release")?[..4] ?? game.Str("year");
        var cover = Parse(response, _settings)?.MediaOrEmpty.FirstOrDefault(m => m.Kind == MediaKinds.Cover);
        return new ScrapeCandidate(id, name, year, method, cover);
    }

    /// <summary>Waits for the first download when there's no copy yet; with none after it, the provider rests.</summary>
    private async Task ReadyAsync(CancellationToken cancellationToken)
    {
        if (_database.IsReady)
        {
            return;
        }

        try
        {
            await _database.UpdateAsync(force: false, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception e) when (e is ProviderException || (e is OperationCanceledException && !cancellationToken.IsCancellationRequested))
        {
            throw Unreachable(e);
        }

        if (!_database.IsReady)
        {
            throw Unreachable(null);
        }
    }

    private ProviderException Unreachable(Exception? why) => new(Id, ProviderFailure.Closed,
        why is OperationCanceledException ? "LaunchBox's database download was stopped" : $"LaunchBox's database couldn't be downloaded{(why is null ? string.Empty : ": " + why.Message)}",
        _http.Clock.GetUtcNow() + DownloadRetry, why);

    private static string Published(LaunchBoxInfo info) =>
        info.Published is { } published ? ", published " + published.ToLocalTime().ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) : string.Empty;

    private static string Untagged(string name) => Tags().Replace(name, string.Empty).Trim();

    /// <summary>Trailing <c>(...)</c> and <c>[...]</c> groups: regions, versions, dump flags.</summary>
    [GeneratedRegex(@"(\s*[\(\[][^\)\]]*[\)\]])+\s*$", RegexOptions.CultureInvariant)]
    private static partial Regex Tags();

    /// <summary>The common mapping, except that a refusal isn't about credentials (there are none).</summary>
    private static Classification Classify(HttpReply reply) => reply.Status is 401 or 403
        ? new Classification(ReplyKind.Rejected, $"LaunchBox refused the request (HTTP {reply.Status})")
        : ScraperHttp.ClassifyCommon(reply, string.Empty);
}
