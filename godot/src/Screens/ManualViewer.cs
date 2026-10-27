using System;
using System.Globalization;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Theming;

namespace Launcher.App.Screens;

/// <summary>
/// A game's manual at the window's full size, on black (A on its card on the details screen), a page at a time through
/// <see cref="ManualPages"/>. Left and right (or up and down) turn the page, the shoulders ten pages, the triggers (or
/// Home and End) go to the first and last; A or R3 zooms the page to the window's width, where up and down, the right
/// stick and the mouse wheel scroll it, and scrolling on past its end turns the page. B or Y goes back. Until a page's
/// render comes, the page shows as it was rendered last (zoomed, its whole page scaled up). The caption fades after a
/// few seconds and comes back with any button. Nothing in <see cref="Tick"/> allocates.
/// </summary>
public sealed partial class ManualViewer : UiPanel
{
    private const double CaptionSeconds = 3;
    private const float CaptionFade = 0.4f;
    private const float StepFraction = 0.2f;
    private const float StickSpeed = 2400;

    private readonly ManualPages? _pages;
    private readonly string _name;
    private readonly Control _area;
    private readonly TextureRect _page;
    private readonly Label _message;
    private readonly Control _caption;
    private readonly Label _place;
    private readonly Label _controls;
    // The texture _page shows, kept here rather than read back from it: ManualPages frees a page's texture, wrapper
    // and all, when it's no longer wanted, and reading back a freed wrapper's texture makes a new wrapper holding it.
    private ImageTexture? _shown;
    private int _index;
    private int _knownCount;
    private bool _zoomed;
    private float _scroll;
    private float _maxScroll;
    private Vector2 _shownArea;
    private Message _shownMessage = Message.Unset;
    private double _captionAge;

    public ManualViewer(UiContext ui, string path, string name)
        : base(name, Vector2.Zero, PanelPlacement.FullScreen)
    {
        _name = name;
        _area = new Control { SizeFlagsVertical = SizeFlags.ExpandFill, SizeFlagsHorizontal = SizeFlags.ExpandFill, ClipContents = true, MouseFilter = MouseFilterEnum.Stop };
        _area.GuiInput += OnAreaInput;
        Body.AddChild(_area);
        _page = new TextureRect
        {
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.Scale,
            MouseFilter = MouseFilterEnum.Ignore,
        };
        _area.AddChild(_page);

        _message = UiStyle.Label(string.Empty, new LabelSettings { FontSize = UiStyle.RowSize, FontColor = UiStyle.Dim }, wrap: true);
        _message.SetAnchorsPreset(LayoutPreset.Center);
        _message.OffsetLeft = -420;
        _message.OffsetRight = 420;
        _message.OffsetTop = -40;
        _message.OffsetBottom = 40;
        _message.HorizontalAlignment = HorizontalAlignment.Center;
        _message.VerticalAlignment = VerticalAlignment.Center;
        _area.AddChild(_message);

        // The caption: what it is, which page of how many, and the controls.
        var bar = new PanelContainer { MouseFilter = MouseFilterEnum.Ignore };
        var barBox = new StyleBoxFlat { BgColor = UiStyle.Colour(MenuRole.Bar), ContentMarginLeft = 24, ContentMarginRight = 24, ContentMarginTop = 10, ContentMarginBottom = 12 };
        bar.AddThemeStyleboxOverride("panel", barBox);
        bar.SetAnchorsPreset(LayoutPreset.BottomWide);
        bar.GrowVertical = GrowDirection.Begin;
        _area.AddChild(bar);
        _caption = bar;
        var line = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        line.AddThemeConstantOverride("separation", 16);
        bar.AddChild(line);
        line.AddChild(UiStyle.Label(name, new LabelSettings { FontSize = UiStyle.RowSize, FontColor = UiStyle.Text, ShadowColor = UiStyle.Glow, ShadowSize = 6, ShadowOffset = Vector2.Zero }));
        _place = UiStyle.Label(string.Empty, UiStyle.Detail);
        _place.SizeFlagsHorizontal = SizeFlags.ExpandFill;
        _place.VerticalAlignment = VerticalAlignment.Center;
        line.AddChild(_place);
        _controls = UiStyle.Label(string.Empty, UiStyle.Hint);
        _controls.VerticalAlignment = VerticalAlignment.Center;
        line.AddChild(_controls);

        if (ui.Pdf is { } renderer)
        {
            _pages = new ManualPages(renderer, path, ui.Queue);
            _pages.Changed += OnPagesChanged;
        }

        UpdateCaption();
    }

    private enum Message
    {
        Unset,
        None,
        Loading,
        Error,
    }

    public override Control? DefaultFocus => null;

    public override bool Handle(NavCommand command)
    {
        _captionAge = 0;
        switch (command)
        {
            case NavCommand.Left:
                Turn(-1, toBottom: false);
                return true;
            case NavCommand.Right:
                Turn(1, toBottom: false);
                return true;
            case NavCommand.Up:
                Scroll(-1);
                return true;
            case NavCommand.Down:
                Scroll(1);
                return true;
            case NavCommand.PageUp:
                Turn(-10, toBottom: false);
                return true;
            case NavCommand.PageDown:
                Turn(10, toBottom: false);
                return true;
            case NavCommand.First or NavCommand.LetterPrevious:
                Turn(-_index, toBottom: false);
                return true;
            case NavCommand.Last or NavCommand.LetterNext:
                Turn(int.MaxValue / 2, toBottom: false);
                return true;
            case NavCommand.Accept or NavCommand.Inspect:
                _zoomed = !_zoomed;
                _scroll = 0;
                Request();
                UpdateCaption();
                return true;
            case NavCommand.Secondary:
                Close();
                return true;
            case NavCommand.Back or NavCommand.Menu:
                return false;
            default:
                // Nothing else here, and no focus to move.
                return true;
        }
    }

    public override void Tick(double delta)
    {
        base.Tick(delta);
        var area = _area.Size;
        if (area != _shownArea)
        {
            _shownArea = area;
            Request();
        }

        // The right stick scrolls a zoomed page, faster the further it's pushed (the push squared, as it turns items).
        if (_zoomed)
        {
            var stick = NavInput.ReadTurn().Y;
            if (stick != 0)
            {
                _scroll += stick * Math.Abs(stick) * StickSpeed * (float)delta;
                _captionAge = 0;
            }
        }

        Place(area);

        // The caption stays while the page is loading or can't be shown; otherwise it fades.
        var holding = _shown is null;
        _captionAge = holding ? 0 : _captionAge + delta;
        var alpha = (float)Math.Clamp(1 - (_captionAge - CaptionSeconds) / CaptionFade, 0, 1);
        if (_caption.Modulate.A != alpha)
        {
            _caption.Modulate = new Color(1, 1, 1, alpha);
        }
    }

    public override void OnClosed()
    {
        _area.GuiInput -= OnAreaInput;
        _page.Texture = null;
        _shown = null;
        _pages?.Dispose();
    }

    /// <summary>Shows the best render there is of the page, fitted or zoomed, and says why when there's none.</summary>
    private void Place(Vector2 area)
    {
        ManualPages.Page page = default;
        var found = _pages is not null && (_pages.TryGet(_index, _zoomed, out page) || (_zoomed && _pages.TryGet(_index, false, out page)));
        var texture = found ? page.Texture : null;
        if (_shown != texture)
        {
            _shown = texture;
            _page.Texture = texture;
        }

        ShowMessage(_pages is null || _pages.Error is not null ? Message.Error : texture is null ? Message.Loading : Message.None);
        if (texture is null || area.X <= 0 || area.Y <= 0 || page.Aspect <= 0)
        {
            return;
        }

        Vector2 size;
        Vector2 at;
        if (_zoomed)
        {
            size = new Vector2(area.X, area.X / page.Aspect);
            _maxScroll = Math.Max(0, size.Y - area.Y);
            _scroll = Math.Clamp(_scroll, 0, _maxScroll);
            at = new Vector2(0, size.Y <= area.Y ? (area.Y - size.Y) / 2 : -_scroll);
        }
        else
        {
            var scale = Math.Min(area.X / page.Aspect, area.Y);
            size = new Vector2(scale * page.Aspect, scale);
            at = (area - size) / 2;
            _maxScroll = 0;
        }

        if (_page.Size != size)
        {
            _page.Size = size;
        }

        if (_page.Position != at)
        {
            _page.Position = at;
        }
    }

    private void ShowMessage(Message message)
    {
        if (message == _shownMessage)
        {
            return;
        }

        _shownMessage = message;
        _message.Text = message switch
        {
            Message.Loading => "Loading…",
            Message.Error => _pages is null ? ManualPages.Unsupported : $"This manual can't be opened: {_pages.Error}.",
            _ => string.Empty,
        };
    }

    /// <summary>Up or down: scrolls a zoomed page (past its end, turns it), or turns a whole one.</summary>
    private void Scroll(int direction)
    {
        if (!_zoomed)
        {
            Turn(direction, toBottom: false);
            return;
        }

        if (direction > 0 ? _scroll >= _maxScroll - 0.5f : _scroll <= 0.5f)
        {
            Turn(direction, toBottom: direction < 0);
            return;
        }

        _scroll += direction * _area.Size.Y * StepFraction;
    }

    private void Turn(int pages, bool toBottom)
    {
        var count = _pages?.PageCount ?? 0;
        if (count == 0)
        {
            return;
        }

        var target = (int)Math.Clamp((long)_index + pages, 0, count - 1);
        if (target == _index)
        {
            return;
        }

        _index = target;
        _scroll = toBottom ? float.MaxValue : 0;
        Request();
        UpdateCaption();
    }

    /// <summary>Asks for the page at the area's size in pixels (the window's, which the UI's stretch may scale).</summary>
    private void Request()
    {
        if (_pages is null || _shownArea.X <= 0 || _shownArea.Y <= 0)
        {
            return;
        }

        var visible = GetViewportRect().Size;
        var scale = visible.Y > 0 ? DisplayServer.WindowGetSize().Y / visible.Y : 1;
        _pages.Show(_index, new Vector2I((int)Math.Round(_shownArea.X * scale), (int)Math.Round(_shownArea.Y * scale)), _zoomed);
    }

    private void UpdateCaption()
    {
        var count = _pages?.PageCount ?? 0;
        _place.Text = count > 0 ? string.Create(CultureInfo.InvariantCulture, $"Page {_index + 1} of {count}") : string.Empty;
        _controls.Text = count == 0
            ? "B  Back"
            : _zoomed
                ? "Up Down  Scroll     Left Right  Page     A  Whole page     B  Back"
                : (count > 1 ? "Left Right  Page     LB RB  Ten pages     " : string.Empty) + "A  Zoom     B  Back";
    }

    /// <summary>A page arrived, or the document opened or failed.</summary>
    private void OnPagesChanged()
    {
        var count = _pages?.PageCount ?? 0;
        if (count == _knownCount)
        {
            return;
        }

        // The count arrives with the document: the pages were asked for before it, the neighbour past the end too.
        _knownCount = count;
        Request();
        UpdateCaption();
    }

    /// <summary>The mouse wheel scrolls (or turns the page), as up and down do.</summary>
    private void OnAreaInput(InputEvent @event)
    {
        if (@event is InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelUp or MouseButton.WheelDown } wheel)
        {
            _captionAge = 0;
            Scroll(wheel.ButtonIndex == MouseButton.WheelDown ? 1 : -1);
            _area.AcceptEvent();
        }
    }
}
