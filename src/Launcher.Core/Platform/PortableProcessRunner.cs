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
    /// <summary>What an AppImage's runtime sets for the launcher (A4): not the emulator's, which may be an AppImage itself.</summary>
    private static readonly string[] AppImageVariables = ["APPIMAGE", "APPDIR", "ARGV0", "OWD"];

    public IRunningProcess Start(LaunchPlan plan)
    {
        ArgumentNullException.ThrowIfNull(plan);
        var (program, arguments, workingDirectory) = plan.RunFile ? RunFileCommand(plan) : (plan.Executable, plan.Arguments, plan.WorkingDirectory);
        var info = new ProcessStartInfo(program)
        {
            UseShellExecute = false,
            WorkingDirectory = workingDirectory,
        };
        foreach (var argument in arguments)
        {
            info.ArgumentList.Add(argument);
        }

        LeaveOutAppImageVariables(info.Environment);

        var process = new Process { StartInfo = info, EnableRaisingEvents = true };
        try
        {
            var started = Stopwatch.GetTimestamp();
            process.Start();
            if (plan.Detached)
            {
                // Something else runs the game: what was started isn't followed.
                process.Dispose();
                return new FinishedProcess(Stopwatch.GetElapsedTime(started));
            }

            return new RunningProcess(process, started);
        }
        catch (Win32Exception e)
        {
            process.Dispose();
            throw new ProcessStartException($"The OS couldn't start '{plan.Executable}': {e.Message} (error {e.NativeErrorCode}).", e.NativeErrorCode);
        }
    }

    /// <summary>
    /// How a game's own file runs (A5 run_file), as a Linux desktop would run it: a <c>.desktop</c> shortcut by its
    /// Exec line, in its Path folder if it names one; a <c>.sh</c> script with bash (so it needn't be executable);
    /// anything else (an AppImage, a program) as it is. Reads the shortcut: never on the main thread.
    /// </summary>
    internal static (string Program, IReadOnlyList<string> Arguments, string WorkingDirectory) RunFileCommand(LaunchPlan plan)
    {
        var file = plan.Executable;
        var extension = Path.GetExtension(file);
        if (extension.Equals(".sh", StringComparison.OrdinalIgnoreCase))
        {
            return (ProgramSearch.System.Find(["bash", "sh"]) ?? "/bin/sh", [file], plan.WorkingDirectory);
        }

        if (!extension.Equals(".desktop", StringComparison.OrdinalIgnoreCase))
        {
            return (file, plan.Arguments, plan.WorkingDirectory);
        }

        string text;
        try
        {
            text = File.ReadAllText(file);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            throw new ProcessStartException($"The shortcut '{file}' couldn't be read: {e.Message}");
        }

        var command = DesktopEntry.Read(text)
            ?? throw new ProcessStartException($"The shortcut '{file}' has no command to run (an Exec line in its [Desktop Entry]).");
        var program = ProgramSearch.IsBareName(command.Program) ? ProgramSearch.System.Find([command.Program]) ?? command.Program : command.Program;
        return (program, command.Arguments, command.WorkingDirectory ?? plan.WorkingDirectory);
    }

    internal static void LeaveOutAppImageVariables(IDictionary<string, string?> environment)
    {
        foreach (var name in AppImageVariables)
        {
            environment.Remove(name);
        }
    }

    private sealed class FinishedProcess(TimeSpan elapsed) : IRunningProcess
    {
        public int ProcessId => 0;

        public Task<ProcessOutcome> Completion { get; } = Task.FromResult(new ProcessOutcome(0, elapsed, false));

        public void Terminate()
        {
        }

        public void Dispose()
        {
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
