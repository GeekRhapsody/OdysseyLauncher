namespace Launcher.Core.Theming;

/// <summary>A box's size in model units: the largest side of a template's rest pose is 1 (A7).</summary>
public readonly record struct BoxSize(float Width, float Height, float Depth);

/// <summary>
/// The shape of a template whose manifest says <c>shape = "media"</c> (A6): its front takes the game's cover's
/// width over height, and its depth the game's spine's width over height times the box's height, so the cover, back
/// and spine show whole. Scraped images are normalised (ScreenScraper's are 700 pixels high), so only these ratios
/// are read, never sizes. The grid works out the list's envelope once (<see cref="Unit"/>, the largest of each
/// side), and each cell's shape inside it (<see cref="Fit"/>). Pure and allocation-free.
/// </summary>
public static class BoxShape
{
    /// <summary>Cover aspects are clamped to this range, so a mis-scraped banner doesn't make a sliver.</summary>
    public const float MinCoverAspect = 0.25f;

    public const float MaxCoverAspect = 4f;

    /// <summary>Spine aspects (depth over height) are clamped to this range.</summary>
    public const float MinDepthRatio = 0.02f;

    public const float MaxDepthRatio = 0.5f;

    /// <summary>
    /// The smallest width and height a shape may have, in model units. The grid moves each half of the rest mesh by
    /// the difference, so shrinking past the rest mesh's corners would fold it.
    /// </summary>
    public const float MinSide = 0.1f;

    /// <summary>The smallest depth a shape may have, in model units.</summary>
    public const float MinDepth = 0.01f;

    /// <summary>
    /// A cover's width and height with the larger of the two 1: what one game adds to its list's envelope.
    /// <paramref name="coverAspect"/> is the cover's width over its height, or 0 or less for the rest pose's.
    /// </summary>
    public static (float Width, float Height) Unit(BoxSize rest, float coverAspect)
    {
        var aspect = CoverAspect(rest, coverAspect);
        return aspect >= 1 ? (1, 1 / aspect) : (aspect, 1);
    }

    /// <summary>
    /// A game's box: its front as wide over high as its cover, the larger side filling the envelope (scaled down if
    /// the cover arrived after the envelope was worked out), and as deep as its spine says.
    /// </summary>
    /// <param name="rest">The template's rest size: the shape without a cover or a spine.</param>
    /// <param name="coverAspect">The cover's width over height; 0 or less without one.</param>
    /// <param name="spineAspect">The spine's width over height, which is the box's depth over its height; 0 or less without one.</param>
    /// <param name="envelopeWidth">The widest box in the list (at most 1).</param>
    /// <param name="envelopeHeight">The tallest box in the list (at most 1).</param>
    public static BoxSize Fit(BoxSize rest, float coverAspect, float spineAspect, float envelopeWidth, float envelopeHeight)
    {
        var (width, height) = Unit(rest, coverAspect);
        var scale = 1f;
        if (envelopeWidth > 0 && width > envelopeWidth)
        {
            scale = envelopeWidth / width;
        }

        if (envelopeHeight > 0 && height * scale > envelopeHeight)
        {
            scale = envelopeHeight / height;
        }

        width = Math.Max(width * scale, MinSide);
        height = Math.Max(height * scale, MinSide);
        var depthRatio = spineAspect > 0 && float.IsFinite(spineAspect)
            ? Math.Clamp(spineAspect, MinDepthRatio, MaxDepthRatio)
            : rest.Depth / Math.Max(rest.Height, MinSide);
        return new BoxSize(width, height, Math.Max(height * depthRatio, MinDepth));
    }

    private static float CoverAspect(BoxSize rest, float coverAspect) =>
        coverAspect > 0 && float.IsFinite(coverAspect)
            ? Math.Clamp(coverAspect, MinCoverAspect, MaxCoverAspect)
            : Math.Clamp(rest.Width / Math.Max(rest.Height, MinSide), MinCoverAspect, MaxCoverAspect);
}
