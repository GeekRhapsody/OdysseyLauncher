using Godot;
using Launcher.App.Grid;
using Launcher.App.Theming;
using Launcher.App.Ui;
using Launcher.Core.Theming;

namespace Launcher.App.Screens;

/// <summary>
/// The PS2-style text over the grid: the focused item's title top left and under it a subtitle (a game's system, then
/// "Favourite" after a separator for a favourite), and the controls bottom right. A system's and a game's details are on their details
/// screens (Y: <see cref="SystemDetailsPanel"/>, <see cref="GameDetailsPanel"/>). 2D, at the project's base size
/// (1280×800) and stretched, so it's native resolution at 4K. Its colours are the theme's (<see cref="OverlayPalette"/>,
/// from <c>[ui.menu]</c>): the launcher's own blue unless the theme sets menu colours.
/// </summary>
public sealed partial class InfoOverlay : CanvasLayer
{
    private const float Margin = 44;

    /// <summary>Kept clear of the title, top right: the status indicators (<see cref="StatusBar"/>).</summary>
    private const float StatusBarRoom = 250;

    private Control _root = null!;
    private CanvasLayer _behind = null!;
    private Control _behindRoot = null!;
    private int _listIndex;
    private int _gameLabelsIndex;
    private int _showcaseIndex;
    private bool _titlesBehind;
    private TextureRect _bottomScrim = null!;
    private Label _title = null!;
    private Label _subtitle = null!;
    private Label _favouriteSeparator = null!;
    private Label _favourite = null!;
    private HintBar _hints = null!;
    private Label _status = null!;
    private OverlayPalette _palette = OverlayPalette.Legacy;

    public InfoOverlay()
    {
        Layer = 1;
        Name = "Overlay";
    }

    /// <summary>The games' titles, shown in the list layout (left), with the focused game's model beside them.</summary>
    public TitleList List { get; } = new();

    /// <summary>The focused game's art and details, above the showcase layout's strip of games.</summary>
    public ShowcasePanel Showcase { get; } = new();

    /// <summary>The systems' names under their cards, in the grid with labels.</summary>
    public GridLabels SystemLabels { get; } = new("SystemLabels");

    /// <summary>The games' titles under their models, in the grid with labels.</summary>
    public GridLabels GameLabels { get; } = new("GameLabels");

    /// <summary>
    /// Main thread: whether the games' titles (the list of titles, the labels under the games, the showcase's text) are drawn behind
    /// the 3D, on a background canvas layer (<see cref="LookStage.BackgroundLayer"/>), so an inspected game stands in
    /// front of them; otherwise they're with the rest of the overlay's text, in front. Behind, they're drawn through the
    /// 3D's buffer, so they're a little softer when the 3D is rendered below the window's resolution. Moves them only
    /// when the value changes.
    /// </summary>
    public bool TitlesBehind
    {
        get => _titlesBehind;
        set
        {
            if (_titlesBehind == value)
            {
                return;
            }

            _titlesBehind = value;
            List.GetParent().RemoveChild(List);
            GameLabels.GetParent().RemoveChild(GameLabels);
            Showcase.GetParent().RemoveChild(Showcase);
            if (value)
            {
                _behindRoot.AddChild(GameLabels);
                _behindRoot.AddChild(List);
                _behindRoot.AddChild(Showcase);
            }
            else
            {
                // Back where they were: the labels under the scrims, and the list over them and under the heading.
                _root.AddChild(GameLabels);
                _root.MoveChild(GameLabels, _gameLabelsIndex);
                _root.AddChild(List);
                _root.MoveChild(List, _listIndex);
                _root.AddChild(Showcase);
                _root.MoveChild(Showcase, _showcaseIndex);
            }
        }
    }

    /// <summary>Main thread, once a frame, after the grids' ticks: the labels under their items, where the grids' layouts have them.</summary>
    public void UpdateLabels(ItemGrid systems, ItemGrid games)
    {
        SystemLabels.Update(systems);
        GameLabels.Update(games);
    }

    /// <summary>0 = hidden, 1 = shown; for transitions.</summary>
    public float Opacity
    {
        get => _root.Modulate.A;
        set
        {
            if (_root.Modulate.A != value)
            {
                _root.Modulate = new Color(1, 1, 1, value);
                _behindRoot.Modulate = _root.Modulate;
            }
        }
    }

    public override void _Ready()
    {
        _root = new Control { MouseFilter = Control.MouseFilterEnum.Ignore };
        _root.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        AddChild(_root);

        // The labels under the grids' items darken under the scrims, as their items do.
        _root.AddChild(SystemLabels);
        _root.AddChild(GameLabels);
        _gameLabelsIndex = GameLabels.GetIndex();
        _root.AddChild(Scrim(top: true));
        _bottomScrim = Scrim(top: false);
        _root.AddChild(_bottomScrim);

        // The games' titles for the list layout, under the heading and the other text. While a game is inspected they go
        // behind the 3D (TitlesBehind), with the games' labels, on a layer that's shown and hidden with this one.
        _root.AddChild(List);
        _listIndex = List.GetIndex();
        _root.AddChild(Showcase);
        _showcaseIndex = Showcase.GetIndex();
        _behind = new CanvasLayer { Layer = LookStage.BackgroundLayer, Name = "OverlayBehind" };
        _behind.Visible = Visible;
        _behindRoot = new Control { MouseFilter = Control.MouseFilterEnum.Ignore };
        _behindRoot.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _behindRoot.AddChild(Showcase.Backdrop);
        _behind.AddChild(_behindRoot);
        AddChild(_behind);
        VisibilityChanged += () => _behind.Visible = Visible;

        // The colours that follow the theme are set by Paint, below.
        var heading = new VBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore };
        heading.AddThemeConstantOverride("separation", 2);
        heading.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.TopWide);
        heading.OffsetLeft = Margin;
        heading.OffsetRight = -Margin - StatusBarRoom;
        heading.OffsetTop = 26;
        _root.AddChild(heading);

        _title = new Label
        {
            LabelSettings = new LabelSettings { FontSize = 34, FontColor = Colors.White, ShadowColor = new Color(0, 0, 0, 0.6f), ShadowSize = 4, ShadowOffset = Vector2.Zero },
            AutowrapMode = TextServer.AutowrapMode.WordSmart,
            MaxLinesVisible = 2,
            TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis,
            MouseFilter = Control.MouseFilterEnum.Ignore,
        };
        heading.AddChild(_title);

        // The subtitle's parts share one LabelSettings, so Paint colours them together; "Favourite" keeps its own gold.
        var subtitleRow = new HBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore };
        subtitleRow.AddThemeConstantOverride("separation", 0);
        heading.AddChild(subtitleRow);
        var subtitleSettings = new LabelSettings { FontSize = 18, ShadowColor = new Color(0, 0, 0, 0.6f), ShadowSize = 4, ShadowOffset = Vector2.Zero };
        _subtitle = new Label { LabelSettings = subtitleSettings, MouseFilter = Control.MouseFilterEnum.Ignore };
        _favouriteSeparator = new Label { LabelSettings = subtitleSettings, Text = " · ", MouseFilter = Control.MouseFilterEnum.Ignore };
        _favourite = new Label
        {
            LabelSettings = new LabelSettings { FontSize = 18, FontColor = new Color("#FFD66B"), ShadowColor = new Color(1, 0.7f, 0.2f, 0.5f), ShadowSize = 6, ShadowOffset = Vector2.Zero },
            Text = "Favourite",
            MouseFilter = Control.MouseFilterEnum.Ignore,
        };
        subtitleRow.AddChild(_subtitle);
        subtitleRow.AddChild(_favouriteSeparator);
        subtitleRow.AddChild(_favourite);

        _hints = new HintBar(new LabelSettings { FontSize = UiStyle.ControlsSize });
        _root.AddChild(_hints);
        _hints.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.BottomRight);
        _hints.OffsetLeft = -Margin - 1000;
        _hints.OffsetRight = -Margin;
        _hints.OffsetTop = -48;
        _hints.OffsetBottom = -16;

        _status = AddLabel(new LabelSettings { FontSize = 20, FontColor = Colors.White, ShadowColor = new Color(0, 0, 0, 0.6f), ShadowSize = 4, ShadowOffset = Vector2.Zero });
        _status.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.Center);
        _status.OffsetLeft = -400;
        _status.OffsetRight = 400;
        _status.OffsetTop = -20;
        _status.OffsetBottom = 20;
        _status.HorizontalAlignment = HorizontalAlignment.Center;
        _status.AutowrapMode = TextServer.AutowrapMode.WordSmart;
        _status.Visible = false;

        Paint();
        ShowFavourite(false);
    }

    /// <summary>
    /// Main thread: the overlay takes <paramref name="palette"/>'s colours (the theme's, A6 Menus). Nothing happens when
    /// it's the one in use; otherwise a few colours are set, and the labels lay out once at the next draw.
    /// </summary>
    public void Use(OverlayPalette palette)
    {
        if (palette == _palette)
        {
            return;
        }

        _palette = palette;
        if (IsNodeReady())
        {
            Paint();
        }
    }

    /// <summary>Main thread; no allocation when the strings already exist.</summary>
    public void ShowHeading(string title, string subtitle)
    {
        _title.Text = title;
        _subtitle.Text = subtitle;
        if (Showcase.Visible)
        {
            Showcase.Focus(title);
        }
    }

    /// <summary>
    /// Main thread: shows or hides the showcase layout's panel. Its logo, or the title in the logo's place, stands for the
    /// heading's title, and its strip of games stands where the bottom scrim would darken it.
    /// </summary>
    public void ShowShowcase(bool shown)
    {
        _title.Visible = !shown;
        _bottomScrim.Visible = !shown;
        if (shown)
        {
            Showcase.Open();
        }
        else
        {
            Showcase.Close();
        }
    }

    /// <summary>Main thread: "Favourite" at the end of the subtitle, or not.</summary>
    public void ShowFavourite(bool favourite)
    {
        _favouriteSeparator.Visible = favourite;
        _favourite.Visible = favourite;
    }

    /// <summary>Main thread: the controls' hints, bottom right (nothing happens when they're the ones shown).</summary>
    public void SetHints(Hint[] hints) => _hints.Show(hints);

    /// <summary>A message in the middle of the screen, or null to hide it.</summary>
    public void SetStatus(string? status)
    {
        _status.Visible = status is not null;
        _status.Text = status ?? string.Empty;
    }

    private void Paint()
    {
        _subtitle.LabelSettings.FontColor = UiStyle.Colour(_palette.Subtitle);
        _hints.Settings.FontColor = UiStyle.Colour(_palette.Hint);
        List.Use(_palette);
        Showcase.Use(_palette);
        SystemLabels.Use(_palette);
        GameLabels.Use(_palette);
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
