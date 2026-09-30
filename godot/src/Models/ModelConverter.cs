using System;
using System.Collections.Generic;
using Godot;
using Launcher.Core.Models;
using Launcher.Core.Theming;

namespace Launcher.App.Models;

/// <summary>
/// A model converted for the item shader, entirely on a worker thread: its merged rest-pose mesh (one surface, for a MultiMesh or a single node), and for a model with clips its node tree too (<see cref="Scene"/>: meshes in the same
/// format, skeletons and an <see cref="AnimationPlayer"/>), both fitted to the spec (A7: standing on y = 0, centred,
/// the largest side 1 m).
/// </summary>
public sealed class ConvertedModel
{
    /// <summary>Each slot face's width over its height, by slot number; 0 where the model has no such material.</summary>
    public float[] SlotAspects { get; } = new float[MediaSlots.Count];

    /// <summary>The authored textures its faces sample, by the index in their face code.</summary>
    public Texture2D?[] Authored { get; } = new Texture2D?[ItemTemplate.MaxAuthoredTextures];

    public List<string> Warnings { get; } = [];

    /// <summary>The fitted rest pose's bounding box.</summary>
    public Vector3 Size { get; set; }

    public int Triangles { get; set; }

    /// <summary>The merged rest-pose mesh, once <see cref="Upload"/> has made it.</summary>
    public ArrayMesh Mesh { get; private set; } = null!;

    internal MeshData? PendingMesh { get; set; }

    internal List<(MeshInstance3D Node, MeshData Data)> PendingNodes { get; } = [];

    /// <summary>
    /// Makes the meshes prepared from the file, at the end of the conversion on its worker. (Making them on the main
    /// thread instead, within its per-frame budget, spread a list's hundreds of models over many frames: its grid took
    /// 350 ms rather than 13-19 ms to show all its art, and the working set rose by 20 MB: docs/perf/m6-models.md.)
    /// </summary>
    public void Upload()
    {
        if (PendingMesh is { } merged)
        {
            Mesh = merged.Build()!;
            PendingMesh = null;
        }

        foreach (var (node, data) in PendingNodes)
        {
            node.Mesh = data.Build();
        }

        PendingNodes.Clear();
    }

    /// <summary>For a model with clips: its fitted node tree (not in the scene tree), to duplicate per cell.</summary>
    public Node3D? Scene { get; set; }

    /// <summary>The clips it plays, by <see cref="ModelClip"/>; null where it has none.</summary>
    public Animation?[] Clips { get; } = new Animation?[3];
}

/// <summary>
/// Remaps a model onto the item shader (A7). A material named after a media kind is a slot (<see cref="MediaSlots"/>);
/// every other material is plain. Base colour (linear, times any vertex colour), roughness and the base colour
/// texture are kept; anything else is ignored. Per vertex: COLOR = (base colour, roughness); UV2 = (face code, face
/// aspect), where the face code is (slot + 1) × 8 + (authored texture + 1), with 0 for none in either part
/// (item.gdshader). Textures are decoded from the file here, with mipmaps (Godot's runtime glTF import makes none), so
/// Godot's parser is told to discard its own.
/// </summary>
public static class ModelConverter
{
    /// <summary>The name of the clip that returns a model to its rest pose (made here, from its clips' tracks).</summary>
    public const string RestClip = "_rest";

    private const float MaxLaunchSeconds = 2;

    /// <summary>
    /// Converts a <c>.glb</c> whose bytes are <paramref name="glb"/> (already checked by <see cref="ModelInspector"/>
    /// for a user's file, or committed and tested for a built-in one). Worker thread; returns null with a reason.
    /// </summary>
    public static ConvertedModel? Convert(byte[] glb, string name, out string? error)
    {
        // Every Godot wrapper read here is disposed at the end: until its finaliser runs, a wrapper keeps its native
        // object alive, and the GC doesn't see native memory. With hundreds of per-game models (the parsed state, its
        // CPU-side meshes and surface arrays) that was over 100 MB of working set (docs/perf/m6-models.md).
        using var document = new GltfDocument();
        using var state = new GltfState { HandleBinaryImageMode = GltfState.HandleBinaryImageModeEnum.DiscardTextures };
        var result = document.AppendFromBuffer(glb, string.Empty, state);
        if (result != Error.Ok)
        {
            error = $"it isn't a glTF 2.0 file Godot can read ({result})";
            return null;
        }

        var model = new ConvertedModel();
        var context = new Context(glb, state, model);
        try
        {
            return Convert(document, state, context, model, name, out error);
        }
        finally
        {
            context.Dispose();
        }
    }

    private static ConvertedModel? Convert(GltfDocument document, GltfState state, Context context, ConvertedModel model, string name, out string? error)
    {
        var merged = new MeshData();
        var nodes = context.TrackArray(state.GetNodes());
        var meshes = context.TrackArray(state.GetMeshes());
        for (var i = 0; i < nodes.Count; i++)
        {
            var node = context.Track(nodes[i]);
            if (node.Mesh < 0 || node.Mesh >= meshes.Count || context.Track(meshes[node.Mesh]).Mesh is not { } mesh)
            {
                continue;
            }

            context.Track(mesh);
            var transform = node.Xform;
            for (var parent = node.Parent; parent >= 0 && parent < nodes.Count; parent = context.Track(nodes[parent]).Parent)
            {
                transform = context.Track(nodes[parent]).Xform * transform;
            }

            context.AddMesh(merged, mesh, context.TrackArray(meshes[node.Mesh].InstanceMaterials), transform, withSkin: false);
        }

        if (merged.Vertices.Count == 0)
        {
            error = "it has no triangle mesh";
            return null;
        }

        // Fitted to the spec from the rest pose, the same for the merged mesh and the node tree.
        var box = merged.Bounds();
        var largest = Mathf.Max(box.Size.X, Mathf.Max(box.Size.Y, box.Size.Z));
        var scale = largest > 0 ? 1 / largest : 1;
        var offset = new Vector3(box.Position.X + box.Size.X / 2, box.Position.Y, box.Position.Z + box.Size.Z / 2);
        var fit = new Transform3D(Basis.Identity.Scaled(new Vector3(scale, scale, scale)), -offset * scale);
        merged.Prepare(name, fit, null);
        model.PendingMesh = merged;
        model.Size = box.Size * scale;
        model.Triangles = merged.Indices.Count / 3;

        if (context.TrackArray(state.GetAnimations()).Count > 0)
        {
            BuildScene(document, state, context, model, fit, name);
        }

        model.Upload();
        error = null;
        return model;
    }

    private static void BuildScene(GltfDocument document, GltfState state, Context context, ConvertedModel model, Transform3D fit, string name)
    {
        if (document.GenerateScene(state) is not Node3D root)
        {
            model.Warnings.Add("its clips couldn't be read, so it doesn't animate");
            return;
        }

        var player = FindPlayer(root);
        if (player is null || player.GetAnimationLibrary(string.Empty) is not { } library)
        {
            root.Free();
            return;
        }

        foreach (var animation in library.GetAnimationList())
        {
            if (ModelClips.OfName(animation) is not { } clip || model.Clips[(int)clip] is not null)
            {
                continue;
            }

            // The grid plays clips by their canonical names: "Idle.001" or "Armature|idle" becomes "idle".
            var resource = library.GetAnimation(animation);
            var canonical = ModelClips.Names[(int)clip];
            if (animation != canonical && !library.HasAnimation(canonical))
            {
                library.RenameAnimation(animation, canonical);
            }

            resource.LoopMode = clip == ModelClip.Launch ? Animation.LoopModeEnum.None : Animation.LoopModeEnum.Linear;
            model.Clips[(int)clip] = resource;
        }

        if (Array.TrueForAll(model.Clips, c => c is null))
        {
            model.Warnings.Add("none of its clips is named idle, focused or launch, so it doesn't animate");
            root.Free();
            return;
        }

        ReplaceMeshes(root, state, context, model);
        library.AddAnimation(RestClip, RestPose(root, player, model.Clips));
        var wrapper = new Node3D { Name = name };
        root.Transform = fit * root.Transform;
        wrapper.AddChild(root);
        root.Owner = null;
        model.Scene = wrapper;
    }

    /// <summary>The launch clip's length, capped (A7: the emulator starts when it ends or after 2 s).</summary>
    public static float LaunchSeconds(Animation? launch) => launch is null ? 0 : Math.Min((float)launch.Length, MaxLaunchSeconds);

    private static AnimationPlayer? FindPlayer(Node node)
    {
        if (node is AnimationPlayer player)
        {
            return player;
        }

        foreach (var child in node.GetChildren())
        {
            if (FindPlayer(child) is { } found)
            {
                return found;
            }
        }

        return null;
    }

    /// <summary>
    /// Gives every mesh node of the generated tree a mesh in the item shader's format, converted from the glTF mesh's
    /// CPU-side <see cref="ImporterMesh"/> (with its instance materials): the generated node may be an
    /// <see cref="ImporterMeshInstance3D"/> (replaced by a <see cref="MeshInstance3D"/>) or, at run time, a
    /// <see cref="MeshInstance3D"/> whose own mesh is already on the GPU, which can't be read back cheaply. Nodes are
    /// found by their unique glTF names: at run time the generator replaces its importer nodes after recording them,
    /// so <c>GltfState.GetSceneNode</c> can return a freed node.
    /// </summary>
    private static void ReplaceMeshes(Node3D root, GltfState state, Context context, ConvertedModel model)
    {
        var nodes = context.TrackArray(state.GetNodes());
        var meshes = context.TrackArray(state.GetMeshes());
        for (var i = 0; i < nodes.Count; i++)
        {
            var gltfNode = context.Track(nodes[i]);
            if (gltfNode.Mesh < 0 || gltfNode.Mesh >= meshes.Count || context.Track(meshes[gltfNode.Mesh]).Mesh is not { } source)
            {
                continue;
            }

            context.Track(source);
            var data = new MeshData();
            context.AddMesh(data, source, context.TrackArray(meshes[gltfNode.Mesh].InstanceMaterials), Transform3D.Identity, withSkin: true);
            data.Prepare(source.ResourceName, Transform3D.Identity, source);
            MeshInstance3D? target = null;
            var name = gltfNode.ResourceName;
            var found = root.Name == name ? root : root.FindChild(name, recursive: true, owned: false);
            switch (found)
            {
                case MeshInstance3D instance:
                    instance.Mesh = null;
                    instance.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
                    target = instance;
                    break;
                case ImporterMeshInstance3D importer when importer.GetParent() is { } parent:
                    var replacement = new MeshInstance3D
                    {
                        Name = importer.Name,
                        Transform = importer.Transform,
                        Skin = importer.Skin,
                        Skeleton = importer.SkeletonPath,
                        CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                    };
                    target = replacement;
                    var index = importer.GetIndex();
                    parent.AddChild(replacement);
                    parent.MoveChild(replacement, index);
                    foreach (var child in importer.GetChildren())
                    {
                        importer.RemoveChild(child);
                        replacement.AddChild(child);
                    }

                    parent.RemoveChild(importer);
                    importer.Free();
                    break;
            }

            if (target is not null)
            {
                model.PendingNodes.Add((target, data));
            }
        }
    }

    /// <summary>
    /// A clip that holds every track the model's clips animate at its rest value, so leaving a clip can blend back to
    /// the pose the batched mesh has.
    /// </summary>
    private static Animation RestPose(Node3D root, AnimationPlayer player, Animation?[] clips)
    {
        var rest = new Animation { Length = 0.1f, LoopMode = Animation.LoopModeEnum.None };
        var done = new HashSet<string>(StringComparer.Ordinal);
        var origin = player.GetNode(player.RootNode) ?? root;
        foreach (var clip in clips)
        {
            if (clip is null)
            {
                continue;
            }

            for (var t = 0; t < clip.GetTrackCount(); t++)
            {
                var path = clip.TrackGetPath(t);
                var type = clip.TrackGetType(t);
                if (!done.Add($"{type}|{path}"))
                {
                    continue;
                }

                var target = origin.GetNodeOrNull(new NodePath(path.GetConcatenatedNames()));
                var track = rest.AddTrack(type);
                rest.TrackSetPath(track, path);
                var bone = path.GetSubNameCount() > 0 && target is Skeleton3D skeleton ? skeleton.FindBone(path.GetSubName(0)) : -1;
                var skeletonNode = target as Skeleton3D;
                switch (type)
                {
                    case Animation.TrackType.Position3D:
                        rest.PositionTrackInsertKey(track, 0, bone >= 0 ? skeletonNode!.GetBoneRest(bone).Origin : (target as Node3D)?.Position ?? Vector3.Zero);
                        break;
                    case Animation.TrackType.Rotation3D:
                        rest.RotationTrackInsertKey(track, 0, bone >= 0 ? skeletonNode!.GetBoneRest(bone).Basis.GetRotationQuaternion() : (target as Node3D)?.Quaternion ?? Quaternion.Identity);
                        break;
                    case Animation.TrackType.Scale3D:
                        rest.ScaleTrackInsertKey(track, 0, bone >= 0 ? skeletonNode!.GetBoneRest(bone).Basis.Scale : (target as Node3D)?.Scale ?? Vector3.One);
                        break;
                    case Animation.TrackType.BlendShape:
                        rest.BlendShapeTrackInsertKey(track, 0, 0);
                        break;
                    default:
                        rest.RemoveTrack(track);
                        break;
                }
            }
        }

        return rest;
    }

    /// <summary>What one conversion shares: the file (for its images), the parsed state, and the textures made so far.</summary>
    private sealed class Context(byte[] glb, GltfState state, ConvertedModel model) : IDisposable
    {
        private readonly Godot.Collections.Array<Material> _materials = state.GetMaterials();
        private readonly Dictionary<int, Texture2D?> _images = [];
        private readonly List<IDisposable> _read = [];
        private bool _disposed;

        /// <summary>A wrapper to dispose when the conversion ends (never one the model keeps).</summary>
        public T Track<T>(T wrapper) where T : IDisposable
        {
            _read.Add(wrapper);
            return wrapper;
        }

        /// <summary>A typed array to dispose when the conversion ends (through its untyped array, which owns it).</summary>
        public Godot.Collections.Array<T> TrackArray<[MustBeVariant] T>(Godot.Collections.Array<T> array)
        {
            _read.Add((Godot.Collections.Array)array);
            return array;
        }

        public void Dispose()
        {
            if (_disposed)
            {
                return;
            }

            _disposed = true;
            foreach (var material in _materials)
            {
                material?.Dispose();
            }

            ((Godot.Collections.Array)_materials).Dispose();
            foreach (var wrapper in _read)
            {
                wrapper.Dispose();
            }

            _read.Clear();
        }

        // Read only for a model with textures: most (every built-in box) have none, and the JSON parse costs start-up.
        private readonly bool _textured = state.GetTextures().Count > 0;
        private GlbFile? _file;

        public void AddMesh(MeshData data, ImporterMesh mesh, Godot.Collections.Array<Material> instanceMaterials, Transform3D toRoot, bool withSkin)
        {
            for (var surface = 0; surface < mesh.GetSurfaceCount(); surface++)
            {
                if (mesh.GetSurfacePrimitiveType(surface) != Godot.Mesh.PrimitiveType.Triangles)
                {
                    continue;
                }

                var material = mesh.GetSurfaceMaterial(surface) ?? (surface < instanceMaterials.Count ? instanceMaterials[surface] : null);
                Godot.Collections.Array[]? shapes = null;
                if (withSkin && mesh.GetBlendShapeCount() > 0)
                {
                    shapes = new Godot.Collections.Array[mesh.GetBlendShapeCount()];
                    for (var b = 0; b < shapes.Length; b++)
                    {
                        shapes[b] = Track(mesh.GetSurfaceBlendShapeArrays(surface, b));
                    }
                }

                AddSurface(data, toRoot, Track(mesh.GetSurfaceArrays(surface)), material, withSkin, shapes);
            }
        }

        private void AddSurface(MeshData data, Transform3D toRoot, Godot.Collections.Array arrays, Material? material, bool withSkin, Godot.Collections.Array[]? shapes)
        {
            var positions = arrays[(int)Godot.Mesh.ArrayType.Vertex].AsVector3Array();
            var normals = arrays[(int)Godot.Mesh.ArrayType.Normal].AsVector3Array();
            var uvs = arrays[(int)Godot.Mesh.ArrayType.TexUV].AsVector2Array();
            var colours = arrays[(int)Godot.Mesh.ArrayType.Color].AsColorArray();
            var indices = arrays[(int)Godot.Mesh.ArrayType.Index].AsInt32Array();
            var slot = MediaSlots.OfMaterial(material?.ResourceName);
            var (colour, roughness) = material is BaseMaterial3D standard
                ? (standard.AlbedoColor.SrgbToLinear(), standard.Roughness)
                : (Colors.White, 0.5f);

            var tex = AuthoredIndex(TextureOf(material), material?.ResourceName);
            var aspect = 0f;
            if (slot >= 0)
            {
                aspect = AspectOf(material, positions, normals, toRoot);
                if (model.SlotAspects[slot] == 0)
                {
                    model.SlotAspects[slot] = aspect;
                }
            }

            var code = new Vector2((slot + 1) * 8 + tex + 1, aspect);
            var first = data.Vertices.Count;
            for (var v = 0; v < positions.Length; v++)
            {
                data.Vertices.Add(toRoot * positions[v]);
                data.Normals.Add(normals.Length > v ? (toRoot.Basis * normals[v]).Normalized() : Vector3.Up);
                data.Uvs.Add(uvs.Length > v ? uvs[v] : Vector2.Zero);
                var tint = colours.Length > v ? colour * colours[v] : colour;
                data.Colours.Add(new Color(tint.R, tint.G, tint.B, roughness));
                data.Codes.Add(code);
            }

            if (indices.Length == 0)
            {
                for (var v = 0; v < positions.Length; v++)
                {
                    data.Indices.Add(first + v);
                }
            }
            else
            {
                foreach (var index in indices)
                {
                    data.Indices.Add(first + index);
                }
            }

            if (withSkin)
            {
                data.AddSkin(arrays, positions.Length);
                data.AddShapes(shapes, positions.Length);
            }
        }

        /// <summary>The material's base colour image, decoded from the file with mipmaps (once per image).</summary>
        private Texture2D? TextureOf(Material? material)
        {
            var index = material is null || !_textured ? -1 : _materials.IndexOf(material);
            if (index < 0 || (_file ??= GlbFile.TryRead(glb, out var read, out _) ? read : null) is not { } file)
            {
                return null;
            }

            var image = ModelInspector.BaseColourImage(file, index);
            if (image < 0)
            {
                return null;
            }

            if (_images.TryGetValue(image, out var known))
            {
                return known;
            }

            var bytes = ModelInspector.ImageBytes(file, image).Span;
            using var decoded = new Image();
            var png = bytes.Length > 4 && bytes[0] == 0x89 && bytes[1] == (byte)'P';
            var loaded = png ? decoded.LoadPngFromBuffer(bytes) : decoded.LoadJpgFromBuffer(bytes);
            Texture2D? texture = null;
            if (loaded == Error.Ok && !decoded.IsEmpty())
            {
                decoded.GenerateMipmaps();
                texture = ImageTexture.CreateFromImage(decoded);
            }
            else
            {
                model.Warnings.Add($"image {image} couldn't be decoded ({loaded}), so its material shows its colour");
            }

            _images[image] = texture;
            return texture;
        }

        /// <summary>The authored texture's index (shared by materials using the same texture), or -1.</summary>
        private int AuthoredIndex(Texture2D? texture, string? material)
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
    }

    /// <summary><c>extras.aspect</c> if the material has it, else the slot mesh's bounds across its facing (A7).</summary>
    private static float AspectOf(Material? material, Vector3[] positions, Vector3[] normals, Transform3D toRoot)
    {
        if (material is not null && material.HasMeta("extras"))
        {
            var extras = material.GetMeta("extras").AsGodotDictionary();
            if (extras.TryGetValue("aspect", out var value) && value.AsSingle() > 0)
            {
                return value.AsSingle();
            }
        }

        var box = new Aabb(positions.Length > 0 ? toRoot * positions[0] : Vector3.Zero, Vector3.Zero);
        var facing = Vector3.Zero;
        for (var i = 0; i < positions.Length; i++)
        {
            box = box.Expand(toRoot * positions[i]);
            if (i < normals.Length)
            {
                facing += toRoot.Basis * normals[i];
            }
        }

        // Height is along Y; width is whichever horizontal axis the face doesn't point along.
        var width = Mathf.Abs(facing.X) > Mathf.Abs(facing.Z) ? box.Size.Z : box.Size.X;
        return box.Size.Y > 0 ? width / box.Size.Y : 1;
    }
}

/// <summary>A mesh's vertices in the item shader's format, gathered surface by surface, then built as one surface.</summary>
public sealed class MeshData
{
    internal readonly List<Vector3> Vertices = [];
    internal readonly List<Vector3> Normals = [];
    internal readonly List<Vector2> Uvs = [];
    internal readonly List<Vector2> Codes = [];
    internal readonly List<Color> Colours = [];
    internal readonly List<int> Indices = [];
    private List<int>? _bones;
    private List<float>? _weights;
    private int _influences;
    private List<Vector3>[]? _shapeVertices;
    private List<Vector3>[]? _shapeNormals;

    public Aabb Bounds()
    {
        var box = new Aabb(Vertices[0], Vector3.Zero);
        foreach (var vertex in Vertices)
        {
            box = box.Expand(vertex);
        }

        return box;
    }

    /// <summary>Bones and weights, 4 or 8 a vertex; a surface without them gets bone 0 at weight 0.</summary>
    internal void AddSkin(Godot.Collections.Array arrays, int count)
    {
        var bones = arrays[(int)Mesh.ArrayType.Bones].AsInt32Array();
        var weights = arrays[(int)Mesh.ArrayType.Weights].AsFloat32Array();
        if (bones.Length == 0 && _bones is null)
        {
            return;
        }

        var influences = count > 0 && bones.Length > 0 ? bones.Length / count : _influences;
        if (_bones is null)
        {
            _influences = influences;
            _bones = [];
            _weights = [];
            for (var i = 0; i < (Vertices.Count - count) * _influences; i++)
            {
                _bones.Add(0);
                _weights!.Add(0);
            }
        }

        for (var i = 0; i < count * _influences; i++)
        {
            _bones.Add(i < bones.Length ? bones[i] : 0);
            _weights!.Add(i < weights.Length ? weights[i] : 0);
        }
    }

    internal void AddShapes(Godot.Collections.Array[]? shapes, int count)
    {
        if (shapes is null)
        {
            return;
        }

        if (_shapeVertices is null)
        {
            _shapeVertices = new List<Vector3>[shapes.Length];
            _shapeNormals = new List<Vector3>[shapes.Length];
            for (var b = 0; b < shapes.Length; b++)
            {
                _shapeVertices[b] = [];
                _shapeNormals[b] = [];
            }
        }

        for (var b = 0; b < Math.Min(shapes.Length, _shapeVertices.Length); b++)
        {
            var vertices = shapes[b][(int)Mesh.ArrayType.Vertex].AsVector3Array();
            var normals = shapes[b][(int)Mesh.ArrayType.Normal].AsVector3Array();
            for (var v = 0; v < count; v++)
            {
                _shapeVertices[b].Add(v < vertices.Length ? vertices[v] : Vector3.Zero);
                _shapeNormals![b].Add(v < normals.Length ? normals[v] : Vector3.Up);
            }
        }
    }

    private string _name = string.Empty;
    private Transform3D _fit = Transform3D.Identity;
    private string[]? _shapeNames;
    private Mesh.BlendShapeMode _shapeMode;

    /// <summary>Worker: what <see cref="Build"/> needs from the source, read before its wrappers are disposed.</summary>
    /// <param name="shapesFrom">The source mesh, for its blend shape names and mode.</param>
    public void Prepare(string name, Transform3D fit, ImporterMesh? shapesFrom)
    {
        _name = name;
        _fit = fit;
        if (_shapeVertices is not null && shapesFrom is not null)
        {
            _shapeMode = shapesFrom.GetBlendShapeMode();
            _shapeNames = new string[_shapeVertices.Length];
            for (var b = 0; b < _shapeNames.Length; b++)
            {
                _shapeNames[b] = shapesFrom.GetBlendShapeName(b);
            }
        }
    }

    /// <summary>Any thread: the mesh, with the prepared fit applied to its vertices.</summary>
    public ArrayMesh? Build()
    {
        if (Vertices.Count == 0)
        {
            return null;
        }

        var name = _name;
        var fit = _fit;
        var vertices = new Vector3[Vertices.Count];
        var normals = new Vector3[Normals.Count];
        for (var i = 0; i < vertices.Length; i++)
        {
            vertices[i] = fit * Vertices[i];
            normals[i] = (fit.Basis * Normals[i]).Normalized();
        }

        var arrays = new Godot.Collections.Array();
        arrays.Resize((int)Mesh.ArrayType.Max);
        arrays[(int)Mesh.ArrayType.Vertex] = vertices;
        arrays[(int)Mesh.ArrayType.Normal] = normals;
        arrays[(int)Mesh.ArrayType.TexUV] = Uvs.ToArray();
        arrays[(int)Mesh.ArrayType.TexUV2] = Codes.ToArray();
        arrays[(int)Mesh.ArrayType.Color] = Colours.ToArray();
        arrays[(int)Mesh.ArrayType.Index] = Indices.ToArray();
        var flags = (Mesh.ArrayFormat)0;
        if (_bones is not null)
        {
            arrays[(int)Mesh.ArrayType.Bones] = _bones.ToArray();
            arrays[(int)Mesh.ArrayType.Weights] = _weights!.ToArray();
            if (_influences == 8)
            {
                flags |= Mesh.ArrayFormat.FlagUse8BoneWeights;
            }
        }

        var mesh = new ArrayMesh { ResourceName = name };
        Godot.Collections.Array<Godot.Collections.Array>? blendShapes = null;
        if (_shapeVertices is not null && _shapeNames is not null)
        {
            mesh.BlendShapeMode = _shapeMode;
            blendShapes = [];
            for (var b = 0; b < _shapeVertices.Length; b++)
            {
                mesh.AddBlendShape(_shapeNames[b]);
                var shape = new Godot.Collections.Array();
                shape.Resize((int)Mesh.ArrayType.Max);
                shape[(int)Mesh.ArrayType.Vertex] = _shapeVertices[b].ToArray();
                shape[(int)Mesh.ArrayType.Normal] = _shapeNormals![b].ToArray();
                blendShapes.Add(shape);
            }
        }

        mesh.AddSurfaceFromArrays(Mesh.PrimitiveType.Triangles, arrays, blendShapes, null, flags);

        // The arrays were copied into the mesh; free them now rather than whenever the GC finalises them.
        arrays.Dispose();
        if (blendShapes is not null)
        {
            foreach (var shape in blendShapes)
            {
                shape.Dispose();
            }

            ((Godot.Collections.Array)blendShapes).Dispose();
        }

        return mesh;
    }
}
