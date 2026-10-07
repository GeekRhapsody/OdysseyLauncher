using Launcher.Core.Config;

namespace Launcher.Core.Tests.Config;

public class ConfigLoaderTests
{
    private static readonly string Home = Path.Combine(Path.GetTempPath(), "odyssey-home");
    private static readonly string ConfigDir = Path.Combine(Home, "config");

    /// <summary>The systems that were built in before the ES-DE catalogue was added, which the install-check tests count on.</summary>
    private static readonly HashSet<string> FirstFourteen = new(
        ["gb", "gbc", "gba", "nes", "snes", "n64", "gc", "mastersystem", "megadrive", "saturn", "dreamcast", "psx", "ps2", "psp"],
        StringComparer.Ordinal);

    /// <param name="fileExists">The install check's view of the disk. By default every file exists.</param>
    /// <param name="checkFor">Which systems the install check covers. By default all of them.</param>
    private static ConfigLoadResult Load(
        string? settings = null, string? systems = null, string? emulators = null, Func<string, bool>? fileExists = null,
        Func<string, bool>? checkFor = null) =>
        new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = Home,
            ConfigDir = ConfigDir,
            Settings = settings is null ? null : new ConfigFile("user/settings.toml", settings),
            Systems = systems is null ? null : new ConfigFile("user/systems.toml", systems),
            Emulators = emulators is null ? null : new ConfigFile("user/emulators.toml", emulators),
            FileExists = fileExists ?? (_ => true),
            CheckInstallsFor = checkFor,
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

        // The first fourteen are the original built-ins, in this order, and the ES-DE catalogue follows them.
        string[] required = ["gb", "gbc", "gba", "nes", "snes", "n64", "gc", "mastersystem", "megadrive", "saturn", "dreamcast", "psx", "ps2", "psp"];
        Assert.Equal(required, systems.Take(required.Length).Select(s => s.Id));
        Assert.All(systems, system =>
        {
            Assert.NotEmpty(system.Extensions);
            Assert.All(system.Extensions, ext => Assert.StartsWith(".", ext, StringComparison.Ordinal));

            // The theme decides each system's box (M6); game_model is only the user's choice.
            Assert.Null(system.GameModel);
        });
        Assert.All(systems.Take(required.Length), system => Assert.NotNull(system.ScreenScraperId));

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
            [
                Path.GetFullPath("D:/Games/ROMs/megadrive"), Path.GetFullPath("D:/Games/ROMs/genesis"), Path.GetFullPath("D:/Games/ROMs/md"),
                Path.GetFullPath("D:/Games/ROMs/megadrivejp"),
            ],
            megadrive.RomDirs);
    }

    [Fact]
    public void The_media_folder_is_unset_by_default_and_can_be_anywhere_relative_paths_against_ConfigDir()
    {
        Assert.Null(Load().Config.Settings.MediaDir);

        var absolute = Load(settings: """
            [variables]
            big = "E:/Big drive"

            [paths]
            media = "{big}/Launcher media"
            """);
        Assert.Empty(absolute.Diagnostics);
        Assert.Equal(Path.GetFullPath("E:/Big drive/Launcher media"), absolute.Config.Settings.MediaDir);

        var relative = Load(settings: """
            [paths]
            media = "my media"
            """);
        Assert.Equal(Path.Combine(ConfigDir, "my media"), relative.Config.Settings.MediaDir);
    }

    [Fact]
    public void A_bad_media_folder_is_an_error_and_the_default_is_used()
    {
        var result = Load(settings: """
            [paths]
            media = ""
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal("paths.media", error.Key);
        Assert.Null(result.Config.Settings.MediaDir);

        var number = Load(settings: """
            [paths]
            media = 3
            """);
        Assert.Equal("paths.media", Single(number, Severity.Error).Key);
        Assert.Null(number.Config.Settings.MediaDir);
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
            [systems.pocketgame]
            name = "Pocket Game"
            extensions = [".GG", ".zip"]
            emulator = "retroarch-genesis-plus-gx"
            """);

        Assert.Empty(result.Diagnostics);
        var pocketgame = result.Config.Systems[^1];
        Assert.Equal("pocketgame", pocketgame.Id);
        Assert.Equal([".gg", ".zip"], pocketgame.Extensions);
        Assert.Null(pocketgame.GameModel);
        Assert.True(pocketgame.Recursive);
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
        Assert.Equal("console", result.Config.Settings.Display.Theme);
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

            [systems.pocketgame]
            name = "Pocket Game"
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal(2, error.Line);
        Assert.Equal("systems.pocketgame", error.Key);
        Assert.Contains("missing: extensions, emulator", error.Message, StringComparison.Ordinal);
        Assert.Null(result.Config.FindSystem("pocketgame"));
        Assert.Contains(result.Diagnostics, d => d.Severity == Severity.Info && d.Key == "systems.pocketgame");
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
        Assert.Equal(Load().Config.Systems.Count - 1, result.Config.Systems.Count);
    }

    [Fact]
    public void An_unknown_alternative_emulator_is_only_a_warning()
    {
        var result = Load(systems: """
            [systems.psx]
            alt_emulators = ["no-such-emulator"]
            """);

        var warning = Single(result, Severity.Warning);
        Assert.Equal("systems.psx.alt_emulators", warning.Key);
        Assert.Empty(result.Config.FindSystem("psx")!.AltEmulators);
    }

    [Fact]
    public void A_system_offers_its_built_in_emulator_and_alternatives_after_the_user_chooses_another()
    {
        var builtIn = Load().Config.FindSystem("megadrive")!;
        Assert.Equal(builtIn.Emulator, builtIn.DefaultEmulator);
        Assert.Equal([builtIn.Emulator, .. builtIn.AltEmulators], builtIn.OfferedEmulators());

        var alternative = builtIn.AltEmulators[0];
        var chosen = Load(systems: $"""
            [systems.megadrive]
            emulator = "{alternative}"
            """).Config.FindSystem("megadrive")!;
        Assert.Equal(alternative, chosen.Emulator);
        Assert.Equal(builtIn.Emulator, chosen.DefaultEmulator);
        Assert.Equal(builtIn.OfferedEmulators().Order(), chosen.OfferedEmulators().Order());
        Assert.Equal(builtIn.Emulator, chosen.OfferedEmulators()[0]);

        // A profile that's none of them is offered too, as the one in use; nothing else is.
        var other = Load(systems: """
            [systems.megadrive]
            emulator = "pcsx2"
            """).Config.FindSystem("megadrive")!;
        Assert.Equal([.. builtIn.OfferedEmulators(), "pcsx2"], other.OfferedEmulators());

        // A system of the user's own has no built-in emulator: its own comes first.
        var own = Load(systems: """
            [systems.mine]
            name = "Mine"
            extensions = [".bin"]
            emulator = "pcsx2"
            alt_emulators = ["dolphin"]
            """).Config.FindSystem("mine")!;
        Assert.Null(own.DefaultEmulator);
        Assert.Equal(["pcsx2", "dolphin"], own.OfferedEmulators());
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
        Assert.DoesNotContain("retroarch-mgba", result.Config.FindSystem("gb")!.AltEmulators);
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

        var result = Load(fileExists: path => path != retroarch, checkFor: FirstFourteen.Contains);

        var gpgx = Assert.Single(result.Diagnostics, d => d.Key == "emulators.retroarch-genesis-plus-gx.executable");
        Assert.Equal(Severity.Warning, gpgx.Severity);
        Assert.Equal("built-in/emulators.toml", gpgx.Source);
        Assert.True(gpgx.Line > 0);
        Assert.Equal(
            $"the executable '{retroarch}' doesn't exist, so Master System (mastersystem) and Mega Drive (megadrive) can't " +
            "launch games (it's their emulator). Install it there, or fix the path here or in the [variables] it uses in settings.toml",
            gpgx.Message);

        // gb and gbc list mgba as an alternative, which isn't reported (the catalogue lists many); gba uses it.
        var mgba = Assert.Single(result.Diagnostics, d => d.Key == "emulators.retroarch-mgba.executable");
        Assert.Contains("Game Boy Advance (gba) can't launch games (it's their emulator)", mgba.Message, StringComparison.Ordinal);
        Assert.DoesNotContain("alternative", mgba.Message, StringComparison.Ordinal);

        // Every system that uses RetroArch is still there, and each profile is reported once, as a warning.
        Assert.Equal(Load().Config.Systems.Count, result.Config.Systems.Count);
        Assert.All(result.Diagnostics, d => Assert.Equal(Severity.Warning, d.Severity));
        Assert.Equal(result.Diagnostics.Count, result.Diagnostics.Select(d => d.Key).Distinct().Count());

        // With nothing installed, each profile reports its executable only, not its core as well.
        var nothing = Load(fileExists: _ => false, checkFor: FirstFourteen.Contains);
        Assert.All(nothing.Diagnostics, d => Assert.EndsWith(".executable", d.Key, StringComparison.Ordinal));

        // The check covers only the systems it's asked for: none of the others is named.
        Assert.DoesNotContain(nothing.Diagnostics, d => d.Message.Contains("(atari2600)", StringComparison.Ordinal));
        Assert.Contains(Load(fileExists: _ => false).Diagnostics, d => d.Message.Contains("(atari2600)", StringComparison.Ordinal));
    }

    [Fact]
    public void A_missing_core_is_reported_on_its_own_key()
    {
        var core = Path.GetFullPath("C:/RetroArch-Win64/cores/snes9x_libretro.dll");

        var result = Load(fileExists: path => path != core, checkFor: FirstFourteen.Contains);

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
                [emulators.unused-emulator]
                name = "Unused"
                executable = "C:/Emulators/Unused/unused.exe"
                """,
            fileExists: path =>
            {
                checkedPaths.Add(path);
                return false;
            });

        Assert.DoesNotContain(result.Diagnostics, d => d.Key.StartsWith("emulators.unused-emulator", StringComparison.Ordinal));
        Assert.DoesNotContain(Path.GetFullPath("C:/Emulators/Unused/unused.exe"), checkedPaths);

        // Each path is checked once, although many profiles share retroarch.exe.
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
    public void A_game_model_is_a_template_id_the_theme_resolves_later()
    {
        // Themes load after config, so any well-formed id is accepted here; ModelResolver reports one no theme defines.
        var chosen = Load(systems: """
            [systems.megadrive]
            game_model = "tall_case"
            """);
        Assert.Empty(chosen.Diagnostics);
        Assert.Equal("tall_case", chosen.Config.FindSystem("megadrive")!.GameModel);

        var malformed = Load(systems: """
            [systems.megadrive]
            game_model = "Tall Case"
            """);
        var error = Single(malformed, Severity.Error);
        Assert.Equal("systems.megadrive.game_model", error.Key);
        Assert.Contains("isn't a template id", error.Message, StringComparison.Ordinal);
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
    public void Empty_systems_are_hidden_unless_the_setting_says_otherwise()
    {
        Assert.True(Load().Config.Settings.Display.HideEmptySystems);

        var shown = Load(settings: """
            [display]
            hide_empty_systems = false
            """);
        Assert.Empty(shown.Diagnostics);
        Assert.False(shown.Config.Settings.Display.HideEmptySystems);

        var bad = Load(settings: """
            [display]
            hide_empty_systems = "no"
            """);
        Assert.Single(bad.Diagnostics, d => d.IsError && d.Key == "display.hide_empty_systems");
        Assert.True(bad.Config.Settings.Display.HideEmptySystems);
    }

    [Fact]
    public void Every_status_indicator_is_on_unless_the_ui_settings_turn_it_off()
    {
        Assert.Equal(new UiSettings(true, true, true), Load().Config.Settings.Ui);

        var off = Load(settings: """
            [ui]
            show_battery = false
            show_clock = false
            """);
        Assert.Empty(off.Diagnostics);
        Assert.Equal(new UiSettings(ShowClock: false, ShowBattery: false, ShowNetwork: true), off.Config.Settings.Ui);

        var bad = Load(settings: """
            [ui]
            show_network = "no"
            show_clok = false
            """);
        Assert.Single(bad.Diagnostics, d => d.IsError && d.Key == "ui.show_network");
        var unknown = Assert.Single(bad.Diagnostics, d => d.Severity == Severity.Warning);
        Assert.Equal("ui.show_clok", unknown.Key);
        Assert.Contains("did you mean 'show_clock'?", unknown.Message, StringComparison.Ordinal);
        Assert.Equal(new UiSettings(true, true, true), bad.Config.Settings.Ui);
    }

    [Fact]
    public void Layouts_default_to_automatic_grids()
    {
        var display = Load().Config.Settings.Display;
        Assert.Equal(SystemsLayout.Grid, display.SystemsLayout);
        Assert.Equal(GamesLayout.Grid, display.GamesLayout);
        Assert.True(display.SystemsGrid.IsAutomatic);
        Assert.True(display.GamesGrid.IsAutomatic);
        Assert.True(display.GamesGridFor(null).IsAutomatic);
    }

    [Fact]
    public void Layouts_and_grid_sizes_are_read_from_the_display_settings()
    {
        var result = Load(settings: """
            [display]
            systems_layout = "single"
            systems_columns = 4
            games_layout = "list"
            games_columns = 6
            games_rows = 2
            """);

        Assert.Empty(result.Diagnostics);
        var display = result.Config.Settings.Display;
        Assert.Equal(SystemsLayout.Single, display.SystemsLayout);
        Assert.Equal(new GridSize(4, 0), display.SystemsGrid);
        Assert.Equal(GamesLayout.List, display.GamesLayout);
        Assert.Equal(new GridSize(6, 2), display.GamesGrid);
    }

    [Fact]
    public void A_bad_layout_or_size_is_an_error_and_the_default_is_used()
    {
        var result = Load(settings: """
            [display]
            systems_layout = "list"
            games_layout = "carousell"
            games_columns = 10
            systems_rows = -1
            """);

        var systems = Assert.Single(result.Diagnostics, d => d.Key == "display.systems_layout");
        Assert.True(systems.IsError);
        Assert.Contains("'list' isn't a layout for this screen", systems.Message, StringComparison.Ordinal);
        Assert.Contains("grid, carousel, single", systems.Message, StringComparison.Ordinal);
        var games = Assert.Single(result.Diagnostics, d => d.Key == "display.games_layout");
        Assert.Contains("did you mean 'carousel'?", games.Message, StringComparison.Ordinal);
        Assert.Single(result.Diagnostics, d => d.IsError && d.Key == "display.games_columns");
        Assert.Single(result.Diagnostics, d => d.IsError && d.Key == "display.systems_rows");

        var display = result.Config.Settings.Display;
        Assert.Equal(SystemsLayout.Grid, display.SystemsLayout);
        Assert.Equal(GamesLayout.Grid, display.GamesLayout);
        Assert.True(display.SystemsGrid.IsAutomatic);
        Assert.True(display.GamesGrid.IsAutomatic);
    }

    [Fact]
    public void A_system_can_have_its_own_games_grid_size()
    {
        var result = Load(
            settings: """
                [display]
                games_columns = 7
                games_rows = 3
                """,
            systems: """
                [systems.megadrive]
                games_columns = 4

                [systems.snes]
                games_columns = 0
                games_rows = 2
                """);

        Assert.Empty(result.Diagnostics);
        var config = result.Config;
        var display = config.Settings.Display;
        Assert.Equal(new GridSize(4, 3), display.GamesGridFor(config.FindSystem("megadrive")));
        Assert.Equal(new GridSize(0, 2), display.GamesGridFor(config.FindSystem("snes")));
        Assert.Equal(new GridSize(7, 3), display.GamesGridFor(config.FindSystem("psx")));
        Assert.Equal(new GridSize(7, 3), display.GamesGridFor(null));
    }

    [Fact]
    public void A_system_can_have_its_own_games_layout_and_follows_the_display_setting_without_one()
    {
        var result = Load(
            settings: """
                [display]
                games_layout = "carousel"
                """,
            systems: """
                [systems.megadrive]
                games_layout = "list"

                [systems.snes]
                games_layout = "grid"
                """);

        Assert.Empty(result.Diagnostics);
        var config = result.Config;
        var display = config.Settings.Display;
        Assert.Equal(GamesLayout.List, config.FindSystem("megadrive")!.GamesLayout);
        Assert.Equal(GamesLayout.List, display.GamesLayoutFor(config.FindSystem("megadrive")));
        Assert.Equal(GamesLayout.Grid, display.GamesLayoutFor(config.FindSystem("snes")));
        Assert.Null(config.FindSystem("psx")!.GamesLayout);
        Assert.Equal(GamesLayout.Carousel, display.GamesLayoutFor(config.FindSystem("psx")));
        Assert.Equal(GamesLayout.Carousel, display.GamesLayoutFor(null));
    }

    [Fact]
    public void A_bad_games_layout_on_a_system_is_a_warning_and_the_display_setting_is_used()
    {
        foreach (var (value, expected) in ((string, string)[])[("\"single\"", "unknown layout 'single'"), ("\"lists\"", "did you mean 'list'?"), ("2", "expected a string")])
        {
            var result = Load(systems: $"[systems.megadrive]\ngames_layout = {value}\n");
            var warning = Assert.Single(result.Diagnostics);
            Assert.Equal(Severity.Warning, warning.Severity);
            Assert.Equal("systems.megadrive.games_layout", warning.Key);
            Assert.Contains(expected, warning.Message, StringComparison.Ordinal);
            Assert.Null(result.Config.FindSystem("megadrive")!.GamesLayout);
        }
    }

    [Fact]
    public void A_bad_games_grid_size_on_a_system_is_a_warning_and_the_system_stays_enabled()
    {
        var result = Load(systems: """
            [systems.megadrive]
            games_columns = 12
            games_rows = "two"
            """);

        Assert.DoesNotContain(result.Diagnostics, d => d.IsError);
        var columns = Assert.Single(result.Diagnostics, d => d.Key == "systems.megadrive.games_columns");
        Assert.Contains("12 is out of range", columns.Message, StringComparison.Ordinal);
        Assert.Single(result.Diagnostics, d => d.Key == "systems.megadrive.games_rows" && d.Severity == Severity.Warning);
        var system = result.Config.FindSystem("megadrive")!;
        Assert.Null(system.GamesColumns);
        Assert.Null(system.GamesRows);
    }

    // ---- Sorting ----------------------------------------------------------------------------------

    [Fact]
    public void Systems_and_games_sort_alphabetically_ascending_by_default()
    {
        var result = Load();
        Assert.Empty(result.Diagnostics);
        var display = result.Config.Settings.Display;
        Assert.Equal(new SystemsOrdering(SystemSort.Alphabetical, SortOrder.Ascending), display.SystemsSort);
        Assert.Equal(new GamesOrdering(GameSort.Alphabetical, SortOrder.Ascending), display.GamesSort);
        Assert.Equal(display.GamesSort, display.GamesSortFor(result.Config.FindSystem("snes")));
        Assert.Equal(display.GamesSort, display.GamesSortFor(null));
    }

    [Fact]
    public void Sorts_and_orders_are_read_from_the_display_settings()
    {
        var result = Load(settings: """
            [display]
            systems_sort = "manufacturer_year"
            systems_sort_order = "descending"
            games_sort = "release_date"
            games_sort_order = "descending"
            """);

        Assert.Empty(result.Diagnostics);
        var display = result.Config.Settings.Display;
        Assert.Equal(new SystemsOrdering(SystemSort.ManufacturerYear, SortOrder.Descending), display.SystemsSort);
        Assert.Equal(new GamesOrdering(GameSort.ReleaseDate, SortOrder.Descending), display.GamesSort);
    }

    [Fact]
    public void Every_sort_name_round_trips()
    {
        foreach (var sort in Enum.GetValues<SystemSort>())
        {
            Assert.True(Sorts.TryParse(Sorts.Name(sort), out SystemSort parsed));
            Assert.Equal(sort, parsed);
        }

        foreach (var sort in Enum.GetValues<GameSort>())
        {
            Assert.True(Sorts.TryParse(Sorts.Name(sort), out GameSort parsed));
            Assert.Equal(sort, parsed);
        }

        foreach (var order in Enum.GetValues<SortOrder>())
        {
            Assert.True(Sorts.TryParse(Sorts.Name(order), out SortOrder parsed));
            Assert.Equal(order, parsed);
        }

        Assert.False(Sorts.TryParse("by_name", out SystemSort _));
    }

    [Fact]
    public void A_bad_sort_or_order_is_an_error_and_the_default_is_used()
    {
        var result = Load(settings: """
            [display]
            systems_sort = "play_time"
            systems_sort_order = "up"
            games_sort = "last_playd"
            games_sort_order = 1
            """);

        var systems = Assert.Single(result.Diagnostics, d => d.Key == "display.systems_sort");
        Assert.True(systems.IsError);
        Assert.Contains("'play_time' sorts games, not systems", systems.Message, StringComparison.Ordinal);
        Assert.Contains("alphabetical, manufacturer, release_year, manufacturer_year", systems.Message, StringComparison.Ordinal);
        var order = Assert.Single(result.Diagnostics, d => d.Key == "display.systems_sort_order");
        Assert.Contains("unknown order 'up'", order.Message, StringComparison.Ordinal);
        var games = Assert.Single(result.Diagnostics, d => d.Key == "display.games_sort");
        Assert.Contains("did you mean 'last_played'?", games.Message, StringComparison.Ordinal);
        Assert.Single(result.Diagnostics, d => d.IsError && d.Key == "display.games_sort_order");

        var display = result.Config.Settings.Display;
        Assert.Equal(default, display.SystemsSort);
        Assert.Equal(default, display.GamesSort);
    }

    [Fact]
    public void A_system_can_have_its_own_games_sort_and_order_and_follows_the_display_setting_without_them()
    {
        var result = Load(
            settings: """
                [display]
                games_sort = "added"
                games_sort_order = "descending"
                """,
            systems: """
                [systems.megadrive]
                games_sort = "play_time"

                [systems.snes]
                games_sort_order = "ascending"
                """);

        Assert.Empty(result.Diagnostics);
        var config = result.Config;
        var display = config.Settings.Display;
        Assert.Equal(GameSort.PlayTime, config.FindSystem("megadrive")!.GamesSort);
        Assert.Null(config.FindSystem("megadrive")!.GamesSortOrder);
        Assert.Equal(new GamesOrdering(GameSort.PlayTime, SortOrder.Descending), display.GamesSortFor(config.FindSystem("megadrive")));
        Assert.Equal(new GamesOrdering(GameSort.Added, SortOrder.Ascending), display.GamesSortFor(config.FindSystem("snes")));
        Assert.Equal(new GamesOrdering(GameSort.Added, SortOrder.Descending), display.GamesSortFor(config.FindSystem("psx")));
    }

    [Fact]
    public void A_bad_games_sort_on_a_system_is_a_warning_and_the_display_setting_is_used()
    {
        var result = Load(systems: """
            [systems.megadrive]
            games_sort = "manufacturer"
            games_sort_order = "descendng"
            """);

        Assert.DoesNotContain(result.Diagnostics, d => d.IsError);
        var sort = Assert.Single(result.Diagnostics, d => d.Key == "systems.megadrive.games_sort");
        Assert.Contains("unknown sort 'manufacturer'", sort.Message, StringComparison.Ordinal);
        Assert.Contains("[display] games_sort is used", sort.Message, StringComparison.Ordinal);
        var order = Assert.Single(result.Diagnostics, d => d.Key == "systems.megadrive.games_sort_order");
        Assert.Contains("did you mean 'descending'?", order.Message, StringComparison.Ordinal);
        var system = result.Config.FindSystem("megadrive")!;
        Assert.Null(system.GamesSort);
        Assert.Null(system.GamesSortOrder);
    }

    [Fact]
    public void Every_system_in_the_catalogue_has_a_year_except_the_catch_alls()
    {
        var config = Load(settings: "[display]\nhide_empty_systems = false\n").Config;

        // The years are ES-DE's theme metadata's, which gives these catch-all systems none ("Various").
        string[] undated = ["arcade", "consolearcade", "desktop", "lcdgames", "pcarcade", "ports"];
        Assert.Equal(undated, config.Systems.Where(s => s.Year is null).Select(s => s.Id).Order(StringComparer.Ordinal));
        Assert.All(config.Systems.Where(s => s.Year is { }), s => Assert.InRange(s.Year!.Value, 1970, 2030));
    }

    [Fact]
    public void Every_system_in_the_catalogue_has_a_description_on_one_line()
    {
        var config = Load(settings: "[display]\nhide_empty_systems = false\n").Config;

        Assert.All(config.Systems, s =>
        {
            Assert.False(string.IsNullOrWhiteSpace(s.Description), s.Id);
            Assert.DoesNotContain('\n', s.Description!);
        });
        Assert.StartsWith("The Mega Drive is a 16-bit", config.FindSystem("megadrive")!.Description, StringComparison.Ordinal);
    }

    [Fact]
    public void A_system_s_description_can_be_replaced()
    {
        var result = Load(systems: """
            [systems.megadrive]
            description = "Sega's 16-bit console."

            [systems.pocketgame]
            name = "Pocket Game"
            extensions = [".gg"]
            emulator = "retroarch-genesis-plus-gx"
            """);

        Assert.DoesNotContain(result.Diagnostics, d => d.IsError);
        Assert.Equal("Sega's 16-bit console.", result.Config.FindSystem("megadrive")!.Description);
        Assert.Null(result.Config.FindSystem("pocketgame")!.Description);
    }

    // ---- The built-in catalogue (every ES-DE system) ---------------------------------------------

    [Fact]
    public void The_catalogue_folds_regional_twins_into_aliases_so_ES_DE_folders_still_work()
    {
        var config = Load(settings: """
            [paths]
            rom_root = "D:/ROMs"
            """).Config;

        // genesis, megadrivejp, sfc, snesna, famicom and so on aren't systems of their own.
        foreach (var twin in (string[])["genesis", "megadrivejp", "sfc", "snesna", "famicom", "saturnjp", "megacd", "sega32xjp", "tg16", "tg-cd", "videopac", "fba"])
        {
            Assert.Null(config.FindSystem(twin));
        }

        Assert.Contains(Path.GetFullPath("D:/ROMs/megacd"), config.FindSystem("segacd")!.RomDirs);
        Assert.Contains(Path.GetFullPath("D:/ROMs/tg16"), config.FindSystem("pcengine")!.RomDirs);
        Assert.Contains(Path.GetFullPath("D:/ROMs/snesna"), config.FindSystem("snes")!.RomDirs);

        // What isn't a game system, or has nothing to launch, was left out. Windows and Steam games came back later,
        // with their own launching (SteamGameTests), and desktop apps with them.
        foreach (var skipped in (string[])["emulators", "kodi", "epic", "androidapps", "androidgames", "lutris", "xboxone", "psvita"])
        {
            Assert.Null(config.FindSystem(skipped));
        }
    }

    [Fact]
    public void Every_catalogue_system_has_a_launchable_default_and_every_alternative_exists()
    {
        var config = Load().Config;

        Assert.True(config.Systems.Count > 150);
        foreach (var system in config.Systems)
        {
            Assert.True(config.Emulators.ContainsKey(system.Emulator), $"{system.Id}: {system.Emulator}");
            Assert.All(system.AltEmulators, alt => Assert.True(config.Emulators.ContainsKey(alt), $"{system.Id}: {alt}"));
            Assert.Equal(system.AltEmulators.Count, system.AltEmulators.Distinct().Count());
            Assert.DoesNotContain(system.Emulator, system.AltEmulators);
        }

        Assert.Equal(config.Systems.Count, config.Systems.Select(s => s.Id).Distinct().Count());
        Assert.Equal("retroarch-opera", config.FindSystem("3do")!.Emulator);
        Assert.Equal("stella", config.FindSystem("atari2600")!.AltEmulators.Intersect(["stella"]).Single());
    }

    [Fact]
    public void Catalogue_emulators_sit_under_the_emulators_variable_with_ES_DEs_folder_names()
    {
        var emulators = Load().Config.Emulators;

        Assert.Equal("C:/Emulators/Mesen/Mesen.exe", emulators["mesen"].Executable.Replace('\\', '/'));
        Assert.Equal(["--fullscreen", "{rom}"], emulators["mesen"].Args);
        Assert.Equal("C:/RetroArch-Win64/cores/opera_libretro.dll", emulators["retroarch-opera"].Core!.Replace('\\', '/'));
        Assert.Equal(["-L", "{core}", "--fullscreen", "{rom}"], emulators["retroarch-opera"].Args);

        // %GAMEDIR%\;%ROMPATH%\adam became {rom_dir};{rom_root}/adam, and ES-DE's work-in-the-game's-folder flag a working_dir.
        Assert.Equal("{rom_dir};D:/ROMs/adam".Replace("D:/ROMs", Path.GetFullPath(Path.Combine(Home, "ROMs")).Replace('\\', '/')),
            emulators["mame-adam"].Args[1].Replace('\\', '/'));
        Assert.Equal("{rom_dir}", emulators["dosbox-staging"].WorkingDir);

        // Profiles that run the game's own file have no program.
        Assert.True(emulators["run-file"].RunFile);
    }

    [Fact]
    public void Disc_systems_in_the_catalogue_leave_out_bin_too()
    {
        var systems = Load().Config.Systems;

        foreach (var id in (string[])["3do", "pcenginecd", "neogeocd", "segacd", "amigacd32", "cdimono1"])
        {
            Assert.DoesNotContain(".bin", systems.Single(s => s.Id == id).Extensions);
        }
    }

    [Fact]
    public void A_bad_setting_falls_back_to_its_default()
    {
        var result = Load(settings: """
            [display]
            fullscreen = "yes"

            [scraping]
            fallback = ["igdb", "steamgrid"]
            """);

        Assert.Equal(2, result.Diagnostics.Count(d => d.IsError));
        Assert.True(result.Config.Settings.Display.Fullscreen);
        Assert.Equal(["igdb", "steamgriddb"], result.Config.Settings.Scraping.Fallback);
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
