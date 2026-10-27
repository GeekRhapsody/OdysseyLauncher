using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using Godot;
using Launcher.App.Boot;
using Launcher.Core.Media;

namespace Launcher.App.Ui;

/// <summary>
/// A manual's pages as textures, for <c>ManualViewer</c>: a thread of its own opens the PDF (through Core's
/// <see cref="IPdfRenderer"/>, which keeps a reader on the thread that opened it) and renders the pages asked for, newest
/// request first, each into an <see cref="Image"/> and its texture made there (making a texture on the main thread can
/// stall it, A3). The main thread asks for the page it shows, whole or zoomed to its width, and gets its neighbours
/// rendered whole after it, so a page turn is usually there already; it keeps only those, freeing the rest. A whole page
/// fits the box it's shown in (at most <see cref="MaxHeight"/> high); a zoomed one fills the box's width (rendered at
/// most <see cref="MaxZoomedWidth"/> wide: scanned manuals hold no more, and the screen scales it the rest).
/// </summary>
public sealed class ManualPages : IDisposable
{
    public const string Unsupported = "Manuals can't be shown on this system yet.";
    public const int MaxHeight = 2160;
    public const int MaxZoomedWidth = 2560;

    private readonly IPdfRenderer _renderer;
    private readonly string _path;
    private readonly MainThreadQueue _queue;
    // Never disposed: the thread may still wait on it after the viewer has finished with it (a small handle the GC frees).
    private readonly AutoResetEvent _wake = new(false);
    private readonly object _lock = new();
    private readonly List<Job> _jobs = [];
    // Taken from the queue and not yet arrived (or failed): asked for again, they'd be rendered twice.
    private readonly HashSet<Job> _inFlight = [];
    private readonly Dictionary<Key, Rendered> _pages = [];
    private readonly List<Key> _gone = [];
    private Vector2I _box;
    private volatile bool _stop;
    private bool _disposed;

    public ManualPages(IPdfRenderer renderer, string path, MainThreadQueue queue)
    {
        _renderer = renderer;
        _path = path;
        _queue = queue;
        var thread = new Thread(Run) { IsBackground = true, Name = "Manual pages", Priority = ThreadPriority.BelowNormal };
        thread.Start();
    }

    /// <summary>A rendered page: its texture and the page's own shape (its width over its height).</summary>
    public readonly record struct Page(ImageTexture Texture, float Aspect);

    /// <summary>Main thread: the page count once the document is open; 0 until then (and if it can't be).</summary>
    public int PageCount { get; private set; }

    /// <summary>Main thread: why the manual can't be shown, for the user; null while it can.</summary>
    public string? Error { get; private set; }

    /// <summary>Main thread: raised when a page arrives, or the document opens or fails.</summary>
    public event Action? Changed;

    /// <summary>
    /// Main thread: show <paramref name="page"/> in a <paramref name="box"/> of that many pixels, whole or zoomed to the
    /// box's width. Its neighbours are rendered whole after it; pages no longer wanted are freed.
    /// </summary>
    public void Show(int page, Vector2I box, bool zoomed)
    {
        if (_disposed || box.X <= 0 || box.Y <= 0)
        {
            return;
        }

        // Pages rendered for another size still show (scaled) until their replacements come.
        _box = box;

        var wanted = new List<Key>(4);
        if (zoomed)
        {
            wanted.Add(new Key(page, true));
        }

        wanted.Add(new Key(page, false));
        wanted.Add(new Key(page + 1, false));
        wanted.Add(new Key(page - 1, false));

        _gone.Clear();
        foreach (var key in _pages.Keys)
        {
            if (!wanted.Contains(key))
            {
                _gone.Add(key);
            }
        }

        foreach (var key in _gone)
        {
            _pages[key].Texture.Dispose();
            _pages.Remove(key);
        }

        lock (_lock)
        {
            _jobs.Clear();
            foreach (var key in wanted)
            {
                // Not one already there at this size, or on its way.
                var job = new Job(key, box);
                if (key.Index >= 0 && (PageCount == 0 || key.Index < PageCount) && (!_pages.TryGetValue(key, out var have) || have.Box != box) && !_inFlight.Contains(job))
                {
                    _jobs.Add(job);
                }
            }
        }

        _wake.Set();
    }

    /// <summary>Main thread: the page as rendered, if it is (perhaps for an earlier box).</summary>
    public bool TryGet(int page, bool zoomed, out Page result)
    {
        if (_pages.TryGetValue(new Key(page, zoomed), out var have))
        {
            result = new Page(have.Texture, have.Aspect);
            return true;
        }

        result = default;
        return false;
    }

    /// <summary>Main thread: stops the thread and frees every page.</summary>
    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        _stop = true;
        _wake.Set();
        foreach (var page in _pages.Values)
        {
            page.Texture.Dispose();
        }

        _pages.Clear();
        Changed = null;
    }

    private void Arrived(Key key, Vector2I box, ImageTexture texture, float aspect)
    {
        lock (_lock)
        {
            _inFlight.Remove(new Job(key, box));
        }

        if (_disposed || box != _box)
        {
            texture.Dispose();
            return;
        }

        if (_pages.TryGetValue(key, out var old))
        {
            old.Texture.Dispose();
        }

        _pages[key] = new Rendered(texture, aspect, box);
        Changed?.Invoke();
    }

    /// <summary>A page's pixel size in the box: fitted whole, or filling its width.</summary>
    private static Vector2I SizeIn(Vector2I box, float width, float height, bool zoomed)
    {
        float scale;
        if (zoomed)
        {
            scale = Math.Min(box.X, MaxZoomedWidth) / width;
        }
        else
        {
            scale = Math.Min(box.X / width, Math.Min(box.Y, MaxHeight) / height);
        }

        return new Vector2I(Math.Max(1, (int)Math.Round(width * scale)), Math.Max(1, (int)Math.Round(height * scale)));
    }

    // ---- The rendering thread ------------------------------------------------------------------------

    private void Run()
    {
        // The thread calls into Godot (its images and textures) for its whole run, so the app waits for it as it quits.
        if (!GodotWork.TryEnter())
        {
            return;
        }

        IPdfReader? reader = null;
        try
        {
            var clock = Stopwatch.StartNew();
            reader = _renderer.Open(_path, out var error);
            var count = reader?.PageCount ?? 0;
            GD.Print(reader is null ? $"Manual: {_path} can't be opened: {error}." : $"Manual: {_path}, {count} pages, opened in {clock.ElapsedMilliseconds} ms.");
            _queue.Post(() =>
            {
                if (_disposed)
                {
                    return;
                }

                PageCount = count;
                Error = reader is null ? error ?? "it can't be read" : null;
                if (count > 0)
                {
                    // Jobs asked for before the count was known may be past the end.
                    lock (_lock)
                    {
                        _jobs.RemoveAll(job => job.Key.Index >= count);
                    }
                }

                Changed?.Invoke();
            });

            if (reader is null)
            {
                return;
            }

            byte[] rgba = [];
            while (!_stop && !GodotWork.Quitting)
            {
                Job job;
                lock (_lock)
                {
                    if (_jobs.Count > 0)
                    {
                        job = _jobs[0];
                        _jobs.RemoveAt(0);
                        _inFlight.Add(job);
                    }
                    else
                    {
                        job = default;
                    }
                }

                if (job.Box == default)
                {
                    // Woken by a request; otherwise a look at whether the app is quitting, which it waits for.
                    _wake.WaitOne(50);
                    continue;
                }

                if (!Render(reader, job, ref rgba))
                {
                    lock (_lock)
                    {
                        _inFlight.Remove(job);
                    }
                }
            }
        }
        finally
        {
            reader?.Dispose();
            GodotWork.Exit();
        }
    }

    /// <summary>Renders the job's page and posts it to the main thread; false if it can't be rendered.</summary>
    private bool Render(IPdfReader reader, Job job, ref byte[] rgba)
    {
        var index = job.Key.Index;
        if (index >= reader.PageCount || !reader.TryGetPageSize(index, out var width, out var height))
        {
            return false;
        }

        var size = SizeIn(job.Box, width, height, job.Key.Zoomed);
        var clock = Stopwatch.StartNew();

        // Image.CreateFromData wants the exact length; the same size page after page reuses the buffer.
        var length = size.X * size.Y * 4;
        if (rgba.Length != length)
        {
            rgba = new byte[length];
        }

        if (!reader.TryRender(index, size.X, size.Y, rgba, out var error))
        {
            GD.PushWarning($"Manual: page {index + 1} of {_path} can't be shown: {error}.");
            return false;
        }

        var rendered = clock.ElapsedMilliseconds;
        var image = Image.CreateFromData(size.X, size.Y, false, Image.Format.Rgba8, rgba);
        var texture = ImageTexture.CreateFromImage(image);
        image.Dispose();
        GD.Print($"Manual: page {index + 1} at {size.X} × {size.Y}{(job.Key.Zoomed ? " (zoomed)" : string.Empty)} in {rendered} ms, its texture in {clock.ElapsedMilliseconds - rendered} ms.");
        var aspect = width / height;
        _queue.Post(() => Arrived(job.Key, job.Box, texture, aspect));
        return true;
    }

    private readonly record struct Key(int Index, bool Zoomed);

    private readonly record struct Job(Key Key, Vector2I Box);

    private readonly record struct Rendered(ImageTexture Texture, float Aspect, Vector2I Box);
}
