namespace Launcher.Core.Config;

public sealed partial class ConfigLoader
{
    private sealed partial class Run
    {
        // ---- emulators.toml ----------------------------------------------------------------------

        private Dictionary<string, EmulatorConfig> ReadEmulators(TomlTableNode? table, HashSet<string> builtIn)
        {
            var result = new Dictionary<string, EmulatorConfig>(StringComparer.Ordinal);
            if (table is null)
            {
                return result;
            }

            foreach (var id in table.Keys)
            {
                table.TryGet(id, out var node);
                var prefix = "emulators." + id;
                if (node is not TomlTableNode entry)
                {
                    Error(node, prefix, $"expected a table, found {TomlNode.KindName(node.Kind)}");
                    continue;
                }

                var errorsBefore = ErrorCount;
                if (!IsValidId(id))
                {
                    Error(entry, prefix, "ids can only use lower-case letters, digits, '_' and '-'");
                }

                WarnUnknownKeys(entry, prefix, EmulatorKeys);
                if (Bool(entry, prefix, "enabled") == false)
                {
                    continue;
                }

                // run_file: the profile runs the game's own file (a program, or a shortcut or script made for the
                // game) instead of an emulator, so it has no program, core or arguments of its own.
                var runFile = Bool(entry, prefix, "run_file") == true;
                if (!builtIn.Contains(id))
                {
                    RequireKeys(entry, prefix, runFile ? EmulatorRunFileRequiredKeys : EmulatorRequiredKeys);
                }

                if (runFile)
                {
                    foreach (var key in (ReadOnlySpan<string>)["executable", "core", "args", "install_args"])
                    {
                        if (entry.TryGet(key, out var extra))
                        {
                            Error(extra, prefix + "." + key,
                                "a run_file profile runs the game's own file, so it takes no executable, core, args or install_args");
                        }
                    }
                }

                var name = NonEmptyString(entry, prefix, "name") ?? id;
                string? executable = null;
                if (!runFile && entry.TryGet("executable", out var exeNode) && String(entry, prefix, "executable") is { } rawExe)
                {
                    executable = ExpandPath(rawExe, exeNode, prefix + ".executable", allowRomRoot: true);
                    var extension = executable is null ? string.Empty : Path.GetExtension(executable);
                    if (extension.Equals(".bat", StringComparison.OrdinalIgnoreCase)
                        || extension.Equals(".cmd", StringComparison.OrdinalIgnoreCase))
                    {
                        Error(exeNode, prefix + ".executable",
                            ".bat and .cmd files can't be emulators: cmd.exe re-parses their arguments, so names like " +
                            "'Sonic & Knuckles' would break or run commands. Point at the emulator's .exe instead");
                    }
                }

                string? core = null;
                var coreNode = default(TomlNode);
                if (!runFile && entry.TryGet("core", out coreNode) && String(entry, prefix, "core") is { } rawCore)
                {
                    core = ExpandPath(rawCore, coreNode, prefix + ".core", allowRomRoot: true);
                }

                var usesCore = false;
                var argsNode = default(TomlNode);
                var args = runFile ? null : ArgTemplates(entry, prefix, "args", ref usesCore, out argsNode);
                var installArgsNode = default(TomlNode);
                var installArgs = runFile ? null : ArgTemplates(entry, prefix, "install_args", ref usesCore, out installArgsNode);

                var workingDir = runFile ? "{rom_dir}" : "{emulator_dir}";
                if (entry.TryGet("working_dir", out var wdNode) && String(entry, prefix, "working_dir") is { } rawWd)
                {
                    workingDir = Expand(rawWd, wdNode, prefix + ".working_dir", keepLaunchPlaceholders: true, allowRomRoot: true)
                        ?? workingDir;
                    usesCore |= UsesPlaceholder(workingDir, "core");
                }

                if (usesCore && core is null && !entry.Contains("core"))
                {
                    Error(argsNode ?? entry, prefix + ".args",
                        "{core} is used, but this profile has no core. Add core = \"{retroarch}/cores/<name>_libretro.dll\"");
                }
                else if (!usesCore && core is not null)
                {
                    Warning(coreNode!, prefix + ".core", "no args entry uses {core}, so the core is never passed to the emulator");
                }

                // How the launcher sets the emulator's controllers up (auto_configure_controllers). An unknown kind is
                // only a warning: the emulator still launches, its pads just aren't set up.
                var controllers = String(entry, prefix, "controllers");
                if (controllers is not null && entry.TryGet("controllers", out var controllersNode))
                {
                    if (runFile)
                    {
                        Warning(controllersNode, prefix + ".controllers", "a run_file profile has no emulator whose controllers could be set up, so it's ignored");
                        controllers = null;
                    }
                    else if (!ControllerKinds.Contains(controllers))
                    {
                        Warning(controllersNode, prefix + ".controllers",
                            $"'{controllers}' isn't a controller setup the launcher knows (only {string.Join(", ", ControllerKinds.Select(k => $"\"{k}\""))}), so it's ignored");
                        controllers = null;
                    }
                }

                // How the launcher knows which games the emulator has installed, so it boots those with args and gives
                // the others to install_args. An unknown kind is only a warning: every game is then launched with args.
                var installs = String(entry, prefix, "installs");
                if (installs is not null && entry.TryGet("installs", out var installsNode))
                {
                    if (runFile)
                    {
                        Warning(installsNode, prefix + ".installs", "a run_file profile has no emulator to install games in, so it's ignored");
                        installs = null;
                    }
                    else if (!InstallKinds.Contains(installs))
                    {
                        Warning(installsNode, prefix + ".installs",
                            $"'{installs}' isn't an emulator whose installed games the launcher knows (only {string.Join(", ", InstallKinds.Select(k => $"\"{k}\""))}), so it's ignored");
                        installs = null;
                    }
                }

                if (installs is null && installArgs is not null)
                {
                    if (!entry.Contains("installs"))
                    {
                        Warning(installArgsNode!, prefix + ".install_args", "install_args is only used with installs, so it's ignored");
                    }

                    installArgs = null;
                }

                if (ErrorCount > errorsBefore || (executable is null && !runFile))
                {
                    Info(entry, prefix, "this emulator is disabled until its errors are fixed");
                    continue;
                }

                result[id] = new EmulatorConfig(
                    id, name, executable ?? string.Empty, args ?? [], workingDir, core, runFile, controllers, installs, installArgs);
            }

            return result;
        }

        /// <summary>
        /// A profile's argument templates under <paramref name="key"/> (<c>args</c>, <c>install_args</c>), with config
        /// variables expanded and launch placeholders kept; null when the profile has none (or it isn't an array).
        /// </summary>
        private List<string>? ArgTemplates(TomlTableNode entry, string prefix, string key, ref bool usesCore, out TomlNode? node)
        {
            if (!entry.TryGet(key, out node) || StringArray(node, prefix + "." + key, string.Empty) is not { } rawArgs)
            {
                return null;
            }

            var args = new List<string>(rawArgs.Count);
            foreach (var rawArg in rawArgs)
            {
                if (Expand(rawArg, node, prefix + "." + key, keepLaunchPlaceholders: true, allowRomRoot: true) is { } arg)
                {
                    args.Add(arg);
                    usesCore |= UsesPlaceholder(arg, "core");
                }
            }

            return args;
        }

        private bool UsesPlaceholder(string template, string name)
        {
            Template.TryParse(template, _parts);
            foreach (var part in _parts)
            {
                if (part.IsPlaceholder && part.Text == name)
                {
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Warns about each emulator that an enabled system uses as its emulator (not an alternative: the catalogue lists
        /// many, which the user mostly doesn't have) whose executable or core doesn't exist, naming those systems. It's
        /// only a warning: the systems stay browsable (an unplugged drive shouldn't empty the library), and launching
        /// reports the same problem. <paramref name="covered"/> picks the systems that are checked.
        /// </summary>
        private void CheckInstalls(
            Dictionary<string, EmulatorConfig> emulators,
            List<SystemConfig> systems,
            TomlTableNode? raw,
            Func<string, bool> fileExists,
            Func<string, bool> covered)
        {
            if (raw is null)
            {
                return;
            }

            var byDefault = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            foreach (var system in systems)
            {
                if (covered(system.Id))
                {
                    if (!byDefault.TryGetValue(system.Emulator, out var names))
                    {
                        byDefault[system.Emulator] = names = [];
                    }

                    names.Add($"{system.Name} ({system.Id})");
                }
            }

            // Most built-in profiles share retroarch.exe, so each path is checked once.
            var exists = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
            bool Exists(string path)
            {
                if (!exists.TryGetValue(path, out var found))
                {
                    found = fileExists(path);
                    exists[path] = found;
                }

                return found;
            }

            foreach (var (id, emulator) in emulators)
            {
                if (emulator.RunFile || !byDefault.TryGetValue(id, out var names))
                {
                    continue;
                }

                raw.TryGet(id, out var entryNode);
                var entry = (TomlTableNode)entryNode;
                foreach (var (key, path, what) in (ReadOnlySpan<(string, string?, string)>)
                    [("executable", emulator.Executable, "executable"), ("core", emulator.Core, "core")])
                {
                    if (path is null || Exists(path))
                    {
                        continue;
                    }

                    // A missing install is one problem: its core is missing too, so it isn't reported again.
                    TomlNode at = entry.TryGet(key, out var node) ? node : entry;
                    Warning(at, $"emulators.{id}.{key}",
                        $"the {what} '{path}' doesn't exist, so {JoinNames(names)} can't launch games (it's their emulator). " +
                        "Install it there, or fix the path here or in the [variables] it uses in settings.toml");
                    break;
                }
            }
        }

        private static string JoinNames(List<string> names) =>
            names.Count == 1 ? names[0] : string.Join(", ", names.Take(names.Count - 1)) + " and " + names[^1];
    }
}
