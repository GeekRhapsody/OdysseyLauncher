using System.Buffers.Binary;
using System.Globalization;
using System.Numerics;
using System.Text.Json.Nodes;
using Launcher.Core.Media;
using Launcher.Core.Theming;

namespace Launcher.Core.Models;

/// <summary>
/// What <see cref="ModelInspector"/> found in a model, and whether it may be used (A7). Saved beside a processed
/// model in the cache, and shown to the user by the import service (and M7's game options panel).
/// </summary>
/// <param name="Accepted">False: the model is rejected (see <see cref="Errors"/>) and the next model in line is used.</param>
/// <param name="Textures">The model's own images that its materials use as base colour (media slots stream theirs; other maps aren't drawn yet).</param>
/// <param name="Slots">The media slots its materials name, in slot order.</param>
/// <param name="Clips">The animation clips it has that the launcher plays (idle, focused, launch).</param>
/// <param name="Joints">The most joints in one skin.</param>
/// <param name="MorphTargets">The most morph targets in one mesh.</param>
/// <param name="Size">The rest pose's bounding box (width, height, depth) in the file's units.</param>
public sealed record ModelReport(
    ModelKind Kind,
    bool Accepted,
    int Triangles,
    int Materials,
    int Textures,
    int LargestTextureSide,
    IReadOnlyList<string> Slots,
    IReadOnlyList<string> Clips,
    int Joints,
    int MorphTargets,
    IReadOnlyList<float> Size,
    IReadOnlyList<string> Errors,
    IReadOnlyList<string> Warnings,
    IReadOnlyList<string> Notes)
{
    /// <summary>A rejected report with one error (a file that couldn't be read at all).</summary>
    public static ModelReport Rejected(ModelKind kind, string error) =>
        new(kind, false, 0, 0, 0, 0, [], [], 0, 0, [0, 0, 0], [error], [], []);

    public bool HasClip(ModelClip clip) => Clips.Contains(ModelClips.Names[(int)clip]);

    /// <summary>One line for logs and the console: "accepted: 1,204 triangles, 3 materials, ...".</summary>
    public string Summary()
    {
        var budget = ModelBudget.For(Kind);
        var slots = Slots.Count == 0 ? "no media slots" : "slots " + string.Join(", ", Slots);
        var clips = Clips.Count == 0 ? "no clips" : "clips " + string.Join(", ", Clips);
        return string.Create(CultureInfo.InvariantCulture,
            $"{(Accepted ? "accepted" : "rejected")} as a {ModelBudget.Describe(Kind)}: {Triangles:N0} triangles (budget {budget.Triangles:N0}), {Materials} materials ({budget.Materials}), {Textures} textures ({budget.Textures} of {budget.TextureSide}²), {slots}, {clips}");
    }
}

/// <summary>An image in a model, as the inspector found it.</summary>
/// <param name="Used">Whether a material draws it (through a base colour texture).</param>
public sealed record ModelImage(int Index, int BufferView, string MimeType, int Width, int Height, bool Used);

/// <summary>A model's report plus what processing needs from the file.</summary>
public sealed record ModelInspection(ModelReport Report, IReadOnlyList<ModelImage> Images);

/// <summary>
/// Validates a <c>.glb</c> against the model spec and budgets (A7) without Godot: every index, accessor and buffer
/// range, the index values, the node tree (no cycles or shared children), images (embedded PNG or JPEG, sized from
/// their headers) and required extensions. A file Godot would misread or crash on is rejected here, so only a model
/// that passed is ever handed to Godot's glTF parser. Pure: works on bytes.
/// </summary>
public static class ModelInspector
{
    /// <summary>More vertices than this in a model is rejected whatever its budget (memory, not looks).</summary>
    public const int MaxVertices = 2_000_000;

    private const int MaxErrors = 12;

    /// <summary>Extensions Godot's glTF importer handles; a model that requires another is rejected.</summary>
    private static readonly string[] SupportedRequired =
        ["KHR_materials_unlit", "KHR_texture_transform", "KHR_materials_emissive_strength", "KHR_mesh_quantization", "KHR_lights_punctual"];

    public static ModelInspection Inspect(ReadOnlySpan<byte> data, ModelKind kind)
    {
        if (data.Length > GlbFile.MaxBytes)
        {
            return new ModelInspection(ModelReport.Rejected(kind, string.Create(CultureInfo.InvariantCulture,
                $"is {data.Length / (1024 * 1024)} MB, more than the {GlbFile.MaxBytes / (1024 * 1024)} MB a model may be")), []);
        }

        return GlbFile.TryRead(data, out var file, out var error)
            ? Inspect(file!, kind)
            : new ModelInspection(ModelReport.Rejected(kind, error!), []);
    }

    public static ModelInspection Inspect(GlbFile file, ModelKind kind)
    {
        ArgumentNullException.ThrowIfNull(file);
        var walk = new Walk(file, kind);
        try
        {
            walk.Run();
        }
        catch (Exception e) when (e is InvalidOperationException or FormatException or OverflowException or ArgumentException or IndexOutOfRangeException)
        {
            // A JSON value of the wrong kind somewhere the walk didn't expect: still a bad file, never a crash.
            walk.Error($"has a value the launcher can't read ({e.Message})");
        }

        return walk.Result();
    }

    /// <summary>The image a material's base colour texture shows, or -1 (the app loads these with mipmaps itself).</summary>
    public static int BaseColourImage(GlbFile file, int material)
    {
        ArgumentNullException.ThrowIfNull(file);
        if (Get(file.Json, "materials", material) is not JsonObject m
            || m["pbrMetallicRoughness"]?["baseColorTexture"]?["index"] is not JsonValue textureIndex
            || !textureIndex.TryGetValue<int>(out var texture)
            || Get(file.Json, "textures", texture) is not JsonObject t
            || t["source"] is not JsonValue source
            || !source.TryGetValue<int>(out var image))
        {
            return -1;
        }

        return Get(file.Json, "images", image) is JsonObject ? image : -1;
    }

    /// <summary>An embedded image's bytes (a PNG or JPEG), or empty if it isn't in the binary chunk.</summary>
    public static ReadOnlyMemory<byte> ImageBytes(GlbFile file, int image)
    {
        ArgumentNullException.ThrowIfNull(file);
        if (Get(file.Json, "images", image) is not JsonObject entry || entry["bufferView"] is not JsonValue viewIndex || !viewIndex.TryGetValue<int>(out var view))
        {
            return ReadOnlyMemory<byte>.Empty;
        }

        return ViewBytes(file, view);
    }

    internal static ReadOnlyMemory<byte> ViewBytes(GlbFile file, int view)
    {
        if (Get(file.Json, "bufferViews", view) is not JsonObject bufferView)
        {
            return ReadOnlyMemory<byte>.Empty;
        }

        var offset = Int(bufferView, "byteOffset") ?? 0;
        var length = Int(bufferView, "byteLength") ?? 0;
        return offset >= 0 && length >= 0 && (long)offset + length <= file.Binary.Length
            ? file.Binary.AsMemory(offset, length)
            : ReadOnlyMemory<byte>.Empty;
    }

    private static JsonNode? Get(JsonObject root, string name, int index) =>
        root[name] is JsonArray array && index >= 0 && index < array.Count ? array[index] : null;

    private static int? Int(JsonObject? node, string name) =>
        node?[name] is JsonValue value && value.TryGetValue<int>(out var result) ? result : null;

    private static string? Str(JsonObject? node, string name) =>
        node?[name] is JsonValue value && value.TryGetValue<string>(out var result) ? result : null;

    /// <summary>One inspection's state.</summary>
    private sealed class Walk(GlbFile file, ModelKind kind)
    {
        private static readonly JsonArray Empty = [];

        private readonly JsonObject _root = file.Json;
        private readonly byte[] _binary = file.Binary;
        private readonly List<string> _errors = [];
        private readonly List<string> _warnings = [];
        private readonly List<string> _notes = [];
        private readonly List<ModelImage> _images = [];
        private readonly SortedSet<int> _slots = [];
        private readonly SortedSet<ModelClip> _clips = [];
        private readonly HashSet<int> _usedImages = [];
        private readonly HashSet<int> _usedMaterials = [];
        private long[] _accessorCounts = [];
        private int[] _meshTriangles = [];
        private int _triangles;
        private int _joints;
        private int _morphTargets;
        private long _vertices;
        private Vector3 _min = new(float.MaxValue);
        private Vector3 _max = new(float.MinValue);

        public void Error(string message)
        {
            if (_errors.Count < MaxErrors)
            {
                _errors.Add(message);
            }
        }

        public void Run()
        {
            var version = Str(_root["asset"] as JsonObject, "version");
            if (version is null || !version.StartsWith("2.", StringComparison.Ordinal))
            {
                Error("doesn't say it's glTF 2.0 (asset.version)");
                return;
            }

            CheckExtensions();
            var bufferLength = CheckBuffers();
            CheckBufferViews(bufferLength);
            CheckAccessors();
            CheckImages();
            CheckTexturesAndMaterials();
            CheckMeshes();
            var parents = CheckNodes();
            CheckSkins();
            CheckAnimations();
            if (_errors.Count == 0)
            {
                CountScene(parents);
            }
        }

        public ModelInspection Result()
        {
            var budget = ModelBudget.For(kind);
            var materials = _usedMaterials.Count;
            var textures = _usedImages.Count;
            var largest = 0;
            foreach (var image in _images)
            {
                if (image.Used)
                {
                    largest = Math.Max(largest, Math.Max(image.Width, image.Height));
                }
            }

            if (_errors.Count == 0)
            {
                Budget("triangles", _triangles, budget.Triangles);
                Budget("materials", materials, budget.Materials);
                Budget("textures", textures, budget.Textures);
                Budget("joints in a skin", _joints, ModelBudget.Joints);
                Budget("morph targets in a mesh", _morphTargets, ModelBudget.MorphTargets);
                if (largest > budget.TextureSide)
                {
                    _notes.Add(string.Create(CultureInfo.InvariantCulture,
                        $"its largest texture is {largest}², more than the {budget.TextureSide}² a {ModelBudget.Describe(kind)} may use, so textures are scaled down to fit"));
                }

                if (_slots.Count == 0 && kind != ModelKind.SystemModel)
                {
                    _notes.Add("it has no media slot (no material is named cover, back, spine, box_texture, label, screenshot, logo or hero), so it shows no art: that's allowed");
                }
            }

            var size = _max.X >= _min.X ? new[] { _max.X - _min.X, _max.Y - _min.Y, _max.Z - _min.Z } : [0f, 0f, 0f];
            var largestSide = Math.Max(size[0], Math.Max(size[1], size[2]));
            if (_errors.Count == 0 && largestSide > 0 && (largestSide > 10 || largestSide < 0.1f))
            {
                _warnings.Add(string.Create(CultureInfo.InvariantCulture,
                    $"its largest side is {largestSide:0.###}, not about 1 m (wrong units?); it's scaled to fit its grid cell"));
            }

            var slots = _slots.Select(s => MediaSlots.Names[s]).ToList();
            var clips = _clips.Select(c => ModelClips.Names[(int)c]).ToList();
            var report = new ModelReport(kind, _errors.Count == 0, _triangles, materials, textures, largest, slots, clips,
                _joints, _morphTargets, size, _errors, _warnings, _notes);
            return new ModelInspection(report, _images);
        }

        private void Budget(string what, int value, int limit)
        {
            if (value > 2 * limit)
            {
                Error(string.Create(CultureInfo.InvariantCulture,
                    $"has {value:N0} {what}, more than twice the {limit:N0} a {ModelBudget.Describe(kind)} may have"));
            }
            else if (value > limit)
            {
                _warnings.Add(string.Create(CultureInfo.InvariantCulture,
                    $"has {value:N0} {what}, over the {limit:N0} a {ModelBudget.Describe(kind)} should have (it's used, but may slow the grid)"));
            }
        }

        private JsonArray Arr(string name) => _root[name] as JsonArray ?? Empty;

        private static JsonArray Arr(JsonObject? node, string name) => node?[name] as JsonArray ?? Empty;

        /// <summary>An index into a top-level array, or -1 (an error is recorded) if it's there but out of range.</summary>
        private int Ref(JsonObject? node, string name, string array, string where, bool required = false)
        {
            if (node?[name] is not JsonValue value)
            {
                if (required)
                {
                    Error($"{where} has no {name}");
                }

                return -1;
            }

            if (!value.TryGetValue<int>(out var index) || index < 0 || index >= Arr(array).Count)
            {
                Error($"{where} names {Singular(array)} {value.ToJsonString()}, which doesn't exist");
                return -1;
            }

            return index;
        }

        private static string Singular(string array) => array switch
        {
            "meshes" => "mesh",
            "bufferViews" => "buffer view",
            _ => array[..^1],
        };

        private void CheckExtensions()
        {
            foreach (var extension in Arr(_root as JsonObject, "extensionsRequired"))
            {
                var name = extension?.GetValue<string>();
                if (name is not null && !SupportedRequired.Contains(name))
                {
                    Error($"needs the glTF extension {name}, which the launcher doesn't support");
                }
            }
        }

        private long CheckBuffers()
        {
            var buffers = Arr("buffers");
            if (buffers.Count == 0)
            {
                return 0;
            }

            for (var i = 0; i < buffers.Count; i++)
            {
                var buffer = buffers[i] as JsonObject;
                if (buffer?["uri"] is not null || i > 0)
                {
                    Error("keeps data outside the .glb (a buffer with a uri): everything must be embedded");
                    return 0;
                }
            }

            var length = Int(buffers[0] as JsonObject, "byteLength") ?? -1;
            if (length < 0 || length > _binary.Length)
            {
                Error("says its binary chunk is longer than it is");
                return 0;
            }

            return length;
        }

        private void CheckBufferViews(long bufferLength)
        {
            var views = Arr("bufferViews");
            for (var i = 0; i < views.Count; i++)
            {
                var view = views[i] as JsonObject;
                var where = $"buffer view {i}";
                Ref(view, "buffer", "buffers", where, required: true);
                var offset = (long)(Int(view, "byteOffset") ?? 0);
                var length = (long)(Int(view, "byteLength") ?? -1);
                var stride = Int(view, "byteStride");
                if (length < 1 || offset < 0 || offset + length > bufferLength)
                {
                    Error($"{where} runs past the end of the binary chunk");
                }

                if (stride is { } s && (s < 4 || s > 252 || s % 4 != 0))
                {
                    Error($"{where} has a byte stride of {s} (4 to 252, a multiple of 4)");
                }
            }
        }

        private static int ComponentSize(int type) => type switch
        {
            5120 or 5121 => 1,
            5122 or 5123 => 2,
            5125 or 5126 => 4,
            _ => 0,
        };

        private static (int Columns, int Rows) Shape(string? type) => type switch
        {
            "SCALAR" => (1, 1),
            "VEC2" => (1, 2),
            "VEC3" => (1, 3),
            "VEC4" => (1, 4),
            "MAT2" => (2, 2),
            "MAT3" => (3, 3),
            "MAT4" => (4, 4),
            _ => (0, 0),
        };

        private void CheckAccessors()
        {
            var accessors = Arr("accessors");
            _accessorCounts = new long[accessors.Count];
            var views = Arr("bufferViews");
            for (var i = 0; i < accessors.Count; i++)
            {
                var accessor = accessors[i] as JsonObject;
                var where = $"accessor {i}";
                var component = ComponentSize(Int(accessor, "componentType") ?? 0);
                var (columns, rows) = Shape(Str(accessor, "type"));
                var count = Int(accessor, "count") ?? -1;
                _accessorCounts[i] = count;
                if (component == 0 || columns == 0 || count < 1)
                {
                    Error($"{where} has an unknown component type, type or count");
                    continue;
                }

                // Matrix columns of 1- and 2-byte components are padded to 4 bytes.
                var elementSize = columns == 1 ? rows * component : columns * GlbFile.Align(rows * component);
                var view = Ref(accessor, "bufferView", "bufferViews", where);
                if (view >= 0)
                {
                    var viewNode = views[view] as JsonObject;
                    var stride = Int(viewNode, "byteStride") ?? elementSize;
                    var needed = (long)(Int(accessor, "byteOffset") ?? 0) + (long)stride * (count - 1) + elementSize;
                    if (needed > (Int(viewNode, "byteLength") ?? 0))
                    {
                        Error($"{where} runs past the end of its buffer view");
                    }
                }

                if (accessor?["sparse"] is JsonObject sparse)
                {
                    CheckSparse(sparse, where, elementSize, count, views);
                }
            }
        }

        private void CheckSparse(JsonObject sparse, string where, int elementSize, int count, JsonArray views)
        {
            var sparseCount = Int(sparse, "count") ?? -1;
            if (sparseCount < 1 || sparseCount > count)
            {
                Error($"{where} has a sparse count out of range");
                return;
            }

            var indices = sparse["indices"] as JsonObject;
            var values = sparse["values"] as JsonObject;
            var indexSize = ComponentSize(Int(indices, "componentType") ?? 0);
            var indexView = Ref(indices, "bufferView", "bufferViews", where + " (sparse indices)", required: true);
            var valueView = Ref(values, "bufferView", "bufferViews", where + " (sparse values)", required: true);
            if (indexSize == 0 || indexView < 0 || valueView < 0)
            {
                Error($"{where} has sparse storage the launcher can't read");
                return;
            }

            if ((Int(indices, "byteOffset") ?? 0) + (long)indexSize * sparseCount > (Int(views[indexView] as JsonObject, "byteLength") ?? 0)
                || (Int(values, "byteOffset") ?? 0) + (long)elementSize * sparseCount > (Int(views[valueView] as JsonObject, "byteLength") ?? 0))
            {
                Error($"{where}'s sparse data runs past the end of its buffer view");
            }
        }

        private void CheckImages()
        {
            var images = Arr("images");
            for (var i = 0; i < images.Count; i++)
            {
                var image = images[i] as JsonObject;
                var where = $"image {i}";
                if (image?["uri"] is not null)
                {
                    Error($"{where} is a separate file (a uri): images must be embedded in the .glb");
                    continue;
                }

                var view = Ref(image, "bufferView", "bufferViews", where, required: true);
                if (view < 0)
                {
                    continue;
                }

                var bytes = ViewBytes(file, view).Span;
                var mime = Str(image, "mimeType");
                var sniffed = bytes.StartsWith((ReadOnlySpan<byte>)[0x89, (byte)'P', (byte)'N', (byte)'G']) ? "image/png"
                    : bytes.StartsWith((ReadOnlySpan<byte>)[0xFF, 0xD8, 0xFF]) ? "image/jpeg"
                    : null;
                if (sniffed is null)
                {
                    Error($"{where} isn't a PNG or JPEG (A7)");
                    continue;
                }

                if (mime is not null && mime != sniffed)
                {
                    _warnings.Add($"{where} says it's {mime}, but it's {sniffed}");
                }

                using var stream = new MemoryStream(bytes.ToArray(), writable: false);
                if (!ImageHeaders.TryReadSize(stream, out var width, out var height) || width < 1 || height < 1 || width > 16384 || height > 16384)
                {
                    Error($"{where} has no readable size (a broken {sniffed[6..].ToUpperInvariant()})");
                    continue;
                }

                _images.Add(new ModelImage(i, view, sniffed, width, height, false));
            }
        }

        private void CheckTexturesAndMaterials()
        {
            var textures = Arr("textures");
            var textureImage = new int[textures.Count];
            for (var i = 0; i < textures.Count; i++)
            {
                var texture = textures[i] as JsonObject;
                Ref(texture, "sampler", "samplers", $"texture {i}");
                textureImage[i] = Ref(texture, "source", "images", $"texture {i}");
                if (texture?["source"] is null)
                {
                    _notes.Add($"texture {i} has no PNG or JPEG source (a texture extension the launcher ignores)");
                }
            }

            // Only base colour textures are drawn (the app decodes those alone), so only they count against the budget.
            // The other maps are still checked, since Godot's parser reads their references, but they cost nothing yet.
            var ignoredMaps = new SortedSet<string>(StringComparer.Ordinal);
            var materials = Arr("materials");
            for (var i = 0; i < materials.Count; i++)
            {
                var material = materials[i] as JsonObject;
                var where = $"material {i} ('{Str(material, "name")}')";
                var pbr = material?["pbrMetallicRoughness"] as JsonObject;
                foreach (var (owner, name) in (ReadOnlySpan<(JsonObject?, string)>)[
                    (pbr, "baseColorTexture"), (pbr, "metallicRoughnessTexture"), (material, "normalTexture"),
                    (material, "occlusionTexture"), (material, "emissiveTexture")])
                {
                    if (owner?[name] is JsonObject info)
                    {
                        var texture = Ref(info, "index", "textures", $"{where} {name}", required: true);
                        if (name != "baseColorTexture")
                        {
                            ignoredMaps.Add(name);
                        }
                        else if (texture >= 0 && textureImage[texture] >= 0)
                        {
                            _usedImages.Add(textureImage[texture]);
                        }
                    }
                }
            }

            if (ignoredMaps.Count > 0)
            {
                _notes.Add($"its materials' {string.Join(", ", ignoredMaps)} maps aren't drawn yet, so they don't count as textures");
            }

            for (var i = 0; i < _images.Count; i++)
            {
                if (_usedImages.Contains(_images[i].Index))
                {
                    _images[i] = _images[i] with { Used = true };
                }
            }

            // An image a texture names that failed its own checks doesn't count as a texture.
            _usedImages.IntersectWith(_images.Select(image => image.Index));
        }

        private void CheckMeshes()
        {
            var meshes = Arr("meshes");
            var accessors = Arr("accessors");
            _meshTriangles = new int[meshes.Count];
            for (var m = 0; m < meshes.Count; m++)
            {
                var mesh = meshes[m] as JsonObject;
                var primitives = Arr(mesh, "primitives");
                if (primitives.Count == 0)
                {
                    Error($"mesh {m} has no primitives");
                }

                for (var p = 0; p < primitives.Count; p++)
                {
                    var primitive = primitives[p] as JsonObject;
                    var where = $"mesh {m} primitive {p}";
                    var attributes = primitive?["attributes"] as JsonObject;
                    var position = Ref(attributes, "POSITION", "accessors", where, required: true);
                    if (position < 0)
                    {
                        continue;
                    }

                    var positionAccessor = accessors[position] as JsonObject;
                    if (Str(positionAccessor, "type") != "VEC3")
                    {
                        Error($"{where}'s POSITION isn't a VEC3");
                        continue;
                    }

                    var vertices = _accessorCounts[position];
                    _vertices += vertices;
                    if (_vertices > MaxVertices)
                    {
                        Error(string.Create(CultureInfo.InvariantCulture, $"has more than {MaxVertices:N0} vertices"));
                        return;
                    }

                    foreach (var (name, _) in attributes!)
                    {
                        var accessor = Ref(attributes, name, "accessors", $"{where} attribute {name}");
                        if (accessor >= 0 && _accessorCounts[accessor] != vertices)
                        {
                            Error($"{where}'s {name} has a different count from its POSITION");
                        }
                    }

                    var material = Ref(primitive, "material", "materials", where);
                    if (material >= 0)
                    {
                        _usedMaterials.Add(material);
                        if (MediaSlots.OfMaterial(Str(Arr("materials")[material] as JsonObject, "name")) is var slot and >= 0)
                        {
                            _slots.Add(slot);
                        }
                    }

                    var mode = Int(primitive, "mode") ?? 4;
                    if (mode is < 0 or > 6)
                    {
                        Error($"{where} has an unknown mode {mode}");
                        continue;
                    }

                    long elements = vertices;
                    var indices = Ref(primitive, "indices", "accessors", where);
                    if (indices >= 0)
                    {
                        elements = _accessorCounts[indices];
                        CheckIndices(indices, vertices, where);
                    }

                    _meshTriangles[m] += mode switch
                    {
                        4 => (int)(elements / 3),
                        5 or 6 => (int)Math.Max(0, elements - 2),
                        _ => 0,
                    };

                    var targets = Arr(primitive, "targets");
                    _morphTargets = Math.Max(_morphTargets, targets.Count);
                    for (var t = 0; t < targets.Count; t++)
                    {
                        if (targets[t] is not JsonObject target)
                        {
                            Error($"{where} morph target {t} isn't an object");
                            continue;
                        }

                        foreach (var (name, _) in target)
                        {
                            var accessor = Ref(target, name, "accessors", $"{where} morph target {t} {name}");
                            if (accessor >= 0 && _accessorCounts[accessor] != vertices)
                            {
                                Error($"{where} morph target {t} has a different count from its POSITION");
                            }
                        }
                    }

                    if (position >= 0 && positionAccessor?["min"] is not JsonArray)
                    {
                        _notes.Add($"{where}'s POSITION has no min and max, so its size isn't known before it loads");
                    }
                }
            }
        }

        /// <summary>Indices must be plain unsigned integers, and every one must name a vertex.</summary>
        private void CheckIndices(int accessorIndex, long vertices, string where)
        {
            var accessor = Arr("accessors")[accessorIndex] as JsonObject;
            var type = Int(accessor, "componentType") ?? 0;
            if (Str(accessor, "type") != "SCALAR" || type is not (5121 or 5123 or 5125) || accessor?["sparse"] is not null)
            {
                Error($"{where}'s indices aren't plain unsigned integers");
                return;
            }

            var view = Ref(accessor, "bufferView", "bufferViews", where + " indices", required: true);
            if (view < 0 || _errors.Count > 0)
            {
                return;
            }

            var bytes = ViewBytes(file, view).Span;
            var offset = Int(accessor, "byteOffset") ?? 0;
            var size = ComponentSize(type);
            var count = _accessorCounts[accessorIndex];
            if (offset + count * size > bytes.Length)
            {
                return;
            }

            bytes = bytes.Slice(offset, (int)(count * size));
            for (var i = 0; i < count; i++)
            {
                var value = size switch
                {
                    1 => bytes[i],
                    2 => BinaryPrimitives.ReadUInt16LittleEndian(bytes[(i * 2)..]),
                    _ => (long)BinaryPrimitives.ReadUInt32LittleEndian(bytes[(i * 4)..]),
                };
                if (value >= vertices)
                {
                    Error(string.Create(CultureInfo.InvariantCulture, $"{where} has an index {value}, but only {vertices} vertices"));
                    return;
                }
            }
        }

        /// <summary>Each node's parent (-1 for roots), after checking there's no cycle or shared child.</summary>
        private int[] CheckNodes()
        {
            var nodes = Arr("nodes");
            var parent = new int[nodes.Count];
            Array.Fill(parent, -1);
            for (var i = 0; i < nodes.Count; i++)
            {
                var node = nodes[i] as JsonObject;
                var where = $"node {i}";
                Ref(node, "mesh", "meshes", where);
                Ref(node, "skin", "skins", where);
                Ref(node, "camera", "cameras", where);
                if (node?["matrix"] is JsonArray matrix && matrix.Count != 16)
                {
                    Error($"{where}'s matrix doesn't have 16 numbers");
                }

                foreach (var child in Arr(node, "children"))
                {
                    if (child is not JsonValue value || !value.TryGetValue<int>(out var c) || c < 0 || c >= nodes.Count || c == i)
                    {
                        Error($"{where} has a child that doesn't exist");
                        continue;
                    }

                    if (parent[c] >= 0)
                    {
                        Error($"node {c} is the child of two nodes");
                        continue;
                    }

                    parent[c] = i;
                }
            }

            // A cycle would leave nodes whose parent chain never ends.
            for (var i = 0; i < nodes.Count && _errors.Count == 0; i++)
            {
                var steps = 0;
                for (var p = parent[i]; p >= 0; p = parent[p])
                {
                    if (++steps > nodes.Count)
                    {
                        Error($"node {i}'s parents form a loop");
                        break;
                    }
                }
            }

            return parent;
        }

        private void CheckSkins()
        {
            var skins = Arr("skins");
            var nodes = Arr("nodes").Count;
            for (var i = 0; i < skins.Count; i++)
            {
                var skin = skins[i] as JsonObject;
                var joints = Arr(skin, "joints");
                _joints = Math.Max(_joints, joints.Count);
                foreach (var joint in joints)
                {
                    if (joint is not JsonValue value || !value.TryGetValue<int>(out var j) || j < 0 || j >= nodes)
                    {
                        Error($"skin {i} names a joint that isn't a node");
                        break;
                    }
                }

                var matrices = Ref(skin, "inverseBindMatrices", "accessors", $"skin {i}");
                if (matrices >= 0 && _accessorCounts[matrices] < joints.Count)
                {
                    Error($"skin {i} has fewer inverse bind matrices than joints");
                }
            }
        }

        private void CheckAnimations()
        {
            var animations = Arr("animations");
            var nodes = Arr("nodes").Count;
            for (var a = 0; a < animations.Count; a++)
            {
                var animation = animations[a] as JsonObject;
                var name = Str(animation, "name");
                var where = $"animation {a} ('{name}')";
                var samplers = Arr(animation, "samplers");
                foreach (var sampler in samplers)
                {
                    var s = sampler as JsonObject;
                    Ref(s, "input", "accessors", where + " sampler", required: true);
                    Ref(s, "output", "accessors", where + " sampler", required: true);
                    if (Str(s, "interpolation") is { } interpolation && interpolation is not ("LINEAR" or "STEP" or "CUBICSPLINE"))
                    {
                        Error($"{where} has an unknown interpolation '{interpolation}'");
                    }
                }

                foreach (var channel in Arr(animation, "channels"))
                {
                    var c = channel as JsonObject;
                    var sampler = Int(c, "sampler") ?? -1;
                    var target = c?["target"] as JsonObject;
                    var node = Int(target, "node");
                    if (sampler < 0 || sampler >= samplers.Count || node is < 0 || node >= nodes)
                    {
                        Error($"{where} has a channel whose sampler or node doesn't exist");
                        break;
                    }

                    if (Str(target, "path") is not ("translation" or "rotation" or "scale" or "weights"))
                    {
                        _notes.Add($"{where} animates something other than a node's transform or weights, which is ignored");
                    }
                }

                if (ModelClips.OfName(name) is { } clip)
                {
                    _clips.Add(clip);
                }
                else
                {
                    _notes.Add($"the clip '{name}' isn't idle, focused or launch, so it's ignored");
                }
            }
        }

        /// <summary>Triangles and the rest pose's bounds over the scene's nodes (a mesh used twice counts twice).</summary>
        private void CountScene(int[] parent)
        {
            var nodes = Arr("nodes");
            var scenes = Arr("scenes");
            if (scenes.Count > 1)
            {
                _notes.Add("it has more than one scene; only the default one is used");
            }

            var scene = Int(_root, "scene") ?? 0;
            var roots = new List<int>();
            if (scene >= 0 && scene < scenes.Count)
            {
                foreach (var node in Arr(scenes[scene] as JsonObject, "nodes"))
                {
                    if (node is JsonValue value && value.TryGetValue<int>(out var n) && n >= 0 && n < nodes.Count && parent[n] < 0)
                    {
                        roots.Add(n);
                    }
                }
            }
            else
            {
                for (var n = 0; n < nodes.Count; n++)
                {
                    if (parent[n] < 0)
                    {
                        roots.Add(n);
                    }
                }
            }

            if (roots.Count == 0 && nodes.Count > 0)
            {
                Error("its scene has no nodes");
                return;
            }

            var stack = new Stack<(int Node, Matrix4x4 Parent)>();
            foreach (var root in roots)
            {
                stack.Push((root, Matrix4x4.Identity));
            }

            var visited = 0;
            while (stack.Count > 0)
            {
                var (index, parentWorld) = stack.Pop();
                if (++visited > nodes.Count)
                {
                    break;
                }

                var node = nodes[index] as JsonObject;
                var world = Local(node) * parentWorld;
                if (Int(node, "mesh") is { } mesh && mesh >= 0 && mesh < _meshTriangles.Length)
                {
                    _triangles += _meshTriangles[mesh];
                    Bounds(mesh, world);
                }

                foreach (var child in Arr(node, "children"))
                {
                    stack.Push((child!.GetValue<int>(), world));
                }
            }

            if (_triangles == 0)
            {
                Error("has no triangles to draw");
            }
        }

        private static Matrix4x4 Local(JsonObject? node)
        {
            if (node?["matrix"] is JsonArray m && m.Count == 16)
            {
                // glTF is column-major with column vectors; read in order, it's System.Numerics' row-vector form.
                var f = new float[16];
                for (var i = 0; i < 16; i++)
                {
                    f[i] = m[i]!.GetValue<float>();
                }

                return new Matrix4x4(f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[8], f[9], f[10], f[11], f[12], f[13], f[14], f[15]);
            }

            var t = Vector(node?["translation"] as JsonArray, 3, 0);
            var r = Vector(node?["rotation"] as JsonArray, 4, 0);
            var s = Vector(node?["scale"] as JsonArray, 3, 1);
            var rotation = node?["rotation"] is JsonArray ? new Quaternion(r[0], r[1], r[2], r[3]) : Quaternion.Identity;
            return Matrix4x4.CreateScale(s[0], s[1], s[2]) * Matrix4x4.CreateFromQuaternion(rotation) * Matrix4x4.CreateTranslation(t[0], t[1], t[2]);
        }

        private static float[] Vector(JsonArray? array, int length, float fallback)
        {
            var values = new float[length];
            for (var i = 0; i < length; i++)
            {
                values[i] = array is not null && i < array.Count ? array[i]!.GetValue<float>() : fallback;
            }

            return values;
        }

        private void Bounds(int mesh, Matrix4x4 world)
        {
            var accessors = Arr("accessors");
            foreach (var primitive in Arr(Arr("meshes")[mesh] as JsonObject, "primitives"))
            {
                var position = Int((primitive as JsonObject)?["attributes"] as JsonObject, "POSITION") ?? -1;
                if (position < 0 || accessors[position] is not JsonObject accessor
                    || accessor["min"] is not JsonArray { Count: 3 } min || accessor["max"] is not JsonArray { Count: 3 } max)
                {
                    continue;
                }

                var lo = new Vector3(min[0]!.GetValue<float>(), min[1]!.GetValue<float>(), min[2]!.GetValue<float>());
                var hi = new Vector3(max[0]!.GetValue<float>(), max[1]!.GetValue<float>(), max[2]!.GetValue<float>());
                for (var corner = 0; corner < 8; corner++)
                {
                    var p = new Vector3((corner & 1) == 0 ? lo.X : hi.X, (corner & 2) == 0 ? lo.Y : hi.Y, (corner & 4) == 0 ? lo.Z : hi.Z);
                    var q = Vector3.Transform(p, world);
                    _min = Vector3.Min(_min, q);
                    _max = Vector3.Max(_max, q);
                }
            }
        }
    }
}
