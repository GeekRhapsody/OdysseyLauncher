"""The SG-1000 card's printing (sg1000_print.png), for the console theme's SG-1000 model (sg1000.py).

One image, laid out as sg1000_layout.REGIONS says, each region in millimetres as the model's UVs map it: the top's slope
in its own frame (the label: SEGA on its silver ground, the red stripe, the blue band with SG-1000 and Computer Video
Game, its blue frame; power on and hold in red; the cartridge well's grey frame and the grilles' shading), the
cartridge's label (a made-up game from tools/made-up-games: its painting and its logo, SEGA and SG-1000 in the band),
the joystick's top (its stick's recess, the black strip with SEGA and SJ-200), and swatches. Make the made-up games'
library first (tools/made-up-games/README.md), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/sg1000_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screens_print as S  # noqa: E402
import sg1000_layout as L  # noqa: E402
from master_system_print import sega  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region, gradient  # noqa: E402

CASE = rgb(L.COLOURS["case"])
BLUE = rgb(L.COLOURS["blue"])
RED = rgb(L.COLOURS["red"])
WHITE = (248, 248, 246)
GAME = ("spellbrk", "arcade")            # a made-up arcade game of 1980, ported


def italic(reg, text, font, size, x, y, fill, outline=None, anchor="lm", lean=0.22):
    """Text leaning forward, as the SG-1000's lettering does; outlined (hollow) if outline is given."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    if outline is not None:
        d.text(reg.p(x, y), text, font=f, fill=outline + (255,), anchor=anchor, stroke_width=max(1, round(0.35 * reg.sx)),
               stroke_fill=outline + (255,))
    d.text(reg.p(x, y), text, font=f, fill=fill + (255,), anchor=anchor)
    yc = reg.p(0, y)[1]
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, lean, -lean * yc, 0, 1, 0)))


def top():
    """The top's slope: x across (-WIDTH/2 at the left), down from its back edge (s = TOP_LENGTH) to its front."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.TOP_LENGTH, CASE)

    def at(x, s):
        return x + L.WIDTH / 2, L.TOP_LENGTH - s

    # The cartridge well's frame and its slot; the grilles' slats.
    (x0, x1), (s0, s1) = L.WELL["x"], L.WELL["s"]
    reg.rect_(*at(x0, s1), *at(x1, s0), rgb(L.COLOURS["grey"]), r=3.0)
    (x0, x1), (s0, s1) = L.SLOT["x"], L.SLOT["s"]
    reg.rect_(*at(x0, s1), *at(x1, s0), rgb(L.COLOURS["dark"]), r=1.0)
    g = L.GRILLES
    for side in (-1, 1):
        a, b = sorted((side * g["x"][0], side * g["x"][1]))
        reg.rect_(*at(a, g["s"][1]), *at(b, g["s"][0]), shade(CASE, -0.04), r=2.0)
        step = (g["s"][1] - g["s"][0]) / g["slats"]
        for k in range(g["slats"]):
            s = g["s"][0] + (k + 0.5) * step
            reg.rect_(*at(a + 2.0, s + step * 0.22), *at(b - 2.0, s - step * 0.22), shade(CASE, -0.16), r=1.0)

    # The label, its ends angled: its blue frame, the silver ground and SEGA, the red stripe, the blue band and its
    # words.
    (front, back), (s0, s1) = L.LABEL["x"], L.LABEL["s"]

    def half(s):                                           # the label's half width at s
        return front + (back - front) * (s - s0) / (s1 - s0)

    def quad(a, b, inset=0.0):
        return [at(-half(a) + inset, a), at(half(a) - inset, a), at(half(b) - inset, b), at(-half(b) + inset, b)]
    reg.poly(quad(s0, s1), BLUE)
    silver = gradient((round(reg.sx * 2 * front), round(reg.sy * (s1 - s0))),
                      [(0.0, (250, 250, 250)), (0.55, (222, 224, 226)), (1.0, (236, 238, 240))])
    mask = Image.new("L", reg.img.size, 0)
    ImageDraw.Draw(mask).polygon([reg.p(*q) for q in quad(s0 + 1.2, s1 - 1.2, 1.2)], fill=255)
    layer = reg.layer()
    a, b = reg.p(*at(-front, s1))
    layer.paste(silver, (round(a), round(b)))
    layer.putalpha(mask)
    reg.over(layer)
    band = (s0 + 1.2, s0 + 11.0)
    reg.poly(quad(band[1], band[1] + 2.8, 1.2), RED)
    reg.poly(quad(band[0], band[1], 1.2), BLUE)
    sega(reg, *at(0.0, s1 - 10.5), 14.0, BLUE, outline=WHITE, anchor="mm")
    italic(reg, "SG-1000", "ariblk.ttf", 6.4, *at(-front + 7.0, (band[0] + band[1]) / 2 + 0.4), BLUE, outline=RED)
    italic(reg, "Computer Video Game", "arialbd.ttf", 5.0, *at(-front + 50.0, (band[0] + band[1]) / 2 - 0.4), WHITE)

    # power on and its light; hold over HOLD.
    reg.text("power on", "arial.ttf", 2.4, *at(L.LIGHT["x"], L.LIGHT["s"] + 2.8), RED)
    lw, lh = L.LIGHT["size"]
    reg.rect_(*at(L.LIGHT["x"] - lw / 2, L.LIGHT["s"] + lh / 2), *at(L.LIGHT["x"] + lw / 2, L.LIGHT["s"] - lh / 2),
              (60, 30, 28), r=0.5)
    (x0, x1), (s0, s1) = L.HOLD["x"], L.HOLD["s"]
    reg.text("hold", "arial.ttf", 2.6, *at((x0 + x1) / 2 + 3.0, s1 + 3.0), RED)
    return reg


def label(made_up):
    """The cartridge's label: the made-up game's painting, its logo over it, the band under it."""
    lw, lh, _ = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (20, 20, 22))
    game = S.made_up(*GAME, made_up)
    a, b, c, d = reg.box(1.5, 1.5, lw - 1.5, lh - 11.0)
    reg.img.paste(ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS), (round(a), round(b)))
    k = min((c - a) * 0.8 / game.logo.width, (d - b) * 0.36 / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(logo, (round((a + c - logo.width) / 2), round(b + (d - b) * 0.06)))
    reg.rect_(0.0, lh - 9.5, lw, lh, BLUE)
    sega(reg, 3.0, lh - 4.8, 5.0, WHITE)
    reg.text("SG-1000  SC-3000", "arialbd.ttf", 2.8, lw - 3.0, lh - 4.8, WHITE, anchor="rm")
    return reg


def stick():
    """The joystick's top: x across, down from its top end (where the cable leaves) to its foot."""
    w, length, _, _ = L.STICK["size"]
    reg = Region(L.REGIONS["stick"], w, length, rgb(L.COLOURS["stick_top"]))
    r = L.STICK["recess"]
    reg.circle(w / 2, r["v"], r["ring"], shade(rgb(L.COLOURS["stick_top"]), -0.18))
    reg.circle(w / 2, r["v"], r["ring"] - 1.2, shade(rgb(L.COLOURS["stick_top"]), 0.06))
    reg.circle(w / 2, r["v"], r["r"], shade(rgb(L.COLOURS["stick_top"]), -0.08))
    s0, s1 = L.STICK["strip"]                               # the black band with SEGA, the white one with SJ-200
    reg.rect_(2.0, s0, w - 2.0, s1, rgb(L.COLOURS["black"]), r=1.0)
    sega(reg, w / 2, (s0 + s1) / 2, 8.4, (60, 140, 230), anchor="mm")
    b0, b1 = L.STICK["band"]
    reg.rect_(2.0, b0, w - 2.0, b1, (236, 236, 232))
    reg.text("SJ-200", "arialbd.ttf", 3.6, w / 2, (b0 + b1) / 2, (20, 20, 20))
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), label(made_up), stick()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, base=rgb(L.COLOURS["base"]), grey=rgb(L.COLOURS["grey"]), dark=rgb(L.COLOURS["dark"]),
                   black=rgb(L.COLOURS["black"]), red=RED, lit=(255, 70, 50), stick_top=rgb(L.COLOURS["stick_top"]),
                   stick_base=rgb(L.COLOURS["stick_base"]), cart=(28, 28, 30))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "sg1000_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
