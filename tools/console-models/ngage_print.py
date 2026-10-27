"""The N-Gage card's printing and screens (ngage_print.png, ngage_media.png), for the console theme's N-Gage model
(ngage.py).

`ngage_print.png`, laid out as ngage_layout.REGIONS says, each region in millimetres as the model's UVs map it: the face
(the charcoal frame, the silver panel's dimples, the D-pad's shield and its brushed disc with its arrows, the black U of
the bezel with NOKIA and N-GAGE, the LCD's window, every key's silver top and its legend, 5 and 7 ringed in bronze), the
back (its cover's raised pad, NOKIA moulded in it) and swatches. `ngage_media.png`: the screens at 176 x 208 in 4,096
colours: NOKIA's start-up, the games menu, a made-up game's title and two moments of it (tools/made-up-games). Make the
made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/ngage_print.py artifacts/made-up-games <out folder>
"""

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ngage_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
WHITE = (240, 240, 240)


def face():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["frame"])

    def at(x, z):
        return x - x0, z1 - z

    base = reg.img
    reg.img = Image.new("RGBA", base.size, C["panel"] + (255,))      # the panel and its dimples, light over dark
    reg.draw = ImageDraw.Draw(reg.img)
    for j in range(22):
        for i in range(30):
            x, z = -40.0 + 2.8 * i + 1.4 * (j % 2), 6.0 + 2.9 * j
            reg.circle(*at(x + 0.3, z - 0.3), 0.9, shade(C["panel"], -0.12))
            reg.circle(*at(x, z), 0.75, shade(C["panel"], 0.12))
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).polygon([reg.p(*at(x, z)) for x, z in L.PANEL], fill=255)
    base.paste(reg.img, (0, 0), mask)
    reg.img, reg.draw = base, ImageDraw.Draw(base)
    reg.poly([at(x, z) for x, z in L.DPAD["shield"]], C["shield"])
    reg.poly([at(x, z) for x, z in L.bezel_outline()], C["bezel"])
    (sw, sh), (sx, sz) = L.SCREEN["size"], L.SCREEN["at"]
    reg.rect_(*at(sx - sw / 2 - 1.0, sz + sh / 2 + 1.0), *at(sx + sw / 2 + 1.0, sz - sh / 2 - 1.0), C["lcd"])
    reg.text("NOKIA", "arialbd.ttf", 3.6, *at(0.0, 66.4), WHITE)
    reg.text("N", "arialbd.ttf", 3.8, *at(-9.0, 19.6), C["nred"])
    reg.text("·GAGE", "arialbd.ttf", 3.8, *at(2.0, 19.6), WHITE)
    x, z = L.DPAD["at"]                                    # the disc: brushed, its arrows, its dot
    for k in range(12, 0, -1):
        reg.circle(*at(x, z), L.DPAD["r"] * k / 12, shade(C["disc"], 0.05 if k % 2 else -0.04))
    for mark, dx, dz in (("▲", 0.0, 6.0), ("▼", 0.0, -6.0), ("◀", -6.0, 0.0), ("▶", 6.0, 0.0)):
        reg.text(mark, "seguisym.ttf", 1.8, *at(x + dx, z + dz), (128, 90, 48))
    reg.circle(*at(x, z), 0.6, (128, 90, 48))
    for name, kx, kz, w, h, turn, kind in L.KEYS:
        reg.poly([at(px, pz) for px, pz in L.turned_rect(kx, kz, w, h, turn)], C["key"])
        legend = L.LEGENDS.get(name, "")
        colour = {"call": C["call"], "end": C["end"], "game": C["bronze"]}.get(kind, C["ink"])
        if kind == "game":
            reg.circle(*at(kx, kz), 3.4, None, outline=C["bronze"], width=0.3)
        font = "seguisym.ttf" if not legend[:1].isalnum() else "arialbd.ttf"
        reg.text(legend, font, 3.0 if len(legend) <= 2 else 2.6, *at(kx, kz), colour)
    for x, z in ((50.1, 42.0), (50.6, 32.6)):              # the two small holes
        reg.circle(*at(x, z), 0.35, (20, 20, 22))
    return reg


def back():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["back"], x1 - x0, z1 - z0, C["back"])
    w, h = x1 - x0, z1 - z0
    reg.rect_(w / 2 - 38.0, h / 2 - 18.0, w / 2 + 38.0, h / 2 + 16.0, shade(C["back"], 0.06), r=8.0,
              outline=shade(C["back"], -0.2), width=0.4)
    reg.text("NOKIA", "arialbd.ttf", 6.0, w / 2, h / 2 - 2.0, shade(C["back"], -0.14))
    for side in (-1, 1):
        for k in range(5):
            for j in range(3):
                reg.circle(w / 2 + side * (30.0 - 2.0 * j), h / 2 - 10.0 + 4.0 * k, 0.5, shade(C["back"], 0.18))
    return reg


def colours12(img):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    levels = 2 ** L.PALETTE_BITS - 1
    return Image.fromarray((np.round(a / 255 * levels) * 255 / levels).astype(np.uint8))


def screens(game):
    size = L.SCREEN["pixels"]
    boot = Image.new("RGB", size, (8, 20, 70))
    d = ImageDraw.Draw(boot)
    for y in range(size[1]):
        d.line([(0, y), (size[0], y)], fill=(8, 20 + y // 6, 70 + y // 3))
    d.text((88, 96), "NOKIA", font=ImageFont.truetype(FONTS + "arialbd.ttf", 28), fill=(240, 240, 240), anchor="mm")
    menu = Image.new("RGB", size, (16, 24, 40))
    d = ImageDraw.Draw(menu)
    d.rectangle([0, 0, size[0], 22], fill=(150, 40, 30))
    d.text((8, 11), "Games", font=ImageFont.truetype(FONTS + "arialbd.ttf", 14), fill=WHITE, anchor="lm")
    f = ImageFont.truetype(FONTS + "arial.ttf", 11)
    for k, name in enumerate(L.GAMES):
        y = 34 + 26 * k
        if k == 0:
            d.rectangle([4, y - 2, size[0] - 4, y + 20], fill=(70, 110, 170))
        d.rectangle([10, y + 2, 24, y + 16], fill=(230, 140, 40) if k == 0 else (90, 100, 120))
        d.text((30, y + 9), name.title(), font=f, fill=WHITE, anchor="lm")
    d.rectangle([0, size[1] - 18, size[0], size[1]], fill=(30, 40, 60))
    d.text((8, size[1] - 9), "Options", font=f, fill=WHITE, anchor="lm")
    d.text((size[0] - 8, size[1] - 9), "Exit", font=f, fill=WHITE, anchor="rm")
    title = S.title(game, size, prompt="PRESS 5")
    game1, game2 = S.play(game, size)
    return {name: colours12(img) for name, img in dict(boot=boot, menu=menu, title=title, game1=game1,
                                                       game2=game2).items()}


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["frame"])
    for reg in (face(), back()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "ngage_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.resize((w, h), Image.NEAREST), (x, y))
    media.save(os.path.join(out, "ngage_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
