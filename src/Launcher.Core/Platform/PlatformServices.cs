using Launcher.Core.Platform.Windows;

namespace Launcher.Core.Platform;

/// <summary>Picks the implementation of each platform interface for the OS we're running on.</summary>
public static class PlatformServices
{
    public static IProcessRunner CreateProcessRunner() =>
        OperatingSystem.IsWindows() ? new WindowsProcessRunner() : new PortableProcessRunner();

    public static IWindowFocus CreateWindowFocus() =>
        OperatingSystem.IsWindows() ? new WindowsWindowFocus() : NullWindowFocus.Instance;
}
