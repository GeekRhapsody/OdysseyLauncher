using Launcher.Core.Platform.Windows;

namespace Launcher.Core.Platform;

/// <summary>Picks the implementation of each platform interface for the OS we're running on.</summary>
public static class PlatformServices
{
    public static IProcessRunner CreateProcessRunner() =>
        OperatingSystem.IsWindows() ? new WindowsProcessRunner() : new PortableProcessRunner();

    public static IWindowFocus CreateWindowFocus() =>
        OperatingSystem.IsWindows() ? new WindowsWindowFocus() : NullWindowFocus.Instance;

    /// <summary>Null where no decoder exists yet (Linux): derivatives aren't baked there, and covers show as plain boxes.</summary>
    public static Media.IImageDecoder? CreateImageDecoder() =>
        OperatingSystem.IsWindows() ? new WicImageDecoder() : null;
}
