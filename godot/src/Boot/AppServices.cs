using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Diagnostics;
using Launcher.App.Theming;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Platform;

namespace Launcher.App.Boot;

/// <summary>Boot marks recorded on the timeline, so <c>--bench</c> shows where our start-up goes.</summary>
public static class BootMarks
{
    public const string ConfigLoaded = "config_loaded";
    public const string ThemeResolved = "theme_resolved";
    public const string LibraryOpened = "library_opened";
    public const string SystemsLoaded = "systems_loaded";
    public const string ModelsLoaded = "models_loaded";
    public const string SceneBuilt = "scene_built";
    public const string SystemsGridBound = "systems_grid_bound";
    public const string WarmUpDone = "warm_up_done";
}

/// <summary>
/// Config, paths, the theme and the library, loaded off the main thread at boot (A3 boot path, steps 2 and 3) and
/// shared by everything after. Loading does file and DB I/O, so it only ever runs on the thread pool.
/// </summary>
public sealed class AppServices : IDisposable
{
    private AppServices(
        PlatformPaths paths, ConfigLoadResult config, LibraryService library, IReadOnlyList<SystemSummary> systems,
        ThemePlan? theme, IReadOnlyList<Launcher.Core.Theming.ThemeSource> builtInThemes)
    {
        Paths = paths;
        _config = config.Config;
        _diagnostics = config.Diagnostics;
        Library = library;
        Systems = systems;
        Theme = theme;
        BuiltInThemes = builtInThemes;
    }

    public PlatformPaths Paths { get; }

    private AppConfig _config;
    private IReadOnlyList<Diagnostic> _diagnostics;
    private int _configVersion;

    /// <summary>Config as it is now: the settings screen replaces it when it saves (M7). Any thread may read it.</summary>
    public AppConfig Config => Volatile.Read(ref _config);

    /// <summary>What loading config found (errors, warnings), for the settings screen's list of problems.</summary>
    public IReadOnlyList<Diagnostic> Diagnostics => Volatile.Read(ref _diagnostics);

    public LibraryService Library { get; }

    /// <summary>The boot query's result: enabled systems in config order, with their game counts.</summary>
    public IReadOnlyList<SystemSummary> Systems { get; set; }

    /// <summary>
    /// The theme in use, resolved for the enabled systems (replaced when the theme is switched). Null in a headless run,
    /// which only launches.
    /// </summary>
    public ThemePlan? Theme { get; set; }

    /// <summary><c>--save-responses</c>: scraping saves each provider's response for this run, to debug it (A4).</summary>
    public bool SaveResponses { get; private init; }

    /// <summary>The app's own themes, read once at boot, for theme switches.</summary>
    public IReadOnlyList<Launcher.Core.Theming.ThemeSource> BuiltInThemes { get; }

    /// <summary>
    /// Bakes cover derivatives on its own below-normal thread (M4). Built on first use, after <c>interactive</c>, so
    /// its thread costs nothing at boot. Null decoder on platforms without one: nothing is baked there.
    /// </summary>
    public DerivativeService Derivatives => _derivatives ??= new DerivativeService(Library, Paths, PlatformServices.CreateImageDecoder());

    private DerivativeService? _derivatives;

    /// <summary>
    /// Main thread: config the settings screen saved (M7) takes effect without a restart. The library uses it for the
    /// next query or scan; the launch controller reads it at the next launch.
    /// </summary>
    public void ApplyConfig(ConfigLoadResult result)
    {
        ArgumentNullException.ThrowIfNull(result);
        Interlocked.Increment(ref _configVersion);
        Volatile.Write(ref _config, result.Config);
        Volatile.Write(ref _diagnostics, result.Diagnostics);
        Library.Config = result.Config;
    }

    /// <summary>
    /// A predicate for <see cref="ConfigSources.CheckInstallsFor"/>: true for the systems that had games when this was
    /// called. The built-in catalogue is long, so only those systems warn about a missing emulator.
    /// </summary>
    public Func<string, bool> SystemsWithGames()
    {
        var withGames = new HashSet<string>(StringComparer.Ordinal);
        foreach (var system in Systems)
        {
            if (system.GameCount > 0)
            {
                withGames.Add(system.SystemId);
            }
        }

        return withGames.Contains;
    }

    /// <summary>
    /// Thread pool: loads config again with the install checks, for the systems that have games, and replaces the
    /// problems the settings screen lists. Boot skips the checks (they're file I/O for every emulator of every system),
    /// and this runs after <c>interactive</c>. A save in the meantime has its own result, which is kept.
    /// </summary>
    public Task CheckInstallsAsync() => Task.Run(() =>
    {
        var version = Volatile.Read(ref _configVersion);
        var loaded = new ConfigLoader().Load(
            ConfigSources.FromDirectory(Paths.ConfigDir, Paths.HomeDir) with { CheckInstallsFor = SystemsWithGames() });
        if (version == Volatile.Read(ref _configVersion))
        {
            Volatile.Write(ref _diagnostics, loaded.Diagnostics);
            foreach (var diagnostic in loaded.Diagnostics)
            {
                if (diagnostic.Message.Contains("doesn't exist, so", StringComparison.Ordinal))
                {
                    GD.Print(diagnostic.ToString());
                }
            }
        }
    });

    /// <summary>
    /// Thread pool only. <paramref name="themeResolved"/> is called (on the thread pool) as soon as the theme is, before
    /// the library opens, so the main thread can start loading its models while the DB opens. Null skips the theme
    /// (a headless run, which only launches and can quit at once: nothing here then calls into Godot).
    /// </summary>
    public static async Task<AppServices> LoadAsync(
        DebugOptions options, string executableDir, string themesDir, Action<ThemePlan>? themeResolved, CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();

        // The base theme needs no config, so it's read while config loads. (Starting its models' threaded loads
        // from here too made them finish later, not sooner: docs/perf/m6-themes.md.)
        Task<(IReadOnlyList<Launcher.Core.Theming.ThemeSource> Sources, Launcher.Core.Theming.ThemeLoadResult Theme)>? builtIn = null;
        if (themeResolved is not null)
        {
            builtIn = Task.Run(() =>
            {
                var listing = new List<Diagnostic>();
                IReadOnlyList<Launcher.Core.Theming.ThemeSource> sources = Launcher.Core.Theming.ThemeCatalog.BuiltInSources(themesDir, listing);
                foreach (var diagnostic in listing)
                {
                    GD.Print(diagnostic.ToString());
                }

                return (sources, Launcher.Core.Theming.ThemeCatalog.LoadBase(sources));
            }, cancellationToken);
        }

        var home = System.Environment.GetFolderPath(System.Environment.SpecialFolder.UserProfile);
        var paths = options.UserDir is { } userDir ? PlatformPaths.InOneFolder(userDir, home) : PlatformPaths.Detect(executableDir);
        // The install checks need to know which systems have games, so they run after the library is open (CheckInstallsAsync).
        var config = new ConfigLoader().Load(ConfigSources.FromDirectory(paths.ConfigDir, paths.HomeDir) with { FileExists = null });
        var configMs = stopwatch.Elapsed.TotalMilliseconds;
        DebugHooks.Timeline.Mark(BootMarks.ConfigLoaded);

        // The theme resolves while the library opens: both are I/O-bound, and the theme's models (loaded as soon as
        // it's resolved) are then in by the time the DB is.
        Task<(IReadOnlyList<Launcher.Core.Theming.ThemeSource> BuiltIns, ThemePlan? Plan, double Ms)>? resolving = null;
        if (themeResolved is not null && builtIn is not null)
        {
            var themeId = options.Theme ?? config.Config.Settings.Display.Theme;
            resolving = Task.Run(async () =>
            {
                var clock = Stopwatch.StartNew();
                var (builtIns, builtInTheme) = await builtIn.ConfigureAwait(false);
                var plan = ThemePlan.Build(config.Config, paths, themeId, builtIns, builtInTheme, allowBase: options.Theme is not null);
                DebugHooks.Timeline.Mark(BootMarks.ThemeResolved);
                themeResolved(plan);
                return (builtIns, (ThemePlan?)plan, clock.Elapsed.TotalMilliseconds);
            }, cancellationToken);
        }

        var library = await LibraryService.OpenAsync(config.Config, paths.DataDir, null, cancellationToken).ConfigureAwait(false);
        library.IndexMedia = true;
        var libraryMs = stopwatch.Elapsed.TotalMilliseconds;
        DebugHooks.Timeline.Mark(BootMarks.LibraryOpened);
        try
        {
            var systems = await library.GetSystemsAsync(cancellationToken).ConfigureAwait(false);
            DebugHooks.Timeline.Mark(BootMarks.SystemsLoaded);
            var systemsMs = stopwatch.Elapsed.TotalMilliseconds;
            var (builtInThemes, theme, themeMs) = resolving is null ? ([], null, 0) : await resolving.ConfigureAwait(false);
            GD.Print(string.Create(CultureInfo.InvariantCulture,
                $"Boot: config {configMs:0.0} ms, then in parallel: theme '{theme?.Active.Id ?? "(headless: none)"}' {themeMs:0.0} ms, library {libraryMs - configMs:0.0} ms and systems query {systemsMs - libraryMs:0.0} ms (off the main thread); config in {paths.ConfigDir}, data in {paths.DataDir}"));
            foreach (var diagnostic in config.Diagnostics)
            {
                GD.Print(diagnostic.ToString());
            }

            foreach (var diagnostic in theme?.Diagnostics ?? [])
            {
                GD.Print(diagnostic.ToString());
            }

            if (library.ClosedOrphanSessions > 0)
            {
                GD.Print($"Boot: closed {library.ClosedOrphanSessions} play session(s) left open by a crash.");
            }

            return new AppServices(paths, config, library, systems, theme, builtInThemes) { SaveResponses = options.SaveResponses };
        }
        catch
        {
            library.Dispose();
            throw;
        }
    }

    public void Dispose()
    {
        _derivatives?.Dispose();
        Library.Dispose();
    }
}
