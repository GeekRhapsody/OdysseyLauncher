using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Scraping;
using Launcher.Core.Theming;

namespace Launcher.App.Settings;

/// <summary>
/// The main settings screen (M7): ROM folders, emulators, the theme, scraping, and the library's actions (rescan,
/// scrape all missing) with their progress and a way to cancel them. Menu, B or the Back button closes it; every
/// change is saved as it's made, and applies without a restart.
/// </summary>
public sealed partial class SettingsHome : ListPanel
{
    private readonly SettingsController _settings;
    private readonly SettingRow _roms;
    private readonly SettingRow _emulators;
    private readonly SettingRow _theme;
    private readonly SettingRow _scraping;
    private readonly SettingRow _rescan;
    private readonly SettingRow _scrapeMissing;
    private readonly SettingRow _problems;
    private readonly Dictionary<int, SettingRow> _jobRows = [];
    private readonly VBoxContainer _jobs;
    private bool _counting;

    public SettingsHome(SettingsController settings)
        : base("Settings")
    {
        _settings = settings;
        Subtitle = $"Saved in {settings.Services.Paths.ConfigDir}";

        AddSection("Games");
        _roms = AddRow("ROM folders", activated: () => Layer.Push(new RomFoldersPage(_settings)));
        _emulators = AddRow("Emulators", activated: () => Layer.Push(new EmulatorsPage(_settings)));

        AddSection("Look");
        _theme = AddRow("Theme", activated: ChooseTheme);

        AddSection("Scraping");
        _scraping = AddRow("Providers, media and credentials", activated: () => Layer.Push(new ScrapingPage(_settings)));

        AddSection("Library");
        _rescan = AddRow("Rescan the library", "Look for new, moved and removed games in every ROM folder", activated: Rescan);
        _scrapeMissing = AddRow("Scrape all missing metadata", "Games never scraped, not found, or without a front cover", activated: ScrapeMissing);
        _jobs = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        _jobs.AddThemeConstantOverride("separation", 4);
        Rows.AddChild(_jobs);

        AddSection("Config files");
        _problems = AddRow("Problems in your config files", activated: ShowProblems);

        SetHints("A  Choose     B / Menu  Close");
        _settings.Jobs.Jobs.Changed += ShowJobs;
        _settings.ConfigApplied += OnConfigApplied;
        Refresh();
        ShowJobs();
    }

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
        var custom = config.Systems.Count(s => s.RomDirSource == RomDirSource.Configured);
        _roms.Detail = custom == 0
            ? $"{config.Settings.RomRoot}, a folder per system"
            : $"{config.Settings.RomRoot}; {custom} system{(custom == 1 ? " has" : "s have")} its own";
        _emulators.Detail = $"{config.Emulators.Count} profiles; the programs your systems use";
        var active = services.Theme?.Active;
        _theme.Detail = active is null ? config.Settings.Display.Theme : $"{active.Name} ({active.Id})";
        var scraping = config.Settings.Scraping;
        _scraping.Detail = scraping.Fallback.Count == 0
            ? $"{ScrapingPage.NameOf(scraping.Provider)} only"
            : $"{ScrapingPage.NameOf(scraping.Provider)}, then {string.Join(" and ", scraping.Fallback.Select(ScrapingPage.NameOf))} for what's missing";

        var problems = services.Diagnostics.Count(d => d.Severity != Severity.Info);
        var errors = services.Diagnostics.Count(d => d.IsError);
        _problems.Detail = problems == 0
            ? "None: every file loaded cleanly"
            : errors == 0
                ? "Warnings only, such as emulators that aren't where config says"
                : $"{errors} error{(errors == 1 ? string.Empty : "s")}: a setting with an error uses its default until it's fixed";
        _problems.Value = problems == 0 ? null : problems.ToString(CultureInfo.InvariantCulture);
        _problems.ValueColour = UiStyle.Warning;
    }

    // ---- Theme --------------------------------------------------------------------------------------

    private void ChooseTheme()
    {
        var services = _settings.Services;
        var current = services.Theme?.Active.Id ?? services.Config.Settings.Display.Theme;
        ShowStatus("Reading the themes…", UiStyle.Dim);
        var builtIns = services.BuiltInThemes;
        var themesDir = Path.Combine(services.Paths.ConfigDir, ThemeLoader.FolderName);
        _ = Task.Run(() =>
        {
            // Each theme's name, from its manifest (user themes replace built-in ones with the same id).
            var names = new SortedDictionary<string, (string Name, string Where)>(StringComparer.Ordinal);
            foreach (var source in builtIns)
            {
                names[source.Id] = (NameOf(source.Manifest.Text, source.Id), "Built in");
            }

            foreach (var source in ThemeCatalog.UserSources(themesDir, []))
            {
                names[source.Id] = (NameOf(source.Manifest.Text, source.Id), source.Folder);
            }

            var choices = names.Select(n => new Choice(n.Key, n.Value.Name, n.Key == ThemeCatalog.BuiltInId ? "Built in; the default" : n.Value.Where)).ToList();
            _settings.Ui.Queue.Post(() =>
            {
                ShowStatus(null);
                if (Layer?.Top != this)
                {
                    return;
                }

                Layer.Push(new ChoicePanel("Theme", "Applied at once, and saved as [display] theme", choices, current, choice =>
                    _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["display", "theme"], choice.Id)], $"Theme: {choice.Title}. Loading it now…")));
            });
        });
    }

    private static string NameOf(string manifest, string id) =>
        TomlEditor.Parse(manifest, id, out _)?.Get(["name"]) as string ?? id;

    // ---- Library actions -------------------------------------------------------------------------------

    private void Rescan()
    {
        if (_settings.Jobs.Scanning)
        {
            ShowStatus("A scan is already running: it's below.", UiStyle.Dim, 4);
            return;
        }

        _settings.Rescan?.Invoke(null);
    }

    /// <summary>Counts what it would scrape first, and asks, saying which providers will be used.</summary>
    private void ScrapeMissing()
    {
        if (_settings.Jobs.Scraping)
        {
            ShowStatus("Scraping is already running: it's below.", UiStyle.Dim, 4);
            return;
        }

        if (_counting)
        {
            return;
        }

        _counting = true;
        _scrapeMissing.Value = "Counting…";
        var config = _settings.Services.Config;
        var jobs = _settings.Jobs;
        _ = Task.Run(async () =>
        {
            string? failure = null;
            (MissingSummary Missing, IReadOnlyList<ProviderStatus> Providers) preview = default;
            try
            {
                preview = await jobs.PreviewMissingAsync(CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                failure = e.Message;
            }

            _settings.Ui.Queue.Post(() =>
            {
                _counting = false;
                _scrapeMissing.Value = null;
                if (Layer?.Top != this)
                {
                    return;
                }

                if (failure is not null)
                {
                    ConfirmDialog.Tell(Layer, "Couldn't count the games", failure);
                    return;
                }

                AskToScrape(config, preview.Missing!, preview.Providers!);
            });
        });
    }

    private void AskToScrape(AppConfig config, MissingSummary missing, IReadOnlyList<ProviderStatus> providers)
    {
        if (missing.Games == 0)
        {
            ConfirmDialog.Tell(Layer, "Nothing to scrape", "Every game has been scraped and has a front cover.");
            return;
        }

        var usable = providers.Where(p => p.InOrder && p.State == ProviderState.Ready).ToList();
        if (usable.Count == 0)
        {
            ConfirmDialog.Ask(Layer, "No provider can scrape yet",
                "None of the providers you use has its credentials yet. Add them under Scraping first.",
                "Open Scraping", "Not now", yes =>
                {
                    if (yes)
                    {
                        Layer.Push(new ScrapingPage(_settings));
                    }
                });
            return;
        }

        var text = new StringBuilder();
        text.Append(CultureInfo.InvariantCulture, $"{missing.Games:N0} game{(missing.Games == 1 ? string.Empty : "s")} in ");
        text.Append(string.Join(", ", missing.Systems.Take(6).Select(s => string.Create(CultureInfo.InvariantCulture, $"{config.FindSystem(s.SystemId)?.Name ?? s.SystemId} ({s.Games:N0})"))));
        if (missing.Systems.Count > 6)
        {
            text.Append(CultureInfo.InvariantCulture, $" and {missing.Systems.Count - 6} more systems");
        }

        text.Append(" have never been scraped, weren't found, or have no front cover.\n\n");
        text.Append("They'll be looked up with ").Append(string.Join(", then ", usable.Select(p => p.DisplayName))).Append('.');
        foreach (var skipped in providers.Where(p => p.InOrder && p.State != ProviderState.Ready))
        {
            text.Append(' ').Append(skipped.DisplayName).Append(skipped.State == ProviderState.MissingCredentials ? " has no credentials, so it's skipped." : " is resting, so it's skipped for now.");
        }

        text.Append("\n\nIt runs in the background: you can keep browsing, and stop it here or with the Cancel button on its progress card.");
        ConfirmDialog.Ask(Layer, $"Scrape {missing.Games:N0} games?", text.ToString(), "Start scraping", "Not now", yes =>
        {
            if (yes)
            {
                _settings.Jobs.ScrapeMissing();
            }
        });
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
                    _scrapeMissing.GrabFocus();
                }

                _jobs.RemoveChild(row);
                row.QueueFree();
            }
        }

        _rescan.Value = _settings.Jobs.Scanning ? "Running" : null;
        _scrapeMissing.Value = _settings.Jobs.Scraping ? "Running" : _counting ? "Counting…" : null;
    }

    // ---- Problems --------------------------------------------------------------------------------------

    private void ShowProblems()
    {
        var problems = _settings.Services.Diagnostics.Where(d => d.Severity != Severity.Info).Take(12).ToList();
        if (problems.Count == 0)
        {
            ShowStatus("Every config file loaded cleanly.", UiStyle.Good, 4);
            return;
        }

        var text = string.Join("\n\n", problems.Select(d => d.ToString()));
        ConfirmDialog.Tell(Layer, "Problems in your config files", text + "\n\nFix them in the files named (the settings screen won't overwrite them), or change the setting here.");
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
