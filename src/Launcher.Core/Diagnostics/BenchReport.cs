namespace Launcher.Core.Diagnostics;

/// <summary>The output of <c>--bench</c>. Written as snake_case JSON by <see cref="BenchReportWriter"/>.</summary>
public sealed record BenchReport
{
    public const int CurrentFormat = 1;

    public int Format { get; init; } = CurrentFormat;

    public required DateTimeOffset CreatedUtc { get; init; }

    /// <summary>The app's informational version, including the commit sha.</summary>
    public required string AppVersion { get; init; }

    public required string GodotVersion { get; init; }

    public required string DotnetVersion { get; init; }

    public required BenchMachine Machine { get; init; }

    public required BenchDisplay Display { get; init; }

    /// <summary>Startup marks in milliseconds since the OS created the process.</summary>
    public required IReadOnlyDictionary<string, double> StartupMs { get; init; }

    /// <summary>Frame intervals measured at <c>frame_post_draw</c> (not Godot's smoothed delta).</summary>
    public required FrameTimeSummary Frames { get; init; }

    public required BenchRenderTimes RenderMs { get; init; }

    public required BenchGc Gc { get; init; }
}

public sealed record BenchMachine(string Os, string Cpu, string Gpu, string RenderingMethod, string RenderingDriver);

/// <summary>Display state during the run. <see cref="RefreshAssumed"/> is true when the refresh rate was unknown.</summary>
public sealed record BenchDisplay(
    double RefreshHz,
    bool RefreshAssumed,
    int WindowWidth,
    int WindowHeight,
    string Vsync,
    bool Headless);

/// <summary>Mean viewport render times reported by Godot's RenderingServer.</summary>
public sealed record BenchRenderTimes(double CpuMeanMs, double GpuMeanMs);

/// <summary>GC activity during the sampling window.</summary>
public sealed record BenchGc(
    int Gen0,
    int Gen1,
    int Gen2,
    double PauseMs,
    long AllocatedBytes,
    long MainThreadAllocatedBytes);
