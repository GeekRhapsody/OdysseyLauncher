using System.Globalization;

namespace Launcher.Core.Library;

/// <summary>
/// Checks and normalises what the user types for a game's title and metadata (M7's game options panel), before it's
/// saved as an override. Each <c>Check*</c> returns why the text can't be saved, or null; each <c>Parse*</c> turns
/// accepted text into the stored value. An empty entry is always accepted: it means "use the scraped value".
/// </summary>
public static class MetadataInput
{
    public const int MaxTitleLength = 200;
    public const int MaxFieldLength = 200;
    public const int MaxDescriptionLength = 4000;
    public const int MaxPlayersLength = 20;

    private static readonly string[] Months =
        ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"];

    public static string? CheckTitle(string text) => CheckLine(text, MaxTitleLength, "A title");

    public static string? CheckField(string text) => CheckLine(text, MaxFieldLength, "It");

    public static string? CheckPlayers(string text) => CheckLine(text, MaxPlayersLength, "The number of players");

    public static string? CheckDescription(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        return text.Trim().Length > MaxDescriptionLength
            ? string.Create(CultureInfo.InvariantCulture, $"A description can be at most {MaxDescriptionLength:N0} characters.")
            : null;
    }

    /// <summary>
    /// A release date, as precise as it's known: a year (1994), a month and year (02/1994, February 1994, 1994-02) or
    /// a day (24/02/1994, 24 February 1994, 1994-02-24). Days come before months, as in the UK.
    /// </summary>
    public static string? CheckReleaseDate(string text) =>
        text.Trim().Length == 0 || ParseReleaseDate(text) is not null
            ? null
            : "Type a year (1994), a month and year (02/1994) or a day (24/02/1994).";

    /// <summary>The release date as stored (ISO 8601, possibly partial: '1994', '1994-02', '1994-02-24'), or null if it isn't one.</summary>
    public static string? ParseReleaseDate(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var parts = text.Trim().Split(['/', '-', '.', ' ', ','], StringSplitOptions.RemoveEmptyEntries);
        int? day = null, month = null;
        int year;
        switch (parts.Length)
        {
            case 1 when Number(parts[0], out year):
                break;
            case 2 when Number(parts[0], out year) && parts[0].Length == 4 && Month(parts[1], out var m):
                month = m;
                break;
            case 2 when Month(parts[0], out var m) && Number(parts[1], out year):
                month = m;
                break;
            case 3 when parts[0].Length == 4 && Number(parts[0], out year) && Month(parts[1], out var m) && Number(parts[2], out var d):
                (month, day) = (m, d);
                break;
            case 3 when Number(parts[0], out var d) && Month(parts[1], out var m) && Number(parts[2], out year):
                (month, day) = (m, d);
                break;
            default:
                return null;
        }

        if (year is < 1000 or > 9999 || (day is { } dd && (dd < 1 || dd > DateTime.DaysInMonth(year, month!.Value))))
        {
            return null;
        }

        return day is { } dayValue
            ? string.Create(CultureInfo.InvariantCulture, $"{year:0000}-{month:00}-{dayValue:00}")
            : month is { } monthValue
                ? string.Create(CultureInfo.InvariantCulture, $"{year:0000}-{monthValue:00}")
                : year.ToString("0000", CultureInfo.InvariantCulture);

        static bool Number(string s, out int value) =>
            int.TryParse(s, NumberStyles.None, CultureInfo.InvariantCulture, out value);

        static bool Month(string s, out int month)
        {
            if (Number(s, out month))
            {
                return month is >= 1 and <= 12;
            }

            var lower = s.ToLowerInvariant();
            for (var i = 0; i < Months.Length; i++)
            {
                if (lower.Length >= 3 && Months[i].StartsWith(lower, StringComparison.Ordinal))
                {
                    month = i + 1;
                    return true;
                }
            }

            return false;
        }
    }

    /// <summary>A rating out of 5, as shown in the details ("4", "4.5", "4,5", "4.5 / 5"); or a percentage ("90%").</summary>
    public static string? CheckRating(string text) =>
        text.Trim().Length == 0 || ParseRating(text) is not null ? null : "Type a rating from 0 to 5 (such as 4.5), or a percentage (90%).";

    /// <summary>The rating as stored, 0 to 1, or null if the text isn't one.</summary>
    public static double? ParseRating(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var trimmed = text.Trim().Replace(',', '.');
        var outOf = 5.0;
        if (trimmed.EndsWith('%'))
        {
            trimmed = trimmed[..^1].TrimEnd();
            outOf = 100;
        }
        else if (trimmed.IndexOf('/', StringComparison.Ordinal) is var slash and > 0)
        {
            if (!double.TryParse(trimmed[(slash + 1)..].Trim(), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out outOf) || outOf <= 0)
            {
                return null;
            }

            trimmed = trimmed[..slash].TrimEnd();
        }

        if (!double.TryParse(trimmed, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var value) || value < 0 || value > outOf)
        {
            return null;
        }

        return Math.Round(value / outOf, 4);
    }

    /// <summary>A rating as the user types it: out of 5, with at most one decimal.</summary>
    public static string FormatRating(double rating) => (rating * 5).ToString("0.#", CultureInfo.InvariantCulture);

    private static string? CheckLine(string text, int max, string what)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (text.Contains('\n', StringComparison.Ordinal) || text.Contains('\r', StringComparison.Ordinal))
        {
            return $"{what} must be one line.";
        }

        return text.Trim().Length > max ? string.Create(CultureInfo.InvariantCulture, $"{what} can be at most {max} characters.") : null;
    }
}
