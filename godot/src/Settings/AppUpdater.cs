using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Diagnostics;
using Launcher.Core.Platform;
using Launcher.Core.Scraping;
using Launcher.Core.Theming.Downloads;
using Launcher.Core.Updates;

namespace Launcher.App.Settings;

/// <summary>
/// "Check for updates" (2026-10-18, docs/ARCHITECTURE.md A1 <c>Updates</c>), owned by the settings controller and made
/// the first time it's used, so nothing of it loads at boot and the launcher never checks unasked. A check asks GitHub
/// (or <c>--update-feed</c>'s folder) on the thread pool for the newest release; a newer one is offered in a question,
/// and yes opens <see cref="UpdatePanel"/>, which downloads it, hands it to the platform's installer and quits so the
/// installer can replace the files (on Linux, the <c>.AppImage</c>) and start the new version. Main thread, except where
/// it says otherwise.
/// </summary>
public sealed class AppUpdater
{
    private readonly SettingsController _settings;
    private readonly string? _feed;
    private readonly IUpdateInstaller _installer = PlatformServices.CreateUpdateInstaller();
    private readonly string _executable = Path.GetFullPath(OS.GetExecutablePath());
    private readonly bool _editorRun = OS.HasFeature("editor");
    private System.Net.Http.HttpClient? _client;
    private ILog? _log;

    public AppUpdater(SettingsController settings, string? feed)
    {
        _settings = settings;
        _feed = feed;
    }

    /// <summary>The running version, or null for a build that isn't a release's (its version doesn't parse).</summary>
    public AppVersion? Current { get; } = AppVersion.Current;

    /// <summary>A check is running.</summary>
    public bool Checking { get; private set; }

    /// <summary>A download is running (its panel is open).</summary>
    public bool Updating { get; internal set; }

    /// <summary>Where releases come from, for the user: GitHub, or the local feed's folder.</summary>
    public string SourceName => _feed ?? "GitHub";

    /// <summary>A check started or ended.</summary>
    public event Action? Changed;

    /// <summary>
    /// Null when this run can install an update, else why not, for the user. An editor run can check (for captures)
    /// but never installs: the executable it would replace is Godot's. Nor does a run the platform can't replace
    /// (a renamed executable, or on Linux a launcher not run from its AppImage).
    /// </summary>
    public string? CantInstall()
    {
        if (_editorRun)
        {
            return "This is an editor run, so it isn't installed: the launcher updates itself only from a release.";
        }

        _installer.Target(_executable, out var problem);
        return problem;
    }

    /// <summary>The file an update replaces and starts again: the executable, or on Linux its <c>.AppImage</c>.</summary>
    private string Installed => _installer.Target(_executable, out _) ?? _executable;

    /// <summary>
    /// Asks for the newest release, showing what it's doing on <paramref name="from"/>, and offers a newer one in a
    /// question. A failure is told in a dialog.
    /// </summary>
    public void Check(UiPanel from)
    {
        if (Checking || Updating)
        {
            return;
        }

        if (_installer.Platform is not { } platform)
        {
            ConfirmDialog.Tell(_settings.Layer, "No updates here", "The launcher can't update itself on this platform yet.");
            return;
        }

        if (Current is not { } current)
        {
            ConfirmDialog.Tell(_settings.Layer, "No updates for this build", $"This build's version ({Launcher.Core.CoreInfo.Version}) isn't a release's, so there's no telling which release is newer.");
            return;
        }

        Checking = true;
        Changed?.Invoke();
        from.ShowStatus($"Checking {SourceName} for a newer version…", UiStyle.Dim);
        var service = Service(platform);
        var queue = _settings.Ui.Queue;
        _ = Task.Run(async () =>
        {
            UpdateCheck? check = null;
            string? failure = null;
            try
            {
                // What an earlier update left (cancelled, failed, or the window closed while it downloaded).
                service.DeleteStaging();
                check = await service.CheckAsync(current).ConfigureAwait(false);
            }
            catch (UpdateException e)
            {
                failure = e.Message;
            }
            catch (Exception e)
            {
                failure = e.Message;
                GD.PushError($"Update: the check failed: {e}");
            }

            queue.Post(() =>
            {
                Checking = false;
                Changed?.Invoke();
                from.ShowStatus(null);
                if (failure is not null)
                {
                    GD.Print($"Update: the check failed: {failure}");
                    ConfirmDialog.Tell(_settings.Layer, "Couldn't check for updates", failure);
                }
                else if (check!.Available is not { } release)
                {
                    from.ShowStatus($"You have the newest version, {current}.", UiStyle.Good, 6);
                }
                else
                {
                    Offer(service, release, current);
                }
            });
        });
    }

    /// <summary>Asks whether to install <paramref name="release"/>, saying what it is and what happens.</summary>
    private void Offer(UpdateService service, UpdateRelease release, AppVersion current)
    {
        var text = new StringBuilder();
        text.Append(CultureInfo.InvariantCulture, $"Odyssey Launcher {release.Version} is out. You have {current}.");
        var notes = ReleaseFeed.Summary(release.Notes);
        if (notes.Count > 0)
        {
            text.Append("\n\n").Append(string.Join("\n", notes));
        }

        if (CantInstall() is { } reason)
        {
            text.Append("\n\n").Append(reason);
            if (release.Page is { } page)
            {
                text.Append(CultureInfo.InvariantCulture, $" It's at {page}.");
            }

            ConfirmDialog.Tell(_settings.Layer, "A new version is out", text.ToString());
            return;
        }

        var size = release.Package.Size > 0 ? $" ({UiStyle.Size(release.Package.Size)})" : string.Empty;
        text.Append(CultureInfo.InvariantCulture, $"\n\nDownload it{size}, install it and restart the launcher with it? Your settings, library, media and themes are kept.");
        if (RunningJobs() is { } jobs)
        {
            text.Append(CultureInfo.InvariantCulture, $" {jobs} stops when the launcher restarts.");
        }

        ConfirmDialog.Ask(_settings.Layer, $"Update to {release.Version}?", text.ToString(), "Update and restart", "Not now", yes =>
        {
            if (yes)
            {
                _settings.Layer.Push(new UpdatePanel(_settings, this, service, release, Handover(service)));
            }
        });
    }

    /// <summary>"The scan that's running", "The 2 jobs running", or null when nothing runs.</summary>
    private string? RunningJobs()
    {
        var running = new List<BackgroundJob>();
        foreach (var job in _settings.Jobs.Jobs.Jobs)
        {
            if (job.State == JobState.Running)
            {
                running.Add(job);
            }
        }

        return running.Count switch
        {
            0 => null,
            1 => $"\"{running[0].Title}\", which is running,",
            _ => $"Each of the {running.Count} jobs running",
        };
    }

    /// <summary>
    /// What the installer needs from this process, read here on the main thread (Godot's calls); the files are written
    /// on the panel's worker. The launcher starts again with the command line it was started with.
    /// </summary>
    private UpdateHandover Handover(UpdateService service)
    {
        var arguments = new List<string>(OS.GetCmdlineArgs());
        var user = OS.GetCmdlineUserArgs();
        if (user.Length > 0)
        {
            arguments.Add("--");
            arguments.AddRange(user);
        }

        return new UpdateHandover(
            OS.GetProcessId(),
            service.InstallDir,
            Package: string.Empty,
            BackupDir: string.Empty,
            service.StagingDir,
            Installed,
            arguments,
            System.Environment.CurrentDirectory,
            LogFile());
    }

    /// <summary>Thread pool: starts the installer for <paramref name="staged"/>; null once it runs, else why not.</summary>
    internal string? StartInstaller(UpdateHandover handover, StagedUpdate staged)
    {
        var problem = _installer.Start(handover with { Package = staged.Package, BackupDir = staged.BackupDir, StagingDir = staged.StagingDir });
        Log().Write(problem is null ? LogLevel.Info : LogLevel.Warning, problem is null
            ? $"Update: {staged.Release.Version} is with the installer, and starts once the launcher (process {handover.ProcessId}) has quit."
            : $"Update: the installer couldn't start: {problem}");
        return problem;
    }

    private UpdateService Service(string platform)
    {
        _client ??= ScraperHttp.CreateClient();
        IReleaseSource source = _feed is null ? new GitHubReleaseSource(_client) : new LocalReleaseSource(_feed);
        var installed = Installed;
        return new UpdateService(source, Path.GetDirectoryName(installed)!, Path.GetFileName(installed), platform, Log(), _installer.HelperName, _installer.Package);
    }

    private string LogFile() => Path.Combine(_settings.Services.Paths.DataDir, "logs", "update.log");

    /// <summary><c>DataDir/logs/update.log</c>, which the installer writes to as well, and Godot's output.</summary>
    private ILog Log() => _log ??= new UpdateLog(new FileLog(LogFile(), "update.1.log"));

    private sealed class UpdateLog(FileLog file) : ILog
    {
        public void Write(LogLevel level, string message)
        {
            file.Write(level, message);
            if (level == LogLevel.Info)
            {
                GD.Print(message);
            }
            else
            {
                GD.PushWarning(message);
            }
        }
    }
}
