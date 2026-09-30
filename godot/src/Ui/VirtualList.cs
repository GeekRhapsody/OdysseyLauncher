using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Ui;

/// <summary>What a list row is, for its icon.</summary>
public enum ItemKind
{
    Folder,
    File,
    Drive,
    Network,
    Place,

    /// <summary>A row that can't be opened now (a disconnected drive): shown dimmed.</summary>
    Unavailable,
}

/// <summary>One row of a <see cref="VirtualList"/>. Built off the main thread for a big folder.</summary>
public sealed record ListItem(string Name, string? Detail, ItemKind Kind, string? Path = null);

/// <summary>
/// A list of any length drawn with a fixed pool of row views (M7): a folder of tens of thousands of files costs the
/// same as one of ten, since only the visible rows exist and binding one sets two labels. It keeps its own selection:
/// the picker gives it the controller's moves while it has focus. The mouse wheel scrolls, a click selects, a double
/// click opens, and the scrollbar drags.
/// </summary>
public sealed partial class VirtualList : Control
{
    public const float RowHeight = 40;

    private static readonly StyleBoxFlat Selected = UiStyle.Focused;
    private static readonly StyleBoxFlat SelectedUnfocused = UiStyle.RowBox(new Color(0.12f, 0.17f, 0.42f, 0.7f), new Color("#3A4C9A"), 1);
    private static readonly StyleBoxFlat Empty = UiStyle.RowBox(Colors.Transparent);
    private static readonly StringName PanelStyle = "panel";

    private readonly List<RowView> _rows = [];
    private readonly VScrollBar _bar;
    private IReadOnlyList<ListItem> _items = [];
    private int _selected = -1;
    private int _top;
    private bool _syncingBar;

    public VirtualList()
    {
        FocusMode = FocusModeEnum.All;
        ClipContents = true;
        MouseFilter = MouseFilterEnum.Stop;
        SizeFlagsHorizontal = SizeFlags.ExpandFill;
        SizeFlagsVertical = SizeFlags.ExpandFill;
        _bar = new VScrollBar { FocusMode = FocusModeEnum.None, Step = 1 };
        _bar.SetAnchorsPreset(LayoutPreset.RightWide);
        _bar.OffsetLeft = -10;
        _bar.ValueChanged += value =>
        {
            if (!_syncingBar)
            {
                _top = (int)value;
                Bind();
            }
        };
        AddChild(_bar);
    }

    /// <summary>The selection moved (by any means).</summary>
    public event Action<int>? SelectionChanged;

    /// <summary>A row was opened: A or Enter (through the picker), or a double click.</summary>
    public event Action<int>? Activated;

    public int Count => _items.Count;

    public int SelectedIndex => _selected;

    public ListItem? SelectedItem => _selected >= 0 && _selected < _items.Count ? _items[_selected] : null;

    public IReadOnlyList<ListItem> Items => _items;

    /// <summary>Whole rows that fit.</summary>
    public int VisibleRows => Math.Max(1, (int)(Size.Y / RowHeight));

    /// <summary>Dims the rows while the list is waiting for a folder that's slow to open.</summary>
    public bool Waiting
    {
        set => Modulate = value ? new Color(1, 1, 1, 0.45f) : Colors.White;
    }

    public void SetItems(IReadOnlyList<ListItem> items, int selected)
    {
        _items = items;
        _selected = items.Count == 0 ? -1 : Math.Clamp(selected, 0, items.Count - 1);
        _top = 0;
        EnsureVisible();
        Bind();
        SelectionChanged?.Invoke(_selected);
    }

    /// <summary>Replaces rows without moving the selection (a drive's label arriving).</summary>
    public void UpdateItems(IReadOnlyList<ListItem> items)
    {
        _items = items;
        _selected = Math.Min(_selected, items.Count - 1);
        Bind();
    }

    public void Select(int index)
    {
        if (_items.Count == 0)
        {
            return;
        }

        index = Math.Clamp(index, 0, _items.Count - 1);
        if (index == _selected)
        {
            return;
        }

        _selected = index;
        EnsureVisible();
        Bind();
        SelectionChanged?.Invoke(_selected);
    }

    public void Move(int delta) => Select(_selected + delta);

    public void Activate()
    {
        if (_selected >= 0)
        {
            Activated?.Invoke(_selected);
        }
    }

    public override void _Notification(int what)
    {
        if (what == NotificationResized)
        {
            BuildRows();
            EnsureVisible();
            Bind();
        }
        else if (what is (int)NotificationFocusEnter or (int)NotificationFocusExit)
        {
            Bind();
        }
    }

    public override void _GuiInput(InputEvent @event)
    {
        switch (@event)
        {
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelUp }:
                Scroll(-3);
                AcceptEvent();
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelDown }:
                Scroll(3);
                AcceptEvent();
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.Left } click when click.Position.X < Size.X - 12:
                GrabFocus();
                var index = _top + (int)(click.Position.Y / RowHeight);
                if (index < _items.Count)
                {
                    Select(index);
                    if (click.DoubleClick)
                    {
                        Activate();
                    }
                }

                AcceptEvent();
                break;
        }
    }

    private void Scroll(int rows)
    {
        _top = Math.Clamp(_top + rows, 0, Math.Max(0, _items.Count - VisibleRows));
        Bind();
    }

    private void EnsureVisible()
    {
        if (_selected < 0)
        {
            return;
        }

        var visible = VisibleRows;
        if (_selected < _top)
        {
            _top = _selected;
        }
        else if (_selected >= _top + visible)
        {
            _top = _selected - visible + 1;
        }

        _top = Math.Clamp(_top, 0, Math.Max(0, _items.Count - visible));
    }

    private void BuildRows()
    {
        var needed = (int)Math.Ceiling(Size.Y / RowHeight) + 1;
        while (_rows.Count < needed)
        {
            var row = new RowView();
            AddChild(row.Root);
            MoveChild(_bar, -1);
            _rows.Add(row);
        }

        for (var i = 0; i < _rows.Count; i++)
        {
            _rows[i].Root.Position = new Vector2(0, i * RowHeight);
            _rows[i].Root.Size = new Vector2(Size.X - 14, RowHeight - 2);
        }
    }

    /// <summary>Puts the visible items in the pooled rows.</summary>
    private void Bind()
    {
        var focused = HasFocus();
        for (var i = 0; i < _rows.Count; i++)
        {
            var index = _top + i;
            var row = _rows[i];
            if (index >= _items.Count)
            {
                row.Root.Visible = false;
                continue;
            }

            row.Root.Visible = true;
            row.Show(_items[index]);
            row.Root.AddThemeStyleboxOverride(PanelStyle, index == _selected ? (focused ? Selected : SelectedUnfocused) : Empty);
        }

        _syncingBar = true;
        _bar.MaxValue = Math.Max(1, _items.Count);
        _bar.Page = VisibleRows;
        _bar.Value = _top;
        _bar.Visible = _items.Count > VisibleRows;
        _syncingBar = false;
    }

    /// <summary>A pooled row: its box, icon, name and detail.</summary>
    private sealed class RowView
    {
        private static readonly Dictionary<ItemKind, StyleBoxFlat> Icons = new()
        {
            [ItemKind.Folder] = Icon("#E8B84A"),
            [ItemKind.File] = Icon("#B8C4E6"),
            [ItemKind.Drive] = Icon("#6F95F2"),
            [ItemKind.Network] = Icon("#6FD2A2"),
            [ItemKind.Place] = Icon("#C58CF0"),
            [ItemKind.Unavailable] = Icon("#4A5378"),
        };

        private readonly Panel _icon;
        private readonly Label _name;
        private readonly Label _detail;
        private readonly LabelSettings _nameSettings = new() { FontSize = 19, FontColor = UiStyle.Text };

        public RowView()
        {
            Root = new PanelContainer { MouseFilter = MouseFilterEnum.Ignore };
            var line = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
            line.AddThemeConstantOverride("separation", 12);
            Root.AddChild(line);
            _icon = new Panel { CustomMinimumSize = new Vector2(16, 13), SizeFlagsVertical = SizeFlags.ShrinkCenter, MouseFilter = MouseFilterEnum.Ignore };
            line.AddChild(_icon);
            _name = UiStyle.Label(string.Empty, _nameSettings);
            _name.SizeFlagsHorizontal = SizeFlags.ExpandFill;
            _name.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
            _name.ClipText = true;
            line.AddChild(_name);
            _detail = UiStyle.Label(string.Empty, UiStyle.Detail);
            _detail.HorizontalAlignment = HorizontalAlignment.Right;
            line.AddChild(_detail);
        }

        public PanelContainer Root { get; }

        public void Show(ListItem item)
        {
            _name.Text = item.Name;
            _detail.Text = item.Detail ?? string.Empty;
            _nameSettings.FontColor = item.Kind == ItemKind.Unavailable ? UiStyle.Faint : UiStyle.Text;
            _icon.AddThemeStyleboxOverride(PanelStyle, Icons[item.Kind]);
        }

        private static StyleBoxFlat Icon(string colour) => new()
        {
            BgColor = new Color(colour),
            CornerRadiusTopLeft = 3,
            CornerRadiusTopRight = 3,
            CornerRadiusBottomLeft = 3,
            CornerRadiusBottomRight = 3,
        };
    }
}
