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
        foreach (var system in config.Systems)
        {
            var entry = Assert.Contains(system.Id, theme.Systems);
            Assert.NotNull(entry.Colour);
            if (entry.GameTemplate is { } template)
            {
                Assert.Contains(template, theme.Templates);
            }

            Assert.Same(theme.Look.Ambient, entry.Look.Ambient);
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
    public void A_template_plays_games_videos_on_the_slot_its_video_names_after_its_delay()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            video = "screenshot"
            video_delay_ms = 2500
            """, Box("screenshot", "case"));

        Assert.Empty(result.Diagnostics);
        var template = result.Theme!.Templates["box"];
        Assert.Equal((MediaSlots.Screenshot, 2500), (template.VideoSlot, template.VideoDelayMs));

        // Without the keys: no video, and a second's delay for one that adds a video.
        var plain = ThemeFixtures.Parse(MinimalTemplate, Box()).Theme!.Templates["box"];
        Assert.Equal((-1, GameTemplate.DefaultVideoDelayMs), (plain.VideoSlot, plain.VideoDelayMs));
    }

    [Fact]
    public void A_bad_video_or_delay_is_an_error_at_its_key_and_the_template_is_kept_without_it()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            video = "screnshot"
            video_delay_ms = 70000
            """, Box("screenshot", "case"));

        Assert.Equal(2, result.Diagnostics.Count(d => d.Severity == Severity.Error));
        var video = Assert.Single(result.Diagnostics, d => d.Key == "templates.box.video");
        Assert.Contains("did you mean 'screenshot'?", video.Message, StringComparison.Ordinal);
        var delay = Assert.Single(result.Diagnostics, d => d.Key == "templates.box.video_delay_ms");
        Assert.Contains("out of range (0 to 60000)", delay.Message, StringComparison.Ordinal);
        var template = result.Theme!.Templates["box"];
        Assert.Equal((-1, GameTemplate.DefaultVideoDelayMs), (template.VideoSlot, template.VideoDelayMs));
    }

    [Fact]
    public void A_video_on_a_slot_the_model_doesnt_have_or_a_delay_without_a_video_is_a_warning()
    {
        var missing = ThemeFixtures.Parse(MinimalTemplate + "\nvideo = \"screenshot\"", Box("cover", "case"));
        var warning = Single(missing, Severity.Warning);
        Assert.Equal("templates.box.video", warning.Key);
        Assert.Contains("has no 'screenshot' material, so games' videos never play on it", warning.Message, StringComparison.Ordinal);

        var unused = ThemeFixtures.Parse(MinimalTemplate + "\nvideo_delay_ms = 500", Box());
        Assert.Equal("templates.box.video_delay_ms", Single(unused, Severity.Warning).Key);
    }

    [Fact]
    public void A_template_extending_the_bases_keeps_its_video_and_can_change_the_delay()
    {
        var files = new FakeThemeFiles().Model("models/tv.glb", "screenshot", "case");
        var baseTheme = ThemeFixtures.ParseBase("""
            format = 1
            name = "Base"

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
            game_template = "tv"

            [templates.tv]
            model = "models/tv.glb"
            video = "screenshot"
            """, files);

        var result = ThemeFixtures.Parse("""
            name = "Slower"

            [templates.tv]
            video_delay_ms = 3000
            """, baseTheme: baseTheme);

        Assert.Empty(result.Diagnostics);
        var tv = result.Theme!.Templates["tv"];
        Assert.Equal((MediaSlots.Screenshot, 3000), (tv.VideoSlot, tv.VideoDelayMs));

        // Its own model without the slot: a warning at the template, since the key is the base's.
        var own = ThemeFixtures.Parse("""
            name = "Own"

            [templates.tv]
            model = "box.glb"
            """, Box("cover", "case"), baseTheme: baseTheme);
        var warning = Single(own, Severity.Warning);
        Assert.Equal("templates.tv.video", warning.Key);
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
    public void A_shape_from_media_needs_a_cover_or_screenshot_material()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + "\nshape = \"media\"", Box("label", "case"));

        var warning = Single(result, Severity.Warning);
        Assert.Equal("templates.box.shape", warning.Key);
        Assert.Contains("has no 'cover' or 'screenshot' material", warning.Message, StringComparison.Ordinal);
        Assert.False(result.Theme!.Templates["box"].ShapeFromMedia);
    }

    [Fact]
    public void A_shape_from_media_follows_the_screenshot_on_a_model_with_no_cover()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + "\nshape = \"media\"", Box("screenshot", "case"));

        Assert.Empty(result.Diagnostics);
        Assert.True(result.Theme!.Templates["box"].ShapeFromMedia);
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
        Assert.Equal(("console", ThemeOrigin.BuiltIn), (console.Id, console.Origin));
        Assert.All(console.Systems.Values, system => Assert.True(File.Exists(console.PathOf(system.Model!)), system.Id));
        Assert.All(console.Templates.Values, template => Assert.True(File.Exists(console.PathOf(template.Model)), template.Id));

        // It builds on the base: it sets no default card or game template of its own, so what it doesn't name resolves
        // to the base's. Which systems and templates it names is the theme's to change, so none is checked by name.
        Assert.Null(console.Defaults.SystemModel);
        Assert.Null(console.Defaults.GameTemplate);
        var baseTheme = ThemeFixtures.Base;
        var config = new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/home", ConfigDir = "C:/config", FileExists = null }).Config;
        var resolver = new ModelResolver(console, baseTheme, UserModels.None("C:/config"), config, "C:/data");
        foreach (var system in config.Systems.Select(s => s.Id))
        {
            var card = resolver.SystemModels(system)[0];
            Assert.True(File.Exists(card.Path), $"{system}: {card.Path}");
            var game = resolver.GameTemplates(system)[0];
            Assert.True(File.Exists(game.Path), $"{system}: {game.Path}");
        }

        var unnamed = config.Systems.Select(s => s.Id).First(system => !console.Systems.ContainsKey(system));
        Assert.Equal(baseTheme.PathOf(baseTheme.Defaults.SystemModel!), resolver.SystemModels(unnamed)[0].Path);
    }

    // ---- System cards' chains and logos ----------------------------------------------------------

    [Fact]
    public void Card_chains_are_read_from_the_defaults_and_each_system()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [defaults]
            system_model = "card.glb"

            [defaults.system_slots]
            label = ["logo", "generated"]

            [systems.ps2.slots]
            cover = ["logo", "authored"]
            """, Box().Model("card.glb", "label", "cover", "case"));

        Assert.Empty(result.Diagnostics);
        var theme = result.Theme!;
        Assert.Equal([SlotSource.Media(MediaSlots.Logo), SlotSource.Generated], theme.Defaults.SystemSlots[MediaSlots.Label].Sources);
        Assert.Equal([MediaSlots.Label], theme.Defaults.SystemSlots.Keys);
        Assert.Equal([SlotSource.Media(MediaSlots.Logo), SlotSource.Authored], theme.Systems["ps2"].Slots![MediaSlots.Cover].Sources);
        Assert.Equal([MediaSlots.Cover], theme.Systems["ps2"].Slots!.Keys);
    }

    [Fact]
    public void A_card_chain_can_only_name_the_logo_and_its_mistakes_are_reported_at_their_keys()
    {
        var result = ThemeFixtures.Parse(MinimalTemplate + """

            [defaults.system_slots]
            label = ["cover", "generated"]
            logo = ["logo", "generated"]
            back = ["logo", "authored"]

            [systems.ps2.slots]
            cover = ["logoo"]
            """, Box());

        var errors = result.Diagnostics.Where(d => d.IsError).ToList();
        Assert.Equal(["defaults.system_slots.label", "defaults.system_slots.logo", "systems.ps2.slots.cover"], errors.Select(e => e.Key));
        Assert.Contains("a system has no cover: its only art is its logo", errors[0].Message, StringComparison.Ordinal);
        Assert.Contains("can't draw a logo", errors[1].Message, StringComparison.Ordinal);
        Assert.Contains("did you mean 'logo'?", errors[2].Message, StringComparison.Ordinal);
        Assert.Equal([7, 8, 12], errors.Select(e => e.Line));

        // The good chain stays; the bad ones fall back to a card's default.
        var theme = result.Theme!;
        Assert.Equal([MediaSlots.Back], theme.Defaults.SystemSlots.Keys);
        Assert.Null(theme.Systems["ps2"].Slots);
    }

    [Fact]
    public void Logos_are_the_logos_folders_images_by_id_and_a_systems_logo_wins()
    {
        var result = ThemeFixtures.Parse("""
            name = "Logos"

            [systems.psx]
            logo = "art/psx.jpg"

            [systems.ps2]
            logo = "./art/ps2.webp"
            """, new FakeThemeFiles().File(
                "logos/ps2.png", "logos/megadrive.webp", "logos/megadrive.png", "logos/Saturn.JPG", "logos/not an id.png",
                "logos/readme.txt", "logos/sub/gb.png", "art/psx.jpg", "art/ps2.webp"));

        Assert.Empty(result.Diagnostics);
        Assert.Equal(
            new Dictionary<string, string>
            {
                ["megadrive"] = "logos/megadrive.png",
                ["ps2"] = "art/ps2.webp",
                ["psx"] = "art/psx.jpg",
                ["saturn"] = "logos/Saturn.JPG",
            },
            result.Theme!.Logos.OrderBy(l => l.Key, StringComparer.Ordinal).ToDictionary());
        Assert.Equal("art/psx.jpg", result.Theme.Systems["psx"].Logo);
    }

    [Fact]
    public void A_bad_logo_is_an_error_and_the_logos_folder_still_counts()
    {
        var result = ThemeFixtures.Parse("""
            name = "Logos"

            [systems.ps2]
            logo = "../ps2.png"

            [systems.psx]
            logo = "logos/psx.gif"

            [systems.saturn]
            logo = "logos/missing.png"
            """, new FakeThemeFiles().File("logos/saturn.png", "logos/psx.gif"));

        var errors = result.Diagnostics.Where(d => d.IsError).ToList();
        Assert.Equal(["systems.ps2.logo", "systems.psx.logo", "systems.saturn.logo"], errors.Select(e => e.Key));
        Assert.Contains("must be a path inside the theme's folder", errors[0].Message, StringComparison.Ordinal);
        Assert.Contains("isn't a PNG, JPEG or WebP image", errors[1].Message, StringComparison.Ordinal);
        Assert.Contains("doesn't exist in the theme's folder", errors[2].Message, StringComparison.Ordinal);
        Assert.Equal(["saturn"], result.Theme!.Logos.Keys);
    }

    // ---- Card videos ------------------------------------------------------------------------------

    [Fact]
    public void A_cards_video_is_an_mp4_in_the_theme_beside_its_model_and_plays_on_its_video_material()
    {
        var result = ThemeFixtures.Parse("""
            name = "Videos"

            [systems.amstradcpc]
            model = "cpc.glb"
            video = "./videos/cpc.mp4"
            """, new FakeThemeFiles().Model("cpc.glb", "Video.001", "case").File("videos/cpc.mp4"));

        Assert.Empty(result.Diagnostics);
        Assert.Equal("videos/cpc.mp4", result.Theme!.Systems["amstradcpc"].Video);
        Assert.Equal((true, true, false, false), (MediaSlots.IsVideoMaterial("Video.001"), MediaSlots.IsVideoMaterial("VIDEO"),
            MediaSlots.IsVideoMaterial("video.1"), MediaSlots.IsVideoMaterial(null)));
        Assert.Equal(-1, MediaSlots.OfMaterial("video"));
    }

    [Fact]
    public void A_bad_video_is_an_error_and_one_without_its_entrys_model_is_ignored_with_a_warning()
    {
        var result = ThemeFixtures.Parse("""
            name = "Videos"

            [systems.a]
            model = "a.glb"
            video = "../a.mp4"

            [systems.b]
            model = "a.glb"
            video = "videos/b.avi"

            [systems.c]
            model = "a.glb"
            video = "videos/missing.mp4"

            [systems.d]
            video = "videos/d.mp4"
            """, new FakeThemeFiles().Model("a.glb", "video").File("videos/b.avi", "videos/d.mp4"));

        var errors = result.Diagnostics.Where(d => d.IsError).ToList();
        Assert.Equal(["systems.a.video", "systems.b.video", "systems.c.video"], errors.Select(e => e.Key));
        Assert.Contains("must be a path inside the theme's folder", errors[0].Message, StringComparison.Ordinal);
        Assert.Contains("isn't an MP4 video", errors[1].Message, StringComparison.Ordinal);
        Assert.Contains("doesn't exist in the theme's folder", errors[2].Message, StringComparison.Ordinal);
        var warning = Assert.Single(result.Diagnostics, d => !d.IsError);
        Assert.Equal("systems.d.video", warning.Key);
        Assert.Contains("it has none", warning.Message, StringComparison.Ordinal);
        Assert.All(result.Theme!.Systems.Values, system => Assert.Null(system.Video));
    }

    [Fact]
    public void The_slab_theme_loads_cleanly_with_a_logo_on_one_grey_card_for_every_built_in_system()
    {
        var result = ThemeFixtures.LoadResult(ThemeFixtures.SlabFolder);

        Assert.Empty(result.Diagnostics);
        var slab = result.Theme!;
        Assert.Equal(("slab", "Slab", ThemeOrigin.BuiltIn), (slab.Id, slab.Name, slab.Origin));
        Assert.Equal(("models/systems/slab.glb", false), (slab.Defaults.SystemModel, slab.Defaults.TintSystemModel));
        Assert.True(File.Exists(slab.PathOf(slab.Defaults.SystemModel!)));

        var config = new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/home", ConfigDir = "C:/config", FileExists = null }).Config;
        var resolver = new ModelResolver(slab, ThemeFixtures.Base, UserModels.None("C:/config"), config, "C:/data");
        foreach (var id in config.Systems.Select(s => s.Id).Concat(["favourites", "recently_played", "all_games"]))
        {
            var logo = resolver.LogoOf(id);
            Assert.True(logo is not null && File.Exists(logo.Path), $"{id} has no logo in the Slab theme.");
        }

        foreach (var id in config.Systems.Select(s => s.Id).Append(null))
        {
            var card = resolver.SystemModels(id)[0];
            Assert.Equal((slab.PathOf("models/systems/slab.glb"), false), (card.Path, card.Tint));
            Assert.Equal([SlotSource.Media(MediaSlots.Logo), SlotSource.Authored], card.ChainFor(MediaSlots.Label, systemCard: true).Sources);
        }

        // Every image in its logos folder is some built-in system's, or a virtual card's.
        var known = config.Systems.Select(s => s.Id).Concat(["favourites", "recently_played", "all_games", "astrocade"]).ToHashSet(StringComparer.Ordinal);
        Assert.All(Directory.GetFiles(slab.PathOf(Theme.LogosFolder)), file => Assert.Contains(Path.GetFileNameWithoutExtension(file), known));
    }

    [Fact]
    public void The_classic_view_theme_loads_cleanly_with_flat_covers_logo_cards_a_wallpaper_and_no_motion()
    {
        var result = ThemeFixtures.LoadResult(ThemeFixtures.ClassicViewFolder);

        Assert.Empty(result.Diagnostics);
        var classic = result.Theme!;
        Assert.Equal(("classic-view", "Classic View", ThemeOrigin.BuiltIn), (classic.Id, classic.Name, classic.Origin));
        Assert.Equal(("models/systems/classic.glb", false), (classic.Defaults.SystemModel, classic.Defaults.TintSystemModel));
        Assert.True(File.Exists(classic.PathOf(classic.Defaults.SystemModel!)));
        Assert.Equal(new ThemeMotion(0, 0), classic.Motion);
        Assert.True(File.Exists(classic.Look.Background.Wallpaper));

        var config = new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/home", ConfigDir = "C:/config", FileExists = null }).Config;
        var resolver = new ModelResolver(classic, ThemeFixtures.Base, UserModels.None("C:/config"), config, "C:/data");
        foreach (var id in config.Systems.Select(s => s.Id))
        {
            // Every system's games are flat covers, whatever Memory Card gives the system.
            var template = resolver.GameTemplates(id)[0];
            Assert.Equal(("flat_cover", ThemeFixtures.Base.PathOf("models/templates/flat_cover.glb")), (template.Template?.Id, template.Path));

            // Every system shows the theme's wallpaper behind its games.
            Assert.Equal(classic.Look.Background.Wallpaper, resolver.LookFor(id).Background.Wallpaper);
        }

        // Every card shows its logo on the panel's grey; a built-in system without a logo shows its name, printed.
        foreach (var id in config.Systems.Select(s => s.Id).Append(null))
        {
            var card = resolver.SystemModels(id)[0];
            Assert.Equal((classic.PathOf("models/systems/classic.glb"), false), (card.Path, card.Tint));
            var chain = card.ChainFor(MediaSlots.Label, systemCard: true).Sources;
            if (id is null || resolver.LogoOf(id) is not null)
            {
                Assert.Equal([SlotSource.Media(MediaSlots.Logo), SlotSource.Authored], chain);
            }
            else
            {
                Assert.Equal(SlotSource.Generated, chain[0]);
            }
        }

        // The virtual cards have logos, and every image in its logos folder is some built-in system's or a virtual card's.
        Assert.All((string[])["favourites", "recently_played", "all_games"], id => Assert.NotNull(resolver.LogoOf(id)));
        var known = config.Systems.Select(s => s.Id).Concat(["favourites", "recently_played", "all_games"]).ToHashSet(StringComparer.Ordinal);
        Assert.All(Directory.GetFiles(classic.PathOf(Theme.LogosFolder)), file => Assert.Contains(Path.GetFileNameWithoutExtension(file), known));
    }

    // ---- Menus (A6 Menus) -------------------------------------------------------------------------

    [Fact]
    public void A_theme_without_ui_has_the_launchers_own_menus()
    {
        Assert.Same(ThemeMenu.None, ThemeFixtures.Base.Menu);
        Assert.Same(ThemeMenu.None, ThemeFixtures.Load(ThemeFixtures.ConsoleFolder).Menu);
        Assert.Same(ThemeMenu.None, ThemeFixtures.Parse("name = \"Test\"").Theme!.Menu);
    }

    [Fact]
    public void Menu_colours_and_font_are_read_and_the_font_is_a_path_in_the_themes_folder()
    {
        var result = ThemeFixtures.Parse("""
            name = "Test"

            [ui.menu]
            background = "#101010"
            text = "#F0F0F0"
            accent = "#C0C0C0"
            font = "fonts/Menu.woff2"
            """, new FakeThemeFiles().File("fonts/Menu.woff2"));

        Assert.Empty(result.Diagnostics);
        var menu = result.Theme!.Menu;
        Assert.Equal(("#101010", "#F0F0F0", "#C0C0C0"), (menu.Background.ToString(), menu.Text.ToString(), menu.Accent.ToString()));
        Assert.Equal(Path.GetFullPath("C:/themes/test/fonts/Menu.woff2"), menu.Font);
        Assert.True(menu.SetsColour);
    }

    [Fact]
    public void Each_menu_key_left_out_is_the_base_themes()
    {
        var baseTheme = ThemeFixtures.ParseBase("""
            format = 1
            name = "Base"

            [look.background]
            top_left = "#000000"
            top_right = "#000000"
            bottom_left = "#000000"
            bottom_right = "#000000"

            [look.ambient]
            colour = "#202020"

            [[look.lights]]
            direction = [0, -1, 0]

            [ui.menu]
            background = "#202020"
            font = "menu.ttf"
            """, new FakeThemeFiles().File("menu.ttf"));

        var menu = ThemeFixtures.Parse("""
            name = "Test"

            [ui.menu]
            text = "#FFFFFF"
            """, baseTheme: baseTheme).Theme!.Menu;

        Assert.Equal(new ThemeMenu(new Rgb(0x20, 0x20, 0x20), new Rgb(0xFF, 0xFF, 0xFF), null, Path.GetFullPath("C:/app/themes/memory-card/menu.ttf")), menu);
    }

    [Fact]
    public void Menu_mistakes_are_reported_at_their_keys_and_keep_the_base_value()
    {
        var result = ThemeFixtures.Parse("""
            name = "Test"

            [ui]
            sounds = "click.wav"

            [ui.menu]
            backgrond = "#000000"
            text = "white"
            accent = "#FFFFFF"
            """);

        var warnings = result.Diagnostics.Where(d => d.Severity == Severity.Warning).ToList();
        Assert.Equal(["ui.sounds", "ui.menu.backgrond"], warnings.Select(w => w.Key));
        Assert.Contains("did you mean 'background'?", warnings[1].Message, StringComparison.Ordinal);
        var error = Single(result, Severity.Error);
        Assert.Equal(("ui.menu.text", 8), (error.Key, error.Line));
        Assert.Contains("'white' isn't a colour", error.Message, StringComparison.Ordinal);
        Assert.Equal(new ThemeMenu(null, null, new Rgb(0xFF, 0xFF, 0xFF), null), result.Theme!.Menu);
    }

    [Theory]
    [InlineData("../menu.ttf", "must be a path inside the theme's folder")]
    [InlineData("fonts/menu.fnt", "isn't a font (.ttf, .otf, .woff, .woff2)")]
    [InlineData("fonts/missing.ttf", "doesn't exist in the theme's folder")]
    [InlineData("fonts/big.otf", "is 4.5 MB; a menu font can be at most 4 MB")]
    public void A_bad_menu_font_is_an_error_and_the_default_font_is_kept(string path, string message)
    {
        var files = new FakeThemeFiles().File("fonts/menu.fnt").Sized("fonts/big.otf", (4 * 1024 * 1024) + (512 * 1024));
        var result = ThemeFixtures.Parse($"""
            name = "Test"

            [ui.menu]
            font = "{path}"
            """, files);

        var error = Single(result, Severity.Error);
        Assert.Equal("ui.menu.font", error.Key);
        Assert.Contains(message, error.Message, StringComparison.Ordinal);
        Assert.Null(result.Theme!.Menu.Font);
    }

    [Fact]
    public void Slab_has_dark_grey_menus_and_background_and_the_default_font()
    {
        var slab = ThemeFixtures.Load(ThemeFixtures.SlabFolder);

        Assert.True(slab.Menu.SetsColour);
        Assert.Null(slab.Menu.Font);
        foreach (var colour in new[] { slab.Menu.Background!.Value, slab.Menu.Accent!.Value, slab.Look.Background.TopLeft, slab.Look.Background.BottomRight })
        {
            Assert.True(colour.R == colour.G && colour.G == colour.B, $"{colour} isn't grey");
        }

        Assert.NotEqual(ThemeFixtures.Base.Look.Background, slab.Look.Background);
    }

    // ---- Wallpapers (A6 Background) ---------------------------------------------------------------

    private const string Corners = """
        top_left = "#101010"
        top_right = "#101010"
        bottom_left = "#000000"
        bottom_right = "#000000"
        """;

    [Fact]
    public void A_wallpaper_is_a_path_in_the_themes_folder_and_a_systems_background_replaces_the_themes_whole()
    {
        var result = ThemeFixtures.Parse($"""
            name = "Test"

            [look.background]
            {Corners}
            wallpaper = "wallpapers/Main.webp"

            [systems.ps2.look.background]
            {Corners}
            wallpaper = "wallpapers/ps2.png"
            fit = "stretch"

            [systems.snes.look.background]
            {Corners}
            """, new FakeThemeFiles().File("wallpapers/Main.webp", "wallpapers/ps2.png"));

        Assert.Empty(result.Diagnostics);
        var theme = result.Theme!;
        Assert.Equal((Path.GetFullPath("C:/themes/test/wallpapers/Main.webp"), WallpaperFit.Cover), (theme.Look.Background.Wallpaper, theme.Look.Background.Fit));
        Assert.Equal((Path.GetFullPath("C:/themes/test/wallpapers/ps2.png"), WallpaperFit.Stretch), (theme.LookFor("ps2").Background.Wallpaper, theme.LookFor("ps2").Background.Fit));
        Assert.Null(theme.LookFor("snes").Background.Wallpaper);
        Assert.Same(theme.Look, theme.LookFor("all_games"));
    }

    [Fact]
    public void A_background_left_out_keeps_the_base_themes_wallpaper_in_the_base_themes_folder()
    {
        var baseTheme = ThemeFixtures.ParseBase($"""
            format = 1
            name = "Base"

            [look.background]
            {Corners}
            wallpaper = "wall.jpg"

            [look.ambient]
            colour = "#202020"

            [[look.lights]]
            direction = [0, -1, 0]
            """, new FakeThemeFiles().File("wall.jpg"));

        var theme = ThemeFixtures.Parse("name = \"Test\"", baseTheme: baseTheme).Theme!;

        Assert.Equal(Path.GetFullPath("C:/app/themes/memory-card/wall.jpg"), theme.Look.Background.Wallpaper);
    }

    [Theory]
    [InlineData("../wall.png", "must be a path inside the theme's folder")]
    [InlineData("wall.gif", "isn't a PNG, JPEG or WebP image")]
    [InlineData("missing.png", "doesn't exist in the theme's folder")]
    [InlineData("big.png", "is 16.5 MB; a wallpaper can be at most 16 MB")]
    public void A_bad_wallpaper_is_an_error_and_the_gradient_is_kept(string path, string message)
    {
        var files = new FakeThemeFiles().File("wall.gif").Sized("big.png", (16 * 1024 * 1024) + (512 * 1024));
        var result = ThemeFixtures.Parse($"""
            name = "Test"

            [look.background]
            {Corners}
            wallpaper = "{path}"
            """, files);

        var error = Single(result, Severity.Error);
        Assert.Equal("look.background.wallpaper", error.Key);
        Assert.Contains(message, error.Message, StringComparison.Ordinal);
        Assert.Equal(new LookBackground(new Rgb(0x10, 0x10, 0x10), new Rgb(0x10, 0x10, 0x10), default, default), result.Theme!.Look.Background);
    }

    [Fact]
    public void A_bad_fit_is_an_error_and_a_fit_without_a_wallpaper_a_warning()
    {
        var result = ThemeFixtures.Parse($"""
            name = "Test"

            [look.background]
            {Corners}
            wallpaper = "wall.png"
            fit = "strech"

            [systems.ps2.look.background]
            {Corners}
            fit = "cover"
            """, new FakeThemeFiles().File("wall.png"));

        var error = Single(result, Severity.Error);
        Assert.Equal("look.background.fit", error.Key);
        Assert.Contains("did you mean 'stretch'?", error.Message, StringComparison.Ordinal);
        Assert.Equal(WallpaperFit.Cover, result.Theme!.Look.Background.Fit);
        Assert.NotNull(result.Theme.Look.Background.Wallpaper);
        var warning = Single(result, Severity.Warning);
        Assert.Equal("systems.ps2.look.background.fit", warning.Key);
    }

    [Fact]
    public void The_committed_themes_have_no_wallpaper_but_classic_views_and_the_slot_showcases()
    {
        foreach (var folder in new[] { ThemeFixtures.BaseFolder, ThemeFixtures.ConsoleFolder, ThemeFixtures.SlabFolder, ThemeFixtures.RetroTvFolder })
        {
            var theme = ThemeFixtures.Load(folder);
            Assert.Null(theme.Look.Background.Wallpaper);
            Assert.All(theme.Systems.Values, system => Assert.Null(system.Look.Background.Wallpaper));
        }

        var showcase = ThemeFixtures.Load(ThemeFixtures.SlotShowcaseFolder);
        Assert.True(File.Exists(showcase.Look.Background.Wallpaper));
        Assert.True(File.Exists(showcase.LookFor("ps2").Background.Wallpaper));
        Assert.NotEqual(showcase.Look.Background.Wallpaper, showcase.LookFor("ps2").Background.Wallpaper);
    }

    // ---- Motion (A6 Motion) -----------------------------------------------------------------------

    [Fact]
    public void A_theme_without_motion_moves_as_the_launcher_does()
    {
        Assert.Same(ThemeMotion.Default, ThemeFixtures.Base.Motion);
        Assert.Same(ThemeMotion.Default, ThemeFixtures.Load(ThemeFixtures.SlabFolder).Motion);
        Assert.Same(ThemeMotion.Default, ThemeFixtures.Parse("name = \"Test\"").Theme!.Motion);
        Assert.Equal(new ThemeMotion(1, 1), ThemeMotion.Default);
    }

    [Fact]
    public void Motion_is_read_as_multiples_of_the_launchers_own()
    {
        var result = ThemeFixtures.Parse("""
            name = "Test"

            [motion]
            focus_sway = 0.5
            idle_bob = 2
            """);

        Assert.Empty(result.Diagnostics);
        Assert.Equal(new ThemeMotion(0.5f, 2), result.Theme!.Motion);
    }

    [Fact]
    public void Each_motion_key_left_out_is_the_base_themes()
    {
        var baseTheme = ThemeFixtures.ParseBase("""
            format = 1
            name = "Base"

            [look.background]
            top_left = "#000000"
            top_right = "#000000"
            bottom_left = "#000000"
            bottom_right = "#000000"

            [look.ambient]
            colour = "#202020"

            [[look.lights]]
            direction = [0, -1, 0]

            [motion]
            focus_sway = 1.5
            idle_bob = 0.5
            """, new FakeThemeFiles());

        var motion = ThemeFixtures.Parse("""
            name = "Test"

            [motion]
            idle_bob = 0
            """, baseTheme: baseTheme).Theme!.Motion;

        Assert.Equal(new ThemeMotion(1.5f, 0), motion);
    }

    [Fact]
    public void Motion_mistakes_are_reported_at_their_keys_and_keep_the_base_value()
    {
        var result = ThemeFixtures.Parse("""
            name = "Test"

            [motion]
            focus_swey = 2
            idle_bob = 4
            """);

        var warning = Single(result, Severity.Warning);
        Assert.Equal("motion.focus_swey", warning.Key);
        Assert.Contains("did you mean 'focus_sway'?", warning.Message, StringComparison.Ordinal);
        var error = Single(result, Severity.Error);
        Assert.Equal(("motion.idle_bob", 5), (error.Key, error.Line));
        Assert.Contains("out of range (0 to 3)", error.Message, StringComparison.Ordinal);
        Assert.Equal(ThemeMotion.Default, result.Theme!.Motion);
    }
}
