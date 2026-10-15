namespace Launcher.Core.Theming;

/// <summary>A colour with alpha, each channel 0 to 1 in sRGB, as Godot's UI takes it.</summary>
public readonly record struct Rgba(float R, float G, float B, float A = 1)
{
    public static Rgba From(Rgb colour, float alpha = 1) => new(colour.R / 255f, colour.G / 255f, colour.B / 255f, alpha);

    /// <summary>This colour moved <paramref name="t"/> of the way to <paramref name="to"/> (in sRGB), with <paramref name="alpha"/>.</summary>
    public Rgba Towards(Rgba to, float t, float alpha) =>
        new(R + ((to.R - R) * t), G + ((to.G - G) * t), B + ((to.B - B) * t), alpha);

    public Rgba WithAlpha(float alpha) => this with { A = alpha };

    /// <summary>The WCAG relative luminance, for checking text stays readable.</summary>
    public double Luminance => (0.2126 * Linear(R)) + (0.7152 * Linear(G)) + (0.0722 * Linear(B));

    /// <summary>The WCAG contrast ratio of two opaque colours: 1 (none) to 21 (black on white).</summary>
    public static double Contrast(Rgba a, Rgba b)
    {
        var (light, dark) = a.Luminance > b.Luminance ? (a.Luminance, b.Luminance) : (b.Luminance, a.Luminance);
        return (light + 0.05) / (dark + 0.05);
    }

    private static double Linear(float channel) =>
        channel <= 0.04045 ? channel / 12.92 : Math.Pow((channel + 0.055) / 1.055, 2.4);
}

/// <summary>Each colour of a <see cref="MenuPalette"/>, for code that maps one palette's colours onto another's.</summary>
public enum MenuRole
{
    Text,
    Dim,
    Faint,
    Accent,
    Glow,
    Panel,
    PanelBorder,
    PanelShadow,
    RowPlain,
    RowHover,
    RowFocus,
    RowPressed,
    RowDisabled,
    FocusGlow,
    Frame,
    FrameBorder,
    Field,
    FieldBorder,
    SelectedUnfocused,
    CardFocused,
    CardPlain,
    Track,
    Fill,
    Grabber,
    ScrollTrack,
    Scrim,
    DialogScrim,
    Bar,
}

/// <summary>
/// Every colour the menus draw with (A6 Menus): what <c>Ui/UiStyle</c> puts on its shared style boxes and label settings.
/// A theme that sets no menu colour gets <see cref="Legacy"/>, the launcher's own deep blue, exactly; one that sets any
/// gets <see cref="Derive"/> of its background, text and accent (the launcher's own for those it doesn't set).
/// </summary>
public sealed record MenuPalette(
    Rgba Text,
    Rgba Dim,
    Rgba Faint,
    Rgba Accent,
    Rgba Glow,
    Rgba Panel,
    Rgba PanelBorder,
    Rgba PanelShadow,
    Rgba RowPlain,
    Rgba RowHover,
    Rgba RowFocus,
    Rgba RowPressed,
    Rgba RowDisabled,
    Rgba FocusGlow,
    Rgba Frame,
    Rgba FrameBorder,
    Rgba Field,
    Rgba FieldBorder,
    Rgba SelectedUnfocused,
    Rgba CardFocused,
    Rgba CardPlain,
    Rgba Track,
    Rgba Fill,
    Rgba Grabber,
    Rgba ScrollTrack,
    Rgba Scrim,
    Rgba DialogScrim,
    Rgba Bar)
{
    /// <summary>The launcher's own background, text and accent: <see cref="Legacy"/>'s panel, text and accent.</summary>
    public static readonly Rgb DefaultBackground = new(0x09, 0x0D, 0x29);

    public static readonly Rgb DefaultText = new(0xEE, 0xF1, 0xFA);

    public static readonly Rgb DefaultAccent = new(0x8F, 0xB2, 0xFF);

    /// <summary>The menus as they were before themes could set them (M7): kept exactly, so such themes don't change.</summary>
    public static MenuPalette Legacy { get; } = new(
        Text: Hex(0xEEF1FA),
        Dim: Hex(0x9AA6CC),
        Faint: Hex(0x5E6894),
        Accent: Hex(0x8FB2FF),
        Glow: new(0.35f, 0.5f, 1.0f, 0.55f),
        Panel: new(0.035f, 0.05f, 0.16f, 0.95f),
        PanelBorder: Hex(0x2E3D86),
        PanelShadow: new(0, 0, 0.05f, 0.6f),
        RowPlain: new(0.08f, 0.11f, 0.3f, 0.35f),
        RowHover: new(0.12f, 0.17f, 0.42f, 0.55f),
        RowFocus: new(0.16f, 0.24f, 0.62f, 0.85f),
        RowPressed: new(0.22f, 0.32f, 0.78f, 0.9f),
        RowDisabled: new(0.05f, 0.07f, 0.2f, 0.3f),
        FocusGlow: new(0.35f, 0.55f, 1.0f, 0.35f),
        Frame: new(0.02f, 0.03f, 0.1f, 0.9f),
        FrameBorder: Hex(0x2E3D86),
        Field: new(0.02f, 0.03f, 0.1f, 0.95f),
        FieldBorder: Hex(0x3A4C9A),
        SelectedUnfocused: new(0.12f, 0.17f, 0.42f, 0.7f),
        CardFocused: new(0.1f, 0.15f, 0.4f, 0.45f),
        CardPlain: new(0.06f, 0.09f, 0.25f, 0.3f),
        Track: new(0.06f, 0.09f, 0.25f, 0.9f),
        Fill: Hex(0x5B82F0),
        Grabber: new(0.35f, 0.45f, 0.85f, 0.8f),
        ScrollTrack: new(0.05f, 0.07f, 0.2f, 0.5f),
        Scrim: new(0, 0, 0.03f, 0.62f),
        DialogScrim: new(0, 0, 0.02f, 0.45f),
        Bar: new(0, 0, 0.03f, 0.6f));

    /// <summary>The colour of <paramref name="role"/>.</summary>
    public Rgba this[MenuRole role] => role switch
    {
        MenuRole.Text => Text,
        MenuRole.Dim => Dim,
        MenuRole.Faint => Faint,
        MenuRole.Accent => Accent,
        MenuRole.Glow => Glow,
        MenuRole.Panel => Panel,
        MenuRole.PanelBorder => PanelBorder,
        MenuRole.PanelShadow => PanelShadow,
        MenuRole.RowPlain => RowPlain,
        MenuRole.RowHover => RowHover,
        MenuRole.RowFocus => RowFocus,
        MenuRole.RowPressed => RowPressed,
        MenuRole.RowDisabled => RowDisabled,
        MenuRole.FocusGlow => FocusGlow,
        MenuRole.Frame => Frame,
        MenuRole.FrameBorder => FrameBorder,
        MenuRole.Field => Field,
        MenuRole.FieldBorder => FieldBorder,
        MenuRole.SelectedUnfocused => SelectedUnfocused,
        MenuRole.CardFocused => CardFocused,
        MenuRole.CardPlain => CardPlain,
        MenuRole.Track => Track,
        MenuRole.Fill => Fill,
        MenuRole.Grabber => Grabber,
        MenuRole.ScrollTrack => ScrollTrack,
        MenuRole.Scrim => Scrim,
        MenuRole.DialogScrim => DialogScrim,
        MenuRole.Bar => Bar,
        _ => throw new ArgumentOutOfRangeException(nameof(role)),
    };

    /// <summary>The palette for a theme's <c>[ui.menu]</c>: <see cref="Legacy"/> unless it sets a colour.</summary>
    public static MenuPalette For(ThemeMenu menu)
    {
        ArgumentNullException.ThrowIfNull(menu);
        return menu.SetsColour
            ? Derive(menu.Background ?? DefaultBackground, menu.Text ?? DefaultText, menu.Accent ?? DefaultAccent)
            : Legacy;
    }

    /// <summary>
    /// Every colour from three. Rows and borders lie between the background and the accent, lighter the more they stand
    /// out (plain, hovered, focused, pressed); frames, fields and the dimming behind a menu are the background
    /// darkened; dim and faint text lie between the text and the background. The steps are <see cref="Legacy"/>'s,
    /// measured as fractions of the way from its background to its accent. A few alphas are 0.01 apart from
    /// <see cref="Legacy"/>'s so that no two roles are equal on a black background (a field and the panel, the media
    /// viewer's bar and the panel's shadow) where they're apart in <see cref="Legacy"/>: a switch maps each colour shown
    /// to its role's in the new palette.
    /// </summary>
    public static MenuPalette Derive(Rgb background, Rgb text, Rgb accent)
    {
        var b = Rgba.From(background);
        var t = Rgba.From(text);
        var a = Rgba.From(accent);
        var black = new Rgba(0, 0, 0);
        return new MenuPalette(
            Text: t,
            Dim: t.Towards(b, 0.3f, 1),
            Faint: t.Towards(b, 0.58f, 1),
            Accent: a,
            Glow: b.Towards(a, 0.6f, 0.55f),
            Panel: b.WithAlpha(0.95f),
            PanelBorder: b.Towards(a, 0.3f, 1),
            PanelShadow: b.Towards(black, 0.85f, 0.6f),
            RowPlain: b.Towards(a, 0.11f, 0.35f),
            RowHover: b.Towards(a, 0.2f, 0.55f),
            RowFocus: b.Towards(a, 0.33f, 0.85f),
            RowPressed: b.Towards(a, 0.45f, 0.9f),
            RowDisabled: b.Towards(a, 0.04f, 0.3f),
            FocusGlow: b.Towards(a, 0.6f, 0.35f),
            Frame: b.Towards(black, 0.4f, 0.9f),
            FrameBorder: b.Towards(a, 0.3f, 1),
            Field: b.Towards(black, 0.4f, 0.96f),
            FieldBorder: b.Towards(a, 0.36f, 1),
            SelectedUnfocused: b.Towards(a, 0.2f, 0.7f),
            CardFocused: b.Towards(a, 0.15f, 0.45f),
            CardPlain: b.Towards(a, 0.08f, 0.3f),
            Track: b.Towards(a, 0.08f, 0.9f),
            Fill: b.Towards(a, 0.65f, 1),
            Grabber: b.Towards(a, 0.6f, 0.8f),
            ScrollTrack: b.Towards(a, 0.04f, 0.5f),
            Scrim: b.Towards(black, 0.85f, 0.62f),
            DialogScrim: b.Towards(black, 0.85f, 0.45f),
            Bar: b.Towards(black, 0.9f, 0.61f));
    }

    private static Rgba Hex(int rgb) => Rgba.From(new Rgb((byte)(rgb >> 16), (byte)(rgb >> 8), (byte)rgb));
}
