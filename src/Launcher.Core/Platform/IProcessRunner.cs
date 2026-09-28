using Launcher.Core.Launching;

namespace Launcher.Core.Platform;

/// <summary>Starts emulators (ARCHITECTURE.md A1, A2).</summary>
public interface IProcessRunner
{
    /// <summary>
    /// Starts the plan's executable with its arguments and working directory. Does blocking OS calls: never call it
    /// on the main thread.
    /// </summary>
    /// <exception cref="ProcessStartException">The OS refused to start it.</exception>
    IRunningProcess Start(LaunchPlan plan);
}

/// <summary>A started emulator. Dispose it after <see cref="Completion"/> finishes.</summary>
public interface IRunningProcess : IDisposable
{
    /// <summary>The process the runner started (for a stub launcher, the stub).</summary>
    int ProcessId { get; }

    /// <summary>
    /// Completes when the game has ended. On Windows that's when every process in its job has exited, so a stub
    /// launcher that starts the real emulator and quits is followed to the end. Never faults.
    /// </summary>
    Task<ProcessOutcome> Completion { get; }

    /// <summary>Ends the game: every process it started. <see cref="Completion"/> then reports <c>Terminated</c>.</summary>
    void Terminate();
}

/// <param name="ExitCode">The exit code of the process the runner started.</param>
/// <param name="Elapsed">From the start until the last process ended, on a monotonic clock.</param>
/// <param name="Terminated">True if <see cref="IRunningProcess.Terminate"/> ended it.</param>
public readonly record struct ProcessOutcome(int ExitCode, TimeSpan Elapsed, bool Terminated);

/// <summary>The OS couldn't start the emulator. <see cref="Exception.Message"/> is written for the user.</summary>
public sealed class ProcessStartException : Exception
{
    public ProcessStartException()
    {
    }

    public ProcessStartException(string message)
        : base(message)
    {
    }

    public ProcessStartException(string message, Exception innerException)
        : base(message, innerException)
    {
    }

    public ProcessStartException(string message, int nativeErrorCode)
        : base(message)
    {
        NativeErrorCode = nativeErrorCode;
    }

    /// <summary>The OS error code (Win32 <c>GetLastError</c>, or errno), or 0.</summary>
    public int NativeErrorCode { get; }
}
