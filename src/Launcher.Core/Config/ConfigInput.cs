using Launcher.Core.Scraping;

namespace Launcher.Core.Config;

/// <summary>
/// Checks what the user entered on the settings screen before it's saved (M7), with a reason written for them. The
/// config loader validates again when <see cref="ConfigWriter"/> saves; these catch what it can't know, such as a
/// folder that doesn't exist. The folder and file checks do I/O: never on the main thread.
/// </summary>
public static class ConfigInput
{
    /// <summary>The most a credential can be: every provider's are far shorter.</summary>
    public const int MaxCredentialLength = 512;

    /// <summary>Null when <paramref name="path"/> is an existing folder given in full.</summary>
    public static string? CheckFolder(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (path.Trim().Length == 0)
        {
            return "Choose a folder.";
        }

        if (!Path.IsPathFullyQualified(path))
        {
            return $"'{path}' isn't a full path. Start it with a drive (D:\\) or a share (\\\\server\\share).";
        }

        try
        {
            return Directory.Exists(path) ? null : $"The folder '{path}' doesn't exist, or can't be reached.";
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or ArgumentException)
        {
            return $"The folder '{path}' can't be read: {e.Message}";
        }
    }

    /// <summary>Null when <paramref name="path"/> is a program the launcher can run: an existing file, and on Windows an .exe (A5).</summary>
    public static string? CheckExecutable(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (!Path.IsPathFullyQualified(path))
        {
            return $"'{path}' isn't a full path.";
        }

        var extension = Path.GetExtension(path);
        if (OperatingSystem.IsWindows())
        {
            if (extension.Equals(".bat", StringComparison.OrdinalIgnoreCase) || extension.Equals(".cmd", StringComparison.OrdinalIgnoreCase))
            {
                return $"{Path.GetFileName(path)} is a batch file, which the launcher won't run: cmd.exe re-reads its arguments, so a ROM named with & or % would break it. Choose the emulator's .exe.";
            }

            if (!extension.Equals(".exe", StringComparison.OrdinalIgnoreCase))
            {
                return $"{Path.GetFileName(path)} isn't a program. Choose the emulator's .exe.";
            }
        }

        return File.Exists(path) ? null : $"'{path}' doesn't exist.";
    }

    /// <summary>Null when <paramref name="value"/> can be a credential: not blank, one line, no control characters. Never quotes the value.</summary>
    public static string? CheckCredential(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (value.Trim().Length == 0)
        {
            return "It's empty. To remove it, choose Clear instead.";
        }

        if (value.Length > MaxCredentialLength)
        {
            return $"It's longer than {MaxCredentialLength} characters, which no provider's is. Check it was pasted correctly.";
        }

        return value.Any(char.IsControl) ? "It has a line break or another control character. Check it was pasted correctly." : null;
    }

    /// <summary>Null when <paramref name="provider"/> and <paramref name="fallback"/> are known providers, each named once.</summary>
    public static string? CheckProviders(string provider, IReadOnlyList<string> fallback)
    {
        ArgumentNullException.ThrowIfNull(provider);
        ArgumentNullException.ThrowIfNull(fallback);
        foreach (var id in fallback.Prepend(provider))
        {
            if (!ConfigLoader.Scrapers.Contains(id))
            {
                return $"'{id}' isn't a provider. The providers are {string.Join(", ", ConfigLoader.Scrapers)}.";
            }
        }

        if (fallback.Contains(provider, StringComparer.Ordinal))
        {
            return $"{provider} is the default provider, so it can't be a fallback too.";
        }

        return fallback.Distinct(StringComparer.Ordinal).Count() == fallback.Count ? null : "A fallback is listed twice.";
    }

    /// <summary>The credential keys each provider has, as secrets.toml names them, with a label for the settings screen.</summary>
    public static IReadOnlyList<(string Key, string Label, bool Secret)> CredentialKeys(string provider) => provider switch
    {
        ScraperIds.ScreenScraper =>
        [
            ("dev_id", "Developer ID", false),
            ("dev_password", "Developer password", true),
            ("username", "Username", false),
            ("password", "Password", true),
        ],
        ScraperIds.SteamGridDb => [("api_key", "API key", true)],
        ScraperIds.Igdb => [("client_id", "Client ID", false), ("client_secret", "Client secret", true)],
        _ => [],
    };
}
