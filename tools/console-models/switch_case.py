"""Memory-card's Switch game case template (godot/themes/memory-card/models/templates/switch_case.glb).

Nintendo's Switch case, 104.1 x 172 x 11.5 mm, as one closed solid: the case's outer hull, nothing inside it. Seen from
the front it's a rectangle with rounded corners; round its edge, the front and the back are chamfered (the back's
chamfer the deeper), and the opening side has the groove the two halves leave between them, its inner corners rounded.
The paper insert wraps the front, the spine and the back: the `cover`, `spine` and `back` slots, each the hull's own
faces (not quads laid over it), the front's and the back's reaching the spine's chamfers and stopping short of the
opening side, the spine's wrapping both chamfers. The case shows round the insert at the top and the bottom. The
spine's art spans its flat wall, centred; the chamfers take its edges, as a clamped texture would. Everything else is
`case`, light grey plastic. The flat faces are flat-shaded; only the rounded corners are smooth. It faces the front,
upright, fitted to the model spec (A7): standing on y = 0, centred, the largest side (the height) 1 m.

The hull's measurements are the earlier hand-made model's, so it looks the same; that model's hollow shell left a hole
at each end of the spine. Four materials and no texture, within the game template budget. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/switch_case.py -- godot/themes/memory-card/models/templates/switch_case.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mega_drive_cartridge import boolean, export, material, new_object, triangles  # noqa: E402

WIDTH, HEIGHT, DEPTH = 104.11, 172.0, 11.538
RADIUS, SEGMENTS = 3.5, 3       # the corners, seen from the front
FRONT_CHAMFER = (0.798, 1.091)  # how far each chamfer is set in from the side, and how deep it is
BACK_CHAMFER = (0.798, 1.999)

# The insert: where its art starts and ends up the case, and how much case shows between it and the opening side.
ART_BOTTOM, ART_TOP, ART_OPENING = 6.509, 166.275, 2.728
SPINE_ASPECT = 0.0613           # the spine's art spans this much of the wrap (width over the art's height), centred

# The groove in the opening side: where it starts and ends up the case, how deep it is, its mouth (the front's and the
# back's lips, from the middle of the depth: each bevelled out to the end of the side wall), and its inner corners.
GROOVE = (45.7, 126.3)
GROOVE_DEPTH = 4.655
GROOVE_MOUTH = (3.6, 3.5)
GROOVE_LIP = 0.355              # how far the lips' bevels reach in from the side
GROOVE_RADIUS = 2.0


def rounded_rect(inset, segments=SEGMENTS):
    """The case's outline seen from the front, (x, z) anticlockwise from the bottom right, set in by inset all round."""
    w, r = WIDTH / 2 - RADIUS, RADIUS - inset
    corners = ((w, RADIUS, -90), (w, HEIGHT - RADIUS, 0), (-w, HEIGHT - RADIUS, 90), (-w, RADIUS, 180))
    points = []
    for cx, cz, start in corners:
        for k in range(segments + 1):
            a = math.radians(start + 90 * k / segments)
            points.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return points


def hull(mat):
    """
    The case in millimetres, standing on its bottom at the origin, its front facing -Y and its spine on -X: the outline
    at four depths (the front face, the side wall's two ends, the back face), joined by the chamfers and the wall.
    """
    d = DEPTH / 2
    rings = [(-d, FRONT_CHAMFER[0]), (-d + FRONT_CHAMFER[1], 0.0), (d - BACK_CHAMFER[1], 0.0), (d, BACK_CHAMFER[0])]
    bm = bmesh.new()
    loops = [[bm.verts.new((x, y, z)) for x, z in rounded_rect(inset)] for y, inset in rings]
    bm.faces.new(loops[0])
    bm.faces.new(list(reversed(loops[-1])))
    for a, b in zip(loops, loops[1:]):
        n = len(a)
        for i in range(n):
            bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object("switch_case", bm, mat)


def prism(name, outline, axis, start, end, mat):
    """A solid from a closed outline in the plane across axis (1: (x, z), 2: (x, y)), extruded from start to end."""
    def point(p, t):
        return (p[0], t, p[1]) if axis == 1 else (p[0], p[1], t)
    bm = bmesh.new()
    a = [bm.verts.new(point(p, start)) for p in outline]
    b = [bm.verts.new(point(p, end)) for p in outline]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        bm.faces.new([a[i], b[i], b[j], a[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def groove(case, mat):
    """
    Cuts the groove into the opening side: its cross-section (with the mouth's bevels) along it, intersected with its
    length seen from the side (the ends, rounded into the floor). Each cutter reaches past the other's faces, so no two
    of their faces lie in one plane.
    """
    side, floor, out = WIDTH / 2, WIDTH / 2 - GROOVE_DEPTH, WIDTH / 2 + 5
    front, back = -DEPTH / 2 + FRONT_CHAMFER[1], DEPTH / 2 - BACK_CHAMFER[1]  # the side wall's ends
    lip = side - GROOVE_LIP
    section = [(floor - 1, -GROOVE_MOUTH[0]), (lip, -GROOVE_MOUTH[0]), (side, front), (out, front),
               (out, back), (side, back), (lip, GROOVE_MOUTH[1]), (floor - 1, GROOVE_MOUTH[1])]
    cutter = prism("groove", section, 2, GROOVE[0] - 1, GROOVE[1] + 1, mat)

    r, (z0, z1) = GROOVE_RADIUS, GROOVE
    out += 1
    ends = [(out, z0), (floor + r, z0)]
    ends += [(floor + r + r * math.cos(math.radians(a)), z0 + r + r * math.sin(math.radians(a))) for a in (-120, -150)]
    ends += [(floor, z0 + r), (floor, z1 - r)]
    ends += [(floor + r + r * math.cos(math.radians(a)), z1 - r + r * math.sin(math.radians(a))) for a in (150, 120)]
    ends += [(floor + r, z1), (out, z1)]
    boolean(cutter, prism("ends", ends, 1, -DEPTH, DEPTH, mat), "INTERSECT")
    boolean(case, cutter)


def spine_u(co):
    """
    The spine's u at a point on its wrap: its distance round the profile from the back's edge, the art's span centred
    on the wrap, clamped so the chamfers take the art's edges.
    """
    d = DEPTH / 2
    profile = [Vector((-WIDTH / 2 + BACK_CHAMFER[0], d)), Vector((-WIDTH / 2, d - BACK_CHAMFER[1])),
               Vector((-WIDTH / 2, -d + FRONT_CHAMFER[1])), Vector((-WIDTH / 2 + FRONT_CHAMFER[0], -d))]
    lengths = [(b - a).length for a, b in zip(profile, profile[1:])]
    p, s = Vector((co.x, co.y)), 0.0
    for (a, b), length in zip(zip(profile, profile[1:]), lengths):
        t = (p - a).dot(b - a) / length ** 2
        if t <= 1 + 1e-4 or b is profile[-1]:
            s += max(t, 0.0) * length
            break
        s += length
    span = SPINE_ASPECT * (ART_TOP - ART_BOTTOM)
    return min(max(0.5 + (s - sum(lengths) / 2) / span, 0.0), 1.0)


def paint(obj, mats):
    """
    Gives the insert's faces their slots, with UVs upright from outside: the front and the back flat across the insert,
    the spine round its wrap. The rest (the border at the top and the bottom, the opening side, the groove) is case.
    """
    mesh = obj.data
    right = WIDTH / 2 - ART_OPENING  # the insert's edge by the opening side
    left = -WIDTH / 2 + FRONT_CHAMFER[0]

    # Cut the faces along the insert's edges: its top, its bottom, and its edge by the opening side.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for co, no in (((0, 0, ART_BOTTOM), (0, 0, 1)), ((0, 0, ART_TOP), (0, 0, 1)), ((right, 0, 0), (1, 0, 0))):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.to_mesh(mesh)
    bm.free()

    for name in ("cover", "spine", "back"):
        mesh.materials.append(mats[name])
    index = {m.name: i for i, m in enumerate(mesh.materials)}
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    height = ART_TOP - ART_BOTTOM

    # Each slot: whether a face is on it (where its centre is, and its normal), and a vertex's UV.
    slots = {
        "cover": (lambda n, c: n.y < -0.99 and c.y < -DEPTH / 2 + 0.01 and c.x < right,
                  lambda p: ((p.x - left) / (right - left), (p.z - ART_BOTTOM) / height)),
        "back": (lambda n, c: n.y > 0.99 and c.y > DEPTH / 2 - 0.01 and c.x < right,
                 lambda p: ((right - p.x) / (right - left), (p.z - ART_BOTTOM) / height)),
        "spine": (lambda n, c: n.x < 0 and abs(n.z) < 1e-4 and c.x < left,
                  lambda p: (spine_u(p), (p.z - ART_BOTTOM) / height)),
    }
    for poly in mesh.polygons:
        poly.material_index = index["case"]
        if not ART_BOTTOM < poly.center.z < ART_TOP:
            continue
        for name, (on, uv_of) in slots.items():
            if on(poly.normal, poly.center):
                poly.material_index = index[name]
                for loop in poly.loop_indices:
                    uv.data[loop].uv = uv_of(mesh.vertices[mesh.loops[loop].vertex_index].co)
                break


def shade(mesh):
    """
    Smooths the rounded corners (the case's and the groove's) and nothing else: an edge is smooth when it joins two
    faces turned round the same corner, at the same tilt, neither of them square to the case. Smoothing a flat face's
    edge would bend its normals over its whole length.
    """
    for p in mesh.polygons:
        p.use_smooth = True
    faces_of = {}
    for p in mesh.polygons:
        for key in p.edge_keys:
            faces_of.setdefault(key, []).append(p)

    def on_corner(n):
        return abs(n.x) > 0.02 and abs(n.z) > 0.02

    for e in mesh.edges:
        faces = faces_of.get(e.key, [])
        smooth = len(faces) == 2 and all(on_corner(f.normal) for f in faces) \
            and abs(faces[0].normal.y - faces[1].normal.y) < 1e-4 and faces[0].normal.angle(faces[1].normal) < math.radians(35)
        e.use_edge_sharp = not smooth


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = os.path.abspath(args[0])
    bpy.ops.wm.read_factory_settings(use_empty=True)

    art = (WIDTH / 2 - ART_OPENING) - (-WIDTH / 2 + FRONT_CHAMFER[0])
    mats = {
        "case": material("case", "#C8CACC", 0.35),
        "cover": material("cover", "#FFFFFF", 0.4, aspect=round(art / (ART_TOP - ART_BOTTOM), 4)),
        "spine": material("spine", "#FFFFFF", 0.4, aspect=SPINE_ASPECT),
        "back": material("back", "#FFFFFF", 0.4, aspect=round(art / (ART_TOP - ART_BOTTOM), 4)),
    }
    case = hull(mats["case"])
    groove(case, mats["case"])
    paint(case, mats)
    shade(case.data)

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    mesh = case.data
    mesh.name = "switch_case"  # the booleans' meshes are numbered
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"Switch case: {triangles(mesh)} triangles, {len(mesh.materials)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm")
    export([case], out)


if __name__ == "__main__":
    main()
