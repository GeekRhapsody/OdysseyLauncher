using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Ui;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Platform;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// The library's long operations (M7): rescans (the grid's F5 and the settings screen) and "scrape all missing",
/// each a <see cref="BackgroundJob"/> the HUD and the settings screen show, bound to the library's progress and the
/// scrape service's M4 events, and cancellable. Neither blocks navigation. It also owns the scrape service: built on
/// first use (off the main thread: it reads secrets.toml), and replaced when credentials or scraping settings change,
/// once no scrape is using it.
/// </summary>
public sealed class LibraryJobs : IDisposable
{
    public const string ScanKind = "scan";
    public const string ScrapeKind = "scrape";

    /// <summary>One game's scrape (M7), which can run beside a batch: the service puts single games first.</summary>
    public const string GameScrapeKind = "scrape-game";

    private readonly AppServices _services;
    private readonly MainThreadQueue _queue;
    private readonly CancellationTokenSource _shutdown = new();
    private readonly object _scraperLock = new();
    private ScrapeService? _scraper;
    private bool _scraperStale;

    public LibraryJobs(AppServices services, MainThreadQueue queue)
    {
        _services = services;
        _queue = queue;
        Jobs = new BackgroundJobs(queue);
    }

    public BackgroundJobs Jobs { get; }

    /// <summary>Main thread: a scan ended, with the systems as they now are, or why it failed (null systems).</summary>
    public event Action<IReadOnlyList<SystemSummary>?, string?>? ScanCompleted;

    public bool Scanning => Jobs.Running(ScanKind) is not null;

    /// <summary>A batch is running (scrape all missing, or a system).</summary>
    public bool Scraping => Jobs.Running(ScrapeKind) is not null;

    /// <summary>Main thread: these games' scraped data or user edits changed (a scrape, a clear), for the grid's titles.</summary>
    public event Action<IReadOnlyList<GameKey>>? GamesUpdated;

    // ---- Scans ---------------------------------------------------------------------------------------

    /// <summary>Rescans the given systems (null: every one) in the background. Main thread; false if a scan is running.</summary>
    public bool Scan(IReadOnlyList<string>? systemIds)
    {
        if (Scanning)
        {
            return false;
        }

        var cancel = CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        var job = Jobs.Start(ScanKind, systemIds is { Count: 1 } ? $"Scanning {SystemName(systemIds[0])}" : "Scanning your ROM folders", "systems", cancel.Cancel);
        var library = _services.Library;
        var progress = new JobProgressSink(job);
        _ = Task.Run(async () =>
        {
            try
            {
                ScanSummary total;
                if (systemIds is null)
                {
                    total = await library.RescanAsync(null, progress, cancel.Token).ConfigureAwait(false);
                }
                else
                {
                    var systems = new List<SystemScanSummary>();
                    for (var i = 0; i < systemIds.Count; i++)
                    {
                        job.Report(i, systemIds.Count);
                        var summary = await library.RescanAsync(systemIds[i], null, cancel.Token).ConfigureAwait(false);
                        systems.AddRange(summary.Systems);
                    }

                    job.Report(systemIds.Count, systemIds.Count);
                    total = new ScanSummary(systems, [], TimeSpan.Zero);
                }

                var shown = await library.GetSystemsAsync(cancel.Token).ConfigureAwait(false);
                GD.Print($"Scan: {total.Added} game(s) added, {total.Removed} removed.");
                var outcome = total.Added + total.Removed == 0
                    ? "Done: no new or removed games."
                    : string.Create(CultureInfo.InvariantCulture, $"Done: {total.Added:N0} new game{(total.Added == 1 ? string.Empty : "s")}, {total.Removed:N0} removed.");
                _queue.Post(() =>
                {
                    Jobs.End(job, JobState.Finished, outcome);
                    ScanCompleted?.Invoke(shown, null);
                });
            }
            catch (OperationCanceledException)
            {
                _queue.Post(() =>
                {
                    Jobs.End(job, JobState.Cancelled, "Scan stopped. Systems already scanned keep their changes.");
                    ScanCompleted?.Invoke(null, null);
                });
            }
            catch (Exception e)
            {
                _queue.Post(() =>
                {
                    Jobs.End(job, JobState.Failed, $"The scan failed: {e.Message}");
                    ScanCompleted?.Invoke(null, $"The scan failed: {e.Message}");
                });
            }
            finally
            {
                cancel.Dispose();
            }
        }, cancel.Token);
        return true;
    }

    // ---- Scraping ------------------------------------------------------------------------------------

    /// <summary>
    /// What "scrape all missing" would take on, and each provider's state, for the question asked before it starts.
    /// Thread pool (builds the service on first use).
    /// </summary>
    public async Task<(MissingSummary Missing, IReadOnlyList<ProviderStatus> Providers)> PreviewMissingAsync(CancellationToken cancellationToken)
    {
        var scraper = Scraper();
        var missing = await scraper.CountMissingAsync(cancellationToken).ConfigureAwait(false);
        return (missing, scraper.GetProviders());
    }

    /// <summary>Starts "scrape all missing" in the background. Main thread; false if a batch is running.</summary>
    public bool ScrapeMissing() => RunBatch("missing", "Scraping missing metadata", (scraper, token) => scraper.ScrapeAllMissingAsync(token));

    /// <summary>
    /// Starts scraping every game of a system in the background (the system options panel, M7). Main thread; false if
    /// a batch is running.
    /// </summary>
    public bool ScrapeSystem(string systemId) =>
        RunBatch("system", $"Scraping {SystemName(systemId)}", (scraper, token) => scraper.ScrapeSystemAsync(systemId, token));

    /// <summary>
    /// Scrapes one game in the background (the game options panel, M7), ahead of any batch. Main thread; false if that
    /// game is being scraped already. <paramref name="done"/> gets the outcome, on the main thread.
    /// </summary>
    public bool ScrapeGame(GameKey game, string title, Action<string>? done = null)
    {
        var jobTitle = $"Scraping {title}";
        foreach (var running in Jobs.Jobs)
        {
            if (running.Kind == GameScrapeKind && running.State == JobState.Running && running.Title == jobTitle)
            {
                return false;
            }
        }

        var cancel = CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        var job = Jobs.Start(GameScrapeKind, jobTitle, "games", cancel.Cancel);
        job.Report(0, 1);
        var library = _services.Library;
        _ = Task.Run(async () =>
        {
            var scraper = Scraper();
            void Noticed(object? sender, ProviderNoticeEventArgs e) => job.SetNote(e.Notice.Message);
            scraper.ProviderNotice += Noticed;
            try
            {
                var result = await scraper.ScrapeGameAsync(game, cancel.Token).ConfigureAwait(false);
                var details = await library.GetGameAsync(game, CancellationToken.None).ConfigureAwait(false);
                string outcome;
                JobState state;
                if (result.Cancelled)
                {
                    (outcome, state) = ("Scraping stopped.", JobState.Cancelled);
                }
                else if (result.Total == 0)
                {
                    (outcome, state) = (NothingQueued(result), JobState.Failed);
                }
                else
                {
                    job.Report(1, 1, result.Failed);
                    outcome = details?.Scrape switch
                    {
                        { Status: "ok" or "partial" } s => $"Found by {string.Join(" and ", s.Providers.Select(ScrapingPage.NameOf))}{(s.Status == "partial" ? ", though a provider failed" : string.Empty)}.",
                        { Status: "not_found" } => "No provider found it. Edit its title to match the game's name, then scrape it again.",
                        _ => "Scraping failed: a provider couldn't be reached.",
                    };
                    state = details?.Scrape?.Status is "ok" or "partial" ? JobState.Finished : JobState.Failed;
                }

                _queue.Post(() =>
                {
                    Jobs.End(job, state, outcome);
                    GamesUpdated?.Invoke([game]);
                    done?.Invoke(outcome);
                });
            }
            catch (OperationCanceledException)
            {
                _queue.Post(() => Jobs.End(job, JobState.Cancelled, "Scraping stopped."));
            }
            catch (Exception e)
            {
                _queue.Post(() =>
                {
                    Jobs.End(job, JobState.Failed, $"Scraping failed: {e.Message}");
                    done?.Invoke($"Scraping failed: {e.Message}");
                });
            }
            finally
            {
                scraper.ProviderNotice -= Noticed;
                cancel.Dispose();
                _queue.Post(RetireStaleScraper);
            }
        }, cancel.Token);
        return true;
    }

    /// <summary>What "scrape this system" would take on, and each provider's state. Thread pool.</summary>
    public async Task<(SystemScrapeCount Count, IReadOnlyList<ProviderStatus> Providers)> PreviewSystemAsync(string systemId, CancellationToken cancellationToken)
    {
        var scraper = Scraper();
        var count = await scraper.CountSystemAsync(systemId, cancellationToken).ConfigureAwait(false);
        return (count, scraper.GetProviders());
    }

    /// <summary>
    /// Clears a game's metadata (M4's clear: scraped data, every image including the user's own, its model, and the
    /// user's edits). Thread pool; the grid hears about it through <see cref="GamesUpdated"/> and the library's
    /// MediaChanged.
    /// </summary>
    public async Task<ClearResult> ClearGameAsync(GameKey game, CancellationToken cancellationToken)
    {
        var result = await Scraper().ClearGameAsync(game, cancellationToken).ConfigureAwait(false);
        _queue.Post(() => GamesUpdated?.Invoke([game]));
        return result;
    }

    /// <summary>Main thread: a game's title or metadata was edited, so the grid shows it.</summary>
    public void GameEdited(GameKey game) => GamesUpdated?.Invoke([game]);

    /// <summary>Why a scrape took on no game: no provider has credentials, or the first provider's reason.</summary>
    private static string NothingQueued(ScrapeBatchResult result, string otherwise = "No provider could look it up.")
    {
        if (result.Notices.Count == 0)
        {
            return otherwise;
        }

        return result.Notices.All(n => n.State == ProviderState.MissingCredentials)
            ? "None of your providers has its credentials yet: add them in Settings, under Scraping."
            : result.Notices[0].Message;
    }

    /// <summary>A batch (all missing, or a system) as a job bound to the service's events. Main thread; false if one is running.</summary>
    private bool RunBatch(string batchKind, string title, Func<ScrapeService, CancellationToken, Task<ScrapeBatchResult>> run)
    {
        if (Scraping)
        {
            return false;
        }

        var cancel = CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        var job = Jobs.Start(ScrapeKind, title, "games", cancel.Cancel);
        _ = Task.Run(async () =>
        {
            var scraper = Scraper();
            long batch = -1;
            void Started(object? sender, ScrapeBatchEventArgs e)
            {
                if (e.Result.Kind == batchKind)
                {
                    Interlocked.CompareExchange(ref batch, e.Result.BatchId, -1);
                }
            }

            void Progressed(object? sender, ScrapeProgressEventArgs e)
            {
                if (e.BatchId == Interlocked.Read(ref batch))
                {
                    job.Report(e.Done, e.Total, e.Failed);
                }
            }

            // Each game as it's done, so its title in the grid follows (its media follow the library's MediaChanged).
            void Scraped(object? sender, ScrapeGameEventArgs e)
            {
                if (e.BatchId == Interlocked.Read(ref batch))
                {
                    var game = e.Result.Game;
                    _queue.Post(() => GamesUpdated?.Invoke([game]));
                }
            }

            void Noticed(object? sender, ProviderNoticeEventArgs e) => job.SetNote(e.Notice.Message);

            scraper.BatchStarted += Started;
            scraper.Progress += Progressed;
            scraper.GameScraped += Scraped;
            scraper.ProviderNotice += Noticed;
            try
            {
                var result = await run(scraper, cancel.Token).ConfigureAwait(false);
                var state = result.Cancelled || result.Paused ? JobState.Cancelled : JobState.Finished;
                var outcome = result.Cancelled
                    ? string.Create(CultureInfo.InvariantCulture, $"Scraping stopped after {result.Done:N0} of {result.Total:N0} games.")
                    : result.Total == 0
                        ? NothingQueued(result, "Nothing needed scraping.")
                        : string.Create(CultureInfo.InvariantCulture, $"Done: {result.Done - result.Failed:N0} of {result.Total:N0} games scraped{(result.Failed > 0 ? $", {result.Failed:N0} failed" : string.Empty)}.");
                _queue.Post(() => Jobs.End(job, state, outcome));
            }
            catch (OperationCanceledException)
            {
                _queue.Post(() => Jobs.End(job, JobState.Cancelled, "Scraping stopped."));
            }
            catch (Exception e)
            {
                _queue.Post(() => Jobs.End(job, JobState.Failed, $"Scraping failed: {e.Message}"));
            }
            finally
            {
                scraper.BatchStarted -= Started;
                scraper.Progress -= Progressed;
                scraper.GameScraped -= Scraped;
                scraper.ProviderNotice -= Noticed;
                cancel.Dispose();
                _queue.Post(RetireStaleScraper);
            }
        }, cancel.Token);
        return true;
    }

    /// <summary>
    /// The settings screen's "test connection", with the credentials as they are in secrets.toml now: a service of
    /// its own, so a refusal doesn't rest the provider for real scrapes, and edits are always tested. Thread pool.
    /// </summary>
    public async Task<ConnectionTestResult> TestConnectionAsync(string providerId, CancellationToken cancellationToken)
    {
        using var service = Build();
        return await service.TestConnectionAsync(providerId, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Each provider's state, for the settings screen. Thread pool.</summary>
    public IReadOnlyList<ProviderStatus> Providers() => Scraper().GetProviders();

    /// <summary>
    /// Main thread: credentials or scraping settings changed, so the next scrape needs a new service. One a scrape is
    /// using carries on and is replaced when that scrape ends.
    /// </summary>
    public void ScraperChanged()
    {
        lock (_scraperLock)
        {
            _scraperStale = true;
        }

        if (!AnyScraping)
        {
            RetireStaleScraper();
        }
    }

    private bool AnyScraping => Scraping || Jobs.Running(GameScrapeKind) is not null;

    private void RetireStaleScraper()
    {
        if (AnyScraping)
        {
            return;
        }

        ScrapeService? old;
        lock (_scraperLock)
        {
            if (!_scraperStale)
            {
                return;
            }

            old = _scraper;
            _scraper = null;
            _scraperStale = false;
        }

        // Disposing waits for the queue to stop: never on the main thread.
        if (old is not null)
        {
            _ = Task.Run(old.Dispose);
        }
    }

    /// <summary>The scrape service, built on first use. Thread pool only: it reads secrets.toml.</summary>
    private ScrapeService Scraper()
    {
        lock (_scraperLock)
        {
            return _scraper ??= Build();
        }
    }

    private ScrapeService Build()
    {
        var accounts = ProviderAccounts.Load(_services.Paths.ConfigDir);
        foreach (var diagnostic in accounts.Diagnostics)
        {
            GD.Print(diagnostic.ToString());
        }

        return new ScrapeService(new ScrapeServiceOptions
        {
            Library = _services.Library,
            Paths = _services.Paths,
            Accounts = accounts.Accounts,
            Log = GodotLog.Instance,
            ImageDecoder = PlatformServices.CreateImageDecoder(),
        });
    }

    private string SystemName(string id) => _services.Config.FindSystem(id)?.Name ?? id;

    public void Dispose()
    {
        _shutdown.Cancel();
        ScrapeService? scraper;
        lock (_scraperLock)
        {
            scraper = _scraper;
            _scraper = null;
        }

        scraper?.Dispose();
    }

    /// <summary>The library's scan progress, straight into the job (Progress&lt;T&gt; would post through Godot's context, unbudgeted).</summary>
    private sealed class JobProgressSink(BackgroundJob job) : IProgress<JobProgress>
    {
        public void Report(JobProgress value) => job.Report(value.Done, value.Total);
    }

    /// <summary>The scrape service's log, in Godot's output (the service redacts it first).</summary>
    private sealed class GodotLog : ILog
    {
        public static GodotLog Instance { get; } = new();

        public void Write(LogLevel level, string message) => GD.Print($"Scrape: {level}: {message}");
    }
}
