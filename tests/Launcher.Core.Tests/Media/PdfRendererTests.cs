using System.Runtime.Versioning;
using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Media;

/// <summary>
/// The platform's PDF renderer (Windows.Data.Pdf on Windows), on PDFs <see cref="TestPdfs"/> writes. Each test starts
/// with <see cref="Renderer"/>, which skips it elsewhere.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class PdfRendererTests : IDisposable
{
    private static readonly TestPdfs.Page Red = new(300, 400, (220, 30, 30));
    private static readonly TestPdfs.Page WideBlue = new(600, 300, (30, 30, 220));

    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    private static IPdfRenderer Renderer()
    {
        var renderer = PlatformServices.CreatePdfRenderer();
        Assert.SkipWhen(renderer is null, "no PDF renderer on this platform");
        return renderer;
    }

    private string Manual(string name = "manual.pdf", params TestPdfs.Page[] pages)
    {
        var path = _dir.Combine(name);
        TestPdfs.Write(path, pages.Length == 0 ? [Red, WideBlue] : pages);
        return path;
    }

    [Fact]
    public void Its_pages_are_counted_and_sized_in_device_independent_pixels()
    {
        using var reader = Renderer().Open(Manual(), out var error);
        Assert.True(reader is not null, error);
        Assert.Equal(2, reader.PageCount);

        // Points are 1/72 inch; DIPs 1/96.
        Assert.True(reader.TryGetPageSize(0, out var width, out var height));
        Assert.Equal((400f, 533.33f), (width, MathF.Round(height, 2)));
        Assert.True(reader.TryGetPageSize(1, out width, out height));
        Assert.Equal((800f, 400f), (width, height));
        Assert.False(reader.TryGetPageSize(2, out _, out _));
        Assert.False(reader.TryGetPageSize(-1, out _, out _));
    }

    [Fact]
    public void A_page_is_rendered_as_opaque_RGBA_top_row_first_on_white()
    {
        using var reader = Renderer().Open(Manual(), out var error);
        Assert.True(reader is not null, error);
        const int width = 150, height = 200;
        var rgba = new byte[width * height * 4];
        Assert.True(reader.TryRender(0, width, height, rgba, out error), error);

        // The colour fills the top-left quarter; the rest is paper.
        AssertColour(rgba, width, width / 4, height / 4, (220, 30, 30));
        AssertColour(rgba, width, width * 3 / 4, height / 4, (255, 255, 255));
        AssertColour(rgba, width, width / 4, height * 3 / 4, (255, 255, 255));
        for (var i = 3; i < rgba.Length; i += 4)
        {
            Assert.Equal(255, rgba[i]);
        }
    }

    [Fact]
    public void Pages_are_rendered_at_any_size_in_any_order()
    {
        using var reader = Renderer().Open(Manual(), out var error);
        Assert.True(reader is not null, error);
        foreach (var (page, width, height, colour) in new[]
        {
            (1, 400, 200, ((byte)30, (byte)30, (byte)220)),
            (0, 33, 44, ((byte)220, (byte)30, (byte)30)),
            (1, 1200, 600, ((byte)30, (byte)30, (byte)220)),
            (0, 600, 800, ((byte)220, (byte)30, (byte)30)),
        })
        {
            var rgba = new byte[width * height * 4];
            Assert.True(reader.TryRender(page, width, height, rgba, out error), error);
            AssertColour(rgba, width, width / 4, height / 4, colour);
            AssertColour(rgba, width, width - 2, height / 4, (255, 255, 255));
        }
    }

    [Fact]
    public void A_page_that_isnt_there_is_an_error()
    {
        using var reader = Renderer().Open(Manual(), out var error);
        Assert.True(reader is not null, error);
        Assert.False(reader.TryRender(2, 10, 10, new byte[400], out error));
        Assert.Equal("there's no page 3", error);
    }

    [Fact]
    public void A_buffer_too_small_is_refused()
    {
        using var reader = Renderer().Open(Manual(), out var error);
        Assert.True(reader is not null, error);
        Assert.Throws<ArgumentException>(() => reader.TryRender(0, 10, 10, new byte[399], out _));
    }

    [Fact]
    public void A_file_that_isnt_a_readable_pdf_is_an_error_not_an_exception()
    {
        var renderer = Renderer();

        Assert.Null(renderer.Open(_dir.Combine("missing.pdf"), out var error));
        Assert.Equal("the file isn't there", error);

        var text = _dir.File("not-a-pdf.pdf", "These are just words.");
        Assert.Null(renderer.Open(text, out error));
        Assert.StartsWith("couldn't read it as a PDF", error, StringComparison.Ordinal);

        var whole = TestPdfs.Bytes(Red);
        var truncated = _dir.Combine("truncated.pdf");
        File.WriteAllBytes(truncated, whole[..(whole.Length / 3)]);
        Assert.Null(renderer.Open(truncated, out error));
        Assert.NotNull(error);
    }

    [Fact]
    public async Task Two_readers_work_at_once_each_on_its_own_thread()
    {
        var renderer = Renderer();
        var first = Manual("first.pdf", Red);
        var second = Manual("second.pdf", WideBlue);
        var ct = TestContext.Current.CancellationToken;

        static (byte, byte, byte) Render(IPdfRenderer renderer, string path)
        {
            using var reader = renderer.Open(path, out var error) ?? throw new InvalidOperationException(error);
            var rgba = new byte[80 * 80 * 4];
            for (var i = 0; i < 10; i++)
            {
                if (!reader.TryRender(0, 80, 80, rgba, out error))
                {
                    throw new InvalidOperationException(error);
                }
            }

            var at = ((20 * 80) + 20) * 4;
            return (rgba[at], rgba[at + 1], rgba[at + 2]);
        }

        var results = await Task.WhenAll(
            Task.Factory.StartNew(() => Render(renderer, first), ct, TaskCreationOptions.LongRunning, TaskScheduler.Default),
            Task.Factory.StartNew(() => Render(renderer, second), ct, TaskCreationOptions.LongRunning, TaskScheduler.Default));
        AssertNear(results[0], (220, 30, 30));
        AssertNear(results[1], (30, 30, 220));
    }

    private static void AssertColour(byte[] rgba, int width, int x, int y, (byte R, byte G, byte B) expected)
    {
        var at = ((y * width) + x) * 4;
        AssertNear((rgba[at], rgba[at + 1], rgba[at + 2]), expected);
    }

    private static void AssertNear((byte R, byte G, byte B) actual, (byte R, byte G, byte B) expected)
    {
        // Colour management may shift a value or two.
        Assert.True(
            Math.Abs(actual.R - expected.R) <= 6 && Math.Abs(actual.G - expected.G) <= 6 && Math.Abs(actual.B - expected.B) <= 6,
            $"expected about {expected}, got {actual}");
    }
}
