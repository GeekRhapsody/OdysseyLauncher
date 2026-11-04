using Launcher.Core.Platform.Linux;
using Launcher.Core.Platform.Windows;

namespace Launcher.Core.Platform;

/// <summary>Picks the implementation of each platform interface for the OS we're running on.</summary>
public static class PlatformServices
{
    public static IProcessRunner CreateProcessRunner() =>
        OperatingSystem.IsWindows() ? new WindowsProcessRunner() : new PortableProcessRunner();

    public static IWindowFocus CreateWindowFocus() =>
        OperatingSystem.IsWindows() ? new WindowsWindowFocus() : NullWindowFocus.Instance;

    /// <summary>The Steam client's state, for following Steam games: the registry on Windows, <c>registry.vdf</c> on Linux.</summary>
    public static ISteamClient CreateSteamClient() =>
        OperatingSystem.IsWindows()
            ? new WindowsSteamClient()
            : new LinuxSteamClient(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "/proc");

    /// <summary>
    /// Restart, shutdown and sleep, for the power menu. On Linux the first <see cref="IPowerControl.Unavailable"/> asks
    /// logind over D-Bus, so make it on a worker.
    /// </summary>
    public static IPowerControl CreatePowerControl() =>
        OperatingSystem.IsWindows() ? new WindowsPowerControl()
        : OperatingSystem.IsLinux() ? new LinuxPowerControl()
        : NullPowerControl.Instance;

    /// <summary>The battery and the network, for the status indicators.</summary>
    public static IDeviceStatus CreateDeviceStatus() =>
        OperatingSystem.IsWindows() ? new WindowsDeviceStatus() : new LinuxDeviceStatus("/");

    /// <summary>The drives and quick-access folders the pickers start from (M7).</summary>
    public static IFileLocations CreateFileLocations(string homeDir) =>
        OperatingSystem.IsWindows() ? new WindowsFileLocations(homeDir) : new LinuxFileLocations(homeDir, Environment.UserName, "/proc/self/mountinfo");

    /// <summary>Installs a downloaded update once the launcher has quit; on Linux, nothing (it can't update itself yet).</summary>
    public static IUpdateInstaller CreateUpdateInstaller() =>
        OperatingSystem.IsWindows() ? new WindowsUpdateInstaller() : NullUpdateInstaller.Instance;

    /// <summary>
    /// Null where Core has no decoder (Linux), so nothing is baked by Core alone there; the app brings Godot's instead
    /// (<c>GodotImageDecoder</c>), which bakes the themes' logos.
    /// </summary>
    public static Media.IImageDecoder? CreateImageDecoder() =>
        OperatingSystem.IsWindows() ? new WicImageDecoder() : null;

    /// <summary>
    /// Plays a game's videos in its details screen and a theme's card videos: Media Foundation on Windows, the FFmpeg
    /// the AppImage carries on Linux (loaded by the first video opened, so this does no I/O).
    /// </summary>
    public static Media.IVideoDecoder? CreateVideoDecoder() =>
        OperatingSystem.IsWindows() ? new MediaFoundationVideoDecoder()
        : OperatingSystem.IsLinux() ? new FfmpegVideoDecoder()
        : null;

    /// <summary>Shows a game's manual; null where no renderer exists yet (Linux), so manuals are listed but not shown.</summary>
    public static Media.IPdfRenderer? CreatePdfRenderer() =>
        OperatingSystem.IsWindows() ? new WindowsPdfRenderer() : null;
}
