using System;
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// Generates the built-in models procedurally and exports each with Godot's glTF exporter (A7): the built-in theme's
/// box templates and its arcade cabinet (<see cref="ArcadeCabinetBuilder"/>) in
/// <c>godot/themes/memory-card/models/templates/</c> and its generic system model in
/// <c>godot/themes/memory-card/models/systems/</c>, the Slab theme's card in <c>godot/themes/slab/models/systems/</c>,
/// and the M6 test theme's models in <c>tests/themes/slot-showcase/models/</c>, and the sample theme's in
/// <c>samples/themes/retro-tv/models/</c> (<see cref="RetroTvBuilder"/>). None is imported by Godot (<c>godot/themes/</c> has a <c>.gdignore</c>): every theme's
/// models are loaded from the <c>.glb</c> files at run time (A6 Locations).
/// <para>
/// Run it headless with <c>godot --headless --path godot res://scenes/tools/generate_box_templates.tscn</c> (it quits
/// when done), or open that scene in the editor and press Generate in the inspector. Then commit the <c>.glb</c> files.
/// </para>
/// </summary>
[Tool]
public partial class BoxTemplateGenerator : Node
{
    public const string TemplatesDir = "res://themes/memory-card/models/templates";
    public const string SystemsDir = "res://themes/memory-card/models/systems";

    /// <summary>The Slab theme's card.</summary>
    public const string SlabSystemsDir = "res://themes/slab/models/systems";

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

        // PlayStation: the same jewel case sized by ScreenScraper's PAL art, so none of it is cut off: a 680 x 680 front
        // (1:1), a 765 x 680 back (1.125) and a 65 x 680 spine (0.0956). The art spans the caps inside the chamfers, and
        // the corners' radii are the bevel's, so the caps are square-cornered: the cover is 123.4 x 123.4 beside a
        // 16.23 mm hinge strip, the back 138.83 x 123.4, and the spine wall 11.8 x 123.4 (deeper than a real case's
        // 10.4, which would crop the spine's ends). The theme's psx_jewel_case.
        new("psx_jewel_case", 140.43f, 125, 13.4f, SpineRadius: 0.8f, OpeningRadius: 0.8f, Bevel: 0.8f,
            CaseColour: new Color("#2A2D35"), CaseRoughness: 0.2f, ArtRoughness: 0.22f,
            Split: FrontSplit.SpineStrip, SplitAt: 16.23f, ArtInsideBevels: true),

        // NES, N64 and Game Boy Advance: a cardboard box, 135 x 185 x 32, printed on both sides.
        new("cartridge_box", 135, 185, 32, SpineRadius: 0.6f, OpeningRadius: 0.6f, Bevel: 0.5f,
            CaseColour: new Color("#D9D3C3"), CaseRoughness: 0.9f, ArtRoughness: 0.75f, PrintedOpeningSide: true),

        // Game Boy, Game Boy Color and Super Game Boy: the square cardboard box, 125 x 125, printed on both sides.
        // The depth follows the scraped art rather than a ruler: ScreenScraper's spines are 98 x 700 against a
        // 700 x 700 front and back, so the spine face (the depth less the chamfers, over the height less the
        // corners) is 0.14: (18.2 - 0.8) / 124. A real box is nearer 22 mm, which would crop a fifth off the spine.
        new("gameboy_box", 125, 125, 18.2f, SpineRadius: 0.5f, OpeningRadius: 0.5f, Bevel: 0.4f,
            CaseColour: new Color("#C4C6C8"), CaseRoughness: 0.85f, ArtRoughness: 0.7f, PrintedOpeningSide: true),

        // DOS, Windows and Steam: a PC big box, printed on both sides and over its bevels. Big boxes came in every size,
        // so the theme gives it shape = "media" (A6) and each game's box takes its cover's proportions and its spine's
        // depth; 190 x 240 x 50 is only the shape of a box with no art. Small corners and bevels, so the box can shrink
        // a long way before they meet. The top and bottom are dark, so they don't show as light edges round the art.
        // The theme's generic_box_spine and generic_box_logo templates both use it.
        new("generic_box", 190, 240, 50, SpineRadius: 0.8f, OpeningRadius: 0.8f, Bevel: 0.6f,
            CaseColour: new Color("#26262A"), CaseRoughness: 0.85f, ArtRoughness: 0.7f, PrintedOpeningSide: true,
            PrintedBevels: true),

        // N64: the same big box, landscape, with its spine on the top and bottom, as US and European N64 and SNES boxes'
        // scraped spines are (680 x 97 against a 680 x 497 front). The theme's generic_box_top_spine shapes it by the art
        // too; 190 x 136 x 30 is a box with none.
        new("generic_box_top", 190, 136, 30, SpineRadius: 0.8f, OpeningRadius: 0.8f, Bevel: 0.6f,
            CaseColour: new Color("#26262A"), CaseRoughness: 0.85f, ArtRoughness: 0.7f, SpineOnTop: true,
            PrintedBevels: true),

        // SNES: the US and European cardboard box, landscape, printed over its bevels, with its spine on the top and
        // bottom. Sized by the scraped art, like the Game Boy's: a 680 x 497 front (1.368) and a 680 x 97 top, so the
        // spine face (the width less the corners, over the depth less the chamfers) is 7.0: 188.8 / 27. The left and
        // right flaps are plain dark case. The theme's snes_box_horizontal, SNES's template.
        new("snes_box_horizontal", 190, 139, 28, SpineRadius: 0.6f, OpeningRadius: 0.6f, Bevel: 0.5f,
            CaseColour: new Color("#1C1C20"), CaseRoughness: 0.85f, ArtRoughness: 0.7f, SpineOnTop: true,
            PrintedBevels: true),

        // Super Famicom: the Japanese cardboard box, portrait, printed over its bevels and on both long sides. Sized by
        // the scraped art: a 478 x 864 front (0.553) and a 136 x 864 spine, so the spine face is 0.157: 28.1 / 178.8.
        // The top and bottom flaps are plain off-white card. The theme's snes_box_vertical, which users choose per game.
        new("snes_box_vertical", 99.6f, 180, 29.1f, SpineRadius: 0.6f, OpeningRadius: 0.6f, Bevel: 0.5f,
            CaseColour: new Color("#D6D3CB"), CaseRoughness: 0.85f, ArtRoughness: 0.7f, PrintedOpeningSide: true,
            PrintedBevels: true),

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
    /// The Slab theme's card: the generic card's slab, all dark grey and untinted, its whole front a <c>label</c> slot of
    /// the same grey, so each system's image (its <c>logo</c>, A6 logos/) shows on the case's own colour.
    /// </summary>
    public static readonly BoxSpec SlabSystem =
        new("slab", 72, 100, 11, SpineRadius: 5, OpeningRadius: 5, Bevel: 1.6f,
            CaseColour: new Color("#2C2E32"), CaseRoughness: 0.5f, ArtRoughness: 0.5f,
            FrontSlot: "label", HasBackSlot: false, HasSpineSlot: false, SlotColour: new Color("#2C2E32"));

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

        ok &= ExportMesh(ArcadeCabinetBuilder.Build(out var cabinetTriangles), "arcade_cabinet", cabinetTriangles, $"{TemplatesDir}/arcade_cabinet.glb");

        // Flat cards, chosen per game or system, each shaped by its art (the theme's shape = "media"): the cover (3:4
        // without one), and the screenshot (4:3 and dark without one).
        ok &= ExportMesh(FlatBuilder.Build("cover", 0.75f, null, out var coverTriangles), "flat_cover", coverTriangles, $"{TemplatesDir}/flat_cover.glb");
        ok &= ExportMesh(FlatBuilder.Build("screenshot", 4 / 3f, ImageTexture.CreateFromImage(FlatBuilder.DarkPanel()), out var screenshotTriangles),
            "flat_screenshot", screenshotTriangles, $"{TemplatesDir}/flat_screenshot.glb");
        ok &= Export(GenericSystem, $"{SystemsDir}/{GenericSystem.Id}.glb");
        DirAccess.MakeDirRecursiveAbsolute(ProjectSettings.GlobalizePath(SlabSystemsDir));
        ok &= Export(SlabSystem, $"{SlabSystemsDir}/{SlabSystem.Id}.glb");

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
    private static bool Export(BoxSpec spec, string path) =>
        ExportMesh(BoxBuilder.Build(spec, out var triangles), spec.Id, triangles, path);

    /// <summary>One mesh, exported as a model with one node.</summary>
    /// <param name="path">A <c>res://</c> path, or an absolute one.</param>
    private static bool ExportMesh(ArrayMesh mesh, string id, int triangles, string path)
    {
        var root = new Node3D { Name = id };
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
