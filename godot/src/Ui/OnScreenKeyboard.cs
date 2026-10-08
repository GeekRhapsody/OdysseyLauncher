using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Navigation;

namespace Launcher.App.Ui;

/// <summary>What the on-screen keyboard is typing, and what happens with it.</summary>
/// <param name="Validate">Returns why the text can't be used (shown, and the keyboard stays open), or null.</param>
public sealed record KeyboardRequest(
    string Title,
    string Text,
    Action<string> Done,
    Action? Cancelled = null,
    bool Secret = false,
    string? Placeholder = null,
    string? Subtitle = null,
    Func<string, string?>? Validate = null);

/// <summary>
/// The on-screen keyboard (M7): Godot has none on Windows desktop. Four rows of keys (letters, or symbols and accented
/// letters), then Shift, Symbols, Space, caret moves, Delete, Paste, Show, Cancel and Done. On a pad it works like
/// the Xbox keyboard: A types the focused key, X deletes, Y is a space, LB and RB move the caret, LT is Shift, RT
/// switches to symbols, Menu is Done and B cancels. A physical keyboard types straight into the field (Enter is Done,
/// Escape cancels, Ctrl+V pastes), and the mouse clicks keys and places the caret.
/// </summary>
public sealed partial class OnScreenKeyboard : UiPanel
{
    public const int MaxLength = 1024;

    private static readonly string[] Letters = ["1234567890-=", "qwertyuiop[]", "asdfghjkl;'\\", "zxcvbnm,./:_"];
    private static readonly string[] Symbols = ["!@#$%^&*()_+", "~`{}|<>\"?&€£", "éèêëàâäçñöüß", "ÉÀÇÑÖÜåøæ°§¿"];

    private readonly KeyboardRequest _request;
    private readonly TextField _field;
    private readonly Label _error;
    private readonly List<Button> _characterKeys = [];
    private readonly Button _shift;
    private readonly Button _symbols;
    private readonly Button? _reveal;
    private bool _shifted;
    private bool _onSymbols;
    private bool _finished;
    private double _blink;

    public OnScreenKeyboard(KeyboardRequest request)
        : base(request.Title, new Vector2(1180, 470), PanelPlacement.Bottom, dimBelow: true)
    {
        _request = request;
        Subtitle = request.Subtitle;
        _field = new TextField { Masked = request.Secret, Placeholder = request.Placeholder ?? string.Empty };
        _field.Text = request.Text.Length > MaxLength ? request.Text[..MaxLength] : request.Text;
        _field.Caret = _field.Text.Length;
        Body.AddChild(_field);
        _error = UiStyle.Label(string.Empty, new LabelSettings { FontSize = UiStyle.DetailSize, FontColor = UiStyle.Bad });
        _error.Visible = false;
        Body.AddChild(_error);

        var keys = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        keys.AddThemeConstantOverride("separation", 6);
        Body.AddChild(keys);
        for (var row = 0; row < Letters.Length; row++)
        {
            var line = Line(keys);
            for (var column = 0; column < Letters[row].Length; column++)
            {
                var key = Key(line, string.Empty, 80);
                key.Pressed += () => Insert(key.Text);
                _characterKeys.Add(key);
            }
        }

        var functions = Line(keys);
        _shift = Key(functions, "Shift", 100);
        _shift.Pressed += ToggleShift;
        _symbols = Key(functions, "Symbols", 110);
        _symbols.Pressed += ToggleSymbols;
        Key(functions, "Space", 170).Pressed += () => Insert(" ");
        Key(functions, "←", 64).Pressed += () => _field.Caret--;
        Key(functions, "→", 64).Pressed += () => _field.Caret++;
        Key(functions, "Delete", 100).Pressed += Backspace;
        Key(functions, "Paste", 90).Pressed += Paste;
        if (request.Secret)
        {
            _reveal = Key(functions, "Show", 80);
            _reveal.Pressed += ToggleReveal;
        }

        Key(functions, "Cancel", 100).Pressed += Cancel;
        Key(functions, "Done", 110).Pressed += Finish;

        Relabel();
        SetHints("A  Type     X  Delete     Y  Space     LB RB  Move     LT  Shift     RT  Symbols     Menu  Done     B  Cancel");
    }

    public override bool CapturesKeyboard => true;

    public override Control? DefaultFocus => _characterKeys.Count > 13 ? _characterKeys[13] : null;

    /// <summary>The text as it is now (for tests and the nav script's log).</summary>
    public string Text => _field.Text;

    public static OnScreenKeyboard Open(UiLayer layer, KeyboardRequest request)
    {
        var keyboard = new OnScreenKeyboard(request);
        layer.Push(keyboard);
        return keyboard;
    }

    public override bool Handle(NavCommand command)
    {
        switch (command)
        {
            case NavCommand.Alternate:
                Backspace();
                return true;
            case NavCommand.Secondary:
                Insert(" ");
                return true;
            case NavCommand.PageUp:
                _field.Caret--;
                return true;
            case NavCommand.PageDown:
                _field.Caret++;
                return true;
            case NavCommand.LetterPrevious:
                ToggleShift();
                return true;
            case NavCommand.LetterNext:
                ToggleSymbols();
                return true;
            case NavCommand.Menu:
                Finish();
                return true;
            case NavCommand.First:
                _field.Caret = 0;
                return true;
            case NavCommand.Last:
                _field.Caret = _field.Text.Length;
                return true;
            default:
                return false;
        }
    }

    public override void GoBack() => Cancel();

    public override void Tick(double delta)
    {
        base.Tick(delta);
        _blink += delta;
        if (_blink >= 0.5)
        {
            _blink = 0;
            _field.Blink();
        }
    }

    public override void OnClosed()
    {
        if (!_finished)
        {
            _finished = true;
            _request.Cancelled?.Invoke();
        }
    }

    /// <summary>A physical keyboard types into the field while the keyboard is on top.</summary>
    public override void _Input(InputEvent @event)
    {
        if (Layer?.Top != this || @event is not InputEventKey { Pressed: true } key)
        {
            return;
        }

        var handled = true;
        if (key.CtrlPressed && key.Keycode == Godot.Key.V)
        {
            Paste();
        }
        else
        {
            switch (key.Keycode)
            {
                case Godot.Key.Enter or Godot.Key.KpEnter:
                    Finish();
                    break;
                case Godot.Key.Escape:
                    Cancel();
                    break;
                case Godot.Key.Backspace:
                    Backspace();
                    break;
                case Godot.Key.Delete:
                    if (_field.Caret < _field.Text.Length)
                    {
                        _field.Text = _field.Text.Remove(_field.Caret, 1);
                    }

                    break;
                case Godot.Key.Left:
                    _field.Caret--;
                    break;
                case Godot.Key.Right:
                    _field.Caret++;
                    break;
                case Godot.Key.Home:
                    _field.Caret = 0;
                    break;
                case Godot.Key.End:
                    _field.Caret = _field.Text.Length;
                    break;
                default:
                    if (key.Unicode >= 32 && !key.CtrlPressed && key.Unicode != 127)
                    {
                        Insert(char.ConvertFromUtf32((int)key.Unicode));
                    }
                    else
                    {
                        handled = false;
                    }

                    break;
            }
        }

        if (handled)
        {
            GetViewport().SetInputAsHandled();
        }
    }

    private void Insert(string text)
    {
        if (_field.Text.Length + text.Length > MaxLength)
        {
            ShowError($"That's as long as it can be ({MaxLength} characters).");
            return;
        }

        var caret = _field.Caret;
        _field.Text = _field.Text.Insert(caret, text);
        _field.Caret = caret + text.Length;
        ShowError(null);
    }

    private void Backspace()
    {
        var caret = _field.Caret;
        if (caret == 0)
        {
            return;
        }

        _field.Text = _field.Text.Remove(caret - 1, 1);
        _field.Caret = caret - 1;
    }

    private void Paste()
    {
        var text = DisplayServer.ClipboardGet().ReplaceLineEndings(string.Empty).Trim();
        if (text.Length > 0)
        {
            Insert(text);
        }
    }

    private void ToggleShift()
    {
        _shifted = !_shifted;
        Relabel();
    }

    private void ToggleSymbols()
    {
        _onSymbols = !_onSymbols;
        Relabel();
    }

    private void ToggleReveal()
    {
        _field.Masked = !_field.Masked;
        _reveal!.Text = _field.Masked ? "Show" : "Hide";
    }

    private void Relabel()
    {
        var rows = _onSymbols ? Symbols : Letters;
        var index = 0;
        foreach (var row in rows)
        {
            foreach (var c in row)
            {
                _characterKeys[index++].Text = (_shifted ? char.ToUpperInvariant(c) : c).ToString();
            }
        }

        _shift.Text = _shifted ? "SHIFT" : "Shift";
        _symbols.Text = _onSymbols ? "Letters" : "Symbols";
    }

    private void Finish()
    {
        if (_finished)
        {
            return;
        }

        if (_request.Validate?.Invoke(_field.Text) is { } problem)
        {
            ShowError(problem);
            return;
        }

        _finished = true;
        Close();
        _request.Done(_field.Text);
    }

    private void Cancel()
    {
        if (_finished)
        {
            return;
        }

        _finished = true;
        Close();
        _request.Cancelled?.Invoke();
    }

    private void ShowError(string? problem)
    {
        _error.Visible = problem is not null;
        _error.Text = problem ?? string.Empty;
    }

    private static HBoxContainer Line(VBoxContainer keys)
    {
        var line = new HBoxContainer { Alignment = BoxContainer.AlignmentMode.Center, MouseFilter = MouseFilterEnum.Ignore };
        line.AddThemeConstantOverride("separation", 6);
        keys.AddChild(line);
        return line;
    }

    private static Button Key(HBoxContainer line, string text, float width)
    {
        var key = new Button { Text = text, CustomMinimumSize = new Vector2(width, 50), FocusMode = FocusModeEnum.All };
        line.AddChild(key);
        return key;
    }
}
