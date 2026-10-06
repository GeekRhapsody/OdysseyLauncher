using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Tests.Scraping;

namespace Launcher.Core.Tests.Media;

public sealed class UserArtServiceTests : IAsyncLifetime
{
    private const string Sonic = "megadrive/Sonic the Hedgehog 3 (Europe).md";

    private static readonly GameKey Key = new("megadrive", "sonic the hedgehog 3 (europe).md");

    private ScrapeBed _bed = null!;
    private DerivativeService _derivatives = null!;
    private UserArtService _service = null!;
    private readonly List<IReadOnlyList<GameKey>?> _changes = [];

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    public async ValueTask InitializeAsync()
    {
        _bed = await ScrapeBed.CreateAsync("media = [\"cover\", \"spine\"]");
        _bed.Rom(Sonic);
        _bed.Rom("megadrive/Ecco the Dolphin (USA, Europe).md");
        await _bed.ScanAsync();
        _derivatives = new DerivativeService(_bed.Library, _bed.Paths, PlatformServices.CreateImageDecoder());
        _service = new UserArtService(_bed.Library, _derivatives);
        _bed.Library.MediaChanged += (_, e) =>
        {
            lock (_changes)
            {
                _changes.Add(e.Games);
            }
        };
    }

    public async ValueTask DisposeAsync()
    {
        _derivatives.Dispose();
        await _bed.DisposeAsync();
    }

    private string Download(string name, byte[] content)
    {
        var path = _bed.Dir.File("downloads/" + name);
        File.WriteAllBytes(path, content);
        return path;
    }

    private async Task<GameMediaInfo?> Media(string kind)
    {
        var game = await _bed.Game("megadrive", "Sonic the Hedgehog 3 (Europe).md");
        return (await _bed.Library.GetGameMediaInfoAsync(game.GameId, Ct)).FirstOrDefault(m => m.Kind == kind);
    }

    [Fact]
    public async Task A_chosen_image_is_copied_to_the_games_name_baked_and_indexed_at_once()
    {
        var result = await _service.SetAsync(Key, MediaKinds.Back, Download("back.png", ScrapeBed.Png("back")), Ct);

        Assert.Equal(UserArtStatus.Set, result.Status);
        Assert.Equal("media/megadrive/backcovers/Sonic the Hedgehog 3 (Europe).png", result.Path);
        Assert.True(File.Exists(Path.Combine(_bed.Paths.DataDir, "media", "megadrive", "backcovers", "Sonic the Hedgehog 3 (Europe).png")));
        var back = (await Media(MediaKinds.Back))!;
        Assert.Equal(result.Path, back.Media.Path);
        Assert.Equal((24, 32), (back.Width, back.Height));
        Assert.Equal([Key], Assert.Single(_changes)!);
        if (_derivatives.CanBake)
        {
            Assert.True(File.Exists(_derivatives.PathFor(back.Media.Path, back.Media.SizeBytes, back.Media.MtimeMs)));
        }

        // Only this game: Ecco has no back.
        var ecco = await _bed.Game("megadrive", "Ecco the Dolphin (USA, Europe).md");
        Assert.DoesNotContain(await _bed.Library.GetGameMediaInfoAsync(ecco.GameId, Ct), m => m.Kind == MediaKinds.Back);
    }

    [Fact]
    public async Task Another_image_for_the_same_slot_replaces_it_even_in_another_format()
    {
        await _service.SetAsync(Key, MediaKinds.Cover, Download("a.png", ScrapeBed.Png("a")), Ct);

        var result = await _service.SetAsync(Key, MediaKinds.Cover, Download("b.jpg", TestSupport.TestImages.Jpeg(40, 56)), Ct);

        Assert.Equal("media/megadrive/covers/Sonic the Hedgehog 3 (Europe).jpg", result.Path);
        Assert.False(File.Exists(Path.Combine(_bed.Paths.DataDir, "media", "megadrive", "covers", "Sonic the Hedgehog 3 (Europe).png")));
        var cover = (await Media(MediaKinds.Cover))!;
        Assert.Equal(result.Path, cover.Media.Path);
        Assert.Equal((40, 56), (cover.Width, cover.Height));
    }

    [Fact]
    public async Task Files_that_arent_images_are_refused_and_nothing_changes()
    {
        var text = await _service.SetAsync(Key, MediaKinds.Cover, Download("notes.txt", "hello"u8.ToArray()), Ct);
        var fake = await _service.SetAsync(Key, MediaKinds.Cover, Download("fake.png", "not a png"u8.ToArray()), Ct);
        var missing = await _service.SetAsync(new GameKey("megadrive", "gone.md"), MediaKinds.Cover, Download("c.png", ScrapeBed.Png("c")), Ct);

        Assert.Equal(UserArtStatus.NotAnImage, text.Status);
        Assert.Contains("isn't a PNG, JPEG or WebP image", text.Message, StringComparison.Ordinal);
        Assert.Equal(UserArtStatus.NotAnImage, fake.Status);
        Assert.Equal(UserArtStatus.NotInLibrary, missing.Status);
        Assert.Null(await Media(MediaKinds.Cover));
        Assert.False(Directory.Exists(Path.Combine(_bed.Paths.DataDir, "media")));
        Assert.Throws<ArgumentException>(() => _service.SetAsync(Key, MediaKinds.Model, "x.glb", Ct).GetAwaiter().GetResult());
    }

    [Fact]
    public async Task A_chosen_image_replaces_a_scraped_one_and_removing_it_empties_the_slot_until_the_next_scrape()
    {
        using var scraper = _bed.Service();
        await scraper.ScrapeGameAsync(Key, Ct);
        var scraped = (await Media(MediaKinds.Cover))!;
        Assert.Equal("media/megadrive/covers/Sonic the Hedgehog 3 (Europe).png", scraped.Media.Path);

        // One file per kind: the user's replaces the scraped one, whatever its format.
        await _service.SetAsync(Key, MediaKinds.Cover, Download("mine.jpg", TestSupport.TestImages.Jpeg(40, 56)), Ct);
        Assert.Equal("media/megadrive/covers/Sonic the Hedgehog 3 (Europe).jpg", (await Media(MediaKinds.Cover))!.Media.Path);
        Assert.False(File.Exists(Path.Combine(_bed.Paths.DataDir, scraped.Media.Path)));

        // A scrape leaves it alone.
        await scraper.ScrapeGameAsync(Key, Ct);
        Assert.Equal("media/megadrive/covers/Sonic the Hedgehog 3 (Europe).jpg", (await Media(MediaKinds.Cover))!.Media.Path);
        _changes.Clear();

        var result = await _service.RemoveAsync(Key, MediaKinds.Cover, Ct);

        Assert.Equal(UserArtStatus.Removed, result.Status);
        Assert.Null(await Media(MediaKinds.Cover));
        Assert.Contains(_changes, c => c is not null && c.Contains(Key));
        Assert.Equal(UserArtStatus.None, (await _service.RemoveAsync(Key, MediaKinds.Cover, Ct)).Status);

        // The next scrape fills the empty slot.
        await scraper.ScrapeGameAsync(Key, Ct);
        Assert.Equal(scraped.Media.Path, (await Media(MediaKinds.Cover))!.Media.Path);
    }

    [Fact]
    public async Task Removing_a_scraped_image_deletes_its_file()
    {
        using (var scraper = _bed.Service())
        {
            await scraper.ScrapeGameAsync(Key, Ct);
        }

        var spine = (await Media(MediaKinds.Spine))!;

        var result = await _service.RemoveAsync(Key, MediaKinds.Spine, Ct);

        Assert.Equal((UserArtStatus.Removed, spine.Media.Path), (result.Status, result.Path));
        Assert.False(File.Exists(Path.Combine(_bed.Paths.DataDir, spine.Media.Path)));
        Assert.Null(await Media(MediaKinds.Spine));
    }

    [Fact]
    public async Task An_image_named_without_the_roms_extension_is_removed_for_every_game_of_that_name()
    {
        _bed.Rom("megadrive/Shared.md");
        _bed.Rom("megadrive/Shared.gen");
        var art = _bed.Dir.File("user/media/megadrive/covers/Shared.png");
        File.WriteAllBytes(art, ScrapeBed.Png("shared"));
        await _bed.ScanAsync();

        var result = await _service.RemoveAsync(new GameKey("megadrive", "shared.md"), MediaKinds.Cover, Ct);

        Assert.Equal((UserArtStatus.Removed, "media/megadrive/covers/Shared.png"), (result.Status, result.Path));
        Assert.False(File.Exists(art));
        var other = await _bed.Game("megadrive", "Shared.gen");
        Assert.DoesNotContain(await _bed.Library.GetGameMediaInfoAsync(other.GameId, Ct), m => m.Kind == MediaKinds.Cover);
    }

    [Fact]
    public async Task A_chosen_image_replaces_one_named_after_the_whole_rom_name()
    {
        var own = _bed.Dir.File("user/media/megadrive/covers/Sonic the Hedgehog 3 (Europe).md.png");
        File.WriteAllBytes(own, ScrapeBed.Png("own"));
        await _bed.ScanAsync();

        var result = await _service.SetAsync(Key, MediaKinds.Cover, Download("mine.jpg", TestSupport.TestImages.Jpeg(40, 56)), Ct);

        Assert.Equal("media/megadrive/covers/Sonic the Hedgehog 3 (Europe).jpg", result.Path);
        Assert.False(File.Exists(own));
        Assert.Equal(result.Path, (await Media(MediaKinds.Cover))!.Media.Path);
    }

    [Fact]
    public async Task A_rebuild_keeps_the_users_images()
    {
        await _service.SetAsync(Key, MediaKinds.Spine, Download("spine.png", ScrapeBed.Png("spine")), Ct);

        await _bed.Library.RebuildAsync(null, Ct);

        Assert.Equal("media/megadrive/spines/Sonic the Hedgehog 3 (Europe).png", (await Media(MediaKinds.Spine))!.Media.Path);
    }
}
