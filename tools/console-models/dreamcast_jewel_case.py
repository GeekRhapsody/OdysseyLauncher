"""Memory-card's PAL Dreamcast jewel case template (godot/themes/memory-card/models/templates/dreamcast_jewel_case.glb).

The jewel case PAL Dreamcast games came in, as one closed solid: the case's outer hull, nothing inside it. Its face is a
CD jewel case's, 142 x 125 mm with small rounded corners and a chamfer round the front and the back, but it's 19 mm
deep, and its tray is an opaque, strong blue: the tray's hinge band shows down the front's left, a pocket the clear lid
stands 1 mm proud of, between a thin clear wall at the case's edge and the lid's hinge knuckles at its ends, with
Dreamcast in a panel moulded into it, read from the bottom up. Round the top, the opening side and the bottom, a seam
where the lid meets the base. The measurements and their references are in dreamcast_jewel_case_layout.py.

The art is the hull's own faces, each sized by ScreenScraper's PAL scans, so none of it is cropped: the `cover` slot is
the booklet under the lid (square, as its 640 x 640 scan), the `back` slot the inlay's back seen through the base (784
x 680), and the `spine` slot the inlay's one spine, seen through the base's hinge side (87 x 680), the inlay 118.6 mm
high; their UVs are projected flat across them, upright from outside. Everything else is `case`, its colours from the
texture dreamcast_jewel_case_print.py draws: the band as the front shows it, and a swatch for each other face (the
clear plastic with the blue tray behind it, its edges and rims, the seam). Every face is flat-shaded, as the generated
boxes are. It faces the front, upright, fitted to the model spec (A7): standing on y = 0, centred, the largest side
(the width) 1 m.

Four materials and one 256 x 1024 texture, within the game template budget. Run from the repo root:

    python tools/console-models/dreamcast_jewel_case_print.py artifacts/console-models/dreamcast_jewel_case
    blender -b --factory-startup --python tools/console-models/dreamcast_jewel_case.py -- artifacts/console-models/dreamcast_jewel_case godot/themes/memory-card/models/templates/dreamcast_jewel_case.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dreamcast_jewel_case_layout as L  # noqa: E402
from mega_drive_cartridge import boolean, box, export, material, new_object, triangles  # noqa: E402

CORNER_SEGMENTS = 3
EPS = 0.01

# Where things are, in the case's millimetres: standing on its bottom at the origin, its front facing -Y and its spine
# (the hinge) on -X.
FRONT, BACK = -L.DEPTH / 2, L.DEPTH / 2
COVER_X = -L.WIDTH / 2 + L.COVER_LEFT
COVER_Z = (L.HEIGHT - L.COVER) / 2
INLAY_Z = (L.HEIGHT - L.INLAY_HEIGHT) / 2
SPINE_BACK = BACK - L.BACK_RIM
SPINE_FRONT = SPINE_BACK - L.SPINE_WIDTH
BAND_X0, BAND_X1 = -L.WIDTH / 2 + L.BAND_LEFT, -L.WIDTH / 2 + L.BAND_RIGHT
SEAM_Y = FRONT + L.SEAM_Y


def outline(inset):
    """The case's outline seen from the front, (x, z) anticlockwise from the bottom right, set in by inset all round."""
    w, r = L.WIDTH / 2 - L.CORNER, L.CORNER - inset
    corners = ((w, L.CORNER, -90), (w, L.HEIGHT - L.CORNER, 0), (-w, L.HEIGHT - L.CORNER, 90), (-w, L.CORNER, 180))
    points = []
    for cx, cz, start in corners:
        for k in range(CORNER_SEGMENTS + 1):
            a = math.radians(start + 90 * k / CORNER_SEGMENTS)
            points.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return points


def hull(mat):
    """The outline at four depths (the front face, the wall's two ends, the back face), joined by the chamfers and the wall."""
    rings = [(FRONT, L.CHAMFER), (FRONT + L.CHAMFER, 0.0), (BACK - L.CHAMFER, 0.0), (BACK, L.CHAMFER)]
    bm = bmesh.new()
    loops = [[bm.verts.new((x, y, z)) for x, z in outline(inset)] for y, inset in rings]
    bm.faces.new(loops[0])
    bm.faces.new(list(reversed(loops[-1])))
    for a, b in zip(loops, loops[1:]):
        n = len(a)
        for i in range(n):
            bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object("dreamcast_jewel_case", bm, mat)


def band(obj, mat):
    """Cuts the band's pocket into the front: the lid's edge on its right, the clear wall on its left, the knuckles at its ends."""
    boolean(obj, box("band", BAND_X0, BAND_X1, FRONT - 1, FRONT + L.BAND_STEP, L.BAND_BOTTOM, L.BAND_TOP, mat))


def seam(obj, mat):
    """
    Cuts the seam where the lid meets the base, SEAM_Y back from the front: a groove round the top, the opening side and
    the bottom, from the band's edge on (the hinge side has none).
    """
    width, depth = L.SEAM
    bm = bmesh.new()
    outer = [[bm.verts.new((x, y, z)) for x, z in outline(-2.0)] for y in (SEAM_Y - width / 2, SEAM_Y + width / 2)]
    inner = [[bm.verts.new((x, y, z)) for x, z in outline(depth)] for y in (SEAM_Y - width / 2, SEAM_Y + width / 2)]
    loops = [outer[0], outer[1], inner[1], inner[0]]
    n = len(outer[0])
    for a, b in zip(loops, loops[1:] + loops[:1]):
        for i in range(n):
            bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ring = new_object("seam", bm, mat)
    boolean(ring, box("open", BAND_X1, L.WIDTH, -L.DEPTH, L.DEPTH, -10, L.HEIGHT + 10, mat), "INTERSECT")
    boolean(obj, ring)


def band_uv(p):
    """A point on the band's pocket floor, in the texture's band region."""
    u = (p.x - BAND_X0) / (BAND_X1 - BAND_X0) * L.BAND_PIXELS / L.ATLAS[0]
    return u, (p.z - L.BAND_BOTTOM) / (L.BAND_TOP - L.BAND_BOTTOM)


def swatch(name):
    uv = L.swatch_uv(name)
    return lambda p: uv


def face(n, c):
    """A face's material and its vertices' UVs, from its normal and its centre."""
    on_front = n.y < -0.99 and c.y < FRONT + L.BAND_STEP + EPS
    on_back = n.y > 0.99 and c.y > BACK - EPS
    if on_front and c.y > FRONT + EPS:
        return "case", band_uv  # the band's pocket floor
    if on_front:
        if COVER_X < c.x < COVER_X + L.COVER and COVER_Z < c.z < COVER_Z + L.COVER:
            return "cover", lambda p: ((p.x - COVER_X) / L.COVER, (p.z - COVER_Z) / L.COVER)
        return "case", swatch("edge" if c.x < BAND_X1 else "clear")  # the wall and knuckles round the band; the lid
    if on_back:
        if abs(c.x) < L.BACK_WIDTH / 2 and INLAY_Z < c.z < INLAY_Z + L.INLAY_HEIGHT:
            return "back", lambda p: ((L.BACK_WIDTH / 2 - p.x) / L.BACK_WIDTH, (p.z - INLAY_Z) / L.INLAY_HEIGHT)
        return "case", swatch("clear")
    if abs(n.y) > 0.99 or abs(c.y - SEAM_Y) < L.SEAM[0] / 2 + EPS and c.x > BAND_X1:
        return "case", swatch("seam")  # the groove's walls and floor
    if abs(n.y) > 0.3:
        return "case", swatch("edge")  # the chamfers round the front and the back
    if c.y < FRONT + L.BAND_STEP and BAND_X0 - EPS < c.x < BAND_X1 + EPS:
        return "case", swatch("edge")  # the pocket's walls
    if n.x < -0.5:  # the hinge side
        if n.x < -0.99 and SPINE_FRONT < c.y < SPINE_BACK and INLAY_Z < c.z < INLAY_Z + L.INLAY_HEIGHT:
            return "spine", lambda p: ((SPINE_BACK - p.y) / L.SPINE_WIDTH, (p.z - INLAY_Z) / L.INLAY_HEIGHT)
        return "case", swatch("band" if c.y < SPINE_FRONT else "clear")
    return "case", swatch("edge" if c.y < SEAM_Y else "clear")  # the lid's flange, then the base


def paint(obj, mats):
    """Cuts the faces along the art's edges and the lid's, then gives every face its material and UVs."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    planes = [(COVER_X, 0), (COVER_X + L.COVER, 0), (-L.BACK_WIDTH / 2, 0), (L.BACK_WIDTH / 2, 0),
              (COVER_Z, 2), (COVER_Z + L.COVER, 2), (INLAY_Z, 2), (INLAY_Z + L.INLAY_HEIGHT, 2),
              (SPINE_FRONT, 1), (SPINE_BACK, 1), (SEAM_Y, 1)]
    for at, axis in planes:
        co, no = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
        co[axis], no[axis] = at, 1.0
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.to_mesh(mesh)
    bm.free()

    for name in ("cover", "back", "spine"):
        mesh.materials.append(mats[name])
    index = {m.name: i for i, m in enumerate(mesh.materials)}
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        name, uv_of = face(poly.normal, poly.center)
        poly.material_index = index[name]
        poly.use_smooth = False
        for loop in poly.loop_indices:
            u, v = uv_of(mesh.vertices[mesh.loops[loop].vertex_index].co)
            uv.data[loop].uv = (min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)

    texture = bpy.data.images.load(os.path.join(images, "dreamcast_jewel_case.png"))
    mats = {
        "case": material("case", "#FFFFFF", 0.3, texture),
        "cover": material("cover", "#FFFFFF", 0.22, aspect=round(L.FRONT_SCAN[0] / L.FRONT_SCAN[1], 4)),
        "back": material("back", "#FFFFFF", 0.22, aspect=round(L.BACK_SCAN[0] / L.BACK_SCAN[1], 4)),
        "spine": material("spine", "#FFFFFF", 0.22, aspect=round(L.SPINE_SCAN[0] / L.SPINE_SCAN[1], 4)),
    }
    case = hull(mats["case"])
    band(case, mats["case"])
    seam(case, mats["case"])
    paint(case, mats)

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    mesh = case.data
    mesh.name = "dreamcast_jewel_case"  # the booleans' meshes are numbered
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"Dreamcast jewel case: {triangles(mesh)} triangles, {len(mesh.materials)} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm")
    export([case], out)


if __name__ == "__main__":
    main()
