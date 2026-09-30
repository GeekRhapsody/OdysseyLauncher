using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Ui;

/// <summary>A panel whose body is a scrolling column of <see cref="SettingRow"/>s under optional section labels.</summary>
public abstract partial class ListPanel : UiPanel
{
    public static readonly Vector2 PageSize = new(980, 680);

    private readonly ScrollContainer _scroll;

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
        Rows = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        Rows.AddThemeConstantOverride("separation", 4);
        _scroll.AddChild(Rows);
    }

    protected VBoxContainer Rows { get; }

    public override Control? DefaultFocus => FirstFocusable(Rows);

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
            rows[Math.Min(index, rows.Count - 1)].GrabFocus();
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
