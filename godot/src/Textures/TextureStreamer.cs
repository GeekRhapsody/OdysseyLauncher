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

    /// <summary>
    /// Main thread (POC, streamed layer pool): the cell's layer for the channel was given to a request nearer the view.
    /// The slot shows its fallback until the streamer brings the media back (<see cref="OnLayerReady"/>).
    /// </summary>
    void OnLayerEvicted(int cell, int channel);

    /// <summary>Main thread (POC): an array was built on first demand; materials sampling the arrays need it.</summary>
    void OnArraysChanged();
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
/// <item>POC (direct source images): a streamer made with <c>directSources</c> reads the media folder's images
/// themselves (PNG, JPEG, WebP), decodes them with Godot, squeezes them to the layer's square with mips, and keeps
/// RGBA8 arrays (4× the VRAM of BC7). Workers allocate per image then, and decodes take tens of milliseconds.</item>
/// <item>POC (streamed layer pool): layers aren't fixed per cell and channel. Each class's array is a pool that may be
/// smaller than cells × channels; a request gets a layer when a worker takes it, so slots with no media (or showing
/// their fallback) hold none, and when the pool is full it takes the layer of the shown or waiting request farthest
/// from the view, if that one is clearly farther than itself. The loser goes back to pending, its cell shows the
/// fallback (<see cref="ITextureSink.OnLayerEvicted"/>), and it's streamed again when it nears the view. A freed
/// layer isn't written until the frame after the grid has stopped showing it.</item>
/// </list>
/// </summary>
public sealed class TextureStreamer : IDisposable
{
    public const int LargeSize = TextureDerivatives.Size;
    public const int SmallSize = TextureDerivatives.Size / 2;
    public const Image.Format DerivativeFormat = Image.Format.BptcRgba;

    /// <summary>POC: the layers' format when the sources are read directly (no runtime BC7 encoder in exports).</summary>
    public const Image.Format DirectFormat = Image.Format.Rgba8;

    /// <summary>POC: the largest source image a worker reads.</summary>
    private const long MaxSourceBytes = 64L * 1024 * 1024;

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

    /// <summary>POC: a request takes a busy layer only from one at least this many rows farther from the view.</summary>
    private const float StealMarginRows = 1.0f;

    /// <summary>POC: how often a worker looks again while requests wait for layers (the view moves; nothing pulses).</summary>
    private const int StarvedWaitMs = 30;

    /// <summary>POC: a layer no upload has to wait for.</summary>
    private const int NotHeld = int.MinValue;

    /// <summary>
    /// POC: frames a layer stays unwritten after the grid stops sampling it. The GPU can still be drawing earlier
    /// frames that sample it (Godot queues 2 frames, with 3 swapchain images), and writing it then means uploading into
    /// a texture the GPU is reading. Every crash of the Deck's AMD driver in this spike came seconds after a run that
    /// did that constantly (a full pool, with 1 frame of hold).
    /// </summary>
    private const int InFlightFrames = 4;

    private static readonly long Bc7SmallChainBytes = ChainBytes(SmallSize, DerivativeFormat);

    private readonly bool _direct;
    private readonly long _largeLayerBytes;
    private readonly long _smallLayerBytes;
    private readonly object _gate = new();
    private string _cacheDir = string.Empty;
    private string _mediaDir = string.Empty;

    // Per request unit: cell × Channels + channel.
    private readonly int[] _state;
    private readonly int[] _generation;
    private readonly int[] _row;
    private readonly bool[] _large;
    private readonly int[] _layer;           // the allocated layer, or -1 (under the gate)
    private readonly int[] _shownLayer;      // main thread: the layer the grid shows for the unit, or -1
    private readonly int[] _evictedLayer;    // a shown layer a worker took, for the main thread to retire, or -1
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

    // POC: each class's layer pool (0 = 512², 1 = 256²), under the gate. A layer's owner is a unit or -1. A layer
    // freed, or taken from a shown unit, isn't uploaded into until _frame > its hold (int.MaxValue until the main
    // thread has retired the shown unit).
    private readonly int _largePool;
    private readonly int _smallPool;
    private readonly int[][] _owner = [[], []];
    private readonly int[][] _free = [[], []];
    private readonly int[][] _hold = [[], []];
    private readonly int[] _freeCount = new int[2];
    private readonly int[] _peakInUse = new int[2];
    private int _frame;
    private bool _evictionsPending;

    // POC: a pooled class's array is built by a worker when its first request arrives (a layout's slots that the shown
    // games have no media for cost nothing), then installed by the main thread. Under the gate.
    private readonly int[] _lazyLayers = new int[2];
    private readonly bool[] _building = new bool[2];
    private readonly Texture2DArray?[] _built = new Texture2DArray?[2];
    private bool _builtPending;
    private int _arraysVersion;
    private bool _stopping;
    private float _viewRow;
    private float _direction = 1;
    private int _reportedMissing;

    // Statistics for the bench: written by workers under the gate or by the main thread.
    private readonly double[] _decodeMs = new double[StatsCapacity];
    private readonly double[] _uploadMs = new double[StatsCapacity];

    /// <summary>Starts the workers. <see cref="SetFolders"/> must be called before the first request.</summary>
    /// <param name="directSources">POC: read the media folder's images instead of their baked derivatives.</param>
    /// <param name="largePool">POC: the 512² layers shared by every cell; 0 keeps one per cell and channel.</param>
    /// <param name="smallPool">POC: the 256² layers shared by every cell; 0 keeps one per cell and channel.</param>
    public TextureStreamer(int cells, int workers, bool directSources = false, int largePool = 0, int smallPool = 0)
    {
        Cells = cells;
        _direct = directSources;
        _largePool = largePool;
        _smallPool = smallPool;
        Format = directSources ? DirectFormat : DerivativeFormat;
        _largeLayerBytes = ChainBytes(LargeSize, Format);
        _smallLayerBytes = ChainBytes(SmallSize, Format);
        var units = cells * Channels;
        _state = new int[units];
        _generation = new int[units];
        _row = new int[units];
        _large = new bool[units];
        _layer = new int[units];
        _shownLayer = new int[units];
        _evictedLayer = new int[units];
        Array.Fill(_layer, -1);
        Array.Fill(_shownLayer, -1);
        Array.Fill(_evictedLayer, -1);
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

    /// <summary>
    /// Where derivatives and their sources (the media folder, which settings can move) are. Main thread, before any
    /// request, and again when the media folder moves.
    /// </summary>
    public void SetFolders(string cacheDir, string mediaDir)
    {
        lock (_gate)
        {
            _cacheDir = cacheDir;
            _mediaDir = mediaDir;
        }
    }

    /// <summary>A3: <c>clamp(ProcessorCount / 4, 1, 4)</c>, which is 2 on the Deck.</summary>
    public static int DefaultWorkers => Math.Clamp(System.Environment.ProcessorCount / 4, 1, 4);

    /// <summary>Pool cells.</summary>
    public int Cells { get; }

    /// <summary>The layers' format: BC7 from derivatives, or RGBA8 from the sources themselves (POC).</summary>
    public Image.Format Format { get; }

    /// <summary>The slot channels requests are for.</summary>
    public SlotLayout Layout { get; private set; } = SlotLayout.Empty;

    /// <summary>The cover-class layers (512²); null while evicted or unused.</summary>
    public Texture2DArray? Large => _largeArray;

    /// <summary>Every other slot's layers (256²); null while evicted or unused.</summary>
    public Texture2DArray? Small => _smallArray;

    /// <summary>
    /// Whether the arrays the layout needs exist, or will be built on first demand (POC); not while a game runs, or
    /// before they're built.
    /// </summary>
    public bool HasArrays => (Layout.LargeCount == 0 || _largeArray is not null || _lazyLayers[0] > 0)
        && (Layout.SmallCount == 0 || _smallArray is not null || _lazyLayers[1] > 0);

    public int Uploads { get; private set; }

    public int Decodes { get; private set; }

    public int FramesAtBudget { get; private set; }

    public int FramesAtCap { get; private set; }

    public int MissingCount { get; private set; }

    public int Failures { get; private set; }

    public int Discarded { get; private set; }

    /// <summary>POC: layers taken from a request farther from the view (shown, or waiting to be uploaded).</summary>
    public int Evictions { get; private set; }

    /// <summary>POC: the most layers of each class in use at once since the last install.</summary>
    public (int Large, int Small) PeakLayersInUse => (_peakInUse[0], _peakInUse[1]);

    /// <summary>POC, for the bench log: per class, the layers by their owner's state, blocked layers, and waiting requests.</summary>
    public string PoolReport()
    {
        lock (_gate)
        {
            var text = new System.Text.StringBuilder();
            var centre = Volatile.Read(ref _viewRow);
            for (var c = 0; c < 2; c++)
            {
                int free = _freeCount[c], loading = 0, ready = 0, idle = 0, other = 0, blocked = 0, pending = 0;
                float nearestPending = float.MaxValue, farthestOwner = float.MinValue;
                for (var layer = 0; layer < _owner[c].Length; layer++)
                {
                    if (_hold[c][layer] == int.MaxValue)
                    {
                        blocked++;
                    }

                    var owner = _owner[c][layer];
                    if (owner < 0)
                    {
                        continue;
                    }

                    farthestOwner = Math.Max(farthestOwner, MathF.Abs(_row[owner] - centre));
                    switch (_state[owner])
                    {
                        case Loading: loading++; break;
                        case Ready: ready++; break;
                        case Idle: idle++; break;
                        default: other++; break;
                    }
                }

                for (var unit = 0; unit < _state.Length; unit++)
                {
                    if (_state[unit] == Pending && (_large[unit] ? 0 : 1) == c)
                    {
                        pending++;
                        nearestPending = Math.Min(nearestPending, MathF.Abs(_row[unit] - centre));
                    }
                }

                text.Append(FormattableString.Invariant(
                    $"{(c == 0 ? "512²" : "256²")}: {_owner[c].Length} layers, free {free}, owners loading {loading} ready {ready} shown {idle} other {other}, blocked {blocked}; pending {pending}, nearest pending {nearestPending:0.0} rows, farthest owner {farthestOwner:0.0} rows. "));
            }

            return text.ToString();
        }
    }

    /// <summary>Main thread: the layer the grid samples for a cell's channel (0 when none is shown).</summary>
    public int ShownLayer(int cell, int channel) => Math.Max(0, _shownLayer[cell * Channels + channel]);

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
    /// A blank array of <paramref name="layers"/> layers with mips, in the streamer's format. Creation can stall the
    /// main thread for tens of milliseconds (M1), so it's done at boot, or on a worker thread, never while browsing.
    /// </summary>
    public Texture2DArray? CreateArray(int size, int layers)
    {
        if (layers <= 0)
        {
            return null;
        }

        using var blank = Image.CreateEmpty(size, size, true, Format);
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
    /// <remarks>POC: a pooled class's array isn't built here unless it can be reused: a worker builds it on first demand.</remarks>
    public (Texture2DArray? Large, Texture2DArray? Small) BuildArrays(SlotLayout layout, Texture2DArray? currentLarge, Texture2DArray? currentSmall)
    {
        var largeLayers = LayersFor(layout, large: true);
        var smallLayers = LayersFor(layout, large: false);
        var large = largeLayers == 0 ? null
            : currentLarge is not null && currentLarge.GetLayers() == largeLayers ? currentLarge
            : _largePool > 0 ? null
            : Warm(CreateArray(LargeSize, largeLayers), LargeSize);
        var small = smallLayers == 0 ? null
            : currentSmall is not null && currentSmall.GetLayers() == smallLayers ? currentSmall
            : _smallPool > 0 ? null
            : Warm(CreateArray(SmallSize, smallLayers), SmallSize);
        return (large, small);
    }

    /// <summary>A class's layers: one per cell and channel, or the pool's size if that's smaller (POC).</summary>
    public int LayersFor(SlotLayout layout, bool large)
    {
        var whole = Cells * (large ? layout.LargeCount : layout.SmallCount);
        var pool = large ? _largePool : _smallPool;
        return pool > 0 ? Math.Min(whole, pool) : whole;
    }

    private Texture2DArray? Warm(Texture2DArray? array, int size)
    {
        if (array is not null)
        {
            using var blank = Image.CreateEmpty(size, size, true, Format);
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
        SetArrays(large, small);
        GD.Print(FormattableString.Invariant($"Textures: layers for {layout}: {large?.GetLayers() ?? 0} × {LargeSize}² and {small?.GetLayers() ?? 0} × {SmallSize}² now, {ArrayMiB(large, LargeSize) + ArrayMiB(small, SmallSize):0.0} MiB of {Format}; on demand {_lazyLayers[0]} and {_lazyLayers[1]} ({Cells} cells; pools {_largePool}, {_smallPool})."));
    }

    /// <summary>
    /// Main thread, with no request holding a layer: the arrays in use, each class's pool fitted to its array, and a
    /// missing array that the layout needs left to be built on first demand.
    /// </summary>
    private void SetArrays(Texture2DArray? large, Texture2DArray? small)
    {
        _largeArray = large;
        _smallArray = small;
        lock (_gate)
        {
            _arraysVersion++;
            for (var c = 0; c < 2; c++)
            {
                _built[c]?.Dispose();
                _built[c] = null;
            }

            _builtPending = false;
            ResetPool(0, large?.GetLayers() ?? 0);
            ResetPool(1, small?.GetLayers() ?? 0);
            _lazyLayers[0] = large is null ? LayersFor(Layout, large: true) : 0;
            _lazyLayers[1] = small is null ? LayersFor(Layout, large: false) : 0;
        }
    }

    /// <summary>
    /// Main thread: installs arrays workers built on first demand, and points the grid's materials at them. Workers
    /// can then give their requests layers.
    /// </summary>
    private void InstallBuilt(ITextureSink sink)
    {
        lock (_gate)
        {
            _builtPending = false;
            for (var c = 0; c < 2; c++)
            {
                if (_built[c] is not { } array)
                {
                    continue;
                }

                _built[c] = null;
                if (c == 0)
                {
                    _largeArray = array;
                }
                else
                {
                    _smallArray = array;
                }

                ResetPool(c, array.GetLayers());
                _lazyLayers[c] = 0;
                GD.Print(FormattableString.Invariant($"Textures: {array.GetLayers()} × {(c == 0 ? LargeSize : SmallSize)}² layers built on first demand ({ArrayMiB(array, c == 0 ? LargeSize : SmallSize):0.0} MiB)."));
            }

            Monitor.PulseAll(_gate);
        }

        sink.OnArraysChanged();
    }

    /// <summary>Under the gate: a pooled class whose array a waiting request needs and no worker is building, or -1.</summary>
    private int ArrayToBuild()
    {
        for (var c = 0; c < 2; c++)
        {
            if (_lazyLayers[c] > 0 && !_building[c] && _built[c] is null && AnyPending(c))
            {
                return c;
            }
        }

        return -1;
    }

    /// <summary>A worker: builds and warms a class's array (tens of milliseconds) for the main thread to install.</summary>
    private void BuildOnDemand(int c, int layers, int version)
    {
        var size = c == 0 ? LargeSize : SmallSize;
        var array = Warm(CreateArray(size, layers), size);
        lock (_gate)
        {
            _building[c] = false;
            if (array is not null && version == _arraysVersion && _lazyLayers[c] == layers)
            {
                _built[c] = array;
                _builtPending = true;
                return;
            }
        }

        array?.Dispose();
    }

    /// <summary>Under the gate: whether any request of the class is waiting.</summary>
    private bool AnyPending(int c)
    {
        for (var unit = 0; unit < _state.Length; unit++)
        {
            if (_state[unit] == Pending && (_large[unit] ? 0 : 1) == c)
            {
                return true;
            }
        }

        return false;
    }

    private double ArrayMiB(Texture2DArray? array, int size) => (array?.GetLayers() ?? 0) * ChainBytes(size, Format) / (1024.0 * 1024.0);

    /// <summary>Under the gate: every layer of the class free (no unit holds one after <see cref="DropAll"/>).</summary>
    private void ResetPool(int c, int layers)
    {
        if (_owner[c].Length != layers)
        {
            _owner[c] = new int[layers];
            _free[c] = new int[layers];
            _hold[c] = new int[layers];
        }

        for (var i = 0; i < layers; i++)
        {
            _owner[c][i] = -1;
            _free[c][i] = layers - 1 - i;
            _hold[c][i] = NotHeld;
        }

        _freeCount[c] = layers;
        _peakInUse[c] = 0;
    }

    /// <summary>
    /// Main thread, at boot: the cover-class array for a whole pool, before the theme's layout is known. Every game
    /// template has a cover (A7), so it's nearly always needed, and making it now overlaps the DB opening.
    /// </summary>
    public void CreateBootArray() => _largeArray ??= CreateArray(LargeSize, _largePool > 0 ? Math.Min(Cells, _largePool) : Cells);

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
                using var blank = Image.CreateEmpty(size, size, true, Format);
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
        _smallArray?.Dispose();
        SetArrays(null, null);
        lock (_gate)
        {
            _lazyLayers[0] = 0;
            _lazyLayers[1] = 0;
        }
    }

    /// <summary>Main thread, after a game: recreates the layout's arrays (POC: pooled ones on first demand, by a worker).</summary>
    public void Restore()
    {
        var (large, small) = BuildArrays(Layout, _largeArray, _smallArray);
        SetArrays(large, small);
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
        _shownLayer[unit] = -1;
        lock (_gate)
        {
            DropResult(unit);
            ReleaseLayer(unit);
            ForgetEviction(unit);
            _generation[unit]++;
            _row[unit] = row;
            _large[unit] = Layout.IsLarge(channel);
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
        _shownLayer[unit] = -1;
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
                _shownLayer[unit] = -1;
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
        Volatile.Write(ref _frame, _frame + 1);
        if (Volatile.Read(ref _builtPending))
        {
            InstallBuilt(sink);
        }

        if (Volatile.Read(ref _evictionsPending))
        {
            RetireEvicted(sink);
        }

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
            var bytes = large ? _largeLayerBytes : _smallLayerBytes;
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

                // A layer freed or taken lately may still be sampled by a frame the GPU hasn't finished: wait it out.
                layer = _layer[unit];
                if (layer < 0 || _hold[large ? 0 : 1][layer] >= _frame)
                {
                    continue;
                }

                image = _result[unit];
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
            _shownLayer[unit] = layer;
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
        _built[0]?.Dispose();
        _built[1]?.Dispose();
    }

    /// <summary>
    /// Main thread: the grid stops showing the layers workers took from shown units, and each may be written from the
    /// next frame on (once the grid's slot state, now showing the fallback, is on the GPU).
    /// </summary>
    private void RetireEvicted(ITextureSink sink)
    {
        Volatile.Write(ref _evictionsPending, false);
        for (var unit = 0; unit < _state.Length; unit++)
        {
            int layer;
            lock (_gate)
            {
                layer = _evictedLayer[unit];
                if (layer < 0)
                {
                    continue;
                }

                _evictedLayer[unit] = -1;
                _hold[_large[unit] ? 0 : 1][layer] = _frame + InFlightFrames;
            }

            if (_shownLayer[unit] == layer)
            {
                _shownLayer[unit] = -1;
                sink.OnLayerEvicted(unit / Channels, unit % Channels);
            }
        }
    }

    /// <summary>
    /// Under the gate: the unit's layer back to its pool. A main-thread release (a re-bind or cancel) comes before the
    /// grid's slot state is uploaded in this frame's tick, or during this frame's uploads; either way the layer is
    /// written from the next upload pass that is safe (see the hold check in <see cref="PumpUploads"/>).
    /// </summary>
    private void ReleaseLayer(int unit)
    {
        var layer = _layer[unit];
        if (layer < 0)
        {
            return;
        }

        var c = _large[unit] ? 0 : 1;
        _layer[unit] = -1;
        if (layer < _owner[c].Length && _owner[c][layer] == unit)
        {
            _owner[c][layer] = -1;
            _free[c][_freeCount[c]++] = layer;
            if (_hold[c][layer] != int.MaxValue)
            {
                _hold[c][layer] = Math.Max(_hold[c][layer], Volatile.Read(ref _frame) + InFlightFrames);
            }
        }
    }

    /// <summary>
    /// Under the gate, from the main thread re-binding or cancelling the unit (the grid has stopped showing it first):
    /// a layer taken from it and not yet retired needn't wait for <see cref="RetireEvicted"/> any longer.
    /// </summary>
    private void ForgetEviction(int unit)
    {
        var layer = _evictedLayer[unit];
        if (layer < 0)
        {
            return;
        }

        _evictedLayer[unit] = -1;
        var hold = _hold[_large[unit] ? 0 : 1];
        if (layer < hold.Length)
        {
            hold[layer] = Volatile.Read(ref _frame) + InFlightFrames;
        }
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
        ReleaseLayer(unit);
        ForgetEviction(unit);
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
            var unit = -1;
            int generation;
            string relPath;
            string cacheDir;
            string mediaDir;
            long size;
            long mtime;
            bool large;
            var build = -1;
            var buildLayers = 0;
            var buildVersion = 0;
            lock (_gate)
            {
                var starved = false;
                while (!_stopping && (build = ArrayToBuild()) < 0 && (unit = PickNearest(out starved)) < 0)
                {
                    // Requests waiting for a layer may win one as the view moves, which nothing signals.
                    Monitor.Wait(_gate, starved ? StarvedWaitMs : Timeout.Infinite);
                }

                if (_stopping)
                {
                    return;
                }

                if (build >= 0)
                {
                    // POC: a pooled class's array, wanted for the first time.
                    _building[build] = true;
                    buildLayers = _lazyLayers[build];
                    buildVersion = _arraysVersion;
                    generation = 0;
                    relPath = cacheDir = mediaDir = string.Empty;
                    size = mtime = 0;
                    large = false;
                }
                else
                {
                    _state[unit] = Loading;
                    generation = _generation[unit];
                    relPath = _relPath[unit]!;
                    cacheDir = _cacheDir;
                    mediaDir = _mediaDir;
                    size = _size[unit];
                    mtime = _mtime[unit];
                    large = _large[unit];
                }
            }

            if (build >= 0)
            {
                BuildOnDemand(build, buildLayers, buildVersion);
                continue;
            }

            var start = Stopwatch.GetTimestamp();
            Image? image = null;
            var failed = false;
            try
            {
                // From the indexed size and time when the library has them (one string, no file access); otherwise from
                // the source file, once per game.
                string? path;
                if (_direct)
                {
                    // POC: the source image itself, wherever the media folder is.
                    path = MediaFolder.FullPath(mediaDir, relPath);
                }
                else if (size > 0)
                {
                    path = TextureDerivatives.PathFor(cacheDir, relPath, size, mtime);
                }
                else if (!_derivativePaths.TryGetValue(relPath, out path))
                {
                    path = TextureDerivatives.PathFor(cacheDir, mediaDir, relPath);
                    _derivativePaths[relPath] = path;
                }

                if (path is not null)
                {
                    image = _direct ? DecodeSource(path, ref buffer, large) : Decode(path, ref buffer, large);
                    failed = image is null && File.Exists(path);
                }

                if (image is null && Interlocked.Increment(ref _reportedMissing) == 1)
                {
                    var why = _direct
                        ? failed ? "it didn't decode as a PNG, JPEG or WebP" : "the source is missing"
                        : path is null ? "the source is missing" : failed ? "it didn't decode as a 512² BC7 DDS with mips" : "not baked yet";
                    GD.Print($"Textures: no usable {(_direct ? "source image" : "derivative")} for {relPath} ({why}: {path}); its slot falls back down its chain. Further misses aren't logged.");
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
                    if (image is null)
                    {
                        ReleaseLayer(unit);
                    }
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
                || image.GetFormat() != DerivativeFormat
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

        image.SetData(SmallSize, SmallSize, true, DerivativeFormat, chain);
        return image;
    }

    /// <summary>
    /// POC: reads a source image (PNG, JPEG or WebP, told apart by its first bytes) into the worker's buffer, decodes
    /// it into a pooled image, squeezes the whole image to the layer's square (as a derivative does, so the shader's crop
    /// by the media's aspect still applies) and builds its mips. Null if there's no such file or it doesn't decode.
    /// </summary>
    private Image? DecodeSource(string path, ref byte[] buffer, bool large)
    {
        if (!TryReadFile(path, ref buffer, MaxSourceBytes, out var read))
        {
            return null;
        }

        var data = buffer.AsSpan(0, read);
        var image = TakeImage();
        var error = data switch
        {
            [0x89, (byte)'P', (byte)'N', (byte)'G', ..] => image.LoadPngFromBuffer(data),
            [0xFF, 0xD8, 0xFF, ..] => image.LoadJpgFromBuffer(data),
            [(byte)'R', (byte)'I', (byte)'F', (byte)'F', _, _, _, _, (byte)'W', (byte)'E', (byte)'B', (byte)'P', ..] => image.LoadWebpFromBuffer(data),
            _ => Error.FileUnrecognized,
        };

        if (error != Error.Ok || image.IsEmpty())
        {
            Recycle(image);
            return null;
        }

        if (image.GetFormat() != DirectFormat)
        {
            image.Convert(DirectFormat);
        }

        var size = large ? LargeSize : SmallSize;
        image.Resize(size, size, Image.Interpolation.Lanczos);
        image.GenerateMipmaps();
        return image;
    }

    /// <summary>Reads a whole file into the worker's buffer (growing it if need be). False if it's missing or too big.</summary>
    private static bool TryReadFile(string path, ref byte[] buffer, long maxBytes, out int read)
    {
        read = 0;
        SafeFileHandle handle;
        try
        {
            handle = File.OpenHandle(path, FileMode.Open, System.IO.FileAccess.Read, FileShare.Read, FileOptions.SequentialScan);
        }
        catch (FileNotFoundException)
        {
            return false;
        }
        catch (DirectoryNotFoundException)
        {
            return false;
        }

        using var file = handle;
        var length = RandomAccess.GetLength(file);
        if (length > maxBytes)
        {
            return false;
        }

        if (length > buffer.Length)
        {
            buffer = new byte[length];
        }

        while (read < length)
        {
            var n = RandomAccess.Read(file, buffer.AsSpan(read, (int)length - read), read);
            if (n == 0)
            {
                break;
            }

            read += n;
        }

        return true;
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
        if (format is not (98 or 99) || dds.Length < start + Bc7SmallChainBytes)
        {
            return false;
        }

        chain = dds.Slice(start, (int)Bc7SmallChainBytes);
        return true;
    }

    /// <summary>A request's distance from the view in rows: rows ahead of the scroll count as nearer, covers first.</summary>
    private float Score(int unit, float centre, float direction)
    {
        var d = _row[unit] - centre;
        return MathF.Abs(d) * (d * direction > 0 ? 0.6f : 1.0f) + (_large[unit] ? 0 : SmallSlotPenaltyRows) + unit * 0.00001f;
    }

    /// <summary>
    /// Under the gate: the pending request nearest the view that can have a layer, and gives it one: a free layer, or
    /// the layer of the farthest shown or waiting request of its class if that's <see cref="StealMarginRows"/> farther.
    /// -1 if none; <paramref name="starved"/> says whether requests are left waiting for layers.
    /// </summary>
    private int PickNearest(out bool starved)
    {
        starved = false;
        var centre = Volatile.Read(ref _viewRow);
        var direction = Volatile.Read(ref _direction);

        // Per class with no free layer: the farthest unit holding one it could give up (not one being decoded into).
        Span<int> victim = [-1, -1];
        Span<float> victimScore = [float.MinValue, float.MinValue];
        for (var c = 0; c < 2; c++)
        {
            if (_freeCount[c] > 0)
            {
                continue;
            }

            var owners = _owner[c];
            for (var layer = 0; layer < owners.Length; layer++)
            {
                var owner = owners[layer];
                if (owner < 0 || _state[owner] == Loading)
                {
                    continue;
                }

                var score = Score(owner, centre, direction);
                if (score > victimScore[c])
                {
                    victimScore[c] = score;
                    victim[c] = owner;
                }
            }
        }

        var best = -1;
        var bestScore = float.MaxValue;
        for (var unit = 0; unit < _state.Length; unit++)
        {
            if (_state[unit] != Pending)
            {
                continue;
            }

            var c = _large[unit] ? 0 : 1;
            var score = Score(unit, centre, direction);
            if (_freeCount[c] == 0 && (victim[c] < 0 || score + StealMarginRows >= victimScore[c]))
            {
                // Waiting for a layer (a class with no layers at all has no arrays, so nothing to wait for).
                starved |= _owner[c].Length > 0;
                continue;
            }

            if (score < bestScore)
            {
                bestScore = score;
                best = unit;
            }
        }

        if (best >= 0)
        {
            var c = _large[best] ? 0 : 1;
            if (_freeCount[c] == 0)
            {
                Evict(victim[c]);
            }

            // The free layer held the shortest (the GPU long done with it), rather than the one freed last.
            var free = _free[c];
            var pick = _freeCount[c] - 1;
            for (var i = 0; i < _freeCount[c]; i++)
            {
                if (_hold[c][free[i]] < _hold[c][free[pick]])
                {
                    pick = i;
                }
            }

            var layer = free[pick];
            free[pick] = free[--_freeCount[c]];
            _owner[c][layer] = best;
            _layer[best] = layer;
            _peakInUse[c] = Math.Max(_peakInUse[c], _owner[c].Length - _freeCount[c]);
        }

        return best;
    }

    /// <summary>
    /// Under the gate: takes a unit's layer for another request. The unit goes back to pending, to be streamed again
    /// when it's near enough; if it was uploaded (so the grid may show it) the layer is held until the main thread has
    /// retired it.
    /// </summary>
    private void Evict(int unit)
    {
        var c = _large[unit] ? 0 : 1;
        var layer = _layer[unit];
        DropResult(unit);
        _layer[unit] = -1;
        _owner[c][layer] = -1;
        _free[c][_freeCount[c]++] = layer;
        if (_state[unit] == Idle)
        {
            _hold[c][layer] = int.MaxValue;
            _evictedLayer[unit] = layer;
            _evictionsPending = true;
        }

        _generation[unit]++;
        _state[unit] = Pending;
        Evictions++;
    }

    /// <summary>
    /// A mip chain's bytes. BC7: 16 per 4×4 block, and mips below 4×4 still take one block. RGBA8 (POC): 4 per pixel.
    /// </summary>
    private static long ChainBytes(int size, Image.Format format)
    {
        long total = 0;
        for (var s = size; s >= 1; s /= 2)
        {
            total += format == DirectFormat ? (long)s * s * 4 : (long)Math.Max(1, s / 4) * Math.Max(1, s / 4) * 16;
        }

        return total;
    }
}
