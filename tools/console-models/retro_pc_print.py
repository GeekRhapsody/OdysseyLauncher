"""The retro PC cards' printing and their screens' stills, for the console theme's DOS, Windows 3.x and Windows 9x
models (retro_pc.py). Each card's set is its own layout's (dos_layout.py, windows3x_layout.py, windows9x_layout.py), the
parts they share retro_pc_layout.py's; its screens are its own module's (dos_screens.py, ...), which its video draws
with too.

Writes three images for a set into a folder:
- <set>_print.png: the keyboard seen from above (the ledges, the well's floor, every key's top in its colour with its
  legends, the lights and the badge on the ledge behind the keys), the media (the floppy's two sides: its label with the
  made-up game, its shutter and hub; the CD's label) and the swatches.
- <set>_devices.png: the case's front (its drives' faces, the badge, the turbo display, the lights, the buttons, the
  keylock, the vents), its back (the power supply's fan and sockets, the ports and the expansion cards), the monitor's
  front (its bezel, the badge, the knobs, the power light and button under the screen) and the swatches.
- <set>_screen.png: the glass, GLASS_PX: the video's first frame, its still.

The brand (Odyssey) and the games are made up. Run it with the system Python (Pillow, numpy):

    python tools/console-models/retro_pc_print.py <set> <made-up games folder> <out folder>
"""

import importlib
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retro_pc_layout as K  # noqa: E402
from windows_pc_print import Region, mix  # noqa: E402


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


def floppy35(reg, x, y, w, h, base):
    """A 3.5-inch drive's face (101.6 x 25.4): the slot behind its flap (wide enough for a disk's 90 mm), the light and
    the eject button. The model cuts the slot and stands the button out of it (the layout's SLOT and EJECT)."""
    face = shade(base, -0.06)
    raised(reg, x, y, x + w, y + h, face, r=0.8)
    sunken(reg, x + 3.8, y + 6.6, x + w - 3.8, y + 13.0, shade(face, -0.1), r=1.2)
    reg.rect_(x + 4.8, y + 7.6, x + w - 4.8, y + 12.0, DARK, r=0.8)
    raised(reg, x + 78.0, y + 15.5, x + 95.0, y + 21.0, shade(face, -0.04), r=1.0)
    reg.rect_(x + 8.0, y + 17.0, x + 14.0, y + 19.5, (40, 70, 36), r=0.5)
    reg.text("1.44 MB", "arialbd.ttf", 2.8, x + 46.0, y + 18.5, shade(face, -0.42))


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
    reg.text("▲", "arial.ttf", 2.6, x + w - 22, y + 32, shade(face, -0.45))


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
    """Lights in a row, each name:colour, or name:colour:off printed unlit (the model lights it when it's on)."""
    items = [t.split(":") for t in text.split("|")]
    for k, item in enumerate(items):
        cx = x + w * (k + 0.5) / len(items)
        led(reg, cx, y + h * 0.36, 2.0, item[1], lit=len(item) < 3)
        reg.text(item[0], "arialbd.ttf", 3.0, cx, y + h * 0.8, shade(base, -0.5))


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
    marks = ("MENU", "◄", "►", "▲", "▼")
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


# -- The keyboard from above -----------------------------------------------------------------------------------------

INK = (44, 42, 40)


def window_glyph(reg, cx, cy, s, ink):
    """A small four-paned window, the Windows keys' sign (a made-up one, not Microsoft's)."""
    g = s * 0.08
    for qx in (-1, 1):
        for qy in (-1, 1):
            x0, y0 = cx + (g if qx > 0 else -s / 2), cy + (g if qy > 0 else -s / 2)
            reg.poly([(x0, y0), (x0 + s / 2 - g, y0 - s * 0.05), (x0 + s / 2 - g, y0 + s / 2 - g - s * 0.05),
                      (x0, y0 + s / 2 - g)], ink)


def legend(reg, key, a0, b0, a1, b1):
    """A key's legend on its top (a0..a1 across, b0..b1 down), as the Model M's were printed: a letter at its top left,
    a pair of characters one over the other, a word small at its top left, an arrow in its middle."""
    text = key["legend"]
    lines = text.split("\n")
    w = a1 - a0
    if not text:
        return
    if text in ("WIN", "MENU"):
        if text == "WIN":
            window_glyph(reg, (a0 + a1) / 2, (b0 + b1) / 2, 6.0, INK)
        else:
            reg.rect_((a0 + a1) / 2 - 2.6, (b0 + b1) / 2 - 3.0, (a0 + a1) / 2 + 2.6, (b0 + b1) / 2 + 3.0, None,
                      outline=INK, width=0.5)
            for k in range(3):
                y = (b0 + b1) / 2 - 1.4 + k * 1.4
                reg.line([((a0 + a1) / 2 - 1.5, y), ((a0 + a1) / 2 + 1.5, y)], INK, 0.4)
        return
    if all(ch in "←↑→↓" for ch in text) and key["name"] != "backspace":
        reg.text(text, "seguisym.ttf", 5.4, (a0 + a1) / 2, (b0 + b1) / 2, INK)
        return
    if key["name"] == "backspace":
        reg.text("←", "seguisym.ttf", 5.0, a0 + 4.0, b0 + 4.2, INK)
        return
    if len(lines) == 2 and len(lines[0]) == 1 and (len(lines[1]) == 1 or lines[0].isdigit()):
        big = lines[0].isdigit() and len(lines[1]) > 1          # a keypad key: the digit large, its word small
        reg.text(lines[0], "arial.ttf", 4.0, a0 + 2.0, b0 + 1.6, INK, anchor="lt")
        reg.text(lines[1], "arial.ttf", 2.2 if big else 4.0, a0 + 2.0, b1 - (1.8 if big else 5.6), INK, anchor="lt")
        return
    if len(text) == 1 or (text.startswith("F") and text[1:].isdigit()) or text in ("+", "-", "*", "/"):
        reg.text(text, "arial.ttf", 4.2 if len(text) == 1 else 3.2, a0 + 2.0, b0 + 1.6, INK, anchor="lt")
        return
    size = 2.3 if w < 20 else 2.6
    for k, line in enumerate(lines):
        reg.text(line, "arial.ttf", size, a0 + 1.8, b0 + 1.8 + k * size * 1.25, INK, anchor="lt")


def keyboard_top(atlas, spec):
    """The keyboard seen from above, its back at the region's top: the ledges, the well's floor, the keys' tops."""
    W, D = K.KB["width"], K.KB["depth"]
    C = {n: rgb(v) for n, v in spec.COLOURS.items()}
    case = C["kbcase"]
    reg = Region(spec.PRINT_REGIONS["kb_top"], W, D, case)

    def at(x, y):
        return x + W / 2, D - y
    wy0, wy1 = K.deck(2.5, 0.0)[0], K.deck(K.WELL_LENGTH - 2.5, 0.0)[0]
    a0, b1 = at(K.KEYS_X0 - 5.0, wy0)
    a1, b0 = at(K.KEYS_X0 + 23 * K.U + 5.0, wy1)
    reg.rect_(a0, b0, a1, b1, shade(case, -0.42))
    by = K.BACK_LEDGE[0]                                 # the ledge behind the well, a little lighter
    reg.rect_(0.0, 0.0, W, D - by, shade(case, 0.05))
    tops = K.key_tops(spec.KEYBOARD["windows"])
    for key in K.keys(spec.KEYBOARD["windows"]):
        x0, y0, x1, y1 = tops[key["name"]]
        a0, b1 = at(x0, y0)
        a1, b0 = at(x1, y1)
        colour = C[key["colour"]]
        reg.rect_(a0 - 0.8, b0 - 0.8, a1 + 0.8, b1 + 0.8, shade(colour, -0.06), r=1.4)
        reg.rect_(a0, b0, a1, b1, colour, r=1.0)
        reg.rect_(a0 + 0.6, b0 + 0.4, a1 - 0.6, b0 + 2.0, shade(colour, 0.08), r=0.8)     # the dish's back lip lit
        legend(reg, key, a0, b0, a1, b1)
    # The lights over the keypad, on the ledge: Num Lock on, as the machine starts.
    lx = K.LIGHTS_X + W / 2
    for k, (name, label) in enumerate(K.LIGHTS):
        cx = lx + (k + 0.5) * 4 * K.U / 3
        reg.rect_(cx - 3.4, 8.0, cx + 3.4, 11.6, (30, 30, 30), r=0.6)
        reg.rect_(cx - 2.8, 8.5, cx + 2.8, 11.1, (90, 255, 110) if name == "num" else (26, 60, 30), r=0.5)
        for j, word in enumerate(label.split()):
            reg.text(word, "arial.ttf", 2.0, cx, 15.0 + j * 2.6, INK)
    bx0, bx1 = K.BADGE                                   # the badge
    reg.rect_(bx0 + W / 2, 7.0, bx1 + W / 2, 17.0, (52, 54, 60), r=1.2)
    reg.text("ODYSSEY", "arialbd.ttf", 4.6, (bx0 + bx1) / 2 + W / 2, 12.0, (214, 216, 220))
    reg.paste(atlas)


# -- The media -------------------------------------------------------------------------------------------------------

def floppy_sides(atlas, spec, made_up):
    """The 3.5-inch floppy's two sides, its shutter at the regions' top: its top (the shutter, the arrow, the label with
    the made-up game's logo) and its underside (the shutter, the hub)."""
    (w, length) = K.FLOPPY["size"]
    C = {n: rgb(v) for n, v in spec.COLOURS.items()}
    body, metal = C["disk"], C["shutter"]
    top = Region(spec.PRINT_REGIONS["floppy"], w, length, body)
    top.rect_(0.6, 0.6, w - 0.6, length - 0.6, shade(body, 0.06), r=2.0)
    top.rect_(w * 0.5 - 30.0, 0.0, w * 0.5 + 21.0, 40.0, shade(metal, -0.05))           # the shutter
    top.rect_(w * 0.5 - 30.0, 0.0, w * 0.5 + 21.0, 40.0, None, outline=shade(metal, -0.3), width=0.5)
    top.rect_(w * 0.5 - 17.0, 4.0, w * 0.5 - 4.0, 34.0, (40, 30, 26))                   # its window: the disk
    top.poly([(6.0, 8.0), (11.0, 14.0), (8.0, 14.0), (8.0, 22.0), (4.0, 22.0), (4.0, 14.0), (1.0, 14.0)],
             shade(body, 0.4))                                                         # insert this way
    label = spec.FLOPPY_LABEL
    top.rect_(5.0, 44.0, w - 5.0, length - 1.0, (244, 242, 234), r=1.0)
    top.rect_(5.0, 44.0, w - 5.0, 51.0, rgb(label["band"]), r=1.0)
    top.text(label["publisher"], "arialbd.ttf", 3.6, w / 2, 47.6, (255, 255, 255))
    logo = Image.open(os.path.join(made_up, "library", "media", label["system"], "logos", label["stem"] + ".png"))
    logo = logo.convert("RGBA")
    k = min((w - 16.0) / logo.width, 22.0 / logo.height)
    lw, lh = logo.width * k, logo.height * k
    layer = top.layer()
    scaled = logo.resize((max(1, round(lw * top.sx)), max(1, round(lh * top.sy))), Image.LANCZOS)
    layer.alpha_composite(scaled, (round((w / 2 - lw / 2) * top.sx), round((63.5 - lh / 2) * top.sy)))
    top.over(layer)
    for k, line in enumerate(label["lines"]):
        top.text(line, "arialbd.ttf" if k == 0 else "arial.ttf", 3.4 if k == 0 else 2.8, w / 2, 80.0 + k * 4.4,
                 (40, 40, 40))
    top.rect_(w - 9.0, length - 9.0, w - 4.0, length - 4.0, (14, 14, 16))               # the write-protect window
    top.paste(atlas)
    under = Region(spec.PRINT_REGIONS["floppy_under"], w, length, body)
    under.rect_(0.6, 0.6, w - 0.6, length - 0.6, shade(body, 0.06), r=2.0)
    under.rect_(w * 0.5 - 21.0, 0.0, w * 0.5 + 30.0, 40.0, shade(metal, -0.05))
    under.rect_(w * 0.5 + 4.0, 4.0, w * 0.5 + 17.0, 34.0, (40, 30, 26))
    under.circle(w / 2, 59.0, 12.5, shade(metal, -0.12))                               # the hub
    under.circle(w / 2, 59.0, 5.0, shade(metal, -0.4))
    under.rect_(w / 2 + 3.0, 52.0, w / 2 + 7.0, 56.0, (14, 14, 16))
    under.paste(atlas)


def cd_label(atlas, spec, made_up):
    """The CD's label side, printed all over as the 1990s' games' discs were: the game's key art, its logo, the line
    round its edge; the clear hub and the hole in the middle."""
    r = K.CD["radius"]
    label = spec.CD_LABEL
    reg = Region(spec.PRINT_REGIONS["cd"], 2 * r, 2 * r, rgb(spec.COLOURS["disc"]))
    art = Image.open(os.path.join(made_up, "paintings", label["art"], "keyart.png")).convert("RGB")
    k = 2 * r * reg.sx / min(art.width, art.height)
    art = art.resize((round(art.width * k), round(art.height * k)), Image.LANCZOS)
    art = art.crop(((art.width - round(2 * r * reg.sx)) // 2, (art.height - round(2 * r * reg.sy)) // 2,
                    (art.width - round(2 * r * reg.sx)) // 2 + round(2 * r * reg.sx),
                    (art.height - round(2 * r * reg.sy)) // 2 + round(2 * r * reg.sy))).convert("RGBA")
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).ellipse([1, 1, art.width - 2, art.height - 2], fill=255)
    layer = reg.layer()
    layer.paste(art, (0, 0), mask)
    reg.over(layer)
    logo = Image.open(os.path.join(made_up, "library", "media", label["system"], "logos", label["stem"] + ".png"))
    logo = logo.convert("RGBA")
    k = min(2 * r * 0.62 / logo.width, 26.0 / logo.height)
    layer = reg.layer()
    scaled = logo.resize((max(1, round(logo.width * k * reg.sx)), max(1, round(logo.height * k * reg.sy))),
                         Image.LANCZOS)
    layer.alpha_composite(scaled, (round((r - logo.width * k / 2) * reg.sx), round((r * 0.42 - logo.height * k / 2)
                                                                                    * reg.sy)))
    reg.over(layer)
    reg.rect_(r - 34.0, 2 * r - 26.0, r + 34.0, 2 * r - 18.0, (20, 20, 24), r=2.0)
    reg.text(label["line"], "arialbd.ttf", 3.6, r, 2 * r - 22.0, (240, 240, 240))
    reg.circle(r, r, 17.0, (214, 218, 224))                     # the clear hub
    reg.circle(r, r, 11.0, (190, 194, 200))
    reg.circle(r, r, K.CD["hole"], (16, 16, 18))
    reg.paste(atlas)


def tray_top(atlas, spec):
    """A CD-ROM drive's tray from above, its front at the region's foot: its two wells (12 and 8 cm) and the
    spindle's hole."""
    t = spec.TRAY
    a0, a1, _b0, _b1 = t["front"]
    w, d = a1 - a0 - 4.8, t["depth"] - 2.0
    colour = rgb(spec.COLOURS["tray"])
    reg = Region(spec.DEVICE_REGIONS["tray_top"], w, d, colour)
    well = d - t["well"]
    reg.circle(w / 2, well, K.CD["radius"] + 1.0, shade(colour, 0.12))
    reg.circle(w / 2, well, K.CD["radius"] - 1.0, shade(colour, -0.2))
    reg.circle(w / 2, well, 41.0, shade(colour, 0.08))
    reg.circle(w / 2, well, 39.0, shade(colour, -0.25))
    reg.rect_(w / 2 - 9.0, 6.0, w / 2 + 9.0, well, (12, 12, 14))     # the laser's slot, towards the back
    reg.circle(w / 2, well, 8.0, (60, 60, 64))
    reg.paste(atlas)


# -- The mouse and its pad -------------------------------------------------------------------------------------------

def mouse_top(atlas, spec):
    """The mouse from above, its front (the buttons) at the region's top: the seam behind the buttons and the one
    between them."""
    length, (wb, _wf) = K.MOUSE["length"], K.MOUSE["width"]
    body = rgb(spec.COLOURS["mouse"])
    reg = Region(spec.PRINT_REGIONS["mouse_top"], wb, length, body)
    split = K.MOUSE["split"]
    reg.line([(0.0, split + 3.0), (wb * 0.25, split + 0.8), (wb * 0.5, split), (wb * 0.75, split + 0.8),
              (wb, split + 3.0)], shade(body, -0.45), 0.7)
    reg.line([(wb / 2, 0.0), (wb / 2, split)], shade(body, -0.45), 0.7)
    for a in (wb * 0.25, wb * 0.75):                    # the buttons a shade lighter where the finger rests
        reg.rect_(a - 9.0, 10.0, a + 9.0, split - 8.0, shade(body, 0.05), r=6.0)
    reg.text("ODYSSEY", "arialbd.ttf", 3.6, wb / 2, split + 34.0, shade(body, -0.35))
    reg.paste(atlas)


def pad_top(atlas, spec):
    """The mouse pad: its colour, a few stripes across a corner and the brand."""
    (w, d) = K.PAD["size"]
    colour = rgb(spec.COLOURS["pad"])
    reg = Region(spec.PRINT_REGIONS["pad"], w, d, colour)
    for k in range(5):
        reg.poly([(w - 70.0 + k * 14.0, d), (w - 60.0 + k * 14.0, d), (w, d - 60.0 + k * 14.0 - 14.0),
                  (w, d - 70.0 + k * 14.0 - 14.0)], shade(colour, 0.12 + 0.04 * k))
    reg.text("ODYSSEY", "arialbd.ttf", 9.0, 40.0, d - 14.0, shade(colour, 0.45), anchor="lm")
    reg.rect_(1.0, 1.0, w - 1.0, d - 1.0, None, r=K.PAD["radius"], outline=shade(colour, -0.35), width=1.2)
    reg.paste(atlas)


# -- The monitor's front ---------------------------------------------------------------------------------------------

def monitor_front(atlas, spec):
    """The monitor's front seen square on: its bezel, the screen's opening (the model cuts it), the strip's parts."""
    mon = spec.MONITOR
    colour = rgb(spec.COLOURS["monitor"])
    w, h = mon["width"], mon["height"]
    reg = Region(spec.DEVICE_REGIONS["monitor"], w, h, colour)
    for k in range(6):                                  # the bezel's edge catches the light, its foot falls in shadow
        reg.rect_(k * 1.2, k * 1.2, w - k * 1.2, h - k * 1.2, None, outline=shade(colour, 0.05 - k * 0.012), width=1.2)
    ow, oh, orad = mon["opening"]
    cz = h - mon["screen_z"]
    reg.rect_(w / 2 - ow / 2, cz - oh / 2, w / 2 + ow / 2, cz + oh / 2, (20, 20, 22), r=orad)
    draw_parts(reg, [(kind, a, b, pw, ph, depth, text) for kind, a, b, pw, ph, depth, text in mon["strip"]], colour,
               plate_badge=False)
    reg.paste(atlas)


# -- The atlases -----------------------------------------------------------------------------------------------------

def swatch_strip(image, spec):
    d = ImageDraw.Draw(image)
    for name, (x, y) in spec.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(spec.COLOURS[name]))


def print_atlas(spec, made_up, out):
    image = Image.new("RGB", (K.ATLAS, K.ATLAS), (110, 108, 104))
    keyboard_top(image, spec)
    if "floppy" in spec.PRINT_REGIONS:
        floppy_sides(image, spec, made_up)
    if "mouse_top" in spec.PRINT_REGIONS:
        mouse_top(image, spec)
        pad_top(image, spec)
    if "cd" in spec.PRINT_REGIONS:
        cd_label(image, spec, made_up)
    for extra in getattr(spec, "PRINT_EXTRAS", ()):
        extra(image, spec, made_up)
    swatch_strip(image, spec)
    image.save(out, optimize=True)


def devices_atlas(spec, out):
    image = Image.new("RGB", (K.ATLAS, K.ATLAS), (110, 108, 104))
    case = spec.CASE
    tower = case["kind"] == "tower"
    w, h = case["width"], case["height"] - case["feet"]
    bezel = rgb(spec.COLOURS["bezel"])
    front = Region(spec.DEVICE_REGIONS["front"], w, h, bezel)
    if not tower:                                        # a desktop bezel's grooves, across its foot
        for k in range(3):
            front.line([(4.0, h - 6.0 - k * 3.0), (w - 4.0, h - 6.0 - k * 3.0)], shade(bezel, -0.12), 0.5)
    draw_parts(front, spec.FRONT, bezel, plate_badge=case.get("plate", True), tower=tower)
    front.paste(image)
    if "back" in spec.DEVICE_REGIONS:
        if tower:
            tower_back(image, spec.DEVICE_REGIONS["back"], w, h)
        else:
            desktop_back(image, spec.DEVICE_REGIONS["back"], w, h, sound=case.get("sound", False))
    monitor_front(image, spec)
    if "tray_top" in spec.DEVICE_REGIONS:
        tray_top(image, spec)
    swatch_strip(image, spec)
    image.save(out, optimize=True)


def main(name, made_up, out):
    os.makedirs(out, exist_ok=True)
    spec = importlib.import_module(name + "_layout")
    screens = importlib.import_module(name + "_screens")
    print_atlas(spec, made_up, os.path.join(out, f"{name}_print.png"))
    devices_atlas(spec, os.path.join(out, f"{name}_devices.png"))
    path = os.path.join(out, f"{name}_screen.png")
    screens.still(made_up).save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]))
