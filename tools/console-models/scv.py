"""The console theme's Super Cassette Vision system model (godot/themes/console/models/systems/scv.glb): Epoch's Super
Cassette Vision and its two controllers, under its flap.

Built in Blender from the real console's proportions (scv_layout.py has the measurements, taken from photographs). The
console is its base, set in, and its upper shell over it (its side outline extruded across its width), the compartment
cut under the front's slope, the slot and POWER's well into the top; the smoked flap lies over the compartment, hinged
along its back edge, the slot's two dust flaps under the cartridge; RESET, PAUSE and the SELECT pad's keys stand on the
panel. Each controller lies in its bed: a box with its two orange caps, the stick's boss and the stick; plain cords run
from their top ends to the middle. The printing is one texture drawn by scv_print.py.

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting over the slot, shrunk to
nothing), the slot's flaps, POWER's slide, the smoked flap, and the 2P controller (its stick and caps riding it).

The `focused` clip (8 s, looping) plays a game: the cartridge (a made-up game) appears over the slot, turns once to show
its label and drops in through the dust flaps; POWER slides on; the flap swings up and the 2P controller rises out of its
bed, tipped towards the player, its stick waggling and its caps pressed; it settles back, the flap shuts, POWER goes off
and the cartridge rises out and goes.

Five materials (print, case, smoked, dark, cord) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/scv_print.py artifacts/made-up-games artifacts/scv
    blender -b --factory-startup --python tools/console-models/scv.py -- artifacts/scv godot/themes/console/models/systems/scv.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scv_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, prism_x  # noqa: E402
from props import tube  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 32.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(print=0.5, case=0.5, smoked=0.15, dark=0.7, cord=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
TOP = ATLAS.uv("top", L.WIDTH, L.DEPTH)
HALF = L.WIDTH / 2
SLOPE = math.atan2(L.HINGE[1] - L.LIP[1], L.HINGE[0] - L.LIP[0])


def top_uv(co):
    return TOP(co.x + HALF, L.DEPTH - co.y)


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The base and the upper shell, the compartment, the slot and POWER's well cut; the panel's keys; printed."""
    i = L.BASE_INSET
    base = box("base", -HALF + i, HALF - i, i, L.DEPTH - i, 0.0, L.SEAM + 1.0, m["case"])
    bevel(base, 1.5, segments=1, angle=40)
    shell = prism_x("scv", [(0.0, L.SEAM), (L.DEPTH, L.SEAM), (L.DEPTH, L.HEIGHT - 3.0), (L.DEPTH - 3.0, L.HEIGHT),
                            L.HINGE, (L.LIP[0] + 2.0, L.LIP[1] - 1.0), (0.0, L.LIP[1] - 4.0)], -HALF, HALF, m["case"])
    bevel(shell, 2.5, segments=2, angle=35)
    body = join([base, shell], "scv")
    c = L.COMPARTMENT
    boolean(body, box("compartment", *c["x"], *c["y"], c["floor"], 80.0, m["dark"]))
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    boolean(body, box("slot", sx0, sx1, sy0, sy1, L.HEIGHT - L.SLOT["depth"], L.HEIGHT + 5.0, m["dark"]))
    sw = L.SWITCH
    boolean(body, box("well", sw["x"][0], sw["x"][1] + sw["travel"], *sw["y"], L.HEIGHT - 2.5, L.HEIGHT + 5.0,
                      m["dark"]))
    coloured(body, m["print"], ATLAS, "case")
    paint(body, m["print"], top_uv, lambda cc, n, name: n.z > 0.9 and cc.z > L.HEIGHT - 0.5)
    paint(body, m["print"], ATLAS.swatch("dark"), lambda cc, n, name: name == "dark")
    paint(body, m["print"], ATLAS.swatch("side"), lambda cc, n, name: name == "case" and cc.z < L.SEAM + 0.5
          and abs(n.z) < 0.5)
    keys = []
    for b in (L.RESET, L.PAUSE):
        key = box("key", *b["x"], *b["y"], L.HEIGHT - 0.5, L.HEIGHT + b["height"], m["print"])
        bevel(key, 0.5, segments=1, angle=40)
        keys.append(coloured(key, m["print"], ATLAS, "key"))
    k = L.KEYPAD
    (kx0, kx1), (ky0, ky1) = k["x"], k["y"]
    kw, kh = k["key"]
    for r in range(k["rows"]):
        for col in range(k["cols"]):
            cx = kx0 + (kx1 - kx0) * (col + 0.5) / k["cols"]
            cy = ky1 - (ky1 - ky0) * (r + 0.5) / k["rows"]
            key = box("key", cx - kw / 2, cx + kw / 2, cy - kh / 2, cy + kh / 2, L.HEIGHT - 0.5, L.HEIGHT + k["height"],
                      m["print"])
            bevel(key, 0.5, segments=1, angle=40)
            paint(key, m["print"], top_uv, lambda cc, n, name: True)
            keys.append(key)
    return join([body] + keys, "scv")


def slot_flaps(m):
    """The slot's two dust flaps, each its origin on its hinge along the slot's front or back edge."""
    (x0, x1), (y0, y1) = L.SLOT["x"], L.SLOT["y"]
    mid = (y0 + y1) / 2
    out = {}
    for name, a, b, hinge_y in (("flap_front", y0 + 0.3, mid - 0.2, y0), ("flap_back", mid + 0.2, y1 - 0.3, y1)):
        flap = box(name, x0 + 0.5, x1 - 0.5, a, b, L.HEIGHT - 2.2, L.HEIGHT - 1.0, m["print"])
        paint(flap, m["print"], top_uv, lambda cc, n, kind: True)
        hinge = Vector((0.0, hinge_y, L.HEIGHT - 1.6))
        flap.data.transform(Matrix.Translation(-hinge))
        out[name] = (flap, hinge)
    return out


def power(m):
    sw = L.SWITCH
    knob = box("power", sw["x"][0] + 1.0, sw["x"][1] - 1.0, sw["y"][0] + 1.0, sw["y"][1] - 1.0, L.HEIGHT - 2.5,
               L.HEIGHT + 1.6, m["print"])
    bevel(knob, 0.5, segments=1, angle=40)
    return coloured(knob, m["print"], ATLAS, "frame")


def flap(m):
    """The smoked flap over the compartment, its origin on its hinge along its back edge."""
    (y0, z0), (y1, z1) = L.LIP, L.HINGE
    t = L.FLAP["thickness"]
    dy, dz = t * math.sin(SLOPE), -t * math.cos(SLOPE)      # its thickness, under the slope
    rings = [[(x, y0, z0), (x, y1, z1), (x, y1 + dy, z1 + dz), (x, y0 + dy, z0 + dz)] for x in L.FLAP["x"]]
    part = solid("flap", rings, m["smoked"])
    bevel(part, 0.8, segments=1, angle=40)
    paint(part, m["smoked"], ATLAS.swatch("smoked"), lambda cc, n, kind: True)
    paint(part, m["smoked"], top_uv, lambda cc, n, kind: n.z > 0.8)
    hinge = Vector((0.0, *L.HINGE))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, standing, its label to the front."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["print"])
    bevel(part, 1.6, segments=2, angle=35)
    coloured(part, m["print"], ATLAS, "cart")
    face = ATLAS.uv("cart", w, h)
    paint(part, m["print"], lambda co: face(co.x + w / 2, h - co.z), lambda cc, n, kind: n.y < -0.9)
    return smoothed(part, 40.0)


# ---- The controllers -------------------------------------------------------------------------------------------------

def controller(name, side, m):
    """A controller lying on its back, its middle's foot at its origin, its top end (the caps') towards the middle
    (x = -side), its stick's boss towards its outer end; its face printed. Its caps and stick are made apart."""
    length, w, h = L.PAD["size"]
    body = prism("pad_" + name, rounded(0.0, 0.0, length, w, 6.0, 3), 0.0, h, m["print"])
    bevel(body, 2.4, segments=2, angle=35)
    coloured(body, m["print"], ATLAS, "pad")
    face = ATLAS.uv(name, w, length)
    # Seen from above, its top end towards the middle: v runs from the inner end outwards.
    paint(body, m["print"], (lambda co: face(w / 2 - co.y, co.x + length / 2)) if side > 0 else
          (lambda co: face(co.y + w / 2, length / 2 - co.x)), lambda cc, n, kind: n.z > 0.9)
    b = L.PAD["boss"]
    bx = side * (b["v"] - length / 2)
    boss = prism("boss", circle(bx, 0.0, b["r"], 24), h - 1.0, h + b["height"], m["print"])
    bevel(boss, 1.0, segments=1, angle=40)
    paint(boss, m["print"], (lambda co: face(w / 2 - co.y, co.x + length / 2)) if side > 0 else
          (lambda co: face(co.y + w / 2, length / 2 - co.x)), lambda cc, n, kind: True)
    part = smoothed(join([body, boss], "pad_" + name), 35.0)
    caps = []
    cv, cw = L.PAD["caps"]["v"], L.PAD["caps"]["width"]
    for k, cy in enumerate((-w / 2 + cw / 2 - 1.0, w / 2 - cw / 2 + 1.0)):
        x_in = -side * length / 2
        cap = box("cap", *sorted((x_in - side * 2.0, x_in + side * cv)), cy - cw / 2, cy + cw / 2, -1.0, h + 1.5,
                  m["print"])
        bevel(cap, 2.0, segments=2, angle=35)
        coloured(cap, m["print"], ATLAS, "orange")
        caps.append(smoothed(cap, 40.0))
    stick = stick_part(m)
    return part, caps, stick, Vector((bx, 0.0, h + b["height"]))


def stick_part(m):
    r, length = L.PAD["stick"]
    k = L.PAD["knob"]
    shaft = solid("stick", [[(r * math.cos(2 * math.pi * j / 12), r * math.sin(2 * math.pi * j / 12), z)
                             for j in range(12)] for z in (-1.0, length)], m["print"])
    knob = solid("knob", [[(k * f * (1.0 if j % 2 else 0.88) * math.cos(2 * math.pi * j / 16),
                            k * f * (1.0 if j % 2 else 0.88) * math.sin(2 * math.pi * j / 16), z) for j in range(16)]
                          for z, f in ((length - 1.0, 0.8), (length + 3.5, 1.0), (length + 4.5, 0.85))], m["print"])
    return smoothed(coloured(join([shaft, knob], "stick"), m["print"], ATLAS, "stick"), 50.0)


def cords(m):
    """The controllers' plain cords, from their top ends to the cable guide in the compartment's middle."""
    out = []
    length, _, h = L.PAD["size"]
    for side, (x, y) in zip((-1, 1), L.PAD["at"]):
        start = Vector((x - side * length / 2, y, L.COMPARTMENT["floor"] + h * 0.5))
        path = [start, start + Vector((-side * 8.0, 0.0, 0.0)), Vector((side * 14.0, y + 18.0, 6.0)),
                Vector((side * 4.0, L.COMPARTMENT["y"][1] - 4.0, 5.0)), Vector((0.0, L.COMPARTMENT["y"][1] + 2.0, 8.0))]
        out.append(smoothed(tube("cord", curve(path, 6), 2.0, m["cord"], 8), 50.0))
    return out


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def timeline(f):
    above = L.CART["above"]
    if f < 6 or f >= 226:
        cart = Pose(z=above, scale=HIDDEN)
    elif f < 14:
        cart = Pose(z=above, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 14)))
    elif f < 30:
        cart = Pose(z=above + 5.0 * math.sin(math.pi * phase(f, 14, 30)), spin=360.0 * smooth(phase(f, 14, 30)))
    elif f < 40:
        cart = Pose(z=above * (1 - ease_in(phase(f, 30, 40))))
    elif f < 204:
        cart = Pose(z=1.2 * math.exp(-(f - 40) / 3.0) * abs(math.sin(math.pi * (f - 40) / 5.0)))
    elif f < 218:
        cart = Pose(z=above * ease_out(phase(f, 204, 218)))
    else:
        cart = Pose(z=above, scale=max(HIDDEN, 1 - ease_in(phase(f, 218, 226))))
    swing = 82.0 * smooth(phase(f, 32, 37)) * (1 - smooth(phase(f, 214, 220)))
    poses = {"cartridge": cart, "flap_front": Pose(pitch=-swing), "flap_back": Pose(pitch=swing)}
    poses["power"] = Pose(x=L.SWITCH["travel"] * smooth(phase(f, 44, 50)) * (1 - smooth(phase(f, 196, 202))))
    poses["flap"] = Pose(pitch=-L.FLAP["open"] * smooth(phase(f, 56, 74)) * (1 - smooth(phase(f, 176, 194)))
                     + wobble(f, 194, 3.0, 6.0, 3.0))
    up = smooth(phase(f, 72, 90)) * (1 - smooth(phase(f, 158, 176)))
    poses["pad_2p"] = Pose(y=-34.0 * up, z=58.0 * up, pitch=40.0 * up, spin=-10.0 * up)
    t = phase(f, 94, 156)
    wave = math.sin(math.pi * t)
    poses["stick"] = Pose(pitch=18.0 * math.sin(2 * math.pi * 4 * t) * wave, roll=20.0 * math.sin(2 * math.pi * 3 * t
                                                                                                 + 0.8) * wave)
    poses["cap1"] = Pose(x=2.0 * max(tap(f, f0) for f0 in (104, 120, 146)))
    poses["cap2"] = Pose(x=2.0 * max(tap(f, f0) for f0 in (112, 132, 152)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "scv_print.png"))
    m = materials(dict(print="#FFFFFF", case=L.COLOURS["case"], smoked="#FFFFFF", dark=L.COLOURS["dark"],
                       cord=L.COLOURS["cord"]), ROUGHNESS, dict(print=printed, smoked=printed))

    floor = L.COMPARTMENT["floor"]
    cord1, cord2 = cords(m)
    statics = [console(m), cord1]
    p1, caps1, stick1, stick1_at = controller("pad1", -1, m)
    x1, y1 = L.PAD["at"][0]
    for part in [p1] + caps1:
        part.data.transform(Matrix.Translation((x1, y1, floor)))
    stick1.data.transform(Matrix.Translation(Vector((x1, y1, floor)) + stick1_at))
    statics += [p1, stick1] + caps1
    whole = smoothed(join(statics, "scv"), 35.0)
    p2, caps2, stick2, stick2_at = controller("pad2", 1, m)
    x2, y2 = L.PAD["at"][1]
    cord2.data.transform(Matrix.Translation((-x2, -y2, -floor)))       # its cord rides with it when it's lifted
    p2 = join([p2, cord2], "pad_2p")
    parts = {"pad_2p": (p2, Vector((x2, y2, floor))), "stick": (stick2, stick2_at, "pad_2p")}
    for k, cap in enumerate(caps2):
        parts[f"cap{k + 1}"] = (cap, Vector(), "pad_2p")
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    parts["cartridge"] = (cartridge(m), Vector(((sx0 + sx1) / 2, (sy0 + sy1) / 2, L.HEIGHT - L.CART["inserted"])))
    parts.update(slot_flaps(m))
    parts["power"] = (power(m), Vector())
    lid, hinge = flap(m)
    parts["flap"] = (lid, hinge)
    finish("scv", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Super Cassette Vision")


if __name__ == "__main__":
    main()
