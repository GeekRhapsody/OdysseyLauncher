"""The TI-99/4A card's printing (ti99_print.png), for the console theme's model (ti99.py).

One image, laid out as ti99_layout.REGIONS says: the aluminium from above (brushed; the vents, Texas Instruments and its
mark, TI-99/4A computer, the black keyboard surround with the strip over the keys and the keys' tops and legends, the
black module bay with Solid State Software), the command module's top (its label: a made-up game, Odyssey), and
swatches. Run it with the system Python (Pillow):

    python tools/console-models/ti99_print.py <out folder>
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ti99_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

ALU = rgb(L.COLOURS["alu"])
KEY = rgb(L.COLOURS["key"])
BLACK = (24, 24, 26)
WHITE = (236, 236, 232)
INK = (40, 40, 42)
STRIP = (214, 214, 208)


def mark(reg, x, y, h, ink):
    """Texas Instruments' mark, h tall, its middle at (x, y): Texas's outline, its panhandle up, a hole for the ti."""
    k = h / 10.0
    outline = [(-2.2, -5.0), (-0.6, -5.0), (-0.6, -2.0), (4.4, -2.0), (5.0, 0.6), (3.4, 2.2), (2.0, 5.0), (0.4, 3.0),
               (-1.6, 3.2), (-3.0, 1.0), (-5.0, 0.6), (-4.0, -1.2), (-2.2, -1.2)]
    reg.poly([(x + px * k, y + py * k) for px, py in outline], ink)
    reg.text("ti", "arialbd.ttf", 3.6 * k, x + 1.0 * k, y + 0.4 * k, ALU)


def spaced(reg, s, name, size, x, y, fill, gap):
    """Text along from x, each letter gap apart (small capitals: the first a size bigger)."""
    for k, c in enumerate(s):
        reg.text(c, name, size * (1.25 if k == 0 or s[k - 1] == " " else 1.0), x + k * gap, y, fill, anchor="ls")


def top():
    """The aluminium from above: x across (-WIDTH/2 at the left), y down from the back to the front."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, ALU)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    rng = random.Random(7)
    y = 0.0
    while y < L.DEPTH:                                                  # the brushed grain
        tone = rng.randint(-14, 12)
        reg.line([at(-L.WIDTH / 2, y), at(L.WIDTH / 2, y)], tuple(c + tone for c in ALU), 0.18)
        y += rng.uniform(0.25, 0.7)
    (vx0, vx1), (vy0, vy1), n, vw = L.VENTS["x"], L.VENTS["y"], L.VENTS["count"], L.VENTS["width"]
    for k in range(n):
        vy = vy0 + (vy1 - vy0) * k / (n - 1)
        reg.rect_(*at(vx0, vy + vw / 2), *at(vx1, vy - vw / 2), (18, 18, 20), r=vw / 2)
    lx, ly = L.LOGO["at"]
    mark(reg, *at(lx + 3.0, ly + 1.2), 7.0, INK)
    spaced(reg, "TEXAS INSTRUMENTS", "times.ttf", 3.8, *at(lx + 9.0, ly - 0.6), INK, 4.6)
    mx, my = L.LOGO["model"]
    reg.text("TI-99/", "arialbd.ttf", 7.6, *at(mx, my), INK, anchor="ls")
    wide = reg.draw.textlength("TI-99/", font=ImageFont.truetype(FONTS + "arialbd.ttf", round(7.6 * reg.sx))) / reg.sx
    reg.text("4A", "arial.ttf", 7.6, *at(mx + wide + 0.4, my), (96, 96, 98), anchor="ls")
    reg.text("computer", "arial.ttf", 3.0, *at(mx + 4.0, my - 4.6), INK, anchor="ls")

    (sx0, sx1), (sy0, sy1) = L.SURROUND["x"], L.SURROUND["y"]
    reg.rect_(*at(sx0, sy1), *at(sx1, sy0), BLACK, r=L.SURROUND["r"])
    (tx0, tx1), (ty0, ty1) = L.STRIP["x"], L.STRIP["y"]
    reg.rect_(*at(tx0, ty1), *at(tx1, ty0), STRIP, r=0.6)
    for k, word in enumerate(L.OVERLAY):
        x0 = L.KEYS_X0 + k * L.U
        if k:
            reg.line([at(x0, ty1 - 0.4), at(x0, ty0 + 0.4)], (150, 150, 146), 0.25)
        reg.text(word, "arial.ttf", 2.3, *at(x0 + L.U / 2, (ty0 + ty1) / 2), INK)
    lx, ly = L.STRIP["light"]
    reg.circle(*at(lx, ly), 1.3, (110, 26, 22))

    top_h = L.KEY["height"]
    inset = L.KEY["inset"]
    for legend, x0, x1, s in L.keys():
        ya = L.deck_point(s - 9.5 + inset, top_h)[0]
        yb = L.deck_point(s + 9.5 - inset, top_h)[0]
        reg.rect_(*at(x0 + inset, yb), *at(x1 - inset, ya), KEY, r=1.2)
        x, y = at((x0 + x1) / 2, (ya + yb) / 2)
        if legend in L.SHIFTED:
            reg.text(L.SHIFTED[legend], "arial.ttf", 3.2, x - 1.2, y - 2.6, WHITE)
            reg.text("Ø" if legend == "0" else legend, "arial.ttf", 4.0, x - 1.2, y + 2.4, WHITE)
        elif len(legend) == 1 and legend != " ":
            reg.text(legend, "arial.ttf", 4.6, x - 1.4, y, WHITE)
        elif legend == "ALPHA LOCK":
            reg.text("ALPHA", "arialbd.ttf", 2.0, x, y - 1.3, WHITE)
            reg.text("LOCK", "arialbd.ttf", 2.0, x, y + 1.3, WHITE)
        elif legend.strip():
            reg.text(legend, "arialbd.ttf", 2.1, x, y, WHITE)

    (bx0, bx1), (by0, by1) = L.BAY["x"], L.BAY["y"]
    reg.rect_(*at(bx0, by1), *at(bx1, by0), BLACK, r=4.0)
    ly0, ly1 = L.BAY["landing"]
    reg.rect_(*at(bx0 + 6.0, ly1), *at(bx1 - 6.0, ly0), (34, 34, 36), r=2.0)
    (lx0, lx1), (lz0, lz1) = L.BAY["label"]
    reg.rect_(*at(lx0, lz1), *at(lx1, lz0), None, r=0.8, outline=(120, 120, 118), width=0.3)
    reg.text("Solid State Software", "arial.ttf", 3.4, *at((lx0 + lx1) / 2, (lz0 + lz1) / 2), (200, 200, 196))
    return reg


def module():
    """The command module's top: x across, y down from its back edge to its front; its label at the front."""
    w, length, _ = L.MODULE["size"]
    reg = Region(L.REGIONS["module"], w, length, (46, 46, 48))
    reg.rect_(6.0, 40.0, w - 6.0, length - 3.0, (20, 20, 22), r=1.5)        # the label, in the part left showing
    art = space((440, 160)).convert("RGB")
    ship(ImageDraw.Draw(art), 120, 82, 2.2, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(9.0, 61.0, w - 9.0, length - 5.5)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("COMMAND MODULE", "arial.ttf", 3.0, 9.0, 45.0, (200, 200, 196), anchor="lm")
    reg.text("ODYSSEY", "ariblk.ttf", 7.4, w / 2, 54.0, (240, 96, 40))
    mark(reg, w - 13.0, 45.0, 6.0, (200, 200, 196))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), ALU)
    for reg in (top(), module()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(alu=ALU, black=BLACK, key=KEY, dark=(8, 8, 8), orange=(240, 96, 40), light=(255, 40, 30),
                   module=(46, 46, 48))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "ti99_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
