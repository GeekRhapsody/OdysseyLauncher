using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

public sealed class OverlayPaletteTests
{
    private static readonly Rgb Black = new(0, 0, 0);
    private static readonly Rgb DarkGrey = new(0x14, 0x14, 0x14);
    private static readonly Rgb LightGrey = new(0xC8, 0xC8, 0xC8);
    private static readonly Rgb NearWhite = new(0xEC, 0xEC, 0xEC);

    [Fact]
    public void A_theme_that_sets_no_colour_keeps_the_launchers_own_overlay_exactly()
    {
        Assert.Same(OverlayPalette.Legacy, OverlayPalette.For(ThemeMenu.None));
        Assert.Same(OverlayPalette.Legacy, OverlayPalette.For(new ThemeMenu(null, null, null, "C:/themes/x/menu.ttf")));

        // The values InfoOverlay and TitleList had before they followed the theme.
        Assert.Equal(new Rgba(0.35f, 0.5f, 1.0f, 0.55f), OverlayPalette.Legacy.Glow);
        Assert.Equal(new Rgba(0xB8 / 255f, 0xC4 / 255f, 0xE6 / 255f), OverlayPalette.Legacy.Subtitle);
        Assert.Equal(new Rgba(0x9A / 255f, 0xA6 / 255f, 0xCC / 255f), OverlayPalette.Legacy.Hint);
        Assert.Equal(new Rgba(0xC9 / 255f, 0xD0 / 255f, 0xE6 / 255f), OverlayPalette.Legacy.ListPlain);
        Assert.Equal(new Rgba(0x8E / 255f, 0x9C / 255f, 0xC6 / 255f), OverlayPalette.Legacy.ListSystem);
        Assert.Equal(new Rgba(0.16f, 0.24f, 0.62f, 0.7f), OverlayPalette.Legacy.ListFocusBox);
        Assert.Equal(new Rgba(0x8F / 255f, 0xB2 / 255f, 0xFF / 255f), OverlayPalette.Legacy.ListFocusBorder);
        Assert.Equal(new Rgba(0.35f, 0.5f, 1.0f, 0.4f), OverlayPalette.Legacy.ListFocusShadow);
    }

    [Fact]
    public void Setting_a_colour_derives_the_overlay_from_the_same_colours_as_the_menus()
    {
        var menu = new ThemeMenu(DarkGrey, NearWhite, LightGrey, null);
        var overlay = OverlayPalette.For(menu);
        var menus = MenuPalette.For(menu);

        Assert.NotSame(OverlayPalette.Legacy, overlay);
        Assert.Equal(menus.Glow, overlay.Glow);
        Assert.Equal(menus.Dim, overlay.Hint);
        Assert.Equal(menus.Accent, overlay.ListFocusBorder);
    }

    [Fact]
    public void A_grey_theme_gets_a_grey_overlay()
    {
        var overlay = OverlayPalette.Derive(DarkGrey, NearWhite, LightGrey);

        foreach (var colour in new[] { overlay.Glow, overlay.Subtitle, overlay.Hint, overlay.ListPlain, overlay.ListSystem, overlay.ListFocusBox, overlay.ListFocusBorder, overlay.ListFocusShadow })
        {
            Assert.Equal(colour.R, colour.G);
            Assert.Equal(colour.G, colour.B);
        }
    }

    [Theory]
    [MemberData(nameof(Backgrounds))]
    public void The_overlays_text_stays_readable_and_in_order(Rgb background)
    {
        var overlay = OverlayPalette.Derive(background, NearWhite, LightGrey);
        var behind = Rgba.From(background);

        // The list's titles are brighter than the subtitle, which is brighter than the system names.
        Assert.True(overlay.ListPlain.Luminance > overlay.Subtitle.Luminance);
        Assert.True(overlay.Subtitle.Luminance > overlay.ListSystem.Luminance);

        // WCAG 4.5:1 against the background for every line of text.
        foreach (var colour in new[] { overlay.Subtitle, overlay.Hint, overlay.ListPlain, overlay.ListSystem })
        {
            Assert.InRange(Rgba.Contrast(colour, behind), 4.5, 21);
        }
    }

    public static TheoryData<Rgb> Backgrounds() => new(Black, DarkGrey, MenuPalette.DefaultBackground);
}
