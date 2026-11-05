using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Files;
using Launcher.Core.Launching;

namespace Launcher.App.Settings;

/// <summary>
/// Emulator profiles and their executables (M7). First the folders the built-in profiles look in, as the ROM root is
/// for ROMs: the emulators folder (<c>{emulators}</c>, a folder per emulator under it, named as ES-DE names them) and
/// RetroArch's (<c>{retroarch}</c>), each a variable in settings.toml. Then each profile: whether its program is in one
/// of its places (checked off the main thread: A5 Finding programs); A picks another with the file picker (.exe only:
/// batch files are rejected, A5). Several profiles sharing one install (every RetroArch core) can be moved together:
/// when they share it through a variable in settings.toml ({retroarch}), that variable is what changes, so their cores
/// move with it. On Linux those variables are lists of places, not folders, so there are no folder rows.
/// </summary>
public sealed partial class EmulatorsPage : ListPanel
{
    /// <summary>The variables the built-in profiles' programs sit under, with their rows' titles and what they're for.</summary>
    private static readonly (string Variable, string Title, string Detail)[] Folders =
    [
        ("emulators", "Emulators folder", "A folder per emulator, named as ES-DE names them"),
        ("retroarch", "RetroArch folder", "RetroArch and its cores"),
    ];

    private readonly SettingsController _settings;
    private readonly Dictionary<string, SettingRow> _rows = new(StringComparer.Ordinal);

    /// <summary>Each profile's program where the check found it among several places, and the systems its row names.</summary>
    private readonly Dictionary<string, string> _found = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _systemsText = new(StringComparer.Ordinal);
    private int _check;

    public EmulatorsPage(SettingsController settings)
        : base("Emulators")
    {
        _settings = settings;
        Subtitle = "Where your emulators are, and the profiles your systems with games offer";
        Build();
        SetHints(CommonHints.ChangeBack);
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        _rows.Clear();
        _found.Clear();
        _systemsText.Clear();
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var config = _settings.Services.Config;

        var folders = Folders.Where(f => config.Settings.Variables.ContainsKey(f.Variable)).ToList();
        if (folders.Count > 0)
        {
            AddSection("Folders");
            foreach (var (variable, title, detail) in folders)
            {
                var captured = variable;
                AddRow(title, $"{ExpandedFolder(config.Settings.Variables[variable])} · {detail}", "Change", () => ChooseFolder(captured, title));
            }

            AddNote("The built-in profiles look for their programs under these folders. A profile given a program of its own keeps it.");
        }
        else
        {
            AddNote("The built-in profiles look for each program on the PATH, in Flatpak's apps, and in ~/Applications, " +
                "~/.local/share/applications, ~/.local/bin and ~/bin ([variables] in settings.toml). A profile " +
                "given a program of its own keeps it.");
        }

        // The built-in catalogue has hundreds of profiles, so with empty systems hidden only the profiles that
        // systems with games offer (their default and alternatives) are listed.
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

            foreach (var id in system.OfferedEmulators())
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
            var row = AddRow(profile.Name, profile.ProgramText + systems, "Checking…", () => ChooseProgram(captured));
            row.ValueColour = UiStyle.Dim;
            _rows[profile.Id] = row;
            _systemsText[profile.Id] = systems;
        }

        CheckInstalls(profiles);
    }

    /// <summary>
    /// Whether each program (and core) is in one of its places: file I/O, so on a worker; an unplugged drive can't
    /// stall the page. A program found among several places shows where.
    /// </summary>
    private void CheckInstalls(List<Launcher.Core.Config.EmulatorConfig> profiles)
    {
        var check = ++_check;
        _ = Task.Run(() =>
        {
            var results = new List<(string Id, string Value, bool Found, string? Program)>();
            foreach (var profile in profiles)
            {
                var (resolved, found, coreFound) = ProgramSearch.System.Resolve(profile);
                var program = found && profile.ProgramPlaces.Count > 1 ? resolved.Executable : null;
                results.Add((profile.Id, !found ? "Not found" : !coreFound ? "Core missing" : "Found", found && coreFound, program));
            }

            _settings.Ui.Queue.Post(() =>
            {
                if (check != _check)
                {
                    return;
                }

                foreach (var (id, value, found, program) in results)
                {
                    if (!_rows.TryGetValue(id, out var row) || !IsInstanceValid(row))
                    {
                        continue;
                    }

                    row.Value = value;
                    row.ValueColour = found ? UiStyle.Good : UiStyle.Warning;
                    if (program is not null)
                    {
                        _found[id] = program;
                        row.Detail = program + _systemsText.GetValueOrDefault(id);
                    }
                }
            });
        });
    }

    /// <summary>Points <paramref name="variable"/> at another folder; every profile under it moves with it.</summary>
    private void ChooseFolder(string variable, string title)
    {
        var current = _settings.Services.Config.Settings.Variables.GetValueOrDefault(variable);
        FilePicker.Open(_settings.Ui, new PickerRequest(
            $"Choose the {title.ToLowerInvariant()}",
            PickerMode.Folder,
            PickerUses.EmulatorsFolder,
            folder => _settings.Save(this,
                [new ConfigEdit(ConfigFileKind.Settings, ["variables", variable], ConfigWriter.PathValue(folder))],
                $"{title} saved: {{{variable}}} is now {folder}.",
                check: () => ConfigInput.CheckFolder(folder)),
            Start: current,
            Subtitle: variable == "retroarch"
                ? $"Open the folder with {(OperatingSystem.IsWindows() ? "retroarch.exe" : "RetroArch's program")}, then press X or choose Use this folder"
                : "Open the folder that holds a folder per emulator, then press X or choose Use this folder"));
    }

    private void ChooseProgram(Launcher.Core.Config.EmulatorConfig profile)
    {
        FilePicker.Open(_settings.Ui, new PickerRequest(
            $"The program for {profile.Name}",
            PickerMode.File,
            PickerUses.Emulator,
            file => Chosen(profile, file),
            Filter: FileFilter.Executables,
            Start: _found.GetValueOrDefault(profile.Id) ?? (ProgramSearch.IsBareName(profile.Executable) ? null : profile.Executable),
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
    /// under it with it; when they share a list of places (Linux's <c>{retroarch}</c>), the list becomes the one program;
    /// otherwise each profile gets the new path.
    /// </summary>
    private void SaveAll(Launcher.Core.Config.EmulatorConfig profile, List<Launcher.Core.Config.EmulatorConfig> sharing, string file)
    {
        if (profile.ProgramVariable is { } list && sharing.All(e => e.ProgramVariable == list))
        {
            _settings.Save(this,
                [new ConfigEdit(ConfigFileKind.Settings, ["variables", list], ConfigWriter.PathValue(file))],
                $"{{{list}}} is now {file}: {sharing.Count + 1} profiles use it.",
                check: () => ConfigInput.CheckExecutable(file));
            return;
        }

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
