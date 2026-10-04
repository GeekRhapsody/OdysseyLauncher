using System.Collections.Concurrent;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Models;
using Launcher.Core.Platform;
using Launcher.Core.Scanning;

namespace Launcher.Core.Scraping;

/// <summary>A provider's state, for the settings screen and the console.</summary>
public enum ProviderState
{
    Ready,

    /// <summary>No credentials: skipped, never an error.</summary>
    MissingCredentials,

    /// <summary>Quota used up, closed, or credentials refused: resting until <see cref="ProviderStatus.Until"/> (null: until restart).</summary>
    Resting,
}

/// <param name="InOrder">Whether config's provider and fallback list names it.</param>
public sealed record ProviderStatus(string Id, string DisplayName, ProviderState State, string? Message, DateTimeOffset? Until, bool InOrder);

/// <summary>Something the user should know about a provider during a batch (skipped for want of credentials, or resting).</summary>
public sealed record ProviderNotice(string Provider, ProviderState State, string Message, DateTimeOffset? Until);

/// <summary>One game's scrape.</summary>
/// <param name="Status">'ok', 'partial', 'not_found', 'error', or 'skipped' (no provider could look it up; nothing written).</param>
/// <param name="Providers">The providers that found it, in order.</param>
/// <param name="Media">The media kinds saved.</param>
/// <param name="Log">Each provider tried, with its outcome.</param>
public sealed record ScrapeGameResult(
    GameKey Game,
    string Status,
    IReadOnlyList<string> Providers,
    IReadOnlyList<string> Media,
    IReadOnlyList<ProviderLog> Log)
{
    /// <summary>The provider each saved kind came from: only this result says, as the media folder doesn't (A4).</summary>
    public IReadOnlyDictionary<string, string> MediaSources { get; init; } = new Dictionary<string, string>();
}

/// <summary>A batch's outcome.</summary>
/// <param name="Paused">The service stopped (the app closed) before the batch finished: it resumes on the next start.</param>
public sealed record ScrapeBatchResult(
    long BatchId,
    string Kind,
    int Total,
    int Done,
    int Failed,
    bool Cancelled,
    bool Paused,
    IReadOnlyList<ProviderNotice> Notices);

/// <summary>The settings screen's "test connection" (M7), written for the user; never holds a credential.</summary>
public sealed record ConnectionTestResult(string Provider, bool Succeeded, string Message);

/// <summary>What "scrape all missing" would take on, counted before it starts (M7).</summary>
/// <param name="Systems">Each system with games to scrape, in config order.</param>
public sealed record MissingSummary(int Games, IReadOnlyList<(string SystemId, int Games)> Systems);

/// <summary>What "scrape this system" would take on, counted before it starts (M7), with each filter's games (2026-10-04).</summary>
/// <param name="Games">Every game of the system: each is scraped (matched ones fetched by id).</param>
/// <param name="Missing">Those never successfully scraped, or without a front cover.</param>
/// <param name="NoCover">Those without a front cover (<see cref="SystemScrapeFilter.NoCover"/>).</param>
/// <param name="NoScreenshot">Those without a screenshot (<see cref="SystemScrapeFilter.NoScreenshot"/>).</param>
/// <param name="NotRecent">Those not scraped within <see cref="ScrapeService.RecentScrape"/> (<see cref="SystemScrapeFilter.NotRecent"/>).</param>
public sealed record SystemScrapeCount(int Games, int Missing, int NoCover, int NoScreenshot, int NotRecent)
{
    /// <summary>How many games <paramref name="filter"/> takes on.</summary>
    public int Of(SystemScrapeFilter filter) => filter switch
    {
        SystemScrapeFilter.NoCover => NoCover,
        SystemScrapeFilter.NoScreenshot => NoScreenshot,
        SystemScrapeFilter.NotRecent => NotRecent,
        _ => Games,
    };
}

/// <summary>
/// Which of a system's games "scrape this system" takes on (2026-10-04). Whichever it is, a game's scrape downloads
/// only the media kinds it has no file for, and fetches a matched game by id.
/// </summary>
public enum SystemScrapeFilter
{
    /// <summary>Every game.</summary>
    All,

    /// <summary>Games without a front cover (any: scraped, the user's own or imported).</summary>
    NoCover,

    /// <summary>Games without a screenshot.</summary>
    NoScreenshot,

    /// <summary>Games never scraped, or last scraped (whatever the outcome) longer ago than <see cref="ScrapeService.RecentScrape"/>.</summary>
    NotRecent,
}

/// <summary>One search hit for a manual match.</summary>
/// <param name="Similarity">How close its name is to the search, 0 to 1 (<see cref="TitleMatcher.Similarity"/>).</param>
/// <param name="MatchedBy">How the game's file matched it, for a hit from the provider's ROM index (<see cref="MatchMethods.Filename"/> or <see cref="MatchMethods.Hash"/>); null for a title search's.</param>
public sealed record MatchCandidate(string ProviderGameId, string Name, string? Year, double Similarity, string? MatchedBy = null);

/// <summary>One provider's answer to a manual match search.</summary>
/// <param name="InOrder">Whether config's provider and fallback list names it; one that doesn't is still used for the game if the user chooses one of its results.</param>
/// <param name="Candidates">The file's own match first (<see cref="MatchCandidate.MatchedBy"/>), then the closest name; empty when nothing was found or it wasn't searched.</param>
/// <param name="Problem">Why it wasn't searched (no credentials, no id for the system, resting) or why the search failed, written for the user; null when it was searched.</param>
/// <param name="Current">The game's match on this provider now: the user's own, else the one found automatically; null when it has none.</param>
public sealed record ProviderMatches(
    string Provider,
    string DisplayName,
    bool InOrder,
    IReadOnlyList<MatchCandidate> Candidates,
    string? Problem,
    string? Current,
    bool CurrentIsManual);

/// <summary>Every provider's results for a manual match, in config order, then the providers config doesn't name.</summary>
/// <param name="Term">The name searched for.</param>
public sealed record MatchSearch(GameKey Game, string Term, IReadOnlyList<ProviderMatches> Providers);

/// <summary>What clearing a game removed.</summary>
/// <param name="KeptSharedArt">Media files another game also uses (by stem): their rows went, the files stay.</param>
public sealed record ClearResult(bool Found, int FilesDeleted, IReadOnlyList<string> KeptSharedArt);

public sealed class ScrapeProgressEventArgs(long batchId, string kind, int total, int done, int failed, GameKey? current) : EventArgs
{
    public long BatchId { get; } = batchId;

    public string Kind { get; } = kind;

    public int Total { get; } = total;

    public int Done { get; } = done;

    public int Failed { get; } = failed;

    /// <summary>The game being started; null when the event reports one finishing.</summary>
    public GameKey? Current { get; } = current;
}

public sealed class ScrapeGameEventArgs(long batchId, ScrapeGameResult result) : EventArgs
{
    public long BatchId { get; } = batchId;

    public ScrapeGameResult Result { get; } = result;
}

public sealed class ScrapeBatchEventArgs(ScrapeBatchResult result) : EventArgs
{
    public ScrapeBatchResult Result { get; } = result;
}

public sealed class ProviderNoticeEventArgs(ProviderNotice notice) : EventArgs
{
    public ProviderNotice Notice { get; } = notice;
}

/// <summary>What <see cref="ScrapeService"/> needs. Tests replace the HTTP handler, clock, delay and providers.</summary>
public sealed class ScrapeServiceOptions
{
    public required LibraryService Library { get; init; }

    public required IPlatformPaths Paths { get; init; }

    public required ProviderAccounts Accounts { get; init; }

    /// <summary>Null uses a real <c>SocketsHttpHandler</c>.</summary>
    public HttpMessageHandler? HttpHandler { get; init; }

    public TimeProvider Clock { get; init; } = TimeProvider.System;

    /// <summary>Null waits for real (<see cref="ScraperHttp.RealDelay"/>).</summary>
    public Delay? Delay { get; init; }

    public RetryPolicy Retry { get; init; } = RetryPolicy.Default;

    public ILog Log { get; init; } = NullLog.Instance;

    /// <summary>Null: no derivatives are baked (a platform without a decoder).</summary>
    public IImageDecoder? ImageDecoder { get; init; }

    /// <summary>Null builds the three real providers.</summary>
    public IReadOnlyList<IScraper>? Scrapers { get; init; }

    /// <summary>Games worked on at once, at most. Each provider still keeps to its own limit.</summary>
    public int MaxWorkers { get; init; } = 8;

    /// <summary>
    /// Saves each provider's response in <c>scraped/responses/</c> (credentials redacted), for debugging a scrape:
    /// off unless the app or <c>odyssey-scrape</c> is started with <c>--save-responses</c> (A4).
    /// </summary>
    public bool SaveResponses { get; init; }
}

/// <summary>
/// Scraping operations as services (M4), with progress events a UI can bind to. Every operation goes through a
/// persistent queue in userdata.db: a batch survives the app closing and <see cref="ResumeAsync"/> picks it up;
/// single games jump ahead of long batches. Games run concurrently, bounded by each provider's own limits; rate
/// limits and transient errors are retried with backoff (<see cref="ScraperHttp"/>).
/// <para>
/// Provider selection: <c>[scraping] provider</c> first, then each fallback in order, asked only for the fields and
/// media still missing and only if its capability map has them. Media is downloaded only for kinds the game has no
/// file for, and never replaces one (A4). A provider with no credentials is skipped and
/// reported (<see cref="ProviderNotice"/>), never an error. A manual match (userdata.db) beats a stored one, which
/// beats a search; scraping never writes the user's overrides.
/// </para>
/// Events are raised on worker threads.
/// </summary>
public sealed class ScrapeService : IDisposable
{
    /// <summary>
    /// The batch kind of a game scraped with the match the user chose (<see cref="ScrapeGameWithMatchAsync"/>): a game's
    /// scrape that runs even when no configured provider can, as the chosen one may be outside the configured order.
    /// </summary>
    public const string ManualKind = "manual";

    /// <summary>A game scraped within this long is skipped by <see cref="SystemScrapeFilter.NotRecent"/>.</summary>
    public static readonly TimeSpan RecentScrape = TimeSpan.FromDays(30);

    private readonly ScrapeServiceOptions _options;
    private readonly LibraryService _library;
    private readonly Dictionary<string, IScraper> _scrapers;
    private readonly HttpClient? _client;
    private readonly MediaStore _media;
    private readonly Redactor _redactor;
    private readonly ILog _log;
    private readonly TimeProvider _clock;
    private readonly CancellationTokenSource _lifetime = new();
    private readonly object _runLock = new();
    private readonly ConcurrentDictionary<long, TaskCompletionSource<ScrapeBatchResult>> _waiting = new();
    private readonly ConcurrentDictionary<long, CancellationTokenSource> _batchTokens = new();
    private readonly ConcurrentDictionary<long, ConcurrentQueue<ProviderNotice>> _notices = new();
    private readonly ConcurrentDictionary<string, ProviderNotice> _resting = new(StringComparer.Ordinal);
    private readonly HashSet<long> _startedBatches = [];
    private Task? _runner;
    private long _generation;
    private bool _disposed;

    public ScrapeService(ScrapeServiceOptions options)
    {
        _options = options ?? throw new ArgumentNullException(nameof(options));
        _library = options.Library;
        _clock = options.Clock;
        _redactor = new Redactor(options.Accounts.Values);
        _log = new RedactingLog(options.Log, _redactor);
        _media = new MediaStore(_library.DataDir);
        Derivatives = new DerivativeService(_library, options.Paths, options.ImageDecoder, _log);
        if (options.Scrapers is { } scrapers)
        {
            _scrapers = scrapers.ToDictionary(s => s.Id, StringComparer.Ordinal);
        }
        else
        {
            _client = ScraperHttp.CreateClient(options.HttpHandler);
            var http = new ScraperHttp(_client, _clock, options.Delay ?? ScraperHttp.RealDelay(_clock), options.Retry, _log);
            var settings = _library.Config.Settings.Scraping;
            var accountsFile = Path.Combine(options.Paths.ConfigDir, ProviderAccounts.FileName);
            var tokenFile = Path.Combine(_library.DataDir, "tokens", "igdb.json");
            _scrapers = new IScraper[]
            {
                new ScreenScraperScraper(http, options.Accounts, settings, _log, accountsFile),
                new IgdbScraper(http, options.Accounts, settings, _log, accountsFile, tokenFile),
                new SteamGridDbScraper(http, options.Accounts, _log, accountsFile),
                new SteamStoreScraper(http, settings, _log),
            }.ToDictionary(s => s.Id, StringComparer.Ordinal);
        }
    }

    public event EventHandler<ScrapeBatchEventArgs>? BatchStarted;

    public event EventHandler<ScrapeProgressEventArgs>? Progress;

    public event EventHandler<ScrapeGameEventArgs>? GameScraped;

    public event EventHandler<ScrapeBatchEventArgs>? BatchFinished;

    /// <summary>A provider was skipped (no credentials) or started resting (quota, closure, refused credentials).</summary>
    public event EventHandler<ProviderNoticeEventArgs>? ProviderNotice;

    public DerivativeService Derivatives { get; }

    /// <summary>The providers, by id.</summary>
    public IReadOnlyDictionary<string, IScraper> Scrapers => _scrapers;

    /// <summary>Every provider's state, in config order first.</summary>
    public IReadOnlyList<ProviderStatus> GetProviders()
    {
        var order = _library.Config.Settings.Scraping.ProviderOrder;
        return order.Concat(_scrapers.Keys).Distinct(StringComparer.Ordinal)
            .Where(_scrapers.ContainsKey)
            .Select(id =>
            {
                var scraper = _scrapers[id];
                if (scraper.Unavailable is { } missing)
                {
                    return new ProviderStatus(id, scraper.DisplayName, ProviderState.MissingCredentials, missing, null, order.Contains(id));
                }

                return IsResting(id, out var notice)
                    ? new ProviderStatus(id, scraper.DisplayName, ProviderState.Resting, notice.Message, notice.Until, order.Contains(id))
                    : new ProviderStatus(id, scraper.DisplayName, ProviderState.Ready, null, null, order.Contains(id));
            })
            .ToList();
    }

    /// <summary>How long a connection test waits, retries included, before it says the provider didn't answer.</summary>
    public static TimeSpan ConnectionTestTimeout { get; } = TimeSpan.FromSeconds(20);

    /// <summary>
    /// The settings screen's "test connection" (M7): one cheap request to <paramref name="providerId"/> with the
    /// credentials this service was built with. Never throws for a refusal or a network problem: the result says what
    /// happened. Refused credentials rest the provider, as they would during a batch, so build a new service once
    /// they're changed.
    /// </summary>
    public async Task<ConnectionTestResult> TestConnectionAsync(string providerId, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(providerId);
        if (!_scrapers.TryGetValue(providerId, out var scraper))
        {
            return new ConnectionTestResult(providerId, false, $"'{providerId}' isn't a provider.");
        }

        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, _lifetime.Token);
        timeout.CancelAfter(ConnectionTestTimeout);
        try
        {
            var message = await scraper.TestConnectionAsync(timeout.Token).ConfigureAwait(false);
            return new ConnectionTestResult(providerId, true, _redactor.Redact(message));
        }
        catch (ProviderException e)
        {
            return new ConnectionTestResult(providerId, false, _redactor.Redact(e.Message));
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return new ConnectionTestResult(providerId, false,
                $"{scraper.DisplayName} didn't answer within {ConnectionTestTimeout.TotalSeconds:0} seconds. Check the internet connection, then try again.");
        }
    }

    /// <summary>How many games <see cref="ScrapeAllMissingAsync"/> would scrape now, and in which systems.</summary>
    public Task<MissingSummary> CountMissingAsync(CancellationToken cancellationToken)
    {
        var config = _library.Config;
        return _library.ReadAsync(c =>
        {
            var games = ScrapeStore.MissingGames(c, config);
            var systems = new List<(string, int)>();
            foreach (var system in config.Systems)
            {
                var count = games.Count(g => g.SystemId == system.Id);
                if (count > 0)
                {
                    systems.Add((system.Id, count));
                }
            }

            return new MissingSummary(games.Count, systems);
        }, cancellationToken);
    }

    /// <summary>
    /// What <see cref="ScrapeSystemAsync"/> would take on (M7: the system options panel asks first): every game of the
    /// system, how many of them are "missing" (never successfully scraped, or without a front cover), and how many
    /// each <see cref="SystemScrapeFilter"/> takes on.
    /// </summary>
    public Task<SystemScrapeCount> CountSystemAsync(string systemId, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        var recentSince = RecentSince();
        return _library.ReadAsync(c => ScrapeStore.CountSystem(c, systemId, recentSince), cancellationToken);
    }

    /// <summary>Scrapes one game, ahead of any batch that's running.</summary>
    public Task<ScrapeBatchResult> ScrapeGameAsync(GameKey game, CancellationToken cancellationToken) =>
        RunBatchAsync("game", $"{game.SystemId}/{game.PathKey}", 0, _ => [game], cancellationToken);

    /// <summary>
    /// Manual matching (the game options' "scrape this game"): searches every provider at once for
    /// <paramref name="term"/> (null: the user's title for the game, else its file name's, without a disc number), so
    /// the user can choose the right game. The first search (a null term) also asks each provider's ROM index for the
    /// file itself, whose hit comes first: a title search can't find an arcade set by its MAME short name
    /// (<c>1on1gov</c>), but ScreenScraper's ROM index can. A typed term is a title search only, so it costs no more of
    /// ScreenScraper's quota. Each provider's results come with its current match. A provider
    /// that can't be searched (no credentials, no id for the system, resting) or whose search fails says why in its
    /// <see cref="ProviderMatches.Problem"/>; this never throws for a provider problem. Null when the game isn't in
    /// the library.
    /// </summary>
    public async Task<MatchSearch?> SearchMatchesAsync(GameKey game, string? term, CancellationToken cancellationToken)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        var context = await _library.ReadAsync(c => ScrapeStore.LoadContext(c, game), cancellationToken).ConfigureAwait(false);
        if (context is null || _library.Config.FindSystem(game.SystemId) is not { } system)
        {
            return null;
        }

        var search = term?.Trim() ?? TitleMatcher.SearchTerm(context.TitleOverride ?? context.FileTitle);
        var settings = _library.Config.Settings.Scraping;
        var order = settings.ProviderOrder;
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, _lifetime.Token);

        // The file's query, hashed as a scrape hashes it (once, then kept), shared by the providers.
        var file = term is null ? FileQueryAsync(context, system, settings, linked.Token) : null;
        var searches = order.Concat(ConfigLoader.Scrapers).Concat(_scrapers.Keys).Distinct(StringComparer.Ordinal)
            .Where(_scrapers.ContainsKey)
            .Select(id => SearchProviderAsync(_scrapers[id], order.Contains(id), context, system, search, file, linked.Token))
            .ToList();
        var providers = await Task.WhenAll(searches).ConfigureAwait(false);
        return new MatchSearch(game, search, providers);
    }

    /// <summary>
    /// Scrapes one game with the provider's game the user chose (a search result), ahead of any batch. The choice is
    /// saved as a manual match in userdata.db first, so it survives a rebuild and wins in every later scrape. A game's
    /// manual matches are asked first, the latest choice first, each fetched by its id; the other providers then fill
    /// in what they lack, as in any scrape. What the chosen provider had brought in before, and this scrape didn't
    /// bring again, goes (<see cref="ScrapeStore.SaveReplacing"/>), so a corrected match leaves nothing of the wrong
    /// game behind.
    /// </summary>
    public async Task<ScrapeBatchResult> ScrapeGameWithMatchAsync(GameKey game, string provider, string providerGameId, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(provider);
        ObjectDisposedException.ThrowIf(_disposed, this);
        if (!_scrapers.ContainsKey(provider))
        {
            throw new ArgumentException($"'{provider}' isn't a provider.", nameof(provider));
        }

        if (string.IsNullOrWhiteSpace(providerGameId))
        {
            throw new ArgumentException("A provider's game id can't be empty.", nameof(providerGameId));
        }

        var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
        await _library.WriteAsync(c =>
        {
            ScrapeStore.SaveManualMatch(c, game, provider, providerGameId, now);
            return true;
        }, cancellationToken).ConfigureAwait(false);
        return await RunBatchAsync(ManualKind, $"{game.SystemId}/{game.PathKey}", 0, _ => [game], cancellationToken).ConfigureAwait(false);
    }

    private async Task<ScrapeQuery> FileQueryAsync(GameContext context, SystemConfig system, ScrapingSettings settings, CancellationToken cancellationToken)
    {
        var hashes = await HashAsync(context, system, [ScraperIds.ScreenScraper], settings, cancellationToken).ConfigureAwait(false);
        return new ScrapeQuery(context.Key, system, Path.GetFileName(context.RelPath), TitleMatcher.SearchTerm(context.FileTitle),
            context.SizeBytes, hashes, new HashSet<string>(StringComparer.Ordinal));
    }

    private async Task<ProviderMatches> SearchProviderAsync(IScraper scraper, bool inOrder, GameContext context, SystemConfig system, string term,
        Task<ScrapeQuery>? file, CancellationToken cancellationToken)
    {
        var id = scraper.Id;
        var (current, manual) = context.ManualMatches.TryGetValue(id, out var own) ? (own, true)
            : context.StoredMatches.TryGetValue(id, out var stored) ? (stored.Id, false)
            : ((string?)null, false);
        ProviderMatches Answer(IReadOnlyList<MatchCandidate> candidates, string? problem) =>
            new(id, scraper.DisplayName, inOrder, candidates, problem, current, manual);

        if (scraper.Unavailable is { } missing)
        {
            return Answer([], missing);
        }

        if (scraper.Unsupported(system) is { } unsupported)
        {
            return Answer([], unsupported);
        }

        if (IsResting(id, out var resting))
        {
            return Answer([], resting.Message);
        }

        if (term.Length == 0 && file is null)
        {
            return Answer([], "Type a name to search for");
        }

        try
        {
            // The file's own match (the ROM index) first, then the title search's hits, closest name first.
            var identify = file is null ? Task.FromResult<ScrapeCandidate?>(null) : IdentifyAsync(scraper, file, cancellationToken);
            var hits = term.Length == 0 ? [] : await scraper.SearchAsync(term, system, cancellationToken).ConfigureAwait(false);
            var fileHit = await identify.ConfigureAwait(false);
            var candidates = hits
                .DistinctBy(h => h.ProviderGameId, StringComparer.Ordinal)
                .Where(h => h.ProviderGameId != fileHit?.ProviderGameId)
                .Select((h, index) => (Candidate: new MatchCandidate(h.ProviderGameId, h.Name, h.Year, TitleMatcher.Similarity(term, h.Name)), Index: index))
                .OrderByDescending(c => c.Candidate.Similarity)
                .ThenBy(c => c.Index)
                .Select(c => c.Candidate)
                .ToList();
            if (fileHit is not null)
            {
                candidates.Insert(0, new MatchCandidate(fileHit.ProviderGameId, fileHit.Name, fileHit.Year, TitleMatcher.Similarity(term, fileHit.Name), fileHit.Method ?? MatchMethods.Filename));
            }

            return Answer(candidates, null);
        }
        catch (ProviderException e)
        {
            Rest(e);
            return Answer([], _redactor.Redact(e.Message));
        }
    }

    private static async Task<ScrapeCandidate?> IdentifyAsync(IScraper scraper, Task<ScrapeQuery> file, CancellationToken cancellationToken)
    {
        var query = await file.ConfigureAwait(false);
        return await scraper.IdentifyFileAsync(query, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Scrapes a system's games, in grid order: every one, or those <paramref name="filter"/> picks. Matched games are
    /// fetched by id, not searched again.
    /// </summary>
    public Task<ScrapeBatchResult> ScrapeSystemAsync(string systemId, CancellationToken cancellationToken) =>
        ScrapeSystemAsync(systemId, SystemScrapeFilter.All, cancellationToken);

    /// <inheritdoc cref="ScrapeSystemAsync(string, CancellationToken)"/>
    public Task<ScrapeBatchResult> ScrapeSystemAsync(string systemId, SystemScrapeFilter filter, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        if (_library.Config.FindSystem(systemId) is null)
        {
            throw new ArgumentException($"'{systemId}' isn't an enabled system.", nameof(systemId));
        }

        var recentSince = RecentSince();
        return RunBatchAsync("system", systemId, 1, c => ScrapeStore.SystemGames(c, systemId, filter, recentSince), cancellationToken);
    }

    /// <summary>The unix ms from which a scrape counts as recent (<see cref="SystemScrapeFilter.NotRecent"/>).</summary>
    private long RecentSince() => (_clock.GetUtcNow() - RecentScrape).ToUnixTimeMilliseconds();

    /// <summary>Scrapes every game never successfully scraped, and every game with no front cover.</summary>
    public Task<ScrapeBatchResult> ScrapeAllMissingAsync(CancellationToken cancellationToken)
    {
        var config = _library.Config;
        return RunBatchAsync("missing", null, 1, c => ScrapeStore.MissingGames(c, config), cancellationToken);
    }

    /// <summary>
    /// Runs every batch the app didn't finish before it closed, and waits for them. Cancelling
    /// <paramref name="cancellationToken"/> stops waiting but leaves them queued.
    /// </summary>
    public async Task<IReadOnlyList<ScrapeBatchResult>> ResumeAsync(CancellationToken cancellationToken)
    {
        var batches = await GetUnfinishedBatchesAsync(cancellationToken).ConfigureAwait(false);
        var waits = batches.Select(b => Wait(b.BatchId)).ToList();
        if (waits.Count == 0)
        {
            return [];
        }

        StartRunner();
        var all = Task.WhenAll(waits);
        await all.WaitAsync(cancellationToken).ConfigureAwait(false);
        return await all.ConfigureAwait(false);
    }

    public Task<IReadOnlyList<ScrapeBatchInfo>> GetUnfinishedBatchesAsync(CancellationToken cancellationToken) =>
        _library.ReadAsync<IReadOnlyList<ScrapeBatchInfo>>(ScrapeStore.UnfinishedBatches, cancellationToken);

    /// <summary>Abandons a batch: its remaining games are dropped from the queue, and games in progress stop.</summary>
    public async Task CancelBatchAsync(long batchId)
    {
        if (_batchTokens.TryGetValue(batchId, out var token))
        {
            await token.CancelAsync().ConfigureAwait(false);
        }

        var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
        await _library.WriteAsync(c =>
        {
            ScrapeStore.CancelBatch(c, batchId, now);
            return true;
        }, CancellationToken.None).ConfigureAwait(false);
        await FinishBatchAsync(batchId).ConfigureAwait(false);
    }

    /// <summary>
    /// Clears a game's metadata: scraped fields, its media files (scraped or the user's own, its model included, but
    /// not a file another game also uses) and their derivatives (and the model's processed copy in the cache), saved
    /// responses, every match (manual ones too), and the title and metadata overrides. Its status goes back to never
    /// scraped. Favourite, play history, emulator and hidden stay.
    /// </summary>
    public async Task<ClearResult> ClearGameAsync(GameKey game, CancellationToken cancellationToken)
    {
        var cleared = await _library.WriteAsync(c => ScrapeStore.Clear(c, game), cancellationToken).ConfigureAwait(false);
        return await Task.Run(() =>
        {
            var deleted = 0;
            void Delete(string path)
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                    deleted++;
                }
            }

            foreach (var (kind, path, size, mtime) in cleared.Media)
            {
                if (size is { } s && mtime is { } m)
                {
                    Delete(Derivatives.PathFor(path, s, m));
                }

                if (!cleared.Shared.Contains(path))
                {
                    var file = _media.FullPath(path);
                    Delete(file);
                    if (kind == MediaKinds.Model)
                    {
                        // M6: the model's processed copy in the cache goes too.
                        new ModelCache(_options.Paths.CacheDir, null, null).Forget(file);
                    }
                }
            }

            // Files named after the game that no scan has indexed yet.
            if (cleared.RelPath is { } relPath)
            {
                foreach (var file in _media.FilesOf(game.SystemId, relPath))
                {
                    Delete(file);
                }
            }

            deleted += ScrapedResponses.Delete(_library.DataDir, game);
            if (cleared.Found)
            {
                _library.RaiseMediaChanged([game]);
            }

            return new ClearResult(cleared.Found, deleted, cleared.Shared);
        }, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Stops the queue (batches stay queued: <see cref="ResumeAsync"/> continues them) and waits up to 10 s. Not on the main thread.</summary>
    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        _lifetime.Cancel();
        Task? runner;
        lock (_runLock)
        {
            runner = _runner;
        }

        try
        {
            runner?.Wait(TimeSpan.FromSeconds(10));
        }
        catch (AggregateException)
        {
            // Stopping: the batches report Paused.
        }

        foreach (var waiting in _waiting.Values)
        {
            waiting.TrySetResult(new ScrapeBatchResult(0, string.Empty, 0, 0, 0, false, true, []));
        }

        Derivatives.Dispose();
        _client?.Dispose();
        _lifetime.Dispose();
    }

    // ---- The queue ---------------------------------------------------------------------------------

    private async Task<ScrapeBatchResult> RunBatchAsync(
        string kind, string? target, int priority, Func<Microsoft.Data.Sqlite.SqliteConnection, List<GameKey>> select, CancellationToken cancellationToken)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        var notices = SkippedNotices();

        // A game with a chosen match is scraped even if no configured provider can be: the chosen one may be outside the order.
        if (kind != ManualKind && !_library.Config.Settings.Scraping.ProviderOrder.Any(id => _scrapers.TryGetValue(id, out var s) && s.Unavailable is null))
        {
            // Nothing could be scraped: say why instead of failing every game.
            foreach (var notice in notices)
            {
                ProviderNotice?.Invoke(this, new ProviderNoticeEventArgs(notice));
            }

            return new ScrapeBatchResult(0, kind, 0, 0, 0, false, false, notices);
        }

        var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
        var batchId = await _library.WriteAsync(c =>
        {
            var games = select(c);
            return ScrapeStore.CreateBatch(c, kind, target, priority, games, now);
        }, cancellationToken).ConfigureAwait(false);

        var queue = _notices.GetOrAdd(batchId, _ => new ConcurrentQueue<ProviderNotice>());
        foreach (var notice in notices)
        {
            queue.Enqueue(notice);
        }

        var wait = Wait(batchId);
        StartRunner();
        using (cancellationToken.Register(() => _ = CancelBatchAsync(batchId)))
        {
            return await wait.ConfigureAwait(false);
        }
    }

    private Task<ScrapeBatchResult> Wait(long batchId) =>
        _waiting.GetOrAdd(batchId, _ => new TaskCompletionSource<ScrapeBatchResult>(TaskCreationOptions.RunContinuationsAsynchronously)).Task;

    private void StartRunner()
    {
        lock (_runLock)
        {
            _generation++;
            if (_runner is null && !_lifetime.IsCancellationRequested)
            {
                _runner = Task.Run(RunAsync);
            }
        }
    }

    private async Task RunAsync()
    {
        var token = _lifetime.Token;
        var running = new ConcurrentDictionary<(long, long), bool>();
        var exited = false;
        try
        {
            await PrepareProvidersAsync(token).ConfigureAwait(false);
            while (!token.IsCancellationRequested)
            {
                long generation;
                lock (_runLock)
                {
                    generation = _generation;
                }

                var workers = Workers();
                var jobs = await _library.ReadAsync(c => ScrapeStore.NextJobs(c, workers * 2, running.Keys.ToList()), token).ConfigureAwait(false);
                if (jobs.Count == 0)
                {
                    await FinishEmptyBatchesAsync().ConfigureAwait(false);
                    lock (_runLock)
                    {
                        if (generation == _generation)
                        {
                            _runner = null;
                            exited = true;
                            return;
                        }
                    }

                    continue;
                }

                await Parallel.ForEachAsync(jobs, new ParallelOptions { MaxDegreeOfParallelism = workers, CancellationToken = token }, async (job, jobToken) =>
                {
                    running[(job.BatchId, job.Seq)] = true;
                    try
                    {
                        await RunJobAsync(job).ConfigureAwait(false);
                    }
                    finally
                    {
                        running.TryRemove((job.BatchId, job.Seq), out _);
                    }
                }).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested)
        {
            // Paused: every unfinished job stays queued.
        }
        catch (Exception e)
        {
            // A bug, not a provider problem: say so to everyone waiting rather than leave them hanging.
            _log.Write(LogLevel.Error, "Scrape queue stopped: " + e.Message);
            foreach (var batchId in _waiting.Keys.ToList())
            {
                if (_waiting.TryRemove(batchId, out var waiting))
                {
                    waiting.TrySetException(e);
                }
            }
        }
        finally
        {
            if (!exited)
            {
                lock (_runLock)
                {
                    _runner = null;
                }
            }

            if (token.IsCancellationRequested)
            {
                foreach (var (batchId, waiting) in _waiting)
                {
                    var info = await _library.ReadAsync(c => ScrapeStore.GetBatch(c, batchId), CancellationToken.None).ConfigureAwait(false);
                    waiting.TrySetResult(Result(info, batchId, paused: true));
                }
            }
        }
    }

    private async Task RunJobAsync(QueuedJob job)
    {
        var lifetime = _lifetime.Token;
        var batchToken = _batchTokens.GetOrAdd(job.BatchId, _ => CancellationTokenSource.CreateLinkedTokenSource(lifetime));
        var token = batchToken.Token;
        if (token.IsCancellationRequested)
        {
            return;
        }

        await AnnounceBatchAsync(job.BatchId).ConfigureAwait(false);
        var before = await _library.ReadAsync(c => ScrapeStore.GetBatch(c, job.BatchId), token).ConfigureAwait(false);
        if (before is null || before.Finished)
        {
            return;
        }

        Progress?.Invoke(this, new ScrapeProgressEventArgs(job.BatchId, before.Kind, before.Total, before.Done, before.Failed, job.Game));
        ScrapeGameResult result;
        try
        {
            result = await ScrapeOneAsync(job.Game, token).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested)
        {
            // Paused (the job stays queued) or cancelled (the batch's jobs are gone).
            return;
        }
        catch (Exception e)
        {
            _log.Write(LogLevel.Error, $"Scrape of {job.Game.SystemId}/{job.Game.PathKey} failed: {e.Message}");
            result = new ScrapeGameResult(job.Game, "error", [], [], [new ProviderLog("-", "error", e.Message)]);
        }

        var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
        var batch = await _library.WriteAsync(c => ScrapeStore.CompleteJob(c, job, result.Status == "error", now), CancellationToken.None).ConfigureAwait(false);
        GameScraped?.Invoke(this, new ScrapeGameEventArgs(job.BatchId, result));
        if (batch is not null)
        {
            Progress?.Invoke(this, new ScrapeProgressEventArgs(batch.BatchId, batch.Kind, batch.Total, batch.Done, batch.Failed, null));
            if (batch.Finished)
            {
                await FinishBatchAsync(batch.BatchId).ConfigureAwait(false);
            }
        }
    }

    private async Task AnnounceBatchAsync(long batchId)
    {
        lock (_startedBatches)
        {
            if (!_startedBatches.Add(batchId))
            {
                return;
            }
        }

        var info = await _library.ReadAsync(c => ScrapeStore.GetBatch(c, batchId), CancellationToken.None).ConfigureAwait(false);
        var queue = _notices.GetOrAdd(batchId, _ => new ConcurrentQueue<ProviderNotice>());
        if (queue.IsEmpty)
        {
            // A resumed batch: work out what's skipped now.
            foreach (var notice in SkippedNotices())
            {
                queue.Enqueue(notice);
            }
        }

        foreach (var notice in queue)
        {
            ProviderNotice?.Invoke(this, new ProviderNoticeEventArgs(notice));
        }

        BatchStarted?.Invoke(this, new ScrapeBatchEventArgs(Result(info, batchId, paused: false)));
    }

    private async Task FinishEmptyBatchesAsync()
    {
        foreach (var batchId in _waiting.Keys.ToList())
        {
            var info = await _library.ReadAsync(c => ScrapeStore.GetBatch(c, batchId), CancellationToken.None).ConfigureAwait(false);
            if (info is null || info.Finished)
            {
                await FinishBatchAsync(batchId).ConfigureAwait(false);
            }
        }
    }

    private async Task FinishBatchAsync(long batchId)
    {
        var info = await _library.ReadAsync(c => ScrapeStore.GetBatch(c, batchId), CancellationToken.None).ConfigureAwait(false);
        var result = Result(info, batchId, paused: false);
        if (_waiting.TryRemove(batchId, out var waiting))
        {
            waiting.TrySetResult(result);
        }

        if (_batchTokens.TryRemove(batchId, out var token))
        {
            token.Dispose();
        }

        bool announced;
        lock (_startedBatches)
        {
            announced = _startedBatches.Remove(batchId);
        }

        _notices.TryRemove(batchId, out _);
        if (announced || result.Total == 0)
        {
            BatchFinished?.Invoke(this, new ScrapeBatchEventArgs(result));
        }

        await _library.WriteAsync(c =>
        {
            ScrapeStore.PruneFinished(c, 50);
            return true;
        }, CancellationToken.None).ConfigureAwait(false);
    }

    private ScrapeBatchResult Result(ScrapeBatchInfo? info, long batchId, bool paused)
    {
        var notices = _notices.TryGetValue(batchId, out var queue) ? queue.ToList() : [];
        return info is null
            ? new ScrapeBatchResult(batchId, string.Empty, 0, 0, 0, true, paused, notices)
            : new ScrapeBatchResult(batchId, info.Kind, info.Total, info.Done, info.Failed, info.Cancelled, paused && !info.Finished, notices);
    }

    private int Workers()
    {
        var most = 1;
        foreach (var id in _library.Config.Settings.Scraping.ProviderOrder)
        {
            if (_scrapers.TryGetValue(id, out var scraper) && scraper.Unavailable is null && !IsResting(id, out _))
            {
                most = Math.Max(most, scraper.MaxConcurrency);
            }
        }

        return Math.Clamp(most, 1, Math.Max(1, _options.MaxWorkers));
    }

    private async Task PrepareProvidersAsync(CancellationToken cancellationToken)
    {
        foreach (var id in _library.Config.Settings.Scraping.ProviderOrder)
        {
            if (!_scrapers.TryGetValue(id, out var scraper) || scraper.Unavailable is not null || IsResting(id, out _))
            {
                continue;
            }

            try
            {
                await scraper.PrepareAsync(cancellationToken).ConfigureAwait(false);
            }
            catch (ProviderException e)
            {
                Rest(e);
            }
            catch (Exception e) when (e is not OperationCanceledException)
            {
                _log.Write(LogLevel.Warning, $"{id}: couldn't prepare: {e.Message}");
            }
        }
    }

    private List<ProviderNotice> SkippedNotices()
    {
        var notices = new List<ProviderNotice>();
        foreach (var id in _library.Config.Settings.Scraping.ProviderOrder)
        {
            if (!_scrapers.TryGetValue(id, out var scraper))
            {
                continue;
            }

            if (scraper.Unavailable is { } missing)
            {
                notices.Add(new ProviderNotice(id, ProviderState.MissingCredentials, missing + ". Skipping it.", null));
            }
            else if (IsResting(id, out var resting))
            {
                notices.Add(resting);
            }
        }

        return notices;
    }

    private bool IsResting(string provider, out ProviderNotice notice)
    {
        if (_resting.TryGetValue(provider, out notice!))
        {
            if (notice.Until is null || notice.Until > _clock.GetUtcNow())
            {
                return true;
            }

            _resting.TryRemove(provider, out _);
        }

        return false;
    }

    private void Rest(ProviderException e)
    {
        if (e.Failure is not (ProviderFailure.QuotaExhausted or ProviderFailure.Closed or ProviderFailure.AuthFailed))
        {
            return;
        }

        var until = e.Failure == ProviderFailure.AuthFailed ? null : e.Until;
        var message = until is { } u
            ? $"{e.Message}. Resting until {u.ToLocalTime():yyyy-MM-dd HH:mm}; games get the other providers' data meanwhile"
            : $"{e.Message}. Left out until the launcher restarts";
        var notice = new ProviderNotice(e.Provider, ProviderState.Resting, message, until);
        if (_resting.TryAdd(e.Provider, notice))
        {
            _log.Write(LogLevel.Warning, $"{e.Provider}: {message}");
            foreach (var queue in _notices.Values)
            {
                queue.Enqueue(notice);
            }

            ProviderNotice?.Invoke(this, new ProviderNoticeEventArgs(notice));
        }
    }

    // ---- One game ----------------------------------------------------------------------------------

    private async Task<ScrapeGameResult> ScrapeOneAsync(GameKey key, CancellationToken cancellationToken)
    {
        var config = _library.Config;
        var settings = config.Settings.Scraping;
        var context = await _library.ReadAsync(c => ScrapeStore.LoadContext(c, key), cancellationToken).ConfigureAwait(false);
        var system = config.FindSystem(key.SystemId);
        if (context is null || system is null)
        {
            return new ScrapeGameResult(key, "skipped", [], [], [new ProviderLog("-", "skipped", "not in the library")]);
        }

        // The game's manual matches first, the latest choice first (the user chose those games), then the configured order.
        var order = context.ManualOrder.Concat(settings.ProviderOrder).Distinct(StringComparer.Ordinal).Where(_scrapers.ContainsKey).ToList();
        var hashes = await HashAsync(context, system, order, settings, cancellationToken).ConfigureAwait(false);

        // A kind the game has a file for, wherever it came from, isn't downloaded again (A4).
        var wanted = settings.Media.Where(k => !context.Media.ContainsKey(k)).ToHashSet(StringComparer.Ordinal);
        var merge = new ScrapeMerge(wanted);
        var query = new ScrapeQuery(key, system, Path.GetFileName(context.RelPath), TitleMatcher.SearchTerm(context.FileTitle),
            context.SizeBytes, hashes, wanted);

        var log = new List<ProviderLog>();
        var found = new List<string>();
        var matches = new Dictionary<string, (string Id, string Method)>(StringComparer.Ordinal);
        var responses = new Dictionary<string, (string Status, string? Response)>(StringComparer.Ordinal);
        var failed = false;
        var tried = false;

        // Providers whose manual match answered: what they'd brought in before is replaced (ScrapeStore.SaveReplacing).
        var replaced = new HashSet<string>(StringComparer.Ordinal);
        for (var i = 0; i < order.Count; i++)
        {
            var id = order[i];
            var scraper = _scrapers[id];
            context.ManualMatches.TryGetValue(id, out var manualMatch);
            if (scraper.Unavailable is not null || scraper.Unsupported(system) is not null)
            {
                continue;
            }

            if (IsResting(id, out var resting))
            {
                failed = true;
                log.Add(new ProviderLog(id, "error", resting.Message));
                continue;
            }

            if (i > 0 && !merge.CouldUse(scraper.Capabilities))
            {
                continue;
            }

            tried = true;
            var providerQuery = query with { WantedMedia = merge.MissingMedia() };
            try
            {
                ProviderResult result;
                string? method;
                if (manualMatch is not null)
                {
                    result = await scraper.FetchAsync(manualMatch, providerQuery, cancellationToken).ConfigureAwait(false);
                    method = MatchMethods.Manual;
                }
                else if (context.StoredMatches.TryGetValue(id, out var stored))
                {
                    result = await scraper.FetchAsync(stored.Id, providerQuery, cancellationToken).ConfigureAwait(false);
                    method = stored.Method;
                    if (!result.Found)
                    {
                        // The stored match has gone from the provider: find it again.
                        result = await scraper.LookupAsync(providerQuery, cancellationToken).ConfigureAwait(false);
                        method = result.Method;
                    }
                }
                else
                {
                    result = await scraper.LookupAsync(providerQuery, cancellationToken).ConfigureAwait(false);
                    method = result.Method;
                }

                if (result.Game is { } game)
                {
                    merge.Add(id, game, scraper.Capabilities);
                    found.Add(id);
                    matches[id] = (game.ProviderGameId, method ?? MatchMethods.Filename);
                    responses[id] = ("ok", result.Response);
                    log.Add(new ProviderLog(id, "ok", null));
                }
                else
                {
                    responses[id] = ("not_found", result.Response);
                    log.Add(new ProviderLog(id, "not_found", null));
                }

                if (manualMatch is not null)
                {
                    replaced.Add(id);
                }
            }
            catch (ProviderException e)
            {
                failed = true;
                log.Add(new ProviderLog(id, "error", e.Message));
                Rest(e);
            }
        }

        if (!tried)
        {
            return new ScrapeGameResult(key, "skipped", [], [], [new ProviderLog("-", "skipped", "no configured provider can look up this system's games")]);
        }

        // Media: each kind from the first provider whose download works.
        var saved = new List<(string Kind, StoredMedia Media)>();
        var sources = new Dictionary<string, string>(StringComparer.Ordinal);
        var savedBy = new Dictionary<string, List<SavedMedia>>(StringComparer.Ordinal);
        foreach (var (kind, candidates) in merge.MediaCandidates())
        {
            foreach (var (provider, media) in candidates)
            {
                if (IsResting(provider, out _))
                {
                    continue;
                }

                try
                {
                    var bytes = await _scrapers[provider].DownloadAsync(media, cancellationToken).ConfigureAwait(false);
                    // Null: a file of that kind turned up meanwhile (the user's own), and it stays.
                    if (await _media.SaveAsync(key.SystemId, context.RelPath, kind, bytes, cancellationToken).ConfigureAwait(false) is not { } stored)
                    {
                        break;
                    }

                    saved.Add((kind, stored));
                    sources[kind] = provider;
                    if (!savedBy.TryGetValue(provider, out var list))
                    {
                        savedBy[provider] = list = [];
                    }

                    list.Add(new SavedMedia(kind, stored.RelativePath, stored.Width, stored.Height));

                    // Any image can fill a theme's slot (M6), so each gets its derivative now.
                    if (MediaKinds.Images.Contains(kind))
                    {
                        await Derivatives.BakeAsync(stored.RelativePath, stored.SizeBytes, stored.MtimeMs, cancellationToken).ConfigureAwait(false);
                    }

                    break;
                }
                catch (ProviderException e)
                {
                    _log.Write(LogLevel.Warning, $"{provider}: {key.SystemId}/{key.PathKey}: {e.Message}");
                    Rest(e);
                }
                catch (InvalidDataException e)
                {
                    _log.Write(LogLevel.Warning, $"{provider}: {key.SystemId}/{key.PathKey}: {kind}: {e.Message}");
                }
            }
        }

        var status = found.Count > 0 ? (failed ? "partial" : "ok") : (failed ? "error" : "not_found");
        var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
        if (_options.SaveResponses)
        {
            await Task.Run(() =>
            {
                foreach (var (provider, (providerStatus, response)) in responses)
                {
                    matches.TryGetValue(provider, out var match);
                    ScrapedResponses.Save(_library.DataDir, new SavedScrape(
                        provider, key, providerStatus, match.Id, match.Method, now,
                        savedBy.TryGetValue(provider, out var media) ? media : [],
                        response is null ? null : _redactor.Redact(response)));
                }
            }, cancellationToken).ConfigureAwait(false);
        }

        var write = new ScrapeWrite(found.Count > 0 ? merge.Metadata() : null, matches, saved, log, status, found, now);
        if (replaced.Count > 0)
        {
            await _library.WriteAsync(c => ScrapeStore.SaveReplacing(c, key, write, replaced), cancellationToken).ConfigureAwait(false);
        }
        else
        {
            await _library.WriteAsync(c => ScrapeStore.Save(c, key, write), cancellationToken).ConfigureAwait(false);
        }

        if (saved.Count > 0)
        {
            _library.RaiseMediaChanged([key]);
        }

        return new ScrapeGameResult(key, status, found, saved.Select(s => s.Kind).ToList(), log) { MediaSources = sources };
    }

    /// <summary>ScreenScraper wants a hash: small files are hashed once, and the hashes kept in the library.</summary>
    private async Task<RomHashes?> HashAsync(GameContext context, SystemConfig system, List<string> order, ScrapingSettings settings, CancellationToken cancellationToken)
    {
        if (context.Hashes is not null || settings.HashLimitBytes <= 0 || context.SizeBytes > settings.HashLimitBytes
            || !RomHasher.IsHashable(context.RelPath)
            || !order.Contains(ScraperIds.ScreenScraper) || _scrapers[ScraperIds.ScreenScraper] is not { Unavailable: null } screenScraper
            || screenScraper.Unsupported(system) is not null)
        {
            return context.Hashes;
        }

        try
        {
            var hashes = await Task.Run(() => RomHasher.Compute(context.RomPath, cancellationToken), cancellationToken).ConfigureAwait(false);
            await _library.WriteAsync(c =>
            {
                ScrapeStore.SaveHashes(c, context.Key, context.SizeBytes, hashes);
                return true;
            }, cancellationToken).ConfigureAwait(false);
            return hashes;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            _log.Write(LogLevel.Warning, $"Couldn't hash {context.RelPath}: {e.Message}");
            return null;
        }
    }
}
