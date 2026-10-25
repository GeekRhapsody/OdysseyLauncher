"""The Commodore VIC-20's printing, for the console theme's VIC-20 model (tools/console-models/vic20.py).

Draws its two atlases, their regions as vic20_layout.py places them. vic20_print.png: the computer seen from above, in
millimetres as the model's planar UVs map it (each key's top in its colour with its legends, the badge with commodore
and the gold VIC 20 plate, the power light, the ribs along the back); the cartridge's label (a made-up game, Odyssey);
the television's front (zx_spectrum_print.py's, where its layout puts it) and the swatches small parts take their
colour from. vic20_media.png: the glass's screens, the VIC's 176 x 184 pixels in the middle of its border (the
screen it starts on, CBM BASIC V2, 3583 BYTES FREE and READY. in blue on white inside the cyan border; the title
screen of Odyssey) and a black swatch. Run it with the system Python (Pillow):

    python tools/console-models/vic20_print.py <out folder>

It writes vic20_print.png and vic20_media.png there.
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vic20_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402
from zx_spectrum_print import tv_front  # noqa: E402

CASE = rgb(L.COLOURS["case"])
KEY = rgb(L.COLOURS["key"])
TAN = rgb(L.COLOURS["tan"])
WHITE = (244, 242, 236)


def top_point(x, y):
    return x + L.WIDTH / 2, L.DEPTH - y


def slope_top(points, h):
    """An (x, s) outline on the top, raised h off it, in the top region's millimetres."""
    return [top_point(x, L.top_point(s, h)[0]) for x, s in points]


# ---- The keys ----------------------------------------------------------------------------------------------------------

def cbm_logo(reg, x, y, s, fill, cut):
    """Commodore's mark, s across, its middle at (x, y): the C, and its two flags."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    r0, r1 = 0.5 * s, 0.29 * s
    d.ellipse(reg.box(x - r0, y - r0, x + r0, y + r0), fill=fill + (255,))
    d.ellipse(reg.box(x - r1, y - r1, x + r1, y + r1), fill=cut + (255,))
    d.rectangle(reg.box(x, y - 0.23 * s, x + r0 + 1, y + 0.23 * s), fill=cut + (255,))
    reg.over(layer)
    for top, bottom in ((-0.21 * s, -0.03 * s), (0.03 * s, 0.21 * s)):
        reg.poly([(x + 0.06 * s, y + top), (x + 0.5 * s, y + top), (x + 0.5 * s - (bottom - top), y + bottom),
                  (x + 0.06 * s, y + bottom)], fill)


def graphics(reg, x, y, k):
    """The two PETSCII graphics under a letter: small squares, each part filled, varying with the key."""
    rng = random.Random(k)
    for i in range(2):
        x0 = x - 3.2 + i * 3.6
        reg.rect_(x0, y - 1.3, x0 + 2.8, y + 1.3, None, outline=WHITE, width=0.22)
        kind = rng.randrange(4)
        if kind == 0:
            reg.rect_(x0, y - 1.3, x0 + 1.4, y + 1.3, WHITE)
        elif kind == 1:
            reg.rect_(x0, y, x0 + 2.8, y + 1.3, WHITE)
        elif kind == 2:
            reg.circle(x0 + 1.4, y, 0.8, WHITE)
        else:
            reg.line([(x0, y + 1.3), (x0 + 2.8, y - 1.3)], WHITE, 0.25)


def key_top(reg, name, outline, colour, legend, k):
    i = L.KEY_INSET
    (x0, s0), (x1, s1) = outline[0], outline[2]
    pts = slope_top([(x0 + i, s0 + i), (x1 - i, s0 + i), (x1 - i, s1 - i), (x0 + i, s1 - i)], L.KEY_HEIGHT)
    fill = shade(KEY if colour == "brown" else TAN, 0.08)
    reg.poly(pts, fill)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ax, ay, bx, by = min(xs), min(ys), max(xs), max(ys)
    cx, cy = (ax + bx) / 2, (ay + by) / 2
    ink = WHITE if colour == "brown" else (74, 52, 30)
    if not legend:
        return
    if name == "cbm":
        cbm_logo(reg, cx, cy, 7.0, ink, fill)
        return
    lines = legend.split("\n")
    if len(lines) == 1 and len(legend) == 1 and legend.isalpha():
        reg.text(legend, "arialbd.ttf", 4.6, cx, cy - 2.2, ink)
        graphics(reg, cx, cy + 3.0, k)
        return
    if name.startswith("d") and len(lines) == 3:          # the digits: the shifted symbol, the digit, the colour
        reg.text(lines[0], "arialbd.ttf", 3.0, cx, cy - 4.2, ink)
        reg.text(lines[1], "arialbd.ttf", 4.0, cx, cy - 0.6, ink)
        reg.text(lines[2], "arialbd.ttf", 2.4, cx, cy + 3.6, ink)
        return
    if name == "d0":
        reg.text(lines[0], "arialbd.ttf", 4.0, cx, cy - 2.0, ink)
        reg.text(lines[1], "arialbd.ttf", 2.2, cx, cy + 2.6, ink)
        return
    size = 2.6 if max(len(line) for line in lines) > 3 else 3.6
    font = "seguisym.ttf" if not legend.isascii() else "arialbd.ttf"
    for j, line in enumerate(lines):
        reg.text(line, "seguisym.ttf" if not line.isascii() else font, size, cx,
                 cy + (j - (len(lines) - 1) / 2) * (size + 0.6), ink)


def keys(reg):
    for k, (name, xu, row, wu, colour, legend) in enumerate(L.KEYS):
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        key_top(reg, name, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], colour, legend, k)
    for name, row, legend in L.FKEYS:
        x0, s0 = L.FKEYS_X + L.GAP / 2, L.ROW_S[row] + L.GAP / 2
        x1, s1 = L.FKEYS_X + L.FKEY_W * L.U - L.GAP / 2, L.ROW_S[row] + L.U - L.GAP / 2
        key_top(reg, name, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], "tan", legend, 0)


# ---- The top -----------------------------------------------------------------------------------------------------------

def badge(reg):
    (x0, x1), (s0, s1), (p0, p1) = L.BADGE["x"], L.BADGE["s"], L.BADGE["plate"]
    (_, y1), (_, y0) = top_point(0, L.top_point(s0, 0)[0]), top_point(0, L.top_point(s1, 0)[0])
    ax, bx = top_point(x0, 0)[0], top_point(p0, 0)[0]
    h = y1 - y0
    reg.rect_(ax, y0, bx + h / 2, y1, (20, 20, 22), r=h / 2)
    cbm_logo(reg, ax + h * 0.8, (y0 + y1) / 2, h * 0.62, (236, 236, 236), (20, 20, 22))
    reg.text("commodore", "arialbd.ttf", h * 0.72, ax + h * 1.4, (y0 + y1) / 2, (236, 236, 236), anchor="lm")
    px0, px1 = top_point(p0, 0)[0], top_point(p1, 0)[0]
    gold = (196, 170, 112)
    reg.poly([(px0, y0), (px1, y0), (px1 - h * 0.5, y1), (px0 - h * 0.5, y1)], gold)
    reg.text("VIC", "arialbd.ttf", h * 0.8, px0 + h * 1.6, (y0 + y1) / 2 - h * 0.08, (30, 26, 20))
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(h * 0.8 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(px0 + h * 3.3, (y0 + y1) / 2 - h * 0.08), "20", font=f, fill=gold + (255,),
                               anchor="mm", stroke_width=max(1, round(0.25 * reg.sx)), stroke_fill=(30, 26, 20, 255))
    reg.over(layer)
    reg.text("COMPUTER", "arialbd.ttf", h * 0.22, px0 + h * 2.4, y1 - h * 0.14, (30, 26, 20))


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)
    for s in L.RIBS["s"]:                                    # the ribs along the back
        y = top_point(0, L.top_point(s, 0)[0])[1]
        reg.line([(4.0, y), (L.WIDTH - 4.0, y)], shade(CASE, -0.16), 0.9)
        reg.line([(4.0, y + 0.9), (L.WIDTH - 4.0, y + 0.9)], shade(CASE, 0.08), 0.5)
    badge(reg)
    lx, ly = top_point(L.LIGHT["x"], L.top_point(L.LIGHT["s"], 0)[0])
    reg.rect_(lx - 16.0, ly - 3.0, lx + 4.0, ly + 3.0, shade(CASE, -0.05), r=3.0)
    reg.text("POWER", "arialbd.ttf", 2.6, lx - 7.0, ly, (70, 66, 58))
    reg.circle(lx, ly, L.LIGHT["r"] + 0.4, (40, 24, 20))
    reg.circle(lx, ly, L.LIGHT["r"], (110, 26, 22))
    keys(reg)
    return reg


def label():
    lw, ld = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, ld, rgb(L.COLOURS["cart"]))
    brown, orange, tan = (90, 52, 30), (214, 120, 40), (226, 184, 120)
    reg.rect_(2.0, 2.0, lw - 2.0, ld - 2.0, None, outline=brown, width=1.0)
    for k, colour in enumerate((tan, orange, brown)):                      # the stripes across it, at a slant
        y = 22.0 + k * 5.0
        reg.poly([(4.0, y), (lw - 4.0, y - 9.0), (lw - 4.0, y - 5.5), (4.0, y + 3.5)], colour)
    cbm_logo(reg, 9.0, 9.0, 6.0, (40, 40, 44), rgb(L.COLOURS["cart"]))
    reg.text("commodore", "arialbd.ttf", 4.4, 14.0, 9.0, (40, 40, 44), anchor="lm")
    art = space((520, 220))
    d = ImageDraw.Draw(art)
    ship(d, 150, 110, 2.6, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(6.0, 34.0, lw - 6.0, ld - 6.0)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 9.0, lw / 2 + 14.0, 44.0, (255, 214, 70))
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), label(), tv_front()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", rgb(SL.COLOURS["bezel"])), ("silver", rgb(SL.COLOURS["handle"])),
                         ("red", (255, 40, 30))):
        x, y = SL.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    for name, colour in (("red", (255, 40, 30)), ("lit", (255, 60, 40)), ("dark", rgb(L.COLOURS["dark"])),
                         ("cart", rgb(L.COLOURS["cart"])), ("key", KEY), ("tan", TAN)):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "vic20_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -------------------------------------------------------------------------------------------------------

VIC = dict(black=(0, 0, 0), white=(255, 255, 255), red=(182, 31, 33), cyan=(77, 240, 255), purple=(180, 63, 255),
           green=(68, 226, 55), blue=(26, 52, 255), yellow=(220, 209, 78), orange=(202, 84, 0))
FONT = ImageFont.truetype(FONTS + "consolab.ttf", 10)


def chars(img, col, row, text, ink, scale=1):
    """Text in the VIC's character cells, 8 x 8 pixels each (times scale)."""
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    f = FONT if scale == 1 else ImageFont.truetype(FONTS + "consolab.ttf", 10 * scale)
    for k, ch in enumerate(text):
        d.text(((col + k * scale) * 8 + 4 * scale, row * 8 + 4 * scale), ch, font=f, fill=ink, anchor="mm")


def boot():
    img = Image.new("RGB", L.VIC_PX, VIC["white"])
    chars(img, 0, 0, "**** CBM BASIC V2 ****", VIC["blue"])
    chars(img, 0, 1, "3583 BYTES FREE", VIC["blue"])
    chars(img, 0, 3, "READY.", VIC["blue"])
    ImageDraw.Draw(img).rectangle([0, 32, 7, 39], fill=VIC["blue"])
    return img, VIC["cyan"]


def title():
    img = Image.new("RGB", L.VIC_PX, VIC["black"])
    d = ImageDraw.Draw(img)
    rng = random.Random(20)
    for _ in range(40):
        d.point((rng.randrange(176), rng.randrange(184)), fill=rng.choice([VIC["white"], VIC["cyan"], VIC["yellow"]]))
    chars(img, 1, 1, "ODYSSEY", VIC["yellow"], scale=2)
    chars(img, 2, 4, "A SPACE TRIP", VIC["cyan"])
    d.ellipse([110, 96, 158, 144], fill=VIC["orange"])
    d.ellipse([116, 100, 150, 130], fill=VIC["yellow"])
    d.line([(96, 124), (172, 112)], fill=VIC["white"], width=2)
    ship(d, 60, 116, 1.4, VIC["white"], VIC["red"])
    chars(img, 2, 20, "PRESS F1 TO START", VIC["green"])
    return img, VIC["purple"]


def glass(picture_and_border):
    """A screen's region: the border filling the glass, the VIC's picture in its middle, its pixels wide as a TV draws
    them."""
    picture, border = picture_and_border
    w, h = L.SCREEN_PX
    image = Image.new("RGB", (w, h), border)
    pw, ph = round(w * 0.62), round(h * 0.8)
    image.paste(picture.resize((pw, ph), Image.NEAREST), ((w - pw) // 2, (h - ph) // 2))
    return image


def media_atlas(out):
    image = Image.new("RGB", (1024, 1024), (0, 0, 0))
    for name, screen in (("boot", boot()), ("title", title())):
        x, y, _, _ = L.MEDIA_REGIONS[name]
        image.paste(glass(screen), (x, y))
    path = os.path.join(out, "vic20_media.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
