"""The Intellivision's printing (intellivision_print.png), for the console theme's model (intellivision.py).

One image, laid out as intellivision_layout.REGIONS says: the console's top from above (the gold strips, MATTEL
ELECTRONICS INTELLIVISION Intelligent Television, RESET and OFF-ON, the docks' band and the vents), its front (the wood
grain), a controller from above (its keypad's twelve keys in their gold frame, the disc's brushed rings), the
cartridge's label (a made-up game, Odyssey), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/intellivision_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intellivision_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

BODY = rgb(L.COLOURS["body"])
GOLD = (204, 178, 132)
GOLD_DARK = (150, 124, 84)
INK = (52, 40, 30)
WOOD = (110, 62, 32)


def brushed(reg, x0, y0, x1, y1, colour, vertical=False):
    """A brushed-metal strip: the colour with fine streaks along it."""
    reg.rect_(x0, y0, x1, y1, colour)
    rng = random.Random(3)
    for _ in range(int((y1 - y0 if not vertical else x1 - x0) * 3)):
        t = rng.uniform(0.0, 1.0)
        shade = tuple(max(0, min(255, c + rng.randint(-14, 12))) for c in colour)
        if vertical:
            x = x0 + (x1 - x0) * t
            reg.line([(x, y0), (x, y1)], shade, 0.15)
        else:
            y = y0 + (y1 - y0) * t
            reg.line([(x0, y), (x1, y)], shade, 0.15)


def wood(size, seed=5):
    """A wood-grain image: warm brown with darker streaks wandering along it."""
    w, h = size
    img = Image.new("RGB", size, WOOD)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    for _ in range(int(h * 1.4)):
        y = rng.uniform(0, h)
        amp, period, phase = rng.uniform(1, h * 0.04), rng.uniform(w * 0.2, w * 0.8), rng.uniform(0, 6.28)
        shade = rng.choice(((74, 38, 18), (92, 50, 24), (128, 76, 40), (66, 34, 16)))
        pts = [(x, y + amp * math.sin(2 * math.pi * x / period + phase)) for x in range(0, w + 6, 6)]
        d.line(pts, fill=shade, width=rng.choice((1, 1, 2, 3)))
    return img.filter(ImageFilter.GaussianBlur(0.6))


# ---- The console -----------------------------------------------------------------------------------------------------

def top():
    """The console from above: x across (-197 at the left), y down from the back (229)."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, BODY)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    half = L.WIDTH / 2
    for y0, y1 in (L.STRIPS["back"], L.STRIPS["front"]):
        brushed(reg, *at(-half + 14.0, y1), *at(half - 14.0, y0), GOLD)
        reg.rect_(*at(-half + 14.0, y1), *at(half - 14.0, y0), None, outline=GOLD_DARK, width=0.5)
    (b0, b1) = L.BAND["y"]
    reg.rect_(*at(-half + 10.0, b1), *at(half - 10.0, b0), (34, 26, 22))
    (v0, v1) = L.VENTS["x"]
    for row in range(2):
        for k in range(14):
            x = v0 + 3.0 + k * (v1 - v0 - 6.0) / 13
            y = b0 + 14.0 + row * 24.0
            reg.rect_(*at(x - 1.0, y + 18.0), *at(x + 1.0, y), (10, 8, 8), r=0.8)
    f0, f1 = L.STRIPS["front"]
    reg.text("MATTEL ELECTRONICS", "arialbd.ttf", 3.6, *at(-170.0, (f0 + f1) / 2 + 4.0), INK, anchor="lm")
    reg.text("INTELLIVISION", "timesbd.ttf", 9.0, *at(-122.0, (f0 + f1) / 2 + 4.0), INK, anchor="lm")
    reg.text("Intelligent Television", "times.ttf", 5.0, *at(-58.0, (f0 + f1) / 2 - 6.0), INK, anchor="lm")
    (rx, ry), (rw, rh) = L.RESET["at"], L.RESET["size"]
    reg.rect_(*at(rx - rw / 2, ry + rh / 2), *at(rx + rw / 2, ry - rh / 2), (40, 30, 24), r=2.0)
    reg.text("RESET", "arial.ttf", 3.0, *at(rx + 6.0, ry + rh / 2 + 3.0), INK)
    (sx, sy), (sw, sh) = L.SWITCH["at"], L.SWITCH["size"]
    reach = sw / 2 + L.SWITCH["travel"] / 2                   # the switch's slot, its whole travel
    reg.rect_(*at(sx - reach, sy + sh / 2), *at(sx + reach, sy - sh / 2), (34, 26, 22), r=2.0)
    reg.text("OFF", "arial.ttf", 3.0, *at(sx - 10.0, sy + sh / 2 + 3.0), INK)
    reg.text("ON", "arial.ttf", 3.0, *at(sx + 10.0, sy + sh / 2 + 3.0), INK)
    return reg


def front():
    """The front: x across, z down from the top (58): the dark rim, the wood grain."""
    reg = Region(L.REGIONS["front"], L.WIDTH, L.TOP, BODY)
    x0, y0, x1, y1 = reg.box(0.0, 8.0, L.WIDTH, 52.0)
    grain = wood((round(x1 - x0), round(y1 - y0)))
    reg.img.paste(grain, (round(x0), round(y0)))
    return reg


# ---- The controller and the cartridge --------------------------------------------------------------------------------

def pad():
    """A controller from above: u along it from its keypad's end (0 at the left), v across (-31 at the top)."""
    length, width = L.PAD["length"], L.PAD["width"]
    reg = Region(L.REGIONS["pad"], length, width, BODY)

    def at(u, v):
        return u, v + width / 2

    (u0, u1), (v0, v1) = L.KEYPAD["u"], L.KEYPAD["v"]
    reg.rect_(*at(u0 - 2.0, v0 - 2.0), *at(u1 + 2.0, v1 + 2.0), GOLD_DARK, r=4.0)
    reg.rect_(*at(u0, v0), *at(u1, v1), (230, 214, 178), r=3.0)
    cols, rows = L.KEYPAD["keys"]
    labels = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["clear", "0", "enter"]]
    pu, pv = (u1 - u0) / rows, (v1 - v0) / cols
    for r in range(rows):
        for c in range(cols):
            cu, cv = u0 + pu * (r + 0.5), v0 + pv * (c + 0.5)
            k = L.KEYPAD["key"] / 2
            reg.rect_(*at(cu - k * 0.9, cv - k), *at(cu + k * 0.9, cv + k), (238, 228, 200), r=2.4,
                      outline=(170, 150, 110), width=0.4)
            text = labels[r][c]
            layer = reg.layer()
            font = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round((5.0 if len(text) == 1 else 2.6) * reg.sx)))
            glyph = Image.new("RGBA", (round(16 * reg.sx), round(16 * reg.sx)), (0, 0, 0, 0))
            ImageDraw.Draw(glyph).text((glyph.width / 2, glyph.height / 2), text, font=font, fill=INK + (255,),
                                       anchor="mm")
            glyph = glyph.rotate(90, resample=Image.BICUBIC)        # the keys read from the controller's cord end
            x, y = reg.p(*at(cu, cv))
            layer.alpha_composite(glyph, (round(x - glyph.width / 2), round(y - glyph.height / 2)))
            reg.over(layer)
    du, r = L.DISC["u"], L.DISC["r"]
    reg.circle(*at(du, 0.0), r + 2.0, (30, 24, 20))
    reg.circle(*at(du, 0.0), r, (196, 176, 140))
    for k in range(1, 9):
        reg.circle(*at(du, 0.0), r * k / 9, None, outline=(176, 156, 120) if k % 2 else (214, 194, 156), width=0.4)
    return reg


def cart():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["cart"], lw, lh, (24, 20, 40))
    art = space((440, 560)).convert("RGB")
    ship(ImageDraw.Draw(art), 140, 320, 3.2, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 12.0, lw, lh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 12.0, (236, 226, 196))
    reg.text("INTELLIVISION", "timesbd.ttf", 5.4, lw / 2, 6.0, INK)
    reg.text("ODYSSEY", "ariblk.ttf", 8.0, lw / 2, 22.0, (255, 214, 70))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BODY)
    for reg in (top(), front(), pad(), cart()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(body=BODY, gold=GOLD, wood=WOOD, dark=(30, 24, 20), key=(238, 228, 200), metal=(196, 176, 140),
                   cart=(40, 34, 30), slot=(8, 6, 6))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "intellivision_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
