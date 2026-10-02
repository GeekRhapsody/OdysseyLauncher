using Launcher.Core.Config;
using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

public sealed class ModelResolverTests
{
    private const string ConfigDir = "C:/config";
    private const string DataDir = "C:/data";

    /// <summary>A user theme with a template for PS2, a default template, and a card model for PS2.</summary>
    private static Theme Active => ThemeFixtures.Parse("""
        name = "Active"

        [defaults]
        game_template = "wide"
        system_model = "card.glb"

        [templates.tall]
        model = "tall.glb"

        [templates.wide]
        model = "wide.glb"

        [templates.clamshell]
        model = "my_clamshell.glb"

        [systems.ps2]
        game_template = "tall"
        model = "ps2.glb"
        tint = true
        colour = "#102030"
        """, new FakeThemeFiles().Model("tall.glb", "cover").Model("wide.glb", "cover").Model("my_clamshell.glb", "cover")
            .Model("card.glb", "label").Model("ps2.glb", "case"), id: "active").Theme!;

    private static AppConfig Config(string systems = "") => new ConfigLoader().Load(new ConfigSources
    {
        HomeDir = "C:/home",
        ConfigDir = ConfigDir,
        Systems = new ConfigFile("systems.toml", systems),
        FileExists = null,
    }).Config;

    private static ModelResolver Resolver(Theme? active = null, UserModels? user = null, AppConfig? config = null)
    {
        var builtIn = ThemeFixtures.BuiltIn;
        return new ModelResolver(active ?? builtIn, builtIn, user ?? UserModels.None(ConfigDir), config ?? Config(), DataDir);
    }

    private static string Describe(IReadOnlyList<ModelCandidate> candidates) =>
        string.Join(" > ", candidates.Select(c => $"{c.Level}:{Path.GetFileName(c.Path)}"));

    [Fact]
    public void Games_use_the_user_template_then_game_model_then_the_theme_then_the_built_in_theme()
    {
        var user = new UserModels(ConfigDir, new HashSet<string> { "ps2" }, new HashSet<string>());
        var resolver = Resolver(Active, user, Config("[systems.ps2]\ngame_model = \"clamshell\"\n"));

        Assert.Equal(
            "User:ps2.glb > GameModelSetting:my_clamshell.glb > ThemeSystem:tall.glb > ThemeDefault:wide.glb > BuiltInSystem:dvd_case.glb",
            Describe(resolver.GameTemplates("ps2")));
        Assert.Empty(resolver.Diagnostics);

        // The built-in default (dvd_case) was already listed for PS2, so it isn't repeated.
        var ps2 = resolver.GameTemplates("ps2");
        Assert.Equal(Path.Combine(ConfigDir, "models", "templates", "ps2.glb"), ps2[0].Path);
        Assert.Equal((ThemeOrigin.User, (GameTemplate?)null), (ps2[0].Origin, ps2[0].Template));
        Assert.Equal(("tall", ThemeOrigin.User), (ps2[2].Template!.Id, ps2[2].Origin));
        Assert.Equal(ThemeOrigin.BuiltIn, ps2[4].Origin);
    }

    [Fact]
    public void A_system_the_active_theme_doesnt_list_gets_its_default_then_the_built_in_choice()
    {
        var resolver = Resolver(Active);

        Assert.Equal("ThemeDefault:wide.glb > BuiltInSystem:clamshell.glb > BuiltInDefault:dvd_case.glb", Describe(resolver.GameTemplates("megadrive")));

        // A system neither theme knows (a user-defined one) falls through to the defaults.
        Assert.Equal("ThemeDefault:wide.glb > BuiltInDefault:dvd_case.glb", Describe(resolver.GameTemplates("madeupsystem")));
    }

    [Fact]
    public void With_the_built_in_theme_active_its_levels_come_once()
    {
        var resolver = Resolver();

        Assert.Equal("ThemeSystem:clamshell.glb > ThemeDefault:dvd_case.glb", Describe(resolver.GameTemplates("megadrive")));
        Assert.Equal("ThemeSystem:dvd_case.glb", Describe(resolver.GameTemplates("ps2")));
    }

    [Fact]
    public void Game_model_can_name_a_built_in_template_while_another_theme_is_active()
    {
        var resolver = Resolver(Active, config: Config("[systems.snes]\ngame_model = \"jewel_case\"\n"));

        var first = resolver.GameTemplates("snes")[0];
        Assert.Equal((ModelLevel.GameModelSetting, "jewel_case", ThemeOrigin.BuiltIn), (first.Level, first.Template!.Id, first.Origin));
    }

    [Fact]
    public void A_game_model_no_theme_defines_is_a_warning_naming_systems_toml_and_the_key()
    {
        var resolver = Resolver(Active, config: Config("[systems.snes]\ngame_model = \"tall_box\"\n"));

        var warning = Assert.Single(resolver.Diagnostics);
        Assert.Equal((Severity.Warning, Path.Combine(ConfigDir, "systems.toml"), "systems.snes.game_model"), (warning.Severity, warning.Source, warning.Key));
        Assert.Contains("no template 'tall_box' in the theme 'active' or the built-in theme", warning.Message, StringComparison.Ordinal);
        Assert.Equal(ModelLevel.ThemeDefault, resolver.GameTemplates("snes")[0].Level);
    }

    [Fact]
    public void A_per_game_model_is_the_users_indexed_file()
    {
        var candidate = Resolver().PerGame("media/ps2/model/Sub/Game.glb");

        Assert.Equal((ModelLevel.UserGame, ThemeOrigin.User), (candidate.Level, candidate.Origin));
        Assert.Equal(Path.GetFullPath(Path.Combine(DataDir, "media", "ps2", "model", "Sub", "Game.glb")), candidate.Path);
        Assert.Equal(SlotChain.Default(MediaSlots.Back), candidate.ChainFor(MediaSlots.Back, systemCard: false));
    }

    [Fact]
    public void System_cards_use_the_users_model_then_the_theme_then_the_built_in_theme_with_their_tint()
    {
        var user = new UserModels(ConfigDir, new HashSet<string>(), new HashSet<string> { "psx" });
        var resolver = Resolver(Active, user);

        Assert.Equal("ThemeSystem:ps2.glb > ThemeDefault:card.glb > BuiltInDefault:generic.glb", Describe(resolver.SystemModels("ps2")));
        Assert.Equal([true, true, true], resolver.SystemModels("ps2").Select(c => c.Tint));
        Assert.Equal("User:psx.glb > ThemeDefault:card.glb > BuiltInDefault:generic.glb", Describe(resolver.SystemModels("psx")));
        Assert.Equal([false, false, true], resolver.SystemModels("psx").Select(c => c.Tint));

        // Favourites and Recently played have no system: the default cards.
        Assert.Equal("ThemeDefault:card.glb > BuiltInDefault:generic.glb", Describe(resolver.SystemModels(null)));
    }

    [Fact]
    public void Colours_and_looks_come_from_the_active_theme_and_colours_fall_back_to_the_built_in_theme()
    {
        var active = Active;
        var resolver = Resolver(active);

        Assert.Equal("#102030", resolver.ColourOf("ps2").ToString());
        Assert.Equal("#1F3E8C", resolver.ColourOf("megadrive").ToString());
        Assert.Null(resolver.ColourOf("madeupsystem"));
        Assert.Same(active.Look, resolver.LookFor("megadrive"));
        Assert.Equal(ThemeFixtures.BuiltIn.Look.Background, resolver.LookFor(null).Background);
    }

    [Fact]
    public void Candidates_carry_their_slot_chains()
    {
        var showcase = ThemeFixtures.Load(ThemeFixtures.SlotShowcaseFolder);
        var candidate = Resolver(showcase).GameTemplates("ps2")[0];

        Assert.Equal("showcase_case", candidate.Template!.Id);
        Assert.Equal([SlotSource.Media(MediaSlots.Screenshot), SlotSource.Media(MediaSlots.Hero), SlotSource.Authored],
            candidate.ChainFor(MediaSlots.Screenshot, systemCard: false).Sources);
        Assert.Equal(SlotChain.ForSystemModel(MediaSlots.Label), candidate.ChainFor(MediaSlots.Label, systemCard: true));
    }
}
