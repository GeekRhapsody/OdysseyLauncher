using System;
using System.Buffers.Binary;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Threading;
using Godot;
using Launcher.App.Grid;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Theming;
using Microsoft.Win32.SafeHandles;

namespace Launcher.App.Textures;

/// <summary>Told when a pool cell's media for one slot channel is on the GPU, or won't be.</summary>
public interface ITextureSink
{
    /// <summary>Main thread: the cell's layer for the channel now holds the media it was last requested for.</summary>
    void OnLayerReady(int cell, int channel);

    /// <summary>Main thread: the media has no usable derivative, so the slot moves on down its fallback chain.</summary>
    void OnLayerMissing(int cell, int channel);
}

/// <summary>
/// Streams baked derivatives into the pool's texture arrays (A3, M6):
/// <list type="bullet">
/// <item>One request per pool cell and slot channel (<see cref="SlotLayout"/>). Re-requesting supersedes the old
/// request; a result that arrives for an old request is dropped.</item>
/// <item>Workers take the pending request nearest the view centre, counting rows ahead of the scroll as 0.6× as far,
/// covers before the other slots.</item>
/// <item>Workers read each file into their own reusable buffer and decode it into a pooled <see cref="Image"/>: the
/// whole 512² BC7 chain for the cover class (<c>Image.LoadDdsFromBuffer(span)</c>), or its mip chain from 256² down
/// for every other slot (<c>Image.SetData(span)</c> past mip 0), so a layer allocates no managed memory once its
/// derivative's path is known, and one derivative serves any slot.</item>
/// <item>The arrays are created up front (never while browsing), and the main thread only updates their layers,
/// within a byte budget and a cap per frame.</item>
/// </list>
/// </summary>
public sealed class TextureStreamer : IDisposable
{
    public const int LargeSize = TextureDerivatives.Size;
    public const int SmallSize = TextureDerivatives.Size / 2;
    public const Image.Format LayerFormat = Image.Format.BptcRgba;

    /// <summary>A3: 4 MB per frame.</summary>
    public const long DefaultBudgetBytes = 4L * 1024 * 1024;

    private const int Channels = MediaSlots.Count;
    private const int Idle = 0;
    private const int Pending = 1;
    private const int Loading = 2;
    private const int Ready = 3;
    private const int Missing = 4;
    private const int StatsCapacity = 1 << 16;
    private const int PoolLimit = 8;

    /// <summary>Workers prefer covers: another slot's request counts as this many rows further away.</summary>
    private const float SmallSlotPenaltyRows = 0.35f;

    private static readonly long LargeLayerBytes = ChainBytes(LargeSize);
    private static readonly long SmallLayerBytes = ChainBytes(SmallSize);

    private readonly object _gate = new();
    private string _cacheDir = string.Empty;
    private string _dataDir = string.Empty;

    // Per request unit: cell × Channels + channel.
    private readonly int[] _state;
    private readonly int[] _generation;
    private readonly int[] _row;
    private readonly bool[] _large;
    private readonly int[] _layer;
    private readonly string?[] _relPath;
    private readonly long[] _size;
    private readonly long[] _mtime;
    private readonly Image?[] _result;
    private readonly Thread[] _workers;

    // A plain array under its own lock: ConcurrentStack allocates a node per push, and the main thread recycles.
    private readonly Image?[] _images = new Image?[PoolLimit];
    private int _pooled;
    private readonly ConcurrentDictionary<string, string?> _derivativePaths = new(StringComparer.Ordinal);
    private Texture2DArray? _largeArray;
    private Texture2DArray? _smallArray;
    private bool _stopping;
    private float _viewRow;
    private float _direction = 1;
    private int _reportedMissing;

    // Statistics for the bench: written by workers under the gate or by the main thread.
    private readonly double[] _decodeMs = new double[StatsCapacity];
    private readonly double[] _uploadMs = new double[StatsCapacity];

    /// <summary>Starts the workers. <see cref="SetFolders"/> must be called before the first request.</summary>
    public TextureStreamer(int cells, int workers)
    {
        Cells = cells;
        var units = cells * Channels;
        _state = new int[units];
        _generation = new int[units];
        _row = new int[units];
        _large = new bool[units];
        _layer = new int[units];
        _relPath = new string?[units];
        _size = new long[units];
        _mtime = new long[units];
        _result = new Image?[units];
        _workers = new Thread[workers];
        for (var i = 0; i < workers; i++)
        {
            _workers[i] = new Thread(WorkerLoop) { IsBackground = true, Name = $"Texture decode {i}", Priority = ThreadPriority.BelowNormal };
            _workers[i].Start();
        }
    }

    /// <summary>Where derivatives and their sources (DataDir's media folder) are. Main thread, before any request.</summary>
    public void SetFolders(string cacheDir, string dataDir)
    {
        lock (_gate)
        {
            _cacheDir = cacheDir;
            _dataDir = dataDir;
        }
    }

    /// <summary>A3: <c>clamp(ProcessorCount / 4, 1, 4)</c>, which is 2 on the Deck.</summary>
    public static int DefaultWorkers => Math.Clamp(System.Environment.ProcessorCount / 4, 1, 4);

    /// <summary>Pool cells.</summary>
    public int Cells { get; }

    /// <summary>The slot channels requests are for.</summary>
    public SlotLayout Layout { get; private set; } = SlotLayout.Empty;

    /// <summary>The cover-class layers (512²); null while evicted or unused.</summary>
    public Texture2DArray? Large => _largeArray;

    /// <summary>Every other slot's layers (256²); null while evicted or unused.</summary>
    public Texture2DArray? Small => _smallArray;

    /// <summary>Whether the arrays the layout needs exist (they don't while a game runs, or before they're built).</summary>
    public bool HasArrays => (Layout.LargeCount == 0 || _largeArray is not null) && (Layout.SmallCount == 0 || _smallArray is not null);

    public int Uploads { get; private set; }

    public int Decodes { get; private set; }

    public int FramesAtBudget { get; private set; }

    public int FramesAtCap { get; private set; }

    public int MissingCount { get; private set; }

    public int Failures { get; private set; }

    public int Discarded { get; private set; }

    /// <summary>Upload counts, total and longest times, for 512² and 256² layers apart (the bench log).</summary>
    public (int Count, double TotalMs, double MaxMs) LargeUploadStats => (_largeUploads, _largeUploadMs, _largeUploadMax);

    public (int Count, double TotalMs, double MaxMs) SmallUploadStats => (_smallUploads, _smallUploadMs, _smallUploadMax);

    private int _largeUploads;
    private double _largeUploadMs;
    private double _largeUploadMax;
    private int _smallUploads;
    private double _smallUploadMs;
    private double _smallUploadMax;

    public ReadOnlySpan<double> DecodeSamples => _decodeMs.AsSpan(0, Math.Min(Decodes, StatsCapacity));

    public ReadOnlySpan<double> UploadSamples => _uploadMs.AsSpan(0, Math.Min(Uploads, StatsCapacity));

    /// <summary>
    /// A blank array of <paramref name="layers"/> BC7 layers with mips. Creation can stall the main thread for tens of
    /// milliseconds (M1), so it's done at boot, or on a worker thread, never while browsing.
    /// </summary>
    public static Texture2DArray? CreateArray(int size, int layers)
    {
        if (layers <= 0)
        {
            return null;
        }

        using var blank = Image.CreateEmpty(size, size, true, LayerFormat);
        var images = new Godot.Collections.Array<Image>();
        for (var i = 0; i < layers; i++)
        {
            images.Add(blank);
        }

        var array = new Texture2DArray();
        var error = array.CreateFromImages(images);
        if (error != Error.Ok)
        {
            GD.PushError($"Textures: couldn't create a {size}² array of {layers} layers: {error}");
        }

        return array;
    }

    /// <summary>
    /// The arrays a layout needs, reusing the current ones where they already fit. Any thread: a worker, so a new
    /// array's creation and first layer update (each can take tens of milliseconds) never land on the main thread.
    /// </summary>
    public (Texture2DArray? Large, Texture2DArray? Small) BuildArrays(SlotLayout layout, Texture2DArray? currentLarge, Texture2DArray? currentSmall)
    {
        var large = layout.LargeCount == 0 ? null
            : currentLarge is not null && currentLarge.GetLayers() == Cells * layout.LargeCount ? currentLarge
            : Warm(CreateArray(LargeSize, Cells * layout.LargeCount), LargeSize);
        var small = layout.SmallCount == 0 ? null
            : currentSmall is not null && currentSmall.GetLayers() == Cells * layout.SmallCount ? currentSmall
            : Warm(CreateArray(SmallSize, Cells * layout.SmallCount), SmallSize);
        return (large, small);
    }

    private static Texture2DArray? Warm(Texture2DArray? array, int size)
    {
        if (array is not null)
        {
            using var blank = Image.CreateEmpty(size, size, true, LayerFormat);
            array.UpdateLayer(blank, 0);
        }

        return array;
    }

    /// <summary>
    /// Main thread: switches to a layout and its arrays (from <see cref="BuildArrays"/>), dropping every request. Arrays
    /// that aren't kept are freed.
    /// </summary>
    public void Install(SlotLayout layout, Texture2DArray? large, Texture2DArray? small)
    {
        DropAll();
        if (_largeArray is not null && _largeArray != large)
        {
            _largeArray.Dispose();
        }

        if (_smallArray is not null && _smallArray != small)
        {
            _smallArray.Dispose();
        }

        Layout = layout;
        _largeArray = large;
        _smallArray = small;
    }

    /// <summary>
    /// Main thread, at boot: the cover-class array for a whole pool, before the theme's layout is known. Every game
    /// template has a cover (A7), so it's nearly always needed, and making it now overlaps the DB opening.
    /// </summary>
    public void CreateBootArray() => _largeArray ??= CreateArray(LargeSize, Cells);

    /// <summary>
    /// Main thread, during boot: the first layer update can take tens of milliseconds, so it's done once before
    /// anyone scrolls.
    /// </summary>
    public void WarmUpload()
    {
        foreach (var (array, size) in (ReadOnlySpan<(Texture2DArray?, int)>)[(_largeArray, LargeSize), (_smallArray, SmallSize)])
        {
            if (array is not null)
            {
                using var blank = Image.CreateEmpty(size, size, true, LayerFormat);
                array.UpdateLayer(blank, 0);
            }
        }
    }

    /// <summary>Main thread. Frees the arrays and drops every request (while a game runs). <see cref="Restore"/> brings them back.</summary>
    public void Evict()
    {
        DropAll();
        EmptyPool();
        _largeArray?.Dispose();
        _largeArray = null;
        _smallArray?.Dispose();
        _smallArray = null;
    }

    /// <summary>Main thread, after a game: recreates the layout's arrays.</summary>
    public void Restore()
    {
        var (large, small) = BuildArrays(Layout, _largeArray, _smallArray);
        _largeArray = large;
        _smallArray = small;
    }

    /// <summary>Main thread, once per frame: where the view is, for the workers' priorities.</summary>
    public void SetView(float centreRow, float direction)
    {
        Volatile.Write(ref _viewRow, centreRow);
        Volatile.Write(ref _direction, direction >= 0 ? 1 : -1);
    }

    /// <summary>
    /// Main thread. Supersedes any earlier request for the cell's channel. The path must be the library's own string
    /// (not built per call). With the source's indexed size and time, the worker works out the derivative's name
    /// without touching the source; 0 makes it read them.
    /// </summary>
    public void Request(int cell, int channel, int row, in MediaRef media)
    {
        var unit = cell * Channels + channel;
        lock (_gate)
        {
            DropResult(unit);
            _generation[unit]++;
            _row[unit] = row;
            _large[unit] = Layout.IsLarge(channel);
            _layer[unit] = Layout.LayerOf(cell, channel);
            _relPath[unit] = media.Path;
            _size[unit] = media.SizeBytes;
            _mtime[unit] = media.MtimeMs;
            _state[unit] = Pending;
            Monitor.Pulse(_gate);
        }
    }

    /// <summary>Main thread: the cell's channel no longer wants media.</summary>
    public void Cancel(int cell, int channel)
    {
        var unit = cell * Channels + channel;
        lock (_gate)
        {
            CancelUnit(unit);
        }
    }

    /// <summary>Main thread: none of the cell's channels want media.</summary>
    public void CancelCell(int cell)
    {
        lock (_gate)
        {
            for (var unit = cell * Channels; unit < (cell + 1) * Channels; unit++)
            {
                CancelUnit(unit);
            }
        }
    }

    /// <summary>
    /// Main thread, once per frame: uploads finished layers, until <paramref name="budgetBytes"/> or
    /// <paramref name="cap"/> (0 = no cap). The cap counts a 512² layer as one upload and a 256² layer as a quarter,
    /// the ratio of their sizes, so a frame never carries more than the M1 burst of eight covers' worth.
    /// </summary>
    public void PumpUploads(ITextureSink sink, long budgetBytes, int cap)
    {
        long spent = 0;
        var quarters = 0;
        var uploads = 0;
        for (var unit = 0; unit < _state.Length; unit++)
        {
            var state = Volatile.Read(ref _state[unit]);
            if (state == Missing)
            {
                lock (_gate)
                {
                    if (_state[unit] != Missing)
                    {
                        continue;
                    }

                    _state[unit] = Idle;
                }

                MissingCount++;
                sink.OnLayerMissing(unit / Channels, unit % Channels);
                continue;
            }

            if (state != Ready)
            {
                continue;
            }

            var large = _large[unit];
            var bytes = large ? LargeLayerBytes : SmallLayerBytes;
            if (spent + bytes > budgetBytes && uploads > 0)
            {
                FramesAtBudget++;
                return;
            }

            var cost = large ? 4 : 1;
            if (cap > 0 && quarters + cost > cap * 4 && uploads > 0)
            {
                FramesAtCap++;
                return;
            }

            Image? image;
            int layer;
            lock (_gate)
            {
                if (_state[unit] != Ready)
                {
                    continue;
                }

                image = _result[unit];
                layer = _layer[unit];
                _result[unit] = null;
                _state[unit] = Idle;
            }

            var array = large ? _largeArray : _smallArray;
            if (image is null || array is null)
            {
                Recycle(image);
                continue;
            }

            var start = Stopwatch.GetTimestamp();
            array.UpdateLayer(image, layer);
            var ms = Stopwatch.GetElapsedTime(start).TotalMilliseconds;
            Recycle(image);
            if (Uploads < StatsCapacity)
            {
                _uploadMs[Uploads] = ms;
            }

            if (large)
            {
                _largeUploads++;
                _largeUploadMs += ms;
                _largeUploadMax = Math.Max(_largeUploadMax, ms);
            }
            else
            {
                _smallUploads++;
                _smallUploadMs += ms;
                _smallUploadMax = Math.Max(_smallUploadMax, ms);
            }

            Uploads++;
            uploads++;
            quarters += cost;
            spent += bytes;
            sink.OnLayerReady(unit / Channels, unit % Channels);
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

        for (var unit = 0; unit < _state.Length; unit++)
        {
            DropResult(unit);
        }

        EmptyPool();
        _largeArray?.Dispose();
        _largeArray = null;
        _smallArray?.Dispose();
        _smallArray = null;
    }

    private void DropAll()
    {
        lock (_gate)
        {
            for (var unit = 0; unit < _state.Length; unit++)
            {
                CancelUnit(unit);
            }
        }
    }

    /// <summary>Under the gate.</summary>
    private void CancelUnit(int unit)
    {
        DropResult(unit);
        _generation[unit]++;
        _state[unit] = Idle;
        _relPath[unit] = null;
    }

    private void DropResult(int unit)
    {
        if (_result[unit] is { } stale)
        {
            Recycle(stale);
            _result[unit] = null;
        }
    }

    /// <summary>Back to the pool for the next decode (its pixels are replaced then).</summary>
    private void Recycle(Image? image)
    {
        if (image is null)
        {
            return;
        }

        // Each pooled image keeps its pixels (341 KB at most), so the pool stays small.
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
            int unit;
            int generation;
            string relPath;
            string cacheDir;
            string dataDir;
            long size;
            long mtime;
            bool large;
            lock (_gate)
            {
                while (!_stopping && (unit = PickNearest()) < 0)
                {
                    Monitor.Wait(_gate);
                }

                if (_stopping)
                {
                    return;
                }

                unit = PickNearest();
                _state[unit] = Loading;
                generation = _generation[unit];
                relPath = _relPath[unit]!;
                cacheDir = _cacheDir;
                dataDir = _dataDir;
                size = _size[unit];
                mtime = _mtime[unit];
                large = _large[unit];
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
                    path = TextureDerivatives.PathFor(cacheDir, relPath, size, mtime);
                }
                else if (!_derivativePaths.TryGetValue(relPath, out path))
                {
                    path = TextureDerivatives.PathFor(cacheDir, dataDir, relPath);
                    _derivativePaths[relPath] = path;
                }

                if (path is not null)
                {
                    image = Decode(path, ref buffer, large);
                    failed = image is null && File.Exists(path);
                }

                if (image is null && Interlocked.Increment(ref _reportedMissing) == 1)
                {
                    GD.Print($"Textures: no usable derivative for {relPath} ({(path is null ? "the source is missing" : failed ? "it didn't decode as a 512² BC7 DDS with mips" : "not baked yet")}: {path}); its slot falls back down its chain. Further misses aren't logged.");
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

                if (_generation[unit] == generation && _state[unit] == Loading)
                {
                    _result[unit] = image;
                    _state[unit] = image is null ? Missing : Ready;
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
    /// Reads the file into the worker's buffer and decodes it into a pooled image: the whole chain, or for a 256²
    /// layer the chain from mip 1. Null if there's no such file or it isn't a 512² BC7 DDS with a full mip chain.
    /// </summary>
    private Image? Decode(string path, ref byte[] buffer, bool large)
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
        var data = buffer.AsSpan(0, read);
        if (large)
        {
            if (image.LoadDdsFromBuffer(data) != Error.Ok
                || image.GetFormat() != LayerFormat
                || image.GetWidth() != LargeSize
                || image.GetHeight() != LargeSize
                || !image.HasMipmaps())
            {
                Recycle(image);
                return null;
            }

            return image;
        }

        if (!TryMipOneChain(data, out var chain))
        {
            Recycle(image);
            return null;
        }

        image.SetData(SmallSize, SmallSize, true, LayerFormat, chain);
        return image;
    }

    /// <summary>
    /// The mip chain from 256² down, inside a 512² BC7 DDS with a full chain: past the header (with its DX10
    /// extension) and mip 0. The header is checked, since <c>SetData</c> can't.
    /// </summary>
    private static bool TryMipOneChain(ReadOnlySpan<byte> dds, out ReadOnlySpan<byte> chain)
    {
        chain = default;
        const int HeaderEnd = 4 + 124;
        if (dds.Length < HeaderEnd + 20 || !dds[..4].SequenceEqual("DDS "u8)
            || BinaryPrimitives.ReadInt32LittleEndian(dds[12..]) != LargeSize
            || BinaryPrimitives.ReadInt32LittleEndian(dds[16..]) != LargeSize
            || BinaryPrimitives.ReadInt32LittleEndian(dds[28..]) < 10
            || !dds[84..88].SequenceEqual("DX10"u8))
        {
            return false;
        }

        // DXGI_FORMAT_BC7_UNORM (98) or its sRGB twin (99).
        var format = BinaryPrimitives.ReadInt32LittleEndian(dds[HeaderEnd..]);
        var start = HeaderEnd + 20 + LargeSize * LargeSize;
        if (format is not (98 or 99) || dds.Length < start + SmallLayerBytes)
        {
            return false;
        }

        chain = dds.Slice(start, (int)SmallLayerBytes);
        return true;
    }

    /// <summary>The pending request nearest the view centre; rows ahead of the scroll count as nearer. Under the gate.</summary>
    private int PickNearest()
    {
        var centre = Volatile.Read(ref _viewRow);
        var direction = Volatile.Read(ref _direction);
        var best = -1;
        var bestScore = float.MaxValue;
        for (var unit = 0; unit < _state.Length; unit++)
        {
            if (_state[unit] != Pending)
            {
                continue;
            }

            var d = _row[unit] - centre;
            var score = MathF.Abs(d) * (d * direction > 0 ? 0.6f : 1.0f) + (_large[unit] ? 0 : SmallSlotPenaltyRows) + unit * 0.00001f;
            if (score < bestScore)
            {
                bestScore = score;
                best = unit;
            }
        }

        return best;
    }

    /// <summary>A BC7 mip chain's bytes: 16 per 4×4 block, and mips below 4×4 still take one block.</summary>
    private static long ChainBytes(int size)
    {
        long total = 0;
        for (var s = size; s >= 1; s /= 2)
        {
            total += (long)Math.Max(1, s / 4) * Math.Max(1, s / 4) * 16;
        }

        return total;
    }
}
