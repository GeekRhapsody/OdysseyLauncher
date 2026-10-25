"""NAOMI's card's printing and screens, for the console theme's NAOMI model (tools/console-models/naomi.py).

Draws its two atlases, their regions as naomi_layout.py places them. naomi_print.png, each in millimetres as the
model's UVs map it: the marquee (NAOMI's logo, its O orange, lit from behind), the speaker panel (two grilles and SEGA
on a badge), the control panel's overlay (dark, its stripes, 1P and 2P, POWER CONTROL SYSTEM's place taken by
ODYSSEY CITY, a made-up name), the lower cabinet's front (the two coin doors, their locks and coin returns), and the
swatches small parts take their colour from. naomi_media.png: the screens, 4:3 (NAOMI's logo on white as the board
starts; Odyssey's title, CREDIT 1 and PRESS START; two frames of play). Run it with the system Python (Pillow):

    python tools/console-models/naomi_print.py <out folder>

It writes naomi_print.png and naomi_media.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import naomi_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
ORANGE = (240, 92, 40)
PANEL_DARK = (40, 42, 48)


def naomi_logo(d, cx, cy, h, ink, scale=1.0):
    """NAOMI's logo on a Pillow draw, h tall, its middle at (cx, cy): N A M I in thin geometric capitals, the O an
    orange ring."""
    w = h * 0.86                       # a letter's width
    gap = h * 0.22
    stroke = max(1, round(h * 0.11))
    total = 4.08 * w + 3.5 * gap + stroke   # N, A, the wider O, M; the I is a stroke
    x = cx - total / 2
    top, bottom = cy - h / 2, cy + h / 2
    # N
    d.line([(x, bottom), (x, top), (x + w, bottom), (x + w, top)], fill=ink, width=stroke, joint="curve")
    x += w + gap
    # A, its crossbar low
    d.line([(x, bottom), (x + w / 2, top), (x + w, bottom)], fill=ink, width=stroke, joint="curve")
    d.line([(x + w * 0.22, cy + h * 0.2), (x + w * 0.78, cy + h * 0.2)], fill=ink, width=stroke)
    x += w + gap * 0.5                                     # the A's slant leaves room of its own
    # O, the orange ring
    d.ellipse([x, top, x + w * 1.08, bottom], outline=ORANGE, width=round(stroke * 1.5))
    x += w * 1.08 + gap
    # M
    d.line([(x, bottom), (x, top), (x + w / 2, cy + h * 0.15), (x + w, top), (x + w, bottom)], fill=ink, width=stroke,
           joint="curve")
    x += w + gap
    # I
    d.line([(x + stroke / 2, top), (x + stroke / 2, bottom)], fill=ink, width=stroke)


# ---- The cabinet's printing --------------------------------------------------------------------------------------------

def marquee():
    (y0, z0), (y1, z1) = L.MARQUEE
    w, h = L.WIDTH - 50.0, math.hypot(y1 - y0, z1 - z0)
    reg = Region(L.REGIONS["marquee"], w, h, (250, 250, 248))
    glow = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for k in range(12):                                     # a soft band of light across it, from the tube behind
        a = 18 - k
        gd.rectangle(reg.box(0.0, h * (0.5 - 0.03 * k), w, h * (0.5 + 0.03 * k)), fill=(255, 236, 200, a))
    reg.over(glow)
    naomi_logo(reg.draw, *reg.p(w / 2, h * 0.47), 54.0 * reg.sy, (20, 20, 22))
    reg.rect_(0.0, h - 9.0, w, h - 5.0, ORANGE)
    reg.rect_(0.0, 4.0, w, 7.0, ORANGE)
    return reg


def speakers():
    (y0, z0), (y1, z1) = L.SPEAKERS
    w, h = L.WIDTH - 50.0, math.hypot(y1 - y0, z1 - z0)
    reg = Region(L.REGIONS["speakers"], w, h, CASE)
    for cx in (w * 0.22, w * 0.78):
        reg.rect_(cx - 70.0, 6.0, cx + 70.0, h - 6.0, (26, 26, 28), r=6.0)
        for i in range(14):
            for j in range(6):
                reg.circle(cx - 60.0 + i * 9.2, 12.0 + j * 9.0, 2.2, (60, 60, 64))
    reg.rect_(w / 2 - 110.0, 10.0, w / 2 + 110.0, h - 10.0, (36, 120, 96), r=4.0)
    reg.text("SEGA", "ariblk.ttf", 30.0, w / 2, h / 2, (250, 250, 250))
    return reg


def panel():
    w, d = L.WIDTH, L.PANEL_DEPTH                            # the whole control panel's top
    reg = Region(L.REGIONS["panel"], w, d, CASE)

    def at(x, v):
        return x + w / 2, d - v
    reg.rect_(*at(-340.0, 238.0), *at(340.0, 8.0), PANEL_DARK, r=6.0)    # the overlay
    for k, colour in enumerate(((60, 160, 90), (226, 70, 120), (70, 120, 200))):   # the stripes along the front
        reg.rect_(*at(-w / 2, 22.0 + k * 5.0), *at(w / 2, 20.0 + k * 5.0), colour)
    for side, (sx, sv) in ((-1, L.STICKS["p1"]), (1, L.STICKS["p2"])):
        reg.circle(*at(sx, sv), 34.0, shade(PANEL_DARK, -0.3))
        reg.text("1P" if side < 0 else "2P", "arialbd.ttf", 14.0, *at(sx, sv + 50.0), (220, 220, 220))
    reg.rect_(*at(-80.0, 190.0), *at(80.0, 100.0), shade(PANEL_DARK, 0.12), r=8.0)
    reg.text("ODYSSEY CITY", "ariblk.ttf", 12.0, *at(0.0, 172.0), (255, 214, 70))
    reg.text("1 PLAYER", "arialbd.ttf", 7.0, *at(-30.0, 112.0), (220, 220, 220))
    reg.text("2 PLAYERS", "arialbd.ttf", 7.0, *at(30.0, 112.0), (220, 220, 220))
    for buttons in (L.BUTTONS["p1"], L.BUTTONS["p2"]):
        for x, v in buttons:
            reg.circle(*at(x, v), L.BUTTONS["r"] + 4.0, shade(PANEL_DARK, -0.35))
    return reg


def front():
    w, h = L.WIDTH, 700.0
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    (z0, z1) = L.DOORS["z"]
    for x0, x1 in L.DOORS["x"]:
        reg.rect_(*at(x0, z1), *at(x1, z0), shade(CASE, -0.06), r=10.0, outline=shade(CASE, -0.25), width=2.0)
    reg.rect_(*at(150.0, 560.0), *at(190.0, 470.0), (40, 40, 44), r=6.0)            # the coin return
    reg.circle(*at(-40.0, 420.0), 9.0, (150, 152, 156))                              # the lock
    reg.circle(*at(-40.0, 420.0), 3.0, (40, 40, 44))
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (marquee(), speakers(), panel(), front()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("green", (70, 210, 90)), ("pink", (240, 120, 170)), ("yellow", (240, 200, 40)),
                         ("yellow_lit", (255, 246, 160)), ("black", (16, 16, 18)), ("metal", rgb(L.COLOURS["metal"])),
                         ("dark", PANEL_DARK), ("coin", (210, 200, 160)), ("white", (250, 250, 250))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "naomi_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -------------------------------------------------------------------------------------------------------

W, H = L.SCREEN_PX
SS = 2


def font(name, size):
    return ImageFont.truetype(FONTS + name, max(1, round(size * SS)))


def boot():
    img = Image.new("RGB", (W * SS, H * SS), (250, 250, 250))
    d = ImageDraw.Draw(img)
    naomi_logo(d, W * SS / 2, H * SS * 0.45, 48 * SS, (20, 20, 22))
    d.text((W * SS / 2, H * SS * 0.66), "SEGA", font=font("ariblk.ttf", 20), fill=(30, 80, 200), anchor="mm")
    return img


def title():
    img = space((W * SS, H * SS)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((W * SS / 2, 80 * SS), "ODYSSEY", font=font("ariblk.ttf", 64), fill=(255, 214, 70), anchor="mm",
           stroke_width=3 * SS, stroke_fill=(120, 30, 10))
    ship(d, 150 * SS, 200 * SS, 3.0 * SS, "#FFFFFF", "#FFB23C")
    d.text((W * SS / 2, 300 * SS), "PRESS START", font=font("arialbd.ttf", 22), fill=(255, 255, 255), anchor="mm")
    d.text((W * SS - 10 * SS, H * SS - 12 * SS), "CREDIT 1", font=font("arialbd.ttf", 14), fill=(255, 255, 255),
           anchor="rm")
    return img


def game(frame):
    img = space((W * SS, H * SS)).convert("RGB")
    d = ImageDraw.Draw(img)
    rng = random.Random(9 + frame)
    for _ in range(40):
        x, y = rng.randrange(W * SS), rng.randrange(H * SS)
        d.ellipse([x - SS, y - SS, x + SS, y + SS], fill=(255, 255, 255))
    sx = 120 + frame * 14
    ship(d, sx * SS, 190 * SS, 2.2 * SS, "#FFFFFF", "#FFB23C")
    d.line([((sx + 40) * SS, 190 * SS), ((sx + 150 + frame * 30) * SS, 190 * SS)], fill=(255, 236, 80), width=3 * SS)
    for ax, ay, r in ((360, 186 - frame * 6, 24), (420, 90, 16), (300, 300, 14)):
        if frame == 1 and ax == 360:
            for k in range(22):
                a = random.Random(k).uniform(0, 2 * math.pi)
                rr = random.Random(k + 50).uniform(4, 30)
                px, py = ax + rr * math.cos(a), ay + rr * math.sin(a)
                d.ellipse([(px - 3) * SS, (py - 3) * SS, (px + 3) * SS, (py + 3) * SS], fill=(255, 200, 60))
            continue
        d.ellipse([(ax - r) * SS, (ay - r) * SS, (ax + r) * SS, (ay + r) * SS], fill=(140, 96, 70),
                  outline=(90, 60, 44), width=2 * SS)
    d.text((14 * SS, 16 * SS), f"1UP {1200 + 250 * frame:06d}", font=font("arialbd.ttf", 16), fill=(255, 255, 255),
           anchor="lm")
    d.text((W * SS / 2, 16 * SS), "HI 050000", font=font("arialbd.ttf", 16), fill=(255, 214, 70), anchor="mm")
    return img


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    for name, art in (("boot", boot()), ("title", title()), ("game1", game(0)), ("game2", game(1))):
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(art.resize((w, h), Image.LANCZOS), (x, y))
    path = os.path.join(out, "naomi_media.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
