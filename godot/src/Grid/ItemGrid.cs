using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Models;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.Core.Library;
using Launcher.Core.Theming;

namespace Launcher.App.Grid;

/// <summary>What a grid cell shows. Filled by an <see cref="IGridSource"/>; no strings are built for it.</summary>
public struct CellInfo
{
    public string Title;

    /// <summary>Index into the grid's templates.</summary>
    public int Template;

    /// <summary>The colour of a box with no art, or of a system card.</summary>
    public Color Plain;
}

/// <summary>The items a grid shows, in order.</summary>
public interface IGridSource
{
    int Count { get; }

    /// <summary>Main thread, while binding: must not allocate.</summary>
    void Describe(int index, out CellInfo cell);

    /// <summary>
    /// Main thread, while binding: the item's media of the kind in slot number <paramref name="slot"/>
    /// (<see cref="MediaSlots"/>), if it has one. Must not allocate.
    /// </summary>
    bool TryGetMedia(int index, int slot, out MediaRef media);

    /// <summary>Whether any item uses the template (so its MultiMesh is drawn at all).</summary>
    bool UsesTemplate(int template);
}

/// <summary>
/// A virtualised 3D grid (A1 Grid): a pool of cells covering the visible rows plus a margin, re-bound as rows scroll
/// into view rather than recreated. Each template is one <see cref="MultiMesh"/> with a fixed instance per cell, and
/// a material of the one item shader (shared by templates with the same authored textures and tint). Every cell has a
/// fixed layer per slot channel in the streamer's arrays, a row of the slot-state texture and a fixed place in the
/// title atlas. The items never move to scroll: the grid's root does (one transform), so a frame only touches newly
/// bound rows, the focused items and fading slots. One <c>Tick</c> drives everything, and nothing in it allocates.
/// <para>
/// Each slot of a cell's template walks its fallback chain (A7, M6) against the item's media: the first media kind it
/// has is requested, and the chain's next <c>generated</c> or <c>authored</c> entry shows until it arrives (or if its
/// derivative turns out missing, the walk carries on). <see cref="RefreshItem"/> redoes that for one item after its
/// media changed, keeping its model and every slot whose media is the same.
/// </para>
/// </summary>
public sealed partial class ItemGrid : Node3D, ITextureSink
{
    public const int MinColumns = 3;
    public const int MaxColumns = 9;
    public const int PreferredColumns = 5;

    private const float PitchXFactor = 1.42f;
    private const float PitchYFactor = 1.3f;
    private const float FadeSeconds = 0.18f;
    private const float FocusBlendPerSecond = 7.0f;
    private const float FocusLift = 0.55f;
    private const float FocusScale = 1.12f;
    private const float ScrollSmoothTime = 0.11f;
    private const int Slots = MediaSlots.Count;

    private static readonly Transform3D Hidden = new(new Basis(Vector3.Zero, Vector3.Zero, Vector3.Zero), Vector3.Zero);
    private static readonly Shader ItemShader = GD.Load<Shader>("res://shaders/item.gdshader");

    private readonly TextureStreamer? _streamer;
    private readonly int _maxCells;
    private readonly bool _systemCards;
    private readonly List<ItemTemplate> _templates = [];
    private readonly List<bool> _perItem = [];
    private readonly List<MultiMesh> _multiMeshes = [];
    private readonly List<MultiMeshInstance3D> _instances = [];
    private readonly List<ShaderMaterial> _materials = [];
    private readonly List<ItemTemplate> _materialOwners = [];
    private readonly List<int> _templateMaterial = [];
    private readonly List<float> _fit = [];
    private readonly TitleAtlas _atlas;
    private readonly Node3D _root = new() { Name = "Items" };
    private readonly Image _stateImage;
    private readonly ImageTexture _stateTexture;
    private bool _stateDirty;

    // Per pool cell.
    private readonly int[] _cellItem;
    private readonly int[] _cellTemplate;
    private readonly float[] _cellPhase;
    private readonly Color[] _cellPlain;
    private readonly Transform3D[] _cellBase;

    // Per pool cell and slot: cell × Slots + slot.
    private readonly bool[] _wanted;
    private readonly bool[] _textured;
    private readonly float[] _fade;
    private readonly byte[] _fallback;
    private readonly int[] _next;
    private readonly MediaRef[] _media;
    private int[] _boundRow = [];

    private IGridSource? _source;
    private int _count;
    private int _columns = 1;
    private int _poolRows = 1;
    private int _rows;
    private float _pitchX = 1;
    private float _pitchY = 1;
    private float _cellWidth = 1;
    private float _itemHeight = 1;
    private float _scale = 1;
    private float _viewHeight = 4.4f;
    private float _viewAspect = 1.6f;
    private float _cameraDistance = 6.2f;
    private float _rowsVisible = 3.4f;
    private float _focusLine = 0.5f;

    private float _scroll;
    private float _scrollVelocity;
    private float _targetScroll;
    private int _focus = -1;
    private int _focusCell = -1;
    private int _previousCell = -1;
    private float _focusBlend;
    private float _previousBlend;
    private float _focusTime;
    private float _launchTime = -1;
    private int _fadingSlots;
    private bool _texturesEnabled = true;

    private float _gridFade;
    private Vector3 _offset;
    private float _zoom = 1;
    private bool _rootDirty = true;
    private LookColours _background;

    /// <param name="streamer">The media streamer, or null for a grid without media (the systems grid).</param>
    /// <param name="systemCards">A grid of system cards: their plain materials can take the system's colour.</param>
    /// <param name="blockSize">The title atlas's block size in pixels.</param>
    public ItemGrid(TextureStreamer? streamer, LookColours background, int maxCells, int blockSize, bool spines, bool systemCards)
    {
        Name = "Grid";
        _streamer = streamer;
        _maxCells = maxCells;
        _systemCards = systemCards;
        _background = background;
        _cellItem = new int[maxCells];
        _cellTemplate = new int[maxCells];
        _cellPhase = new float[maxCells];
        _cellPlain = new Color[maxCells];
        _cellBase = new Transform3D[maxCells];
        _wanted = new bool[maxCells * Slots];
        _textured = new bool[maxCells * Slots];
        _fade = new float[maxCells * Slots];
        _fallback = new byte[maxCells * Slots];
        _next = new int[maxCells * Slots];
        _media = new MediaRef[maxCells * Slots];
        Array.Fill(_cellItem, -1);
        Array.Fill(_cellTemplate, -1);

        // One texel per cell and slot (item.gdshader): the fallback shown without media, the media's aspect (0: none
        // wanted), its fade, and its layer. Made once; only updated after that.
        _stateImage = Image.CreateEmpty(Slots, maxCells, false, Image.Format.Rgbaf);
        _stateTexture = ImageTexture.CreateFromImage(_stateImage);
        _atlas = new TitleAtlas(maxCells, blockSize, spines);
    }

    public int Count => _count;

    public int Columns => _columns;

    public int FocusIndex => _focus;

    public int Rows => _rows;

    /// <summary>The source currently bound, or null.</summary>
    public IGridSource? Source => _source;

    /// <summary>The templates the grid can show, indexed by <see cref="CellInfo.Template"/>.</summary>
    public IReadOnlyList<ItemTemplate> Templates => _templates;

    /// <summary>Rows of items that fit the view's height (sets the items' size on screen).</summary>
    public float RowsVisible
    {
        get => _rowsVisible;
        set => _rowsVisible = value;
    }

    /// <summary>0 = shown, 1 = faded into the background (then not drawn at all).</summary>
    public float Fade
    {
        get => _gridFade;
        set
        {
            if (_gridFade == value)
            {
                return;
            }

            _gridFade = value;
            foreach (var material in _materials)
            {
                material.SetShaderParameter(ShaderParams.GridFade, value);
            }

            Visible = value < 1;
        }
    }

    /// <summary>Moves the whole grid, for transitions.</summary>
    public Vector3 Offset
    {
        get => _offset;
        set
        {
            _offset = value;
            _rootDirty = true;
        }
    }

    /// <summary>Scales the whole grid, for transitions.</summary>
    public float Zoom
    {
        get => _zoom;
        set
        {
            _zoom = value;
            _rootDirty = true;
        }
    }

    /// <summary>True once every on-screen slot that wants media shows it (the bench's "visible textured").</summary>
    public bool VisibleTextured { get; private set; }

    /// <summary>The share of on-screen media slots that show their media this frame; 1 when none wants any.</summary>
    public float VisibleTexturedFraction { get; private set; } = 1;

    /// <summary>Whether any on-screen slot wants media this frame.</summary>
    public bool AnyVisibleArt { get; private set; }

    public override void _Ready()
    {
        AddChild(_atlas);
        AddChild(_root);
        foreach (var material in _materials)
        {
            _atlas.ApplyTo(material);
        }
    }

    /// <summary>
    /// Main thread: replaces every template (a theme was applied). Unbinds everything; bind a source again after.
    /// </summary>
    public void SetTemplates(IReadOnlyList<ItemTemplate> templates)
    {
        UnbindAll();
        foreach (var instance in _instances)
        {
            instance.QueueFree();
        }

        _templates.Clear();
        _perItem.Clear();
        _multiMeshes.Clear();
        _instances.Clear();
        _materials.Clear();
        _materialOwners.Clear();
        _templateMaterial.Clear();
        _fit.Clear();
        foreach (var template in templates)
        {
            AddTemplate(template, perItem: false);
        }
    }

    /// <summary>
    /// Main thread: adds a template, such as a per-game model once it has loaded (A7). A per-item template doesn't
    /// change the grid's pitch: it's scaled down to fit the cell.
    /// </summary>
    public int AddTemplate(ItemTemplate template, bool perItem)
    {
        for (var t = 0; t < _templates.Count; t++)
        {
            if (_templates[t] == template)
            {
                return t;
            }
        }

        var material = MaterialFor(template);

        var multiMesh = new MultiMesh
        {
            TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
            UseCustomData = true,
            Mesh = template.Mesh,
            InstanceCount = _maxCells,
        };
        for (var cell = 0; cell < _maxCells; cell++)
        {
            multiMesh.SetInstanceTransform(cell, Hidden);
            multiMesh.SetInstanceCustomData(cell, new Color(cell, 0, 0, 0));
        }

        var instance = new MultiMeshInstance3D
        {
            Name = template.Mesh.ResourceName,
            Multimesh = multiMesh,
            MaterialOverride = material,
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            Visible = perItem,
        };
        _root.AddChild(instance);
        _templates.Add(template);
        _perItem.Add(perItem);
        _multiMeshes.Add(multiMesh);
        _instances.Add(instance);
        _fit.Add(FitOf(template, perItem));
        return _templates.Count - 1;
    }

    /// <summary>
    /// A material for the template: shared with any template whose authored textures and tint are the same (every
    /// built-in box), since only those differ between them. Binding the texture arrays to one material instead of five
    /// kept the working set as it was in M5.
    /// </summary>
    private ShaderMaterial MaterialFor(ItemTemplate template)
    {
        for (var m = 0; m < _materials.Count; m++)
        {
            var owner = _materialOwners[m];
            if (owner.Tint == template.Tint && SameTextures(owner, template))
            {
                _templateMaterial.Add(m);
                return _materials[m];
            }
        }

        var material = new ShaderMaterial { Shader = ItemShader };
        material.SetShaderParameter(ShaderParams.GridFade, _gridFade);
        material.SetShaderParameter(ShaderParams.TintCase, _systemCards && template.Tint);
        material.SetShaderParameter(ShaderParams.SlotState, _stateTexture);
        for (var i = 0; i < ItemTemplate.MaxAuthoredTextures; i++)
        {
            if (template.Authored[i] is { } texture)
            {
                material.SetShaderParameter(ShaderParams.Authored[i], texture);
            }
        }

        _background.ApplyTo(material);
        if (IsInsideTree())
        {
            _atlas.ApplyTo(material);
        }

        if (_texturesEnabled && _streamer is not null)
        {
            SetArrays(material);
        }

        _materials.Add(material);
        _materialOwners.Add(template);
        _templateMaterial.Add(_materials.Count - 1);
        return material;

        static bool SameTextures(ItemTemplate a, ItemTemplate b)
        {
            for (var i = 0; i < ItemTemplate.MaxAuthoredTextures; i++)
            {
                if (a.Authored[i] != b.Authored[i])
                {
                    return false;
                }
            }

            return true;
        }
    }

    /// <summary>The look's corners, for items fading into the background (every frame of a look's cross-fade).</summary>
    public void SetBackground(in LookColours background)
    {
        _background = background;
        foreach (var material in _materials)
        {
            background.ApplyTo(material);
        }
    }

    /// <summary>
    /// The camera's view at the grid's plane (z = 0), in world units, and the camera's distance from it. Call again
    /// when the window's shape changes.
    /// </summary>
    public void SetView(float viewHeight, float viewAspect, float cameraDistance)
    {
        _cameraDistance = cameraDistance;
        _viewHeight = viewHeight;
        _viewAspect = viewAspect;
        if (_source is not null)
        {
            Bind(_source, Math.Max(_focus, 0));
        }
    }

    /// <summary>Main thread: shows a new source, focused on <paramref name="focus"/>, and binds the visible rows.</summary>
    public void Bind(IGridSource source, int focus)
    {
        UnbindAll();
        _source = source;
        _count = source.Count;

        var width = 0.1f;
        var height = 0.1f;
        for (var t = 0; t < _templates.Count; t++)
        {
            var used = source.UsesTemplate(t);
            _instances[t].Visible = used;
            if (used && !_perItem[t])
            {
                width = Math.Max(width, _templates[t].Size.X);
                height = Math.Max(height, _templates[t].Size.Y);
            }
        }

        _cellWidth = width;
        _pitchX = width * PitchXFactor;
        _pitchY = height * PitchYFactor;
        _itemHeight = height;
        for (var t = 0; t < _templates.Count; t++)
        {
            _fit[t] = FitOf(_templates[t], _perItem[t]);
        }

        // Items are sized so RowsVisible rows fit the height, unless that leaves fewer than PreferredColumns across
        // (wide templates such as jewel cases): then they're sized to fit those columns, and more rows show.
        var usableWidth = _viewHeight * _viewAspect * 0.9f;
        _scale = Math.Min(_viewHeight / (_rowsVisible * _pitchY), usableWidth / (PreferredColumns * _pitchX));
        var rowsShown = _viewHeight / (_pitchY * _scale);
        var fit = (int)(usableWidth / (_pitchX * _scale));
        _columns = Math.Clamp(fit, MinColumns, MaxColumns);
        _rows = (_count + _columns - 1) / _columns;

        // The pool covers the visible rows plus a margin, or every row when there are fewer; a full pool that
        // doesn't fit the cells gives up columns.
        _poolRows = Math.Max(1, Math.Min(Mathf.CeilToInt(rowsShown) + 3, _rows));
        while (_columns > MinColumns && _columns * _poolRows > _maxCells)
        {
            _columns--;
            _rows = (_count + _columns - 1) / _columns;
            _poolRows = Math.Max(1, Math.Min(Mathf.CeilToInt(rowsShown) + 3, _rows));
        }

        _boundRow = new int[_poolRows];
        Array.Fill(_boundRow, -1);

        // The focused row sits a little above the middle; the overlay's title is above it and its details below.
        _focusLine = _viewHeight * 0.12f;
        _focus = _count == 0 ? -1 : Math.Clamp(focus, 0, _count - 1);
        _targetScroll = _scroll = _focus < 0 ? 0 : _focus / _columns;
        _scrollVelocity = 0;
        _focusCell = _previousCell = -1;
        _focusBlend = _previousBlend = 0;
        _launchTime = -1;
        VisibleTextured = false;
        _rootDirty = true;
        BindVisibleRows();
    }

    /// <summary>Main thread: hides every item and drops every media request.</summary>
    public void UnbindAll()
    {
        for (var cell = 0; cell < _maxCells; cell++)
        {
            HideCell(cell);
        }

        Array.Fill(_boundRow, -1);
        _fadingSlots = 0;
        _source = null;
        _count = 0;
    }

    /// <summary>
    /// Main thread: the item's media (or its template) changed, so its bound cell, if any, walks its slot chains again.
    /// Its model stays; slots whose media is unchanged keep their layers; a slot whose derivative was missing tries again.
    /// </summary>
    public void RefreshItem(int item)
    {
        var cell = CellOf(item);
        if (cell < 0 || _source is null)
        {
            return;
        }

        _source.Describe(item, out var info);
        var template = Math.Clamp(info.Template, 0, _templates.Count - 1);
        if (template != _cellTemplate[cell])
        {
            _multiMeshes[_cellTemplate[cell]].SetInstanceTransform(cell, Hidden);
            _cellTemplate[cell] = template;
            _instances[template].Visible = true;
            _cellBase[cell] = BaseTransform(template, _cellBase[cell].Origin);
            SetCellTransform(cell, _cellBase[cell]);
            WriteCustom(cell);
        }

        ResolveSlots(cell, item, refresh: true);
    }

    /// <summary>Main thread: moves the focus by <paramref name="step"/> items, stopping at the ends of a row for ±1.</summary>
    public bool MoveFocus(int step)
    {
        if (_count == 0)
        {
            return false;
        }

        var column = _focus % _columns;
        if ((step == -1 && column == 0) || (step == 1 && (column == _columns - 1 || _focus == _count - 1)))
        {
            return false;
        }

        var target = _focus + step;
        if (target < 0 || target >= _count)
        {
            // A move down from the last full row goes to the last item; up from the first row stays.
            if (step > 0 && _focus / _columns < _rows - 1)
            {
                target = _count - 1;
            }
            else
            {
                return false;
            }
        }

        SetFocus(target);
        return true;
    }

    /// <summary>Main thread: focuses an item and scrolls its row to the focus line.</summary>
    public void SetFocus(int index)
    {
        if (_count == 0)
        {
            return;
        }

        _focus = Math.Clamp(index, 0, _count - 1);
        _targetScroll = _focus / _columns;
    }

    /// <summary>
    /// The scripted scroll (bench): sets the scroll row directly, with the focus following the row at the focus line.
    /// </summary>
    public void SetScrollDirect(float row, float velocity)
    {
        _scroll = _targetScroll = row;
        _scrollVelocity = velocity;
        var focusRow = Math.Clamp((int)(row + 0.5f), 0, Math.Max(_rows - 1, 0));
        _focus = Math.Min(_count - 1, focusRow * _columns + _columns / 2);
        _rootDirty = true;
    }

    /// <summary>The focused item spins up and flies towards the camera (the A7 launch fallback).</summary>
    public void PlayLaunch() => _launchTime = 0;

    public void StopLaunch() => _launchTime = -1;

    /// <summary>Stops streaming and frees nothing; the next <see cref="EnableTextures"/> re-requests what's bound.</summary>
    public void DisableTextures()
    {
        _texturesEnabled = false;
        for (var cell = 0; cell < _maxCells; cell++)
        {
            _streamer?.CancelCell(cell);
            for (var slot = 0; slot < Slots; slot++)
            {
                var i = cell * Slots + slot;
                if (_textured[i])
                {
                    _textured[i] = false;
                    _fade[i] = 0;
                    WriteState(cell, slot);
                }
            }
        }

        _fadingSlots = 0;
        foreach (var material in _materials)
        {
            material.SetShaderParameter(ShaderParams.SlotsLarge, default(Variant));
            material.SetShaderParameter(ShaderParams.SlotsSmall, default(Variant));
        }
    }

    /// <summary>After the streamer's arrays are (re)created: points the materials at them and re-requests every bound slot.</summary>
    public void EnableTextures()
    {
        _texturesEnabled = true;
        if (_streamer is null)
        {
            return;
        }

        foreach (var material in _materials)
        {
            SetArrays(material);
        }

        if (_source is null)
        {
            return;
        }

        for (var cell = 0; cell < _maxCells; cell++)
        {
            if (_cellItem[cell] >= 0)
            {
                ResolveSlots(cell, _cellItem[cell], refresh: true);
            }
        }
    }

    /// <summary>
    /// Warm-up after interactive: shows one instance of every template, faded into the background, so each pipeline
    /// is compiled before it's first needed (A3). <see cref="EndWarmUp"/> hides them again.
    /// </summary>
    public void BeginWarmUp()
    {
        Visible = true;
        for (var t = 0; t < _templates.Count; t++)
        {
            _materials[_templateMaterial[t]].SetShaderParameter(ShaderParams.GridFade, 1.0f);
            _instances[t].Visible = true;
            _multiMeshes[t].SetInstanceTransform(0, new Transform3D(Basis.Identity, new Vector3(t * 0.3f, 0, -2)));
        }

        _rootDirty = true;
    }

    public void EndWarmUp()
    {
        for (var t = 0; t < _templates.Count; t++)
        {
            _multiMeshes[t].SetInstanceTransform(0, _cellTemplate[0] == t ? _cellBase[0] : Hidden);
            _instances[t].Visible = _source?.UsesTemplate(t) ?? false;
            _materials[_templateMaterial[t]].SetShaderParameter(ShaderParams.GridFade, _gridFade);
        }

        Visible = _gridFade < 1;
    }

    /// <summary>The font sizes the title atlas draws at, for the glyph warm-up.</summary>
    public (int Block, int Spine) AtlasFontSizes => _atlas.FontSizes;

    /// <summary>Called by the owner each frame (the grid's one per-frame update).</summary>
    public void Tick(float dt)
    {
        if (_source is not null)
        {
            SmoothScroll(dt);
            UpdateRoot();
            BindVisibleRows();
            UpdateFocus(dt);
            AnimateFades(dt);
            MeasureTexturing();
        }
        else
        {
            UpdateRoot();
        }

        _atlas.Flush();
        if (_stateDirty)
        {
            _stateDirty = false;
            _stateTexture.Update(_stateImage);
        }
    }

    /// <summary>Main thread, once per frame, after <see cref="Tick"/>: uploads media within the budget.</summary>
    public void PumpTextures(long budgetBytes, int cap)
    {
        if (_streamer is not null && _texturesEnabled && _source is not null)
        {
            _streamer.SetView(_scroll, _scrollVelocity);
            _streamer.PumpUploads(this, budgetBytes, cap);
        }
    }

    public void OnLayerReady(int cell, int channel)
    {
        var slot = _streamer!.Layout.Slots[channel];
        var i = cell * Slots + slot;
        if (_cellItem[cell] < 0 || !_wanted[i] || _textured[i])
        {
            return;
        }

        _textured[i] = true;
        _fadingSlots++;
    }

    public void OnLayerMissing(int cell, int channel)
    {
        var item = _cellItem[cell];
        var slot = _streamer!.Layout.Slots[channel];
        var i = cell * Slots + slot;
        if (item < 0 || !_wanted[i] || _source is null || _templates[_cellTemplate[cell]].Chain(slot) is not { } chain)
        {
            return;
        }

        // No derivative yet (or a broken one): carry on down the chain, to the next media kind or the fallback.
        var media = new SourceMedia(_source, item, true);
        var resolution = chain.Resolve(_next[i], ref media);
        Apply(cell, slot, channel, resolution, item);
    }

    // ---- Binding --------------------------------------------------------------------------------

    private void VisibleRange(out int first, out int last)
    {
        var rowWorld = _pitchY * _scale * _zoom;
        var above = (_viewHeight / 2 - _focusLine) / rowWorld + 0.5f;
        var below = (_viewHeight / 2 + _focusLine) / rowWorld + 0.5f;
        first = Math.Max(0, (int)MathF.Floor(_scroll - above));
        last = Math.Min(_rows - 1, (int)MathF.Ceiling(_scroll + below));
    }

    private void BindVisibleRows()
    {
        // The pool's spare rows go ahead of the scroll: one behind, the rest in front.
        VisibleRange(out var first, out var last);
        var spare = Math.Max(0, _poolRows - (last - first + 1));
        var behind = Math.Min(1, spare);
        var from = _scrollVelocity >= 0 ? first - behind : first - (spare - behind);
        from = Math.Clamp(from, 0, Math.Max(0, _rows - _poolRows));
        var to = Math.Min(_rows - 1, from + _poolRows - 1);
        for (var row = from; row <= to; row++)
        {
            var poolRow = row % _poolRows;
            if (_boundRow[poolRow] != row)
            {
                BindRow(poolRow, row);
            }
        }
    }

    private void BindRow(int poolRow, int row)
    {
        _boundRow[poolRow] = row;
        for (var column = 0; column < _columns; column++)
        {
            var cell = poolRow * _columns + column;
            var item = row * _columns + column;
            if (cell == _focusCell)
            {
                _focusCell = -1;
            }

            if (cell == _previousCell)
            {
                _previousCell = -1;
            }

            if (item >= _count)
            {
                HideCell(cell);
                continue;
            }

            _source!.Describe(item, out var info);
            var template = Math.Clamp(info.Template, 0, _templates.Count - 1);
            if (_cellTemplate[cell] >= 0 && _cellTemplate[cell] != template)
            {
                _multiMeshes[_cellTemplate[cell]].SetInstanceTransform(cell, Hidden);
            }

            _cellItem[cell] = item;
            _cellTemplate[cell] = template;
            _cellPlain[cell] = info.Plain;
            _cellPhase[cell] = item * 2.39996f % Mathf.Tau;

            // A grid of one part-filled row is centred; otherwise rows fill from the left.
            var shown = _rows == 1 ? _count : _columns;
            var x = (column - (shown - 1) / 2.0f) * _pitchX;
            _cellBase[cell] = BaseTransform(template, new Vector3(x, -row * _pitchY - _itemHeight / 2, 0));
            _multiMeshes[template].SetInstanceTransform(cell, _cellBase[cell]);
            WriteCustom(cell);
            _atlas.SetTitle(cell, info.Title);
            ResolveSlots(cell, item, refresh: false);
        }
    }

    /// <summary>
    /// Walks each of the cell's template slots down its chain against the item's media. On a refresh, a slot whose
    /// media is the same as before keeps its layer (and its request in flight).
    /// </summary>
    private void ResolveSlots(int cell, int item, bool refresh)
    {
        var template = _templates[_cellTemplate[cell]];
        for (var slot = 0; slot < Slots; slot++)
        {
            var i = cell * Slots + slot;
            if (template.Chain(slot) is not { } chain)
            {
                ClearSlot(cell, slot);
                continue;
            }

            // A slot the grid has no layers for (a per-game model's slot the theme never fills) shows its fallback.
            var channel = _streamer is null ? -1 : _streamer.Layout.ChannelOf(slot);
            var media = new SourceMedia(_source!, item, channel >= 0);
            var resolution = chain.Resolve(0, ref media);
            if (refresh && resolution.MediaSlot >= 0 && _wanted[i]
                && _source!.TryGetMedia(item, resolution.MediaSlot, out var current) && current == _media[i])
            {
                if (!_textured[i] && _texturesEnabled && _streamer?.HasArrays == true)
                {
                    _streamer.Request(cell, channel, item / _columns, _media[i]);
                }

                continue;
            }

            Apply(cell, slot, channel, resolution, item);
        }
    }

    /// <summary>Shows a resolution in a cell's slot: requests its media, or shows its fallback.</summary>
    private void Apply(int cell, int slot, int channel, SlotResolution resolution, int item)
    {
        var i = cell * Slots + slot;
        if (_textured[i] && _fade[i] < 1)
        {
            _fadingSlots--;
        }

        _textured[i] = false;
        _fade[i] = 0;
        _fallback[i] = resolution.Fallback == SlotSourceKind.Generated ? (byte)1 : (byte)0;
        _next[i] = resolution.Next;
        if (resolution.MediaSlot >= 0 && _source!.TryGetMedia(item, resolution.MediaSlot, out var media))
        {
            _wanted[i] = true;
            _media[i] = media;
            if (_texturesEnabled && _streamer?.HasArrays == true)
            {
                _streamer.Request(cell, channel, item / _columns, media);
            }
        }
        else
        {
            _wanted[i] = false;
            _media[i] = default;
            if (channel >= 0)
            {
                _streamer?.Cancel(cell, channel);
            }
        }

        WriteState(cell, slot);
    }

    private void ClearSlot(int cell, int slot)
    {
        var i = cell * Slots + slot;
        if (_textured[i] && _fade[i] < 1)
        {
            _fadingSlots--;
        }

        _wanted[i] = false;
        _textured[i] = false;
        _fade[i] = 0;
        _media[i] = default;
    }

    private void HideCell(int cell)
    {
        if (_cellTemplate[cell] >= 0)
        {
            _multiMeshes[_cellTemplate[cell]].SetInstanceTransform(cell, Hidden);
            _cellTemplate[cell] = -1;
        }

        _cellItem[cell] = -1;
        for (var slot = 0; slot < Slots; slot++)
        {
            ClearSlot(cell, slot);
        }

        _streamer?.CancelCell(cell);
    }

    private void SetArrays(ShaderMaterial material)
    {
        material.SetShaderParameter(ShaderParams.SlotsLarge, _streamer?.Large is { } large ? large : default(Variant));
        material.SetShaderParameter(ShaderParams.SlotsSmall, _streamer?.Small is { } small ? small : default(Variant));
    }

    /// <summary>One texel per cell and slot: (fallback: 1 generated, 0 authored; media aspect or 0; fade; layer).</summary>
    private void WriteState(int cell, int slot)
    {
        var i = cell * Slots + slot;
        var aspect = 0f;
        var layer = 0f;
        if (_wanted[i])
        {
            aspect = _media[i].Aspect > 0 ? _media[i].Aspect : _templates[_cellTemplate[cell]].SlotAspect(slot);
            var channel = _streamer!.Layout.ChannelOf(slot);
            layer = _streamer.Layout.LayerOf(cell, channel);
        }

        _stateImage.SetPixel(slot, cell, new Color(_fallback[i], aspect, _textured[i] ? _fade[i] : 0, layer));
        _stateDirty = true;
    }

    private void WriteCustom(int cell)
    {
        var template = _cellTemplate[cell];
        if (template < 0)
        {
            return;
        }

        // See item.gdshader: the cell, the plain colour packed into one channel, and the idle phase (-1: focused).
        var phase = cell == _focusCell ? -1 : _cellPhase[cell];
        var plain = _cellPlain[cell];
        var packed = (Math.Clamp(plain.R8, 0, 255) << 16) | (Math.Clamp(plain.G8, 0, 255) << 8) | Math.Clamp(plain.B8, 0, 255);
        _multiMeshes[template].SetInstanceCustomData(cell, new Color(cell, packed, phase, 0));
    }

    private int CellOf(int item)
    {
        if (item < 0 || _columns == 0 || _boundRow.Length == 0)
        {
            return -1;
        }

        var row = item / _columns;
        var poolRow = row % _poolRows;
        return _boundRow[poolRow] == row ? poolRow * _columns + item % _columns : -1;
    }

    /// <summary>A per-item model is scaled down to the cell; theme templates set the cell, so they're drawn as they are.</summary>
    private float FitOf(ItemTemplate template, bool perItem) => perItem
        ? Math.Min(1, Math.Min(_cellWidth / Math.Max(template.Size.X, 0.01f), _itemHeight / Math.Max(template.Size.Y, 0.01f)))
        : 1;

    private Transform3D BaseTransform(int template, Vector3 origin)
    {
        var fit = _fit[template];
        return new Transform3D(Basis.Identity.Scaled(new Vector3(fit, fit, fit)), origin);
    }

    // ---- Motion ---------------------------------------------------------------------------------

    /// <summary>A critically damped spring towards the target row.</summary>
    private void SmoothScroll(float dt)
    {
        if (_scroll == _targetScroll && _scrollVelocity == 0)
        {
            return;
        }

        var omega = 2.0f / ScrollSmoothTime;
        var x = omega * dt;
        var decay = 1.0f / (1.0f + x + 0.48f * x * x + 0.235f * x * x * x);
        var change = _scroll - _targetScroll;
        var temp = (_scrollVelocity + omega * change) * dt;
        _scrollVelocity = (_scrollVelocity - omega * temp) * decay;
        _scroll = _targetScroll + (change + temp) * decay;
        if (MathF.Abs(_scroll - _targetScroll) < 0.0005f && MathF.Abs(_scrollVelocity) < 0.001f)
        {
            _scroll = _targetScroll;
            _scrollVelocity = 0;
        }

        _rootDirty = true;
    }

    private void UpdateRoot()
    {
        if (!_rootDirty)
        {
            return;
        }

        _rootDirty = false;
        var scale = _scale * _zoom;
        var origin = _offset + new Vector3(0, _focusLine + _scroll * _pitchY * scale, 0);
        _root.Transform = new Transform3D(Basis.Identity.Scaled(new Vector3(scale, scale, scale)), origin);
    }

    private void UpdateFocus(float dt)
    {
        var cell = CellOf(_focus);
        if (cell != _focusCell)
        {
            if (_focusCell >= 0)
            {
                if (_previousCell >= 0)
                {
                    SetCellTransform(_previousCell, _cellBase[_previousCell]);
                }

                _previousCell = _focusCell;
                _previousBlend = _focusBlend;
            }

            _focusCell = cell;
            _focusBlend = 0;
            _focusTime = 0;
            if (_previousCell >= 0)
            {
                WriteCustom(_previousCell);
            }

            if (_focusCell >= 0)
            {
                WriteCustom(_focusCell);
            }
        }

        _focusTime += dt;
        if (_focusCell >= 0)
        {
            _focusBlend = Math.Min(1, _focusBlend + dt * FocusBlendPerSecond);
            var launch = 0f;
            if (_launchTime >= 0)
            {
                _launchTime += dt;
                launch = Math.Min(1, _launchTime / 0.7f);
            }

            SetCellTransform(_focusCell, FocusTransform(_focusCell, _focusBlend, _focusTime, launch));
        }

        if (_previousCell >= 0)
        {
            _previousBlend = Math.Max(0, _previousBlend - dt * FocusBlendPerSecond);
            SetCellTransform(_previousCell, FocusTransform(_previousCell, _previousBlend, 0, 0));
            if (_previousBlend <= 0)
            {
                _previousCell = -1;
            }
        }
    }

    /// <summary>
    /// The focused item lifts towards the camera, grows a little and sways to show its spine; launching spins it up
    /// and flies it forward.
    /// </summary>
    private Transform3D FocusTransform(int cell, float blend, float time, float launch)
    {
        var eased = blend * blend * (3 - 2 * blend);
        var scale = 1 + (FocusScale - 1) * eased;
        var angle = (0.3f + 0.3f * MathF.Sin(time * 1.1f)) * eased;
        var lift = FocusLift * eased;
        if (launch > 0)
        {
            var e = launch * launch;
            angle += e * Mathf.Tau * 1.5f;
            lift += e * 2.2f;
            scale += e * 0.3f;
        }

        var fit = _fit[_cellTemplate[cell]];
        var basis = new Basis(Vector3.Up, angle).Scaled(new Vector3(scale * fit, scale * fit, scale * fit));
        // Coming towards the camera, an item would drift outwards in perspective (off screen at the edge columns), so
        // it's pulled in to stay where it was on screen; launching, it flies towards the middle.
        var toCamera = Math.Clamp(1 - lift * _scale * _zoom / _cameraDistance, 0.2f, 1);
        var baseOrigin = _cellBase[cell].Origin;
        var origin = new Vector3(baseOrigin.X * toCamera, baseOrigin.Y + _itemHeight / 2 * (1 - scale), baseOrigin.Z + lift);
        return new Transform3D(basis, origin);
    }

    private void SetCellTransform(int cell, Transform3D transform)
    {
        var template = _cellTemplate[cell];
        if (template >= 0)
        {
            _multiMeshes[template].SetInstanceTransform(cell, transform);
        }
    }

    private void AnimateFades(float dt)
    {
        if (_fadingSlots <= 0)
        {
            _fadingSlots = 0;
            return;
        }

        var step = dt / FadeSeconds;
        for (var i = 0; i < _textured.Length; i++)
        {
            if (_textured[i] && _fade[i] < 1)
            {
                _fade[i] = Math.Min(1, _fade[i] + step);
                if (_fade[i] >= 1)
                {
                    _fadingSlots--;
                }

                WriteState(i / Slots, i % Slots);
            }
        }
    }

    private void MeasureTexturing()
    {
        // The rows whose centre is on screen.
        var rowWorld = _pitchY * _scale * _zoom;
        var first = Math.Max(0, (int)MathF.Ceiling(_scroll - (_viewHeight / 2 - _focusLine) / rowWorld));
        var last = Math.Min(_rows - 1, (int)MathF.Floor(_scroll + (_viewHeight / 2 + _focusLine) / rowWorld));
        var wanting = 0;
        var textured = 0;
        for (var row = first; row <= last; row++)
        {
            var poolRow = row % _poolRows;
            if (_boundRow[poolRow] != row)
            {
                continue;
            }

            for (var column = 0; column < _columns; column++)
            {
                var cell = poolRow * _columns + column;
                if (_cellItem[cell] < 0)
                {
                    continue;
                }

                for (var i = cell * Slots; i < (cell + 1) * Slots; i++)
                {
                    if (_wanted[i])
                    {
                        wanting++;
                        if (_textured[i])
                        {
                            textured++;
                        }
                    }
                }
            }
        }

        AnyVisibleArt = wanting > 0;
        VisibleTexturedFraction = wanting == 0 ? 1 : (float)textured / wanting;
        if (!VisibleTextured && textured == wanting && _source is not null)
        {
            VisibleTextured = true;
        }
    }

    /// <summary>
    /// What media an item has, for <see cref="SlotChain.Resolve"/>: a struct, so resolving allocates nothing. With no
    /// layers for the slot, nothing counts, so the chain ends at its fallback.
    /// </summary>
    private readonly struct SourceMedia(IGridSource source, int item, bool canShow) : IMediaAvailability
    {
        public bool Has(int slot) => canShow && source.TryGetMedia(item, slot, out _);
    }
}
