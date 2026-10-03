"""The console theme's Sega Mega Drive system model (godot/themes/console/models/systems/megadrive.glb).

Built in Blender from the first model's proportions (280 x 212 mm): the body, flat behind and sloping down to its front,
its top side edges chamfered; the vents at the back left, wrapping round the side; the control panel sunk into the
slope at the front left, with the volume slider, the power switch and RESET; the raised round platform with its glossy
black ring, the disc and the slot's lip; the 16-BIT plate running over the ring; and the controller ports and the
headphone socket in the front. The printing (the ring's legend, the plate, the panel's legends, MEGA DRIVE SEGA) is
one texture, drawn by mega_drive_print.py and projected onto the top.

A cartridge (mega_drive_cartridge.py's, with the whole label from mega_drive_label.png) is its own node. At rest it's
shrunk to nothing inside the slot, so the console stands empty and the rest pose's bounds are the console's. The
`focused` clip (6 s, looping) has it appear above the slot, slide in and seat with a push, stay a while, then come
back out and vanish, and the next one appear.

The model is turned to a three-quarter view (TILT_YAW, TILT_PITCH: its right end towards the viewer and its top tipped
up, as the console looks on a table in front of you), then fitted to the model spec (A7): standing on y = 0, centred,
the largest side 1 m. The cartridge's mesh and its clip are turned and scaled the same way.

Seven materials (print, gloss, dark, reset; cart, cart_label, pcb) and two textures, within the system model budget.
Run from the repo root:

    python tools/console-models/mega_drive_print.py artifacts/megadrive
    blender -b --factory-startup --python tools/console-models/mega_drive.py -- artifacts/megadrive godot/themes/console/models/systems/megadrive.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mega_drive_cartridge as cartridge  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, material, new_object, prism_x  # noqa: E402

TILT_YAW = -25.0   # degrees about the vertical: the right end (the slot side) comes towards the viewer
TILT_PITCH = 30.0  # degrees about the horizontal: the top tips up towards the viewer

WIDTH, DEPTH = 280.0, 212.0
TOP = 50.0                                   # the flat top, behind the slope
CENTRE = (34.0, 17.4)                        # the platform's centre (as in mega_drive_print.py)
LIP = (34.0, 38.0, 134.0, 23.0, 57.5)        # the slot's lip: centre, length, width, top
OPENING = (34.0, 37.0, 114.0, 15.0)          # the slot's opening: centre, length, width
INSERTED = 14.0                              # how far the cartridge goes in
ABOVE = 39.0                                 # how far above its seat the cartridge appears
FPS = 30
# The focused clip's keys: (frame, height above the seat in mm, scale).
KEYS = [(0, 0.0, 0.001), (1, ABOVE, 0.001), (8, ABOVE, 1.06), (11, ABOVE, 1.0), (16, ABOVE, 1.0), (38, 0.0, 1.0),
        (41, -2.0, 1.0), (45, 0.0, 1.0), (150, 0.0, 1.0), (164, ABOVE, 1.0), (172, ABOVE, 0.001), (180, ABOVE, 0.001)]


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


def prism_y(name, outline, y0, y1, mat):
    """A solid from an (x, z) outline, extruded along y."""
    obj = prism_z(name, outline, y0, y1, mat)
    obj.data.transform(Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))))  # swaps y and z
    obj.data.flip_normals()
    return obj


def stadium(cx, cy, length, width, segments=10):
    """A rounded slot's outline: a rectangle with semicircular ends."""
    r = width / 2
    points = []
    for end, a0 in ((cx + length / 2 - r, -90), (cx - length / 2 + r, 90)):
        for k in range(segments + 1):
            a = math.radians(a0 + 180 * k / segments)
            points.append((end + r * math.cos(a), cy + r * math.sin(a)))
    return points


def chamfered(corners, cuts):
    """A polygon's outline (x, y) with each corner cut by its own length."""
    points = []
    n = len(corners)
    for i in range(n):
        c, p, q = Vector(corners[i]), Vector(corners[i - 1]), Vector(corners[(i + 1) % n])
        points.append(tuple(c + (p - c).normalized() * cuts[i]))
        points.append(tuple(c + (q - c).normalized() * cuts[i]))
    return points


def lathe(name, profile, centre, mats, segments=96):
    """
    A solid turned from an (r, z) profile about a vertical axis at centre (both ends of the profile on the axis).
    mats(r0, r1, z0, z1) picks each band's material index.
    """
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([bm.verts.new((centre[0], centre[1], z))])
        else:
            rings.append([bm.verts.new((centre[0] + r * math.cos(2 * math.pi * k / segments),
                                        centre[1] + r * math.sin(2 * math.pi * k / segments), z)) for k in range(segments)])
    for i in range(len(profile) - 1):
        a, b = rings[i], rings[i + 1]
        index = mats(profile[i][0], profile[i + 1][0], profile[i][1], profile[i + 1][1])
        for k in range(segments):
            j = (k + 1) % segments
            verts = [v for v in (a[k % len(a)], a[j % len(a)], b[j % len(b)], b[k % len(b)])]
            verts = [v for n, v in enumerate(verts) if v not in verts[:n]]
            bm.faces.new(verts).material_index = index
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build(m):
    # The body: the side outline (flat top, then the slope down to the front) cut by the plan's corners and the top
    # side chamfers.
    body = prism_x("megadrive", [(-106, 0), (106, 0), (106, TOP), (-38, TOP), (-104, 25), (-106, 23)], -141, 141, m["print"])
    plan = chamfered([(-140, -106), (140, -106), (140, 106), (-140, 106)], [9, 9, 15, 10])
    boolean(body, prism_z("plan", plan, -1, 80, m["print"]), "INTERSECT")
    ends = [(-141, -1), (141, -1), (141, TOP - 7), (133, TOP + 1), (-133, TOP + 1), (-141, TOP - 7)]
    boolean(body, prism_y("ends", ends, -107, 107, m["print"]), "INTERSECT")
    bevel(body, 1.5)

    # The platform: the glossy ring round the disc, standing out of the top and the slope.
    platform = [(0, 30), (88, 30), (88, 52), (87, 53), (84, 54.4), (80, 55.4), (76, 55.8), (74, 55.5), (74, 53.5),
                (0, 53.5)]
    ring = lathe("platform", platform, CENTRE, lambda r0, r1, z0, z1: 1 if min(r0, r1) >= 74 else 0)
    ring.data.materials.append(m["print"])
    ring.data.materials.append(m["gloss"])
    boolean(body, ring, "UNION")

    # The slot's lip on the disc.
    x, y, length, width, top = LIP
    lip = prism_z("lip", stadium(x, y, length, width), 52.0, top, m["gloss"])
    bevel(lip, 1.2, angle=30)
    boolean(body, lip, "UNION")

    # The 16-BIT plate: flat over the disc, then following the ring down to its edge.
    plate = box("plate", 1.6, 65.4, -80, -1.6, 50.0, 58.0, m["gloss"])
    cover = [(0, 45), (88.3, 45), (88.3, 53.0), (87, 54.2), (84, 55.6), (80, 56.6), (76, 57.0), (0, 57.0)]
    shape = lathe("cover", cover, CENTRE, lambda *_: 0)
    shape.data.materials.append(m["gloss"])
    boolean(plate, shape, "INTERSECT")
    bevel(plate, 0.8, angle=30)
    boolean(body, plate, "UNION")

    # The slot's opening, deep enough for the cartridge's thin end.
    x, y, length, width = OPENING
    boolean(body, prism_z("opening", stadium(x, y, length, width, 6), 40.0, 70.0, m["dark"]))

    # The vents, back left: a recess over the top and down the side, with slats in it.
    boolean(body, box("vents", -150, -93.5, -16, 85, TOP - 5, 70, m["dark"]))
    boolean(body, box("vents", -150, -136.6, -16, 85, 20, 70, m["dark"]))
    slats = []
    pitch = 101.0 / 22
    outline = [(-139.4, 21), (-136.4, 21), (-136.4, TOP - 6), (-94.0, TOP - 6), (-94.0, TOP - 0.8), (-134.6, TOP - 0.8),
               (-139.4, TOP - 5.6)]
    for i in range(22):
        y = -16 + pitch * (i + 0.5)
        slats.append(prism_y("slat", outline, y - 1.25, y + 1.25, m["print"]))

    # The control panel, sunk into the slope, with the volume slider's and power switch's knobs and RESET.
    floor = 25.5
    boolean(body, box("panel", -121, -50, -98, -37.5, floor, 70, m["print"]))
    parts = []
    for name, (x0, x1, y0, y1, h), mat in (("volume", (-109.4, -96.6, -78.3, -67.6, 5.5), m["gloss"]),
                                           ("power", (-73.0, -60.6, -57.2, -46.1, 4.5), m["gloss"]),
                                           ("reset", (-84.7, -60.5, -90.0, -79.0, 3.0), m["reset"])):
        part = box(name, x0, x1, y0, y1, floor - 1, floor + h, mat)
        bevel(part, 0.8, angle=30)
        parts.append(part)

    # The controller ports and the headphone socket, in the front.
    for x in (22.0, 66.0):
        port = [(x - 16, 6), (x + 16, 6), (x + 14, 16), (x - 14, 16)]
        boolean(body, prism_y("port", port, -110, -101, m["dark"]))
    jack = [(-112 + 2.6 * math.cos(math.radians(a)), 12 + 2.6 * math.sin(math.radians(a))) for a in range(0, 360, 30)]
    boolean(body, prism_y("jack", jack, -110, -101, m["dark"]))

    console = join([body] + slats + parts, "megadrive")

    # Everything's top is printed: the planar projection from above (as mega_drive_print.py draws it).
    mesh = console.data
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        co = mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((co.x + WIDTH / 2) / WIDTH, (co.y + DEPTH / 2) / DEPTH)
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(35))
    return console


def animate(cart, place):
    """The focused clip: place(height above the seat) is where the cartridge's node goes."""
    cart.animation_data_create()
    for frame, height, scale in KEYS:
        cart.location = place(height)
        cart.scale = (scale, scale, scale)
        cart.keyframe_insert("location", frame=frame)
        cart.keyframe_insert("scale", frame=frame)
    cart.animation_data.action.name = "focused"


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    print_image = bpy.data.images.load(os.path.join(images, "megadrive_print.png"))
    label_image = bpy.data.images.load(os.path.join(images, "megadrive_label.png"))

    m = {
        "print": material("print", "#FFFFFF", 0.55, print_image),
        "gloss": material("gloss", "#FFFFFF", 0.18, print_image),
        "dark": material("dark", "#060607", 0.9),
        "reset": material("reset", "#C4C5BC", 0.5),
    }
    console = build(m)
    cart = cartridge.build({"case": material("cart", "#141416", 0.45),
                            "label": material("cart_label", "#FFFFFF", 0.4, label_image),
                            "pcb": material("pcb", "#B8924A", 0.35)}, whole_label=True)

    # The three-quarter view, then the spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    mesh = console.data
    mesh.transform(tilt)
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    fit = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    mesh.transform(fit)
    whole = fit @ tilt

    # The cartridge: its mesh turned and scaled like the console's, its node moving along the console's up.
    cart.data.transform(Matrix.Scale(1 / max(size), 4) @ tilt)
    seat = Vector((OPENING[0], OPENING[1], LIP[4] - INSERTED))
    animate(cart, lambda height: whole @ (seat + Vector((0, 0, height))))
    scene.frame_start, scene.frame_end = KEYS[0][0], KEYS[-1][0]
    scene.frame_set(0)

    tris = cartridge.triangles(mesh) + cartridge.triangles(cart.data)
    print(f"Mega Drive: {tris} triangles ({cartridge.triangles(cart.data)} the cartridge), "
          f"{len(mesh.materials) + len(cart.data.materials)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    cartridge.export([console, cart], out, animations=True)


main()
