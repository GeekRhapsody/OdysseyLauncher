using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// The built-in theme's television template (<c>crt_tv_90s</c>): a 1990s colour CRT, about a 21-inch set. A charcoal
/// cabinet with rounded corners and a chamfered front edge; the tube's face, bulging a little, set back in a recess,
/// is the <c>screenshot</c> slot; under it, a silver badge, two speaker grilles, a control flap with the power button
/// and the standby light; behind, the tube's housing tapers to the back, with vents on top; it stands on a low swivel
/// base. The theme plays the focused game's video on the screen (A6 Game videos).
/// <para>
/// Built in millimetres, front facing +Z, then fitted to the model spec (A7: standing on y = 0, centred, the largest side
/// 1 m). Two materials, as the arcade cabinet's (<see cref="ArcadeCabinetBuilder"/>): the screen, whose authored texture
/// is a switched-off tube, and <c>case</c>, whose colours come from a small palette texture. No clips: the grid's
/// procedural motion animates it, and it stays batched.
/// </para>
/// </summary>
public sealed class CrtTvBuilder
{
    // The cabinet's front: its width, its bottom and top (above the base), its corners' radius and the front edge's chamfer.
    private const float Width = 600;
    private const float Bottom = 26;
    private const float Top = 521;
    private const float Radius = 40;
    private const float Chamfer = 8;

    // The cabinet runs straight back this far, then the tube's housing tapers to the back.
    private const float FrontDepth = 110;
    private const float Back = -440;
    private const float BackWidth = 440;
    private const float BackHeight = 380;
    private const float BackCentreY = 300;
    private const float BackRadius = 50;

    // The tube's visible face, 4:3, its middle bulging forwards; the recess round it slopes back from the front.
    private const float ScreenCentreY = 316;
    private const float ScreenWidth = 444;
    private const float ScreenHeight = 334;
    private const float ScreenZ = -15;
    private const float Bulge = 14;
    private const float OpeningWidth = 462;
    private const float OpeningHeight = 352;
    private const float OpeningRadius = 26;
    private const float RecessWidth = 440;
    private const float RecessHeight = 330;
    private const float RecessRadius = 14;
    private const float RecessDepth = 14;

    // Each rounded corner's segments, and the screen's grid.
    private const int CornerSegments = 6;
    private const int ScreenColumns = 16;
    private const int ScreenRows = 12;

    /// <summary>The palette's colours (sRGB), one 16-pixel swatch each in a 4 x 4 grid.</summary>
    private enum Paint
    {
        Cabinet,
        Housing,
        Recess,
        Slot,
        Silver,
        Button,
        Light,
        Base,
    }

    private static readonly Color[] Palette =
    [
        new("#2C2D32"), // the cabinet's charcoal plastic
        new("#25262A"), // the tube's housing, a shade darker
        new("#151619"), // the recess round the screen
        new("#0B0B0D"), // grille and vent slots, the flap's groove
        new("#B4B8BF"), // the badge
        new("#3C3D43"), // the power button and the flap
        new("#D8261E"), // the standby light
        new("#1D1E21"), // the swivel base
    ];

    private const int PaletteSwatch = 16;
    private const int PaletteColumns = 4;

    private readonly Dictionary<string, Surface> _surfaces = new(StringComparer.Ordinal);
    private readonly List<string> _order = [];

    /// <summary>The screen's width over its height, for its <c>extras.aspect</c> (the face is curved: measuring its bounds would do too, but the slot's own number is surer).</summary>
    public const float ScreenAspect = ScreenWidth / ScreenHeight;

    private CrtTvBuilder()
    {
    }

    public static ArrayMesh Build(out int triangles)
    {
        var builder = new CrtTvBuilder();
        builder.BuildAll();
        return builder.ToMesh(out triangles);
    }

    private void BuildAll()
    {
        Cabinet();
        Screen();
        Controls();
        Housing();
        SwivelBase();
    }

    // ---- The parts -----------------------------------------------------------------------------------------

    /// <summary>
    /// The front: the face between the chamfer and the screen's opening, the chamfer, and the straight sides back to
    /// where the housing starts; then the recess from the opening back to the tube's face.
    /// </summary>
    private void Cabinet()
    {
        var centreY = (Bottom + Top) / 2;
        var height = Top - Bottom;
        var face = RoundedRect(0, centreY, Width - 2 * Chamfer, height - 2 * Chamfer, Radius - Chamfer, 0);
        var edge = RoundedRect(0, centreY, Width, height, Radius, -Chamfer);
        var side = RoundedRect(0, centreY, Width, height, Radius, -FrontDepth);
        var opening = RoundedRect(0, ScreenCentreY, OpeningWidth, OpeningHeight, OpeningRadius, 0);
        var recess = RoundedRect(0, ScreenCentreY, RecessWidth, RecessHeight, RecessRadius, -RecessDepth);

        Ring(Paint.Cabinet, face, opening, Vector3.Back);
        Ring(Paint.Cabinet, edge, face, null);
        Ring(Paint.Cabinet, side, edge, null);
        Ring(Paint.Recess, opening, recess, null, inwards: true);
    }

    /// <summary>
    /// The tube's face: a grid bulging forwards in the middle and flat at its edges (a cushion), a little larger than
    /// the recess's back edge and just behind it, so the recess rounds its corners off as a real tube's mask does and
    /// no edge pokes through it.
    /// </summary>
    private void Screen()
    {
        var s = SurfaceFor("screenshot");
        var first = s.Count;
        var halfWidth = ScreenWidth / 2;
        var halfHeight = ScreenHeight / 2;

        // z = ScreenZ + Bulge (1 - a²)(1 - b²), with a and b from -1 to 1 across the face; smooth normals from its slope.
        for (var row = 0; row <= ScreenRows; row++)
        {
            for (var column = 0; column <= ScreenColumns; column++)
            {
                var u = (float)column / ScreenColumns;
                var v = (float)row / ScreenRows;
                var a = 2 * u - 1;
                var b = 1 - 2 * v;
                var z = ScreenZ + Bulge * (1 - a * a) * (1 - b * b);
                var slopeX = Bulge * -2 * a / halfWidth * (1 - b * b);
                var slopeY = Bulge * (1 - a * a) * -2 * b / halfHeight;
                var position = new Vector3(a * halfWidth, ScreenCentreY + b * halfHeight, z);
                s.Add(position, new Vector3(-slopeX, -slopeY, 1).Normalized(), new Vector2(u, v));
            }
        }

        for (var row = 0; row < ScreenRows; row++)
        {
            for (var column = 0; column < ScreenColumns; column++)
            {
                var a = first + row * (ScreenColumns + 1) + column;
                var b = a + 1;
                var c = a + ScreenColumns + 2;
                var d = a + ScreenColumns + 1;
                s.Facing(a, b, c, Vector3.Back);
                s.Facing(a, c, d, Vector3.Back);
            }
        }
    }

    /// <summary>Under the screen: the badge, a speaker grille each side, and the control flap with the power button and light.</summary>
    private void Controls()
    {
        const float Proud = 0.6f;

        // The maker's badge, centred under the screen.
        var badgeY = ScreenCentreY - OpeningHeight / 2 - 22;
        Panel(Paint.Silver, new Vector3(0, badgeY, Proud), 84, 12);

        // The grilles: rows of slots, each side of the flap.
        foreach (var sign in (ReadOnlySpan<float>)[-1f, 1f])
        {
            for (var i = 0; i < 6; i++)
            {
                Panel(Paint.Slot, new Vector3(sign * 212, 54 + i * 10, Proud), 116, 4);
            }
        }

        // The control flap: a panel with a groove round it, the power button on its left and the light beside it.
        var flapY = 76f;
        Panel(Paint.Slot, new Vector3(0, flapY, Proud), 214, 34);
        Panel(Paint.Button, new Vector3(0, flapY, Proud + 0.4f), 208, 28);
        Box(Paint.Button, new Vector3(-84, flapY - 8, Proud), new Vector3(-58, flapY + 8, Proud + 5));
        Panel(Paint.Light, new Vector3(-44, flapY, Proud + 0.8f), 6, 6);

        // Four small buttons along the flap's right, flush with it.
        for (var i = 0; i < 4; i++)
        {
            Panel(Paint.Slot, new Vector3(30 + i * 20, flapY, Proud + 0.8f), 12, 6);
        }
    }

    /// <summary>The tube's housing, tapering from the cabinet's sides to the back, with vents on its top and a back panel.</summary>
    private void Housing()
    {
        var centreY = (Bottom + Top) / 2;
        var side = RoundedRect(0, centreY, Width, Top - Bottom, Radius, -FrontDepth);
        var back = RoundedRect(0, BackCentreY, BackWidth, BackHeight, BackRadius, Back);
        Ring(Paint.Housing, back, side, null);
        Cap(Paint.Housing, back, Vector3.Forward);

        // Vents along the top's slope: dark slots just above it, across most of its flat width there.
        var topFront = new Vector3(0, Top, -FrontDepth);
        var topBack = new Vector3(0, BackCentreY + BackHeight / 2, Back);
        var slope = (topBack - topFront).Normalized();
        var normal = Vector3.Right.Cross(slope).Normalized();
        if (normal.Y < 0)
        {
            normal = -normal;
        }

        for (var i = 0; i < 8; i++)
        {
            var t = 0.12f + 0.76f * (i + 0.5f) / 8;
            var at = topFront + (topBack - topFront) * t + normal * 0.8f;
            var flat = Mathf.Lerp(Width / 2 - Radius, BackWidth / 2 - BackRadius, t);
            var halfWidth = Vector3.Right * (flat * 0.8f);
            var halfLength = slope * 6;
            Oriented(Paint.Slot, normal, at - halfWidth - halfLength, at + halfWidth - halfLength, at + halfWidth + halfLength, at - halfWidth + halfLength);
        }
    }

    /// <summary>A low turntable the set stands on, set back under its middle.</summary>
    private void SwivelBase()
    {
        Box(Paint.Base, new Vector3(-190, 0, -300), new Vector3(190, Bottom, -40));
        Box(Paint.Base, new Vector3(-210, 0, -320), new Vector3(210, 6, -20));
    }

    // ---- Primitives ----------------------------------------------------------------------------------------

    /// <summary>A rounded rectangle's outline at depth <paramref name="z"/>, clockwise seen from the front, starting at the top right corner.</summary>
    private static Vector3[] RoundedRect(float centreX, float centreY, float width, float height, float radius, float z)
    {
        var points = new Vector3[4 * (CornerSegments + 1)];
        var half = new Vector2(width / 2 - radius, height / 2 - radius);
        (float X, float Y, float Start)[] corners = [(1, 1, 90), (1, -1, 0), (-1, -1, -90), (-1, 1, -180)];
        var n = 0;
        foreach (var (sx, sy, start) in corners)
        {
            var cx = centreX + sx * half.X;
            var cy = centreY + sy * half.Y;
            for (var i = 0; i <= CornerSegments; i++)
            {
                var angle = Mathf.DegToRad(start - 90f * i / CornerSegments);
                points[n++] = new Vector3(cx + MathF.Cos(angle) * radius, cy + MathF.Sin(angle) * radius, z);
            }
        }

        return points;
    }

    /// <summary>
    /// The band between two outlines with as many points: a quad per pair of neighbours, facing <paramref name="facing"/>,
    /// or, when that's null, away from the band's middle line (a side wall, a chamfer, a taper), or towards it when
    /// <paramref name="inwards"/> (a recess's walls).
    /// </summary>
    private void Ring(Paint colour, Vector3[] outer, Vector3[] inner, Vector3? facing, bool inwards = false)
    {
        var middle = Vector3.Zero;
        foreach (var p in inner)
        {
            middle += p;
        }

        middle /= inner.Length;
        for (var i = 0; i < outer.Length; i++)
        {
            var j = (i + 1) % outer.Length;
            var outward = facing ?? Outward(outer[i], outer[j], inner[j], inner[i], middle) * (inwards ? -1 : 1);
            Oriented(colour, outward, outer[i], outer[j], inner[j], inner[i]);
        }
    }

    /// <summary>A quad's normal turned away from <paramref name="middle"/> (measured across x and y only, along the band's axis).</summary>
    private static Vector3 Outward(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 middle)
    {
        var normal = (b - a).Cross(d - a).Normalized();
        var centre = (a + b + c + d) / 4;
        var away = new Vector3(centre.X - middle.X, centre.Y - middle.Y, 0);
        if (normal.Dot(away) < 0 || (away.LengthSquared() < 1e-6f && normal.Z < 0))
        {
            normal = -normal;
        }

        return normal;
    }

    /// <summary>A flat, convex outline filled as a fan, facing <paramref name="facing"/>.</summary>
    private void Cap(Paint colour, Vector3[] outline, Vector3 facing)
    {
        for (var i = 1; i < outline.Length - 1; i++)
        {
            Triangle(colour, facing, outline[0], outline[i], outline[i + 1]);
        }
    }

    /// <summary>A flat rectangle facing +Z, centred on <paramref name="centre"/>.</summary>
    private void Panel(Paint colour, Vector3 centre, float width, float height)
    {
        var x = Vector3.Right * (width / 2);
        var y = Vector3.Up * (height / 2);
        Oriented(colour, Vector3.Back, centre - x + y, centre + x + y, centre + x - y, centre - x - y);
    }

    /// <summary>An axis-aligned box between two corners.</summary>
    private void Box(Paint colour, Vector3 min, Vector3 max)
    {
        Vector3 P(int x, int y, int z) => new(x == 0 ? min.X : max.X, y == 0 ? min.Y : max.Y, z == 0 ? min.Z : max.Z);
        Oriented(colour, Vector3.Back, P(0, 1, 1), P(1, 1, 1), P(1, 0, 1), P(0, 0, 1));
        Oriented(colour, Vector3.Forward, P(1, 1, 0), P(0, 1, 0), P(0, 0, 0), P(1, 0, 0));
        Oriented(colour, Vector3.Right, P(1, 1, 1), P(1, 1, 0), P(1, 0, 0), P(1, 0, 1));
        Oriented(colour, Vector3.Left, P(0, 1, 0), P(0, 1, 1), P(0, 0, 1), P(0, 0, 0));
        Oriented(colour, Vector3.Up, P(0, 1, 0), P(1, 1, 0), P(1, 1, 1), P(0, 1, 1));
        Oriented(colour, Vector3.Down, P(0, 0, 1), P(1, 0, 1), P(1, 0, 0), P(0, 0, 0));
    }

    /// <summary>A plain quad facing <paramref name="outward"/>, whichever way round its corners are given.</summary>
    private void Oriented(Paint colour, Vector3 outward, Vector3 a, Vector3 b, Vector3 c, Vector3 d)
    {
        Triangle(colour, outward, a, b, c);
        Triangle(colour, outward, a, c, d);
    }

    /// <summary>A plain, flat-shaded triangle facing <paramref name="outward"/>, whichever way round it's given.</summary>
    private void Triangle(Paint colour, Vector3 outward, Vector3 a, Vector3 b, Vector3 c)
    {
        // Slivers (a corner's two points meeting where its radius is 0) add nothing.
        if ((b - a).Cross(c - a).LengthSquared() < 1e-6f)
        {
            return;
        }

        var s = SurfaceFor("case");
        var normal = outward.Normalized();
        var uv = Swatch(colour);
        var first = s.Count;
        s.Add(a, normal, uv);
        s.Add(b, normal, uv);
        s.Add(c, normal, uv);
        s.Facing(first, first + 1, first + 2, normal);
    }

    /// <summary>The middle of a colour's swatch in the palette texture.</summary>
    private static Vector2 Swatch(Paint colour)
    {
        var i = (int)colour;
        return new Vector2((i % PaletteColumns + 0.5f) / PaletteColumns, (i / PaletteColumns + 0.5f) / PaletteColumns);
    }

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

    // ---- Output ----------------------------------------------------------------------------------------------

    private ArrayMesh ToMesh(out int triangles)
    {
        // Fit to the spec: standing on y = 0, centred in x and z, the largest side 1 m.
        var min = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue);
        var max = new Vector3(float.MinValue, float.MinValue, float.MinValue);
        foreach (var surface in _surfaces.Values)
        {
            foreach (var p in surface.Vertices)
            {
                min = min.Min(p);
                max = max.Max(p);
            }
        }

        var size = max - min;
        var scale = 1 / Math.Max(size.X, Math.Max(size.Y, size.Z));
        var offset = new Vector3(-(min.X + max.X) / 2, -min.Y, -(min.Z + max.Z) / 2);

        var mesh = new ArrayMesh();
        triangles = 0;

        // The slot first, then the case, as the boxes list theirs.
        _order.Sort((a, b) => (a == "case").CompareTo(b == "case"));
        foreach (var name in _order)
        {
            var surface = _surfaces[name];
            var vertices = new Vector3[surface.Vertices.Count];
            for (var i = 0; i < vertices.Length; i++)
            {
                vertices[i] = (surface.Vertices[i] + offset) * scale;
            }

            var arrays = new Godot.Collections.Array();
            arrays.Resize((int)Mesh.ArrayType.Max);
            arrays[(int)Mesh.ArrayType.Vertex] = vertices;
            arrays[(int)Mesh.ArrayType.Normal] = surface.Normals.ToArray();
            arrays[(int)Mesh.ArrayType.TexUV] = surface.Uvs.ToArray();
            arrays[(int)Mesh.ArrayType.Index] = surface.Indices.ToArray();
            mesh.AddSurfaceFromArrays(Mesh.PrimitiveType.Triangles, arrays);
            triangles += surface.Indices.Count / 3;

            StandardMaterial3D material;
            if (name == "screenshot")
            {
                // Matte, as the arcade cabinet's: a glossy screen mirrors the lights as the focused set sways.
                material = new StandardMaterial3D
                {
                    ResourceName = name,
                    AlbedoColor = Colors.White,
                    AlbedoTexture = ImageTexture.CreateFromImage(ArcadeCabinetBuilder.DarkScreen()),
                    Roughness = 0.9f,
                    Metallic = 0,
                };

                // The face's aspect ratio (A7): it's curved, so its own number rather than its bounds.
                material.SetMeta("extras", new Godot.Collections.Dictionary { ["aspect"] = ScreenAspect });
            }
            else
            {
                material = new StandardMaterial3D
                {
                    ResourceName = name,
                    AlbedoColor = Colors.White,
                    AlbedoTexture = ImageTexture.CreateFromImage(PaletteImage()),
                    Roughness = 0.5f,
                    Metallic = 0,
                };
            }

            var index = mesh.GetSurfaceCount() - 1;
            mesh.SurfaceSetMaterial(index, material);
            mesh.SurfaceSetName(index, name);
        }

        return mesh;
    }

    /// <summary>The case's colours, a 16-pixel swatch each.</summary>
    private static Image PaletteImage()
    {
        const int Side = PaletteSwatch * PaletteColumns;
        var image = Image.CreateEmpty(Side, Side, false, Image.Format.Rgb8);
        for (var y = 0; y < Side; y++)
        {
            for (var x = 0; x < Side; x++)
            {
                var i = y / PaletteSwatch * PaletteColumns + x / PaletteSwatch;
                image.SetPixel(x, y, i < Palette.Length ? Palette[i] : Palette[0]);
            }
        }

        return image;
    }

    private sealed class Surface
    {
        public List<Vector3> Vertices { get; } = [];

        public List<Vector3> Normals { get; } = [];

        public List<Vector2> Uvs { get; } = [];

        public List<int> Indices { get; } = [];

        public int Count => Vertices.Count;

        public void Add(Vector3 position, Vector3 normal, Vector2 uv)
        {
            Vertices.Add(position);
            Normals.Add(normal);
            Uvs.Add(uv);
        }

        /// <summary>
        /// A triangle facing <paramref name="outward"/>. Godot's front faces wind clockwise seen from outside, so the
        /// corners are stored in whichever order makes that so.
        /// </summary>
        public void Facing(int a, int b, int c, Vector3 outward)
        {
            var normal = (Vertices[c] - Vertices[a]).Cross(Vertices[b] - Vertices[a]);
            if (normal.Dot(outward) >= 0)
            {
                Indices.AddRange([a, b, c]);
            }
            else
            {
                Indices.AddRange([a, c, b]);
            }
        }
    }
}
