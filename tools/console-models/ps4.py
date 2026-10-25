"""The console theme's PlayStation 4 system model (godot/themes/console/models/systems/ps4.glb): the first PlayStation 4
and its DualShock 4.

Built in Blender (ps4_layout.py has the measurements, taken from photographs). The console is its decks, each a slab
whose side is a parallelogram (the front set back at the top, the back overhanging), the slit between them set in all
round; the upper deck in its glossy and matte parts with the groove between them, where the light bar shines. The
DualShock 4 is its traced outline given its depth, its edges rounded, the touchpad, the stick housings, the d-pad and
the face buttons on it. The printing is one texture (ps4_print.py's), projected from above onto the tops, from in front
onto the fronts and from behind onto the backs.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the disc (waiting in front of its slot, shrunk to nothing), the console's light bar lit (shrunk to nothing while
it's off), and the controller's sticks, d-pad, cross, circle and lit light bar.

The `focused` clip (8 s, looping): the disc appears in front of the slot and slides in, turning; the light bar comes on
blue, and the controller's; the game's played on the sticks, the d-pad, cross and circle; then the disc slides back out
and goes, and the lights go off.

Four materials (gloss, matte, pad, disc) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/ps4_print.py artifacts/ps4
    blender -b --factory-startup --python tools/console-models/ps4.py -- artifacts/ps4 godot/themes/console/models/systems/ps4.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps4_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, export, join, material, prism_x, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(gloss=0.12, matte=0.7, pad=0.45, disc=0.2)
PAD_W, PAD_D = 162.0, 100.0


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT)
BACK = atlas_uv(L.REGIONS["back"], L.WIDTH, L.HEIGHT)
PAD_TOP = atlas_uv(L.REGIONS["pad"], PAD_W, PAD_D)


def front_y(z):
    """Where the front is at height z: set back as it rises."""
    return z * L.SLANT


def back_y(z):
    return L.DEPTH - (L.HEIGHT - z) * L.SLANT


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def upright(name, points, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


# ---- The console -----------------------------------------------------------------------------------------------------

def slab(name, x0, x1, z0, z1, mat, inset_by=0.0):
    """A deck's piece from x0 to x1 and z0 to z1, its side the console's parallelogram, set in by inset_by."""
    profile = [(front_y(z0) + inset_by, z0), (back_y(z0) - inset_by, z0), (back_y(z1) - inset_by, z1),
               (front_y(z1) + inset_by, z1)]
    return prism_x(name, profile, x0, x1, mat)


def printed(obj, mat):
    """The console's printing on a piece: its top from above, its fronts from in front, its backs from behind."""
    paint(obj, mat, lambda co: TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y), lambda c, n, name: n.z > 0.9)
    paint(obj, mat, lambda co: FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z), lambda c, n, name: n.y < -0.6)
    paint(obj, mat, lambda co: BACK(L.WIDTH / 2 - co.x, L.HEIGHT - co.z), lambda c, n, name: n.y > 0.6)


def console(m):
    """The decks, the slit's core and the groove's floor; printed."""
    half, split, g = L.WIDTH / 2, -L.WIDTH / 2 + L.GLOSS, L.GROOVE
    (s0, s1) = L.SLIT["z"]
    glossy = slab("glossy", -half, split, s1, L.HEIGHT, m["gloss"])
    matte = slab("matte", split + g, half, s1, L.HEIGHT, m["matte"])
    lower_left = slab("lower", -half, split, 0.0, s0, m["matte"])
    lower_right = slab("lower", split + g, half, 0.0, s0, m["matte"])
    parts = [glossy, matte, lower_left, lower_right]
    for part in parts:
        bevel(part, L.EDGE, segments=2, angle=40)
    core = slab("slit", -half + L.SLIT["depth"], half - L.SLIT["depth"], s0 - 1.0, s1 + 1.0, m["matte"],
                inset_by=L.SLIT["depth"])
    groove = slab("groove", split - 0.5, split + g + 0.5, 1.0, L.HEIGHT - 1.4, m["matte"], inset_by=1.4)
    for part in (core, groove):
        paint(part, m["matte"], swatch("slit"), lambda c, n, name: True)
    paint(glossy, m["gloss"], swatch("gloss"), lambda c, n, name: True)
    printed(glossy, m["gloss"])
    for part in (matte, lower_left, lower_right):
        paint(part, m["matte"], swatch("matte"), lambda c, n, name: True)
        printed(part, m["matte"])
    # The slit's front, where the disc slot and the USB ports are printed.
    paint(core, m["matte"], lambda co: FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z), lambda c, n, name: n.y < -0.6)
    return join(parts + [core, groove], "ps4")


def light_bar(m):
    """The light bar lit: along the groove's floor from the front to the back, and down the upper deck's front."""
    x = -L.WIDTH / 2 + L.GLOSS + L.GROOVE / 2
    w = L.GROOVE / 2 - 0.3
    z = L.HEIGHT - 1.2
    y0, y1 = front_y(z) + 1.4, back_y(z) - 1.4
    top = solid("light_bar", [[(x - w, y0, zz), (x + w, y0, zz), (x + w, y1, zz), (x - w, y1, zz)]
                              for zz in (z - 0.4, z)], m["matte"])
    z0, z1 = L.SLIT["z"][1] + 1.0, z
    down = solid("light_front", [[(x + dx, front_y(zz) + 1.4 + dy, zz) for dx, dy in ((-w, 0.0), (w, 0.0), (w, 0.4),
                                                                                      (-w, 0.4))] for zz in (z0, z1)],
                 m["matte"])
    lit = join([top, down], "light_bar")
    paint(lit, m["matte"], swatch("blue"), lambda c, n, name: True)
    return lit, Vector((0.0, 0.0, 0.0))


def disc(m):
    """The disc, its middle at its origin, its label up."""
    r, t = L.DISC["diameter"] / 2, L.DISC["thickness"]
    part = upright("disc", circle(0.0, 0.0, r, 48), -t / 2, t / 2, m["disc"])
    label = atlas_uv(L.REGIONS["disc"], 2 * r, 2 * r)
    paint(part, m["disc"], swatch("white"), lambda c, n, name: True)
    paint(part, m["disc"], lambda co: label(co.x + r, r - co.y), lambda c, n, name: n.z > 0.9)
    return part


# ---- The DualShock 4 -------------------------------------------------------------------------------------------------

def pad_uv(co):
    return PAD_TOP(co.x + PAD_W / 2, PAD_D - co.y)


def arrow(cx, cy, angle, length, width):
    c, s = math.cos(angle), math.sin(angle)
    inner, outer, half = 3.0, 3.0 + length, width / 2
    local = [(inner, 0.0), (inner + half, -half), (outer, -half), (outer, half), (inner + half, half)]
    return [(cx + c * u - s * v, cy + s * u + c * v) for u, v in local]


def controller(m):
    """The DualShock 4 in its own frame (its grips' ends at y = 0, the table at z = 0): its body, the touchpad, the
    stick housings, the face buttons but cross and circle, SHARE, OPTIONS, the PS button and the light bar unlit; the
    moving parts apart, each its foot's middle at its origin."""
    h = L.PAD["height"]
    # Round from the middle of its lower edge; the top edge's middle point left out, in line with its neighbours.
    outline = L.PAD_RIGHT[:-1] + [(-x, y) for x, y in reversed(L.PAD_RIGHT[1:-1])]
    body = solid("controller", [[(x, y, z) for x, y in inset(outline, k)] for k, z in
                                ((3.0, 0.0), (0.0, 5.0), (0.0, h - 6.0), (2.2, h - 1.2), (3.6, h))], m["pad"])
    paint(body, m["pad"], swatch("pad"), lambda c, n, name: True)
    paint(body, m["pad"], pad_uv, lambda c, n, name: n.z > 0.95)
    (tx0, tx1), (ty0, ty1), tr = L.TOUCHPAD["x"], L.TOUCHPAD["y"], L.TOUCHPAD["r"]
    touch = upright("touchpad", rounded((tx0 + tx1) / 2, (ty0 + ty1) / 2, tx1 - tx0, ty1 - ty0, tr, 3), h - 1.0,
                    h + L.TOUCHPAD["height"], m["pad"])
    bevel(touch, 0.6, segments=1)
    parts = [body, touch]
    for name in ("left", "right"):
        hx, hy = L.STICKS[name]
        housing = upright("housing", circle(hx, hy, L.STICKS["housing"], 36), h - 4.0, h + 0.6, m["pad"])
        bevel(housing, 1.2, segments=2)
        parts.append(housing)
    for name in ("triangle", "square"):
        b = upright(name, circle(*L.FACE[name], L.FACE["r"], 24), h - 1.0, h + L.FACE["height"], m["pad"])
        bevel(b, 1.0, segments=2)
        parts.append(b)
    sw, sh = L.SMALL["size"]
    for name in ("share", "options"):
        x, y = L.SMALL[name]
        pill = upright(name, rounded(x, y, sw, sh, sw / 2 - 0.05, 4), h - 1.0, h + 1.2, m["pad"])
        parts.append(pill)
    ps = upright("ps", circle(*L.SMALL["ps"], L.SMALL["ps_r"], 24), h - 1.0, h + 1.0, m["pad"])
    bevel(ps, 0.6, segments=1)
    parts.append(ps)
    (lx0, lx1), (lz0, lz1) = L.LIGHT_BAR["x"], L.LIGHT_BAR["z"]
    top_y = L.PAD_RIGHT[-1][1]
    unlit = solid("light_unlit", [[(x, top_y - 0.6, z) for x, z in ((lx0, lz0), (lx1, lz0), (lx1, lz1), (lx0, lz1))],
                                  [(x, top_y + 0.5, z) for x, z in ((lx0, lz0), (lx1, lz0), (lx1, lz1), (lx0, lz1))]],
                  m["pad"])
    paint(unlit, m["pad"], swatch("grey"), lambda c, n, name: True)
    parts.append(unlit)
    for part in parts[1:-1]:
        paint(part, m["pad"], swatch("pad"), lambda c, n, name: True)
        paint(part, m["pad"], pad_uv, lambda c, n, name: n.z > 0.95)
    shell = join(parts, "controller")

    moving = {}
    for name in ("left", "right"):
        (r1, (z0, z1)) = L.STICKS["cap"], L.STICKS["height"]
        shaft = upright("shaft", circle(0.0, 0.0, 4.0, 16), -2.0, z0, m["pad"])
        cap = solid("cap", [[(x, y, z) for x, y in circle(0.0, 0.0, r1 * k, 28)] for k, z in
                            ((0.85, z0 - 0.5), (1.0, z0 + 0.8), (1.0, z1 - 1.4), (0.92, z1))], m["pad"])
        stick = join([shaft, cap], name + "_stick")
        paint(stick, m["pad"], swatch("dark"), lambda c, n, _name: True)
        moving[name + "_stick"] = (stick, Vector((*L.STICKS[name], h)))
    dx, dy = L.DPAD["at"]
    arrows = []
    for k in range(4):
        a = math.radians(90 * k)
        key_ = upright("arrow", arrow(0.0, 0.0, a, L.DPAD["span"] / 2 - 3.0, L.DPAD["arm"]), -1.0, L.DPAD["height"],
                       m["pad"])
        bevel(key_, 0.6, segments=1)
        arrows.append(key_)
    dpad = join(arrows, "dpad")
    paint(dpad, m["pad"], swatch("dark"), lambda c, n, _name: True)
    moving["dpad"] = (dpad, Vector((dx, dy, h)))
    for name in ("cross", "circle"):
        b = upright(name, circle(0.0, 0.0, L.FACE["r"], 24), -1.0, L.FACE["height"], m["pad"])
        bevel(b, 1.0, segments=2)
        x, y = L.FACE[name]
        paint(b, m["pad"], swatch("pad"), lambda c, n, _name: True)
        paint(b, m["pad"], lambda co, x=x, y=y: pad_uv(Vector((co.x + x, co.y + y, co.z))),
              lambda c, n, _name: n.z > 0.95)
        moving[name] = (b, Vector((x, y, h)))
    lit = solid("light_lit", [[(x, -0.3, z) for x, z in ((lx0, lz0), (lx1, lz0), (lx1, lz1), (lx0, lz1))],
                              [(x, 0.8, z) for x, z in ((lx0, lz0), (lx1, lz0), (lx1, lz1), (lx0, lz1))]], m["pad"])
    paint(lit, m["pad"], swatch("blue"), lambda c, n, _name: True)
    moving["pad_light"] = (lit, Vector((0.0, top_y, 0.0)))
    return shell, moving


def pad_frame():
    (x, y), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    out = L.DISC["out"]
    if f < 6 or f >= 216:
        disc_ = Pose(scale=HIDDEN)
    elif f < 14:
        disc_ = Pose(y=-out, scale=max(HIDDEN, back_out(phase(f, 6, 13))))
    elif f < 24:
        disc_ = Pose(y=-out, z=1.5 * math.sin(2 * math.pi * phase(f, 14, 24)))
    elif f < 44:
        t = smooth(phase(f, 24, 44))
        disc_ = Pose(y=-out * (1 - t), spin=200.0 * t)
    elif f < 186:
        disc_ = Pose(spin=200.0)
    elif f < 206:
        t = smooth(phase(f, 186, 206))
        disc_ = Pose(y=-out * t, spin=200.0 - 200.0 * t)
    else:
        disc_ = Pose(y=-out, z=8.0 * ease_out(phase(f, 206, 216)), scale=max(HIDDEN, 1 - ease_in(phase(f, 208, 216))))
    on = 46 <= f < 206
    pad_on = 52 <= f < 210
    t = phase(f, 60, 180)
    k = math.sin(math.pi * t)
    tilt = L.STICKS["tilt"]
    return {"disc": disc_, "light_bar": Pose() if on else Pose(scale=HIDDEN),
            "pad_light": Pose() if pad_on else Pose(scale=HIDDEN),
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
    atlas = bpy.data.images.load(os.path.join(images, "ps4_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    body = console(m)
    for p in body.data.polygons:
        p.use_smooth = p.area < 40.0            # the bevels round; the decks' big faces flat
    pad, pad_nodes = controller(m)
    for p in pad.data.polygons:
        p.use_smooth = True
    to_world = pad_frame()
    pad.data.transform(to_world)
    whole = join([body, pad], "ps4")
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("ps4_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    parts = {"light_bar": light_bar(m)}
    (d0, d1) = L.DISC_SLOT["x"]
    zs = sum(L.SLIT["z"]) / 2
    parts["disc"] = (disc(m), Vector(((d0 + d1) / 2, front_y(zs) + L.DISC["diameter"] / 2 + 12.0, zs)))
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
    print(f"PS4: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
