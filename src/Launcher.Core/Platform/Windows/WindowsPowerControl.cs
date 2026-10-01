using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using static Launcher.Core.Platform.Windows.NativeMethods;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Restart and shutdown through <c>ExitWindowsEx</c>, sleep through <c>SetSuspendState</c>. Each needs the shutdown
/// privilege, which every interactive user holds but a process has to enable in its own token first. Windows then
/// asks every app to close, as the Start menu does; an app that's hung is closed anyway. Shutdown is a full one,
/// not Fast Startup's hybrid. Sleep is offered only where the PC has S1–S3 sleep: a Modern Standby PC can't be put
/// to sleep by an app.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed unsafe class WindowsPowerControl : IPowerControl
{
    private const string ShutdownPrivilege = "SeShutdownPrivilege";

    private readonly Lazy<bool> _canSleep = new(CanSleep);

    public string? Unavailable(PowerAction action) =>
        action == PowerAction.Sleep && !_canSleep.Value ? "This PC can only sleep from its power button (it uses Modern Standby)." : null;

    public string? Request(PowerAction action)
    {
        if (Unavailable(action) is { } unavailable)
        {
            return unavailable;
        }

        if (EnableShutdownPrivilege() is { } problem)
        {
            return problem;
        }

        var ok = action switch
        {
            PowerAction.Restart => ExitWindowsEx(EwxReboot | EwxForceIfHung, ShtdnReasonFlagPlanned),
            PowerAction.ShutDown => ExitWindowsEx(EwxShutdown | EwxPowerOff | EwxForceIfHung, ShtdnReasonFlagPlanned),
            _ => SetSuspendState(0, 0, 0) != 0,
        };
        return ok ? null : Failure(action switch
        {
            PowerAction.Restart => "restart",
            PowerAction.ShutDown => "shut down",
            _ => "go to sleep",
        }, Marshal.GetLastPInvokeError());
    }

    private static bool CanSleep()
    {
        SystemPowerCapabilities capabilities;
        return GetPwrCapabilities(&capabilities) != 0 && (capabilities.SystemS1 | capabilities.SystemS2 | capabilities.SystemS3) != 0;
    }

    /// <summary>Enables the shutdown privilege in this process's token: null when it's on, otherwise why not.</summary>
    private static string? EnableShutdownPrivilege()
    {
        if (!OpenProcessToken(GetCurrentProcess(), TokenAdjustPrivileges | TokenQuery, out var token))
        {
            return Failure("open the launcher's security token", Marshal.GetLastPInvokeError());
        }

        try
        {
            if (!LookupPrivilegeValue(null, ShutdownPrivilege, out var luid))
            {
                return Failure("look up the shutdown privilege", Marshal.GetLastPInvokeError());
            }

            var privileges = new TokenPrivileges { PrivilegeCount = 1, Luid = luid, Attributes = SePrivilegeEnabled };

            // It succeeds without enabling anything when the user doesn't hold the privilege, and says so in the last error.
            var ok = AdjustTokenPrivileges(token, false, &privileges, 0, 0, 0);
            var error = Marshal.GetLastPInvokeError();
            return !ok ? Failure("enable the shutdown privilege", error)
                : error == ErrorNotAllAssigned ? "Windows doesn't let this account shut down or restart the PC (a policy may forbid it)."
                : null;
        }
        finally
        {
            CloseHandle(token);
        }
    }

    private static string Failure(string what, int error) =>
        $"Windows couldn't {what}: {new Win32Exception(error).Message} (error {error}).";
}
