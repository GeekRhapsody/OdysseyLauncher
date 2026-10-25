"""The Virtual Boy's printing and screens (virtualboy_print.png), for the console theme's model (virtualboy.py).

One image, laid out as virtualboy_layout.REGIONS says: VIRTUAL BOY on the unit's red front, the controller's battery
pack (VIRTUAL BOY, the Nintendo oval), the stand's Nintendo plate, the controller's face (its lobes, SELECT, START, B,
A, the power switch), the screens three ways in the Virtual Boy's red on black (a made-up game, Odyssey: its title,
then the ship over a grid running into the distance, a shot), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/virtualboy_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import virtualboy_layout as L  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

RED = rgb(L.COLOURS["red"])
BLACK = rgb(L.COLOURS["black"])
GREY = (150, 152, 158)
LIGHT = (205, 207, 212)
# The screens' four shades of red.
SHADES = [(0, 0, 0), (96, 6, 4), (176, 14, 8), (255, 34, 20)]


def condensed(reg, text, font, x0, y0, x1, y1, fill):
    """text stretched to the box (x0, y0)-(x1, y1), as the Virtual Boy's tall, narrow logo is."""
    f = ImageFont.truetype(FONTS + font, 200)
    mask = Image.new("L", (round(f.getlength(text)) + 40, 280), 0)
    ImageDraw.Draw(mask).text((20, 140), text, font=f, fill=255, anchor="lm")
    mask = mask.crop(mask.getbbox())
    a, b, c, d = reg.box(x0, y0, x1, y1)
    mask = mask.resize((max(1, round(c - a)), max(1, round(d - b))), Image.LANCZOS)
    reg.img.paste(Image.new("RGBA", mask.size, fill + (255,)), (round(a), round(b)), mask)


def nintendo(reg, cx, cy, w, h, colour):
    """Nintendo in its oval."""
    reg.rect_(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, None, r=h / 2, outline=colour, width=h * 0.08)
    reg.text("Nintendo", "arialbd.ttf", h * 0.62, cx, cy, colour)


# ---- The unit, the pack, the plate, the controller's face ------------------------------------------------------------

def front():
    """The unit's front round the logo, seen from in front: x from LOGO's area's left, z down from its top."""
    x0, x1, z0, z1 = L.LOGO["area"]
    reg = Region(L.REGIONS["front"], x1 - x0, z1 - z0, RED)
    (lx0, lx1), (lz0, lz1) = L.LOGO["x"], L.LOGO["z"]
    condensed(reg, "VIRTUAL BOY", "bahnschrift.ttf", lx0 - x0, z1 - lz1 + 6.0, lx1 - x0, z1 - lz0 - 6.0, (62, 60, 64))
    reg.text("TM", "arial.ttf", 1.8, lx1 - x0 + 1.4, z1 - lz0 - 7.0, (62, 60, 64), anchor="lm")
    return reg


def pack():
    """The battery pack's front: x across its width, z down from its top."""
    (x0, x1), (z0, z1) = L.PACK["x"], L.PACK["z"]
    w, h = x1 - x0, z1 - z0
    reg = Region(L.REGIONS["pack"], w, h, (46, 46, 50))
    condensed(reg, "VIRTUAL BOY", "bahnschrift.ttf", 6.0, 8.0, w - 6.0, 22.0, GREY)
    nintendo(reg, w / 2, 31.0, 26.0, 7.0, (28, 28, 30))
    return reg


def plate():
    w, h = L.JOINT["size"][0], L.JOINT["size"][2] - 4.0
    reg = Region(L.REGIONS["plate"], w, h, (22, 22, 24))
    nintendo(reg, w / 2, h * 0.38, 26.0, 7.0, (60, 60, 64))
    reg.text("MADE IN JAPAN", "arial.ttf", 2.2, w / 2, h * 0.68, (60, 60, 64))
    reg.text("PAT. PEND.", "arial.ttf", 2.2, w / 2, h * 0.8, (60, 60, 64))
    return reg


def face():
    """The controller's face from in front: x from 80 left of its middle, z down from 32 above it."""
    reg = Region(L.REGIONS["face"], 160.0, 64.0, BLACK)

    def at(x, z):
        return x + 80.0, 32.0 - z

    lx, lr = L.LOBES["x"], L.LOBES["r"]
    for side in (-1, 1):
        reg.circle(*at(side * lx, 0.0), lr - 3.0, (34, 34, 38))
    (sx, sz), (tx, tz) = L.SELECT_START["at"]
    reg.text("SELECT", "arialbd.ttf", 2.4, *at(sx - 2.0, sz + 8.0), LIGHT)
    reg.text("START", "arialbd.ttf", 2.4, *at(tx + 4.0, tz + 8.0), LIGHT)
    (bx, bz), (ax, az) = L.B_A["at"]
    reg.text("B", "arialbd.ttf", 3.0, *at(bx, bz + 9.0), LIGHT)
    reg.text("A", "arialbd.ttf", 3.0, *at(ax, az + 9.0), LIGHT)
    reg.rect_(*at(-10.0, 20.0), *at(10.0, 15.0), (110, 112, 118), r=1.0)          # the power switch
    reg.rect_(*at(-10.0, 20.0), *at(-6.0, 15.0), (200, 30, 26))
    reg.text("OFF", "arial.ttf", 1.8, *at(-6.0, 23.0), GREY)
    reg.text("ON", "arial.ttf", 1.8, *at(6.0, 23.0), GREY)
    return reg


# ---- The screens -----------------------------------------------------------------------------------------------------

def screen(draw_fn):
    """One eye's screen, red on black at twice its size, then softened as the LEDs' lines are."""
    w, h = L.SCREEN_PX
    img = Image.new("RGB", (w * 2, h * 2), SHADES[0])
    d = ImageDraw.Draw(img)
    draw_fn(d, w * 2, h * 2)
    img = img.resize((w, h), Image.LANCZOS)
    glow = img.filter(ImageFilter.GaussianBlur(1.6))
    return Image.blend(img, glow, 0.35)


def ship(d, cx, cy, s, colour):
    """The ship from behind: its wings and fin as lines."""
    pts = [(cx - 14 * s, cy + 4 * s), (cx, cy - 6 * s), (cx + 14 * s, cy + 4 * s), (cx + 5 * s, cy + 2 * s),
           (cx, cy + 6 * s), (cx - 5 * s, cy + 2 * s)]
    d.line(pts + pts[:1], fill=colour, width=max(2, round(1.4 * s)))
    d.line([(cx, cy - 6 * s), (cx, cy - 13 * s), (cx + 3 * s, cy - 6 * s)], fill=colour, width=max(2, round(1.2 * s)))


def grid(d, w, h, horizon, scroll):
    """A floor of red lines running into the distance from the horizon."""
    for k in range(-9, 10):
        d.line([(w / 2 + k * w * 0.12, h), (w / 2 + k * w * 0.012, horizon)], fill=SHADES[1], width=2)
    for k in range(9):
        t = ((k + scroll) % 9) / 9.0
        y = horizon + (h - horizon) * t ** 2.2
        d.line([(0, y), (w, y)], fill=SHADES[2] if t > 0.4 else SHADES[1], width=2)


def planet(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SHADES[1], outline=SHADES[2], width=3)
    d.arc([cx - r * 1.8, cy - r * 0.38, cx + r * 1.8, cy + r * 0.38], 160, 380, fill=SHADES[3], width=3)


def stars(d, w, h, seed):
    rng = random.Random(seed)
    for _ in range(26):
        x, y = rng.uniform(0, w), rng.uniform(0, h * 0.45)
        r = rng.choice((1.5, 2.0, 3.0))
        d.ellipse([x - r, y - r, x + r, y + r], fill=SHADES[rng.choice((2, 3))])


def title(d, w, h):
    stars(d, w, h, 3)
    planet(d, w * 0.78, h * 0.3, h * 0.12)
    f = ImageFont.truetype(FONTS + "ariblk.ttf", round(h * 0.2))
    d.text((w / 2, h * 0.52), "ODYSSEY", font=f, fill=SHADES[3], anchor="mm", stroke_width=4, stroke_fill=SHADES[1])
    ship(d, w * 0.5, h * 0.8, 3.4, SHADES[3])


def game(frame):
    def draw(d, w, h):
        horizon = h * 0.42
        stars(d, w, horizon / 0.45, 5)
        planet(d, w * 0.25, horizon - h * 0.08, h * 0.08)
        grid(d, w, h, horizon, frame * 0.5)
        for k, (x, y, s) in enumerate(((0.7, 0.55, 1.0), (0.32, 0.62, 1.4), (0.62, 0.75, 2.0))):
            r = 9 * s + frame * 3 * s
            cx, cy = w * x - frame * 10 * (k - 1), h * y + frame * 6 * s
            d.polygon([(cx + r * math.cos(a), cy + r * 0.8 * math.sin(a)) for a in
                       [2 * math.pi * j / 7 + k for j in range(7)]], outline=SHADES[3], fill=SHADES[1])
        ship(d, w * (0.5 + 0.05 * frame), h * 0.84, 3.0, SHADES[3])
        if frame:
            for j in range(4):
                y = h * 0.7 - j * h * 0.07
                d.line([(w * 0.55, y), (w * 0.55, y - h * 0.035)], fill=SHADES[3], width=3)
        f = ImageFont.truetype(FONTS + "arialbd.ttf", round(h * 0.07))
        d.text((w * 0.04, h * 0.05), "SCORE 0" + ("120" if frame == 0 else "250"), font=f, fill=SHADES[3])
    return draw


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BLACK)
    for reg in (front(), pack(), plate(), face()):
        reg.paste(image)
    for name, draw_fn in (("title", title), ("game_1", game(0)), ("game_2", game(1))):
        x, y, w, h = L.REGIONS[name]
        image.paste(screen(draw_fn), (x, y))
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        colour = (6, 2, 2) if name == "dark" else rgb(L.COLOURS[name])
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "virtualboy_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
