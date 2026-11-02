using System;
using Godot;
using Launcher.App.Grid;
using Launcher.App.Ui;
using Launcher.Core.Theming;

namespace Launcher.App.Screens;

/// <summary>
/// The titles under a grid's items, for the grid with labels (<see cref="GridLayout.Labels"/>): a label per pool cell,
/// up to two lines a column wide, its top middle where the grid says its item's foot shows (<see
/// cref="ItemGrid.TryGetLabel"/>), so it follows the scroll, the focused item's growth and the transitions. Drawn in the
/// overlay rather than the 3D, so the text is sharp at any resolution (the 3D is rendered at 1080p at most); under the
/// scrims, so the rows at the top and the bottom darken with their items. Labels change only when the grid says one may
/// have (<see cref="ItemGrid.LabelsVersion"/>), and a frame allocates nothing. Part of the overlay, at its base size.
/// </summary>
public sealed partial class GridLabels : Control
{
    private const int FontSize = 16;

    private readonly LabelSettings _plain;
    private readonly LabelSettings _focused;
    private Label[] _labels = [];
    private string?[] _titles = [];
    private Vector2[] _positions = [];
    private float[] _scales = [];
    private bool[] _shown = [];
    private bool[] _focus = [];
    private bool _visible;
    private float _alpha = -1;
    private int _version = -1;
    private Vector2 _size;
    private Vector2 _labelSize;

    public GridLabels(string name)
    {
        Name = name;
        MouseFilter = MouseFilterEnum.Ignore;
        Visible = false;
        SetAnchorsPreset(LayoutPreset.FullRect);

        // The colours are the theme's, set by Use: the launcher's own until then.
        var shadow = new Color(0, 0, 0, 0.7f);
        _plain = new LabelSettings { FontSize = FontSize, LineSpacing = -2, ShadowColor = shadow, ShadowSize = 3, ShadowOffset = Vector2.Zero };
        _focused = new LabelSettings { FontSize = FontSize, LineSpacing = -2, FontColor = Colors.White, ShadowSize = 6, ShadowOffset = Vector2.Zero };
        Use(OverlayPalette.Legacy);
    }

    /// <summary>Main thread: the labels take the theme's colours (A6 Menus), the list of titles' (<see cref="TitleList"/>).</summary>
    public void Use(OverlayPalette palette)
    {
        _plain.FontColor = UiStyle.Colour(palette.ListPlain);
        _focused.ShadowColor = UiStyle.Colour(palette.Glow);
    }

    /// <summary>Main thread, once a frame, after the grid's tick: shows its labels, if its layout has them. Allocates nothing once made.</summary>
    public void Update(ItemGrid grid)
    {
        var visible = grid.HasLabels && grid.Fade < 1;
        if (visible != _visible)
        {
            _visible = visible;
            Visible = visible;
            _version = -1;
        }

        if (!visible)
        {
            return;
        }

        // They fade with their grid.
        var alpha = 1 - grid.Fade;
        if (alpha != _alpha)
        {
            _alpha = alpha;
            Modulate = new Color(1, 1, 1, alpha);
        }

        var size = Size;
        if (grid.LabelsVersion == _version && size == _size)
        {
            return;
        }

        _version = grid.LabelsVersion;
        _size = size;
        if (_labels.Length != grid.PoolSize)
        {
            MakeLabels(grid.PoolSize);
        }

        // A column wide, less a little either side, and the grid's room for labels tall; laid out again only when that changes.
        var labelSize = new Vector2(Math.Max(grid.LabelWidth * size.X - 8, 16), ItemGrid.LabelRoom * size.Y);
        var resized = labelSize != _labelSize;
        _labelSize = labelSize;
        for (var cell = 0; cell < _labels.Length; cell++)
        {
            var label = _labels[cell];
            if (resized)
            {
                label.Size = labelSize;
                label.PivotOffset = new Vector2(labelSize.X / 2, 0);
            }

            // Scaled about its top middle, which stays at its item's foot.
            var position = Vector2.Zero;
            var shown = grid.TryGetLabel(cell, out var title, out var at, out var scale, out var focused);
            if (shown)
            {
                position = new Vector2(at.X * size.X - labelSize.X / 2, at.Y * size.Y);
                shown = position.Y < size.Y && position.Y + labelSize.Y * scale > 0;
            }

            if (!shown)
            {
                if (_shown[cell])
                {
                    _shown[cell] = false;
                    label.Visible = false;
                }

                continue;
            }

            // Compared with the title last set (a managed reference: reading Label.Text back would allocate).
            if (!string.Equals(_titles[cell], title, StringComparison.Ordinal))
            {
                _titles[cell] = title;
                label.Text = title;
            }

            if (focused != _focus[cell] || !_shown[cell])
            {
                _focus[cell] = focused;
                label.LabelSettings = focused ? _focused : _plain;
            }

            if (position != _positions[cell] || !_shown[cell])
            {
                _positions[cell] = position;
                label.Position = position;
            }

            if (scale != _scales[cell] || !_shown[cell])
            {
                _scales[cell] = scale;
                label.Scale = new Vector2(scale, scale);
            }

            if (!_shown[cell])
            {
                _shown[cell] = true;
                label.Visible = true;
            }
        }
    }

    /// <summary>A label per pool cell, made the first time the grid shows labels.</summary>
    private void MakeLabels(int count)
    {
        foreach (var label in _labels)
        {
            label.QueueFree();
        }

        _labels = new Label[count];
        _titles = new string?[count];
        _positions = new Vector2[count];
        _scales = new float[count];
        _shown = new bool[count];
        _focus = new bool[count];
        _labelSize = Vector2.Zero;
        for (var cell = 0; cell < count; cell++)
        {
            _labels[cell] = new Label
            {
                LabelSettings = _plain,
                MouseFilter = MouseFilterEnum.Ignore,
                AutowrapMode = TextServer.AutowrapMode.WordSmart,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Top,
                ClipText = true,
                MaxLinesVisible = 2,
                TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis,
                Visible = false,
            };
            AddChild(_labels[cell]);
        }
    }
}
