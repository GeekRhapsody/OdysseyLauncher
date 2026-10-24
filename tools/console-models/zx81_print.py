"""The ZX81's printing and screens, for the console theme's ZX81 model (tools/console-models/zx81.py).

Draws its two atlases, their regions as zx81_layout.py places them. zx81_print.png: the computer's top seen from above,
in millimetres as the model's planar UVs map it (the embossed name, ZX81 in red, the membrane keyboard's keys with their
letters, red symbols and keywords), and the television's front and swatches where zx_spectrum_layout.py places them
(drawn by zx_spectrum_print.py, as the ZX Spectrum's). zx81_media.png: the screens, each the whole screen at 320 x 256
pixels with the ZX81's white border round its 256 x 192: at rest the inverse K cursor on white; LOAD and LOAD "" typed;
the black and white bands it shows while it loads, twice; and a made-up game, Odyssey, in its 64 x 48 block graphics.
Run it with the system Python (Pillow):

    python tools/console-models/zx81_print.py <out folder>

It writes zx81_print.png and zx81_media.png there.
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zx81_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402
from zx_spectrum_print import FONT, sinclair_logo, tv_front  # noqa: E402

RED = (226, 64, 52)
INK, PAPER = (0, 0, 0), (236, 236, 232)
TYPED = ("j", "shift", "p", "newline")


def top_point(x, y):
    """A point of the top (x from the middle, y back from the front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


def key(reg, k, rect):
    name, row, letter, red, up, down = k
    x0, y0, x1, y1 = rect
    (a, b), (c, e) = top_point(x0, y1), top_point(x1, y0)
    if name in TYPED:                                    # the well the moving key leaves when it's pressed
        reg.rect_(a - 0.6, b - 0.6, c + 0.6, e + 0.6, (70, 70, 72), r=L.KEY["radius"] + 0.6)
    reg.rect_(a, b, c, e, rgb(L.COLOURS["key"]), r=L.KEY["radius"])
    if "\n" in letter:                                   # NEW LINE, FUNCTION over it
        reg.text("FUNCTION", "arial.ttf", 1.8, (a + c) / 2, b + 2.0, RED)
        for j, line in enumerate(letter.split("\n")):
            reg.text(line, "arial.ttf", 2.2, (a + c) / 2, b + 4.8 + j * 2.6, INK)
        return
    if name in ("shift", "space"):
        reg.text(letter, "arialbd.ttf", 2.8 if name == "shift" else 2.0, (a + c) / 2, (b + e) / 2 + 1.5,
                 RED if name == "shift" else INK)
        if red:
            reg.text(red, "arial.ttf", 2.6, (a + c) / 2 + 2.5, b + 2.4, RED)
        if up:
            reg.text(up, "arial.ttf", 2.0, (a + c) / 2, b - 1.8, (230, 230, 230))
        return
    reg.text(letter, "arialbd.ttf", 4.6, a + 3.0, (b + e) / 2 + 1.4, INK)
    if row == 1:
        reg.text(red, "arial.ttf" if red.isascii() else "seguisym.ttf", 2.0, c - 1.0, b + 2.0, RED, anchor="rm")
        reg.rect_(c - 4.6, e - 5.2, c - 1.4, e - 2.0, INK)
        reg.rect_(c - 4.0, e - 4.6, c - 2.0, e - 3.6 if int(letter if letter != "0" else 0) % 2 else e - 2.6, PAPER)
    else:
        reg.text(red, "arial.ttf", 2.2 if len(red) > 2 else 2.6, c - 1.2, b + 2.2, RED, anchor="rm")
    if up:
        reg.text(up, "arial.ttf", 1.9, a + 1.0, b - 1.4, (230, 230, 230), anchor="lm")
    if down:
        reg.text(down, "arial.ttf", 1.9, a + 1.0, e + 1.4, (230, 230, 230), anchor="lm")


def top():
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH, rgb(L.COLOURS["case"]))
    sinclair_logo(reg, *top_point(L.NAME["x"], L.NAME["y"] - L.NAME["height"] / 2), L.NAME["height"], (44, 44, 48))
    reg.text("ZX81", "arialbd.ttf", L.MODEL["height"] * 1.3, *top_point(L.MODEL["x"], L.MODEL["y"]), (232, 86, 42),
             anchor="lm")
    x0, x1, y0, y1 = L.MEMBRANE
    (a, b), (c, e) = top_point(x0, y1), top_point(x1, y0)
    reg.rect_(a - 0.8, b - 0.8, c + 0.8, e + 0.8, shade(rgb(L.COLOURS["case"]), -0.4), r=1.5)
    reg.rect_(a, b, c, e, rgb(L.COLOURS["membrane"]), r=1.0)
    for k, rect in L.keys_with_rects():
        key(reg, k, rect)
    return reg


def print_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["case"]))
    top().paste(image)
    tv_front().paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", rgb(SL.COLOURS["bezel"])), ("silver", rgb(SL.COLOURS["handle"])),
                         ("red", (255, 40, 30))):
        x, y = SL.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    return image


# ---- The screens -----------------------------------------------------------------------------------------------------

def chars(img, col, row, text, inverse=False):
    """Text in the ZX81's 8 x 8 character cells of the display (inside the border)."""
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    fg, bg = (PAPER, INK) if inverse else (INK, PAPER)
    for k, ch in enumerate(text):
        x, y = 32 + (col + k) * 8, 32 + row * 8
        d.rectangle([x, y, x + 7, y + 7], fill=bg)
        d.text((x + 4, y + 4), ch, font=FONT, fill=fg, anchor="mm")


def screen(lines=()):
    img = Image.new("RGB", (320, 256), PAPER)
    for col, row, text, inverse in lines:
        chars(img, col, row, text, inverse)
    return img


def bands(seed):
    """The loading's bands: black and white stripes across the whole screen, each a few lines tall."""
    img = Image.new("RGB", (320, 256), PAPER)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    y = 0
    while y < 256:
        h = rng.choice((1, 2, 2, 3, 4, 6))
        if rng.random() < 0.55:
            d.rectangle([0, y, 319, y + h - 1], fill=INK)
        y += h
    return img


def game():
    """Odyssey in the ZX81's block graphics: the display drawn at 64 x 48 blocks of 4 x 4 pixels (stars, the title, the
    ship, a planet's edge), then PRESS ANY KEY in inverse characters."""
    blocks = Image.new("1", (64, 48), 0)
    d = ImageDraw.Draw(blocks)
    rng = random.Random(81)
    for _ in range(26):
        d.point((rng.randrange(64), rng.randrange(40)), fill=1)
    title = Image.new("1", (40, 8), 0)
    dt = ImageDraw.Draw(title)
    dt.fontmode = "1"
    dt.text((0, -1), "ODYSSEY", font=ImageFont.truetype(FONTS + "consolab.ttf", 9), fill=1)
    blocks.paste(title.crop(title.getbbox()), (32 - (title.getbbox()[2] - title.getbbox()[0]) // 2, 4))
    d.polygon([(30, 26), (14, 20), (18, 26), (14, 32)], fill=1)          # the ship
    d.polygon([(20, 23), (10, 16), (14, 24)], fill=1)
    d.polygon([(20, 29), (10, 36), (14, 28)], fill=1)
    d.line([(4, 26), (10, 26)], fill=1)
    d.ellipse([44, 18, 76, 50], outline=1)                              # a planet's edge
    d.arc([38, 30, 70, 38], 160, 340, fill=1)
    img = Image.new("RGB", (320, 256), PAPER)
    img.paste(Image.eval(blocks.convert("L"), lambda v: 0 if v else 236).convert("RGB").resize((256, 192),
              Image.NEAREST), (32, 32))
    chars(img, 9, 21, "PRESS ANY KEY", inverse=True)
    return img


def media_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (24, 24, 24))
    screens = {
        "glass": screen([(0, 23, "K", True)]),
        "load": screen([(0, 23, "LOAD ", False), (5, 23, "L", True)]),
        "load2": screen([(0, 23, 'LOAD ""', False), (7, 23, "L", True)]),
        "bands_a": bands(1),
        "bands_b": bands(2),
        "game": game(),
    }
    for name, img in screens.items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(img, (x, y))
    return image


def main(out):
    os.makedirs(out, exist_ok=True)
    for name, image in (("zx81_print.png", print_atlas()), ("zx81_media.png", media_atlas())):
        path = os.path.join(out, name)
        image.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1])
