using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Scanning;
using Launcher.Core.Scraping;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Scraping;

public sealed class ScraperUnitTests
{
    private static ScrapingSettings Settings(string scraping = "")
    {
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = "C:/home",
            ConfigDir = "C:/home/config",
            FileExists = null,
            Settings = new ConfigFile("settings.toml", "[scraping]\n" + scraping),
        });
        Assert.False(result.HasErrors, string.Join('\n', result.Diagnostics));
        return result.Config.Settings.Scraping;
    }

    private static SystemConfig MegaDrive() => new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/home", ConfigDir = "C:/c", FileExists = null })
        .Config.FindSystem("megadrive")!;

    // ---- Credentials -------------------------------------------------------------------------------

    [Fact]
    public void Credentials_come_from_secrets_toml_and_the_environment_overrides_each_value()
    {
        var text = """
            [screenscraper]
            dev_id = "file-dev"
            dev_password = "file-pass"

            [igdb]
            client_id = "file-client"
            client_secret = "file-secret"
            """;
        var environment = new Dictionary<string, string> { ["ODYSSEY_IGDB_CLIENT_SECRET"] = "env-secret", ["ODYSSEY_STEAMGRIDDB_API_KEY"] = "env-key" };

        var result = ProviderAccounts.Parse(text, "secrets.toml", name => environment.GetValueOrDefault(name));

        Assert.Empty(result.Diagnostics);
        var accounts = result.Accounts;
        Assert.Equal("file-dev", accounts.ScreenScraperDevId);
        Assert.Null(accounts.ScreenScraperUsername);
        Assert.Equal("file-client", accounts.IgdbClientId);
        Assert.Equal("env-secret", accounts.IgdbClientSecret);
        Assert.Equal("env-key", accounts.SteamGridDbApiKey);
        Assert.DoesNotContain("file-pass", accounts.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public void A_mistake_in_secrets_toml_is_reported_without_quoting_the_value()
    {
        var text = """
            [igdb]
            client_secret = 12345678
            client = "x"

            [steamgrid]
            api_key = "k"
            """;

        var result = ProviderAccounts.Parse(text, "secrets.toml", _ => null);

        Assert.Equal(3, result.Diagnostics.Count);
        Assert.Contains(result.Diagnostics, d => d.IsError && d.Key == "igdb.client_secret");
        Assert.All(result.Diagnostics, d => Assert.DoesNotContain("12345678", d.ToString(), StringComparison.Ordinal));
        Assert.Null(result.Accounts.IgdbClientSecret);
    }

    [Fact]
    public void A_syntax_error_in_secrets_toml_never_shows_the_text_it_choked_on()
    {
        var result = ProviderAccounts.Parse("[igdb]\nclient_secret = supersecretvalue123\n", "secrets.toml", _ => null);

        Assert.NotEmpty(result.Diagnostics);
        Assert.All(result.Diagnostics, d => Assert.DoesNotContain("supersecret", d.ToString(), StringComparison.Ordinal));
        Assert.Equal(2, result.Diagnostics[0].Line);
        Assert.Empty(result.Accounts.Values);
    }

    [Fact]
    public void A_missing_secrets_file_means_no_credentials()
    {
        using var dir = new TempDir();

        var result = ProviderAccounts.Load(dir.Path, _ => null);

        Assert.Empty(result.Diagnostics);
        Assert.Empty(result.Accounts.Values);
    }

    [Fact]
    public void The_redactor_masks_known_values_in_every_encoding_and_any_credential_parameter()
    {
        var redactor = new Redactor(["p@ss word!", "abc"]);

        var text = redactor.Redact(
            "https://x.fr/a?devid=someone&devpassword=p%40ss%20word%21&sspassword=unknown-value&media=box-2D(eu) " +
            "json: \"p@ss word!\" form: client_secret=zzz9 header: Authorization: Bearer abcdefghijkl1234 plain abc");

        Assert.DoesNotContain("p@ss", text, StringComparison.Ordinal);
        Assert.DoesNotContain("p%40ss", text, StringComparison.Ordinal);
        Assert.DoesNotContain("someone", text, StringComparison.Ordinal);
        Assert.DoesNotContain("unknown-value", text, StringComparison.Ordinal);
        Assert.DoesNotContain("zzz9", text, StringComparison.Ordinal);
        Assert.DoesNotContain("abcdefghijkl1234", text, StringComparison.Ordinal);
        Assert.Contains("media=box-2D(eu)", text, StringComparison.Ordinal);
        Assert.EndsWith("plain abc", text, StringComparison.Ordinal);                 // too short to mask safely
    }

    // ---- Names, JSON, hashes -----------------------------------------------------------------------

    [Theory]
    [InlineData("Sonic the Hedgehog 3", "Sonic The Hedgehog 3", 1.0)]
    [InlineData("Legend of Zelda, The - A Link to the Past", "The Legend of Zelda: A Link to the Past", 0.97)]
    [InlineData("Sonic & Knuckles", "Sonic and Knuckles", 1.0)]
    [InlineData("Pokemon Red", "Pokémon Red", 1.0)]
    [InlineData("Castlevania", "Castlevania: Symphony of the Night", 0.9)]
    [InlineData("Sonic the Hedgehog 3", "Sonic Mania", 0.0)]
    public void Title_similarity_ignores_case_accents_punctuation_and_articles(string title, string candidate, double atLeast)
    {
        var score = TitleMatcher.Similarity(title, candidate);

        if (atLeast == 0)
        {
            Assert.True(score < TitleMatcher.Threshold, $"{score}");
        }
        else
        {
            Assert.True(score >= Math.Min(atLeast, TitleMatcher.Threshold), $"{score}");
        }
    }

    [Theory]
    [InlineData("Final Fantasy VII (Disc 1)", "Final Fantasy VII")]
    [InlineData("Metal Gear Solid (Disc 2 of 2)", "Metal Gear Solid")]
    [InlineData("Discworld", "Discworld")]
    public void The_search_term_drops_the_disc_number(string title, string term) =>
        Assert.Equal(term, TitleMatcher.SearchTerm(title));

    [Fact]
    public void Lenient_JSON_repairs_stray_backslashes_and_trailing_commas_without_breaking_valid_escapes()
    {
        using var document = LenientJson.Parse("""{"path":"C:\Games\x","ok":"a\\b\n","list":[1,2,],}""");

        Assert.NotNull(document);
        Assert.Equal(@"C:\Games\x", document.RootElement.Str("path"));
        Assert.Equal("a\\b\n", document.RootElement.Str("ok"));
        Assert.Null(LenientJson.Parse("Erreur : Jeu non trouvée !"));
    }

    [Fact]
    public void ROM_hashes_are_the_standard_checksums_in_upper_case()
    {
        using var dir = new TempDir();
        var path = dir.File("rom.bin", "abc");

        var hashes = RomHasher.Compute(path, CancellationToken.None);

        Assert.Equal(0xCBF43926u, RomHasher.Crc32("123456789"u8));
        Assert.Equal("352441C2", hashes.Crc32);
        Assert.Equal("900150983CD24FB0D6963F7D28E17F72", hashes.Md5);
        Assert.Equal("A9993E364706816ABA3E25717850C26C9CD0D89D", hashes.Sha1);
        Assert.False(RomHasher.IsHashable("Game (Disc 1).cue"));
        Assert.True(RomHasher.IsHashable("Game.md"));
    }

    // ---- Parsers -----------------------------------------------------------------------------------

    [Fact]
    public void ScreenScraper_picks_the_wanted_region_and_language_and_decodes_entities()
    {
        var response = ScrapeBed.Fixture("ss_jeuinfos.json");

        var game = ScreenScraperScraper.Parse(response, Settings("regions = [\"jp\"]\nlanguages = [\"fr\"]"))!;

        Assert.Equal("1187", game.ProviderGameId);
        Assert.Equal("Sonic 3", game.Title);
        Assert.Equal("1994-05-27", game.ReleaseDate);
        Assert.Equal("Texte en français.", game.Description);
        Assert.Equal("Plateforme", game.Genre);
        Assert.Equal(0.8, game.Rating!.Value, 3);
        var kinds = game.MediaOrEmpty.Select(m => m.Kind).ToList();
        Assert.Equal(["cover", "spine", "box_texture", "screenshot"], kinds.Order().Select(k => k).OrderBy(k => Array.IndexOf(new[] { "cover", "spine", "box_texture", "screenshot" }, k)));
        Assert.DoesNotContain(game.MediaOrEmpty, m => m.Url.Contains("mediaGroup", StringComparison.Ordinal));   // the publisher's logo isn't the game's
    }

    [Fact]
    public void ScreenScraper_ignores_entries_that_arent_games()
    {
        var response = ScrapeBed.Fixture("ss_jeuinfos.json").Replace("\"notgame\": \"false\"", "\"notgame\": \"true\"", StringComparison.Ordinal);

        Assert.Null(ScreenScraperScraper.Parse(response, Settings()));
    }

    [Fact]
    public void IGDB_dates_keep_their_precision_and_players_and_rating_are_normalised()
    {
        var system = MegaDrive();

        var sonic = IgdbScraper.Parse(ScrapeBed.Fixture("igdb_games.json"), Settings("regions = [\"us\"]"), system)!;
        var ecco = IgdbScraper.Parse(ScrapeBed.Fixture("igdb_games_ecco.json"), Settings(), system)!;
        var bare = IgdbScraper.Parse("""[{"id":5,"name":"X","first_release_date":760060800}]""", Settings(), system)!;

        Assert.Equal("1994-02-02", sonic.ReleaseDate);      // the us release, a full date
        Assert.Equal("1-2", sonic.Players);                 // the Mega Drive's mode, not the PC's 4
        Assert.Equal("Sonic Team", sonic.Developer);
        Assert.Equal("Sega", sonic.Publisher);
        Assert.Equal(0.845, sonic.Rating!.Value, 3);
        Assert.Equal("https://images.igdb.com/igdb/image/upload/t_1080p/co1abc.jpg", sonic.MediaOrEmpty.Single(m => m.Kind == "cover").Url);
        Assert.Equal("1992", ecco.ReleaseDate);             // year only, as IGDB knows it
        Assert.Equal("1", ecco.Players);
        Assert.Equal(0.7, ecco.Rating!.Value, 3);            // the critics' rating when there's no total
        Assert.Equal("1994-02-01", bare.ReleaseDate);          // first_release_date, 760060800 s
    }

    [Fact]
    public void SteamGridDB_prefers_a_case_shaped_grid_for_the_cover()
    {
        var saved = $$"""{"id":"5170","cover":{{Data("sgdb_grids.json")}},"hero":{{Data("sgdb_heroes.json")}},"logo":{{Data("sgdb_logos.json")}}}""";

        var game = SteamGridDbScraper.Parse(saved)!;

        Assert.Equal("https://cdn2.steamgriddb.com/grid/b660.png", game.MediaOrEmpty.Single(m => m.Kind == "cover").Url);
        Assert.Equal("https://cdn2.steamgriddb.com/hero/h1.png", game.MediaOrEmpty.Single(m => m.Kind == "hero").Url);
        Assert.Equal("https://cdn2.steamgriddb.com/logo/l1.png", game.MediaOrEmpty.Single(m => m.Kind == "logo").Url);
        Assert.Null(game.Title);

        static string Data(string fixture)
        {
            using var document = System.Text.Json.JsonDocument.Parse(ScrapeBed.Fixture(fixture));
            return document.RootElement.GetProperty("data").GetRawText();
        }
    }

    // ---- Selection and limits ----------------------------------------------------------------------

    [Fact]
    public void Merging_takes_each_field_from_the_first_provider_that_can_supply_it()
    {
        var merge = new ScrapeMerge(new HashSet<string>(["cover", "hero"]));
        merge.Add("screenscraper", new ScrapedGame("1", Title: "A", Developer: "Dev", Media: [new ScrapedMedia("hero", "h")]), ScreenScraperScraper.Supplies);

        Assert.True(merge.CouldUse(IgdbScraper.Supplies));                         // description, cover...
        Assert.True(merge.CouldUse(SteamGridDbScraper.Supplies));                  // the cover
        merge.Add("igdb", new ScrapedGame("2", Title: "B", Description: "D", Developer: "Other", Media: [new ScrapedMedia("cover", "c")]), IgdbScraper.Supplies);
        Assert.False(merge.CouldUse(SteamGridDbScraper.Supplies));                 // nothing it has is missing

        var metadata = merge.Metadata();
        Assert.Equal(("A", "D", "Dev"), (metadata.Title, metadata.Description, metadata.Developer));
        Assert.Equal(["screenscraper", "igdb"], metadata.Sources);
        Assert.Equal("igdb", merge.MediaCandidates()["cover"].Single().Provider);
    }

    [Fact]
    public async Task The_gate_keeps_to_its_concurrency_and_per_minute_limits_and_pauses()
    {
        var clock = new SteppingClock(DateTimeOffset.UnixEpoch);
        var waits = new List<TimeSpan>();
        var gate = new ProviderGate("test", 2, null, 3, clock, (d, _) =>
        {
            lock (waits)
            {
                waits.Add(d);
            }

            clock.Advance(d);
            return Task.CompletedTask;
        });

        var first = await gate.EnterAsync(CancellationToken.None);
        var second = await gate.EnterAsync(CancellationToken.None);
        var third = gate.EnterAsync(CancellationToken.None);
        Assert.False(third.IsCompleted);                                           // two in flight
        first.Dispose();
        (await third).Dispose();
        second.Dispose();

        // The fourth start in a minute waits for the first to be a minute old.
        (await gate.EnterAsync(CancellationToken.None)).Dispose();
        Assert.Contains(TimeSpan.FromMinutes(1), waits);

        gate.PauseUntil(clock.GetUtcNow().AddSeconds(30));
        gate.SetLimits(2, null);
        (await gate.EnterAsync(CancellationToken.None)).Dispose();
        Assert.Equal(TimeSpan.FromSeconds(30), waits[^1]);
        Assert.Equal(2, gate.PeakInFlight);

        gate.Close(new ProviderException("test", ProviderFailure.QuotaExhausted, "used up", clock.GetUtcNow().AddHours(1)));
        await Assert.ThrowsAsync<ProviderException>(() => gate.EnterAsync(CancellationToken.None));
        clock.Advance(TimeSpan.FromHours(2));
        (await gate.EnterAsync(CancellationToken.None)).Dispose();                 // open again after the reset
    }

    // ---- Config ------------------------------------------------------------------------------------

    [Fact]
    public void Scraping_settings_default_to_screenscraper_then_igdb_then_steamgriddb()
    {
        var settings = Settings();
        var systems = new ConfigLoader().Load(new ConfigSources { HomeDir = "C:/h", ConfigDir = "C:/c", FileExists = null }).Config;

        Assert.Equal(["screenscraper", "igdb", "steamgriddb"], settings.ProviderOrder);
        Assert.Equal(["cover", "box_texture"], settings.Media);
        Assert.Equal(64L * 1024 * 1024, settings.HashLimitBytes);
        Assert.Equal([18, 99], systems.FindSystem("nes")!.IgdbPlatforms);
        Assert.Equal([29], systems.FindSystem("megadrive")!.IgdbPlatforms);
        Assert.All(systems.Systems, s => Assert.NotEmpty(s.IgdbPlatforms!));
    }

    [Fact]
    public void Bad_scraping_settings_fall_back_with_an_error_each()
    {
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = "C:/h",
            ConfigDir = "C:/c",
            FileExists = null,
            Settings = new ConfigFile("settings.toml", """
                [scraping]
                provider = "screenscrapper"
                media = ["cover", "box-texture"]
                hash_limit_mb = -1
                """),
        });

        Assert.Equal(3, result.Diagnostics.Count(d => d.IsError));
        Assert.Contains(result.Diagnostics, d => d.Message.Contains("did you mean 'screenscraper'?", StringComparison.Ordinal));
        Assert.Contains(result.Diagnostics, d => d.Message.Contains("did you mean 'box_texture'?", StringComparison.Ordinal));
        var settings = result.Config.Settings.Scraping;
        Assert.Equal("screenscraper", settings.Provider);
        Assert.Equal(["cover", "box_texture"], settings.Media);
        Assert.Equal(64L * 1024 * 1024, settings.HashLimitBytes);
    }

    [Fact]
    public void The_provider_is_never_also_a_fallback()
    {
        var settings = Settings("provider = \"igdb\"\nfallback = [\"igdb\", \"steamgriddb\", \"screenscraper\", \"steamgriddb\"]");

        Assert.Equal(["igdb", "steamgriddb", "screenscraper"], settings.ProviderOrder);
    }
}

/// <summary>Derivatives for the user's art and scraped covers, baked off the main thread by the derivative service.</summary>
public sealed class DerivativeServiceTests : IAsyncLifetime
{
    private ScrapeBed _bed = null!;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    public async ValueTask InitializeAsync() => _bed = await ScrapeBed.CreateAsync();

    public async ValueTask DisposeAsync() => await _bed.DisposeAsync();

    [Fact]
    public async Task Missing_derivatives_are_baked_and_regenerated_when_their_source_changes()
    {
        _bed.Rom("megadrive/Game.md");
        var art = _bed.Dir.File("user/media/megadrive/cover/Game.png");
        File.WriteAllBytes(art, TestImages.RealPng(40, 56, (_, _) => (200, 10, 10, 255)));
        File.SetLastWriteTimeUtc(art, new DateTime(2024, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        await _bed.ScanAsync();
        using var service = _bed.Service(derivatives: true);
        Assert.SkipUnless(service.Derivatives.CanBake, "no image decoder on this platform");

        var first = await service.Derivatives.BakeMissingAsync(null, Ct);

        Assert.Equal((1, 1, 0), (first.Images, first.Baked, first.Failed));
        var row = (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single();
        var old = TextureDerivatives.PathFor(_bed.Paths.CacheDir, MediaRoot.Config, row.CoverPath!, row.CoverSizeBytes, row.CoverMtimeMs);
        Assert.Equal(Bc7DdsWriter.FileLength, new FileInfo(old).Length);
        Assert.Equal(1, (await service.Derivatives.BakeMissingAsync(null, Ct)).AlreadyBaked);

        // The user replaces the art: the rescan sees the new size and time, and the old derivative goes.
        File.WriteAllBytes(art, TestImages.RealPng(60, 84, (_, _) => (10, 10, 200, 255)));
        File.SetLastWriteTimeUtc(art, new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        await _bed.ScanAsync();
        var second = await service.Derivatives.BakeMissingAsync(null, Ct);

        row = (await _bed.Library.GetGamesAsync("megadrive", Ct)).Games.Single();
        var fresh = TextureDerivatives.PathFor(_bed.Paths.CacheDir, MediaRoot.Config, row.CoverPath!, row.CoverSizeBytes, row.CoverMtimeMs);
        Assert.NotEqual(old, fresh);
        Assert.Equal((1, 1), (second.Baked, second.Pruned));
        Assert.True(File.Exists(fresh));
        Assert.False(File.Exists(old));
    }

    [Fact]
    public async Task Without_a_decoder_nothing_is_baked_and_nothing_fails_loudly()
    {
        _bed.Rom("megadrive/Game.md");
        File.WriteAllBytes(_bed.Dir.File("user/media/megadrive/cover/Game.png"), ScrapeBed.Png("x"));
        await _bed.ScanAsync();
        using var service = _bed.Service(derivatives: false);

        var summary = await service.Derivatives.BakeMissingAsync(null, Ct);

        Assert.False(service.Derivatives.CanBake);
        Assert.Equal((1, 0), (summary.Images, summary.Baked));
    }
}
