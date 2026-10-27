"""The console theme's Arcadia 2001 system model (godot/themes/console/models/systems/arcadia.glb): Emerson's Arcadia
2001 and its two controllers.

Built in Blender from the real console's proportions (arcadia_layout.py has the measurements, from the magazine's figures
and photographs). The console is its walnut plinth, the dark shell on it with the two bays cut out of its top (their
rims along the ends and the front, a wedge rising at the back of each), and the centre block: its side outline extruded
across its width, the grille's and the buttons' strips sunk into its slope, the slot into its raised back. RESET,
SELECT, OPTION, START and POWER stand in their strip. Each controller lies in its bay: its body, the keypad's window sunk
into its top, the joystick's block standing on it with the spun-metal disc in its recess, the stick on the disc and a
red fire button on each side; its coiled cord (a helix round a spline) comes from the console's back over the wedge into
its top corner. The printing is one texture drawn by arcadia_print.py.

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting over the slot, shrunk to
nothing), the POWER ON light (shrunk to nothing), POWER, START and the right controller's stick, its fire buttons and
its 5 key.

The `focused` clip (8 s, looping) plays a game: the cartridge (a made-up game, its title in rainbow letters on its end)
appears over the slot, turns once to show its label and drops in; POWER goes down and the light comes on; START, then
the right controller's stick waggles and its fire buttons are pressed, 5 once; POWER again, the light goes off, and the
cartridge rises out and goes.

Five materials (shell, print, wood, dark, cord) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/arcadia_print.py artifacts/arcadia
    blender -b --factory-startup --python tools/console-models/arcadia.py -- artifacts/arcadia godot/themes/console/models/systems/arcadia.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcadia_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, prism_x  # noqa: E402
from props import tube  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 34.0    # degrees about the horizontal: the top tips up towards the viewer, the bays' controllers to see
ROUGHNESS = dict(shell=0.55, print=0.5, wood=0.6, dark=0.7, cord=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
TOP = ATLAS.uv("top", L.WIDTH, L.DEPTH)
SLOPE_FRAME = Matrix.Translation((0.0, *L.SLOPE[0])) @ Matrix.Rotation(L.SLOPE_ANGLE, 4, "X")
PRESS = SLOPE_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a button's travel


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def on_slope(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline on the centre block's slope, from h0 to h1 off it."""
    return solid(name, [[SLOPE_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def circle(cx, cy, r, n=20):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def rect(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ---- The console -----------------------------------------------------------------------------------------------------

def plinth(m):
    """The walnut band round the foot; its sides printed with the grain."""
    band = prism("plinth", rounded(0.0, L.DEPTH / 2, L.WIDTH, L.DEPTH, L.CORNER, 4), 0.0, L.PLINTH, m["wood"])
    bevel(band, 1.2, segments=1, angle=40)
    grain = ATLAS.uv("wood", 1000.0, L.PLINTH)
    paint(band, m["wood"], lambda co: grain((co.x + co.y * 1.7 + 300.0) % 1000.0, L.PLINTH - co.z),
          lambda c, n, name: abs(n.z) < 0.5)
    paint(band, m["wood"], ATLAS.swatch("black"), lambda c, n, name: abs(n.z) >= 0.5)
    return band


def shell(m):
    """The tray over the plinth with the bays cut out of it, the wedges at their backs."""
    tray = prism("tray", rounded(0.0, L.DEPTH / 2, L.WIDTH - 3.0, L.DEPTH - 3.0, L.CORNER - 1.5, 4), L.PLINTH - 1.0,
                 L.FLOOR + L.RIM["height"], m["shell"])
    bevel(tray, 2.0, segments=2, angle=40)
    rim = L.RIM["width"]
    for side in (-1, 1):
        x0, x1 = sorted((side * L.BLOCK["x"], side * (L.WIDTH / 2 - rim)))
        boolean(tray, box("bay", x0, x1, rim, L.DEPTH + 5.0, L.FLOOR, L.FLOOR + 20.0, m["shell"]))
    wedges = []
    (y0, y1), h = L.WEDGE["y"], L.WEDGE["height"]
    for side in (-1, 1):
        x0, x1 = sorted((side * (L.BLOCK["x"] - 1.0), side * (L.WIDTH / 2 - 1.6)))
        wedge = prism_x("wedge", [(y0, L.FLOOR - 1.0), (L.DEPTH - 1.6, L.FLOOR - 1.0), (L.DEPTH - 1.6, L.FLOOR + h),
                                  (y1 - 6.0, L.FLOOR + h)], x0, x1, m["shell"])
        bevel(wedge, 1.6, segments=2, angle=40)
        wedges.append(wedge)
    return [tray] + wedges


def block(m):
    """The centre block: its outline across its width, the grille's and the buttons' strips sunk into its slope, the
    slot into its raised back."""
    half = L.BLOCK["x"]
    part = prism_x("block", L.BLOCK_PROFILE, -half, half, m["shell"])
    bevel(part, 2.0, segments=2, angle=35)
    g, b = L.GRILLE, L.BUTTONS
    boolean(part, on_slope("grille", rect(*g["x"], *g["s"]), -g["depth"], 10.0, m["shell"]))
    boolean(part, on_slope("strip", rect(-56.0, 56.0, *b["s"]), -b["depth"], 10.0, m["shell"]))
    (x0, x1), (y0, y1) = L.SLOT["x"], L.SLOT["y"]
    boolean(part, box("slot", x0, x1, y0, y1, L.HEIGHT - L.SLOT["depth"], L.HEIGHT + 5.0, m["dark"]))
    return part


def button(name, outline, m, swatch):
    b = L.BUTTONS
    part = on_slope(name, outline, -b["depth"] - 1.0, -b["depth"] + b["height"] + 1.0, m["print"])
    bevel(part, 0.8, segments=1, angle=35)
    return coloured(part, m["print"], ATLAS, swatch)


def buttons(m):
    """The fixed buttons (RESET, SELECT, OPTION) and the moving ones (START, POWER), each its origin on the strip's
    floor under its middle."""
    b = L.BUTTONS
    mid = (b["s"][0] + b["s"][1]) / 2
    fixed = [button(name, circle(x, mid, b["r"]), m, "gold") for name, x in zip(("reset", "select", "option"), b["x"])]
    moving = {}
    for name, outline, middle in (("start", circle(b["x"][3], mid, b["r"]), b["x"][3]),
                                  ("power", rect(*b["power"], mid - 4.5, mid + 4.5), sum(b["power"]) / 2)):
        part = button(name, outline, m, "gold")
        at = SLOPE_FRAME @ Vector((middle, mid, -b["depth"]))
        part.data.transform(Matrix.Translation(-at))
        moving[name] = (part, at)
    lit = on_slope("power_light", circle(L.LIGHT["x"], L.LIGHT["s"], L.LIGHT["r"], 12), -0.4, 0.3, m["print"])
    coloured(lit, m["print"], ATLAS, "light")
    at = SLOPE_FRAME @ Vector((L.LIGHT["x"], L.LIGHT["s"], 0.0))
    lit.data.transform(Matrix.Translation(-at))
    moving["power_light"] = (lit, at)
    return fixed, moving


def console(m):
    whole = join([plinth(m)] + shell(m) + [block(m)], "console")
    paint(whole, m["print"], ATLAS.swatch("shell"), lambda c, n, name: name == "shell")
    paint(whole, m["print"], top_uv, lambda c, n, name: name in ("shell", "print") and n.z > 0.5)
    (x0, x1), (y0, y1) = L.SLOT["x"], L.SLOT["y"]
    paint(whole, m["print"], ATLAS.swatch("black"),
          lambda c, n, name: abs(c.x) < x1 + 0.3 and y0 - 0.3 < c.y < y1 + 0.3 and c.z < L.HEIGHT - 0.5)
    return whole


# ---- The controllers -------------------------------------------------------------------------------------------------

def pad_point(side, x, v, z=0.0):
    """A controller's point (x across it, v from its top end, z up from its foot) in the model."""
    length = L.PAD["size"][0]
    return Vector((L.PAD["x"][side] + x, L.PAD["y"] + length / 2 - v, L.FLOOR + z))


def controller(side, m):
    """A controller in its bay: its body, the keypad's window, the joystick's block and recess, the disc; its face
    printed."""
    p = L.PAD
    length, w, h = p["size"]
    name = ("left", "right")[side]
    body = prism("pad_" + name, rounded(0.0, 0.0, w, length, p["corner"], 4), 0.0, h, m["shell"])
    v0, v1, b_h = p["block"]
    blk = prism("block", rounded(0.0, length / 2 - (v0 + v1) / 2, w - 4.0, v1 - v0, 6.0, 3), h - 1.0, h + b_h,
                m["shell"])
    body = join([body, blk], "pad_" + name)
    bevel(body, 1.6, segments=2, angle=35)
    wv0, wv1, inset, depth = p["window"]
    boolean(body, box("window", -w / 2 + inset, w / 2 - inset, length / 2 - wv1, length / 2 - wv0, h - depth, h + 5.0,
                      m["shell"]))
    d = p["disc"]
    boolean(body, prism("recess", circle(0.0, length / 2 - d["v"], d["recess"], 32), h + b_h - d["depth"], h + 10.0,
                        m["shell"]))
    disc = prism("disc", circle(0.0, length / 2 - d["v"], d["r"], 32), h + b_h - d["depth"] - 0.5, h + b_h - 1.2,
                 m["shell"])
    part = join([body, disc], "pad_" + name)
    face = ATLAS.uv(name, w, length)
    coloured(part, m["print"], ATLAS, "shell")
    paint(part, m["print"], lambda co: face(co.x + w / 2, length / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    part.data.transform(Matrix.Translation(pad_point(side, 0.0, length / 2)))
    fixed = [part]
    f = p["fire"]
    moving = {}
    for k, sx in enumerate((-1, 1)):                     # the fire buttons, a red block on each long side
        fire = box("fire", *sorted((-sx * 1.0, sx * f["out"])), -(f["v"][1] - f["v"][0]) / 2, (f["v"][1] - f["v"][0]) / 2,
                   *f["z"], m["print"])
        bevel(fire, 0.6, segments=1, angle=35)
        coloured(fire, m["print"], ATLAS, "red")
        at = pad_point(side, sx * w / 2, sum(f["v"]) / 2)
        if side == 1:
            moving[f"fire{k + 1}"] = (fire, at)
        else:
            fire.data.transform(Matrix.Translation(at))
            fixed.append(fire)
    stick = joystick(m)
    at = pad_point(side, 0.0, d["v"], h + b_h - 1.2)
    if side == 1:
        moving["stick"] = (stick, at)
        key = keytop(m)
        moving["key5"] = (key, pad_point(side, p["keys"]["cols"][1], p["keys"]["rows"][1], h - depth))
    else:
        stick.data.transform(Matrix.Translation(at))
        fixed.append(stick)
    return fixed, moving


def joystick(m):
    """The stick standing on its disc, its foot at its origin."""
    r, length = L.PAD["stick"]
    k = L.PAD["knob"]
    shaft = solid("stick", [[(r * math.cos(2 * math.pi * j / 12), r * math.sin(2 * math.pi * j / 12), z)
                             for j in range(12)] for z in (-1.0, length)], m["print"])
    knob = solid("knob", [[(k * math.cos(math.radians(lat)) * math.cos(2 * math.pi * j / 14),
                            k * math.cos(math.radians(lat)) * math.sin(2 * math.pi * j / 14),
                            length + k * math.sin(math.radians(lat))) for j in range(14)] for lat in range(-60, 81, 20)],
                 m["print"])
    part = join([shaft, knob], "stick")
    return smoothed(coloured(part, m["print"], ATLAS, "stick"), 50.0)


def keytop(m):
    """The 5 key, pressed in the clip: a thin round cap over its printed key, its foot at its origin, printed as the
    face under it."""
    k = L.PAD["keys"]
    length, w, _ = L.PAD["size"]
    part = prism("key5", circle(0.0, 0.0, k["r"] - 0.6, 20), -0.4, 0.5, m["print"])
    coloured(part, m["print"], ATLAS, "champagne")
    face = ATLAS.uv("right", w, length)
    x, v = k["cols"][1], k["rows"][1]
    paint(part, m["print"], lambda co: face(x + co.x + w / 2, v - co.y), lambda c, n, kind: n.z > 0.9)
    return part


def cord(side, m):
    """A coiled cord from the console's back over the wedge into the controller's top corner: a helix round a
    spline."""
    c = L.CORD
    x_out, z_out = c["out"]
    sx = -1 if side == 0 else 1
    length, w, h = L.PAD["size"]
    start = Vector((sx * x_out, L.DEPTH + 1.0, z_out))
    end = pad_point(side, sx * (w / 2 - 9.0), 2.0, h - 4.0)
    spine = curve([start, start + Vector((sx * 6.0, 18.0, 6.0)), Vector((sx * (x_out + 20.0), L.DEPTH + 14.0,
                                                                         L.FLOOR + L.WEDGE["height"] + 16.0)),
                   end + Vector((0.0, 22.0, 16.0)), end + Vector((0.0, 6.0, 3.0)), end], 12)
    points, travelled = [], 0.0
    for i, p in enumerate(spine):
        p = Vector(p)
        a, b = Vector(spine[max(0, i - 1)]), Vector(spine[min(len(spine) - 1, i + 1)])
        t = (b - a).normalized()
        if i:
            travelled += (p - Vector(spine[i - 1])).length
        n = t.cross(Vector((0.0, 0.0, 1.0)))
        if n.length < 0.1:
            n = t.cross(Vector((1.0, 0.0, 0.0)))
        n.normalize()
        bnorm = t.cross(n)
        # The coil grows from nothing at the ends (where the plain cord meets the console and the controller).
        r = c["coil"] * min(1.0, travelled / 10.0, (sum((Vector(spine[j + 1]) - Vector(spine[j])).length
                                                        for j in range(i, len(spine) - 1))) / 10.0)
        angle = 2 * math.pi * travelled / c["pitch"]
        points.append(p + r * (math.cos(angle) * n + math.sin(angle) * bnorm))
    wire = tube("cord", [tuple(q) for q in points], c["r"], m["cord"], 6)
    return smoothed(wire, 60.0)


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, standing: its blue label to the front, its title end up."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["print"])
    bevel(part, 2.0, segments=2, angle=35)
    coloured(part, m["print"], ATLAS, "cart")
    face = ATLAS.uv("cart", w, h)
    paint(part, m["print"], lambda co: face(co.x + w / 2, h - co.z), lambda c, n, kind: n.y < -0.9)
    end = ATLAS.uv("cart_end", w, t)
    paint(part, m["print"], lambda co: end(co.x + w / 2, t / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    return smoothed(part, 40.0)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def timeline(f):
    above = L.CART["above"]
    if f < 6 or f >= 222:
        cart = Pose(z=above, scale=HIDDEN)
    elif f < 14:
        cart = Pose(z=above, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 14)))
    elif f < 30:
        cart = Pose(z=above + 5.0 * math.sin(math.pi * phase(f, 14, 30)), spin=360.0 * smooth(phase(f, 14, 30)))
    elif f < 42:
        cart = Pose(z=above * (1 - ease_in(phase(f, 30, 42))))
    elif f < 198:
        cart = Pose(z=1.4 * math.exp(-(f - 42) / 3.0) * abs(math.sin(math.pi * (f - 42) / 5.0)))
    elif f < 212:
        cart = Pose(z=above * ease_out(phase(f, 198, 212)))
    else:
        cart = Pose(z=above, scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    poses = {"cartridge": cart, "power_light": Pose() if 52 <= f < 192 else Pose(scale=HIDDEN)}
    poses["power"] = Pose(*(PRESS * 2.2 * max(tap(f, 48), tap(f, 188))))
    poses["start"] = Pose(*(PRESS * 2.2 * tap(f, 62)))
    t = phase(f, 72, 178)
    wave = math.sin(math.pi * t)
    poses["stick"] = Pose(pitch=18.0 * math.sin(2 * math.pi * 4 * t) * wave, roll=20.0 * math.sin(2 * math.pi * 3 * t
                                                                                                 + 1.1) * wave)
    poses["fire1"] = Pose(x=1.6 * max(tap(f, f0) for f0 in (84, 98, 130, 160)))
    poses["fire2"] = Pose(x=-1.6 * max(tap(f, f0) for f0 in (106, 118, 146, 168)))
    poses["key5"] = Pose(z=-0.8 * tap(f, 76))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "arcadia_print.png"))
    m = materials(dict(shell=L.COLOURS["shell"], print="#FFFFFF", wood="#FFFFFF", dark=L.COLOURS["dark"],
                       cord=L.COLOURS["cord"]), ROUGHNESS, dict(print=printed, wood=printed))

    fixed_buttons, moving = buttons(m)
    statics = [console(m)] + fixed_buttons
    for side in (0, 1):
        fixed, parts = controller(side, m)
        statics += fixed + [cord(side, m)]
        moving.update(parts)
    whole = smoothed(join(statics, "arcadia"), 35.0)
    (x0, x1), (y0, y1) = L.SLOT["x"], L.SLOT["y"]
    seat = Vector(((x0 + x1) / 2, (y0 + y1) / 2, L.HEIGHT - L.CART["inserted"]))
    moving["cartridge"] = (cartridge(m), seat)
    finish("arcadia", whole, moving, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Arcadia 2001")


if __name__ == "__main__":
    main()
