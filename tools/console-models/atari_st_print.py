"""The Atari 520STFM's, its SC1224's and its mouse's printing, for the console theme's Atari ST model
(tools/console-models/atari_st.py).

Draws its two atlases, their regions as atari_st_layout.py places them. atari_st_print.png: the computer seen from
above, in millimetres as the model's planar UVs map it (each key's top with its legend, the function keys' blades,
the badge, the power light lit and the drive light off), the monitor's badge (ATARI and SC1224), the mouse's back, and
the swatches small parts take their colour from. atari_st_media.png: the screens, each the glass's whole width and
height, a dark border round the ST's 320 x 200 (GEM's desktop as TOS shows it, green, its two floppy disks and the
trash; the floppy's window open over it, ODYSSEY.PRG chosen; and the title screen of a made-up game, Odyssey), and the
floppy's two sides. Run it with the system Python (Pillow):

    python tools/console-models/atari_st_print.py <out folder>

It writes atari_st_print.png and atari_st_media.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari_st_layout as L  # noqa: E402
from msx_layout import inset  # noqa: E402
from psp_print import ship  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
LEGEND = (70, 68, 62)
BLUE = (40, 120, 220)


def top_point(x, y):
    """A point of the computer (x from its middle, y back from its front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


def fuji(reg, x, y, size, colour):
    """Atari's mark, size tall, its middle at (x, y): three columns, the outer two flaring out at their feet."""
    s = size
    reg.rect_(x - 0.08 * s, y - 0.5 * s, x + 0.08 * s, y + 0.5 * s, colour)
    for side in (-1, 1):
        pts = [(x + side * 0.16 * s, y - 0.5 * s), (x + side * 0.3 * s, y - 0.5 * s), (x + side * 0.3 * s, y - 0.05 * s),
               (x + side * 0.58 * s, y + 0.5 * s), (x + side * 0.4 * s, y + 0.5 * s), (x + side * 0.16 * s, y + 0.05 * s)]
        reg.poly(pts, colour)


def slanted(reg, text, font, size, x, y, fill, shear=0.18, anchor="lm"):
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(x, y), text, font=f, fill=fill + (255,), anchor=anchor)
    yc = reg.p(0, y)[1]
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, shear, -shear * yc, 0, 1, 0)))


def badge_plate(reg, x0, y0, x1, y1, model):
    """The slanted plate: Atari's mark and ATARI in blue, the model in black, on silver."""
    lean = (y1 - y0) * 0.9
    reg.poly([(x0 + lean, y0), (x1, y0), (x1 - lean, y1), (x0, y1)], (224, 226, 228))
    h = y1 - y0
    fuji(reg, x0 + lean + 2.6, (y0 + y1) / 2, h * 0.62, (30, 30, 34))
    slanted(reg, "ATARI", "arialbd.ttf", h * 0.8, x0 + lean + 6.4, (y0 + y1) / 2, BLUE, shear=0.0)
    slanted(reg, model, "arialbd.ttf", h * 0.82, x1 - lean - 1.0, (y0 + y1) / 2, (30, 30, 34), anchor="rm")


# ---- The computer's top ----------------------------------------------------------------------------------------------

def deck_top(points, h):
    """An (x, s) outline on the deck, raised h off it, in the top region's millimetres."""
    return [top_point(x, L.deck_point(s, h)[0]) for x, s in points]


def key_top(reg, name, outline, legend):
    fill = rgb(L.COLOURS["top_keys"])
    xs = [x for x, _ in outline]
    ss = [s for _, s in outline]
    i = L.KEY_INSET
    inner = [(min(xs) + i, min(ss) + i), (max(xs) - i, min(ss) + i), (max(xs) - i, max(ss) - i), (min(xs) + i, max(ss) - i)]
    if name == "return":
        inner = inset(outline, i)
    pts = deck_top(inner, L.KEY_HEIGHT)
    reg.poly(pts, fill)
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    if name != "return":
        reg.rect_(x0 + 0.9, y0 + 0.9, x1 - 0.9, y1 - 0.9, shade(fill, 0.04), r=1.2)
    if not legend:
        return
    lines = legend.split("\n")
    if name == "return":
        x0 = top_point(L.kx(L.RETURN["foot"][0]), 0.0)[0]
        y0 = deck_top([(0.0, L.ROW_S[3] + L.U - i)], L.KEY_HEIGHT)[0][1]
        reg.text("Return", "arial.ttf", 2.1, x0 + 1.8, y0 + 2.6, LEGEND, anchor="lm")
        return
    if len(lines) == 1 and len(legend) == 1 and not legend.isalnum() and name.startswith(("up", "down", "left", "right")):
        reg.text(legend, "seguisym.ttf", 3.6, (x0 + x1) / 2, (y0 + y1) / 2, LEGEND)
        return
    if len(lines) == 1 and len(legend) == 1:
        reg.text(legend, "arial.ttf", 3.6 if legend.isalpha() else 3.2, (x0 + x1) / 2 if name.startswith("np")
                 else x0 + 2.6, (y0 + y1) / 2 if name.startswith("np") else y0 + 3.0, LEGEND)
        return
    size = 2.1 if max(len(line) for line in lines) > 2 else 2.8
    for k, line in enumerate(lines):
        reg.text(line, "arial.ttf", size, x0 + 1.6, y0 + 2.4 + k * (size + 1.1), LEGEND, anchor="lm")


def band_top(points):
    """An (x, s) outline on the band's face, in the top region's millimetres."""
    return [top_point(x, L.band_point(s, 0.0)[0]) for x, s in points]


def fkey_outline(k):
    f = L.FKEYS
    x0 = f["x0"] + k * f["width"]
    x1 = x0 + f["width"] - f["gap"]
    (s0, s1), lean = f["s"], f["lean"]
    return [(x0, s0), (x1, s0), (x1 + lean, s1), (x0 + lean, s1)]


def top():
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH, CASE)
    (vx0, vx1), (vy0, vy1) = L.VENT["x"], L.VENT["y"]
    vent = rgb(L.COLOURS["vent"])
    reg.rect_(*top_point(vx0, vy1), *top_point(vx1, vy0), vent)
    layer = reg.layer()                                     # the grooves' floors, darker, at 45 degrees (x - y constant)
    d = ImageDraw.Draw(layer)
    h = L.VENT["width"] / math.sqrt(2)
    c = vx0 - vy1
    while c < vx1 - vy0:
        d.polygon([reg.p(*top_point(x, y)) for x, y in ((vy0 + c - h, vy0), (vy0 + c + h, vy0), (vy1 + c + h, vy1),
                                                         (vy1 + c - h, vy1))], fill=shade(vent, -0.3) + (255,))
        c += L.VENT["pitch"] * math.sqrt(2)
    mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(mask).rectangle(reg.box(*top_point(vx0, vy1), *top_point(vx1, vy0)), fill=255)
    reg.img.paste(layer, (0, 0), Image.composite(layer.getchannel("A"), Image.new("L", layer.size, 0), mask))
    for name, xu, row, wu, legend, *rest in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu, rest[0] if rest else 1)
        key_top(reg, name, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], legend)
    key_top(reg, "return", L.return_outline(), "Return")

    # The function keys: slanted blades, each a shade lighter at its top, its name at its foot.
    for k in range(10):
        pts = band_top(fkey_outline(k))
        reg.poly(pts, shade(CASE, 0.08))
        a, b = pts[0], pts[1]
        reg.line([a, b], shade(CASE, -0.3), 0.3)
        reg.text(f"F{k + 1}", "arial.ttf", 1.9, (pts[0][0] + pts[3][0]) / 2 + 4.0, (pts[0][1] + pts[3][1]) / 2 + 0.6,
                 shade(CASE, -0.25))

    (bx0, bx1), (bs0, bs1) = L.BADGE["x"], L.BADGE["s"]
    (_, by1), (_, by0) = top_point(0, L.band_point(bs0, 0)[0]), top_point(0, L.band_point(bs1, 0)[0])
    badge_plate(reg, top_point(bx0, 0)[0], by0, top_point(bx1, 0)[0], by1, "520STFM")
    w, d = L.LIGHTS["size"]
    for name, colour, on in (("drive", (110, 48, 30), False), ("power", (120, 255, 110), True)):
        x, s = L.LIGHTS[name]
        y = L.band_point(s, 0)[0] if name == "drive" else L.deck_point(s, 0)[0]
        cx, cy = top_point(x, y)
        if on:
            glow = reg.layer()
            ImageDraw.Draw(glow).rounded_rectangle(reg.box(cx - w / 2 - 2, cy - d - 1, cx + w / 2 + 2, cy + d + 1),
                                                   radius=2 * reg.sx, fill=colour + (110,))
            reg.over(glow.filter(ImageFilter.GaussianBlur(1.2 * reg.sx)))
        reg.rect_(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2, colour, r=0.4)
    return reg


def monitor_badge():
    b = L.MONITOR["badge"]
    w, h = b["x"][1] - b["x"][0], b["z"][1] - b["z"][0]
    reg = Region(L.PRINT_REGIONS["badge"], w, h, rgb(L.COLOURS["monitor"]))
    fuji(reg, 4.0, h / 2, h * 0.6, (40, 40, 44))
    reg.text("ATARI", "arialbd.ttf", h * 0.62, 8.0, h / 2, BLUE, anchor="lm")
    lean = h * 0.7
    reg.poly([(44.0 + lean, 1.5), (w - 2.0, 1.5), (w - 2.0 - lean, h - 1.5), (44.0, h - 1.5)], (205, 208, 206))
    slanted(reg, "SC1224", "arialbd.ttf", h * 0.6, w - 6.0 - lean, h / 2, (70, 72, 76), anchor="rm")
    return reg


def mouse_top():
    w, d, _ = L.MOUSE["size"]
    reg = Region(L.PRINT_REGIONS["mouse"], w, d, rgb(L.COLOURS["case"]))
    b = L.MOUSE["buttons"]
    reg.rect_(0.0, 0.0, w, b, shade(CASE, 0.05))
    reg.rect_(w / 2 - 0.4, 0.0, w / 2 + 0.4, b, shade(CASE, -0.35))
    reg.rect_(0.0, b - 0.4, w, b + 0.4, shade(CASE, -0.35))
    fuji(reg, w / 2, d - 20.0, 9.0, shade(CASE, -0.2))
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), monitor_badge(), mouse_top()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("lit", (255, 150, 60)), ("off", (110, 48, 30)), ("green", (120, 255, 110)),
                         ("dark", rgb(L.COLOURS["dark"])), ("vent", rgb(L.COLOURS["vent"])),
                         ("monitor", rgb(L.COLOURS["monitor"]))):
        x, y = L.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "atari_st_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -----------------------------------------------------------------------------------------------------

WHITE, BLACK = (255, 255, 255), (0, 0, 0)
GREEN = (0, 219, 0)                    # the ST's desktop green: 0, 7, 0 on its 3-bit scale, a shade under full
FONT = ImageFont.truetype(FONTS + "consolab.ttf", 9)


def st_text(d, x, y, s, fill):
    d.text((x, y), s, font=FONT, fill=fill, anchor="lm")


def pointer(d, x, y):
    arrow = [(0, 0), (0, 11), (3, 8), (5, 13), (7, 12), (5, 7), (9, 7)]
    d.polygon([(x + a, y + b) for a, b in arrow], fill=BLACK, outline=WHITE)


def caption(d, x, y, text, inverted=False):
    w = len(text) * 5 + 4
    d.rectangle([x - w // 2, y - 4, x + w // 2, y + 4], fill=BLACK if inverted else WHITE)
    small = ImageFont.truetype(FONTS + "consola.ttf", 7)
    d.text((x, y), text, font=small, fill=WHITE if inverted else BLACK, anchor="mm")


def disk_icon(d, x, y, letter):
    """TOS's floppy disk: a drawer, its slot and its letter, its name under it."""
    d.rectangle([x - 12, y - 10, x + 12, y + 8], fill=WHITE, outline=BLACK)
    d.rectangle([x - 9, y - 7, x + 9, y + 1], outline=BLACK)
    d.rectangle([x - 5, y + 3, x + 5, y + 5], fill=BLACK)
    st_text(d, x - 2, y - 3, letter, BLACK)
    caption(d, x, y + 15, "FLOPPY DISK")


def trash_icon(d, x, y):
    d.rectangle([x - 8, y - 12, x + 8, y - 10], fill=WHITE, outline=BLACK)
    d.polygon([(x - 7, y - 9), (x + 7, y - 9), (x + 6, y + 8), (x - 6, y + 8)], fill=WHITE, outline=BLACK)
    for k in (-3, 0, 3):
        d.line([(x + k, y - 6), (x + k, y + 5)], fill=BLACK)
    caption(d, x, y + 15, "TRASH")


def desktop(with_pointer=True):
    img = Image.new("RGB", (320, 200), GREEN)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.rectangle([0, 0, 319, 9], fill=WHITE)
    d.line([(0, 9), (319, 9)], fill=BLACK)
    for x, word in ((4, "Desk"), (40, "File"), (76, "View"), (112, "Options")):
        st_text(d, x, 5, word, BLACK)
    disk_icon(d, 24, 30, "A")
    disk_icon(d, 24, 70, "B")
    trash_icon(d, 24, 172)
    if with_pointer:
        pointer(d, 196, 112)
    return img


def window():
    img = desktop(with_pointer=False)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    x0, y0, x1, y1 = 70, 26, 300, 150
    d.rectangle([x0, y0, x1, y1], fill=WHITE, outline=BLACK)
    for k in range(0, 9, 2):                               # the title bar's stripes
        d.line([(x0 + 11, y0 + 1 + k), (x1 - 11, y0 + 1 + k)], fill=BLACK)
    d.rectangle([x0 + 120 - 16, y0 + 1, x0 + 120 + 16, y0 + 9], fill=WHITE)
    st_text(d, x0 + 109, y0 + 5, "A:\\", BLACK)
    d.rectangle([x0, y0, x0 + 10, y0 + 10], fill=WHITE, outline=BLACK)
    d.rectangle([x0 + 3, y0 + 3, x0 + 7, y0 + 7], outline=BLACK)
    d.rectangle([x1 - 10, y0, x1, y0 + 10], fill=WHITE, outline=BLACK)
    d.line([(x0, y0 + 10), (x1, y0 + 10)], fill=BLACK)
    small = ImageFont.truetype(FONTS + "consola.ttf", 8)
    d.text((x0 + 4, y0 + 15), "61440 bytes used in 3 items.", font=small, fill=BLACK, anchor="lm")
    d.line([(x0, y0 + 20), (x1, y0 + 20)], fill=BLACK)
    d.line([(x1 - 10, y0 + 20), (x1 - 10, y1)], fill=BLACK)
    d.rectangle([x1 - 9, y0 + 32, x1 - 1, y0 + 70], fill=(170, 170, 170))
    d.line([(x0, y1 - 10), (x1, y1 - 10)], fill=BLACK)

    def icon(cx, cy, kind, name, chosen=False):
        ink, paper = (WHITE, BLACK) if chosen else (BLACK, WHITE)
        if kind == "prg":
            d.rectangle([cx - 11, cy - 10, cx + 11, cy + 8], fill=paper, outline=ink)
            d.rectangle([cx - 11, cy - 10, cx + 11, cy - 6], fill=ink)
        elif kind == "txt":
            d.polygon([(cx - 8, cy - 10), (cx + 4, cy - 10), (cx + 8, cy - 6), (cx + 8, cy + 8), (cx - 8, cy + 8)],
                      fill=paper, outline=ink)
            for k in range(4):
                d.line([(cx - 5, cy - 4 + 3 * k), (cx + 5, cy - 4 + 3 * k)], fill=ink)
        else:
            d.polygon([(cx - 11, cy - 6), (cx - 4, cy - 6), (cx - 2, cy - 9), (cx + 11, cy - 9), (cx + 11, cy + 8),
                       (cx - 11, cy + 8)], fill=paper, outline=ink)
        caption(d, cx, cy + 15, name, inverted=chosen)
    icon(x0 + 34, y0 + 46, "prg", "ODYSSEY.PRG", chosen=True)
    icon(x0 + 94, y0 + 46, "txt", "READ_ME.TXT")
    icon(x0 + 154, y0 + 46, "dir", "SAVES")
    pointer(d, x0 + 40, y0 + 44)
    return img


def title_screen():
    """Odyssey's title screen, 320 x 200: the sky banded as the ST's 3-bit palette bands it, stars, a ringed planet,
    the ship, the title in raster-bar colours, PRESS FIRE."""
    w, h = 320, 200
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    stops = [(0.0, (0, 0, 2)), (0.5, (3, 0, 5)), (0.8, (6, 1, 4)), (1.0, (7, 4, 2))]   # 0-7 per channel
    for y in range(h):
        t = y / h
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0)
                colour = tuple(round(a + (b - a) * u) * 255 // 7 for a, b in zip(c0, c1))
        d.line([(0, y), (w, y)], fill=colour)
    rng = random.Random(1040)
    for _ in range(80):
        x, y = rng.randrange(w), rng.randrange(120)
        d.point((x, y), fill=(255, 255, 255) if rng.random() < 0.5 else (146, 182, 255))
    d.ellipse([206, 96, 300, 190], fill=(255, 109, 36))
    d.ellipse([212, 100, 284, 166], fill=(255, 146, 72))
    d.arc([174, 128, 332, 158], 160, 380, fill=(255, 219, 182), width=3)
    ship(d, 118, 140, 2.0, (255, 255, 255), (255, 182, 0))
    for k in range(4):
        d.line([(46 - k * 8, 136 + k * 3), (86 - k * 5, 136 + k * 3)], fill=(255, 219, 109), width=2)
    font = ImageFont.truetype(FONTS + "ariblk.ttf", 40)
    mask = Image.new("L", (w, 60), 0)
    dm = ImageDraw.Draw(mask)
    dm.fontmode = "1"
    dm.text((w / 2, 30), "ODYSSEY", font=font, fill=255, anchor="mm")
    bars = Image.new("RGB", (w, 60))
    db = ImageDraw.Draw(bars)
    for y in range(60):                                       # the raster bars through the letters
        t = abs(math.sin(y / 60 * math.pi * 2.0))
        db.line([(0, y), (w, y)], fill=(255, round(73 + 182 * t) // 36 * 36, round(255 * (1 - t)) // 36 * 36))
    img.paste((36, 0, 73), (2, 14), mask)
    img.paste(bars, (0, 12), mask)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((w / 2, 178), "PRESS FIRE TO START", font=ImageFont.truetype(FONTS + "consolab.ttf", 11),
           fill=(255, 255, 109), anchor="mm")
    return img


def glass_image(raster, size):
    """A screen's region: the tube's dark border, the 320 x 200 picture in its middle."""
    sw, sh = L.SCREEN_PX
    rw, rh = L.RASTER
    image = Image.new("RGB", (sw, sh), (20, 22, 21))
    picture = raster.resize((rw * 2, rh * 2), Image.NEAREST).resize((rw, rh), Image.LANCZOS)
    image.paste(picture, ((sw - rw) // 2, (sh - rh) // 2))
    return image.resize(size, Image.LANCZOS)


# ---- The floppy ------------------------------------------------------------------------------------------------------

def disk_side(rect, label):
    """One side of the floppy, seen looking at it, its shutter's edge to the left: the shell, the shutter, and either
    the label (the label side) or the hub."""
    grey = rgb(L.COLOURS["disk"])
    reg = Region(rect, L.DISK["length"], L.DISK["width"], grey)
    reg.rect_(0.0, 0.0, 94.0, 90.0, shade(grey, 0.06), r=2.0)
    reg.rect_(0.0, 15.0, 36.0, 75.0, shade(grey, -0.18))
    reg.rect_(0.0, 19.0, 32.0, 71.0, (196, 200, 206))
    reg.rect_(8.0, 37.0, 27.0, 53.0, (40, 38, 44), r=1.5)
    reg.rect_(9.5, 38.5, 25.5, 51.5, (92, 64, 44), r=1.0)
    reg.circle(88.0, 7.0, 2.2, (16, 16, 20))
    if label:
        reg.rect_(39.0, 5.5, 92.0, 84.5, (240, 238, 230), r=1.2)
        art = Image.new("RGB", (790, 530), (240, 238, 230))
        da = ImageDraw.Draw(art)
        da.rectangle([0, 0, 790, 150], fill=(30, 60, 160))
        ship(da, 150, 75, 3.0, (255, 255, 255), (255, 182, 0))
        da.text((480, 75), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 96), fill=(255, 230, 90),
                anchor="mm")
        da.text((395, 240), "ATARI ST  ·  DISK 1", font=ImageFont.truetype(FONTS + "arialbd.ttf", 50),
                fill=(40, 40, 60), anchor="mm")
        for y in (330, 400, 470):
            da.line([(50, y), (740, y)], fill=(180, 176, 168), width=4)
        art = art.rotate(90, expand=True)
        x0, y0, x1, y1 = reg.box(40.0, 6.5, 91.0, 83.5)
        reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
        reg.poly([(3.0, 6.0), (8.0, 3.5), (8.0, 8.5)], shade(grey, 0.35))
    else:
        cx, cy = 52.0, 45.0
        reg.circle(cx, cy, 14.5, shade(grey, -0.25))
        reg.circle(cx, cy, 12.5, (176, 180, 186))
        reg.circle(cx, cy, 11.0, (196, 200, 206))
        reg.rect_(cx - 2.2, cy - 2.2, cx + 2.2, cy + 2.2, (30, 30, 34))
        reg.rect_(cx + 4.0, cy + 2.0, cx + 8.0, cy + 6.5, (30, 30, 34))
        reg.rect_(86.0, 79.0, 91.0, 86.0, (230, 230, 232), r=0.6)
    return reg


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (20, 22, 21))
    for name, raster in (("desktop", desktop()), ("window", window()), ("title", title_screen())):
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(glass_image(raster, (w, h)), (x, y))
    disk_side(L.MEDIA_REGIONS["disk_top"], True).paste(image)
    disk_side(L.MEDIA_REGIONS["disk_bottom"], False).paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", (6, 7, 6)), ("edge", rgb(L.COLOURS["disk"]))):
        x, y = L.MEDIA_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "atari_st_media.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
