"""The Desktop Apps card's printing and screens (desktop_print.png), for the console theme's model (desktop.py).

One image, laid out as desktop_layout.REGIONS says: the screen at rest (a made-up desktop: its wallpaper, a column of
shortcuts, each icon with its shortcut arrow, the first a made-up game, Odyssey; the taskbar and its clock), the
Odyssey shortcut selected, the game's window three ways (its title bar, then its title screen and two moments of its
play), the base from above (the keyboard in its well, the touchpad, the speaker grilles), and swatches. Run it with
the system Python (Pillow):

    python tools/console-models/desktop_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desktop_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

BODY = rgb(L.COLOURS["body"])
WHITE = (246, 247, 250)
SW, SH = L.SCREEN["size"]
NAMES = ["Odyssey", "Notes", "Music", "Photos", "Files", "Browser"]


# ---- The desktop -----------------------------------------------------------------------------------------------------

def wallpaper(reg):
    """A made-up wallpaper: an indigo to teal gradient, soft bands of light, a ringed planet low on the right."""
    w, h = reg.img.size
    layer = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(layer)
    for y in range(h):
        for x in range(0, w, 4):
            t = 0.55 * x / w + 0.45 * y / h
            colour = (round(28 + 10 * t), round(30 + 110 * t), round(92 + 60 * t), 255)
            d.line([(x, y), (x + 3, y)], fill=colour)
    bands = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bands)
    for k, (amp, base, alpha) in enumerate(((0.07, 0.62, 70), (0.05, 0.7, 50), (0.09, 0.55, 40))):
        pts = [(x, h * (base + amp * math.sin(2 * math.pi * x / w * (1.2 + 0.3 * k) + k))) for x in range(0, w + 8, 8)]
        bd.line(pts, fill=(200, 236, 255, alpha), width=max(2, round(h / 60)))
    layer = Image.alpha_composite(layer, bands.filter(ImageFilter.GaussianBlur(h / 90)))
    reg.img.alpha_composite(layer)
    cx, cy, r = reg.p(SW * 0.8, SH * 0.68)[0], reg.p(0, SH * 0.68)[1], SH * 0.13 * reg.sx
    reg.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(242, 140, 82, 255))
    reg.draw.ellipse([cx - r * 0.82, cy - r * 0.95, cx + r * 0.7, cy + r * 0.5], fill=(247, 166, 106, 255))
    reg.draw.arc([cx - r * 1.8, cy - r * 0.36, cx + r * 1.8, cy + r * 0.36], 160, 380, fill=(240, 230, 255, 255),
                 width=max(2, round(r / 9)))


def glyph(reg, name, cx, cy, s):
    """An icon, s across, its middle at (cx, cy) in the region's millimetres: a rounded tile and its picture."""
    tiles = dict(Odyssey=(70, 40, 140), Notes=(250, 210, 70), Music=(236, 80, 130), Photos=(60, 150, 236),
                 Files=(240, 176, 60), Browser=(40, 170, 160))
    h = s / 2
    reg.rect_(cx - h, cy - h, cx + h, cy + h, tiles[name], r=s * 0.22)
    if name == "Odyssey":
        art = space((120, 120)).convert("RGB")
        a, b, c, d = reg.box(cx - h + 1.0, cy - h + 1.0, cx + h - 1.0, cy + h - 1.0)
        mask = Image.new("L", (round(c - a), round(d - b)), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, mask.width - 1, mask.height - 1], radius=s * 0.18 * reg.sx,
                                               fill=255)
        reg.img.paste(art.resize(mask.size, Image.LANCZOS), (round(a), round(b)), mask)
        dd = ImageDraw.Draw(reg.img)
        ship(dd, cx * reg.sx - s * 0.12 * reg.sx, cy * reg.sy, s * 0.03 * reg.sx, "#FFFFFF", "#FFB23C")
    elif name == "Notes":
        reg.rect_(cx - h * 0.55, cy - h * 0.62, cx + h * 0.55, cy + h * 0.62, WHITE, r=0.6)
        for k in range(4):
            reg.line([(cx - h * 0.4, cy - h * 0.3 + k * h * 0.22), (cx + h * 0.4, cy - h * 0.3 + k * h * 0.22)],
                     (150, 150, 160), 0.4)
    elif name == "Music":
        reg.circle(cx - h * 0.18, cy + h * 0.32, h * 0.2, WHITE)
        reg.rect_(cx - h * 0.02, cy - h * 0.5, cx + h * 0.08, cy + h * 0.32, WHITE)
        reg.poly([(cx + h * 0.08, cy - h * 0.5), (cx + h * 0.45, cy - h * 0.3), (cx + h * 0.08, cy - h * 0.18)], WHITE)
    elif name == "Photos":
        reg.poly([(cx - h * 0.6, cy + h * 0.45), (cx - h * 0.15, cy - h * 0.2), (cx + h * 0.15, cy + h * 0.15),
                  (cx + h * 0.3, cy), (cx + h * 0.6, cy + h * 0.45)], WHITE)
        reg.circle(cx + h * 0.32, cy - h * 0.35, h * 0.14, (255, 240, 160))
    elif name == "Files":
        reg.rect_(cx - h * 0.6, cy - h * 0.35, cx - h * 0.05, cy - h * 0.15, (255, 226, 150), r=0.4)
        reg.rect_(cx - h * 0.6, cy - h * 0.22, cx + h * 0.6, cy + h * 0.5, (255, 226, 150), r=0.6)
    else:
        reg.circle(cx, cy, h * 0.55, None, outline=WHITE, width=0.6)
        reg.line([(cx - h * 0.55, cy), (cx + h * 0.55, cy)], WHITE, 0.5)
        reg.draw.ellipse(reg.box(cx - h * 0.22, cy - h * 0.55, cx + h * 0.22, cy + h * 0.55), outline=WHITE,
                         width=reg.width(0.5))
    # The shortcut's arrow, at the icon's lower left.
    a = s * 0.3
    x0, y0 = cx - h, cy + h - a
    reg.rect_(x0, y0, x0 + a, y0 + a, WHITE, r=0.3)
    reg.draw.arc(reg.box(x0 + a * 0.2, y0 + a * 0.3, x0 + a * 0.95, y0 + a * 1.05), 180, 270, fill=(30, 100, 220),
                 width=reg.width(a * 0.14))
    reg.poly([(x0 + a * 0.55, y0 + a * 0.18), (x0 + a * 0.82, y0 + a * 0.32), (x0 + a * 0.55, y0 + a * 0.5)],
             (30, 100, 220))


def icon_middle(k):
    """The k-th shortcut's icon's middle, (u, v) on the screen."""
    return L.ICONS["x"], L.ICONS["top"] - k * L.ICONS["pitch"]


def selection_box(k):
    """The box the selection highlight fills round the k-th shortcut and its label, (u0, v0, u1, v1)."""
    u, v = icon_middle(k)
    s = L.ICONS["size"]
    return u - 14.0, v - s / 2 - 8.5, u + 14.0, v + s / 2 + 1.5


def desktop(selected=False):
    """The screen: u across (-172 at the left), v up (0 at the bottom); drawn as a region of the screen's size."""
    reg = Region((0, 0, 640, 360), SW, SH, (20, 20, 30))

    def at(u, v):
        return u + SW / 2, SH - v

    wallpaper(reg)
    if selected:
        u0, v0, u1, v1 = selection_box(L.ODYSSEY)
        layer = reg.layer()
        ImageDraw.Draw(layer).rounded_rectangle(reg.box(*at(u0, v1), *at(u1, v0)), radius=1.6 * reg.sx,
                                                fill=(150, 200, 255, 90), outline=(190, 225, 255, 200),
                                                width=reg.width(0.4))
        reg.over(layer)
    s = L.ICONS["size"]
    for k, name in enumerate(NAMES):
        u, v = icon_middle(k)
        glyph(reg, name, *at(u, v), s)
        shadow = reg.layer()                                       # the label's soft shadow, then the label
        font = ImageFont.truetype(FONTS + "segoeui.ttf", max(1, round(3.4 * reg.sx)))
        ImageDraw.Draw(shadow).text(reg.p(*at(u + 0.3, v - s / 2 - 4.5)), name, font=font, fill=(0, 0, 0, 150),
                                    anchor="mm")
        reg.over(shadow.filter(ImageFilter.GaussianBlur(1.2)))
        reg.text(name, "segoeui.ttf", 3.4, *at(u, v - s / 2 - 4.2), WHITE)
    # The taskbar: its start button, a few apps, the clock.
    bar = reg.layer()
    ImageDraw.Draw(bar).rectangle(reg.box(*at(-SW / 2, 11.0), *at(SW / 2, 0.0)), fill=(14, 18, 34, 200))
    reg.over(bar)
    reg.circle(*at(-SW / 2 + 8.0, 5.5), 3.0, (120, 180, 255))
    reg.circle(*at(-SW / 2 + 8.0, 5.5), 1.2, (14, 18, 34))
    for k, name in enumerate(("Odyssey", "Notes", "Files", "Browser")):
        glyph(reg, name, *at(-20.0 + k * 12.0, 5.5), 7.0)
    reg.text("12:00", "segoeui.ttf", 3.2, *at(SW / 2 - 12.0, 5.5), WHITE)
    return reg.img.convert("RGB")


# ---- The game's window -----------------------------------------------------------------------------------------------

def window(frame):
    """The game's window: its title bar, its content (frame 0 the title screen, 1 and 2 its play)."""
    ww, wh = L.WINDOW["size"]
    reg = Region((0, 0, 320, 200), ww, wh, (20, 20, 30))
    bar = 9.0
    art = space((640, 400)).convert("RGB")
    d = ImageDraw.Draw(art)
    if frame == 0:
        ship(d, 200, 250, 4.2, "#FFFFFF", "#FFB23C")
    else:
        sx = (150, 230)[frame - 1]
        ship(d, sx, 230, 3.0, "#FFFFFF", "#FFB23C")
        for k, (x, y, r) in enumerate(((420, 120, 26), (520, 300, 34), (330, 330, 18))):
            x -= 40 * frame
            d.polygon([(x + r * math.cos(a), y + r * 0.85 * math.sin(a)) for a in [j * 0.9 + k for j in range(7)]],
                      fill=(150, 130, 120), outline=(90, 80, 76))
        if frame == 2:
            for j in range(3):
                d.line([(sx + 70 + j * 40, 230), (sx + 90 + j * 40, 230)], fill=(255, 230, 120), width=5)
    x0, y0, x1, y1 = reg.box(0.0, bar, ww, wh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    if frame == 0:
        reg.text("ODYSSEY", "ariblk.ttf", 22.0, ww / 2, bar + 40.0, (255, 214, 70))
        reg.text("PRESS ENTER", "segoeuib.ttf", 7.0, ww / 2, wh - 22.0, WHITE)
    else:
        reg.text("SCORE 0" + ("120" if frame == 1 else "240"), "segoeuib.ttf", 6.0, 8.0, bar + 8.0, WHITE, anchor="lm")
    reg.rect_(0.0, 0.0, ww, bar, (32, 34, 44))
    glyph(reg, "Odyssey", 5.0, bar / 2, 5.6)
    reg.text("Odyssey", "segoeui.ttf", 4.0, 10.0, bar / 2, WHITE, anchor="lm")
    for k, symbol in enumerate(("min", "max", "close")):
        x = ww - 6.0 - (2 - k) * 12.0
        if symbol == "close":
            reg.rect_(x - 6.0, 0.0, x + 6.0, bar, (196, 43, 28))
            reg.line([(x - 1.8, bar / 2 - 1.8), (x + 1.8, bar / 2 + 1.8)], WHITE, 0.5)
            reg.line([(x - 1.8, bar / 2 + 1.8), (x + 1.8, bar / 2 - 1.8)], WHITE, 0.5)
        elif symbol == "max":
            reg.rect_(x - 1.8, bar / 2 - 1.8, x + 1.8, bar / 2 + 1.8, None, outline=WHITE, width=0.4)
        else:
            reg.line([(x - 1.8, bar / 2), (x + 1.8, bar / 2)], WHITE, 0.4)
    reg.rect_(0.0, 0.0, ww, wh, None, outline=(80, 84, 96), width=0.4)
    return reg.img.convert("RGB")


# ---- The base --------------------------------------------------------------------------------------------------------

def keyboard():
    """The base from above: x across (-178 at the left), y down from the back (240)."""
    reg = Region(L.REGIONS["keyboard"], L.WIDTH, L.DEPTH, BODY)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    (wx0, wx1), (wy0, wy1) = L.WELL["x"], L.WELL["y"]
    reg.rect_(*at(wx0, wy1), *at(wx1, wy0), (40, 42, 46), r=2.0)
    pitch = (wx1 - wx0 - 4.0) / 15
    rows = [(wy1 - 6.0, 0.5, [1] * 15)]                                   # the function row, half height
    y = wy1 - 12.0
    for widths in ([1] * 13 + [2], [1.5] + [1] * 12 + [1.5], [1.8] + [1] * 11 + [2.2], [2.3] + [1] * 10 + [2.7],
                   [1, 1, 1, 1.3, 6.4, 1.3, 1, 1, 1, 1]):
        rows.append((y - pitch / 2, 1.0, widths))
        y -= pitch
    for yc, hfrac, widths in rows:
        x = wx0 + 2.0
        total = sum(widths)
        scale = (wx1 - wx0 - 4.0) / (total * pitch)
        for wkey in widths:
            w = wkey * pitch * scale
            h = pitch * hfrac
            reg.rect_(*at(x + 0.9, yc + h / 2 - 0.9), *at(x + w - 0.9, yc - h / 2 + 0.9), (24, 25, 28), r=1.6)
            reg.rect_(*at(x + 1.4, yc + h / 2 - 1.4), *at(x + w - 1.4, yc - h / 2 + 1.6), (30, 31, 35), r=1.4)
            x += w
    (tx0, tx1), (ty0, ty1) = L.TOUCHPAD["x"], L.TOUCHPAD["y"]
    reg.rect_(*at(tx0, ty1), *at(tx1, ty0), (98, 101, 107), r=4.0, outline=(84, 86, 92), width=0.4)
    for side in (-1, 1):
        for i in range(4):
            for j in range(26):
                reg.circle(*at(side * (wx1 + 9.0 + i * 3.2), wy0 + 4.0 + j * 4.6), 0.7, (60, 62, 66))
    reg.rect_(*at(wx1 + 6.0, wy1 + 9.0), *at(wx1 + 18.0, wy1 + 4.0), (40, 42, 46), r=1.0)     # the power key
    return reg


def paste(image, name, img):
    x, y, w, h = L.REGIONS[name]
    image.paste(img.resize((w, h), Image.LANCZOS), (x, y))


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BODY)
    plain, chosen = desktop(), desktop(selected=True)
    paste(image, "desktop", plain)
    u0, v0, u1, v1 = selection_box(L.ODYSSEY)
    sx, sy = chosen.width / SW, chosen.height / SH             # the desktop's own pixels per millimetre (supersampled)
    crop = chosen.crop((round((u0 + SW / 2) * sx), round((SH - v1) * sy), round((u1 + SW / 2) * sx),
                        round((SH - v0) * sy)))
    paste(image, "selected", crop)
    for k, name in enumerate(("title", "game_1", "game_2")):
        paste(image, name, window(k))
    keyboard().paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(body=BODY, dark=(40, 42, 46), black=(8, 8, 10), white=WHITE, bezel=(14, 14, 16), hinge=(30, 31, 34),
                   key=(30, 31, 35), lid=(96, 99, 106))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "desktop_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
