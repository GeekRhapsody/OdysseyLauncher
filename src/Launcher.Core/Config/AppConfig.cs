using System.Globalization;

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

    /// <summary>
    /// The system whose card a system's games show under (A5 Grouped systems): its <c>group</c>, which the loader has
    /// checked names an enabled system that isn't grouped itself. Null when it isn't grouped, or <c>group_systems</c> is off.
    /// </summary>
    public SystemConfig? GroupParentOf(SystemConfig system) =>
        Settings.Display.GroupSystems && system.Group is { } parent ? FindSystem(parent) : null;

    /// <summary>
    /// The systems whose games a system's card shows: the system, then those grouped under it, in systems.toml's order.
    /// Just the system when nothing is grouped under it (or <c>group_systems</c> is off).
    /// </summary>
    public List<string> GroupMembers(string id)
    {
        var members = new List<string> { id };
        if (!Settings.Display.GroupSystems)
        {
            return members;
        }

        foreach (var system in Systems)
        {
            if (string.Equals(system.Group, id, StringComparison.Ordinal))
            {
                members.Add(system.Id);
            }
        }

        return members;
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
    UiSettings Ui)
{
    /// <summary>
    /// Absolute, expanded <c>paths.media</c> (2026-10-04): the media folder. Null: the default, <c>DataDir/media</c>,
    /// which the loader doesn't know (<see cref="Media.MediaFolder.Of"/>).
    /// </summary>
    public string? MediaDir { get; init; }
}

/// <param name="Exclude">Glob patterns applied to every system; already folded into each <see cref="SystemConfig.Exclude"/>.</param>
/// <param name="ScanAtLaunch">
/// <c>scan_at_launch</c> (2026-10-08): every system is rescanned once the app is interactive, not only those never
/// scanned. Off by default. Either is "Rescan the library" (<see cref="Library.RescanMedia.SystemsWithNewGames"/>, 2026-10-18).
/// </param>
public sealed record ScanningSettings(IReadOnlyList<string> Exclude, bool ScanAtLaunch = false);

/// <param name="ScreenMode"><c>screen_mode</c> (2026-10-08): fullscreen (exclusive), borderless fullscreen (the default) or a window.</param>
/// <param name="HideEmptySystems">The systems grid leaves out systems with no games (like ES-DE), so the built-in catalogue only shows what the user has.</param>
public sealed record DisplaySettings(string Theme, ScreenMode ScreenMode = ScreenMode.Borderless, bool HideEmptySystems = true)
{
    /// <summary>
    /// <c>group_systems</c> (2026-11-03): a system with a <c>group</c> (a regional variant) shows its games under its
    /// group's card instead of a card of its own (A5 Grouped systems). On by default.
    /// </summary>
    public bool GroupSystems { get; init; } = true;

    /// <summary>The anisotropic filtering levels <c>anisotropic_filtering</c> takes; 0 is off.</summary>
    public static IReadOnlyList<int> AnisotropicLevels { get; } = [0, 2, 4, 8, 16];

    /// <summary>
    /// <c>render_resolution</c> (2026-10-08): the height the 3D renders at in the fullscreen modes (the 2D UI is always
    /// native). A window always uses <see cref="RenderResolution.Automatic"/>.
    /// </summary>
    public RenderResolution RenderResolution { get; init; }

    /// <summary><c>window_size</c> (2026-10-08): the window's size when <see cref="ScreenMode"/> is windowed.</summary>
    public WindowSize WindowSize { get; init; } = WindowSize.Default;

    /// <summary>
    /// <c>rendering_driver</c> (2026-10-08): the driver the engine starts with, from the next start
    /// (<see cref="Platform.RenderingOverride"/>).
    /// </summary>
    public RenderingDriver RenderingDriver { get; init; }

    /// <summary>
    /// <c>anisotropic_filtering</c> (2026-10-08): the most texture samples along a squeezed axis, one of
    /// <see cref="AnisotropicLevels"/>; 16 by default, the most D3D12 and Vulkan allow.
    /// </summary>
    public int AnisotropicFiltering { get; init; } = 16;

    /// <summary>The 3D resolution in use: <see cref="RenderResolution"/> in the fullscreen modes, automatic in a window.</summary>
    public RenderResolution EffectiveRenderResolution => ScreenMode == ScreenMode.Windowed ? RenderResolution.Automatic : RenderResolution;

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

    /// <summary><c>[display.favourites]</c> (2026-11-10): Favourites' own view and order; what it leaves unset is these settings'.</summary>
    public GamesView Favourites { get; init; } = GamesView.None;

    /// <summary><c>[display.all_games]</c> (2026-11-10): All games' own view and order; what it leaves unset is these settings'.</summary>
    public GamesView AllGames { get; init; } = GamesView.None;

    /// <summary>How a list's games are shown: its own <c>games_layout</c>, else these settings'. Null: Recently played.</summary>
    public GamesLayout GamesLayoutFor(GamesView? view) => view?.Layout ?? GamesLayout;

    /// <summary>The games grid's size for a list: its own columns and rows where it sets them, else these settings'.</summary>
    public GridSize GamesGridFor(GamesView? view) =>
        new(view?.Columns ?? GamesGrid.Columns, view?.Rows ?? GamesGrid.Rows);

    /// <summary><c>systems_sort</c> and <c>systems_sort_order</c>: the systems' order (Favourites, Recently played and All games always come first).</summary>
    public SystemsOrdering SystemsSort { get; init; }

    /// <summary><c>games_sort</c> and <c>games_sort_order</c>: a system's games' order, unless the system has its own (<see cref="GamesSortFor"/>).</summary>
    public GamesOrdering GamesSort { get; init; }

    /// <summary>A list's games' order: its own <c>games_sort</c> and <c>games_sort_order</c> where it sets them, else these settings'.</summary>
    public GamesOrdering GamesSortFor(GamesView? view) =>
        new(view?.Sort ?? GamesSort.Sort, view?.Order ?? GamesSort.Order);
}

/// <summary>
/// A list's own view and order, each null where <c>[display]</c>'s applies: a system's (systems.toml) or Favourites' or
/// All games' (<c>[display.favourites]</c>, <c>[display.all_games]</c>), with the same keys.
/// </summary>
/// <param name="Layout"><c>games_layout</c>.</param>
/// <param name="Columns"><c>games_columns</c> (0 automatic).</param>
/// <param name="Rows"><c>games_rows</c> (0 automatic).</param>
/// <param name="Sort"><c>games_sort</c>.</param>
/// <param name="Order"><c>games_sort_order</c>.</param>
public sealed record GamesView(GamesLayout? Layout, int? Columns, int? Rows, GameSort? Sort, SortOrder? Order)
{
    /// <summary>Nothing of its own: <c>[display]</c>'s everything.</summary>
    public static GamesView None { get; } = new(null, null, null, null, null);
}

/// <summary>What the systems are sorted by (<c>[display] systems_sort</c>). Ties are broken by name, A to Z.</summary>
public enum SystemSort
{
    /// <summary><c>"alphabetical"</c>: by name (the default).</summary>
    Alphabetical,

    /// <summary><c>"manufacturer"</c>: by manufacturer, then name.</summary>
    Manufacturer,

    /// <summary><c>"release_year"</c>: by the year it came out, then name.</summary>
    ReleaseYear,

    /// <summary><c>"manufacturer_year"</c>: by manufacturer, then the year it came out, then name.</summary>
    ManufacturerYear,
}

/// <summary>What a system's games are sorted by (<c>[display] games_sort</c>). Ties are broken by title, A to Z.</summary>
public enum GameSort
{
    /// <summary><c>"alphabetical"</c>: by title (the default).</summary>
    Alphabetical,

    /// <summary><c>"last_played"</c>: by when it was last played; games never played come last either way.</summary>
    LastPlayed,

    /// <summary><c>"play_time"</c>: by the time spent playing it (a game never played has none).</summary>
    PlayTime,

    /// <summary><c>"added"</c>: by when its file arrived in the ROM folder (the file's creation time).</summary>
    Added,

    /// <summary><c>"release_date"</c>: by its release date (scraped, or the user's); games without one come last either way.</summary>
    ReleaseDate,
}

/// <summary><c>systems_sort_order</c> and <c>games_sort_order</c>.</summary>
public enum SortOrder
{
    /// <summary><c>"ascending"</c>: A to Z, oldest first, least first (the default).</summary>
    Ascending,

    /// <summary><c>"descending"</c>: Z to A, newest first, most first.</summary>
    Descending,
}

/// <summary>The systems' order: what they're sorted by, and which way.</summary>
public readonly record struct SystemsOrdering(SystemSort Sort, SortOrder Order);

/// <summary>A list of games' order: what they're sorted by, and which way.</summary>
public readonly record struct GamesOrdering(GameSort Sort, SortOrder Order)
{
    /// <summary>The order changes when a game is played.</summary>
    public bool FollowsPlays => Sort is GameSort.LastPlayed or GameSort.PlayTime;
}

/// <summary>The names config uses for the sorts and their orders.</summary>
public static class Sorts
{
    public static IReadOnlyList<string> SystemsNames { get; } = ["alphabetical", "manufacturer", "release_year", "manufacturer_year"];

    public static IReadOnlyList<string> GamesNames { get; } = ["alphabetical", "last_played", "play_time", "added", "release_date"];

    public static IReadOnlyList<string> OrderNames { get; } = ["ascending", "descending"];

    public static string Name(SystemSort sort) => SystemsNames[(int)sort];

    public static string Name(GameSort sort) => GamesNames[(int)sort];

    public static string Name(SortOrder order) => OrderNames[(int)order];

    public static bool TryParse(string name, out SystemSort sort)
    {
        var index = Layouts.IndexOf(SystemsNames, name);
        sort = (SystemSort)Math.Max(index, 0);
        return index >= 0;
    }

    public static bool TryParse(string name, out GameSort sort)
    {
        var index = Layouts.IndexOf(GamesNames, name);
        sort = (GameSort)Math.Max(index, 0);
        return index >= 0;
    }

    public static bool TryParse(string name, out SortOrder order)
    {
        var index = Layouts.IndexOf(OrderNames, name);
        order = (SortOrder)Math.Max(index, 0);
        return index >= 0;
    }
}

/// <summary>How the systems are shown (<c>[display] systems_layout</c>).</summary>
public enum SystemsLayout
{
    /// <summary><c>"grid"</c>: rows and columns of cards (the default).</summary>
    Grid,

    /// <summary><c>"grid_with_labels"</c>: the grid, each card's name under it.</summary>
    GridWithLabels,

    /// <summary><c>"carousel"</c>: one row, the focused card in the middle.</summary>
    Carousel,

    /// <summary><c>"single"</c>: one card at a time, filling the screen; left and right move to the next.</summary>
    Single,

    /// <summary><c>"coverflow"</c>: one row, the focused card facing out in the middle, the others side on.</summary>
    Coverflow,
}

/// <summary>How a system's games are shown (<c>[display] games_layout</c>).</summary>
public enum GamesLayout
{
    /// <summary><c>"grid"</c>: rows and columns of games (the default).</summary>
    Grid,

    /// <summary><c>"grid_with_labels"</c>: the grid, each game's title under it.</summary>
    GridWithLabels,

    /// <summary><c>"carousel"</c>: one row, the focused game in the middle.</summary>
    Carousel,

    /// <summary><c>"list"</c>: the titles in a list, with the focused game's model beside it.</summary>
    List,

    /// <summary><c>"coverflow"</c>: one row, the focused game facing out in the middle, the others showing their spines.</summary>
    Coverflow,

    /// <summary><c>"showcase"</c>: a strip of games along the bottom, the focused game's art and details above it.</summary>
    Showcase,
}

/// <summary>A grid's columns and the rows that fit the screen's height; 0 for either is automatic.</summary>
public readonly record struct GridSize(int Columns, int Rows)
{
    public bool IsAutomatic => Columns == 0 && Rows == 0;
}

/// <summary>The names config uses for the layouts.</summary>
public static class Layouts
{
    public static IReadOnlyList<string> SystemsNames { get; } = ["grid", "grid_with_labels", "carousel", "single", "coverflow"];

    public static IReadOnlyList<string> GamesNames { get; } = ["grid", "grid_with_labels", "carousel", "list", "coverflow", "showcase"];

    public static string Name(SystemsLayout layout) => SystemsNames[(int)layout];

    public static string Name(GamesLayout layout) => GamesNames[(int)layout];

    /// <summary>Whether the layout has rows and columns, so a grid size applies to it.</summary>
    public static bool IsGrid(SystemsLayout layout) => layout is SystemsLayout.Grid or SystemsLayout.GridWithLabels;

    /// <summary>Whether the layout has rows and columns, so a grid size applies to it.</summary>
    public static bool IsGrid(GamesLayout layout) => layout is GamesLayout.Grid or GamesLayout.GridWithLabels;

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

    internal static int IndexOf(IReadOnlyList<string> names, string name)
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

/// <summary><c>[ui]</c>: the status indicators top right, each on or off, the navigation sounds, the controls' button icons and the UI's size.</summary>
/// <param name="ShowClock">The time, in the user's regional short-time format.</param>
/// <param name="ShowBattery">The battery's charge; nothing shows on a device without one.</param>
/// <param name="ShowNetwork">Wi-Fi (with its signal), a cable, or disconnected.</param>
/// <param name="NavigationSounds">A tock when the focus moves to another system or game, and a whoosh when a system is entered (2026-10-10); on by default.</param>
/// <param name="ButtonIcons">Which buttons the controls' hints show (2026-11-05): the last device used's, or one kind always.</param>
/// <param name="Size">The size of the whole 2D UI (2026-11-05): menus, text and the controls' hints.</param>
public sealed record UiSettings(
    bool ShowClock = true, bool ShowBattery = true, bool ShowNetwork = true, bool NavigationSounds = true,
    ButtonIcons ButtonIcons = ButtonIcons.Automatic, UiSize Size = UiSize.Medium);

/// <summary>
/// The size of the whole 2D UI (<c>[ui] size</c>, docs/ARCHITECTURE.md A1 "UI size"): smaller for a desk's monitor at arm's
/// length, larger for a handheld's small screen or a television across the room. The 3D grids keep their size.
/// </summary>
public enum UiSize
{
    Small,
    Medium,
    Large,
}

/// <summary>
/// The buttons the controls' hints show (<c>[ui] button_icons</c>, docs/ARCHITECTURE.md A1 "Button icons"): automatically
/// those of the device last used, or one kind always (Steam Input, say, shows every pad as an Xbox 360 pad). The app's
/// current kind is one of the others, never <see cref="Automatic"/>.
/// </summary>
public enum ButtonIcons
{
    Automatic,
    Xbox,
    PlayStation,

    /// <summary>A Switch's (and a Switch 2's, the same buttons).</summary>
    Nintendo,
    GameCube,

    /// <summary>The Steam Deck's, and the new Steam Controller's (the same buttons).</summary>
    SteamDeck,

    /// <summary>The 2015 Steam Controller's.</summary>
    SteamController,
    Keyboard,
}

/// <summary>How the window fills the screen (<c>[display] screen_mode</c>).</summary>
public enum ScreenMode
{
    /// <summary><c>"borderless"</c>: a borderless window covering the screen (the default; Godot's <c>Fullscreen</c>).</summary>
    Borderless,

    /// <summary><c>"fullscreen"</c>: exclusive fullscreen, at the desktop's resolution (Godot can't change the display mode).</summary>
    Fullscreen,

    /// <summary><c>"windowed"</c>: a window of <see cref="DisplaySettings.WindowSize"/>.</summary>
    Windowed,
}

/// <summary>The rendering drivers <c>[display] rendering_driver</c> can choose.</summary>
public enum RenderingDriver
{
    /// <summary><c>"d3d12"</c>: Direct3D 12 (the default; M1).</summary>
    D3D12,

    /// <summary><c>"vulkan"</c>: Vulkan.</summary>
    Vulkan,
}

/// <summary>The names config uses for the screen modes and the rendering drivers.</summary>
public static class DisplayNames
{
    public static IReadOnlyList<string> ScreenModes { get; } = ["borderless", "fullscreen", "windowed"];

    /// <summary><c>[ui] button_icons</c>' values, in <see cref="ButtonIcons"/>' order.</summary>
    public static IReadOnlyList<string> ButtonIcons { get; } = ["automatic", "xbox", "playstation", "nintendo", "gamecube", "steamdeck", "steamcontroller", "keyboard"];

    /// <summary><c>[ui] size</c>'s values, in <see cref="UiSize"/>'s order.</summary>
    public static IReadOnlyList<string> UiSizes { get; } = ["small", "medium", "large"];

    /// <summary>As Godot names them (<c>RenderingServer.GetCurrentRenderingDriverName()</c>, <c>--rendering-driver</c>).</summary>
    public static IReadOnlyList<string> RenderingDrivers { get; } = ["d3d12", "vulkan"];

    public static string Name(ScreenMode mode) => ScreenModes[(int)mode];

    public static string Name(RenderingDriver driver) => RenderingDrivers[(int)driver];

    public static string Name(ButtonIcons icons) => ButtonIcons[(int)icons];

    public static string Name(UiSize size) => UiSizes[(int)size];

    public static bool TryParse(string name, out RenderingDriver driver)
    {
        var index = Layouts.IndexOf(RenderingDrivers, name);
        driver = (RenderingDriver)Math.Max(index, 0);
        return index >= 0;
    }
}

/// <summary>
/// The height the 3D renders at (<c>[display] render_resolution</c>): <c>"auto"</c> (at most <see cref="AutomaticCap"/>,
/// A3), <c>"native"</c>, or a height in pixels. Never more than the window's.
/// </summary>
public readonly record struct RenderResolution(int Height)
{
    /// <summary>The automatic setting's most: 1080p, so a 4K screen renders its 3D at half resolution (A3).</summary>
    public const int AutomaticCap = 1080;

    public const int MinHeight = 240;

    public const int MaxHeight = 4320;

    /// <summary>The heights the settings page offers (those under the screen's).</summary>
    public static IReadOnlyList<int> Presets { get; } = [720, 900, 1080, 1440, 2160];

    public static RenderResolution Automatic => default;

    public static RenderResolution Native { get; } = new(-1);

    public bool IsAutomatic => Height == 0;

    public bool IsNative => Height < 0;

    /// <summary>The 3D scale for a window <paramref name="windowHeight"/> pixels high: at most 1.</summary>
    public double ScaleFor(int windowHeight)
    {
        if (windowHeight <= 0 || IsNative)
        {
            return 1;
        }

        var height = IsAutomatic ? AutomaticCap : Height;
        return height >= windowHeight ? 1 : (double)height / windowHeight;
    }

    /// <summary>What settings.toml says: <c>"auto"</c>, <c>"native"</c>, or the height as an integer.</summary>
    public object ConfigValue => IsAutomatic ? "auto" : IsNative ? "native" : (long)Height;
}

/// <summary>A window's size in pixels (<c>[display] window_size</c>, written <c>"1280x800"</c>).</summary>
public readonly record struct WindowSize(int Width, int Height)
{
    public const int MinWidth = 640;

    public const int MinHeight = 360;

    public const int MaxSide = 7680;

    public static WindowSize Default { get; } = new(1280, 800);

    /// <summary>The sizes the settings page offers (those that fit the screen).</summary>
    public static IReadOnlyList<WindowSize> Presets { get; } =
        [new(1280, 720), new(1280, 800), new(1600, 900), new(1920, 1080), new(2560, 1440), new(3840, 2160)];

    public override string ToString() => string.Create(CultureInfo.InvariantCulture, $"{Width}x{Height}");

    /// <summary><c>"1280x800"</c> (an <c>x</c>, <c>X</c> or <c>×</c> between), within the limits.</summary>
    public static bool TryParse(string text, out WindowSize size)
    {
        size = default;
        var x = text.AsSpan().IndexOfAny('x', 'X', '×');
        if (x <= 0
            || !int.TryParse(text.AsSpan(0, x).Trim(), NumberStyles.None, CultureInfo.InvariantCulture, out var width)
            || !int.TryParse(text.AsSpan(x + 1).Trim(), NumberStyles.None, CultureInfo.InvariantCulture, out var height)
            || width < MinWidth || height < MinHeight || width > MaxSide || height > MaxSide)
        {
            return false;
        }

        size = new WindowSize(width, height);
        return true;
    }
}

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
/// <param name="LaunchBoxPlatforms">
/// <c>launchbox_platforms</c>: the LaunchBox Games DB platforms (their names, as LaunchBox writes them) searched for this
/// system's games; null or empty skips LaunchBox.
/// </param>
/// <param name="GameModel">
/// <c>game_model</c>: a game template id the user chose for this system, looked up in the active theme and then the
/// built-in one (A7). Null when unset: the theme decides.
/// </param>
/// <param name="GamesLayout"><c>games_layout</c>: how this system's games are shown; null uses <c>[display] games_layout</c>.</param>
/// <param name="GamesColumns"><c>games_columns</c>: the system's games grid's columns (0 automatic); null uses <c>[display] games_columns</c>.</param>
/// <param name="GamesRows"><c>games_rows</c>: the rows of its games grid that fit the screen (0 automatic); null uses <c>[display] games_rows</c>.</param>
/// <param name="GamesSort"><c>games_sort</c>: what its games are sorted by; null uses <c>[display] games_sort</c>.</param>
/// <param name="GamesSortOrder"><c>games_sort_order</c>: which way; null uses <c>[display] games_sort_order</c>.</param>
/// <param name="Description"><c>description</c>: a paragraph about the system, shown in its details; null when there's none.</param>
/// <param name="AutoConfigureControllers">
/// <c>auto_configure_controllers</c>: before each launch, the connected pads are set up in the emulator's own config,
/// when its profile says how (<see cref="EmulatorConfig.Controllers"/>).
/// </param>
/// <param name="SwapFaceButtons">
/// <c>swap_ab_xy</c>: with <paramref name="AutoConfigureControllers"/>, a pad not labelled as a Switch's (an Xbox pad)
/// gets A/B and X/Y switched, so the button labelled A is the Switch's A. False keeps the Switch's positions.
/// </param>
/// <param name="Group">
/// <c>group</c> (2026-11-03): the system whose card this system's games show under while <c>group_systems</c> is on
/// (A5 Grouped systems); null when it has its own card. Checked by the loader: an enabled system that isn't grouped itself.
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
    bool SteamStore = false,
    int? GamesColumns = null,
    int? GamesRows = null,
    GamesLayout? GamesLayout = null,
    GameSort? GamesSort = null,
    SortOrder? GamesSortOrder = null,
    string? Description = null,
    bool AutoConfigureControllers = false,
    bool SwapFaceButtons = false,
    IReadOnlyList<string>? LaunchBoxPlatforms = null,
    string? Group = null)
{
    /// <summary>Its own games view and order (<c>games_layout</c> and the rest), for <see cref="DisplaySettings.GamesLayoutFor"/> and the others.</summary>
    public GamesView View => new(GamesLayout, GamesColumns, GamesRows, GamesSort, GamesSortOrder);

    /// <summary>
    /// The built-in definition's <c>emulator</c>, when it's a configured profile; null for a system the user defined, or
    /// one whose built-in emulator is gone. It's <see cref="Emulator"/> unless the user chose another.
    /// </summary>
    public string? DefaultEmulator { get; init; }

    /// <summary>
    /// The built-in definition's <c>group</c> (a regional variant's system), whether or not the user took it out with
    /// <c>group = ""</c>; null for a system that isn't grouped by default.
    /// </summary>
    public string? DefaultGroup { get; init; }

    /// <summary>
    /// The emulators the system offers, each once: its default (the built-in one, else its own), its alternatives,
    /// then the one it uses if that's neither (a profile the user named in systems.toml).
    /// </summary>
    public IReadOnlyList<string> OfferedEmulators()
    {
        var offered = new List<string>(AltEmulators.Count + 2) { DefaultEmulator ?? Emulator };
        foreach (var alt in AltEmulators)
        {
            if (!offered.Contains(alt))
            {
                offered.Add(alt);
            }
        }

        if (!offered.Contains(Emulator))
        {
            offered.Add(Emulator);
        }

        return offered;
    }
}

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
/// <param name="Controllers">
/// <c>controllers</c>: how the launcher sets up the connected pads in this emulator's config before a launch, for
/// systems with <c>auto_configure_controllers</c>. Only <c>"eden"</c> (<see cref="Launching.Controllers.EdenControllers"/>);
/// null when the emulator isn't set up.
/// </param>
/// <param name="Installs">
/// <c>installs</c>: the emulator runs games installed in its own storage, so the launcher boots one installed there
/// with <paramref name="Args"/>, and gives one that isn't to <paramref name="InstallArgs"/>. Only <c>"vita3k"</c>
/// (<see cref="Launching.Vita3KGames"/>, which knows where Vita3K keeps them); null for every other emulator.
/// </param>
/// <param name="InstallArgs">
/// <c>install_args</c>, templates like <paramref name="Args"/>: a game that isn't installed yet is launched with these,
/// so the emulator installs it and then runs it. Only with <paramref name="Installs"/>; null when the profile has none,
/// and then such a game can't be launched until it's installed.
/// </param>
/// <param name="Programs">
/// Every place <c>executable</c> lists, expanded, when it lists more than one (a list, or a list variable such as
/// Linux's <c>{retroarch}</c>); null for one place.
/// </param>
/// <param name="Cores">Every place <c>core</c> lists, as <paramref name="Programs"/>.</param>
/// <param name="ProgramVariable">
/// The list variable <c>executable</c> is made of when it's a single entry using one (Linux's <c>{retroarch}</c>), so
/// the settings can point every profile sharing it at another program by changing the variable.
/// </param>
public sealed record EmulatorConfig(
    string Id,
    string Name,
    string Executable,
    IReadOnlyList<string> Args,
    string WorkingDir,
    string? Core = null,
    bool RunFile = false,
    string? Controllers = null,
    string? Installs = null,
    IReadOnlyList<string>? InstallArgs = null,
    IReadOnlyList<string>? Programs = null,
    IReadOnlyList<string>? Cores = null,
    string? ProgramVariable = null)
{
    /// <summary>
    /// Where the program is looked for, in order (A5 Finding programs): <see cref="Programs"/> when
    /// <c>executable</c> lists more than one place, else <see cref="Executable"/> alone. <see cref="Executable"/> is the
    /// first place until <see cref="Launching.ProgramSearch"/> has found the program.
    /// </summary>
    public IReadOnlyList<string> ProgramPlaces => Programs ?? [Executable];

    /// <summary>Where the core is looked for, as <see cref="ProgramPlaces"/>; null without a core.</summary>
    public IReadOnlyList<string>? CorePlaces => Cores ?? (Core is null ? null : [Core]);

    /// <summary>What the settings screens show where a profile's program goes.</summary>
    public string ProgramText => RunFile
        ? "Runs the game's own file"
        : Programs is { Count: > 1 } places ? $"{places[0]}, or {places.Count - 1} more places" : Executable;
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
