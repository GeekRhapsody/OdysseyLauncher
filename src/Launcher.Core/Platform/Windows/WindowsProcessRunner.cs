using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Launcher.Core.Launching;
using static Launcher.Core.Platform.Windows.NativeMethods;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Starts the emulator inside a new job object, from its first instruction (<c>PROC_THREAD_ATTRIBUTE_JOB_LIST</c>),
/// so every process it starts is in the job too. The game has ended when the job has no processes left, which
/// follows stub launchers that start the real emulator and exit (ARCHITECTURE.md A1).
/// <list type="bullet">
/// <item>The job doesn't kill its processes when the launcher closes or crashes: the game keeps running.</item>
/// <item>A process may still leave the job if it asks to (<c>CREATE_BREAKAWAY_FROM_JOB</c>), instead of failing to start.</item>
/// <item>No handles are inherited, so the emulator can't hold the launcher's database files open.</item>
/// </list>
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class WindowsProcessRunner : IProcessRunner
{
    public IRunningProcess Start(LaunchPlan plan)
    {
        ArgumentNullException.ThrowIfNull(plan);
        var commandLine = WindowsCommandLine.Build(plan.Executable, plan.Arguments);
        if (commandLine.Length >= WindowsCommandLine.MaxLength)
        {
            throw new ProcessStartException(
                $"The command line for {plan.EmulatorName} is {commandLine.Length:N0} characters long, and Windows allows " +
                $"{WindowsCommandLine.MaxLength - 1:N0}. Shorten the ROM's path, or the profile's arguments.");
        }

        nint job = 0, port = 0;
        try
        {
            job = CreateJobObject(0, 0);
            if (job == 0)
            {
                throw Failure("create a job object for the game", Marshal.GetLastPInvokeError());
            }

            port = CreateIoCompletionPort(-1, 0, 0, 1);
            if (port == 0)
            {
                throw Failure("create a completion port for the game's job", Marshal.GetLastPInvokeError());
            }

            Configure(job, port);
            var (process, processId) = CreateInJob(plan, commandLine, job);
            var running = new RunningProcess(job, port, process, processId, Stopwatch.GetTimestamp());
            job = port = 0;
            return running;
        }
        finally
        {
            if (job != 0)
            {
                CloseHandle(job);
            }

            if (port != 0)
            {
                CloseHandle(port);
            }
        }
    }

    private static unsafe void Configure(nint job, nint port)
    {
        var association = new JobObjectAssociateCompletionPort { CompletionKey = RunningProcess.JobKey, CompletionPort = port };
        if (!SetInformationJobObject(job, JobObjectAssociateCompletionPortInformationClass, &association, sizeof(JobObjectAssociateCompletionPort)))
        {
            throw Failure("watch the game's job", Marshal.GetLastPInvokeError());
        }

        var limits = default(JobObjectExtendedLimitInformation);
        limits.BasicLimitInformation.LimitFlags = JobObjectLimitBreakawayOk;
        if (!SetInformationJobObject(job, JobObjectExtendedLimitInformationClass, &limits, sizeof(JobObjectExtendedLimitInformation)))
        {
            throw Failure("set up the game's job", Marshal.GetLastPInvokeError());
        }
    }

    private static unsafe (nint Process, int ProcessId) CreateInJob(LaunchPlan plan, string commandLine, nint job)
    {
        nint size = 0;
        InitializeProcThreadAttributeList(0, 1, 0, ref size);
        var attributes = Marshal.AllocHGlobal(size);
        try
        {
            if (!InitializeProcThreadAttributeList(attributes, 1, 0, ref size))
            {
                throw Failure("prepare the game's start-up attributes", Marshal.GetLastPInvokeError());
            }

            try
            {
                var jobHandle = job;
                if (!UpdateProcThreadAttribute(attributes, 0, ProcThreadAttributeJobList, &jobHandle, sizeof(nint), 0, 0))
                {
                    throw Failure("put the game in its job", Marshal.GetLastPInvokeError());
                }

                var startup = default(StartupInfoEx);
                startup.StartupInfo.Cb = sizeof(StartupInfoEx);
                startup.AttributeList = attributes;

                // CreateProcessW may write to the command line, so it gets its own buffer.
                var buffer = new char[commandLine.Length + 1];
                commandLine.CopyTo(0, buffer, 0, commandLine.Length);
                fixed (char* line = buffer)
                {
                    if (!CreateProcess(
                        plan.Executable, line, 0, 0, inheritHandles: false,
                        ExtendedStartupInfoPresent | CreateDefaultErrorMode, 0, plan.WorkingDirectory,
                        &startup, out var info))
                    {
                        throw StartFailure(plan, Marshal.GetLastPInvokeError());
                    }

                    CloseHandle(info.Thread);
                    return (info.Process, info.ProcessId);
                }
            }
            finally
            {
                DeleteProcThreadAttributeList(attributes);
            }
        }
        finally
        {
            Marshal.FreeHGlobal(attributes);
        }
    }

    private static ProcessStartException StartFailure(LaunchPlan plan, int error)
    {
        var exe = plan.Executable;
        var message = error switch
        {
            ErrorFileNotFound or ErrorPathNotFound => $"Windows can't find '{exe}'.",
            ErrorDirectory => $"The working folder '{plan.WorkingDirectory}' doesn't exist. Check working_dir in emulators.toml.",
            ErrorAccessDenied => $"Windows refused access to '{exe}'. Check the file's permissions, and that security software isn't blocking it.",
            ErrorBadExeFormat or ErrorExeMachineTypeMismatch => $"'{exe}' isn't a program this PC can run. It may be the wrong file, or built for another kind of processor.",
            ErrorElevationRequired => $"'{exe}' asks to run as administrator, which the launcher won't do for it. Turn off \"Run this program as an administrator\" in the file's Compatibility properties.",
            _ => $"Windows couldn't start '{exe}': {new Win32Exception(error).Message} (error {error}).",
        };
        return new ProcessStartException(message, error);
    }

    private static ProcessStartException Failure(string what, int error) =>
        new($"Windows couldn't {what}: {new Win32Exception(error).Message} (error {error}).", error);

    /// <summary>
    /// A dedicated thread waits on the job's completion port for "no active processes". Windows doesn't guarantee
    /// job messages arrive, so the wait also wakes every second to ask the job directly.
    /// </summary>
    private sealed class RunningProcess : IRunningProcess
    {
        public const nint JobKey = 1;
        private const nuint WakeKey = 2;
        private const uint PollMs = 1000;

        private readonly TaskCompletionSource<ProcessOutcome> _completion = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private readonly object _gate = new();
        private readonly long _startTimestamp;
        private nint _job;
        private nint _port;
        private nint _process;
        private bool _terminated;
        private bool _stopWaiting;

        public RunningProcess(nint job, nint port, nint process, int processId, long startTimestamp)
        {
            _job = job;
            _port = port;
            _process = process;
            _startTimestamp = startTimestamp;
            ProcessId = processId;
            new Thread(Wait) { IsBackground = true, Name = "Emulator job watcher" }.Start();
        }

        public int ProcessId { get; }

        public Task<ProcessOutcome> Completion => _completion.Task;

        public void Terminate()
        {
            lock (_gate)
            {
                if (_job != 0 && !_completion.Task.IsCompleted)
                {
                    _terminated = true;
                    TerminateJobObject(_job, 1);
                }
            }
        }

        /// <summary>Stops watching; the game isn't touched. If it's still running, <see cref="Completion"/> is cancelled.</summary>
        public void Dispose()
        {
            lock (_gate)
            {
                if (_port != 0 && !_stopWaiting)
                {
                    _stopWaiting = true;
                    PostQueuedCompletionStatus(_port, 0, WakeKey, 0);
                }
            }
        }

        private void Wait()
        {
            var detached = false;
            while (true)
            {
                if (GetQueuedCompletionStatus(_port, out var message, out var key, out _, PollMs))
                {
                    if (key == WakeKey)
                    {
                        detached = true;
                        break;
                    }

                    if (key == (nuint)JobKey && message == JobObjectMsgActiveProcessZero)
                    {
                        break;
                    }

                    continue;
                }

                if (Marshal.GetLastPInvokeError() != WaitTimeout || ActiveProcesses() == 0)
                {
                    break;
                }
            }

            var elapsed = Stopwatch.GetElapsedTime(_startTimestamp);
            var exitCode = -1;
            if (!detached && WaitForSingleObject(_process, 0) == 0 && GetExitCodeProcess(_process, out var code))
            {
                exitCode = unchecked((int)code);
            }

            bool terminated;
            lock (_gate)
            {
                terminated = _terminated;
                CloseHandle(_process);
                CloseHandle(_port);
                CloseHandle(_job);
                _process = _port = _job = 0;
            }

            if (detached)
            {
                _completion.TrySetCanceled();
            }
            else
            {
                _completion.TrySetResult(new ProcessOutcome(exitCode, elapsed, terminated));
            }
        }

        /// <summary>A failed query counts as still running, so only a real "empty" ends the wait.</summary>
        private unsafe uint ActiveProcesses()
        {
            var info = default(JobObjectBasicAccountingInformation);
            return QueryInformationJobObject(_job, JobObjectBasicAccountingInformationClass, &info, sizeof(JobObjectBasicAccountingInformation), 0)
                ? info.ActiveProcesses
                : 1;
        }
    }
}
