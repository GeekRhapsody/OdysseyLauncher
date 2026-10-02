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
    ScanningSettings Scanning,
    UiSettings Ui);

/// <param name="Exclude">Glob patterns applied to every system; already folded into each <see cref="SystemConfig.Exclude"/>.</param>
public sealed record ScanningSettings(IReadOnlyList<string> Exclude);

/// <param name="HideEmptySystems">The systems grid leaves out systems with no games (like ES-DE), so the built-in catalogue only shows what the user has.</param>
public sealed record DisplaySettings(string Theme, bool Fullscreen, bool HideEmptySystems = true)
{
    /// <summary>The most columns a grid can have (<c>systems_columns</c>, <c>games_columns</c>).</summary>
    public const int MaxColumns = 9;

    /// <summary>The most rows a grid can fit on screen (<c>systems_rows</c>, <c>games_rows</c>).</summary>
    public const int MaxRows = 6;

    /// <summary><c>systems_layout</c>: how the systems are shown.</summary>
    public SystemsLayout SystemsLayout { get; init; }

    /// <summary><c>systems_columns</c> and <c>systems_rows</c>: the systems grid's size; 0 is automatic.</summary>
    public GridSize SystemsGrid { get; init; }

    /// <summary><c>games_layout</c>: how a system's games are shown, unless the system has its own (<see cref="GamesLayoutFor"/>).</summary>
    public GamesLayout GamesLayout { get; init; }

    /// <summary><c>games_columns</c> and <c>games_rows</c>: the games grid's size; 0 is automatic. A system can have its own.</summary>
    public GridSize GamesGrid { get; init; }

    /// <summary>How a system's games are shown: its own <c>games_layout</c>, else these settings'. Null: Favourites and Recently played.</summary>
    public GamesLayout GamesLayoutFor(SystemConfig? system) => system?.GamesLayout ?? GamesLayout;

    /// <summary>The games grid's size for a system: its own columns and rows where it sets them, else these settings'.</summary>
    public GridSize GamesGridFor(SystemConfig? system) =>
        new(system?.GamesColumns ?? GamesGrid.Columns, system?.GamesRows ?? GamesGrid.Rows);
}

/// <summary>How the systems are shown (<c>[display] systems_layout</c>).</summary>
public enum SystemsLayout
{
    /// <summary><c>"grid"</c>: rows and columns of cards (the default).</summary>
    Grid,

    /// <summary><c>"carousel"</c>: one row, the focused card in the middle.</summary>
    Carousel,

    /// <summary><c>"single"</c>: one card at a time, filling the screen; left and right move to the next.</summary>
    Single,
}

/// <summary>How a system's games are shown (<c>[display] games_layout</c>).</summary>
public enum GamesLayout
{
    /// <summary><c>"grid"</c>: rows and columns of games (the default).</summary>
    Grid,

    /// <summary><c>"carousel"</c>: one row, the focused game in the middle.</summary>
    Carousel,

    /// <summary><c>"list"</c>: the titles in a list, with the focused game's model beside it.</summary>
    List,
}

/// <summary>A grid's columns and the rows that fit the screen's height; 0 for either is automatic.</summary>
public readonly record struct GridSize(int Columns, int Rows)
{
    public bool IsAutomatic => Columns == 0 && Rows == 0;
}

/// <summary>The names config uses for the layouts.</summary>
public static class Layouts
{
    public static IReadOnlyList<string> SystemsNames { get; } = ["grid", "carousel", "single"];

    public static IReadOnlyList<string> GamesNames { get; } = ["grid", "carousel", "list"];

    public static string Name(SystemsLayout layout) => SystemsNames[(int)layout];

    public static string Name(GamesLayout layout) => GamesNames[(int)layout];

    public static bool TryParse(string name, out SystemsLayout layout)
    {
        var index = IndexOf(SystemsNames, name);
        layout = (SystemsLayout)Math.Max(index, 0);
        return index >= 0;
    }

    public static bool TryParse(string name, out GamesLayout layout)
    {
        var index = IndexOf(GamesNames, name);
        layout = (GamesLayout)Math.Max(index, 0);
        return index >= 0;
    }

    private static int IndexOf(IReadOnlyList<string> names, string name)
    {
        for (var i = 0; i < names.Count; i++)
        {
            if (string.Equals(names[i], name, StringComparison.Ordinal))
            {
                return i;
            }
        }

        return -1;
    }
}

/// <summary><c>[ui]</c>: the status indicators top right, each on or off.</summary>
/// <param name="ShowClock">The time, in the user's regional short-time format.</param>
/// <param name="ShowBattery">The battery's charge; nothing shows on a device without one.</param>
/// <param name="ShowNetwork">Wi-Fi (with its signal), a cable, or disconnected.</param>
public sealed record UiSettings(bool ShowClock = true, bool ShowBattery = true, bool ShowNetwork = true);

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
/// <param name="GamesLayout"><c>games_layout</c>: how this system's games are shown; null uses <c>[display] games_layout</c>.</param>
/// <param name="GamesColumns"><c>games_columns</c>: the system's games grid's columns (0 automatic); null uses <c>[display] games_columns</c>.</param>
/// <param name="GamesRows"><c>games_rows</c>: the rows of its games grid that fit the screen (0 automatic); null uses <c>[display] games_rows</c>.</param>
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
    bool SteamStore = false,
    int? GamesColumns = null,
    int? GamesRows = null,
    GamesLayout? GamesLayout = null);

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
