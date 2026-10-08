using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Scraping;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Config;

/// <summary>
/// M7 acceptance: TOML writes preserve comments and formatting and contain only changed values; secrets are written
/// only to secrets.toml; input is validated before saving.
/// </summary>
public sealed class ConfigWriterTests : IDisposable
{
    private readonly TempDir _dir = new();

    private ConfigWriter Writer() => new(_dir.Combine("config"), _dir.Path) { FileExists = null, Environment = _ => null };

    private string ConfigFile(string name) => _dir.Combine("config", name);

    private string Write(string name, string text)
    {
        Directory.CreateDirectory(_dir.Combine("config"));
        File.WriteAllText(ConfigFile(name), text);
        return text;
    }

    public void Dispose() => _dir.Dispose();

    [Fact]
    public void A_first_change_creates_the_file_with_that_value_only()
    {
        var result = Writer().Save([new ConfigEdit(ConfigFileKind.Settings, ["display", "theme"], "retro-tv")]);

        Assert.True(result.Saved, result.Problem);
        Assert.Equal([ConfigFile("settings.toml")], result.ChangedFiles);
        var text = File.ReadAllText(ConfigFile("settings.toml"));
        Assert.EndsWith("format = 1\n\n[display]\ntheme = \"retro-tv\"\n", text, StringComparison.Ordinal);
        Assert.StartsWith("# ", text, StringComparison.Ordinal);
        Assert.Equal("retro-tv", result.Config!.Config.Settings.Display.Theme);
        Assert.False(File.Exists(ConfigFile("systems.toml")));
        Assert.False(File.Exists(ConfigFile("settings.toml.saving")));
    }

    [Fact]
    public void Editing_keeps_the_users_comments_and_layout()
    {
        var original = Write("settings.toml", """
            # Mine.
            [display]
            theme = "memory-card"   # the default look
            fullscreen = false      # I use a window

            # Scraping
            [scraping]
            provider = "igdb"
            """);

        var result = Writer().Save(
        [
            new ConfigEdit(ConfigFileKind.Settings, ["display", "theme"], "slot-showcase"),
            new ConfigEdit(ConfigFileKind.Settings, ["scraping", "fallback"], (string[])["steamgriddb"]),
        ]);

        Assert.True(result.Saved, result.Problem);
        Assert.Equal(
            original.Replace("theme = \"memory-card\"", "theme = \"slot-showcase\"", StringComparison.Ordinal) + "\nfallback = [\"steamgriddb\"]\n",
            File.ReadAllText(ConfigFile("settings.toml")));
    }

    [Fact]
    public void A_value_equal_to_the_default_isnt_added_and_one_set_back_to_it_is_removed()
    {
        Write("settings.toml", "[display]\ntheme = \"retro-tv\"\n\n[scraping]\nprovider = \"igdb\" # I prefer it\n");
        var writer = Writer();

        var noop = writer.Save([new ConfigEdit(ConfigFileKind.Settings, ["display", "screen_mode"], "borderless")]);
        Assert.True(noop.Saved);
        Assert.Empty(noop.ChangedFiles);

        writer.Save(
        [
            new ConfigEdit(ConfigFileKind.Settings, ["display", "theme"], "slab"),
            new ConfigEdit(ConfigFileKind.Settings, ["scraping", "provider"], "screenscraper"),
        ]);

        // The theme's line had no comment, so it goes (and its empty table); the provider's has one, so it stays, updated.
        Assert.Equal("[scraping]\nprovider = \"screenscraper\" # I prefer it\n", File.ReadAllText(ConfigFile("settings.toml")));
    }

    [Fact]
    public void A_status_indicator_turned_off_gets_a_ui_table_and_turned_on_again_leaves_nothing()
    {
        Write("settings.toml", "[display]\ntheme = \"retro-tv\"\n");
        var writer = Writer();

        var off = writer.Save([new ConfigEdit(ConfigFileKind.Settings, ["ui", "show_clock"], false)]);
        Assert.True(off.Saved, off.Problem);
        Assert.Equal("[display]\ntheme = \"retro-tv\"\n\n[ui]\nshow_clock = false\n", File.ReadAllText(ConfigFile("settings.toml")));
        Assert.False(off.Config!.Config.Settings.Ui.ShowClock);

        var on = writer.Save([new ConfigEdit(ConfigFileKind.Settings, ["ui", "show_clock"], true)]);
        Assert.True(on.Saved, on.Problem);
        // The empty table goes too (the blank line that separated it stays).
        Assert.Equal("[display]\ntheme = \"retro-tv\"\n", File.ReadAllText(ConfigFile("settings.toml")).TrimEnd('\n') + "\n");
        Assert.True(on.Config!.Config.Settings.Ui.ShowClock);
    }

    [Fact]
    public void Layouts_and_a_systems_own_games_grid_size_are_written_and_removed_again()
    {
        var writer = Writer();
        var saved = writer.Save(
        [
            new ConfigEdit(ConfigFileKind.Settings, ["display", "games_layout"], "list"),
            new ConfigEdit(ConfigFileKind.Settings, ["display", "systems_columns"], 4L),
            new ConfigEdit(ConfigFileKind.Systems, ["systems", "snes", "games_columns"], 0L),
            new ConfigEdit(ConfigFileKind.Systems, ["systems", "snes", "games_layout"], "carousel"),
        ]);

        Assert.True(saved.Saved, saved.Problem);
        Assert.EndsWith("[display]\ngames_layout = \"list\"\nsystems_columns = 4\n", File.ReadAllText(ConfigFile("settings.toml")), StringComparison.Ordinal);
        Assert.EndsWith("[systems.snes]\ngames_columns = 0\ngames_layout = \"carousel\"\n", File.ReadAllText(ConfigFile("systems.toml")), StringComparison.Ordinal);
        var config = saved.Config!.Config;
        Assert.Equal(GamesLayout.List, config.Settings.Display.GamesLayout);
        Assert.Equal(new GridSize(4, 0), config.Settings.Display.SystemsGrid);
        Assert.Equal(0, config.FindSystem("snes")!.GamesColumns);
        Assert.Equal(GamesLayout.Carousel, config.Settings.Display.GamesLayoutFor(config.FindSystem("snes")));

        // A system's 0 (automatic) is its own choice, so only null takes it back to [display]'s.
        var removed = writer.Save(
        [
            new ConfigEdit(ConfigFileKind.Systems, ["systems", "snes", "games_columns"], null),
            new ConfigEdit(ConfigFileKind.Systems, ["systems", "snes", "games_layout"], null),
        ]);
        Assert.True(removed.Saved, removed.Problem);
        Assert.Null(removed.Config!.Config.FindSystem("snes")!.GamesColumns);
        Assert.Null(removed.Config!.Config.FindSystem("snes")!.GamesLayout);
        Assert.DoesNotContain("games_", File.ReadAllText(ConfigFile("systems.toml")), StringComparison.Ordinal);
    }

    [Fact]
    public void Null_removes_a_key_so_the_default_applies_again()
    {
        Write("systems.toml", "[systems.snes]\nrom_dirs = [\"E:/SNES\"]\nrecursive = false\n");

        var result = Writer().Save([new ConfigEdit(ConfigFileKind.Systems, ["systems", "snes", "rom_dirs"], null)]);

        Assert.Equal("[systems.snes]\nrecursive = false\n", File.ReadAllText(ConfigFile("systems.toml")));
        Assert.Equal(RomDirSource.Default, result.Config!.Config.FindSystem("snes")!.RomDirSource);
    }

    [Fact]
    public void Paths_are_written_so_they_read_back_exactly()
    {
        var folder = OperatingSystem.IsWindows() ? @"D:\Games {x}\ROMs" : "/games {x}/ROMs";

        var result = Writer().Save(
        [
            new ConfigEdit(ConfigFileKind.Settings, ["paths", "rom_root"], ConfigWriter.PathValue(folder)),
            new ConfigEdit(ConfigFileKind.Systems, ["systems", "megadrive", "rom_dirs"], (string[])[ConfigWriter.PathValue(folder + "/md"), "{rom_root}/genesis"]),
        ]);

        Assert.True(result.Saved, result.Problem);
        var config = result.Config!.Config;
        Assert.Equal(Path.GetFullPath(folder), config.Settings.RomRoot);
        Assert.Equal([Path.GetFullPath(folder + "/md"), Path.GetFullPath(Path.Combine(folder, "genesis"))], config.FindSystem("megadrive")!.RomDirs);
        if (OperatingSystem.IsWindows())
        {
            Assert.Contains("rom_root = \"D:/Games {{x}}/ROMs\"", File.ReadAllText(ConfigFile("settings.toml")), StringComparison.Ordinal);
        }
    }

    [Fact]
    public void An_edit_config_would_reject_is_refused_and_nothing_is_written()
    {
        var original = Write("systems.toml", "# keep me\n[systems.snes]\nrecursive = true\n");

        var result = Writer().Save(
        [
            new ConfigEdit(ConfigFileKind.Settings, ["display", "theme"], "retro-tv"),
            new ConfigEdit(ConfigFileKind.Systems, ["systems", "snes", "emulator"], "no-such-emulator"),
        ]);

        Assert.False(result.Saved);
        Assert.Contains("systems.snes.emulator", result.Problem, StringComparison.Ordinal);
        Assert.Contains("no-such-emulator", result.Problem, StringComparison.Ordinal);
        Assert.Equal(original, File.ReadAllText(ConfigFile("systems.toml")));
        Assert.False(File.Exists(ConfigFile("settings.toml")));
    }

    [Fact]
    public void An_error_the_file_already_had_doesnt_block_other_changes()
    {
        Write("systems.toml", "[systems.snes]\nemulator = \"gone\"\n");

        var result = Writer().Save([new ConfigEdit(ConfigFileKind.Systems, ["systems", "megadrive", "recursive"], false)]);

        Assert.True(result.Saved, result.Problem);
    }

    [Fact]
    public void A_file_with_a_syntax_error_is_left_alone()
    {
        var original = Write("settings.toml", "[display\ntheme = 'x'\n");

        var result = Writer().Save([new ConfigEdit(ConfigFileKind.Settings, ["display", "theme"], "retro-tv")]);

        Assert.False(result.Saved);
        Assert.Contains("syntax error at line 1", result.Problem, StringComparison.Ordinal);
        Assert.Equal(original, File.ReadAllText(ConfigFile("settings.toml")));
    }

    [Fact]
    public void Secrets_go_to_secrets_toml_only_and_no_message_quotes_them()
    {
        const string Key = "sgdb-secret-key-1234";
        var writer = Writer();

        var saved = writer.Save([new ConfigEdit(ConfigFileKind.Secrets, ["steamgriddb", "api_key"], Key)]);

        Assert.True(saved.Saved, saved.Problem);
        Assert.Equal([ConfigFile("secrets.toml")], saved.ChangedFiles);
        Assert.StartsWith("# Scraping credentials", File.ReadAllText(ConfigFile("secrets.toml")), StringComparison.Ordinal);
        Assert.EndsWith("\n\n[steamgriddb]\napi_key = \"" + Key + "\"\n", File.ReadAllText(ConfigFile("secrets.toml")), StringComparison.Ordinal);
        Assert.Equal(Key, saved.Accounts!.Accounts.SteamGridDbApiKey);
        Assert.Equal(CredentialSource.File, saved.Accounts.Accounts.SourceOf("steamgriddb", "api_key"));
        foreach (var file in Directory.GetFiles(_dir.Combine("config")))
        {
            Assert.Equal(Path.GetFileName(file) == "secrets.toml", File.ReadAllText(file).Contains(Key, StringComparison.Ordinal));
        }

        // A value TOML can't hold as typed is quoted, never echoed in a problem.
        var odd = writer.Save([new ConfigEdit(ConfigFileKind.Secrets, ["igdb", "client_secret"], "a\"b'c\\d")]);
        Assert.True(odd.Saved, odd.Problem);
        Assert.Equal("a\"b'c\\d", odd.Accounts!.Accounts.IgdbClientSecret);

        var cleared = writer.Save([new ConfigEdit(ConfigFileKind.Secrets, ["steamgriddb", "api_key"], null)]);
        Assert.Null(cleared.Accounts!.Accounts.SteamGridDbApiKey);
        Assert.DoesNotContain(Key, File.ReadAllText(ConfigFile("secrets.toml")), StringComparison.Ordinal);
    }

    [Fact]
    public void A_byte_order_mark_and_windows_line_endings_are_kept()
    {
        Directory.CreateDirectory(_dir.Combine("config"));
        File.WriteAllBytes(ConfigFile("settings.toml"), [0xEF, 0xBB, 0xBF, .. Encoding.UTF8.GetBytes("[display]\r\ntheme = \"x\"\r\n")]);

        Writer().Save([new ConfigEdit(ConfigFileKind.Settings, ["display", "fullscreen"], false)]);

        var bytes = File.ReadAllBytes(ConfigFile("settings.toml"));
        Assert.Equal([0xEF, 0xBB, 0xBF], bytes[..3]);
        Assert.Equal("[display]\r\ntheme = \"x\"\r\nfullscreen = false\r\n", Encoding.UTF8.GetString(bytes[3..]));
    }

    [Fact]
    public void Input_checks_explain_what_to_fix()
    {
        var folder = _dir.Combine("roms");
        Directory.CreateDirectory(folder);
        var exe = _dir.File("emu/emu.exe");
        var bat = _dir.File("emu/run.bat");

        Assert.Null(ConfigInput.CheckFolder(folder));
        Assert.Contains("doesn't exist", ConfigInput.CheckFolder(folder + "-gone"), StringComparison.Ordinal);
        Assert.Contains("full path", ConfigInput.CheckFolder("roms"), StringComparison.Ordinal);
        Assert.Null(ConfigInput.CheckExecutable(exe));
        if (OperatingSystem.IsWindows())
        {
            Assert.Contains("batch file", ConfigInput.CheckExecutable(bat), StringComparison.Ordinal);
        }

        Assert.NotNull(ConfigInput.CheckCredential("   "));
        Assert.NotNull(ConfigInput.CheckCredential("two\nlines"));
        Assert.Null(ConfigInput.CheckCredential("fine-value"));
        Assert.Null(ConfigInput.CheckProviders("igdb", ["screenscraper"]));
        Assert.NotNull(ConfigInput.CheckProviders("igdb", ["igdb"]));
        Assert.NotNull(ConfigInput.CheckProviders("nope", []));
    }
}
