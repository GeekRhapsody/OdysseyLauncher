"""The Game Master card's printing and screens (gmaster_print.png, gmaster_media.png), for the console theme's Game
Master model (gmaster.py).

`gmaster_print.png`, laid out as gmaster_layout.REGIONS says, each region in millimetres as the model's UVs map it: the
face (the black band, the silver surround with its orange line and GAME MASTER, the LCD's window; START, SELECT, A and B
in white; the mould seams; the D-pad's arrows), the cartridge's label (a made-up game from tools/made-up-games: its
painting and logo) and swatches. `gmaster_media.png`: the screens at the LCD's 64 x 64 dots, dark on its pale
grey-green: the start-up screen, the made-up game's title and two moments of it. Make the made-up games' library first
(tools/made-up-games/README.md), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/gmaster_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gmaster_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
WHITE = (238, 240, 240)


def face():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["body"])

    def at(x, z):
        return x - x0, z1 - z

    for seam in L.SEAMS:
        reg.line([at(x, z) for x, z in seam], shade(C["body"], -0.3), 0.4)
    reg.poly([at(x, z) for x, z in L.BAND["outline"]], C["band"])
    sx0, sx1, sz0, sz1 = L.SURROUND["rect"]
    reg.rect_(*at(sx0, sz1), *at(sx1, sz0), C["surround"], r=L.SURROUND["r"])
    lx0, lx1, lz0, lz1 = L.LINE["rect"]
    for d, colour in ((0.0, C["orange"]), (1.2, (40, 40, 40))):
        reg.line([at(-20.0, lz0 + d), at(lx0 + d, lz0 + d), at(lx0 + d, lz1 - d), at(lx1 - d, lz1 - d),
                  at(lx1 - d, lz0 + d), at(22.0, lz0 + d)], colour, 0.5 if d == 0.0 else 0.25)
    reg.text("GAME MASTER", "ariblk.ttf", 4.6, *at(1.0, lz0 - 0.4), C["orange"])
    (w, h), (cx, cz) = L.SCREEN["size"], L.SCREEN["at"]
    reg.rect_(*at(cx - w / 2, cz + h / 2), *at(cx + w / 2, cz - h / 2), C["lcd"])
    for name in ("start", "select"):
        x, z = L.BUTTONS[name]
        reg.text(name.upper(), "arialbd.ttf", 2.4, *at(x, z + 5.6), WHITE)
    reg.text("A", "arialbd.ttf", 2.4, *at(L.BUTTONS["a"][0] - 7.5, L.BUTTONS["a"][1] + 7.5), WHITE)
    reg.text("B", "arialbd.ttf", 2.4, *at(L.BUTTONS["b"][0] - 7.0, L.BUTTONS["b"][1] + 7.5), WHITE)
    x, z = L.DPAD["at"]                                    # the arrows moulded on the D-pad's arms
    arm = shade(C["button"], -0.12)
    reg.rect_(*at(x - L.DPAD["half"], z + L.DPAD["arm"]), *at(x + L.DPAD["half"], z - L.DPAD["arm"]), C["button"])
    reg.rect_(*at(x - L.DPAD["arm"], z + L.DPAD["half"]), *at(x + L.DPAD["arm"], z - L.DPAD["half"]), C["button"])
    for mark, dx, dz in (("⇧", 0.0, 7.0), ("⇩", 0.0, -7.0), ("⇦", -7.0, 0.0), ("⇨", 7.0, 0.0)):
        reg.text(mark, "seguisym.ttf", 3.6, *at(x + dx, z + dz), arm)
    reg.circle(*at(x, z), 1.8, shade(C["button"], -0.06))
    return reg


def label(game):
    w, _, h = L.CART["size"]
    reg = Region(L.REGIONS["label"], w, h, C["cart"])
    for k in range(4):                                     # the ribs along its top
        reg.rect_(8.0, 1.0 + 1.3 * k, w - 8.0, 1.6 + 1.3 * k, shade(C["cart"], -0.25))
    reg.rect_(3.0, 7.0, w - 3.0, h - 3.0, (16, 16, 18), r=1.5)
    a, b, c, d = reg.box(4.0, 8.0, w - 4.0, h - 4.0)
    reg.img.paste(ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.4)),
                  (round(a), round(b)))
    k = min((c - a) * 0.86 / game.logo.width, (d - b) * 0.36 / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(logo, (round((a + c - logo.width) / 2), round(b + 1.5 * reg.sy)))
    return reg


def screens(game):
    size = L.SCREEN["pixels"]
    ink, paper = rgb(L.PALETTE[0]), rgb(L.PALETTE[-1])
    boot = Image.new("RGB", size, paper)
    d = ImageDraw.Draw(boot)
    S.chars(boot, 2, 2.5, "GAME", ink)
    S.chars(boot, 1, 4, "MASTER", ink)
    d.rectangle([4, 44, 59, 46], fill=ink)
    title = S.title(game, size, palette=L.PALETTE, prompt="", ink=paper)
    game1, game2 = S.play(game, size, palette=L.PALETTE)
    return dict(boot=boot, title=title, game1=game1, game2=game2)


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["body"])
    for reg in (face(), label(game)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "gmaster_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.PALETTE[-1]))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.convert("RGB").resize((w, h), Image.NEAREST), (x, y))
    media.save(os.path.join(out, "gmaster_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
