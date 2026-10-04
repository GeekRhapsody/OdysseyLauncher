using System;
using System.Globalization;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Files;
using Launcher.Core.Media;

namespace Launcher.App.Settings;

/// <summary>
/// Where the media folder is (2026-10-04, A4): every game's images, videos and models, a folder per system in it. By
/// default it's in the data folder; another folder is saved as <c>[paths] media</c>. Choosing one asks whether to move
/// the media there (<see cref="MediaMovePanel"/>) or to use the folder as it is (one that has the media already). Either
/// way the library is rescanned, and the theme loaded again for per-game models.
/// </summary>
public sealed partial class MediaFolderPage : ListPanel
{
    private readonly SettingsController _settings;
    private Label _contents = null!;
    private CancellationTokenSource? _counting;
    private bool _planning;

    public MediaFolderPage(SettingsController settings)
        : base("Media folder")
    {
        _settings = settings;
        Build();
        SetHints("A  Choose     B  Back");
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed()
    {
        _settings.ConfigApplied -= Rebuild;
        _counting?.Cancel();
    }

    private string Current => _settings.Services.Library.MediaDir;

    private string DefaultFolder => MediaFolder.Default(_settings.Services.Paths.DataDir);

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var isDefault = _settings.Services.Config.Settings.MediaDir is null;
        AddRow("Folder", Current, "Change", ChooseFolder);
        AddRow("Use the default folder", DefaultFolder, isDefault ? "In use" : null, UseDefault).ValueColour = UiStyle.Good;
        _contents = AddNote("Counting its files…");
        AddNote("Every game's covers, screenshots, logos, videos and models, scraped or your own, with a folder per system in it. "
            + "When you choose another folder, your media can move there with it, and every game keeps its art.");
        Count();
    }

    /// <summary>What's in the media folder, counted on the thread pool.</summary>
    private void Count()
    {
        _counting?.Cancel();
        var cancel = _counting = new CancellationTokenSource();
        var folder = Current;
        _ = Task.Run(() =>
        {
            string text;
            try
            {
                if (!Directory.Exists(folder))
                {
                    text = "It doesn't exist yet: scraping, or your own art, makes it.";
                }
                else
                {
                    var plan = MediaFolderMove.Plan(folder, folder, cancel.Token);
                    text = plan.Files.Count == 0
                        ? "It's empty."
                        : string.Create(CultureInfo.InvariantCulture, $"In it: {plan.Files.Count:N0} file{(plan.Files.Count == 1 ? string.Empty : "s")}, {UiStyle.Size(plan.Bytes)}.");
                }
            }
            catch (OperationCanceledException)
            {
                return;
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                text = $"It can't be read: {e.Message}";
            }

            _settings.Ui.Queue.Post(() =>
            {
                if (!cancel.IsCancellationRequested && IsInstanceValid(_contents))
                {
                    _contents.Text = text;
                }
            });
        }, cancel.Token);
    }

    private void ChooseFolder()
    {
        if (Busy())
        {
            return;
        }

        FilePicker.Open(_settings.Ui, new PickerRequest(
            "Choose the media folder",
            PickerMode.Folder,
            PickerUses.MediaFolder,
            folder => Change(folder),
            Start: Directory.Exists(Current) ? Current : null,
            Subtitle: "Open the folder for your media, then press X or choose Use this folder"));
    }

    private void UseDefault()
    {
        if (_settings.Services.Config.Settings.MediaDir is null)
        {
            ShowStatus("The default folder is in use already.", UiStyle.Dim, 4);
            return;
        }

        if (!Busy())
        {
            Change(DefaultFolder);
        }
    }

    /// <summary>A scan, a scrape or an import writes to the media folder, so the folder can't change while one runs.</summary>
    private bool Busy()
    {
        if (_settings.Jobs.UsingMedia is not { } busy)
        {
            return false;
        }

        ConfirmDialog.Tell(Layer, "Not now", $"Wait for {busy} to finish first: it uses the media folder. Its progress is on the settings screen.");
        return true;
    }

    /// <summary>Checks the folder and counts what would move (thread pool), then asks what to do with the media.</summary>
    private void Change(string target)
    {
        if (_planning || Busy())
        {
            return;
        }

        var from = Current;
        var dataDir = _settings.Services.Paths.DataDir;
        var toDefault = MediaFolder.Same(target, MediaFolder.Default(dataDir));
        _planning = true;
        ShowStatus("Looking at the folders…", UiStyle.Dim);
        _ = Task.Run(() =>
        {
            string? problem;
            MediaMovePlan? plan = null;
            try
            {
                problem = MediaFolderMove.Problem(from, target);
                if (problem is null && toDefault)
                {
                    Directory.CreateDirectory(target);
                }
                else
                {
                    problem ??= ConfigInput.CheckFolder(target);
                }

                if (problem is null)
                {
                    plan = MediaFolderMove.Plan(from, target, CancellationToken.None);
                }
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                problem = e.Message;
            }

            _settings.Ui.Queue.Post(() => Planned(plan, problem, toDefault));
        });
    }

    private void Planned(MediaMovePlan? plan, string? problem, bool toDefault)
    {
        _planning = false;
        ShowStatus(null);
        if (Layer?.Top != this)
        {
            return;
        }

        if (plan is null)
        {
            ConfirmDialog.Tell(Layer, "That folder can't be used", problem ?? "It couldn't be read.");
            return;
        }

        // The default is no key at all, so the setting follows the data folder (a portable install moving, say).
        var edit = new ConfigEdit(ConfigFileKind.Settings, ["paths", "media"], toDefault ? null : ConfigWriter.PathValue(plan.To));
        if (plan.Files.Count == 0)
        {
            UseAsItIs(edit, plan.To);
            return;
        }

        var what = string.Create(CultureInfo.InvariantCulture,
            $"{plan.Files.Count:N0} file{(plan.Files.Count == 1 ? string.Empty : "s")} ({UiStyle.Size(plan.Bytes)}) in the media folder now");
        Layer.Push(new ChoicePanel("Your media", what, [
            new Choice("move", "Move it there",
                plan.SameVolume
                    ? "Each file moves at once: it's the same drive."
                    : "Each file is copied, then deleted from the old folder once the new one is in use."),
            new Choice("keep", "Use the folder as it is",
                "For a folder that has your media already. The old folder's files stay where they are, unused."),
        ], null, choice =>
        {
            if (choice.Id == "move")
            {
                Layer.Push(new MediaMovePanel(_settings, this, plan, edit));
            }
            else
            {
                UseAsItIs(edit, plan.To);
            }
        }));
    }

    /// <summary>Saves the new folder without moving anything, then rescans so the library has what's in it.</summary>
    private void UseAsItIs(ConfigEdit edit, string folder) =>
        _settings.Save(this, [edit], "Media folder saved. Rescanning the library…", then: result =>
        {
            if (result.ChangedFiles.Count > 0)
            {
                GD.Print($"Settings: the media folder is {folder} now.");
                _settings.MediaFolderMoved(_settings.Services.Library.MediaDir);
            }
        });
}
