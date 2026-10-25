"""The PlayStation's printing, for the console theme's PlayStation model (tools/console-models/psx.py).

Draws its atlas, its regions as psx_layout.py places them, each in millimetres as the model's planar UVs map it: the top
seen from above (the lid's SONY and PlayStation logos, the seams round the lid's area, the buttons' wells and their
POWER, RESET and OPEN, the compact disc mark); the recess's back wall seen from in front (the two controller ports, the
memory card slots, their numbers); the disc's label side (a made-up game, Odyssey) and its black data side; and the
swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/psx_print.py <out folder>

It writes psx_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psx_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
INK = (58, 60, 68)


def top_point(x, y):
    """A point of the top (x from the middle, y back from the front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


def ps_logo(reg, x, y, s):
    """The PlayStation mark, s high, its foot's middle at (x, y): the red P standing on the S, which lies flat in
    yellow, green and blue."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    # The S: three bands lying back in perspective, from front to back blue, green, yellow.
    for k, colour in enumerate(((0, 114, 188), (0, 166, 81), (247, 199, 0))):
        y0 = y - 0.06 * s - k * 0.11 * s
        pts = [(x - 0.55 * s + 0.12 * k * s, y0), (x + 0.35 * s, y0), (x + 0.5 * s, y0 - 0.11 * s),
               (x - 0.4 * s + 0.12 * k * s, y0 - 0.11 * s)]
        d.polygon([reg.p(px, py) for px, py in pts], fill=colour + (255,))
    # The P: its stem, and its bowl.
    d.polygon([reg.p(px, py) for px, py in ((x - 0.18 * s, y), (x - 0.02 * s, y - 0.06 * s), (x - 0.02 * s, y - s),
                                            (x - 0.18 * s, y - 0.94 * s))], fill=(226, 35, 26, 255))
    d.ellipse(reg.box(x - 0.1 * s, y - s, x + 0.36 * s, y - 0.52 * s), fill=(226, 35, 26, 255))
    d.ellipse(reg.box(x + 0.0 * s, y - 0.9 * s, x + 0.2 * s, y - 0.64 * s), fill=CASE + (255,))
    reg.over(layer)


def well(reg, x, y, r, label, colour, size):
    cx, cy = top_point(x, y)
    reg.circle(cx, cy, r + L.BUTTON["well"], shade(CASE, -0.45))
    reg.circle(cx, cy, r, shade(CASE, 0.04))
    reg.circle(cx, cy, r - 0.8, CASE)
    reg.text(label, "arial.ttf", size, cx, cy, colour)


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)
    # The seams round the lid's area, and its slightly paler panel.
    (x0, _), (x1, _) = top_point(L.SEAMS[0], 0), top_point(L.SEAMS[1], 0)
    _, back = top_point(0, L.BACK["y"])
    reg.rect_(x0, back, x1, L.DEPTH, shade(CASE, 0.03))
    for x in (x0, x1):
        reg.rect_(x - 0.35, back, x + 0.35, L.DEPTH, shade(CASE, -0.35))
    # The lid: the paler disc, SONY at its back, the mark and PlayStation at its front.
    lx, ly = top_point(L.LID["x"], L.LID["y"])
    r = L.LID["r"]
    reg.circle(lx, ly, r + 0.5, shade(CASE, -0.25))
    reg.circle(lx, ly, r, shade(CASE, 0.06))
    font = ImageFont.truetype(FONTS + "timesbd.ttf", round(9.0 * reg.sx))
    layer = reg.layer()
    ImageDraw.Draw(layer).text(reg.p(lx, ly - 46.0), "SONY", font=font, fill=INK + (255,), anchor="mm")
    reg.over(layer.transform(layer.size, Image.AFFINE, (0.82, 0, lx * reg.sx * 0.18, 0, 1, 0)))  # SONY is wide
    ps_logo(reg, lx, ly + 38.0, 13.0)
    reg.text("PlayStation", "arialbi.ttf", 4.6, lx, ly + 44.0, INK)
    for k in range(5):                                            # the lid's grip: a row of dots at its front right
        a = math.radians(-32 + k * 4.5)
        reg.circle(lx + (r - 7) * math.cos(a), ly - (r - 7) * math.sin(a), 0.5, shade(CASE, -0.2))
    reg.text("COMPACT", "arialbd.ttf", 1.8, *top_point(L.SEAMS[1] - 8.0, 176.0), shade(CASE, -0.4))
    reg.text("disc", "timesbi.ttf", 2.6, *top_point(L.SEAMS[1] - 8.0, 172.5), shade(CASE, -0.4))
    # The buttons in their wells, and the power light's slot.
    for name, colour, size in (("power", (46, 178, 150), 3.6), ("reset", INK, 2.2), ("open", (66, 118, 212), 3.6)):
        x, y, br = L.BUTTONS[name]
        well(reg, x, y, br, name.upper(), colour, size)
    x, y, length, width = L.LED
    lx, ly = top_point(x, y)
    reg.rect_(lx - length / 2, ly - width / 2, lx + length / 2, ly + width / 2, (40, 42, 44), r=1.0)
    return reg


def front():
    """The recess's back wall seen from in front: x to the right, z up."""
    (x0, x1), (z0, z1) = L.RECESS["x"], L.RECESS["z"]
    w, h = x1 - x0, z1 - z0
    reg = Region(L.REGIONS["front"], w, h, shade(CASE, -0.08))

    def at(x, z):
        return x - x0, z1 - z
    for k, x in enumerate((-30.0, 32.0)):
        # The controller port: a rounded opening with its pins; the memory card slot above it.
        reg.rect_(*at(x - 19.0, 23.0), *at(x + 19.0, 9.0), shade(CASE, -0.3), r=2.5)
        reg.rect_(*at(x - 17.5, 21.5), *at(x + 17.5, 10.5), (34, 35, 38), r=2.0)
        for j in range(9):
            reg.rect_(*at(x - 13.0 + j * 3.25 - 0.6, 17.0), *at(x - 13.0 + j * 3.25 + 0.6, 14.0), (150, 150, 150))
        reg.rect_(*at(x - 16.0, 33.5), *at(x + 16.0, 27.0), shade(CASE, -0.3), r=1.0)
        reg.rect_(*at(x - 15.0, 31.5), *at(x + 15.0, 28.8), (30, 31, 34), r=0.6)
        reg.text(str(k + 1), "arialbd.ttf", 4.0, *at(x, 37.0), INK)
        reg.text("MEMORY CARD", "arial.ttf", 2.0, *at(x, 25.0), INK)
    return reg


def label():
    """The disc's label side, seen looking at it: Odyssey's art, its title, the hole and its clear ring."""
    size = 2 * L.DISC["r"]
    art = space((960, 960))
    d = ImageDraw.Draw(art)
    ship(d, 250, 600, 3.6, "#FFFFFF", "#FFB23C")
    d.text((480, 230), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 120), fill="#FFE45C", anchor="mm",
           stroke_width=6, stroke_fill="#5A1A08")
    d.text((480, 760), "SCES-01986", font=ImageFont.truetype(FONTS + "arialbd.ttf", 34), fill="#D8D0F0", anchor="mm")
    reg = Region(L.REGIONS["label"], size, size, (0, 0, 0))
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 959, 959], fill=255)
    art.putalpha(mask)
    reg.img.paste(art.resize(reg.img.size, Image.LANCZOS), (0, 0), art.resize(reg.img.size, Image.LANCZOS))
    c = size / 2
    reg.circle(c, c, 22.0, (225, 228, 232))
    reg.circle(c, c, 18.0, (190, 194, 200))
    reg.circle(c, c, L.DISC["hole"], (30, 30, 32))
    ps_logo(reg, c - 12.0, c + 4.0, 7.0)
    return reg


def data_side():
    """The disc's other side: black, a faint rainbow where the light catches it, the clear ring round the hole."""
    size = 2 * L.DISC["r"]
    reg = Region(L.REGIONS["data"], size, size, (0, 0, 0))
    c = size / 2
    reg.circle(c, c, c, (22, 22, 26))
    sheen = reg.layer()
    d = ImageDraw.Draw(sheen)
    for k, colour in enumerate(((255, 90, 90), (255, 210, 90), (90, 255, 140), (90, 160, 255), (200, 110, 255))):
        d.arc(reg.box(c - 50 + k * 4, c - 50 + k * 4, c + 50 - k * 4, c + 50 - k * 4), 200, 250, fill=colour + (90,),
              width=round(3 * reg.sx))
    reg.over(sheen.filter(ImageFilter.GaussianBlur(2 * reg.sx)))
    reg.circle(c, c, 22.0, (150, 156, 164))
    reg.circle(c, c, 17.0, (120, 124, 130))
    reg.circle(c, c, L.DISC["hole"], (30, 30, 32))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), label(), data_side()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("led", (90, 255, 120)), ("dark", rgb(L.COLOURS["dark"])), ("lens", (70, 120, 255)),
                         ("metal", (190, 194, 200))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "psx_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
