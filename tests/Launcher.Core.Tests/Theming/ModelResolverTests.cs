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
            .Model("card.glb", "label").Model("ps2.glb", "case"), Base, id: "active").Theme!;

    /// <summary>
    /// The base theme's part, with fixed templates: the real memory-card theme's assignments change as its models
    /// do, and these tests are about the resolution order, not its choices.
    /// </summary>
    private static Theme Base => ThemeFixtures.ParseBase("""
        format = 1
        name = "Built-in"

        [look.background]
        top_left = "#1B1F4A"
        top_right = "#1B1F4A"
        bottom_left = "#04040C"
        bottom_right = "#0B0B24"

        [look.ambient]
        colour = "#303038"

        [[look.lights]]
        direction = [-0.5, -0.4, -0.75]

        [defaults]
        system_model = "models/systems/generic.glb"
        tint_system_model = true
        game_template = "dvd_case"

        [templates.dvd_case]
        model = "models/templates/dvd_case.glb"

        [templates.jewel_case]
        model = "models/templates/jewel_case.glb"

        [templates.clamshell]
        model = "models/templates/clamshell.glb"

        [systems.ps2]
        colour = "#2A3A8C"
        game_template = "dvd_case"

        [systems.megadrive]
        colour = "#1F3E8C"
        game_template = "clamshell"
        """, new FakeThemeFiles().Model("models/systems/generic.glb", "label", "case")
            .Model("models/templates/dvd_case.glb", "cover", "back", "spine", "case")
            .Model("models/templates/jewel_case.glb", "cover", "back", "spine", "case")
            .Model("models/templates/clamshell.glb", "cover", "back", "spine", "case"));

    private static AppConfig Config(string systems = "") => new ConfigLoader().Load(new ConfigSources
    {
        HomeDir = "C:/home",
        ConfigDir = ConfigDir,
        Systems = new ConfigFile("systems.toml", systems),
        FileExists = null,
    }).Config;

    private static ModelResolver Resolver(Theme? active = null, UserModels? user = null, AppConfig? config = null)
    {
        var baseTheme = Base;
        return new ModelResolver(active ?? baseTheme, baseTheme, user ?? UserModels.None(ConfigDir), config ?? Config(), DataDir);
    }

    private static string Describe(IReadOnlyList<ModelCandidate> candidates) =>
        string.Join(" > ", candidates.Select(c => $"{c.Level}:{Path.GetFileName(c.Path)}"));

    [Fact]
    public void Games_use_the_user_template_then_game_model_then_the_theme_then_the_built_in_theme()
    {
        var user = new UserModels(ConfigDir, new HashSet<string> { "ps2" }, new HashSet<string>());
        var resolver = Resolver(Active, user, Config("[systems.ps2]\ngame_model = \"clamshell\"\n"));

        Assert.Equal(
            "User:ps2.glb > GameModelSetting:my_clamshell.glb > ThemeSystem:tall.glb > ThemeDefault:wide.glb > BaseSystem:dvd_case.glb",
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

        Assert.Equal("ThemeDefault:wide.glb > BaseSystem:clamshell.glb > BaseDefault:dvd_case.glb", Describe(resolver.GameTemplates("megadrive")));

        // A system neither theme knows (a user-defined one) falls through to the defaults.
        Assert.Equal("ThemeDefault:wide.glb > BaseDefault:dvd_case.glb", Describe(resolver.GameTemplates("madeupsystem")));
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
    public void A_theme_can_give_a_system_one_of_the_base_themes_templates_from_the_base_themes_folder()
    {
        var active = ThemeFixtures.Parse("""
            name = "Borrows"

            [defaults]
            game_template = "clamshell"

            [systems.snes]
            game_template = "jewel_case"
            """, baseTheme: Base, id: "borrows").Theme!;
        var resolver = Resolver(active);

        Assert.Equal("ThemeSystem:jewel_case.glb > ThemeDefault:clamshell.glb > BaseDefault:dvd_case.glb", Describe(resolver.GameTemplates("snes")));
        var first = resolver.GameTemplates("snes")[0];
        Assert.Equal(("memory-card", ThemeOrigin.BuiltIn), (first.Template!.ThemeId, first.Origin));
        Assert.Equal(Path.GetFullPath("C:/app/themes/memory-card/models/templates/jewel_case.glb"), first.Path);
        Assert.Equal("models/templates/jewel_case.glb", first.Template.Model);
    }

    [Fact]
    public void A_template_extending_the_bases_uses_the_bases_model_with_its_own_chains_and_is_a_separate_template()
    {
        var active = ThemeFixtures.Parse("""
            name = "Extends"

            [templates.dvd_case.slots]
            back = ["screenshot", "generated"]

            [systems.ps2]
            game_template = "dvd_case"
            """, baseTheme: Base, id: "extends").Theme!;
        var resolver = Resolver(active);

        var candidates = resolver.GameTemplates("ps2");
        Assert.Equal("ThemeSystem:dvd_case.glb > BaseSystem:dvd_case.glb", Describe(candidates));
        Assert.Equal(candidates[0].Path, candidates[1].Path);
        Assert.Equal((ThemeOrigin.BuiltIn, "extends", true), (candidates[0].Origin, candidates[0].Template!.ThemeId, candidates[0].Template!.ModelFromBase));
        Assert.NotEqual(candidates[0].Key, candidates[1].Key);
        Assert.Equal([SlotSource.Media(MediaSlots.Screenshot), SlotSource.Generated], candidates[0].ChainFor(MediaSlots.Back, systemCard: false).Sources);
        Assert.Equal(SlotChain.Default(MediaSlots.Back), candidates[1].ChainFor(MediaSlots.Back, systemCard: false));
    }

    [Fact]
    public void A_game_model_no_theme_defines_is_a_warning_naming_systems_toml_and_the_key()
    {
        var resolver = Resolver(Active, config: Config("[systems.snes]\ngame_model = \"tall_box\"\n"));

        var warning = Assert.Single(resolver.Diagnostics);
        Assert.Equal((Severity.Warning, Path.Combine(ConfigDir, "systems.toml"), "systems.snes.game_model"), (warning.Severity, warning.Source, warning.Key));
        Assert.Contains("no template 'tall_box' in the theme 'active' or the base theme", warning.Message, StringComparison.Ordinal);
        Assert.Equal(ModelLevel.ThemeDefault, resolver.GameTemplates("snes")[0].Level);
    }

    [Fact]
    public void A_games_chosen_template_is_the_active_themes_else_the_bases_and_shares_its_key_with_a_systems_use()
    {
        var extends = ThemeFixtures.Parse("""
            name = "Extends"

            [templates.dvd_case.slots]
            back = ["screenshot", "generated"]

            [templates.tall]
            model = "tall.glb"
            """, new FakeThemeFiles().Model("tall.glb", "cover"), Base, id: "extends").Theme!;
        var resolver = Resolver(extends);

        // Its own template, from its folder.
        var own = resolver.GameChoice("tall")!;
        Assert.Equal((ModelLevel.GameChoice, "extends", ThemeOrigin.User), (own.Level, own.Template!.ThemeId, own.Origin));
        Assert.Equal("tall.glb", Path.GetFileName(own.Path));

        // A base template it doesn't name, from the base's folder.
        var borrowed = resolver.GameChoice("jewel_case")!;
        Assert.Equal(("memory-card", ThemeOrigin.BuiltIn), (borrowed.Template!.ThemeId, borrowed.Origin));
        Assert.Equal(Path.GetFullPath("C:/app/themes/memory-card/models/templates/jewel_case.glb"), borrowed.Path);

        // Its extension of a base template: the base's model with its own chains.
        var extended = resolver.GameChoice("dvd_case")!;
        Assert.Equal(("extends", true), (extended.Template!.ThemeId, extended.Template.ModelFromBase));
        Assert.Equal([SlotSource.Media(MediaSlots.Screenshot), SlotSource.Generated], extended.ChainFor(MediaSlots.Back, systemCard: false).Sources);

        // The same template as a system's level is the same grid template, so the grid draws it without loading it again.
        Assert.Equal(Resolver().GameTemplates("ps2")[0].Key, Resolver().GameChoice("dvd_case")!.Key);

        // An id neither theme has: the game shows its system's.
        Assert.Null(resolver.GameChoice("no_such_box"));
    }

    [Fact]
    public void A_per_game_model_is_the_users_indexed_file()
    {
        var candidate = Resolver().PerGame("media/ps2/models/Sub/Game.glb");

        Assert.Equal((ModelLevel.UserGame, ThemeOrigin.User), (candidate.Level, candidate.Origin));
        Assert.Equal(Path.GetFullPath(Path.Combine(DataDir, "media", "ps2", "models", "Sub", "Game.glb")), candidate.Path);
        Assert.Equal(SlotChain.Default(MediaSlots.Back), candidate.ChainFor(MediaSlots.Back, systemCard: false));
    }

    [Fact]
    public void System_cards_use_the_users_model_then_the_theme_then_the_built_in_theme_with_their_tint()
    {
        var user = new UserModels(ConfigDir, new HashSet<string>(), new HashSet<string> { "psx" });
        var resolver = Resolver(Active, user);

        Assert.Equal("ThemeSystem:ps2.glb > ThemeDefault:card.glb > BaseDefault:generic.glb", Describe(resolver.SystemModels("ps2")));
        Assert.Equal([true, true, true], resolver.SystemModels("ps2").Select(c => c.Tint));
        Assert.Equal("User:psx.glb > ThemeDefault:card.glb > BaseDefault:generic.glb", Describe(resolver.SystemModels("psx")));
        Assert.Equal([false, false, true], resolver.SystemModels("psx").Select(c => c.Tint));

        // Favourites and Recently played have no system: the default cards.
        Assert.Equal("ThemeDefault:card.glb > BaseDefault:generic.glb", Describe(resolver.SystemModels(null)));
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
        Assert.Equal(ThemeFixtures.Base.Look.Background, resolver.LookFor(null).Background);
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

    /// <summary>A user theme whose default card shows each system's logo on its label, and PS2's on its cover too.</summary>
    private static Theme Logos => ThemeFixtures.Parse("""
        name = "Logos"

        [defaults]
        system_model = "card.glb"

        [defaults.system_slots]
        label = ["logo", "generated"]

        [systems.ps2]
        model = "ps2.glb"

        [systems.ps2.slots]
        cover = ["logo", "authored"]

        [systems.psx]
        logo = "art/psx.png"
        """, new FakeThemeFiles().Model("card.glb", "label", "case").Model("ps2.glb", "cover", "label", "case")
            .File("logos/ps2.png", "logos/favourites.png", "art/psx.png"), Base, id: "logos").Theme!;

    [Fact]
    public void A_cards_chains_are_its_themes_systems_over_its_defaults_and_the_users_card_takes_the_active_themes()
    {
        var user = new UserModels(ConfigDir, new HashSet<string>(), new HashSet<string> { "ps2" });
        var cards = Resolver(Logos, user).SystemModels("ps2");

        Assert.Equal("User:ps2.glb > ThemeSystem:ps2.glb > ThemeDefault:card.glb > BaseDefault:generic.glb", Describe(cards));
        var logoThenGenerated = new[] { SlotSource.Media(MediaSlots.Logo), SlotSource.Generated };
        var logoThenAuthored = new[] { SlotSource.Media(MediaSlots.Logo), SlotSource.Authored };
        foreach (var card in cards.Take(3))
        {
            Assert.Equal(logoThenGenerated, card.ChainFor(MediaSlots.Label, systemCard: true).Sources);
            Assert.Equal(logoThenAuthored, card.ChainFor(MediaSlots.Cover, systemCard: true).Sources);
        }

        // The base theme's card keeps its own chains: the base names none.
        Assert.Equal(SlotChain.ForSystemModel(MediaSlots.Label), cards[3].ChainFor(MediaSlots.Label, systemCard: true));

        // A game's template never takes a card's chains.
        Assert.Equal(SlotChain.Default(MediaSlots.Cover), cards[2].ChainFor(MediaSlots.Cover, systemCard: false));
    }

    [Fact]
    public void Cards_that_share_a_model_but_not_its_chains_are_different_grid_templates()
    {
        var resolver = Resolver(Logos);
        var megadrive = resolver.SystemModels("megadrive")[0];
        var psx = resolver.SystemModels("psx")[0];
        var plain = Resolver(Active).SystemModels("megadrive")[0];

        // Same file, same chains: one template.
        Assert.Equal(megadrive.Key, psx.Key);

        // A system with chains of its own on the same default card: another template.
        var withOwn = new ModelCandidate(megadrive.Level, megadrive.Origin, megadrive.Path, null, megadrive.Tint, "", resolver.Active.Systems["ps2"].Slots);
        Assert.NotEqual(megadrive.Key, withOwn.Key);

        // A card without chains keeps the key it always had.
        Assert.Equal($"{plain.Path}|:|plain", plain.Key);
    }

    [Fact]
    public void A_cards_logo_is_the_active_themes_then_the_base_themes()
    {
        var logos = Logos;
        var resolver = Resolver(logos);

        Assert.Equal(new LogoFile("logos", "logos/ps2.png", logos.PathOf("logos/ps2.png")), resolver.LogoOf("ps2"));
        Assert.Equal(logos.PathOf("art/psx.png"), resolver.LogoOf("psx")!.Path);
        Assert.Equal(logos.PathOf("logos/favourites.png"), resolver.LogoOf("favourites")!.Path);
        Assert.Null(resolver.LogoOf("megadrive"));

        // Named by the theme and the path in it, wherever the theme's folder is (an editor run's or an export's).
        Assert.Equal("logos/logos/ps2.png", resolver.LogoOf("ps2")!.Key);

        // The base theme's logos stand in for the active theme's.
        var withBaseLogo = ThemeFixtures.ParseBase("""
            format = 1
            name = "Built-in"

            [look.background]
            top_left = "#1B1F4A"
            top_right = "#1B1F4A"
            bottom_left = "#04040C"
            bottom_right = "#0B0B24"

            [look.ambient]
            colour = "#303038"

            [[look.lights]]
            direction = [-0.5, -0.4, -0.75]
            """, new FakeThemeFiles().File("logos/megadrive.webp"));
        var layered = new ModelResolver(logos, withBaseLogo, UserModels.None(ConfigDir), Config(), DataDir);
        Assert.Equal(new LogoFile(ThemeCatalog.BaseId, "logos/megadrive.webp", withBaseLogo.PathOf("logos/megadrive.webp")), layered.LogoOf("megadrive"));
        Assert.Equal(logos.PathOf("logos/ps2.png"), layered.LogoOf("ps2")!.Path);
    }
}
