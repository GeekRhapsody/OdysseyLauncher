using System.Globalization;

namespace Launcher.Core.Diagnostics;

/// <summary>What <c>--bench</c> measures.</summary>
public enum BenchScenario
{
    /// <summary>Boot into the systems grid and sample <see cref="DebugOptions.BenchFrames"/> frames.</summary>
    Boot,

    /// <summary>
    /// Boot, enter a system, then scroll its games grid from the first row to the last at a steady speed over
    /// <see cref="DebugOptions.BenchScrollSeconds"/>, sampling the scroll frames.
    /// </summary>
    Scroll,
}

/// <summary>How the 3D scene is upscaled when it renders below the window's resolution.</summary>
public enum Upscaler
{
    Bilinear,
    Fsr,
}

/// <summary>
/// Debug facilities requested on the command line. The Godot app passes only its user arguments
/// (everything after <c>--</c> or <c>++</c>), so engine arguments never reach this parser.
/// </summary>
public sealed record DebugOptions
{
    public const string CaptureArg = "--capture";
    public const string CaptureFrameArg = "--capture-frame";
    public const string BenchArg = "--bench";
    public const string BenchFramesArg = "--bench-frames";
    public const string BenchScenarioArg = "--bench-scenario";
    public const string BenchSystemArg = "--bench-system";
    public const string BenchScrollSecondsArg = "--bench-scroll-seconds";
    public const string NoTexturesArg = "--no-textures";
    public const string RenderScaleArg = "--render-scale";
    public const string UpscalerArg = "--upscaler";
    public const string UploadCapArg = "--upload-cap";
    public const string StartSystemArg = "--start-system";
    public const string StartIndexArg = "--start-index";
    public const string NavScriptArg = "--nav-script";
    public const string LaunchArg = "--launch";
    public const string UserDirArg = "--user-dir";
    public const string QuitAfterLaunchArg = "--quit-after-launch";
    public const string ThemeArg = "--theme";
    public const string NoOverlayArg = "--no-overlay";
    public const string OpenArg = "--open";
    public const string OpenPathArg = "--open-path";

    /// <summary>
    /// What <c>--open</c> can show once the app is interactive (M7), for captures of each settings screen and shared
    /// component: the settings screen, the on-screen keyboard, the three pickers, a confirmation, a progress card, the
    /// power menu, and the match panel over made-up results (for <see cref="StartSystem"/>'s game at
    /// <see cref="StartIndex"/>).
    /// </summary>
    public static IReadOnlyList<string> OpenTargets { get; } =
        ["settings", "keyboard", "folder-picker", "image-picker", "program-picker", "confirm", "progress", "power", "match"];

    public const int DefaultCaptureFrame = 60;
    public const int DefaultBenchFrames = 600;
    public const int MaxFrames = 1_000_000;
    public const double DefaultBenchScrollSeconds = 60;

    /// <summary>
    /// Cover-sized uploads in one frame, at most (ARCHITECTURE.md A3; a 256² slot layer counts a quarter). M1 proposed
    /// 8, because a few of its hitch frames followed a burst of uploads. M6 measured bursts of 5 to 8 covers in a
    /// frame (a whole row) making single uploads take 14–21 ms; at 4 the longest was 1 ms, still 100% textured.
    /// </summary>
    public const int DefaultUploadCap = 4;

    private static readonly string[] KnownArgs =
    [
        CaptureArg, CaptureFrameArg, BenchArg, BenchFramesArg, BenchScenarioArg, BenchSystemArg, BenchScrollSecondsArg,
        NoTexturesArg, RenderScaleArg, UpscalerArg, UploadCapArg, StartSystemArg, StartIndexArg, NavScriptArg, LaunchArg,
        UserDirArg, QuitAfterLaunchArg, ThemeArg, NoOverlayArg, OpenArg, OpenPathArg,
    ];

    /// <summary>
    /// The steps <c>--nav-script</c> takes: the navigation commands (as the controller sends them; <c>menu</c> is Menu,
    /// <c>x</c> is X, <c>favourite</c> is Y, <c>power</c> is View), <c>theme</c> (the next theme, as T does), <c>rescan</c> (every system, from
    /// any screen, so a capture can show media changing), and <c>wait</c>, which does nothing for a step. While a
    /// settings screen is open (M7), the commands go to it. Three steps send real input events instead, through
    /// Godot's input like the mouse and keyboard: <c>click</c> (the left button, on the focused control), <c>scroll</c>
    /// (the wheel, down three notches, over the middle of the screen) and <c>type</c> (the keys "Ok 1").
    /// </summary>
    public static IReadOnlyList<string> NavScriptSteps { get; } =
    [
        "up", "down", "left", "right", "pageup", "pagedown", "letterprevious", "letternext", "first", "last",
        "accept", "back", "favourite", "menu", "x", "power", "theme", "rescan", "click", "scroll", "type", "wait",
    ];

    /// <summary>Frames between <c>--nav-script</c> steps: long enough for a transition to finish.</summary>
    public const int NavScriptStepFrames = 30;

    /// <summary>Arguments that are switches, with no value.</summary>
    private static readonly string[] FlagArgs = [QuitAfterLaunchArg, NoTexturesArg, NoOverlayArg];

    public static DebugOptions None { get; } = new();

    /// <summary>Absolute path of the PNG to write, or null when no capture was requested.</summary>
    public string? CapturePath { get; init; }

    /// <summary>Number of drawn frames to wait before capturing.</summary>
    public int CaptureFrame { get; init; } = DefaultCaptureFrame;

    /// <summary>Absolute path of the JSON report to write, or null when no bench was requested.</summary>
    public string? BenchPath { get; init; }

    /// <summary>Number of frame intervals to sample after the first drawn frame (the boot scenario).</summary>
    public int BenchFrames { get; init; } = DefaultBenchFrames;

    public BenchScenario BenchScenario { get; init; } = BenchScenario.Boot;

    /// <summary>The system the scroll scenario enters; null means the one with the most games.</summary>
    public string? BenchSystem { get; init; }

    /// <summary>How long the scroll scenario takes to go from the first row to the last.</summary>
    public double BenchScrollSeconds { get; init; } = DefaultBenchScrollSeconds;

    /// <summary>The no-texture control: covers aren't streamed, so the grid shows every box as it looks without art.</summary>
    public bool NoTextures { get; init; }

    /// <summary>The 3D render scale, overriding the automatic cap of 1080p; null for automatic.</summary>
    public double? RenderScale { get; init; }

    public Upscaler Upscaler { get; init; } = Upscaler.Bilinear;

    /// <summary>Cover uploads per frame, at most; 0 means no cap.</summary>
    public int UploadCap { get; init; } = DefaultUploadCap;

    /// <summary>Enter this system once interactive (for captures), or null.</summary>
    public string? StartSystem { get; init; }

    /// <summary>With <see cref="StartSystem"/>: focus this game, counting from 0 in grid order.</summary>
    public int? StartIndex { get; init; }

    /// <summary>
    /// Navigation steps to play once interactive (after <see cref="StartSystem"/>), one every
    /// <see cref="NavScriptStepFrames"/> frames, through the same path as the controller; empty for none.
    /// </summary>
    public IReadOnlyList<string> NavScript { get; init; } = [];

    /// <summary>The system id of the game <c>--launch</c> names, or null.</summary>
    public string? LaunchSystem { get; init; }

    /// <summary>The game's path relative to its ROM folder, '/'-separated (<c>rel_path</c>), or null.</summary>
    public string? LaunchRelPath { get; init; }

    /// <summary>
    /// <c>--user-dir</c>: keep config, data and cache in this absolute folder, as portable mode does, instead of the
    /// user's AppData. Null for the normal locations.
    /// </summary>
    public string? UserDir { get; init; }

    /// <summary>Quit once the <c>--launch</c> game has ended: exit code 0 if it ran, 1 if the launch failed.</summary>
    public bool QuitAfterLaunch { get; init; }

    /// <summary><c>--theme</c>: use this theme id for the run instead of settings.toml's <c>[display] theme</c>; null for that.</summary>
    public string? Theme { get; init; }

    /// <summary>
    /// <c>--no-overlay</c>: hide the text overlay, whose scrims darken the top and bottom of the screen, so a capture
    /// shows the look's corners exactly.
    /// </summary>
    public bool NoOverlay { get; init; }

    /// <summary><c>--open</c>: a settings screen or component to show once interactive (<see cref="OpenTargets"/>), or null.</summary>
    public string? Open { get; init; }

    /// <summary><c>--open-path</c>: the folder a picker opened by <c>--open</c> starts in (absolute), or null.</summary>
    public string? OpenPath { get; init; }

    public bool CaptureRequested => CapturePath is not null;

    public bool BenchRequested => BenchPath is not null;

    public bool LaunchRequested => LaunchSystem is not null;

    /// <summary>Capture or bench: the facilities that need a windowed run and a watchdog.</summary>
    public bool IsActive => CaptureRequested || BenchRequested;

    /// <summary>
    /// Parses user arguments of the form <c>--name=value</c>. Arguments this parser doesn't know are
    /// ignored, so other facilities can share the command line. Any error yields <see cref="None"/>.
    /// </summary>
    public static DebugOptionsParseResult Parse(IReadOnlyList<string> args)
    {
        ArgumentNullException.ThrowIfNull(args);

        var errors = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var options = new DebugOptions();

        foreach (var arg in args)
        {
            var separator = arg.IndexOf('=', StringComparison.Ordinal);
            var name = separator < 0 ? arg : arg[..separator];
            if (Array.IndexOf(KnownArgs, name) < 0)
            {
                continue;
            }

            var isFlag = Array.IndexOf(FlagArgs, name) >= 0;
            if (isFlag != (separator < 0))
            {
                errors.Add(isFlag ? $"{name} doesn't take a value." : $"{name} needs a value, e.g. {Example(name)}.");
                continue;
            }

            if (!seen.Add(name))
            {
                errors.Add($"{name} was given more than once.");
                continue;
            }

            var value = isFlag ? string.Empty : arg[(separator + 1)..];
            options = name switch
            {
                CaptureArg => options with { CapturePath = ParsePath(name, value, ".png", errors) },
                CaptureFrameArg => options with { CaptureFrame = ParseInt(name, value, 1, MaxFrames, errors) ?? DefaultCaptureFrame },
                BenchArg => options with { BenchPath = ParsePath(name, value, ".json", errors) },
                BenchFramesArg => options with { BenchFrames = ParseInt(name, value, 1, MaxFrames, errors) ?? DefaultBenchFrames },
                BenchScenarioArg => options with { BenchScenario = ParseEnum(name, value, BenchScenario.Boot, errors) },
                BenchSystemArg => options with { BenchSystem = ParseId(name, value, errors) },
                BenchScrollSecondsArg => options with { BenchScrollSeconds = ParseDouble(name, value, 1, 3600, errors) ?? DefaultBenchScrollSeconds },
                NoTexturesArg => options with { NoTextures = true },
                RenderScaleArg => options with { RenderScale = ParseDouble(name, value, 0.25, 1, errors) },
                UpscalerArg => options with { Upscaler = ParseEnum(name, value, Upscaler.Bilinear, errors) },
                UploadCapArg => options with { UploadCap = ParseInt(name, value, 0, 64, errors) ?? DefaultUploadCap },
                StartSystemArg => options with { StartSystem = ParseId(name, value, errors) },
                StartIndexArg => options with { StartIndex = ParseInt(name, value, 0, MaxFrames, errors) },
                NavScriptArg => options with { NavScript = ParseNavScript(value, errors) },
                LaunchArg => ParseLaunch(options, value, errors),
                UserDirArg => options with { UserDir = ParsePath(name, value, null, errors) },
                QuitAfterLaunchArg => options with { QuitAfterLaunch = true },
                ThemeArg => options with { Theme = ParseId(name, value, errors) },
                NoOverlayArg => options with { NoOverlay = true },
                OpenArg => options with { Open = ParseOpen(value, errors) },
                OpenPathArg => options with { OpenPath = ParsePath(name, value, null, errors) },
                _ => options,
            };
        }

        Requires(seen, QuitAfterLaunchArg, LaunchArg, $"{LaunchArg}=<system>/<path>", errors);
        Requires(seen, CaptureFrameArg, CaptureArg, $"{CaptureArg}=<path.png>", errors);
        Requires(seen, BenchFramesArg, BenchArg, $"{BenchArg}=<path.json>", errors);
        Requires(seen, BenchScenarioArg, BenchArg, $"{BenchArg}=<path.json>", errors);
        Requires(seen, BenchSystemArg, BenchScenarioArg, $"{BenchScenarioArg}=scroll", errors);
        Requires(seen, BenchScrollSecondsArg, BenchScenarioArg, $"{BenchScenarioArg}=scroll", errors);
        Requires(seen, StartIndexArg, StartSystemArg, $"{StartSystemArg}=<system>", errors);
        Requires(seen, OpenPathArg, OpenArg, $"{OpenArg}=folder-picker", errors);
        if (options.BenchScenario != BenchScenario.Scroll)
        {
            foreach (var scrollOnly in (ReadOnlySpan<string>)[BenchSystemArg, BenchScrollSecondsArg])
            {
                if (seen.Contains(scrollOnly) && seen.Contains(BenchScenarioArg))
                {
                    errors.Add($"{scrollOnly} only applies to {BenchScenarioArg}=scroll.");
                }
            }
        }
        else if (seen.Contains(BenchFramesArg))
        {
            errors.Add($"{BenchFramesArg} only applies to the boot scenario; the scroll scenario samples the scroll ({BenchScrollSecondsArg}).");
        }

        if (options.BenchScenario == BenchScenario.Scroll && (seen.Contains(StartSystemArg) || seen.Contains(NavScriptArg)))
        {
            errors.Add($"{StartSystemArg} and {NavScriptArg} can't be combined with {BenchScenarioArg}=scroll, which drives the grid itself.");
        }

        return errors.Count > 0 ? new DebugOptionsParseResult(None, errors) : new DebugOptionsParseResult(options, errors);
    }

    private static void Requires(HashSet<string> seen, string arg, string needs, string example, List<string> errors)
    {
        if (seen.Contains(arg) && !seen.Contains(needs))
        {
            errors.Add($"{arg} needs {example}.");
        }
    }

    /// <summary>Comma-separated steps from <see cref="NavScriptSteps"/>, ignoring case.</summary>
    private static List<string> ParseNavScript(string value, List<string> errors)
    {
        var steps = new List<string>();
        foreach (var part in value.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries))
        {
            var step = part.ToLowerInvariant();
            if (!NavScriptSteps.Contains(step))
            {
                errors.Add($"{NavScriptArg} doesn't know the step '{part}'. The steps are {string.Join(", ", NavScriptSteps)}.");
                continue;
            }

            steps.Add(step);
        }

        if (steps.Count == 0 && errors.Count == 0)
        {
            errors.Add($"{NavScriptArg} needs at least one step, e.g. {Example(NavScriptArg)}.");
        }

        return steps;
    }

    private static string? ParseOpen(string value, List<string> errors)
    {
        var target = value.ToLowerInvariant();
        if (OpenTargets.Contains(target))
        {
            return target;
        }

        errors.Add($"{OpenArg} doesn't know '{value}'. It opens {string.Join(", ", OpenTargets)}.");
        return null;
    }

    /// <summary><c>&lt;system&gt;/&lt;path relative to its ROM folder&gt;</c>; either slash separates.</summary>
    private static DebugOptions ParseLaunch(DebugOptions options, string value, List<string> errors)
    {
        var path = value.Replace('\\', '/');
        var slash = path.IndexOf('/', StringComparison.Ordinal);
        if (slash <= 0 || slash == path.Length - 1 || path.StartsWith("//", StringComparison.Ordinal))
        {
            errors.Add($"{LaunchArg} needs a system and a ROM path, e.g. {Example(LaunchArg)}; got '{value}'.");
            return options;
        }

        return options with { LaunchSystem = path[..slash], LaunchRelPath = path[(slash + 1)..] };
    }

    /// <param name="extension">The file extension the path must have, or null for a folder.</param>
    private static string? ParsePath(string name, string value, string? extension, List<string> errors)
    {
        if (value.Length == 0)
        {
            errors.Add($"{name} needs a path, e.g. {Example(name)}.");
            return null;
        }

        if (!Path.IsPathFullyQualified(value))
        {
            errors.Add($"{name} needs an absolute path, because Godot changes the working directory; got '{value}'.");
            return null;
        }

        if (extension is not null && !string.Equals(Path.GetExtension(value), extension, StringComparison.OrdinalIgnoreCase))
        {
            errors.Add($"{name} must name a {extension} file; got '{value}'.");
            return null;
        }

        return Path.GetFullPath(value);
    }

    private static int? ParseInt(string name, string value, int min, int max, List<string> errors)
    {
        if (int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var number) && number >= min && number <= max)
        {
            return number;
        }

        errors.Add(string.Create(CultureInfo.InvariantCulture, $"{name} needs a whole number from {min:N0} to {max:N0}; got '{value}'."));
        return null;
    }

    private static double? ParseDouble(string name, string value, double min, double max, List<string> errors)
    {
        if (double.TryParse(value, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var number) && number >= min && number <= max)
        {
            return number;
        }

        errors.Add(string.Create(CultureInfo.InvariantCulture, $"{name} needs a number from {min} to {max}; got '{value}'."));
        return null;
    }

    private static T ParseEnum<T>(string name, string value, T fallback, List<string> errors)
        where T : struct, Enum
    {
        foreach (var candidate in Enum.GetValues<T>())
        {
            if (string.Equals(candidate.ToString(), value, StringComparison.OrdinalIgnoreCase))
            {
                return candidate;
            }
        }

        var names = string.Join(", ", Enum.GetNames<T>().Select(n => n.ToLowerInvariant()));
        errors.Add($"{name} must be one of {names}; got '{value}'.");
        return fallback;
    }

    /// <summary>A config id: lower-case letters, digits, '_' and '-' (A5).</summary>
    private static string? ParseId(string name, string value, List<string> errors)
    {
        if (value.Length > 0 && value.All(c => c is (>= 'a' and <= 'z') or (>= '0' and <= '9') or '_' or '-'))
        {
            return value;
        }

        errors.Add($"{name} needs {(name == ThemeArg ? "a theme" : "a system")} id, e.g. {Example(name)}; got '{value}'.");
        return null;
    }

    private static string Example(string name) => name switch
    {
        CaptureArg => $"{CaptureArg}=C:/captures/shot.png",
        CaptureFrameArg => $"{CaptureFrameArg}={DefaultCaptureFrame}",
        BenchArg => $"{BenchArg}=C:/bench/run.json",
        BenchScenarioArg => $"{BenchScenarioArg}=scroll",
        BenchSystemArg or StartSystemArg => $"{name}=ps2",
        BenchScrollSecondsArg => $"{BenchScrollSecondsArg}=60",
        RenderScaleArg => $"{RenderScaleArg}=0.5",
        UpscalerArg => $"{UpscalerArg}=fsr",
        UploadCapArg => $"{UploadCapArg}={DefaultUploadCap}",
        StartIndexArg => $"{StartIndexArg}=12",
        NavScriptArg => $"{NavScriptArg}=down,right,accept,back",
        LaunchArg => $"{LaunchArg}=megadrive/Sonic the Hedgehog (USA, Europe).md",
        UserDirArg => $"{UserDirArg}=C:/OdysseyTest",
        ThemeArg => $"{ThemeArg}=slot-showcase",
        OpenArg => $"{OpenArg}=settings",
        OpenPathArg => $"{OpenPathArg}=C:/Games",
        _ => $"{BenchFramesArg}={DefaultBenchFrames}",
    };
}

/// <summary>Result of <see cref="DebugOptions.Parse"/>: the options, or the reasons they were rejected.</summary>
public sealed record DebugOptionsParseResult(DebugOptions Options, IReadOnlyList<string> Errors)
{
    public bool IsValid => Errors.Count == 0;
}
