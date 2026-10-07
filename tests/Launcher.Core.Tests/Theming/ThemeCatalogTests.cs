using Launcher.Core.Config;
using Launcher.Core.Tests.TestSupport;
using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

public sealed class ThemeCatalogTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    /// <summary>The app's own themes, as it ships them: memory-card (the base), console and slab.</summary>
    private static List<ThemeSource> BuiltIns()
    {
        var diagnostics = new List<Diagnostic>();
        var sources = ThemeCatalog.BuiltInSources(ThemeFixtures.BuiltInThemesFolder, diagnostics);
        Assert.Empty(diagnostics);
        return sources;
    }

    private string Themes => _dir.Combine("themes");

    private void UserTheme(string id, string toml) => _dir.File($"themes/{id}/theme.toml", toml);

    [Fact]
    public void The_apps_themes_are_built_in_and_their_models_arent_inspected()
    {
        var sources = BuiltIns();

        Assert.Equal([ThemeCatalog.DefaultId, ThemeCatalog.BaseId, "slab"], sources.Select(s => s.Id));
        Assert.All(sources, s => Assert.Equal(ThemeOrigin.BuiltIn, s.Origin));
        Assert.All(sources, s => Assert.Null(s.Files.MaterialsOf("models/systems/gb.glb", out _)));
        Assert.True(sources[0].Files.Exists("models/systems/gb.glb"));
        Assert.False(sources[0].Files.Exists("models/systems/psp.glb"));
    }

    [Fact]
    public void The_chosen_user_theme_is_active_and_the_base_theme_stays_the_fallback()
    {
        UserTheme("neon", "name = \"Neon\"\n");
        UserTheme("plain", "name = \"Plain\"\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns(), ThemeCatalog.UserSources(Themes, diagnostics), "neon", diagnostics);

        Assert.Empty(diagnostics);
        Assert.Equal(("neon", "Neon", ThemeOrigin.User), (set.Active.Id, set.Active.Name, set.Active.Origin));
        Assert.Equal("memory-card", set.Base.Id);

        // The base theme isn't one to choose, so it isn't offered.
        Assert.Equal(["console", "neon", "plain", "slab"], set.Available);

        // A user theme with no look of its own takes the base's.
        Assert.Equal(set.Base.Look, set.Active.Look);
    }

    [Fact]
    public void The_default_theme_is_console_over_the_base()
    {
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns(), [], ThemeCatalog.DefaultId, diagnostics);

        Assert.Empty(diagnostics);
        Assert.Equal(("console", ThemeOrigin.BuiltIn), (set.Active.Id, set.Active.Origin));
        Assert.Equal("memory-card", set.Base.Id);
        Assert.NotSame(set.Base, set.Active);
    }

    [Fact]
    public void A_user_theme_can_replace_a_built_in_one_by_id()
    {
        UserTheme("console", "name = \"My Console\"\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns(), ThemeCatalog.UserSources(Themes, diagnostics), "console", diagnostics);

        Assert.Equal(("My Console", ThemeOrigin.User), (set.Active.Name, set.Active.Origin));
        Assert.Equal(("Memory Card", ThemeOrigin.BuiltIn), (set.Base.Name, set.Base.Origin));
    }

    [Fact]
    public void The_base_themes_id_is_reserved_so_a_user_theme_with_it_is_ignored()
    {
        UserTheme("memory-card", "name = \"My Memory Card\"\n");
        var diagnostics = new List<Diagnostic>();

        var users = ThemeCatalog.UserSources(Themes, diagnostics);

        Assert.Empty(users);
        var warning = Assert.Single(diagnostics);
        Assert.Contains("can't be replaced", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void The_base_theme_chosen_in_settings_is_a_warning_and_the_default_theme_is_used()
    {
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns(), [], ThemeCatalog.BaseId, diagnostics);

        Assert.Equal("console", set.Active.Id);
        var warning = Assert.Single(diagnostics);
        Assert.Equal((Severity.Warning, "display.theme"), (warning.Severity, warning.Key));
        Assert.Contains("'memory-card' is the base every theme builds on, not a theme to choose, so 'console' is used", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void The_base_theme_can_be_used_alone_when_allowed()
    {
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns(), [], ThemeCatalog.BaseId, diagnostics, allowBase: true);

        Assert.Empty(diagnostics);
        Assert.Same(set.Base, set.Active);
        Assert.Equal("memory-card", set.Active.Id);
    }

    [Fact]
    public void An_unknown_theme_is_a_warning_on_display_theme_and_the_default_theme_is_used()
    {
        UserTheme("neon", "name = \"Neon\"\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns(), ThemeCatalog.UserSources(Themes, diagnostics), "neom", diagnostics);

        Assert.Equal("console", set.Active.Id);
        var warning = Assert.Single(diagnostics);
        Assert.Equal((Severity.Warning, "display.theme"), (warning.Severity, warning.Key));
        Assert.Contains("did you mean 'neon'?", warning.Message, StringComparison.Ordinal);
        Assert.Contains("so 'console' is used", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_broken_theme_is_reported_with_its_file_and_the_default_theme_is_used()
    {
        UserTheme("broken", "name = \"Broken\"\nformat = 3\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns(), ThemeCatalog.UserSources(Themes, diagnostics), "broken", diagnostics);

        Assert.Equal("console", set.Active.Id);
        Assert.Equal(["format", string.Empty], diagnostics.Select(d => d.Key));
        Assert.All(diagnostics, d => Assert.Equal(Path.Combine(Themes, "broken", "theme.toml"), d.Source));
        Assert.Equal(2, diagnostics[0].Line);
    }

    [Fact]
    public void A_broken_default_theme_leaves_the_base_theme_alone()
    {
        UserTheme("console", "name = \"Broken\"\nformat = 3\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns(), ThemeCatalog.UserSources(Themes, diagnostics), "console", diagnostics);

        Assert.Same(set.Base, set.Active);
        Assert.Contains("so the base theme 'memory-card' is used", diagnostics[^1].Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Without_the_base_theme_the_app_cant_start()
    {
        var builtIns = BuiltIns().Where(s => s.Id != ThemeCatalog.BaseId).ToList();

        var error = Assert.Throws<InvalidOperationException>(() => ThemeCatalog.Load(builtIns, [], "console", []));
        Assert.Contains("'memory-card' is missing from the app's themes folder", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Folders_without_a_manifest_or_with_a_bad_id_are_skipped()
    {
        Directory.CreateDirectory(Path.Combine(Themes, "empty"));
        UserTheme("Bad Name", "name = \"Bad\"\n");
        var diagnostics = new List<Diagnostic>();

        var sources = ThemeCatalog.UserSources(Themes, diagnostics);

        Assert.Empty(sources);
        Assert.Contains("isn't a valid theme id", Assert.Single(diagnostics).Message, StringComparison.Ordinal);
        Assert.Empty(ThemeCatalog.UserSources(_dir.Combine("missing"), diagnostics));
    }
}
