using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Ui;

/// <summary>
/// A panel whose body is a scrolling column of <see cref="SettingRow"/>s under optional section labels. The column
/// keeps <see cref="ScrollContainer.FollowFocus"/> on, without which Godot's focus search skips the rows scrolled out
/// of view, but its scroll is put right at the end of the frame: Godot scrolls by the focused row's place on screen,
/// which only changes when the container is laid out again, after the frame, so several focus moves in one frame (a
/// page up or down is six) each added their own scroll and overshot, the column jumping about. The scroll kept is
/// worked out from the row's place in the column, which scrolling doesn't change.
/// </summary>
public abstract partial class ListPanel : UiPanel
{
    public static readonly Vector2 PageSize = new(980, 680);

    private readonly ScrollContainer _scroll;
    private readonly HashSet<Label> _sections = [];
    private readonly Callable _scrollToFocus;
    private Viewport? _viewport;
    private Control? _scrollTarget;
    private int _scrollFrom;

    protected ListPanel(string title, Vector2? size = null, bool dimBelow = false)
        : base(title, size ?? PageSize, PanelPlacement.Centre, dimBelow)
    {
        _scroll = new ScrollContainer
        {
            FollowFocus = true,
            HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled,
            SizeFlagsVertical = SizeFlags.ExpandFill,
        };
        Body.AddChild(_scroll);
        _scrollToFocus = Callable.From(ScrollToFocus);
        Rows = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        Rows.AddThemeConstantOverride("separation", 4);
        _scroll.AddChild(Rows);
    }

    protected VBoxContainer Rows { get; }

    public override Control? DefaultFocus => FirstFocusable(Rows);

    public override void _EnterTree()
    {
        _viewport = GetViewport();
        _viewport.GuiFocusChanged += OnFocusChanged;
    }

    public override void _ExitTree()
    {
        if (_viewport is not null)
        {
            _viewport.GuiFocusChanged -= OnFocusChanged;
            _viewport = null;
        }
    }

    private void OnFocusChanged(Control focused)
    {
        if (!Rows.IsAncestorOf(focused))
        {
            return;
        }

        if (_scrollTarget is null)
        {
            // The frame's first move: Godot's follow has scrolled at most once, and rightly, so far.
            _scrollFrom = _scroll.ScrollVertical;
            _scrollToFocus.CallDeferred();
        }

        _scrollTarget = focused;
    }

    /// <summary>End of the frame: the last focus change's row, scrolled to once, over what Godot's follow did.</summary>
    private void ScrollToFocus()
    {
        var target = _scrollTarget;
        _scrollTarget = null;
        if (target is not null && IsInstanceValid(target) && Rows.IsAncestorOf(target))
        {
            ScrollTo(target, _scrollFrom);
        }
    }

    /// <summary>
    /// Scrolls the least from <paramref name="from"/> that shows all of <paramref name="control"/> (a row under a
    /// section heading shows the heading too, and the first row everything above it). Its place is taken in the column,
    /// which scrolling doesn't move until the container is laid out again.
    /// </summary>
    private void ScrollTo(Control control, int from)
    {
        var top = control.GlobalPosition.Y - Rows.GlobalPosition.Y;
        var bottom = top + control.Size.Y;
        if (control == FirstFocusable(Rows))
        {
            top = 0;
        }
        else if (control.GetParent() == Rows && control.GetIndex() > 0 && Rows.GetChild(control.GetIndex() - 1) is Label heading
            && _sections.Contains(heading))
        {
            top = heading.Position.Y;
        }

        var view = _scroll.Size.Y;
        double scroll = from;
        if (top < scroll || bottom - top > view)
        {
            scroll = top;
        }
        else if (bottom > scroll + view)
        {
            scroll = bottom - view;
        }

        _scroll.ScrollVertical = (int)Math.Round(scroll);
    }

    protected SettingRow AddRow(string title, string? detail = null, string? value = null, Action? activated = null)
    {
        var row = new SettingRow(title, detail, value, activated);
        Rows.AddChild(row);
        return row;
    }

    protected Label AddSection(string text)
    {
        var label = UiStyle.Label(text.ToUpperInvariant(), UiStyle.Section);
        label.CustomMinimumSize = new Vector2(0, 30);
        label.VerticalAlignment = VerticalAlignment.Bottom;
        Rows.AddChild(label);
        _sections.Add(label);
        return label;
    }

    protected Label AddNote(string text, Color? colour = null)
    {
        var label = UiStyle.Label(text, new LabelSettings { FontSize = UiStyle.DetailSize, FontColor = colour ?? UiStyle.Dim }, wrap: true);
        Rows.AddChild(label);
        return label;
    }

    /// <summary>Removes every row, for a page that rebuilds itself; <paramref name="focusedIndex"/> is the focused row's place.</summary>
    protected void ClearRows(out int focusedIndex)
    {
        focusedIndex = -1;
        var owner = GetViewport()?.GuiGetFocusOwner();
        var rows = new List<SettingRow>();
        CollectRows(Rows, rows);
        for (var i = 0; i < rows.Count; i++)
        {
            if (rows[i] == owner)
            {
                focusedIndex = i;
            }
        }

        foreach (var child in Rows.GetChildren())
        {
            Rows.RemoveChild(child);
            child.QueueFree();
        }

        _sections.Clear();
    }

    /// <summary>Focuses the <paramref name="index"/>th row (clamped), after <see cref="ClearRows"/> and a rebuild.</summary>
    protected void FocusRow(int index)
    {
        if (index < 0 || Layer?.Top != this)
        {
            // A page rebuilt under another panel gets its focus back from FocusDefault when it's on top again.
            return;
        }

        var rows = new List<SettingRow>();
        CollectRows(Rows, rows);
        if (rows.Count > 0)
        {
            var row = rows[Math.Min(index, rows.Count - 1)];
            row.GrabFocus();
            ScrollToLater(row);
        }
    }

    /// <summary>
    /// Scrolls <paramref name="row"/> into view once it's laid out: rows added this frame have no place yet, so following
    /// the focus at once would scroll a rebuilt page to its top, away from the row.
    /// </summary>
    private async void ScrollToLater(Control row)
    {
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        if (IsInstanceValid(row) && row.IsInsideTree() && IsInstanceValid(_scroll) && Rows.IsAncestorOf(row))
        {
            ScrollTo(row, _scroll.ScrollVertical);
        }
    }

    /// <summary>Every row under <paramref name="node"/>, in order (rows can sit inside a line with other controls).</summary>
    private static void CollectRows(Node node, List<SettingRow> rows)
    {
        foreach (var child in node.GetChildren())
        {
            if (child is SettingRow row)
            {
                rows.Add(row);
            }
            else
            {
                CollectRows(child, rows);
            }
        }
    }
}
