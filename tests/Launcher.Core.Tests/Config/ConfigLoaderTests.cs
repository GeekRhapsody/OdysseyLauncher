using Launcher.Core.Config;

namespace Launcher.Core.Tests.Config;

public class ConfigLoaderTests
{
    private static readonly string Home = Path.Combine(Path.GetTempPath(), "odyssey-home");
    private static readonly string ConfigDir = Path.Combine(Home, "config");

    /// <param name="fileExists">The install check's view of the disk. By default every file exists.</param>
    private static ConfigLoadResult Load(
        string? settings = null, string? systems = null, string? emulators = null, Func<string, bool>? fileExists = null) =>
        new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = Home,
            ConfigDir = ConfigDir,
            Settings = settings is null ? null : new ConfigFile("user/settings.toml", settings),
            Systems = systems is null ? null : new ConfigFile("user/systems.toml", systems),
            Emulators = emulators is null ? null : new ConfigFile("user/emulators.toml", emulators),
            FileExists = fileExists ?? (_ => true),
        });

    private static Diagnostic Single(ConfigLoadResult result, Severity severity) =>
        Assert.Single(result.Diagnostics, d => d.Severity == severity);

    // ---- Defaults ------------------------------------------------------------------------------

    [Fact]
    public void The_built_in_defaults_load_without_any_diagnostics()
    {
        var result = Load();

        Assert.Empty(result.Diagnostics);
        Assert.Equal(Path.GetFullPath(Path.Combine(Home, "ROMs")), result.Config.Settings.RomRoot);
        Assert.Equal("C:/RetroArch-Win64", result.Config.Settings.Variables["retroarch"]);
    }

    [Fact]
    public void The_default_systems_cover_the_required_set_with_extensions_and_ScreenScraper_ids()
    {
        var systems = Load().Config.Systems;

        string[] required = ["gb", "gbc", "gba", "nes", "snes", "n64", "gc", "mastersystem", "megadrive", "saturn", "dreamcast", "psx", "ps2", "psp"];
        Assert.Equal(required, systems.Select(s => s.Id));
        Assert.All(systems, system =>
        {
            Assert.NotEmpty(system.Extensions);
            Assert.All(system.Extensions, ext => Assert.StartsWith(".", ext, StringComparison.Ordinal));
            Assert.NotNull(system.ScreenScraperId);
            Assert.Contains(system.GameModel, ConfigLoader.GameModels);
        });

        // Checked against ScreenScraper's own system pages (see Defaults/systems.toml).
        var ids = systems.ToDictionary(s => s.Id, s => s.ScreenScraperId);
        Assert.Equal(1, ids["megadrive"]);
        Assert.Equal(2, ids["mastersystem"]);
        Assert.Equal(3, ids["nes"]);
        Assert.Equal(4, ids["snes"]);
        Assert.Equal(9, ids["gb"]);
        Assert.Equal(10, ids["gbc"]);
        Assert.Equal(12, ids["gba"]);
        Assert.Equal(13, ids["gc"]);
        Assert.Equal(14, ids["n64"]);
        Assert.Equal(22, ids["saturn"]);
        Assert.Equal(23, ids["dreamcast"]);
        Assert.Equal(57, ids["psx"]);
        Assert.Equal(58, ids["ps2"]);
        Assert.Equal(61, ids["psp"]);
    }

    [Fact]
    public void Disc_systems_leave_out_bin_so_stray_tracks_never_show()
    {
        var systems = Load().Config.Systems;

        foreach (var id in (string[])["saturn", "dreamcast", "psx", "ps2", "psp", "gc"])
        {
            Assert.DoesNotContain(".bin", systems.Single(s => s.Id == id).Extensions);
        }
    }

    [Fact]
    public void Built_in_emulator_templates_expand_variables_and_keep_launch_placeholders()
    {
        var emulator = Load().Config.Emulators["retroarch-genesis-plus-gx"];

        Assert.Equal(Path.GetFullPath("C:/RetroArch-Win64/retroarch.exe"), emulator.Executable);
        Assert.Equal(["-L", "{core}", "--fullscreen", "{rom}"], emulator.Args);
        Assert.Equal(Path.GetFullPath("C:/RetroArch-Win64/cores/genesis_plus_gx_libretro.dll"), emulator.Core);
        Assert.Equal("{emulator_dir}", emulator.WorkingDir);
    }

    // ---- ROM folders ---------------------------------------------------------------------------

    [Fact]
    public void A_system_defaults_to_its_id_then_its_aliases_under_rom_root()
    {
        var result = Load(settings: """
            [paths]
            rom_root = "D:/Games/ROMs"
            """);

        var megadrive = result.Config.FindSystem("megadrive")!;
        Assert.Equal(RomDirSource.Default, megadrive.RomDirSource);
        Assert.Equal(
            [Path.GetFullPath("D:/Games/ROMs/megadrive"), Path.GetFullPath("D:/Games/ROMs/genesis"), Path.GetFullPath("D:/Games/ROMs/md")],
            megadrive.RomDirs);
    }

    [Fact]
    public void A_system_can_list_several_folders_using_variables_and_relative_paths()
    {
        var result = Load(
            settings: """
                [variables]
                sega = "E:/Sega"
                """,
            systems: """
                [systems.megadrive]
                rom_dirs = ["{sega}/Mega Drive", "{rom_root}/genesis", "local/md"]
                """);

        Assert.Empty(result.Diagnostics);
        var megadrive = result.Config.FindSystem("megadrive")!;
        Assert.Equal(RomDirSource.Configured, megadrive.RomDirSource);
        Assert.Equal(
            [
                Path.GetFullPath("E:/Sega/Mega Drive"),
                Path.GetFullPath(Path.Combine(Home, "ROMs", "genesis")),
                Path.GetFullPath(Path.Combine(ConfigDir, "local", "md")),
            ],
            megadrive.RomDirs);

        // The rest of the built-in entry is still there.
        Assert.Equal("Mega Drive", megadrive.Name);
        Assert.Contains(".md", megadrive.Extensions);
    }

    [Fact]
    public void A_user_file_changes_only_the_keys_it_sets()
    {
        var result = Load(systems: """
            [systems.megadrive]
            emulator = "retroarch-mesen"
            """);

        var megadrive = result.Config.FindSystem("megadrive")!;
        Assert.Equal("retroarch-mesen", megadrive.Emulator);
        Assert.Equal(1, megadrive.ScreenScraperId);
    }

    [Fact]
    public void Scanning_exclusions_default_to_ES_DE_media_folders_and_gamelists_for_every_system()
    {
        var config = Load().Config;

        string[] defaults = ["images", "manuals", "videos", "gamelist.xml"];
        Assert.Equal(defaults, config.Settings.Scanning.Exclude);
        Assert.All(config.Systems, system => Assert.Equal(defaults, system.Exclude));
    }

    [Fact]
    public void A_user_exclusion_list_replaces_the_default_and_a_system_adds_its_own()
    {
        var result = Load(
            settings: """
                [scanning]
                exclude = ["media", "*.txt"]
                """,
            systems: """
                [systems.psx]
                exclude = ["bios", "MEDIA"]
                """);

        Assert.Empty(result.Diagnostics);
        Assert.Equal(["media", "*.txt"], result.Config.Settings.Scanning.Exclude);
        Assert.Equal(["media", "*.txt", "bios"], result.Config.FindSystem("psx")!.Exclude);
        Assert.Equal(["media", "*.txt"], result.Config.FindSystem("snes")!.Exclude);
    }

    [Fact]
    public void An_empty_exclusion_list_turns_the_defaults_off()
    {
        var config = Load(settings: "[scanning]\nexclude = []\n").Config;

        Assert.Empty(config.FindSystem("gb")!.Exclude);
    }

    [Fact]
    public void A_bad_exclusion_pattern_is_an_error_and_the_defaults_are_used()
    {
        var result = Load(settings: """
            [scanning]
            exclude = ["images", "media\\art"]
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal("scanning.exclude", error.Key);
        Assert.Equal(2, error.Line);
        Assert.Contains("use '/' to separate folders", error.Message, StringComparison.Ordinal);
        Assert.Equal(["images", "manuals", "videos", "gamelist.xml"], result.Config.Settings.Scanning.Exclude);
    }

    [Fact]
    public void An_unknown_scanning_key_is_a_warning()
    {
        var warning = Single(Load(settings: "[scanning]\nexclude_dirs = []\n"), Severity.Warning);

        Assert.Equal("scanning.exclude_dirs", warning.Key);
    }

    [Fact]
    public void Enabled_false_switches_off_a_built_in_system()
    {
        var result = Load(systems: """
            [systems.mastersystem]
            enabled = false
            """);

        Assert.Empty(result.Diagnostics);
        Assert.Null(result.Config.FindSystem("mastersystem"));
        Assert.NotNull(result.Config.FindSystem("megadrive"));
    }

    [Fact]
    public void A_complete_new_system_is_added_after_the_built_in_ones()
    {
        var result = Load(systems: """
            [systems.gamegear]
            name = "Game Gear"
            extensions = [".GG", ".zip"]
            emulator = "retroarch-genesis-plus-gx"
            """);

        Assert.Empty(result.Diagnostics);
        var gamegear = result.Config.Systems[^1];
        Assert.Equal("gamegear", gamegear.Id);
        Assert.Equal([".gg", ".zip"], gamegear.Extensions);
        Assert.Equal("dvd_case", gamegear.GameModel);
        Assert.True(gamegear.Recursive);
    }

    // ---- Each class of error -------------------------------------------------------------------

    [Fact]
    public void A_syntax_error_names_file_line_and_column_and_ignores_the_whole_file()
    {
        var result = Load(systems: """
            [systems.megadrive]
            emulator = "blastem"
            year = = 1988
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal("user/systems.toml", error.Source);
        Assert.Equal(3, error.Line);
        Assert.True(error.Column > 0);
        Assert.Contains("whole file was ignored", error.Message, StringComparison.Ordinal);

        // The broken file's other values weren't applied either.
        Assert.Equal("retroarch-genesis-plus-gx", result.Config.FindSystem("megadrive")!.Emulator);
    }

    [Fact]
    public void A_duplicate_key_is_a_syntax_error()
    {
        var result = Load(settings: """
            [display]
            theme = "a"
            theme = "b"
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal(3, error.Line);
        Assert.Equal("memory-card", result.Config.Settings.Display.Theme);
    }

    [Fact]
    public void An_unknown_key_is_a_warning_with_a_suggestion()
    {
        var result = Load(systems: """
            [systems.megadrive]
            emulater = "blastem"
            """);

        var warning = Single(result, Severity.Warning);
        Assert.Equal("user/systems.toml", warning.Source);
        Assert.Equal(2, warning.Line);
        Assert.Equal(1, warning.Column);
        Assert.Equal("systems.megadrive.emulater", warning.Key);
        Assert.Contains("did you mean 'emulator'?", warning.Message, StringComparison.Ordinal);
        Assert.NotNull(result.Config.FindSystem("megadrive"));
    }

    [Fact]
    public void An_unknown_top_level_table_is_a_warning()
    {
        var result = Load(systems: """
            [system.megadrive]
            name = "x"
            """);

        var warning = Single(result, Severity.Warning);
        Assert.Equal("system", warning.Key);
        Assert.Contains("did you mean 'systems'?", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_new_system_missing_required_keys_lists_them_and_is_disabled()
    {
        var result = Load(systems: """

            [systems.gamegear]
            name = "Game Gear"
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal(2, error.Line);
        Assert.Equal("systems.gamegear", error.Key);
        Assert.Contains("missing: extensions, emulator", error.Message, StringComparison.Ordinal);
        Assert.Null(result.Config.FindSystem("gamegear"));
        Assert.Contains(result.Diagnostics, d => d.Severity == Severity.Info && d.Key == "systems.gamegear");
    }

    [Fact]
    public void An_unknown_emulator_is_an_error_that_disables_only_that_system()
    {
        var result = Load(systems: """
            [systems.megadrive]
            name = "Mega Drive"
            emulator = "blastemm"
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal("user/systems.toml", error.Source);
        Assert.Equal(3, error.Line);
        Assert.Equal("systems.megadrive.emulator", error.Key);
        Assert.Contains("unknown emulator 'blastemm'", error.Message, StringComparison.Ordinal);
        Assert.Null(result.Config.FindSystem("megadrive"));
        Assert.Equal(13, result.Config.Systems.Count);
    }

    [Fact]
    public void An_unknown_alternative_emulator_is_only_a_warning()
    {
        var result = Load(systems: """
            [systems.psx]
            alt_emulators = ["duckstation"]
            """);

        var warning = Single(result, Severity.Warning);
        Assert.Equal("systems.psx.alt_emulators", warning.Key);
        Assert.Empty(result.Config.FindSystem("psx")!.AltEmulators);
    }

    [Fact]
    public void An_unknown_placeholder_is_an_error_that_disables_the_emulator_and_its_systems()
    {
        var result = Load(emulators: """
            [emulators.retroarch-mgba]
            args = ["-L", "{retroarch}/cores/mgba_libretro.dll", "{romm}"]
            """);

        var placeholder = Assert.Single(result.Diagnostics, d => d.Key == "emulators.retroarch-mgba.args");
        Assert.Equal(Severity.Error, placeholder.Severity);
        Assert.Equal(2, placeholder.Line);
        Assert.Contains("unknown placeholder {romm} (did you mean 'rom'?)", placeholder.Message, StringComparison.Ordinal);
        Assert.False(result.Config.Emulators.ContainsKey("retroarch-mgba"));

        // gba's emulator is now invalid, so gba is disabled; gb only listed it as an alternative.
        var gba = Assert.Single(result.Diagnostics, d => d.Key == "systems.gba.emulator");
        Assert.Contains("has errors (see emulators.retroarch-mgba)", gba.Message, StringComparison.Ordinal);
        Assert.Equal("built-in/systems.toml", gba.Source);
        Assert.Null(result.Config.FindSystem("gba"));
        Assert.Empty(result.Config.FindSystem("gb")!.AltEmulators);
    }

    [Theory]
    [InlineData("{rom", "has no closing '}'")]
    [InlineData("rom}", "has no opening '{'")]
    [InlineData("{}", "empty placeholder")]
    [InlineData("{a b}", "isn't a valid placeholder name")]
    public void A_malformed_template_is_an_error(string arg, string expected)
    {
        var result = Load(emulators: $$"""
            [emulators.pcsx2]
            args = ["{{arg}}"]
            """);

        var error = Assert.Single(result.Diagnostics, d => d.Key == "emulators.pcsx2.args");
        Assert.Contains(expected, error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Braces_can_be_escaped_and_expansion_is_single_pass()
    {
        var result = Load(
            settings: """
                [variables]
                odd = "C:/{{braces}}"
                """,
            emulators: """
                [emulators.pcsx2]
                args = ["--x={{literal}}", "{odd}/{rom}"]
                """);

        Assert.Empty(result.Diagnostics);
        Assert.Equal("C:/{braces}", result.Config.Settings.Variables["odd"]);

        // Still a template: the variable's braces are escaped again, the launch placeholder stays.
        Assert.Equal(["--x={{literal}}", "C:/{{braces}}/{rom}"], result.Config.Emulators["pcsx2"].Args);
    }

    [Fact]
    public void A_launch_placeholder_in_the_executable_is_an_error()
    {
        var result = Load(emulators: """
            [emulators.pcsx2]
            executable = "{rom_dir}/pcsx2.exe"
            """);

        var error = Assert.Single(result.Diagnostics, d => d.Key == "emulators.pcsx2.executable");
        Assert.Contains("only known at launch time", error.Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("C:/Emulators/run.bat")]
    [InlineData("C:/Emulators/run.CMD")]
    public void Bat_and_cmd_executables_are_rejected(string executable)
    {
        var result = Load(emulators: $"""
            [emulators.pcsx2]
            executable = "{executable}"
            """);

        var error = Assert.Single(result.Diagnostics, d => d.Key == "emulators.pcsx2.executable");
        Assert.Equal(Severity.Error, error.Severity);
        Assert.Contains("cmd.exe re-parses", error.Message, StringComparison.Ordinal);
        Assert.False(result.Config.Emulators.ContainsKey("pcsx2"));
    }

    // ---- Cores and install checks ---------------------------------------------------------------

    [Fact]
    public void A_core_is_expanded_like_a_path_and_the_built_in_RetroArch_profiles_pass_it_with_L()
    {
        var emulator = Load().Config.Emulators["retroarch-snes9x"];

        Assert.Equal(Path.GetFullPath("C:/RetroArch-Win64/cores/snes9x_libretro.dll"), emulator.Core);
        Assert.Equal(["-L", "{core}", "--fullscreen", "{rom}"], emulator.Args);
        Assert.Null(Load().Config.Emulators["pcsx2"].Core);
    }

    [Fact]
    public void Using_core_in_a_profile_without_one_is_an_error_that_disables_it()
    {
        var result = Load(emulators: """
            [emulators.blastem]
            name = "BlastEm"
            executable = "C:/Emulators/BlastEm/blastem.exe"
            args = ["-L", "{core}", "{rom}"]
            """);

        var error = Assert.Single(result.Diagnostics, d => d.Key == "emulators.blastem.args");
        Assert.Equal(Severity.Error, error.Severity);
        Assert.Contains("{core} is used, but this profile has no core", error.Message, StringComparison.Ordinal);
        Assert.False(result.Config.Emulators.ContainsKey("blastem"));
    }

    [Fact]
    public void A_core_that_no_argument_uses_is_a_warning()
    {
        var result = Load(emulators: """
            [emulators.retroarch-snes9x]
            args = ["{rom}"]
            """);

        var warning = Single(result, Severity.Warning);
        Assert.Equal("emulators.retroarch-snes9x.core", warning.Key);
        Assert.Contains("never passed to the emulator", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Launch_placeholders_can_be_used_in_args_and_rom_name_is_now_rom_stem()
    {
        var result = Load(emulators: """
            [emulators.pcsx2]
            args = ["{rom_stem}", "{emulator}", "{rom_file}", "{system}"]
            """);
        var renamed = Load(emulators: """
            [emulators.pcsx2]
            args = ["{rom_name}"]
            """);

        Assert.Empty(result.Diagnostics);
        var error = Assert.Single(renamed.Diagnostics, d => d.Key == "emulators.pcsx2.args");
        Assert.Contains("unknown placeholder {rom_name}", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_missing_executable_is_a_warning_naming_every_system_it_affects_and_the_systems_stay_enabled()
    {
        var retroarch = Path.GetFullPath("C:/RetroArch-Win64/retroarch.exe");

        var result = Load(fileExists: path => path != retroarch);

        var gpgx = Assert.Single(result.Diagnostics, d => d.Key == "emulators.retroarch-genesis-plus-gx.executable");
        Assert.Equal(Severity.Warning, gpgx.Severity);
        Assert.Equal("built-in/emulators.toml", gpgx.Source);
        Assert.True(gpgx.Line > 0);
        Assert.Equal(
            $"the executable '{retroarch}' doesn't exist, so Master System (mastersystem) and Mega Drive (megadrive) can't " +
            "launch games (it's their emulator). Install it there, or fix the path here or in the [variables] it uses in settings.toml",
            gpgx.Message);

        // gb and gbc use gambatte and list mgba as an alternative; gba uses mgba.
        var mgba = Assert.Single(result.Diagnostics, d => d.Key == "emulators.retroarch-mgba.executable");
        Assert.Contains("Game Boy Advance (gba) can't launch games (it's their emulator); and Game Boy (gb) and Game Boy Color (gbc) can't use it as an alternative", mgba.Message, StringComparison.Ordinal);

        // Every system that uses RetroArch is still there, and nothing else is reported.
        Assert.Equal(14, result.Config.Systems.Count);
        Assert.Equal(13, result.Diagnostics.Count);
        Assert.All(result.Diagnostics, d => Assert.Equal(Severity.Warning, d.Severity));

        // With nothing installed, each profile reports its executable only, not its core as well.
        var nothing = Load(fileExists: _ => false);
        Assert.Equal(16, nothing.Diagnostics.Count);
        Assert.All(nothing.Diagnostics, d => Assert.EndsWith(".executable", d.Key, StringComparison.Ordinal));
    }

    [Fact]
    public void A_missing_core_is_reported_on_its_own_key()
    {
        var core = Path.GetFullPath("C:/RetroArch-Win64/cores/snes9x_libretro.dll");

        var result = Load(fileExists: path => path != core);

        var warning = Single(result, Severity.Warning);
        Assert.Equal("emulators.retroarch-snes9x.core", warning.Key);
        Assert.StartsWith($"the core '{core}' doesn't exist, so Super Nintendo Entertainment System (snes) can't launch games", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Emulators_that_no_system_uses_are_not_checked_and_the_check_can_be_turned_off()
    {
        var checkedPaths = new List<string>();
        var result = Load(
            emulators: """
                [emulators.blastem]
                name = "BlastEm"
                executable = "C:/Emulators/BlastEm/blastem.exe"
                """,
            fileExists: path =>
            {
                checkedPaths.Add(path);
                return false;
            });

        Assert.DoesNotContain(result.Diagnostics, d => d.Key.StartsWith("emulators.blastem", StringComparison.Ordinal));
        Assert.DoesNotContain(Path.GetFullPath("C:/Emulators/BlastEm/blastem.exe"), checkedPaths);

        // Each path is checked once, although 13 profiles share retroarch.exe.
        Assert.Single(checkedPaths, p => p.EndsWith("retroarch.exe", StringComparison.Ordinal));

        var unchecked_ = new ConfigLoader().Load(new ConfigSources { HomeDir = Home, ConfigDir = ConfigDir, FileExists = null });
        Assert.Empty(unchecked_.Diagnostics);
    }

    [Fact]
    public void A_variable_cycle_is_an_error_naming_the_cycle()
    {
        var result = Load(settings: """
            [variables]
            a = "{b}/x"
            b = "{c}/y"
            c = "{a}/z"
            """);

        var cycle = Assert.Single(result.Diagnostics, d => d.Message.Contains("cycle", StringComparison.Ordinal));
        Assert.Contains("a -> b -> c -> a", cycle.Message, StringComparison.Ordinal);
        Assert.Equal("user/settings.toml", cycle.Source);
        Assert.DoesNotContain("a", result.Config.Settings.Variables.Keys);
        Assert.DoesNotContain("c", result.Config.Settings.Variables.Keys);
    }

    [Fact]
    public void A_variable_can_use_home_and_other_variables_in_any_order()
    {
        var result = Load(settings: """
            [variables]
            tools = "{base}/tools"
            base = "{home}/stuff"
            """);

        Assert.Empty(result.Diagnostics);
        Assert.Equal(Home + "/stuff/tools", result.Config.Settings.Variables["tools"]);
    }

    [Fact]
    public void A_variable_cannot_redefine_a_built_in_placeholder()
    {
        var result = Load(settings: """
            [variables]
            rom = "x"
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal("variables.rom", error.Key);
    }

    [Fact]
    public void A_wrong_type_names_the_expected_type_and_the_line()
    {
        var result = Load(systems: """
            [systems.megadrive]
            name = "Mega Drive"
            year = "1988"
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal(3, error.Line);
        Assert.Equal("systems.megadrive.year", error.Key);
        Assert.Contains("expected an integer, found a string", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void An_unknown_box_template_is_an_error_with_a_suggestion()
    {
        var result = Load(systems: """
            [systems.megadrive]
            game_model = "clamshel"
            """);

        var error = Single(result, Severity.Error);
        Assert.Contains("did you mean 'clamshell'?", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_malformed_extension_is_an_error()
    {
        var result = Load(systems: """
            [systems.megadrive]
            extensions = ["md"]
            """);

        var error = Single(result, Severity.Error);
        Assert.Contains("isn't a file extension", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_bad_setting_falls_back_to_its_default()
    {
        var result = Load(settings: """
            [display]
            fullscreen = "yes"

            [scraping]
            cover_sources = ["screenscraper", "steamgrid"]
            """);

        Assert.Equal(2, result.Diagnostics.Count(d => d.IsError));
        Assert.True(result.Config.Settings.Display.Fullscreen);
        Assert.Equal(["screenscraper", "steamgriddb"], result.Config.Settings.Scraping.CoverSources);
        Assert.Contains(result.Diagnostics, d => d.Message.Contains("did you mean 'steamgriddb'?", StringComparison.Ordinal));
    }

    [Fact]
    public void An_unsupported_format_is_an_error()
    {
        var result = Load(settings: "format = 2");

        var error = Single(result, Severity.Error);
        Assert.Equal("format", error.Key);
    }

    [Fact]
    public void Diagnostics_format_as_file_line_column_severity_key_message()
    {
        var diagnostic = new Diagnostic(Severity.Error, "systems.toml", 12, 3, "systems.x.emulator", "unknown emulator 'y'");

        Assert.Equal("systems.toml:12:3: error: systems.x.emulator: unknown emulator 'y'", diagnostic.ToString());
        Assert.Equal("f: warning: m", new Diagnostic(Severity.Warning, "f", 0, 0, "", "m").ToString());
    }
}
