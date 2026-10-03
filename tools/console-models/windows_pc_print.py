"""The Windows PC's printing, for the console theme's Windows model (windows_pc.py). windows_pc_layout.py has where
each of the tower's faces is in its atlas.

Writes two images into a folder:
- pc_print.png: the tower's printed faces. The front panel's hexagonal mesh over three fans with lit rings (cyan to
  blue to magenta to pink round each); the top's vent, power button and ports; and the inside behind the glass: the
  motherboard with its heatsinks, slots and grommets, the front fans' backs, the graphics card's and the power supply
  shroud's sides, and the cooler's fins, its plate, and its fans' faces.
- pc_screen.png: the monitor's desktop: an abstract bloom on deep blue (the model's own, not Windows' wallpaper), three
  icons, and a centred taskbar (Start, search, files, browser, store and a racing game, then the time and date).

The apps and the racing game, Odyssey Racer, are made up. Run it with the system Python (Pillow):

    python tools/console-models/windows_pc_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windows_pc_layout as L  # noqa: E402

SS = 2  # supersampling: each region is drawn this many times larger, then resampled
FONTS = "C:/Windows/Fonts/"

# The fans' lit rings, round the colour wheel (degrees, colour).
RING = [(0, (56, 217, 255)), (90, (78, 107, 255)), (180, (192, 70, 255)), (270, (255, 95, 192)), (360, (56, 217, 255))]


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


class Region:
    """A region drawn at w x h units (millimetres, or the screen's pixels), supersampled, then pasted into an image."""

    def __init__(self, rect, w, h, background):
        self.rect = rect
        self.img = Image.new("RGBA", (rect[2] * SS, rect[3] * SS), background)
        self.draw = ImageDraw.Draw(self.img)
        self.sx, self.sy = rect[2] * SS / w, rect[3] * SS / h

    def p(self, x, y):
        return (x * self.sx, y * self.sy)

    def box(self, x0, y0, x1, y1):
        return [x0 * self.sx, y0 * self.sy, x1 * self.sx, y1 * self.sy]

    def width(self, w):
        return max(1, round(w * self.sx))

    def rect_(self, x0, y0, x1, y1, fill, r=0.0, outline=None, width=0.0):
        extra = {"outline": outline, "width": self.width(width)} if outline else {}
        if r:
            self.draw.rounded_rectangle(self.box(x0, y0, x1, y1), radius=r * self.sx, fill=fill, **extra)
        else:
            self.draw.rectangle(self.box(x0, y0, x1, y1), fill=fill, **extra)

    def circle(self, x, y, r, fill=None, outline=None, width=0.0):
        extra = {"outline": outline, "width": self.width(width)} if outline else {}
        self.draw.ellipse(self.box(x - r, y - r, x + r, y + r), fill=fill, **extra)

    def poly(self, points, fill):
        self.draw.polygon([self.p(x, y) for x, y in points], fill=fill)

    def line(self, points, fill, width):
        self.draw.line([self.p(x, y) for x, y in points], fill=fill, width=self.width(width))

    def text(self, s, name, size, x, y, fill, anchor="mm"):
        f = ImageFont.truetype(FONTS + name, max(1, round(size * self.sx)))
        self.draw.text(self.p(x, y), s, font=f, fill=fill, anchor=anchor)

    def layer(self):
        return Image.new("RGBA", self.img.size, (0, 0, 0, 0))

    def over(self, layer):
        self.img.alpha_composite(layer)

    def paste(self, image):
        x, y, w, h = self.rect
        image.paste(self.img.convert("RGB").resize((w, h), Image.LANCZOS), (x, y))


def gradient(size, stops):
    """An RGBA image graded through (t, colour) stops, top to bottom."""
    w, h = size
    strip = Image.new("RGBA", (1, h))
    for i in range(h):
        t = i / max(1, h - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                strip.putpixel((0, i), mix(c0, c1, (t - t0) / max(1e-6, t1 - t0)) + (255,))
                break
    return strip.resize((w, h), Image.BILINEAR)


def ring_colour(degrees):
    for (a0, c0), (a1, c1) in zip(RING, RING[1:]):
        if a0 <= degrees <= a1:
            return mix(c0, c1, (degrees - a0) / (a1 - a0))
    return RING[0][1]


def lit_ring(reg, cx, cy, r_out, r_in, dim=1.0, turn=0.0):
    """A fan's LED ring: an annulus graded round the colour wheel, a paler inner edge, and a soft halo."""
    ring = reg.layer()
    d = ImageDraw.Draw(ring)
    box = reg.box(cx - r_out, cy - r_out, cx + r_out, cy + r_out)
    for a in range(0, 360, 2):
        d.pieslice(box, a, a + 3, fill=mix((0, 0, 0), ring_colour((a + turn) % 360), dim) + (255,))
    mask = Image.new("L", ring.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(box, fill=255)
    md.ellipse(reg.box(cx - r_in, cy - r_in, cx + r_in, cy + r_in), fill=0)
    ring.putalpha(mask)
    halo = ring.filter(ImageFilter.GaussianBlur(r_out * 0.18 * reg.sx))
    reg.over(halo)
    reg.over(halo)
    reg.over(ring)
    edge = reg.layer()
    ImageDraw.Draw(edge).ellipse(reg.box(cx - r_in - 1.6, cy - r_in - 1.6, cx + r_in + 1.6, cy + r_in + 1.6),
                                 outline=(255, 255, 255, round(150 * dim)), width=reg.width(1.4))
    reg.over(edge)


def blades(reg, cx, cy, r, hub, colour, count=9):
    """A fan's swept blades round its hub."""
    for k in range(count):
        a0 = 2 * math.pi * k / count
        lead = [(cx + (hub + (r - hub) * i / 8) * math.cos(a0 + 0.55 * i / 8),
                 cy + (hub + (r - hub) * i / 8) * math.sin(a0 + 0.55 * i / 8)) for i in range(9)]
        trail = [(cx + (hub + (r - hub) * i / 8) * math.cos(a0 + 0.97 + 0.12 * i / 8 - 0.42 * (1 - i / 8)),
                  cy + (hub + (r - hub) * i / 8) * math.sin(a0 + 0.97 + 0.12 * i / 8 - 0.42 * (1 - i / 8)))
                 for i in range(8, -1, -1)]
        reg.poly(lead + trail, colour)
        reg.line(lead, mix(colour, (140, 145, 155), 0.45), 0.8)
    reg.circle(cx, cy, hub, "#24262C", outline="#3A3D45", width=1.0)


# -- pc_print.png -------------------------------------------------------------------------------------------------------

def front(atlas):
    w, h = 236.0, 470.0
    reg = Region(L.FRONT, w, h, "#0A0B0D")
    cx = w / 2
    for k, y in enumerate((75.0, 210.0, 345.0)):        # the fans' centres, from the top (windows_pc.py: FRONT_FANS)
        reg.rect_(cx - 69, y - 69, cx + 69, y + 69, "#15161A", r=7)
        reg.circle(cx, y, 56, "#0E0F12")
        blades(reg, cx, y, 54, 18, (44, 46, 52))
        lit_ring(reg, cx, y, 64, 55, turn=40 * k)

    # The mesh: hexagonal holes in a dark lattice, between the panel's solid bands.
    lattice = Image.new("L", reg.img.size, 255)
    ld = ImageDraw.Draw(lattice)
    pitch, hole = 4.4, 1.85
    row, y = 0, 12.0
    while y < h - 10:
        x = 18.0 + (pitch / 2 if row % 2 else 0)
        while x < w - 16:
            ld.polygon([reg.p(x + hole * math.cos(math.radians(60 * k + 30)), y + hole * math.sin(math.radians(60 * k + 30)))
                        for k in range(6)], fill=0)
            x += pitch
        y += pitch * math.sqrt(3) / 2
        row += 1
    reg.img.paste((29, 30, 35, 255), mask=lattice)

    # The side bands with their chamfer lines, and the top and bottom rails.
    for x0, x1 in ((0, 17), (w - 17, w)):
        reg.rect_(x0, 0, x1, h, "#1A1B1F")
    reg.rect_(0, 0, w, 11, "#1A1B1F")
    reg.rect_(0, h - 11, w, h, "#1A1B1F")
    for x in (16.2, w - 16.2):
        reg.line([(x, 10), (x, h - 10)], "#34363D", 0.8)
    for x0, x1 in ((2.5, 12.0), (w - 2.5, w - 12.0)):
        reg.line([(x0, 26), (x1, 40), (x1, h - 40), (x0, h - 26)], "#2A2C32", 0.9)
    reg.line([(16, 10.6), (w - 16, 10.6)], "#34363D", 0.8)
    reg.line([(16, h - 10.6), (w - 16, h - 10.6)], "#34363D", 0.8)
    reg.paste(atlas)


def top(atlas):
    w, h = 230.0, 440.0
    reg = Region(L.TOP, w, h, "#1A1B1F")
    reg.rect_(18, 26, w - 18, 352, "#141518", r=6)
    row, y = 0, 32.0
    while y < 348:
        x = 24.0 + (2.5 if row % 2 else 0)
        while x < w - 22:
            reg.circle(x, y, 1.55, "#060607")
            x += 5.0
        y += 4.4
        row += 1
    # At the front: the power button with its light, reset, two USB-A ports, a USB-C port and the audio jack.
    reg.circle(w / 2, 404, 9.0, "#26282E", outline="#3A3D45", width=1.2)
    reg.circle(w / 2, 404, 2.0, "#E8F4FF")
    reg.circle(w / 2 + 22, 404, 3.2, "#26282E")
    for x in (48, 66):
        reg.rect_(x - 6.5, 400, x + 6.5, 408, "#08090A", r=0.6)
        reg.rect_(x - 5, 402.5, x + 5, 404.5, "#3C66C8")
    reg.rect_(162, 401, 176, 407, "#08090A", r=3)
    reg.circle(190, 404, 2.6, "#08090A")
    reg.paste(atlas)


def mobo(atlas):
    # x: millimetres from the back (tower y = 205 - x); y: from the top (tower z = 470 - y).
    w, h = 405.0, 440.0
    reg = Region(L.MOBO, w, h, "#1C1D21")
    reg.rect_(20, 15, 365, 300, "#101216", r=2)
    for k in range(26):                                  # traces
        y = 40 + k * 9.5
        reg.line([(60, y), (180 + (k * 37) % 120, y), (195 + (k * 37) % 120, y + 6)], "#151920", 0.7)
    reg.rect_(22, 18, 58, 170, "#24262B", r=2)           # the I/O cover
    reg.line([(26, 30), (54, 60)], "#34373E", 1.0)
    reg.rect_(60, 18, 240, 33, "#2A2C32", r=2)           # the VRM heatsinks
    for x in range(64, 238, 5):
        reg.line([(x, 20), (x, 31)], "#1B1C20", 0.9)
    reg.rect_(60, 34, 74, 160, "#2A2C32", r=2)
    for k, x in enumerate((345, 354, 366, 375)):         # the RAM slots
        reg.rect_(x - 2, 25, x + 2, 155, "#1A1B1E" if k % 2 else "#24262B")
    for y in (275, 300):                                 # PCIe slots under the card
        reg.rect_(70, y, 300, y + 4, "#2A2C31", r=1)
        reg.rect_(70, y, 76, y + 4, "#5A5E66")
    reg.rect_(270, 255, 350, 292, "#2A2C32", r=3)        # the chipset heatsink
    reg.line([(276, 286), (344, 262)], "#585C66", 1.0)
    reg.rect_(368, 150, 378, 230, "#2B2D33", r=1.5)      # the 24-pin connector
    for y0, y1 in ((40, 140), (160, 250), (310, 380)):   # cable grommets in the tray
        reg.rect_(385, y0, 399, y1, "#09090B", r=4)
    reg.rect_(5, 330, 395, 440, "#18191C")               # behind the shroud
    reg.paste(atlas)


def inner_front(atlas):
    # x: millimetres from the board's side (tower x = 95 - x); y: from the top (tower z = 470 - y).
    w, h = 210.0, 440.0
    reg = Region(L.INNER_FRONT, w, h, "#121316")
    for k, y in enumerate((65.0, 200.0, 335.0)):
        reg.rect_(95 - 69, y - 69, 95 + 69, y + 69, "#17181C", r=7)
        reg.circle(95, y, 55, "#0D0E10")
        for a in (45, 135, 225, 315):                    # the motor's struts
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            reg.line([(95 + 20 * c, y + 20 * s), (95 + 56 * c, y + 56 * s)], "#1E2025", 3.0)
        reg.circle(95, y, 20, "#1E2025")
        lit_ring(reg, 95, y, 64, 56, dim=0.8, turn=40 * k)
    reg.paste(atlas)


def gpu(atlas):
    # x: millimetres from the card's back end (tower y = 135 - x); y: from its top (tower z = 262 - y).
    w, h = 325.0, 57.0
    reg = Region(L.GPU, w, h, "#16171B")
    reg.poly([(0, 0), (w, 0), (w, 9), (230, 9), (215, 15), (0, 15)], "#202227")
    reg.line([(4, 12), (212, 12), (228, 6), (w - 4, 6)], "#5B6070", 0.9)
    reg.rect_(18, 24, 300, 26.5, "#D8E6FF")              # the light bar
    reg.rect_(18, 26.5, 300, 28, "#7FA6FF")
    for x in range(10, 318, 6):                          # the fins' edges along the bottom
        reg.line([(x, 46), (x, 55)], "#2B2D33", 1.6)
    reg.line([(0, 56.3), (w, 56.3)], "#09090B", 1.4)
    reg.paste(atlas)


def shroud(atlas):
    # x: millimetres from the back (tower y = 205 - x); y: from the top (tower z = 135 - y).
    w, h = 405.0, 105.0
    reg = Region(L.SHROUD, w, h, "#222429")
    reg.line([(0, 1.2), (w, 1.2)], "#3A3D45", 1.4)
    reg.rect_(24, 22, 150, 84, "#1A1B1F", r=6)           # the window on the power supply
    reg.rect_(30, 28, 144, 78, "#0C0C0E", r=4)
    for k in range(9):                                   # the vent slots, at the front
        x = 250 + k * 15
        reg.rect_(x, 30, x + 7, 76, "#0E0F11", r=3.5)
    reg.line([(170, 90), (230, 90), (240, 80), (w - 10, 80)], "#30333A", 1.0)
    reg.paste(atlas)


def fins(atlas):
    w, h = 150.0, 270.0
    reg = Region(L.FINS, w, h, "#7D828A")
    for k in range(int(w / 2.2)):
        x = 2 + k * 2.2
        reg.line([(x, 0), (x, h)], "#4E5259", 0.6)
    for k in range(6):                                   # the heat pipes' ends, copper
        reg.circle(30 + k * 18, h / 2, 4.2, "#C27A3A", outline="#7E4A20", width=0.8)
    reg.paste(atlas)


def plate(atlas):
    reg = Region(L.PLATE, 14.0, 126.0, "#2A2C32")
    reg.line([(7, 8), (7, 118)], "#D8E6FF", 1.4)
    reg.line([(2, 0), (2, 126)], "#3A3D45", 0.6)
    reg.line([(12, 0), (12, 126)], "#16171A", 0.6)
    reg.paste(atlas)


def fan_face(atlas):
    reg = Region(L.FAN, 126.0, 126.0, "#18191C")
    reg.rect_(0, 0, 126, 126, "#16171B", r=8)
    for x, y in ((8, 8), (118, 8), (8, 118), (118, 118)):
        reg.circle(x, y, 2.6, "#08090A")
    reg.circle(63, 63, 51, "#0F1013")
    blades(reg, 63, 63, 50, 16, (62, 65, 74))
    lit_ring(reg, 63, 63, 60, 51.5)
    reg.paste(atlas)


def print_atlas(out):
    atlas = Image.new("RGB", (L.ATLAS, L.ATLAS), "#18191C")
    for draw in (front, top, mobo, inner_front, gpu, shroud, fins, plate, fan_face):
        draw(atlas)
    atlas.save(out, optimize=True)


# -- pc_screen.png ------------------------------------------------------------------------------------------------------

W, H = 1024, 576                    # the desktop's units: a 1024 x 576 screen
TASKBAR = 34
WHITE = (243, 243, 243)
GREY = (170, 170, 170)


def wallpaper(reg):
    """An abstract bloom on deep blue."""
    reg.img.paste(gradient(reg.img.size, [(0, (14, 34, 86)), (0.55, (8, 22, 62)), (1, (3, 8, 28))]))
    centre = (W * 0.5, H * 0.53)
    petals = reg.layer()
    for a, length, colour in ((-150, 330, (37, 99, 235)), (-120, 360, (59, 130, 246)), (-90, 380, (96, 165, 250)),
                              (-60, 360, (59, 130, 246)), (-30, 330, (37, 99, 235)), (-180, 260, (30, 64, 175)),
                              (0, 260, (30, 64, 175))):
        petal = reg.layer()
        pd = ImageDraw.Draw(petal)
        for i in range(10):
            t = i / 10
            l, wd = length * (1 - 0.6 * t), 120 * (1 - 0.55 * t)
            x0 = centre[0] + 10
            pd.ellipse(reg.box(x0, centre[1] - wd / 2, x0 + l, centre[1] + wd / 2),
                       fill=mix(colour, (190, 225, 255), t * 0.9) + (70,))
        petals.alpha_composite(petal.rotate(-a, resample=Image.BICUBIC, center=reg.p(*centre)))
    reg.over(petals.filter(ImageFilter.GaussianBlur(1.5 * reg.sx)))
    glow = reg.layer()
    ImageDraw.Draw(glow).ellipse(reg.box(centre[0] - 70, centre[1] - 50, centre[0] + 70, centre[1] + 50),
                                 fill=(200, 230, 255, 120))
    reg.over(glow.filter(ImageFilter.GaussianBlur(30 * reg.sx)))


def icon(reg, kind, x, y, s):
    """An app's icon, s units square, centred on (x, y)."""
    h = s / 2
    if kind == "start":
        g, q = s * 0.06, s * 0.36
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            x0, y0 = x + (g if dx > 0 else -g - q), y + (g if dy > 0 else -g - q)
            reg.rect_(x0, y0, x0 + q, y0 + q, (72, 160, 248) if dy < 0 else (40, 128, 232), r=q * 0.08)
    elif kind == "search":
        reg.circle(x - s * 0.08, y - s * 0.08, s * 0.24, outline=WHITE, width=s * 0.07)
        reg.line([(x + s * 0.1, y + s * 0.1), (x + s * 0.3, y + s * 0.3)], WHITE, s * 0.08)
    elif kind == "files":
        reg.rect_(x - h * 0.9, y - h * 0.62, x - h * 0.1, y - h * 0.3, (230, 160, 30), r=s * 0.05)
        reg.rect_(x - h * 0.9, y - h * 0.45, x + h * 0.9, y + h * 0.7, (247, 196, 66), r=s * 0.06)
    elif kind == "browser":
        reg.circle(x, y, h * 0.85, (24, 132, 214))
        reg.draw.arc(reg.box(x - h * 0.55, y - h * 0.55, x + h * 0.55, y + h * 0.55), 160, 430, fill=(120, 220, 160),
                     width=reg.width(s * 0.12))
    elif kind == "store":
        reg.draw.arc(reg.box(x - h * 0.35, y - h * 0.85, x + h * 0.35, y - h * 0.15), 180, 360, fill=WHITE,
                     width=reg.width(s * 0.06))
        reg.rect_(x - h * 0.8, y - h * 0.45, x + h * 0.8, y + h * 0.8, (42, 120, 214), r=s * 0.08)
        reg.rect_(x - h * 0.3, y - h * 0.05, x + h * 0.3, y + h * 0.45, WHITE, r=s * 0.03)
    elif kind == "racer":
        reg.rect_(x - h * 0.9, y - h * 0.9, x + h * 0.9, y + h * 0.9, (210, 36, 36), r=s * 0.18)
        q = s * 0.16
        for i in range(4):
            for j in range(3):
                reg.rect_(x - 2 * q + i * q, y - 1.5 * q + j * q, x - q + i * q, y - 0.5 * q + j * q,
                          WHITE if (i + j) % 2 == 0 else (30, 30, 30))


def screen_image(out):
    image = Image.new("RGB", L.SCREEN_PX)
    reg = Region((0, 0) + L.SCREEN_PX, W, H, "#000000")
    wallpaper(reg)

    for k, (kind, name) in enumerate((("files", "Files"), ("racer", "Odyssey Racer"), ("browser", "Browser"))):
        y = 34 + k * 66
        icon(reg, kind, 36, y, 30)
        reg.text(name, "segoeui.ttf", 8.5, 36.6, y + 24.6, (0, 0, 0))
        reg.text(name, "segoeui.ttf", 8.5, 36, y + 24, WHITE)

    # The taskbar: its icons centred, the weather left, the network, sound, time and date right.
    bar = reg.layer()
    ImageDraw.Draw(bar).rectangle(reg.box(0, H - TASKBAR, W, H), fill=(28, 30, 38, 225))
    reg.over(bar)
    reg.line([(0, H - TASKBAR + 0.3), (W, H - TASKBAR + 0.3)], (60, 64, 76), 0.6)
    kinds = ("start", "search", "files", "browser", "store", "racer")
    for i, kind in enumerate(kinds):
        x, y = W / 2 + (i - (len(kinds) - 1) / 2) * 38, H - TASKBAR / 2
        if kind in ("files", "browser"):
            reg.rect_(x - 3, y + 13, x + 3, y + 14.6, (150, 150, 160), r=0.8)   # running
        icon(reg, kind, x, y, 20)
    reg.text("18\u00b0C", "segoeuib.ttf", 8, 30, H - 23, WHITE)
    reg.text("Cloudy", "segoeui.ttf", 7.5, 30, H - 11, GREY)
    for k in range(3):
        reg.rect_(W - 108 + k * 4, H - 12 - k * 3, W - 106 + k * 4, H - 10, WHITE)
    reg.poly([(W - 88, H - 20), (W - 84, H - 20), (W - 79, H - 24), (W - 79, H - 10), (W - 84, H - 14), (W - 88, H - 14)],
             WHITE)
    reg.text("16:45", "segoeui.ttf", 8.5, W - 40, H - 23, WHITE)
    reg.text("03/10/2026", "segoeui.ttf", 8.5, W - 40, H - 11, WHITE)
    reg.paste(image)
    image.save(out, optimize=True)


if __name__ == "__main__":
    folder = os.path.abspath(sys.argv[1])
    os.makedirs(folder, exist_ok=True)
    print_atlas(os.path.join(folder, "pc_print.png"))
    screen_image(os.path.join(folder, "pc_screen.png"))
