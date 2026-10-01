namespace Launcher.Core.Config;

/// <summary>The merged, validated configuration. Only enabled, valid entries are present.</summary>
public sealed record AppConfig(
    Settings Settings,
    IReadOnlyList<SystemConfig> Systems,
    IReadOnlyDictionary<string, EmulatorConfig> Emulators)
{
    /// <summary>A linear search: there are a few dozen systems at most, and a cached map would go stale under <c>with</c>.</summary>
    public SystemConfig? FindSystem(string id)
    {
        foreach (var system in Systems)
        {
            if (string.Equals(system.Id, id, StringComparison.Ordinal))
            {
                return system;
            }
        }

        return null;
    }
}

/// <summary><c>settings.toml</c>.</summary>
/// <param name="RomRoot">Absolute, expanded <c>paths.rom_root</c>.</param>
/// <param name="Variables">Expanded <c>[variables]</c>: plain strings, no placeholders left.</param>
public sealed record Settings(
    int Format,
    string RomRoot,
    IReadOnlyDictionary<string, string> Variables,
    DisplaySettings Display,
    ScrapingSettings Scraping,
    ScanningSettings Scanning);

/// <param name="Exclude">Glob patterns applied to every system; already folded into each <see cref="SystemConfig.Exclude"/>.</param>
public sealed record ScanningSettings(IReadOnlyList<string> Exclude);

/// <param name="HideEmptySystems">The systems grid leaves out systems with no games (like ES-DE), so the built-in catalogue only shows what the user has.</param>
public sealed record DisplaySettings(string Theme, bool Fullscreen, bool HideEmptySystems = true);

/// <summary><c>[scraping]</c>.</summary>
/// <param name="Provider">The provider asked first for every game.</param>
/// <param name="Fallback">Asked in order for what the provider before them left missing. Never contains <paramref name="Provider"/>.</param>
/// <param name="Regions">ScreenScraper region codes, most wanted first.</param>
/// <param name="Languages">Language codes, most wanted first.</param>
/// <param name="Media">The media kinds to download, as <c>media.kind</c> values.</param>
/// <param name="HashLimitBytes">ROMs up to this size are hashed (CRC32, MD5, SHA-1) for ScreenScraper lookups; 0 hashes none.</param>
public sealed record ScrapingSettings(
    string Provider,
    IReadOnlyList<string> Fallback,
    IReadOnlyList<string> Regions,
    IReadOnlyList<string> Languages,
    IReadOnlyList<string> Media,
    long HashLimitBytes)
{
    /// <summary>The provider, then each fallback.</summary>
    public IReadOnlyList<string> ProviderOrder => [Provider, .. Fallback];
}

public enum RomDirSource
{
    /// <summary>
    /// No <c>rom_dirs</c> in config. <see cref="SystemConfig.RomDirs"/> lists the candidates
    /// <c>{rom_root}/&lt;id&gt;</c> then <c>{rom_root}/&lt;alias&gt;</c>..., and the scanner uses the first that exists.
    /// </summary>
    Default,

    /// <summary><c>rom_dirs</c> is set. Every folder is scanned, in order; earlier folders win path collisions.</summary>
    Configured,
}

/// <summary>A <c>[systems.&lt;id&gt;]</c> entry.</summary>
/// <param name="Extensions">Lower-case, each starting with '.'.</param>
/// <param name="RomDirs">Absolute folders; see <see cref="RomDirSource"/>.</param>
/// <param name="Exclude">
/// The effective glob patterns, matched against paths relative to a ROM folder: <c>scanning.exclude</c>
/// from settings.toml, then the system's own <c>exclude</c>.
/// </param>
/// <param name="IgdbPlatforms">IGDB platform ids searched for this system's games (a regional twin too, such as Famicom); null or empty skips IGDB.</param>
/// <param name="SteamStore"><c>steam_store</c>: this system's games are looked up on the Steam store (a PC system).</param>
/// <param name="GameModel">
/// <c>game_model</c>: a game template id the user chose for this system, looked up in the active theme and then the
/// built-in one (A7). Null when unset: the theme decides.
/// </param>
public sealed record SystemConfig(
    string Id,
    string Name,
    string? Manufacturer,
    int? Year,
    IReadOnlyList<string> Aliases,
    IReadOnlyList<string> Extensions,
    string Emulator,
    IReadOnlyList<string> AltEmulators,
    string? GameModel,
    int? ScreenScraperId,
    IReadOnlyList<string> RomDirs,
    RomDirSource RomDirSource,
    bool Recursive,
    IReadOnlyList<string> Exclude,
    IReadOnlyList<int>? IgdbPlatforms = null,
    bool SteamStore = false);

/// <summary>An <c>[emulators.&lt;id&gt;]</c> entry.</summary>
/// <param name="Executable">Expanded absolute path, with no placeholders left.</param>
/// <param name="Args">Templates: config variables are expanded, launch placeholders remain (A5).</param>
/// <param name="WorkingDir">Template, like <paramref name="Args"/>.</param>
/// <param name="Core">
/// Expanded absolute path of a RetroArch core (or any plug-in the emulator loads), which <c>{core}</c> expands to.
/// Null when the profile has none, and then no template uses <c>{core}</c>.
/// </param>
/// <param name="RunFile">
/// <c>run_file</c>: the profile runs the game's own file (a program, or a shortcut or script made for the game)
/// instead of an emulator. <paramref name="Executable"/> is then empty, there are no arguments or core, and
/// <paramref name="WorkingDir"/> defaults to the game's folder.
/// </param>
public sealed record EmulatorConfig(
    string Id,
    string Name,
    string Executable,
    IReadOnlyList<string> Args,
    string WorkingDir,
    string? Core = null,
    bool RunFile = false)
{
    /// <summary>What the settings screens show where a profile's program goes.</summary>
    public string ProgramText => RunFile ? "Runs the game's own file" : Executable;
}

public sealed record ConfigLoadResult(AppConfig Config, IReadOnlyList<Diagnostic> Diagnostics)
{
    public bool HasErrors => Diagnostics.Any(d => d.IsError);
}

public interface IConfigLoader
{
    /// <summary>Loads, merges and validates. Never throws for user mistakes: they become diagnostics.</summary>
    ConfigLoadResult Load(ConfigSources sources);
}
