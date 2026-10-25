"""The Commodore Plus/4 card's printing and screens (plus4_print.png, plus4_media.png), for the console theme's model
(plus4.py).

`plus4_print.png`, laid out as plus4_layout.PRINT_REGIONS says: the Plus/4 from above (the keys' tops and legends, the
function keys', the cursor keys' arrows, the Commodore logo with its rainbow and plus/4, the fins, the power light), the
1531 from above (its silver plate, the lid's window, the keys' names, commodore, the counter), the cassette's label (a
made-up game, Odyssey), and swatches; the television's front (zx_spectrum_print.py's) and its swatches where
zx_spectrum_layout.py puts them. `plus4_media.png`: the screens, the TED's picture in its border (the start-up screen,
LOAD and PRESS PLAY ON TAPE, SEARCHING, FOUND ODYSSEY and LOADING, the title, two moments of the game), drawn in its
character cells as the VIC-20's are. Run it with the system Python (Pillow):

    python tools/console-models/plus4_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plus4_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from vic20_print import cbm_logo, chars  # noqa: E402
from windows_pc_print import Region  # noqa: E402
from zx_spectrum_print import tv_front  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
FKEY = rgb(L.COLOURS["fkey"])
DECK = rgb(L.COLOURS["deck"])
INK = (52, 50, 48)
SILVER = (178, 180, 182)
RAINBOW = [(52, 120, 220), (60, 170, 230), (80, 190, 120), (200, 210, 60), (240, 190, 50), (240, 120, 40),
           (220, 50, 50)]
ARROWS = dict(up=(0.0, 1.0), down=(0.0, -1.0), left=(-1.0, 0.0), right=(1.0, 0.0))


# ---- The Plus/4 ------------------------------------------------------------------------------------------------------

def top():
    """The Plus/4 from above: x across (-WIDTH/2 at the left), y down from the fins' back to the front."""
    back = L.FINS["y"][1]
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, back, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, back - y

    (fx0, fx1), (fy0, fy1), n = L.FINS["x"], L.FINS["y"], L.FINS["count"]
    reg.rect_(*at(fx0, fy1), *at(fx1, fy0), (8, 8, 9))
    pitch = (fx1 - fx0) / n
    for k in range(n):
        x = fx0 + (k + 0.5) * pitch
        reg.rect_(*at(x - L.FINS["thickness"] / 2, fy1), *at(x + L.FINS["thickness"] / 2, fy0), (56, 56, 60))

    (lx0, lx1), (ly0, ly1) = L.LOGO["x"], L.LOGO["y"]
    my = (ly0 + ly1) / 2
    reg.rect_(*at(lx0 - 2.0, ly1 + 1.0), *at(lx1 + 2.0, ly0 - 1.0), (22, 22, 24), r=1.0)
    cbm_logo(reg, *at(lx0 + 4.5, my), 7.0, (226, 226, 222), (22, 22, 24))
    reg.text("commodore", "arialbd.ttf", 6.2, *at(lx0 + 10.0, my), (226, 226, 222), anchor="lm")
    for k, colour in enumerate(RAINBOW * 3):                # the rainbow's thin stripes
        x = lx0 + 57.0 + k * 1.75
        reg.rect_(*at(x, ly1 - 2.0), *at(x + 1.1, ly0 + 2.0), colour)
    reg.text("plus/4", "arialbd.ttf", 7.0, *at(lx1 - 1.0, my), (226, 226, 222), anchor="rm")

    w = L.FKEYS["width"]
    fy0, fy1 = L.FKEYS["y"]
    for x, name in zip(L.FKEYS["x"], L.FKEYS["names"]):
        reg.rect_(*at(x, fy1), *at(x + w, fy0), FKEY, r=0.8)
        reg.text(name, "arial.ttf", 2.8, *at(x + 2.0, (fy0 + fy1) / 2), INK, anchor="lm")

    top_h, inset = L.KEY["height"], L.KEY["inset"]
    for legend, x0, x1, s in L.keys():
        ya = L.deck_point(s - 9.5 + inset, top_h)[0]
        yb = L.deck_point(s + 9.5 - inset, top_h)[0]
        reg.rect_(*at(x0 + inset, yb), *at(x1 - inset, ya), KEY, r=1.4)
        x, y = at((x0 + x1) / 2, (ya + yb) / 2)
        if legend == "C=":
            cbm_logo(reg, x, y, 5.0, INK, KEY)
        elif len(legend) == 1 and legend != " ":
            reg.text(legend, "arial.ttf", 4.6, x0 + L.WIDTH / 2 + inset + 1.6, y, INK, anchor="lm")
        elif legend.strip():
            for k, word in enumerate(legend.split(" ")):
                reg.text(word, "arial.ttf", 2.4, x0 + L.WIDTH / 2 + inset + 1.4, y - 1.6 + 3.0 * k, INK, anchor="lm")

    (cx, cy), reach, (kw, kh) = L.CURSOR["at"], L.CURSOR["reach"], L.CURSOR["size"]
    for name, (dx, dy) in ARROWS.items():
        kx, ky = cx + dx * reach, cy + dy * reach
        reg.rect_(*at(kx - kw / 2, ky + kh / 2), *at(kx + kw / 2, ky - kh / 2), (140, 140, 138), r=1.2)
        tip, base = (kx + dx * 4.0, ky + dy * 4.0), (kx - dx * 3.0, ky - dy * 3.0)
        side = (-dy * 3.0, dx * 3.0)
        reg.poly([at(*tip), at(base[0] + side[0], base[1] + side[1]), at(base[0] - side[0], base[1] - side[1])],
                 (210, 210, 206))
    (px, py), (pw, ph) = L.LIGHT["at"], L.LIGHT["size"]
    reg.rect_(*at(px - pw / 2, py + ph / 2), *at(px + pw / 2, py - ph / 2), (230, 40, 34), r=0.6)
    return reg


# ---- The 1531 --------------------------------------------------------------------------------------------------------

def deck():
    """The 1531 from above: x from its left, y down from its back to its front."""
    w, d, _ = L.DECK["size"]
    reg = Region(L.PRINT_REGIONS["deck"], w, d, DECK)

    def at(x, y):
        return x, d - y

    (px0, px1), (py0, py1) = L.PLATE["x"], L.PLATE["y"]
    reg.rect_(*at(px0, py1), *at(px1, py0), SILVER, r=3.0)
    (lx0, lx1), (ly0, ly1) = L.LID["x"], L.LID["y"]
    reg.rect_(*at(lx0 - 2.0, ly1 + 2.0), *at(lx1 + 2.0, ly0 - 2.0), (40, 40, 42), r=2.0)
    reg.rect_(*at(lx0 + 8.0, ly1 - 10.0), *at(lx1 - 8.0, ly0 + 18.0), (70, 72, 76), r=2.0)
    reg.text("AUTO  STOP", "arial.ttf", 3.4, *at((lx0 + lx1) / 2, ly0 + 8.0), (230, 230, 226))
    reg.rect_(*at(px0 + 4.0, 50.0), *at(px1 - 4.0, 40.0), (16, 16, 18))
    cbm_logo(reg, *at(px0 + 12.0, 45.0), 7.0, (230, 230, 226), (16, 16, 18))
    reg.text("commodore", "arialbd.ttf", 6.0, *at(px0 + 18.0, 45.0), (230, 230, 226), anchor="lm")
    for k in range(6):                                      # the stripes at the band's right
        reg.rect_(*at(px1 - 30.0 + k * 4.2, 49.0), *at(px1 - 28.4 + k * 4.2, 41.0), (230, 230, 226))
    (kx0, kx1) = L.PIANO["x"]
    kw = (kx1 - kx0) / 6
    for k, name in enumerate(L.PIANO["names"]):
        reg.text(name, "arial.ttf", 2.6, *at(kx0 + (k + 0.5) * kw, 37.0), (60, 60, 64))
    (cx0, cx1), (cy0, cy1) = L.COUNTER["x"], L.COUNTER["y"]
    reg.rect_(*at(cx0, cy1), *at(cx1, cy0), (10, 10, 10), r=1.0)
    for k, digit in enumerate("000"):
        reg.rect_(*at(cx0 + 2.0 + 8.4 * k, cy1 - 2.0), *at(cx0 + 9.0 + 8.4 * k, cy0 + 2.0), (230, 230, 226))
        reg.text(digit, "arialbd.ttf", 7.0, *at(cx0 + 5.5 + 8.4 * k, (cy0 + cy1) / 2), (20, 20, 20))
    reg.circle(*at(cx1 - 3.5, (cy0 + cy1) / 2), 2.4, (120, 120, 124))
    return reg


def cassette():
    """The cassette's face: its label (a made-up game, Odyssey) round its window and reels."""
    w, h, _ = L.CASSETTE["size"]
    reg = Region(L.PRINT_REGIONS["cassette"], w, h, (30, 30, 34))
    reg.rect_(4.0, 4.0, w - 4.0, h - 12.0, (240, 236, 224), r=2.0)
    art = space((440, 120)).convert("RGB")
    ship(ImageDraw.Draw(art), 120, 60, 2.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(6.0, 6.0, w - 6.0, 22.0)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 7.0, w / 2, 28.5, (60, 40, 120))
    reg.rect_(26.0, 33.0, w - 26.0, 47.0, (60, 60, 66), r=3.0)
    for x in (36.0, w - 36.0):
        reg.circle(x, 40.0, 5.5, (240, 236, 224))
        reg.circle(x, 40.0, 2.6, (40, 40, 44))
    reg.rect_(32.0, h - 9.0, w - 32.0, h - 2.0, (24, 24, 26))
    return reg


# ---- The screens -----------------------------------------------------------------------------------------------------

TED = dict(black=(0, 0, 0), white=(255, 255, 255), border=(108, 94, 181), yellow=(236, 220, 90),
           cyan=(110, 220, 230), orange=(220, 120, 50), red=(200, 60, 60), green=(110, 200, 90), blue=(70, 80, 200))
BOOT = ["COMMODORE BASIC V3.5 60671 BYTES FREE", "3-PLUS-1 ON KEY F1", "", "READY."]


def text_screen(lines, cursor=True):
    img = Image.new("RGB", L.TED_PX, TED["white"])
    for row, line in enumerate(lines):
        chars(img, 0, row, line, TED["black"])
    if cursor:
        ImageDraw.Draw(img).rectangle([0, len(lines) * 8, 7, len(lines) * 8 + 7], fill=TED["black"])
    return img, TED["border"]


def title():
    img = Image.new("RGB", L.TED_PX, TED["black"])
    d = ImageDraw.Draw(img)
    rng = random.Random(41)
    for _ in range(70):
        d.point((rng.randrange(320), rng.randrange(200)), fill=rng.choice([TED["white"], TED["cyan"], TED["yellow"]]))
    chars(img, 8, 2, "ODYSSEY", TED["yellow"], scale=3)
    chars(img, 12, 6, "A SPACE TRIP", TED["cyan"])
    d.ellipse([200, 100, 268, 168], fill=TED["orange"])
    d.ellipse([208, 106, 256, 150], fill=TED["yellow"])
    d.line([(180, 146), (290, 124)], fill=TED["white"], width=2)
    ship(d, 90, 134, 2.0, TED["white"], TED["red"])
    chars(img, 8, 22, "PRESS FIRE TO START", TED["green"])
    return img, TED["blue"]


def game(frame):
    img = Image.new("RGB", L.TED_PX, TED["black"])
    d = ImageDraw.Draw(img)
    rng = random.Random(7)
    for _ in range(60):
        x, y = rng.randrange(320), rng.randrange(176)
        d.point(((x - frame * 12) % 320, y + 16), fill=TED["white"])
    chars(img, 0, 0, "SCORE 0%d40" % (frame + 1), TED["yellow"])
    chars(img, 30, 0, "SHIPS 3", TED["cyan"])
    d.ellipse([230 - 10 * frame, 70, 290 - 10 * frame, 130], fill=TED["orange"])
    d.line([(214 - 10 * frame, 110), (306 - 10 * frame, 92)], fill=TED["white"], width=2)
    ship(d, 70, 110 + 16 * frame, 1.8, TED["white"], TED["red"])
    for k in range(3):                                      # the shots
        d.line([(110 + 40 * k + 14 * frame, 110 + 16 * frame), (124 + 40 * k + 14 * frame, 110 + 16 * frame)],
               fill=TED["yellow"], width=2)
    return img, TED["black"]


def glass(picture_and_border):
    """A screen's region: the border filling the glass, the TED's picture in its middle, its pixels as a TV draws
    them."""
    picture, border = picture_and_border
    w, h = 320, 246
    image = Image.new("RGB", (w, h), border)
    pw, ph = round(w * 0.82), round(h * 0.8)
    image.paste(picture.resize((pw, ph), Image.NEAREST), ((w - pw) // 2, (h - ph) // 2))
    return image


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    screens = dict(boot=text_screen(BOOT), press=text_screen(BOOT + ["LOAD", "", "PRESS PLAY ON TAPE"], False),
                   search=text_screen(BOOT + ["LOAD", "", "PRESS PLAY ON TAPE", "OK", "", "SEARCHING"], False),
                   found=text_screen(BOOT + ["LOAD", "", "PRESS PLAY ON TAPE", "OK", "", "SEARCHING",
                                             "FOUND ODYSSEY", "LOADING"], False),
                   title=title(), game_1=game(0), game_2=game(1))
    for name, screen in screens.items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(glass(screen).resize((w, h), Image.LANCZOS), (x, y))
    path = os.path.join(out, "plus4_media.png")
    image.save(path, optimize=True)
    print(path)


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), deck(), cassette(), tv_front()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", rgb(SL.COLOURS["bezel"])), ("silver", rgb(SL.COLOURS["handle"])),
                         ("red", (255, 40, 30))):
        x, y = SL.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    colours = dict(case=CASE, key=KEY, fkey=FKEY, deck=DECK, silver=SILVER, black=(18, 18, 20), lit=(230, 40, 34),
                   cassette=(30, 30, 34), tape=(60, 44, 32))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "plus4_print.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
