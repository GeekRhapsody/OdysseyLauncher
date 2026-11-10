using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Theming;

namespace Launcher.App.Screens;

/// <summary>What the showcase shows of the focused game's metadata, read and formatted off the main thread.</summary>
public sealed record ShowcaseDetails(long Key, string Description, IReadOnlyList<(string Label, string Value)> Fields);

/// <summary>The focused game's images for the showcase, decoded off the main thread; null for one it doesn't have.</summary>
public sealed record ShowcaseArt(long Key, ImageTexture? Logo, ImageTexture? Screenshot, ImageTexture? Hero) : IDisposable
{
    public void Dispose()
    {
        Logo?.Dispose();
        Screenshot?.Dispose();
        Hero?.Dispose();
    }
}

/// <summary>
/// The focused game above the showcase layout's strip of games (<see cref="Grid.GridShape.Showcase"/>): its logo (its
/// title until the logo is in, or if it has none), description and main details on the left, its screenshot on the right,
/// and its hero art behind everything, cross-faded from game to game. The art and the screenshot are in
/// <see cref="Backdrop"/>, on the overlay's layer behind the 3D, as a tall screenshot reaches down to the focused game. Moving the focus dips the old game's details at once; the new game's come when the focus rests. Part of
/// the overlay, at its base size.
/// </summary>
public sealed partial class ShowcasePanel : Control
{
    private const float Margin = 44;
    private const float Top = 100;
    // The column and the screenshot share the width: the first ends and the second starts at these shares of it.
    private const float ColumnShare = 0.44f;
    private const float ScreenShare = 0.46f;
    private const float HeadWidth = 440;
    private const float HeadHeight = 130;
    private const int Separation = 14;

    // Where the panel ends: just above the focused game, whose height is a share of the screen's and which stands on the
    // controls' room, the same at the overlay's base size in every UI size (ItemGrid.Showcase*).
    private const float BottomShare = 0.765f;
    private const float BottomRoom = 84;

    private const double DipSeconds = 0.1;
    private const double LogoSeconds = 0.15;
    private const double HeroSeconds = 0.3;
    private const int MaxFields = 5;

    private static readonly NodePath Alpha = "modulate:a";

    private readonly VBoxContainer _column;
    private readonly Label _name;
    private readonly TextureRect _logo;
    private readonly VBoxContainer _details;
    private readonly Label _description;
    private readonly GridContainer _facts;
    private readonly Label[] _factLabels = new Label[MaxFields];
    private readonly Label[] _factValues = new Label[MaxFields];
    private readonly LabelSettings _factLabelStyle;
    private readonly AspectRatioContainer _screen;
    private readonly TextureRect _screenshot;
    private readonly TextureRect[] _heroes = new TextureRect[2];
    private int _hero;
    private long _artKey = -1;
    private bool _dipped;
    private Tween? _detailsFade;
    private Tween? _screenFade;
    private Tween? _logoFade;
    private Tween? _heroFade;

    public ShowcasePanel()
    {
        Name = "Showcase";
        MouseFilter = MouseFilterEnum.Ignore;
        Visible = false;
        SetAnchorsPreset(LayoutPreset.FullRect);

        Backdrop = new Control { Name = "ShowcaseBackdrop", MouseFilter = MouseFilterEnum.Ignore };
        Backdrop.SetAnchorsPreset(LayoutPreset.FullRect);
        var sideways = Scrim(new Vector2(1, 0), [0, 0.42f, 1], [0.94f, 0.82f, 0.32f]);
        var upwards = Scrim(new Vector2(0, 1), [0, 0.55f, 1], [0.2f, 0.25f, 0.96f]);
        for (var i = 0; i < _heroes.Length; i++)
        {
            _heroes[i] = Hero(sideways, upwards);
            Backdrop.AddChild(_heroes[i]);
        }

        var shadow = new Color(0, 0, 0, 0.7f);
        _column = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        _column.AddThemeConstantOverride("separation", Separation);
        _column.AnchorRight = ColumnShare;
        _column.AnchorBottom = BottomShare;
        _column.OffsetBottom = -BottomRoom;
        _column.OffsetLeft = Margin;
        _column.OffsetTop = Top;
        AddChild(_column);

        var head = new Control { CustomMinimumSize = new Vector2(0, HeadHeight), MouseFilter = MouseFilterEnum.Ignore };
        _column.AddChild(head);
        var nameStyle = new LabelSettings { FontSize = 38, FontColor = Colors.White, ShadowColor = new Color(0, 0, 0, 0.6f), ShadowSize = 4, ShadowOffset = Vector2.Zero };
        _name = new Label
        {
            LabelSettings = nameStyle,
            AutowrapMode = TextServer.AutowrapMode.WordSmart,
            MaxLinesVisible = 2,
            TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis,
            VerticalAlignment = VerticalAlignment.Center,
            MouseFilter = MouseFilterEnum.Ignore,
        };
        _name.SetAnchorsPreset(LayoutPreset.FullRect);
        head.AddChild(_name);
        _logo = new TextureRect
        {
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.Scale,
            MouseFilter = MouseFilterEnum.Ignore,
            Visible = false,
        };
        head.AddChild(_logo);

        _details = new VBoxContainer { SizeFlagsVertical = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        _details.AddThemeConstantOverride("separation", Separation);
        _column.AddChild(_details);
        _description = new Label
        {
            LabelSettings = new LabelSettings { FontSize = 18, FontColor = Colors.White, ShadowColor = shadow, ShadowSize = 3, ShadowOffset = Vector2.Zero },
            AutowrapMode = TextServer.AutowrapMode.WordSmart,
            ClipText = true,
            TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis,
            MouseFilter = MouseFilterEnum.Ignore,
        };
        _details.AddChild(_description);

        _facts = new GridContainer { Columns = 4, MouseFilter = MouseFilterEnum.Ignore };
        _facts.AddThemeConstantOverride("h_separation", 12);
        _facts.AddThemeConstantOverride("v_separation", 6);
        _details.AddChild(_facts);
        _factLabelStyle = new LabelSettings { FontSize = 16, ShadowColor = shadow, ShadowSize = 3, ShadowOffset = Vector2.Zero };
        var factValueStyle = new LabelSettings { FontSize = 16, FontColor = Colors.White, ShadowColor = shadow, ShadowSize = 3, ShadowOffset = Vector2.Zero };
        for (var i = 0; i < MaxFields; i++)
        {
            _factLabels[i] = new Label { LabelSettings = _factLabelStyle, MouseFilter = MouseFilterEnum.Ignore };
            _facts.AddChild(_factLabels[i]);
            _factValues[i] = new Label
            {
                LabelSettings = factValueStyle,

                // The left column's values are the long ones (a date, a genre, a developer): they take what's spare.
                ClipText = i % 2 == 0,
                TextOverrunBehavior = i % 2 == 0 ? TextServer.OverrunBehavior.TrimEllipsis : TextServer.OverrunBehavior.NoTrimming,
                SizeFlagsHorizontal = i % 2 == 0 ? SizeFlags.ExpandFill : SizeFlags.Fill,
                MouseFilter = MouseFilterEnum.Ignore,
            };
            _facts.AddChild(_factValues[i]);
        }

        _screen = new AspectRatioContainer
        {
            StretchMode = AspectRatioContainer.StretchModeEnum.Fit,
            AlignmentHorizontal = AspectRatioContainer.AlignmentMode.End,
            AlignmentVertical = AspectRatioContainer.AlignmentMode.Center,
            MouseFilter = MouseFilterEnum.Ignore,
            Visible = false,
        };
        _screen.AnchorLeft = ScreenShare;
        _screen.AnchorRight = 1;
        _screen.AnchorBottom = BottomShare;
        _screen.OffsetBottom = -BottomRoom;
        _screen.OffsetRight = -Margin;
        _screen.OffsetTop = Top;
        Backdrop.AddChild(_screen);
        var frame = new PanelContainer { MouseFilter = MouseFilterEnum.Ignore };
        var box = new StyleBoxFlat { BgColor = new Color("#0B0F1C"), ShadowColor = new Color(0, 0, 0, 0.6f), ShadowSize = 18 };
        box.SetCornerRadiusAll(4);
        box.SetContentMarginAll(7);
        frame.AddThemeStyleboxOverride("panel", box);
        _screen.AddChild(frame);
        _screenshot = new TextureRect
        {
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
            MouseFilter = MouseFilterEnum.Ignore,
        };
        frame.AddChild(_screenshot);

        _column.Resized += FitDescription;
    }

    /// <summary>The hero art and the screenshot, which the overlay puts on its layer behind the 3D, so the games stand in front of them.</summary>
    public Control Backdrop { get; }

    /// <summary>Main thread: the panel takes the theme's colours (A6 Menus).</summary>
    public void Use(OverlayPalette palette)
    {
        _factLabelStyle.FontColor = UiStyle.Colour(palette.Subtitle);
    }

    /// <summary>Main thread: shows the panel, empty, for a list in the showcase layout.</summary>
    public void Open()
    {
        Visible = true;
        _artKey = -1;
        _dipped = true;
        _details.Modulate = Colors.Transparent;
        _screen.Visible = false;
        _logo.Visible = false;
        _name.Visible = true;
    }

    /// <summary>Main thread: hides the panel; its hero art fades out, then its images are released.</summary>
    public void Close()
    {
        if (!Visible)
        {
            return;
        }

        Visible = false;
        _artKey = -1;
        ShowHero(null);
        SetLogo(null);
        SetScreenshot(null);
    }

    /// <summary>Main thread: the focus moved. The game's title shows at once; its details and images follow when the focus rests.</summary>
    public void Focus(string title)
    {
        _name.Text = title;
        _name.Visible = true;
        _logo.Visible = false;
        _artKey = -1;
        if (!_dipped)
        {
            _dipped = true;
            Fade(ref _detailsFade, _details, 0, DipSeconds);
            Fade(ref _screenFade, _screen, 0, DipSeconds);
        }
    }

    /// <summary>Main thread: the game's details, unless the focus has moved on.</summary>
    public void ShowDetails(ShowcaseDetails details, long focusedKey)
    {
        if (!Visible || details.Key != focusedKey)
        {
            return;
        }

        _description.Text = details.Description;
        for (var i = 0; i < MaxFields; i++)
        {
            var shown = i < details.Fields.Count;
            _factLabels[i].Visible = shown;
            _factValues[i].Visible = shown;
            if (shown)
            {
                _factLabels[i].Text = details.Fields[i].Label;
                _factValues[i].Text = details.Fields[i].Value;
            }
        }

        FitDescription();
        _dipped = false;
        Fade(ref _detailsFade, _details, 1, DipSeconds);
    }

    /// <summary>Whether the images of the game keyed <paramref name="key"/> are the ones shown, so they needn't be read again.</summary>
    public bool HasArt(long key) => _artKey == key;

    /// <summary>Main thread: the shown game's images changed, so the next read of its details reads them again.</summary>
    public void ForgetArt() => _artKey = -1;

    /// <summary>Main thread: takes the game's images, or disposes of them if the focus has moved on.</summary>
    public void ShowArt(ShowcaseArt art, long focusedKey)
    {
        if (!Visible || art.Key != focusedKey)
        {
            art.Dispose();
            return;
        }

        _artKey = art.Key;
        SetLogo(art.Logo);
        SetScreenshot(art.Screenshot);
        ShowHero(art.Hero);
    }

    /// <summary>Main thread, while the game launches: the panel and its hero art fade with the games grid.</summary>
    public void FadeWithGrid(float alpha)
    {
        if (Modulate.A != alpha)
        {
            Modulate = new Color(1, 1, 1, alpha);
            Backdrop.Modulate = Modulate;
        }
    }

    private void SetLogo(ImageTexture? logo)
    {
        var old = _logo.Texture;
        _logo.Texture = logo;
        old?.Dispose();
        _logo.Visible = logo is not null;
        _name.Visible = logo is null;
        if (logo is null)
        {
            return;
        }

        var size = logo.GetSize();
        var fitted = size * Math.Min(HeadWidth / size.X, HeadHeight / size.Y);
        _logo.Size = fitted;
        _logo.Position = new Vector2(0, (HeadHeight - fitted.Y) / 2);
        _logo.Modulate = Colors.Transparent;
        Fade(ref _logoFade, _logo, 1, LogoSeconds);
    }

    private void SetScreenshot(ImageTexture? screenshot)
    {
        var old = _screenshot.Texture;
        _screenshot.Texture = screenshot;
        old?.Dispose();
        _screen.Visible = screenshot is not null;
        if (screenshot is not null)
        {
            _screen.Ratio = (float)screenshot.GetWidth() / screenshot.GetHeight();
            Fade(ref _screenFade, _screen, 1, DipSeconds);
        }
    }

    /// <summary>Cross-fades to <paramref name="hero"/>, or out to the theme's look when it's null. The one faded out is released.</summary>
    private void ShowHero(ImageTexture? hero)
    {
        var from = _heroes[_hero];
        if (hero is null && from.Texture is null)
        {
            return;
        }

        _hero = 1 - _hero;
        var to = _heroes[_hero];
        ReleaseTexture(to);
        to.Texture = hero;
        Backdrop.MoveChild(to, 1);
        _heroFade?.Kill();
        _heroFade = CreateTween();
        _heroFade.SetParallel();
        _heroFade.TweenProperty(to, Alpha, 1f, HeroSeconds);
        _heroFade.TweenProperty(from, Alpha, 0f, HeroSeconds);
        _heroFade.Chain().TweenCallback(Callable.From(ReleaseHiddenHero));
    }

    private void ReleaseHiddenHero() => ReleaseTexture(_heroes[1 - _hero]);

    private static void ReleaseTexture(TextureRect rect)
    {
        var old = rect.Texture;
        rect.Texture = null;
        old?.Dispose();
    }

    private void Fade(ref Tween? tween, CanvasItem item, float alpha, double seconds)
    {
        tween?.Kill();
        tween = CreateTween();
        tween.TweenProperty(item, Alpha, alpha, seconds);
    }

    /// <summary>The description takes the lines it needs, as many as fit above the facts, which sit right under it.</summary>
    private void FitDescription()
    {
        var line = _description.GetLineHeight() + _description.LabelSettings.LineSpacing;
        var room = _column.Size.Y - HeadHeight - (2 * Separation) - _facts.GetCombinedMinimumSize().Y;
        var lines = Math.Clamp(_description.GetLineCount(), 1, Math.Max(1, (int)(room / line)));
        _description.MaxLinesVisible = lines;
        _description.CustomMinimumSize = new Vector2(0, lines * line);
    }

    private static TextureRect Hero(GradientTexture2D sideways, GradientTexture2D upwards)
    {
        var hero = new TextureRect
        {
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.KeepAspectCovered,
            MouseFilter = MouseFilterEnum.Ignore,
            Modulate = Colors.Transparent,
        };
        hero.SetAnchorsPreset(LayoutPreset.FullRect);
        foreach (var scrim in (GradientTexture2D[])[sideways, upwards])
        {
            var rect = new TextureRect
            {
                Texture = scrim,
                ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
                StretchMode = TextureRect.StretchModeEnum.Scale,
                MouseFilter = MouseFilterEnum.Ignore,
            };
            rect.SetAnchorsPreset(LayoutPreset.FullRect);
            hero.AddChild(rect);
        }

        return hero;
    }

    /// <summary>A dark gradient over the art, so the text over it reads: the alphas at the offsets, along the direction.</summary>
    private static GradientTexture2D Scrim(Vector2 direction, float[] offsets, float[] alphas)
    {
        var colours = new Color[alphas.Length];
        for (var i = 0; i < alphas.Length; i++)
        {
            colours[i] = new Color(0.012f, 0.024f, 0.055f, alphas[i]);
        }

        return new GradientTexture2D
        {
            Gradient = new Gradient { Offsets = offsets, Colors = colours },
            Width = direction.X > 0 ? 64 : 4,
            Height = direction.Y > 0 ? 64 : 4,
            FillFrom = Vector2.Zero,
            FillTo = direction,
        };
    }
}
