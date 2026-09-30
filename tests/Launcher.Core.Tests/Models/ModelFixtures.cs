using System.Numerics;
using System.Text.Json.Nodes;
using Launcher.Core.Models;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Models;

/// <summary>
/// The model fixtures (ROADMAP M6: in budget, over budget and more than 2× over), written as <c>.glb</c> files by
/// <see cref="GltfBuilder"/> rather than committed, since their size is the point: a flat panel of quads with the
/// materials, textures and clips asked for, standing on y = 0, 1 m high.
/// </summary>
internal static class ModelFixtures
{
    public static byte[] Model(int triangles, string[]? materials = null, (int Width, int Height)[]? textures = null, string[]? clips = null, float size = 1)
    {
        materials ??= ["cover", "case"];
        textures ??= [];
        var builder = new GltfBuilder();
        var textureIndex = textures.Select(t => builder.AddImage(TestImages.RealPng(t.Width, t.Height, (x, y) => ((byte)x, (byte)y, 128, 255)), "image/png")).ToArray();
        var materialIndex = new int[materials.Length];
        for (var m = 0; m < materials.Length; m++)
        {
            var slot = Launcher.Core.Theming.MediaSlots.OfMaterial(materials[m]) >= 0;
            materialIndex[m] = builder.AddMaterial(materials[m], slot ? Vector4.One : new Vector4(0.2f, 0.2f, 0.25f, 1),
                texture: m < textureIndex.Length ? textureIndex[m] : -1, aspect: slot ? 0.7f : null);
        }

        // Quads in a square panel; each material gets an equal share of the triangles.
        var quads = (triangles + 1) / 2;
        var side = (int)Math.Ceiling(Math.Sqrt(quads));
        var primitives = new List<GltfPrimitive>();
        var perMaterial = (quads + materials.Length - 1) / materials.Length;
        for (var m = 0; m < materials.Length; m++)
        {
            var positions = new List<Vector3>();
            var uvs = new List<Vector2>();
            var indices = new List<int>();
            for (var q = m * perMaterial; q < Math.Min(quads, (m + 1) * perMaterial); q++)
            {
                var (x, y) = (q % side, q / side);
                var cell = size / side;
                var first = positions.Count;
                positions.AddRange([
                    new Vector3(x * cell - size / 2, y * cell, 0), new Vector3((x + 1) * cell - size / 2, y * cell, 0),
                    new Vector3((x + 1) * cell - size / 2, (y + 1) * cell, 0), new Vector3(x * cell - size / 2, (y + 1) * cell, 0)]);
                uvs.AddRange([new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0), new Vector2(0, 0)]);
                indices.AddRange([first, first + 1, first + 2]);
                if (q * 2 + 1 < triangles)
                {
                    indices.AddRange([first, first + 2, first + 3]);
                }
            }

            if (indices.Count > 0)
            {
                primitives.Add(new GltfPrimitive([.. positions], [.. positions.Select(_ => Vector3.UnitZ)], [.. uvs], [.. indices], materialIndex[m]));
            }
        }

        var mesh = builder.AddMesh("panel", primitives);
        var root = builder.AddNode("root");
        var panel = builder.AddNode("panel", mesh, parent: root);
        foreach (var clip in clips ?? [])
        {
            builder.AddAnimation(clip, [new GltfChannel(panel, "rotation", [0, 1], [0, 0, 0, 1, 0, 0.3826834f, 0, 0.9238795f])]);
        }

        return builder.ToGlb();
    }

    /// <summary>A good model whose JSON is changed by <paramref name="edit"/>: for the broken-file cases.</summary>
    public static byte[] Edited(Action<JsonObject> edit, byte[]? model = null)
    {
        Assert.True(GlbFile.TryRead(model ?? Model(12), out var file, out _));
        edit(file!.Json);
        return file.Write();
    }

    /// <summary>Writes a fixture into <paramref name="dir"/> and returns its path.</summary>
    public static string Write(TempDir dir, string relativePath, byte[] model, DateTime? modifiedUtc = null)
    {
        var path = dir.Combine(relativePath.Split('/'));
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllBytes(path, model);
        File.SetLastWriteTimeUtc(path, modifiedUtc ?? new DateTime(2020, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        return path;
    }
}
