using System.Text.Json;
using System.Text.Json.Serialization;
using Launcher.Core.Config;

namespace Launcher.Core.Theming.Downloads;

/// <summary>One of a listed theme's screenshots.</summary>
/// <param name="Image">The image, an absolute path inside the list's checkout (it may be missing).</param>
public sealed record ThemeScreenshot(string Image, string Caption);

/// <summary>
/// What a listed theme brings (A6 Downloading themes), as <c>odyssey-scrape inspect-theme --json</c> counts it: the part
/// ES-DE's variant and colour-scheme counts play. Every value is what the theme itself sets, not the base theme's.
/// </summary>
/// <param name="SystemCards">Systems (and Favourites, Recently played and All games) with a card or a logo of their own.</param>
/// <param name="Templates">Game templates the theme declares, its own or extending the base's.</param>
/// <param name="Menus">Whether it sets the menus' colours or font (<c>[ui.menu]</c>).</param>
/// <param name="CardVideos">Whether a system card plays a video.</param>
/// <param name="GameVideos">Whether a game template plays the focused game's video.</param>
public sealed record ThemeCovers(int SystemCards, int Templates, bool Menus, bool CardVideos, bool GameVideos)
{
    /// <summary>Counts what a loaded theme sets itself.</summary>
    public static ThemeCovers Of(Theme theme)
    {
        ArgumentNullException.ThrowIfNull(theme);
        var cards = new HashSet<string>(StringComparer.Ordinal);
        foreach (var (id, system) in theme.Systems)
        {
            if (system.Model is not null)
            {
                cards.Add(id);
            }
        }

        foreach (var id in theme.Logos.Keys)
        {
            cards.Add(id);
        }

        var templates = theme.Templates.Values.Where(t => t.ThemeId == theme.Id).ToList();
        return new ThemeCovers(
            cards.Count,
            templates.Count,
            theme.Menu.SetsColour || theme.Menu.Font is not null,
            theme.Systems.Values.Any(s => s.Video is not null),
            templates.Any(t => t.VideoSlot >= 0));
    }
}

/// <summary>A theme the list offers (A6 Downloading themes).</summary>
/// <param name="Id">The folder it's installed in, <c>ConfigDir/themes/&lt;id&gt;/</c>: a valid theme id, never a built-in one.</param>
/// <param name="Url">The theme's git repository.</param>
/// <param name="Commit">The commit the list pins: what the owner tested. An update is the list pinning another.</param>
/// <param name="Version">For display only.</param>
/// <param name="MinAppVersion">The oldest launcher that can use it; null for any.</param>
/// <param name="New">Shown as new.</param>
/// <param name="Deprecated">Shown faded, as soon to leave the list.</param>
public sealed record ThemeListing(
    string Id,
    string Name,
    string Author,
    string Description,
    string Url,
    string Commit,
    string? Version,
    string? MinAppVersion,
    bool New,
    bool Deprecated,
    ThemeCovers? Covers,
    IReadOnlyList<ThemeScreenshot> Screenshots)
{
    /// <summary>The commit's first seven characters, as git shows it.</summary>
    public string ShortCommit => Commit[..7];
}

/// <summary>The theme list, read from <c>themes.json</c>.</summary>
/// <param name="LatestAppVersion">The launcher's latest release, as the list knows it; null when it doesn't say.</param>
/// <param name="Themes">The usable entries, sorted by name; entries with problems are left out with a diagnostic.</param>
public sealed record ThemeIndex(string? LatestAppVersion, IReadOnlyList<ThemeListing> Themes, IReadOnlyList<Diagnostic> Diagnostics)
{
    public static ThemeIndex Empty(IReadOnlyList<Diagnostic> diagnostics) => new(null, [], diagnostics);
}

/// <summary>
/// Reads the theme list's <c>themes.json</c> (A6 Downloading themes). Never throws for a bad file: a file it can't read
/// at all gives an empty list and an error, and a bad entry is left out with a warning naming it.
/// </summary>
public static class ThemeIndexReader
{
    public const string FileName = "themes.json";
    public const int SupportedFormat = 1;

    /// <param name="listFolder">The list's checkout, which the screenshots' paths are relative to.</param>
    /// <param name="reservedIds">The built-in themes' ids (the base theme's among them): a listed theme may not take one.</param>
    /// <param name="allowFileUrls">
    /// Whether a theme may be a <c>file://</c> repository as well as an https one: only for a list read from a local
    /// folder (<c>--themes-list</c>), for testing a list before publishing it.
    /// </param>
    public static ThemeIndex Read(string json, string source, string listFolder, IReadOnlyCollection<string> reservedIds, bool allowFileUrls = false)
    {
        ArgumentNullException.ThrowIfNull(json);
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(listFolder);
        ArgumentNullException.ThrowIfNull(reservedIds);
        var diagnostics = new List<Diagnostic>();
        IndexFile? file;
        try
        {
            file = JsonSerializer.Deserialize(json, ThemeIndexJsonContext.Default.IndexFile);
        }
        catch (JsonException e)
        {
            diagnostics.Add(Problem(Severity.Error, (int)(e.LineNumber ?? -1) + 1, string.Empty, $"isn't valid JSON: {e.Message}"));
            return ThemeIndex.Empty(diagnostics);
        }

        if (file is null)
        {
            diagnostics.Add(Problem(Severity.Error, 0, string.Empty, "is empty"));
            return ThemeIndex.Empty(diagnostics);
        }

        if (file.Format != SupportedFormat)
        {
            diagnostics.Add(Problem(Severity.Error, 0, "format",
                $"format {file.Format} isn't supported: this version reads format {SupportedFormat}, so update the launcher"));
            return ThemeIndex.Empty(diagnostics);
        }

        var latest = file.LatestAppVersion is { } text && AppVersion.TryParse(text, out _) ? text : null;
        if (file.LatestAppVersion is not null && latest is null)
        {
            diagnostics.Add(Problem(Severity.Warning, 0, "latest_app_version", $"'{file.LatestAppVersion}' isn't a version"));
        }

        var themes = new List<ThemeListing>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var root = Path.GetFullPath(listFolder);
        for (var i = 0; i < (file.Themes?.Count ?? 0); i++)
        {
            var entry = file.Themes![i];
            var key = $"themes[{i}]";
            if (Check(entry, key, reservedIds, seen, allowFileUrls) is { } problem)
            {
                diagnostics.Add(Problem(Severity.Warning, 0, key, problem + ", so it isn't offered"));
                continue;
            }

            var screenshots = new List<ThemeScreenshot>();
            foreach (var shot in entry!.Screenshots ?? [])
            {
                if (shot is { Image: { Length: > 0 } image, Caption: { Length: > 0 } caption } && Inside(root, image) is { } path)
                {
                    screenshots.Add(new ThemeScreenshot(path, caption));
                }
                else
                {
                    diagnostics.Add(Problem(Severity.Warning, 0, key + ".screenshots",
                        "a screenshot needs an image inside the list and a caption, so it's left out"));
                }
            }

            seen.Add(entry.Id!);
            themes.Add(new ThemeListing(
                entry.Id!,
                entry.Name!,
                entry.Author ?? string.Empty,
                entry.Description ?? string.Empty,
                entry.Url!,
                entry.Commit!.ToLowerInvariant(),
                entry.Version,
                entry.MinAppVersion,
                entry.New,
                entry.Deprecated,
                entry.Covers is { } covers
                    ? new ThemeCovers(covers.SystemCards, covers.Templates, covers.Menus, covers.CardVideos, covers.GameVideos)
                    : null,
                screenshots));
        }

        themes.Sort((a, b) => string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase));
        return new ThemeIndex(latest, themes, diagnostics);

        Diagnostic Problem(Severity severity, int line, string key, string message) =>
            new(severity, source, Math.Max(line, 0), 0, key, message);
    }

    private static string? Check(EntryFile? entry, string key, IReadOnlyCollection<string> reservedIds, HashSet<string> seen, bool allowFileUrls)
    {
        if (entry is null)
        {
            return $"{key} is empty";
        }

        if (string.IsNullOrWhiteSpace(entry.Id) || !TomlValidator.IsValidId(entry.Id))
        {
            return $"'{entry.Id}' isn't a valid theme id (lower-case letters, digits, '_' and '-')";
        }

        if (reservedIds.Contains(entry.Id))
        {
            return $"'{entry.Id}' is a built-in theme's id";
        }

        if (seen.Contains(entry.Id))
        {
            return $"'{entry.Id}' is listed twice";
        }

        if (string.IsNullOrWhiteSpace(entry.Name))
        {
            return $"'{entry.Id}' has no name";
        }

        if (!Uri.TryCreate(entry.Url, UriKind.Absolute, out var url) || !(url.Scheme == Uri.UriSchemeHttps || (allowFileUrls && url.IsFile)))
        {
            return $"'{entry.Id}': '{entry.Url}' isn't an https URL";
        }

        if (entry.Commit is not { Length: 40 } commit || !commit.All(char.IsAsciiHexDigit))
        {
            return $"'{entry.Id}': the commit must be a full 40-character sha";
        }

        if (entry.MinAppVersion is { } min && !AppVersion.TryParse(min, out _))
        {
            return $"'{entry.Id}': min_app_version '{min}' isn't a version";
        }

        return null;
    }

    // A screenshot's path, relative to the list, '/'-separated (ES-DE's list has doubled slashes: they're one).
    private static string? Inside(string root, string relative)
    {
        if (Path.IsPathRooted(relative) || relative.Contains(':', StringComparison.Ordinal))
        {
            return null;
        }

        var parts = relative.Split(['/', '\\'], StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0 || parts.Any(p => p is "." or ".."))
        {
            return null;
        }

        return Path.Combine([root, .. parts]);
    }

    internal sealed class IndexFile
    {
        public int Format { get; set; }

        public string? LatestAppVersion { get; set; }

        public List<EntryFile?>? Themes { get; set; }
    }

    internal sealed class EntryFile
    {
        public string? Id { get; set; }

        public string? Name { get; set; }

        public string? Author { get; set; }

        public string? Description { get; set; }

        public string? Url { get; set; }

        public string? Commit { get; set; }

        public string? Version { get; set; }

        public string? MinAppVersion { get; set; }

        public bool New { get; set; }

        public bool Deprecated { get; set; }

        public CoversFile? Covers { get; set; }

        public List<ScreenshotFile?>? Screenshots { get; set; }
    }

    internal sealed class CoversFile
    {
        public int SystemCards { get; set; }

        public int Templates { get; set; }

        public bool Menus { get; set; }

        public bool CardVideos { get; set; }

        public bool GameVideos { get; set; }
    }

    internal sealed class ScreenshotFile
    {
        public string? Image { get; set; }

        public string? Caption { get; set; }
    }
}

/// <summary>Writes a theme's <see cref="ThemeCovers"/> as the list's <c>covers</c> block (<c>inspect-theme --json</c>).</summary>
public static class ThemeCoversJson
{
    public static string Serialize(ThemeCovers covers)
    {
        ArgumentNullException.ThrowIfNull(covers);
        var file = new ThemeIndexReader.CoversFile
        {
            SystemCards = covers.SystemCards,
            Templates = covers.Templates,
            Menus = covers.Menus,
            CardVideos = covers.CardVideos,
            GameVideos = covers.GameVideos,
        };
        return JsonSerializer.Serialize(file, ThemeIndexJsonContext.Default.CoversFile).ReplaceLineEndings("\n");
    }
}

[JsonSourceGenerationOptions(
    WriteIndented = true,
    PropertyNamingPolicy = JsonKnownNamingPolicy.SnakeCaseLower,
    ReadCommentHandling = JsonCommentHandling.Skip,
    AllowTrailingCommas = true)]
[JsonSerializable(typeof(ThemeIndexReader.IndexFile))]
[JsonSerializable(typeof(ThemeIndexReader.CoversFile))]
internal sealed partial class ThemeIndexJsonContext : JsonSerializerContext
{
}
