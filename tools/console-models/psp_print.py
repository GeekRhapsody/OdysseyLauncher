"""The PlayStation Portable's printing, for the console theme's model (tools/console-models/psp.py).

Draws its two atlases, their regions as psp_layout.py places them, each in millimetres as the model's planar UVs map
it. psp_print.png: the front (the piano-black face, the speaker's dots, the switched-off screen, the logos and legends,
the buttons' wells and tops, the analogue nub, the lights) and the back seen from behind (the empty UMD bay the door
covers, the battery cover, the seams), and the swatches small parts take their colour from. psp_media.png: the XMB
(the menu, with the UMD's game on it) and the game's title screen, each drawn at the PSP's 480 x 272 pixels and pasted
one texel a pixel; the UMD's label side (a made-up game, Odyssey) and its other side; and the UMD door's outside, its
ring and logo. Run it with the system Python (Pillow):

    python tools/console-models/psp_print.py <out folder>

It writes psp_print.png and psp_media.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psp_layout as L  # noqa: E402
from game_boy_print import FONTS, SCALE, Face, rgb  # noqa: E402
from game_gear_print import rounded_polygon  # noqa: E402

CASE = L.COLOURS["case"]
TOP = "#2A2A30"       # the buttons' tops
LEGEND = "#9A9EA6"    # the grey printing
SILVER = "#C9CDD3"


def outline(face, points, width, fill):
    for (ax, az), (bx, bz) in zip(points, points[1:] + points[:1]):
        face.line(ax, az, bx, bz, width, fill)


def psp_logo(face, x, z, width, stroke, fill):
    """The PSP logotype's letters drawn in thin strokes, as squared letters: P, S, P, width wide, centred at (x, z)."""
    w = width / 3.6
    h = w * 0.46
    gap = (width - 3 * w) / 2
    z0, z1, zm = z - h / 2, z + h / 2, z
    for k, letter in enumerate("PSP"):
        x0 = x - width / 2 + k * (w + gap)
        x1 = x0 + w
        if letter == "P":
            lines = [(x0, z0, x0, z1), (x0, z1, x1, z1), (x1, z1, x1, zm), (x1, zm, x0 + w * 0.3, zm)]
        else:
            lines = [(x1, z1, x0, z1), (x0, z1, x0, zm), (x0, zm, x1, zm), (x1, zm, x1, z0), (x1, z0, x0, z0)]
        for ax, az, bx, bz in lines:
            face.line(ax, az, bx, bz, stroke, fill)


def ps_mark(face, x, z, size, fill):
    """A small PlayStation mark: a tall P, and a flattened S lying across its foot."""
    s = size
    face.rounded(x - 0.3 * s, x - 0.1 * s, z - 0.42 * s, z + 0.5 * s, 0.02 * s, fill)
    face.ring(x + 0.04 * s, z + 0.26 * s, 0.2 * s, 0.11 * s, fill)
    face.rounded(x - 0.3 * s, x + 0.04 * s, z + 0.4 * s, z + 0.5 * s, 0.02 * s, fill)
    face.rounded(x - 0.3 * s, x + 0.04 * s, z + 0.03 * s, z + 0.13 * s, 0.02 * s, fill)
    path = [(x + 0.5 * s, z - 0.12 * s), (x - 0.05 * s, z - 0.2 * s), (x - 0.5 * s, z - 0.3 * s),
            (x + 0.05 * s, z - 0.38 * s), (x + 0.45 * s, z - 0.48 * s)]
    for (ax, az), (bx, bz) in zip(path, path[1:]):
        face.line(ax, az, bx, bz, 0.1 * s, fill)


def symbol(face, name, x, z, r, width, fill):
    """A face button's symbol, about r from its middle."""
    if name == "triangle":
        pts = [(x + r * math.cos(math.radians(a)), z - 0.15 * r + r * math.sin(math.radians(a))) for a in (90, 210, 330)]
        outline(face, pts, width, fill)
    elif name == "circle":
        face.ring(x, z, r * 0.9, width, fill)
    elif name == "cross":
        d = r * 0.72
        face.line(x - d, z - d, x + d, z + d, width, fill)
        face.line(x - d, z + d, x + d, z - d, width, fill)
    else:
        d = r * 0.72
        outline(face, [(x - d, z - d), (x + d, z - d), (x + d, z + d), (x - d, z + d)], width, fill)


def grown(points, centre, amount):
    cx, cz = centre
    out = []
    for x, z in points:
        d = math.hypot(x - cx, z - cz)
        out.append((x + (x - cx) / d * amount, z + (z - cz) / d * amount))
    return out


# ---- The front -------------------------------------------------------------------------------------------------------

def speaker_dots(face):
    """The speaker's grille along the top: three rows of fine holes."""
    for row in range(3):
        z = 70.6 + row * 0.82
        x = -54.0 + (0.41 if row % 2 else 0.0)
        while x < 54.0:
            face.circle(x, z, 0.24, rgb(CASE, 0.45))
            x += 0.82


def glass(face):
    (x0, x1), (z0, z1) = L.GLASS["x"], L.GLASS["z"]
    face.rounded(x0 - 0.4, x1 + 0.4, z0 - 0.4, z1 + 0.4, 1.2, rgb(CASE, 0.7))
    face.rounded(x0, x1, z0, z1, 1.0, rgb("#141518"))
    s = L.SCREEN
    sx0, sx1 = s["x"] - s["width"] / 2, s["x"] + s["width"] / 2
    sz0, sz1 = s["z"] - s["height"] / 2, s["z"] + s["height"] / 2
    face.rounded(sx0, sx1, sz0, sz1, 0.3, rgb("#34373C"))
    # The switched-off LCD catches the light in a soft diagonal band.
    layer = Image.new("RGBA", face.img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a, b = face.p(sx0, sz1)
    c, e = face.p(sx1, sz0)
    for k in range(40):
        t = k / 39
        alpha = int(26 * math.sin(math.pi * t))
        x = a + (c - a) * (0.18 + 0.4 * t)
        d.polygon([(x, b), (x + 40, b), (x - (e - b) * 0.55 + 40, e), (x - (e - b) * 0.55, e)], fill=(255, 255, 255, alpha))
    mask = Image.new("L", face.img.size, 0)
    ImageDraw.Draw(mask).rectangle([a, b, c, e], fill=255)
    layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", face.img.size, 0), mask))
    face.img.alpha_composite(layer)


def dpad(face):
    cx, cz = L.DPAD["x"], L.DPAD["z"]
    face.ring(cx, cz, L.DPAD["well"], 0.35, rgb(CASE, 0.6))
    face.circle(cx, cz, L.DPAD["well"] - 0.2, rgb(CASE, 1.08))
    for _, a in L.DPAD_BUTTONS:
        corners, radii = L.pentagon(cx, cz, a)
        face.polygon(rounded_polygon(grown(corners, (cx, cz), 0.6), [r + 0.4 for r in radii], 10), rgb(CASE, 0.5))
    for _, a in L.DPAD_BUTTONS:
        corners, radii = L.pentagon(cx, cz, a)
        face.polygon(rounded_polygon(corners, radii, 10), rgb(TOP))
        # The arrow on its top: a small hollow triangle pointing outwards.
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        mx, mz = cx + 8.6 * c, cz + 8.6 * s
        tri = [(mx + 1.5 * c, mz + 1.5 * s), (mx - 0.9 * c - 1.6 * s, mz - 0.9 * s + 1.6 * c),
               (mx - 0.9 * c + 1.6 * s, mz - 0.9 * s - 1.6 * c)]
        outline(face, tri, 0.28, rgb(LEGEND))


def face_buttons(face):
    cx, cz = L.FACE["x"], L.FACE["z"]
    face.ring(cx, cz, L.FACE["well"], 0.35, rgb(CASE, 0.6))
    face.circle(cx, cz, L.FACE["well"] - 0.2, rgb(CASE, 1.08))
    r = L.FACE["radius"]
    for name, x, z in L.face_centres():
        face.circle(x, z, r + 0.7, rgb(CASE, 0.5))
        face.circle(x, z, r, rgb(TOP))
        symbol(face, name, x, z, r * 0.5, 0.3, rgb("#B4B8BF"))


def nub(face):
    x, z, r = L.NUB["x"], L.NUB["z"], L.NUB["radius"]
    face.circle(x, z, r + 0.8, rgb(CASE, 0.45))
    face.circle(x, z, r, rgb("#33333A"))
    face.circle(x, z, r - 1.0, rgb("#2C2C32"))
    # The rubbery top's knurling: a grid of tiny dimples inside its flat.
    step = 0.7
    k = -r
    while k <= r:
        j = -r
        while j <= r:
            if math.hypot(k, j) < r - 1.4:
                face.circle(x + k, z + j, 0.13, rgb("#222227"))
            j += step
        k += step


def bottom_row(face):
    z = L.ROW_Z
    for name, x, shape in L.ROW:
        if shape == "shield":
            corners, radii = L.shield(x, z)
            face.polygon(rounded_polygon(grown(corners, (x, z), 0.55), [r + 0.4 for r in radii], 10), rgb(CASE, 0.5))
            face.polygon(rounded_polygon(corners, radii, 10), rgb(TOP))
            face.text(name, "arialbd.ttf", 0.85, x, z + 0.25, rgb(LEGEND), anchor="centre")
        else:
            face.pill(x, z, 6.9, 5.9, 0.0, rgb(CASE, 0.5))
            face.pill(x, z, 5.8, 4.8, 0.0, rgb(TOP))
            if name == "VOL-":
                face.line(x - 0.9, z, x + 0.9, z, 0.3, rgb(LEGEND))
            elif name == "VOL+":
                face.line(x - 0.9, z, x + 0.9, z, 0.3, rgb(LEGEND))
                face.line(x, z - 0.9, x, z + 0.9, 0.3, rgb(LEGEND))
            elif name == "DISPLAY":
                face.rounded(x - 1.2, x + 1.2, z - 0.8, z + 0.8, 0.3, rgb(LEGEND))
                face.rounded(x - 0.9, x + 0.9, z - 0.5, z + 0.5, 0.2, rgb(TOP))
            else:
                face.text("♪", "seguisym.ttf", 1.6, x, z, rgb(LEGEND), anchor="centre")
    face.text("VOL", "arialbd.ttf", 0.75, -32.8, z, rgb(LEGEND), anchor="centre")
    psp_logo(face, 0.0, z, 22.0, 0.32, rgb("#A9ADB4"))


def lights(face):
    """The Memory Stick and WLAN lights at the left, POWER and HOLD at the right, all unlit."""
    off = rgb("#3B4440")
    face.circle(-82.2, 23.6, 0.5, off)
    face.circle(-79.4, 15.8, 0.5, off)
    # The Memory Stick's icon: a card with a notch; the WLAN's: radio waves.
    face.polygon([(-79.6, 22.9), (-76.6, 22.9), (-76.6, 24.3), (-77.2, 24.6), (-79.6, 24.6)], rgb(LEGEND))
    face.polygon([(-79.1, 23.3), (-77.1, 23.3), (-77.1, 24.2), (-79.1, 24.2)], rgb(CASE))
    for r in (0.8, 1.5, 2.2):
        steps = 6
        pts = [(-78.4 + r * math.cos(math.radians(a)), 15.0 + r * math.sin(math.radians(a)))
               for a in (k * 90 / steps for k in range(steps + 1))]
        for (ax, az), (bx, bz) in zip(pts, pts[1:]):
            face.line(ax, az, bx, bz, 0.25, rgb(LEGEND))
    face.circle(-78.4, 15.0, 0.35, rgb(LEGEND))
    face.text("POWER", "arialbd.ttf", 1.05, 79.0, 24.4, rgb("#4FCB82"), anchor="right")
    face.circle(81.2, 24.4, 0.45, off)
    face.text("HOLD", "arialbd.ttf", 1.05, 76.0, 16.3, rgb("#C4C8CE"), anchor="right")
    face.circle(77.9, 16.3, 0.45, off)


def front():
    face = Face(L.PRINT_REGIONS["front"]["mm"], rgb(CASE))
    speaker_dots(face)
    glass(face)
    ps_mark(face, -66.5, 61.0, 4.4, rgb("#8E9299"))
    face.text("SONY", "timesbd.ttf", 2.0, 58.8, 65.4, rgb("#B9BDC4"), anchor="centre", stretch=1.15)
    dpad(face)
    face_buttons(face)
    nub(face)
    lights(face)
    for x, z in L.SPEAKERS:
        face.rounded(x - 1.6, x + 1.6, z - 0.7, z + 0.7, 0.7, rgb("#08080A"))
    bottom_row(face)
    return face


# ---- The back --------------------------------------------------------------------------------------------------------

def rear():
    """The back, seen from behind (x is the front's, negated): the UMD bay the door covers, the battery cover on the
    viewer's left (the console's right end), the Memory Stick's side on the right, the seams."""
    matte = "#212127"
    face = Face(L.PRINT_REGIONS["rear"]["mm"], rgb(matte))
    (x0, x1), (z0, z1) = L.DOOR["x"], L.DOOR["z"]

    # The bay: a dark well, the spindle, the laser's track and the door's hinges.
    face.rounded(x0 - 0.6, x1 + 0.6, z0 - 0.6, z1 + 0.6, 3.0, rgb(matte, 0.55))
    face.rounded(x0, x1, z0, z1, 2.6, rgb("#111114"))
    cz = L.DOOR["ring"][0]
    face.circle(0.0, cz, 31.0, rgb("#18181C"))
    face.rounded(-30.0, -6.0, cz - 3.2, cz + 3.2, 1.0, rgb("#0A0A0C"))
    face.rounded(-20.0, -16.0, cz - 1.8, cz + 1.8, 0.4, rgb("#2C2E36"))
    face.circle(-18.0, cz, 1.1, rgb("#5A6CB0"))
    face.circle(0.0, cz, 5.5, rgb("#4A4C52"))
    face.circle(0.0, cz, 3.6, rgb("#8A8D94"))
    face.circle(0.0, cz, 1.4, rgb("#5A5C62"))
    for x in (x0 + 8.0, x1 - 8.0):
        face.rounded(x - 3.0, x + 3.0, z0 + 0.2, z0 + 2.2, 0.5, rgb("#2A2A30"))

    # The battery cover (the viewer's left), its release, and the Memory Stick's side (the viewer's right).
    face.rounded(-79.0, -42.0, 10.0, 66.0, [9.0, 6.0, 6.0, 9.0], rgb(matte, 0.7))
    face.rounded(-78.6, -42.4, 10.4, 65.6, [8.6, 5.6, 5.6, 8.6], rgb(matte, 1.05))
    for k in range(5):
        face.line(-76.5, 34.0 + k * 1.3, -73.5, 34.0 + k * 1.3, 0.45, rgb(matte, 0.7))
    face.text("PUSH", "arialbd.ttf", 0.9, -70.0, 36.6, rgb(matte, 1.7), anchor="centre", degrees=90)
    face.text("BATTERY PACK  3.6V", "arial.ttf", 0.85, -60.0, 14.0, rgb(matte, 1.6), anchor="centre")
    face.circle(73.0, 63.0, 1.1, rgb(matte, 0.5))
    face.text("MAGICGATE", "arialbd.ttf", 0.95, 80.0, 44.0, rgb(matte, 1.7), anchor="centre", degrees=-90)
    face.text("PSP-1000", "arial.ttf", 0.9, 60.0, 14.0, rgb(matte, 1.6), anchor="centre")
    for x in (-60.0, 60.0):
        face.circle(x, 70.0, 0.9, rgb(matte, 0.6))
    return face


# ---- The screens -----------------------------------------------------------------------------------------------------

def font(name, px):
    return ImageFont.truetype(FONTS + name, px)


def wave_layer(size, colour, waves, glow=6):
    """The XMB's wave: thin bright ribbons across the screen, blurred into a glow."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for amp, length, phase, base, alpha, width in waves:
        pts = [(x, base * h + amp * h * math.sin(2 * math.pi * x / (length * w) + phase)) for x in range(0, w + 4, 4)]
        d.line(pts, fill=colour + (alpha,), width=width)
    return Image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(glow)), layer)


def ship(d, x, y, s, fill, flame):
    """Odyssey's ship, pointing right."""
    d.polygon([(x + 16 * s, y), (x - 8 * s, y - 7 * s), (x - 4 * s, y), (x - 8 * s, y + 7 * s)], fill=fill)
    d.polygon([(x - 2 * s, y - 3 * s), (x - 14 * s, y - 13 * s), (x - 9 * s, y - 2 * s)], fill=fill)
    d.polygon([(x - 2 * s, y + 3 * s), (x - 14 * s, y + 13 * s), (x - 9 * s, y + 2 * s)], fill=fill)
    d.polygon([(x - 5 * s, y - 2.5 * s), (x - 15 * s, y), (x - 5 * s, y + 2.5 * s)], fill=flame)


def space(size, seed_stars=True):
    """Odyssey's backdrop: a deep violet sky, stars, an orange ringed planet."""
    w, h = size
    img = Image.new("RGBA", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(int(16 + 44 * t), int(10 + 16 * t), int(48 + 70 * t), 255))
    if seed_stars:
        for k in range(140):
            x = (k * 7919) % w
            y = (k * 104729 // 7) % h
            v = 140 + (k * 37) % 115
            r = 1 if k % 5 else 2
            d.ellipse([x - r, y - r, x + r, y + r], fill=(v, v, 255, 255))
    pr = h * 0.42
    px, py = w * 0.74, h * 0.62
    d.ellipse([px - pr, py - pr, px + pr, py + pr], fill="#F27A3B")
    d.ellipse([px - pr * 0.82, py - pr * 0.95, px + pr * 0.7, py + pr * 0.5], fill="#F79A55")
    d.arc([px - pr * 1.7, py - pr * 0.35, px + pr * 1.7, py + pr * 0.35], 160, 380, fill="#F2E6FF", width=max(2, int(h / 60)))
    return img


def xmb():
    """The XMB at 2x, 960 x 544: the wave over a blue gradient, the category icons with Game chosen, and the UMD's game
    at the top of its list."""
    w, h = 960, 544
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(int(8 + 20 * t), int(30 + 60 * t), int(92 + 90 * t), 255))
    img = Image.alpha_composite(img, wave_layer((w, h), (190, 220, 255), [
        (0.06, 1.3, 0.4, 0.66, 150, 3), (0.08, 1.1, 1.3, 0.68, 110, 2), (0.05, 0.9, 2.2, 0.70, 90, 2),
        (0.07, 1.6, 3.0, 0.64, 70, 5), (0.04, 0.7, 4.1, 0.72, 120, 2)], glow=10))
    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    dim = (255, 255, 255, 150)

    # The status: the date and time, the battery.
    d.text((w - 210, 26), "17/10  12:00", font=font("segoeui.ttf", 26), fill=white)
    d.rounded_rectangle([w - 58, 30, w - 22, 50], 3, outline=white, width=3)
    d.rectangle([w - 54, 34, w - 32, 46], fill=white)
    d.rectangle([w - 20, 36, w - 16, 44], fill=white)

    # The categories along the top: Settings, Photo, Music, Video, Game (chosen, larger), Network.
    y = 128
    def gear(cx, s, fill):
        for k in range(8):
            a = math.radians(k * 45)
            d.line([(cx + 0.6 * s * math.cos(a), y + 0.6 * s * math.sin(a)), (cx + s * math.cos(a), y + s * math.sin(a))],
                   fill=fill, width=int(s / 3))
        d.ellipse([cx - 0.7 * s, y - 0.7 * s, cx + 0.7 * s, y + 0.7 * s], fill=fill)
        d.ellipse([cx - 0.3 * s, y - 0.3 * s, cx + 0.3 * s, y + 0.3 * s], fill=(30, 70, 150, 255))

    def photo(cx, s, fill):
        d.rectangle([cx - s, y - 0.75 * s, cx + s, y + 0.75 * s], outline=fill, width=4)
        d.polygon([(cx - 0.8 * s, y + 0.55 * s), (cx - 0.2 * s, y - 0.2 * s), (cx + 0.2 * s, y + 0.2 * s),
                   (cx + 0.45 * s, y), (cx + 0.8 * s, y + 0.55 * s)], fill=fill)

    def music(cx, s, fill):
        d.ellipse([cx - 0.8 * s, y + 0.2 * s, cx - 0.1 * s, y + 0.8 * s], fill=fill)
        d.rectangle([cx - 0.22 * s, y - 0.9 * s, cx - 0.1 * s, y + 0.5 * s], fill=fill)
        d.polygon([(cx - 0.22 * s, y - 0.9 * s), (cx + 0.7 * s, y - 0.5 * s), (cx + 0.7 * s, y - 0.2 * s),
                   (cx - 0.1 * s, y - 0.55 * s)], fill=fill)

    def video(cx, s, fill):
        d.rectangle([cx - s, y - 0.6 * s, cx + s, y + 0.6 * s], fill=fill)
        for k in range(5):
            x = cx - 0.85 * s + k * 0.42 * s
            d.rectangle([x, y - 0.5 * s, x + 0.18 * s, y - 0.32 * s], fill=(30, 70, 150, 255))
            d.rectangle([x, y + 0.32 * s, x + 0.18 * s, y + 0.5 * s], fill=(30, 70, 150, 255))

    def game(cx, s, fill):
        d.rounded_rectangle([cx - s, y - 0.5 * s, cx + s, y + 0.5 * s], int(0.45 * s), fill=fill)
        d.ellipse([cx - 0.95 * s, y - 0.2 * s, cx - 0.35 * s, y + 0.75 * s], fill=fill)
        d.ellipse([cx + 0.35 * s, y - 0.2 * s, cx + 0.95 * s, y + 0.75 * s], fill=fill)
        d.rectangle([cx - 0.62 * s, y - 0.1 * s, cx - 0.5 * s, y + 0.3 * s], fill=(30, 70, 150, 255))
        d.rectangle([cx - 0.76 * s, y + 0.04 * s, cx - 0.36 * s, y + 0.16 * s], fill=(30, 70, 150, 255))
        for dx, dy in ((0.55, 0.0), (0.7, 0.15), (0.4, 0.15), (0.55, 0.3)):
            d.ellipse([cx + dx * s - 0.06 * s, y + dy * s - 0.06 * s, cx + dx * s + 0.06 * s, y + dy * s + 0.06 * s],
                      fill=(30, 70, 150, 255))

    def network(cx, s, fill):
        d.ellipse([cx - s, y - s, cx + s, y + s], outline=fill, width=4)
        d.ellipse([cx - 0.4 * s, y - s, cx + 0.4 * s, y + s], outline=fill, width=3)
        d.line([(cx - s, y), (cx + s, y)], fill=fill, width=3)

    for draw, cx in ((gear, 70), (photo, 170), (music, 270), (video, 370)):
        draw(cx, 26, dim)
    game(520, 46, white)
    network(680, 26, dim)
    label = font("segoeuib.ttf", 30)
    d.text((520, 198), "Game", font=label, fill=white, anchor="mm")

    # The Game list: the UMD's game, chosen, its icon glowing; then Saved Data Utility and Memory Stick.
    icon = space((144, 80))
    di = ImageDraw.Draw(icon)
    ship(di, 46, 40, 1.1, "#FFFFFF", "#FFB23C")
    di.text((72, 66), "ODYSSEY", font=font("ariblk.ttf", 15), fill="#FFE45C", anchor="mm")
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([440, 240, 600, 336], 10, fill=(255, 255, 255, 180))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(9)))
    img.alpha_composite(icon, (448, 248))
    d = ImageDraw.Draw(img)
    d.rectangle([448, 248, 591, 327], outline=white, width=2)
    d.text((620, 268), "ODYSSEY", font=font("segoeuib.ttf", 34), fill=white)
    d.text((620, 306), "UMD™", font=font("segoeui.ttf", 22), fill=(220, 232, 255, 255))
    for k, text in enumerate(("Saved Data Utility", "Memory Stick™")):
        yy = 384 + k * 70
        d.rounded_rectangle([488, yy, 552, yy + 46], 6, outline=dim, width=3)
        d.text((620, yy + 23), text, font=font("segoeui.ttf", 26), fill=dim, anchor="lm")
    return img.resize((480, 272), Image.LANCZOS)


def title_screen():
    """Odyssey's title screen at 2x: the ship over the planet, the title, PRESS START."""
    w, h = 960, 544
    img = space((w, h))
    d = ImageDraw.Draw(img)
    ship(d, 270, 330, 4.0, "#FFFFFF", "#FFB23C")
    for k in range(4):
        d.line([(110 - k * 30, 316 + k * 10), (200 - k * 22, 316 + k * 10)], fill=(255, 210, 120, 160 - k * 30), width=4)
    title = font("ariblk.ttf", 108)
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((w / 2 + 6, 128), "ODYSSEY", font=title, fill=(255, 120, 40, 255), anchor="mm")
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(4)))
    d = ImageDraw.Draw(img)
    d.text((w / 2, 122), "ODYSSEY", font=title, fill="#FFE45C", anchor="mm", stroke_width=4, stroke_fill="#5A1A08")
    d.text((w / 2, 206), "A PORTABLE VOYAGE", font=font("arialbd.ttf", 30), fill="#E8E0FF", anchor="mm")
    d.text((w / 2 + 120, 452), "PRESS START", font=font("arialbd.ttf", 38), fill="#FFFFFF", anchor="mm",
           stroke_width=2, stroke_fill="#20104A")
    d.text((w / 2 + 120, 508), "© ODYSSEY LAUNCHER", font=font("arial.ttf", 20), fill="#B8B0E0", anchor="mm")
    return img.resize((480, 272), Image.LANCZOS)


# ---- The UMD and its door --------------------------------------------------------------------------------------------

def umd_label():
    """The UMD's label side, seen looking at it: the white shell, the disc's label through its window."""
    face = Face(L.MEDIA_REGIONS["umd"]["mm"], rgb(L.COLOURS["umd"]))
    r = L.UMD["disc"]
    face.circle(0.0, 0.0, r + 0.6, rgb("#B7BAC0"))
    art = space((960, 960), seed_stars=True)
    d = ImageDraw.Draw(art)
    ship(d, 200, 640, 3.6, "#FFFFFF", "#FFB23C")
    d.text((480, 180), "ODYSSEY", font=font("ariblk.ttf", 118), fill="#FFE45C", anchor="mm", stroke_width=6,
           stroke_fill="#5A1A08")
    d.text((480, 262), "A PORTABLE VOYAGE", font=font("arialbd.ttf", 40), fill="#E8E0FF", anchor="mm")
    d.text((480, 870), "ULES-ODY01", font=font("arialbd.ttf", 34), fill="#D8D0F0", anchor="mm")
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 959, 959], fill=255)
    art.putalpha(mask)
    face.paste(art, -r, r, -r, r)
    # The hub: a white disc with UMD's name, and the clear ring round the spindle's hole.
    face.circle(0.0, 0.0, 10.5, rgb("#F4F4F2"))
    face.ring(0.0, 0.0, 10.5, 0.25, rgb("#C9CBD0"))
    face.text("UMD", "segoeui.ttf", 3.0, 0.0, 1.6, rgb("#5B63C2"), anchor="centre")
    face.text("UNIVERSAL MEDIA DISC", "segoeui.ttf", 0.75, 0.0, -2.2, rgb("#5B63C2"), anchor="centre")
    face.text("© ODYSSEY LAUNCHER", "arial.ttf", 0.7, 0.0, -6.8, rgb("#80848C"), anchor="centre")
    # Under the window, on the shell: the logotype and a controller.
    psp_logo(face, -21.5, -29.4, 8.0, 0.3, rgb("#7A7E86"))
    face.rounded(19.0, 25.0, -30.6, -28.2, 1.1, rgb("#7A7E86"))
    face.circle(19.6, -30.4, 1.1, rgb("#7A7E86"))
    face.circle(24.4, -30.4, 1.1, rgb("#7A7E86"))
    return face


def umd_back():
    """The UMD's other side, seen looking at it: the disc's silver under the clear back, the hub, the shutter."""
    face = Face(L.MEDIA_REGIONS["umd_rear"]["mm"], rgb(L.COLOURS["umd"]))
    r = L.UMD["disc"]
    face.circle(0.0, 0.0, r + 0.6, rgb("#C4C7CC"))
    disc = Image.new("RGBA", (600, 600))
    d = ImageDraw.Draw(disc)
    for k in range(300, 0, -2):
        v = int(150 + 70 * math.sin(k / 300 * math.pi * 3))
        d.ellipse([300 - k, 300 - k, 300 + k, 300 + k], fill=(v, v + 4, v + 10, 255))
    rainbow = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    dr = ImageDraw.Draw(rainbow)
    for k, colour in enumerate(((255, 120, 120), (255, 220, 120), (140, 255, 160), (120, 190, 255), (200, 140, 255))):
        dr.arc([40 + k * 10, 40 + k * 10, 560 - k * 10, 560 - k * 10], 200, 250, fill=colour + (150,), width=12)
    disc = Image.alpha_composite(disc, rainbow.filter(ImageFilter.GaussianBlur(6)))
    mask = Image.new("L", disc.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 599, 599], fill=255)
    disc.putalpha(mask)
    face.paste(disc, -r, r, -r, r)
    face.rounded(-29.0, -10.0, -3.0, 12.0, 1.2, rgb("#A9ADB4"))
    face.rounded(-28.2, -10.8, -2.2, 11.2, 0.8, rgb("#BFC3C9"))
    face.circle(0.0, 0.0, 8.5, rgb("#D9DBDF"))
    face.circle(0.0, 0.0, 4.2, rgb("#9A9EA6"))
    face.circle(0.0, 0.0, 1.3, rgb("#5E6168"))
    for x in (-18.0, 18.0):
        face.circle(x, -29.0, 1.2, rgb("#BDC0C6"))
    return face


def door():
    """The UMD door's outside, seen from behind (x negated): the matte panel, the silver ring with the logotype in it,
    UMD at the top right."""
    matte = "#212127"
    face = Face(L.MEDIA_REGIONS["door"]["mm"], rgb(matte))
    (x0, x1), (z0, z1) = L.DOOR["x"], L.DOOR["z"]
    face.rounded(x0, x1, z0, z1, [2.0, 4.0, 4.0, 2.0], rgb(matte, 1.12))
    face.rounded(x0 + 0.8, x1 - 0.8, z0 + 0.8, z1 - 0.8, [1.4, 3.4, 3.4, 1.4], rgb(matte))
    cz, outer, inner = L.DOOR["ring"]
    # The ring: brushed aluminium, a soft highlight across it.
    face.circle(0.0, cz, outer + 0.3, rgb("#6E7279"))
    face.circle(0.0, cz, outer, rgb("#C8CCD2"))
    layer = Image.new("RGBA", face.img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    cx, cy = face.p(0.0, cz)
    for a in range(0, 360, 2):
        v = int(200 + 40 * math.cos(math.radians(2 * a - 60)))
        ld.pieslice([cx - outer * SCALE, cy - outer * SCALE, cx + outer * SCALE, cy + outer * SCALE], a, a + 2,
                    fill=(v, v + 3, v + 8, 255))
    face.img.alpha_composite(layer)
    face.circle(0.0, cz, inner + 0.3, rgb("#7E828A"))
    face.circle(0.0, cz, inner, rgb(matte))
    psp_logo(face, 0.0, cz, 31.0, 0.55, rgb("#D9DCE1"))
    face.text("UMD", "arial.ttf", 1.8, 29.5, z1 - 3.0, rgb("#AEB2B9"), anchor="centre")
    return face


# ---- The atlases -----------------------------------------------------------------------------------------------------

def image_face(image):
    face = Face((0, 1, 0, 1), (0, 0, 0, 255))
    face.img = image
    return face


def paste_regions(image, regions, faces, exact=()):
    for name, face in faces.items():
        # Each region bleeds 4 pixels into the gap round it, so filtering and mipmaps at its edges see its own colours.
        x, y, w, h = regions[name]["px"]
        region = face.img.resize((w, h), Image.NEAREST if name in exact else Image.LANCZOS)
        image.paste(region.resize((w + 8, h + 8), Image.NEAREST), (x - 4, y - 4))
        image.paste(region, (x, y))


def print_atlas():
    image = Image.new("RGBA", (L.ATLAS, L.ATLAS), rgb(CASE))
    paste_regions(image, L.PRINT_REGIONS, {"front": front(), "rear": rear()})
    d = ImageDraw.Draw(image)
    for name, colour in (("yellow", "#F2C230"), ("dark", "#0C0C0E"), ("metal", "#8C9097")):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(colour))
    return image.convert("RGB")


def media_atlas():
    image = Image.new("RGBA", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["umd"]))
    paste_regions(image, L.MEDIA_REGIONS, {
        "screen": image_face(xmb()),
        "screen_game": image_face(title_screen()),
        "umd": umd_label(),
        "door": door(),
        "umd_rear": umd_back(),
    }, exact=("screen", "screen_game"))
    return image.convert("RGB")


def main(out):
    os.makedirs(out, exist_ok=True)
    for name, image in (("psp_print.png", print_atlas()), ("psp_media.png", media_atlas())):
        path = os.path.join(out, name)
        image.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1])
