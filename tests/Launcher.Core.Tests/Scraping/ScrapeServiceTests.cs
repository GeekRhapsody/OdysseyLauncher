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

    public async ValueTask InitializeAsync() => _bed = await ScrapeBed.CreateAsync("media = [\"cover\", \"label\", \"spine\"]");

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
        foreach (var kind in (string[])["cover", "label", "spine"])
        {
            // In the media folder, named after the ROM as the user's own art is, and indexed as a scan would.
            var file = _bed.MediaFile(Sonic, kind, ".png");
            Assert.True(File.Exists(file), kind);
            Assert.Equal($"media/megadrive/{MediaKinds.FolderOf(kind)}/Sonic the Hedgehog 3 (Europe).png", _bed.Query<string>("SELECT path FROM media WHERE kind = $kind", ("$kind", kind)));
            Assert.Equal("screenscraper", _bed.SuppliedBy(Key(Sonic), kind));
        }

        // Nothing was missing, so the fallbacks weren't asked (and IGDB needed no token).
        Assert.Equal(0, _bed.Http.Count("igdb"));
        Assert.Equal(0, _bed.Http.Count("twitch"));
        Assert.Equal(0, _bed.Http.Count("steamgriddb"));

        // Responses are saved only with --save-responses.
        Assert.False(Directory.Exists(Path.Combine(_bed.Paths.DataDir, ScrapedResponses.ScrapedFolder)));
    }

    [Fact]
    public async Task Responses_are_saved_only_when_asked_and_redacted()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service(saveResponses: true);

        await service.ScrapeGameAsync(Key(Sonic), Ct);

        var saved = ScrapedResponses.Load(_bed.Paths.DataDir, "screenscraper", Key(Sonic))!;
        Assert.Equal(("ok", "1187", "hash"), (saved.Status, saved.GameId, saved.Method));
        Assert.Equal(["cover", "label", "spine"], saved.Media.Select(m => m.Kind).Order());
        Assert.All(saved.Media, m => Assert.True(File.Exists(Path.Combine(_bed.Paths.DataDir, m.Path)), m.Path));
        Assert.DoesNotContain(ScrapeBed.DevPassword, saved.Response!, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_lookup_that_finds_nothing_saves_what_ScreenScraper_said()
    {
        _bed.Rom(Ecco);
        await _bed.ScanAsync();
        using var service = _bed.Service(saveResponses: true);

        await service.ScrapeGameAsync(Key(Ecco), Ct);

        // What the file lookup answered, and what the title search found, for debugging a game that isn't found.
        var saved = ScrapedResponses.Load(_bed.Paths.DataDir, "screenscraper", Key(Ecco))!;
        Assert.Equal(("not_found", null), (saved.Status, saved.GameId));
        Assert.Contains("jeuInfos.php, romnom=Ecco the Dolphin (USA, Europe).md: Erreur : Rom/Iso/Dossier non trouvée !", saved.Response, StringComparison.Ordinal);
        Assert.Contains("jeuRecherche.php, recherche=Ecco the Dolphin: 0 results", saved.Response, StringComparison.Ordinal);

        // A rebuild doesn't read a game into it.
        _bed.Http.Offline = true;
        await _bed.Library.RebuildAsync(null, Ct);
        Assert.Null((await _bed.Game("megadrive", "Ecco the Dolphin (USA, Europe).md")).Metadata);
    }

    [Fact]
    public async Task A_scrape_fills_only_kinds_with_no_file_and_never_replaces_one()
    {
        _bed.Rom(Sonic);
        var own = _bed.Dir.File("user/media/megadrive/covers/Sonic the Hedgehog 3 (Europe).jpg");
        var ownBytes = TestImages.Jpeg(30, 40);
        File.WriteAllBytes(own, ownBytes);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeGameAsync(Key(Sonic), Ct);

        // The cover the user put there (shared by the ROM's name, without its extension) stays, and isn't asked for.
        Assert.Equal(ownBytes, File.ReadAllBytes(own));
        Assert.False(File.Exists(_bed.MediaFile(Sonic, "cover", ".png")));
        Assert.DoesNotContain(_bed.Http.Requests, r => r.Query("media") is { } m && m.StartsWith("box-2D(", StringComparison.Ordinal));
        Assert.Equal("media/megadrive/covers/Sonic the Hedgehog 3 (Europe).jpg", _bed.Query<string>("SELECT path FROM media WHERE kind = 'cover'"));
        Assert.Equal(["label", "spine"], _bed.Scraped[Key(Sonic)].Media.Order());

        // A rescrape downloads nothing: every kind has its file.
        var label = File.ReadAllBytes(_bed.MediaFile(Sonic, "label", ".png"));
        var downloads = _bed.Http.Count("mediaJeu.php");
        await service.ScrapeGameAsync(Key(Sonic), Ct);
        Assert.Equal(downloads, _bed.Http.Count("mediaJeu.php"));
        Assert.Equal(label, File.ReadAllBytes(_bed.MediaFile(Sonic, "label", ".png")));

        // A file deleted (and the folder rescanned) is filled again by the next scrape.
        File.Delete(_bed.MediaFile(Sonic, "label", ".png"));
        await _bed.ScanAsync();
        await service.ScrapeGameAsync(Key(Sonic), Ct);
        Assert.True(File.Exists(_bed.MediaFile(Sonic, "label", ".png")));
        Assert.Equal(["label"], _bed.Scraped[Key(Sonic)].Media);
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
        Assert.Equal("igdb", _bed.SuppliedBy(Key(Ecco), "cover"));
        Assert.Equal("screenscraper", _bed.SuppliedBy(Key(Ecco), "screenshot"));

        // In order: ScreenScraper, then IGDB; SteamGridDB had nothing left to add, so it wasn't asked.
        var requests = _bed.Http.Requests.ToList();
        Assert.True(requests.FindIndex(r => r.Uri.Host.Contains("screenscraper", StringComparison.Ordinal))
            < requests.FindIndex(r => r.Uri.Host == "api.igdb.com"));
        Assert.Equal(0, _bed.Http.Count("steamgriddb"));
    }

    [Fact]
    public async Task The_configured_provider_answers_first()
    {
        _bed.Reconfigure("provider = \"igdb\"\nfallback = [\"screenscraper\"]\nmedia = [\"cover\", \"label\"]");
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
        Assert.Equal("igdb", _bed.SuppliedBy(Key(Sonic), "cover"));

        // ScreenScraper was still asked, for the support texture IGDB doesn't have.
        Assert.Equal("screenscraper", _bed.SuppliedBy(Key(Sonic), "label"));
    }

    [Fact]
    public async Task ScreenScraper_supplies_every_scrapable_kind_videos_as_mp4s_manuals_as_pdfs_and_no_box_texture()
    {
        _bed.Reconfigure("media = [\"cover\", \"back\", \"spine\", \"screenshot\", \"logo\", \"hero\", \"label\", \"video\", \"manual\"]");
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var result = await service.ScrapeGameAsync(Key(Sonic), Ct);

        Assert.True((1, 0) == (result.Done, result.Failed), string.Join(" | ", _bed.Log.Lines));
        foreach (var kind in MediaKinds.Scrapable)
        {
            Assert.Equal("screenscraper", _bed.SuppliedBy(Key(Sonic), kind));
        }

        Assert.Equal(MediaKinds.Scrapable.Count, (int)_bed.Query<long>("SELECT COUNT(*) FROM media"));   // no box texture
        Assert.DoesNotContain(_bed.Http.Requests, r => r.Query("media") is { } m && m.StartsWith("box-texture", StringComparison.Ordinal));
        Assert.Equal(0, _bed.Http.Count("igdb"));                                    // nothing was left for the fallbacks
        Assert.Equal(0, _bed.Http.Count("steamgriddb"));

        // The preferred types: the HD wheel, the normalised video, the support texture for the label.
        var asked = _bed.Http.Requests.Select(r => r.Query("media")).OfType<string>().ToList();
        Assert.Contains("wheel-hd(wor)", asked);
        Assert.DoesNotContain("wheel(wor)", asked);
        Assert.Contains("video-normalized", asked);
        Assert.DoesNotContain("video", asked);
        Assert.Contains("support-texture(eu)", asked);
        Assert.Contains("box-2D-back(eu)", asked);
        Assert.Contains("fanart", asked);
        Assert.Contains("manuel(eu)", asked);

        // The video is an .mp4 with no size; a rebuild indexes it from the media folder, and it goes with a clear.
        var video = _bed.MediaFile(Sonic, MediaKinds.Video, ".mp4");
        Assert.True(File.Exists(video));
        Assert.Equal(1L, _bed.Query<long>("SELECT COUNT(*) FROM media WHERE kind = 'video' AND width IS NULL AND height IS NULL"));
        _bed.Http.Offline = true;
        await _bed.Library.RebuildAsync(null, Ct);
        Assert.Equal(1L, _bed.Query<long>("SELECT COUNT(*) FROM media WHERE kind = 'video' AND width IS NULL"));

        // So is the manual, in ES-DE's manuals folder.
        var manual = _bed.MediaFile(Sonic, MediaKinds.Manual, ".pdf");
        Assert.EndsWith(Path.Combine("megadrive", "manuals", "Sonic the Hedgehog 3 (Europe).pdf"), manual, StringComparison.Ordinal);
        Assert.Equal(1L, _bed.Query<long>("SELECT COUNT(*) FROM media WHERE kind = 'manual' AND width IS NULL"));

        await service.ClearGameAsync(Key(Sonic), Ct);
        Assert.False(File.Exists(video));
        Assert.False(File.Exists(manual));
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
                    INSERT INTO media (game_id, kind, path) SELECT game_id, 'cover', 'x.png' FROM games WHERE path_key = $key AND $cover;
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
    public async Task Editing_sees_the_scraped_values_and_the_users_apart()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        var key = Key(Sonic);
        using var service = _bed.Service();
        await service.ScrapeGameAsync(key, Ct);
        await _bed.Library.SetTitleOverrideAsync(key, "My Sonic", Ct);
        await _bed.Library.SetMetadataOverrideAsync(key, new MetadataOverride(Genre: "Mine", Rating: 0.5), Ct);

        var edit = (await _bed.Library.GetMetadataEditAsync(key, Ct))!;

        Assert.Equal("Sonic the Hedgehog 3", edit.Title);
        Assert.Equal("My Sonic", edit.TitleOverride);
        Assert.Equal("Platform", edit.Scraped!.Genre);
        Assert.Equal(0.8, edit.Scraped.Rating!.Value, 3);
        Assert.Equal(new MetadataOverride(Genre: "Mine", Rating: 0.5), edit.Overrides);
        Assert.Null(await _bed.Library.GetMetadataEditAsync(new GameKey("megadrive", "gone.md"), Ct));

        // The game's media, each a file in the media folder.
        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        var media = await _bed.Library.GetGameMediaInfoAsync(game.GameId, Ct);
        Assert.Equal(["cover", "label", "spine"], media.Select(m => m.Kind));
        Assert.All(media, m => Assert.Equal($"media/megadrive/{MediaKinds.FolderOf(m.Kind)}/Sonic the Hedgehog 3 (Europe).png", m.Media.Path));
    }

    [Fact]
    public async Task Scraping_a_system_is_counted_first()
    {
        _bed.Rom(Sonic);
        _bed.Rom(Ecco);
        _bed.Rom("megadrive/Other.md");
        _bed.Rom("snes/Elsewhere.sfc");
        await _bed.ScanAsync();
        using var service = _bed.Service();
        await service.ScrapeGameAsync(Key(Sonic), Ct);

        Assert.Equal(new SystemScrapeCount(3, 2, 2, 3, 2), await service.CountSystemAsync("megadrive", Ct));
        Assert.Equal(new SystemScrapeCount(1, 1, 1, 1, 1), await service.CountSystemAsync("snes", Ct));
        Assert.Equal(new SystemScrapeCount(0, 0, 0, 0, 0), await service.CountSystemAsync("unknown", Ct));
    }

    [Fact]
    public async Task Scraping_a_system_can_skip_games_with_a_cover_or_a_screenshot_or_scraped_recently()
    {
        _bed.Rom(Sonic);
        _bed.Rom(Ecco);
        _bed.Rom("megadrive/Other.md");
        File.WriteAllBytes(_bed.Dir.File("user/media/megadrive/screenshots/Ecco the Dolphin (USA, Europe).jpg"), TestImages.Jpeg(30, 40));
        await _bed.ScanAsync();
        using var service = _bed.Service();

        // Sonic is found (a cover, no screenshot), then 31 days on Other isn't found; Ecco has only the user's screenshot.
        await service.ScrapeGameAsync(Key(Sonic), Ct);
        _bed.Clock.Advance(TimeSpan.FromDays(31));
        await service.ScrapeGameAsync(Key("megadrive/Other.md"), Ct);
        Assert.Equal(new SystemScrapeCount(3, 2, 2, 2, 2), await service.CountSystemAsync("megadrive", Ct));

        async Task<List<GameKey>> Scrape(SystemScrapeFilter filter)
        {
            _bed.Scraped.Clear();
            var result = await service.ScrapeSystemAsync("megadrive", filter, Ct);
            Assert.Equal(result.Total, _bed.Scraped.Count);
            return [.. _bed.Scraped.Keys.OrderBy(k => k.PathKey, StringComparer.Ordinal)];
        }

        Assert.Equal([Key(Ecco), Key("megadrive/Other.md")], await Scrape(SystemScrapeFilter.NoCover));
        Assert.Equal([Key("megadrive/Other.md"), Key(Sonic)], await Scrape(SystemScrapeFilter.NoScreenshot));

        // Everything was scraped just now; a scrape counts as recent for 30 days, whatever it found.
        Assert.Empty(await Scrape(SystemScrapeFilter.NotRecent));
        _bed.Clock.Advance(TimeSpan.FromDays(30) - TimeSpan.FromMinutes(1));
        Assert.Equal(0, (await service.CountSystemAsync("megadrive", Ct)).NotRecent);
        _bed.Clock.Advance(TimeSpan.FromMinutes(2));
        Assert.Equal(3, (await Scrape(SystemScrapeFilter.NotRecent)).Count);
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
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false), saveResponses: true);

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
    public async Task A_rebuild_without_saved_responses_keeps_the_media_but_not_the_scraped_metadata()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using (var service = _bed.Service())
        {
            await service.ScrapeGameAsync(Key(Sonic), Ct);
        }

        var coverBefore = (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single();
        _bed.Http.Offline = true;

        await _bed.Library.RebuildAsync(null, Ct);

        // The media folder is indexed like any other files; what only the network knew needs a scrape.
        var coverAfter = (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single();
        Assert.Equal((coverBefore.CoverPath, coverBefore.CoverAspect, coverBefore.CoverSizeBytes), (coverAfter.CoverPath, coverAfter.CoverAspect, coverAfter.CoverSizeBytes));
        Assert.Equal(3L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
        var after = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Null(after.Metadata);
        Assert.Null(after.Scrape);
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM scraper_matches"));
    }

    [Fact]
    public async Task A_rebuild_with_the_network_off_restores_metadata_and_matches_from_saved_responses()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using (var service = _bed.Service(saveResponses: true))
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
        using (var service = _bed.Service(saveResponses: true))
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

    // ---- The Steam store ---------------------------------------------------------------------------

    private const string Portal = "steam/Portal 2.url";

    /// <summary>The Steam store first, for Windows and Steam games; every other system starts with ScreenScraper.</summary>
    private void SteamFirst(string media = "[\"cover\", \"hero\", \"logo\", \"screenshot\"]") =>
        _bed.Reconfigure($"provider = \"steam\"\nfallback = [\"screenscraper\", \"steamgriddb\"]\nmedia = {media}");

    [Fact]
    public async Task The_steam_store_finds_a_game_by_its_title_not_its_shortcuts_app_id()
    {
        SteamFirst();
        _bed.Rom(Portal, "[InternetShortcut]\nURL=steam://rungameid/400\n");     // the shortcut names Portal (400), not Portal 2
        await _bed.ScanAsync();
        using var service = _bed.Service(saveResponses: true);

        var result = await service.ScrapeGameAsync(Key(Portal), Ct);

        Assert.True((1, 1, 0) == (result.Total, result.Done, result.Failed), string.Join(" | ", _bed.Log.Lines));
        var search = Assert.Single(_bed.Http.Requests, r => r.Uri.AbsolutePath.Contains("SearchSuggestions", StringComparison.Ordinal));
        Assert.Contains("\"search_term\":\"Portal 2\"", ScrapeBed.SteamInput(search), StringComparison.Ordinal);
        Assert.Contains("\"country_code\":\"US\"", ScrapeBed.SteamInput(search), StringComparison.Ordinal);
        Assert.DoesNotContain(_bed.Http.Requests, r => r.Uri.AbsolutePath.Contains("/apps/400/", StringComparison.Ordinal)
            || ScrapeBed.SteamInput(r).Contains("400", StringComparison.Ordinal));
        Assert.Equal(0, _bed.Http.Count("GetItems"));                                    // the search answer had everything

        var game = await _bed.Game("steam", "Portal 2.url");
        Assert.Equal("Portal 2", game.Title);
        Assert.Equal(("Valve", "Valve", "2011-04-19", "steam"), (game.Metadata!.Developer, game.Metadata.Publisher, game.Metadata.ReleaseDate, game.Metadata.Source));
        Assert.Equal(0.98, game.Metadata.Rating!.Value, 3);
        Assert.Equal("ok", game.Scrape!.Status);
        Assert.Equal(["steam"], game.Scrape.Providers);
        Assert.Equal(("620", "search"), (_bed.Query<string>("SELECT scraper_game_id FROM scraper_matches"), _bed.Query<string>("SELECT method FROM scraper_matches")));
        foreach (var kind in (string[])["cover", "hero", "logo", "screenshot"])
        {
            Assert.Equal("steam", _bed.SuppliedBy(Key(Portal), kind));
        }

        Assert.Contains(_bed.Http.Requests, r => r.Method == "GET" && r.Uri.AbsolutePath.EndsWith("/apps/620/library_600x900_2x.jpg", StringComparison.Ordinal));
        Assert.Contains(_bed.Http.Requests, r => r.Method == "HEAD" && r.Uri.AbsolutePath.EndsWith("/apps/620/logo.png", StringComparison.Ordinal));
        Assert.Equal(1, _bed.Http.Count("jeuInfos.php"));                                // ScreenScraper for the genre and players Steam hasn't
        Assert.Equal(0, _bed.Http.Count("steamgriddb"));                                 // no media left for SteamGridDB

        // A rebuild with the network off gets it all back from the saved response and the media folder.
        var requests = _bed.Http.Requests.Count;
        _bed.Http.Offline = true;
        await _bed.Library.RebuildAsync(null, Ct);
        Assert.Equal(requests, _bed.Http.Requests.Count);
        var rebuilt = await _bed.Game("steam", "Portal 2.url");
        Assert.Equal((game.Title, game.Metadata), (rebuilt.Title, rebuilt.Metadata));
        Assert.Equal(4L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
    }

    [Fact]
    public async Task The_steam_store_is_only_asked_about_systems_with_steam_store()
    {
        SteamFirst("[\"cover\"]");
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeGameAsync(Key(Sonic), Ct);

        Assert.Equal(0, _bed.Http.Count("steampowered") + _bed.Http.Count("steamstatic"));
        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal(("Sonic the Hedgehog 3", "screenscraper"), (game.Title, game.Metadata!.Source));
    }

    [Fact]
    public async Task A_game_with_no_logo_on_steam_gets_one_from_the_next_provider()
    {
        SteamFirst("[\"cover\", \"logo\"]");
        _bed.Http.On("HEAD", u => u.Host == SteamStoreScraper.ImageHost, _ => FakeHttpHandler.Text("Not Found", HttpStatusCode.NotFound));
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "steamgriddb.com", "/api/v2/search/autocomplete/"),
            _ => FakeHttpHandler.Json("""{"success":true,"data":[{"id":5170,"name":"Portal 2","release_date":1303186800}]}"""));
        _bed.Rom(Portal, "[InternetShortcut]\nURL=steam://rungameid/620\n");
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeGameAsync(Key(Portal), Ct);

        Assert.Equal("steam", _bed.SuppliedBy(Key(Portal), "cover"));
        Assert.Equal("steamgriddb", _bed.SuppliedBy(Key(Portal), "logo"));
        Assert.Equal(0, _bed.Http.Count("/api/v2/grids/"));                             // SteamGridDB was asked for the logo alone
        Assert.DoesNotContain(_bed.Http.Requests, r => r.Method == "GET" && r.Uri.AbsolutePath.EndsWith("/logo.png", StringComparison.Ordinal));
    }

    [Fact]
    public async Task A_steam_store_match_is_fetched_by_its_app_id_and_found_again_when_its_gone()
    {
        SteamFirst("[\"cover\"]");
        _bed.Rom(Portal);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeGameAsync(Key(Portal), Ct);
        await service.ScrapeGameAsync(Key(Portal), Ct);

        Assert.Equal(1, _bed.Http.Count("SearchSuggestions"));
        var fetch = Assert.Single(_bed.Http.Requests, r => r.Uri.AbsolutePath.Contains("GetItems", StringComparison.Ordinal));
        Assert.Contains("\"ids\":[{\"appid\":620}]", ScrapeBed.SteamInput(fetch), StringComparison.Ordinal);
        Assert.Equal("search", _bed.Query<string>("SELECT method FROM scraper_matches"));   // the method it was matched by is kept

        // Steam no longer knows the stored id (success 15): the game is searched for again.
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "api.steampowered.com", "/IStoreBrowseService/GetItems/"),
            _ => FakeHttpHandler.Json(ScrapeBed.Fixture("steam_getitems_missing.json")));
        await service.ScrapeGameAsync(Key(Portal), Ct);

        Assert.Equal(2, _bed.Http.Count("GetItems"));
        Assert.Equal(2, _bed.Http.Count("SearchSuggestions"));
        Assert.Equal("ok", (await _bed.Game("steam", "Portal 2.url")).Scrape!.Status);
    }

    // ---- Clearing ----------------------------------------------------------------------------------

    [Fact]
    public async Task Clearing_a_game_removes_its_scraped_data_files_matches_and_overrides()
    {
        _bed.Rom(Sonic);
        var art = _bed.Dir.File("user/media/megadrive/screenshots/Sonic the Hedgehog 3 (Europe).png");
        File.WriteAllBytes(art, ScrapeBed.Png("own art"));
        await _bed.ScanAsync();
        var key = Key(Sonic);
        await _bed.Library.SetTitleOverrideAsync(key, "My Sonic", Ct);
        await _bed.Library.SetMetadataOverrideAsync(key, new MetadataOverride(Genre: "Mine"), Ct);
        await _bed.Library.SetFavouriteAsync(key, true, Ct);
        await _bed.Library.SetEmulatorOverrideAsync(key, "blastem", Ct);
        _bed.Execute("INSERT INTO manual_matches VALUES ('megadrive', 'sonic the hedgehog 3 (europe).md', 'igdb', '1234', 1)");
        using var service = _bed.Service(derivatives: true, saveResponses: true);
        await service.ScrapeGameAsync(key, Ct);
        var cover = _bed.MediaFile(Sonic, "cover", ".png");
        var response = ScrapedResponses.FullPath(_bed.Paths.DataDir, "screenscraper", key);
        var row = (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single();
        var derivative = TextureDerivatives.PathFor(_bed.Paths.CacheDir, row.CoverPath!, row.CoverSizeBytes, row.CoverMtimeMs);
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
        Assert.Empty(Directory.EnumerateFiles(Path.Combine(_bed.Paths.DataDir, MediaScanner.FolderName), "*", SearchOption.AllDirectories));
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
        var art = _bed.Dir.File("user/media/megadrive/covers/Shared.png");
        File.WriteAllBytes(art, ScrapeBed.Png("shared"));
        await _bed.ScanAsync();
        using var service = _bed.Service(ProviderAccounts.None);

        var result = await service.ClearGameAsync(Key("megadrive/Shared.md"), Ct);

        Assert.True(File.Exists(art));
        Assert.Equal(["media/megadrive/covers/Shared.png"], result.KeptSharedArt);
        Assert.NotNull((await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single(g => g.Title == "Shared" && g.CoverPath is not null).CoverPath);
    }

    [Fact]
    public async Task A_file_deleted_since_the_last_scan_is_scraped_again_and_its_stale_row_goes()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));
        await service.ScrapeGameAsync(Key(Sonic), Ct);
        var cover = _bed.MediaFile(Sonic, MediaKinds.Cover, ".png");
        var spine = _bed.MediaFile(Sonic, MediaKinds.Spine, ".png");

        // Deleted by hand, with no rescan: the rows still name the files.
        File.Delete(cover);
        File.Delete(spine);
        _bed.Reconfigure("media = [\"cover\"]");
        await service.ScrapeGameAsync(Key(Sonic), Ct);

        // The cover is fetched again; the spine isn't wanted any more, so its row goes rather than name a missing file.
        Assert.True(File.Exists(cover));
        Assert.Equal(1L, _bed.Query<long>("SELECT COUNT(*) FROM media WHERE kind = 'cover'"));
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM media WHERE kind = 'spine'"));
    }

    [Fact]
    public async Task Clearing_a_game_with_its_own_art_keeps_the_art_another_rom_of_its_name_uses()
    {
        _bed.Rom("megadrive/Shared.md");
        _bed.Rom("megadrive/Shared.gen");
        var own = _bed.Dir.File("user/media/megadrive/covers/Shared.md.png");
        var shared = _bed.Dir.File("user/media/megadrive/covers/Shared.png");
        File.WriteAllBytes(own, ScrapeBed.Png("own"));
        File.WriteAllBytes(shared, ScrapeBed.Png("shared"));
        await _bed.ScanAsync();
        using var service = _bed.Service(ProviderAccounts.None);

        await service.ClearGameAsync(Key("megadrive/Shared.md"), Ct);

        // Shared.md's cover was its own file; Shared.png is named for every ROM of that name, and Shared.gen shows it.
        Assert.False(File.Exists(own));
        Assert.True(File.Exists(shared));
    }

    [Fact]
    public async Task Clearing_removes_the_games_own_model_and_its_processed_copy()
    {
        _bed.Rom(Sonic);
        var model = _bed.Dir.File("user/media/megadrive/models/Sonic the Hedgehog 3 (Europe).md.glb");
        File.WriteAllBytes(model, Launcher.Core.Tests.Models.ModelFixtures.Model(100));
        await _bed.ScanAsync();
        var cache = new Launcher.Core.Models.ModelCache(_bed.Paths.CacheDir, null, null);
        Assert.NotNull(cache.Get(model, Launcher.Core.Models.ModelKind.PerGame).Path);
        using var service = _bed.Service(ProviderAccounts.None);

        var result = await service.ClearGameAsync(Key(Sonic), Ct);

        Assert.True(result.Found);
        Assert.False(File.Exists(model));
        Assert.Empty(Directory.GetFiles(cache.Folder));
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM media WHERE kind = 'model'"));
    }

    // ---- Credentials -------------------------------------------------------------------------------

    [Fact]
    public async Task Credentials_appear_in_no_log_saved_response_database_or_media_file()
    {
        _bed.Reconfigure("media = [\"cover\", \"label\", \"screenshot\", \"hero\", \"logo\", \"video\"]");
        var limited = 0;
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php") && Interlocked.Increment(ref limited) == 1,
            _ => FakeHttpHandler.Json("{}", HttpStatusCode.TooManyRequests));
        _bed.Rom(Sonic);
        _bed.Rom(Ecco);
        await _bed.ScanAsync();
        using (var service = _bed.Service(saveResponses: true))
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
