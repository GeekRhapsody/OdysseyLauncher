using Launcher.Core.Config;
using Launcher.Core.Tests.TestSupport;
using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

public sealed class ThemeCatalogTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    private static IReadOnlyList<ThemeSource> BuiltIns => [ThemeFixtures.Source(ThemeFixtures.BuiltInFolder, ThemeOrigin.BuiltIn)];

    private string Themes => _dir.Combine("themes");

    private void UserTheme(string id, string toml) => _dir.File($"themes/{id}/theme.toml", toml);

    [Fact]
    public void The_chosen_user_theme_is_active_and_the_built_in_one_stays_the_fallback()
    {
        UserTheme("neon", "name = \"Neon\"\n");
        UserTheme("plain", "name = \"Plain\"\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns, ThemeCatalog.UserSources(Themes, diagnostics), "neon", diagnostics);

        Assert.Empty(diagnostics);
        Assert.Equal(("neon", "Neon", ThemeOrigin.User), (set.Active.Id, set.Active.Name, set.Active.Origin));
        Assert.Equal("memory-card", set.BuiltIn.Id);
        Assert.Equal(["memory-card", "neon", "plain"], set.Available);

        // A user theme with no look of its own takes the built-in one.
        Assert.Equal(set.BuiltIn.Look, set.Active.Look);
    }

    [Fact]
    public void A_user_theme_can_replace_the_built_in_one_by_id()
    {
        UserTheme("memory-card", "name = \"My Memory Card\"\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns, ThemeCatalog.UserSources(Themes, diagnostics), "memory-card", diagnostics);

        Assert.Equal(("My Memory Card", ThemeOrigin.User), (set.Active.Name, set.Active.Origin));
        Assert.Equal(("Memory Card", ThemeOrigin.BuiltIn), (set.BuiltIn.Name, set.BuiltIn.Origin));
    }

    [Fact]
    public void An_unknown_theme_is_a_warning_on_display_theme_and_the_built_in_one_is_used()
    {
        UserTheme("neon", "name = \"Neon\"\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns, ThemeCatalog.UserSources(Themes, diagnostics), "neom", diagnostics);

        Assert.Same(set.BuiltIn, set.Active);
        var warning = Assert.Single(diagnostics);
        Assert.Equal((Severity.Warning, "display.theme"), (warning.Severity, warning.Key));
        Assert.Contains("did you mean 'neon'?", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_broken_theme_is_reported_with_its_file_and_the_built_in_one_is_used()
    {
        UserTheme("broken", "name = \"Broken\"\nformat = 3\n");
        var diagnostics = new List<Diagnostic>();

        var set = ThemeCatalog.Load(BuiltIns, ThemeCatalog.UserSources(Themes, diagnostics), "broken", diagnostics);

        Assert.Same(set.BuiltIn, set.Active);
        Assert.Equal(["format", string.Empty], diagnostics.Select(d => d.Key));
        Assert.All(diagnostics, d => Assert.Equal(Path.Combine(Themes, "broken", "theme.toml"), d.Source));
        Assert.Equal(2, diagnostics[0].Line);
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
