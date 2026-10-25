"""The Game & Watch's printing and screens, for the console theme's Game & Watch model
(tools/console-models/gameandwatch.py).

Draws its atlas, its regions as gameandwatch_layout.py places them, each in millimetres as the model's planar UVs map
it: the lower half's face (the brown panels, GAME & WATCH, CONTROLLER, the buttons' names and their rings, ALARM and
ACL, JUMP, the Nintendo plate, the ribbon along its back, its screen at rest showing the clock) and the upper half's
(the title plate, ODYSSEY, the raised side panels, the screws, its screen at rest); the screens while the game's played,
three frames each (an LCD's black segments, the ship along the bottom and the rocks falling at the top, over the
printed backdrop of a made-up game, Odyssey); and the swatches small parts take their colour from. Run it with the
system Python (Pillow):

    python tools/console-models/gameandwatch_print.py <out folder>

It writes gameandwatch_print.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gameandwatch_layout as L  # noqa: E402
from cdi_print import digit  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

BROWN = rgb(L.COLOURS["case"])
CREAM = (232, 226, 210)
PANEL = (240, 236, 224)
INK = (64, 40, 30)
SEGMENT = (24, 26, 22)
LCD = (200, 204, 184)


# ---- The LCD screens -------------------------------------------------------------------------------------------------

def backdrop(reg, w, h, upper):
    """The printed picture behind the LCD: a pale planet and stars above, the ground's line below."""
    rng = random.Random(23 if upper else 29)
    for _ in range(26):
        reg.circle(rng.uniform(1.0, w - 1.0), rng.uniform(1.0, h - 1.0), 0.25, (150, 160, 190))
    if upper:
        reg.circle(w * 0.78, h * 0.32, h * 0.22, (232, 176, 140))
        reg.draw.arc(reg.box(w * 0.78 - h * 0.4, h * 0.32 - h * 0.08, w * 0.78 + h * 0.4, h * 0.32 + h * 0.08), 160,
                     380, fill=(210, 160, 200), width=reg.width(0.5))
    else:
        reg.line([(0.0, h - 5.0), (w, h - 5.0)], (150, 130, 110), 0.8)
        for k in range(9):
            reg.line([(k * w / 8, h - 5.0), (k * w / 8 - 3.0, h)], (170, 150, 130), 0.4)


def ship_segment(reg, x, y, s, colour):
    """The ship as an LCD segment: an arrowhead pointing up, s tall, its middle at (x, y)."""
    reg.poly([(x, y - s / 2), (x + s * 0.42, y + s / 2), (x, y + s * 0.28), (x - s * 0.42, y + s / 2)], colour)


def rock_segment(reg, x, y, s, colour):
    points = [(x + s / 2 * math.cos(a) * (0.8 + 0.2 * ((k * 7) % 3) / 2), y + s / 2 * math.sin(a))
              for k, a in enumerate(math.radians(36 * j) for j in range(10))]
    reg.poly(points, colour)


def lcd(upper, frame):
    """A screen: the LCD's grey-green, the backdrop, the segments for frame (0 at rest)."""
    w, h = L.UPPER_LCD["size"] if upper else L.LOWER_LCD["size"]
    px = (L.SCREEN_PX[0] * 4, L.SCREEN_PX[1] * 4)
    reg = Region((0, 0) + px, w, h, LCD)
    backdrop(reg, w, h, upper)
    lanes = [w * 0.25, w * 0.5, w * 0.75]
    if upper:
        if frame:
            lane = (frame - 1) % 3
            rock_segment(reg, lanes[lane], 8.0 + 9.0 * frame, 7.0, SEGMENT)
            score = f"{frame * 10:04d}"
            for k, ch in enumerate(score):
                digit(reg, ch, w - 17.0 + 4.0 * k, 2.0, 3.0, 5.0, SEGMENT)
        else:
            for k in range(4):
                digit(reg, "0", w - 17.0 + 4.0 * k, 2.0, 3.0, 5.0, SEGMENT)
    else:
        lane = {0: 1, 1: 0, 2: 1, 3: 2}[frame]
        ship_segment(reg, lanes[lane], h - 11.0, 8.0, SEGMENT)
        if frame == 2:                                           # a shot, going up
            reg.rect_(lanes[lane] - 0.5, 4.0, lanes[lane] + 0.5, h - 17.0, SEGMENT)
        if frame == 0:                                           # the clock, at rest
            for k, ch in enumerate("1200"):
                digit(reg, ch, 4.0 + 5.4 * k + (2.0 if k > 1 else 0.0), 3.0, 4.2, 7.0, SEGMENT)
            reg.circle(15.5, 5.0, 0.5, SEGMENT)
            reg.circle(15.5, 8.0, 0.5, SEGMENT)
            reg.text("AM", "arialbd.ttf", 2.4, 1.6, 5.0, SEGMENT, anchor="lm")
        else:
            reg.text("GAME A", "arialbd.ttf", 2.2, 2.0, 3.0, SEGMENT, anchor="lm")
    return reg.img.convert("RGB")


# ---- The faces -------------------------------------------------------------------------------------------------------

def lower():
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["lower"], w, d, BROWN)

    def at(u, v):
        return u + w / 2, d - v
    reg.rect_(*at(-w / 2 + 2.5, d - 2.5), *at(w / 2 - 2.5, 2.5), CREAM, r=1.5)
    for (u0, u1), lean in ((L.PANELS["left"], -1), (L.PANELS["right"], 1)):    # the brown panels, their inner corners cut
        cut = 8.0
        if lean < 0:
            reg.poly([at(u0, d - 6.0), at(u1, d - 6.0), at(u1, 36.0), at(u1 - cut, 30.0), at(u0, 30.0)], BROWN)
        else:
            reg.poly([at(u0, d - 6.0), at(u1, d - 6.0), at(u1, 30.0), at(u0 + cut, 30.0), at(u0, 36.0)], BROWN)
    (bu, bv), (bw, bh) = L.BADGE["at"], L.BADGE["size"]
    reg.rect_(*at(bu - bw / 2, bv + bh / 2), *at(bu + bw / 2, bv - bh / 2), (196, 190, 176), r=0.8)
    for k, word in enumerate(("GAME", "&", "WATCH")):
        reg.text(word, "arialbd.ttf", 2.8, *at(bu, bv + 3.0 - 3.0 * k), INK)
    (du, dv) = L.DPAD["at"]
    s = L.DPAD["size"] / 2 + 1.0
    a = L.DPAD["arm"] / 2 + 1.0
    for x0, y0, x1, y1 in ((-s, -a, s, a), (-a, -s, a, s)):
        reg.rect_(*at(du + x0, dv + y1), *at(du + x1, dv + y0), (200, 194, 180), r=1.0)
    reg.text("CONTROLLER", "arialbd.ttf", 2.4, *at(du, 10.0), INK)
    sw, sh = L.SMALL["size"]
    for name, label in (("game_a", "GAME A"), ("game_b", "GAME B"), ("time", "TIME")):
        u, v = L.SMALL[name]
        reg.rect_(*at(u - sw / 2 - 0.8, v + sh / 2 + 0.8), *at(u + sw / 2 + 0.8, v - sh / 2 - 0.8), CREAM, r=sh / 2 + 0.8)
        reg.text(label, "arialbd.ttf", 1.7, *at(u, v - sh / 2 - 1.9), CREAM)
    for name, label in (("alarm", "ALARM"), ("acl", "ACL")):
        u, v = L.LIGHTS[name]
        reg.circle(*at(u, v), 0.9, (180, 176, 160))
        reg.text(label, "arial.ttf", 1.5, *at(u, v - 2.4), CREAM)
    (ju, jv), jr = L.JUMP["at"], L.JUMP["r"]
    reg.circle(*at(ju, jv), jr + 1.4, (204, 198, 184))
    reg.text("JUMP", "arialbd.ttf", 2.6, *at(ju, 10.0), INK)
    (nu, nv), (nw, nh) = L.NINTENDO["at"], L.NINTENDO["size"]
    reg.rect_(*at(nu - nw / 2, nv + nh / 2), *at(nu + nw / 2, nv - nh / 2), BROWN, r=nh / 2)
    reg.rect_(*at(nu - nw / 2 + 1.0, nv + nh / 2 - 1.0), *at(nu + nw / 2 - 1.0, nv - nh / 2 + 1.0), (200, 190, 176),
              r=nh / 2 - 1.0)
    reg.text("Nintendo", "arialbi.ttf", 3.6, *at(nu, nv), BROWN)
    for k in range(40):                                        # the ribbon along the back
        u = -34.0 + 68.0 * k / 39
        reg.rect_(*at(u - 0.5, d - 0.5), *at(u + 0.5, d - 4.0), (70, 80, 110) if k % 2 else (230, 230, 236))
    (lu, lv), (lw, lh) = L.LOWER_LCD["at"], L.LOWER_LCD["size"]
    reg.rect_(*at(lu - lw / 2 - 3.0, lv + lh / 2 + 3.0), *at(lu + lw / 2 + 3.0, lv - lh / 2 - 3.0), PANEL, r=1.0)
    paste_lcd(reg, at, (lu, lv), (lw, lh), lcd(False, 0))
    return reg


def upper():
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["upper"], w, d, BROWN)

    def at(u, v):
        return u + w / 2, d - v
    reg.rect_(*at(-w / 2 + 2.5, d - 2.5), *at(w / 2 - 2.5, 2.5), CREAM, r=1.5)
    (s0, s1) = L.SIDE["v"]
    for (u0, u1) in (L.SIDE["left"], L.SIDE["right"]):
        reg.rect_(*at(u0, s1), *at(u1, s0), PANEL, r=1.0, outline=shade(CREAM, -0.12), width=0.4)
        reg.line([at(u0 + 1.0, (s0 + s1) / 2), at(u1 - 1.0, (s0 + s1) / 2)], shade(CREAM, -0.1), 0.4)
    (tu, tv), (tw, th) = L.TITLE["at"], L.TITLE["size"]
    reg.rect_(*at(tu - tw / 2, tv + th / 2), *at(tu + tw / 2, tv - th / 2), BROWN, r=th / 2)
    reg.text("ODYSSEY", "arialbd.ttf", 4.0, *at(tu, tv), (236, 226, 210))
    for u, v in L.SCREWS:
        reg.circle(*at(u, v), 1.5, (190, 190, 194), outline=(120, 120, 124), width=0.3)
        reg.line([at(u - 1.0, v), at(u + 1.0, v)], (110, 110, 114), 0.3)
    (lu, lv), (lw, lh) = L.UPPER_LCD["at"], L.UPPER_LCD["size"]
    reg.rect_(*at(lu - lw / 2 - 3.0, lv + lh / 2 + 3.0), *at(lu + lw / 2 + 3.0, lv - lh / 2 - 3.0), PANEL, r=1.0)
    paste_lcd(reg, at, (lu, lv), (lw, lh), lcd(True, 0))
    return reg


def paste_lcd(reg, at, middle, size, picture):
    (u, v), (w, h) = middle, size
    reg.rect_(*at(u - w / 2 - 0.6, v + h / 2 + 0.6), *at(u + w / 2 + 0.6, v - h / 2 - 0.6), (30, 30, 28))
    x0, y0, x1, y1 = reg.box(*at(u - w / 2, v + h / 2), *at(u + w / 2, v - h / 2))
    reg.img.paste(picture.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BROWN)
    for reg in (lower(), upper()):
        reg.paste(image)
    for name in ("lower_1", "lower_2", "lower_3", "upper_1", "upper_2", "upper_3"):
        x, y, w, h = L.REGIONS[name]
        image.paste(lcd(name.startswith("upper"), int(name[-1])).resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(image)
    for name, colour in (("brown", BROWN), ("cream", CREAM), ("dark", rgb(L.COLOURS["key"])), ("lit", (255, 60, 40)),
                         ("metal", (190, 190, 194))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "gameandwatch_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
