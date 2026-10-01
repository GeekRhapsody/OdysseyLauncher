using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Microsoft.Win32;
using static Launcher.Core.Platform.Windows.NativeMethods;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// The Steam client's state from what it writes to the user's registry, <c>HKCU\Software\Valve\Steam</c>:
/// <list type="bullet">
/// <item><c>SteamExe</c>, the client's program;</item>
/// <item><c>ActiveProcess\pid</c>, the running client's process (0 once it has closed);</item>
/// <item><c>RunningAppID</c>, the game it's running now (0 for none);</item>
/// <item><c>Apps\&lt;app id&gt;</c>: <c>Installed</c>, <c>Running</c> and <c>Updating</c>, each a DWORD 0 or 1.</item>
/// </list>
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class WindowsSteamClient : ISteamClient
{
    private const string SteamKey = @"Software\Valve\Steam";

    public string? ClientPath
    {
        get
        {
            using var steam = Registry.CurrentUser.OpenSubKey(SteamKey);
            if (steam?.GetValue("SteamExe") is not string exe || exe.Length == 0)
            {
                return null;
            }

            var path = Path.GetFullPath(exe);
            return File.Exists(path) ? path : null;
        }
    }

    public SteamAppState GetAppState(uint appId)
    {
        using var steam = Registry.CurrentUser.OpenSubKey(SteamKey);
        if (steam is null)
        {
            return default;
        }

        using var active = steam.OpenSubKey("ActiveProcess");
        var clientRunning = IsAlive(Dword(active, "pid"));
        var current = Dword(steam, "RunningAppID") == appId;
        using var app = steam.OpenSubKey(@"Apps\" + appId.ToString(CultureInfo.InvariantCulture));
        return new SteamAppState(
            clientRunning,
            Installed: Dword(app, "Installed") == 1,
            Running: Dword(app, "Running") == 1,
            current,
            Updating: Dword(app, "Updating") == 1);
    }

    /// <summary>A DWORD value, or 0 if it's missing or of another type.</summary>
    private static uint Dword(RegistryKey? key, string name) =>
        key?.GetValue(name) is int value ? unchecked((uint)value) : 0;

    private static bool IsAlive(uint processId)
    {
        if (processId == 0)
        {
            return false;
        }

        var process = OpenProcess(Synchronize, inheritHandle: false, processId);
        if (process == 0)
        {
            // Gone, or not ours to open (then it's there).
            return Marshal.GetLastPInvokeError() == ErrorAccessDenied;
        }

        try
        {
            return WaitForSingleObject(process, 0) == WaitTimeout;
        }
        finally
        {
            CloseHandle(process);
        }
    }
}
