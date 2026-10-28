"""The PlayStation Portable's printing and screens, for the console theme's PSP model (psp.py) and its video
(psp_video.py). psp_layout.py has the measurements and where each part is in the atlases.

Writes three images into a folder:
- psp_print.png: the face seen square on (the piano black, the speaker's holes, the glass's edge, the PlayStation mark
  and SONY, the D-pad's well and its buttons' tops, the face buttons' ring and their symbols, the analogue nub's
  knurled top, the lights and their legends, the bottom row's buttons and the logotype, the speakers' slits, the clear
  corner over the strap's loop); the back seen from behind (the bay's floor under the door: the spindle and the
  laser's track; the battery cover and its release, SONY, MAGICGATE, the screws); the top edge seen from above (the
  silver strip: the IR window, the USB port and its screws, OPEN by the latch's track); and the swatches small parts
  take their colour from.
- psp_media.png: the UMD's label side (a made-up game from tools/made-up-games: its key art and logo on the disc) and
  its other side (the disc's silver under the clear back), and the door's outside (the brushed ring round the
  logotype, UMD).
- psp_screen.png: the glass with the LCD switched off: the still of the model's `video` material, and the first and
  last frame of the card's video.

The screens the video shows (the start-up, the XMB with the game on it, the game's title and the game played) are drawn
here too, at the PSP's 480 x 272 pixels, and composed onto the glass by glass(); psp_video.py puts them in order. The
game is made up (no real game's art): Skylance, Arcwave's shoot 'em up, its key art, logo and painting from the
made-up games' library, its ship and a fighter cut out of the painting, which is filled in where they were.

ship() and space() draw the first made-up game, Odyssey, for many other cards' print scripts, which import them.

Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow,
numpy, scipy):

    python tools/console-models/psp_print.py artifacts/made-up-games artifacts/psp
"""

import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psp_layout as L  # noqa: E402

FONTS = "C:/Windows/Fonts/"
SCALE = 12        # pixels a millimetre while drawing the printing; each region is resampled to its size in the atlas

CASE = L.COLOURS["case"]
REAR = L.COLOURS["rear"]
TOP = "#26262C"       # the buttons' tops
LEGEND = "#9EA2AA"    # the grey printing
SILVER = L.COLOURS["silver"]


def rgb(hex_colour, scale=1.0):
    """A #RRGGBB colour as an (r, g, b, 255) tuple, each channel times scale (darker below 1)."""
    return tuple(max(0, min(255, round(int(hex_colour[i:i + 2], 16) * scale))) for i in (1, 3, 5)) + (255,)


def font(name, px):
    return ImageFont.truetype(FONTS + name, max(1, round(px)))


class Canvas:
    """One region's drawing: x to the right and z up, in millimetres, over the region's box (x0, x1, z0, z1)."""

    def __init__(self, mm, fill, scale=SCALE):
        self.x0, self.x1, self.z0, self.z1 = mm
        self.s = scale
        self.img = Image.new("RGBA", (round((self.x1 - self.x0) * scale), round((self.z1 - self.z0) * scale)), fill)
        self.draw = ImageDraw.Draw(self.img)

    def p(self, x, z):
        return ((x - self.x0) * self.s, (self.z1 - z) * self.s)

    def polygon(self, points, fill):
        self.draw.polygon([self.p(x, z) for x, z in points], fill=fill)

    def rounded(self, x0, x1, z0, z1, radii, fill):
        """A rectangle with its corners rounded: one radius, or four (bottom right, top right, top left, bottom left)."""
        radii = list(radii) if isinstance(radii, (list, tuple)) else [radii] * 4
        self.polygon(L.rounded_rect(x0, x1, z0, z1, radii, steps=10), fill)

    def circle(self, x, z, r, fill):
        cx, cy = self.p(x, z)
        self.draw.ellipse([cx - r * self.s, cy - r * self.s, cx + r * self.s, cy + r * self.s], fill=fill)

    def ring(self, x, z, r, width, fill):
        cx, cy = self.p(x, z)
        self.draw.ellipse([cx - r * self.s, cy - r * self.s, cx + r * self.s, cy + r * self.s], outline=fill,
                          width=max(1, round(width * self.s)))

    def line(self, points, width, fill):
        self.draw.line([self.p(x, z) for x, z in points], fill=fill, width=max(1, round(width * self.s)), joint="curve")
        r = width / 2
        for x, z in (points[0], points[-1]):
            self.circle(x, z, r, fill)

    def outline(self, points, width, fill):
        self.line(points + points[:1], width, fill)

    def text(self, s, name, cap_mm, x, z, fill, anchor="centre", degrees=0.0, stretch=1.0, spacing=0.0):
        """Text whose capitals are cap_mm high, its left edge (or centre, or right edge) at x and its middle at z."""
        probe = font(name, 200)
        _, top, _, bottom = probe.getbbox("H")
        size = 200 * cap_mm * self.s / (bottom - top)
        f = font(name, size)
        left, top, right, bottom = f.getbbox(s)
        pad = round(size)
        extra = round(spacing * self.s) * max(0, len(s) - 1)
        layer = Image.new("RGBA", (right - left + 2 * pad + extra, bottom - top + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if spacing:
            cursor = pad - left
            for ch in s:
                d.text((cursor, pad - top), ch, font=f, fill=fill)
                cursor += f.getlength(ch) + spacing * self.s
        else:
            d.text((pad - left, pad - top), s, font=f, fill=fill)
        if stretch != 1.0:
            layer = layer.resize((max(1, round(layer.width * stretch)), layer.height), Image.LANCZOS)
        if degrees:
            layer = layer.rotate(degrees, resample=Image.BICUBIC, expand=True)
        box = layer.getbbox()
        if box is None:
            return
        layer = layer.crop(box)
        cx, cy = self.p(x, z)
        offset = {"left": 0, "centre": layer.width / 2, "right": layer.width}[anchor]
        self.img.alpha_composite(layer, (round(cx - offset), round(cy - layer.height / 2)))

    def paste(self, image, x0, x1, z0, z1, resample=Image.LANCZOS):
        """An image stretched over the box (x0..x1, z0..z1)."""
        a, b = self.p(x0, z1)
        c, d = self.p(x1, z0)
        layer = image.convert("RGBA").resize((max(1, round(c - a)), max(1, round(d - b))), resample)
        self.img.alpha_composite(layer, (round(a), round(b)))

    def layer(self):
        return Image.new("RGBA", self.img.size, (0, 0, 0, 0))

    def over(self, layer, mask=None):
        if mask is not None:
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
        self.img.alpha_composite(layer)


def psp_logo(c, x, z, width, stroke, fill):
    """The PSP logotype's squared letters, P, S, P, in thin strokes, width wide, centred at (x, z)."""
    w = width / 3.6
    h = w * 0.46
    gap = (width - 3 * w) / 2
    z0, z1, zm = z - h / 2, z + h / 2, z
    for k, letter in enumerate("PSP"):
        x0 = x - width / 2 + k * (w + gap)
        x1 = x0 + w
        if letter == "P":
            c.line([(x0, z0), (x0, z1), (x1, z1), (x1, zm), (x0 + w * 0.3, zm)], stroke, fill)
        else:
            c.line([(x1, z1), (x0, z1), (x0, zm), (x1, zm), (x1, z0), (x0, z0)], stroke, fill)


def ps_mark(c, x, z, size, fill, ground):
    """A small PlayStation mark, size high: the P standing, and the S lying flat across its foot."""
    s = size
    # The P: its bowl a half ring on its stem's top.
    bx, bz = x + 0.06 * s, z + 0.26 * s
    c.circle(bx, bz, 0.24 * s, fill)
    c.circle(bx, bz, 0.105 * s, ground)
    c.polygon([(bx - 0.3 * s, bz - 0.3 * s), (bx, bz - 0.3 * s), (bx, bz + 0.3 * s), (bx - 0.3 * s, bz + 0.3 * s)], ground)
    c.polygon([(x - 0.2 * s, z - 0.5 * s), (x - 0.04 * s, z - 0.43 * s), (x - 0.04 * s, z + 0.5 * s),
               (x - 0.2 * s, z + 0.5 * s)], fill)
    c.polygon([(x - 0.06 * s, z + 0.5 * s), (bx, z + 0.5 * s), (bx, z + 0.5 * s - 0.135 * s),
               (x - 0.06 * s, z + 0.5 * s - 0.135 * s)], fill)
    c.polygon([(x - 0.06 * s, bz - 0.24 * s), (bx, bz - 0.24 * s), (bx, bz - 0.105 * s), (x - 0.06 * s, bz - 0.105 * s)],
              fill)
    # The S, flattened and sheared as if lying on the ground in front of the P.
    path = []
    for k in range(25):
        u = k / 24
        path.append((x + 0.55 * s - 1.1 * s * (0.5 - 0.5 * math.cos(math.pi * u)) + 0.42 * s * math.sin(2 * math.pi * u),
                     z - 0.12 * s - 0.36 * s * u))
    c.line(path, 0.11 * s, fill)


def symbol(c, name, x, z, r, width, fill):
    """A face button's symbol, about r from its middle."""
    if name == "triangle":
        c.outline([(x + r * math.cos(math.radians(a)), z - 0.15 * r + r * math.sin(math.radians(a))) for a in (90, 210, 330)],
                  width, fill)
    elif name == "circle":
        c.ring(x, z, r * 0.9, width, fill)
    elif name == "cross":
        d = r * 0.72
        c.line([(x - d, z - d), (x + d, z + d)], width, fill)
        c.line([(x - d, z + d), (x + d, z - d)], width, fill)
    else:
        d = r * 0.72
        c.outline([(x - d, z - d), (x + d, z - d), (x + d, z + d), (x - d, z + d)], width, fill)


def grown(points, centre, amount):
    cx, cz = centre
    return [(x + (x - cx) / math.hypot(x - cx, z - cz) * amount, z + (z - cz) / math.hypot(x - cx, z - cz) * amount)
            for x, z in points]


def glossy(c, x, z, r, colour):
    """A domed button's top seen square on: its colour, a little darker towards its rim (the dome's own shading does
    the rest)."""
    base = c.layer()
    d = ImageDraw.Draw(base)
    cx, cy = c.p(x, z)
    R = r * c.s
    for k in range(12):
        t = k / 11
        rr = R * (1 - 0.35 * t)
        tone = rgb(colour, 0.8 + 0.35 * t)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=tone)
    c.over(base)


# ---- Odyssey, the first made-up game (other cards' print scripts import these) ---------------------------------------

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


# ---- The face --------------------------------------------------------------------------------------------------------

def front():
    c = Canvas(L.PRINT_REGIONS["front"]["mm"], rgb(CASE))
    # The speaker's holes along the top.
    g = L.GRILLE
    for row in range(g["rows"]):
        z = g["z"] + row * g["pitch"]
        x = g["x"][0] + (g["pitch"] / 2 if row % 2 else 0.0)
        while x < g["x"][1]:
            c.circle(x, z, 0.24, rgb(CASE, 0.4))
            x += g["pitch"]
    # The glass: its edge catches the light a little round the video's quad.
    (x0, x1), (z0, z1) = L.GLASS["x"], L.GLASS["z"]
    c.rounded(x0 - 0.5, x1 + 0.5, z0 - 0.5, z1 + 0.5, 1.4, rgb("#33343A"))
    c.rounded(x0 - 0.1, x1 + 0.1, z0 - 0.1, z1 + 0.1, 1.0, rgb("#08090B"))
    ps_mark(c, -66.5, 61.0, 4.4, rgb("#8E9299"), rgb(CASE))
    c.text("SONY", "timesbd.ttf", 2.0, 58.8, 65.4, rgb("#B9BDC4"), stretch=1.15, spacing=0.12)
    dpad(c)
    face_buttons(c)
    nub(c)
    lights(c)
    for x, z in L.SPEAKERS:
        c.rounded(x - 1.6, x + 1.6, z - 0.7, z + 0.7, 0.7, rgb("#050506"))
    bottom_row(c)
    corner(c)
    return c


def dpad(c):
    cx, cz = L.DPAD["x"], L.DPAD["z"]
    c.circle(cx, cz, L.DPAD["well"] + 0.35, rgb(CASE, 0.55))
    c.circle(cx, cz, L.DPAD["well"], rgb(CASE, 1.12))
    for _, a in L.DPAD_BUTTONS:
        corners, radii = L.pentagon(cx, cz, a)
        c.polygon(L.rounded_polygon(grown(corners, (cx, cz), 0.6), [r + 0.4 for r in radii]), rgb(CASE, 0.45))
    for _, a in L.DPAD_BUTTONS:
        corners, radii = L.pentagon(cx, cz, a)
        c.polygon(L.rounded_polygon(corners, radii), rgb(TOP))
        # The arrow on its top: a small hollow triangle pointing outwards.
        co, si = math.cos(math.radians(a)), math.sin(math.radians(a))
        mx, mz = cx + 8.6 * co, cz + 8.6 * si
        c.outline([(mx + 1.5 * co, mz + 1.5 * si), (mx - 0.9 * co - 1.6 * si, mz - 0.9 * si + 1.6 * co),
                   (mx - 0.9 * co + 1.6 * si, mz - 0.9 * si - 1.6 * co)], 0.26, rgb(LEGEND))


def face_buttons(c):
    cx, cz = L.FACE["x"], L.FACE["z"]
    c.ring(cx, cz, L.FACE["ring"], 0.3, rgb(CASE, 0.45))
    r = L.FACE["radius"]
    for name, x, z in L.face_centres():
        c.circle(x, z, r + 0.75, rgb(CASE, 0.4))
        glossy(c, x, z, r, TOP)
        symbol(c, name, x, z, r * 0.5, 0.3, rgb("#B8BCC3"))


def nub(c):
    x, z, r = L.NUB["x"], L.NUB["z"], L.NUB["radius"]
    c.circle(x, z, L.NUB["well"] + 0.3, rgb(CASE, 0.4))
    c.circle(x, z, L.NUB["well"], rgb(CASE, 0.75))
    c.circle(x, z, r, rgb("#34343B"))
    c.circle(x, z, r - 0.9, rgb("#2B2B31"))
    # The rubbery top's knurling: a grid of fine dimples inside its flat.
    step = 0.62
    for i in range(-12, 13):
        for j in range(-12, 13):
            dx, dz = i * step, j * step
            if math.hypot(dx, dz) < r - 1.2:
                c.circle(x + dx, z + dz, 0.15, rgb("#1E1E23"))


def lights(c):
    """The Memory Stick and WLAN lights at the left, POWER and HOLD at the right, all unlit (psp.py lights POWER)."""
    off = rgb("#2E3533")
    r = L.LIGHTS["r"]
    for name in ("memory", "wlan", "power", "hold"):
        c.circle(*L.LIGHTS[name], r, off)
    mx, mz = L.LIGHTS["memory"]
    c.polygon([(mx + 2.6, mz - 0.7), (mx + 5.6, mz - 0.7), (mx + 5.6, mz + 0.7), (mx + 5.0, mz + 1.0),
               (mx + 2.6, mz + 1.0)], rgb(LEGEND))
    c.rounded(mx + 3.1, mx + 5.1, mz - 0.3, mz + 0.6, 0.1, rgb(CASE))
    wx, wz = L.LIGHTS["wlan"]
    for rr in (0.8, 1.5, 2.2):
        c.line([(wx + 1.0 + rr * math.cos(math.radians(a)), wz - 0.8 + rr * math.sin(math.radians(a)))
                for a in range(0, 91, 15)], 0.25, rgb(LEGEND))
    c.circle(wx + 1.0, wz - 0.8, 0.35, rgb(LEGEND))
    px, pz = L.LIGHTS["power"]
    c.text("POWER", "arialbd.ttf", 1.05, px - 2.2, pz, rgb("#4FCB82"), anchor="right")
    hx, hz = L.LIGHTS["hold"]
    c.text("HOLD", "arialbd.ttf", 1.05, hx - 1.9, hz, rgb("#C4C8CE"), anchor="right")


def bottom_row(c):
    z = L.ROW_Z
    for name, x, shape in L.ROW:
        if shape == "shield":
            corners, radii = L.shield(x, z)
            c.polygon(L.rounded_polygon(grown(corners, (x, z), 0.55), [r + 0.4 for r in radii]), rgb(CASE, 0.45))
            c.polygon(L.rounded_polygon(corners, radii), rgb(TOP))
            c.text(name, "arialbd.ttf", 0.85, x, z + 0.3, rgb(LEGEND))
        else:
            c.rounded(x - 3.45, x + 3.45, z - 2.95, z + 2.95, 2.9, rgb(CASE, 0.45))
            c.rounded(x - 2.9, x + 2.9, z - 2.4, z + 2.4, 2.35, rgb(TOP))
            if name == "VOL-":
                c.line([(x - 0.9, z), (x + 0.9, z)], 0.3, rgb(LEGEND))
            elif name == "VOL+":
                c.line([(x - 0.9, z), (x + 0.9, z)], 0.3, rgb(LEGEND))
                c.line([(x, z - 0.9), (x, z + 0.9)], 0.3, rgb(LEGEND))
            elif name == "DISPLAY":
                c.rounded(x - 1.2, x + 1.2, z - 0.8, z + 0.8, 0.3, rgb(LEGEND))
                c.rounded(x - 0.9, x + 0.9, z - 0.5, z + 0.5, 0.2, rgb(TOP))
            else:
                c.text("♪", "seguisym.ttf", 1.7, x, z, rgb(LEGEND))
    c.text("VOL", "arialbd.ttf", 0.78, -32.8, z, rgb(LEGEND))
    psp_logo(c, 0.0, z - 0.3, 22.0, 0.34, rgb("#B4B8BF"))


def corner(c):
    """The face's lower left: a clear piece over the strap's silver loop."""
    (x0, x1), (z0, z1) = L.CORNER["x"], L.CORNER["z"]
    c.rounded(x0, x1, z0, z1, [1.0, 2.0, 2.0, 1.0], rgb("#5E646C"))
    c.rounded(x0 + 1.2, x1 - 1.4, z0 + 1.6, z1 - 1.6, 1.2, rgb("#34383E"))
    c.rounded(x0 + 1.6, x1 - 1.8, z0 + 2.0, z1 - 2.0, 0.8, rgb("#8A9098"))
    sheen = c.layer()
    ImageDraw.Draw(sheen).rectangle([*c.p(x0, z1), *c.p(x1, z1 - 1.2)], fill=(255, 255, 255, 36))
    c.over(sheen)


# ---- The back and the top edge ---------------------------------------------------------------------------------------

def rear():
    """The back, seen from behind (x is the face's, negated): the bay under the door, the battery cover on the viewer's
    left (the console's right end), the Memory Stick's end on the right."""
    c = Canvas(L.PRINT_REGIONS["rear"]["mm"], rgb(REAR))
    # The bay: a dark well, the spindle, the laser's track and its lens, the door's hinges at its foot.
    c.polygon(L.door_outline(-0.3), rgb(REAR, 0.55))
    c.polygon(L.door_outline(L.BAY["inset"]), rgb("#111114"))
    cz = L.RING["z"]
    c.circle(0.0, cz, 31.0, rgb("#18181C"))
    c.rounded(-30.0, -6.0, cz - 3.2, cz + 3.2, 1.0, rgb("#09090B"))
    c.rounded(-21.0, -15.0, cz - 1.9, cz + 1.9, 0.4, rgb("#2C2E36"))
    c.circle(-18.0, cz, 1.1, rgb("#5A6CB0"))
    c.circle(0.0, cz, 5.6, rgb("#4A4C52"))
    c.circle(0.0, cz, 3.7, rgb("#8A8D94"))
    c.circle(0.0, cz, 1.4, rgb("#5A5C62"))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        c.circle(2.6 * math.cos(a), cz + 2.6 * math.sin(a), 0.5, rgb("#B0B3B9"))
    (x0, x1), (z0, z1) = L.DOOR["x"], L.DOOR["z"]
    for x in (x0 + 9.0, x1 - 9.0):
        c.rounded(x - 3.0, x + 3.0, z0 + 1.4, z0 + 3.0, 0.5, rgb("#2C2C33"))
    # The battery cover (the viewer's left), its release; SONY above it.
    c.rounded(-80.0, -40.5, 9.0, 66.0, [9.0, 4.0, 4.0, 9.0], rgb(REAR, 0.62))
    c.rounded(-79.6, -40.9, 9.4, 65.6, [8.6, 3.6, 3.6, 8.6], rgb(REAR, 1.04))
    c.rounded(-79.0, -74.0, 31.0, 43.0, 1.2, rgb(REAR, 0.7))
    c.rounded(-78.6, -74.4, 31.4, 42.6, 1.0, rgb(REAR, 1.12))
    c.text("PUSH", "arialbd.ttf", 0.8, -76.5, 37.0, rgb(REAR, 1.9), degrees=90)
    c.polygon([(-71.5, 37.0), (-69.4, 38.4), (-69.4, 35.6)], rgb(REAR, 1.7))
    c.text("SONY", "timesbd.ttf", 1.7, -50.0, 69.6, rgb(REAR, 2.4), stretch=1.15, spacing=0.1)
    # The Memory Stick's end (the viewer's right): two screws by the door, MAGICGATE along the end.
    for z in (64.0, 17.0):
        c.circle(42.5, z, 1.0, rgb(REAR, 0.5))
        c.circle(42.5, z, 0.6, rgb(REAR, 0.8))
    c.text("MAGICGATE", "arialbd.ttf", 0.9, 79.5, 44.0, rgb(REAR, 2.0), degrees=-90)
    c.text("PSP-1003", "arial.ttf", 0.8, 60.0, 12.5, rgb(REAR, 1.7))
    # The seams beside the door.
    for x in (x0 - 0.6, x1 + 0.6):
        c.line([(x, z0 + 3.0), (x, z1 - 1.0)], 0.25, rgb(REAR, 0.5))
    return c


def top():
    """The top edge seen from above, its face towards the bottom: y (depth) up the region. The band's silver strip
    between the shoulder buttons: the IR window, the USB port and its screws, OPEN by the latch's track."""
    x0, x1, y0, y1 = L.PRINT_REGIONS["top"]["mm"]
    c = Canvas((x0, x1, y0, y1), rgb(REAR))
    c.rounded(x0, x1, y0, L.SEAM, 0.0, rgb(CASE))                   # the face's shell
    b0, b1 = L.BAND
    c.rounded(x0, x1, b0 - 0.3, b1 + 0.3, 0.0, rgb(SILVER))
    # The strip's brushed grain.
    grain = c.layer()
    gd = ImageDraw.Draw(grain)
    rng = random.Random(1000)
    for k in range(260):
        yy = rng.uniform(b0, b1)
        gd.line([c.p(x0, yy), c.p(x1, yy)], fill=(255, 255, 255, rng.randint(6, 22)), width=1)
    c.over(grain)
    mid = (b0 + b1) / 2
    ix0, ix1 = L.TOP["ir"]
    c.rounded(ix0, ix1, mid - 1.6, mid + 1.6, 1.6, rgb("#141417"))
    c.rounded(ix0 + 1.0, ix1 - 3.0, mid - 0.6, mid + 0.9, 0.6, rgb("#2C2F38"))
    ux0, ux1 = L.TOP["usb"]
    c.rounded(ux0 - 1.0, ux1 + 1.0, mid - 1.9, mid + 1.9, 0.6, rgb("#7E838B"))
    c.rounded(ux0, ux1, mid - 1.3, mid + 1.3, 0.4, rgb("#101013"))
    c.rounded(ux0 + 1.0, ux1 - 1.0, mid - 0.3, mid + 0.4, 0.1, rgb("#8C8F96"))
    for x in (ux0 - 2.4, ux1 + 2.4):
        c.rounded(x - 0.5, x + 0.5, mid - 0.7, mid + 0.7, 0.2, rgb("#E2A030"))
    c.text("⇌", "seguisym.ttf", 1.4, ux0 - 6.0, mid, rgb("#5A5E66"))
    for x in L.TOP["screws"]:
        c.circle(x, mid, 1.2, rgb("#6C7078"))
        c.circle(x, mid, 0.85, rgb("#9DA1A8"))
        c.line([(x - 0.6, mid), (x + 0.6, mid)], 0.22, rgb("#4A4E55"))
        c.line([(x, mid - 0.6), (x, mid + 0.6)], 0.22, rgb("#4A4E55"))
    # The OPEN latch's track, and the latch at rest in it (psp.py's latch takes its top from here): its grip's ridges,
    # OPEN and the arrow towards R.
    lx0, lx1 = L.LATCH["x"]
    c.rounded(lx0 - 0.6, lx1 + L.LATCH["travel"] + 0.6, mid - 2.0, mid + 2.0, 1.0, rgb("#4A4E56"))
    c.rounded(lx0, lx1, mid - 1.6, mid + 1.6, 0.8, rgb("#B9BEC6"))
    for k in range(5):
        x = lx0 + 1.2 + k * 0.7
        c.line([(x, mid - 1.1), (x, mid + 1.1)], 0.25, rgb("#7C818A"))
    c.text("OPEN", "arialbd.ttf", 0.95, lx0 + 7.6, mid, rgb("#3C4048"))
    c.polygon([(lx1 - 2.4, mid - 0.8), (lx1 - 0.9, mid), (lx1 - 2.4, mid + 0.8)], rgb("#3C4048"))
    return c


def swatches(image):
    d = ImageDraw.Draw(image)
    colours = dict(L.COLOURS, case=CASE)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 10, y - 10, x + 9, y + 9], fill=rgb(colours[name]))


def paste_region(image, px, canvas):
    """A canvas into its region, the region's edge pixels bled 4 pixels out round it, so filtering and mipmaps at its
    edges see its own colours."""
    x, y, w, h = px
    region = canvas.img.convert("RGB").resize((w, h), Image.LANCZOS)
    image.paste(region.resize((w + 8, h + 8), Image.NEAREST), (x - 4, y - 4))
    image.paste(region, (x, y))


def print_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(CASE))
    for name, draw in (("front", front), ("rear", rear), ("top", top)):
        paste_region(image, L.PRINT_REGIONS[name]["px"], draw())
    swatches(image)
    return image


# ---- The UMD and its door ----------------------------------------------------------------------------------------------

def made_up(made_up_dir):
    """The UMD's game: a made-up game from tools/made-up-games's library (arcade_print.Game)."""
    from arcade_print import Game
    stem, system = L.MADE_UP
    return Game(stem, made_up_dir, system)


def fit(img, size, centre=(0.5, 0.5)):
    return ImageOps.fit(img.convert("RGB"), size, Image.LANCZOS, centering=centre)


def logo_at(game, width):
    k = width / game.logo.width
    return game.logo.resize((max(1, round(game.logo.width * k)), max(1, round(game.logo.height * k))), Image.LANCZOS)


def umd_label(game):
    """The UMD's label side, seen looking at it: the white shell, the disc's label through its window (the game's key art
    and logo round the hub), the logotype and a controller on the shell."""
    c = Canvas(L.MEDIA_REGIONS["umd"]["mm"], rgb(L.COLOURS["umd"]))
    c.polygon(L.umd_outline(), rgb(L.COLOURS["umd"]))
    r = L.UMD["disc"]
    c.circle(0.0, 0.0, r + 0.7, rgb("#B9BCC2"))
    size = round(2 * r * c.s)
    art = fit(game.keyart, (size, size), (0.5, 0.45)).convert("RGBA")
    art = ImageEnhance.Brightness(art).enhance(0.92)
    logo = logo_at(game, size * 0.78)
    art.alpha_composite(logo, ((size - logo.width) // 2, round(size * 0.13)))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    art.putalpha(mask)
    c.paste(art, -r, r, -r, r)
    # The hub: white, the format's name; the clear ring round the spindle's hole.
    c.circle(0.0, 0.0, 10.4, rgb("#F4F4F2"))
    c.ring(0.0, 0.0, 10.4, 0.25, rgb("#C9CBD0"))
    c.text("UMD", "segoeui.ttf", 2.6, 0.0, 1.4, rgb("#4C58B8"))
    c.text("UNIVERSAL MEDIA DISC", "segoeui.ttf", 0.6, 0.0, -2.0, rgb("#4C58B8"))
    c.text("ULES-04215", "arialbd.ttf", 1.0, 0.0, -23.0, rgb("#F2F2F2"))
    c.text(f"© {game.publisher.upper()}", "arial.ttf", 0.75, 0.0, -25.4, rgb("#E0E0E8"))
    # Under the window, on the shell: the logotype and a controller.
    psp_logo(c, -21.5, -28.6, 8.0, 0.3, rgb("#7A7E86"))
    c.rounded(19.0, 25.0, -29.8, -27.4, 1.1, rgb("#7A7E86"))
    c.circle(19.6, -29.6, 1.1, rgb("#7A7E86"))
    c.circle(24.4, -29.6, 1.1, rgb("#7A7E86"))
    return c


def umd_back():
    """The UMD's other side, seen looking at it: the disc's silver under the clear back, the hub, the opening."""
    c = Canvas(L.MEDIA_REGIONS["umd_rear"]["mm"], rgb(L.COLOURS["umd"]))
    r = L.UMD["disc"]
    c.circle(0.0, 0.0, r + 0.7, rgb("#C4C7CC"))
    size = round(2 * r * c.s)
    disc = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(disc)
    for k in range(size // 2, 0, -2):
        v = int(150 + 70 * math.sin(k / (size / 2) * math.pi * 3))
        d.ellipse([size / 2 - k, size / 2 - k, size / 2 + k, size / 2 + k], fill=(v, v + 4, v + 10, 255))
    rainbow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(rainbow)
    for k, colour in enumerate(((255, 120, 120), (255, 220, 120), (140, 255, 160), (120, 190, 255), (200, 140, 255))):
        o = size * (0.07 + k * 0.017)
        dr.arc([o, o, size - o, size - o], 200, 250, fill=colour + (150,), width=max(2, size // 50))
    disc = Image.alpha_composite(disc, rainbow.filter(ImageFilter.GaussianBlur(size / 100)))
    mask = Image.new("L", disc.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    disc.putalpha(mask)
    c.paste(disc, -r, r, -r, r)
    c.rounded(-29.0, -10.0, -3.0, 12.0, 1.2, rgb("#A9ADB4"))
    c.rounded(-28.2, -10.8, -2.2, 11.2, 0.8, rgb("#BFC3C9"))
    c.circle(0.0, 0.0, 8.5, rgb("#D9DBDF"))
    c.circle(0.0, 0.0, 4.2, rgb("#9A9EA6"))
    c.circle(0.0, 0.0, 1.3, rgb("#5E6168"))
    for x in (-18.0, 18.0):
        c.circle(x, -28.6, 1.2, rgb("#BDC0C6"))
    return c


def door():
    """The UMD door's outside, seen from behind (x negated): the matte panel, the brushed aluminium ring round the
    logotype, UMD at its top right."""
    c = Canvas(L.MEDIA_REGIONS["door"]["mm"], rgb(REAR))
    c.polygon(L.door_outline(), rgb(REAR, 1.08))
    c.polygon(L.door_outline(0.7), rgb(REAR))
    cz, outer, inner = L.RING["z"], L.RING["outer"], L.RING["inner"]
    c.circle(0.0, cz, outer + 0.25, rgb("#5E6269"))
    # The ring: turned aluminium, its grain concentric, the light catching it on two opposite arcs.
    layer = c.layer()
    d = ImageDraw.Draw(layer)
    cx, cy = c.p(0.0, cz)
    R = outer * c.s
    for a in range(0, 360, 2):
        v = int(196 + 44 * math.cos(math.radians(2 * a - 70)))
        d.pieslice([cx - R, cy - R, cx + R, cy + R], a, a + 2, fill=(v, v + 3, v + 8, 255))
    c.over(layer)
    grain = c.layer()
    gd = ImageDraw.Draw(grain)
    rng = random.Random(41)
    for k in range(90):
        rr = rng.uniform(inner, outer) * c.s
        tone = rng.choice((255, 0))
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(tone, tone, tone, rng.randint(6, 18)), width=1)
    ring = Image.new("L", c.img.size, 0)
    md = ImageDraw.Draw(ring)
    md.ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    ri = inner * c.s
    md.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=0)
    c.over(grain, ring)
    c.circle(0.0, cz, inner + 0.2, rgb("#75797F"))
    c.circle(0.0, cz, inner, rgb(REAR))
    psp_logo(c, 0.0, cz, 30.0, 0.45, rgb("#DADDE2"))
    (x0, x1), (z0, z1) = L.DOOR["x"], L.DOOR["z"]
    c.text("UMD", "segoeui.ttf", 1.6, x1 - 5.5, z1 - 3.2, rgb("#9A9EA6"))
    return c


def media_atlas(game):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["umd"]))
    for name, canvas in (("umd", umd_label(game)), ("umd_rear", umd_back()), ("door", door())):
        paste_region(image, L.MEDIA_REGIONS[name]["px"], canvas)
    d = ImageDraw.Draw(image)
    for name, colour in (("umd", L.COLOURS["umd"]), ("inside", "#151518"), ("edge", "#D6D8DC")):
        x, y = L.MEDIA_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(colour))
    return image


# ---- The screens -------------------------------------------------------------------------------------------------------
# Each screen is drawn at twice the LCD's 480 x 272 and halved, so its edges are smooth, then put on the glass.

W2, H2 = 2 * L.LCD_PX[0], 2 * L.LCD_PX[1]
BORDER = (6, 7, 8)
LCD_OFF = (34, 37, 41)


def sheen(size, strength):
    """The glass's reflection: a soft diagonal band of light, the same on every frame."""
    w, h = size
    band = Image.new("L", size, 0)
    d = ImageDraw.Draw(band)
    d.polygon([(w * 0.12, 0), (w * 0.42, 0), (w * 0.22, h), (-w * 0.08, h)], fill=255)
    return band.filter(ImageFilter.GaussianBlur(w * 0.06)).point(lambda v: round(v * strength))


_SHEEN = {}


def off_panel():
    """The LCD switched off: a dark grey, a little darker towards its foot."""
    w, h = L.LCD_PX
    shade = Image.linear_gradient("L").resize((w, h)).point(lambda v: round(v * 0.22))
    return Image.composite(Image.new("RGB", (w, h), (20, 22, 25)), Image.new("RGB", (w, h), LCD_OFF), shade)


def glass(lcd=None, off=1.0):
    """The glass's frame, VIDEO_PX: black round the LCD, which shows lcd (480 x 272) or, without it, is switched off.
    off (0 to 1) mixes lcd towards the switched-off LCD, as its backlight dies."""
    if "panel" not in _SHEEN:
        _SHEEN["panel"] = off_panel()
        _SHEEN["glass"] = sheen(L.VIDEO_PX, 0.06)
    frame = Image.new("RGB", L.VIDEO_PX, BORDER)
    if lcd is None:
        panel = _SHEEN["panel"]
    else:
        panel = lcd.convert("RGB")
        if off > 0:
            panel = Image.blend(panel, _SHEEN["panel"], min(1.0, off))
    frame.paste(panel, L.LCD_AT)
    return Image.composite(Image.new("RGB", L.VIDEO_PX, (255, 255, 255)), frame, _SHEEN["glass"])


def still():
    """The switched-off screen: the video's material's own texture, and its first and last frame."""
    return glass()


def half(img):
    return img.convert("RGB").resize(L.LCD_PX, Image.LANCZOS)


def boot(t):
    """The PSP's start-up, t from 0 to 1: a line of white light opens across the black, swells into a glow that sweeps
    away, and SONY COMPUTER ENTERTAINMENT comes up out of it, then fades."""
    img = Image.new("RGB", (W2, H2), (0, 0, 0))
    glow = Image.new("L", (W2, H2), 0)
    d = ImageDraw.Draw(glow)
    cy = H2 * 0.5
    if t < 0.45:
        k = t / 0.45
        width = W2 * (0.1 + 0.9 * (1 - (1 - min(1.0, k * 1.6)) ** 2))
        thick = 4 + 60 * math.sin(math.pi * k) ** 2
        v = round(255 * (1 - max(0.0, k - 0.6) / 0.4))
        d.ellipse([W2 / 2 - width / 2, cy - thick / 2, W2 / 2 + width / 2, cy + thick / 2], fill=v)
        glow = glow.filter(ImageFilter.GaussianBlur(6 + 30 * k))
        core = Image.new("L", (W2, H2), 0)
        ImageDraw.Draw(core).rectangle([W2 / 2 - width / 2, cy - 1.5, W2 / 2 + width / 2, cy + 1.5], fill=v)
        glow = ImageChops.lighter(glow, core.filter(ImageFilter.GaussianBlur(2)))
    img = Image.composite(Image.new("RGB", (W2, H2), (255, 255, 255)), img, glow)
    if t > 0.3:
        a = min(1.0, (t - 0.3) / 0.15) * (1 - max(0.0, (t - 0.85) / 0.15))
        words = Image.new("L", (W2, H2), 0)
        f = font("segoeuisl.ttf", 34)
        wd = ImageDraw.Draw(words)
        text = "SONY COMPUTER ENTERTAINMENT"
        spacing = 5
        width = sum(f.getlength(ch) + spacing for ch in text) - spacing
        x = (W2 - width) / 2
        for ch in text:
            wd.text((x, cy), ch, font=f, fill=round(255 * a), anchor="lm")
            x += f.getlength(ch) + spacing
        img = Image.composite(Image.new("RGB", (W2, H2), (255, 255, 255)), img, words)
    return half(img)


# The XMB, drawn at 2x: the wave over its gradient, the categories along the top with Game chosen, the UMD's game at
# the top of the Game column with its icon, then its background.

XMB_TOP, XMB_BOTTOM = (16, 52, 128), (70, 132, 214)


def xmb_backdrop(t):
    """The XMB's background at t seconds: its gradient and the wave, whose ribbons drift and swell."""
    img = Image.linear_gradient("L").resize((W2, H2))
    img = Image.merge("RGB", [img.point(lambda v, a=a, b=b: round(a + (b - a) * v / 255)) for a, b in zip(XMB_TOP, XMB_BOTTOM)])
    layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ribbons = [(0.07, 1.25, 0.4, 0.62, 210, 4, 0.55), (0.09, 1.05, 1.3, 0.65, 170, 3, -0.4),
               (0.05, 0.85, 2.2, 0.67, 150, 3, 0.8), (0.08, 1.6, 3.0, 0.61, 110, 8, 0.3), (0.045, 0.7, 4.1, 0.69, 180, 3, -0.7)]
    for amp, length, phase, base, alpha, width, speed in ribbons:
        swell = 1 + 0.25 * math.sin(t * 1.3 + phase)
        pts = [(x, base * H2 + amp * swell * H2 * math.sin(2 * math.pi * x / (length * W2) + phase + speed * t * 2.2))
               for x in range(0, W2 + 8, 8)]
        d.line(pts, fill=(205, 228, 255, alpha), width=width)
    glow = layer.filter(ImageFilter.GaussianBlur(12))
    img = img.convert("RGBA")
    img.alpha_composite(glow)
    img.alpha_composite(glow)
    img.alpha_composite(layer)
    return img


def xmb_icons(d, y, chosen_fill, dim):
    def gear(cx, s, fill):
        for k in range(8):
            a = math.radians(k * 45)
            d.line([(cx + 0.6 * s * math.cos(a), y + 0.6 * s * math.sin(a)), (cx + s * math.cos(a), y + s * math.sin(a))],
                   fill=fill, width=int(s / 3))
        d.ellipse([cx - 0.7 * s, y - 0.7 * s, cx + 0.7 * s, y + 0.7 * s], fill=fill)
        d.ellipse([cx - 0.3 * s, y - 0.3 * s, cx + 0.3 * s, y + 0.3 * s], fill=(40, 80, 160, 255))

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
            d.rectangle([x, y - 0.5 * s, x + 0.18 * s, y - 0.32 * s], fill=(40, 80, 160, 255))
            d.rectangle([x, y + 0.32 * s, x + 0.18 * s, y + 0.5 * s], fill=(40, 80, 160, 255))

    def game(cx, s, fill):
        d.rounded_rectangle([cx - s, y - 0.5 * s, cx + s, y + 0.5 * s], int(0.45 * s), fill=fill)
        d.ellipse([cx - 0.95 * s, y - 0.2 * s, cx - 0.35 * s, y + 0.75 * s], fill=fill)
        d.ellipse([cx + 0.35 * s, y - 0.2 * s, cx + 0.95 * s, y + 0.75 * s], fill=fill)
        d.rectangle([cx - 0.62 * s, y - 0.1 * s, cx - 0.5 * s, y + 0.3 * s], fill=(40, 80, 160, 255))
        d.rectangle([cx - 0.76 * s, y + 0.04 * s, cx - 0.36 * s, y + 0.16 * s], fill=(40, 80, 160, 255))
        for dx, dy in ((0.55, 0.0), (0.7, 0.15), (0.4, 0.15), (0.55, 0.3)):
            d.ellipse([cx + dx * s - 0.06 * s, y + dy * s - 0.06 * s, cx + dx * s + 0.06 * s, y + dy * s + 0.06 * s],
                      fill=(40, 80, 160, 255))

    def network(cx, s, fill):
        d.ellipse([cx - s, y - s, cx + s, y + s], outline=fill, width=4)
        d.ellipse([cx - 0.4 * s, y - s, cx + 0.4 * s, y + s], outline=fill, width=3)
        d.line([(cx - s, y), (cx + s, y)], fill=fill, width=3)

    for draw, cx in ((gear, 74), (photo, 174), (music, 274), (video, 374)):
        draw(cx, 26, dim)
    game(520, 46, chosen_fill)
    network(680, 26, dim)


def icon0(game):
    """The game's icon in the XMB, 144 x 80 at 1x (288 x 160 here): its key art, its logo across it."""
    art = fit(game.keyart, (288, 160), (0.5, 0.42)).convert("RGBA")
    logo = logo_at(game, 250)
    art.alpha_composite(logo, ((288 - logo.width) // 2, 160 - logo.height - 10))
    return art


def pic1(game):
    """The game's background in the XMB: its key art, dimmed, behind the menu."""
    img = fit(game.keyart, (W2, H2), (0.5, 0.45))
    return ImageEnhance.Brightness(img.filter(ImageFilter.GaussianBlur(1.5))).enhance(0.55).convert("RGBA")


def xmb(game, t, background=0.0, chosen=0.0, fade=1.0):
    """The XMB at t seconds: background (0 to 1) fades the game's own picture in behind it; chosen (0 to 1) flashes the
    game's icon as CROSS starts it; fade (0 to 1) from black."""
    img = xmb_backdrop(t)
    if background > 0:
        img = Image.blend(img, pic1(game), background)
    ui = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)
    white, dim = (255, 255, 255, 255), (255, 255, 255, 150)
    d.text((W2 - 214, 26), "27/10  21:43", font=font("segoeui.ttf", 26), fill=white)
    d.rounded_rectangle([W2 - 58, 30, W2 - 22, 50], 3, outline=white, width=3)
    d.rectangle([W2 - 54, 34, W2 - 30, 46], fill=white)
    d.rectangle([W2 - 20, 36, W2 - 16, 44], fill=white)
    xmb_icons(d, 128, white, dim)
    d.text((520, 198), "Game", font=font("segoeuib.ttf", 30), fill=white, anchor="mm")
    for k, text in enumerate(("Saved Data Utility", "Memory Stick™")):
        yy = 440 + k * 52
        d.rounded_rectangle([488, yy, 552, yy + 40], 6, outline=dim, width=3)
        d.text((582, yy + 20), text, font=font("segoeui.ttf", 24), fill=dim, anchor="lm")
    # The UMD's game, chosen: its icon glowing (breathing), its name.
    breathe = 0.6 + 0.4 * math.sin(t * 4.4)
    glow = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([432, 236, 736, 412], 14,
                                           fill=(255, 255, 255, min(255, round(110 + 90 * breathe + 120 * chosen))))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12)))
    img.alpha_composite(ui)
    icon = icon0(game)
    if chosen:
        icon = Image.blend(icon, Image.new("RGBA", icon.size, (255, 255, 255, 255)), 0.55 * chosen)
    img.alpha_composite(icon, (440, 244))
    d = ImageDraw.Draw(img)
    d.rectangle([440, 244, 727, 403], outline=white, width=2)
    d.text((750, 290), game.title, font=font("segoeuib.ttf", 34), fill=white, anchor="lm")
    d.text((752, 330), "UMD™", font=font("segoeui.ttf", 22), fill=(220, 232, 255, 255), anchor="lm")
    out = half(img)
    if fade < 1:
        out = Image.blend(Image.new("RGB", out.size, (0, 0, 0)), out, max(0.0, fade))
    return out


def title(game, t, prompt=True, fade=1.0, flash=0.0):
    """The game's title at t seconds: its key art drifting closer, its logo, PRESS START blinking (prompt), © its
    publisher; fade (0 to 1) from black, flash (0 to 1) to white."""
    zoom = 1.0 + 0.012 * t
    art = fit(game.keyart, (round(W2 * zoom), round(H2 * zoom)), (0.5, 0.45))
    art = art.crop(((art.width - W2) // 2, (art.height - H2) // 2, (art.width - W2) // 2 + W2, (art.height - H2) // 2 + H2))
    img = ImageEnhance.Brightness(art).enhance(0.82).convert("RGBA")
    shade = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle([0, 0, W2, 170], fill=(4, 8, 24, 110))
    img.alpha_composite(shade.filter(ImageFilter.GaussianBlur(40)))
    logo = logo_at(game, W2 * 0.72)
    img.alpha_composite(logo, ((W2 - logo.width) // 2, 34))
    d = ImageDraw.Draw(img)
    if prompt:
        d.text((W2 / 2, H2 - 92), "PRESS START", font=font("arialbd.ttf", 34), fill=(255, 255, 255), anchor="mm",
               stroke_width=3, stroke_fill=(10, 20, 60))
    d.text((W2 / 2, H2 - 34), f"© {game.publisher.upper()}", font=font("arial.ttf", 20), fill=(220, 226, 240), anchor="mm",
           stroke_width=2, stroke_fill=(10, 20, 60))
    out = half(img)
    if flash:
        out = Image.blend(out, Image.new("RGB", out.size, (255, 255, 255)), flash)
    if fade < 1:
        out = Image.blend(Image.new("RGB", out.size, (0, 0, 0)), out, max(0.0, fade))
    return out


# ---- The game played ---------------------------------------------------------------------------------------------------
# The painting's player ship and one of its fighters are cut out along hand-traced outlines (in the painting's 767 x 511
# pixels), and the painting filled in where they, the other fighters, the explosion, the lasers and the sight were.

PLAYER = [(351, 310), (371, 310), (380, 322), (390, 332), (412.5, 325), (418.5, 341), (462.5, 352.5), (520, 374),
          (556, 413), (542.5, 411), (465, 397.5), (462.5, 409), (450, 416), (410, 416), (390, 405), (350, 405),
          (327.5, 416), (290, 416), (272.5, 409), (270, 397.5), (192.5, 406), (179, 409), (217.5, 375), (275, 352.5),
          (320, 341), (322.5, 325), (335, 332), (342.5, 322)]
PLAYER_SPAN = 377.0                          # its wingspan, in the painting's pixels
NOZZLES = [(309.0, 414.0), (430.0, 414.0)]   # its exhausts
GUNS = [(214.0, 392.0), (522.0, 395.0)]       # its wingtips' guns
FIGHTER = [(231, 178), (262, 181), (276, 171), (289, 171), (301, 182), (339, 183), (335, 187), (304, 192),
           (300, 203), (291, 213), (281, 213), (273, 203), (264, 193), (236, 183)]
REMOVE = [  # what the painting loses: the player and its flames, the fighters, the blast, the lasers and the sight
    PLAYER, [(344, 298), (400, 298), (400, 342), (344, 342)],
    [(276, 410), (344, 410), (338, 510), (284, 510)], [(396, 410), (464, 410), (458, 510), (404, 510)],
    FIGHTER, [(400, 205), (492, 205), (492, 246), (400, 246)], [(312, 218), (402, 218), (402, 280), (312, 280)],
    [(190, 226), (226, 226), (226, 244), (190, 244)], [(286, 238), (310, 238), (310, 260), (286, 260)],
    [(276, 296), (312, 296), (312, 344), (276, 344)], [(406, 234), (424, 234), (424, 256), (406, 256)],
    [(500, 272), (556, 272), (556, 314), (500, 314)], [(408, 250), (486, 250), (486, 326), (408, 326)],
]
CLOUD = (8, 330, 168, 500)   # a stretch of clean cloud (x0, y0, x1, y1) whose grain fills the holes


def _membrane(a, mask):
    """a (h x w x 3, float) with its masked pixels replaced by the smoothest surface through their edges: Laplace's
    equation, relaxed from a coarse grid to the full one."""
    import numpy as np
    from scipy import ndimage

    if a.shape[0] > 24 and a.shape[1] > 24:
        small = _membrane(a[::2, ::2].copy(), mask[::2, ::2].copy())
        guess = np.repeat(np.repeat(small, 2, axis=0), 2, axis=1)[:a.shape[0], :a.shape[1]]
        a = np.where(mask[..., None], guess, a)
    else:
        a = np.where(mask[..., None], a[~mask].mean(axis=0), a)
    kernel = np.array([[0, 0.25, 0], [0.25, 0, 0.25], [0, 0.25, 0]])
    for _ in range(80):
        smooth = np.stack([ndimage.convolve(a[..., k], kernel, mode="nearest") for k in range(3)], axis=-1)
        a = np.where(mask[..., None], smooth, a)
    return a


def plate(painting):
    """The painting with what moves taken out: the sky, the clouds and the islands, for the game's background."""
    import numpy as np
    from scipy import ndimage

    img = painting.convert("RGB")
    mask_img = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask_img)
    for poly in REMOVE:
        md.polygon(poly, fill=255)
    mask_img = mask_img.filter(ImageFilter.MaxFilter(7))
    mask = np.asarray(mask_img) > 0
    a = np.asarray(img).astype(np.float64)
    filled = _membrane(a.copy(), mask)
    # The clouds' grain over the smooth fill: the fine detail of a clean stretch of cloud, tiled across the holes (finer
    # higher up, where the clouds are further away).
    detail = a - np.stack([ndimage.gaussian_filter(a[..., k], 3.0) for k in range(3)], axis=-1)
    x0, y0, x1, y1 = CLOUD
    patch = detail[y0:y1, x0:x1]
    far = np.asarray(Image.fromarray(np.clip(patch + 128, 0, 255).astype(np.uint8)).resize(
        (patch.shape[1] // 2, patch.shape[0] // 2), Image.LANCZOS)).astype(np.float64) - 128
    ys, xs = np.nonzero(mask)
    near = ys >= 330
    grain = np.zeros_like(a)
    grain[ys[near], xs[near]] = patch[(ys[near] - 330) % patch.shape[0], xs[near] % patch.shape[1]]
    grain[ys[~near], xs[~near]] = 0.5 * far[ys[~near] % far.shape[0], xs[~near] % far.shape[1]]
    filled = np.where(mask[..., None], filled + grain * 0.85, a)
    soft = np.asarray(mask_img.filter(ImageFilter.GaussianBlur(2.0))).astype(np.float64)[..., None] / 255.0
    out = a * (1 - soft) + filled * soft
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def cutout(painting, outline, pad=4):
    """A part of the painting along its outline, on a clear ground, cropped to it; its edge a pixel soft."""
    mask = Image.new("L", painting.size, 0)
    ImageDraw.Draw(mask).polygon(outline, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.7))
    part = painting.convert("RGBA")
    part.putalpha(mask)
    xs, ys = [p[0] for p in outline], [p[1] for p in outline]
    box = (int(min(xs)) - pad, int(min(ys)) - pad, int(max(xs)) + pad + 1, int(max(ys)) + pad + 1)
    return part.crop(box), box


_PUFFS = {}


def puff(r):
    """A soft round puff of radius r: its alpha falling from full at its middle to nothing at its edge."""
    r = max(2, int(round(r)))
    if r not in _PUFFS:
        import numpy as np
        y, x = np.mgrid[-r:r + 1, -r:r + 1]
        d = np.sqrt(x * x + y * y) / r
        _PUFFS[r] = Image.fromarray((np.clip(1 - d * d, 0, 1) ** 1.6 * 255).astype(np.uint8))
    return _PUFFS[r]


def over_at(img, sprite, x, y):
    """sprite composited onto img with its top left at (x, y), cropped to img."""
    x, y = round(x), round(y)
    left, top = max(0, -x), max(0, -y)
    right, bottom = min(sprite.width, img.width - x), min(sprite.height, img.height - y)
    if right > left and bottom > top:
        img.alpha_composite(sprite.crop((left, top, right, bottom)), (x + left, y + top))


def glow_at(img, x, y, r, colour, alpha):
    """A soft glow of colour, radius r, at (x, y), alpha (0 to 1) at its middle."""
    mask = puff(r)
    if alpha < 1:
        mask = mask.point(lambda v: round(v * max(0.0, alpha)))
    sprite = Image.new("RGBA", mask.size, tuple(colour) + (0,))
    sprite.putalpha(mask)
    over_at(img, sprite, x - mask.width / 2, y - mask.height / 2)


class Sky:
    """Skylance's flight, drawn at 2x: the filled-in painting as the far scene, the camera drifting closer and swaying
    with the player; clouds rushing past; the player's ship banking with the nub, its exhausts flickering; two fighters
    weaving ahead; green bolts from its wingtips when CROSS is pressed; the fighters blown up; the score."""

    def __init__(self, game):
        painting = Image.open(game.painting).convert("RGB")
        self.size = painting.size
        self.plate = plate(painting)
        self.player, self.player_box = cutout(painting, PLAYER)
        self.fighter, _ = cutout(painting, FIGHTER)
        rng = random.Random(4215)
        self.wisps = [(rng.uniform(-1.0, 1.0), rng.uniform(-0.25, 0.65), rng.uniform(0.0, 1.0), rng.uniform(0.7, 1.3))
                      for _ in range(16)]

    # The camera: a 16:9 window of the painting, drifting closer through the game, swaying against the player.
    def background(self, s, steer):
        pw, ph = self.size
        zoom = 1.12 + 0.12 * s
        width = pw / zoom
        height = width * H2 / W2
        cx = pw / 2 - steer[0] * 18 / zoom
        cy = ph * 0.47 - steer[1] * 8 / zoom
        box = (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
        img = self.plate.transform((W2, H2), Image.EXTENT, box, Image.BICUBIC)
        roll = -steer[0] * 2.4
        if abs(roll) > 0.01:
            m = 40
            big = self.plate.transform((W2 + 2 * m, H2 + 2 * m), Image.EXTENT,
                                       (box[0] - m * width / W2, box[1] - m * height / H2,
                                        box[2] + m * width / W2, box[3] + m * height / H2), Image.BICUBIC)
            img = big.rotate(roll, resample=Image.BICUBIC).crop((m, m, m + W2, m + H2))
        return img.convert("RGBA")

    def clouds(self, img, frame):
        """Thin cloud rushing out from the horizon past the camera."""
        layer = Image.new("L", (W2 // 4, H2 // 4), 0)
        d = ImageDraw.Draw(layer)
        vx, vy = W2 / 8, H2 * 0.36 / 4
        for k, (dx, dy, offset, size) in enumerate(self.wisps):
            life = ((frame / 26.0) + offset) % 1.0
            reach = life ** 2.2
            x = vx + dx * reach * W2 / 4 * 0.9
            y = vy + (0.2 + dy) * reach * H2 / 4 * 1.4
            r = (4 + 70 * reach) * size
            alpha = round(115 * math.sin(math.pi * life) ** 1.5)
            d.ellipse([x - r * 1.8, y - r * 0.55, x + r * 1.8, y + r * 0.55], fill=alpha)
        mist = layer.filter(ImageFilter.GaussianBlur(5)).resize((W2, H2), Image.BICUBIC)
        img.alpha_composite(Image.merge("RGBA", (Image.new("L", (W2, H2), 248), Image.new("L", (W2, H2), 250),
                                                 Image.new("L", (W2, H2), 255), mist)))

    def placed(self, sprite, x, y, scale, degrees=0.0):
        part = sprite.resize((max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))), Image.LANCZOS)
        if degrees:
            part = part.rotate(degrees, resample=Image.BICUBIC, expand=True)
        return part, (round(x - part.width / 2), round(y - part.height / 2))

    def ship_at(self, steer):
        """Where the player's ship is: its middle (x, y), its scale and its bank."""
        scale = W2 * 0.47 / PLAYER_SPAN
        return W2 / 2 + steer[0] * 120, H2 - 132 - steer[1] * 18, scale, -steer[0] * 11.0

    def to_screen(self, point, steer):
        """A point of the ship in the painting's pixels to the screen, as the ship is placed."""
        x, y, scale, bank = self.ship_at(steer)
        bx0, by0, bx1, by1 = self.player_box
        px, py = (point[0] - (bx0 + bx1) / 2) * scale, (point[1] - (by0 + by1) / 2) * scale
        a = math.radians(-bank)
        return x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a)

    def exhaust(self, img, steer, frame):
        layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for k, nozzle in enumerate(NOZZLES):
            x, y = self.to_screen(nozzle, steer)
            flicker = 1 + 0.18 * math.sin(frame * 2.7 + k * 1.9) + 0.1 * math.sin(frame * 5.3 + k)
            length = 70 * flicker
            d.ellipse([x - 24, y - 10, x + 24, y + length], fill=(255, 150, 50, 150))
            d.ellipse([x - 15, y - 8, x + 15, y + length * 0.6], fill=(255, 220, 140, 220))
            d.ellipse([x - 8, y - 6, x + 8, y + length * 0.3], fill=(255, 255, 235, 255))
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(6)))

    def frame(self, f):
        """The game at clip frame f (within L.PLAY): (the picture, 480 x 272)."""
        s = (f - L.PLAY[0]) / (L.PLAY[1] - L.PLAY[0])
        steer = L.steer(f)
        img = self.background(s, steer)
        self.clouds(img, f)
        self.fighters(img, f)
        self.bolts(img, f, steer)
        self.exhaust(img, steer, f)
        x, y, scale, bank = self.ship_at(steer)
        part, at = self.placed(self.player, x, y, scale, bank)
        over_at(img, part, *at)
        self.hud(img, f)
        return half(img)

    # The fighters: each weaves in from a side, growing as it nears, until the bolts reach it.
    FLIGHTS = [  # (first frame, hit frame, from (x, y), to (x, y)) at 2x
        (L.PLAY[0], L.HITS[0], (820, 120), (560, 210)),
        (L.HITS[0] + 2, L.HITS[1], (150, 110), (400, 200)),
    ]

    def fighter_at(self, k, f):
        f0, hit, (x0, y0), (x1, y1) = self.FLIGHTS[k]
        t = (f - f0) / (hit - f0)
        e = 1 - (1 - t) ** 2
        x = x0 + (x1 - x0) * e + 26 * math.sin(t * 7.0 + k)
        y = y0 + (y1 - y0) * e + 12 * math.sin(t * 9.0 + 1 + k)
        return x, y, 0.75 + 0.5 * t, 14 * math.sin(t * 6.0 + k)

    def fighters(self, img, f):
        for k, (f0, hit, _, _) in enumerate(self.FLIGHTS):
            if f0 <= f < hit:
                x, y, scale, bank = self.fighter_at(k, f)
                part, at = self.placed(self.fighter, x, y, scale, bank)
                over_at(img, part, *at)
                # The sight, locked on.
                sight = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
                d = ImageDraw.Draw(sight)
                r = 46
                d.ellipse([x - r, y - r, x + r, y + r], outline=(150, 255, 170, 190), width=3)
                for a in range(0, 360, 90):
                    c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
                    d.line([(x + c * (r - 10), y + s_ * (r - 10)), (x + c * (r + 10), y + s_ * (r + 10))],
                           fill=(150, 255, 170, 220), width=4)
                img.alpha_composite(sight)
            elif hit <= f < hit + 16:
                x, y, _, _ = self.fighter_at(k, hit - 0.01)
                self.blast(img, x, y, (f - hit) / 16, k)

    def blast(self, img, x, y, t, seed):
        """A fighter blown up, t from 0 to 1: a white-hot flash, fireballs swelling, reddening and drifting apart into
        smoke, a ring of shock and sparks flying out."""
        rng = random.Random(seed)
        grow = 1 - (1 - t) ** 2.2
        for k in range(4):                                   # the smoke, behind the fire
            a = rng.uniform(0, 2 * math.pi)
            if t > 0.25:
                glow_at(img, x + 50 * grow * math.cos(a), y + 40 * grow * math.sin(a) - 30 * t, 40 + 60 * grow,
                        (96, 92, 96), 0.55 * math.sin(math.pi * (t - 0.25) / 0.75))
        for k in range(7):                                   # the fireballs
            a = rng.uniform(0, 2 * math.pi)
            off = rng.uniform(0.2, 0.6) * 80 * grow
            heat = max(0.0, 1 - 1.5 * t + rng.uniform(-0.1, 0.1))
            colour = (255, round(90 + 140 * heat), round(30 + 120 * heat ** 2))
            glow_at(img, x + off * math.cos(a), y + off * math.sin(a) - 20 * t, (26 + rng.uniform(16, 36)) * (0.6 + grow),
                    colour, 0.95 * (1 - t ** 1.4))
        if t < 0.35:                                         # the flash
            glow_at(img, x, y, 50 + 70 * t / 0.35, (255, 252, 230), 1 - t / 0.35)
        ring = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        d = ImageDraw.Draw(ring)
        rr = 30 + 190 * grow
        d.ellipse([x - rr, y - rr * 0.75, x + rr, y + rr * 0.75], outline=(255, 236, 200, round(120 * (1 - t))), width=3)
        for _ in range(16):
            a = rng.uniform(0, 2 * math.pi)
            dist = 30 + rng.uniform(70, 190) * grow
            px, py = x + dist * math.cos(a), y + dist * math.sin(a) + 50 * t * t
            d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(255, 226, 150, round(255 * (1 - t))))
        img.alpha_composite(ring.filter(ImageFilter.GaussianBlur(1.5)))

    def bolts(self, img, f, steer):
        """CROSS fires a pair of bolts from the wingtips, which streak to the fighter in the sight in six frames."""
        halo = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        core = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        dh, dc = ImageDraw.Draw(halo), ImageDraw.Draw(core)
        for fire in L.FIRE:
            age = f - fire - 1
            if not 0 <= age < 7:
                continue
            target = next((self.fighter_at(k, min(fire + 6, hit - 0.5))[:2] for k, (f0, hit, _, _) in
                           enumerate(self.FLIGHTS) if f0 <= fire < hit), (W2 / 2, H2 * 0.32))
            for gun in GUNS:
                sx, sy = self.to_screen(gun, steer)
                t0 = min(1.0, age / 6)
                t1 = min(1.0, t0 + 0.28)
                p0 = (sx + (target[0] - sx) * t0, sy + (target[1] - sy) * t0)
                p1 = (sx + (target[0] - sx) * t1, sy + (target[1] - sy) * t1)
                width = 9 - 6 * t0
                dh.line([p0, p1], fill=(80, 255, 110, 230), width=round(width * 2.2))
                dc.line([p0, p1], fill=(225, 255, 225, 255), width=max(2, round(width * 0.6)))
        img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(7)))
        img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(2.5)))
        img.alpha_composite(core)

    def hud(self, img, f):
        score = 12340 + 500 * sum(1 for hit in L.HITS if f >= hit)
        d = ImageDraw.Draw(img)
        d.text((28, 22), f"SCORE {score:06d}", font=font("arialbd.ttf", 30), fill=(255, 255, 255), stroke_width=3,
               stroke_fill=(8, 20, 50))
        d.text((W2 - 250, 22), "SHIELD", font=font("arialbd.ttf", 26), fill=(255, 255, 255), stroke_width=3,
               stroke_fill=(8, 20, 50))
        d.rounded_rectangle([W2 - 250, 62, W2 - 30, 78], 5, fill=(8, 20, 50), outline=(255, 255, 255), width=2)
        d.rounded_rectangle([W2 - 247, 65, W2 - 247 + 214 * 0.8, 75], 4, fill=(110, 230, 140))


def main(made_up_dir, out):
    os.makedirs(out, exist_ok=True)
    game = made_up(made_up_dir)
    for name, image in (("psp_print.png", print_atlas()), ("psp_media.png", media_atlas(game)),
                        ("psp_screen.png", still())):
        path = os.path.join(out, name)
        image.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
