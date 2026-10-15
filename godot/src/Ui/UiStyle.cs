using System;
using System.Collections.Generic;
using System.Globalization;
using Godot;
using Launcher.Core.Theming;
using Theme = Godot.Theme;

namespace Launcher.App.Ui;

/// <summary>
/// The menus' look (M7), built in code: translucent panels over the dimmed grid, rows that light up with a soft glow
/// when focused, as the PS2 browser's text does. Sizes are at the project's base resolution (1280×800), which the
/// canvas stretches, so they're native at 4K.
/// <para>
/// The colours and the font are the active theme's (A6 Menus, <see cref="MenuPalette"/>): the launcher's own deep blue
/// unless the theme sets its own. <see cref="Apply"/> switches them in place: the shared style boxes and label settings
/// (this class's, and those other classes <see cref="Keep"/>) take the new colours, and the menus shown at the time
/// (under the roots given to <see cref="Follow"/>) have each colour they copied mapped to the same role's new one. A
/// menu built later reads the new colours from here. Good, Warning and Bad mean the same in every theme, so they stay.
/// </para>
/// </summary>
public static class UiStyle
{
    public const int TitleSize = 28;
    public const int RowSize = 20;
    public const int DetailSize = 16;
    public const int HintSize = 14;

    public static readonly Color Good = new("#8CE6A6");
    public static readonly Color Warning = new("#FFD66B");
    public static readonly Color Bad = new("#FF8A8A");

    private static readonly StringName PanelStyle = "panel";
    private static readonly List<Resource> Kept = [];
    private static readonly List<Node> Roots = [];
    private static MenuPalette _palette = MenuPalette.Legacy;
    private static Color[] _colours = ColoursOf(MenuPalette.Legacy);
    private static Font? _font;
    private static Theme? _theme;

    /// <summary>The menus' text.</summary>
    public static Color Text => Colour(MenuRole.Text);

    /// <summary>Details and hints.</summary>
    public static Color Dim => Colour(MenuRole.Dim);

    /// <summary>Notes, placeholders and what's off.</summary>
    public static Color Faint => Colour(MenuRole.Faint);

    /// <summary>The focus's border, section headings and values.</summary>
    public static Color Accent => Colour(MenuRole.Accent);

    /// <summary>The glow around a heading.</summary>
    public static Color Glow => Colour(MenuRole.Glow);

    public static Color PanelColour => Colour(MenuRole.Panel);

    /// <summary>The theme every menu control uses (set on each panel's root).</summary>
    public static Theme Theme => _theme ??= Build();

    /// <summary>The theme's font for the menus, or null for Godot's default.</summary>
    public static Font? Font => _font;

    public static LabelSettings Title { get; } = Keep(new LabelSettings { FontSize = TitleSize, FontColor = Text, ShadowColor = Glow, ShadowSize = 10, ShadowOffset = Vector2.Zero });

    public static LabelSettings Subtitle { get; } = Keep(new LabelSettings { FontSize = DetailSize, FontColor = Dim });

    public static LabelSettings Hint { get; } = Keep(new LabelSettings { FontSize = HintSize, FontColor = Dim });

    public static LabelSettings Body { get; } = Keep(new LabelSettings { FontSize = 18, FontColor = Text });

    public static LabelSettings Detail { get; } = Keep(new LabelSettings { FontSize = DetailSize, FontColor = Dim });

    public static LabelSettings Section { get; } = Keep(new LabelSettings { FontSize = HintSize, FontColor = Accent });

    public static StyleBoxFlat Focused { get; } = Keep(RowBox(Colour(MenuRole.RowFocus), Accent, 2, 10));

    public static StyleBoxFlat Hovered { get; } = Keep(RowBox(Colour(MenuRole.RowHover)));

    public static StyleBoxFlat Plain { get; } = Keep(RowBox(Colour(MenuRole.RowPlain)));

    /// <summary>One colour of the palette in use.</summary>
    public static Color Colour(MenuRole role) => _colours[(int)role];

    /// <summary>A panel's frame: a new box each time, so its caller can change its margins.</summary>
    public static StyleBoxFlat PanelBox(float radius = 16) => new()
    {
        BgColor = PanelColour,
        BorderColor = Colour(MenuRole.PanelBorder),
        BorderWidthLeft = 1,
        BorderWidthRight = 1,
        BorderWidthTop = 1,
        BorderWidthBottom = 1,
        CornerRadiusTopLeft = (int)radius,
        CornerRadiusTopRight = (int)radius,
        CornerRadiusBottomLeft = (int)radius,
        CornerRadiusBottomRight = (int)radius,
        ShadowColor = Colour(MenuRole.PanelShadow),
        ShadowSize = 24,
        ContentMarginLeft = 28,
        ContentMarginRight = 28,
        ContentMarginTop = 22,
        ContentMarginBottom = 18,
    };

    /// <summary>A row's box in one state: transparent, hovered, focused (glowing) or pressed.</summary>
    public static StyleBoxFlat RowBox(Color background, Color border = default, int borderWidth = 0, int glow = 0) => new()
    {
        BgColor = background,
        BorderColor = border,
        BorderWidthLeft = borderWidth,
        BorderWidthRight = borderWidth,
        BorderWidthTop = borderWidth,
        BorderWidthBottom = borderWidth,
        CornerRadiusTopLeft = 8,
        CornerRadiusTopRight = 8,
        CornerRadiusBottomLeft = 8,
        CornerRadiusBottomRight = 8,
        ShadowColor = glow > 0 ? Colour(MenuRole.FocusGlow) : Colors.Transparent,
        ShadowSize = glow,
        ContentMarginLeft = 16,
        ContentMarginRight = 16,
        ContentMarginTop = 8,
        ContentMarginBottom = 8,
    };

    /// <summary>A frame around a picture (a thumbnail, a cover): a new box each time.</summary>
    public static StyleBoxFlat FrameBox() => RowBox(Colour(MenuRole.Frame), Colour(MenuRole.FrameBorder), 1);

    /// <summary>
    /// Keeps <paramref name="resource"/> (a <see cref="LabelSettings"/> or <see cref="StyleBoxFlat"/> made from this
    /// class's colours and held for the session, such as a static one) in step with the palette: <see cref="Apply"/>
    /// maps its colours to the new palette's whether or not a menu shows it then.
    /// </summary>
    public static T Keep<T>(T resource)
        where T : Resource
    {
        Kept.Add(resource);
        return resource;
    }

    /// <summary>A node whose menus <see cref="Apply"/> repaints when the palette changes (the UI layer, the job cards).</summary>
    public static void Follow(Node root) => Roots.Add(root);

    /// <summary>
    /// Main thread: the menus take <paramref name="palette"/>. Nothing happens when it's the one in use, so a theme
    /// switch between themes with the same menus costs nothing; otherwise it walks the menus shown once.
    /// </summary>
    public static void Apply(MenuPalette palette)
    {
        ArgumentNullException.ThrowIfNull(palette);
        if (palette == _palette)
        {
            return;
        }

        var from = _colours;
        var to = ColoursOf(palette);
        _palette = palette;
        _colours = to;

        // A change to the theme, or to a style box in it, tells every control using the theme (each control looks its
        // items up and lays out again): once per box, which made a switch with the settings open a 30-37 ms frame on
        // the export (docs/perf/menus.md). So the theme is silent while they change, and tells them once.
        var theme = _theme;
        theme?.SetBlockSignals(true);
        var seen = new HashSet<Resource>(ReferenceEqualityComparer.Instance);
        foreach (var resource in Kept)
        {
            Remap(resource, from, to, seen);
        }

        if (theme is not null)
        {
            Populate(theme);
            theme.SetBlockSignals(false);
            theme.EmitChanged();
        }

        for (var i = Roots.Count - 1; i >= 0; i--)
        {
            if (GodotObject.IsInstanceValid(Roots[i]))
            {
                Walk(Roots[i], from, to, seen);
            }
            else
            {
                Roots.RemoveAt(i);
            }
        }
    }

    /// <summary>Main thread: the menus' font (null: Godot's default). Every label under <see cref="Theme"/> lays out again.</summary>
    public static void SetFont(Font? font)
    {
        _font = font;
        if (_theme is { } theme)
        {
            theme.DefaultFont = font;
        }
    }

    /// <summary>A label with the given settings that never takes the mouse.</summary>
    public static Label Label(string text, LabelSettings settings, bool wrap = false)
    {
        var label = new Label { Text = text, LabelSettings = settings, MouseFilter = Control.MouseFilterEnum.Ignore };
        if (wrap)
        {
            label.AutowrapMode = TextServer.AutowrapMode.WordSmart;
        }

        return label;
    }

    /// <summary>A byte count for people: "812 KB", "4.7 GB".</summary>
    public static string Size(long bytes) => bytes switch
    {
        < 1024 => string.Create(CultureInfo.InvariantCulture, $"{bytes} B"),
        < 1024 * 1024 => string.Create(CultureInfo.InvariantCulture, $"{bytes / 1024.0:0} KB"),
        < 1024L * 1024 * 1024 => string.Create(CultureInfo.InvariantCulture, $"{bytes / (1024.0 * 1024):0.0} MB"),
        _ => string.Create(CultureInfo.InvariantCulture, $"{bytes / (1024.0 * 1024 * 1024):0.0} GB"),
    };

    private static Theme Build()
    {
        var theme = new Theme { DefaultFontSize = RowSize, DefaultFont = _font };
        Populate(theme);
        return theme;
    }

    /// <summary>Sets the theme's colours; its boxes are made once and kept, so <see cref="Apply"/> recolours them.</summary>
    private static void Populate(Theme theme)
    {
        var first = !theme.HasStylebox("normal", "Button");
        foreach (var type in (string[])["Button"])
        {
            if (first)
            {
                theme.SetStylebox("normal", type, Plain);
                theme.SetStylebox("hover", type, Hovered);
                var pressed = Keep(RowBox(Colour(MenuRole.RowPressed), Accent, 2, 6));
                theme.SetStylebox("pressed", type, pressed);
                theme.SetStylebox("hover_pressed", type, pressed);
                theme.SetStylebox("disabled", type, Keep(RowBox(Colour(MenuRole.RowDisabled))));
                theme.SetStylebox("focus", type, Focused);
                theme.SetFontSize("font_size", type, RowSize);
            }

            theme.SetColor("font_color", type, Text);
            theme.SetColor("font_hover_color", type, Text);
            theme.SetColor("font_focus_color", type, Colors.White);
            theme.SetColor("font_pressed_color", type, Colors.White);
            theme.SetColor("font_hover_pressed_color", type, Colors.White);
            theme.SetColor("font_disabled_color", type, Faint);
        }

        theme.SetColor("font_color", "Label", Text);
        theme.SetColor("font_color", "ProgressBar", Text);
        if (!first)
        {
            return;
        }

        theme.SetStylebox("panel", "PanelContainer", Keep(PanelBox()));
        theme.SetFontSize("font_size", "Label", 18);

        var track = Keep(RowBox(Colour(MenuRole.Track)));
        track.ContentMarginTop = track.ContentMarginBottom = 0;
        var fill = Keep(RowBox(Colour(MenuRole.Fill), default, 0, 6));
        fill.ContentMarginTop = fill.ContentMarginBottom = 0;
        theme.SetStylebox("background", "ProgressBar", track);
        theme.SetStylebox("fill", "ProgressBar", fill);
        theme.SetFontSize("font_size", "ProgressBar", HintSize);

        var grabber = Keep(RowBox(Colour(MenuRole.Grabber)));
        grabber.ContentMarginLeft = grabber.ContentMarginRight = 3;
        var scrollTrack = Keep(RowBox(Colour(MenuRole.ScrollTrack)));
        scrollTrack.ContentMarginLeft = scrollTrack.ContentMarginRight = 3;
        foreach (var type in (string[])["VScrollBar", "HScrollBar"])
        {
            theme.SetStylebox("scroll", type, scrollTrack);
            theme.SetStylebox("grabber", type, grabber);
            theme.SetStylebox("grabber_highlight", type, grabber);
            theme.SetStylebox("grabber_pressed", type, grabber);
        }
    }

    private static Color[] ColoursOf(MenuPalette palette)
    {
        var roles = Enum.GetValues<MenuRole>();
        var colours = new Color[roles.Length];
        foreach (var role in roles)
        {
            var c = palette[role];
            colours[(int)role] = new Color(c.R, c.G, c.B, c.A);
        }

        return colours;
    }

    /// <summary>The new palette's colour for the role <paramref name="colour"/> had in the old one; anything else as it is.</summary>
    private static Color Map(Color colour, Color[] from, Color[] to)
    {
        for (var i = 0; i < from.Length; i++)
        {
            if (from[i] == colour)
            {
                return to[i];
            }
        }

        return colour;
    }

    private static void Remap(Resource resource, Color[] from, Color[] to, HashSet<Resource> seen)
    {
        if (!seen.Add(resource))
        {
            return;
        }

        // Each property set tells every control using the resource (a label lays its text out again), so the sets are
        // made silently and the controls told once, and only when a colour changed.
        resource.SetBlockSignals(true);
        var changed = false;
        switch (resource)
        {
            case LabelSettings settings:
                (settings.FontColor, changed) = Mapped(settings.FontColor, from, to, changed);
                (settings.ShadowColor, changed) = Mapped(settings.ShadowColor, from, to, changed);
                break;
            case StyleBoxFlat box:
                (box.BgColor, changed) = Mapped(box.BgColor, from, to, changed);
                (box.BorderColor, changed) = Mapped(box.BorderColor, from, to, changed);
                (box.ShadowColor, changed) = Mapped(box.ShadowColor, from, to, changed);
                break;
        }

        resource.SetBlockSignals(false);
        if (changed)
        {
            resource.EmitChanged();
        }
    }

    private static (Color Colour, bool Changed) Mapped(Color colour, Color[] from, Color[] to, bool changed)
    {
        var mapped = Map(colour, from, to);
        return (mapped, changed || mapped != colour);
    }

    /// <summary>The menus shown: each label's settings, each frame and each dimming rectangle, and a redraw for those drawn in code.</summary>
    private static void Walk(Node node, Color[] from, Color[] to, HashSet<Resource> seen)
    {
        switch (node)
        {
            case Label { LabelSettings: { } settings }:
                Remap(settings, from, to, seen);
                break;
            case ColorRect rect when Map(rect.Color, from, to) is var mapped && mapped != rect.Color:
                rect.Color = mapped;
                break;
        }

        if (node is Control control)
        {
            if (control.HasThemeStyleboxOverride(PanelStyle) && control.GetThemeStylebox(PanelStyle) is { } box)
            {
                Remap(box, from, to, seen);
            }

            control.QueueRedraw();
        }

        foreach (var child in node.GetChildren(includeInternal: true))
        {
            Walk(child, from, to, seen);
        }
    }
}
