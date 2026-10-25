"""PICO-8's cartridge's printing and its label's screens, for the console theme's PICO-8 model
(tools/console-models/pico8.py).

Draws its two atlases, their regions as pico8_layout.py places them, in PICO-8's pixels and its sixteen colours.
pico8_print.png: the cartridge's face (the grey body cut in pixel steps at its corners, PICO-8's logo and
WWW.PICO-8.COM along its top, the label's black window, the dark box with the title, a tagline and PICO-8 CARTRIDGE)
and its back, and swatches. pico8_media.png: the label's screens, 128 x 128 each: the label at rest (the title screen
of a made-up game, Odyssey), booting (noise, then PICO-8's logo and version), and two frames of Odyssey being played.
Text is in PICO-8's own three-by-five letters. Run it with the system Python (Pillow):

    python tools/console-models/pico8_print.py <out folder>

It writes pico8_print.png and pico8_media.png there.
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pico8_layout as L  # noqa: E402
from retro_pc_print import rgb  # noqa: E402

P = [rgb(c) for c in L.PALETTE]
BLACK, DARK_BLUE, DARK_PURPLE, DARK_GREEN, BROWN, DARK_GREY, LIGHT_GREY, WHITE, RED, ORANGE, YELLOW, GREEN, BLUE, \
    LAVENDER, PINK, PEACH = range(16)

# PICO-8's letters, three by five ('#' lit).
FONT = {
    "A": "###/#.#/###/#.#/#.#", "B": "###/#.#/##./#.#/###", "C": ".##/#../#../#../.##", "D": "##./#.#/#.#/#.#/###",
    "E": "###/#../##./#../###", "F": "###/#../##./#../#..", "G": ".##/#../#../#.#/###", "H": "#.#/#.#/###/#.#/#.#",
    "I": "###/.#./.#./.#./###", "K": "#.#/#.#/##./#.#/#.#", "L": "#../#../#../#../###", "M": "###/###/#.#/#.#/#.#",
    "N": "##./#.#/#.#/#.#/#.#", "O": ".##/#.#/#.#/#.#/##.", "P": "###/#.#/###/#../#..", "R": "###/#.#/##./#.#/#.#",
    "S": ".##/#../###/..#/##.", "T": "###/.#./.#./.#./.#.", "U": "#.#/#.#/#.#/#.#/###", "V": "#.#/#.#/#.#/###/.#.",
    "W": "#.#/#.#/#.#/###/###", "X": "#.#/#.#/.#./#.#/#.#", "Y": "#.#/#.#/###/..#/###",
    "0": "###/#.#/#.#/#.#/###", "1": "##./.#./.#./.#./###", "2": "###/..#/###/#../###", "3": "###/..#/.##/..#/###",
    "4": "#.#/#.#/###/..#/..#", "5": "###/#../###/..#/###", "6": "#../#../###/#.#/###", "7": "###/..#/..#/..#/..#",
    "8": "###/#.#/###/#.#/###", "9": "###/#.#/###/..#/..#", ".": ".../.../.../.../.#.", "-": ".../.../###/.../...",
    "+": ".../.#./###/.#./...", "(": ".#./#../#../#../.#.", ")": ".#./..#/..#/..#/.#.", ">": "#../.#./..#/.#./#..",
    " ": ".../.../.../.../...",
}


def text(img, x, y, s, colour, scale=1, shadow=None):
    """s in PICO-8's letters, its top left at (x, y), each letter four pixels on (times scale)."""
    d = ImageDraw.Draw(img)
    for k, ch in enumerate(s):
        rows = FONT[ch].split("/")
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                if c != "#":
                    continue
                px, py = x + (k * 4 + i) * scale, y + j * scale
                if shadow is not None:
                    d.rectangle([px + scale, py + scale, px + 2 * scale - 1, py + 2 * scale - 1], fill=P[shadow])
                d.rectangle([px, py, px + scale - 1, py + scale - 1], fill=P[colour])
    if shadow is not None:                                   # the letters over every shadow
        text(img, x, y, s, colour, scale)


def width(s, scale=1):
    return (len(s) * 4 - 1) * scale


def logo(img, x, y):
    for j, row in enumerate(L.LOGO):
        for i, c in enumerate(row):
            if c != ".":
                img.putpixel((x + i, y + j), P[int(c, 16)])


# ---- The cartridge -----------------------------------------------------------------------------------------------------

def silhouette():
    """The cartridge's outline, a mask a cartridge pixel a pixel: its corners cut in STEP-pixel steps."""
    w, h = L.CART_PX
    mask = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(mask)
    s, c = L.STEP, L.CORNERS
    for k in range(c["top_left"]):
        d.rectangle([0, k * s, (c["top_left"] - k) * s - 1, (k + 1) * s - 1], fill=0)
    for k in range(c["top_right"]):
        d.rectangle([w - (c["top_right"] - k) * s, k * s, w - 1, (k + 1) * s - 1], fill=0)
    for k in range(c["bottom_left"]):
        d.rectangle([0, h - (k + 1) * s, (c["bottom_left"] - k) * s - 1, h - k * s - 1], fill=0)
    for k in range(c["chamfer"]):
        d.rectangle([w - (c["chamfer"] - k) * s, h - (k + 1) * s, w - 1, h - k * s - 1], fill=0)
    return mask


def front():
    w, h = L.CART_PX
    img = Image.new("RGB", (w, h), rgb(L.COLOURS["body"]))
    mask = silhouette()
    inside = mask.filter(ImageFilter.MinFilter(3))           # a pixel in from the outline: the dark border round it
    img = Image.composite(img, Image.new("RGB", (w, h), (20, 20, 20)), inside)
    d = ImageDraw.Draw(img)
    logo(img, 13, 5)
    url = "WWW.PICO-8.COM"
    text(img, 145 - width(url), 10, url, LIGHT_GREY)
    u, v, lw, lh = L.LABEL
    d.rectangle([u - 1, v - 1, u + lw, v + lh], fill=P[BLACK])
    bu, bv, bw, bh = L.TEXT_BOX
    d.rectangle([bu, bv, bu + bw - 1, bv + bh - 1], fill=rgb(L.COLOURS["box"]))
    text(img, bu + 3, bv + 4, "ODYSSEY", WHITE)
    text(img, bu + 3, bv + 12, "A TINY SPACE TRIP", WHITE)
    text(img, bu + 3, bv + 24, "PICO-8 CARTRIDGE", LIGHT_GREY)
    img.putalpha(mask)
    return img


def back():
    w, h = L.CART_PX
    img = Image.new("RGB", (w, h), rgb(L.COLOURS["body"]))
    d = ImageDraw.Draw(img)
    d.rectangle([14, 20, w - 15, 150], fill=(88, 88, 88))
    d.rectangle([16, 22, w - 17, 148], fill=(94, 94, 94))
    logo(img, (w - 40) // 2 + 2, 76)
    for k in range(6):                                       # the grip's ridges along its foot
        d.rectangle([24, 164 + k * 6, w - 25, 165 + k * 6], fill=(76, 76, 76))
    img.putalpha(silhouette())
    return img


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["edge"]))
    for name, pixels, art in (("front", L.FRONT_PX, front()), ("back", 2, back())):
        x, y, w, h = L.PRINT_REGIONS[name]
        flat = Image.new("RGB", art.size, rgb(L.COLOURS["edge"]))
        flat.paste(art, (0, 0), art)
        image.paste(flat.resize((w, h), Image.NEAREST), (x, y))
    d = ImageDraw.Draw(image)
    for name in ("edge", "seam"):
        x, y = L.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(L.COLOURS[name]))
    path = os.path.join(out, "pico8_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -------------------------------------------------------------------------------------------------------

def stars(img, seed, count=46):
    rng = random.Random(seed)
    for _ in range(count):
        img.putpixel((rng.randrange(128), rng.randrange(128)), P[rng.choice([WHITE, LIGHT_GREY, LAVENDER, DARK_GREY])])


def planet(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=P[ORANGE])
    for k, colour in enumerate((PEACH, BROWN, PEACH)):
        y = cy - r // 2 + k * (r // 2)
        d.ellipse([cx - r + 2, y - 2, cx + r - 2, y + 1], fill=P[colour])
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=P[BROWN])
    d.arc([cx - r - 14, cy - 6, cx + r + 14, cy + 6], 160, 380, fill=P[LIGHT_GREY])
    d.arc([cx - r - 13, cy - 5, cx + r + 13, cy + 5], 160, 380, fill=P[WHITE])


def ship(d, x, y, flame=True):
    """The ship, pointing right, its nose at (x, y)."""
    d.polygon([(x, y), (x - 12, y - 4), (x - 9, y), (x - 12, y + 4)], fill=P[WHITE])
    d.polygon([(x - 6, y - 2), (x - 14, y - 8), (x - 10, y - 1)], fill=P[LIGHT_GREY])
    d.polygon([(x - 6, y + 2), (x - 14, y + 8), (x - 10, y + 1)], fill=P[LIGHT_GREY])
    d.rectangle([x - 5, y - 1, x - 3, y], fill=P[BLUE])
    if flame:
        d.polygon([(x - 11, y - 2), (x - 17, y), (x - 11, y + 2)], fill=P[ORANGE])
        d.point((x - 13, y), fill=P[YELLOW])


def label_screen():
    img = Image.new("RGB", (128, 128), P[BLACK])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 96, 127, 127], fill=P[DARK_BLUE])
    stars(img, 8)
    planet(d, 94, 82, 18)
    ship(d, 52, 66)
    title = "ODYSSEY"
    text(img, (128 - width(title, 3)) // 2, 14, title, WHITE, 3, shadow=DARK_BLUE)
    d.rectangle([20, 34, 107, 34], fill=P[PINK])
    hint = "PRESS X TO LAUNCH"
    text(img, (128 - width(hint)) // 2, 112, hint, LIGHT_GREY)
    return img


def noise_screen():
    img = Image.new("RGB", (128, 128), P[BLACK])
    rng = random.Random(80)
    for y in range(128):
        run = rng.choice([1, 2, 3, 5, 8])
        colour = None
        for x in range(128):
            if x % run == 0:
                colour = P[rng.choice([BLACK, BLACK, DARK_BLUE, DARK_PURPLE, DARK_GREY, LIGHT_GREY, WHITE, RED, ORANGE,
                                       YELLOW, GREEN, BLUE, PINK])]
            img.putpixel((x, y), colour)
    return img


def boot_screen():
    img = Image.new("RGB", (128, 128), P[BLACK])
    logo(img, 0, 1)
    text(img, 1, 18, "PICO-8 0.2.6", LIGHT_GREY)
    text(img, 1, 25, "(C) LEXALOFFLE GAMES", LIGHT_GREY)
    text(img, 1, 38, "> LOAD ODYSSEY", WHITE)
    return img


def game_screen(frame):
    img = Image.new("RGB", (128, 128), P[BLACK])
    d = ImageDraw.Draw(img)
    stars(img, 30 + frame, 54)
    planet(d, 104, 104, 12)
    sy = 64 if frame == 1 else 56
    ship(d, 40, sy)
    for k in range(3):                                         # lives
        ship(d, 124 - k * 10, 6, flame=False)
    text(img, 2, 2, f"SCORE {120 if frame == 1 else 170:05d}", WHITE)
    if frame == 1:
        d.line([(44, sy), (80, sy)], fill=P[YELLOW])
        d.line([(44, sy + 1), (80, sy + 1)], fill=P[ORANGE])
        for cx, cy, r in ((90, sy - 1, 7), (108, 34, 5), (76, 96, 6)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=P[BROWN], outline=P[DARK_GREY])
            d.point((cx - r // 2, cy - r // 2), fill=P[PEACH])
    else:
        rng = random.Random(7)
        for _ in range(40):                                     # the asteroid blowing up
            a, b = rng.randint(-9, 9), rng.randint(-9, 9)
            if a * a + b * b <= 81:
                d.point((90 + a, 63 + b), fill=P[rng.choice([YELLOW, ORANGE, RED, WHITE])])
        for cx, cy, r in ((106, 38, 5), (74, 92, 6)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=P[BROWN], outline=P[DARK_GREY])
        text(img, 84, 50, "+50", YELLOW)
    return img


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), P[BLACK])
    screens = dict(label=label_screen(), noise=noise_screen(), boot=boot_screen(), game1=game_screen(1),
                   game2=game_screen(2))
    for name, art in screens.items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(art.resize((w, h), Image.NEAREST), (x, y))
    path = os.path.join(out, "pico8_media.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
