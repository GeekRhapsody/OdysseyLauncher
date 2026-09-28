using System.Text;

namespace Launcher.Core.Config;

/// <summary>A piece of a template: literal text, or the name of a <c>{placeholder}</c>.</summary>
internal readonly record struct TemplatePart(bool IsPlaceholder, string Text);

/// <summary>
/// The <c>{name}</c> template syntax used in config (ARCHITECTURE.md A5). <c>{{</c> and <c>}}</c> are
/// literal braces. Config variables are expanded at load; launch placeholders stay in the template
/// until launch time, so an expanded template is still a template.
/// </summary>
public static class Template
{
    /// <summary>Placeholders that are only known at launch time.</summary>
    public static IReadOnlySet<string> LaunchPlaceholders { get; } =
        new HashSet<string>(StringComparer.Ordinal) { "rom", "rom_dir", "rom_file", "rom_name", "system", "emulator_dir" };

    /// <summary>Placeholders the loader provides itself, which variables can't shadow.</summary>
    public static IReadOnlySet<string> BuiltInVariables { get; } =
        new HashSet<string>(StringComparer.Ordinal) { "home", "rom_root" };

    /// <summary>Escapes braces so <paramref name="literal"/> survives as literal text in a template.</summary>
    public static string Escape(string literal)
    {
        ArgumentNullException.ThrowIfNull(literal);
        return literal.Contains('{', StringComparison.Ordinal) || literal.Contains('}', StringComparison.Ordinal)
            ? literal.Replace("{", "{{", StringComparison.Ordinal).Replace("}", "}}", StringComparison.Ordinal)
            : literal;
    }

    /// <summary>A placeholder name: letters, digits, <c>_</c> and <c>-</c>.</summary>
    public static bool IsValidName(string name)
    {
        ArgumentNullException.ThrowIfNull(name);
        if (name.Length == 0)
        {
            return false;
        }

        foreach (var c in name)
        {
            if (!(char.IsAsciiLetterOrDigit(c) || c == '_' || c == '-'))
            {
                return false;
            }
        }

        return true;
    }

    /// <summary>Splits a template into literal and placeholder parts, or returns an error message.</summary>
    internal static string? TryParse(string text, List<TemplatePart> parts)
    {
        parts.Clear();
        var literal = new StringBuilder();
        var i = 0;
        while (i < text.Length)
        {
            var c = text[i];
            if (c == '{')
            {
                if (i + 1 < text.Length && text[i + 1] == '{')
                {
                    literal.Append('{');
                    i += 2;
                    continue;
                }

                var close = text.IndexOf('}', i + 1);
                if (close < 0)
                {
                    return $"'{{' at position {i + 1} has no closing '}}'. Write '{{{{' for a literal brace";
                }

                var name = text[(i + 1)..close];
                if (!IsValidName(name))
                {
                    return name.Length == 0
                        ? "'{}' is an empty placeholder"
                        : $"'{{{name}}}' isn't a valid placeholder name (use letters, digits, '_' and '-')";
                }

                if (literal.Length > 0)
                {
                    parts.Add(new TemplatePart(false, literal.ToString()));
                    literal.Clear();
                }

                parts.Add(new TemplatePart(true, name));
                i = close + 1;
                continue;
            }

            if (c == '}')
            {
                if (i + 1 < text.Length && text[i + 1] == '}')
                {
                    literal.Append('}');
                    i += 2;
                    continue;
                }

                return $"'}}' at position {i + 1} has no opening '{{'. Write '}}}}' for a literal brace";
            }

            literal.Append(c);
            i++;
        }

        if (literal.Length > 0)
        {
            parts.Add(new TemplatePart(false, literal.ToString()));
        }

        return null;
    }
}
