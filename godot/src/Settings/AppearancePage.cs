using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Theming;

namespace Launcher.App.Settings;

/// <summary>
/// Settings, Appearance (the Layout page until 2026-11-07, with the theme and which systems show moved in from the main
/// page): the theme, chosen from a list and applied at once, and the theme downloader. Then how the systems and the
/// games are shown (<c>[display]</c> in settings.toml): whether systems without games have a card and whether regional
/// variants show in their system's (A5 Grouped systems); the systems as a grid, a grid with
/// labels, a carousel, one at a time or a coverflow; the games as a grid, a grid with labels, a carousel, a list with
/// the focused game's model beside it, a coverflow or a showcase; each grid's columns and rows (automatic, or a number); and the order of each (what they're sorted by, and which way). A changes a row
/// through a list; left and right step through its values. Each change is saved at once, and the grid behind shows
/// it. A system's own games view, grid size and order are on its page (X on it).
/// </summary>
public sealed partial class AppearancePage : ListPanel
{
    private readonly SettingsController _settings;
    private readonly SettingRow _theme;
    private readonly SettingRow _emptySystems;
    private readonly SettingRow _groupSystems;
    private readonly SettingRow _systems;
    private readonly SettingRow _systemsColumns;
    private readonly SettingRow _systemsRows;
    private readonly SettingRow _games;
    private readonly SettingRow _gamesColumns;
    private readonly SettingRow _gamesRows;
    private readonly SettingRow _systemsSort;
    private readonly SettingRow _systemsOrder;
    private readonly SettingRow _gamesSort;
    private readonly SettingRow _gamesOrder;

    // Values saved but not yet applied, so presses in quick succession step on from each other.
    private readonly Dictionary<string, object> _pending = new(StringComparer.Ordinal);

    public AppearancePage(SettingsController settings)
        : base("Appearance")
    {
        _settings = settings;
        Subtitle = "The theme, and how the systems and games are shown";

        AddSection("Theme");
        _theme = AddRow("Theme", "Its system cards, game boxes, background and menus", activated: ChooseTheme);
        AddRow("Download themes", "Themes made for Odyssey Launcher: get them, keep them up to date, or remove them",
            activated: () => Layer.Push(new ThemeDownloaderPage(_settings)));

        AddSection("Systems");
        _emptySystems = AddRow("Show systems without games", "A card for every system, even one with nothing in its ROM folders",
            activated: () => SetShowEmptySystems(null));
        _emptySystems.Adjuster = direction => SetShowEmptySystems(direction > 0);
        _groupSystems = AddRow("Group regional variants", "A variant's games in its console's card, each in its own box, such as Dreamcast (NA/JP) games in the Dreamcast's card",
            activated: () => SetGroupSystems(null));
        _groupSystems.Adjuster = direction => SetGroupSystems(direction > 0);
        _systems = AddRow("Systems view", activated: () => ChooseLayout("systems_layout", "Systems view", SystemsChoices()));
        _systems.Adjuster = direction => StepLayout("systems_layout", Layouts.SystemsNames, direction);
        _systemsColumns = AddSizeRow("Columns", "systems_columns", DisplaySettings.MaxColumns);
        _systemsRows = AddSizeRow("Rows", "systems_rows", DisplaySettings.MaxRows);
        _systemsSort = AddSortRow("Sort by", "systems_sort", "Sort systems by", Sorts.SystemsNames, () => SystemsSortChoices());
        _systemsOrder = AddSortRow("Order", "systems_sort_order", "Systems' order", Sorts.OrderNames,
            () => OrderChoices(sort => SystemsOrderDetail((SystemSort)Current("systems_sort", (int)Display.SystemsSort.Sort), sort)));
        AddNote("Favourites, Recently played and All games always come first. All games follows the games' sort.");

        AddSection("Games");
        _games = AddRow("Games view", activated: () => ChooseLayout("games_layout", "Games view", GamesChoices()));
        _games.Adjuster = direction => StepLayout("games_layout", Layouts.GamesNames, direction);
        _gamesColumns = AddSizeRow("Columns", "games_columns", DisplaySettings.MaxColumns);
        _gamesRows = AddSizeRow("Rows", "games_rows", DisplaySettings.MaxRows);
        _gamesSort = AddSortRow("Sort by", "games_sort", "Sort games by", Sorts.GamesNames, () => GamesSortChoices());
        _gamesOrder = AddSortRow("Order", "games_sort_order", "Games' order", Sorts.OrderNames,
            () => OrderChoices(sort => GamesOrderDetail((GameSort)Current("games_sort", (int)Display.GamesSort.Sort), sort)));
        AddNote("A system can have its own view, columns, rows and order: press X on it in the systems view, or choose it in Settings > Systems.");

        SetHints(CommonHints.ChooseChangeBack);
        _settings.ConfigApplied += OnConfigApplied;
        Refresh();
    }

    public override void OnRevealed() => Refresh();

    public override void OnClosed() => _settings.ConfigApplied -= OnConfigApplied;

    private void OnConfigApplied(AppConfig config)
    {
        _pending.Clear();
        Refresh();
    }

    private DisplaySettings Display => _settings.Services.Config.Settings.Display;

    private void Refresh()
    {
        var display = Display;
        _theme.Value = _settings.Services.Theme?.Active.Name ?? display.Theme;
        ShowToggle(_emptySystems, !display.HideEmptySystems);
        ShowToggle(_groupSystems, display.GroupSystems);
        var systems = (SystemsLayout)Current("systems_layout", (int)display.SystemsLayout);
        var games = (GamesLayout)Current("games_layout", (int)display.GamesLayout);
        _systems.Value = SystemsTitle(systems);
        _systems.Detail = SystemsDetail(systems);
        _games.Value = GamesTitle(games);
        _games.Detail = GamesDetail(games);
        ShowSize(_systemsColumns, Current("systems_columns", display.SystemsGrid.Columns), Layouts.IsGrid(systems), "columns");
        ShowSize(_systemsRows, Current("systems_rows", display.SystemsGrid.Rows), Layouts.IsGrid(systems), "rows");
        ShowSize(_gamesColumns, Current("games_columns", display.GamesGrid.Columns), Layouts.IsGrid(games), "columns");
        ShowSize(_gamesRows, Current("games_rows", display.GamesGrid.Rows), Layouts.IsGrid(games), "rows");
        var systemsSort = (SystemSort)Current("systems_sort", (int)display.SystemsSort.Sort);
        var systemsOrder = (SortOrder)Current("systems_sort_order", (int)display.SystemsSort.Order);
        _systemsSort.Value = SystemsSortTitle(systemsSort);
        _systemsSort.Detail = SystemsSortDetail(systemsSort);
        _systemsOrder.Value = OrderTitle(systemsOrder);
        _systemsOrder.Detail = SystemsOrderDetail(systemsSort, systemsOrder);
        var gamesSort = (GameSort)Current("games_sort", (int)display.GamesSort.Sort);
        var gamesOrder = (SortOrder)Current("games_sort_order", (int)display.GamesSort.Order);
        _gamesSort.Value = GamesSortTitle(gamesSort);
        _gamesSort.Detail = GamesSortDetail(gamesSort);
        _gamesOrder.Value = OrderTitle(gamesOrder);
        _gamesOrder.Detail = GamesOrderDetail(gamesSort, gamesOrder);
    }

    private int Current(string key, int saved) => _pending.TryGetValue(key, out var value) ? Convert.ToInt32(value, CultureInfo.InvariantCulture) : saved;

    private static void ShowSize(SettingRow row, int value, bool used, string what)
    {
        row.Value = SizeText(value);
        row.ValueColour = used ? UiStyle.Accent : UiStyle.Faint;
        row.Detail = !used
            ? "Only for the grid views"
            : value == 0
                ? $"As many {what} as fit the screen"
                : what == "rows" ? $"{value} row{(value == 1 ? string.Empty : "s")} fill the screen's height" : $"{value} across";
    }

    // ---- Layouts --------------------------------------------------------------------------------------

    public static string SystemsTitle(SystemsLayout layout) => layout switch
    {
        SystemsLayout.GridWithLabels => "Grid with labels",
        SystemsLayout.Carousel => "Carousel",
        SystemsLayout.Single => "One at a time",
        SystemsLayout.Coverflow => "Coverflow",
        _ => "Grid",
    };

    private static string SystemsDetail(SystemsLayout layout) => layout switch
    {
        SystemsLayout.GridWithLabels => "Rows and columns of systems, each one's name under it",
        SystemsLayout.Carousel => "One row, the focused system in the middle",
        SystemsLayout.Single => "One system fills the screen; left and right go to the next",
        SystemsLayout.Coverflow => "One row, the focused system facing you, the others side on",
        _ => "Rows and columns of systems",
    };

    public static string GamesTitle(GamesLayout layout) => layout switch
    {
        GamesLayout.GridWithLabels => "Grid with labels",
        GamesLayout.Carousel => "Carousel",
        GamesLayout.List => "List",
        GamesLayout.Coverflow => "Coverflow",
        GamesLayout.Showcase => "Showcase",
        _ => "Grid",
    };

    public static string GamesDetail(GamesLayout layout) => layout switch
    {
        GamesLayout.GridWithLabels => "Rows and columns of games, each one's title under it",
        GamesLayout.Carousel => "One row, the focused game in the middle",
        GamesLayout.List => "The titles in a list, the focused game's model beside it",
        GamesLayout.Coverflow => "One row of spines, the focused game turned to face you",
        GamesLayout.Showcase => "A strip of games, the focused game's art and details above it",
        _ => "Rows and columns of games",
    };

    private static List<Choice> SystemsChoices()
    {
        var choices = new List<Choice>();
        foreach (var layout in Enum.GetValues<SystemsLayout>())
        {
            choices.Add(new Choice(Layouts.Name(layout), SystemsTitle(layout), SystemsDetail(layout)));
        }

        return choices;
    }

    private static List<Choice> GamesChoices()
    {
        var choices = new List<Choice>();
        foreach (var layout in Enum.GetValues<GamesLayout>())
        {
            choices.Add(new Choice(Layouts.Name(layout), GamesTitle(layout), GamesDetail(layout)));
        }

        return choices;
    }

    private void ChooseLayout(string key, string title, List<Choice> choices)
    {
        var display = Display;
        var current = key == "systems_layout"
            ? Layouts.Name((SystemsLayout)Current(key, (int)display.SystemsLayout))
            : Layouts.Name((GamesLayout)Current(key, (int)display.GamesLayout));
        Layer.Push(new ChoicePanel(title, null, choices, current, choice =>
            Save(key, Index(key, choice.Id), choice.Id, $"{title}: {choice.Title}.")));
    }

    private void StepLayout(string key, IReadOnlyList<string> names, int direction)
    {
        var display = Display;
        var current = Current(key, key == "systems_layout" ? (int)display.SystemsLayout : (int)display.GamesLayout);
        var next = Math.Clamp(current + Math.Sign(direction), 0, names.Count - 1);
        if (next != current)
        {
            var title = key == "systems_layout" ? $"Systems view: {SystemsTitle((SystemsLayout)next)}." : $"Games view: {GamesTitle((GamesLayout)next)}.";
            Save(key, next, names[next], title);
        }
    }

    private static int Index(string key, string name) =>
        key == "systems_layout"
            ? Layouts.TryParse(name, out SystemsLayout systems) ? (int)systems : 0
            : Layouts.TryParse(name, out GamesLayout games) ? (int)games : 0;

    // ---- Sorting --------------------------------------------------------------------------------------

    public static string SystemsSortTitle(SystemSort sort) => sort switch
    {
        SystemSort.Manufacturer => "Manufacturer",
        SystemSort.ReleaseYear => "Release year",
        SystemSort.ManufacturerYear => "Manufacturer, then year",
        _ => "Alphabetical",
    };

    public static string SystemsSortDetail(SystemSort sort) => sort switch
    {
        SystemSort.Manufacturer => "Each manufacturer's systems together, by name",
        SystemSort.ReleaseYear => "By the year each came out; those without one come last",
        SystemSort.ManufacturerYear => "Each manufacturer's systems together, by the year each came out",
        _ => "By name",
    };

    public static string GamesSortTitle(GameSort sort) => sort switch
    {
        GameSort.LastPlayed => "Last played",
        GameSort.PlayTime => "Time played",
        GameSort.Added => "Date added",
        GameSort.ReleaseDate => "Release date",
        _ => "Alphabetical",
    };

    public static string GamesSortDetail(GameSort sort) => sort switch
    {
        GameSort.LastPlayed => "When each was last played; games never played come last",
        GameSort.PlayTime => "The time spent playing each one",
        GameSort.Added => "When each game's file arrived in the ROM folder",
        GameSort.ReleaseDate => "Scraped or your own; games without one come last",
        _ => "By title",
    };

    public static string OrderTitle(SortOrder order) => order == SortOrder.Descending ? "Descending" : "Ascending";

    public static string SystemsOrderDetail(SystemSort sort, SortOrder order) => (sort, order) switch
    {
        (SystemSort.ReleaseYear, SortOrder.Descending) => "Newest first",
        (SystemSort.ReleaseYear, _) => "Oldest first",
        (SystemSort.ManufacturerYear, SortOrder.Descending) => "Manufacturers Z to A, newest first",
        (SystemSort.ManufacturerYear, _) => "Manufacturers A to Z, oldest first",
        (_, SortOrder.Descending) => "Z to A",
        _ => "A to Z",
    };

    public static string GamesOrderDetail(GameSort sort, SortOrder order) => (sort, order) switch
    {
        (GameSort.LastPlayed, SortOrder.Descending) => "Most recently played first",
        (GameSort.LastPlayed, _) => "Played longest ago first",
        (GameSort.PlayTime, SortOrder.Descending) => "Most played first",
        (GameSort.PlayTime, _) => "Least played first",
        (GameSort.Added or GameSort.ReleaseDate, SortOrder.Descending) => "Newest first",
        (GameSort.Added or GameSort.ReleaseDate, _) => "Oldest first",
        (_, SortOrder.Descending) => "Z to A",
        _ => "A to Z",
    };

    public static List<Choice> SystemsSortChoices()
    {
        var choices = new List<Choice>();
        foreach (var sort in Enum.GetValues<SystemSort>())
        {
            choices.Add(new Choice(Sorts.Name(sort), SystemsSortTitle(sort), SystemsSortDetail(sort)));
        }

        return choices;
    }

    public static List<Choice> GamesSortChoices()
    {
        var choices = new List<Choice>();
        foreach (var sort in Enum.GetValues<GameSort>())
        {
            choices.Add(new Choice(Sorts.Name(sort), GamesSortTitle(sort), GamesSortDetail(sort)));
        }

        return choices;
    }

    /// <param name="detail">What each order means for the sort chosen.</param>
    public static List<Choice> OrderChoices(Func<SortOrder, string> detail)
    {
        var choices = new List<Choice>();
        foreach (var order in Enum.GetValues<SortOrder>())
        {
            choices.Add(new Choice(Sorts.Name(order), OrderTitle(order), detail(order)));
        }

        return choices;
    }

    /// <summary>A sort or an order: A chooses from a list, left and right step through the values.</summary>
    private SettingRow AddSortRow(string title, string key, string pickerTitle, IReadOnlyList<string> names, Func<List<Choice>> choices)
    {
        var row = AddRow(title, activated: () =>
            Layer.Push(new ChoicePanel(pickerTitle, null, choices(), names[SortOf(key)], choice =>
                Save(key, IndexOf(names, choice.Id), choice.Id, $"{pickerTitle}: {choice.Title}."))));
        row.Adjuster = direction =>
        {
            var current = SortOf(key);
            var next = Math.Clamp(current + Math.Sign(direction), 0, names.Count - 1);
            if (next != current)
            {
                Save(key, next, names[next], $"{pickerTitle}: {choices()[next].Title}.");
            }
        };
        return row;
    }

    private int SortOf(string key)
    {
        var display = Display;
        return Current(key, key switch
        {
            "systems_sort" => (int)display.SystemsSort.Sort,
            "systems_sort_order" => (int)display.SystemsSort.Order,
            "games_sort" => (int)display.GamesSort.Sort,
            _ => (int)display.GamesSort.Order,
        });
    }

    private static int IndexOf(IReadOnlyList<string> names, string name)
    {
        for (var i = 0; i < names.Count; i++)
        {
            if (names[i] == name)
            {
                return i;
            }
        }

        return 0;
    }

    // ---- Sizes ----------------------------------------------------------------------------------------

    /// <summary>"Automatic", or the number.</summary>
    public static string SizeText(int value) => value == 0 ? "Automatic" : value.ToString(CultureInfo.InvariantCulture);

    /// <summary>Automatic, then 1 to <paramref name="max"/>.</summary>
    public static List<Choice> SizeChoices(int max, string what)
    {
        var choices = new List<Choice> { new("0", "Automatic", $"As many {what} as fit the screen") };
        for (var i = 1; i <= max; i++)
        {
            choices.Add(new Choice(i.ToString(CultureInfo.InvariantCulture), i.ToString(CultureInfo.InvariantCulture)));
        }

        return choices;
    }

    private SettingRow AddSizeRow(string title, string key, int max)
    {
        var what = key.EndsWith("rows", StringComparison.Ordinal) ? "rows" : "columns";
        var row = AddRow(title, activated: () =>
            Layer.Push(new ChoicePanel(title, null, SizeChoices(max, what), SizeOf(key).ToString(CultureInfo.InvariantCulture), choice =>
            {
                var value = int.Parse(choice.Id, CultureInfo.InvariantCulture);
                Save(key, value, (long)value, $"{title}: {SizeText(value)}.");
            })));
        row.Adjuster = direction =>
        {
            var current = SizeOf(key);
            var next = Math.Clamp(current + Math.Sign(direction), 0, max);
            if (next != current)
            {
                Save(key, next, (long)next, $"{title}: {SizeText(next)}.");
            }
        };
        return row;
    }

    private int SizeOf(string key)
    {
        var display = Display;
        return Current(key, key switch
        {
            "systems_columns" => display.SystemsGrid.Columns,
            "systems_rows" => display.SystemsGrid.Rows,
            "games_columns" => display.GamesGrid.Columns,
            _ => display.GamesGrid.Rows,
        });
    }

    /// <param name="current">The new value as this page reads it back (a layout's index, a size).</param>
    /// <param name="value">What's written to settings.toml.</param>
    private void Save(string key, int current, object value, string saved)
    {
        _pending[key] = current;
        Refresh();
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["display", key], value)], saved);
    }

    // ---- Theme ----------------------------------------------------------------------------------------

    private void ChooseTheme()
    {
        var services = _settings.Services;
        var current = services.Theme?.Active.Id ?? services.Config.Settings.Display.Theme;
        ShowStatus("Reading the themes…", UiStyle.Dim);
        var builtIns = services.BuiltInThemes;
        var themesDir = Path.Combine(services.Paths.ConfigDir, ThemeLoader.FolderName);
        _ = Task.Run(() =>
        {
            // Each theme's name, from its manifest (user themes replace built-in ones with the same id).
            var names = new SortedDictionary<string, (string Name, string Where)>(StringComparer.Ordinal);
            // The base theme isn't one to choose: every theme builds on it.
            foreach (var source in builtIns)
            {
                if (source.Id != ThemeCatalog.BaseId)
                {
                    names[source.Id] = (NameOf(source.Manifest.Text, source.Id), "Built in");
                }
            }

            foreach (var source in ThemeCatalog.UserSources(themesDir, []))
            {
                names[source.Id] = (NameOf(source.Manifest.Text, source.Id), source.Folder);
            }

            var choices = names.Select(n => new Choice(n.Key, n.Value.Name, n.Key == ThemeCatalog.DefaultId && n.Value.Where == "Built in" ? "Built in; the default" : n.Value.Where)).ToList();
            _settings.Ui.Queue.Post(() =>
            {
                ShowStatus(null);
                if (Layer?.Top != this)
                {
                    return;
                }

                Layer.Push(new ChoicePanel("Theme", "Applied at once", choices, current, choice =>
                    _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["display", "theme"], choice.Id)], $"Theme: {choice.Title}. Loading it now…")));
            });
        });
    }

    private static string NameOf(string manifest, string id) =>
        TomlEditor.Parse(manifest, id, out _)?.Get(["name"]) as string ?? id;

    // ---- Which systems show ---------------------------------------------------------------------------

    private static void ShowToggle(SettingRow row, bool on)
    {
        row.Value = on ? "Yes" : "No";
        row.ValueColour = on ? UiStyle.Good : UiStyle.Faint;
    }

    /// <param name="on">Shown or not; null turns it the other way. It's saved the other way round, as <c>[display] hide_empty_systems</c>.</param>
    private void SetShowEmptySystems(bool? on)
    {
        var current = !Display.HideEmptySystems;
        var wanted = on ?? !current;
        if (current == wanted)
        {
            return;
        }

        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["display", "hide_empty_systems"], !wanted)],
            wanted ? "Every system has a card now, with games or not." : "Systems without games are hidden.");
    }

    /// <param name="on">Grouped or not; null turns it the other way. It's saved as <c>[display] group_systems</c> (A5 Grouped systems).</param>
    private void SetGroupSystems(bool? on)
    {
        var current = Display.GroupSystems;
        var wanted = on ?? !current;
        if (current == wanted)
        {
            return;
        }

        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["display", "group_systems"], wanted)],
            wanted ? "Regional variants show in their console's card." : "Every regional variant has a card of its own.");
    }

    // ---- Summary --------------------------------------------------------------------------------------

    /// <summary>The layouts, for the settings' Appearance row: "Systems: Grid · Games: Grid (5 columns, automatic rows)".</summary>
    public static string LayoutSummary(DisplaySettings display) =>
        $"Systems: {SystemsTitle(display.SystemsLayout)}{GridSummary(Layouts.IsGrid(display.SystemsLayout), display.SystemsGrid)} · Games: {GamesTitle(display.GamesLayout)}{GridSummary(Layouts.IsGrid(display.GamesLayout), display.GamesGrid)}";

    /// <summary>A grid's size after its layout's name, when it isn't automatic: " (5 columns, automatic rows)".</summary>
    private static string GridSummary(bool grid, GridSize size) =>
        !grid || size.IsAutomatic
            ? string.Empty
            : $" ({Count(size.Columns, "column")}, {Count(size.Rows, "row")})";

    private static string Count(int value, string what) =>
        value == 0 ? $"automatic {what}s" : value == 1 ? $"1 {what}" : $"{value} {what}s";
}
