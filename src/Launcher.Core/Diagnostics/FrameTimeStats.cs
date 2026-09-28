namespace Launcher.Core.Diagnostics;

/// <summary>One frame interval: its position in the sampled sequence and its length.</summary>
public readonly record struct FrameSample(int Frame, double Ms);

/// <summary>Summary statistics for a run of frame intervals.</summary>
public sealed record FrameTimeSummary
{
    public required int Count { get; init; }

    public required double MeanMs { get; init; }

    public required double MinMs { get; init; }

    public required double MaxMs { get; init; }

    public required double P50Ms { get; init; }

    public required double P95Ms { get; init; }

    public required double P99Ms { get; init; }

    public required double StdDevMs { get; init; }

    /// <summary>Intervals longer than this count as hitches.</summary>
    public required double HitchThresholdMs { get; init; }

    public required int HitchCount { get; init; }

    /// <summary>Intervals longer than twice the refresh interval: the target is none (A3).</summary>
    public required int Over2xCount { get; init; }

    /// <summary>The longest intervals, longest first.</summary>
    public required IReadOnlyList<FrameSample> Worst { get; init; }
}

/// <summary>Frame-interval statistics for the bench report.</summary>
public static class FrameTimeStats
{
    /// <summary>An interval longer than this multiple of the refresh interval is a hitch.</summary>
    public const double HitchFactor = 1.5;

    public const int WorstFrameCount = 10;

    public static FrameTimeSummary Compute(ReadOnlySpan<double> intervalsMs, double refreshHz)
    {
        if (!(refreshHz > 0) || double.IsInfinity(refreshHz))
        {
            throw new ArgumentOutOfRangeException(nameof(refreshHz), refreshHz, "Refresh rate must be a positive number.");
        }

        var threshold = 1000.0 / refreshHz * HitchFactor;
        var count = intervalsMs.Length;
        if (count == 0)
        {
            return new FrameTimeSummary
            {
                Count = 0,
                MeanMs = 0,
                MinMs = 0,
                MaxMs = 0,
                P50Ms = 0,
                P95Ms = 0,
                P99Ms = 0,
                StdDevMs = 0,
                HitchThresholdMs = threshold,
                HitchCount = 0,
                Over2xCount = 0,
                Worst = [],
            };
        }

        var twice = 2000.0 / refreshHz;
        var sum = 0.0;
        var min = double.MaxValue;
        var max = double.MinValue;
        var hitches = 0;
        var over2x = 0;
        foreach (var ms in intervalsMs)
        {
            sum += ms;
            min = Math.Min(min, ms);
            max = Math.Max(max, ms);
            if (ms > threshold)
            {
                hitches++;
            }

            if (ms > twice)
            {
                over2x++;
            }
        }

        var mean = sum / count;
        var squares = 0.0;
        foreach (var ms in intervalsMs)
        {
            squares += (ms - mean) * (ms - mean);
        }

        var sorted = intervalsMs.ToArray();
        Array.Sort(sorted);

        return new FrameTimeSummary
        {
            Count = count,
            MeanMs = mean,
            MinMs = min,
            MaxMs = max,
            P50Ms = Percentile(sorted, 50),
            P95Ms = Percentile(sorted, 95),
            P99Ms = Percentile(sorted, 99),
            StdDevMs = Math.Sqrt(squares / count),
            HitchThresholdMs = threshold,
            HitchCount = hitches,
            Over2xCount = over2x,
            Worst = WorstFrames(intervalsMs, WorstFrameCount),
        };
    }

    /// <summary>Nearest-rank percentile of a non-empty, ascending-sorted list.</summary>
    public static double Percentile(IReadOnlyList<double> sorted, double percentile)
    {
        ArgumentNullException.ThrowIfNull(sorted);
        if (sorted.Count == 0)
        {
            throw new ArgumentException("There are no samples.", nameof(sorted));
        }

        if (percentile is <= 0 or > 100 || double.IsNaN(percentile))
        {
            throw new ArgumentOutOfRangeException(nameof(percentile), percentile, "Percentile must be in (0, 100].");
        }

        // Multiply before dividing so integral percentiles give exact ranks.
        var rank = (int)Math.Ceiling(percentile * sorted.Count / 100.0);
        return sorted[Math.Clamp(rank, 1, sorted.Count) - 1];
    }

    /// <summary>Mean of the samples, or 0 when there are none.</summary>
    public static double Mean(ReadOnlySpan<double> samples)
    {
        if (samples.IsEmpty)
        {
            return 0;
        }

        var sum = 0.0;
        foreach (var sample in samples)
        {
            sum += sample;
        }

        return sum / samples.Length;
    }

    private static FrameSample[] WorstFrames(ReadOnlySpan<double> intervalsMs, int take)
    {
        var values = intervalsMs.ToArray();
        var order = new int[values.Length];
        for (var i = 0; i < order.Length; i++)
        {
            order[i] = i;
        }

        // Longest first; ties keep sequence order.
        Array.Sort(order, (a, b) =>
        {
            var byLength = values[b].CompareTo(values[a]);
            return byLength != 0 ? byLength : a.CompareTo(b);
        });

        var worst = new FrameSample[Math.Min(take, values.Length)];
        for (var i = 0; i < worst.Length; i++)
        {
            worst[i] = new FrameSample(order[i], values[order[i]]);
        }

        return worst;
    }
}
