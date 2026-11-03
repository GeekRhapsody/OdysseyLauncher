using Launcher.Core.Config;

namespace Launcher.Core.Tests.Config;

/// <summary>Where an emulator's program and core are looked for (A5 Finding programs), and the built-in Linux defaults.</summary>
public class EmulatorPlacesTests
{
    private static readonly string Home = Path.Combine(Path.GetTempPath(), "odyssey-home");
    private static readonly string ConfigDir = Path.Combine(Home, "config");

    /// <param name="linux">Linux's built-in defaults (its emulators, and its settings and systems over the shared ones), else Windows'.</param>
    private static ConfigLoadResult Load(
        string? settings = null, string? emulators = null, bool linux = false, Func<string, bool>? fileExists = null,
        Func<string, bool>? checkFor = null) =>
        new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = Home,
            ConfigDir = ConfigDir,
            Settings = settings is null ? null : new ConfigFile("user/settings.toml", settings),
            Emulators = emulators is null ? null : new ConfigFile("user/emulators.toml", emulators),
            DefaultEmulators = BuiltInDefaults.Read(linux ? BuiltInDefaults.LinuxEmulatorsFileName : BuiltInDefaults.WindowsEmulatorsFileName),
            PlatformSettings = linux ? BuiltInDefaults.Read(BuiltInDefaults.LinuxSettingsFileName) : null,
            PlatformSystems = linux ? BuiltInDefaults.Read(BuiltInDefaults.LinuxSystemsFileName) : null,
            FileExists = fileExists ?? (_ => true),
            CheckInstallsFor = checkFor,
        });

    private static string Full(string path) => Path.GetFullPath(path);

    // ---- The built-in Linux defaults -------------------------------------------------------------

    [Fact]
    public void The_Linux_defaults_load_without_any_diagnostics_and_keep_every_system()
    {
        var linux = Load(linux: true);

        Assert.Empty(linux.Diagnostics);
        Assert.Equal(
            Load().Config.Systems.Select(s => s.Id).Order(StringComparer.Ordinal),
            linux.Config.Systems.Select(s => s.Id).Order(StringComparer.Ordinal));
    }

    [Fact]
    public void On_Linux_every_system_offers_Linux_profiles_and_a_variant_its_systems()
    {
        var config = Load(linux: true).Config;

        foreach (var system in config.Systems)
        {
            Assert.Contains(system.Emulator, config.Emulators.Keys);
            Assert.All(system.AltEmulators, id => Assert.Contains(id, config.Emulators.Keys));
            if (system.Group is { } group && config.FindSystem(group) is { } parent)
            {
                Assert.Equal(parent.Emulator, system.Emulator);
                Assert.Equal(parent.AltEmulators, system.AltEmulators);
            }
        }

        // A profile with the same emulator has the same id and name on both, so systems.toml names it on either.
        var windows = Load().Config.Emulators;
        Assert.All(config.Emulators.Values.Where(e => windows.ContainsKey(e.Id)), e => Assert.Equal(windows[e.Id].Name, e.Name));
        Assert.Equal("eden", config.FindSystem("switch")!.Emulator);
        Assert.Equal([".desktop", ".sh"], config.FindSystem("steam")!.Extensions);
    }

    [Fact]
    public void A_Linux_RetroArch_profile_looks_where_the_retroarch_variables_list()
    {
        var gpgx = Load(linux: true).Config.Emulators["retroarch-genesis-plus-gx"];

        Assert.Equal("retroarch", gpgx.ProgramVariable);
        Assert.Equal("retroarch", gpgx.Executable);
        Assert.Contains(Full(Home + "/Applications/RetroArch-Linux*.AppImage"), gpgx.ProgramPlaces);
        Assert.Contains(Full("/var/lib/flatpak/exports/bin/org.libretro.RetroArch"), gpgx.ProgramPlaces);
        Assert.Equal(Full(Home + "/.config/retroarch/cores/genesis_plus_gx_libretro.so"), gpgx.Core);
        Assert.Contains(Full("/usr/lib/libretro/genesis_plus_gx_libretro.so"), gpgx.CorePlaces!);
        Assert.Equal(["-L", "{core}", "--fullscreen", "{rom}"], gpgx.Args);
    }

    // ---- Places ----------------------------------------------------------------------------------

    [Fact]
    public void An_executable_can_list_places_and_a_bare_name_is_kept_for_the_PATH()
    {
        var result = Load(emulators: """
            [emulators.x]
            name = "X"
            executable = ["x-emu", "bin/x-emu", "/opt/x/x-emu"]
            args = ["{rom}"]
            """);

        Assert.Empty(result.Diagnostics);
        var x = result.Config.Emulators["x"];
        Assert.Equal("x-emu", x.Executable);
        Assert.Equal(["x-emu", Full(Path.Combine(ConfigDir, "bin/x-emu")), Full("/opt/x/x-emu")], x.ProgramPlaces);
        Assert.Null(x.ProgramVariable);
        Assert.Equal("x-emu, or 2 more places", x.ProgramText);
    }

    [Fact]
    public void A_list_variable_gives_an_executable_or_core_one_place_for_each_item()
    {
        var result = Load(
            settings: """
                [variables]
                tools = ["{home}/a", "/b"]
                """,
            emulators: """
                [emulators.x]
                name = "X"
                executable = "{tools}/emu"
                core = "{tools}/core.so"
                args = ["-L", "{core}", "{rom}"]
                """);

        Assert.Empty(result.Diagnostics);
        var x = result.Config.Emulators["x"];
        Assert.Equal([Full(Home + "/a/emu"), Full("/b/emu")], x.ProgramPlaces);
        Assert.Equal([Full(Home + "/a/core.so"), Full("/b/core.so")], x.CorePlaces);
        Assert.Equal("tools", x.ProgramVariable);
        Assert.False(result.Config.Settings.Variables.ContainsKey("tools"));
    }

    [Fact]
    public void A_list_variable_is_an_error_anywhere_but_an_executable_or_a_core()
    {
        var result = Load(
            settings: """
                [variables]
                tools = ["/a", "/b"]
                more = ["/c"]
                other = "{tools}/x"
                """,
            emulators: """
                [emulators.x]
                name = "X"
                executable = "/x"
                args = ["{tools}"]

                [emulators.y]
                name = "Y"
                executable = "{tools}/{more}"
                args = ["{rom}"]

                [emulators.z]
                name = "Z"
                executable = []
                args = ["{rom}"]
                """);

        Assert.Contains(result.Diagnostics, d => d.Key == "variables.other" && d.Message.Contains("is a list of places", StringComparison.Ordinal));
        Assert.Contains(result.Diagnostics, d => d.Key == "emulators.x.args" && d.Message.Contains("is a list of places", StringComparison.Ordinal));
        Assert.Contains(result.Diagnostics, d => d.Key == "emulators.y.executable" && d.Message.Contains("uses two lists", StringComparison.Ordinal));
        Assert.Contains(result.Diagnostics, d => d.Key == "emulators.z.executable" && d.Message.Contains("no places", StringComparison.Ordinal));
        Assert.DoesNotContain("x", result.Config.Emulators.Keys);
        Assert.DoesNotContain("y", result.Config.Emulators.Keys);
        Assert.DoesNotContain("z", result.Config.Emulators.Keys);
    }

    [Fact]
    public void The_install_check_warns_only_when_no_place_has_the_program()
    {
        var gpgx = Load(linux: true).Config.Emulators["retroarch-genesis-plus-gx"];
        var program = gpgx.ProgramPlaces[^1];
        var core = gpgx.CorePlaces![^1];

        var nothing = Load(linux: true, fileExists: _ => false, checkFor: id => id == "megadrive");
        var missing = Assert.Single(nothing.Diagnostics, d => d.Key == "emulators.retroarch-genesis-plus-gx.executable");
        Assert.Contains($"isn't in any of its {gpgx.ProgramPlaces.Count} places ('retroarch', ", missing.Message, StringComparison.Ordinal);

        var installed = Load(linux: true, fileExists: p => p == program || p == core, checkFor: id => id == "megadrive");
        Assert.DoesNotContain(installed.Diagnostics, d => d.Key.StartsWith("emulators.retroarch-genesis-plus-gx.", StringComparison.Ordinal));
    }
}
