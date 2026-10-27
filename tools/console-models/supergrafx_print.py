"""The SuperGrafx card's printing (supergrafx_print.png), for the console theme's SuperGrafx model (supergrafx.py).

One image, laid out as supergrafx_layout.REGIONS says, each region in millimetres as the model's UVs map it: the
console from above (SUPER GRAFX up the spine's strip in light blue, PC Engine under it, the bolts' sockets, NEC and
POWER's OFF and ON on the left block, HE on the right one, AC ADAPTER on the rear block, the channel's floor, its
finger notch, the lock tab's slot), the base's front (the S EXP door, the pad's socket), the HuCard's face (a made-up
game from tools/made-up-games: its box art, HuCARD and SUPER GRAFX on the band) and the pad's top (the dark face plate,
the light blue fan round the D-pad, the turbo switches, SELECT and RUN, II and I on their blue tags, NEC PI-PD6), where
pc_engine_layout.py has the card's and the pad's; and swatches. Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system
Python (Pillow):

    python tools/console-models/supergrafx_print.py artifacts/made-up-games <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc_engine_layout as P  # noqa: E402
import screens_print as S  # noqa: E402
import supergrafx_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
DARK = rgb(L.COLOURS["dark"])
BLUE = rgb(L.COLOURS["blue"])
PAD = rgb(L.COLOURS["pad"])
GAME = ("Concrete Knuckles (Europe)", "snes")       # a made-up beat-'em-up, on its HuCard


def upright(reg, text, font, size, x, y, fill, stretch=1.0):
    """Text turned to read up the page (bottom to top), its middle at (x, y), stretched along its length."""
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    box = f.getbbox(text)
    layer = Image.new("RGBA", (box[2] - box[0] + 8, box[3] - box[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((4 - box[0], 4 - box[1]), text, font=f, fill=fill + (255,))
    layer = layer.resize((round(layer.width * stretch), layer.height), Image.LANCZOS).rotate(90, expand=True)
    cx, cy = reg.p(x, y)
    reg.img.alpha_composite(layer, (round(cx - layer.width / 2), round(cy - layer.height / 2)))


def pc_engine(reg, x, y, s, colour):
    """PC Engine's logo, s across, its middle at (x, y): PC over Engine, outlined, in an oval; in one colour."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    d.ellipse(reg.box(x - s / 2, y - s * 0.17, x + s / 2, y + s * 0.17), outline=colour + (255,),
              width=max(1, round(s * 0.02 * reg.sx)))
    big = ImageFont.truetype(FONTS + "arialbi.ttf", max(1, round(s * 0.2 * reg.sx)))
    for text, ty, tx in (("PC", y - s * 0.1, x - s * 0.08), ("Engine", y + s * 0.07, x + s * 0.02)):
        d.text(reg.p(tx, ty), text, font=big, fill=CASE + (255,), anchor="mm",
               stroke_width=max(1, round(s * 0.016 * reg.sx)), stroke_fill=colour + (255,))
    reg.over(layer)


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    # The strip down the spine, its lettering reading up it; the ribs' shading either side.
    x0, x1 = -L.RIBS["x"][0], L.RIBS["x"][0]
    reg.rect_(*at(x0 + 2.0, L.STRIP["y"][1]), *at(x1 - 2.0, L.STRIP["y"][0]), shade(CASE, 0.05), r=2.0)
    upright(reg, "SUPER", "ariblk.ttf", 21.0, *at(-8.0, 68.0), BLUE, stretch=1.15)
    upright(reg, "GRAFX", "arialbd.ttf", 10.0, *at(12.0, 84.0), BLUE, stretch=1.25)
    pc_engine(reg, *at(0.0, 15.0), 32.0, BLUE)
    r = L.RIBS
    for side in (-1, 1):
        for k in range(r["count"]):
            x = side * (r["x"][0] + (r["x"][1] - r["x"][0]) * (k + 0.5) / r["count"])
            reg.rect_(*at(x - r["width"] / 2, r["y"][1]), *at(x + r["width"] / 2, r["y"][0]), shade(CASE, -0.35))
    for x, y in L.SCREWS["at"]:                                 # the screws' heads and their hex sockets
        reg.circle(*at(x, y), L.SCREWS["r"], shade(CASE, -0.2))
        cx, cy = at(x, y)
        reg.poly([(cx + 2.4 * math.cos(math.pi * k / 3), cy + 2.4 * math.sin(math.pi * k / 3)) for k in range(6)],
                 DARK)
    (cx0, cx1), (cy0, cy1) = L.CHANNEL["x"], L.CHANNEL["y"]
    reg.rect_(*at(cx0, cy1), *at(cx1, cy0), shade(CASE, -0.12))
    n0, n1, _ = L.CHANNEL["notch"]
    reg.rect_(*at(cx0 + 8.0, n1), *at(cx1 - 8.0, n0), shade(CASE, -0.3))
    (tx0, tx1), (ty0, ty1) = L.TAB["x"], L.TAB["y"]
    reg.rect_(*at(tx0 - 1.0, ty1 + 1.0), *at(tx1 + 1.0, ty0 - 1.0), DARK, r=0.8)
    # The blocks: NEC, POWER's OFF and ON round its well; HE.
    (bx0, bx1), (by0, by1) = L.BLOCKS["x"], L.BLOCKS["y"]
    reg.text("NEC", "timesbd.ttf", 4.6, *at(-bx1 + 9.0, by1 - 6.0), shade(CASE, 0.25))
    (px0, px1), (py0, py1) = L.POWER["x"], L.POWER["y"]
    reg.rect_(*at(px0 - 1.0, py1 + 1.0), *at(px1 + L.POWER["travel"] + 1.0, py0 - 1.0), DARK, r=1.0)
    reg.text("POWER", "arialbd.ttf", 3.0, *at((px0 + px1) / 2 + 3.5, py1 + 4.0), shade(CASE, 0.35))
    reg.text("OFF", "arial.ttf", 2.6, *at(px0, py0 - 3.0), shade(CASE, 0.3))
    reg.text("ON", "arial.ttf", 2.6, *at(px1 + L.POWER["travel"], py0 - 3.0), shade(CASE, 0.3))
    reg.text("HE", "timesbd.ttf", 6.0, *at(bx1 - 10.0, by1 - 7.0), shade(CASE, 0.2))
    reg.text("AC ADAPTER", "arialbd.ttf", 3.0, *at(-30.0, L.TOWER["y"][0] + 10.0), shade(CASE, 0.22), anchor="lm")
    return reg


def front():
    """The base's front, from in front: the S EXP door and the pad's socket, right of the spine."""
    w, h = L.WIDTH, L.WINGS["height"]
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    (x0, x1), (z0, z1) = L.HATCH["x"], L.HATCH["z"]
    reg.rect_(*at(x0, z1), *at(x1, z0), shade(CASE, -0.08), r=1.5, outline=shade(CASE, -0.4), width=0.5)
    reg.text("S EXP", "arialbd.ttf", 2.6, *at((x0 + x1) / 2, z1 - 4.0), shade(CASE, 0.3))
    reg.circle(*at(L.SOCKET["x"], L.SOCKET["z"]), L.SOCKET["r"] + 1.2, shade(CASE, -0.3))
    return reg


def card(made_up):
    """The HuCard's face as it stands in the slot, its contacts' end down: the band (HuCARD, SUPER GRAFX), the made-up
    game's box art, the dark end; turned half round, as pc_engine.py's card is stood up."""
    w, length = P.CARD["size"]
    reg = Region(L.REGIONS["card"], w, length, (238, 238, 236))
    reg.rect_(3.0, 3.0, w - 3.0, 12.0, (20, 22, 26))
    reg.text("HuCARD", "arialbi.ttf", 3.6, 14.0, 7.5, (240, 240, 240))
    reg.text("SUPER GRAFX", "arialbd.ttf", 3.0, w - 4.0, 7.5, BLUE, anchor="rm")
    art = S.cover(*GAME, made_up)
    a, b, c, d = reg.box(3.0, 13.0, w - 3.0, length - 27.0)
    reg.img.paste(ImageOps.fit(art, (round(c - a), round(d - b)), Image.LANCZOS), (round(a), round(b)))
    reg.rect_(0.0, length - 24.0, w, length, DARK, r=1.2)
    for k in range(38):
        x = 3.0 + k * (w - 6.0) / 38
        reg.rect_(x, length - 6.0, x + 0.8, length - 1.4, (196, 160, 70))
    reg.img = reg.img.rotate(180)
    return reg


def pad():
    """The pad's top (pc_engine_layout's PAD): the SuperGrafx's dark grey and light blue."""
    pw, pd, _ = P.PAD["size"]
    reg = Region(L.REGIONS["pad"], pw, pd, PAD)
    p = P.PAD

    def at(x, y):
        return x + pw / 2, pd / 2 - y
    x0, x1, y0, y1 = p["plate"]
    plate = shade(PAD, -0.25)
    reg.rect_(*at(x0, y1), *at(x1, y0), plate, r=4.0)
    reg.circle(*at(0.0, p["dome"]["y"]), p["dome"]["r"] + 1.5, PAD)
    dx, dy, span, _ = p["dpad"]
    for k in range(5):                                        # the fan of light blue round the D-pad's right
        a0 = math.radians(-60 + k * 26)
        a1 = a0 + math.radians(20)
        pts = [at(dx + r * math.cos(a), dy + r * math.sin(a)) for r, a in ((17.0, a0), (22.0, a0), (22.0, a1),
                                                                            (17.0, a1))]
        reg.poly(pts, BLUE)
    reg.circle(*at(dx, dy), span / 2 + 2.5, shade(plate, -0.25))
    pw_, ph_ = p["pill"]
    for (x, y), word in ((p["select"], "SELECT"), (p["run"], "RUN")):
        reg.rect_(*at(x - pw_ / 2 - 1.2, y + ph_ / 2 + 1.2), *at(x + pw_ / 2 + 1.2, y - ph_ / 2 - 1.2), shade(plate, -0.3),
                  r=ph_ / 2 + 1.2)
        reg.text(word, "arialbd.ttf", 3.0, *at(x, y - 7.0), (220, 222, 226))
    for (x, y), word in ((p["ii"], "II"), (p["i"], "I")):
        reg.circle(*at(x, y), p["button_r"] + 0.9, shade(plate, -0.3))
        reg.rect_(*at(x - 4.5, y + 19.5), *at(x + 4.5, y + 12.5), BLUE, r=1.2)
        reg.text(word, "timesbd.ttf", 4.6, *at(x, y + 16.0), (250, 250, 250))
    for k, x in enumerate((30.0, 46.0)):                      # the turbo switches, their blue dots
        reg.rect_(*at(x - 2.0, 24.0), *at(x + 2.0, 12.0), shade(plate, -0.35), r=1.0)
        for j in range(3):
            reg.circle(*at(x + 4.5, 22.0 - j * 4.0), 0.9, BLUE)
    reg.text("NEC", "timesbd.ttf", 4.6, *at(-50.0, 13.0), (230, 232, 236))
    reg.text("PI-PD6", "arialbi.ttf", 3.0, *at(-38.0, 13.0), (230, 232, 236), anchor="lm")
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), card(made_up), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(green=rgb(L.COLOURS["green"]), grey=(62, 64, 68), dark=DARK, red=(226, 82, 64), white=(70, 72, 76),
                   case=CASE, rib=shade(CASE, -0.3), screw=shade(CASE, -0.2), blue=BLUE)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "supergrafx_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
