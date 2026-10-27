"""The Gamate card's printing and screens (gamate_print.png, gamate_media.png), for the console theme's Gamate model
(gamate.py).

`gamate_print.png`, laid out as gamate_layout.REGIONS says, each region in millimetres as the model's UVs map it: the
face (the black bezel, its red frame line broken by DOT MATRIX LCD and GAMATE®, the LCD's olive window; SELECT, START, A
and B moulded; the D-pad's cross and arrows embossed on its disc), the card's label (a made-up game from
tools/made-up-games: its painting and logo over the blue band with GAMATE CARD) and swatches. `gamate_media.png`: the
screens at the LCD's 160 x 152 in its four shades: the start-up screen, the made-up game's title and two moments of it.
Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow,
numpy, scipy):

    python tools/console-models/gamate_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamate_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}


def face():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["body"])

    def at(x, z):
        return x - x0, z1 - z

    bx0, bx1, bz0, bz1 = L.BEZEL["rect"]
    reg.rect_(*at(bx0, bz1), *at(bx1, bz0), C["bezel"], r=L.BEZEL["r"])
    fx0, fx1, fz0, fz1 = L.FRAME["rect"]
    red = (180, 39, 18)
    reg.line([at(-14.0, fz1), at(fx0, fz1), at(fx0, fz0), at(-17.0, fz0)], red, 0.5)
    reg.line([at(14.0, fz1), at(fx1, fz1), at(fx1, fz0), at(17.0, fz0)], red, 0.5)
    reg.text("DOT MATRIX LCD", "arialbd.ttf", 2.8, *at(0.0, fz1), (170, 210, 120))
    reg.text("GAMATE", "timesbd.ttf", 5.2, *at(-1.0, fz0), C["yellow"])
    reg.text("®", "arial.ttf", 1.8, *at(16.0, fz0 - 1.0), C["yellow"])
    (sw, sh), (sx, sz) = L.SCREEN["size"], L.SCREEN["at"]
    reg.rect_(*at(sx - sw / 2, sz + sh / 2), *at(sx + sw / 2, sz - sh / 2), C["olive"])
    moulded = shade(C["body"], 0.18)
    for name in ("select", "start"):
        x, z = L.PILLS[name]
        reg.text(name.upper(), "arial.ttf", 2.4, *at(x, z + 6.5), moulded)
    for name, (dx, dz) in (("a", (-5.4, 7.2)), ("b", (-4.8, 6.9))):
        x, z = L.BUTTONS[name]
        reg.text(name.upper(), "arial.ttf", 2.6, *at(x + dx, z + dz), moulded)
    x, z = L.DPAD["at"]                                    # the disc's embossed cross and arrows
    dark = shade(C["yellow"], -0.18)
    reg.circle(*at(x, z), L.DPAD["r"] + 0.5, C["yellow"])
    reg.rect_(*at(x - 3.4, z + 10.0), *at(x + 3.4, z - 10.0), dark, r=1.0)
    reg.rect_(*at(x - 10.0, z + 3.4), *at(x + 10.0, z - 3.4), dark, r=1.0)
    reg.rect_(*at(x - 2.6, z + 9.2), *at(x + 2.6, z - 9.2), C["yellow"], r=0.8)
    reg.rect_(*at(x - 9.2, z + 2.6), *at(x + 9.2, z - 2.6), C["yellow"], r=0.8)
    for mark, dx, dz in (("▲", 0.0, 6.6), ("▼", 0.0, -6.6), ("◀", -6.6, 0.0), ("▶", 6.6, 0.0)):
        reg.text(mark, "seguisym.ttf", 2.4, *at(x + dx, z + dz), dark)
    return reg


def label(game):
    w, _, h = L.CARD["size"]
    reg = Region(L.REGIONS["label"], w, h, C["card"])
    reg.rect_(3.0, 3.0, w - 3.0, 64.0, (240, 240, 236), r=2.0)
    a, b, c, d = reg.box(4.0, 4.0, w - 4.0, 63.0)
    reg.img.paste(ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.4)),
                  (round(a), round(b)))
    k = min((c - a) * 0.86 / game.logo.width, (d - b) * 0.3 / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(logo, (round((a + c - logo.width) / 2), round(b + 2.0 * reg.sy)))
    reg.rect_(3.0, 66.0, w - 3.0, 74.0, (30, 70, 170), r=1.0)
    reg.text("GAMATE CARD  C1-104", "arialbd.ttf", 3.0, w / 2, 70.0, (240, 240, 240))
    for k in range(10):                                    # the contacts, at the end that goes in first
        reg.rect_(4.0 + 4.8 * k, h - 7.0, 6.6 + 4.8 * k, h - 1.0, (196, 160, 70))
    return reg


def screens(game):
    size = L.SCREEN["pixels"]
    ink, paper = rgb(L.PALETTE[0]), rgb(L.PALETTE[-1])
    boot = Image.new("RGB", size, paper)
    S.chars(boot, 7, 7, "GAMATE", ink, 1)
    ImageDraw.Draw(boot).line([(52, 72), (108, 72)], fill=rgb(L.PALETTE[1]), width=2)
    S.chars(boot, 2.5, 12, "BIT CORPORATION", rgb(L.PALETTE[1]))
    title = S.title(game, size, palette=L.PALETTE, prompt="PRESS START", ink=paper)
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
    image.save(os.path.join(out, "gamate_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.PALETTE[-1]))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.convert("RGB").resize((w, h), Image.NEAREST), (x, y))
    media.save(os.path.join(out, "gamate_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
