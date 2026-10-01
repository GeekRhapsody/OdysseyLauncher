using System.Runtime.InteropServices;

namespace Launcher.Core.Platform.Windows;

/// <summary>The kernel32, user32, advapi32 and powrprof calls the Windows platform code uses. Structs are blittable.</summary>
internal static unsafe partial class NativeMethods
{
    public const int ErrorFileNotFound = 2;
    public const int ErrorPathNotFound = 3;
    public const int ErrorAccessDenied = 5;
    public const int ErrorBadExeFormat = 193;
    public const int ErrorDirectory = 267;
    public const int ErrorExeMachineTypeMismatch = 216;
    public const int ErrorElevationRequired = 740;
    public const int ErrorInsufficientBuffer = 122;
    public const int WaitTimeout = 258;

    public const uint ExtendedStartupInfoPresent = 0x0008_0000;
    public const uint CreateUnicodeEnvironment = 0x0000_0400;
    public const uint CreateDefaultErrorMode = 0x0400_0000;
    public const nint ProcThreadAttributeJobList = 0x0002_000D;

    public const int JobObjectBasicAccountingInformationClass = 1;
    public const int JobObjectAssociateCompletionPortInformationClass = 7;
    public const int JobObjectExtendedLimitInformationClass = 9;
    public const uint JobObjectLimitBreakawayOk = 0x0000_0800;
    public const uint JobObjectMsgActiveProcessZero = 4;

    public const uint Infinite = 0xFFFF_FFFF;
    public const uint AsfwAny = 0xFFFF_FFFF;
    public const int SwRestore = 9;
    public const int SwShowMinNoActive = 7;
    public const uint InputKeyboard = 1;
    public const uint KeyEventFKeyUp = 0x0002;
    public const ushort VkMenu = 0x12;
    public const uint FlashWTray = 0x0000_0002;
    public const uint FlashWTimerNoFg = 0x0000_000C;

    public const uint TokenAdjustPrivileges = 0x0020;
    public const uint TokenQuery = 0x0008;
    public const uint SePrivilegeEnabled = 0x0000_0002;
    public const int ErrorNotAllAssigned = 1300;
    public const uint EwxShutdown = 0x0000_0001;
    public const uint EwxReboot = 0x0000_0002;
    public const uint EwxPowerOff = 0x0000_0008;
    public const uint EwxForceIfHung = 0x0000_0010;
    public const uint ShtdnReasonFlagPlanned = 0x8000_0000;

    [StructLayout(LayoutKind.Sequential)]
    public struct StartupInfo
    {
        public int Cb;
        public nint Reserved;
        public nint Desktop;
        public nint Title;
        public int X;
        public int Y;
        public int XSize;
        public int YSize;
        public int XCountChars;
        public int YCountChars;
        public int FillAttribute;
        public int Flags;
        public short ShowWindow;
        public short Reserved2Size;
        public nint Reserved2;
        public nint StdInput;
        public nint StdOutput;
        public nint StdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct StartupInfoEx
    {
        public StartupInfo StartupInfo;
        public nint AttributeList;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct ProcessInformation
    {
        public nint Process;
        public nint Thread;
        public int ProcessId;
        public int ThreadId;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JobObjectAssociateCompletionPort
    {
        public nint CompletionKey;
        public nint CompletionPort;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JobObjectBasicLimitInformation
    {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public nuint MinimumWorkingSetSize;
        public nuint MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public nuint Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct IoCounters
    {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JobObjectExtendedLimitInformation
    {
        public JobObjectBasicLimitInformation BasicLimitInformation;
        public IoCounters IoInfo;
        public nuint ProcessMemoryLimit;
        public nuint JobMemoryLimit;
        public nuint PeakProcessMemoryUsed;
        public nuint PeakJobMemoryUsed;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JobObjectBasicAccountingInformation
    {
        public long TotalUserTime;
        public long TotalKernelTime;
        public long ThisPeriodTotalUserTime;
        public long ThisPeriodTotalKernelTime;
        public uint TotalPageFaultCount;
        public uint TotalProcesses;
        public uint ActiveProcesses;
        public uint TotalTerminatedProcesses;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct KeyboardInput
    {
        public ushort VirtualKey;
        public ushort ScanCode;
        public uint Flags;
        public uint Time;
        public nint ExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct MouseInput
    {
        public int Dx;
        public int Dy;
        public uint MouseData;
        public uint Flags;
        public uint Time;
        public nint ExtraInfo;
    }

    [StructLayout(LayoutKind.Explicit)]
    public struct InputUnion
    {
        [FieldOffset(0)]
        public MouseInput Mouse;

        [FieldOffset(0)]
        public KeyboardInput Keyboard;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct Input
    {
        public uint Type;
        public InputUnion Data;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct FlashWInfo
    {
        public uint Size;
        public nint Window;
        public uint Flags;
        public uint Count;
        public uint Timeout;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct Luid
    {
        public uint LowPart;
        public int HighPart;
    }

    /// <summary><c>TOKEN_PRIVILEGES</c> with room for one privilege.</summary>
    [StructLayout(LayoutKind.Sequential)]
    public struct TokenPrivileges
    {
        public uint PrivilegeCount;
        public Luid Luid;
        public uint Attributes;
    }

    /// <summary><c>SYSTEM_POWER_CAPABILITIES</c> (76 bytes): only the sleep states are read.</summary>
    [StructLayout(LayoutKind.Explicit, Size = 76)]
    public struct SystemPowerCapabilities
    {
        [FieldOffset(3)]
        public byte SystemS1;

        [FieldOffset(4)]
        public byte SystemS2;

        [FieldOffset(5)]
        public byte SystemS3;
    }

    // ---- kernel32 --------------------------------------------------------------------------------

    [LibraryImport("kernel32.dll", EntryPoint = "CreateJobObjectW", SetLastError = true)]
    public static partial nint CreateJobObject(nint jobAttributes, nint name);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool SetInformationJobObject(nint job, int infoClass, void* info, int length);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool QueryInformationJobObject(nint job, int infoClass, void* info, int length, nint returnLength);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool TerminateJobObject(nint job, uint exitCode);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    public static partial nint CreateIoCompletionPort(nint fileHandle, nint existingPort, nuint completionKey, uint threads);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool GetQueuedCompletionStatus(
        nint port, out uint bytesTransferred, out nuint completionKey, out nint overlapped, uint milliseconds);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool PostQueuedCompletionStatus(nint port, uint bytesTransferred, nuint completionKey, nint overlapped);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool InitializeProcThreadAttributeList(nint list, int count, int flags, ref nint size);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool UpdateProcThreadAttribute(
        nint list, uint flags, nint attribute, void* value, nint size, nint previousValue, nint returnSize);

    [LibraryImport("kernel32.dll")]
    public static partial void DeleteProcThreadAttributeList(nint list);

    [LibraryImport("kernel32.dll", EntryPoint = "CreateProcessW", SetLastError = true, StringMarshalling = StringMarshalling.Utf16)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool CreateProcess(
        string applicationName,
        char* commandLine,
        nint processAttributes,
        nint threadAttributes,
        [MarshalAs(UnmanagedType.Bool)] bool inheritHandles,
        uint creationFlags,
        nint environment,
        string currentDirectory,
        StartupInfoEx* startupInfo,
        out ProcessInformation processInformation);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool GetExitCodeProcess(nint process, out uint exitCode);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    public static partial uint WaitForSingleObject(nint handle, uint milliseconds);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool CloseHandle(nint handle);

    [LibraryImport("kernel32.dll")]
    public static partial uint GetCurrentThreadId();

    [LibraryImport("kernel32.dll")]
    public static partial uint GetCurrentProcessId();

    [LibraryImport("kernel32.dll")]
    public static partial nint GetCurrentProcess();

    // ---- user32 ----------------------------------------------------------------------------------

    [LibraryImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool AllowSetForegroundWindow(uint processId);

    [LibraryImport("user32.dll")]
    public static partial nint GetForegroundWindow();

    [LibraryImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool SetForegroundWindow(nint window);

    [LibraryImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool BringWindowToTop(nint window);

    [LibraryImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool ShowWindow(nint window, int command);

    [LibraryImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool IsIconic(nint window);

    [LibraryImport("user32.dll")]
    public static partial uint GetWindowThreadProcessId(nint window, out uint processId);

    [LibraryImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool AttachThreadInput(uint attach, uint attachTo, [MarshalAs(UnmanagedType.Bool)] bool doAttach);

    [LibraryImport("user32.dll")]
    public static partial nint SetActiveWindow(nint window);

    [LibraryImport("user32.dll")]
    public static partial nint SetFocus(nint window);

    [LibraryImport("user32.dll", SetLastError = true)]
    public static partial uint SendInput(uint count, Input* inputs, int size);

    [LibraryImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool FlashWindowEx(in FlashWInfo info);

    [LibraryImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool ExitWindowsEx(uint flags, uint reason);

    // ---- advapi32 --------------------------------------------------------------------------------

    [LibraryImport("advapi32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool OpenProcessToken(nint process, uint desiredAccess, out nint token);

    [LibraryImport("advapi32.dll", EntryPoint = "LookupPrivilegeValueW", SetLastError = true, StringMarshalling = StringMarshalling.Utf16)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool LookupPrivilegeValue(string? systemName, string name, out Luid luid);

    [LibraryImport("advapi32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool AdjustTokenPrivileges(
        nint token, [MarshalAs(UnmanagedType.Bool)] bool disableAll, TokenPrivileges* newState, uint bufferLength, nint previousState, nint returnLength);

    // ---- powrprof --------------------------------------------------------------------------------

    /// <summary>The three arguments and the result are Win32 <c>BOOLEAN</c>s (a byte).</summary>
    [LibraryImport("powrprof.dll", SetLastError = true)]
    public static partial byte SetSuspendState(byte hibernate, byte force, byte wakeupEventsDisabled);

    [LibraryImport("powrprof.dll")]
    public static partial byte GetPwrCapabilities(SystemPowerCapabilities* capabilities);
}
