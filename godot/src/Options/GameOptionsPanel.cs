using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Screens;
using Launcher.App.Settings;
using Launcher.App.Ui;
using Launcher.Core.Files;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Models;

namespace Launcher.App.Options;

/// <summary>
/// One game's options (M7 part 2), opened with X on the game: the emulator it launches with, its own model, its
/// title and metadata, its images (one per media slot, the user's own or scraped), "scrape this game" and "clear
/// metadata". Every change is saved at once (userdata.db for edits and the emulator, files in ConfigDir for images
/// and the model) and shows in the grid without a restart.
/// </summary>
public sealed partial class GameOptionsPanel : ListPanel
{
    private readonly ItemOptions _options;
    private readonly SettingRow _emulator;
    private readonly SettingRow _model;
    private readonly SettingRow _metadata;
    private readonly SettingRow _media;
    private readonly SettingRow _scrape;
    private readonly SettingRow _clear;
    private GameDetails _game;
    private (string Path, ModelReport Report)? _ownModel;
    private IReadOnlyList<GameMediaInfo> _mediaRows = [];
    private int _generation;
    private bool _scraping;

    public GameOptionsPanel(ItemOptions options, GameDetails game)
        : base(game.Title)
    {
        _options = options;
        _game = game;
        Subtitle = $"{options.SystemName(game.Key.SystemId)} · {game.RelPath}";

        AddSection("Launching");
        _emulator = AddRow("Emulator", activated: ChooseEmulator);

        AddSection("Look");
        _model = AddRow("Model", activated: PickModel);
        _media = AddRow("Images", "Reading…", "Open", () => Layer.Push(new GameMediaPanel(_options, _game)));

        AddSection("Title and metadata");
        _metadata = AddRow("Edit the title and metadata", activated: () => Layer.Push(new GameMetadataPanel(_options, _game.Key, _game.Title)));

        AddSection("Scraping");
        _scrape = AddRow("Scrape this game", activated: Scrape);
        _clear = AddRow("Clear metadata", "Removes what was scraped, every image (yours too), its model and your edits", activated: AskToClear);
        _clear.DetailColour = UiStyle.Warning;

        SetHints("A  Choose     Y  Remove     B  Back");
        _options.Jobs.GamesUpdated += OnGamesUpdated;
        _options.Library.MediaChanged += OnMediaChanged;
        ShowGame();
        Reload();
    }

    public override void OnRevealed() => Reload();

    public override void OnClosed()
    {
        _options.Jobs.GamesUpdated -= OnGamesUpdated;
        _options.Library.MediaChanged -= OnMediaChanged;
    }

    public override bool Handle(NavCommand command)
    {
        if (command == NavCommand.Favourite && GetViewport().GuiGetFocusOwner() == _model)
        {
            RemoveModel();
            return true;
        }

        return false;
    }

    private void OnGamesUpdated(IReadOnlyList<GameKey> games)
    {
        if (games.Contains(_game.Key))
        {
            Reload();
        }
    }

    /// <summary>A worker thread: an import, a scrape or a clear changed the game's media.</summary>
    private void OnMediaChanged(object? sender, MediaChangedEventArgs e)
    {
        if (e.Games is null || e.Games.Contains(_game.Key))
        {
            _options.Ui.Queue.Post(() =>
            {
                if (IsInstanceValid(this))
                {
                    Reload();
                }
            });
        }
    }

    /// <summary>Reads the game, its model and its media again, off the main thread.</summary>
    private void Reload()
    {
        var generation = ++_generation;
        var key = _game.Key;
        var options = _options;
        _ = Task.Run(async () =>
        {
            try
            {
                var game = await options.Library.GetGameAsync(key, CancellationToken.None).ConfigureAwait(false);
                if (game is null)
                {
                    return;
                }

                var model = await options.Models.GetGameModelAsync(key, CancellationToken.None).ConfigureAwait(false);
                var media = await options.Library.GetGameMediaInfoAsync(game.GameId, CancellationToken.None).ConfigureAwait(false);
                options.Ui.Queue.Post(() =>
                {
                    if (generation != _generation || !IsInstanceValid(this))
                    {
                        return;
                    }

                    (_game, _ownModel, _mediaRows) = (game, model, media);
                    ShowGame();
                });
            }
            catch (Exception e)
            {
                GD.PushWarning($"Options: couldn't read {key.SystemId}/{key.PathKey}: {e.Message}");
            }
        });
    }

    private void ShowGame()
    {
        Heading = _game.Title;
        var config = _options.Settings.Services.Config;
        var system = config.FindSystem(_game.Key.SystemId);
        string NameOf(string id) => config.Emulators.TryGetValue(id, out var e) ? e.Name : id;
        if (_game.EmulatorOverride is { } own)
        {
            _emulator.Detail = config.Emulators.ContainsKey(own) ? NameOf(own) : $"'{own}', which isn't configured any more: it can't launch until another is chosen";
            _emulator.DetailColour = config.Emulators.ContainsKey(own) ? UiStyle.Dim : UiStyle.Warning;
            _emulator.Value = "Its own";
        }
        else
        {
            _emulator.Detail = system is null ? "The system's" : $"The system's: {NameOf(system.Emulator)}";
            _emulator.DetailColour = UiStyle.Dim;
            _emulator.Value = "Change";
        }

        if (_ownModel is { } model)
        {
            _model.Detail = $"Its own, {ItemOptions.ModelsText(model.Report).Split('\n')[0]} · Y removes it";
            _model.Value = "Its own";
        }
        else
        {
            _model.Detail = $"The system's: {_options.Theme.GameModelInUse(_game.Key.SystemId)?.Description ?? "its template"} · A chooses a .glb";
            _model.Value = "Change";
        }

        var users = _mediaRows.Count(m => m.IsUsers && m.Kind != MediaKinds.Model);
        var scraped = _mediaRows.Count(m => !m.IsUsers && m.Kind != MediaKinds.Model);
        var counts = users == 0 ? $"{scraped} scraped" : scraped == 0 ? $"{users} yours" : $"{users} yours, {scraped} scraped";
        _media.Detail = users + scraped == 0
            ? "None yet: scrape it, or choose your own"
            : counts + " · " + string.Join(", ", MediaKinds.Images.Where(k => _mediaRows.Any(m => m.Kind == k)).Select(GameMediaPanel.SlotName));

        var metadata = _game.Metadata;
        var filled = metadata is null ? 0 : new[] { metadata.Description, metadata.ReleaseDate, metadata.Developer, metadata.Publisher, metadata.Genre, metadata.Players }
            .Count(v => v is not null) + (metadata.Rating is null ? 0 : 1);
        _metadata.Detail = (_game.TitleOverride is null ? "Title from " + (_game.Scrape is { Status: "ok" or "partial" } ? "scraping" : "the file name") : "Your title")
            + string.Create(CultureInfo.InvariantCulture, $" · {filled} of 7 fields filled")
            + (metadata?.Source.Contains("user", StringComparison.Ordinal) == true || _game.TitleOverride is not null ? ", some by you" : string.Empty);

        _scrape.Detail = _game.Scrape switch
        {
            null => "Never scraped",
            { Status: "ok" } s => $"Found by {string.Join(" and ", s.Providers.Select(ScrapingPage.NameOf))}, {DetailsFormatter.Relative(s.ScrapedAt, DateTimeOffset.Now)}",
            { Status: "partial" } s => $"Found by {string.Join(" and ", s.Providers.Select(ScrapingPage.NameOf))}, but a provider failed, {DetailsFormatter.Relative(s.ScrapedAt, DateTimeOffset.Now)}",
            { Status: "not_found" } s => $"Not found, {DetailsFormatter.Relative(s.ScrapedAt, DateTimeOffset.Now)}: edit its title to the game's name, then scrape it again",
            { } s => $"Failed {DetailsFormatter.Relative(s.ScrapedAt, DateTimeOffset.Now)}: a provider couldn't be reached",
        };
        _scrape.Value = _scraping ? "Running" : null;
    }

    // ---- Emulator ------------------------------------------------------------------------------------

    private void ChooseEmulator()
    {
        var config = _options.Settings.Services.Config;
        var system = config.FindSystem(_game.Key.SystemId);
        var suggested = new HashSet<string>(StringComparer.Ordinal);
        if (system is not null)
        {
            suggested.UnionWith(system.AltEmulators.Prepend(system.Emulator));
        }

        var systemsName = system is not null && config.Emulators.TryGetValue(system.Emulator, out var e) ? e.Name : system?.Emulator ?? "?";
        var choices = new List<Choice> { new(string.Empty, "The system's emulator", systemsName) };
        choices.AddRange(config.Emulators.Values
            .OrderBy(p => suggested.Contains(p.Id) ? 0 : 1)
            .ThenBy(p => p.Name, StringComparer.CurrentCultureIgnoreCase)
            .Select(p => new Choice(p.Id, p.Name, (suggested.Contains(p.Id) ? "Suggested · " : string.Empty) + p.Executable)));
        var key = _game.Key;
        Layer.Push(new ChoicePanel($"Emulator for {_game.Title}", "Only this game; the others keep the system's", choices, _game.EmulatorOverride ?? string.Empty, choice =>
            Run(library => library.SetEmulatorOverrideAsync(key, choice.Id.Length == 0 ? null : choice.Id, CancellationToken.None),
                choice.Id.Length == 0 ? $"It launches with the system's emulator, {systemsName}." : $"It launches with {choice.Title}.")));
    }

    /// <summary>A library write off the main thread, then a status, a reload and the grid told.</summary>
    private void Run(Func<LibraryService, Task> write, string done)
    {
        var options = _options;
        var key = _game.Key;
        _ = Task.Run(async () =>
        {
            string? failure = null;
            try
            {
                await write(options.Library).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                failure = e.Message;
            }

            options.Ui.Queue.Post(() =>
            {
                options.GameEdited(key);
                if (IsInstanceValid(this))
                {
                    ShowStatus(failure is null ? done : $"Not saved: {failure}", failure is null ? UiStyle.Good : UiStyle.Bad, 5);
                    Reload();
                }
            });
        });
    }

    // ---- Model ---------------------------------------------------------------------------------------

    private void PickModel()
    {
        FilePicker.Open(_options.Ui, new PickerRequest(
            $"A model for {_game.Title}",
            PickerMode.File,
            PickerUses.Model,
            ImportModel,
            Filter: FileFilter.ModelImports,
            Subtitle: "A .glb, or a zip of an OBJ model (.obj, .mtl and its textures): it replaces the system's template for this game"));
    }

    private void ImportModel(string file)
    {
        ShowStatus("Checking the model…", UiStyle.Dim);
        var options = _options;
        var key = _game.Key;
        _ = Task.Run(async () =>
        {
            ModelImportResult result;
            try
            {
                result = await options.Models.ImportGameModelAsync(key, file, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e) when (e is System.IO.IOException or UnauthorizedAccessException)
            {
                result = new ModelImportResult(ModelImportStatus.Unsupported, null, false, null, [e.Message]);
            }

            options.Ui.Queue.Post(() =>
            {
                if (!IsInstanceValid(this))
                {
                    return;
                }

                ShowStatus(null);
                Reload();
                ConfirmDialog.Tell(Layer, result.Status == ModelImportStatus.Imported ? "Model imported" : "Model not imported", ItemOptions.Describe(result));
            });
        });
    }

    private void RemoveModel()
    {
        if (_ownModel is not { } model)
        {
            ShowStatus("It shows the system's template: there's no model of its own to remove.", UiStyle.Dim, 4);
            return;
        }

        var options = _options;
        var key = _game.Key;
        ConfirmDialog.Ask(Layer, "Remove its model?", $"{model.Path} is deleted, and the game shows its system's template again.", "Remove it", "Keep it", yes =>
        {
            if (!yes)
            {
                return;
            }

            _ = Task.Run(async () =>
            {
                var result = await options.Models.RemoveGameModelAsync(key, CancellationToken.None).ConfigureAwait(false);
                options.Ui.Queue.Post(() =>
                {
                    if (IsInstanceValid(this))
                    {
                        ShowStatus(result.Status switch
                        {
                            ModelRemoveStatus.Removed => "Its model was removed.",
                            ModelRemoveStatus.Shared => $"{result.SharedPath} is every game of that name's, so it was left alone.",
                            _ => "It had no model of its own.",
                        }, result.Status == ModelRemoveStatus.Removed ? UiStyle.Good : UiStyle.Warning, 6);
                        Reload();
                    }
                });
            });
        }, destructive: true);
    }

    // ---- Scraping ------------------------------------------------------------------------------------

    private void Scrape()
    {
        if (_scraping)
        {
            return;
        }

        if (!_options.Jobs.ScrapeGame(_game.Key, _game.Title, Scraped))
        {
            ShowStatus("It's being scraped already.", UiStyle.Dim, 4);
            return;
        }

        _scraping = true;
        _scrape.Value = "Running";
        ShowStatus($"Scraping {_game.Title}…", UiStyle.Dim);
    }

    private void Scraped(string outcome)
    {
        _scraping = false;
        if (IsInstanceValid(this))
        {
            ShowStatus(outcome, UiStyle.Text, 8);
            Reload();
        }
    }

    private void AskToClear()
    {
        var title = _game.Title;
        ConfirmDialog.Ask(Layer, "Clear this game's metadata?",
            $"This removes, for {title}:\n" +
            "• everything scraped: its metadata, its scraped images and the saved responses\n" +
            "• all its images, including the ones you chose yourself (their files are deleted)\n" +
            "• its own model\n" +
            "• your edits to its title and metadata\n\n" +
            "Its favourite, play history and emulator stay. Scrape it again to get its metadata back.",
            "Clear it", "Keep it", yes =>
            {
                if (yes)
                {
                    Clear();
                }
            }, destructive: true);
    }

    private void Clear()
    {
        ShowStatus("Clearing…", UiStyle.Dim);
        var options = _options;
        var key = _game.Key;
        _ = Task.Run(async () =>
        {
            string message;
            try
            {
                var result = await options.Jobs.ClearGameAsync(key, CancellationToken.None).ConfigureAwait(false);
                message = !result.Found
                    ? "It isn't in the library any more."
                    : string.Create(CultureInfo.InvariantCulture, $"Cleared: {result.FilesDeleted} file{(result.FilesDeleted == 1 ? string.Empty : "s")} removed.")
                      + (result.KeptSharedArt.Count > 0 ? $" Kept {string.Join(", ", result.KeptSharedArt)}: other games of that name use it." : string.Empty);
            }
            catch (Exception e)
            {
                message = $"It couldn't be cleared: {e.Message}";
            }

            options.Ui.Queue.Post(() =>
            {
                if (IsInstanceValid(this))
                {
                    ShowStatus(message, UiStyle.Text, 8);
                    Reload();
                }
            });
        });
    }
}
