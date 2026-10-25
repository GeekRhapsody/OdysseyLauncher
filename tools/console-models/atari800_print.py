"""The Atari 800 card's printing (atari800_print.png), for the console theme's model (atari800.py).

One image, laid out as atari800_layout.REGIONS says: the keyboard deck from above (the keys' tops and legends, the
function keys', the power light's), the lid's front face (the ATARI 800 plate), the front of the ports' block (the four
joystick ports), the bay's back wall (its LEFT CARTRIDGE / RIGHT CARTRIDGE plate), the cartridge's front (its label: a
made-up game, Odyssey), and swatches; the joystick's top (atari_2600_print.py's) and its red where atari_2600_layout.py
puts them. Run it with the system Python (Pillow):

    python tools/console-models/atari800_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari800_layout as L  # noqa: E402
import atari_2600_layout as AL  # noqa: E402
from atari5200_print import fuji  # noqa: E402
from atari_2600_print import stick_top  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
LEGEND = (236, 232, 222)
BROWN = (84, 62, 46)
INK = (62, 54, 48)
PLATE = (204, 198, 184)
METAL = (168, 170, 172)
CART = (58, 52, 48)
FUNCTION = dict(reset=(190, 118, 44), option=(226, 148, 36), select=(238, 172, 32), start=(244, 192, 40))


def outlined(reg, s, name, size, x, y, ink, fill, width, anchor="lm"):
    """Text drawn hollow: its letters' outlines in ink, filled with fill."""
    f = ImageFont.truetype(FONTS + name, max(1, round(size * reg.sy)))
    reg.draw.text(reg.p(x, y), s, font=f, fill=fill, anchor=anchor, stroke_width=reg.width(width), stroke_fill=ink)


def deck():
    """The deck from above: x across (-200 at the left), y down from where it meets the housing (DECK_BACK) to the
    front."""
    y_back = L.DECK_BACK[0]
    reg = Region(L.REGIONS["deck"], L.WIDTH, y_back, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, y_back - y

    def top(x0, x1, s, half, h, fill):
        """A key's top, half its foot's depth along the slope, h its height; returns its middle."""
        inset = L.KEY["inset"]
        ya, yb = L.deck_point(s - half - 0.5 + inset, h)[0], L.deck_point(s + half + 0.5 - inset, h)[0]
        reg.rect_(*at(x0 + inset, yb), *at(x1 - inset, ya), fill, r=1.4)
        return (x0 + x1) / 2, (ya + yb) / 2

    for legend, x0, x1, s in L.keys():
        x, y = top(x0, x1, s, 9.0, L.KEY["height"], KEY)
        if legend == "ATARI":
            fuji(reg, *at(x, y), 5.0, LEGEND)
        elif legend.strip():
            reg.text(legend, "arialbd.ttf", 4.2 if len(legend) == 1 else 2.0, *at(x, y), LEGEND)
    fx0, fx1 = L.FUNCTION["x"]
    for legend, s, name in L.FUNCTION["keys"]:
        x, y = top(fx0, fx1, s, 8.5, L.KEY["height"], FUNCTION[name])
        lines = legend.split(" ")
        for k, line in enumerate(lines):
            reg.text(line, "arialbd.ttf", 2.2, *at(x, y + (len(lines) - 1) * 1.3 - k * 2.6), BROWN)
    x, y = top(fx0, fx1, L.LIGHT["s"], L.LIGHT["half"], L.LIGHT["height"], (206, 200, 188))
    reg.rect_(*at(x - 7.0, y + 1.6), *at(x + 7.0, y - 1.6), (70, 30, 26), r=0.6)
    return reg


def badge():
    """The lid's front face from in front: x across from the lid's left edge, z down from its top."""
    (x0, x1), h = L.LID["x"], L.HEIGHT - L.DECK_BACK[1]
    reg = Region(L.REGIONS["badge"], x1 - x0, h, CASE)

    def at(x, z):
        return x - x0, L.HEIGHT - z

    (fx0, fx1), (px0, px1), (z0, z1) = L.BADGE["fuji"], L.BADGE["plate"], L.BADGE["z"]
    middle = (z0 + z1) / 2
    reg.rect_(*at(fx0, z1 + 0.5), *at(fx1, z0 - 0.5), INK, r=1.0)
    fuji(reg, *at((fx0 + fx1) / 2, middle), 15.0, (226, 224, 216))
    reg.rect_(*at(px0, z1), *at(px1, z0), PLATE, r=0.8, outline=(176, 170, 156), width=0.4)
    reg.text("ATARI", "arialbd.ttf", 15.0, *at(px0 + 7.0, middle), INK, anchor="lm")
    outlined(reg, "800", "arialbd.ttf", 15.0, *at(px0 + 57.0, middle), (150, 96, 64), PLATE, 0.6)
    return reg


def ports():
    """The front of the ports' block: x across, z down from the shell's underside."""
    (bx0, bx1), z1 = L.PORTS["block"], L.BASE
    reg = Region(L.REGIONS["ports"], bx1 - bx0, z1, CASE)

    def at(x, z):
        return x - bx0, z1 - z

    pw, ph = L.PORTS["size"]
    z = L.PORTS["z"]
    for k, x in enumerate(L.PORTS["x"]):
        reg.rect_(*at(x - pw / 2, z + ph / 2), *at(x + pw / 2, z - ph / 2), (44, 40, 36), r=1.4)
        reg.rect_(*at(x - pw / 2 + 2.0, z + ph / 2 - 1.6), *at(x + pw / 2 - 2.0, z - ph / 2 + 1.6), (10, 10, 10), r=0.8)
        reg.text(str(k + 1), "arialbd.ttf", 2.6, *at(x + pw / 2 + 3.0, z), (120, 112, 96))
    return reg


def plate():
    """The bay's back wall: x across from the bay's left edge, z down from the deck's back edge; the metal, its dark
    plate."""
    (bx0, bx1), h = L.BAY["x"], L.DECK_BACK[1] - L.BAY["floor"]
    reg = Region(L.REGIONS["plate"], bx1 - bx0, h, METAL)

    def at(x, z):
        return x - bx0, L.DECK_BACK[1] - z

    mid = (bx0 + bx1) / 2
    reg.rect_(*at(bx0 + 7.0, 76.0), *at(bx1 - 7.0, 62.0), (34, 32, 30), r=1.0)
    for x0, x1, s in ((bx0 + 10.0, mid - 20.0, "«LEFT CARTRIDGE"), (mid + 20.0, bx1 - 10.0, "RIGHT CARTRIDGE»")):
        reg.rect_(*at(x0, 73.5), *at(x1, 64.5), None, r=1.0, outline=(150, 148, 142), width=0.4)
        reg.text(s, "arial.ttf", 5.0, *at((x0 + x1) / 2, 69.0), (196, 194, 188))
    fuji(reg, *at(mid, 70.6), 6.0, (196, 194, 188))
    reg.text("ATARI", "arialbd.ttf", 2.8, *at(mid, 65.4), (196, 194, 188))
    return reg


def cart():
    """The cartridge's front: x across from its left edge, y down from its top; LEFT CARTRIDGE over the label."""
    (w, t, h), (lw, lh), top = L.CART["size"], L.CART["label"], L.CART["top"]
    reg = Region(L.REGIONS["cart"], w, h, CART)
    x0 = (w - lw) / 2
    art = space((440, 283)).convert("RGB")
    ship(ImageDraw.Draw(art), 140, 170, 3.0, "#FFFFFF", "#FFB23C")
    bx0, by0, bx1, by1 = reg.box(x0, top + 10.0, x0 + lw, top + lh)
    reg.img.paste(art.resize((round(bx1 - bx0), round(by1 - by0)), Image.LANCZOS), (round(bx0), round(by0)))
    reg.rect_(x0, top, x0 + lw, top + 10.0, (236, 228, 208))
    reg.text("ODYSSEY", "ariblk.ttf", 6.0, w / 2, top + 5.0, (62, 48, 40))
    reg.text("«LEFT CARTRIDGE", "arial.ttf", 2.6, w / 2, top / 2, (150, 142, 132))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (deck(), badge(), ports(), plate(), cart(), stick_top()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    x, y = AL.SWATCHES["red"]
    d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=(200, 30, 26))
    colours = dict(case=CASE, key=KEY, dark=(14, 13, 12), metal=METAL, cart=CART, black=(22, 22, 24),
                   light=(206, 200, 188), vent=(112, 104, 90), **FUNCTION)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "atari800_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
