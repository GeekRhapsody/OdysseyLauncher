"""The console theme's Bally Astrocade system model (godot/themes/console/models/systems/astrocade.glb): the Bally
Professional Arcade and one of its pistol-grip controllers.

Built in Blender from the real console's proportions (astrocade_layout.py has the measurements, from the museum's figures
and photographs). The console is its black plinth, the walnut side panels (their outline extruded through their
thickness) and the body between them (its side outline extruded across: the walnut band, the deck's slope, the smoked
cover over the bin, the back), the cassette well cut into the deck, open over its front and running on under its lip;
the keypad's plate on the deck with its 24 keys standing on it, RESET and EJECT under the well. The controller stands
at the console's right: its side outline extruded through its width and rounded, the trigger under its head, the copper
knob on its shaft on top, its cable to the console's back. The printing is one texture drawn by astrocade_print.py.

A node tree (card.finish()): the root holding the set; the set holding the Videocade (waiting over the well, shrunk to
nothing), RESET, EJECT, the keypad's 1 and =, the knob and the trigger.

The `focused` clip (8 s, looping) plays a game: the Videocade (a made-up game) appears over the well, turns once to
show its label, drops into the well and slides back under the lip; RESET, 1 and = start it; the knob turns as a paddle
and rocks as a stick, the trigger pulled; then EJECT, and the Videocade slides out, rises and goes.

Five materials (print, wood, smoked, black, cable) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/astrocade_print.py artifacts/astrocade
    blender -b --factory-startup --python tools/console-models/astrocade.py -- artifacts/astrocade godot/themes/console/models/systems/astrocade.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import astrocade_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, prism_x  # noqa: E402
from props import tube  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(print=0.55, wood=0.6, smoked=0.25, black=0.7, cable=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
DECK_FRAME = Matrix.Translation((0.0, *L.DECK[0])) @ Matrix.Rotation(L.DECK_ANGLE, 4, "X")
NORMAL = DECK_FRAME.to_3x3() @ Vector((0.0, 0.0, 1.0))
UP_DECK = DECK_FRAME.to_3x3() @ Vector((0.0, 1.0, 0.0))
DECK_UV = ATLAS.uv("deck", 2 * L.INNER, L.DECK_LENGTH)


def deck_uv(co):
    """A point on the deck (or standing on it), by where it lies along the slope."""
    s = (co.y - L.DECK[0][0]) * math.cos(L.DECK_ANGLE) + (co.z - L.DECK[0][1]) * math.sin(L.DECK_ANGLE)
    return DECK_UV(co.x + L.INNER, L.DECK_LENGTH - min(L.DECK_LENGTH, max(0.0, s)))


def on_deck(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline on the deck, from h0 to h1 off it."""
    return solid(name, [[DECK_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def rect(x0, x1, s0, s1):
    return [(x0, s0), (x1, s0), (x1, s1), (x0, s1)]


# ---- The console -----------------------------------------------------------------------------------------------------

def panels(m):
    """The walnut side panels, their outsides printed (the front at the viewer's left, whichever side)."""
    out = []
    face = ATLAS.uv("panel", L.DEPTH, L.HEIGHT - 8.0)
    for side in (-1, 1):
        x0, x1 = sorted((side * L.INNER, side * L.WIDTH / 2))
        part = prism_x("panel", L.PANEL["outline"], x0, x1, m["wood"])
        bevel(part, 2.0, segments=2, angle=40)
        coloured(part, m["wood"], ATLAS, "wood")
        paint(part, m["wood"], (lambda co: face(co.y, L.HEIGHT - co.z)) if side > 0 else
              (lambda co: face(L.DEPTH - co.y, L.HEIGHT - co.z)), lambda c, n, name: n.x * side > 0.9)
        out.append(part)
    return out


def body(m):
    """The body between the panels: the band, the deck with its well, the cover, the back; printed."""
    part = prism_x("astrocade", L.BODY_PROFILE, -L.INNER, L.INNER, m["print"])
    bevel(part, 1.5, segments=2, angle=35)
    (x0, x1), (s0, s1) = L.WELL["x"], L.WELL["s"]
    l0, _ = L.WELL["lip"]
    depth = L.WELL["depth"]
    boolean(part, on_deck("well", rect(x0, x1, s0, l0), -depth, 10.0, m["black"]))
    boolean(part, on_deck("under_lip", rect(x0, x1, l0 - 2.0, s1), -depth, -4.0, m["black"]))
    coloured(part, m["print"], ATLAS, "black")
    paint(part, m["print"], deck_uv, lambda c, n, name: n.dot(NORMAL) > 0.98 and name == "print")
    front = ATLAS.uv("front", 2 * L.INNER, L.BAND - 8.0)
    paint(part, m["print"], lambda co: front(co.x + L.INNER, L.BAND - co.z),
          lambda c, n, name: n.y < -0.9 and c.z < L.BAND and c.y < 10.0)
    badge = ATLAS.uv("badge", 2 * L.INNER, L.HEIGHT - L.DECK[1][1])
    paint(part, m["smoked"], lambda co: badge(co.x + L.INNER, L.HEIGHT - co.z),
          lambda c, n, name: n.y < -0.9 and c.z > L.DECK[1][1] - 0.5)
    paint(part, m["smoked"], ATLAS.swatch("smoked"),
          lambda c, n, name: c.y > L.COVER["y"][0] + 0.5 and c.z > 104.0 and n.y > -0.9)
    paint(part, m["print"], ATLAS.swatch("black"), lambda c, n, name: name == "black")
    return part


def plinth(m):
    i = L.PLINTH["inset"]
    part = box("plinth", -L.WIDTH / 2 + i, L.WIDTH / 2 - i, i, L.DEPTH - i, 0.0, L.PLINTH["height"] + 1.0, m["black"])
    return coloured(part, m["print"], ATLAS, "black")


def keypad(m):
    """The keypad's plate and its keys: the fixed ones, and 1 and = apart (each its foot's middle at its origin)."""
    k = L.KEYPAD
    plate = on_deck("plate", rect(*k["x"], *k["s"]), -0.5, k["plate"], m["print"])
    paint(plate, m["print"], deck_uv, lambda c, n, name: True)
    fixed, moving = [plate], {}
    kw, kh = k["key"]
    for legend, x, s in L.keys():
        key = on_deck("key", rect(x - kw / 2, x + kw / 2, s - kh / 2, s + kh / 2), 0.0, k["plate"] + k["height"],
                      m["print"])
        bevel(key, 0.4, segments=1, angle=35)
        paint(key, m["print"], deck_uv, lambda c, n, name: True)
        name = {"1": "key1", "=": "key_equals"}.get(legend)
        if name:
            at = DECK_FRAME @ Vector((x, s, 0.0))
            key.data.transform(Matrix.Translation(-at))
            moving[name] = (key, at)
        else:
            fixed.append(key)
    for name, (a, b) in (("reset", L.KEYS["reset"]), ("eject", L.KEYS["eject"])):
        key = on_deck(name, rect(a, b, *L.KEYS["s"]), -0.5, L.KEYS["height"], m["print"])
        bevel(key, 0.5, segments=1, angle=35)
        paint(key, m["print"], deck_uv, lambda c, n, name_: True)
        at = DECK_FRAME @ Vector(((a + b) / 2, sum(L.KEYS["s"]) / 2, 0.0))
        key.data.transform(Matrix.Translation(-at))
        moving[name] = (key, at)
    return fixed, moving


def videocade(m):
    """The Videocade lying label up in the deck's frame, its middle at its origin."""
    w, length, t = L.VIDEOCADE["size"]
    lw, lh = L.VIDEOCADE["label"]
    part = box("videocade", -w / 2, w / 2, -length / 2, length / 2, -t / 2, t / 2, m["print"])
    bevel(part, 1.6, segments=2, angle=35)
    coloured(part, m["print"], ATLAS, "shell")
    face = ATLAS.uv("cart", lw, lh)
    paint(part, m["print"], lambda co: face(co.x + lw / 2, lh / 2 - co.y),
          lambda c, n, name: n.z > 0.9 and abs(c.x) < lw / 2 and abs(c.y) < lh / 2)
    part.data.transform(DECK_FRAME.to_3x3().to_4x4())
    return smoothed(part, 40.0)


# ---- The controller --------------------------------------------------------------------------------------------------

def grip_frame():
    (x, y), turn = L.GRIP["at"], L.GRIP["turn"]
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def controller(m):
    """The pistol grip standing on its foot (its front towards its own -y), its sides printed; and its cable."""
    g = L.GRIP
    w = g["width"]
    body_ = prism_x("grip", [(v - 33.0, z) for v, z in g["outline"]], -w / 2, w / 2, m["print"])
    bevel(body_, 5.0, segments=3, angle=30)
    coloured(body_, m["print"], ATLAS, "grip")
    face = ATLAS.uv("grip", 70.0, 124.0)
    paint(body_, m["print"], lambda co: face(co.y + 33.0, 124.0 - co.z), lambda c, n, name: abs(n.x) > 0.8)
    sv, sr, sh = g["shaft"]
    shaft = solid("shaft", [[(sr * math.cos(2 * math.pi * k / 12), sv - 33.0 + sr * math.sin(2 * math.pi * k / 12), z)
                             for k in range(12)] for z in (118.0, 125.0 + sh)], m["print"])
    coloured(shaft, m["print"], ATLAS, "black")
    part = join([body_, shaft], "controller")
    part.data.transform(grip_frame())
    start = grip_frame() @ Vector((0.0, g["cable"][0] - 33.0 + 10.0, g["cable"][1]))
    out = grip_frame().to_3x3() @ Vector((0.0, 1.0, 0.0))
    path = [start, start + out * 16.0 + Vector((0.0, 0.0, -1.0)), Vector((240.0, 150.0, 2.4)),
            Vector((200.0, 300.0, 2.4)), Vector((120.0, L.DEPTH + 22.0, 8.0)), Vector((110.0, L.DEPTH + 2.0, 24.0)),
            Vector((110.0, L.DEPTH - 6.0, 24.0))]
    cable = smoothed(tube("cable", curve(path, 6), 2.4, m["cable"], 10), 50.0)
    return [part, cable]


def knob(m):
    """The copper knob on its shaft, ribbed, its foot's middle at its origin."""
    r, h = L.GRIP["knob"]
    ring = [(r * (1.0 if k % 2 else 0.9) * math.cos(2 * math.pi * k / 32), r * (1.0 if k % 2 else 0.9)
             * math.sin(2 * math.pi * k / 32)) for k in range(32)]
    part = solid("knob", [[(x * f, y * f, z) for x, y in ring] for z, f in ((0.0, 0.92), (h - 3.0, 1.0),
                                                                          (h, 0.82))], m["print"])
    coloured(part, m["print"], ATLAS, "knob")
    return part


def trigger(m):
    (v0, v1), (z0, z1) = L.GRIP["trigger"]
    part = box("trigger", -7.0, 7.0, v0 - 33.0 - 8.0, v1 - 33.0, z0, z1, m["print"])
    bevel(part, 2.0, segments=2, angle=35)
    coloured(part, m["print"], ATLAS, "black")
    part.data.transform(Matrix.Rotation(math.radians(L.GRIP["turn"]), 4, "Z"))
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


ABOVE = 70.0                 # how far over the well the Videocade appears
SLIDE = 8.0                  # how far it slides back under the lip


def timeline(f):
    if f < 6 or f >= 222:
        cart = Pose(*(NORMAL * ABOVE - UP_DECK * SLIDE), scale=HIDDEN)
    elif f < 14:
        cart = Pose(*(NORMAL * ABOVE - UP_DECK * SLIDE), scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 14)))
    elif f < 30:
        lift = ABOVE + 5.0 * math.sin(math.pi * phase(f, 14, 30))
        cart = Pose(*(NORMAL * lift - UP_DECK * SLIDE), spin=360.0 * smooth(phase(f, 14, 30)))
    elif f < 40:
        cart = Pose(*(NORMAL * ABOVE * (1 - ease_in(phase(f, 30, 40))) - UP_DECK * SLIDE))
    elif f < 186:
        cart = Pose(*(-UP_DECK * SLIDE * (1 - smooth(phase(f, 42, 50)))))
    elif f < 198:
        cart = Pose(*(-UP_DECK * SLIDE * ease_out(phase(f, 188, 196))))
    elif f < 212:
        cart = Pose(*(NORMAL * ABOVE * ease_out(phase(f, 198, 212)) - UP_DECK * SLIDE))
    else:
        cart = Pose(*(NORMAL * ABOVE - UP_DECK * SLIDE), scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    poses = {"videocade": cart}
    for name, frames in (("reset", (56,)), ("key1", (66,)), ("key_equals", (76,)), ("eject", (186,))):
        poses[name] = Pose(*(-NORMAL * 1.4 * max(tap(f, f0) for f0 in frames)))
    t = phase(f, 84, 178)
    wave = math.sin(math.pi * t)
    turn = math.radians(L.GRIP["turn"])
    pitch, roll = 14.0 * math.sin(2 * math.pi * 3 * t) * wave, 14.0 * math.sin(2 * math.pi * 2 * t + 0.7) * wave
    poses["knob"] = Pose(spin=200.0 * math.sin(2 * math.pi * 1.5 * t) * wave, pitch=pitch * math.cos(turn)
                         + roll * math.sin(turn), roll=roll * math.cos(turn) - pitch * math.sin(turn))
    back = Matrix.Rotation(turn, 3, "Z") @ Vector((0.0, 3.0, 0.0))
    poses["trigger"] = Pose(*(back * max(tap(f, f0, 3) for f0 in (96, 112, 130, 150, 166))))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "astrocade_print.png"))
    m = materials(dict(print="#FFFFFF", wood="#FFFFFF", smoked="#FFFFFF", black=L.COLOURS["black"], cable="#151515"),
                  ROUGHNESS, dict(print=printed, wood=printed, smoked=printed))

    fixed, moving = keypad(m)
    whole = smoothed(join([body(m), plinth(m)] + panels(m) + fixed + controller(m), "astrocade"), 35.0)
    (x0, x1), _ = L.WELL["x"], L.WELL["s"]
    seat = DECK_FRAME @ Vector(((x0 + x1) / 2, L.SEAT_S, -L.WELL["depth"] + L.VIDEOCADE["size"][2] / 2 + 0.3))
    moving["videocade"] = (videocade(m), seat)
    sv = L.GRIP["shaft"][0]
    moving["knob"] = (smoothed(knob(m), 50.0), grip_frame() @ Vector((0.0, sv - 33.0, 125.0 + L.GRIP["shaft"][2])))
    moving["trigger"] = (smoothed(trigger(m), 40.0), grip_frame() @ Vector((0.0, 0.0, 0.0)))
    finish("astrocade", whole, moving, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Bally Astrocade")


if __name__ == "__main__":
    main()
