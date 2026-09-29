namespace Launcher.Core.Config;

/// <summary>
/// Typed reads over a <see cref="TomlTableNode"/> tree that turn every user mistake into a <see cref="Diagnostic"/>
/// naming the file, line, column and dotted key. Used by the theme loader; <see cref="ConfigLoader"/> shares its
/// <see cref="Suggest"/> and <see cref="IsValidId"/>.
/// </summary>
internal sealed class TomlValidator
{
    private readonly List<Diagnostic> _diagnostics;

    public TomlValidator(List<Diagnostic> diagnostics)
    {
        _diagnostics = diagnostics;
    }

    public int ErrorCount { get; private set; }

    public void Error(TomlNode node, string key, string message)
    {
        ErrorCount++;
        Add(Severity.Error, node, key, message);
    }

    public void Warning(TomlNode node, string key, string message) => Add(Severity.Warning, node, key, message);

    public void Info(TomlNode node, string key, string message) => Add(Severity.Info, node, key, message);

    private void Add(Severity severity, TomlNode node, string key, string message) =>
        _diagnostics.Add(new Diagnostic(severity, node.Pos.Source, node.Pos.Line, node.Pos.Column, key, message));

    public static string Join(string prefix, string key) => prefix.Length == 0 ? key : $"{prefix}.{key}";

    public TomlTableNode? Table(TomlTableNode table, string prefix, string key)
    {
        if (!table.TryGet(key, out var node))
        {
            return null;
        }

        if (node is TomlTableNode sub)
        {
            return sub;
        }

        Error(node, Join(prefix, key), $"expected a table, found {TomlNode.KindName(node.Kind)}");
        return null;
    }

    public string? String(TomlTableNode table, string prefix, string key)
    {
        if (!table.TryGet(key, out var node))
        {
            return null;
        }

        if (node is TomlScalar { Kind: TomlKind.String, Value: string value })
        {
            return value;
        }

        Error(node, Join(prefix, key), $"expected a string, found {TomlNode.KindName(node.Kind)}");
        return null;
    }

    public string? NonEmptyString(TomlTableNode table, string prefix, string key)
    {
        var value = String(table, prefix, key);
        if (value is not null && value.Trim().Length == 0 && table.TryGet(key, out var node))
        {
            Error(node, Join(prefix, key), "can't be empty");
            return null;
        }

        return value;
    }

    public bool? Bool(TomlTableNode table, string prefix, string key)
    {
        if (!table.TryGet(key, out var node))
        {
            return null;
        }

        if (node is TomlScalar { Kind: TomlKind.Boolean, Value: bool value })
        {
            return value;
        }

        Error(node, Join(prefix, key), $"expected true or false, found {TomlNode.KindName(node.Kind)}");
        return null;
    }

    public long? Integer(TomlTableNode table, string prefix, string key, long min, long max)
    {
        if (!table.TryGet(key, out var node))
        {
            return null;
        }

        if (node is not TomlScalar { Kind: TomlKind.Integer, Value: long value })
        {
            Error(node, Join(prefix, key), $"expected an integer, found {TomlNode.KindName(node.Kind)}");
            return null;
        }

        if (value < min || value > max)
        {
            Error(node, Join(prefix, key), $"{value} is out of range ({min} to {max})");
            return null;
        }

        return value;
    }

    /// <summary>An integer or a float, as a double.</summary>
    public static bool TryNumber(TomlNode node, out double value)
    {
        switch (node)
        {
            case TomlScalar { Kind: TomlKind.Integer, Value: long integer }:
                value = integer;
                return true;
            case TomlScalar { Kind: TomlKind.Float, Value: double number } when double.IsFinite(number):
                value = number;
                return true;
            default:
                value = 0;
                return false;
        }
    }

    public double? Number(TomlTableNode table, string prefix, string key, double min, double max)
    {
        if (!table.TryGet(key, out var node))
        {
            return null;
        }

        if (!TryNumber(node, out var value))
        {
            Error(node, Join(prefix, key), $"expected a number, found {TomlNode.KindName(node.Kind)}");
            return null;
        }

        if (value < min || value > max)
        {
            Error(node, Join(prefix, key), $"{value} is out of range ({min} to {max})");
            return null;
        }

        return value;
    }

    public List<string>? StringArray(TomlNode node, string key)
    {
        if (node is not TomlArrayNode array)
        {
            Error(node, key, $"expected an array of strings, found {TomlNode.KindName(node.Kind)}");
            return null;
        }

        var values = new List<string>(array.Items.Count);
        foreach (var item in array.Items)
        {
            if (item is TomlScalar { Kind: TomlKind.String, Value: string value })
            {
                values.Add(value);
            }
            else
            {
                Error(item, key, $"expected an array of strings, but an item is {TomlNode.KindName(item.Kind)}");
                return null;
            }
        }

        return values;
    }

    public void WarnUnknownKeys(TomlTableNode table, string prefix, IReadOnlyList<string> known)
    {
        foreach (var key in table.Keys)
        {
            if (known.Contains(key))
            {
                continue;
            }

            table.TryGet(key, out var node);
            Warning(node, Join(prefix, key), $"unknown key{Suggest(key, known)}. It's ignored");
        }
    }

    public void CheckFormat(TomlTableNode root, int supported)
    {
        if (!root.TryGet("format", out var node))
        {
            return;
        }

        if (node is not TomlScalar { Kind: TomlKind.Integer, Value: long format })
        {
            Error(node, "format", $"expected an integer, found {TomlNode.KindName(node.Kind)}");
        }
        else if (format != supported)
        {
            Error(node, "format", $"format {format} isn't supported: this version reads format {supported}");
        }
    }

    /// <summary>Lower-case letters, digits, '_' and '-', starting with a letter or digit.</summary>
    public static bool IsValidId(string id)
    {
        if (id.Length == 0 || !(char.IsAsciiLetterLower(id[0]) || char.IsAsciiDigit(id[0])))
        {
            return false;
        }

        foreach (var c in id)
        {
            if (!(char.IsAsciiLetterLower(c) || char.IsAsciiDigit(c) || c == '_' || c == '-'))
            {
                return false;
            }
        }

        return true;
    }

    /// <summary>", did you mean 'x'?" for the closest candidate within two edits, else empty.</summary>
    public static string Suggest(string value, IEnumerable<string> candidates)
    {
        string? best = null;
        var bestDistance = int.MaxValue;
        foreach (var candidate in candidates)
        {
            var distance = EditDistance(value, candidate);
            if (distance < bestDistance)
            {
                best = candidate;
                bestDistance = distance;
            }
        }

        return best is not null && bestDistance <= Math.Min(2, Math.Max(1, value.Length / 3))
            ? $" (did you mean '{best}'?)"
            : string.Empty;
    }

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
                var cost = char.ToLowerInvariant(a[i - 1]) == char.ToLowerInvariant(b[j - 1]) ? 0 : 1;
                current[j] = Math.Min(Math.Min(current[j - 1] + 1, previous[j] + 1), previous[j - 1] + cost);
            }

            (previous, current) = (current, previous);
        }

        return previous[b.Length];
    }
}
