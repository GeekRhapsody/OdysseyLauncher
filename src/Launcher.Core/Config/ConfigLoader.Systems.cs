using Launcher.Core.Media;
using Launcher.Core.Scanning;

namespace Launcher.Core.Config;

public sealed partial class ConfigLoader
{
    private sealed partial class Run
    {
        // ---- systems.toml ------------------------------------------------------------------------

        private List<SystemConfig> ReadSystems(
            TomlTableNode? table,
            HashSet<string> builtIn,
            Dictionary<string, string> builtInEmulatorOf,
            Dictionary<string, string> builtInGroupOf,
            TomlTableNode? rawEmulators,
            Dictionary<string, EmulatorConfig> emulators)
        {
            var result = new List<SystemConfig>();
            if (table is null)
            {
                return result;
            }

            var groups = new Dictionary<string, (string Parent, TomlNode Node)>(StringComparer.Ordinal);
            var claimedNames = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var id in table.Keys)
            {
                claimedNames.TryAdd(id, id);
            }

            foreach (var id in table.Keys)
            {
                table.TryGet(id, out var node);
                var prefix = "systems." + id;
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

                WarnUnknownKeys(entry, prefix, SystemKeys);
                if (Bool(entry, prefix, "enabled") == false)
                {
                    continue;
                }

                if (!builtIn.Contains(id))
                {
                    RequireKeys(entry, prefix, SystemRequiredKeys);
                }

                var name = NonEmptyString(entry, prefix, "name") ?? id;
                var manufacturer = String(entry, prefix, "manufacturer");
                var year = Integer(entry, prefix, "year", 1950, 2100);
                var description = String(entry, prefix, "description");
                var screenScraperId = Integer(entry, prefix, "screenscraper_id", 1, int.MaxValue);
                var igdbPlatforms = new List<int>();
                if (entry.TryGet("igdb_platforms", out var igdbNode))
                {
                    if (igdbNode is TomlArrayNode igdbArray)
                    {
                        foreach (var item in igdbArray.Items)
                        {
                            if (item is TomlScalar { Kind: TomlKind.Integer, Value: long platform } && platform is > 0 and <= int.MaxValue)
                            {
                                if (!igdbPlatforms.Contains((int)platform))
                                {
                                    igdbPlatforms.Add((int)platform);
                                }
                            }
                            else
                            {
                                Error(item, prefix + ".igdb_platforms", "expected positive integer IGDB platform ids");
                            }
                        }
                    }
                    else
                    {
                        Error(igdbNode, prefix + ".igdb_platforms", $"expected an array of integers, found {TomlNode.KindName(igdbNode.Kind)}");
                    }
                }
                var launchBoxPlatforms = new List<string>();
                if (entry.TryGet("launchbox_platforms", out var launchBoxNode)
                    && StringArray(launchBoxNode, prefix + ".launchbox_platforms", string.Empty) is { } rawLaunchBox)
                {
                    foreach (var platform in rawLaunchBox)
                    {
                        if (!string.IsNullOrWhiteSpace(platform) && !launchBoxPlatforms.Contains(platform.Trim(), StringComparer.Ordinal))
                        {
                            launchBoxPlatforms.Add(platform.Trim());
                        }
                    }
                }

                var steamStore = Bool(entry, prefix, "steam_store") ?? false;
                var autoControllers = Bool(entry, prefix, "auto_configure_controllers") ?? false;
                var swapFaceButtons = Bool(entry, prefix, "swap_ab_xy") ?? false;
                var recursive = Bool(entry, prefix, "recursive") ?? true;

                // The system whose card it shows under (A5 Grouped systems); "" (a user's) takes a built-in one out.
                // Checked once every system is read.
                var group = String(entry, prefix, "group");
                if (group is { Length: > 0 } && entry.TryGet("group", out var groupNode))
                {
                    if (group == id)
                    {
                        Warning(groupNode, prefix + ".group", "a system can't be grouped under itself, so it has its own card");
                        group = null;
                    }
                    else
                    {
                        groups[id] = (group, groupNode);
                    }
                }

                var aliases = new List<string>();
                if (entry.TryGet("aliases", out var aliasesNode) && StringArray(aliasesNode, prefix + ".aliases", string.Empty) is { } rawAliases)
                {
                    foreach (var alias in rawAliases)
                    {
                        if (!IsValidId(alias))
                        {
                            Error(aliasesNode, prefix + ".aliases", $"'{alias}' isn't a valid id: use lower-case letters, digits, '_' and '-'");
                        }
                        else if (alias == id || aliases.Contains(alias))
                        {
                            continue;
                        }
                        else if (!claimedNames.TryAdd(alias, id) && claimedNames[alias] != id)
                        {
                            Warning(aliasesNode, prefix + ".aliases", $"'{alias}' is already used by systems.{claimedNames[alias]}, so it's ignored here");
                        }
                        else
                        {
                            aliases.Add(alias);
                        }
                    }
                }

                var extensions = new List<string>();
                if (entry.TryGet("extensions", out var extNode) && StringArray(extNode, prefix + ".extensions", string.Empty) is { } rawExtensions)
                {
                    foreach (var raw in rawExtensions)
                    {
                        var extension = raw.ToLowerInvariant();
                        if (extension.Length < 2 || extension[0] != '.' || extension.IndexOfAny(['/', '\\', '*', '?', ' ']) >= 0
                            || extension.IndexOf('.', 1) >= 0)
                        {
                            Error(extNode, prefix + ".extensions", $"'{raw}' isn't a file extension: write it like \".md\"");
                        }
                        else if (!extensions.Contains(extension))
                        {
                            extensions.Add(extension);
                        }
                    }

                    if (rawExtensions.Count == 0)
                    {
                        Error(extNode, prefix + ".extensions", "needs at least one extension");
                    }
                }

                var emulator = String(entry, prefix, "emulator");
                if (emulator is not null && entry.TryGet("emulator", out var emuNode))
                {
                    CheckEmulator(emulator, emuNode, prefix + ".emulator", rawEmulators, emulators, isError: true);
                }

                var altEmulators = new List<string>();
                if (entry.TryGet("alt_emulators", out var altNode) && StringArray(altNode, prefix + ".alt_emulators", string.Empty) is { } rawAlts)
                {
                    foreach (var alt in rawAlts)
                    {
                        if (CheckEmulator(alt, altNode, prefix + ".alt_emulators", rawEmulators, emulators, isError: false)
                            && !altEmulators.Contains(alt) && alt != emulator)
                        {
                            altEmulators.Add(alt);
                        }
                    }
                }

                // A game template id in the theme (M6). Themes load after config, so an id no theme defines is
                // reported when models are resolved, and the theme's own choice is used instead.
                var gameModel = String(entry, prefix, "game_model");
                if (gameModel is not null && !IsValidId(gameModel) && entry.TryGet("game_model", out var modelNode))
                {
                    Error(modelNode, prefix + ".game_model", $"'{gameModel}' isn't a template id: use lower-case letters, digits, '_' and '-'");
                    gameModel = null;
                }

                // The system's own games view and order: a bad one is only a warning, so the system stays enabled.
                var view = ViewOverride(entry, prefix);

                var romDirs = new List<string>();
                var romDirSource = RomDirSource.Default;
                if (entry.TryGet("rom_dirs", out var dirsNode) && StringArray(dirsNode, prefix + ".rom_dirs", string.Empty) is { } rawDirs)
                {
                    romDirSource = RomDirSource.Configured;
                    foreach (var rawDir in rawDirs)
                    {
                        // The same folder twice is listed once; folders that differ only in case are separate on Linux.
                        if (ExpandPath(rawDir, dirsNode, prefix + ".rom_dirs", allowRomRoot: true) is { } dir
                            && !romDirs.Exists(listed => MediaFolder.Same(listed, dir)))
                        {
                            romDirs.Add(dir);
                        }
                    }

                    if (rawDirs.Count == 0)
                    {
                        Error(dirsNode, prefix + ".rom_dirs", "needs at least one folder. Leave it out to use {rom_root}/" + id);
                    }
                }
                else
                {
                    romDirs.Add(Path.Combine(_romRoot, id));
                    foreach (var alias in aliases)
                    {
                        romDirs.Add(Path.Combine(_romRoot, alias));
                    }
                }

                // scanning.exclude from settings.toml applies to every system, before the system's own patterns.
                var exclude = new List<string>(_globalExcludes);
                if (entry.TryGet("exclude", out var excludeNode) && StringArray(excludeNode, prefix + ".exclude", string.Empty) is { } rawExclude)
                {
                    foreach (var pattern in rawExclude)
                    {
                        if (GlobPattern.Validate(pattern) is { } globError)
                        {
                            Error(excludeNode, prefix + ".exclude", $"'{pattern}': {globError}");
                        }
                        else if (!exclude.Contains(pattern, StringComparer.OrdinalIgnoreCase))
                        {
                            exclude.Add(pattern);
                        }
                    }
                }

                if (ErrorCount > errorsBefore || emulator is null || extensions.Count == 0)
                {
                    Info(entry, prefix, "this system is disabled until its errors are fixed");
                    continue;
                }

                result.Add(new SystemConfig(
                    id, name, manufacturer, (int?)year, aliases, extensions, emulator, altEmulators, gameModel,
                    (int?)screenScraperId, romDirs, romDirSource, recursive, exclude, igdbPlatforms, steamStore, view.Columns, view.Rows, view.Layout,
                    view.Sort, view.Order, string.IsNullOrWhiteSpace(description) ? null : description, autoControllers, swapFaceButtons,
                    launchBoxPlatforms, string.IsNullOrEmpty(group) ? null : group)
                {
                    // The built-in definition's own emulator, offered with the alternatives once the user has chosen another.
                    DefaultEmulator = builtInEmulatorOf.TryGetValue(id, out var builtInEmulator) && emulators.ContainsKey(builtInEmulator) ? builtInEmulator : null,
                    DefaultGroup = builtInGroupOf.GetValueOrDefault(id),
                });
            }

            CheckGroups(result, groups, table);
            return result;
        }

        /// <summary>
        /// Each <c>group</c> must name an enabled system that isn't grouped itself (one level, as in Batocera); otherwise
        /// it's a warning and the system keeps its own card. A parent that's disabled (or has errors) is only noted: the
        /// user turned it off, and its variants carry on alone.
        /// </summary>
        private void CheckGroups(List<SystemConfig> systems, Dictionary<string, (string Parent, TomlNode Node)> groups, TomlTableNode table)
        {
            var enabled = new HashSet<string>(StringComparer.Ordinal);
            foreach (var system in systems)
            {
                enabled.Add(system.Id);
            }

            for (var i = 0; i < systems.Count; i++)
            {
                var system = systems[i];
                if (system.Group is not { } parent || !groups.TryGetValue(system.Id, out var declared))
                {
                    continue;
                }

                string? problem = null;
                if (!enabled.Contains(parent) && table.TryGet(parent, out _))
                {
                    Info(declared.Node, "systems." + system.Id + ".group", $"'{parent}' is disabled, so this system has its own card");
                    systems[i] = system with { Group = null };
                    continue;
                }

                if (!enabled.Contains(parent))
                {
                    problem = $"unknown system '{parent}'{Suggest(parent, enabled)}";
                }
                else if (groups.TryGetValue(parent, out var parentsGroup) && enabled.Contains(parentsGroup.Parent))
                {
                    problem = $"'{parent}' is grouped under '{parentsGroup.Parent}' itself, and groups don't nest";
                }

                if (problem is not null)
                {
                    Warning(declared.Node, "systems." + system.Id + ".group", problem + ", so this system has its own card");
                    systems[i] = system with { Group = null };
                }
            }
        }

        private bool CheckEmulator(
            string id, TomlNode at, string key, TomlTableNode? raw, Dictionary<string, EmulatorConfig> valid, bool isError)
        {
            if (valid.ContainsKey(id))
            {
                return true;
            }

            string message;
            if (raw is not null && raw.TryGet(id, out var rawNode))
            {
                message = rawNode is TomlTableNode rawEntry
                    && rawEntry.TryGet("enabled", out var enabled)
                    && enabled is TomlScalar { Value: false }
                    ? $"emulator '{id}' is disabled"
                    : $"emulator '{id}' has errors (see emulators.{id})";
            }
            else
            {
                message = $"unknown emulator '{id}'{Suggest(id, valid.Keys.ToList())}";
            }

            if (isError)
            {
                Error(at, key, message);
            }
            else
            {
                Warning(at, key, message + ", so it's left out");
            }

            return false;
        }
    }
}
