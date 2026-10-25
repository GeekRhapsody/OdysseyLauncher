"""The Mega-CD's printing, for the console theme's Mega-CD model (tools/console-models/mega_cd.py).

Draws its atlas, its regions as mega_cd_layout.py places them, each in millimetres as the model's planar UVs map it: the
Mega-CD's front panel (the glossy black, SEGA under the door, the READY, compact disc and ACCESS panel, the four
lights' legends and their lights off); the tray's door (MEGA-CD); the CD's two sides (a made-up game, Odyssey, and the
shiny side); and the swatches small parts take their colour from. The Mega Drive on it keeps mega_drive_print.py's
printing. Run it with the system Python (Pillow):

    python tools/console-models/mega_cd_print.py <out folder>

It writes mega_cd_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mega_cd_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

GLOSS = rgb(L.COLOURS["gloss"])
WHITE = (232, 232, 234)
GREY = (150, 152, 156)


def sega(reg, x, y, size, fill):
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(size * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(x, y), "SEGA", font=f, fill=fill + (255,), anchor="mm")
    yc = reg.p(0, y)[1]
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.18, -0.18 * yc, 0, 1, 0)))


def front():
    (x0, x1), (z0, z1) = L.PANEL["x"], L.PANEL["z"]
    w, h = x1 - x0, z1 - z0
    reg = Region(L.REGIONS["front"], w, h, GLOSS)

    def at(x, z):
        return x - x0, z1 - z
    reg.rect_(0.0, 0.0, w, h, None, r=h / 2, outline=shade(GLOSS, 0.3), width=0.5)
    (dx0, dx1), (dz0, dz1) = L.DOOR["x"], L.DOOR["z"]
    reg.rect_(*at(dx0 - 1.5, dz1 + 1.5), *at(dx1 + 1.5, dz0 - 1.5), (4, 4, 5), r=1.5)
    sega(reg, *at((dx0 + dx1) / 2, dz0 - 7.0), 5.0, GREY)
    # The READY / compact disc / ACCESS panel and the lights' legends under it.
    px0, px1 = 28.0, 122.0
    reg.rect_(*at(px0, 48.0), *at(px1, 31.0), None, r=3.0, outline=GREY, width=0.4)
    for name, (x, z) in (("READY", L.LIGHTS["ready"]), ("ACCESS", L.LIGHTS["access"])):
        pw, ph = L.LIGHTS["size"]
        reg.rect_(*at(x - pw / 2, z + ph / 2), *at(x + pw / 2, z - ph / 2), (70, 72, 78), r=1.2)
        reg.text(name, "arialbd.ttf", 3.4, *at(x, z), (200, 202, 208))
    reg.text("COMPACT", "arialbd.ttf", 1.4, *at(76.0, 43.2), WHITE)
    reg.text("disc", "arialbd.ttf", 5.4, *at(75.0, 39.4), WHITE)
    reg.text("DIGITAL AUDIO", "arialbd.ttf", 1.2, *at(75.0, 35.6), WHITE)
    reg.rect_(*at(px0, 28.0), *at(px1, 19.0), None, r=2.0, outline=GREY, width=0.3)
    for k, (name, colours) in enumerate((("CD\nACCESS", ((40, 120, 60), (120, 30, 30))), ("CD IN", ((40, 120, 60),)),
                                         ("CD OUT", ((40, 120, 60), (140, 60, 20))),
                                         ("STAND-BY\nMODE", ((40, 120, 60),)))):
        cx = px0 + 11.0 + k * 23.5
        lines = name.split("\n")
        for j, line in enumerate(lines):
            reg.text(line, "arial.ttf", 1.8, *at(cx, 26.0 - j * 2.0 + (len(lines) - 1) * 1.0), WHITE)
        for j, colour in enumerate(colours):
            lx = cx - 3.0 * (len(colours) - 1) + 6.0 * j
            reg.rect_(*at(lx - 2.0, 21.6), *at(lx + 2.0, 20.4), colour)
        if k:
            reg.line([at(px0 + k * 23.5, 27.0), at(px0 + k * 23.5, 20.0)], GREY, 0.3)
    return reg


def door():
    (x0, x1), (z0, z1) = L.DOOR["x"], L.DOOR["z"]
    w, h = x1 - x0, z1 - z0
    reg = Region(L.REGIONS["door"], w, h, (14, 14, 16))
    reg.rect_(0.5, 0.5, w - 0.5, h - 0.5, None, outline=(40, 40, 44), width=0.4)
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(7.0 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(w / 2, h / 2), "MEGA-CD", font=f, fill=WHITE + (255,), anchor="mm")
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.2, -0.2 * reg.p(0, h / 2)[1], 0, 1, 0)))
    return reg


def disc_side(region, label):
    r = L.DISC["r"]
    reg = Region(region, 2 * r, 2 * r, (40, 40, 44))
    c = r
    if label:
        art = space((640, 640))
        d = ImageDraw.Draw(art)
        ship(d, 220, 270, 4.0, "#FFFFFF", "#FFB23C")
        x0, y0, x1, y1 = reg.box(0.0, 0.0, 2 * r, 2 * r)
        reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (0, 0))
        reg.text("ODYSSEY", "ariblk.ttf", 15.0, c, c - 34.0, (255, 214, 70))
        reg.rect_(0.0, c + 22.0, 2 * r, 2 * r, (14, 14, 16))
        sega(reg, c, c + 32.0, 8.0, WHITE)
        reg.text("MEGA-CD", "arialbd.ttf", 4.6, c, c + 42.0, (220, 220, 224))
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
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["case"]))
    for reg in (front(), door(), disc_side(L.REGIONS["disc"], True), disc_side(L.REGIONS["data"], False)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("green", (90, 255, 110)), ("red", (255, 60, 40)), ("dark", (6, 6, 7)), ("grey", GREY)):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "mega_cd_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
