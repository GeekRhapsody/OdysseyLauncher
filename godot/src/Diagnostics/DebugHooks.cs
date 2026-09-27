using System;
using System.IO;
using System.Runtime.InteropServices;
using Godot;
using Launcher.Core;
using Launcher.Core.Diagnostics;

namespace Launcher.App.Diagnostics;

/// <summary>
/// Autoload implementing the <c>--capture</c> and <c>--bench</c> debug facilities, driven by user
/// arguments (after <c>--</c> or <c>++</c>). Both need a windowed run, because headless mode doesn't
/// render. With no debug arguments it only records the first-frame mark, then unhooks itself.
/// </summary>
public partial class DebugHooks : Node
{
    private const int ExitOk = 0;
    private const int ExitFailed = 1;
    private const int ExitBadArguments = 2;
    private const double AssumedRefreshHz = 60.0;

    // Watchdog, so a run that stops drawing (e.g. a minimised window) can't hang forever:
    // 30 s plus 100 ms per requested frame, i.e. it tolerates 10 fps.
    private const ulong WatchdogBaseMs = 30_000;
    private const ulong WatchdogPerFrameMs = 100;

    private DebugOptions _options = DebugOptions.None;
    private bool _hooked;
    private bool _finished;
    private bool _captureDone = true;
    private bool _benchDone = true;
    private int _exitCode = ExitOk;
    private int _framesDrawn;
    private ulong _deadlineMs;

    // Bench samples live in arrays sized up front, so sampling never allocates.
    private Rid _viewport;
    private double[] _intervalsMs = [];
    private double[] _cpuMs = [];
    private double[] _gpuMs = [];
    private int _samples;
    private ulong _lastFrameUsec;
    private GcSnapshot _gcAtStart;

    /// <summary>Startup marks in milliseconds since the OS created the process.</summary>
    public static StartupTimeline Timeline { get; } = StartupTimeline.ForCurrentProcess();

    public override void _EnterTree()
    {
        // Godot's tick clock starts when the engine initialises, so it dates the engine start.
        var sinceProcessStartMs = Timeline.ElapsedMs;
        Timeline.MarkAt(StartupMarks.EngineStart, sinceProcessStartMs - Time.GetTicksUsec() / 1000.0);
        Timeline.MarkAt(StartupMarks.AutoloadEnterTree, sinceProcessStartMs);

        // The start-up target covers our code only and is timed from this mark, so it must come first.
        if (GetIndex() != 0)
        {
            GD.PushWarning("DebugHooks isn't the first autoload, so app_startup_ms misses code that ran before it. Move it to the top of the autoload list.");
        }

        var parsed = DebugOptions.Parse(OS.GetCmdlineUserArgs());
        if (!parsed.IsValid)
        {
            foreach (var error in parsed.Errors)
            {
                GD.PrintErr($"Debug arguments: {error}");
            }

            Finish(ExitBadArguments);
            return;
        }

        _options = parsed.Options;
        if (_options.IsActive && DisplayServer.GetName() == "headless")
        {
            GD.PrintErr("--capture and --bench need a windowed run; headless mode doesn't render.");
            Finish(ExitFailed);
            return;
        }

        RenderingServer.FramePostDraw += OnFramePostDraw;
        _hooked = true;
        if (!_options.IsActive)
        {
            return;
        }

        _captureDone = !_options.CaptureRequested;
        _benchDone = !_options.BenchRequested;
        if (_options.BenchRequested)
        {
            _intervalsMs = new double[_options.BenchFrames];
            _cpuMs = new double[_options.BenchFrames];
            _gpuMs = new double[_options.BenchFrames];
            _viewport = GetViewport().GetViewportRid();
            RenderingServer.ViewportSetMeasureRenderTime(_viewport, true);
        }

        var frames = Math.Max(
            _options.CaptureRequested ? _options.CaptureFrame : 0,
            _options.BenchRequested ? _options.BenchFrames + 1 : 0);
        _deadlineMs = Time.GetTicksMsec() + WatchdogBaseMs + (ulong)frames * WatchdogPerFrameMs;
        ProcessMode = ProcessModeEnum.Always;
    }

    public override void _Ready()
    {
        // Godot enables processing at READY for scripts that define _Process; only the watchdog needs it.
        SetProcess(_options.IsActive && !_finished);
    }

    public override void _ExitTree()
    {
        Unhook();
    }

    public override void _Process(double delta)
    {
        if (!_finished && Time.GetTicksMsec() > _deadlineMs)
        {
            GD.PrintErr($"Debug facilities timed out after {_framesDrawn} drawn frames. Is the window minimised?");
            Finish(ExitFailed);
        }
    }

    private void OnFramePostDraw()
    {
        var nowUsec = Time.GetTicksUsec();
        _framesDrawn++;
        if (_framesDrawn == 1)
        {
            Timeline.Mark(StartupMarks.FirstFrameDrawn);
        }

        if (!_options.IsActive)
        {
            Unhook();
            return;
        }

        if (_finished)
        {
            return;
        }

        if (!_benchDone)
        {
            SampleBench(nowUsec);
        }

        if (!_captureDone && _framesDrawn >= _options.CaptureFrame)
        {
            Capture();
        }

        _lastFrameUsec = nowUsec;
        if (_captureDone && _benchDone)
        {
            Finish(_exitCode);
        }
    }

    private void SampleBench(ulong nowUsec)
    {
        // Intervals are measured from the first drawn frame onwards.
        if (_framesDrawn == 1)
        {
            _gcAtStart = GcSnapshot.Take();
            return;
        }

        var i = _samples++;
        _intervalsMs[i] = (nowUsec - _lastFrameUsec) / 1000.0;
        _cpuMs[i] = RenderingServer.ViewportGetMeasuredRenderTimeCpu(_viewport);
        _gpuMs[i] = RenderingServer.ViewportGetMeasuredRenderTimeGpu(_viewport);
        if (_samples == _intervalsMs.Length)
        {
            WriteBench();
            _benchDone = true;
        }
    }

    private void Capture()
    {
        _captureDone = true;
        var path = _options.CapturePath!;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            using var image = GetViewport().GetTexture().GetImage();
            var error = image.SavePng(path);
            if (error != Error.Ok)
            {
                GD.PrintErr($"--capture couldn't write {path}: {error}.");
                _exitCode = ExitFailed;
                return;
            }

            GD.Print($"Captured frame {_framesDrawn} to {path}");
        }
        catch (Exception exception)
        {
            GD.PrintErr($"--capture failed: {exception.Message}");
            _exitCode = ExitFailed;
        }
    }

    private void WriteBench()
    {
        var gcAtEnd = GcSnapshot.Take();
        var path = _options.BenchPath!;
        try
        {
            var reportedHz = DisplayServer.ScreenGetRefreshRate();
            var refreshAssumed = !(reportedHz > 0);
            var refreshHz = refreshAssumed ? AssumedRefreshHz : reportedHz;
            var windowSize = DisplayServer.WindowGetSize();

            var report = new BenchReport
            {
                CreatedUtc = DateTimeOffset.UtcNow,
                AppVersion = CoreInfo.InformationalVersionOf(typeof(DebugHooks).Assembly),
                GodotVersion = Engine.GetVersionInfo()["string"].AsString(),
                DotnetVersion = RuntimeInformation.FrameworkDescription,
                Machine = new BenchMachine(
                    $"{OS.GetName()} {OS.GetVersion()}",
                    OS.GetProcessorName(),
                    RenderingServer.GetVideoAdapterName(),
                    RenderingServer.GetCurrentRenderingMethod(),
                    RenderingServer.GetCurrentRenderingDriverName()),
                Display = new BenchDisplay(
                    refreshHz,
                    refreshAssumed,
                    windowSize.X,
                    windowSize.Y,
                    DisplayServer.WindowGetVsyncMode().ToString(),
                    Headless: false),
                AppStartupMs = Timeline.Between(StartupMarks.AutoloadEnterTree, StartupMarks.Interactive),
                StartupMs = Timeline.ToDictionary(),
                Frames = FrameTimeStats.Compute(_intervalsMs, refreshHz),
                RenderMs = new BenchRenderTimes(FrameTimeStats.Mean(_cpuMs), FrameTimeStats.Mean(_gpuMs)),
                Gc = new BenchGc(
                    gcAtEnd.Gen0 - _gcAtStart.Gen0,
                    gcAtEnd.Gen1 - _gcAtStart.Gen1,
                    gcAtEnd.Gen2 - _gcAtStart.Gen2,
                    (gcAtEnd.Pause - _gcAtStart.Pause).TotalMilliseconds,
                    gcAtEnd.Allocated - _gcAtStart.Allocated,
                    gcAtEnd.MainThreadAllocated - _gcAtStart.MainThreadAllocated),
            };

            BenchReportWriter.Write(path, report);
            GD.Print($"Bench report written to {path}");
        }
        catch (Exception exception)
        {
            GD.PrintErr($"--bench failed: {exception.Message}");
            _exitCode = ExitFailed;
        }
    }

    private void Finish(int exitCode)
    {
        _finished = true;
        Unhook();
        SetProcess(false);
        GetTree().Quit(exitCode);
    }

    private void Unhook()
    {
        if (_hooked)
        {
            _hooked = false;
            RenderingServer.FramePostDraw -= OnFramePostDraw;
        }
    }

    /// <summary>GC counters, read on the main thread so the per-thread allocation figure is the main thread's.</summary>
    private readonly record struct GcSnapshot(
        int Gen0,
        int Gen1,
        int Gen2,
        TimeSpan Pause,
        long Allocated,
        long MainThreadAllocated)
    {
        public static GcSnapshot Take() => new(
            GC.CollectionCount(0),
            GC.CollectionCount(1),
            GC.CollectionCount(2),
            GC.GetTotalPauseDuration(),
            GC.GetTotalAllocatedBytes(precise: true),
            GC.GetAllocatedBytesForCurrentThread());
    }
}
