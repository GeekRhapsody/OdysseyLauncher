using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// The built-in theme's arcade template (<c>arcade_cabinet</c>): the top half of an upright arcade cabinet, cut off
/// below the control panel. The monitor, tilted back in its bezel, is the <c>screenshot</c> slot; the marquee above it
/// is the <c>label</c> slot, which the theme fills with the game's logo (drawn whole over a deep shade: A7), else a
/// printed title. The control panel has two players' joysticks and buttons.
/// <para>
/// Built in millimetres from a real cabinet's proportions, front facing +Z, then fitted to the model spec (A7: standing
/// on y = 0, centred, the largest side 1 m). Three materials: the two slots, and <c>case</c>, whose colours come from
/// a small palette texture (each part's UVs sit in the middle of its colour's swatch, so it samples one colour at any
/// distance), so the cabinet needs no more materials than a box. The screen's authored texture, shown when a game has
/// no screenshot, is a switched-off CRT. No clips: the grid's procedural motion animates it, and it stays batched.
/// </para>
/// </summary>
public sealed class ArcadeCabinetBuilder
{
    // The cabinet, in millimetres. The side panels' inner faces are at ±InnerHalf, their outer faces at ±OuterHalf, and
    // the control panel overhangs them to ±PanelHalf.
    private const float InnerHalf = 300;
    private const float OuterHalf = 320;
    private const float PanelHalf = 335;
    private const float Back = -180;
    private const float Top = 960;

    // The monitor tilts back 12 degrees, its bezel running from the control panel to the marquee.
    private const float TiltDegrees = 12;
    private const float ScreenWidth = 568;
    private const float ScreenHeight = 426;

    // The marquee's lit panel: a little taller than most real ones (about 2.7:1, not 3.5:1), since a logo is drawn
    // whole and most are nearer 2:1, so they'd be small on a wider panel.
    private const float MarqueeBottom = 700;
    private const float MarqueeTop = 915;
    private const float MarqueeFront = 160;
    private const float MarqueeWidth = 2 * InnerHalf - 24;

    /// <summary>The palette's colours (sRGB), one 16-pixel swatch each in a 4 x 4 grid.</summary>
    private enum Paint
    {
        Cabinet,
        Side,
        Moulding,
        Bezel,
        Panel,
        Metal,
        Ball,
        Red,
        Yellow,
        Green,
        Blue,
        White,
        Dark,
    }

    private static readonly Color[] Palette =
    [
        new("#17171B"), // cabinet: black laminate
        new("#1D2B55"), // side panels' outsides: deep blue side art
        new("#737985"), // T-moulding along the front edges, so the silhouette reads on a dark background
        new("#232429"), // the bezel round the screen
        new("#24262C"), // the control panel's top
        new("#B9BEC7"), // joystick shafts
        new("#C41A1A"), // ball tops
        new("#D4262A"),
        new("#E8C21E"),
        new("#22A04A"),
        new("#2464D2"),
        new("#E6E6EA"),
        new("#0D0D10"), // dust washers
    ];

    private const int PaletteSwatch = 16;
    private const int PaletteColumns = 4;

    private readonly Dictionary<string, Surface> _surfaces = new(StringComparer.Ordinal);
    private readonly List<string> _order = [];

    /// <summary>The screen's width over its height, for its <c>extras.aspect</c>.</summary>
    public const float ScreenAspect = ScreenWidth / ScreenHeight;

    /// <summary>The marquee's width over its height, for its <c>extras.aspect</c>.</summary>
    public const float MarqueeAspect = MarqueeWidth / (MarqueeTop - MarqueeBottom);

    private ArcadeCabinetBuilder()
    {
    }

    public static ArrayMesh Build(out int triangles)
    {
        var builder = new ArcadeCabinetBuilder();
        builder.BuildAll();
        return builder.ToMesh(out triangles);
    }

    private void BuildAll()
    {
        SidePanels();
        Body();
        Screen();
        Marquee();
        ControlPanel();
    }

    // ---- The parts -----------------------------------------------------------------------------------------

    /// <summary>
    /// Each side panel's profile (z, y), front to back: inside the control panel (well under its top and behind its
    /// front, so no face of the panel's is shared or nearly shared: those flickered as the model moved), the edge
    /// alongside the screen, rising out through the panel's top, the marquee's end, then the top and the back.
    /// </summary>
    private static readonly Vector2[] SideProfile =
    [
        new(Back, 0),
        new(366, 0),
        new(366, 90),
        new(140, 160),
        new(52, 690),
        new(MarqueeFront + 2, 690),
        new(MarqueeFront + 2, Top),
        new(Back, Top),
    ];

    private void SidePanels()
    {
        foreach (var sign in (ReadOnlySpan<float>)[-1f, 1f])
        {
            // The outside carries the side art; the inside is the cabinet's black. Edges facing forwards or up are the
            // T-moulding; the bottom and back are plain.
            Prism(SideProfile, sign * InnerHalf, sign * OuterHalf, outside: Paint.Side, inside: Paint.Cabinet,
                edge: i => SideProfile[i].X <= Back + 1 && SideProfile[(i + 1) % SideProfile.Length].X <= Back + 1
                    || SideProfile[i].Y == 0 && SideProfile[(i + 1) % SideProfile.Length].Y == 0
                    ? Paint.Cabinet
                    : Paint.Moulding);
        }
    }

    /// <summary>The back, the top and the floor between the side panels, so the cabinet is closed from any angle.</summary>
    private void Body()
    {
        Box(Paint.Cabinet, new Vector3(-InnerHalf, 0, Back), new Vector3(InnerHalf, Top, Back + 18));
        Box(Paint.Cabinet, new Vector3(-InnerHalf, Top - 26, Back), new Vector3(InnerHalf, Top, MarqueeFront));
        Box(Paint.Cabinet, new Vector3(-InnerHalf, 0, Back), new Vector3(InnerHalf, 12, 150));
    }

    private void Screen()
    {
        // The bezel: a board tilted back from under the control panel's top edge to inside the marquee box, so no gap
        // shows at either end, with the screen on it.
        var up = Tilted(Vector3.Up);
        var normal = Tilted(Vector3.Back);
        var bottom = new Vector3(0, 170, 131);
        var length = (MarqueeBottom - 5 - bottom.Y) / up.Y;
        var right = Vector3.Right * InnerHalf;
        var top = bottom + up * length;
        Quad(Paint.Bezel, top - right, top + right, bottom + right, bottom - right);

        // The screen, filling the bezel's visible part (the control panel hides its bottom few millimetres, the marquee
        // box its top) but for a thin margin, just in front of it.
        var centre = bottom + up * (length * 0.53f) + normal * 3;
        var halfWidth = Vector3.Right * (ScreenWidth / 2);
        var halfHeight = up * (ScreenHeight / 2);
        SlotQuad("screenshot", centre - halfWidth + halfHeight, centre + halfWidth + halfHeight, centre + halfWidth - halfHeight, centre - halfWidth - halfHeight);

        // A thin frame round it, standing on the bezel.
        const float Frame = 8;
        var onBezel = centre - normal * 3;
        Frame4(onBezel, normal, Vector3.Right * (ScreenWidth / 2 + Frame), up * (ScreenHeight / 2 + Frame), halfWidth, halfHeight, 7);
    }

    /// <summary>The marquee box: the lit panel, set in a frame, between the side panels above the screen.</summary>
    private void Marquee()
    {
        Box(Paint.Cabinet, new Vector3(-InnerHalf, MarqueeBottom - 12, Back), new Vector3(InnerHalf, Top - 26, MarqueeFront));
        var centre = new Vector3(0, (MarqueeBottom + MarqueeTop) / 2, MarqueeFront + 1);
        var halfWidth = Vector3.Right * (MarqueeWidth / 2);
        var halfHeight = Vector3.Up * ((MarqueeTop - MarqueeBottom) / 2);
        SlotQuad("label", centre - halfWidth + halfHeight, centre + halfWidth + halfHeight, centre + halfWidth - halfHeight, centre - halfWidth - halfHeight);

        // A strip along the bottom, holding the panel in, no prouder than it, so it never hides the logo.
        Box(Paint.Moulding, new Vector3(-InnerHalf, MarqueeBottom - 12, MarqueeFront), new Vector3(InnerHalf, MarqueeBottom, MarqueeFront + 2));
    }

    /// <summary>The control panel, sloping down towards the player, with two players' joysticks and six buttons each.</summary>
    private void ControlPanel()
    {
        // Its profile (z, y): the front edge, the sloping top, and the back under the bezel.
        Vector2[] profile = [new(120, 0), new(372, 0), new(372, 104), new(120, 176)];
        Prism(profile, -PanelHalf, PanelHalf, outside: Paint.Cabinet, inside: Paint.Cabinet,
            edge: i => i == 2 ? Paint.Panel : Paint.Cabinet);

        // A point on the top, a fraction of the way from the back edge to the front, and the top's normal.
        var back = new Vector3(0, 176, 120);
        var front = new Vector3(0, 104, 372);
        var slope = (front - back).Normalized();
        var normal = slope.Cross(Vector3.Right).Normalized();
        Vector3 OnTop(float x, float t) => new Vector3(x, 0, 0) + back + (front - back) * t;

        Paint[] colours = [Paint.Red, Paint.Yellow, Paint.Green, Paint.Blue, Paint.White, Paint.Red];
        foreach (var player in (ReadOnlySpan<float>)[-1f, 1f])
        {
            // The joystick on the left of its buttons, as on a Japanese cabinet.
            var centre = player * 170;
            var stick = OnTop(centre - 80, 0.52f);
            Cylinder(Paint.Dark, stick, normal, 30, 3, 12);
            Cylinder(Paint.Metal, stick, normal, 7, 72, 8);
            Sphere(Paint.Ball, stick + normal * 92, 24, 10, 6);

            // Two rows of three, the front row stepped right, the middle column a little further back.
            for (var b = 0; b < 6; b++)
            {
                var row = b / 3;
                var column = b % 3;
                var at = OnTop(centre + column * 52 + row * 12, (row == 0 ? 0.36f : 0.66f) - (column == 1 ? 0.03f : 0));
                Cylinder(Paint.Dark, at, normal, 22, 2, 12);
                Cylinder(colours[b], at, normal, 17, 12, 12);
            }
        }

        // The start buttons, at the back between the players.
        foreach (var x in (ReadOnlySpan<float>)[-18f, 18f])
        {
            Cylinder(Paint.White, OnTop(x, 0.22f), normal, 10, 8, 10);
        }
    }

    private static Vector3 Tilted(Vector3 v) => v.Rotated(Vector3.Right, -Mathf.DegToRad(TiltDegrees));

    // ---- Primitives ----------------------------------------------------------------------------------------

    /// <summary>
    /// A profile in (z, y) extruded across x from <paramref name="x0"/> to <paramref name="x1"/>: its two flat faces
    /// (the one at <paramref name="x1"/> is the outside when it's further from the middle) and a quad per edge.
    /// </summary>
    private void Prism(Vector2[] profile, float x0, float x1, Paint outside, Paint inside, Func<int, Paint> edge)
    {
        var outwards = x1 > x0 ? Vector3.Right : Vector3.Left;
        var outerIsOutside = Math.Abs(x1) >= Math.Abs(x0);
        Flat(profile, x1, outwards, outerIsOutside ? outside : inside);
        Flat(profile, x0, -outwards, outerIsOutside ? inside : outside);

        // Each edge's outward normal: perpendicular to it in (z, y), on the outside for the profile's winding (it may
        // be concave, so not simply away from its middle).
        var area = 0f;
        for (var i = 0; i < profile.Length; i++)
        {
            area += profile[i].Cross(profile[(i + 1) % profile.Length]);
        }

        for (var i = 0; i < profile.Length; i++)
        {
            var a = profile[i];
            var b = profile[(i + 1) % profile.Length];
            var n = new Vector2(b.Y - a.Y, a.X - b.X).Normalized() * Math.Sign(area);
            var outward = new Vector3(0, n.Y, n.X);
            var colour = edge(i);
            Oriented(colour, outward,
                new Vector3(x0, a.Y, a.X), new Vector3(x1, a.Y, a.X), new Vector3(x1, b.Y, b.X), new Vector3(x0, b.Y, b.X));
        }
    }

    /// <summary>A profile's flat face at <paramref name="x"/>, triangulated (it may be concave), facing <paramref name="facing"/>.</summary>
    private void Flat(Vector2[] profile, float x, Vector3 facing, Paint colour)
    {
        var indices = Geometry2D.TriangulatePolygon(profile);
        for (var t = 0; t < indices.Length; t += 3)
        {
            var a = profile[indices[t]];
            var b = profile[indices[t + 1]];
            var c = profile[indices[t + 2]];
            Triangle(colour, facing, new Vector3(x, a.Y, a.X), new Vector3(x, b.Y, b.X), new Vector3(x, c.Y, c.X));
        }
    }

    /// <summary>An axis-aligned box between two corners.</summary>
    private void Box(Paint colour, Vector3 min, Vector3 max)
    {
        Vector3 P(int x, int y, int z) => new(x == 0 ? min.X : max.X, y == 0 ? min.Y : max.Y, z == 0 ? min.Z : max.Z);
        Quad(colour, P(0, 1, 1), P(1, 1, 1), P(1, 0, 1), P(0, 0, 1)); // front
        Quad(colour, P(1, 1, 0), P(0, 1, 0), P(0, 0, 0), P(1, 0, 0)); // back
        Quad(colour, P(1, 1, 1), P(1, 1, 0), P(1, 0, 0), P(1, 0, 1)); // right
        Quad(colour, P(0, 1, 0), P(0, 1, 1), P(0, 0, 1), P(0, 0, 0)); // left
        Quad(colour, P(0, 1, 0), P(1, 1, 0), P(1, 1, 1), P(0, 1, 1)); // top
        Quad(colour, P(0, 0, 1), P(1, 0, 1), P(1, 0, 0), P(0, 0, 0)); // bottom
    }

    /// <summary>
    /// A raised frame round a rectangle on a plane facing <paramref name="facing"/>: four bars between the outer and
    /// inner half-extents, each with its top face and its walls, <paramref name="depth"/> proud of the plane.
    /// </summary>
    private void Frame4(Vector3 centre, Vector3 facing, Vector3 outerX, Vector3 outerY, Vector3 innerX, Vector3 innerY, float depth)
    {
        // Outer and inner corners, top-left first, clockwise seen from the front.
        Vector3[] outer = [centre - outerX + outerY, centre + outerX + outerY, centre + outerX - outerY, centre - outerX - outerY];
        Vector3[] inner = [centre - innerX + innerY, centre + innerX + innerY, centre + innerX - innerY, centre - innerX - innerY];
        var height = facing * depth;
        for (var i = 0; i < 4; i++)
        {
            var j = (i + 1) % 4;
            Oriented(Paint.Cabinet, facing, outer[i] + height, outer[j] + height, inner[j] + height, inner[i] + height);

            // The inner wall, facing the screen, and the outer wall, facing away.
            var mid = (inner[i] + inner[j]) / 2;
            Oriented(Paint.Cabinet, (centre - mid).Normalized(), inner[i] + height, inner[j] + height, inner[j], inner[i]);
            var outerMid = (outer[i] + outer[j]) / 2;
            Oriented(Paint.Cabinet, (outerMid - centre).Normalized(), outer[i], outer[j], outer[j] + height, outer[i] + height);
        }
    }

    /// <summary>A cylinder standing on <paramref name="base"/> along <paramref name="axis"/>, capped at the top.</summary>
    private void Cylinder(Paint colour, Vector3 @base, Vector3 axis, float radius, float height, int segments)
    {
        var (u, v) = Perpendiculars(axis);
        var top = @base + axis * height;
        for (var i = 0; i < segments; i++)
        {
            var a0 = Mathf.Tau * i / segments;
            var a1 = Mathf.Tau * (i + 1) / segments;
            var r0 = u * MathF.Cos(a0) + v * MathF.Sin(a0);
            var r1 = u * MathF.Cos(a1) + v * MathF.Sin(a1);
            var s = SurfaceFor("case");
            var first = s.Count;
            var uv = Swatch(colour);
            s.Add(top + r0 * radius, r0, uv);
            s.Add(top + r1 * radius, r1, uv);
            s.Add(@base + r1 * radius, r1, uv);
            s.Add(@base + r0 * radius, r0, uv);
            s.Facing(first, first + 1, first + 2, (r0 + r1) / 2);
            s.Facing(first, first + 2, first + 3, (r0 + r1) / 2);
            Triangle(colour, axis, top, top + r0 * radius, top + r1 * radius);
        }
    }

    /// <summary>A UV sphere, smooth-shaded.</summary>
    private void Sphere(Paint colour, Vector3 centre, float radius, int slices, int stacks)
    {
        var s = SurfaceFor("case");
        var uv = Swatch(colour);
        for (var stack = 0; stack < stacks; stack++)
        {
            var p0 = Mathf.Pi * stack / stacks;
            var p1 = Mathf.Pi * (stack + 1) / stacks;
            for (var slice = 0; slice < slices; slice++)
            {
                var t0 = Mathf.Tau * slice / slices;
                var t1 = Mathf.Tau * (slice + 1) / slices;
                Vector3 D(float p, float t) => new(MathF.Sin(p) * MathF.Cos(t), MathF.Cos(p), MathF.Sin(p) * MathF.Sin(t));
                var a = D(p0, t0);
                var b = D(p0, t1);
                var c = D(p1, t1);
                var d = D(p1, t0);
                var first = s.Count;
                foreach (var n in (ReadOnlySpan<Vector3>)[a, b, c, d])
                {
                    s.Add(centre + n * radius, n, uv);
                }

                var outward = (a + b + c + d).Normalized();
                if (stack > 0)
                {
                    s.Facing(first, first + 1, first + 2, outward);
                }

                if (stack < stacks - 1)
                {
                    s.Facing(first, first + 2, first + 3, outward);
                }
            }
        }
    }

    private static (Vector3 U, Vector3 V) Perpendiculars(Vector3 axis)
    {
        var u = axis.Cross(Math.Abs(axis.X) < 0.9f ? Vector3.Right : Vector3.Up).Normalized();
        return (u, axis.Cross(u).Normalized());
    }

    /// <summary>A plain quad, corners top-left, top-right, bottom-right, bottom-left as seen from outside.</summary>
    private void Quad(Paint colour, Vector3 tl, Vector3 tr, Vector3 br, Vector3 bl) =>
        Oriented(colour, (bl - tl).Cross(tr - tl).Normalized(), tl, tr, br, bl);

    /// <summary>A plain quad facing <paramref name="outward"/>, whichever way round its corners are given.</summary>
    private void Oriented(Paint colour, Vector3 outward, Vector3 a, Vector3 b, Vector3 c, Vector3 d)
    {
        Triangle(colour, outward, a, b, c);
        Triangle(colour, outward, a, c, d);
    }

    /// <summary>A plain, flat-shaded triangle facing <paramref name="outward"/>, whichever way round it's given.</summary>
    private void Triangle(Paint colour, Vector3 outward, Vector3 a, Vector3 b, Vector3 c)
    {
        var s = SurfaceFor("case");
        var normal = outward.Normalized();
        var uv = Swatch(colour);
        var first = s.Count;
        s.Add(a, normal, uv);
        s.Add(b, normal, uv);
        s.Add(c, normal, uv);
        s.Facing(first, first + 1, first + 2, normal);
    }

    /// <summary>A slot's face: corners top-left, top-right, bottom-right, bottom-left seen from outside, UVs 0..1 upright.</summary>
    private void SlotQuad(string slot, Vector3 tl, Vector3 tr, Vector3 br, Vector3 bl)
    {
        var s = SurfaceFor(slot);
        var normal = (bl - tl).Cross(tr - tl).Normalized();
        var first = s.Count;
        s.Add(tl, normal, new Vector2(0, 0));
        s.Add(tr, normal, new Vector2(1, 0));
        s.Add(br, normal, new Vector2(1, 1));
        s.Add(bl, normal, new Vector2(0, 1));
        s.Facing(first, first + 1, first + 2, normal);
        s.Facing(first, first + 2, first + 3, normal);
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

        // Slots first, then the case, as the boxes list theirs.
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

            var material = name switch
            {
                // Matte: glossy glass mirrored the theme's lights as the focused cabinet swayed, whiting out the
                // screen, and a middling roughness spread that sheen over it, so a pillarboxed game's bars looked grey.
                "screenshot" => SlotMaterial(name, ScreenAspect, 0.9f, ImageTexture.CreateFromImage(DarkScreen())),
                "label" => SlotMaterial(name, MarqueeAspect, 0.9f, null),
                _ => new StandardMaterial3D
                {
                    ResourceName = name,
                    AlbedoColor = Colors.White,
                    AlbedoTexture = ImageTexture.CreateFromImage(PaletteImage()),
                    Roughness = 0.45f,
                    Metallic = 0,
                },
            };
            var index = mesh.GetSurfaceCount() - 1;
            mesh.SurfaceSetMaterial(index, material);
            mesh.SurfaceSetName(index, name);
        }

        return mesh;
    }

    private static StandardMaterial3D SlotMaterial(string name, float aspect, float roughness, Texture2D? texture)
    {
        var material = new StandardMaterial3D { ResourceName = name, AlbedoColor = Colors.White, Roughness = roughness, AlbedoTexture = texture, Metallic = 0 };

        // The face's aspect ratio (A7): the screen is tilted, so measuring its bounds would get it wrong.
        material.SetMeta("extras", new Godot.Collections.Dictionary { ["aspect"] = aspect });
        return material;
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

    /// <summary>A switched-off CRT, 4:3: dark glass, a little lighter in the middle, with faint scanlines.</summary>
    public static Image DarkScreen()
    {
        const int Width = 128;
        const int Height = 96;
        var image = Image.CreateEmpty(Width, Height, false, Image.Format.Rgb8);
        for (var y = 0; y < Height; y++)
        {
            for (var x = 0; x < Width; x++)
            {
                var dx = (x + 0.5f) / Width - 0.5f;
                var dy = (y + 0.5f) / Height - 0.5f;
                var glow = 1 - Math.Clamp((dx * dx + dy * dy) * 3.2f, 0, 1);
                var line = y % 2 == 0 ? 1f : 0.82f;
                var level = (0.035f + 0.06f * glow) * line;
                image.SetPixel(x, y, new Color(level * 0.85f, level * 0.95f, level * 1.1f));
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
