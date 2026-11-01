namespace Launcher.Core.Media;

/// <summary>
/// Spots a provider's placeholder image: ScreenScraper serves some games' missing art (box backs, mostly) as one flat
/// bright green PNG (2026-11-01: 90 of the owner's Switch back covers were the same 421×680, 2,658-byte #00FF00
/// file), which a scrape would otherwise keep in place of a fallback's real art (ARCHITECTURE.md A2, "Provider
/// selection"). Only flat bright green counts: an image of one other colour is kept.
/// </summary>
public static class PlaceholderImages
{
    /// <summary>What <see cref="Check"/> says of a placeholder: a scrape logs it and tries the next provider's image.</summary>
    public const string Reason = "a flat green placeholder";

    /// <summary>The side the image is shrunk to before it's looked at.</summary>
    public const int Side = 32;

    /// <summary>How far, in levels of a channel, a pixel may be from the image's median colour and still count as it (JPEG noise).</summary>
    public const int Tolerance = 24;

    /// <summary>The share of pixels that must be the median colour: the rest may be a little text ("no back cover").</summary>
    public const double Share = 0.97;

    /// <summary>
    /// The most bytes a pixel a file may take to be decoded at all: a flat image compresses to almost nothing (the
    /// placeholder is 0.0093), real art to far more (the owner's Switch art: median 0.68, 1st percentile 0.057), so
    /// almost every download is never decoded.
    /// </summary>
    public const double MaxBytesPerPixel = 1.0 / 16;

    /// <summary>The least green, and how far red and blue must stay below it, for "bright green".</summary>
    public const int MinGreen = 150;

    /// <inheritdoc cref="MinGreen"/>
    public const int GreenLead = 80;

    /// <summary>
    /// Why the image at <paramref name="path"/> is a placeholder, or null when it's real art (or can't be decoded).
    /// Decodes it only when it's small for its size (<see cref="MaxBytesPerPixel"/>). File I/O: not on the main thread.
    /// </summary>
    public static string? Check(IImageDecoder decoder, string path, long sizeBytes, int width, int height)
    {
        ArgumentNullException.ThrowIfNull(decoder);
        ArgumentNullException.ThrowIfNull(path);
        if (width <= 0 || height <= 0 || sizeBytes > MaxBytesPerPixel * width * height)
        {
            return null;
        }

        var rgba = new byte[Side * Side * 4];
        return decoder.TryDecodeScaled(path, Side, Side, rgba, out _) && IsFlatGreen(rgba) ? Reason : null;
    }

    /// <summary>Whether <see cref="Side"/>-square RGBA pixels are, but for <see cref="Share"/>'s remainder, one opaque bright green.</summary>
    public static bool IsFlatGreen(ReadOnlySpan<byte> rgba)
    {
        var count = rgba.Length / 4;
        if (count == 0)
        {
            return false;
        }

        Span<int> median = stackalloc int[3];
        Span<byte> channel = new byte[count];
        for (var c = 0; c < 3; c++)
        {
            for (var i = 0; i < count; i++)
            {
                channel[i] = rgba[(i * 4) + c];
            }

            channel.Sort();
            median[c] = channel[count / 2];
        }

        if (median[1] < MinGreen || median[0] > median[1] - GreenLead || median[2] > median[1] - GreenLead)
        {
            return false;
        }

        var near = 0;
        for (var i = 0; i < count; i++)
        {
            var p = i * 4;
            if (rgba[p + 3] >= 200
                && Math.Abs(rgba[p] - median[0]) <= Tolerance
                && Math.Abs(rgba[p + 1] - median[1]) <= Tolerance
                && Math.Abs(rgba[p + 2] - median[2]) <= Tolerance)
            {
                near++;
            }
        }

        return near >= Share * count;
    }
}
