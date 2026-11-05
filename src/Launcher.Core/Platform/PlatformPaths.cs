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
/// Windows: <c>%APPDATA%\OdysseyLauncher</c>, <c>%LOCALAPPDATA%\OdysseyLauncher</c> and its <c>cache</c>. Linux: the XDG
/// folders, <c>$XDG_CONFIG_HOME</c>, <c>$XDG_DATA_HOME</c> and <c>$XDG_CACHE_HOME</c> (by default <c>~/.config</c>,
/// <c>~/.local/share</c> and <c>~/.cache</c>), each with its <c>OdysseyLauncher</c> folder. A <c>portable.txt</c> beside
/// the launcher puts all three under its <c>userdata</c> folder: beside the executable or, in an AppImage, beside the
/// <c>.AppImage</c> file (the executable is in its read-only mount).
/// </summary>
public sealed record PlatformPaths(string ConfigDir, string DataDir, string CacheDir, string HomeDir) : IPlatformPaths
{
    public const string AppFolder = "OdysseyLauncher";
    public const string PortableMarker = "portable.txt";

    /// <summary>Works the paths out; creates nothing. Checks for the portable marker, so it does file I/O.</summary>
    public static PlatformPaths Detect(string executableDir) =>
        Detect(executableDir, Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), OperatingSystem.IsWindows(),
            Environment.GetEnvironmentVariable, File.Exists);

    /// <summary>
    /// <see cref="Detect(string)"/> with the OS, the environment and the file check passed in. Linux's paths are joined
    /// with <c>/</c>, so tests get the same answer on either OS.
    /// </summary>
    internal static PlatformPaths Detect(string executableDir, string home, bool windows, Func<string, string?> environment, Func<string, bool> fileExists)
    {
        ArgumentNullException.ThrowIfNull(executableDir);
        if (windows)
        {
            if (fileExists(Path.Combine(executableDir, PortableMarker)))
            {
                return InOneFolder(Path.Combine(executableDir, "userdata"), home);
            }

            var local = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), AppFolder);
            return new PlatformPaths(
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), AppFolder), local, Path.Combine(local, "cache"), home);
        }

        var launcherDir = AppImageDir(executableDir, environment) ?? executableDir;
        if (fileExists(Join(launcherDir, PortableMarker)))
        {
            var root = Join(launcherDir, "userdata");
            return new PlatformPaths(root, root, Join(root, "cache"), home);
        }

        return new PlatformPaths(
            Join(Xdg(environment, "XDG_CONFIG_HOME", home, ".config"), AppFolder),
            Join(Xdg(environment, "XDG_DATA_HOME", home, ".local/share"), AppFolder),
            Join(Xdg(environment, "XDG_CACHE_HOME", home, ".cache"), AppFolder),
            home);
    }

    /// <summary>The portable layout: config and data in <paramref name="root"/>, the cache in its <c>cache</c> folder.</summary>
    public static PlatformPaths InOneFolder(string root, string homeDir)
    {
        ArgumentNullException.ThrowIfNull(root);
        ArgumentNullException.ThrowIfNull(homeDir);
        return new PlatformPaths(root, root, Path.Combine(root, "cache"), homeDir);
    }

    /// <summary>The folder holding the <c>.AppImage</c> file when the launcher runs from one (<see cref="AppImageFile"/>). Null otherwise.</summary>
    internal static string? AppImageDir(string executableDir, Func<string, string?> environment)
    {
        var file = AppImageFile(executableDir, environment);
        if (file is null)
        {
            return null;
        }

        var slash = file.LastIndexOf('/');
        return slash == 0 ? "/" : file[..slash];
    }

    /// <summary>
    /// The <c>.AppImage</c> file the launcher runs from: its runtime sets <c>APPIMAGE</c> to the file and <c>APPDIR</c>
    /// to the mount (or the folder it was unpacked in) the executable is in. Null otherwise.
    /// </summary>
    internal static string? AppImageFile(string executableDir, Func<string, string?> environment)
    {
        var file = environment("APPIMAGE");
        var mount = environment("APPDIR")?.TrimEnd('/');
        if (string.IsNullOrEmpty(file) || !file.StartsWith('/') || string.IsNullOrEmpty(mount) || !mount.StartsWith('/'))
        {
            return null;
        }

        return executableDir == mount || executableDir.StartsWith(mount + "/", StringComparison.Ordinal) ? file : null;
    }

    /// <summary>An XDG base folder: the variable when it's an absolute path (the spec ignores a relative one), else its default under home.</summary>
    private static string Xdg(Func<string, string?> environment, string variable, string home, string fallback)
    {
        var value = environment(variable);
        return !string.IsNullOrEmpty(value) && value.StartsWith('/') ? value : Join(home, fallback);
    }

    private static string Join(string folder, string name) => folder.EndsWith('/') ? folder + name : folder + "/" + name;
}
