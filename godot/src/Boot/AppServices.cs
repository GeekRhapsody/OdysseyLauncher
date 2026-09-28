using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Diagnostics;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Platform;

namespace Launcher.App.Boot;

/// <summary>Boot marks recorded on the timeline, so <c>--bench</c> shows where our start-up goes.</summary>
public static class BootMarks
{
    public const string ConfigLoaded = "config_loaded";
    public const string LibraryOpened = "library_opened";
    public const string SystemsLoaded = "systems_loaded";
    public const string ModelsLoaded = "models_loaded";
    public const string SceneBuilt = "scene_built";
    public const string SystemsGridBound = "systems_grid_bound";
    public const string WarmUpDone = "warm_up_done";
}

/// <summary>
/// Config, paths and the library, loaded off the main thread at boot (A3 boot path, steps 2 and 3) and shared by
/// everything after. Loading does file and DB I/O, so it only ever runs on the thread pool.
/// </summary>
public sealed class AppServices : IDisposable
{
    private AppServices(PlatformPaths paths, ConfigLoadResult config, LibraryService library, IReadOnlyList<SystemSummary> systems)
    {
        Paths = paths;
        Config = config.Config;
        Diagnostics = config.Diagnostics;
        Library = library;
        Systems = systems;
    }

    public PlatformPaths Paths { get; }

    public AppConfig Config { get; }

    public IReadOnlyList<Diagnostic> Diagnostics { get; }

    public LibraryService Library { get; }

    /// <summary>The boot query's result: enabled systems in config order, with their game counts.</summary>
    public IReadOnlyList<SystemSummary> Systems { get; set; }

    /// <summary>The root folder a media path is relative to.</summary>
    public string RootOf(MediaRoot root) => root == MediaRoot.Config ? Paths.ConfigDir : Paths.DataDir;

    /// <summary>Thread pool only.</summary>
    public static async Task<AppServices> LoadAsync(DebugOptions options, string executableDir, CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();
        var home = System.Environment.GetFolderPath(System.Environment.SpecialFolder.UserProfile);
        var paths = options.UserDir is { } userDir ? PlatformPaths.InOneFolder(userDir, home) : PlatformPaths.Detect(executableDir);
        var config = new ConfigLoader().Load(ConfigSources.FromDirectory(paths.ConfigDir, paths.HomeDir));
        var configMs = stopwatch.Elapsed.TotalMilliseconds;
        DebugHooks.Timeline.Mark(BootMarks.ConfigLoaded);

        var library = await LibraryService.OpenAsync(config.Config, paths.DataDir, null, cancellationToken).ConfigureAwait(false);
        library.ConfigDir = paths.ConfigDir;
        var libraryMs = stopwatch.Elapsed.TotalMilliseconds;
        DebugHooks.Timeline.Mark(BootMarks.LibraryOpened);
        try
        {
            var systems = await library.GetSystemsAsync(cancellationToken).ConfigureAwait(false);
            DebugHooks.Timeline.Mark(BootMarks.SystemsLoaded);
            GD.Print(string.Create(CultureInfo.InvariantCulture,
                $"Boot: config {configMs:0.0} ms, library {libraryMs - configMs:0.0} ms, systems query {stopwatch.Elapsed.TotalMilliseconds - libraryMs:0.0} ms (off the main thread); config in {paths.ConfigDir}, data in {paths.DataDir}"));
            foreach (var diagnostic in config.Diagnostics)
            {
                GD.Print(diagnostic.ToString());
            }

            if (library.ClosedOrphanSessions > 0)
            {
                GD.Print($"Boot: closed {library.ClosedOrphanSessions} play session(s) left open by a crash.");
            }

            return new AppServices(paths, config, library, systems);
        }
        catch
        {
            library.Dispose();
            throw;
        }
    }

    public void Dispose() => Library.Dispose();
}
