using System;
using Godot;
using Launcher.App.Navigation;
using Launcher.Core.Theming;

namespace Launcher.App.Ui;

/// <summary>Where a panel sits on the screen.</summary>
public enum PanelPlacement
{
    Centre,

    /// <summary>Along the bottom (the on-screen keyboard, so the field it types into can stay in view).</summary>
    Bottom,

    /// <summary>The whole window, on black, with no header or hints (the game details screen's image and video viewer).</summary>
    FullScreen,
}

/// <summary>
/// One screen or dialog of the settings UI (M7), stacked on a <see cref="UiLayer"/>: a framed panel with a title, a
/// body the subclass fills, a status line and the controls' hints. Every panel is driven the same way: D-pad or
/// arrows move the focus, A or Enter activates, B or Escape goes back; the mouse clicks and scrolls, but there's no
/// button for going back (the launcher is for a pad). A panel can take commands first (<see cref="Handle"/>) for its own controls.
/// </summary>
public abstract partial class UiPanel : Control
{
    private readonly Label _title;
    private readonly Label _subtitle;
    private readonly Label _status;
    private readonly HintBar _hints;
    private readonly Vector2 _size;
    private readonly bool _bottom;
    private readonly Control? _holder;
    private double _statusClearAt = -1;
    private double _clock;

    protected UiPanel(string title, Vector2 size, PanelPlacement placement = PanelPlacement.Centre, bool dimBelow = false)
    {
        Name = GetType().Name;
        Theme = UiStyle.Theme;
        IsDialog = dimBelow;
        FullScreen = placement == PanelPlacement.FullScreen;
        SetAnchorsPreset(LayoutPreset.FullRect);
        MouseFilter = MouseFilterEnum.Ignore;

        if (dimBelow)
        {
            // A dialog over another panel: the panel below is darkened, and doesn't take clicks.
            var dim = new ColorRect { Color = UiStyle.Colour(MenuRole.DialogScrim), MouseFilter = MouseFilterEnum.Stop };
            dim.SetAnchorsPreset(LayoutPreset.FullRect);
            AddChild(dim);
        }

        if (FullScreen)
        {
            Frame = new PanelContainer { MouseFilter = MouseFilterEnum.Stop };
            Frame.SetAnchorsPreset(LayoutPreset.FullRect);
            Frame.AddThemeStyleboxOverride("panel", new StyleBoxFlat { BgColor = Colors.Black });
            AddChild(Frame);
        }
        else
        {
            // Centred, or along the bottom in the middle. A frame wider or taller than the window makes the holder
            // grow about its middle (up, along the bottom), so it stays there while FitFrame scales it down.
            var holder = new MarginContainer
            {
                MouseFilter = MouseFilterEnum.Ignore,
                GrowHorizontal = GrowDirection.Both,
                GrowVertical = placement == PanelPlacement.Bottom ? GrowDirection.Begin : GrowDirection.Both,
            };
            holder.SetAnchorsPreset(LayoutPreset.FullRect);
            foreach (var side in (ReadOnlySpan<string>)["margin_top", "margin_bottom", "margin_left", "margin_right"])
            {
                holder.AddThemeConstantOverride(side, UiStyle.ScreenEdge);
            }

            AddChild(holder);
            _holder = holder;
            Frame = new PanelContainer
            {
                MouseFilter = MouseFilterEnum.Stop,
                SizeFlagsHorizontal = SizeFlags.ShrinkCenter,
                SizeFlagsVertical = placement == PanelPlacement.Bottom ? SizeFlags.ShrinkEnd : SizeFlags.ShrinkCenter,
            };
            holder.AddChild(Frame);
            _size = size;
            _bottom = placement == PanelPlacement.Bottom;
            FitFrame();
            Resized += FitFrame;
            Frame.MinimumSizeChanged += FitFrame;
        }

        var column = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        column.AddThemeConstantOverride("separation", 10);
        Frame.AddChild(column);

        var header = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore, Visible = !FullScreen };
        column.AddChild(header);
        var headings = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        headings.AddThemeConstantOverride("separation", 0);
        header.AddChild(headings);
        _title = UiStyle.Label(title, UiStyle.Title);
        _title.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
        headings.AddChild(_title);
        _subtitle = UiStyle.Label(string.Empty, UiStyle.Subtitle);
        _subtitle.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
        _subtitle.Visible = false;
        headings.AddChild(_subtitle);

        Body = new VBoxContainer { SizeFlagsVertical = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        Body.AddThemeConstantOverride("separation", 6);
        column.AddChild(Body);

        _status = UiStyle.Label(string.Empty, new LabelSettings { FontSize = UiStyle.DetailSize, FontColor = UiStyle.Text }, wrap: true);
        _status.Visible = false;
        column.AddChild(_status);
        _hints = new HintBar(UiStyle.Hint);
        _hints.Visible = !FullScreen;
        column.AddChild(_hints);
    }

    /// <summary>
    /// The frame at the panel's size, or less where the window is smaller (the large UI size, A1 "UI size"): a panel's
    /// rows scroll, and its columns share what's left. What can't shrink (a keyboard's keys, a grid of thumbnails) is
    /// drawn smaller instead, as large as fits, about the window's middle (or the middle of its foot, along the bottom).
    /// The holder is what's scaled: a container resets its children's scale.
    /// </summary>
    private void FitFrame()
    {
        var room = Size - new Vector2(2 * UiStyle.ScreenEdge, 2 * UiStyle.ScreenEdgeY);
        if (_holder is null || room.X <= 0 || room.Y <= 0)
        {
            Frame.CustomMinimumSize = _size;
            return;
        }

        Frame.CustomMinimumSize = new Vector2(Math.Min(_size.X, room.X), Math.Min(_size.Y, room.Y));
        var needed = Frame.GetCombinedMinimumSize();
        var scale = Math.Min(1, Math.Min(room.X / Math.Max(needed.X, 1), room.Y / Math.Max(needed.Y, 1)));
        var grown = new Vector2(Math.Max(Size.X, needed.X + (2 * UiStyle.ScreenEdge)), Math.Max(Size.Y, needed.Y + (2 * UiStyle.ScreenEdge)));
        _holder.Scale = new Vector2(scale, scale);
        _holder.PivotOffset = new Vector2(grown.X / 2, _bottom ? grown.Y : grown.Y / 2);
    }

    /// <summary>The frame around the panel's content.</summary>
    protected PanelContainer Frame { get; }

    /// <summary>Where subclasses put their content.</summary>
    protected VBoxContainer Body { get; }

    /// <summary>
    /// A dialog shows over the panel below it (dimmed); a page replaces it, since two translucent frames would show
    /// through each other.
    /// </summary>
    public bool IsDialog { get; }

    /// <summary>The panel fills the window (<see cref="PanelPlacement.FullScreen"/>): the status indicators step aside for it.</summary>
    public bool FullScreen { get; }

    /// <summary>The layer showing this panel; set when it's pushed.</summary>
    public UiLayer Layer { get; internal set; } = null!;

    /// <summary>True while the panel takes typing from the physical keyboard, so only gamepads navigate.</summary>
    public virtual bool CapturesKeyboard => false;

    /// <summary>The control focused when the panel is shown (and when focus is lost).</summary>
    public virtual Control? DefaultFocus => FirstFocusable(Body);

    /// <summary>The focus when another panel was pushed over this one, restored when it closes.</summary>
    internal Control? LastFocus { get; set; }

    public string Heading
    {
        get => _title.Text;
        set => _title.Text = value;
    }

    public string? Subtitle
    {
        get => _subtitle.Visible ? _subtitle.Text : null;
        set
        {
            _subtitle.Text = value ?? string.Empty;
            _subtitle.Visible = !string.IsNullOrEmpty(value);
        }
    }

    /// <summary>Takes a command before the layer's own handling (focus moves, accept, back). True when it was used.</summary>
    public virtual bool Handle(NavCommand command) => false;

    /// <summary>Once a frame while the panel is on top.</summary>
    public virtual void Tick(double delta)
    {
        _clock += delta;
        if (_statusClearAt >= 0 && _clock >= _statusClearAt)
        {
            _statusClearAt = -1;
            _status.Visible = false;
        }
    }

    /// <summary>Called when the panel is on top again, after a panel over it closed.</summary>
    public virtual void OnRevealed()
    {
    }

    /// <summary>Called once, after the panel has been taken off the layer.</summary>
    public virtual void OnClosed()
    {
    }

    /// <summary>B or Escape: closes the panel unless a subclass does something else first.</summary>
    public virtual void GoBack() => Close();

    public void Close() => Layer?.Pop(this);

    /// <summary>The controls' hints; a pad's buttons while the panel takes typing from the keyboard (<see cref="CapturesKeyboard"/>).</summary>
    protected void SetHints(Hint[] hints) => _hints.Show(hints, padOnly: CapturesKeyboard);

    /// <summary>A line above the hints; cleared after <paramref name="seconds"/> (0 keeps it).</summary>
    public void ShowStatus(string? text, Color? colour = null, double seconds = 0)
    {
        _status.Visible = !string.IsNullOrEmpty(text);
        _status.Text = text ?? string.Empty;
        _status.LabelSettings.FontColor = colour ?? UiStyle.Text;
        _statusClearAt = seconds > 0 ? _clock + seconds : -1;
    }

    public void FocusDefault()
    {
        (LastFocus is { } last && IsInstanceValid(last) && last.IsVisibleInTree() && IsAncestorOf(last) ? last : DefaultFocus)?.GrabFocus();
    }

    /// <summary>The first control under <paramref name="root"/> that can take focus, depth first.</summary>
    public static Control? FirstFocusable(Node root)
    {
        foreach (var child in root.GetChildren())
        {
            if (child is Control { Visible: true } control)
            {
                if (control.FocusMode == FocusModeEnum.All)
                {
                    return control;
                }

                if (FirstFocusable(control) is { } inner)
                {
                    return inner;
                }
            }
        }

        return null;
    }

    /// <summary>The last control under <paramref name="root"/> that can take focus.</summary>
    public static Control? LastFocusable(Node root)
    {
        var children = root.GetChildren();
        for (var i = children.Count - 1; i >= 0; i--)
        {
            if (children[i] is Control { Visible: true } control)
            {
                if (LastFocusable(control) is { } inner)
                {
                    return inner;
                }

                if (control.FocusMode == FocusModeEnum.All)
                {
                    return control;
                }
            }
        }

        return null;
    }
}
