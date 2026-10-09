"""Memory-card's Mega Drive clamshell template (godot/themes/memory-card/models/templates/megadrive_clamshell.glb).

The Sega plastic clamshell, European Mega Drive and US Genesis, as one solid: the case's outer hull, nothing inside it.
The paper insert is sized by ScreenScraper's scans rather than a ruler, so none of the art is cropped: a 484 x 680
front, a 481 x 680 back and an 81 x 680 spine make it 131 x 184 x 21.9 mm, and the case, 3 mm of black plastic
showing round it at the top, the bottom and the opening side, 134 x 190 x 21.9 mm. Its shape follows reference photos of the case: 
the spine is one flat wall, the paper insert's (under the clear sleeve); the top, the bottom and
the opening side are the two halves' walls, set back between a rim round each face and meeting at a seam; and the shop
hanger tab stands up from the back half's top edge, with its hook hole. The insert wraps the front, the spine and the
back: the `cover`, `spine` and `back` slots, each its face but the border (the front's and the back's reaching round
the rounded edges to the spine), its art spanning it (the default chains). Everything else is `case`, black plastic.
Every face is flat-shaded, as the generated boxes are: smooth normals bent towards the rounded edges would be spread
over the long triangles across the faces, and catch the light as hot spots. It faces the front, upright, fitted
to the model spec (A7): standing on y = 0, centred, the largest side (the height, with the tab) 1 m.

Four materials and no texture, within the game template budget. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/mega_drive_clamshell.py -- godot/themes/memory-card/models/templates/megadrive_clamshell.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mega_drive_cartridge import bevel, boolean, box, export, material, new_object, triangles  # noqa: E402

HEIGHT = 190.0
BORDER = 3.0                    # the case showing round the insert at the top, the bottom and the opening side
INSERT_HEIGHT = HEIGHT - 2 * BORDER
INSERT_WIDTH = INSERT_HEIGHT * 484 / 680  # the front scan's proportions: 131 mm
WIDTH = INSERT_WIDTH + BORDER   # 134 mm
DEPTH = INSERT_HEIGHT * 81 / 680  # the spine scan's: 21.9 mm, the insert's spine as deep as the case
EDGE = 0.6                      # the case's rounded edges
RIM = 1.2                       # each face's rim, round the top, the bottom and the opening side
SPINE_WALL = 1.2                # the spine wall's thickness, where the recess stops
RECESS = (1.0, 1.5, 1.8)        # how far the walls are set back: at the rims, at the seam on the front half, on the back half

# The hanger tab (35% of the width), as thick as the back's rim, with its corners rounded.
TAB_WIDTH, TAB_HEIGHT, TAB_RADIUS = 47.7, 15.4, 1.8
SLOT = (13.1, 6.9, 2.8)         # the hook hole's slot: its ends' centres (+-x), its centre's height above the case, its radius
HOOK = (9.8, 2.8)               # the round notch over the slot's middle, for the hook: its centre's height, its radius


def prism(name, outline, extrusion, mat):
    """A solid from a closed 3D outline, extruded by a vector."""
    bm = bmesh.new()
    a = [bm.verts.new(p) for p in outline]
    b = [bm.verts.new(Vector(p) + Vector(extrusion)) for p in outline]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        bm.faces.new([a[i], b[i], b[j], a[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def arc(cx, cz, r, a0, a1, segments):
    """Points round an arc in the (x, z) plane, from angle a0 to a1 (degrees), both ends included."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / segments)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / segments))) for k in range(segments + 1)]


def walls(depth_of):
    """The recessed walls' cross-section, (y, depth in from the outside), from the front's rim to the back's."""
    front, back = -DEPTH / 2 + RIM, DEPTH / 2 - RIM
    return [(front, -5.0), (front, depth_of(0)), (0.0, depth_of(1)), (0.0, depth_of(2)), (back, depth_of(0)), (back, -5.0)]


def build(mats):
    """The case in millimetres, standing on its bottom at the origin, its front facing -Y and its spine on -X."""
    body = box("clamshell", -WIDTH / 2, WIDTH / 2, -DEPTH / 2, DEPTH / 2, 0.0, HEIGHT, mats["case"])
    bevel(body, EDGE)

    # The two halves' walls, set back between the rims on the top, the bottom and the opening side (+X).
    section = walls(lambda k: RECESS[k])
    x0, x1 = -WIDTH / 2 + SPINE_WALL, WIDTH / 2 + 5
    top = [(x0, y, HEIGHT - d) for y, d in section]
    bottom = [(x0, y, d) for y, d in section]
    opening = [(WIDTH / 2 - d, y, -5.0) for y, d in section]
    boolean(body, prism("top", top, (x1 - x0, 0, 0), mats["case"]))
    boolean(body, prism("bottom", bottom, (x1 - x0, 0, 0), mats["case"]))
    boolean(body, prism("opening", opening, (0, 0, HEIGHT + 10), mats["case"]))

    # The hanger tab, the back's rim carried up, with the hook hole through it: a slot with a round notch over its middle.
    w = TAB_WIDTH / 2
    outline = [(-w, HEIGHT - 1.0), (w, HEIGHT - 1.0)] + arc(w - TAB_RADIUS, HEIGHT + TAB_HEIGHT - TAB_RADIUS, TAB_RADIUS, 0, 90, 4) \
        + arc(-w + TAB_RADIUS, HEIGHT + TAB_HEIGHT - TAB_RADIUS, TAB_RADIUS, 90, 180, 4)
    back = DEPTH / 2 - RIM
    tab = prism("tab", [(x, back, z) for x, z in outline], (0, RIM, 0), mats["case"])
    bevel(tab, 0.3, segments=1)
    sx, sz, sr = SLOT
    slot = arc(sx, HEIGHT + sz, sr, -90, 90, 8) + arc(-sx, HEIGHT + sz, sr, 90, 270, 8)
    boolean(tab, prism("slot", [(x, back - 1, z) for x, z in slot], (0, RIM + 2, 0), mats["case"]))
    hz, hr = HOOK
    boolean(tab, prism("hook", [(x, back - 1, z) for x, z in arc(0, HEIGHT + hz, hr, 0, 360, 16)[:-1]], (0, RIM + 2, 0), mats["case"]))
    boolean(body, tab, "UNION")
    return body


def paint(obj, mats):
    """
    Gives the insert's faces their slots: the front, the back and the spine, each but the border, the front's and the
    back's with the half of the rounded edge to the spine that faces their way, and UVs projected flat across the
    insert's face, upright from outside. The rest (the border, the walls and the tab) is case.
    """
    mesh = obj.data

    # Cut the faces along the insert's edges: its top and bottom, and the opening side's.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for co, no in (((0, 0, BORDER), (0, 0, 1)), ((0, 0, HEIGHT - BORDER), (0, 0, 1)), ((WIDTH / 2 - BORDER, 0, 0), (1, 0, 0))):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.to_mesh(mesh)
    bm.free()

    for name in ("cover", "back", "spine"):
        mesh.materials.append(mats[name])
    index = {m.name: i for i, m in enumerate(mesh.materials)}
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    near = EDGE + 0.05
    left, right = -WIDTH / 2, WIDTH / 2 - BORDER  # the insert's front, seen from the front

    # Each slot: whether a face is on it (its normal's main axis and where it is), and a vertex's UV.
    slots = {
        "cover": (lambda n, c: n.y < 0 and abs(n.y) == max(abs(n.x), abs(n.y), abs(n.z)) and c.y < -DEPTH / 2 + near,
                  lambda p: ((p.x - left) / INSERT_WIDTH, (p.z - BORDER) / INSERT_HEIGHT)),
        "back": (lambda n, c: n.y > 0 and abs(n.y) == max(abs(n.x), abs(n.y), abs(n.z)) and c.y > DEPTH / 2 - near,
                 lambda p: ((right - p.x) / INSERT_WIDTH, (p.z - BORDER) / INSERT_HEIGHT)),
        "spine": (lambda n, c: n.x < 0 and abs(n.x) == max(abs(n.x), abs(n.y), abs(n.z)) and c.x < -WIDTH / 2 + near,
                  lambda p: ((DEPTH / 2 - p.y) / DEPTH, (p.z - BORDER) / INSERT_HEIGHT)),
    }
    for poly in mesh.polygons:
        poly.material_index = index["case"]
        c = poly.center
        if not BORDER < c.z < HEIGHT - BORDER or c.x > right:
            continue  # the border, the top and bottom walls, the tab
        for name, (on, uv_of) in slots.items():
            if on(poly.normal, poly.center):
                poly.material_index = index[name]
                for loop in poly.loop_indices:
                    u, v = uv_of(mesh.vertices[mesh.loops[loop].vertex_index].co)
                    uv.data[loop].uv = (min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0))
                break


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = os.path.abspath(args[0])
    bpy.ops.wm.read_factory_settings(use_empty=True)

    mats = {
        "case": material("case", "#0E0E10", 0.45),
        "cover": material("cover", "#FFFFFF", 0.3, aspect=round(INSERT_WIDTH / INSERT_HEIGHT, 4)),
        "back": material("back", "#FFFFFF", 0.3, aspect=round(INSERT_WIDTH / INSERT_HEIGHT, 4)),
        "spine": material("spine", "#FFFFFF", 0.3, aspect=round(DEPTH / INSERT_HEIGHT, 4)),
    }
    case = build(mats)
    paint(case, mats)
    for p in case.data.polygons:
        p.use_smooth = False

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    mesh = case.data
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"Mega Drive clamshell: {triangles(mesh)} triangles, {len(mesh.materials)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm")
    export([case], out)


if __name__ == "__main__":
    main()
