"""The Acorn Archimedes card's printing and screens (archimedes_print.png, archimedes_media.png), for the console
theme's model (archimedes.py).

`archimedes_print.png`, laid out as archimedes_layout.REGIONS says: the A3000 from above (the keys' tops and legends,
the red function keys, the two grilles, the BBC badge at the keypad's head), the monitor's front (its bezel, Acorn and
the green acorn, the power switch and its light), the Acorn badge, the floppy's top (a made-up game, Odyssey), the mouse
from above (its three buttons), and swatches. `archimedes_media.png`: the screens, drawn at RISC OS's 640 x 512 (the
desktop and its icon bar; the floppy's filer window with !Odyssey in it; two moments of the game, full screen). Run it
with the system Python (Pillow):

    python tools/console-models/archimedes_print.py <out folder>
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archimedes_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
RED = rgb(L.COLOURS["red"])
MONITOR = rgb(L.COLOURS["monitor"])
INK = (60, 58, 54)
GREEN = (60, 150, 60)
BRASS = (196, 170, 96)


def shade(colour, k):
    return tuple(max(0, min(255, round(c * (1 + k)))) for c in colour)


def acorn(reg, x, y, h, fill):
    """Acorn's acorn, h tall, its middle at (x, y): the nut, its cup and its stalk."""
    reg.draw.ellipse(reg.box(x - 0.38 * h, y - 0.3 * h, x + 0.38 * h, y + 0.5 * h), fill=fill)
    reg.draw.chord(reg.box(x - 0.46 * h, y - 0.5 * h, x + 0.46 * h, y + 0.1 * h), 180, 360, fill=shade(fill, -0.3))
    reg.rect_(x - 0.04 * h, y - 0.6 * h, x + 0.04 * h, y - 0.4 * h, shade(fill, -0.3))


# ---- The print -------------------------------------------------------------------------------------------------------

def deck():
    """The A3000 from above: x across (-WIDTH/2 at the left), y down from the back to the front."""
    reg = Region(L.REGIONS["deck"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    for g in L.GRILLES:                                     # the grilles' slots, running back to front
        (x0, x1), (y0, y1) = g["x"], g["y"]
        n = int((x1 - x0) / 5.2)
        for k in range(n):
            x = x0 + (x1 - x0) * (k + 0.5) / n
            reg.rect_(*at(x - 1.3, y1), *at(x + 1.3, y0), shade(CASE, -0.45), r=1.2)
    (bx0, bx1) = L.BBC["x"]
    y0, y1 = (L.deck_point(L.row_s(0) - 8.0, 0.0)[0], L.deck_point(L.row_s(0) + 8.0, 0.0)[0])
    xa, xb = L.KEYS_X0 + bx0 * L.U, L.KEYS_X0 + bx1 * L.U
    reg.rect_(*at(xa, y1), *at(xb, y0), (200, 186, 120), r=1.0)
    reg.rect_(*at(xa + 2.0, y1 - 2.0), *at(xa + 40.0, y0 + 2.0), (40, 40, 44))
    for k, line in enumerate(("BRITISH", "BROADCASTING", "CORPORATION")):
        reg.text(line, "arialbd.ttf", 2.6, *at(xa + 4.0, y1 - 4.5 - 3.4 * k), (230, 230, 226), anchor="lm")
    reg.rect_(*at(xa + 44.0, y1 - 2.0), *at(xb - 2.0, y0 + 2.0), (110, 170, 80))
    reg.text("A3000", "ariblk.ttf", 7.0, *at((xa + 44.0 + xb) / 2, (y0 + y1) / 2), (240, 240, 230))

    top_h, inset = L.KEY["height"], L.KEY["inset"]
    for legend, x0, x1, s0, s1 in L.keys():
        ya = L.deck_point(s0 + inset - 0.5, top_h)[0]
        yb = L.deck_point(s1 - inset + 0.5, top_h)[0]
        fill = RED if legend[0] == "F" and legend[1:].isdigit() else KEY
        reg.rect_(*at(x0 + inset, yb), *at(x1 - inset, ya), fill, r=1.2)
        x, y = at(x0 + inset + 1.4, yb)
        ink = (250, 236, 228) if fill == RED else INK
        if len(legend) == 1 and legend != " ":
            reg.text(legend, "seguisym.ttf" if ord(legend) > 0x2000 else "arial.ttf", 3.8, x, y + 3.2, ink,
                     anchor="lm")
        elif legend.strip():
            for k, word in enumerate(legend.split(" ")):
                reg.text(word, "arial.ttf", 2.2, x, y + 2.6 + 2.6 * k, ink, anchor="lm")
    return reg


def badge():
    """The Acorn badge: a brass plate, Acorn in dark italic, the green acorn."""
    (x0, x1), (z0, z1) = L.BADGE["x"], L.BADGE["z"]
    w, h = x1 - x0, z1 - z0
    reg = Region(L.REGIONS["badge"], w, h, BRASS)
    reg.rect_(0.6, 0.6, w - 0.6, h - 0.6, None, r=1.0, outline=shade(BRASS, -0.3), width=0.4)
    reg.text("Acorn", "timesbi.ttf", 9.0, 4.0, h / 2, (50, 40, 30), anchor="lm")
    acorn(reg, w - 9.0, h / 2, 9.0, GREEN)
    return reg


def bezel():
    """The monitor's front: x across, z down from its top; the opening dark, Acorn, the power switch and its light."""
    w, h = L.MONITOR["width"], L.MONITOR["height"]
    reg = Region(L.REGIONS["bezel"], w, h, MONITOR)
    fw, fh, r = L.SCREEN["frame"]
    zc = h - (L.SCREEN["z"] - L.MONITOR["base"][1])
    reg.rect_(w / 2 - fw / 2 - 4.0, zc - fh / 2 - 4.0, w / 2 + fw / 2 + 4.0, zc + fh / 2 + 4.0, shade(MONITOR, -0.08),
              r=r + 4.0)
    reg.rect_(w / 2 - fw / 2, zc - fh / 2, w / 2 + fw / 2, zc + fh / 2, (20, 20, 22), r=r)
    reg.text("Acorn", "timesbi.ttf", 12.0, 26.0, h - 22.0, (70, 66, 60), anchor="lm")
    acorn(reg, 70.0, h - 22.0, 11.0, GREEN)
    reg.rect_(w - 64.0, h - 30.0, w - 30.0, h - 14.0, shade(MONITOR, -0.12), r=2.0)
    reg.circle(w - 22.0, h - 22.0, 2.4, (40, 200, 60))
    return reg


def floppy():
    """The floppy's top: x across, y down from its shutter's edge (the end going in) to its label's."""
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
    """The mouse from above: x across, y back from its front (the buttons' end)."""
    w, length, _ = L.MOUSE["size"]
    reg = Region(L.REGIONS["mouse"], w, length, CASE)
    bw = (w - 12.0) / 3
    for k in range(3):
        reg.rect_(6.0 + k * bw + 1.0, 6.0, 6.0 + (k + 1) * bw - 1.0, 34.0, shade(CASE, -0.12), r=1.5)
    return reg


# ---- The screens -----------------------------------------------------------------------------------------------------

W, H = 640, 512
GREY = (187, 187, 187)
BAR = (221, 221, 221)


def font(size, bold=False):
    return ImageFont.truetype(FONTS + ("arialbd.ttf" if bold else "arial.ttf"), size)


def disc_icon(d, x, y):
    """The floppy drive's icon on the icon bar, its top left at (x, y), and its name under it."""
    d.rectangle([x, y, x + 34, y + 30], fill=(40, 60, 140), outline=(0, 0, 0))
    d.rectangle([x + 9, y, x + 25, y + 11], fill=(200, 200, 204), outline=(0, 0, 0))
    d.rectangle([x + 6, y + 15, x + 28, y + 30], fill=(250, 250, 250), outline=(0, 0, 0))
    d.text((x + 17, y + 38), ":0", font=font(13), fill=(0, 0, 0), anchor="mm")


def icon_bar(img):
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 64, W - 1, H - 1], fill=BAR)
    d.line([0, H - 64, W - 1, H - 64], fill=(255, 255, 255), width=2)
    disc_icon(d, 20, H - 56)
    d.rectangle([80, H - 54, 110, H - 26], fill=(220, 180, 60), outline=(0, 0, 0))   # Apps
    d.text((95, H - 18), "Apps", font=font(13), fill=(0, 0, 0), anchor="mm")
    x = W - 46                                                # the Acorn icon at the right
    d.ellipse([x, H - 52, x + 26, H - 20], fill=(70, 150, 60), outline=(0, 0, 0))
    d.chord([x - 4, H - 58, x + 30, H - 34], 180, 360, fill=(110, 80, 40), outline=(0, 0, 0))
    d.rectangle([W - 96, H - 52, W - 66, H - 22], fill=(255, 255, 255), outline=(0, 0, 0))   # the palette
    for k, colour in enumerate(((220, 40, 40), (40, 180, 40), (40, 80, 220), (240, 200, 40))):
        d.rectangle([W - 92 + (k % 2) * 13, H - 48 + (k // 2) * 13, W - 81 + (k % 2) * 13, H - 37 + (k // 2) * 13],
                    fill=colour)


def desktop():
    img = Image.new("RGB", (W, H), GREY)
    icon_bar(img)
    return img


def filer():
    """The desktop and the floppy's filer window, !Odyssey in it."""
    img = desktop()
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 150, 90, 520, 330
    d.rectangle([x0 + 4, y0 + 4, x1 + 4, y1 + 4], fill=(110, 110, 110))
    d.rectangle([x0, y0, x1, y1], fill=(255, 255, 255), outline=(0, 0, 0))
    d.rectangle([x0, y0, x1, y0 + 24], fill=(255, 255, 190), outline=(0, 0, 0))     # the title bar, with input focus
    for xx in (x0, x0 + 24, x1 - 24):
        d.rectangle([xx, y0, xx + 24, y0 + 24], fill=(220, 220, 220), outline=(0, 0, 0))
    d.text(((x0 + x1) // 2, y0 + 12), "adfs::0.$", font=font(15), fill=(0, 0, 0), anchor="mm")
    d.rectangle([x1 - 20, y0 + 24, x1, y1], fill=(200, 230, 255), outline=(0, 0, 0))  # the scroll bar
    d.rectangle([x1 - 17, y0 + 50, x1 - 3, y1 - 80], fill=(150, 200, 240))
    art = Image.new("RGB", (60, 60), (10, 10, 40))           # !Odyssey's sprite: the ship by the planet
    ad = ImageDraw.Draw(art)
    ad.ellipse([30, 14, 56, 40], fill=(240, 140, 60))
    ship(ad, 18, 30, 0.9, "#FFFFFF", "#FFB23C")
    img.paste(art, (x0 + 40, y0 + 50))
    d.rectangle([x0 + 40, y0 + 50, x0 + 100, y0 + 110], outline=(0, 0, 0))
    d.text((x0 + 70, y0 + 126), "!Odyssey", font=font(15), fill=(0, 0, 0), anchor="mm")
    for k, name in enumerate(("!Help", "Levels")):
        xx = x0 + 160 + k * 100
        d.rectangle([xx, y0 + 66, xx + 34, y0 + 100], fill=(240, 240, 240), outline=(0, 0, 0))
        d.text((xx + 17, y0 + 126), name, font=font(15), fill=(0, 0, 0), anchor="mm")
    d.polygon([(x0 + 90, y0 + 90), (x0 + 90, y0 + 112), (x0 + 96, y0 + 106), (x0 + 101, y0 + 116),
               (x0 + 104, y0 + 114), (x0 + 99, y0 + 104), (x0 + 107, y0 + 104)], fill=(60, 60, 220),
              outline=(0, 0, 0))                                                          # the pointer
    return img


def game(frame):
    """The game full screen: space, the ship firing at the ringed planet, the score."""
    img = Image.new("RGB", (W, H), (8, 6, 30))
    d = ImageDraw.Draw(img)
    rng = random.Random(9)
    for _ in range(80):
        x, y = rng.randrange(W), rng.randrange(H)
        d.point(((x - frame * 24) % W, y), fill=(255, 255, 255))
    d.ellipse([400 - 20 * frame, 150, 540 - 20 * frame, 290], fill=(240, 140, 60))
    d.ellipse([310 - 20 * frame, 205, 630 - 20 * frame, 235], outline=(250, 250, 250), width=3)
    ship(d, 150, 230 + 30 * frame, 4.0, "#FFFFFF", "#FFB23C")
    for k in range(3):
        d.line([(230 + 60 * k + 20 * frame, 230 + 30 * frame), (256 + 60 * k + 20 * frame, 230 + 30 * frame)],
               fill=(255, 230, 80), width=4)
    d.text((24, 22), "SCORE %05d" % (2600 + 400 * frame), font=font(22, True), fill=(255, 230, 80), anchor="lm")
    d.text((W - 24, 22), "ODYSSEY", font=font(22, True), fill=(120, 220, 255), anchor="rm")
    return img


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    for name, screen in (("desktop", desktop()), ("filer", filer()), ("game_1", game(0)), ("game_2", game(1))):
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(screen.resize((w, h), Image.LANCZOS), (x, y))
    path = os.path.join(out, "archimedes_media.png")
    image.save(path, optimize=True)
    print(path)


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (deck(), badge(), bezel(), floppy(), mouse()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, key=KEY, red=RED, monitor=MONITOR, dark=(14, 14, 14), light=(60, 70, 60),
                   lit=(60, 240, 80), floppy=(52, 58, 72), cord=(210, 204, 190))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "archimedes_print.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
