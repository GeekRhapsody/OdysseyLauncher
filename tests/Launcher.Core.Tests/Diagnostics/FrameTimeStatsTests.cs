using Launcher.Core.Diagnostics;

namespace Launcher.Core.Tests.Diagnostics;

public class FrameTimeStatsTests
{
    [Fact]
    public void Percentiles_use_nearest_rank()
    {
        var samples = Enumerable.Range(1, 100).Select(i => (double)i).ToArray();

        var summary = FrameTimeStats.Compute(samples, 60);

        Assert.Equal(100, summary.Count);
        Assert.Equal(50.5, summary.MeanMs, 9);
        Assert.Equal(1.0, summary.MinMs);
        Assert.Equal(100.0, summary.MaxMs);
        Assert.Equal(50.0, summary.P50Ms);
        Assert.Equal(95.0, summary.P95Ms);
        Assert.Equal(99.0, summary.P99Ms);
    }

    [Fact]
    public void Percentile_ranks_round_up_on_small_samples()
    {
        double[] sorted = [10, 20, 30];

        Assert.Equal(20.0, FrameTimeStats.Percentile(sorted, 50));
        Assert.Equal(30.0, FrameTimeStats.Percentile(sorted, 99));
    }

    [Fact]
    public void Hitches_are_intervals_over_one_and_a_half_refresh_intervals()
    {
        double[] samples = [16.7, 16.7, 33.4, 16.7, 50.0, 25.0];

        var summary = FrameTimeStats.Compute(samples, 59.94);

        Assert.Equal(1000 / 59.94 * 1.5, summary.HitchThresholdMs, 9);
        Assert.Equal(2, summary.HitchCount);
        Assert.Equal(new FrameSample(4, 50.0), summary.Worst[0]);
        Assert.Equal(new FrameSample(2, 33.4), summary.Worst[1]);
    }

    [Fact]
    public void Worst_frames_are_capped_and_ties_keep_sequence_order()
    {
        var samples = Enumerable.Repeat(16.7, 25).ToArray();

        var summary = FrameTimeStats.Compute(samples, 60);

        Assert.Equal(Enumerable.Range(0, FrameTimeStats.WorstFrameCount), summary.Worst.Select(sample => sample.Frame));
        Assert.Equal(0.0, summary.StdDevMs, 9);
    }

    [Fact]
    public void Empty_input_gives_an_empty_summary()
    {
        var summary = FrameTimeStats.Compute(ReadOnlySpan<double>.Empty, 60);

        Assert.Equal(0, summary.Count);
        Assert.Empty(summary.Worst);
        Assert.Equal(25.0, summary.HitchThresholdMs, 9);
    }

    [Theory]
    [InlineData(0.0)]
    [InlineData(-1.0)]
    [InlineData(double.NaN)]
    [InlineData(double.PositiveInfinity)]
    public void Refresh_rate_must_be_a_positive_number(double refreshHz)
    {
        double[] samples = [16.7];

        Assert.Throws<ArgumentOutOfRangeException>(() => FrameTimeStats.Compute(samples, refreshHz));
    }

    [Fact]
    public void Mean_of_no_samples_is_zero()
    {
        Assert.Equal(0.0, FrameTimeStats.Mean(ReadOnlySpan<double>.Empty));
    }
}
