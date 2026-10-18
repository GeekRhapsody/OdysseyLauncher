"""Memory-card's PlayStation 2 clamshell templates (godot/themes/memory-card/models/templates/ps2_clamshell.glb, black,
and ps2_clamshell_blue.glb, blue).

Sony's PlayStation 2 game case as one closed solid: the case's outer hull, nothing inside it. It's no DVD keep case:
its edges are rounded round the top, the bottom and the opening side (the spine's are crisp, where the clear sleeve
folds round it, so the spine is flat), the two halves meet at a seam round the top, the bottom and the opening side, and
the opening side has a long finger recess, a slot with rounded ends set into the edge between the front's and the back's
rims, the seam running along its floor (the owner's photos of PAL cases, and a photo of an open case on Wikimedia
Commons for where the recess starts and ends). The paper insert is sized by ScreenScraper's PAL scans rather than a
ruler, so none of the art is cropped: a 486 x 680 front and back and a 55 x 680 spine make it 130.8 x 183 x 14.8 mm,
with 3.5 mm of case showing above and below it, so the case is 135 x 190 x 14.8 mm (a real one is about 14 mm deep).
The insert wraps the front, the spine and the back: the `cover`, `spine` and `back` slots, each the hull's own faces,
the front's and the back's reaching round the spine's edges, their UVs projected flat across the insert, the art
spanning it (the default chains). Everything else is `case`: black plastic, or the later PAL cases' blue. The flat faces are
flat-shaded, and only the rounded edges and corners are smooth. It faces the front, upright, fitted to the model spec
(A7): standing on y = 0, centred, the largest side (the height) 1 m.

Four materials and no texture, within the game template budget. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/ps2_clamshell.py -- black godot/themes/memory-card/models/templates/ps2_clamshell.glb
    blender -b --factory-startup --python tools/console-models/ps2_clamshell.py -- blue godot/themes/memory-card/models/templates/ps2_clamshell_blue.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mega_drive_cartridge import boolean, box, export, material, new_object, prism_x, triangles  # noqa: E402

HEIGHT = 190.0
BORDER = 3.5                    # the case showing above and below the insert
INSERT_HEIGHT = HEIGHT - 2 * BORDER
INSERT_WIDTH = INSERT_HEIGHT * 486 / 680  # the front scan's proportions: 130.8 mm
WIDTH = 135.0                   # so 4.2 mm of case shows by the opening side
DEPTH = INSERT_HEIGHT * 55 / 680  # the spine scan's: 14.8 mm, the insert's spine as deep as the case
CORNERS = (2.5, 4.0)            # the corners' radii seen from the front: the spine's side, the opening side's
CORNER_SEGMENTS = 4
EDGE, EDGE_SEGMENTS = 1.5, 2    # the rounded edges round the front and the back, at the top, the bottom and the opening side
SPINE_EDGE = 0.3                # the spine's edges, where the sleeve folds round: the spine's corners blend from one to the other
COLOURS = {"black": "#111114", "blue": "#2A55B5"}  # the case's plastic

# The finger recess in the opening side: where it starts and ends up the case, how deep it is, how far it reaches
# towards the front and the back from the middle of the depth, and its ends' corners (seen from the side).
RECESS = (50.0, 140.0)
RECESS_DEPTH = 3.0
RECESS_HALF_WIDTH = DEPTH / 2 - EDGE - 1.0  # a 1 mm flat rim each side, beyond the rounded edges
RECESS_RADIUS, RECESS_SEGMENTS = 2.0, 3
SEAM = (0.5, 0.4)               # the seam between the halves: its width and its depth


def corner_points():
    """The outline's points seen from the front, anticlockwise from the bottom right: (corner centre, radius, angle) each."""
    s, o = CORNERS
    corners = ((WIDTH / 2 - o, o, o, -90), (WIDTH / 2 - o, HEIGHT - o, o, 0),
               (-WIDTH / 2 + s, HEIGHT - s, s, 90), (-WIDTH / 2 + s, s, s, 180))
    return [(cx, cz, r, math.radians(start + 90 * k / CORNER_SEGMENTS))
            for cx, cz, r, start in corners for k in range(CORNER_SEGMENTS + 1)]


def rounded_rect(inset):
    """The case's outline seen from the front, (x, z) anticlockwise from the bottom right, set in by inset all round."""
    return [(cx + (r - inset) * math.cos(a), cz + (r - inset) * math.sin(a)) for cx, cz, r, a in corner_points()]


def edge_radii():
    """
    Each outline point's edge radius: the spine's along the spine, the others' elsewhere, blending round the spine's
    corners (the top's from the top to the spine, the bottom's from the spine to the bottom).
    """
    radii = []
    for i, (cx, cz, r, a) in enumerate(corner_points()):
        k = i % (CORNER_SEGMENTS + 1)
        corner = i // (CORNER_SEGMENTS + 1)
        t = k / CORNER_SEGMENTS if corner == 2 else 1 - k / CORNER_SEGMENTS if corner == 3 else 0.0
        radii.append(EDGE + (SPINE_EDGE - EDGE) * t)
    return radii


def hull(mat):
    """
    The case in millimetres, standing on its bottom at the origin, its front facing -Y and its spine on -X: the outline
    at each step of the rounded edges, the front face's and the back face's set in by the edges' radius.
    """
    d = DEPTH / 2
    points, radii = corner_points(), edge_radii()

    def ring(side, k):
        """
        The outline k steps round the rounded edge from the face (side -1, the front; 1, the back) to the wall: set in
        by e (1 - sin t) and back from the face by e (1 - cos t), round the edge's centre, e in from both.
        """
        t = math.radians(90 * k / EDGE_SEGMENTS)
        return [bm.verts.new((cx + (r - e * (1 - math.sin(t))) * math.cos(a), side * (d - e * (1 - math.cos(t))),
                              cz + (r - e * (1 - math.sin(t))) * math.sin(a))) for (cx, cz, r, a), e in zip(points, radii)]

    bm = bmesh.new()
    loops = [ring(-1, k) for k in range(EDGE_SEGMENTS + 1)] + [ring(1, k) for k in reversed(range(EDGE_SEGMENTS + 1))]
    bm.faces.new(loops[0])
    bm.faces.new(list(reversed(loops[-1])))
    for a, b in zip(loops, loops[1:]):
        n = len(a)
        for i in range(n):
            bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object("ps2_clamshell", bm, mat)


def recess(case, mat):
    """Cuts the finger recess into the opening side: a slot with rounded corners, seen from the side, straight in."""
    w, r, (z0, z1) = RECESS_HALF_WIDTH, RECESS_RADIUS, RECESS
    outline = []
    for cy, cz, start in ((w - r, z0 + r, -90), (w - r, z1 - r, 0), (-w + r, z1 - r, 90), (-w + r, z0 + r, 180)):
        for k in range(RECESS_SEGMENTS + 1):
            a = math.radians(start + 90 * k / RECESS_SEGMENTS)
            outline.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    boolean(case, prism_x("recess", outline, WIDTH / 2 - RECESS_DEPTH, WIDTH / 2 + 5, mat))


def seam(case, mat):
    """
    Cuts the seam where the halves meet, in the middle of the depth: round the top, the opening side and the bottom (a
    ring round the outline, stopping where the spine's corners start), and along the recess's floor and up its ends.
    """
    width, depth = SEAM
    bm = bmesh.new()
    outer = [[bm.verts.new((x, y, z)) for x, z in rounded_rect(-2.0)] for y in (-width / 2, width / 2)]
    inner = [[bm.verts.new((x, y, z)) for x, z in rounded_rect(depth)] for y in (-width / 2, width / 2)]
    loops = [outer[0], outer[1], inner[1], inner[0]]
    n = len(outer[0])
    for a, b in zip(loops, loops[1:] + loops[:1]):
        for i in range(n):
            bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ring = new_object("seam", bm, mat)
    x0 = -WIDTH / 2 + CORNERS[0]
    boolean(ring, box("open", x0, WIDTH, -DEPTH, DEPTH, -10, HEIGHT + 10, mat), "INTERSECT")
    boolean(case, ring)

    floor = WIDTH / 2 - RECESS_DEPTH
    boolean(case, box("floor", floor - depth, WIDTH / 2 + 1, -width / 2, width / 2, RECESS[0] - depth, RECESS[1] + depth, mat))


def paint(obj, mats):
    """
    Gives the insert's faces their slots: the front, the back and the spine, each between the border at the top and the
    bottom, the front's and the back's stopping short of the opening side and taking the half of the rounded edge to
    the spine that faces their way (the spine's edge is crisp, so these are slivers), with UVs projected flat across the insert's face, upright from outside. The rest
    (the border, the walls, the recess) is case.
    """
    mesh = obj.data
    right = WIDTH / 2 - (WIDTH - INSERT_WIDTH)  # the insert's edge by the opening side
    left = -WIDTH / 2

    # Cut the faces along the insert's edges: its top, its bottom, and its edge by the opening side.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for co, no in (((0, 0, BORDER), (0, 0, 1)), ((0, 0, HEIGHT - BORDER), (0, 0, 1)), ((right, 0, 0), (1, 0, 0))):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.to_mesh(mesh)
    bm.free()

    for name in ("cover", "back", "spine"):
        mesh.materials.append(mats[name])
    index = {m.name: i for i, m in enumerate(mesh.materials)}
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    near = SPINE_EDGE + 0.05

    def main_axis(n):
        return max(range(3), key=lambda i: abs(n[i]))

    # Each slot: whether a face is on it (its normal's main axis and where its centre is), and a vertex's UV.
    slots = {
        "cover": (lambda n, c: main_axis(n) == 1 and n.y < 0 and c.y < -DEPTH / 2 + near,
                  lambda p: ((p.x - left) / INSERT_WIDTH, (p.z - BORDER) / INSERT_HEIGHT)),
        "back": (lambda n, c: main_axis(n) == 1 and n.y > 0 and c.y > DEPTH / 2 - near,
                 lambda p: ((right - p.x) / INSERT_WIDTH, (p.z - BORDER) / INSERT_HEIGHT)),
        "spine": (lambda n, c: main_axis(n) == 0 and n.x < 0 and c.x < -WIDTH / 2 + near,
                  lambda p: ((DEPTH / 2 - p.y) / DEPTH, (p.z - BORDER) / INSERT_HEIGHT)),
    }
    for poly in mesh.polygons:
        poly.material_index = index["case"]
        c = poly.center
        if not BORDER < c.z < HEIGHT - BORDER or c.x > right:
            continue  # the border, the top and bottom walls, the opening side
        for name, (on, uv_of) in slots.items():
            if on(poly.normal, c):
                poly.material_index = index[name]
                for loop in poly.loop_indices:
                    u, v = uv_of(mesh.vertices[mesh.loops[loop].vertex_index].co)
                    uv.data[loop].uv = (min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0))
                break


def shade(mesh):
    """
    Smooths the rounded edges and corners (the case's, the seam's, the recess's) and nothing else: an edge is smooth
    when it joins two faces at less than 50 degrees, neither of them square to the case. Smoothing a flat face's edge
    would bend its normals over its whole length.
    """
    for p in mesh.polygons:
        p.use_smooth = True
    faces_of = {}
    for p in mesh.polygons:
        for key in p.edge_keys:
            faces_of.setdefault(key, []).append(p)

    def square(n):
        return max(abs(n.x), abs(n.y), abs(n.z)) > 0.999

    for e in mesh.edges:
        faces = faces_of.get(e.key, [])
        smooth = len(faces) == 2 and not any(square(f.normal) for f in faces) \
            and faces[0].normal.angle(faces[1].normal) < math.radians(50)
        e.use_edge_sharp = not smooth


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    colour, out = COLOURS[args[0]], os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)

    mats = {
        "case": material("case", colour, 0.4),
        "cover": material("cover", "#FFFFFF", 0.3, aspect=round(INSERT_WIDTH / INSERT_HEIGHT, 4)),
        "back": material("back", "#FFFFFF", 0.3, aspect=round(INSERT_WIDTH / INSERT_HEIGHT, 4)),
        "spine": material("spine", "#FFFFFF", 0.3, aspect=round(DEPTH / INSERT_HEIGHT, 4)),
    }
    case = hull(mats["case"])
    recess(case, mats["case"])
    seam(case, mats["case"])
    paint(case, mats)
    shade(case.data)

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    mesh = case.data
    mesh.name = os.path.splitext(os.path.basename(out))[0]  # the booleans' meshes are numbered
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"PS2 clamshell: {triangles(mesh)} triangles, {len(mesh.materials)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm")
    export([case], out)


if __name__ == "__main__":
    main()
