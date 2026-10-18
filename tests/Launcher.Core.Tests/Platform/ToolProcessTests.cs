using System.Diagnostics;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Platform;

public sealed class ToolProcessTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    [Fact]
    public void A_tools_leftover_process_is_ended_when_it_exits()
    {
        // The fake starts a copy of itself that sleeps 30 s, then exits 1.5 s later (time for the copy to log itself):
        // a build leaving vctip.exe behind.
        var log = _dir.Combine("tool.json");
        var start = new ProcessStartInfo(Path.Combine(FakeEmulator.OutputDir, FakeEmulator.ExeName))
        {
            ArgumentList = { "--fake-spawn=30000", "--fake-sleep=1500", $"--fake-log={log}", "--fake-exit=3" },
        };
        var watch = Stopwatch.StartNew();

        var result = ToolProcess.Run(start, TimeSpan.FromSeconds(60));

        Assert.Equal(3, result.ExitCode);
        Assert.True(watch.Elapsed < TimeSpan.FromSeconds(20), $"It waited {watch.Elapsed} for the leftover's output pipe.");
        if (OperatingSystem.IsWindows())
        {
            var child = WaitForLog(log + ".child");
            Assert.True(HasExited(child.ProcessId), "The leftover should have been ended with the tool.");
        }
    }

    [Fact]
    public void A_tool_that_takes_too_long_is_ended()
    {
        var start = new ProcessStartInfo(Path.Combine(FakeEmulator.OutputDir, FakeEmulator.ExeName)) { ArgumentList = { "--fake-sleep=30000" } };

        var result = ToolProcess.Run(start, TimeSpan.FromMilliseconds(500));

        Assert.Null(result.ExitCode);
    }

    private static FakeLog WaitForLog(string path)
    {
        var watch = Stopwatch.StartNew();
        while (!File.Exists(path))
        {
            Assert.True(watch.Elapsed < TimeSpan.FromSeconds(10), "The leftover never started.");
            Thread.Sleep(50);
        }

        return FakeEmulator.ReadLog(path);
    }

    private static bool HasExited(int processId)
    {
        try
        {
            using var process = Process.GetProcessById(processId);
            return process.WaitForExit(5000);
        }
        catch (ArgumentException)
        {
            return true;
        }
    }
}
