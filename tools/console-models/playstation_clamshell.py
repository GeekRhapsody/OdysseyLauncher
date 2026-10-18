"""Memory-card's PlayStation 2 and PSP clamshell templates (godot/themes/memory-card/models/templates/ps2_clamshell.glb,
black, ps2_clamshell_blue.glb, blue, and psp_clamshell.glb, grey).

Sony's PlayStation 2 and PSP game cases share a hull, in different proportions, each as one closed solid: the case's
outer hull, nothing inside it. Neither is a DVD keep case: their edges are rounded round the top, the bottom and the
opening side (the spine's are crisp, where the clear sleeve folds round it, so the spine is flat), the two halves meet
at a seam round the top, the bottom and the opening side, and the opening side has a long finger recess, a slot with
rounded ends set into the edge between the front's and the back's rims, the seam running along its floor (the owner's
photos of PAL PS2 cases; for where the recesses start and end, a photo of an open PS2 case on Wikimedia Commons and a
retailer's photo of an open PSP case). Each paper insert is sized by ScreenScraper's scans rather than a ruler, so none
of the art is cropped, with the case showing round it at the top, the bottom and the opening side:
- PS2: a 486 x 680 front and back and a 55 x 680 spine make it 130.8 x 183 x 14.8 mm, and the case 135 x 190 x 14.8 mm
  (a real one is about 14 mm deep). Black plastic, or the later PAL cases' blue.
- PSP: a 398 x 680 front and back and a 59 x 680 spine make it 100.7 x 172 x 14.9 mm, and the case 104 x 180 x 14.9 mm
  (a retailer gives 104 x 178 x 15). The real case is clear; its plastic is a light grey here, a stand-in.
The insert wraps the front, the spine and the back: the `cover`, `spine` and `back` slots, each the hull's own faces,
the front's and the back's reaching round the spine's edges, their UVs projected flat across the insert, the art
spanning it (the default chains). Everything else is `case`. The flat faces are flat-shaded, and only the rounded edges
and corners are smooth. It faces the front, upright, fitted to the model spec (A7): standing on y = 0, centred, the
largest side (the height) 1 m.

Four materials and no texture, within the game template budget. Run from the repo root, once per case:

    blender -b --factory-startup --python tools/console-models/playstation_clamshell.py -- ps2 godot/themes/memory-card/models/templates/ps2_clamshell.glb
    blender -b --factory-startup --python tools/console-models/playstation_clamshell.py -- ps2_blue godot/themes/memory-card/models/templates/ps2_clamshell_blue.glb
    blender -b --factory-startup --python tools/console-models/playstation_clamshell.py -- psp godot/themes/memory-card/models/templates/psp_clamshell.glb
"""

import math
import os
import sys
from dataclasses import dataclass

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mega_drive_cartridge import boolean, box, export, material, new_object, prism_x, triangles  # noqa: E402

CORNER_SEGMENTS = 4
EDGE_SEGMENTS = 2
RECESS_SEGMENTS = 3


@dataclass(frozen=True)
class Case:
    """A case's measurements, in millimetres."""
    name: str
    height: float
    width: float
    border: float               # the case showing above and below the insert
    front: tuple                # the front scan's size in pixels (the back's is cropped to it)
    spine: tuple                # the spine scan's
    recess: tuple               # where the finger recess starts and ends up the case
    colour: str                 # the case's plastic
    roughness: float
    corners: tuple = (2.5, 4.0)  # the corners' radii seen from the front: the spine's side, the opening side's
    edge: float = 1.5           # the rounded edges round the front and the back, at the top, the bottom and the opening side
    spine_edge: float = 0.3     # the spine's edges, where the sleeve folds round: the spine's corners blend from one to the other
    recess_depth: float = 3.0
    recess_rim: float = 1.0     # the flat rim each side of the recess, beyond the rounded edges
    recess_radius: float = 2.0  # the recess's ends' corners, seen from the side
    seam: tuple = (0.5, 0.4)    # the seam between the halves: its width and its depth

    @property
    def insert_height(self):
        return self.height - 2 * self.border

    @property
    def insert_width(self):
        return self.insert_height * self.front[0] / self.front[1]

    @property
    def depth(self):
        """The spine scan's proportions: the insert's spine as deep as the case."""
        return self.insert_height * self.spine[0] / self.spine[1]


CASES = {
    "ps2": Case("PS2 clamshell", 190.0, 135.0, 3.5, (486, 680), (55, 680), (50.0, 140.0), "#111114", 0.4),
    "ps2_blue": Case("PS2 clamshell (blue)", 190.0, 135.0, 3.5, (486, 680), (55, 680), (50.0, 140.0), "#2A55B5", 0.4),
    "psp": Case("PSP clamshell", 180.0, 104.0, 4.0, (398, 680), (59, 680), (40.0, 145.0), "#A4A8AE", 0.25),
}


def corner_points(case):
    """The outline's points seen from the front, anticlockwise from the bottom right: (corner centre, radius, angle) each."""
    s, o = case.corners
    w, h = case.width, case.height
    corners = ((w / 2 - o, o, o, -90), (w / 2 - o, h - o, o, 0), (-w / 2 + s, h - s, s, 90), (-w / 2 + s, s, s, 180))
    return [(cx, cz, r, math.radians(start + 90 * k / CORNER_SEGMENTS))
            for cx, cz, r, start in corners for k in range(CORNER_SEGMENTS + 1)]


def rounded_rect(case, inset):
    """The case's outline seen from the front, (x, z) anticlockwise from the bottom right, set in by inset all round."""
    return [(cx + (r - inset) * math.cos(a), cz + (r - inset) * math.sin(a)) for cx, cz, r, a in corner_points(case)]


def edge_radii(case):
    """
    Each outline point's edge radius: the spine's along the spine, the others' elsewhere, blending round the spine's
    corners (the top's from the top to the spine, the bottom's from the spine to the bottom).
    """
    radii = []
    for i in range(len(corner_points(case))):
        k = i % (CORNER_SEGMENTS + 1)
        corner = i // (CORNER_SEGMENTS + 1)
        t = k / CORNER_SEGMENTS if corner == 2 else 1 - k / CORNER_SEGMENTS if corner == 3 else 0.0
        radii.append(case.edge + (case.spine_edge - case.edge) * t)
    return radii


def hull(case, mat):
    """
    The case in millimetres, standing on its bottom at the origin, its front facing -Y and its spine on -X: the outline
    at each step of the rounded edges, the front face's and the back face's set in by the edges' radius.
    """
    d = case.depth / 2
    points, radii = corner_points(case), edge_radii(case)

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
    return new_object("clamshell", bm, mat)


def recess(case, obj, mat):
    """Cuts the finger recess into the opening side: a slot with rounded corners, seen from the side, straight in."""
    w = case.depth / 2 - case.edge - case.recess_rim
    r, (z0, z1) = case.recess_radius, case.recess
    outline = []
    for cy, cz, start in ((w - r, z0 + r, -90), (w - r, z1 - r, 0), (-w + r, z1 - r, 90), (-w + r, z0 + r, 180)):
        for k in range(RECESS_SEGMENTS + 1):
            a = math.radians(start + 90 * k / RECESS_SEGMENTS)
            outline.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    boolean(obj, prism_x("recess", outline, case.width / 2 - case.recess_depth, case.width / 2 + 5, mat))


def seam(case, obj, mat):
    """
    Cuts the seam where the halves meet, in the middle of the depth: round the top, the opening side and the bottom (a
    ring round the outline, stopping where the spine's corners start), and along the recess's floor and up its ends.
    """
    width, depth = case.seam
    bm = bmesh.new()
    outer = [[bm.verts.new((x, y, z)) for x, z in rounded_rect(case, -2.0)] for y in (-width / 2, width / 2)]
    inner = [[bm.verts.new((x, y, z)) for x, z in rounded_rect(case, depth)] for y in (-width / 2, width / 2)]
    loops = [outer[0], outer[1], inner[1], inner[0]]
    n = len(outer[0])
    for a, b in zip(loops, loops[1:] + loops[:1]):
        for i in range(n):
            bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ring = new_object("seam", bm, mat)
    x0 = -case.width / 2 + case.corners[0]
    boolean(ring, box("open", x0, case.width, -case.depth, case.depth, -10, case.height + 10, mat), "INTERSECT")
    boolean(obj, ring)

    floor, (z0, z1) = case.width / 2 - case.recess_depth, case.recess
    boolean(obj, box("floor", floor - depth, case.width / 2 + 1, -width / 2, width / 2, z0 - depth, z1 + depth, mat))


def paint(case, obj, mats):
    """
    Gives the insert's faces their slots: the front, the back and the spine, each between the border at the top and the
    bottom, the front's and the back's stopping short of the opening side and taking the half of the spine's edge that
    faces their way (a sliver, as the edge is crisp), with UVs projected flat across the insert's face, upright from
    outside. The rest (the border, the walls, the recess) is case.
    """
    mesh = obj.data
    border, height, width, depth = case.border, case.insert_height, case.insert_width, case.depth
    right = case.width / 2 - (case.width - width)  # the insert's edge by the opening side
    left = -case.width / 2

    # Cut the faces along the insert's edges: its top, its bottom, and its edge by the opening side.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for co, no in (((0, 0, border), (0, 0, 1)), ((0, 0, case.height - border), (0, 0, 1)), ((right, 0, 0), (1, 0, 0))):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.to_mesh(mesh)
    bm.free()

    for name in ("cover", "back", "spine"):
        mesh.materials.append(mats[name])
    index = {m.name: i for i, m in enumerate(mesh.materials)}
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    near = case.spine_edge + 0.05

    def main_axis(n):
        return max(range(3), key=lambda i: abs(n[i]))

    # Each slot: whether a face is on it (its normal's main axis and where its centre is), and a vertex's UV.
    slots = {
        "cover": (lambda n, c: main_axis(n) == 1 and n.y < 0 and c.y < -depth / 2 + near,
                  lambda p: ((p.x - left) / width, (p.z - border) / height)),
        "back": (lambda n, c: main_axis(n) == 1 and n.y > 0 and c.y > depth / 2 - near,
                 lambda p: ((right - p.x) / width, (p.z - border) / height)),
        "spine": (lambda n, c: main_axis(n) == 0 and n.x < 0 and c.x < -case.width / 2 + near,
                  lambda p: ((depth / 2 - p.y) / depth, (p.z - border) / height)),
    }
    for poly in mesh.polygons:
        poly.material_index = index["case"]
        c = poly.center
        if not border < c.z < case.height - border or c.x > right:
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
    case, out = CASES[args[0]], os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)

    face = round(case.insert_width / case.insert_height, 4)
    mats = {
        "case": material("case", case.colour, case.roughness),
        "cover": material("cover", "#FFFFFF", 0.3, aspect=face),
        "back": material("back", "#FFFFFF", 0.3, aspect=face),
        "spine": material("spine", "#FFFFFF", 0.3, aspect=round(case.depth / case.insert_height, 4)),
    }
    obj = hull(case, mats["case"])
    recess(case, obj, mats["case"])
    seam(case, obj, mats["case"])
    paint(case, obj, mats)
    shade(obj.data)

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    mesh = obj.data
    obj.name = mesh.name = os.path.splitext(os.path.basename(out))[0]  # the booleans' meshes are numbered
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"{case.name}: {triangles(mesh)} triangles, {len(mesh.materials)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm")
    export([obj], out)


if __name__ == "__main__":
    main()
