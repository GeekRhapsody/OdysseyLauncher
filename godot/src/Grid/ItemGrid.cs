using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Models;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.Core.Library;

namespace Launcher.App.Grid;

/// <summary>What a grid cell shows. Filled by an <see cref="IGridSource"/>; no strings are built for it.</summary>
public struct CellInfo
{
    public string Title;

    /// <summary>Index into the grid's templates.</summary>
    public int Template;

    /// <summary>The colour of a box with no art, or of a system card.</summary>
    public Color Plain;

    public MediaRoot CoverRoot;

    /// <summary>The library's own string (relative to the root), or null for no art.</summary>
    public string? CoverPath;

    /// <summary>The art's width over its height; 0 when unknown.</summary>
    public float CoverAspect;

    /// <summary>The art file's indexed size and time, for its derivative's key; 0 when unknown (the streamer reads them).</summary>
    public long CoverSizeBytes;

    public long CoverMtimeMs;
}

/// <summary>The items a grid shows, in order.</summary>
public interface IGridSource
{
    int Count { get; }

    /// <summary>Main thread, while binding a row: must not allocate.</summary>
    void Describe(int index, out CellInfo cell);

    /// <summary>Whether any item uses the template (so its MultiMesh is drawn at all).</summary>
    bool UsesTemplate(int template);
}

/// <summary>
/// A virtualised 3D grid (A1 Grid): a pool of cells covering the visible rows plus a margin, re-bound as rows scroll
/// into view rather than recreated. Each template is one <see cref="MultiMesh"/> with a fixed instance per cell, and
/// every cell has a fixed layer in the shared cover array and a fixed place in the title atlas. The items never
/// move to scroll: the grid's root does (one transform), so a frame only touches newly bound rows, the focused
/// items and fading covers. One <c>_Process</c> drives everything, and nothing in it allocates.
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

    private static readonly Transform3D Hidden = new(new Basis(Vector3.Zero, Vector3.Zero, Vector3.Zero), Vector3.Zero);

    private readonly IReadOnlyList<ItemMesh> _templates;
    private readonly TextureStreamer? _streamer;
    private readonly int _maxSlots;
    private readonly ShaderMaterial _material;
    private readonly MultiMesh[] _multiMeshes;
    private readonly MultiMeshInstance3D[] _instances;
    private readonly TitleAtlas _atlas;
    private readonly Node3D _root = new() { Name = "Items" };

    // Per pool slot.
    private readonly int[] _slotItem;
    private readonly int[] _slotTemplate;
    private readonly float[] _slotFade;
    private readonly float[] _slotPhase;
    private readonly float[] _slotAspect;
    private readonly bool[] _slotWantsArt;
    private readonly bool[] _slotTextured;
    private readonly Color[] _slotPlain;
    private readonly Transform3D[] _slotBase;
    private int[] _boundRow = [];

    private IGridSource? _source;
    private int _count;
    private int _columns = 1;
    private int _poolRows = 1;
    private int _rows;
    private float _pitchX = 1;
    private float _pitchY = 1;
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
    private int _focusSlot = -1;
    private int _previousSlot = -1;
    private float _focusBlend;
    private float _previousBlend;
    private float _focusTime;
    private float _launchTime = -1;
    private int _fadingSlots;
    private bool _texturesEnabled = true;

    private float _fade;
    private Vector3 _offset;
    private float _zoom = 1;
    private bool _rootDirty = true;

    /// <param name="templates">The models this grid can show, indexed by <see cref="CellInfo.Template"/>.</param>
    /// <param name="streamer">The cover streamer, or null for a grid without art (the systems grid).</param>
    /// <param name="blockSize">The title atlas's block size in pixels.</param>
    public ItemGrid(IReadOnlyList<ItemMesh> templates, TextureStreamer? streamer, Look look, int maxSlots, int blockSize, bool spines, bool tintCase)
    {
        Name = "Grid";
        _templates = templates;
        _streamer = streamer;
        _maxSlots = maxSlots;
        _slotItem = new int[maxSlots];
        _slotTemplate = new int[maxSlots];
        _slotFade = new float[maxSlots];
        _slotPhase = new float[maxSlots];
        _slotAspect = new float[maxSlots];
        _slotWantsArt = new bool[maxSlots];
        _slotTextured = new bool[maxSlots];
        _slotPlain = new Color[maxSlots];
        _slotBase = new Transform3D[maxSlots];
        Array.Fill(_slotItem, -1);
        Array.Fill(_slotTemplate, -1);

        _atlas = new TitleAtlas(maxSlots, blockSize, spines);
        _material = new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/item.gdshader") };
        look.ApplyTo(_material);
        _material.SetShaderParameter(ShaderParams.TintCase, tintCase);
        if (streamer?.Array is { } array)
        {
            _material.SetShaderParameter(ShaderParams.Covers, array);
        }

        _multiMeshes = new MultiMesh[templates.Count];
        _instances = new MultiMeshInstance3D[templates.Count];
        for (var t = 0; t < templates.Count; t++)
        {
            var multiMesh = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                UseCustomData = true,
                Mesh = templates[t].Mesh,
                InstanceCount = maxSlots,
            };
            for (var slot = 0; slot < maxSlots; slot++)
            {
                multiMesh.SetInstanceTransform(slot, Hidden);
                multiMesh.SetInstanceCustomData(slot, new Color(slot, 0, 0, 0));
            }

            _multiMeshes[t] = multiMesh;
            _instances[t] = new MultiMeshInstance3D
            {
                Name = templates[t].Id,
                Multimesh = multiMesh,
                MaterialOverride = _material,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                Visible = false,
            };
            _root.AddChild(_instances[t]);
        }
    }

    public int Count => _count;

    public int Columns => _columns;

    public int FocusIndex => _focus;

    /// <summary>The source currently bound, or null.</summary>
    public IGridSource? Source => _source;

    /// <summary>Rows of items that fit the view's height (sets the items' size on screen).</summary>
    public float RowsVisible
    {
        get => _rowsVisible;
        set => _rowsVisible = value;
    }

    /// <summary>0 = shown, 1 = faded into the background (then not drawn at all).</summary>
    public float Fade
    {
        get => _fade;
        set
        {
            if (_fade == value)
            {
                return;
            }

            _fade = value;
            _material.SetShaderParameter(ShaderParams.GridFade, value);
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

    /// <summary>True once every on-screen cell that has art shows it (the bench's "visible textured").</summary>
    public bool VisibleTextured { get; private set; }

    /// <summary>The share of on-screen cells with art that show it this frame; 1 when none has art.</summary>
    public float VisibleTexturedFraction { get; private set; } = 1;

    /// <summary>Whether any on-screen cell wants art this frame.</summary>
    public bool AnyVisibleArt { get; private set; }

    /// <summary>The title atlas and the item root.</summary>
    public override void _Ready()
    {
        AddChild(_atlas);
        _atlas.ApplyTo(_material);
        AddChild(_root);
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
            if (used)
            {
                width = Math.Max(width, _templates[t].Size.X);
                height = Math.Max(height, _templates[t].Size.Y);
            }
        }

        _pitchX = width * PitchXFactor;
        _pitchY = height * PitchYFactor;
        _itemHeight = height;
        // Items are sized so RowsVisible rows fit the height, unless that leaves fewer than PreferredColumns across
        // (wide templates such as jewel cases): then they're sized to fit those columns, and more rows show.
        var usableWidth = _viewHeight * _viewAspect * 0.9f;
        _scale = Math.Min(_viewHeight / (_rowsVisible * _pitchY), usableWidth / (PreferredColumns * _pitchX));
        var rowsShown = _viewHeight / (_pitchY * _scale);
        var fit = (int)(usableWidth / (_pitchX * _scale));
        _columns = Math.Clamp(fit, MinColumns, MaxColumns);
        _rows = (_count + _columns - 1) / _columns;

        // The pool covers the visible rows plus a margin, or every row when there are fewer; a full pool that
        // doesn't fit the slots gives up columns.
        _poolRows = Math.Max(1, Math.Min(Mathf.CeilToInt(rowsShown) + 3, _rows));
        while (_columns > MinColumns && _columns * _poolRows > _maxSlots)
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
        _focusSlot = _previousSlot = -1;
        _focusBlend = _previousBlend = 0;
        _launchTime = -1;
        VisibleTextured = false;
        _rootDirty = true;
        BindVisibleRows();
    }

    /// <summary>Main thread: hides every item and drops every texture request.</summary>
    public void UnbindAll()
    {
        for (var slot = 0; slot < _maxSlots; slot++)
        {
            if (_slotTemplate[slot] >= 0)
            {
                _multiMeshes[_slotTemplate[slot]].SetInstanceTransform(slot, Hidden);
                _slotTemplate[slot] = -1;
            }

            _slotItem[slot] = -1;
            _streamer?.Cancel(slot);
        }

        Array.Fill(_boundRow, -1);
        _fadingSlots = 0;
        _source = null;
        _count = 0;
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

    public int Rows => _rows;

    /// <summary>The focused item spins up and flies towards the camera (the A7 launch fallback).</summary>
    public void PlayLaunch() => _launchTime = 0;

    public void StopLaunch() => _launchTime = -1;

    /// <summary>Stops streaming and frees nothing; the next <see cref="EnableTextures"/> re-requests what's bound.</summary>
    public void DisableTextures()
    {
        _texturesEnabled = false;
        for (var slot = 0; slot < _maxSlots; slot++)
        {
            _streamer?.Cancel(slot);
            if (_slotTextured[slot])
            {
                _slotTextured[slot] = false;
                _slotFade[slot] = 0;
                WriteCustom(slot);
            }
        }

        _material.SetShaderParameter(ShaderParams.Covers, default(Variant));
    }

    /// <summary>After the cover array is (re)created: points the material at it and re-requests every bound cover.</summary>
    public void EnableTextures()
    {
        _texturesEnabled = true;
        if (_streamer?.Array is not { } array)
        {
            return;
        }

        _material.SetShaderParameter(ShaderParams.Covers, array);
        for (var slot = 0; slot < _maxSlots; slot++)
        {
            RequestCover(slot);
        }
    }

    /// <summary>
    /// Warm-up after interactive: shows one instance of every template, faded into the background, so each pipeline
    /// is compiled before it's first needed (A3). <see cref="EndWarmUp"/> hides them again.
    /// </summary>
    public void BeginWarmUp()
    {
        Visible = true;
        _material.SetShaderParameter(ShaderParams.GridFade, 1.0f);
        for (var t = 0; t < _templates.Count; t++)
        {
            _instances[t].Visible = true;
            _multiMeshes[t].SetInstanceTransform(0, new Transform3D(Basis.Identity, new Vector3(t * 0.3f, 0, -2)));
        }

        _rootDirty = true;
    }

    public void EndWarmUp()
    {
        for (var t = 0; t < _templates.Count; t++)
        {
            _multiMeshes[t].SetInstanceTransform(0, _slotTemplate[0] == t ? _slotBase[0] : Hidden);
            _instances[t].Visible = _source?.UsesTemplate(t) ?? false;
        }

        _material.SetShaderParameter(ShaderParams.GridFade, _fade);
        Visible = _fade < 1;
    }

    /// <summary>The font sizes the title atlas draws at, for the glyph warm-up.</summary>
    public (int Block, int Spine) AtlasFontSizes => _atlas.FontSizes;

    /// <summary>Called by the owner each frame (the grid's one per-frame update).</summary>
    public void Tick(float dt)
    {
        if (_source is null)
        {
            UpdateRoot();
            _atlas.Flush();
            return;
        }

        SmoothScroll(dt);
        UpdateRoot();
        BindVisibleRows();
        UpdateFocus(dt);
        AnimateFades(dt);
        _atlas.Flush();
        MeasureTexturing();
    }

    /// <summary>Main thread, once per frame, after <see cref="Tick"/>: uploads covers within the budget.</summary>
    public void PumpTextures(long budgetBytes, int cap)
    {
        if (_streamer is not null && _texturesEnabled && _source is not null)
        {
            _streamer.SetView(_scroll, _scrollVelocity);
            _streamer.PumpUploads(this, budgetBytes, cap);
        }
    }

    public void OnLayerReady(int slot)
    {
        if (_slotItem[slot] < 0 || !_slotWantsArt[slot])
        {
            return;
        }

        _slotTextured[slot] = true;
        if (_slotFade[slot] < 1)
        {
            _fadingSlots++;
        }
    }

    public void OnLayerMissing(int slot)
    {
        if (_slotItem[slot] < 0)
        {
            return;
        }

        // No derivative yet (baking is M4's): the box shows as it would with no art, title and all.
        _slotWantsArt[slot] = false;
        _slotAspect[slot] = 0;
        WriteCustom(slot);
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
            var slot = poolRow * _columns + column;
            var item = row * _columns + column;
            if (slot == _focusSlot)
            {
                _focusSlot = -1;
            }

            if (slot == _previousSlot)
            {
                _previousSlot = -1;
            }

            if (_slotTextured[slot] && _slotFade[slot] < 1)
            {
                _fadingSlots--;
            }

            _slotTextured[slot] = false;
            _slotFade[slot] = 0;
            if (item >= _count)
            {
                HideSlot(slot);
                continue;
            }

            _source!.Describe(item, out var cell);
            var template = Math.Clamp(cell.Template, 0, _templates.Count - 1);
            if (_slotTemplate[slot] >= 0 && _slotTemplate[slot] != template)
            {
                _multiMeshes[_slotTemplate[slot]].SetInstanceTransform(slot, Hidden);
            }

            _slotItem[slot] = item;
            _slotTemplate[slot] = template;
            _slotPlain[slot] = cell.Plain;
            _slotPhase[slot] = item * 2.39996f % Mathf.Tau;
            _slotWantsArt[slot] = cell.CoverPath is not null;
            _slotAspect[slot] = cell.CoverPath is null ? 0 : cell.CoverAspect > 0 ? cell.CoverAspect : _templates[template].CoverAspect;

            // A grid of one part-filled row is centred; otherwise rows fill from the left.
            var shown = _rows == 1 ? _count : _columns;
            var x = (column - (shown - 1) / 2.0f) * _pitchX;
            _slotBase[slot] = new Transform3D(Basis.Identity, new Vector3(x, -row * _pitchY - _itemHeight / 2, 0));
            var multiMesh = _multiMeshes[template];
            multiMesh.SetInstanceTransform(slot, _slotBase[slot]);
            WriteCustom(slot);
            _atlas.SetTitle(slot, cell.Title);
            if (_slotWantsArt[slot])
            {
                if (_texturesEnabled && _streamer?.Array is not null)
                {
                    _streamer.Request(slot, row, cell.CoverRoot, cell.CoverPath!, cell.CoverSizeBytes, cell.CoverMtimeMs);
                }
            }
            else
            {
                _streamer?.Cancel(slot);
            }
        }
    }

    private void RequestCover(int slot)
    {
        if (_slotItem[slot] < 0 || !_slotWantsArt[slot] || _slotTextured[slot] || _source is null || _streamer is null)
        {
            return;
        }

        _source.Describe(_slotItem[slot], out var cell);
        if (cell.CoverPath is not null)
        {
            _streamer.Request(slot, _slotItem[slot] / _columns, cell.CoverRoot, cell.CoverPath, cell.CoverSizeBytes, cell.CoverMtimeMs);
        }
    }

    private void HideSlot(int slot)
    {
        if (_slotTemplate[slot] >= 0)
        {
            _multiMeshes[_slotTemplate[slot]].SetInstanceTransform(slot, Hidden);
            _slotTemplate[slot] = -1;
        }

        _slotItem[slot] = -1;
        _slotWantsArt[slot] = false;
        _streamer?.Cancel(slot);
    }

    private void WriteCustom(int slot)
    {
        var template = _slotTemplate[slot];
        if (template < 0)
        {
            return;
        }

        // See item.gdshader: the layer and fade share a channel, and the plain colour is packed into one.
        var phase = slot == _focusSlot ? -1 : _slotPhase[slot];
        var plain = _slotPlain[slot];
        var packed = (Math.Clamp(plain.R8, 0, 255) << 16) | (Math.Clamp(plain.G8, 0, 255) << 8) | Math.Clamp(plain.B8, 0, 255);
        _multiMeshes[template].SetInstanceCustomData(slot, new Color(slot + _slotFade[slot] * 0.999f, packed, phase, _slotAspect[slot]));
    }

    private int SlotOf(int item)
    {
        if (item < 0 || _columns == 0)
        {
            return -1;
        }

        var row = item / _columns;
        var poolRow = row % _poolRows;
        return _boundRow.Length > 0 && _boundRow[poolRow] == row ? poolRow * _columns + item % _columns : -1;
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
        var slot = SlotOf(_focus);
        if (slot != _focusSlot)
        {
            if (_focusSlot >= 0)
            {
                if (_previousSlot >= 0)
                {
                    SetSlotTransform(_previousSlot, _slotBase[_previousSlot]);
                }

                _previousSlot = _focusSlot;
                _previousBlend = _focusBlend;
            }

            _focusSlot = slot;
            _focusBlend = 0;
            _focusTime = 0;
            if (_previousSlot >= 0)
            {
                WriteCustom(_previousSlot);
            }

            if (_focusSlot >= 0)
            {
                WriteCustom(_focusSlot);
            }
        }

        _focusTime += dt;
        if (_focusSlot >= 0)
        {
            _focusBlend = Math.Min(1, _focusBlend + dt * FocusBlendPerSecond);
            var launch = 0f;
            if (_launchTime >= 0)
            {
                _launchTime += dt;
                launch = Math.Min(1, _launchTime / 0.7f);
            }

            SetSlotTransform(_focusSlot, FocusTransform(_focusSlot, _focusBlend, _focusTime, launch));
        }

        if (_previousSlot >= 0)
        {
            _previousBlend = Math.Max(0, _previousBlend - dt * FocusBlendPerSecond);
            SetSlotTransform(_previousSlot, FocusTransform(_previousSlot, _previousBlend, 0, 0));
            if (_previousBlend <= 0)
            {
                _previousSlot = -1;
            }
        }
    }

    /// <summary>
    /// The focused item lifts towards the camera, grows a little and sways to show its spine; launching spins it up
    /// and flies it forward.
    /// </summary>
    private Transform3D FocusTransform(int slot, float blend, float time, float launch)
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

        var basis = new Basis(Vector3.Up, angle).Scaled(new Vector3(scale, scale, scale));
        // Coming towards the camera, an item would drift outwards in perspective (off screen at the edge columns), so
        // it's pulled in to stay where it was on screen; launching, it flies towards the middle.
        var toCamera = Math.Clamp(1 - lift * _scale * _zoom / _cameraDistance, 0.2f, 1);
        var baseOrigin = _slotBase[slot].Origin;
        var origin = new Vector3(baseOrigin.X * toCamera, baseOrigin.Y + _itemHeight / 2 * (1 - scale), baseOrigin.Z + lift);
        return new Transform3D(basis, origin);
    }

    private void SetSlotTransform(int slot, Transform3D transform)
    {
        var template = _slotTemplate[slot];
        if (template >= 0)
        {
            _multiMeshes[template].SetInstanceTransform(slot, transform);
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
        for (var slot = 0; slot < _maxSlots; slot++)
        {
            if (_slotTextured[slot] && _slotFade[slot] < 1)
            {
                _slotFade[slot] = Math.Min(1, _slotFade[slot] + step);
                if (_slotFade[slot] >= 1)
                {
                    _fadingSlots--;
                }

                WriteCustom(slot);
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
                var slot = poolRow * _columns + column;
                if (_slotItem[slot] < 0 || !_slotWantsArt[slot])
                {
                    continue;
                }

                wanting++;
                if (_slotTextured[slot])
                {
                    textured++;
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
}
