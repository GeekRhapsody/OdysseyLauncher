using System.Net;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Scraping;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Scraping;

/// <summary>Manual matching: "scrape this game" searches every provider, and scrapes with the result the user chose.</summary>
public sealed class ManualMatchTests : IAsyncLifetime
{
    private const string Sonic = "megadrive/Sonic the Hedgehog 3 (Europe).md";
    private const string Odd = "megadrive/Zz Unknown Prototype.md";

    private ScrapeBed _bed = null!;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private static GameKey Key(string relPath) => new(relPath.Split('/')[0], relPath[(relPath.IndexOf('/') + 1)..].ToLowerInvariant());

    public async ValueTask InitializeAsync()
    {
        _bed = await ScrapeBed.CreateAsync("media = [\"cover\", \"label\", \"spine\"]");

        // ScreenScraper's search finds Sonic 3 and Sonic & Knuckles.
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuRecherche.php"), r =>
            (r.Query("recherche") ?? string.Empty).Contains("Sonic", StringComparison.Ordinal)
                ? FakeHttpHandler.Json(_bed.Fill("ss_jeurecherche.json"))
                : FakeHttpHandler.Json(_bed.Fill("ss_jeurecherche_empty.json")));
    }

    public async ValueTask DisposeAsync()
    {
        Assert.Empty(_bed.Http.Unmatched);
        await _bed.DisposeAsync();
    }


    // ---- Searching ---------------------------------------------------------------------------------

    [Fact]
    public async Task A_search_asks_every_provider_at_once_and_ranks_each_ones_results_by_name()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var search = (await service.SearchMatchesAsync(Key(Sonic), null, Ct))!;

        Assert.Equal("Sonic the Hedgehog 3", search.Term);                      // the file name's title, without its tags
        Assert.Equal(["screenscraper", "igdb", "steamgriddb", "steam"], search.Providers.Select(p => p.Provider));
        var ss = search.Providers[0];
        Assert.Null(ss.Problem);
        Assert.True(ss.InOrder);
        Assert.Equal(["1187", "1190"], ss.Candidates.Select(c => c.ProviderGameId));
        Assert.Equal("Sonic & Knuckles", ss.Candidates[1].Name);              // HTML entities decoded
        Assert.Equal(1.0, ss.Candidates[0].Similarity, 3);
        Assert.Equal(["1234", "99"], search.Providers[1].Candidates.Select(c => c.ProviderGameId));
        Assert.Equal("1994", search.Providers[1].Candidates[0].Year);

        // SteamGridDB lists Sonic 3 & Knuckles first; the closer name comes first here.
        Assert.Equal(["5170", "1"], search.Providers[2].Candidates.Select(c => c.ProviderGameId));

        // The Steam store isn't in the order, and has nothing for a Mega Drive game: it says why.
        var steam = search.Providers[3];
        Assert.False(steam.InOrder);
        Assert.Empty(steam.Candidates);
        Assert.Contains("steam_store", steam.Problem, StringComparison.Ordinal);

        // ScreenScraper's ROM index was asked for the file too, and knows it as the same game: it's listed once, first,
        // as the file's match. The other providers have no ROM index.
        var lookup = Assert.Single(_bed.Http.Requests, r => r.Uri.AbsolutePath.EndsWith("jeuInfos.php", StringComparison.Ordinal));
        Assert.Equal(("Sonic the Hedgehog 3 (Europe).md", null), (lookup.Query("romnom"), lookup.Query("gameid")));
        Assert.Equal([MatchMethods.Hash, null], ss.Candidates.Select(c => c.MatchedBy));
        Assert.All(search.Providers.Skip(1), p => Assert.All(p.Candidates, c => Assert.Null(c.MatchedBy)));

        // Searches only: nothing fetched, downloaded or written.
        Assert.Equal(0, _bed.Http.Count("steamgriddb.com/api/v2/grids"));
        Assert.Null((await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md")).Scrape);
        Assert.All(search.Providers, p => Assert.Null(p.Current));
    }

    [Fact]
    public async Task The_users_title_is_searched_by_default_a_typed_name_replaces_it_and_the_current_match_is_reported()
    {
        _bed.Rom(Odd);
        await _bed.ScanAsync();
        await _bed.Library.SetTitleOverrideAsync(Key(Odd), "Sonic the Hedgehog 3 (Disc 1)", Ct);
        _bed.Execute("INSERT INTO manual_matches VALUES ('megadrive', 'zz unknown prototype.md', 'igdb', '1234', 1)");
        using var service = _bed.Service();

        var search = (await service.SearchMatchesAsync(Key(Odd), null, Ct))!;

        Assert.Equal("Sonic the Hedgehog 3", search.Term);
        var igdb = search.Providers.Single(p => p.Provider == "igdb");
        Assert.Equal("1234", igdb.Current);
        Assert.True(igdb.CurrentIsManual);
        Assert.Null(search.Providers[0].Current);

        // The first search asked ScreenScraper's ROM index for the file, which doesn't know it. A typed name is only
        // searched for.
        Assert.Equal(1, _bed.Http.Count("jeuInfos.php"));
        var typed = (await service.SearchMatchesAsync(Key(Odd), "  Ecco  ", Ct))!;
        Assert.Equal(1, _bed.Http.Count("jeuInfos.php"));
        Assert.Equal("Ecco", typed.Term);
        Assert.Contains(_bed.Http.Requests, r => r.Query("recherche") == "Ecco");
        Assert.All(typed.Providers.Take(3), p => Assert.Empty(p.Candidates));

        var empty = (await service.SearchMatchesAsync(Key(Odd), " ", Ct))!;
        Assert.All(empty.Providers, p => Assert.NotNull(p.Problem));
        Assert.Null(await service.SearchMatchesAsync(new GameKey("megadrive", "not a game.md"), null, Ct));
    }

    [Fact]
    public async Task An_arcade_set_is_found_by_its_MAME_short_name_which_the_title_search_cant_find()
    {
        const string Arcade = "arcade/3kokushi.zip";
        _bed.Rom(Arcade);
        await _bed.ScanAsync();

        // ScreenScraper's ROM index knows the set by its file name (its hash differs); its title search has nothing
        // for "3kokushi".
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php") && u.Query.Contains("romnom=3kokushi.zip", StringComparison.Ordinal),
            _ => FakeHttpHandler.Json(_bed.Fill("ss_jeuinfos.json")));
        using var service = _bed.Service();

        var search = (await service.SearchMatchesAsync(Key(Arcade), null, Ct))!;

        Assert.Equal("3kokushi", search.Term);
        Assert.Contains(_bed.Http.Requests, r => r.Query("recherche") == "3kokushi");
        var hit = Assert.Single(search.Providers[0].Candidates);
        Assert.Equal(("1187", "Sonic the Hedgehog 3", MatchMethods.Filename), (hit.ProviderGameId, hit.Name, hit.MatchedBy));
        var lookup = Assert.Single(_bed.Http.Requests, r => r.Query("romnom") is not null);
        Assert.Equal(("75", "rom"), (lookup.Query("systemeid"), lookup.Query("romtype")));
        Assert.NotNull(lookup.Query("crc"));                                          // hashed, as a scrape would
        Assert.All(search.Providers.Skip(1), p => Assert.Empty(p.Candidates));

        // Choosing it scrapes the game with it.
        await service.ScrapeGameWithMatchAsync(Key(Arcade), "screenscraper", hit.ProviderGameId, Ct);
        Assert.Equal("Sonic the Hedgehog 3", (await _bed.Game("arcade", "3kokushi.zip")).Title);
    }

    [Fact]
    public async Task A_provider_without_credentials_or_whose_search_fails_says_why_and_the_others_still_answer()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "steamgriddb.com", "/api/v2/search/autocomplete/"),
            _ => FakeHttpHandler.Text("down", HttpStatusCode.BadGateway));
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false));

        var search = (await service.SearchMatchesAsync(Key(Sonic), null, Ct))!;

        Assert.Equal(2, search.Providers[0].Candidates.Count);
        Assert.Contains("client_id", search.Providers[1].Problem, StringComparison.Ordinal);
        Assert.Contains("HTTP 502", search.Providers[2].Problem, StringComparison.Ordinal);
        Assert.Empty(search.Providers[2].Candidates);
        Assert.Equal(0, _bed.Http.Count("igdb"));
        Assert.All(search.Providers, p => Assert.DoesNotContain(ScrapeBed.SgdbKey, p.Problem ?? string.Empty, StringComparison.Ordinal));
    }

    // ---- Scraping with the chosen match ------------------------------------------------------------

    [Fact]
    public async Task The_chosen_result_is_fetched_by_id_saved_as_a_manual_match_and_survives_a_rebuild()
    {
        _bed.Rom(Odd);
        await _bed.ScanAsync();
        using var service = _bed.Service(saveResponses: true);

        var result = await service.ScrapeGameWithMatchAsync(Key(Odd), "screenscraper", "1187", Ct);

        Assert.True((ScrapeService.ManualKind, 1, 1, 0) == (result.Kind, result.Total, result.Done, result.Failed), string.Join(" | ", _bed.Log.Lines));
        Assert.DoesNotContain(_bed.Http.Requests, r => r.Query("romnom") is not null);  // fetched by id, never looked up
        Assert.Contains(_bed.Http.Requests, r => r.Query("gameid") == "1187");
        Assert.Equal(0, _bed.Http.Count("igdb"));                                       // nothing was left for the fallbacks
        var game = await _bed.Game("megadrive", "Zz Unknown Prototype.md");
        Assert.Equal("Sonic the Hedgehog 3", game.Title);
        Assert.Equal("ok", game.Scrape!.Status);
        Assert.Equal("1187", _bed.Query<string>("SELECT scraper_game_id FROM user.manual_matches WHERE scraper = 'screenscraper'"));
        Assert.Equal("manual", _bed.Query<string>("SELECT method FROM scraper_matches WHERE scraper = 'screenscraper'"));
        Assert.Equal(3L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
        Assert.All((string[])["cover", "label", "spine"], kind => Assert.Equal("screenscraper", _bed.SuppliedBy(Key(Odd), kind)));

        _bed.Http.Offline = true;
        await _bed.Library.RebuildAsync(null, Ct);

        Assert.Equal("Sonic the Hedgehog 3", (await _bed.Game("megadrive", "Zz Unknown Prototype.md")).Title);
        Assert.Equal("manual", _bed.Query<string>("SELECT method FROM scraper_matches"));
    }

    [Fact]
    public async Task The_chosen_game_comes_first_the_others_fill_in_what_it_lacks_and_the_latest_choice_leads()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        var key = Key(Sonic);
        using var service = _bed.Service(saveResponses: true);
        await service.ScrapeGameAsync(key, Ct);                                         // ScreenScraper matches it by hash
        Assert.Equal("screenscraper", _bed.SuppliedBy(key, "cover"));
        var spine = File.ReadAllBytes(_bed.MediaFile(Sonic, "spine", ".png"));

        // The user deletes the cover and label to get them again.
        File.Delete(_bed.MediaFile(Sonic, "cover", ".png"));
        File.Delete(_bed.MediaFile(Sonic, "label", ".png"));
        await _bed.ScanAsync();

        // IGDB's game chosen: its cover and metadata win; ScreenScraper (its stored match) fills in the label. The
        // spine the game has stays: a scrape never replaces a file in the media folder.
        await service.ScrapeGameWithMatchAsync(key, "igdb", "1234", Ct);

        Assert.Contains(_bed.Http.Requests, r => (r.Body ?? string.Empty).Contains("where id = 1234;", StringComparison.Ordinal));
        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("IGDB summary of Sonic the Hedgehog 3.", game.Metadata!.Description);
        Assert.Equal(["igdb", "screenscraper"], game.Scrape!.Providers);
        Assert.Equal(("igdb", "screenscraper", null), (_bed.SuppliedBy(key, "cover"), _bed.SuppliedBy(key, "label"), _bed.SuppliedBy(key, "spine")));
        Assert.Equal(spine, File.ReadAllBytes(_bed.MediaFile(Sonic, "spine", ".png")));

        // A rebuild merges in the same order.
        _bed.Http.Offline = true;
        await _bed.Library.RebuildAsync(null, Ct);
        Assert.Equal("IGDB summary of Sonic the Hedgehog 3.", (await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md")).Metadata!.Description);
        Assert.Equal(3L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
        _bed.Http.Offline = false;

        // Choosing ScreenScraper's game later puts it first.
        _bed.Clock.Advance(TimeSpan.FromSeconds(1));
        await service.ScrapeGameWithMatchAsync(key, "screenscraper", "1187", Ct);

        game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("Sonic and Tails race to stop Dr. Robotnik's Death Egg.", game.Metadata!.Description);
        Assert.Equal(2L, _bed.Query<long>("SELECT COUNT(*) FROM user.manual_matches"));
    }

    [Fact]
    public async Task A_corrected_match_replaces_the_wrong_games_metadata_but_not_its_images()
    {
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php") && u.Query.Contains("gameid=5001", StringComparison.Ordinal),
            _ => FakeHttpHandler.Json(_bed.Fill("ss_jeuinfos_nocover.json")));
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        var key = Key(Sonic);
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false), saveResponses: true);
        await service.ScrapeGameAsync(key, Ct);
        Assert.Equal(3L, _bed.Query<long>("SELECT COUNT(*) FROM media"));

        // The right game (Ecco, here): its metadata and match replace the wrong game's. The media folder doesn't say
        // which files a provider brought (A4), so the images stay until the user removes them.
        await service.ScrapeGameWithMatchAsync(key, "screenscraper", "5001", Ct);

        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("Ecco the Dolphin", game.Title);
        Assert.Equal(3L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
        foreach (var kind in (string[])["cover", "label", "spine"])
        {
            Assert.True(File.Exists(_bed.MediaFile(Sonic, kind, ".png")), kind);
        }

        Assert.Equal("5001", _bed.Query<string>("SELECT scraper_game_id FROM scraper_matches"));
        Assert.Equal("5001", ScrapedResponses.Load(_bed.Paths.DataDir, "screenscraper", key)!.GameId);

        _bed.Http.Offline = true;
        await _bed.Library.RebuildAsync(null, Ct);
        Assert.Equal("Ecco the Dolphin", (await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md")).Title);
        Assert.Equal(3L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
    }

    [Fact]
    public async Task A_chosen_provider_that_fails_keeps_what_it_had()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        var key = Key(Sonic);
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false, steamGridDb: false));
        await service.ScrapeGameAsync(key, Ct);
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "jeuInfos.php"), _ => FakeHttpHandler.Text("down", HttpStatusCode.BadGateway));

        await service.ScrapeGameWithMatchAsync(key, "screenscraper", "1187", Ct);

        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("error", game.Scrape!.Status);
        Assert.Equal("screenscraper", game.Metadata!.Source);
        Assert.Equal(3L, _bed.Query<long>("SELECT COUNT(*) FROM media"));
        Assert.True(File.Exists(_bed.MediaFile(Sonic, "label", ".png")));
        Assert.Equal(1L, _bed.Query<long>("SELECT COUNT(*) FROM scraper_matches WHERE scraper = 'screenscraper'"));
    }

    [Fact]
    public async Task A_provider_outside_the_configured_order_is_used_first_when_its_result_is_chosen()
    {
        _bed.Reconfigure("fallback = []\nmedia = [\"cover\", \"hero\"]");
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        var key = Key(Sonic);
        using var service = _bed.Service();

        var search = (await service.SearchMatchesAsync(key, null, Ct))!;
        var sgdb = search.Providers.Single(p => p.Provider == "steamgriddb");
        Assert.False(sgdb.InOrder);
        Assert.Equal("5170", sgdb.Candidates[0].ProviderGameId);

        await service.ScrapeGameWithMatchAsync(key, "steamgriddb", "5170", Ct);

        // SteamGridDB's art first; ScreenScraper, in the order, still fills in the metadata SteamGridDB doesn't have.
        Assert.Equal("steamgriddb", _bed.SuppliedBy(key, "cover"));
        Assert.Equal("steamgriddb", _bed.SuppliedBy(key, "hero"));
        Assert.Equal("manual", _bed.Query<string>("SELECT method FROM scraper_matches WHERE scraper = 'steamgriddb'"));
        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        Assert.Equal("screenscraper", game.Metadata!.Source);
        Assert.Equal(["steamgriddb", "screenscraper"], game.Scrape!.Providers);
    }

    [Fact]
    public async Task A_choice_must_name_a_provider_and_a_game()
    {
        _bed.Rom(Sonic);
        await _bed.ScanAsync();
        using var service = _bed.Service();

        await Assert.ThrowsAsync<ArgumentException>(() => service.ScrapeGameWithMatchAsync(Key(Sonic), "thegamesdb", "1", Ct));
        await Assert.ThrowsAsync<ArgumentException>(() => service.ScrapeGameWithMatchAsync(Key(Sonic), "igdb", " ", Ct));
        Assert.Equal(0L, _bed.Query<long>("SELECT COUNT(*) FROM user.manual_matches"));
        Assert.Empty(_bed.Http.Requests);
    }
}
