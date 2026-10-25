"""The Fairchild Channel F card's printing (channelf_print.png), for the console theme's model (channelf.py).

One image, laid out as channelf_layout.REGIONS says: the front panel from above (RESET and the keys' tops, TIME MODE
HOLD START, the times, HOCKEY TENNIS GAME 3 GAME 4, INSERT CARTRIDGE, Press to Eject), the lid's chrome strip, the
cartridge door's ribs, the Videocart's top (its label: a made-up game, Odyssey), the walnut's grain, a controller's
ribbed grip, and swatches. Run it with the system Python (Pillow):

    python tools/console-models/channelf_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import channelf_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

BLACK = rgb(L.COLOURS["black"])
WOOD = rgb(L.COLOURS["wood"])
CART = rgb(L.COLOURS["cart"])
WHITE = (232, 232, 226)
CREAM = (232, 226, 200)
YELLOW = (232, 188, 40)
CHROME = (200, 200, 196)


def panel():
    """The front panel from above: x across, y down from the lid's front face to the panel's front edge."""
    back = L.LID["y"]
    reg = Region(L.REGIONS["panel"], L.WIDTH, back, BLACK)

    def at(x, y):
        return x + L.WIDTH / 2, back - y

    xs, y, k = L.KEYS["x"], L.KEYS["y"], L.KEYS["size"] / 2
    reg.rect_(*at(xs[0] - 13.0, 62.0), *at(xs[-1] + 13.0, 18.0), (30, 30, 32), r=2.0)
    for word, x in zip(("TIME", "MODE", "HOLD", "START"), xs[1:]):
        reg.text(word, "arialbd.ttf", 3.4, *at(x, 57.0), WHITE)
    reg.text("RESET", "arialbd.ttf", 3.0, *at(xs[0], 51.5), YELLOW)
    for word, x in zip(("2 MIN", "5 MIN", "10 MIN", "20 MIN"), xs[1:]):
        reg.text(word, "arialbd.ttf", 2.6, *at(x, 51.5), WHITE)
    for ly in (48.5, 29.0):
        reg.line([at(xs[0] - 8.0, ly), at(xs[-1] + 8.0, ly)], (160, 156, 140), 0.3)
    for word, x in zip(("HOCKEY", "TENNIS", "GAME 3", "GAME 4"), xs[1:]):
        reg.text(word, "arialbd.ttf", 2.6, *at(x, 25.5), WHITE)
    for x, name in zip(xs, L.KEYS["names"]):
        reg.rect_(*at(x - k, y + k), *at(x + k, y - k), YELLOW if name == "RESET" else CREAM, r=1.6)
        if name != "RESET":
            reg.text(name, "arialbd.ttf", 6.0, *at(x, y), BLACK)

    (px0, px1), (py0, py1) = L.PLATE["x"], L.PLATE["y"]
    reg.rect_(*at(px0, py1), *at(px1, py0), (12, 12, 14), r=3.0)
    reg.rect_(*at(px0 + 4.0, py1 - 3.0), *at(px1 - 4.0, py0 + 3.0), None, r=3.0, outline=(214, 190, 120), width=0.5)
    mx, my = (px0 + px1) / 2, (py0 + py1) / 2
    reg.text("INSERT", "arialbd.ttf", 3.2, *at(mx - 6.0, my), WHITE, anchor="rm")
    reg.text("CARTRIDGE", "arialbd.ttf", 3.2, *at(mx + 6.0, my), WHITE, anchor="lm")
    reg.line([at(mx - 3.0, my - 1.4), at(mx, my + 1.6), at(mx + 3.0, my - 1.4)], WHITE, 0.5)
    (ex0, ex1), (ey0, ey1) = L.EJECT["x"], L.EJECT["y"]
    reg.rect_(*at(ex0, ey1), *at(ex1, ey0), (22, 22, 24), r=1.0)
    for k in range(7):
        for x0 in (ex0 + 2.0, ex1 - 17.0):
            yy = ey0 + 2.5 + k * (ey1 - ey0 - 5.0) / 6
            reg.line([at(x0, yy), at(x0 + 15.0, yy)], (60, 60, 62), 0.5)
    reg.rect_(*at(ex0 + 20.0, ey1 - 4.0), *at(ex1 - 20.0, ey0 + 4.0), (40, 40, 42), r=1.0)
    reg.text("Press to Eject", "arialbd.ttf", 3.6, *at((ex0 + ex1) / 2, (ey0 + ey1) / 2), WHITE)
    return reg


def strip():
    """The lid's chrome strip from above: x across, y down from its back edge."""
    (x0, x1), (y0, y1) = L.STRIP["x"], L.STRIP["y"]
    reg = Region(L.REGIONS["strip"], L.WIDTH, y1 - y0, BLACK)

    def at(x, y):
        return x + L.WIDTH / 2, y1 - y

    reg.rect_(*at(x0, y1), *at(x1, y0), (18, 18, 20), r=1.5)
    for ly in (y0 + 2.5, y1 - 2.5):
        reg.line([at(x0 + 3.0, ly), at(x1 - 3.0, ly)], CHROME, 0.7)
    my = (y0 + y1) / 2
    reg.rect_(*at(-112.0, my + 4.0), *at(-74.0, my - 4.0), CHROME)
    for k in range(3):
        reg.line([at(-112.0, my - 2.0 + 2.0 * k), at(-74.0, my - 2.0 + 2.0 * k)], (18, 18, 20), 0.25)
    reg.text("FAIRCHILD", "arialbd.ttf", 3.6, *at(-93.0, my), (18, 18, 20))
    reg.text("VIDEO   ENTERTAINMENT   SYSTEM", "arialbd.ttf", 3.4, *at(40.0, my), WHITE)
    return reg


def door():
    """The cartridge door's face: ribbed."""
    (x0, x1), (z0, z1) = L.SLOT["x"], L.SLOT["z"]
    w, h = x1 - x0, z1 - z0
    reg = Region(L.REGIONS["door"], w, h, (20, 20, 22))
    for k in range(11):
        y = 1.5 + k * (h - 3.0) / 10
        reg.line([(2.0, y), (w - 2.0, y)], (52, 52, 56), 0.8)
    return reg


def cart():
    """The Videocart's top: x across, y down from its back end to its front (the grip's ribs); the label showing in
    front of the slot."""
    w, length, _ = L.CART["size"]
    reg = Region(L.REGIONS["cart"], w, length, CART)
    reg.rect_(8.0, 22.0, w - 8.0, length - 14.0, (16, 16, 18), r=2.0)
    for k in range(6):
        y = length - 12.0 + k * 2.0
        reg.line([(4.0, y), (w - 4.0, y)], (212, 164, 30), 0.6)
    art = space((440, 168)).convert("RGB")
    ship(ImageDraw.Draw(art), 120, 86, 2.3, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(12.0, 101.0, w - 12.0, length - 17.0)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 7.0, w / 2, 95.0, (240, 196, 48))
    reg.text("VIDEOCART-26", "arialbd.ttf", 3.0, 12.0, 88.0, WHITE, anchor="lm")
    reg.text("FAIRCHILD", "arialbd.ttf", 3.0, w - 12.0, 88.0, WHITE, anchor="rm")
    return reg


def wood():
    """Walnut: dark brown, its grain running along."""
    reg = Region(L.REGIONS["wood"], 400.0, 160.0, WOOD)
    rng = random.Random(11)
    for _ in range(140):
        y0, tone = rng.uniform(0.0, 160.0), rng.uniform(-0.35, 0.25)
        colour = tuple(max(0, min(255, round(c * (1 + tone)))) for c in WOOD)
        wave, phase, width = rng.uniform(0.5, 3.0), rng.uniform(0, 2 * math.pi), rng.uniform(0.4, 1.6)
        reg.line([(x, y0 + wave * math.sin(x / rng.uniform(30.0, 70.0) + phase)) for x in range(0, 401, 10)], colour,
                 width)
    return reg


def grip():
    """A controller's grip: black, ribbed across."""
    length, _, h = L.CONTROLLER["grip"]
    reg = Region(L.REGIONS["grip"], length, h, (14, 14, 16))
    for k in range(34):
        x = 8.0 + k * (length - 16.0) / 33
        reg.line([(x, 3.0), (x, h - 3.0)], (46, 46, 50), 0.9)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BLACK)
    for reg in (panel(), strip(), door(), cart(), wood(), grip()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(black=BLACK, wood=WOOD, cream=CREAM, yellow=YELLOW, cart=CART, chrome=CHROME, dark=(6, 6, 6),
                   gloss=(14, 14, 16))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "channelf_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
