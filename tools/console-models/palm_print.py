"""The Palm OS card's printing and screens (palm_print.png, palm_media.png), for the console theme's Palm OS model
(palm.py).

`palm_print.png`, laid out as palm_layout.REGIONS says, each region in millimetres as the model's UVs map it: the face
(Palm Pilot and U.S.Robotics; the window's LCD and its silkscreened Graffiti area with its four icons and the writing
box, abc and 123; the buttons' icons; the power key's sun; the lip) and swatches. `palm_media.png`: the screens at the
LCD's 160 x 160 in four greys: the application launcher (a made-up game among the applications), the game's title and
two moments of it (tools/made-up-games). Make the made-up games' library first (tools/made-up-games/README.md), then
run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/palm_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palm_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}


def face():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["body"])

    def at(x, z):
        return x - x0, z1 - z

    lip = [(x, L.LIP["middle"] + (L.LIP["ends"] - L.LIP["middle"]) * (x / L.HALF) ** 2)
           for x in [x0 + (x1 - x0) * k / 30 for k in range(31)]]
    reg.poly([at(x0, z0)] + [at(x, z) for x, z in lip] + [at(x1, z0)], C["lip"])
    reg.text("Palm Pilot", "arialbi.ttf", 3.6, *at(-22.0, 112.0), C["white"])
    reg.text("U.S.Robotics", "arialbd.ttf", 2.6, *at(20.0, 112.0), C["white"])
    wx0, wx1, wz0, wz1 = L.WINDOW["rect"]
    reg.rect_(*at(wx0, wz1), *at(wx1, wz0), C["silk"], r=L.WINDOW["r"])
    (lw, lh), (lx, lz) = L.WINDOW["lcd"], L.WINDOW["lcd_at"]
    reg.rect_(*at(lx - lw / 2, lz + lh / 2), *at(lx + lw / 2, lz - lh / 2), C["lcd"])
    ink = C["ink"]
    for x, z, mark in ((-24.0, 47.0, "⌂"), (-24.0, 37.0, "☰"), (24.0, 47.0, "⊞"), (24.0, 37.0, "⌕")):
        reg.circle(*at(x, z), 3.4, None, outline=ink, width=0.3)
        reg.text(mark, "seguisym.ttf", 3.0, *at(x, z), ink)
    reg.rect_(*at(-18.0, 49.5), *at(18.0, 34.5), None, outline=ink, width=0.35)
    reg.line([at(4.0, 49.5), at(4.0, 47.5)], ink, 0.35)
    reg.line([at(4.0, 34.5), at(4.0, 36.5)], ink, 0.35)
    reg.text("abc", "arial.ttf", 1.8, *at(-15.0, 36.0), ink)
    reg.text("123", "arial.ttf", 1.8, *at(15.0, 36.0), ink)
    z = L.BUTTONS["z"]
    for x, name in L.BUTTONS["apps"]:
        reg.circle(*at(x, z), L.BUTTONS["r"] + 0.4, C["button"])
        mark = {"date": "◷", "address": "☎", "todo": "☑", "memo": "✎"}[name]
        reg.text(mark, "seguisym.ttf", 3.6, *at(x, z), C["white"])
    px, pz = L.POWER["at"]
    reg.text("☀", "seguisym.ttf", 2.6, *at(px + 3.6, pz), C["white"])
    return reg


def launcher():
    size = (160, 160)
    ink, paper = rgb(L.PALETTE[0]), rgb(L.PALETTE[-1])
    img = Image.new("RGB", size, paper)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 160, 13], fill=ink)
    f = ImageFont.truetype(FONTS + "arialbd.ttf", 10)
    d.text((4, 7), "Applications", font=f, fill=paper, anchor="lm")
    small = ImageFont.truetype(FONTS + "arial.ttf", 8)
    for k, name in enumerate(L.APPS):
        cx, cy = 20 + 40 * (k % 4), 30 + 44 * (k // 4)
        d.rectangle([cx - 9, cy - 9, cx + 9, cy + 9], outline=ink, width=2, fill=rgb(L.PALETTE[1]) if k == 0 else None)
        d.rectangle([cx - 4, cy - 4, cx + 4, cy + 4], fill=ink if k == 0 else rgb(L.PALETTE[2]))
        d.text((cx, cy + 16), name, font=small, fill=ink, anchor="mm")
    return img


def screens(game):
    size = (160, 160)
    title = S.title(game, size, palette=L.PALETTE, prompt="TAP TO START", ink=rgb(L.PALETTE[-1]))
    game1, game2 = S.play(game, size, palette=L.PALETTE)
    return dict(launcher=launcher(), title=title, game1=game1, game2=game2)


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["body"])
    face().paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "palm_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.PALETTE[-1]))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.convert("RGB").resize((w, h), Image.NEAREST), (x, y))
    media.save(os.path.join(out, "palm_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
