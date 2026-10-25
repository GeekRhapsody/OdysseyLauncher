"""The console theme's BBC Micro system model (godot/themes/console/models/systems/bbcmicro.glb): the BBC Micro Model B,
a twin disk drive on it and a Microvitec Cub monitor on the drive.

Built in Blender (bbcmicro_layout.py has the measurements, taken from photographs). The computer is its case (its
plan's corners rounded, its top's edges softened) with the keyboard panel sunk into its front half, the clear strip
along the panel's back, the blank plate and the keys standing in the panel, each key a frustum, its top printed with its
legend. The drive is a box on the computer's back half, its two slots cut into its front, a latch on each; the monitor
a box on the drive, the bezel printed on its front and the tube's recess cut into it, the tube's face curved. The
printing is one texture (bbcmicro_print.py's), projected from above onto the panel and the keys and from in front onto
the drive's and the monitor's fronts.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the floppy (waiting in front of drive 0, shrunk to nothing), drive 0's latch and light (shrunk to nothing while
it's off), the tube's four faces (those not shown a little behind the one that is) and the keys the clip presses
(SHIFT, BREAK, RETURN, Z, X and the space bar).

The `focused` clip (8 s, looping): the floppy slides into drive 0 and the latch turns down; SHIFT and BREAK boot it, the
drive's light flickers and the title comes up in teletext; SPACE, and the game's played in Mode 2 on Z, X and RETURN;
BREAK brings the boot screen back, the latch turns up and the floppy slides out.

Four materials (case, keys, screen, floppy) and one 1024² texture, within the system model budget. Run from the repo
root:

    python tools/console-models/bbcmicro_print.py artifacts/bbcmicro
    blender -b --factory-startup --python tools/console-models/bbcmicro.py -- artifacts/bbcmicro godot/themes/console/models/systems/bbcmicro.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbcmicro_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 16.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, keys=0.35, screen=0.3, floppy=0.4)
TOP = L.FEET + L.HEIGHT                      # the computer's top
FLOOR = TOP - L.PANEL["depth"]               # the keyboard panel's floor
DRIVE_TOP = TOP + L.DRIVE["height"]
MOVING = {"SHIFT": "shift", "BREAK": "break", "RETURN": "return", "Z": "z", "X": "x", " ": "space"}


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


def upright(name, points, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


(PX0, PX1), (PY0, PY1) = L.PANEL["x"], L.PANEL["y"]
PANEL = atlas_uv(L.REGIONS["panel"], PX1 - PX0, PY1 - PY0)


def panel_uv(co):
    return PANEL(co.x - PX0, PY1 - co.y)


# ---- The computer ----------------------------------------------------------------------------------------------------

def computer(m):
    """The case with the panel sunk in, the strip, the plate, the feet; printed."""
    case = upright("bbcmicro", rounded(0.0, L.DEPTH / 2, L.WIDTH, L.DEPTH, 8.0, 4), L.FEET, TOP, m["case"])
    bevel(case, 3.0, segments=2, angle=40)
    boolean(case, box("panel", PX0, PX1, PY0, PY1, FLOOR, TOP + 5.0, m["case"]))
    colour(case, m["case"], "case")
    paint(case, m["case"], panel_uv, lambda c, n, kind: n.z > 0.9 and abs(c.z - FLOOR) < 0.5)
    paint(case, m["case"], swatch("black"),
          lambda c, n, kind: abs(n.z) < 0.5 and PX0 - 0.5 < c.x < PX1 + 0.5 and PY0 - 0.5 < c.y < PY1 + 0.5
          and c.z > FLOOR - 0.5)
    s0, s1 = L.STRIP["y"]
    strip = box("strip", PX0, PX1, s0, s1, FLOOR - 0.5, TOP - 1.5, m["case"])
    colour(strip, m["case"], "black")
    paint(strip, m["case"], panel_uv, lambda c, n, kind: n.z > 0.9)
    (p0, p1), (q0, q1) = L.PLATE["x"], L.PLATE["y"]
    plate = box("plate", p0, p1, q0, q1, FLOOR - 0.5, FLOOR + 5.0, m["case"])
    colour(plate, m["case"], "dark")
    paint(plate, m["case"], panel_uv, lambda c, n, kind: n.z > 0.9)
    feet = [colour(box("foot", x - 12.0, x + 12.0, y - 8.0, y + 8.0, 0.0, L.FEET + 0.5, m["case"]), m["case"], "dark")
            for x in (-170.0, 170.0) for y in (30.0, 320.0)]
    return join([case, strip, plate] + feet, "bbcmicro")


def keys(m):
    """The keys: those the clip presses apart (each its foot's middle at its origin, with where it goes), the rest
    joined."""
    fixed, moving = [], {}
    shifts = 0
    for legend, tone, x0, x1, y in L.keys():
        bottom = [(x, yy) for x, yy in ((x0 + 0.6, y - 9.0), (x1 - 0.6, y - 9.0), (x1 - 0.6, y + 9.0),
                                       (x0 + 0.6, y + 9.0))]
        top = [(x, yy) for x, yy in ((x0 + 2.8, y - 6.8), (x1 - 2.8, y - 6.8), (x1 - 2.8, y + 6.8),
                                     (x0 + 2.8, y + 6.8))]
        part = solid("key", [[(x, yy, FLOOR) for x, yy in bottom],
                             [(x, yy, FLOOR + L.KEYS["height"]) for x, yy in top]], m["keys"])
        colour(part, m["keys"], tone)
        paint(part, m["keys"], panel_uv, lambda c, n, kind: n.z > 0.9)
        name = MOVING.get(legend)
        if legend == "SHIFT":
            shifts += 1
            name = "shift" if shifts == 1 else None
        if name:
            middle = Vector(((x0 + x1) / 2, y, FLOOR))
            part.data.transform(Matrix.Translation(-middle))
            moving[name] = (part, middle)
        else:
            fixed.append(part)
    return join(fixed, "keys"), moving


# ---- The drive and the monitor ---------------------------------------------------------------------------------------

def drive(m):
    """The twin drive on the computer: its box, its slots cut in, drive 1's latch; its front printed."""
    d = L.DRIVE
    w, depth, h, y0 = d["width"], d["depth"], d["height"], d["y"]
    part = upright("drive", rounded(0.0, y0 + depth / 2, w, depth, 6.0, 3), TOP, DRIVE_TOP, m["case"])
    bevel(part, 2.0, segments=2, angle=40)
    sw, sh = L.BAYS["slot"]
    zc = TOP + L.BAYS["z"]
    for x in L.BAYS["x"]:
        boolean(part, box("slot", x - sw / 2, x + sw / 2, y0 - 5.0, y0 + 40.0, zc - sh / 2, zc + sh / 2, m["case"]))
    colour(part, m["case"], "case")
    face = atlas_uv(L.REGIONS["drive"], w, h)
    paint(part, m["case"], lambda co: face(co.x + w / 2, DRIVE_TOP - co.z),
          lambda c, n, kind: n.y < -0.9 and c.y < y0 + 1.0)
    paint(part, m["case"], swatch("black"),
          lambda c, n, kind: c.y > y0 + 0.5 and abs(c.z - zc) < sh / 2 + 0.5 and any(abs(c.x - x) < sw / 2 + 0.5
                                                                                     for x in L.BAYS["x"]))
    latch = latch_part(m)
    latch.data.transform(Matrix.Translation((L.BAYS["x"][1], y0 - 2.0, zc)))
    return join([part, latch], "drive")


def latch_part(m):
    """A drive's latch, open (lying along the slot), its middle at its origin."""
    lw, lh = L.BAYS["latch"]
    part = box("latch", -lw / 2, lw / 2, -4.0, 0.0, -lh / 2, lh / 2, m["keys"])
    bevel(part, 1.0, segments=1)
    return colour(part, m["keys"], "grey")


def monitor(m):
    """The monitor on the drive: its box, the tube's recess cut into its front; its bezel printed."""
    mon = L.MONITOR
    w, h, depth, y0 = mon["width"], mon["height"], mon["depth"], L.DRIVE["y"]
    part = upright("monitor", rounded(0.0, y0 + depth / 2, w, depth, 6.0, 3), DRIVE_TOP, DRIVE_TOP + h, m["case"])
    bevel(part, 3.0, segments=2, angle=40)
    sw, sh = L.SCREEN["size"]
    zc = DRIVE_TOP + L.SCREEN["z"]
    boolean(part, solid("recess", [[(x, y, z) for x, z in rounded(0.0, zc, sw + 16.0, sh + 16.0, 18.0, 5)]
                                   for y in (y0 - 5.0, y0 + 14.0)], m["case"]))
    colour(part, m["case"], "monitor")
    face = atlas_uv(L.REGIONS["bezel"], w, h)
    paint(part, m["case"], lambda co: face(co.x + w / 2, DRIVE_TOP + h - co.z),
          lambda c, n, kind: n.y < -0.9 and c.y < y0 + 1.0)
    paint(part, m["case"], swatch("bezel"),
          lambda c, n, kind: y0 + 0.5 < c.y < y0 + 14.5 and abs(c.x) < sw / 2 + 9.0
          and abs(c.z - zc) < sh / 2 + 9.0)
    return part


def screen(m, name):
    """One of the tube's faces, its middle at its origin, facing the viewer."""
    sw, sh = L.SCREEN["size"]
    rx, ry, rw, rh = L.REGIONS[name]
    return curved(name, sw, sh, L.SCREEN["bulge"], lambda a, b: ((rx + a * rw) / L.ATLAS, 1 - (ry + b * rh) / L.ATLAS),
                  m["screen"], 16, 12)


def floppy(m):
    """The floppy, lying flat, its middle at its origin, its label up and towards the viewer, going in along +y."""
    s, t = L.FLOPPY["size"], L.FLOPPY["thickness"]
    part = box("floppy", -s / 2, s / 2, -s / 2, s / 2, -t / 2, t / 2, m["floppy"])
    colour(part, m["floppy"], "floppy")
    top = atlas_uv(L.REGIONS["floppy"], s, s)
    paint(part, m["floppy"], lambda co: top(co.x + s / 2, co.y + s / 2), lambda c, n, kind: n.z > 0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

SCREENS = ("boot", "title", "game_1", "game_2")
BEHIND = 1.5              # how far back the tube's faces not shown wait


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def shown(f):
    if f < 60 or f >= 188:
        return "boot"
    if f < 100:
        return "title"
    return "game_1" if ((f - 100) // 8) % 2 == 0 else "game_2"


def timeline(f):
    out = L.FLOPPY["out"]
    if f < 8 or f >= 232:
        disk = Pose(y=-out, scale=HIDDEN)
    elif f < 14:
        disk = Pose(y=-out, scale=max(HIDDEN, back_out(phase(f, 8, 13))))
    elif f < 34:
        disk = Pose(y=-out * (1 - smooth(phase(f, 14, 34))))
    elif f < 204:
        disk = Pose()
    elif f < 224:
        disk = Pose(y=-out * smooth(phase(f, 204, 224)))
    else:
        disk = Pose(y=-out, scale=max(HIDDEN, 1 - ease_in(phase(f, 224, 232))))
    shut = smooth(phase(f, 36, 42)) * (1 - smooth(phase(f, 196, 202)))
    reading = 52 <= f < 92 and (f // 3) % 4 != 3
    poses = {"floppy": disk, "latch": Pose(roll=90.0 * shut), "drive_light": Pose() if reading else Pose(scale=HIDDEN)}
    for name in SCREENS:
        poses[name] = Pose() if name == shown(f) else Pose(y=BEHIND)
    press = -2.6
    poses["shift"] = Pose(z=press * smooth(phase(f, 44, 47)) * (1 - smooth(phase(f, 53, 56))))
    poses["break"] = Pose(z=press * max(tap(f, 48), tap(f, 184)))
    poses["space"] = Pose(z=press * tap(f, 96))
    poses["z"] = Pose(z=press * max(tap(f, f0) for f0 in (108, 132, 156)))
    poses["x"] = Pose(z=press * max(tap(f, f0) for f0 in (120, 144, 168)))
    poses["return"] = Pose(z=press * max(tap(f, f0) for f0 in (116, 140, 162)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "bbcmicro_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    fixed_keys, moving_keys = keys(m)
    whole = join([computer(m), fixed_keys, drive(m), monitor(m)], "bbcmicro")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("bbcmicro_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    y0 = L.DRIVE["y"]
    zc = TOP + L.BAYS["z"]
    x0 = L.BAYS["x"][0]
    lw, lh = L.BAYS["latch"]
    light = colour(box("drive_light", -1.6, 1.6, -0.6, 0.0, -1.6, 1.6, m["keys"]), m["keys"], "lit")
    bw, bh = L.BAYS["size"]
    parts = {"floppy": (floppy(m), Vector((x0, y0 + L.FLOPPY["size"] / 2 + 4.0, zc))),
             "latch": (latch_part(m), Vector((x0, y0 - 2.0, zc))),
             "drive_light": (light, Vector((x0 - bw / 2 + 10.0, y0 - 0.2, zc - bh / 2 + 8.0)))}
    sz = DRIVE_TOP + L.SCREEN["z"]
    for name in SCREENS:
        parts[name] = (screen(m, name), Vector((0.0, y0 + 13.5, sz)))
    parts.update(moving_keys)
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
    print(f"BBC Micro: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
