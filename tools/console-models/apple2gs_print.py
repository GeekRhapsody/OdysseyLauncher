"""The Apple IIGS set's printing and screens, for the console theme's Apple IIGS model (tools/console-models/apple2gs.py).

Draws its two atlases, their regions as apple2gs_layout.py places them. apple2gs_print.png, each in millimetres as the
model's UVs map it: the keyboard seen from above (each key's top with its legend, the blank column's joins, the strip
behind with the apple and the power key), the IIGS's front (the rainbow apple and Apple IIGS), the monitor's front
frame (the apple, the power switch), the drive's front (the slot's lips, its label, its light, the apple), the mouse's
top, and the swatches small parts take their colour from. apple2gs_media.png: the screens, each the glass's whole area
(Check startup device! as the IIGS shows it without a disk, white on its medium blue, the rainbow apple; GS/OS
starting, its welcome box and its bar; the title screen of a made-up game, Odyssey, and a moment of its play), and the
3.5-inch disk's two sides. Run it with the system Python (Pillow):

    python tools/console-models/apple2gs_print.py <out folder>

It writes apple2gs_print.png and apple2gs_media.png there.
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apple2gs_layout as L  # noqa: E402
from apple2_print import apple  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
LEGEND = (64, 66, 80)


# ---- The printing ------------------------------------------------------------------------------------------------------

def keyboard():
    w, d = L.KEYBOARD["width"], L.KEYBOARD["depth"] + L.STRIP["depth"]
    reg = Region(L.REGIONS["keyboard"], w, d, CASE)

    def at(x, s):
        return x + w / 2, d - s
    i = L.KEY_INSET
    apple(reg, *at(*L.STRIP_APPLE), 8.0, rainbow=True)
    (px0, px1), (ps0, ps1) = L.POWER["x"], L.POWER["s"]
    (ax, ay), (bx, by) = at(px0 + i, ps1 - i), at(px1 - i, ps0 + i)
    reg.rect_(ax - 0.5, ay - 0.5, bx + 0.5, by + 0.5, shade(KEY, 0.04), r=1.2)
    tx, ty = ax + 5.0, (ay + by) / 2                                      # the power key's triangle, pointing left
    reg.line([(tx + 3.6, ty - 2.4), (tx, ty), (tx + 3.6, ty + 2.4), (tx + 3.6, ty - 2.4)], LEGEND, 0.35)
    x0, x1 = L.kx(L.BLANK[0]) + L.GAP / 2, L.kx(L.BLANK[1]) - L.GAP / 2   # the blank column's joins, row by row
    for row in (4, 3, 2, 1):
        reg.line([at(x0, L.ROW_S[row]), at(x1, L.ROW_S[row])], shade(CASE, -0.22), 0.5)
    for name, xu, row, wu, legend, *rest in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu, rest[0] if rest else 1)
        (ax, ay), (bx, by) = at(x0 + i, s1 - i), at(x1 - i, s0 + i)
        kw, kh = bx - ax, by - ay
        reg.rect_(ax - 0.5, ay - 0.5, bx + 0.5, by + 0.5, shade(KEY, 0.04), r=1.2)
        if name == "apple":                                               # the open apple and the command sign
            apple(reg, ax + 3.4, ay + kh * 0.55, 3.4, outline=LEGEND, width=0.3)
            reg.text(legend, "seguisym.ttf", 3.2, bx - 3.4, ay + kh * 0.55, LEGEND)
            continue
        if not legend:
            continue
        lines = legend.split("\n")
        if len(lines) == 1 and len(legend) == 1:
            font = "seguisym.ttf" if not legend.isascii() else "arial.ttf"
            reg.text(legend, font, 3.4, ax + kw * 0.35, ay + kh * 0.55, LEGEND)
        elif all(len(line) == 1 for line in lines):                       # a symbol over a digit
            for k, line in enumerate(lines):
                reg.text(line, "arial.ttf", 2.8, ax + 2.4, ay + kh * (0.33 + 0.34 * k), LEGEND, anchor="lm")
        else:                                                             # words, at the foot of the key
            for k, line in enumerate(lines):
                reg.text(line, "arial.ttf", 2.1, ax + 1.8, ay + kh * 0.74 - (len(lines) - 1 - k) * 3.0, LEGEND,
                         anchor="lm")
    return reg


def front():
    w, h = L.WIDTH, L.BOX["z"][1] - L.BOX["z"][0]
    reg = Region(L.REGIONS["front"], w, h, CASE)
    apple(reg, 20.0, h - 22.0, 9.0, rainbow=True)
    reg.text("Apple IIGS", "times.ttf", 7.0, 28.0, h - 21.5, (70, 68, 64), anchor="lm")
    return reg


def monitor():
    M = L.MONITOR
    w, h = M["width"], M["height"]
    reg = Region(L.REGIONS["monitor"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    apple(reg, *at(-128.0, 24.0), 9.0, rainbow=True)
    sx, sz = M["switch"]
    reg.rect_(*at(sx - 0.8, sz + 5.0), *at(sx + 0.8, sz - 5.0), (70, 72, 64))
    return reg


def drive():
    w, d, h = L.DRIVE["size"]
    reg = Region(L.REGIONS["drive"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    x0, x1, z0, z1 = L.DRIVE["slot"]
    reg.rect_(*at(x0 - 1.5, z1 + 1.5), *at(x1 + 1.5, z0 - 1.5), shade(CASE, -0.12), r=1.0)   # the slot's lips
    lx0, lx1, lz0, lz1 = L.DRIVE["label"]
    reg.rect_(*at(lx0, lz1), *at(lx1, lz0), (240, 238, 230), r=0.6)
    reg.text("3.5 DRIVE", "arial.ttf", 2.2, *at(lx0 + 2.0, lz0 + 6.5), (110, 120, 150), anchor="lm")
    lx, lz = L.DRIVE["light"]
    reg.rect_(*at(lx - 2.5, lz + 0.8), *at(lx + 2.5, lz - 0.8), (70, 34, 26))
    ex0, ex1, ez0, ez1 = L.DRIVE["eject"]
    reg.rect_(*at(ex0 - 0.6, ez1 + 0.6), *at(ex1 + 0.6, ez0 - 0.6), shade(CASE, -0.35))      # the eject button's gap
    apple(reg, *at(-40.0, 12.0), 9.0, rainbow=True)
    return reg


def mouse():
    w, d, _ = L.MOUSE["size"]
    reg = Region(L.REGIONS["mouse"], w, d, CASE)
    reg.rect_(4.0, 4.0, w - 4.0, L.MOUSE["button"], shade(CASE, 0.03), r=3.0)
    reg.line([(4.0, L.MOUSE["button"]), (w - 4.0, L.MOUSE["button"])], shade(CASE, -0.3), 0.6)
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (keyboard(), front(), monitor(), drive(), mouse()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("green", (110, 255, 120)), ("dark", rgb(L.COLOURS["dark"])), ("lit", (255, 96, 60)),
                         ("case", CASE)):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "apple2gs_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -------------------------------------------------------------------------------------------------------

W, H = 320, 200                                    # the IIGS's super hi-res screen, its 320 mode
BLUE = (36, 56, 214)


def check():
    img = Image.new("RGB", (W * 4, H * 4), BLUE)
    reg = Region((0, 0, W * 4, H * 4), W, H, BLUE)
    apple(reg, W / 2, H * 0.42, 34.0, rainbow=True)
    reg.text("Check startup device!", "consolab.ttf", 9.0, W / 2, H * 0.72, (250, 250, 250))
    img.paste(reg.img.convert("RGB").resize(img.size, Image.LANCZOS), (0, 0))
    return img


def boot():
    reg = Region((0, 0, W * 4, H * 4), W, H, (200, 200, 204))
    for y in range(0, H, 2):                       # the desktop's grey dither, line by line
        reg.line([(0, y), (W, y)], (176, 176, 182), 0.5)
    reg.rect_(70.0, 50.0, 250.0, 150.0, (255, 255, 255), outline=(20, 20, 22), width=1.0)
    apple(reg, 100.0, 86.0, 26.0, rainbow=True)
    reg.text("Apple IIGS", "timesbd.ttf", 15.0, 116.0, 80.0, (20, 20, 22), anchor="lm")
    reg.text("GS/OS", "arialbd.ttf", 9.0, 116.0, 96.0, (20, 20, 22), anchor="lm")
    reg.rect_(90.0, 120.0, 230.0, 130.0, (255, 255, 255), outline=(20, 20, 22), width=0.8)
    reg.rect_(91.0, 121.0, 170.0, 129.0, (20, 20, 22))
    return reg.img.convert("RGB")


def title():
    img = space((W * 4, H * 4)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((W * 2, 64), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 150), fill=(255, 214, 70),
           anchor="mt", stroke_width=6, stroke_fill=(120, 30, 10))
    ship(d, 360, 470, 6.0, "#FFFFFF", "#FFB23C")
    d.text((W * 2, 700), "PRESS RETURN TO PLAY", font=ImageFont.truetype(FONTS + "arialbd.ttf", 44),
           fill=(255, 255, 255), anchor="mm")
    return img


def game():
    """A moment of Odyssey's play: the ship firing at the asteroids, the score along the top."""
    img = space((W * 4, H * 4)).convert("RGB")
    d = ImageDraw.Draw(img)
    rng = random.Random(5)
    for _ in range(40):
        x, y = rng.randrange(W * 4), rng.randrange(H * 4)
        d.rectangle([x, y, x + 3, y + 3], fill=(255, 255, 255))
    ship(d, 300, 430, 4.5, "#FFFFFF", "#FFB23C")
    d.line([(390, 430), (720, 430)], fill=(255, 236, 80), width=8)
    for ax, ay, r in ((860, 420, 70), (1040, 650, 46), (760, 170, 38)):
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(140, 96, 70), outline=(90, 60, 44), width=6)
    font = ImageFont.truetype(FONTS + "consolab.ttf", 44)
    d.text((40, 44), "SCORE 001250", font=font, fill=(255, 255, 255), anchor="lm")
    d.text((W * 4 - 40, 44), "SHIPS 3", font=font, fill=(255, 214, 70), anchor="rm")
    return img


def glass(picture, size):
    """A screen's region: the raster in the middle of the tube's dark border."""
    w, h = size
    image = Image.new("RGB", (w, h), (14, 14, 16))
    rw, rh = round(w * 0.9), round(h * 0.86)
    image.paste(picture.resize((rw, rh), Image.LANCZOS), ((w - rw) // 2, (h - rh) // 2))
    return image


def disk_side(rect, label):
    """One side of the 3.5-inch disk, seen looking at it, its shutter's end at the top."""
    w, l = L.DISK["size"]
    blue = (40, 44, 52)
    reg = Region(rect, w, l, blue)
    reg.rect_(0.0, 0.0, w, l, shade(blue, 0.06), r=2.0)
    reg.rect_(26.0, 0.0, 64.0, 36.0, (200, 204, 210))               # the shutter
    reg.rect_(36.0, 6.0, 54.0, 26.0, (40, 38, 44), r=1.5)
    reg.rect_(37.5, 7.5, 52.5, 24.5, (92, 64, 44), r=1.0)
    if label:
        reg.rect_(8.0, 40.0, w - 8.0, l - 6.0, (244, 242, 234), r=1.2)
        art = space((640, 300)).convert("RGB")
        da = ImageDraw.Draw(art)
        ship(da, 200, 160, 3.0, "#FFFFFF", "#FFB23C")
        x0, y0, x1, y1 = reg.box(10.0, 42.0, w - 10.0, l - 22.0)
        reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
        reg.text("ODYSSEY", "ariblk.ttf", 8.0, w / 2, 50.0, (255, 214, 70))
        reg.text("Apple IIGS  ·  Disk 1", "arialbd.ttf", 3.8, w / 2, l - 13.0, (40, 40, 60))
    else:
        reg.circle(w / 2, l * 0.6, 12.0, (176, 180, 186))
        reg.circle(w / 2, l * 0.6, 3.0, (30, 30, 34))
    return reg


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (14, 14, 16))
    for name, picture in (("check", check()), ("boot", boot()), ("title", title()), ("game", game())):
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(glass(picture, (w, h)), (x, y))
    disk_side(L.MEDIA_REGIONS["disk_top"], True).paste(image)
    disk_side(L.MEDIA_REGIONS["disk_bottom"], False).paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", (14, 14, 16)), ("edge", (40, 44, 52))):
        x, y = L.MEDIA_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "apple2gs_media.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
