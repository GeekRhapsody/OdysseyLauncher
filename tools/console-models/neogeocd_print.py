"""The Neo Geo CD set's printing, for the console theme's Neo Geo CD model (tools/console-models/neogeocd.py).

Draws its atlas, its regions as neogeocd_layout.py places them, each in millimetres as the model's planar UVs map it:
the console's top from above (the lid's SNK NEO·GEO CD, PRO-GEAR SPEC and ADVANCED ENTERTAINMENT SYSTEM, the Compact
Disc logo, the lid's dots, the deck's edge, the vent strip, POWER on its button, the access light's window); the front
face (the two controller ports and their numbers); the controller's top (the ring's eight arrows, SNK NEO·GEO, SELECT,
START, A, B, C and D); the CD's label (a made-up game, Odyssey); and the swatches small parts take their colour from.
Run it with the system Python (Pillow):

    python tools/console-models/neogeocd_print.py <out folder>

It writes neogeocd_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neogeocd_layout as L  # noqa: E402
from cdi_print import disc_logo  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
INK = (214, 214, 216)
GREY = (176, 176, 180)


def stretched(reg, text, font, x0, y0, x1, y1, fill, outline=None):
    """text drawn to fill the box (x0, y0)-(x1, y1), stretched to it."""
    mask = Image.new("L", (1600, 260), 0)
    d = ImageDraw.Draw(mask)
    f = ImageFont.truetype(FONTS + font, 200)
    if outline:
        d.text((20, 130), text, font=f, fill=255, anchor="lm", stroke_width=12, stroke_fill=255)
        inner = Image.new("L", mask.size, 0)
        ImageDraw.Draw(inner).text((20, 130), text, font=f, fill=255, anchor="lm")
        box = mask.getbbox()
        mask = Image.composite(Image.new("L", mask.size, 0), mask, inner)
    else:
        d.text((20, 130), text, font=f, fill=255, anchor="lm")
        box = mask.getbbox()
    mask = mask.crop(box)
    a, b, c, e = reg.box(x0, y0, x1, y1)
    mask = mask.resize((max(1, round(c - a)), max(1, round(e - b))), Image.LANCZOS)
    reg.img.paste(Image.new("RGBA", mask.size, fill + (255,)), (round(a), round(b)), mask)


def neogeo(reg, x, y, h, ink, cd=True):
    """NEO·GEO (and CD, in outline), h tall, its left middle at (x, y)."""
    w = h * 6.2
    stretched(reg, "NEO·GEO", "timesbd.ttf", x, y - h / 2, x + w, y + h / 2, ink)
    if cd:
        stretched(reg, "CD", "times.ttf", x + w + h * 0.3, y - h / 2, x + w + h * 2.3, y + h / 2, ink, outline=True)


# ---- The top -----------------------------------------------------------------------------------------------------------

def top():
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["top"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y
    deck = L.DECK
    reg.poly([at(x, y) for x, y in L.bowed(*deck["x"], *deck["y"], deck["bow"])], shade(CASE, 0.03))
    lid = L.LID
    outline = [at(x, y) for x, y in L.bowed(*lid["x"], *lid["y"], lid["bow"])]
    reg.poly(outline, shade(CASE, 0.07))
    reg.line(outline + outline[:1], (6, 6, 7), 0.6)
    reg.text("SNK", "ariblk.ttf", 4.6, *at(0.0, 176.0), INK)
    neogeo(reg, *at(-46.0, 160.0), 8.6, INK)
    reg.text("PRO-GEAR SPEC", "arial.ttf", 2.6, *at(16.0, 150.0), INK)
    reg.text("ADVANCED ENTERTAINMENT SYSTEM", "arial.ttf", 2.6, *at(0.0, 145.0), INK)
    disc_logo(reg, *at(52.0, 168.0), 9.0, INK)
    for k in range(6):                                         # the lid's dots, where it's lifted
        x = -10.0 + 4.0 * k
        reg.circle(*at(x, 82.0 if k % 2 else 86.0), 0.7, (8, 8, 9))
    (vx0, vx1), (vy0, vy1) = L.VENT["x"], L.VENT["y"]
    reg.rect_(*at(vx0, vy1), *at(vx1, vy0), (6, 6, 7))
    n = L.VENT["slats"]
    for k in range(n):
        y = vy0 + (vy1 - vy0) * (k + 0.5) / n
        reg.rect_(*at(vx0 + 2.0, y + 2.6), *at(vx1 - 2.0, y - 2.6), shade(CASE, 0.06))
    (px, py), pr = L.POWER["at"], L.POWER["r"]
    reg.circle(*at(px, py), pr, (150, 150, 154))
    reg.circle(*at(px, py), pr - 1.2, (176, 176, 180))
    reg.text("POWER", "arial.ttf", 3.2, *at(px, py), (70, 70, 74))
    reg.circle(*at(*L.LIGHT["at"]), L.LIGHT["r"], (40, 12, 12))
    return reg


# ---- The front ---------------------------------------------------------------------------------------------------------

def front():
    w, h = L.WIDTH, L.BODY_TOP
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    (z0, z1), pw = L.PORTS["z"], L.PORTS["width"]
    for k, x in enumerate(L.PORTS["x"]):
        reg.rect_(*at(x - pw / 2 - 2.0, z1 + 2.0), *at(x + pw / 2 + 2.0, z0 - 2.0), shade(CASE, 0.05), r=2.0)
        reg.rect_(*at(x - pw / 2, z1), *at(x + pw / 2, z0), (6, 6, 7), r=2.0)
        for j in range(8):
            reg.rect_(*at(x - 12.0 + 3.4 * j, (z0 + z1) / 2 + 1.0), *at(x - 10.6 + 3.4 * j, (z0 + z1) / 2 - 1.0),
                      (170, 150, 90))
        reg.text(str(k + 1), "arial.ttf", 4.0, *at(x - pw / 2 - 6.0 if k == 0 else x + pw / 2 + 6.0, (z0 + z1) / 2),
                 (110, 110, 114))
    return reg


# ---- The controller ----------------------------------------------------------------------------------------------------

def pad():
    w, h = 156.0, 76.0
    reg = Region(L.REGIONS["pad"], w, h, CASE)

    def at(x, y):
        return x + w / 2, h / 2 - y
    (rx, ry), (r0, r1) = L.RING["at"], L.RING["r"]
    reg.circle(*at(rx, ry), r1, (12, 12, 13))
    reg.circle(*at(rx, ry), r0 + 1.0, (6, 6, 7))
    for k in range(8):                                          # the ring's arrows, pointing out
        a = math.radians(45 * k)
        c, s = math.cos(a), math.sin(a)
        mid = (r0 + r1) / 2 + 0.6
        tip = (rx + c * (mid + 3.0), ry + s * (mid + 3.0))
        l = (rx + c * (mid - 2.2) - s * 2.6, ry + s * (mid - 2.2) + c * 2.6)
        r = (rx + c * (mid - 2.2) + s * 2.6, ry + s * (mid - 2.2) - c * 2.6)
        reg.poly([at(*tip), at(*l), at(*r)], GREY)
    reg.text("SNK", "ariblk.ttf", 5.2, *at(4.0, 27.0), INK)
    neogeo(reg, *at(-13.0, 20.0), 4.0, INK, cd=False)
    for name in ("select", "start"):
        x, y = L.SMALL[name]
        reg.text(name.upper(), "arialbd.ttf", 2.8, *at(x + 1.0, y + 6.0), INK)
    for name in ("a", "b", "c", "d"):
        x, y = L.FACE[name]
        dx, dy = {"a": (-6.0, -10.0), "b": (9.0, -10.0), "c": (-11.0, -5.0), "d": (9.0, -9.0)}[name]
        reg.text(name.upper(), "arialbd.ttf", 4.6, *at(x + dx, y + dy), INK)
    return reg


def disc():
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (20, 20, 22))
    c = dm / 2
    art = space((600, 600)).convert("RGB")
    ship(ImageDraw.Draw(art), 180, 330, 4.0, "#FFFFFF", "#FFB23C")
    mask = Image.new("L", reg.img.size, 0)
    dm_ = ImageDraw.Draw(mask)
    dm_.ellipse(reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0), fill=255)
    dm_.ellipse(reg.box(c - 21.0, c - 21.0, c + 21.0, c + 21.0), fill=0)
    x0, y0, x1, y1 = reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.img.paste(layer, (0, 0), mask)
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)   # the clear hub
    reg.text("ODYSSEY", "ariblk.ttf", 11.0, c, c - 36.0, (255, 214, 70))
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("grey", (176, 176, 180)), ("red", (220, 70, 60)), ("yellow", (240, 196, 40)),
                         ("green", (70, 170, 90)), ("blue", (50, 110, 200)), ("lit", (255, 50, 40)),
                         ("dark", (6, 6, 7)), ("silver", (200, 204, 210))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "neogeocd_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
