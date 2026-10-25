"""The Acorn Electron card's printing and screens (electron_print.png), for the console theme's model (electron.py).

One image, laid out as electron_layout.REGIONS says: the computer and the Plus 1 from above (the key tops and legends,
the dark band with its grid, acorn electron and the green acorn, the Plus 1's slot covers), the cartridge's label (a
made-up game, Odyssey), the screens (the Electron's start-up screen, then the game's title and two moments of its play
in Mode 2's eight colours, drawn as the BBC Micro's are), the television's front (zx_spectrum_print.py's, where its
layout puts it), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/electron_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import electron_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from bbcmicro_print import game, mode7, title  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402
from zx_spectrum_print import tv_front  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
BAND = rgb(L.COLOURS["band"])
INK = (40, 40, 44)
GREEN = (110, 200, 60)


def top():
    """The computer and the Plus 1 from above: x across (-170 at the left), y down from the Plus 1's back (250)."""
    w, d = L.WIDTH, L.PLUS1["y"][1]
    reg = Region(L.REGIONS["top"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y

    # The opening's floor and the band.
    (ox0, ox1), (s0, s1) = L.OPENING["x"], L.OPENING["s"]
    reg.rect_(*at(ox0, L.top_point(s1, 0.0)[0]), *at(ox1, L.top_point(s0, 0.0)[0]), (176, 168, 150))
    (b0, b1) = L.BAND["s"]
    y0, y1 = L.top_point(b0, 0.0)[0], L.top_point(b1, 0.0)[0]
    reg.rect_(*at(-w / 2 + 6.0, y1), *at(w / 2 - 6.0, y0), BAND)
    x = -w / 2 + 6.0
    while x < w / 2 - 6.0:
        reg.line([at(x, y0), at(x, y1)], (88, 96, 84), 0.25)
        x += 4.0
    yy = y0
    while yy < y1:
        reg.line([at(-w / 2 + 6.0, yy), at(w / 2 - 6.0, yy)], (88, 96, 84), 0.25)
        yy += 4.0
    my = (y0 + y1) / 2
    reg.text("acorn", "arialbd.ttf", 7.0, *at(-140.0, my), (240, 240, 236), anchor="lm")
    reg.draw.ellipse(reg.box(*at(-111.5, my + 4.6), *at(-104.5, my - 4.8)), fill=GREEN)
    reg.text("electron", "arialbd.ttf", 7.0, *at(-102.0, my), (240, 240, 236), anchor="lm")
    # The keys' tops.
    for legend, kx0, kx1, s in L.keys():
        ya, yb = L.top_point(s - 9.5 + L.KEY["inset"], L.KEY["height"] - L.OPENING["depth"])[0], \
            L.top_point(s + 9.5 - L.KEY["inset"], L.KEY["height"] - L.OPENING["depth"])[0]
        reg.rect_(*at(kx0 + L.KEY["inset"], yb), *at(kx1 - L.KEY["inset"], ya), KEY, r=1.2)
        if legend.strip():
            size = 4.4 if len(legend) <= 2 else 2.2
            reg.text(legend, "arialbd.ttf" if len(legend) > 2 else "arial.ttf", size,
                     *at((kx0 + kx1) / 2, (ya + yb) / 2), INK)
    # The Plus 1's slot covers.
    (cx0, cx1) = L.PLUS1["x"]
    for (sy0, sy1) in L.PLUS1["slots"]:
        reg.rect_(*at(cx0 - 3.0, sy1 + 3.0), *at(cx1 + 3.0, sy0 - 3.0), (200, 192, 172), r=2.0)
        reg.rect_(*at(cx0, sy1), *at(cx1, sy0), (220, 212, 192), r=1.0)
    reg.text("PLUS 1", "arialbd.ttf", 4.0, *at(-110.0, 205.0), (150, 142, 124))
    return reg


def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (20, 20, 24))
    art = space((480, 312)).convert("RGB")
    ship(ImageDraw.Draw(art), 150, 190, 3.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 12.0, lw, lh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 12.0, (16, 16, 18))
    reg.text("ODYSSEY", "ariblk.ttf", 7.0, lw / 2, 6.0, (255, 214, 70))
    return reg


def boot():
    return mode7([(0, 0, "Acorn Electron", "white", False), (2, 0, "BASIC", "white", False),
                  (4, 0, ">_", "white", False)])


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), label(), tv_front()):
        reg.paste(image)
    for name, screen in (("boot", boot()), ("title", title()), ("game_1", game(0)), ("game_2", game(1))):
        x, y, w, h = L.REGIONS[name]
        image.paste(screen.resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(image)
    for name, colour in (("black", rgb(SL.COLOURS["bezel"])), ("silver", rgb(SL.COLOURS["handle"])),
                         ("red", (255, 40, 30))):
        x, y = SL.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    colours = dict(case=CASE, key=KEY, band=BAND, dark=rgb(L.COLOURS["dark"]), cart=(24, 24, 26), lit=(255, 60, 40))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "electron_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
