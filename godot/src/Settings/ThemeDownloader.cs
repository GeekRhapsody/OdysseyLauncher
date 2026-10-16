using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Theming.Downloads;

namespace Launcher.App.Settings;

/// <summary>
/// The theme downloader's state and operations (A6 Downloading themes), owned by the settings controller so a download
/// carries on when its page closes: the list as last read, and one install, update or removal at a time, run by Core's
/// <see cref="ThemeDownloads"/> on the thread pool (git and file I/O), with a progress card. Built the first time the
/// page opens, so nothing here (libgit2 included) loads at boot. Main thread, except where it says otherwise.
/// </summary>
public sealed class ThemeDownloader
{
    private readonly SettingsController _settings;
    private readonly ThemeDownloads _downloads;
    private bool _refreshing;

    public ThemeDownloader(SettingsController settings, string? localList)
    {
        _settings = settings;
        var services = settings.Services;
        _downloads = new ThemeDownloads(new LibGit2Client(), ThemeDownloadPaths.For(services.Paths),
            services.BuiltInThemes.Select(s => s.Id).ToList(), new GodotLog(), localList: localList, appVersion: Launcher.Core.Theming.Downloads.AppVersion.Current);
    }

    /// <summary>The list as last read, and the user's themes against it; null until the first read is in.</summary>
    public ThemeListResult? List { get; private set; }

    /// <summary>The theme an operation is running for, or null.</summary>
    public string? Busy { get; private set; }

    /// <summary>The running operation's progress, 0 to 1 (0 until the size is known).</summary>
    public double Progress { get; private set; }

    public bool Refreshing => _refreshing;

    public AppVersion? AppVersion => _downloads.AppVersion;

    public ThemeDownloadPaths Paths => _downloads.Paths;

    /// <summary>The list, a theme's state or the running operation changed.</summary>
    public event Action? Changed;

    /// <summary>
    /// Reads the list kept from last time at once, then fetches it (ES-DE's refresh on open; the only time the downloader
    /// touches the network unasked).
    /// </summary>
    public void Refresh()
    {
        if (_refreshing)
        {
            return;
        }

        _refreshing = true;
        Changed?.Invoke();
        var queue = _settings.Ui.Queue;
        _ = Task.Run(async () =>
        {
            if (List is null)
            {
                var cached = await _downloads.ReadCachedAsync().ConfigureAwait(false);
                queue.Post(() => Show(cached, refreshing: true));
            }

            ThemeListResult result;
            try
            {
                result = await _downloads.RefreshAsync().ConfigureAwait(false);
            }
            catch (Exception e)
            {
                GD.PushWarning($"Themes: {e.Message}");
                result = await _downloads.ReadCachedAsync().ConfigureAwait(false) with { RefreshProblem = e.Message };
            }

            queue.Post(() => Show(result, refreshing: false));
        });
    }

    /// <summary>Installs a listed theme (<paramref name="replace"/>: moving a folder of its id the downloader didn't make to the backups first).</summary>
    public void Install(ThemeListing listing, bool replace) =>
        Run(listing, $"Downloading {listing.Name}", (downloads, progress, token) =>
            downloads.InstallAsync(listing, BaseTheme(), replace, progress, token), Installed);

    /// <summary>
    /// Fetches an installed theme and brings it to its branch's tip, as ES-DE does (<paramref name="discardChanges"/>:
    /// overwriting the user's own changes). When an update would overwrite them, the user is asked first.
    /// </summary>
    public void Update(ThemeListing listing, bool discardChanges) =>
        Run(listing, $"Updating {listing.Name}", (downloads, progress, token) =>
            downloads.UpdateAsync(listing, BaseTheme(), discardChanges, progress, token), Updated, () => AskToOverwrite(listing));

    /// <summary>Deletes an installed theme. The page refuses the theme in use first.</summary>
    public void Remove(ThemeListing listing) =>
        Run(listing, $"Removing {listing.Name}", async (downloads, _, token) =>
            new ThemeOperationResult(await downloads.RemoveAsync(listing, token).ConfigureAwait(false), []), result =>
            {
                Tell($"{listing.Name} was removed.", UiStyle.Good);
            });

    private Launcher.Core.Theming.Theme? BaseTheme() => _settings.Services.Theme?.Themes.Base;

    private void Show(ThemeListResult result, bool refreshing)
    {
        List = result;
        _refreshing = refreshing;
        Changed?.Invoke();
    }

    private void Run(
        ThemeListing listing,
        string title,
        Func<ThemeDownloads, IProgress<GitProgress>, CancellationToken, Task<ThemeOperationResult>> operation,
        Action<ThemeOperationResult> done,
        Action? changesInTheWay = null)
    {
        if (Busy is not null)
        {
            Tell($"Wait for {Busy} to finish first.", UiStyle.Warning);
            return;
        }

        var cancel = new CancellationTokenSource();
        Busy = listing.Name;
        Progress = 0;
        var jobs = _settings.Jobs.Jobs;
        var job = jobs.Start("theme", title, "objects", () => cancel.Cancel());
        var queue = _settings.Ui.Queue;
        var progress = new JobProgress(this, job, queue);
        Changed?.Invoke();
        _ = Task.Run(async () =>
        {
            ThemeOperationResult? result = null;
            string? failure = null;
            var cancelled = false;
            var changes = false;
            try
            {
                result = await operation(_downloads, progress, cancel.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                cancelled = true;
            }
            catch (ThemeChangesException)
            {
                changes = true;
            }
            catch (GitException e)
            {
                failure = e.Message;
            }
            catch (Exception e)
            {
                failure = e.Message;
                GD.PushError($"Themes: {title} failed: {e}");
            }

            // The list's states again, from disk: what this changed, and nothing fetched.
            var list = await _downloads.ReadCachedAsync().ConfigureAwait(false);
            queue.Post(() =>
            {
                cancel.Dispose();
                Busy = null;
                List = List is null ? list : list with { RefreshProblem = List.RefreshProblem, Refreshed = List.Refreshed };
                if (result is not null)
                {
                    jobs.End(job, JobState.Finished, "Done");
                    GD.Print($"Themes: {title}: done.");
                    foreach (var diagnostic in result.Diagnostics)
                    {
                        GD.Print(diagnostic.ToString());
                    }

                    done(result);
                }
                else if (changes && changesInTheWay is not null)
                {
                    jobs.End(job, JobState.Cancelled, "Waiting: your own changes are in the way.");
                    Changed?.Invoke();
                    changesInTheWay();
                    return;
                }
                else if (cancelled)
                {
                    jobs.End(job, JobState.Cancelled, "Cancelled: nothing was changed.");
                    Tell($"{title}: cancelled.", UiStyle.Dim);
                }
                else
                {
                    jobs.End(job, JobState.Failed, failure ?? "It failed.");
                    GD.Print($"Themes: {title} failed: {failure}");
                    ConfirmDialog.Tell(_settings.Layer, $"{title} failed", failure ?? "It failed.");
                }

                Changed?.Invoke();
            });
        });
    }

    private void Installed(ThemeOperationResult result)
    {
        var listing = result.Status.Listing;
        var backup = result.BackupFolder is { } folder ? $"\n\nThe theme that was in its folder is in {folder}." : string.Empty;
        if (listing.Id == ActiveThemeId)
        {
            // A theme in use that was replaced (the user's own copy, or a broken download): applied again from its new files.
            _settings.ThemeFilesChanged(listing.Id);
            ConfirmDialog.Tell(_settings.Layer, $"{listing.Name} is installed", "It's the theme in use, so it's loaded again now." + backup);
            return;
        }

        ConfirmDialog.Ask(_settings.Layer, $"{listing.Name} is installed", $"Use it now? You can choose it later under Theme.{backup}", "Use it", "Not now", yes =>
        {
            if (yes && _settings.Layer.Top is { } top)
            {
                _settings.Save(top, [new Launcher.Core.Config.ConfigEdit(Launcher.Core.Config.ConfigFileKind.Settings, ["display", "theme"], listing.Id)],
                    $"Theme: {listing.Name}. Loading it now…");
            }
        });
    }

    private void Updated(ThemeOperationResult result)
    {
        var listing = result.Status.Listing;
        var inUse = listing.Id == ActiveThemeId;
        if (!result.Updated)
        {
            Tell($"{listing.Name} is up to date: there's nothing new.", UiStyle.Good);
            return;
        }

        if (inUse)
        {
            _settings.ThemeFilesChanged(listing.Id);
        }

        Tell(inUse ? $"{listing.Name} is updated, and loaded again." : $"{listing.Name} is updated.", UiStyle.Good);
    }

    // Its author changed the theme, and so did the user: updating overwrites the user's changes (ES-DE asks too).
    private void AskToOverwrite(ThemeListing listing) =>
        ConfirmDialog.Ask(_settings.Layer, $"Update {listing.Name}?",
            $"{listing.Name} has an update, but you've changed it too, and updating it overwrites your changes. Files you added are kept.",
            "Update it", "Keep my changes", yes =>
            {
                if (yes)
                {
                    Update(listing, discardChanges: true);
                }
            }, destructive: true);

    public string? ActiveThemeId => _settings.Services.Theme?.Active.Id;

    private void Tell(string text, Color colour)
    {
        if (_settings.Layer.Top is { } top)
        {
            top.ShowStatus(text, colour, 6);
        }
    }

    /// <summary>A download's progress, from libgit2's thread: the job's card, and the page's row once a frame at most.</summary>
    private sealed class JobProgress(ThemeDownloader owner, BackgroundJob job, Boot.MainThreadQueue queue) : IProgress<GitProgress>
    {
        private int _posted;

        public void Report(GitProgress value)
        {
            job.Report(value.ReceivedObjects, value.TotalObjects);
            if (Interlocked.Exchange(ref _posted, 1) == 0)
            {
                queue.Post(() =>
                {
                    Volatile.Write(ref _posted, 0);
                    owner.Progress = job.Fraction;
                    owner.Changed?.Invoke();
                });
            }
        }
    }

    private sealed class GodotLog : Launcher.Core.Diagnostics.ILog
    {
        public void Write(Launcher.Core.Diagnostics.LogLevel level, string message)
        {
            if (level == Launcher.Core.Diagnostics.LogLevel.Info)
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
