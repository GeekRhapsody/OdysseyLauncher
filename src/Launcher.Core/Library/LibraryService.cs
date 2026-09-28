using System.Diagnostics;
using System.Runtime.ExceptionServices;
using Launcher.Core.Config;
using Launcher.Core.Data;
using Launcher.Core.Scanning;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Library;

/// <summary>
/// <see cref="ILibrary"/> over <c>library.db</c> (with <c>userdata.db</c> ATTACHed as <c>user</c>).
/// Reads use pooled connections on the thread pool; writes run on one dedicated writer thread; scans and
/// rebuilds run one at a time.
/// </summary>
public sealed class LibraryService : ILibrary, IDisposable
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

    /// <summary>Why library.db was recreated, if it was.</summary>
    public string? RecreatedBecause { get; }

    /// <summary>How many systems are scanned at once (each on its own thread).</summary>
    public int ScanParallelism { get; set; } = DefaultScanParallelism;

    /// <summary>
    /// On a NAS, an unchanged rescan of 14 systems took 2.9 s one at a time, 1.5 s with 4 at once, and 1.4 s
    /// with 8 or 14 (docs/perf/m2-core.md). Local scans neither gain nor lose.
    /// </summary>
    public const int DefaultScanParallelism = 8;

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
            await service._writer.RunAsync(connection =>
            {
                LibraryStore.RekeyAliases(connection, config);
                return true;
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
            var caches = await _readers.RunAsync(
                c => systems.Select(s => LibraryStore.LoadPlaylists(c, s.Id)).ToList(), cancellationToken).ConfigureAwait(false);
            var scans = await Task.Run(() => Scan(systems, caches, progress, cancellationToken), cancellationToken).ConfigureAwait(false);
            var keepOnly = systemId is null ? config.Systems.Select(s => s.Id).ToHashSet(StringComparer.Ordinal) : null;
            var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
            var summaries = await _writer.RunAsync(c => LibraryStore.Apply(c, scans, keepOnly, now), cancellationToken).ConfigureAwait(false);
            return new ScanSummary(summaries, scans.SelectMany(s => s.Diagnostics).ToList(), stopwatch.Elapsed);
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
            var (scans, summaries) = await Task.Run(() =>
            {
                // Offline and from scratch: no playlist cache, nothing from the current library.
                Sqlite.DeleteFiles(rebuildPath);
                LibraryDatabase.Prepare(rebuildPath, out _);
                var scanned = Scan(config.Systems, null, progress, cancellationToken);
                using var connection = Sqlite.Open(rebuildPath);
                var written = LibraryStore.Apply(
                    connection, scanned, null, _clock.GetUtcNow().ToUnixTimeMilliseconds());

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
            return new ScanSummary(summaries, scans.SelectMany(s => s.Diagnostics).ToList(), stopwatch.Elapsed);
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
    private List<SystemScan> Scan(
        IReadOnlyList<SystemConfig> systems,
        IReadOnlyList<Dictionary<string, PlaylistEntry>>? caches,
        IProgress<JobProgress>? progress,
        CancellationToken cancellationToken)
    {
        var count = systems.Count;
        var results = new SystemScan[count];
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
                    results[i] = _scanner.Scan(systems[i], caches?[i], cancellationToken);
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

        return [.. results];
    }
}
