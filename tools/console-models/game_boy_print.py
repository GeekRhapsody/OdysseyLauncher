"""The Game Boys' printing, for the console theme's models (tools/console-models/game_boy.py).

Draws each handheld's print atlas, its regions as game_boy_layout.py places them, each in millimetres as the model's
planar UVs map it: the front (the body's colour, the screen's surround, the switched-off screen, the power light, the
legends, the buttons' wells and the speaker), the cartridge's label side (a made-up game, Odyssey, drawn as pixel art)
and its other side, the screen switched on (the DMG's: its Nintendo logo, pixel by pixel, on the switched-off screen),
and the power light lit. Run it with the system Python (Pillow):

    python tools/console-models/game_boy_print.py <out folder>

It writes gb_print.png, gbc_print.png and gba_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_boy_layout as L  # noqa: E402
from game_gear_print import rounded_polygon  # noqa: E402

SCALE = 16  # pixels per millimetre while drawing; each region is resampled to its size in the atlas
FONTS = "C:/Windows/Fonts/"

NAVY = "#2B2D86"
LED_LIT = {"gb": "#FF3B30", "gbc": "#FF3346", "gba": "#53FF73"}
LED_OFF = {"gb": "#3B2024", "gbc": "#3A2026", "gba": "#2E3A33"}


def rgb(hex_colour, scale=1.0):
    """A #RRGGBB colour as an (r, g, b, 255) tuple, each channel times scale (darker below 1)."""
    return tuple(max(0, min(255, round(int(hex_colour[i:i + 2], 16) * scale))) for i in (1, 3, 5)) + (255,)


class Face:
    """One region's canvas: x to the right and z up, in millimetres, over the region's box."""

    def __init__(self, mm, fill):
        self.x0, self.x1, self.z0, self.z1 = mm
        self.img = Image.new("RGBA", (round((self.x1 - self.x0) * SCALE), round((self.z1 - self.z0) * SCALE)), fill)
        self.draw = ImageDraw.Draw(self.img)

    def p(self, x, z):
        return ((x - self.x0) * SCALE, (self.z1 - z) * SCALE)

    def polygon(self, points, fill):
        self.draw.polygon([self.p(x, z) for x, z in points], fill=fill)

    def rounded(self, x0, x1, z0, z1, radii, fill):
        radii = radii if isinstance(radii, list) else [radii] * 4
        self.polygon(rounded_polygon([(x1, z0), (x1, z1), (x0, z1), (x0, z0)], radii, 16), fill)

    def circle(self, x, z, r, fill):
        cx, cy = self.p(x, z)
        self.draw.ellipse([cx - r * SCALE, cy - r * SCALE, cx + r * SCALE, cy + r * SCALE], fill=fill)

    def ring(self, x, z, r, width, fill):
        cx, cy = self.p(x, z)
        self.draw.ellipse([cx - r * SCALE, cy - r * SCALE, cx + r * SCALE, cy + r * SCALE], outline=fill,
                          width=max(1, round(width * SCALE)))

    def pill(self, x, z, length, width, degrees, fill):
        """A stadium length long and width wide, centred at (x, z), turned anticlockwise by degrees."""
        r = width / 2
        c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
        points = []
        for end, a0 in ((length / 2 - r, -90), (-(length / 2 - r), 90)):
            for k in range(13):
                a = math.radians(a0 + 180 * k / 12)
                u, v = end + r * math.cos(a), r * math.sin(a)
                points.append((x + u * c - v * s, z + u * s + v * c))
        self.polygon(points, fill)

    def line(self, x0, z0, x1, z1, width, fill):
        self.pill((x0 + x1) / 2, (z0 + z1) / 2, math.hypot(x1 - x0, z1 - z0) + width, width,
                  math.degrees(math.atan2(z1 - z0, x1 - x0)), fill)

    def text(self, s, font, cap_mm, x, z, fill, anchor="left", shear=0.0, degrees=0.0, stretch=1.0):
        """Text whose capitals are cap_mm high, its left edge (or centre, or right edge) at x and its middle at z.
        Returns its width in millimetres."""
        probe = ImageFont.truetype(FONTS + font, 200)
        left, top, right, bottom = probe.getbbox("H")
        size = max(1, int(200 * cap_mm * SCALE / (bottom - top)))
        face = ImageFont.truetype(FONTS + font, size)
        left, top, right, bottom = face.getbbox(s)
        pad = size
        layer = Image.new("RGBA", (right - left + 2 * pad, bottom - top + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((pad - left, pad - top), s, font=face, fill=fill)
        if stretch != 1.0:
            layer = layer.resize((int(layer.width * stretch), layer.height), Image.LANCZOS)
        if shear:
            layer = layer.transform(layer.size, Image.AFFINE, (1, shear, -shear * layer.height / 2, 0, 1, 0),
                                    resample=Image.BICUBIC)
        if degrees:
            layer = layer.rotate(degrees, resample=Image.BICUBIC, expand=True)
        layer = layer.crop(layer.getbbox())
        cx, cy = self.p(x, z)
        offset = {"left": 0, "centre": layer.width / 2, "right": layer.width}[anchor]
        self.img.alpha_composite(layer, (int(cx - offset), int(cy - layer.height / 2)))
        return layer.width / SCALE

    def paste(self, image, x0, x1, z0, z1, resample=Image.LANCZOS):
        """An image stretched over the box (x0..x1, z0..z1)."""
        a, b = self.p(x0, z1)
        c, d = self.p(x1, z0)
        layer = image.convert("RGBA").resize((round(c - a), round(d - b)), resample)
        self.img.alpha_composite(layer, (round(a), round(b)))

    def glow(self, x, z, r, colour):
        """A lit light: a bright dot with a soft halo."""
        base = rgb(colour)
        for k in range(10, 0, -1):
            rr = r * (1 + 0.06 * k)  # the halo stays inside the light's 5 mm face
            alpha = int(255 * (1 - k / 11) ** 2 * 0.6)
            self.circle(x, z, rr, base[:3] + (alpha,))
        self.circle(x, z, r, base)
        self.circle(x - r * 0.3, z + r * 0.3, r * 0.35, (255, 255, 255, 200))


def bezel_outline(m, grow=0.0):
    """The screen's surround, grown by grow on every side: a rounded rectangle, its bottom bowed by bulge if any."""
    b = m["bezel"]
    (x0, x1), (z0, z1), radii = b["x"], b["z"], b["radii"]
    x0, x1, z0, z1 = x0 - grow, x1 + grow, z0 - grow, z1 + grow
    if b.get("bulge"):
        return rounded_polygon([(0, z0 - b["bulge"]), (x1, z0), (x1, z1), (x0, z1), (x0, z0)],
                               [120.0, radii[0], radii[1], radii[2], radii[3]], 16)
    return rounded_polygon([(x1, z0), (x1, z1), (x0, z1), (x0, z0)], radii, 16)


def screen(face, m, shade):
    """The switched-off screen: its glass, with a darker rim."""
    (x0, x1), (z0, z1) = m["screen"]["x"], m["screen"]["z"]
    face.rounded(x0 - 0.6, x1 + 0.6, z0 - 0.6, z1 + 0.6, 0.8, rgb(m["screen"]["colour"], shade))
    face.rounded(x0, x1, z0, z1, 0.4, rgb(m["screen"]["colour"]))


def speaker_slots(face, centre, count, spacing, length, width, degrees, fill):
    x, z = centre
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    for i in range(count):
        offset = (i - (count - 1) / 2) * spacing
        face.pill(x + offset * s, z - offset * c, length, width, degrees, fill)


# ---- Fronts ----------------------------------------------------------------------------------------------------------

def front_gb(m):
    case = m["colours"]["case"]
    face = Face(m["regions"]["front"]["mm"], rgb(case))
    groove = rgb(case, 0.86)

    # The top's grooves, and OFF/ON by the power switch.
    for z in (141.2, 139.4):
        face.line(-46, z, 46, z, 0.35, groove)
    face.text("\u25C4OFF\u2022ON\u25BA", "arialbd.ttf", 1.3, -33.0, 144.2, rgb(case, 0.62), anchor="centre")

    # The surround, its stripes and DOT MATRIX WITH STEREO SOUND, the screen, the battery light.
    face.polygon(bezel_outline(m), rgb(m["bezel"]["colour"]))
    width = face.text("DOT MATRIX WITH STEREO SOUND", "arialbd.ttf", 1.25, 13.0, 133.0, "#D8D8E0", anchor="centre",
                      stretch=0.9)
    for z, colour in ((133.6, "#8E1F55"), (132.4, "#2F3184")):
        face.line(-34.5, z, 13.0 - width / 2 - 1.2, z, 0.5, colour)
        face.line(13.0 + width / 2 + 1.2, z, 34.5, z, 0.5, colour)
    screen(face, m, 0.86)
    x, z = m["led"]
    face.circle(x, z, 1.5, LED_OFF["gb"])
    face.text("BATTERY", "arialbd.ttf", 0.95, x, z - 4.0, "#C9C9D2", anchor="centre")

    # Nintendo GAME BOY(TM).
    width = face.text("Nintendo", "arialbi.ttf", 2.6, -37.0, 78.6, NAVY)
    width += face.text("GAME BOY", "ariblk.ttf", 4.2, -37.0 + width + 1.4, 79.0, NAVY, shear=0.22, stretch=0.95)
    face.text("TM", "arialbd.ttf", 0.9, -37.0 + width + 2.0, 77.4, NAVY)

    # The A and B legends, SELECT and START's wells and legends, the speaker.
    for name, x, z, r in m["buttons"]:
        face.circle(x, z, r + 0.5, rgb(case, 0.9))
        face.text(name, "ariblk.ttf", 2.1, x, z - r - 3.2, NAVY, anchor="centre", shear=0.2)
    length, width, degrees = m["pill"]
    for name, x, z in m["pills"]:
        face.pill(x, z, length + 1.2, width + 1.2, degrees, rgb(case, 0.88))
        a = math.radians(degrees)
        face.text(name, "arialbi.ttf", 1.45, x + 4.3 * math.sin(a), z - 4.3 * math.cos(a), NAVY, anchor="centre",
                  degrees=degrees)
    speaker_slots(face, (24.0, 18.5), 6, 4.0, 16.5, 2.1, 65.0, rgb(case, 0.42))
    return face


def front_gbc(m):
    case = m["colours"]["case"]
    face = Face(m["regions"]["front"]["mm"], rgb(case))
    shade = rgb(case, 0.74)

    # The lens: the screen, the power light, GAME BOY COLOR.
    face.polygon(bezel_outline(m), rgb(m["bezel"]["colour"]))
    screen(face, m, 0.7)
    x, z = m["led"]
    face.circle(x, z, 1.3, LED_OFF["gbc"])
    for k in range(3):
        cx, cy = face.p(x + 0.4, z)
        r = (2.4 + 0.9 * k) * SCALE
        face.draw.arc([cx - r, cy - r, cx + r, cy + r], -35, 35, fill="#8E8E98", width=max(1, int(0.3 * SCALE)))
    face.text("POWER", "arialbd.ttf", 1.0, x + 1.2, z - 3.9, "#9A9AA4", anchor="centre")
    width = face.text("GAME BOY", "ariblk.ttf", 3.3, -21.0, 76.6, "#ECECF2", shear=0.2, stretch=0.92)
    x = -21.0 + width + 1.6
    for letter, colour in zip("COLOR", ("#E8213A", "#9B3FD8", "#2DB84A", "#F4C21C", "#2F6CE0")):
        x += face.text(letter, "ariblk.ttf", 3.3, x, 76.6, colour, shear=0.2) + 0.15

    # Nintendo, in its racetrack below the lens.
    face.rounded(-10.0, 10.0, 61.6, 65.6, 2.0, shade)
    face.rounded(-9.6, 9.6, 62.0, 65.2, 1.6, rgb(case, 0.97))
    face.text("Nintendo", "arialbi.ttf", 2.0, 0.0, 63.6, shade, anchor="centre")

    # The wells round the D-pad, A and B and SELECT and START, their legends, the speaker's holes.
    x, z, _, _ = m["dpad"]
    face.circle(x, z, 11.6, rgb(case, 0.82))
    for name, x, z, r in m["buttons"]:
        face.circle(x, z, r + 1.2, rgb(case, 0.82))
        face.text(name, "ariblk.ttf", 1.7, x + r + 1.6, z - r - 0.6, shade, anchor="centre")
    length, width, degrees = m["pill"]
    for name, x, z in m["pills"]:
        face.pill(x, z, length + 1.6, width + 1.6, degrees, rgb(case, 0.82))
        face.text(name, "arialbd.ttf", 1.1, x, z - 3.6, shade, anchor="centre")
    cx, cz = 22.0, 18.0
    for row in range(-7, 8):
        for col in range(-7, 8):
            x = cx + col * 1.9 + (0.95 if row % 2 else 0)
            z = cz + row * 1.65
            if (x - cx) ** 2 + (z - cz) ** 2 <= 7.4 ** 2:
                face.circle(x, z, 0.55, rgb(case, 0.4))
    return face


def front_gba(m):
    case = m["colours"]["case"]
    face = Face(m["regions"]["front"]["mm"], rgb(case))
    shade = rgb(case, 0.72)

    # The wells round the D-pad and A and B (under the lens, which they meet).
    x, z, _, _ = m["dpad"]
    face.circle(x, z, 12.4, rgb(case, 0.86))
    for _, x, z, r in m["buttons"]:
        face.circle(x, z, r + 1.3, rgb(case, 0.86))

    # The lens: the screen and GAME BOY ADVANCE.
    face.polygon(bezel_outline(m), rgb(m["bezel"]["colour"]))
    screen(face, m, 0.75)
    width = face.text("GAME BOY", "ariblk.ttf", 2.5, -16.0, 24.6, "#E6E6EE", shear=0.2, stretch=0.95)
    face.text("ADVANCE", "arialbi.ttf", 2.5, -16.0 + width + 1.2, 24.6, "#E6E6EE", stretch=1.05)

    # Nintendo above it; the power light and POWER.
    face.rounded(-9.5, 9.5, 75.6, 79.6, 2.0, shade)
    face.rounded(-9.1, 9.1, 76.0, 79.2, 1.6, rgb(case))
    face.text("Nintendo", "arialbi.ttf", 1.9, 0.0, 77.6, shade, anchor="centre")
    x, z = m["led"]
    face.circle(x, z, 1.2, LED_OFF["gba"])
    face.text("POWER", "arialbd.ttf", 1.0, x, z - 3.4, shade, anchor="centre")

    # START and SELECT with their wells and legends, the speaker.
    for name, x, z in m["small_buttons"]:
        face.circle(x, z, 3.2, rgb(case, 0.86))
        face.text(name, "arialbd.ttf", 1.15, x - 4.2, z, shade, anchor="right")
    for i, length in enumerate((18.0, 18.0, 17.0, 15.5, 13.5, 11.0)):
        z = 22.0 - i * 2.7
        face.pill(46.0 + length / 2, z + 0.12 * length / 2, length, 1.3, 7.0, rgb(case, 0.42))
    return face


# ---- Cartridges ------------------------------------------------------------------------------------------------------

def pixel_scene(kind, size):
    """The label's picture as pixel art (size in label pixels), from Odyssey, a made-up game."""
    w, h = size
    img = Image.new("RGBA", size)
    d = ImageDraw.Draw(img)
    if kind == "gb":
        dark, mid, light, pale = "#0F380F", "#306230", "#8BAC0F", "#C4D88A"
        d.rectangle([0, 0, w, h], fill=pale)
        d.ellipse([w * 0.66, h * 0.12, w * 0.66 + 9, h * 0.12 + 9], fill=light)
        d.polygon([(0, h * 0.78), (w * 0.22, h * 0.42), (w * 0.42, h * 0.72), (w * 0.62, h * 0.36), (w, h * 0.8),
                   (w, h), (0, h)], fill=mid)
        d.polygon([(w * 0.62, h * 0.36), (w * 0.56, h * 0.47), (w * 0.68, h * 0.47)], fill=pale)
        d.rectangle([0, h * 0.86, w, h], fill=dark)
        rocket = [(w * 0.3, h * 0.12), (w * 0.34, h * 0.24), (w * 0.34, h * 0.42), (w * 0.26, h * 0.42),
                  (w * 0.26, h * 0.24)]
        d.polygon(rocket, fill=dark)
        d.rectangle([w * 0.28, h * 0.43, w * 0.32, h * 0.5], fill=light)
    elif kind == "gbc":
        for y in range(h):
            t = y / h
            r, g, b = (255 - 60 * t, 120 + 90 * t, 70 + 40 * t) if t < 0.6 else (40, 120, 200)
            d.line([(0, y), (w, y)], fill=(int(r), int(g), int(b)))
        d.ellipse([w * 0.38, h * 0.32, w * 0.62, h * 0.62], fill="#FFE45C")
        d.rectangle([0, h * 0.6, w, h], fill="#2A7BD0")
        for k in range(4):
            y = h * (0.66 + 0.07 * k)
            d.line([(w * (0.3 + 0.04 * k), y), (w * (0.7 - 0.04 * k), y)], fill="#FFE45C")
        d.polygon([(w * 0.08, h), (w * 0.14, h * 0.3), (w * 0.17, h * 0.3), (w * 0.15, h)], fill="#5A3A1E")
        for a in (-150, -110, -60, -20):
            x1 = w * 0.155 + 12 * math.cos(math.radians(a))
            y1 = h * 0.3 + 6 * math.sin(math.radians(a)) + 5
            d.line([(w * 0.155, h * 0.3), (x1, y1)], fill="#1F9A4A", width=2)
    else:
        for y in range(h):
            t = y / h
            d.line([(0, y), (w, y)], fill=(int(20 + 30 * t), int(16 + 20 * t), int(70 + 60 * t)))
        for x, y in ((5, 4), (14, 11), (30, 3), (44, 9), (52, 18), (8, 20), (24, 15), (60, 6), (38, 22), (3, 12)):
            if x < w and y < h:
                d.point((x, y), fill="#FFFFFF")
        cx, cy, r = w * 0.66, h * 0.55, h * 0.24
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#F08A3C")
        d.ellipse([cx - r * 0.7, cy - r * 0.9, cx + r * 0.4, cy - r * 0.2], fill="#F6B068")
        d.arc([cx - r * 1.9, cy - r * 0.45, cx + r * 1.9, cy + r * 0.45], 160, 380, fill="#E8E0FF", width=2)
        d.polygon([(w * 0.2, h * 0.7), (w * 0.3, h * 0.55), (w * 0.33, h * 0.6), (w * 0.24, h * 0.76)], fill="#DDE3F2")
        d.polygon([(w * 0.2, h * 0.7), (w * 0.24, h * 0.76), (w * 0.16, h * 0.82)], fill="#FF7A3C")
    return img


def label(face, kind, x0, x1, z0, z1):
    """The made-up game's label: a title band above its pixel-art picture, inside a thin white edge."""
    face.rounded(x0, x1, z0, z1, 0.8, "#F2F2F0")
    band = {"gb": "#2B2D86", "gbc": "#D8263A", "gba": "#1B1F4A"}[kind]
    top = z1 - (z1 - z0) * 0.26
    face.rounded(x0 + 0.8, x1 - 0.8, top, z1 - 0.8, 0.5, band)
    picture = pixel_scene(kind, (64, round(64 * (top - z0 - 1.2) / (x1 - x0 - 1.6))))
    face.paste(picture, x0 + 0.8, x1 - 0.8, z0 + 0.8, top - 0.4, Image.NEAREST)
    title = {"gb": "#F2F2F0", "gbc": "#FFE45C", "gba": "#FFFFFF"}[kind]
    cap = (z1 - top) * 0.36
    face.text("ODYSSEY", "ariblk.ttf", cap, (x0 + x1) / 2, (top + z1) / 2 + cap * 0.25, title, anchor="centre", shear=0.15)
    sub = {"gb": "THE LAUNCHER QUEST", "gbc": "COLOR ISLAND", "gba": "ADVANCE TO ORBIT"}[kind]
    face.text(sub, "arialbd.ttf", cap * 0.32, (x0 + x1) / 2, top + (z1 - top) * 0.17, title, anchor="centre")


def cart_label_side(m, kind):
    """The cartridge's label side, seen looking at it (game_boy.py mirrors it onto the model's +y face)."""
    colour = m["colours"]["cart"]
    face = Face(m["regions"]["cart"]["mm"], rgb(colour))
    c = m["cart"]
    half, height = c["width"] / 2, c["height"]
    light, dark = rgb(colour, 1.25 if colour != "#222226" else 1.9), rgb(colour, 0.72)
    if c["kind"] == "dmg":
        # Grip ridges along the top, Nintendo GAME BOY in the middle of them; the label below; the arrow.
        for k in range(9):
            z = height - 3.0 - k * 1.05
            face.line(-half + 2.5, z, half - 6.5, z, 0.32, dark)
        face.rounded(-17.0, 17.0, height - 9.8, height - 4.4, 0.8, rgb(colour))
        face.text("Nintendo GAME BOY", "arialbi.ttf", 2.0, 0.0, height - 7.1, light, anchor="centre")
        label(face, kind, -22.5, 22.5, 8.0, 48.5)
        face.polygon([(-2.6, 4.8), (2.6, 4.8), (0.0, 2.2)], dark)
    else:
        for k in range(4):
            z = height - 2.2 - k * 0.9
            face.line(-half + 9.0, z, half - 9.0, z, 0.3, dark)
        label(face, kind, -23.0, 23.0, 2.4, 28.4)
    return face


def cart_rear(m):
    """The cartridge's other side, towards the console's front: its screw, Nintendo and the arrow."""
    colour = m["colours"]["cart"]
    face = Face(m["regions"]["cart_rear"]["mm"], rgb(colour))
    c = m["cart"]
    half, height = c["width"] / 2, c["height"]
    light, dark = rgb(colour, 1.2 if colour != "#222226" else 1.8), rgb(colour, 0.7)
    screw_z = height * 0.55
    face.circle(0.0, screw_z, 2.3, dark)
    face.circle(0.0, screw_z, 1.6, rgb(colour, 0.85))
    face.line(-1.1, screw_z, 1.1, screw_z, 0.4, dark)
    face.line(0.0, screw_z - 1.1, 0.0, screw_z + 1.1, 0.4, dark)
    face.text("Nintendo", "arialbi.ttf", 2.4 if height > 40 else 1.8, 0.0, height * 0.82, light, anchor="centre")
    face.rounded(-half + 4.0, half - 4.0, 2.0, height * 0.3, 1.0, rgb(colour, 0.92))
    face.text("MADE FOR ODYSSEY", "arialbd.ttf", 1.0, 0.0, height * 0.16, light, anchor="centre")
    face.polygon([(-2.2, height * 0.38 + 2.2), (2.2, height * 0.38 + 2.2), (0.0, height * 0.38)], dark)
    return face


# ---- The switched-on screen and the lit light ------------------------------------------------------------------------

def lcd_text(face, s, font, cap_mm, x, z, fill, pixel_mm, threshold=110):
    """Text drawn as the screen's pixels: rendered small, thresholded, and scaled up without smoothing."""
    probe = Face((0, 1, 0, 1), (0, 0, 0, 0))
    width = probe.text(s, font, cap_mm, 0, 0, (0, 0, 0, 255))
    w, h = max(1, round(width / pixel_mm)), max(1, round(cap_mm * 1.6 / pixel_mm))
    layer = Face((0, width, -cap_mm * 0.8, cap_mm * 0.8), (0, 0, 0, 0))
    layer.text(s, font, cap_mm, 0, 0, (0, 0, 0, 255))
    small = layer.img.resize((w, h), Image.BOX)
    alpha = small.getchannel("A").point(lambda a: 255 if a > threshold else 0)
    block = Image.new("RGBA", (w, h), fill)
    block.putalpha(alpha)
    face.paste(block, x - width / 2, x + width / 2, z - cap_mm * 0.8, z + cap_mm * 0.8, Image.NEAREST)


def screen_on(m, kind):
    face = Face(m["regions"]["screen"]["mm"], (0, 0, 0, 255))
    if kind == "gb":
        # The DMG's start-up: the Nintendo logo on the switched-off screen, as its pixels show it.
        face.img.paste(rgb(m["screen"]["colour"]), (0, 0, face.img.width, face.img.height))
        lcd_text(face, "Nintendo", "arialbd.ttf", 2.6, -0.8, 0.0, "#2E3A1C", 0.29)
        lcd_text(face, "\u00AE", "arialbd.ttf", 1.4, 7.9, 1.4, "#2E3A1C", 0.29, threshold=80)
    elif kind == "gbc":
        face.img.paste((236, 240, 230, 255), (0, 0, face.img.width, face.img.height))
        for k, colour in enumerate(("#E8213A", "#F4C21C", "#2DB84A", "#2F6CE0", "#9B3FD8")):
            cx, cy = face.p(0.0, -2.0)
            r = (19.0 - k * 1.1) * SCALE
            face.draw.arc([cx - r, cy - r, cx + r, cy + r], 205, 335, fill=colour, width=int(1.0 * SCALE))
        face.text("GAME BOY", "ariblk.ttf", 5.0, 0.0, -2.0, "#1E2A8C", anchor="centre", shear=0.2, stretch=0.92)
        face.text("COLOR", "ariblk.ttf", 2.2, 0.0, -8.0, "#E8213A", anchor="centre", shear=0.2)
        face.text("Nintendo", "arialbi.ttf", 2.0, 0.0, -14.5, "#5A5A64", anchor="centre")
    else:
        face.img.paste((244, 245, 250, 255), (0, 0, face.img.width, face.img.height))
        face.text("GAME BOY", "ariblk.ttf", 6.0, 0.0, 3.0, "#1C2A8E", anchor="centre", shear=0.22, stretch=0.95)
        face.rounded(-10.0, 10.0, -9.8, -5.4, 2.2, "#7A7A86")
        face.rounded(-9.6, 9.6, -9.4, -5.8, 1.8, (244, 245, 250, 255))
        face.text("Nintendo", "arialbi.ttf", 2.2, 0.0, -7.6, "#7A7A86", anchor="centre")
        for x, z, r in ((-21.0, 10.0, 1.6), (22.0, 12.5, 1.2), (19.0, -10.0, 1.0), (-24.0, -8.0, 0.9)):
            face.polygon([(x, z + r * 2), (x + r * 0.4, z + r * 0.4), (x + r * 2, z), (x + r * 0.4, z - r * 0.4),
                          (x, z - r * 2), (x - r * 0.4, z - r * 0.4), (x - r * 2, z), (x - r * 0.4, z + r * 0.4)],
                         "#8FB4FF")
    return face


def led_lit(m, kind):
    """The power light lit, on whatever is round it (the surround, or the body)."""
    x, z = m["led"]
    (x0, x1), (z0, z1) = m["bezel"]["x"], m["bezel"]["z"]
    behind = m["bezel"]["colour"] if x0 < x < x1 and z0 < z < z1 else m["colours"]["case"]
    face = Face(m["regions"]["led"]["mm"], rgb(behind))
    face.glow(0.0, 0.0, 1.5 if kind == "gb" else 1.3, LED_LIT[kind])
    return face


FRONTS = {"gb": front_gb, "gbc": front_gbc, "gba": front_gba}


def atlas(kind):
    m = L.MODELS[kind]
    image = Image.new("RGBA", (L.ATLAS, L.ATLAS), rgb(m["colours"]["case"]))
    faces = {
        "front": FRONTS[kind](m),
        "cart": cart_label_side(m, kind),
        "cart_rear": cart_rear(m),
        "screen": screen_on(m, kind),
        "led": led_lit(m, kind),
    }
    for name, face in faces.items():
        # Each region bleeds 4 pixels into the gap round it, so filtering and mipmaps at its edges see its own colours.
        x, y, w, h = m["regions"][name]["px"]
        region = face.img.resize((w, h), Image.LANCZOS)
        image.paste(region.resize((w + 8, h + 8), Image.NEAREST), (x - 4, y - 4))
        image.paste(region, (x, y))
    return image.convert("RGB")


def main(out):
    os.makedirs(out, exist_ok=True)
    for kind in L.MODELS:
        path = os.path.join(out, f"{kind}_print.png")
        atlas(kind).save(path, optimize=True)
        print(f"{path}")


if __name__ == "__main__":
    main(sys.argv[1])
