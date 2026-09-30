using Launcher.Core.Config;

namespace Launcher.Core.Tests.Config;

/// <summary>M7: writes go through Tomlyn's syntax tree, so everything an edit doesn't touch stays as the user wrote it.</summary>
public sealed class TomlEditorTests
{
    private const string UserSettings = """
        # My launcher settings.
        format = 1

        [paths]
        # Where the ROMs live.
        rom_root = "D:/ROMs"   # the big drive

        # Scraping, as I like it.
        [scraping]
        provider = 'igdb'
        fallback = [
          "screenscraper", # best art
          "steamgriddb",
        ]
        hash_limit_mb = 0x40

        [display]
        fullscreen   =   false

        """;

    private static TomlEditor Parse(string text)
    {
        var editor = TomlEditor.Parse(text, "settings.toml", out var error);
        Assert.Null(error);
        return editor!;
    }

    [Fact]
    public void An_unedited_file_round_trips_byte_for_byte()
    {
        foreach (var text in (string[])[UserSettings, UserSettings.Replace("\n", "\r\n", StringComparison.Ordinal), "a = 1", string.Empty, "# only a comment"])
        {
            Assert.Equal(text, Parse(text).ToString());
        }
    }

    [Fact]
    public void A_changed_value_keeps_its_comment_and_every_other_line()
    {
        var editor = Parse(UserSettings);
        editor.Set(["paths", "rom_root"], "E:/Games");
        editor.Set(["display", "fullscreen"], true);

        Assert.Equal(
            UserSettings
                .Replace("rom_root = \"D:/ROMs\"   # the big drive", "rom_root = \"E:/Games\"   # the big drive", StringComparison.Ordinal)
                .Replace("fullscreen   =   false", "fullscreen   =   true", StringComparison.Ordinal),
            editor.ToString());
    }

    [Fact]
    public void A_new_key_goes_at_the_end_of_its_table_before_the_blank_line_and_the_next_tables_comment()
    {
        var editor = Parse(UserSettings);
        editor.Set(["paths", "extra"], "x");

        Assert.Contains("rom_root = \"D:/ROMs\"   # the big drive\nextra = \"x\"\n\n# Scraping, as I like it.\n[scraping]", editor.ToString(), StringComparison.Ordinal);
        AssertValid(editor);
    }

    [Fact]
    public void A_new_table_goes_at_the_end_after_a_blank_line()
    {
        var editor = Parse(UserSettings);
        editor.Set(["systems", "snes", "emulator"], "retroarch-snes9x");

        Assert.Equal(UserSettings + "\n[systems.snes]\nemulator = \"retroarch-snes9x\"\n", editor.ToString());
    }

    [Fact]
    public void A_file_without_a_final_line_break_gets_one_before_a_new_table()
    {
        var editor = Parse("[display]\ntheme = \"memory-card\" # mine");
        editor.Set(["paths", "rom_root"], "D:/ROMs");

        Assert.Equal("[display]\ntheme = \"memory-card\" # mine\n\n[paths]\nrom_root = \"D:/ROMs\"\n", editor.ToString());
        AssertValid(editor);
    }

    [Fact]
    public void A_new_key_in_a_file_without_a_final_line_break_ends_the_last_line_first()
    {
        var editor = Parse("[display]\ntheme = \"memory-card\"");
        editor.Set(["display", "fullscreen"], false);

        Assert.Equal("[display]\ntheme = \"memory-card\"\nfullscreen = false\n", editor.ToString());
    }

    [Fact]
    public void A_file_ending_in_a_blank_line_doesnt_get_a_second_one()
    {
        var editor = Parse("[display]\ntheme = \"x\"\n\n");
        editor.Set(["systems", "gb", "rom_dirs"], (string[])["E:/GB"]);

        Assert.Equal("[display]\ntheme = \"x\"\n\n[systems.gb]\nrom_dirs = [\"E:/GB\"]\n", editor.ToString());
    }

    [Fact]
    public void A_file_of_comments_alone_keeps_them_above_what_is_added()
    {
        var table = Parse("# Credentials.\n# Keep private.\n");
        table.Set(["igdb", "client_id"], "abc");
        Assert.Equal("# Credentials.\n# Keep private.\n\n[igdb]\nclient_id = \"abc\"\n", table.ToString());

        var root = Parse("# Settings.\n");
        root.Set(["format"], 1L);
        root.Set(["display", "theme"], "retro-tv");
        Assert.Equal("# Settings.\n\nformat = 1\n\n[display]\ntheme = \"retro-tv\"\n", root.ToString());
    }

    [Fact]
    public void An_empty_file_gets_a_table_with_no_blank_line_above_it()
    {
        var editor = Parse(string.Empty);
        editor.Set(["display", "theme"], "retro-tv");

        Assert.Equal("[display]\ntheme = \"retro-tv\"\n", editor.ToString());
    }

    [Fact]
    public void Comment_lines_right_below_a_header_stay_above_a_new_key()
    {
        var editor = Parse("[variables]\n# RetroArch lives here.\n\n# Next.\n[display]\ntheme = \"x\"\n");
        editor.Set(["variables", "retroarch"], "C:/RetroArch");

        Assert.Equal("[variables]\n# RetroArch lives here.\nretroarch = \"C:/RetroArch\"\n\n# Next.\n[display]\ntheme = \"x\"\n", editor.ToString());
    }

    [Fact]
    public void Windows_line_endings_are_kept_on_new_lines()
    {
        var editor = Parse(UserSettings.Replace("\n", "\r\n", StringComparison.Ordinal));
        editor.Set(["paths", "extra"], "x");
        editor.Set(["systems", "gb", "enabled"], false);

        var text = editor.ToString();
        Assert.DoesNotContain("\n", text.Replace("\r\n", string.Empty, StringComparison.Ordinal), StringComparison.Ordinal);
        Assert.EndsWith("\r\n[systems.gb]\r\nenabled = false\r\n", text, StringComparison.Ordinal);
    }

    [Fact]
    public void A_removed_key_takes_its_line_and_keeps_the_comments_around_it()
    {
        var editor = Parse(UserSettings);
        Assert.True(editor.Remove(["paths", "rom_root"]));
        Assert.False(editor.Remove(["paths", "rom_root"]));

        // The comment above it is the user's, so it stays; the table has a comment, so it stays too.
        Assert.Contains("[paths]\n# Where the ROMs live.\n\n# Scraping, as I like it.\n[scraping]", editor.ToString(), StringComparison.Ordinal);
        AssertValid(editor);
    }

    [Fact]
    public void A_table_left_empty_without_comments_goes_with_its_last_key()
    {
        var editor = Parse(UserSettings);
        editor.Set(["systems", "snes", "rom_dirs"], (string[])["E:/SNES"]);
        Assert.True(editor.Remove(["systems", "snes", "rom_dirs"]));
        Assert.True(editor.Remove(["display", "fullscreen"]));

        Assert.Equal(UserSettings.Replace("\n[display]\nfullscreen   =   false\n", string.Empty, StringComparison.Ordinal).TrimEnd('\n') + "\n\n", editor.ToString());
        AssertValid(editor);
    }

    [Fact]
    public void Removing_the_first_key_keeps_the_comment_at_the_top_of_the_file()
    {
        var editor = Parse(UserSettings);
        editor.Remove(["format"]);

        Assert.StartsWith("# My launcher settings.\n", editor.ToString(), StringComparison.Ordinal);
        AssertValid(editor);
    }

    [Fact]
    public void Arrays_are_written_on_one_line()
    {
        var editor = Parse(UserSettings);
        editor.Set(["scraping", "fallback"], (string[])["steamgriddb"]);
        editor.Set(["scraping", "regions"], (string[])[]);

        Assert.Contains("fallback = [\"steamgriddb\"]\nhash_limit_mb = 0x40\nregions = []\n", editor.ToString(), StringComparison.Ordinal);
        Assert.Equal((List<string>)["steamgriddb"], editor.Get(["scraping", "fallback"]));
    }

    [Fact]
    public void Dotted_keys_under_a_table_are_edited_and_extended_where_they_are()
    {
        var editor = Parse("[systems]\nmegadrive.emulator = \"blastem\" # fast\n");
        editor.Set(["systems", "megadrive", "emulator"], "retroarch-genesis-plus-gx");
        editor.Set(["systems", "megadrive", "rom_dirs"], (string[])["E:/MD"]);

        // A [systems.megadrive] table would define it twice.
        Assert.Equal("[systems]\nmegadrive.emulator = \"retroarch-genesis-plus-gx\" # fast\nmegadrive.rom_dirs = [\"E:/MD\"]\n", editor.ToString());
        AssertValid(editor);
    }

    [Fact]
    public void Inline_tables_can_be_changed_but_not_added_to()
    {
        var editor = Parse("[systems]\nmegadrive = { emulator = \"blastem\" }\n");
        editor.Set(["systems", "megadrive", "emulator"], "picodrive");
        Assert.Equal("[systems]\nmegadrive = { emulator = \"picodrive\" }\n", editor.ToString());

        var add = Assert.Throws<TomlEditException>(() => editor.Set(["systems", "megadrive", "rom_dirs"], (string[])["E:/MD"]));
        Assert.Contains("inline table", add.Message, StringComparison.Ordinal);
        Assert.Throws<TomlEditException>(() => editor.Remove(["systems", "megadrive", "emulator"]));
    }

    [Fact]
    public void Strings_are_quoted_so_they_read_back_exactly()
    {
        var values = (string[])[@"\\nas\roms\Mega Drive", @"it's C:\here", "tab\there \"quoted\"", "{rom_root}/x", "日本 ü 😀", "bell\u0007"];
        var editor = Parse(string.Empty);
        for (var i = 0; i < values.Length; i++)
        {
            editor.Set(["t", "k" + i], values[i]);
        }

        Assert.Contains(@"k0 = '\\nas\roms\Mega Drive'", editor.ToString(), StringComparison.Ordinal);
        var reparsed = Parse(editor.ToString());
        for (var i = 0; i < values.Length; i++)
        {
            Assert.Equal(values[i], reparsed.Get(["t", "k" + i]));
        }
    }

    [Fact]
    public void Keys_that_arent_bare_are_quoted()
    {
        var editor = Parse(string.Empty);
        editor.Set(["variables", "my emulators"], "C:/E");

        Assert.Equal("[variables]\n\"my emulators\" = \"C:/E\"\n", editor.ToString());
        Assert.Equal("C:/E", Parse(editor.ToString()).Get(["variables", "my emulators"]));
    }

    [Fact]
    public void Arrays_of_tables_arent_added_to()
    {
        var editor = Parse("[[look.lights]]\nenergy = 1.0\n");
        Assert.Throws<TomlEditException>(() => editor.Set(["look", "lights", "colour"], "#FFFFFF"));
    }

    [Fact]
    public void A_file_with_a_syntax_error_isnt_edited()
    {
        Assert.Null(TomlEditor.Parse("[paths\nrom_root = 1", "settings.toml", out var error));
        Assert.Equal(1, error!.Line);
    }

    [Fact]
    public void A_trailing_comment_is_detected()
    {
        var editor = Parse(UserSettings);
        Assert.True(editor.HasTrailingComment(["paths", "rom_root"]));
        Assert.False(editor.HasTrailingComment(["scraping", "provider"]));
    }

    private static void AssertValid(TomlEditor editor) => Assert.NotNull(TomlEditor.Parse(editor.ToString(), "check", out _));
}
