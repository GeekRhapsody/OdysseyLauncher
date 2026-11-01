using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Media;

/// <summary>Spotting ScreenScraper's flat green placeholders, and keeping everything else.</summary>
public sealed class PlaceholderImagesTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    /// <summary>The platform's decoder (WIC on Windows); the test is skipped where there's none.</summary>
    private static IImageDecoder Decoder()
    {
        var decoder = PlatformServices.CreateImageDecoder();
        Assert.SkipWhen(decoder is null, "no image decoder on this platform");
        return decoder;
    }

    /// <summary>Writes a PNG and checks it, as a scrape checks a download.</summary>
    private string? Check(IImageDecoder decoder, int width, int height, Func<int, int, (byte, byte, byte, byte)> colour)
    {
        var path = _dir.Combine(Guid.NewGuid().ToString("N") + ".png");
        File.WriteAllBytes(path, TestImages.RealPng(width, height, colour));
        return PlaceholderImages.Check(decoder, path, new FileInfo(path).Length, width, height);
    }

    [Fact]
    public void ScreenScrapers_own_placeholder_is_one()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Scraping", "Fixtures", "ss_green_placeholder.png");

        Assert.Equal(PlaceholderImages.Reason, PlaceholderImages.Check(Decoder(), path, new FileInfo(path).Length, 421, 680));
    }

    [Fact]
    public void Flat_bright_green_is_one_even_with_a_little_text()
    {
        var decoder = Decoder();

        Assert.Equal(PlaceholderImages.Reason, Check(decoder, 400, 600, (_, _) => (0, 255, 0, 255)));
        Assert.Equal(PlaceholderImages.Reason, Check(decoder, 400, 600,
            (x, y) => x is >= 180 and < 220 && y is >= 290 and < 310 ? ((byte)20, (byte)20, (byte)20, (byte)255) : ((byte)10, (byte)200, (byte)10, (byte)255)));
    }

    [Fact]
    public void Another_flat_colour_or_green_art_is_kept()
    {
        var decoder = Decoder();

        Assert.Null(Check(decoder, 400, 600, (_, _) => (0, 0, 0, 255)));                // black
        Assert.Null(Check(decoder, 400, 600, (_, _) => (255, 255, 255, 255)));          // white
        Assert.Null(Check(decoder, 400, 600, (_, _) => (0, 0, 255, 255)));              // blue
        Assert.Null(Check(decoder, 400, 600, (_, _) => (40, 110, 40, 255)));            // dark green, not bright
        Assert.Null(Check(decoder, 400, 600, (_, y) => y < 300                          // two-tone green
            ? ((byte)0, (byte)255, (byte)0, (byte)255)
            : ((byte)0, (byte)120, (byte)60, (byte)255)));
        Assert.Null(Check(decoder, 400, 600, (_, _) => (0, 255, 0, 0)));                // transparent
    }

    [Fact]
    public void An_image_too_big_for_its_size_to_be_flat_is_never_decoded()
    {
        var decoder = new CountingDecoder();

        Assert.Null(PlaceholderImages.Check(decoder, "cover.jpg", 300_000, 1000, 1400));      // 0.21 bytes a pixel
        Assert.Equal(0, decoder.Calls);
        Assert.Null(PlaceholderImages.Check(decoder, "cover.png", 2_658, 421, 680));          // 0.0093: decoded (black)
        Assert.Equal(1, decoder.Calls);
    }

    [Fact]
    public void The_rule_reads_the_median_colour_and_allows_a_few_stray_pixels()
    {
        var pixels = new byte[PlaceholderImages.Side * PlaceholderImages.Side * 4];
        for (var i = 0; i < pixels.Length; i += 4)
        {
            (pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3]) = ((byte)5, (byte)250, (byte)5, (byte)255);
        }

        Assert.True(PlaceholderImages.IsFlatGreen(pixels));

        // 2% of the pixels another colour: still the placeholder. 4%: not.
        for (var i = 0; i < 20; i++)
        {
            pixels[(i * 4) + 1] = 0;
        }

        Assert.True(PlaceholderImages.IsFlatGreen(pixels));
        for (var i = 20; i < 41; i++)
        {
            pixels[(i * 4) + 1] = 0;
        }

        Assert.False(PlaceholderImages.IsFlatGreen(pixels));
    }

    /// <summary>
    /// The owner's check on real media, read only (2026-11-01: <c>S:\[media]\switch</c> has 90 copies of ScreenScraper's
    /// placeholder, all back covers): every image under <c>ODYSSEY_PLACEHOLDER_DIR</c> is checked and the placeholders
    /// listed. Skipped without it.
    /// </summary>
    [Fact]
    [Trait("Category", "Manual")]
    public void Real_media_folder()
    {
        var folder = Environment.GetEnvironmentVariable("ODYSSEY_PLACEHOLDER_DIR");
        Assert.SkipWhen(string.IsNullOrEmpty(folder), "set ODYSSEY_PLACEHOLDER_DIR to a media folder to check it");
        var decoder = Decoder();
        var flagged = new List<string>();
        var checkedCount = 0;
        foreach (var path in Directory.EnumerateFiles(folder!, "*", SearchOption.AllDirectories))
        {
            using var stream = File.OpenRead(path);
            if (ImageHeaders.TryReadSize(stream, out var width, out var height))
            {
                checkedCount++;
                if (PlaceholderImages.Check(decoder, path, stream.Length, width, height) is not null)
                {
                    flagged.Add(Path.GetRelativePath(folder!, path));
                }
            }
        }

        TestContext.Current.SendDiagnosticMessage($"{checkedCount} images, {flagged.Count} placeholders:\n{string.Join('\n', flagged)}");
        Assert.NotEmpty(flagged);
    }

    /// <summary>Counts decodes, and decodes everything as black.</summary>
    private sealed class CountingDecoder : IImageDecoder
    {
        public int Calls { get; private set; }

        public bool TryDecodeScaled(string path, int width, int height, Span<byte> rgba, out string? error)
        {
            Calls++;
            rgba.Clear();
            error = null;
            return true;
        }
    }
}
