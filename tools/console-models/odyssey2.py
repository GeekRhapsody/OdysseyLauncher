"""The console theme's Odyssey² system model (godot/themes/console/models/systems/odyssey2.glb): a Magnavox Odyssey² and
its two joysticks.

Built in Blender from the real console's proportions (odyssey2_layout.py has the measurements, taken from
photographs). The case is the black body and the silver top over it, each its side outline extruded across the width;
the keyboard's panel is sunk into the top's slope and the slot's panel into its back, the slot cut through both. The
POWER key stands in the slot's panel. The joysticks are black boxes, a plate on each, the stick in its ring, ACTION at
the plate's back left. The printing is one texture drawn by odyssey2_print.py: the keyboard's panel and the slot's
panel (planar-mapped onto their floors), the logo (a decal on the silver), the cartridge's label, the joysticks'
plates, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting in its slot, shrunk to nothing), POWER, and the first joystick; the joystick holding its
stick and ACTION.

The `focused` clip (8 s, looping) plays a cartridge: it drops into the slot, POWER goes in, and the game is played on
the joystick, the stick swung about and ACTION pressed. Then POWER again, and the cartridge comes out and goes.

Five materials (silver, body, black, red, print) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/odyssey2_print.py artifacts/odyssey2
    blender -b --factory-startup --python tools/console-models/odyssey2.py -- artifacts/odyssey2 godot/themes/console/models/systems/odyssey2.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odyssey2_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(silver=0.35, body=0.55, black=0.6, red=0.4, print=0.5)

# The keyboard's slope and the flat back: their frames (x across, s along them from their front edges, h off them).
KB_FRAME = Matrix.Translation((0.0, L.TOP[0][0], L.TOP[0][1])) @ Matrix.Rotation(L.SLOPE, 4, "X")
(BY0, BZ0), (BY1, BZ1) = L.TOP[4], L.TOP[5]
BACK_FRAME = Matrix.Translation((0.0, BY0, BZ0)) @ Matrix.Rotation(math.atan2(BZ1 - BZ0, BY1 - BY0), 4, "X")


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def back_s(y):
    """How far along the flat back a point y back from the front edge is."""
    return (y - BY0) / math.cos(math.atan2(BZ1 - BZ0, BY1 - BY0))


def on_frame(frame, name, outline, h0, h1, mat):
    """A solid from an (x, s) outline in a frame, from h0 to h1 off it."""
    return solid(name, [[frame @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


# ---- The case --------------------------------------------------------------------------------------------------------

def case(m):
    """The black body and the silver top: the keyboard's and the slot's panels sunk into the top, the slot through
    both, the panels' floors printed; the logo's decal."""
    top_line = L.TOP
    under = [(y, z - L.SHELL) for y, z in top_line]
    silver = prism_x("odyssey2", top_line + list(reversed(under)), -L.WIDTH / 2, L.WIDTH / 2, m["silver"])
    bevel(silver, 2.4, segments=2)
    i = L.BODY_INSET
    body_line = [(max(i, min(L.DEPTH - i, y)), z - L.SHELL + 1.0) for y, z in reversed(top_line)]
    body = prism_x("body", [(i, 0.0), (L.DEPTH - i, 0.0)] + body_line, -L.WIDTH / 2 + i, L.WIDTH / 2 - i, m["body"])
    bevel(body, 1.5, segments=2)

    (kx0, kx1), (ks0, ks1) = L.KEYBOARD["x"], L.KEYBOARD["s"]
    panel = rounded((kx0 + kx1) / 2, (ks0 + ks1) / 2, kx1 - kx0, ks1 - ks0, L.KEYBOARD["corner"], 4)
    boolean(silver, on_frame(KB_FRAME, "keys", panel, -L.KEYBOARD["sink"], 12.0, m["black"]))
    face = atlas_uv(L.REGIONS["keyboard"], kx1 - kx0, ks1 - ks0)
    inverse = KB_FRAME.inverted()

    def key_uv(co):
        local = inverse @ co
        return face(local.x - kx0, ks1 - local.y)
    paint(silver, m["print"], key_uv, lambda c, n, name: name == "black" and n.z > 0.9 and c.y < 200.0)

    (bx0, bx1), (by0, by1) = L.BACK["x"], L.BACK["y"]
    s0, s1 = back_s(by0), back_s(by1)
    outline = rounded((bx0 + bx1) / 2, (s0 + s1) / 2, bx1 - bx0, s1 - s0, 3.0, 3)
    boolean(silver, on_frame(BACK_FRAME, "back", outline, -L.BACK["sink"], 12.0, m["black"]))
    back = atlas_uv(L.REGIONS["back"], bx1 - bx0, by1 - by0)
    back_inverse = BACK_FRAME.inverted()

    def back_uv(co):
        local = back_inverse @ co
        return back(local.x - bx0, s1 - local.y)
    paint(silver, m["print"], back_uv, lambda c, n, name: name == "black" and n.z > 0.9 and c.y > 240.0)

    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    z_floor = BZ1 - L.SLOT["depth"]
    for shell in (silver, body):
        boolean(shell, box("slot", sx0, sx1, sy0, sy1, z_floor, 95.0, m["black"]))

    (lx0, lx1), (ly0, ly1) = L.LOGO["x"], L.LOGO["y"]
    t0, t1 = back_s(ly0), back_s(ly1)
    decal = on_frame(BACK_FRAME, "logo", [(lx0, t0), (lx1, t0), (lx1, t1), (lx0, t1)], 0.05, 0.1, m["print"])
    logo = atlas_uv(L.REGIONS["logo"], lx1 - lx0, ly1 - ly0)
    paint(decal, m["print"], lambda co: logo(co.x - lx0, ly1 - co.y), lambda c, n, name: True)
    return [silver, body, decal]


def floor_z(y):
    """The slot's panel's floor at y."""
    return (BACK_FRAME @ Vector((0.0, back_s(y), -L.BACK["sink"]))).z


def power(m):
    (x0, x1), (y0, y1) = L.POWER["x"], L.POWER["y"]
    z0 = floor_z(y1) - 0.5
    part = box("power", x0, x1, y0, y1, z0, z0 + 0.5 + L.POWER["height"], m["red"])
    bevel(part, 0.8, segments=2)
    return part


def cartridge(m):
    """The cartridge, its bottom's middle at its origin: a black shell, its label on its front (towards -y)."""
    w, d, h = L.CART["size"]
    lw, lh = L.CART["label"]
    shell = box("cartridge", -w / 2, w / 2, -d / 2, d / 2, 0.0, h, m["body"])
    bevel(shell, 1.2, segments=2)
    z1 = h - 4.0
    decal = box("label", -lw / 2, lw / 2, -d / 2 - 0.15, -d / 2 + 0.2, z1 - lh, z1, m["print"])
    face = atlas_uv(L.REGIONS["label"], lw, lh)
    paint(decal, m["print"], lambda co: face(co.x + lw / 2, z1 - co.z), lambda c, n, name: n.y < -0.9)
    paint(decal, m["print"], swatch("black"), lambda c, n, name: n.y >= -0.9)
    return join([shell, decal], "cartridge")


# ---- The joysticks ---------------------------------------------------------------------------------------------------

def joystick(m, n):
    """A joystick in its own frame (its middle at the origin, the table): its box and plate; its stick and ACTION
    apart, each its foot's middle at its origin."""
    S = L.STICK
    bw, bd, bh = S["box"]
    pw, pd, ph = S["plate"]
    shell = box(f"joystick_{n}", -bw / 2, bw / 2, -bd / 2, bd / 2, 0.0, bh, m["body"])
    bevel(shell, 4.0, segments=2)
    plate = box("plate", -pw / 2, pw / 2, -pd / 2, pd / 2, bh - 1.0, bh + ph, m["body"])
    bevel(plate, 1.5, segments=2)
    face = atlas_uv(L.REGIONS["stick"], pw, pd)
    paint(plate, m["print"], lambda co: face(co.x + pw / 2, pd / 2 - co.y), lambda c, n_, name: n_.z > 0.9)
    top = bh + ph
    ring = solid("ring", [[(S["ring"] * math.cos(a), S["ring"] * math.sin(a), z)
                           for a in (2 * math.pi * k / 12 for k in range(12))] for z in (top - 0.5, top + 3.0)],
                 m["black"])
    shell = join([shell, plate, ring], f"joystick_{n}")
    r, length = S["shaft"]
    shaft = solid(f"stick_{n}", [[(r * math.cos(a), r * math.sin(a), z) for a in (2 * math.pi * k / 12 for k in
                                                                                  range(12))] for z in (0.0, length)],
                  m["black"])
    knob = solid("knob", [[(S["knob"] * k * math.cos(a), S["knob"] * k * math.sin(a), z)
                           for a in (2 * math.pi * j / 16 for j in range(16))]
                          for k, z in ((0.55, length - 2.0), (1.0, length + 2.0), (0.9, length + 6.0), (0.4, length + 8.0))],
                 m["black"])
    stick = join([shaft, knob], f"stick_{n}")
    ax, ay, aw, ad, ah = S["action"]
    action = box(f"action_{n}", -aw / 2, aw / 2, -ad / 2, ad / 2, -0.5, ah, m["print"])
    bevel(action, 0.6, segments=1)
    paint(action, m["print"], lambda co: face(co.x + ax + pw / 2, pd / 2 - (co.y + ay)), lambda c, n_, name: n_.z > 0.9)
    paint(action, m["print"], swatch("red"), lambda c, n_, name: n_.z <= 0.9)
    return shell, (stick, Vector((0.0, 0.0, top + 3.0))), (action, Vector((ax, ay, top)))


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


DROP = 96.0          # how far over its seat the cartridge appears


def timeline(f):
    if f < 8 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 18:
        cart = Pose(z=DROP, scale=appear(f, 8, 16))
    elif f < 30:
        cart = Pose(z=DROP * (1 - ease_in(phase(f, 18, 30))))
    elif f < 204:
        cart = Pose(squash=0.05 * math.sin(math.pi * phase(f, 30, 36)))
    else:
        cart = Pose(z=DROP * ease_out(phase(f, 204, 216)), scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 226))))
    t = phase(f, 50, 188)
    k = math.sin(math.pi * t)
    return {"cartridge": cart, "power": Pose(z=-2.2 * max(tap(f, 38), tap(f, 196))),
            "stick_1": Pose(pitch=22.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=22.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "action_1": Pose(z=-1.8 * max(tap(f, f0) for f0 in (74, 96, 118, 140, 162)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "odyssey2_print.png"))
    m = {n: material(n, L.COLOURS[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    parts = case(m)
    key_power = power(m)
    cart = cartridge(m)
    (pad_1, (stick_1, stick_at), (action_1, action_at)), second = joystick(m, 1), joystick(m, 2)
    pad_2, (stick_2, stick_2_at), (action_2, action_2_at) = second
    stick_2.data.transform(Matrix.Translation(stick_2_at))
    action_2.data.transform(Matrix.Translation(action_2_at))
    pad_2 = join([pad_2, stick_2, action_2], "joystick_2")
    s2 = L.STICKS[1]
    pad_2.data.transform(Matrix.Translation((*s2["at"], 0.0)) @ Matrix.Rotation(math.radians(s2["turn"]), 4, "Z"))
    whole = join(parts + [pad_2], "odyssey2")
    for obj in [whole, key_power, cart, pad_1, stick_1, action_1]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("odyssey2_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    seat = Vector(((sx0 + sx1) / 2, (sy0 + sy1) / 2, floor_z((sy0 + sy1) / 2) - L.CART["depth"]))
    cart.parent = whole
    cart.location = seat
    key_power.parent = whole
    s1 = L.STICKS[0]
    pad_1.parent = whole
    pad_1.location = (*s1["at"], 0.0)
    pad_1.rotation_euler = (0.0, 0.0, math.radians(s1["turn"]))
    stick_1.parent = pad_1
    stick_1.location = stick_at
    action_1.parent = pad_1
    action_1.location = action_at
    nodes = {"cartridge": cart, "power": key_power, "stick_1": stick_1, "action_1": action_1}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((*s1["at"], 0.0)) @ Matrix.Rotation(math.radians(s1["turn"]), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in pad_1.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, key_power, cart, pad_1, stick_1, action_1]
    print(f"Odyssey2: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
