using Launcher.Core.Media;
using Launcher.Core.Scanning;

namespace Launcher.Core.Config;

public sealed partial class ConfigLoader
{
    private sealed partial class Run
    {
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
            var groupSystems = SettingBool(tree, defaults, "display", "group_systems") ?? true;
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
                SettingBool(tree, defaults, "ui", "navigation_sounds") ?? true,
                (ButtonIcons)SettingName(tree, defaults, "button_icons", DisplayNames.ButtonIcons, [], "value", string.Empty, "ui"),
                (UiSize)SettingName(tree, defaults, "size", DisplayNames.UiSizes, [], "size", string.Empty, "ui"));
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
                    GroupSystems = groupSystems,
                },
                new ScrapingSettings(provider, fallback, regions, languages, media, hashLimitMb * 1024 * 1024),
                new ScanningSettings(_globalExcludes, SettingBool(tree, defaults, "scanning", "scan_at_launch") ?? false),
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
        /// A <c>[display]</c> (or <paramref name="section"/>) value that is one of <paramref name="names"/> (a layout, a sort,
        /// an order): its index. A bad one is an error and the default is used; one of <paramref name="others"/> (the other
        /// screen's) says why with <paramref name="otherWhy"/>.
        /// </summary>
        private int SettingName(
            TomlTableNode tree, TomlTableNode defaults, string key, IReadOnlyList<string> names, IReadOnlyList<string> others, string what, string otherWhy,
            string section = "display")
        {
            foreach (var source in (ReadOnlySpan<TomlTableNode>)[tree, defaults])
            {
                if (!TryGetSetting(source, section, key, out var node))
                {
                    continue;
                }

                if (node is not TomlScalar { Kind: TomlKind.String, Value: string value })
                {
                    Error(node, $"{section}.{key}", $"expected a string, found {TomlNode.KindName(node.Kind)}. Using the default");
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
                Error(node, $"{section}.{key}", $"{why}. The {what}s are {string.Join(", ", names)}. Using the default");
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
    }
}
