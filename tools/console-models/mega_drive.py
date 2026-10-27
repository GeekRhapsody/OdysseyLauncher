"""The console theme's Sega Mega Drive system model (godot/themes/console/models/systems/megadrive.glb): the first Mega
Drive and its control pad. build(), the console alone, is the 32X's and Mega-CD's cards' too (sega32x.py, mega_cd.py).

Built in Blender from the first model's proportions (280 x 212 mm) and photographs of the European one (Evan-Amos's and
Bill Bertram's on Wikimedia Commons, from the front left; its underside, Solomon203's): the black body, flat behind and
sloping down to its front, its top side edges chamfered, standing on four rubber feet; the seam between its two halves
running round it; the vents at the back left, wrapping round the side; the control panel sunk a little into the slope
at the front left, its floor following the slope, with the volume slider, the power switch and RESET standing out of it;
the raised round platform with its glossy black ring, the disc and the slot's lip, the slot's two dust flaps meeting in
the middle; the 16-BIT plate running over the ring; the controller ports and the headphone socket in the front; the A/V,
RF and power sockets in the back; the expansion port's cover in the right end; and underneath, the feet, the screws, the
two vents and the labels. The printing (the plate, the panel's legends, MEGA DRIVE SEGA) is one texture, drawn by
mega_drive_print.py and projected onto every face that looks up; the rest take the body's black, or the ring's.

The card (main(); mega_drive_layout.py has its measurements) adds the three-button control pad in front of it at its
left: its smoothed outline raised with a rounded profile, the D-pad, A, B and C, START, its printing its own texture;
its cable runs from its strain relief to its 9-pin plug in CONTROL 1 (plugs.py's). The power switch, RESET and the
flaps are build()'s, left apart; the POWER light sits on the plate's white strip. The cartridge is
mega_drive_cartridge.py's, a made-up game, Odyssey, on its label (mega_drive_print.py's megadrive_odyssey.png); seated,
it sinks into the slot as a real one does, its thin lower half and the label's band out of sight.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting over the slot, shrunk to nothing), the flaps (each on its hinge), the power switch,
RESET, the POWER light (lit and unlit, swapped by depth), and the pad's D-pad, A, B and C.

The `focused` clip (8 s, looping): the cartridge drops into the slot, pushing the flaps down, and seats with a push; the
power switch slides to ON and the light comes on; the D-pad rocks while A, B and C fire; RESET; the switch slides back
to OFF, the light goes out, and the cartridge rises out, the flaps springing shut behind it, and goes.

Eight materials (print, gloss, dark, reset, pad; cart, cart_label, pcb) and three textures, within the system model
budget. Run from the repo root:

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
import mega_drive_layout as ML  # noqa: E402
import plugs  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, material, new_object, prism_x  # noqa: E402

TILT_YAW = -25.0   # degrees about the vertical: the right end (the slot side) comes towards the viewer
TILT_PITCH = 30.0  # degrees about the horizontal: the top tips up towards the viewer

WIDTH, DEPTH = 280.0, 212.0
TOP = 50.0                                   # the flat top, behind the slope
FEET = 1.5                                   # the rubber feet's height: the body's underside is this far up
SLOPE = math.atan2(25.0, 66.0)               # the front slope, from its foot (y -104, z 25) up to the top (-38, 50)
CENTRE = (34.0, 17.4)                        # the platform's centre (as in mega_drive_print.py)
LIP = (34.0, 38.0, 134.0, 23.0, 57.5)        # the slot's lip: centre, length, width, top
OPENING = (34.0, 37.0, 114.0, 15.0)          # the slot's opening: centre, length, width
FLAP = dict(length=98.0, width=7.6, thickness=1.4, z=55.6, droop=8.0, open=80.0)   # each dust flap, hinged at an
                                             # edge of the opening, drooping to the middle; how far it swings open
PANEL = dict(x=(-121.0, -50.0), y=(-98.0, -37.5), depth=3.5)   # the control panel, sunk depth under the slope
BODY_AT, BLACK_AT = (-75.0, 50.0), (-42.1, -10.3)   # spots of the print in the body's black and the ring's


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


def print_uv(x, y):
    """A point of the console's top, seen from above, in the print (as mega_drive_print.py draws it)."""
    return (x + WIDTH / 2) / WIDTH, (y + DEPTH / 2) / DEPTH


def print_uvs(obj):
    """Prints an object: each face that looks up takes the planar projection from above; every other face (the sides,
    the front and back, the underside, the recesses' walls) the body's black, or the ring's on the glossy parts, from a
    spot of it in the print. Smooth, its sharp edges kept."""
    mesh = obj.data
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    names = [mat.name for mat in mesh.materials]
    body, black = print_uv(*BODY_AT), print_uv(*BLACK_AT)
    for p in mesh.polygons:
        side = black if names[p.material_index].startswith("gloss") else body
        for li in p.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv = print_uv(co.x, co.y) if p.normal.z > 0.3 else side
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(35))


def panel_floor(y):
    """The control panel's floor at y: the slope, the panel's depth under it."""
    return 25.0 + (y + 104.0) * math.tan(SLOPE) - PANEL["depth"] / math.cos(SLOPE)


def on_panel(name, x0, x1, y0, y1, h, mat, rounded=0.8):
    """A part standing out of the panel's sloping floor, square to it: its plan rectangle and its height off the floor
    (from 1 under it), its edges rounded. Returns it and its foot's middle."""
    ym = (y0 + y1) / 2
    half = (y1 - y0) / 2 / math.cos(SLOPE)
    part = box(name, x0, x1, -half, half, -1.0, h, mat)
    if rounded:
        bevel(part, rounded, angle=30)
    part.data.transform(Matrix.Translation((0.0, ym, panel_floor(ym))) @ Matrix.Rotation(SLOPE, 4, "X"))
    return part, Vector(((x0 + x1) / 2, ym, panel_floor(ym)))


def flap(m, side):
    """A dust flap, its origin on its hinge (the opening's front edge, side -1, or its back edge, side 1), drooping to
    the middle; and where its hinge goes."""
    f = FLAP
    y0, y1 = (0.0, f["width"]) if side < 0 else (-f["width"], 0.0)
    part = box("flap", -f["length"] / 2, f["length"] / 2, y0, y1, -f["thickness"], 0.0, m["print"])
    part.data.transform(Matrix.Rotation(math.radians(f["droop"] * side), 4, "X"))
    x, y, _, width = OPENING
    return part, Vector((x, y + side * width / 2, f["z"]))


def build(m, apart=False):
    """The console, its top printed. With apart, the power switch, RESET and the slot's flaps are left out of it and
    returned too, each with its origin where it moves about (a switch's foot's middle, a flap's hinge) and where that
    goes: (console, {"power": (part, place), "reset": ..., "flap_front": ..., "flap_back": ...})."""
    # The body: the side outline (flat top, then the slope down to the front) cut by the plan's corners and the top
    # side chamfers; its underside FEET up, on its feet.
    outline = [(-106, FEET), (106, FEET), (106, TOP), (-38, TOP), (-104, 25), (-106, 23)]
    body = prism_x("megadrive", outline, -141, 141, m["print"])
    plan = chamfered([(-140, -106), (140, -106), (140, 106), (-140, 106)], [9, 9, 15, 10])
    boolean(body, prism_z("plan", plan, -1, 80, m["print"]), "INTERSECT")
    ends = [(-141, -1), (141, -1), (141, TOP - 7), (133, TOP + 1), (-133, TOP + 1), (-141, TOP - 7)]
    boolean(body, prism_y("ends", ends, -107, 107, m["print"]), "INTERSECT")
    bevel(body, 1.5)

    # The seam between the halves, round the body.
    inner = chamfered([(-139.2, -105.2), (139.2, -105.2), (139.2, 105.2), (-139.2, 105.2)], [8.7, 8.7, 14.7, 9.7])
    seam = box("seam", -150, 150, -120, 120, 10.4, 11.6, m["print"])
    boolean(seam, prism_z("inner", inner, 9, 13, m["print"]))
    boolean(body, seam)

    # The platform: the glossy ring round the disc, standing out of the top and the slope, on a matte wall.
    platform = [(0, 30), (88, 30), (88, 52), (87, 53), (84, 54.4), (80, 55.4), (76, 55.8), (74, 55.5), (74, 53.5),
                (0, 53.5)]
    ring = lathe("platform", platform, CENTRE, lambda r0, r1, z0, z1: 1 if min(r0, r1) >= 74 and min(z0, z1) >= 52
                 else 0)
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

    # The control panel, sunk a little into the slope, its floor following it, with the volume slider's and power
    # switch's knobs and RESET standing out of it.
    (px0, px1), (py0, py1) = PANEL["x"], PANEL["y"]
    sunk = [(py0, panel_floor(py0)), (py1, panel_floor(py1)), (py1, 70.0), (py0, 70.0)]
    boolean(body, prism_x("panel", sunk, px0, px1, m["print"]))
    parts = {name: on_panel(name, *where, mat) for name, where, mat in (
        ("volume", (-109.4, -96.6, -78.3, -67.6, 5.5), m["gloss"]),
        ("power", (-73.0, -60.6, -57.2, -46.1, 4.5), m["gloss"]),
        ("reset", (-84.7, -60.5, -90.0, -79.0, 3.0), m["reset"]))}

    # The controller ports and the headphone socket, in the front; the A/V, RF and power sockets in the back; the
    # expansion port's cover, set in the right end.
    for x in (22.0, 66.0):
        port = [(x - 16, 6), (x + 16, 6), (x + 14, 16), (x - 14, 16)]
        boolean(body, prism_y("port", port, -110, -101, m["dark"]))

    def hole(x, z, r, y0, y1, n=12):
        return prism_y("hole", [(x + r * math.cos(2 * math.pi * k / n), z + r * math.sin(2 * math.pi * k / n))
                                for k in range(n)], y0, y1, m["dark"])

    boolean(body, hole(-112.0, 12.0, 2.6, -110, -101))
    for x, r in ((-64.0, 7.0), (-86.0, 4.5), (-40.0, 4.0)):
        boolean(body, hole(x, 24.0, r, 98.0, 110.0, 16))
    boolean(body, box("expansion", 139.2, 150.0, -40.0, 75.0, 14.0, 38.0, m["print"]))

    # Underneath: the screws, the two vents' slots and the labels; the feet.
    under = []
    for x, y in ((107.0, 89.0), (4.0, 89.0), (-117.0, 89.0), (121.0, -79.0), (4.0, -79.0), (-117.0, -79.0)):
        ring = [(x + 3.2 * math.cos(2 * math.pi * k / 12), y + 3.2 * math.sin(2 * math.pi * k / 12)) for k in range(12)]
        under.append(prism_z("screw", ring, -1.0, FEET + 2.5, m["dark"]))
    for y0, y1 in ((40.0, 59.0), (-56.0, -37.0)):
        under += [box("vent", x - 1.0, x + 1.0, y0, y1, -1.0, FEET + 1.5, m["dark"]) for x in range(-108, -28, 4)]
    boolean(body, join(under, "underneath"))
    labels = [box("label", x0, x1, -11.0, 24.0, FEET - 0.3, FEET + 0.1, m["gloss"]) for x0, x1 in ((27.5, 106.0),
                                                                                                  (-24.5, 22.0))]
    feet = [prism_z("foot", stadium(x, y, 26.0, 7.0, 6), 0.0, FEET + 0.5, m["dark"]) for x in (-92.0, 92.0)
            for y in (-78.0, 78.0)]

    # The slot's flaps, meeting in the middle.
    flaps = {}
    for name, side in (("flap_front", -1), ("flap_back", 1)):
        part, hinge = flap(m, side)
        mesh = part.data
        uv = mesh.uv_layers.new(name="UVMap")
        for loop in mesh.loops:
            uv.data[loop.index].uv = print_uv(*BLACK_AT)
        flaps[name] = (part, hinge)

    names = ("power", "reset", "flap_front", "flap_back") if apart else ()
    rest = [part for name, (part, _) in parts.items() if name not in names]
    for name, (part, hinge) in flaps.items():
        if name not in names:
            part.data.transform(Matrix.Translation(hinge))
            rest.append(part)
    console = join([body] + slats + labels + feet + rest, "megadrive")

    # Everything that looks up is printed: the planar projection from above (as mega_drive_print.py draws it).
    print_uvs(console)
    if not apart:
        return console
    out = {}
    for name in names[:2]:
        part, foot = parts[name]
        print_uvs(part)
        part.data.transform(Matrix.Translation(-foot))
        out[name] = (part, foot)
    for name in names[2:]:
        out[name] = flaps[name]
    return console, out


# ---- The card --------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / ML.PAD_ATLAS, 1 - (ry + b / h * rh) / ML.PAD_ATLAS)


def swatch(name):
    x, y = ML.SWATCHES[name]
    return lambda co: (x / ML.PAD_ATLAS, 1 - y / ML.PAD_ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


def pad(m):
    """The control pad at its place: its body and START; the D-pad, A, B and C apart (each with where it goes). Returns
    them, and where its cable leaves it and which way."""
    from saturn import inset, smooth_outline     # here, not at the top: saturn.py imports this module
    P = ML.PAD
    x, y, turn = P["at"]
    spin = Matrix.Rotation(math.radians(turn), 4, "Z")
    place = Matrix.Translation((x, y, 0.0)) @ spin
    outline = smooth_outline(P["points"])
    h = P["height"]
    profile = ((0.0, 6.0), (0.12, 2.2), (0.3, 0.0), (0.55, 0.4), (0.78, 2.0), (0.9, 3.4), (0.96, 4.8), (0.99, 6.0),
               (1.0, 7.4))
    body = solid("pad", [[(px, py, h * z) for px, py in (inset(outline, d) if d else outline)] for z, d in profile],
                 m["pad"])
    colour(body, m["pad"], "pad")
    face = atlas_uv(ML.PAD_REGIONS["pad"], 168.0, 100.0)
    paint(body, m["pad"], lambda co: face(co.x + 84.0, 50.0 - co.y), lambda c, n, kind: n.z > 0.8)
    (sx, sy), (sw, sh) = P["start"]
    ring = [(sx + sw / 2 * math.cos(2 * math.pi * k / 20), sy + sh / 2 * math.sin(2 * math.pi * k / 20))
            for k in range(20)]
    start = colour(solid("start", [[(px, py, z) for px, py in ring] for z in (h - 1.5, h + 1.2)], m["pad"]),
                   m["pad"], "start")
    whole = join([body, start], "pad")
    whole.data.transform(place)

    moving = {}
    (dx, dy), _ = P["disc"]
    arm, width = P["dpad"]
    cross = join([box("arm", -arm, arm, -width / 2, width / 2, -1.0, 3.0, m["pad"]),
                  box("arm", -width / 2, width / 2, -arm, arm, -1.0, 3.0, m["pad"])], "dpad")
    bevel(cross, 1.2, segments=2, angle=30)
    colour(cross, m["pad"], "button")
    moving["dpad"] = (cross, place @ Vector((dx, dy, h)))
    r = P["abc_r"]
    for name, (bx, by) in zip(("a", "b", "c"), P["abc"]):
        button = solid(name, [[(rr * math.cos(2 * math.pi * k / 24), rr * math.sin(2 * math.pi * k / 24), z)
                               for k in range(24)] for rr, z in ((r, -1.0), (r, 2.6), (r * 0.8, 4.0))], m["pad"])
        moving[name] = (colour(button, m["pad"], "button"), place @ Vector((bx, by, h)))
    for part, _ in moving.values():
        part.data.transform(spin)
    cx, cy = P["cable"]
    return whole, moving, (place @ Vector((cx, cy, h * 0.5)), spin @ Vector((0.0, 1.0, 0.0)))


def light(m):
    """The POWER light on the plate's strip, lit and unlit (swapped by depth)."""
    (x, y), z, r = ML.LIGHT["at"], ML.LIGHT["z"], ML.LIGHT["r"]
    ring = [(r * math.cos(2 * math.pi * k / 12), r * math.sin(2 * math.pi * k / 12)) for k in range(12)]
    return {name: (colour(solid(name, [[(px, py, h) for px, py in ring] for h in (-0.6, 0.35)], m["pad"]), m["pad"],
                          tone), Vector((x, y, z)))
            for name, tone in (("light", "lit"), ("light_off", "off"))}


def cable(m, points):
    """The pad's cable: a tube along the Bézier curve through four control points."""
    p0, p1, p2, p3 = (Vector(p) for p in points)
    path = [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / 24 for k in range(25)]]
    bm = bmesh.new()
    rings, normal = [], Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(path):
        tangent = (path[min(k + 1, 24)] - path[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * 2.2)
                      for a in [2 * math.pi * j / 8 for j in range(8)]])
    for a, b in zip(rings, rings[1:]):
        for j in range(8):
            bm.faces.new([a[j], a[(j + 1) % 8], b[(j + 1) % 8], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return colour(new_object("cable", bm, m["pad"]), m["pad"], "black")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def flaps_open(f):
    """How far the cartridge has pushed the flaps down: as its edge reaches them going in; they spring shut once it's
    out."""
    if f < 23:
        return 0.0
    if f < 190:
        return smooth(phase(f, 23, 25))
    return 1.0 - back_out(phase(f, 190, 199))


def timeline(f):
    above = ML.CART["above"]
    if f < 8 or f >= 200:
        cart = Pose(z=above, scale=HIDDEN)
    elif f < 15:
        cart = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 8, 15))))
    elif f < 30:
        cart = Pose(z=above * (1 - ease_in(phase(f, 15, 30))))
    elif f < 186:
        cart = Pose(z=-2.0 * math.sin(math.pi * phase(f, 30, 36)))
    else:
        cart = Pose(z=above * ease_out(phase(f, 186, 196)), scale=max(HIDDEN, 1 - ease_in(phase(f, 194, 200))))
    on = smooth(phase(f, 40, 46)) * (1 - smooth(phase(f, 172, 178)))
    lit = 44 <= f < 176
    t = phase(f, 66, 162)
    k = math.sin(math.pi * t)
    sink = Pose(z=-1.2)
    press = 1.6 * tap(f, 164)                                  # RESET goes in square to the panel's floor
    swing = (FLAP["open"] - FLAP["droop"]) * flaps_open(f)
    return {"cartridge": cart, "power": Pose(x=ML.SWITCH["on"] * on),
            "reset": Pose(y=press * math.sin(SLOPE), z=-press * math.cos(SLOPE)),
            "flap_front": Pose(pitch=-swing), "flap_back": Pose(pitch=swing),
            "light": Pose() if lit else sink, "light_off": sink if lit else Pose(),
            "dpad": Pose(pitch=8.0 * k * math.sin(2 * math.pi * 3.0 * t),
                         roll=8.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "a": Pose(z=-2.0 * max(tap(f, f0) for f0 in (74, 98, 122, 146))),
            "b": Pose(z=-2.0 * max(tap(f, f0) for f0 in (84, 110, 134))),
            "c": Pose(z=-2.0 * max(tap(f, f0) for f0 in (92, 118, 140, 156)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = ML.FPS
    print_image = bpy.data.images.load(os.path.join(images, "megadrive_print.png"))
    label_image = bpy.data.images.load(os.path.join(images, "megadrive_odyssey.png"))
    pad_image = bpy.data.images.load(os.path.join(images, "megadrive_pad.png"))
    m = {
        "print": material("print", "#FFFFFF", 0.55, print_image),
        "gloss": material("gloss", "#FFFFFF", 0.18, print_image),
        "dark": material("dark", "#060607", 0.9),
        "reset": material("reset", "#C4C5BC", 0.5),
        "pad": material("pad", "#FFFFFF", 0.4, pad_image),
    }
    console, moving = build(m, apart=True)
    body, pad_parts, (exit_at, exit_dir) = pad(m)
    moving.update(pad_parts)
    black = (lambda o: colour(o, m["pad"], "black"))
    relief, start, leaving = plugs.place(*plugs.grommet(black, 3.6), m["pad"], exit_at, exit_dir)
    port = Vector((ML.PORT["x"], ML.PORT["front"], ML.PORT["z"]))
    plug, end, back = plugs.place(*plugs.dsub(black, black, 12.0), m["pad"], port, (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
    lead = cable(m, [start, start + leaving * 40.0 + Vector((0.0, 0.0, -8.0)), end + back * 50.0, end])
    # The power switch's slot, dark: its print shows the knob's stripe where the knob rests, which the slid knob would
    # leave behind.
    slot = colour(on_panel("switch_slot", -85.5, -58.5, -57.2, -46.1, 0.1, m["pad"], rounded=0)[0], m["pad"], "black")
    extras = [body, lead, slot] + relief + plug
    for part in extras:
        for p in part.data.polygons:
            p.use_smooth = True
    whole = join([console] + extras, "megadrive")
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("megadrive_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    moving.update(light(m))
    cart = cartridge.build({"case": material("cart", "#141416", 0.45),
                            "label": material("cart_label", "#FFFFFF", 0.4, label_image),
                            "pcb": material("pcb", "#B8924A", 0.35)}, whole_label=True)
    moving["cartridge"] = (cart, Vector((OPENING[0], OPENING[1], LIP[4] - ML.CART["inserted"])))
    nodes = {}
    for name, (part, where) in moving.items():
        if name != "cartridge":
            for p in part.data.polygons:
                p.use_smooth = True
            part.data.set_sharp_from_angle(angle=math.radians(35))
        part.parent = whole
        part.location = where
        nodes[name] = part

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, ML.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"Mega Drive: {sum(cartridge.triangles(o.data) for o in meshes)} triangles "
          f"({cartridge.triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    cartridge.export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
