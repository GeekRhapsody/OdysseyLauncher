"""The Magnavox Odyssey²'s printing, for the console theme's Odyssey² model (tools/console-models/odyssey2.py).

Draws its atlas, its regions as odyssey2_layout.py places them, each in millimetres as the model's planar UVs map it:
the membrane keyboard's panel from above (its boxes and their names, NUMERIC, FUNCTION, INPUT, RESET and ALPHA, the
keys with their legends, the function keys ringed in red, RESET red, SPACE and its stripes); the slot's panel (its
stripes, MAGNAVOX, POWER); ODYSSEY² MICROPROCESSOR on the silver; the cartridge's label (a made-up game, Odyssey); a
joystick's plate (ACTION on its button); and the swatches small parts take their colour from. Run it with the system
Python (Pillow):

    python tools/console-models/odyssey2_print.py <out folder>

It writes odyssey2_print.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odyssey2_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

PANEL = (22, 22, 24)
KEY = (214, 216, 218)
LINE = (214, 214, 214)
RED = (214, 46, 44)
INK = (30, 30, 32)
SILVER = rgb(L.COLOURS["silver"])


def stripes(reg, x0, x1, y0, y1, denser_right=True, colour=(200, 200, 204)):
    """A run of vertical lines, closer together towards one end."""
    w = x1 - x0
    x, gap = 0.0, 2.2
    while x < w:
        t = x / w if denser_right else 1 - x / w
        reg.line([(x0 + x, y0), (x0 + x, y1)], colour, 0.35)
        x += gap * (1.0 - 0.75 * t) + 0.25
    return reg


def box_line(reg, x0, x1, y0, y1, gaps, colour):
    """A box's outline, its top line broken where gaps (x0, x1) let names through."""
    reg.rect_(x0, y0, x1, y1, None, r=2.0, outline=colour, width=0.45)
    for a, b in gaps:
        reg.rect_(a, y0 - 0.6, b, y0 + 0.6, PANEL)


# ---- The keyboard ------------------------------------------------------------------------------------------------------

def keyboard():
    (x0, x1), (s0, s1) = L.KEYBOARD["x"], L.KEYBOARD["s"]
    w, d = x1 - x0, s1 - s0
    reg = Region(L.REGIONS["keyboard"], w, d, PANEL)
    b = L.BOXES
    (bx0, bx1) = b["x"]
    box_line(reg, bx0, bx1, *b["numeric"], [(88.0, 120.0)], LINE)
    reg.text("NUMERIC", "arialbd.ttf", 2.6, 104.0, b["numeric"][0], LINE)
    box_line(reg, bx0, bx1, *b["function"], [(48.0, 78.0), (138.0, 158.0), (172.0, 194.0)], LINE)
    for name, x in (("FUNCTION", 63.0), ("INPUT", 148.0), ("RESET", 183.0)):
        reg.text(name, "arialbd.ttf", 2.6, x, b["function"][0], RED)
    box_line(reg, bx0, bx1, *b["alpha"], [(92.0, 116.0)], LINE)
    reg.text("ALPHA", "arialbd.ttf", 2.6, 104.0, b["alpha"][0], LINE)
    kw, kd = L.KEY
    for k, row in enumerate(L.ROWS):
        for j, legend in enumerate(row["keys"]):
            cx, cy = row["x"] + j * L.U, row["s"]
            reset = legend == "△"
            ring = RED if k == 1 else (120, 120, 124)
            reg.rect_(cx - kw / 2, cy - kd / 2, cx + kw / 2, cy + kd / 2, RED if reset else KEY, r=1.6,
                      outline=ring, width=0.45)
            if reset:
                reg.text(legend, "seguisym.ttf", 4.0, cx, cy, (255, 255, 255))
            else:
                size = 2.5 if len(legend) > 1 else 5.0
                reg.text(legend, "seguisym.ttf" if not legend.isascii() else "arial.ttf", size, cx, cy + 0.2, INK)
    (sx0, sx1), (ss0, ss1) = L.SPACE["x"], L.SPACE["s"]
    reg.rect_(sx0, ss0, sx1, ss1, KEY, r=1.6, outline=RED, width=0.45)
    reg.text("SPACE", "arial.ttf", 2.4, (sx0 + sx1) / 2, (ss0 + ss1) / 2, INK)
    (a, c), (e, g) = L.SPACE["stripes"]
    stripes(reg, a, c, ss0, ss1, True)
    stripes(reg, e, g, ss0, ss1, False)
    return reg


# ---- The slot's panel, the logo --------------------------------------------------------------------------------------

def back():
    (x0, x1), (y0, y1) = L.BACK["x"], L.BACK["y"]
    w, d = x1 - x0, y1 - y0
    reg = Region(L.REGIONS["back"], w, d, PANEL)

    def at(x, y):
        return x - x0, y1 - y

    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    (a, top), (c, bottom) = at(sx0, sy1), at(sx1, sy0)
    stripes(reg, 4.0, a - 3.0, top - 6.0, bottom + 6.0, True)
    stripes(reg, c + 3.0, c + 24.0, top - 6.0, bottom + 6.0, False)
    (px0, px1), (py0, py1) = L.POWER["x"], L.POWER["y"]
    (pa, pt), (pc, pb) = at(px0, py1), at(px1, py0)
    stripes(reg, pa - 26.0, pa - 3.0, pt - 3.0, pb + 3.0, True)
    stripes(reg, pc + 3.0, w - 4.0, pt - 3.0, pb + 3.0, False)
    reg.text("MAGNAVOX", "arialbd.ttf", 6.2, (pa + pc) / 2 - 6.0, pt - 7.0, (236, 236, 236))
    reg.text("POWER", "arial.ttf", 2.6, (pa + pc) / 2, pb + 4.0, RED)
    return reg


def logo():
    (x0, x1), (y0, y1) = L.LOGO["x"], L.LOGO["y"]
    w, d = x1 - x0, y1 - y0
    reg = Region(L.REGIONS["logo"], w, d, SILVER)
    font = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(8.4 * reg.sx)))
    reg.draw.text(reg.p(2.0, 13.0), "ODYSSEY", font=font, fill=SILVER, anchor="lm",      # in outline, as on the case
                  stroke_width=max(1, round(0.45 * reg.sx)), stroke_fill=(56, 56, 60))
    reg.text("2", "arialbd.ttf", 11.0, 47.5, 10.5, RED)
    reg.text("MICROPROCESSOR", "arial.ttf", 3.3, 2.4, 21.0, INK, anchor="lm")
    return reg


# ---- The cartridge's label, the joystick's plate ---------------------------------------------------------------------

def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (20, 20, 22))
    art = space((660, 440)).convert("RGB")
    ship(ImageDraw.Draw(art), 220, 250, 3.2, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(2.0, 12.0, lw - 2.0, lh - 2.0)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 11.0, RED)
    reg.text("ODYSSEY", "arialbi.ttf", 7.6, lw / 2, 5.8, (255, 250, 236))
    reg.text("#1", "arialbd.ttf", 4.0, lw - 6.0, lh - 6.0, (255, 214, 70))
    return reg


def stick():
    pw, pd, _ = L.STICK["plate"]
    reg = Region(L.REGIONS["stick"], pw, pd, (24, 24, 26))
    ax, ay, aw, ad, _ = L.STICK["action"]
    cx, cy = pw / 2 + ax, pd / 2 - ay
    reg.rect_(cx - aw / 2, cy - ad / 2, cx + aw / 2, cy + ad / 2, (226, 50, 46), r=0.8)
    reg.text("ACTION", "arialbd.ttf", 2.2, cx, cy, (40, 10, 10))
    for k in range(6):                                      # the plate's ridges along its foot
        y = pd - 4.0 - 1.6 * k
        reg.line([(6.0, y), (pw - 6.0, y)], (44, 44, 48), 0.5)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), SILVER)
    for reg in (keyboard(), back(), logo(), label(), stick()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", rgb(L.COLOURS["red"])), ("red_lit", (255, 90, 80)), ("black", rgb(L.COLOURS["black"])),
                         ("silver", SILVER), ("body", rgb(L.COLOURS["body"]))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "odyssey2_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
