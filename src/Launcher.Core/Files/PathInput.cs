namespace Launcher.Core.Files;

/// <summary>Paths the user types into a picker (M7), and moving up and down folders.</summary>
public static class PathInput
{
    private static readonly char[] Forbidden = OperatingSystem.IsWindows() ? ['<', '>', '"', '|', '?', '*'] : ['\0'];

    /// <summary>
    /// Turns what the user typed into a full path, or says why it can't be one. Quotes around it (Explorer's "Copy as
    /// path") are dropped, '/' works as '\' on Windows (so <c>//nas/roms</c> is a share), <c>C:</c> means that drive's
    /// root, <c>~</c> the user's folder, and a relative path is taken from <paramref name="relativeTo"/>.
    /// Doesn't check the path exists.
    /// </summary>
    public static (string? Path, string? Problem) Resolve(string typed, string? relativeTo, string homeDir)
    {
        ArgumentNullException.ThrowIfNull(typed);
        ArgumentNullException.ThrowIfNull(homeDir);
        var text = typed.Trim();
        if (text.Length >= 2 && text[0] == '"' && text[^1] == '"')
        {
            text = text[1..^1].Trim();
        }

        if (text.Length == 0)
        {
            return (null, "Type a folder, such as D:\\ROMs or \\\\nas\\roms.");
        }

        if (OperatingSystem.IsWindows())
        {
            text = text.Replace('/', '\\');
        }

        if (text == "~" || text.StartsWith("~" + Path.DirectorySeparatorChar, StringComparison.Ordinal))
        {
            text = homeDir + text[1..];
        }

        if (OperatingSystem.IsWindows())
        {
            if (text.Length == 2 && char.IsAsciiLetter(text[0]) && text[1] == ':')
            {
                text += "\\";
            }

            if (text.StartsWith(@"\\", StringComparison.Ordinal))
            {
                var parts = text[2..].Split('\\', StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length < 2)
                {
                    return (null, parts.Length == 0
                        ? "Type the computer's name and a share: \\\\server\\share."
                        : $"Add the share's name: \\\\{parts[0]}\\share. A computer's shares can't be listed here.");
                }
            }
        }

        if (text.IndexOfAny(Forbidden) >= 0 || text.Any(char.IsControl) || HasColonInside(text))
        {
            return (null, OperatingSystem.IsWindows()
                ? $"'{typed.Trim()}' isn't a valid path: it can't contain < > \" | ? * or a ':' after the drive."
                : $"'{typed.Trim()}' isn't a valid path.");
        }

        try
        {
            if (!Path.IsPathFullyQualified(text))
            {
                if (relativeTo is null || !Path.IsPathFullyQualified(relativeTo))
                {
                    return (null, "Type the full path, starting with a drive (D:\\) or a share (\\\\server\\share).");
                }

                text = Path.Combine(relativeTo, text);
            }

            return (Path.GetFullPath(text), null);
        }
        catch (Exception e) when (e is ArgumentException or NotSupportedException or PathTooLongException)
        {
            return (null, $"'{typed.Trim()}' isn't a valid path: {e.Message}");
        }
    }

    /// <summary>The folder above <paramref name="folder"/>; null at a drive's or share's root (the pickers' top level).</summary>
    public static string? Parent(string folder)
    {
        ArgumentNullException.ThrowIfNull(folder);
        var root = Path.GetPathRoot(folder);
        var trimmed = Path.TrimEndingDirectorySeparator(folder);
        if (root is null || trimmed.Length <= Path.TrimEndingDirectorySeparator(root).Length)
        {
            return null;
        }

        return Path.GetDirectoryName(trimmed);
    }

    /// <summary>A folder's own name, or the root itself (<c>C:\</c>, <c>\\nas\roms</c>).</summary>
    public static string NameOf(string folder)
    {
        ArgumentNullException.ThrowIfNull(folder);
        var trimmed = Path.TrimEndingDirectorySeparator(folder);
        var name = Path.GetFileName(trimmed);
        return name.Length == 0 || Parent(folder) is null ? folder : name;
    }

    /// <summary>True when <paramref name="path"/> is on a network share (a UNC path; a mapped drive isn't detected here).</summary>
    public static bool IsShare(string path) =>
        OperatingSystem.IsWindows() && path is not null && path.StartsWith(@"\\", StringComparison.Ordinal);

    /// <summary>A ':' anywhere but after a drive letter (Windows); alternate data streams aren't folders.</summary>
    private static bool HasColonInside(string text)
    {
        if (!OperatingSystem.IsWindows())
        {
            return false;
        }

        var first = text.IndexOf(':', StringComparison.Ordinal);
        return first >= 0 && (first != 1 || text.IndexOf(':', 2) >= 0);
    }
}
