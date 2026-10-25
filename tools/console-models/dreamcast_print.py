"""The Dreamcast card's printing (dreamcast_print.png), for the console theme's model (dreamcast.py).

One image, laid out as dreamcast_layout.REGIONS says: the console from above (the lid's blue swirl and Dreamcast, its
arrow, its rim, the two creases to the back corners, POWER and OPEN), its front (SEGA over the ports' panel, A B C D),
the controller from above (the swirl and Dreamcast, the VMU's face round its screen, the D-pad's and buttons' marks,
START), the VMU's screens (off, and the made-up game's ship on it), the GD-ROM's label (a made-up game, Odyssey), and
swatches. Run it with the system Python (Pillow):

    python tools/console-models/dreamcast_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dreamcast_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
BLUE = (40, 90, 200)
GREY = (150, 150, 152)
INK = (110, 110, 114)
LCD = (176, 206, 168)
PIXEL = (40, 56, 44)


def shade(colour, k):
    return tuple(max(0, min(255, round(c * (1 + k)))) for c in colour)


def swirl(reg, x, y, r, ink, width):
    """The Dreamcast's swirl: a spiral of two and a half turns, its middle at (x, y)."""
    points = []
    for k in range(121):
        a = 2.5 * 2 * math.pi * k / 120
        rr = r * (0.08 + 0.92 * k / 120)
        points.append(reg.p(x + rr * math.cos(a), y + rr * math.sin(a)))
    reg.draw.line(points, fill=ink, width=reg.width(width), joint="curve")


def badge(reg, x, y, size, ink):
    """The swirl over Dreamcast, its middle at (x, y)."""
    swirl(reg, x, y - size * 0.45, size * 0.42, ink, size * 0.1)
    reg.text("Dreamcast", "timesi.ttf", size * 0.5, x, y + size * 0.42, ink)


def top():
    """The console from above: x across (-WIDTH/2 at the left), y down from the back to the front."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    (lx, ly), r = L.LID["at"], L.LID["r"]
    for side in (-1, 1):                                    # the creases from the lid to the back corners
        reg.line([at(side * r * 0.98, ly + 6.0), at(side * (L.WIDTH / 2 - 2.0), L.DEPTH - 4.0)], shade(CASE, -0.12),
                 0.6)
    reg.circle(*at(lx, ly), r + 1.2, shade(CASE, -0.18))
    reg.circle(*at(lx, ly), r, shade(CASE, 0.02))
    badge(reg, *at(0.0, ly + 30.0), 22.0, BLUE)
    reg.poly([at(x, y) for x, y in L.ARROW], shade(CASE, -0.1))
    for name, (x, y) in (("POWER", L.BUTTONS["power"]), ("OPEN", L.BUTTONS["open"])):
        reg.circle(*at(x, y), L.BUTTONS["r"] + 1.0, shade(CASE, -0.1))
        reg.circle(*at(x, y), L.BUTTONS["r"], shade(CASE, 0.03))
        reg.text(name, "arial.ttf", 3.0, *at(x, y), INK)
    return reg


def front():
    """The front from in front: x across, z down from the front's top."""
    h = L.TOP[0]
    reg = Region(L.REGIONS["front"], L.WIDTH, h, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, h - z

    (px0, px1), (pz0, pz1) = L.PANEL["x"], L.PANEL["z"]
    reg.rect_(*at(px0, pz1), *at(px1, pz0), shade(CASE, -0.05), r=2.0)
    reg.text("SEGA", "ariblk.ttf", 6.0, *at(-21.0, pz1 - 3.6), shade(CASE, -0.3))
    (pw, ph), pz = L.PORTS["size"], L.PORTS["z"]
    for c, x in zip("ABCD", L.PORTS["x"]):
        reg.rect_(*at(x - pw / 2 - 2.0, pz + ph / 2 + 2.0), *at(x + pw / 2 + 2.0, pz - ph / 2 - 2.0),
                  shade(CASE, -0.12), r=5.0)
        reg.rect_(*at(x - pw / 2, pz + ph / 2), *at(x + pw / 2, pz - ph / 2), (24, 24, 26), r=4.0)
        reg.text(c, "arial.ttf", 3.2, *at(x, pz + ph / 2 + 3.6), INK)
    reg.text("Compatible with", "arial.ttf", 2.0, *at(68.0, 24.0), INK)
    reg.text("Windows CE", "arialbd.ttf", 2.6, *at(68.0, 20.0), INK)
    return reg


def pad():
    """The controller from above: x across (-80 at the left), y down from its top (80) to its grips' ends."""
    w, h = 160.0, 160.0
    reg = Region(L.REGIONS["pad"], w, h, CASE)

    def at(x, y):
        return x + w / 2, 80.0 - y

    badge(reg, *at(0.0, 66.0), 13.0, BLUE)
    (sx, sy), sw, sh = L.PAD["slot"]
    reg.rect_(*at(sx - sw / 2, sy + sh / 2), *at(sx + sw / 2, sy - sh / 2), (216, 216, 214), r=8.0)
    reg.rect_(*at(sx - sw / 2 + 3.0, sy + sh / 2 - 3.0), *at(sx + sw / 2 - 3.0, sy - sh / 2 + 3.0), (226, 226, 222),
              r=6.0)
    (vx, vy), vw, vh = L.PAD["screen"]
    reg.rect_(*at(vx - vw / 2 - 2.0, vy + vh / 2 + 2.0), *at(vx + vw / 2 + 2.0, vy - vh / 2 - 2.0), (90, 92, 96),
              r=2.0)
    (cx, cy), reach, _ = L.PAD["abxy"]
    for c, (dx, dy), colour in (("A", (0, -1), (220, 60, 50)), ("B", (1, 0), (40, 110, 220)),
                                ("X", (-1, 0), (240, 200, 40)), ("Y", (0, 1), (60, 180, 90))):
        reg.text(c, "arialbd.ttf", 3.6, *at(cx + dx * reach, cy + dy * reach), shade(colour, -0.3))
    (tx, ty), ts = L.PAD["start"]
    reg.poly([at(tx - ts / 2, ty - ts * 0.4), at(tx + ts / 2, ty - ts * 0.4), at(tx, ty + ts * 0.5)],
             shade(CASE, -0.1))
    reg.text("START", "arial.ttf", 2.6, *at(tx, ty - ts * 0.4 - 3.0), INK)
    return reg


def vmu(lit):
    """The VMU's screen: its 48 x 32 LCD, blank, or the made-up game's ship and its name."""
    reg = Region(L.REGIONS["vmu_on" if lit else "vmu_off"], 48.0, 32.0, LCD)
    if lit:
        img = Image.new("1", (48, 32), 1)
        d = ImageDraw.Draw(img)
        ship(d, 13, 17, 0.5, 0, 0)
        d.ellipse([30, 10, 41, 21], outline=0)
        d.line([(27, 18), (45, 13)], fill=0)
        for x, y in ((6, 4), (22, 6), (40, 27), (12, 27), (44, 4)):
            d.point((x, y), fill=0)
        layer = Image.new("RGB", (48, 32), LCD)
        layer.paste(Image.new("RGB", (48, 32), PIXEL), (0, 0), Image.eval(img, lambda v: 255 - v * 255).convert("L"))
        x0, y0, x1, y1 = reg.box(0.0, 0.0, 48.0, 32.0)
        reg.img.paste(layer.resize((round(x1 - x0), round(y1 - y0)), Image.NEAREST), (round(x0), round(y0)))
    return reg


def disc():
    """The GD-ROM's label side: the silver rim, the label (a made-up game, Odyssey), GD-ROM and the swirl."""
    r = L.DISC["r"]
    reg = Region(L.REGIONS["disc"], 2 * r, 2 * r, CASE)
    reg.circle(r, r, r, (196, 198, 204))
    art = space((480, 480)).convert("RGB")
    ship(ImageDraw.Draw(art), 140, 300, 3.0, "#FFFFFF", "#FFB23C")
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).ellipse([10, 10, 470, 470], fill=255)
    ImageDraw.Draw(mask).ellipse([168, 168, 312, 312], fill=0)
    x0, y0, x1, y1 = reg.box(4.0, 4.0, 2 * r - 4.0, 2 * r - 4.0)
    size = (round(x1 - x0), round(y1 - y0))
    reg.img.paste(art.resize(size, Image.LANCZOS), (round(x0), round(y0)), mask.resize(size, Image.LANCZOS))
    reg.text("ODYSSEY", "ariblk.ttf", 12.0, r, r - 30.0, (255, 214, 70))
    swirl(reg, r - 22.0, r + 36.0, 5.0, (236, 236, 240), 1.0)
    reg.text("GD-ROM", "ariblk.ttf", 6.0, r + 8.0, r + 36.0, (236, 236, 240))
    reg.circle(r, r, 18.0, (200, 204, 210))
    reg.circle(r, r, L.DISC["hole"], (60, 60, 64))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), vmu(False), vmu(True), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, dark=(30, 30, 32), button=shade(CASE, -0.04), lit=(255, 150, 30), off=(150, 120, 90),
                   disc=(196, 198, 204), cable=(200, 196, 220), red=(220, 60, 50), blue=(40, 110, 220),
                   yellow=(240, 200, 40), green=(60, 180, 90), grey=(206, 206, 204))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "dreamcast_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
