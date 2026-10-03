using System;
using Godot;
using Launcher.Core.Theming;
using ThemeLook = Launcher.Core.Theming.Look;

namespace Launcher.App.Theming;

/// <summary>A look's four background corners (sRGB), which the item shader fades opaque items into (A3).</summary>
public readonly struct LookColours(Vector3 topLeft, Vector3 topRight, Vector3 bottomLeft, Vector3 bottomRight)
{
    public Vector3 TopLeft { get; } = topLeft;

    public Vector3 TopRight { get; } = topRight;

    public Vector3 BottomLeft { get; } = bottomLeft;

    public Vector3 BottomRight { get; } = bottomRight;

    public static LookColours Of(ThemeLook look) => new(
        LookStage.Rgb(look.Background.TopLeft), LookStage.Rgb(look.Background.TopRight),
        LookStage.Rgb(look.Background.BottomLeft), LookStage.Rgb(look.Background.BottomRight));

    public void ApplyTo(ShaderMaterial material)
    {
        material.SetShaderParameter(ShaderParams.BackgroundTopLeft, TopLeft);
        material.SetShaderParameter(ShaderParams.BackgroundTopRight, TopRight);
        material.SetShaderParameter(ShaderParams.BackgroundBottomLeft, BottomLeft);
        material.SetShaderParameter(ShaderParams.BackgroundBottomRight, BottomRight);
    }
}

/// <summary>
/// The icon.sys-style look on screen (A6): a four-corner gradient on a background canvas layer, an ambient colour, and
/// up to three directional lights in view space (children of the camera). <see cref="Show"/> cross-fades to another
/// look over the theme's <c>look_transition_ms</c>, the way entering a system does; <see cref="Tick"/> drives it with
/// no allocation. At rest, each corner renders as its exact hex value (Linear tonemapper, Colour ambient, no glow).
/// </summary>
public sealed class LookStage
{
    public const int BackgroundLayer = -1;
    public const int MaxLights = 3;

    private static readonly StringName TopLeftParam = "top_left";
    private static readonly StringName TopRightParam = "top_right";
    private static readonly StringName BottomLeftParam = "bottom_left";
    private static readonly StringName BottomRightParam = "bottom_right";

    private readonly Godot.Environment _environment;
    private readonly ShaderMaterial _gradient;
    private readonly DirectionalLight3D[] _lights = new DirectionalLight3D[MaxLights];
    private State _from;
    private State _to;
    private State _now;
    private float _elapsed;
    private float _duration;
    private bool _moving;

    /// <summary>
    /// Adds the environment, the gradient layer and the lights, showing <paramref name="look"/>, or black with no lights
    /// until <see cref="Show"/> (at boot, before the theme is known).
    /// </summary>
    public LookStage(Node parent, Camera3D camera, ThemeLook? look = null)
    {
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
        var layer = new CanvasLayer { Layer = BackgroundLayer, Name = "Background" };
        layer.AddChild(rect);
        parent.AddChild(layer);

        for (var i = 0; i < MaxLights; i++)
        {
            _lights[i] = new DirectionalLight3D { ShadowEnabled = false, Name = $"Light{i}" };
            camera.AddChild(_lights[i]);
        }

        Apply(_now);
    }

    /// <summary>The corners on screen now (mid-fade too), for the item materials.</summary>
    public LookColours Colours => new(_now.TopLeft, _now.TopRight, _now.BottomLeft, _now.BottomRight);

    /// <summary>True while a cross-fade runs.</summary>
    public bool Moving => _moving;

    /// <summary>Main thread: cross-fades to a look over <paramref name="seconds"/> (0: at once), from wherever the last fade got to.</summary>
    public void Show(ThemeLook look, float seconds)
    {
        _from = _now;
        _to = State.Of(look);
        _elapsed = 0;
        _duration = seconds;
        _moving = true;
        if (seconds <= 0)
        {
            Tick(0);
        }
    }

    /// <summary>Main thread, each frame: advances a cross-fade. True when the look changed this frame.</summary>
    public bool Tick(float dt)
    {
        if (!_moving)
        {
            return false;
        }

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

    private void Apply(in State state)
    {
        _gradient.SetShaderParameter(TopLeftParam, state.TopLeft);
        _gradient.SetShaderParameter(TopRightParam, state.TopRight);
        _gradient.SetShaderParameter(BottomLeftParam, state.BottomLeft);
        _gradient.SetShaderParameter(BottomRightParam, state.BottomRight);
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

    /// <summary>A look as numbers that blend: a light the look doesn't have is off (energy 0), aimed like the other side's.</summary>
    private readonly record struct State(
        Vector3 TopLeft, Vector3 TopRight, Vector3 BottomLeft, Vector3 BottomRight, Vector3 Ambient, float AmbientEnergy,
        LightState Light0, LightState Light1, LightState Light2)
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
            Blend(a.Light0, b.Light0, t), Blend(a.Light1, b.Light1, t), Blend(a.Light2, b.Light2, t));

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
    public static readonly StringName EdgeFade = "edge_fade";
    public static readonly StringName TintCase = "tint_case";

    /// <summary>A per-instance uniform: INSTANCE_CUSTOM for an item drawn as its own node (item.gdshader).</summary>
    public static readonly StringName NodeCustom = "node_custom";
    public static readonly StringName BackgroundTopLeft = "bg_top_left";
    public static readonly StringName BackgroundTopRight = "bg_top_right";
    public static readonly StringName BackgroundBottomLeft = "bg_bottom_left";
    public static readonly StringName BackgroundBottomRight = "bg_bottom_right";
}
