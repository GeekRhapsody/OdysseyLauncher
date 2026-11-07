using System.Linq;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Files;
using Launcher.Core.Library;

namespace Launcher.App.Settings;

/// <summary>
/// Settings, Library (2026-11-07): the ROM root and the media folder, the rescans, and whether the library is scanned at
/// launch. Changing the root rescans every system that uses it. A running scan's row, to cancel it, is at the top of
/// <see cref="SettingsHome"/>.
/// </summary>
public sealed partial class LibraryPage : ListPanel
{
    private readonly SettingsController _settings;
    private readonly SettingRow _root;
    private readonly SettingRow _media;
    private readonly SettingRow _rescan;
    private readonly SettingRow _rescanMedia;
    private readonly SettingRow _scanAtLaunch;

    public LibraryPage(SettingsController settings)
        : base("Library")
    {
        _settings = settings;
        Subtitle = "Where your games and media are, and when they're scanned";

        AddSection("Folders");
        _root = AddRow("ROM root", value: "Change", activated: ChooseRoot);
        _media = AddRow("Media folder", activated: () => Layer.Push(new MediaFolderPage(_settings)));
        AddNote("Each system's games are in a folder named after it under the ROM root (megadrive, snes…). A system can have folders of its own: Settings > Systems, then the system.");

        AddSection("Scanning");
        _rescan = AddRow("Rescan the library", "Look for new, moved and removed games in every ROM folder, and for media only where there are new games",
            activated: () => Rescan(RescanMedia.SystemsWithNewGames));
        _rescanMedia = AddRow("Rescan the library and media", "Every ROM folder and every media folder: for art, videos or models you added or removed yourself",
            activated: () => Rescan(RescanMedia.All));
        _scanAtLaunch = AddRow("Rescan when the launcher starts", "Look for new and removed games in the ROM folders, in the background, each time the launcher starts",
            activated: () => SetScanAtLaunch(null));
        _scanAtLaunch.Adjuster = direction => SetScanAtLaunch(direction > 0);

        SetHints(CommonHints.ChooseChangeBack);
        _settings.ConfigApplied += OnConfigApplied;
        _settings.Jobs.Jobs.Changed += ShowJobs;
        Refresh();
        ShowJobs();
    }

    public override void OnRevealed() => Refresh();

    public override void OnClosed()
    {
        _settings.ConfigApplied -= OnConfigApplied;
        _settings.Jobs.Jobs.Changed -= ShowJobs;
    }

    private void OnConfigApplied(AppConfig config) => Refresh();

    private void Refresh()
    {
        var services = _settings.Services;
        var config = services.Config;
        var custom = config.Systems.Count(s => s.RomDirSource == RomDirSource.Configured);
        _root.Detail = custom == 0
            ? $"{config.Settings.RomRoot}, a folder per system"
            : $"{config.Settings.RomRoot}; {custom} system{(custom == 1 ? " has" : "s have")} its own";
        _media.Detail = config.Settings.MediaDir is null
            ? $"{services.Library.MediaDir}, the default: covers, videos and models"
            : $"{services.Library.MediaDir}: covers, videos and models";
        var on = config.Settings.Scanning.ScanAtLaunch;
        _scanAtLaunch.Value = on ? "Yes" : "No";
        _scanAtLaunch.ValueColour = on ? UiStyle.Good : UiStyle.Faint;
    }

    private void ShowJobs()
    {
        var scanning = _settings.Jobs.ScanningMedia;
        _rescan.Value = scanning == RescanMedia.SystemsWithNewGames ? "Running" : null;
        _rescanMedia.Value = scanning == RescanMedia.All ? "Running" : null;
    }

    private void ChooseRoot()
    {
        var root = _settings.Services.Config.Settings.RomRoot;
        FilePicker.Open(_settings.Ui, new PickerRequest(
            "Choose the ROM root",
            PickerMode.Folder,
            PickerUses.RomRoot,
            folder =>
            {
                var usesRoot = _settings.Services.Config.Systems.Where(s => s.RomDirSource == RomDirSource.Default).Select(s => s.Id).ToList();
                _settings.Save(this,
                    [new ConfigEdit(ConfigFileKind.Settings, ["paths", "rom_root"], ConfigWriter.PathValue(folder))],
                    usesRoot.Count == 0 ? "ROM root saved." : "ROM root saved. Rescanning the systems that use it…",
                    then: result =>
                    {
                        if (result.ChangedFiles.Count > 0 && usesRoot.Count > 0)
                        {
                            _settings.Rescan?.Invoke(usesRoot, RescanMedia.All);
                        }
                    },
                    check: () => ConfigInput.CheckFolder(folder));
            },
            Start: root,
            Subtitle: "Open the folder that holds a folder per system, then press X or choose Use this folder"));
    }

    /// <param name="media">Every media folder, or only those of systems with new games.</param>
    private void Rescan(RescanMedia media)
    {
        if (_settings.Jobs.Scanning)
        {
            ShowStatus("A scan is already running: it's at the top of the settings.", UiStyle.Dim, 4);
            return;
        }

        _settings.Rescan?.Invoke(null, media);
    }

    /// <param name="on">Scanned at launch or not; null turns it the other way. It's saved as <c>[scanning] scan_at_launch</c>.</param>
    private void SetScanAtLaunch(bool? on)
    {
        var current = _settings.Services.Config.Settings.Scanning.ScanAtLaunch;
        var wanted = on ?? !current;
        if (current == wanted)
        {
            return;
        }

        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["scanning", "scan_at_launch"], wanted)],
            wanted ? "The library is rescanned each time the launcher starts." : "The library isn't rescanned when the launcher starts (only systems never scanned are).");
    }
}
