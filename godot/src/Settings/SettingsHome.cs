using System.Collections.Generic;
using System.Linq;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Library;

namespace Launcher.App.Settings;

/// <summary>
/// The main settings screen (M7; a short list of pages since 2026-11-07, docs/ARCHITECTURE.md decisions log): Library,
/// Systems, Emulators, Scraping, Appearance, Interface, Graphics and About, each with a one-line summary of its settings.
/// Above them, only while there are any: a row per running job (a rescan, a scrape, an import) with its progress, A
/// cancelling it. The problems in the config files are on <see cref="AboutPage"/>. Menu, B or the Back button closes
/// it; every change is saved as it's made, and applies without a restart.
/// </summary>
public sealed partial class SettingsHome : ListPanel
{
    private static readonly Hint[] Hints = [new("Choose", Prompt.Accept), new("Close", Prompt.Back, Prompt.Menu)];

    private readonly SettingsController _settings;
    private readonly SettingRow _library;
    private readonly SettingRow _scraping;
    private readonly SettingRow _appearance;
    private readonly SettingRow _interface;
    private readonly SettingRow _graphics;
    private readonly Dictionary<int, SettingRow> _jobRows = [];
    private readonly VBoxContainer _jobs;

    public SettingsHome(SettingsController settings)
        : base("Settings")
    {
        _settings = settings;

        _jobs = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        _jobs.AddThemeConstantOverride("separation", 4);
        Rows.AddChild(_jobs);

        _library = AddRow("Library", activated: () => Layer.Push(new LibraryPage(_settings)));
        AddRow("Systems", "Each system's ROM folders, emulator, games view and models", activated: () => Layer.Push(new SystemsPage(_settings)));
        AddRow("Emulators", "The programs your systems use, and where they are", activated: () => Layer.Push(new EmulatorsPage(_settings)));
        _scraping = AddRow("Scraping", activated: () => Layer.Push(new ScrapingPage(_settings)));
        _appearance = AddRow("Appearance", activated: () => Layer.Push(new AppearancePage(_settings)));
        _interface = AddRow("Interface", activated: () => Layer.Push(new InterfacePage(_settings)));
        _graphics = AddRow("Graphics", activated: () => Layer.Push(new GraphicsPage(_settings)));
        AddRow("About", $"Version {AboutPage.VersionText} · Check for updates, and your config files", activated: () => Layer.Push(new AboutPage(_settings)));

        SetHints(Hints);
        _settings.Jobs.Jobs.Changed += ShowJobs;
        _settings.ConfigApplied += OnConfigApplied;
        Refresh();
        ShowJobs();
    }

    /// <summary>Library, not a job's row above it, where A would cancel the job.</summary>
    public override Control? DefaultFocus => _library;

    public override void OnRevealed() => Refresh();

    public override void OnClosed()
    {
        _settings.Jobs.Jobs.Changed -= ShowJobs;
        _settings.ConfigApplied -= OnConfigApplied;
    }

    private void OnConfigApplied(AppConfig config) => Refresh();

    private void Refresh()
    {
        var services = _settings.Services;
        var config = services.Config;
        var withGames = services.Systems.Count(s => s.GameCount > 0);
        _library.Detail = $"{withGames} system{(withGames == 1 ? string.Empty : "s")} with games · {config.Settings.RomRoot}";

        var scraping = config.Settings.Scraping;
        _scraping.Detail = scraping.Fallback.Count == 0
            ? $"{ScrapingPage.NameOf(scraping.Provider)} only"
            : $"{ScrapingPage.NameOf(scraping.Provider)}, then {string.Join(" and ", scraping.Fallback.Select(ScrapingPage.NameOf))} for what's missing";

        var display = config.Settings.Display;
        _appearance.Detail = $"{services.Theme?.Active.Name ?? display.Theme} · {AppearancePage.LayoutSummary(display)}";
        _interface.Detail = InterfacePage.Summary(config.Settings.Ui);
        _graphics.Detail = GraphicsPage.Summary(display);
    }

    /// <summary>A row per running (or just ended) job: its progress, and A to cancel it.</summary>
    private void ShowJobs()
    {
        var jobs = _settings.Jobs.Jobs.Jobs;
        var seen = new HashSet<int>();
        foreach (var job in jobs)
        {
            seen.Add(job.Id);
            if (!_jobRows.TryGetValue(job.Id, out var row))
            {
                var captured = job;
                row = new SettingRow(job.Title, activated: () =>
                {
                    if (captured.CanCancel)
                    {
                        captured.Cancel();
                    }
                });
                _jobRows[job.Id] = row;
                _jobs.AddChild(row);
            }

            row.Detail = job.State == JobState.Running && job.Note is { } note ? $"{job.Describe()} · {note}" : job.Describe();
            row.Value = job.CanCancel ? "A  Cancel" : job.State == JobState.Running ? "Stopping…" : null;
            row.ValueColour = UiStyle.Warning;
            row.DetailColour = job.State switch
            {
                JobState.Running => UiStyle.Dim,
                JobState.Finished => UiStyle.Good,
                _ => UiStyle.Warning,
            };
        }

        foreach (var id in _jobRows.Keys.ToList())
        {
            if (!seen.Contains(id))
            {
                var row = _jobRows[id];
                _jobRows.Remove(id);
                if (row.HasFocus())
                {
                    _library.GrabFocus();
                }

                _jobs.RemoveChild(row);
                row.QueueFree();
            }
        }
    }

    public override bool Handle(NavCommand command)
    {
        if (command == NavCommand.Menu)
        {
            Close();
            return true;
        }

        return false;
    }
}
