using Launcher.Core.Config;
using Launcher.Core.Launching;
using Launcher.Core.Library;

namespace Launcher.Core.Tests.Launching;

public class LaunchPlannerTests
{
    private static readonly string Root = Path.Combine(Path.GetTempPath(), "odyssey-planner");
    private static readonly string Exe = Path.Combine(Root, "Emu Dir", "emu.exe");
    private static readonly string Core = Path.Combine(Root, "cores", "genesis_plus_gx_libretro.dll");
    private static readonly string Rom = Path.Combine(Root, "ROMs", "megadrive", "Sonic & Knuckles (World).md");

    private static EmulatorConfig Emulator(string[] args, string workingDir = "{emulator_dir}", string? core = null, string id = "emu") =>
        new(id, "Emu", Exe, args, workingDir, core);

    private static string[] Expand(params string[] args) =>
        LaunchPlanner.Plan(Emulator(args, core: Core), "megadrive", Rom).Plan!.Arguments.ToArray();

    private static GameDetails Game(string? emulatorOverride = null) => new(
        new GameKey("megadrive", "sonic & knuckles (world).md"), 1, Path.GetDirectoryName(Rom)!, "Sonic & Knuckles (World).md", Rom,
        "Sonic & Knuckles", "World", null, null, null, null, 3, false, false, null, emulatorOverride);

    private static AppConfig Config()
    {
        var loaded = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = Root,
            ConfigDir = Root,
            FileExists = null,
            Emulators = new ConfigFile("emulators.toml", """
                [emulators.blastem]
                name = "BlastEm"
                executable = "C:/Emulators/BlastEm/blastem.exe"
                args = ["{rom}"]
                """),
        });
        Assert.False(loaded.HasErrors, string.Join('\n', loaded.Diagnostics));
        return loaded.Config;
    }

    [Fact]
    public void Each_placeholder_expands_to_its_rom_or_emulator_value()
    {
        var args = Expand("{rom}", "{rom_dir}", "{rom_file}", "{rom_stem}", "{system}", "{emulator}", "{emulator_dir}", "{core}");

        Assert.Equal(
            [Rom, Path.GetDirectoryName(Rom), "Sonic & Knuckles (World).md", "Sonic & Knuckles (World)", "megadrive", Exe, Path.GetDirectoryName(Exe), Core],
            args);
    }

    [Fact]
    public void Placeholders_can_sit_anywhere_inside_an_argument_and_each_entry_stays_one_argument()
    {
        Assert.Equal(["--rom=" + Rom, "-L", Core, "a b c"], Expand("--rom={rom}", "-L", "{core}", "a b c"));
    }

    [Fact]
    public void Expansion_is_single_pass_so_values_that_look_like_placeholders_stay_literal()
    {
        var rom = Path.Combine(Root, "{rom_dir} {core}.md");

        var plan = LaunchPlanner.Plan(Emulator(["{rom}", "{rom_stem}"], core: Core), "megadrive", rom).Plan!;

        Assert.Equal([rom, "{rom_dir} {core}"], plan.Arguments);
    }

    [Fact]
    public void Doubled_braces_are_literal_braces()
    {
        Assert.Equal(["{rom}", "}{", "x{" + Rom + "}"], Expand("{{rom}}", "}}{{", "x{{{rom}}}"));
    }

    [Fact]
    public void The_working_directory_is_a_template_too_and_defaults_to_the_emulator_folder()
    {
        Assert.Equal(Path.GetDirectoryName(Exe), LaunchPlanner.Plan(Emulator([]), "megadrive", Rom).Plan!.WorkingDirectory);
        Assert.Equal(Path.GetDirectoryName(Rom), LaunchPlanner.Plan(Emulator([], "{rom_dir}"), "megadrive", Rom).Plan!.WorkingDirectory);
    }

    [Fact]
    public void Core_without_a_core_and_unknown_placeholders_are_errors_naming_the_key()
    {
        var noCore = LaunchPlanner.Plan(Emulator(["-L", "{core}"]), "megadrive", Rom);
        var unknown = LaunchPlanner.Plan(Emulator(["{rom_name}"]), "megadrive", Rom);

        Assert.Equal("emulators.emu.args: {core} is used, but this profile has no core", noCore.Error);
        Assert.Equal("emulators.emu.args: unknown placeholder {rom_name}", unknown.Error);
    }

    [Fact]
    public void Title_id_expands_to_the_id_given_and_without_one_the_plan_says_where_to_put_it()
    {
        var emulator = Emulator(["-r", "{title_id}"]);

        Assert.Equal(["-r", "PCSF00024"], LaunchPlanner.Plan(emulator, "psvita", Rom, "PCSF00024").Plan!.Arguments);
        var none = LaunchPlanner.Plan(emulator, "psvita", Rom);
        Assert.Null(none.Plan);
        Assert.Equal($"No title id was found for '{Rom}', and Emu needs one to know which game to run. Put it in the file's name in " +
            "square brackets, as in 'Gravity Rush [PCSF00024].vpk'.", none.Error);
        Assert.Equal("emulators.emu.working_dir: {title_id} is used, but the game has no title id",
            LaunchPlanner.Plan(Emulator([], "{title_id}"), "psvita", Rom).Error);
    }

    [Fact]
    public void A_game_to_install_is_planned_with_the_install_args()
    {
        var emulator = Emulator(["-r", "{title_id}"]) with { Installs = "vita3k", InstallArgs = ["--install", "{rom}"] };

        Assert.Equal(["-r", "PCSF00024"], LaunchPlanner.Plan(emulator, "psvita", Rom, "PCSF00024").Plan!.Arguments);
        Assert.Equal(["--install", Rom], LaunchPlanner.Plan(emulator, "psvita", Rom, "PCSF00024", install: true).Plan!.Arguments);
        Assert.Equal(["--install", Rom], LaunchPlanner.Plan(emulator, "psvita", Rom, null, install: true).Plan!.Arguments);
        Assert.Equal("Emu has no install_args in emulators.toml, so a game that isn't installed in it can't be installed.",
            LaunchPlanner.Plan(emulator with { InstallArgs = null }, "psvita", Rom, null, install: true).Error);
    }

    [Fact]
    public void Uses_finds_a_placeholder_in_the_args_the_install_args_or_the_working_folder()
    {
        Assert.False(LaunchPlanner.Uses(Emulator(["{rom}", "{{title_id}}"]), "title_id"));
        Assert.True(LaunchPlanner.Uses(Emulator(["-r={title_id}"]), "title_id"));
        Assert.True(LaunchPlanner.Uses(Emulator([]) with { InstallArgs = ["{title_id}"] }, "title_id"));
        Assert.True(LaunchPlanner.Uses(Emulator([], "{rom_dir}/{title_id}"), "title_id"));
    }

    [Fact]
    public void An_argument_with_a_NUL_character_is_refused()
    {
        var plan = LaunchPlanner.Plan(Emulator(["a\0b"]), "megadrive", Rom);

        Assert.Equal("emulators.emu.args: an argument contains a NUL character", plan.Error);
    }

    [Fact]
    public void The_emulator_is_the_per_launch_choice_then_the_games_override_then_the_systems()
    {
        var config = Config();

        Assert.Equal("retroarch-genesis-plus-gx", LaunchPlanner.Plan(config, Game()).Plan!.EmulatorId);
        Assert.Equal("blastem", LaunchPlanner.Plan(config, Game("blastem")).Plan!.EmulatorId);
        Assert.Equal("retroarch-genesis-plus-gx", LaunchPlanner.Plan(config, Game("blastem"), "retroarch-genesis-plus-gx").Plan!.EmulatorId);
    }

    [Fact]
    public void The_built_in_RetroArch_profiles_pass_their_core_with_L()
    {
        var plan = LaunchPlanner.Plan(Config(), Game()).Plan!;

        Assert.Equal(Path.GetFullPath("C:/RetroArch-Win64/retroarch.exe"), plan.Executable);
        Assert.Equal(["-L", Path.GetFullPath("C:/RetroArch-Win64/cores/genesis_plus_gx_libretro.dll"), "--fullscreen", Rom], plan.Arguments);
        Assert.Equal(Path.GetFullPath("C:/RetroArch-Win64/cores/genesis_plus_gx_libretro.dll"), plan.Core);
    }

    [Theory]
    [InlineData("nope", null, "The emulator 'nope' was chosen for this launch, but it isn't configured")]
    [InlineData(null, "nope", "The emulator 'nope' is set for this game, but it isn't configured")]
    public void An_unknown_emulator_is_an_error_that_says_where_it_was_named(string? chosen, string? gameOverride, string expected)
    {
        var plan = LaunchPlanner.Plan(Config(), Game(gameOverride), chosen);

        Assert.Null(plan.Plan);
        Assert.StartsWith(expected, plan.Error, StringComparison.Ordinal);
    }

    [Fact]
    public void A_disabled_system_is_an_error()
    {
        var game = Game() with { Key = new GameKey("no-such-system", "x.a26") };

        Assert.Equal("The system 'no-such-system' isn't enabled in systems.toml.", LaunchPlanner.Plan(Config(), game).Error);
    }

    [Theory]
    [InlineData(0, "0")]
    [InlineData(3, "3")]
    [InlineData(unchecked((int)0xC0000005), "0xC0000005")]
    [InlineData(-1, "0xFFFFFFFF")]
    public void Exit_codes_that_are_NTSTATUS_values_are_shown_in_hex(int code, string expected)
    {
        Assert.Equal(expected, LaunchService.FormatExitCode(code));
    }
}
