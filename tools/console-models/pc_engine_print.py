"""The PC Engine's printing, for the console theme's PC Engine model (tools/console-models/pc_engine.py).

Draws its atlas, its regions as pc_engine_layout.py places them, each in millimetres as the model's planar UVs map it:
the console seen from above (PC Engine's red logo behind the slot, the grilles on the front corners, AC ADAPTER and AV
SWITCH outlined, NEC, POWER's OFF and ON, the channel's ribs); its front face (the pad's socket); the HuCard's face
(the contacts' black end, a made-up game's label, Odyssey); the pad's top (the dark face plate, the red arc round the
D-pad, SELECT and RUN, II and I in their red frames, NEC PI-PD001); and the swatches small parts take their colour
from. Run it with the system Python (Pillow):

    python tools/console-models/pc_engine_print.py <out folder>

It writes pc_engine_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc_engine_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
DARK = rgb(L.COLOURS["dark"])
RED = (226, 82, 64)
PLATE = rgb(L.COLOURS["plate"])
EMBOSS = shade(CASE, -0.12)


def logo(reg, x, y, s):
    """PC Engine's logo, s across, its middle at (x, y): PC over Engine in red, outlined, in a red oval."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    d.ellipse(reg.box(x - s / 2, y - s * 0.17, x + s / 2, y + s * 0.17), outline=RED + (255,),
              width=max(1, round(s * 0.012 * reg.sx)))
    big = ImageFont.truetype(FONTS + "arialbi.ttf", max(1, round(s * 0.2 * reg.sx)))
    for text, ty, tx in (("PC", y - s * 0.1, x - s * 0.08), ("Engine", y + s * 0.07, x + s * 0.02)):
        d.text(reg.p(tx, ty), text, font=big, fill=(255, 255, 255, 255), anchor="mm",
               stroke_width=max(1, round(s * 0.012 * reg.sx)), stroke_fill=RED + (255,))
    reg.over(layer)


def grille(reg, x0, y0, x1, y1, n):
    for k in range(n):
        y = y0 + (y1 - y0) * (k + 0.5) / n
        reg.line([(x0, y), (x1, y)], EMBOSS, 0.9)


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    logo(reg, *at(4.0, 92.0), 52.0)
    for x0, x1 in ((-60.0, -36.0), (36.0, 60.0)):           # the grilles on the front corners
        (a, b), (c, e) = at(x0, 42.0), at(x1, 28.0)
        grille(reg, a, b, c, e, 5)
    for x0, x1, word in ((-62.0, -38.0, "AC ADAPTER"), (38.0, 62.0, "AV SWITCH")):
        (a, b), (c, e) = at(x0, 124.0), at(x1, 98.0)
        reg.rect_(a, b, c, e, None, r=3.0, outline=EMBOSS, width=0.5)
        reg.text(word, "arialbd.ttf", 2.6, (a + c) / 2, (b + e) / 2, EMBOSS)
    reg.text("NEC", "timesbd.ttf", 4.4, *at(-56.0, 132.0), EMBOSS)
    reg.text("POWER", "arialbd.ttf", 2.4, *at(-52.0, 18.0), EMBOSS)
    reg.text("OFF   ON", "arialbd.ttf", 2.0, *at(-52.0, 13.0), EMBOSS)
    for k in range(6):                                       # the channel's ribs, running back
        x = -22.0 + 8.8 * k
        reg.line([at(x, 20.0), at(x, 52.0)], shade(CASE, -0.07), 0.5)
    return reg


def front():
    reg = Region(L.REGIONS["front"], L.WIDTH, L.HEIGHT, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z
    px, pz, r = L.PORT["x"], L.PORT["z"], L.PORT["r"]
    reg.circle(*at(px, pz), r + 1.8, shade(CASE, 0.05), outline=shade(CASE, -0.2), width=0.4)
    reg.circle(*at(px, pz), r, DARK)
    for k in range(8):
        a = 2 * math.pi * k / 8
        reg.circle(*at(px + 3.0 * math.cos(a), pz + 3.0 * math.sin(a)), 0.5, (150, 130, 80))
    reg.text("PAD", "arialbd.ttf", 2.2, *at(px, pz + r + 4.0), EMBOSS)
    return reg



def card():
    w, length = L.CARD["size"]
    reg = Region(L.REGIONS["card"], w, length, (246, 246, 244))
    reg.rect_(0.0, 0.0, w, 28.0, DARK, r=1.2)
    for k in range(38):                                      # the contacts, along the end that goes in
        x = 3.0 + k * (w - 6.0) / 38
        reg.rect_(x, 1.4, x + 0.8, 6.0, (196, 160, 70))
    art = space((520, 400))
    d = ImageDraw.Draw(art)
    ship(d, 160, 230, 2.8, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(3.0, 31.0, w - 3.0, length - 14.0)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 7.2, w / 2, 38.0, (255, 214, 70))
    reg.rect_(3.0, length - 13.0, w - 3.0, length - 3.0, (206, 34, 40))
    reg.text("HuCARD", "arialbi.ttf", 4.6, w / 2, length - 8.0, (255, 255, 255))
    return reg


def pad():
    pw, pd, _ = L.PAD["size"]
    reg = Region(L.REGIONS["pad"], pw, pd, rgb(L.COLOURS["pad"]))
    p = L.PAD

    def at(x, y):
        return x + pw / 2, pd / 2 - y
    x0, x1, y0, y1 = p["plate"]
    reg.rect_(*at(x0, y1), *at(x1, y0), PLATE, r=4.0)
    reg.circle(*at(0.0, p["dome"]["y"]), p["dome"]["r"] + 1.5, rgb(L.COLOURS["pad"]))   # the dome cuts into it
    dx, dy, span, _ = p["dpad"]
    layer = reg.layer()
    ImageDraw.Draw(layer).arc(reg.box(*at(dx - 21.0, dy + 21.0), *at(dx + 21.0, dy - 21.0)), 196, 410,
                              fill=RED + (255,), width=max(1, round(1.2 * reg.sx)))
    reg.over(layer)
    reg.circle(*at(dx, dy), span / 2 + 2.5, shade(PLATE, -0.25))
    pw_, ph_ = p["pill"]
    for (x, y), word in ((p["select"], "SELECT"), (p["run"], "RUN")):
        reg.rect_(*at(x - pw_ / 2 - 1.2, y + ph_ / 2 + 1.2), *at(x + pw_ / 2 + 1.2, y - ph_ / 2 - 1.2), (238, 238, 236),
                  r=ph_ / 2 + 1.2)
        reg.text(word, "arialbd.ttf", 3.2, *at(x, y - 7.0), RED)
    (xa, ya), (xb, _) = p["ii"], p["i"]
    reg.rect_(*at(xa - 10.5, ya + 10.5), *at(xb + 10.5, ya - 10.5), RED, r=10.5)      # the red frame round both
    for (x, y), word in ((p["ii"], "II"), (p["i"], "I")):
        reg.circle(*at(x, y), p["button_r"] + 0.9, shade(PLATE, -0.3))
        reg.rect_(*at(x - 3.0, y + 19.0), *at(x + 3.0, y + 12.5), RED)
        reg.poly([at(x - 3.6, y + 19.0), at(x + 3.6, y + 19.0), at(x, y + 22.0)], RED)
        reg.text(word, "timesbd.ttf", 4.0, *at(x, y + 15.8), (238, 238, 236))
    reg.text("NEC", "timesbd.ttf", 4.6, *at(-50.0, 13.0), RED)
    reg.text("PI-PD001", "arialbi.ttf", 3.0, *at(-36.0, 13.0), (238, 238, 236), anchor="lm")
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), card(), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("green", rgb(L.COLOURS["green"])), ("grey", (112, 114, 118)), ("dark", DARK),
                         ("red", RED), ("white", (240, 240, 238))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "pc_engine_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
