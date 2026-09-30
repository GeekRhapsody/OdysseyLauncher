using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// The sample theme's models (<c>samples/themes/retro-tv/</c>), built from boxes, a tapered cabinet, cylinders and
/// quads, in metres, to the model spec (A7), with clips the launcher plays:
/// <list type="bullet">
/// <item>
/// <c>crt_tv</c>, a game template that isn't a box: a wood-cased CRT whose screen is the <c>screenshot</c> slot (its
/// authored texture, a test card, is "no signal"), on a stand whose plate is the <c>label</c> slot (the theme fills it
/// with the game's logo, else a printed title). Clips: <c>focused</c> (the rabbit-ear aerials sway) and <c>launch</c>
/// (the set spins up and the aerials fold). No <c>idle</c> clip, so the grid batches every TV but the focused one.
/// </item>
/// <item>
/// <c>console</c>, a system model: a console with a cartridge in its slot and a <c>label</c> across its front. Clips:
/// <c>idle</c> (the cartridge rises and settles; so every card is drawn as its own node) and <c>focused</c> (it pops up
/// and wobbles). Its plain <c>case</c> material takes each system's colour.
/// </item>
/// </list>
/// </summary>
public static class RetroTvBuilder
{
    private static readonly Color Wood = new("#6B4527");
    private static readonly Color Trim = new("#26262B");
    private static readonly Color Console = new("#C9C6BE");
    private static readonly Color Cartridge = new("#34343C");

    public static Node3D Tv(out int triangles)
    {
        var root = new Node3D { Name = "crt_tv" };
        var materials = Materials();
        var tv = Child(root, new Node3D { Name = "tv", Position = new Vector3(0, 0.3f, 0) });

        // The cabinet, tapering towards the back like a real tube set; the screen sits on the front, left of the knobs.
        var body = new Kit();
        body.Frustum("case", frontWidth: 0.9f, frontHeight: 0.7f, backWidth: 0.62f, backHeight: 0.5f, depth: 0.62f, frontZ: 0.31f, centreY: 0.35f);
        body.Box("trim", new Vector3(-0.08f, 0.36f, 0.312f), new Vector3(0.7f, 0.54f, 0.004f));
        body.Quad("screenshot", new Vector3(-0.08f, 0.36f, 0.316f), 0.64f, 0.48f);
        body.Cylinder("trim", new Vector3(0.34f, 0.5f, 0.325f), 0.04f, 0.03f);
        body.Cylinder("trim", new Vector3(0.34f, 0.3f, 0.325f), 0.04f, 0.03f);
        body.Box("trim", new Vector3(0, 0.72f, 0), new Vector3(0.12f, 0.04f, 0.1f));
        Child(tv, body.Instance("body", materials));

        foreach (var (name, x, tilt) in (ReadOnlySpan<(string, float, float)>)[("antenna_left", -0.02f, 25f), ("antenna_right", 0.02f, -25f)])
        {
            var aerial = new Kit();
            aerial.Box("trim", new Vector3(0, 0.15f, 0), new Vector3(0.014f, 0.3f, 0.014f));
            aerial.Box("trim", new Vector3(0, 0.3f, 0), new Vector3(0.03f, 0.02f, 0.03f));
            var node = Child(tv, aerial.Instance(name, materials));
            node.Position = new Vector3(x, 0.74f, 0);
            node.RotationDegrees = new Vector3(0, 0, tilt);
        }

        // The stand: a column on a plinth, whose front plate is the label slot.
        var stand = new Kit();
        stand.Box("trim", new Vector3(0, 0.2f, 0), new Vector3(0.12f, 0.2f, 0.12f));
        stand.Box("case", new Vector3(0, 0.065f, 0), new Vector3(0.52f, 0.13f, 0.34f));
        stand.Quad("label", new Vector3(0, 0.065f, 0.172f), 0.46f, 0.1f);
        Child(root, stand.Instance("stand", materials));

        var player = Child(root, new AnimationPlayer { Name = "AnimationPlayer" });
        var library = new AnimationLibrary();
        library.AddAnimation("focused", Clip(1.6f, loop: true,
            ("tv/antenna_left", Rotations(Z(25), Z(38), Z(22), Z(25))),
            ("tv/antenna_right", Rotations(Z(-25), Z(-20), Z(-36), Z(-25))),
            ("tv", Rotations(Y(0), Y(-5), Y(5), Y(0)))));
        library.AddAnimation("launch", Clip(1.2f, loop: false,
            ("tv/antenna_left", Rotations(Z(25), Z(60), Z(88), Z(88))),
            ("tv/antenna_right", Rotations(Z(-25), Z(-60), Z(-88), Z(-88))),
            ("tv", Rotations(Y(0), Y(60), Y(200), Y(360)))));
        player.AddAnimationLibrary(string.Empty, library);

        triangles = body.Triangles + stand.Triangles + 2 * 24;
        SetOwners(root, root);
        return root;

        Dictionary<string, StandardMaterial3D> Materials() => new()
        {
            ["case"] = Plain("case", Wood, 0.55f),
            ["trim"] = Plain("trim", Trim, 0.3f),
            ["screenshot"] = Slot("screenshot", 0.64f / 0.48f, 0.15f, ImageTexture.CreateFromImage(BoxBuilder.TestCard())),
            ["label"] = Slot("label", 0.46f / 0.1f, 0.5f, null),
        };
    }

    public static Node3D ConsoleModel(out int triangles)
    {
        var root = new Node3D { Name = "console" };
        var materials = Materials();
        var body = new Kit();
        body.Box("case", new Vector3(0, 0.1f, 0), new Vector3(0.9f, 0.2f, 0.6f));
        body.Box("case", new Vector3(0, 0.215f, -0.06f), new Vector3(0.56f, 0.03f, 0.36f));
        body.Quad("label", new Vector3(0, 0.1f, 0.301f), 0.56f, 0.15f);
        body.Box("cartridge", new Vector3(0.33f, 0.21f, 0.2f), new Vector3(0.08f, 0.02f, 0.05f));
        body.Box("cartridge", new Vector3(0.22f, 0.21f, 0.2f), new Vector3(0.08f, 0.02f, 0.05f));
        Child(root, body.Instance("body", materials));

        var cartridge = new Kit();
        cartridge.Box("cartridge", new Vector3(0, 0.12f, 0), new Vector3(0.36f, 0.24f, 0.05f));
        cartridge.Box("cartridge", new Vector3(0, 0.25f, 0), new Vector3(0.3f, 0.02f, 0.06f));
        var slot = Child(root, cartridge.Instance("cartridge", materials));
        slot.Position = new Vector3(0, 0.1f, -0.06f);

        var player = Child(root, new AnimationPlayer { Name = "AnimationPlayer" });
        var library = new AnimationLibrary();
        library.AddAnimation("idle", Clip(3f, loop: true,
            ("cartridge", Positions(new Vector3(0, 0.1f, -0.06f), new Vector3(0, 0.13f, -0.06f), new Vector3(0, 0.1f, -0.06f)))));
        library.AddAnimation("focused", Clip(1.2f, loop: true,
            ("cartridge", Positions(new Vector3(0, 0.22f, -0.06f), new Vector3(0, 0.25f, -0.06f), new Vector3(0, 0.22f, -0.06f))),
            ("cartridge", Rotations(Z(0), Z(6), Z(-6), Z(0)))));
        player.AddAnimationLibrary(string.Empty, library);

        triangles = body.Triangles + cartridge.Triangles;
        SetOwners(root, root);
        return root;

        Dictionary<string, StandardMaterial3D> Materials() => new()
        {
            ["case"] = Plain("case", Console, 0.5f),
            ["cartridge"] = Plain("cartridge", Cartridge, 0.4f),
            ["label"] = Slot("label", 0.56f / 0.15f, 0.5f, null),
        };
    }

    private static T Child<T>(Node parent, T child) where T : Node
    {
        parent.AddChild(child);
        return child;
    }

    private static void SetOwners(Node node, Node owner)
    {
        foreach (var child in node.GetChildren())
        {
            child.Owner = owner;
            SetOwners(child, owner);
        }
    }

    private static StandardMaterial3D Plain(string name, Color colour, float roughness) =>
        new() { ResourceName = name, AlbedoColor = colour, Roughness = roughness };

    private static StandardMaterial3D Slot(string name, float aspect, float roughness, Texture2D? texture)
    {
        var material = new StandardMaterial3D { ResourceName = name, AlbedoColor = Colors.White, Roughness = roughness, AlbedoTexture = texture };

        // The face's aspect ratio (A7), so the loader needn't measure it.
        material.SetMeta("extras", new Godot.Collections.Dictionary { ["aspect"] = aspect });
        return material;
    }

    private static Quaternion Y(float degrees) => new(Vector3.Up, Mathf.DegToRad(degrees));

    private static Quaternion Z(float degrees) => new(Vector3.Back, Mathf.DegToRad(degrees));

    private static object[] Rotations(params Quaternion[] keys) => Array.ConvertAll(keys, k => (object)k);

    private static object[] Positions(params Vector3[] keys) => Array.ConvertAll(keys, k => (object)k);

    /// <summary>A clip whose tracks spread their keys evenly over its length (rotations or positions).</summary>
    private static Animation Clip(float length, bool loop, params (string Node, object[] Keys)[] tracks)
    {
        var clip = new Animation { Length = length, LoopMode = loop ? Animation.LoopModeEnum.Linear : Animation.LoopModeEnum.None };
        foreach (var (node, keys) in tracks)
        {
            var rotation = keys[0] is Quaternion;
            var track = clip.AddTrack(rotation ? Animation.TrackType.Rotation3D : Animation.TrackType.Position3D);
            clip.TrackSetPath(track, node);
            for (var k = 0; k < keys.Length; k++)
            {
                var time = length * k / (keys.Length - 1);
                if (rotation)
                {
                    clip.RotationTrackInsertKey(track, time, (Quaternion)keys[k]);
                }
                else
                {
                    clip.PositionTrackInsertKey(track, time, (Vector3)keys[k]);
                }
            }
        }

        return clip;
    }

    /// <summary>Surfaces by material, as in <see cref="BoxBuilder"/>: counter-clockwise from outside, stored for Godot.</summary>
    private sealed class Kit
    {
        private readonly Dictionary<string, (List<Vector3> V, List<Vector3> N, List<Vector2> Uv, List<int> I)> _surfaces = new(StringComparer.Ordinal);
        private readonly List<string> _order = [];

        public int Triangles { get; private set; }

        /// <summary>An axis-aligned box, each face's UVs spanning 0..1 upright.</summary>
        public void Box(string material, Vector3 centre, Vector3 size)
        {
            var h = size / 2;
            Face(material, centre + new Vector3(0, 0, h.Z), Vector3.Right * h.X, Vector3.Up * h.Y);     // front
            Face(material, centre - new Vector3(0, 0, h.Z), Vector3.Left * h.X, Vector3.Up * h.Y);      // back
            Face(material, centre + new Vector3(h.X, 0, 0), Vector3.Forward * h.Z, Vector3.Up * h.Y);   // right
            Face(material, centre - new Vector3(h.X, 0, 0), Vector3.Back * h.Z, Vector3.Up * h.Y);      // left
            Face(material, centre + new Vector3(0, h.Y, 0), Vector3.Right * h.X, Vector3.Forward * h.Z); // top
            Face(material, centre - new Vector3(0, h.Y, 0), Vector3.Right * h.X, Vector3.Back * h.Z);   // bottom
        }

        /// <summary>A quad facing +Z (a slot's face), UVs 0..1 from its top left.</summary>
        public void Quad(string material, Vector3 centre, float width, float height) =>
            Face(material, centre, Vector3.Right * width / 2, Vector3.Up * height / 2);

        /// <summary>A box tapering from its front to a smaller back, centred on x.</summary>
        public void Frustum(string material, float frontWidth, float frontHeight, float backWidth, float backHeight, float depth, float frontZ, float centreY)
        {
            var backZ = frontZ - depth;
            Vector3 F(float sx, float sy) => new(sx * frontWidth / 2, centreY + sy * frontHeight / 2, frontZ);
            Vector3 B(float sx, float sy) => new(sx * backWidth / 2, centreY + sy * backHeight / 2, backZ);
            Quad4(material, F(-1, 1), F(1, 1), F(1, -1), F(-1, -1));   // front
            Quad4(material, B(1, 1), B(-1, 1), B(-1, -1), B(1, -1));   // back
            Quad4(material, F(1, 1), B(1, 1), B(1, -1), F(1, -1));     // right
            Quad4(material, B(-1, 1), F(-1, 1), F(-1, -1), B(-1, -1)); // left
            Quad4(material, B(-1, 1), B(1, 1), F(1, 1), F(-1, 1));     // top
            Quad4(material, F(-1, -1), F(1, -1), B(1, -1), B(-1, -1)); // bottom
        }

        /// <summary>A cylinder along +Z (a knob), capped at the front.</summary>
        public void Cylinder(string material, Vector3 frontCentre, float radius, float length, int segments = 16)
        {
            for (var i = 0; i < segments; i++)
            {
                var a0 = Mathf.Tau * i / segments;
                var a1 = Mathf.Tau * (i + 1) / segments;
                var p0 = new Vector3(MathF.Cos(a0) * radius, MathF.Sin(a0) * radius, 0);
                var p1 = new Vector3(MathF.Cos(a1) * radius, MathF.Sin(a1) * radius, 0);
                var back = new Vector3(0, 0, -length);
                Quad4(material, frontCentre + p0, frontCentre + p1, frontCentre + p1 + back, frontCentre + p0 + back);
                Triangle(material, frontCentre, frontCentre + p0, frontCentre + p1, Vector3.Back);
            }
        }

        /// <summary>A rectangle around <paramref name="centre"/> spanned by half-extents right and up (seen from outside).</summary>
        private void Face(string material, Vector3 centre, Vector3 right, Vector3 up) =>
            Quad4(material, centre - right + up, centre + right + up, centre + right - up, centre - right - up);

        /// <summary>Corners top-left, top-right, bottom-right, bottom-left, seen from outside; UVs 0..1 across it.</summary>
        private void Quad4(string material, Vector3 tl, Vector3 tr, Vector3 br, Vector3 bl)
        {
            var normal = (bl - tl).Cross(tr - tl).Normalized();
            var s = Surface(material);
            var first = s.V.Count;
            foreach (var (p, uv) in (ReadOnlySpan<(Vector3, Vector2)>)[(tl, new Vector2(0, 0)), (tr, new Vector2(1, 0)), (br, new Vector2(1, 1)), (bl, new Vector2(0, 1))])
            {
                s.V.Add(p);
                s.N.Add(normal);
                s.Uv.Add(uv);
            }

            // Counter-clockwise from outside is tl, bl, br; Godot's front faces wind clockwise, so they're stored reversed.
            s.I.AddRange([first, first + 1, first + 2, first, first + 2, first + 3]);
            Triangles += 2;
        }

        private void Triangle(string material, Vector3 a, Vector3 b, Vector3 c, Vector3 normal)
        {
            var s = Surface(material);
            var first = s.V.Count;
            foreach (var p in (ReadOnlySpan<Vector3>)[a, b, c])
            {
                s.V.Add(p);
                s.N.Add(normal);
                s.Uv.Add(new Vector2(0.5f, 0.5f));
            }

            s.I.AddRange([first, first + 2, first + 1]);
            Triangles++;
        }

        private (List<Vector3> V, List<Vector3> N, List<Vector2> Uv, List<int> I) Surface(string material)
        {
            if (!_surfaces.TryGetValue(material, out var surface))
            {
                surface = ([], [], [], []);
                _surfaces[material] = surface;
                _order.Add(material);
            }

            return surface;
        }

        public MeshInstance3D Instance(string name, Dictionary<string, StandardMaterial3D> materials)
        {
            var mesh = new ArrayMesh();
            foreach (var material in _order)
            {
                var (v, n, uv, i) = _surfaces[material];
                var arrays = new Godot.Collections.Array();
                arrays.Resize((int)Mesh.ArrayType.Max);
                arrays[(int)Mesh.ArrayType.Vertex] = v.ToArray();
                arrays[(int)Mesh.ArrayType.Normal] = n.ToArray();
                arrays[(int)Mesh.ArrayType.TexUV] = uv.ToArray();
                arrays[(int)Mesh.ArrayType.Index] = i.ToArray();
                mesh.AddSurfaceFromArrays(Mesh.PrimitiveType.Triangles, arrays);
                mesh.SurfaceSetMaterial(mesh.GetSurfaceCount() - 1, materials[material]);
                mesh.SurfaceSetName(mesh.GetSurfaceCount() - 1, material);
            }

            return new MeshInstance3D { Name = name, Mesh = mesh };
        }
    }
}
