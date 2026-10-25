"""The Atari 7800 set's printing, for the console theme's Atari 7800 model (tools/console-models/atari7800.py).

Draws its atlas, its regions as atari7800_layout.py places them, each in millimetres as the model's planar UVs map it:
the console from above (the black strip with POWER, PAUSE, SELECT and RESET and the power light's window, the brushed
silver band with Atari's logo, ATARI and 7800 PROSYSTEM and the rainbow line crossing it, the vents' slots); the
joystick's top, drawn sideways, its front to the left (the silver plate with ATARI and the rainbow); the cartridge's
label (a made-up game, Odyssey, in the style of the 7800's labels); and the swatches small parts take their colour
from. Run it with the system Python (Pillow):

    python tools/console-models/atari7800_print.py <out folder>

It writes atari7800_print.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari7800_layout as L  # noqa: E402
from atari5200_print import fuji  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
SILVER = (204, 205, 208)
EMBOSS = (168, 169, 173)
STRIP = (14, 14, 16)
INK = (220, 220, 224)
LINE = [(240, 200, 60), (238, 130, 50), (222, 64, 60), (176, 60, 150), (86, 80, 190), (60, 130, 200), (70, 170, 110)]


def blend(stops, t):
    """A colour t (0 to 1) along a list of colour stops."""
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    k = min(int(t), len(stops) - 2)
    f = t - k
    return tuple(round(a + (b - a) * f) for a, b in zip(stops[k], stops[k + 1]))


def brushed(reg, x0, y0, x1, y1, base, lines=80):
    """A brushed-metal rectangle: fine lines along it."""
    reg.rect_(x0, y0, x1, y1, base)
    for k in range(lines):
        y = y0 + (y1 - y0) * (k + 0.5) / lines
        reg.line([(x0, y), (x1, y)], shade(base, 0.04 if k % 3 else -0.05), 0.2)


# ---- The console -----------------------------------------------------------------------------------------------------

def top():
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["top"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y
    (sy0, _), (sy1, _) = L.STRIP
    reg.rect_(*at(-w / 2, sy1), *at(w / 2, sy0), STRIP)
    reg.line([at(-w / 2, sy1), at(w / 2, sy1)], shade(CASE, 0.15), 0.4)
    kw, kh = L.KEYS["size"]
    ky = sy0 + L.KEYS["s"] * (sy1 - sy0) / L.STRIP_LENGTH
    for name in ("power", "pause", "select", "reset"):
        x = L.KEYS[name]
        reg.rect_(*at(x - kw / 2, ky + kh / 2), *at(x + kw / 2, ky - kh / 2), (24, 24, 27))
        reg.text(name.upper(), "arialbd.ttf", 2.8, *at(x, ky), INK)
    reg.circle(*at(L.LIGHT["x"], ky), L.LIGHT["r"] + 0.5, (4, 4, 5))
    reg.circle(*at(L.LIGHT["x"], ky), L.LIGHT["r"], (70, 16, 14))

    (by0, by1) = L.BAND["y"]
    (ax, ay), (bx, byy) = at(-w / 2, by1), at(w / 2, by0)
    brushed(reg, ax, ay, bx, byy, SILVER)
    lx, (ly0, ly1) = L.LOGO["x"], L.LOGO["y"]
    fuji(reg, *at(lx + 4.0, ly1), 8.0, EMBOSS)
    reg.text("ATARI", "arialbd.ttf", 9.0, *at(lx + 10.0, ly1), EMBOSS, anchor="lm")
    reg.text("7800 PROSYSTEM", "arial.ttf", 7.4, *at(lx, ly0), EMBOSS, anchor="lm")
    (ry0, ry1), rw = L.RAINBOW["y"], L.RAINBOW["width"]
    n = 120
    for k in range(n):                                        # the line, its colours running along it
        t0, t1 = k / n, (k + 1) / n
        x0, x1 = -w / 2 + w * t0, -w / 2 + w * t1
        y0, y1 = ry0 + (ry1 - ry0) * t0, ry0 + (ry1 - ry0) * t1
        reg.line([at(x0, y0), at(x1, y1)], blend(LINE, (t0 + t1) / 2), rw)

    v = L.VENTS
    x = v["x"][0] + v["pitch"] / 2
    while x < v["x"][1]:
        reg.rect_(*at(x - v["width"] / 2, v["y"][1]), *at(x + v["width"] / 2, v["y"][0]), (6, 6, 7), r=1.2)
        x += v["pitch"]
    return reg


# ---- The joystick, the label -----------------------------------------------------------------------------------------

def stick():
    """The joystick's top seen from above, drawn turned a quarter: along its length to the right (its front at the
    left), across it downwards (its left side at the top)."""
    pw, pl = L.PAD["size"]
    reg = Region(L.REGIONS["stick"], pl, pw, CASE)

    def at(x, y):
        return y + pl / 2, x + pw / 2

    def box(x0, y0, x1, y1):
        """A rectangle of the joystick's plan as the region's corners, top left first."""
        (a, b), (c, e) = at(x0, y0), at(x1, y1)
        return min(a, c), min(b, e), max(a, c), max(b, e)
    (py0, py1), i = L.PLATE["y"], L.PLATE["inset"]
    brushed(reg, *box(-pw / 2 + i, py0, pw / 2 - i, py1), SILVER, 60)
    mid = (py0 + py1) / 2
    for k in range(5):                                        # the rainbow, short bars along the plate
        reg.rect_(*box(-pw / 2 + i + 3.0 + 2.6 * k, mid - 28.0, -pw / 2 + i + 4.8 + 2.6 * k, mid - 10.0),
                  blend(LINE, k / 4))
    layer = reg.layer()                                       # ATARI, reading along the plate
    f = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(8.0 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(*at(2.0, mid + 4.0)), "ATARI", font=f, fill=EMBOSS + (255,), anchor="mm")
    reg.over(layer)
    return reg


def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (232, 232, 236))
    brushed(reg, 0.0, 0.0, lw, lh, (214, 215, 220), 30)
    reg.text("ODYSSEY", "arialbd.ttf", 6.0, lw / 2, 6.6, (200, 40, 50))
    reg.text("ATARI 7800  ProSystem", "arialbd.ttf", 3.2, lw / 2, 14.0, (40, 40, 48))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), stick(), label()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", (150, 20, 16)), ("red_lit", (255, 50, 40)), ("dark", STRIP), ("silver", SILVER),
                         ("orange", (232, 92, 30)), ("knob", (22, 22, 24))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "atari7800_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
