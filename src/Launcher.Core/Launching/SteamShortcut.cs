using System.Globalization;

namespace Launcher.Core.Launching;

/// <summary>
/// Reads a Steam game's app id from the internet shortcut (<c>.url</c>) Steam makes for it:
/// <code>
/// [InternetShortcut]
/// URL=steam://rungameid/1260320
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
    /// The app id in the <c>.url</c> file at <paramref name="path"/>, or null if it isn't a Steam game's shortcut
    /// (another extension, another URL, or a file that can't be read). Reads the file: not on the main thread.
    /// </summary>
    public static uint? ReadAppId(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (!Path.GetExtension(path).Equals(".url", StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        try
        {
            var file = new FileInfo(path);
            return file.Exists && file.Length <= MaxBytes ? ParseAppId(File.ReadAllText(path)) : null;
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
