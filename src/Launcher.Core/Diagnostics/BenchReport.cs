namespace Launcher.Core.Diagnostics;

/// <summary>The output of <c>--bench</c>. Written as snake_case JSON by <see cref="BenchReportWriter"/>.</summary>
public sealed record BenchReport
{
    /// <summary>2: adds the scenario, the options, the library and the scroll, texture and memory sections (M5).</summary>
    public const int CurrentFormat = 2;

    public int Format { get; init; } = CurrentFormat;

    public required DateTimeOffset CreatedUtc { get; init; }

    /// <summary>The app's informational version, including the commit sha.</summary>
    public required string AppVersion { get; init; }

    public required string GodotVersion { get; init; }

    public required string DotnetVersion { get; init; }

    public required BenchMachine Machine { get; init; }

    public required BenchDisplay Display { get; init; }

    /// <summary><c>boot</c> or <c>scroll</c> (<see cref="BenchScenario"/>).</summary>
    public string Scenario { get; init; } = "boot";

    /// <summary>The debug options that change what's measured. Null in format 1.</summary>
    public BenchOptions? Options { get; init; }

    /// <summary>What was loaded. Null if the library never opened.</summary>
    public BenchLibrary? Library { get; init; }

    /// <summary>
    /// Our code's start-up, from <see cref="StartupMarks.AutoloadEnterTree"/> to
    /// <see cref="StartupMarks.Interactive"/>; the 1 s target applies to this. Null if either mark is missing.
    /// </summary>
    public required double? AppStartupMs { get; init; }

    /// <summary>
    /// Startup marks in milliseconds since the OS created the process. Everything before
    /// <see cref="StartupMarks.AutoloadEnterTree"/> is engine and .NET start-up, outside the target.
    /// </summary>
    public required IReadOnlyDictionary<string, double> StartupMs { get; init; }

    /// <summary>
    /// Frame intervals measured at <c>frame_post_draw</c> (not Godot's smoothed delta): the whole sampled window,
    /// from the first drawn frame. In the scroll scenario, <see cref="Scroll"/> has the scroll frames alone.
    /// </summary>
    public required FrameTimeSummary Frames { get; init; }

    public required BenchRenderTimes RenderMs { get; init; }

    public required BenchGc Gc { get; init; }

    /// <summary>The scroll scenario's measurements. Null in the boot scenario.</summary>
    public BenchScroll? Scroll { get; init; }

    public BenchTextures? Textures { get; init; }

    public BenchMemory? Memory { get; init; }
}

public sealed record BenchMachine(string Os, string Cpu, string Gpu, string RenderingMethod, string RenderingDriver);

/// <summary>Display state during the run. <see cref="RefreshAssumed"/> is true when the refresh rate was unknown.</summary>
public sealed record BenchDisplay(
    double RefreshHz,
    bool RefreshAssumed,
    int WindowWidth,
    int WindowHeight,
    string Vsync,
    bool Headless)
{
    /// <summary>The window mode (Windowed, Fullscreen, ExclusiveFullscreen...). Null in format 1.</summary>
    public string? WindowMode { get; init; }

    /// <summary>The 3D scene's render size, after the render scale.</summary>
    public int SceneRenderWidth { get; init; }

    public int SceneRenderHeight { get; init; }

    public int ScreenWidth { get; init; }

    public int ScreenHeight { get; init; }
}

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

/// <param name="RenderScale">The 3D render scale in use (1 = native).</param>
/// <param name="Upscaler"><c>bilinear</c> or <c>fsr</c>.</param>
/// <param name="UploadCap">Most cover-sized uploads in one frame (a 256² layer counts a quarter); 0 means no cap.</param>
/// <param name="NoTextures">The no-texture control: covers aren't streamed.</param>
/// <param name="Theme">The active theme's id (M6).</param>
/// <param name="MediaSlots">The games grid's media slots, with their standard sizes: "cover (512²), spine (256²)".</param>
/// <param name="Layout">The systems' and the games' layouts: "grid/grid", "carousel/list", "grid 4x2/grid".</param>
public sealed record BenchOptions(double RenderScale, string Upscaler, int UploadCap, bool NoTextures, string? Theme = null, string? MediaSlots = null, string? Layout = null);

/// <param name="Systems">Systems in the systems grid, virtual ones included.</param>
/// <param name="Games">Games across every system.</param>
/// <param name="System">The system the scroll scenario entered, or null.</param>
/// <param name="SystemGames">Its games.</param>
public sealed record BenchLibrary(int Systems, int Games, string? System, int SystemGames);

/// <summary>A scripted scroll through one system's games, from the first row to the last at a steady speed.</summary>
/// <param name="Frames">The scroll frames only.</param>
/// <param name="Rows">Rows scrolled.</param>
/// <param name="Seconds">The planned scroll time.</param>
/// <param name="TexturedFractionMean">Mean share of on-screen cells showing their cover (cells with art only).</param>
/// <param name="TexturedFractionMin">The lowest share in any scroll frame.</param>
/// <param name="VisibleTexturedMs">From the games grid's first frame to every visible cover being shown; null if never.</param>
public sealed record BenchScroll(
    FrameTimeSummary Frames,
    int Rows,
    double Seconds,
    double TexturedFractionMean,
    double TexturedFractionMin,
    double? VisibleTexturedMs,
    long MainThreadAllocatedBytes,
    int Gen0,
    int Gen1,
    int Gen2);

/// <summary>Cover streaming over the sampled window.</summary>
/// <param name="FramesAtByteBudget">Frames that stopped uploading at the per-frame byte budget.</param>
/// <param name="FramesAtCountCap">Frames that stopped uploading at the per-frame upload cap.</param>
/// <param name="MissingDerivatives">Covers with no baked derivative, which show as a plain box.</param>
public sealed record BenchTextures(
    int Uploads,
    double UploadMeanMs,
    double UploadMaxMs,
    int Decodes,
    double DecodeMeanMs,
    double DecodeP95Ms,
    int FramesAtByteBudget,
    int FramesAtCountCap,
    int MissingDerivatives,
    int Failures,
    int Discarded);

/// <summary>Memory at the end of the window.</summary>
public sealed record BenchMemory(
    long WorkingSetBytes,
    long PeakWorkingSetBytes,
    long ManagedHeapBytes,
    long TextureMemBytes,
    long VideoMemBytes);
