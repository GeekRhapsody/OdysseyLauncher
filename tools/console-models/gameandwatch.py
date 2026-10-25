"""The console theme's Game & Watch system model (godot/themes/console/models/systems/gameandwatch.glb): a Game & Watch
Multi Screen, open on the table, a made-up game on its two screens.

Built in Blender from the real handheld's proportions (gameandwatch_layout.py has the measurements, taken from
photographs). Each half is a slab, its edges rounded, its face printed; the lower half lies on the table, the D-pad,
GAME A, GAME B, TIME and JUMP standing on its face; the upper half turns on the hinges along the lower half's back edge,
open, its title plate and side panels printed. The printing is one texture drawn by gameandwatch_print.py: the two
faces (each with its screen at rest: the clock), the screens while the game's played, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the top
tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the lower half; the
lower half holding the D-pad, GAME A, JUMP, three screens over its screen and the upper half (its origin on the hinge);
the upper half holding three screens over its own.

The `focused` clip (8 s, looping) plays a game: GAME A is pressed; the rocks fall down the top screen while the ship
dodges along the bottom one, the D-pad rocking left and right, JUMP firing; then the game ends, the handheld shuts with
a snap and springs open again, back to the clock.

Four materials (case, key, glass, print) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/gameandwatch_print.py artifacts/gameandwatch
    blender -b --factory-startup --python tools/console-models/gameandwatch.py -- artifacts/gameandwatch godot/themes/console/models/systems/gameandwatch.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gameandwatch_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 22.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.45, key=0.4, glass=0.3, print=0.45)
W, D, T = L.WIDTH, L.DEPTH, L.HALF


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


LOWER = atlas_uv(L.REGIONS["lower"], W, D)
UPPER = atlas_uv(L.REGIONS["upper"], W, D)


def lower_uv(co):
    return LOWER(co.x + W / 2, D - co.y)


def upper_uv(co):
    """The upper half's face, in its own frame (y back from the hinge: its face lies from y = -D to 0)."""
    return UPPER(co.x + W / 2, D + co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def upright(name, points, z0, z1, mat):
    """A solid from an (x, y) plan, from z0 up to z1."""
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=28):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The halves ------------------------------------------------------------------------------------------------------

def lower_half(m):
    """The lower half: its slab, its face printed; GAME B and TIME; the hinges' knuckles along its back edge."""
    slab = box("gameandwatch", -W / 2, W / 2, 0.0, D, 0.0, T, m["case"])
    bevel(slab, 2.0, segments=2)
    paint(slab, m["print"], lower_uv, lambda c, n, name: n.z > 0.9)
    parts = [slab]
    sw, sh = L.SMALL["size"]
    for name in ("game_b", "time"):
        u, v = L.SMALL[name]
        pill = upright(name, [(u + a, v + b) for a, b in rounded(0.0, 0.0, sw, sh, sh / 2 - 0.01, 4)], T - 1.0,
                       T + L.SMALL["height"], m["key"])
        bevel(pill, 0.5, segments=1)
        parts.append(pill)
    for x0, x1 in ((-W / 2 + 4.0, -W / 2 + 20.0), (W / 2 - 20.0, W / 2 - 4.0)):
        knuckle = solid("knuckle", [[(x, D + 0.5 + 2.6 * math.cos(a), T + 2.6 * math.sin(a))
                                     for a in (2 * math.pi * k / 12 for k in range(12))] for x in (x0, x1)], m["case"])
        parts.append(knuckle)
    return join(parts, "gameandwatch")


def upper_half(m):
    """The upper half in its own frame (its origin on the hinge, shut: lying face down on the lower half)."""
    slab = box("upper", -W / 2, W / 2, -D, 0.0, 0.0, T, m["case"])
    bevel(slab, 2.0, segments=2)
    paint(slab, m["print"], upper_uv, lambda c, n, name: n.z < -0.9)
    tab = box("latch", -6.0, 6.0, -D - 2.0, -D + 1.0, 4.0, T + 0.5, m["case"])
    bevel(tab, 0.8, segments=1)
    return join([slab, tab], "upper")


def dpad(m):
    s, a = L.DPAD["size"] / 2, L.DPAD["arm"] / 2
    cross = [(a, s), (-a, s), (-a, a), (-s, a), (-s, -a), (-a, -a), (-a, -s), (a, -s), (a, -a), (s, -a), (s, a), (a, a)]
    part = upright("dpad", cross, -1.0, L.DPAD["height"], m["key"])
    bevel(part, 0.6, segments=1)
    return part, Vector((*L.DPAD["at"], T))


def game_a(m):
    sw, sh = L.SMALL["size"]
    part = upright("game_a", rounded(0.0, 0.0, sw, sh, sh / 2 - 0.01, 4), -1.0, L.SMALL["height"], m["key"])
    bevel(part, 0.5, segments=1)
    return part, Vector((*L.SMALL["game_a"], T))


def jump(m):
    part = solid("jump", [[(x, y, z) for x, y in circle(0.0, 0.0, L.JUMP["r"] * k)] for k, z in
                          ((1.0, -1.0), (1.0, L.JUMP["height"] - 0.8), (0.8, L.JUMP["height"]))], m["key"])
    return part, Vector((*L.JUMP["at"], T))


def screen(m, name, size, upper):
    w, h = size
    part = curved(name, w, h, 0.0, atlas_uv(L.REGIONS[name], 1.0, 1.0), m["glass"], nu=1, nv=1)
    # face up on the lower half (its picture's top towards the hinge), face down on the upper half
    part.data.transform(Matrix.Rotation(math.radians(90.0 if upper else -90.0), 4, "X"))
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


FRAMES = [(40, 1), (62, 2), (84, 3), (106, 1), (128, 2), (150, 3)]   # each step of the game: its frame, its screen


def timeline(f):
    shown = 0
    for f0, k in FRAMES:
        if f0 <= f < 172:
            shown = k
    poses = {}
    for k in (1, 2, 3):
        on = Pose() if shown == k else Pose(scale=HIDDEN)
        poses[f"lower_{k}"] = on
        poses[f"upper_{k}"] = on
    # the D-pad rocks the ship's way (left for frame 1, right for frame 3); JUMP fires on frame 2
    rock = 0.0
    for f0, k in FRAMES:
        if k != 2:
            rock += (-1 if k == 1 else 1) * tap(f, f0 - 3, 3)
    poses["dpad"] = Pose(roll=6.0 * rock)
    poses["jump"] = Pose(z=-1.4 * max(tap(f, f0 - 3) for f0, k in FRAMES if k == 2))
    poses["game_a"] = Pose(z=-1.0 * tap(f, 28))
    # the snap shut and open again
    if 180 <= f < 194:
        shut = ease_in(phase(f, 180, 194))
    elif 194 <= f < 200:
        shut = 1.0
    elif 200 <= f < 222:
        shut = 1 - back_out(phase(f, 200, 222), 1.4)
    else:
        shut = 0.0
    poses["upper"] = Pose(pitch=-L.OPEN * shut)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "gameandwatch_print.png"))
    m = {n: material(n, L.COLOURS[n], r, printed if n in ("print", "glass") else None) for n, r in ROUGHNESS.items()}

    lower = lower_half(m)
    upper = upper_half(m)
    parts = {"dpad": dpad(m), "game_a": game_a(m), "jump": jump(m)}
    (lu, lv), (uu, uv) = L.LOWER_LCD["at"], L.UPPER_LCD["at"]
    lower_screens = {f"lower_{k}": (screen(m, f"lower_{k}", L.LOWER_LCD["size"], False), Vector((lu, lv, T + 0.15)))
                     for k in (1, 2, 3)}
    upper_screens = {f"upper_{k}": (screen(m, f"upper_{k}", L.UPPER_LCD["size"], True), Vector((uu, -uv, -0.15)))
                     for k in (1, 2, 3)}
    for obj in [lower, upper] + [p for p, _ in parts.values()]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the lower half; the lower half its parts and the upper half,
    # open on its hinge; the upper half its screens.
    root = bpy.data.objects.new("gameandwatch_root", None)
    scene.collection.objects.link(root)
    lower.parent = root
    for part, where in list(parts.values()) + list(lower_screens.values()):
        part.parent = lower
        part.location = where
    upper.parent = lower
    upper.location = (0.0, D, T)
    upper.rotation_euler = (math.radians(L.OPEN), 0.0, 0.0)
    for part, where in upper_screens.values():
        part.parent = upper
        part.location = where
    nodes = {"upper": upper, **{n: p for n, (p, _) in parts.items()}, **{n: p for n, (p, _) in lower_screens.items()},
             **{n: p for n, (p, _) in upper_screens.items()}}

    # The three-quarter view, then the spec's fit of the open handheld at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    hinge = Matrix.Translation((0.0, D, T)) @ Matrix.Rotation(math.radians(L.OPEN), 4, "X")
    points = [tilt @ v.co for v in lower.data.vertices] + [tilt @ hinge @ v.co for v in upper.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = ([lower, upper] + [p for p, _ in parts.values()] + [p for p, _ in lower_screens.values()]
              + [p for p, _ in upper_screens.values()])
    print(f"Game & Watch: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(lower.data)} the lower half), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
