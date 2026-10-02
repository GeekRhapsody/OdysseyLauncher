using System;
using Godot;

namespace Launcher.App.Screens;

/// <summary>
/// The games' titles as a list, on the left of the screen, for the list layout: the games grid shows the focused game's
/// model beside it (<see cref="Grid.GridShape.List"/>). It follows the grid's scroll, a line per title, so the two move
/// together; the focused title stays on a line a third of the way down, under a highlight. A fixed pool of labels is
/// re-bound as titles scroll into view, so a frame allocates nothing. Part of the overlay, at its base size.
/// </summary>
public sealed partial class TitleList : Control
{
    private const float RowHeight = 34;
    private const float FocusShare = 0.36f;
    private const float FadeRows = 1.5f;

    private readonly Label[] _titles;
    private readonly Label[] _systems;
    private readonly int[] _bound;
    private readonly Panel _highlight;
    private readonly LabelSettings _plain;
    private readonly LabelSettings _focused;
    private GamesSource? _source;
    private bool _showSystems;
    private float _scroll = float.NaN;
    private int _focus = -1;

    public TitleList()
    {
        Name = "TitleList";
        MouseFilter = MouseFilterEnum.Ignore;
        ClipContents = true;
        Visible = false;

        // Under the heading (title and system) and above the hints, on the left half.
        SetAnchorsPreset(LayoutPreset.LeftWide);
        OffsetLeft = 36;
        OffsetRight = 36 + 540;
        OffsetTop = 150;
        OffsetBottom = -64;

        var box = new StyleBoxFlat
        {
            BgColor = new Color(0.16f, 0.24f, 0.62f, 0.7f),
            BorderColor = new Color("#8FB2FF"),
            ShadowColor = new Color(0.35f, 0.5f, 1.0f, 0.4f),
            ShadowSize = 8,
        };
        box.SetBorderWidthAll(1);
        box.SetCornerRadiusAll(8);
        _highlight = new Panel { MouseFilter = MouseFilterEnum.Ignore, Size = new Vector2(540, RowHeight) };
        _highlight.AddThemeStyleboxOverride("panel", box);
        AddChild(_highlight);

        var shadow = new Color(0, 0, 0, 0.7f);
        _plain = new LabelSettings { FontSize = 19, FontColor = new Color("#C9D0E6"), ShadowColor = shadow, ShadowSize = 3, ShadowOffset = Vector2.Zero };
        _focused = new LabelSettings { FontSize = 19, FontColor = Colors.White, ShadowColor = new Color(0.35f, 0.5f, 1.0f, 0.55f), ShadowSize = 6, ShadowOffset = Vector2.Zero };
        var systemStyle = new LabelSettings { FontSize = 14, FontColor = new Color("#8E9CC6"), ShadowColor = shadow, ShadowSize = 3, ShadowOffset = Vector2.Zero };

        // Enough labels for the tallest list (2160p is the same 800-high base, stretched) and one coming in at each end.
        var pool = (int)(800 / RowHeight) + 3;
        _titles = new Label[pool];
        _systems = new Label[pool];
        _bound = new int[pool];
        Array.Fill(_bound, -1);
        for (var i = 0; i < pool; i++)
        {
            _titles[i] = new Label
            {
                LabelSettings = _plain,
                MouseFilter = MouseFilterEnum.Ignore,
                ClipText = true,
                TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis,
                VerticalAlignment = VerticalAlignment.Center,
                Size = new Vector2(520, RowHeight),
                Visible = false,
            };
            AddChild(_titles[i]);
            _systems[i] = new Label
            {
                LabelSettings = systemStyle,
                MouseFilter = MouseFilterEnum.Ignore,
                ClipText = true,
                HorizontalAlignment = HorizontalAlignment.Right,
                VerticalAlignment = VerticalAlignment.Center,
                Size = new Vector2(160, RowHeight),
                Visible = false,
            };
            AddChild(_systems[i]);
        }
    }

    /// <summary>The titles a page (LB, RB) moves through: those that show at once.</summary>
    public int RowsShown => Math.Max(1, (int)(Size.Y / RowHeight) - 1);

    /// <summary>
    /// Main thread: shows the source's titles (null hides the list). <paramref name="showSystems"/> adds each game's
    /// system on the right (Favourites and Recently played).
    /// </summary>
    public void Bind(GamesSource? source, bool showSystems)
    {
        _source = source;
        _showSystems = showSystems;
        Visible = source is not null;
        Array.Fill(_bound, -1);
        _scroll = float.NaN;
        _focus = -1;
        _highlight.Visible = false;
        foreach (var label in _titles)
        {
            label.Visible = false;
        }

        foreach (var label in _systems)
        {
            label.Visible = false;
        }
    }

    /// <summary>Main thread: the source's titles changed in place (a scrape, an edit), so the shown ones are set again.</summary>
    public void RefreshTitles()
    {
        Array.Fill(_bound, -1);
        _scroll = float.NaN;
    }

    /// <summary>Main thread, once a frame: the grid's scroll (in titles) and its focus. Allocates nothing.</summary>
    public void Update(float scroll, int focus)
    {
        if (_source is not { } source || (scroll == _scroll && focus == _focus))
        {
            return;
        }

        var height = Size.Y;
        var width = Size.X;
        var focusY = Mathf.Round(height * FocusShare / RowHeight) * RowHeight;
        var focusChanged = focus != _focus;
        _scroll = scroll;
        _focus = focus;

        // Titles from the one above the top to the one below the bottom; label i shows title n where n % pool == i.
        var pool = _titles.Length;
        var first = (int)MathF.Floor(scroll - focusY / RowHeight) - 1;
        for (var n = first; n < first + pool; n++)
        {
            var i = ((n % pool) + pool) % pool;
            var title = _titles[i];
            var system = _systems[i];
            if (n < 0 || n >= source.Count)
            {
                title.Visible = false;
                system.Visible = false;
                _bound[i] = -1;
                continue;
            }

            if (_bound[i] != n)
            {
                _bound[i] = n;
                title.Text = source.Row(n).Title;
                system.Text = _showSystems ? source.SystemName(n) : string.Empty;
                title.LabelSettings = n == focus ? _focused : _plain;
            }
            else if (focusChanged)
            {
                title.LabelSettings = n == focus ? _focused : _plain;
            }

            // Fades out over the last rows at the top and bottom, as the 3D items fade under the overlay's text.
            var y = focusY + (n - scroll) * RowHeight;
            var alpha = Math.Clamp(Math.Min(y + RowHeight, height - y) / (RowHeight * FadeRows), 0, 1);
            title.Visible = alpha > 0;
            title.Position = new Vector2(14, y);
            title.Size = new Vector2(width - (_showSystems ? 190 : 28), RowHeight);
            title.Modulate = new Color(1, 1, 1, alpha);
            system.Visible = _showSystems && alpha > 0;
            if (_showSystems)
            {
                system.Position = new Vector2(width - 174, y);
                system.Modulate = new Color(1, 1, 1, alpha);
            }
        }

        // The highlight goes to the focused title, which the scroll then brings to the focus line.
        _highlight.Visible = focus >= 0 && focus < source.Count;
        _highlight.Position = new Vector2(0, focusY + (focus - scroll) * RowHeight);
        _highlight.Size = new Vector2(width, RowHeight);
    }
}
