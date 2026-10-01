using Tomlyn.Parsing;
using Tomlyn.Syntax;

namespace Launcher.Core.Config;

/// <summary>Where a key or value was written: 1-based line and column.</summary>
internal readonly record struct SourcePos(string Source, int Line, int Column);

internal enum TomlKind
{
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Array,
    Table,
}

/// <summary>
/// A TOML value that remembers where it was written, so diagnostics can name the file, line and key
/// even after user files have been merged over the built-in defaults.
/// </summary>
internal abstract class TomlNode(SourcePos pos)
{
    /// <summary>Position of the key that defined this node (for array items, of the item itself).</summary>
    public SourcePos Pos { get; } = pos;

    public abstract TomlKind Kind { get; }

    public static string KindName(TomlKind kind) => kind switch
    {
        TomlKind.String => "a string",
        TomlKind.Integer => "an integer",
        TomlKind.Float => "a float",
        TomlKind.Boolean => "a boolean",
        TomlKind.DateTime => "a date-time",
        TomlKind.Array => "an array",
        _ => "a table",
    };
}

internal sealed class TomlScalar(SourcePos pos, TomlKind kind, object value) : TomlNode(pos)
{
    public override TomlKind Kind { get; } = kind;

    public object Value { get; } = value;
}

internal sealed class TomlArrayNode(SourcePos pos) : TomlNode(pos)
{
    public override TomlKind Kind => TomlKind.Array;

    public List<TomlNode> Items { get; } = [];

    /// <summary>True for an array of tables (<c>[[name]]</c>), which later headers append to.</summary>
    public bool IsTableArray { get; init; }
}

internal sealed class TomlTableNode(SourcePos pos) : TomlNode(pos)
{
    private readonly Dictionary<string, TomlNode> _entries = new(StringComparer.Ordinal);
    private readonly List<string> _order = [];

    public override TomlKind Kind => TomlKind.Table;

    /// <summary>Keys in the order they were first written.</summary>
    public IReadOnlyList<string> Keys => _order;

    public int Count => _order.Count;

    public bool TryGet(string key, out TomlNode node) => _entries.TryGetValue(key, out node!);

    public bool Contains(string key) => _entries.ContainsKey(key);

    public void Set(string key, TomlNode node)
    {
        if (_entries.TryAdd(key, node))
        {
            _order.Add(key);
        }
        else
        {
            _entries[key] = node;
        }
    }

    /// <summary>
    /// Layers <paramref name="overlay"/> over this table: tables merge recursively, and scalars and
    /// arrays are replaced whole (ARCHITECTURE.md A5).
    /// </summary>
    public void MergeFrom(TomlTableNode overlay)
    {
        foreach (var key in overlay.Keys)
        {
            var incoming = overlay._entries[key];
            if (incoming is TomlTableNode incomingTable
                && _entries.TryGetValue(key, out var existing)
                && existing is TomlTableNode existingTable)
            {
                existingTable.MergeFrom(incomingTable);
            }
            else
            {
                Set(key, incoming);
            }
        }
    }
}

/// <summary>Parses TOML text into a <see cref="TomlTableNode"/> tree with source positions.</summary>
internal static class TomlTree
{
    /// <summary>
    /// <see cref="Parse"/> for text the app ships (the built-in defaults): the plain-TOML fast path first (about
    /// 50 times quicker, same tree), and Tomlyn if the text needs more than it handles.
    /// </summary>
    public static TomlTableNode? ParseBuiltIn(string text, string source, List<Diagnostic> diagnostics) =>
        TomlFast.TryParse(text, source) ?? Parse(text, source, diagnostics);

    /// <summary>
    /// Parses <paramref name="text"/>. On any syntax or TOML semantic error (such as a duplicate key)
    /// the result is null and every problem is added to <paramref name="diagnostics"/>, so the caller
    /// ignores the whole file (ARCHITECTURE.md A5).
    /// </summary>
    public static TomlTableNode? Parse(string text, string source, List<Diagnostic> diagnostics)
    {
        ArgumentNullException.ThrowIfNull(text);
        ArgumentNullException.ThrowIfNull(source);

        var document = SyntaxParser.Parse(text, source, validate: true);
        if (document.HasErrors)
        {
            // Only the first error: the parser's recovery reports follow-on errors that are rarely real.
            DiagnosticMessage? first = null;
            var count = 0;
            foreach (var message in document.Diagnostics)
            {
                if (message.Kind == DiagnosticMessageKind.Error)
                {
                    first ??= message;
                    count++;
                }
            }

            var start = first!.Span.Start;
            var more = count > 1 ? $" ({count - 1} more error{(count > 2 ? "s" : string.Empty)} may follow from it)" : string.Empty;
            diagnostics.Add(new Diagnostic(
                Severity.Error,
                source,
                start.Line + 1,
                start.Column + 1,
                string.Empty,
                $"TOML syntax error: {first.Message.TrimEnd('.')}{more}. The whole file was ignored."));
            return null;
        }

        var root = new TomlTableNode(new SourcePos(source, 1, 1));
        foreach (var keyValue in document.KeyValues)
        {
            AddKeyValue(root, keyValue, source);
        }

        foreach (var table in document.Tables)
        {
            if (table.Name is null)
            {
                continue;
            }

            var target = OpenTable(root, table.Name, table is TableArraySyntax, source);
            foreach (var keyValue in table.Items)
            {
                AddKeyValue(target, keyValue, source);
            }
        }

        return root;
    }

    private static TomlTableNode OpenTable(TomlTableNode root, KeySyntax name, bool isArray, string source)
    {
        var segments = Segments(name);
        var pos = PosOf(name, source);
        var table = root;
        for (var i = 0; i < segments.Count - 1; i++)
        {
            table = Descend(table, segments[i], pos);
        }

        var last = segments[^1];
        if (isArray)
        {
            if (!table.TryGet(last, out var node) || node is not TomlArrayNode array)
            {
                array = new TomlArrayNode(pos) { IsTableArray = true };
                table.Set(last, array);
            }

            var element = new TomlTableNode(pos);
            array.Items.Add(element);
            return element;
        }

        if (table.TryGet(last, out var existing) && existing is TomlTableNode existingTable)
        {
            return existingTable;
        }

        var created = new TomlTableNode(pos);
        table.Set(last, created);
        return created;
    }

    /// <summary>Walks into (or creates) a sub-table; through an array of tables, the last element.</summary>
    private static TomlTableNode Descend(TomlTableNode table, string key, SourcePos pos)
    {
        if (table.TryGet(key, out var node))
        {
            if (node is TomlTableNode sub)
            {
                return sub;
            }

            if (node is TomlArrayNode { IsTableArray: true, Items.Count: > 0 } array
                && array.Items[^1] is TomlTableNode lastElement)
            {
                return lastElement;
            }
        }

        var created = new TomlTableNode(pos);
        table.Set(key, created);
        return created;
    }

    private static void AddKeyValue(TomlTableNode table, KeyValueSyntax keyValue, string source)
    {
        if (keyValue.Key is null || keyValue.Value is null)
        {
            return;
        }

        var segments = Segments(keyValue.Key);
        var pos = PosOf(keyValue.Key, source);
        var target = table;
        for (var i = 0; i < segments.Count - 1; i++)
        {
            target = Descend(target, segments[i], pos);
        }

        target.Set(segments[^1], Convert(keyValue.Value, pos, source));
    }

    private static TomlNode Convert(ValueSyntax value, SourcePos keyPos, string source)
    {
        switch (value)
        {
            case StringValueSyntax s:
                return new TomlScalar(keyPos, TomlKind.String, s.Value ?? string.Empty);
            case IntegerValueSyntax i:
                return new TomlScalar(keyPos, TomlKind.Integer, i.Value);
            case FloatValueSyntax f:
                return new TomlScalar(keyPos, TomlKind.Float, f.Value);
            case BooleanValueSyntax b:
                return new TomlScalar(keyPos, TomlKind.Boolean, b.Value);
            case DateTimeValueSyntax d:
                return new TomlScalar(keyPos, TomlKind.DateTime, d.Value.ToString() ?? string.Empty);
            case ArraySyntax a:
            {
                var array = new TomlArrayNode(keyPos);
                if (a.Items is not null)
                {
                    foreach (var item in a.Items)
                    {
                        if (item.Value is not null)
                        {
                            array.Items.Add(Convert(item.Value, PosOf(item.Value, source), source));
                        }
                    }
                }

                return array;
            }

            case InlineTableSyntax t:
            {
                var table = new TomlTableNode(keyPos);
                if (t.Items is not null)
                {
                    foreach (var item in t.Items)
                    {
                        if (item.KeyValue is not null)
                        {
                            AddKeyValue(table, item.KeyValue, source);
                        }
                    }
                }

                return table;
            }

            default:
                return new TomlScalar(keyPos, TomlKind.String, value.ToString() ?? string.Empty);
        }
    }

    private static List<string> Segments(KeySyntax key)
    {
        var segments = new List<string> { SegmentText(key.Key) };
        if (key.DotKeys is not null)
        {
            foreach (var dotted in key.DotKeys)
            {
                segments.Add(SegmentText(dotted.Key));
            }
        }

        return segments;
    }

    private static string SegmentText(BareKeyOrStringValueSyntax? segment) => segment switch
    {
        BareKeySyntax bare => bare.Key?.Text ?? string.Empty,
        StringValueSyntax quoted => quoted.Value ?? string.Empty,
        _ => string.Empty,
    };

    private static SourcePos PosOf(SyntaxNode node, string source)
    {
        var start = node.Span.Start;
        return new SourcePos(source, start.Line + 1, start.Column + 1);
    }
}
