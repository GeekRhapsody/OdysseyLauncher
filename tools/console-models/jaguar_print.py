"""The Atari Jaguar set's printing, for the console theme's Jaguar and Jaguar CD models (tools/console-models/jaguar.py).

Draws one atlas for both, its regions as jaguar_layout.py places them, each in millimetres as the model's planar UVs
map it: the Jaguar from above (JAGUAR in red script, the dish's rim, Atari's logo and 64-BIT INTERACTIVE MULTIMEDIA
SYSTEM on the nose, the power button's ring); the controller from above (the D-pad's ring, the ridges and Atari's logo
by the cable, PAUSE and OPTION, A, B and C, the keypad's plate and its numbers); the Jaguar CD from above (its lid with
the crescent window and JAGUAR CD, CLOSE HERE, Atari's logo and COMPACT DIGITAL MEDIA PLAYER); the CD's label and the
cartridge's (a made-up game, Odyssey); and the swatches small parts take their colour from. Run it with the system
Python (Pillow):

    python tools/console-models/jaguar_print.py <out folder>

It writes jaguar_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jaguar_layout as L  # noqa: E402
from atari5200_print import fuji  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
RED = rgb(L.COLOURS["red"])
INK = (210, 210, 214)
LOGO_RED = (178, 52, 40)


def jaguar(reg, cx, cy, w, h, colour, cd=False):
    """JAGUAR in a slanted brush script, w x h, its middle at (cx, cy), the claw marks trailing from its R; CD under it,
    when it's the Jaguar CD's."""
    mask = Image.new("L", (1400, 300), 0)
    d = ImageDraw.Draw(mask)
    f = ImageFont.truetype(FONTS + "BRUSHSCI.TTF", 240)
    d.text((40, 150), "JAGUAR", font=f, fill=255, anchor="lm")
    for k in range(3):                                         # the claw marks after the R
        y = 150 + 30 * k
        d.line([(1000, y), (1360, y - 30)], fill=255, width=14)
    mask = mask.crop(mask.getbbox())
    mask = mask.transform(mask.size, Image.AFFINE, (1, 0.25, -0.25 * mask.height / 2, 0, 1, 0))
    x0, y0, x1, y1 = reg.box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    mask = mask.resize((max(1, round(x1 - x0)), max(1, round(y1 - y0))), Image.LANCZOS)
    reg.img.paste(Image.new("RGBA", mask.size, colour + (255,)), (round(x0), round(y0)), mask)
    if cd:
        reg.text("CD", "BRUSHSCI.TTF", h * 0.9, cx + w * 0.22, cy + h * 0.85, colour)


# ---- The Jaguar --------------------------------------------------------------------------------------------------------

def top():
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["top"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y
    (dx, dy), r = L.DISH["at"], L.DISH["r"]
    reg.circle(*at(dx, dy), r + 1.5, shade(CASE, -0.25))
    reg.circle(*at(dx, dy), r, shade(CASE, 0.06))
    (lx, ly), (lw, lh) = L.LOGO["at"], L.LOGO["size"]
    jaguar(reg, *at(lx, ly), lw, lh, LOGO_RED)
    (px, py), (pw, ph) = L.POWER["at"], L.POWER["size"]
    reg.draw.ellipse(reg.box(*at(px - pw / 2 - 1.2, py + ph / 2 + 1.2), *at(px + pw / 2 + 1.2, py - ph / 2 - 1.2)),
                     fill=(10, 10, 11))
    reg.circle(*at(px, py - 9.0), 1.2, (60, 16, 14))           # the power light
    fuji(reg, *at(-12.0, 12.0), 4.4, INK)
    reg.text("ATARI", "arialbd.ttf", 3.8, *at(-8.0, 12.0), INK, anchor="lm")
    reg.text("64-BIT  INTERACTIVE  MULTIMEDIA  SYSTEM", "arialbd.ttf", 2.6, *at(0.0, 5.0), INK)
    (fx0, fx1), (fy0, fy1) = L.FRAME["x"], L.FRAME["y"]
    reg.rect_(*at(fx0, fy1), *at(fx1, fy0), shade(CASE, -0.06), r=3.0)
    return reg


# ---- The controller ------------------------------------------------------------------------------------------------

def pad():
    w = 2 * max(x for x, _ in L.PAD_OUTLINE)
    d = L.PAD_D
    reg = Region(L.REGIONS["pad"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y
    (dx, dy), ring = L.DPAD["at"], L.DPAD["ring"]
    reg.circle(*at(dx, dy), ring + 1.5, (12, 12, 13))
    reg.circle(*at(dx, dy), ring - 2.5, (24, 24, 26))
    for k in range(6):
        a = math.radians(60 * k + 30)
        reg.circle(*at(dx + (ring - 0.5) * math.cos(a), dy + (ring - 0.5) * math.sin(a)), 0.6, (60, 60, 64))
    for k in range(3):                                         # the ridges under the cable
        y = 108.0 - 6.0 * k
        reg.draw.arc(reg.box(*at(-34.0 + 6.0 * k, y + 8.0), *at(34.0 - 6.0 * k, y - 8.0)), 200, 340,
                     fill=shade(CASE, -0.3), width=reg.width(1.2))
    reg.rect_(*at(-30.0, 124.0), *at(30.0, 114.0), shade(CASE, 0.05), r=4.0)
    fuji(reg, *at(-10.0, 119.0), 4.0, shade(CASE, -0.2))
    reg.text("ATARI", "arialbd.ttf", 3.6, *at(-6.0, 119.0), shade(CASE, -0.2), anchor="lm")
    for name, label in (("pause", "PAUSE"), ("option", "OPTION")):
        x, y = L.SMALL[name]
        reg.text(label, "arialbd.ttf", 2.6, *at(x - 4.0, y + 4.0), INK)
    for name in ("a", "b", "c"):
        x, y = L.ABC[name]
        reg.text(name.upper(), "arialbd.ttf", 4.2, *at(x - 9.0, y + 8.0), INK)
    px0, px1, py0, py1 = L.KEYPAD["plate"]
    reg.rect_(*at(px0 - 12.0, py1 + 4.0), *at(px1 + 12.0, 0.0), shade(CASE, 0.03), r=6.0)
    reg.line([at(px0 - 8.0, py1 + 2.0), at(px1 + 8.0, py1 + 2.0)], (8, 8, 9), 0.9)
    reg.rect_(*at(px0, py1), *at(px1, py0), shade(CASE, 0.07), r=2.0)
    labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"]
    (kx0, kx1), (ky0, ky1) = L.KEYPAD["x"], L.KEYPAD["y"]
    for i in range(4):
        for j in range(3):
            x = kx0 + (kx1 - kx0) * j / 2
            y = ky1 - (ky1 - ky0) * i / 3
            reg.text(labels[i * 3 + j], "arial.ttf", 3.0, *at(x, y + 4.6), shade(CASE, -0.35))
    return reg


# ---- The Jaguar CD -----------------------------------------------------------------------------------------------------

def cd():
    r, cy = L.CD["r"], L.CD["at"]
    y0, y1 = cy - r, L.CD["back"][2]
    w, d = 2 * r, y1 - y0
    reg = Region(L.REGIONS["cd"], w, d, CASE)

    def at(x, y):
        return x + w / 2, y1 - y
    lr = L.LID["r"]
    lid = [at(lr * math.cos(math.radians(a)), cy + lr * math.sin(math.radians(a))) for a in range(0, -181, -5)]
    lid += [at(-lr, L.LID["back"]), at(lr, L.LID["back"])]
    reg.poly(lid, shade(CASE, 0.05))
    reg.line(lid + lid[:1], (8, 8, 9), 0.6)
    reg.draw.ellipse(reg.box(*at(-62.0, 150.0), *at(46.0, 66.0)), fill=shade(CASE, 0.1), outline=(10, 10, 11),
                     width=reg.width(0.5))
    for k in range(18):                                        # the crescent window
        t = k / 17
        a = math.radians(200 + 140 * t)
        x, y = -44.0 + 16.0 * math.cos(a), 108.0 + 22.0 * math.sin(a)
        reg.circle(*at(x, y), 3.4 + 1.6 * math.sin(math.pi * t), (150, 160, 176))
    jaguar(reg, *at(8.0, 112.0), 52.0, 14.0, LOGO_RED, cd=True)
    reg.text("CLOSE HERE", "arialbd.ttf", 3.0, *at(-20.0, 46.0), INK)
    reg.text("COMPACT  DIGITAL  MEDIA  PLAYER", "arialbd.ttf", 3.0, *at(18.0, 178.0), INK)
    fuji(reg, *at(10.0, 184.0), 3.6, INK)
    reg.text("ATARI", "arialbd.ttf", 3.2, *at(14.0, 184.0), INK, anchor="lm")
    return reg


# ---- The labels --------------------------------------------------------------------------------------------------------

def disc():
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (20, 20, 24))
    c = dm / 2
    art = space((600, 600)).convert("RGB")
    ship(ImageDraw.Draw(art), 180, 330, 4.0, "#FFFFFF", "#FFB23C")
    mask = Image.new("L", reg.img.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0), fill=255)
    md.ellipse(reg.box(c - 21.0, c - 21.0, c + 21.0, c + 21.0), fill=0)
    x0, y0, x1, y1 = reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.img.paste(layer, (0, 0), mask)
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.text("ODYSSEY", "ariblk.ttf", 11.0, c, c - 36.0, (255, 214, 70))
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (20, 20, 22))
    art = space((900, 460)).convert("RGB")
    ship(ImageDraw.Draw(art), 300, 250, 3.6, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 0.0, lw, lh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 9.0, lw / 2, 9.0, (255, 214, 70))
    jaguar(reg, lw - 16.0, lh - 6.0, 24.0, 6.0, (230, 70, 50))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), pad(), cd(), disc(), label()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", RED), ("dark", (10, 10, 11)), ("grey", (60, 60, 64)), ("silver", (200, 204, 210)),
                         ("window", (150, 160, 176)), ("lit", (255, 60, 40))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "jaguar_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
