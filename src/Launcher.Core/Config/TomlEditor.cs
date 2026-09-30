using System.Globalization;
using System.Text;
using Tomlyn.Parsing;
using Tomlyn.Syntax;

namespace Launcher.Core.Config;

/// <summary>An edit the file's layout doesn't allow, written for the user (the key, and what to do instead).</summary>
public sealed class TomlEditException(string message) : Exception(message);

/// <summary>
/// Edits a TOML file through Tomlyn's syntax tree (M7), so everything the edit doesn't touch stays exactly as written:
/// comments, blank lines, key order, quoting and line endings. Tomlyn keeps trivia on tokens, so:
/// <list type="bullet">
/// <item>A changed value keeps the comment after it on its line; only a multi-line array's inner comments go, since
/// the array is written again on one line.</item>
/// <item>A new key goes at the end of its table, before the blank lines (and the comments above the next table) that
/// followed the table's last line; a new table goes at the end of the file, after a blank line.</item>
/// <item>A removed key takes its own line with it (its trailing comment too). Comments on other lines stay, and a
/// table left empty goes only if it has no comments.</item>
/// </list>
/// Values are strings (basic quotes, or literal ones for text with backslashes), booleans, integers and arrays of
/// strings. Keys under an array of tables, or inside an inline table, can be changed but not added or removed.
/// </summary>
public sealed class TomlEditor
{
    private readonly DocumentSyntax _document;
    private readonly string _newLine;
    private readonly bool _endsWithNewLine;

    private TomlEditor(DocumentSyntax document, string newLine, bool endsWithNewLine)
    {
        _document = document;
        _newLine = newLine;
        _endsWithNewLine = endsWithNewLine;
    }

    /// <summary>The file's line ending: CRLF if its first line ends with one.</summary>
    public string NewLine => _newLine;

    /// <summary>Parses <paramref name="text"/>. Null (with the first error) when it isn't valid TOML: a file with a syntax error isn't edited.</summary>
    public static TomlEditor? Parse(string text, string source, out Diagnostic? error)
    {
        ArgumentNullException.ThrowIfNull(text);
        ArgumentNullException.ThrowIfNull(source);
        var document = SyntaxParser.Parse(text, source, validate: true);
        if (document.HasErrors)
        {
            var first = document.Diagnostics.First(d => d.Kind == DiagnosticMessageKind.Error);
            error = new Diagnostic(Severity.Error, source, first.Span.Start.Line + 1, first.Span.Start.Column + 1, string.Empty,
                $"TOML syntax error: {first.Message.TrimEnd('.')}");
            return null;
        }

        error = null;
        var firstBreak = text.IndexOf('\n', StringComparison.Ordinal);
        var newLine = firstBreak > 0 && text[firstBreak - 1] == '\r' ? "\r\n" : "\n";
        return new TomlEditor(document, newLine, text.Length == 0 || text.EndsWith('\n'));
    }

    /// <summary>The edited text.</summary>
    public override string ToString() => _document.ToString();

    /// <summary>The value at <paramref name="path"/> as a <see cref="string"/>, <see cref="bool"/>, <see cref="long"/> or string list; null when the file doesn't set it (or it's another kind).</summary>
    public object? Get(IReadOnlyList<string> path)
    {
        var found = Find(path);
        return found is { } f ? ValueOf(f.Value.Value) : null;
    }

    public bool Contains(IReadOnlyList<string> path) => Find(path) is not null;

    /// <summary>True when the line holding <paramref name="path"/>'s value has a comment after it.</summary>
    public bool HasTrailingComment(IReadOnlyList<string> path) =>
        Find(path) is { } found && LastToken(found.Value.Value!) is { } last && HasComment(last.TrailingTrivia);

    /// <summary>Sets <paramref name="path"/> to <paramref name="value"/>, replacing its value or adding the key (and its table).</summary>
    /// <param name="value">A <see cref="string"/>, <see cref="bool"/>, <see cref="int"/>, <see cref="long"/>, or a list of strings.</param>
    /// <exception cref="TomlEditException">The key sits where it can't be added (an inline table, an array of tables).</exception>
    public void Set(IReadOnlyList<string> path, object value)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentNullException.ThrowIfNull(value);
        if (path.Count == 0)
        {
            throw new ArgumentException("The path is empty.", nameof(path));
        }

        var created = MakeValue(value);
        if (Find(path) is { } found)
        {
            // The old value's last token carries the rest of its line (spaces and a comment): the new one keeps it.
            var old = found.Value.Value!;
            if (LastToken(old) is { } oldLast && LastToken(created) is { } newLast)
            {
                newLast.TrailingTrivia = oldLast.TrailingTrivia;
            }

            found.Value.Value = created;
            return;
        }

        var (container, prefix, table) = ContainerFor(path);
        var relative = path.Skip(prefix.Count).ToList();
        var keyValue = new KeyValueSyntax(MakeKey(relative), created)
        {
            EndOfLineToken = new SyntaxToken(TokenKind.NewLine, _newLine),
        };
        Append(container, table, keyValue);
    }

    /// <summary>Removes <paramref name="path"/>'s key. False when the file doesn't set it.</summary>
    /// <exception cref="TomlEditException">The key is inside an inline table.</exception>
    public bool Remove(IReadOnlyList<string> path)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (Find(path) is not { } found)
        {
            return false;
        }

        if (found.Inline)
        {
            throw new TomlEditException($"{string.Join('.', path)} is inside an inline table ({{ ... }}), which the settings screen can't change. Edit the file by hand, or write it as a [{string.Join('.', path.Take(path.Count - 1))}] table.");
        }

        var list = found.List!;
        var index = found.Index;
        var keyValue = found.Value;

        // What came after the removed line (blank lines, the next table's comments) moves to the line before it; a
        // comment above it (on the removed key itself, at the top of the file) moves to whatever follows.
        var after = keyValue.EndOfLineToken?.TrailingTrivia;
        var previous = index > 0 ? ((KeyValueSyntax)list.GetChild(index - 1)!).EndOfLineToken : found.Table?.EndOfLineToken;
        list.RemoveChildAt(index);
        if (after is { Count: > 0 })
        {
            if (previous is not null)
            {
                previous.TrailingTrivia = Concat(previous.TrailingTrivia, after);
            }
            else if (NextNode(found.Table, list, index) is { } next)
            {
                next.LeadingTrivia = Concat(after, next.LeadingTrivia);
            }
        }

        if (keyValue.LeadingTrivia is { Count: > 0 } leading && NextNode(found.Table, list, index) is { } following)
        {
            following.LeadingTrivia = Concat(leading, following.LeadingTrivia);
        }

        if (found.Table is { } table && table.Items.ChildrenCount == 0 && !HasComment(table.EndOfLineToken?.TrailingTrivia) && !HasComment(table.LeadingTrivia))
        {
            for (var i = 0; i < _document.Tables.ChildrenCount; i++)
            {
                if (_document.Tables.GetChild(i) == table)
                {
                    _document.Tables.RemoveChildAt(i);
                    break;
                }
            }
        }

        return true;
    }

    // ---- Finding keys ----------------------------------------------------------------------------

    private sealed record Found(KeyValueSyntax Value, SyntaxList<KeyValueSyntax>? List, int Index, TableSyntax? Table, bool Inline);

    private Found? Find(IReadOnlyList<string> path)
    {
        if (FindIn(_document.KeyValues, [], path, null) is { } atRoot)
        {
            return atRoot;
        }

        foreach (var table in _document.Tables)
        {
            if (table is TableSyntax plain && table.Name is { } name && FindIn(plain.Items, Segments(name), path, plain) is { } found)
            {
                return found;
            }
        }

        return null;
    }

    private static Found? FindIn(SyntaxList<KeyValueSyntax> list, IReadOnlyList<string> prefix, IReadOnlyList<string> path, TableSyntax? table)
    {
        if (!StartsWith(path, prefix))
        {
            return null;
        }

        for (var i = 0; i < list.ChildrenCount; i++)
        {
            var keyValue = (KeyValueSyntax)list.GetChild(i)!;
            if (keyValue.Key is null)
            {
                continue;
            }

            var full = prefix.Concat(Segments(keyValue.Key)).ToList();
            if (full.SequenceEqual(path, StringComparer.Ordinal))
            {
                return new Found(keyValue, list, i, table, false);
            }

            if (keyValue.Value is InlineTableSyntax inline && StartsWith(path, full) && FindInline(inline, full, path) is { } nested)
            {
                return nested;
            }
        }

        return null;
    }

    private static Found? FindInline(InlineTableSyntax inline, List<string> prefix, IReadOnlyList<string> path)
    {
        foreach (var item in inline.Items)
        {
            if (item.KeyValue is not { Key: { } key } keyValue)
            {
                continue;
            }

            var full = prefix.Concat(Segments(key)).ToList();
            if (full.SequenceEqual(path, StringComparer.Ordinal))
            {
                return new Found(keyValue, null, -1, null, true);
            }

            if (keyValue.Value is InlineTableSyntax deeper && StartsWith(path, full) && FindInline(deeper, full, path) is { } nested)
            {
                return nested;
            }
        }

        return null;
    }

    /// <summary>
    /// Where a new key goes: the table named by its parent path; else a table (or the root) that already writes
    /// dotted keys under that parent; else a new table at the end of the file. Adding a <c>[a.b]</c> table where
    /// <c>a</c> already has <c>b.x = ...</c> would define <c>a.b</c> twice.
    /// </summary>
    private (SyntaxList<KeyValueSyntax> Container, IReadOnlyList<string> Prefix, TableSyntax? Table) ContainerFor(IReadOnlyList<string> path)
    {
        var parent = path.Take(path.Count - 1).ToList();
        if (parent.Count == 0)
        {
            return (_document.KeyValues, [], null);
        }

        foreach (var table in _document.Tables)
        {
            if (table.Name is not { } name)
            {
                continue;
            }

            var segments = Segments(name);
            if (segments.SequenceEqual(parent, StringComparer.Ordinal))
            {
                return table is TableSyntax plain
                    ? (plain.Items, segments, plain)
                    : throw new TomlEditException($"{string.Join('.', parent)} is an array of tables ([[{string.Join('.', parent)}]]), so the settings screen can't add {path[^1]} to it. Edit the file by hand.");
            }
        }

        // Dotted keys already under the parent, at the root or in a table above it: add there, the same way.
        var containers = new List<(SyntaxList<KeyValueSyntax> List, IReadOnlyList<string> Prefix, TableSyntax? Table)> { (_document.KeyValues, [], null) };
        foreach (var table in _document.Tables)
        {
            if (table is TableSyntax plain && table.Name is { } name)
            {
                containers.Add((plain.Items, Segments(name), plain));
            }
        }

        foreach (var (list, prefix, owner) in containers.OrderByDescending(c => c.Prefix.Count))
        {
            if (!StartsWith(parent, prefix))
            {
                continue;
            }

            foreach (var keyValue in list)
            {
                if (keyValue.Key is null)
                {
                    continue;
                }

                var full = prefix.Concat(Segments(keyValue.Key)).ToList();
                if (full.Count > parent.Count && StartsWith(full, parent))
                {
                    return (list, prefix, owner);
                }

                if (StartsWith(parent, full) && keyValue.Value is InlineTableSyntax)
                {
                    throw new TomlEditException($"{string.Join('.', full)} is an inline table ({{ ... }}), which the settings screen can't add to. Edit the file by hand, or write it as a [{string.Join('.', full)}] table.");
                }

                if (StartsWith(parent, full))
                {
                    throw new TomlEditException($"{string.Join('.', full)} is set to a value, so it can't also hold {string.Join('.', path)}.");
                }
            }
        }

        var created = new TableSyntax(MakeKey(parent))
        {
            EndOfLineToken = new SyntaxToken(TokenKind.NewLine, _newLine),
        };
        if (TakeCommentsOfEmptyFile() is { } comments)
        {
            // A file of comments alone: they stay above the new table, with a blank line after them.
            created.LeadingTrivia = comments;
        }
        else if (!IsEmpty())
        {
            EnsureEndsWithNewLine();
            if (!EndsWithBlankLine())
            {
                created.LeadingTrivia = [new SyntaxTrivia(TokenKind.NewLine, _newLine)];
            }
        }

        _document.Tables.Add(created);
        return (created.Items, parent, created);
    }

    // ---- Adding ----------------------------------------------------------------------------------

    /// <summary>
    /// Adds a line at the end of a table (or the root keys). The lines after the table's last one (blank lines, and
    /// comments above the next table) belong after the new line; comment lines right below it, with no blank line in
    /// between, stay above it, since they're about that table.
    /// </summary>
    private void Append(SyntaxList<KeyValueSyntax> container, TableSyntax? table, KeyValueSyntax keyValue)
    {
        SyntaxToken? before = null;
        if (container.ChildrenCount > 0)
        {
            before = ((KeyValueSyntax)container.GetChild(container.ChildrenCount - 1)!).EndOfLineToken;
            if (before is null)
            {
                // The file's last line, with no line break yet.
                var last = (KeyValueSyntax)container.GetChild(container.ChildrenCount - 1)!;
                last.EndOfLineToken = new SyntaxToken(TokenKind.NewLine, _newLine);
            }
        }
        else if (table is not null)
        {
            before = table.EndOfLineToken;
        }
        else if (container == _document.KeyValues && _document.Tables.ChildrenCount > 0)
        {
            // The first root key of a file that has only tables: it goes above them, with a blank line.
            keyValue.EndOfLineToken!.TrailingTrivia = [new SyntaxTrivia(TokenKind.NewLine, _newLine)];
        }
        else if (container == _document.KeyValues && TakeCommentsOfEmptyFile() is { } comments)
        {
            keyValue.LeadingTrivia = comments;
        }

        if (before?.TrailingTrivia is { Count: > 0 } trivia)
        {
            var split = SplitAtFirstBlankLine(trivia);
            before.TrailingTrivia = trivia.Take(split).ToList();
            keyValue.EndOfLineToken!.TrailingTrivia = trivia.Skip(split).ToList();
        }

        container.Add(keyValue);
    }

    /// <summary>The index of the first trivia that starts a blank line (or the end).</summary>
    private static int SplitAtFirstBlankLine(List<SyntaxTrivia> trivia)
    {
        var lineStart = 0;
        var blank = true;
        for (var i = 0; i < trivia.Count; i++)
        {
            switch (trivia[i].Kind)
            {
                case TokenKind.NewLine:
                    if (blank)
                    {
                        return lineStart;
                    }

                    lineStart = i + 1;
                    blank = true;
                    break;
                case TokenKind.Whitespaces:
                    break;
                default:
                    blank = false;
                    break;
            }
        }

        return blank ? lineStart : trivia.Count;
    }

    private bool IsEmpty() => _document.KeyValues.ChildrenCount == 0 && _document.Tables.ChildrenCount == 0 && _document.ToString().Trim().Length == 0;

    /// <summary>
    /// A file with nothing but comments keeps them as the document's own trailing trivia, which is written after
    /// everything: taken off it (ending with a blank line) for the first node to carry in front of itself. Null when
    /// the file has any key or table.
    /// </summary>
    private List<SyntaxTrivia>? TakeCommentsOfEmptyFile()
    {
        if (_document.KeyValues.ChildrenCount > 0 || _document.Tables.ChildrenCount > 0 || _document.TrailingTrivia is not { Count: > 0 } trivia)
        {
            return null;
        }

        _document.TrailingTrivia = null;
        var comments = new List<SyntaxTrivia>(trivia);
        if (comments[^1].Kind != TokenKind.NewLine)
        {
            comments.Add(new SyntaxTrivia(TokenKind.NewLine, _newLine));
        }

        if (comments.Count < 2 || comments[^2].Kind != TokenKind.NewLine)
        {
            comments.Add(new SyntaxTrivia(TokenKind.NewLine, _newLine));
        }

        return comments;
    }

    private bool EndsWithBlankLine()
    {
        var text = _document.ToString().TrimEnd(' ', '\t');
        return text.EndsWith("\n\n", StringComparison.Ordinal) || text.EndsWith("\n\r\n", StringComparison.Ordinal);
    }

    private void EnsureEndsWithNewLine()
    {
        if (_endsWithNewLine && _document.ToString().EndsWith('\n'))
        {
            return;
        }

        if (!_document.ToString().EndsWith('\n') && LastToken(_document) is { } last)
        {
            last.TrailingTrivia = Concat(last.TrailingTrivia, [new SyntaxTrivia(TokenKind.NewLine, _newLine)]);
        }
    }

    // ---- Values and keys --------------------------------------------------------------------------

    private static ValueSyntax MakeValue(object value) => value switch
    {
        string s => MakeString(s),
        bool b => new BooleanValueSyntax(b),
        int i => new IntegerValueSyntax(i),
        long l => new IntegerValueSyntax(l),
        IEnumerable<string> strings => MakeArray(strings.ToList()),
        _ => throw new ArgumentException($"A config value can't be a {value.GetType().Name}.", nameof(value)),
    };

    private static ArraySyntax MakeArray(List<string> items)
    {
        var array = new ArraySyntax
        {
            OpenBracket = new SyntaxToken(TokenKind.OpenBracket, "["),
            CloseBracket = new SyntaxToken(TokenKind.CloseBracket, "]"),
        };
        for (var i = 0; i < items.Count; i++)
        {
            var item = new ArrayItemSyntax { Value = MakeString(items[i]) };
            if (i < items.Count - 1)
            {
                item.Comma = new SyntaxToken(TokenKind.Comma, ",") { TrailingTrivia = [new SyntaxTrivia(TokenKind.Whitespaces, " ")] };
            }

            array.Items.Add(item);
        }

        return array;
    }

    /// <summary>A literal string ('...') for text with backslashes and nothing a literal can't hold; else a basic one.</summary>
    private static StringValueSyntax MakeString(string value)
    {
        var literal = value.Contains('\\', StringComparison.Ordinal) && !value.Contains('\'', StringComparison.Ordinal) && !value.Any(char.IsControl);
        var text = literal ? "'" + value + "'" : Quote(value);
        return new StringValueSyntax
        {
            Token = new SyntaxToken(literal ? TokenKind.StringLiteral : TokenKind.String, text),
            Value = value,
        };
    }

    /// <summary>A TOML basic string.</summary>
    public static string Quote(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        var builder = new StringBuilder(value.Length + 2).Append('"');
        foreach (var c in value)
        {
            switch (c)
            {
                case '"': builder.Append("\\\""); break;
                case '\\': builder.Append("\\\\"); break;
                case '\b': builder.Append("\\b"); break;
                case '\t': builder.Append("\\t"); break;
                case '\n': builder.Append("\\n"); break;
                case '\f': builder.Append("\\f"); break;
                case '\r': builder.Append("\\r"); break;
                default:
                    if (char.IsControl(c))
                    {
                        builder.Append("\\u").Append(((int)c).ToString("X4", CultureInfo.InvariantCulture));
                    }
                    else
                    {
                        builder.Append(c);
                    }

                    break;
            }
        }

        return builder.Append('"').ToString();
    }

    private static KeySyntax MakeKey(IReadOnlyList<string> segments)
    {
        var key = new KeySyntax { Key = KeyPart(segments[0]) };
        for (var i = 1; i < segments.Count; i++)
        {
            key.DotKeys.Add(new DottedKeyItemSyntax { Dot = new SyntaxToken(TokenKind.Dot, "."), Key = KeyPart(segments[i]) });
        }

        return key;
    }

    private static BareKeyOrStringValueSyntax KeyPart(string segment) =>
        segment.Length > 0 && segment.All(c => char.IsAsciiLetterOrDigit(c) || c is '_' or '-')
            ? new BareKeySyntax { Key = new SyntaxToken(TokenKind.BasicKey, segment) }
            : new StringValueSyntax { Token = new SyntaxToken(TokenKind.String, Quote(segment)), Value = segment };

    private static object? ValueOf(ValueSyntax? value) => value switch
    {
        StringValueSyntax s => s.Value,
        BooleanValueSyntax b => b.Value,
        IntegerValueSyntax i => i.Value,
        ArraySyntax a when a.Items.All(item => item.Value is StringValueSyntax) =>
            a.Items.Select(item => ((StringValueSyntax)item.Value!).Value ?? string.Empty).ToList(),
        _ => null,
    };

    // ---- Syntax helpers ---------------------------------------------------------------------------

    private static List<string> Segments(KeySyntax key)
    {
        var segments = new List<string> { Segment(key.Key) };
        if (key.DotKeys is not null)
        {
            foreach (var dotted in key.DotKeys)
            {
                segments.Add(Segment(dotted.Key));
            }
        }

        return segments;
    }

    private static string Segment(BareKeyOrStringValueSyntax? part) => part switch
    {
        BareKeySyntax bare => bare.Key?.Text ?? string.Empty,
        StringValueSyntax quoted => quoted.Value ?? string.Empty,
        _ => string.Empty,
    };

    private static bool StartsWith(IReadOnlyList<string> path, IReadOnlyList<string> prefix)
    {
        if (prefix.Count > path.Count)
        {
            return false;
        }

        for (var i = 0; i < prefix.Count; i++)
        {
            if (!string.Equals(path[i], prefix[i], StringComparison.Ordinal))
            {
                return false;
            }
        }

        return true;
    }

    private static SyntaxToken? LastToken(SyntaxNode node)
    {
        if (node is SyntaxToken token)
        {
            return token;
        }

        for (var i = node.ChildrenCount - 1; i >= 0; i--)
        {
            if (node.GetChild(i) is { } child && LastToken(child) is { } found)
            {
                return found;
            }
        }

        return null;
    }

    /// <summary>The node that follows the removed key: the next key in its list, else the next table.</summary>
    private SyntaxNode? NextNode(TableSyntax? table, SyntaxList<KeyValueSyntax> list, int removedIndex)
    {
        if (removedIndex < list.ChildrenCount)
        {
            return list.GetChild(removedIndex);
        }

        var tables = _document.Tables;
        var start = 0;
        if (table is not null)
        {
            for (var i = 0; i < tables.ChildrenCount; i++)
            {
                if (tables.GetChild(i) == table)
                {
                    start = i + 1;
                    break;
                }
            }
        }

        return start < tables.ChildrenCount ? tables.GetChild(start) : null;
    }

    private static bool HasComment(List<SyntaxTrivia>? trivia) => trivia is not null && trivia.Exists(t => t.Kind == TokenKind.Comment);

    private static List<SyntaxTrivia> Concat(List<SyntaxTrivia>? first, List<SyntaxTrivia>? second) => [.. first ?? [], .. second ?? []];
}
