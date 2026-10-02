using Launcher.Core.Config;
using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

/// <summary>The committed themes, and manifests written inline.</summary>
internal static class ThemeFixtures
{
    public static string RepoRoot { get; } = FindRepoRoot();

    /// <summary>The built-in theme, as the app ships it: <c>godot/themes/memory-card</c>.</summary>
    public static string BuiltInFolder => Path.Combine(RepoRoot, "godot", "themes", ThemeCatalog.BuiltInId);

    /// <summary>The M6 test theme: <c>tests/themes/slot-showcase</c>.</summary>
    public static string SlotShowcaseFolder => Path.Combine(RepoRoot, "tests", "themes", "slot-showcase");

    /// <summary>The M6 sample theme for theme authors: <c>samples/themes/retro-tv</c>.</summary>
    public static string RetroTvFolder => Path.Combine(RepoRoot, "samples", "themes", "retro-tv");

    public static ThemeSource Source(string folder, ThemeOrigin origin)
    {
        var manifest = Path.Combine(folder, ThemeLoader.ManifestFileName);
        return new ThemeSource(Path.GetFileName(folder), new ConfigFile(manifest, File.ReadAllText(manifest)), origin, folder, new FolderThemeFiles(folder));
    }

    public static ThemeLoadResult LoadResult(string folder) => folder == BuiltInFolder
        ? ThemeLoader.Load(Source(folder, ThemeOrigin.BuiltIn), null)
        : ThemeLoader.Load(Source(folder, ThemeOrigin.User), BuiltIn.Look);

    public static Theme Load(string folder) => LoadResult(folder).Theme ?? throw new InvalidOperationException($"{folder} didn't load.");

    public static Theme BuiltIn => Load(BuiltInFolder);

    /// <summary>An inline manifest, as <c>user/themes/test/theme.toml</c>, over fake files.</summary>
    public static ThemeLoadResult Parse(string toml, FakeThemeFiles? files = null, Look? fallback = null, string id = "test") =>
        ThemeLoader.Load(
            new ThemeSource(id, new ConfigFile($"user/themes/{id}/theme.toml", toml), ThemeOrigin.User, $"C:/themes/{id}", files ?? new FakeThemeFiles()),
            fallback ?? BuiltIn.Look);

    /// <summary>
    /// An inline manifest loaded as a built-in theme (no fallback look), over fake files: a stand-in for the
    /// memory-card theme where a test needs fixed templates, since that theme's choices keep changing.
    /// </summary>
    public static Theme ParseBuiltIn(string toml, FakeThemeFiles files, string id = ThemeCatalog.BuiltInId) =>
        ThemeLoader.Load(
            new ThemeSource(id, new ConfigFile($"res://themes/{id}/theme.toml", toml), ThemeOrigin.BuiltIn, $"res://themes/{id}", files),
            null).Theme ?? throw new InvalidOperationException($"The inline built-in theme '{id}' didn't load.");

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
