"""The Vectrex's printing (vectrex_print.png) and its tube's still (vectrex_screen.png), for the console theme's model
(vectrex.py), and the tube's pictures, which its video (vectrex_video.py) draws with Face and beam().

vectrex_print.png is laid out as vectrex_layout.REGIONS says: the controller's face (MB's rings round the joystick and
the buttons, the red numbers, MB and VECTREX), the bay's back wall (the vents, the controller port, RESET and the volume
knob's legends), the cartridge's label (the grey grid, the title in its box) and the lid's strip (MB, the red dots,
VECTREX), and swatches. vectrex_screen.png is the tube's face at VIDEO_PX showing the power-on screen, VECTREX drawn in
lines over a sunrise of rays: the still of the model's `video` material, and the first and last frame of its video. The
video draws the game's overlay (its tinted bands, its yellow frame, the PLAYER ONE and TWO band, the title band) over
the tube, sliding in and out. Run it with the system Python (Pillow, numpy):

    python tools/console-models/vectrex_print.py <out folder>
"""

import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vectrex_layout as L  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
RED = (226, 52, 44)
BLUE = (70, 140, 236)
YELLOW = (255, 214, 64)
WHITE = (236, 238, 240)

# The overlay: its bands (top, bottom, in the tube's millimetres) and their colours.
TOP_BAND, BOTTOM_BAND = 26.0, 30.0
TINTS = dict(top=(236, 70, 170), middle=(90, 150, 255), bottom=(255, 150, 40))


def outlined(reg, text, font, x, y, size, colour, width, anchor="mm"):
    """Text drawn as its outline only, the way the Vectrex's logo is."""
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    stroke = max(1, round(width * reg.sx))
    mask = Image.new("L", reg.img.size, 0)
    md = ImageDraw.Draw(mask)
    md.text(reg.p(x, y), text, font=f, fill=255, anchor=anchor, stroke_width=stroke, stroke_fill=255)
    inner = Image.new("L", reg.img.size, 0)
    ImageDraw.Draw(inner).text(reg.p(x, y), text, font=f, fill=255, anchor=anchor)
    reg.img.paste(Image.new("RGBA", reg.img.size, colour + (255,)), (0, 0), ImageChops.subtract(mask, inner))


def dots(reg, x0, x1, y, r, colour, pitch=4.5):
    x = x0
    while x <= x1:
        reg.circle(x, y, r, colour)
        x += pitch


def mb(reg, x, y, size):
    """MB's logo, its left middle at (x, y): a red M and a blue B."""
    reg.text("M", "arialbd.ttf", size, x, y, RED, anchor="lm")
    f = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(size * reg.sx)))
    reg.text("B", "arialbd.ttf", size, x + f.getlength("M") / reg.sx * 0.92, y, BLUE, anchor="lm")


# ---- The tube's face -------------------------------------------------------------------------------------------------
# Its pictures are light added to the tube switched off: vector lines drawn as the beam draws them, a bright line in a
# soft glow (beam()), in the tube's own cold white, or in the overlay's colours while it's in place (Face).

GLOW = (190, 220, 255)       # the tube's own light
SHADES = (0.13, 0.3)         # how bright the overlay's tinted bands are over the tube switched off, and lit behind them


def beam(groups, size, width=0.9, blur=2.4):
    """Vector lines as the tube's light: groups of (lines, brightness 0 to 1), a line a list of (x, y) points in
    millimetres on the tube (one point a dot). Drawn at twice the size and scaled down, so a moving line doesn't crawl,
    with a soft glow round it. An array (h x w), 1 a line's full light, up to 1.75 where its glow adds to it."""
    ss = 2
    sx = size[0] / L.TUBE["size"][0]
    layer = Image.new("L", (size[0] * ss, size[1] * ss), 0)
    d = ImageDraw.Draw(layer)
    stroke, dot, k = max(1, round(width * sx)) * ss, 1.4 * ss, sx * ss
    for lines, brightness in groups:
        fill = round(255 * brightness)
        for points in lines:
            if len(points) == 1:
                (x, y), = points
                d.ellipse([x * k - dot, y * k - dot, x * k + dot, y * k + dot], fill=fill)
            else:
                d.line([(x * k, y * k) for x, y in points], fill=fill, width=stroke, joint="curve")
    line = layer.resize(size, Image.BOX)
    halo = line.filter(ImageFilter.GaussianBlur(blur * sx))
    return (np.asarray(line, np.float32) + 0.75 * np.asarray(halo, np.float32)) / 255


class Face:
    """The tube's face at a size: the tube switched off, and the overlay's layers (the light its tinted bands give the
    tube, the colours they give the beam's light, its printed ink)."""

    def __init__(self, size):
        self.dark = np.asarray(tube(size), np.float32)
        tint, colours, self.ink = overlay_layers(size)
        self.tint = np.asarray(tint, np.float32) / SHADES[1]
        self.colours = np.asarray(colours, np.float32)

    def picture(self, light=None, overlay=0.0, lit=1.0):
        """The face showing light (beam()'s, or none) in the tube's own white, with the overlay slid `overlay` of the
        way down into place over it (0, out, to 1): where it covers the tube, the light takes its colours and its bands
        glow as lit as the tube behind them is (lit, 0 to 1)."""
        above = round(self.dark.shape[0] * (1 - overlay))   # the overlay's rows still above the glass
        cover = self.dark.shape[0] - above                  # the glass's rows it covers, from the top
        image = self.dark.copy()
        colour = np.empty_like(image)
        colour[:] = GLOW
        if cover:
            image[:cover] += self.tint[above:] * (SHADES[0] + (SHADES[1] - SHADES[0]) * lit)
            colour[:cover] = self.colours[above:]
        if light is not None:
            image += light[..., None] * colour
        out = Image.fromarray(np.clip(image + 0.5, 0, 255).astype(np.uint8))
        if cover:
            out.paste(self.ink, (0, -above), self.ink)
        return corners(out)


def tube(size):
    """The dark tube: near black, a little lighter at its middle."""
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(0, w, 4):
            r = math.hypot((x - w / 2) / w, (y - h / 2) / h)
            v = round(22 - 14 * min(1.0, r * 1.6))
            d.line([(x, y), (x + 3, y)], fill=(v, v + 1, v + 3))
    return img


def letter_strokes(text, x0, y0, h, spacing=1.25):
    """Text in a vector font of straight strokes (the letters and digits the game needs), h high from (x0, y0)."""
    w = h * 0.62
    shapes = {
        "0": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]], "1": [[(0.5, 0), (0.5, 1)]],
        "2": [[(0, 0), (1, 0), (1, 0.5), (0, 0.5), (0, 1), (1, 1)]],
        "3": [[(0, 0), (1, 0), (1, 1), (0, 1)], [(0, 0.5), (1, 0.5)]],
        "5": [[(1, 0), (0, 0), (0, 0.5), (1, 0.5), (1, 1), (0, 1)]],
        "6": [[(1, 0), (0, 0), (0, 1), (1, 1), (1, 0.5), (0, 0.5)]],
        "O": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]],
        "D": [[(0, 0), (0.7, 0), (1, 0.3), (1, 0.7), (0.7, 1), (0, 1), (0, 0)]],
        "Y": [[(0, 0), (0.5, 0.5), (1, 0)], [(0.5, 0.5), (0.5, 1)]],
        "S": [[(1, 0), (0, 0), (0, 0.5), (1, 0.5), (1, 1), (0, 1)]],
        "E": [[(1, 0), (0, 0), (0, 1), (1, 1)], [(0, 0.5), (0.7, 0.5)]], "V": [[(0, 0), (0.5, 1), (1, 0)]],
        "C": [[(1, 0), (0, 0), (0, 1), (1, 1)]], "T": [[(0, 0), (1, 0)], [(0.5, 0), (0.5, 1)]],
        "R": [[(0, 1), (0, 0), (1, 0), (1, 0.5), (0, 0.5), (1, 1)]], "X": [[(0, 0), (1, 1)], [(1, 0), (0, 1)]],
    }
    lines = []
    x = x0
    for c in text:
        for stroke in shapes.get(c, []):
            lines.append([(x + px * w, y0 + py * h) for px, py in stroke])
        x += w * spacing
    return lines


def text_width(text, h, spacing=1.25):
    return h * 0.62 * (spacing * (len(text) - 1) + 1)


def logo(rise=1.0):
    """The power-on screen's lines: VECTREX over a sunrise of rays, `rise` of the way out (0 to 1)."""
    w, h = L.TUBE["size"]
    lines = letter_strokes("VECTREX", (w - text_width("VECTREX", 18.0)) / 2, 44.0, 18.0)
    for k in range(9):
        a = math.radians(20 + 140 * k / 8)
        lines.append([(w / 2 + r * math.cos(a), 132 - r * math.sin(a)) for r in (16.0, 16.0 + 28.0 * rise)])
    lines.append([(w / 2 - 52, 132), (w / 2 + 52, 132)])
    return lines


def overlay_layers(size):
    """The overlay: the light its tinted bands add to the tube lit behind them (SHADES[1]); the colour each part gives
    the beam's light through it (its bands, and the printed planet's); and its printed ink (the frame, the labels, the
    title box) over everything."""
    w, h = L.TUBE["size"]
    sx = size[0] / w
    tint, colours = Image.new("RGB", size), Image.new("RGB", size)
    d, dc = ImageDraw.Draw(tint), ImageDraw.Draw(colours)
    shade = SHADES[1]
    for name, (y0, y1), lighter in (("top", (0, TOP_BAND), 70), ("middle", (TOP_BAND, h - BOTTOM_BAND), 80),
                                    ("bottom", (h - BOTTOM_BAND, h), 80)):
        d.rectangle([0, y0 * sx, size[0], y1 * sx], fill=tuple(round(c * shade) for c in TINTS[name]))
        dc.rectangle([0, y0 * sx, size[0], y1 * sx], fill=tuple(min(255, c + lighter) for c in TINTS[name]))
    cx, cy, r = 112 * sx, 112 * sx, 20 * sx           # a ringed planet printed in the play area
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(round(c * shade * 1.1) for c in TINTS["bottom"]))
    dc.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(min(255, c + 80) for c in TINTS["bottom"]))
    ring = tuple(round(c * shade * 1.8) for c in (200, 170, 255))
    d.ellipse([cx - r * 1.75, cy - r * 0.34, cx + r * 1.75, cy + r * 0.34], outline=ring, width=max(1, round(0.9 * sx)))
    ink = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    line = max(1, round(0.9 * sx))
    d.rectangle([2 * sx, 2 * sx, size[0] - 2 * sx, size[1] - 2 * sx], outline=YELLOW + (255,),
                width=max(1, round(2.2 * sx)))
    for y in (TOP_BAND, h - BOTTOM_BAND):
        d.line([(2 * sx, y * sx), (size[0] - 2 * sx, y * sx)], fill=YELLOW + (255,), width=line)
    f = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(5.0 * sx)))
    d.text((8 * sx, 9 * sx), "PLAYER ONE", font=f, fill=YELLOW + (255,), anchor="lm")
    d.text((size[0] - 8 * sx, 9 * sx), "PLAYER TWO", font=f, fill=YELLOW + (255,), anchor="rm")
    bx0, by0, bx1, by1 = 22 * sx, (h - 24) * sx, (w - 22) * sx, (h - 8) * sx
    d.rectangle([bx0, by0, bx1, by1], fill=(18, 12, 30, 255), outline=YELLOW + (255,), width=line)
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(10.0 * sx)))
    d.text(((bx0 + bx1) / 2, (by0 + by1) / 2), "ODYSSEY", font=f, fill=YELLOW + (255,), anchor="mm",
           stroke_width=max(1, round(0.5 * sx)), stroke_fill=(120, 40, 20, 255))
    return tint, colours, ink


# ---- The controller, the bay, the cartridge, the strip ---------------------------------------------------------------

def pad():
    """The controller's face from above, its back edge at the top: x from its left end, y from its back edge."""
    pw, pd, _ = L.PAD["size"]
    reg = Region(L.REGIONS["pad"], pw, pd, (22, 22, 25))
    sx, sy = pw / 2 + L.STICK["at"][0], pd - L.STICK["at"][1]
    by = pd - L.BUTTONS["y"]
    xs = [pw / 2 + x for x in L.BUTTONS["x"]]
    reg.line([(sx + L.STICK["ring"] + 2.0, by), (xs[0] - L.BUTTONS["ring"], by)], WHITE, 0.9)
    for a, b in zip(xs, xs[1:]):
        reg.line([(a + L.BUTTONS["ring"], by), (b - L.BUTTONS["ring"], by)], WHITE, 0.9)
    reg.circle(sx, sy, L.STICK["ring"] + 2.0, outline=WHITE, width=0.9)
    for k, x in enumerate(xs):
        reg.circle(x, by, L.BUTTONS["ring"], outline=WHITE, width=0.9)
        reg.text(str(k + 1), "arialbd.ttf", 5.4, x, by + 15.0, RED)
    mb(reg, 6.0, 8.0, 6.0)
    dots(reg, 20.0, 128.0, 8.0, 0.45, RED)
    outlined(reg, "VECTREX", "bahnschrift.ttf", 168.0, 8.5, 9.0, BLUE, 0.35)
    reg.text("Made in Hong Kong", "arial.ttf", 2.2, 6.0, pd - 7.0, (120, 120, 126), anchor="lm")
    return reg


def bay():
    """The bay's back wall, from in front: x from its left (-105), y down from its top (z 87)."""
    (x0, x1), (z0, z1) = L.BAY["x"], L.BAY["z"]
    reg = Region(L.REGIONS["bay"], x1 - x0, z1 - z0, (26, 27, 30))

    def at(x, z):
        return x - x0, z1 - z

    for k in range(20):
        x = -70.0 + 6.0 * k
        reg.rect_(*at(x - 1.6, 76.0), *at(x + 1.6, 24.0), (8, 8, 10), r=0.8)
    px, pz = L.PORT["at"]
    pw, ph = L.PORT["size"]
    reg.poly([at(px - pw / 2, pz + ph / 2), at(px + pw / 2, pz + ph / 2), at(px + pw / 2 - 3, pz - ph / 2),
              at(px - pw / 2 + 3, pz - ph / 2)], (60, 62, 66))
    reg.poly([at(px - pw / 2 + 2, pz + ph / 2 - 2), at(px + pw / 2 - 2, pz + ph / 2 - 2),
              at(px + pw / 2 - 4.4, pz - ph / 2 + 2), at(px - pw / 2 + 4.4, pz - ph / 2 + 2)], (10, 10, 12))
    for row, n in ((2.0, 5), (-2.0, 4)):
        for k in range(n):
            x = px - (n - 1) * 2.4 + 4.8 * k
            reg.circle(*at(x, pz + row), 0.7, (170, 150, 90))
    reg.text("RESET", "arialbd.ttf", 2.4, *at(L.RESET["at"][0], L.RESET["at"][1] - 9.0), (170, 172, 176))
    reg.text("ON/OFF", "arialbd.ttf", 2.4, *at(L.VOLUME["at"][0], L.VOLUME["at"][1] - 10.0), (170, 172, 176))
    reg.text("VOLUME", "arialbd.ttf", 2.4, *at(L.VOLUME["at"][0], L.VOLUME["at"][1] - 13.5), (170, 172, 176))
    return reg


def cart():
    """The cartridge's top: its length across (its outer end at the right), its width down (its front at the bottom);
    the label on its outer end, its title running along its width."""
    length, width, lw = L.CART["length"], L.CART["width"], L.CART["label"]
    reg = Region(L.REGIONS["cart"], length, width, (24, 24, 26))
    label = Region((0, 0, round(width * 8), round(lw * 8)), width, lw, (24, 24, 26))
    label.rect_(2.0, 2.0, width - 2.0, lw - 2.0, (150, 152, 156), r=1.0)
    for k in range(int((width - 4) / 4.5) + 1):
        label.line([(2.0 + 4.5 * k, 2.0), (2.0 + 4.5 * k, lw - 2.0)], (215, 216, 218), 0.3)
    for k in range(int((lw - 4) / 4.5) + 1):
        label.line([(2.0, 2.0 + 4.5 * k), (width - 2.0, 2.0 + 4.5 * k)], (215, 216, 218), 0.3)
    outlined(label, "VECTREX", "bahnschrift.ttf", width / 2, 9.0, 6.5, (40, 40, 44), 0.3)
    label.rect_(6.0, 15.0, width - 6.0, 31.0, (255, 140, 30), r=3.0)
    label.rect_(7.4, 16.4, width - 7.4, 29.6, (230, 40, 30), r=2.4)
    label.rect_(8.6, 17.6, width - 8.6, 28.4, (12, 12, 14), r=2.0)
    label.text("ODYSSEY", "ariblk.ttf", 8.0, width / 2, 23.2, WHITE)
    mb(label, width - 20.0, lw - 7.0, 5.0)
    art = label.img.rotate(90, expand=True)
    x0, y0, x1, y1 = reg.box(length - lw - 1.0, 0.0, length - 1.0, width)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    return reg


def strip():
    """The lid's logo strip: MB, the red dots, VECTREX in the middle, the dots again."""
    (u0, u1), (v0, v1) = L.STRIP["u"], L.STRIP["v"]
    w, h = u1 - u0, v1 - v0
    reg = Region(L.REGIONS["strip"], w, h, (30, 31, 34))
    reg.rect_(0.0, 0.0, w, 0.6, (60, 61, 66))
    mb(reg, 8.0, h / 2, 7.0)
    dots(reg, 24.0, w / 2 - 30.0, h / 2, 0.5, RED, pitch=5.0)
    outlined(reg, "VECTREX", "bahnschrift.ttf", w / 2, h / 2, 10.0, BLUE, 0.35)
    dots(reg, w / 2 + 30.0, w - 8.0, h / 2, 0.5, RED, pitch=5.0)
    return reg


def corners(screen):
    """The tube's face is a rounded rectangle: outside its corners, the bezel round it."""
    w, h = L.TUBE["size"]
    sx = screen.width / w
    mask = Image.new("L", screen.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, screen.width - 1, screen.height - 1], radius=L.TUBE["r"] * sx,
                                           fill=255)
    out = Image.new("RGB", screen.size, rgb(L.COLOURS["bezel"]))
    out.paste(screen, (0, 0), mask)
    return out


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (pad(), bay(), cart(), strip()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(L.COLOURS[name]))
    still = Face(L.VIDEO_PX).picture(beam([(logo(), 1.0)], L.VIDEO_PX))
    for name, picture in (("vectrex_print.png", image), ("vectrex_screen.png", still)):
        path = os.path.join(out, name)
        picture.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1])
