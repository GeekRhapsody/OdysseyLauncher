namespace Launcher.Core.Theming;

/// <summary>
/// The colours of the text over the grids (A6 Menus): the heading's glow and the line under it, the controls' hints,
/// the centre message's glow, and the list layout's titles. The heading's title stays white on every theme. A theme
/// that sets no menu colour gets <see cref="Legacy"/>, the launcher's own deep blue, exactly; one that sets any gets
/// <see cref="Derive"/> of the same background, text and accent its menus are derived from.
/// </summary>
/// <param name="Glow">The heading's and the focused list title's glow, and the centre message's.</param>
/// <param name="Subtitle">The line under the heading's title: what the focused game belongs to, or a system's maker and year.</param>
/// <param name="Hint">The controls' hints, bottom right.</param>
/// <param name="ListPlain">The list layout's titles but the focused one.</param>
/// <param name="ListSystem">The list layout's system names, beside each title in Favourites, Recently played and All games.</param>
/// <param name="ListFocusBox">The list layout's highlight behind the focused title.</param>
/// <param name="ListFocusBorder">The highlight's border.</param>
/// <param name="ListFocusShadow">The highlight's glow.</param>
public sealed record OverlayPalette(
    Rgba Glow,
    Rgba Subtitle,
    Rgba Hint,
    Rgba ListPlain,
    Rgba ListSystem,
    Rgba ListFocusBox,
    Rgba ListFocusBorder,
    Rgba ListFocusShadow)
{
    /// <summary>The overlay as it was before it followed the theme: kept exactly, so themes without menu colours don't change.</summary>
    public static OverlayPalette Legacy { get; } = new(
        Glow: MenuPalette.Legacy.Glow,
        Subtitle: Hex(0xB8C4E6),
        Hint: MenuPalette.Legacy.Dim,
        ListPlain: Hex(0xC9D0E6),
        ListSystem: Hex(0x8E9CC6),
        ListFocusBox: new(0.16f, 0.24f, 0.62f, 0.7f),
        ListFocusBorder: MenuPalette.Legacy.Accent,
        ListFocusShadow: MenuPalette.Legacy.Glow.WithAlpha(0.4f));

    /// <summary>The overlay for a theme's <c>[ui.menu]</c>: <see cref="Legacy"/> unless it sets a colour, as <see cref="MenuPalette.For"/>.</summary>
    public static OverlayPalette For(ThemeMenu menu)
    {
        ArgumentNullException.ThrowIfNull(menu);
        return menu.SetsColour
            ? Derive(menu.Background ?? MenuPalette.DefaultBackground, menu.Text ?? MenuPalette.DefaultText, menu.Accent ?? MenuPalette.DefaultAccent)
            : Legacy;
    }

    /// <summary>
    /// Every colour from three, as the menus' (<see cref="MenuPalette.Derive"/>): the glows, hints and highlight's border
    /// are the menus' own; the subtitle and the list's text lie between the text and the background, and the highlight
    /// between the background and the accent, by the fractions <see cref="Legacy"/>'s lie at from the launcher's own.
    /// </summary>
    public static OverlayPalette Derive(Rgb background, Rgb text, Rgb accent)
    {
        var menu = MenuPalette.Derive(background, text, accent);
        var b = Rgba.From(background);
        var t = Rgba.From(text);
        return new OverlayPalette(
            Glow: menu.Glow,
            Subtitle: t.Towards(b, 0.18f, 1),
            Hint: menu.Dim,
            ListPlain: t.Towards(b, 0.13f, 1),
            ListSystem: t.Towards(b, 0.35f, 1),
            ListFocusBox: b.Towards(Rgba.From(accent), 0.33f, 0.7f),
            ListFocusBorder: menu.Accent,
            ListFocusShadow: menu.Glow.WithAlpha(0.4f));
    }

    private static Rgba Hex(int rgb) => Rgba.From(new Rgb((byte)(rgb >> 16), (byte)(rgb >> 8), (byte)rgb));
}
