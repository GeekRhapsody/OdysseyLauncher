using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Files;

namespace Launcher.App.Settings;

/// <summary>
/// Emulator profiles and their executables (M7). Each row says whether its program is there (checked off the main
/// thread); A picks another with the file picker (.exe only: batch files are rejected, A5). Several profiles
/// sharing one install (every RetroArch core) can be moved together: when they share it through a variable in
/// settings.toml ({retroarch}), that variable is what changes, so their cores move with it.
/// </summary>
public sealed partial class EmulatorsPage : ListPanel
{
    private readonly SettingsController _settings;
    private readonly Dictionary<string, SettingRow> _rows = new(StringComparer.Ordinal);
    private int _check;

    public EmulatorsPage(SettingsController settings)
        : base("Emulators")
    {
        _settings = settings;
        Subtitle = "Profiles used by systems that have games; each system chooses one on its own page";
        Build();
        SetHints("A  Choose the program     B  Back");
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        _rows.Clear();
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var config = _settings.Services.Config;

        // The built-in catalogue has hundreds of profiles, so with empty systems hidden only the profiles that
        // systems with games use are listed (every profile can still be chosen on a system's own page).
        var hideEmpty = config.Settings.Display.HideEmptySystems;
        var withGames = new HashSet<string>(StringComparer.Ordinal);
        foreach (var summary in _settings.Services.Systems)
        {
            if (summary.GameCount > 0)
            {
                withGames.Add(summary.SystemId);
            }
        }

        var used = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        foreach (var system in config.Systems)
        {
            if (hideEmpty && !withGames.Contains(system.Id))
            {
                continue;
            }

            foreach (var id in system.AltEmulators.Prepend(system.Emulator))
            {
                if (!used.TryGetValue(id, out var names))
                {
                    used[id] = names = [];
                }

                if (!names.Contains(system.Name))
                {
                    names.Add(system.Name);
                }
            }
        }

        // A profile that runs the game's own file (a shortcut or program) has no program to choose.
        var profiles = config.Emulators.Values
            .Where(e => !e.RunFile && (!hideEmpty || used.ContainsKey(e.Id)))
            .OrderBy(e => used.ContainsKey(e.Id) ? 0 : 1)
            .ThenBy(e => e.Name, StringComparer.CurrentCultureIgnoreCase)
            .ToList();
        var inUse = true;
        AddSection(hideEmpty && profiles.Count == 0 ? "No system has games yet" : "Used by your systems");
        foreach (var profile in profiles)
        {
            if (inUse && !used.ContainsKey(profile.Id))
            {
                inUse = false;
                AddSection("Other profiles");
            }

            var captured = profile;
            var systems = used.TryGetValue(profile.Id, out var names) ? $" · {string.Join(", ", names.Take(3))}{(names.Count > 3 ? $" and {names.Count - 3} more" : string.Empty)}" : string.Empty;
            var row = AddRow(profile.Name, profile.Executable + systems, "Checking…", () => ChooseProgram(captured));
            row.ValueColour = UiStyle.Dim;
            _rows[profile.Id] = row;
        }

        CheckInstalls(profiles.Select(p => (p.Id, p.Executable, p.Core)).ToList());
    }

    /// <summary>Whether each program (and core) exists: file I/O, so on a worker; an unplugged drive can't stall the page.</summary>
    private void CheckInstalls(List<(string Id, string Executable, string? Core)> profiles)
    {
        var check = ++_check;
        _ = Task.Run(() =>
        {
            var results = new List<(string Id, string Value, bool Found)>();
            foreach (var (id, executable, core) in profiles)
            {
                var found = File.Exists(executable);
                var coreFound = core is null || File.Exists(core);
                results.Add((id, !found ? "Not found" : !coreFound ? "Core missing" : "Found", found && coreFound));
            }

            _settings.Ui.Queue.Post(() =>
            {
                if (check != _check)
                {
                    return;
                }

                foreach (var (id, value, found) in results)
                {
                    if (_rows.TryGetValue(id, out var row) && IsInstanceValid(row))
                    {
                        row.Value = value;
                        row.ValueColour = found ? UiStyle.Good : UiStyle.Warning;
                    }
                }
            });
        });
    }

    private void ChooseProgram(Launcher.Core.Config.EmulatorConfig profile)
    {
        FilePicker.Open(_settings.Ui, new PickerRequest(
            $"The program for {profile.Name}",
            PickerMode.File,
            PickerUses.Emulator,
            file => Chosen(profile, file),
            Filter: FileFilter.Executables,
            Start: profile.Executable,
            Subtitle: OperatingSystem.IsWindows() ? "The emulator's .exe" : "The emulator's program"));
    }

    private void Chosen(Launcher.Core.Config.EmulatorConfig profile, string file)
    {
        var config = _settings.Services.Config;
        var sharing = config.Emulators.Values.Where(e => e.Id != profile.Id && SamePath(e.Executable, profile.Executable)).ToList();
        if (sharing.Count == 0)
        {
            SaveOne(profile, file);
            return;
        }

        ConfirmDialog.Ask(Layer, "Change it for the others too?",
            $"{sharing.Count + 1} profiles use {profile.Executable}, including {string.Join(", ", sharing.Take(3).Select(e => e.Name))}{(sharing.Count > 3 ? " and more" : string.Empty)}.\n\nChange all of them to {file}, or only {profile.Name}?",
            $"All {sharing.Count + 1}", "Only this one", all =>
            {
                if (all)
                {
                    SaveAll(profile, sharing, file);
                }
                else
                {
                    SaveOne(profile, file);
                }
            });
    }

    private void SaveOne(Launcher.Core.Config.EmulatorConfig profile, string file) =>
        _settings.Save(this,
            [new ConfigEdit(ConfigFileKind.Emulators, ["emulators", profile.Id, "executable"], ConfigWriter.PathValue(file))],
            $"{profile.Name} now runs {Path.GetFileName(file)}.",
            check: () => ConfigInput.CheckExecutable(file));

    /// <summary>
    /// Moves every profile sharing <paramref name="profile"/>'s program. When they share it through a variable (the
    /// program is <c>{variable}/name.exe</c> and the new one has the same name), the variable moves, and the cores
    /// under it with it; otherwise each profile gets the new path.
    /// </summary>
    private void SaveAll(Launcher.Core.Config.EmulatorConfig profile, List<Launcher.Core.Config.EmulatorConfig> sharing, string file)
    {
        var config = _settings.Services.Config;
        var oldFolder = Path.GetDirectoryName(profile.Executable);
        var variable = config.Settings.Variables
            .Where(v => oldFolder is not null && SamePath(ExpandedFolder(v.Value), oldFolder))
            .Select(v => v.Key)
            .FirstOrDefault();
        var sameName = string.Equals(Path.GetFileName(file), Path.GetFileName(profile.Executable), StringComparison.OrdinalIgnoreCase);
        List<ConfigEdit> edits;
        string saved;
        if (variable is not null && sameName)
        {
            edits = [new ConfigEdit(ConfigFileKind.Settings, ["variables", variable], ConfigWriter.PathValue(Path.GetDirectoryName(file)!))];
            saved = $"{{{variable}}} is now {Path.GetDirectoryName(file)}: {sharing.Count + 1} profiles and their cores use it.";
        }
        else
        {
            edits = sharing.Prepend(profile)
                .Select(e => new ConfigEdit(ConfigFileKind.Emulators, ["emulators", e.Id, "executable"], ConfigWriter.PathValue(file)))
                .ToList();
            saved = $"{sharing.Count + 1} profiles now run {Path.GetFileName(file)}.";
        }

        _settings.Save(this, edits, saved, check: () => ConfigInput.CheckExecutable(file));
    }

    private static string ExpandedFolder(string value)
    {
        try
        {
            return Path.GetFullPath(value);
        }
        catch (Exception e) when (e is ArgumentException or NotSupportedException or PathTooLongException)
        {
            return value;
        }
    }

    private static bool SamePath(string a, string b) =>
        string.Equals(Path.TrimEndingDirectorySeparator(a), Path.TrimEndingDirectorySeparator(b), OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);
}
