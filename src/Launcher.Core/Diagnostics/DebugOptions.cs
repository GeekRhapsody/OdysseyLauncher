using System.Globalization;

namespace Launcher.Core.Diagnostics;

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
    public const string LaunchArg = "--launch";
    public const string UserDirArg = "--user-dir";
    public const string QuitAfterLaunchArg = "--quit-after-launch";

    public const int DefaultCaptureFrame = 60;
    public const int DefaultBenchFrames = 600;
    public const int MaxFrames = 1_000_000;

    private static readonly string[] KnownArgs = [CaptureArg, CaptureFrameArg, BenchArg, BenchFramesArg, LaunchArg, UserDirArg, QuitAfterLaunchArg];

    /// <summary>Arguments that are switches, with no value.</summary>
    private static readonly string[] FlagArgs = [QuitAfterLaunchArg];

    public static DebugOptions None { get; } = new();

    /// <summary>Absolute path of the PNG to write, or null when no capture was requested.</summary>
    public string? CapturePath { get; init; }

    /// <summary>Number of drawn frames to wait before capturing.</summary>
    public int CaptureFrame { get; init; } = DefaultCaptureFrame;

    /// <summary>Absolute path of the JSON report to write, or null when no bench was requested.</summary>
    public string? BenchPath { get; init; }

    /// <summary>Number of frame intervals to sample after the first drawn frame.</summary>
    public int BenchFrames { get; init; } = DefaultBenchFrames;

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
        string? capturePath = null;
        string? benchPath = null;
        int? captureFrame = null;
        int? benchFrames = null;
        string? launchSystem = null;
        string? launchRelPath = null;
        string? userDir = null;

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
            switch (name)
            {
                case CaptureArg:
                    capturePath = ParsePath(name, value, ".png", errors);
                    break;
                case CaptureFrameArg:
                    captureFrame = ParseFrames(name, value, errors);
                    break;
                case BenchArg:
                    benchPath = ParsePath(name, value, ".json", errors);
                    break;
                case BenchFramesArg:
                    benchFrames = ParseFrames(name, value, errors);
                    break;
                case LaunchArg:
                    (launchSystem, launchRelPath) = ParseLaunch(value, errors);
                    break;
                case UserDirArg:
                    userDir = ParsePath(name, value, null, errors);
                    break;
            }
        }

        if (seen.Contains(QuitAfterLaunchArg) && !seen.Contains(LaunchArg))
        {
            errors.Add($"{QuitAfterLaunchArg} needs {LaunchArg}=<system>/<path>.");
        }

        if (seen.Contains(CaptureFrameArg) && !seen.Contains(CaptureArg))
        {
            errors.Add($"{CaptureFrameArg} needs {CaptureArg}=<path.png>.");
        }

        if (seen.Contains(BenchFramesArg) && !seen.Contains(BenchArg))
        {
            errors.Add($"{BenchFramesArg} needs {BenchArg}=<path.json>.");
        }

        if (errors.Count > 0)
        {
            return new DebugOptionsParseResult(None, errors);
        }

        var options = new DebugOptions
        {
            CapturePath = capturePath,
            CaptureFrame = captureFrame ?? DefaultCaptureFrame,
            BenchPath = benchPath,
            BenchFrames = benchFrames ?? DefaultBenchFrames,
            LaunchSystem = launchSystem,
            LaunchRelPath = launchRelPath,
            UserDir = userDir,
            QuitAfterLaunch = seen.Contains(QuitAfterLaunchArg),
        };
        return new DebugOptionsParseResult(options, errors);
    }

    /// <summary><c>&lt;system&gt;/&lt;path relative to its ROM folder&gt;</c>; either slash separates.</summary>
    private static (string? System, string? RelPath) ParseLaunch(string value, List<string> errors)
    {
        var path = value.Replace('\\', '/');
        var slash = path.IndexOf('/', StringComparison.Ordinal);
        if (slash <= 0 || slash == path.Length - 1 || path.StartsWith("//", StringComparison.Ordinal))
        {
            errors.Add($"{LaunchArg} needs a system and a ROM path, e.g. {Example(LaunchArg)}; got '{value}'.");
            return (null, null);
        }

        return (path[..slash], path[(slash + 1)..]);
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

    private static int? ParseFrames(string name, string value, List<string> errors)
    {
        if (int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var frames)
            && frames is >= 1 and <= MaxFrames)
        {
            return frames;
        }

        errors.Add($"{name} needs a whole number from 1 to {MaxFrames:N0}; got '{value}'.");
        return null;
    }

    private static string Example(string name) => name switch
    {
        CaptureArg => $"{CaptureArg}=C:/captures/shot.png",
        CaptureFrameArg => $"{CaptureFrameArg}={DefaultCaptureFrame}",
        BenchArg => $"{BenchArg}=C:/bench/run.json",
        LaunchArg => $"{LaunchArg}=megadrive/Sonic the Hedgehog (USA, Europe).md",
        UserDirArg => $"{UserDirArg}=C:/OdysseyTest",
        _ => $"{BenchFramesArg}={DefaultBenchFrames}",
    };
}

/// <summary>Result of <see cref="DebugOptions.Parse"/>: the options, or the reasons they were rejected.</summary>
public sealed record DebugOptionsParseResult(DebugOptions Options, IReadOnlyList<string> Errors)
{
    public bool IsValid => Errors.Count == 0;
}
