using System;
using System.Collections.Generic;
using Godot;
using Launcher.Core.Theming;

namespace Launcher.App.Models;

/// <summary>
/// A model merged into one surface for the item shader, first on the CPU (any thread), then as an
/// <see cref="ArrayMesh"/> (<see cref="Build"/>, main thread).
/// </summary>
public sealed class ConvertedModel
{
    internal readonly List<Vector3> Vertices = [];
    internal readonly List<Vector3> Normals = [];
    internal readonly List<Vector2> Uvs = [];
    internal readonly List<Vector2> Codes = [];
    internal readonly List<Color> Colours = [];
    internal readonly List<int> Indices = [];

    /// <summary>Each slot face's width over its height, by slot number; 0 where the model has no such material.</summary>
    public float[] SlotAspects { get; } = new float[MediaSlots.Count];

    /// <summary>The authored textures its faces sample, by the index in their face code.</summary>
    public Texture2D?[] Authored { get; } = new Texture2D?[ItemTemplate.MaxAuthoredTextures];

    public List<string> Warnings { get; } = [];

    public Vector3 Size { get; private set; }

    public ArrayMesh? Mesh { get; private set; }

    /// <summary>
    /// Main thread: fits the model to the spec (A7: standing on y = 0, centred, the largest side 1 m, so the grid can
    /// size every template alike) and uploads it.
    /// </summary>
    public void Build(string name)
    {
        if (Mesh is not null)
        {
            return;
        }

        var box = new Aabb(Vertices[0], Vector3.Zero);
        foreach (var vertex in Vertices)
        {
            box = box.Expand(vertex);
        }

        var largest = Mathf.Max(box.Size.X, Mathf.Max(box.Size.Y, box.Size.Z));
        var scale = largest > 0 ? 1 / largest : 1;
        if (scale is > 10 or < 0.1f)
        {
            Warnings.Add(FormattableString.Invariant($"its largest side is {largest:0.###} m, not about 1 m (wrong units?); it's scaled to fit"));
        }

        var offset = new Vector3(box.Position.X + box.Size.X / 2, box.Position.Y, box.Position.Z + box.Size.Z / 2);
        var vertices = new Vector3[Vertices.Count];
        for (var i = 0; i < vertices.Length; i++)
        {
            vertices[i] = (Vertices[i] - offset) * scale;
        }

        var arrays = new Godot.Collections.Array();
        arrays.Resize((int)Godot.Mesh.ArrayType.Max);
        arrays[(int)Godot.Mesh.ArrayType.Vertex] = vertices;
        arrays[(int)Godot.Mesh.ArrayType.Normal] = Normals.ToArray();
        arrays[(int)Godot.Mesh.ArrayType.TexUV] = Uvs.ToArray();
        arrays[(int)Godot.Mesh.ArrayType.TexUV2] = Codes.ToArray();
        arrays[(int)Godot.Mesh.ArrayType.Color] = Colours.ToArray();
        arrays[(int)Godot.Mesh.ArrayType.Index] = Indices.ToArray();
        Mesh = new ArrayMesh { ResourceName = name };
        Mesh.AddSurfaceFromArrays(Godot.Mesh.PrimitiveType.Triangles, arrays);
        Size = box.Size * scale;
    }
}

/// <summary>
/// Remaps a model onto the item shader (A7). A material named after a media kind is a slot (<see cref="MediaSlots"/>);
/// every other material is plain. Base colour (linear), roughness and the base colour texture are kept; anything
/// else is ignored. Per vertex: COLOR = (base colour, roughness); UV2 = (face code, face aspect), where the face code
/// is (slot + 1) × 8 + (authored texture + 1), with 0 for none in either part (item.gdshader).
/// </summary>
public static class ModelConverter
{
    /// <summary>
    /// A <c>.glb</c> parsed by <see cref="GltfDocument"/>: its CPU-side meshes (<see cref="ImporterMesh"/>), so this
    /// runs on a worker thread and reads nothing back from the renderer.
    /// </summary>
    public static ConvertedModel? FromGltf(GltfState state, out string? error)
    {
        var model = new ConvertedModel();
        var nodes = state.GetNodes();
        var meshes = state.GetMeshes();
        for (var i = 0; i < nodes.Count; i++)
        {
            var node = nodes[i];
            if (node.Mesh < 0 || node.Mesh >= meshes.Count || meshes[node.Mesh].Mesh is not { } mesh)
            {
                continue;
            }

            var transform = node.Xform;
            for (var parent = node.Parent; parent >= 0 && parent < nodes.Count; parent = nodes[parent].Parent)
            {
                transform = nodes[parent].Xform * transform;
            }

            var instanceMaterials = meshes[node.Mesh].InstanceMaterials;
            for (var surface = 0; surface < mesh.GetSurfaceCount(); surface++)
            {
                if (mesh.GetSurfacePrimitiveType(surface) != Mesh.PrimitiveType.Triangles)
                {
                    continue;
                }

                var material = mesh.GetSurfaceMaterial(surface) ?? (surface < instanceMaterials.Count ? instanceMaterials[surface] : null);
                AddSurface(model, transform, mesh.GetSurfaceArrays(surface), material);
            }
        }

        return Finish(model, out error);
    }

    private static ConvertedModel? Finish(ConvertedModel model, out string? error)
    {
        if (model.Vertices.Count == 0)
        {
            error = "it has no triangle mesh";
            return null;
        }

        error = null;
        return model;
    }

    private static void AddSurface(ConvertedModel model, Transform3D toRoot, Godot.Collections.Array arrays, Material? material)
    {
        var positions = arrays[(int)Mesh.ArrayType.Vertex].AsVector3Array();
        var normals = arrays[(int)Mesh.ArrayType.Normal].AsVector3Array();
        for (var v = 0; v < positions.Length; v++)
        {
            positions[v] = toRoot * positions[v];
        }

        for (var v = 0; v < normals.Length; v++)
        {
            normals[v] = (toRoot.Basis * normals[v]).Normalized();
        }

        var uvs = arrays[(int)Mesh.ArrayType.TexUV].AsVector2Array();
        var indices = arrays[(int)Mesh.ArrayType.Index].AsInt32Array();
        var slot = MediaSlots.OfMaterial(material?.ResourceName);
        var (colour, roughness, texture) = material is BaseMaterial3D standard
            ? (standard.AlbedoColor.SrgbToLinear(), standard.Roughness, standard.AlbedoTexture)
            : (Colors.White, 0.5f, null);

        var tex = AuthoredIndex(model, texture, material?.ResourceName);
        var aspect = 0f;
        if (slot >= 0)
        {
            aspect = AspectOf(material, positions, normals);
            if (model.SlotAspects[slot] == 0)
            {
                model.SlotAspects[slot] = aspect;
            }
        }

        var code = new Vector2((slot + 1) * 8 + tex + 1, aspect);
        var first = model.Vertices.Count;
        for (var v = 0; v < positions.Length; v++)
        {
            model.Vertices.Add(positions[v]);
            model.Normals.Add(normals.Length > v ? normals[v] : Vector3.Up);
            model.Uvs.Add(uvs.Length > v ? uvs[v] : Vector2.Zero);
            model.Colours.Add(new Color(colour.R, colour.G, colour.B, roughness));
            model.Codes.Add(code);
        }

        if (indices.Length == 0)
        {
            for (var v = 0; v < positions.Length; v++)
            {
                model.Indices.Add(first + v);
            }
        }
        else
        {
            foreach (var index in indices)
            {
                model.Indices.Add(first + index);
            }
        }
    }

    /// <summary>The authored texture's index (shared by materials using the same texture), or -1.</summary>
    private static int AuthoredIndex(ConvertedModel model, Texture2D? texture, string? material)
    {
        if (texture is null)
        {
            return -1;
        }

        for (var i = 0; i < model.Authored.Length; i++)
        {
            if (model.Authored[i] == texture)
            {
                return i;
            }

            if (model.Authored[i] is null)
            {
                model.Authored[i] = texture;
                return i;
            }
        }

        model.Warnings.Add($"the material '{material}' has a texture, but only {ItemTemplate.MaxAuthoredTextures} textures are supported, so it shows its base colour");
        return -1;
    }

    /// <summary><c>extras.aspect</c> if the material has it, else the slot mesh's bounds across its facing (A7).</summary>
    private static float AspectOf(Material? material, Vector3[] positions, Vector3[] normals)
    {
        if (material is not null && material.HasMeta("extras"))
        {
            var extras = material.GetMeta("extras").AsGodotDictionary();
            if (extras.TryGetValue("aspect", out var value) && value.AsSingle() > 0)
            {
                return value.AsSingle();
            }
        }

        var box = new Aabb(positions.Length > 0 ? positions[0] : Vector3.Zero, Vector3.Zero);
        var facing = Vector3.Zero;
        for (var i = 0; i < positions.Length; i++)
        {
            box = box.Expand(positions[i]);
            if (i < normals.Length)
            {
                facing += normals[i];
            }
        }

        // Height is along Y; width is whichever horizontal axis the face doesn't point along.
        var width = Mathf.Abs(facing.X) > Mathf.Abs(facing.Z) ? box.Size.Z : box.Size.X;
        return box.Size.Y > 0 ? width / box.Size.Y : 1;
    }

}
