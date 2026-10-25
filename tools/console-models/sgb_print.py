"""The Super Game Boy's front and the Game Boy cartridge's label (sgb_print.png), for the console theme's Super Game Boy
card (sgb.py), whose Super Nintendo is snes.py's (its printing is snes_print.py's).

One image, laid out as sgb_layout.REGIONS says: the adapter's front (the side ridges, the Nintendo emblem, the label
with Super GAME BOY and the SUPER NES mark, the grip), the Game Boy cartridge's front (its ridges, the label: Nintendo
GAME BOY over a made-up game, Odyssey), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/sgb_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgb_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

GREY = rgb(L.COLOURS["sgb"])
LINE = (160, 160, 166)
INK = (60, 60, 70)
RED = (214, 40, 46)
BLUE = (52, 52, 150)


def snes_mark(reg, cx, cy, r):
    """The SUPER NES mark: four coloured dots in a ring."""
    reg.circle(cx, cy, r, (236, 236, 238), outline=INK, width=r * 0.12)
    for (dx, dy), colour in (((0, -1), (60, 140, 60)), ((1, 0), (216, 40, 50)), ((0, 1), (240, 200, 40)),
                             ((-1, 0), (60, 90, 190))):
        reg.circle(cx + dx * r * 0.45, cy + dy * r * 0.45, r * 0.24, colour)


def nintendo(reg, cx, cy, w, h, colour):
    reg.rect_(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, None, r=h / 2, outline=colour, width=h * 0.12)
    reg.text("Nintendo", "arialbd.ttf", h * 0.6, cx, cy, colour)


def front():
    """The adapter's front: x across (-67 at the left), z down from its top (118)."""
    w, h = L.SGB["width"], L.SGB["height"]
    reg = Region(L.REGIONS["front"], w, h, GREY)

    def at(x, z):
        return x + w / 2, h - z

    for side in (-1, 1):                                       # the side ridges
        for k in range(9):
            z = 14.0 + k * 9.0
            x0, x1 = sorted((side * (w / 2 - 2.0), side * (w / 2 - 15.0)))
            reg.rect_(*at(x0, z + 1.4), *at(x1, z - 1.4), (176, 176, 180), r=0.6)
    nintendo(reg, *at(0.0, L.EMBLEM["z"]), *L.EMBLEM["size"], (140, 140, 146))
    (z0, z1), lw = L.LABEL["z"], L.LABEL["width"]
    reg.rect_(*at(-lw / 2, z1), *at(lw / 2, z0), (232, 232, 234), r=4.0, outline=LINE, width=0.4)
    reg.text("Super", "segoescb.ttf", 7.5, *at(-24.0, z1 - 9.0), RED)
    reg.text("GAME BOY", "ariblk.ttf", 10.0, *at(-8.0, z0 + 9.0), BLUE)
    snes_mark(reg, *at(36.0, (z0 + z1) / 2 + 2.0), 7.0)
    reg.text("SUPER NES", "arialbd.ttf", 2.6, *at(36.0, z0 + 4.0), INK)
    (g0, g1), gw = L.GRIP["z"], L.GRIP["width"]
    reg.rect_(*at(-gw / 2, g1), *at(gw / 2, g0), None, r=3.0, outline=LINE, width=0.6)
    reg.rect_(*at(-14.0, g1 - 4.0), *at(14.0, g0 + 2.0), None, r=2.0, outline=LINE, width=0.5)
    return reg


def gb():
    """The Game Boy cartridge's front: x across (-28.5 at the left), z down from its top (65)."""
    w, h = L.GB["width"], L.GB["height"]
    reg = Region(L.REGIONS["gb"], w, h, rgb(L.COLOURS["gb"]))

    def at(x, z):
        return x + w / 2, h - z

    for k in range(5):                                         # the grip's ridges along the top
        reg.rect_(*at(-20.0, 62.5 - k * 1.6), *at(20.0, 62.0 - k * 1.6), (120, 120, 126))
    x0, z1, x1, z0 = -23.5, 54.0, 23.5, 10.0
    reg.rect_(*at(x0, z1), *at(x1, z0), (40, 40, 46), r=1.0)
    art = space((380, 300)).convert("RGB")
    ship(ImageDraw.Draw(art), 120, 170, 2.6, "#FFFFFF", "#FFB23C")
    a, b, c, d = reg.box(*at(x0 + 1.0, z1 - 7.0), *at(x1 - 1.0, z0 + 1.0))
    reg.img.paste(art.resize((round(c - a), round(d - b)), Image.LANCZOS), (round(a), round(b)))
    reg.rect_(*at(x0 + 1.0, z1 - 1.0), *at(x1 - 1.0, z1 - 7.0), (226, 226, 228))
    reg.text("Nintendo GAME BOY", "arialbd.ttf", 3.0, *at(0.0, z1 - 4.0), INK)
    reg.text("ODYSSEY", "ariblk.ttf", 6.0, *at(0.0, z1 - 12.0), (255, 214, 70))
    reg.poly([at(-4.0, 6.0), at(4.0, 6.0), at(0.0, 2.0)], (120, 120, 126))   # the arrow pointing in
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), GREY)
    for reg in (front(), gb()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(sgb=GREY, gb=rgb(L.COLOURS["gb"]), dark=(12, 12, 14))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "sgb_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
