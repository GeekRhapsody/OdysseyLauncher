using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// The libc and libsystemd calls the Linux platform code uses: <c>kill</c>, and sd-bus, for logind. Only sd-bus's
/// non-variadic functions, since .NET can't call a C function with variable arguments on Linux; each returns a
/// negative errno on failure.
/// </summary>
[SupportedOSPlatform("linux")]
internal static unsafe partial class LinuxNativeMethods
{
    public const int Eperm = 1;
    public const int Esrch = 3;
    public const int Sigkill = 9;

    // glibc's soname: a bare "libc" can find the development linker script, libc.so, which isn't a library.
    private const string Libc = "libc.so.6";
    private const string Systemd = "libsystemd.so.0";

    /// <summary>Sends a signal; a negative <paramref name="pid"/> sends it to that process group, and signal 0 only checks.</summary>
    [LibraryImport(Libc, EntryPoint = "kill", SetLastError = true)]
    public static partial int Kill(int pid, int signal);

    /// <summary>sd-bus's <c>sd_bus_error</c>; all zeros is <c>SD_BUS_ERROR_NULL</c>.</summary>
    [StructLayout(LayoutKind.Sequential)]
    public struct SdBusError
    {
        public nint Name;
        public nint Message;
        public int NeedFree;
    }

    [LibraryImport(Systemd, EntryPoint = "sd_bus_open_system")]
    public static partial int SdBusOpenSystem(out nint bus);

    [LibraryImport(Systemd, EntryPoint = "sd_bus_flush_close_unref")]
    public static partial nint SdBusFlushCloseUnref(nint bus);

    [LibraryImport(Systemd, EntryPoint = "sd_bus_message_new_method_call", StringMarshalling = StringMarshalling.Utf8)]
    public static partial int SdBusMessageNewMethodCall(nint bus, out nint message, string destination, string path, string iface, string member);

    [LibraryImport(Systemd, EntryPoint = "sd_bus_message_append_basic")]
    public static partial int SdBusMessageAppendBasic(nint message, byte type, void* value);

    [LibraryImport(Systemd, EntryPoint = "sd_bus_call")]
    public static partial int SdBusCall(nint bus, nint message, ulong timeoutMicroseconds, SdBusError* error, out nint reply);

    [LibraryImport(Systemd, EntryPoint = "sd_bus_message_read_basic")]
    public static partial int SdBusMessageReadBasic(nint message, byte type, void* value);

    [LibraryImport(Systemd, EntryPoint = "sd_bus_message_unref")]
    public static partial nint SdBusMessageUnref(nint message);

    [LibraryImport(Systemd, EntryPoint = "sd_bus_error_free")]
    public static partial void SdBusErrorFree(SdBusError* error);
}
