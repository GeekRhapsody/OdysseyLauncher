"""The console theme's Windows system model (godot/themes/console/models/systems/windows.glb): a gaming PC and its monitor.

A mid-tower (230 x 440 x 480 mm, on four feet) with a glass side, so its inside shows: the motherboard on the back
wall, a dual-fan tower cooler, the graphics card and RAM, the power supply shroud along the bottom, and the front
fans' backs. Its front is a hexagonal mesh over three fans with lit rings, and its top a vent with the power button and
ports. Beside it, a 24-inch 16:9 monitor (528 x 297 mm lit) on a neck and an oval base, showing a desktop. The
printing is two textures drawn by windows_pc_print.py: the tower's faces in one atlas (windows_pc_layout.py), the
desktop in the other. The glass itself isn't modelled (the launcher draws no transparency, A7), so the side is open.

As in the reference photo, the monitor stands in front and to the left, turned a little to the right (MONITOR_YAW), and
the tower behind it on the right, its glass side towards the viewer and its front turned to the right (TOWER_YAW).
The set is seen head-on and level, as in the photo (not tipped towards the viewer like the consoles), and fitted to
the model spec (A7): standing on y = 0, centred, the largest side 1 m. No clips: the RGB lights are lit but still.

Three materials (case, print, screen) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/windows_pc_print.py artifacts/windows
    blender -b --factory-startup --python tools/console-models/windows_pc.py -- artifacts/windows godot/themes/console/models/systems/windows.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windows_pc_layout as L  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

MONITOR_YAW, MONITOR_AT = 18.0, (-200.0, -70.0)
TOWER_YAW, TOWER_AT = 45.0, (210.0, 150.0)

SCREEN_BOTTOM = 119.0                 # the screen's lit area: 528 x 297 mm, centred, its bottom this high


def textured(name, quads, image_size, mat):
    """
    Flat quads printed from an image: each is (origin, right, up, width, height, region), its corners origin,
    origin + right * width, ... (right x up faces out), showing that region (x, y, w, h in the image's pixels).
    """
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    iw, ih = image_size
    for origin, right, up, w, h, (x, y, rw, rh) in quads:
        o, r, u = Vector(origin), Vector(right), Vector(up)
        face = bm.faces.new([bm.verts.new(p) for p in (o, o + r * w, o + r * w + u * h, o + u * h)])
        u0, u1 = (x + 0.5) / iw, (x + rw - 0.5) / iw
        v0, v1 = 1 - (y + rh - 0.5) / ih, 1 - (y + 0.5) / ih
        for loop, coords in zip(face.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
            loop[uv].uv = coords
    return new_object(name, bm, mat)


def prism_z(name, outline, z0, z1, mat):
    """A solid from an (x, y) outline, extruded along z."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y, z0)) for x, y in outline]
    b = [bm.verts.new((x, y, z1)) for x, y in outline]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        bm.faces.new([a[i], b[i], b[j], a[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def tower(m):
    """The tower, its front facing -Y, its glass side -X, standing on z = 0."""
    body = box("tower", -115, 115, -220, 220, 12, 480, m["case"])
    bevel(body, 3.0)
    boolean(body, box("window", -125, 95, -200, 205, 30, 470, m["case"]))
    front = box("front", -118, 118, -227, -219, 10, 480, m["case"])
    bevel(front, 2.0)
    parts = [body, front]
    for x in (-85, 85):
        for y in (-180, 180):
            foot = box("foot", x - 18, x + 18, y - 25, y + 25, 0, 13, m["case"])
            bevel(foot, 2.0)
            parts.append(foot)
    for name, extent, width in (("shroud", (-113, 95, -200, 205, 30, 135), 1.5),
                                ("gpu", (-35, 95, -190, 135, 205, 262), 1.5),
                                ("cooler", (-55, 95, -125, 145, 305, 435), 1.5),
                                ("ram", (60, 95, -152, -146, 320, 440), 0.8),
                                ("ram", (60, 95, -140, -134, 320, 440), 0.8)):
        part = box(name, *extent, m["case"])
        bevel(part, width)
        parts.append(part)

    x, y, z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    back, inward = (0, -1, 0), (-1, 0, 0)     # seen through the glass, right is the front (-Y)
    size = (L.ATLAS, L.ATLAS)
    quads = [((-118, -227.3, 10), x, z, 236, 470, L.FRONT),
             ((-115, -220, 480.3), x, y, 230, 440, L.TOP),
             ((94.7, 205, 30), back, z, 405, 440, L.MOBO),
             ((95, -199.7, 30), inward, z, 210, 440, L.INNER_FRONT),
             ((-113.3, 205, 30), back, z, 405, 105, L.SHROUD),
             ((-35.3, 135, 205), back, z, 325, 57, L.GPU),
             ((-55, -125, 435.3), x, y, 150, 270, L.FINS),
             ((-55.3, 17, 307), back, z, 14, 126, L.PLATE)]
    for centre in (-60, 80):                  # the cooler's two fans, facing the glass
        quads.append(((-55.3, centre + 63, 307), back, z, 126, 126, L.FAN))
    parts.append(textured("tower_print", quads, size, m["print"]))
    return join(parts, "tower")


def monitor(m):
    """The monitor, facing -Y, standing on z = 0."""
    base = [(125 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a)),
             40 + 85 * math.copysign(abs(math.sin(a)) ** 0.5, math.sin(a)))
            for a in (2 * math.pi * k / 48 for k in range(48))]
    plate = prism_z("base", base, 0, 7, m["case"])
    bevel(plate, 2.0, angle=60)
    neck = box("neck", -22, 22, 30, 50, 5, 300, m["case"])
    bevel(neck, 3.0)
    panel = box("panel", -274, 274, -7, 7, 100, 426, m["case"])
    bevel(panel, 2.0)
    housing = box("housing", -150, 150, 5, 30, 170, 360, m["case"])
    bevel(housing, 6.0, segments=3)
    w, h = L.SCREEN_MM
    screen = textured("screen", [((-w / 2, -7.3, SCREEN_BOTTOM), (1, 0, 0), (0, 0, 1), w, h, (0, 0) + L.SCREEN_PX)],
                      L.SCREEN_PX, m["screen"])
    return join([panel, plate, neck, housing, screen], "monitor")


def placed(obj, yaw, at):
    obj.data.transform(Matrix.Translation((at[0], at[1], 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))
    return obj


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    m = {
        "case": material("case", "#1A1B1F", 0.5),
        "print": material("print", "#FFFFFF", 0.55, bpy.data.images.load(os.path.join(images, "pc_print.png"))),
        "screen": material("screen", "#FFFFFF", 0.3, bpy.data.images.load(os.path.join(images, "pc_screen.png"))),
    }
    pc = join([placed(monitor(m), MONITOR_YAW, MONITOR_AT), placed(tower(m), TOWER_YAW, TOWER_AT)], "windows")
    mesh = pc.data
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(35))

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"Windows PC: {triangles(mesh)} triangles, {len(mesh.materials)} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm before the fit")
    export([pc], out)


main()
