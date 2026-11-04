namespace Launcher.Core.Launching;

/// <summary>
/// The games installed in Vita3K, for profiles with <c>installs = "vita3k"</c> (ARCHITECTURE.md A5, Vita3K's games).
/// Vita3K runs a game from its emulated memory card: <c>-r &lt;title id&gt;</c> boots one installed there, and a package
/// or a game's folder given on its command line is installed first, every time, over the copy already there (a copy of
/// up to a few gigabytes). So the launcher boots a game that's installed by its title id, and hands over only one that
/// isn't. Where Vita3K keeps them is worked out as its own start-up does (its <c>app/src/app_init.cpp</c>,
/// <c>config/src/config.cpp</c> and <c>config/include/config/config.h</c>, read on 2026-10-28 for Windows and on
/// 2026-11-04 for Linux), which differs by OS. Does file I/O: never on the main thread.
/// </summary>
public static class Vita3KGames
{
    /// <summary>The <c>installs</c> value of an emulator profile this knows the games of.</summary>
    public const string Kind = "vita3k";

    /// <summary>
    /// Windows: the folder of Vita3K's emulated storage (it holds <c>ux0</c>, the memory card): <c>portable/fs</c> when a
    /// <c>portable</c> folder is beside the executable; else the <c>pref-path</c> set in <c>config.yml</c> beside the
    /// executable; else SDL's preference folder, <c>%APPDATA%\Vita3K\Vita3K</c>.
    /// </summary>
    /// <param name="applicationData">The user's roaming application data (<c>Environment.SpecialFolder.ApplicationData</c>).</param>
    public static string StorageFolder(string executable, string applicationData)
    {
        ArgumentNullException.ThrowIfNull(executable);
        ArgumentNullException.ThrowIfNull(applicationData);
        var folder = Path.GetDirectoryName(executable) ?? executable;
        return Storage(
            Path.Combine(folder, "portable"), Path.Combine(folder, "config.yml"), folder, Path.Combine(applicationData, "Vita3K", "Vita3K"));
    }

    /// <summary>
    /// Linux: the folder of Vita3K's emulated storage: <c>portable/fs</c> when a <c>portable</c> folder is beside the
    /// program, its links followed (an AppImage's is beside the <c>.AppImage</c> file, which Vita3K reads from
    /// <c>$APPIMAGE</c>; any other build's beside its real program, SDL's base folder); else the <c>pref-path</c> set in
    /// <c>config.yml</c> in its XDG config folder, <c>$XDG_CONFIG_HOME/Vita3K</c>; else its XDG data folder's,
    /// <c>$XDG_DATA_HOME/Vita3K/Vita3K</c>.
    /// </summary>
    /// <param name="configHome"><c>$XDG_CONFIG_HOME</c>, else <c>~/.config</c> (<c>Environment.SpecialFolder.ApplicationData</c> on Linux).</param>
    /// <param name="dataHome"><c>$XDG_DATA_HOME</c>, else <c>~/.local/share</c> (<c>Environment.SpecialFolder.LocalApplicationData</c> on Linux).</param>
    public static string LinuxStorageFolder(string executable, string configHome, string dataHome)
    {
        ArgumentNullException.ThrowIfNull(executable);
        ArgumentNullException.ThrowIfNull(configHome);
        ArgumentNullException.ThrowIfNull(dataHome);
        var folder = Path.GetDirectoryName(executable) ?? executable;
        // The program a link (a vita3k on the PATH) leads to, as /proc/self/exe names it to SDL. The launch found the
        // program, so the link resolves.
        var program = File.ResolveLinkTarget(executable, returnFinalTarget: true)?.FullName ?? executable;
        return Storage(
            Path.Combine(Path.GetDirectoryName(program) ?? program, "portable"),
            Path.Combine(configHome, "Vita3K", "config.yml"),
            folder,
            Path.Combine(dataHome, "Vita3K", "Vita3K"));
    }

    /// <param name="relativeTo">Where a relative <c>pref-path</c> starts: Vita3K's working folder, by default its executable's.</param>
    private static string Storage(string portable, string config, string relativeTo, string preferences)
    {
        if (Directory.Exists(portable))
        {
            return Path.Combine(portable, "fs");
        }

        try
        {
            if (File.Exists(config) && PrefPath(File.ReadAllText(config)) is { } prefPath)
            {
                return Path.GetFullPath(prefPath, relativeTo);
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or ArgumentException or NotSupportedException)
        {
            // Unreadable, or a path the OS can't use: Vita3K won't start with it either, and says why.
        }

        return preferences;
    }

    /// <summary>Whether the game <paramref name="titleId"/> is installed in the storage at <paramref name="storageFolder"/>.</summary>
    public static bool IsInstalled(string storageFolder, string titleId)
    {
        ArgumentNullException.ThrowIfNull(storageFolder);
        ArgumentNullException.ThrowIfNull(titleId);
        return Directory.Exists(Path.Combine(storageFolder, "ux0", "app", titleId));
    }

    /// <summary>Whether Vita3K can install <paramref name="path"/> from its command line: a <c>.vpk</c> or <c>.zip</c> package, or a game's folder.</summary>
    public static bool CanInstall(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        var extension = Path.GetExtension(path);
        return Directory.Exists(path)
            || extension.Equals(".vpk", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".zip", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// The <c>pref-path</c> a <c>config.yml</c>'s text sets, or null when it sets none or an empty one. Vita3K writes the
    /// file with yaml-cpp, one top-level key a line, so only that line is read: its value plain, or quoted in single
    /// quotes (<c>''</c> a quote) or double quotes (a backslash escaping the next character).
    /// </summary>
    public static string? PrefPath(string yaml)
    {
        ArgumentNullException.ThrowIfNull(yaml);
        const string Key = "pref-path:";
        foreach (var line in yaml.Split('\n'))
        {
            if (!line.StartsWith(Key, StringComparison.Ordinal))
            {
                continue;
            }

            var value = line[Key.Length..].Trim();
            if (value.Length >= 2 && value[0] == '\'' && value[^1] == '\'')
            {
                value = value[1..^1].Replace("''", "'", StringComparison.Ordinal);
            }
            else if (value.Length >= 2 && value[0] == '"' && value[^1] == '"')
            {
                var unescaped = new System.Text.StringBuilder(value.Length);
                for (var i = 1; i < value.Length - 1; i++)
                {
                    if (value[i] == '\\' && i + 1 < value.Length - 1)
                    {
                        i++;
                    }

                    unescaped.Append(value[i]);
                }

                value = unescaped.ToString();
            }
            else if (value is "~" or "null")
            {
                value = string.Empty;
            }

            return value.Length == 0 ? null : value;
        }

        return null;
    }
}
