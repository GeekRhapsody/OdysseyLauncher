using Launcher.Core.Importing;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Scraping;
using Launcher.Core.Tests.Scraping;

namespace Launcher.Core.Tests.Importing;

public sealed class GamelistImportServiceTests : IAsyncLifetime
{
    private const string Skate = "720 Degrees (USA).zip";
    private const string Zelda = "Sub/Zelda (USA).zip";
    private const string Mario = "Super Mario Bros. (World).zip";

    private static readonly GameKey SkateKey = new("nes", "720 degrees (usa).zip");
    private static readonly GameKey ZeldaKey = new("nes", "sub/zelda (usa).zip");

    private ScrapeBed _bed = null!;
    private DerivativeService _derivatives = null!;
    private GamelistImportService _service = null!;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    public async ValueTask InitializeAsync()
    {
        _bed = await ScrapeBed.CreateAsync();
        _bed.Rom("nes/" + Skate);
        _bed.Rom("nes/" + Zelda);
        _bed.Rom("nes/" + Mario);
        await _bed.ScanAsync();
        _derivatives = new DerivativeService(_bed.Library, _bed.Paths, PlatformServices.CreateImageDecoder());
        _service = new GamelistImportService(_bed.Library, _bed.Paths, _derivatives, _bed.Clock);
    }

    public async ValueTask DisposeAsync()
    {
        _derivatives.Dispose();
        await _bed.DisposeAsync();
    }

    private string RomDir => _bed.Dir.Combine("ROMs", "nes");

    private string Gamelist(string games, string? path = null)
    {
        path ??= Path.Combine(RomDir, GamelistImportService.FileName);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, $"<?xml version=\"1.0\"?>\n<gameList>\n{games}\n</gameList>\n");
        return path;
    }

    private string Art(string relative, byte[] content)
    {
        var path = Path.Combine(RomDir, relative.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllBytes(path, content);
        return path;
    }

    /// <summary>An MP4's first box: the import checks the first bytes only.</summary>
    private static byte[] Mp4() => [0, 0, 0, 24, (byte)'f', (byte)'t', (byte)'y', (byte)'p', (byte)'i', (byte)'s', (byte)'o', (byte)'m', 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0];

    private const string SkateEntry = """
        <game id="1726">
            <path>./720 Degrees (USA).zip</path>
            <name>720°</name>
            <desc>You're a skateboarder.</desc>
            <genre>Sports / Skateboard</genre>
            <image>./images/720 Degrees (USA)-image.png</image>
            <video>./videos/720 Degrees (USA)-video.mp4</video>
            <marquee>./images/720 Degrees (USA)-marquee.png</marquee>
            <thumbnail>./images/720 Degrees (USA)-thumb.png</thumbnail>
            <rating>0.55</rating>
            <releasedate>19891101T000000</releasedate>
            <developer>Atari</developer>
            <publisher>Mindscape International</publisher>
            <players>1</players>
            <favorite>true</favorite>
            <scrap name="ScreenScraper" date="20260529T090149" />
        </game>
        """;

    private void SkateArt()
    {
        Art("images/720 Degrees (USA)-image.png", ScrapeBed.Png("image"));
        Art("images/720 Degrees (USA)-marquee.png", ScrapeBed.Png("marquee"));
        Art("images/720 Degrees (USA)-thumb.png", ScrapeBed.Png("thumb"));
        Art("videos/720 Degrees (USA)-video.mp4", Mp4());
    }

    private async Task<GamelistImportResult> ImportAsync(string file, List<IReadOnlyList<GameKey>>? saved = null)
    {
        var plan = await _service.PlanAsync("nes", file, Ct);
        Assert.Null(plan.Error);
        return await _service.ImportAsync(plan, null, keys => saved?.Add(keys), Ct);
    }

    private async Task<IReadOnlyList<GameMediaInfo>> Media(string relPath) =>
        await _bed.Library.GetGameMediaInfoAsync((await _bed.Game("nes", relPath)).GameId, Ct);

    [Fact]
    public async Task Finds_the_gamelist_in_the_ROM_folder_and_in_ES_DEs_gamelists_folder()
    {
        Assert.Empty(await _service.FindAsync("nes", Ct));

        var inRoms = Gamelist(string.Empty);
        var esde = Gamelist(string.Empty, _bed.Dir.Combine("ES-DE", "gamelists", "nes", "gamelist.xml"));

        Assert.Equal([inRoms, esde], await _service.FindAsync("nes", Ct));
    }

    [Fact]
    public async Task Imports_metadata_as_the_users_own_and_copies_media_to_the_games_own_names()
    {
        SkateArt();
        var file = Gamelist(SkateEntry);
        var saved = new List<IReadOnlyList<GameKey>>();

        var plan = await _service.PlanAsync("nes", file, Ct);
        Assert.Equal((1, 1, 0, 1, 1, 1, 4), (plan.Entries, plan.InLibrary, plan.NotInLibrary, plan.WithMetadata, plan.Favourites, plan.Matches, plan.Files));
        var result = await _service.ImportAsync(plan, null, keys => saved.Add(keys), Ct);

        Assert.Equal((1, 1, 1, 4, 0, 0, 0), (result.MetadataGames, result.Favourites, result.Matches, result.CopiedTotal, result.AlreadyThere, result.Missing, result.Unreadable));
        Assert.Equal([SkateKey], Assert.Single(saved));

        var edit = (await _bed.Library.GetMetadataEditAsync(SkateKey, Ct))!;
        Assert.Equal("720°", edit.TitleOverride);
        Assert.Null(edit.Scraped);
        Assert.Equal(new MetadataOverride("You're a skateboarder.", "1989-11-01", "Atari", "Mindscape International", "Sports / Skateboard", "1", 0.55), edit.Overrides);

        var game = await _bed.Game("nes", Skate);
        Assert.Equal("720°", game.Title);
        Assert.True(game.IsFavourite);

        // Each kind, at the game's own name; the gamelist's files are copied, not moved.
        var media = (await Media(Skate)).ToDictionary(m => m.Kind, m => m.Media.Path);
        Assert.Equal("media/nes/cover/720 Degrees (USA).zip.png", media[MediaKinds.Cover]);
        Assert.Equal("media/nes/screenshot/720 Degrees (USA).zip.png", media[MediaKinds.Screenshot]);
        Assert.Equal("media/nes/logo/720 Degrees (USA).zip.png", media[MediaKinds.Logo]);
        Assert.Equal("media/nes/video/720 Degrees (USA).zip.mp4", media[MediaKinds.Video]);
        Assert.True(File.Exists(Path.Combine(RomDir, "images", "720 Degrees (USA)-thumb.png")));
        Assert.True(File.Exists(Path.Combine(RomDir, "videos", "720 Degrees (USA)-video.mp4")));
        Assert.Equal(ScrapeBed.Png("thumb"), File.ReadAllBytes(_bed.MediaFile("nes/" + Skate, MediaKinds.Cover, ".png")));

        if (_derivatives.CanBake)
        {
            var cover = (await Media(Skate)).Single(m => m.Kind == MediaKinds.Cover).Media;
            Assert.True(File.Exists(_derivatives.PathFor(cover.Path, cover.SizeBytes, cover.MtimeMs)));
        }

        // The ScreenScraper id is the game's match, fetched by id by the next scrape.
        Assert.Equal(("1726", MatchMethods.Gamelist), await Match(SkateKey));
    }

    [Fact]
    public async Task Only_fills_gaps_and_importing_again_adds_nothing()
    {
        SkateArt();
        var file = Gamelist(SkateEntry);

        // The user's own genre, and a cover the game already has, stay.
        await _bed.Library.SetMetadataOverrideAsync(SkateKey, new MetadataOverride(Genre: "Skating"), Ct);
        var cover = _bed.MediaFile("nes/" + Skate, MediaKinds.Cover, ".png");
        Directory.CreateDirectory(Path.GetDirectoryName(cover)!);
        File.WriteAllBytes(cover, ScrapeBed.Png("mine"));
        await _bed.Library.RefreshMediaAsync("nes", Ct);

        var first = await ImportAsync(file);
        Assert.Equal(3, first.CopiedTotal);
        Assert.False(first.Copied.ContainsKey(MediaKinds.Cover));
        Assert.Equal("Skating", (await _bed.Library.GetMetadataEditAsync(SkateKey, Ct))!.Overrides.Genre);
        Assert.Equal(ScrapeBed.Png("mine"), File.ReadAllBytes(cover));

        var again = await _service.PlanAsync("nes", file, Ct);
        Assert.Equal((1, 0, 0, 0, 0), (again.InLibrary, again.Games.Count, again.Files, again.Favourites, again.Matches));
    }

    [Fact]
    public async Task Leaves_scraped_values_and_matches_alone()
    {
        var file = Gamelist(SkateEntry);
        await _bed.Library.WriteAsync(c =>
        {
            using var command = c.CreateCommand();
            command.CommandText = """
                INSERT INTO metadata (game_id, title, developer, source) SELECT game_id, '720 Degrees!', 'Tengen', 'screenscraper' FROM games WHERE path_key = $key;
                INSERT INTO scraper_matches (game_id, scraper, scraper_game_id, method, matched_at) SELECT game_id, 'screenscraper', '5', 'hash', 1 FROM games WHERE path_key = $key;
                """;
            command.Parameters.AddWithValue("$key", SkateKey.PathKey);
            return command.ExecuteNonQuery();
        }, Ct);

        var plan = await _service.PlanAsync("nes", file, Ct);
        var game = Assert.Single(plan.Games);
        Assert.Null(game.Title);
        Assert.Null(game.Fill.Developer);
        Assert.Equal("Mindscape International", game.Fill.Publisher);
        Assert.Null(game.ScreenScraperId);

        await _service.ImportAsync(plan, null, null, Ct);
        Assert.Equal(("5", "hash"), await Match(SkateKey));
        Assert.Null((await _bed.Library.GetMetadataEditAsync(SkateKey, Ct))!.TitleOverride);
    }

    [Fact]
    public async Task Matches_subfolders_and_home_and_absolute_paths_and_counts_games_not_in_the_library()
    {
        Art("Sub/zelda-thumb.png", ScrapeBed.Png("zelda"));
        Art("mario.png", ScrapeBed.Png("mario"));
        var file = Gamelist($"""
            <game><path>./Sub/Zelda (USA).zip</path><name>The Legend of Zelda</name><thumbnail>./Sub/zelda-thumb.png</thumbnail></game>
            <game><path>~/ROMs/nes/Super Mario Bros. (World).zip</path><name>Super Mario Bros.</name><thumbnail>{Path.Combine(RomDir, "mario.png")}</thumbnail></game>
            <game><path>./Not Here (USA).zip</path><name>Not here</name></game>
            <game><path>/userdata/roms/nes/Elsewhere.zip</path><name>Elsewhere</name></game>
            """);

        var plan = await _service.PlanAsync("nes", file, Ct);
        Assert.Equal((4, 2, 2), (plan.Entries, plan.InLibrary, plan.NotInLibrary));
        await _service.ImportAsync(plan, null, null, Ct);

        Assert.Equal("The Legend of Zelda", (await _bed.Game("nes", Zelda)).Title);
        Assert.Equal("Super Mario Bros.", (await _bed.Game("nes", Mario)).Title);
        Assert.Equal(ScrapeBed.Png("zelda"), File.ReadAllBytes(_bed.MediaFile("nes/" + Zelda, MediaKinds.Cover, ".png")));
        Assert.Equal(ScrapeBed.Png("mario"), File.ReadAllBytes(_bed.MediaFile("nes/" + Mario, MediaKinds.Cover, ".png")));
    }

    [Fact]
    public async Task A_gamelist_outside_the_ROM_folder_is_read_against_it()
    {
        Art("images/zelda.png", ScrapeBed.Png("zelda"));
        var file = Gamelist(
            "<game><path>./Sub/Zelda (USA).zip</path><name>Zelda</name><thumbnail>./images/zelda.png</thumbnail></game>",
            _bed.Dir.Combine("ES-DE", "gamelists", "nes", "gamelist.xml"));

        var result = await ImportAsync(file);

        Assert.Equal(1, result.CopiedTotal);
        Assert.Equal("Zelda", (await _bed.Game("nes", Zelda)).Title);
    }

    [Fact]
    public async Task An_unscraped_entrys_file_name_isnt_taken_as_a_title()
    {
        var file = Gamelist("""
            <game><path>./Super Mario Bros. (World).zip</path><name>Super Mario Bros. (World)</name></game>
            <game><path>./720 Degrees (USA).zip</path><name>720 Degrees</name></game>
            <game><path>./Sub/Zelda (USA).zip</path><name>The Legend of Zelda</name></game>
            """);

        var plan = await _service.PlanAsync("nes", file, Ct);

        // Neither is the cleaned file name, which shows anyway; the second adds the article.
        Assert.Equal([ZeldaKey], plan.Games.Select(g => g.Key));
    }

    [Fact]
    public async Task Missing_and_unreadable_files_are_counted_and_nothing_is_left_behind()
    {
        Art("images/bad-thumb.png", "not an image"u8.ToArray());
        Art("images/manual.pdf", "%PDF"u8.ToArray());
        var file = Gamelist("""
            <game>
                <path>./720 Degrees (USA).zip</path>
                <thumbnail>./images/bad-thumb.png</thumbnail>
                <image>./images/missing.png</image>
                <marquee>./images/manual.pdf</marquee>
            </game>
            """);

        var result = await ImportAsync(file);

        Assert.Equal((0, 1, 2), (result.CopiedTotal, result.Missing, result.Unreadable));
        Assert.Empty(await Media(Skate));
        var mediaDir = Path.Combine(_bed.Paths.DataDir, "media");
        Assert.False(Directory.Exists(mediaDir) && Directory.EnumerateFiles(mediaDir, "*", SearchOption.AllDirectories).Any());
    }

    [Fact]
    public async Task Hidden_flags_are_counted_not_imported()
    {
        var file = Gamelist("<game><path>./720 Degrees (USA).zip</path><hidden>true</hidden></game>");

        var plan = await _service.PlanAsync("nes", file, Ct);

        Assert.Equal((1, 0), (plan.Hidden, plan.Games.Count));
    }

    [Fact]
    public async Task A_bad_gamelist_is_a_plan_with_an_error()
    {
        var file = Gamelist("<game><path>");

        var plan = await _service.PlanAsync("nes", file, Ct);

        Assert.NotNull(plan.Error);
        Assert.Empty(plan.Games);
    }

    private async Task<(string Id, string Method)?> Match(GameKey key) =>
        await _bed.Library.ReadAsync<(string, string)?>(c =>
        {
            using var command = c.CreateCommand();
            command.CommandText = """
                SELECT m.scraper_game_id, m.method FROM scraper_matches m JOIN games g ON g.game_id = m.game_id
                WHERE g.path_key = $key AND m.scraper = 'screenscraper'
                """;
            command.Parameters.AddWithValue("$key", key.PathKey);
            using var reader = command.ExecuteReader();
            return reader.Read() ? (reader.GetString(0), reader.GetString(1)) : null;
        }, Ct);
}
