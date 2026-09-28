using System;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Screens;
using Launcher.App.Textures;
using Launcher.Core.Diagnostics;

namespace Launcher.App.Diagnostics;

/// <summary>
/// <c>--bench-scenario=scroll</c>: enters a system (the biggest, unless <c>--bench-system</c> names one), waits for
/// its first screen of covers (or 3 s), then scrolls from the first row to the last at a steady speed over
/// <c>--bench-scroll-seconds</c>, with the focus following the row at the focus line. It measures the scroll
/// frames alone, the share of on-screen covers shown, and the main thread's allocations, then hands the results
/// to <see cref="DebugHooks"/>, which writes the report.
/// </summary>
public sealed class ScrollBench : IDisposable
{
    private const double SettleTimeoutSeconds = 3;
    private const double SettleAfterTexturedSeconds = 0.5;

    private readonly Navigator _navigator;
    private readonly TextureStreamer? _streamer;
    private readonly DebugOptions _options;
    private readonly string? _system;
    private readonly int _systemGames;
    private readonly int _systems;
    private readonly int _games;
    private readonly double[] _intervals;
    private int _samples;
    private Phase _phase = Phase.Entering;
    private double _elapsed;
    private ulong _enteredUsec;
    private double? _visibleTexturedMs;
    private ulong _lastFrameUsec;
    private bool _hooked;
    private int _rows;
    private double _texturedSum;
    private double _texturedMin = 1;
    private int _texturedFrames;
    private long _allocatedAtStart;
    private int _gen0;
    private int _gen1;
    private int _gen2;
    private int _uploadsAtStart;

    public ScrollBench(Navigator navigator, TextureStreamer? streamer, DebugOptions options, AppServices services)
    {
        _navigator = navigator;
        _streamer = streamer;
        _options = options;
        _intervals = new double[(int)(options.BenchScrollSeconds * 250) + 1000];
        _systems = services.Systems.Count + 2;
        var biggest = 0;
        foreach (var system in services.Systems)
        {
            _games += system.GameCount;
            if (options.BenchSystem is null ? system.GameCount > biggest : system.SystemId == options.BenchSystem)
            {
                biggest = system.GameCount;
                _system = system.SystemId;
                _systemGames = system.GameCount;
            }
        }

        if (_system is null || _systemGames == 0 || !navigator.EnterSystem(_system))
        {
            DebugHooks.FailScroll(_system is null ? $"there's no system '{options.BenchSystem}'" : $"{_system} has no games to scroll");
            _phase = Phase.Done;
        }
    }

    private enum Phase
    {
        Entering,
        Settling,
        Scrolling,
        Done,
    }

    /// <summary>Main thread, each frame, before the grids tick.</summary>
    public void Update(double delta)
    {
        var grid = _navigator.GamesGrid;
        switch (_phase)
        {
            case Phase.Entering:
                if (_navigator.InGames)
                {
                    _phase = Phase.Settling;
                    _elapsed = 0;
                    _enteredUsec = Time.GetTicksUsec();
                }

                return;

            case Phase.Settling:
                _elapsed += delta;
                if (_visibleTexturedMs is null && grid.VisibleTextured && grid.AnyVisibleArt)
                {
                    _visibleTexturedMs = (Time.GetTicksUsec() - _enteredUsec) / 1000.0;
                    _elapsed = Math.Max(_elapsed, SettleTimeoutSeconds - SettleAfterTexturedSeconds);
                }

                if (_elapsed >= SettleTimeoutSeconds)
                {
                    StartScrolling(grid.Rows);
                }

                return;

            case Phase.Scrolling:
                _elapsed += delta;
                var t = Math.Min(1, _elapsed / _options.BenchScrollSeconds);
                var rowsPerSecond = (float)((_rows - 1) / _options.BenchScrollSeconds);
                grid.SetScrollDirect((float)(t * (_rows - 1)), rowsPerSecond);
                if (grid.AnyVisibleArt)
                {
                    _texturedSum += grid.VisibleTexturedFraction;
                    _texturedMin = Math.Min(_texturedMin, grid.VisibleTexturedFraction);
                    _texturedFrames++;
                }

                if (t >= 1)
                {
                    Finish();
                }

                return;
        }
    }

    private void StartScrolling(int rows)
    {
        _rows = Math.Max(rows, 2);
        _phase = Phase.Scrolling;
        _elapsed = 0;
        _allocatedAtStart = GC.GetAllocatedBytesForCurrentThread();
        _gen0 = GC.CollectionCount(0);
        _gen1 = GC.CollectionCount(1);
        _gen2 = GC.CollectionCount(2);
        _uploadsAtStart = _streamer?.Uploads ?? 0;
        _lastFrameUsec = Time.GetTicksUsec();
        _hooked = true;
        RenderingServer.FramePostDraw += OnFramePostDraw;
    }

    private void OnFramePostDraw()
    {
        var now = Time.GetTicksUsec();
        if (_samples < _intervals.Length)
        {
            _intervals[_samples++] = (now - _lastFrameUsec) / 1000.0;
        }

        _lastFrameUsec = now;
    }

    private void Finish()
    {
        _phase = Phase.Done;
        var allocated = GC.GetAllocatedBytesForCurrentThread() - _allocatedAtStart;
        Dispose();
        var refresh = DisplayServer.ScreenGetRefreshRate();
        var frames = FrameTimeStats.Compute(_intervals.AsSpan(0, _samples), refresh > 0 ? refresh : 60);
        var scroll = new BenchScroll(
            frames,
            _rows - 1,
            _options.BenchScrollSeconds,
            _texturedFrames > 0 ? _texturedSum / _texturedFrames : 0,
            _texturedFrames > 0 ? _texturedMin : 0,
            _visibleTexturedMs,
            allocated,
            GC.CollectionCount(0) - _gen0,
            GC.CollectionCount(1) - _gen1,
            GC.CollectionCount(2) - _gen2);

        BenchTextures? textures = null;
        if (_streamer is { } streamer)
        {
            var uploads = streamer.UploadSamples;
            var decodes = streamer.DecodeSamples;
            var uploadMax = 0.0;
            foreach (var ms in uploads)
            {
                uploadMax = Math.Max(uploadMax, ms);
            }

            var sorted = decodes.ToArray();
            Array.Sort(sorted);
            textures = new BenchTextures(
                streamer.Uploads - _uploadsAtStart,
                FrameTimeStats.Mean(uploads),
                uploadMax,
                streamer.Decodes,
                FrameTimeStats.Mean(decodes),
                sorted.Length > 0 ? FrameTimeStats.Percentile(sorted, 95) : 0,
                streamer.FramesAtBudget,
                streamer.FramesAtCap,
                streamer.MissingCount,
                streamer.Failures,
                streamer.Discarded);
        }

        GD.Print(FormattableString.Invariant(
            $"Scroll bench: {_system}, {_rows - 1} rows in {_options.BenchScrollSeconds} s: mean {frames.MeanMs:0.00} ms, p99 {frames.P99Ms:0.00} ms, {frames.HitchCount} hitches, textured {scroll.TexturedFractionMean:P1}, main thread allocated {allocated} B"));
        DebugHooks.CompleteScroll(scroll, textures, new BenchLibrary(_systems, _games, _system, _systemGames));
    }

    public void Dispose()
    {
        if (_hooked)
        {
            _hooked = false;
            RenderingServer.FramePostDraw -= OnFramePostDraw;
        }
    }
}
