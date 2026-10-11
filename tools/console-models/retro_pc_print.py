"""The retro PCs' printing, for the console theme's DOS, Windows 3.x and Windows 9x models (retro_pc.py).
retro_pc_layout.py has the faces, their parts and where each is in the atlas.

Writes two images per set into a folder:
- <set>_print.png: the printed faces. The case's front (its drives, badge, turbo display, lights, buttons and
  keylock, power switch and vents) and back (the power supply's fan and sockets, the ports and expansion cards), and
  the monitor's band under its screen (its badge, knobs or buttons and power light), the vents on its top, and the
  label on its back.
- <set>_screen.png: the CRT's glass, its raster showing the era's desktop: for DOS a two-panel file commander, for
  Windows 3.x a Program Manager, for Windows 9x a desktop with a game in a window and the taskbar.

The brand (Odyssey), the games and the programs on the screens are made up. Run it with the system Python (Pillow):

    python tools/console-models/retro_pc_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retro_pc_layout as L  # noqa: E402
from windows_pc_print import Region, gradient, mix  # noqa: E402


def rgb(hex_colour):
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def shade(colour, t):
    """colour (an (r, g, b) tuple) darkened (t < 0) or lightened (t > 0)."""
    return mix(colour, (0, 0, 0) if t < 0 else (255, 255, 255), abs(t))


def raised(reg, x0, y0, x1, y1, fill, r=1.0, edge=0.5):
    """A part standing off its face: a lit top and left edge, a shadowed bottom and right."""
    reg.rect_(x0, y0, x1, y1, shade(fill, -0.28), r=r)
    reg.rect_(x0, y0, x1 - edge, y1 - edge, shade(fill, 0.22), r=r)
    reg.rect_(x0 + edge, y0 + edge, x1 - edge, y1 - edge, fill, r=max(0.0, r - edge))


def sunken(reg, x0, y0, x1, y1, fill, r=1.0, edge=0.5):
    reg.rect_(x0, y0, x1, y1, shade(fill, 0.25), r=r)
    reg.rect_(x0, y0, x1 - edge, y1 - edge, shade(fill, -0.5), r=r)
    reg.rect_(x0 + edge, y0 + edge, x1 - edge, y1 - edge, fill, r=max(0.0, r - edge))


def led(reg, x, y, r, colour, lit=True):
    c = rgb(colour)
    if lit:
        halo = reg.layer()
        ImageDraw.Draw(halo).ellipse(reg.box(x - r * 2.2, y - r * 2.2, x + r * 2.2, y + r * 2.2), fill=c + (90,))
        reg.over(halo.filter(ImageFilter.GaussianBlur(r * 0.9 * reg.sx)))
        reg.circle(x, y, r, c, outline=shade(c, -0.4), width=0.3)
        reg.circle(x - r * 0.3, y - r * 0.3, r * 0.35, shade(c, 0.6))
    else:
        reg.circle(x, y, r, shade(c, -0.6), outline=shade(c, -0.75), width=0.3)


SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
            "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def seven_segment(reg, digit, x, y, w, h, colour):
    """A seven-segment digit in the box (x, y, w, h), its segments slanted a little."""
    t = w * 0.16
    slant = w * 0.12
    def p(px, py):
        return (x + px + slant * (1 - (py - y) / h), py)
    segs = {"a": ((t, y), (w - t, y)), "g": ((t, y + h / 2), (w - t, y + h / 2)), "d": ((t, y + h), (w - t, y + h))}
    for name, ((x0, y0), (x1, y1)) in segs.items():
        if name in SEGMENTS[digit]:
            reg.poly([p(x0 + t * 0.6, y0 - t / 2), p(x1 - t * 0.6, y0 - t / 2), p(x1, y0), p(x1 - t * 0.6, y0 + t / 2),
                      p(x0 + t * 0.6, y0 + t / 2), p(x0, y0)], colour)
    vert = {"f": (t / 2, y, y + h / 2), "b": (w - t / 2, y, y + h / 2), "e": (t / 2, y + h / 2, y + h),
            "c": (w - t / 2, y + h / 2, y + h)}
    for name, (cx, y0, y1) in vert.items():
        if name in SEGMENTS[digit]:
            reg.poly([p(cx, y0 + t * 0.6), p(cx + t / 2, y0 + t * 1.1), p(cx + t / 2, y1 - t * 1.1), p(cx, y1 - t * 0.6),
                      p(cx - t / 2, y1 - t * 1.1), p(cx - t / 2, y0 + t * 1.1)], colour)


# -- The faces' parts ------------------------------------------------------------------------------------------------

TEXT = (92, 88, 78)
DARK = (22, 22, 22)


def drive_face(reg, x, y, w, h, base):
    raised(reg, x, y, x + w, y + h, shade(base, -0.06), r=0.8)


def floppy35(reg, x, y, w, h, base):
    """A 3.5-inch drive's face: the slot behind its door, the eject button and the light."""
    face = shade(base, -0.06)
    raised(reg, x, y, x + w, y + h, face, r=0.8)
    sunken(reg, x + 10, y + 6.5, x + w - 10, y + 12.5, shade(face, -0.12), r=1.0)
    reg.rect_(x + 13, y + 9, x + w - 13, y + 10.4, DARK, r=0.6)
    raised(reg, x + w - 22, y + 16, x + w - 9, y + 21, shade(face, -0.04), r=1.0)
    reg.rect_(x + 11, y + 17.5, x + 17, y + 19.5, (58, 110, 52), r=0.5)
    reg.text("1.44 MB", "arialbd.ttf", 2.8, x + w / 2, y + 18.5, shade(face, -0.42))


def floppy525(reg, x, y, w, h, base):
    """A 5.25-inch drive's face: the long slot, the latch across it, and the light."""
    face = shade(base, -0.08)
    raised(reg, x, y, x + w, y + h, face, r=0.8)
    sunken(reg, x + 10, y + 12, x + w - 10, y + 24, shade(face, -0.1), r=1.5)
    reg.rect_(x + 14, y + 16.5, x + w - 14, y + 19.5, DARK, r=1.0)
    lx = x + w * 0.58                                   # the latch, turned down: closed
    raised(reg, lx - 5, y + 9, lx + 5, y + 31, shade(face, -0.1), r=2.5, edge=0.8)
    reg.rect_(lx - 1.2, y + 12, lx + 1.2, y + 28, shade(face, -0.3), r=1.0)
    reg.rect_(x + 12, y + 31, x + 20, y + 34, (120, 36, 30), r=0.6)
    reg.text("1.2 MB", "arialbd.ttf", 3.0, x + w - 24, y + 33, shade(face, -0.42))


def floppy35adapter(reg, x, y, w, h, base):
    """A 3.5-inch drive in a 5.25-inch bay's frame."""
    face = shade(base, -0.03)
    raised(reg, x, y, x + w, y + h, face, r=0.8)
    for gy in (y + 4, y + h - 5):
        reg.line([(x + 4, gy), (x + w - 4, gy)], shade(face, -0.12), 0.5)
    floppy35(reg, x + (w - 101.6) / 2, y + (h - 25.4) / 2, 101.6, 25.4, base)


def cdcaddy(reg, x, y, w, h, base):
    """An early CD-ROM drive, loaded with a caddy: its wide flap, the eject button, the light and the jack."""
    face = shade(base, -0.1)
    raised(reg, x, y, x + w, y + h, face, r=0.8)
    sunken(reg, x + 8, y + 6, x + w - 8, y + 23, shade(face, -0.22), r=1.0)
    reg.rect_(x + 10, y + 8, x + w - 10, y + 21, shade(face, -0.12), r=0.8)
    reg.line([(x + 12, y + 14.5), (x + w - 12, y + 14.5)], shade(face, -0.3), 0.6)
    reg.text("CD-ROM", "arialbd.ttf", 4.2, x + 24, y + 32, shade(face, -0.5))
    reg.text("DOUBLE SPEED", "arial.ttf", 2.6, x + 58, y + 32.3, shade(face, -0.42))
    reg.circle(x + 84, y + 32, 2.4, DARK, outline=shade(face, -0.35), width=0.4)
    reg.rect_(x + 96, y + 31, x + 104, y + 33.5, (120, 36, 30), r=0.5)
    raised(reg, x + w - 30, y + 28, x + w - 10, y + 36, shade(face, -0.04), r=1.2)


def cdrom(reg, x, y, w, h, base):
    """A tray-loading CD-ROM drive: the tray's seam, the logo, the jack, volume, light and eject button."""
    face = shade(base, -0.04)
    raised(reg, x, y, x + w, y + h, face, r=0.8)
    reg.rect_(x + 4, y + 7, x + w - 4, y + 25, shade(face, -0.18), r=0.6)
    reg.rect_(x + 4.5, y + 7.5, x + w - 4.5, y + 24.4, face, r=0.5)
    reg.text("CD-ROM", "arialbd.ttf", 4.0, x + 24, y + 16, shade(face, -0.5))
    reg.text("24X", "arialbd.ttf", 4.6, x + w - 18, y + 16, (176, 40, 34))
    reg.circle(x + 14, y + 32, 2.4, DARK, outline=shade(face, -0.35), width=0.4)
    reg.circle(x + 27, y + 32, 3.2, shade(face, -0.25))
    reg.circle(x + 27, y + 32, 2.2, shade(face, -0.05))
    reg.rect_(x + 74, y + 31, x + 82, y + 33.5, (58, 110, 52), r=0.5)
    raised(reg, x + w - 34, y + 28.5, x + w - 10, y + 35.5, shade(face, -0.05), r=1.5)
    reg.text("\u25b2", "arial.ttf", 2.6, x + w - 22, y + 32, shade(face, -0.45))


def blank525(reg, x, y, w, h, base):
    face = shade(base, -0.02)
    raised(reg, x, y, x + w, y + h, face, r=0.8)
    for gy in (y + h * 0.36, y + h * 0.64):
        reg.line([(x + 6, gy), (x + w - 6, gy)], shade(face, -0.1), 0.6)
        reg.line([(x + 6, gy + 0.6), (x + w - 6, gy + 0.6)], shade(face, 0.2), 0.4)


def badge(reg, x, y, w, h, text, base, plate):
    brand, model = text.split("|")
    if plate:                                           # the 80s: a brushed silver plate
        raised(reg, x, y, x + w, y + h, (196, 198, 200), r=1.0)
        for k in range(int(h * 2)):
            reg.line([(x + 1, y + 1 + k * 0.5), (x + w - 1, y + 1 + k * 0.5)], (186 + (k * 7) % 18,) * 3, 0.2)
        reg.text(brand, "arialbd.ttf", h * 0.42, x + 6, y + h / 2, (34, 40, 66), anchor="lm")
        for k, c in enumerate(((210, 40, 40), (240, 170, 30), (40, 120, 200))):
            reg.rect_(x + w * 0.56 + k * 4.5, y + h * 0.3, x + w * 0.56 + k * 4.5 + 3, y + h * 0.7, c)
        reg.text(model, "arialbd.ttf", h * 0.36, x + w - 6, y + h / 2, (34, 40, 66), anchor="rm")
    else:                                               # the 90s: printed on the plastic
        for k, c in enumerate(((212, 52, 44), (60, 160, 70), (40, 110, 200), (240, 180, 30))):
            cx, cy = x + 4 + (k % 2) * 4.4, y + h / 2 - 4.2 + (k // 2) * 4.4
            reg.rect_(cx, cy, cx + 3.8, cy + 3.8, c, r=0.6)
        reg.text(brand, "arialbd.ttf", h * 0.5, x + 15, y + h / 2, shade(base, -0.55), anchor="lm")
        if model:
            reg.text(model, "arial.ttf", h * 0.36, x + w - 2, y + h / 2, shade(base, -0.45), anchor="rm")


def display(reg, x, y, w, h, text):
    """The turbo speed in red seven-segment digits behind a dark window."""
    sunken(reg, x, y, x + w, y + h, (30, 14, 14), r=1.0, edge=0.8)
    glow = reg.layer()
    inner = Region((0, 0, 1, 1), 1, 1, (0, 0, 0, 0))   # draws onto glow through reg's scale
    inner.img, inner.draw, inner.sx, inner.sy = glow, ImageDraw.Draw(glow), reg.sx, reg.sy
    dw = (w - 10) / len(text)
    for k, d in enumerate(text):
        seven_segment(inner, d, x + 5 + k * dw + dw * 0.1, y + h * 0.18, dw * 0.8, h * 0.64, (255, 46, 30, 255))
    reg.over(glow.filter(ImageFilter.GaussianBlur(1.2 * reg.sx)))
    reg.over(glow)
    reg.text("MHz", "arialbd.ttf", 3.0, x + w / 2, y + h + 4, TEXT)


def leds(reg, x, y, w, h, text, base):
    items = [t.split(":") for t in text.split("|")]
    for k, (name, colour) in enumerate(items):
        cx = x + w * (k + 0.5) / len(items)
        led(reg, cx, y + h * 0.36, 2.0, colour)
        reg.text(name, "arialbd.ttf", 3.0, cx, y + h * 0.8, shade(base, -0.5))


def button(reg, x, y, w, h, text, base):
    raised(reg, x, y, x + w, y + h, shade(base, -0.05), r=1.5)
    reg.rect_(x + 1.5, y + 1.5, x + w - 1.5, y + h - 1.5, shade(base, -0.02), r=1.0)
    if text:
        reg.text(text, "arialbd.ttf", 3.0, x + w / 2, y + h + 4, shade(base, -0.5))


def power(reg, x, y, w, h, base, label=True):
    raised(reg, x, y, x + w, y + h, shade(base, -0.04), r=2.0, edge=0.8)
    reg.rect_(x + 2, y + 2, x + w - 2, y + h - 2, shade(base, 0.03), r=1.5)
    reg.circle(x + w / 2, y + h / 2, min(w, h) * 0.18, None, outline=shade(base, -0.45), width=0.9)
    reg.rect_(x + w / 2 - 0.5, y + h / 2 - min(w, h) * 0.26, x + w / 2 + 0.5, y + h / 2, shade(base, -0.45))
    if label:
        reg.text("POWER", "arialbd.ttf", 3.0, x + w / 2, y - 4, shade(base, -0.5))


def keylock(reg, x, y, w, h):
    cx, cy, r = x + w / 2, y + h / 2, w / 2
    reg.circle(cx, cy, r, (150, 152, 156), outline=(90, 92, 96), width=0.6)
    reg.circle(cx, cy, r * 0.72, (200, 202, 206))
    reg.circle(cx - r * 0.2, cy - r * 0.2, r * 0.3, (232, 234, 236))
    reg.rect_(cx - 0.9, cy - r * 0.45, cx + 0.9, cy + r * 0.45, (40, 40, 42), r=0.5)
    reg.text("LOCK", "arialbd.ttf", 3.0, cx, y + h + 4, TEXT)


def vents(reg, x, y, w, h, base, tower=False):
    if tower:                                           # a grid of short slots
        for row in range(int(h // 8)):
            for col in range(int(w // 13)):
                sx, sy = x + col * 13 + (6.5 if row % 2 else 0), y + row * 8
                if sx + 9 <= x + w:
                    sunken(reg, sx, sy, sx + 9, sy + 4, shade(base, -0.55), r=1.6, edge=0.4)
    else:                                               # long grooves
        for k in range(int(h // 4.5)):
            gy = y + k * 4.5
            sunken(reg, x, gy, x + w, gy + 2.2, shade(base, -0.5), r=1.0, edge=0.3)


def sticker(reg, x, y, w, h, text):
    big, small = text.split("|")
    reg.rect_(x, y, x + w, y + h, (24, 40, 120), r=1.5)
    reg.rect_(x + 1, y + 1, x + w - 1, y + h - 1, None, r=1.2, outline=(220, 190, 60), width=0.5)
    reg.text(big, "arialbd.ttf", h * 0.5, x + w * 0.42, y + h * 0.48, (255, 214, 60))
    reg.text(small, "arialbd.ttf", h * 0.24, x + w * 0.8, y + h * 0.56, (255, 255, 255))


def knob(reg, x, y, w, h, base):
    cx, cy, r = x + w / 2, y + h / 2, w / 2
    reg.circle(cx, cy, r, shade(base, -0.3))
    reg.circle(cx, cy, r * 0.86, shade(base, -0.08))
    reg.circle(cx - r * 0.15, cy - r * 0.15, r * 0.55, shade(base, 0.04))
    reg.line([(cx, cy - r * 0.8), (cx, cy - r * 0.35)], shade(base, -0.5), 0.8)


def brand(reg, x, y, w, h, text, base):
    name, model = text.split("|")
    if model:
        reg.text(name, "arialbd.ttf", h * 0.46, x, y + h * 0.4, shade(base, -0.6), anchor="lm")
        reg.text(model, "arial.ttf", h * 0.3, x, y + h * 0.88, shade(base, -0.5), anchor="lm")
    else:
        badge(reg, x, y, w, h, text, base, plate=False)


def osd(reg, x, y, w, h, base):
    """The 90s monitor's on-screen menu buttons."""
    marks = ("MENU", "\u25c4", "\u25ba", "\u25b2", "\u25bc")
    bw = w / len(marks)
    for k, mark in enumerate(marks):
        x0 = x + k * bw + 1
        raised(reg, x0, y, x0 + bw - 2, y + h, shade(base, -0.06), r=1.5)
        reg.text(mark, "arialbd.ttf", 2.8 if k == 0 else 3.4, x0 + (bw - 2) / 2, y + h + 4, shade(base, -0.5))


def draw_parts(reg, parts, base, plate_badge, tower=False):
    for kind, x, y, w, h, _depth, text in parts:
        if kind == "floppy35":
            floppy35(reg, x, y, w, h, base)
        elif kind == "floppy525":
            floppy525(reg, x, y, w, h, base)
        elif kind == "floppy35adapter":
            floppy35adapter(reg, x, y, w, h, base)
        elif kind == "cdcaddy":
            cdcaddy(reg, x, y, w, h, base)
        elif kind == "cdrom":
            cdrom(reg, x, y, w, h, base)
        elif kind == "blank525":
            blank525(reg, x, y, w, h, base)
        elif kind == "badge":
            badge(reg, x, y, w, h, text, base, plate_badge)
        elif kind == "display":
            display(reg, x, y, w, h, text)
        elif kind == "leds":
            leds(reg, x, y, w, h, text, base)
        elif kind == "button":
            button(reg, x, y, w, h, text, base)
        elif kind == "power":
            power(reg, x, y, w, h, base, label=h > 25)
        elif kind == "keylock":
            keylock(reg, x, y, w, h)
        elif kind == "vents":
            vents(reg, x, y, w, h, base, tower)
        elif kind == "sticker":
            sticker(reg, x, y, w, h, text)
        elif kind == "knob":
            knob(reg, x, y, w, h, base)
        elif kind == "led":
            led(reg, x + w / 2, y + h / 2, w / 2, text)
        elif kind == "brand":
            brand(reg, x, y, w, h, text, base)
        elif kind == "osd":
            osd(reg, x, y, w, h, base)
        else:
            raise ValueError(kind)


# -- The backs -----------------------------------------------------------------------------------------------------

STEEL = (168, 168, 160)


def fan_grille(reg, cx, cy, r):
    reg.circle(cx, cy, r, shade(STEEL, -0.5))
    for k in range(1, 6):
        reg.circle(cx, cy, r * k / 6, None, outline=shade(STEEL, 0.1), width=1.4)
    for a in range(0, 180, 45):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        reg.line([(cx - r * c, cy - r * s), (cx + r * c, cy + r * s)], shade(STEEL, 0.1), 1.4)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        reg.circle(cx + dx * r * 0.92, cy + dy * r * 0.92, 2.2, shade(STEEL, -0.35))


def socket(reg, x, y, w, h):
    reg.rect_(x, y, x + w, y + h, (36, 36, 38), r=2.0)
    reg.rect_(x + 3, y + 3, x + w - 3, y + h - 3, (14, 14, 16), r=1.5)
    for k in (-1, 0, 1):
        reg.rect_(x + w / 2 + k * 5 - 0.8, y + h / 2 - 3, x + w / 2 + k * 5 + 0.8, y + h / 2 + 3, (150, 150, 150))


def dsub(reg, cx, cy, pins, colour=(40, 40, 42)):
    """A D-sub connector, pins wide."""
    w = pins * 2.8 + 6
    reg.rect_(cx - w / 2 - 3, cy - 6, cx + w / 2 + 3, cy + 6, shade(STEEL, 0.1), r=1.0)
    reg.poly([(cx - w / 2, cy - 4), (cx + w / 2, cy - 4), (cx + w / 2 - 2, cy + 4), (cx - w / 2 + 2, cy + 4)], colour)
    for k in range(pins):
        reg.circle(cx - (pins - 1) * 1.4 + k * 2.8, cy - 1.4, 0.6, (200, 190, 120))
    for k in range(pins - 1):
        reg.circle(cx - (pins - 2) * 1.4 + k * 2.8, cy + 1.4, 0.6, (200, 190, 120))


def din(reg, cx, cy, r, colour=(40, 40, 42)):
    reg.circle(cx, cy, r + 1.5, shade(STEEL, 0.1))
    reg.circle(cx, cy, r, colour)
    reg.circle(cx, cy, r * 0.62, (14, 14, 14))
    for a in (200, 240, 270, 300, 340):
        reg.circle(cx + r * 0.38 * math.cos(math.radians(a)), cy + r * 0.38 * math.sin(math.radians(a)), 0.5,
                   (200, 190, 120))


def slot_cover(reg, x, y, w, h, vertical):
    reg.rect_(x, y, x + w, y + h, shade(STEEL, 0.06), r=0.5)
    if vertical:
        reg.line([(x + w / 2, y + 6), (x + w / 2, y + h - 6)], shade(STEEL, -0.2), 0.6)
    else:
        reg.line([(x + 6, y + h / 2), (x + w - 6, y + h / 2)], shade(STEEL, -0.2), 0.6)
    reg.rect_(x + 0.5, y + 0.5, x + w - 0.5, y + h - 0.5, None, outline=shade(STEEL, -0.3), width=0.4)


def jacks(reg, cx, cy, colours, vertical):
    for k, c in enumerate(colours):
        x, y = (cx, cy + k * 9) if vertical else (cx + k * 9, cy)
        reg.circle(x, y, 3.2, c)
        reg.circle(x, y, 1.4, (14, 14, 14))


def desktop_back(atlas, rect, w, h, sound):
    reg = Region(rect, w, h, STEEL)
    reg.rect_(1, 1, w - 1, h - 1, None, outline=shade(STEEL, -0.25), width=0.8)
    # The power supply, right: its fan, the mains in and out sockets, the voltage switch.
    px = w - 158
    reg.rect_(px, 8, w - 8, h - 8, shade(STEEL, -0.08), r=2.0)
    fan_grille(reg, px + 50, h / 2, 40)
    socket(reg, px + 102, 22, 26, 20)
    socket(reg, px + 102, 56, 26, 20)
    reg.rect_(px + 106, 92, px + 124, 102, (190, 40, 30), r=1.0)
    reg.text("115V", "arialbd.ttf", 3.0, px + 115, 108, (40, 40, 40))
    # The keyboard's DIN socket, then the expansion slots: some cards, the rest covered.
    din(reg, px - 22, h - 34, 7.0)
    for k in range(8):
        x = 24 + k * 30
        slot_cover(reg, x, 14, 22, h - 28, vertical=True)
        cx = x + 11
        if k == 0:                                      # the graphics card
            reg.rect_(cx - 7, 30, cx + 7, 56, shade(STEEL, 0.1))
            dsub(reg, cx, 43, 5, colour=(30, 30, 90))
        elif k == 2:                                    # serial and parallel
            dsub(reg, cx, 36, 9, colour=(40, 40, 40))
            dsub(reg, cx, 70, 5)
        elif k == 4 and sound:                          # the sound card
            jacks(reg, cx, 30, [(60, 160, 70), (220, 120, 160), (90, 140, 220), (30, 30, 30)], vertical=True)
            dsub(reg, cx, 80, 7, colour=(50, 50, 52))
    reg.text("ODYSSEY COMPUTER  MADE IN TAIWAN", "arial.ttf", 3.2, 140, h - 6, (60, 60, 60))
    reg.paste(atlas)


def tower_back(atlas, rect, w, h):
    reg = Region(rect, w, h, STEEL)
    reg.rect_(1, 1, w - 1, h - 1, None, outline=shade(STEEL, -0.25), width=0.8)
    reg.rect_(8, 8, w - 8, 150, shade(STEEL, -0.08), r=2.0)          # the power supply
    fan_grille(reg, 62, 80, 42)
    socket(reg, 124, 26, 26, 20)
    socket(reg, 124, 62, 26, 20)
    reg.rect_(128, 100, 146, 110, (190, 40, 30), r=1.0)
    reg.text("230V", "arialbd.ttf", 3.0, 137, 116, (40, 40, 40))
    reg.rect_(20, 162, 170, 232, shade(STEEL, 0.08), r=1.0)           # the ATX ports
    din(reg, 36, 176, 5.5, colour=(120, 90, 180))
    din(reg, 36, 194, 5.5, colour=(80, 160, 90))
    for k in range(2):
        reg.rect_(52, 172 + k * 12, 64, 178 + k * 12, (20, 20, 20), r=0.5)
    dsub(reg, 118, 176, 13, colour=(170, 40, 110))
    dsub(reg, 94, 204, 5, colour=(40, 120, 140))
    dsub(reg, 142, 204, 5, colour=(40, 120, 140))
    jacks(reg, 52, 220, [(80, 160, 220), (100, 200, 80), (220, 120, 160)], vertical=False)
    for k in range(7):                                               # the expansion slots
        y = 250 + k * 20
        slot_cover(reg, 22, y, w - 52, 14, vertical=False)
        if k == 0:
            dsub(reg, 60, y + 7, 5, colour=(30, 30, 90))
        elif k == 2:
            jacks(reg, 50, y + 7, [(60, 160, 70), (220, 120, 160), (90, 140, 220)], vertical=False)
            dsub(reg, 110, y + 7, 7, colour=(220, 200, 60))
        elif k == 3:
            reg.rect_(50, y + 3, 66, y + 11, (40, 40, 40), r=1.0)              # a modem's phone sockets
            reg.rect_(72, y + 3, 88, y + 11, (40, 40, 40), r=1.0)
    for j in range(16):                                              # vent holes beside the slots
        reg.circle(w - 18, 250 + j * 8.6, 1.6, shade(STEEL, -0.5))
    reg.paste(atlas)


def monitor_vents(atlas, rect, colour):
    reg = Region(rect, 100.0, 100.0, colour)
    for row in range(12):
        y = 6 + row * 7.6
        for col in range(2):
            x0 = 8 + col * 44
            sunken(reg, x0, y, x0 + 40, y + 3.2, shade(colour, -0.55), r=1.4, edge=0.35)
    reg.paste(atlas)


def monitor_label(atlas, rect, colour, model):
    reg = Region(rect, 120.0, 90.0, colour)
    reg.rect_(20, 18, 100, 72, (236, 234, 226), r=1.5)
    reg.text("ODYSSEY", "arialbd.ttf", 6.0, 60, 26, (30, 30, 30))
    reg.text(model, "arial.ttf", 4.0, 60, 33, (40, 40, 40))
    for k in range(6):
        reg.line([(26, 40 + k * 4.5), (94 - (k * 13) % 30, 40 + k * 4.5)], (130, 130, 130), 1.2)
    reg.rect_(76, 56, 94, 68, None, outline=(40, 40, 40), width=0.6)
    reg.text("FCC", "arialbd.ttf", 4.5, 85, 62, (40, 40, 40))
    reg.paste(atlas)


def print_atlas(set_id, spec, out):
    case, mon, regions = spec["case"], spec["monitor"], spec["atlas"]
    atlas = Image.new("RGB", (L.ATLAS, L.ATLAS), (120, 120, 120))
    tower = case["kind"] == "tower"
    w, h = case["width"], case["height"] - case["feet"]
    bezel = rgb(case["bezel_colour"])
    front = Region(regions["front"], w, h, bezel)
    if tower:                                            # the bays' surround, a shade darker
        front.rect_(18, 16, w - 18, 152, shade(bezel, -0.05), r=3.0)
    draw_parts(front, case["front"], bezel, plate_badge=set_id == "dos", tower=tower)
    front.paste(atlas)
    if tower:
        tower_back(atlas, regions["back"], w, h)
    else:
        desktop_back(atlas, regions["back"], w, h, sound=set_id != "dos")
    colour = rgb(mon["colour"])
    strip = Region(regions["strip"], mon["width"], mon["strip"], colour)
    draw_parts(strip, mon["parts"], colour, plate_badge=False)
    strip.paste(atlas)
    monitor_vents(atlas, regions["vents"], colour)
    monitor_label(atlas, regions["label"], colour, mon["parts"][0][6].split("|")[1] or "MULTISCAN 15")
    atlas.save(out, optimize=True)


# -- The screens ---------------------------------------------------------------------------------------------------
# Each raster is drawn in its 640 x 480 pixels.

CGA = {"black": (0, 0, 0), "blue": (0, 0, 170), "cyan": (0, 170, 170), "grey": (170, 170, 170),
       "white": (255, 255, 255), "bcyan": (85, 255, 255), "yellow": (255, 255, 85)}
CELL_W, CELL_H = 8.0, 19.2                               # an 80 x 25 text screen


def chars(reg, col, row, s, colour, bg=None):
    if bg is not None:
        reg.rect_(col * CELL_W, row * CELL_H, (col + len(s)) * CELL_W, (row + 1) * CELL_H, bg)
    for k, ch in enumerate(s):
        if ch != " ":
            reg.text(ch, "lucon.ttf", 14.0, (col + k + 0.5) * CELL_W, (row + 0.5) * CELL_H, colour)


def double_box(reg, c0, r0, c1, r1, colour):
    """A double-lined frame round the cells c0..c1, r0..r1."""
    x0, y0 = (c0 + 0.5) * CELL_W, (r0 + 0.5) * CELL_H
    x1, y1 = (c1 + 0.5) * CELL_W, (r1 + 0.5) * CELL_H
    for d in (-1.5, 1.5):
        reg.rect_(x0 + d, y0 + d, x1 - d, y1 - d, None, outline=colour, width=1.0)


def commander(reg):
    """A two-panel file commander on DOS: the games folder left, the drive's root right."""
    reg.rect_(0, 0, 640, 480, CGA["black"])
    left = [("..", "UP--DIR", "", "")] + [(n, "SUB-DIR", d, t) for n, d, t in (
        ("ASTRO", "03-14-91", "10:22"), ("CASTLE", "11-02-90", "21:05"), ("DUNGEON", "06-30-92", "18:40"),
        ("FLIGHT", "01-19-92", "09:12"), ("GOLF", "08-08-91", "14:31"), ("PINBALL", "04-22-93", "20:17"),
        ("RACER", "02-11-93", "16:58"), ("SOCCER", "09-27-92", "11:03"), ("TANKS", "12-05-91", "22:46"))] + [
        ("games   bat", "412", "02-11-93", "17:01"), ("menu    exe", "48213", "02-11-93", "17:00"),
        ("readme  txt", "3907", "02-11-93", "17:00")]
    right = [(n, "SUB-DIR", d, t) for n, d, t in (("DOS", "06-01-93", "06:00"), ("GAMES", "02-11-93", "16:55"),
                                                     ("TEMP", "02-14-93", "08:30"), ("UTILS", "07-19-92", "12:12"))] + [
        ("autoexec bat", "362", "02-11-93", "17:04"), ("command  com", "54645", "06-01-93", "06:00"),
        ("config   sys", "218", "02-11-93", "17:04")]
    for c0, title, files, cursor in ((0, " C:\\GAMES ", left, 7), (40, " C:\\ ", right, -1)):
        reg.rect_(c0 * CELL_W, 0, (c0 + 40) * CELL_W, 23 * CELL_H, CGA["blue"])
        double_box(reg, c0, 0, c0 + 39, 22, CGA["bcyan"])
        for col in (13, 23, 32):                         # the columns' dividers
            x = (c0 + col + 0.5) * CELL_W
            reg.line([(x, 1.0 * CELL_H), (x, 19.5 * CELL_H)], CGA["bcyan"], 1.0)
        for d in (-1.5, 1.5):
            reg.line([((c0 + 0.5) * CELL_W, 19.5 * CELL_H + d), ((c0 + 39.5) * CELL_W, 19.5 * CELL_H + d)],
                     CGA["bcyan"], 1.0)
        chars(reg, c0 + 20 - len(title) // 2, 0, title, CGA["black"] if c0 == 0 else CGA["bcyan"],
              CGA["cyan"] if c0 == 0 else CGA["blue"])
        for col, head in ((5, "Name"), (16, "Size"), (26, "Date"), (34, "Time")):
            chars(reg, c0 + col, 1, head, CGA["yellow"])
        for k, (name, size, date, time) in enumerate(files):
            row = 2 + k
            colour = CGA["white"] if size == "SUB-DIR" or name == ".." else CGA["bcyan"]
            if k == cursor:
                reg.rect_((c0 + 1) * CELL_W, row * CELL_H, (c0 + 39) * CELL_W, (row + 1) * CELL_H, CGA["cyan"])
                colour = CGA["black"]
            chars(reg, c0 + 1, row, name, colour)
            chars(reg, c0 + 23 - len(size), row, size, colour)
            chars(reg, c0 + 24, row, date, colour)
            chars(reg, c0 + 33, row, time, colour)
        info = "RACER        SUB-DIR  02-11-93 16:58" if c0 == 0 else "54,645 bytes in 3 files"
        chars(reg, c0 + 2, 20, info, CGA["bcyan"])
    chars(reg, 0, 23, "C:\\GAMES>", CGA["grey"])
    reg.rect_(9 * CELL_W, 23.8 * CELL_H, 10 * CELL_W, 24 * CELL_H - 1, CGA["grey"])   # the cursor
    keys = ("Help", "Menu", "View", "Edit", "Copy", "RenMov", "Mkdir", "Delete", "PullDn", "Quit")
    col = 0
    for k, name in enumerate(keys):
        number = str(k + 1)
        chars(reg, col, 24, number, CGA["white"], CGA["black"])
        col += len(number)
        chars(reg, col, 24, name.ljust(6), CGA["black"], CGA["cyan"])
        col += 6 if k < 9 else 70 - col + 10
    reg.rect_(col * CELL_W, 24 * CELL_H, 640, 480, CGA["black"])


# Windows' 16 colours.
W_GREY, W_DARK, W_NAVY, W_WHITE, W_BLACK = (192, 192, 192), (128, 128, 128), (0, 0, 128), (255, 255, 255), (0, 0, 0)
W_TEAL = (0, 128, 128)


def bevel_box(reg, x0, y0, x1, y1, fill=W_GREY, pressed=False):
    """A Windows 3D box: white and black edges, a grey inner shadow."""
    light, dark = (W_BLACK, W_WHITE) if pressed else (W_WHITE, W_BLACK)
    reg.rect_(x0, y0, x1, y1, dark)
    reg.rect_(x0, y0, x1 - 1, y1 - 1, light)
    reg.rect_(x0 + 1, y0 + 1, x1 - 1, y1 - 1, W_DARK if not pressed else W_GREY)
    reg.rect_(x0 + 1, y0 + 1, x1 - 2, y1 - 2, fill)


def icon(reg, kind, x, y):
    """A 32 x 32 icon at (x, y), its top left."""
    if kind == "files":                                  # a filing cabinet
        reg.rect_(x + 6, y + 2, x + 26, y + 30, (200, 160, 40), outline=W_BLACK, width=1)
        for k in range(3):
            reg.rect_(x + 8, y + 4 + k * 9, x + 24, y + 10 + k * 9, (240, 200, 70), outline=W_BLACK, width=1)
            reg.rect_(x + 14, y + 6 + k * 9, x + 18, y + 8 + k * 9, W_BLACK)
    elif kind == "control":                              # a monitor with a slider beside it
        reg.rect_(x + 2, y + 4, x + 22, y + 20, W_GREY, outline=W_BLACK, width=1)
        reg.rect_(x + 5, y + 7, x + 19, y + 17, W_TEAL)
        reg.rect_(x + 8, y + 22, x + 16, y + 26, W_GREY, outline=W_BLACK, width=1)
        reg.rect_(x + 24, y + 4, x + 30, y + 28, W_GREY, outline=W_BLACK, width=1)
        reg.rect_(x + 25, y + 14, x + 29, y + 18, (200, 0, 0))
    elif kind == "printer":
        reg.rect_(x + 8, y + 4, x + 24, y + 14, W_WHITE, outline=W_BLACK, width=1)
        reg.rect_(x + 3, y + 13, x + 29, y + 26, W_GREY, outline=W_BLACK, width=1)
        reg.rect_(x + 6, y + 22, x + 26, y + 28, W_WHITE, outline=W_BLACK, width=1)
        reg.rect_(x + 23, y + 16, x + 26, y + 18, (0, 200, 0))
    elif kind == "dos":                                  # a prompt in a window
        reg.rect_(x + 2, y + 5, x + 30, y + 27, W_BLACK, outline=W_GREY, width=1)
        reg.rect_(x + 2, y + 5, x + 30, y + 9, W_NAVY)
        reg.text("C:\\>", "lucon.ttf", 7, x + 12, y + 17, W_WHITE)
    elif kind == "setup":                                # a computer and a box
        reg.rect_(x + 2, y + 16, x + 20, y + 28, W_GREY, outline=W_BLACK, width=1)
        reg.rect_(x + 5, y + 4, x + 19, y + 15, W_GREY, outline=W_BLACK, width=1)
        reg.rect_(x + 7, y + 6, x + 17, y + 13, W_NAVY)
        reg.rect_(x + 20, y + 12, x + 30, y + 28, (230, 200, 120), outline=W_BLACK, width=1)
    elif kind == "notes":                                # a notepad
        reg.rect_(x + 6, y + 2, x + 26, y + 30, W_WHITE, outline=W_BLACK, width=1)
        reg.rect_(x + 6, y + 2, x + 26, y + 6, (0, 160, 220))
        for k in range(5):
            reg.line([(x + 9, y + 10 + k * 4), (x + 23, y + 10 + k * 4)], W_DARK, 1)
    elif kind == "cards":                                # two playing cards
        reg.rect_(x + 3, y + 4, x + 19, y + 26, W_NAVY, outline=W_BLACK, width=1)
        reg.rect_(x + 12, y + 6, x + 28, y + 28, W_WHITE, outline=W_BLACK, width=1)
        reg.text("A", "arialbd.ttf", 9, x + 17, y + 11, (200, 0, 0))
        reg.text("\u2665", "arial.ttf", 11, x + 21, y + 21, (200, 0, 0))
    elif kind == "mines":                                # a bomb on a grid
        reg.rect_(x + 2, y + 2, x + 30, y + 30, W_GREY, outline=W_DARK, width=1)
        reg.circle(x + 16, y + 17, 8, W_BLACK)
        reg.line([(x + 16, y + 9), (x + 22, y + 4)], (120, 80, 0), 1.5)
        reg.circle(x + 23, y + 4, 2, (255, 200, 0))
        reg.circle(x + 13, y + 14, 2, W_WHITE)
    elif kind == "racer":                                # a red car on a chequered flag
        for i in range(4):
            for j in range(4):
                reg.rect_(x + 2 + i * 7, y + 2 + j * 7, x + 9 + i * 7, y + 9 + j * 7, W_WHITE if (i + j) % 2 else W_BLACK)
        reg.rect_(x + 3, y + 17, x + 29, y + 25, (220, 0, 0), r=2)
        reg.rect_(x + 9, y + 13, x + 22, y + 18, (220, 0, 0), r=2)
        reg.circle(x + 9, y + 26, 3, W_BLACK)
        reg.circle(x + 23, y + 26, 3, W_BLACK)
    elif kind == "computer":                             # My Computer
        reg.rect_(x + 4, y + 2, x + 26, y + 20, (220, 216, 200), outline=W_BLACK, width=1)
        reg.rect_(x + 7, y + 5, x + 23, y + 16, W_TEAL)
        reg.rect_(x + 2, y + 22, x + 30, y + 30, (220, 216, 200), outline=W_BLACK, width=1)
        reg.rect_(x + 18, y + 25, x + 27, y + 27, W_DARK)
    elif kind == "network":
        for dx in (0, 14):
            reg.rect_(x + 1 + dx, y + 4, x + 15 + dx, y + 15, (220, 216, 200), outline=W_BLACK, width=1)
            reg.rect_(x + 3 + dx, y + 6, x + 13 + dx, y + 13, W_TEAL)
        reg.line([(x + 8, y + 16), (x + 8, y + 26), (x + 22, y + 26), (x + 22, y + 16)], W_BLACK, 1.2)
        reg.rect_(x + 11, y + 23, x + 19, y + 29, (220, 216, 200), outline=W_BLACK, width=1)
    elif kind == "bin":                                  # a wire basket
        reg.poly([(x + 6, y + 6), (x + 26, y + 6), (x + 23, y + 30), (x + 9, y + 30)], (220, 220, 220))
        for k in range(5):
            reg.line([(x + 8 + k * 4, y + 7), (x + 10 + k * 3, y + 29)], W_DARK, 1)
        reg.rect_(x + 4, y + 4, x + 28, y + 8, (200, 200, 200), outline=W_BLACK, width=1)
    elif kind == "group":                                # a minimised program group
        reg.rect_(x + 3, y + 5, x + 29, y + 27, W_WHITE, outline=W_BLACK, width=1)
        reg.rect_(x + 3, y + 5, x + 29, y + 10, W_NAVY)
        for k in range(3):
            reg.rect_(x + 6 + k * 8, y + 14, x + 11 + k * 8, y + 19, (k * 90, 160 - k * 40, 200 - k * 60))


def title_31(reg, x0, y0, x1, text, active):
    """A Windows 3.1 title bar: the control-menu box, the title, minimise and maximise."""
    h = 18
    reg.rect_(x0, y0, x1, y0 + h, W_NAVY if active else W_WHITE)
    reg.rect_(x0, y0, x0 + h, y0 + h, W_GREY, outline=W_BLACK, width=1)
    reg.rect_(x0 + 4, y0 + 7, x0 + h - 3, y0 + 10, W_WHITE, outline=W_BLACK, width=1)
    for k, up in enumerate((False, True)):
        bx = x1 - (2 - k) * h
        bevel_box(reg, bx, y0, bx + h, y0 + h)
        cx, cy = bx + h / 2, y0 + h / 2
        tri = [(cx - 4, cy + 2), (cx + 4, cy + 2), (cx, cy - 2)] if up else [(cx - 4, cy - 2), (cx + 4, cy - 2), (cx, cy + 2)]
        reg.poly(tri, W_BLACK)
    reg.text(text, "arialbd.ttf", 11, (x0 + h + x1 - 2 * h) / 2, y0 + h / 2 + 0.5, W_WHITE if active else W_BLACK)
    reg.line([(x0, y0 + h), (x1, y0 + h)], W_BLACK, 1)


def window_31(reg, x0, y0, x1, y1, title, active, frame=4):
    reg.rect_(x0, y0, x1, y1, W_GREY if active else W_WHITE, outline=W_BLACK, width=1)
    reg.rect_(x0 + frame, y0 + frame, x1 - frame, y1 - frame, W_WHITE, outline=W_BLACK, width=1)
    title_31(reg, x0 + frame, y0 + frame, x1 - frame, title, active)
    return x0 + frame + 1, y0 + frame + 19


def icons_31(reg, x, y, items, step=72):
    for k, (kind, label) in enumerate(items):
        cx = x + k * step
        icon(reg, kind, cx - 16, y)
        reg.text(label, "arial.ttf", 10, cx, y + 41, W_BLACK)


def program_manager(reg):
    """Windows 3.x's Program Manager: the Main and Games groups open, the others minimised."""
    reg.rect_(0, 0, 640, 480, W_GREY)
    cx, cy = window_31(reg, 6, 4, 634, 452, "Program Manager", active=True)
    reg.rect_(cx, cy, 629, cy + 18, W_WHITE)
    for x, name in ((12, "File"), (46, "Options"), (104, "Window"), (164, "Help")):
        reg.text(name, "arial.ttf", 11, cx + x, cy + 9.5, W_BLACK, anchor="lm")
    reg.line([(cx, cy + 18), (629, cy + 18)], W_BLACK, 1)
    top = cy + 19
    reg.rect_(cx, top, 629, 447, W_WHITE)
    gx, gy = window_31(reg, cx + 10, top + 10, cx + 390, top + 182, "Main", active=True)
    icons_31(reg, gx + 44, gy + 12, [("files", "File Manager"), ("control", "Control Panel"),
                                     ("printer", "Print Manager"), ("setup", "Setup"), ("dos", "DOS Prompt")])
    icons_31(reg, gx + 44, gy + 82, [("notes", "Notepad"), ("racer", "Odyssey Racer")])
    gx, gy = window_31(reg, cx + 300, top + 196, cx + 610, top + 340, "Games", active=False)
    icons_31(reg, gx + 46, gy + 14, [("cards", "Patience"), ("mines", "Sweeper"), ("racer", "Racer")], step=90)
    for k, name in enumerate(("Accessories", "StartUp", "Applications")):
        x = cx + 40 + k * 82
        icon(reg, "group", x - 16, 370)
        reg.text(name, "arial.ttf", 10, x, 411, W_BLACK)


def title_95(reg, x0, y0, x1, text):
    reg.rect_(x0, y0, x1, y0 + 18, W_NAVY)
    icon_small(reg, x0 + 2, y0 + 1)
    reg.text(text, "tahomabd.ttf", 11, x0 + 22, y0 + 9.5, W_WHITE, anchor="lm")
    for k, mark in enumerate(("_", "\u25a1", "\u00d7")):
        bx = x1 - 3 * 16 - 2 + k * 16 + (2 if k == 2 else 0)
        bevel_box(reg, bx, y0 + 2, bx + 16, y0 + 16)
        reg.text(mark, "arialbd.ttf", 12 if k else 10, bx + 8, y0 + 8.5 - (3 if k == 0 else 0), W_BLACK)


def icon_small(reg, x, y):
    for i in range(2):
        for j in range(2):
            reg.rect_(x + 2 + i * 8, y + 2 + j * 8, x + 9 + i * 8, y + 9 + j * 8, W_WHITE if (i + j) % 2 else W_BLACK)
    reg.rect_(x + 3, y + 10, x + 16, y + 15, (220, 0, 0), r=1.5)


def flag(reg, x, y, s):
    """The Start button's four-colour flag, waving."""
    for k, c in enumerate(((240, 40, 30), (40, 180, 60), (30, 90, 230), (250, 200, 20))):
        i, j = k % 2, k // 2
        x0, y0 = x + i * s * 0.52, y + j * s * 0.5 + (s * 0.08 if i else 0)
        reg.poly([(x0, y0), (x0 + s * 0.46, y0 - s * 0.06), (x0 + s * 0.46, y0 + s * 0.38), (x0, y0 + s * 0.44)], c)


def racing_scene(reg, x0, y0, x1, y1):
    """Odyssey Racer's game: a road to the horizon, hills, a car."""
    w, h = x1 - x0, y1 - y0
    horizon = y0 + h * 0.42
    sky = gradient((max(1, round(w * reg.sx)), max(1, round((horizon - y0) * reg.sy))),
                   [(0, (40, 80, 200)), (1, (150, 200, 255))])
    reg.img.paste(sky, (round(x0 * reg.sx), round(y0 * reg.sy)))
    reg.rect_(x0, horizon, x1, y1, (40, 150, 50))
    reg.poly([(x0, horizon), (x0 + w * 0.2, horizon - 40), (x0 + w * 0.42, horizon - 14), (x0 + w * 0.62, horizon - 52),
              (x0 + w * 0.85, horizon - 18), (x1, horizon - 30), (x1, horizon)], (70, 110, 150))
    for k in range(10):                                  # the verge's stripes
        t0, t1 = k / 10, (k + 1) / 10
        def edge(t, side):
            return x0 + w / 2 + side * (6 + t * t * w * 0.4)
        ya, yb = horizon + (y1 - horizon) * t0 * t0, horizon + (y1 - horizon) * t1 * t1
        for side in (-1, 1):
            reg.poly([(edge(t0, side), ya), (edge(t0, side) + side * (1 + t0 * 10), ya),
                      (edge(t1, side) + side * (1 + t1 * 10), yb), (edge(t1, side), yb)],
                     (230, 40, 40) if k % 2 else W_WHITE)
    reg.poly([(x0 + w / 2 - 6, horizon), (x0 + w / 2 + 6, horizon), (x0 + w / 2 + w * 0.4 + 6, y1),
              (x0 + w / 2 - w * 0.4 - 6, y1)], (90, 90, 96))
    for k in range(5):
        t0, t1 = (k + 0.3) / 5, (k + 0.6) / 5
        ya, yb = horizon + (y1 - horizon) * t0 * t0, horizon + (y1 - horizon) * t1 * t1
        reg.poly([(x0 + w / 2 - 0.5 - t0 * 3, ya), (x0 + w / 2 + 0.5 + t0 * 3, ya), (x0 + w / 2 + 0.5 + t1 * 3, yb),
                  (x0 + w / 2 - 0.5 - t1 * 3, yb)], W_WHITE)
    cx, cy = x0 + w / 2 - 20, y1 - 34                     # the player's car, from behind
    reg.rect_(cx - 42, cy, cx + 42, cy + 22, (210, 20, 20), r=4)
    reg.rect_(cx - 28, cy - 14, cx + 28, cy + 2, (180, 10, 10), r=4)
    reg.rect_(cx - 24, cy - 11, cx + 24, cy - 2, (60, 80, 120), r=2)
    reg.rect_(cx - 46, cy + 4, cx + 46, cy + 9, (30, 30, 30))
    for side in (-1, 1):
        reg.rect_(cx + side * 44 - 9, cy + 12, cx + side * 44 + 9, cy + 30, (20, 20, 20), r=3)
        reg.rect_(cx + side * 30 - 8, cy + 12, cx + side * 30 + 8, cy + 16, (255, 200, 40))
    reg.text("LAP 2/3", "arialbd.ttf", 14, x0 + 10, y0 + 14, W_WHITE, anchor="lm")
    reg.text("0:48.20", "arialbd.ttf", 14, x1 - 10, y0 + 14, (255, 230, 60), anchor="rm")


def desktop95(reg):
    """A 95-style desktop: its icons, Odyssey Racer in a window, and the taskbar."""
    reg.rect_(0, 0, 640, 480, W_TEAL)
    for k, (kind, label) in enumerate((("computer", "My Computer"), ("network", "Network"), ("bin", "Recycle Bin"),
                                       ("racer", "Odyssey Racer"))):
        x, y = 36, 10 + k * 72
        icon(reg, kind, x - 16, y)
        reg.text(label, "tahoma.ttf", 10.5, x, y + 42, W_WHITE)
    x0, y0, x1, y1 = 120, 40, 600, 420
    bevel_box(reg, x0, y0, x1, y1)
    title_95(reg, x0 + 3, y0 + 3, x1 - 3, "Odyssey Racer")
    for x, name in ((8, "Game"), (50, "Options"), (106, "Help")):
        reg.text(name, "tahoma.ttf", 11, x0 + x, y0 + 31, W_BLACK, anchor="lm")
    bevel_box(reg, x0 + 4, y0 + 42, x1 - 4, y1 - 4, pressed=True)
    racing_scene(reg, x0 + 6, y0 + 44, x1 - 6, y1 - 6)

    reg.rect_(0, 452, 640, 480, W_GREY)
    reg.line([(0, 452.5), (640, 452.5)], W_WHITE, 1)
    bevel_box(reg, 2, 455, 58, 477)
    flag(reg, 6, 459, 14)
    reg.text("Start", "tahomabd.ttf", 11, 40, 466.5, W_BLACK)
    bevel_box(reg, 62, 455, 222, 477, fill=(224, 224, 224), pressed=True)
    icon_small(reg, 66, 457)
    reg.text("Odyssey Racer", "tahomabd.ttf", 11, 86, 466.5, W_BLACK, anchor="lm")
    reg.rect_(560, 455, 638, 477, W_DARK)
    reg.rect_(561, 456, 638, 477, W_WHITE)
    reg.rect_(561, 456, 637, 476, W_GREY)
    reg.poly([(568, 463), (572, 463), (577, 459), (577, 474), (572, 470), (568, 470)], W_BLACK)
    reg.text("4:20 PM", "tahoma.ttf", 11, 610, 466.5, W_BLACK)


def screen_image(spec, out):
    """The glass: dark, its raster centred with rounded corners, a vignette, and a sheen across it."""
    mon = spec["monitor"]
    gw, gh = mon["glass"]
    rw, rh = mon["raster"]
    iw, ih = L.SCREEN_PX
    image = Image.new("RGB", L.SCREEN_PX, (26, 30, 29))
    x0, y0 = round((gw - rw) / 2 / gw * iw), round((gh - rh) / 2 / gh * ih)
    pw, ph = round(rw / gw * iw), round(rh / gh * ih)
    raster = Region((0, 0, pw, ph), 640.0, 480.0, (0, 0, 0))
    {"commander": commander, "program_manager": program_manager, "desktop95": desktop95}[spec["screen"]](raster)
    lit = raster.img.convert("RGB").resize((pw, ph), Image.LANCZOS)
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=pw * 0.025, fill=255)
    image.paste(lit, (x0, y0), mask.filter(ImageFilter.GaussianBlur(1.2)))

    # The raster dims towards its edges, and the glass catches a soft light from the top left.
    vignette = Image.new("L", L.SCREEN_PX, 0)
    ImageDraw.Draw(vignette).rounded_rectangle([x0 + pw * 0.04, y0 + ph * 0.05, x0 + pw * 0.96, y0 + ph * 0.95],
                                               radius=pw * 0.12, fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(pw * 0.06))
    dark = Image.new("RGB", L.SCREEN_PX, (0, 0, 0))
    image = Image.composite(image, Image.blend(image, dark, 0.35), vignette)
    sheen = Image.new("L", L.SCREEN_PX, 0)
    ImageDraw.Draw(sheen).ellipse([-iw * 0.3, -ih * 0.6, iw * 0.75, ih * 0.42], fill=26)
    sheen = sheen.filter(ImageFilter.GaussianBlur(iw * 0.08))
    image = Image.composite(Image.new("RGB", L.SCREEN_PX, (255, 255, 255)), image, sheen)
    image.save(out, optimize=True)


if __name__ == "__main__":
    folder = os.path.abspath(sys.argv[1])
    os.makedirs(folder, exist_ok=True)
    for set_id, spec in L.SETS.items():
        print_atlas(set_id, spec, os.path.join(folder, f"{set_id}_print.png"))
        screen_image(spec, os.path.join(folder, f"{set_id}_screen.png"))
        print(f"{set_id}: {spec['name']}")
