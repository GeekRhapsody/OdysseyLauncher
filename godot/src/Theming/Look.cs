using System;
using Godot;
using Launcher.Core.Theming;
using ThemeLook = Launcher.Core.Theming.Look;

namespace Launcher.App.Theming;

/// <summary>
/// A look's background as the item shader fades opaque items into it (A3): its four corners (sRGB) and the wallpapers
/// over them (A6 Background), with their weights and aspects as the background layer has them.
/// </summary>
public readonly struct LookBackdrop(
    Vector3 topLeft, Vector3 topRight, Vector3 bottomLeft, Vector3 bottomRight,
    Texture2D? wallpaperA = null, Texture2D? wallpaperB = null, Vector4 wallpaperState = default)
{
    public Vector3 TopLeft { get; } = topLeft;

    public Vector3 TopRight { get; } = topRight;

    public Vector3 BottomLeft { get; } = bottomLeft;

    public Vector3 BottomRight { get; } = bottomRight;

    public Texture2D? WallpaperA { get; } = wallpaperA;

    public Texture2D? WallpaperB { get; } = wallpaperB;

    /// <summary>(A's weight, B's weight, A's aspect, B's aspect); an aspect of 0 stretches the image.</summary>
    public Vector4 WallpaperState { get; } = wallpaperState;

    /// <summary>Whether the two show the same textures, so a material needn't be pointed at them again.</summary>
    public bool SameWallpapers(in LookBackdrop other) => WallpaperA == other.WallpaperA && WallpaperB == other.WallpaperB;

    /// <summary>
    /// Sets the corners and weights, and the textures when <paramref name="textures"/> is set. Pointing a material at a
    /// texture remakes its uniform set, so it's done only when they change, not every frame of a cross-fade.
    /// </summary>
    public void ApplyTo(ShaderMaterial material, bool textures = true)
    {
        material.SetShaderParameter(ShaderParams.BackgroundTopLeft, TopLeft);
        material.SetShaderParameter(ShaderParams.BackgroundTopRight, TopRight);
        material.SetShaderParameter(ShaderParams.BackgroundBottomLeft, BottomLeft);
        material.SetShaderParameter(ShaderParams.BackgroundBottomRight, BottomRight);
        material.SetShaderParameter(ShaderParams.BackgroundWallpaperState, WallpaperState);
        if (textures)
        {
            // Nil puts the shader's default back: a slot never filled has weight 0.
            material.SetShaderParameter(ShaderParams.BackgroundWallpaperA, WallpaperA is { } a ? a : default(Variant));
            material.SetShaderParameter(ShaderParams.BackgroundWallpaperB, WallpaperB is { } b ? b : default(Variant));
        }
    }
}

/// <summary>
/// The icon.sys-style look on screen (A6): a four-corner gradient on a background canvas layer, an ambient colour, and
/// up to three directional lights in view space (children of the camera). <see cref="Show"/> cross-fades to another
/// look over the theme's <c>look_transition_ms</c>, the way entering a system does; <see cref="Tick"/> drives it with
/// no allocation. At rest, each corner renders as its exact hex value (Linear tonemapper, Colour ambient, no glow).
/// <para>
/// A look's wallpaper (A6 Background) is drawn over the gradient by the same layer, from one of two slots, so a
/// cross-fade between two wallpapers, or to or from none, blends them as it blends the corners. One still loading
/// (<see cref="Wallpapers"/>) leaves the gradient alone until it's in, then fades in.
/// </para>
/// </summary>
public sealed class LookStage
{
    /// <summary>
    /// The highest canvas layer drawn behind the 3D (the environment's <c>background_canvas_max_layer</c>). The gradient
    /// is the layer under it; the list of titles comes down to it while a game is inspected (<see cref="Screens.InfoOverlay"/>).
    /// </summary>
    public const int BackgroundLayer = -1;
    private const int GradientLayer = BackgroundLayer - 1;
    public const int MaxLights = 3;

    private static readonly StringName TopLeftParam = "top_left";
    private static readonly StringName TopRightParam = "top_right";
    private static readonly StringName BottomLeftParam = "bottom_left";
    private static readonly StringName BottomRightParam = "bottom_right";
    private static readonly StringName WallpaperAParam = "wallpaper_a";
    private static readonly StringName WallpaperBParam = "wallpaper_b";
    private static readonly StringName WallpaperStateParam = "wallpaper_state";

    /// <summary>How long a wallpaper that loaded after its look was shown takes to fade in.</summary>
    private const float LateWallpaperSeconds = 0.3f;

    private readonly Godot.Environment _environment;
    private readonly ShaderMaterial _gradient;
    private readonly DirectionalLight3D[] _lights = new DirectionalLight3D[MaxLights];
    private State _from;
    private State _to;
    private State _now;
    private float _elapsed;
    private float _duration;
    private bool _moving;
    private bool _changed;

    private readonly Wallpapers? _wallpapers;
    private ThemeLook? _shown;
    private Slot _slotA;
    private Slot _slotB;

    /// <summary>
    /// Adds the environment, the gradient layer and the lights, showing <paramref name="look"/>, or black with no lights
    /// until <see cref="Show"/> (at boot, before the theme is known). Without <paramref name="wallpapers"/>, looks show
    /// their gradients alone.
    /// </summary>
    public LookStage(Node parent, Camera3D camera, ThemeLook? look = null, Wallpapers? wallpapers = null)
    {
        _wallpapers = wallpapers;
        if (wallpapers is not null)
        {
            wallpapers.Loaded += OnWallpaperLoaded;
        }

        _now = look is null ? default : State.Of(look);
        _environment = new Godot.Environment
        {
            BackgroundMode = Godot.Environment.BGMode.Canvas,
            BackgroundCanvasMaxLayer = BackgroundLayer,
            AmbientLightSource = Godot.Environment.AmbientSource.Color,
            ReflectedLightSource = Godot.Environment.ReflectionSource.Disabled,
            TonemapMode = Godot.Environment.ToneMapper.Linear,
            GlowEnabled = false,
        };
        parent.AddChild(new WorldEnvironment { Environment = _environment });

        _gradient = new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/background_gradient.gdshader") };
        var rect = new ColorRect { Material = _gradient, MouseFilter = Control.MouseFilterEnum.Ignore };
        rect.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        var layer = new CanvasLayer { Layer = GradientLayer, Name = "Background" };
        layer.AddChild(rect);
        parent.AddChild(layer);

        for (var i = 0; i < MaxLights; i++)
        {
            _lights[i] = new DirectionalLight3D { ShadowEnabled = false, Name = $"Light{i}" };
            camera.AddChild(_lights[i]);
        }

        Apply(_now);
    }

    /// <summary>The background on screen now (mid-fade too), for the item materials.</summary>
    public LookBackdrop Backdrop => new(
        _now.TopLeft, _now.TopRight, _now.BottomLeft, _now.BottomRight, _slotA.Texture, _slotB.Texture, WallpaperState(_now));

    /// <summary>True while a cross-fade runs.</summary>
    public bool Moving => _moving;

    /// <summary>Main thread: cross-fades to a look over <paramref name="seconds"/> (0: at once), from wherever the last fade got to.</summary>
    public void Show(ThemeLook look, float seconds)
    {
        _shown = look;
        var (weightA, weightB) = WallpaperWeights(look.Background);
        _from = _now;
        _to = State.Of(look) with { WallpaperA = weightA, WallpaperB = weightB };
        _elapsed = 0;
        _duration = seconds;
        _moving = true;
        _changed = true;
        if (seconds <= 0)
        {
            Tick(0);
            _changed = true;
        }
    }

    /// <summary>Main thread: starts loading a look's wallpaper ahead of it being shown (a system's card focused).</summary>
    public void Prefetch(ThemeLook look)
    {
        if (_wallpapers is not null && look.Background.Wallpaper is { } path)
        {
            _wallpapers.Request(path);
        }
    }

    /// <summary>
    /// Main thread: lets go of the wallpapers not on screen, so a theme applied again (switched to, or updated in place)
    /// reads its files afresh.
    /// </summary>
    public void ForgetWallpapers() => _wallpapers?.Forget(_slotA.Texture, _slotB.Texture);

    /// <summary>
    /// Main thread, each frame: advances a cross-fade. True when the look changed since the last call (the item
    /// materials then take <see cref="Backdrop"/>).
    /// </summary>
    public bool Tick(float dt)
    {
        if (!_moving)
        {
            var changed = _changed;
            _changed = false;
            return changed;
        }

        _changed = false;
        _elapsed += dt;
        var t = _duration <= 0 ? 1 : Math.Min(1, _elapsed / _duration);
        var eased = t * t * (3 - 2 * t);

        // At the end it's the target exactly, so a look at rest shows its hex values.
        _now = t >= 1 ? _to : State.Lerp(_from, _to, eased);
        Apply(_now);
        if (t >= 1)
        {
            _moving = false;
        }

        return true;
    }

    /// <summary>
    /// The weights that show the background's wallpaper from its slot: (1, 0) or (0, 1), its texture put in a slot
    /// first if it's in neither; (0, 0) for none, and while it loads (<see cref="OnWallpaperLoaded"/> shows it then).
    /// </summary>
    private (float A, float B) WallpaperWeights(LookBackground background)
    {
        if (_wallpapers is null || background.Wallpaper is not { } path
            || _wallpapers.Get(path, out var aspect) is not { } texture)
        {
            return (0, 0);
        }

        var shownAspect = background.Fit == WallpaperFit.Stretch ? 0 : aspect;
        if (_slotA.Texture == texture)
        {
            _slotA.Aspect = shownAspect;
            return (1, 0);
        }

        if (_slotB.Texture == texture)
        {
            _slotB.Aspect = shownAspect;
            return (0, 1);
        }

        // The slot showing less of its wallpaper takes it; mid-fade between two others, what's left of that one is cut.
        var useA = _now.WallpaperA <= _now.WallpaperB;
        if (useA)
        {
            _slotA = new Slot(texture, shownAspect);
            _now = _now with { WallpaperA = 0 };
            _gradient.SetShaderParameter(WallpaperAParam, texture);
        }
        else
        {
            _slotB = new Slot(texture, shownAspect);
            _now = _now with { WallpaperB = 0 };
            _gradient.SetShaderParameter(WallpaperBParam, texture);
        }

        _wallpapers.Trim(_slotA.Texture, _slotB.Texture);
        return useA ? (1, 0) : (0, 1);
    }

    private void OnWallpaperLoaded(string path, Texture2D? texture)
    {
        if (texture is not null && _shown is { } shown && shown.Background.Wallpaper == path)
        {
            Show(shown, LateWallpaperSeconds);
        }
        else
        {
            _wallpapers!.Trim(_slotA.Texture, _slotB.Texture);
        }
    }

    private Vector4 WallpaperState(in State state) => new(state.WallpaperA, state.WallpaperB, _slotA.Aspect, _slotB.Aspect);

    private void Apply(in State state)
    {
        _gradient.SetShaderParameter(TopLeftParam, state.TopLeft);
        _gradient.SetShaderParameter(TopRightParam, state.TopRight);
        _gradient.SetShaderParameter(BottomLeftParam, state.BottomLeft);
        _gradient.SetShaderParameter(BottomRightParam, state.BottomRight);
        _gradient.SetShaderParameter(WallpaperStateParam, WallpaperState(state));
        _environment.AmbientLightColor = new Color(state.Ambient.X, state.Ambient.Y, state.Ambient.Z);
        _environment.AmbientLightEnergy = state.AmbientEnergy;
        for (var i = 0; i < MaxLights; i++)
        {
            var light = state.Light(i);
            _lights[i].Visible = light.Energy > 0;
            _lights[i].LightEnergy = light.Energy;
            _lights[i].LightColor = new Color(light.Colour.X, light.Colour.Y, light.Colour.Z);
            _lights[i].Basis = FacingBasis(light.Direction);
        }
    }

    /// <summary>sRGB 0..1, as the shaders take it.</summary>
    public static Vector3 Rgb(Launcher.Core.Theming.Rgb colour) => new(colour.R / 255f, colour.G / 255f, colour.B / 255f);

    /// <summary>A basis whose -Z axis, the way a DirectionalLight3D shines, points along the direction.</summary>
    private static Basis FacingBasis(Vector3 direction)
    {
        var forward = direction.LengthSquared() > 0 ? direction.Normalized() : Vector3.Forward;
        var up = Mathf.Abs(forward.Dot(Vector3.Up)) > 0.999f ? Vector3.Back : Vector3.Up;
        return Basis.LookingAt(forward, up);
    }

    private readonly record struct LightState(Vector3 Direction, Vector3 Colour, float Energy);

    /// <summary>A wallpaper slot: its texture and the aspect it's shown at (0: stretched).</summary>
    private record struct Slot(Texture2D? Texture, float Aspect);

    /// <summary>
    /// A look as numbers that blend: a light the look doesn't have is off (energy 0), aimed like the other side's; each
    /// wallpaper slot's weight (a look shows at most one, so they never sum past 1).
    /// </summary>
    private readonly record struct State(
        Vector3 TopLeft, Vector3 TopRight, Vector3 BottomLeft, Vector3 BottomRight, Vector3 Ambient, float AmbientEnergy,
        LightState Light0, LightState Light1, LightState Light2, float WallpaperA = 0, float WallpaperB = 0)
    {
        public LightState Light(int i) => i switch
        {
            0 => Light0,
            1 => Light1,
            _ => Light2,
        };

        public static State Of(ThemeLook look)
        {
            var lights = new LightState[MaxLights];
            for (var i = 0; i < MaxLights; i++)
            {
                var source = look.Lights[Math.Min(i, look.Lights.Count - 1)];
                var direction = new Vector3(source.Direction.X, source.Direction.Y, source.Direction.Z);
                lights[i] = i < look.Lights.Count
                    ? new LightState(direction, Rgb(source.Colour), source.Energy)
                    : new LightState(direction, Vector3.One, 0);
            }

            var background = look.Background;
            return new State(
                Rgb(background.TopLeft), Rgb(background.TopRight), Rgb(background.BottomLeft), Rgb(background.BottomRight),
                Rgb(look.Ambient.Colour), look.Ambient.Energy, lights[0], lights[1], lights[2]);
        }

        public static State Lerp(in State a, in State b, float t) => new(
            a.TopLeft.Lerp(b.TopLeft, t), a.TopRight.Lerp(b.TopRight, t), a.BottomLeft.Lerp(b.BottomLeft, t),
            a.BottomRight.Lerp(b.BottomRight, t), a.Ambient.Lerp(b.Ambient, t), a.AmbientEnergy + (b.AmbientEnergy - a.AmbientEnergy) * t,
            Blend(a.Light0, b.Light0, t), Blend(a.Light1, b.Light1, t), Blend(a.Light2, b.Light2, t),
            a.WallpaperA + (b.WallpaperA - a.WallpaperA) * t, a.WallpaperB + (b.WallpaperB - a.WallpaperB) * t);

        private static LightState Blend(in LightState a, in LightState b, float t)
        {
            var direction = a.Direction.Normalized().Lerp(b.Direction.Normalized(), t);
            return new LightState(direction.LengthSquared() > 1e-6f ? direction : b.Direction, a.Colour.Lerp(b.Colour, t), a.Energy + (b.Energy - a.Energy) * t);
        }
    }
}

/// <summary>The item shader's uniform names, cached once (C# rules: no implicit string to StringName per use).</summary>
public static class ShaderParams
{
    public static readonly StringName SlotsLarge = "slots_large";
    public static readonly StringName SlotsSmall = "slots_small";
    public static readonly StringName SlotState = "slot_state";
    public static readonly StringName[] Authored = ["authored_1", "authored_2", "authored_3", "authored_4"];
    public static readonly StringName Titles = "titles";
    public static readonly StringName BlockSize = "block_size";
    public static readonly StringName BlockColumns = "block_columns";
    public static readonly StringName SpineOrigin = "spine_origin";
    public static readonly StringName SpineSize = "spine_size";
    public static readonly StringName SpineColumns = "spine_columns";
    public static readonly StringName GridFade = "grid_fade";
    public static readonly StringName TintCase = "tint_case";
    public static readonly StringName IdleBob = "idle_bob";

    /// <summary>The focused game's video (A6 Game videos): its picture, where it shows, and whether it's fitted whole.</summary>
    public static readonly StringName VideoFrame = "video_frame";
    public static readonly StringName VideoState = "video_state";
    public static readonly StringName VideoWhole = "video_whole";

    /// <summary>The inspected game's art (R3): its array, the cell and fade, and each slot's layer.</summary>
    public static readonly StringName SlotsInspect = "slots_inspect";
    public static readonly StringName InspectState = "inspect_state";
    public static readonly StringName InspectLayersLow = "inspect_layers_low";
    public static readonly StringName InspectLayersHigh = "inspect_layers_high";

    /// <summary>A per-instance uniform: INSTANCE_CUSTOM for an item drawn as its own node (item.gdshader).</summary>
    public static readonly StringName NodeCustom = "node_custom";
    public static readonly StringName BackgroundTopLeft = "bg_top_left";
    public static readonly StringName BackgroundTopRight = "bg_top_right";
    public static readonly StringName BackgroundBottomLeft = "bg_bottom_left";
    public static readonly StringName BackgroundBottomRight = "bg_bottom_right";
    public static readonly StringName BackgroundWallpaperA = "bg_wallpaper_a";
    public static readonly StringName BackgroundWallpaperB = "bg_wallpaper_b";
    public static readonly StringName BackgroundWallpaperState = "bg_wallpaper_state";
}
