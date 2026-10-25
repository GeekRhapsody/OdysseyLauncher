"""The Sega Saturn card's printing (saturn_print.png), for the console theme's model (saturn.py).

One image, laid out as saturn_layout.REGIONS says: the console from above (the lid's planet and SEGA SATURN and its two
sweeps, the groove round the lid, POWER, OPEN, ACCESS and RESET, SEGA at the front left, CARTRIDGE INPUT on the slot's
flap), its front (the ports' band, CONTROL 1 and 2), the pad from above (SEGA SATURN, START, the buttons' letters, the
D-pad's cross), the CD's label (a made-up game, Odyssey), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/saturn_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import saturn_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
GREY = (150, 150, 156)
LIGHT = (214, 214, 218)


def shade(colour, k):
    return tuple(max(0, min(255, round(c * (1 + k)))) for c in colour)


def planet(reg, x, y, r, ink):
    """The Saturn's planet: a disc of stripes in a tilted ring."""
    for k in range(7):                                       # the disc's stripes
        dy = -r + (k + 0.5) * 2 * r / 7
        half = math.sqrt(max(0.0, r * r - dy * dy))
        reg.rect_(x - half, y + dy - r / 9, x + half, y + dy + r / 9, ink)
    reg.draw.ellipse(reg.box(x - 1.9 * r, y - 0.55 * r, x + 1.9 * r, y + 0.55 * r), outline=ink,
                     width=reg.width(r * 0.16))


def wordmark(reg, x, y, size, ink):
    """SEGA SATURN, its middle at (x, y)."""
    reg.text("SEGA SATURN", "ariblk.ttf", size, x, y, ink)


def top():
    """The console from above: x across (-WIDTH/2 at the left), y down from the back to the front."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    lid = L.lid_outline(16)
    grown = [(x * 1.06, L.LID["front"] - 6.0 + (y - L.LID["front"]) * 1.03) for x, y in lid]
    reg.draw.line([reg.p(*at(x, y)) for x, y in grown + grown[:1]], fill=shade(CASE, -0.5), width=reg.width(1.2))
    reg.draw.line([reg.p(*at(x, y)) for x, y in lid + lid[:1]], fill=shade(CASE, -0.6), width=reg.width(0.8))
    cy = (L.LID["front"] + L.LID["back"]) / 2
    for k, (x0, x1, dy) in enumerate(((-58.0, 44.0, 12.0), (-10.0, 60.0, -2.0))):   # the lid's two sweeps
        reg.poly([at(x0, cy + dy), at(x1, cy + dy + 6.0), at(x1 + 4.0, cy + dy + 4.0), at(x0 + 6.0, cy + dy - 1.0)],
                 shade(CASE, 0.6 if k == 0 else 0.4))
    planet(reg, *at(0.0, cy + 46.0), 6.0, LIGHT)
    wordmark(reg, *at(0.0, cy - 20.0), 9.0, LIGHT)
    reg.text("SEGA", "ariblk.ttf", 9.0, *at(-108.0, 18.0), LIGHT)
    reg.text("POWER", "arialbd.ttf", 3.2, *at(-62.0, 18.0), GREY)
    reg.text("ACCESS", "arialbd.ttf", 3.2, *at(58.0, 14.0), GREY)
    (px, py, pw, pd) = L.BUTTONS["power"]
    reg.draw.ellipse(reg.box(*at(px - pw / 2, py + pd / 2), *at(px + pw / 2, py - pd / 2)), fill=shade(CASE, 0.3))
    (ox, oy, ow, od) = L.BUTTONS["open"]
    reg.rect_(*at(ox - ow / 2, oy + od / 2), *at(ox + ow / 2, oy - od / 2), shade(CASE, 0.3), r=3.0)
    reg.text("OPEN", "arialbd.ttf", 3.0, *at(ox, oy), GREY)
    (rx, ry, rr) = L.BUTTONS["reset"]
    reg.circle(*at(rx, ry), rr, shade(CASE, 0.3))
    reg.text("RESET", "arialbd.ttf", 2.6, *at(rx, ry), GREY)
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    reg.rect_(*at(sx0, sy1), *at(sx1, sy0), shade(CASE, -0.4), r=1.5)
    reg.rect_(*at(sx0 + 3.0, sy1 - 3.0), *at(sx1 - 3.0, sy0 + 3.0), shade(CASE, 0.15), r=1.0)
    reg.text("CARTRIDGE INPUT", "arialbd.ttf", 4.0, *at(0.0, (sy0 + sy1) / 2), GREY)
    return reg


def front():
    """The front from in front: x across, z down from the top."""
    reg = Region(L.REGIONS["front"], L.WIDTH, L.HEIGHT, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z

    (bx0, bx1), _, (bz0, bz1) = L.BAND["x"], L.BAND["y"], L.BAND["z"]
    reg.rect_(*at(bx0, bz1), *at(bx1, bz0), shade(CASE, -0.3))
    (pw, ph), pz = L.PORTS["size"], L.PORTS["z"]
    for k, x in enumerate(L.PORTS["x"]):
        reg.rect_(*at(x - pw / 2, pz + ph / 2), *at(x + pw / 2, pz - ph / 2), (6, 6, 8), r=2.0)
        reg.rect_(*at(x - pw / 2 + 3.0, pz + 1.5), *at(x + pw / 2 - 3.0, pz - 1.5), (90, 90, 96))
        reg.text("CONTROL %d" % (k + 1), "arialbd.ttf", 2.4, *at(x, pz + ph / 2 + 3.2), GREY)
    return reg


def pad():
    """The pad from above: x across (-80 at the left), y down from its top edge (50)."""
    w, h = 160.0, 100.0
    reg = Region(L.REGIONS["pad"], w, h, CASE)

    def at(x, y):
        return x + w / 2, 50.0 - y

    (dx, dy), dr = L.PAD["dpad"]
    reg.circle(*at(dx, dy), dr, shade(CASE, 0.25))
    for ang in (0, 90, 180, 270):                            # the D-pad's cross and its arrows
        a = math.radians(ang)
        tip = (dx + math.cos(a) * dr * 0.78, dy + math.sin(a) * dr * 0.78)
        side = (-math.sin(a) * 2.4, math.cos(a) * 2.4)
        base = (dx + math.cos(a) * dr * 0.56, dy + math.sin(a) * dr * 0.56)
        reg.poly([at(*tip), at(base[0] + side[0], base[1] + side[1]), at(base[0] - side[0], base[1] - side[1])],
                 shade(CASE, 0.8))
    reg.rect_(*at(dx - dr * 0.5, dy + 1.6), *at(dx + dr * 0.5, dy - 1.6), shade(CASE, 0.5))
    reg.rect_(*at(dx - 1.6, dy + dr * 0.5), *at(dx + 1.6, dy - dr * 0.5), shade(CASE, 0.5))
    planet(reg, *at(0.0, 35.0), 2.6, LIGHT)
    wordmark(reg, *at(0.0, 28.0), 4.2, LIGHT)
    (sx, sy), (sw, sh) = L.PAD["start"]
    reg.draw.ellipse(reg.box(*at(sx - sw / 2, sy + sh / 2), *at(sx + sw / 2, sy - sh / 2)), fill=shade(CASE, 0.35))
    reg.text("START", "arialbd.ttf", 3.0, *at(sx, sy + sh / 2 + 3.0), GREY)
    for letters, points, r in (("ABC", L.PAD["abc"], L.PAD["abc_r"]), ("XYZ", L.PAD["xyz"], L.PAD["xyz_r"])):
        for c, (x, y) in zip(letters, points):
            reg.circle(*at(x, y), r, shade(CASE, 0.2))
            reg.text(c, "arialbd.ttf", r * 0.9, *at(x, y), shade(CASE, 1.4))
    return reg


def disc():
    """The CD's label side: the silver rim, the label (a made-up game, Odyssey), the clear hub."""
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
    wordmark(reg, r, r + 36.0, 6.0, (236, 236, 240))
    reg.circle(r, r, 18.0, (200, 204, 210))
    reg.circle(r, r, L.DISC["hole"], CASE)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, dark=(4, 4, 6), button=shade(CASE, 0.3), lit=(255, 70, 40), off=(40, 14, 12),
                   disc=(196, 198, 204), pad=shade(CASE, 0.1), cable=(20, 20, 22))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "saturn_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
