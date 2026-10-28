"""The console theme's Game Boy and Game Boy Color system models (godot/themes/console/models/systems/gb.glb and
gbc.glb), standing up.

Built in Blender with handheld.py's pieces (game_boy_layout.py has the measurements, from photographs): the shell from
the face's outline (the DMG's big bottom right corner, the Color's bowed bottom edge), its edges rounded; the lens set
into a recess in the face, its whole front the card's screen; the D-pad, B and A standing out of the face, SELECT and
START (the DMG's slanting); the DMG's speaker slots cut into the face; the power switch on the top, the wheels
standing out of the ends; on the back the cartridge's open bay at the top, and the DMG's label panel and battery cover
or the Color's batteries' bulge. The printing is two textures drawn by game_boy_print.py (the shell's: its face, back,
ends, top and bottom, the D-pad's top, the Color's buttons' letters, swatches; and the cartridge's two sides).

The lens's material is `video`: while the card is focused, the launcher plays the theme's video for it there
(godot/themes/console/videos/gb.mp4 and gbc.mp4, drawn by game_boy_video.py), starting it again each time the clip
loops (A6 Card videos); otherwise it shows its own texture, the lens switched off. So the power light, the start-up,
the game and the picture fading are all the video's, under the lens, frame for frame with the clip.

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting in its seat, shrunk to
nothing), the power switch, the D-pad, B, A and START.

The `focused` clip (10 s, looping; its timing is game_boy_layout.py's, which the video follows) plays a game: the
cartridge (a made-up game) appears above the bay showing its label, turns round and drops into the bay, settling; the
switch slides to ON (the light and the LCD come on in the video); the start-up; the game's title, START pressed; the
game played on the D-pad, A and B as the screen shows it; the switch slides OFF, and the cartridge rises out and goes.

Four materials (case, gloss, cart, video) and three textures, within the system model budget. Run from the repo root:

    python tools/console-models/game_boy_print.py artifacts/made-up-games artifacts/gameboys
    python tools/console-models/game_boy_video.py artifacts/made-up-games gb godot/themes/console/videos/gb.mp4
    blender -b --factory-startup --python tools/console-models/game_boy.py -- artifacts/gameboys gb godot/themes/console/models/systems/gb.glb

and the same with gbc.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_boy_layout as L  # noqa: E402
import handheld as H  # noqa: E402
from amiga import paint  # noqa: E402
from card import finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_in, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: its right end comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = {"gb": dict(case=0.55, gloss=0.3, cart=0.5, video=0.25),
             "gbc": dict(case=0.42, gloss=0.3, cart=0.42, video=0.22)}
HOVER = 4.0          # how far above the console's top the cartridge's bottom hovers, millimetres
PRESS = 1.1          # how far a button goes in
TILT = 6.0           # degrees the D-pad rocks


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(size, region, w, h):
    """A face drawn w x h mm into region (x, y, width, height) of a texture of size (width, height) pixels: (a, b) mm
    across it (a to the right, b down from its top) to UVs."""
    sw, sh = size if isinstance(size, tuple) else (size, size)
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / sw, 1 - (ry + b / h * rh) / sh)


def swatch(name, table=L.SWATCHES, size=L.PRINT_ATLAS):
    sw, sh = size if isinstance(size, tuple) else (size, size)
    x, y = table[name]
    return lambda co: (x / sw, 1 - y / sh)


def flat_caps(obj, area=4.0):
    """Big flat faces square to an axis shade flat, so their long triangles light evenly; the rest stays smooth."""
    for p in obj.data.polygons:
        n = p.normal
        if p.area > area and max(abs(n.x), abs(n.y), abs(n.z)) > 0.999:
            p.use_smooth = False
    return obj


# ---- The shell -------------------------------------------------------------------------------------------------------

def paint_shell(obj, m, mat):
    w, h, d = m["width"], m["height"], m["depth"]
    reg, S = m["print_regions"], L.PRINT_ATLAS
    face = atlas_uv(S, reg["face"], w, h)
    back = atlas_uv(S, reg["back"], w, h)
    right = atlas_uv(S, reg["right"], d, h)
    left = atlas_uv(S, reg["left"], d, h)
    top = atlas_uv(S, reg["top"], w, d)
    bottom = atlas_uv(S, reg["bottom"], w, d)
    lx0, lx1, lz0, lz1 = m["lens"]["rect"]
    deep = d - m.get("bay", {}).get("deep", 0.0) - 0.6
    paint(obj, mat, swatch("case"), lambda c, n, k: True)
    paint(obj, mat, lambda co: face(co.x + w / 2, h - co.z), lambda c, n, k: n.y < -0.9 and c.y < 0.05)
    paint(obj, mat, lambda co: back(w / 2 - co.x, h - co.z), lambda c, n, k: n.y > 0.9 and c.y > deep)
    paint(obj, mat, lambda co: right(co.y, h - co.z), lambda c, n, k: n.x > 0.9 and c.x > w / 2 - 0.05)
    paint(obj, mat, lambda co: left(d - co.y, h - co.z), lambda c, n, k: n.x < -0.9 and c.x < -w / 2 + 0.05)
    paint(obj, mat, lambda co: top(co.x + w / 2, d - co.y), lambda c, n, k: n.z > 0.9 and c.z > h - 0.05)
    paint(obj, mat, lambda co: bottom(co.x + w / 2, co.y), lambda c, n, k: n.z < -0.9 and c.z < 2.0)
    # The lens's recess, round the lens: dark.
    paint(obj, mat, swatch("gap"), lambda c, n, k: 0.05 < c.y < 1.5 and lx0 - 1 < c.x < lx1 + 1 and lz0 - 3 < c.z < lz1 + 1)
    return obj


def shell(kind, m, mats):
    w, h, d = m["width"], m["height"], m["depth"]
    part = H.body(kind, L.body_outline(kind), d, mats["case"], front=m["round"][0], back=m["round"][1])
    lens = m["lens"]
    boolean(part, plate("recess", L.lens_outline(kind, grow=lens["gap"]), -1.0, lens["recess"], mats["case"]))
    (bx0, bx1), bz0 = m["bay"]["x"], m["bay"]["z0"]
    boolean(part, box("bay", bx0, bx1, d - m["bay"]["deep"], d + 5.0, bz0, h + 5.0, mats["case"]))
    if kind == "gb":
        s = m["speaker"]
        cutters = [plate("slot", H.stadium(s["first"][0] + s["step"][0] * k, s["first"][1] + s["step"][1] * k,
                                           s["length"], s["width"], s["slant"], n=4), -1.0, s["deep"], mats["case"])
                   for k in range(s["count"])]
        boolean(part, join(cutters, "slots"))
    paint_shell(part, m, mats["case"])
    if kind == "gb":
        s = m["speaker"]
        ux, uz = math.cos(math.radians(s["slant"])), math.sin(math.radians(s["slant"]))

        def in_slot(c):
            for k in range(s["count"]):
                dx, dz = c.x - s["first"][0] - s["step"][0] * k, c.z - s["first"][1] - s["step"][1] * k
                if abs(dx * ux + dz * uz) <= s["length"] / 2 + 0.3 and abs(dz * ux - dx * uz) <= s["width"] / 2 + 0.3:
                    return True
            return False
        paint(part, mats["case"], swatch("slot"), lambda c, n, k: 0.05 < c.y < s["deep"] + 0.5 and in_slot(c))
    return part


def back_plates(kind, m, mats):
    """What stands off the back: the DMG's label panel, battery cover and its latch; the Color's batteries' bulge."""
    d = m["depth"]
    out = []
    if kind == "gb":
        for rect, r, depth in ((m["panel"]["rect"], 1.5, m["panel"]["out"]), (m["cover"]["rect"], 1.2, m["cover"]["out"]),
                               (m["cover"]["tab"], 0.8, m["cover"]["out"])):
            x0, x1, z0, z1 = rect
            part = plate("plate", L.rounded_rect(x0, x1, z0, z1, (r, r, r, r), n=4), d - 0.4, d + depth, mats["case"])
            bevel(part, 0.3, segments=1)
            out.append(part)
    else:
        x0, x1, z0, z1 = m["bulge"]["rect"]
        r = m["bulge"]["r"]
        part = plate("bulge", L.rounded_rect(x0, x1, z0, z1, (r, r, r, r), n=6), d - 1.0, d + m["bulge"]["out"],
                     mats["case"])
        bevel(part, 1.4, segments=3)
        out.append(part)
    return out


def lens_part(kind, m, mats):
    lens = m["lens"]
    x0, x1, z0, z1 = lens["rect"]
    part = plate("lens", L.lens_outline(kind), lens["front"], lens["recess"] - 0.05, mats["case"])
    paint(part, mats["case"], swatch("lens"), lambda c, n, k: True)
    paint(part, mats["video"], lambda co: ((co.x - x0) / (x1 - x0), (co.z - z0) / (z1 - z0)),
          lambda c, n, k: n.y < -0.9)
    return part


def wheels(m, mats):
    w = m["width"]
    out = []
    for wh in m["wheels"]:
        r, n = wh["r"], 48
        teeth = [(r - (0.0 if k % 2 == 0 else 0.35)) for k in range(n)]
        cx = wh["side"] * (w / 2 - r + wh["out"])
        outline = [(cx + teeth[k] * math.cos(2 * math.pi * k / n), wh["z"] + teeth[k] * math.sin(2 * math.pi * k / n))
                   for k in range(n)]
        part = plate("wheel", outline, wh["y"][0], wh["y"][1], mats["case"])
        paint(part, mats["case"], swatch("wheel"), lambda c, n, k: True)
        out.append(part)
    return out


# ---- The controls ----------------------------------------------------------------------------------------------------

def dpad(kind, m, mats):
    d = m["dpad"]
    a, half = d["arm"] / 2, d["width"] / 2
    part = plate("dpad", H.cross(0.0, 0.0, a, half), -d["out"], 1.0, mats["gloss"])
    bevel(part, 0.7, segments=2, angle=50)
    uv = atlas_uv(L.PRINT_ATLAS, m["print_regions"]["dpad"], 2 * a, 2 * a)
    paint(part, mats["gloss"], swatch("dark"), lambda c, n, k: True)
    paint(part, mats["gloss"], lambda co: uv(co.x + a, a - co.z), lambda c, n, k: n.y < -0.9)
    return smoothed(part, 50.0)


def button(kind, m, mats, name):
    b = m["buttons"]
    r, h = b["r"], b["out"]
    profile = [(0.0, -1.5), (r, -1.5), (r, h * 0.55)] + [(r * math.cos(math.pi / 2 * k / 5),
                                                          h * 0.55 + h * 0.45 * math.sin(math.pi / 2 * k / 5))
                                                         for k in range(1, 6)]
    part = lathe(name, profile, mats["gloss"], 28)
    part.data.transform(Matrix.Rotation(math.radians(90.0), 4, "X"))
    paint(part, mats["gloss"], swatch("ab"), lambda c, n, k: True)
    if kind == "gbc":
        uv = atlas_uv(L.PRINT_ATLAS, m["print_regions"]["btn_" + name[-1]], 2 * r, 2 * r)
        paint(part, mats["gloss"], lambda co: uv(co.x + r, r - co.z), lambda c, n, k: n.y < -0.6)
    return flat_caps(smoothed(part, 50.0), area=1.0)


def pill(kind, m, mats, name):
    p = m["pills"]
    length, width = p["size"]
    part = plate(name, H.stadium(0.0, 0.0, length, width, p["slant"], n=8), -p["out"], 0.8, mats["case"])
    bevel(part, min(0.6, width / 4), segments=2, angle=50)
    paint(part, mats["case"], swatch("rubber"), lambda c, n, k: True)
    return smoothed(part, 50.0)


def switch(m, mats):
    s = m["switch"]
    sw, sh = s["size"]
    y0, y1 = s["y"]
    part = box("switch", -sw / 2, sw / 2, y0, y1, -1.0, sh, mats["case"])
    bevel(part, 0.6, segments=2)
    paint(part, mats["case"], swatch("case"), lambda c, n, k: True)
    return smoothed(part, 40.0)


def cartridge(m, mats):
    """The cartridge, its bottom edge's middle at its origin, its label towards +y (the console's back)."""
    w, hh, t = m["cart"]["size"]
    part = plate("cartridge", L.cart_outline((w, hh, t)), -t / 2, t / 2, mats["cart"])
    bevel(part, 0.5, segments=2)
    size = L.CART_ATLAS
    label = atlas_uv(size, L.CART_REGIONS["label"], w, hh)
    front = atlas_uv(size, L.CART_REGIONS["front"], w, hh)
    paint(part, mats["cart"], swatch("edge", L.CART_SWATCHES, size), lambda c, n, k: True)
    paint(part, mats["cart"], lambda co: label(w / 2 - co.x, hh - co.z), lambda c, n, k: n.y > 0.9)
    paint(part, mats["cart"], lambda co: front(co.x + w / 2, hh - co.z), lambda c, n, k: n.y < -0.9)
    return flat_caps(smoothed(part, 40.0))


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def held(f, f0, frames):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + frames, f0 + frames + 2)))


def timeline(kind, m):
    T, mv = L.TIMING[kind], L.MOVES[kind]
    hh = m["cart"]["size"][1]
    lift = hh - m["cart"]["protrudes"] + HOVER       # from the seat to hovering just above the top
    travel = m["switch"]["travel"]
    play = T["play"]

    def directions(f, name):
        return sum(held(f, play + f0, n) for f0, n in mv.get(name, []))

    def poses(f):
        a0, a1 = T["appear"]
        if f < a0 or f >= T["gone"][1]:
            cart = Pose(scale=HIDDEN)                     # in its seat, so the rest pose's bounds are the console's
        elif f < T["drop"][0]:
            # Grown in above the bay, its label towards the viewer, bobbing; then turned round to go in.
            grow = HIDDEN + (1 - HIDDEN) * back_out(phase(f, a0, a1)) if f < a1 else 1.0
            bob = 1.4 * math.sin(2 * math.pi * (f - a0) / 28) * (1 - phase(f, T["turn"][0] - 8, T["turn"][0]))
            cart = Pose(z=lift + bob, spin=180.0 * (1 - smooth(phase(f, *T["turn"]))), scale=grow)
        elif f < T["out"][0]:
            settle = 0.0
            if f >= T["drop"][1]:
                t = f - T["drop"][1]
                settle = 1.0 * math.exp(-t / 3.0) * abs(math.sin(math.pi * t / 4.0))
            cart = Pose(z=lift * (1 - ease_in(phase(f, *T["drop"]))) + settle)
        else:
            g = phase(f, *T["gone"])
            cart = Pose(z=lift * ease_out(phase(f, *T["out"])) + 10.0 * g, scale=max(HIDDEN, 1 - back_in(g)))
        on = smooth(phase(f, *T["switch_on"])) * (1 - smooth(phase(f, *T["switch_off"])))
        spin = TILT * (directions(f, "right") - directions(f, "left"))
        pitch = TILT * (directions(f, "down") - directions(f, "up"))
        return {"cartridge": cart, "switch": Pose(x=travel * on), "dpad": Pose(spin=spin, pitch=pitch),
                "start": Pose(y=PRESS * tap(f, T["start"], 3)),
                "button_a": Pose(y=PRESS * max([tap(f, play + f0) for f0 in mv["a"]] + [0.0])),
                "button_b": Pose(y=PRESS * max([tap(f, play + f0) for f0 in mv["b"]] + [0.0]))}
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, kind, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    m = L.MODELS[kind]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    load = lambda name: bpy.data.images.load(os.path.join(images, f"{kind}_{name}.png"))
    printed = load("print")
    mats = materials(dict(case="#FFFFFF", gloss="#FFFFFF", cart="#FFFFFF", video="#FFFFFF"), ROUGHNESS[kind],
                     dict(case=printed, gloss=printed, cart=load("cart"), video=load("screen")))

    w, h, d = m["width"], m["height"], m["depth"]
    p = m["pills"]
    select = pill(kind, m, mats, "select")
    select.data.transform(Matrix.Translation((p["select"][0], 0.0, p["select"][1])))
    parts_of_set = [shell(kind, m, mats), lens_part(kind, m, mats), select] + back_plates(kind, m, mats) + wheels(m, mats)
    for part in parts_of_set[3:]:
        if part.name.startswith(("plate", "bulge")):
            paint_shell(part, m, mats["case"])
    whole = flat_caps(smoothed(join(parts_of_set, kind), 40.0))

    s = m["switch"]
    hh, t = m["cart"]["size"][1], m["cart"]["size"][2]
    seat = Vector((0.0, d - m["cart"]["back"] - t / 2, h + m["cart"]["protrudes"] - hh))
    b = m["buttons"]
    parts = {"cartridge": (cartridge(m, mats), seat),
             "switch": (switch(m, mats), Vector((s["x"], 0.0, h))),
             "dpad": (dpad(kind, m, mats), Vector((m["dpad"]["at"][0], 0.0, m["dpad"]["at"][1]))),
             "button_b": (button(kind, m, mats, "button_b"), Vector((b["b"][0], 0.0, b["b"][1]))),
             "button_a": (button(kind, m, mats, "button_a"), Vector((b["a"][0], 0.0, b["a"][1]))),
             "start": (pill(kind, m, mats, "start"), Vector((p["start"][0], 0.0, p["start"][1])))}
    finish(kind, whole, parts, timeline(kind, m), L.LENGTH, TILT_YAW, TILT_PITCH, out, m["name"])


if __name__ == "__main__":
    main()
