"""The Atari 2600's printing, for the console theme's Atari 2600 model (tools/console-models/atari_2600.py).

Draws its atlas, its regions as atari_2600_layout.py places them, each in millimetres as the model's planar UVs map it:
the control panel's face seen square on (the orange outline, POWER, TV TYPE, VIDEO COMPUTER SYSTEM, GAME SELECT and
GAME RESET, the switches' slots); the wood-grain strip across the front with ATARI and its mark; the cartridge's label (a
made-up game, Odyssey); the joystick's top (the orange ring and TOP); and the swatches small parts take their colour
from. Run it with the system Python (Pillow):

    python tools/console-models/atari_2600_print.py <out folder>

It writes atari_2600_print.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari_2600_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
ORANGE = rgb(L.COLOURS["orange"])
RED_LEGEND = (214, 74, 62)


def fuji(reg, x, y, size, colour):
    """Atari's mark, size tall, its middle at (x, y): three columns, the outer two flaring out at their feet."""
    s = size
    reg.rect_(x - 0.08 * s, y - 0.5 * s, x + 0.08 * s, y + 0.5 * s, colour)
    for side in (-1, 1):
        pts = [(x + side * 0.16 * s, y - 0.5 * s), (x + side * 0.3 * s, y - 0.5 * s), (x + side * 0.3 * s, y - 0.05 * s),
               (x + side * 0.58 * s, y + 0.5 * s), (x + side * 0.4 * s, y + 0.5 * s), (x + side * 0.16 * s, y + 0.05 * s)]
        reg.poly(pts, colour)


def panel():
    _, _, length = L.frame(*L.PANEL)
    reg = Region(L.REGIONS["panel"], L.WIDTH, length, CASE)

    def at(x, s):
        return x + L.WIDTH / 2, length - s
    hw = L.PANEL_W / 2
    a, b = at(-hw, length - 5.0)
    c, e = at(hw, 4.0)
    reg.rect_(a, b, c, e, ORANGE, r=1.5)
    reg.rect_(a + 0.8, b + 0.8, c - 0.8, e - 0.8, shade(CASE, -0.15), r=1.0)
    sw = L.SWITCH
    for name, x in L.SWITCHES:
        sx, sy = at(x, sw["s"])
        reg.rect_(sx - sw["slot"][0] / 2, sy - sw["slot"][1] / 2, sx + sw["slot"][0] / 2, sy + sw["slot"][1] / 2,
                  (6, 6, 8), r=sw["slot"][0] / 2)
    def legend(text, x, s, size=3.4, colour=RED_LEGEND, font="arialbd.ttf"):
        reg.text(text, font, size, *at(x, s), colour)
    legend("POWER", -122.0, 60.0)
    legend("ON", -140.0, 51.0, 3.0)
    legend("OFF", -140.0, 27.0, 3.0)
    legend("TV TYPE", -88.0, 56.0, 3.4, ORANGE)
    legend("COLOR", -110.0, 46.0, 3.0, ORANGE)
    legend("B•W", -110.0, 24.0, 3.0, ORANGE)
    legend("VIDEO COMPUTER SYSTEM™", 0.0, 52.0, 4.4, (236, 236, 236))
    for name, x in L.SWITCHES[2:]:
        lines = name.upper().split("_")
        legend(lines[0], x, 64.0, 3.0, ORANGE)
        legend(lines[1], x, 60.0, 3.0, ORANGE)
        for k in range(4):                                     # the arrow's dashes, pointing down
            reg.rect_(*at(x + 9.0, 46.0 - k * 4.0), *at(x + 9.0 + 3.0 - k * 0.6, 45.0 - k * 4.0), ORANGE)
        reg.poly([at(x + 8.0, 28.0), at(x + 12.0, 28.0), at(x + 10.0, 24.0)], ORANGE)
    (x0, x1), (s0, s1) = L.CART_SLOT["x"], L.CART_SLOT["s"]
    reg.rect_(*at(x0 - 2.0, s1 + 2.0), *at(x1 + 2.0, s0 - 2.0), shade(CASE, 0.15), r=2.0)
    reg.rect_(*at(x0, s1), *at(x1, s0), (8, 8, 10), r=1.0)
    return reg


def wood():
    (y0, z0), (y1, z1) = L.WOOD["bottom"], L.WOOD["top"]
    length = math.hypot(y1 - y0, z1 - z0)
    reg = Region(L.REGIONS["wood"], L.WIDTH, length, (118, 74, 36))
    rng = random.Random(2600)
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    for k in range(70):                                         # the grain: long wavering streaks
        y = rng.uniform(0, length)
        colour = rng.choice([(92, 54, 24), (140, 92, 48), (104, 62, 30), (156, 104, 56)])
        pts = [(x, y + 0.6 * math.sin(x / rng.uniform(12, 30) + k)) for x in range(0, int(L.WIDTH) + 10, 6)]
        d.line([reg.p(px, py) for px, py in pts], fill=colour + (160,), width=max(1, round(rng.uniform(0.2, 0.8) * reg.sx)))
    reg.over(layer)
    fuji(reg, L.WIDTH - 22.0, length / 2 - 4.0, 12.0, (240, 238, 232))
    reg.text("ATARI®", "arial.ttf", 4.4, L.WIDTH - 22.0, length / 2 + 7.5, (240, 238, 232))
    return reg


def label():
    lw, lh, _ = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (230, 226, 216))
    art = space((660, 540))
    d = ImageDraw.Draw(art)
    ship(d, 220, 330, 3.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(2.0, 15.0, lw - 2.0, lh - 9.0)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 13.0, (196, 46, 40))
    reg.text("ODYSSEY", "arialbi.ttf", 9.0, lw / 2, 6.8, (255, 248, 230))
    fuji(reg, 7.0, lh - 4.4, 5.0, (40, 40, 44))
    reg.text("ATARI", "arialbd.ttf", 3.6, 18.0, lh - 4.4, (40, 40, 44), anchor="lm")
    reg.text("GAME PROGRAM™", "arial.ttf", 2.6, lw - 3.0, lh - 4.4, (40, 40, 44), anchor="rm")
    return reg


def stick_top():
    w, d, _ = L.STICK["base"]
    reg = Region(L.REGIONS["stick"], w, d, CASE)
    reg.rect_(1.0, 1.0, w - 1.0, d - 1.0, shade(CASE, 0.08), r=10.0)
    cx, cy = w / 2 + 6.0, d / 2 + 3.0
    for k in range(40):                                         # the ring's dashes
        a = 2 * math.pi * k / 40
        if k % 10 in (0, 5):
            continue
        reg.line([(cx + 25 * math.cos(a), cy + 25 * math.sin(a)), (cx + 29 * math.cos(a), cy + 29 * math.sin(a))],
                 ORANGE, 1.4)
    reg.circle(cx, cy, 20.0, shade(CASE, -0.2))
    reg.circle(cx, cy, 15.0, shade(CASE, 0.05))
    reg.text("TOP", "arialbd.ttf", 4.0, cx - 21.0, cy - 21.0, ORANGE)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (panel(), wood(), label(), stick_top()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", (228, 58, 40)), ("dark", rgb(L.COLOURS["dark"])), ("wood", (118, 74, 36))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "atari_2600_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
