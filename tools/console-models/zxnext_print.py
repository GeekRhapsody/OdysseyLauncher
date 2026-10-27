"""The ZX Spectrum Next card's printing and screens (zxnext_print.png, zxnext_media.png), for the console theme's model
(zxnext.py).

`zxnext_print.png`, laid out as zxnext_layout.PRINT_REGIONS says: the Next from above (its keys' tops and legends: the
main one large, its keyword over it, the colours' names on the digits; sinclair moulded in gloss and ZX Spectrum Next in
red; the bands right of the keys and the four stripes in their grooves; the vents), the right end (the stripes running
down it), the left end (RESET, DRIVE, SD and NMI), and swatches; the television's front (zx_spectrum_print.py's) and
its swatches where zx_spectrum_layout.py puts them. `zxnext_media.png`: the screens, the Next's 256 x 192 paper in its
black border: the start-up menu, the browser with a made-up game chosen, the game's title and two moments of it in the
Next's 256 colours (3 bits of red and green, 2 of blue). The game is tools/made-up-games's (made up: no real game's
art). Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow,
numpy, scipy):

    python tools/console-models/zxnext_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screens_print as S  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
import zxnext_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402
from zx_spectrum_print import tv_front  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
LEGEND = rgb(L.COLOURS["legend"])
RED = rgb(L.COLOURS["red"])
GAME = ("Rotorstorm (Europe)", "megadrive")
FILES = ["ROTORSTORM.NEX", "SPRINGHEEL.NEX", "KALEIDROP.NEX", "TIDECALLER.NEX", "GRAVELKING.NEX", "DEEPFATHOM.NEX"]


# ---- The printing ----------------------------------------------------------------------------------------------------

def top():
    """The Next from above: x across (-WIDTH/2 at the left), y down from its back edge to its front."""
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    # The bands right of the keys, the stripes in the grooves between them.
    x0, x1 = L.PANEL["x"]
    for k, colour in enumerate(L.STRIPES):
        y = L.ROW_FRONT + (len(L.KEYS) - 1 - k) * L.KEY_PITCH
        reg.rect_(*at(x0, y + 1.6), *at(x1, y - 1.6), shade(CASE, -0.5))
        reg.rect_(*at(x0 + 40.0, y + 0.9), *at(x1, y - 0.9), rgb(colour))
    v = L.VENTS
    for k in range(v["count"]):
        x = v["x"][0] + (v["x"][1] - v["x"][0]) * (k + 0.5) / v["count"]
        reg.rect_(*at(x - 0.9, v["y"][1]), *at(x + 0.9, v["y"][0]), (8, 8, 9), r=0.6)
    # sinclair, moulded gloss on the matt top, ZX Spectrum Next in red under it.
    f = ImageFont.truetype(FONTS + "ariblk.ttf", round(11.0 * reg.sx))
    lx, ly = at(L.LOGO["x"], L.LOGO["y"])
    for dx, colour in ((0.3, shade(CASE, -0.4)), (-0.2, shade(CASE, 0.35)), (0.0, shade(CASE, 0.12))):
        reg.draw.text(reg.p(lx + dx, ly + dx), "sinclair", font=f, fill=colour, anchor="ls")
    reg.text("ZX Spectrum Next", "arialbi.ttf", 4.6, lx, ly + 5.0, RED, anchor="lm")
    # The keys.
    g, inset = L.KEY["gap"] / 2, L.KEY["inset"]
    enter = 0
    for legend, kx0, kx1, ky0, ky1 in L.keys():
        if legend == "ENTER":                              # one L-shaped key: its upper part runs down into its lower
            enter += 1
            reg.rect_(*at(kx0 + g + inset, ky1 - g - inset), *at(kx1 - g - inset, ky0 + g + inset - (
                L.KEY["gap"] + 2 * inset if enter == 1 else 0.0)), KEY, r=L.KEY["r"])
            if enter == 1:
                continue
        else:
            reg.rect_(*at(kx0 + g + inset, ky1 - g - inset), *at(kx1 - g - inset, ky0 + g + inset), KEY,
                      r=L.KEY["r"])
        cx, cy = at((kx0 + kx1) / 2, (ky0 + ky1) / 2)
        if len(legend) == 1 and legend.isalnum():
            reg.text(legend, "arialbd.ttf", 5.4, cx - 2.0, cy + 2.6, LEGEND)
            word = L.KEYWORDS.get(legend, "")
            reg.text(word, "arial.ttf", 2.0, cx, cy - 2.0, LEGEND)
            colour = L.COLOUR_KEYS.get(legend)
            if colour:
                reg.text(colour, "arial.ttf", 1.6, cx, cy - 5.2, LEGEND)
        elif legend in "⇦⇧⇨⇩" and legend.strip():
            reg.text(legend, "seguisym.ttf", 6.0, cx, cy, LEGEND)
        elif legend.strip():
            lines = legend.split(" ") if " " in legend else [legend]
            for k, line in enumerate(lines):
                reg.text(line, "arialbd.ttf", 2.3, cx, cy + (k - (len(lines) - 1) / 2) * 2.8, LEGEND)
    return reg


def right_end():
    """The right end from the right: y across (0, the front, at the right), z down from the top."""
    reg = Region(L.PRINT_REGIONS["end"], L.DEPTH, L.BACK[1], CASE)
    for k, colour in enumerate(L.STRIPES):
        y = L.ROW_FRONT + (len(L.KEYS) - 1 - k) * L.KEY_PITCH
        reg.rect_(L.DEPTH - y - 1.6, 0.0, L.DEPTH - y + 1.6, L.BACK[1] - 4.0, shade(CASE, -0.5))
        reg.rect_(L.DEPTH - y - 0.9, 0.0, L.DEPTH - y + 0.9, L.BACK[1] - 6.0, rgb(colour))
    return reg


def left_end():
    """The left end from the left: y across (0, the front, at the left), z down from the top."""
    reg = Region(L.PRINT_REGIONS["left"], L.DEPTH, L.BACK[1], CASE)
    b = L.BUTTONS
    for name in ("reset", "drive", "nmi"):
        y, _ = b[name]
        reg.text(name.upper(), "arialbd.ttf", 2.2, y, L.BACK[1] - b["z"] - 5.4, shade(CASE, 0.6))
    reg.text("SD", "arialbd.ttf", 2.2, sum(L.SD["y"]) / 2, L.BACK[1] - L.SD["z"][1] - 3.0, shade(CASE, 0.6))
    reg.rect_(L.SD["y"][0], L.BACK[1] - L.SD["z"][1], L.SD["y"][1], L.BACK[1] - L.SD["z"][0], (6, 6, 7))
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), right_end(), left_end(), tv_front()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", rgb(SL.COLOURS["bezel"])), ("silver", rgb(SL.COLOURS["handle"])),
                         ("red", (255, 40, 30))):
        x, y = SL.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    colours = dict(case=CASE, key=KEY, dark=(8, 8, 9), reset=rgb(L.BUTTONS["reset"][1]),
                   drive=rgb(L.BUTTONS["drive"][1]), nmi=rgb(L.BUTTONS["nmi"][1]))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "zxnext_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -----------------------------------------------------------------------------------------------------

RAINBOW = [(216, 0, 0), (216, 216, 0), (0, 216, 0), (0, 216, 216)]


def rgb332(img):
    """A picture in the Next's 256 colours: 3 bits of red and green, 2 of blue."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    a[..., 0] = np.round(a[..., 0] / 255 * 7) * 255 / 7
    a[..., 1] = np.round(a[..., 1] / 255 * 7) * 255 / 7
    a[..., 2] = np.round(a[..., 2] / 255 * 3) * 255 / 3
    return Image.fromarray(a.astype(np.uint8))


def boxed(title, entries, chosen):
    """A menu in the Spectrum's manner: a white box, its title in a black bar with the rainbow at its right, a cyan bar
    over the chosen entry."""
    w, h = L.PAPER
    img = Image.new("RGB", L.PAPER, (0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0, x1 = 24, 24, w - 24
    y1 = y0 + 16 + 12 * len(entries) + 6
    d.rectangle([x0, y0, x1, y1], fill=(216, 216, 216))
    d.rectangle([x0, y0, x1, y0 + 11], fill=(0, 0, 0))
    S.chars(img, (x0 + 4) / 8, (y0 + 2) / 8, title, (255, 255, 255))
    for k, colour in enumerate(RAINBOW):
        d.polygon([(x1 - 44 + k * 9, y0 + 11), (x1 - 36 + k * 9, y0), (x1 - 30 + k * 9, y0), (x1 - 38 + k * 9, y0 + 11)],
                  fill=colour)
    for k, entry in enumerate(entries):
        y = y0 + 16 + 12 * k
        if k == chosen:
            d.rectangle([x0 + 2, y - 2, x1 - 2, y + 9], fill=(0, 216, 216))
        S.chars(img, (x0 + 8) / 8, y / 8, entry, (0, 0, 0))
    return img


def glass(picture):
    """A screen's region: the black border filling the glass, the paper in its middle."""
    w, h = L.SCREEN_PX
    image = Image.new("RGB", (w, h), (0, 0, 0))
    pw, ph = L.PAPER
    image.paste(picture.resize((pw, ph), Image.NEAREST), ((w - pw) // 2, (h - ph) // 2))
    return image


def media_atlas(made_up, out):
    game = S.made_up(*GAME, made_up)
    shots = dict(menu=boxed("NextZXOS", ["Browser", "Command Line", "Calculator", "NextBASIC", "48K BASIC"], 0),
                 browser=boxed("Browser", FILES, 0),
                 title=rgb332(S.title(game, L.PAPER, prompt="PRESS SPACE")))
    shots["game1"], shots["game2"] = (rgb332(frame) for frame in S.play(game, L.PAPER))
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    for name, (x, y, w, h) in L.MEDIA_REGIONS.items():
        image.paste(glass(shots[name]).resize((w, h), Image.LANCZOS), (x, y))
    path = os.path.join(out, "zxnext_media.png")
    image.save(path, optimize=True)
    print(path)


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(made_up, out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
