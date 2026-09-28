using System.Text;
using System.Text.RegularExpressions;

namespace Launcher.Core.Scanning;

/// <summary>
/// An <c>exclude</c> pattern, matched case-insensitively against a '/'-separated path relative to a
/// ROM folder. <c>*</c> matches within one path segment, <c>**</c> across segments, <c>?</c> one character.
/// A pattern without '/' matches any single segment (file or folder name) at any depth, like .gitignore.
/// An excluded folder is skipped with everything in it.
/// </summary>
public sealed class GlobPattern
{
    private readonly Regex _regex;
    private readonly bool _matchesName;

    private GlobPattern(string pattern)
    {
        Pattern = pattern;
        var trimmed = pattern.Trim('/');
        _matchesName = !trimmed.Contains('/', StringComparison.Ordinal);
        _regex = new Regex(ToRegex(trimmed), RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    }

    public string Pattern { get; }

    /// <summary>Returns an error message, or null when the pattern is usable.</summary>
    public static string? Validate(string pattern)
    {
        ArgumentNullException.ThrowIfNull(pattern);
        if (pattern.Trim('/').Trim().Length == 0)
        {
            return "the pattern is empty";
        }

        if (pattern.Contains('\\', StringComparison.Ordinal))
        {
            return "use '/' to separate folders in patterns";
        }

        return null;
    }

    public static GlobPattern Create(string pattern)
    {
        if (Validate(pattern) is { } error)
        {
            throw new ArgumentException(error, nameof(pattern));
        }

        return new GlobPattern(pattern);
    }

    /// <param name="relPath">'/'-separated path relative to the ROM folder.</param>
    public bool IsMatch(string relPath)
    {
        ArgumentNullException.ThrowIfNull(relPath);
        if (!_matchesName)
        {
            return _regex.IsMatch(relPath);
        }

        var slash = relPath.LastIndexOf('/');
        return _regex.IsMatch(slash < 0 ? relPath : relPath[(slash + 1)..]);
    }

    private static string ToRegex(string glob)
    {
        var regex = new StringBuilder("^");
        for (var i = 0; i < glob.Length; i++)
        {
            var c = glob[i];
            if (c == '*')
            {
                if (i + 1 < glob.Length && glob[i + 1] == '*')
                {
                    var slashFollows = i + 2 < glob.Length && glob[i + 2] == '/';
                    regex.Append(slashFollows ? "(?:.*/)?" : ".*");
                    i += slashFollows ? 2 : 1;
                }
                else
                {
                    regex.Append("[^/]*");
                }
            }
            else if (c == '?')
            {
                regex.Append("[^/]");
            }
            else
            {
                regex.Append(Regex.Escape(c.ToString()));
            }
        }

        return regex.Append('$').ToString();
    }
}
