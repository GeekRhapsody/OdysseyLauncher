namespace Launcher.Core.Platform;

/// <summary>Where the launcher keeps its files (ARCHITECTURE.md A4).</summary>
public interface IPlatformPaths
{
    /// <summary>settings/systems/emulators/secrets .toml, themes/, models/, media/ (user overrides).</summary>
    string ConfigDir { get; }

    /// <summary>library.db, userdata.db, media/, scraped/, logs/.</summary>
    string DataDir { get; }

    /// <summary>Regenerable without the network: textures/, models/.</summary>
    string CacheDir { get; }

    string HomeDir { get; }
}

/// <summary>
/// Windows: <c>%APPDATA%\OdysseyLauncher</c>, <c>%LOCALAPPDATA%\OdysseyLauncher</c> and its <c>cache</c>.
/// A <c>portable.txt</c> next to the executable puts all three under <c>&lt;exe dir&gt;\userdata\</c>.
/// Linux (XDG) comes later.
/// </summary>
public sealed record PlatformPaths(string ConfigDir, string DataDir, string CacheDir, string HomeDir) : IPlatformPaths
{
    public const string AppFolder = "OdysseyLauncher";
    public const string PortableMarker = "portable.txt";

    /// <summary>Works the paths out; creates nothing. Checks for the portable marker, so it does file I/O.</summary>
    public static PlatformPaths Detect(string executableDir)
    {
        ArgumentNullException.ThrowIfNull(executableDir);
        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (File.Exists(Path.Combine(executableDir, PortableMarker)))
        {
            var root = Path.Combine(executableDir, "userdata");
            return new PlatformPaths(root, root, Path.Combine(root, "cache"), home);
        }

        var config = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), AppFolder);
        var data = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), AppFolder);
        return new PlatformPaths(config, data, Path.Combine(data, "cache"), home);
    }
}
