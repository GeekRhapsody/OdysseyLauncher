using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Models;

/// <summary>What each part of a model shows; the item shader's face ids (item.gdshader).</summary>
public enum Face
{
    Cover = 0,
    Back = 1,
    Spine = 2,
    Case = 3,
    Label = 4,
}

/// <summary>
/// A model remapped onto the launcher's fixed item shader (A7): every surface merged into one, so a MultiMesh of it
/// is a single draw call. Per vertex, COLOR carries the material's base colour (linear) and roughness, and UV2 the
/// face id and the face's aspect ratio.
/// </summary>
/// <param name="Size">The rest-pose bounding box: the model stands on y = 0, centred on x and z.</param>
public sealed record ItemMesh(string Id, ArrayMesh Mesh, Vector3 Size, float CoverAspect);

/// <summary>
/// The built-in models: the box templates (A7) and the generic system model. Loaded with Godot's threaded loader,
/// so the main thread doesn't read the files, then converted to <see cref="ItemMesh"/>es on the main thread (a few
/// hundred vertices each).
/// </summary>
public sealed class TemplateLibrary
{
    public const string GenericSystemId = "generic";

    private readonly List<(string Id, string Path)> _pending = [];
    private readonly Dictionary<string, ItemMesh> _meshes = new(StringComparer.Ordinal);

    /// <summary>Starts loading every built-in model.</summary>
    public void Request(IEnumerable<string> templateIds)
    {
        foreach (var id in templateIds)
        {
            Queue(id, $"res://assets/models/templates/{id}.glb");
        }

        Queue(GenericSystemId, $"res://assets/models/systems/{GenericSystemId}.glb");
    }

    private void Queue(string id, string path)
    {
        var error = ResourceLoader.LoadThreadedRequest(path, "PackedScene", useSubThreads: false);
        if (error != Error.Ok)
        {
            GD.PushError($"Models: couldn't start loading {path}: {error}");
            return;
        }

        _pending.Add((id, path));
    }

    /// <summary>Main thread, each frame until true: converts whatever has finished loading.</summary>
    public bool Poll()
    {
        for (var i = _pending.Count - 1; i >= 0; i--)
        {
            var (id, path) = _pending[i];
            var status = ResourceLoader.LoadThreadedGetStatus(path);
            if (status == ResourceLoader.ThreadLoadStatus.InProgress)
            {
                continue;
            }

            _pending.RemoveAt(i);
            if (status != ResourceLoader.ThreadLoadStatus.Loaded || ResourceLoader.LoadThreadedGet(path) is not PackedScene scene)
            {
                GD.PushError($"Models: couldn't load {path} ({status}).");
                continue;
            }

            if (Convert(id, scene) is { } mesh)
            {
                _meshes[id] = mesh;
            }
        }

        return _pending.Count == 0;
    }

    /// <summary>The template, or the DVD case if it's missing (it never is for built-ins).</summary>
    public ItemMesh Get(string id) =>
        _meshes.TryGetValue(id, out var mesh) ? mesh : _meshes.TryGetValue("dvd_case", out var fallback) ? fallback : _meshes[GenericSystemId];

    public IEnumerable<ItemMesh> All => _meshes.Values;

    /// <summary>Merges every mesh surface in the scene into one, with the face data the item shader reads.</summary>
    public static ItemMesh? Convert(string id, PackedScene scene)
    {
        var root = scene.Instantiate<Node>();
        try
        {
            var vertices = new List<Vector3>();
            var normals = new List<Vector3>();
            var uvs = new List<Vector2>();
            var colours = new List<Color>();
            var faces = new List<Vector2>();
            var indices = new List<int>();
            var coverAspect = 0f;
            foreach (var instance in MeshInstances(root))
            {
                if (instance.Mesh is not { } mesh)
                {
                    continue;
                }

                var toRoot = RelativeTransform(instance, root);
                for (var surface = 0; surface < mesh.GetSurfaceCount(); surface++)
                {
                    var arrays = mesh.SurfaceGetArrays(surface);
                    var positions = arrays[(int)Mesh.ArrayType.Vertex].AsVector3Array();
                    var surfaceNormals = arrays[(int)Mesh.ArrayType.Normal].AsVector3Array();
                    var surfaceUvs = arrays[(int)Mesh.ArrayType.TexUV].AsVector2Array();
                    var surfaceIndices = arrays[(int)Mesh.ArrayType.Index].AsInt32Array();
                    var material = instance.GetActiveMaterial(surface);
                    var face = FaceOf(material?.ResourceName);
                    var (baseColour, roughness) = material is BaseMaterial3D standard
                        ? (standard.AlbedoColor.SrgbToLinear(), standard.Roughness)
                        : (Colors.White, 0.5f);
                    var aspect = face == Face.Case ? 0 : AspectOf(material, positions, surfaceNormals);
                    if (face is Face.Cover or Face.Label && coverAspect == 0)
                    {
                        coverAspect = aspect;
                    }

                    var first = vertices.Count;
                    for (var v = 0; v < positions.Length; v++)
                    {
                        vertices.Add(toRoot * positions[v]);
                        normals.Add(surfaceNormals.Length > v ? (toRoot.Basis * surfaceNormals[v]).Normalized() : Vector3.Up);
                        uvs.Add(surfaceUvs.Length > v ? surfaceUvs[v] : Vector2.Zero);
                        colours.Add(new Color(baseColour.R, baseColour.G, baseColour.B, roughness));
                        faces.Add(new Vector2((float)face, aspect));
                    }

                    if (surfaceIndices.Length == 0)
                    {
                        for (var v = 0; v < positions.Length; v++)
                        {
                            indices.Add(first + v);
                        }
                    }
                    else
                    {
                        foreach (var index in surfaceIndices)
                        {
                            indices.Add(first + index);
                        }
                    }
                }
            }

            if (vertices.Count == 0)
            {
                GD.PushError($"Models: {id} has no mesh.");
                return null;
            }

            var merged = new Godot.Collections.Array();
            merged.Resize((int)Mesh.ArrayType.Max);
            merged[(int)Mesh.ArrayType.Vertex] = vertices.ToArray();
            merged[(int)Mesh.ArrayType.Normal] = normals.ToArray();
            merged[(int)Mesh.ArrayType.TexUV] = uvs.ToArray();
            merged[(int)Mesh.ArrayType.TexUV2] = faces.ToArray();
            merged[(int)Mesh.ArrayType.Color] = colours.ToArray();
            merged[(int)Mesh.ArrayType.Index] = indices.ToArray();
            var result = new ArrayMesh { ResourceName = id };
            result.AddSurfaceFromArrays(Mesh.PrimitiveType.Triangles, merged);
            var box = result.GetAabb();
            return new ItemMesh(id, result, box.Size, coverAspect);
        }
        finally
        {
            root.Free();
        }
    }

    /// <summary>Slot names match ignoring case and a trailing Blender <c>.NNN</c> suffix (A7).</summary>
    public static Face FaceOf(string? materialName)
    {
        if (string.IsNullOrEmpty(materialName))
        {
            return Face.Case;
        }

        var name = materialName;
        var dot = name.LastIndexOf('.');
        if (dot > 0 && dot == name.Length - 4 && int.TryParse(name.AsSpan(dot + 1), out _))
        {
            name = name[..dot];
        }

        return name.ToLowerInvariant() switch
        {
            "cover" => Face.Cover,
            "back" => Face.Back,
            "spine" => Face.Spine,
            "label" => Face.Label,
            _ => Face.Case,
        };
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

    private static IEnumerable<MeshInstance3D> MeshInstances(Node node)
    {
        if (node is MeshInstance3D instance)
        {
            yield return instance;
        }

        foreach (var child in node.GetChildren())
        {
            foreach (var found in MeshInstances(child))
            {
                yield return found;
            }
        }
    }

    private static Transform3D RelativeTransform(Node3D node, Node root)
    {
        var transform = Transform3D.Identity;
        for (Node? current = node; current is not null && current != root; current = current.GetParent())
        {
            if (current is Node3D spatial)
            {
                transform = spatial.Transform * transform;
            }
        }

        return transform;
    }
}
