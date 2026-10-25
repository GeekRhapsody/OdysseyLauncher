"""The console theme's PC-FX system model (godot/themes/console/models/systems/pcfx.glb): NEC's PC-FX, the tower, and
its pad.

Built in Blender (pcfx_layout.py has the measurements, taken from photographs). The body is a box with its edges
rounded, its underside arched between its feet; the front's strip is recessed between the pillars, the lid's pocket
and the drive's bay under it are cut into the top, and the sides' raised panels stand on it. The pad is its traced
outline given its depth, its edges rounded, the d-pad, the six buttons, SELECT and RUN on it; its cord runs to port 1.
The printing is one texture (pcfx_print.py's), projected from the side onto the sides, from above onto the tops and
from in front onto the front.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the CD lid (its origin on its hinge, along its back edge), the CD (waiting over the drive, shrunk to nothing),
the POWER and BUSY lights (shrunk to nothing while they're off), and the pad's d-pad and buttons I and II.

The `focused` clip (8 s, looping): the lid swings up, the CD appears over the drive and drops onto the spindle,
spinning, and the lid shuts; POWER lights and BUSY flickers while it reads; the game's played on the d-pad, I and II;
then the lid swings up again, the CD rises out and goes, and the lid shuts.

Two materials (body, gloss) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/pcfx_print.py artifacts/pcfx
    blender -b --factory-startup --python tools/console-models/pcfx.py -- artifacts/pcfx godot/themes/console/models/systems/pcfx.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcfx_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)
from msx_layout import inset  # noqa: E402

TILT_YAW = -26.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 18.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(body=0.55, gloss=0.25)
PAD_W, PAD_D = 168.0, 74.8


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


SIDE = atlas_uv(L.REGIONS["side"], L.DEPTH, L.HEIGHT)
TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT)
DRIVE = atlas_uv(L.REGIONS["drive"], 2 * L.DRIVE["half"][0], 2 * L.DRIVE["half"][1])
PAD_TOP = atlas_uv(L.REGIONS["pad"], PAD_W, PAD_D)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def upright(name, points, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


def facing(name, points, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1."""
    return solid(name, [[(x, y, z) for x, z in points] for y in (y0, y1)], mat)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


def tube(name, points, r, mat, sides=8):
    bm = bmesh.new()
    rings = []
    normal = Vector((0.0, 0.0, 1.0))
    n = len(points) - 1
    for k, p in enumerate(points):
        tangent = (points[min(k + 1, n)] - points[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        around = [2 * math.pi * j / sides for j in range(sides)]
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * r) for a in around])
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            bm.faces.new([a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def curve(p0, p1, p2, p3, n):
    p0, p1, p2, p3 = (Vector(p) for p in (p0, p1, p2, p3))
    return [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / n for k in range(n + 1)]]


# ---- The console -----------------------------------------------------------------------------------------------------

def body(m):
    """The tower: the box, its edges rounded, the arch under it, the front's strip, the lid's pocket and the drive's
    bay, the sides' raised panels; printed."""
    half = L.WIDTH / 2
    shell = box("pcfx", -half, half, 0.0, L.DEPTH, 0.0, L.HEIGHT, m["body"])
    bevel(shell, L.EDGE, segments=3, angle=40)
    (a0, a1), rise = L.ARCH["y"], L.ARCH["rise"]
    arch = [(a0 + (a1 - a0) * k / 16, rise * math.sin(math.pi * k / 16)) for k in range(17)]
    boolean(shell, prism_x("arch", [(a1, -2.0), (a0, -2.0)] + arch, -half - 5.0, half + 5.0, m["body"]))
    inner, recess = L.PILLARS["inner"], L.PILLARS["recess"]
    boolean(shell, box("strip", -inner, inner, -5.0, recess, 6.0, L.PILLARS["top"], m["body"]))
    lid_floor = L.HEIGHT - L.LID["thickness"] - L.DRIVE["floor"]
    boolean(shell, box("pocket", -half + L.LID["inset"], half - L.LID["inset"], L.SEAMS["front"], L.SEAMS["back"],
                       lid_floor, L.HEIGHT + 5.0, m["body"]))
    colour(shell, m["body"], "body")
    paint(shell, m["body"], lambda co: SIDE(co.y, L.HEIGHT - co.z), lambda c, n, kind: abs(n.x) > 0.9)
    paint(shell, m["body"], lambda co: TOP(co.x + half, L.DEPTH - co.y),
          lambda c, n, kind: n.z > 0.9 and c.z > L.HEIGHT - 0.5)
    paint(shell, m["body"], lambda co: FRONT(co.x + half, L.HEIGHT - co.z), lambda c, n, kind: n.y < -0.9)
    hx, hy = L.DRIVE["half"]
    paint(shell, m["body"], lambda co: DRIVE(co.x + hx, (L.SPINDLE["y"] + hy) - co.y),
          lambda c, n, kind: n.z > 0.9 and abs(c.z - lid_floor) < 0.5)
    paint(shell, m["body"], swatch("grey"),
          lambda c, n, kind: abs(n.z) < 0.5 and lid_floor - 0.5 < c.z < L.HEIGHT - L.LID["thickness"]
          and L.SEAMS["front"] - 0.5 < c.y < L.SEAMS["back"] + 0.5)
    parts = [shell]
    (py0, py1), (pz0, pz1), ph = L.PANEL["y"], L.PANEL["z"], L.PANEL["height"]
    for side in (-1, 1):
        x0, x1 = sorted((side * (half - 0.5), side * (half + ph)))
        panel = box("panel", x0, x1, py0, py1, pz0, pz1, m["body"])
        bevel(panel, 1.6, segments=2)
        colour(panel, m["body"], "body")
        paint(panel, m["body"], lambda co: SIDE(co.y, L.HEIGHT - co.z), lambda c, n, kind: abs(n.x) > 0.9)
        parts.append(panel)
    spindle = upright("spindle", circle(0.0, L.SPINDLE["y"], L.SPINDLE["r"], 24), lid_floor - 0.5,
                      lid_floor + L.SPINDLE["height"], m["gloss"])
    bevel(spindle, 1.0, segments=1)
    parts.append(colour(spindle, m["gloss"], "black"))
    return join(parts, "pcfx")


def lid(m):
    """The CD lid, its origin on its hinge (its back edge's top), its top printed, its underside grey."""
    half = L.WIDTH / 2 - L.LID["inset"] - 0.3
    y0, y1 = L.SEAMS["front"] + 0.3, L.SEAMS["back"] - 0.3
    part = box("lid", -half, half, y0, y1, L.HEIGHT - L.LID["thickness"], L.HEIGHT, m["body"])
    bevel(part, 1.2, segments=2)
    colour(part, m["body"], "light")
    paint(part, m["body"], lambda co: TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y), lambda c, n, kind: n.z > 0.9)
    paint(part, m["body"], lambda co: SIDE(co.y, L.HEIGHT - co.z), lambda c, n, kind: abs(n.x) > 0.9)
    paint(part, m["body"], swatch("grey"), lambda c, n, kind: n.z < -0.9)
    hinge = Vector((0.0, L.SEAMS["back"], L.HEIGHT))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def disc(m):
    r, t = L.DISC["diameter"] / 2, L.DISC["thickness"]
    part = upright("disc", circle(0.0, 0.0, r, 48), -t / 2, t / 2, m["gloss"])
    boolean(part, upright("hole", circle(0.0, 0.0, L.DISC["hole"] / 2, 20), -5.0, 5.0, m["gloss"]))
    label = atlas_uv(L.REGIONS["disc"], 2 * r, 2 * r)
    colour(part, m["gloss"], "light")
    paint(part, m["gloss"], lambda co: label(co.x + r, r - co.y), lambda c, n, kind: n.z > 0.9)
    seat = Vector((0.0, L.SPINDLE["y"], L.HEIGHT - L.LID["thickness"] - L.DRIVE["floor"] + 2.6))
    return part, seat


def light(m, name, colour_name):
    x, z = L.LIGHTS[name]
    w, h = L.LIGHTS["size"]
    part = facing(name, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], -0.3, 0.2, m["gloss"])
    return colour(part, m["gloss"], colour_name), Vector((x, L.PILLARS["recess"] - 0.05, z))


# ---- The pad ---------------------------------------------------------------------------------------------------------

def pad_uv(co):
    return PAD_TOP(co.x + PAD_W / 2, PAD_D - co.y)


def pad_frame():
    (x, y), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def controller(m):
    """The pad in its own frame (its lower edge's lowest points at y = 0, the table at z = 0): its body, the d-pad's
    dish, buttons III to VI, SELECT and RUN; the d-pad and buttons I and II apart, each with where its node goes."""
    h = L.PAD["height"]
    outline = list(reversed(L.PAD_TOP + L.PAD_BOTTOM))      # the traced edges run clockwise: turned anticlockwise
    shell = solid("pad", [[(x, y, z) for x, y in inset(outline, k)] for k, z in
                          ((3.0, 0.0), (0.0, 5.0), (0.0, h - 6.0), (2.4, h - 1.2), (3.8, h))], m["body"])
    colour(shell, m["body"], "body")
    paint(shell, m["body"], pad_uv, lambda c, n, kind: n.z > 0.95 and c.z > h - 0.5)
    (dx, dy), dish = L.DPAD["at"], L.DPAD["dish"]
    plate = upright("dish", circle(dx, dy, dish, 40), h - 1.0, h + 0.6, m["body"])
    parts = [shell, plate]
    for name in ("III", "IV", "V", "VI"):
        b = upright(name, circle(*L.BUTTONS[name], L.BUTTONS["r"], 24), h - 1.0, h + L.BUTTONS["height"], m["body"])
        bevel(b, 1.0, segments=2)
        parts.append(b)
    sw, sh = L.SMALL["size"]
    for name in ("select", "run"):
        parts.append(upright(name, rounded(*L.SMALL[name], sw, sh, sh / 2 - 0.05, 4), h - 1.0, h + 1.0, m["body"]))
    for part in parts[1:]:
        colour(part, m["body"], "key")
        paint(part, m["body"], pad_uv, lambda c, n, kind: n.z > 0.95)
    body_ = join(parts, "pad")
    moving = {}
    s, a = L.DPAD["span"] / 2, L.DPAD["arm"] / 2
    cross = [(a, -s), (a, -a), (s, -a), (s, a), (a, a), (a, s), (-a, s), (-a, a), (-s, a), (-s, -a), (-a, -a), (-a, -s)]
    dpad = upright("dpad", cross, -1.0, L.DPAD["height"], m["body"])
    bevel(dpad, 0.8, segments=1)
    moving["dpad"] = (colour(dpad, m["body"], "grey"), Vector((dx, dy, h + 0.6)))
    for name in ("I", "II"):
        x, y = L.BUTTONS[name]
        b = upright("button_" + name, circle(0.0, 0.0, L.BUTTONS["r"], 24), -1.0, L.BUTTONS["height"], m["body"])
        bevel(b, 1.0, segments=2)
        colour(b, m["body"], "key")
        paint(b, m["body"], lambda co, x=x, y=y: pad_uv(Vector((co.x + x, co.y + y, co.z))),
              lambda c, n, kind: n.z > 0.95)
        moving["button_" + name] = (b, Vector((x, y, h)))
    return body_, moving


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def opening(f):
    """How far open the lid is, 0 to 1 (a little over as it swings up)."""
    if f < 6:
        return 0.0
    if f < 48:
        return back_out(phase(f, 6, 20), 1.4)
    if f < 172:
        return 1.0 - ease_in(phase(f, 48, 58)) if f < 58 else 0.0
    if f < 206:
        return back_out(phase(f, 172, 186), 1.4)
    return 1.0 - ease_in(phase(f, 206, 216))


def timeline(f):
    above = L.DISC["above"]
    if f < 24 or f >= 204:
        cd = Pose(scale=HIDDEN)
    elif f < 30:
        cd = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 24, 29))))
    elif f < 44:
        t = phase(f, 30, 44)
        cd = Pose(z=above * (1 - ease_in(t)), spin=240.0 * t)
    elif f < 188:
        cd = Pose(spin=240.0 + 60.0 * math.sin(math.pi * phase(f, 44, 50)))
    else:
        t = phase(f, 188, 198)
        cd = Pose(z=above * ease_out(t), spin=300.0 - 240.0 * t, scale=max(HIDDEN, 1 - ease_in(phase(f, 196, 204))))
    reading = (66 <= f < 108 or 128 <= f < 134) and (f // 3) % 3 != 2
    t = phase(f, 100, 170)
    k = math.sin(math.pi * t)
    tilt = L.DPAD["tilt"]
    return {"lid": Pose(pitch=L.LID["open"] * opening(f)), "disc": cd,
            "power_light": Pose() if 64 <= f < 228 else Pose(scale=HIDDEN),
            "busy_light": Pose() if reading else Pose(scale=HIDDEN),
            "dpad": Pose(pitch=tilt * k * math.sin(2 * math.pi * 3.0 * t),
                         roll=tilt * k * math.cos(2 * math.pi * 2.0 * t)),
            "button_I": Pose(z=-L.BUTTONS["press"] * max(tap(f, f0) for f0 in (104, 122, 140, 158))),
            "button_II": Pose(z=-L.BUTTONS["press"] * max(tap(f, f0) for f0 in (113, 131, 149, 166)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "pcfx_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    console = body(m)
    pad, pad_nodes = controller(m)
    to_world = pad_frame()
    pad.data.transform(to_world)
    start = to_world @ Vector((0.0, PAD_D - 2.0, L.PAD["height"] - 6.0))
    (px, pz) = L.PORTS["at"][0]
    end = Vector((px, L.PILLARS["recess"] - 1.0, pz))
    cord = tube("cord", curve(start, start + Vector((0.0, 30.0, 0.0)), end + Vector((0.0, -50.0, -30.0)), end, 24), 2.4,
                m["body"])
    colour(cord, m["body"], "light")
    whole = join([console, pad, cord], "pcfx")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("pcfx_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    parts = {"lid": lid(m), "disc": disc(m), "power_light": light(m, "power", "green"),
             "busy_light": light(m, "busy", "amber")}
    turn = Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z")
    for name, (part, where) in pad_nodes.items():
        part.data.transform(turn)
        parts[name] = (part, to_world @ where)
    nodes = {}
    for name, (part, where) in parts.items():
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

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"PC-FX: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
