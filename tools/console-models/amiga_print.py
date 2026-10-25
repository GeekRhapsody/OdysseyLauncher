"""The Amiga 500's and its 1084S monitor's printing, for the console theme's Amiga model (tools/console-models/amiga.py).

Draws its two atlases, their regions as amiga_layout.py places them. amiga_print.png: the computer's top seen from
above, in millimetres as the model's planar UVs map it (each key's top in its colour with its legend, the Commodore
badge, the power light lit and the drive light off, the AMIGA lettering in relief), the monitor's badge, and the
swatches small parts take their colour from. amiga_media.png: the two screens, each the glass's whole width and
height, a dark border round the lit raster, drawn at the Amiga's 320 x 256 pixels: Kickstart 1.3's hand holding a
disk (the glass at rest) and the title screen of a made-up game, Odyssey; and the floppy's two sides, its label
(Odyssey's) and its hub. Run it with the system Python (Pillow):

    python tools/console-models/amiga_print.py <out folder>

It writes amiga_print.png and amiga_media.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amiga_layout as L  # noqa: E402
from psp_print import ship  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region, gradient, mix  # noqa: E402

CASE = rgb(L.COLOURS["case"])
LEGEND = (62, 61, 57)


def top_point(x, y):
    """A point of the computer's top (x from its middle, y back from its front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


# ---- The computer's top ----------------------------------------------------------------------------------------------

def key_top(reg, key):
    """A key's top: its colour, a slightly lighter middle, and its legend at the top left (arrows and symbols in the
    middle), the shifted character above the other."""
    name, xu, row, wu, colour, legend = key[:6]
    rows = key[6] if len(key) > 6 else 1
    x0, s0, x1, s1 = L.key_rect(xu, row, wu, rows)
    inset = L.KEY_INSET + 0.5
    (ya, _), (yb, _) = L.deck_point(s0 + inset, L.KEY_HEIGHT), L.deck_point(s1 - inset, L.KEY_HEIGHT)
    (rx0, ry0), (rx1, ry1) = top_point(x0 + inset, yb), top_point(x1 - inset, ya)
    fill = rgb(L.COLOURS["top_light" if colour == "light" else "top_dark"])
    reg.rect_(rx0 - 0.6, ry0 - 0.6, rx1 + 0.6, ry1 + 0.6, fill)
    reg.rect_(rx0 + 1.2, ry0 + 1.2, rx1 - 1.2, ry1 - 1.2, shade(fill, 0.05), r=1.5)
    if not legend:
        return
    if name in ("lamiga", "ramiga"):
        reg.text("A", "timesbi.ttf", 5.0, rx0 + 2.2, ry0 + 3.4, LEGEND, anchor="lm")
        return
    lines = legend.split("\n")
    symbol = len(lines) == 1 and len(legend) == 1 and not legend.isalnum()
    if symbol or name.startswith("np") and len(lines[0]) == 1 and len(lines) == 1:
        font = "seguisym.ttf" if not legend.isascii() else "arial.ttf"
        reg.text(legend, font, 4.2 if not legend.isascii() else 3.4, (rx0 + rx1) / 2, (ry0 + ry1) / 2, LEGEND)
        return
    size = 2.4 if len(lines[0]) > 2 or len(lines) > 1 and len(lines[1]) > 2 else 3.0
    for k, line in enumerate(lines):
        font = "seguisym.ttf" if not line.isascii() else "arial.ttf"
        reg.text(line, font, size, rx0 + 1.9, ry0 + 2.6 + k * (size + 0.9), LEGEND, anchor="lm")
    if name == "caps":
        reg.circle(rx1 - 2.2, ry0 + 2.2, 0.7, (40, 38, 34))


def commodore_logo(reg, cx, cy, s, fill):
    """Commodore's mark, s across: the C open to the right, and its two flags in the opening."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    r0, r1 = 0.5 * s, 0.29 * s
    d.ellipse(reg.box(cx - r0, cy - r0, cx + r0, cy + r0), fill=fill + (255,))
    d.ellipse(reg.box(cx - r1, cy - r1, cx + r1, cy + r1), fill=(0, 0, 0, 0))
    d.rectangle(reg.box(cx, cy - 0.23 * s, cx + r0 + 1, cy + 0.23 * s), fill=(0, 0, 0, 0))
    reg.over(layer)
    for top, bottom in ((-0.21 * s, -0.03 * s), (0.03 * s, 0.21 * s)):
        reg.poly([(cx + 0.06 * s, cy + top), (cx + 0.5 * s, cy + top), (cx + 0.5 * s - (bottom - top), cy + bottom),
                  (cx + 0.06 * s, cy + bottom)], fill)


def lettering(reg):
    """AMIGA in relief on the raised back: lit along its upper left, shadowed along its lower right."""
    x1, y, h = L.LETTERING["x"], L.LETTERING["y"], L.LETTERING["height"]
    rx1, ry = top_point(x1, y)
    font = ImageFont.truetype(FONTS + "timesbi.ttf", max(1, round(h * 1.38 * reg.sx)))
    spacing = h * 0.55
    widths = [font.getlength(ch) / reg.sx for ch in "AMIGA"]
    x = rx1 - (sum(widths) + spacing * 4)
    for ch, w in zip("AMIGA", widths):
        for (dx, dy), colour in (((-0.6, -0.6), shade(CASE, 0.5)), ((0.7, 0.7), shade(CASE, -0.38)),
                                 ((0.0, 0.0), shade(CASE, 0.06))):
            reg.draw.text(reg.p(x + dx, ry + dy), ch, font=font, fill=colour, anchor="lm")
        x += w + spacing


def top():
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH, CASE)
    for key in L.KEYS:
        key_top(reg, key)

    # The badge behind the function keys, and the lights beside them.
    bx, by = top_point(L.BADGE["x"], L.BADGE["y"])
    s = L.BADGE["size"]
    reg.rect_(bx - s / 2, by - s / 2, bx + s / 2, by + s / 2, (150, 151, 150), r=1.0)
    reg.rect_(bx - s / 2 + 0.5, by - s / 2 + 0.5, bx + s / 2 - 0.5, by + s / 2 - 0.5, (208, 209, 207), r=0.7)
    commodore_logo(reg, bx, by, s * 0.62, (84, 88, 96))
    (lx0, _), (lx1, _) = top_point(L.LIGHTS["x"][0], 0), top_point(L.LIGHTS["x"][1], 0)
    w = L.LIGHTS["width"]
    for name, lit in (("power", True), ("drive", False)):
        _, ly = top_point(0, L.LIGHTS[name])
        reg.rect_(lx0 - 0.4, ly - w / 2 - 0.4, lx1 + 0.4, ly + w / 2 + 0.4, shade(CASE, -0.3), r=0.4)
        if lit:
            glow = reg.layer()
            ImageDraw.Draw(glow).rounded_rectangle(reg.box(lx0 - 2, ly - w, lx1 + 2, ly + w), radius=2 * reg.sx,
                                                   fill=(255, 60, 40, 110))
            reg.over(glow.filter(ImageFilter.GaussianBlur(1.2 * reg.sx)))
            reg.rect_(lx0, ly - w / 2, lx1, ly + w / 2, (255, 70, 52), r=0.3)
            reg.rect_(lx0 + 0.6, ly - w / 4, lx1 - 0.6, ly, (255, 180, 160), r=0.2)
        else:
            reg.rect_(lx0, ly - w / 2, lx1, ly + w / 2, (96, 52, 46), r=0.3)
        reg.text(name.upper(), "arial.ttf", 1.6, lx0 - 1.6, ly, shade(CASE, -0.32), anchor="rm")
    lettering(reg)
    return reg


def monitor_badge():
    reg = Region(L.PRINT_REGIONS["badge"], 62.0, 12.0, (128, 129, 132))
    reg.rect_(0.3, 0.3, 61.7, 11.7, (150, 151, 154), r=0.8)
    reg.rect_(0.8, 0.8, 61.2, 11.2, (118, 119, 122), r=0.6)
    commodore_logo(reg, 4.6, 4.3, 4.4, (238, 238, 236))
    reg.text("Commodore 1084S", "arialbd.ttf", 4.2, 7.6, 4.3, (238, 238, 236), anchor="lm")
    reg.text("V I D E O   M O N I T O R", "arial.ttf", 2.6, 31.0, 8.9, (230, 230, 228))
    return reg


def print_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    top().paste(image)
    monitor_badge().paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("bezel", rgb(L.COLOURS["bezel"])), ("lit", (255, 64, 46)), ("black", (8, 8, 8))):
        x, y = L.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    return image


# ---- The screens -----------------------------------------------------------------------------------------------------

WHITE, BLACK = (255, 255, 255), (0, 0, 0)
DISK_BLUE, METAL = (0, 85, 170), (170, 170, 170)


def pixel_font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def kickstart():
    """Kickstart 1.3's screen, 320 x 256: on white, a hand holding a disk out to be put in the drive, and V1.3."""
    img = Image.new("RGB", (320, 256), WHITE)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    ox, oy = 92, 60                                   # the drawing's top left

    def p(points):
        return [(ox + x, oy + y) for x, y in points]

    # The disk, tipped a little: its shell, the shutter with its window, the label with Workbench's name.
    a = math.radians(-14)
    c, s = math.cos(a), math.sin(a)

    def disk(points):
        return p([(66 + x * c - y * s, 50 + x * s + y * c) for x, y in points])
    d.polygon(disk([(-38, -40), (38, -40), (38, 40), (-34, 40), (-38, 36)]), fill=DISK_BLUE, outline=BLACK)
    d.polygon(disk([(-18, -40), (18, -40), (18, -12), (-18, -12)]), fill=METAL, outline=BLACK)
    d.polygon(disk([(2, -36), (10, -36), (10, -16), (2, -16)]), fill=DISK_BLUE, outline=BLACK)
    d.polygon(disk([(-30, 2), (30, 2), (30, 40), (-30, 40)]), fill=WHITE, outline=BLACK)
    label = Image.new("L", (60, 24), 0)
    dl = ImageDraw.Draw(label)
    dl.fontmode = "1"
    dl.text((30, 7), "AMIGA", font=pixel_font("timesbd.ttf", 11), fill=255, anchor="mm")
    dl.text((30, 18), "Workbench", font=pixel_font("arial.ttf", 9), fill=255, anchor="mm")
    label = label.rotate(14, resample=Image.NEAREST, expand=True)
    lx, ly = disk([(6, 22)])[0]
    img.paste(BLACK, (round(lx - label.width / 2), round(ly - label.height / 2)), label)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"

    # The hand, from the lower left: the wrist and its cuff, the palm, the fingertips curled round the disk's left
    # edge, the thumb across its front.
    outline = dict(fill=WHITE, outline=BLACK, width=2)
    d.polygon(p([(4, 156), (22, 108), (46, 116), (30, 162)]), **outline)
    d.line(p([(16, 124), (40, 132)]), fill=BLACK, width=2)
    d.polygon(p([(22, 110), (16, 88), (18, 62), (30, 50), (44, 56), (52, 92), (48, 118)]), **outline)
    for x, y in ((26, 52), (24, 64), (24, 76), (26, 88)):
        d.ellipse([ox + x, oy + y - 6, ox + x + 22, oy + y + 6], **outline)
    d.polygon(p([(40, 114), (44, 100), (52, 88), (62, 78), (70, 76), (72, 84), (64, 96), (56, 118)]), **outline)
    d.line(p([(64, 80), (68, 86)]), fill=BLACK, width=2)
    d.text((ox + 110, oy + 122), "V1.3", font=pixel_font("arialbi.ttf", 15), fill=BLACK, anchor="mm")
    return img


def checker_floor(d, horizon, w, h, colours):
    """A floor of tiles running to the horizon, rows narrowing with distance: the demo scene's favourite."""
    for row in range(h - horizon):
        y = horizon + row
        z = 400.0 / (row + 4)                         # distance into the screen
        for x in range(w):
            u = (x - w / 2) * z / 64.0
            tile = (int(math.floor(u / 8.0)) + int(math.floor(z / 6.0))) % 2
            d.point((x, y), fill=colours[tile])


def title_screen():
    """Odyssey's title screen, 320 x 256: copper bars graded to the horizon, a ringed planet, the ship over a tiled
    floor, the title in chrome, PRESS FIRE TO START."""
    w, h, horizon = 320, 256, 176
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    stops = [(0, (0, 0, 48)), (0.45, (64, 16, 112)), (0.8, (208, 64, 96)), (1.0, (255, 176, 64))]
    for y in range(0, horizon, 2):                    # the copper's bands: two lines each
        t = y / horizon
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                colour = mix(c0, c1, (t - t0) / (t1 - t0))
        d.rectangle([0, y, w, y + 1], fill=tuple(v // 16 * 16 for v in colour))
    rng = random.Random(500)
    for _ in range(90):
        x, y = rng.randrange(w), rng.randrange(horizon - 40)
        d.point((x, y), fill=(255, 255, 255) if rng.random() < 0.5 else (160, 176, 255))
    d.ellipse([200, 92, 300, 192], fill=(240, 112, 48))
    d.ellipse([206, 96, 286, 168], fill=(255, 160, 80))
    d.arc([168, 128, 332, 156], 160, 380, fill=(255, 240, 208), width=3)
    checker_floor(d, horizon, w, h, [(40, 16, 96), (112, 48, 160)])
    d.line([(0, horizon), (w, horizon)], fill=(255, 208, 128))
    ship(d, 116, 150, 2.2, (255, 255, 255), (255, 176, 48))
    for k in range(4):
        d.line([(40 - k * 10, 146 + k * 3), (84 - k * 6, 146 + k * 3)], fill=(255, 208, 128), width=2)

    # The title: chrome letters, a dark outline, graded from sky to ground.
    font = pixel_font("ariblk.ttf", 46)
    mask = Image.new("L", (w, 80), 0)
    dm = ImageDraw.Draw(mask)
    dm.fontmode = "1"
    dm.text((w / 2, 40), "ODYSSEY", font=font, fill=255, anchor="mm")
    edge = mask.filter(ImageFilter.MaxFilter(5))
    chrome = gradient((w, 80), [(0.0, (180, 240, 255)), (0.45, (255, 255, 255)), (0.5, (40, 48, 128)),
                                (0.75, (120, 96, 200)), (1.0, (255, 208, 120))]).convert("RGB")
    img.paste((16, 0, 48), (0, 8), edge)
    img.paste(chrome.crop((0, 0, w, 80)), (0, 8), mask)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((w / 2, 230), "PRESS FIRE TO START", font=pixel_font("arialbd.ttf", 12), fill=(255, 240, 64), anchor="mm")
    d.text((w / 2, 246), "© ODYSSEY LAUNCHER", font=pixel_font("arial.ttf", 9), fill=(208, 192, 255), anchor="mm")
    return img


def glass_image(raster):
    """A screen's region: the tube's dark border, the 320 x 256 picture in its middle (doubled, then fitted)."""
    image = Image.new("RGB", L.SCREEN_PX, (22, 24, 23))
    picture = raster.resize((640, 512), Image.NEAREST).resize(L.RASTER, Image.LANCZOS)
    image.paste(picture, ((L.SCREEN_PX[0] - L.RASTER[0]) // 2, (L.SCREEN_PX[1] - L.RASTER[1]) // 2))
    return image


# ---- The floppy ------------------------------------------------------------------------------------------------------

def disk_side(rect, label):
    """One side of the floppy, seen looking at it, its shutter's edge to the left: the shell, the shutter (its window
    showing the disk), and either the label (the label side) or the hub (the other)."""
    blue = rgb(L.COLOURS["disk"])
    reg = Region(rect, L.DISK["length"], L.DISK["width"], blue)
    reg.rect_(0.0, 0.0, 94.0, 90.0, shade(blue, 0.06), r=2.0)
    reg.rect_(0.0, 15.0, 36.0, 75.0, shade(blue, -0.18))           # the shutter's track
    reg.rect_(0.0, 19.0, 32.0, 71.0, (200, 204, 210))               # the shutter
    reg.rect_(0.5, 19.5, 31.5, 22.0, (225, 228, 232))
    reg.rect_(8.0, 37.0, 27.0, 53.0, (40, 38, 44), r=1.5)           # its window, the disk's brown showing
    reg.rect_(9.5, 38.5, 25.5, 51.5, (92, 64, 44), r=1.0)
    reg.circle(91.0 - 3.0, 4.0 + 3.0, 2.2, (16, 16, 20))           # the write-protect hole
    if label:
        art = Image.new("RGB", (780, 515), (246, 244, 236))
        da = ImageDraw.Draw(art)
        band = gradient((780, 250), [(0.0, (24, 12, 72)), (1.0, (120, 40, 140))]).convert("RGB")
        art.paste(band, (0, 0))
        dband = ImageDraw.Draw(art)
        dband.ellipse([610, 150, 730, 270], fill=(240, 112, 48))
        ship(dband, 190, 170, 3.2, (255, 255, 255), (255, 176, 48))
        da.text((390, 82), "ODYSSEY", font=pixel_font("ariblk.ttf", 120), fill=(255, 228, 92), anchor="mm",
                stroke_width=5, stroke_fill=(70, 20, 10))
        da.text((390, 318), "AMIGA  ·  DISK 1 OF 1", font=pixel_font("arialbd.ttf", 46), fill=(40, 40, 60),
                anchor="mm")
        da.line([(60, 372), (720, 372)], fill=(180, 176, 168), width=4)
        da.line([(60, 432), (720, 432)], fill=(180, 176, 168), width=4)
        da.text((390, 476), "© ODYSSEY LAUNCHER", font=pixel_font("arial.ttf", 34), fill=(110, 108, 120), anchor="mm")
        art = art.rotate(90, expand=True)              # it reads with the shutter at the top
        reg.rect_(39.0, 5.5, 92.0, 84.5, (230, 228, 220), r=1.2)
        x0, y0, x1, y1 = reg.box(40.0, 6.5, 91.0, 83.5)
        reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
        reg.poly([(3.0, 6.0), (8.0, 3.5), (8.0, 8.5)], shade(blue, 0.3))  # the arrow: this edge goes in first
    else:
        cx, cy = 52.0, 45.0
        reg.circle(cx, cy, 14.5, shade(blue, -0.25))
        reg.circle(cx, cy, 12.5, (176, 180, 186))
        reg.circle(cx, cy, 11.0, (196, 200, 206))
        reg.rect_(cx - 2.2, cy - 2.2, cx + 2.2, cy + 2.2, (30, 30, 34))
        reg.rect_(cx + 4.0, cy + 2.0, cx + 8.0, cy + 6.5, (30, 30, 34))
        reg.rect_(86.0, 79.0, 91.0, 86.0, (230, 230, 232), r=0.6)  # the write-protect tab
    return reg


def media_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (22, 24, 23))
    for name, raster in (("kickstart", kickstart()), ("title", title_screen())):
        x, y, _, _ = L.MEDIA_REGIONS[name]
        image.paste(glass_image(raster), (x, y))
    disk_side(L.MEDIA_REGIONS["disk_top"], True).paste(image)
    disk_side(L.MEDIA_REGIONS["disk_bottom"], False).paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", (6, 6, 7)), ("edge", rgb(L.COLOURS["disk"]))):
        x, y = L.MEDIA_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    return image


def main(out):
    os.makedirs(out, exist_ok=True)
    for name, image in (("amiga_print.png", print_atlas()), ("amiga_media.png", media_atlas())):
        path = os.path.join(out, name)
        image.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1])
