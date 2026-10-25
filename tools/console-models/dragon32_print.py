"""The Dragon 32 card's printing and screens (dragon32_print.png, dragon32_media.png), for the console theme's model
(dragon32.py).

`dragon32_print.png`, laid out as dragon32_layout.PRINT_REGIONS says: the Dragon's slope from above (the black keys'
tops and their white legends, the DRAGON 32 badge with the red dragon), the cartridge's label (a made-up game, Odyssey),
and swatches; the television's front (zx_spectrum_print.py's) and its swatches where zx_spectrum_layout.py puts them.
`dragon32_media.png`: the screens, the VDG's 256 x 192 in its black border: the start-up screen (black on green), the
game's title and two moments of it in the VDG's colours. Run it with the system Python (Pillow):

    python tools/console-models/dragon32_print.py <out folder>
"""

import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dragon32_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from vic20_print import chars  # noqa: E402
from windows_pc_print import Region  # noqa: E402
from zx_spectrum_print import tv_front  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
WHITE = (236, 236, 230)
RAINBOW = [(220, 40, 40), (240, 130, 30), (240, 210, 40), (60, 170, 60), (40, 120, 220), (130, 60, 180)]


def dragon(reg, x, y, h, fill):
    """The Dragon's mark, h tall, its middle at (x, y): a winged dragon in a few strokes."""
    k = h / 10.0
    reg.poly([(x - 5 * k, y + 3 * k), (x - 1 * k, y - 1 * k), (x + 2 * k, y - 5 * k), (x + 1 * k, y - 0.5 * k),
              (x + 5 * k, y - 3 * k), (x + 2.5 * k, y + 1 * k), (x + 4 * k, y + 4 * k), (x, y + 1.5 * k),
              (x - 2.5 * k, y + 4.5 * k)], fill)


def top():
    """The slope from above: x across (-WIDTH/2 at the left), y down from TOP to the front."""
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, L.TOP, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.TOP - y

    (bx0, bx1), (bs0, bs1) = L.BADGE["x"], L.BADGE["s"]
    y0, y1 = L.slope_point(bs0, 0.0)[0], L.slope_point(bs1, 0.0)[0]
    reg.rect_(*at(bx0, y1), *at(bx1, y0), (18, 18, 20), r=1.0)
    my = (y0 + y1) / 2
    dragon(reg, *at(bx0 + 18.0, my), 12.0, (220, 40, 40))
    x = bx0 + 58.0
    for c, colour in zip("DRAGON", RAINBOW):
        reg.text(c, "ariblk.ttf", 10.0, *at(x, my + 1.0), colour, anchor="lm")
        x += 8.6
    reg.text("32", "ariblk.ttf", 10.0, *at(x + 1.0, my + 1.0), WHITE, anchor="lm")
    reg.text("DATA LTD.", "arialbd.ttf", 1.8, *at(x - 14.0, my - 5.4), WHITE)

    top_h, inset = L.KEY["height"], L.KEY["inset"]
    for legend, x0, x1, s in L.keys():
        ya = L.slope_point(s - 9.5 + inset, top_h)[0]
        yb = L.slope_point(s + 9.5 - inset, top_h)[0]
        reg.rect_(*at(x0 + inset, yb), *at(x1 - inset, ya), KEY, r=1.2)
        x, y = at((x0 + x1) / 2, (ya + yb) / 2)
        if legend in L.SHIFTED:
            reg.text(L.SHIFTED[legend], "arial.ttf", 3.0, x, y - 2.6, WHITE)
            reg.text("Ø" if legend == "0" else legend, "arial.ttf", 3.8, x, y + 2.0, WHITE)
        elif len(legend) == 1 and legend != " ":
            reg.text(legend, "seguisym.ttf" if ord(legend) > 0x2000 else "arial.ttf", 4.4, x, y, WHITE)
        elif legend.strip():
            reg.text(legend, "arialbd.ttf", 2.4, x, y, WHITE)
    return reg


def cartridge():
    """The cartridge's top: x across (its width, along y in the model), y down from its outer end to the end going
    in."""
    length, w, _ = L.CART["size"]
    reg = Region(L.PRINT_REGIONS["cartridge"], w, length, (236, 232, 222))
    reg.rect_(6.0, 6.0, w - 6.0, length - 24.0, (20, 20, 26), r=1.5)
    art = space((440, 300)).convert("RGB")
    ship(ImageDraw.Draw(art), 140, 170, 3.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(8.0, 18.0, w - 8.0, length - 26.0)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 7.0, w / 2, 12.0, (255, 214, 70))
    dragon(reg, 12.0, length - 14.0, 8.0, (220, 40, 40))
    reg.text("DRAGON DATA", "arialbd.ttf", 4.0, 22.0, length - 14.0, (40, 40, 44), anchor="lm")
    return reg


# ---- The screens -----------------------------------------------------------------------------------------------------

VDG = dict(green=(0, 255, 0), dark=(0, 64, 0), yellow=(255, 255, 0), blue=(0, 0, 255), red=(255, 0, 0),
           buff=(255, 255, 255), cyan=(0, 255, 255), magenta=(255, 0, 255), orange=(255, 128, 0), black=(0, 0, 0))


def boot():
    """The start-up screen: the VDG's text, 32 columns of 16 rows 12 pixels tall, dark on green."""
    img = Image.new("RGB", L.VDG_PX, VDG["green"])
    for row, line in enumerate(["(C) 1982 DRAGON DATA LTD", "16K BASIC INTERPRETER 1.0", "(C) 1982 BY MICROSOFT", "",
                                "OK"]):
        chars(img, 0, row * 1.5, line, VDG["dark"])
    ImageDraw.Draw(img).rectangle([0, 60, 7, 71], fill=VDG["dark"])
    return img


def title():
    img = Image.new("RGB", L.VDG_PX, VDG["black"])
    d = ImageDraw.Draw(img)
    rng = random.Random(32)
    for _ in range(50):
        d.point((rng.randrange(256), rng.randrange(192)), fill=rng.choice([VDG["buff"], VDG["cyan"], VDG["yellow"]]))
    chars(img, 4, 2, "ODYSSEY", VDG["yellow"], scale=3)
    chars(img, 8, 6, "A SPACE TRIP", VDG["cyan"])
    d.ellipse([160, 90, 214, 144], fill=VDG["orange"])
    d.line([(144, 128), (232, 108)], fill=VDG["buff"], width=2)
    ship(d, 70, 118, 1.6, "#FFFFFF", "#FF0000")
    chars(img, 4, 21, "PRESS SPACE TO START", VDG["green"])
    return img


def game(frame):
    img = Image.new("RGB", L.VDG_PX, VDG["black"])
    d = ImageDraw.Draw(img)
    rng = random.Random(64)
    for _ in range(50):
        x, y = rng.randrange(256), rng.randrange(176)
        d.point(((x - frame * 10) % 256, y + 16), fill=VDG["buff"])
    chars(img, 0, 0, "SCORE 0%d40" % (frame + 1), VDG["yellow"])
    chars(img, 24, 0, "SHIPS 3", VDG["cyan"])
    d.ellipse([180 - 8 * frame, 70, 228 - 8 * frame, 118], fill=VDG["orange"])
    d.line([(166 - 8 * frame, 104), (242 - 8 * frame, 88)], fill=VDG["buff"], width=2)
    ship(d, 56, 100 + 14 * frame, 1.5, "#FFFFFF", "#FF0000")
    for k in range(3):
        d.line([(90 + 32 * k + 12 * frame, 100 + 14 * frame), (102 + 32 * k + 12 * frame, 100 + 14 * frame)],
               fill=VDG["yellow"], width=2)
    return img


def glass(picture):
    """A screen's region: the VDG's black border filling the glass, its picture in its middle."""
    w, h = 320, 246
    image = Image.new("RGB", (w, h), VDG["black"])
    pw, ph = round(w * 0.8), round(h * 0.8)
    image.paste(picture.resize((pw, ph), Image.NEAREST), ((w - pw) // 2, (h - ph) // 2))
    return image


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    for name, picture in (("boot", boot()), ("title", title()), ("game_1", game(0)), ("game_2", game(1))):
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(glass(picture).resize((w, h), Image.LANCZOS), (x, y))
    path = os.path.join(out, "dragon32_media.png")
    image.save(path, optimize=True)
    print(path)


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), cartridge(), tv_front()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", rgb(SL.COLOURS["bezel"])), ("silver", rgb(SL.COLOURS["handle"])),
                         ("red", (255, 40, 30))):
        x, y = SL.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    colours = dict(case=CASE, key=KEY, dark=(12, 12, 12), cart=(236, 232, 222), rib=(196, 186, 160))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "dragon32_print.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
