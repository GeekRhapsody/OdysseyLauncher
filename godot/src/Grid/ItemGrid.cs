using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Models;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.Core.Config;
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
    public const int MaxColumns = DisplaySettings.MaxColumns;
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

    // The right stick turns the focused item this fast at full tilt (radians a second), and tips it towards or away
    // from the camera this far at most, so its top or bottom faces the camera but it never turns over.
    private const float TurnSpeed = 3.0f;
    private const float MaxTurnPitch = 1.45f;

    // Inspected (R3), the focused item stands in the middle of the view this share of its height tall (or this share of
    // its width wide, if that's smaller), and gets there or back in 1 / InspectBlendPerSecond seconds.
    private const float InspectHeight = 0.9f;
    private const float InspectWidth = 0.9f;
    private const float InspectBlendPerSecond = 5.0f;
    private const int Slots = MediaSlots.Count;

    // A grid whose rows are set fits them between the overlay's heading and its details, these shares of the view's
    // height from the top and the bottom.
    private const float RowsBandTop = 0.15f;
    private const float RowsBandBottom = 0.18f;

    // The carousel: rows of its items that would fit the view's height (their size), at least this many items across,
    // the spacing over an item's width, and how much an item a place from the middle shrinks, turns to face the middle
    // and steps back (more places step back further).
    private const float CarouselRows = 2.1f;
    private const float CarouselShown = 5.5f;
    private const float CarouselPitchFactor = 1.3f;
    private const float CarouselShrink = 0.2f;
    private const float CarouselTurn = 0.32f;
    private const float CarouselDepth = 0.3f;

    // One at a time (Single) and beside the list (List): the item's share of the view's height and width at most, and
    // where the list's item stands across the view (from the middle, as a share of its width).
    private const float SingleHeight = 0.52f;
    private const float SingleWidth = 0.42f;
    private const float ListHeight = 0.56f;
    private const float ListWidth = 0.34f;
    private const float ListCentre = 0.22f;

    // A big item (carousel, single, list) comes this far towards the camera when focused, in world units, at most.
    private const float BigFocusLift = 0.45f;

    // The slot-state texture's two columns after the slots: a reshaped box's growth, and its faces' aspects (item.gdshader).
    private const int ShapeColumn = Slots;
    private const int StateColumns = Slots + 2;

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
    private readonly float[] _cellCurve;
    private readonly Transform3D[] _cellBase;
    private readonly MeshInstance3D[] _cellMesh;
    private readonly SceneInstance?[] _cellScene;
    private readonly Node3D?[] _cellNode;
    private readonly bool[] _shaped;
    private readonly bool[] _inspectedCell;

    // Per pool cell and slot: cell × Slots + slot.
    private readonly bool[] _wanted;
    private readonly bool[] _textured;
    private readonly float[] _fade;
    private readonly byte[] _fallback;
    private readonly int[] _next;
    private readonly MediaRef[] _media;
    private int[] _boundRow = [];

    private IGridSource? _source;
    private GridLayout _layout;
    private bool _horizontal;
    private bool _curved;
    private int _count;
    private int _columns = 1;
    private int _poolRows = 1;
    private int _rows;
    private float _pitchX = 1;
    private float _pitchY = 1;

    // The distance between lines (rows, or a carousel's items) along the scroll, and a column's place across the view
    // (the list's), in world units before the grid's scale.
    private float _linePitch = 1;
    private float _crossOffset;
    private Vector3 _rootOrigin;
    private float _focusLift = FocusLift;
    private float _curveScroll = float.NaN;
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

    // The player's turn of the focused item (the right stick) and of the one it left, which eases back as it blends
    // out; and the focused item's sway clock, which stops once the player has turned it, so it holds still.
    private float _turnYaw;
    private float _turnPitch;
    private float _previousYaw;
    private float _previousPitch;
    private float _swayTime;
    private bool _turned;

    // Whether the focused item is inspected (R3), and how far it and the item it left are towards that pose (0 to 1).
    private bool _inspecting;
    private float _inspectBlend;
    private float _previousInspect;
    private int _fadingSlots;
    private bool _texturesEnabled = true;

    // The bound list's widest and tallest reshaped box (A6 shape = "media"), in model units; 0 when it has none.
    private float _envelopeWidth;
    private float _envelopeHeight;

    private float _gridFade;
    private bool _fadeAtEdges = true;
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
        _cellCurve = new float[maxCells];
        _cellBase = new Transform3D[maxCells];
        _cellMesh = new MeshInstance3D[maxCells];
        _cellScene = new SceneInstance?[maxCells];
        _cellNode = new Node3D?[maxCells];
        _shaped = new bool[maxCells];
        _inspectedCell = new bool[maxCells];
        _wanted = new bool[maxCells * Slots];
        _textured = new bool[maxCells * Slots];
        _fade = new float[maxCells * Slots];
        _fallback = new byte[maxCells * Slots];
        _next = new int[maxCells * Slots];
        _media = new MediaRef[maxCells * Slots];
        Array.Fill(_cellItem, -1);
        Array.Fill(_cellTemplate, -1);
        Array.Fill(_cellCurve, 1f);

        // A node per cell for the items drawn on their own (per-game models), made now so binding one allocates nothing.
        for (var cell = 0; cell < maxCells; cell++)
        {
            _cellMesh[cell] = new MeshInstance3D { Name = $"Cell{cell}", Visible = false, CastShadow = GeometryInstance3D.ShadowCastingSetting.Off };
            _root.AddChild(_cellMesh[cell]);
        }

        _root.AddChild(_warmNode);

        // One texel per cell and slot (item.gdshader): the fallback shown without media, the media's aspect (0: none
        // wanted), its fade, and its layer; then two per cell for a reshaped box (WriteShape). Made once; only updated
        // after that.
        _stateImage = Image.CreateEmpty(StateColumns, maxCells, false, Image.Format.Rgbaf);
        _stateTexture = ImageTexture.CreateFromImage(_stateImage);
        _atlas = new TitleAtlas(maxCells, blockSize, spines);
    }

    public int Count => _count;

    public int Columns => _columns;

    public int FocusIndex => _focus;

    /// <summary>The lines the items are laid out in: rows, or a carousel's, single's or list's items.</summary>
    public int Rows => _rows;

    /// <summary>The layout the next <see cref="Bind"/> uses (each bind keeps it: a resize, a theme).</summary>
    public GridLayout Layout
    {
        get => _layout;
        set => _layout = value;
    }

    /// <summary>Where the scroll is, in lines (the list of titles beside a <see cref="GridShape.List"/> follows it).</summary>
    public float ScrollPosition => _scroll;

    /// <summary>How far LB and RB move the focus: four rows of a grid, a carousel's width, or 5 items.</summary>
    public int PageStep => _layout.Shape switch
    {
        GridShape.Grid => _columns * 4,
        GridShape.Carousel => Math.Max(1, (int)(_viewHeight * _viewAspect / (_linePitch * _scale))),
        _ => 5,
    };

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

    /// <summary>
    /// Whether items fade into the background near the top and bottom of the view, under the overlay's text (on by
    /// default). Off for a model shown on its own, which fills its view (a system's details).
    /// </summary>
    public bool FadeAtEdges
    {
        get => _fadeAtEdges;
        set
        {
            _fadeAtEdges = value;
            foreach (var material in _materials)
            {
                ApplyEdgeFade(material);
            }
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

    /// <summary>World units per model unit in the bound layout, before <see cref="Zoom"/>.</summary>
    public float ItemScale => _scale;

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

        // A reshaped box grows past its rest mesh, up to the largest a box can be (BoxShape: sides of 1, half as deep),
        // so its bounds for culling are that.
        if (template.ShapeFromMedia)
        {
            template.Mesh.CustomAabb = new Aabb(new Vector3(-0.55f, -0.05f, -0.3f), new Vector3(1.1f, 1.1f, 0.6f));
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
        ApplyEdgeFade(material);
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

    /// <summary>The shader's default bands (item.gdshader <c>edge_fade</c>), or none.</summary>
    private void ApplyEdgeFade(ShaderMaterial material)
    {
        if (_fadeAtEdges)
        {
            material.SetShaderParameter(ShaderParams.EdgeFade, default(Variant));
        }
        else
        {
            material.SetShaderParameter(ShaderParams.EdgeFade, Vector3.Zero);
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

        FindEnvelope(source);
        var width = 0.1f;
        var height = 0.1f;
        for (var t = 0; t < _templates.Count; t++)
        {
            var used = source.UsesTemplate(t);
            if (_instances[t] is { } instance)
            {
                instance.Visible = used;
            }

            if (used && _templates[t].ShapeFromMedia && _envelopeWidth > 0)
            {
                // Reshaped boxes: the cells fit the list's widest and tallest.
                width = Math.Max(width, _envelopeWidth);
                height = Math.Max(height, _envelopeHeight);
            }
            else if (used)
            {
                width = Math.Max(width, _templates[t].Size.X);
                height = Math.Max(height, _templates[t].Size.Y);
            }
        }

        _cellWidth = width;
        _itemHeight = height;
        _pitchX = width * PitchXFactor;
        _pitchY = height * PitchYFactor;
        _horizontal = _layout.Shape is GridShape.Carousel or GridShape.Single;
        _curved = _layout.Shape == GridShape.Carousel;
        _crossOffset = 0;
        var viewWidth = _viewHeight * _viewAspect;
        float linesShown;
        switch (_layout.Shape)
        {
            case GridShape.Carousel:
                // Sized so CarouselRows of its items would fit the height, unless fewer than CarouselShown fit across.
                _columns = 1;
                _linePitch = width * CarouselPitchFactor;
                _scale = Math.Min(_viewHeight / (CarouselRows * _pitchY), viewWidth / (CarouselShown * _linePitch));
                _focusLine = _viewHeight * 0.02f;
                linesShown = viewWidth / (_linePitch * _scale) + 2;
                break;
            case GridShape.Single:
                // The next item is a screen to the right, so one shows at a time and moving slides it in.
                _columns = 1;
                _scale = Math.Min(_viewHeight * SingleHeight / height, viewWidth * SingleWidth / width);
                _linePitch = viewWidth / _scale;
                _focusLine = 0;
                linesShown = 2;
                break;
            case GridShape.List:
                // A column on the right, an item a screen apart: the titles' list is on the left.
                _columns = 1;
                _scale = Math.Min(_viewHeight * ListHeight / height, viewWidth * ListWidth / width);
                _linePitch = _viewHeight / _scale;
                _crossOffset = viewWidth * ListCentre;
                _focusLine = _viewHeight * 0.02f;
                linesShown = 2;
                break;
            default:
                // The focused row sits a little above the middle; the overlay's title is above it and its details below.
                _linePitch = _pitchY;
                _focusLine = _viewHeight * 0.12f;
                linesShown = SizeGrid(viewWidth);
                break;
        }

        _focusLift = _layout.Shape == GridShape.Grid ? FocusLift : Math.Min(FocusLift, BigFocusLift / _scale);
        _rows = (_count + _columns - 1) / _columns;

        // The pool covers the visible rows plus a margin, or every row when there are fewer. A full pool that doesn't
        // fit the cells gives up spare rows when the columns were chosen (keeping one ahead of the scroll), then columns.
        var spare = 3;
        _poolRows = Math.Max(1, Math.Min(Mathf.CeilToInt(linesShown) + spare, _rows));
        while (_layout.Columns > 0 && spare > 1 && _columns * _poolRows > _maxCells)
        {
            spare--;
            _poolRows = Math.Max(1, Math.Min(Mathf.CeilToInt(linesShown) + spare, _rows));
        }

        var fewestColumns = _layout.Shape == GridShape.Grid && _layout.Columns == 0 && _layout.Rows == 0 ? MinColumns : 1;
        while (_columns > fewestColumns && _columns * _poolRows > _maxCells)
        {
            _columns--;
            _rows = (_count + _columns - 1) / _columns;
            _poolRows = Math.Max(1, Math.Min(Mathf.CeilToInt(linesShown) + spare, _rows));
        }

        _boundRow = new int[_poolRows];
        Array.Fill(_boundRow, -1);

        _focus = _count == 0 ? -1 : Math.Clamp(focus, 0, _count - 1);
        _targetScroll = _scroll = _focus < 0 ? 0 : _focus / _columns;
        _scrollVelocity = 0;
        _focusCell = _previousCell = -1;
        _focusBlend = _previousBlend = 0;
        _launchTime = -1;
        ResetPose();
        VisibleTextured = false;
        _rootDirty = true;
        _curveScroll = _scroll;
        BindVisibleRows();
    }

    /// <summary>
    /// A grid's scale and columns (<see cref="GridLayout.Columns"/> and <see cref="GridLayout.Rows"/>, 0 automatic);
    /// returns the rows that show. Automatic: items are sized so <see cref="RowsVisible"/> rows fit the height, unless
    /// that leaves fewer than <see cref="PreferredColumns"/> across (wide templates such as jewel cases): then they're
    /// sized to fit those columns, and more rows show. Set rows fit between the overlay's heading and its details (the
    /// focused row in the middle one, or the upper of the two middle ones), with as many columns as fit across; set
    /// columns fill the width, unless the set rows leave less room (or, rows automatic, one row wouldn't fit there).
    /// </summary>
    private float SizeGrid(float viewWidth)
    {
        var usableWidth = viewWidth * 0.9f;
        var band = _viewHeight * (1 - RowsBandTop - RowsBandBottom);
        if (_layout.Columns > 0)
        {
            _scale = Math.Min(usableWidth / (_layout.Columns * _pitchX),
                band / (Math.Max(_layout.Rows, 1) * _pitchY));
            _columns = _layout.Columns;
        }
        else if (_layout.Rows > 0)
        {
            _scale = Math.Min(band / (_layout.Rows * _pitchY), usableWidth / _pitchX);
            _columns = Math.Clamp((int)(usableWidth / (_pitchX * _scale)), 1, MaxColumns);
        }
        else
        {
            _scale = Math.Min(_viewHeight / (_rowsVisible * _pitchY), usableWidth / (PreferredColumns * _pitchX));
            _columns = Math.Clamp((int)(usableWidth / (_pitchX * _scale)), MinColumns, MaxColumns);
        }

        // A size that was set lays the rows out in the band: the focused one in the middle of those that fit (the upper
        // of the two middle ones).
        if (_layout.Rows > 0 || _layout.Columns > 0)
        {
            var row = _pitchY * _scale;
            var fitting = _layout.Rows > 0 ? _layout.Rows : Math.Max(1, (int)(band / row + 0.001f));
            _focusLine = _viewHeight / 2 - _viewHeight * RowsBandTop - ((fitting - 1) / 2 + 0.5f) * row;
        }

        return _viewHeight / (_pitchY * _scale);
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
        ResetPose();
    }

    /// <summary>
    /// Main thread: the item's media, model or title changed, so its bound cell, if any, walks its slot chains again.
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
        _atlas.SetTitle(cell, info.Title);
        var template = Math.Clamp(info.Template, 0, _templates.Count - 1);
        var model = info.Model ?? _templates[template];
        if (model != _cellModel[cell])
        {
            ShowModel(cell, template, model);
            _cellBase[cell] = RestTransform(cell);
            SetCellTransform(cell, _cellBase[cell]);
            WriteCustom(cell);
            if (cell == _focusCell)
            {
                OnFocusEnter(cell);
            }
        }

        ResolveSlots(cell, item, refresh: true);
    }

    /// <summary>
    /// Main thread: moves the focus one place left or right (<paramref name="dx"/>) or up or down (<paramref name="dy"/>)
    /// as the layout lays the items out: a grid's rows and columns; a carousel's or single's items left and right; a
    /// list's up and down.
    /// </summary>
    public bool Move(int dx, int dy)
    {
        if (_layout.Shape == GridShape.Grid)
        {
            return dx != 0 ? MoveFocus(dx) : dy != 0 && MoveFocus(dy * _columns);
        }

        var step = _horizontal ? dx : dy;
        var target = _focus + step;
        if (step == 0 || _count == 0 || target < 0 || target >= _count)
        {
            return false;
        }

        SetFocus(target);
        return true;
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
    /// Main thread, each frame the right stick is held (<paramref name="stick"/>: each axis -1 to 1, right and down
    /// positive): turns the focused item about its middle, round its vertical with the stick's x, and towards or away
    /// from the camera with its y, slowly near the middle of the stick's travel and fast at its edge. The item stays
    /// turned until the focus moves (it then eases back as it blends out) or the grid is bound again; once turned, it
    /// stops swaying. Nothing while it launches.
    /// </summary>
    public void Turn(Vector2 stick, float dt)
    {
        // A move this frame hasn't reached the focused cell yet (UpdateFocus): the turn would go to the item it leaves.
        if (_focusCell < 0 || _launchTime >= 0 || CellOf(_focus) != _focusCell)
        {
            return;
        }

        var speed = TurnSpeed * dt;
        _turnYaw = Mathf.Wrap(_turnYaw + stick.X * MathF.Abs(stick.X) * speed, -MathF.PI, MathF.PI);

        // Up (negative) brings the front up towards the top of the screen: a negative turn round x.
        _turnPitch = Math.Clamp(_turnPitch + stick.Y * MathF.Abs(stick.Y) * speed, -MaxTurnPitch, MaxTurnPitch);
        _turned = true;
    }

    /// <summary>
    /// Whether the focused item is inspected (<see cref="ToggleInspect"/>), or on its way there; false as soon as the
    /// focus moves (the next tick lets it go).
    /// </summary>
    public bool Inspecting => _inspecting && CellOf(_focus) == _focusCell;

    /// <summary>
    /// Main thread: inspects the focused item (R3), or ends it. Inspected, it moves to the middle of the view and grows
    /// until it's nearly as tall as the view (<see cref="InspectHeight"/>), in front of the other items, facing the
    /// camera; it still turns, plays its clips and launches there. Moving the focus, or binding the grid again, ends it:
    /// the item eases back as it blends out. Nothing while it launches.
    /// </summary>
    public void ToggleInspect()
    {
        if (_focusCell < 0 || _launchTime >= 0 || CellOf(_focus) != _focusCell)
        {
            return;
        }

        _inspecting = !_inspecting;
    }

    /// <summary>Main thread: ends the inspection, the item easing back. False if the item wasn't inspected.</summary>
    public bool EndInspect()
    {
        if (!Inspecting)
        {
            return false;
        }

        _inspecting = false;
        return true;
    }

    /// <summary>The focused item goes back to how it rests: square, not turned, not inspected.</summary>
    private void ResetPose()
    {
        _turnYaw = _turnPitch = _previousYaw = _previousPitch = _swayTime = 0;
        _turned = false;
        _inspecting = false;
        _inspectBlend = _previousInspect = 0;
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
            UpdateCurve();
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

    public void OnArraysChanged()
    {
        foreach (var material in _materials)
        {
            SetArrays(material);
        }
    }

    public void OnLayerEvicted(int cell, int channel)
    {
        var slot = _streamer!.Layout.Slots[channel];
        var i = cell * Slots + slot;
        if (!_textured[i])
        {
            return;
        }

        // The media is still wanted: the streamer brings it back when the cell nears the view again.
        if (_fade[i] < 1)
        {
            _fadingSlots--;
        }

        _textured[i] = false;
        _fade[i] = 0;
        WriteState(cell, slot);
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
        var rowWorld = _linePitch * _scale * _zoom;
        float above, below;
        if (_horizontal)
        {
            // The carousel's curve draws its far items in, so one more shows each side.
            above = below = _viewHeight * _viewAspect / 2 / rowWorld + (_curved ? 1.5f : 0.5f);
        }
        else
        {
            above = (_viewHeight / 2 - _focusLine) / rowWorld + 0.5f;
            below = (_viewHeight / 2 + _focusLine) / rowWorld + 0.5f;
        }

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

            _cellBase[cell] = RestTransform(cell);
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

        WriteShape(cell);
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
        // Bit 0: the fallback is generated. Bit 1: the art is drawn whole over the fallback, fitted inside the face (the
        // template's fit, or a logo). Bit 2: it's a logo, so it has a margin, and along a spine it's turned.
        var logo = resolution.MediaSlot == MediaSlots.Logo;
        _fallback[i] = (byte)((resolution.Fallback == SlotSourceKind.Generated ? 1 : 0)
            | (logo || _cellModel[cell]?.ShowsWhole(slot) == true ? 2 : 0)
            | (logo ? 4 : 0));
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
        _inspectedCell[cell] = false;
        WriteShape(cell);
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

    /// <summary>
    /// One texel per cell and slot: (fallback: 1 generated, 0 authored, plus 2 for art drawn whole and 4 for a logo;
    /// media aspect or 0; fade; layer).
    /// </summary>
    private void WriteState(int cell, int slot)
    {
        var i = cell * Slots + slot;
        var aspect = 0f;
        var layer = 0f;
        if (_wanted[i])
        {
            aspect = _media[i].Aspect > 0 ? _media[i].Aspect : _cellModel[cell]?.SlotAspect(slot) ?? 1;
            // POC: layers are handed out as media streams in, so it's whichever the streamer gave the cell's channel.
            layer = _textured[i] ? _streamer!.ShownLayer(cell, _streamer.Layout.ChannelOf(slot)) : 0;
        }

        _stateImage.SetPixel(slot, cell, new Color(_fallback[i], aspect, _textured[i] ? _fade[i] : 0, layer));
        _stateDirty = true;
    }

    /// <summary>
    /// Main thread, binding a list: the widest and tallest of its reshaped boxes (A6 shape = "media"), each with the
    /// larger of its width and height 1, so the cells fit them. Lists without such a template skip the walk.
    /// </summary>
    private void FindEnvelope(IGridSource source)
    {
        _envelopeWidth = 0;
        _envelopeHeight = 0;
        var any = false;
        for (var t = 0; t < _templates.Count; t++)
        {
            any |= _templates[t].ShapeFromMedia && source.UsesTemplate(t);
        }

        if (!any)
        {
            return;
        }

        for (var item = 0; item < source.Count; item++)
        {
            source.Describe(item, out var info);
            var template = _templates[Math.Clamp(info.Template, 0, _templates.Count - 1)];
            if (info.Model is not null || !template.ShapeFromMedia)
            {
                continue;
            }

            var cover = source.TryGetMedia(item, MediaSlots.Cover, out var media) ? media.Aspect : 0;
            var (width, height) = BoxShape.Unit(RestOf(template), cover);
            _envelopeWidth = Math.Max(_envelopeWidth, width);
            _envelopeHeight = Math.Max(_envelopeHeight, height);
        }
    }

    private static BoxSize RestOf(ItemTemplate template) => new(template.Size.X, template.Size.Y, template.Size.Z);

    /// <summary>
    /// A reshaped box's two texels (item.gdshader), from its game's cover and spine (<see cref="BoxShape"/>): how much
    /// each half of the rest mesh moves out (half the width's growth, the height's, half the depth's) and the height
    /// above which a vertex is in the top half; then the faces' new aspects (front and back, spine: on the sides as deep
    /// over high as the box, or for a template whose spine face is wider than high, on the top and bottom, as wide over
    /// deep). Zeros for every other cell, which the shader leaves as it is.
    /// </summary>
    private void WriteShape(int cell)
    {
        var item = _cellItem[cell];
        if (_cellModel[cell] is not { ShapeFromMedia: true } model || item < 0 || _source is null)
        {
            if (_shaped[cell])
            {
                _stateImage.SetPixel(ShapeColumn, cell, default);
                _stateImage.SetPixel(ShapeColumn + 1, cell, default);
                _shaped[cell] = false;
                _stateDirty = true;
            }

            return;
        }

        var rest = RestOf(model);
        var size = ShapeOf(item, rest);
        _stateImage.SetPixel(ShapeColumn, cell, new Color(
            (size.Width - rest.Width) / 2, size.Height - rest.Height, (size.Depth - rest.Depth) / 2, rest.Height / 2));
        var spineFace = model.SlotAspect(MediaSlots.Spine) > 1 ? size.Width / size.Depth : size.Depth / size.Height;
        _stateImage.SetPixel(ShapeColumn + 1, cell, new Color(size.Width / size.Height, spineFace, 0, 0));
        _shaped[cell] = true;
        _stateDirty = true;
    }

    /// <summary>A reshaped box's size for its item's cover and spine (<see cref="BoxShape.Fit"/>), in model units.</summary>
    private BoxSize ShapeOf(int item, BoxSize rest)
    {
        var cover = _source!.TryGetMedia(item, MediaSlots.Cover, out var coverMedia) ? coverMedia.Aspect : 0;
        var spine = _source.TryGetMedia(item, MediaSlots.Spine, out var spineMedia) ? spineMedia.Aspect : 0;
        return BoxShape.Fit(rest, cover, spine, _envelopeWidth, _envelopeHeight);
    }

    /// <summary>
    /// The cell's model's size as drawn, in model units before the cell's fit: a reshaped box's (<see cref="WriteShape"/>:
    /// it still stands on its origin, centred), else the model's.
    /// </summary>
    private Vector3 DrawnSize(int cell)
    {
        if (_cellModel[cell] is not { } model)
        {
            return Vector3.One;
        }

        if (!_shaped[cell] || _source is null || _cellItem[cell] < 0)
        {
            return model.Size;
        }

        var size = ShapeOf(_cellItem[cell], RestOf(model));
        return new Vector3(size.Width, size.Height, size.Depth);
    }

    /// <summary>Whether the cell's item is inspected, or still on its way there or back (it then doesn't fade at the edges).</summary>
    private bool IsInspected(int cell) =>
        cell >= 0 && ((cell == _focusCell && (_inspecting || _inspectBlend > 0)) || (cell == _previousCell && _previousInspect > 0));

    /// <summary>Writes the cell's data again if whether it's inspected changed.</summary>
    private void SyncInspected(int cell)
    {
        if (cell >= 0 && _inspectedCell[cell] != IsInspected(cell))
        {
            WriteCustom(cell);
        }
    }

    /// <summary>
    /// The cell's per-instance data (item.gdshader): the cell, the plain colour packed into one channel, the idle phase
    /// (-1: focused), and 1 when a clip animates it (so the shader doesn't bob it too), plus 2 while it's inspected (so
    /// it doesn't fade at the view's top and bottom).
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
        _inspectedCell[cell] = IsInspected(cell);
        var animated = (model.HasClip(ModelClip.Idle) && _cellScene[cell] is not null ? 1 : 0) + (_inspectedCell[cell] ? 2 : 0);

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

    /// <summary>Where the bound cell's item stands, before the carousel's curve: its line along the scroll, and its column.</summary>
    private Vector3 FlatOrigin(int cell)
    {
        var item = _cellItem[cell];
        var row = item / _columns;
        if (_horizontal)
        {
            return new Vector3(row * _linePitch, -_itemHeight / 2, 0);
        }

        // A grid of one part-filled row is centred; otherwise rows fill from the left.
        var shown = _rows == 1 ? _count : _columns;
        var x = (item % _columns - (shown - 1) / 2.0f) * _pitchX;
        return new Vector3(x, -row * _linePitch - _itemHeight / 2, 0);
    }

    /// <summary>
    /// Half the cell's model's height as drawn (fitted), about which it's centred in the cell, shrinks on a carousel's
    /// curve and grows when focused. A reshaped box counts as the cell's height: boxes stand on the row's floor.
    /// </summary>
    private float HalfHeight(int cell) =>
        _cellModel[cell] is { ShapeFromMedia: false } model
            ? Math.Min(model.Size.Y * _cellFit[cell], _itemHeight) / 2
            : _itemHeight / 2;

    /// <summary>The bound cell's resting transform: fitted, centred in the cell's height, and on a carousel's curve.</summary>
    private Transform3D RestTransform(int cell)
    {
        var origin = FlatOrigin(cell);
        if (_curved)
        {
            return CurvedTransform(cell, origin);
        }

        _cellCurve[cell] = 1;
        var fit = _cellFit[cell];
        origin.Y += _itemHeight / 2 - HalfHeight(cell);
        return new Transform3D(Basis.Identity.Scaled(new Vector3(fit, fit, fit)), origin);
    }

    /// <summary>
    /// A carousel's item, by its places from the middle: within a place it shrinks to the size of its neighbours, and
    /// it turns towards the middle and steps back the further away it is (its centre staying on the line).
    /// </summary>
    private Transform3D CurvedTransform(int cell, Vector3 origin)
    {
        var places = origin.X / _linePitch - _scroll;
        var away = MathF.Abs(places);
        var curve = 1 - CarouselShrink * Math.Min(away, 1);
        _cellCurve[cell] = curve;
        var fit = _cellFit[cell] * curve;
        var turn = -Math.Clamp(places, -1.5f, 1.5f) * CarouselTurn;
        var back = -CarouselDepth * Math.Min(away, 3) * _itemHeight;
        return new Transform3D(
            new Basis(Vector3.Up, turn).Scaled(new Vector3(fit, fit, fit)),
            new Vector3(origin.X, origin.Y + _itemHeight / 2 - HalfHeight(cell) * curve, back));
    }

    /// <summary>A carousel's items take their places on its curve again whenever it scrolls (the focused ones follow in <see cref="UpdateFocus"/>).</summary>
    private void UpdateCurve()
    {
        if (!_curved || _scroll == _curveScroll)
        {
            return;
        }

        _curveScroll = _scroll;
        for (var cell = 0; cell < _maxCells; cell++)
        {
            if (_cellItem[cell] < 0)
            {
                continue;
            }

            _cellBase[cell] = CurvedTransform(cell, FlatOrigin(cell));
            if (cell != _focusCell && cell != _previousCell)
            {
                SetCellTransform(cell, _cellBase[cell]);
            }
        }
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
        var origin = _horizontal
            ? _offset + new Vector3(-_scroll * _linePitch * scale, _focusLine, 0)
            : _offset + new Vector3(_crossOffset, _focusLine + _scroll * _linePitch * scale, 0);
        _rootOrigin = origin;
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
                    var replaced = _previousCell;
                    SetCellTransform(replaced, _cellBase[replaced]);
                    UseBatched(replaced);
                    _previousCell = -1;
                    SyncInspected(replaced);
                }

                _previousCell = _focusCell;
                _previousBlend = _focusBlend;
                _previousInspect = _inspectBlend;
                OnFocusLeave(_previousCell);
            }

            // The item left takes the player's turn and inspection with it, to ease back as it blends out; the new one
            // starts square, where it rests.
            _previousYaw = _turnYaw;
            _previousPitch = _turnPitch;
            _turnYaw = _turnPitch = _swayTime = 0;
            _turned = false;
            _inspecting = false;
            _inspectBlend = 0;
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
        if (!_turned)
        {
            _swayTime += dt;
        }

        if (_focusCell >= 0)
        {
            _focusBlend = Math.Min(1, _focusBlend + dt * FocusBlendPerSecond);
            _inspectBlend = Mathf.MoveToward(_inspectBlend, _inspecting ? 1 : 0, dt * InspectBlendPerSecond);
            var launch = 0f;
            if (_launchTime >= 0)
            {
                _launchTime += dt;
                launch = Math.Min(1, _launchTime / LaunchFallbackSeconds);
            }

            SetCellTransform(_focusCell, FocusTransform(_focusCell, _focusBlend, _swayTime, launch, _turnYaw, _turnPitch, _inspectBlend));
            SyncInspected(_focusCell);
        }

        if (_previousCell >= 0)
        {
            _previousBlend = Math.Max(0, _previousBlend - dt * FocusBlendPerSecond);
            _previousInspect = Math.Max(0, _previousInspect - dt * InspectBlendPerSecond);
            SetCellTransform(_previousCell, FocusTransform(_previousCell, _previousBlend, 0, 0, _previousYaw, _previousPitch, _previousInspect));
            SyncInspected(_previousCell);

            // A batched model's clip has blended back to rest by now (ClipBlendSeconds), so it can rejoin its MultiMesh.
            if (_previousBlend <= 0 && _previousInspect <= 0 && _focusTime >= ClipBlendSeconds)
            {
                UseBatched(_previousCell);
                _previousCell = -1;
            }
        }
    }

    /// <summary>
    /// The focused item lifts towards the camera and grows a little (always), and sways to show its spine unless a
    /// focused clip animates it; launching, it spins up and flies forward unless a launch clip plays instead (A7's
    /// procedural fallbacks). The player's turn (<see cref="Turn"/>) is about its middle, and blends with the focus.
    /// Inspected (<paramref name="inspect"/>, 0 to 1), it rests in the middle of the view, large (<see cref="Inspected"/>),
    /// instead of in its cell, without the lift and growth (which that place already has).
    /// </summary>
    private Transform3D FocusTransform(int cell, float blend, float time, float launch, float yaw, float pitch, float inspect)
    {
        var model = _cellModel[cell];
        var rest = _cellBase[cell];
        var eased = blend * blend * (3 - 2 * blend);
        var restOrigin = rest.Origin;
        var grow = 1f;
        var inspected = 0f;
        var size = Vector3.One;
        if (inspect > 0 || yaw != 0 || pitch != 0)
        {
            size = DrawnSize(cell);
        }

        if (inspect > 0)
        {
            inspected = inspect * inspect * (3 - 2 * inspect);
            var (origin, factor) = Inspected(cell, size);
            restOrigin = restOrigin.Lerp(origin, inspected);
            grow = 1 + (factor - 1) * inspected;
        }

        var scale = 1 + (FocusScale - 1) * eased * (1 - inspected);

        // Inspected, it faces the camera (only the player turns it): swaying that close, its near edge would leave the view.
        var angle = model?.HasClip(ModelClip.Focused) == true ? 0 : (0.3f + 0.3f * MathF.Sin(time * 1.1f)) * eased * (1 - inspected);
        var lift = _focusLift * eased * (1 - inspected);
        if (launch > 0 && model?.HasClip(ModelClip.Launch) != true)
        {
            var e = launch * launch;
            angle += e * Mathf.Tau * 1.5f;
            lift += e * 2.2f * _focusLift / FocusLift;
            scale += e * 0.3f;
        }

        var scaled = grow * scale;
        var basis = new Basis(Vector3.Up, angle) * rest.Basis.Scaled(new Vector3(scaled, scaled, scaled));

        // Round its vertical, then towards or away from the camera, about its middle (it stands on its origin), so it
        // turns in place.
        var pivot = Vector3.Zero;
        if (yaw != 0 || pitch != 0)
        {
            var turn = new Basis(Vector3.Right, pitch * eased) * new Basis(Vector3.Up, yaw * eased);
            var middle = basis * new Vector3(0, size.Y / 2, 0);
            pivot = middle - turn * middle;
            basis = turn * basis;
        }

        // Coming towards the camera, an item would drift outwards in perspective (off screen at the edge columns), so
        // it's pulled in to stay where it was on screen; launching, it flies towards the middle.
        var rootScale = _scale * _zoom;
        var toCamera = Math.Clamp(1 - lift * rootScale / _cameraDistance, 0.2f, 1);
        var x = ((_rootOrigin.X + restOrigin.X * rootScale) * toCamera - _rootOrigin.X) / rootScale;
        var y = restOrigin.Y + HalfHeight(cell) * _cellCurve[cell] * grow * (1 - scale);
        return new Transform3D(basis, new Vector3(x, y, restOrigin.Z + lift) + pivot);
    }

    /// <summary>
    /// Where the cell's item rests when inspected, in the grid's root, and how much it grows from its rest size: its
    /// middle on the camera's axis, its front <see cref="InspectHeight"/> of the view tall (or <see cref="InspectWidth"/>
    /// of it wide, if that's smaller), and far enough in front of the other items that turned round its vertical it
    /// doesn't touch them.
    /// </summary>
    /// <param name="size">The model's size as drawn (<see cref="DrawnSize"/>), in model units.</param>
    private (Vector3 Origin, float Grow) Inspected(int cell, Vector3 size)
    {
        var rootScale = _scale * _zoom;
        var restScale = _cellFit[cell] * _cellCurve[cell];

        // How far it reaches from its vertical, turned any way round it, and how far its front is from its middle.
        var reach = MathF.Sqrt(size.X * size.X + size.Z * size.Z) / 2;
        var near = reach + size.Z / 2;

        // The other items come no nearer the camera than this (world z): a focused one's lift and half the cell.
        var front = _rootOrigin.Z + (_focusLift + Math.Max(_cellWidth, _itemHeight) / 2) * rootScale;
        var depth = _cameraDistance - front;
        var tall = InspectHeight * _viewHeight;
        var wide = InspectWidth * _viewHeight * _viewAspect;

        // World units per model unit, k: the view at depth z is viewHeight × (D − z) / D tall; the middle stands reach × k
        // in front of the others, and the front near × k, so the front's height fills `tall` of the view there.
        var k = Math.Min(
            tall * depth / (_cameraDistance * Math.Max(size.Y, 0.01f) + tall * near),
            wide * depth / (_cameraDistance * Math.Max(size.X, 0.01f) + wide * near));
        var middle = (new Vector3(0, 0, front + reach * k) - _rootOrigin) / rootScale;
        var grow = k / (Math.Max(restScale, 0.0001f) * rootScale);
        return (middle - new Vector3(0, size.Y / 2 * restScale * grow, 0), grow);
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
        var rowWorld = _linePitch * _scale * _zoom;
        var before = _horizontal ? _viewHeight * _viewAspect / 2 : _viewHeight / 2 - _focusLine;
        var after = _horizontal ? before : _viewHeight / 2 + _focusLine;
        var first = Math.Max(0, (int)MathF.Ceiling(_scroll - before / rowWorld));
        var last = Math.Min(_rows - 1, (int)MathF.Floor(_scroll + after / rowWorld));
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
