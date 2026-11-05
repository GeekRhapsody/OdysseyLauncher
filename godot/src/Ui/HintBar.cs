using System.Collections.Generic;
using Godot;
using Launcher.App.Navigation;

namespace Launcher.App.Ui;

/// <summary>One of the controls' hints: the button's glyph, or two buttons' (B / Menu), then what it does.</summary>
public readonly record struct Hint(string Text, Prompt First, Prompt? Second = null);

/// <summary>
/// The controls' hints along the bottom of a screen: each one's glyphs for the device in use (<see cref="ButtonPrompts"/>,
/// docs/ARCHITECTURE.md A1 "Button icons") and its words, right-aligned. The glyphs take the words' colour (their
/// <see cref="LabelSettings"/>' font colour, followed when it changes), so a theme's palette tints both. Callers keep
/// their hints in static arrays: <see cref="Show"/> with the array already shown does nothing, so a screen can show its
/// hints as often as it likes. A hint none of whose buttons the device has (the right stick, on a keyboard) is left out.
/// </summary>
public sealed partial class HintBar : HBoxContainer
{
    private const int GapBetweenHints = 18;
    private const int GapInHint = 4;

    private readonly LabelSettings _settings;
    private readonly float _glyphSize;
    private readonly List<HBoxContainer> _items = [];
    private Hint[] _hints = [];
    private bool _padOnly;

    /// <param name="settings">The words' look: their font size sets the glyphs' size, and their colour the glyphs'.</param>
    public HintBar(LabelSettings settings)
    {
        _settings = settings;
        _glyphSize = Mathf.Round(settings.FontSize * 1.6f);
        Alignment = AlignmentMode.End;
        MouseFilter = MouseFilterEnum.Ignore;
        AddThemeConstantOverride("separation", GapBetweenHints);
    }

    /// <summary>The words' look, whose font colour the glyphs take too.</summary>
    public LabelSettings Settings => _settings;

    /// <summary>Main thread: shows <paramref name="hints"/>, unless they're the array already shown.</summary>
    /// <param name="padOnly">
    /// A pad's glyphs even while the keyboard is the device in use (the last pad used's, or Xbox's): for the on-screen
    /// keyboard, which the pad drives while the keyboard types.
    /// </param>
    public void Show(Hint[] hints, bool padOnly = false)
    {
        if (ReferenceEquals(hints, _hints) && padOnly == _padOnly)
        {
            return;
        }

        _hints = hints;
        _padOnly = padOnly;
        Refresh();
    }

    public override void _EnterTree()
    {
        ButtonPrompts.Changed += Refresh;
        _settings.Changed += Tint;
        Refresh();
    }

    public override void _ExitTree()
    {
        ButtonPrompts.Changed -= Refresh;
        _settings.Changed -= Tint;
    }

    /// <summary>Lays the hints out again with the glyphs of the device in use, reusing the nodes already made.</summary>
    private void Refresh()
    {
        var kind = _padOnly ? ButtonPrompts.PadKind : ButtonPrompts.Kind;
        for (var i = 0; i < _hints.Length; i++)
        {
            var hint = _hints[i];
            var item = Item(i);
            var glyphs = Place(item, 0, ButtonPrompts.Glyphs(kind, hint.First));
            if (hint.Second is { } second)
            {
                glyphs = Place(item, glyphs, ButtonPrompts.Glyphs(kind, second));
            }

            // The rest of the item's glyphs are hidden; its last child is the words.
            for (var g = glyphs; g < item.GetChildCount() - 1; g++)
            {
                item.GetChild<TextureRect>(g).Visible = false;
            }

            var words = item.GetChild<Label>(item.GetChildCount() - 1);
            words.Text = hint.Text;
            item.Visible = glyphs > 0;
        }

        for (var i = _hints.Length; i < _items.Count; i++)
        {
            _items[i].Visible = false;
        }

        Tint();
    }

    /// <summary>Shows <paramref name="textures"/> in <paramref name="item"/>'s glyphs from <paramref name="first"/>; returns how many it now shows.</summary>
    private int Place(HBoxContainer item, int first, Texture2D[] textures)
    {
        foreach (var texture in textures)
        {
            if (first == item.GetChildCount() - 1)
            {
                var glyph = new TextureRect
                {
                    ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
                    StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
                    CustomMinimumSize = new Vector2(_glyphSize, _glyphSize),
                    MouseFilter = MouseFilterEnum.Ignore,
                };
                item.AddChild(glyph);
                item.MoveChild(glyph, first);
            }

            var rect = item.GetChild<TextureRect>(first);
            rect.Texture = texture;
            rect.Visible = true;
            first++;
        }

        return first;
    }

    /// <summary>The <paramref name="index"/>th hint's box (its glyphs, then its words), made the first time it's needed.</summary>
    private HBoxContainer Item(int index)
    {
        if (index < _items.Count)
        {
            return _items[index];
        }

        var item = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        item.AddThemeConstantOverride("separation", GapInHint);
        item.AddChild(new Label { LabelSettings = _settings, VerticalAlignment = VerticalAlignment.Center, MouseFilter = MouseFilterEnum.Ignore });
        AddChild(item);
        _items.Add(item);
        return item;
    }

    /// <summary>The glyphs take the words' colour.</summary>
    private void Tint()
    {
        var colour = _settings.FontColor;
        foreach (var item in _items)
        {
            for (var g = 0; g < item.GetChildCount() - 1; g++)
            {
                item.GetChild<TextureRect>(g).SelfModulate = colour;
            }
        }
    }
}
