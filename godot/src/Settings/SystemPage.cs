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
using Launcher.Core.Models;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// One system's options (M7): its ROM folders (several are allowed, scanned in order; the default is the first of
/// <c>{rom_root}/&lt;id&gt;</c> and its aliases that exists), the emulator it launches with, its models (its own card for
/// the systems grid, and the template its games use: one of the theme's, or the user's own <c>.glb</c>), and
/// "scrape this system", which says how many games it will take on first. The settings screen opens it from ROM
/// folders, and X on a system in the grid opens it too. Saving folders rescans the system; a model change reloads the
/// theme, so the grid shows it without a restart.
/// </summary>
public sealed partial class SystemPage : ListPanel
{
    private const string OwnTemplate = "*own";
    private const string ThemesChoice = "";

    private readonly SettingsController _settings;
    private readonly string _systemId;
    private readonly List<(SettingRow Row, int Index)> _folderRows = [];
    private SettingRow? _card;
    private SettingRow? _template;
    private SettingRow? _scrape;
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
        LoadInfo();
    }

    private ItemOptions? Options => _settings.Options;

    public override void OnClosed()
    {
        _settings.ConfigApplied -= Rebuild;
        _settings.Jobs.Jobs.Changed -= ShowScrapeState;
    }

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        _folderRows.Clear();
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var config = _settings.Services.Config;
        if (config.FindSystem(_systemId) is not { } system)
        {
            _card = _template = _scrape = null;
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

        if (Options is null)
        {
            _card = _template = _scrape = null;
            return;
        }

        AddSection("Models");
        _card = AddRow("System model", activated: PickCard);
        _template = AddRow("Game template", activated: ChooseTemplate);
        AddNote("A game with a model of its own (X on the game, then Model) shows it instead of the template.");

        AddSection("Scraping");
        _scrape = AddRow("Scrape this system", "Counting its games…", activated: ScrapeSystem);
        ShowModels();
        ShowScrapeState();
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

    /// <summary>The theme's templates (the active theme's, then the built-in one's), or the user's own model.</summary>
    private void ChooseTemplate()
    {
        var options = Options!;
        var system = _settings.Services.Config.FindSystem(_systemId)!;
        var resolver = options.Theme.Plan.Resolver;
        var choices = new List<Choice>
        {
            new(ThemesChoice, "The theme's choice", ThemeDefault(resolver.Active, system.Id) is { } themes ? $"'{themes}' in {resolver.Active.Name}" : "Whatever the theme gives it"),
            new(OwnTemplate, "Your own model…", "A .glb (or an OBJ zip) for every game of this system"),
        };
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var theme in (Launcher.Core.Theming.Theme[])[resolver.Active, resolver.BuiltIn])
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

    private static string? ThemeDefault(Launcher.Core.Theming.Theme theme, string systemId) =>
        theme.Systems.TryGetValue(systemId, out var entry) && entry.GameTemplate is { } id ? id : theme.Defaults.GameTemplate;

    // ---- Scraping --------------------------------------------------------------------------------------

    private void ShowScrapeState()
    {
        if (_scrape is null)
        {
            return;
        }

        var jobs = _settings.Jobs;
        _scrape.Value = jobs.Scraping ? "Running" : null;
        if (_count is { } count)
        {
            _scrape.Detail = count.Games == 0
                ? "No games yet: rescan it first"
                : string.Create(CultureInfo.InvariantCulture,
                    $"{Games(count.Games)}; {count.Missing:N0} never scraped, not found or without a front cover");
        }
    }

    private static string Games(int count) => count == 1 ? "1 game" : string.Create(CultureInfo.InvariantCulture, $"{count:N0} games");

    /// <summary>Counts again, says how many games and which providers, and asks before it starts.</summary>
    private void ScrapeSystem()
    {
        var jobs = _settings.Jobs;
        if (jobs.Scraping)
        {
            ShowStatus("A scrape is already running: it's on the progress card, and in Settings.", UiStyle.Dim, 4);
            return;
        }

        var name = _settings.Services.Config.FindSystem(_systemId)?.Name ?? _systemId;
        _scrape!.Value = "Counting…";
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

                AskToScrape(name, preview.Count!, preview.Providers!);
            });
        });
    }

    private void AskToScrape(string name, SystemScrapeCount count, IReadOnlyList<ProviderStatus> providers)
    {
        if (count.Games == 0)
        {
            ConfirmDialog.Tell(Layer, "Nothing to scrape", $"{name} has no games in the library yet. Check its ROM folders, then rescan.");
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
        text.Append(CultureInfo.InvariantCulture, $"Every game of {name} is looked up: {Games(count.Games)}. ");
        text.Append(count.Missing == 0
            ? "All of them have been scraped before, so each is fetched again by its match, not searched for."
            : count.Missing == count.Games
                ? "None of them has been scraped successfully yet (or each has no front cover)."
                : string.Create(CultureInfo.InvariantCulture, $"{count.Missing:N0} have never been scraped, weren't found or have no front cover; the others are fetched again by their match."));
        text.Append("\n\nThey'll be looked up with ").Append(string.Join(", then ", usable.Select(p => p.DisplayName))).Append('.');
        foreach (var skipped in providers.Where(p => p.InOrder && p.State != ProviderState.Ready))
        {
            text.Append(' ').Append(skipped.DisplayName).Append(skipped.State == ProviderState.MissingCredentials ? " has no credentials, so it's skipped." : " is resting, so it's skipped for now.");
        }

        text.Append("\n\nYour own images and edits are kept. It runs in the background: you can keep browsing, and its games update in the grid as they're done.");
        ConfirmDialog.Ask(Layer, string.Create(CultureInfo.InvariantCulture, $"Scrape {Games(count.Games)}?"), text.ToString(), "Start scraping", "Not now", yes =>
        {
            if (yes && !_settings.Jobs.ScrapeSystem(_systemId))
            {
                ShowStatus("A scrape is already running.", UiStyle.Warning, 4);
            }
        });
    }
}
