"""The console theme's PlayStation 5 system model (godot/themes/console/models/systems/ps5.glb): the first PlayStation
5 with its disc drive, standing on its stand, and its DualSense.

Built in Blender (ps5_layout.py has the measurements, taken from photographs). The core is a box with its edges
rounded, the disc slot cut into its front; each white panel is lofted up the console through its side outline's
width at each height, its outer face following the front's hourglass in and out again; the stand is a disc under it.
The DualSense is its traced outline given its depth, its edges rounded, the touchpad, the stick housings and the face
buttons on it. The printing is one texture (ps5_print.py's), projected from in front onto the core's front, from the
side onto the panels and from above onto the DualSense.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the disc (waiting in front of its slot, shrunk to nothing), the light strips lit (shrunk to nothing while
they're off), and the DualSense's sticks, d-pad, cross, circle and its light bar lit.

The `focused` clip (8 s, looping): the disc appears in front of the slot, upright, and slides in, turning; the light
strips come on, and the DualSense's light bar; the game's played on the sticks, the d-pad, cross and circle; then the
disc slides back out and goes, and the lights go off.

Three materials (white, gloss, disc) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/ps5_print.py artifacts/ps5
    blender -b --factory-startup --python tools/console-models/ps5.py -- artifacts/ps5 godot/themes/console/models/systems/ps5.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps5_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -28.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(white=0.4, gloss=0.15, disc=0.2)
FOOT = L.STAND["height"]
PAD_W, PAD_D = 160.0, 106.0
TRAVEL = 152.0            # how far in front of its seat the disc waits: its back edge just in front of the panels


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def upright(name, points, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


def table(points, x):
    x = min(max(x, points[0][0]), points[-1][0])
    for (x0, v0), (x1, v1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def span(z):
    """The panel's side outline's width at height z (above the console's foot): the front and back y where it's cut."""
    hits = []
    n = len(L.OUTLINE)
    for i in range(n):
        (y0, z0), (y1, z1) = L.OUTLINE[i], L.OUTLINE[(i + 1) % n]
        if (z0 - z) * (z1 - z) <= 0 and z0 != z1:
            hits.append(y0 + (y1 - y0) * (z - z0) / (z1 - z0))
    return min(hits), max(hits)


# ---- The console -----------------------------------------------------------------------------------------------------

def core(m):
    """The black core: its box, its edges rounded, the disc slot cut into its front; its front printed."""
    h, (y0, y1), (z0, z1) = L.CORE["half"], L.CORE["y"], L.CORE["z"]
    part = box("ps5", -h, h, y0, y1, z0, z1, m["gloss"])
    bevel(part, 4.0, segments=3, angle=40)
    sx, (s0, s1), sw = L.SLOT["x"], L.SLOT["z"], L.SLOT["width"]
    boolean(part, box("slot", sx - sw / 2, sx + sw / 2, y0 - 5.0, y0 + 12.0, s0, s1, m["gloss"]))
    colour(part, m["gloss"], "gloss")
    face = atlas_uv(L.REGIONS["front"], 2 * h, z1 - z0)
    paint(part, m["gloss"], lambda co: face(co.x + h, z1 - co.z), lambda c, n, kind: n.y < -0.9 and c.y < y0 + 0.5)
    paint(part, m["gloss"], swatch("dark"),
          lambda c, n, kind: abs(c.x - sx) < sw / 2 + 0.5 and s0 - 0.5 < c.z < s1 + 0.5 and c.y > y0 + 0.5)
    return part


def panel(m, side):
    """A white panel: lofted up the console, at each height its side outline's width, its outer face at the hourglass's
    |x| there; its outer face printed."""
    t = L.PANEL["thickness"]
    levels = [0.6 + (L.HEIGHT - 1.2) * k / 64 for k in range(65)]
    rings = []
    for z in levels:
        y0, y1 = span(z)
        out = table(L.HOURGLASS, z)
        xo, xi = side * out, side * (out - t)
        rings.append([(xo, y0, FOOT + z), (xi, y0, FOOT + z), (xi, y1, FOOT + z), (xo, y1, FOOT + z)])
    part = solid("panel", rings, m["white"])
    bevel(part, 1.4, segments=2, angle=30)
    colour(part, m["white"], "white")
    face = atlas_uv(L.REGIONS["panel"], L.DEPTH, L.HEIGHT)
    paint(part, m["white"], lambda co: face(co.y, L.HEIGHT - (co.z - FOOT)),
          lambda c, n, kind: n.x * side > 0.7)
    return part


def stand(m):
    part = upright("stand", circle(0.0, L.STAND["y"], L.STAND["r"], 40), 0.0, FOOT, m["gloss"])
    bevel(part, 2.0, segments=2)
    return colour(part, m["gloss"], "stand")


def lights(m):
    """The light strips lit, along the core's front edges; their node at the front's middle."""
    x, (z0, z1), w = L.LIGHTS["x"], L.LIGHTS["z"], L.LIGHTS["width"]
    y = L.CORE["y"][0] - 0.3
    strips = [box("light", side * x - w / 2, side * x + w / 2, y - 0.4, y + 0.2, z0, z1, m["gloss"])
              for side in (-1, 1)]
    part = colour(join(strips, "lights"), m["gloss"], "blue")
    middle = Vector((0.0, y, (z0 + z1) / 2))
    part.data.transform(Matrix.Translation(-middle))
    return part, middle


def disc(m):
    """The disc, its middle at its origin, standing upright (its axis along x), its label facing +x, its top up."""
    r, t = L.DISC["diameter"] / 2, L.DISC["thickness"]
    part = upright("disc", circle(0.0, 0.0, r, 48), -t / 2, t / 2, m["disc"])
    boolean(part, upright("hole", circle(0.0, 0.0, L.DISC["hole"] / 2, 20), -5.0, 5.0, m["disc"]))
    label = atlas_uv(L.REGIONS["disc"], 2 * r, 2 * r)
    colour(part, m["disc"], "clear")
    paint(part, m["disc"], lambda co: label(co.y + r, r + co.x), lambda c, n, kind: n.z > 0.9)
    part.data.transform(Matrix.Rotation(math.radians(90.0), 4, "Y"))
    sx, (s0, s1) = L.SLOT["x"], L.SLOT["z"]
    seat = Vector((sx, L.CORE["y"][0] + r + 4.0, (s0 + s1) / 2))
    return part, seat


# ---- The DualSense ---------------------------------------------------------------------------------------------------

PAD_TOP = atlas_uv(L.REGIONS["pad"], PAD_W, PAD_D)


def pad_uv(co):
    return PAD_TOP(co.x + PAD_W / 2, PAD_D - co.y)


def pad_frame():
    (x, y), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def arrow(cx, cy, angle, length, width):
    c, s = math.cos(angle), math.sin(angle)
    inner, outer, half = 3.0, 3.0 + length, width / 2
    local = [(inner, 0.0), (inner + half, -half), (outer, -half), (outer, half), (inner + half, half)]
    return [(cx + c * u - s * v, cy + s * u + c * v) for u, v in local]


def controller(m):
    """The DualSense in its own frame (its grips' ends at y = 0, the table at z = 0): its body, the touchpad, the stick
    housings, triangle and square, Create and Options, the PS and mute buttons; the moving parts apart, each its
    foot's middle at its origin."""
    h = L.PAD["height"]
    outline = L.PAD_RIGHT[:-1] + [(-x, y) for x, y in reversed(L.PAD_RIGHT[1:-1])]
    body = solid("dualsense", [[(x, y, z) for x, y in inset(outline, k)] for k, z in
                               ((4.0, 0.0), (0.0, 6.0), (0.0, h - 7.0), (2.6, h - 1.4), (4.4, h))], m["white"])
    colour(body, m["white"], "white")
    paint(body, m["white"], swatch("black"), lambda c, n, kind: abs(c.x) < 40.0 and c.y < 46.0 and n.z < 0.9)
    paint(body, m["white"], pad_uv, lambda c, n, kind: n.z > 0.95 and c.z > h - 0.5)
    (tx0, tx1), (ty0, ty1), tr = L.TOUCHPAD["x"], L.TOUCHPAD["y"], L.TOUCHPAD["r"]
    touch = upright("touchpad", rounded((tx0 + tx1) / 2, (ty0 + ty1) / 2, tx1 - tx0, ty1 - ty0, tr, 3), h - 1.0,
                    h + L.TOUCHPAD["height"], m["white"])
    bevel(touch, 0.6, segments=1)
    parts = [touch]
    for name in ("left", "right"):
        hx, hy = L.STICKS[name]
        housing = upright("housing", circle(hx, hy, L.STICKS["housing"], 36), h - 4.0, h + 0.6, m["white"])
        bevel(housing, 1.2, segments=2)
        parts.append(colour(housing, m["white"], "black"))
    for name in ("triangle", "square"):
        b = upright(name, circle(*L.FACE[name], L.FACE["r"], 24), h - 1.0, h + L.FACE["height"], m["gloss"])
        bevel(b, 1.0, segments=2)
        parts.append(b)
    w, hh = L.SMALL["size"]
    for name in ("create", "options"):
        parts.append(upright(name, rounded(*L.SMALL[name], w, hh, w / 2 - 0.05, 4), h - 1.0, h + 1.2, m["white"]))
    ps = upright("ps", circle(*L.SMALL["ps"], L.SMALL["ps_r"], 24), h - 1.0, h + 1.0, m["gloss"])
    bevel(ps, 0.6, segments=1)
    mute = upright("mute", rounded(*L.SMALL["mute"], 7.6, 2.4, 1.15, 3), h - 1.0, h + 0.8, m["white"])
    parts += [ps, mute]
    for part in parts:
        mat = part.data.materials[0]
        if not part.name.startswith("housing"):              # the housings are coloured black already
            colour(part, mat, "white" if mat.name == "white" else "clear")
        paint(part, mat, pad_uv, lambda c, n, kind: n.z > 0.95)
    shell = join([body] + parts, "dualsense")

    moving = {}
    for name in ("left", "right"):
        r1, (z0, z1) = L.STICKS["cap"], L.STICKS["height"]
        shaft = upright("shaft", circle(0.0, 0.0, 4.0, 16), -2.0, z0, m["white"])
        cap = solid("cap", [[(x, y, z) for x, y in circle(0.0, 0.0, r1 * k, 28)] for k, z in
                            ((0.85, z0 - 0.5), (1.0, z0 + 0.8), (1.0, z1 - 1.4), (0.92, z1))], m["white"])
        stick = colour(join([shaft, cap], name + "_stick"), m["white"], "grey")
        moving[name + "_stick"] = (stick, Vector((*L.STICKS[name], h + 0.6)))
    dx, dy = L.DPAD["at"]
    keys = []
    for k in range(4):
        part = upright("arrow", arrow(0.0, 0.0, math.radians(90 * k), L.DPAD["span"] / 2 - 3.0, L.DPAD["arm"]), -1.0,
                       L.DPAD["height"], m["gloss"])
        bevel(part, 0.6, segments=1)
        keys.append(part)
    dpad = join(keys, "dpad")
    colour(dpad, m["gloss"], "clear")
    paint(dpad, m["gloss"], lambda co: pad_uv(Vector((co.x + dx, co.y + dy, co.z))), lambda c, n, kind: n.z > 0.95)
    moving["dpad"] = (dpad, Vector((dx, dy, h)))
    for name in ("cross", "circle"):
        x, y = L.FACE[name]
        b = upright(name, circle(0.0, 0.0, L.FACE["r"], 24), -1.0, L.FACE["height"], m["gloss"])
        bevel(b, 1.0, segments=2)
        colour(b, m["gloss"], "clear")
        paint(b, m["gloss"], lambda co, x=x, y=y: pad_uv(Vector((co.x + x, co.y + y, co.z))),
              lambda c, n, kind: n.z > 0.95)
        moving[name] = (b, Vector((x, y, h)))
    strips = []
    for side, x in ((-1, tx0), (1, tx1)):
        strips.append(box("pad_light", x - side * 1.8 - 0.7, x - side * 1.8 + 0.7, ty0 + 4.0, ty1 - 2.0, -0.2, 0.3,
                          m["gloss"]))
    lit = colour(join(strips, "pad_light"), m["gloss"], "blue")
    moving["pad_light"] = (lit, Vector((0.0, 0.0, h + L.TOUCHPAD["height"])))
    return shell, moving


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    if f < 8 or f >= 214:
        cd = Pose(y=-TRAVEL, scale=HIDDEN)
    elif f < 16:
        cd = Pose(y=-TRAVEL, scale=max(HIDDEN, back_out(phase(f, 8, 15))))
    elif f < 22:
        cd = Pose(y=-TRAVEL, z=2.0 * math.sin(2 * math.pi * phase(f, 16, 22)))
    elif f < 40:
        t = smooth(phase(f, 22, 40))
        cd = Pose(y=-TRAVEL * (1 - t), pitch=-200.0 * t)
    elif f < 180:
        cd = Pose(pitch=-200.0)
    elif f < 200:
        t = smooth(phase(f, 180, 200))
        cd = Pose(y=-TRAVEL * t, pitch=-200.0 + 200.0 * t)
    else:
        cd = Pose(y=-TRAVEL, z=10.0 * ease_out(phase(f, 200, 214)), scale=max(HIDDEN, 1 - ease_in(phase(f, 204, 214))))
    t = phase(f, 60, 172)
    k = math.sin(math.pi * t)
    tilt = L.STICKS["tilt"]
    return {"disc": cd, "lights": Pose() if 42 <= f < 206 else Pose(scale=HIDDEN),
            "pad_light": Pose() if 48 <= f < 210 else Pose(scale=HIDDEN),
            "left_stick": Pose(pitch=tilt * k * math.sin(2 * math.pi * 3.0 * t),
                               roll=tilt * k * math.cos(2 * math.pi * 2.0 * t)),
            "right_stick": Pose(pitch=tilt * 0.7 * k * math.cos(2 * math.pi * 2.5 * t),
                                roll=tilt * 0.7 * k * math.sin(2 * math.pi * 1.5 * t)),
            "dpad": Pose(pitch=-7.0 * tap(f, 150, 6), roll=7.0 * tap(f, 120, 4)),
            "cross": Pose(z=-L.FACE["press"] * max(tap(f, f0) for f0 in (70, 92, 114, 136, 166))),
            "circle": Pose(z=-L.FACE["press"] * max(tap(f, f0) for f0 in (82, 104, 128, 158)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "ps5_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    console = join([core(m), panel(m, -1), panel(m, 1), stand(m)], "ps5")
    pad, pad_nodes = controller(m)
    to_world = pad_frame()
    pad.data.transform(to_world)
    whole = join([console, pad], "ps5")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("ps5_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    cd, seat = disc(m)
    parts = {"lights": lights(m), "disc": (cd, seat)}
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
    print(f"PS5: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
