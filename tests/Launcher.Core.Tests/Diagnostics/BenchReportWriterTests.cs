using System.Text.Json;
using Launcher.Core.Diagnostics;

namespace Launcher.Core.Tests.Diagnostics;

public class BenchReportWriterTests
{
    [Fact]
    public void Writes_snake_case_json_into_a_new_folder()
    {
        var folder = Path.Combine(Path.GetTempPath(), "odyssey-tests", Guid.NewGuid().ToString("N"));
        var path = Path.Combine(folder, "nested", "bench.json");
        try
        {
            BenchReportWriter.Write(path, SampleReport());

            using var json = JsonDocument.Parse(File.ReadAllText(path));
            var root = json.RootElement;
            Assert.Equal(BenchReport.CurrentFormat, root.GetProperty("format").GetInt32());
            Assert.Equal("0.1.0+abc", root.GetProperty("app_version").GetString());
            Assert.Equal(125.25, root.GetProperty("app_startup_ms").GetDouble());
            Assert.Equal(401.5, root.GetProperty("startup_ms").GetProperty("interactive").GetDouble());
            Assert.Equal(16.8, root.GetProperty("frames").GetProperty("p99_ms").GetDouble());
            Assert.Equal(2, root.GetProperty("frames").GetProperty("worst")[0].GetProperty("frame").GetInt32());
            Assert.True(root.GetProperty("display").GetProperty("refresh_assumed").GetBoolean());
            Assert.Equal(128, root.GetProperty("gc").GetProperty("main_thread_allocated_bytes").GetInt64());
        }
        finally
        {
            if (Directory.Exists(folder))
            {
                Directory.Delete(folder, recursive: true);
            }
        }
    }

    [Fact]
    public void Output_uses_lf_line_endings()
    {
        Assert.DoesNotContain("\r", BenchReportWriter.Serialize(SampleReport()), StringComparison.Ordinal);
    }

    [Fact]
    public void A_missing_app_startup_is_written_as_null()
    {
        var json = BenchReportWriter.Serialize(SampleReport() with { AppStartupMs = null });

        using var document = JsonDocument.Parse(json);
        Assert.Equal(JsonValueKind.Null, document.RootElement.GetProperty("app_startup_ms").ValueKind);
    }

    private static BenchReport SampleReport()
    {
        double[] intervals = [16.6, 16.7, 16.8];
        return new BenchReport
        {
            CreatedUtc = new DateTimeOffset(2026, 9, 27, 12, 0, 0, TimeSpan.Zero),
            AppVersion = "0.1.0+abc",
            AppStartupMs = 125.25,
            GodotVersion = "4.7.2.stable.mono.official.ed1daf0bf",
            DotnetVersion = ".NET 10.0.12",
            Machine = new BenchMachine("Windows", "AMD Custom APU 0405", "AMD Custom GPU 0405", "forward_plus", "d3d12"),
            Display = new BenchDisplay(60, RefreshAssumed: true, 1280, 800, "enabled", Headless: false),
            StartupMs = new Dictionary<string, double>
            {
                [StartupMarks.FirstFrameDrawn] = 400.25,
                [StartupMarks.Interactive] = 401.5,
            },
            Frames = FrameTimeStats.Compute(intervals, 60),
            RenderMs = new BenchRenderTimes(1.25, 2.5),
            Gc = new BenchGc(0, 0, 0, 0, 4096, 128),
        };
    }
}
