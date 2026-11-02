"""The Windows card's printing, its screen's still and the screens of its video, for the console theme's Windows model
(windows_pc.py); its video (windows_pc_video.py) draws its frames with the screens here. windows_pc_layout.py has the
measurements, where each face is in its atlas, the screen's layout and the clip's timing.

Writes three images into a folder:
- windows_case.png: the tower's printing. Its front round the fans' opening, two light bars down its sides; its top's
  dust filter and the buttons and ports at its front; its back; and the inside seen through the open side: the
  motherboard (its I/O cover and heatsinks, its slots, the chipset's lit cover), the graphics card's long side (its lit
  strip) and its backplate, the shroud's side with its lit window, the cooler's fins, a memory stick's light bar; a
  fan's frame with its lit ring round the hole, and its rotor (the hub and the blades, lit); swatches.
- windows_desk.png: the keyboard from above (the keys' tops with their legends lit in a band of colour across it, the
  plate between them, a glow round each switch), the desk mat with its lit edge, the mouse's top, the monitor's chin
  and its housing's back; swatches.
- windows_screen.png: the glass, VIDEO_PX: the desktop, the `video` material's texture: the video's first frame.

The lights' colours run round the same wheel as the fans' rings (RING: cyan, blue, violet, pink), across the keyboard
and along the mat's edge. The screens are the desktop (an abstract bloom of the card's own, the icons, a centred
taskbar; no Microsoft mark or wordmark), and a made-up game, Wyrmspire (tools/made-up-games), remastered in HD: its
developer's splash, its title over new key art, its loading screen, its play (the valley painted by Codex, the hero and
the beast cut out of their poses on green, the HUD), its pause menu. Make the made-up games' library and the paintings
first (tools/made-up-games/README.md; paintings.py), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/windows_pc_print.py artifacts/made-up-games <out folder>
"""

import math
import os
import random
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


def hexrgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def swatches(image, places, colours):
    d = ImageDraw.Draw(image)
    for name, (x, y) in places.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=hexrgb(colours[name]))


def glow(reg, draw, blur, times=1):
    """Something drawn on a layer of its own (draw(layer's ImageDraw)), blurred into a glow, then laid over."""
    layer = reg.layer()
    draw(ImageDraw.Draw(layer))
    halo = layer.filter(ImageFilter.GaussianBlur(blur * reg.sx))
    for _ in range(times):
        reg.over(halo)
    reg.over(layer)


def light_bar(reg, x0, y0, x1, y1, turn=0.0, vertical=True):
    """A lit strip, its colour running round the wheel along it, with its glow."""
    def draw(d):
        n = 48
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            colour = ring_colour((turn + 300 * (t0 + t1) / 2) % 360) + (255,)
            if vertical:
                d.rectangle(reg.box(x0, y0 + (y1 - y0) * t0, x1, y0 + (y1 - y0) * t1), fill=colour)
            else:
                d.rectangle(reg.box(x0 + (x1 - x0) * t0, y0, x0 + (x1 - x0) * t1, y1), fill=colour)
    glow(reg, draw, max(x1 - x0, y1 - y0) * 0.02 + 1.5, 2)


def hex_mark(reg, x, y, r, colour, width=0.8):
    """The house mark: a hexagon's outline round a smaller filled one (made up)."""
    pts = [(x + r * math.cos(math.radians(30 + 60 * k)), y + r * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    reg.line(pts + [pts[0]], colour, width)
    reg.poly([(x + 0.45 * (px_ - x), y + 0.45 * (py_ - y)) for px_, py_ in pts], colour)


# -- windows_case.png --------------------------------------------------------------------------------------------------

T = L.TOWER
TW, TD, TH = T["width"], T["depth"], T["height"]


def case_region(atlas, name, w, h, colour):
    return Region(L.CASE_REGIONS[name], w, h, colour)


def front(atlas):
    """The front round the fans' opening, its light bars down the opening's sides, the mark at its foot."""
    reg = case_region(atlas, "front", TW, TH, "#16171A")
    reg.img.paste(gradient(reg.img.size, [(0, (30, 31, 36)), (1, (18, 19, 22))]))
    o = L.FRONT_OPENING
    m = o["margin"]
    reg.rect_(m, TH - o["z"][1], TW - m, TH - o["z"][0], "#08090A", r=3)
    for x in (m - 9.0, TW - m + 5.0):
        light_bar(reg, x, TH - o["z"][1] + 6, x + 4.0, TH - o["z"][0] - 6, turn=40.0)
    hex_mark(reg, TW / 2, TH - 12.0, 5.0, (150, 156, 168))
    reg.paste(atlas)


def top(atlas):
    """The top, its front edge at the bottom: the dust filter's fine mesh over the vents, then the buttons and ports."""
    reg = case_region(atlas, "top", TW, TD, "#18191C")
    reg.rect_(16, 22, TW - 16, TD - 62, "#0D0E10", r=6)
    for row in range(0, 160):
        y = 26 + row * 2.2
        if y > TD - 66:
            break
        for col in range(0, 110):
            x = 20 + col * 2.0 + (1.0 if row % 2 else 0.0)
            if x > TW - 20:
                break
            reg.circle(x, y, 0.62, "#222429")
    y = TD - 30
    reg.circle(42, y, 8.0, "#0B0B0D", outline="#5A5E66", width=0.8)
    glow(reg, lambda d: d.ellipse(reg.box(42 - 5.6, y - 5.6, 42 + 5.6, y + 5.6), outline=(130, 220, 255, 255),
                                  width=reg.width(0.9)), 1.2)
    reg.rect_(70, y - 2.0, 79, y + 2.0, "#050506", r=1.6)                         # USB-C
    for x in (94, 116):                                                           # USB-A
        reg.rect_(x, y - 3.0, x + 13, y + 3.0, "#050506", r=0.6)
        reg.rect_(x + 1.5, y - 1.2, x + 11.5, y + 0.4, "#2A6FD8")
    reg.circle(146, y, 2.8, "#050506", outline="#3A3D44", width=0.5)              # the headset's jack
    reg.rect_(162, y - 2.6, 172, y + 2.6, "#0B0B0D", r=1.0)                       # reset
    reg.paste(atlas)


def back(atlas):
    """The back, seen from behind: the exhaust fan's grille, the I/O, the slots' covers, the power supply."""
    reg = case_region(atlas, "back", TW, TH, "#141518")
    fx, fz = TW - L.REAR_FAN["x"], TH - L.REAR_FAN["z"]
    reg.circle(fx, fz, 60, "#0B0C0E")
    for k in range(1, 6):
        reg.circle(fx, fz, 60 - k * 10, outline="#26282D", width=1.2)
    bx0, bx1 = TW - L.BOARD["x"] + 4, TW - L.BOARD["x"] + 48
    reg.rect_(bx0, TH - L.BOARD["z"][1] + 4, bx1, TH - L.BOARD["z"][1] + 170, "#1F2126", r=1)
    for k in range(7):
        y = TH - L.BOARD["z"][1] + 190 + k * 20
        reg.rect_(bx0 - 6, y, TW - 26, y + 14, "#1C1E22", r=1)
        for s in range(10):
            reg.rect_(bx0 + 4 + s * 12, y + 4, bx0 + 9 + s * 12, y + 10, "#0A0B0C")
    reg.rect_(24, TH - 96, TW - 24, TH - 6, "#101113", r=2)
    reg.circle(80, TH - 51, 36, "#08090A")
    for k in range(1, 4):
        reg.circle(80, TH - 51, 36 - k * 9, outline="#24262B", width=1.0)
    reg.rect_(150, TH - 70, 186, TH - 46, "#050506", r=2)
    reg.paste(atlas)


def board(atlas):
    """The motherboard from the open side (from its back edge, at the left, to its front): the I/O cover and the
    heatsinks, the socket and the memory's slots (hidden), the slots, the chipset's lit cover, the connectors."""
    b = L.BOARD
    w, h = b["y"][1] - b["y"][0], b["z"][1] - b["z"][0]
    reg = case_region(atlas, "board", w, h, "#14161B")
    rng = random.Random(4)
    for _ in range(120):                                          # its traces, faint
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        reg.line([(x, y), (x + rng.uniform(-30, 30), y), (x + rng.uniform(-30, 30), y + rng.uniform(-20, 20))],
                 "#1C1F26", 0.35)
    reg.rect_(0, 0, 46, 132, "#202228", r=2)                      # the I/O cover, its lit edge
    light_bar(reg, 40, 8, 43, 124, turn=200.0)
    hex_mark(reg, 22, 66, 9.0, (190, 196, 206))
    reg.rect_(48, 3, 160, 32, "#2C2F36", r=2)                     # the top heatsink
    for k in range(12):
        reg.rect_(52 + k * 9, 6, 56 + k * 9, 29, "#3C4049")
    socket_a, socket_b = b["y"][1] - 330, b["z"][1] - 370
    reg.rect_(socket_a - 24, socket_b - 24, socket_a + 24, socket_b + 24, "#2A2C31", r=2)
    reg.rect_(b["y"][1] - 262, 4, b["y"][1] - 226, 142, "#0E0F12")   # the memory's slots
    for y in (178, 224):                                          # the slots
        reg.rect_(18, y, 236, y + 6, "#08090B", r=1)
    reg.rect_(60, 196, 214, 214, "#2C2F36", r=2)                  # an M.2 drive's heatsink
    reg.rect_(206, 150, 296, 236, "#25272D", r=3)                 # the chipset's cover
    light_bar(reg, 212, 228, 290, 231, turn=120.0, vertical=False)
    reg.text("ODYSSEY", "segoeuib.ttf", 7.0, 251, 190, "#8C929E")
    reg.rect_(282, 36, 296, 116, "#0B0C0E", r=1)                  # the main power connector, and its cable
    reg.rect_(296, 40, w, 112, "#111214")
    for k in range(9):
        reg.circle(rng.uniform(150, 200), rng.uniform(150, 175), 2.6, "#3A3D44", outline="#55585F", width=0.4)
    reg.paste(atlas)


def gpu(atlas):
    """The graphics card's long side, from its bracket (left) to its far end: its shroud's facets, its lit strip, its
    name."""
    g = L.GPU
    w, h = g["y"][1] - g["y"][0], g["z"][1] - g["z"][0]
    reg = case_region(atlas, "gpu", w, h, "#1C1D21")
    reg.rect_(0, 0, 5, h, "#7A7E87")
    reg.poly([(10, 0), (w, 0), (w, 9), (40, 9)], "#24262B")
    reg.poly([(10, h), (w, h), (w, h - 9), (40, h - 9)], "#141518")
    light_bar(reg, 52, h / 2 - 2.2, w - 26, h / 2 + 2.2, turn=60.0, vertical=False)
    reg.text("AERIS", "bahnschrift.ttf", 6.5, w - 60, h / 2 + 12, "#9AA0AC")
    reg.paste(atlas)


def gpu_top(atlas):
    """The graphics card's backplate from above: brushed dark metal, a lit mark, the power cable."""
    g = L.GPU
    w, h = g["y"][1] - g["y"][0], g["x"][1] - g["x"][0]
    reg = case_region(atlas, "gpu_top", w, h, "#202227")
    rng = random.Random(9)
    for _ in range(220):
        y = rng.uniform(0, h)
        reg.line([(rng.uniform(0, w), y), (rng.uniform(0, w), y)], "#262930", 0.3)
    reg.rect_(4, 4, w - 4, h - 4, None, r=3, outline="#30333A", width=0.8)
    glow(reg, lambda d: hex_mark_on(d, reg, w * 0.62, h * 0.45, 12.0), 2.0, 2)
    reg.rect_(150, 6, 172, 20, "#0B0C0E", r=1)
    reg.line([(161, 6), (161, 0)], "#0B0C0E", 6.0)
    reg.paste(atlas)


def hex_mark_on(d, reg, x, y, r):
    pts = [(x + r * math.cos(math.radians(30 + 60 * k)), y + r * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    d.line([reg.p(*p) for p in pts + [pts[0]]], fill=(140, 220, 255, 255), width=reg.width(1.4))
    d.polygon([reg.p(x + 0.45 * (a - x), y + 0.45 * (b - y)) for a, b in pts], fill=(200, 150, 255, 255))


def shroud(atlas):
    """The shroud's side: black, its lit window with the mark, the vents near its front (at the right)."""
    w, h = TD - T["wall"] - L.SHROUD["y"], L.SHROUD["z"] - T["wall"]
    reg = case_region(atlas, "shroud", w, h, "#111215")
    reg.rect_(110, 26, 250, 70, "#0A0B0D", r=6)
    glow(reg, lambda d: d.rounded_rectangle(reg.box(114, 30, 246, 66), radius=5 * reg.sx,
                                            outline=(120, 210, 255, 255), width=reg.width(1.2)), 2.5, 2)
    hex_mark(reg, 180, 48, 10.0, (210, 220, 236))
    for k in range(10):
        reg.rect_(w - 70 + k * 6, 18, w - 66 + k * 6, h - 18, "#08090A", r=1)
    reg.paste(atlas)


def fins(atlas):
    """The cooler's fins' edges, seen from the open side: many thin fins, the cap over them with its lit line."""
    c = L.COOLER
    w, h = c["y"][1] - c["y"][0], c["z"][1] - c["z"][0]
    reg = case_region(atlas, "fins", w, h, "#3C4048")
    y = 8.0
    while y < h:
        reg.rect_(0, y, w, y + 0.9, "#9AA0AA")
        reg.rect_(0, y + 0.9, w, y + 1.8, "#4C5058")
        y += 2.0
    reg.rect_(0, 0, w, 8, "#16171A")
    light_bar(reg, 4, 3.0, w - 4, 5.0, turn=260.0, vertical=False)
    reg.paste(atlas)


def ram(atlas):
    """A memory stick's light bar: its colour round the wheel along it, a dark rim."""
    r = L.RAM
    w, h = (r["y"][1] - r["y"][0]) / r["sticks"] * 0.7, r["z"][1] - r["z"][0]
    reg = case_region(atlas, "ram", w, h, "#16171A")
    def draw(d):
        n = 40
        for k in range(n):
            d.rectangle(reg.box(0.9, 4 + (h - 8) * k / n, w - 0.9, 4 + (h - 8) * (k + 1) / n),
                        fill=ring_colour((300 * k / n + 30) % 360) + (255,))
    glow(reg, draw, 0.6, 1)
    reg.paste(atlas)


def fan_face(atlas):
    """A fan's frame from its front: dark, its screw holes, its lit ring round the hole."""
    s, hole = L.FAN["size"], L.FAN["hole"]
    reg = case_region(atlas, "fan", s, s, "#16171B")
    reg.rect_(0, 0, s, s, "#17181C", r=7)
    for x, y in ((7, 7), (s - 7, 7), (7, s - 7), (s - 7, s - 7)):
        reg.circle(x, y, 2.4, "#060607")
    reg.circle(s / 2, s / 2, hole + 1.0, "#0B0B0D")
    lit_ring(reg, s / 2, s / 2, hole + 3.4, hole + 0.4)
    reg.paste(atlas)


def rotor_face(atlas):
    """A fan's rotor from its front: its smoky blades lit from the hub, the gaps dark, the hub's lit ring."""
    r = L.FAN["rotor"]
    reg = case_region(atlas, "blades", 2 * r, 2 * r, "#08090A")
    blades(reg, r, r, r - 0.5, 15.0, (58, 62, 72), count=L.FAN["blades"])
    tint = reg.layer()
    td = ImageDraw.Draw(tint)
    for a in range(0, 360, 3):
        td.pieslice(reg.box(0, 0, 2 * r, 2 * r), a, a + 4, fill=ring_colour(a) + (70,))
    mask = Image.new("L", tint.size, 0)
    ImageDraw.Draw(mask).ellipse(reg.box(16, 16, 2 * r - 16, 2 * r - 16), fill=180)
    tint.putalpha(Image.composite(tint.getchannel("A"), Image.new("L", tint.size, 0), mask))
    reg.over(tint.filter(ImageFilter.GaussianBlur(3 * reg.sx)))
    reg.circle(r, r, 14.0, "#1C1D22", outline="#33363E", width=0.8)
    glow(reg, lambda d: d.ellipse(reg.box(r - 10, r - 10, r + 10, r + 10), outline=(170, 225, 255, 255),
                                  width=reg.width(1.6)), 1.5, 2)
    hex_mark(reg, r, r, 4.0, (170, 176, 188), 0.6)
    reg.paste(atlas)


def case_atlas(out):
    atlas = Image.new("RGB", (L.CASE_ATLAS, L.CASE_ATLAS), "#101114")
    for draw in (front, top, back, board, gpu, gpu_top, shroud, fins, ram, fan_face, rotor_face):
        draw(atlas)
    swatches(atlas, L.CASE_SWATCH_AT, L.CASE_SWATCHES)
    atlas.save(out, optimize=True)


# -- windows_desk.png --------------------------------------------------------------------------------------------------

KB = L.KEYBOARD


def key_colour(a):
    """The lights' colour across the keyboard, a mm from its left edge."""
    return ring_colour((300 * a / KB["width"] + 10) % 360)


def keys_region(atlas):
    """The keyboard from above, its back edge at the top: the plate (each switch's housing, its glow), then the keys'
    tops (each as keycap() builds it) with their legends lit."""
    w, h = KB["width"], KB["depth"]
    reg = Region(L.DESK_REGIONS["keys"], w, h, "#191A1E")
    cap = KB["cap"]
    rects = [(name, L.key_rect(x, row, kw, tall), legend) for name, x, row, kw, legend, tall in L.KEYS]

    def halos(d):
        for _name, (x0, y0, x1, y1), _legend in rects:
            colour = key_colour((x0 + x1) / 2)
            d.rounded_rectangle(reg.box(x0 - 0.6, h - y1 - 0.6, x1 + 0.6, h - y0 + 0.6), radius=2.5 * reg.sx,
                                fill=colour + (200,))
    glow(reg, halos, 1.6, 1)
    for _name, (x0, y0, x1, y1), _legend in rects:          # the switches' housings under the caps
        reg.rect_(x0 + 2.2, h - y1 + 2.2, x1 - 2.2, h - y0 - 2.2, "#0B0B0D", r=1.4)
    for _name, (x0, y0, x1, y1), legend in rects:
        tw, td = cap["top"]
        iw, idp = x1 - x0 - (cap["base"] - tw), y1 - y0 - (cap["base"] - td)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 0.8
        a0, b0 = cx - iw / 2 - 0.4, h - (cy + idp / 2) - 0.4
        reg.rect_(a0, b0, a0 + iw + 0.8, b0 + idp + 0.8, "#17181C", r=1.6)
        if legend:
            ink = mix(key_colour(cx), (255, 255, 255), 0.25)
            lines = legend.split("\n")
            if len(lines) == 2:
                reg.text(lines[0], "segoeuib.ttf", 2.6, cx, h - cy - 2.6, ink)
                reg.text(lines[1], "segoeuib.ttf", 3.0, cx, h - cy + 2.6, ink)
            else:
                size = 3.4 if len(legend) == 1 else (2.2 if len(legend) > 4 else 2.5)
                reg.text(legend, "segoeuib.ttf", size, cx, h - cy, ink)
    reg.paste(atlas)


def mat_region(atlas):
    """The mat from above: dark cloth, a faint mark, its lit edge all round."""
    x0, x1 = L.MAT["x"]
    y0, y1 = L.MAT["y"]
    w, h = x1 - x0, y1 - y0
    reg = Region(L.DESK_REGIONS["mat"], w, h, "#121316")
    rng = random.Random(7)
    for _ in range(900):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        reg.line([(x, y), (x + rng.uniform(2, 9), y + rng.uniform(-1, 1))], "#16171B", 0.4)
    hex_mark(reg, w - 46, h - 34, 9.0, (40, 42, 48), 1.0)

    def edge(d):
        n = 120
        for k in range(n):                                   # along the top and bottom
            t0, t1 = k / n, (k + 1) / n
            c = ring_colour((300 * (t0 + t1) / 2) % 360) + (255,)
            d.rectangle(reg.box(w * t0, 0, w * t1, 2.4), fill=c)
            d.rectangle(reg.box(w * t0, h - 2.4, w * t1, h), fill=c)
        n = 40
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            d.rectangle(reg.box(0, h * t0, 2.4, h * t1), fill=ring_colour(0) + (255,))
            d.rectangle(reg.box(w - 2.4, h * t0, w, h * t1), fill=ring_colour(300) + (255,))
    glow(reg, edge, 3.0, 2)
    reg.paste(atlas)


def mouse_region(atlas):
    """The mouse from above, its buttons forward (at the top): the split between them, the wheel's slot, the lit
    mark in the palm."""
    w, length, _h = L.MOUSE["size"]
    reg = Region(L.DESK_REGIONS["mouse"], w, length, "#141518")
    split = L.MOUSE["split"]
    reg.line([(w / 2, 0), (w / 2, split)], "#050506", 0.7)
    reg.draw.arc(reg.box(-10, split - 18, w + 10, split + 18), 200, 340, fill="#050506", width=reg.width(0.7))
    reg.rect_(w / 2 - 4.2, 18, w / 2 + 4.2, 40, "#060607", r=3.0)
    glow(reg, lambda d: hex_mark_on(d, reg, w / 2, 88, 6.0), 1.5, 2)
    reg.paste(atlas)


def chin_region(atlas):
    w, h = L.MONITOR["width"] - 6.0, L.MONITOR["chin"] - 2.0
    reg = Region(L.DESK_REGIONS["chin"], w, h, "#0A0A0C")
    reg.text("ODYSSEY", "segoeuib.ttf", 4.6, w / 2, h / 2, "#3A3C42")
    reg.circle(w - 18, h / 2 + 4, 0.9, "#E8F2FF")
    reg.paste(atlas)


def back_region(atlas):
    hw, hh, _hd = L.MONITOR["housing"]
    reg = Region(L.DESK_REGIONS["back"], hw, hh, "#141518")
    for k in range(16):
        reg.rect_(60 + k * 19, 22, 70 + k * 19, 60, "#0B0C0E", r=3)
    hex_mark(reg, hw / 2, hh * 0.62, 18.0, (40, 42, 48), 1.6)
    reg.paste(atlas)


def desk_atlas(out):
    atlas = Image.new("RGB", (L.DESK_ATLAS, L.DESK_ATLAS), "#111215")
    for draw in (keys_region, mat_region, mouse_region, chin_region, back_region):
        draw(atlas)
    swatches(atlas, L.DESK_SWATCH_AT, L.DESK_SWATCHES)
    atlas.save(out, optimize=True)


# -- The screens -------------------------------------------------------------------------------------------------------

SW, SH = L.SCREEN
SSV = 2                                    # the screens drawn this many times larger, then resampled
K = L.VIDEO_PX[0] / SW * SSV               # pixels a screen unit, while drawing
TASKBAR = 48
WHITE = (243, 243, 243)
GREY = (172, 172, 176)
GOLD = (236, 196, 112)
_fonts = {}


def font(name, size):
    key = (name, max(1, round(size * K)))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONTS + name, key[1])
    return _fonts[key]


def bx(x0, y0, x1, y1):
    return [x0 * K, y0 * K, x1 * K, y1 * K]


def pw(units):
    """A line's width in pixels, for a width in units."""
    return max(1, round(units * K))


def screen_size():
    return round(SW * K), round(SH * K)


def finished(img):
    return img.convert("RGB").resize(L.VIDEO_PX, Image.LANCZOS)


def faded(img, t, colour=(0, 0, 0)):
    """img faded towards colour: t 1 shows it, 0 is the colour."""
    return img if t >= 1.0 else Image.blend(Image.new("RGB", img.size, colour), img.convert("RGB"), max(0.0, t))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def phase(f, f0, f1):
    return min(1.0, max(0.0, (f - f0) / (f1 - f0)))


def painting(name):
    from arcade_print import painting as load                 # the paintings (artifacts/console-paintings)
    return load(name)


def cover(img, size, centre=(0.5, 0.5), zoom=1.0):
    """img scaled to cover size (zoom times more), cropped about centre (fractions of img)."""
    w, h = size
    s = max(w / img.width, h / img.height) * zoom
    big = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    x = min(max(0, round(big.width * centre[0] - w / 2)), big.width - w)
    y = min(max(0, round(big.height * centre[1] - h / 2)), big.height - h)
    return big.crop((x, y, x + w, y + h))


# The desktop.

_desktop = {}


def bloom():
    """The wallpaper: an abstract bloom on deep blue, the card's own."""
    if "wallpaper" in _desktop:
        return _desktop["wallpaper"]
    size = screen_size()
    img = gradient(size, [(0, (14, 34, 86)), (0.55, (8, 22, 62)), (1, (3, 8, 28))])
    cx, cy = SW * 0.56 * K, SH * 0.5 * K
    petals = Image.new("RGBA", size, (0, 0, 0, 0))
    for a, length, colour in ((-150, 410, (37, 99, 235)), (-120, 450, (59, 130, 246)), (-90, 470, (96, 165, 250)),
                              (-60, 450, (59, 130, 246)), (-30, 410, (37, 99, 235)), (-180, 320, (30, 64, 175)),
                              (0, 320, (30, 64, 175))):
        petal = Image.new("RGBA", size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(petal)
        for i in range(10):
            t = i / 10
            ln, wd = length * (1 - 0.6 * t) * K, 150 * (1 - 0.55 * t) * K
            x0 = cx + 12 * K
            pd.ellipse([x0, cy - wd / 2, x0 + ln, cy + wd / 2], fill=mix(colour, (190, 225, 255), t * 0.9) + (70,))
        petals.alpha_composite(petal.rotate(-a, resample=Image.BICUBIC, center=(cx, cy)))
    img.alpha_composite(petals.filter(ImageFilter.GaussianBlur(2 * K)))
    halo = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([cx - 90 * K, cy - 64 * K, cx + 90 * K, cy + 64 * K], fill=(200, 230, 255, 120))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(38 * K)))
    _desktop["wallpaper"] = img
    return img


def game_icon():
    """Wyrmspire's icon: its title's spire and dragon in a rounded square."""
    if "game_icon" not in _desktop:
        art = cover(painting("win_title").convert("RGB"), (256, 256), centre=(0.72, 0.42))
        mask = Image.new("L", art.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, 255, 255], radius=46, fill=255)
        icon = Image.new("RGBA", art.size, (0, 0, 0, 0))
        icon.paste(art, (0, 0), mask)
        _desktop["game_icon"] = icon
    return _desktop["game_icon"]


def icon(img, d, kind, x, y, s):
    """An app's icon, s units square, centred on (x, y)."""
    h = s / 2
    if kind == "start":                      # the card's own: four petals round a point, as its wallpaper's bloom
        for k in range(4):
            a = math.radians(45 + 90 * k)
            px_, py_ = x + math.cos(a) * s * 0.2, y + math.sin(a) * s * 0.2
            d.ellipse(bx(px_ - s * 0.17, py_ - s * 0.17, px_ + s * 0.17, py_ + s * 0.17),
                      fill=(120, 190, 255) if k in (2, 3) else (70, 150, 245))
    elif kind == "search":
        d.ellipse(bx(x - s * 0.3, y - s * 0.3, x + s * 0.14, y + s * 0.14), outline=WHITE, width=pw(s * 0.07))
        d.line(bx(x + s * 0.1, y + s * 0.1, x + s * 0.3, y + s * 0.3), fill=WHITE, width=pw(s * 0.08))
    elif kind == "files":
        d.rounded_rectangle(bx(x - h * 0.9, y - h * 0.62, x - h * 0.1, y - h * 0.3), radius=s * 0.05 * K,
                            fill=(230, 160, 30))
        d.rounded_rectangle(bx(x - h * 0.9, y - h * 0.45, x + h * 0.9, y + h * 0.7), radius=s * 0.06 * K,
                            fill=(247, 196, 66))
    elif kind == "browser":
        d.ellipse(bx(x - h * 0.85, y - h * 0.85, x + h * 0.85, y + h * 0.85), fill=(24, 132, 214))
        d.arc(bx(x - h * 0.55, y - h * 0.55, x + h * 0.55, y + h * 0.55), 160, 430, fill=(120, 220, 160),
              width=pw(s * 0.12))
    elif kind == "store":
        d.arc(bx(x - h * 0.35, y - h * 0.85, x + h * 0.35, y - h * 0.15), 180, 360, fill=WHITE, width=pw(s * 0.06))
        d.rounded_rectangle(bx(x - h * 0.8, y - h * 0.45, x + h * 0.8, y + h * 0.8), radius=s * 0.08 * K,
                            fill=(42, 120, 214))
        d.rounded_rectangle(bx(x - h * 0.3, y - h * 0.05, x + h * 0.3, y + h * 0.45), radius=s * 0.03 * K, fill=WHITE)
    elif kind == "bin":
        d.rounded_rectangle(bx(x - h * 0.6, y - h * 0.5, x + h * 0.6, y + h * 0.9), radius=s * 0.06 * K,
                            fill=(200, 214, 230))
        d.rectangle(bx(x - h * 0.75, y - h * 0.68, x + h * 0.75, y - h * 0.52), fill=(225, 234, 245))
        for k in (-1, 0, 1):
            d.line(bx(x + k * h * 0.28, y - h * 0.3, x + k * h * 0.28, y + h * 0.7), fill=(150, 166, 186),
                   width=pw(s * 0.05))
    elif kind == "game":
        art = game_icon().resize((round(s * K), round(s * K)), Image.LANCZOS)
        img.paste(art, (round((x - h) * K), round((y - h) * K)), art)


DESKTOP_ICONS = [("files", "Files", 70.0), ("game", "Wyrmspire", L.ICON[1] - 4.0), ("browser", "Browser", 290.0),
                 ("bin", "Bin", 400.0)]
TASK_ICONS = ("start", "search", "files", "browser", "store", "game")


def desktop(selected=False, launching=0.0):
    """The desktop: the wallpaper, the icons down its left (Wyrmspire's selected, if selected), the taskbar (its icons
    centred, Wyrmspire's lit as it starts: launching 0 to 1), the tray."""
    img = bloom().convert("RGB")                    # RGB: an RGBA draw blends its translucent fills only onto RGB
    d = ImageDraw.Draw(img, "RGBA")
    for kind, name, y in DESKTOP_ICONS:
        x = L.ICON[0]
        if kind == "game" and selected:
            d.rounded_rectangle(bx(x - 40, y - 34, x + 40, y + 46), radius=6 * K, fill=(120, 170, 255, 70),
                                outline=(160, 200, 255, 150), width=pw(1))
        icon(img, d, kind, x, y, 44)
        d.text(((x + 0.8) * K, (y + 36.8) * K), name, font=font("segoeui.ttf", 11.5), fill=(0, 0, 0, 200),
               anchor="mm")
        d.text((x * K, (y + 36) * K), name, font=font("segoeui.ttf", 11.5), fill=WHITE, anchor="mm")
    d.rectangle(bx(0, SH - TASKBAR, SW, SH), fill=(26, 28, 36, 232))
    d.line(bx(0, SH - TASKBAR + 0.3, SW, SH - TASKBAR + 0.3), fill=(62, 66, 78), width=pw(0.7))
    for i, kind in enumerate(TASK_ICONS):
        x, y = SW / 2 + (i - (len(TASK_ICONS) - 1) / 2) * 48, SH - TASKBAR / 2
        if kind in ("files", "browser") or (kind == "game" and launching > 0):
            wide = 6 + 10 * launching if kind == "game" else 6
            d.rounded_rectangle(bx(x - wide / 2, y + 17, x + wide / 2, y + 19.4), radius=1.2 * K,
                                fill=(150, 190, 255) if kind == "game" else (150, 150, 160))
        if kind == "game" and launching > 0:
            d.rounded_rectangle(bx(x - 20, y - 20, x + 20, y + 20), radius=5 * K,
                                fill=(255, 255, 255, round(26 * launching)))
        icon(img, d, kind, x, y, 26)
    d.text((40 * K, (SH - 31) * K), "18°C", font=font("segoeuib.ttf", 11), fill=WHITE, anchor="lm")
    d.text((40 * K, (SH - 15) * K), "Cloudy", font=font("segoeui.ttf", 10), fill=GREY, anchor="lm")
    for k in range(3):                                         # the network, the sound
        d.rectangle(bx(SW - 142 + k * 5, SH - 16 - k * 4, SW - 139 + k * 5, SH - 13), fill=WHITE)
    d.polygon([(p[0] * K, p[1] * K) for p in ((SW - 118, SH - 27), (SW - 113, SH - 27), (SW - 106, SH - 32),
                                              (SW - 106, SH - 13), (SW - 113, SH - 18), (SW - 118, SH - 18))],
              fill=WHITE)
    d.text(((SW - 52) * K, (SH - 31) * K), "16:45", font=font("segoeui.ttf", 11), fill=WHITE, anchor="mm")
    d.text(((SW - 52) * K, (SH - 15) * K), "02/11/2026", font=font("segoeui.ttf", 11), fill=WHITE, anchor="mm")
    return img


# The pointers.

ARROW = [(0, 0), (0, 23), (6.2, 17.4), (10.6, 26.4), (14.2, 24.8), (9.8, 16.2), (17.4, 16.2)]


def pointer(img, x, y, kind="arrow", t=0.0):
    """The pointer, its tip at (x, y): the arrow; the arrow with a spinning ring while an app starts (busy, t seconds
    in); or the game's own, gold (game)."""
    d = ImageDraw.Draw(img, "RGBA")
    if kind == "game":
        pts = [(0, 0), (0, 22), (5.6, 16.6), (9.8, 25), (13, 23.6), (9, 15.6), (16, 15.6)]
        d.polygon([((x + a) * K, (y + b) * K) for a, b in pts], fill=(236, 200, 120), outline=(60, 34, 10),
                  width=pw(1.1))
        d.line([((x + 2.2) * K, (y + 5) * K), ((x + 2.2) * K, (y + 15) * K)], fill=(255, 238, 190), width=pw(1))
        return
    d.polygon([((x + a) * K, (y + b) * K) for a, b in ARROW], fill=(255, 255, 255), outline=(0, 0, 0), width=pw(1.1))
    if kind == "busy":
        cx, cy, r = x + 22, y + 24, 7.0
        start = (t * 400) % 360
        d.arc(bx(cx - r, cy - r, cx + r, cy + r), start, start + 250, fill=(40, 120, 220), width=pw(2.4))


def still():
    """The desktop with the pointer at rest: the video's first and last frame."""
    img = desktop()
    pointer(img, *L.REST)
    return finished(img)


# The game: Wyrmspire, remastered.

SERIF = "georgia.ttf"
SERIF_BOLD = "georgiab.ttf"
MENU = ["Continue", "New Game", "Load Game", "Options", "Credits", "Quit to Desktop"]
MENU_X, MENU_Y, MENU_STEP = 112.0, 372.0, 40.0          # the title's menu: its items' left edge, Continue's middle
PAUSE = ["Resume", "Settings", "Controls", "Quit to Desktop"]
PAUSE_Y, PAUSE_STEP = 354.0, 40.0                         # the pause menu's first item's middle; Quit is the last


class Wyrmspire:
    """The game's art: its logo (from the made-up games' library), its title's key art, the valley it's played in,
    and its hero's and its beast's poses, cut out of their green."""

    def __init__(self, made_up):
        from psvita_print import poses                    # cuts Codex's 2 x 2 poses out of their green
        self.logo = Image.open(os.path.join(made_up, "library", "media", "n64", "logos",
                                            "Wyrmspire (Europe).png")).convert("RGBA")
        self.title = painting("win_title").convert("RGB")
        self.vale = painting("win_vale").convert("RGB")
        self.hero = poses(painting("win_hero"))           # running (left foot), running (right foot), ready, thrust
        self.beast = poses(painting("win_beast"))         # prowling, rearing, reeling, down


def item_box(x_left, y, text, size=19.0):
    """A menu item's bounds, (x0, y0, x1, y1) units, its text's left edge at x_left and middle at y."""
    w = font(SERIF, size).getlength(text) / K
    return x_left - 18, y - 16, x_left + w + 18, y + 16


def splash(t):
    """The developer's splash, t from 0 to 1: Pebbleglass's mark (a pebble of glass) and its name, fading in and out."""
    img = Image.new("RGB", screen_size(), (0, 0, 0))
    a = smooth(t / 0.25) * (1 - smooth((t - 0.72) / 0.28))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = SW / 2, SH / 2 - 26
    d.ellipse(bx(cx - 42, cy - 30, cx + 42, cy + 30), fill=(80, 150, 190, 255))
    d.ellipse(bx(cx - 34, cy - 24, cx + 30, cy + 18), fill=(130, 200, 230, 255))
    d.ellipse(bx(cx - 24, cy - 20, cx + 4, cy - 8), fill=(235, 250, 255, 255))
    d.text((cx * K, (cy + 66) * K), "P E B B L E G L A S S", font=font("segoeuil.ttf", 22), fill=(230, 236, 242, 255),
           anchor="mm")
    layer.putalpha(layer.getchannel("A").point(lambda v: round(v * a)))
    img.paste(layer, (0, 0), layer)
    return img


def title_screen(game, n, hover=0.0, pressed=False):
    """The title n frames in: the key art pushing in slowly, darkened at the left; the logo; the menu sliding in, item
    by item, Continue lit by hover (0 to 1) and flashing while pressed."""
    img = cover(game.title, screen_size(), centre=(0.6 + 0.02 * n / 60, 0.5), zoom=1.04 + 0.03 * n / 60).convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(SSV * 0.45))
    ramp = Image.linear_gradient("L").rotate(90, expand=True).resize(img.size)
    img.paste((0, 0, 0), (0, 0) + img.size, ramp.point(lambda v: round(max(0, 205 - v * 1.35))))
    logo = game.logo
    lw = 420
    lh = round(lw * logo.height / logo.width)
    small = logo.resize((round(lw * K), round(lh * K)), Image.LANCZOS)
    img.paste(small, (round(72 * K), round(70 * K)), small)
    d = ImageDraw.Draw(img, "RGBA")
    d.text(((72 + lw / 2) * K, (82 + lh) * K), "R E M A S T E R E D", font=font(SERIF_BOLD, 15), fill=GOLD + (255,),
           anchor="mm")
    for i, item in enumerate(MENU):
        t = smooth((n - 8 - 2 * i) / 8)
        if t <= 0:
            continue
        x, y = MENU_X - 40 * (1 - t), MENU_Y + i * MENU_STEP
        lit = hover if i == 0 else 0.0
        if lit > 0:
            x0, y0, x1, y1 = item_box(MENU_X, y, item)
            d.rectangle(bx(x0, y0, x1 + 60, y1), fill=(236, 196, 112, round(46 * lit)))
            d.polygon([((MENU_X - 14) * K, y * K), ((MENU_X - 9) * K, (y - 5) * K), ((MENU_X - 4) * K, y * K),
                       ((MENU_X - 9) * K, (y + 5) * K)], fill=GOLD + (round(255 * lit),))
        colour = mix((226, 222, 212), GOLD, lit)
        if pressed and i == 0:
            colour = (255, 248, 220)
        d.text((x * K, y * K), item, font=font(SERIF, 19), fill=colour + (round(255 * t),), anchor="lm")
    d.text((72 * K, (SH - 34) * K), "© 2026 Moonquill. Developed by Pebbleglass.", font=font("segoeui.ttf", 10),
           fill=(200, 196, 186, 200), anchor="lm")
    d.text(((SW - 40) * K, (SH - 34) * K), "v1.0.4", font=font("segoeui.ttf", 10), fill=(200, 196, 186, 200),
           anchor="rm")
    return img


def loading(n):
    """The loading screen n frames in: dark, a tip, Loading and a turning rune."""
    img = Image.new("RGB", screen_size(), (6, 7, 9))
    d = ImageDraw.Draw(img, "RGBA")
    d.text((72 * K, (SH - 64) * K), "Tip: hold Shift to sprint; the Mossback Warg tires when it rears.",
           font=font(SERIF, 14), fill=(200, 196, 186), anchor="lm")
    d.text(((SW - 110) * K, (SH - 64) * K), "Loading", font=font(SERIF, 18), fill=GOLD, anchor="rm")
    cx, cy, r = SW - 76, SH - 64, 14
    for k in range(8):
        a = math.radians(k * 45 + n * 12)
        v = 0.25 + 0.75 * ((k + n // 2) % 8) / 7
        d.ellipse(bx(cx + r * math.cos(a) - 2.6, cy + r * math.sin(a) - 2.6, cx + r * math.cos(a) + 2.6,
                     cy + r * math.sin(a) + 2.6), fill=mix((40, 34, 20), GOLD, v))
    return img


class Play:
    """The play, frame by frame from L.PLAY: the camera low behind the hero in the valley, pushing in as she runs
    (sprinting, faster), turned as the mouse looks round (the pointer's travel), stepping aside on A and D; the beast
    prowls in along the path, rears, takes her two thrusts (a flash, the damage rising) and falls, its light going up
    as it fades; the spoils she takes on E; the HUD (her health and stamina, the compass, the quest, the beast's
    health, the abilities)."""

    HERO_H = 0.50            # her height, of the screen's
    STEP = 5                 # frames a stride, running; four sprinting

    def __init__(self, game):
        self.game = game
        self.look0 = L.POINTER.at(L.PLAY[0])[0]
        self.stamina = {}
        s = 1.0
        for f in range(L.PLAY[0], L.PLAY[1] + 1):
            s = max(0.38, s - 0.012) if L.pressed("lshift", f) else min(1.0, s + 0.008)
            self.stamina[f] = s

    def pan(self, f):
        return (L.POINTER.at(f)[0] - self.look0) * L.LOOK

    def strafe(self, f):
        """How far she has stepped aside at frame f (units, + right), and her lean."""
        a = smooth(phase(f, 196, 204)) * (1 - smooth(phase(f, 208, 216)))
        dd = smooth(phase(f, 214, 220)) * (1 - smooth(phase(f, 222, 230)))
        return -70 * a + 52 * dd, -4.0 * a + 3.0 * dd

    def zoom(self, f):
        run = phase(f, L.RUN[0], L.RUN[1])
        sprint = smooth(phase(f, L.SPRINT[0], L.SPRINT[0] + 8)) * (1 - smooth(phase(f, L.SPRINT[1], L.SPRINT[1] + 8)))
        return 1.14 + 0.10 * smooth(run) + 0.02 * sprint

    def hero_pose(self, f):
        for f0 in L.ATTACKS:
            if f0 <= f < f0 + 9:
                return 3
        if L.RUN[0] <= f < L.RUN[1]:
            step = 4 if L.pressed("lshift", f) else self.STEP
            return ((f - L.RUN[0]) // step) % 2
        return 2

    def beast(self, f):
        """The beast at frame f: (pose, depth 0 far to 1 near, x offset units, alpha) or None."""
        b0, b1 = L.BEAST
        if f < b0 or f >= b1:
            return None
        a1, a2 = L.ATTACKS
        near = smooth(phase(f, b0, 234))
        if f < 226:
            pose = 0
        elif f < a1 + 2:
            pose = 1
        elif f < a1 + 10:
            pose = 2
        elif f < a2 + 2:
            pose = 1
        elif f < a2 + 6:
            pose = 2
        else:
            pose = 3
        alpha = 1 - smooth(phase(f, 276, b1))
        return pose, near, 40 + 170 * near, alpha        # down the path, then ahead of her to her right

    def frame(self, f):
        g = self.game
        w, h = screen_size()
        bob = 3.0 * math.sin(math.pi * (f - L.RUN[0]) / self.STEP) if L.RUN[0] <= f < L.RUN[1] else 0.0
        z = self.zoom(f)
        cw = g.vale.width / z
        ch = cw * h / w
        cx = g.vale.width / 2 + self.pan(f)
        cy = g.vale.height * 0.53
        view = g.vale.crop((round(cx - cw / 2), round(cy - ch / 2), round(cx + cw / 2), round(cy + ch / 2)))
        img = view.resize((w, h), Image.LANCZOS).convert("RGB").filter(ImageFilter.GaussianBlur(SSV * 0.45))
        scale = w / cw                                          # the painting's pixels to the screen's
        beast = self.beast(f)
        if beast:
            pose, near, offset, alpha = beast
            p = g.beast[pose]
            bh = h * (0.09 + 0.27 * near) * (0.62 if pose == 3 else 1.0)
            sprite = p["img"].resize((max(1, round(p["img"].width * bh / p["foot"])), max(1, round(bh))),
                                     Image.LANCZOS)
            if alpha < 1:
                sprite.putalpha(sprite.getchannel("A").point(lambda v: round(v * alpha)))
            bx_ = w / 2 + offset * K - self.pan(f) * scale      # on the path: it turns with the valley
            foot = h * (0.58 + 0.22 * near)
            img.paste(sprite, (round(bx_ - sprite.width / 2), round(foot - sprite.height)), sprite)
            self.beast_effects(img, f, bx_, foot - bh * 0.55, bh)
        step, lean = self.strafe(f)
        p = g.hero[self.hero_pose(f)]
        hh = h * self.HERO_H
        sprite = p["img"].resize((max(1, round(p["img"].width * hh / p["foot"])), max(1, round(hh))), Image.LANCZOS)
        if lean:
            sprite = sprite.rotate(lean, resample=Image.BICUBIC, expand=True)
        hx = w / 2 + step * K + (p["img"].width / 2 - p["hip"]) * hh / p["foot"]
        img.paste(sprite, (round(hx - sprite.width / 2), round(h * 0.985 - sprite.height + abs(bob) * K)), sprite)
        self.hud(img, f)
        return faded(img, smooth((f - L.PLAY[0] + 1) / 6))

    def beast_effects(self, img, f, x, y, size):
        """Her thrusts' flashes and damage on the beast, its light going up as it fades, the spoils left."""
        for f0 in (L.ATTACKS[0] + 2, L.ATTACKS[1] + 2):          # the flash where the spear strikes
            age = f - f0
            if 0 <= age < 6:
                r = size * (0.05 + 0.025 * age)
                burst = Image.new("RGBA", img.size, (0, 0, 0, 0))
                ImageDraw.Draw(burst).ellipse([x - r, y - r, x + r, y + r],
                                              fill=(255, 246, 210, round(230 * (1 - age / 6))))
                burst = burst.filter(ImageFilter.GaussianBlur(r * 0.6))
                img.paste(burst, (0, 0), burst)
        d = ImageDraw.Draw(img, "RGBA")
        for f0, dmg, crit in ((L.ATTACKS[0] + 2, "138", False), (L.ATTACKS[1] + 2, "212", True)):
            age = f - f0
            if 0 <= age < 22:
                rise = age * 2.4 * K
                a = round(255 * (1 - max(0, age - 12) / 10))
                text = dmg + (" CRITICAL" if crit else "")
                d.text((x + 40 * K, y - 40 * K - rise), text, font=font(SERIF_BOLD, 22 if crit else 18),
                       fill=(255, 214, 90, a) if crit else (255, 255, 255, a), anchor="mm",
                       stroke_width=pw(1.6), stroke_fill=(40, 20, 0, a))
        if f >= 268:
            rng = random.Random(3)
            for k in range(26):
                age = f - 268 - k * 0.6
                if age < 0:
                    continue
                px_ = x + rng.uniform(-1, 1) * size * 0.6
                py_ = y + size * 0.3 - age * rng.uniform(2.0, 4.0) * K
                a = round(220 * max(0.0, 1 - age / 26))
                d.ellipse([px_ - 3 * K, py_ - 3 * K, px_ + 3 * K, py_ + 3 * K], fill=(255, 226, 150, a))
        if 266 <= f < L.TAKE + 2:
            sp = 0.5 + 0.5 * math.sin(f * 0.6)
            d.ellipse([x - 14 * K, y + size * 0.36 - 14 * K, x + 14 * K, y + size * 0.36 + 14 * K],
                      fill=(255, 240, 180, round(90 + 90 * sp)))
            d.rounded_rectangle([x - 50 * K, y - size * 0.5 - 18 * K, x + 50 * K, y - size * 0.5 + 10 * K],
                                radius=5 * K, fill=(10, 10, 12, 190))
            d.text((x, y - size * 0.5 - 4 * K), "[E]  Take", font=font("segoeuib.ttf", 13), fill=(240, 236, 226),
                   anchor="mm")

    def hud(self, img, f):
        d = ImageDraw.Draw(img, "RGBA")
        # Her health and stamina, top left.
        d.text((40 * K, 34 * K), "Lv 12", font=font(SERIF_BOLD, 15), fill=GOLD, anchor="lm", stroke_width=pw(1.4),
               stroke_fill=(20, 14, 6))
        d.rounded_rectangle(bx(92, 26, 352, 38), radius=3 * K, fill=(0, 0, 0, 150))
        d.rounded_rectangle(bx(94, 28, 350, 36), radius=2 * K, fill=(200, 40, 46))
        s = self.stamina.get(f, 1.0)
        d.rounded_rectangle(bx(92, 44, 272, 50), radius=2 * K, fill=(0, 0, 0, 150))
        d.rounded_rectangle(bx(93, 45, 93 + 178 * s, 49), radius=2 * K, fill=(96, 206, 120))
        # The compass, top middle: its marks turning with the camera, the spire's marker.
        cx, y = SW / 2, 30
        d.rounded_rectangle(bx(cx - 190, y - 12, cx + 190, y + 12), radius=12 * K, fill=(0, 0, 0, 120))
        heading = -self.pan(f) * 0.4
        for k, mark in enumerate(("N", "NE", "E", "SE", "S", "SW", "W", "NW") * 2):
            x = cx + (k - 8) * 70 + heading
            if abs(x - cx) < 176:
                fade = round(255 * (1 - abs(x - cx) / 176))
                d.text((x * K, y * K), mark, font=font("segoeuib.ttf", 11 if len(mark) == 1 else 9),
                       fill=(236, 232, 222, fade), anchor="mm")
        mx = cx + heading * 0.15
        d.polygon([(mx * K, (y - 16) * K), ((mx + 5) * K, (y - 11) * K), (mx * K, (y - 6) * K),
                   ((mx - 5) * K, (y - 11) * K)], fill=GOLD)
        # The quest, top right.
        d.text(((SW - 40) * K, 30 * K), "THE SPIRE AWAITS", font=font(SERIF_BOLD, 14), fill=GOLD, anchor="rm",
               stroke_width=pw(1.4), stroke_fill=(20, 14, 6))
        d.text(((SW - 40) * K, 50 * K), "Follow the path to the Wyrmspire", font=font(SERIF, 12),
               fill=(240, 236, 226), anchor="rm", stroke_width=pw(1.4), stroke_fill=(20, 14, 6))
        # The beast's health, top middle, while she fights it.
        if 222 <= f < 280:
            a = smooth(phase(f, 222, 228)) * (1 - smooth(phase(f, 272, 280)))
            left = 1.0 - 0.45 * smooth(phase(f, L.ATTACKS[0] + 2, L.ATTACKS[0] + 6)) \
                - 0.55 * smooth(phase(f, L.ATTACKS[1] + 2, L.ATTACKS[1] + 6))
            d.text((cx * K, 70 * K), "MOSSBACK WARG", font=font(SERIF_BOLD, 13), fill=(236, 232, 222, round(255 * a)),
                   anchor="mm", stroke_width=pw(1.4), stroke_fill=(20, 14, 6, round(255 * a)))
            d.rounded_rectangle(bx(cx - 160, 82, cx + 160, 90), radius=2 * K, fill=(0, 0, 0, round(170 * a)))
            if left > 0.005:
                d.rounded_rectangle(bx(cx - 158, 84, cx - 158 + 316 * left, 88), radius=2 * K,
                                    fill=(214, 60, 52, round(255 * a)))
        # The spoils taken, and what she earned.
        if L.TAKE <= f:
            t = smooth(phase(f, L.TAKE, L.TAKE + 5))
            d.rounded_rectangle(bx(SW - 260, 80, SW - 40, 112), radius=5 * K, fill=(10, 10, 12, round(170 * t)))
            d.text(((SW - 250) * K, 96 * K), "+ Warg Fang", font=font(SERIF, 14), fill=(236, 214, 150, round(255 * t)),
                   anchor="lm")
            d.text(((SW - 50) * K, 96 * K), "+250 XP", font=font("segoeuib.ttf", 12),
                   fill=(150, 220, 255, round(255 * t)), anchor="rm")
        # The abilities, bottom middle, each with its key.
        for k, (key, glyph) in enumerate((("1", "spear"), ("2", "shield"), ("3", "flask"), ("4", "wing"))):
            x0 = SW / 2 - 104 + k * 54
            d.rounded_rectangle(bx(x0, SH - 70, x0 + 46, SH - 24), radius=6 * K, fill=(8, 8, 10, 170),
                                outline=(236, 196, 112, 150), width=pw(1))
            self.glyph(d, glyph, x0 + 23, SH - 47)
            d.text(((x0 + 6) * K, (SH - 64) * K), key, font=font("segoeuib.ttf", 9), fill=(230, 226, 214), anchor="lm")

    @staticmethod
    def glyph(d, kind, x, y):
        c = (232, 210, 150)
        if kind == "spear":
            d.line(bx(x - 12, y + 12, x + 10, y - 10), fill=c, width=pw(2))
            d.polygon([((x + 13) * K, (y - 13) * K), ((x + 4) * K, (y - 9) * K), ((x + 9) * K, (y - 4) * K)], fill=c)
        elif kind == "shield":
            d.polygon([((x - 10) * K, (y - 11) * K), ((x + 10) * K, (y - 11) * K), ((x + 9) * K, (y + 2) * K),
                       (x * K, (y + 12) * K), ((x - 9) * K, (y + 2) * K)], outline=c, width=pw(2))
        elif kind == "flask":
            d.ellipse(bx(x - 9, y - 4, x + 9, y + 13), fill=(200, 60, 70))
            d.rectangle(bx(x - 3, y - 12, x + 3, y - 3), fill=c)
        else:
            d.polygon([((x - 12) * K, (y + 6) * K), ((x + 2) * K, (y - 12) * K), ((x + 12) * K, (y - 8) * K),
                       ((x + 2) * K, (y + 2) * K)], fill=c)


def paused(game_frame, hover=0.0, pressed=False):
    """The pause menu over the game's frame (blurred, darkened): PAUSED and its items, Quit to Desktop lit by hover
    (0 to 1) and flashing while pressed."""
    img = game_frame.filter(ImageFilter.GaussianBlur(6 * K)).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, img.width, img.height], fill=(0, 0, 0, 120))
    cx = SW / 2
    top = PAUSE_Y - 70
    d.rounded_rectangle(bx(cx - 200, top, cx + 200, PAUSE_Y + (len(PAUSE) - 1) * PAUSE_STEP + 40), radius=10 * K,
                        fill=(10, 10, 12, 200), outline=(236, 196, 112, 120), width=pw(1))
    d.text((cx * K, (top + 32) * K), "P A U S E D", font=font(SERIF_BOLD, 22), fill=GOLD, anchor="mm")
    for i, item in enumerate(PAUSE):
        y = PAUSE_Y + i * PAUSE_STEP
        lit = hover if item == "Quit to Desktop" else 0.0
        if lit > 0:
            d.rounded_rectangle(bx(cx - 150, y - 16, cx + 150, y + 16), radius=4 * K,
                                fill=(236, 196, 112, round(50 * lit)))
        colour = mix((226, 222, 212), GOLD, lit)
        if pressed and lit > 0:
            colour = (255, 248, 220)
        d.text((cx * K, y * K), item, font=font(SERIF, 19), fill=colour, anchor="mm")
    return img


def on_item(point, box):
    x, y = point
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def continue_box():
    return item_box(MENU_X, MENU_Y, MENU[0])


def quit_box():
    y = PAUSE_Y + (len(PAUSE) - 1) * PAUSE_STEP
    return SW / 2 - 150, y - 16, SW / 2 + 150, y + 16


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    case_atlas(os.path.join(out, "windows_case.png"))
    desk_atlas(os.path.join(out, "windows_desk.png"))
    path = os.path.join(out, "windows_screen.png")
    still().save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
