using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// A flat card (A7): one media slot on its front and plain dark <c>case</c> on its back, both in the plane z = 0, so it
/// has no thickness. Base theme templates <c>flat_cover</c> and <c>flat_screenshot</c> use it, each shaped by its own
/// art. With no thickness, the depth a <c>shape = "media"</c> template takes from a game's spine moves nothing (the item
/// shader moves a vertex by the sign of its z), so a flat card stays flat. Every vertex is a corner, off the centre
/// planes x = 0 and half the height, as the reshaping needs.
/// </summary>
public static class FlatBuilder
{
    private static readonly Color Back = new("#26262A");

    /// <param name="slot">The front's material, a media kind.</param>
    /// <param name="aspect">The front's width over its height; the larger side is 1 m.</param>
    /// <param name="authored">The slot's own texture (its last fallback), or null for plain white.</param>
    public static ArrayMesh Build(string slot, float aspect, Texture2D? authored, out int triangles)
    {
        var width = aspect >= 1 ? 1 : aspect;
        var height = aspect >= 1 ? 1 / aspect : 1;
        var left = -width / 2;
        var right = width / 2;

        var mesh = new ArrayMesh();

        // The front faces +Z: Godot's front faces wind clockwise seen from outside. UVs run 0..1 left to right and top
        // to bottom, upright.
        AddQuad(mesh, Vector3.Back,
            [new(left, height, 0), new(right, height, 0), new(right, 0, 0), new(left, 0, 0)],
            [new(0, 0), new(1, 0), new(1, 1), new(0, 1)]);
        // Fully matte, so it reads as the image itself rather than a print under a glossy sleeve.
        var front = new StandardMaterial3D { ResourceName = slot, AlbedoColor = Colors.White, AlbedoTexture = authored, Roughness = 1, Metallic = 0 };
        front.SetMeta("extras", new Godot.Collections.Dictionary { ["aspect"] = aspect });
        mesh.SurfaceSetMaterial(0, front);
        mesh.SurfaceSetName(0, slot);

        // The back faces -Z, the same corners seen from behind.
        AddQuad(mesh, Vector3.Forward,
            [new(right, height, 0), new(left, height, 0), new(left, 0, 0), new(right, 0, 0)],
            [new(0, 0), new(1, 0), new(1, 1), new(0, 1)]);
        mesh.SurfaceSetMaterial(1, new StandardMaterial3D { ResourceName = "case", AlbedoColor = Back, Roughness = 0.85f, Metallic = 0 });
        mesh.SurfaceSetName(1, "case");

        triangles = 4;
        return mesh;
    }

    /// <summary>A plain near-black 4:3 texture, for a card with no screenshot.</summary>
    public static Image DarkPanel()
    {
        var image = Image.CreateEmpty(16, 12, false, Image.Format.Rgb8);
        image.Fill(new Color("#0B0B0E"));
        image.GenerateMipmaps();
        return image;
    }

    /// <param name="corners">Top left, top right, bottom right, bottom left, seen from the side <paramref name="normal"/> faces.</param>
    private static void AddQuad(ArrayMesh mesh, Vector3 normal, Vector3[] corners, Vector2[] uvs)
    {
        var arrays = new Godot.Collections.Array();
        arrays.Resize((int)Mesh.ArrayType.Max);
        arrays[(int)Mesh.ArrayType.Vertex] = corners;
        arrays[(int)Mesh.ArrayType.Normal] = new[] { normal, normal, normal, normal };
        arrays[(int)Mesh.ArrayType.TexUV] = uvs;
        arrays[(int)Mesh.ArrayType.Index] = new[] { 0, 1, 2, 0, 2, 3 };
        mesh.AddSurfaceFromArrays(Mesh.PrimitiveType.Triangles, arrays);
    }
}
