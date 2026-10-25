"""The console theme's Atari 7800 system model (godot/themes/console/models/systems/atari7800.glb): an Atari 7800
ProSystem and its ProLine joystick.

Built in Blender from the real console's proportions (atari7800_layout.py has the measurements, taken from
photographs). The console is its side outline extruded across its width (the rounded front bumper, the strip of
switches sloping down along the top's front edge, the flat top), its edges rounded, on four feet; the cartridge slot
and the vents are cut into its top; the four keys stand on the strip. The joystick is its side outline extruded across
its width, its top rising to the back, the stick standing on its boot at its back, the orange fire buttons in its
sides. The printing is one texture drawn by atari7800_print.py: the console from above and the joystick's top
(planar-mapped onto the faces facing up), the cartridge's label, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting in its slot, shrunk to nothing), POWER, RESET, the lit power light (shrunk to nothing)
and the joystick; the joystick holding its stick and its right fire button.

The `focused` clip (8 s, looping) plays a cartridge: it drops into the slot, POWER is pressed and its light comes on,
RESET starts the game; the stick is swung about and the fire button pressed. Then POWER again, the light goes out, and
the cartridge rises out and goes.

Four materials (case, key, print, dark) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/atari7800_print.py artifacts/atari7800
    blender -b --factory-startup --python tools/console-models/atari7800.py -- artifacts/atari7800 godot/themes/console/models/systems/atari7800.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari7800_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, key=0.5, print=0.35, dark=0.7)
STRIP_FRAME = Matrix.Translation((0.0, *L.STRIP[0])) @ Matrix.Rotation(L.STRIP_SLOPE, 4, "X")
PRESS = STRIP_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame
PW, PL = L.PAD["size"]


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
STICK_TOP = atlas_uv(L.REGIONS["stick"], PL, PW)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def ring(r, z, n=24, at=(0.0, 0.0)):
    return [(at[0] + r * math.cos(2 * math.pi * k / n), at[1] + r * math.sin(2 * math.pi * k / n), z) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The console: its outline extruded, the slot and the vents cut into its top, its top printed; its feet and the
    two keys that stay."""
    w = L.WIDTH
    shell = prism_x("atari7800", L.PROFILE, -w / 2, w / 2, m["case"])
    bevel(shell, 2.0, segments=2)
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    boolean(shell, box("slot", sx0, sx1, sy0, sy1, L.TOP_Z - L.SLOT["depth"], L.TOP_Z + 5.0, m["dark"]))
    v = L.VENTS
    cuts, x = [], v["x"][0] + v["pitch"] / 2
    while x < v["x"][1]:
        cuts.append(box("vent", x - v["width"] / 2, x + v["width"] / 2, *v["y"], L.TOP_Z - v["depth"], L.TOP_Z + 5.0,
                        m["dark"]))
        x += v["pitch"]
    boolean(shell, join(cuts, "vents"))
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "case" and c.z > L.STRIP[0][1] - 1.0)
    feet = [box("foot", x - 12.0, x + 12.0, y - 10.0, y + 10.0, 0.0, L.FEET + 1.0, m["dark"])
            for x in (-110.0, 110.0) for y in (24.0, L.DEPTH - 24.0)]
    parts = [shell] + feet
    for name in ("pause", "select"):
        part, where = strip_key(name, m)
        part.data.transform(Matrix.Translation(where))
        parts.append(part)
    return parts


def strip_key(name, m):
    """A key on the strip, its foot's middle at its origin, its top printed."""
    kw, kh = L.KEYS["size"]
    x, s = L.KEYS[name], L.KEYS["s"]
    corners = [(-kw / 2, -kh / 2), (kw / 2, -kh / 2), (kw / 2, kh / 2), (-kw / 2, kh / 2)]
    frame = STRIP_FRAME.to_3x3().to_4x4()
    part = solid(name, [[frame @ Vector((a, b, h)) for a, b in corners] for h in (-1.0, L.KEYS["height"])], m["key"])
    bevel(part, 0.4, segments=1)
    where = STRIP_FRAME @ Vector((x, s, 0.0))
    paint(part, m["print"], lambda co: top_uv(co + where), lambda c, n, _name: n.z > 0.9)
    return part, where


def light(m):
    s = L.KEYS["s"]
    where = STRIP_FRAME @ Vector((L.LIGHT["x"], s, 0.05))
    frame = STRIP_FRAME.to_3x3().to_4x4()
    part = solid("power_light", [[frame @ Vector(p) for p in ring(L.LIGHT["r"] + 0.2, h, 14)] for h in (-0.2, 0.3)],
                 m["print"])
    return painted(part, m, "red_lit"), where


def cartridge(m):
    """The cartridge, its bottom's middle at its origin: its shell, its label on its front (-y) near its top."""
    w, t, h = L.CART["size"]
    lw, lh = L.CART["label"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["dark"])
    bevel(shell, 1.6, segments=2)
    z1 = h - 4.0
    decal = box("label", -lw / 2, lw / 2, -t / 2 - 0.2, -t / 2 + 0.3, z1 - lh, z1, m["print"])
    face = atlas_uv(L.REGIONS["label"], lw, lh)
    paint(decal, m["print"], lambda co: face(co.x + lw / 2, z1 - co.z), lambda c, n, name: n.y < -0.9)
    paint(decal, m["print"], swatch("silver"), lambda c, n, name: n.y >= -0.9)
    return join([shell, decal], "cartridge")


# ---- The joystick ----------------------------------------------------------------------------------------------------

def top_z(y):
    """The joystick's top at y (back from its middle)."""
    h0, h1 = L.PAD["height"]
    return h0 + (h1 - h0) * (y + PL / 2) / PL


def joystick(m):
    """The joystick in its own frame (its plan's middle at the origin, the table): its base, its top printed, the left
    fire button; the stick and the right fire button apart."""
    h0, h1 = L.PAD["height"]
    profile = [(-PL / 2, 0.0), (PL / 2, 0.0), (PL / 2, h1 - 3.0), (PL / 2 - 3.0, h1), (-PL / 2 + 3.0, h0),
               (-PL / 2, h0 - 3.0)]
    base = prism_x("joystick", profile, -PW / 2, PW / 2, m["case"])
    bevel(base, 4.0, segments=3)
    paint(base, m["print"], lambda co: STICK_TOP(co.y + PL / 2, co.x + PW / 2), lambda c, n, name: n.z > 0.95)
    left = fire(-1, m)
    right = fire(1, m)
    (b0, b1), (r, length), (kr, kh) = L.STICK["boot"], L.STICK["shaft"], L.STICK["knob"]
    boot = solid("boot", [ring(b0, -1.0, 28), ring(b0 * 0.85, 3.0, 28), ring(b1, 8.0, 28)], m["dark"])
    shaft = solid("shaft", [ring(r, 6.0, 16), ring(r, length, 16)], m["key"])
    knob = solid("knob", [ring(kr * 0.8, length - 1.0, 32), ring(kr, length + 1.5, 32), ring(kr, length + kh - 1.5, 32),
                          ring(kr * 0.85, length + kh, 32)], m["print"])
    painted(knob, m, "knob")
    stick = join([boot, shaft, knob], "stick")
    return join([base, left], "joystick"), stick, right


def fire(side, m):
    """An orange fire button in the joystick's side (side -1 the left, 1 the right)."""
    (y0, y1), (z0, z1), out = L.FIRE["y"], L.FIRE["z"], L.FIRE["out"]
    a, b = (PW / 2 - 1.0, PW / 2 + out) if side > 0 else (-PW / 2 - out, -PW / 2 + 1.0)
    part = painted(box("fire", a, b, y0, y1, z0, z1, m["print"]), m, "orange")
    bevel(part, 0.8, segments=1)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

DROP = 96.0          # how far over its seat the cartridge appears


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    if f < 8 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 18:
        cart = Pose(z=DROP, scale=appear(f, 8, 16))
    elif f < 30:
        cart = Pose(z=DROP * (1 - ease_in(phase(f, 18, 30))))
    elif f < 206:
        cart = Pose(squash=0.05 * math.sin(math.pi * phase(f, 30, 36)))
    else:
        cart = Pose(z=DROP * ease_out(phase(f, 206, 218)), scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 226))))
    on = max(tap(f, 38), tap(f, 198))
    reset = tap(f, 56)
    t = phase(f, 70, 190)
    k = math.sin(math.pi * t)
    return {"cartridge": cart,
            "power": Pose(x=PRESS.x * 1.0 * on, y=PRESS.y * 1.0 * on, z=PRESS.z * 1.0 * on),
            "reset": Pose(x=PRESS.x * 1.0 * reset, y=PRESS.y * 1.0 * reset, z=PRESS.z * 1.0 * reset),
            "power_light": Pose() if 42 <= f < 202 else Pose(scale=HIDDEN),
            "stick": Pose(pitch=20.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=20.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "fire": Pose(x=-2.4 * max(tap(f, f0) for f0 in (88, 106, 124, 142, 160, 176)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "atari7800_print.png"))
    colours = dict(L.COLOURS, dark="#121214")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join(console(m), "atari7800")
    power, power_at = strip_key("power", m)
    reset, reset_at = strip_key("reset", m)
    lit, lit_at = light(m)
    cart = cartridge(m)
    base, stick, button = joystick(m)
    for obj in [whole, power, reset, cart, base, stick, button]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("atari7800_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (sy0, sy1) = L.SLOT["y"]
    seat = Vector((0.0, (sy0 + sy1) / 2, L.TOP_Z - L.CART["seat_depth"]))
    for part, where in ((cart, seat), (power, power_at), (reset, reset_at), (lit, lit_at)):
        part.parent = whole
        part.location = where
    (px, py), turn = L.PAD["at"], math.radians(L.PAD["turn"])
    base.parent = whole
    base.location = (px, py, 0.0)
    base.rotation_euler = (0.0, 0.0, turn)
    stick.parent = base
    stick.location = (0.0, L.STICK["y"], top_z(L.STICK["y"]))
    button.parent = base
    nodes = {"cartridge": cart, "power": power, "reset": reset, "power_light": lit, "stick": stick, "fire": button}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(turn, 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in base.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, power, reset, lit, cart, base, stick, button]
    print(f"Atari 7800: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
