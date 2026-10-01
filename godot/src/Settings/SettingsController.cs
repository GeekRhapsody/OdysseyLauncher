using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Ui;
using Launcher.Core.Config;

namespace Launcher.App.Settings;

/// <summary>
/// The main settings screen's logic (M7): opens it, saves what its pages change and applies it without a restart.
/// A save runs on the thread pool through <see cref="ConfigWriter"/> (the user's TOML files, comments kept, only
/// changed values, validated first; credentials to secrets.toml only). Then, on the main thread, the new config goes
/// to the library and launcher at once, a new theme is switched to, ROM folder changes rescan what they affect, and
/// new credentials or scraping settings give the next scrape a new service.
/// </summary>
public sealed class SettingsController(AppServices services, UiContext ui, LibraryJobs jobs)
{
    public AppServices Services { get; } = services;

    public UiContext Ui { get; } = ui;

    public LibraryJobs Jobs { get; } = jobs;

    public UiLayer Layer => Ui.Layer;

    /// <summary>The item options (M7 part 2), which a system's page also shows: its models and "scrape this system".</summary>
    public Options.ItemOptions? Options { get; set; }

    /// <summary>Main thread: config changed (the navigator refreshes what it shows, the launcher uses it next launch).</summary>
    public event Action<AppConfig>? ConfigApplied;

    /// <summary>Main thread: a theme was chosen and saved; the navigator switches to it.</summary>
    public event Action<string>? ThemeChosen;

    /// <summary>Main thread, from the Library section: rescan (the navigator's rescan, so the grid refreshes after it).</summary>
    public Action<IReadOnlyList<string>?>? Rescan { get; set; }

    public bool IsOpen => Layer.IsOpen;

    /// <summary>Opens the settings screen on its main page.</summary>
    public SettingsHome Open()
    {
        var home = new SettingsHome(this);
        Layer.Push(home);
        return home;
    }

    public ConfigWriter Writer() =>
        new(Services.Paths.ConfigDir, Services.Paths.HomeDir) { CheckInstallsFor = Services.SystemsWithGames() };

    /// <summary>
    /// Checks and saves <paramref name="edits"/> off the main thread, then applies them. <paramref name="check"/>
    /// runs first on the thread pool (it may do I/O: does the folder exist?) and returns why not to save, or null.
    /// <paramref name="saved"/> is shown on <paramref name="from"/> once it's done; <paramref name="then"/> runs after.
    /// </summary>
    public void Save(UiPanel from, IReadOnlyList<ConfigEdit> edits, string saved, Action<ConfigSaveResult>? then = null, Func<string?>? check = null)
    {
        from.ShowStatus("Saving…", UiStyle.Dim);
        var writer = Writer();
        _ = Task.Run(() =>
        {
            ConfigSaveResult result;
            try
            {
                result = check?.Invoke() is { } problem ? new ConfigSaveResult(problem, [], null, null) : writer.Save(edits);
            }
            catch (Exception e) when (e is System.IO.IOException or UnauthorizedAccessException)
            {
                result = new ConfigSaveResult($"The settings couldn't be written: {e.Message}", [], null, null);
            }

            Ui.Queue.Post(() => Applied(from, edits, result, saved, then));
        });
    }

    private void Applied(UiPanel from, IReadOnlyList<ConfigEdit> edits, ConfigSaveResult result, string saved, Action<ConfigSaveResult>? then)
    {
        if (!result.Saved)
        {
            from.ShowStatus(null);
            ConfirmDialog.Tell(Layer, "Not saved", result.Problem!);
            return;
        }

        if (result.Config is { } config)
        {
            Services.ApplyConfig(config);
            foreach (var diagnostic in config.Diagnostics)
            {
                if (diagnostic.Severity != Severity.Info)
                {
                    GD.Print(diagnostic.ToString());
                }
            }

            ConfigApplied?.Invoke(config.Config);
        }

        var scraperChanged = result.Accounts is not null;
        foreach (var edit in edits)
        {
            if (edit.File == ConfigFileKind.Settings && edit.Path.Count > 0 && edit.Path[0] == "scraping")
            {
                scraperChanged = true;
            }

            if (edit.File == ConfigFileKind.Settings && edit.Path is ["display", "theme"] && edit.Value is string theme)
            {
                ThemeChosen?.Invoke(theme);
            }
        }

        if (scraperChanged)
        {
            Jobs.ScraperChanged();
        }

        GD.Print(result.ChangedFiles.Count == 0
            ? "Settings: nothing changed."
            : $"Settings: saved {string.Join(", ", result.ChangedFiles)}.");
        from.ShowStatus(result.ChangedFiles.Count == 0 ? "No change: that's already the setting." : saved, UiStyle.Good, 5);
        then?.Invoke(result);
    }
}
