using System;
using Godot;
using Launcher.App.Theming;

namespace Launcher.App.Grid;

/// <summary>
/// Every pool cell's title, drawn by Godot's text renderer into one texture the item shader samples: a square block
/// per cell (wrapped, for a front with no art, a back or a label) and, optionally, a strip per cell for its spine.
/// Any script the fonts cover works, with system fallbacks. The viewport only redraws in a frame where a title
/// changed, and setting a label's text doesn't allocate managed memory.
/// <para>
/// A viewport costs about three times its pixels in GPU memory (measured: docs/perf/m5-navigation.md), so the blocks
/// and strips are no bigger than the items need on screen.
/// </para>
/// </summary>
public sealed partial class TitleAtlas : SubViewport
{
    private const int SpineWidth = 384;
    private const int SpineHeight = 24;
    private const int SpineFontSize = 16;
    private const int SpineColumns = 2;

    private readonly int _slots;
    private readonly int _blockSize;
    private readonly int _blockColumns;
    private readonly bool _withSpines;
    private Label[] _blocks = [];
    private Label[] _spines = [];
    private bool _dirty;
    private readonly string?[] _titles;

    /// <param name="blockSize">A block's side in pixels.</param>
    public TitleAtlas(int slots, int blockSize, bool withSpines)
    {
        _slots = slots;
        _blockSize = blockSize;
        _withSpines = withSpines;
        _titles = new string?[slots];
        _blockColumns = Mathf.CeilToInt(Mathf.Sqrt(slots));
        var blockRows = (slots + _blockColumns - 1) / _blockColumns;
        var spineRows = (slots + SpineColumns - 1) / SpineColumns;
        var width = _blockColumns * blockSize + (withSpines ? SpineColumns * SpineWidth : 0);
        var height = Mathf.Max(blockRows * blockSize, withSpines ? spineRows * SpineHeight : 0);
        Size = new Vector2I(width, height);
        TransparentBg = true;
        Disable3D = true;
        RenderTargetUpdateMode = UpdateMode.Once;
        RenderTargetClearMode = ClearMode.Always;
        CanvasItemDefaultTextureFilter = DefaultCanvasItemTextureFilter.Linear;
        Name = "TitleAtlas";
    }

    public override void _Ready()
    {
        var blockStyle = new LabelSettings
        {
            FontSize = BlockFontSize,
            LineSpacing = -_blockSize / 60f,
            FontColor = Colors.White,
        };
        var spineStyle = new LabelSettings { FontSize = SpineFontSize, FontColor = Colors.White };
        _blocks = new Label[_slots];
        _spines = new Label[_withSpines ? _slots : 0];
        for (var slot = 0; slot < _slots; slot++)
        {
            var block = new Label
            {
                LabelSettings = blockStyle,
                AutowrapMode = TextServer.AutowrapMode.WordSmart,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                ClipText = true,
                MaxLinesVisible = 4,
                TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis,
                Position = new Vector2(slot % _blockColumns * _blockSize, slot / _blockColumns * _blockSize),
                Size = new Vector2(_blockSize, _blockSize),
            };
            _blocks[slot] = block;
            AddChild(block);

            if (_withSpines)
            {
                var spine = new Label
                {
                    LabelSettings = spineStyle,
                    HorizontalAlignment = HorizontalAlignment.Center,
                    VerticalAlignment = VerticalAlignment.Center,
                    ClipText = true,
                    TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis,
                    Position = new Vector2(_blockColumns * _blockSize + slot % SpineColumns * SpineWidth, slot / SpineColumns * SpineHeight),
                    Size = new Vector2(SpineWidth, SpineHeight),
                };
                _spines[slot] = spine;
                AddChild(spine);
            }
        }
    }

    private int BlockFontSize => _blockSize / 7;

    public (int Block, int Spine) FontSizes => (BlockFontSize, _withSpines ? SpineFontSize : BlockFontSize);

    /// <summary>Main thread. The atlas redraws at the next <see cref="Flush"/>.</summary>
    public void SetTitle(int slot, string title)
    {
        // Compared with the title last set (a managed reference: reading Label.Text back would allocate per bind).
        if (string.Equals(_titles[slot], title, StringComparison.Ordinal))
        {
            return;
        }

        _titles[slot] = title;
        _blocks[slot].Text = title;
        if (_withSpines)
        {
            _spines[slot].Text = title;
        }

        _dirty = true;
    }

    /// <summary>Main thread, once per frame after binding: redraws the atlas if any title changed.</summary>
    public void Flush()
    {
        if (_dirty)
        {
            _dirty = false;
            RenderTargetUpdateMode = UpdateMode.Once;
        }
    }

    /// <summary>Points an item material at this atlas.</summary>
    public void ApplyTo(ShaderMaterial material)
    {
        var size = new Vector2(Size.X, Size.Y);
        material.SetShaderParameter(ShaderParams.Titles, GetTexture());
        material.SetShaderParameter(ShaderParams.BlockSize, new Vector2(_blockSize, _blockSize) / size);
        material.SetShaderParameter(ShaderParams.BlockColumns, _blockColumns);
        material.SetShaderParameter(ShaderParams.SpineOrigin, new Vector2(_blockColumns * _blockSize, 0) / size);
        material.SetShaderParameter(ShaderParams.SpineSize, new Vector2(SpineWidth, SpineHeight) / size);
        material.SetShaderParameter(ShaderParams.SpineColumns, SpineColumns);
    }
}
