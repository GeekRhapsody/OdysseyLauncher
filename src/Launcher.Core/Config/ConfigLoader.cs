using System.Text;
using Launcher.Core.Media;
using Launcher.Core.Scanning;

namespace Launcher.Core.Config;

/// <summary>
/// Loads <c>settings.toml</c>, <c>systems.toml</c> and <c>emulators.toml</c>, each layered over its
/// embedded default, and validates them (ARCHITECTURE.md A5).
/// <list type="bullet">
/// <item>A TOML syntax error ignores that whole file.</item>
/// <item>A semantic error disables only the offending system or emulator. A bad setting falls back to its default.</item>
/// <item>Unknown keys are warnings, with a "did you mean" suggestion.</item>
/// </list>
/// </summary>
public sealed class ConfigLoader : IConfigLoader
{
    public const int SupportedFormat = 1;

    /// <summary>Used when <c>paths.rom_root</c> is missing or invalid.</summary>
    public const string DefaultRomRoot = "{home}/ROMs";

    /// <summary>The scraping providers <c>[scraping] provider</c> and <c>fallback</c> can name.</summary>
    public static IReadOnlyList<string> Scrapers { get; } = ["screenscraper", "igdb", "steamgriddb", "steam"];

    /// <summary>Used when <c>scraping.hash_limit_mb</c> is missing or invalid.</summary>
    public const long DefaultHashLimitMb = 64;

    private static readonly string[] SettingsRootKeys = ["format", "paths", "scanning", "variables", "display", "ui", "scraping"];
    private static readonly string[] SystemsRootKeys = ["format", "systems"];
    private static readonly string[] EmulatorsRootKeys = ["format", "emulators"];
    private static readonly string[] PathsKeys = ["rom_root", "media"];
    private static readonly string[] DisplayKeys =
    [
        "theme", "screen_mode", "fullscreen", "render_resolution", "window_size", "rendering_driver", "anisotropic_filtering",
        "hide_empty_systems",
        "systems_layout", "systems_columns", "systems_rows", "games_layout", "games_columns", "games_rows",
        "systems_sort", "systems_sort_order", "games_sort", "games_sort_order",
    ];
    private static readonly string[] UiKeys = ["show_clock", "show_battery", "show_network", "show_performance"];
    private static readonly string[] ScrapingKeys = ["provider", "fallback", "regions", "languages", "media", "hash_limit_mb"];
    private static readonly string[] ScanningKeys = ["exclude"];

    private static readonly string[] SystemKeys =
    [
        "enabled", "name", "manufacturer", "year", "description", "aliases", "extensions", "emulator", "alt_emulators",
        "game_model", "screenscraper_id", "igdb_platforms", "steam_store", "rom_dirs", "recursive", "exclude",
        "games_layout", "games_columns", "games_rows", "games_sort", "games_sort_order",
    ];

    private static readonly string[] SystemRequiredKeys = ["name", "extensions", "emulator"];
    private static readonly string[] EmulatorKeys = ["enabled", "name", "executable", "core", "args", "working_dir", "run_file"];
    private static readonly string[] EmulatorRequiredKeys = ["name", "executable"];
    private static readonly string[] EmulatorRunFileRequiredKeys = ["name"];

    public ConfigLoadResult Load(ConfigSources sources)
    {
        ArgumentNullException.ThrowIfNull(sources);
        return new Run(sources).Execute();
    }

    /// <summary>One load: holds the diagnostics and the resolved variables.</summary>
    private sealed class Run(ConfigSources sources)
    {
        private readonly List<Diagnostic> _diagnostics = [];
        private readonly Dictionary<string, string?> _variables = new(StringComparer.Ordinal);
        private readonly List<TemplatePart> _parts = [];
        private TomlTableNode? _rawVariables;
        private string _romRoot = string.Empty;
        private List<string> _globalExcludes = [];

        public ConfigLoadResult Execute()
        {
            // Settings keep a pristine copy of the defaults: a bad user value falls back to the default one.
            var settingsDefaults = ParseDefault(sources.DefaultSettings);
            var settingsTree = LoadLayered(sources.DefaultSettings, sources.Settings, out _);
            var emulatorsTree = LoadLayered(sources.DefaultEmulators, sources.Emulators, out var builtInEmulators);
            var builtInEmulatorOf = new Dictionary<string, string>(StringComparer.Ordinal);
            var systemsTree = LoadLayered(sources.DefaultSystems, sources.Systems, out var builtInSystems, defaults => ReadBuiltInEmulators(defaults, builtInEmulatorOf));

            var settings = ReadSettings(settingsTree, settingsDefaults);
            CheckRoot(emulatorsTree, EmulatorsRootKeys);
            CheckRoot(systemsTree, SystemsRootKeys);

            var rawEmulators = SubTable(emulatorsTree, "emulators", "emulators");
            var emulators = ReadEmulators(rawEmulators, builtInEmulators);
            var systems = ReadSystems(SubTable(systemsTree, "systems", "systems"), builtInSystems, builtInEmulatorOf, rawEmulators, emulators);
            if (sources.FileExists is { } fileExists)
            {
                CheckInstalls(emulators, systems, rawEmulators, fileExists, sources.CheckInstallsFor ?? (_ => true));
            }

            return new ConfigLoadResult(new AppConfig(settings, systems, emulators), _diagnostics);
        }

        // ---- Files and layering ------------------------------------------------------------------

        /// <summary>
        /// Parses the default and the user file and merges them. Also returns the ids the default defines;
        /// <paramref name="readDefaults"/> sees the default tree before the user's file is merged into it.
        /// </summary>
        private TomlTableNode LoadLayered(ConfigFile defaults, ConfigFile? user, out HashSet<string> builtInIds, Action<TomlTableNode>? readDefaults = null)
        {
            var merged = ParseDefault(defaults);
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
        private static void ReadBuiltInEmulators(TomlTableNode defaults, Dictionary<string, string> emulatorOf)
        {
            if (!defaults.TryGet("systems", out var node) || node is not TomlTableNode systems)
            {
                return;
            }

            foreach (var id in systems.Keys)
            {
                if (systems.TryGet(id, out var entry) && entry is TomlTableNode table
                    && table.TryGet("emulator", out var emulator) && emulator is TomlScalar { Kind: TomlKind.String, Value: string value })
                {
                    emulatorOf[id] = value;
                }
            }
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

        // ---- settings.toml -----------------------------------------------------------------------

        private Settings ReadSettings(TomlTableNode tree, TomlTableNode defaults)
        {
            CheckRoot(tree, SettingsRootKeys);

            _rawVariables = SubTable(tree, "variables", "variables");
            if (_rawVariables is not null)
            {
                foreach (var name in _rawVariables.Keys)
                {
                    ResolveVariable(name, []);
                }
            }

            var paths = SubTable(tree, "paths", "paths");
            if (paths is not null)
            {
                WarnUnknownKeys(paths, "paths", PathsKeys);
            }

            var romRootSetting = SettingString(tree, defaults, "paths", "rom_root");
            TomlNode romRootNode = romRootSetting?.Node ?? tree;
            _romRoot = ExpandPath(romRootSetting?.Value ?? DefaultRomRoot, romRootNode, "paths.rom_root", allowRomRoot: false)
                ?? ExpandPath(DefaultRomRoot, romRootNode, "paths.rom_root", allowRomRoot: false)
                ?? sources.HomeDir;

            // The media folder (2026-10-04): unset is DataDir/media, which the loader doesn't know; a bad one is an error,
            // and the default is used.
            string? mediaDir = null;
            if (SettingString(tree, defaults, "paths", "media") is { } mediaSetting)
            {
                mediaDir = ExpandPath(mediaSetting.Value, mediaSetting.Node, "paths.media", allowRomRoot: false);
            }

            var display = SubTable(tree, "display", "display");
            if (display is not null)
            {
                WarnUnknownKeys(display, "display", DisplayKeys);
            }

            var ui = SubTable(tree, "ui", "ui");
            if (ui is not null)
            {
                WarnUnknownKeys(ui, "ui", UiKeys);
            }

            var scraping = SubTable(tree, "scraping", "scraping");
            if (scraping is not null)
            {
                WarnUnknownKeys(scraping, "scraping", ScrapingKeys);
            }

            var scanning = SubTable(tree, "scanning", "scanning");
            if (scanning is not null)
            {
                WarnUnknownKeys(scanning, "scanning", ScanningKeys);
            }

            var theme = SettingString(tree, defaults, "display", "theme")?.Value ?? Theming.ThemeCatalog.DefaultId;
            var screenMode = ScreenModeSetting(tree, defaults);
            var renderResolution = RenderResolutionSetting(tree, defaults);
            var windowSize = WindowSizeSetting(tree, defaults);
            var renderingDriver = (RenderingDriver)SettingName(tree, defaults, "rendering_driver", DisplayNames.RenderingDrivers, [], "rendering driver", string.Empty);
            var anisotropic = AnisotropicSetting(tree, defaults);
            var hideEmptySystems = SettingBool(tree, defaults, "display", "hide_empty_systems") ?? true;
            var systemsLayout = SettingLayout(tree, defaults, "systems_layout", Layouts.SystemsNames, Layouts.GamesNames);
            var gamesLayout = SettingLayout(tree, defaults, "games_layout", Layouts.GamesNames, Layouts.SystemsNames);
            var systemsSort = new SystemsOrdering(
                (SystemSort)SettingName(tree, defaults, "systems_sort", Sorts.SystemsNames, Sorts.GamesNames, "sort", "sorts games, not systems"),
                (SortOrder)SettingName(tree, defaults, "systems_sort_order", Sorts.OrderNames, [], "order", string.Empty));
            var gamesSort = new GamesOrdering(
                (GameSort)SettingName(tree, defaults, "games_sort", Sorts.GamesNames, Sorts.SystemsNames, "sort", "sorts systems, not games"),
                (SortOrder)SettingName(tree, defaults, "games_sort_order", Sorts.OrderNames, [], "order", string.Empty));
            var systemsGrid = new GridSize(
                (int)(SettingInteger(tree, defaults, "display", "systems_columns", 0, DisplaySettings.MaxColumns) ?? 0),
                (int)(SettingInteger(tree, defaults, "display", "systems_rows", 0, DisplaySettings.MaxRows) ?? 0));
            var gamesGrid = new GridSize(
                (int)(SettingInteger(tree, defaults, "display", "games_columns", 0, DisplaySettings.MaxColumns) ?? 0),
                (int)(SettingInteger(tree, defaults, "display", "games_rows", 0, DisplaySettings.MaxRows) ?? 0));
            var uiSettings = new UiSettings(
                SettingBool(tree, defaults, "ui", "show_clock") ?? true,
                SettingBool(tree, defaults, "ui", "show_battery") ?? true,
                SettingBool(tree, defaults, "ui", "show_network") ?? true,
                SettingBool(tree, defaults, "ui", "show_performance") ?? false);
            var regions = SettingStrings(tree, defaults, "scraping", "regions", null) ?? [];
            var languages = SettingStrings(tree, defaults, "scraping", "languages", null) ?? [];
            string? CheckScraper(string value) => Scrapers.Contains(value) ? null : $"unknown provider '{value}'{Suggest(value, Scrapers)}";
            var providerSetting = SettingString(tree, defaults, "scraping", "provider");
            var provider = "screenscraper";
            if (providerSetting is { } p)
            {
                if (CheckScraper(p.Value) is { } problem)
                {
                    Error(p.Node, "scraping.provider", problem + ". Using screenscraper");
                }
                else
                {
                    provider = p.Value;
                }
            }

            var fallback = new List<string>();
            foreach (var id in SettingStrings(tree, defaults, "scraping", "fallback", CheckScraper) ?? [])
            {
                if (id != provider && !fallback.Contains(id))
                {
                    fallback.Add(id);
                }
            }

            var media = SettingStrings(tree, defaults, "scraping", "media",
                value => MediaKinds.Scrapable.Contains(value)
                    ? null
                    : $"unknown media kind '{value}'{Suggest(value, MediaKinds.Scrapable)}. The kinds are {string.Join(", ", MediaKinds.Scrapable)}",
                value => value == MediaKinds.BoxTexture
                    ? "box_texture isn't scraped any more, so it's left out (your own box textures still show)"
                    : null) ?? [MediaKinds.Cover];
            var hashLimitMb = SettingInteger(tree, defaults, "scraping", "hash_limit_mb", 0, 65536) ?? DefaultHashLimitMb;
            _globalExcludes = SettingStrings(tree, defaults, "scanning", "exclude",
                value => GlobPattern.Validate(value) is { } problem ? $"'{value}': {problem}" : null) ?? [];

            var variables = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var (name, value) in _variables)
            {
                if (value is not null)
                {
                    variables[name] = value;
                }
            }

            return new Settings(
                SupportedFormat,
                _romRoot,
                variables,
                new DisplaySettings(theme, screenMode, hideEmptySystems)
                {
                    RenderResolution = renderResolution,
                    WindowSize = windowSize,
                    RenderingDriver = renderingDriver,
                    AnisotropicFiltering = anisotropic,
                    SystemsLayout = (SystemsLayout)systemsLayout,
                    SystemsGrid = systemsGrid,
                    GamesLayout = (GamesLayout)gamesLayout,
                    GamesGrid = gamesGrid,
                    SystemsSort = systemsSort,
                    GamesSort = gamesSort,
                },
                new ScrapingSettings(provider, fallback, regions, languages, media, hashLimitMb * 1024 * 1024),
                new ScanningSettings(_globalExcludes),
                uiSettings)
            {
                MediaDir = mediaDir,
            };
        }

        private readonly record struct Located(string Value, TomlNode Node);

        /// <summary>
        /// <c>[display] screen_mode</c>. A user's settings.toml without one may have the key it replaced (2026-10-08),
        /// <c>fullscreen</c>: false is a window, true borderless fullscreen (what it always meant).
        /// </summary>
        private ScreenMode ScreenModeSetting(TomlTableNode tree, TomlTableNode defaults)
        {
            // The tree is the defaults with the user's file over them: screen_mode is the user's only if it came from their file.
            var userMode = TryGetSetting(tree, "display", "screen_mode", out var mode)
                && !(TryGetSetting(defaults, "display", "screen_mode", out var builtIn) && mode.Pos == builtIn.Pos);
            if (!userMode && TryGetSetting(tree, "display", "fullscreen", out _))
            {
                var fullscreen = SettingBool(tree, defaults, "display", "fullscreen");
                if (fullscreen is { } value)
                {
                    return value ? ScreenMode.Borderless : ScreenMode.Windowed;
                }
            }

            return (ScreenMode)SettingName(tree, defaults, "screen_mode", DisplayNames.ScreenModes, [], "screen mode", string.Empty);
        }

        /// <summary><c>[display] render_resolution</c>: <c>"auto"</c>, <c>"native"</c> or a height.</summary>
        private RenderResolution RenderResolutionSetting(TomlTableNode tree, TomlTableNode defaults)
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, "display", "render_resolution", out var node))
                {
                    continue;
                }

                switch (node)
                {
                    case TomlScalar { Kind: TomlKind.String, Value: "auto" }:
                        return RenderResolution.Automatic;
                    case TomlScalar { Kind: TomlKind.String, Value: "native" }:
                        return RenderResolution.Native;
                    case TomlScalar { Kind: TomlKind.Integer, Value: long height } when height is >= RenderResolution.MinHeight and <= RenderResolution.MaxHeight:
                        return new RenderResolution((int)height);
                }

                Error(node, "display.render_resolution",
                    $"expected \"auto\", \"native\" or a height from {RenderResolution.MinHeight} to {RenderResolution.MaxHeight}. Using the default");
            }

            return RenderResolution.Automatic;
        }

        /// <summary><c>[display] window_size</c>: <c>"1280x800"</c>.</summary>
        private WindowSize WindowSizeSetting(TomlTableNode tree, TomlTableNode defaults)
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, "display", "window_size", out var node))
                {
                    continue;
                }

                if (node is TomlScalar { Kind: TomlKind.String, Value: string text } && WindowSize.TryParse(text, out var size))
                {
                    return size;
                }

                Error(node, "display.window_size",
                    $"expected a size like \"1280x800\", from {WindowSize.MinWidth}x{WindowSize.MinHeight} to {WindowSize.MaxSide}x{WindowSize.MaxSide}. Using the default");
            }

            return WindowSize.Default;
        }

        /// <summary><c>[display] anisotropic_filtering</c>: 0 (off), 2, 4, 8 or 16.</summary>
        private int AnisotropicSetting(TomlTableNode tree, TomlTableNode defaults)
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, "display", "anisotropic_filtering", out var node))
                {
                    continue;
                }

                if (node is TomlScalar { Kind: TomlKind.Integer, Value: long value and >= 0 and <= 16 } && DisplaySettings.AnisotropicLevels.Contains((int)value))
                {
                    return (int)value;
                }

                Error(node, "display.anisotropic_filtering", "expected 0 (off), 2, 4, 8 or 16. Using the default");
            }

            return 16;
        }

        /// <summary>
        /// A <c>[display]</c> layout: its index in <paramref name="names"/>. A bad one is an error and the default is used;
        /// one of the other screen's layouts says which screen it's for.
        /// </summary>
        private int SettingLayout(TomlTableNode tree, TomlTableNode defaults, string key, IReadOnlyList<string> names, IReadOnlyList<string> others) =>
            SettingName(tree, defaults, key, names, others, "layout", "isn't a layout for this screen");

        /// <summary>
        /// A <c>[display]</c> value that is one of <paramref name="names"/> (a layout, a sort, an order): its index. A bad
        /// one is an error and the default is used; one of <paramref name="others"/> (the other screen's) says why with
        /// <paramref name="otherWhy"/>.
        /// </summary>
        private int SettingName(
            TomlTableNode tree, TomlTableNode defaults, string key, IReadOnlyList<string> names, IReadOnlyList<string> others, string what, string otherWhy)
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, "display", key, out var node))
                {
                    continue;
                }

                if (node is not TomlScalar { Kind: TomlKind.String, Value: string value })
                {
                    Error(node, $"display.{key}", $"expected a string, found {TomlNode.KindName(node.Kind)}. Using the default");
                    continue;
                }

                var index = Layouts.IndexOf(names, value);
                if (index >= 0)
                {
                    return index;
                }

                var why = Layouts.IndexOf(others, value) >= 0
                    ? $"'{value}' {otherWhy}"
                    : $"unknown {what} '{value}'{Suggest(value, names)}";
                Error(node, $"display.{key}", $"{why}. The {what}s are {string.Join(", ", names)}. Using the default");
            }

            return 0;
        }

        private Located? SettingString(TomlTableNode tree, TomlTableNode defaults, string section, string key)
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, section, key, out var node))
                {
                    continue;
                }

                if (node is TomlScalar { Kind: TomlKind.String, Value: string value })
                {
                    return new Located(value, node);
                }

                Error(node, $"{section}.{key}", $"expected a string, found {TomlNode.KindName(node.Kind)}. Using the default");
            }

            return null;
        }

        private bool? SettingBool(TomlTableNode tree, TomlTableNode defaults, string section, string key)
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, section, key, out var node))
                {
                    continue;
                }

                if (node is TomlScalar { Kind: TomlKind.Boolean, Value: bool value })
                {
                    return value;
                }

                Error(node, $"{section}.{key}", $"expected a boolean, found {TomlNode.KindName(node.Kind)}. Using the default");
            }

            return null;
        }

        private long? SettingInteger(TomlTableNode tree, TomlTableNode defaults, string section, string key, long min, long max)
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, section, key, out var node))
                {
                    continue;
                }

                if (node is not TomlScalar { Kind: TomlKind.Integer, Value: long value })
                {
                    Error(node, $"{section}.{key}", $"expected an integer, found {TomlNode.KindName(node.Kind)}. Using the default");
                }
                else if (value < min || value > max)
                {
                    Error(node, $"{section}.{key}", $"{value} is out of range ({min} to {max}). Using the default");
                }
                else
                {
                    return value;
                }
            }

            return null;
        }

        /// <param name="check">Returns an error message for a bad item, or null. Any bad item falls back to the default list.</param>
        /// <param name="retired">
        /// Says why a value that used to be valid is now left out (a warning), or null; the rest of the list is kept.
        /// </param>
        private List<string>? SettingStrings(
            TomlTableNode tree, TomlTableNode defaults, string section, string key, Func<string, string?>? check,
            Func<string, string?>? retired = null)
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, section, key, out var node))
                {
                    continue;
                }

                var values = StringArray(node, $"{section}.{key}", ". Using the default");
                if (values is null)
                {
                    continue;
                }

                if (retired is not null)
                {
                    for (var i = values.Count - 1; i >= 0; i--)
                    {
                        if (retired(values[i]) is { } why)
                        {
                            Warning(node, $"{section}.{key}", why);
                            values.RemoveAt(i);
                        }
                    }
                }

                if (check is not null)
                {
                    var bad = false;
                    foreach (var value in values)
                    {
                        if (check(value) is { } problem)
                        {
                            Error(node, $"{section}.{key}", problem + ". Using the default");
                            bad = true;
                        }
                    }

                    if (bad)
                    {
                        continue;
                    }
                }

                return values;
            }

            return null;
        }

        private static bool TryGetSetting(TomlTableNode root, string section, string key, out TomlNode node)
        {
            node = null!;
            return root.TryGet(section, out var sectionNode)
                && sectionNode is TomlTableNode table
                && table.TryGet(key, out node);
        }

        // ---- Variables and templates -------------------------------------------------------------

        /// <summary>Resolves a <c>[variables]</c> entry, recursively. Null means it has an error (already reported).</summary>
        private string? ResolveVariable(string name, List<string> chain)
        {
            if (_variables.TryGetValue(name, out var done))
            {
                return done;
            }

            var key = "variables." + name;
            if (_rawVariables is null || !_rawVariables.TryGet(name, out var node))
            {
                return null;
            }

            if (chain.Contains(name))
            {
                var cycle = string.Join(" -> ", chain.SkipWhile(n => n != name).Append(name));
                Error(node, key, $"variables refer to each other in a cycle: {cycle}");
                foreach (var member in chain.SkipWhile(n => n != name))
                {
                    _variables[member] = null;
                }

                return null;
            }

            if (!Template.IsValidName(name))
            {
                Error(node, key, "variable names can only use letters, digits, '_' and '-'");
                _variables[name] = null;
                return null;
            }

            if (Template.BuiltInVariables.Contains(name) || Template.LaunchPlaceholders.Contains(name))
            {
                Error(node, key, $"'{name}' is a built-in placeholder, so it can't be redefined");
                _variables[name] = null;
                return null;
            }

            if (node is not TomlScalar { Kind: TomlKind.String, Value: string raw })
            {
                Error(node, key, $"expected a string, found {TomlNode.KindName(node.Kind)}");
                _variables[name] = null;
                return null;
            }

            if (Template.TryParse(raw, _parts) is { } syntaxError)
            {
                Error(node, key, syntaxError);
                _variables[name] = null;
                return null;
            }

            var parts = _parts.ToArray();
            var result = new StringBuilder();
            chain.Add(name);
            foreach (var part in parts)
            {
                if (!part.IsPlaceholder)
                {
                    result.Append(part.Text);
                    continue;
                }

                if (part.Text == "home")
                {
                    result.Append(sources.HomeDir);
                    continue;
                }

                if (part.Text == "rom_root" || Template.LaunchPlaceholders.Contains(part.Text))
                {
                    Error(node, key, $"{{{part.Text}}} can't be used in [variables]; only {{home}} and other variables can");
                    chain.RemoveAt(chain.Count - 1);
                    _variables[name] = null;
                    return null;
                }

                if (_rawVariables.Contains(part.Text))
                {
                    var value = ResolveVariable(part.Text, chain);
                    if (value is null)
                    {
                        if (!_variables.ContainsKey(name))
                        {
                            Error(node, key, $"{{{part.Text}}} couldn't be resolved (see its own error)");
                            _variables[name] = null;
                        }

                        chain.RemoveAt(chain.Count - 1);
                        return null;
                    }

                    result.Append(value);
                    continue;
                }

                Error(node, key, $"unknown placeholder {{{part.Text}}}{Suggest(part.Text, VariableNames())}");
                chain.RemoveAt(chain.Count - 1);
                _variables[name] = null;
                return null;
            }

            chain.RemoveAt(chain.Count - 1);
            var resolved = result.ToString();
            _variables[name] = resolved;
            return resolved;
        }

        private List<string> VariableNames()
        {
            var names = new List<string> { "home", "rom_root" };
            if (_rawVariables is not null)
            {
                names.AddRange(_rawVariables.Keys);
            }

            return names;
        }

        /// <summary>
        /// Expands config variables in <paramref name="raw"/>. When <paramref name="keepLaunchPlaceholders"/>
        /// is true the result is still a template: literals are re-escaped and launch placeholders stay.
        /// Otherwise launch placeholders are errors and the result is plain text. Null means an error was reported.
        /// </summary>
        private string? Expand(string raw, TomlNode at, string key, bool keepLaunchPlaceholders, bool allowRomRoot)
        {
            if (Template.TryParse(raw, _parts) is { } syntaxError)
            {
                Error(at, key, syntaxError);
                return null;
            }

            var result = new StringBuilder();
            foreach (var part in _parts)
            {
                if (!part.IsPlaceholder)
                {
                    result.Append(keepLaunchPlaceholders ? Template.Escape(part.Text) : part.Text);
                    continue;
                }

                string? value;
                if (part.Text == "home")
                {
                    value = sources.HomeDir;
                }
                else if (part.Text == "rom_root" && allowRomRoot)
                {
                    value = _romRoot;
                }
                else if (Template.LaunchPlaceholders.Contains(part.Text))
                {
                    if (!keepLaunchPlaceholders)
                    {
                        Error(at, key, $"{{{part.Text}}} is only known at launch time, so it can't be used here");
                        return null;
                    }

                    result.Append('{').Append(part.Text).Append('}');
                    continue;
                }
                else if (_rawVariables is not null && _rawVariables.Contains(part.Text))
                {
                    value = ResolveVariable(part.Text, []);
                    if (value is null)
                    {
                        Error(at, key, $"variable {{{part.Text}}} has an error (see variables.{part.Text})");
                        return null;
                    }
                }
                else
                {
                    var known = VariableNames();
                    if (!allowRomRoot)
                    {
                        known.Remove("rom_root");
                    }

                    if (keepLaunchPlaceholders)
                    {
                        known.AddRange(Template.LaunchPlaceholders);
                    }

                    Error(at, key, part.Text == "rom_root"
                        ? "{rom_root} can't be used here"
                        : $"unknown placeholder {{{part.Text}}}{Suggest(part.Text, known)}. Define it under [variables] in settings.toml");
                    return null;
                }

                result.Append(keepLaunchPlaceholders ? Template.Escape(value) : value);
            }

            return result.ToString();
        }

        /// <summary>Expands a path and makes it absolute (relative paths resolve against ConfigDir).</summary>
        private string? ExpandPath(string raw, TomlNode at, string key, bool allowRomRoot)
        {
            var expanded = Expand(raw, at, key, keepLaunchPlaceholders: false, allowRomRoot);
            if (expanded is null)
            {
                return null;
            }

            if (expanded.Length == 0)
            {
                Error(at, key, "the path is empty");
                return null;
            }

            try
            {
                return Path.GetFullPath(Path.IsPathRooted(expanded) ? expanded : Path.Combine(sources.ConfigDir, expanded));
            }
            catch (Exception e) when (e is ArgumentException or NotSupportedException or PathTooLongException)
            {
                Error(at, key, $"'{expanded}' isn't a valid path: {e.Message}");
                return null;
            }
        }

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
                    foreach (var key in (ReadOnlySpan<string>)["executable", "core", "args"])
                    {
                        if (entry.TryGet(key, out var extra))
                        {
                            Error(extra, prefix + "." + key,
                                "a run_file profile runs the game's own file, so it takes no executable, core or args");
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

                var args = new List<string>();
                var usesCore = false;
                var argsNode = default(TomlNode);
                if (!runFile && entry.TryGet("args", out argsNode) && StringArray(argsNode, prefix + ".args", string.Empty) is { } rawArgs)
                {
                    foreach (var rawArg in rawArgs)
                    {
                        if (Expand(rawArg, argsNode, prefix + ".args", keepLaunchPlaceholders: true, allowRomRoot: true) is { } arg)
                        {
                            args.Add(arg);
                            usesCore |= UsesPlaceholder(arg, "core");
                        }
                    }
                }

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

                if (ErrorCount > errorsBefore || (executable is null && !runFile))
                {
                    Info(entry, prefix, "this emulator is disabled until its errors are fixed");
                    continue;
                }

                result[id] = new EmulatorConfig(id, name, executable ?? string.Empty, args, workingDir, core, runFile);
            }

            return result;
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

        // ---- systems.toml ------------------------------------------------------------------------

        private List<SystemConfig> ReadSystems(
            TomlTableNode? table,
            HashSet<string> builtIn,
            Dictionary<string, string> builtInEmulatorOf,
            TomlTableNode? rawEmulators,
            Dictionary<string, EmulatorConfig> emulators)
        {
            var result = new List<SystemConfig>();
            if (table is null)
            {
                return result;
            }

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
                var steamStore = Bool(entry, prefix, "steam_store") ?? false;
                var recursive = Bool(entry, prefix, "recursive") ?? true;

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

                // The system's own games grid size: a bad one is only a warning (it's a matter of taste, so the system
                // stays enabled), and [display]'s is used.
                var gamesLayout = LayoutOverride(entry, prefix);
                var gamesColumns = GridOverride(entry, prefix, "games_columns", DisplaySettings.MaxColumns);
                var gamesRows = GridOverride(entry, prefix, "games_rows", DisplaySettings.MaxRows);
                var gamesSort = NameOverride(entry, prefix, "games_sort", Sorts.GamesNames, "sort", out var sortIndex) ? (GameSort?)sortIndex : null;
                var gamesSortOrder = NameOverride(entry, prefix, "games_sort_order", Sorts.OrderNames, "order", out var orderIndex) ? (SortOrder?)orderIndex : null;

                var romDirs = new List<string>();
                var romDirSource = RomDirSource.Default;
                if (entry.TryGet("rom_dirs", out var dirsNode) && StringArray(dirsNode, prefix + ".rom_dirs", string.Empty) is { } rawDirs)
                {
                    romDirSource = RomDirSource.Configured;
                    foreach (var rawDir in rawDirs)
                    {
                        if (ExpandPath(rawDir, dirsNode, prefix + ".rom_dirs", allowRomRoot: true) is { } dir
                            && !romDirs.Contains(dir, StringComparer.OrdinalIgnoreCase))
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
                    (int?)screenScraperId, romDirs, romDirSource, recursive, exclude, igdbPlatforms, steamStore, gamesColumns, gamesRows, gamesLayout,
                    gamesSort, gamesSortOrder, string.IsNullOrWhiteSpace(description) ? null : description)
                {
                    // The built-in definition's own emulator, offered with the alternatives once the user has chosen another.
                    DefaultEmulator = builtInEmulatorOf.TryGetValue(id, out var builtInEmulator) && emulators.ContainsKey(builtInEmulator) ? builtInEmulator : null,
                });
            }

            return result;
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
