"""The Mega Duck card's printing and screens (megaduck_print.png, megaduck_media.png), for the console theme's Mega Duck
model (megaduck.py).

`megaduck_print.png`, laid out as megaduck_layout.REGIONS says, each region in millimetres as the model's UVs map it:
the face (the ridges, the slate bezel with its labels and the LCD's green window, B and A, SELECT and START, Mega Duck
lettered, PHONES), the back (the battery cover, its screws and arrow), the cartridge's label (a made-up game from
tools/made-up-games: its painting and logo) and swatches. `megaduck_media.png`: the screens at the LCD's 160 x 144 in its
four blues on green: the start-up screen, the made-up game's title and two moments of it. Make the made-up games'
library first (tools/made-up-games/README.md), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/megaduck_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import megaduck_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
WHITE = (240, 240, 240)
TURQ = (88, 200, 196)


def at_face(x, z):
    return x + L.WIDTH / 2, L.HEIGHT - z


def face():
    reg = Region(L.REGIONS["face"], L.WIDTH, L.HEIGHT, C["shell"])
    at = at_face
    for z in L.RIDGES:
        reg.line([at(-40.0, z), at(40.0, z)], shade(C["shell"], -0.12), 0.7)
        reg.line([at(-40.0, z - 0.7), at(40.0, z - 0.7)], shade(C["shell"], 0.05), 0.4)
    x0, x1, z0, z1 = L.BEZEL["rect"]
    reg.rect_(*at(x0, z1), *at(x1, z0), C["bezel"], r=L.BEZEL["r"])
    ww, wh = L.SCREEN["window"]
    sx, sz = L.SCREEN["at"]
    reg.rect_(*at(sx - ww / 2, sz + wh / 2), *at(sx + ww / 2, sz - wh / 2), C["lcd"])
    reg.text("◀OFF • ON▶", "seguisym.ttf", 2.0, *at(-24.0, 139.5), WHITE)
    reg.text("DC 6V", "arialbd.ttf", 1.8, *at(-30.0, 133.0), WHITE)
    reg.text("SUPER STEREO SOUND", "ariblk.ttf", 3.0, *at(4.0, 139.0), TURQ)
    reg.text("EXT.", "arialbd.ttf", 1.8, *at(30.0, 133.5), WHITE)
    reg.text("CONNECTOR", "arialbd.ttf", 1.6, *at(30.0, 131.0), WHITE)
    reg.text("CONTRAST", "arialbd.ttf", 1.7, *at(-30.0, 90.0), WHITE)
    reg.text("BATTERY", "arialbd.ttf", 1.7, *at(30.5, 106.5), WHITE)
    reg.circle(*at(*L.LIGHT["at"]), L.LIGHT["r"], (90, 20, 24))
    reg.text("VOL. ☽", "seguisym.ttf", 1.9, *at(30.0, 92.0), WHITE)
    reg.text("HIGH RESOLUTION DOT MATRIX LCD", "ariblk.ttf", 2.5, *at(0.0, 79.0), TURQ)
    for k in range(30):
        reg.circle(*at(-26.0 + 1.8 * k, 76.4), 0.3, (60, 110, 200))
    # The buttons' names, the lettering.
    for name in ("a", "b"):
        x, z = L.BUTTONS[name]
        reg.text(name.upper(), "ariblk.ttf", 3.0, *at(x, z - 10.0), C["slate"])
    for name in ("select", "start"):
        x, z = L.PILLS[name]
        reg.text(name.upper(), "ariblk.ttf", 2.2, *at(x, z - 5.2), C["slate"])
    reg.text("Mega", "segoepr.ttf", 9.0, *at(-27.0, 25.0), C["slate"])
    reg.text("Duck", "segoepr.ttf", 9.0, *at(-21.0, 14.0), C["slate"])
    reg.text("™", "arial.ttf", 2.2, *at(-14.0, 31.0), C["slate"])
    reg.text("PHONES", "arialbd.ttf", 1.8, *at(-16.0, 4.5), C["slate"])
    return reg


def back():
    reg = Region(L.REGIONS["back"], L.WIDTH, L.HEIGHT, C["shell"])

    def at(x, z):                                          # seen from behind: the device's right at the left
        return L.WIDTH / 2 - x, L.HEIGHT - z
    reg.rect_(*at(30.0, 92.0), *at(-30.0, 22.0), shade(C["shell"], -0.05), r=4.0, outline=shade(C["shell"], -0.2),
              width=0.5)
    reg.text("▼ OPEN", "seguisym.ttf", 3.0, *at(0.0, 86.0), shade(C["shell"], -0.3))
    reg.text("BATTERY 1.5V × 4 (AA)", "arialbd.ttf", 2.4, *at(0.0, 40.0), shade(C["shell"], -0.3))
    for x, z in ((40.0, 140.0), (-40.0, 140.0), (40.0, 98.0), (-40.0, 98.0), (40.0, 12.0), (-40.0, 12.0)):
        reg.circle(*at(x, z), 2.0, shade(C["shell"], -0.25))
        reg.circle(*at(x, z), 1.0, shade(C["shell"], -0.45))
    return reg


def label(game):
    w, _, h = L.CART["size"]
    reg = Region(L.REGIONS["label"], w, h, C["cart"])
    reg.rect_(3.0, 3.0, w - 3.0, h - 9.0, (240, 240, 236), r=2.0)
    a, b, c, d = reg.box(4.0, 4.0, w - 4.0, h - 10.0)
    reg.img.paste(ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.4)),
                  (round(a), round(b)))
    k = min((c - a) * 0.86 / game.logo.width, (d - b) * 0.32 / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(logo, (round((a + c - logo.width) / 2), round(b + 1.5 * reg.sy)))
    reg.text("MEGA DUCK", "ariblk.ttf", 3.0, w / 2, h - 5.0, WHITE)
    return reg


def screens(game):
    size = L.SCREEN["pixels"]
    ink, paper = rgb(L.PALETTE[0]), rgb(L.PALETTE[-1])
    boot = Image.new("RGB", size, paper)
    d = ImageDraw.Draw(boot)
    d.rectangle([36, 46, 124, 82], outline=ink, width=2)
    S.chars(boot, 5.5, 7.5, "MEGA DUCK", ink)
    S.chars(boot, 4, 13, "WELBACK 1993", rgb(L.PALETTE[1]))
    title = S.title(game, size, palette=L.PALETTE, prompt="PUSH START", ink=rgb(L.PALETTE[-1]))
    game1, game2 = S.play(game, size, palette=L.PALETTE)
    return dict(boot=boot, title=title, game1=game1, game2=game2)


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["shell"])
    for reg in (face(), back(), label(game)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "megaduck_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.PALETTE[-1]))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.convert("RGB").resize((w, h), Image.NEAREST), (x, y))
    media.save(os.path.join(out, "megaduck_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
