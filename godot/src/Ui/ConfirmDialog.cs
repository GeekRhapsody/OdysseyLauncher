using System;
using Godot;

namespace Launcher.App.Ui;

/// <summary>
/// A question with two answers, or a message with one (M7): a title, the message, and buttons side by side. A picks
/// the focused button, B (or Escape, or the header's Cancel) answers no. The focus starts on the safe answer when
/// the action can't be undone.
/// </summary>
public sealed partial class ConfirmDialog : UiPanel
{
    private readonly Action<bool>? _answered;
    private readonly Button _yes;
    private readonly Button? _no;
    private readonly bool _startOnNo;
    private bool _done;

    private ConfirmDialog(string title, string message, string yes, string? no, bool startOnNo, Action<bool>? answered)
        : base(title, new Vector2(700, 0), PanelPlacement.Centre, dimBelow: true)
    {
        _answered = answered;
        _startOnNo = startOnNo;
        var text = UiStyle.Label(message, UiStyle.Body, wrap: true);
        text.CustomMinimumSize = new Vector2(640, 0);
        Body.AddChild(text);
        Body.AddChild(new Control { CustomMinimumSize = new Vector2(0, 8), MouseFilter = MouseFilterEnum.Ignore });

        var buttons = new HBoxContainer { Alignment = BoxContainer.AlignmentMode.End, MouseFilter = MouseFilterEnum.Ignore };
        buttons.AddThemeConstantOverride("separation", 12);
        Body.AddChild(buttons);
        _yes = new Button { Text = yes, CustomMinimumSize = new Vector2(180, 46), FocusMode = FocusModeEnum.All };
        _yes.Pressed += () => Answer(true);
        buttons.AddChild(_yes);
        if (no is not null)
        {
            _no = new Button { Text = no, CustomMinimumSize = new Vector2(180, 46), FocusMode = FocusModeEnum.All };
            _no.Pressed += () => Answer(false);
            buttons.AddChild(_no);
        }

        SetHints(no is null ? "A  OK" : "A  Choose     B  " + no);
    }

    protected override string BackLabel => "Cancel";

    public override Control? DefaultFocus => _startOnNo && _no is not null ? _no : _yes;

    /// <summary>Asks a question. <paramref name="answered"/> gets true for <paramref name="yes"/>, false for anything else.</summary>
    public static ConfirmDialog Ask(UiLayer layer, string title, string message, string yes, string no, Action<bool> answered, bool destructive = false)
    {
        var dialog = new ConfirmDialog(title, message, yes, no, destructive, answered);
        layer.Push(dialog);
        return dialog;
    }

    /// <summary>Tells the user something, with one button.</summary>
    public static ConfirmDialog Tell(UiLayer layer, string title, string message, Action? closed = null)
    {
        var dialog = new ConfirmDialog(title, message, "OK", null, false, closed is null ? null : _ => closed());
        layer.Push(dialog);
        return dialog;
    }

    public override void GoBack() => Answer(false);

    public override void OnClosed()
    {
        // Closed some other way (the whole settings screen closing): that's a no.
        if (!_done)
        {
            _done = true;
            _answered?.Invoke(false);
        }
    }

    private void Answer(bool yes)
    {
        if (_done)
        {
            return;
        }

        _done = true;
        Close();
        _answered?.Invoke(yes);
    }
}
