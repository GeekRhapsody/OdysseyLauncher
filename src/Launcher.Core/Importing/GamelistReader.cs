using System.Globalization;
using System.Text;
using System.Xml;
using System.Xml.Linq;
using Launcher.Core.Library;
using Launcher.Core.Media;

namespace Launcher.Core.Importing;

/// <summary>A media file a gamelist names for a game, as written there (<c>./images/Game-thumb.png</c>).</summary>
/// <param name="Kind">The media kind it fills (<see cref="GamelistReader.MediaTags"/>).</param>
public sealed record GamelistMedia(string Kind, string Path);

/// <summary>
/// One <c>&lt;game&gt;</c> of an ES-DE gamelist, normalised as the user's own edits would be (<see cref="MetadataInput"/>):
/// a value the launcher couldn't take (too long, not a date) is left out.
/// </summary>
/// <param name="Path">The ROM, as written (<c>./Game (USA).zip</c>).</param>
/// <param name="ReleaseDate">ISO 8601, possibly partial: '1989', '1989-11' or '1989-11-01'.</param>
/// <param name="Rating">0 to 1, ES-DE's scale too; ES-DE's 0 (not rated) is left out.</param>
/// <param name="ScreenScraperId">The game's ScreenScraper id, when the gamelist says ScreenScraper scraped it.</param>
public sealed record GamelistEntry(
    string Path,
    string? Name,
    string? Description,
    string? ReleaseDate,
    string? Developer,
    string? Publisher,
    string? Genre,
    string? Players,
    double? Rating,
    IReadOnlyList<GamelistMedia> Media,
    bool Favourite,
    bool Hidden,
    string? ScreenScraperId);

/// <summary>What reading a gamelist found: its games, or why it couldn't be read (then no games).</summary>
public sealed record GamelistReadResult(IReadOnlyList<GamelistEntry> Games, string? Error);

/// <summary>
/// Reads an ES-DE (or Batocera, RetroBat, EmulationStation) <c>gamelist.xml</c>. ES-DE writes an
/// <c>&lt;alternativeEmulator&gt;</c> element beside <c>&lt;gameList&gt;</c>, so the file is read as a fragment (two roots).
/// DTDs are refused and nothing outside the file is resolved. <c>&lt;folder&gt;</c> entries and tags the launcher has no
/// use for are skipped. Never throws for a bad file.
/// </summary>
public static class GamelistReader
{
    /// <summary>The media tags imported, and the kind each fills.</summary>
    public static IReadOnlyList<(string Tag, string Kind)> MediaTags { get; } =
    [
        ("thumbnail", MediaKinds.Cover),
        ("image", MediaKinds.Screenshot),
        ("marquee", MediaKinds.Logo),
        ("video", MediaKinds.Video),
        ("manual", MediaKinds.Manual),
    ];

    public static GamelistReadResult Read(Stream xml, string sourceName)
    {
        ArgumentNullException.ThrowIfNull(xml);
        var settings = new XmlReaderSettings
        {
            ConformanceLevel = ConformanceLevel.Fragment,
            DtdProcessing = DtdProcessing.Prohibit,
            XmlResolver = null,
            CheckCharacters = false,
            IgnoreComments = true,
            IgnoreProcessingInstructions = true,
        };

        var games = new List<GamelistEntry>();
        try
        {
            using var reader = XmlReader.Create(xml, settings);
            reader.MoveToContent();
            while (!reader.EOF)
            {
                if (reader.NodeType == XmlNodeType.Element && reader.Depth == 1 && reader.LocalName == "game")
                {
                    if (Entry((XElement)XNode.ReadFrom(reader)) is { } entry)
                    {
                        games.Add(entry);
                    }

                    continue;
                }

                reader.Read();
            }
        }
        catch (XmlException e)
        {
            return new GamelistReadResult([], $"{sourceName} isn't a gamelist the launcher can read: {e.Message}");
        }

        return new GamelistReadResult(games, null);
    }

    private static GamelistEntry? Entry(XElement game)
    {
        if (Text(game, "path") is not { } path)
        {
            return null;
        }

        var media = new List<GamelistMedia>();
        foreach (var (tag, kind) in MediaTags)
        {
            if (Text(game, tag) is { } file)
            {
                media.Add(new GamelistMedia(kind, file));
            }
        }

        var screenScraper = game.Elements("scrap").Any(s => string.Equals((string?)s.Attribute("name"), "ScreenScraper", StringComparison.OrdinalIgnoreCase))
            && (string?)game.Attribute("id") is { Length: > 0 and <= 12 } id && id.All(char.IsAsciiDigit) && id.Any(c => c != '0')
                ? id
                : null;

        return new GamelistEntry(
            path,
            Line(game, "name", MetadataInput.CheckTitle),
            Description(Text(game, "desc")),
            Text(game, "releasedate") is { } date ? ReleaseDate(date) : null,
            Line(game, "developer", MetadataInput.CheckField),
            Line(game, "publisher", MetadataInput.CheckField),
            Line(game, "genre", MetadataInput.CheckField),
            Line(game, "players", MetadataInput.CheckPlayers),
            Text(game, "rating") is { } rating ? Rating(rating) : null,
            media,
            IsTrue(Text(game, "favorite")),
            IsTrue(Text(game, "hidden")),
            screenScraper);
    }

    /// <summary>
    /// ES-DE's date (<c>19891101T000000</c>, a month or day of 00 when it isn't known) as ISO 8601, or anything else
    /// the game's metadata panel takes (<see cref="MetadataInput.ParseReleaseDate"/>); null for neither.
    /// </summary>
    public static string? ReleaseDate(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var trimmed = text.Trim();
        var t = trimmed.IndexOf('T', StringComparison.Ordinal);
        var digits = t >= 0 ? trimmed[..t] : trimmed;
        if (digits.Length == 8 && digits.All(char.IsAsciiDigit))
        {
            var year = int.Parse(digits[..4], CultureInfo.InvariantCulture);
            var month = int.Parse(digits[4..6], CultureInfo.InvariantCulture);
            var day = int.Parse(digits[6..], CultureInfo.InvariantCulture);
            if (year < 1 || month > 12)
            {
                return null;
            }

            if (month == 0)
            {
                return year.ToString("D4", CultureInfo.InvariantCulture);
            }

            if (day == 0)
            {
                return string.Create(CultureInfo.InvariantCulture, $"{year:D4}-{month:D2}");
            }

            return day <= DateTime.DaysInMonth(year, month) ? string.Create(CultureInfo.InvariantCulture, $"{year:D4}-{month:D2}-{day:D2}") : null;
        }

        return t >= 0 ? null : MetadataInput.ParseReleaseDate(trimmed);
    }

    private static double? Rating(string text) =>
        double.TryParse(text.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var value) && double.IsFinite(value) && value > 0
            ? Math.Min(value, 1)
            : null;

    private static string? Description(string? text)
    {
        if (text is null)
        {
            return null;
        }

        var normalised = text.ReplaceLineEndings("\n").Trim();
        return normalised.Length == 0 || MetadataInput.CheckDescription(normalised) is not null ? null : normalised;
    }

    /// <summary>A one-line field, its whitespace collapsed, or null if it's empty or <paramref name="check"/> refuses it.</summary>
    private static string? Line(XElement game, string tag, Func<string, string?> check)
    {
        if (Text(game, tag) is not { } text)
        {
            return null;
        }

        var line = new StringBuilder(text.Length);
        foreach (var c in text)
        {
            if (char.IsWhiteSpace(c))
            {
                if (line.Length > 0 && line[^1] != ' ')
                {
                    line.Append(' ');
                }
            }
            else
            {
                line.Append(c);
            }
        }

        var value = line.ToString().TrimEnd();
        return value.Length == 0 || check(value) is not null ? null : value;
    }

    /// <summary>A child's text, trimmed, or null when it's missing or empty.</summary>
    private static string? Text(XElement game, string tag) =>
        game.Element(tag)?.Value.Trim() is { Length: > 0 } value ? value : null;

    private static bool IsTrue(string? text) => string.Equals(text, "true", StringComparison.OrdinalIgnoreCase);
}
