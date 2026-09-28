using System.Net;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Scraping;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Scraping;

public sealed class ScrapeServiceTests : IAsyncLifetime
{
    private const string Sonic = "megadrive/Sonic the Hedgehog 3 (Europe).md";
    private const string Ecco = "megadrive/Ecco the Dolphin (USA, Europe).md";

    private ScrapeBed _bed = null!;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private static GameKey Key(string relPath) => new(relPath.Split('/')[0], relPath[(relPath.IndexOf('/') + 1)..].ToLowerInvariant());

    public async ValueTask InitializeAsync() => _bed = await ScrapeBed.CreateAsync("media = [\"cover\", \"box_texture\", \"spine\"]");

    public async ValueTask DisposeAsync()
    {
        Assert.Empty(_bed.Http.Unmatched);
        await _bed.DisposeAsync();
    }

    /// <summary>ScreenScraper doesn't have Ecco's cover or most of its metadata; IGDB does.</summary>
    private void EccoRoutes()
    {
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php") && u.Query.Contains("Ecco", StringComparison.Ordinal),
            _ => FakeHttpHandler.Json(_bed.Fill("ss_jeuinfos_nocover.json")));
        _bed.Http.On("POST", u => u.Host == "api.igdb.com", r =>
            (r.Body ?? string.Empty).Contains("Ecco the Dolphin", StringComparison.Ordinal)
                ? FakeHttpHandler.Json(ScrapeBed.Fixture("igdb_games_ecco.json"))
                : FakeHttpHandler.Json("[]"));
    }

    // ---- Matching and provider selection -----------------------------------------------------------

    [Fact]
    public async Task A_game_is_matched_by_file_name_size_and_hash_and_its_metadata_and_media_stored()
    {
        _bed.Rom(Sonic, "a small cartridge");
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var result = await service.ScrapeGameAsync(Key(Sonic), Ct);

        Assert.True((1, 1, 0) == (result.Total, result.Done, result.Failed), string.Join(" | ", _bed.Log.Lines));
        var lookup = _bed.Http.Requests.Single(r => r.Uri.AbsolutePath.EndsWith("jeuInfos.php", StringComparison.Ordinal));
        Assert.Equal("Sonic the Hedgehog 3 (Europe).md", lookup.Query("romnom"));
        Assert.Equal("1", lookup.Query("systemeid"));
        Assert.Equal("17", lookup.Query("romtaille"));
        Assert.Equal("rom", lookup.Query("romtype"));
        Assert.Matches("^[0-9A-F]{8}$", lookup.Query("crc"));
        Assert.Matches("^[0-9A-F]{40}$", lookup.Query("sha1"));

        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("Sonic the Hedgehog 3", game.Title);
        var metadata = game.Metadata!;
        Assert.Equal("Sonic and Tails race to stop Dr. Robotnik's Death Egg.", metadata.Description);
        Assert.Equal("1994-02-24", metadata.ReleaseDate);
        Assert.Equal("Sonic Team", metadata.Developer);
        Assert.Equal("Sega", metadata.Publisher);
        Assert.Equal("Platform", metadata.Genre);
        Assert.Equal("1-2", metadata.Players);
        Assert.Equal(0.8, metadata.Rating!.Value, 3);
        Assert.Equal("screenscraper", metadata.Source);
        Assert.Equal("ok", game.Scrape!.Status);
        Assert.Equal(["screenscraper"], game.Scrape.Providers);
        Assert.Equal(_bed.Clock.GetUtcNow(), game.Scrape.ScrapedAt);

        // The crc matched the ROM's, so the match is by hash; the eu cover beats the us one (regions = eu first).
        Assert.Equal("hash", _bed.Query<string>("SELECT method FROM scraper_matches WHERE scraper = 'screenscraper'"));
        Assert.Contains(_bed.Http.Requests, r => r.Query("media") == "box-2D(eu)");
        Assert.DoesNotContain(_bed.Http.Requests, r => r.Query("media") == "box-2D(us)");
        foreach (var kind in (string[])["cover", "box_texture", "spine"])
        {
            var path = MediaStore.RelativePathFor(Key(Sonic), kind, ".png");
            Assert.True(File.Exists(Path.Combine(_bed.Paths.DataDir, path)), kind);
            Assert.Equal("screenscraper", _bed.Query<string>("SELECT source FROM media WHERE kind = $kind", ("$kind", kind)));
        }

        // Nothing was missing, so the fallbacks weren't asked (and IGDB needed no token).
        Assert.Equal(0, _bed.Http.Count("igdb"));
        Assert.Equal(0, _bed.Http.Count("twitch"));
        Assert.Equal(0, _bed.Http.Count("steamgriddb"));
        Assert.True(File.Exists(ScrapedResponses.FullPath(_bed.Paths.DataDir, "screenscraper", Key(Sonic))));
    }

    [Fact]
    public async Task Fallback_providers_fill_only_the_missing_fields_and_media_in_order()
    {
        _bed.Reconfigure("media = [\"cover\", \"screenshot\"]");
        EccoRoutes();
        _bed.Rom(Ecco);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeGameAsync(Key(Ecco), Ct);

        var game = await _bed.Game("megadrive", "Ecco the Dolphin (USA, Europe).md");
        var metadata = game.Metadata!;
        Assert.Equal("Ecco the Dolphin", game.Title);
        Assert.Equal("Sega", metadata.Publisher);           // ScreenScraper
        Assert.Equal("1992", metadata.ReleaseDate);         // ScreenScraper, before IGDB's
        Assert.Equal("Novotrade", metadata.Developer);      // IGDB fills the gaps
        Assert.Equal("A dolphin searches for his pod.", metadata.Description);
        Assert.Equal("Adventure", metadata.Genre);
        Assert.Equal("1", metadata.Players);
        Assert.Equal(0.7, metadata.Rating!.Value, 3);
        Assert.Equal("screenscraper,igdb", metadata.Source);
        Assert.Equal("igdb", _bed.Query<string>("SELECT source FROM media WHERE kind = 'cover'"));
        Assert.Equal("screenscraper", _bed.Query<string>("SELECT source FROM media WHERE kind = 'screenshot'"));

        // In order: ScreenScraper, then IGDB; SteamGridDB had nothing left to add, so it wasn't asked.
        var requests = _bed.Http.Requests.ToList();
        Assert.True(requests.FindIndex(r => r.Uri.Host.Contains("screenscraper", StringComparison.Ordinal))
            < requests.FindIndex(r => r.Uri.Host == "api.igdb.com"));
        Assert.Equal(0, _bed.Http.Count("steamgriddb"));
    }

    [Fact]
    public async Task The_configured_provider_answers_first()
    {
        _bed.Reconfigure("provider = \"igdb\"\nfallback = [\"screenscraper\"]\nmedia = [\"cover\", \"box_texture\"]");
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeGameAsync(Key(Sonic), Ct);

        var metadata = (await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md")).Metadata!;
        Assert.Equal("IGDB summary of Sonic the Hedgehog 3.", metadata.Description);
        Assert.Equal("1994-02", metadata.ReleaseDate);      // the eu release, month precision, on the Mega Drive (29)
        Assert.Equal("1-2", metadata.Players);              // the Mega Drive's multiplayer mode, not another platform's
        Assert.Equal(0.845, metadata.Rating!.Value, 3);
        Assert.Equal("igdb", metadata.Source);
        Assert.Equal("igdb", _bed.Query<string>("SELECT source FROM media WHERE kind = 'cover'"));

        // ScreenScraper was still asked, for the box texture IGDB doesn't have.
        Assert.Equal("screenscraper", _bed.Query<string>("SELECT source FROM media WHERE kind = 'box_texture'"));
    }

    [Fact]
    public async Task A_title_search_finds_a_game_the_file_name_doesnt_and_takes_only_a_matching_name()
    {
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuRecherche.php"), _ => FakeHttpHandler.Json(_bed.Fill("ss_jeurecherche.json")));
        _bed.Rom("megadrive/Sonic the Hedgehog 3 [My Dump].md".Replace("Sonic the Hedgehog 3 [", "SONIC THE HEDGEHOG 3 [", StringComparison.Ordinal));
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php") && u.Query.Contains("romnom=SONIC", StringComparison.Ordinal),
            _ => FakeHttpHandler.Text("Erreur : Rom/Iso/Dossier non trouvée !", HttpStatusCode.NotFound));
        await _bed.ScanAsync();
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));

        await service.ScrapeGameAsync(Key("megadrive/SONIC THE HEDGEHOG 3 [My Dump].md"), Ct);

        Assert.Equal("search", _bed.Query<string>("SELECT method FROM scraper_matches"));
        Assert.Equal("1187", _bed.Query<string>("SELECT scraper_game_id FROM scraper_matches"));
        Assert.Contains(_bed.Http.Requests, r => r.Query("gameid") == "1187");
    }

    [Fact]
    public async Task Providers_without_credentials_are_skipped_and_reported_not_failed()
    {
        _bed.Reconfigure("media = [\"cover\", \"screenshot\"]");
        EccoRoutes();
        _bed.Rom(Ecco);
        await _bed.ScanAsync();
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));
        var notices = new List<ProviderNotice>();
        service.ProviderNotice += (_, e) => { lock (notices) { notices.Add(e.Notice); } };

        var result = await service.ScrapeGameAsync(Key(Ecco), Ct);

        Assert.Equal(0, result.Failed);
        var igdb = Assert.Single(result.Notices, n => n.Provider == "igdb");
        Assert.Equal(ProviderState.MissingCredentials, igdb.State);
        Assert.Contains("secrets.toml", igdb.Message, StringComparison.Ordinal);
        Assert.Contains("ODYSSEY_IGDB_CLIENT_ID", igdb.Message, StringComparison.Ordinal);
        Assert.Contains(result.Notices, n => n.Provider == "steamgriddb" && n.State == ProviderState.MissingCredentials);
        Assert.Contains(notices, n => n.Provider == "igdb");
        Assert.Equal("ok", (await _bed.Game("megadrive", "Ecco the Dolphin (USA, Europe).md")).Scrape!.Status);
        Assert.Equal(0, _bed.Http.Count("igdb") + _bed.Http.Count("twitch") + _bed.Http.Count("steamgriddb"));
        Assert.Equal(ProviderState.MissingCredentials, service.GetProviders().Single(p => p.Id == "igdb").State);
    }

    [Fact]
    public async Task With_no_credentials_at_all_nothing_is_queued_and_the_reasons_are_given()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service(ProviderAccounts.None);

        var result = await service.ScrapeAllMissingAsync(Ct);

        Assert.Equal(0, result.Total);
        Assert.Equal(3, result.Notices.Count);
        Assert.All(result.Notices, n => Assert.Equal(ProviderState.MissingCredentials, n.State));
        Assert.Empty(_bed.Http.Requests);
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM user.scrape_batches"));
    }

    // ---- IGDB's token ------------------------------------------------------------------------------

    [Fact]
    public async Task The_IGDB_token_is_cached_on_disk_and_renewed_when_refused_or_near_expiry()
    {
        _bed.Reconfigure("provider = \"igdb\"\nfallback = []\nmedia = [\"cover\"]");
        _bed.Rom(Sonic);
        _bed.Rom("megadrive/Sonic the Hedgehog 3 (USA).md");
        await _bed.ScanAsync();
        var accounts = ScrapeBed.Accounts(screenScraper: false, steamGridDb: false);

        using (var first = _bed.Service(accounts))
        {
            await first.ScrapeSystemAsync("megadrive", Ct);
        }

        Assert.Equal(1, _bed.Http.Count("id.twitch.tv"));
        var tokenRequest = _bed.Http.Requests.Single(r => r.Uri.Host == "id.twitch.tv");
        Assert.DoesNotContain(ScrapeBed.IgdbSecret, tokenRequest.Uri.AbsoluteUri, StringComparison.Ordinal);   // in the form body, never the URL
        var tokenFile = Path.Combine(_bed.Paths.DataDir, "tokens", "igdb.json");
        Assert.DoesNotContain(ScrapeBed.IgdbSecret, File.ReadAllText(tokenFile), StringComparison.Ordinal);
        Assert.All(_bed.Http.Requests.Where(r => r.Uri.Host == "api.igdb.com"), r => Assert.Equal(ScrapeBed.IgdbClientId, r.ClientId));

        // A new service (a new run) reads the cached token.
        using (var second = _bed.Service(accounts))
        {
            await second.ScrapeGameAsync(Key(Sonic), Ct);
        }

        Assert.Equal(1, _bed.Http.Count("id.twitch.tv"));

        // IGDB refuses it: a new token is fetched and the query tried again with it.
        var refusals = 0;
        _bed.Http.On("POST", u => u.Host == "api.igdb.com" && Interlocked.Increment(ref refusals) == 1, _ => FakeHttpHandler.Text("{\"message\":\"Authorization Failure\"}", HttpStatusCode.Unauthorized));
        using (var third = _bed.Service(accounts))
        {
            var result = await third.ScrapeGameAsync(Key(Sonic), Ct);
            Assert.Equal(0, result.Failed);
        }

        Assert.Equal(2, _bed.Http.Count("id.twitch.tv"));
        var igdbCalls = _bed.Http.Requests.Where(r => r.Uri.Host == "api.igdb.com").TakeLast(2).ToList();
        Assert.NotEqual(igdbCalls[0].Authorization, igdbCalls[1].Authorization);

        // 60 days on, the token is within a day of expiry: another one.
        _bed.Clock.Advance(TimeSpan.FromDays(60));
        using (var fourth = _bed.Service(accounts))
        {
            await fourth.ScrapeGameAsync(Key(Sonic), Ct);
        }

        Assert.Equal(3, _bed.Http.Count("id.twitch.tv"));
    }

    // ---- Limits, retries and quotas ----------------------------------------------------------------

    [Fact]
    public async Task Rate_limits_are_retried_after_the_wait_the_provider_asks_for()
    {
        var limited = 0;
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php") && Interlocked.Increment(ref limited) <= 2,
            _ => FakeHttpHandler.Json("{}", HttpStatusCode.TooManyRequests, TimeSpan.FromSeconds(7)));
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var result = await service.ScrapeGameAsync(Key(Sonic), Ct);

        Assert.Equal(0, result.Failed);
        Assert.Equal(3, _bed.Http.Count("jeuInfos.php"));
        Assert.Equal(2, _bed.Delays.Count(d => d == TimeSpan.FromSeconds(7)));
        Assert.Contains(_bed.Log.Lines, l => l.Contains("retrying in 7 s", StringComparison.Ordinal));
        Assert.Equal("ok", (await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md")).Scrape!.Status);
    }

    [Fact]
    public async Task Transient_errors_back_off_and_a_provider_that_keeps_failing_leaves_the_game_partial()
    {
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php"), _ => FakeHttpHandler.Text("down", HttpStatusCode.ServiceUnavailable));
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var result = await service.ScrapeGameAsync(Key(Sonic), Ct);

        Assert.Equal(4, _bed.Http.Count("jeuInfos.php"));                          // the retry policy's 4 attempts
        var waits = _bed.Delays.Where(d => d >= TimeSpan.FromSeconds(1)).Take(3).ToList();
        Assert.Equal(3, waits.Count);
        Assert.True(waits[1] > waits[0] && waits[2] > waits[1], "exponential backoff");
        Assert.Equal(0, result.Failed);                                            // IGDB found it: partial, not failed
        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("partial", game.Scrape!.Status);
        Assert.Equal("igdb", game.Metadata!.Source);
        Assert.Equal("error", _bed.Query<string>("SELECT status FROM scrape_log WHERE scraper = 'screenscraper'"));
    }

    [Fact]
    public async Task A_used_up_daily_quota_rests_the_provider_until_the_reset()
    {
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php"),
            _ => FakeHttpHandler.Text("Votre quota de scrape est dépassé pour aujourd'hui !", (HttpStatusCode)430));
        _bed.MaxThreads = 1;
        _bed.Rom(Sonic);
        _bed.Rom("megadrive/Sonic the Hedgehog 3 (USA).md");
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var result = await service.ScrapeSystemAsync("megadrive", Ct);

        Assert.Equal(1, _bed.Http.Count("jeuInfos.php"));                          // the second game didn't ask again
        var resting = Assert.Single(result.Notices, n => n.State == ProviderState.Resting);
        Assert.Equal("screenscraper", resting.Provider);
        Assert.True(resting.Until > _bed.Clock.GetUtcNow() && resting.Until <= _bed.Clock.GetUtcNow().AddDays(1));
        Assert.Equal(2L, _bed.Query<long>("SELECT COUNT(*) FROM scrape_state WHERE status = 'partial'"));
        Assert.Equal(ProviderState.Resting, service.GetProviders().Single(p => p.Id == "screenscraper").State);
    }

    [Fact]
    public async Task The_account_quota_ScreenScraper_reports_is_respected_before_asking()
    {
        _bed.RequestsToday = 20000;                                                 // of maxrequestsperday 20000
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var result = await service.ScrapeGameAsync(Key(Sonic), Ct);

        Assert.Equal(0, _bed.Http.Count("jeuInfos.php"));
        Assert.Equal(1, _bed.Http.Count("ssuserInfos.php"));
        Assert.Contains(result.Notices, n => n.Provider == "screenscraper" && n.Message.Contains("20000 of 20000", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Concurrency_stays_within_the_limit_the_account_reports()
    {
        _bed.MaxThreads = 2;
        var inFlight = 0;
        var peak = 0;
        _bed.Http.OnAsync("GET", u => u.Host.EndsWith("screenscraper.fr", StringComparison.Ordinal) && !u.AbsolutePath.Contains("ssuserInfos", StringComparison.Ordinal), async (r, token) =>
        {
            var now = Interlocked.Increment(ref inFlight);
            InterlockedMax(ref peak, now);
            await Task.Delay(15, token);
            Interlocked.Decrement(ref inFlight);
            return r.Uri.AbsolutePath.Contains("mediaJeu", StringComparison.Ordinal)
                ? FakeHttpHandler.Bytes(ScrapeBed.Png(r.Query("media") ?? "x"))
                : FakeHttpHandler.Json(_bed.Fill("ss_jeuinfos.json", r));
        });
        for (var i = 1; i <= 8; i++)
        {
            _bed.Rom($"megadrive/Sonic the Hedgehog 3 (Beta {i}).md");
        }

        await _bed.ScanAsync();
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));

        var result = await service.ScrapeSystemAsync("megadrive", Ct);

        Assert.Equal((8, 0), (result.Done, result.Failed));
        Assert.InRange(peak, 1, 2);
        var screenScraper = (ScreenScraperScraper)service.Scrapers["screenscraper"];
        Assert.Equal(2, screenScraper.Gate.MaxConcurrency);
        Assert.InRange(screenScraper.Gate.PeakInFlight, 1, 2);
        Assert.Equal(2, screenScraper.Limits!.MaxThreads);
    }

    private static void InterlockedMax(ref int target, int value)
    {
        int current;
        while ((current = Volatile.Read(ref target)) < value && Interlocked.CompareExchange(ref target, value, current) != current)
        {
        }
    }

    // ---- The queue: resume and cancel --------------------------------------------------------------

    /// <summary>ScreenScraper answers the first <paramref name="answered"/> lookups, then holds every other one until released.</summary>
    private TaskCompletionSource HoldLookupsAfter(int answered)
    {
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var seen = 0;
        _bed.Http.OnAsync("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php"), async (r, token) =>
        {
            if (Interlocked.Increment(ref seen) > answered)
            {
                await release.Task.WaitAsync(token);
            }

            return FakeHttpHandler.Json(_bed.Fill("ss_jeuinfos.json", r));
        });
        return release;
    }

    [Fact]
    public async Task A_batch_left_unfinished_when_the_service_stops_resumes_where_it_left_off()
    {
        _bed.MaxThreads = 1;
        for (var i = 1; i <= 5; i++)
        {
            _bed.Rom($"megadrive/Sonic the Hedgehog 3 (Beta {i}).md");
        }

        await _bed.ScanAsync();
        var release = HoldLookupsAfter(2);
        var accounts = ScrapeBed.Accounts(igdb: false, steamGridDb: false);
        var scraped = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var count = 0;
        var service = _bed.Service(accounts);
        service.GameScraped += (_, _) =>
        {
            if (Interlocked.Increment(ref count) == 2)
            {
                scraped.TrySetResult();
            }
        };

        var running = service.ScrapeSystemAsync("megadrive", Ct);
        await scraped.Task.WaitAsync(TimeSpan.FromSeconds(30), Ct);
        service.Dispose();                                                          // the app closes
        var paused = await running.WaitAsync(TimeSpan.FromSeconds(30), Ct);

        Assert.True(paused.Paused);
        var unfinished = Assert.Single(await ScrapeStoreBatches());
        Assert.Equal((5, 2, 3), (unfinished.Total, unfinished.Done, unfinished.Pending));

        release.SetResult();
        using var resumed = _bed.Service(accounts);
        var results = await resumed.ResumeAsync(Ct);

        var result = Assert.Single(results);
        Assert.Equal((5, 5, 0, false), (result.Total, result.Done, result.Failed, result.Paused));
        Assert.Equal(5L, _bed.Query<long>("SELECT COUNT(*) FROM scrape_state WHERE status = 'ok'"));
        Assert.Empty(await ScrapeStoreBatches());
    }

    [Fact]
    public async Task Cancelling_a_batch_drops_its_remaining_games()
    {
        _bed.MaxThreads = 1;
        for (var i = 1; i <= 4; i++)
        {
            _bed.Rom($"megadrive/Sonic the Hedgehog 3 (Beta {i}).md");
        }

        await _bed.ScanAsync();
        _ = HoldLookupsAfter(1);
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));
        var first = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        service.GameScraped += (_, _) => first.TrySetResult();
        long batchId = 0;
        service.BatchStarted += (_, e) => batchId = e.Result.BatchId;

        var running = service.ScrapeSystemAsync("megadrive", Ct);
        await first.Task.WaitAsync(TimeSpan.FromSeconds(30), Ct);
        await service.CancelBatchAsync(batchId);
        var result = await running.WaitAsync(TimeSpan.FromSeconds(30), Ct);

        Assert.True(result.Cancelled);
        Assert.Equal(1, result.Done);
        Assert.Empty(await ScrapeStoreBatches());
        Assert.Equal(1L, _bed.Query<long>("SELECT COUNT(*) FROM scrape_state"));
    }

    [Fact]
    public async Task Cancelling_the_callers_token_cancels_the_batch()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        _ = HoldLookupsAfter(0);
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));
        using var cancel = new CancellationTokenSource();
        service.Progress += (_, e) =>
        {
            if (e.Current is not null)
            {
                cancel.CancelAfter(50);
            }
        };

        var result = await service.ScrapeGameAsync(Key(Sonic), cancel.Token).WaitAsync(TimeSpan.FromSeconds(30), Ct);

        Assert.True(result.Cancelled);
        Assert.Empty(await ScrapeStoreBatches());
    }

    private Task<IReadOnlyList<ScrapeBatchInfo>> ScrapeStoreBatches() =>
        _bed.Library.ReadAsync<IReadOnlyList<ScrapeBatchInfo>>(ScrapeStore.UnfinishedBatches, Ct);

    // ---- Which games, and what survives -----------------------------------------------------------

    [Fact]
    public async Task Scrape_all_missing_picks_games_never_scraped_or_failed_plus_games_with_no_cover()
    {
        foreach (var name in (string[])["A", "B", "C", "D", "E", "F"])
        {
            _bed.Rom($"megadrive/{name}.md");
        }

        await _bed.ScanAsync();
        await _bed.Library.WriteAsync(c =>
        {
            foreach (var (name, status, cover) in (ReadOnlySpan<(string, string?, bool)>)
                [("B", "ok", true), ("C", "ok", false), ("D", "not_found", true), ("E", "partial", true), ("F", "error", true)])
            {
                using var command = c.CreateCommand();
                command.CommandText = """
                    INSERT INTO scrape_state (game_id, status, scraped_at) SELECT game_id, $status, 1 FROM games WHERE path_key = $key;
                    INSERT INTO media (game_id, kind, path, source) SELECT game_id, 'cover', 'x.png', 'screenscraper' FROM games WHERE path_key = $key AND $cover;
                    """;
                command.Parameters.AddWithValue("$status", status);
                command.Parameters.AddWithValue("$key", name.ToLowerInvariant() + ".md");
                command.Parameters.AddWithValue("$cover", cover);
                command.ExecuteNonQuery();
            }

            return true;
        }, Ct);

        var missing = await _bed.Library.ReadAsync(c => ScrapeStore.MissingGames(c, _bed.Config), Ct);

        Assert.Equal(["a.md", "c.md", "d.md", "f.md"], missing.Select(k => k.PathKey));

        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));
        var result = await service.ScrapeAllMissingAsync(Ct);
        Assert.Equal(4, result.Total);
        Assert.Equal(["A.md", "C.md", "D.md", "F.md"], _bed.Http.Requests.Where(r => r.Query("romnom") is not null).Select(r => r.Query("romnom")).Order());
    }

    [Fact]
    public async Task A_rescrape_never_overwrites_the_users_overrides()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        var key = Key(Sonic);
        await _bed.Library.SetTitleOverrideAsync(key, "My Sonic", Ct);
        await _bed.Library.SetMetadataOverrideAsync(key, new MetadataOverride(Description: "My own words.", Rating: 0.1), Ct);
        using var service = _bed.Service();

        await service.ScrapeGameAsync(key, Ct);
        await service.ScrapeGameAsync(key, Ct);

        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("My Sonic", game.Title);
        Assert.Equal("My own words.", game.Metadata!.Description);
        Assert.Equal(0.1, game.Metadata.Rating!.Value, 3);
        Assert.Equal("Sonic Team", game.Metadata.Developer);                      // not overridden: the scraped value
        Assert.Equal("My Sonic", _bed.Query<string>("SELECT title FROM user.game_overrides"));
        Assert.Equal("My own words.", _bed.Query<string>("SELECT description FROM user.game_overrides"));
        Assert.StartsWith("Sonic and Tails", _bed.Query<string>("SELECT description FROM metadata"), StringComparison.Ordinal);
        Assert.Equal("My Sonic", (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single().Title);
    }

    [Fact]
    public async Task A_stored_match_is_fetched_by_id_without_searching_again()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeGameAsync(Key(Sonic), Ct);
        await service.ScrapeGameAsync(Key(Sonic), Ct);

        var lookups = _bed.Http.Requests.Where(r => r.Uri.AbsolutePath.EndsWith("jeuInfos.php", StringComparison.Ordinal)).ToList();
        Assert.Equal(2, lookups.Count);
        Assert.NotNull(lookups[0].Query("romnom"));
        Assert.Equal("1187", lookups[1].Query("gameid"));
        Assert.Null(lookups[1].Query("romnom"));
        Assert.Equal("hash", _bed.Query<string>("SELECT method FROM scraper_matches"));   // the method it was matched by is kept
    }

    [Fact]
    public async Task A_manual_match_wins_and_survives_a_rescrape_and_a_rebuild()
    {
        const string Odd = "megadrive/Zz Unknown Prototype.md";
        _bed.Rom(Odd);
        await _bed.ScanAsync();
        _bed.Execute("INSERT INTO manual_matches VALUES ('megadrive', 'zz unknown prototype.md', 'screenscraper', '1187', 1)");
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));

        await service.ScrapeGameAsync(Key(Odd), Ct);

        Assert.DoesNotContain(_bed.Http.Requests, r => r.Query("romnom") is not null);   // never searched
        Assert.Equal("Sonic the Hedgehog 3", (await _bed.Game("megadrive", "Zz Unknown Prototype.md")).Title);
        Assert.Equal("manual", _bed.Query<string>("SELECT method FROM scraper_matches"));

        await service.ScrapeGameAsync(Key(Odd), Ct);
        Assert.Equal(2, _bed.Http.Requests.Count(r => r.Query("gameid") == "1187"));

        _bed.Http.Offline = true;
        await _bed.Library.RebuildAsync(null, Ct);

        Assert.Equal("manual", _bed.Query<string>("SELECT method FROM scraper_matches"));
        Assert.Equal("1187", _bed.Query<string>("SELECT scraper_game_id FROM scraper_matches"));
        Assert.Equal("Sonic the Hedgehog 3", (await _bed.Game("megadrive", "Zz Unknown Prototype.md")).Title);

        _bed.Http.Offline = false;
        await service.ScrapeGameAsync(Key(Odd), Ct);
        Assert.Equal(3, _bed.Http.Requests.Count(r => r.Query("gameid") == "1187"));
    }

    [Fact]
    public async Task A_rebuild_with_the_network_off_restores_metadata_matches_and_media_links()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using (var service = _bed.Service())
        {
            await service.ScrapeGameAsync(Key(Sonic), Ct);
        }

        var before = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        var coverBefore = (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single();
        var requests = _bed.Http.Requests.Count;
        _bed.Http.Offline = true;

        await _bed.Library.RebuildAsync(null, Ct);

        Assert.Equal(requests, _bed.Http.Requests.Count);
        var after = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal(before.Title, after.Title);
        Assert.Equal(before.Metadata, after.Metadata);
        Assert.Equal("ok", after.Scrape!.Status);
        var coverAfter = (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single();
        Assert.NotNull(coverAfter.CoverPath);
        Assert.Equal(coverBefore.CoverPath, coverAfter.CoverPath);
        Assert.Equal(coverBefore.CoverAspect, coverAfter.CoverAspect);
        Assert.Equal(coverBefore.CoverSizeBytes, coverAfter.CoverSizeBytes);
        Assert.Equal(3L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
        Assert.Equal("hash", _bed.Query<string>("SELECT method FROM scraper_matches"));
    }

    [Fact]
    public async Task A_recreated_library_gets_its_scraped_data_back_on_the_first_scan()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using (var service = _bed.Service())
        {
            await service.ScrapeGameAsync(Key(Sonic), Ct);
        }

        await _bed.ReopenAsync(deleteLibrary: true);
        Assert.Equal(Launcher.Core.Data.LibraryOpenOutcome.Created, _bed.Library.OpenOutcome);
        await _bed.ScanAsync();

        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("Sonic the Hedgehog 3", game.Title);
        Assert.Equal("Sonic Team", game.Metadata!.Developer);
        Assert.NotNull((await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single().CoverPath);
    }

    // ---- Clearing ----------------------------------------------------------------------------------

    [Fact]
    public async Task Clearing_a_game_removes_its_scraped_data_files_matches_and_overrides()
    {
        _bed.Rom(Sonic);
        var art = _bed.Dir.File("user/media/megadrive/screenshot/Sonic the Hedgehog 3 (Europe).png");
        File.WriteAllBytes(art, ScrapeBed.Png("own art"));
        await _bed.ScanAsync();
        var key = Key(Sonic);
        await _bed.Library.SetTitleOverrideAsync(key, "My Sonic", Ct);
        await _bed.Library.SetMetadataOverrideAsync(key, new MetadataOverride(Genre: "Mine"), Ct);
        await _bed.Library.SetFavouriteAsync(key, true, Ct);
        await _bed.Library.SetEmulatorOverrideAsync(key, "blastem", Ct);
        _bed.Execute("INSERT INTO manual_matches VALUES ('megadrive', 'sonic the hedgehog 3 (europe).md', 'igdb', '1234', 1)");
        using var service = _bed.Service(derivatives: true);
        await service.ScrapeGameAsync(key, Ct);
        var cover = Path.Combine(_bed.Paths.DataDir, MediaStore.RelativePathFor(key, "cover", ".png"));
        var response = ScrapedResponses.FullPath(_bed.Paths.DataDir, "screenscraper", key);
        var row = (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single();
        var derivative = TextureDerivatives.PathFor(_bed.Paths.CacheDir, MediaRoot.Data, row.CoverPath!, row.CoverSizeBytes, row.CoverMtimeMs);
        Assert.True(File.Exists(cover) && File.Exists(response));
        if (service.Derivatives.CanBake)
        {
            Assert.True(File.Exists(derivative));
        }

        var result = await service.ClearGameAsync(key, Ct);

        Assert.True(result.Found);
        Assert.False(File.Exists(cover));
        Assert.False(File.Exists(response));
        Assert.False(File.Exists(derivative));
        Assert.False(File.Exists(art));                                            // the user's own art for it, as asked
        Assert.Empty(Directory.EnumerateFiles(Path.Combine(_bed.Paths.DataDir, "scraped", "media"), "*", SearchOption.AllDirectories));
        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Null(game.Scrape);                                                  // never scraped
        Assert.Null(game.Metadata);
        Assert.Equal("Sonic the Hedgehog 3", game.Title);                          // the file-name title
        Assert.Null(game.TitleOverride);
        Assert.True(game.IsFavourite);
        Assert.Equal("blastem", game.EmulatorOverride);
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM scraper_matches"));
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM user.manual_matches"));
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM scrape_log"));
    }

    [Fact]
    public async Task Clearing_keeps_user_art_that_another_game_also_uses()
    {
        _bed.Rom("megadrive/Shared.md");
        _bed.Rom("megadrive/Shared.gen");
        var art = _bed.Dir.File("user/media/megadrive/cover/Shared.png");
        File.WriteAllBytes(art, ScrapeBed.Png("shared"));
        await _bed.ScanAsync();
        using var service = _bed.Service(ProviderAccounts.None);

        var result = await service.ClearGameAsync(Key("megadrive/Shared.md"), Ct);

        Assert.True(File.Exists(art));
        Assert.Equal(["media/megadrive/cover/Shared.png"], result.KeptSharedArt);
        Assert.NotNull((await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single(g => g.Title == "Shared" && g.CoverPath is not null).CoverPath);
    }

    // ---- Credentials -------------------------------------------------------------------------------

    [Fact]
    public async Task Credentials_appear_in_no_log_saved_response_database_or_media_file()
    {
        _bed.Reconfigure("media = [\"cover\", \"box_texture\", \"screenshot\", \"hero\", \"logo\"]");
        var limited = 0;
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php") && Interlocked.Increment(ref limited) == 1,
            _ => FakeHttpHandler.Json("{}", HttpStatusCode.TooManyRequests));
        _bed.Rom(Sonic);
        _bed.Rom(Ecco);
        await _bed.ScanAsync();
        using (var service = _bed.Service())
        {
            await service.ScrapeSystemAsync("megadrive", Ct);
        }

        Assert.Contains(_bed.Http.Requests, r => r.Uri.Host == "api.igdb.com");      // every provider took part
        Assert.Contains(_bed.Http.Requests, r => r.Uri.Host.EndsWith("steamgriddb.com", StringComparison.Ordinal));
        var saved = File.ReadAllText(ScrapedResponses.FullPath(_bed.Paths.DataDir, "screenscraper", Key(Sonic)));
        Assert.Contains("devpassword=***", saved, StringComparison.Ordinal);       // ScreenScraper's echoes were there, and are masked

        var forms = ScrapeBed.AllCredentials.SelectMany(c => new[] { c, Uri.EscapeDataString(c) }).Distinct().ToList();
        foreach (var file in Directory.EnumerateFiles(_bed.Paths.DataDir, "*", SearchOption.AllDirectories))
        {
            if (file.EndsWith(".png", StringComparison.Ordinal) || file.EndsWith(".dds", StringComparison.Ordinal))
            {
                continue;
            }

            using var stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
            using var reader = new StreamReader(stream);
            var text = reader.ReadToEnd();
            foreach (var form in forms)
            {
                Assert.False(text.Contains(form, StringComparison.Ordinal), $"'{Path.GetFileName(file)}' contains a credential");
            }
        }

        foreach (var line in _bed.Log.Lines)
        {
            foreach (var form in forms)
            {
                Assert.DoesNotContain(form, line, StringComparison.Ordinal);
            }
        }
    }
}
