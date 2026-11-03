using System.Text;

namespace Launcher.Core.Launching;

/// <summary>
/// What a Linux desktop shortcut (a <c>.desktop</c> file) runs: its <c>[Desktop Entry]</c> group's <c>Exec</c> line,
/// split as freedesktop.org's Desktop Entry Specification says, and its <c>Path</c>, the folder it runs in. A game's
/// shortcut is run this way on Linux (A5 Finding programs), Steam's included.
/// </summary>
public static class DesktopEntry
{
    /// <summary>A shortcut's command: its program (a bare name is looked for on the PATH) and arguments.</summary>
    public sealed record Command(string Program, IReadOnlyList<string> Arguments, string? WorkingDirectory);

    /// <summary>The shortcut's command, or null when it has no <c>Exec</c> line that can be split.</summary>
    public static Command? Read(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        string? exec = null;
        string? path = null;
        var inEntry = false;
        foreach (var raw in text.Split('\n'))
        {
            var line = raw.Trim();
            if (line.StartsWith('['))
            {
                inEntry = line == "[Desktop Entry]";
                continue;
            }

            var equals = line.IndexOf('=', StringComparison.Ordinal);
            if (!inEntry || equals < 0)
            {
                continue;
            }

            // Only the unlocalised keys: Exec[fr] isn't the command.
            var key = line[..equals].TrimEnd();
            var value = Unescape(line[(equals + 1)..].TrimStart());
            exec = key == "Exec" ? value : exec;
            path = key == "Path" ? value : path;
        }

        var words = exec is null ? null : Split(exec);
        return words is { Count: > 0 }
            ? new Command(words[0], words.GetRange(1, words.Count - 1), string.IsNullOrEmpty(path) ? null : path)
            : null;
    }

    /// <summary>The specification's string escapes: \s, \n, \t, \r and \\.</summary>
    private static string Unescape(string value)
    {
        var result = new StringBuilder(value.Length);
        for (var i = 0; i < value.Length; i++)
        {
            if (value[i] != '\\' || i + 1 == value.Length)
            {
                result.Append(value[i]);
                continue;
            }

            i++;
            switch (value[i])
            {
                case 's':
                    result.Append(' ');
                    break;
                case 'n':
                    result.Append('\n');
                    break;
                case 't':
                    result.Append('\t');
                    break;
                case 'r':
                    result.Append('\r');
                    break;
                case '\\':
                    result.Append('\\');
                    break;
                default:
                    // Not a string escape: the backslash belongs to Exec's quoting, which Split reads.
                    result.Append('\\').Append(value[i]);
                    break;
            }
        }

        return result.ToString();
    }

    /// <summary>
    /// Exec's words: separated by spaces, a word in double quotes may hold spaces, and in quotes a backslash escapes the
    /// next character. Field codes (%f, %U, ...) stand for files the launcher never passes, so they're left out; %% is a
    /// percent sign. Null for an unclosed quote.
    /// </summary>
    private static List<string>? Split(string exec)
    {
        var words = new List<string>();
        var word = new StringBuilder();
        var quoted = false;
        var started = false;
        for (var i = 0; i < exec.Length; i++)
        {
            var c = exec[i];
            if (quoted && c == '\\' && i + 1 < exec.Length)
            {
                word.Append(exec[++i]);
            }
            else if (c == '"')
            {
                quoted = !quoted;
                started = true;
            }
            else if (c == '%' && i + 1 < exec.Length)
            {
                if (exec[++i] == '%')
                {
                    word.Append('%');
                    started = true;
                }
            }
            else if (c == ' ' && !quoted)
            {
                EndWord(words, word, ref started);
            }
            else
            {
                word.Append(c);
                started = true;
            }
        }

        EndWord(words, word, ref started);
        return quoted ? null : words;
    }

    private static void EndWord(List<string> words, StringBuilder word, ref bool started)
    {
        if (started)
        {
            words.Add(word.ToString());
        }

        word.Clear();
        started = false;
    }
}
