using Launcher.Core.Config;

namespace Launcher.Core.Theming;

/// <summary>The themes loaded for a session: the active one, and the base theme every lookup falls back to.</summary>
/// <param name="Base">
/// The base theme (memory-card): whatever the active theme leaves out is its. The same object as
/// <paramref name="Active"/> when it's the only theme loaded (<c>--theme=memory-card</c>, or no other theme can be used).
/// </param>
/// <param name="Available">Every theme id that can be switched to, sorted (user themes and built-in ones; never the base).</param>
public sealed record ThemeSet(Theme Active, Theme Base, IReadOnlyList<string> Available, IReadOnlyList<Diagnostic> Diagnostics);

/// <summary>
/// Finds themes (A6): built-in ones in the app's <c>themes/&lt;id&gt;/</c> folder, beside its executable, and the
/// user's in <c>ConfigDir/themes/&lt;id&gt;/</c>. A user theme with a built-in theme's id replaces it. The base theme,
/// memory-card, isn't a theme to choose: every theme builds on it, and it's the last resort for anything the active
/// theme doesn't provide.
/// </summary>
public static class ThemeCatalog
{
    /// <summary>The base theme every theme builds on (A6). Not offered as a theme; its id is reserved.</summary>
    public const string BaseId = "memory-card";

    /// <summary>The default theme (settings.toml's default <c>[display] theme</c>).</summary>
    public const string DefaultId = "slab";

    /// <summary>Every <c>&lt;id&gt;/theme.toml</c> under the user's themes folder. Does file I/O: never on the main thread.</summary>
    public static List<ThemeSource> UserSources(string themesDir, List<Diagnostic> diagnostics) =>
        Sources(themesDir, ThemeOrigin.User, diagnostics);

    /// <summary>
    /// Every <c>&lt;id&gt;/theme.toml</c> under the app's themes folder (the base theme among them). Their models aren't
    /// inspected when the manifests load. Does file I/O: never on the main thread.
    /// </summary>
    public static List<ThemeSource> BuiltInSources(string themesDir, List<Diagnostic> diagnostics) =>
        Sources(themesDir, ThemeOrigin.BuiltIn, diagnostics);

    /// <summary>
    /// Loads the base theme and the one <paramref name="wantedId"/> names over it. A theme that's missing or can't be
    /// used is reported, and the default theme is used instead, else the base theme alone.
    /// </summary>
    /// <param name="builtIns">The app's built-in themes; one must be <see cref="BaseId"/>.</param>
    /// <param name="users">The user's themes (<see cref="UserSources"/>).</param>
    /// <param name="baseResult">The base theme already loaded (<see cref="LoadBase"/>), or null to load it here.</param>
    /// <param name="allowBase">
    /// Whether <paramref name="wantedId"/> may be the base theme, alone (<c>--theme=memory-card</c>, for captures and
    /// benches). From settings.toml it's a warning, and the default theme is used.
    /// </param>
    /// <exception cref="InvalidOperationException">The base theme is missing or broken: the app can't draw anything.</exception>
    public static ThemeSet Load(
        IReadOnlyList<ThemeSource> builtIns, IReadOnlyList<ThemeSource> users, string wantedId, List<Diagnostic> diagnostics,
        ThemeLoadResult? baseResult = null, bool allowBase = false)
    {
        ArgumentNullException.ThrowIfNull(builtIns);
        ArgumentNullException.ThrowIfNull(users);
        ArgumentNullException.ThrowIfNull(wantedId);
        ArgumentNullException.ThrowIfNull(diagnostics);
        baseResult ??= LoadBase(builtIns);
        diagnostics.AddRange(baseResult.Diagnostics);
        var baseTheme = baseResult.Theme
            ?? throw new InvalidOperationException($"The base theme '{BaseId}' couldn't be loaded: {string.Join("; ", baseResult.Diagnostics)}");

        var byId = new Dictionary<string, ThemeSource>(StringComparer.Ordinal);
        foreach (var source in builtIns.Concat(users))
        {
            if (source.Id != BaseId)
            {
                byId[source.Id] = source;
            }
        }

        var available = byId.Keys.Order(StringComparer.Ordinal).ToList();
        if (wantedId == BaseId)
        {
            if (allowBase)
            {
                return new ThemeSet(baseTheme, baseTheme, available, diagnostics);
            }

            diagnostics.Add(new Diagnostic(Severity.Warning, ConfigSources.SettingsFileName, 0, 0, "display.theme",
                $"'{BaseId}' is the base every theme builds on, not a theme to choose, so {FallbackName(BaseId)} is used (themes: {string.Join(", ", available)})"));
            return Fallback(BaseId);
        }

        if (!byId.TryGetValue(wantedId, out var wanted))
        {
            diagnostics.Add(new Diagnostic(Severity.Warning, ConfigSources.SettingsFileName, 0, 0, "display.theme",
                $"there's no theme '{wantedId}'{TomlValidator.Suggest(wantedId, available)} (themes: {string.Join(", ", available)}), so {FallbackName(wantedId)} is used"));
            return Fallback(wantedId);
        }

        return TryLoad(wanted) is { } active ? new ThemeSet(active, baseTheme, available, diagnostics) : Fallback(wantedId);

        // The default theme, unless it's the one that failed (or missing, or broken too): then the base theme alone.
        ThemeSet Fallback(string failed)
        {
            if (failed != DefaultId && byId.TryGetValue(DefaultId, out var fallback) && TryLoad(fallback) is { } defaultTheme)
            {
                return new ThemeSet(defaultTheme, baseTheme, available, diagnostics);
            }

            return new ThemeSet(baseTheme, baseTheme, available, diagnostics);
        }

        string FallbackName(string failed) => failed != DefaultId && byId.ContainsKey(DefaultId) ? $"'{DefaultId}'" : $"the base theme '{BaseId}'";

        Theme? TryLoad(ThemeSource source)
        {
            var result = ThemeLoader.Load(source, baseTheme);
            diagnostics.AddRange(result.Diagnostics);
            if (result.Theme is null)
            {
                diagnostics.Add(new Diagnostic(Severity.Warning, source.Manifest.Source, 0, 0, string.Empty,
                    $"the theme '{source.Id}' can't be used until its errors are fixed, so {FallbackName(source.Id)} is used"));
            }

            return result.Theme;
        }
    }

    /// <summary>
    /// The base theme alone. It needs no config, so the app loads it (and starts loading its models, the last resort for
    /// every system) while config loads.
    /// </summary>
    /// <exception cref="InvalidOperationException">The base theme isn't among <paramref name="builtIns"/>.</exception>
    public static ThemeLoadResult LoadBase(IReadOnlyList<ThemeSource> builtIns)
    {
        ArgumentNullException.ThrowIfNull(builtIns);
        var source = builtIns.FirstOrDefault(s => s.Id == BaseId)
            ?? throw new InvalidOperationException($"The base theme '{BaseId}' is missing from the app's themes folder: reinstall the app.");
        return ThemeLoader.Load(source, null);
    }

    private static List<ThemeSource> Sources(string themesDir, ThemeOrigin origin, List<Diagnostic> diagnostics)
    {
        ArgumentNullException.ThrowIfNull(themesDir);
        ArgumentNullException.ThrowIfNull(diagnostics);
        var sources = new List<ThemeSource>();
        if (!Directory.Exists(themesDir))
        {
            return sources;
        }

        IEnumerable<string> folders;
        try
        {
            folders = Directory.GetDirectories(themesDir).Order(StringComparer.Ordinal).ToList();
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            diagnostics.Add(new Diagnostic(Severity.Warning, themesDir, 0, 0, string.Empty, $"couldn't be read: {e.Message}"));
            return sources;
        }

        foreach (var folder in folders)
        {
            var id = Path.GetFileName(folder);
            var manifest = Path.Combine(folder, ThemeLoader.ManifestFileName);
            if (!File.Exists(manifest))
            {
                continue;
            }

            if (!TomlValidator.IsValidId(id))
            {
                diagnostics.Add(new Diagnostic(Severity.Warning, folder, 0, 0, string.Empty,
                    "isn't a valid theme id (use lower-case letters, digits, '_' and '-'), so this theme is ignored"));
                continue;
            }

            if (origin == ThemeOrigin.User && id == BaseId)
            {
                diagnostics.Add(new Diagnostic(Severity.Warning, folder, 0, 0, string.Empty,
                    $"'{BaseId}' is the base every theme builds on, and can't be replaced, so this theme is ignored: give its folder another name"));
                continue;
            }

            try
            {
                sources.Add(new ThemeSource(id, new ConfigFile(manifest, File.ReadAllText(manifest)), origin, folder,
                    new FolderThemeFiles(folder, inspect: origin == ThemeOrigin.User)));
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                diagnostics.Add(new Diagnostic(Severity.Warning, manifest, 0, 0, string.Empty, $"couldn't be read: {e.Message}"));
            }
        }

        return sources;
    }
}
