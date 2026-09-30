using System;
using Godot;

namespace Launcher.App.Ui;

/// <summary>
/// The on-screen keyboard's text box (M7): draws the text (or dots for a secret), a blinking caret, and scrolls
/// sideways so the caret stays in view in a long path. It never takes focus: the keyboard's keys have it, and the
/// keyboard edits <see cref="Text"/> and <see cref="Caret"/>. A click moves the caret.
/// </summary>
public sealed partial class TextField : Control
{
    private const int FontSize = 24;
    private const float Padding = 16;
    private static readonly StyleBoxFlat Box = UiStyle.RowBox(new Color(0.02f, 0.03f, 0.1f, 0.95f), new Color("#3A4C9A"), 1);

    private string _text = string.Empty;
    private int _caret;
    private float _scroll;
    private bool _caretShown = true;

    public TextField()
    {
        FocusMode = FocusModeEnum.None;
        ClipContents = true;
        CustomMinimumSize = new Vector2(0, 56);
        MouseFilter = MouseFilterEnum.Stop;
    }

    public string Text
    {
        get => _text;
        set
        {
            _text = value ?? string.Empty;
            _caret = Math.Clamp(_caret, 0, _text.Length);
            QueueRedraw();
        }
    }

    public int Caret
    {
        get => _caret;
        set
        {
            _caret = Math.Clamp(value, 0, _text.Length);
            _caretShown = true;
            QueueRedraw();
        }
    }

    /// <summary>Shows dots instead of the text (a credential).</summary>
    public bool Masked
    {
        get => _masked;
        set
        {
            _masked = value;
            QueueRedraw();
        }
    }

    private bool _masked;

    public string Placeholder { get; set; } = string.Empty;

    public void Blink()
    {
        _caretShown = !_caretShown;
        QueueRedraw();
    }

    public override void _Draw()
    {
        var font = GetThemeDefaultFont();
        var size = Size;
        DrawStyleBox(Box, new Rect2(Vector2.Zero, size));
        var shown = Masked ? new string('•', _text.Length) : _text;
        var baseline = (size.Y + font.GetAscent(FontSize) - font.GetDescent(FontSize)) / 2;
        if (shown.Length == 0)
        {
            DrawString(font, new Vector2(Padding, baseline), Placeholder, HorizontalAlignment.Left, -1, FontSize, UiStyle.Faint);
        }

        // Scroll so the caret stays inside the box.
        var caretX = font.GetStringSize(shown[.._caret], HorizontalAlignment.Left, -1, FontSize).X;
        var room = size.X - 2 * Padding;
        if (caretX - _scroll > room)
        {
            _scroll = caretX - room;
        }
        else if (caretX < _scroll)
        {
            _scroll = Math.Max(0, caretX - room / 3);
        }

        if (shown.Length > 0)
        {
            DrawString(font, new Vector2(Padding - _scroll, baseline), shown, HorizontalAlignment.Left, -1, FontSize, UiStyle.Text);
        }

        if (_caretShown)
        {
            var x = Padding - _scroll + caretX;
            DrawRect(new Rect2(x, (size.Y - FontSize * 1.2f) / 2, 2, FontSize * 1.2f), UiStyle.Accent);
        }
    }

    public override void _GuiInput(InputEvent @event)
    {
        if (@event is InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.Left } click)
        {
            Caret = IndexAt(click.Position.X);
            AcceptEvent();
        }
    }

    /// <summary>The caret position nearest to <paramref name="x"/> (in the field's coordinates).</summary>
    private int IndexAt(float x)
    {
        var font = GetThemeDefaultFont();
        var shown = Masked ? new string('•', _text.Length) : _text;
        var target = x - Padding + _scroll;
        var best = 0;
        var bestDistance = float.MaxValue;
        for (var i = 0; i <= shown.Length; i++)
        {
            var distance = Math.Abs(font.GetStringSize(shown[..i], HorizontalAlignment.Left, -1, FontSize).X - target);
            if (distance < bestDistance)
            {
                (best, bestDistance) = (i, distance);
            }
        }

        return best;
    }
}
