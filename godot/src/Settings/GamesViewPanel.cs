using System;
using System.Collections.Generic;
using System.Globalization;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Config;

namespace Launcher.App.Settings;

/// <summary>
/// A page with a list's "Games view" rows (M7): its own view, grid columns and rows, sort and order, each "As in
/// Settings" (the Appearance page's) until it has its own. A choice saves at once; left and right step; Y goes back to
/// the Appearance page's. A system's page keeps them in systems.toml's <c>[systems.&lt;id&gt;]</c>, Favourites' and All
/// games' in settings.toml's <c>[display.favourites]</c> and <c>[display.all_games]</c> (2026-11-10).
/// </summary>
public abstract partial class GamesViewPanel : ListPanel
{
    private readonly SettingsController _settings;
    private readonly ConfigFileKind _file;
    private readonly string[] _table;
    private string _owner = string.Empty;
    private SettingRow? _view;
    private SettingRow? _columns;
    private SettingRow? _rows;
    private SettingRow? _sort;
    private SettingRow? _order;

    /// <param name="table">The table its keys go in: <c>["systems", id]</c> or <c>["display", id]</c>.</param>
    protected GamesViewPanel(string title, SettingsController settings, ConfigFileKind file, string[] table)
        : base(title)
    {
        _settings = settings;
        _file = file;
        _table = table;
    }

    /// <summary>
    /// Adds the rows for <paramref name="own"/>, the list's own settings. <paramref name="owner"/> is the list's name as a
    /// possessive ("Mega Drive's", "Favourites'"), for the messages and the choices' titles.
    /// </summary>
    protected void AddGamesViewRows(string owner, GamesView own)
    {
        _owner = owner;
        var display = _settings.Services.Config.Settings.Display;
        _view = AddViewRow(own.Layout, display.GamesLayout);
        _columns = AddGridRow("Columns", "games_columns", DisplaySettings.MaxColumns, own.Columns, display.GamesGrid.Columns);
        _rows = AddGridRow("Rows", "games_rows", DisplaySettings.MaxRows, own.Rows, display.GamesGrid.Rows);
        if (!Layouts.IsGrid(display.GamesLayoutFor(own)))
        {
            AddNote("Columns and rows are for the grid views.");
        }

        var sortedBy = display.GamesSortFor(own).Sort;
        _sort = AddSortRow("Sort by", "games_sort", Sorts.GamesNames, (int?)own.Sort, (int)display.GamesSort.Sort,
            i => AppearancePage.GamesSortTitle((GameSort)i), i => AppearancePage.GamesSortDetail((GameSort)i));
        _order = AddSortRow("Order", "games_sort_order", Sorts.OrderNames, (int?)own.Order, (int)display.GamesSort.Order,
            i => AppearancePage.OrderTitle((SortOrder)i), i => AppearancePage.GamesOrderDetail(sortedBy, (SortOrder)i));
    }

    /// <summary>Y on one of the rows: that setting goes back to the Appearance page's. False when the focus is elsewhere.</summary>
    protected bool ResetGamesView(Control? focused)
    {
        if (focused is null)
        {
            return false;
        }

        if (focused == _view)
        {
            SaveView(null);
        }
        else if (focused == _columns || focused == _rows)
        {
            SaveGrid(focused == _columns ? "games_columns" : "games_rows", null);
        }
        else if (focused == _sort || focused == _order)
        {
            SaveSort(focused == _sort ? "games_sort" : "games_sort_order", null, null);
        }
        else
        {
            return false;
        }

        return true;
    }

    private ConfigEdit Edit(string key, object? value) => new(_file, [.. _table, key], value);

    /// <summary>
    /// How the list's games are shown: its own <c>games_layout</c>, or the Appearance page's when unset (the default).
    /// A chooses, left and right step through Default, Grid, Grid with labels, Carousel, List, Coverflow and Showcase, Y goes back to the default.
    /// </summary>
    private SettingRow AddViewRow(GamesLayout? own, GamesLayout settings)
    {
        var inherited = AppearancePage.GamesTitle(settings).ToLowerInvariant();
        var row = AddRow("View", own is null ? $"As in Settings: {inherited}" : $"Its own · Y goes back to the default ({inherited})",
            own is { } value ? AppearancePage.GamesTitle(value) : "Default", () =>
        {
            var choices = new List<Choice> { new(string.Empty, "As in Settings", $"{AppearancePage.GamesTitle(settings)}, the Appearance page's") };
            foreach (var layout in Enum.GetValues<GamesLayout>())
            {
                choices.Add(new Choice(Layouts.Name(layout), AppearancePage.GamesTitle(layout), AppearancePage.GamesDetail(layout)));
            }

            Layer.Push(new ChoicePanel("How its games are shown", null, choices,
                own is { } current ? Layouts.Name(current) : string.Empty,
                choice => SaveView(Layouts.TryParse(choice.Id, out GamesLayout chosen) ? chosen : null)));
        });

        // Left and right step through Default, then each layout.
        row.Adjuster = direction =>
        {
            var at = own is { } current ? (int)current + 1 : 0;
            var next = Math.Clamp(at + Math.Sign(direction), 0, Enum.GetValues<GamesLayout>().Length);
            if (next != at)
            {
                SaveView(next == 0 ? null : (GamesLayout)(next - 1));
            }
        };
        return row;
    }

    /// <summary>Saves the list's own games layout (null: the Appearance page's again).</summary>
    private void SaveView(GamesLayout? layout)
    {
        _settings.Save(this, [Edit("games_layout", layout is { } l ? Layouts.Name(l) : null)],
            layout is { } chosen ? $"{_owner} games: {AppearancePage.GamesTitle(chosen).ToLowerInvariant()}." : $"{_owner} games: as in Settings.");
    }

    /// <summary>
    /// The list's games grid columns or rows: its own (<c>games_columns</c>, <c>games_rows</c>; 0 automatic), or
    /// the Appearance page's when unset. A chooses, left and right step (from the Appearance page's value), Y goes back to it.
    /// </summary>
    private SettingRow AddGridRow(string title, string key, int max, int? own, int settings)
    {
        var what = key == "games_rows" ? "rows" : "columns";
        var inherited = $"As in Settings: {AppearancePage.SizeText(settings).ToLowerInvariant()}";
        var row = AddRow(title, own is null ? inherited : $"{_owner} own · Y goes back to the default ({AppearancePage.SizeText(settings).ToLowerInvariant()})",
            own is { } value ? AppearancePage.SizeText(value) : "Default", () =>
        {
            var choices = AppearancePage.SizeChoices(max, what);
            choices.Insert(0, new Choice(string.Empty, "As in Settings", $"{AppearancePage.SizeText(settings)}, the Appearance page's"));
            Layer.Push(new ChoicePanel($"{title} of {_owner} games", null, choices,
                own?.ToString(CultureInfo.InvariantCulture) ?? string.Empty,
                choice => SaveGrid(key, choice.Id.Length == 0 ? null : int.Parse(choice.Id, CultureInfo.InvariantCulture))));
        });
        row.Adjuster = direction =>
        {
            var current = own ?? settings;
            var next = Math.Clamp(current + Math.Sign(direction), 0, max);
            if (next != current || own is null)
            {
                SaveGrid(key, next);
            }
        };
        return row;
    }

    /// <summary>Saves the list's own games grid columns or rows (null: the Appearance page's again).</summary>
    private void SaveGrid(string key, int? value)
    {
        var what = key == "games_rows" ? "rows" : "columns";
        _settings.Save(this, [Edit(key, value is { } v ? (long)v : null)],
            value switch
            {
                null => $"{_owner} games grid: {what} as in Settings.",
                0 => $"{_owner} games grid: automatic {what}.",
                1 => $"{_owner} games grid: 1 {what[..^1]}.",
                _ => $"{_owner} games grid: {value} {what}.",
            });
    }

    /// <summary>
    /// What the list's games are sorted by, or which way: its own (<c>games_sort</c>, <c>games_sort_order</c>), or the
    /// Appearance page's when unset. A chooses, left and right step through Default and each value, Y goes back to the default.
    /// </summary>
    private SettingRow AddSortRow(string title, string key, IReadOnlyList<string> names, int? own, int settings, Func<int, string> titleOf, Func<int, string> detailOf)
    {
        var inherited = titleOf(settings);
        var row = AddRow(title, own is null ? $"As in Settings: {inherited.ToLowerInvariant()}" : $"Its own · Y goes back to the default ({inherited.ToLowerInvariant()})",
            own is { } value ? titleOf(value) : "Default", () =>
        {
            var choices = new List<Choice> { new(string.Empty, "As in Settings", $"{inherited}, the Appearance page's") };
            for (var i = 0; i < names.Count; i++)
            {
                choices.Add(new Choice(names[i], titleOf(i), detailOf(i)));
            }

            Layer.Push(new ChoicePanel(key == "games_sort" ? "Sort its games by" : "Its games' order", null, choices,
                own is { } current ? names[current] : string.Empty,
                choice => SaveSort(key, choice.Id.Length == 0 ? null : choice.Id, choice.Id.Length == 0 ? null : choice.Title)));
        });

        // Left and right step through Default, then each value.
        row.Adjuster = direction =>
        {
            var at = own is { } current ? current + 1 : 0;
            var next = Math.Clamp(at + Math.Sign(direction), 0, names.Count);
            if (next != at)
            {
                SaveSort(key, next == 0 ? null : names[next - 1], next == 0 ? null : titleOf(next - 1));
            }
        };
        return row;
    }

    /// <summary>Saves the list's own <paramref name="key"/> (null: the Appearance page's again).</summary>
    private void SaveSort(string key, string? name, string? title)
    {
        var what = key == "games_sort" ? "sorted" : "order";
        _settings.Save(this, [Edit(key, name)],
            title is null
                ? $"{_owner} games: {what} as in Settings."
                : key == "games_sort" ? $"{_owner} games: sorted by {title.ToLowerInvariant()}." : $"{_owner} games: {title.ToLowerInvariant()}.");
    }
}
