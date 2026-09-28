using System.Collections.Concurrent;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Platform;
using Launcher.Core.Scraping;

namespace Launcher.Core.Media;

/// <summary>What <see cref="DerivativeService.BakeMissingAsync"/> did.</summary>
public sealed record BakeSummary(int Covers, int Baked, int AlreadyBaked, int Failed, int Pruned, TimeSpan Elapsed);

/// <summary>
/// Bakes the grid's cover derivatives (A3) off the main thread: on its own worker threads at below-normal priority,
/// so a bake never competes with the render loop or holds a thread-pool thread for its ~0.2 s. Scraping bakes each
/// new cover as it's saved; <see cref="BakeMissingAsync"/> bakes every cover in the library that has no derivative
/// (the user's own art too), and deletes derivatives nothing uses any more. A derivative's name includes its source's
/// size and time, so a changed source gets a new one.
/// </summary>
public sealed class DerivativeService : IDisposable
{
    private readonly LibraryService _library;
    private readonly IPlatformPaths _paths;
    private readonly DerivativeBaker? _baker;
    private readonly ILog _log;
    private readonly BlockingCollection<Action> _work = new();
    private readonly Thread[] _threads;

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

    /// <summary>The derivative's path for a media row.</summary>
    public string PathFor(MediaRoot root, string relPath, long sizeBytes, long mtimeMs) =>
        TextureDerivatives.PathFor(_paths.CacheDir, root, relPath, sizeBytes, mtimeMs);

    /// <summary>Bakes one derivative (unless it exists). False when it couldn't be (the reason is logged).</summary>
    public Task<bool> BakeAsync(MediaRoot root, string relPath, long sizeBytes, long mtimeMs, CancellationToken cancellationToken)
    {
        if (_baker is null)
        {
            return Task.FromResult(false);
        }

        var destination = PathFor(root, relPath, sizeBytes, mtimeMs);
        var source = Path.Combine(root == MediaRoot.Config ? _paths.ConfigDir : _paths.DataDir, relPath.Replace('/', Path.DirectorySeparatorChar));
        var completion = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        _work.Add(() =>
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

                var ok = _baker.TryBake(source, destination, out var error);
                if (!ok)
                {
                    _log.Write(LogLevel.Warning, $"Derivative: couldn't bake '{relPath}': {error}");
                }

                completion.TrySetResult(ok);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                _log.Write(LogLevel.Warning, $"Derivative: couldn't bake '{relPath}': {e.Message}");
                completion.TrySetResult(false);
            }
        }, CancellationToken.None);
        return completion.Task;
    }

    /// <summary>
    /// Bakes every cover in the library that has no derivative, then deletes the derivatives no cover names (stale
    /// ones whose source changed or went). Safe to run while browsing: one below-normal thread by default.
    /// </summary>
    public async Task<BakeSummary> BakeMissingAsync(IProgress<JobProgress>? progress, CancellationToken cancellationToken)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var covers = await _library.ReadAsync(c => ScrapeStore.MediaOfKind(c, MediaKinds.Cover), cancellationToken).ConfigureAwait(false);
        var wanted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var missing = new List<(MediaRoot Root, string Path, long Size, long Mtime)>();
        foreach (var cover in covers)
        {
            var path = PathFor(cover.Root, cover.Path, cover.SizeBytes, cover.MtimeMs);
            wanted.Add(Path.GetFileName(path));
            if (!File.Exists(path))
            {
                missing.Add(cover);
            }
        }

        int baked = 0, failed = 0, done = 0;
        progress?.Report(new JobProgress("bake", 0, missing.Count));
        if (_baker is not null)
        {
            var tasks = missing.Select(async m =>
            {
                var ok = await BakeAsync(m.Root, m.Path, m.Size, m.Mtime, cancellationToken).ConfigureAwait(false);
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

        return new BakeSummary(covers.Count, baked, covers.Count - missing.Count, _baker is null ? missing.Count : failed, pruned, stopwatch.Elapsed);
    }

    public void Dispose()
    {
        _work.CompleteAdding();
        foreach (var thread in _threads)
        {
            thread.Join();
        }

        _work.Dispose();
    }

    private void Loop()
    {
        foreach (var job in _work.GetConsumingEnumerable())
        {
            job();
        }
    }
}
