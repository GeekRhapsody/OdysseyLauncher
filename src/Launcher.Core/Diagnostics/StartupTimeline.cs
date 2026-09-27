using System.Diagnostics;

namespace Launcher.Core.Diagnostics;

/// <summary>Standard startup mark names. Later milestones add their own.</summary>
public static class StartupMarks
{
    /// <summary>When Godot's own clock started (derived from <c>Time.GetTicksUsec</c>).</summary>
    public const string EngineStart = "engine_start";

    public const string AutoloadEnterTree = "autoload_enter_tree";

    public const string MainReady = "main_ready";

    public const string FirstFrameDrawn = "first_frame_drawn";

    /// <summary>The first frame in which content is drawn and input is handled.</summary>
    public const string Interactive = "interactive";
}

/// <summary>A named point in time, in milliseconds since the OS created the process.</summary>
public readonly record struct StartupMark(string Name, double Milliseconds);

/// <summary>
/// Named startup marks, in milliseconds since the OS created the process. Thread-safe; the first
/// mark recorded under a name wins.
/// </summary>
public sealed class StartupTimeline
{
    private readonly object _gate = new();
    private readonly List<StartupMark> _marks = [];
    private readonly TimeProvider _time;
    private readonly long _anchorTimestamp;
    private readonly double _anchorMs;

    public StartupTimeline(DateTimeOffset processStart, TimeProvider time)
    {
        ArgumentNullException.ThrowIfNull(time);
        _time = time;
        _anchorTimestamp = time.GetTimestamp();
        _anchorMs = (time.GetUtcNow() - processStart).TotalMilliseconds;
    }

    /// <summary>Milliseconds since the process was created.</summary>
    public double ElapsedMs => _anchorMs + _time.GetElapsedTime(_anchorTimestamp).TotalMilliseconds;

    /// <summary>A snapshot of the marks, in the order they were recorded.</summary>
    public IReadOnlyList<StartupMark> Marks
    {
        get
        {
            lock (_gate)
            {
                return _marks.ToArray();
            }
        }
    }

    /// <summary>Creates a timeline anchored to the current process's creation time.</summary>
    public static StartupTimeline ForCurrentProcess()
    {
        using var process = Process.GetCurrentProcess();
        return new StartupTimeline(new DateTimeOffset(process.StartTime), TimeProvider.System);
    }

    /// <summary>Records a mark at the current time and returns its value (or the earlier value).</summary>
    public double Mark(string name) => MarkAt(name, ElapsedMs);

    /// <summary>Records a mark at an explicit time, e.g. one derived from another clock.</summary>
    public double MarkAt(string name, double milliseconds)
    {
        ArgumentException.ThrowIfNullOrEmpty(name);
        lock (_gate)
        {
            foreach (var mark in _marks)
            {
                if (mark.Name == name)
                {
                    return mark.Milliseconds;
                }
            }

            _marks.Add(new StartupMark(name, milliseconds));
            return milliseconds;
        }
    }

    /// <summary>
    /// Returns the marks as a name-to-milliseconds map in time order. Marks derived from another
    /// clock can be recorded after later ones; ties keep recording order.
    /// </summary>
    public IReadOnlyDictionary<string, double> ToDictionary()
    {
        var result = new Dictionary<string, double>(StringComparer.Ordinal);
        foreach (var mark in Marks.OrderBy(mark => mark.Milliseconds))
        {
            result[mark.Name] = mark.Milliseconds;
        }

        return result;
    }
}
