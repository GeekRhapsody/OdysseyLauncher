using System.Globalization;
using System.Linq;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Theming.Downloads;

namespace Launcher.App.Settings;

/// <summary>
/// Settings, About (2026-11-07): the version and "Check for updates" (<see cref="AppUpdater"/>), the problems in the
/// config files, and the folder the settings are saved in.
/// </summary>
public sealed partial class AboutPage : ListPanel
{
    private readonly SettingsController _settings;
    private readonly SettingRow _update;
    private readonly SettingRow _problems;

    public AboutPage(SettingsController settings)
        : base("About")
    {
        _settings = settings;
        Subtitle = $"Odyssey Launcher {VersionText}";

        AddSection("Updates");
        _update = AddRow("Check for updates", activated: () => _settings.Updater.Check(this));

        AddSection("Config files");
        _problems = AddRow("Problems in your config files", activated: ShowProblems);
        AddRow("Settings folder", settings.Services.Paths.ConfigDir);

        SetHints(CommonHints.ChooseBack);
        _settings.ConfigApplied += OnConfigApplied;
        _settings.Updater.Changed += ShowUpdate;
        Refresh();
    }

    public override void OnRevealed() => Refresh();

    public override void OnClosed()
    {
        _settings.ConfigApplied -= OnConfigApplied;
        _settings.Updater.Changed -= ShowUpdate;
    }

    /// <summary>The version, without the commit a build adds after a +.</summary>
    public static string VersionText => AppVersion.Current?.ToString() ?? Launcher.Core.CoreInfo.Version;

    /// <summary>The problems (errors and warnings) in the config files, on a page of their own.</summary>
    private void ShowProblems()
    {
        var problems = _settings.Services.Diagnostics.Where(d => d.Severity != Severity.Info).ToList();
        if (problems.Count == 0)
        {
            ShowStatus("Every config file loaded cleanly.", UiStyle.Good, 4);
            return;
        }

        Layer.Push(new ConfigProblemsPanel(problems));
    }

    private void OnConfigApplied(AppConfig config) => Refresh();

    private void Refresh()
    {
        var diagnostics = _settings.Services.Diagnostics;
        var problems = diagnostics.Count(d => d.Severity != Severity.Info);
        var errors = diagnostics.Count(d => d.IsError);
        _problems.Detail = problems == 0
            ? "None: every file loaded cleanly"
            : errors == 0
                ? "Warnings only, such as emulators that aren't where config says"
                : $"{errors} error{(errors == 1 ? string.Empty : "s")}: a setting with an error uses its default until it's fixed";
        _problems.Value = problems == 0 ? null : problems.ToString(CultureInfo.InvariantCulture);
        _problems.ValueColour = UiStyle.Warning;
        ShowUpdate();
    }

    private void ShowUpdate()
    {
        var updater = _settings.Updater;
        _update.Detail = updater.Current is { } current
            ? $"You have {current}. Looks for a newer version on {updater.SourceName}, and installs it if you say so"
            : $"This build ({Launcher.Core.CoreInfo.Version}) isn't a release's, so it can't be updated";
        _update.Value = updater.Checking ? "Checking…" : null;
        _update.ValueColour = UiStyle.Dim;
    }
}
