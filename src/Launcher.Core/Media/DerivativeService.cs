using System.Collections.Concurrent;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Platform;
using Launcher.Core.Scraping;

namespace Launcher.Core.Media;

/// <summary>What <see cref="DerivativeService.BakeMissingAsync"/> did.</summary>
/// <param name="Images">The indexed images of every kind (covers, backs, spines...), each file once.</param>
public sealed record BakeSummary(int Images, int Baked, int AlreadyBaked, int Failed, int Pruned, TimeSpan Elapsed);

/// <summary>
/// Bakes the grid's derivatives (A3) off the main thread: on its own worker threads at below-normal priority, so a
/// bake never competes with the render loop or holds a thread-pool thread for its ~0.2 s. Every image kind gets one,
/// since a theme's template can show any of them in a slot (M6). Scraping bakes each new image as it's saved;
/// <see cref="BakeMissingAsync"/> bakes every image in the library that has no derivative (one the user put there too),
/// and deletes derivatives nothing uses any more. A derivative's name includes its source's size and time, so a
/// changed source gets a new one.
/// </summary>
public sealed class DerivativeService : IDisposable
{
    private readonly LibraryService _library;
    private readonly IPlatformPaths _paths;
    private readonly DerivativeBaker? _baker;
    private readonly ILog _log;
    private readonly BlockingCollection<Action> _work = new();

    // Theme logos (A6): on screen the moment a theme with logos is first used, so they have threads of their own (made
    // then), which the library's threads help, taking them before any library image.
    private readonly BlockingCollection<Action> _urgent = new();
    private readonly Thread[] _threads;
    private readonly object _logoGate = new();
    private Thread[]? _logoThreads;

    /// <param name="decoder">Null where there's no decoder (Linux, for now): nothing is baked, and covers show as plain boxes.</param>
    /// <param name="workers">Bake threads. One by default: baking is background work.</param>
    public DerivativeService(LibraryService library, IPlatformPaths paths, IImageDecoder? decoder, ILog? log = null, int workers = 1)
    {
        _library = library ?? throw new ArgumentNullException(nameof(library));
        _paths = paths ?? throw new ArgumentNullException(nameof(paths));
        _baker = decoder is null ? null : new DerivativeBaker(decoder);
        _log = log ?? NullLog.Instance;
        _threads = new Thread[Math.Clamp(workers, 1, 4)];
        for (var i = 0; i < _threads.Length; i++)
        {
            _threads[i] = new Thread(Loop) { IsBackground = true, Name = "Derivative baker", Priority = ThreadPriority.BelowNormal };
            _threads[i].Start();
        }
    }

    /// <summary>False when this platform has no image decoder.</summary>
    public bool CanBake => _baker is not null;

    /// <summary>The derivative's path for a media row (its stored path, <c>media/...</c>).</summary>
    public string PathFor(string relPath, long sizeBytes, long mtimeMs) =>
        TextureDerivatives.PathFor(_paths.CacheDir, relPath, sizeBytes, mtimeMs);

    /// <summary>Bakes one derivative (unless it exists). False when it couldn't be (the reason is logged).</summary>
    public Task<bool> BakeAsync(string relPath, long sizeBytes, long mtimeMs, CancellationToken cancellationToken)
    {
        if (_baker is null)
        {
            return Task.FromResult(false);
        }

        var destination = PathFor(relPath, sizeBytes, mtimeMs);
        var source = _library.MediaPath(relPath);
        return Enqueue(source, destination, relPath, cancellationToken);
    }

    /// <summary>
    /// Bakes an image outside the library (a theme's logo, A6) to <paramref name="destination"/>, unless it exists, on
    /// below-normal logo threads (half the processors, at most 4, made on first use) that the library's thread helps,
    /// ahead of the library's images still waiting. False when it couldn't be (the reason is logged).
    /// </summary>
    public Task<bool> BakeFileAsync(string source, string destination, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(destination);
        if (_baker is null)
        {
            return Task.FromResult(false);
        }

        StartLogoThreads();
        return Enqueue(source, destination, source, cancellationToken, urgent: true);
    }

    private void StartLogoThreads()
    {
        lock (_logoGate)
        {
            if (_logoThreads is not null || _urgent.IsAddingCompleted)
            {
                return;
            }

            _logoThreads = new Thread[Math.Clamp(Environment.ProcessorCount / 2, 1, 4)];
            for (var i = 0; i < _logoThreads.Length; i++)
            {
                _logoThreads[i] = new Thread(() =>
                {
                    foreach (var job in _urgent.GetConsumingEnumerable())
                    {
                        job();
                    }
                })
                { IsBackground = true, Name = "Logo baker", Priority = ThreadPriority.BelowNormal };
                _logoThreads[i].Start();
            }
        }
    }

    private Task<bool> Enqueue(string source, string destination, string name, CancellationToken cancellationToken, bool urgent = false)
    {
        var baker = _baker!;
        var completion = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        (urgent ? _urgent : _work).Add(() =>
        {
            if (cancellationToken.IsCancellationRequested)
            {
                completion.TrySetCanceled(cancellationToken);
                return;
            }

            try
            {
                if (File.Exists(destination))
                {
                    completion.TrySetResult(true);
                    return;
                }

                var ok = baker.TryBake(source, destination, out var error);
                if (!ok)
                {
                    _log.Write(LogLevel.Warning, $"Derivative: couldn't bake '{name}': {error}");
                }

                completion.TrySetResult(ok);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                _log.Write(LogLevel.Warning, $"Derivative: couldn't bake '{name}': {e.Message}");
                completion.TrySetResult(false);
            }
        }, CancellationToken.None);
        return completion.Task;
    }

    /// <summary>
    /// Bakes every image in the library that has no derivative, then deletes the derivatives no image names (stale
    /// ones whose source changed or went). Safe to run while browsing: one below-normal thread by default. When any
    /// were baked, <see cref="LibraryService.MediaChanged"/> is raised for every game, so the grid can show them.
    /// </summary>
    public async Task<BakeSummary> BakeMissingAsync(IProgress<JobProgress>? progress, CancellationToken cancellationToken)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var images = await _library.ReadAsync(c => ScrapeStore.MediaOfKinds(c, MediaKinds.Images), cancellationToken).ConfigureAwait(false);
        var wanted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var missing = new List<(string Path, long Size, long Mtime)>();
        foreach (var image in images)
        {
            var path = PathFor(image.Path, image.SizeBytes, image.MtimeMs);
            if (wanted.Add(Path.GetFileName(path)) && !File.Exists(path))
            {
                missing.Add(image);
            }
        }

        int baked = 0, failed = 0, done = 0;
        progress?.Report(new JobProgress("bake", 0, missing.Count));
        if (_baker is not null)
        {
            var tasks = missing.Select(async m =>
            {
                var ok = await BakeAsync(m.Path, m.Size, m.Mtime, cancellationToken).ConfigureAwait(false);
                Interlocked.Increment(ref ok ? ref baked : ref failed);
                progress?.Report(new JobProgress("bake", Interlocked.Increment(ref done), missing.Count));
            }).ToList();
            await Task.WhenAll(tasks).ConfigureAwait(false);
        }

        var pruned = 0;
        var folder = Path.Combine(_paths.CacheDir, TextureDerivatives.FolderName);
        if (Directory.Exists(folder))
        {
            foreach (var file in Directory.EnumerateFiles(folder, "*" + TextureDerivatives.Extension))
            {
                if (!wanted.Contains(Path.GetFileName(file)))
                {
                    try
                    {
                        File.Delete(file);
                        pruned++;
                    }
                    catch (IOException)
                    {
                        // In use (the grid is reading it): the next run prunes it.
                    }
                }
            }
        }

        if (baked > 0)
        {
            _library.RaiseMediaChanged(null);
        }

        return new BakeSummary(images.Count, baked, images.Count - missing.Count, _baker is null ? missing.Count : failed, pruned, stopwatch.Elapsed);
    }

    public void Dispose()
    {
        lock (_logoGate)
        {
            _urgent.CompleteAdding();
        }

        _work.CompleteAdding();
        foreach (var thread in _threads.Concat(_logoThreads ?? []))
        {
            thread.Join();
        }

        _urgent.Dispose();
        _work.Dispose();
    }

    private void Loop()
    {
        // TryTakeFromAny takes from the first collection that has work: the urgent one first. -1 once both are done.
        BlockingCollection<Action>[] queues = [_urgent, _work];
        while (BlockingCollection<Action>.TryTakeFromAny(queues, out var job, Timeout.Infinite) >= 0)
        {
            job!();
        }
    }
}
