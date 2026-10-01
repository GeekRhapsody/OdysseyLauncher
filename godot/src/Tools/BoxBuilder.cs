using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Tools;

/// <summary>How a template's front face is divided between art and plain case.</summary>
public enum FrontSplit
{
    /// <summary>The whole front is the front slot.</summary>
    None,

    /// <summary>A strip on the spine side is plain case (a jewel case's hinge); the rest is the front slot.</summary>
    SpineStrip,

    /// <summary>The top part is the front slot (a label); the part below it is plain case.</summary>
    TopLabel,

    /// <summary>The top part is the front slot; the part below it is <see cref="BoxSpec.LowerSlot"/> (a screenshot panel).</summary>
    LowerPanel,
}

/// <summary>
/// One built-in model, in millimetres. The front outline is a rounded rectangle; the spine is the left side, as on a
/// case facing you. Materials are named after the media slot they show (A7): the front slot, <c>back</c>,
/// <c>spine</c>, and <c>case</c> for everything else.
/// </summary>
/// <param name="SpineRadius">Front-view corner radius on the spine side.</param>
/// <param name="OpeningRadius">Front-view corner radius on the opening side.</param>
/// <param name="Bevel">The chamfer between the front or back and the sides.</param>
/// <param name="SplitAt">
/// For <see cref="FrontSplit.SpineStrip"/>, the strip's width; for <see cref="FrontSplit.TopLabel"/>, the case part's
/// height; for <see cref="FrontSplit.LowerPanel"/>, the lower slot's height.
/// </param>
/// <param name="PrintedOpeningSide">The opening side shows the spine art too (a cardboard box printed on both sides).</param>
/// <param name="LowerSlot">For <see cref="FrontSplit.LowerPanel"/>, the lower part's slot.</param>
/// <param name="TestCardOnLowerSlot">Give the lower slot's material an authored texture (a test card), its last fallback.</param>
public sealed record BoxSpec(
    string Id,
    float Width,
    float Height,
    float Depth,
    float SpineRadius,
    float OpeningRadius,
    float Bevel,
    Color CaseColour,
    float CaseRoughness,
    float ArtRoughness,
    string FrontSlot = "cover",
    bool HasBackSlot = true,
    bool HasSpineSlot = true,
    FrontSplit Split = FrontSplit.None,
    float SplitAt = 0,
    bool PrintedOpeningSide = false,
    string? LowerSlot = null,
    bool TestCardOnLowerSlot = false);

/// <summary>
/// Builds a <see cref="BoxSpec"/> as an <see cref="ArrayMesh"/> with one surface per material, to the model spec (A7):
/// metres, +Y up, the front facing +Z, the origin at the bottom centre, the largest side 1 m, and each slot's
/// TEXCOORD_0 spanning 0..1 across its face, upright as seen from outside.
/// </summary>
public sealed class BoxBuilder
{
    private const int CornerSegments = 6;

    private readonly BoxSpec _spec;
    private readonly float _scale;
    private readonly Dictionary<string, Surface> _surfaces = new(StringComparer.Ordinal);
    private readonly List<string> _order = [];

    private BoxBuilder(BoxSpec spec)
    {
        _spec = spec;
        _scale = 1.0f / Math.Max(spec.Width, Math.Max(spec.Height, spec.Depth));
    }

    public static ArrayMesh Build(BoxSpec spec, out int triangles)
    {
        var builder = new BoxBuilder(spec);
        builder.BuildAll();
        return builder.ToMesh(out triangles);
    }

    /// <summary>A face's width over its height, for a slot material's <c>extras.aspect</c>.</summary>
    public static float SlotAspect(BoxSpec spec, string slot) => slot switch
    {
        // The spine's UVs span the straight wall: the depth less both chamfers, and the height less both corners.
        "spine" => (spec.Depth - 2 * spec.Bevel) / (spec.Height - 2 * spec.SpineRadius),
        "back" => spec.Width / spec.Height,
        _ when slot == spec.LowerSlot => spec.Width / spec.SplitAt,
        _ => spec.Split switch
        {
            FrontSplit.SpineStrip => (spec.Width - spec.SplitAt) / spec.Height,
            FrontSplit.TopLabel or FrontSplit.LowerPanel => spec.Width / (spec.Height - spec.SplitAt),
            _ => spec.Width / spec.Height,
        },
    };

    private void BuildAll()
    {
        var s = _spec;
        var halfDepth = s.Depth / 2;
        var outer = Outline(0);
        var inner = Outline(s.Bevel);

        // Front and back caps, inset by the bevel.
        FrontCap(inner, halfDepth);
        BackCap(inner, -halfDepth);

        // The chamfers from each cap out to the sides.
        Ring(inner, halfDepth, outer, halfDepth - s.Bevel, +1);
        Ring(outer, -halfDepth + s.Bevel, inner, -halfDepth, -1);

        // The sides.
        Walls(outer, halfDepth - s.Bevel, -halfDepth + s.Bevel);
    }

    // ---- Outline ----------------------------------------------------------------------------------

    /// <summary>A point on the front outline, with its outward normal and which side it belongs to.</summary>
    private readonly record struct OutlinePoint(Vector2 Position, Vector2 Normal, Side Side);

    private enum Side
    {
        Spine,
        Top,
        Opening,
        Bottom,
        Corner,
    }

    /// <summary>
    /// The rounded rectangle, inset by <paramref name="inset"/>, counter-clockwise seen from the front, starting at the
    /// bottom of the spine side. Every corner has the same number of points whatever its radius, so an inset outline
    /// pairs up with the outer one.
    /// </summary>
    private List<OutlinePoint> Outline(float inset)
    {
        var s = _spec;
        var left = -s.Width / 2 + inset;
        var right = s.Width / 2 - inset;
        var bottom = inset;
        var top = s.Height - inset;
        var spineRadius = Math.Max(s.SpineRadius - inset, 0.01f);
        var openingRadius = Math.Max(s.OpeningRadius - inset, 0.01f);
        var points = new List<OutlinePoint>();

        // Counter-clockwise from the front: bottom-right, top-right, top-left, bottom-left, with the spine on the left.
        Corner(new Vector2(right - openingRadius, bottom + openingRadius), openingRadius, -90);
        Corner(new Vector2(right - openingRadius, top - openingRadius), openingRadius, 0);
        Corner(new Vector2(left + spineRadius, top - spineRadius), spineRadius, 90);
        Corner(new Vector2(left + spineRadius, bottom + spineRadius), spineRadius, 180);
        return points;

        void Corner(Vector2 centre, float radius, float startDegrees)
        {
            for (var i = 0; i <= CornerSegments; i++)
            {
                var angle = Mathf.DegToRad(startDegrees + 90f * i / CornerSegments);
                var normal = new Vector2(MathF.Cos(angle), MathF.Sin(angle));
                points.Add(new OutlinePoint(centre + normal * radius, normal, Side.Corner));
            }
        }
    }

    /// <summary>Which side the straight edge from point i to i+1 is on.</summary>
    private static Side EdgeSide(List<OutlinePoint> outline, int i)
    {
        // Each corner contributes CornerSegments + 1 points; the edge from its last point to the next corner's first is straight.
        var perCorner = CornerSegments + 1;
        if (i % perCorner != perCorner - 1)
        {
            return Side.Corner;
        }

        return (i / perCorner) switch
        {
            0 => Side.Opening,
            1 => Side.Top,
            2 => Side.Spine,
            _ => Side.Bottom,
        };
    }

    // ---- Caps ----------------------------------------------------------------------------------------

    private void FrontCap(List<OutlinePoint> inner, float z)
    {
        var s = _spec;
        var polygon = new List<Vector2>(inner.Count);
        foreach (var point in inner)
        {
            polygon.Add(point.Position);
        }

        var left = -s.Width / 2;
        var right = s.Width / 2;
        switch (s.Split)
        {
            case FrontSplit.SpineStrip:
            {
                var split = left + s.SplitAt;
                Cap(Clip(polygon, split, keepAbove: false, vertical: true), z, Vector3.Back, "case", p => PlanarUv(p, left, split, 0, s.Height));
                Cap(Clip(polygon, split, keepAbove: true, vertical: true), z, Vector3.Back, s.FrontSlot, p => PlanarUv(p, split, right, 0, s.Height));
                break;
            }

            case FrontSplit.TopLabel or FrontSplit.LowerPanel:
            {
                var split = s.SplitAt;
                var lower = s.Split == FrontSplit.LowerPanel ? s.LowerSlot! : "case";
                Cap(Clip(polygon, split, keepAbove: true, vertical: false), z, Vector3.Back, s.FrontSlot, p => PlanarUv(p, left, right, split, s.Height));
                Cap(Clip(polygon, split, keepAbove: false, vertical: false), z, Vector3.Back, lower, p => PlanarUv(p, left, right, 0, split));
                break;
            }

            default:
                Cap(polygon, z, Vector3.Back, s.FrontSlot, p => PlanarUv(p, left, right, 0, s.Height));
                break;
        }
    }

    private void BackCap(List<OutlinePoint> inner, float z)
    {
        var s = _spec;
        var polygon = new List<Vector2>(inner.Count);

        // Counter-clockwise seen from behind is clockwise seen from the front.
        for (var i = inner.Count - 1; i >= 0; i--)
        {
            polygon.Add(inner[i].Position);
        }

        // Seen from behind, +X is on the left.
        Cap(polygon, z, Vector3.Forward, s.HasBackSlot ? "back" : "case", p => PlanarUv(p, s.Width / 2, -s.Width / 2, 0, s.Height));
    }

    /// <summary>u across the face from <paramref name="uFrom"/> to <paramref name="uTo"/>; v from the top down.</summary>
    private static Vector2 PlanarUv(Vector2 p, float uFrom, float uTo, float bottom, float top) =>
        new((p.X - uFrom) / (uTo - uFrom), (top - p.Y) / (top - bottom));

    /// <summary>A convex polygon, counter-clockwise seen from outside, as a fan.</summary>
    private void Cap(List<Vector2> polygon, float z, Vector3 normal, string material, Func<Vector2, Vector2> uv)
    {
        if (polygon.Count < 3)
        {
            return;
        }

        var surface = SurfaceFor(material);
        var first = surface.Vertices.Count;
        foreach (var p in polygon)
        {
            surface.Add(Metres(p.X, p.Y, z), normal, uv(p));
        }

        for (var i = 1; i < polygon.Count - 1; i++)
        {
            surface.Triangle(first, first + i, first + i + 1);
        }
    }

    /// <summary>Sutherland–Hodgman against one axis-aligned line: the part at or above (or right of) it, or below.</summary>
    private static List<Vector2> Clip(List<Vector2> polygon, float at, bool keepAbove, bool vertical)
    {
        var result = new List<Vector2>();
        for (var i = 0; i < polygon.Count; i++)
        {
            var a = polygon[i];
            var b = polygon[(i + 1) % polygon.Count];
            var da = (vertical ? a.X : a.Y) - at;
            var db = (vertical ? b.X : b.Y) - at;
            var inA = keepAbove ? da >= 0 : da <= 0;
            var inB = keepAbove ? db >= 0 : db <= 0;
            if (inA)
            {
                result.Add(a);
            }

            if (inA != inB)
            {
                result.Add(a + (b - a) * (da / (da - db)));
            }
        }

        return result;
    }

    // ---- Chamfers and sides ----------------------------------------------------------------------------

    /// <summary>A band between two outlines of the same length, the first nearer the front.</summary>
    private void Ring(List<OutlinePoint> front, float frontZ, List<OutlinePoint> back, float backZ, float facing)
    {
        var surface = SurfaceFor("case");
        for (var i = 0; i < front.Count; i++)
        {
            var j = (i + 1) % front.Count;
            var n0 = new Vector3(front[i].Normal.X, front[i].Normal.Y, facing).Normalized();
            var n1 = new Vector3(front[j].Normal.X, front[j].Normal.Y, facing).Normalized();
            var v = surface.Vertices.Count;
            surface.Add(Metres(front[i].Position.X, front[i].Position.Y, frontZ), n0, new Vector2(0, 0));
            surface.Add(Metres(front[j].Position.X, front[j].Position.Y, frontZ), n1, new Vector2(1, 0));
            surface.Add(Metres(back[j].Position.X, back[j].Position.Y, backZ), n1, new Vector2(1, 1));
            surface.Add(Metres(back[i].Position.X, back[i].Position.Y, backZ), n0, new Vector2(0, 1));

            // Front outline runs counter-clockwise seen from the front; seen from outside the band, i -> j is to the right.
            surface.Triangle(v, v + 3, v + 2);
            surface.Triangle(v, v + 2, v + 1);
        }
    }

    private void Walls(List<OutlinePoint> outline, float frontZ, float backZ)
    {
        var s = _spec;
        var straightTop = s.Height - s.SpineRadius;
        var straightBottom = s.SpineRadius;
        for (var i = 0; i < outline.Count; i++)
        {
            var j = (i + 1) % outline.Count;
            var side = EdgeSide(outline, i);
            var a = outline[i];
            var b = outline[j];
            string material;
            Vector2 uvA0, uvB0, uvA1, uvB1; // (point, front), (point, back)
            if (side == Side.Spine && s.HasSpineSlot)
            {
                // Seen from the left, the front is on the right: u runs from the back edge to the front edge.
                material = "spine";
                var va = (straightTop - a.Position.Y) / (straightTop - straightBottom);
                var vb = (straightTop - b.Position.Y) / (straightTop - straightBottom);
                (uvA0, uvA1) = (new Vector2(1, va), new Vector2(0, va));
                (uvB0, uvB1) = (new Vector2(1, vb), new Vector2(0, vb));
            }
            else if (side == Side.Opening && s.PrintedOpeningSide && s.HasSpineSlot)
            {
                // Seen from the right, the front is on the left.
                material = "spine";
                var top = s.Height - s.OpeningRadius;
                var bottom = s.OpeningRadius;
                var va = (top - a.Position.Y) / (top - bottom);
                var vb = (top - b.Position.Y) / (top - bottom);
                (uvA0, uvA1) = (new Vector2(0, va), new Vector2(1, va));
                (uvB0, uvB1) = (new Vector2(0, vb), new Vector2(1, vb));
            }
            else
            {
                material = "case";
                (uvA0, uvA1, uvB0, uvB1) = (new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 0), new Vector2(1, 1));
            }

            var surface = SurfaceFor(material);
            var v = surface.Vertices.Count;
            var na = new Vector3(a.Normal.X, a.Normal.Y, 0);
            var nb = new Vector3(b.Normal.X, b.Normal.Y, 0);
            surface.Add(Metres(a.Position.X, a.Position.Y, frontZ), na, uvA0);
            surface.Add(Metres(b.Position.X, b.Position.Y, frontZ), nb, uvB0);
            surface.Add(Metres(b.Position.X, b.Position.Y, backZ), nb, uvB1);
            surface.Add(Metres(a.Position.X, a.Position.Y, backZ), na, uvA1);
            surface.Triangle(v, v + 3, v + 2);
            surface.Triangle(v, v + 2, v + 1);
        }
    }

    // ---- Output ------------------------------------------------------------------------------------------

    private Vector3 Metres(float x, float y, float z) => new(x * _scale, y * _scale, z * _scale);

    private Surface SurfaceFor(string material)
    {
        if (!_surfaces.TryGetValue(material, out var surface))
        {
            surface = new Surface();
            _surfaces[material] = surface;
            _order.Add(material);
        }

        return surface;
    }

    private ArrayMesh ToMesh(out int triangles)
    {
        var s = _spec;
        var mesh = new ArrayMesh();
        triangles = 0;

        // Slots first, then the case, so every template lists its materials in the same order.
        _order.Sort((a, b) => Rank(a).CompareTo(Rank(b)));
        foreach (var name in _order)
        {
            var surface = _surfaces[name];
            var arrays = new Godot.Collections.Array();
            arrays.Resize((int)Mesh.ArrayType.Max);
            arrays[(int)Mesh.ArrayType.Vertex] = surface.Vertices.ToArray();
            arrays[(int)Mesh.ArrayType.Normal] = surface.Normals.ToArray();
            arrays[(int)Mesh.ArrayType.TexUV] = surface.Uvs.ToArray();
            arrays[(int)Mesh.ArrayType.Index] = surface.Indices.ToArray();
            mesh.AddSurfaceFromArrays(Mesh.PrimitiveType.Triangles, arrays);
            triangles += surface.Indices.Count / 3;

            var isSlot = name != "case";
            var material = new StandardMaterial3D
            {
                ResourceName = name,
                AlbedoColor = isSlot ? Colors.White : s.CaseColour,
                Roughness = isSlot ? s.ArtRoughness : s.CaseRoughness,
                Metallic = 0,
            };
            if (name == s.LowerSlot && s.TestCardOnLowerSlot)
            {
                material.AlbedoTexture = ImageTexture.CreateFromImage(TestCard());
            }

            if (isSlot)
            {
                // The face's aspect ratio (A7), so a loader needn't measure the slot mesh.
                material.SetMeta("extras", new Godot.Collections.Dictionary { ["aspect"] = SlotAspect(s, name) });
            }

            var index = mesh.GetSurfaceCount() - 1;
            mesh.SurfaceSetMaterial(index, material);
            mesh.SurfaceSetName(index, name);
        }

        return mesh;

        static int Rank(string name) => name switch
        {
            "cover" or "label" => 0,
            "spine" => 1,
            "back" => 2,
            "case" => 4,
            _ => 3,
        };
    }

    /// <summary>
    /// A 16:9 test card: seven colour bars over a strip of greys and a checker, so a slot showing its authored texture
    /// is obvious in a capture.
    /// </summary>
    public static Image TestCard()
    {
        const int Width = 256;
        const int Height = 144;
        Color[] bars = [new("#C0C0C0"), new("#C0C000"), new("#00C0C0"), new("#00C000"), new("#C000C0"), new("#C00000"), new("#0000C0")];
        var image = Image.CreateEmpty(Width, Height, false, Image.Format.Rgb8);
        for (var y = 0; y < Height; y++)
        {
            for (var x = 0; x < Width; x++)
            {
                Color colour;
                if (y < Height * 2 / 3)
                {
                    colour = bars[x * bars.Length / Width];
                }
                else if (y < Height * 5 / 6)
                {
                    colour = Color.FromHsv(0, 0, x * 5 / Width / 4f);
                }
                else
                {
                    colour = (x / 16 + y / 12) % 2 == 0 ? Colors.White : new Color("#101010");
                }

                image.SetPixel(x, y, colour);
            }
        }

        image.GenerateMipmaps();
        return image;
    }

    private sealed class Surface
    {
        public List<Vector3> Vertices { get; } = [];

        public List<Vector3> Normals { get; } = [];

        public List<Vector2> Uvs { get; } = [];

        public List<int> Indices { get; } = [];

        public void Add(Vector3 position, Vector3 normal, Vector2 uv)
        {
            Vertices.Add(position);
            Normals.Add(normal);
            Uvs.Add(new Vector2(Math.Clamp(uv.X, 0, 1), Math.Clamp(uv.Y, 0, 1)));
        }

        /// <summary>Counter-clockwise seen from outside; Godot's front faces wind clockwise, so it's stored reversed.</summary>
        public void Triangle(int a, int b, int c)
        {
            Indices.Add(a);
            Indices.Add(c);
            Indices.Add(b);
        }
    }
}
