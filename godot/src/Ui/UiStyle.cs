using System.Globalization;
using Godot;

namespace Launcher.App.Ui;

/// <summary>
/// The settings screens' look (M7), built in code once: deep blue translucent panels over the dimmed grid, rows that
/// light up with a soft blue glow when focused, as the PS2 browser's text does. Sizes are at the project's base
/// resolution (1280×800), which the canvas stretches, so they're native at 4K.
/// </summary>
public static class UiStyle
{
    public static readonly Color Text = new("#EEF1FA");
    public static readonly Color Dim = new("#9AA6CC");
    public static readonly Color Faint = new("#5E6894");
    public static readonly Color Accent = new("#8FB2FF");
    public static readonly Color Good = new("#8CE6A6");
    public static readonly Color Warning = new("#FFD66B");
    public static readonly Color Bad = new("#FF8A8A");
    public static readonly Color PanelColour = new(0.035f, 0.05f, 0.16f, 0.95f);
    public static readonly Color Glow = new(0.35f, 0.5f, 1.0f, 0.55f);

    public const int TitleSize = 28;
    public const int RowSize = 20;
    public const int DetailSize = 16;
    public const int HintSize = 14;

    private static Theme? _theme;

    /// <summary>The theme every settings control uses (set on each panel's root).</summary>
    public static Theme Theme => _theme ??= Build();

    public static LabelSettings Title { get; } = new() { FontSize = TitleSize, FontColor = Text, ShadowColor = Glow, ShadowSize = 10, ShadowOffset = Vector2.Zero };

    public static LabelSettings Subtitle { get; } = new() { FontSize = DetailSize, FontColor = Dim };

    public static LabelSettings Hint { get; } = new() { FontSize = HintSize, FontColor = Dim };

    public static LabelSettings Body { get; } = new() { FontSize = 18, FontColor = Text };

    public static LabelSettings Detail { get; } = new() { FontSize = DetailSize, FontColor = Dim };

    public static LabelSettings Section { get; } = new() { FontSize = HintSize, FontColor = Accent };

    public static StyleBoxFlat PanelBox(float radius = 16) => new()
    {
        BgColor = PanelColour,
        BorderColor = new Color("#2E3D86"),
        BorderWidthLeft = 1,
        BorderWidthRight = 1,
        BorderWidthTop = 1,
        BorderWidthBottom = 1,
        CornerRadiusTopLeft = (int)radius,
        CornerRadiusTopRight = (int)radius,
        CornerRadiusBottomLeft = (int)radius,
        CornerRadiusBottomRight = (int)radius,
        ShadowColor = new Color(0, 0, 0.05f, 0.6f),
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
        ShadowColor = glow > 0 ? new Color(0.35f, 0.55f, 1.0f, 0.35f) : Colors.Transparent,
        ShadowSize = glow,
        ContentMarginLeft = 16,
        ContentMarginRight = 16,
        ContentMarginTop = 8,
        ContentMarginBottom = 8,
    };

    public static StyleBoxFlat Focused { get; } = RowBox(new Color(0.16f, 0.24f, 0.62f, 0.85f), Accent, 2, 10);

    public static StyleBoxFlat Hovered { get; } = RowBox(new Color(0.12f, 0.17f, 0.42f, 0.55f));

    public static StyleBoxFlat Plain { get; } = RowBox(new Color(0.08f, 0.11f, 0.3f, 0.35f));

    private static Theme Build()
    {
        var theme = new Theme { DefaultFontSize = RowSize };
        var pressed = RowBox(new Color(0.22f, 0.32f, 0.78f, 0.9f), Accent, 2, 6);
        var disabled = RowBox(new Color(0.05f, 0.07f, 0.2f, 0.3f));
        foreach (var type in (string[])["Button"])
        {
            theme.SetStylebox("normal", type, Plain);
            theme.SetStylebox("hover", type, Hovered);
            theme.SetStylebox("pressed", type, pressed);
            theme.SetStylebox("hover_pressed", type, pressed);
            theme.SetStylebox("disabled", type, disabled);
            theme.SetStylebox("focus", type, Focused);
            theme.SetColor("font_color", type, Text);
            theme.SetColor("font_hover_color", type, Text);
            theme.SetColor("font_focus_color", type, Colors.White);
            theme.SetColor("font_pressed_color", type, Colors.White);
            theme.SetColor("font_hover_pressed_color", type, Colors.White);
            theme.SetColor("font_disabled_color", type, Faint);
            theme.SetFontSize("font_size", type, RowSize);
        }

        theme.SetStylebox("panel", "PanelContainer", PanelBox());
        theme.SetColor("font_color", "Label", Text);
        theme.SetFontSize("font_size", "Label", 18);

        var track = RowBox(new Color(0.06f, 0.09f, 0.25f, 0.9f));
        track.ContentMarginTop = track.ContentMarginBottom = 0;
        var fill = RowBox(new Color("#5B82F0"), default, 0, 6);
        fill.ContentMarginTop = fill.ContentMarginBottom = 0;
        theme.SetStylebox("background", "ProgressBar", track);
        theme.SetStylebox("fill", "ProgressBar", fill);
        theme.SetColor("font_color", "ProgressBar", Text);
        theme.SetFontSize("font_size", "ProgressBar", HintSize);

        var grabber = RowBox(new Color(0.35f, 0.45f, 0.85f, 0.8f));
        grabber.ContentMarginLeft = grabber.ContentMarginRight = 3;
        var scrollTrack = RowBox(new Color(0.05f, 0.07f, 0.2f, 0.5f));
        scrollTrack.ContentMarginLeft = scrollTrack.ContentMarginRight = 3;
        foreach (var type in (string[])["VScrollBar", "HScrollBar"])
        {
            theme.SetStylebox("scroll", type, scrollTrack);
            theme.SetStylebox("grabber", type, grabber);
            theme.SetStylebox("grabber_highlight", type, grabber);
            theme.SetStylebox("grabber_pressed", type, grabber);
        }

        return theme;
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
}
