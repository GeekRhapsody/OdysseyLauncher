"""The console theme's Philips CD-i system model (godot/themes/console/models/systems/cdimono1.glb): a CD-i 220 and its
gamepad.

Built in Blender from the real player's proportions (cdi_layout.py has the measurements, taken from photographs). The
body is a box on four feet, the tray's opening cut into its front and the vents into its top; the buttons stand proud
of the front, the display's smoked window over its place. The tray is its door and, behind it, the black platform the
disc lies in. The gamepad is its arched outline extruded, a raised plate on it, the ring round the thumbpad and the
buttons' slanted well cut into the plate, the thumbpad and the three buttons standing in them. The printing is one
texture drawn by cdi_print.py: the front (planar-mapped onto the faces facing forward: the door's dots and logo,
PHILIPS, the buttons' names), the window three ways (dark, the disc read, playing), the disc's label, the gamepad's top,
and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the tray (and on it the disc, shrunk to nothing), OPEN, the two lit windows (shrunk to nothing) and the gamepad;
the gamepad holding its thumbpad and its three buttons.

The `focused` clip (8 s, looping) plays a disc: OPEN is pressed and the tray slides out; the disc drops onto it and the
tray goes in; the display reads the disc (CD-i), then plays, the gamepad's thumbpad and buttons played. Then OPEN again,
the tray comes out, the disc lifts away and the tray goes back in.

Five materials (case, button, black, glass, print) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/cdi_print.py artifacts/cdi
    blender -b --factory-startup --python tools/console-models/cdi.py -- artifacts/cdi godot/themes/console/models/systems/cdimono1.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdi_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 25.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, button=0.5, black=0.6, glass=0.12, print=0.5)
DOOR_FRONT = 1.0     # the door's face, back from the front's


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT - L.FOOT)


def front_uv(co):
    """The front seen from in front."""
    return FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def facing_front(c, n, name):
    return n.y < -0.9


# ---- The player ------------------------------------------------------------------------------------------------------

def body(m):
    """The body on its feet: the tray's opening cut into its front, the vents into its top, its front printed."""
    w = L.WIDTH
    shell = box("cdi", -w / 2, w / 2, 0.0, L.DEPTH, L.FOOT, L.HEIGHT, m["case"])
    bevel(shell, 2.0, segments=2)
    (dx0, dx1), (dz0, dz1) = L.DOOR["x"], L.DOOR["z"]
    boolean(shell, box("opening", dx0, dx1, -5.0, 150.0, dz0, dz1, m["black"]))
    v = L.VENTS
    step = (v["y"][1] - v["y"][0]) / v["count"]
    for x0, x1 in v["columns"]:
        boolean(shell, join([box("vent", x0, x1, v["y"][0] + (k + 0.5) * step - v["width"] / 2,
                                 v["y"][0] + (k + 0.5) * step + v["width"] / 2, L.HEIGHT - v["depth"], L.HEIGHT + 5.0,
                                 m["black"]) for k in range(v["count"])], "vents"))
    paint(shell, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < 0.5 and name == "case")
    (fx0, fx1, fx2, fx3), ys = L.FEET["x"], L.FEET["y"]
    feet = [box("foot", a, b, y0, y1, 0.0, L.FOOT + 1.0, m["black"]) for a, b in ((fx0, fx1), (fx2, fx3))
            for y0, y1 in ys]
    return [shell] + feet


def button(name, x0, x1, z0, z1, m):
    part = box(name, x0, x1, -L.BUTTON_OUT, 1.0, z0, z1, m["button"])
    bevel(part, 0.9, segments=2)
    return part


def window(m):
    (x0, x1), (z0, z1) = L.WINDOW["x"], L.WINDOW["z"]
    part = box("window", x0, x1, -L.WINDOW["out"], 1.0, z0, z1, m["glass"])
    bevel(part, 0.6, segments=1)
    face = atlas_uv(L.REGIONS["display"], x1 - x0, z1 - z0)
    paint(part, m["glass"], lambda co: face(co.x - x0, z1 - co.z), facing_front)
    return part


def lit_window(m, name):
    """A lit window over the dark one, its middle at its origin."""
    (x0, x1), (z0, z1) = L.WINDOW["x"], L.WINDOW["z"]
    w, h = x1 - x0, z1 - z0
    face = atlas_uv(L.REGIONS[name], w, h)
    part = curved(name, w - 0.6, h - 0.6, 0.0, lambda a, b: face(0.3 + a * (w - 0.6), 0.3 + b * (h - 0.6)), m["glass"],
                  nu=1, nv=1)
    return part, Vector(((x0 + x1) / 2, -L.WINDOW["out"] - 0.15, (z0 + z1) / 2))


def tray(m):
    """The tray, at rest in the body: its door, the platform behind it with the disc's recess."""
    (dx0, dx1), (dz0, dz1) = L.DOOR["x"], L.DOOR["z"]
    g = 0.6
    door = box("tray", dx0 + g, dx1 - g, DOOR_FRONT, DOOR_FRONT + 3.0, dz0 + g, dz1 - g, m["case"])
    bevel(door, 0.6, segments=1)
    paint(door, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
    p = L.PLATFORM
    platform = box("platform", *p["x"], DOOR_FRONT + 3.0, DOOR_FRONT + 3.0 + p["depth"], p["top"] - p["thickness"],
                   p["top"], m["black"])
    rx, ry = L.RECESS["centre"]
    r = L.RECESS["diameter"] / 2
    boolean(platform, solid("recess", [[(rx + r * math.cos(a), DOOR_FRONT + ry + r * math.sin(a), z)
                                        for a in (2 * math.pi * k / 48 for k in range(48))]
                                       for z in (p["top"] - L.RECESS["depth"], p["top"] + 5.0)], m["black"]))
    return join([door, platform], "tray")


def disc(m):
    """The disc, its middle at its origin, lying flat: a ring, its label on its top."""
    ro, ri, t = L.DISC["diameter"] / 2, L.DISC["hole"] / 2, L.DISC["thickness"]
    n = 64
    bm = bmesh.new()
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), z)) for k in range(n)]
             for r, z in ((ro, -t / 2), (ro, t / 2), (ri, t / 2), (ri, -t / 2))]
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new([a[k], a[j], b[j], b[k]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    part = new_object("disc", bm, m["print"])
    d = L.DISC["diameter"]
    top = atlas_uv(L.REGIONS["disc_top"], d, d)
    paint(part, m["print"], lambda co: top(co.x + d / 2, d / 2 - co.y), lambda c, n_, name: n_.z > 0.9)
    paint(part, m["print"], swatch("silver"), lambda c, n_, name: n_.z <= 0.9)
    return part


# ---- The gamepad -----------------------------------------------------------------------------------------------------

def pad(m):
    """The gamepad in its own frame (its plan's origin, the table): its base, the plate on it with the thumbpad's ring
    and the buttons' well cut into it; the thumbpad and the buttons apart (the clip plays them), each its foot's middle
    at its origin."""
    P = L.PAD
    outline = L.PAD_OUTLINE
    base = solid("pad", [[(x, y, z) for x, y in outline] for z in (0.0, P["base"])], m["case"])
    bevel(base, 3.0, segments=2)
    i, top = P["plate"]
    plate = solid("plate", [[(x, y, z) for x, y in inset(outline, i)] for z in (P["base"] - 1.0, top)], m["case"])
    bevel(plate, 2.0, segments=2)
    d = P["dpad"]
    cx, cy = d["at"]
    floor = top - 2.5
    boolean(plate, solid("ring", [[(cx + d["ring"] * math.cos(a), cy + d["ring"] * math.sin(a), z)
                                   for a in (2 * math.pi * k / 40 for k in range(40))] for z in (floor, top + 5.0)],
                         m["button"]))
    b = P["buttons"]
    (ax, ay), (bx, by) = b["at"][0], b["at"][-1]
    turn = math.atan2(by - ay, bx - ax)
    r = b["r"] + b["margin"]
    well = rounded(0.0, 0.0, math.hypot(bx - ax, by - ay) + 2 * r, 2 * r, r - 0.01, 6)
    mx, my = (ax + bx) / 2, (ay + by) / 2
    c, s = math.cos(turn), math.sin(turn)
    boolean(plate, solid("well", [[(mx + x * c - y * s, my + x * s + y * c, z) for x, y in well]
                                  for z in (top - 2.0, top + 5.0)], m["button"]))
    xs = [x for x, _ in L.PAD_OUTLINE]
    w = max(xs) - min(xs)
    face = atlas_uv(L.REGIONS["pad"], w, 101.0)
    paint(plate, m["print"], lambda co: face(co.x + w / 2, 101.0 - co.y), lambda c_, n, name: n.z > 0.9 and
          name == "case")
    shell = join([base, plate], "pad")

    thumb = solid("dpad", [[(d["disc"] * math.cos(a), d["disc"] * math.sin(a), z)
                            for a in (2 * math.pi * k / 32 for k in range(32))] for z in (-1.0, d["height"])],
                  m["button"])
    bevel(thumb, 1.2, segments=2)
    cross = join([box("arm", -12.0, 12.0, -4.2, 4.2, d["height"] - 0.5, d["height"] + 1.6, m["button"]),
                  box("arm", -4.2, 4.2, -12.0, 12.0, d["height"] - 0.5, d["height"] + 1.6, m["button"])], "cross")
    thumb = join([thumb, cross], "dpad")
    buttons = []
    for k, (x, y) in enumerate(b["at"]):
        part = solid(f"button_{k + 1}", [[(b["r"] * math.cos(a), b["r"] * math.sin(a), z)
                                          for a in (2 * math.pi * j / 28 for j in range(28))]
                                         for z in (-1.0, b["height"])], m["button"])
        bevel(part, 1.4, segments=2)
        buttons.append((part, Vector((x, y, top - 2.0))))
    return shell, (thumb, Vector((cx, cy, floor))), buttons


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


TILTS = [(112, "right"), (126, "up"), (140, "left"), (154, "down"), (176, "right")]
PRESSES = {"button_1": (118, 166), "button_2": (132, 186), "button_3": (150,)}


def tray_out(f):
    if f < 54:
        return back_out(phase(f, 12, 26), 1.2)
    if f < 196:
        return 1 - smooth(phase(f, 54, 70))
    if f < 220:
        return back_out(phase(f, 196, 210), 1.2)
    return 1 - smooth(phase(f, 222, 238))


def timeline(f):
    if f < 26 or f >= 222:
        dsk = Pose(scale=HIDDEN)
    elif f < 36:
        dsk = Pose(z=70.0, scale=appear(f, 26, 34))
    elif f < 48:
        dsk = Pose(z=70.0 * (1 - ease_in(phase(f, 36, 48))))
    elif f < 210:
        dsk = Pose(z=wobble(f, 48, 1.2, period=6.0, decay=5.0))
    else:
        dsk = Pose(z=60.0 * ease_out(phase(f, 210, 218)), scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 222))))
    tilt = dict(right=(0.0, 1.0), left=(0.0, -1.0), up=(-1.0, 0.0), down=(1.0, 0.0))
    pitch = roll = 0.0
    for f0, way in TILTS:
        k = tap(f, f0, hold=4)
        pitch += 8.0 * tilt[way][0] * k
        roll += 8.0 * tilt[way][1] * k
    poses = {"tray": Pose(y=-L.TRAY_OUT * tray_out(f)), "disc": dsk,
             "open": Pose(y=1.5 * max(tap(f, f0) for f0 in (8, 50, 192))),
             "display_disc": Pose() if 72 <= f < 108 and (f < 80 or f % 8 < 6) else Pose(scale=HIDDEN),
             "display_play": Pose() if 108 <= f < 194 else Pose(scale=HIDDEN),
             "dpad": Pose(pitch=pitch, roll=roll)}
    for name, frames in PRESSES.items():
        poses[name] = Pose(z=-2.4 * max(tap(f, f0) for f0 in frames))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "cdi_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n in ("print", "glass") else None) for n, r in ROUGHNESS.items()}

    buttons = {name: button(name, x0, x1, z0, z1, m) for name, x0, x1, z0, z1 in L.BUTTONS}
    opener = buttons.pop("open")
    whole = join(body(m) + list(buttons.values()) + [window(m)], "cdimono1")
    drawer = tray(m)
    platter = disc(m)
    lit = {name: lit_window(m, name) for name in ("display_disc", "display_play")}
    shell, (thumb, thumb_at), presses = pad(m)
    for obj in [whole, opener, drawer, platter, shell, thumb] + [part for part, _ in presses]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("cdimono1_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    rx, ry = L.RECESS["centre"]
    seat = Vector((rx, DOOR_FRONT + ry, L.PLATFORM["top"] - L.RECESS["depth"] + L.DISC["thickness"] / 2 + 0.1))
    for part in (drawer, opener):
        part.parent = whole
    platter.parent = drawer
    platter.location = seat
    for name, (part, where) in lit.items():
        part.parent = whole
        part.location = where
    (px, py), turn = L.PAD["at"], math.radians(L.PAD["turn"])
    shell.parent = whole
    shell.location = (px, py, 0.0)
    shell.rotation_euler = (0.0, 0.0, turn)
    thumb.parent = shell
    thumb.location = thumb_at
    for part, where in presses:
        part.parent = shell
        part.location = where
    nodes = {"tray": drawer, "disc": platter, "open": opener, "dpad": thumb, **{n: p for n, (p, _) in lit.items()},
             **{part.name: part for part, _ in presses}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(turn, 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in shell.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, opener, drawer, platter, shell, thumb] + [p for p, _ in lit.values()] + [p for p, _ in presses]
    print(f"CD-i: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
