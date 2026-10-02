using Launcher.Core.Platform.Windows;

namespace Launcher.Core.Platform;

/// <summary>Picks the implementation of each platform interface for the OS we're running on.</summary>
public static class PlatformServices
{
    public static IProcessRunner CreateProcessRunner() =>
        OperatingSystem.IsWindows() ? new WindowsProcessRunner() : new PortableProcessRunner();

    public static IWindowFocus CreateWindowFocus() =>
        OperatingSystem.IsWindows() ? new WindowsWindowFocus() : NullWindowFocus.Instance;

    /// <summary>The Steam client's state, for following Steam games; null where it isn't read yet (Linux).</summary>
    public static ISteamClient? CreateSteamClient() =>
        OperatingSystem.IsWindows() ? new WindowsSteamClient() : null;

    /// <summary>Restart, shutdown and sleep, for the power menu.</summary>
    public static IPowerControl CreatePowerControl() =>
        OperatingSystem.IsWindows() ? new WindowsPowerControl() : NullPowerControl.Instance;

    /// <summary>The battery and the network, for the status indicators.</summary>
    public static IDeviceStatus CreateDeviceStatus() =>
        OperatingSystem.IsWindows() ? new WindowsDeviceStatus() : new PortableDeviceStatus();

    /// <summary>The drives and quick-access folders the pickers start from (M7).</summary>
    public static IFileLocations CreateFileLocations(string homeDir) =>
        OperatingSystem.IsWindows() ? new WindowsFileLocations(homeDir) : new PortableFileLocations(homeDir);

    /// <summary>Null where no decoder exists yet (Linux): derivatives aren't baked there, and covers show as plain boxes.</summary>
    public static Media.IImageDecoder? CreateImageDecoder() =>
        OperatingSystem.IsWindows() ? new WicImageDecoder() : null;
}
