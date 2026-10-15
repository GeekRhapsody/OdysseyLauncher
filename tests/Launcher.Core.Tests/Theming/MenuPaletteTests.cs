using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

public sealed class MenuPaletteTests
{
    private static readonly Rgb Black = new(0, 0, 0);
    private static readonly Rgb DarkGrey = new(0x14, 0x14, 0x14);
    private static readonly Rgb LightGrey = new(0xC8, 0xC8, 0xC8);
    private static readonly Rgb NearWhite = new(0xEC, 0xEC, 0xEC);

    [Fact]
    public void A_theme_that_sets_no_colour_keeps_the_launchers_own_menus_exactly()
    {
        Assert.Same(MenuPalette.Legacy, MenuPalette.For(ThemeMenu.None));
        Assert.Same(MenuPalette.Legacy, MenuPalette.For(new ThemeMenu(null, null, null, "C:/themes/x/menu.ttf")));

        // M7's values, as UiStyle had them.
        Assert.Equal(new Rgba(0xEE / 255f, 0xF1 / 255f, 0xFA / 255f), MenuPalette.Legacy.Text);
        Assert.Equal(new Rgba(0.035f, 0.05f, 0.16f, 0.95f), MenuPalette.Legacy.Panel);
        Assert.Equal(new Rgba(0.16f, 0.24f, 0.62f, 0.85f), MenuPalette.Legacy.RowFocus);
    }

    [Fact]
    public void Setting_one_colour_derives_the_rest_from_the_launchers_own()
    {
        var palette = MenuPalette.For(new ThemeMenu(null, NearWhite, null, null));

        Assert.NotSame(MenuPalette.Legacy, palette);
        Assert.Equal(Rgba.From(NearWhite), palette.Text);
        Assert.Equal(Rgba.From(MenuPalette.DefaultBackground, 0.95f), palette.Panel);
        Assert.Equal(Rgba.From(MenuPalette.DefaultAccent), palette.Accent);
    }

    [Theory]
    [MemberData(nameof(Backgrounds))]
    public void Derived_rows_get_lighter_the_more_they_stand_out_and_the_text_stays_readable(Rgb background)
    {
        var palette = MenuPalette.Derive(background, NearWhite, LightGrey);

        Assert.True(palette.RowPlain.Luminance < palette.RowHover.Luminance);
        Assert.True(palette.RowHover.Luminance < palette.RowFocus.Luminance);
        Assert.True(palette.RowFocus.Luminance < palette.RowPressed.Luminance);
        Assert.True(palette.Frame.Luminance <= palette.Panel.Luminance);

        // WCAG: body text 7:1 on the panel, the dim details 4.5:1, the faint notes 3:1; and on a focused row, 4.5:1.
        var panel = palette.Panel.WithAlpha(1);
        Assert.InRange(Rgba.Contrast(palette.Text, panel), 7, 21);
        Assert.InRange(Rgba.Contrast(palette.Dim, panel), 4.5, 21);
        Assert.InRange(Rgba.Contrast(palette.Faint, panel), 3, 21);
        Assert.InRange(Rgba.Contrast(palette.Text, palette.RowFocus.WithAlpha(1)), 4.5, 21);
    }

    [Fact]
    public void A_grey_theme_gets_grey_menus()
    {
        var palette = MenuPalette.Derive(DarkGrey, NearWhite, LightGrey);

        foreach (var colour in new[] { palette.Panel, palette.RowFocus, palette.PanelBorder, palette.Glow, palette.Fill, palette.Dim, palette.Scrim })
        {
            Assert.Equal(colour.R, colour.G);
            Assert.Equal(colour.G, colour.B);
        }
    }

    [Theory]
    [MemberData(nameof(Backgrounds))]
    public void Roles_that_share_a_colour_in_one_palette_share_it_in_every_other(Rgb background)
    {
        // The menus switch palette by mapping each colour shown to the same role's in the new palette, so two roles
        // must be equal in a derived palette exactly where they're equal in the launcher's own.
        var derived = MenuPalette.Derive(background, NearWhite, LightGrey);
        var roles = Enum.GetValues<MenuRole>();
        foreach (var a in roles)
        {
            foreach (var b in roles)
            {
                Assert.True(
                    MenuPalette.Legacy[a] == MenuPalette.Legacy[b] == (derived[a] == derived[b]),
                    $"{a} and {b} are {(MenuPalette.Legacy[a] == MenuPalette.Legacy[b] ? "equal" : "apart")} in the launcher's own palette but not in {background}'s");
            }
        }
    }

    public static TheoryData<Rgb> Backgrounds() => new(Black, DarkGrey, MenuPalette.DefaultBackground);
}
