"""Memory-card's Mega-CD and Sega CD game case templates (godot/themes/memory-card/models/templates/megacd_case.glb and
segacd_case.glb).

The case each region's games came in, as one closed solid: the case's outer hull, nothing inside it. megacd is the PAL
Mega-CD's double jewel case, a CD jewel case's face, 142 x 125 mm, 16.5 mm deep; segacd the North American Sega CD's
long box, 144 x 207 x 21.5 mm. Both have small rounded corners, a chamfer round the front and the back, and a seam where
the clear lid meets the base round the top, the opening side and the bottom (not the hinge side). The measurements
and their references are in sega_cd_case_layout.py.

The art is the hull's own faces, each sized by ScreenScraper's scans, so none of it is cropped: the `cover` slot is the
front insert under the lid, centred on the front; the `back` slot the inlay's back seen through the base, centred on
the back; and the `spine` slot the inlay's one spine, seen through the base's hinge side; their UVs are projected flat
across them, upright from outside. Everything else is `case`, its colours from the swatches sega_cd_case_print.py draws
(the clear plastic with the black tray behind it, its edges and rims, the seam, the tray). Every face is flat-shaded,
as the generated boxes are. It faces the front, upright, fitted to the model spec (A7): standing on y = 0, centred, the
largest side 1 m.

Four materials and one 64 x 256 texture, within the game template budget. Run from the repo root:

    python tools/console-models/sega_cd_case_print.py artifacts/console-models/sega_cd_case
    blender -b --factory-startup --python tools/console-models/sega_cd_case.py -- megacd artifacts/console-models/sega_cd_case godot/themes/memory-card/models/templates/megacd_case.glb
    blender -b --factory-startup --python tools/console-models/sega_cd_case.py -- segacd artifacts/console-models/sega_cd_case godot/themes/memory-card/models/templates/segacd_case.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sega_cd_case_layout as L  # noqa: E402
from mega_drive_cartridge import boolean, box, export, material, new_object, triangles  # noqa: E402

CORNER_SEGMENTS = 3
EPS = 0.01


class Case:
    """Where things are, in the case's millimetres: standing on its bottom at the origin, its front facing -Y and its
    spine (the hinge) on -X."""

    def __init__(self, kind):
        k = L.KINDS[kind]
        self.width, self.height, self.depth = k["size"]
        self.scans = {"cover": k["front"], "back": k["back"], "spine": k["spine"]}
        inlay = k["inlay"]
        self.front, self.back = -self.depth / 2, self.depth / 2
        self.cover_w = inlay * k["front"][0] / k["front"][1]
        self.back_w = inlay * k["back"][0] / k["back"][1]
        self.spine_w = inlay * k["spine"][0] / k["spine"][1]
        self.inlay = inlay
        self.inlay_z = (self.height - inlay) / 2
        self.spine_back = self.back - L.BACK_RIM
        self.spine_front = self.spine_back - self.spine_w
        self.seam_y = self.front + L.SEAM_Y
        assert max(self.cover_w, self.back_w) < self.width - 2 * L.CHAMFER and self.spine_w < self.depth - 2 * L.CHAMFER, kind

    def outline(self, inset):
        """The case's outline seen from the front, (x, z) anticlockwise from the bottom right, set in by inset all round."""
        w, h, r = self.width / 2 - L.CORNER, self.height, L.CORNER - inset
        corners = ((w, L.CORNER, -90), (w, h - L.CORNER, 0), (-w, h - L.CORNER, 90), (-w, L.CORNER, 180))
        points = []
        for cx, cz, start in corners:
            for k in range(CORNER_SEGMENTS + 1):
                a = math.radians(start + 90 * k / CORNER_SEGMENTS)
                points.append((cx + r * math.cos(a), cz + r * math.sin(a)))
        return points


def hull(c, name, mat):
    """The outline at four depths (the front face, the wall's two ends, the back face), joined by the chamfers and the wall."""
    rings = [(c.front, L.CHAMFER), (c.front + L.CHAMFER, 0.0), (c.back - L.CHAMFER, 0.0), (c.back, L.CHAMFER)]
    bm = bmesh.new()
    loops = [[bm.verts.new((x, y, z)) for x, z in c.outline(inset)] for y, inset in rings]
    bm.faces.new(loops[0])
    bm.faces.new(list(reversed(loops[-1])))
    for a, b in zip(loops, loops[1:]):
        n = len(a)
        for i in range(n):
            bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def seam(c, obj, mat):
    """
    Cuts the seam where the lid meets the base, SEAM_Y back from the front: a groove round the top, the opening side and
    the bottom, from HINGE in from the hinge side on (the lid's knuckles have none).
    """
    width, depth = L.SEAM
    bm = bmesh.new()
    outer = [[bm.verts.new((x, y, z)) for x, z in c.outline(-2.0)] for y in (c.seam_y - width / 2, c.seam_y + width / 2)]
    inner = [[bm.verts.new((x, y, z)) for x, z in c.outline(depth)] for y in (c.seam_y - width / 2, c.seam_y + width / 2)]
    loops = [outer[0], outer[1], inner[1], inner[0]]
    n = len(outer[0])
    for a, b in zip(loops, loops[1:] + loops[:1]):
        for i in range(n):
            bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ring = new_object("seam", bm, mat)
    boolean(ring, box("open", -c.width / 2 + L.HINGE, c.width, -c.depth, c.depth, -10, c.height + 10, mat), "INTERSECT")
    boolean(obj, ring)


def swatch(name):
    uv = L.swatch_uv(name)
    return lambda p: uv


def face(c, n, ctr):
    """A face's material and its vertices' UVs, from its normal and its centre."""
    in_inlay = c.inlay_z < ctr.z < c.inlay_z + c.inlay
    if n.y < -0.99 and ctr.y < c.front + EPS:
        if abs(ctr.x) < c.cover_w / 2 and in_inlay:
            return "cover", lambda p: ((p.x + c.cover_w / 2) / c.cover_w, (p.z - c.inlay_z) / c.inlay)
        return "case", swatch("clear")
    if n.y > 0.99 and ctr.y > c.back - EPS:
        if abs(ctr.x) < c.back_w / 2 and in_inlay:
            return "back", lambda p: ((c.back_w / 2 - p.x) / c.back_w, (p.z - c.inlay_z) / c.inlay)
        return "case", swatch("clear")
    if abs(n.y) > 0.99 or abs(ctr.y - c.seam_y) < L.SEAM[0] / 2 + EPS and ctr.x > -c.width / 2 + L.HINGE:
        return "case", swatch("seam")  # the groove's walls and floor
    if abs(n.y) > 0.3:
        return "case", swatch("edge")  # the chamfers round the front and the back
    if n.x < -0.5:  # the hinge side
        if n.x < -0.99 and c.spine_front < ctr.y < c.spine_back and in_inlay:
            return "spine", lambda p: ((c.spine_back - p.y) / c.spine_w, (p.z - c.inlay_z) / c.inlay)
        return "case", swatch("tray")
    return "case", swatch("edge" if ctr.y < c.seam_y else "clear")  # the lid's flange, then the base


def paint(c, obj, mats):
    """Cuts the faces along the art's edges, then gives every face its material and UVs."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    planes = [(-c.cover_w / 2, 0), (c.cover_w / 2, 0), (-c.back_w / 2, 0), (c.back_w / 2, 0),
              (c.inlay_z, 2), (c.inlay_z + c.inlay, 2), (c.spine_front, 1), (c.spine_back, 1), (c.seam_y, 1)]
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
        name, uv_of = face(c, poly.normal, poly.center)
        poly.material_index = index[name]
        poly.use_smooth = False
        for loop in poly.loop_indices:
            u, v = uv_of(mesh.vertices[mesh.loops[loop].vertex_index].co)
            uv.data[loop].uv = (min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    kind, images, out = args[0], os.path.abspath(args[1]), os.path.abspath(args[2])
    c = Case(kind)
    bpy.ops.wm.read_factory_settings(use_empty=True)

    texture = bpy.data.images.load(os.path.join(images, "sega_cd_case.png"))
    mats = {"case": material("case", "#FFFFFF", 0.3, texture)}
    for name, (w, h) in c.scans.items():
        mats[name] = material(name, "#FFFFFF", 0.22, aspect=round(w / h, 4))
    case = hull(c, f"{kind}_case", mats["case"])
    seam(c, case, mats["case"])
    paint(c, case, mats)

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    mesh = case.data
    mesh.name = f"{kind}_case"  # the boolean's mesh is numbered
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"{kind} case: {triangles(mesh)} triangles, {len(mesh.materials)} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm")
    export([case], out)


if __name__ == "__main__":
    main()
