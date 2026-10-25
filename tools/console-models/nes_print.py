"""The NES card's printing (nes_print.png), for the console theme's model (nes.py).

One image, laid out as nes_layout.REGIONS says: the console from above (the band's black ends and the ribs' shadows
between, the upper body's edges), its front (Nintendo ENTERTAINMENT SYSTEM on the door, POWER and RESET, the band, 1 and
2), the controller from above (its black face, the cross, the grey stripes with SELECT and START, B and A, Nintendo),
the cartridge's top (its ribs and its label: a made-up game, Odyssey), and swatches. Run it with the system Python
(Pillow):

    python tools/console-models/nes_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nes_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
BASE = (124, 122, 122)
BLACK = (30, 30, 32)
RED = (200, 36, 36)
GREY = (150, 150, 150)


def shade(colour, k):
    return tuple(max(0, min(255, round(c * (1 + k)))) for c in colour)


def top():
    """The console from above: x across (-WIDTH/2 at the left), y down from the back to the front."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    (bx0, bx1) = L.BAND["x"]
    reg.rect_(*at(bx0, L.BAND["front"]), *at(bx1, 0.0), BLACK)
    reg.rect_(*at(bx0, L.DEPTH), *at(bx1, L.DEPTH - L.BAND["back"]), BLACK)
    reg.rect_(*at(bx0, L.DEPTH - L.BAND["back"]), *at(bx1, L.BAND["front"]), shade(CASE, -0.08))
    (ry0, ry1), n, w = L.RIBS["y"], L.RIBS["count"], L.RIBS["width"]
    for k in range(n):                                       # the shadows between the ribs
        y = ry0 + (ry1 - ry0) * (k + 0.5) / n
        reg.rect_(*at(bx0 + 1.0, y - w / 2 - 1.2), *at(bx1 - 1.0, y - w / 2 - 3.0), shade(CASE, -0.3))
    return reg


def front():
    """The front from in front: x across, z down from the top."""
    reg = Region(L.REGIONS["front"], L.WIDTH, L.HEIGHT, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z

    reg.rect_(*at(-L.WIDTH / 2, L.BASE["top"]), *at(L.WIDTH / 2, 0.0), BASE)
    (bx0, bx1) = L.BAND["x"]
    reg.rect_(*at(bx0, L.HEIGHT), *at(bx1, 0.0), BLACK)
    (dx0, dx1), (dz0, dz1) = L.DOOR["x"], L.DOOR["z"]
    reg.text("Nintendo", "arialbd.ttf", 7.0, *at(dx0 + 6.0, dz1 - 12.0), RED, anchor="lm")
    reg.text("ENTERTAINMENT SYSTEM", "arial.ttf", 4.0, *at(dx0 + 6.0, dz1 - 19.0), RED, anchor="lm")
    reg.rect_(*at((dx0 + dx1) / 2 - 12.0, dz0 + 2.4), *at((dx0 + dx1) / 2 + 12.0, dz0 + 1.2), shade(CASE, -0.15),
              r=0.6)
    for name, (x, z) in (("POWER", L.BUTTONS["power"]), ("RESET", L.BUTTONS["reset"])):
        w, h, _ = L.BUTTONS["size"]
        reg.rect_(*at(x - w / 2 - 1.0, z + h / 2 + 1.0), *at(x + w / 2 + 1.0, z - h / 2 - 1.0), shade(BASE, -0.2))
        reg.text(name, "arialbd.ttf", 3.6, *at(x, z), RED)
    lx, lz = L.LIGHT["at"]
    reg.rect_(*at(lx - 3.0, lz + 3.0), *at(lx + 3.0, lz - 3.0), (40, 40, 42))
    (pz0, pz1), pw = L.PORTS["z"], L.PORTS["width"]
    for k, x in enumerate(L.PORTS["x"]):
        reg.rect_(*at(x - pw / 2 - 1.5, pz1 + 1.5), *at(x + pw / 2 + 1.5, pz0 - 1.5), (16, 16, 18), r=2.0)
        reg.text(str(k + 1), "arialbd.ttf", 4.0, *at(x - 3.0, pz1 + 5.0), RED)
    return reg


def pad():
    """The controller from above: x across (-w/2 at the left), y down from its far edge."""
    w, d, _ = L.PAD["size"]
    reg = Region(L.REGIONS["pad"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d / 2 - y

    f = L.PAD["face"]
    reg.rect_(*at(-w / 2 + f, d / 2 - f), *at(w / 2 - f, -d / 2 + f), BLACK, r=1.0)
    for y in (6.0, -6.0, -18.0):                             # the grey stripes behind SELECT and START
        reg.rect_(*at(-18.0, y + 3.2), *at(18.0, y - 3.2), (196, 196, 194), r=1.0)
    reg.rect_(*at(-17.0, -1.0), *at(17.0, -11.0), (210, 210, 208), r=2.0)
    reg.text("SELECT", "arialbd.ttf", 3.0, *at(-8.0, 1.6), RED)
    reg.text("START", "arialbd.ttf", 3.0, *at(9.0, 1.6), RED)
    for (x, y), c in zip(L.PAD["ba"], "BA"):
        reg.rect_(*at(x - 7.0, y + 7.0), *at(x + 7.0, y - 7.0), (210, 210, 208), r=1.0)
        reg.text(c, "arialbd.ttf", 3.6, *at(x + 4.0, y - 9.4), RED)
    reg.text("Nintendo", "arialbd.ttf", 5.0, *at(38.0, 13.0), RED)
    return reg


def cart():
    """The cartridge's top: x across, y down from its outer end to the end going in; its label at the outer end."""
    w, length, _ = L.CART["size"]
    reg = Region(L.REGIONS["cart"], w, length, (128, 128, 130))
    for k in range(22):                                      # the ribs down its left
        y = 20.0 + k * 4.8
        reg.rect_(10.0, y, 32.0, y + 2.2, (110, 110, 112))
    reg.rect_(36.0, 8.0, w - 8.0, 88.0, (240, 238, 232), r=1.0)
    art = space((360, 200)).convert("RGB")
    ship(ImageDraw.Draw(art), 100, 110, 2.4, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(39.0, 22.0, w - 11.0, 85.0)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 9.0, (36.0 + w - 8.0) / 2, 15.0, (40, 40, 44))
    reg.poly([(76.0, 104.0), (86.0, 104.0), (81.0, 112.0)], (110, 110, 112))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), cart()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, base=BASE, black=BLACK, dark=(10, 10, 10), red=RED, lit=(255, 40, 30), off=(70, 20, 20),
                   cart=(128, 128, 130), grey=(196, 196, 194), rubber=(40, 40, 42))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "nes_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
