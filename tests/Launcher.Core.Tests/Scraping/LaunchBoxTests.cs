using System.Net;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Scraping;
using Launcher.Core.Tests.TestSupport;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Tests.Scraping;

/// <summary>
/// LaunchBox's Games DB: the local copy of its database (downloaded, indexed, checked weekly), how its answers are read
/// (names and images by ScreenScraper's region order), and the provider in a scrape.
/// </summary>
public sealed class LaunchBoxTests : IAsyncLifetime
{
    private const string Sor2 = "megadrive/Streets of Rage 2 (USA).md";

    private ScrapeBed _bed = null!;
    private LaunchBoxDatabase? _database;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private static GameKey Key(string relPath) => new(relPath.Split('/')[0], relPath[(relPath.IndexOf('/') + 1)..].ToLowerInvariant());

    public async ValueTask InitializeAsync() => _bed = await ScrapeBed.CreateAsync("media = [\"cover\", \"back\", \"spine\", \"logo\", \"label\"]");

    public async ValueTask DisposeAsync()
    {
        _database?.Dispose();
        Assert.Empty(_bed.Http.Unmatched);
        await _bed.DisposeAsync();
    }

    private string Folder => Path.Combine(_bed.Paths.CacheDir, "launchbox");

    /// <summary>A copy of the database in the bed's cache folder, as a service makes its own.</summary>
    private LaunchBoxDatabase Database() => _database = new LaunchBoxDatabase(Folder, _bed.Http, _bed.Clock, (duration, _) =>
    {
        _bed.Clock.Advance(duration);
        return Task.CompletedTask;
    }, _bed.Log);

    private int DumpRequests => _bed.Http.Requests.Count(r => r.Method == "GET" && r.Uri.AbsoluteUri == LaunchBoxDatabase.DumpUrl);

    private static ScrapingSettings Settings(string regions) => new ConfigLoader().Load(new ConfigSources
    {
        HomeDir = "C:/home",
        ConfigDir = "C:/home/config",
        FileExists = null,
        Settings = new ConfigFile("settings.toml", $"[scraping]\nregions = {regions}\n"),
    }).Config.Settings.Scraping;

    // ---- Built-in systems --------------------------------------------------------------------------

    [Fact]
    public void Every_built_in_systems_LaunchBox_platforms_are_platforms_LaunchBox_has()
    {
        var known = ScrapeBed.Fixture("launchbox_platforms.txt").Split('\n', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries)
            .Where(line => !line.StartsWith('#'))
            .ToHashSet(StringComparer.Ordinal);
        var systems = new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/home", ConfigDir = "C:/home/config", FileExists = null }).Config.Systems;

        var named = systems.Where(s => s.LaunchBoxPlatforms is { Count: > 0 }).ToList();
        Assert.Equal(145, named.Count);
        Assert.All(named, s => Assert.All(s.LaunchBoxPlatforms!, p => Assert.True(known.Contains(p), $"{s.Id}: '{p}' isn't a LaunchBox platform")));
    }

    // ---- The local copy ----------------------------------------------------------------------------

    [Fact]
    public async Task The_dump_is_indexed_once_and_LaunchBox_is_asked_for_a_newer_one_only_after_a_week()
    {
        var database = Database();
        Assert.False(database.IsReady);
        Assert.True(database.NeedsCheck);

        Assert.Equal(LaunchBoxUpdateOutcome.Updated, await database.UpdateAsync(force: false, Ct));

        var info = database.Info!;
        Assert.Equal(5, info.Games);
        Assert.Equal(new DateTimeOffset(2026, 9, 28, 8, 0, 0, TimeSpan.Zero), info.Published);
        Assert.False(database.NeedsCheck);
        Assert.False(File.Exists(Path.Combine(Folder, "Metadata.zip.part")));         // the download isn't kept

        // Within the week: nothing asked.
        _bed.Clock.Advance(TimeSpan.FromDays(6));
        Assert.Equal(LaunchBoxUpdateOutcome.Unchanged, await database.UpdateAsync(force: false, Ct));
        Assert.Equal(1, DumpRequests);

        // After it: a conditional request, which LaunchBox answers with 304 Not Modified.
        _bed.Clock.Advance(TimeSpan.FromDays(2));
        Assert.True(database.NeedsCheck);
        Assert.Equal(LaunchBoxUpdateOutcome.Unchanged, await database.UpdateAsync(force: false, Ct));
        Assert.Equal("\"lb-1\"", _bed.Http.Requests.Last().IfNoneMatch);
        Assert.False(database.NeedsCheck);                                             // checked now

        // A newer dump replaces the copy.
        _bed.LaunchBoxETag = "\"lb-2\"";
        _bed.LaunchBoxDump = ScrapeBed.LaunchBoxZip(new Dictionary<string, string>
        {
            ["Metadata.xml"] = ScrapeBed.Fixture("launchbox_metadata.xml")
                .Replace("</LaunchBox>", "<Game><Name>Golden Axe</Name><DatabaseID>2006</DatabaseID><Platform>Sega Genesis</Platform></Game></LaunchBox>", StringComparison.Ordinal),
        });
        var titles = database.Titles(["Sega Genesis"]);
        Assert.Equal(LaunchBoxUpdateOutcome.Updated, await database.UpdateAsync(force: true, Ct));
        Assert.Equal(6, database.Info!.Games);
        Assert.DoesNotContain(titles, t => t.Name == "Golden Axe");
        Assert.Contains(database.Titles(["Sega Genesis"]), t => t.Name == "Golden Axe");  // the cached titles were the old copy's
    }

    [Fact]
    public async Task The_index_keeps_names_images_of_the_kinds_used_and_the_file_and_MAME_lists()
    {
        var database = Database();
        await database.UpdateAsync(force: false, Ct);

        var genesis = database.Titles(["Sega Genesis"]);
        Assert.Equal(
            [(2001L, "Streets of Rage 2", false), (2001, "Bare Knuckle II: Shitou e no Requiem", true), (2001, "Streets of Rage II", true),
             (2002, "Gunstar Heroes", false), (2003, "Streets of Rage", false)],
            genesis.Select(t => (t.Id, t.Name, t.Alternate)));
        Assert.Equal("1992", genesis[0].Year);
        Assert.Equal("1993", genesis[3].Year);                                         // ReleaseYear, with no date
        Assert.Equal("streets of rage 2", genesis[0].Norm);

        Assert.Equal("Streets of Rage 2 (USA)", database.FindFile(["Sega Genesis"], "sor2_V1.1"));
        Assert.Null(database.FindFile(["Sega Genesis"], "Gunstar Heroes (USA)"));     // named as its game: not kept
        Assert.Null(database.FindFile(["Super Nintendo Entertainment System"], "SOR2_v1.1"));
        Assert.Equal("Pac-Man (Midway)", database.FindMame("PACMAN"));

        var saved = database.Load(2001)!;
        Assert.DoesNotContain("sor2-banner", saved, StringComparison.Ordinal);       // a type no media kind uses
        Assert.Contains("sor2-front-eu.jpg", saved, StringComparison.Ordinal);
        Assert.Null(database.Load(9999));
    }

    [Fact]
    public async Task A_failed_update_keeps_the_copy_there_is()
    {
        var database = Database();
        await database.UpdateAsync(force: false, Ct);
        _bed.Http.On("GET", u => u.AbsoluteUri == LaunchBoxDatabase.DumpUrl, _ => FakeHttpHandler.Text("gone", HttpStatusCode.Forbidden));
        string? ended = null;
        database.UpdateEnded += (_, e) => ended = e.Error;

        var failure = await Assert.ThrowsAsync<ProviderException>(() => database.UpdateAsync(force: true, Ct));

        Assert.Equal(ScraperIds.LaunchBox, failure.Provider);
        Assert.Contains("HTTP 403", failure.Message, StringComparison.Ordinal);
        Assert.Equal(failure.Message, ended);
        Assert.True(database.IsReady);
        Assert.NotNull(database.Load(2001));
    }

    [Fact]
    public async Task A_server_error_is_retried()
    {
        var failures = 0;
        _bed.Http.On("GET", u => u.AbsoluteUri == LaunchBoxDatabase.DumpUrl, _ => Interlocked.Increment(ref failures) == 1
            ? FakeHttpHandler.Text("busy", HttpStatusCode.ServiceUnavailable)
            : FakeHttpHandler.Bytes(_bed.LaunchBoxDump, "application/x-zip-compressed"));
        var database = Database();

        Assert.Equal(LaunchBoxUpdateOutcome.Updated, await database.UpdateAsync(force: false, Ct));
        Assert.Equal(2, DumpRequests);
    }

    [Fact]
    public async Task A_copy_of_another_schema_is_downloaded_again()
    {
        var database = Database();
        await database.UpdateAsync(force: false, Ct);
        database.Dispose();
        _database = null;
        using (var connection = new SqliteConnection($"Data Source={Path.Combine(Folder, LaunchBoxDatabase.FileName)};Pooling=False"))
        {
            connection.Open();
            using var command = connection.CreateCommand();
            command.CommandText = "UPDATE meta SET value = '0' WHERE key = 'schema'";
            command.ExecuteNonQuery();
        }

        var reopened = Database();

        Assert.False(reopened.IsReady);
        Assert.True(reopened.NeedsCheck);
        Assert.Equal(LaunchBoxUpdateOutcome.Updated, await reopened.UpdateAsync(force: false, Ct));
        Assert.Null(_bed.Http.Requests.Last().IfNoneMatch);                            // not conditional: the copy is no use
        Assert.True(reopened.IsReady);
    }

    [Fact]
    public async Task Callers_share_one_update()
    {
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        _bed.Http.OnAsync("GET", u => u.AbsoluteUri == LaunchBoxDatabase.DumpUrl, async (_, token) =>
        {
            await release.Task.WaitAsync(token);
            return FakeHttpHandler.Bytes(_bed.LaunchBoxDump, "application/x-zip-compressed");
        });
        var database = Database();
        var started = 0;
        database.UpdateStarted += (_, _) => Interlocked.Increment(ref started);

        var first = database.UpdateAsync(force: false, Ct);
        var second = database.UpdateAsync(force: true, Ct);
        Assert.True(database.Updating);
        release.SetResult();

        Assert.Equal(LaunchBoxUpdateOutcome.Updated, await first);
        Assert.Equal(LaunchBoxUpdateOutcome.Updated, await second);
        Assert.Equal(1, started);
        Assert.Equal(1, DumpRequests);
    }

    // ---- Reading a game ----------------------------------------------------------------------------

    [Fact]
    public async Task Names_and_images_are_picked_by_ScreenScrapers_region_order()
    {
        var database = Database();
        await database.UpdateAsync(force: false, Ct);
        var saved = database.Load(2001)!;

        string? File(ScrapedGame game, string kind) =>
            game.MediaOrEmpty.SingleOrDefault(m => m.Kind == kind)?.Url[LaunchBoxScraper.ImageBaseUrl.Length..];

        // Europe first: its cover and spine; no European back, so World's (none), then the USA's.
        var europe = LaunchBoxScraper.Parse(saved, Settings("[\"eu\", \"wor\", \"us\", \"jp\"]"))!;
        Assert.Equal("2001", europe.ProviderGameId);
        Assert.Equal("Streets of Rage 2", europe.Title);                               // the main name ranks as World's
        Assert.Equal("sor2-front-eu.jpg", File(europe, MediaKinds.Cover));
        Assert.Equal("sor2-back-na.jpg", File(europe, MediaKinds.Back));
        Assert.Equal("sor2-spine-eu.jpg", File(europe, MediaKinds.Spine));
        Assert.Equal("sor2-logo.png", File(europe, MediaKinds.Logo));
        Assert.Equal("sor2-play.png", File(europe, MediaKinds.Screenshot));           // gameplay before the title screen
        Assert.Equal("sor2-fanart.jpg", File(europe, MediaKinds.Hero));
        Assert.Equal("sor2-cart-jp.png", File(europe, MediaKinds.Label));             // the only one, whatever its region
        Assert.Equal("Europe", europe.MediaOrEmpty.Single(m => m.Kind == MediaKinds.Cover).Region);

        // Japan first: the Japanese name and box.
        var japan = LaunchBoxScraper.Parse(saved, Settings("[\"jp\"]"))!;
        Assert.Equal("Bare Knuckle II: Shitou e no Requiem", japan.Title);
        Assert.Equal("sor2-front-jp.jpg", File(japan, MediaKinds.Cover));
        Assert.Equal("sor2-back-jp.jpg", File(japan, MediaKinds.Back));

        // The USA first: "United States" counts as the USA too, and the fallback order (World first) ranks the rest.
        var usa = LaunchBoxScraper.Parse(saved, Settings("[\"us\"]"))!;
        Assert.Equal("sor2-front-na.jpg", File(usa, MediaKinds.Cover));
        Assert.Equal("Streets of Rage 2", usa.Title);

        Assert.Equal("1992-12-20", europe.ReleaseDate);
        Assert.Equal("Mr. X is back, and he has kidnapped Adam.", europe.Description);
        Assert.Equal("Sega, Ancient", europe.Developer);
        Assert.Equal("Sega", europe.Publisher);
        Assert.Equal("Beat 'em Up, Action", europe.Genre);
        Assert.Equal("1-2", europe.Players);
        Assert.Equal(0.9, europe.Rating!.Value, 3);
    }

    [Fact]
    public async Task A_game_with_no_front_box_takes_the_next_cover_type_and_its_year_alone()
    {
        var database = Database();
        await database.UpdateAsync(force: false, Ct);

        var gunstar = LaunchBoxScraper.Parse(database.Load(2002)!, Settings("[\"us\"]"))!;

        Assert.Equal(LaunchBoxScraper.ImageBaseUrl + "gunstar-front-rebuilt-eu.jpg", gunstar.MediaOrEmpty.Single(m => m.Kind == MediaKinds.Cover).Url);
        Assert.Equal("1993", gunstar.ReleaseDate);
        Assert.Equal("1", gunstar.Players);
        Assert.Null(gunstar.Rating);
        Assert.False(gunstar.Has(MetadataField.Rating));
    }

    // ---- In a scrape -------------------------------------------------------------------------------

    [Fact]
    public async Task LaunchBox_fills_what_ScreenScraper_has_not_got_and_is_downloaded_on_first_use()
    {
        _bed.Rom(Sor2);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var result = await service.ScrapeGameAsync(Key(Sor2), Ct);

        Assert.True((1, 0) == (result.Done, result.Failed), string.Join(" | ", _bed.Log.Lines));
        var game = await _bed.Game("megadrive", "Streets of Rage 2 (USA).md");
        Assert.Equal("Streets of Rage 2", game.Title);
        Assert.Equal("launchbox", game.Metadata!.Source);
        Assert.Equal("1992-12-20", game.Metadata.ReleaseDate);
        foreach (var kind in (string[])[MediaKinds.Cover, MediaKinds.Back, MediaKinds.Spine, MediaKinds.Logo, MediaKinds.Label])
        {
            Assert.Equal("launchbox", _bed.SuppliedBy(Key(Sor2), kind));
        }

        Assert.Equal("search", _bed.Query<string>("SELECT method FROM scraper_matches WHERE scraper = 'launchbox'"));
        Assert.Equal("2001", _bed.Query<string>("SELECT scraper_game_id FROM scraper_matches WHERE scraper = 'launchbox'"));
        Assert.Equal(1, _bed.Http.Count("images.launchbox-app.com/sor2-front-eu.jpg"));  // the bed's regions start with Europe
        Assert.Equal(1, DumpRequests);
        Assert.True(service.LaunchBox!.IsReady);
    }

    [Fact]
    public async Task A_file_LaunchBox_lists_under_another_name_or_a_MAME_set_is_matched_by_its_file()
    {
        _bed.Rom("megadrive/SOR2_v1.1.md");
        _bed.Rom("arcade/pacman.zip");
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeAllMissingAsync(Ct);

        Assert.Equal("Streets of Rage 2", (await _bed.Game("megadrive", "SOR2_v1.1.md")).Title);
        Assert.Equal("Pac-Man", (await _bed.Game("arcade", "pacman.zip")).Title);
        Assert.Equal("1980-05-22", (await _bed.Game("arcade", "pacman.zip")).Metadata!.ReleaseDate);
        Assert.Equal(2L, _bed.Query<long>("SELECT COUNT(*) FROM scraper_matches WHERE scraper = 'launchbox' AND method = 'filename'"));
    }

    [Fact]
    public async Task Only_the_systems_LaunchBox_platforms_are_searched()
    {
        _bed.Rom("megadrive/Comix Zone (USA).md");                                     // LaunchBox has it on the SNES only
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await service.ScrapeGameAsync(Key("megadrive/Comix Zone (USA).md"), Ct);

        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM scraper_matches WHERE scraper = 'launchbox'"));
        var tic80 = _bed.Config.FindSystem("tic80")!;
        Assert.Contains("launchbox_platforms", service.Scrapers["launchbox"].Unsupported(tic80), StringComparison.Ordinal);
        Assert.Null(service.Scrapers["launchbox"].Unsupported(_bed.Config.FindSystem("megadrive")!));
    }

    [Fact]
    public async Task With_no_credentials_at_all_LaunchBox_still_scrapes()
    {
        _bed.Rom(Sor2);
        await _bed.ScanAsync();
        using var service = _bed.Service(ProviderAccounts.None);

        var result = await service.ScrapeAllMissingAsync(Ct);

        Assert.Equal(1, result.Done);
        Assert.Equal("Streets of Rage 2", (await _bed.Game("megadrive", "Streets of Rage 2 (USA).md")).Title);
        Assert.Contains(result.Notices, n => n.Provider == "screenscraper" && n.State == ProviderState.MissingCredentials);
    }

    [Fact]
    public async Task With_no_copy_and_no_download_LaunchBox_rests_and_the_others_carry_on()
    {
        _bed.Http.On("GET", u => u.AbsoluteUri == LaunchBoxDatabase.DumpUrl, _ => FakeHttpHandler.Text("no", HttpStatusCode.NotFound));
        _bed.Rom("megadrive/Sonic the Hedgehog 3 (Europe).md");
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var result = await service.ScrapeAllMissingAsync(Ct);

        Assert.Equal((1, 0), (result.Done, result.Failed));
        Assert.Equal("Sonic the Hedgehog 3", (await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md")).Title);
        var resting = Assert.Single(result.Notices, n => n.Provider == "launchbox");
        Assert.Equal(ProviderState.Resting, resting.State);
        Assert.Contains("couldn't be downloaded", resting.Message, StringComparison.Ordinal);
        Assert.Equal(1, DumpRequests);                                                 // a refusal isn't retried
    }

    [Fact]
    public async Task A_manual_search_lists_the_files_match_first_then_names_holding_the_search()
    {
        _bed.Rom("megadrive/SOR2_v1.1.md");
        await _bed.ScanAsync();
        using var service = _bed.Service();
        await service.LaunchBox!.UpdateAsync(force: false, Ct);

        var search = (await service.SearchMatchesAsync(Key("megadrive/SOR2_v1.1.md"), "streets of rage", Ct))!;

        var launchBox = search.Providers.Single(p => p.Provider == "launchbox");
        Assert.Null(launchBox.Problem);
        Assert.Equal(["2003", "2001"], launchBox.Candidates.Select(c => c.ProviderGameId));
        Assert.Equal("1992", launchBox.Candidates[1].Year);
        Assert.Equal(LaunchBoxScraper.ImageBaseUrl + "sor2-front-eu.jpg", launchBox.Candidates[1].Cover!.Candidate.Cover!.Url);

        var byFile = (await service.SearchMatchesAsync(Key("megadrive/SOR2_v1.1.md"), null, Ct))!.Providers.Single(p => p.Provider == "launchbox");
        Assert.Equal(("2001", MatchMethods.Filename), (byFile.Candidates[0].ProviderGameId, byFile.Candidates[0].MatchedBy));
    }

    [Fact]
    public async Task The_connection_test_asks_for_the_dump_and_describes_the_copy()
    {
        using var service = _bed.Service(ProviderAccounts.None);

        var before = await service.TestConnectionAsync("launchbox", Ct);
        await service.LaunchBox!.UpdateAsync(force: false, Ct);
        var after = await service.TestConnectionAsync("launchbox", Ct);

        Assert.True(before.Succeeded, before.Message);
        Assert.Contains("first time", before.Message, StringComparison.Ordinal);
        Assert.Contains("5 games", after.Message, StringComparison.Ordinal);
        Assert.Equal(2, _bed.Http.Requests.Count(r => r.Method == "HEAD"));
    }

    [Fact]
    public async Task A_saved_response_is_read_again_as_the_scrape_read_it()
    {
        var database = Database();
        await database.UpdateAsync(force: false, Ct);
        var settings = Settings("[\"jp\"]");
        var megadrive = _bed.Config.FindSystem("megadrive")!;

        var saved = new SavedScrape(ScraperIds.LaunchBox, Key(Sor2), "ok", "2001", MatchMethods.Search, 0, [], database.Load(2001));
        var restored = ScrapedResponses.Parse(saved, settings, megadrive);

        Assert.Equal("Bare Knuckle II: Shitou e no Requiem", restored!.Title);
        Assert.Same(LaunchBoxScraper.Supplies, ScrapedRestore.CapabilitiesOf(ScraperIds.LaunchBox));
    }
}
