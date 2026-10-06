using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Launcher.App.Navigation;
using Launcher.App.Options;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Files;
using Launcher.Core.Importing;
using Launcher.Core.Media;
using Launcher.Core.Models;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// One system's options (M7): its ROM folders (several are allowed, scanned in order; the default is the first of
/// <c>{rom_root}/&lt;id&gt;</c> and its aliases that exists), the emulator it launches with, its models (its own card for
/// the systems grid, and the template its games use: one of the theme's, or the user's own <c>.glb</c>), and
/// how its games are shown (its own layout, its grid's columns and rows, and their order, or the Layout page's), "scrape this system", which says how many games it
/// will take on first (and since 2026-10-04 three narrower scrapes: games without a front cover, without a screenshot,
/// or not scraped in the last 30 days), and "import gamelist.xml" (ES-DE's metadata and media, copied in; 2026-10-04). The settings screen opens it from ROM
/// folders, and X on a system in the grid opens it too. Saving folders rescans the system; a model change reloads the
/// theme, so the grid shows it without a restart.
/// </summary>
public sealed partial class SystemPage : ListPanel
{
    private const string OwnTemplate = "*own";
    private const string ThemesChoice = "";
    private const string OtherGamelist = "*other";

    private readonly SettingsController _settings;
    private readonly string _systemId;
    private readonly List<(SettingRow Row, int Index)> _folderRows = [];
    private SettingRow? _card;
    private SettingRow? _template;
    private readonly List<(SettingRow Row, SystemScrapeFilter Filter)> _scrapeRows = [];
    private SettingRow? _import;
    private SettingRow? _view;
    private SettingRow? _columns;
    private SettingRow? _rows;
    private SettingRow? _sort;
    private SettingRow? _order;
    private ModelReport? _ownCard;
    private ModelReport? _ownTemplate;
    private SystemScrapeCount? _count;
    private int _infoGeneration;

    public SystemPage(SettingsController settings, string systemId)
        : base(settings.Services.Config.FindSystem(systemId)?.Name ?? systemId)
    {
        _settings = settings;
        _systemId = systemId;
        Subtitle = $"systems.{systemId} in systems.toml";
        Build();
        SetHints("A  Change     Y  Remove     B  Back");
        _settings.ConfigApplied += Rebuild;
        _settings.Jobs.Jobs.Changed += ShowScrapeState;
        _settings.Jobs.Jobs.Changed += ShowImportState;
        LoadInfo();
    }

    private ItemOptions? Options => _settings.Options;

    public override void OnClosed()
    {
        _settings.ConfigApplied -= Rebuild;
        _settings.Jobs.Jobs.Changed -= ShowScrapeState;
        _settings.Jobs.Jobs.Changed -= ShowImportState;
    }

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        _folderRows.Clear();
        _scrapeRows.Clear();
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var config = _settings.Services.Config;
        if (config.FindSystem(_systemId) is not { } system)
        {
            _card = _template = _import = null;
            AddNote("This system isn't enabled any more.", UiStyle.Warning);
            return;
        }

        AddSection("ROM folders");
        if (system.RomDirSource == RomDirSource.Default)
        {
            var candidates = string.Join(", then ", system.RomDirs);
            AddRow(system.RomDirs.Count > 0 ? system.RomDirs[0] : config.Settings.RomRoot,
                system.RomDirs.Count > 1 ? $"The default: the first of {candidates} that exists" : "The default, under the ROM root",
                "Change", () => Pick(null));
        }
        else
        {
            for (var i = 0; i < system.RomDirs.Count; i++)
            {
                var index = i;
                var row = AddRow(system.RomDirs[i], i == 0 && system.RomDirs.Count > 1 ? "Scanned first: its games win a clash" : null, "Change", () => Pick(index));
                _folderRows.Add((row, i));
            }

            AddRow("Add another folder", "Scanned after the ones above", null, () => Pick(system.RomDirs.Count));
            AddRow("Use the default folder", $"{config.Settings.RomRoot}{System.IO.Path.DirectorySeparatorChar}{system.Id} (or an alias's folder)", null, UseDefault);
        }

        AddSection("Emulator");
        var emulator = config.Emulators.TryGetValue(system.Emulator, out var profile) ? profile.Name : system.Emulator;
        AddRow("Emulator", emulator, "Change", ChooseEmulator);
        if (system.AltEmulators.Count > 0)
        {
            AddNote($"Also suggested for {system.Name}: {string.Join(", ", system.AltEmulators.Select(id => config.Emulators.TryGetValue(id, out var e) ? e.Name : id))}.");
        }

        AddSection("Games view");
        var display = config.Settings.Display;
        _view = AddViewRow(system.GamesLayout, display.GamesLayout);
        _columns = AddGridRow("Columns", "games_columns", DisplaySettings.MaxColumns, system.GamesColumns, display.GamesGrid.Columns);
        _rows = AddGridRow("Rows", "games_rows", DisplaySettings.MaxRows, system.GamesRows, display.GamesGrid.Rows);
        if (display.GamesLayoutFor(system) != GamesLayout.Grid)
        {
            AddNote("Columns and rows are for the grid view.");
        }

        var sortedBy = display.GamesSortFor(system).Sort;
        _sort = AddSortRow("Sort by", "games_sort", Sorts.GamesNames, (int?)system.GamesSort, (int)display.GamesSort.Sort,
            i => LayoutPage.GamesSortTitle((GameSort)i), i => LayoutPage.GamesSortDetail((GameSort)i));
        _order = AddSortRow("Order", "games_sort_order", Sorts.OrderNames, (int?)system.GamesSortOrder, (int)display.GamesSort.Order,
            i => LayoutPage.OrderTitle((SortOrder)i), i => LayoutPage.GamesOrderDetail(sortedBy, (SortOrder)i));

        if (Options is null)
        {
            _card = _template = null;
            AddImport();
            return;
        }

        AddSection("Models");
        _card = AddRow("System model", activated: PickCard);
        _template = AddRow("Game template", activated: ChooseTemplate);
        AddNote("A game with a model of its own (X on the game, then Model) shows it instead of the template.");

        AddSection("Scraping");
        foreach (var filter in ScrapeFilters)
        {
            var captured = filter;
            _scrapeRows.Add((AddRow(ScrapeTitle(filter), "Counting its games…", activated: () => ScrapeSystem(captured)), filter));
        }

        AddImport();
        ShowModels();
        ShowScrapeState();
    }

    private void AddImport()
    {
        AddSection("Import");
        _import = AddRow("Import gamelist.xml", "ES-DE's titles, metadata, covers, screenshots, logos and videos, copied in", activated: ImportGamelist);
        ShowImportState();
    }

    public override bool Handle(NavCommand command)
    {
        if (command != NavCommand.Secondary)
        {
            return false;
        }

        var focused = GetViewport().GuiGetFocusOwner();
        foreach (var (row, index) in _folderRows)
        {
            if (row == focused)
            {
                RemoveFolder(index);
                return true;
            }
        }

        if (focused is not null && focused == _view)
        {
            SaveView(null);
            return true;
        }

        if (focused is not null && (focused == _columns || focused == _rows))
        {
            SaveGrid(focused == _columns ? "games_columns" : "games_rows", null);
            return true;
        }

        if (focused is not null && (focused == _sort || focused == _order))
        {
            SaveSort(focused == _sort ? "games_sort" : "games_sort_order", null, null);
            return true;
        }

        if (focused is not null && focused == _card)
        {
            RemoveOwn(SystemModelSlot.Card);
            return true;
        }

        if (focused is not null && focused == _template)
        {
            RemoveOwn(SystemModelSlot.GameTemplate);
            return true;
        }

        return false;
    }

    // ---- ROM folders and emulator ----------------------------------------------------------------------

    /// <summary>Replaces folder <paramref name="index"/> (or adds one past the end); null replaces the default with a folder of its own.</summary>
    private void Pick(int? index)
    {
        var system = _settings.Services.Config.FindSystem(_systemId)!;
        var start = index is { } i && i < system.RomDirs.Count ? system.RomDirs[i] : system.RomDirs.Count > 0 ? system.RomDirs[0] : null;
        FilePicker.Open(_settings.Ui, new PickerRequest(
            $"A ROM folder for {system.Name}",
            PickerMode.Folder,
            PickerUses.RomFolder,
            folder =>
            {
                var folders = system.RomDirSource == RomDirSource.Configured ? system.RomDirs.ToList() : [];
                if (index is { } at && at < folders.Count)
                {
                    folders[at] = folder;
                }
                else
                {
                    folders.Add(folder);
                }

                SaveFolders(folders, () => ConfigInput.CheckFolder(folder));
            },
            Start: start,
            Subtitle: "Open the folder with the games, then press X or choose Use this folder"));
    }

    private void RemoveFolder(int index)
    {
        var system = _settings.Services.Config.FindSystem(_systemId)!;
        var folders = system.RomDirs.ToList();
        var removed = folders[index];
        folders.RemoveAt(index);
        ConfirmDialog.Ask(Layer, "Remove this folder?",
            $"{removed}\n\n{system.Name} won't be scanned there any more, and its games from there leave the library (their favourites and play history are kept, for if you add it back).",
            "Remove it", "Keep it", yes =>
            {
                if (yes)
                {
                    SaveFolders(folders.Count == 0 ? null : folders, null);
                }
            }, destructive: true);
    }

    private void UseDefault() => SaveFolders(null, null);

    /// <summary>Saves the system's <c>rom_dirs</c> (null: the default again), then rescans it.</summary>
    private void SaveFolders(List<string>? folders, Func<string?>? check)
    {
        object? value = folders?.Select(ConfigWriter.PathValue).ToList();
        _settings.Save(this,
            [new ConfigEdit(ConfigFileKind.Systems, ["systems", _systemId, "rom_dirs"], value)],
            "Saved. Rescanning this system…",
            then: result =>
            {
                if (result.ChangedFiles.Count > 0)
                {
                    _settings.Rescan?.Invoke([_systemId]);
                }
            },
            check: check);
    }

    private void ChooseEmulator()
    {
        var config = _settings.Services.Config;
        var system = config.FindSystem(_systemId)!;
        var suggested = new HashSet<string>(system.AltEmulators.Prepend(system.Emulator), StringComparer.Ordinal);
        var choices = config.Emulators.Values
            .OrderBy(e => suggested.Contains(e.Id) ? 0 : 1)
            .ThenBy(e => e.Name, StringComparer.CurrentCultureIgnoreCase)
            .Select(e => new Choice(e.Id, e.Name, (suggested.Contains(e.Id) ? "Suggested · " : string.Empty) + e.ProgramText))
            .ToList();
        Layer.Push(new ChoicePanel($"Emulator for {system.Name}", "Games can still choose their own", choices, system.Emulator, choice =>
            _settings.Save(this, [new ConfigEdit(ConfigFileKind.Systems, ["systems", _systemId, "emulator"], choice.Id)], $"{system.Name} now launches with {choice.Title}.")));
    }

    // ---- Games view ------------------------------------------------------------------------------------

    /// <summary>
    /// How the system's games are shown: its own <c>games_layout</c>, or the Layout page's when unset (the default).
    /// A chooses, left and right step through Default, Grid, Carousel and List, Y goes back to the default.
    /// </summary>
    private SettingRow AddViewRow(GamesLayout? own, GamesLayout settings)
    {
        var inherited = LayoutPage.GamesTitle(settings).ToLowerInvariant();
        var row = AddRow("View", own is null ? $"As in Settings: {inherited}" : $"Its own · Y goes back to the default ({inherited})",
            own is { } value ? LayoutPage.GamesTitle(value) : "Default", () =>
        {
            var choices = new List<Choice> { new(string.Empty, "As in Settings", $"{LayoutPage.GamesTitle(settings)}, the Layout page's") };
            foreach (var layout in Enum.GetValues<GamesLayout>())
            {
                choices.Add(new Choice(Layouts.Name(layout), LayoutPage.GamesTitle(layout), LayoutPage.GamesDetail(layout)));
            }

            Layer.Push(new ChoicePanel("How its games are shown", $"Saved as systems.{_systemId}.games_layout", choices,
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

    /// <summary>Saves the system's own games layout (null: the Layout page's again).</summary>
    private void SaveView(GamesLayout? layout)
    {
        var name = _settings.Services.Config.FindSystem(_systemId)?.Name ?? _systemId;
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Systems, ["systems", _systemId, "games_layout"], layout is { } l ? Layouts.Name(l) : null)],
            layout is { } chosen ? $"{name}'s games: {LayoutPage.GamesTitle(chosen).ToLowerInvariant()}." : $"{name}'s games: as in Settings.");
    }

    /// <summary>
    /// The system's games grid columns or rows: its own (<c>games_columns</c>, <c>games_rows</c>; 0 automatic), or
    /// the Layout page's when unset. A chooses, left and right step (from the Layout page's value), Y goes back to it.
    /// </summary>
    private SettingRow AddGridRow(string title, string key, int max, int? own, int settings)
    {
        var what = key == "games_rows" ? "rows" : "columns";
        var inherited = $"As in Settings: {LayoutPage.SizeText(settings).ToLowerInvariant()}";
        var row = AddRow(title, own is null ? inherited : $"{SystemName()}'s own · Y goes back to the default ({LayoutPage.SizeText(settings).ToLowerInvariant()})",
            own is { } value ? LayoutPage.SizeText(value) : "Default", () =>
        {
            var choices = LayoutPage.SizeChoices(max, what);
            choices.Insert(0, new Choice(string.Empty, "As in Settings", $"{LayoutPage.SizeText(settings)}, the Layout page's"));
            Layer.Push(new ChoicePanel($"{title} of {SystemName()}'s games", $"Saved as systems.{_systemId}.{key}", choices,
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

        string SystemName() => _settings.Services.Config.FindSystem(_systemId)?.Name ?? _systemId;
    }

    /// <summary>Saves the system's own games grid columns or rows (null: the Layout page's again).</summary>
    private void SaveGrid(string key, int? value)
    {
        var name = _settings.Services.Config.FindSystem(_systemId)?.Name ?? _systemId;
        var what = key == "games_rows" ? "rows" : "columns";
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Systems, ["systems", _systemId, key], value is { } v ? (long)v : null)],
            value switch
            {
                null => $"{name}'s games grid: {what} as in Settings.",
                0 => $"{name}'s games grid: automatic {what}.",
                1 => $"{name}'s games grid: 1 {what[..^1]}.",
                _ => $"{name}'s games grid: {value} {what}.",
            });
    }

    /// <summary>
    /// What the system's games are sorted by, or which way: its own (<c>games_sort</c>, <c>games_sort_order</c>), or the
    /// Layout page's when unset. A chooses, left and right step through Default and each value, Y goes back to the default.
    /// </summary>
    private SettingRow AddSortRow(string title, string key, IReadOnlyList<string> names, int? own, int settings, Func<int, string> titleOf, Func<int, string> detailOf)
    {
        var inherited = titleOf(settings);
        var row = AddRow(title, own is null ? $"As in Settings: {inherited.ToLowerInvariant()}" : $"Its own · Y goes back to the default ({inherited.ToLowerInvariant()})",
            own is { } value ? titleOf(value) : "Default", () =>
        {
            var choices = new List<Choice> { new(string.Empty, "As in Settings", $"{inherited}, the Layout page's") };
            for (var i = 0; i < names.Count; i++)
            {
                choices.Add(new Choice(names[i], titleOf(i), detailOf(i)));
            }

            Layer.Push(new ChoicePanel(key == "games_sort" ? "Sort its games by" : "Its games' order", $"Saved as systems.{_systemId}.{key}", choices,
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

    /// <summary>Saves the system's own <paramref name="key"/> (null: the Layout page's again).</summary>
    private void SaveSort(string key, string? name, string? title)
    {
        var system = _settings.Services.Config.FindSystem(_systemId)?.Name ?? _systemId;
        var what = key == "games_sort" ? "sorted" : "order";
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Systems, ["systems", _systemId, key], name)],
            title is null
                ? $"{system}'s games: {what} as in Settings."
                : key == "games_sort" ? $"{system}'s games: sorted by {title.ToLowerInvariant()}." : $"{system}'s games: {title.ToLowerInvariant()}.");
    }

    // ---- Models ----------------------------------------------------------------------------------------

    /// <summary>The user's own models' reports and the scrape count, read off the main thread.</summary>
    private void LoadInfo()
    {
        if (Options is not { } options)
        {
            return;
        }

        var generation = ++_infoGeneration;
        var jobs = _settings.Jobs;
        var systemId = _systemId;
        _ = Task.Run(async () =>
        {
            ModelReport? card = null, template = null;
            SystemScrapeCount? count = null;
            try
            {
                card = await options.Models.GetSystemModelAsync(systemId, SystemModelSlot.Card, CancellationToken.None).ConfigureAwait(false);
                template = await options.Models.GetSystemModelAsync(systemId, SystemModelSlot.GameTemplate, CancellationToken.None).ConfigureAwait(false);
                count = (await jobs.PreviewSystemAsync(systemId, CancellationToken.None).ConfigureAwait(false)).Count;
            }
            catch (Exception e)
            {
                Godot.GD.PushWarning($"Options: couldn't read {systemId}'s models or games: {e.Message}");
            }

            _settings.Ui.Queue.Post(() =>
            {
                if (generation != _infoGeneration || !IsInstanceValid(this))
                {
                    return;
                }

                (_ownCard, _ownTemplate, _count) = (card, template, count);
                ShowModels();
                ShowScrapeState();
            });
        });
    }

    private void ShowModels()
    {
        if (Options is not { } options || _card is null || _template is null)
        {
            return;
        }

        var system = _settings.Services.Config.FindSystem(_systemId);
        _card.Detail = _ownCard is { } card
            ? $"Yours, {ItemOptions.ModelsText(card).Split('\n')[0]} · Y removes it"
            : $"The theme's: {InUse(options.Theme.CardModelInUse(_systemId)?.Description)}";
        _card.Value = _ownCard is null ? "Change" : "Yours";
        _template.Detail = _ownTemplate is { } template
            ? $"Yours, {ItemOptions.ModelsText(template).Split('\n')[0]} · Y removes it"
            : system?.GameModel is { } chosen
                ? $"'{chosen}', chosen from the theme (game_model)"
                : $"The theme's choice: {InUse(options.Theme.GameModelInUse(_systemId)?.Description)}";
        _template.Value = _ownTemplate is not null ? "Yours" : system?.GameModel is not null ? "Chosen" : "Change";
    }

    private static string InUse(string? description) => description ?? "none could be loaded";

    private void PickCard() => PickModel(SystemModelSlot.Card);

    private void PickModel(SystemModelSlot slot)
    {
        var options = Options!;
        var name = options.SystemName(_systemId);
        FilePicker.Open(_settings.Ui, new PickerRequest(
            slot == SystemModelSlot.Card ? $"A model for {name}'s card" : $"A game template for {name}",
            PickerMode.File,
            PickerUses.Model,
            file => ImportModel(slot, file),
            Filter: FileFilter.ModelImports,
            Subtitle: slot == SystemModelSlot.Card
                ? "A .glb (or a zip of an OBJ model), shown for this system in the systems grid"
                : "A .glb (or a zip of an OBJ model), shown for every game of this system without a model of its own"));
    }

    private void ImportModel(SystemModelSlot slot, string file)
    {
        var options = Options!;
        ShowStatus("Checking the model…", UiStyle.Dim);
        var systemId = _systemId;
        _ = Task.Run(async () =>
        {
            ModelImportResult result;
            try
            {
                result = await options.Models.ImportSystemModelAsync(systemId, slot, file, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e) when (e is System.IO.IOException or UnauthorizedAccessException)
            {
                result = new ModelImportResult(ModelImportStatus.Unsupported, null, false, null, [e.Message]);
            }

            _settings.Ui.Queue.Post(() =>
            {
                if (!IsInstanceValid(this))
                {
                    return;
                }

                ShowStatus(null);
                if (result.Status == ModelImportStatus.Imported)
                {
                    options.SystemModelsChanged();
                    LoadInfo();
                }

                ConfirmDialog.Tell(Layer, result.Status == ModelImportStatus.Imported ? "Model imported" : "Model not imported",
                    ItemOptions.Describe(result) + (result.Status == ModelImportStatus.Imported ? "\n\nThe theme is reloading to show it." : string.Empty));
            });
        });
    }

    private void RemoveOwn(SystemModelSlot slot)
    {
        var options = Options!;
        if ((slot == SystemModelSlot.Card ? _ownCard : _ownTemplate) is null)
        {
            ShowStatus("That's the theme's model: there's no model of yours to remove.", UiStyle.Dim, 4);
            return;
        }

        var what = slot == SystemModelSlot.Card ? "system model" : "game template";
        ConfirmDialog.Ask(Layer, $"Remove your {what}?",
            $"{ModelImportService.SystemModelPathFor(_systemId, slot)} is deleted, and the theme's {what} shows again.",
            "Remove it", "Keep it", yes =>
            {
                if (!yes)
                {
                    return;
                }

                _ = Task.Run(async () =>
                {
                    await options.Models.RemoveSystemModelAsync(_systemId, slot, CancellationToken.None).ConfigureAwait(false);
                    _settings.Ui.Queue.Post(() =>
                    {
                        options.SystemModelsChanged();
                        if (IsInstanceValid(this))
                        {
                            ShowStatus($"Your {what} was removed. The theme is reloading.", UiStyle.Good, 5);
                            LoadInfo();
                        }
                    });
                });
            }, destructive: true);
    }

    /// <summary>The theme's templates (the active theme's, then the base theme's), or the user's own model.</summary>
    private void ChooseTemplate()
    {
        var options = Options!;
        var system = _settings.Services.Config.FindSystem(_systemId)!;
        var resolver = options.Theme.Plan.Resolver;
        var choices = new List<Choice>
        {
            new(ThemesChoice, "The theme's choice", ThemeDefault(resolver, system.Id) is { } themes ? $"'{themes}' in {resolver.Active.Name}" : "Whatever the theme gives it"),
            new(OwnTemplate, "Your own model…", "A .glb (or an OBJ zip) for every game of this system"),
        };
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var theme in (Launcher.Core.Theming.Theme[])[resolver.Active, resolver.Base])
        {
            foreach (var id in theme.Templates.Keys.Order(StringComparer.Ordinal))
            {
                if (seen.Add(id))
                {
                    choices.Add(new Choice(id, id, $"From {theme.Name}"));
                }
            }
        }

        var current = _ownTemplate is not null ? OwnTemplate : system.GameModel ?? ThemesChoice;
        Layer.Push(new ChoicePanel($"Game template for {system.Name}", "What its games show, unless one has a model of its own", choices, current, choice =>
        {
            if (choice.Id == OwnTemplate)
            {
                PickModel(SystemModelSlot.GameTemplate);
                return;
            }

            var ownRemoved = _ownTemplate is not null;
            _settings.Save(this,
                [new ConfigEdit(ConfigFileKind.Systems, ["systems", _systemId, "game_model"], choice.Id == ThemesChoice ? null : choice.Id)],
                choice.Id == ThemesChoice ? "Saved: the theme chooses. Reloading the theme…" : $"Saved: {choice.Id}. Reloading the theme…",
                then: saved =>
                {
                    // The user's own template would still beat the choice, so it goes.
                    if (ownRemoved)
                    {
                        _ = Task.Run(async () =>
                        {
                            await options.Models.RemoveSystemModelAsync(_systemId, SystemModelSlot.GameTemplate, CancellationToken.None).ConfigureAwait(false);
                            _settings.Ui.Queue.Post(() =>
                            {
                                options.SystemModelsChanged();
                                LoadInfo();
                            });
                        });
                        return;
                    }

                    options.SystemModelsChanged();
                });
        }));
    }

    /// <summary>The template the theme gives the system: the active theme's choice, else the base theme's.</summary>
    private static string? ThemeDefault(Launcher.Core.Theming.ModelResolver resolver, string systemId)
    {
        return Chosen(resolver.Active) ?? Chosen(resolver.Base);

        string? Chosen(Launcher.Core.Theming.Theme theme) =>
            theme.Systems.TryGetValue(systemId, out var entry) && entry.GameTemplate is { } id ? id : theme.Defaults.GameTemplate;
    }

    // ---- Scraping --------------------------------------------------------------------------------------

    /// <summary>The scrape rows, in order: every game, then the games without a front cover, a screenshot, or a recent scrape (2026-10-04).</summary>
    private static readonly SystemScrapeFilter[] ScrapeFilters =
        [SystemScrapeFilter.All, SystemScrapeFilter.NoCover, SystemScrapeFilter.NoScreenshot, SystemScrapeFilter.NotRecent];

    private static int RecentDays => (int)ScrapeService.RecentScrape.TotalDays;

    private static string ScrapeTitle(SystemScrapeFilter filter) => filter switch
    {
        SystemScrapeFilter.NoCover => "Scrape games without a front cover",
        SystemScrapeFilter.NoScreenshot => "Scrape games without a screenshot",
        SystemScrapeFilter.NotRecent => string.Create(CultureInfo.InvariantCulture, $"Scrape games not scraped in the last {RecentDays} days"),
        _ => "Scrape this system",
    };

    /// <summary>The media kind a filter's games lack, or null.</summary>
    private static string? KindOf(SystemScrapeFilter filter) => filter switch
    {
        SystemScrapeFilter.NoCover => MediaKinds.Cover,
        SystemScrapeFilter.NoScreenshot => MediaKinds.Screenshot,
        _ => null,
    };

    private void ShowScrapeState()
    {
        var running = _settings.Jobs.Scraping;
        foreach (var (row, filter) in _scrapeRows)
        {
            row.Value = running ? "Running" : null;
            if (_count is not { } count)
            {
                continue;
            }

            row.Detail = count.Games == 0
                ? "No games yet: rescan it first"
                : filter == SystemScrapeFilter.All
                    ? string.Create(CultureInfo.InvariantCulture, $"{Games(count.Games)}; {count.Missing:N0} never scraped, not found or without a front cover")
                    : string.Create(CultureInfo.InvariantCulture, $"{Games(count.Of(filter))} of {count.Games:N0}; only the media they're missing is downloaded");
        }
    }

    private static string Games(int count) => count == 1 ? "1 game" : string.Create(CultureInfo.InvariantCulture, $"{count:N0} games");

    /// <summary>Counts again, says how many games and which providers, and asks before it starts.</summary>
    private void ScrapeSystem(SystemScrapeFilter filter)
    {
        var jobs = _settings.Jobs;
        if (jobs.Scraping)
        {
            ShowStatus("A scrape is already running: it's on the progress card, and in Settings.", UiStyle.Dim, 4);
            return;
        }

        var name = _settings.Services.Config.FindSystem(_systemId)?.Name ?? _systemId;
        foreach (var (row, rowFilter) in _scrapeRows)
        {
            if (rowFilter == filter)
            {
                row.Value = "Counting…";
            }
        }

        var systemId = _systemId;
        _ = Task.Run(async () =>
        {
            string? failure = null;
            (SystemScrapeCount Count, IReadOnlyList<ProviderStatus> Providers) preview = default;
            try
            {
                preview = await jobs.PreviewSystemAsync(systemId, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                failure = e.Message;
            }

            _settings.Ui.Queue.Post(() =>
            {
                if (!IsInstanceValid(this) || Layer?.Top != this)
                {
                    return;
                }

                _count = preview.Count ?? _count;
                ShowScrapeState();
                if (failure is not null)
                {
                    ConfirmDialog.Tell(Layer, "Couldn't count the games", failure);
                    return;
                }

                AskToScrape(name, filter, preview.Count!, preview.Providers!);
            });
        });
    }

    private void AskToScrape(string name, SystemScrapeFilter filter, SystemScrapeCount count, IReadOnlyList<ProviderStatus> providers)
    {
        if (count.Games == 0)
        {
            ConfirmDialog.Tell(Layer, "Nothing to scrape", $"{name} has no games in the library yet. Check its ROM folders, then rescan.");
            return;
        }

        var games = count.Of(filter);
        if (games == 0)
        {
            ConfirmDialog.Tell(Layer, "Nothing to scrape", filter switch
            {
                SystemScrapeFilter.NoCover => $"Every game of {name} has a front cover.",
                SystemScrapeFilter.NoScreenshot => $"Every game of {name} has a screenshot.",
                _ => string.Create(CultureInfo.InvariantCulture, $"Every game of {name} was scraped in the last {RecentDays} days."),
            });
            return;
        }

        var usable = providers.Where(p => p.InOrder && p.State == ProviderState.Ready).ToList();
        if (usable.Count == 0)
        {
            ConfirmDialog.Ask(Layer, "No provider can scrape yet",
                "None of the providers you use has its credentials yet. Add them under Scraping in the settings first.",
                "Open Scraping", "Not now", yes =>
                {
                    if (yes)
                    {
                        Layer.Push(new ScrapingPage(_settings));
                    }
                });
            return;
        }

        var text = new StringBuilder();
        switch (filter)
        {
            case SystemScrapeFilter.All:
                text.Append(CultureInfo.InvariantCulture, $"Every game of {name} is looked up: {Games(count.Games)}. ");
                text.Append(count.Missing == 0
                    ? "All of them have been scraped before, so each is fetched again by its match, not searched for."
                    : count.Missing == count.Games
                        ? "None of them has been scraped successfully yet (or each has no front cover)."
                        : string.Create(CultureInfo.InvariantCulture, $"{count.Missing:N0} have never been scraped, weren't found or have no front cover; the others are fetched again by their match."));
                break;
            case SystemScrapeFilter.NotRecent:
                text.Append(games == count.Games
                    ? string.Create(CultureInfo.InvariantCulture, $"None of {name}'s {Games(count.Games)} has been scraped in the last {RecentDays} days, so every one is looked up.")
                    : string.Create(CultureInfo.InvariantCulture, $"{games:N0} of {name}'s {Games(count.Games)} haven't been scraped in the last {RecentDays} days, or ever: those are looked up, and the {count.Games - games:N0} scraped since are skipped."));
                break;
            default:
                var kind = ScrapeMediaPage.NameOf(KindOf(filter)!).ToLowerInvariant();
                text.Append(games == count.Games
                    ? string.Create(CultureInfo.InvariantCulture, $"None of {name}'s {Games(count.Games)} has a {kind}, so every one is looked up.")
                    : string.Create(CultureInfo.InvariantCulture, $"{games:N0} of {name}'s {Games(count.Games)} have no {kind}: those are looked up, and the {count.Games - games:N0} with one are skipped."));
                break;
        }

        text.Append(" Each game gets only the media it's missing, and its metadata is refreshed.");
        if (KindOf(filter) is { } wanted && !_settings.Services.Config.Settings.Scraping.Media.Contains(wanted))
        {
            text.Append(CultureInfo.InvariantCulture, $" {ScrapeMediaPage.NameOf(wanted)}s aren't in your media to scrape, though, so none is downloaded: turn them on under Scraping, Media to scrape.");
        }

        text.Append("\n\nThey'll be looked up with ").Append(string.Join(", then ", usable.Select(p => p.DisplayName))).Append('.');
        foreach (var skipped in providers.Where(p => p.InOrder && p.State != ProviderState.Ready))
        {
            text.Append(' ').Append(skipped.DisplayName).Append(skipped.State == ProviderState.MissingCredentials ? " has no credentials, so it's skipped." : " is resting, so it's skipped for now.");
        }

        text.Append("\n\nYour own images and edits are kept. It runs in the background: you can keep browsing, and its games update in the grid as they're done.");
        ConfirmDialog.Ask(Layer, string.Create(CultureInfo.InvariantCulture, $"Scrape {Games(games)}?"), text.ToString(), "Start scraping", "Not now", yes =>
        {
            if (yes && !_settings.Jobs.ScrapeSystem(_systemId, filter))
            {
                ShowStatus("A scrape is already running.", UiStyle.Warning, 4);
            }
        });
    }

    // ---- Gamelist import -------------------------------------------------------------------------------

    private void ShowImportState()
    {
        if (_import is not null)
        {
            _import.Value = _settings.Jobs.Importing ? "Running" : null;
        }
    }

    /// <summary>Looks for the system's gamelists (its ROM folders, then ES-DE's own folder), then reads the one chosen.</summary>
    private void ImportGamelist()
    {
        var jobs = _settings.Jobs;
        if (jobs.Importing)
        {
            ShowStatus("A gamelist is already being imported: it's on the progress card.", UiStyle.Dim, 4);
            return;
        }

        var service = jobs.Gamelists;
        var systemId = _systemId;
        _import!.Value = "Looking…";
        _ = Task.Run(async () =>
        {
            IReadOnlyList<string> found = [];
            string? failure = null;
            try
            {
                found = await service.FindAsync(systemId, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                failure = e.Message;
            }

            _settings.Ui.Queue.Post(() =>
            {
                if (!IsInstanceValid(this) || Layer?.Top != this)
                {
                    return;
                }

                ShowImportState();
                if (failure is not null)
                {
                    ConfirmDialog.Tell(Layer, "Couldn't look for a gamelist", failure);
                    return;
                }

                ChooseGamelist(found);
            });
        });
    }

    private void ChooseGamelist(IReadOnlyList<string> found)
    {
        if (found.Count == 0)
        {
            PickGamelist();
            return;
        }

        if (found.Count == 1)
        {
            ReadGamelist(found[0]);
            return;
        }

        var choices = found.Select(f => new Choice(f, f)).ToList();
        choices.Add(new Choice(OtherGamelist, "Choose a file…", "A gamelist.xml somewhere else"));
        Layer.Push(new ChoicePanel("Which gamelist?", $"Found for {SystemName()}", choices, found[0], choice =>
        {
            if (choice.Id == OtherGamelist)
            {
                PickGamelist();
            }
            else
            {
                ReadGamelist(choice.Id);
            }
        }));
    }

    private void PickGamelist()
    {
        var system = _settings.Services.Config.FindSystem(_systemId);
        FilePicker.Open(_settings.Ui, new PickerRequest(
            $"A gamelist for {SystemName()}",
            PickerMode.File,
            PickerUses.Gamelist,
            ReadGamelist,
            Filter: FileFilter.Gamelists,
            Start: system is { RomDirs.Count: > 0 } ? system.RomDirs[0] : null,
            Subtitle: "ES-DE's gamelist.xml: its games are found in this system's ROM folders"));
    }

    /// <summary>Reads the gamelist and works out what it would add, off the main thread, then asks.</summary>
    private void ReadGamelist(string file)
    {
        var service = _settings.Jobs.Gamelists;
        var systemId = _systemId;
        ShowStatus("Reading the gamelist…", UiStyle.Dim);
        _ = Task.Run(async () =>
        {
            GamelistPlan? plan = null;
            string? failure = null;
            try
            {
                plan = await service.PlanAsync(systemId, file, CancellationToken.None).ConfigureAwait(false);
                failure = plan.Error;
            }
            catch (Exception e)
            {
                failure = e.Message;
            }

            _settings.Ui.Queue.Post(() =>
            {
                if (!IsInstanceValid(this) || Layer is null)
                {
                    return;
                }

                ShowStatus(null);
                if (failure is not null || plan is null)
                {
                    ConfirmDialog.Tell(Layer, "Couldn't read the gamelist", failure ?? file);
                    return;
                }

                AskToImport(plan);
            });
        });
    }

    private void AskToImport(GamelistPlan plan)
    {
        var name = SystemName();
        if (plan.InLibrary == 0)
        {
            ConfirmDialog.Tell(Layer, "Nothing to import", plan.Entries == 0
                ? $"{plan.File}\n\nThe gamelist has no games."
                : $"{plan.File}\n\nNone of its {Games(plan.Entries)} is in the library. Check {name}'s ROM folders and rescan it, then import again.");
            return;
        }

        if (plan.Games.Count == 0)
        {
            ConfirmDialog.Tell(Layer, "Nothing new to import",
                $"{plan.File}\n\nEvery game it lists already has what it offers: a title and metadata (scraped or yours), and each kind of image and video.");
            return;
        }

        var text = new StringBuilder();
        text.Append(plan.File).Append("\n\n");
        text.Append(plan.InLibrary == plan.Entries
            ? plan.Entries == 1 ? "Its game is in the library" : string.Create(CultureInfo.InvariantCulture, $"All {plan.Entries:N0} of its games are in the library")
            : string.Create(CultureInfo.InvariantCulture, $"{plan.InLibrary:N0} of its {Games(plan.Entries)} are in the library"));
        text.Append(plan.NotInLibrary == 0
            ? ". "
            : string.Create(CultureInfo.InvariantCulture, $"; {plan.NotInLibrary:N0} aren't (not scanned yet, or in another folder). "));
        if (plan.WithMetadata > 0)
        {
            text.Append(CultureInfo.InvariantCulture, $"{Games(plan.WithMetadata)} get titles and metadata where they have none, saved as your own edits: scraping won't replace them, and Clear metadata removes them.");
        }

        if (plan.Files > 0)
        {
            var kinds = plan.FilesByKind();
            var parts = new List<string>();
            foreach (var (kind, label) in (ReadOnlySpan<(string, string)>)[(MediaKinds.Cover, "covers"), (MediaKinds.Screenshot, "screenshots"), (MediaKinds.Logo, "logos"), (MediaKinds.Video, "videos"), (MediaKinds.Manual, "manuals")])
            {
                if (kinds.TryGetValue(kind, out var count))
                {
                    parts.Add(string.Create(CultureInfo.InvariantCulture, $"{count:N0} {label}"));
                }
            }

            text.Append("\n\nUp to ").Append(parts.Count == 1 ? parts[0] : string.Join(", ", parts[..^1]) + " and " + parts[^1]);
            text.Append(" are copied into the launcher's media folder. The gamelist's own files aren't moved or changed, and images a game already has are kept.");
        }

        if (plan.Favourites > 0 || plan.Matches > 0)
        {
            text.Append("\n\n");
            if (plan.Favourites > 0)
            {
                text.Append(CultureInfo.InvariantCulture, $"{plan.Favourites:N0} become favourites. ");
            }

            if (plan.Matches > 0)
            {
                text.Append(CultureInfo.InvariantCulture, $"{Games(plan.Matches)} get their ScreenScraper match, so a scrape fetches them by id.");
            }
        }

        if (plan.Hidden > 0)
        {
            text.Append(CultureInfo.InvariantCulture, $"\n\n{Games(plan.Hidden)} it hides stay shown: the launcher can't hide games yet.");
        }

        text.Append("\n\nIt runs in the background: you can keep browsing, and the games update as it goes.");
        ConfirmDialog.Ask(Layer, $"Import {Games(plan.Games.Count)}?", text.ToString(), "Import", "Not now", yes =>
        {
            if (yes && !_settings.Jobs.ImportGamelist(plan))
            {
                ShowStatus("A gamelist is already being imported.", UiStyle.Warning, 4);
            }
        });
    }

    private string SystemName() => _settings.Services.Config.FindSystem(_systemId)?.Name ?? _systemId;
}
