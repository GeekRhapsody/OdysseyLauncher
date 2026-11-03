namespace Launcher.Core.Config;

/// <summary>
/// Loads <c>settings.toml</c>, <c>systems.toml</c> and <c>emulators.toml</c>, each layered over its
/// embedded default, and validates them (ARCHITECTURE.md A5).
/// <list type="bullet">
/// <item>A TOML syntax error ignores that whole file.</item>
/// <item>A semantic error disables only the offending system or emulator. A bad setting falls back to its default.</item>
/// <item>Unknown keys are warnings, with a "did you mean" suggestion.</item>
/// </list>
/// This file layers the files and holds the typed reads; each file's own reading is in ConfigLoader.Settings.cs,
/// .Variables.cs, .Emulators.cs and .Systems.cs.
/// </summary>
public sealed partial class ConfigLoader : IConfigLoader
{
    public const int SupportedFormat = 1;

    /// <summary>Used when <c>paths.rom_root</c> is missing or invalid.</summary>
    public const string DefaultRomRoot = "{home}/ROMs";

    /// <summary>The scraping providers <c>[scraping] provider</c> and <c>fallback</c> can name.</summary>
    public static IReadOnlyList<string> Scrapers { get; } = ["screenscraper", "igdb", "steamgriddb", "steam", "launchbox"];

    /// <summary>Used when <c>scraping.hash_limit_mb</c> is missing or invalid.</summary>
    public const long DefaultHashLimitMb = 64;

    private static readonly string[] SettingsRootKeys = ["format", "paths", "scanning", "variables", "display", "ui", "scraping"];
    private static readonly string[] SystemsRootKeys = ["format", "systems"];
    private static readonly string[] EmulatorsRootKeys = ["format", "emulators"];
    private static readonly string[] PathsKeys = ["rom_root", "media"];
    private static readonly string[] DisplayKeys =
    [
        "theme", "screen_mode", "fullscreen", "render_resolution", "window_size", "rendering_driver", "anisotropic_filtering",
        "hide_empty_systems", "group_systems",
        "systems_layout", "systems_columns", "systems_rows", "games_layout", "games_columns", "games_rows",
        "systems_sort", "systems_sort_order", "games_sort", "games_sort_order",
    ];
    private static readonly string[] UiKeys = ["show_clock", "show_battery", "show_network", "show_performance", "navigation_sounds"];
    private static readonly string[] ScrapingKeys = ["provider", "fallback", "regions", "languages", "media", "hash_limit_mb"];
    private static readonly string[] ScanningKeys = ["exclude", "scan_at_launch"];

    private static readonly string[] SystemKeys =
    [
        "enabled", "name", "manufacturer", "year", "description", "aliases", "extensions", "emulator", "alt_emulators",
        "game_model", "screenscraper_id", "igdb_platforms", "launchbox_platforms", "steam_store", "rom_dirs", "recursive", "exclude",
        "games_layout", "games_columns", "games_rows", "games_sort", "games_sort_order", "auto_configure_controllers", "swap_ab_xy",
        "group",
    ];

    private static readonly string[] SystemRequiredKeys = ["name", "extensions", "emulator"];
    private static readonly string[] EmulatorKeys =
        ["enabled", "name", "executable", "core", "args", "working_dir", "run_file", "controllers", "installs", "install_args"];

    private static readonly string[] ControllerKinds = [Launching.Controllers.EdenControllers.Kind];
    private static readonly string[] InstallKinds = [Launching.Vita3KGames.Kind];
    private static readonly string[] EmulatorRequiredKeys = ["name", "executable"];
    private static readonly string[] EmulatorRunFileRequiredKeys = ["name"];

    public ConfigLoadResult Load(ConfigSources sources)
    {
        ArgumentNullException.ThrowIfNull(sources);
        return new Run(sources).Execute();
    }

    /// <summary>One load: holds the diagnostics and the resolved variables.</summary>
    private sealed partial class Run(ConfigSources sources)
    {
        private readonly List<Diagnostic> _diagnostics = [];
        private readonly Dictionary<string, string?> _variables = new(StringComparer.Ordinal);
        private readonly Dictionary<string, List<string>?> _lists = new(StringComparer.Ordinal);
        private readonly List<TemplatePart> _parts = [];
        private TomlTableNode? _rawVariables;
        private string _romRoot = string.Empty;
        private List<string> _globalExcludes = [];

        public ConfigLoadResult Execute()
        {
            // Settings keep a pristine copy of the defaults: a bad user value falls back to the default one.
            var settingsDefaults = ParseDefaults(sources.DefaultSettings, sources.PlatformSettings);
            var settingsTree = LoadLayered(sources.DefaultSettings, sources.PlatformSettings, sources.Settings, out _);
            var emulatorsTree = LoadLayered(sources.DefaultEmulators, null, sources.Emulators, out var builtInEmulators);
            var builtInEmulatorOf = new Dictionary<string, string>(StringComparer.Ordinal);
            var builtInGroupOf = new Dictionary<string, string>(StringComparer.Ordinal);
            var systemsTree = LoadLayered(sources.DefaultSystems, sources.PlatformSystems, sources.Systems, out var builtInSystems,
                defaults => ReadBuiltInSystems(defaults, builtInEmulatorOf, builtInGroupOf));

            var settings = ReadSettings(settingsTree, settingsDefaults);
            CheckRoot(emulatorsTree, EmulatorsRootKeys);
            CheckRoot(systemsTree, SystemsRootKeys);

            var rawEmulators = SubTable(emulatorsTree, "emulators", "emulators");
            var emulators = ReadEmulators(rawEmulators, builtInEmulators);
            var systems = ReadSystems(SubTable(systemsTree, "systems", "systems"), builtInSystems, builtInEmulatorOf, builtInGroupOf, rawEmulators, emulators);
            if (sources.FileExists is { } fileExists)
            {
                CheckInstalls(emulators, systems, rawEmulators, fileExists, sources.CheckInstallsFor ?? (_ => true));
            }

            return new ConfigLoadResult(new AppConfig(settings, systems, emulators), _diagnostics);
        }

        // ---- Files and layering ------------------------------------------------------------------

        /// <summary>
        /// Parses the default, the OS's own default over it and the user file, and merges them. Also returns the ids the
        /// defaults define; <paramref name="readDefaults"/> sees the defaults' tree before the user's file is merged into it.
        /// </summary>
        private TomlTableNode LoadLayered(
            ConfigFile defaults, ConfigFile? platform, ConfigFile? user, out HashSet<string> builtInIds, Action<TomlTableNode>? readDefaults = null)
        {
            var merged = ParseDefaults(defaults, platform);
            readDefaults?.Invoke(merged);

            // The ids of [section.<id>] tables in the default file: a new id must be complete, a built-in one needn't be.
            builtInIds = new HashSet<string>(StringComparer.Ordinal);
            foreach (var key in merged.Keys)
            {
                if (merged.TryGet(key, out var section) && section is TomlTableNode sectionTable)
                {
                    foreach (var id in sectionTable.Keys)
                    {
                        builtInIds.Add(id);
                    }
                }
            }

            if (user is not null)
            {
                var userTree = TomlTree.Parse(user.Text, user.Source, _diagnostics);
                if (userTree is not null)
                {
                    merged.MergeFrom(userTree);
                }
            }

            return merged;
        }

        /// <summary>Each built-in system's own <c>emulator</c>, before the user's file can change it.</summary>
        /// <summary>The built-in systems' own <c>emulator</c> and <c>group</c>, before the user's file is merged in.</summary>
        private static void ReadBuiltInSystems(TomlTableNode defaults, Dictionary<string, string> emulatorOf, Dictionary<string, string> groupOf)
        {
            if (!defaults.TryGet("systems", out var node) || node is not TomlTableNode systems)
            {
                return;
            }

            foreach (var id in systems.Keys)
            {
                if (!systems.TryGet(id, out var entry) || entry is not TomlTableNode table)
                {
                    continue;
                }

                if (table.TryGet("emulator", out var emulator) && emulator is TomlScalar { Kind: TomlKind.String, Value: string value })
                {
                    emulatorOf[id] = value;
                }

                if (table.TryGet("group", out var group) && group is TomlScalar { Kind: TomlKind.String, Value: string parent } && parent.Length > 0)
                {
                    groupOf[id] = parent;
                }
            }
        }

        private TomlTableNode ParseDefaults(ConfigFile defaults, ConfigFile? platform)
        {
            var tree = ParseDefault(defaults);
            if (platform is not null)
            {
                tree.MergeFrom(ParseDefault(platform));
            }

            return tree;
        }

        private TomlTableNode ParseDefault(ConfigFile defaults) =>
            TomlTree.ParseBuiltIn(defaults.Text, defaults.Source, _diagnostics)
            ?? new TomlTableNode(new SourcePos(defaults.Source, 0, 0));

        private void CheckRoot(TomlTableNode root, string[] knownKeys)
        {
            WarnUnknownKeys(root, string.Empty, knownKeys);
            if (root.TryGet("format", out var node))
            {
                if (node is not TomlScalar { Kind: TomlKind.Integer, Value: long format })
                {
                    Error(node, "format", $"expected an integer, found {TomlNode.KindName(node.Kind)}");
                }
                else if (format != SupportedFormat)
                {
                    Error(node, "format", $"format {format} isn't supported: this version reads format {SupportedFormat}");
                }
            }
        }

        private TomlTableNode? SubTable(TomlTableNode root, string key, string path)
        {
            if (!root.TryGet(key, out var node))
            {
                return null;
            }

            if (node is TomlTableNode table)
            {
                return table;
            }

            Error(node, path, $"expected a table, found {TomlNode.KindName(node.Kind)}");
            return null;
        }

        // ---- Typed reads -------------------------------------------------------------------------

        private string? String(TomlTableNode table, string prefix, string key)
        {
            if (!table.TryGet(key, out var node))
            {
                return null;
            }

            if (node is TomlScalar { Kind: TomlKind.String, Value: string value })
            {
                return value;
            }

            Error(node, $"{prefix}.{key}", $"expected a string, found {TomlNode.KindName(node.Kind)}");
            return null;
        }

        private string? NonEmptyString(TomlTableNode table, string prefix, string key)
        {
            var value = String(table, prefix, key);
            if (value is not null && value.Trim().Length == 0 && table.TryGet(key, out var node))
            {
                Error(node, $"{prefix}.{key}", "can't be empty");
                return null;
            }

            return value;
        }

        private bool? Bool(TomlTableNode table, string prefix, string key)
        {
            if (!table.TryGet(key, out var node))
            {
                return null;
            }

            if (node is TomlScalar { Kind: TomlKind.Boolean, Value: bool value })
            {
                return value;
            }

            Error(node, $"{prefix}.{key}", $"expected true or false, found {TomlNode.KindName(node.Kind)}");
            return null;
        }

        private long? Integer(TomlTableNode table, string prefix, string key, long min, long max)
        {
            if (!table.TryGet(key, out var node))
            {
                return null;
            }

            if (node is not TomlScalar { Kind: TomlKind.Integer, Value: long value })
            {
                Error(node, $"{prefix}.{key}", $"expected an integer, found {TomlNode.KindName(node.Kind)}");
                return null;
            }

            if (value < min || value > max)
            {
                Error(node, $"{prefix}.{key}", $"{value} is out of range ({min} to {max})");
                return null;
            }

            return value;
        }

        /// <summary>A system's <c>games_layout</c>; anything but a games layout warns and is ignored.</summary>
        private GamesLayout? LayoutOverride(TomlTableNode table, string prefix)
        {
            if (!table.TryGet("games_layout", out var node))
            {
                return null;
            }

            if (node is TomlScalar { Kind: TomlKind.String, Value: string name } && Layouts.TryParse(name, out GamesLayout layout))
            {
                return layout;
            }

            var why = node is TomlScalar { Kind: TomlKind.String, Value: string other }
                ? $"unknown layout '{other}'{Suggest(other, Layouts.GamesNames)}. The layouts are {string.Join(", ", Layouts.GamesNames)}"
                : $"expected a string, found {TomlNode.KindName(node.Kind)}";
            Warning(node, $"{prefix}.games_layout", why + ", so [display] games_layout is used");
            return null;
        }

        /// <summary>A system's <c>games_sort</c> or <c>games_sort_order</c>: one of <paramref name="names"/>; anything else warns and is ignored.</summary>
        private bool NameOverride(TomlTableNode table, string prefix, string key, IReadOnlyList<string> names, string what, out int index)
        {
            index = 0;
            if (!table.TryGet(key, out var node))
            {
                return false;
            }

            if (node is TomlScalar { Kind: TomlKind.String, Value: string name } && Layouts.IndexOf(names, name) is var found and >= 0)
            {
                index = found;
                return true;
            }

            var why = node is TomlScalar { Kind: TomlKind.String, Value: string other }
                ? $"unknown {what} '{other}'{Suggest(other, names)}. The {what}s are {string.Join(", ", names)}"
                : $"expected a string, found {TomlNode.KindName(node.Kind)}";
            Warning(node, $"{prefix}.{key}", $"{why}, so [display] {key} is used");
            return false;
        }

        /// <summary>A system's <c>games_columns</c> or <c>games_rows</c>, 0 to <paramref name="max"/>; anything else warns and is ignored.</summary>
        private int? GridOverride(TomlTableNode table, string prefix, string key, int max)
        {
            if (!table.TryGet(key, out var node))
            {
                return null;
            }

            if (node is TomlScalar { Kind: TomlKind.Integer, Value: long value } && value >= 0 && value <= max)
            {
                return (int)value;
            }

            Warning(node, $"{prefix}.{key}", node is TomlScalar { Kind: TomlKind.Integer, Value: long outOfRange }
                ? $"{outOfRange} is out of range (0, automatic, to {max}), so [display] {key} is used"
                : $"expected an integer, found {TomlNode.KindName(node.Kind)}, so [display] {key} is used");
            return null;
        }

        private List<string>? StringArray(TomlNode node, string key, string suffix)
        {
            if (node is not TomlArrayNode array)
            {
                Error(node, key, $"expected an array of strings, found {TomlNode.KindName(node.Kind)}{suffix}");
                return null;
            }

            var values = new List<string>(array.Items.Count);
            foreach (var item in array.Items)
            {
                if (item is TomlScalar { Kind: TomlKind.String, Value: string value })
                {
                    values.Add(value);
                }
                else
                {
                    Error(item, key, $"expected an array of strings, but an item is {TomlNode.KindName(item.Kind)}{suffix}");
                    return null;
                }
            }

            return values;
        }

        private void RequireKeys(TomlTableNode entry, string prefix, string[] required)
        {
            var missing = required.Where(key => !entry.Contains(key)).ToList();
            if (missing.Count > 0)
            {
                Error(entry, prefix, $"a new entry needs every required key; missing: {string.Join(", ", missing)}");
            }
        }

        private void WarnUnknownKeys(TomlTableNode table, string prefix, string[] known)
        {
            foreach (var key in table.Keys)
            {
                if (Array.IndexOf(known, key) >= 0)
                {
                    continue;
                }

                table.TryGet(key, out var node);
                var path = prefix.Length == 0 ? key : $"{prefix}.{key}";
                Warning(node, path, $"unknown key{Suggest(key, known)}. It's ignored");
            }
        }

        private static bool IsValidId(string id) => TomlValidator.IsValidId(id);

        // ---- Diagnostics -------------------------------------------------------------------------

        private int ErrorCount { get; set; }

        private void Error(TomlNode node, string key, string message)
        {
            ErrorCount++;
            Add(Severity.Error, node, key, message);
        }

        private void Warning(TomlNode node, string key, string message) => Add(Severity.Warning, node, key, message);

        private void Info(TomlNode node, string key, string message) => Add(Severity.Info, node, key, message);

        private void Add(Severity severity, TomlNode node, string key, string message) =>
            _diagnostics.Add(new Diagnostic(severity, node.Pos.Source, node.Pos.Line, node.Pos.Column, key, message));

        private static string Suggest(string value, IEnumerable<string> candidates) => TomlValidator.Suggest(value, candidates);
    }
}
