"""The Amstrad CPC 464's printing, for the console theme's Amstrad CPC model (amstrad_cpc.py). amstrad_cpc_layout.py has
the measurements and where each part is in the atlases.

Writes two images into a folder:
- cpc_print.png: the keyboard unit's top seen square on (the navy panel round the main keys with the AMSTRAD and
  CPC 464 printing and the power light, the numeric pad's surround, the datacorder's outline, its panel's
  MONITOR / TAPE / COMPUTER diagram, the door's smoked plastic with its tape scale and red DATACORDER band, every key's
  top and legend), a cassette's two sides (a made-up game, Odyssey, on its labels: side B is seen from below, under
  the open door), a reel's hub, and the monitor's band under its screen.
- cpc_screen.png: the CTM644's glass showing BASIC 1.0's boot screen: the texture of the model's `video` material,
  shown while its video doesn't play.

The screens' drawing (the CPC's text screens, the game's title and its loading, the glass) is shared with
amstrad_cpc_video.py, which draws the card's video with it.

The game, Odyssey, and its picture are made up. Run it with the system Python (Pillow):

    python tools/console-models/amstrad_cpc_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amstrad_cpc_layout as L  # noqa: E402
from windows_pc_print import FONTS, Region, mix  # noqa: E402

CASE = (54, 56, 58)
NAVY = (40, 46, 72)
PAD = (40, 42, 45)
SMOKE = (30, 32, 36)
WHITE = (238, 238, 232)
KEY_TOPS = {"dark": (46, 48, 52), "green": (60, 172, 76), "red": (226, 46, 38), "blue": (50, 100, 196)}
MONITOR = (58, 60, 62)


def y(s):
    """The top region's y (down from the slope's back edge) for s up the slope."""
    return L.SLOPE_LENGTH - s


def legend(reg, x0, s0, x1, s1, text):
    """A key's legend on its top (x0, s0, x1, s1): characters at its top left, words in its middle."""
    lines = text.split("\n")
    w, h = x1 - x0, s1 - s0
    if text in ("↑", "←", "→", "↓"):
        cx, cy, a = (x0 + x1) / 2, y((s0 + s1) / 2), min(w, h) * 0.3
        turn = {"↑": 0, "→": 90, "↓": 180, "←": 270}[text]
        shape = [(0, -a), (a * 0.75, -a * 0.1), (a * 0.28, -a * 0.1), (a * 0.28, a), (-a * 0.28, a),
                 (-a * 0.28, -a * 0.1), (-a * 0.75, -a * 0.1)]
        c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
        reg.poly([(cx + px * c - py * s, cy + px * s + py * c) for px, py in shape], WHITE)
    elif all(len(line) == 1 for line in lines):
        size = 4.4 if len(lines) == 1 else 3.4
        for k, line in enumerate(lines):
            reg.text(line, "arialbd.ttf", size, x0 + 1.6, y(s1) + 1.2 + k * h * 0.46, WHITE, anchor="lt")
    else:
        size = 2.4 if len(lines) == 1 else 2.0
        for k, line in enumerate(lines):
            cy = y((s0 + s1) / 2) + (k - (len(lines) - 1) / 2) * size * 1.25
            reg.text(line, "arialbd.ttf", size, (x0 + x1) / 2, cy, WHITE)


def deck_symbol(reg, name, cx, cy):
    """The datacorder keys' symbols, over their names."""
    a = 1.4
    if name == "rec":
        reg.circle(cx, cy, a * 0.8, fill=WHITE)
    elif name in ("play", "ffwd", "rew"):
        flip = -1 if name == "rew" else 1
        for k in range(1 if name == "play" else 2):
            ox = cx + flip * (k - (0 if name == "play" else 0.5)) * a * 1.4
            reg.poly([(ox - flip * a * 0.7, cy - a), (ox + flip * a * 0.7, cy), (ox - flip * a * 0.7, cy + a)], WHITE)
    elif name == "eject":
        reg.rect_(cx - a * 1.9, cy - a * 0.7, cx - a * 0.5, cy + a * 0.7, WHITE)
        reg.poly([(cx + a * 0.4, cy + a * 0.5), (cx + a * 1.2, cy - a * 0.7), (cx + a * 2.0, cy + a * 0.5)], WHITE)
    elif name == "pause":
        reg.rect_(cx - a * 0.8, cy - a, cx - a * 0.25, cy + a, WHITE)
        reg.rect_(cx + a * 0.25, cy - a, cx + a * 0.8, cy + a, WHITE)


def key_top(reg, x0, s0, x1, s1, colour, text, r=1.2):
    top = KEY_TOPS[colour]
    reg.rect_(x0, y(s1), x1, y(s0), mix(top, (0, 0, 0), 0.25), r=r)
    reg.rect_(x0 + 0.3, y(s1) + 0.3, x1 - 0.3, y(s0) - 0.3, top, r=r)
    if text:
        legend(reg, x0, s0, x1, s1, text)


def keyboard(reg):
    reg.rect_(*_box(L.NAVY), mix(NAVY, (110, 130, 190), 0.35), r=3)
    reg.rect_(*_box(L.NAVY, 0.6), NAVY, r=2.6)
    # The panel catches the screen's blue towards its back (as in the photographs).
    glow = reg.layer()
    gd = ImageDraw.Draw(glow)
    for k in range(24):
        t = k / 23
        gd.ellipse(reg.box(120 + 60 * t, y(128) - 20 + 10 * t, 330 - 40 * t, y(70) + 10 - 14 * t),
                   fill=(70, 100, 220, 5))
    mask = Image.new("L", glow.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(reg.box(*_box(L.NAVY, 0.6)), radius=2.6 * reg.sx, fill=255)
    glow.putalpha(ImageChops.multiply(glow.getchannel("A"), mask))
    reg.over(glow)

    # AMSTRAD (bold italic, its stripes), CPC 464 and its colour bars, the power light.
    reg.text("AMSTRAD", "arialbi.ttf", 7.4, 52, y(117.5), WHITE, anchor="lm")
    for k in range(3):
        reg.rect_(52, y(113.4) + k * 0.9, 96, y(113.4) + k * 0.9 + 0.35, NAVY)
    reg.text("CPC 464", "arialbi.ttf", 7.0, 232, y(118.5), (96, 120, 236), anchor="lm")
    reg.text("COLOUR PERSONAL COMPUTER", "arialbd.ttf", 1.7, 233, y(112.6), (150, 160, 200), anchor="lm")
    for k, c in enumerate(((226, 52, 44), (60, 176, 80), (58, 104, 220))):
        reg.rect_(268 + k * 6.5, y(121), 273 + k * 6.5, y(115.5), c)
    reg.rect_(318, y(120.5), 326, y(116.5), (40, 8, 6), r=0.8)
    reg.rect_(318.6, y(119.9), 325.4, y(117.1), (236, 48, 40), r=0.6)
    reg.text("ON", "arialbd.ttf", 1.6, 322, y(113.5), (150, 160, 200))

    reg.rect_(*_box(L.PAD), mix(PAD, (0, 0, 0), 0.3), r=2.5)
    reg.rect_(*_box(L.PAD, 0.6), PAD, r=2.0)

    for _name, x, row, w, rows, colour, text in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(x, row, w, rows)
        key_top(reg, x0 + L.TOP_INSET, s0 + L.TOP_INSET, x1 - L.TOP_INSET, s1 - L.TOP_INSET, colour, text)


def datacorder(reg):
    reg.rect_(*_box(L.DECK), mix(CASE, (0, 0, 0), 0.35), r=2.0)
    reg.rect_(*_box(L.DECK, 0.7), mix(CASE, (0, 0, 0), 0.08), r=1.6)
    x0, s0, x1, s1, _ = L.SLOT
    reg.rect_(x0, y(s1), x1, y(s0), (16, 16, 18), r=1.0)

    # The panel between the keys and the door: the leads' diagram.
    px0, ps0, px1, ps1 = L.PANEL
    reg.rect_(px0, y(ps1), px1, y(ps0), (40, 42, 45), r=1.0)
    top = y(ps1)
    green, red = (64, 176, 78), (222, 54, 48)
    reg.rect_(px0 + 8, top + 4.6, px0 + 56, top + 9.0, green)
    reg.text("MONITOR", "arialbd.ttf", 2.6, px0 + 32, top + 6.8, WHITE)
    reg.rect_(px0 + 8, top + 10.6, px0 + 56, top + 15.0, red)
    reg.text("TAPE", "arialbd.ttf", 2.6, px0 + 32, top + 12.8, WHITE)
    reg.rect_(px0 + 8, top + 16.6, px0 + 56, top + 21.0, None, outline=WHITE, width=0.45)
    reg.text("COMPUTER", "arialbd.ttf", 2.6, px0 + 32, top + 18.8, WHITE)
    reg.line([(px0 + 56, top + 12.8), (px0 + 68, top + 12.8), (px0 + 72, top + 18.8), (px0 + 76, top + 18.8)], red, 0.45)
    reg.line([(px0 + 56, top + 18.8), (px0 + 70, top + 18.8)], WHITE, 0.45)
    reg.line([(px0 + 56, top + 6.8), (px0 + 112, top + 6.8)], (90, 92, 96), 0.35)
    reg.rect_(px0 + 86, top + 3.0, px0 + 100, top + 11.4, mix(green, WHITE, 0.25), r=0.4)
    reg.rect_(px0 + 86.6, top + 3.6, px0 + 99.4, top + 10.8, green, r=0.3)
    reg.rect_(px0 + 76, top + 16.0, px0 + 120, top + 21.6, None, outline=WHITE, width=0.45)
    reg.rect_(px0 + 108, top + 16.9, px0 + 119.1, top + 20.7, red)
    reg.rect_(px0 + 78, top + 18.2, px0 + 106, top + 19.4, None, outline=WHITE, width=0.3)

    # The door: smoked plastic, its edge catching the light, the red band near its front and the tape scale.
    dx0, ds0, dx1, ds1, _ = L.DOOR
    reg.rect_(dx0, y(ds1), dx1, y(ds0), (70, 72, 78), r=1.4)
    reg.rect_(dx0 + 0.8, y(ds1) + 0.8, dx1 - 0.8, y(ds0) - 0.8, SMOKE, r=1.0)
    sheen = reg.layer()
    ImageDraw.Draw(sheen).polygon([reg.p(dx0 + 10, y(ds1) + 1), reg.p(dx0 + 40, y(ds1) + 1),
                                   reg.p(dx0 + 22, y(ds0) - 1), reg.p(dx0 - 8, y(ds0) - 1)], fill=(255, 255, 255, 14))
    reg.over(sheen)
    reg.rect_(dx0 + 9, y(65.5), dx1 - 9, y(58.5), (212, 46, 40))
    reg.text("MICRO COMPUTER SOFTWARE DATACORDER", "arialbd.ttf", 2.5, (dx0 + dx1) / 2, y(62), (60, 10, 8))
    sy = y(73.5)
    reg.line([(452, sy - 1.6), (452, sy), (522, sy), (522, sy - 1.6)], WHITE, 0.4)
    for k in range(15):
        x = 456 + k * 4.4
        reg.line([(x, sy), (x, sy - (2.2 if k % 5 == 2 else 1.2))], WHITE, 0.35)
    wx0, ws0, wx1, ws1 = L.WINDOW
    reg.rect_(wx0 - 1.2, y(ws1) - 1.2, wx1 + 1.2, y(ws0) + 1.2, (66, 68, 74), r=1.4)
    reg.rect_(wx0, y(ws1), wx1, y(ws0), (12, 12, 14), r=1.0)

    # The slide switch behind the door, and the datacorder's keys.
    x0, s0, x1, s1, _ = L.SLIDER
    reg.rect_(x0 - 2, y(s1) - 1, x1 + 2, y(s0) + 1, (24, 24, 26), r=1.0)
    left, pitch, width, front, back, _ = L.DECK_KEY
    for k, (name, colour, text) in enumerate(L.DECK_KEYS):
        kx0 = left + k * pitch
        key_top(reg, kx0 + 0.8, front + 0.8, kx0 + width - 0.8, back - 0.8, colour, "", r=0.8)
        cx = kx0 + width / 2
        deck_symbol(reg, name, cx, y(back - 4.4))
        for j, line in enumerate(text.split("\n")):
            reg.text(line, "arialbd.ttf", 2.0, cx, y(back - 9.2) + j * 2.4, WHITE)


def _box(rect, inset=0.0):
    x0, s0, x1, s1 = rect
    return x0 + inset, y(s1) + inset, x1 - inset, y(s0) - inset


def top(atlas):
    reg = Region(L.REGIONS["top"], L.WIDTH, L.SLOPE_LENGTH, CASE + (255,))
    keyboard(reg)
    datacorder(reg)
    reg.paste(atlas)


def cassette(atlas, side):
    """
    A side of the cassette, as it lies in the datacorder: side A its top, the back edge at the image's top and the
    tape's opening at the bottom; side B its bottom, seen from below (as the open door shows it), the tape's opening at
    the top. Each label reads upright: the title's sunset band above the hubs on A, below them on B.
    """
    w, d, _ = L.CASSETTE
    flip = side == "B"
    yy = (lambda v: d - v) if flip else (lambda v: v)
    reg = Region(L.REGIONS["cassette_b" if flip else "cassette"], w, d, (34, 34, 38, 255))
    reg.rect_(1.2, 1.2, w - 1.2, d - 1.2, None, outline=(52, 52, 58), width=0.5)
    # The label: a sunset band with the title, a cream field round the window, the side.
    label = (yy(46), yy(3.5)) if flip else (3.5, 46)
    band = 44.5 if flip else 3.5
    reg.rect_(6, label[0], w - 6, label[1], (238, 232, 214), r=2.0)
    for k, c in enumerate(((44, 18, 92), (128, 24, 120), (214, 40, 110), (246, 110, 40), (250, 196, 60))):
        reg.rect_(6, band + k * 3.0, w - 6, band + 3.0 + k * 3.0, c)
    reg.text("ODYSSEY", "arialbi.ttf", 7.6, w / 2, band + 6.1, (255, 246, 190))
    words = label[0] + 3.4 if flip else label[1] - 4.5
    reg.text("AMSTRAD CPC 464", "arialbd.ttf", 2.3, w - 9, words, (60, 50, 70), anchor="rm")
    reg.text("SIDE " + side, "arialbd.ttf", 3.2, 10, words, (60, 50, 70), anchor="lm")
    hy = yy(L.HUBS_FROM_TOP)
    hubs = (w / 2 - L.SPINDLES[0], w / 2 + L.SPINDLES[0])
    reg.rect_(hubs[0] - 9.5, hy - 8.5, hubs[1] + 9.5, hy + 8.5, (226, 220, 202), r=8.5)
    # The window between the hubs: the tape wound round each, the left reel fuller.
    win = reg.layer()
    wd = ImageDraw.Draw(win)
    wd.rounded_rectangle(reg.box(hubs[0] + 6.5, hy - 6.5, hubs[1] - 6.5, hy + 6.5), radius=1.5 * reg.sx, fill=(58, 52, 50, 255))
    for cx, r in ((hubs[0], 16.5), (hubs[1], 11.0)):
        wd.ellipse(reg.box(cx - r, hy - r, cx + r, hy + r), fill=(92, 52, 30, 255))
    mask = Image.new("L", win.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(reg.box(hubs[0] + 6.5, hy - 6.5, hubs[1] - 6.5, hy + 6.5), radius=1.5 * reg.sx, fill=255)
    win.putalpha(ImageChops.multiply(win.getchannel("A"), mask))
    reg.over(win)
    for cx in hubs:
        reg.circle(cx, hy, L.HUB + 1.4, fill=(34, 34, 38))
        reg.circle(cx, hy, L.HUB + 1.4, outline=(120, 116, 104), width=0.4)
    # The tape's edge: the raised trapezoid, its holes, and the five screws.
    reg.poly([(14, yy(d - 1.2)), (20, yy(50)), (w - 20, yy(50)), (w - 14, yy(d - 1.2))], (44, 44, 50))
    for x in (30, 42, w / 2, w - 42, w - 30):
        reg.circle(x, yy(d - 6.5), 1.3 if x in (30, w - 30) else 1.9, fill=(14, 14, 16))
    for x, v in ((4, 4), (w - 4, 4), (4, d - 4), (w - 4, d - 4), (w / 2, 50.5)):
        reg.circle(x, yy(v), 1.3, fill=(80, 80, 86))
        reg.line([(x - 0.8, yy(v)), (x + 0.8, yy(v))], (30, 30, 34), 0.3)
    reg.paste(atlas)


def hub(atlas):
    r = L.HUB
    reg = Region(L.REGIONS["hub"], 2 * r, 2 * r, (34, 34, 38, 255))
    reg.circle(r, r, r, fill=(236, 234, 226))
    reg.circle(r, r, r * 0.62, fill=(34, 34, 38))
    for k in range(6):                                   # the teeth that grip the spindle
        a = math.radians(k * 60)
        c, s = math.cos(a), math.sin(a)
        pts = [(-0.7, r * 0.3), (0.7, r * 0.3), (0.7, r * 0.66), (-0.7, r * 0.66)]
        reg.poly([(r + px * c - py * s, r + px * s + py * c) for px, py in pts], (236, 234, 226))
    reg.circle(r, r, r * 0.08 + 0.4, fill=(236, 234, 226))
    reg.paste(atlas)


def strip(atlas):
    mon = L.MONITOR
    w, h = mon["width"] - 16.0, mon["strip"][1]
    reg = Region(L.REGIONS["strip"], w, h, MONITOR + (255,))
    reg.text("power", "arial.ttf", 3.0, w - 26, h / 2, (150, 152, 156), anchor="rm")
    reg.rect_(w - 22, h / 2 - 2.5, w - 10, h / 2 + 2.5, (34, 35, 37), r=0.8)
    reg.rect_(w - 21.4, h / 2 - 1.9, w - 10.6, h / 2 + 1.9, (64, 66, 69), r=0.6)
    reg.text("AMSTRAD", "arialbi.ttf", 3.2, 10, h / 2, (120, 122, 126), anchor="lm")
    reg.text("CTM644 COLOUR MONITOR", "arialbd.ttf", 2.0, 40, h / 2, (110, 112, 116), anchor="lm")
    reg.paste(atlas)


def print_atlas(out):
    atlas = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    top(atlas)
    cassette(atlas, "A")
    cassette(atlas, "B")
    hub(atlas)
    strip(atlas)
    atlas.save(out, optimize=True)


# -- The screens -----------------------------------------------------------------------------------------------------
# The CPC's 40 x 25 characters of 8 x 8 pixels (mode 1), its firmware's colours, and its mode 0 picture (160 x 200
# pixels, twice as wide as they're tall).

BLUE, YELLOW, BLACK = (30, 58, 226), (240, 242, 104), (0, 0, 0)
BOOT = [" Amstrad 64K Microcomputer  (v1)", "", " ©1984 Amstrad Consumer Electronics plc",
        "           and Locomotive Software Ltd.", "", " BASIC 1.0", "", "Ready"]
PRESS = BOOT + ['run"', "Press PLAY then any key:"]
LOADING = PRESS + ["Loading ODYSSEY block 1"]
SCREEN_BYTES = 16384   # the CPC's screen memory: eight blocks of 2048, each one pixel row of all 25 character rows


def text_screen(lines, cursor=None):
    """A 320 x 200 mode 1 screen: lines from the top, the cursor (a solid block) at (column, row) if there is one."""
    font = ImageFont.truetype(FONTS + "lucon.ttf", 9)
    ink = Image.new("1", (320, 200), 0)
    d = ImageDraw.Draw(ink)
    d.fontmode = "1"
    for row, line in enumerate(lines):
        for col, ch in enumerate(line):
            d.text((col * 8, row * 8), ch, font=font, fill=1)
    ink = ImageChops.lighter(ink, ImageChops.offset(ink, 1, 0))   # the CPC's characters have two-pixel strokes
    if cursor is not None:
        col, row = cursor
        ImageDraw.Draw(ink).rectangle([col * 8, row * 8, col * 8 + 7, row * 8 + 7], fill=1)
    screen = Image.new("RGB", (320, 200), BLUE)
    screen.paste(Image.new("RGB", (320, 200), YELLOW), (0, 0), ink.convert("L"))
    return screen, BLUE


# The CPC's 27 colours are every mix of three levels of red, green and blue.
def cpc(r, g, b):
    return tuple((0, 128, 255)[c] for c in (r, g, b))


def small_text(img, text, y, colour):
    """A line of mode 1 characters, halved to mode 0's wide pixels, centred at row y of a 160 x 200 picture."""
    line = Image.new("1", (320, 8), 0)
    d = ImageDraw.Draw(line)
    d.fontmode = "1"
    d.text((160, 4), text, font=ImageFont.truetype(FONTS + "lucon.ttf", 9), fill=1, anchor="mm")
    line = ImageChops.lighter(line, ImageChops.offset(line, 1, 0)).resize((160, 8), Image.NEAREST)
    img.paste(Image.new("RGB", (160, 8), colour), (0, y), line.convert("L"))


def picture(t=0.0, prompt=False):
    """
    The game's title in mode 0: a sun setting behind mountains over a grid, stars, and the title. t (seconds) runs it:
    the grid's lines roll towards the viewer and the stars twinkle; prompt adds a blinking PRESS FIRE.
    """
    img = Image.new("RGB", (160, 200), cpc(0, 0, 0))
    d = ImageDraw.Draw(img)
    bands = [(0, cpc(0, 0, 0)), (40, cpc(0, 0, 1)), (70, cpc(1, 0, 1)), (92, cpc(2, 0, 1)), (108, cpc(2, 1, 0)),
             (118, cpc(2, 2, 1)), (124, None)]
    for (y0, c0), (y1, c1) in zip(bands, bands[1:]):
        d.rectangle([0, y0, 159, y1 - 1], fill=c0)
        if c1 is not None:                           # a dithered seam between bands
            for x in range(0, 160, 2):
                d.point((x + (y1 // 2) % 2, y1 - 2), fill=c1)
                d.point((x + 1 - (y1 // 2) % 2, y1 - 1), fill=c1)
    rng = random.Random(464)
    for k in range(60):
        x, yy = rng.randrange(160), rng.randrange(4, 66)
        bright = rng.random() < 0.6
        phase = rng.random()
        if t > 0 and (t * 1.7 + phase) % 1.0 < 0.18:   # each star dims for a moment now and then
            continue
        d.point((x, yy), fill=cpc(2, 2, 2) if bright else cpc(1, 2, 2))
    # The sun: bands of yellow to red, cut by widening gaps towards its foot.
    cx, cy, r = 80, 102, 34
    for yy in range(cy - r, cy + 1):
        half = int(round(2 * math.sqrt(max(0, r * r - (yy - cy) ** 2))) / 2)
        f = (yy - (cy - r)) / r
        gap = yy > cy - 14 and (yy - (cy - 14)) % 6 < 1 + (yy - (cy - 14)) // 6
        if not gap:
            c = cpc(2, 2, 1) if f < 0.35 else cpc(2, 2, 0) if f < 0.6 else cpc(2, 1, 0) if f < 0.82 else cpc(2, 0, 1)
            d.line([(cx - half, yy), (cx + half, yy)], fill=c)
    # The mountains, then the grid: its lines roll down towards the viewer, two a second.
    ridge = [(0, 112), (12, 100), (22, 106), (36, 88), (50, 104), (60, 98), (70, 110), (92, 108), (104, 92),
             (118, 104), (128, 96), (142, 108), (152, 100), (160, 106), (160, 126), (0, 126)]
    d.polygon(ridge, fill=cpc(0, 0, 1))
    d.line(ridge[:-2], fill=cpc(1, 0, 2))
    d.rectangle([0, 126, 159, 199], fill=cpc(0, 0, 0))
    roll = (t * 2.0) % 1.0
    for k in range(8):
        yy = 126 + int(round(74 * ((k + roll) / 8) ** 1.8))
        if yy < 200:
            d.line([(0, yy), (159, yy)], fill=cpc(2, 0, 2))
    d.line([(0, 126), (159, 126)], fill=cpc(2, 1, 2))
    for k in range(-10, 11):
        d.line([(80 + k * 4, 126), (80 + k * 26, 199)], fill=cpc(2, 0, 2))
    # The title, chunky: drawn at twice the width, then halved, so its pixels are mode 0's.
    title = Image.new("1", (320, 40), 0)
    td = ImageDraw.Draw(title)
    td.fontmode = "1"
    td.text((160, 20), "ODYSSEY", font=ImageFont.truetype(FONTS + "arialbi.ttf", 34), fill=1, anchor="mm")
    title = title.resize((160, 40), Image.NEAREST)
    shadow = ImageChops.offset(title, 1, 2)
    img.paste(Image.new("RGB", (160, 40), cpc(2, 0, 0)), (0, 10), shadow.convert("L"))
    outline = title.filter(ImageFilter.MaxFilter(3))
    img.paste(Image.new("RGB", (160, 40), cpc(0, 2, 2)), (0, 10), ImageChops.subtract(outline, title).convert("L"))
    img.paste(Image.new("RGB", (160, 40), cpc(2, 2, 1)), (0, 10), title.convert("L"))
    if prompt and t % 1.0 < 0.6:
        small_text(img, "PRESS FIRE", 168, cpc(2, 2, 2))
    small_text(img, "(C) 1985 ODYSSEY SOFTWARE", 190, cpc(1, 2, 2))
    return img.resize((320, 200), Image.NEAREST)


def loading(full, loaded, under=None):
    """
    The picture as it loads into the screen memory, loaded bytes of SCREEN_BYTES in: a block of 2048 holds one pixel
    row of every character row, left to right and top to bottom, so it fills like a venetian blind. Under the rows not
    loaded yet is under (black by default).
    """
    part = under.copy() if under is not None else Image.new("RGB", (320, 200), BLACK)
    for yy in range(200):
        start = (yy % 8) * 2048 + (yy // 8) * 80          # 80 bytes a pixel row: 160 mode 0 pixels, 2 to a byte
        done = max(0, min(80, loaded - start))
        if done:
            part.paste(full.crop((0, yy, done * 4, yy + 1)), (0, yy))
    return part


def glass(paper, border, size):
    """The glass at size (pixels): its lit raster the border's colour round the paper, a vignette and a sheen."""
    cw, ch = size
    gw, gh = L.GLASS
    rw, rh = L.RASTER
    image = Image.new("RGB", (cw, ch), (18, 20, 22))
    x0, y0 = round((gw - rw) / 2 / gw * cw), round((gh - rh) / 2 / gh * ch)
    pw, ph = round(rw / gw * cw), round(rh / gh * ch)
    raster = Image.new("RGB", (pw, ph), border)
    qw, qh = round(pw * L.PAPER[0]), round(ph * L.PAPER[1])
    raster.paste(paper.resize((qw, qh), Image.NEAREST), ((pw - qw) // 2, (ph - qh) // 2))
    raster = raster.filter(ImageFilter.GaussianBlur(0.6 * cw / 1024))          # a CRT's soft dots
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=pw * 0.035, fill=255)
    image.paste(raster, (x0, y0), mask.filter(ImageFilter.GaussianBlur(1.5 * cw / 1024)))
    vignette = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(vignette).rounded_rectangle([x0 + pw * 0.05, y0 + ph * 0.06, x0 + pw * 0.95, y0 + ph * 0.94],
                                               radius=pw * 0.14, fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(pw * 0.07))
    image = Image.composite(image, Image.blend(image, Image.new("RGB", (cw, ch), (0, 0, 0)), 0.35), vignette)
    sheen = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(sheen).ellipse([-cw * 0.3, -ch * 0.6, cw * 0.75, ch * 0.42], fill=24)
    sheen = sheen.filter(ImageFilter.GaussianBlur(cw * 0.08))
    return Image.composite(Image.new("RGB", (cw, ch), (255, 255, 255)), image, sheen)


def boot_glass(size):
    """The boot screen on the glass: the video's first and last frames, and the still shown when no video plays."""
    return glass(*text_screen(BOOT, (0, 8)), size)


if __name__ == "__main__":
    folder = os.path.abspath(sys.argv[1])
    os.makedirs(folder, exist_ok=True)
    print_atlas(os.path.join(folder, "cpc_print.png"))
    boot_glass(L.SCREEN_PX).save(os.path.join(folder, "cpc_screen.png"), optimize=True)
    print("Amstrad CPC 464: print and screen")


