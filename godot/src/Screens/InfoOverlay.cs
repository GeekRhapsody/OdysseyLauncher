using Godot;

namespace Launcher.App.Screens;

/// <summary>What the overlay shows of the focused game, read off the main thread: whether it's a favourite.</summary>
public sealed record OverlayDetails(long Key, bool Favourite);

/// <summary>
/// The PS2-style text over the grid: the focused item's title top left with a soft glow, what it belongs to under
/// it, "Favourite" top right on a favourite game, and the controls bottom right. A system's and a game's details are on
/// their details screens (Y: <see cref="SystemDetailsPanel"/>, <see cref="GameDetailsPanel"/>). 2D, at the project's
/// base size (1280×800) and stretched, so it's native resolution at 4K.
/// </summary>
public sealed partial class InfoOverlay : CanvasLayer
{
    private const float Margin = 44;

    /// <summary>Kept clear of the title, top right: the status indicators (<see cref="StatusBar"/>), and "Favourite" under them.</summary>
    private const float StatusBarRoom = 250;

    private Control _root = null!;
    private Label _title = null!;
    private Label _subtitle = null!;
    private Label _favourite = null!;
    private Label _hints = null!;
    private Label _status = null!;
    private long _detailsKey = -1;

    public InfoOverlay()
    {
        Layer = 1;
        Name = "Overlay";
    }

    /// <summary>The games' titles, shown in the list layout (left), with the focused game's model beside them.</summary>
    public TitleList List { get; } = new();

    /// <summary>0 = hidden, 1 = shown; for transitions.</summary>
    public float Opacity
    {
        get => _root.Modulate.A;
        set
        {
            if (_root.Modulate.A != value)
            {
                _root.Modulate = new Color(1, 1, 1, value);
            }
        }
    }

    public override void _Ready()
    {
        _root = new Control { MouseFilter = Control.MouseFilterEnum.Ignore };
        _root.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        AddChild(_root);

        _root.AddChild(Scrim(top: true));
        _root.AddChild(Scrim(top: false));

        // The games' titles for the list layout, under the heading and the other text.
        _root.AddChild(List);

        var glow = new Color(0.35f, 0.5f, 1.0f, 0.55f);
        var heading = new VBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore };
        heading.AddThemeConstantOverride("separation", 2);
        heading.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.TopWide);
        heading.OffsetLeft = Margin;
        heading.OffsetRight = -Margin - StatusBarRoom;
        heading.OffsetTop = 26;
        _root.AddChild(heading);

        _title = new Label
        {
            LabelSettings = new LabelSettings { FontSize = 34, FontColor = Colors.White, ShadowColor = glow, ShadowSize = 10, ShadowOffset = Vector2.Zero },
            AutowrapMode = TextServer.AutowrapMode.WordSmart,
            MaxLinesVisible = 2,
            TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis,
            MouseFilter = Control.MouseFilterEnum.Ignore,
        };
        heading.AddChild(_title);

        var subtle = new Color("#B8C4E6");
        _subtitle = new Label
        {
            LabelSettings = new LabelSettings { FontSize = 18, FontColor = subtle, ShadowColor = new Color(0, 0, 0, 0.6f), ShadowSize = 4, ShadowOffset = Vector2.Zero },
            MouseFilter = Control.MouseFilterEnum.Ignore,
        };
        heading.AddChild(_subtitle);

        _favourite = AddLabel(new LabelSettings { FontSize = 18, FontColor = new Color("#FFD66B"), ShadowColor = new Color(1, 0.7f, 0.2f, 0.5f), ShadowSize = 6, ShadowOffset = Vector2.Zero });
        _favourite.Text = "Favourite";
        _favourite.Visible = false;
        _favourite.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.TopRight);
        _favourite.OffsetLeft = -Margin - 150;
        _favourite.OffsetRight = -Margin;
        _favourite.OffsetTop = 56;
        _favourite.OffsetBottom = 82;
        _favourite.HorizontalAlignment = HorizontalAlignment.Right;

        _hints = AddLabel(new LabelSettings { FontSize = 14, FontColor = new Color("#9AA6CC") });
        _hints.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.BottomRight);
        _hints.OffsetLeft = -Margin - 1000;
        _hints.OffsetRight = -Margin;
        _hints.OffsetTop = -40;
        _hints.OffsetBottom = -18;
        _hints.HorizontalAlignment = HorizontalAlignment.Right;

        _status = AddLabel(new LabelSettings { FontSize = 20, FontColor = Colors.White, ShadowColor = glow, ShadowSize = 8, ShadowOffset = Vector2.Zero });
        _status.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.Center);
        _status.OffsetLeft = -400;
        _status.OffsetRight = 400;
        _status.OffsetTop = -20;
        _status.OffsetBottom = 20;
        _status.HorizontalAlignment = HorizontalAlignment.Center;
        _status.AutowrapMode = TextServer.AutowrapMode.WordSmart;
        _status.Visible = false;

        ClearDetails();
    }

    /// <summary>Main thread; no allocation when the strings already exist.</summary>
    public void ShowHeading(string title, string subtitle)
    {
        _title.Text = title;
        _subtitle.Text = subtitle;
    }

    /// <summary>The details belong to the item keyed <paramref name="key"/>; they're dropped if focus has moved on.</summary>
    public void ShowDetails(OverlayDetails details, long focusedKey)
    {
        if (details.Key != focusedKey)
        {
            return;
        }

        _detailsKey = details.Key;
        _favourite.Visible = details.Favourite;
    }

    /// <summary>Hides the details (focus moved; new ones are on their way).</summary>
    public void ClearDetails()
    {
        if (_detailsKey == -2)
        {
            return;
        }

        _detailsKey = -2;
        _favourite.Visible = false;
    }

    public void SetHints(string hints) => _hints.Text = hints;

    /// <summary>A message in the middle of the screen, or null to hide it.</summary>
    public void SetStatus(string? status)
    {
        _status.Visible = status is not null;
        _status.Text = status ?? string.Empty;
    }

    private Label AddLabel(LabelSettings settings)
    {
        var label = new Label { LabelSettings = settings, MouseFilter = Control.MouseFilterEnum.Ignore };
        _root.AddChild(label);
        return label;
    }

    private static TextureRect Scrim(bool top)
    {
        var gradient = new Gradient();
        gradient.SetColor(0, new Color(0, 0, 0.02f, top ? 0.55f : 0));
        gradient.SetColor(1, new Color(0, 0, 0.02f, top ? 0 : 0.6f));
        var texture = new GradientTexture2D { Gradient = gradient, Width = 4, Height = 64, FillFrom = Vector2.Zero, FillTo = new Vector2(0, 1) };
        var rect = new TextureRect { Texture = texture, StretchMode = TextureRect.StretchModeEnum.Scale, MouseFilter = Control.MouseFilterEnum.Ignore };
        rect.SetAnchorsPreset(top ? Control.LayoutPreset.TopWide : Control.LayoutPreset.BottomWide);
        rect.OffsetTop = top ? 0 : -190;
        rect.OffsetBottom = top ? 170 : 0;
        return rect;
    }
}
