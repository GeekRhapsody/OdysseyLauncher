using Launcher.Core.Scanning;

namespace Launcher.Core.Importing;

/// <summary>
/// Paths as gamelists write them: relative to the system's ROM folder (<c>./Game.zip</c>, <c>./images/Game-thumb.png</c>,
/// or with no <c>./</c>), the user's home (<c>~/ROMs/nes/Game.zip</c>), or absolute. Pure: nothing touches the disk.
/// </summary>
public static class GamelistPaths
{
    /// <summary>
    /// The full path <paramref name="value"/> names, resolved against <paramref name="baseDir"/>; null when it can't
    /// name a file on this machine (empty, a URL, or a rooted path with no drive, such as Batocera's <c>/userdata/roms/...</c> on Windows).
    /// </summary>
    public static string? Resolve(string value, string baseDir, string homeDir)
    {
        ArgumentNullException.ThrowIfNull(value);
        ArgumentNullException.ThrowIfNull(baseDir);
        ArgumentNullException.ThrowIfNull(homeDir);
        var path = value.Trim();
        if (path.Length == 0 || path.Contains("://", StringComparison.Ordinal))
        {
            return null;
        }

        try
        {
            if (path == "~" || path.StartsWith("~/", StringComparison.Ordinal) || path.StartsWith("~\\", StringComparison.Ordinal))
            {
                return Path.GetFullPath(Path.Combine(homeDir, path.Length > 2 ? path[2..] : string.Empty));
            }

            if (Path.IsPathFullyQualified(path))
            {
                return Path.GetFullPath(path);
            }

            return Path.IsPathRooted(path) ? null : Path.GetFullPath(Path.Combine(baseDir, path));
        }
        catch (Exception e) when (e is ArgumentException or NotSupportedException or PathTooLongException)
        {
            return null;
        }
    }

    /// <summary>
    /// <paramref name="fullPath"/>'s <c>rel_path</c> in <paramref name="romDir"/> (A4: '/'-separated, NFC), or null when
    /// it isn't inside it. Case is ignored on Windows, as the file system ignores it.
    /// </summary>
    public static string? RelPathUnder(string fullPath, string romDir)
    {
        ArgumentNullException.ThrowIfNull(fullPath);
        ArgumentNullException.ThrowIfNull(romDir);
        // A drive's root (S:\) keeps its separator when trimmed.
        var root = Path.TrimEndingDirectorySeparator(Path.GetFullPath(romDir));
        if (!Path.EndsInDirectorySeparator(root))
        {
            root += Path.DirectorySeparatorChar;
        }

        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        return fullPath.Length > root.Length && fullPath.StartsWith(root, comparison)
            ? PathKeys.ToRelPath(fullPath[root.Length..])
            : null;
    }

    /// <summary>Whether two folders are the same, ignoring a trailing separator (and case, on Windows).</summary>
    public static bool SameFolder(string a, string b) =>
        string.Equals(
            Path.TrimEndingDirectorySeparator(Path.GetFullPath(a)),
            Path.TrimEndingDirectorySeparator(Path.GetFullPath(b)),
            OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);
}
