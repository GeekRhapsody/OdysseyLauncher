"""The Oric card's printing and screens (oric_print.png, oric_media.png), for the console theme's model (oric.py).

`oric_print.png`, laid out as oric_layout.PRINT_REGIONS says: the Atmos from above (the keys' tops and legends, the red
ones, the grille's holes, the ORIC ATMOS 48K badge, the ports' names along the back), the recorder's top (its silver
plate, the lid's window, the piano keys' names, the speaker's slots, the counter), the cassette's label (a made-up game,
Odyssey), and swatches; the television's front (zx_spectrum_print.py's) and its swatches where zx_spectrum_layout.py
puts them. `oric_media.png`: the screens, the Oric's 240 x 224 in its black border: Ready with the status line, CLOAD""
and Searching, Loading ODYSSEY, the title and two moments of the game. Run it with the system Python (Pillow):

    python tools/console-models/oric_print.py <out folder>
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oric_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402
from zx_spectrum_print import tv_front  # noqa: E402

SHELL = rgb(L.COLOURS["shell"])
KEY = rgb(L.COLOURS["key"])
RED = rgb(L.COLOURS["red"])
RECORDER = rgb(L.COLOURS["recorder"])
WHITE = (236, 236, 230)
SILVER = (176, 178, 182)


def shade(colour, k):
    return tuple(max(0, min(255, round(c * (1 + k)))) for c in colour)


def oric_logo(reg, x, y, h, ink, slash):
    """ORIC, h tall, its middle at (x, y): the O struck through by the red slash."""
    reg.text("ORIC", "ariblk.ttf", h, x, y, ink)
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(h * reg.sy)))
    w = reg.draw.textlength("ORIC", font=f) / reg.sx
    ox = x - w / 2 + 0.33 * h
    reg.poly([(ox - 0.42 * h, y + 0.36 * h), (ox + 0.36 * h, y - 0.42 * h), (ox + 0.48 * h, y - 0.3 * h),
              (ox - 0.3 * h, y + 0.48 * h)], slash)


# ---- The print -------------------------------------------------------------------------------------------------------

def top():
    """The Atmos from above: x across (-WIDTH/2 at the left), y down from the back to the front."""
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH, SHELL)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    (gx0, gx1), (gy0, gy1), cols, rows = L.GRILLE["x"], L.GRILLE["y"], L.GRILLE["columns"], L.GRILLE["rows"]
    for r in range(rows):
        for c in range(cols):
            x = gx0 + (gx1 - gx0) * c / (cols - 1)
            y = gy0 + (gy1 - gy0) * r / (rows - 1)
            reg.circle(*at(x, y), 1.0, (4, 4, 5))
            reg.circle(*at(x - 0.25, y + 0.25), 0.55, (60, 60, 66))
    (bx0, bx1), (by0, by1) = L.BADGE["x"], L.BADGE["y"]
    reg.rect_(*at(bx0, by1), *at(bx1, by0), None, r=0.6, outline=(200, 200, 196), width=0.35)
    oric_logo(reg, *at((bx0 + bx1) / 2, by1 - 6.0), 8.0, WHITE, RED)
    reg.text("A T M O S   48K", "arialbd.ttf", 2.4, *at((bx0 + bx1) / 2, by0 + 3.0), WHITE)
    for k, name in enumerate(L.PORTS):
        reg.text(name, "arial.ttf", 1.7, *at(-105.0 + k * 44.0, L.DEPTH - 1.6), (110, 110, 116))

    top_h, inset = L.KEY["height"], L.KEY["inset"]
    for legend, x0, x1, y in L.keys():
        s = L.plan_s(y)
        ya = L.deck_point(s - 9.5 + inset, top_h - L.WELL["depth"])[0]
        yb = L.deck_point(s + 9.5 - inset, top_h - L.WELL["depth"])[0]
        red = legend in L.RED
        reg.rect_(*at(x0 + inset, yb), *at(x1 - inset, ya), RED if red else KEY, r=1.2)
        x, yy = at((x0 + x1) / 2, (ya + yb) / 2)
        if red:
            reg.text(legend, "seguisym.ttf" if ord(legend[0]) > 0x2000 else "arialbd.ttf",
                     3.8 if len(legend) == 1 else 1.9, x, yy, WHITE)
        elif legend in L.SHIFTED:
            reg.text(L.SHIFTED[legend], "arialbd.ttf", 3.0, x, yy - 2.4, WHITE)
            reg.text("Ø" if legend == "0" else legend, "arialbd.ttf", 3.4, x, yy + 2.0, WHITE)
        elif legend.strip():
            reg.text(legend, "arialbd.ttf", 4.2, x, yy, WHITE)
    return reg


def recorder():
    """The recorder from above: x from its left, y down from its back to its front."""
    w, d, _ = L.RECORDER["size"]
    reg = Region(L.PRINT_REGIONS["recorder"], w, d, RECORDER)

    def at(x, y):
        return x, d - y

    (px0, px1), (py0, py1) = L.PLATE["x"], L.PLATE["y"]
    reg.rect_(*at(px0, py1), *at(px1, py0), SILVER, r=4.0)
    (lx0, lx1), (ly0, ly1) = L.LID["x"], L.LID["y"]
    reg.rect_(*at(lx0 - 2.0, ly1 + 2.0), *at(lx1 + 2.0, ly0 - 2.0), (36, 36, 38), r=2.0)
    reg.rect_(*at(lx0 + 8.0, ly1 - 8.0), *at(lx1 - 8.0, ly0 + 14.0), (66, 68, 72), r=2.0)
    reg.text("DATA RECORDER", "arialbd.ttf", 3.6, *at((lx0 + lx1) / 2, ly0 + 7.0), (230, 230, 226))
    (kx0, kx1) = L.PIANO["x"]
    kw = (kx1 - kx0) / 6
    for k, name in enumerate(L.PIANO["names"]):
        reg.text(name, "arial.ttf", 2.4, *at(kx0 + (k + 0.5) * kw, L.PIANO["y"][1] + 3.6), (50, 50, 54))
    (sx0, sx1), (sy0, sy1), n = L.SPEAKER["x"], L.SPEAKER["y"], L.SPEAKER["count"]
    for k in range(n):
        y = sy0 + (sy1 - sy0) * (k + 0.5) / n
        reg.rect_(*at(sx0, y + 2.0), *at(sx1, y - 2.0), (30, 30, 32), r=2.0)
    (cx0, cx1), (cy0, cy1) = L.COUNTER["x"], L.COUNTER["y"]
    reg.rect_(*at(cx0, cy1), *at(cx1, cy0), (14, 14, 14), r=1.0)
    for k in range(3):
        reg.rect_(*at(cx0 + 3.0 + 9.4 * k, cy1 - 2.5), *at(cx0 + 10.6 + 9.4 * k, cy0 + 2.5), (232, 232, 228))
        reg.text("0", "arialbd.ttf", 7.0, *at(cx0 + 6.8 + 9.4 * k, (cy0 + cy1) / 2), (20, 20, 20))
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
    reg.text("ODYSSEY", "ariblk.ttf", 7.0, w / 2, 28.5, (190, 30, 30))
    reg.rect_(26.0, 33.0, w - 26.0, 47.0, (60, 60, 66), r=3.0)
    for x in (36.0, w - 36.0):
        reg.circle(x, 40.0, 5.5, (240, 236, 224))
        reg.circle(x, 40.0, 2.6, (40, 40, 44))
    reg.rect_(32.0, h - 9.0, w - 32.0, h - 2.0, (24, 24, 26))
    return reg


# ---- The screens -----------------------------------------------------------------------------------------------------

ORIC = dict(black=(0, 0, 0), red=(255, 0, 0), green=(0, 255, 0), yellow=(255, 255, 0), blue=(0, 0, 255),
            magenta=(255, 0, 255), cyan=(0, 255, 255), white=(255, 255, 255))
FONT = ImageFont.truetype(FONTS + "consolab.ttf", 8)
BOOT = ["ORIC EXTENDED BASIC V1.1", "© 1983 TANGERINE", "", " 37631 BYTES FREE", "", "Ready"]


def text(img, col, row, s, ink, scale=1):
    """Text in the Oric's character cells, 6 x 8 pixels each (times scale)."""
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    f = FONT if scale == 1 else ImageFont.truetype(FONTS + "consolab.ttf", 8 * scale)
    for k, ch in enumerate(s):
        d.text(((col + k * scale) * 6 + 3 * scale, row * 8 + 4 * scale), ch, font=f, fill=ink, anchor="mm")


def console(lines, status="", cursor=True):
    """The text screen: the status line at the top (its message at the left, CAPS at the right), the lines under it."""
    img = Image.new("RGB", L.ORIC_PX, ORIC["black"])
    text(img, 1, 0, status, ORIC["white"])
    text(img, 35, 0, "CAPS", ORIC["white"])
    for row, line in enumerate(lines):
        text(img, 1, row + 1, line, ORIC["white"])
    if cursor:
        ImageDraw.Draw(img).rectangle([6, (len(lines) + 1) * 8, 11, (len(lines) + 1) * 8 + 7], fill=ORIC["white"])
    return img


def title():
    img = Image.new("RGB", L.ORIC_PX, ORIC["black"])
    d = ImageDraw.Draw(img)
    rng = random.Random(84)
    for _ in range(60):
        d.point((rng.randrange(240), rng.randrange(224)),
                fill=rng.choice([ORIC["white"], ORIC["cyan"], ORIC["yellow"]]))
    text(img, 7, 2, "ODYSSEY", ORIC["yellow"], scale=3)
    text(img, 13, 6, "A SPACE TRIP", ORIC["cyan"])
    d.ellipse([140, 100, 196, 156], fill=ORIC["red"])
    d.ellipse([146, 106, 186, 144], fill=ORIC["yellow"])
    d.line([(124, 140), (214, 118)], fill=ORIC["white"], width=2)
    ship(d, 62, 128, 1.6, "#FFFFFF", "#FF0000")
    text(img, 9, 24, "PRESS SPACE TO START", ORIC["green"])
    return img


def game(frame):
    img = Image.new("RGB", L.ORIC_PX, ORIC["black"])
    d = ImageDraw.Draw(img)
    rng = random.Random(48)
    for _ in range(60):
        x, y = rng.randrange(240), rng.randrange(206)
        d.point(((x - frame * 10) % 240, y + 18), fill=ORIC["white"])
    text(img, 1, 0, "SCORE 0%d40" % (frame + 1), ORIC["yellow"])
    text(img, 31, 0, "SHIPS 3", ORIC["cyan"])
    d.ellipse([168 - 8 * frame, 76, 216 - 8 * frame, 124], fill=ORIC["red"])
    d.line([(154 - 8 * frame, 110), (230 - 8 * frame, 92)], fill=ORIC["white"], width=2)
    ship(d, 52, 106 + 14 * frame, 1.5, "#FFFFFF", "#FF0000")
    for k in range(3):
        d.line([(86 + 30 * k + 12 * frame, 106 + 14 * frame), (98 + 30 * k + 12 * frame, 106 + 14 * frame)],
               fill=ORIC["yellow"], width=2)
    return img


def glass(picture):
    """A screen's region: the black border filling the glass, the Oric's picture in its middle."""
    w, h = 320, 246
    image = Image.new("RGB", (w, h), ORIC["black"])
    pw, ph = round(w * 0.8), round(h * 0.86)
    image.paste(picture.resize((pw, ph), Image.NEAREST), ((w - pw) // 2, (h - ph) // 2))
    return image


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    screens = dict(boot=console(BOOT), search=console(BOOT + ["CLOAD\"\""], "Searching ..", False),
                   loading=console(BOOT + ["CLOAD\"\""], "Loading .. ODYSSEY", False), title=title(), game_1=game(0),
                   game_2=game(1))
    for name, picture in screens.items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(glass(picture).resize((w, h), Image.LANCZOS), (x, y))
    path = os.path.join(out, "oric_media.png")
    image.save(path, optimize=True)
    print(path)


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), SHELL)
    for reg in (top(), recorder(), cassette(), tv_front()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", rgb(SL.COLOURS["bezel"])), ("silver", rgb(SL.COLOURS["handle"])),
                         ("red", (255, 40, 30))):
        x, y = SL.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    colours = dict(shell=SHELL, base=rgb(L.COLOURS["base"]), key=KEY, red=RED, recorder=RECORDER, silver=SILVER,
                   black=(14, 14, 16), cassette=(30, 30, 34), lit=(255, 60, 40))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "oric_print.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
