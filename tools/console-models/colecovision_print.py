"""The ColecoVision's printing, for the console theme's ColecoVision model (tools/console-models/colecovision.py).

Draws its atlas, its regions as colecovision_layout.py places them, each in millimetres as the model's planar UVs map
it: the console seen from above (the silver INSERT CARTRIDGE HERE plate with ON, OFF and RESET, RESET's recess); its
front face (the silver band with COLECOVISION's rainbow lettering, VIDEO GAME SYSTEM, EXPANSION MODULE INTERFACE and
the COLECO badge); a controller's top (the keys' numbers, the star and the hash, COLECO, the knob's collar); the
cartridge's label (a made-up game, Odyssey, in the black-and-white style of Coleco's labels); and the swatches small
parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/colecovision_print.py <out folder>

It writes colecovision_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colecovision_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
SILVER = rgb(L.COLOURS["silver"])
KEY = rgb(L.COLOURS["key"])
RED = (214, 40, 36)
RAINBOW = [(226, 52, 52), (240, 140, 40), (240, 214, 40), (90, 190, 70), (40, 170, 210), (70, 90, 210),
           (150, 70, 200)]


def brushed(reg, x0, y0, x1, y1):
    """A brushed aluminium strip: silver with fine streaks along it."""
    reg.rect_(x0, y0, x1, y1, SILVER)
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    k = 0
    y = y0
    while y < y1:
        shade_ = 245 if k % 3 == 0 else 150
        d.line([reg.p(x0, y), reg.p(x1, y)], fill=(shade_, shade_, shade_ + 4, 40))
        y += 0.35
        k += 1
    reg.over(layer)


def rainbow_text(reg, text, x, y, size):
    """Lettering outlined in the rainbow, letter by letter, left to right, its left edge at x and its middle at y."""
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(size * reg.sx)))
    px, py = reg.p(x, y)
    for k, ch in enumerate(text):
        colour = RAINBOW[k % len(RAINBOW)]
        reg.draw.text((px, py), ch, font=f, fill=CASE, anchor="lm", stroke_width=max(1, round(0.35 * reg.sx)),
                      stroke_fill=colour)
        px += f.getlength(ch) + 0.4 * reg.sx


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    (x0, x1), (y0, y1) = L.PLATE["x"], L.PLATE["y"]
    brushed(reg, *at(x0, y1), *at(x1, y0))
    reg.rect_(*at(x0, y0 + 9.0), *at(x1, y0), (14, 14, 16))
    reg.rect_(*at(x0, y1), *at(x1, y0), None, outline=(60, 60, 64), width=0.6)
    reg.text("INSERT CARTRIDGE HERE", "times.ttf", 3.4, *at((x0 + x1) / 2 + 10.0, y1 - 5.0), (30, 30, 32))
    reg.text("ON", "times.ttf", 3.2, *at(x0 + 6.0, y1 - 12.0), (30, 30, 32))
    reg.text("OFF", "times.ttf", 3.2, *at(x0 + 7.0, y0 + 4.5), RED)
    reg.text("RESET", "times.ttf", 3.2, *at(x1 - 9.0, y0 + 4.5), RED)
    (x0, x1), (y0, y1) = L.SWITCH["x"], L.SWITCH["y"]
    reg.rect_(*at(x0 - 3.0, y1 + 3.0), *at(x1 + 3.0, y0 - 3.0), shade(CASE, -0.4))
    return reg


def front():
    reg = Region(L.REGIONS["front"], L.WIDTH, L.HEIGHT, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z
    (z0, z1) = L.BAND["z"]
    brushed(reg, *at(-170.0, z1), *at(170.0, z0))
    reg.rect_(*at(-170.0, z1), *at(170.0, z0), None, outline=(60, 60, 64), width=0.4)
    rainbow_text(reg, "COLECO", *at(-164.0, z0 + 6.0), 8.0)
    rainbow_text(reg, "VISION", *at(-116.0, z0 + 6.0), 8.0)
    reg.text("VIDEO GAME SYSTEM", "times.ttf", 4.0, *at(-60.0, z0 + 4.0), (24, 24, 26), anchor="lm")
    (e0, e1) = L.EXPANSION["x"]
    reg.text("EXPANSION MODULE INTERFACE", "times.ttf", 3.2, *at((e0 + e1) / 2, z1 - 4.0), (24, 24, 26))
    reg.rect_(*at(152.0, z0 + 8.0), *at(168.0, z0 + 3.0), (20, 20, 22), r=0.6)
    reg.rect_(*at(152.6, z0 + 7.4), *at(167.4, z0 + 3.6), None, outline=SILVER, width=0.25)
    reg.text("COLECO", "arialbd.ttf", 2.8, *at(160.0, z0 + 5.5), SILVER)
    return reg


def pad():
    p = L.PAD
    length, width = p["length"], p["width"]
    reg = Region(L.REGIONS["pad"], length, width, CASE)

    def at(x, y):
        return x + length / 2, width / 2 - y
    kx = p["knob"][0]
    reg.circle(*at(kx, 0.0), p["knob"][1] + 5.0, shade(CASE, -0.3))
    for k in range(8):                                        # the collar's notches
        a = 2 * math.pi * k / 8
        reg.circle(*at(kx + (p["knob"][1] + 3.0) * math.cos(a), (p["knob"][1] + 3.0) * math.sin(a)), 0.8,
                   shade(CASE, 0.15))
    # COLECO, embossed, running along the controller between the knob and the keys.
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(4.6 * reg.sx)))
    tile = Image.new("RGBA", (round(24 * reg.sx), round(7 * reg.sx)), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((tile.width / 2, tile.height / 2), "COLECO", font=f, fill=shade(CASE, 0.2) + (255,),
                              anchor="mm")
    tile = tile.rotate(90, expand=True)
    cx, cy = reg.p(*at(-16.0, 0.0))
    layer.paste(tile, (round(cx - tile.width / 2), round(cy - tile.height / 2)))
    reg.over(layer)
    pitch_across, pitch_along, w, h = p["keys"]
    for row in range(4):
        for col in range(3):
            x = p["first_row"] + row * pitch_along
            y = (col - 1) * pitch_across                         # col 0 at the bottom: 1, 4, 7, *
            name = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"][row * 3 + col]
            dark = name in "*#"
            fill = (24, 24, 26) if dark else KEY
            reg.rect_(*at(x - h / 2, y + w / 2), *at(x + h / 2, y - w / 2), fill, r=1.6)
            tile = Image.new("RGBA", (round(14 * reg.sx), round(14 * reg.sx)), (0, 0, 0, 0))
            ft = ImageFont.truetype(FONTS + ("arialbd.ttf" if dark else "times.ttf"), max(1, round(8.0 * reg.sx)))
            ImageDraw.Draw(tile).text((tile.width / 2, tile.height / 2), name, font=ft,
                                      fill=((240, 240, 240) if dark else (20, 20, 22)) + (255,), anchor="mm")
            tile = tile.rotate(90)                              # upright with the knob at the top
            px, py = reg.p(*at(x, y))
            reg.img.alpha_composite(tile, (round(px - tile.width / 2), round(py - tile.height / 2)))
    return reg


def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (14, 14, 16))
    reg.rect_(1.5, 1.5, lw - 1.5, lh - 1.5, None, r=4.0, outline=(236, 236, 236), width=0.6)
    reg.text("COLECO", "ariblk.ttf", 6.0, lw / 2, 9.0, (236, 236, 236))
    reg.text("VISION", "ariblk.ttf", 6.0, lw / 2, 15.0, (236, 236, 236))
    reg.text("PRESENTS", "arialbd.ttf", 2.8, lw / 2, 20.5, (236, 236, 236))
    art = space((560, 300))
    d = ImageDraw.Draw(art)
    ship(d, 180, 170, 2.8, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(5.0, 24.0, lw - 5.0, lh - 12.0)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(9.0 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(lw / 2, 32.0), "ODYSSEY", font=f, fill=(226, 52, 52, 255), anchor="mm",
                               stroke_width=max(1, round(0.6 * reg.sx)), stroke_fill=(60, 200, 230, 255))
    reg.over(layer)
    reg.text("A Space Trip for One or Two Players", "arial.ttf", 2.4, lw / 2, lh - 7.0, (236, 236, 236))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), label()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("dark", rgb(L.COLOURS["dark"])), ("silver", SILVER), ("key", KEY),
                         ("grey", rgb(L.COLOURS["grey"])), ("aluminium", (200, 202, 206)), ("red", RED)):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "colecovision_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
