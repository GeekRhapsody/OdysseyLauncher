using System.ComponentModel;
using System.Diagnostics;
using Launcher.Core.Launching;

namespace Launcher.Core.Platform;

/// <summary>
/// <see cref="Process"/> with <c>ArgumentList</c>, for platforms without a native runner (Linux, for now). The
/// arguments reach the emulator as they are, with no shell. It only follows the process it started, so a stub
/// launcher's game ends when the stub does.
/// </summary>
public sealed class PortableProcessRunner : IProcessRunner
{
    public IRunningProcess Start(LaunchPlan plan)
    {
        ArgumentNullException.ThrowIfNull(plan);
        var info = new ProcessStartInfo(plan.Executable)
        {
            UseShellExecute = false,
            WorkingDirectory = plan.WorkingDirectory,
        };
        foreach (var argument in plan.Arguments)
        {
            info.ArgumentList.Add(argument);
        }

        var process = new Process { StartInfo = info, EnableRaisingEvents = true };
        try
        {
            var started = Stopwatch.GetTimestamp();
            process.Start();
            return new RunningProcess(process, started);
        }
        catch (Win32Exception e)
        {
            process.Dispose();
            throw new ProcessStartException($"The OS couldn't start '{plan.Executable}': {e.Message} (error {e.NativeErrorCode}).", e.NativeErrorCode);
        }
    }

    private sealed class RunningProcess : IRunningProcess
    {
        private readonly Process _process;
        private volatile bool _terminated;

        public RunningProcess(Process process, long started)
        {
            _process = process;
            ProcessId = process.Id;
            Completion = WaitAsync(started);
        }

        public int ProcessId { get; }

        public Task<ProcessOutcome> Completion { get; }

        public void Terminate()
        {
            _terminated = true;
            try
            {
                _process.Kill(entireProcessTree: true);
            }
            catch (InvalidOperationException)
            {
                // It has already exited.
            }
        }

        public void Dispose() => _process.Dispose();

        private async Task<ProcessOutcome> WaitAsync(long started)
        {
            await _process.WaitForExitAsync().ConfigureAwait(false);
            return new ProcessOutcome(_process.ExitCode, Stopwatch.GetElapsedTime(started), _terminated);
        }
    }
}
