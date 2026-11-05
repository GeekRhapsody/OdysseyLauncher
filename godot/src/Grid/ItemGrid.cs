using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Models;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Models;
using Launcher.Core.Theming;

namespace Launcher.App.Grid;

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
    // Below the whole view, so turning a deep or wide model round takes less of it off screen (2026-10-18).
    private const float InspectHeight = 0.75f;
    private const float InspectWidth = 0.75f;
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

    // A grid with labels (GridLayout.Labels): the room under each row for its items' labels, as a share of the view's
    // height (two lines of Screens/GridLabels.cs's text in the overlay's 800-pixel base), the same on screen whatever the
    // items' size; the gap between an item's foot and its label, over the items' height; and the rows' spacing over the
    // items' height, less than the grid's since the labels' room parts the rows too.
    public const float LabelRoom = 0.064f;
    private const float LabelGap = 0.03f;
    private const float LabelledPitchYFactor = 1.18f;

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

    // Each template's MultiMesh draws only the instances in use (2026-10-08): its cells are packed into the first ones,
    // and VisibleInstanceCount says how many. Every instance is vertex-shaded, hidden or not, so drawing all of them
    // ran each template's whole mesh once per cell: 9 million vertices a frame for the console theme's models. Its
    // node shows only while it has some (2026-10-27, PlaceInstance).
    private readonly List<int[]> _instanceCell = [];
    private readonly List<int> _instancesUsed = [];
    private readonly int[] _cellInstance;
    private readonly Transform3D[] _cellDrawn;
    private readonly Color[] _cellData;
    private readonly List<MultiMeshInstance3D> _warmInstances = [];
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

    // The labels under the items (GridLayout.Labels; Screens/GridLabels.cs draws them in the overlay): whether the bound
    // layout has them, each cell's title, where its label's top middle shows (shares of the view's width and height from
    // its top left), its scale (1 at rest; the grid's zoom and depth in transitions), and a count that changes whenever
    // any label's title, place or focus may have.
    private bool _labels;
    private readonly string?[] _cellTitle;
    private readonly Vector2[] _labelAt;
    private readonly float[] _labelScale;
    private int _labelsVersion;

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

    // The theme's motion (A6 Motion): the focused item's sway and the others' bob, as multiples of the launcher's own.
    private float _focusSway = 1;
    private float _idleBob = 1;

    // The focused card's video (A6 Card videos): its cell and model, the material showing it, and its own clock for a
    // card without a focused clip.
    private CardVideo? _video;
    private int _videoCell = -1;
    private ItemTemplate? _videoModel;
    private ShaderMaterial? _videoMaterial;
    private double _videoClock;

    // The focused game's video (A6 Game videos): the cell, item and model it's for, how long they've been focused, the
    // playback (and the next one, opening while an ended one holds its last frame), the material and texture showing
    // it, its fade in, and the sound's player. Done: the game has no video, or it can't be played.
    private int _gameVideoCell = -1;
    private int _gameVideoItem = -1;
    private ItemTemplate? _gameVideoModel;
    private float _gameVideoWait;
    private bool _gameVideoDone;
    private string? _gameVideoPath;
    private VideoPlayback? _gameVideo;
    private VideoPlayback? _gameVideoNext;
    private ShaderMaterial? _gameVideoMaterial;
    private ImageTexture? _gameVideoTexture;
    private float _gameVideoFade;
    private readonly AudioStreamPlayer? _videoSound;
    private bool _turned;

    // The inspected game's sharper art (Textures/InspectTextures.cs; only the games grid reads its sources): the cell
    // it's for (-1: none), whether that cell's slots changed since it was asked for, the request's slots and files, the
    // art once it's made, the material showing it, and its fade in.
    private readonly InspectTextures? _inspectArt;
    private readonly int[] _inspectSlots = new int[Slots];
    private readonly string[] _inspectPaths = new string[Slots];
    private int _inspectArtCell = -1;
    private bool _inspectArtStale;
    private InspectArt? _inspectArtShown;
    private ShaderMaterial? _inspectArtMaterial;
    private float _inspectArtFade;

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
    private Vector3 _offset;
    private float _zoom = 1;
    private bool _rootDirty = true;
    private LookBackdrop _background;

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
    public ItemGrid(TextureStreamer? streamer, LookBackdrop background, int maxCells, int blockSize, bool spines, bool systemCards)
    {
        Name = "Grid";
        _streamer = streamer;
        _inspectArt = streamer is { DirectSources: true } ? new InspectTextures() : null;
        _maxCells = maxCells;
        _systemCards = systemCards;
        _background = background;
        _cellItem = new int[maxCells];
        if (!systemCards)
        {
            _videoSound = new AudioStreamPlayer { Name = "VideoSound" };
            AddChild(_videoSound);
        }

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
        _wanted = new bool[maxCells * Slots];
        _textured = new bool[maxCells * Slots];
        _fade = new float[maxCells * Slots];
        _fallback = new byte[maxCells * Slots];
        _next = new int[maxCells * Slots];
        _media = new MediaRef[maxCells * Slots];
        Array.Fill(_cellItem, -1);
        Array.Fill(_cellTemplate, -1);
        Array.Fill(_cellCurve, 1f);
        _cellTitle = new string?[maxCells];
        _labelAt = new Vector2[maxCells];
        _labelScale = new float[maxCells];
        _cellInstance = new int[maxCells];
        _cellDrawn = new Transform3D[maxCells];
        _cellData = new Color[maxCells];
        Array.Fill(_cellInstance, -1);
        for (var cell = 0; cell < maxCells; cell++)
        {
            _cellData[cell] = new Color(cell, 0, 0, 0);
        }

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

    /// <summary>Whether the bound layout shows each item's title under it (<see cref="GridLayout.Labels"/>).</summary>
    public bool HasLabels => _labels && _source is not null;

    /// <summary>The pool's cells: the most labels that can show at once.</summary>
    public int PoolSize => _maxCells;

    /// <summary>Changes whenever a label's title, place or focus may have (each frame the grid moves, and not otherwise).</summary>
    public int LabelsVersion => _labelsVersion;

    /// <summary>A column's width at rest, as a share of the view's width: a label's.</summary>
    public float LabelWidth => _pitchX * _scale / (_viewHeight * _viewAspect);

    /// <summary>
    /// The cell's label, if the layout has labels and the cell is bound: its title, where its top middle shows (shares of
    /// the view's width and height from its top left), its scale (1 at rest), and whether its item is focused.
    /// </summary>
    public bool TryGetLabel(int cell, out string title, out Vector2 at, out float scale, out bool focused)
    {
        title = _cellTitle[cell] ?? string.Empty;
        at = _labelAt[cell];
        scale = _labelScale[cell];
        focused = cell == _focusCell;
        return _labels && _cellItem[cell] >= 0;
    }

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
        StopVideo();
        StopGameVideo();
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

        // Their wrappers are let go now rather than by their finalisers (2026-10-16), which hold the old templates'
        // meshes and textures, and so a theme switched from, in video memory. The nodes freed above, at the end of the
        // frame, are the last to hold them.
        foreach (var multiMesh in _multiMeshes)
        {
            multiMesh?.Dispose();
        }

        foreach (var material in _materials)
        {
            material.Dispose();
        }

        _templates.Clear();
        _multiMeshes.Clear();
        _instances.Clear();
        _instanceCell.Clear();
        _instancesUsed.Clear();
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
            multiMesh = GridMultiMesh.Create(template.Mesh, _maxCells);
            multiMesh.VisibleInstanceCount = 0;
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
        _instanceCell.Add(new int[_maxCells]);
        _instancesUsed.Add(0);
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
        if (_idleBob != 1)
        {
            material.SetShaderParameter(ShaderParams.IdleBob, _idleBob);
        }
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

    /// <summary>Main thread: the theme's sway and bob (A6 Motion), for the focused item and every material's shader.</summary>
    public void SetMotion(ThemeMotion motion)
    {
        _focusSway = motion.FocusSway;
        if (motion.IdleBob == _idleBob)
        {
            return;
        }

        _idleBob = motion.IdleBob;
        foreach (var material in _materials)
        {
            material.SetShaderParameter(ShaderParams.IdleBob, _idleBob);
        }
    }

    /// <summary>
    /// The look's background, for items fading into it (every frame of a look's cross-fade). The wallpapers' textures
    /// are set only when they change.
    /// </summary>
    public void SetBackground(in LookBackdrop background)
    {
        var textures = !background.SameWallpapers(_background);
        _background = background;
        foreach (var material in _materials)
        {
            background.ApplyTo(material, textures);
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
        _labels = _layout.Labels && _layout.Shape == GridShape.Grid;
        _labelsVersion++;
        _pitchX = width * PitchXFactor;
        _pitchY = height * (_labels ? LabelledPitchYFactor : PitchYFactor);
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
    /// With labels, a row is its items and their labels' room (<see cref="LabelRoom"/>), which stays the same on screen.
    /// </summary>
    private float SizeGrid(float viewWidth)
    {
        var usableWidth = viewWidth * 0.9f;
        var band = _viewHeight * (1 - RowsBandTop - RowsBandBottom);
        var room = _labels ? _viewHeight * LabelRoom : 0;
        if (_layout.Columns > 0)
        {
            _scale = Math.Min(usableWidth / (_layout.Columns * _pitchX), RowScale(band / Math.Max(_layout.Rows, 1), room));
            _columns = _layout.Columns;
        }
        else if (_layout.Rows > 0)
        {
            _scale = Math.Min(RowScale(band / _layout.Rows, room), usableWidth / _pitchX);
            _columns = Math.Clamp((int)(usableWidth / (_pitchX * _scale)), 1, MaxColumns);
        }
        else
        {
            _scale = Math.Min(RowScale(_viewHeight / _rowsVisible, room), usableWidth / (PreferredColumns * _pitchX));
            _columns = Math.Clamp((int)(usableWidth / (_pitchX * _scale)), MinColumns, MaxColumns);
        }

        _linePitch = _pitchY + room / _scale;

        // A size that was set lays the rows out in the band: the focused one in the middle of those that fit (the upper
        // of the two middle ones).
        if (_layout.Rows > 0 || _layout.Columns > 0)
        {
            var row = _linePitch * _scale;
            var fitting = _layout.Rows > 0 ? _layout.Rows : Math.Max(1, (int)(band / row + 0.001f));
            _focusLine = _viewHeight / 2 - _viewHeight * RowsBandTop - ((fitting - 1) / 2 + 0.5f) * row;
        }

        // The items' middle is on the line, so a row with its labels under it is centred there too.
        _focusLine += room / 2;
        return _viewHeight / (_linePitch * _scale);
    }

    /// <summary>The scale at which a row, its labels' room included, is <paramref name="height"/> tall (the items keep a quarter of it at least).</summary>
    private float RowScale(float height, float room) => Math.Max(height - room, height * 0.25f) / _pitchY;

    /// <summary>Main thread: hides every item and drops every media request.</summary>
    public void UnbindAll()
    {
        for (var cell = 0; cell < _maxCells; cell++)
        {
            HideCell(cell);
        }

        Array.Fill(_boundRow, -1);
        _fadingSlots = 0;
        _labelsVersion++;
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
        _cellTitle[cell] = info.Title;
        _labelsVersion++;
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
    /// Whether an item is inspected or easing to or from that pose: from <see cref="ToggleInspect"/> until it's back in its
    /// place. The list of titles beside a <see cref="GridShape.List"/> goes behind the 3D for that long.
    /// </summary>
    public bool InspectShown => _inspecting || _inspectBlend > 0 || _previousInspect > 0;

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
        DropInspectArt();
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
    /// mesh). Each template's instance is in a one-instance MultiMesh of its own (the same mesh, material and format,
    /// so the same pipeline), which leaves the grid's instances to its cells. <see cref="EndWarmUp"/> frees them.
    /// </summary>
    public void BeginWarmUp()
    {
        Visible = true;
        for (var t = 0; t < _templates.Count; t++)
        {
            _materials[_templateMaterial[t]].SetShaderParameter(ShaderParams.GridFade, 1.0f);
            if (_multiMeshes[t] is not null)
            {
                var multiMesh = GridMultiMesh.Create(_templates[t].Mesh, 1);
                multiMesh.SetInstanceTransform(0, new Transform3D(Basis.Identity, new Vector3(t * 0.3f, 0, -2)));
                multiMesh.SetInstanceCustomData(0, new Color(0, 0, 0, 0));
                var warm = new MultiMeshInstance3D
                {
                    Name = "WarmUp" + t,
                    Multimesh = multiMesh,
                    MaterialOverride = _materials[_templateMaterial[t]],
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                };
                _root.AddChild(warm);
                _warmInstances.Add(warm);
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
        foreach (var warm in _warmInstances)
        {
            // Its MultiMesh's wrapper would hold the template's mesh until its finaliser ran (2026-10-16).
            warm.Multimesh?.Dispose();
            warm.QueueFree();
        }

        _warmInstances.Clear();
        for (var t = 0; t < _templates.Count; t++)
        {
            _materials[_templateMaterial[t]].SetShaderParameter(ShaderParams.GridFade, _gridFade);
        }

        _warmNode.Visible = false;
        _warmNode.Mesh = null;
        _warmNode.MaterialOverride = null;
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
            UpdateLabels();
            UpdateVideo(dt);
            UpdateGameVideo(dt);
            UpdateInspectArt(dt);
            AnimateFades(dt);
            MeasureTexturing();
        }
        else
        {
            StopVideo();
            StopGameVideo();
            DropInspectArt();
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
}
