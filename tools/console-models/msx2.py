"""The console theme's MSX2 system model (godot/themes/console/models/systems/msx2.glb): a Philips VG-8235.

Built in Blender from the real machine's proportions (msx2_layout.py has the measurements, taken from photographs).
Two shells: the keyboard, its side outline extruded across its width and its corners rounded in plan, cut for its
wells and the handle's groove along its front; and the main unit behind it, its outline extruded too, cut for its
vents and the drive's slot in its right end, the drive's black bezel over that end. The keys stand in the wells (the
/00's QWERTY layout), tapering to their printed tops, light grey or dark grey as the real ones; RETURN is an inverted
L, and the cursor keys four wedges round a dark square. The printing is one texture drawn by msx2_print.py: the top
seen from above (planar-mapped onto every face facing up: the key tops and legends, the grips and LOCK labels, the
main unit's printing and lights), the right end's joystick ports, the 3.5-inch disk (a made-up game, Odyssey), and
swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end, with the drive,
towards the viewer, the top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m)
holding the set; the set holding the disk (waiting in the drive, shrunk to nothing), the eject button, the lit CAPS,
FDD BUSY and drive lights (shrunk to nothing) and the keys the clip presses.

The `focused` clip (8 s, looping) plays a game from a disk: the disk slides into the drive in the right end and FDD
BUSY flickers with the drive's light while it loads; the cursor keys and the space bar are played, CAPS goes on and
off. Then the eject button goes in, the disk pops out and goes.

Six materials (case, deck, key_light, key_dark, black, print) and one texture, within the system model budget. Run
from the repo root:

    python tools/console-models/msx2_print.py artifacts/msx2
    blender -b --factory-startup --python tools/console-models/msx2.py -- artifacts/msx2 godot/themes/console/models/systems/msx2.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msx2_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end (the drive) comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, deck=0.45, key_light=0.5, key_dark=0.5, black=0.35, print=0.45)
PLAYED = ("up", "down", "left", "right", "space", "caps")

# The deck's frame: x across, s up the slope from the deck's front edge, h off it.
SLOPE_FRAME = Matrix.Translation((0.0, L.DECK[0][0], L.DECK[0][1])) @ Matrix.Rotation(L.SLOPE, 4, "X")
PRESS = SLOPE_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame
RIGHT = L.MAIN["x"][1]                                     # the main unit's right end


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    """The top seen from above."""
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def on_slope(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline on the deck, from h0 to h1 off it."""
    return solid(name, [[SLOPE_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def keyboard(m):
    """The keyboard: its outline across its width, its corners rounded in plan, the wells and the handle's groove cut
    into its top."""
    w = L.KB["width"]
    shell = prism_x("keyboard", L.KB_PROFILE, -w / 2, w / 2, m["deck"])
    bevel(shell, 2.0, segments=2)
    d = L.DECK[1][0]
    plan = rounded(0.0, d / 2 + 4.0, w, d + 8.0, L.KB["corner"], 5)
    boolean(shell, solid("plan", [[(x, y, z) for x, y in plan] for z in (-5.0, 80.0)], m["deck"]), "INTERSECT")
    boolean(shell, join([on_slope("well", outline, -L.WELL, 14.0, m["black"]) for outline in L.wells()], "wells"))
    (x0, x1), (y0, y1) = L.HANDLE["x"], L.HANDLE["y"]
    floor, top = L.HANDLE["floor"], L.DECK[0][1] + 10.0
    r = (y1 - y0) / 2
    groove = [[(x, y, z) for x, y in rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 2 * k, y1 - y0 - 2 * k, r - k, 6)]
              for k, z in ((3.0, floor), (0.0, floor + 2.5), (0.0, top))]
    boolean(shell, solid("handle", groove, m["deck"]))
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "deck")
    return shell


def main_unit(m):
    """The main unit: its outline across its width, the vents and the drive's slot cut into it, its top and its right
    end printed; the drive's bezel over its right end, the slot cut through it."""
    (x0, x1) = L.MAIN["x"]
    shell = prism_x("main", L.MAIN_PROFILE, x0, x1, m["case"])
    bevel(shell, 1.5, segments=2)
    (vy0, vy1) = L.VENT_Y
    for vent in L.VENTS:
        a, b = vent["x"]
        step = (b - a) / vent["count"]
        boolean(shell, join([box("vent", a + (k + 0.5) * step - L.VENT_WIDTH / 2, a + (k + 0.5) * step + L.VENT_WIDTH / 2,
                                 vy0, vy1, L.HEIGHT - L.VENT_DEPTH, L.HEIGHT + 5.0, m["black"])
                             for k in range(vent["count"])], "vents"))
    (sy0, sy1), (sz0, sz1) = L.SLOT["y"], L.SLOT["z"]
    boolean(shell, box("slot", RIGHT - 60.0, RIGHT + 5.0, sy0, sy1, sz0, sz1, m["black"]))
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "case" and c.z > L.HEIGHT - 0.5)
    y_front = L.MAIN["y"][0]
    end = atlas_uv(L.REGIONS["end"], L.MAIN["y"][1] - y_front, L.HEIGHT)
    paint(shell, m["print"], lambda co: end(co.y - y_front, L.HEIGHT - co.z),
          lambda c, n, name: n.x > 0.9 and c.x > RIGHT - 0.5 and name == "case")
    (by0, by1), (bz0, bz1) = L.BEZEL["y"], L.BEZEL["z"]
    bezel = box("bezel", RIGHT - 1.0, RIGHT + L.BEZEL["out"], by0, by1, bz0, bz1, m["black"])
    bevel(bezel, 0.5, segments=1)
    boolean(bezel, box("slot", RIGHT - 60.0, RIGHT + 5.0, sy0, sy1, sz0, sz1, m["black"]))
    (rx0, rx1), (ry0, ry1) = L.RESET["x"], L.RESET["y"]
    reset = box("reset", rx0, rx1, ry0, ry1, L.HEIGHT - 0.5, L.HEIGHT + L.RESET["height"], m["black"])
    bevel(reset, 0.5, segments=1)
    return [shell, bezel, reset]


def key_solid(name, outline, height, mat, m):
    """A key: from the well's floor up its sides, tapering to its printed top, height off the deck."""
    rings = [[(x, s, -L.WELL - 0.5) for x, s in outline], [(x, s, height - 4.5) for x, s in outline],
             [(x, s, height) for x, s in L.inset(outline, L.KEY_INSET)]]
    cap = solid(name, rings, mat)
    bevel(cap, 0.6, segments=1, angle=30)
    cap.data.transform(SLOPE_FRAME)
    paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.95)
    return cap


def keys(m):
    """The keys, standing in their wells: the cursor keys, the space bar and CAPS apart (the clip plays them); the
    LOCK sliders' knobs."""
    static, moving = [], {}
    for name, xu, row, wu, colour, _ in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        height = L.KEY_HEIGHT - 2.0 if row == 0 else L.KEY_HEIGHT
        cap = key_solid(name, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], height, m["key_" + colour], m)
        if name in PLAYED:
            moving[name] = cap
        else:
            static.append(cap)
    static.append(key_solid("return", L.return_outline(), L.KEY_HEIGHT, m["key_dark"], m))
    for name in ("up", "down", "left", "right"):
        moving[name] = key_solid(name, L.cursor_outline(name), L.CURSOR["height"], m["black"], m)
    mx, ms = L.cursor_middle()
    iw, idp = L.CURSOR["inner"]
    square = L.inset([(mx - iw / 2, ms - idp / 2), (mx + iw / 2, ms - idp / 2), (mx + iw / 2, ms + idp / 2),
                      (mx - iw / 2, ms + idp / 2)], 0.6)
    plug = on_slope("plug", square, -L.WELL - 0.5, L.CURSOR["height"] - 2.0, m["black"])
    bevel(plug, 0.6, segments=1)
    paint(plug, m["print"], top_uv, lambda c, n, _name: n.z > 0.95)
    static.append(plug)
    s0 = L.LOCKS["s"][0] + 1.0
    for x0, x1 in L.LOCKS["x"]:
        knob = on_slope("knob", [(x0 + 1.0, s0), (x1 - 1.0, s0), (x1 - 1.0, s0 + L.LOCKS["knob"]),
                                 (x0 + 1.0, s0 + L.LOCKS["knob"])], -1.0, 2.2, m["key_dark"])
        bevel(knob, 0.5, segments=1)
        static.append(knob)
    return static, moving


def lights(m):
    """The lit CAPS and FDD BUSY lights (each a window's glow just over its printed window) and the drive's light on
    the bezel, each its middle at its origin."""
    parts = {}
    w, d = L.LIGHTS["size"]
    for name, colour in (("caps", "green"), ("fdd", "amber")):
        x, y = L.LIGHTS[name]
        lit = box(name + "_light", x - w / 2 - 0.2, x + w / 2 + 0.2, y - d / 2 - 0.2, y + d / 2 + 0.2, L.HEIGHT + 0.05,
                  L.HEIGHT + 0.35, m["print"])
        paint(lit, m["print"], swatch(colour), lambda c, n, _name: True)
        middle = Vector((x, y, L.HEIGHT + 0.2))
        lit.data.transform(Matrix.Translation(-middle))
        parts[name + "_light"] = (lit, middle)
    (y0, y1), (z0, z1) = L.DRIVE_LIGHT["y"], L.DRIVE_LIGHT["z"]
    x = RIGHT + L.BEZEL["out"]
    lit = box("drive_light", x - 0.2, x + 0.3, y0, y1, z0, z1, m["print"])
    paint(lit, m["print"], swatch("red"), lambda c, n, _name: True)
    middle = Vector((x, (y0 + y1) / 2, (z0 + z1) / 2))
    lit.data.transform(Matrix.Translation(-middle))
    parts["drive_light"] = (lit, middle)
    return parts


def eject_button(m):
    (y0, y1), (z0, z1) = L.EJECT["y"], L.EJECT["z"]
    x = RIGHT + L.BEZEL["out"]
    part = box("eject", x - 1.0, x + L.EJECT["out"], y0, y1, z0, z1, m["key_dark"])
    bevel(part, 0.5, segments=1)
    return part


def disk(m):
    """The 3.5-inch disk, its middle at its origin, lying flat, its shutter's end towards -x (into the drive)."""
    (w, length), t = L.DISK["size"], L.DISK["thickness"]
    part = box("disk", -length / 2, length / 2, -w / 2, w / 2, -t / 2, t / 2, m["print"])
    bevel(part, 0.6, segments=1)
    top = atlas_uv(L.REGIONS["disk_top"], w, length)
    bottom = atlas_uv(L.REGIONS["disk_bottom"], w, length)
    paint(part, m["print"], lambda co: top(co.y + w / 2, co.x + length / 2), lambda c, n, name: n.z > 0.9)
    paint(part, m["print"], lambda co: bottom(w / 2 - co.y, co.x + length / 2), lambda c, n, name: n.z < -0.9)
    paint(part, m["print"], swatch("black"), lambda c, n, name: abs(n.z) <= 0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 104.0          # how far right of its seat the disk waits: wholly out of the drive


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


PLAY = dict(right=(96, 104), up=(114,), left=(124, 132), down=(144,), space=(154, 162), caps=(172, 184))


def timeline(f):
    # The disk: appears beside the drive, slides in; later pops out, is pulled clear and goes.
    if f < 6 or f >= 226:
        dsk = Pose(scale=HIDDEN)
    elif f < 16:
        dsk = Pose(x=OUT, scale=appear(f, 6, 14))
    elif f < 198:
        dsk = Pose(x=OUT * (1 - smooth(phase(f, 16, 30))))
    elif f < 210:
        dsk = Pose(x=34.0 * back_out(phase(f, 198, 204)))
    else:
        lift = ease_in(phase(f, 216, 226))
        dsk = Pose(x=34.0 + 70.0 * smooth(phase(f, 210, 218)), z=30.0 * lift, scale=max(HIDDEN, 1 - lift))

    reading = (32 <= f < 84 or 196 <= f < 202) and (f // 3) % 4 != 3
    push = smooth(phase(f, 192, 195)) * (1 - smooth(phase(f, 198, 202)))
    poses = {"disk": dsk, "eject": Pose(x=-1.6 * push),
             "fdd_light": Pose() if reading else Pose(scale=HIDDEN),
             "drive_light": Pose() if reading else Pose(scale=HIDDEN),
             "caps_light": Pose() if 175 <= f < 187 else Pose(scale=HIDDEN)}
    for name, frames in PLAY.items():
        d = 2.8 * max(tap(f, f0) for f0 in frames)
        poses[name] = Pose(x=PRESS.x * d, y=PRESS.y * d, z=PRESS.z * d)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "msx2_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    static, moving = keys(m)
    whole = join([keyboard(m)] + main_unit(m) + static, "msx2")
    eject = eject_button(m)
    floppy = disk(m)
    lit = lights(m)
    for obj in [whole, eject, floppy] + list(moving.values()):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("msx2_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    placed = [(floppy, Vector(L.SEAT))] + list(lit.values())
    for part, where in placed:
        part.parent = whole
        part.location = where
    for part in [eject] + list(moving.values()):
        part.parent = whole
    nodes = {"disk": floppy, "eject": eject, **{name: part for name, (part, _) in lit.items()}, **moving}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, eject, floppy] + [part for part, _ in lit.values()] + list(moving.values())
    print(f"MSX2: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
