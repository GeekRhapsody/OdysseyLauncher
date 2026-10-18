using System.Diagnostics;
using static Launcher.Core.Platform.Windows.NativeMethods;

namespace Launcher.Core.Platform;

/// <summary>What a build tool did: its exit code (null if it was ended for taking too long) and everything it wrote.</summary>
public sealed record ToolResult(int? ExitCode, string Output);

/// <summary>
/// Runs a build tool (the export's <c>dotnet publish</c> of the update helper) to the end, and ends whatever it started
/// that's still running when it exits. A build leaves processes behind (MSVC's linker starts <c>vctip.exe</c>, its
/// telemetry uploader; MSBuild and the compiler can leave servers), and each inherited its parent's handles: under
/// Godot, the console wrapper's output pipe, which the wrapper waits on, so a leftover kept a release's export
/// waiting 15 minutes after it had finished (2026-10-18). On Windows the tool runs in a job object of its own, and
/// everything left in it is ended when the tool exits; elsewhere it just runs.
/// </summary>
public static class ToolProcess
{
    /// <summary>
    /// Runs <paramref name="start"/> (its output and errors are captured here) for at most <paramref name="timeout"/>.
    /// Throws what <see cref="Process.Start(ProcessStartInfo)"/> throws.
    /// </summary>
    public static ToolResult Run(ProcessStartInfo start, TimeSpan timeout)
    {
        ArgumentNullException.ThrowIfNull(start);
        start.UseShellExecute = false;
        start.RedirectStandardOutput = true;
        start.RedirectStandardError = true;
        var job = OperatingSystem.IsWindows() ? CreateKillJob() : 0;
        try
        {
            using var process = Process.Start(start) ?? throw new InvalidOperationException($"{start.FileName} didn't start.");
            if (job != 0 && !AssignProcessToJobObject(job, process.Handle))
            {
                // Not in the job (a parent's job that forbids nesting): it still runs, and leftovers may linger.
                CloseHandle(job);
                job = 0;
            }

            var stdout = process.StandardOutput.ReadToEndAsync();
            var stderr = process.StandardError.ReadToEndAsync();
            var exited = process.WaitForExit(timeout);
            if (!exited)
            {
                process.Kill(entireProcessTree: true);
            }

            // Before reading to the end: a leftover holding the pipes would keep them open.
            if (job != 0)
            {
                TerminateJobObject(job, 1);
            }

            process.WaitForExit();
            return new ToolResult(exited ? process.ExitCode : null, stdout.GetAwaiter().GetResult() + stderr.GetAwaiter().GetResult());
        }
        finally
        {
            if (job != 0)
            {
                CloseHandle(job);
            }
        }
    }

    /// <summary>A job that ends its processes when its last handle closes (if this process dies first, too); 0 if none could be made.</summary>
    private static unsafe nint CreateKillJob()
    {
        var job = CreateJobObject(0, 0);
        if (job == 0)
        {
            return 0;
        }

        var limits = default(JobObjectExtendedLimitInformation);
        limits.BasicLimitInformation.LimitFlags = JobObjectLimitKillOnJobClose;
        if (!SetInformationJobObject(job, JobObjectExtendedLimitInformationClass, &limits, sizeof(JobObjectExtendedLimitInformation)))
        {
            CloseHandle(job);
            return 0;
        }

        return job;
    }
}
