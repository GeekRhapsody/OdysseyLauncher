using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Launcher.Core.Launching;
using Launcher.Core.Platform.Linux;

namespace Launcher.Core.Platform;

/// <summary>
/// <see cref="Process"/> with <c>ArgumentList</c>, for platforms without a native runner (Linux). The arguments reach
/// the emulator as they are, with no shell. On Linux the game runs in a process group of its own, made by util-linux's
/// <c>setsid</c>, which executes the program in its place (the same pid, so the same exit code), and the game has
/// ended once the group is empty, so a stub launcher is followed until the program it started ends, as a job is on
/// Windows (2026-11-04). A program that makes a session of its own escapes it, as a breakaway escapes a job. Without
/// <c>setsid</c>, only the process started is followed.
/// </summary>
public sealed class PortableProcessRunner : IProcessRunner
{
    /// <summary>What an AppImage's runtime sets for the launcher (A4): not the emulator's, which may be an AppImage itself.</summary>
    private static readonly string[] AppImageVariables = ["APPIMAGE", "APPDIR", "ARGV0", "OWD"];

    /// <summary>How often a game's process group is checked once the process started has ended (Windows asks its job as often).</summary>
    private static readonly TimeSpan GroupPoll = TimeSpan.FromSeconds(1);

    public IRunningProcess Start(LaunchPlan plan)
    {
        ArgumentNullException.ThrowIfNull(plan);
        var (program, arguments, workingDirectory) = plan.RunFile ? RunFileCommand(plan) : (plan.Executable, plan.Arguments, plan.WorkingDirectory);
        var setsid = OperatingSystem.IsLinux() && !plan.Detached ? ProgramSearch.System.Find(["setsid"]) : null;
        var info = new ProcessStartInfo(setsid ?? program)
        {
            UseShellExecute = false,
            WorkingDirectory = workingDirectory,
        };
        if (setsid is not null && OperatingSystem.IsLinux())
        {
            info.ArgumentList.Add(Runnable(program, plan.Executable));
        }

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

            return new RunningProcess(process, started, grouped: setsid is not null);
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

    /// <summary>
    /// The program's path, checked as starting it would check it: <c>setsid</c> starts whatever it's given, and a
    /// program it can't run would be a game that exits at once (127 or 126) rather than a launch that failed.
    /// </summary>
    [SupportedOSPlatform("linux")]
    private static string Runnable(string program, string executable)
    {
        var path = ProgramSearch.IsBareName(program) ? ProgramSearch.System.Find([program]) : Path.GetFullPath(program);
        if (path is null || !File.Exists(path))
        {
            throw StartFailure(executable, 2);
        }

        const UnixFileMode Execute = UnixFileMode.UserExecute | UnixFileMode.GroupExecute | UnixFileMode.OtherExecute;
        return (File.GetUnixFileMode(path) & Execute) != 0 ? path : throw StartFailure(executable, 13);
    }

    private static ProcessStartException StartFailure(string executable, int error) =>
        new($"The OS couldn't start '{executable}': {Marshal.GetPInvokeErrorMessage(error)} (error {error}).", error);

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
        private readonly bool _grouped;
        private volatile bool _terminated;

        /// <param name="grouped">The process leads a process group of its own (setsid), which is the game.</param>
        public RunningProcess(Process process, long started, bool grouped)
        {
            _process = process;
            _grouped = grouped;
            ProcessId = process.Id;
            Completion = WaitAsync(started);
        }

        public int ProcessId { get; }

        public Task<ProcessOutcome> Completion { get; }

        public void Terminate()
        {
            _terminated = true;
            if (_grouped && OperatingSystem.IsLinux())
            {
                LinuxNativeMethods.Kill(-ProcessId, LinuxNativeMethods.Sigkill);
            }

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
            while (_grouped && OperatingSystem.IsLinux() && GroupAlive(ProcessId))
            {
                await Task.Delay(GroupPoll).ConfigureAwait(false);
            }

            return new ProcessOutcome(_process.ExitCode, Stopwatch.GetElapsedTime(started), _terminated);
        }

        /// <summary>Whether any process is left in the group (one it may not signal, such as a setuid program's, counts).</summary>
        [SupportedOSPlatform("linux")]
        private static bool GroupAlive(int group) =>
            LinuxNativeMethods.Kill(-group, 0) == 0 || Marshal.GetLastPInvokeError() == LinuxNativeMethods.Eperm;
    }
}
