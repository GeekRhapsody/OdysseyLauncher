using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

public sealed class BoxShapeTests
{
    // The big box's rest shape, 190 x 240 x 50 mm, with its largest side 1 (A7).
    private static readonly BoxSize Rest = new(190 / 240f, 1, 50 / 240f);

    private const float Tolerance = 1e-5f;

    [Theory]
    [InlineData(0.75f, 0.75f, 1)]       // portrait: as tall as the envelope
    [InlineData(1f, 1, 1)]              // square
    [InlineData(1.25f, 1, 0.8f)]        // landscape: as wide as the envelope
    public void The_front_takes_the_covers_proportions_with_its_larger_side_1(float cover, float width, float height)
    {
        var size = BoxShape.Fit(Rest, cover, 0.2f, 1, 1);

        Assert.Equal(width, size.Width, Tolerance);
        Assert.Equal(height, size.Height, Tolerance);
        Assert.Equal(cover, size.Width / size.Height, Tolerance);
    }

    [Fact]
    public void The_depth_is_the_spines_width_over_height_times_the_boxs_height()
    {
        // ScreenScraper's Game Boy art: a 700 x 700 front and a 98 x 700 spine.
        var square = BoxShape.Fit(Rest, 1, 98 / 700f, 1, 1);
        var landscape = BoxShape.Fit(Rest, 4 / 3f, 0.2f, 1, 1);

        Assert.Equal(0.14f, square.Depth, Tolerance);
        Assert.Equal(0.75f * 0.2f, landscape.Depth, Tolerance);
    }

    [Fact]
    public void A_spine_wider_than_tall_is_the_top_and_the_depth_is_its_height_over_width_times_the_boxs_width()
    {
        // ScreenScraper's SNES art (USA): a 680 x 497 front and a 680 x 97 spine, the box's top.
        var snes = BoxShape.Fit(Rest, 680 / 497f, 680 / 97f, 1, 1);

        Assert.Equal(1, snes.Width, Tolerance);
        Assert.Equal(97 / 680f, snes.Depth, Tolerance);
    }

    [Fact]
    public void Without_a_cover_or_a_spine_the_rest_shape_stands_in()
    {
        var neither = BoxShape.Fit(Rest, 0, 0, 1, 1);
        var noSpine = BoxShape.Fit(Rest, 1, 0, 1, 1);

        Assert.Equal(Rest, neither);
        Assert.Equal(Rest.Depth / Rest.Height, noSpine.Depth / noSpine.Height, Tolerance);
    }

    [Theory]
    [InlineData(0.01f, BoxShape.MinCoverAspect)]
    [InlineData(40f, BoxShape.MaxCoverAspect)]
    [InlineData(float.NaN, 190 / 240f)]
    [InlineData(float.PositiveInfinity, 190 / 240f)]
    public void Cover_aspects_out_of_range_are_clamped_and_broken_ones_ignored(float cover, float expected)
    {
        var size = BoxShape.Fit(Rest, cover, 0.2f, 1, 1);

        Assert.Equal(expected, size.Width / size.Height, 1e-4f);
    }

    [Theory]
    [InlineData(0.001f, BoxShape.MinDepthRatio)]
    [InlineData(0.9f, BoxShape.MaxDepthRatio)]
    [InlineData(1000f, BoxShape.MinDepthRatio)]
    [InlineData(1.2f, BoxShape.MaxDepthRatio)]
    public void Spine_aspects_out_of_range_are_clamped(float spine, float expected)
    {
        // A square cover, so the depth over the height and over the width are the same.
        var size = BoxShape.Fit(Rest, 1, spine, 1, 1);

        Assert.Equal(expected, size.Depth / size.Height, Tolerance);
    }

    [Fact]
    public void A_list_of_portrait_boxes_has_a_narrow_envelope_and_every_box_fits_it()
    {
        float[] covers = [0.7f, 0.75f, 0.8f, 0];
        var (width, height) = Envelope(covers);

        Assert.Equal((0.8f, 1f), (width, height));
        foreach (var cover in covers)
        {
            var size = BoxShape.Fit(Rest, cover, 0.2f, width, height);
            Assert.InRange(size.Width, 0, width + Tolerance);
            Assert.InRange(size.Height, 0, height + Tolerance);
        }
    }

    [Fact]
    public void A_mixed_list_is_as_wide_as_its_widest_box_and_as_tall_as_its_tallest()
    {
        var (width, height) = Envelope([0.7f, 1.6f, 1]);

        Assert.Equal((1f, 1f), (width, height));
    }

    [Fact]
    public void A_cover_wider_than_the_envelope_is_scaled_down_into_it()
    {
        // A landscape cover scraped after a portrait-only list was bound: it keeps its proportions and fits the cells.
        var size = BoxShape.Fit(Rest, 2, 0.2f, 0.8f, 1);

        Assert.Equal(0.8f, size.Width, Tolerance);
        Assert.Equal(0.4f, size.Height, Tolerance);
        Assert.Equal(0.08f, size.Depth, Tolerance);
    }

    [Fact]
    public void A_shape_never_shrinks_past_the_smallest_side_or_depth()
    {
        var size = BoxShape.Fit(Rest, BoxShape.MaxCoverAspect, BoxShape.MinDepthRatio, 0.2f, 1);

        Assert.True(size.Height >= BoxShape.MinSide);
        Assert.True(size.Depth >= BoxShape.MinDepth);
    }

    private static (float Width, float Height) Envelope(float[] covers)
    {
        var width = 0f;
        var height = 0f;
        foreach (var cover in covers)
        {
            var unit = BoxShape.Unit(Rest, cover);
            width = Math.Max(width, unit.Width);
            height = Math.Max(height, unit.Height);
        }

        return (width, height);
    }
}
