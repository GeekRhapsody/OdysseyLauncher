"""The console theme's device cards (godot/themes/console/models/systems/<card>.glb): for systems with no hardware of
their own, a device that stands for them (devices_layout.py).

Built in Blender from devices_layout.py's measurements, each card from its own function here (CARDS), with the
screens and printing devices_print.py draws (one image a card):
- `tic80`: TIC-80's mascot made solid in its pixels; the `focused` clip blinks, drops a cartridge into its top, plays
  a made-up game on its face, pops the cartridge out and hops.
- `wasm4`: WASM-4's emblem made a handheld; the clip picks it up, presses its d-pad and buttons, turns it round to the
  game on its screen, turns it back and puts it down.
- `lowresnx`: LowRes NX's handheld; the clip types RUN, slides the screen down over the keyboard and plays a made-up
  game, then slides it back up.
- `vircon32`: Vircon32's console and gamepad; the clip lifts the cartridge out, turns it round to show its label and
  drops it back in, lights the power light, plays on the pad and slides a memory card in, and later out.
- `fpinball`: a pinball machine; the clip pulls the plunger and plays a ball through the bumpers and off a flipper
  until it drains, the backglass's lamps chasing.
- `vpinball`: a corner of a playfield, its chrome ball engraved with an X; the clip flips the ball off the bumper and
  back and catches it on the left flipper, its X to the front again.
- `zmachine`: a 1980s terminal and a brass lantern; the clip types LIGHT LAMP, lights the lantern and plays a made-up
  text adventure, then the lantern goes out.
- `steam`: a Steam Deck; the clip picks it up, wakes it with STEAM, launches a made-up game from its library and plays
  it on the sticks and a trackpad, then sleeps it and puts it down.

A node tree: a root (the turn to a three-quarter view and the model spec's fit, as emblems.py's) holding the card's
parts, each moving part its own node. Plain materials and the card's image, within the system model budget. Run from
the repo root:

    python tools/console-models/devices_print.py <card> artifacts/made-up-games artifacts/devices
    blender -b --factory-startup --python tools/console-models/devices.py -- artifacts/devices <card> godot/themes/console/models/systems/<card>.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import devices_layout as L  # noqa: E402
import emblems_layout as E  # noqa: E402
from amiga import curved, paint, rounded  # noqa: E402
from clip import HIDDEN, Pose, bump, ease_in, ease_out, hop, key, phase, smooth, wobble  # noqa: E402
from emblems import TILT_PITCH, TILT_YAW, about, ball, one_tone, plate, star, two_tone  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import bevel, box, export, join, material, prism_x, triangles  # noqa: E402
from props import lathe, smooth_shaded, tube  # noqa: E402

CARD = {}                    # the card being built: its id


def media_uv(name):
    """UVs for a screen or label: a across from its left, b down from its top (0 to 1), into the card's region."""
    x, y, w, h = L.REGIONS[CARD["id"]][name]
    size = L.MEDIA_SIZE
    return lambda a, b: ((x + a * w) / size, 1 - (y + b * h) / size)


def screen(name, w, h, region, m, bulge=0.0, at=(0.0, 0.0, 0.0), turn=None):
    """A screen (or a label), w x h, facing the viewer, its middle at `at` (turned by `turn` first)."""
    part = curved(name, w, h, bulge, media_uv(region), m["media"], 8, 6)
    if turn is not None:
        part.data.transform(turn)
    part.data.transform(Matrix.Translation(at))
    return part


def layered(names, w, h, m, at, turn=None, step=0.3, bulge=0.0):
    """Screens stacked in front of a base screen, each a node shrunk to nothing until it's shown; the later in
    front."""
    out = {}
    for k, name in enumerate(names):
        a = Vector(at) + (turn.to_3x3() if turn else Matrix.Identity(3)) @ Vector((0.0, -step * (k + 1), 0.0))
        part = screen("screen_" + name, w, h, name, m, bulge, (0.0, 0.0, 0.0), turn)
        part.location = a
        out["screen_" + name] = (part, None)
    return out


def showing_poses(names, showing, f):
    """The screens' poses: the one showing, and the one before it a frame longer, so a swap never shows the base."""
    on = (showing(f), showing(f - 1))
    return {"screen_" + n: Pose() if n in on else Pose(scale=HIDDEN) for n in names}


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def taps(f, frames, hold=2):
    return max(tap(f, f0, hold) for f0 in frames)


def recolour(obj, mat):
    return one_tone(obj, mat)


# ---- TIC-80 ----------------------------------------------------------------------------------------------------------

def tic80(m):
    p, rows = L.TIC80_PIXEL, L.TIC80
    depth = L.TIC80_DEPTH * p
    width = len(rows[0]) * p
    blocks = []
    for r, row in enumerate(rows):
        z0 = (len(rows) - 1 - r) * p
        x = 0
        while x < len(row):
            ch, x1 = row[x], x
            while x1 < len(row) and row[x1] == ch:
                x1 += 1
            if ch != ".":
                y0, y1 = {"W": (-2.0, depth), "S": (depth * 0.3, depth * 0.7)}.get(ch, (0.0, depth))
                mat = m[{"F": "B", "S": "D"}.get(ch, ch)]
                blocks.append(recolour(box(f"px{r}_{x}", x * p - width / 2, x1 * p - width / 2, y0, y1, z0, z0 + p,
                                           mat), mat))
            x = x1
    top = len(rows) * p
    blocks.append(recolour(box("slot", -3.5 * p, 3.5 * p, depth * 0.4, depth * 0.6, top, top + 0.6, m["D"]), m["D"]))
    body = join(blocks, "tic80")
    cols = [i for i, ch in enumerate(rows[2]) if ch == "F"]
    face_rows = [r for r, row in enumerate(rows) if "F" in row]
    fw, fh = len(cols) * p, len(face_rows) * p
    fx = (cols[0] + len(cols) / 2) * p - width / 2
    fz = (len(rows) - 1 - face_rows[-1]) * p + fh / 2
    body = join([body, screen("face", fw, fh, "eyes", m, at=(fx, -0.4, fz))], "tic80")
    parts = {"tic80": (body, None)}
    for name, (part, _) in layered(("blink", "game1", "game2"), fw, fh, m, (fx, -0.4, fz)).items():
        parts[name] = (part, "tic80")
    cart = recolour(box("cart", -3.0 * p, 3.0 * p, -p / 2, p / 2, 0.0, 6.0 * p, m["cart"]), m["cart"])
    cart = join([cart, screen("label", 5.4 * p, 4.5 * p, "label", m, at=(0.0, -p / 2 - 0.3, 3.4 * p))], "cart")
    cart.location = (0.0, depth / 2, top)
    parts["cart"] = (cart, None)
    return parts, [], tic80_timeline, 150


def tic80_showing(f):
    if 46 <= f < 52:
        return "game1" if (f // 2) % 2 == 0 else None
    if 52 <= f < 112:
        return "game1" if ((f - 52) // 8) % 2 == 0 else "game2"
    if 10 <= f < 14 or 136 <= f < 140:
        return "blink"
    return None


def tic80_timeline(f):
    poses = showing_poses(("blink", "game1", "game2"), tic80_showing, f)
    p = L.TIC80_PIXEL
    appear = back_in_out(f)
    if f < 22 or f >= 128:
        poses["cart"] = Pose(scale=HIDDEN)
    elif f < 34:
        poses["cart"] = Pose(z=3 * p, scale=HIDDEN + (1 - HIDDEN) * appear)
    elif f < 112:
        poses["cart"] = Pose(z=3 * p - 6 * p * ease_in(phase(f, 34, 44)))
    else:
        out = ease_out(phase(f, 112, 118))
        poses["cart"] = Pose(z=-3 * p + 5 * p * out, scale=1.0 - (1 - HIDDEN) * smooth(phase(f, 120, 128)))
    poses["tic80"] = Pose(z=hop(f, 132, 146, 40.0), squash=wobble(f, 44, 0.06, 7.0, 4.0) + wobble(f, 146, 0.1, 7.0,
                                                                                                    4.0))
    return poses


def back_in_out(f):
    t = phase(f, 22, 32)
    return 1 + (t - 1) ** 2 * (3.2 * (t - 1) + 2.2)


# ---- WASM-4 ----------------------------------------------------------------------------------------------------------

def wasm4(m):
    w = L.WASM4
    s, d, r = w["size"], w["depth"], w["notch"]
    outline = ([(-s / 2, 0.0), (s / 2, 0.0), (s / 2, s), (r, s)] + E.arc(0.0, s, r, 0.0, -180.0, 16)[1:-1]
               + [(-r, s), (-s / 2, s)])
    slab = plate("wasm4", E.ccw(outline), -d / 2, d / 2, m["body"])
    bevel(slab, w["round"], segments=2, angle=30.0)
    two_tone(slab, m["body"], m["side"])
    sc = w["screen"]
    bezel = recolour(plate("bezel", rounded(sc["at"][0], sc["at"][1], sc["bezel"], sc["bezel"], 5.0, 3), d / 2 - 0.5,
                           d / 2 + 1.0, m["bezel"]), m["bezel"])
    back = Matrix.Rotation(math.pi, 4, "Z")
    glass = screen("glass", sc["size"], sc["size"], "title", m, at=(0.0, d / 2 + 1.3, sc["at"][1]), turn=back)
    body = join([slab, bezel, glass], "wasm4")
    parts = {"wasm4": (body, None)}
    for name, (part, _) in layered(("game1", "game2"), sc["size"], sc["size"], m, (0.0, d / 2 + 1.3, sc["at"][1]),
                                   turn=back).items():
        parts[name] = (part, "wasm4")
    (dx, dz), arm, wd = w["dpad"]["at"], w["dpad"]["arm"], w["dpad"]["width"] / 2
    plus = [(dx - wd, dz - arm), (dx + wd, dz - arm), (dx + wd, dz - wd), (dx + arm, dz - wd), (dx + arm, dz + wd),
            (dx + wd, dz + wd), (dx + wd, dz + arm), (dx - wd, dz + arm), (dx - wd, dz + wd), (dx - arm, dz + wd),
            (dx - arm, dz - wd), (dx - wd, dz - wd)]
    dpad = plate("dpad", E.ccw(plus), -d / 2 - 3.0, -d / 2 + 1.0, m["controls"])
    bevel(dpad, 0.8, segments=1, angle=30.0)
    parts["dpad"] = (about(recolour(dpad, m["controls"]), (dx, -d / 2, dz)), "wasm4")
    for k, (bx, bz) in enumerate(w["buttons"]):
        button = plate(f"button{k}", E.circle(bx, bz, w["button_r"], 28), -d / 2 - 3.0, -d / 2 + 1.0, m["controls"])
        bevel(button, 0.8, segments=1, angle=30.0)
        parts[f"button{k}"] = (about(recolour(button, m["controls"]), (bx, -d / 2, bz)), "wasm4")
    return parts, [], wasm4_timeline, 150


def wasm4_showing(f):
    if 70 <= f < 128:
        return "game1" if ((f - 70) // 8) % 2 == 0 else "game2"
    return None


def wasm4_timeline(f):
    poses = showing_poses(("game1", "game2"), wasm4_showing, f)
    up = smooth(phase(f, 6, 22)) * (1 - smooth(phase(f, 134, 148)))
    turn = 180.0 * smooth(phase(f, 60, 76)) + 180.0 * smooth(phase(f, 118, 134))
    poses["wasm4"] = Pose(z=30.0 * up, pitch=-16.0 * up, spin=turn, squash=wobble(f, 148, 0.08, 7.0, 4.0))
    press = 2.5
    poses["dpad"] = Pose(y=press * taps(f, (26, 36, 46)), roll=6.0 * tap(f, 36) - 6.0 * tap(f, 46))
    poses["button0"] = Pose(y=press * taps(f, (30, 42, 52)))
    poses["button1"] = Pose(y=press * taps(f, (34, 48)))
    return poses


# ---- LowRes NX -------------------------------------------------------------------------------------------------------

def lowresnx(m):
    lw = L.LOWRES
    w, h, d = lw["width"], lw["height"], lw["depth"]
    body = plate("body", rounded(0.0, h / 2, w, h, lw["grip"], 10), -d / 2, d / 2, m["body"])
    bevel(body, 4.0, segments=2, angle=30.0)
    recolour(body, m["body"])
    cw, ch = lw["column"]
    column = recolour(box("column", -cw / 2, cw / 2, -d / 2 - 1.5, -d / 2 + 1.0, 3.0, 3.0 + ch, m["dark"]), m["dark"])
    nx, nz = lw["keys"]
    keys, pressed = [], {}
    kw, kh, gap = 9.0, 12.0, 2.5
    x0 = -(nx * kw + (nx - 1) * gap) / 2
    for j in range(nz):
        for i in range(nx):
            kx, kz = x0 + i * (kw + gap), 10.0 + j * 18.0
            key_box = recolour(box(f"key{i}_{j}", kx, kx + kw, -d / 2 - 4.0, -d / 2 - 1.0, kz, kz + kh, m["key"]),
                               m["key"])
            if (i, j) in PRESSED_KEYS:
                pressed[PRESSED_KEYS[(i, j)]] = about(key_box, (kx + kw / 2, -d / 2 - 1.0, kz + kh / 2))
            else:
                keys.append(key_box)
    dx, dz = lw["dpad"]
    base = recolour(plate("dpad_base", E.circle(dx, dz, 14.0, 28), -d / 2 - 1.5, -d / 2 + 1.0, m["dark"]), m["dark"])
    plus = [(dx + px, dz + pz) for px, pz in E.turned(E.ccw([(-3.5, -11.0), (3.5, -11.0), (3.5, -3.5), (11.0, -3.5),
                                                            (11.0, 3.5), (3.5, 3.5), (3.5, 11.0), (-3.5, 11.0),
                                                            (-3.5, 3.5), (-11.0, 3.5), (-11.0, -3.5),
                                                            (-3.5, -3.5)]), 0.0)]
    dpad = recolour(plate("dpad", plus, -d / 2 - 4.0, -d / 2 - 1.0, m["button"]), m["button"])
    buttons = {}
    for k, (bx, bz) in enumerate(lw["buttons"]):
        b = recolour(plate(f"button{k}", E.circle(bx, bz, 6.0, 20), -d / 2 - 4.0, -d / 2 + 1.0, m["button"]),
                     m["button"])
        buttons[f"button{k}"] = about(b, (bx, -d / 2, bz))
    tx, tz = lw["teal"]
    teal = recolour(plate("teal", E.circle(tx, tz, 4.5, 20), -d / 2 - 3.0, -d / 2 + 1.0, m["teal"]), m["teal"])
    whole = join([body, column, base, teal] + keys, "lowresnx")
    pn = lw["panel"]
    panel = plate("panel", rounded(0.0, pn["z"] + pn["height"] / 2, pn["width"], pn["height"], 5.0, 4),
                  -d / 2 - 5.0 - pn["depth"], -d / 2 - 5.0, m["dark"])
    bevel(panel, 2.0, segments=2, angle=30.0)
    recolour(panel, m["dark"])
    sw, sh = lw["screen"]
    sz = pn["z"] + pn["height"] / 2 + 2.0
    sy = -d / 2 - 5.0 - pn["depth"] - 0.4
    panel = join([panel, screen("glass", sw, sh, "ready", m, at=(0.0, sy, sz))], "panel")
    parts = {"lowresnx": (whole, None), "panel": (about(panel, (0.0, sy, pn["z"])), None),
             "dpad": (about(dpad, (dx, -d / 2 - 1.0, dz)), None)}
    for name, (part, _) in layered(("run", "game1", "game2"), sw, sh, m, (0.0, sy, sz)).items():
        parts[name] = (part, "panel")
    for name, part in list(buttons.items()) + [(n, p) for n, p in pressed.items()]:
        parts[name] = (part, None)
    return parts, [], lowresnx_timeline, 180


PRESSED_KEYS = {(3, 2): "key_r", (4, 1): "key_u", (2, 0): "key_n", (5, 0): "key_return"}


def lowresnx_showing(f):
    if 30 <= f < 52:
        return "run"
    if 52 <= f < 136:
        return "game1" if ((f - 52) // 8) % 2 == 0 else "game2"
    return None


def lowresnx_timeline(f):
    poses = showing_poses(("run", "game1", "game2"), lowresnx_showing, f)
    down = smooth(phase(f, 38, 52)) * (1 - smooth(phase(f, 140, 156)))
    poses["panel"] = Pose(z=L.LOWRES["panel"]["slide"] * down)
    for name, f0 in (("key_r", 12), ("key_u", 18), ("key_n", 24), ("key_return", 32)):
        poses[name] = Pose(y=2.0 * tap(f, f0))
    poses["dpad"] = Pose(y=1.5 * taps(f, (64, 80, 104)), roll=8.0 * tap(f, 80) - 8.0 * tap(f, 104))
    poses["button0"] = Pose(y=2.0 * taps(f, (72, 92, 118)))
    poses["button1"] = Pose(y=2.0 * taps(f, (86, 112)))
    return poses


# ---- Vircon32 --------------------------------------------------------------------------------------------------------

def vircon32(m):
    v = L.VIRCON
    bw, bd, bh = v["base"]
    base = box("base", -bw / 2, bw / 2, -bd / 2, bd / 2, 0.0, bh, m["body"])
    bevel(base, 8.0, segments=3, angle=30.0)
    recolour(base, m["body"])
    tw, td, th = v["top"]
    top = box("top", -tw / 2, tw / 2, -10.0, -10.0 + td, bh, bh + th, m["inset"])
    bevel(top, 3.0, segments=2, angle=30.0)
    recolour(top, m["inset"])
    cw, cd, ch = v["cart"]
    sy = v["slot_y"]
    slot = recolour(box("slot", -cw / 2 - 2.0, cw / 2 + 2.0, sy - cd / 2 - 2.0, sy + cd / 2 + 2.0, bh + th,
                        bh + th + 0.6, m["dark"]), m["dark"])
    name_print = screen("name", 90.0, 30.0, "top", m, at=(-38.0, -40.0, bh + 0.4),
                        turn=Matrix.Rotation(-math.pi / 2, 4, "X"))
    front = screen("front", 200.0, 24.0, "front", m, at=(0.0, -bd / 2 - 0.4, 22.0))
    power = plate("power", E.circle(-88.0, -52.0, 8.0, 20), -2.0, 2.0, m["red"])
    power.data.transform(Matrix.Translation((0.0, 0.0, bh + 2.0)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    led = recolour(box("led", -73.0, -67.0, -55.0, -49.0, bh, bh + 1.2, m["dark"]), m["dark"])
    console = join([base, top, slot, name_print, front, recolour(power, m["red"]), led], "vircon32")
    lit = recolour(box("led_lit", -73.3, -66.7, -55.3, -48.7, bh, bh + 1.6, m["led"]), m["led"])
    cart = recolour(box("cart", -cw / 2, cw / 2, -cd / 2, cd / 2, 0.0, ch, m["cart"]), m["cart"])
    bevel(cart, 2.0, segments=2, angle=30.0)
    recolour(cart, m["cart"])
    cart = join([cart, screen("label", 75.0, 30.0, "label", m, at=(0.0, -cd / 2 - 0.4, ch - 22.0))], "cart")
    inserted = bh + th - 24.0                            # how deep it stands in the slot
    cart.location = (0.0, sy, inserted)
    card_w, card_d, card_h = v["card"]
    card = recolour(box("card", -card_w / 2, card_w / 2, -card_h, 0.0, -card_d / 2, card_d / 2, m["dark"]), m["dark"])
    card = join([card, screen("card_label", card_w - 4.0, card_h - 6.0, "card", m, at=(0.0, -card_h / 2, card_d / 2 +
                                                                                         0.3),
                              turn=Matrix.Rotation(-math.pi / 2, 4, "X"))], "card")
    card.location = (64.0, -bd / 2 - 6.0, 18.0)
    # The gamepad, lying in front, its cable to P1.
    (px, py), (pw, pd, ph) = v["pad"]["at"], v["pad"]["size"]
    shell = prism_z("pad", rounded(0.0, 0.0, pw, pd, pd / 2, 10), 0.0, ph, m["body"])
    bevel(shell, 5.0, segments=3, angle=30.0)
    recolour(shell, m["body"])
    start = recolour(prism_z("start", rounded(0.0, -8.0, 22.0, 7.0, 3.5, 4), ph - 1.0, ph + 2.0, m["dark"]),
                     m["dark"])
    mint = []
    for k, (bx, by) in enumerate(((42.0, 12.0), (54.0, 0.0), (30.0, 0.0))):
        mint.append(recolour(prism_z(f"b{k}", E.circle(bx, by, 5.0, 18), ph - 1.0, ph + 2.5, m["mint"]), m["mint"]))
    pad = join([shell, start] + mint, "pad")
    plus = E.ccw([(-4.0, -12.0), (4.0, -12.0), (4.0, -4.0), (12.0, -4.0), (12.0, 4.0), (4.0, 4.0), (4.0, 12.0),
                  (-4.0, 12.0), (-4.0, 4.0), (-12.0, 4.0), (-12.0, -4.0), (-4.0, -4.0)])
    dpad = recolour(prism_z("dpad", [(x - 42.0, y) for x, y in plus], ph - 1.0, ph + 2.5, m["dark"]), m["dark"])
    a_button = recolour(prism_z("a", E.circle(42.0, -12.0, 5.0, 18), ph - 1.0, ph + 2.5, m["mint"]), m["mint"])
    place = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(math.radians(12.0), 4, "Z")
    for obj in (pad, dpad, a_button):
        obj.data.transform(place)
    cable = smooth_shaded(tube("cable", [place @ Vector((-30.0, pd / 2, ph / 2)), (px - 60.0, py + 70.0, 4.0),
                                         (-96.0, -bd / 2 - 30.0, 6.0), (-100.0, -bd / 2 - 4.0, 16.0)], 2.6, m["dark"],
                                   8))
    parts = {"cart": (cart, None), "led_lit": (about(lit, (-70.0, -52.0, bh)), None), "card": (card, None),
             "pad_dpad": (about(dpad, place @ Vector((-42.0, 0.0, ph))), None),
             "pad_a": (about(a_button, place @ Vector((42.0, -12.0, ph))), None)}
    return parts, [console, pad, cable], vircon32_timeline, 180


def vircon32_timeline(f):
    up = smooth(phase(f, 8, 26))
    down = ease_in(phase(f, 46, 56))
    lift = 84.0 * up * (1 - down)
    poses = {"cart": Pose(z=lift + wobble(f, 56, -3.0, 7.0, 3.5), spin=360.0 * smooth(phase(f, 26, 44)))}
    lit = 60 <= f < 172
    poses["led_lit"] = Pose() if lit else Pose(scale=HIDDEN)
    poses["pad_dpad"] = Pose(z=-1.5 * taps(f, (64, 76, 88)))
    poses["pad_a"] = Pose(z=-1.5 * taps(f, (70, 82, 100)))
    seen = 112 <= f < 172
    into = smooth(phase(f, 116, 128)) * (1 - smooth(phase(f, 150, 162)))
    poses["card"] = Pose(y=30.0 * into, scale=(1.0 if seen else HIDDEN))
    return poses


# ---- Pinball ---------------------------------------------------------------------------------------------------------

def pinball_frame():
    """The playfield's frame: its origin at its front edge's middle, u across, v up the slope, n out of it."""
    p = L.PINBALL
    slope = math.atan2(p["back"] - p["front"], p["length"])
    inset = 26.0
    return Matrix.Translation((0.0, 40.0, p["front"] - inset + 40.0 * math.tan(slope))) @ \
        Matrix.Rotation(slope, 4, "X"), slope


def fpinball(m):
    p = L.PINBALL
    w, length = p["width"], p["length"]
    profile = [(0.0, p["front"] - p["side_depth"]), (length, p["back"] - p["side_depth"]), (length, p["back"]),
               (0.0, p["front"])]
    cabinet = prism_x("cabinet", profile, -w / 2, w / 2, m["cabinet"])
    bevel(cabinet, 6.0, segments=2, angle=30.0)
    recolour(cabinet, m["cabinet"])
    frame, slope = pinball_frame()
    pw, pl = p["playfield"]
    field = curved("playfield", pw, pl, 0.0, media_uv("playfield"), m["media"], 6, 12)
    field.data.transform(frame @ Matrix.Translation((0.0, pl / 2, 0.0)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    rails = []
    for sign in (-1, 1):
        rail = box("rail", -14.0, 14.0, 0.0, length, -10.0, 12.0, m["trim"])
        rail.data.transform(Matrix.Translation((sign * (w / 2 - 14.0), 0.0, p["front"])) @
                            Matrix.Rotation(slope, 4, "X"))
        rails.append(recolour(rail, m["trim"]))
    lockdown = recolour(box("lockdown", -w / 2, w / 2, -10.0, 30.0, p["front"] - 6.0, p["front"] + 16.0, m["trim"]),
                        m["trim"])
    legs = []
    for x in (-w / 2 + 30.0, w / 2 - 30.0):
        for y, top in ((30.0, p["front"] - p["side_depth"]), (length - 30.0, p["back"] - p["side_depth"])):
            legs.append(recolour(box("leg", x - p["legs"] / 2, x + p["legs"] / 2, y - p["legs"] / 2,
                                     y + p["legs"] / 2, 0.0, top + 20.0, m["trim"]), m["trim"]))
    bb = p["backbox"]
    neck = recolour(box("neck", -w / 2 + 40.0, w / 2 - 40.0, length - 200.0, length, p["back"] - 20.0,
                        p["back"] + 110.0, m["cabinet"]), m["cabinet"])
    head = box("backbox", -bb["width"] / 2, bb["width"] / 2, length - bb["depth"], length, p["back"] + 100.0,
               p["back"] + 100.0 + bb["height"], m["cabinet"])
    bevel(head, 6.0, segments=2, angle=30.0)
    recolour(head, m["cabinet"])
    glass_z = p["back"] + 100.0 + bb["height"] / 2 + 20.0
    glass = screen("backglass", 560.0, 560.0, "backglass", m, at=(0.0, length - bb["depth"] - 0.6, glass_z))
    apron = box("apron", -pw / 2 + 4.0, pw / 2 - 4.0, -4.0, 70.0, 0.0, 30.0, m["cabinet"])
    apron.data.transform(frame)
    recolour(apron, m["cabinet"])
    apron_print = screen("apron_print", pw - 10.0, 26.0, "apron", m)
    apron_print.data.transform(frame @ Matrix.Translation((0.0, -4.6, 15.0)))
    statics = [cabinet, field, lockdown, neck, head, glass, apron, apron_print] + rails + legs
    for k, (u, v) in enumerate(p["bumpers"]):              # the pop bumpers: a base, a cap; a lit cap that flashes
        base = recolour(lathe("bumper", [(p["bumper_r"], 0.0), (p["bumper_r"], 26.0), (8.0, 26.0)], m["bumper"],
                              24), m["bumper"])
        cap = recolour(lathe("cap", [(p["bumper_r"] - 4.0, 26.0), (p["bumper_r"] - 4.0, 40.0), (6.0, 44.0)], m["cap"],
                             24), m["cap"])
        for obj in (base, cap):
            obj.data.transform(frame @ Matrix.Translation((u, v, 0.0)))
            statics.append(obj)
        lit = recolour(lathe("lit", [(p["bumper_r"] - 3.0, 25.0), (p["bumper_r"] - 3.0, 41.0), (6.0, 45.5)],
                             m["lit"], 24), m["lit"])
        lit.data.transform(frame @ Matrix.Translation((u, v, 0.0)))
        parts_lit = about(lit, frame @ Vector((u, v, 30.0)))
        PIN_NODES[f"bumper{k}"] = parts_lit
    for k, sign in enumerate((-1, 1)):                     # the slingshots
        sling = recolour(plate("sling", E.ccw([(sign * 190.0, 330.0), (sign * 190.0, 210.0),
                                               (sign * 130.0, 200.0)]), -30.0, 0.0, m["bumper"]), m["bumper"])
        sling.data.transform(frame @ Matrix.Rotation(-math.pi / 2, 4, "X"))
        statics.append(sling)
    lane = recolour(box("lane", 214.0, 222.0, 0.0, 900.0, 0.0, 28.0, m["trim"]), m["trim"])
    lane.data.transform(frame)
    statics.append(lane)
    parts = {}
    holders = []
    fl, ft = p["flipper"]
    for k, ((u, v), name) in enumerate(zip(p["flippers"], ("flipper_left", "flipper_right"))):
        sign = -1 if k == 0 else 1
        holder = bpy.data.objects.new(name + "_axis", None)
        bpy.context.scene.collection.objects.link(holder)
        holder.location = frame @ Vector((u, v, 0.0))
        holder.rotation_euler = (slope, 0.0, 0.0)
        holders.append(holder)
        shape = flipper_outline(fl, ft, rest=sign * 28.0, side=sign)
        flip = plate(name, shape, -22.0, 0.0, m["bumper"])
        flip.data.transform(Matrix.Rotation(-math.pi / 2, 4, "X"))
        rubber = plate(name + "_rubber", flipper_outline(fl + 2.0, ft + 2.0, rest=sign * 28.0, side=sign), -16.0,
                       -6.0, m["rubber"])
        rubber.data.transform(Matrix.Rotation(-math.pi / 2, 4, "X"))
        flip = join([recolour(flip, m["bumper"]), recolour(rubber, m["rubber"])], name)
        parts[name] = (flip, holder.name)
        PIN_NODES[name + "_holder"] = holder
    plunger = smooth_shaded(tube("plunger", [(240.0, -120.0, 0.0), (240.0, 10.0, 0.0)], 6.0, m["trim"], 10))
    knob = ball("knob", 14.0, m["rubber"], 14, (240.0, -128.0, 0.0))
    plunger = join([plunger, knob], "plunger")
    plunger.data.transform(frame @ Matrix.Translation((0.0, 0.0, 14.0)))
    parts["plunger"] = (about(plunger, frame @ Vector((240.0, 0.0, 14.0))), None)
    rest = frame @ Vector((p["lane"][0] + 8.0, 40.0, p["ball"]))
    parts["ball"] = (about(ball("ball", p["ball"], m["ball"], 16, tuple(rest)), rest), None)
    for k in range(8):                                     # the backglass's lamps
        at = Vector((-245.0 + 70.0 * k, length - bb["depth"] - 1.4, glass_z - 258.0))
        lamp = recolour(plate(f"lamp{k}", E.circle(at.x, at.z, 9.0, 16), -1.6, -0.2, m["lit"]), m["lit"])
        lamp.data.transform(Matrix.Translation((0.0, at.y + 0.9, 0.0)))
        parts[f"lamp{k}"] = (about(lamp, at), None)
    for k in range(3):
        parts[f"bumper{k}"] = (PIN_NODES[f"bumper{k}"], None)
    PIN_NODES["frame"] = frame
    PIN_NODES["rest"] = rest
    for holder in holders:
        parts[holder.name] = (holder, None)
    return parts, statics, fpinball_timeline, 180


PIN_NODES = {}


def flipper_outline(length, tip, rest, side):
    """A flipper's outline about its pivot, pointing in (side -1: the left flipper, pointing right) and down by
    `rest` degrees: the pivot's round end, the tip's."""
    base = E.arc(0.0, 0.0, tip * 1.6, 90.0, 270.0, 10) + E.arc(length, 0.0, tip * 0.6, -90.0, 90.0, 8)
    if side > 0:
        base = [(-x, z) for x, z in base]
    return E.ccw(E.turned(base, rest))


BALL_PATH = [(33, (248.0, 40.0)), (48, (248.0, 1000.0)), (54, (150.0, 1080.0)), (58, (0.0, 1080.0)),
             (64, (-100.0, 800.0)), (70, (90.0, 830.0)), (76, (-5.0, 940.0)), (98, (-70.0, 175.0)),
             (104, (-60.0, 180.0)), (118, (40.0, 700.0)), (138, (10.0, 60.0)), (142, (0.0, -30.0))]


def ball_at(f):
    """Where the ball is on the playfield at frame f (u, v), along BALL_PATH."""
    for (f0, a), (f1, b) in zip(BALL_PATH, BALL_PATH[1:]):
        if f0 <= f < f1:
            t = (f - f0) / (f1 - f0)
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    return BALL_PATH[0][1] if f < BALL_PATH[0][0] else BALL_PATH[-1][1]


def fpinball_timeline(f):
    poses = {}
    frame, rest = PIN_NODES["frame"], PIN_NODES["rest"]
    pull = smooth(phase(f, 10, 30)) * (1 - (1.0 if f >= 31 else 0.0))
    snap = wobble(f, 31, 10.0, 6.0, 3.0)
    along = frame.to_3x3() @ Vector((0.0, -1.0, 0.0))
    poses["plunger"] = Pose(*(along * (60.0 * pull + snap)))
    u, v = ball_at(f)
    if f < 33:
        u, v = BALL_PATH[0][1][0], BALL_PATH[0][1][1] - 60.0 * pull
    at = frame @ Vector((u, v, L.PINBALL["ball"]))
    gone = 140 <= f < 168
    poses["ball"] = Pose(*(at - rest), scale=HIDDEN if gone else 1.0)
    if f >= 168:
        poses["ball"] = Pose(scale=HIDDEN + (1 - HIDDEN) * smooth(phase(f, 168, 176)))
    for k, f0 in enumerate((64, 70, 76)):
        poses[f"bumper{k}"] = Pose(scale=1.0 if f0 <= f < f0 + 5 else HIDDEN)
    poses["flipper_left"] = Pose(spin=50.0 * tap(f, 100, 3))
    poses["flipper_right"] = Pose(spin=-50.0 * tap(f, 124, 3))
    for k in range(8):
        on = 40 <= f < 150 and ((f // 4) % 8) == k
        poses[f"lamp{k}"] = Pose() if on else Pose(scale=HIDDEN)
    return poses


def vpinball(m):
    v = L.VPIN
    sw, sd, sh = v["slab"]
    slab = box("slab", -sw / 2, sw / 2, -sd / 2, sd / 2, -sh, 0.0, m["wood"])
    recolour(slab, m["wood"])
    field = curved("playfield", sw, sd, 0.0, media_uv("playfield"), m["media"], 4, 4)
    field.data.transform(Matrix.Translation((0.0, 0.0, 0.2)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    apron = recolour(box("apron", -sw / 2, sw / 2, -sd / 2 - 16.0, -sd / 2, -sh, 34.0, m["rubber"]), m["rubber"])
    apron_print = screen("apron_print", sw - 8.0, 30.0, "apron", m, at=(0.0, -sd / 2 - 16.4, 12.0))
    (bx, by), br = v["bumper"]
    base = recolour(lathe("bumper", [(br, 0.0), (br, 22.0), (8.0, 22.0)], m["bumper"], 28), m["bumper"])
    cap = recolour(lathe("cap", [(br - 4.0, 22.0), (br - 4.0, 34.0), (6.0, 38.0)], m["cap"], 28), m["cap"])
    for obj in (base, cap):
        obj.data.transform(Matrix.Translation((bx, by, 0.0)))
    sling = plate("sling", E.ccw(v["sling"]), -20.0, 0.0, m["bumper"])
    sling.data.transform(Matrix.Rotation(-math.pi / 2, 4, "X"))
    posts = [recolour(lathe("post", [(5.0, 0.0), (5.0, 26.0), (2.0, 28.0)], m["post"], 12), m["post"])
             for _ in v["sling"]]
    for post, (px, py) in zip(posts, v["sling"]):
        post.data.transform(Matrix.Translation((px, py, 0.0)))
    statics = [slab, field, apron, apron_print, base, cap, recolour(sling, m["bumper"])] + posts
    lit = recolour(lathe("lit", [(br - 3.0, 21.0), (br - 3.0, 35.0), (6.0, 39.5)], m["lit"], 28), m["lit"])
    lit.data.transform(Matrix.Translation((bx, by, 0.0)))
    parts = {"bumper_lit": (about(lit, (bx, by, 30.0)), None)}
    fl, ft = v["flipper"]
    for k, ((fx, fy), name) in enumerate(zip(v["flippers"], ("flipper_left", "flipper_right"))):
        sign = -1 if k == 0 else 1
        body = plate(name, flipper_outline(fl, ft, rest=sign * 28.0, side=sign), -20.0, 0.0, m["bumper"])
        rubber = plate(name + "_rubber", flipper_outline(fl + 2.0, ft + 2.0, rest=sign * 28.0, side=sign), -14.0,
                       -6.0, m["rubber"])
        flip = join([recolour(body, m["bumper"]), recolour(rubber, m["rubber"])], name)
        flip.data.transform(Matrix.Translation((fx, fy, 0.0)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
        parts[name] = (about(flip, (fx, fy, 0.0)), None)
    r = v["ball"]
    orb = ball("ball", r, m["media"], 32)
    chrome_uv(orb)
    rest = Vector((-36.0, -34.0, r))
    orb.data.transform(Matrix.Translation(rest))
    parts["ball"] = (about(orb, rest), None)
    VPIN_NODES["rest"] = rest
    return parts, statics, vpinball_timeline, 150


VPIN_NODES = {}


def chrome_uv(obj):
    """The ball's UVs: round its equator from its front (-y) as the chrome's middle, up and down by latitude, each
    face kept on one side of the seam."""
    mesh = obj.data
    layer = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    x, y, w, h = L.REGIONS[CARD["id"]]["ball"]
    size = L.MEDIA_SIZE
    for poly in mesh.polygons:
        mid = (math.atan2(poly.center.y, poly.center.x) / (2 * math.pi)) % 1.0
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            u = (math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0
            if abs(u - mid) > 0.5:
                u += 1.0 if u < mid else -1.0
            lat = math.asin(max(-1.0, min(1.0, co.z / co.length)))
            b = 0.5 - lat / math.pi
            layer.data[li].uv = ((x + min(1.0, max(0.0, u)) * w) / size, 1 - (y + b * h) / size)


VPIN_PATH = [(14, (-36.0, -34.0)), (30, (-14.0, 40.0)), (42, (40.0, -20.0)), (64, (40.0, -36.0)),
             (76, (40.0, -20.0)), (100, (-10.0, -14.0)), (126, (-36.0, -34.0))]


def vpinball_timeline(f):
    poses = {}
    rest = VPIN_NODES["rest"]
    pos = VPIN_PATH[0][1]
    for (f0, a), (f1, b) in zip(VPIN_PATH, VPIN_PATH[1:]):
        if f0 <= f < f1:
            t = smooth((f - f0) / (f1 - f0))
            pos = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    if f >= VPIN_PATH[-1][0]:
        pos = VPIN_PATH[-1][1]
    travel = smooth(phase(f, 14, 126))
    poses["ball"] = Pose(x=pos[0] - rest.x, y=pos[1] - rest.y, z=hop(f, 30, 42, 8.0),
                         spin=360.0 * travel, pitch=720.0 * travel)
    poses["flipper_left"] = Pose(spin=46.0 * tap(f, 12, 3) + 30.0 * tap(f, 118, 6))
    poses["flipper_right"] = Pose(spin=-46.0 * tap(f, 62, 3))
    poses["bumper_lit"] = Pose(scale=1.0 if 28 <= f < 36 else HIDDEN)
    return poses


# ---- The terminal ----------------------------------------------------------------------------------------------------

TYPED = (14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 66)       # L I G H T _ L A M P, then RETURN
LATER = (120, 125, 130, 135, 140, 147)


def zmachine(m):
    t = L.TERMINAL
    bw, bd, bh = t["base"]
    base = prism_x("base", [(0.0, 0.0), (bd, 0.0), (bd, bh), (150.0, bh), (0.0, 30.0)], -bw / 2, bw / 2, m["case"])
    bevel(base, 6.0, segments=2, angle=30.0)
    recolour(base, m["case"])
    slope = math.atan2(bh - 30.0, 150.0)
    deck = Matrix.Translation((0.0, 0.0, 30.0)) @ Matrix.Rotation(slope, 4, "X")
    nx, nz = t["keys"]
    keys, pressed = [], {}
    for j in range(nz):
        for i in range(nx):
            kx = -bw / 2 + 40.0 + i * 27.5
            kv = 22.0 + j * 30.0
            k = recolour(box(f"key{i}_{j}", kx, kx + 24.0, kv, kv + 22.0, 0.0, 9.0, m["keys"]), m["keys"])
            k.data.transform(deck)
            label = f"key{i}_{j}"
            if (i, j) in TERMINAL_PRESSED:
                pressed[TERMINAL_PRESSED[(i, j)]] = about(k, deck @ Vector((kx + 12.0, kv + 11.0, 9.0)))
            else:
                keys.append(k)
    hw, hd, hh = t["housing"]
    housing = box("housing", -hw / 2, hw / 2, 130.0, 130.0 + hd, bh, bh + hh, m["case"])
    bevel(housing, 18.0, segments=3, angle=30.0)
    recolour(housing, m["case"])
    sw, sh = t["screen"]
    sz = bh + hh / 2 + 6.0
    bezel = recolour(plate("bezel", rounded(0.0, sz, sw + 50.0, sh + 46.0, 14.0, 4), 127.0, 131.0, m["bezel"]),
                     m["bezel"])
    glass = screen("glass", sw, sh, "dark", m, bulge=6.0, at=(0.0, 126.0, sz))
    terminal = join([base, housing, bezel, glass] + keys, "terminal")
    parts = {"terminal": (terminal, None)}
    for name, (part, _) in layered(("typed", "lit", "room"), sw, sh, m, (0.0, 126.0, sz), bulge=6.0).items():
        parts[name] = (part, None)
    for name, part in pressed.items():
        parts[name] = (part, None)
    lx, ly = t["lantern"]["at"]
    lr, lh = t["lantern"]["r"], t["lantern"]["height"]
    foot = smooth_shaded(lathe("foot", [(lr, 0.0), (lr, 12.0), (lr * 0.86, 20.0), (lr * 0.7, 24.0)], m["brass"], 28))
    glass_l = smooth_shaded(lathe("lantern_glass", [(lr * 0.68, 24.0), (lr * 0.72, lh * 0.45), (lr * 0.68, lh * 0.72)],
                                  m["dark_glass"], 28))
    hood = smooth_shaded(lathe("hood", [(lr * 0.78, lh * 0.72), (lr * 0.6, lh * 0.82), (lr * 0.25, lh * 0.9),
                                        (lr * 0.25, lh * 0.95), (0.5, lh * 0.97)], m["brass"], 28))
    bars = [recolour(box("bar", -2.0, 2.0, -lr * 0.74, -lr * 0.7, 24.0, lh * 0.72, m["brass"]), m["brass"])
            for _ in range(4)]
    for k, bar in enumerate(bars):
        bar.data.transform(Matrix.Rotation(math.pi / 2 * k + math.pi / 4, 4, "Z"))
    handle = smooth_shaded(tube("handle", [(lr * 0.5 * math.cos(a), 0.0, lh * 0.95 + lr * 0.5 * math.sin(a))
                                           for a in [math.pi * k / 10 for k in range(11)]], 2.4, m["brass"], 8))
    lantern = join([foot, glass_l, hood, handle] + bars, "lantern")
    lantern.data.transform(Matrix.Translation((lx, ly, 0.0)))
    lit = smooth_shaded(lathe("lit", [(lr * 0.69, 24.5), (lr * 0.73, lh * 0.45), (lr * 0.69, lh * 0.715)],
                              m["lit_glass"], 28))
    lit.data.transform(Matrix.Translation((lx, ly, 0.0)))
    parts["lantern_lit"] = (about(lit, (lx, ly, lh * 0.4)), None)
    return parts, [lantern], zmachine_timeline, 210


TERMINAL_PRESSED = {(9, 1): "key_l", (8, 2): "key_i", (5, 1): "key_g", (6, 1): "key_h", (5, 2): "key_t",
                    (6, 0): "key_space", (2, 1): "key_a", (7, 0): "key_m", (10, 2): "key_p",
                    (12, 1): "key_return"}


def zmachine_showing(f):
    if 30 <= f < 68:
        return "typed"
    if 68 <= f < 150:
        return "lit"
    if 150 <= f < 198:
        return "room"
    return None


def zmachine_timeline(f):
    poses = showing_poses(("typed", "lit", "room"), zmachine_showing, f)
    order = ["key_l", "key_i", "key_g", "key_h", "key_t", "key_space", "key_l", "key_a", "key_m", "key_p",
             "key_return"]
    presses = {}
    for name, f0 in zip(order, TYPED):
        presses.setdefault(name, []).append(f0)
    for name, f0 in zip(["key_t", "key_a", "key_h", "key_g", "key_i", "key_return"], LATER):
        presses.setdefault(name, []).append(f0)
    down = L.TERMINAL["base"]
    slope = math.atan2(down[2] - 30.0, 150.0)
    normal = Vector((0.0, math.sin(slope), -math.cos(slope)))
    for name, frames in presses.items():
        poses[name] = Pose(*(normal * 3.0 * taps(f, frames, 1)))
    poses["lantern_lit"] = Pose() if 72 <= f < 198 else Pose(scale=HIDDEN)
    return poses


# ---- Steam Deck ------------------------------------------------------------------------------------------------------

def deck_outline():
    """The Deck's outline seen from the front (x, z): straight across the top, its grips reaching down at the ends."""
    (w, h), r = L.DECK["size"], L.DECK["round"]
    top = h / 2
    points = E.arc(w / 2 - r, top - r, r, 0.0, 90.0, 8) + E.arc(-w / 2 + r, top - r, r, 90.0, 180.0, 8)
    points += E.arc(-w / 2 + r * 1.3, -top + r * 1.3, r * 1.3, 180.0, 300.0, 10)
    points += [(-w / 2 + 92.0, -top + 14.0), (w / 2 - 92.0, -top + 14.0)]
    points += E.arc(w / 2 - r * 1.3, -top + r * 1.3, r * 1.3, 240.0, 360.0, 10)
    return E.ccw(points)


def steam(m):
    dk = L.DECK
    d = dk["depth"]
    body = plate("deck", deck_outline(), -d / 2, d / 2, m["body"])
    bevel(body, 5.0, segments=3, angle=30.0)
    recolour(body, m["body"])
    grips = []
    for x0, x1 in ((-146.0, -95.0), (95.0, 146.0)):     # the grips, bulging behind
        grip = box("grip", x0, x1, d / 2 - 2.0, d / 2 + 24.0, -56.0, 34.0, m["body"])
        bevel(grip, 12.0, segments=3, angle=30.0)
        grips.append(recolour(grip, m["body"]))
    bw, bh = dk["bezel"]
    bezel = recolour(plate("bezel", rounded(0.0, 4.0, bw, bh, 6.0, 4), -d / 2 - 0.6, -d / 2 + 1.0, m["button"]),
                     m["button"])
    sw, sh = dk["screen"]
    dark = recolour(plate("screen_off", rounded(0.0, 4.0, sw, sh, 1.0, 1), -d / 2 - 1.0, -d / 2 - 0.6, m["glass"]),
                    m["glass"])
    pads = []
    for k, (px, pz) in enumerate(dk["pads"]):
        pad = recolour(plate(f"pad{k}", rounded(px, pz, dk["pad"], dk["pad"], 4.0, 3), -d / 2 - 0.4, -d / 2 + 1.0,
                             m["button"]), m["button"])
        pads.append(pad)
    dx, dz = dk["dpad"]
    plus = E.ccw([(dx - 3.5, dz - 10.0), (dx + 3.5, dz - 10.0), (dx + 3.5, dz - 3.5), (dx + 10.0, dz - 3.5),
                  (dx + 10.0, dz + 3.5), (dx + 3.5, dz + 3.5), (dx + 3.5, dz + 10.0), (dx - 3.5, dz + 10.0),
                  (dx - 3.5, dz + 3.5), (dx - 10.0, dz + 3.5), (dx - 10.0, dz - 3.5), (dx - 3.5, dz - 3.5)])
    dpad = recolour(plate("dpad", plus, -d / 2 - 2.5, -d / 2 + 1.0, m["button"]), m["button"])
    ax, az = dk["abxy"]
    face = [recolour(plate(f"face{k}", E.circle(ax + ox, az + oz, 4.6, 16), -d / 2 - 2.5, -d / 2 + 1.0, m["button"]),
                     m["button"]) for k, (ox, oz) in enumerate(((0.0, 9.0), (-9.0, 0.0), (9.0, 0.0)))]
    dots_x, dots_z = dk["dots"]
    dots = recolour(plate("dots", rounded(dots_x, dots_z, 14.0, 5.0, 2.5, 3), -d / 2 - 1.5, -d / 2 + 1.0,
                          m["button"]), m["button"])
    shoulders = []
    for sign in (-1, 1):
        x0, x1 = sorted((sign * 104.0, sign * 140.0))
        shoulders.append(recolour(box("bumper", x0, x1, -4.0, 8.0, 56.0, 62.0, m["stick"]), m["stick"]))
        shoulders.append(recolour(box("trigger", x0 + 4.0, x1 - 4.0, 8.0, 26.0, 50.0, 60.0, m["stick"]), m["stick"]))
    deck = join([body, bezel, dark, dpad, dots] + grips + pads[:1] + face + shoulders, "deck")
    parts = {"deck": (deck, None)}
    for name, (part, _) in layered(("boot", "library", "game1", "game2"), sw, sh, m, (0.0, -d / 2 - 1.2, 4.0)
                                   ).items():
        parts[name] = (part, "deck")
    parts["pad_right"] = (about(pads[1], (dk["pads"][1][0], -d / 2, dk["pads"][1][1])), "deck")
    a_button = recolour(plate("a", E.circle(ax, az - 9.0, 4.6, 16), -d / 2 - 2.5, -d / 2 + 1.0, m["button"]),
                        m["button"])
    parts["button_a"] = (about(a_button, (ax, -d / 2, az - 9.0)), "deck")
    sx, sz = dk["steam"]
    steam_button = recolour(plate("steam_button", rounded(sx, sz, 16.0, 6.0, 3.0, 3), -d / 2 - 1.8, -d / 2 + 1.0,
                                  m["button"]), m["button"])
    parts["button_steam"] = (about(steam_button, (sx, -d / 2, sz)), "deck")
    for k, (kx, kz) in enumerate(dk["sticks"]):
        ring = lathe("ring", [(17.0, 0.0), (17.0, 2.5), (8.0, 2.5)], m["stick"], 24)
        shaft = lathe("shaft", [(6.0, 0.0), (6.0, 9.0)], m["stick"], 16)
        cap = lathe("cap", [(15.0, 9.0), (16.0, 13.0), (15.0, 15.0), (12.0, 14.0), (0.5, 13.0)], m["cap"], 24)
        stick = join([recolour(ring, m["stick"]), recolour(shaft, m["stick"]), smooth_shaded(cap)], f"stick{k}")
        stick.data.transform(Matrix.Translation((kx, -d / 2, kz)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        parts[f"stick{k}"] = (about(stick, (kx, -d / 2, kz)), "deck")
    deck.location = (0.0, 0.0, 0.0)
    return parts, [], steam_timeline, 180


def steam_showing(f):
    if 30 <= f < 40:
        return "boot"
    if 40 <= f < 76:
        return "library"
    if 76 <= f < 150:
        return "game1" if ((f - 76) // 8) % 2 == 0 else "game2"
    return None


def steam_timeline(f):
    poses = showing_poses(("boot", "library", "game1", "game2"), steam_showing, f)
    up = smooth(phase(f, 6, 22)) * (1 - smooth(phase(f, 154, 170)))
    shake = 2.2 * math.sin(f * 2.7) * (1.0 if 120 <= f < 130 else 0.0)
    poses["deck"] = Pose(z=25.0 * up, pitch=-12.0 * up, roll=shake)
    poses["button_steam"] = Pose(y=1.5 * tap(f, 26))
    poses["button_a"] = Pose(y=1.5 * tap(f, 70))
    poses["pad_right"] = Pose(y=1.0 * taps(f, (100, 116)))
    t = phase(f, 80, 146)
    wave = math.sin(math.pi * t)
    poses["stick0"] = Pose(pitch=14.0 * math.sin(2 * math.pi * 3 * t) * wave, spin=12.0 * math.sin(2 * math.pi * 2 * t)
                           * wave)
    poses["stick1"] = Pose(pitch=10.0 * math.sin(2 * math.pi * 2 * t + 1.0) * wave,
                           spin=16.0 * math.sin(2 * math.pi * 3 * t) * wave)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

CARDS = dict(tic80=(tic80, L.TIC80_COLOURS), wasm4=(wasm4, dict(L.WASM4_COLOURS, side="#4E7228")),
             lowresnx=(lowresnx, L.LOWRES_COLOURS), vircon32=(vircon32, L.VIRCON_COLOURS),
             fpinball=(fpinball, L.PINBALL_COLOURS), vpinball=(vpinball, L.VPIN_COLOURS),
             zmachine=(zmachine, L.TERMINAL_COLOURS), steam=(steam, dict(L.DECK_COLOURS, glass="#0A0A0C")))
HIDDEN_AT_REST = dict(tic80=("screen_", "cart"), wasm4=("screen_",), lowresnx=("screen_",),
                      vircon32=("led_lit", "card"), fpinball=("bumper", "lamp"), vpinball=("bumper_lit",),
                      zmachine=("screen_", "lantern_lit"), steam=("screen_",))
TILTS = dict(fpinball=(-32.0, 14.0), vpinball=(-20.0, 34.0), zmachine=(-26.0, 10.0))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, card, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    CARD["id"] = card
    build, colours = CARDS[card]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    m = {name: material(name, colour, 0.35) for name, colour in colours.items() if not name.startswith(("contacts",
                                                                                                         "edge"))}
    m["media"] = material("media", "#FFFFFF", 0.3, bpy.data.images.load(os.path.join(images, L.media_file(card))))
    parts, statics, timeline, length = build(m)

    root = bpy.data.objects.new(card + "_root", None)
    scene.collection.objects.link(root)
    meshes, empties = [], []
    if statics:
        base = join(statics, card + "_set") if len(statics) > 1 else statics[0]
        base.parent = root
        meshes.append(base)
    by_name = {name: obj for name, (obj, _) in parts.items()}
    for name, (obj, parent) in parts.items():
        if obj.type == "MESH":
            obj.name = name
        if parent:
            holder = by_name.get(parent) or bpy.data.objects[parent]
            obj.parent = holder
            if holder.type != "EMPTY":                   # an empty's parts are made at its origin
                obj.location = Vector(obj.location) - holder.location
        else:
            obj.parent = root
        (meshes if obj.type == "MESH" else empties).append(obj)
    bpy.context.view_layer.update()

    yaw, pitch = TILTS.get(card, (TILT_YAW, TILT_PITCH))
    tilt = Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    points = []
    for obj in meshes:
        if obj.name.startswith(HIDDEN_AT_REST[card]):
            continue
        points += [tilt @ (obj.matrix_world @ v.co) for v in obj.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt
    nodes = {name: obj for name, (obj, _) in parts.items() if obj.type == "MESH"}
    key("focused", nodes, lambda f: {k: v for k, v in timeline(f).items() if k in nodes}, length)
    print(f"{card}: {sum(triangles(o.data) for o in meshes)} triangles, "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + empties + meshes, out, animations=True)


if __name__ == "__main__":
    main()
