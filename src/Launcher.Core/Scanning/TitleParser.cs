using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace Launcher.Core.Scanning;

/// <summary>What a No-Intro or Redump style file name says about a game.</summary>
/// <param name="Title">Display title: tags removed, a trailing article moved to the front, plus " (Disc n)" for a lone disc.</param>
/// <param name="SortTitle">Internal sort key (see <see cref="TitleParser.SortKey"/>).</param>
/// <param name="Region">The region tag as written, e.g. "USA, Europe".</param>
/// <param name="Languages">The language tag as written, e.g. "En,Fr,De".</param>
/// <param name="Revision">"Rev 1", "Rev A", "v1.1".</param>
/// <param name="Tags">Every other tag, as written and in order, e.g. "(Beta) [b1]".</param>
public sealed record TitleInfo(
    string Title,
    string SortTitle,
    string? Region,
    string? Languages,
    string? Revision,
    int? Disc,
    string? Tags);

/// <summary>
/// Derives a clean title from a file name such as <c>Legend of Zelda, The - A Link to the Past (USA) (Rev 1)</c>.
/// Trailing <c>(...)</c> and <c>[...]</c> groups are tags; the first all-region group is the region, the first
/// language list is the languages, and the first revision and disc tags are kept as their own fields.
/// </summary>
public static partial class TitleParser
{
    private static readonly HashSet<string> Regions = new(StringComparer.OrdinalIgnoreCase)
    {
        // No-Intro and Redump region names.
        "World", "Europe", "Asia", "Australia", "Brazil", "Canada", "China", "France", "Germany", "Hong Kong",
        "Italy", "Japan", "Korea", "Netherlands", "Spain", "Sweden", "USA", "UK", "Russia", "Taiwan",
        "Scandinavia", "Denmark", "Finland", "Norway", "Poland", "Portugal", "Greece", "Ireland", "Belgium",
        "Austria", "Switzerland", "Latin America", "Mexico", "Argentina", "New Zealand", "India", "South Africa",
        "Croatia", "Czech", "Hungary", "Israel", "Turkey", "United Arab Emirates", "Unknown",

        // GoodTools codes.
        "U", "E", "J", "W", "UE", "JU", "JE", "JUE", "EU", "UJ", "K", "F", "G", "S", "I", "NL", "SW", "HK", "Ch", "B",
    };

    public static TitleInfo Parse(string fileNameWithoutExtension)
    {
        ArgumentNullException.ThrowIfNull(fileNameWithoutExtension);
        var name = fileNameWithoutExtension.Trim();
        if (!name.Contains(' ', StringComparison.Ordinal) && name.Contains('_', StringComparison.Ordinal))
        {
            name = name.Replace('_', ' ');
        }

        // Peel tag groups off the end (and Redump's leading "[BIOS]"-style groups off the start).
        var groups = new List<string>();
        var body = name;
        while (true)
        {
            body = body.TrimEnd();
            if (body.Length < 2)
            {
                break;
            }

            var close = body[^1];
            var open = close switch { ')' => '(', ']' => '[', _ => '\0' };
            if (open == '\0')
            {
                break;
            }

            var start = body.LastIndexOf(open);
            if (start <= 0 || body[..start].Trim().Length == 0)
            {
                break;
            }

            groups.Insert(0, body[start..]);
            body = body[..start];
        }

        var leading = new List<string>();
        while (body.StartsWith('[') && body.IndexOf(']', StringComparison.Ordinal) is var end and > 0
               && body[(end + 1)..].Trim().Length > 0)
        {
            leading.Add(body[..(end + 1)]);
            body = body[(end + 1)..].TrimStart();
        }

        body = CollapseSpaces(body.Trim());
        if (body.Length == 0)
        {
            body = CollapseSpaces(name);
        }

        string? region = null;
        string? languages = null;
        string? revision = null;
        int? disc = null;
        var tags = new List<string>(leading);
        foreach (var group in groups)
        {
            var inner = group[1..^1].Trim();
            if (group[0] == '(')
            {
                if (region is null && IsRegionList(inner))
                {
                    region = inner;
                    continue;
                }

                if (languages is null && LanguageListRegex().IsMatch(inner))
                {
                    languages = inner;
                    continue;
                }

                if (revision is null && RevisionRegex().IsMatch(inner))
                {
                    revision = inner;
                    continue;
                }

                if (disc is null && DiscRegex().Match(inner) is { Success: true } discMatch
                    && int.TryParse(discMatch.Groups[1].ValueSpan, NumberStyles.None, CultureInfo.InvariantCulture, out var number))
                {
                    disc = number;
                    continue;
                }
            }

            tags.Add(group);
        }

        var title = MoveArticleToFront(body);
        var displayTitle = disc is null ? title : string.Create(CultureInfo.InvariantCulture, $"{title} (Disc {disc})");
        var sortTitle = SortKey(title);
        if (disc is not null)
        {
            // \u0001 sorts before every printable character, so a game's discs sit right after the game
            // and before "Game 2" or "Game - Subtitle".
            sortTitle = string.Create(CultureInfo.InvariantCulture, $"{sortTitle}\u0001{SortKey(disc.Value.ToString(CultureInfo.InvariantCulture))}");
        }

        return new TitleInfo(
            displayTitle,
            sortTitle,
            region,
            languages,
            revision,
            disc,
            tags.Count == 0 ? null : string.Join(' ', tags));
    }

    /// <summary>
    /// The key the grid sorts by: lower-case, accents removed, a leading "The", "A" or "An" dropped, and
    /// each run of digits prefixed with its length so numbers sort naturally ("Mega Man 2" before "Mega Man 10").
    /// It's internal and never shown.
    /// </summary>
    public static string SortKey(string title)
    {
        ArgumentNullException.ThrowIfNull(title);
        var text = CollapseSpaces(title.Trim());
        foreach (var article in (ReadOnlySpan<string>)["The ", "A ", "An "])
        {
            if (text.Length > article.Length && text.StartsWith(article, StringComparison.OrdinalIgnoreCase))
            {
                text = text[article.Length..];
                break;
            }
        }

        var decomposed = text.Normalize(NormalizationForm.FormD);
        var key = new StringBuilder(decomposed.Length + 8);
        for (var i = 0; i < decomposed.Length; i++)
        {
            var c = decomposed[i];
            if (CharUnicodeInfo.GetUnicodeCategory(c) == UnicodeCategory.NonSpacingMark)
            {
                continue;
            }

            if (char.IsAsciiDigit(c))
            {
                var end = i;
                while (end < decomposed.Length && char.IsAsciiDigit(decomposed[end]))
                {
                    end++;
                }

                // Leading zeros don't change the value: "007" sorts as 7.
                var start = i;
                while (start < end - 1 && decomposed[start] == '0')
                {
                    start++;
                }

                var length = Math.Min(end - start, 9);
                key.Append((char)('0' + length)).Append(decomposed, start, end - start);
                i = end - 1;
                continue;
            }

            key.Append(char.ToLowerInvariant(c));
        }

        return key.ToString().Normalize(NormalizationForm.FormC);
    }

    /// <summary>"Legend of Zelda, The - A Link to the Past" becomes "The Legend of Zelda - A Link to the Past".</summary>
    private static string MoveArticleToFront(string title)
    {
        var match = TrailingArticleRegex().Match(title);
        if (!match.Success)
        {
            return title;
        }

        var article = match.Groups["article"].Value;
        var separator = article.EndsWith('\'') ? string.Empty : " ";
        return article + separator + match.Groups["base"].Value + match.Groups["rest"].Value;
    }

    private static bool IsRegionList(string inner)
    {
        foreach (var part in inner.Split(','))
        {
            if (!Regions.Contains(part.Trim()))
            {
                return false;
            }
        }

        return true;
    }

    private static string CollapseSpaces(string text) =>
        text.Contains("  ", StringComparison.Ordinal) ? SpacesRegex().Replace(text, " ") : text;

    [GeneratedRegex(@"^(?<base>.+?), (?<article>The|A|An|Le|La|Les|L'|Der|Die|Das|El|Los|Las|Il|Lo|Gli|De|Het)(?<rest> - .*)?$", RegexOptions.CultureInvariant)]
    private static partial Regex TrailingArticleRegex();

    /// <summary>"En", "En,Fr,De", "En-GB,Zh-Hant".</summary>
    [GeneratedRegex(@"^[A-Z][a-z](-[A-Za-z]{2,4})?(\s*[,+]\s*[A-Z][a-z](-[A-Za-z]{2,4})?)*$", RegexOptions.CultureInvariant)]
    private static partial Regex LanguageListRegex();

    /// <summary>"Rev 1", "Rev A", "Rev 1.1", "v1.1", "v1.02b", "Version 2".</summary>
    [GeneratedRegex(@"^(Rev\s*[0-9A-Z][0-9A-Za-z.]*|v\d+(\.\d+)*[a-z]?|Version\s+\d+(\.\d+)*[a-z]?)$", RegexOptions.CultureInvariant)]
    private static partial Regex RevisionRegex();

    /// <summary>"Disc 1", "Disc 2 of 3", "Disk 1", "CD1".</summary>
    [GeneratedRegex(@"^(?:Disc|Disk|CD)\s*(\d+)(?:\s+of\s+\d+)?$", RegexOptions.CultureInvariant | RegexOptions.IgnoreCase)]
    private static partial Regex DiscRegex();

    [GeneratedRegex(@"\s{2,}", RegexOptions.CultureInvariant)]
    private static partial Regex SpacesRegex();
}
