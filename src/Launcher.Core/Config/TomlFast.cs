using System.Globalization;
using System.Text;

namespace Launcher.Core.Config;

/// <summary>
/// A parser for the plain subset of TOML the built-in defaults and theme use: <c>[a.b]</c> tables and <c>[[a.b]]</c>
/// arrays of tables, bare keys, and string (basic or literal, single-line), integer, float and boolean values and
/// single-line arrays of those. Tomlyn's parser
/// takes about 50 ms for the built-in catalogue (every ES-DE system and emulator), which is too much for boot, and
/// this takes about 1 ms. It builds the same tree as <see cref="TomlTree.Parse"/>, with the same positions (a test
/// compares them for the shipped defaults).
/// <para>
/// It's strict: anything it doesn't handle, or that TOML forbids (a duplicate key, a table defined twice), makes
/// <see cref="TryParse"/> return null, and the caller parses with Tomlyn instead, which also reports the problems.
/// So it never changes what a file means, and it's only used for files the app ships, never the user's.
/// </para>
/// </summary>
internal static class TomlFast
{
    public static TomlTableNode? TryParse(string text, string source)
    {
        ArgumentNullException.ThrowIfNull(text);
        ArgumentNullException.ThrowIfNull(source);

        var root = new TomlTableNode(new SourcePos(source, 1, 1));
        var defined = new HashSet<TomlTableNode>(ReferenceEqualityComparer.Instance);
        var table = root;
        var line = 1;
        var i = 0;
        var n = text.Length;
        StringBuilder? scratch = null;

        while (i < n)
        {
            var lineStart = i;
            i = SkipBlanks(text, i);
            if (i >= n)
            {
                break;
            }

            var c = text[i];
            if (c == '\n')
            {
                i++;
                line++;
                continue;
            }

            if (c == '#')
            {
                i = SkipToLineEnd(text, i);
                continue;
            }

            if (c == '[')
            {
                // [a.b.c] and [[a.b.c]]: bare segments only.
                var isArray = i + 1 < n && text[i + 1] == '[';
                var nameStart = i + (isArray ? 2 : 1);
                var close = text.IndexOf(']', nameStart);
                if (close < 0 || (isArray && (close + 1 >= n || text[close + 1] != ']')))
                {
                    return null;
                }

                var pos = new SourcePos(source, line, nameStart - lineStart + 1);
                var current = root;
                var segmentStart = nameStart;
                for (var j = nameStart; j <= close; j++)
                {
                    if (j < close && text[j] != '.')
                    {
                        if (!IsBareKeyChar(text[j]))
                        {
                            return null;
                        }

                        continue;
                    }

                    if (j == segmentStart)
                    {
                        return null;
                    }

                    var segment = text.Substring(segmentStart, j - segmentStart);
                    segmentStart = j + 1;
                    var last = j == close;
                    if (last && isArray)
                    {
                        if (!current.TryGet(segment, out var existingArray))
                        {
                            existingArray = new TomlArrayNode(pos) { IsTableArray = true };
                            current.Set(segment, existingArray);
                        }

                        if (existingArray is not TomlArrayNode { IsTableArray: true } array)
                        {
                            return null;
                        }

                        var element = new TomlTableNode(pos);
                        array.Items.Add(element);
                        defined.Add(element);
                        current = element;
                    }
                    else if (current.TryGet(segment, out var existing))
                    {
                        if (existing is TomlTableNode next)
                        {
                            current = next;
                        }
                        else if (!last && existing is TomlArrayNode { IsTableArray: true, Items.Count: > 0 } arrayOfTables
                            && arrayOfTables.Items[^1] is TomlTableNode lastElement)
                        {
                            current = lastElement;
                        }
                        else
                        {
                            return null;
                        }
                    }
                    else
                    {
                        var created = new TomlTableNode(pos);
                        current.Set(segment, created);
                        current = created;
                    }
                }

                if (!isArray && !defined.Add(current))
                {
                    return null;
                }

                table = current;
                i = EndOfValueLine(text, close + (isArray ? 2 : 1));
                if (i < 0)
                {
                    return null;
                }

                if (text[i - 1] == '\n')
                {
                    line++;
                }

                continue;
            }

            // key = value
            var keyStart = i;
            while (i < n && IsBareKeyChar(text[i]))
            {
                i++;
            }

            if (i == keyStart)
            {
                return null;
            }

            var key = text.Substring(keyStart, i - keyStart);
            var keyPos = new SourcePos(source, line, keyStart - lineStart + 1);
            i = SkipBlanks(text, i);
            if (i >= n || text[i] != '=')
            {
                return null;
            }

            i = SkipBlanks(text, i + 1);
            var node = ParseValue(text, ref i, keyPos, source, line, lineStart, ref scratch);
            if (node is null || table.Contains(key))
            {
                return null;
            }

            table.Set(key, node);
            i = EndOfValueLine(text, i);
            if (i < 0)
            {
                return null;
            }

            if (text[i - 1] == '\n')
            {
                line++;
            }
        }

        return root;
    }

    private static TomlNode? ParseValue(
        string text, ref int i, SourcePos keyPos, string source, int line, int lineStart, ref StringBuilder? scratch)
    {
        if (i >= text.Length)
        {
            return null;
        }

        var c = text[i];
        if (c == '[')
        {
            var array = new TomlArrayNode(keyPos);
            i = SkipBlanks(text, i + 1);
            while (true)
            {
                if (i >= text.Length)
                {
                    return null;
                }

                if (text[i] == ']')
                {
                    i++;
                    return array;
                }

                var itemPos = new SourcePos(source, line, i - lineStart + 1);
                var item = ParseScalar(text, ref i, itemPos, ref scratch);
                if (item is null)
                {
                    return null;
                }

                array.Items.Add(item);
                i = SkipBlanks(text, i);
                if (i < text.Length && text[i] == ',')
                {
                    i = SkipBlanks(text, i + 1);
                }
                else if (i >= text.Length || text[i] != ']')
                {
                    return null;
                }
            }
        }

        return ParseScalar(text, ref i, keyPos, ref scratch);
    }

    private static TomlScalar? ParseScalar(string text, ref int i, SourcePos pos, ref StringBuilder? scratch)
    {
        if (i >= text.Length)
        {
            return null;
        }

        var c = text[i];
        if (c == '"')
        {
            if (i + 2 < text.Length && text[i + 1] == '"' && text[i + 2] == '"')
            {
                return null;
            }

            var value = ParseBasicString(text, ref i, ref scratch);
            return value is null ? null : new TomlScalar(pos, TomlKind.String, value);
        }

        if (c == '\'')
        {
            if (i + 2 < text.Length && text[i + 1] == '\'' && text[i + 2] == '\'')
            {
                return null;
            }

            var end = text.IndexOf('\'', i + 1);
            if (end < 0 || text.AsSpan(i + 1, end - i - 1).IndexOfAny('\r', '\n') >= 0)
            {
                return null;
            }

            var value = text.Substring(i + 1, end - i - 1);
            i = end + 1;
            return new TomlScalar(pos, TomlKind.String, value);
        }

        if (string.CompareOrdinal(text, i, "true", 0, 4) == 0 && IsValueEnd(text, i + 4))
        {
            i += 4;
            return new TomlScalar(pos, TomlKind.Boolean, true);
        }

        if (string.CompareOrdinal(text, i, "false", 0, 5) == 0 && IsValueEnd(text, i + 5))
        {
            i += 5;
            return new TomlScalar(pos, TomlKind.Boolean, false);
        }

        var start = i;
        if (c is '+' or '-')
        {
            i++;
        }

        var digits = i;
        while (i < text.Length && text[i] is >= '0' and <= '9')
        {
            i++;
        }

        if (i == digits)
        {
            return null;
        }

        // A float has a fractional part (digits after the point) or an exponent.
        var isFloat = false;
        if (i + 1 < text.Length && text[i] == '.' && text[i + 1] is >= '0' and <= '9')
        {
            isFloat = true;
            i++;
            while (i < text.Length && text[i] is >= '0' and <= '9')
            {
                i++;
            }
        }

        if (i < text.Length && text[i] is 'e' or 'E')
        {
            var exponent = i + 1;
            if (exponent < text.Length && text[exponent] is '+' or '-')
            {
                exponent++;
            }

            var exponentDigits = exponent;
            while (exponent < text.Length && text[exponent] is >= '0' and <= '9')
            {
                exponent++;
            }

            if (exponent == exponentDigits)
            {
                return null;
            }

            isFloat = true;
            i = exponent;
        }

        if (!IsValueEnd(text, i))
        {
            return null;
        }

        if (isFloat)
        {
            return double.TryParse(text.AsSpan(start, i - start), NumberStyles.Float, CultureInfo.InvariantCulture, out var real)
                ? new TomlScalar(pos, TomlKind.Float, real)
                : null;
        }

        return long.TryParse(text.AsSpan(start, i - start), NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out var number)
            ? new TomlScalar(pos, TomlKind.Integer, number)
            : null;
    }

    private static string? ParseBasicString(string text, ref int i, ref StringBuilder? scratch)
    {
        var start = i + 1;
        var j = start;
        // The common case has no escapes: one substring.
        while (j < text.Length)
        {
            var c = text[j];
            if (c == '"')
            {
                i = j + 1;
                return text.Substring(start, j - start);
            }

            if (c is '\\' or '\n' or '\r')
            {
                break;
            }

            j++;
        }

        if (j >= text.Length || text[j] != '\\')
        {
            return null;
        }

        var builder = scratch ??= new StringBuilder();
        builder.Clear();
        builder.Append(text, start, j - start);
        while (j < text.Length)
        {
            var c = text[j];
            if (c == '"')
            {
                i = j + 1;
                return builder.ToString();
            }

            if (c is '\n' or '\r')
            {
                return null;
            }

            if (c != '\\')
            {
                builder.Append(c);
                j++;
                continue;
            }

            if (j + 1 >= text.Length)
            {
                return null;
            }

            var escape = text[j + 1];
            j += 2;
            switch (escape)
            {
                case '"': builder.Append('"'); break;
                case '\\': builder.Append('\\'); break;
                case 'n': builder.Append('\n'); break;
                case 't': builder.Append('\t'); break;
                case 'r': builder.Append('\r'); break;
                case 'b': builder.Append('\b'); break;
                case 'f': builder.Append('\f'); break;
                case 'u':
                    if (j + 4 > text.Length
                        || !int.TryParse(text.AsSpan(j, 4), NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture, out var code)
                        || code is >= 0xD800 and <= 0xDFFF)
                    {
                        return null;
                    }

                    builder.Append((char)code);
                    j += 4;
                    break;
                default:
                    return null;
            }
        }

        return null;
    }

    private static bool IsBareKeyChar(char c) => c is (>= 'a' and <= 'z') or (>= 'A' and <= 'Z') or (>= '0' and <= '9') or '_' or '-';

    /// <summary>A value ends at a blank, a comment, a comma, a closing bracket or the line's end.</summary>
    private static bool IsValueEnd(string text, int i) =>
        i >= text.Length || text[i] is ' ' or '\t' or '\r' or '\n' or '#' or ',' or ']';

    private static int SkipBlanks(string text, int i)
    {
        while (i < text.Length && text[i] is ' ' or '\t' or '\r')
        {
            i++;
        }

        return i;
    }

    private static int SkipToLineEnd(string text, int i)
    {
        while (i < text.Length && text[i] != '\n')
        {
            i++;
        }

        return i;
    }

    /// <summary>After a table header or a value: blanks and an optional comment, then the newline (consumed) or the end. -1 if anything else follows.</summary>
    private static int EndOfValueLine(string text, int i)
    {
        i = SkipBlanks(text, i);
        if (i < text.Length && text[i] == '#')
        {
            i = SkipToLineEnd(text, i);
        }

        if (i >= text.Length)
        {
            return text.Length;
        }

        return text[i] == '\n' ? i + 1 : -1;
    }
}
