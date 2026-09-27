using System.Runtime.InteropServices;
using Godot;
using Launcher.App.Diagnostics;
using Launcher.Core;
using Launcher.Core.Diagnostics;

namespace Launcher.App.Boot;

/// <summary>
/// Scaffold main scene: a hard-coded preview of the memory card style, with a four-corner gradient,
/// three view-space directional lights, an ambient colour and one spinning case. M5 and M6
/// replace it with the real grid and theme loading.
/// </summary>
public partial class Main : Node3D
{
    private const int BackgroundLayer = -1;
    private const float SpinRadiansPerSecond = 0.8f;

    // Placeholder look, matching the default theme example in docs/ARCHITECTURE.md (A6).
    private static readonly Color TopLeft = Color.FromHtml("#1B1F4A");
    private static readonly Color TopRight = Color.FromHtml("#1B1F4A");
    private static readonly Color BottomLeft = Color.FromHtml("#04040C");
    private static readonly Color BottomRight = Color.FromHtml("#0B0B24");
    private static readonly Color Ambient = Color.FromHtml("#303038");

    private static readonly (Vector3 Direction, Color Colour, float Energy)[] Lights =
    [
        (new Vector3(-0.5f, -0.4f, -0.75f), Color.FromHtml("#FFFFFF"), 1.0f),
        (new Vector3(0.7f, -0.2f, -0.6f), Color.FromHtml("#8090FF"), 0.5f),
        (new Vector3(0.0f, 0.9f, -0.4f), Color.FromHtml("#FF9060"), 0.25f),
    ];

    // DVD case proportions (135 x 190 x 14 mm), scaled to 1 m tall as the model spec requires (A7).
    private static readonly Vector3 CaseSize = new(0.711f, 1.0f, 0.074f);

    private Node3D _casePivot = null!;
    private bool _waitingForFirstFrame;

    public override void _Ready()
    {
        BuildBackground();
        BuildCameraAndLights();
        BuildCase();
        BuildLabel();

        DebugHooks.Timeline.Mark(StartupMarks.MainReady);
        RenderingServer.FramePostDraw += OnFramePostDraw;
        _waitingForFirstFrame = true;

        GD.Print(
            $"Launcher.Core {CoreInfo.Version} | Godot {Engine.GetVersionInfo()["string"].AsString()} | " +
            $"{RuntimeInformation.FrameworkDescription} | " +
            $"{RenderingServer.GetCurrentRenderingMethod()}/{RenderingServer.GetCurrentRenderingDriverName()}");
    }

    public override void _ExitTree()
    {
        StopWaitingForFirstFrame();
    }

    public override void _Process(double delta)
    {
        _casePivot.RotateY((float)delta * SpinRadiansPerSecond);
    }

    private void OnFramePostDraw()
    {
        // The scaffold is interactive as soon as its first frame is drawn.
        DebugHooks.Timeline.Mark(StartupMarks.Interactive);
        StopWaitingForFirstFrame();
    }

    private void StopWaitingForFirstFrame()
    {
        if (_waitingForFirstFrame)
        {
            _waitingForFirstFrame = false;
            RenderingServer.FramePostDraw -= OnFramePostDraw;
        }
    }

    private void BuildBackground()
    {
        // The gradient sits on a canvas layer drawn behind the 3D scene. The Linear tonemapper and
        // Colour ambient keep every corner at its exact sRGB value.
        var environment = new Godot.Environment
        {
            BackgroundMode = Godot.Environment.BGMode.Canvas,
            BackgroundCanvasMaxLayer = BackgroundLayer,
            AmbientLightSource = Godot.Environment.AmbientSource.Color,
            AmbientLightColor = Ambient,
            AmbientLightEnergy = 1.0f,
            ReflectedLightSource = Godot.Environment.ReflectionSource.Disabled,
            TonemapMode = Godot.Environment.ToneMapper.Linear,
            GlowEnabled = false,
        };
        AddChild(new WorldEnvironment { Environment = environment });

        var material = new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/background_gradient.gdshader") };
        material.SetShaderParameter("top_left", ToRgb(TopLeft));
        material.SetShaderParameter("top_right", ToRgb(TopRight));
        material.SetShaderParameter("bottom_left", ToRgb(BottomLeft));
        material.SetShaderParameter("bottom_right", ToRgb(BottomRight));

        var gradient = new ColorRect { Material = material, MouseFilter = Control.MouseFilterEnum.Ignore };
        gradient.SetAnchorsPreset(Control.LayoutPreset.FullRect);

        var layer = new CanvasLayer { Layer = BackgroundLayer };
        layer.AddChild(gradient);
        AddChild(layer);
    }

    private void BuildCameraAndLights()
    {
        // The camera looks along -Z at the middle of the case.
        var camera = new Camera3D { Fov = 40.0f, Position = new Vector3(0.0f, 0.5f, 3.0f), Current = true };
        AddChild(camera);

        // Theme light directions are in view space, as in icon.sys, so the lights are camera children.
        foreach (var (direction, colour, energy) in Lights)
        {
            var light = new DirectionalLight3D { LightColor = colour, LightEnergy = energy, ShadowEnabled = false };
            light.Basis = FacingBasis(direction);
            camera.AddChild(light);
        }
    }

    private void BuildCase()
    {
        // The pivot is the model origin: the bottom-centre of the case.
        _casePivot = new Node3D { Name = "CasePivot" };
        AddChild(_casePivot);

        var mesh = new BoxMesh
        {
            Size = CaseSize,
            Material = new StandardMaterial3D { AlbedoColor = Color.FromHtml("#D8D8E0"), Roughness = 0.6f },
        };
        _casePivot.AddChild(new MeshInstance3D { Mesh = mesh, Position = new Vector3(0.0f, CaseSize.Y / 2.0f, 0.0f) });

        // Start turned away so that, a second in, the case shows its front and one side.
        _casePivot.RotateY(-1.3f);
    }

    private void BuildLabel()
    {
        var label = new Label { Text = $"Odyssey Launcher · scaffold\nLauncher.Core {CoreInfo.Version}" };
        var layer = new CanvasLayer { Layer = 1 };
        layer.AddChild(label);
        AddChild(layer);
        label.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.BottomLeft, Control.LayoutPresetMode.Minsize, 24);
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
