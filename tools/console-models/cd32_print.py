"""The Amiga CD32's printing, for the console theme's CD32 model (tools/console-models/cd32.py).

Draws its atlas, its regions as cd32_layout.py places them, each in millimetres as the model's planar UVs map it: the
console seen from above (32bit on the dome, its smoked window, Commodore, the AMIGA CD32 badge on the slope); its front
face (RESET, the power and CD lights off, the volume slider's slot and scale, the headphone socket); the pad's top
(its D-pad's ring and dots, AMIGA CD32, the play/pause slot and its marks, the buttons' marks); the CD's two sides (a
made-up game, Odyssey, and the shiny side); and the swatches small parts take their colour from. Run it with the
system Python (Pillow):

    python tools/console-models/cd32_print.py <out folder>

It writes cd32_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd32_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
PAD = rgb(L.COLOURS["pad"])
RED = (214, 64, 44)
WHITE = (232, 232, 232)


def amiga_cd32(reg, x, y, size):
    """AMIGA in red serif italics, CD in white, 32 in small red: its left edge at x, its middle at y."""
    f1 = ImageFont.truetype(FONTS + "timesbi.ttf", max(1, round(size * reg.sx)))
    f2 = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(size * 0.92 * reg.sx)))
    f3 = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(size * 0.48 * reg.sx)))
    px, py = reg.p(x, y)
    reg.draw.text((px, py), "AMIGA", font=f1, fill=RED, anchor="lm")
    px += f1.getlength("AMIGA") + size * 0.4 * reg.sx
    reg.draw.text((px, py), "CD", font=f2, fill=WHITE, anchor="lm")
    px += f2.getlength("CD") + size * 0.06 * reg.sx
    reg.draw.text((px, py - size * 0.24 * reg.sy), "32", font=f3, fill=RED, anchor="lm")


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    (dx, dy), r = L.DOME["at"], L.DOME["r"]
    reg.circle(*at(dx, dy), r, shade(CASE, 0.06))
    reg.circle(*at(dx, dy), r, None, outline=shade(CASE, -0.3), width=0.5)
    layer = reg.layer()                                      # the smoked window: the dome's front half, lens-shaped
    d = ImageDraw.Draw(layer)
    d.chord(reg.box(*at(dx - r * 0.82, dy + r * 0.25), *at(dx + r * 0.82, dy - r * 0.95)), 0, 180,
            fill=(14, 14, 16, 255))
    reg.over(layer)
    reg.line([at(dx - r * 0.92, dy + r * 0.36), at(dx + r * 0.92, dy + r * 0.36)], shade(CASE, -0.3), 0.5)
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(13.0 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(*at(dx - 4.0, dy + r * 0.62)), "32bit", font=f, fill=(206, 206, 210, 255),
                               anchor="mm")
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.15, -0.15 * reg.p(0, at(0, dy + r * 0.62)[1])[1],
                                                        0, 1, 0)))
    reg.text("Commodore", "arialbd.ttf", 9.0, *at(98.0, 190.0), WHITE)
    reg.rect_(*at(16.0, 52.0), *at(142.0, 30.0), (24, 24, 26))
    amiga_cd32(reg, *at(22.0, 41.0), 11.0)
    reg.text("DO NOT STARE INTO BEAM", "arial.ttf", 2.6, *at(-104.0, 32.0), shade(CASE, -0.25))
    return reg


FRONT_H = L.FRONT[1][1]


def front():
    reg = Region(L.REGIONS["front"], L.WIDTH, FRONT_H, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, FRONT_H - z
    (x0, x1), (z0, z1) = L.RESET["x"], L.RESET["z"]
    reg.rect_(*at(x0 - 2.0, z1 + 2.0), *at(x1 + 2.0, z0 - 2.0), shade(CASE, -0.2), r=(z1 - z0) / 2 + 2.0)
    reg.text("RESET", "arial.ttf", 2.4, *at((x0 + x1) / 2, z0 - 5.0), shade(CASE, 0.35))
    w, h = L.LIGHTS["size"]
    for name, colour in (("power", (60, 30, 26)), ("access", (60, 46, 20))):
        x, z = L.LIGHTS[name]
        reg.rect_(*at(x - w / 2, z + h / 2), *at(x + w / 2, z - h / 2), colour, r=0.6)
    reg.rect_(*at(104.0, 28.0), *at(130.0, 24.0), (12, 12, 13))
    for k in range(14):
        reg.rect_(*at(104.0 + 2.0 * k, 19.0), *at(104.6 + 2.0 * k, 17.0 - k * 0.12), shade(CASE, 0.25))
    reg.circle(*at(140.0, 26.0), 2.6, (10, 10, 11))
    reg.circle(*at(140.0, 26.0), 1.2, (60, 60, 64))
    return reg


def pad():
    reg = Region(L.REGIONS["pad"], L.PAD["width"], L.PAD["length"], PAD)
    p = L.PAD

    def at(x, y):
        return x + L.PAD["width"] / 2, L.PAD["length"] - y
    reg.line([at(-48.0, p["band"]), at(48.0, p["band"])], shade(PAD, -0.4), 0.8)
    dx, dy, r = p["dpad"]
    reg.circle(*at(dx, dy), r + 1.2, shade(PAD, -0.35))
    for k, glyph in enumerate(("▲", "▶", "▼", "◀")):
        a = math.pi / 2 - k * math.pi / 2
        reg.text(glyph, "seguisym.ttf", 2.2, *at(dx + (r + 4.0) * math.cos(a), dy + (r + 4.0) * math.sin(a)),
                 shade(PAD, -0.4))
    for name, (x, y, br) in p["buttons"].items():
        reg.circle(*at(x, y), br + 1.0, shade(PAD, -0.3))
    reg.line([at(53.6, 53.3), at(70.9, 58.8)], shade(PAD, -0.3), 7.0)
    reg.line([at(58.5, 36.0), at(75.4, 40.9)], shade(PAD, -0.3), 7.0)
    lx, ly, lw = p["logo"]
    amiga_cd32(reg, *at(lx - lw / 2, ly), 6.4)
    x, y, w, h = p["pause"]
    reg.rect_(*at(x - w / 2, y + h / 2), *at(x + w / 2, y - h / 2), (16, 16, 18), r=h / 2)
    reg.text("II ▶", "seguisym.ttf", 2.6, *at(x + 4.0, y - 6.0), shade(PAD, -0.4))
    reg.text("◀◀", "seguisym.ttf", 2.6, *at(-62.0, 72.0), shade(PAD, -0.4))
    reg.text("▶▶", "seguisym.ttf", 2.6, *at(62.0, 72.0), shade(PAD, -0.4))
    return reg


def disc_side(region, label):
    r = L.DISC["r"]
    reg = Region(region, 2 * r, 2 * r, (40, 40, 44))
    c = r
    if label:
        art = space((560, 560))
        d = ImageDraw.Draw(art)
        ship(d, 200, 240, 3.6, "#FFFFFF", "#FFB23C")
        x0, y0, x1, y1 = reg.box(0.0, 0.0, 2 * r, 2 * r)
        reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (0, 0))
        reg.text("ODYSSEY", "ariblk.ttf", 15.0, c, c - 34.0, (255, 214, 70))
        reg.rect_(0.0, c + 20.0, 2 * r, 2 * r, (20, 20, 22))
        amiga_cd32(reg, c - 32.0, c + 32.0, 10.0)
    else:
        for k in range(60):                                  # the shiny side: silver, a faint rainbow sheen
            t = k / 60
            colour = (round(196 + 22 * math.sin(6.3 * t)), round(198 + 22 * math.sin(6.3 * t + 2.1)),
                      round(204 + 22 * math.sin(6.3 * t + 4.2)))
            reg.circle(c, c, r * (1 - t * 0.8), colour)
    reg.circle(c, c, 17.0, (205, 208, 214))
    reg.circle(c, c, L.DISC["hole"], (30, 30, 34))
    mask = Image.new("L", reg.img.size, 0)
    ImageDraw.Draw(mask).ellipse(reg.box(0.0, 0.0, 2 * r, 2 * r), fill=255)
    out = Image.new("RGBA", reg.img.size, (190, 192, 198, 255))
    out.paste(reg.img, (0, 0), mask)
    reg.img = out
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), disc_side(L.REGIONS["disc"], True), disc_side(L.REGIONS["data"], False)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("dark", rgb(L.COLOURS["dark"])), ("green", (92, 200, 160)), ("yellow", (242, 210, 60)),
                         ("red", (224, 87, 58)), ("blue", (77, 104, 216)), ("lit", (255, 70, 50)),
                         ("amber", (255, 180, 50)), ("grey", PAD), ("smoke", (16, 16, 18))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "cd32_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
