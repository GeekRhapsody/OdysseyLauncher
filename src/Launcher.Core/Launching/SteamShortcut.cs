using System.Globalization;

namespace Launcher.Core.Launching;

/// <summary>
/// Reads a Steam game's app id from the shortcut Steam makes for it: on Windows an internet shortcut (<c>.url</c>), on
/// Linux a desktop shortcut (<c>.desktop</c>, whose <c>Exec</c> line hands Steam the same URL):
/// <code>
/// [InternetShortcut]
/// URL=steam://rungameid/1260320
///
/// [Desktop Entry]
/// Exec=steam steam://rungameid/1260320
/// </code>
/// <c>steam://run/&lt;id&gt;</c> and <c>steam://launch/&lt;id&gt;</c> are read too. A non-Steam game added to Steam
/// has a 64-bit game id in its shortcut, not an app id, and Steam doesn't report its state, so it isn't one.
/// </summary>
public static class SteamShortcut
{
    /// <summary>Bigger than any internet shortcut; a bigger file isn't read.</summary>
    private const long MaxBytes = 64 * 1024;

    private static readonly string[] Prefixes = ["steam://rungameid/", "steam://run/", "steam://launch/"];

    /// <summary>
    /// The app id in the <c>.url</c> or <c>.desktop</c> file at <paramref name="path"/>, or null if it isn't a Steam
    /// game's shortcut (another extension, another URL, or a file that can't be read). Reads the file: not on the main thread.
    /// </summary>
    public static uint? ReadAppId(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        var extension = Path.GetExtension(path);
        var desktop = extension.Equals(".desktop", StringComparison.OrdinalIgnoreCase);
        if (!desktop && !extension.Equals(".url", StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        try
        {
            var file = new FileInfo(path);
            if (!file.Exists || file.Length > MaxBytes)
            {
                return null;
            }

            var text = File.ReadAllText(path);
            return desktop ? ParseDesktopAppId(text) : ParseAppId(text);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    /// <summary>The app id in an internet shortcut's text, from its <c>[InternetShortcut]</c> section's <c>URL</c>.</summary>
    public static uint? ParseAppId(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        return Url(text) is { } url ? AppIdOf(url) : null;
    }

    /// <summary>
    /// The app id in a desktop shortcut's text: the first argument of its <c>Exec</c> line that is a <c>steam://</c> URL,
    /// whatever program it's handed to (<c>steam</c>, or Flathub's Steam through <c>flatpak run</c>).
    /// </summary>
    public static uint? ParseDesktopAppId(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        foreach (var argument in DesktopEntry.Read(text)?.Arguments ?? [])
        {
            if (argument.StartsWith("steam://", StringComparison.OrdinalIgnoreCase))
            {
                return AppIdOf(argument);
            }
        }

        return null;
    }

    /// <summary>The app id in a <c>steam://</c> URL that runs a game, or null.</summary>
    public static uint? AppIdOf(string url)
    {
        ArgumentNullException.ThrowIfNull(url);
        foreach (var prefix in Prefixes)
        {
            if (!url.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            // The id ends at the URL's end, or at the '/' or '?' before anything Steam passes to the game.
            var rest = url.AsSpan(prefix.Length);
            var end = rest.IndexOfAny('/', '?');
            var digits = end < 0 ? rest : rest[..end];
            return uint.TryParse(digits, NumberStyles.None, CultureInfo.InvariantCulture, out var appId) && appId != 0
                ? appId
                : null;
        }

        return null;
    }

    private static string? Url(string text)
    {
        var inSection = false;
        foreach (var raw in text.Split('\n'))
        {
            var line = raw.Trim();
            if (line.StartsWith('['))
            {
                inSection = line.Equals("[InternetShortcut]", StringComparison.OrdinalIgnoreCase);
                continue;
            }

            var equals = line.IndexOf('=', StringComparison.Ordinal);
            if (inSection && equals > 0 && line.AsSpan(0, equals).Trim().Equals("URL", StringComparison.OrdinalIgnoreCase))
            {
                return line[(equals + 1)..].Trim();
            }
        }

        return null;
    }
}
