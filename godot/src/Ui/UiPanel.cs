using System;
using Godot;
using Launcher.App.Navigation;

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
    private readonly Label _hints;
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
            var dim = new ColorRect { Color = new Color(0, 0, 0.02f, 0.45f), MouseFilter = MouseFilterEnum.Stop };
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
            var holder = placement == PanelPlacement.Centre ? (Container)new CenterContainer() : new MarginContainer();
            holder.MouseFilter = MouseFilterEnum.Ignore;
            holder.SetAnchorsPreset(LayoutPreset.FullRect);
            if (holder is MarginContainer margins)
            {
                margins.AddThemeConstantOverride("margin_top", (int)Math.Max(0, 800 - size.Y - 24));
                margins.AddThemeConstantOverride("margin_bottom", 24);
                margins.AddThemeConstantOverride("margin_left", (int)Math.Max(0, (1280 - size.X) / 2));
                margins.AddThemeConstantOverride("margin_right", (int)Math.Max(0, (1280 - size.X) / 2));
            }

            AddChild(holder);
            Frame = new PanelContainer { CustomMinimumSize = size, MouseFilter = MouseFilterEnum.Stop };
            holder.AddChild(Frame);
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
        _hints = UiStyle.Label(string.Empty, UiStyle.Hint);
        _hints.HorizontalAlignment = HorizontalAlignment.Right;
        _hints.Visible = !FullScreen;
        column.AddChild(_hints);
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

    protected void SetHints(string hints) => _hints.Text = hints;

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
