using System.Buffers.Binary;
using System.Globalization;
using System.IO.Compression;
using System.Numerics;
using System.Text;
using Launcher.Core.Media;

namespace Launcher.Core.Models;

/// <summary>What converting a model to glTF produced: the <c>.glb</c> (null on failure) and what the user should know.</summary>
public sealed record ConvertedModelFile(byte[]? Glb, IReadOnlyList<string> Errors, IReadOnlyList<string> Warnings);

/// <summary>
/// Converts a Wavefront OBJ model (the <c>.obj</c>, its <c>.mtl</c> materials and their textures) into a glTF 2.0
/// binary, so the rest of the pipeline only ever sees <c>.glb</c> files (A7). A zip is read in memory and nothing
/// in it is extracted, so its paths can't write anywhere. OBJ's axes are glTF's (+Y up, the front facing +Z, as
/// Blender exports them); faces are triangulated as fans; missing normals are computed (smoothed within an
/// <c>s</c> group, flat otherwise); texture coordinates are flipped to glTF's top-left origin. Materials keep their
/// names, so one named <c>cover</c> or <c>screenshot</c> is a media slot. A PS2 save icon (an <c>.anim</c> or an
/// <c>iconsys.json</c> beside the OBJ) faces -Z, so it's turned a half turn about Y; its shape animation
/// (<c>ICON.ICO.anim</c> for <c>ICON.ICO.obj</c>, <see cref="ShapeAnimation"/>) becomes morph targets and a
/// <c>focused</c> clip. Never throws for a bad file.
/// </summary>
public static class ObjConverter
{
    /// <summary>More than this uncompressed in a zip is refused (a zip bomb, or not a model).</summary>
    public const long MaxZipBytes = 256L * 1024 * 1024;

    private const int MaxEntryBytes = 128 * 1024 * 1024;

    /// <summary>A zip holding one <c>.obj</c> with its <c>.mtl</c> and textures (or one <c>.glb</c>, passed through).</summary>
    public static ConvertedModelFile FromZip(Stream zip, IImageDecoder? decoder, string scratchDir)
    {
        ArgumentNullException.ThrowIfNull(zip);
        try
        {
            using var archive = new ZipArchive(zip, ZipArchiveMode.Read, leaveOpen: true);
            var entries = archive.Entries
                .Where(e => e.Length > 0 && !e.FullName.EndsWith('/') && !e.FullName.StartsWith("__MACOSX/", StringComparison.OrdinalIgnoreCase)
                    && !Path.GetFileName(e.FullName).StartsWith('.'))
                .ToList();
            if (entries.Sum(e => e.Length) > MaxZipBytes)
            {
                return Failed($"is more than {MaxZipBytes / (1024 * 1024)} MB uncompressed");
            }

            var objs = entries.Where(e => e.FullName.EndsWith(".obj", StringComparison.OrdinalIgnoreCase)).ToList();
            var glbs = entries.Where(e => e.FullName.EndsWith(".glb", StringComparison.OrdinalIgnoreCase)).ToList();
            if (objs.Count == 0 && glbs.Count == 1)
            {
                return new ConvertedModelFile(Read(glbs[0]), [], []);
            }

            if (objs.Count != 1)
            {
                return Failed(objs.Count == 0
                    ? "has no .obj model in it"
                    : $"has {objs.Count} .obj files in it ({string.Join(", ", objs.Select(o => o.FullName))}); put one model in a zip");
            }

            var byPath = new Dictionary<string, ZipArchiveEntry>(StringComparer.OrdinalIgnoreCase);
            foreach (var entry in entries)
            {
                byPath.TryAdd(Normalise(entry.FullName), entry);
            }

            byte[]? Open(string path)
            {
                if (byPath.TryGetValue(Normalise(path), out var entry))
                {
                    return Read(entry);
                }

                // Exporters often write absolute or wrong folders: fall back to a unique file of that name.
                var name = Path.GetFileName(Normalise(path));
                var matches = entries.Where(e => string.Equals(Path.GetFileName(e.FullName), name, StringComparison.OrdinalIgnoreCase)).ToList();
                return matches.Count == 1 ? Read(matches[0]) : null;
            }

            return Convert(objs[0].FullName, Open, decoder, scratchDir);
        }
        catch (InvalidDataException e)
        {
            return Failed($"isn't a zip the launcher can read ({e.Message})");
        }

        static byte[] Read(ZipArchiveEntry entry)
        {
            if (entry.Length > MaxEntryBytes)
            {
                throw new InvalidDataException($"{entry.FullName} is too large");
            }

            using var stream = entry.Open();
            using var memory = new MemoryStream((int)entry.Length);
            stream.CopyTo(memory);
            return memory.ToArray();
        }
    }

    /// <summary>An <c>.obj</c> file on disk; its <c>.mtl</c> and textures are looked up beside it.</summary>
    public static ConvertedModelFile FromFile(string objPath, IImageDecoder? decoder, string scratchDir)
    {
        ArgumentNullException.ThrowIfNull(objPath);
        var folder = Path.GetDirectoryName(Path.GetFullPath(objPath))!;
        byte[]? Open(string path)
        {
            try
            {
                var candidate = Path.IsPathRooted(path) ? path : Path.Combine(folder, path.Replace('/', Path.DirectorySeparatorChar));
                if (!File.Exists(candidate))
                {
                    candidate = Path.Combine(folder, Path.GetFileName(Normalise(path)));
                }

                return File.Exists(candidate) && new FileInfo(candidate).Length <= MaxEntryBytes ? File.ReadAllBytes(candidate) : null;
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException or ArgumentException)
            {
                return null;
            }
        }

        return Convert(Path.GetFileName(objPath), Open, decoder, scratchDir);
    }

    private static ConvertedModelFile Failed(string error) => new(null, [error], []);

    private static string Normalise(string path)
    {
        var normal = path.Replace('\\', '/').Trim();
        while (normal.StartsWith("./", StringComparison.Ordinal))
        {
            normal = normal[2..];
        }

        return normal;
    }

    private static string FolderOf(string path)
    {
        var slash = Normalise(path).LastIndexOf('/');
        return slash < 0 ? string.Empty : Normalise(path)[..(slash + 1)];
    }

    private sealed class Material(string name)
    {
        public string Name { get; } = name;

        public Vector3 Diffuse { get; set; } = new(0.8f);

        public float Alpha { get; set; } = 1;

        public float? Roughness { get; set; }

        public float? Shininess { get; set; }

        public float Metallic { get; set; }

        public string? Texture { get; set; }
    }

    private readonly record struct Corner(int Position, int Uv, int Normal);

    private sealed record Face(Corner[] Corners, int Material, int SmoothGroup);

    private static ConvertedModelFile Convert(string objName, Func<string, byte[]?> open, IImageDecoder? decoder, string scratchDir)
    {
        var errors = new List<string>();
        var warnings = new List<string>();
        var obj = open(objName);
        if (obj is null)
        {
            return Failed($"'{objName}' couldn't be read");
        }

        var positions = new List<Vector3>();
        var uvs = new List<Vector2>();
        var normals = new List<Vector3>();
        var faces = new List<Face>();
        var materials = new List<Material>();
        var materialIndex = new Dictionary<string, int>(StringComparer.Ordinal);
        var libraries = new Dictionary<string, Material>(StringComparer.Ordinal);
        var current = -1;
        var smooth = 0;
        var skipped = 0;
        var lineNumber = 0;
        foreach (var raw in Lines(obj))
        {
            lineNumber++;
            var line = StripComment(raw);
            if (line.Length == 0)
            {
                continue;
            }

            var (keyword, rest) = Split(line);
            switch (keyword)
            {
                case "v" when Floats(rest, 3) is { } v:
                    positions.Add(new Vector3(v[0], v[1], v[2]));
                    break;
                case "vt" when Floats(rest, 1) is { } t:
                    uvs.Add(new Vector2(t[0], t.Length > 1 ? t[1] : 0));
                    break;
                case "vn" when Floats(rest, 3) is { } n:
                    normals.Add(new Vector3(n[0], n[1], n[2]));
                    break;
                case "f":
                    if (current < 0)
                    {
                        current = MaterialFor("default");
                    }

                    if (FaceOf(rest, positions.Count, uvs.Count, normals.Count) is { } corners)
                    {
                        faces.Add(new Face(corners, current, smooth));
                    }
                    else
                    {
                        skipped++;
                    }

                    break;
                case "usemtl":
                    current = MaterialFor(rest.Trim());
                    break;
                case "mtllib":
                    LoadLibraries(rest.Trim());
                    break;
                case "s":
                    var group = rest.Trim();
                    smooth = group is "off" or "0" ? 0 : int.TryParse(group, NumberStyles.Integer, CultureInfo.InvariantCulture, out var g) ? g : 1;
                    break;
                case "v" or "vt" or "vn":
                    errors.Add(string.Create(CultureInfo.InvariantCulture, $"'{objName}' line {lineNumber}: '{keyword}' has too few numbers"));
                    break;
            }

            if (errors.Count > 5)
            {
                break;
            }
        }

        if (errors.Count > 0)
        {
            return new ConvertedModelFile(null, errors, warnings);
        }

        if (skipped > 0)
        {
            warnings.Add(string.Create(CultureInfo.InvariantCulture, $"{skipped} face(s) with fewer than 3 corners or indices out of range were left out"));
        }

        if (faces.Count == 0)
        {
            return new ConvertedModelFile(null, [$"'{objName}' has no faces"], warnings);
        }

        var builder = new GltfBuilder { Generator = "Odyssey Launcher (from OBJ)" };
        var textureCache = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        var gltfMaterials = new int[materials.Count];
        for (var m = 0; m < materials.Count; m++)
        {
            gltfMaterials[m] = AddMaterial(builder, materials[m]);
        }

        // A PS2 save icon (ps2iodb's zips: an .anim beside the OBJ, an iconsys.json) is the PS2's frame turned a half
        // turn about Z, so it stands up but faces -Z, as the PS2 browser's camera looks along +Z. A half turn about Y
        // faces it +Z (A7) without mirroring it; the animation's frames are matched to the turned OBJ.
        var animationName = Path.ChangeExtension(objName, ".anim");
        var animationBytes = open(animationName);
        if (animationBytes is not null || open(FolderOf(objName) + "iconsys.json") is not null)
        {
            TurnAboutY(positions);
            TurnAboutY(normals);
        }

        var animation = animationBytes is { } animationFile
            ? ShapeAnimation.Read(animationFile, positions, Path.GetFileName(animationName), warnings)
            : null;

        var primitives = new List<GltfPrimitive>();
        for (var m = 0; m < materials.Count; m++)
        {
            if (BuildPrimitive(faces, m, positions, uvs, normals, gltfMaterials[m], animation) is { } primitive)
            {
                primitives.Add(primitive);
            }
        }

        var mesh = builder.AddMesh(Path.GetFileNameWithoutExtension(objName), primitives);
        var node = builder.AddNode(Path.GetFileNameWithoutExtension(objName), mesh);
        if (animation is not null)
        {
            builder.AddAnimation(ModelClips.Names[(int)ModelClip.Focused], [new GltfChannel(node, "weights", animation.Times, animation.Weights)]);
        }

        return new ConvertedModelFile(builder.ToGlb(), [], warnings);

        int MaterialFor(string name)
        {
            if (name.Length == 0)
            {
                name = "default";
            }

            if (!materialIndex.TryGetValue(name, out var index))
            {
                index = materials.Count;
                materials.Add(libraries.TryGetValue(name, out var known) ? known : new Material(name));
                materialIndex[name] = index;
                if (known is null && name != "default" && libraries.Count > 0)
                {
                    warnings.Add($"the material '{name}' isn't in the .mtl file, so it's plain grey");
                }
            }

            return index;
        }

        void LoadLibraries(string names)
        {
            // One file whose name has spaces (as Blender writes it), or several separated by spaces (as the spec has it).
            var folder = FolderOf(objName);
            string[] candidates = open(folder + names) is not null ? [names] : names.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            var found = 0;
            foreach (var name in candidates)
            {
                var path = folder + name;
                if (open(path) is not { } mtl)
                {
                    continue;
                }

                found++;
                foreach (var material in ParseMtl(mtl, FolderOf(path)))
                {
                    libraries.TryAdd(material.Name, material);
                }
            }

            if (found == 0)
            {
                warnings.Add($"the material file '{names}' isn't there, so its materials are plain grey");
            }

            // Materials used before their library was named pick up its values now.
            for (var i = 0; i < materials.Count; i++)
            {
                if (libraries.TryGetValue(materials[i].Name, out var known))
                {
                    materials[i] = known;
                }
            }
        }

        int AddMaterial(GltfBuilder gltf, Material material)
        {
            var texture = -1;
            if (material.Texture is { } file)
            {
                if (!textureCache.TryGetValue(file, out texture))
                {
                    texture = AddTexture(gltf, file);
                    textureCache[file] = texture;
                }
            }

            var roughness = material.Roughness ?? (material.Shininess is { } ns ? MathF.Sqrt(2 / (Math.Max(ns, 0) + 2)) : 0.6f);
            var slot = Theming.MediaSlots.OfMaterial(material.Name) >= 0;

            // A slot's colour multiplies the art it shows, so it's white (A7); a textured material's is the texture's.
            var colour = slot || texture >= 0 ? Vector3.One : material.Diffuse;
            return gltf.AddMaterial(material.Name, new Vector4(colour, Math.Clamp(material.Alpha, 0, 1)),
                Math.Clamp(roughness, 0.04f, 1), Math.Clamp(material.Metallic, 0, 1), texture);
        }

        int AddTexture(GltfBuilder gltf, string file)
        {
            if (open(file) is not { } bytes)
            {
                warnings.Add($"the texture '{file}' isn't there, so its material shows its colour");
                return -1;
            }

            if (bytes.AsSpan().StartsWith((ReadOnlySpan<byte>)[0x89, (byte)'P', (byte)'N', (byte)'G']))
            {
                return gltf.AddImage(bytes, "image/png");
            }

            if (bytes.AsSpan().StartsWith((ReadOnlySpan<byte>)[0xFF, 0xD8, 0xFF]))
            {
                return gltf.AddImage(bytes, "image/jpeg");
            }

            // WebP and BMP are converted to PNG by the OS's decoder; glTF only carries PNG and JPEG.
            if (decoder is not null && SizeOf(bytes) is { } size && Transcode(bytes, size, file, decoder, scratchDir) is { } png)
            {
                return gltf.AddImage(png, "image/png");
            }

            warnings.Add($"the texture '{file}' isn't a PNG or JPEG{(decoder is null ? string.Empty : ", WebP or BMP")}, so its material shows its colour");
            return -1;
        }
    }

    private static GltfPrimitive? BuildPrimitive(List<Face> faces, int material, List<Vector3> positions, List<Vector2> uvs, List<Vector3> normals, int gltfMaterial, ShapeAnimation? animation)
    {
        // Smooth normals per (position, smoothing group), for corners without their own.
        var smoothNormals = new Dictionary<(int Position, int Group), Vector3>();
        foreach (var face in faces)
        {
            if (face.Material != material || face.SmoothGroup == 0)
            {
                continue;
            }

            var n = FaceNormal(face, positions);
            foreach (var corner in face.Corners)
            {
                if (corner.Normal < 0)
                {
                    var key = (corner.Position, face.SmoothGroup);
                    smoothNormals[key] = smoothNormals.GetValueOrDefault(key) + n;
                }
            }
        }

        var vertexOf = new Dictionary<(Corner, int Group, int Face), int>();
        var outPositions = new List<Vector3>();
        var outNormals = new List<Vector3>();
        var outUvs = new List<Vector2>();
        var sources = new List<int>();
        var indices = new List<int>();
        var hasUvs = false;
        for (var f = 0; f < faces.Count; f++)
        {
            var face = faces[f];
            if (face.Material != material)
            {
                continue;
            }

            var flat = FaceNormal(face, positions);
            var corners = new int[face.Corners.Length];
            for (var c = 0; c < corners.Length; c++)
            {
                var corner = face.Corners[c];

                // A flat-shaded corner without a normal is its own vertex, so its face's normal isn't shared.
                var ownFace = corner.Normal < 0 && face.SmoothGroup == 0 ? f : -1;
                var key = (corner, face.SmoothGroup, ownFace);
                if (!vertexOf.TryGetValue(key, out var vertex))
                {
                    vertex = outPositions.Count;
                    vertexOf[key] = vertex;
                    outPositions.Add(positions[corner.Position]);
                    sources.Add(corner.Position);
                    var normal = corner.Normal >= 0 ? normals[corner.Normal]
                        : face.SmoothGroup != 0 ? smoothNormals[(corner.Position, face.SmoothGroup)]
                        : flat;
                    outNormals.Add(normal.LengthSquared() > 0 ? Vector3.Normalize(normal) : Vector3.UnitY);
                    if (corner.Uv >= 0)
                    {
                        hasUvs = true;
                        outUvs.Add(new Vector2(uvs[corner.Uv].X, 1 - uvs[corner.Uv].Y));
                    }
                    else
                    {
                        outUvs.Add(Vector2.Zero);
                    }
                }

                corners[c] = vertex;
            }

            for (var c = 1; c < corners.Length - 1; c++)
            {
                indices.Add(corners[0]);
                indices.Add(corners[c]);
                indices.Add(corners[c + 1]);
            }
        }

        if (indices.Count == 0)
        {
            return null;
        }

        // A morph target moves each vertex from the OBJ's position to the shape's (normals stay the OBJ's).
        Vector3[][]? targets = null;
        if (animation is not null)
        {
            targets = new Vector3[animation.Shapes.Count][];
            for (var t = 0; t < targets.Length; t++)
            {
                var shape = animation.Shapes[t];
                targets[t] = new Vector3[sources.Count];
                for (var v = 0; v < sources.Count; v++)
                {
                    targets[t][v] = shape[sources[v]] - positions[sources[v]];
                }
            }
        }

        return new GltfPrimitive([.. outPositions], [.. outNormals], hasUvs ? [.. outUvs] : null, [.. indices], gltfMaterial, targets);
    }

    /// <summary>A half turn about +Y: x and z negated. A rotation, so faces keep their winding.</summary>
    private static void TurnAboutY(List<Vector3> vectors)
    {
        for (var i = 0; i < vectors.Count; i++)
        {
            vectors[i] = new Vector3(-vectors[i].X, vectors[i].Y, -vectors[i].Z);
        }
    }

    /// <summary>Newell's method, so a polygon that isn't quite flat still gets a sensible normal.</summary>
    private static Vector3 FaceNormal(Face face, List<Vector3> positions)
    {
        var normal = Vector3.Zero;
        for (var i = 0; i < face.Corners.Length; i++)
        {
            var a = positions[face.Corners[i].Position];
            var b = positions[face.Corners[(i + 1) % face.Corners.Length].Position];
            normal += new Vector3((a.Y - b.Y) * (a.Z + b.Z), (a.Z - b.Z) * (a.X + b.X), (a.X - b.X) * (a.Y + b.Y));
        }

        return normal;
    }

    /// <summary>A face's corners (<c>v</c>, <c>v/vt</c>, <c>v//vn</c>, <c>v/vt/vn</c>; negative indices count back), or null.</summary>
    private static Corner[]? FaceOf(string rest, int positions, int uvs, int normals)
    {
        var tokens = rest.Split((char[])[' ', '\t'], StringSplitOptions.RemoveEmptyEntries);
        if (tokens.Length < 3)
        {
            return null;
        }

        var corners = new Corner[tokens.Length];
        for (var i = 0; i < tokens.Length; i++)
        {
            var parts = tokens[i].Split('/');
            var position = Index(parts[0], positions);
            var uv = parts.Length > 1 && parts[1].Length > 0 ? Index(parts[1], uvs) : -1;
            var normal = parts.Length > 2 && parts[2].Length > 0 ? Index(parts[2], normals) : -1;
            if (position < 0 || (parts.Length > 1 && parts[1].Length > 0 && uv < 0) || (parts.Length > 2 && parts[2].Length > 0 && normal < 0))
            {
                return null;
            }

            corners[i] = new Corner(position, uv, normal);
        }

        return corners;

        static int Index(string token, int count)
        {
            if (!int.TryParse(token, NumberStyles.Integer, CultureInfo.InvariantCulture, out var index) || index == 0)
            {
                return -1;
            }

            var zeroBased = index > 0 ? index - 1 : count + index;
            return zeroBased >= 0 && zeroBased < count ? zeroBased : -1;
        }
    }

    private static List<Material> ParseMtl(byte[] mtl, string folder)
    {
        var materials = new List<Material>();
        Material? current = null;
        foreach (var raw in Lines(mtl))
        {
            var line = StripComment(raw);
            if (line.Length == 0)
            {
                continue;
            }

            var (keyword, rest) = Split(line);
            if (keyword == "newmtl")
            {
                current = new Material(rest.Trim());
                materials.Add(current);
                continue;
            }

            if (current is null)
            {
                continue;
            }

            switch (keyword.ToLowerInvariant())
            {
                case "kd" when Floats(rest, 3) is { } kd:
                    current.Diffuse = new Vector3(kd[0], kd[1], kd[2]);
                    break;
                case "d" when Floats(rest, 1) is { } d:
                    current.Alpha = d[0];
                    break;
                case "tr" when Floats(rest, 1) is { } tr:
                    current.Alpha = 1 - tr[0];
                    break;
                case "ns" when Floats(rest, 1) is { } ns:
                    current.Shininess = ns[0];
                    break;
                case "pr" when Floats(rest, 1) is { } pr:
                    current.Roughness = pr[0];
                    break;
                case "pm" when Floats(rest, 1) is { } pm:
                    current.Metallic = pm[0];
                    break;
                case "map_kd" when TextureFile(rest) is { } file:
                    current.Texture = Path.IsPathRooted(file) ? file : folder + file;
                    break;
            }
        }

        return materials;
    }

    /// <summary>The file of a <c>map_Kd</c> line, after its options (<c>-s 1 1 1</c>, <c>-bm 0.5</c>, ...).</summary>
    private static string? TextureFile(string rest)
    {
        var tokens = rest.Split((char[])[' ', '\t'], StringSplitOptions.RemoveEmptyEntries);
        var i = 0;
        while (i < tokens.Length && tokens[i].StartsWith('-') && !float.TryParse(tokens[i], NumberStyles.Float, CultureInfo.InvariantCulture, out _))
        {
            i++;
            while (i < tokens.Length - 1 && (float.TryParse(tokens[i], NumberStyles.Float, CultureInfo.InvariantCulture, out _) || tokens[i] is "on" or "off"))
            {
                i++;
            }
        }

        return i < tokens.Length ? string.Join(' ', tokens[i..]) : null;
    }

    private static IEnumerable<string> Lines(byte[] bytes)
    {
        using var reader = new StreamReader(new MemoryStream(bytes, writable: false), Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        var pending = new StringBuilder();
        while (reader.ReadLine() is { } line)
        {
            // A trailing backslash continues the line.
            if (line.EndsWith('\\'))
            {
                pending.Append(line.AsSpan(0, line.Length - 1)).Append(' ');
                continue;
            }

            if (pending.Length > 0)
            {
                pending.Append(line);
                yield return pending.ToString();
                pending.Clear();
                continue;
            }

            yield return line;
        }
    }

    private static string StripComment(string line)
    {
        var hash = line.IndexOf('#', StringComparison.Ordinal);
        return (hash >= 0 ? line[..hash] : line).Trim();
    }

    private static (string Keyword, string Remainder) Split(string line)
    {
        var space = line.IndexOfAny([' ', '\t']);
        return space < 0 ? (line, string.Empty) : (line[..space], line[(space + 1)..]);
    }

    private static float[]? Floats(string rest, int minimum)
    {
        var tokens = rest.Split((char[])[' ', '\t'], StringSplitOptions.RemoveEmptyEntries);
        if (tokens.Length < minimum)
        {
            return null;
        }

        var values = new float[Math.Min(tokens.Length, 4)];
        for (var i = 0; i < values.Length; i++)
        {
            if (!float.TryParse(tokens[i], NumberStyles.Float, CultureInfo.InvariantCulture, out values[i]) || !float.IsFinite(values[i]))
            {
                return i >= minimum ? values[..i] : null;
            }
        }

        return values;
    }

    /// <summary>A WebP's size from its header, or a BMP's; null for anything else.</summary>
    private static (int Width, int Height)? SizeOf(byte[] bytes)
    {
        if (bytes.Length >= 26 && bytes[0] == 'B' && bytes[1] == 'M')
        {
            var width = BinaryPrimitives.ReadInt32LittleEndian(bytes.AsSpan(18));
            var height = Math.Abs(BinaryPrimitives.ReadInt32LittleEndian(bytes.AsSpan(22)));
            return width is > 0 and <= 16384 && height is > 0 and <= 16384 ? (width, height) : null;
        }

        using var stream = new MemoryStream(bytes, writable: false);
        return ImageHeaders.TryReadSize(stream, out var w, out var h) && w is > 0 and <= 16384 && h is > 0 and <= 16384 ? (w, h) : null;
    }

    private static byte[]? Transcode(byte[] bytes, (int Width, int Height) size, string name, IImageDecoder decoder, string scratchDir)
    {
        var scratch = Path.Combine(scratchDir, $"obj-{Guid.NewGuid():N}{Path.GetExtension(name)}");
        try
        {
            Directory.CreateDirectory(scratchDir);
            File.WriteAllBytes(scratch, bytes);
            var rgba = new byte[size.Width * size.Height * 4];
            return decoder.TryDecodeScaled(scratch, size.Width, size.Height, rgba, out _) ? PngEncoder.Encode(rgba, size.Width, size.Height) : null;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return null;
        }
        finally
        {
            try
            {
                File.Delete(scratch);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                // Harmless.
            }
        }
    }
}
