using System;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Grid;
using Launcher.App.Models;
using Launcher.App.Navigation;
using Launcher.App.Theming;
using Launcher.Core.Library;
using ThemeLook = Launcher.Core.Theming.Look;

namespace Launcher.App.Screens;

/// <summary>
/// One item's model, large, in a world of its own (a system's details): a <see cref="SubViewport"/> with its own camera,
/// its look's gradient, ambient and lights (<see cref="LookStage"/>), and a one-cell <see cref="ItemGrid"/> showing it
/// one at a time and focused, so the model is drawn as the grid draws it (its colour, its generated faces and title, its
/// clips, the focus's sway) and turns as it does (<see cref="Tick"/>, <see cref="Step"/>). Its own world keeps its
/// environment and lights away from the grids'. Shown through a <see cref="TextureRect"/>, rendered at the grids' pixel
/// density (A3: 3D at no more than 1080p).
/// <para>
/// There's one, made on first use and kept (<see cref="Show"/>, <see cref="Park"/>): making its world, grid and render
/// target took 10–15 ms of the main thread, and its render target's first frames more, on every open.
/// </para>
/// </summary>
public sealed partial class ModelView : Control
{
    /// <summary>
    /// The model at rest fills at most these shares of the view's height and width (the one-at-a-time layout fits it in
    /// about half), leaving room for the focus's growth, lift and sway.
    /// </summary>
    private const float FillHeight = 0.62f;
    private const float FillWidth = 0.66f;

    /// <summary>A left or right press turns the model as this long at the stick's full tilt does (0.3 rad).</summary>
    private const float StepSeconds = 0.1f;

    private static ModelView? _shared;

    private readonly SubViewport _viewport;
    private readonly LookStage _stage;
    private readonly ItemGrid _grid;
    private ItemTemplate? _model;
    private OneItem _item = new(string.Empty, default);

    private ModelView()
    {
        Name = "ModelView";
        MouseFilter = MouseFilterEnum.Ignore;
        _viewport = new SubViewport
        {
            Name = "ModelWorld",
            OwnWorld3D = true,
            RenderTargetUpdateMode = SubViewport.UpdateMode.Always,
            Size = new Vector2I(16, 16),
        };
        AddChild(_viewport);

        var camera = new Camera3D { Fov = Main.FieldOfView, Position = new Vector3(0, 0, Main.CameraDistance), Current = true };
        _viewport.AddChild(camera);
        _stage = new LookStage(_viewport, camera);

        _grid = new ItemGrid(null, _stage.Colours, maxCells: 1, blockSize: 192, spines: false, systemCards: true)
        {
            Name = "Model",
            Layout = new GridLayout(GridShape.Single),
            FadeAtEdges = false,
        };
        _viewport.AddChild(_grid);

        var picture = new TextureRect
        {
            Texture = _viewport.GetTexture(),
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.Scale,
            MouseFilter = MouseFilterEnum.Ignore,
        };
        picture.SetAnchorsPreset(LayoutPreset.FullRect);
        AddChild(picture);
        Resized += Fit;
    }

    /// <summary>
    /// Main thread: the model view, moved into <paramref name="parent"/> (which may not be in the tree yet), showing
    /// <paramref name="model"/> in <paramref name="look"/>.
    /// </summary>
    /// <param name="title">The item's name, for a face the launcher draws (a generated label).</param>
    /// <param name="colour">Its plain colour (a system's card takes its system's).</param>
    public static ModelView Show(Control parent, ItemTemplate model, string title, Color colour, ThemeLook look)
    {
        if (_shared is null || !IsInstanceValid(_shared))
        {
            _shared = new ModelView();
        }

        var view = _shared;
        view._stage.Show(look, 0);
        view._grid.SetBackground(view._stage.Colours);
        if (view._model != model)
        {
            view._model = model;
            view._grid.SetTemplates([model]);
        }
        else
        {
            view._grid.UnbindAll();
        }

        // Bound once it's in the tree and laid out (Fit).
        view._item = new OneItem(title, colour);
        view.GetParent()?.RemoveChild(view);
        view.Visible = true;
        view._viewport.RenderTargetUpdateMode = SubViewport.UpdateMode.Always;
        parent.AddChild(view);
        return view;
    }

    /// <summary>
    /// Main thread: puts the view aside under <paramref name="keeper"/> (so it's freed with the scene), hidden and not
    /// rendering, until it's shown again. Its model stays, for the same system's details next time.
    /// </summary>
    public void Park(Node keeper)
    {
        _grid.UnbindAll();
        _viewport.RenderTargetUpdateMode = SubViewport.UpdateMode.Disabled;
        Visible = false;
        GetParent()?.RemoveChild(this);
        keeper.AddChild(this);
    }

    /// <summary>Shown again at the size it had, it gets no <see cref="Control.Resized"/>: it's bound here.</summary>
    public override void _EnterTree() => Fit();

    /// <summary>Main thread, each frame while it's shown: the right stick turns the model; then its motion.</summary>
    public void Tick(float dt)
    {
        if (NavInput.ReadTurn() is var turn && turn != Vector2.Zero)
        {
            _grid.Turn(turn, dt);
        }

        _grid.Tick(dt);
    }

    /// <summary>A step of the turn round its vertical (-1 left, 1 right), for the D-pad, the arrows and the left stick.</summary>
    public void Step(int direction) => _grid.Turn(new Vector2(direction, 0), StepSeconds);

    /// <summary>
    /// The render target follows the control's size at the grids' density: the window's pixels per UI unit, times the
    /// main view's 3D scale. The camera is the grids', so the lighting matches theirs; the model is zoomed to fill the
    /// view, whatever its shape. Binds the model if it isn't bound. Nothing while it's parked.
    /// </summary>
    private void Fit()
    {
        if (Size.X < 1 || Size.Y < 1 || _model is null || !Visible || !IsInsideTree())
        {
            return;
        }

        var root = GetViewport();
        var visible = root.GetVisibleRect().Size.Y;
        var density = (visible > 0 ? DisplayServer.WindowGetSize().Y / visible : 1) * root.Scaling3DScale;
        var pixels = new Vector2I(Math.Max(1, (int)(Size.X * density)), Math.Max(1, (int)(Size.Y * density)));
        if (_viewport.Size != pixels)
        {
            _viewport.Size = pixels;
        }

        // A new view binds the grid again (SetView); an unbound one is bound.
        var height = 2 * Main.CameraDistance * Mathf.Tan(Mathf.DegToRad(Main.FieldOfView / 2));
        var aspect = Size.X / Size.Y;
        _grid.SetView(height, aspect, Main.CameraDistance);
        if (_grid.Source is null)
        {
            _grid.Bind(_item, 0);
        }

        var size = _model.Size;
        var fill = Math.Min(height * FillHeight / Math.Max(size.Y, 0.01f), height * aspect * FillWidth / Math.Max(size.X, 0.01f));
        _grid.Zoom = fill / _grid.ItemScale;
    }

    /// <summary>The one item: its title and colour, no media (a system's card has none).</summary>
    private sealed class OneItem(string title, Color colour) : IGridSource
    {
        public int Count => 1;

        public void Describe(int index, out CellInfo cell) => cell = new CellInfo { Title = title, Template = 0, Plain = colour };

        public bool TryGetMedia(int index, int slot, out MediaRef media)
        {
            media = default;
            return false;
        }

        public bool UsesTemplate(int template) => template == 0;
    }
}
