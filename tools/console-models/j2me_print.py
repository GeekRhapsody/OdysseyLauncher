"""The J2ME card's printing and screens (j2me_print.png, j2me_media.png), for the console theme's J2ME model (j2me.py).

`j2me_print.png`, laid out as j2me_layout.REGIONS says, each region in millimetres as the model's UVs map it: the face
(the dark shell's sides, the silver plate, the earpiece's slot, the screen's black window, the middle column's inset
panel and its bright outline, every key's silver top, its digit and letters or its mark: the soft keys' blue corners,
call's green and end's red, the navi key's blue dot) and swatches. `j2me_media.png`: the screens at 128 x 128: the idle
screen, the menu's grid, the games list with a made-up game (tools/made-up-games), its title and two moments of it.
Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow,
numpy, scipy):

    python tools/console-models/j2me_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import j2me_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
WHITE = (250, 250, 250)


def mark(reg, at, kind, x, z):
    """A key's mark: the soft keys' corner, call's and end's handset corners, the navi key's dot."""
    if kind == "navi":
        reg.circle(*at(x, z), 0.6, C["blue"])
        return
    colour = {"soft": C["blue"], "call": C["green"], "end": C["red"]}[kind]
    left = x < 0
    if kind == "soft":
        reg.line([at(x + (1.2 if left else -1.2), z + 1.0), at(x + (-1.2 if left else 1.2), z + 1.0),
                  at(x + (-1.2 if left else 1.2), z - 0.6)], colour, 0.45)
    else:
        reg.line([at(x + (-1.2 if left else 1.2), z + 1.0), at(x + (-1.2 if left else 1.2), z - 0.8),
                  at(x + (1.2 if left else -1.2), z - 0.8)], colour, 0.45)


def face():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["shell"])

    def at(x, z):
        return x - x0, z1 - z

    p = L.PLATE
    reg.rect_(*at(-p["x"], p["z"][1]), *at(p["x"], p["z"][0]), C["plate"], r=p["top"])
    reg.rect_(*at(-p["x"], (p["z"][0] + p["z"][1]) / 2), *at(p["x"], p["z"][0]), C["plate"], r=p["bottom"])
    sx, sz = L.BADGE["slot"]
    reg.rect_(*at(sx - 5.0, sz + 0.6), *at(sx + 5.0, sz - 0.6), (20, 20, 20), r=0.6)
    (ww, wh), (wx, wz) = L.WINDOW["size"], L.WINDOW["at"]
    reg.rect_(*at(wx - ww / 2, wz + wh / 2), *at(wx + ww / 2, wz - wh / 2), C["window"], r=1.0)
    cx, (cz0, cz1) = L.COLUMN["x"], L.COLUMN["z"]
    reg.rect_(*at(-cx, cz1), *at(cx, cz0), shade(C["plate"], -0.15), r=2.4, outline=C["line"], width=0.35)
    for name, x, z, w, h, legend, kind in L.KEYS:
        reg.rect_(*at(x - w / 2, z + h / 2), *at(x + w / 2, z - h / 2), C["key"], r=1.0)
        if kind != "key":
            mark(reg, at, kind, x, z)
            continue
        digit, letters = legend.split("\n")
        reg.text(digit, "arialbd.ttf", 2.2, *at(x, z + 0.8), C["ink"])
        reg.text(letters, "seguisym.ttf" if letters == "⇧" else "arial.ttf", 1.5, *at(x, z - 1.2), C["ink"])
    reg.circle(*at(0.0, 7.0), 0.4, (14, 14, 14))
    return reg


def colours16(img):
    a = np.asarray(img.convert("RGB")).astype(np.int32)
    a[..., 0] = (a[..., 0] >> 3) << 3
    a[..., 1] = (a[..., 1] >> 2) << 2
    a[..., 2] = (a[..., 2] >> 3) << 3
    return Image.fromarray(a.astype(np.uint8))


def bars(d, w):
    for k in range(4):
        d.rectangle([4 + 3 * k, 12 - 2 * k, 5 + 3 * k, 13], fill=(30, 30, 40))
    d.rectangle([w - 14, 6, w - 4, 12], outline=(30, 30, 40))
    d.rectangle([w - 12, 8, w - 6, 10], fill=(30, 30, 40))


def softkeys(d, w, h, left, right):
    f = ImageFont.truetype(FONTS + "arialbd.ttf", 10)
    d.rectangle([0, h - 15, w, h], fill=(220, 228, 240))
    d.text((4, h - 7), left, font=f, fill=(20, 30, 60), anchor="lm")
    d.text((w - 4, h - 7), right, font=f, fill=(20, 30, 60), anchor="rm")


def screens(game):
    w, h = L.SCREEN["pixels"]
    f = ImageFont.truetype(FONTS + "arial.ttf", 10)
    fb = ImageFont.truetype(FONTS + "arialbd.ttf", 11)
    idle = Image.new("RGB", (w, h), (180, 210, 240))
    d = ImageDraw.Draw(idle)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=(150 + y // 3, 190 + y // 6, 235))
    bars(d, w)
    d.text((w / 2, 40), "ODYSSEY", font=fb, fill=(20, 30, 60), anchor="mm")
    d.text((w / 2, 62), "10:24", font=ImageFont.truetype(FONTS + "arialbd.ttf", 22), fill=(20, 30, 60), anchor="mm")
    softkeys(d, w, h, "Menu", "Names")
    menu = Image.new("RGB", (w, h), (235, 240, 248))
    d = ImageDraw.Draw(menu)
    d.rectangle([0, 0, w, 15], fill=(40, 80, 160))
    d.text((4, 8), "Menu", font=fb, fill=WHITE, anchor="lm")
    d.text((w - 4, 8), "Games", font=f, fill=WHITE, anchor="rm")
    for k, name in enumerate(L.MENU):
        cx, cy = 22 + 42 * (k % 3), 32 + 30 * (k // 3)
        sel = name == "Games"
        if sel:
            d.rectangle([cx - 20, cy - 13, cx + 20, cy + 13], fill=(255, 210, 90))
        d.rounded_rectangle([cx - 8, cy - 10, cx + 8, cy + 4], radius=3,
                            fill=[(200, 60, 60), (60, 140, 200), (90, 170, 90)][k % 3])
    softkeys(d, w, h, "Select", "Exit")
    games = Image.new("RGB", (w, h), (235, 240, 248))
    d = ImageDraw.Draw(games)
    d.rectangle([0, 0, w, 15], fill=(40, 80, 160))
    d.text((4, 8), "Collection", font=fb, fill=WHITE, anchor="lm")
    for k, name in enumerate(["Top Corner '94", "Puck Rush", "Kaleidrop", "Baseline Heroes"]):
        y = 24 + 20 * k
        if k == 0:
            d.rectangle([2, y - 8, w - 2, y + 9], fill=(60, 110, 200))
        d.text((8, y), name, font=f, fill=WHITE if k == 0 else (20, 30, 60), anchor="lm")
    softkeys(d, w, h, "Open", "Back")
    title = S.title(game, (w, h), prompt="PRESS 5")
    game1, game2 = S.play(game, (w, h))
    return {name: colours16(img) for name, img in dict(idle=idle, menu=menu, games=games, title=title, game1=game1,
                                                       game2=game2).items()}


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["shell"])
    face().paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "j2me_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.resize((w, h), Image.NEAREST), (x, y))
    media.save(os.path.join(out, "j2me_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
