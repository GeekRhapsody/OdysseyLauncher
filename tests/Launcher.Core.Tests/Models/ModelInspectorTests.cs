using System.Text.Json.Nodes;
using Launcher.Core.Models;
using Launcher.Core.Tests.Theming;

namespace Launcher.Core.Tests.Models;

public sealed class ModelInspectorTests
{
    private static ModelReport Inspect(byte[] model, ModelKind kind = ModelKind.PerGame) => ModelInspector.Inspect(model, kind).Report;

    [Fact]
    public void An_in_budget_model_is_accepted_with_nothing_to_say()
    {
        var report = Inspect(ModelFixtures.Model(1_000, ["cover", "case"], [(512, 512)]));

        Assert.True(report.Accepted, string.Join("; ", report.Errors));
        Assert.Empty(report.Warnings);
        Assert.Equal((1_000, 2, 1, 512), (report.Triangles, report.Materials, report.Textures, report.LargestTextureSide));
        Assert.Equal(["cover"], report.Slots);
        Assert.Equal(1f, report.Size[0], 3);
    }

    [Fact]
    public void An_over_budget_model_is_accepted_with_a_warning()
    {
        var report = Inspect(ModelFixtures.Model(6_000));

        Assert.True(report.Accepted);
        var warning = Assert.Single(report.Warnings);
        Assert.Contains("6,000 triangles, over the 5,000 a per-game model should have", warning, StringComparison.Ordinal);
    }

    [Fact]
    public void A_model_more_than_twice_over_a_budget_is_rejected()
    {
        var triangles = Inspect(ModelFixtures.Model(10_002));
        var materials = Inspect(ModelFixtures.Model(100, ["cover", "a", "b", "c", "d", "e", "f", "g", "h"]));

        Assert.False(triangles.Accepted);
        Assert.Contains("10,002 triangles, more than twice the 5,000 a per-game model may have", Assert.Single(triangles.Errors), StringComparison.Ordinal);
        Assert.False(materials.Accepted);
        Assert.Contains("9 materials, more than twice the 4", Assert.Single(materials.Errors), StringComparison.Ordinal);
    }

    [Fact]
    public void Budgets_depend_on_what_the_model_is_for()
    {
        var model = ModelFixtures.Model(3_000);

        Assert.Empty(Inspect(model, ModelKind.PerGame).Warnings);
        Assert.Contains("3,000 triangles, over the 2,000 a game template", Assert.Single(Inspect(model, ModelKind.GameTemplate).Warnings), StringComparison.Ordinal);
        Assert.Empty(Inspect(model, ModelKind.SystemModel).Warnings);
    }

    [Fact]
    public void A_texture_over_the_budgets_side_is_noted_for_scaling_not_rejected()
    {
        var report = Inspect(ModelFixtures.Model(100, ["cover", "case"], [(64, 64), (2048, 512)]));

        Assert.True(report.Accepted);
        Assert.Equal(2048, report.LargestTextureSide);
        Assert.Contains(report.Notes, n => n.Contains("scaled down", StringComparison.Ordinal));
    }

    [Fact]
    public void Only_base_colour_textures_count_since_other_maps_arent_drawn()
    {
        // Two base colour images, plus eight more on maps the app doesn't draw: ten images, five times the budget.
        var model = ModelFixtures.Edited(json =>
        {
            var materials = (JsonArray)json["materials"]!;
            var next = 2;
            foreach (var material in materials.Cast<JsonObject>())
            {
                var pbr = (JsonObject)material["pbrMetallicRoughness"]!;
                pbr["metallicRoughnessTexture"] = new JsonObject { ["index"] = next++ };
                foreach (var map in (string[])["normalTexture", "occlusionTexture", "emissiveTexture"])
                {
                    material[map] = new JsonObject { ["index"] = next++ };
                }
            }
        }, ModelFixtures.Model(100, ["cover", "case"], [.. Enumerable.Repeat((8, 8), 9), (2048, 2048)]));

        var report = Inspect(model);

        Assert.True(report.Accepted, string.Join("; ", report.Errors));
        Assert.Equal((2, 8), (report.Textures, report.LargestTextureSide));
        Assert.Empty(report.Warnings);
        Assert.Contains(report.Notes, n => n.Contains("emissiveTexture, metallicRoughnessTexture, normalTexture, occlusionTexture maps aren't drawn yet", StringComparison.Ordinal));
    }

    [Fact]
    public void A_model_needs_no_media_slot()
    {
        var report = Inspect(ModelFixtures.Model(100, ["body", "stand"]));

        Assert.True(report.Accepted);
        Assert.Empty(report.Slots);
        Assert.Contains(report.Notes, n => n.Contains("no media slot", StringComparison.Ordinal));
    }

    [Fact]
    public void A_model_in_the_wrong_units_is_accepted_with_a_warning()
    {
        var report = Inspect(ModelFixtures.Model(100, size: 100));

        Assert.True(report.Accepted);
        Assert.Contains("wrong units?", Assert.Single(report.Warnings), StringComparison.Ordinal);
    }

    public static TheoryData<string, byte[], string> BrokenFiles() => new()
    {
        { "not a glb", "just text"u8.ToArray(), "isn't a glTF binary" },
        { "cut short", ModelFixtures.Model(12)[..40], "cut short" },
        { "glTF 1", SetVersion(ModelFixtures.Model(12), 1), "isn't glTF 2.0" },
        { "no asset version", ModelFixtures.Edited(j => j.Remove("asset")), "doesn't say it's glTF 2.0" },
        { "accessor past its view", ModelFixtures.Edited(j => Accessor(j, 0)["count"] = 100_000), "accessor 0 runs past the end of its buffer view" },
        { "view past the buffer", ModelFixtures.Edited(j => ((JsonObject)((JsonArray)j["bufferViews"]!)[0]!)["byteLength"] = 1 << 24), "runs past the end of the binary chunk" },
        { "index out of range", ModelFixtures.Edited(j => { foreach (var i in (int[])[0, 1, 2]) { Accessor(j, i)["count"] = 3; } }), "has an index 3, but only 3 vertices" },
        { "missing accessor", ModelFixtures.Edited(j => Primitive(j)["indices"] = 99), "names accessor 99, which doesn't exist" },
        { "missing material", ModelFixtures.Edited(j => Primitive(j)["material"] = 7), "names material 7" },
        { "missing normal map", ModelFixtures.Edited(j => ((JsonObject)((JsonArray)j["materials"]!)[0]!)["normalTexture"] = new JsonObject { ["index"] = 5 }), "names texture 5" },
        { "cycle", ModelFixtures.Edited(j => ((JsonObject)((JsonArray)j["nodes"]!)[1]!)["children"] = new JsonArray(0)), "loop" },
        { "external buffer", ModelFixtures.Edited(j => ((JsonObject)((JsonArray)j["buffers"]!)[0]!)["uri"] = "model.bin"), "everything must be embedded" },
        { "required extension", ModelFixtures.Edited(j => j["extensionsRequired"] = new JsonArray("KHR_draco_mesh_compression")), "KHR_draco_mesh_compression" },
        { "no triangles", ModelFixtures.Edited(j => { foreach (var p in Primitives(j)) { p["mode"] = 1; } }), "no triangles" },
        { "wrong value type", ModelFixtures.Edited(j => ((JsonObject)((JsonArray)j["nodes"]!)[1]!)["matrix"] = new JsonArray([.. Enumerable.Repeat<JsonNode?>("x", 16).Select(n => n?.DeepClone())])), "a value the launcher can't read" },
        { "image not png", ModelFixtures.Edited(j => ((JsonObject)((JsonArray)j["images"]!)[0]!)["bufferView"] = 1, ModelFixtures.Model(12, ["cover"], [(8, 8)])), "isn't a PNG or JPEG" },
    };

    [Theory]
    [MemberData(nameof(BrokenFiles))]
    public void A_broken_file_is_rejected_with_a_reason_and_never_throws(string name, byte[] model, string reason)
    {
        var report = Inspect(model);

        Assert.False(report.Accepted, name);
        Assert.Contains(report.Errors, e => e.Contains(reason, StringComparison.Ordinal));
    }

    [Theory]
    [InlineData("idle", ModelClip.Idle)]
    [InlineData("Idle.001", ModelClip.Idle)]
    [InlineData("FOCUSED", ModelClip.Focused)]
    [InlineData("Armature|launch", ModelClip.Launch)]
    [InlineData("launch.12", null)]
    [InlineData("walk", null)]
    [InlineData("", null)]
    public void Clip_names_match_ignoring_case_a_Blender_suffix_and_an_object_prefix(string name, ModelClip? clip) =>
        Assert.Equal(clip, ModelClips.OfName(name));

    [Fact]
    public void The_clips_the_launcher_plays_are_found_and_others_noted()
    {
        var report = Inspect(ModelFixtures.Model(100, clips: ["Idle.001", "Armature|launch", "Walk"]));

        Assert.True(report.Accepted);
        Assert.Equal(["idle", "launch"], report.Clips);
        Assert.True(report.HasClip(ModelClip.Launch));
        Assert.False(report.HasClip(ModelClip.Focused));
        Assert.Contains(report.Notes, n => n.Contains("'Walk' isn't idle, focused or launch", StringComparison.Ordinal));
    }

    public static TheoryData<string, string, ModelKind> CommittedModels()
    {
        var data = new TheoryData<string, string, ModelKind>();
        foreach (var folder in (string[])[ThemeFixtures.BuiltInFolder, ThemeFixtures.SlotShowcaseFolder, ThemeFixtures.RetroTvFolder])
        {
            var theme = ThemeFixtures.Load(folder);
            foreach (var template in theme.Templates.Values)
            {
                data.Add(folder, template.Model, ModelKind.GameTemplate);
            }

            foreach (var model in theme.Systems.Values.Select(s => s.Model).Append(theme.Defaults.SystemModel).OfType<string>().Distinct())
            {
                data.Add(folder, model, ModelKind.SystemModel);
            }
        }

        return data;
    }

    [Theory]
    [MemberData(nameof(CommittedModels))]
    public void Every_committed_model_passes_the_inspector_in_budget(string folder, string model, ModelKind kind)
    {
        var report = Inspect(File.ReadAllBytes(Path.Combine(folder, model.Replace('/', Path.DirectorySeparatorChar))), kind);

        Assert.True(report.Accepted, $"{model}: {string.Join("; ", report.Errors)}");
        Assert.Empty(report.Warnings);
    }

    private static byte[] SetVersion(byte[] model, uint version)
    {
        var copy = model.ToArray();
        System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(copy.AsSpan(4), version);
        return copy;
    }

    private static JsonObject Accessor(JsonObject json, int index) => (JsonObject)((JsonArray)json["accessors"]!)[index]!;

    private static IEnumerable<JsonObject> Primitives(JsonObject json) =>
        ((JsonArray)json["meshes"]!).SelectMany(m => (JsonArray)((JsonObject)m!)["primitives"]!).Cast<JsonObject>();

    private static JsonObject Primitive(JsonObject json) =>
        (JsonObject)((JsonArray)((JsonObject)((JsonArray)json["meshes"]!)[0]!)["primitives"]!)[0]!;
}
