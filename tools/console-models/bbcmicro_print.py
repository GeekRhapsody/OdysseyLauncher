"""The BBC Micro card's printing and screens (bbcmicro_print.png), for the console theme's model (bbcmicro.py).

One image, laid out as bbcmicro_layout.REGIONS says: the keyboard panel from above (the keys' tops and legends where
they stand, the clear strip with the speaker's grille, BRITISH BROADCASTING CORPORATION MICROCOMPUTER SYSTEM and the
owl, the blank plate, the three lights and their legends), the screens (Mode 7's boot screen and a made-up game's title,
Odyssey, in teletext; two moments of its play in Mode 2's eight colours), the monitor's bezel (CUB, the power switch),
the drive's front (its two drives), the floppy's top (its label), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/bbcmicro_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbcmicro_layout as L  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

PANEL = (28, 27, 30)
KEY = dict(black=(42, 38, 36), red=(200, 58, 46), brown=(92, 82, 72))
LEGEND = (236, 236, 236)
CREAM = (214, 200, 160)
# Mode 2's and Mode 7's eight colours.
COLOURS = dict(black=(0, 0, 0), red=(255, 0, 0), green=(0, 255, 0), yellow=(255, 255, 0), blue=(0, 0, 255),
               magenta=(255, 0, 255), cyan=(0, 255, 255), white=(255, 255, 255))


# ---- The keyboard panel ----------------------------------------------------------------------------------------------

def panel():
    """The panel from above: x across (-180 at the left), y down from its back (182)."""
    (x0, x1), (y0, y1) = L.PANEL["x"], L.PANEL["y"]
    reg = Region(L.REGIONS["panel"], x1 - x0, y1 - y0, PANEL)

    def at(x, y):
        return x - x0, y1 - y

    # The strip: the grille's slots at its left, the name and the owl at its right.
    s0, s1 = L.STRIP["y"]
    reg.rect_(*at(x0, s1), *at(x1, s0), (38, 38, 42))
    for k in range(8):
        x = -172.0 + k * 5.0
        reg.rect_(*at(x, s1 - 4.0), *at(x + 2.2, s0 + 4.0), (10, 10, 12), r=1.0)
    reg.text("BRITISH BROADCASTING CORPORATION", "times.ttf", 2.6, *at(118.0, s1 - 6.0), CREAM, anchor="rm")
    reg.text("MICROCOMPUTER SYSTEM", "times.ttf", 4.4, *at(118.0, s0 + 7.0), CREAM, anchor="rm")
    rng = random.Random(4)
    for i in range(7):                                          # the owl, a pattern of dots
        for j in range(6):
            if (i - 3) ** 2 / 9 + (j - 2.5) ** 2 / 7 < 1.1 and rng.random() < 0.85:
                reg.rect_(*at(126.0 + i * 3.0, s1 - 3.5 - j * 2.6), *at(127.8 + i * 3.0, s1 - 5.1 - j * 2.6), CREAM)
    # The blank plate and the lights.
    (p0, p1), (q0, q1) = L.PLATE["x"], L.PLATE["y"]
    reg.rect_(*at(p0, q1), *at(p1, q0), (18, 18, 20), r=1.5)
    for x, label, lit in zip(L.LIGHTS["x"], ("cassette\nmotor", "caps\nlock", "shift\nlock"), (False, True, False)):
        reg.circle(*at(x, L.LIGHTS["y"]), 1.6, (255, 40, 30) if lit else (90, 20, 18), outline=(60, 60, 64), width=0.3)
        for k, line in enumerate(label.split("\n")):
            reg.text(line, "arial.ttf", 2.4, *at(x, L.LIGHTS["y"] + 8.0 - k * 2.8), CREAM)
    # The keys' tops: each its colour, its legend.
    for legend, colour, kx0, kx1, ky in L.keys():
        reg.rect_(*at(kx0 + 2.8, ky + 6.8), *at(kx1 - 2.8, ky - 6.8), KEY[colour], r=1.4)
        if legend.strip():
            size = 4.6 if len(legend) <= 2 else 2.2
            lines = legend.split(" ") if len(legend) > 6 and " " in legend else [legend]
            for k, line in enumerate(lines):
                dy = (len(lines) - 1) * 1.4 - k * 2.8
                reg.text(line, "arialbd.ttf" if len(legend) > 2 else "arial.ttf", size, *at((kx0 + kx1) / 2, ky + dy),
                         LEGEND)
    return reg


# ---- The screens -----------------------------------------------------------------------------------------------------

def mode7(cells, sixels=None):
    """A Mode 7 screen: 40 x 25 cells of (row, column, text, colour, double); sixels (x, y, colour) on its 80 x 75
    block grid."""
    w, h = 480, 360
    cw, ch = w / 40, h / 25
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for x, y, colour in sixels or []:
        d.rectangle([x * cw / 2, y * ch / 3, (x + 1) * cw / 2 - 1, (y + 1) * ch / 3 - 1], fill=COLOURS[colour])
    font = ImageFont.truetype(FONTS + "consolab.ttf", round(ch * 0.95))
    for row, col, text, colour, double in cells:
        if double:
            layer = Image.new("L", (round(cw * len(text)), round(ch)), 0)
            ImageDraw.Draw(layer).text((0, 0), text, font=font, fill=255)
            layer = layer.resize((layer.width, round(ch * 2)), Image.NEAREST)
            img.paste(COLOURS[colour], (round(col * cw), round(row * ch)), layer)
        else:
            d.text((col * cw, row * ch), text, font=font, fill=COLOURS[colour])
    return img


def boot():
    return mode7([(0, 0, "BBC Computer 32K", "white", False), (2, 0, "Acorn DFS", "white", False),
                  (4, 0, "BASIC", "white", False), (6, 0, ">_", "white", False)])


BLOCK_FONT = {   # 5 x 7, for teletext's block-graphics titles
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
}


def title():
    sixels = []
    word = "ODYSSEY"
    x0 = (80 - (len(word) * 6 - 1)) // 2
    for k, letter in enumerate(word):                           # the title in block graphics
        for j, row in enumerate(BLOCK_FONT[letter]):
            for i, bit in enumerate(row):
                if bit == "#":
                    sixels.append((x0 + k * 6 + i, 5 + j, "yellow"))
    cx, cy, r = 52, 44, 12
    for y in range(75):
        for x in range(80):
            dx, dy = (x - cx) / r, (y - cy) / (r * 1.0)
            if dx * dx + dy * dy <= 1.0:
                sixels.append((x, y, "red" if dx + dy > -0.4 else "yellow"))
            elif abs((x - cx) ** 2 / (2.0 * r) ** 2 + (y - cy) ** 2 / (0.4 * r) ** 2 - 1.0) < 0.12 and not (
                    dy < 0 and abs(dx) < 1.0):
                sixels.append((x, y, "white"))
    for x, y in ((8, 22), (20, 30), (70, 18), (14, 56), (36, 64), (66, 62), (30, 14), (76, 50)):
        sixels.append((x, y, "white"))
    for x, y in ((16, 45), (17, 45), (18, 45), (19, 45), (20, 45), (17, 44), (18, 44), (17, 46), (18, 46), (14, 43),
                 (14, 47), (15, 44), (15, 46)):
        sixels.append((x, y, "cyan"))
    return mode7([(21, 14, "PRESS SPACE", "cyan", True), (24, 8, "Z / X  MOVE   RETURN  FIRE", "green", False)],
                 sixels)


def game(frame):
    """A moment of play in Mode 2: 160 x 256 logical pixels, shown at 4:3 as blocks."""
    w, h = 480, 360
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    px, py = w / 160, h / 128

    def block(x, y, colour, size=1):
        d.rectangle([x * px, y * py, (x + size) * px - 1, (y + size) * py - 1], fill=COLOURS[colour])

    rng = random.Random(9 + frame)
    for _ in range(40):
        block(rng.randrange(160), rng.randrange(14, 128), "white")
    ship_x = (62, 84)[frame]
    for dx, dy, colour in ((0, 0, "yellow"), (-1, 1, "yellow"), (1, 1, "yellow"), (0, 1, "white"), (-2, 2, "yellow"),
                           (2, 2, "yellow"), (-1, 2, "white"), (0, 2, "white"), (1, 2, "white")):
        block(ship_x + dx * 3, 108 + dy * 3, colour, 3)
    for k, (x, y, s) in enumerate(((30, 40, 9), (110, 30, 12), (80, 66, 7))):
        y += frame * 6
        for i in range(-s, s + 1, 2):
            for j in range(-s, s + 1, 2):
                if i * i + j * j <= s * s:
                    block(x + i, y + j, "magenta" if (i + j) % 4 else "red", 2)
    if frame == 1:
        for j in range(4):
            block(ship_x, 96 - j * 8, "cyan", 2)
    font = ImageFont.truetype(FONTS + "consolab.ttf", 22)
    d.text((12, 6), "SCORE 0" + ("120" if frame == 0 else "240"), font=font, fill=COLOURS["yellow"])
    d.text((330, 6), "SHIPS 3", font=font, fill=COLOURS["green"])
    return img


# ---- The monitor, the drive, the floppy ------------------------------------------------------------------------------

def bezel():
    """The monitor's front: x across (-176 at the left), z down from its top (300)."""
    w, h = L.MONITOR["width"], L.MONITOR["height"]
    reg = Region(L.REGIONS["bezel"], w, h, rgb(L.COLOURS["bezel"]))
    reg.rect_(4.0, 4.0, w - 4.0, h - 4.0, None, r=6.0, outline=(72, 60, 52), width=1.2)
    sw, sh = L.SCREEN["size"]
    cz = h - L.SCREEN["z"]
    reg.rect_(w / 2 - sw / 2 - 8.0, cz - sh / 2 - 8.0, w / 2 + sw / 2 + 8.0, cz + sh / 2 + 8.0, (24, 20, 18), r=18.0)
    for k, (letter, colour) in enumerate((("C", (214, 50, 40)), ("U", (60, 170, 70)), ("B", (60, 90, 200)))):
        reg.text(letter, "arialbd.ttf", 9.0, 36.0 + k * 7.0, h - 16.0, colour)
    reg.rect_(w - 40.0, h - 20.0, w - 30.0, h - 12.0, (200, 40, 34), r=1.5)
    return reg


def drive():
    """The drive's front: x across (-180 at the left), z down from its top (80)."""
    w, h = L.DRIVE["width"], L.DRIVE["height"]
    reg = Region(L.REGIONS["drive"], w, h, rgb(L.COLOURS["case"]))
    bw, bh = L.BAYS["size"]
    sw, sh = L.BAYS["slot"]
    for k, x in enumerate(L.BAYS["x"]):
        cx, cz = x + w / 2, h - L.BAYS["z"]
        reg.rect_(cx - bw / 2, cz - bh / 2, cx + bw / 2, cz + bh / 2, (60, 58, 56), r=2.0)
        reg.rect_(cx - sw / 2, cz - sh / 2, cx + sw / 2, cz + sh / 2, (8, 8, 10), r=1.0)
        reg.circle(cx - bw / 2 + 10.0, cz + bh / 2 - 8.0, 1.8, (90, 20, 18))
        reg.text(str(k), "arialbd.ttf", 4.0, cx - bw / 2 + 10.0, cz + bh / 2 - 16.0, (200, 196, 186))
    return reg


def floppy():
    """The floppy's top: x across; down the image from its trailing edge (the label's) to the edge that goes in
    first."""
    s = L.FLOPPY["size"]
    reg = Region(L.REGIONS["floppy"], s, s, (24, 24, 26))
    lw, lh = L.FLOPPY["label"]
    reg.rect_((s - lw) / 2, 4.0, (s + lw) / 2, 4.0 + lh, (244, 242, 236), r=1.0)
    for k in range(4):
        reg.line([((s - lw) / 2 + 3.0, 12.0 + k * 7.0), ((s + lw) / 2 - 3.0, 12.0 + k * 7.0)], (170, 190, 220), 0.3)
    reg.text("ODYSSEY", "segoeprb.ttf", 9.0, s / 2, 16.0, (40, 60, 170))
    reg.text("CHAIN \"ODYSSEY\"", "segoepr.ttf", 4.6, s / 2, 30.0, (40, 60, 170))
    reg.circle(s / 2, s / 2 + 6.0, 19.0, (80, 76, 70))
    reg.circle(s / 2, s / 2 + 6.0, 14.0, (24, 24, 26))
    reg.rect_(s / 2 - 6.0, s - 40.0, s / 2 + 6.0, s - 6.0, (80, 76, 70), r=6.0)
    reg.circle(s / 2 + 26.0, s / 2 + 6.0, 2.0, (80, 76, 70))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["case"]))
    for reg in (panel(), bezel(), drive(), floppy()):
        reg.paste(image)
    for name, screen in (("boot", boot()), ("title", title()), ("game_1", game(0)), ("game_2", game(1))):
        x, y, w, h = L.REGIONS[name]
        image.paste(screen.resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(image)
    colours = dict(case=rgb(L.COLOURS["case"]), monitor=rgb(L.COLOURS["monitor"]), bezel=rgb(L.COLOURS["bezel"]),
                   black=KEY["black"], red=KEY["red"], brown=KEY["brown"], dark=(10, 10, 12), lit=(255, 50, 30),
                   floppy=(24, 24, 26), grey=(60, 58, 56))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "bbcmicro_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
