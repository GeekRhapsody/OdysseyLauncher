"""The Othello Multivision card's printing (multivision_print.png), for the console theme's Othello Multivision model
(multivision.py).

One image, laid out as multivision_layout.REGIONS says, each region in millimetres as the model's UVs map it: the shell's
top seen from above (Othello® Multivision in navy, the vents' shade, the keys' maroon tops and their legends, the arrows
moulded round the joystick, Tsukuda Original moulded at the front right), the cartridge's face, its label in the manner
of Tsukuda's (a made-up game from tools/made-up-games: its logo, FOR OTHELLO MULTIVISION, its painting), and swatches. Make
the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/multivision_print.py artifacts/made-up-games <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multivision_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CREAM = rgb(L.COLOURS["cream"])
MAROON = rgb(L.COLOURS["maroon"])
LOGO = rgb(L.COLOURS["logo"])
WHITE = (246, 246, 242)
GAME = ("hivehstl", "arcade")            # a made-up arcade game of 1981, ported


def top_point(x, y):
    return x + L.HALF, L.DEPTH - y


def moulded(reg, text, font, size, x, y, anchor="mm"):
    for d, colour in ((0.25, shade(CREAM, -0.2)), (-0.25, shade(CREAM, 0.06)), (0.0, shade(CREAM, -0.04))):
        reg.text(text, font, size, x + d, y + d, colour, anchor=anchor)


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CREAM)
    reg.text("Othello", "segoeuib.ttf", 11.0, *top_point(-115.7, 139.0), LOGO, anchor="ls")
    reg.text("®", "segoeuib.ttf", 4.0, *top_point(-74.5, 143.5), LOGO, anchor="ls")
    reg.text("Multivision", "segoeuib.ttf", 11.0, *top_point(-115.7, 129.0), LOGO, anchor="ls")
    v = L.VENTS
    for k in range(v["count"]):
        x = v["x"][0] + (v["x"][1] - v["x"][0]) * (k + 0.5) / v["count"]
        reg.rect_(*top_point(x - v["width"] / 2, v["y"][1]), *top_point(x + v["width"] / 2, v["y"][0]),
                  shade(CREAM, -0.3))
    x0, x1, y0, y1 = L.FLAP["rect"]
    reg.rect_(*top_point(x0, y1), *top_point(x1, y0), (10, 10, 12))
    i = L.KEY["inset"]
    for legend, kx0, kx1, ky0, ky1 in L.KEYS:
        reg.rect_(*top_point(kx0, ky1), *top_point(kx1, ky0), shade(MAROON, -0.15), r=0.8)
        reg.rect_(*top_point(kx0 + i, ky1 - i), *top_point(kx1 - i, ky0 + i), MAROON, r=0.6)
        cx, cy = top_point((kx0 + kx1) / 2, (ky0 + ky1) / 2)
        lines = legend.split("\n")
        for k, line in enumerate(lines):
            font = "seguisym.ttf" if line in "✱#" else "arial.ttf"
            reg.text(line, font, 4.2 if len(line) == 1 else 3.2, cx, cy + (k - (len(lines) - 1) / 2) * 8.0,
                     shade(MAROON, -0.42))
    sx, sy = top_point(*L.STICK["at"])
    for k in range(8):                                    # the arrows moulded round the joystick
        a = math.pi * k / 4
        c, s = math.cos(a), math.sin(a)
        r0 = 16.5
        tip = (sx + (r0 + 2.4) * c, sy - (r0 + 2.4) * s)
        reg.poly([tip, (sx + r0 * c - 1.6 * s, sy - r0 * s - 1.6 * c), (sx + r0 * c + 1.6 * s, sy - r0 * s + 1.6 * c)],
                 shade(CREAM, -0.16))
    moulded(reg, "Tsukuda Original", "segoeuib.ttf", 4.6, *top_point(85.0, 17.0))
    return reg


def face(made_up):
    """The cartridge's face, its label on it: the game's logo on blue, FOR OTHELLO MULTIVISION, its painting framed in
    white."""
    cw, _, ch = L.CART["size"]
    lw, lh, margin = L.CART["label"]
    reg = Region(L.REGIONS["face"], cw, ch, rgb(L.COLOURS["shell"]))
    for k in range(9):                                     # the shell's grip ribs under the label
        reg.rect_(4.0, lh + margin + 2.0 + 1.6 * k, cw - 4.0, lh + margin + 2.6 + 1.6 * k, (14, 14, 15))
    ox, oy = (cw - lw) / 2, margin                         # the label's top left corner on the face
    reg.rect_(ox, oy, ox + lw, oy + lh, (36, 72, 168), r=1.0)
    game = S.made_up(*GAME, made_up)
    k = min(lw * 0.86 * reg.sx / game.logo.width, 20.0 * reg.sy / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(logo, (round((ox + lw / 2) * reg.sx - logo.width / 2), round((oy + 2.5) * reg.sy)))
    reg.text("FOR OTHELLO MULTIVISION", "arialbd.ttf", 2.6, ox + lw / 2, oy + 25.5, WHITE)
    reg.text("Tsukuda Original", "segoeuib.ttf", 3.2, ox + lw - 4.0, oy + 30.5, WHITE, anchor="rm")
    reg.rect_(ox + 4.0, oy + 33.5, ox + lw - 4.0, oy + lh - 4.0, WHITE)
    a, b, c, d = reg.box(ox + 5.2, oy + 34.7, ox + lw - 5.2, oy + lh - 5.2)
    reg.img.paste(ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.45)),
                  (round(a), round(b)))
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CREAM)
    for reg in (top(), face(made_up)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(L.COLOURS[name]))
    path = os.path.join(out, "multivision_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
