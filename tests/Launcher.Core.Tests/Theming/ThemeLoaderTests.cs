using Launcher.Core.Config;
using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

public sealed class ThemeLoaderTests
{
    private const string MinimalTemplate = """
        format = 1
        name = "Test"

        [templates.box]
        model = "box.glb"
        """;

    private static FakeThemeFiles Box(params string[] materials) =>
        new FakeThemeFiles().Model("box.glb", materials.Length == 0 ? ["cover", "back", "spine", "case"] : materials);

    private static Diagnostic Single(ThemeLoadResult result, Severity severity) =>
        Assert.Single(result.Diagnostics, d => d.Severity == severity);

    // ---- The committed themes -------------------------------------------------------------------

    [Fact]
    public void The_built_in_theme_loads_cleanly_with_a_look_and_colour_for_every_built_in_system_and_only_templates_it_has()
    {
        var result = ThemeFixtures.LoadResult(ThemeFixtures.BaseFolder);

        Assert.Empty(result.Diagnostics);
        var theme = result.Theme!;
        Assert.Equal(("memory-card", "Memory Card", ThemeOrigin.BuiltIn), (theme.Id, theme.Name, theme.Origin));
        // Which template each system gets (its own, or the default) is the theme's to change as its models do, so only
        // that the templates named exist is checked.
        Assert.Equal(("models/systems/generic.glb", true), (theme.Defaults.SystemModel, theme.Defaults.TintSystemModel));
        Assert.Contains(Assert.IsType<string>(theme.Defaults.GameTemplate), theme.Templates);

        // The look of A6, exactly.
        Assert.Equal("#1B1F4A", theme.Look.Background.TopLeft.ToString());
        Assert.Equal("#0B0B24", theme.Look.Background.BottomRight.ToString());
        Assert.Equal(3, theme.Look.Lights.Count);

        var config = new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/home", ConfigDir = "C:/config", FileExists = null }).Config;
        foreach (var (system, index) in config.Systems.Select((s, i) => (s, i)))
        {
            var entry = Assert.Contains(system.Id, theme.Systems);
            Assert.NotNull(entry.Colour);
            if (entry.GameTemplate is { } template)
            {
                Assert.Contains(template, theme.Templates);
            }

            Assert.Same(theme.Look.Ambient, entry.Look.Ambient);

            // The first fourteen have a look of their own; the rest of the catalogue shows the theme's.
            if (index < 14)
            {
                Assert.NotSame(theme.Look.Background, entry.Look.Background);
            }
        }
    }

    [Fact]
    public void The_test_theme_loads_cleanly_with_three_slot_chains()
    {
        var result = ThemeFixtures.LoadResult(ThemeFixtures.SlotShowcaseFolder);

        Assert.Empty(result.Diagnostics);
        var template = result.Theme!.Templates["showcase_case"];
        Assert.Equal("cover = [\"cover\", \"generated\"]", template.ChainFor(MediaSlots.Cover).ToString());
        Assert.Equal("spine = [\"spine\", \"logo\", \"generated\"]", template.ChainFor(MediaSlots.Spine).ToString());
        Assert.Equal("screenshot = [\"screenshot\", \"hero\", \"authored\"]", template.ChainFor(MediaSlots.Screenshot).ToString());
        Assert.Equal(2, result.Theme.Look.Lights.Count);
    }

    // ---- Manifest errors name the file, line and key ----------------------------------------------

    [Fact]
    public void A_syntax_error_rejects_the_whole_theme_with_its_position()
    {
        var result = ThemeFixtures.Parse("name = \"Test\"\n[look\n");

        Assert.Null(result.Theme);
        var error = Assert.Single(result.Diagnostics);
        Assert.Equal(("user/themes/test/theme.toml", 2), (error.Source, error.Line));
        Assert.Contains("TOML syntax error", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void An_unsupported_format_rejects_the_theme()
    {
        var result = ThemeFixtures.Parse("format = 2\nname = \"Test\"\n");

        Assert.Null(result.Theme);
        Assert.Equal("format", Single(result, Severity.Error).Key);
    }

    [Fact]
    public void Unknown_keys_are_warnings_with_a_suggestion()
    {
        var result = ThemeFixtures.Parse("""
            name = "Test"
            look_transiton_ms = 200

            [look.background]
            top_lft = "#000000"
            top_left = "#000000"
            top_right = "#000000"
            bottom_left = "#000000"
            bottom_right = "#000000"
            """);

        Assert.NotNull(result.Theme);
        var warnings = result.Diagnostics.Where(d => d.Severity == Severity.Warning).ToList();
        Assert.Equal(["look_transiton_ms", "look.background.top_lft"], warnings.Select(w => w.Key));
        Assert.Contains("did you mean 'look_transition_ms'?", warnings[0].Message, StringComparison.Ordinal);
        Assert.Equal((5, 1), (warnings[1].Line, warnings[1].Column));
    }

    [Fact]
    public void A_bad_colour_is_an_error_at_its_key_and_the_block_falls_back_to_the_built_in_look()
    {
        var result = ThemeFixtures.Parse("""
            name = "Test"

            [look.background]
            top_left = "#12345"
            top_right = "#000000"
            bottom_left = "#000000"
            bottom_right = "#000000"
            """);

        var error = Single(result, Severity.Error);
        Assert.Equal(("look.background.top_left", 4), (error.Key, error.Line));
        Assert.Contains("'#12345' isn't a colour", error.Message, StringComparison.Ordinal);
        Assert.Equal(ThemeFixtures.Base.Look.Background, result.Theme!.Look.Background);
    }

    [Fact]
    public void A_look_needs_one_to_three_lights_each_with_a_direction()
    {
        var four = ThemeFixtures.Parse("""
            name = "Test"
            [[look.lights]]
            direction = [0, 0, -1]
            [[look.lights]]
            direction = [0, 0, -1]
            [[look.lights]]
            direction = [0, 0, -1]
            [[look.lights]]
            direction = [0, 0, -1]
            """);
        Assert.Contains("1 to 3 directional lights", Single(four, Severity.Error).Message, StringComparison.Ordinal);
        Assert.Equal(3, four.Theme!.Look.Lights.Count);

        var zero = ThemeFixtures.Parse("""
            name = "Test"
            [[look.lights]]
            direction = [0, 0, 0]
            colour = "#FFFFFF"
            """);
        var error = Single(zero, Severity.Error);
        Assert.Equal(("look.lights[0].direction", 3), (error.Key, error.Line));

        var one = ThemeFixtures.Parse("""
            name = "Test"
            [[look.lights]]
            direction = [0.5, -1, -0.25]
            energy = 2
            """);
        Assert.Empty(one.Diagnostics);
        var light = Assert.Single(one.Theme!.Look.Lights);
        Assert.Equal((new LightDirection(0.5f, -1, -0.25f), "#FFFFFF", 2f), (light.Direction, light.Colour.ToString(), light.Energy));
    }

    [Fact]
    public void The_built_in_theme_itself_must_have_a_complete_look()
    {
        var result = ThemeLoader.Load(
            new ThemeSource("memory-card", new ConfigFile("built-in/theme.toml", "name = \"Broken\"\n"), ThemeOrigin.BuiltIn, "C:/app/themes/memory-card", new FakeThemeFiles()),
            baseTheme: null);

        Assert.Null(result.Theme);
        Assert.Equal("look", Single(result, Severity.Error).Key);
    }

    [Fact]
    public void A_system_look_block_replaces_the_theme_block_whole_and_the_rest_is_inherited()
    {
        var result = ThemeFixtures.Parse("""
            name = "Test"

            [look.ambient]
            colour = "#101010"

            [systems.saturn.look.background]
            top_left = "#2A1A3A"
            top_right = "#2A1A3A"
            bottom_left = "#050008"
            bottom_right = "#100818"
            """);

        Assert.Empty(result.Diagnostics);
        var theme = result.Theme!;
        var saturn = theme.LookFor("saturn");
        Assert.Equal("#2A1A3A", saturn.Background.TopLeft.ToString());
        Assert.Same(theme.Look.Ambient, saturn.Ambient);
        Assert.Equal("#101010", saturn.Ambient.Colour.ToString());
        Assert.Same(theme.Look.Lights, saturn.Lights);
        Assert.Same(theme.Look, theme.LookFor("psx"));
        Assert.Same(theme.Look, theme.LookFor(null));
    }

    // ---- Templates and slot chains -----------------------------------------------------------------

    [Fact]
    public void A_template_whose_model_is_missing_is_left_out_and_references_to_it_are_errors()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [systems.ps2]
            game_template = "box"
            """, new FakeThemeFiles());

        var errors = result.Diagnostics.Where(d => d.IsError).ToList();
        Assert.Equal(["templates.box.model", "systems.ps2.game_template"], errors.Select(e => e.Key));
        Assert.Contains("'box.glb' doesn't exist in the theme's folder", errors[0].Message, StringComparison.Ordinal);
        Assert.Equal(5, errors[0].Line);
        Assert.Empty(result.Theme!.Templates);
        Assert.Null(result.Theme.Systems["ps2"].GameTemplate);
    }

    [Theory]
    [InlineData("../box.glb", "must be a path inside the theme's folder")]
    [InlineData("C:/models/box.glb", "must be a path inside the theme's folder")]
    [InlineData("box.gltf", "isn't a .glb")]
    public void A_model_path_must_be_a_glb_inside_the_theme(string path, string message)
    {
        var result = ThemeFixtures.Parse($"name = \"Test\"\n[templates.box]\nmodel = \"{path}\"\n", Box());

        var error = Single(result, Severity.Error);
        Assert.Equal("templates.box.model", error.Key);
        Assert.Contains(message, error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_game_template_needs_no_cover_material()
    {
        // M6 part 2: a CRT showing the screenshot, or a model with no slot at all, is a valid template.
        var withoutCover = ThemeFixtures.Parse(MinimalTemplate, Box("screenshot", "case"));
        var withoutSlots = ThemeFixtures.Parse(MinimalTemplate, Box("case"));

        Assert.Empty(withoutCover.Diagnostics);
        Assert.Empty(withoutSlots.Diagnostics);
        Assert.True(withoutCover.Theme!.Templates.ContainsKey("box"));
        Assert.True(withoutSlots.Theme!.Templates.ContainsKey("box"));
    }

    [Fact]
    public void Slot_materials_match_ignoring_case_and_a_Blender_suffix()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate, Box("Cover.001", "SPINE", "case"));

        Assert.Empty(result.Diagnostics);
        Assert.Equal((MediaSlots.Cover, MediaSlots.Spine, -1, -1), (MediaSlots.OfMaterial("Cover.001"), MediaSlots.OfMaterial("SPINE"), MediaSlots.OfMaterial("case"), MediaSlots.OfMaterial("cover.1")));
    }

    [Fact]
    public void Slot_chains_are_read_in_order_and_unlisted_slots_use_the_default_chain()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [templates.box.slots]
            back = ["back", "screenshot", "generated"]
            """, Box());

        Assert.Empty(result.Diagnostics);
        var template = result.Theme!.Templates["box"];
        Assert.Equal(
            [SlotSource.Media(MediaSlots.Back), SlotSource.Media(MediaSlots.Screenshot), SlotSource.Generated],
            template.ChainFor(MediaSlots.Back).Sources);
        Assert.Equal([SlotSource.Media(MediaSlots.Spine), SlotSource.Generated], template.ChainFor(MediaSlots.Spine).Sources);
        Assert.Equal([SlotSource.Media(MediaSlots.Screenshot)], template.ChainFor(MediaSlots.Screenshot).Sources);
    }

    [Fact]
    public void Slot_chain_mistakes_are_reported_at_the_slot_key()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [templates.box.slots]
            screenshots = ["screenshot"]
            spine = ["spine", "genrated"]
            screenshot = ["screenshot", "generated"]
            back = ["back", "authored", "screenshot"]
            cover = ["cover", "cover"]
            """, Box("cover", "back", "spine", "screenshot", "case"));

        var errors = result.Diagnostics.Where(d => d.IsError).ToList();
        Assert.Equal(["templates.box.slots.screenshots", "templates.box.slots.spine", "templates.box.slots.screenshot"], errors.Select(e => e.Key));
        Assert.Contains("did you mean 'screenshot'?", errors[0].Message, StringComparison.Ordinal);
        Assert.Contains("did you mean 'generated'?", errors[1].Message, StringComparison.Ordinal);
        Assert.Contains("can't draw a screenshot", errors[2].Message, StringComparison.Ordinal);
        Assert.Equal([7, 8, 9], errors.Select(e => e.Line));

        var warnings = result.Diagnostics.Where(d => d.Severity == Severity.Warning).ToList();
        Assert.Equal(["templates.box.slots.back", "templates.box.slots.cover"], warnings.Select(w => w.Key));
        Assert.Contains("never used", warnings[0].Message, StringComparison.Ordinal);
        Assert.Contains("listed twice", warnings[1].Message, StringComparison.Ordinal);

        // The template stays, with the valid chains; the bad ones fall back to the defaults.
        var template = result.Theme!.Templates["box"];
        Assert.Equal([SlotSource.Media(MediaSlots.Back), SlotSource.Authored], template.ChainFor(MediaSlots.Back).Sources);
        Assert.Equal(SlotChain.Default(MediaSlots.Spine), template.ChainFor(MediaSlots.Spine));
    }

    [Fact]
    public void A_chain_for_a_slot_the_model_doesnt_have_is_a_warning()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [templates.box.slots]
            screenshot = ["screenshot"]
            """, Box("cover", "case"));

        var warning = Single(result, Severity.Warning);
        Assert.Equal("templates.box.slots.screenshot", warning.Key);
        Assert.Contains("has no 'screenshot' material", warning.Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("", false)]
    [InlineData("\nshape = \"model\"", false)]
    [InlineData("\nshape = \"media\"", true)]
    public void A_template_takes_its_shape_from_the_model_unless_it_says_media(string shape, bool fromMedia)
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + shape, Box());

        Assert.Empty(result.Diagnostics);
        Assert.Equal(fromMedia, result.Theme!.Templates["box"].ShapeFromMedia);
    }

    [Fact]
    public void A_bad_shape_is_an_error_at_its_key_and_the_template_keeps_its_own_shape()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + "\nshape = \"meda\"", Box());

        var error = Single(result, Severity.Error);
        Assert.Equal(("templates.box.shape", 6), (error.Key, error.Line));
        Assert.Contains("did you mean 'media'?", error.Message, StringComparison.Ordinal);
        Assert.False(result.Theme!.Templates["box"].ShapeFromMedia);
    }

    [Fact]
    public void A_template_draws_a_slot_whole_only_where_its_fit_says_so()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [templates.box.fit]
            screenshot = "whole"
            cover = "crop"
            """, Box("cover", "screenshot", "case"));

        Assert.Empty(result.Diagnostics);
        var template = result.Theme!.Templates["box"];
        Assert.True(template.ShowsWhole(MediaSlots.Screenshot));
        Assert.False(template.ShowsWhole(MediaSlots.Cover));
        Assert.False(template.ShowsWhole(MediaSlots.Back));
        Assert.False(ThemeFixtures.Parse(MinimalTemplate, Box()).Theme!.Templates["box"].ShowsWhole(MediaSlots.Cover));
    }

    [Fact]
    public void A_bad_fit_is_an_error_at_its_key_and_the_slot_stays_cropped()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [templates.box.fit]
            cover = "hole"
            screnshot = "whole"
            """, Box());

        Assert.Equal(2, result.Diagnostics.Count(d => d.Severity == Severity.Error));
        var fit = Assert.Single(result.Diagnostics, d => d.Key == "templates.box.fit.cover");
        Assert.Contains("did you mean 'whole'?", fit.Message, StringComparison.Ordinal);
        var slot = Assert.Single(result.Diagnostics, d => d.Key == "templates.box.fit.screnshot");
        Assert.Contains("did you mean 'screenshot'?", slot.Message, StringComparison.Ordinal);
        Assert.False(result.Theme!.Templates["box"].ShowsWhole(MediaSlots.Cover));
    }

    [Fact]
    public void A_fit_for_a_slot_the_model_doesnt_have_is_a_warning()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [templates.box.fit]
            screenshot = "whole"
            """, Box("cover", "case"));

        var warning = Single(result, Severity.Warning);
        Assert.Equal("templates.box.fit.screenshot", warning.Key);
        Assert.Contains("has no 'screenshot' material", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_models_path_as_a_game_template_says_how_to_declare_the_template()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [systems.dos]
            game_template = "models/games/big_box.glb"
            """, Box());

        var error = Single(result, Severity.Error);
        Assert.Equal("systems.dos.game_template", error.Key);
        Assert.Contains("[templates.big_box] and model = \"models/games/big_box.glb\"", error.Message, StringComparison.Ordinal);
        Assert.Contains("game_template = \"big_box\"", error.Message, StringComparison.Ordinal);
        Assert.Null(result.Theme!.Systems["dos"].GameTemplate);
    }

    [Fact]
    public void A_shape_from_media_needs_a_cover_material()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + "\nshape = \"media\"", Box("screenshot", "case"));

        var warning = Single(result, Severity.Warning);
        Assert.Equal("templates.box.shape", warning.Key);
        Assert.Contains("has no 'cover' material", warning.Message, StringComparison.Ordinal);
        Assert.False(result.Theme!.Templates["box"].ShapeFromMedia);
    }

    [Fact]
    public void Defaults_and_systems_name_templates_and_models_in_the_theme()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [defaults]
            system_model = "card.glb"
            tint_system_model = true
            game_template = "boxx"

            [systems.ps2]
            model = "ps2.glb"
            tint = false
            colour = "#1F3A7A"
            game_template = "box"
            """, Box().Model("card.glb", "label", "case").Model("ps2.glb", "case"));

        var error = Single(result, Severity.Error);
        Assert.Equal("defaults.game_template", error.Key);
        Assert.Contains("did you mean 'box'?", error.Message, StringComparison.Ordinal);
        var theme = result.Theme!;
        Assert.Equal(("card.glb", true, (string?)null), (theme.Defaults.SystemModel, theme.Defaults.TintSystemModel, theme.Defaults.GameTemplate));
        Assert.Equal(new ThemeSystem("ps2", "ps2.glb", false, "box", new Rgb(0x1F, 0x3A, 0x7A), theme.Look), theme.Systems["ps2"]);
    }

    [Fact]
    public void Theme_paths_resolve_inside_the_theme_folder()
    {
        var baseTheme = ThemeFixtures.Base;
        var template = baseTheme.Templates[baseTheme.Defaults.GameTemplate!];
        Assert.Equal(Path.Combine(ThemeFixtures.BaseFolder, template.Model.Replace('/', Path.DirectorySeparatorChar)), baseTheme.PathOf(template.Model));
        Assert.True(File.Exists(baseTheme.PathOf(template.Model)));

        var user = ThemeFixtures.Load(ThemeFixtures.SlotShowcaseFolder);
        Assert.Equal(
            Path.Combine(ThemeFixtures.SlotShowcaseFolder, "models", "templates", "showcase_case.glb"),
            user.PathOf(user.Templates["showcase_case"].Model));
        Assert.True(File.Exists(user.PathOf(user.Templates["showcase_case"].Model)));
    }

    // ---- What a theme leaves out is the base theme's ------------------------------------------------

    /// <summary>
    /// A stand-in base theme: a box shaped by its art whose back shows a screenshot and whose cover is drawn whole, and
    /// a slower cross-fade.
    /// </summary>
    private static Theme InlineBase => ThemeFixtures.ParseBase("""
        format = 1
        name = "Base"
        look_transition_ms = 750

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
        game_template = "box"

        [templates.box]
        model = "models/box.glb"
        shape = "media"

        [templates.box.slots]
        back = ["screenshot", "generated"]

        [templates.box.fit]
        cover = "whole"

        [templates.jewel_case]
        model = "models/jewel_case.glb"
        """, new FakeThemeFiles().Model("models/box.glb", "cover", "back", "spine", "case").Model("models/jewel_case.glb", "cover", "case"));

    [Fact]
    public void A_theme_can_name_the_base_themes_templates()
    {
        var result = ThemeFixtures.Parse("""
            name = "Borrows"

            [defaults]
            game_template = "jewel_case"

            [systems.snes]
            game_template = "box"
            """, baseTheme: InlineBase);

        Assert.Empty(result.Diagnostics);
        var theme = result.Theme!;
        Assert.Equal("jewel_case", theme.Defaults.GameTemplate);
        Assert.Equal("box", theme.Systems["snes"].GameTemplate);

        // They stay the base's: nothing is copied into the theme.
        Assert.Empty(theme.Templates);
    }

    [Fact]
    public void A_template_id_neither_theme_has_is_an_error_suggesting_from_both()
    {
        var result = ThemeFixtures.Parse("""
            name = "Typo"

            [systems.snes]
            game_template = "jewel_cas"
            """, baseTheme: InlineBase);

        var error = Single(result, Severity.Error);
        Assert.Equal("systems.snes.game_template", error.Key);
        Assert.Contains("no template 'jewel_cas' in this theme or the base theme (did you mean 'jewel_case'?)", error.Message, StringComparison.Ordinal);
        Assert.Null(result.Theme!.Systems["snes"].GameTemplate);
    }

    [Fact]
    public void A_template_with_a_base_templates_id_extends_it_key_by_key()
    {
        var result = ThemeFixtures.Parse("""
            name = "Extends"

            [templates.box.slots]
            spine = ["logo", "generated"]

            [templates.box.fit]
            cover = "crop"
            """, baseTheme: InlineBase, id: "extends");

        Assert.Empty(result.Diagnostics);
        var box = result.Theme!.Templates["box"];

        // The model and shape are the base's; the back's chain is the base's, the spine's the theme's; the cover is
        // cropped again.
        Assert.Equal(("models/box.glb", true, true, "extends"), (box.Model, box.ModelFromBase, box.ShapeFromMedia, box.ThemeId));
        Assert.Equal([SlotSource.Media(MediaSlots.Screenshot), SlotSource.Generated], box.ChainFor(MediaSlots.Back).Sources);
        Assert.Equal([SlotSource.Media(MediaSlots.Logo), SlotSource.Generated], box.ChainFor(MediaSlots.Spine).Sources);
        Assert.False(box.ShowsWhole(MediaSlots.Cover));
    }

    [Fact]
    public void A_template_extending_the_bases_with_its_own_model_keeps_the_rest_of_the_base_template()
    {
        var result = ThemeFixtures.Parse("""
            name = "Own model"

            [templates.box]
            model = "my_box.glb"
            shape = "model"
            """, Box().Model("my_box.glb", "cover", "back", "case"), baseTheme: InlineBase);

        Assert.Empty(result.Diagnostics);
        var box = result.Theme!.Templates["box"];
        Assert.Equal(("my_box.glb", false, false), (box.Model, box.ModelFromBase, box.ShapeFromMedia));
        Assert.True(box.ShowsWhole(MediaSlots.Cover));
        Assert.Equal([SlotSource.Media(MediaSlots.Screenshot), SlotSource.Generated], box.ChainFor(MediaSlots.Back).Sources);
    }

    [Fact]
    public void A_new_template_still_needs_a_model()
    {
        var result = ThemeFixtures.Parse("""
            name = "New"

            [templates.tall_box.slots]
            back = ["screenshot"]
            """, baseTheme: InlineBase);

        Assert.Equal("templates.tall_box.model", Single(result, Severity.Error).Key);
        Assert.Empty(result.Theme!.Templates);
    }

    [Fact]
    public void A_bad_model_on_an_extending_template_leaves_it_out_so_the_base_template_is_used()
    {
        var result = ThemeFixtures.Parse("""
            name = "Bad"

            [templates.box]
            model = "missing.glb"

            [systems.snes]
            game_template = "box"
            """, baseTheme: InlineBase);

        Assert.Equal("templates.box.model", Single(result, Severity.Error).Key);
        Assert.Empty(result.Theme!.Templates);
        Assert.Equal("box", result.Theme.Systems["snes"].GameTemplate);
    }

    [Fact]
    public void The_cross_fade_time_is_the_base_themes_unless_the_theme_sets_one()
    {
        Assert.Equal(750, ThemeFixtures.Parse("name = \"Plain\"\n", baseTheme: InlineBase).Theme!.LookTransitionMs);
        Assert.Equal(200, ThemeFixtures.Parse("name = \"Quick\"\nlook_transition_ms = 200\n", baseTheme: InlineBase).Theme!.LookTransitionMs);
    }

    [Fact]
    public void The_console_theme_loads_cleanly_over_the_base_and_takes_the_rest_from_it()
    {
        var result = ThemeFixtures.LoadResult(ThemeFixtures.ConsoleFolder);

        Assert.Empty(result.Diagnostics);
        var console = result.Theme!;
        Assert.Equal(("console", "Console", ThemeOrigin.BuiltIn), (console.Id, console.Name, console.Origin));
        Assert.All(console.Systems.Values, system => Assert.True(File.Exists(console.PathOf(system.Model!)), system.Id));

        // Its cards fall back to the base's slab, and its games to the base's templates.
        Assert.Null(console.Defaults.SystemModel);
        Assert.Null(console.Defaults.GameTemplate);
        var baseTheme = ThemeFixtures.Base;
        var config = new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/home", ConfigDir = "C:/config", FileExists = null }).Config;
        var resolver = new ModelResolver(console, baseTheme, UserModels.None("C:/config"), config, "C:/data");
        Assert.Equal(console.PathOf("models/systems/gb.glb"), resolver.SystemModels("gb")[0].Path);
        Assert.Equal(baseTheme.PathOf(baseTheme.Defaults.SystemModel!), resolver.SystemModels("saturn")[0].Path);
        var megadrive = resolver.GameTemplates("megadrive")[0];
        Assert.Equal((ModelLevel.BaseSystem, "memory-card"), (megadrive.Level, megadrive.Template!.ThemeId));
        Assert.True(File.Exists(megadrive.Path));
    }
}
