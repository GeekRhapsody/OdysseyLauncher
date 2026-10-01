using System;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Screens;
using Launcher.App.Settings;
using Launcher.App.Ui;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Models;

namespace Launcher.App.Options;

/// <summary>
/// The item options panels (M7 part 2): X on a system or a game in the grids opens its options, on the settings
/// screen's layer and with its components (pickers, keyboard, dialogs, progress). It owns the services they use (the
/// user's models and images) and tells the grid what changed: a game's media and model follow the library's
/// MediaChanged, its title and details <see cref="LibraryJobs.GamesUpdated"/>, and a system's own models or
/// template a theme reload, so nothing needs a restart.
/// </summary>
public sealed class ItemOptions
{
    private readonly Navigator _navigator;
    private bool _opening;

    public ItemOptions(SettingsController settings, Navigator navigator)
    {
        Settings = settings;
        _navigator = navigator;
        var services = settings.Services;
        Models = new ModelImportService(services.Library, services.Paths, settings.Ui.Decoder);
        Art = new UserArtService(services.Library, services.Paths, services.Derivatives);
    }

    public SettingsController Settings { get; }

    public ModelImportService Models { get; }

    public UserArtService Art { get; }

    public LibraryJobs Jobs => Settings.Jobs;

    public UiLayer Layer => Settings.Layer;

    public UiContext Ui => Settings.Ui;

    public LibraryService Library => Settings.Services.Library;

    /// <summary>The theme the grids show, to say which model a system and its games use.</summary>
    public Theming.ThemeRuntime Theme => _navigator.Theme;

    /// <summary>Opens a system's options. Main thread.</summary>
    public SystemPage OpenSystem(string systemId)
    {
        var page = new SystemPage(Settings, systemId);
        Layer.Push(page);
        return page;
    }

    /// <summary>Opens a game's options once its details are read (off the main thread). Main thread.</summary>
    public void OpenGame(long gameId)
    {
        if (_opening)
        {
            return;
        }

        _opening = true;
        var library = Library;
        _ = Task.Run(async () =>
        {
            GameDetails? game = null;
            try
            {
                game = await library.GetGameAsync(gameId, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                GD.PushError($"Options: couldn't read game {gameId}: {e.Message}");
            }

            Ui.Queue.Post(() =>
            {
                _opening = false;
                if (game is not null && !Layer.IsOpen)
                {
                    Layer.Push(new GameOptionsPanel(this, game));
                }
            });
        });
    }

    /// <summary>
    /// Main thread: a system's own models or its template choice changed, so the theme is resolved again and applied
    /// (in the background, as a theme switch is).
    /// </summary>
    public void SystemModelsChanged() => _navigator.ReloadTheme();

    /// <summary>Main thread: a game's title, metadata or emulator was edited.</summary>
    public void GameEdited(GameKey game) => Jobs.GameEdited(game);

    /// <summary>The system's name, from config.</summary>
    public string SystemName(string systemId) => Settings.Services.Config.FindSystem(systemId)?.Name ?? systemId;

    /// <summary>A model import's outcome, written for the user (a dialog's text).</summary>
    public static string Describe(ModelImportResult result)
    {
        var text = result.Status switch
        {
            ModelImportStatus.Imported => result.Converted ? "Converted from OBJ and imported." : "Imported.",
            ModelImportStatus.Rejected => "It wasn't imported, and nothing changed.",
            ModelImportStatus.NotInLibrary => "It isn't in the library any more: rescan first.",
            _ => "It isn't a model the launcher can import.",
        };
        if (result.Report is { } report)
        {
            text += "\n\n" + ModelsText(report);
        }

        foreach (var message in result.Messages)
        {
            text += "\n• " + message;
        }

        return text;
    }

    /// <summary>A model's counts and problems from its report.</summary>
    public static string ModelsText(ModelReport report)
    {
        var text = FormattableString.Invariant(
            $"{report.Triangles:N0} triangle{Plural(report.Triangles)}, {report.Materials} material{Plural(report.Materials)}, {report.Textures} texture{Plural(report.Textures)}");
        if (report.Slots.Count > 0)
        {
            text += "; shows " + string.Join(", ", report.Slots);
        }

        foreach (var error in report.Errors)
        {
            text += "\n• " + error;
        }

        foreach (var warning in report.Warnings)
        {
            text += "\n• " + warning;
        }

        return text;
    }

    private static string Plural(int count) => count == 1 ? string.Empty : "s";
}
