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

    public const int DefaultCaptureFrame = 60;
    public const int DefaultBenchFrames = 600;
    public const int MaxFrames = 1_000_000;

    private static readonly string[] KnownArgs = [CaptureArg, CaptureFrameArg, BenchArg, BenchFramesArg];

    public static DebugOptions None { get; } = new();

    /// <summary>Absolute path of the PNG to write, or null when no capture was requested.</summary>
    public string? CapturePath { get; init; }

    /// <summary>Number of drawn frames to wait before capturing.</summary>
    public int CaptureFrame { get; init; } = DefaultCaptureFrame;

    /// <summary>Absolute path of the JSON report to write, or null when no bench was requested.</summary>
    public string? BenchPath { get; init; }

    /// <summary>Number of frame intervals to sample after the first drawn frame.</summary>
    public int BenchFrames { get; init; } = DefaultBenchFrames;

    public bool CaptureRequested => CapturePath is not null;

    public bool BenchRequested => BenchPath is not null;

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

        foreach (var arg in args)
        {
            var separator = arg.IndexOf('=', StringComparison.Ordinal);
            var name = separator < 0 ? arg : arg[..separator];
            if (Array.IndexOf(KnownArgs, name) < 0)
            {
                continue;
            }

            if (separator < 0)
            {
                errors.Add($"{name} needs a value, e.g. {Example(name)}.");
                continue;
            }

            if (!seen.Add(name))
            {
                errors.Add($"{name} was given more than once.");
                continue;
            }

            var value = arg[(separator + 1)..];
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
            }
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
        };
        return new DebugOptionsParseResult(options, errors);
    }

    private static string? ParsePath(string name, string value, string extension, List<string> errors)
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

        if (!string.Equals(Path.GetExtension(value), extension, StringComparison.OrdinalIgnoreCase))
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
        _ => $"{BenchFramesArg}={DefaultBenchFrames}",
    };
}

/// <summary>Result of <see cref="DebugOptions.Parse"/>: the options, or the reasons they were rejected.</summary>
public sealed record DebugOptionsParseResult(DebugOptions Options, IReadOnlyList<string> Errors)
{
    public bool IsValid => Errors.Count == 0;
}
