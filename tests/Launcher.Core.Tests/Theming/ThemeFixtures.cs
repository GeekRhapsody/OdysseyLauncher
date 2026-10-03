using Launcher.Core.Config;
using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

/// <summary>The committed themes, and manifests written inline.</summary>
internal static class ThemeFixtures
{
    public static string RepoRoot { get; } = FindRepoRoot();

    /// <summary>The app's themes folder, as the export copies it beside the executable: <c>godot/themes</c>.</summary>
    public static string BuiltInThemesFolder => Path.Combine(RepoRoot, "godot", "themes");

    /// <summary>The base theme, as the app ships it: <c>godot/themes/memory-card</c>.</summary>
    public static string BaseFolder => Path.Combine(BuiltInThemesFolder, ThemeCatalog.BaseId);

    /// <summary>The default theme, built in: <c>godot/themes/console</c>.</summary>
    public static string ConsoleFolder => Path.Combine(BuiltInThemesFolder, ThemeCatalog.DefaultId);

    /// <summary>The M6 test theme: <c>tests/themes/slot-showcase</c>.</summary>
    public static string SlotShowcaseFolder => Path.Combine(RepoRoot, "tests", "themes", "slot-showcase");

    /// <summary>The M6 sample theme for theme authors: <c>samples/themes/retro-tv</c>.</summary>
    public static string RetroTvFolder => Path.Combine(RepoRoot, "samples", "themes", "retro-tv");

    /// <summary>A committed theme's folder as a source: the app's own (<c>godot/themes</c>) are built in, others the user's.</summary>
    public static ThemeSource Source(string folder, ThemeOrigin origin)
    {
        var manifest = Path.Combine(folder, ThemeLoader.ManifestFileName);
        return new ThemeSource(Path.GetFileName(folder), new ConfigFile(manifest, File.ReadAllText(manifest)), origin, folder,
            new FolderThemeFiles(folder, inspect: origin == ThemeOrigin.User));
    }

    /// <summary>A committed theme, loaded as the app loads it: the base alone, every other theme over the base.</summary>
    public static ThemeLoadResult LoadResult(string folder) => folder == BaseFolder
        ? ThemeLoader.Load(Source(folder, ThemeOrigin.BuiltIn), null)
        : ThemeLoader.Load(Source(folder, Path.GetDirectoryName(folder) == BuiltInThemesFolder ? ThemeOrigin.BuiltIn : ThemeOrigin.User), Base);

    public static Theme Load(string folder) => LoadResult(folder).Theme ?? throw new InvalidOperationException($"{folder} didn't load.");

    /// <summary>The real base theme, memory-card.</summary>
    public static Theme Base => Load(BaseFolder);

    /// <summary>An inline manifest, as <c>user/themes/test/theme.toml</c>, over fake files, loaded over a base theme (the real one by default).</summary>
    public static ThemeLoadResult Parse(string toml, FakeThemeFiles? files = null, Theme? baseTheme = null, string id = "test") =>
        ThemeLoader.Load(
            new ThemeSource(id, new ConfigFile($"user/themes/{id}/theme.toml", toml), ThemeOrigin.User, $"C:/themes/{id}", files ?? new FakeThemeFiles()),
            baseTheme ?? Base);

    /// <summary>
    /// An inline manifest loaded as the base theme (nothing under it), over fake files: a stand-in for memory-card where
    /// a test needs fixed templates, since that theme's choices keep changing.
    /// </summary>
    public static Theme ParseBase(string toml, FakeThemeFiles files, string id = ThemeCatalog.BaseId) =>
        ThemeLoader.Load(
            new ThemeSource(id, new ConfigFile($"app/themes/{id}/theme.toml", toml), ThemeOrigin.BuiltIn, $"C:/app/themes/{id}", files),
            null).Theme ?? throw new InvalidOperationException($"The inline base theme '{id}' didn't load.");

    private static string FindRepoRoot()
    {
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir is not null; dir = dir.Parent)
        {
            if (File.Exists(Path.Combine(dir.FullName, "OdysseyLauncher.slnx")))
            {
                return dir.FullName;
            }
        }

        throw new InvalidOperationException("The repository root (OdysseyLauncher.slnx) wasn't found above the test binaries.");
    }
}

/// <summary>Theme files that exist by name, with the materials each model has (null: can't be inspected).</summary>
internal sealed class FakeThemeFiles : IThemeFiles
{
    private readonly Dictionary<string, string[]?> _models = new(StringComparer.Ordinal);

    public FakeThemeFiles Model(string path, params string[]? materials)
    {
        _models[path] = materials;
        return this;
    }

    public bool Exists(string relativePath) => _models.ContainsKey(relativePath);

    public IReadOnlyList<string>? MaterialsOf(string relativePath, out string? error)
    {
        error = null;
        return _models.TryGetValue(relativePath, out var materials) ? materials : null;
    }
}
