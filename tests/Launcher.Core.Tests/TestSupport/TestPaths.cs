namespace Launcher.Core.Tests.TestSupport;

/// <summary>Absolute paths for tests that configure a folder on another drive, rooted on whichever OS runs them.</summary>
public static class TestPaths
{
    /// <summary>
    /// <c>D:/Games</c> for <c>OnDrive('D', "Games")</c> on Windows; elsewhere <c>/mnt/d/Games</c>, since a drive letter
    /// isn't a root there (config resolves <c>D:/Games</c> against ConfigDir).
    /// </summary>
    public static string OnDrive(char drive, string path) =>
        OperatingSystem.IsWindows() ? $"{drive}:/{path}" : $"/mnt/{char.ToLowerInvariant(drive)}/{path}";
}
