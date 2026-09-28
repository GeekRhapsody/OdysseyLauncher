using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Threading;
using Godot;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Microsoft.Win32.SafeHandles;

namespace Launcher.App.Textures;

/// <summary>Told when a pool cell's cover is on the GPU, or won't be.</summary>
public interface ITextureSink
{
    /// <summary>Main thread: the slot's layer now holds the cover it was last requested for.</summary>
    void OnLayerReady(int slot);

    /// <summary>Main thread: the slot's cover has no derivative (or it couldn't be read), so the box stays plain.</summary>
    void OnLayerMissing(int slot);
}

/// <summary>
/// Streams baked cover derivatives into the pool's <see cref="Texture2DArray"/> (A3, ITextureStreamer in A2):
/// <list type="bullet">
/// <item>One request slot per pool cell. Re-requesting a slot supersedes the old request; a result that arrives
/// for an old request is dropped.</item>
/// <item>Workers take the pending slot nearest the view centre, counting rows ahead of the scroll as 0.6× as far.</item>
/// <item>Workers read each file into their own reusable buffer and decode it with
/// <c>Image.LoadDdsFromBuffer(span)</c> into a pooled <see cref="Image"/>, so a cover allocates no managed memory once
/// its derivative's path is known; paths are worked out once per game (A3, R10).</item>
/// <item>The array is created up front, and the main thread only updates its layers, within a byte budget and a
/// count cap per frame.</item>
/// </list>
/// </summary>
public sealed class TextureStreamer : IDisposable
{
    public const int LayerSize = TextureDerivatives.Size;
    public const Image.Format LayerFormat = Image.Format.BptcRgba;

    /// <summary>A3: 4 MB per frame.</summary>
    public const long DefaultBudgetBytes = 4L * 1024 * 1024;

    private const int Idle = 0;
    private const int Pending = 1;
    private const int Loading = 2;
    private const int Ready = 3;
    private const int Missing = 4;
    private const int StatsCapacity = 1 << 16;
    private const int PoolLimit = 8;

    private readonly object _gate = new();
    private string _cacheDir = string.Empty;
    private string _configDir = string.Empty;
    private string _dataDir = string.Empty;
    private readonly int[] _state;
    private readonly int[] _generation;
    private readonly int[] _row;
    private readonly MediaRoot[] _root;
    private readonly string?[] _relPath;
    private readonly long[] _size;
    private readonly long[] _mtime;
    private readonly Image?[] _result;
    private readonly Thread[] _workers;
    private readonly long _layerBytes;
    // A plain array under its own lock: ConcurrentStack allocates a node per push, and the main thread recycles.
    private readonly Image?[] _images = new Image?[PoolLimit];
    private int _pooled;
    private readonly ConcurrentDictionary<string, string?> _configPaths = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, string?> _dataPaths = new(StringComparer.Ordinal);
    private Texture2DArray? _array;
    private bool _stopping;
    private float _viewRow;
    private float _direction = 1;
    private int _reportedMissing;

    // Statistics for the bench: written by workers under the gate or by the main thread.
    private readonly double[] _decodeMs = new double[StatsCapacity];
    private readonly double[] _uploadMs = new double[StatsCapacity];

    /// <summary>Starts the workers. <see cref="SetFolders"/> must be called before the first request.</summary>
    public TextureStreamer(int slots, int workers)
    {
        _state = new int[slots];
        _generation = new int[slots];
        _row = new int[slots];
        _root = new MediaRoot[slots];
        _relPath = new string?[slots];
        _size = new long[slots];
        _mtime = new long[slots];
        _result = new Image?[slots];
        _layerBytes = LayerBytes();
        _workers = new Thread[workers];
        for (var i = 0; i < workers; i++)
        {
            _workers[i] = new Thread(WorkerLoop) { IsBackground = true, Name = $"Cover decode {i}", Priority = ThreadPriority.BelowNormal };
            _workers[i].Start();
        }
    }

    /// <summary>Where derivatives and their sources are. Main thread, before any request.</summary>
    public void SetFolders(string cacheDir, string configDir, string dataDir)
    {
        lock (_gate)
        {
            _cacheDir = cacheDir;
            _configDir = configDir;
            _dataDir = dataDir;
        }
    }

    /// <summary>A3: <c>clamp(ProcessorCount / 4, 1, 4)</c>, which is 2 on the Deck.</summary>
    public static int DefaultWorkers => Math.Clamp(System.Environment.ProcessorCount / 4, 1, 4);

    public int Slots => _state.Length;

    /// <summary>The pool's layers; null while evicted.</summary>
    public Texture2DArray? Array => _array;

    public int Uploads { get; private set; }

    public int Decodes { get; private set; }

    public int FramesAtBudget { get; private set; }

    public int FramesAtCap { get; private set; }

    public int MissingCount { get; private set; }

    public int Failures { get; private set; }

    public int Discarded { get; private set; }

    public ReadOnlySpan<double> DecodeSamples => _decodeMs.AsSpan(0, Math.Min(Decodes, StatsCapacity));

    public ReadOnlySpan<double> UploadSamples => _uploadMs.AsSpan(0, Math.Min(Uploads, StatsCapacity));

    /// <summary>
    /// Main thread. Creates the array, one blank layer per slot (A3: never while browsing; creation can stall for
    /// tens of milliseconds).
    /// </summary>
    public Texture2DArray CreateArray()
    {
        if (_array is not null)
        {
            return _array;
        }

        using var blank = Image.CreateEmpty(LayerSize, LayerSize, true, LayerFormat);
        var layers = new Godot.Collections.Array<Image>();
        for (var i = 0; i < Slots; i++)
        {
            layers.Add(blank);
        }

        _array = new Texture2DArray();
        var error = _array.CreateFromImages(layers);
        if (error != Error.Ok)
        {
            GD.PushError($"Textures: couldn't create the cover array: {error}");
        }

        return _array;
    }

    /// <summary>
    /// Main thread, during the warm-up after interactive: the first layer update can take tens of milliseconds, so
    /// it's done once before anyone scrolls.
    /// </summary>
    public void WarmUpload()
    {
        if (_array is null)
        {
            return;
        }

        using var blank = Image.CreateEmpty(LayerSize, LayerSize, true, LayerFormat);
        _array.UpdateLayer(blank, 0);
    }

    /// <summary>Main thread. Frees the array and drops every request (while a game runs). <see cref="CreateArray"/> restores it.</summary>
    public void Evict()
    {
        lock (_gate)
        {
            for (var slot = 0; slot < Slots; slot++)
            {
                DropResult(slot);
                _generation[slot]++;
                _state[slot] = Idle;
            }
        }

        EmptyPool();
        _array?.Dispose();
        _array = null;
    }

    /// <summary>Main thread, once per frame: where the view is, for the workers' priorities.</summary>
    public void SetView(float centreRow, float direction)
    {
        Volatile.Write(ref _viewRow, centreRow);
        Volatile.Write(ref _direction, direction >= 0 ? 1 : -1);
    }

    /// <summary>
    /// Main thread. Supersedes any earlier request for the slot. The path must be the library's own string (not built
    /// per call). With the source's indexed size and time, the worker works out the derivative's name without touching
    /// the source; 0 makes it read them.
    /// </summary>
    public void Request(int slot, int row, MediaRoot root, string relPath, long sizeBytes, long mtimeMs)
    {
        lock (_gate)
        {
            DropResult(slot);
            _generation[slot]++;
            _row[slot] = row;
            _root[slot] = root;
            _relPath[slot] = relPath;
            _size[slot] = sizeBytes;
            _mtime[slot] = mtimeMs;
            _state[slot] = Pending;
            Monitor.Pulse(_gate);
        }
    }

    /// <summary>Main thread: the slot no longer wants a cover.</summary>
    public void Cancel(int slot)
    {
        lock (_gate)
        {
            DropResult(slot);
            _generation[slot]++;
            _state[slot] = Idle;
            _relPath[slot] = null;
        }
    }

    /// <summary>
    /// Main thread, once per frame: uploads finished covers into their layers, nearest first, until
    /// <paramref name="budgetBytes"/> or <paramref name="cap"/> uploads (0 = no cap).
    /// </summary>
    public void PumpUploads(ITextureSink sink, long budgetBytes, int cap)
    {
        long spent = 0;
        var uploads = 0;
        for (var slot = 0; slot < Slots; slot++)
        {
            var state = Volatile.Read(ref _state[slot]);
            if (state == Missing)
            {
                lock (_gate)
                {
                    if (_state[slot] != Missing)
                    {
                        continue;
                    }

                    _state[slot] = Idle;
                }

                MissingCount++;
                sink.OnLayerMissing(slot);
                continue;
            }

            if (state != Ready)
            {
                continue;
            }

            if (spent + _layerBytes > budgetBytes && uploads > 0)
            {
                FramesAtBudget++;
                return;
            }

            if (cap > 0 && uploads >= cap)
            {
                FramesAtCap++;
                return;
            }

            Image? image;
            lock (_gate)
            {
                if (_state[slot] != Ready)
                {
                    continue;
                }

                image = _result[slot];
                _result[slot] = null;
                _state[slot] = Idle;
            }

            if (image is null || _array is null)
            {
                Recycle(image);
                continue;
            }

            var start = Stopwatch.GetTimestamp();
            _array.UpdateLayer(image, slot);
            var ms = Stopwatch.GetElapsedTime(start).TotalMilliseconds;
            Recycle(image);
            if (Uploads < StatsCapacity)
            {
                _uploadMs[Uploads] = ms;
            }

            Uploads++;
            uploads++;
            spent += _layerBytes;
            sink.OnLayerReady(slot);
        }
    }

    public void Dispose()
    {
        lock (_gate)
        {
            _stopping = true;
            Monitor.PulseAll(_gate);
        }

        foreach (var worker in _workers)
        {
            worker.Join();
        }

        for (var slot = 0; slot < Slots; slot++)
        {
            DropResult(slot);
        }

        EmptyPool();
        _array?.Dispose();
        _array = null;
    }

    private void DropResult(int slot)
    {
        if (_result[slot] is { } stale)
        {
            Recycle(stale);
            _result[slot] = null;
        }
    }

    /// <summary>Back to the pool for the next decode (its pixels are replaced then).</summary>
    private void Recycle(Image? image)
    {
        if (image is null)
        {
            return;
        }

        // Each pooled image keeps its 341 KB of pixels, so the pool stays small.
        lock (_images)
        {
            if (_pooled < _images.Length)
            {
                _images[_pooled++] = image;
                return;
            }
        }

        image.Dispose();
    }

    private Image TakeImage()
    {
        lock (_images)
        {
            if (_pooled > 0)
            {
                var image = _images[--_pooled]!;
                _images[_pooled] = null;
                return image;
            }
        }

        return new Image();
    }

    private void EmptyPool()
    {
        lock (_images)
        {
            while (_pooled > 0)
            {
                _images[--_pooled]!.Dispose();
                _images[_pooled] = null;
            }
        }
    }

    private void WorkerLoop()
    {
        // The buffer grows only for an unusually large file; a 512² BC7 mip chain is 341 KB.
        var buffer = new byte[512 * 1024];
        while (true)
        {
            int slot;
            int generation;
            MediaRoot root;
            string relPath;
            string cacheDir;
            string rootDir;
            long size;
            long mtime;
            lock (_gate)
            {
                while (!_stopping && (slot = PickNearest()) < 0)
                {
                    Monitor.Wait(_gate);
                }

                if (_stopping)
                {
                    return;
                }

                slot = PickNearest();
                _state[slot] = Loading;
                generation = _generation[slot];
                root = _root[slot];
                relPath = _relPath[slot]!;
                cacheDir = _cacheDir;
                rootDir = root == MediaRoot.Config ? _configDir : _dataDir;
                size = _size[slot];
                mtime = _mtime[slot];
            }

            var start = Stopwatch.GetTimestamp();
            Image? image = null;
            var failed = false;
            try
            {
                // From the indexed size and time when the library has them (one string, no file access); otherwise from
                // the source file, once per game.
                string? path;
                if (size > 0)
                {
                    path = TextureDerivatives.PathFor(cacheDir, root, relPath, size, mtime);
                }
                else
                {
                    var paths = root == MediaRoot.Config ? _configPaths : _dataPaths;
                    if (!paths.TryGetValue(relPath, out path))
                    {
                        path = TextureDerivatives.PathFor(cacheDir, rootDir, root, relPath);
                        paths[relPath] = path;
                    }
                }

                if (path is not null)
                {
                    image = Decode(path, ref buffer);
                    failed = image is null && File.Exists(path);
                }

                if (image is null && Interlocked.Increment(ref _reportedMissing) == 1)
                {
                    GD.Print($"Textures: no usable derivative for {relPath} ({(path is null ? "the source is missing" : failed ? "it didn't decode as a 512² BC7 DDS with mips" : "not baked yet")}: {path}). Baking derivatives is M4's.");
                }
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                failed = true;
            }

            var ms = Stopwatch.GetElapsedTime(start).TotalMilliseconds;
            lock (_gate)
            {
                if (image is not null && Decodes < StatsCapacity)
                {
                    _decodeMs[Decodes] = ms;
                }

                if (image is not null)
                {
                    Decodes++;
                }

                if (failed)
                {
                    Failures++;
                }

                if (_generation[slot] == generation && _state[slot] == Loading)
                {
                    _result[slot] = image;
                    _state[slot] = image is null ? Missing : Ready;
                }
                else
                {
                    Recycle(image);
                    Discarded++;
                }
            }
        }
    }

    /// <summary>
    /// Reads the file into the worker's buffer and decodes it into a pooled image; null if there's no such file or it
    /// isn't a 512² BC7 DDS with mips.
    /// </summary>
    private Image? Decode(string path, ref byte[] buffer)
    {
        SafeFileHandle handle;
        try
        {
            handle = File.OpenHandle(path, FileMode.Open, System.IO.FileAccess.Read, FileShare.Read, FileOptions.SequentialScan);
        }
        catch (FileNotFoundException)
        {
            return null;
        }
        catch (DirectoryNotFoundException)
        {
            return null;
        }

        using var file = handle;
        var length = RandomAccess.GetLength(file);
        if (length > 16 * 1024 * 1024)
        {
            return null;
        }

        if (length > buffer.Length)
        {
            buffer = new byte[length];
        }

        var read = 0;
        while (read < length)
        {
            var n = RandomAccess.Read(file, buffer.AsSpan(read, (int)length - read), read);
            if (n == 0)
            {
                break;
            }

            read += n;
        }

        var image = TakeImage();
        if (image.LoadDdsFromBuffer(buffer.AsSpan(0, read)) != Error.Ok
            || image.GetFormat() != LayerFormat
            || image.GetWidth() != LayerSize
            || image.GetHeight() != LayerSize
            || !image.HasMipmaps())
        {
            Recycle(image);
            return null;
        }

        return image;
    }

    /// <summary>The pending slot nearest the view centre; rows ahead of the scroll count as nearer. Under the gate.</summary>
    private int PickNearest()
    {
        var centre = Volatile.Read(ref _viewRow);
        var direction = Volatile.Read(ref _direction);
        var best = -1;
        var bestScore = float.MaxValue;
        for (var slot = 0; slot < _state.Length; slot++)
        {
            if (_state[slot] != Pending)
            {
                continue;
            }

            var d = _row[slot] - centre;
            var score = MathF.Abs(d) * (d * direction > 0 ? 0.6f : 1.0f) + slot * 0.0001f;
            if (score < bestScore)
            {
                bestScore = score;
                best = slot;
            }
        }

        return best;
    }

    private static long LayerBytes()
    {
        long total = 0;
        for (var size = LayerSize; size >= 1; size /= 2)
        {
            // 16 bytes per 4x4 block; mips below 4x4 still take one block.
            total += (long)Math.Max(1, size / 4) * Math.Max(1, size / 4) * 16;
        }

        return total;
    }
}
