"""The Macintosh card's printing and screens (macintosh_print.png), for the console theme's model (macintosh.py).

One image, laid out as macintosh_layout.REGIONS says: the keyboard from above (the keys' tops and legends), the four
screens (drawn at the Macintosh's 512 x 342, one bit deep, then set into the tube's face: the disk with its blinking
question mark, the happy Mac, Welcome to Macintosh., and a made-up game, Odyssey, in its window), the floppy's top (its
shutter and label), the mouse from above (its button), the rainbow Apple, and swatches. Run it with the system Python
(Pillow):

    python tools/console-models/macintosh_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import macintosh_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
LEGEND = (70, 66, 60)
RAINBOW = [(97, 187, 70), (253, 184, 39), (245, 130, 31), (224, 58, 62), (150, 61, 151), (0, 157, 220)]
W, H = 512, 342                  # the Macintosh's screen
TUBE = (22, 26, 24)


# ---- The screens -----------------------------------------------------------------------------------------------------

def grey(img, box=None):
    """The desktop's grey: every other pixel black, in a checkerboard."""
    x0, y0, x1, y1 = box or (0, 0, img.width, img.height)
    px = img.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[x, y] = 0 if (x + y) % 2 else 1


def font(size, bold=True):
    return ImageFont.truetype(FONTS + ("arialbd.ttf" if bold else "arial.ttf"), size)


def mac_icon(d, x, y, k):
    """The happy Mac, k pixels to its pixel, its top left at (x, y): the case, the screen with its smile."""
    def r(x0, y0, x1, y1, fill):
        d.rectangle([x + x0 * k, y + y0 * k, x + x1 * k - 1, y + y1 * k - 1], fill=fill)
    r(0, 0, 22, 30, 0)
    r(1, 1, 21, 29, 1)
    r(3, 3, 19, 17, 0)
    r(4, 4, 18, 16, 1)
    for ex in (7, 14):                                      # the eyes
        r(ex, 7, ex + 1, 10, 0)
    r(11, 8, 12, 12, 0)                                     # the nose
    r(10, 11, 11, 12, 0)
    r(7, 13, 8, 14, 0)                                      # the smile
    r(8, 14, 14, 15, 0)
    r(14, 13, 15, 14, 0)
    r(4, 22, 9, 23, 0)                                      # the drive
    r(13, 22, 19, 23, 0)
    r(0, 30, 22, 33, 0)                                     # the foot
    r(1, 30, 21, 32, 1)


def disk_icon(d, x, y, k):
    """The floppy with its question mark, k pixels to its pixel, its top left at (x, y)."""
    def r(x0, y0, x1, y1, fill):
        d.rectangle([x + x0 * k, y + y0 * k, x + x1 * k - 1, y + y1 * k - 1], fill=fill)
    r(0, 0, 30, 30, 0)
    r(1, 1, 29, 29, 1)
    r(26, 0, 30, 4, 1)                                      # the cut corner
    r(7, 1, 22, 11, 0)                                      # the shutter
    r(8, 2, 21, 10, 1)
    r(16, 3, 19, 9, 0)
    r(5, 15, 25, 29, 0)                                     # the label
    r(6, 16, 24, 29, 1)
    d.text((x + 15 * k, y + 22 * k), "?", font=font(10 * k), fill=0, anchor="mm")


def screen_disk():
    img = Image.new("1", (W, H), 1)
    grey(img)
    disk_icon(ImageDraw.Draw(img), W // 2 - 60, H // 2 - 60, 4)        # four times its size, to read on a card
    return img


def screen_happy():
    img = Image.new("1", (W, H), 1)
    grey(img)
    mac_icon(ImageDraw.Draw(img), W // 2 - 44, H // 2 - 66, 4)
    return img


def screen_welcome():
    img = Image.new("1", (W, H), 1)
    grey(img)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([W // 2 - 130, H // 2 - 34, W // 2 + 130, H // 2 + 34], 8, fill=1, outline=0, width=2)
    d.rounded_rectangle([W // 2 - 125, H // 2 - 29, W // 2 + 125, H // 2 + 29], 6, outline=0, width=1)
    d.text((W // 2, H // 2), "Welcome to Macintosh.", font=font(19), fill=0, anchor="mm")
    return img


def screen_game():
    """The game in its window: the menu bar, the title bar's stripes, space with the ship and the ringed planet."""
    img = Image.new("1", (W, H), 1)
    grey(img)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, 19], fill=1)
    d.line([0, 19, W - 1, 19], fill=0)
    d.ellipse([14, 4, 24, 15], fill=0)                      # the Apple
    d.rectangle([18, 1, 20, 4], fill=0)
    for x, word in ((44, "File"), (90, "Edit"), (138, "Game")):
        d.text((x, 10), word, font=font(13), fill=0, anchor="lm")
    x0, y0, x1, y1 = 30, 34, W - 30, H - 14
    d.rectangle([x0 + 3, y0 + 3, x1 + 3, y1 + 3], fill=0)  # the window's shadow
    d.rectangle([x0, y0, x1, y1], fill=1, outline=0)
    for k in range(6):                                      # the title bar
        d.line([x0 + 3, y0 + 4 + 2 * k, x1 - 3, y0 + 4 + 2 * k], fill=0)
    d.rectangle([W // 2 - 44, y0 + 2, W // 2 + 44, y0 + 16], fill=1)
    d.text((W // 2, y0 + 9), "Odyssey", font=font(13), fill=0, anchor="mm")
    d.line([x0, y0 + 19, x1, y0 + 19], fill=0)
    d.rectangle([x0 + 1, y0 + 20, x1 - 1, y1 - 1], fill=0)  # space
    rng = random.Random(5)
    for _ in range(90):
        d.point((rng.randint(x0 + 2, x1 - 2), rng.randint(y0 + 21, y1 - 2)), fill=1)
    px = img.load()
    cx, cy, r = 340, 190, 52                                # the planet, dithered
    for y in range(cy - r, cy + r):
        for x in range(cx - r, cx + r):
            if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
                lit = (x - cx + r) / (2 * r)
                px[x, y] = 1 if (x * 7 + y * 13) % 8 < 8 * (1 - lit) * 0.9 + 1 else 0
    d.ellipse([cx - 92, cy - 16, cx + 92, cy + 16], outline=1, width=2)   # its ring
    for x in range(cx - r, cx + r):                         # the ring behind the planet hides
        for y in range(cy - 16, cy + 1):
            on_ring = abs(((x - cx) / 92) ** 2 + ((y - cy) / 16) ** 2 - 1) < 0.12
            if (x - cx) ** 2 + (y - cy) ** 2 < r * r and px[x, y] == 1 and on_ring:
                px[x, y] = 0
    d.polygon([(110, 186), (176, 172), (110, 158), (124, 172)], fill=1)    # the ship
    d.polygon([(110, 166), (96, 172), (110, 178)], fill=1)
    d.text((x0 + 10, y1 - 14), "SCORE 2600", font=font(11), fill=1, anchor="lm")
    return img


def tube(img):
    """A screen set into the tube's face: its raster in the middle, the glass's dark round it, a little glow."""
    rw, rh = 238, 159
    glass = Image.new("RGB", (256, 206), TUBE)
    raster = img.convert("L").resize((rw, rh), Image.LANCZOS)
    raster = Image.merge("RGB", [raster.point(lambda v, k=k: round(base + v * k)) for base, k in
                                 ((26, 0.86), (30, 0.86), (28, 0.84))])                  # a faint green cast
    glass.paste(raster, ((256 - rw) // 2, (206 - rh) // 2))
    return glass


# ---- The printing ----------------------------------------------------------------------------------------------------

def keys():
    """The keyboard from above: x across (-w/2 at the left), v down from its back edge to its front."""
    w, d = L.KEYBOARD["size"]
    reg = Region(L.REGIONS["keys"], w, d, CASE)
    (hf, hb), inset, top = L.KEYBOARD["height"], L.KEY["inset"], L.KEY["height"]
    slope = math.atan2(hb - hf, d)

    def at(x, v):
        return x + w / 2, d - v

    for legend, x0, x1, v in L.keys():
        va = v - 9.5 + inset - top * math.sin(slope)
        vb = v + 9.5 - inset - top * math.sin(slope)
        reg.rect_(*at(x0 + inset, vb), *at(x1 - inset, va), KEY, r=1.4)
        x, y = at((x0 + x1) / 2, (va + vb) / 2)
        if legend == "⌘":
            reg.text(legend, "seguisym.ttf", 4.6, x, y, LEGEND)
        elif len(legend) == 1 and legend != " ":
            reg.text(legend, "arial.ttf", 4.2, x0 + w / 2 + inset + 2.0, y - 2.4, LEGEND, anchor="lm")
        elif legend.strip():
            reg.text(legend, "arial.ttf", 2.6, x0 + w / 2 + inset + 1.6, y + 3.0, LEGEND, anchor="lm")
    return reg


def floppy():
    """The floppy's top: x across, y back from its shutter's edge (the edge going in) to its label's."""
    w, d, _ = L.FLOPPY["size"]
    reg = Region(L.REGIONS["floppy"], w, d, (52, 58, 72))
    sw, sd = L.FLOPPY["shutter"]
    reg.rect_(w / 2 - sw / 2, 0.0, w / 2 + sw / 2, sd, (192, 194, 198))
    reg.rect_(w / 2 + 2.0, 6.0, w / 2 + 12.0, sd - 4.0, (40, 40, 44), r=1.0)
    reg.rect_(8.0, 40.0, w - 8.0, d - 4.0, (238, 236, 228), r=1.0)
    art = space((360, 160)).convert("RGB")
    ship(ImageDraw.Draw(art), 100, 82, 2.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(11.0, 58.0, w - 11.0, d - 7.0)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 7.0, w / 2, 49.0, (40, 40, 44))
    return reg


def mouse():
    """The mouse from above: x across, y back from its front (the button's end) to the end under the hand."""
    w, length, _ = L.MOUSE["size"]
    reg = Region(L.REGIONS["mouse"], w, length, CASE)
    reg.rect_(4.0, 2.0, w - 4.0, length * L.MOUSE["button"], (196, 188, 168), r=2.0, outline=(150, 142, 124),
              width=0.5)
    return reg


def apple():
    """The rainbow Apple on its badge."""
    reg = Region(L.REGIONS["apple"], 16.3, 17.9, (200, 192, 172))
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    mask = Image.new("L", layer.size, 0)
    m = ImageDraw.Draw(mask)
    k = reg.sx

    def e(cx, cy, rx, ry, fill):
        m.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=fill)
    e(6.1, 10.4, 3.9, 4.6, 255)
    e(10.2, 10.4, 3.9, 4.6, 255)
    e(8.15, 8.6, 4.4, 3.4, 255)
    e(13.6, 9.6, 1.9, 2.2, 0)                               # the bite
    m.ellipse([8.2 * k, 2.6 * k, 10.6 * k, 5.4 * k], fill=255)   # the leaf
    for i, colour in enumerate(RAINBOW):
        d.rectangle([0, (2.6 + i * 2.25) * k, layer.width, (2.6 + (i + 1) * 2.25) * k], fill=colour + (255,))
    layer.putalpha(mask)
    reg.over(layer)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (keys(), floppy(), mouse(), apple()):
        reg.paste(image)
    for name, screen in (("disk", screen_disk()), ("happy", screen_happy()), ("welcome", screen_welcome()),
                         ("game", screen_game())):
        x, y, w, h = L.REGIONS[name]
        image.paste(tube(screen).resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, key=KEY, dark=(16, 16, 16), tube=TUBE, floppy=(52, 58, 72), shutter=(192, 194, 198),
                   cord=(204, 196, 176), legend=LEGEND)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "macintosh_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
