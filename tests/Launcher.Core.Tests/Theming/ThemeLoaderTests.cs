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
    public void The_built_in_theme_loads_cleanly_with_a_look_colour_and_template_for_every_built_in_system()
    {
        var result = ThemeFixtures.LoadResult(ThemeFixtures.BuiltInFolder);

        Assert.Empty(result.Diagnostics);
        var theme = result.Theme!;
        Assert.Equal(("memory-card", "Memory Card", ThemeOrigin.BuiltIn), (theme.Id, theme.Name, theme.Origin));
        Assert.Equal(["cartridge_box", "clamshell", "dvd_case", "jewel_case", "umd_case"], theme.Templates.Keys.Order(StringComparer.Ordinal));
        Assert.Equal(("models/systems/generic.glb", true, "dvd_case"), (theme.Defaults.SystemModel, theme.Defaults.TintSystemModel, theme.Defaults.GameTemplate));

        // The look of A6, exactly.
        Assert.Equal("#1B1F4A", theme.Look.Background.TopLeft.ToString());
        Assert.Equal("#0B0B24", theme.Look.Background.BottomRight.ToString());
        Assert.Equal(3, theme.Look.Lights.Count);

        var config = new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/home", ConfigDir = "C:/config", FileExists = null }).Config;
        foreach (var (system, index) in config.Systems.Select((s, i) => (s, i)))
        {
            var entry = Assert.Contains(system.Id, theme.Systems);
            Assert.NotNull(entry.Colour);
            Assert.NotNull(entry.GameTemplate);
            Assert.Same(theme.Look.Ambient, entry.Look.Ambient);

            // The first fourteen have a look of their own; the rest of the catalogue shows the theme's.
            if (index < 14)
            {
                Assert.NotSame(theme.Look.Background, entry.Look.Background);
            }
        }

        Assert.Equal("clamshell", theme.Systems["megadrive"].GameTemplate);
        Assert.Equal("umd_case", theme.Systems["psp"].GameTemplate);
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
        Assert.Equal(ThemeFixtures.BuiltIn.Look.Background, result.Theme!.Look.Background);
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
            new ThemeSource("memory-card", new ConfigFile("built-in/theme.toml", "name = \"Broken\"\n"), ThemeOrigin.BuiltIn, "res://themes/memory-card", new FakeThemeFiles()),
            fallback: null);

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
        var builtIn = ThemeFixtures.BuiltIn;
        Assert.Equal($"{ThemeFixtures.BuiltInFolder}/models/templates/dvd_case.glb", builtIn.PathOf(builtIn.Templates["dvd_case"].Model));

        var user = ThemeFixtures.Load(ThemeFixtures.SlotShowcaseFolder);
        Assert.Equal(
            Path.Combine(ThemeFixtures.SlotShowcaseFolder, "models", "templates", "showcase_case.glb"),
            user.PathOf(user.Templates["showcase_case"].Model));
        Assert.True(File.Exists(user.PathOf(user.Templates["showcase_case"].Model)));
    }
}
