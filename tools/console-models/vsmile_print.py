"""The V.Smile card's printing (vsmile_print.png), for the console theme's V.Smile model (vsmile.py).

One image, laid out as vsmile_layout.REGIONS says, each region in millimetres as the model's UVs map it: the console
from above (the smoked lid's ripples, V.SMILE and TV LEARNING SYSTEM on it with the mascot, its finger notch, RESTART),
the console from the front (the periwinkle band under its wavy edge: vtech, PLAYER 1 and 2 over the ports, the logo,
ON's sun over OFF's moon in their silver bezel; the cartridge's mark in the pocket), the Smartridge's face (a made-up
game from tools/made-up-games on its label, vtech moulded under it), the controller from above (ENTER and its tick,
V.SMILE, HELP, EXIT and ABC, the joystick base's ticks), and swatches. Make the made-up games' library first
(tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/vsmile_print.py artifacts/made-up-games <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screens_print as S  # noqa: E402
import vsmile_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
WHITE = (250, 250, 250)
GAME = ("Budling - Sky Garden (Europe)", "n64")   # the friendliest of the made-up games, as a learning game


def mascot(reg, x, y, s):
    """V.Smile's mascot: a yellow, toast-shaped face with two eyes and a smile."""
    reg.rect_(x - s, y - s * 1.1, x + s, y + s, C["yellow"], r=s * 0.45)
    for dx in (-0.4, 0.4):
        reg.circle(x + dx * s, y - 0.2 * s, 0.16 * s, (30, 30, 40))
    reg.line([(x - 0.45 * s, y + 0.35 * s), (x, y + 0.55 * s), (x + 0.45 * s, y + 0.35 * s)], (30, 30, 40), 0.12 * s)


def logo(reg, x, y, h, small=True):
    """V.SMILE: the V in blue, SMILE in yellow; TV LEARNING SYSTEM under it."""
    reg.text("V", "ariblk.ttf", h * 1.3, x, y, C["blue"], anchor="rs")
    reg.text(".SMILE", "ariblk.ttf", h, x, y, C["yellow"], anchor="ls")
    mascot(reg, x + h * 4.6, y - h * 0.5, h * 0.55)
    if small:
        reg.text("TV LEARNING SYSTEM", "arialbd.ttf", h * 0.32, x + h * 1.6, y + h * 0.5, WHITE)


def top():
    x0, x1, y0, y1 = L.TOP_SPAN
    reg = Region(L.REGIONS["top"], x1 - x0, y1 - y0, C["orange"])

    def at(x, y):
        return x - x0, y1 - y

    lx0, lx1, ly0, ly1 = L.LID["rect"]
    reg.rect_(*at(lx0, ly1), *at(lx1, ly0), C["lid"], r=L.LID["r"])
    cx, cy = at(0.0, (ly0 + ly1) / 2 + 6.0)
    for k in range(32, 0, -1):                             # the ripples, ring in ring
        reg.circle(cx, cy, 4.0 * k, shade(C["lid"], 0.1 if k % 2 else -0.04))
    mask = Image.new("L", reg.img.size, 255)               # keep the rings inside the lid
    ImageDraw.Draw(mask).rounded_rectangle(reg.box(*at(lx0, ly1), *at(lx1, ly0)), radius=L.LID["r"] * reg.sx, fill=0)
    reg.img.paste(Image.new("RGBA", reg.img.size, C["orange"] + (255,)), (0, 0), mask)
    logo(reg, *at(-18.0, ly0 + 18.0), 7.0)
    reg.circle(*at(0.0, ly0), 6.0, shade(C["lid"], -0.3))
    rx, ry = L.RESTART["at"]
    reg.circle(*at(rx, ry), L.RESTART["r"], C["restart"])
    reg.text("RESTART", "arialbd.ttf", 2.0, *at(rx, ry), WHITE)
    return reg


def band_edge(x):
    return L.BAND_TOP + 2.6 * math.cos(2 * math.pi * x / 64.0)


def front():
    x0, x1, z0, z1 = L.FRONT_SPAN
    reg = Region(L.REGIONS["front"], x1 - x0, z1 - z0, C["orange"])

    def at(x, z):
        return x - x0, z1 - z

    reg.poly([at(x0, z0)] + [at(x0 + (x1 - x0) * k / 60, band_edge(x0 + (x1 - x0) * k / 60)) for k in range(61)]
             + [at(x1, z0)], C["band"])
    reg.text("vtech", "arialbd.ttf", 8.0, *at(-82.0, 42.0), WHITE)
    for k, x in enumerate(L.PORTS["x"]):
        reg.text(f"PLAYER {k + 1}", "arialbd.ttf", 1.9, *at(x, L.PORTS["z"] + 7.0), WHITE)
        reg.circle(*at(x, L.PORTS["z"]), L.PORTS["r"] + 1.0, shade(C["band"], -0.3))
        reg.circle(*at(x, L.PORTS["z"]), L.PORTS["r"], C["dark"])
    logo(reg, *at(-6.0, 26.0), 7.5)
    bx = L.ON_OFF["x"]
    for z in L.ON_OFF["z"]:
        reg.circle(*at(bx, z), L.ON_OFF["bezel"][0], C["silver"])
    reg.rect_(*at(bx - 4.0, L.ON_OFF["z"][0]), *at(bx + 4.0, L.ON_OFF["z"][1]), C["silver"])
    for z, sun in zip(L.ON_OFF["z"], (True, False)):
        reg.circle(*at(bx, z), L.ON_OFF["r"], C["blue"])
        if sun:
            reg.circle(*at(bx, z), 2.0, C["yellow"])
            for k in range(8):
                a = math.pi * k / 4
                reg.line([at(bx + 2.6 * math.cos(a), z + 2.6 * math.sin(a)),
                          at(bx + 3.6 * math.cos(a), z + 3.6 * math.sin(a))], C["yellow"], 0.5)
        else:
            reg.circle(*at(bx, z), 2.8, C["yellow"])
            reg.circle(*at(bx + 1.3, z + 0.8), 2.5, C["blue"])
    reg.text("ON", "arialbd.ttf", 2.2, *at(bx + 12.0, L.ON_OFF["z"][0]), WHITE)
    reg.text("OFF", "arialbd.ttf", 2.2, *at(bx + 12.0, L.ON_OFF["z"][1]), WHITE)
    reg.rect_(*at(-6.0, 70.0), *at(6.0, 56.0), shade(C["orange"], -0.18), r=1.5)   # the cartridge's mark in the pocket
    return reg


def face(made_up):
    w, _, h = L.CART["size"]
    span = h + 3.0
    reg = Region(L.REGIONS["face"], w, span, C["purple"])
    game = S.made_up(*GAME, made_up)
    reg.rect_(5.0, 7.0, w - 5.0, 56.0, shade(C["purple"], -0.2), r=3.0)
    a, b, c, d = reg.box(6.0, 8.0, w - 6.0, 55.0)
    reg.img.paste(ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.4)),
                  (round(a), round(b)))
    k = min((c - a) * 0.8 / game.logo.width, (d - b) * 0.32 / game.logo.height)
    lg = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(lg, (round((a + c - lg.width) / 2), round(d - lg.height - 1.5 * reg.sy)))
    reg.text("vtech", "arialbd.ttf", 5.0, w / 2, 64.0, shade(C["purple"], -0.12))
    reg.text("▼", "seguisym.ttf", 3.0, w / 2, 70.0, shade(C["purple"], -0.12))
    reg.rect_(7.0, span - 9.0, w - 7.0, span, shade(C["purple"], -0.25))
    return reg


def pad():
    x0, x1, y0, y1 = L.PAD_SPAN
    reg = Region(L.REGIONS["pad"], x1 - x0, y1 - y0, C["band"])

    def at(x, y):
        return x - x0, y1 - y

    P = L.PAD
    sx, sy, sr = P["stick"]
    reg.rect_(*at(30.0, P["bridge"]), *at(sx, -P["bridge"]), C["orange"])
    reg.circle(*at(sx, sy), sr, C["orange"])
    for k in range(24):
        a = 2 * math.pi * k / 24
        reg.line([at(sx + (sr - 6.0) * math.cos(a), sy + (sr - 6.0) * math.sin(a)),
                  at(sx + (sr - 2.0) * math.cos(a), sy + (sr - 2.0) * math.sin(a))], shade(C["orange"], -0.2), 0.8)
    reg.circle(*at(0.0, 0.0), P["r"] + 2.0, C["band"])
    reg.circle(*at(0.0, 0.0), P["enter"][1], C["silver"])
    reg.circle(*at(0.0, 0.0), P["enter"][0], C["orange"])
    reg.text("ENTER", "ariblk.ttf", 5.4, *at(0.0, -9.0), WHITE)
    reg.line([at(-6.0, 4.0), at(-1.5, -1.0), at(8.0, 10.0)], WHITE, 2.2)
    reg.text("vtech", "arialbd.ttf", 3.2, *at(0.0, 14.0), WHITE)
    reg.text("V.SMILE", "ariblk.ttf", 3.6, *at(0.0, 35.5), C["yellow"])
    for (x, y), mark in zip(P["small"], ("?", "⇥", "ABC")):
        reg.circle(*at(x, y), 5.0, shade(C["band"], 0.15))
        reg.text(mark, "seguisym.ttf" if mark == "⇥" else "arialbd.ttf", 4.0 if len(mark) == 1 else 2.6, *at(x, y),
                 WHITE)
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["orange"])
    for reg in (top(), front(), face(made_up), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    path = os.path.join(out, "vsmile_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
