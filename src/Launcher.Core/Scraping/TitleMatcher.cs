using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Launcher.Core.Scraping;

/// <summary>
/// Compares a ROM's cleaned title with a provider's game names, for the providers that can only search by name
/// (SteamGridDB, IGDB, and ScreenScraper's fallback search). Names are compared case-, accent- and
/// punctuation-blind, with a leading article dropped and '&amp;' read as "and".
/// </summary>
public static partial class TitleMatcher
{
    /// <summary>The similarity a search hit needs to count as the game.</summary>
    public const double Threshold = 0.85;

    public static string Normalise(string title)
    {
        ArgumentNullException.ThrowIfNull(title);
        var decomposed = title.Normalize(NormalizationForm.FormD);
        var builder = new StringBuilder(decomposed.Length);
        foreach (var c in decomposed)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) == UnicodeCategory.NonSpacingMark)
            {
                continue;
            }

            if (c == '&')
            {
                builder.Append(" and ");
            }
            else if (char.IsLetterOrDigit(c))
            {
                builder.Append(char.ToLowerInvariant(c));
            }
            else
            {
                builder.Append(' ');
            }
        }

        var words = builder.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries).ToList();
        if (words.Count > 1 && words[0] is "the" or "a" or "an")
        {
            words.RemoveAt(0);
        }

        return string.Join(' ', words);
    }

    /// <summary>1 for the same name, falling towards 0 with the edit distance; a name that matches before its subtitle scores 0.9.</summary>
    public static double Similarity(string title, string candidate)
    {
        var a = Normalise(title);
        var b = Normalise(candidate);
        if (a.Length == 0 || b.Length == 0)
        {
            return 0;
        }

        if (a == b)
        {
            return 1;
        }

        var score = 1.0 - ((double)EditDistance(a, b) / Math.Max(a.Length, b.Length));

        // "Castlevania: Symphony of the Night" against a file named "Castlevania - Symphony of the Night" is
        // handled by normalising; a missing subtitle on either side is a near match.
        foreach (var (shorter, longer) in (ReadOnlySpan<(string, string)>)[(a, b), (b, a)])
        {
            if (longer.StartsWith(shorter + " ", StringComparison.Ordinal) && shorter.Length >= 6)
            {
                score = Math.Max(score, 0.9);
            }
        }

        return score;
    }

    /// <summary>The title a search uses: the file-name title without its disc number.</summary>
    public static string SearchTerm(string title)
    {
        ArgumentNullException.ThrowIfNull(title);
        return DiscSuffix().Replace(title, string.Empty).Trim();
    }

    [GeneratedRegex(@"\s*\((?:Disc|Disk|CD)\s*\d+[^)]*\)\s*$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex DiscSuffix();

    private static int EditDistance(string a, string b)
    {
        var previous = new int[b.Length + 1];
        var current = new int[b.Length + 1];
        for (var j = 0; j <= b.Length; j++)
        {
            previous[j] = j;
        }

        for (var i = 1; i <= a.Length; i++)
        {
            current[0] = i;
            for (var j = 1; j <= b.Length; j++)
            {
                var cost = a[i - 1] == b[j - 1] ? 0 : 1;
                current[j] = Math.Min(Math.Min(current[j - 1] + 1, previous[j] + 1), previous[j - 1] + cost);
            }

            (previous, current) = (current, previous);
        }

        return previous[b.Length];
    }
}

/// <summary>JSON reading that tolerates what providers send: trailing commas, stray backslashes, numbers as strings.</summary>
public static class LenientJson
{
    private static readonly JsonDocumentOptions Options = new() { AllowTrailingCommas = true, CommentHandling = JsonCommentHandling.Skip, MaxDepth = 128 };

    /// <summary>Parses <paramref name="text"/>, repairing invalid backslash escapes if the first attempt fails. Null when it isn't JSON.</summary>
    public static JsonDocument? Parse(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        try
        {
            return JsonDocument.Parse(text, Options);
        }
        catch (JsonException)
        {
        }

        try
        {
            return JsonDocument.Parse(RepairEscapes(text), Options);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    /// <summary>A mutable, normalised copy of an element (its raw text may still hold the trailing commas it was read with).</summary>
    public static System.Text.Json.Nodes.JsonNode? ToNode(JsonElement element) =>
        System.Text.Json.Nodes.JsonNode.Parse(element.GetRawText(), null, Options);

    /// <summary>A string property, or a number written as one; null when missing or empty.</summary>
    public static string? Str(this JsonElement element, string name)
    {
        if (element.ValueKind != JsonValueKind.Object || !element.TryGetProperty(name, out var value))
        {
            return null;
        }

        var text = value.ValueKind switch
        {
            JsonValueKind.String => value.GetString(),
            JsonValueKind.Number => value.GetRawText(),
            JsonValueKind.True => "true",
            JsonValueKind.False => "false",
            _ => null,
        };
        return string.IsNullOrWhiteSpace(text) ? null : text;
    }

    /// <summary>A number property, or a number written as a string.</summary>
    public static double? Num(this JsonElement element, string name) =>
        element.Str(name) is { } text && double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var value) ? value : null;

    public static JsonElement? Obj(this JsonElement element, string name) =>
        element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Object ? value : null;

    /// <summary>The items of an array property; empty when it's missing or not an array.</summary>
    public static IEnumerable<JsonElement> Arr(this JsonElement element, string name) =>
        element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Array
            ? value.EnumerateArray()
            : [];

    /// <summary>Doubles every backslash that doesn't start a valid JSON escape, reading escapes left to right.</summary>
    private static string RepairEscapes(string text)
    {
        const string Escapable = "\"\\/bfnrtu";
        var builder = new StringBuilder(text.Length + 16);
        for (var i = 0; i < text.Length; i++)
        {
            var c = text[i];
            if (c != '\\')
            {
                builder.Append(c);
            }
            else if (i + 1 < text.Length && Escapable.Contains(text[i + 1], StringComparison.Ordinal))
            {
                builder.Append(c).Append(text[++i]);
            }
            else
            {
                builder.Append('\\').Append('\\');
            }
        }

        return builder.ToString();
    }
}
