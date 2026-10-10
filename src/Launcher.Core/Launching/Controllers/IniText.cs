using System.Text;

namespace Launcher.Core.Launching.Controllers;

/// <summary>
/// An INI file edited in place, for another program's config (Eden's <c>qt-config.ini</c>, which it reads with
/// SimpleIni): every line is kept as it was except the keys that are set. Sections and keys match ignoring case, as
/// SimpleIni's do, and the first of a repeated key is the one read, so setting a key replaces the first and removes
/// the others. A key not there is added at the end of its section, and a section not there at the end of the file.
/// </summary>
internal sealed class IniText
{
    private readonly List<string> _lines;
    private readonly string _newline;
    private readonly bool _bom;
    private readonly bool _finalNewline;

    private IniText(List<string> lines, string newline, bool bom, bool finalNewline)
    {
        _lines = lines;
        _newline = newline;
        _bom = bom;
        _finalNewline = finalNewline;
    }

    public static IniText Parse(byte[] bytes)
    {
        ArgumentNullException.ThrowIfNull(bytes);
        var bom = bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF;
        var text = new UTF8Encoding(false).GetString(bytes, bom ? 3 : 0, bom ? bytes.Length - 3 : bytes.Length);
        var newline = text.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";
        var finalNewline = text.Length == 0 || text.EndsWith('\n');
        var lines = new List<string>(text.Split('\n'));
        if (finalNewline)
        {
            lines.RemoveAt(lines.Count - 1);
        }

        for (var i = 0; i < lines.Count; i++)
        {
            lines[i] = lines[i].TrimEnd('\r');
        }

        return new IniText(lines, newline, bom, finalNewline);
    }

    public byte[] ToBytes()
    {
        var text = string.Join(_newline, _lines) + (_finalNewline && _lines.Count > 0 ? _newline : string.Empty);
        var body = new UTF8Encoding(false).GetBytes(text);
        return _bom ? [0xEF, 0xBB, 0xBF, .. body] : body;
    }

    /// <summary>The first value of <paramref name="key"/> in <paramref name="section"/>, unquoted, or null.</summary>
    public string? Get(string section, string key)
    {
        var (start, end) = Section(section);
        for (var i = start; i < end; i++)
        {
            if (KeyOf(_lines[i]) is { } found && found.Equals(key, StringComparison.OrdinalIgnoreCase))
            {
                return ValueOf(_lines[i]).Replace("\"", string.Empty, StringComparison.Ordinal);
            }
        }

        return null;
    }

    /// <summary>Sets <paramref name="key"/> to <paramref name="value"/>, written as it is (quote it yourself).</summary>
    public void Set(string section, string key, string value)
    {
        var line = key + "=" + value;
        var (start, end) = Section(section);
        if (start < 0)
        {
            if (_lines.Count > 0 && _lines[^1].Trim().Length > 0)
            {
                _lines.Add(string.Empty);
            }

            _lines.Add("[" + section + "]");
            _lines.Add(line);
            return;
        }

        var replaced = false;
        for (var i = start; i < end; i++)
        {
            if (KeyOf(_lines[i]) is not { } found || !found.Equals(key, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (!replaced)
            {
                _lines[i] = line;
                replaced = true;
            }
            else
            {
                _lines.RemoveAt(i);
                i--;
                end--;
            }
        }

        if (!replaced)
        {
            // After the section's last key, before the blank lines that end it.
            var at = end;
            while (at > start && _lines[at - 1].Trim().Length == 0)
            {
                at--;
            }

            _lines.Insert(at, line);
        }
    }

    /// <summary>The lines after the section's header up to the next header; (-1, -1) when there's no such section.</summary>
    private (int Start, int End) Section(string section)
    {
        for (var i = 0; i < _lines.Count; i++)
        {
            if (SectionOf(_lines[i]) is { } name && name.Equals(section, StringComparison.OrdinalIgnoreCase))
            {
                var end = i + 1;
                while (end < _lines.Count && SectionOf(_lines[end]) is null)
                {
                    end++;
                }

                return (i + 1, end);
            }
        }

        return (-1, -1);
    }

    private static string? SectionOf(string line)
    {
        var trimmed = line.Trim();
        return trimmed.Length >= 2 && trimmed[0] == '[' && trimmed[^1] == ']' ? trimmed[1..^1].Trim() : null;
    }

    private static string? KeyOf(string line)
    {
        var trimmed = line.TrimStart();
        if (trimmed.Length == 0 || trimmed[0] is ';' or '#' or '[')
        {
            return null;
        }

        var equals = trimmed.IndexOf('=', StringComparison.Ordinal);
        return equals > 0 ? trimmed[..equals].TrimEnd() : null;
    }

    private static string ValueOf(string line)
    {
        var equals = line.IndexOf('=', StringComparison.Ordinal);
        return line[(equals + 1)..].Trim();
    }
}
