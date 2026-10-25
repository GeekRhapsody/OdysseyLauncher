"""The Atari XE Game System card's printing (xegs_print.png), for the console theme's model (xegs.py).

One image, laid out as xegs_layout.REGIONS says: the keyboard from above (the keys' tops and legends), the console's
front strip from above (the ATARI logo in relief, the four buttons' tops and names), the cartridge's front (its label: a
made-up game, Odyssey), the POWER and HELP buttons' tops, and swatches; the joystick's top (the beige CX40's, drawn
where atari_2600_layout.py puts the 2600's) and its red. Run it with the system Python (Pillow):

    python tools/console-models/xegs_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari_2600_layout as AL  # noqa: E402
import xegs_layout as L  # noqa: E402
from atari5200_print import fuji  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
LEGEND = (88, 86, 82)
JOY = (206, 200, 172)
CART = (52, 50, 48)
BUTTONS = dict(start=(186, 214, 198), select=(238, 230, 150), option=(240, 192, 162), reset=(214, 202, 222),
               power=(198, 226, 168), help=(200, 194, 160))


def shade(colour, k):
    return tuple(max(0, min(255, round(c * (1 + k)))) for c in colour)


def turned(reg, s, name, size, x, y, fill, angle):
    """Text centred at (x, y), turned angle degrees anticlockwise."""
    f = ImageFont.truetype(FONTS + name, max(1, round(size * reg.sy)))
    box = reg.draw.textbbox((0, 0), s, font=f)
    w, h = box[2] - box[0] + 8, box[3] - box[1] + 8
    tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((w / 2, h / 2), s, font=f, fill=fill, anchor="mm")
    tile = tile.rotate(angle, resample=Image.BICUBIC, expand=True)
    px, py = reg.p(x, y)
    reg.img.alpha_composite(tile, (round(px - tile.width / 2), round(py - tile.height / 2)))


def keys():
    """The keyboard from above: x across (-w/2 at the left), v down from its back edge to its front."""
    w, d, _ = L.KEYBOARD["size"]
    reg = Region(L.REGIONS["keys"], w, d, CASE)

    def at(x, v):
        return x + w / 2, d - v

    inset = L.KEY["inset"]
    for legend, x0, x1, v in L.keys():
        reg.rect_(*at(x0 + inset, v + 9.5 - inset), *at(x1 - inset, v - 9.5 + inset), KEY, r=1.6)
        if not legend.strip():
            continue
        x, y = at((x0 + x1) / 2, v)
        if legend == "◪":                                   # inverse video: a square, half of it filled
            reg.rect_(x - 2.4, y - 2.4, x + 2.4, y + 2.4, None, outline=LEGEND, width=0.4)
            reg.poly([(x - 2.4, y + 2.4), (x + 2.4, y - 2.4), (x + 2.4, y + 2.4)], LEGEND)
        elif len(legend) == 1:
            reg.text(legend, "arial.ttf", 4.6, x, y, LEGEND)
        else:
            reg.text(legend, "arial.ttf", 2.6, x0 + w / 2 + inset + 1.2, y - 3.2, LEGEND, anchor="lm")
    return reg


def strip():
    """The front strip from above: x across, y down from its back edge to its front; the logo in relief, the buttons'
    tops."""
    (y0, y1), w = L.STRIP["y"], L.WIDTH
    reg = Region(L.REGIONS["strip"], w, y1 - y0, CASE)

    def at(x, y):
        return x + w / 2, y1 - y

    # The logo stands out of the strip: drawn twice, its shadow a shade darker below and right of it.
    for dx, dy, colour in ((0.7, -0.7, shade(CASE, -0.22)), (-0.35, 0.35, shade(CASE, 0.12)), (0.0, 0.0, CASE)):
        fuji(reg, *at(-139.0 + dx, 25.0 + dy), 19.0, colour)
        reg.text("ATARI", "arialbd.ttf", 21.0, *at(-127.0 + dx, 25.0 + dy), colour, anchor="lm")
    r = L.BUTTONS["r"]
    for x, name in zip(L.BUTTONS["x"], L.BUTTONS["names"]):
        cx, cy = at(x, L.BUTTONS["y"])
        reg.circle(cx, cy, r - 0.4, BUTTONS[name.lower()])
        reg.circle(cx, cy, r - 0.4, None, outline=shade(BUTTONS[name.lower()], -0.12), width=0.5)
        turned(reg, name, "arialbd.ttf", 3.2, cx, cy, (255, 255, 255, 235), 45)
    return reg


def button(name, label, mark=False):
    """A round button's top: its colour, its name turned along the console's diagonal, and the LED's hole."""
    r = L.POWER["r"] if name == "power" else L.HELP["r"]
    reg = Region(L.REGIONS[name], 2 * r, 2 * r, BUTTONS[name])
    turned(reg, label, "arialbd.ttf", 3.4, r - 1.0, r - 1.0, (255, 255, 255, 235), 45)
    if mark:
        dx, dy = L.POWER["led"]
        reg.circle(r + dx, r - dy, 1.3, (60, 34, 30))
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
    reg.rect_(x0, top, x0 + lw, top + 10.0, (240, 238, 232))
    reg.text("ODYSSEY", "ariblk.ttf", 6.0, w / 2, top + 5.0, (40, 40, 44))
    reg.text("«LEFT CARTRIDGE", "arial.ttf", 2.6, w / 2, top / 2, (170, 168, 160))
    return reg


def stick_top():
    """The beige CX40's top, drawn where atari_2600_layout.py puts the 2600's: the black boot's rings, the raised ring
    of ticks round it."""
    w, d, _ = AL.STICK["base"]
    reg = Region(AL.REGIONS["stick"], w, d, shade(JOY, -0.06))
    reg.rect_(1.0, 1.0, w - 1.0, d - 1.0, JOY, r=10.0)
    cx, cy = w / 2 + 6.0, d / 2 + 3.0
    for k in range(48):
        a = 2 * math.pi * k / 48
        reg.line([(cx + 23 * math.cos(a), cy + 23 * math.sin(a)), (cx + 27 * math.cos(a), cy + 27 * math.sin(a))],
                 shade(JOY, -0.18), 1.1)
    reg.circle(cx, cy, 21.0, (22, 22, 22))
    for rr in (18.0, 15.0, 12.0):
        reg.circle(cx, cy, rr, None, outline=(64, 64, 62), width=0.8)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (keys(), strip(), cart(), button("power", "Power", True), button("help", "Help"), stick_top()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    x, y = AL.SWATCHES["red"]
    d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=(232, 72, 40))
    colours = dict(case=CASE, dark=(16, 16, 16), well=shade(CASE, -0.35), key=shade(KEY, -0.06), cart=CART,
                   black=(24, 24, 24), joy=JOY, led=(236, 36, 28),
                   **{name: shade(colour, -0.08) for name, colour in BUTTONS.items()})
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "xegs_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
