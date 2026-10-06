using Launcher.Core.Config;

namespace Launcher.Core.Media;

/// <summary>
/// Where the media folder is (A4): <c>[paths] media</c> in settings.toml (2026-10-04), else <c>DataDir/media</c>.
/// Stored paths (<c>media.path</c>, <see cref="MediaFile.Path"/>, <see cref="StoredMedia.RelativePath"/>, a derivative's
/// key) start with <c>media/</c>, which stands for the media folder wherever it is, so moving it changes no row and no
/// derivative.
/// </summary>
public static class MediaFolder
{
    /// <summary>The media folder's name in DataDir, and the first part of every stored path.</summary>
    public const string Name = "media";

    /// <summary>The default media folder: <c>DataDir/media</c>.</summary>
    public static string Default(string dataDir)
    {
        ArgumentNullException.ThrowIfNull(dataDir);
        return Path.Combine(dataDir, Name);
    }

    /// <summary>The media folder <paramref name="settings"/> name, else the default in <paramref name="dataDir"/>.</summary>
    public static string Of(Settings settings, string dataDir)
    {
        ArgumentNullException.ThrowIfNull(settings);
        return settings.MediaDir ?? Default(dataDir);
    }

    /// <summary>
    /// A stored path's file: <c>media/ps2/covers/Game.png</c> is <c>&lt;media folder&gt;\ps2\covers\Game.png</c>.
    /// Either separator is read.
    /// </summary>
    public static string FullPath(string mediaDir, string stored)
    {
        ArgumentNullException.ThrowIfNull(mediaDir);
        ArgumentNullException.ThrowIfNull(stored);
        var rest = stored.Length > Name.Length && stored.StartsWith(Name, StringComparison.Ordinal) && stored[Name.Length] is '/' or '\\'
            ? stored[(Name.Length + 1)..]
            : stored;
        return Path.Combine(mediaDir, rest.Replace('/', Path.DirectorySeparatorChar));
    }

    /// <summary>Whether two folders are the same folder (ignoring case on Windows, and a trailing separator).</summary>
    public static bool Same(string a, string b) =>
        string.Equals(Normalise(a), Normalise(b), PathComparison);

    /// <summary>Whether <paramref name="folder"/> is inside <paramref name="parent"/> (not the same folder).</summary>
    public static bool Inside(string folder, string parent)
    {
        var child = Normalise(folder);
        var root = Normalise(parent);
        if (child.Length <= root.Length || !child.StartsWith(root, PathComparison))
        {
            return false;
        }

        return Path.EndsInDirectorySeparator(root) || child[root.Length] == Path.DirectorySeparatorChar;
    }

    internal static StringComparison PathComparison =>
        OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;

    /// <summary>Full, with the OS's separators and no trailing separator (a drive's or share's root keeps its own).</summary>
    internal static string Normalise(string folder)
    {
        ArgumentNullException.ThrowIfNull(folder);
        return Path.TrimEndingDirectorySeparator(Path.GetFullPath(folder));
    }
}
