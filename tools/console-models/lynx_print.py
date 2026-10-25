"""The Atari Lynx II's printing and screens, for the console theme's Lynx model (tools/console-models/lynx.py).

Draws its atlas, its regions as lynx_layout.py places them, each in millimetres as the model's planar UVs map it (the
screens in their pixels): the front from in front (the grips' grey and the glossy black middle, the window's surround
and the switched-off screen, LYNX in orange over it and ATARI under it, the power light, the buttons' names and their
brackets, the D-pad's well and the grooves beside it, the wells of A and B, the speaker's slots); the screens (the
title of a made-up game, Odyssey; a moment of its play; the same turned over, as FLIP shows it); the game card's label;
and the swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/lynx_print.py <out folder>

It writes lynx_print.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lynx_layout as L  # noqa: E402
from atari5200_print import fuji  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

GRIP = (40, 40, 43)
MIDDLE = (12, 12, 13)
ORANGE = (236, 128, 34)
LCD_OFF = (44, 46, 44)


def outline():
    right = L.RIGHT_HALF
    return right + [(-x, z) for x, z in reversed(right[1:-1])]


# ---- The front ---------------------------------------------------------------------------------------------------------

def front():
    w, h = L.WIDTH, L.HEIGHT
    reg = Region(L.REGIONS["front"], w, h, rgb(L.COLOURS["case"]))

    def at(x, z):
        return x + w / 2, h / 2 - z
    reg.poly([at(x, z) for x, z in outline()], GRIP)
    rng = random.Random(3)                                     # the grips' fine texture
    for _ in range(9000):
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-h / 2, h / 2)
        reg.circle(*at(x, z), 0.12, shade(GRIP, rng.uniform(-0.12, 0.1)))
    g = L.GRIP_X
    reg.poly([at(-g, 55.0), at(g, 55.0), at(g + 1.0, 0.0), at(g, -55.0), at(-g, -55.0), at(-g - 1.0, 0.0)], MIDDLE)
    for side in (-1, 1):                                       # the grips' edges along the middle
        reg.line([at(side * g, 54.0), at(side * (g + 1.0), 0.0), at(side * g, -54.0)], (10, 10, 11), 0.5)

    (wx, wz), (ww, wh) = L.WINDOW["at"], L.WINDOW["size"]
    reg.rect_(*at(wx - ww / 2, wz + wh / 2), *at(wx + ww / 2, wz - wh / 2), (8, 8, 9), r=L.WINDOW["corner"])
    (sx, sz), (sw, sh) = L.SCREEN["at"], L.SCREEN["size"]
    reg.rect_(*at(sx - sw / 2, sz + sh / 2), *at(sx + sw / 2, sz - sh / 2), LCD_OFF)

    lx, lz = L.LYNX["at"]                                     # LYNX: heavy letters stretched wide, as its logo
    mask = Image.new("L", (900, 200), 0)
    ImageDraw.Draw(mask).text((10, 100), "LYNX", font=ImageFont.truetype(FONTS + "ariblk.ttf", 150), fill=255,
                              anchor="lm")
    mask = mask.crop(mask.getbbox())
    x0, y0, x1, y1 = reg.box(*at(lx - L.LYNX["width"] / 2, lz + L.LYNX["height"] / 2),
                             *at(lx + L.LYNX["width"] / 2, lz - L.LYNX["height"] / 2))
    mask = mask.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS)
    reg.img.paste(Image.new("RGBA", mask.size, ORANGE + (255,)), (round(x0), round(y0)), mask)
    reg.circle(*at(*L.LIGHT["at"]), L.LIGHT["r"], (70, 30, 24))
    reg.text("POWER", "arial.ttf", 2.0, *at(L.LIGHT["at"][0], L.LIGHT["at"][1] - 3.2), ORANGE)
    ax, az = L.ATARI["at"]
    fuji(reg, *at(ax - 8.0, az), L.ATARI["height"], (190, 190, 194))
    reg.text("ATARI", "arial.ttf", 3.8, *at(ax - 4.6, az), (190, 190, 194), anchor="lm")

    def bracket(x, z0, z1, side, label_z=None):
        """A bracket from z0 to z1 beside the buttons at x (side 1: to their right)."""
        bx = x + side * 5.2
        reg.line([at(x + side * 3.6, z0), at(bx, z0), at(bx, z1), at(x + side * 3.6, z1)], ORANGE, 0.3)
    b = L.LEFT_BUTTONS
    bw, bh = b["size"]
    for z in b["z"]:
        reg.rect_(*at(b["x"] - bw / 2 - 0.6, z + bh / 2 + 0.6), *at(b["x"] + bw / 2 + 0.6, z - bh / 2 - 0.6), (4, 4, 5),
                  r=1.4)
    z_on, z_off, z_back = b["z"]
    bracket(b["x"], z_on + 3.0, z_off - 3.0, 1)
    reg.text("ON", "arial.ttf", 2.2, *at(b["x"] + 2.0, z_on + bh / 2 + 2.0), ORANGE)
    reg.text("POWER", "arial.ttf", 2.0, *at(b["x"], z_on - bh / 2 - 1.8), ORANGE)
    reg.text("OFF", "arial.ttf", 2.2, *at(b["x"] + 2.0, z_off - bh / 2 - 2.0), ORANGE)
    reg.text("BACKLIGHT", "arial.ttf", 2.2, *at(b["x"] + 4.0, z_back - bh / 2 - 2.2), ORANGE)
    bracket(b["x"], z_back + 3.0, z_back - bh / 2 - 1.0, -1)
    r = L.RIGHT_BUTTONS
    for z in r["z"]:
        reg.rect_(*at(r["x"] - bw / 2 - 0.6, z + bh / 2 + 0.6), *at(r["x"] + bw / 2 + 0.6, z - bh / 2 - 0.6), (4, 4, 5),
                  r=1.4)
    z1, z2, z3 = r["z"]
    reg.text("OPTION 1", "arial.ttf", 2.2, *at(r["x"] - 1.5, z1 + bh / 2 + 2.0), ORANGE)
    reg.text("RESTART", "arial.ttf", 2.2, *at(r["x"] - 1.0, (z1 + z2) / 2), ORANGE)
    reg.text("FLIP", "arial.ttf", 2.2, *at(r["x"] - 1.0, (z2 + z3) / 2), ORANGE)
    reg.text("OPTION 2", "arial.ttf", 2.2, *at(r["x"] - 1.5, z3 - bh / 2 - 2.0), ORANGE)
    bracket(r["x"], z1 + 2.0, z2 + 1.0, 1)
    bracket(r["x"], z2 - 1.0, z3 - 2.0, -1)
    reg.text("II", "arialbd.ttf", 1.8, *at(r["x"] + 6.4, z2), (150, 150, 154))

    (dx, dz), size, arm = L.DPAD["at"], L.DPAD["size"], L.DPAD["arm"] + 2.0
    for a, b_ in (((size + 2.0) / 2, arm / 2), (arm / 2, (size + 2.0) / 2)):
        reg.rect_(*at(dx - a, dz + b_), *at(dx + a, dz - b_), (14, 14, 15), r=2.0)
    (gx0, gx1), (gz0, gz1) = L.GROOVES["x"], L.GROOVES["z"]
    for gx in (gx0, gx1):
        reg.line([at(gx + 1.2 * (1 - (z / gz1) ** 2), z) for z in [gz0 + (gz1 - gz0) * k / 12 for k in range(13)]],
                 (30, 30, 32), 0.45)
    for pair, turn in ((L.AB["top"], L.AB["turn"][0]), (L.AB["bottom"], L.AB["turn"][1])):
        for (x, z) in pair:
            c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
            half = L.AB["well"] / 2
            corners = [(x + c * u - s * v, z + s * u + c * v) for u, v in ((-half, -half), (half, -half), (half, half),
                                                                            (-half, half))]
            reg.poly([at(px, pz) for px, pz in corners], (14, 14, 15))
    (sx0, sx1), (sz0, sz1), n = L.SPEAKER["x"], L.SPEAKER["z"], L.SPEAKER["count"]
    for k in range(n):
        x = sx0 + (sx1 - sx0) * k / (n - 1)
        span = (sz1 - sz0) * (0.62 + 0.38 * math.sin(math.pi * (k + 0.5) / n))
        for j in range(9):
            z0 = -span / 2 + span * j / 9
            z1_ = z0 + span / 9 * 0.62
            bow = 1.6 * (1 - ((z0 + z1_) / span) ** 2)
            reg.line([at(x - bow, z0), at(x - bow, z1_)], (14, 14, 15), 0.7)
    return reg


# ---- The screens -------------------------------------------------------------------------------------------------------

W, H = 320, 200                                      # the Lynx's 160 x 102, doubled


def title():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 22), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 40), fill=(255, 214, 70), anchor="mt",
           stroke_width=2, stroke_fill=(120, 30, 10))
    ship(d, 90, 120, 2.0, "#FFFFFF", "#FFB23C")
    d.text((W / 2, 182), "PRESS A", font=ImageFont.truetype(FONTS + "arialbd.ttf", 16), fill=(255, 255, 255),
           anchor="mm")
    return img


def game():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    rng = random.Random(11)
    for _ in range(30):
        x, y = rng.randrange(W), rng.randrange(H)
        d.rectangle([x, y, x + 1, y + 1], fill=(255, 255, 255))
    ship(d, 70, 110, 1.6, "#FFFFFF", "#FFB23C")
    d.line([(104, 110), (200, 110)], fill=(255, 236, 80), width=3)
    for ax, ay, r in ((236, 104, 24), (280, 160, 14), (210, 40, 11)):
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(140, 96, 70), outline=(90, 60, 44), width=2)
    font = ImageFont.truetype(FONTS + "arialbd.ttf", 14)
    d.text((8, 12), "SCORE 001250", font=font, fill=(255, 255, 255), anchor="lm")
    d.text((W - 8, 12), "x3", font=font, fill=(255, 214, 70), anchor="rm")
    return img


# ---- The card's label --------------------------------------------------------------------------------------------------

def card():
    cw, ch, _ = L.CARD["size"]
    reg = Region(L.REGIONS["card"], cw, ch, rgb("#2A2A2D"))
    reg.rect_(3.0, 9.0, cw - 3.0, ch - 3.0, (240, 238, 232), r=1.0)
    art = space((420, 460)).convert("RGB")
    ship(ImageDraw.Draw(art), 140, 260, 3.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(4.0, 18.0, cw - 4.0, ch - 4.0)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(4.0, 10.0, cw - 4.0, 18.0, ORANGE)
    reg.text("ODYSSEY", "ariblk.ttf", 5.6, cw / 2, 14.2, (30, 20, 10))
    for k in range(5):                                        # the grip's ribs along the top edge
        reg.rect_(cw / 2 - 12.0 + 6.0 * k, 2.0, cw / 2 - 10.0 + 6.0 * k, 7.0, (20, 20, 22))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["case"]))
    for reg in (front(), card()):
        reg.paste(image)
    flipped = game().rotate(180)
    for name, picture in (("title", title()), ("game", game()), ("game_flipped", flipped)):
        x, y, w, h = L.REGIONS[name]
        image.paste(picture.resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(image)
    for name, colour in (("case", rgb(L.COLOURS["case"])), ("key", rgb(L.COLOURS["key"])), ("red", (255, 60, 40)),
                         ("lcd", LCD_OFF), ("card", rgb("#2A2A2D"))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "lynx_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
