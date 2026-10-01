using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Tests.Theming;

namespace Launcher.Core.Tests.Config;

/// <summary>The fast parser for the built-in defaults must build exactly the tree Tomlyn's path builds, positions included.</summary>
public class TomlFastTests
{
    private static string Describe(TomlNode node)
    {
        var text = new StringBuilder();
        Write(text, node, 0);
        return text.ToString();
    }

    private static void Write(StringBuilder text, TomlNode node, int depth)
    {
        var pad = new string(' ', depth * 2);
        text.Append(pad).Append(node.Kind).Append(" @").Append(node.Pos.Line).Append(':').Append(node.Pos.Column).Append(' ').Append(node.Pos.Source);
        switch (node)
        {
            case TomlScalar scalar:
                text.Append(' ').Append(scalar.Value.GetType().Name).Append('=').Append(System.Convert.ToString(scalar.Value, System.Globalization.CultureInfo.InvariantCulture)).AppendLine();
                break;
            case TomlArrayNode array:
                text.Append(" tables=").Append(array.IsTableArray).AppendLine();
                foreach (var item in array.Items)
                {
                    Write(text, item, depth + 1);
                }

                break;
            case TomlTableNode table:
                text.AppendLine();
                foreach (var key in table.Keys)
                {
                    table.TryGet(key, out var child);
                    text.Append(pad).Append(" [").Append(key).AppendLine("]");
                    Write(text, child, depth + 1);
                }

                break;
        }
    }

    private static void AssertSameTree(string text, string source = "test.toml")
    {
        var diagnostics = new List<Diagnostic>();
        var expected = TomlTree.Parse(text, source, diagnostics);
        Assert.NotNull(expected);
        var fast = TomlFast.TryParse(text, source);
        Assert.NotNull(fast);
        Assert.Equal(Describe(expected), Describe(fast));
    }

    [Theory]
    [InlineData("settings.toml")]
    [InlineData("systems.toml")]
    [InlineData("emulators.toml")]
    public void The_built_in_defaults_parse_to_the_same_tree_as_Tomlyn(string file)
    {
        var text = file switch
        {
            "settings.toml" => BuiltInDefaults.Settings.Text,
            "systems.toml" => BuiltInDefaults.Systems.Text,
            _ => BuiltInDefaults.Emulators.Text,
        };

        AssertSameTree(text, "built-in/" + file);
    }

    [Fact]
    public void The_built_in_theme_parses_to_the_same_tree_as_Tomlyn()
    {
        AssertSameTree(File.ReadAllText(Path.Combine(ThemeFixtures.BuiltInFolder, "theme.toml")), "theme.toml");
    }

    [Fact]
    public void Tables_arrays_of_tables_escapes_numbers_and_comments_match_Tomlyn()
    {
        AssertSameTree("""
            # a comment
            top = 1
            neg = -42
            real = 0.25
            exp = 1.5e3
            flag = true # trailing comment
            off = false
            literal = 'C:\raw\path'
            plain = "with \"quotes\", a \\ backslash, a tab\t and \u00E9 and \n newline"
            list = ["a", "b",]
            numbers = [-0.5, 1.0, 3]

            [one.two]
            key = "v"

            [[lights]]
            colour = "#FFFFFF"

            [[lights]]
            colour = "#000000"
            [one]
            late = 1
            """);
    }

    [Fact]
    public void Windows_line_endings_and_a_missing_final_newline_are_accepted()
    {
        AssertSameTree("a = 1\r\n[t]\r\nb = \"x\"\r\n\r\nc = [1, 2]");
    }

    [Theory]
    [InlineData("a = 1\na = 2\n")]                       // a duplicate key
    [InlineData("[t]\n[t]\n")]                           // a table defined twice
    [InlineData("a = 1\n[a]\n")]                         // a table over a value
    [InlineData("a.b = 1\n")]                            // dotted keys
    [InlineData("a = \"\"\"multi\nline\"\"\"\n")]        // multi-line strings
    [InlineData("a = { x = 1 }\n")]                      // inline tables
    [InlineData("a = [1,\n 2]\n")]                       // multi-line arrays
    [InlineData("a = 0x10\n")]
    [InlineData("a = 1979-05-27\n")]
    [InlineData("a = \"\\q\"\n")]                        // an invalid escape
    [InlineData("a = \"unterminated\n")]
    [InlineData("a = 1 b = 2\n")]
    [InlineData("[a b]\n")]
    [InlineData("[\"quoted\"]\n")]
    [InlineData("a = nan\n")]
    public void Anything_it_does_not_handle_is_left_to_Tomlyn(string text)
    {
        Assert.Null(TomlFast.TryParse(text, "test.toml"));
    }

    [Fact]
    public void A_user_file_with_a_syntax_error_still_gets_Tomlyns_diagnostics_when_it_is_a_default()
    {
        var diagnostics = new List<Diagnostic>();

        var tree = TomlTree.ParseBuiltIn("a = = 1\n", "defaults.toml", diagnostics);

        Assert.Null(tree);
        Assert.Contains(diagnostics, d => d.Severity == Severity.Error && d.Message.Contains("syntax error", StringComparison.Ordinal));
    }
}
