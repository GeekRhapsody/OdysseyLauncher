using System.Buffers.Binary;
using System.Numerics;
using System.Text.Json.Nodes;

namespace Launcher.Core.Models;

/// <summary>One primitive of a mesh: triangles, counter-clockwise seen from the front (glTF's winding).</summary>
/// <param name="Uvs">TEXCOORD_0, with v = 0 at the top of the image (glTF's convention).</param>
/// <param name="Targets">Morph targets: per target, each vertex's position offset. Every primitive of a mesh needs the same number.</param>
public sealed record GltfPrimitive(Vector3[] Positions, Vector3[]? Normals, Vector2[]? Uvs, int[] Indices, int Material, Vector3[][]? Targets = null);

/// <summary>A node's transform or its mesh's morph target weights over time, for one channel of an animation clip.</summary>
/// <param name="Path">"translation", "rotation", "scale" or "weights".</param>
/// <param name="Values">3 floats a key for translation and scale, 4 (x, y, z, w) for rotation, one per morph target for weights.</param>
public sealed record GltfChannel(int Node, string Path, float[] Times, float[] Values);

/// <summary>
/// Writes a glTF 2.0 binary from meshes (with morph targets), materials, embedded images, nodes and animations: what the OBJ
/// converter, the synthetic library's per-game models and the tests' fixture models need. Everything goes in one
/// buffer; POSITION accessors carry min and max, as the spec requires.
/// </summary>
public sealed class GltfBuilder
{
    private readonly MemoryStream _binary = new();
    private readonly JsonArray _bufferViews = [];
    private readonly JsonArray _accessors = [];
    private readonly JsonArray _images = [];
    private readonly JsonArray _textures = [];
    private readonly JsonArray _materials = [];
    private readonly JsonArray _meshes = [];
    private readonly JsonArray _nodes = [];
    private readonly JsonArray _animations = [];
    private readonly List<int> _parents = [];

    public string Generator { get; init; } = "Odyssey Launcher";

    /// <summary>An embedded PNG or JPEG. Returns its texture index (one texture per image).</summary>
    public int AddImage(byte[] bytes, string mimeType)
    {
        ArgumentNullException.ThrowIfNull(bytes);
        var view = AddView(bytes, target: null);
        _images.Add(new JsonObject { ["bufferView"] = view, ["mimeType"] = mimeType });
        _textures.Add(new JsonObject { ["source"] = _images.Count - 1, ["sampler"] = 0 });
        return _textures.Count - 1;
    }

    /// <param name="baseColour">Linear RGBA. A7: a media slot's should be white.</param>
    /// <param name="texture">A texture from <see cref="AddImage"/>, or -1.</param>
    /// <param name="aspect">A slot face's width over its height (<c>extras.aspect</c>, A7), or null.</param>
    public int AddMaterial(string name, Vector4 baseColour, float roughness = 0.5f, float metallic = 0, int texture = -1, float? aspect = null, bool doubleSided = false)
    {
        var pbr = new JsonObject
        {
            ["baseColorFactor"] = new JsonArray(baseColour.X, baseColour.Y, baseColour.Z, baseColour.W),
            ["metallicFactor"] = metallic,
            ["roughnessFactor"] = roughness,
        };
        if (texture >= 0)
        {
            pbr["baseColorTexture"] = new JsonObject { ["index"] = texture };
        }

        var material = new JsonObject { ["name"] = name, ["pbrMetallicRoughness"] = pbr };
        if (doubleSided)
        {
            material["doubleSided"] = true;
        }

        if (aspect is { } a)
        {
            material["extras"] = new JsonObject { ["aspect"] = a };
        }

        _materials.Add(material);
        return _materials.Count - 1;
    }

    public int AddMesh(string name, IReadOnlyList<GltfPrimitive> primitives)
    {
        ArgumentNullException.ThrowIfNull(primitives);
        var list = new JsonArray();
        foreach (var primitive in primitives)
        {
            var attributes = new JsonObject { ["POSITION"] = AddVec3(primitive.Positions, withBounds: true) };
            if (primitive.Normals is { } normals)
            {
                attributes["NORMAL"] = AddVec3(normals, withBounds: false);
            }

            if (primitive.Uvs is { } uvs)
            {
                var bytes = new byte[uvs.Length * 8];
                for (var i = 0; i < uvs.Length; i++)
                {
                    BinaryPrimitives.WriteSingleLittleEndian(bytes.AsSpan(i * 8), uvs[i].X);
                    BinaryPrimitives.WriteSingleLittleEndian(bytes.AsSpan(i * 8 + 4), uvs[i].Y);
                }

                attributes["TEXCOORD_0"] = AddAccessor(AddView(bytes, 34962), 5126, uvs.Length, "VEC2");
            }

            var entry = new JsonObject { ["attributes"] = attributes, ["indices"] = AddIndices(primitive.Indices, primitive.Positions.Length) };
            if (primitive.Targets is { Length: > 0 } targets)
            {
                // A morph target's POSITION accessor needs its bounds too.
                var targetList = new JsonArray();
                foreach (var target in targets)
                {
                    targetList.Add(new JsonObject { ["POSITION"] = AddVec3(target, withBounds: true) });
                }

                entry["targets"] = targetList;
            }

            if (primitive.Material >= 0)
            {
                entry["material"] = primitive.Material;
            }

            list.Add(entry);
        }

        _meshes.Add(new JsonObject { ["name"] = name, ["primitives"] = list });
        return _meshes.Count - 1;
    }

    /// <param name="parent">A node from an earlier call, or -1 for a root of the scene.</param>
    public int AddNode(string name, int mesh = -1, Vector3? translation = null, Quaternion? rotation = null, Vector3? scale = null, int parent = -1)
    {
        var node = new JsonObject { ["name"] = name };
        if (mesh >= 0)
        {
            node["mesh"] = mesh;
        }

        if (translation is { } t)
        {
            node["translation"] = new JsonArray(t.X, t.Y, t.Z);
        }

        if (rotation is { } r)
        {
            node["rotation"] = new JsonArray(r.X, r.Y, r.Z, r.W);
        }

        if (scale is { } s)
        {
            node["scale"] = new JsonArray(s.X, s.Y, s.Z);
        }

        _nodes.Add(node);
        _parents.Add(parent);
        if (parent >= 0)
        {
            var parentNode = (JsonObject)_nodes[parent]!;
            if (parentNode["children"] is not JsonArray children)
            {
                parentNode["children"] = children = [];
            }

            children.Add(_nodes.Count - 1);
        }

        return _nodes.Count - 1;
    }

    /// <summary>A clip of linearly interpolated node transforms and morph target weights.</summary>
    public void AddAnimation(string name, IReadOnlyList<GltfChannel> channels)
    {
        ArgumentNullException.ThrowIfNull(channels);
        var samplers = new JsonArray();
        var list = new JsonArray();
        foreach (var channel in channels)
        {
            var (width, type) = channel.Path switch
            {
                "rotation" => (4, "VEC4"),
                "weights" => (1, "SCALAR"),    // the output is keys × targets scalars
                _ => (3, "VEC3"),
            };
            var times = new byte[channel.Times.Length * 4];
            for (var i = 0; i < channel.Times.Length; i++)
            {
                BinaryPrimitives.WriteSingleLittleEndian(times.AsSpan(i * 4), channel.Times[i]);
            }

            var values = new byte[channel.Values.Length * 4];
            for (var i = 0; i < channel.Values.Length; i++)
            {
                BinaryPrimitives.WriteSingleLittleEndian(values.AsSpan(i * 4), channel.Values[i]);
            }

            var input = AddAccessor(AddView(times, null), 5126, channel.Times.Length, "SCALAR");
            ((JsonObject)_accessors[input]!)["min"] = new JsonArray(channel.Times.Min());
            ((JsonObject)_accessors[input]!)["max"] = new JsonArray(channel.Times.Max());
            var output = AddAccessor(AddView(values, null), 5126, channel.Values.Length / width, type);
            samplers.Add(new JsonObject { ["input"] = input, ["output"] = output, ["interpolation"] = "LINEAR" });
            list.Add(new JsonObject { ["sampler"] = samplers.Count - 1, ["target"] = new JsonObject { ["node"] = channel.Node, ["path"] = channel.Path } });
        }

        _animations.Add(new JsonObject { ["name"] = name, ["channels"] = list, ["samplers"] = samplers });
    }

    public GlbFile Build()
    {
        var roots = new JsonArray();
        for (var i = 0; i < _parents.Count; i++)
        {
            if (_parents[i] < 0)
            {
                roots.Add(i);
            }
        }

        var json = new JsonObject
        {
            ["asset"] = new JsonObject { ["version"] = "2.0", ["generator"] = Generator },
            ["scene"] = 0,
            ["scenes"] = new JsonArray(new JsonObject { ["nodes"] = roots }),
            ["nodes"] = _nodes.DeepClone(),
            ["meshes"] = _meshes.DeepClone(),
        };
        Add(json, "materials", _materials);
        Add(json, "textures", _textures);
        Add(json, "images", _images);
        if (_textures.Count > 0)
        {
            json["samplers"] = new JsonArray(new JsonObject { ["magFilter"] = 9729, ["minFilter"] = 9987 });
        }

        Add(json, "animations", _animations);
        Add(json, "accessors", _accessors);
        Add(json, "bufferViews", _bufferViews);
        var binary = _binary.ToArray();
        json["buffers"] = new JsonArray(new JsonObject { ["byteLength"] = binary.Length });
        return GlbFile.Create(json, binary);

        static void Add(JsonObject json, string name, JsonArray array)
        {
            if (array.Count > 0)
            {
                json[name] = array.DeepClone();
            }
        }
    }

    public byte[] ToGlb() => Build().Write();

    private int AddView(byte[] bytes, int? target)
    {
        while (_binary.Length % 4 != 0)
        {
            _binary.WriteByte(0);
        }

        var view = new JsonObject { ["buffer"] = 0, ["byteOffset"] = (int)_binary.Length, ["byteLength"] = bytes.Length };
        if (target is { } t)
        {
            view["target"] = t;
        }

        _binary.Write(bytes);
        _bufferViews.Add(view);
        return _bufferViews.Count - 1;
    }

    private int AddAccessor(int view, int componentType, int count, string type)
    {
        _accessors.Add(new JsonObject { ["bufferView"] = view, ["componentType"] = componentType, ["count"] = count, ["type"] = type });
        return _accessors.Count - 1;
    }

    private int AddVec3(Vector3[] values, bool withBounds)
    {
        var bytes = new byte[values.Length * 12];
        var min = new Vector3(float.MaxValue);
        var max = new Vector3(float.MinValue);
        for (var i = 0; i < values.Length; i++)
        {
            BinaryPrimitives.WriteSingleLittleEndian(bytes.AsSpan(i * 12), values[i].X);
            BinaryPrimitives.WriteSingleLittleEndian(bytes.AsSpan(i * 12 + 4), values[i].Y);
            BinaryPrimitives.WriteSingleLittleEndian(bytes.AsSpan(i * 12 + 8), values[i].Z);
            min = Vector3.Min(min, values[i]);
            max = Vector3.Max(max, values[i]);
        }

        var accessor = AddAccessor(AddView(bytes, 34962), 5126, values.Length, "VEC3");
        if (withBounds && values.Length > 0)
        {
            var entry = (JsonObject)_accessors[accessor]!;
            entry["min"] = new JsonArray(min.X, min.Y, min.Z);
            entry["max"] = new JsonArray(max.X, max.Y, max.Z);
        }

        return accessor;
    }

    private int AddIndices(int[] indices, int vertices)
    {
        var wide = vertices > ushort.MaxValue;
        var bytes = new byte[indices.Length * (wide ? 4 : 2)];
        for (var i = 0; i < indices.Length; i++)
        {
            if (wide)
            {
                BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(i * 4), (uint)indices[i]);
            }
            else
            {
                BinaryPrimitives.WriteUInt16LittleEndian(bytes.AsSpan(i * 2), (ushort)indices[i]);
            }
        }

        return AddAccessor(AddView(bytes, 34963), wide ? 5125 : 5123, indices.Length, "SCALAR");
    }
}
