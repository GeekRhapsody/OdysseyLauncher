using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Media;

public sealed class ImageHeadersTests
{
    public static TheoryData<string, byte[], int, int> Images => new()
    {
        { "png", TestImages.Png(640, 896), 640, 896 },
        { "jpeg", TestImages.Jpeg(1000, 1400), 1000, 1400 },
        { "jpeg after a 60 KB EXIF segment", TestImages.Jpeg(512, 364, 60_000), 512, 364 },
        { "webp lossy", TestImages.WebPLossy(300, 420), 300, 420 },
        { "webp lossless", TestImages.WebPLossless(16383, 2), 16383, 2 },
        { "webp extended", TestImages.WebPExtended(4096, 3000), 4096, 3000 },
    };

    [Theory]
    [MemberData(nameof(Images))]
    public void Reads_the_size_from_the_header(string format, byte[] bytes, int width, int height)
    {
        using var stream = new MemoryStream(bytes);

        Assert.True(ImageHeaders.TryReadSize(stream, out var w, out var h), format);
        Assert.Equal((width, height), (w, h));
    }

    [Theory]
    [InlineData(new byte[0])]
    [InlineData(new byte[] { 0x42, 0x4D, 0, 0, 0, 0 })]
    [InlineData(new byte[] { 0xFF, 0xD8, 0xFF, 0xD9 })]
    [InlineData(new byte[] { 0xFF, 0xD8, 0xFF, 0xDA, 0x00, 0x02 })]
    [InlineData(new byte[] { 0x89, (byte)'P', (byte)'N', (byte)'G', 0x0D, 0x0A })]
    public void Anything_else_is_unreadable(byte[] bytes)
    {
        using var stream = new MemoryStream(bytes);

        Assert.False(ImageHeaders.TryReadSize(stream, out var w, out var h));
        Assert.Equal((0, 0), (w, h));
    }

    [Fact]
    public void A_zero_size_is_rejected()
    {
        using var stream = new MemoryStream(TestImages.Png(0, 100));

        Assert.False(ImageHeaders.TryReadSize(stream, out _, out _));
    }

    [Fact]
    public void A_missing_file_is_unreadable()
    {
        Assert.False(ImageHeaders.TryReadSize(Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".png"), out _, out _));
    }

    [Fact]
    public void Derivative_names_are_stable_and_change_with_every_input()
    {
        var name = TextureDerivatives.FileName("media/ps2/cover/game.png", 1000, 5000);

        Assert.Equal(name, TextureDerivatives.FileName("media\\ps2\\cover\\game.png", 1000, 5000));
        Assert.Matches("^[0-9a-f]{32}\\.dds$", name);
        Assert.NotEqual(name, TextureDerivatives.FileName("media/ps2/cover/Game.png", 1000, 5000));
        Assert.NotEqual(name, TextureDerivatives.FileName("media/ps2/cover/game.png", 1001, 5000));
        Assert.NotEqual(name, TextureDerivatives.FileName("media/ps2/cover/game.png", 1000, 5001));
    }

    [Fact]
    public void A_derivative_path_from_indexed_stamps_matches_one_from_the_file()
    {
        var cache = Path.Combine(Path.GetTempPath(), "cache");
        var name = TextureDerivatives.FileName("media/snes/cover/Zelda ü.png", 123_456, 1_700_000_000_000);

        Assert.Equal(Path.Combine(cache, "textures", name), TextureDerivatives.PathFor(cache, "media/snes/cover/Zelda ü.png", 123_456, 1_700_000_000_000));
        Assert.Equal(Path.Combine(cache, "textures", name), TextureDerivatives.PathFor(cache + Path.DirectorySeparatorChar, @"media\snes\cover\Zelda ü.png", 123_456, 1_700_000_000_000));
    }

    [Fact]
    public void A_derivative_path_follows_its_source_file_wherever_the_media_folder_is()
    {
        using var dir = new TempDir();
        var source = dir.File("Launcher media/ps2/cover/game.png", "x", new DateTime(2025, 1, 2, 3, 4, 5, DateTimeKind.Utc));

        // The stored path's "media/" stands for the media folder, which needn't be called that (A4, 2026-10-04).
        var path = TextureDerivatives.PathFor(dir.Combine("cache"), dir.Combine("Launcher media"), "media/ps2/cover/game.png");

        var expected = TextureDerivatives.FileName("media/ps2/cover/game.png", 1,
            new DateTimeOffset(2025, 1, 2, 3, 4, 5, TimeSpan.Zero).ToUnixTimeMilliseconds());
        Assert.Equal(dir.Combine("cache", "textures", expected), path);
        File.Delete(source);
        Assert.Null(TextureDerivatives.PathFor(dir.Combine("cache"), dir.Combine("Launcher media"), "media/ps2/cover/game.png"));
    }
}
