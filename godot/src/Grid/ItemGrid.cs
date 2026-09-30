using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Models;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.Core.Library;
using Launcher.Core.Models;
using Launcher.Core.Theming;

namespace Launcher.App.Grid;

/// <summary>What a grid cell shows. Filled by an <see cref="IGridSource"/>; no strings are built for it.</summary>
public struct CellInfo
{
    public string Title;

    /// <summary>Index into the grid's templates.</summary>
    public int Template;

    /// <summary>
    /// The item's own model (a per-game model, A7 level 1), once it has loaded and been given to
    /// <see cref="ItemGrid.PrepareModel"/>; null to show <see cref="Template"/>. It's drawn on its own node.
    /// </summary>
    public ItemTemplate? Model;

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
/// Items that can't share a MultiMesh are drawn on their own nodes beside it (M6 part 2): a game's own model on the
/// cell's pooled <see cref="MeshInstance3D"/> (created with the grid, so binding one allocates nothing), and a model
/// with clips on a copy of its node tree, which plays idle while unfocused, focused while focused and launch when the
/// game starts (A7). A model with only focused or launch clips stays batched, and the focused cell swaps to its node
/// tree while it plays them, blending back to the rest pose before it swaps back. The shader reads such a node's
/// per-cell data from an instance uniform instead of INSTANCE_CUSTOM, so it's the same material and no new variant.
/// </para>
/// <para>
/// Each slot of a cell's model walks its fallback chain (A7, M6) against the item's media: the first media kind it
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
    private const float ClipBlendSeconds = 0.25f;
    private const float LaunchFallbackSeconds = 0.7f;
    private const int Slots = MediaSlots.Count;

    private static readonly Transform3D Hidden = new(new Basis(Vector3.Zero, Vector3.Zero, Vector3.Zero), Vector3.Zero);
    private static readonly Shader ItemShader = GD.Load<Shader>("res://shaders/item.gdshader");
    private static readonly StringName[] ClipNames = ["idle", "focused", "launch"];
    private static readonly StringName RestClip = ModelConverter.RestClip;

    private readonly TextureStreamer? _streamer;
    private readonly int _maxCells;
    private readonly bool _systemCards;
    private readonly List<ItemTemplate> _templates = [];
    private readonly List<MultiMesh?> _multiMeshes = [];
    private readonly List<MultiMeshInstance3D?> _instances = [];
    private readonly List<ShaderMaterial> _materials = [];
    private readonly List<ItemTemplate> _materialOwners = [];
    private readonly List<int> _templateMaterial = [];
    private readonly List<float> _fit = [];
    private readonly Dictionary<ItemTemplate, ShaderMaterial> _modelMaterials = [];
    private readonly Dictionary<ItemTemplate, Stack<SceneInstance>> _scenePools = [];
    private readonly TitleAtlas _atlas;
    private readonly Node3D _root = new() { Name = "Items" };
    private readonly MeshInstance3D _warmNode = new() { Name = "WarmUp", Visible = false, CastShadow = GeometryInstance3D.ShadowCastingSetting.Off };
    private readonly Image _stateImage;
    private readonly ImageTexture _stateTexture;
    private bool _stateDirty;

    // Per pool cell.
    private readonly int[] _cellItem;
    private readonly int[] _cellTemplate;
    private readonly ItemTemplate?[] _cellModel;
    private readonly float[] _cellFit;
    private readonly float[] _cellPhase;
    private readonly Color[] _cellPlain;
    private readonly Transform3D[] _cellBase;
    private readonly MeshInstance3D[] _cellMesh;
    private readonly SceneInstance?[] _cellScene;
    private readonly Node3D?[] _cellNode;

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

    /// <summary>A copy of a model's node tree for one cell: the geometry to give the cell's data, and its player.</summary>
    private sealed class SceneInstance(ItemTemplate template, Node3D root, GeometryInstance3D[] geometry, AnimationPlayer? player)
    {
        public ItemTemplate Template { get; } = template;

        public Node3D Root { get; } = root;

        public GeometryInstance3D[] Geometry { get; } = geometry;

        public AnimationPlayer? Player { get; } = player;
    }

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
        _cellModel = new ItemTemplate?[maxCells];
        _cellFit = new float[maxCells];
        _cellPhase = new float[maxCells];
        _cellPlain = new Color[maxCells];
        _cellBase = new Transform3D[maxCells];
        _cellMesh = new MeshInstance3D[maxCells];
        _cellScene = new SceneInstance?[maxCells];
        _cellNode = new Node3D?[maxCells];
        _wanted = new bool[maxCells * Slots];
        _textured = new bool[maxCells * Slots];
        _fade = new float[maxCells * Slots];
        _fallback = new byte[maxCells * Slots];
        _next = new int[maxCells * Slots];
        _media = new MediaRef[maxCells * Slots];
        Array.Fill(_cellItem, -1);
        Array.Fill(_cellTemplate, -1);

        // A node per cell for the items drawn on their own (per-game models), made now so binding one allocates nothing.
        for (var cell = 0; cell < maxCells; cell++)
        {
            _cellMesh[cell] = new MeshInstance3D { Name = $"Cell{cell}", Visible = false, CastShadow = GeometryInstance3D.ShadowCastingSetting.Off };
            _root.AddChild(_cellMesh[cell]);
        }

        _root.AddChild(_warmNode);

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

    /// <summary>Cells drawn on their own nodes this frame (per-game models and clips), for the bench and logs.</summary>
    public int NodeCells
    {
        get
        {
            var count = 0;
            foreach (var node in _cellNode)
            {
                if (node is not null)
                {
                    count++;
                }
            }

            return count;
        }
    }

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

    /// <summary>
    /// How long the focused item's launch plays before the emulator starts: its launch clip (at most 2 s, A7), else
    /// the procedural fallback's 0.7 s.
    /// </summary>
    public float LaunchSeconds => CellOf(_focus) is var cell and >= 0 && _cellModel[cell] is { } model && model.HasClip(ModelClip.Launch)
        ? model.LaunchSeconds
        : LaunchFallbackSeconds;

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
    /// Per-game models' materials go too: prepare them again (<see cref="PrepareModel"/>).
    /// </summary>
    public void SetTemplates(IReadOnlyList<ItemTemplate> templates)
    {
        UnbindAll();
        foreach (var instance in _instances)
        {
            instance?.QueueFree();
        }

        foreach (var pool in _scenePools.Values)
        {
            foreach (var scene in pool)
            {
                scene.Root.QueueFree();
            }
        }

        _templates.Clear();
        _multiMeshes.Clear();
        _instances.Clear();
        _materials.Clear();
        _materialOwners.Clear();
        _templateMaterial.Clear();
        _fit.Clear();
        _modelMaterials.Clear();
        _scenePools.Clear();
        foreach (var template in templates)
        {
            AddTemplate(template);
        }
    }

    /// <summary>
    /// Main thread: adds a theme template. One with an idle clip plays it in every cell, so it gets no MultiMesh: its
    /// cells are drawn as nodes.
    /// </summary>
    public int AddTemplate(ItemTemplate template)
    {
        for (var t = 0; t < _templates.Count; t++)
        {
            if (_templates[t] == template)
            {
                return t;
            }
        }

        var material = MaterialFor(template);
        _templateMaterial.Add(_materials.IndexOf(material));
        MultiMesh? multiMesh = null;
        MultiMeshInstance3D? instance = null;
        if (!template.AlwaysNodes)
        {
            multiMesh = new MultiMesh
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

            instance = new MultiMeshInstance3D
            {
                Name = template.Mesh.ResourceName,
                Multimesh = multiMesh,
                MaterialOverride = material,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                Visible = false,
            };
            _root.AddChild(instance);
        }

        _templates.Add(template);
        _multiMeshes.Add(multiMesh);
        _instances.Add(instance);
        _fit.Add(1);

        // A batched template with focused or launch clips needs its node tree for the focused cell and the one it
        // left, which are made now, so moving the focus while scrolling allocates nothing.
        if (template.FocusNodes && !template.AlwaysNodes)
        {
            var pool = _scenePools[template] = new Stack<SceneInstance>();
            pool.Push(Instantiate(template));
            pool.Push(Instantiate(template));
        }

        return _templates.Count - 1;
    }

    /// <summary>
    /// Main thread, when a per-game model has loaded (not while scrolling): makes its material, so binding it
    /// allocates nothing. Its material is shared with any model or template that has the same authored textures.
    /// </summary>
    public void PrepareModel(ItemTemplate model)
    {
        if (!_modelMaterials.ContainsKey(model))
        {
            _modelMaterials[model] = MaterialFor(model);
        }
    }

    /// <summary>
    /// Main thread: forgets per-game models' materials and node copies (a new list is about to be bound; prepare its
    /// models again). Nothing bound may use them: call it before <see cref="Bind"/>.
    /// </summary>
    public void ReleaseModels()
    {
        UnbindAll();
        _modelMaterials.Clear();
        foreach (var (template, pool) in _scenePools)
        {
            if (template.PerGame)
            {
                foreach (var scene in pool)
                {
                    scene.Root.QueueFree();
                }

                pool.Clear();
            }
        }

        // Per-game models' own materials come after every template's (templates are only added by SetTemplates).
        while (_materials.Count > 0 && !_templateMaterial.Contains(_materials.Count - 1))
        {
            _materials.RemoveAt(_materials.Count - 1);
            _materialOwners.RemoveAt(_materialOwners.Count - 1);
        }
    }

    /// <summary>
    /// A material for the model: shared with any model whose authored textures and tint are the same (every built-in
    /// box), since only those differ between them. Binding the texture arrays to one material instead of five kept the
    /// working set as it was in M5.
    /// </summary>
    private ShaderMaterial MaterialFor(ItemTemplate template)
    {
        for (var m = 0; m < _materials.Count; m++)
        {
            var owner = _materialOwners[m];
            if (owner.Tint == template.Tint && SameTextures(owner, template))
            {
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
            if (_instances[t] is { } instance)
            {
                instance.Visible = used;
            }

            if (used)
            {
                width = Math.Max(width, _templates[t].Size.X);
                height = Math.Max(height, _templates[t].Size.Y);
            }
        }

        _cellWidth = width;
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
        _focusCell = _previousCell = -1;
    }

    /// <summary>
    /// Main thread: the item's media (or its model) changed, so its bound cell, if any, walks its slot chains again.
    /// Its model stays unless it changed; slots whose media is unchanged keep their layers; a slot whose derivative
    /// was missing tries again.
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
        var model = info.Model ?? _templates[template];
        if (model != _cellModel[cell])
        {
            var origin = _cellBase[cell].Origin;
            ShowModel(cell, template, model);
            _cellBase[cell] = BaseTransform(cell, origin);
            SetCellTransform(cell, _cellBase[cell]);
            WriteCustom(cell);
            if (cell == _focusCell)
            {
                OnFocusEnter(cell);
            }
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

    /// <summary>
    /// The focused item launches: its launch clip plays (A7), or without one it spins up and flies towards the camera
    /// (the procedural fallback). <see cref="LaunchSeconds"/> says how long before the emulator starts.
    /// </summary>
    public void PlayLaunch()
    {
        _launchTime = 0;
        if (_focusCell >= 0 && _cellModel[_focusCell] is { } model && model.HasClip(ModelClip.Launch))
        {
            UseScene(_focusCell);
            _cellScene[_focusCell]?.Player?.Play(ClipNames[(int)ModelClip.Launch], ClipBlendSeconds * 0.5f);
        }
    }

    public void StopLaunch()
    {
        _launchTime = -1;
        if (_focusCell >= 0)
        {
            OnFocusEnter(_focusCell);
        }
    }

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
    /// is compiled before it's first needed (A3), the node variant too (a per-game model's, drawn with template 0's
    /// mesh). <see cref="EndWarmUp"/> hides them again.
    /// </summary>
    public void BeginWarmUp()
    {
        Visible = true;
        for (var t = 0; t < _templates.Count; t++)
        {
            _materials[_templateMaterial[t]].SetShaderParameter(ShaderParams.GridFade, 1.0f);
            if (_multiMeshes[t] is { } multiMesh)
            {
                _instances[t]!.Visible = true;
                multiMesh.SetInstanceTransform(0, new Transform3D(Basis.Identity, new Vector3(t * 0.3f, 0, -2)));
            }
        }

        if (_templates.Count > 0)
        {
            _warmNode.Mesh = _templates[0].Mesh;
            _warmNode.MaterialOverride = _materials[_templateMaterial[0]];
            _warmNode.Transform = new Transform3D(Basis.Identity, new Vector3(-0.3f, 0, -2));
            _warmNode.Visible = true;
        }

        _rootDirty = true;
    }

    public void EndWarmUp()
    {
        for (var t = 0; t < _templates.Count; t++)
        {
            if (_multiMeshes[t] is { } multiMesh)
            {
                multiMesh.SetInstanceTransform(0, _cellTemplate[0] == t && _cellNode[0] is null ? _cellBase[0] : Hidden);
                _instances[t]!.Visible = _source?.UsesTemplate(t) ?? false;
            }

            _materials[_templateMaterial[t]].SetShaderParameter(ShaderParams.GridFade, _gridFade);
        }

        _warmNode.Visible = false;
        _warmNode.Mesh = null;
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
        if (item < 0 || !_wanted[i] || _source is null || _cellModel[cell]?.Chain(slot) is not { } chain)
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
            _cellItem[cell] = item;
            _cellPlain[cell] = info.Plain;
            _cellPhase[cell] = item * 2.39996f % Mathf.Tau;
            ShowModel(cell, template, info.Model ?? _templates[template]);

            // A grid of one part-filled row is centred; otherwise rows fill from the left.
            var shown = _rows == 1 ? _count : _columns;
            var x = (column - (shown - 1) / 2.0f) * _pitchX;
            _cellBase[cell] = BaseTransform(cell, new Vector3(x, -row * _pitchY - _itemHeight / 2, 0));
            SetCellTransform(cell, _cellBase[cell]);
            WriteCustom(cell);
            _atlas.SetTitle(cell, info.Title);
            ResolveSlots(cell, item, refresh: false);
        }
    }

    // ---- How a cell is drawn ------------------------------------------------------------------------

    /// <summary>
    /// Puts the cell's model on screen: its template's MultiMesh instance, or a node. A per-game model is fitted to the
    /// cell (scaled down if it's bigger than the theme's templates); a theme's template sets the cell, so it's drawn
    /// as it is.
    /// </summary>
    private void ShowModel(int cell, int template, ItemTemplate model)
    {
        ReleaseNode(cell);
        if (_cellTemplate[cell] >= 0 && _multiMeshes[_cellTemplate[cell]] is { } previous)
        {
            previous.SetInstanceTransform(cell, Hidden);
        }

        _cellModel[cell] = model;
        _cellTemplate[cell] = model.PerGame ? -1 : template;
        _cellFit[cell] = model.PerGame
            ? Math.Min(1, Math.Min(_cellWidth / Math.Max(model.Size.X, 0.01f), _itemHeight / Math.Max(model.Size.Y, 0.01f)))
            : _fit[template];
        if (!model.AlwaysNodes)
        {
            return;
        }

        if (model.Scene is not null)
        {
            UseScene(cell);
            PlayClip(cell, model.HasClip(ModelClip.Idle) ? ClipNames[(int)ModelClip.Idle] : null, 0);
            return;
        }

        var node = _cellMesh[cell];
        node.Mesh = model.Mesh;
        node.MaterialOverride = _modelMaterials.TryGetValue(model, out var material) ? material : MaterialForUnprepared(model);
        node.Visible = true;
        _cellNode[cell] = node;
    }

    /// <summary>A model shown before <see cref="PrepareModel"/> (a template with an idle clip is always prepared).</summary>
    private ShaderMaterial MaterialForUnprepared(ItemTemplate model)
    {
        PrepareModel(model);
        return _modelMaterials[model];
    }

    /// <summary>Draws the cell with a copy of its model's node tree (from the model's pool), hiding its batched instance.</summary>
    private void UseScene(int cell)
    {
        if (_cellScene[cell] is not null || _cellModel[cell] is not { Scene: not null } model)
        {
            return;
        }

        if (_cellTemplate[cell] >= 0 && _multiMeshes[_cellTemplate[cell]] is { } multiMesh)
        {
            multiMesh.SetInstanceTransform(cell, Hidden);
        }

        if (_cellNode[cell] is MeshInstance3D mesh)
        {
            mesh.Visible = false;
            mesh.Mesh = null;
        }

        if (!_scenePools.TryGetValue(model, out var pool))
        {
            _scenePools[model] = pool = new Stack<SceneInstance>();
        }

        if (!pool.TryPop(out var scene))
        {
            scene = Instantiate(model);
        }

        var material = _cellTemplate[cell] >= 0 ? _materials[_templateMaterial[_cellTemplate[cell]]]
            : _modelMaterials.TryGetValue(model, out var prepared) ? prepared : MaterialForUnprepared(model);
        foreach (var geometry in scene.Geometry)
        {
            geometry.MaterialOverride = material;
        }

        scene.Root.Visible = true;
        _cellScene[cell] = scene;
        _cellNode[cell] = scene.Root;
        scene.Root.Transform = _cellBase[cell];
        WriteCustom(cell);
    }

    /// <summary>Allocates: only the first time a model's node tree is needed in a cell (then it's pooled).</summary>
    private SceneInstance Instantiate(ItemTemplate model)
    {
        var root = (Node3D)model.Scene!.Duplicate();
        root.Visible = false;
        var geometry = new List<GeometryInstance3D>();
        AnimationPlayer? player = null;
        Collect(root);
        _root.AddChild(root);
        return new SceneInstance(model, root, [.. geometry], player);

        void Collect(Node node)
        {
            if (node is GeometryInstance3D g)
            {
                geometry.Add(g);
            }

            if (node is AnimationPlayer p)
            {
                player ??= p;
            }

            foreach (var child in node.GetChildren())
            {
                Collect(child);
            }
        }
    }

    /// <summary>Back to the MultiMesh (a batched model's cell whose clip has blended back to its rest pose).</summary>
    private void UseBatched(int cell)
    {
        var template = _cellTemplate[cell];
        if (_cellScene[cell] is null || template < 0 || _multiMeshes[template] is not { } multiMesh)
        {
            return;
        }

        ReleaseNode(cell);
        multiMesh.SetInstanceTransform(cell, _cellBase[cell]);
        WriteCustom(cell);
    }

    private void ReleaseNode(int cell)
    {
        if (_cellScene[cell] is { } scene)
        {
            scene.Player?.Stop();
            scene.Root.Visible = false;
            _scenePools[scene.Template].Push(scene);
            _cellScene[cell] = null;
        }
        else if (_cellNode[cell] is MeshInstance3D mesh)
        {
            mesh.Visible = false;
            mesh.Mesh = null;
        }

        _cellNode[cell] = null;
    }

    private void PlayClip(int cell, StringName? clip, float blend)
    {
        if (_cellScene[cell]?.Player is not { } player)
        {
            return;
        }

        if (clip is null)
        {
            player.Stop();
        }
        else
        {
            player.Play(clip, blend);
        }
    }

    private void OnFocusEnter(int cell)
    {
        if (_cellModel[cell] is not { } model || _launchTime >= 0)
        {
            return;
        }

        if (model.FocusNodes)
        {
            UseScene(cell);
        }

        if (model.HasClip(ModelClip.Focused))
        {
            PlayClip(cell, ClipNames[(int)ModelClip.Focused], ClipBlendSeconds);
        }
    }

    private void OnFocusLeave(int cell)
    {
        if (_cellModel[cell] is not { } model || _cellScene[cell] is null)
        {
            return;
        }

        PlayClip(cell, model.HasClip(ModelClip.Idle) ? ClipNames[(int)ModelClip.Idle] : RestClip, ClipBlendSeconds);
    }

    // ---- Slots ------------------------------------------------------------------------------------

    /// <summary>
    /// Walks each of the cell's model slots down its chain against the item's media. On a refresh, a slot whose
    /// media is the same as before keeps its layer (and its request in flight).
    /// </summary>
    private void ResolveSlots(int cell, int item, bool refresh)
    {
        var model = _cellModel[cell]!;
        for (var slot = 0; slot < Slots; slot++)
        {
            var i = cell * Slots + slot;
            if (model.Chain(slot) is not { } chain)
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
        ReleaseNode(cell);
        if (_cellTemplate[cell] >= 0 && _cellTemplate[cell] < _multiMeshes.Count && _multiMeshes[_cellTemplate[cell]] is { } multiMesh)
        {
            multiMesh.SetInstanceTransform(cell, Hidden);
        }

        _cellTemplate[cell] = -1;
        _cellModel[cell] = null;
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
            aspect = _media[i].Aspect > 0 ? _media[i].Aspect : _cellModel[cell]?.SlotAspect(slot) ?? 1;
            var channel = _streamer!.Layout.ChannelOf(slot);
            layer = _streamer.Layout.LayerOf(cell, channel);
        }

        _stateImage.SetPixel(slot, cell, new Color(_fallback[i], aspect, _textured[i] ? _fade[i] : 0, layer));
        _stateDirty = true;
    }

    /// <summary>
    /// The cell's per-instance data (item.gdshader): the cell, the plain colour packed into one channel, the idle phase
    /// (-1: focused), and 1 when a clip animates it (so the shader doesn't bob it too).
    /// </summary>
    private void WriteCustom(int cell)
    {
        if (_cellModel[cell] is not { } model)
        {
            return;
        }

        var phase = cell == _focusCell ? -1 : _cellPhase[cell];
        var plain = _cellPlain[cell];
        var packed = (Math.Clamp(plain.R8, 0, 255) << 16) | (Math.Clamp(plain.G8, 0, 255) << 8) | Math.Clamp(plain.B8, 0, 255);
        var animated = model.HasClip(ModelClip.Idle) && _cellScene[cell] is not null ? 1 : 0;

        // A node's data goes through an instance uniform as a Vector4: Godot converts a Color given to one from sRGB
        // to linear, which would scramble the cell and the packed colour.
        var node = new Vector4(cell, packed, phase, animated);
        if (_cellScene[cell] is { } scene)
        {
            foreach (var geometry in scene.Geometry)
            {
                geometry.SetInstanceShaderParameter(ShaderParams.NodeCustom, node);
            }
        }
        else if (_cellNode[cell] is MeshInstance3D mesh)
        {
            mesh.SetInstanceShaderParameter(ShaderParams.NodeCustom, node);
        }
        else if (_cellTemplate[cell] >= 0 && _multiMeshes[_cellTemplate[cell]] is { } multiMesh)
        {
            multiMesh.SetInstanceCustomData(cell, new Color(cell, packed, phase, animated));
        }
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

    private Transform3D BaseTransform(int cell, Vector3 origin)
    {
        var fit = _cellFit[cell];
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
                    UseBatched(_previousCell);
                }

                _previousCell = _focusCell;
                _previousBlend = _focusBlend;
                OnFocusLeave(_previousCell);
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
                OnFocusEnter(_focusCell);
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
                launch = Math.Min(1, _launchTime / LaunchFallbackSeconds);
            }

            SetCellTransform(_focusCell, FocusTransform(_focusCell, _focusBlend, _focusTime, launch));
        }

        if (_previousCell >= 0)
        {
            _previousBlend = Math.Max(0, _previousBlend - dt * FocusBlendPerSecond);
            SetCellTransform(_previousCell, FocusTransform(_previousCell, _previousBlend, 0, 0));

            // A batched model's clip has blended back to rest by now (ClipBlendSeconds), so it can rejoin its MultiMesh.
            if (_previousBlend <= 0 && _focusTime >= ClipBlendSeconds)
            {
                UseBatched(_previousCell);
                _previousCell = -1;
            }
        }
    }

    /// <summary>
    /// The focused item lifts towards the camera and grows a little (always), and sways to show its spine unless a
    /// focused clip animates it; launching, it spins up and flies forward unless a launch clip plays instead (A7's
    /// procedural fallbacks).
    /// </summary>
    private Transform3D FocusTransform(int cell, float blend, float time, float launch)
    {
        var model = _cellModel[cell];
        var eased = blend * blend * (3 - 2 * blend);
        var scale = 1 + (FocusScale - 1) * eased;
        var angle = model?.HasClip(ModelClip.Focused) == true ? 0 : (0.3f + 0.3f * MathF.Sin(time * 1.1f)) * eased;
        var lift = FocusLift * eased;
        if (launch > 0 && model?.HasClip(ModelClip.Launch) != true)
        {
            var e = launch * launch;
            angle += e * Mathf.Tau * 1.5f;
            lift += e * 2.2f;
            scale += e * 0.3f;
        }

        var fit = _cellFit[cell];
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
        if (_cellNode[cell] is { } node)
        {
            node.Transform = transform;
        }
        else if (_cellTemplate[cell] >= 0 && _multiMeshes[_cellTemplate[cell]] is { } multiMesh)
        {
            multiMesh.SetInstanceTransform(cell, transform);
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
