using Launcher.Core.Diagnostics;

namespace Launcher.Core.Tests.Diagnostics;

public class StartupTimelineTests
{
    private static readonly DateTimeOffset ProcessStart = new(2026, 9, 27, 12, 0, 0, TimeSpan.Zero);

    [Fact]
    public void Marks_are_measured_from_process_creation()
    {
        var clock = new ManualClock(ProcessStart.AddMilliseconds(250));
        var timeline = new StartupTimeline(ProcessStart, clock);

        var first = timeline.Mark(StartupMarks.AutoloadEnterTree);
        clock.Advance(TimeSpan.FromMilliseconds(100));
        var second = timeline.Mark(StartupMarks.MainReady);

        Assert.Equal(250.0, first, 6);
        Assert.Equal(350.0, second, 6);
        Assert.Equal(
            new[] { StartupMarks.AutoloadEnterTree, StartupMarks.MainReady },
            timeline.Marks.Select(mark => mark.Name));
    }

    [Fact]
    public void The_first_mark_under_a_name_wins()
    {
        var clock = new ManualClock(ProcessStart);
        var timeline = new StartupTimeline(ProcessStart, clock);

        timeline.Mark(StartupMarks.Interactive);
        clock.Advance(TimeSpan.FromSeconds(1));

        Assert.Equal(0.0, timeline.Mark(StartupMarks.Interactive), 6);
        Assert.Single(timeline.Marks);
    }

    [Fact]
    public void Reported_marks_are_in_time_order_even_when_recorded_out_of_order()
    {
        var timeline = new StartupTimeline(ProcessStart, new ManualClock(ProcessStart.AddSeconds(1)));

        timeline.Mark(StartupMarks.AutoloadEnterTree);
        timeline.MarkAt(StartupMarks.EngineStart, 40);
        var marks = timeline.ToDictionary();

        Assert.Equal(new[] { StartupMarks.EngineStart, StartupMarks.AutoloadEnterTree }, marks.Keys);
        Assert.Equal(40.0, marks[StartupMarks.EngineStart]);
        Assert.Equal(1000.0, marks[StartupMarks.AutoloadEnterTree], 6);
        Assert.Equal(
            new[] { StartupMarks.AutoloadEnterTree, StartupMarks.EngineStart },
            timeline.Marks.Select(mark => mark.Name));
    }

    [Fact]
    public void Between_measures_from_one_mark_to_another()
    {
        var timeline = new StartupTimeline(ProcessStart, new ManualClock(ProcessStart));

        timeline.MarkAt(StartupMarks.AutoloadEnterTree, 1200);
        timeline.MarkAt(StartupMarks.Interactive, 1325.5);

        Assert.Equal(125.5, timeline.Between(StartupMarks.AutoloadEnterTree, StartupMarks.Interactive));
    }

    [Fact]
    public void Between_is_null_until_both_marks_exist()
    {
        var timeline = new StartupTimeline(ProcessStart, new ManualClock(ProcessStart));

        timeline.MarkAt(StartupMarks.AutoloadEnterTree, 1200);

        Assert.Null(timeline.Between(StartupMarks.AutoloadEnterTree, StartupMarks.Interactive));
        Assert.Null(timeline.Between(StartupMarks.MainReady, StartupMarks.AutoloadEnterTree));
    }

    [Fact]
    public void The_current_process_timeline_is_after_process_creation()
    {
        var timeline = StartupTimeline.ForCurrentProcess();

        Assert.True(timeline.ElapsedMs > 0);
    }

    private sealed class ManualClock(DateTimeOffset start) : TimeProvider
    {
        private DateTimeOffset _now = start;
        private long _timestamp;

        public override long TimestampFrequency => TimeSpan.TicksPerSecond;

        public override DateTimeOffset GetUtcNow() => _now;

        public override long GetTimestamp() => _timestamp;

        public void Advance(TimeSpan by)
        {
            _now += by;
            _timestamp += by.Ticks;
        }
    }
}
