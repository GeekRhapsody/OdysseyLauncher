using System.Diagnostics;
using System.Runtime.ExceptionServices;
using Launcher.Core.Config;
using Launcher.Core.Data;
using Launcher.Core.Media;
using Launcher.Core.Scanning;
using Launcher.Core.Scraping;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Library;

/// <summary>
/// <see cref="ILibrary"/> over <c>library.db</c> (with <c>userdata.db</c> ATTACHed as <c>user</c>).
/// Reads use pooled connections on the thread pool; writes run on one dedicated writer thread; scans and
/// rebuilds run one at a time.
/// </summary>
public sealed class LibraryService : ILibrary, IPlayHistory, IDisposable
{
    public const string LibraryFileName = "library.db";
    public const string UserDataFileName = "userdata.db";

    private readonly string _libraryPath;
    private readonly string _userPath;
    private readonly TimeProvider _clock;
    private readonly RomScanner _scanner = new();
    private readonly SemaphoreSlim _jobLock = new(1, 1);
    private readonly DbWriter _writer;
    private readonly ReaderPool _readers;
    private AppConfig _config;

    private LibraryService(AppConfig config, string dataDir, TimeProvider clock, LibraryOpenOutcome outcome, string? reason)
    {
        _config = config;
        _clock = clock;
        DataDir = dataDir;
        _libraryPath = Path.Combine(dataDir, LibraryFileName);
        _userPath = Path.Combine(dataDir, UserDataFileName);
        OpenOutcome = outcome;
        RecreatedBecause = reason;
        _writer = new DbWriter(() => Sqlite.Open(_libraryPath, attachUserData: _userPath), "Library writer");
        _readers = new ReaderPool(() => Sqlite.Open(_libraryPath, queryOnly: true, attachUserData: _userPath));
    }

    /// <summary>
    /// <see cref="LibraryOpenOutcome.Created"/> or <see cref="LibraryOpenOutcome.Recreated"/> mean the library is
    /// empty: run <see cref="RescanAsync"/> for every system.
    /// </summary>
    public LibraryOpenOutcome OpenOutcome { get; }

    /// <summary>library.db, userdata.db and scraped/ live here.</summary>
    public string DataDir { get; }

    /// <summary>Why library.db was recreated, if it was.</summary>
    public string? RecreatedBecause { get; }

    /// <summary>Play sessions a crashed launcher left open, which opening the library closed.</summary>
    public int ClosedOrphanSessions { get; private set; }

    /// <summary>How many systems are scanned at once (each on its own thread).</summary>
    public int ScanParallelism { get; set; } = DefaultScanParallelism;

    /// <summary>
    /// On a NAS, an unchanged rescan of 14 systems took 2.9 s one at a time, 1.5 s with 4 at once, and 1.4 s
    /// with 8 or 14 (docs/perf/m2-core.md). Local scans neither gain nor lose.
    /// </summary>
    public const int DefaultScanParallelism = 8;

    /// <summary>
    /// The user's ConfigDir, whose <c>media/&lt;system&gt;/&lt;kind&gt;/</c> art and <c>models/games/&lt;system&gt;/</c>
    /// models scans index (source <c>user</c>). Null indexes none and leaves existing rows alone. Set it before scanning.
    /// </summary>
    public string? ConfigDir { get; set; }

    /// <summary>
    /// A game's media rows changed: a rescan indexed new or changed user art or models, a scrape saved media, a game
    /// was cleared, or derivatives were baked (M6). Raised on a worker thread after the change is committed, so the
    /// grid can rebind the games it shows without reloading their models.
    /// </summary>
    public event EventHandler<MediaChangedEventArgs>? MediaChanged;

    internal void RaiseMediaChanged(IReadOnlyList<GameKey>? games) => MediaChanged?.Invoke(this, new MediaChangedEventArgs(games));

    /// <summary>Config for the next query or scan. Takes effect at once; rescan to apply new ROM folders.</summary>
    public AppConfig Config
    {
        get => Volatile.Read(ref _config);
        set => Volatile.Write(ref _config, value ?? throw new ArgumentNullException(nameof(value)));
    }

    /// <summary>
    /// Prepares both databases in <paramref name="dataDir"/> (creating, migrating, backing up) on the thread
    /// pool, and opens the library.
    /// </summary>
    /// <exception cref="DatabaseTooNewException">userdata.db is newer than this build. It's left untouched.</exception>
    public static async Task<LibraryService> OpenAsync(
        AppConfig config, string dataDir, TimeProvider? clock, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(config);
        ArgumentNullException.ThrowIfNull(dataDir);
        var time = clock ?? TimeProvider.System;
        var (outcome, reason) = await Task.Run(() =>
        {
            Directory.CreateDirectory(dataDir);
            UserDatabase.Prepare(Path.Combine(dataDir, UserDataFileName), time);
            var result = LibraryDatabase.Prepare(Path.Combine(dataDir, LibraryFileName), out var why);
            return (result, why);
        }, cancellationToken).ConfigureAwait(false);

        var service = new LibraryService(config, dataDir, time, outcome, reason);
        try
        {
            service.ClosedOrphanSessions = await service._writer.RunAsync(connection =>
            {
                LibraryStore.RekeyAliases(connection, config);
                return LibraryStore.CloseOrphanedSessions(connection);
            }, cancellationToken).ConfigureAwait(false);
        }
        catch
        {
            service.Dispose();
            throw;
        }

        return service;
    }

    public Task<IReadOnlyList<SystemSummary>> GetSystemsAsync(CancellationToken cancellationToken)
    {
        var config = Config;
        return _readers.RunAsync<IReadOnlyList<SystemSummary>>(c => LibraryStore.GetSystems(c, config), cancellationToken);
    }

    public Task<GameList> GetGamesAsync(string systemId, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        return _readers.RunAsync(c => new GameList(systemId, LibraryStore.GetGames(c, systemId, 256)), cancellationToken);
    }

    public Task<IReadOnlyList<GameMediaRow>> GetGameMediaAsync(string systemId, IReadOnlyList<string> kinds, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        ArgumentNullException.ThrowIfNull(kinds);
        return kinds.Count == 0
            ? Task.FromResult<IReadOnlyList<GameMediaRow>>([])
            : _readers.RunAsync<IReadOnlyList<GameMediaRow>>(c => LibraryStore.GetGameMedia(c, systemId, kinds), cancellationToken);
    }

    public Task<IReadOnlyList<GameMediaRow>> GetGameMediaAsync(IReadOnlyList<long> gameIds, IReadOnlyList<string> kinds, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(gameIds);
        ArgumentNullException.ThrowIfNull(kinds);
        return kinds.Count == 0 || gameIds.Count == 0
            ? Task.FromResult<IReadOnlyList<GameMediaRow>>([])
            : _readers.RunAsync<IReadOnlyList<GameMediaRow>>(c => LibraryStore.GetGameMedia(c, gameIds, kinds), cancellationToken);
    }

    public Task<IReadOnlyList<VirtualGameRow>> GetFavouritesAsync(CancellationToken cancellationToken)
    {
        var config = Config;
        return _readers.RunAsync<IReadOnlyList<VirtualGameRow>>(c => LibraryStore.GetFavourites(c, config), cancellationToken);
    }

    public Task<IReadOnlyList<VirtualGameRow>> GetRecentlyPlayedAsync(int limit, CancellationToken cancellationToken)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(limit);
        var config = Config;
        return _readers.RunAsync<IReadOnlyList<VirtualGameRow>>(c => LibraryStore.GetRecentlyPlayed(c, limit, config), cancellationToken);
    }

    public Task<GameDetails?> GetGameAsync(long gameId, CancellationToken cancellationToken) =>
        _readers.RunAsync(c => LibraryStore.GetGame(c, gameId), cancellationToken);

    public Task<GameDetails?> GetGameAsync(GameKey game, CancellationToken cancellationToken) =>
        _readers.RunAsync(c => LibraryStore.GetGame(c, game), cancellationToken);

    public Task SetEmulatorOverrideAsync(GameKey game, string? emulatorId, CancellationToken cancellationToken)
    {
        var id = string.IsNullOrWhiteSpace(emulatorId) ? null : emulatorId.Trim();
        return _writer.RunAsync(c =>
        {
            LibraryStore.SetEmulatorOverride(c, game, id);
            return true;
        }, cancellationToken);
    }

    public Task<long> BeginSessionAsync(GameKey game, string emulatorId, DateTimeOffset startedAt, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(emulatorId);
        var started = startedAt.ToUnixTimeMilliseconds();
        return _writer.RunAsync(c => LibraryStore.BeginSession(c, game, emulatorId, started), cancellationToken);
    }

    public Task EndSessionAsync(PlaySessionEnd end, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(end);
        return _writer.RunAsync(c =>
        {
            LibraryStore.EndSession(c, end);
            return true;
        }, cancellationToken);
    }

    public Task<PlayStats?> GetPlayStatsAsync(GameKey game, CancellationToken cancellationToken) =>
        _readers.RunAsync(c => LibraryStore.GetPlayStats(c, game), cancellationToken);

    public Task SetFavouriteAsync(GameKey game, bool favourite, CancellationToken cancellationToken)
    {
        var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
        return _writer.RunAsync(c =>
        {
            LibraryStore.SetFavourite(c, game, favourite, now);
            return true;
        }, cancellationToken);
    }

    public Task SetTitleOverrideAsync(GameKey game, string? title, CancellationToken cancellationToken)
    {
        var trimmed = string.IsNullOrWhiteSpace(title) ? null : title.Trim();
        return _writer.RunAsync(c =>
        {
            LibraryStore.SetTitleOverride(c, game, trimmed);
            return true;
        }, cancellationToken);
    }

    public Task SetMetadataOverrideAsync(GameKey game, MetadataOverride values, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(values);
        static string? Clean(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
        var cleaned = new MetadataOverride(
            Clean(values.Description), Clean(values.ReleaseDate), Clean(values.Developer), Clean(values.Publisher),
            Clean(values.Genre), Clean(values.Players), values.Rating is { } r ? Math.Clamp(r, 0, 1) : null);
        return _writer.RunAsync(c =>
        {
            LibraryStore.SetMetadataOverride(c, game, cleaned);
            return true;
        }, cancellationToken);
    }

    /// <summary>A read on a pooled connection on the thread pool (the scraping services' queries).</summary>
    internal Task<T> ReadAsync<T>(Func<SqliteConnection, T> work, CancellationToken cancellationToken) =>
        _readers.RunAsync(work, cancellationToken);

    /// <summary>A job on the writer thread (the scraping services' writes).</summary>
    internal Task<T> WriteAsync<T>(Func<SqliteConnection, T> work, CancellationToken cancellationToken) =>
        _writer.RunAsync(work, cancellationToken);

    public Task SetHiddenAsync(GameKey game, bool hidden, CancellationToken cancellationToken) =>
        _writer.RunAsync(c =>
        {
            LibraryStore.SetHidden(c, game, hidden);
            return true;
        }, cancellationToken);

    public async Task<ScanSummary> RescanAsync(
        string? systemId, IProgress<JobProgress>? progress, CancellationToken cancellationToken)
    {
        var config = Config;
        IReadOnlyList<SystemConfig> systems;
        if (systemId is null)
        {
            systems = config.Systems;
        }
        else
        {
            var system = config.FindSystem(systemId)
                ?? throw new ArgumentException($"'{systemId}' isn't an enabled system.", nameof(systemId));
            systems = [system];
        }

        await _jobLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var stopwatch = Stopwatch.StartNew();
            var configDir = ConfigDir;
            var caches = await _readers.RunAsync(
                c => systems.Select(s => new ScanCache(
                    LibraryStore.LoadPlaylists(c, s.Id), configDir is null ? null : LibraryStore.LoadUserMedia(c, s.Id))).ToList(),
                cancellationToken).ConfigureAwait(false);
            var scans = await Task.Run(() => Scan(systems, caches, configDir, progress, cancellationToken), cancellationToken).ConfigureAwait(false);
            var keepOnly = systemId is null ? config.Systems.Select(s => s.Id).ToHashSet(StringComparer.Ordinal) : null;
            var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
            var mediaChanged = new List<GameKey>();
            var summaries = await _writer.RunAsync(
                c =>
                {
                    var added = new List<GameKey>();
                    var written = LibraryStore.Apply(c, scans.Roms, scans.Media, keepOnly, now, added, mediaChanged);

                    // Games that are new to the library get their scraped data back from scraped/responses/ (M4).
                    ScrapedRestore.Apply(c, DataDir, config, added);
                    return written;
                }, cancellationToken).ConfigureAwait(false);
            if (mediaChanged.Count > 0)
            {
                RaiseMediaChanged(mediaChanged);
            }

            return new ScanSummary(summaries, scans.Diagnostics(), stopwatch.Elapsed);
        }
        finally
        {
            _jobLock.Release();
        }
    }

    /// <summary>
    /// Indexes one system's user art and per-game models again, without scanning its ROM folders (the import service,
    /// after it writes or removes a model), and raises <see cref="MediaChanged"/> for the games whose rows changed.
    /// Needs <see cref="ConfigDir"/>. Returns those games.
    /// </summary>
    public async Task<IReadOnlyList<GameKey>> RefreshUserMediaAsync(string systemId, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        var configDir = ConfigDir ?? throw new InvalidOperationException("ConfigDir isn't set, so there's no user media to index.");
        await _jobLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var cache = await _readers.RunAsync(c => LibraryStore.LoadUserMedia(c, systemId), cancellationToken).ConfigureAwait(false);
            var scan = await Task.Run(() => UserMedia.Scan(configDir, systemId, cache, cancellationToken), cancellationToken).ConfigureAwait(false);
            var changed = await _writer.RunAsync(c =>
            {
                var games = new List<GameKey>();
                LibraryStore.ApplyUserMediaOnly(c, systemId, scan, games);
                return games;
            }, cancellationToken).ConfigureAwait(false);
            if (changed.Count > 0)
            {
                RaiseMediaChanged(changed);
            }

            return changed;
        }
        finally
        {
            _jobLock.Release();
        }
    }

    public async Task<ScanSummary> RebuildAsync(IProgress<JobProgress>? progress, CancellationToken cancellationToken)
    {
        var config = Config;
        await _jobLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var stopwatch = Stopwatch.StartNew();
            var rebuildPath = _libraryPath + ".rebuild";
            var configDir = ConfigDir;
            var (scans, summaries) = await Task.Run(() =>
            {
                // Offline and from scratch: no playlist or header cache, nothing from the current library.
                Sqlite.DeleteFiles(rebuildPath);
                LibraryDatabase.Prepare(rebuildPath, out _);
                var scanned = Scan(config.Systems, null, configDir, progress, cancellationToken);
                using var connection = Sqlite.Open(rebuildPath);
                var added = new List<GameKey>();
                var written = LibraryStore.Apply(
                    connection, scanned.Roms, scanned.Media, null, _clock.GetUtcNow().ToUnixTimeMilliseconds(), added);

                // Scraped metadata, matches and media links come back from scraped/responses/, offline (M4).
                ScrapedRestore.Apply(connection, DataDir, config, added);

                // Leave a single self-contained file behind, with no -wal to carry over.
                MigrationRunner.Execute(connection, "PRAGMA journal_mode = DELETE");
                return (scanned, written);
            }, cancellationToken).ConfigureAwait(false);

            progress?.Report(new JobProgress("swap", 0, 1));
            await _writer.RunDisconnectedAsync(
                () => _readers.Exclusive(() =>
                {
                    SqliteConnection.ClearAllPools();
                    File.Delete(_libraryPath + "-wal");
                    File.Delete(_libraryPath + "-shm");
                    File.Move(rebuildPath, _libraryPath, overwrite: true);
                }),
                CancellationToken.None).ConfigureAwait(false);
            progress?.Report(new JobProgress("swap", 1, 1));
            RaiseMediaChanged(null);
            return new ScanSummary(summaries, scans.Diagnostics(), stopwatch.Elapsed);
        }
        finally
        {
            _jobLock.Release();
        }
    }

    public void Dispose()
    {
        _writer.Dispose();
        _readers.Dispose();
        _jobLock.Dispose();
    }

    /// <summary>
    /// Scans systems in parallel on dedicated threads. Scanning is latency-bound on network shares (every
    /// listing refill is a round trip), and blocking that many thread-pool threads would starve the pool.
    /// Results keep config order, so the writes and diagnostics don't depend on timing.
    /// </summary>
    private ScanResults Scan(
        IReadOnlyList<SystemConfig> systems,
        IReadOnlyList<ScanCache>? caches,
        string? configDir,
        IProgress<JobProgress>? progress,
        CancellationToken cancellationToken)
    {
        var count = systems.Count;
        var results = new SystemScan[count];
        var media = new UserMediaScan?[count];
        var next = -1;
        var done = 0;
        Exception? failure = null;
        progress?.Report(new JobProgress("scan", 0, count));

        void Work()
        {
            while (Volatile.Read(ref failure) is null)
            {
                var i = Interlocked.Increment(ref next);
                if (i >= count)
                {
                    return;
                }

                try
                {
                    results[i] = _scanner.Scan(systems[i], caches?[i].Playlists, cancellationToken);
                    if (configDir is not null)
                    {
                        media[i] = UserMedia.Scan(configDir, systems[i].Id, caches?[i].UserMedia, cancellationToken);
                    }

                    progress?.Report(new JobProgress("scan", Interlocked.Increment(ref done), count));
                }
                catch (Exception e)
                {
                    Interlocked.CompareExchange(ref failure, e, null);
                }
            }
        }

        var threads = new Thread[Math.Clamp(ScanParallelism, 1, Math.Max(count, 1))];
        for (var t = 0; t < threads.Length; t++)
        {
            threads[t] = new Thread(Work) { IsBackground = true, Name = "ROM scan" };
            threads[t].Start();
        }

        foreach (var thread in threads)
        {
            thread.Join();
        }

        if (failure is not null)
        {
            ExceptionDispatchInfo.Throw(failure);
        }

        return new ScanResults(results, media);
    }

    /// <summary>What the previous scan left in the library, so unchanged playlists and images aren't read again.</summary>
    private sealed record ScanCache(Dictionary<string, PlaylistEntry> Playlists, Dictionary<string, UserMediaEntry>? UserMedia);

    /// <summary>Per system, in config order: the ROM scan and the user art found (null when art isn't indexed).</summary>
    private sealed record ScanResults(IReadOnlyList<SystemScan> Roms, IReadOnlyList<UserMediaScan?> Media)
    {
        public List<Diagnostic> Diagnostics()
        {
            var diagnostics = new List<Diagnostic>();
            for (var i = 0; i < Roms.Count; i++)
            {
                diagnostics.AddRange(Roms[i].Diagnostics);
                if (Media[i] is { } media)
                {
                    diagnostics.AddRange(media.Diagnostics);
                }
            }

            return diagnostics;
        }
    }
}
