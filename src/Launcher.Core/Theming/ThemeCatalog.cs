using Launcher.Core.Config;

namespace Launcher.Core.Theming;

/// <summary>The themes loaded for a session: the active one, and the built-in one every lookup falls back to.</summary>
/// <param name="Available">Every theme id that can be switched to, sorted (user themes and built-in ones).</param>
public sealed record ThemeSet(Theme Active, Theme BuiltIn, IReadOnlyList<string> Available, IReadOnlyList<Diagnostic> Diagnostics);

/// <summary>
/// Finds themes (A6): built-in ones in the app (<c>res://themes/&lt;id&gt;/</c>, whose text the app reads) and the
/// user's in <c>ConfigDir/themes/&lt;id&gt;/</c>. A user theme with a built-in theme's id replaces it, but the
/// built-in default theme stays the last resort for anything the active theme doesn't provide.
/// </summary>
public static class ThemeCatalog
{
    /// <summary>The built-in default theme (settings.toml's default <c>[display] theme</c>).</summary>
    public const string BuiltInId = "memory-card";

    /// <summary>Every <c>&lt;id&gt;/theme.toml</c> under the user's themes folder. Does file I/O: never on the main thread.</summary>
    public static List<ThemeSource> UserSources(string themesDir, List<Diagnostic> diagnostics)
    {
        ArgumentNullException.ThrowIfNull(themesDir);
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

            try
            {
                sources.Add(new ThemeSource(id, new ConfigFile(manifest, File.ReadAllText(manifest)), ThemeOrigin.User, folder, new FolderThemeFiles(folder)));
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                diagnostics.Add(new Diagnostic(Severity.Warning, manifest, 0, 0, string.Empty, $"couldn't be read: {e.Message}"));
            }
        }

        return sources;
    }

    /// <summary>
    /// Loads the built-in default theme and the one <paramref name="wantedId"/> names. A theme that's missing or
    /// can't be used is reported, and the built-in one is used instead.
    /// </summary>
    /// <param name="builtIns">The app's built-in themes; one must be <see cref="BuiltInId"/>.</param>
    /// <param name="users">The user's themes (<see cref="UserSources"/>).</param>
    /// <param name="builtInResult">The built-in theme already loaded (<see cref="LoadBuiltIn"/>), or null to load it here.</param>
    /// <exception cref="InvalidOperationException">The built-in default theme is missing or broken: the app can't draw anything.</exception>
    public static ThemeSet Load(
        IReadOnlyList<ThemeSource> builtIns, IReadOnlyList<ThemeSource> users, string wantedId, List<Diagnostic> diagnostics,
        ThemeLoadResult? builtInResult = null)
    {
        ArgumentNullException.ThrowIfNull(builtIns);
        ArgumentNullException.ThrowIfNull(users);
        ArgumentNullException.ThrowIfNull(wantedId);
        ArgumentNullException.ThrowIfNull(diagnostics);
        var defaultSource = DefaultSource(builtIns);
        builtInResult ??= LoadBuiltIn(builtIns);
        diagnostics.AddRange(builtInResult.Diagnostics);
        var builtIn = builtInResult.Theme
            ?? throw new InvalidOperationException($"The built-in theme '{BuiltInId}' couldn't be loaded: {string.Join("; ", builtInResult.Diagnostics)}");

        var byId = new Dictionary<string, ThemeSource>(StringComparer.Ordinal);
        foreach (var source in builtIns)
        {
            byId[source.Id] = source;
        }

        foreach (var source in users)
        {
            byId[source.Id] = source;
        }

        var available = byId.Keys.Order(StringComparer.Ordinal).ToList();
        if (!byId.TryGetValue(wantedId, out var wanted))
        {
            diagnostics.Add(new Diagnostic(Severity.Warning, ConfigSources.SettingsFileName, 0, 0, "display.theme",
                $"there's no theme '{wantedId}'{TomlValidator.Suggest(wantedId, available)} (themes: {string.Join(", ", available)}), so '{builtIn.Id}' is used"));
            return new ThemeSet(builtIn, builtIn, available, diagnostics);
        }

        if (ReferenceEquals(wanted, defaultSource))
        {
            return new ThemeSet(builtIn, builtIn, available, diagnostics);
        }

        var result = ThemeLoader.Load(wanted, builtIn.Look);
        diagnostics.AddRange(result.Diagnostics);
        if (result.Theme is null)
        {
            diagnostics.Add(new Diagnostic(Severity.Warning, wanted.Manifest.Source, 0, 0, string.Empty,
                $"the theme '{wantedId}' can't be used until its errors are fixed, so '{builtIn.Id}' is used"));
            return new ThemeSet(builtIn, builtIn, available, diagnostics);
        }

        return new ThemeSet(result.Theme, builtIn, available, diagnostics);
    }

    /// <summary>
    /// The built-in default theme alone. It needs no config, so the app loads it (and starts loading its models, the
    /// last resort for every system) while config loads.
    /// </summary>
    public static ThemeLoadResult LoadBuiltIn(IReadOnlyList<ThemeSource> builtIns) => ThemeLoader.Load(DefaultSource(builtIns), null);

    private static ThemeSource DefaultSource(IReadOnlyList<ThemeSource> builtIns) =>
        builtIns.FirstOrDefault(s => s.Id == BuiltInId)
        ?? throw new InvalidOperationException($"The built-in theme '{BuiltInId}' is missing from the app.");
}
