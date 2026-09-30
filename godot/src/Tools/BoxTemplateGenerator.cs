using System;
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// Generates the built-in models procedurally and exports each with Godot's glTF exporter (A7): the built-in theme's
/// box templates in <c>res://themes/memory-card/models/templates/</c> and its generic system model in
/// <c>res://themes/memory-card/models/systems/</c>, and the M6 test theme's models in
/// <c>tests/themes/slot-showcase/models/</c>, and the sample theme's in <c>samples/themes/retro-tv/models/</c>
/// (<see cref="RetroTvBuilder"/>; both outside the project, so Godot doesn't import them: a user theme's models are
/// loaded from the <c>.glb</c> at run time).
/// <para>
/// Run it headless with <c>godot --headless --path godot res://scenes/tools/generate_box_templates.tscn</c> (it quits
/// when done), or open that scene in the editor and press Generate in the inspector. Then run
/// <c>godot --headless --path godot --import</c> and commit the <c>.glb</c> and <c>.import</c> files.
/// </para>
/// </summary>
[Tool]
public partial class BoxTemplateGenerator : Node
{
    public const string TemplatesDir = "res://themes/memory-card/models/templates";
    public const string SystemsDir = "res://themes/memory-card/models/systems";

    /// <summary>The test theme, relative to the project folder.</summary>
    public const string TestThemeDir = "../tests/themes/slot-showcase/models";

    /// <summary>The sample theme for theme authors (M6 part 2), relative to the project folder.</summary>
    public const string SampleThemeDir = "../samples/themes/retro-tv/models";

    // Sizes are in millimetres, from real cases (width x height x depth).
    public static readonly BoxSpec[] Templates =
    [
        // PS2 and GameCube: a black DVD keep case, 135 x 190 x 14, with the art under a clear sleeve.
        new("dvd_case", 135, 190, 14, SpineRadius: 2.5f, OpeningRadius: 3.5f, Bevel: 1.2f,
            CaseColour: new Color("#121216"), CaseRoughness: 0.4f, ArtRoughness: 0.3f),

        // PlayStation, Saturn and Dreamcast: a CD jewel case, 142 x 125 x 10.4. The front's hinge strip is clear
        // plastic; the booklet sits to its right.
        new("jewel_case", 142, 125, 10.4f, SpineRadius: 0.8f, OpeningRadius: 0.8f, Bevel: 0.8f,
            CaseColour: new Color("#2A2D35"), CaseRoughness: 0.2f, ArtRoughness: 0.22f,
            Split: FrontSplit.SpineStrip, SplitAt: 15),

        // NES, SNES, N64 and the Game Boy family: a cardboard box, 135 x 185 x 32, printed on both sides.
        new("cartridge_box", 135, 185, 32, SpineRadius: 0.6f, OpeningRadius: 0.6f, Bevel: 0.5f,
            CaseColour: new Color("#D9D3C3"), CaseRoughness: 0.9f, ArtRoughness: 0.75f, PrintedOpeningSide: true),

        // Mega Drive (and Master System): the European plastic clamshell, 136 x 190 x 24, with a thick rim.
        new("clamshell", 136, 190, 24, SpineRadius: 3, OpeningRadius: 6, Bevel: 2.5f,
            CaseColour: new Color("#0E0E10"), CaseRoughness: 0.45f, ArtRoughness: 0.3f),

        // PSP: a UMD case, 104 x 180 x 14, with large rounded corners on the opening side.
        new("umd_case", 104, 180, 14, SpineRadius: 4, OpeningRadius: 14, Bevel: 1.4f,
            CaseColour: new Color("#15161A"), CaseRoughness: 0.4f, ArtRoughness: 0.3f),
    ];

    /// <summary>
    /// A memory-card-shaped slab with a label on its upper part, for systems with no model of their own. The case is
    /// light grey so the grid can tint it per system.
    /// </summary>
    public static readonly BoxSpec GenericSystem =
        new("generic", 72, 100, 11, SpineRadius: 5, OpeningRadius: 5, Bevel: 1.6f,
            CaseColour: new Color("#B4B8C0"), CaseRoughness: 0.45f, ArtRoughness: 0.5f,
            FrontSlot: "label", HasBackSlot: false, HasSpineSlot: false, Split: FrontSplit.TopLabel, SplitAt: 34);

    /// <summary>
    /// The test theme's game template: a tall case with the cover on the upper front, a 16:9 screenshot panel below
    /// it whose authored texture is a test card, and a spine. Four materials, the A7 budget.
    /// </summary>
    public static readonly BoxSpec ShowcaseCase =
        new("showcase_case", 135, 262, 16, SpineRadius: 3, OpeningRadius: 5, Bevel: 1.5f,
            CaseColour: new Color("#1A1D24"), CaseRoughness: 0.35f, ArtRoughness: 0.3f,
            HasBackSlot: false, Split: FrontSplit.LowerPanel, SplitAt: 76, LowerSlot: "screenshot", TestCardOnLowerSlot: true);

    /// <summary>The test theme's system card: a square tile with a label on its upper part, tinted per system.</summary>
    public static readonly BoxSpec Tile =
        new("tile", 100, 100, 10, SpineRadius: 8, OpeningRadius: 8, Bevel: 2,
            CaseColour: new Color("#C8CCD4"), CaseRoughness: 0.5f, ArtRoughness: 0.5f,
            FrontSlot: "label", HasBackSlot: false, HasSpineSlot: false, Split: FrontSplit.TopLabel, SplitAt: 30);

    [ExportToolButton("Generate")]
    public Callable GenerateButton => Callable.From(() => Generate());

    public override void _Ready()
    {
        if (Engine.IsEditorHint())
        {
            return;
        }

        GetTree().Quit(Generate() ? 0 : 1);
    }

    /// <summary>Writes every model. Returns false if any failed.</summary>
    public static bool Generate()
    {
        var ok = true;
        DirAccess.MakeDirRecursiveAbsolute(ProjectSettings.GlobalizePath(TemplatesDir));
        DirAccess.MakeDirRecursiveAbsolute(ProjectSettings.GlobalizePath(SystemsDir));
        foreach (var spec in Templates)
        {
            ok &= Export(spec, $"{TemplatesDir}/{spec.Id}.glb");
        }

        ok &= Export(GenericSystem, $"{SystemsDir}/{GenericSystem.Id}.glb");

        var testTheme = System.IO.Path.GetFullPath(System.IO.Path.Combine(ProjectSettings.GlobalizePath("res://"), TestThemeDir));
        DirAccess.MakeDirRecursiveAbsolute(System.IO.Path.Combine(testTheme, "templates"));
        DirAccess.MakeDirRecursiveAbsolute(System.IO.Path.Combine(testTheme, "systems"));
        ok &= Export(ShowcaseCase, System.IO.Path.Combine(testTheme, "templates", ShowcaseCase.Id + ".glb"));
        ok &= Export(Tile, System.IO.Path.Combine(testTheme, "systems", Tile.Id + ".glb"));

        var sample = System.IO.Path.GetFullPath(System.IO.Path.Combine(ProjectSettings.GlobalizePath("res://"), SampleThemeDir));
        DirAccess.MakeDirRecursiveAbsolute(System.IO.Path.Combine(sample, "templates"));
        DirAccess.MakeDirRecursiveAbsolute(System.IO.Path.Combine(sample, "systems"));
        ok &= ExportScene(RetroTvBuilder.Tv(out var tvTriangles), tvTriangles, System.IO.Path.Combine(sample, "templates", "crt_tv.glb"));
        ok &= ExportScene(RetroTvBuilder.ConsoleModel(out var consoleTriangles), consoleTriangles, System.IO.Path.Combine(sample, "systems", "console.glb"));
        return ok;
    }

    /// <summary>A node tree with meshes and an <see cref="AnimationPlayer"/>, exported with its clips.</summary>
    private static bool ExportScene(Node3D root, int triangles, string path)
    {
        try
        {
            var document = new GltfDocument();
            var state = new GltfState();
            var error = document.AppendFromScene(root, state);
            if (error == Error.Ok)
            {
                error = document.WriteToFilesystem(state, path);
            }

            if (error != Error.Ok)
            {
                GD.PrintErr($"Box templates: couldn't export {path}: {error}");
                return false;
            }

            GD.Print($"Box templates: {path}: about {triangles} triangles, {state.GetMaterials().Count} materials, {state.GetAnimations().Count} clips");
            return true;
        }
        finally
        {
            root.Free();
        }
    }

    /// <param name="path">A <c>res://</c> path, or an absolute one.</param>
    private static bool Export(BoxSpec spec, string path)
    {
        var mesh = BoxBuilder.Build(spec, out var triangles);
        var root = new Node3D { Name = spec.Id };
        root.AddChild(new MeshInstance3D { Name = "box", Mesh = mesh });
        try
        {
            var document = new GltfDocument();
            var state = new GltfState();
            var error = document.AppendFromScene(root, state);
            if (error == Error.Ok)
            {
                error = document.WriteToFilesystem(state, ProjectSettings.GlobalizePath(path));
            }

            if (error != Error.Ok)
            {
                GD.PrintErr($"Box templates: couldn't export {path}: {error}");
                return false;
            }

            var aabb = mesh.GetAabb();
            GD.Print(FormattableString.Invariant(
                $"Box templates: {path}: {triangles} triangles, {mesh.GetSurfaceCount()} materials, size {aabb.Size.X:0.000} x {aabb.Size.Y:0.000} x {aabb.Size.Z:0.000} m"));
            return true;
        }
        finally
        {
            root.Free();
        }
    }
}
