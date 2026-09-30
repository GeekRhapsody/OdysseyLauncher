using System.Linq;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Files;

namespace Launcher.App.Settings;

/// <summary>
/// The ROM root and each system's folders (M7). By default a system's games are in <c>{rom_root}/&lt;id&gt;</c> (or an
/// alias's folder); a system can have folders of its own instead. Changing the root rescans every system that
/// uses it; changing a system's folders rescans that system.
/// </summary>
public sealed partial class RomFoldersPage : ListPanel
{
    private readonly SettingsController _settings;

    public RomFoldersPage(SettingsController settings)
        : base("ROM folders")
    {
        _settings = settings;
        Build();
        SetHints("A  Change     B  Back");
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    public override void OnRevealed() => Rebuild(_settings.Services.Config);

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var config = _settings.Services.Config;
        AddRow("ROM root", config.Settings.RomRoot, "Change", ChooseRoot);
        AddNote("Each system's games are in a folder named after it under the ROM root (megadrive, snes…), unless it has folders of its own.");
        AddSection("Systems");
        foreach (var system in config.Systems)
        {
            var captured = system;
            string detail;
            if (system.RomDirSource == RomDirSource.Default)
            {
                detail = system.RomDirs.Count > 0 ? system.RomDirs[0] : config.Settings.RomRoot;
            }
            else
            {
                detail = system.RomDirs.Count == 1 ? system.RomDirs[0] : $"{system.RomDirs[0]} and {system.RomDirs.Count - 1} more";
            }

            var row = AddRow(system.Name, detail, system.RomDirSource == RomDirSource.Default ? "Default" : "Its own",
                () => Layer.Push(new SystemPage(_settings, captured.Id)));
            if (system.RomDirSource == RomDirSource.Configured)
            {
                row.ValueColour = UiStyle.Warning;
            }
        }
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
                            _settings.Rescan?.Invoke(usesRoot);
                        }
                    },
                    check: () => ConfigInput.CheckFolder(folder));
            },
            Start: root,
            Subtitle: "Open the folder that holds a folder per system, then press X or choose Use this folder"));
    }
}
