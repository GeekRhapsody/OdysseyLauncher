"""The SuFami Turbo's front and its mini cartridges' labels (sufami_print.png), for the console theme's SuFami Turbo
card (sufami.py), whose Super Famicom is snes.py's (its printing is snes_print.py's `sfc`).

One image, laid out as sufami_layout.REGIONS says: the adapter's front (the dark band across it: スーファミターボ over
SUFAMI TURBO in white, its round emblem, スーパーファミコン under it) and two mini cartridges' labels (made-up games from
tools/made-up-games: the band with SUFAMI TURBO over each game's box art and its title), and swatches. Make the made-up
games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/sufami_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screens_print as S  # noqa: E402
import sufami_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

BODY = rgb(L.COLOURS["body"])
BAND = rgb(L.COLOURS["band"])
WHITE = (244, 244, 242)
GAMES = dict(a=("Springheel Sam (Europe)", "snes", (232, 64, 120)), b=("Kaleidrop (Europe)", "snes", (40, 150, 220)))


def slanted(reg, text, font, size, x, y, fill, lean=0.18, anchor="mm", outline=None):
    """Text leaning forward, as SUFAMI TURBO is lettered."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    extra = dict(stroke_width=max(1, round(0.4 * reg.sx)), stroke_fill=outline + (255,)) if outline else {}
    d.text(reg.p(x, y), text, font=f, fill=fill + (255,), anchor=anchor, **extra)
    yc = reg.p(0, y)[1]
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, lean, -lean * yc, 0, 1, 0)))


def emblem(reg, x, y, r, ink, ground):
    """The round emblem beside the name: a ring, SF inside it."""
    reg.circle(x, y, r, ink)
    reg.circle(x, y, r * 0.78, ground)
    reg.text("SF", "ariblk.ttf", r * 0.9, x, y + r * 0.05, ink)


def front():
    """The body's front: x across (-top/2 at the left), z down from its top."""
    w, h = L.BODY["top"][0], L.BODY["height"]
    reg = Region(L.REGIONS["front"], w, h, BODY)

    def at(x, z):
        return x + w / 2, h - z
    half, (z0, z1) = L.BAND["x"], L.BAND["z"]
    reg.rect_(*at(-half, z1), *at(half, z0), BAND, r=2.0)
    reg.text("スーファミターボ", "YuGothB.ttc", 3.2, *at(-14.0, z1 - 3.6), WHITE)
    slanted(reg, "SUFAMI TURBO", "ariblk.ttf", 7.6, *at(-8.0, (z0 + z1) / 2 - 0.8), WHITE)
    emblem(reg, *at(half - 9.0, (z0 + z1) / 2), 5.6, WHITE, BAND)
    reg.text("スーパーファミコン", "YuGothB.ttc", 2.6, *at(-8.0, z0 + 2.6), shade(WHITE, -0.15))
    return reg


def label(name, made_up):
    """A mini cartridge's label: the band with SUFAMI TURBO, the made-up game's box art, its title."""
    lw, lh, _ = L.MINI["label"]
    stem, system, colour = GAMES[name]
    reg = Region(L.REGIONS[name], lw, lh, (250, 248, 240))
    reg.rect_(0.0, 0.0, lw, 7.0, colour)
    slanted(reg, "SUFAMI TURBO", "ariblk.ttf", 4.0, lw / 2, 3.5, WHITE)
    art = S.cover(stem, system, made_up)
    a, b, c, d = reg.box(2.0, 8.5, lw - 2.0, lh - 7.5)
    reg.img.paste(ImageOps.fit(art, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.3)),
                  (round(a), round(b)))
    reg.rect_(0.0, lh - 6.5, lw, lh, (250, 248, 240))
    reg.text(stem.split(" (")[0].upper(), "arialbd.ttf", 3.0, lw / 2, lh - 3.3, (40, 40, 44))
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BODY)
    for reg in (front(), label("a", made_up), label("b", made_up)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(body=BODY, dark=(26, 26, 30), mini=rgb(L.COLOURS["mini"]), grip=shade(rgb(L.COLOURS["mini"]), -0.15))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "sufami_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
