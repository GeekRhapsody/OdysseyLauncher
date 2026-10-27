"""The Symbian card's printing and screens (symbian_print.png, symbian_media.png), for the console theme's Symbian model
(symbian.py).

`symbian_print.png`, laid out as symbian_layout.REGIONS says, each region in millimetres as the model's UVs map it: the
face (silver: the earpiece, the front camera's ring, the screen's black window, the navi cluster: the chrome ring round
the five-way key, the menu and multimedia keys' icons, the soft keys' blue marks, call's green and end's red, edit and
C), the back half's front (the twelve silver keys, the media keys' black strip), the back (plum, the camera's ring) and
swatches. `symbian_media.png`: the screens at 240 x 320: the standby screen, the menu with a made-up game among its
icons, the game's title and two moments of it (tools/made-up-games). Unbranded. Make the made-up games' library first
(tools/made-up-games/README.md), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/symbian_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screens_print as S  # noqa: E402
import symbian_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}


def region(name, background):
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS[name], x1 - x0, z1 - z0, background)
    return reg, (lambda x, z: (x - x0, z1 - z))


def face():
    reg, at = region("face", C["silver"])
    reg.rect_(0.0, 0.0, L.WIDTH, L.HEIGHT, None, outline=C["plum"], width=1.6)
    (ex, ez), (ew, eh) = L.EARPIECE["at"], L.EARPIECE["size"]
    reg.rect_(*at(ex - ew / 2, ez + eh / 2), *at(ex + ew / 2, ez - eh / 2), (60, 60, 60), r=0.8)
    reg.circle(*at(*L.CAMERA["at"]), L.CAMERA["r"], C["chrome"])
    reg.circle(*at(*L.CAMERA["at"]), L.CAMERA["r"] - 1.0, (20, 20, 24))
    reg.circle(*at(L.CAMERA["at"][0] - 5.0, L.CAMERA["at"][1]), 0.5, (40, 40, 44))
    (ww, wh), (wx, wz) = L.WINDOW["size"], L.WINDOW["at"]
    reg.rect_(*at(wx - ww / 2, wz + wh / 2), *at(wx + ww / 2, wz - wh / 2), C["window"], r=1.5)
    (nx, nz), (nw, nh) = L.NAVI["at"], L.NAVI["size"]
    reg.rect_(*at(nx - nw / 2, nz + nh / 2), *at(nx + nw / 2, nz - nh / 2), C["chrome"], r=6.0)
    reg.rect_(*at(nx - nw / 2 + 0.8, nz + nh / 2 - 0.8), *at(nx + nw / 2 - 0.8, nz - nh / 2 + 0.8), C["key"], r=5.4)
    p = L.NAVI["pad"]
    reg.rect_(*at(nx - p / 2 - 0.8, nz + p / 2 + 0.8), *at(nx + p / 2 + 0.8, nz - p / 2 - 0.8), C["chrome"], r=3.0)
    reg.text("§", "seguisym.ttf", 3.6, *at(nx - 14.0, nz), C["blue"])
    reg.text("⌑", "seguisym.ttf", 3.6, *at(nx + 14.0, nz), C["ink"])
    for side, colour, dz in ((-1, C["blue"], 6.5), (1, C["blue"], 6.5), (-1, C["green"], -6.5), (1, C["red"], -6.5)):
        x, z = nx + side * 19.5, nz + dz
        reg.line([at(x - side * 1.2, z + 1.0), at(x, z + 1.0), at(x, z - 1.0)], colour, 0.4)
    reg.text("✎", "seguisym.ttf", 2.4, *at(nx - 7.0, nz - 7.2), C["ink"])
    reg.text("C", "arialbd.ttf", 2.2, *at(nx + 7.0, nz - 7.2), C["ink"])
    return reg


def keypad():
    reg, at = region("keypad", C["plum"])
    kw, kh = L.KEYPAD["key"]
    for row, z in zip(L.LEGENDS, L.KEYPAD["rows"]):
        for legend, x in zip(row, L.KEYPAD["cols"]):
            reg.rect_(*at(x - kw / 2, z + kh / 2), *at(x + kw / 2, z - kh / 2), C["key"], r=1.0)
            digit, _, letters = legend.partition(" ")
            reg.text(digit, "arialbd.ttf", 3.0, *at(x - 2.6, z), C["ink"])
            reg.text(letters, "seguisym.ttf" if letters == "⇧" else "arial.ttf", 1.7, *at(x + 2.6, z), C["ink"])
    z0, z1 = L.MEDIA_KEYS["z"]
    reg.rect_(*at(-L.WIDTH / 2 + 2.0, z1), *at(L.WIDTH / 2 - 2.0, z0), C["black"], r=2.0)
    for k, icon in enumerate(L.MEDIA_KEYS["icons"]):
        reg.text(icon, "seguisym.ttf", 3.6, *at(-18.0 + 12.0 * k, (z0 + z1) / 2), C["white"])
    return reg


def back():
    reg, _ = region("back", C["plum"])
    x, z = L.LENS["at"]
    cx, cz = L.WIDTH / 2 - x, L.HEIGHT - z                 # seen from behind
    reg.circle(cx, cz, L.LENS["r"] + 1.0, shade(C["plum"], -0.2))
    return reg


def font(size, bold=False):
    return ImageFont.truetype(FONTS + ("segoeuib.ttf" if bold else "segoeui.ttf"), size)


def chrome(img, left, right):
    """The status bar and the soft keys' bar."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    d.rectangle([0, 0, w, 18], fill=(30, 60, 120))
    for k in range(5):
        d.rectangle([4 + 4 * k, 14 - 2 * k, 6 + 4 * k, 15], fill=(240, 240, 240))
    d.text((w - 6, 9), "10:24", font=font(11, True), fill=(240, 240, 240), anchor="rm")
    d.rectangle([0, h - 20, w, h], fill=(30, 60, 120))
    d.text((6, h - 10), left, font=font(11, True), fill=(240, 240, 240), anchor="lm")
    d.text((w - 6, h - 10), right, font=font(11, True), fill=(240, 240, 240), anchor="rm")


def background(size):
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(size[1]):
        d.line([(0, y), (size[0], y)], fill=(200 - y // 4, 225 - y // 6, 250))
    return img


def screens(game):
    size = L.SCREEN["pixels"]
    w, h = size
    standby = background(size)
    d = ImageDraw.Draw(standby)
    d.text((12, 48), "10:24", font=font(40, True), fill=(20, 40, 90), anchor="lm")
    d.text((14, 80), "Tue 27.10.2026", font=font(12), fill=(20, 40, 90), anchor="lm")
    d.text((14, 100), "ODYSSEY", font=font(12, True), fill=(20, 40, 90), anchor="lm")
    for k in range(5):
        d.rounded_rectangle([12 + 44 * k, 130, 44 + 44 * k, 160], radius=6, fill=(60 + 30 * k, 120, 200 - 20 * k))
    chrome(standby, "Menu", "Contacts")
    menu = background(size)
    d = ImageDraw.Draw(menu)
    icon = ImageOps.fit(game.keyart, (52, 52), Image.LANCZOS)
    for k, name in enumerate(L.APPS):
        cx, cy = 40 + 80 * (k % 3), 50 + 64 * (k // 3)
        if name == "Halcyon":
            d.rectangle([cx - 36, cy - 30, cx + 36, cy + 32], fill=(255, 200, 80))
            menu.paste(icon, (cx - 26, cy - 26))
        else:
            d.rounded_rectangle([cx - 20, cy - 22, cx + 20, cy + 18], radius=6,
                                fill=[(220, 80, 60), (60, 140, 220), (80, 170, 90), (160, 90, 200)][k % 4])
        d.text((cx, cy + 26), name, font=font(10), fill=(20, 40, 90), anchor="mm")
    chrome(menu, "Options", "Exit")
    title = S.title(game, size, prompt="PRESS 5")
    game1, game2 = S.play(game, size)
    return dict(standby=standby, menu=menu, title=title, game1=game1, game2=game2)


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["plum"])
    for reg in (face(), keypad(), back()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "symbian_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.convert("RGB").resize((w, h), Image.LANCZOS), (x, y))
    media.save(os.path.join(out, "symbian_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
