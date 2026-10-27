"""The Game.com card's printing and screens (gamecom_print.png, gamecom_media.png), for the console theme's Game.com
model (gamecom.py).

`gamecom_print.png`, laid out as gamecom_layout.REGIONS says, each region in millimetres as the model's UVs map it: the
face (the silver panel over the charcoal band, game.com with its ringed planet, TIGER, ON/OFF, MENU SOUND PAUSE, the
letters on A B C D, the D-pad's dimple, the LCD's floor), a cartridge's label (a made-up game from tools/made-up-games:
its painting and logo) and swatches. `gamecom_media.png`: the screens at 200 x 160 in the LCD's four greys, the touch
screen's 12 x 10 grid faint over each: the start-up screen, the menu, the made-up game's title and two moments of it.
Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow,
numpy, scipy):

    python tools/console-models/gamecom_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamecom_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}


def gamecom(reg, x, y, size, ink):
    """game.com: the dot a ringed planet."""
    reg.text("game", "segoeuib.ttf", size, x - size * 0.1, y, ink, anchor="rm")
    reg.circle(x + size * 0.12, y + size * 0.05, size * 0.16, ink)
    reg.line([(x - size * 0.2, y + size * 0.22), (x + size * 0.45, y - size * 0.12)], ink, size * 0.05)
    reg.text("com", "segoeuib.ttf", size, x + size * 0.35, y, ink, anchor="lm")
    reg.text("™", "arial.ttf", size * 0.3, x + size * 2.3, y - size * 0.4, ink)


def tiger(reg, x, y, size, ink):
    reg.text("TIGER", "ariblk.ttf", size, x, y, ink, anchor="rm")
    reg.line([(x + 0.3, y + size * 0.3), (x + size * 1.3, y + size * 0.3), (x + size * 1.5, y - size * 0.2)], ink,
             size * 0.12)
    reg.text("®", "arial.ttf", size * 0.5, x + size * 2.0, y, ink)


def face():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["silver"])

    def at(x, z):
        return x - x0, z1 - z

    reg.poly([at(x0, z0)] + [at(x, z) for x, z in L.BAND_TOP] + [at(x1, z0)], C["band"])
    reg.line([at(x, z) for x, z in L.BAND_TOP], shade(C["band"], -0.3), 0.5)
    gamecom(reg, *at(*L.LOGOS["gamecom"]), 6.2, C["ink"])
    tiger(reg, *at(L.LOGOS["tiger"][0] + 4.0, L.LOGOS["tiger"][1]), 2.6, C["ink"])
    fw, fh = L.BEZEL["floor"]
    cx, cz = L.SCREEN["at"]
    reg.rect_(*at(cx - fw / 2, cz + fh / 2), *at(cx + fw / 2, cz - fh / 2), C["lcd"])
    reg.text("ON/OFF", "arial.ttf", 2.6, *at(L.POWER["at"][0] + 6.0, L.POWER["at"][1]), C["ink"], anchor="lm")
    for name in ("menu", "sound", "pause"):
        x, z = L.STRIP[name]
        reg.text(name.upper(), "arial.ttf", 2.0, *at(x, z + 3.6), C["ink"])
    for name in ("a", "b", "c", "d"):
        x, z = L.BUTTONS[name]
        reg.circle(*at(x, z), L.BUTTONS["r"] + 0.5, C["button"])
        reg.text(name.upper(), "arialbd.ttf", 3.6, *at(x, z), shade(C["button"], 0.5))
    x, z = L.DPAD["at"]
    reg.circle(*at(x, z), L.DPAD["arm"] + 0.5, C["button"])
    reg.circle(*at(x, z), 1.6, shade(C["button"], -0.3))
    sx0, sx1 = L.STYLUS["x"]
    reg.rect_(*at(-16.0, L.STYLUS["z"] + 3.6), *at(2.0, L.STYLUS["z"] - 3.6), C["stylus"])
    tiger(reg, *at(14.0, L.STYLUS["z"]), 2.2, (220, 220, 220))
    for k in range(3):
        reg.circle(*at(-11.0 + 2.6 * k, L.STYLUS["z"]), 0.35, (120, 120, 124))
    return reg


def label(game):
    length, _, w = L.CART["size"]
    reg = Region(L.REGIONS["label"], w, length, C["cart"])
    reg.rect_(3.0, 3.0, w - 3.0, length - 8.0, (236, 236, 232), r=2.0)
    a, b, c, d = reg.box(4.0, 4.0, w - 4.0, length - 9.0)
    reg.img.paste(ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.4)),
                  (round(a), round(b)))
    k = min((c - a) * 0.86 / game.logo.width, (d - b) * 0.34 / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(logo, (round((a + c - logo.width) / 2), round(b + 1.5 * reg.sy)))
    gamecom(reg, w / 2 - 2.0, length - 4.0, 3.0, (230, 230, 230))
    return reg


def grid(img):
    """The touch screen's grid, faint over a screen."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    cols, rows = L.SCREEN["grid"]
    for i in range(1, cols):
        for j in range(1, rows):
            d.point((round(w * i / cols), round(h * j / rows)), fill=rgb(L.PALETTE[1]))
    return img


def screens(game):
    size = L.SCREEN["pixels"]
    ink, paper = rgb(L.PALETTE[0]), rgb(L.PALETTE[-1])
    boot = Image.new("RGB", size, paper)
    S.chars(boot, 4.5, 6, "game.com", ink, 2)
    S.chars(boot, 10, 13, "TIGER", rgb(L.PALETTE[1]))
    menu = Image.new("RGB", size, paper)
    d = ImageDraw.Draw(menu)
    for k, name in enumerate(L.MENU):
        cx, cy = 34 + 66 * (k % 3), 40 + 72 * (k // 3)
        d.rectangle([cx - 20, cy - 22, cx + 20, cy + 14], outline=ink, width=2,
                    fill=rgb(L.PALETTE[1]) if k == 0 else None)
        d.rectangle([cx - 10, cy - 12, cx + 10, cy + 4], fill=ink if k == 0 else rgb(L.PALETTE[2]))
        S.chars(menu, (cx - 4 * len(name)) / 8, (cy + 18) / 8, name, ink)
    title = S.title(game, size, palette=L.PALETTE, prompt="TOUCH TO START", ink=paper)
    game1, game2 = S.play(game, size, palette=L.PALETTE)
    return {name: grid(img) for name, img in dict(boot=boot, menu=menu, title=title, game1=game1, game2=game2).items()}


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["silver"])
    for reg in (face(), label(game)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "gamecom_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.PALETTE[-1]))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.convert("RGB").resize((w, h), Image.NEAREST), (x, y))
    media.save(os.path.join(out, "gamecom_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
