using System.Net;
using Launcher.Core.Library;
using Launcher.Core.Scraping;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Scraping;

/// <summary>M7: the settings screen's "test connection" per provider, and "scrape all missing"'s count before it starts.</summary>
public sealed class ConnectionTestTests : IAsyncLifetime
{
    private ScrapeBed _bed = null!;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    public async ValueTask InitializeAsync() => _bed = await ScrapeBed.CreateAsync();

    public async ValueTask DisposeAsync()
    {
        Assert.Empty(_bed.Http.Unmatched);
        await _bed.DisposeAsync();
    }

    [Fact]
    public async Task Each_provider_accepts_good_credentials_with_one_cheap_request()
    {
        using var service = _bed.Service();

        var screenScraper = await service.TestConnectionAsync(ScraperIds.ScreenScraper, Ct);
        var igdb = await service.TestConnectionAsync(ScraperIds.Igdb, Ct);
        var steamGridDb = await service.TestConnectionAsync(ScraperIds.SteamGridDb, Ct);

        Assert.True(screenScraper.Succeeded, screenScraper.Message);
        Assert.Equal("Signed in to ScreenScraper: 10 of 20,000 requests used today, up to 2 at once.", screenScraper.Message);
        Assert.True(igdb.Succeeded, igdb.Message);
        Assert.True(steamGridDb.Succeeded, steamGridDb.Message);
        Assert.Equal(1, _bed.Http.Count("ssuserInfos.php"));
        Assert.Equal(1, _bed.Http.Count("id.twitch.tv"));
        Assert.Equal(1, _bed.Http.Count("api.igdb.com"));
        Assert.Equal(1, _bed.Http.Count("steamgriddb.com"));
        AssertNoCredentials(screenScraper, igdb, steamGridDb);
    }

    [Fact]
    public async Task ScreenScraper_without_an_account_checks_the_developer_credentials_alone()
    {
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "ssinfraInfos.php"),
            _ => FakeHttpHandler.Json(_bed.Fill("ss_ssinfrainfos.json").Replace("{{CLOSED}}", "1", StringComparison.Ordinal)));
        var accounts = ProviderAccounts.FromValues(new Dictionary<string, string>
        {
            ["screenscraper.dev_id"] = ScrapeBed.DevId,
            ["screenscraper.dev_password"] = ScrapeBed.DevPassword,
        });
        using var service = _bed.Service(accounts);

        var result = await service.TestConnectionAsync(ScraperIds.ScreenScraper, Ct);

        Assert.True(result.Succeeded, result.Message);
        Assert.Contains("anonymous limits apply", result.Message, StringComparison.Ordinal);
        Assert.Contains("closed to anonymous users right now", result.Message, StringComparison.Ordinal);
        Assert.Equal(0, _bed.Http.Count("ssuserInfos.php"));
        AssertNoCredentials(result);
    }

    [Fact]
    public async Task Refused_credentials_and_missing_ones_say_what_to_fix()
    {
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "steamgriddb.com", "/api/v2/search/autocomplete/"),
            _ => FakeHttpHandler.Json("""{"success":false,"errors":["Unauthorized"]}""", HttpStatusCode.Unauthorized));
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "screenscraper.fr", "ssuserInfos.php"),
            _ => FakeHttpHandler.Text("Erreur de login : Vérifier vos identifiants !", HttpStatusCode.OK));
        using var service = _bed.Service(ScrapeBed.Accounts(igdb: false));

        var steamGridDb = await service.TestConnectionAsync(ScraperIds.SteamGridDb, Ct);
        var screenScraper = await service.TestConnectionAsync(ScraperIds.ScreenScraper, Ct);
        var igdb = await service.TestConnectionAsync(ScraperIds.Igdb, Ct);

        Assert.False(steamGridDb.Succeeded);
        Assert.Contains("SteamGridDB refused the API key", steamGridDb.Message, StringComparison.Ordinal);
        Assert.False(screenScraper.Succeeded);
        Assert.Contains("refused the username or password", screenScraper.Message, StringComparison.Ordinal);
        Assert.False(igdb.Succeeded);
        Assert.Contains("client_id and client_secret", igdb.Message, StringComparison.Ordinal);
        Assert.Equal(0, _bed.Http.Count("id.twitch.tv"));
        AssertNoCredentials(steamGridDb, screenScraper, igdb);
    }

    [Fact]
    public async Task A_provider_that_doesnt_answer_is_reported_without_hanging()
    {
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "steamgriddb.com", "/api/v2/search/autocomplete/"),
            _ => FakeHttpHandler.Text("busy", HttpStatusCode.ServiceUnavailable));
        using var service = _bed.Service();

        var result = await service.TestConnectionAsync(ScraperIds.SteamGridDb, Ct);

        Assert.False(result.Succeeded);
        Assert.Contains("server error (HTTP 503)", result.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task The_steam_store_needs_no_credentials_and_is_tested_with_one_search()
    {
        using var service = _bed.Service(ScrapeBed.Accounts(screenScraper: false, igdb: false, steamGridDb: false));

        var ok = await service.TestConnectionAsync(ScraperIds.Steam, Ct);
        _bed.Http.On("GET", u => ScrapeBed.Is(u, "api.steampowered.com", "/IStoreQueryService/SearchSuggestions/"),
            _ => FakeHttpHandler.Text("busy", HttpStatusCode.ServiceUnavailable));
        var busy = await service.TestConnectionAsync(ScraperIds.Steam, Ct);

        Assert.True(ok.Succeeded, ok.Message);
        Assert.Equal("The Steam store answered.", ok.Message);
        Assert.False(busy.Succeeded);
        Assert.Contains("server error (HTTP 503)", busy.Message, StringComparison.Ordinal);
        var first = _bed.Http.Requests.First();
        Assert.Contains("\"search_term\":\"Portal 2\"", ScrapeBed.SteamInput(first), StringComparison.Ordinal);
        Assert.DoesNotContain("data_request", ScrapeBed.SteamInput(first), StringComparison.Ordinal);   // the ids alone
        Assert.Contains(service.GetProviders(), p => p.Id == ScraperIds.Steam && p.State == ProviderState.Ready);
    }

    [Fact]
    public async Task Scrape_all_missing_counts_its_games_per_system_before_it_starts()
    {
        _bed.Rom("megadrive/Sonic the Hedgehog 3 (Europe).md");
        _bed.Rom("megadrive/Ecco the Dolphin (USA, Europe).md");
        _bed.Rom("snes/Super Metroid (Japan, USA).sfc");
        await _bed.ScanAsync();
        using var service = _bed.Service();

        var before = await service.CountMissingAsync(Ct);
        Assert.Equal(3, before.Games);
        Assert.Equal([("snes", 1), ("megadrive", 2)], before.Systems.OrderByDescending(s => s.SystemId).ToList());

        await service.ScrapeGameAsync(new GameKey("megadrive", "sonic the hedgehog 3 (europe).md"), Ct);

        var after = await service.CountMissingAsync(Ct);
        Assert.Equal(2, after.Games);
    }

    private static void AssertNoCredentials(params ConnectionTestResult[] results)
    {
        foreach (var result in results)
        {
            foreach (var credential in ScrapeBed.AllCredentials)
            {
                Assert.DoesNotContain(credential, result.Message, StringComparison.Ordinal);
            }
        }
    }
}
