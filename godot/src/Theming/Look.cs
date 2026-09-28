using Godot;

namespace Launcher.App.Theming;

/// <summary>
/// The icon.sys-style look (A6): a four-corner gradient on a background canvas layer, an ambient colour, and up to
/// three directional lights in view space (children of the camera). M6 loads it from the theme; until then it's
/// the default theme's values from ARCHITECTURE.md A6.
/// </summary>
public sealed class Look
{
    public const int BackgroundLayer = -1;

    public static Look Default { get; } = new(
        Color.FromHtml("#1B1F4A"),
        Color.FromHtml("#1B1F4A"),
        Color.FromHtml("#04040C"),
        Color.FromHtml("#0B0B24"),
        Color.FromHtml("#303038"),
        1.0f,
        [
            (new Vector3(-0.5f, -0.4f, -0.75f), Color.FromHtml("#FFFFFF"), 1.0f),
            (new Vector3(0.7f, -0.2f, -0.6f), Color.FromHtml("#8090FF"), 0.5f),
            (new Vector3(0.0f, 0.9f, -0.4f), Color.FromHtml("#FF9060"), 0.25f),
        ]);

    public Look(
        Color topLeft,
        Color topRight,
        Color bottomLeft,
        Color bottomRight,
        Color ambient,
        float ambientEnergy,
        (Vector3 Direction, Color Colour, float Energy)[] lights)
    {
        TopLeft = topLeft;
        TopRight = topRight;
        BottomLeft = bottomLeft;
        BottomRight = bottomRight;
        Ambient = ambient;
        AmbientEnergy = ambientEnergy;
        Lights = lights;
    }

    /// <summary>sRGB, as written in the theme.</summary>
    public Color TopLeft { get; }

    public Color TopRight { get; }

    public Color BottomLeft { get; }

    public Color BottomRight { get; }

    public Color Ambient { get; }

    public float AmbientEnergy { get; }

    public (Vector3 Direction, Color Colour, float Energy)[] Lights { get; }

    /// <summary>
    /// Adds the environment, the gradient layer and the lights. The Linear tonemapper, Colour ambient and no glow
    /// keep every corner at its exact sRGB value.
    /// </summary>
    public void Build(Node parent, Camera3D camera)
    {
        var environment = new Godot.Environment
        {
            BackgroundMode = Godot.Environment.BGMode.Canvas,
            BackgroundCanvasMaxLayer = BackgroundLayer,
            AmbientLightSource = Godot.Environment.AmbientSource.Color,
            AmbientLightColor = Ambient,
            AmbientLightEnergy = AmbientEnergy,
            ReflectedLightSource = Godot.Environment.ReflectionSource.Disabled,
            TonemapMode = Godot.Environment.ToneMapper.Linear,
            GlowEnabled = false,
        };
        parent.AddChild(new WorldEnvironment { Environment = environment });

        var material = new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/background_gradient.gdshader") };
        material.SetShaderParameter("top_left", ToRgb(TopLeft));
        material.SetShaderParameter("top_right", ToRgb(TopRight));
        material.SetShaderParameter("bottom_left", ToRgb(BottomLeft));
        material.SetShaderParameter("bottom_right", ToRgb(BottomRight));
        var gradient = new ColorRect { Material = material, MouseFilter = Control.MouseFilterEnum.Ignore };
        gradient.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        var layer = new CanvasLayer { Layer = BackgroundLayer, Name = "Background" };
        layer.AddChild(gradient);
        parent.AddChild(layer);

        foreach (var (direction, colour, energy) in Lights)
        {
            var light = new DirectionalLight3D { LightColor = colour, LightEnergy = energy, ShadowEnabled = false };
            light.Basis = FacingBasis(direction);
            camera.AddChild(light);
        }
    }

    /// <summary>The corners for a shader that fades items into the background (A3: opaque, no blending).</summary>
    public void ApplyTo(ShaderMaterial material)
    {
        material.SetShaderParameter(ShaderParams.BackgroundTopLeft, ToRgb(TopLeft));
        material.SetShaderParameter(ShaderParams.BackgroundTopRight, ToRgb(TopRight));
        material.SetShaderParameter(ShaderParams.BackgroundBottomLeft, ToRgb(BottomLeft));
        material.SetShaderParameter(ShaderParams.BackgroundBottomRight, ToRgb(BottomRight));
    }

    /// <summary>A basis whose -Z axis, the way a DirectionalLight3D shines, points along the direction.</summary>
    private static Basis FacingBasis(Vector3 direction)
    {
        var forward = direction.Normalized();
        var up = Mathf.Abs(forward.Dot(Vector3.Up)) > 0.999f ? Vector3.Back : Vector3.Up;
        return Basis.LookingAt(forward, up);
    }

    private static Vector3 ToRgb(Color colour) => new(colour.R, colour.G, colour.B);
}

/// <summary>The item shader's uniform names, cached once (C# rules: no implicit string to StringName per use).</summary>
public static class ShaderParams
{
    public static readonly StringName Covers = "covers";
    public static readonly StringName Titles = "titles";
    public static readonly StringName BlockSize = "block_size";
    public static readonly StringName BlockColumns = "block_columns";
    public static readonly StringName SpineOrigin = "spine_origin";
    public static readonly StringName SpineSize = "spine_size";
    public static readonly StringName SpineColumns = "spine_columns";
    public static readonly StringName GridFade = "grid_fade";
    public static readonly StringName TintCase = "tint_case";
    public static readonly StringName BackgroundTopLeft = "bg_top_left";
    public static readonly StringName BackgroundTopRight = "bg_top_right";
    public static readonly StringName BackgroundBottomLeft = "bg_bottom_left";
    public static readonly StringName BackgroundBottomRight = "bg_bottom_right";
}
