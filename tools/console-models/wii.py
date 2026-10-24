"""The console theme's Wii system model (godot/themes/console/models/systems/wii.glb).

Built in Blender from the console's proportions (wii_layout.py has the measurements, taken from photographs): the white
console standing on its stand (the grey cradle under its front half, the round plate under its back), its edges
rounded; the disc slot cut down its front, POWER, RESET and EJECT standing out of it; and its remote leaning against its
right side, the D-pad and A standing out of its face. The printing (the front's legends and the SD card's flap, the
side's panel and name, the remote's face, the disc's two sides) is one texture, drawn by wii_print.py and projected
onto the faces.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: its right side, and the remote, towards
the viewer; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the disc (Odyssey, a made-up game), EJECT, the slot's glow (bright and dim), the power light lit green, and the
remote, which holds its player 1 light. The disc waits in the slot shrunk to nothing, and the lights are shrunk to
nothing, so at rest the card is the console in standby.

The `focused` clip (8 s, looping) plays a game: the disc appears in front of the slot, spinning, and slides in; the slot
glows blue, breathing, and the power light turns green; the remote's player 1 light comes on and it rumbles. Later
EJECT: the disc slides out and goes, and the slot goes dark.

Four materials (case, print, dark, stand) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/wii_print.py artifacts/wii
    blender -b --factory-startup --python tools/console-models/wii.py -- artifacts/wii godot/themes/console/models/systems/wii.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wii_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402
from psx import ring_solid  # noqa: E402

TILT_YAW = -30.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.25, print=0.25, dark=0.6, stand=0.35)


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


TOP_Z = L.LIFT + L.HEIGHT
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT)
SIDE = atlas_uv(L.REGIONS["side"], L.DEPTH, L.HEIGHT)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, TOP_Z - co.z)


def along_y(name, outline, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1."""
    return solid(name, [[(x, y, z) for x, z in outline] for y in (y0, y1)], mat)


def console(m):
    w, d = L.WIDTH, L.DEPTH
    shell = box("wii", -w / 2, w / 2, 0.0, d, L.LIFT, TOP_Z, m["case"])
    bevel(shell, L.EDGE, segments=3)
    s = L.SLOT
    (x0, x1), (z0, z1) = s["x"], s["z"]
    r = (x1 - x0) / 2
    slot = [(x0 + r + r * math.cos(math.radians(a)), L.LIFT + z1 - r + r * math.sin(math.radians(a))) for a in range(0, 181, 30)]
    slot += [(x0 + r + r * math.cos(math.radians(a)), L.LIFT + z0 + r + r * math.sin(math.radians(a))) for a in range(180, 361, 30)]
    boolean(shell, along_y("slot", slot, -5.0, s["depth"], m["dark"]))
    paint(shell, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and name == "case")
    paint(shell, m["print"], lambda co: SIDE(co.y, TOP_Z - co.z), lambda c, n, name: n.x > 0.9 and name == "case")
    parts = [shell]
    for name in ("power", "reset"):
        parts.append(button(name, m))

    # The stand: the cradle round its front half's foot, the round plate under its back.
    cw, cd, ch = L.STAND["cradle"]
    cradle = box("cradle", -cw / 2, cw / 2, 4.0, 4.0 + cd, 0.0, ch, m["stand"])
    bevel(cradle, 2.0, segments=2)
    pr, ph = L.STAND["plate"]
    plate = solid("plate", [[(pr * math.cos(2 * math.pi * k / 48), d * 0.68 + pr * math.sin(2 * math.pi * k / 48), z)
                             for k in range(48)] for z in (0.0, ph)], m["stand"])
    bevel(plate, 1.0, segments=1)
    return join(parts + [cradle, plate], "wii")


def button(name, m):
    x, z, (bw, bh) = L.BUTTONS[name]
    part = box(name, x - bw / 2, x + bw / 2, -1.2, 1.0, L.LIFT + z - bh / 2, L.LIFT + z + bh / 2, m["case"])
    bevel(part, 0.6, segments=1)
    paint(part, m["print"], front_uv, lambda c, n, _name: n.y < -0.9)
    return part


def remote(m):
    """The remote, its foot's middle at its origin, standing upright with its face towards -y."""
    w, h, t = L.REMOTE["size"]
    body = solid("remote", [[(x, y, z) for x, y in rounded(0.0, 0.0, w, t, 7.0, 4)] for z in (0.0, h)], m["case"])
    bevel(body, 3.0, segments=3)
    face = atlas_uv(L.REGIONS["remote"], w, h)
    paint(body, m["print"], lambda co: face(co.x + w / 2, h - co.z), lambda c, n, name: n.y < -0.9)
    pad = []
    for horizontal in (True, False):
        a, b = (7.5, 2.4) if horizontal else (2.4, 7.5)
        arm = box("dpad", -a, a, -t / 2 - 1.6, -t / 2 + 0.5, h - 24.0 - b, h - 24.0 + b, m["case"])
        bevel(arm, 0.5, segments=1)
        pad.append(arm)
    a_button = solid("a", [[(5.2 * math.cos(2 * math.pi * k / 24), -t / 2 + dy, h - 46.0 + 5.2 * math.sin(2 * math.pi * k / 24))
                            for k in range(24)] for dy in (0.5, -1.6)], m["case"])
    bevel(a_button, 0.8, segments=2)
    return join([body] + pad + [a_button], "remote")


def disc(m):
    """The disc, its middle at its origin, standing in the yz plane, its label towards +x."""
    d = L.DISC
    size = 2 * d["r"]
    shell = ring_solid("disc", d["r"], d["hole"], -d["thickness"] / 2, d["thickness"] / 2, m["print"])
    label, data = atlas_uv(L.REGIONS["label"], size, size), atlas_uv(L.REGIONS["data"], size, size)
    paint(shell, m["print"], lambda co: label(co.x + d["r"], d["r"] - co.y), lambda c, n, name: n.z > 0.9)
    paint(shell, m["print"], lambda co: data(co.x + d["r"], d["r"] + co.y), lambda c, n, name: n.z < -0.9)
    paint(shell, m["print"], swatch("white"), lambda c, n, name: abs(n.z) <= 0.9)
    # Stood up: its label (+z) turned to face +x, its top up.
    shell.data.transform(Matrix.Rotation(math.radians(90.0), 4, "Y") @ Matrix.Rotation(math.radians(90.0), 4, "Z"))
    return shell


def glow(m, name, colour):
    """The slot's glow: a strip just inside the slot, its middle at its origin."""
    s = L.SLOT
    (x0, x1), (z0, z1) = s["x"], s["z"]
    strip = box(name, -(x1 - x0) / 2 + 0.8, (x1 - x0) / 2 - 0.8, -0.5, 0.5, -(z1 - z0) / 2 + 3.0, (z1 - z0) / 2 - 3.0,
                m["print"])
    paint(strip, m["print"], swatch(colour), lambda c, n, _name: True)
    return strip, Vector(((x0 + x1) / 2, 2.0, L.LIFT + (z0 + z1) / 2))


def lamp(m, name, colour, w, h, at):
    lit = box(name, -w / 2, w / 2, -0.4, 0.0, -h / 2, h / 2, m["print"])
    paint(lit, m["print"], swatch(colour), lambda c, n, _name: True)
    return lit, at


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 5, f0 + 9)))


def timeline(f):
    poses = {}
    if f < 12 or f >= 200:
        poses["disc"] = Pose(scale=HIDDEN)
    elif f < 30:
        poses["disc"] = Pose(y=-150.0, pitch=-24.0 * (f - 12), scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 12, 20)))
    elif f < 180:
        t = ease_in(phase(f, 30, 46))
        poses["disc"] = Pose(y=-150.0 * (1 - t), pitch=-432.0 - 300.0 * ease_out(phase(f, 30, 46)))
    else:
        t = phase(f, 180, 200)
        poses["disc"] = Pose(y=-150.0 * ease_out(t), z=20.0 * ease_in(t), pitch=-200.0 * t,
                             scale=max(HIDDEN, 1 - ease_in(phase(f, 192, 200))))
    lit = 46 <= f < 182
    breath = (f // 15) % 2 == 0
    poses["glow"] = Pose() if lit and breath else Pose(scale=HIDDEN)
    poses["glow_dim"] = Pose() if lit and not breath else Pose(scale=HIDDEN)
    poses["power_light"] = Pose() if 46 <= f < 200 else Pose(scale=HIDDEN)
    poses["player_light"] = Pose() if 60 <= f < 196 else Pose(scale=HIDDEN)
    shake = wobble(f, 60, 2.2, 3.0, 6.0) + wobble(f, 64, -1.6, 3.0, 6.0)
    poses["remote"] = Pose(roll=shake, z=0.4 * abs(shake))
    poses["eject"] = Pose(y=1.0 * tap(f, 176))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "wii_print.png"))
    colours = dict(case=L.COLOURS["case"], print="#FFFFFF", dark=L.COLOURS["dark"], stand=L.COLOURS["stand"])
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = console(m)
    ejector = button("eject", m)
    wand = remote(m)
    platter = disc(m)
    bright, bright_at = glow(m, "glow", "glow")
    dim, dim_at = glow(m, "glow_dim", "led")
    x, z, r = L.LIGHT
    green, green_at = lamp(m, "power_light", "green", 2 * r + 0.6, 2 * r + 0.6, Vector((x, -0.05, L.LIFT + z)))
    w, h, t = L.REMOTE["size"]
    player, player_at = lamp(m, "player_light", "led", 1.8, 1.8, Vector((-6.75, -t / 2 - 0.05, 16.25)))
    for obj in (whole, ejector, wand):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("wii_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    s = L.SLOT
    seat = Vector((sum(s["x"]) / 2, L.DISC["r"] + 6.0, L.LIFT + sum(s["z"]) / 2))
    for part, where in ((ejector, Vector()), (platter, seat), (bright, bright_at), (dim, dim_at), (green, green_at)):
        part.parent = whole
        part.location = where
    rx, ry = L.REMOTE["at"]
    wand.parent = whole
    wand.location = (rx, ry, 0.0)
    wand.rotation_mode = "QUATERNION"
    wand.rotation_quaternion = Matrix.Rotation(math.radians(L.REMOTE["lean"]), 4, "Y").to_quaternion()
    player.parent = wand
    player.location = player_at
    nodes = {"eject": ejector, "disc": platter, "glow": bright, "glow_dim": dim, "power_light": green, "remote": wand,
             "player_light": player}

    bpy.context.view_layer.update()
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    points += [tilt @ (wand.matrix_basis @ v.co) for v in wand.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"Wii: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the console), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
