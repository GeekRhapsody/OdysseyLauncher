"""The console theme's CreatiVision system model (godot/themes/console/models/systems/crvision.glb): VTech's
CreatiVision and its two controllers, docked.

Built in Blender from the real console's proportions (crvision_layout.py has the measurements, taken from photographs).
The console is a box, its ends set in for the woodgrain panels between the four corner posts, the compartment cut into
the front of its top either side of the divider, the slide switch's well in the deck; the cartridge slot's frame stands
out of the right end's foot. Each controller is a slab docked in its tray, the keypad's window in its raised frame, the
joystick's well with the knob standing in it. The printing is one texture drawn by crvision_print.py.

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting right of the slot, shrunk
to nothing), the OFF/ON slide and the right controller, which holds its knob.

The `focused` clip (8 s, looping) plays a game: the cartridge (a made-up game) slides into the slot and the switch goes
to ON; the right controller rises out of its tray and tips towards the player, its knob waggling; then it settles back
into its tray, the switch goes OFF and the cartridge slides out and goes.

Four materials (print, case, wood, deep) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/crvision_print.py artifacts/made-up-games artifacts/crvision
    blender -b --factory-startup --python tools/console-models/crvision.py -- artifacts/crvision godot/themes/console/models/systems/crvision.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crvision_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402

TILT_YAW = -26.0     # degrees about the vertical: the right end (the slot) comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(print=0.65, case=0.75, wood=0.6, deep=0.8)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
TOP = ATLAS.uv("top", L.WIDTH, L.DEPTH)
HALF = L.WIDTH / 2


def top_uv(co):
    return TOP(co.x + HALF, L.DEPTH - co.y)


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The box with its ends set in, the compartment, the switch's well and the slot cut; the posts, the woodgrain
    panels and the slot's frame; the top printed."""
    t = L.PANEL["thickness"]
    body = box("crvision", -HALF + t, HALF - t, 0.0, L.DEPTH, 0.0, L.HEIGHT, m["case"])
    bevel(body, 1.5, segments=1, angle=40)
    (t0, t1), d = L.TRAYS["y"], L.TRAYS["divider"]
    for x0, x1 in ((-HALF + L.POST, -d / 2), (d / 2, HALF - L.POST)):
        boolean(body, box("tray", x0, x1, t0, t1, L.TRAYS["floor"], L.HEIGHT + 5.0, m["deep"]))
    boolean(body, box("front", -HALF + L.POST, HALF - L.POST, -5.0, t0, L.FRONT_TOP, L.HEIGHT + 5.0, m["case"]))
    sw = L.SWITCH
    boolean(body, box("switch_well", *sw["x"], *sw["y"], L.HEIGHT - 3.0, L.HEIGHT + 5.0, m["deep"]))
    s = L.SLOT
    boolean(body, box("slot", HALF - 80.0, HALF + 20.0, *s["y"], *s["z"], m["deep"]))
    parts = [body]
    for sx in (-1, 1):                                    # the corner posts, standing out of the set-in ends
        for y0, y1 in ((0.0, L.POST), (L.DEPTH - L.POST, L.DEPTH)):
            post = box("post", *sorted((sx * (HALF - t - 1.0), sx * HALF)), y0, y1, 0.0, L.HEIGHT, m["case"])
            bevel(post, 1.2, segments=1, angle=40)
            parts.append(post)
    frame = box("slot_frame", HALF - 2.0, HALF + s["out"], s["y"][0] - s["frame"], s["y"][1] + s["frame"],
                s["z"][0] - s["frame"], s["z"][1] + s["frame"], m["case"])
    bevel(frame, 1.6, segments=2, angle=40)
    boolean(frame, box("opening", HALF - 10.0, HALF + 20.0, *s["y"], *s["z"], m["deep"]))
    parts.append(frame)
    whole = join(parts, "crvision")
    coloured(whole, m["print"], ATLAS, "case")
    paint(whole, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name in ("case", "print"))
    paint(whole, m["deep"], ATLAS.swatch("deep"), lambda c, n, name: name == "deep")
    wood = ATLAS.uv("end", L.PANEL["y"][1] - L.PANEL["y"][0], L.PANEL["z"][1] - L.PANEL["z"][0])
    (py0, py1), (pz0, pz1) = L.PANEL["y"], L.PANEL["z"]
    for sx in (-1, 1):
        panel = box("panel", *sorted((sx * (HALF - t - 0.5), sx * (HALF - 0.4))), py0, py1, pz0, pz1, m["wood"])
        paint(panel, m["wood"], ATLAS.swatch("case"), lambda c, n, name: True)
        paint(panel, m["wood"], (lambda co: wood(co.y - py0, pz1 - co.z)) if sx > 0 else
              (lambda co: wood(py1 - co.y, pz1 - co.z)), lambda c, n, name: n.x * sx > 0.9)
        whole = join([whole, panel], "crvision")
    return whole


def reset(m):
    r = L.RESET
    key = box("reset", *r["x"], *r["y"], L.HEIGHT - 1.0, L.HEIGHT + r["height"], m["print"])
    bevel(key, 0.6, segments=1, angle=40)
    return coloured(key, m["print"], ATLAS, "black")


def switch(m):
    """The OFF/ON slide's knob, at OFF (the left of its well), its middle at its origin."""
    kw, kd, kh = L.SWITCH["knob"]
    knob = box("switch", -kw / 2, kw / 2, -kd / 2, kd / 2, -2.0, kh, m["print"])
    bevel(knob, 0.6, segments=1, angle=40)
    coloured(knob, m["print"], ATLAS, "ring")
    sw = L.SWITCH
    return knob, Vector((sw["x"][0] + kw / 2 + 1.0, sum(sw["y"]) / 2, L.HEIGHT - 1.0))


# ---- The controllers -------------------------------------------------------------------------------------------------

def pad_x(name):
    """A controller's middle's x, docked in its tray."""
    length = L.PAD["size"][0]
    d = L.TRAYS["divider"]
    return -d / 2 - 1.0 - length / 2 if name == "left" else d / 2 + 1.0 + length / 2


def controller(name, m):
    """A controller, its middle's foot at its origin: the slab, the keypad's frame raised round its window, the
    joystick's well; its top printed."""
    length, w, h = L.PAD["size"]
    slab = prism("pad_" + name, rounded(0.0, 0.0, length, w, 4.0, 3), 0.0, h, m["print"])
    bevel(slab, 1.4, segments=2, angle=40)
    left = name == "left"
    well = L.PAD["well"]
    jx = -length / 2 + well["u"] if left else length / 2 - well["u"]
    boolean(slab, prism("well", circle(jx, 0.0, well["r"], 28), h - 4.0, h + 5.0, m["print"]))
    a, b, inset = L.PAD["window"]
    x0, x1 = (length / 2 - b, length / 2 - a) if left else (-length / 2 + a, -length / 2 + b)
    frame = prism("frame", rounded((x0 + x1) / 2, 0.0, x1 - x0 + 3.0, w - 2 * inset + 3.0, 2.0, 2), h - 1.0, h + 1.5,
                  m["print"])
    boolean(frame, box("window", x0, x1, -w / 2 + inset, w / 2 - inset, h - 5.0, h + 5.0, m["print"]))
    part = join([slab, frame], "pad_" + name)
    coloured(part, m["print"], ATLAS, "case")
    face = ATLAS.uv(name, length, w)
    paint(part, m["print"], lambda co: face(co.x + length / 2, w / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    return smoothed(part, 35.0), Vector((jx, 0.0, h - 4.0))


def knob(m):
    """The joystick's knob, its foot at its origin: the black stem and cap, the knurled ring round its top."""
    r, h = L.PAD["knob"]
    stem = solid("knob", [[(r * f * math.cos(2 * math.pi * k / 24), r * f * math.sin(2 * math.pi * k / 24), z)
                           for k in range(24)] for z, f in ((0.0, 0.55), (h * 0.5, 0.6), (h * 0.62, 1.0), (h, 0.92))],
                 m["print"])
    coloured(stem, m["print"], ATLAS, "knob")
    paint(stem, m["print"], ATLAS.swatch("ring"), lambda c, n, kind: c.z > h * 0.55 and abs(n.z) < 0.8)
    return smoothed(stem, 40.0)


def cartridge(m):
    """The cartridge, its inner end at its origin's x, lying flat, its label up (its outer end to the right)."""
    length, w, t = L.CART["size"]
    part = box("cartridge", 0.0, length, -w / 2, w / 2, -t / 2, t / 2, m["print"])
    bevel(part, 1.4, segments=2, angle=40)
    coloured(part, m["print"], ATLAS, "cart")
    lw, lh = length - 14.0, w - 8.0
    face = ATLAS.uv("cart", lw, lh)
    paint(part, m["print"], lambda co: face(co.x - 12.0, lh / 2 - co.y),
          lambda c, n, kind: n.z > 0.9 and 12.0 < c.x < 12.0 + lw and abs(c.y) < lh / 2)
    return smoothed(part, 40.0)


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 92.0                   # how far right of its seat the cartridge appears


def timeline(f):
    if f < 6 or f >= 220:
        cart = Pose(x=OUT, scale=HIDDEN)
    elif f < 16:
        cart = Pose(x=OUT, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 15)))
    elif f < 196:
        cart = Pose(x=OUT * (1 - smooth(phase(f, 16, 32))))
    elif f < 210:
        cart = Pose(x=OUT * smooth(phase(f, 196, 210)))
    else:
        cart = Pose(x=OUT, scale=max(HIDDEN, 1 - ease_in(phase(f, 210, 220))))
    on = smooth(phase(f, 40, 46)) * (1 - smooth(phase(f, 186, 192)))
    poses = {"cartridge": cart, "switch": Pose(x=L.SWITCH["travel"] * on)}
    up = smooth(phase(f, 56, 72)) * (1 - smooth(phase(f, 162, 178)))
    poses["pad_right"] = Pose(y=-18.0 * up, z=46.0 * up + wobble(f, 178, -2.0, 7.0, 3.0), pitch=34.0 * up,
                              roll=-6.0 * up)
    t = phase(f, 76, 158)
    wave = math.sin(math.pi * t)
    poses["knob"] = Pose(pitch=20.0 * math.sin(2 * math.pi * 4 * t) * wave, roll=22.0 * math.sin(2 * math.pi * 3 * t
                                                                                                 + 0.9) * wave)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "crvision_print.png"))
    m = materials(dict(print="#FFFFFF", case=L.COLOURS["case"], wood="#FFFFFF", deep=L.COLOURS["deep"]), ROUGHNESS,
                  dict(print=printed, wood=printed))

    left, left_well = controller("left", m)
    left.data.transform(Matrix.Translation((pad_x("left"), L.PAD["y"], L.TRAYS["floor"])))
    fixed_knob = knob(m)
    fixed_knob.data.transform(Matrix.Translation(Vector((pad_x("left"), L.PAD["y"], L.TRAYS["floor"])) + left_well))
    whole = smoothed(join([console(m), reset(m), left, fixed_knob], "crvision"), 35.0)
    right, right_well = controller("right", m)
    knob_, knob_at = switch(m)
    s = L.SLOT
    seat_x = HALF + L.CART["out"] - L.CART["size"][0]
    parts = {"cartridge": (cartridge(m), Vector((seat_x, sum(s["y"]) / 2, sum(s["z"]) / 2))),
             "switch": (knob_, knob_at),
             "pad_right": (right, Vector((pad_x("right"), L.PAD["y"], L.TRAYS["floor"]))),
             "knob": (knob(m), right_well, "pad_right")}
    finish("crvision", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "CreatiVision")


if __name__ == "__main__":
    main()
