using System.IO.Compression;
using System.Text;
using System.Text.Json.Nodes;
using Launcher.Core.Diagnostics;
using Launcher.Core.Media;
using Launcher.Core.Models;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Models;

/// <summary>Budgets enforced when a model is processed, OBJ conversion, the processed-model cache and the model log.</summary>
public sealed class ModelProcessingTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    private string Scratch => _dir.Combine("scratch");

    private static IImageDecoder Decoder()
    {
        var decoder = PlatformServices.CreateImageDecoder();
        Assert.SkipWhen(decoder is null, "no image decoder on this platform");
        return decoder;
    }

    // ---- Processing ---------------------------------------------------------------------------------------

    [Fact]
    public void Textures_over_the_budget_are_scaled_down_and_the_rest_kept()
    {
        var model = ModelFixtures.Model(200, ["cover", "case"], [(2048, 1024), (64, 64)]);

        var processed = ModelProcessor.Process(model, ModelKind.PerGame, Decoder(), Scratch);

        Assert.NotNull(processed.Glb);
        Assert.True(processed.Report.Accepted);
        Assert.Equal(1024, processed.Report.LargestTextureSide);
        Assert.Contains(processed.Report.Notes, n => n.Contains("scaled down from 2048×1024 to 1024×512", StringComparison.Ordinal));
        var images = ModelInspector.Inspect(processed.Glb!, ModelKind.PerGame).Images;
        Assert.Equal([(1024, 512), (64, 64)], images.Select(i => (i.Width, i.Height)));
        Assert.Empty(Directory.Exists(Scratch) ? Directory.GetFiles(Scratch) : []);
    }

    [Fact]
    public void Without_a_decoder_an_oversized_texture_is_kept_with_a_warning()
    {
        var processed = ModelProcessor.Process(ModelFixtures.Model(200, ["cover"], [(2048, 64)]), ModelKind.PerGame, null, Scratch);

        Assert.NotNull(processed.Glb);
        Assert.Contains(processed.Report.Warnings, w => w.Contains("can't scale them down", StringComparison.Ordinal));
    }

    [Fact]
    public void An_in_budget_model_passes_through_unchanged_and_a_rejected_one_gives_no_bytes()
    {
        var model = ModelFixtures.Model(200);

        Assert.Equal(model, ModelProcessor.Process(model, ModelKind.PerGame, null, Scratch).Glb);
        var rejected = ModelProcessor.Process(ModelFixtures.Model(20_000), ModelKind.PerGame, null, Scratch);
        Assert.Null(rejected.Glb);
        Assert.False(rejected.Report.Accepted);
    }

    // ---- OBJ ---------------------------------------------------------------------------------------------

    private const string Obj = """
        # A quad showing the cover, and a triangle of case, with negative indices on the triangle.
        mtllib Game Model.mtl
        v -0.5 0 0
        v 0.5 0 0
        v 0.5 1 0
        v -0.5 1 0
        v 0 0 -0.2
        vt 0 0
        vt 1 0
        vt 1 1
        vt 0 1
        vn 0 0 1
        usemtl cover
        f 1/1/1 2/2/1 3/3/1 4/4/1
        usemtl case
        s 1
        f -5 -3 -1
        """;

    private const string Mtl = """
        newmtl cover
        Kd 0.5 0.5 0.5
        map_Kd -s 1 1 1 textures\art.png
        newmtl case
        Kd 0.1 0.2 0.3
        Ns 250
        """;

    private byte[] Zip(params (string Name, byte[] Content)[] entries)
    {
        using var memory = new MemoryStream();
        using (var zip = new ZipArchive(memory, ZipArchiveMode.Create, leaveOpen: true))
        {
            foreach (var (name, content) in entries)
            {
                using var stream = zip.CreateEntry(name).Open();
                stream.Write(content);
            }
        }

        return memory.ToArray();
    }

    private static byte[] Text(string text) => Encoding.UTF8.GetBytes(text);

    [Fact]
    public void An_obj_zip_becomes_a_glb_with_its_materials_named_and_textures_embedded()
    {
        var zip = Zip(("model/Game Model.obj", Text(Obj)), ("model/Game Model.mtl", Text(Mtl)),
            ("model/textures/art.png", TestImages.RealPng(16, 16, (x, y) => (255, 0, 0, 255))));

        var converted = ObjConverter.FromZip(new MemoryStream(zip), null, Scratch);

        Assert.Empty(converted.Errors);
        Assert.Empty(converted.Warnings);
        var report = ModelInspector.Inspect(converted.Glb!, ModelKind.PerGame).Report;
        Assert.True(report.Accepted, string.Join("; ", report.Errors));
        Assert.Equal((3, 2, 1), (report.Triangles, report.Materials, report.Textures));
        Assert.Equal(["cover"], report.Slots);

        Assert.True(GlbFile.TryRead(converted.Glb, out var file, out _));
        var materials = (JsonArray)file!.Json["materials"]!;
        Assert.Equal(["cover", "case"], materials.Select(m => (string)m!["name"]!));
        var cover = materials[0]!["pbrMetallicRoughness"]!;
        Assert.Equal(1.0, (double)cover["baseColorFactor"]![0]!, 3);       // a slot is white (A7)
        Assert.NotNull(cover["baseColorTexture"]);
        var caseColour = materials[1]!["pbrMetallicRoughness"]!;
        Assert.Equal(0.3, (double)caseColour["baseColorFactor"]![2]!, 3);
        Assert.InRange((double)caseColour["roughnessFactor"]!, 0.05, 0.15); // from Ns 250
        Assert.Equal((0, -1), (ModelInspector.BaseColourImage(file, 0), ModelInspector.BaseColourImage(file, 1)));
    }

    [Fact]
    public void Obj_texture_coordinates_are_flipped_to_the_top_left_origin()
    {
        var zip = Zip(("a.obj", Text("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n")));

        var converted = ObjConverter.FromZip(new MemoryStream(zip), null, Scratch);

        Assert.True(GlbFile.TryRead(converted.Glb, out var file, out _));
        var uvView = ModelInspector.ViewBytes(file!, 2).ToArray();
        Assert.Equal(1f, BitConverter.ToSingle(uvView, 4));   // the first corner's v: 0 in OBJ, 1 in glTF
        Assert.Contains("default", ((JsonArray)file!.Json["materials"]!).Select(m => (string)m!["name"]!));
    }

    [Fact]
    public void A_zip_with_no_model_two_models_or_no_faces_is_refused_with_a_reason()
    {
        Assert.Contains("no .obj model", Assert.Single(ObjConverter.FromZip(new MemoryStream(Zip(("readme.txt", Text("hi")))), null, Scratch).Errors), StringComparison.Ordinal);
        Assert.Contains("2 .obj files", Assert.Single(ObjConverter.FromZip(new MemoryStream(Zip(("a.obj", Text(Obj)), ("b.obj", Text(Obj)))), null, Scratch).Errors), StringComparison.Ordinal);
        Assert.Contains("has no faces", Assert.Single(ObjConverter.FromZip(new MemoryStream(Zip(("a.obj", Text("v 0 0 0\n")))), null, Scratch).Errors), StringComparison.Ordinal);
        Assert.Contains("isn't a zip", Assert.Single(ObjConverter.FromZip(new MemoryStream(Text("not a zip")), null, Scratch).Errors), StringComparison.Ordinal);
    }

    [Fact]
    public void A_missing_material_file_or_texture_is_a_warning_not_a_failure()
    {
        var converted = ObjConverter.FromZip(new MemoryStream(Zip(("m.obj", Text(Obj)))), null, Scratch);

        Assert.NotNull(converted.Glb);
        Assert.Contains(converted.Warnings, w => w.Contains("'Game Model.mtl' isn't there", StringComparison.Ordinal));
    }

    [Fact]
    public void A_zip_holding_a_glb_is_passed_through_and_a_bare_obj_reads_its_neighbours()
    {
        var glb = ModelFixtures.Model(20);
        Assert.Equal(glb, ObjConverter.FromZip(new MemoryStream(Zip(("model.glb", glb))), null, Scratch).Glb);

        _dir.File("obj/Game Model.obj", Obj);
        _dir.File("obj/Game Model.mtl", Mtl);
        File.WriteAllBytes(_dir.File("obj/textures/art.png"), TestImages.RealPng(8, 8, (x, y) => (0, 255, 0, 255)));
        var converted = ObjConverter.FromFile(_dir.Combine("obj", "Game Model.obj"), null, Scratch);
        Assert.Empty(converted.Warnings);
        Assert.Equal(1, ModelInspector.Inspect(converted.Glb!, ModelKind.PerGame).Report.Textures);
    }

    // A PS2 save icon as ps2iodb exports it: the OBJ is the first frame turned about Z (the PS2's y points down).
    private const string IconObj = "v 0 0 0\nv -1 0 0\nv 0 -1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n";

    // Three frames over 20 frames at half speed: the second moves the first vertex, the third is the first again.
    private const string IconAnim = """
        { "version": 3, "frameLength": 20, "animSpeed": 0.5, "playOffset": 0, "frames": [
          { "shapeId": 0, "keys": [{ "time": 0, "value": 1 }, { "time": 10, "value": 0 }], "vertexData": [0, 0, 0, 1, 0, 0, 0, 1, 0] },
          { "shapeId": 1, "keys": [{ "time": 0, "value": 0 }, { "time": 10, "value": 1 }, { "time": 15, "value": 0 }], "vertexData": [0, 0, 2, 1, 0, 0, 0, 1, 0] },
          { "shapeId": 2, "keys": [{ "time": 10, "value": 0 }, { "time": 15, "value": 1 }], "vertexData": [0, 0, 0, 1, 0, 0, 0, 1, 0] }
        ] }
        """;

    [Fact]
    public void A_ps2_icons_shape_animation_becomes_morph_targets_and_a_focused_clip()
    {
        var converted = ObjConverter.FromZip(new MemoryStream(Zip(("ICON.ICO.obj", Text(IconObj)), ("ICON.ICO.anim", Text(IconAnim)))), null, Scratch);

        Assert.Empty(converted.Warnings);
        var report = ModelInspector.Inspect(converted.Glb!, ModelKind.PerGame).Report;
        Assert.True(report.Accepted, string.Join("; ", report.Errors));
        Assert.Equal(["focused"], report.Clips);
        Assert.Equal(1, report.MorphTargets);    // the third frame is the first's shape, so it needs no target

        Assert.True(GlbFile.TryRead(converted.Glb, out var file, out _));
        var json = file!.Json;
        var target = (int)json["meshes"]![0]!["primitives"]![0]!["targets"]![0]!["POSITION"]!;
        var offsets = Floats(file, target);
        Assert.Equal([0f, 0, 2, 0, 0, 0, 0, 0, 0], offsets);    // z is kept when x and y are turned

        var sampler = json["animations"]![0]!["samplers"]![0]!;
        Assert.Equal("weights", (string)json["animations"]![0]!["channels"]![0]!["target"]!["path"]!);
        Assert.Equal([0f, 1f / 3, 0.5f, 2f / 3], Floats(file, (int)sampler["input"]!));    // frames at 30 Hz (60 at half speed)
        Assert.Equal([0f, 1, 0, 0], Floats(file, (int)sampler["output"]!));

        static float[] Floats(GlbFile file, int accessor)
        {
            var view = (int)file.Json["accessors"]![accessor]!["bufferView"]!;
            var bytes = ModelInspector.ViewBytes(file, view).ToArray();
            return [.. Enumerable.Range(0, bytes.Length / 4).Select(i => BitConverter.ToSingle(bytes, i * 4))];
        }
    }

    [Fact]
    public void An_animation_that_doesnt_fit_the_obj_is_left_out_with_a_warning()
    {
        string[] anims =
        [
            IconAnim.Replace("\"time\": 10, \"value\": 0 }], \"vertexData\": [0, 0, 0", "\"time\": 10, \"value\": 0 }], \"vertexData\": [0, 0, 5", StringComparison.Ordinal),
            IconAnim.Replace("[0, 0, 2, 1, 0, 0, 0, 1, 0]", "[0, 0, 2, 1, 0, 0]", StringComparison.Ordinal),
            "{ not json",
        ];
        string[] reasons = ["doesn't start from the model's shape", "has 2 vertices a frame, but the model has 3", "couldn't be read"];

        for (var i = 0; i < anims.Length; i++)
        {
            var converted = ObjConverter.FromZip(new MemoryStream(Zip(("ICON.ICO.obj", Text(IconObj)), ("ICON.ICO.anim", Text(anims[i])))), null, Scratch);

            Assert.Contains(converted.Warnings, w => w.Contains(reasons[i], StringComparison.Ordinal) && w.EndsWith("so the model doesn't animate", StringComparison.Ordinal));
            var report = ModelInspector.Inspect(converted.Glb!, ModelKind.PerGame).Report;
            Assert.True(report.Accepted);
            Assert.Empty(report.Clips);
        }
    }

    // ---- Cache ------------------------------------------------------------------------------------------

    [Fact]
    public void The_cache_processes_a_model_once_and_again_when_its_file_changes()
    {
        var source = ModelFixtures.Write(_dir, "config/models/games/ps2/Game.iso.glb", ModelFixtures.Model(100));
        var log = new ModelLog(_dir.Combine("data"));
        var cache = new ModelCache(_dir.Combine("cache"), null, log);

        var first = cache.Get(source, ModelKind.PerGame, "your Game.glb");
        var second = cache.Get(source, ModelKind.PerGame);

        Assert.False(first.FromCache);
        Assert.True(second.FromCache);
        Assert.Equal(first.Path, second.Path);
        Assert.True(File.Exists(first.Path));
        Assert.Contains(ModelLog.ReadRecent(_dir.Combine("data")), l => l.Contains("your Game.glb: accepted as a per-game model", StringComparison.Ordinal));

        ModelFixtures.Write(_dir, "config/models/games/ps2/Game.iso.glb", ModelFixtures.Model(200), new DateTime(2021, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        var changed = cache.Get(source, ModelKind.PerGame);

        Assert.False(changed.FromCache);
        Assert.Equal(200, changed.Report.Triangles);
        Assert.False(File.Exists(first.Path));                                   // the stale entry went
        Assert.Equal(2, Directory.GetFiles(cache.Folder).Length);                // the model and its report
    }

    [Fact]
    public void A_rejected_model_is_remembered_and_logged_once()
    {
        var source = ModelFixtures.Write(_dir, "config/models/templates/ps2.glb", ModelFixtures.Model(5_000));
        var cache = new ModelCache(_dir.Combine("cache"), null, new ModelLog(_dir.Combine("data")));

        var first = cache.Get(source, ModelKind.GameTemplate);
        var second = cache.Get(source, ModelKind.GameTemplate);

        Assert.Null(first.Path);
        Assert.False(first.Report.Accepted);
        Assert.True(second.FromCache);
        Assert.Null(second.Path);
        var errors = ModelLog.ReadRecent(_dir.Combine("data")).Where(l => l.Contains(" error: ", StringComparison.Ordinal)).ToList();
        Assert.Equal(2, errors.Count);                                           // the reason, and the summary with what happens next
        Assert.Contains("The next model in line is used instead", errors[1], StringComparison.Ordinal);
    }

    [Fact]
    public void The_same_file_has_separate_entries_per_budget_and_forget_removes_them()
    {
        var source = ModelFixtures.Write(_dir, "config/models/x.glb", ModelFixtures.Model(3_000));
        var cache = new ModelCache(_dir.Combine("cache"), null, null);

        Assert.Single(cache.Get(source, ModelKind.GameTemplate).Report.Warnings);
        Assert.Empty(cache.Get(source, ModelKind.PerGame).Report.Warnings);
        cache.Forget(source);

        Assert.Empty(Directory.GetFiles(cache.Folder));
        Assert.False(cache.Get(_dir.Combine("config", "missing.glb"), ModelKind.PerGame).Report.Accepted);
    }

    // ---- Log --------------------------------------------------------------------------------------------

    [Fact]
    public void The_model_log_keeps_about_a_megabyte_and_reads_back_its_last_lines()
    {
        var log = new ModelLog(_dir.Combine("data"), new ManualClock(new DateTimeOffset(2026, 9, 30, 12, 0, 0, TimeSpan.Zero)));
        var line = new string('x', 1000);
        for (var i = 0; i < 1100; i++)
        {
            log.Write(LogLevel.Warning, $"{i} {line}");
        }

        Assert.True(new FileInfo(log.Path).Length < ModelLog.MaxBytes);
        Assert.True(File.Exists(Path.Combine(_dir.Combine("data"), "logs", ModelLog.PreviousFileName)));
        var recent = ModelLog.ReadRecent(_dir.Combine("data"), 2);
        Assert.Equal(2, recent.Count);
        Assert.StartsWith("2026-09-30", recent[1], StringComparison.Ordinal);
        Assert.Contains(" warning: 1099 ", recent[1], StringComparison.Ordinal);
        Assert.Empty(ModelLog.ReadRecent(_dir.Combine("nowhere")));
    }
}
