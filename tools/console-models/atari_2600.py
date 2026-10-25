"""The console theme's Atari 2600 system model (godot/themes/console/models/systems/atari2600.glb).

Built in Blender from the four-switch woody's proportions (atari_2600_layout.py has the measurements, taken from
photographs): its side outline extruded across its width, the grooves cut across its ribbed slope, the cartridge slot
and the switches' slots cut into its control panel's face; the chrome levers standing out of their slots; and its CX40
joystick in front of its left end, the shaft and the red button standing on its base. The printing (the panel's outline
and legends, the wood-grain strip, the cartridge's label, the joystick's top) is one texture, drawn by
atari_2600_print.py and projected onto the faces.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: its right end towards the viewer, its
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (Odyssey, a made-up game), the POWER, GAME SELECT and GAME RESET levers, and the joystick's shaft
and button. The cartridge waits in the slot shrunk to nothing, so at rest the card is the console switched off.

The `focused` clip (8 s, looping) plays a game: the cartridge appears above the slot, turns to show its label and drops
in; POWER flips on, GAME SELECT and GAME RESET flick; the joystick's shaft waggles and its button fires; then POWER goes
off and the cartridge jumps out and goes.

Four materials (case, print, dark, chrome) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/atari_2600_print.py artifacts/a2600
    blender -b --factory-startup --python tools/console-models/atari_2600.py -- artifacts/a2600 godot/themes/console/models/systems/atari2600.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari_2600_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, print=0.5, dark=0.7, chrome=0.22)
FLIP = 25.0          # degrees a lever leans either way


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def face_frame(a, b):
    """A sloping face's frame: (x, s, h) with s up the slope from a and h off it, to the model's (x, y, z); and its
    length."""
    (y0, z0), angle, length = L.frame(a, b)
    return Matrix.Translation((0.0, y0, z0)) @ Matrix.Rotation(angle, 4, "X"), length


SLOPE, SLOPE_LEN = face_frame(*L.SLOPE)
PANEL, PANEL_LEN = face_frame(*L.PANEL)
WOOD, WOOD_LEN = face_frame(L.WOOD["bottom"], L.WOOD["top"])


def framed(name, frame, x0, x1, s0, s1, h0, h1, mat):
    """A box in a face's frame."""
    part = box(name, x0, x1, s0, s1, h0, h1, mat)
    part.data.transform(frame)
    return part


def paint_face(obj, frame, length, region, mat):
    """Prints the faces lying on a frame's face (its normal, within its length) with the region, seen square on."""
    inverse = frame.inverted()
    normal = (frame.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    uv = atlas_uv(region, L.WIDTH, length)

    def keep(c, n, name):
        local = inverse @ c
        return name == "case" and n.dot(normal) > 0.99 and -0.5 < local.y < length + 0.5 and abs(local.z) < 0.5
    paint(obj, mat, lambda co: uv((inverse @ co).x + L.WIDTH / 2, length - (inverse @ co).y), keep)


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    body = prism_x("atari2600", L.profile(), -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 2.0, segments=2)
    g = L.GROOVES
    pitch = SLOPE_LEN / (g["count"] + 1)
    boolean(body, join([framed("groove", SLOPE, -L.WIDTH / 2 + 5.0, L.WIDTH / 2 - 5.0, pitch * (k + 1) - g["width"] / 2,
                               pitch * (k + 1) + g["width"] / 2, -g["depth"], 5.0, m["dark"]) for k in range(g["count"])],
                        "grooves"))
    (x0, x1), (s0, s1) = L.CART_SLOT["x"], L.CART_SLOT["s"]
    boolean(body, framed("slot", PANEL, x0, x1, s0, s1, -L.CART_SLOT["depth"], 5.0, m["dark"]))
    sw = L.SWITCH
    boolean(body, join([framed("switch_slot", PANEL, x - sw["slot"][0] / 2, x + sw["slot"][0] / 2,
                               sw["s"] - sw["slot"][1] / 2, sw["s"] + sw["slot"][1] / 2, -3.0, 5.0, m["dark"])
                        for _, x in L.SWITCHES], "switch_slots"))
    paint_face(body, PANEL, PANEL_LEN, L.REGIONS["panel"], m["print"])
    paint_face(body, WOOD, WOOD_LEN, L.REGIONS["wood"], m["print"])
    paint(body, m["print"], swatch("wood"),
          lambda c, n, name: name == "case" and c.y < L.WOOD["top"][0] + 1.0 and abs(n.x) > 0.9 and c.z > 6.0)
    return body


def lever(name, m):
    """A switch's chrome lever, its pivot at its origin, pointing along +z."""
    r, length = L.SWITCH["lever"]
    rings = [[(rr * math.cos(2 * math.pi * k / 12), rr * math.sin(2 * math.pi * k / 12), z) for k in range(12)]
             for rr, z in ((r * 0.9, -2.0), (r * 0.8, length - 2.0), (r * 1.15, length - 1.2), (r * 1.15, length),
                           (r * 0.6, length + 0.8))]
    return solid(name, rings, m["chrome"])


def cartridge(m):
    """The cartridge, its middle at its origin, upright, its label facing -y."""
    c = L.CART
    w, h, t = c["width"], c["height"], c["thickness"]
    shell = solid("cartridge", [[(x, y, z) for x, y in rounded(0.0, 0.0, w, t, 3.0, 3)] for z in (-h / 2, h / 2)],
                  m["case"])
    bevel(shell, 1.0, segments=1)
    lw, lh, from_top = c["label"]
    top = h / 2 - from_top
    label = framed("label", Matrix.Rotation(math.radians(90.0), 4, "X"), -lw / 2, lw / 2, top - lh, top, t / 2 + 0.1,
                   t / 2 + 0.2, m["print"])
    uv = atlas_uv(L.REGIONS["label"], lw, lh)
    paint(label, m["print"], lambda co: uv(co.x + lw / 2, top - co.z), lambda c_, n, name: n.y < -0.9)
    ridges = [box("ridge", -w / 2 + 6.0, w / 2 - 6.0, -t / 2 - 0.6, t / 2 + 0.6, h / 2 - 3.0 - 4.0 * k, h / 2 - 1.8 - 4.0 * k,
                  m["case"]) for k in range(1)]
    return join([shell, label] + ridges, "cartridge")


def joystick(m):
    """The CX40's base, its top printed, at its place; and its shaft and button, each its own node."""
    sx, sy = L.STICK["at"]
    w, d, h = L.STICK["base"]
    base = solid("joystick", [[(sx + x, sy + y, z) for x, y in rounded(0.0, 0.0, w, d, 10.0, 4)] for z in (0.0, h)],
                 m["case"])
    bevel(base, 2.5, segments=2)
    top = atlas_uv(L.REGIONS["stick"], w, d)
    paint(base, m["print"], lambda co: top(co.x - (sx - w / 2), (sy + d / 2) - co.y), lambda c, n, name: n.z > 0.9)
    r, length = L.STICK["shaft"]
    boot = [[(r * 2.2 * math.cos(2 * math.pi * k / 16), r * 2.2 * math.sin(2 * math.pi * k / 16), z) for k in range(16)]
            for z in (-1.0, 4.0)]
    shaft = solid("shaft", boot + [[(rr * math.cos(2 * math.pi * k / 16), rr * math.sin(2 * math.pi * k / 16), z)
                                    for k in range(16)] for rr, z in ((r, 8.0), (r * 0.9, length - 4.0), (r, length - 1.0),
                                                                      (r * 0.6, length))], m["case"])
    angle, br = L.STICK["button"]
    a = math.radians(angle)
    ring = [(br * math.cos(2 * math.pi * k / 20), br * math.sin(2 * math.pi * k / 20)) for k in range(20)]
    button = solid("fire", [[(x, y, z) for x, y in ring] for z in (-2.0, 5.0)], m["print"])
    paint(button, m["print"], swatch("red"), lambda c, n, name: True)
    shaft_at = Vector((sx + 6.0, sy - 3.0, h))
    button_at = Vector((sx + 28.0 * math.cos(a), sy + 28.0 * math.sin(a), h))
    return base, (shaft, shaft_at), (button, button_at)


# ---- The focused clip ------------------------------------------------------------------------------------------------

NORMAL = (PANEL.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()   # out of the panel's face


def along(d, **kw):
    """A pose d along the panel's normal."""
    return Pose(x=0.0, y=NORMAL.y * d, z=NORMAL.z * d, **kw)


def flick(f, f0):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 6, f0 + 10)))


def timeline(f):
    poses = {}
    above = 110.0
    if f < 10 or f >= 200:
        poses["cartridge"] = Pose(scale=HIDDEN)
    elif f < 22:
        poses["cartridge"] = along(above, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 10, 18)))
    elif f < 40:
        poses["cartridge"] = along(above - 10.0 * smooth(phase(f, 22, 40)), spin=360.0 * smooth(phase(f, 22, 40)))
    elif f < 172:
        t = ease_in(phase(f, 40, 54))
        settle = 2.0 * math.exp(-(f - 54) / 3.0) * abs(math.sin(math.pi * (f - 54) / 5.0)) if f >= 54 else 0.0
        poses["cartridge"] = along((above - 10.0) * (1 - t) + settle)
    else:
        t = phase(f, 172, 200)
        poses["cartridge"] = along(30.0 * back_out(phase(f, 172, 180)) + 60.0 * ease_in(t), spin=-200.0 * ease_in(t),
                                   scale=max(HIDDEN, 1 - ease_in(phase(f, 190, 200))))
    on = smooth(phase(f, 60, 64)) * (1 - smooth(phase(f, 164, 168)))
    poses["power"] = Pose(pitch=-2 * FLIP * on)                  # up, from OFF to ON
    poses["game_select"] = Pose(pitch=2 * FLIP * flick(f, 72))   # pushed down, springing back
    poses["game_reset"] = Pose(pitch=2 * FLIP * flick(f, 82))
    waggle = phase(f, 92, 150)
    if 0.0 < waggle < 1.0:
        envelope = math.sin(math.pi * waggle)
        poses["shaft"] = Pose(roll=18.0 * envelope * math.sin(waggle * 6 * math.pi),
                              pitch=12.0 * envelope * math.sin(waggle * 4 * math.pi + 1.0))
    poses["fire"] = Pose(z=-3.0 * sum(flick(f, f0) for f0 in (100, 112, 124, 136)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "atari_2600_print.png"))
    colours = dict(case=L.COLOURS["case"], print="#FFFFFF", dark=L.COLOURS["dark"], chrome=L.COLOURS["chrome"])
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    body = console(m)
    base, (shaft, shaft_at), (button, button_at) = joystick(m)
    levers = {}
    for name, x in L.SWITCHES:
        part = lever(name, m)
        rest = -FLIP if name in ("power",) else FLIP              # POWER rests OFF (down); the others up
        place = PANEL @ Matrix.Translation((x, L.SWITCH["s"], 0.0)) @ Matrix.Rotation(math.radians(-rest), 4, "X")
        levers[name] = (part, place)
    static = [part for name, (part, place) in levers.items() if name == "tv_type"]
    for part in static:
        part.data.transform(levers["tv_type"][1])
    whole = join([body, base] + static, "atari2600")
    cart = cartridge(m)
    for obj in [whole, cart, shaft] + [p for n, (p, _) in levers.items() if n != "tv_type"]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("atari2600_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    nodes = {}
    for name, (part, place) in levers.items():
        if name == "tv_type":
            continue
        part.parent = whole
        part.matrix_basis = place
        nodes[name] = part
    seat = PANEL @ Vector((0.0, sum(L.CART_SLOT["s"]) / 2, -L.CART_SLOT["depth"] + 2.0 + L.CART["height"] / 2))
    cart.parent = whole
    cart.matrix_basis = Matrix.Translation(seat) @ Matrix.Rotation(L.frame(*L.PANEL)[1], 4, "X")
    for part, where in ((shaft, shaft_at), (button, button_at)):
        part.parent = whole
        part.location = where
    nodes.update(cartridge=cart, shaft=shaft, fire=button)

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ (v.co + shaft_at) for v in shaft.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"Atari 2600: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
