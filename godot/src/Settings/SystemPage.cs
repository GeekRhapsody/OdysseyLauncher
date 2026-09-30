using System;
using System.Collections.Generic;
using System.Linq;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Files;

namespace Launcher.App.Settings;

/// <summary>
/// One system's settings (M7): its ROM folders (several are allowed, scanned in order; the default is the first of
/// <c>{rom_root}/&lt;id&gt;</c> and its aliases that exists) and the emulator it launches with. Saving folders
/// rescans the system.
/// </summary>
public sealed partial class SystemPage : ListPanel
{
    private readonly SettingsController _settings;
    private readonly string _systemId;
    private readonly List<(SettingRow Row, int Index)> _folderRows = [];

    public SystemPage(SettingsController settings, string systemId)
        : base(settings.Services.Config.FindSystem(systemId)?.Name ?? systemId)
    {
        _settings = settings;
        _systemId = systemId;
        Subtitle = $"systems.{systemId} in systems.toml";
        Build();
        SetHints("A  Change     Y  Remove a folder     B  Back");
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

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
    }

    public override bool Handle(NavCommand command)
    {
        if (command != NavCommand.Favourite)
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

        return false;
    }

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
            .Select(e => new Choice(e.Id, e.Name, (suggested.Contains(e.Id) ? "Suggested · " : string.Empty) + e.Executable))
            .ToList();
        Layer.Push(new ChoicePanel($"Emulator for {system.Name}", "Games can still choose their own", choices, system.Emulator, choice =>
            _settings.Save(this, [new ConfigEdit(ConfigFileKind.Systems, ["systems", _systemId, "emulator"], choice.Id)], $"{system.Name} now launches with {choice.Title}.")));
    }
}
