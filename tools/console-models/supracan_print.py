"""The Super A'Can card's printing (supracan_print.png), for the console theme's Super A'Can model (supracan.py).

One image, laid out as supracan_layout.REGIONS says, each region in millimetres as the model's UVs map it: the console
from above (the flap with USE CASSETTE WITH FUNTECH ONLY and its arrows, POWER with ON and OFF, EJECT and RESET, the
power light, the vents' shade, the A'can logo moulded at the front right), the cartridge's face (a made-up game from
tools/made-up-games on its label, the A'can bubble and a catalogue number; the ribs and windows under it), the
controller from above (the D-pad's well, the raised A'can panel, Y X B A, SELECT and START), and swatches. Make the
made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/supracan_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screens_print as S  # noqa: E402
import supracan_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
PAD = rgb(L.COLOURS["pad"])
WHITE = (238, 238, 236)
GAME = ("Stormfist (Europe)", "snes")    # a made-up 16-bit fighter, as the A'Can's own Sango Fighter was
NUMBER = "F-021"


def bubble(reg, cx, cy, r, ink, drops=((0.95, -0.95, 0.22), (1.25, -0.6, 0.16), (1.2, -1.2, 0.12))):
    """The A'can bubble: a ball, its tail, three drops above it at its right."""
    reg.circle(cx, cy, r, ink)
    reg.poly([(cx - 0.55 * r, cy + 0.6 * r), (cx - 0.15 * r, cy + 0.95 * r), (cx - 0.75 * r, cy + 1.35 * r)], ink)
    for dx, dy, k in drops:
        reg.circle(cx + dx * r, cy + dy * r, k * r, ink)


def top():
    x0, x1 = L.TOP_X
    y0, y1 = L.TOP_Y
    reg = Region(L.REGIONS["top"], x1 - x0, y1 - y0, CASE)

    def at(x, y):
        return x - x0, y1 - y

    v = L.VENTS
    for k in range(v["count"]):
        x = v["x"][0] + (v["x"][1] - v["x"][0]) * (k + 0.5) / v["count"]
        reg.rect_(*at(x - v["width"] / 2, v["y"][1]), *at(x + v["width"] / 2, v["y"][0]), shade(CASE, -0.45))
    fx0, fx1, fy0, fy1 = L.FLAP["rect"]
    flap = rgb(L.COLOURS["flap"])
    reg.rect_(*at(fx0, fy1), *at(fx1, fy0), flap, r=2.0)
    reg.text("USE CASSETTE WITH FUNTECH ONLY", "arialbd.ttf", 2.6, *at(0.0, (fy0 + fy1) / 2 + 2.0), WHITE)
    reg.text("◥◤", "seguisym.ttf", 2.6, *at(0.0, fy0 + 3.0), shade(flap, -0.3))
    for x in (fx0 + 5.0, fx1 - 5.0):
        reg.rect_(*at(x - 0.4, fy1 - 3.0), *at(x + 0.4, fy0 + 3.0), shade(flap, -0.25))
    # The panel's names, POWER's slide.
    wx0, wx1, wy0, wy1 = L.POWER["well"]
    reg.rect_(*at(wx0, wy1), *at(wx1, wy0), shade(CASE, -0.35), r=0.8)
    reg.text("POWER", "arialbd.ttf", 3.0, *at((wx0 + wx1) / 2, wy1 + 3.4), WHITE)
    reg.text("ON", "arial.ttf", 1.9, *at(wx0 - 3.6, wy0 + L.POWER["knob"] / 2 + L.POWER["travel"]), WHITE)
    reg.text("OFF", "arial.ttf", 1.9, *at(wx0 - 3.6, wy0 + L.POWER["knob"] / 2), WHITE)
    for name, rect in (("EJECT", L.EJECT["rect"]), ("RESET", L.RESET["rect"])):
        bx0, bx1, by0, by1 = rect
        reg.text(name, "arialbd.ttf", 3.0, *at((bx0 + bx1) / 2, by1 + 3.4), WHITE)
        reg.circle(*at((bx0 + bx1) / 2, (by0 + by1) / 2), 5.0, shade(CASE, -0.06))
    lw, lh = L.LIGHT["size"]
    reg.rect_(*at(L.LIGHT["x"] - lw / 2, L.LIGHT["y"] + lh / 2), *at(L.LIGHT["x"] + lw / 2, L.LIGHT["y"] - lh / 2),
              (70, 22, 20), r=1.2)
    # The logo, moulded in the case's grey.
    cx, cy = at(L.LOGO["x"], L.LOGO["y"])
    reg.circle(cx, cy, L.LOGO["r"], shade(CASE, -0.05), outline=shade(CASE, -0.18), width=0.4)
    bubble(reg, cx - 1.0, cy - 3.0, 5.6, shade(CASE, -0.16))
    reg.text("Acan", "arialbi.ttf", 5.0, cx + 1.0, cy + 9.0, shade(CASE, -0.16))
    return reg


def face(made_up):
    """The cartridge's face: the label (the game's painting and logo, the bubble, its number), ribs under it."""
    w, _, h = L.CART["size"]
    cart = rgb(L.COLOURS["cart"])
    reg = Region(L.REGIONS["face"], w, h, cart)
    for k in range(10):
        reg.rect_(6.0, 60.0 + 2.6 * k, w - 6.0, 61.0 + 2.6 * k, shade(cart, -0.3))
    for x in (20.0, w - 44.0):
        reg.rect_(x, 64.0, x + 24.0, 80.0, shade(cart, -0.55), r=1.0)
    game = S.made_up(*GAME, made_up)
    reg.rect_(5.0, 4.0, w - 5.0, 56.0, (240, 240, 236), r=4.0)
    a, b, c, d = reg.box(6.5, 5.5, w - 6.5, 54.5)
    art = ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.35))
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, art.width - 1, art.height - 1], radius=round(3.0 * reg.sx), fill=255)
    reg.img.paste(art, (round(a), round(b)), mask)
    k = min((c - a) * 0.62 / game.logo.width, (d - b) * 0.3 / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(logo, (round(c - logo.width - 2.0 * reg.sx), round(d - logo.height - 2.0 * reg.sy)))
    bubble(reg, 14.0, 13.0, 4.0, (40, 170, 90))
    reg.text(NUMBER, "arialbd.ttf", 2.8, w - 10.0, 9.5, WHITE, anchor="rm")
    return reg


def pad():
    x0, x1, y0, y1 = L.PAD_SPAN
    reg = Region(L.REGIONS["pad"], x1 - x0, y1 - y0, PAD)
    P = L.PAD

    def at(x, y):
        return x - x0, y1 - y

    dx, dy, _, _ = P["dpad"]
    reg.circle(*at(dx, dy), P["well"], shade(PAD, -0.25))
    (px0, py0), (px1, py1) = P["panel"]
    reg.poly([at(px0, py1), at(px1, py1), at(px1 - 2.0, py0), at(px0 + 2.0, py0)], rgb(L.COLOURS["panel"]))
    bubble(reg, *at(px0 + 4.0, (py0 + py1) / 2 - 1.0), 1.6, shade(rgb(L.COLOURS["panel"]), -0.2))
    reg.text("Acan", "arialbi.ttf", 5.4, *at(2.0, (py0 + py1) / 2), shade(rgb(L.COLOURS["panel"]), -0.2))
    for name, (bx, by) in P["buttons"].items():
        reg.circle(*at(bx, by), P["button_r"] + 0.8, shade(PAD, -0.2))
        lx, ly = {"y": (bx + 8.0, by - 2.0), "x": (bx - 7.5, by - 5.0), "b": (bx + 8.5, by - 2.0),
                  "a": (bx + 1.0, by - 8.6)}[name]
        reg.text(name.upper(), "arialbd.ttf", 2.6, *at(lx, ly), WHITE)
    for name in ("select", "start"):
        sx, sy = P[name]
        reg.text(name.upper(), "arialn.ttf" if os.path.exists("C:/Windows/Fonts/arialn.ttf") else "arial.ttf", 2.0,
                 *at(sx, sy - 4.6), WHITE)
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), face(made_up), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(L.COLOURS[name]))
    path = os.path.join(out, "supracan_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
