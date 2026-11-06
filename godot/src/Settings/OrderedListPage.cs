using System.Collections.Generic;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Config;

namespace Launcher.App.Settings;

/// <summary>
/// A list of things each on or off, the ones on in an order (regions, fallback providers). Each is a row, A turning it
/// on or off, and for one that's on, ↑ and ↓ buttons beside it moving it earlier or later. The buttons take the focus
/// as the row does (2026-11-06), left and right going between them, so a pad reaches them as the mouse does. The page
/// rebuilds on every save, and the focus follows the thing just changed, on the same row or button.
/// </summary>
public abstract partial class OrderedListPage : ListPanel
{
    private static readonly Hint[] RowHints = [new("On or off", Prompt.Accept), new("Back", Prompt.Back)];
    private static readonly Hint[] EarlierHints = [new("Earlier", Prompt.Accept), new("Back", Prompt.Back)];
    private static readonly Hint[] LaterHints = [new("Later", Prompt.Accept), new("Back", Prompt.Back)];

    private readonly Dictionary<string, HBoxContainer> _lines = [];

    /// <summary>The thing just turned on, off or moved, and which of its line's controls had the focus (0 the row).</summary>
    private string? _follow;
    private int _followPart;

    protected OrderedListPage(string title, Vector2 size)
        : base(title, size)
    {
        SetHints(RowHints);
    }

    /// <summary>Adds the page's note and its rows (<see cref="AddItem"/>).</summary>
    protected abstract void Build();

    protected abstract void Toggle(string id);

    /// <summary>Moves <paramref name="id"/> one place earlier (−1) or later (+1).</summary>
    protected abstract void Move(string id, int direction);

    protected static string Ordinal(int n) => (n % 100) switch
    {
        11 or 12 or 13 => $"{n}th",
        _ => (n % 10) switch
        {
            1 => $"{n}st",
            2 => $"{n}nd",
            3 => $"{n}rd",
            _ => $"{n}th",
        },
    };

    protected void AddItem(string id, string title, string? detail, int place)
    {
        var on = place > 0;
        var line = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        line.AddThemeConstantOverride("separation", 6);
        Rows.AddChild(line);
        _lines[id] = line;
        var row = new SettingRow(title, detail, on ? $"On, {Ordinal(place)}" : "Off", () => Act(id, 0))
        {
            ValueColour = on ? UiStyle.Good : UiStyle.Faint,
        };
        row.FocusEntered += () => SetHints(RowHints);
        line.AddChild(row);
        if (on)
        {
            line.AddChild(Arrow("↑", 1, id, EarlierHints));
            line.AddChild(Arrow("↓", 2, id, LaterHints));
        }
    }

    protected void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        _lines.Clear();
        Build();
        var follow = _follow;
        _follow = null;
        if (follow is null || !_lines.TryGetValue(follow, out var line))
        {
            FocusRow(focused);
            return;
        }

        // A thing turned off has no buttons any more: its row has the focus.
        FocusRebuilt(line.GetChild<Control>(_followPart < line.GetChildCount() ? _followPart : 0));
    }

    private Button Arrow(string text, int part, string id, Hint[] hints)
    {
        var button = new Button { Text = text, FocusMode = FocusModeEnum.All, CustomMinimumSize = new Vector2(46, 0) };
        button.Pressed += () => Act(id, part);
        button.FocusEntered += () => SetHints(hints);
        return button;
    }

    /// <param name="part">0 the row (on or off), 1 the ↑ button, 2 the ↓ one.</param>
    private void Act(string id, int part)
    {
        _follow = id;
        _followPart = part;
        if (part == 0)
        {
            Toggle(id);
        }
        else
        {
            Move(id, part == 1 ? -1 : 1);
        }
    }
}
