"""The Sega Game Gear card's printing, lens and screens, for the console theme's Game Gear model (game_gear.py) and its
video (game_gear_video.py). game_gear_layout.py has the measurements and where each part is in the atlas.

Writes two images into a folder:
- game_gear_print.png, laid out as game_gear_layout.REGIONS says, each region in millimetres as the model's UVs map it:
  the face (the matt grips; the island's gloss; START's blue drop, the bracket and 1 and 2; the D-pad's cross cut by its
  X; the wells' shadows), the back (the battery covers with OPEN, the rating sticker, the serial plate, the screws, the
  accessory slots, CARTRIDGE under the notch), the top edge (POWER, DC 9V, EXT, PHONE, VOLUME), the cartridge's label
  side (a made-up game from tools/made-up-games: its key art and logo under a GAME GEAR band, the grip's ridges, SEGA
  moulded in its frame) and swatches.
- game_gear_lens.png: the lens with the Game Gear switched off, the texture of the model's `video` material and the
  first and last frames of its video.

The lens and the screens are drawn here for game_gear_video.py too: the lens's black acrylic and its printing (the
coloured ovals, GAME GEAR, the power light and POWER, SEGA, PORTABLE VIDEO GAME SYSTEM, the LCD's grey frame), and the
LCD at the Game Gear's 160 x 144 in its 4096 colours (four bits a channel): a made-up publisher's splash, the made-up
game's title and its play, a ninja drawn here running, leaping and throwing knives over the game's painting, scrolled
a whole pixel at a time as the console scrolls. Every game and mark on them is made up.

Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow,
numpy, scipy):

    python tools/console-models/game_gear_print.py artifacts/made-up-games artifacts/gamegear
"""

import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_gear_layout as L  # noqa: E402
from arcade_print import Game  # noqa: E402

FONTS = "C:/Windows/Fonts/"
SS = 4                                  # supersampling while drawing


def rgb(hex_colour):
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def shade(colour, t):
    """colour darkened (t < 0) or lightened (t > 0)."""
    return mix(colour, (0, 0, 0) if t < 0 else (255, 255, 255), abs(t))


def back_out(t, s=2.2):
    """Overshoots, then settles at 1 (clip.py's, which needs Blender)."""
    t -= 1
    return 1 + t * t * ((s + 1) * t + s)


C = {name: rgb(value) for name, value in L.COLOURS.items()}
WHITE = (236, 236, 232)
OVALS = [(-57.3, (214, 40, 46)), (-51.8, (26, 163, 122)), (-46.7, (35, 102, 209))]


class Sheet:
    """A face drawn in millimetres as the model's UVs project it: x across from x0 to x1 (mirrored, x1 at the left, for
    a face seen from behind), z down from z1 at the top to z0; supersampled, then resampled to its size in pixels. Its
    two scales may differ (the lens's video): text and circles are drawn to keep their shapes on the model."""

    def __init__(self, size, span, fill, mirror=False, ss=SS):
        self.size = size
        self.x0, self.x1, self.z0, self.z1 = span
        self.mirror = mirror
        self.img = Image.new("RGBA", (size[0] * ss, size[1] * ss), tuple(fill) + (255,))
        self.draw = ImageDraw.Draw(self.img)
        self.sx = size[0] * ss / (self.x1 - self.x0)
        self.sz = size[1] * ss / (self.z1 - self.z0)

    def p(self, x, z):
        return ((self.x1 - x) if self.mirror else (x - self.x0)) * self.sx, (self.z1 - z) * self.sz

    def poly(self, points, fill):
        self.draw.polygon([self.p(x, z) for x, z in points], fill=fill)

    def ellipse(self, x, z, rx, rz, fill, degrees=0.0, n=48):
        c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
        self.poly([(x + rx * math.cos(a) * c - rz * math.sin(a) * s, z + rx * math.cos(a) * s + rz * math.sin(a) * c)
                   for a in (2 * math.pi * k / n for k in range(n))], fill)

    def circle(self, x, z, r, fill):
        self.ellipse(x, z, r, r, fill)

    def rect(self, x0, z0, x1, z1, fill, r=0.0):
        (a, b), (c, d) = self.p(x0, z1), self.p(x1, z0)
        box = [min(a, c), min(b, d), max(a, c), max(b, d)]
        if r:
            self.draw.rounded_rectangle(box, radius=r * self.sx, fill=fill)
        else:
            self.draw.rectangle(box, fill=fill)

    def line(self, points, fill, width):
        self.draw.line([self.p(x, z) for x, z in points], fill=fill, width=max(1, round(width * self.sz)),
                       joint="curve")

    def text(self, s, font, cap, x, z, fill, anchor="m", shear=0.0, stretch=1.0, degrees=0.0, inline=None):
        """Text whose capitals are cap millimetres tall on the model, its middle (or, anchor "l", its left end) at
        (x, z); shear leans it, stretch widens it, degrees turns it anticlockwise; inline draws a line of that colour
        inside each stroke (SEGA's letters)."""
        probe = ImageFont.truetype(FONTS + font, 400)
        top, bottom = probe.getbbox("H")[1], probe.getbbox("H")[3]
        face = ImageFont.truetype(FONTS + font, max(4, round(400 * cap * self.sz / (bottom - top))))
        box = face.getbbox(s)
        pad = round(cap * self.sz)
        mask = Image.new("L", (box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad), 0)
        ImageDraw.Draw(mask).text((pad - box[0], pad - box[1]), s, font=face, fill=255)
        mask = mask.resize((max(1, round(mask.width * stretch * self.sx / self.sz)), mask.height), Image.LANCZOS)
        if shear:
            mask = mask.transform(mask.size, Image.AFFINE, (1, shear, -shear * mask.height / 2, 0, 1, 0),
                                  resample=Image.BICUBIC)
        layer = Image.new("RGBA", mask.size, tuple(fill) + (0,))
        layer.putalpha(mask)
        if inline is not None:
            w = max(1, round(cap * self.sz * 0.04))
            inner = mask.filter(ImageFilter.MinFilter(2 * w + 1))
            ring = ImageChops.subtract(inner, inner.filter(ImageFilter.MinFilter(2 * w + 1)))
            dark = Image.new("RGBA", mask.size, tuple(inline) + (255,))
            layer.paste(dark, (0, 0), ring)
        if degrees:
            layer = layer.rotate(degrees, resample=Image.BICUBIC, expand=True)
        layer = layer.crop(layer.getbbox())
        px, pz = self.p(x, z)
        left = px if anchor == "l" else px - layer.width / 2
        self.img.alpha_composite(layer, (round(left), round(pz - layer.height / 2)))

    def image(self):
        return self.img.convert("RGB").resize(self.size, Image.LANCZOS)


def swatch_blocks(atlas):
    d = ImageDraw.Draw(atlas)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 14, y - 14, x + 13, y + 13], fill=C[name])


def paste(atlas, region, img, grow=4):
    """A region into the atlas, its edge pixels carried grow pixels out round it, so sampling at its edges never
    picks up its neighbour's colour."""
    x, y, w, h = region
    padded = ImageOps.expand(img, grow)
    a = np.asarray(padded).copy()
    a[:grow, :] = a[grow, :]
    a[-grow:, :] = a[-grow - 1, :]
    a[:, :grow] = a[:, grow:grow + 1]
    a[:, -grow:] = a[:, -grow - 1:-grow]
    padded = Image.fromarray(a)
    x0, y0 = x - grow, y - grow
    crop = (max(0, -x0), max(0, -y0))
    atlas.paste(padded.crop((crop[0], crop[1], padded.width, padded.height)), (x0 + crop[0], y0 + crop[1]))


# ---- The face, the back, the top edge --------------------------------------------------------------------------------

def dpad_top(s):
    """The D-pad seen from the front: a glossy black disc, its cross standing up, the X between the arms."""
    x, z = L.DPAD["at"]
    r, arm, half = L.DPAD["r"], L.DPAD["arm"], L.DPAD["half"]
    s.circle(x, z, r + 0.4, C["black"])
    s.circle(x, z, r - 0.5, shade(C["black"], 0.05))
    cross = shade(C["black"], 0.09)
    s.rect(x - arm, z - half, x + arm, z + half, cross, r=1.4)
    s.rect(x - half, z - arm, x + half, z + arm, cross, r=1.4)
    groove = (0, 0, 0)
    for dx, dz in ((1, 1), (1, -1)):
        s.line([(x - dx * 7.4, z - dz * 7.4), (x + dx * 7.4, z + dz * 7.4)], groove, 0.45)
    for k in range(4):                                     # the arrows' ticks, on the arms' ends
        a = math.pi / 2 * k
        cx, cz = x + math.cos(a) * (arm - 2.6), z + math.sin(a) * (arm - 2.6)
        tx, tz = -math.sin(a) * 1.3, math.cos(a) * 1.3
        s.line([(cx - tx, cz - tz), (cx + tx, cz + tz)], (70, 72, 78), 0.3)


def creases(s):
    """The grips' sculpting, where their raised plates fall away to the face's lower bulge: a soft light along each
    plate's edge, a soft shadow under it."""
    for line in L.CREASES:
        for offset, colour, alpha, blur in ((0.9, (255, 255, 255), 22, 0.8), (-1.4, (0, 0, 0), 60, 1.6)):
            layer = Image.new("RGBA", s.img.size, colour + (0,))
            ImageDraw.Draw(layer).line([s.p(x, z + offset) for x, z in line], fill=colour + (alpha,),
                                       width=round(1.6 * s.sz), joint="curve")
            s.img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur * s.sz)))


def face():
    s = Sheet(L.REGIONS["face"][2:], (-L.WIDTH / 2, L.WIDTH / 2, 0.0, L.HEIGHT), C["shell"])
    creases(s)
    s.poly(L.rounded(*L.ISLAND, inset=-0.7, segments=12), C["band"])
    s.poly(L.rounded(*L.PANEL, inset=-0.3, segments=12), C["dark"])
    well = shade(C["shell"], -0.3)
    s.circle(*L.DPAD["at"], L.DPAD["well"] + 0.3, well)
    for name in ("one", "two"):
        s.circle(*L.BUTTONS[name], L.BUTTONS["well"] + 0.3, well)
    dpad_top(s)
    for name in ("one", "two"):
        s.circle(*L.BUTTONS[name], L.BUTTONS["r"] + 0.4, C["black"])
    s.poly(L.drop(), C["blue"])
    cx, cz = L.START["at"]
    s.circle(cx + 2.6, cz + 0.6, 0.45, shade(C["blue"], -0.35))
    s.line(L.BRACKET, C["legend"], 0.5)
    s.text("1", "arialbd.ttf", 2.3, *L.LEGENDS["one"], C["legend"], degrees=40.0)
    s.text("2", "arialbd.ttf", 2.5, *L.LEGENDS["two"], C["legend"], degrees=40.0)
    s.text("START", "arialbd.ttf", 2.4, *L.LEGENDS["start"], C["legend"], anchor="l")
    return s.image()


def back():
    s = Sheet(L.REGIONS["back"][2:], (-L.WIDTH / 2, L.WIDTH / 2, 0.0, L.HEIGHT), C["shell"], mirror=True)
    seam = shade(C["shell"], -0.45)
    w, h = L.COVERS["size"]
    for side in (-1, 1):
        x = side * L.COVERS["x"]
        s.rect(x - w / 2 - 0.4, L.COVERS["z"] - h / 2 - 0.4, x + w / 2 + 0.4, L.COVERS["z"] + h / 2 + 0.4, seam,
               r=L.COVERS["r"] + 0.4)
        s.rect(x - w / 2, L.COVERS["z"] - h / 2, x + w / 2, L.COVERS["z"] + h / 2, shade(C["shell"], 0.03),
               r=L.COVERS["r"])
        z = L.COVERS["z"] - h / 2 + 5.0
        s.text("OPEN", "arial.ttf", 1.6, x, z + 2.6, shade(C["shell"], 0.22))
        s.line([(x - 2.4, z + 0.4), (x, z - 1.2), (x + 2.4, z + 0.4)], shade(C["shell"], 0.22), 0.3)
    s.rect(-23.0, 45.0, 23.0, 61.0, (150, 152, 156))      # the rating sticker
    s.rect(-22.4, 45.6, 22.4, 60.4, (178, 180, 184))
    for k, line in enumerate(("SEGA   GAME GEAR  MODEL 2110", "RATING: DC 9V  6 AA BATTERIES",
                              "AC ADAPTOR: USE 2110 AC ADAPTOR ONLY", "SEGA ENTERPRISES, LTD.   MADE IN TAIWAN")):
        s.text(line, "arialbd.ttf" if k == 0 else "arial.ttf", 1.15, 21.0, 58.0 - 3.2 * k, (52, 54, 58), anchor="l")
    s.rect(-15.0, 64.0, 15.0, 69.6, (232, 232, 228))     # the serial plate
    s.rect(-14.4, 64.6, 14.4, 69.0, (24, 24, 26))
    s.rect(-14.0, 65.0, 14.0, 68.6, (232, 232, 228))
    s.text("0127 10942", "consola.ttf", 2.2, 0.0, 66.8, (24, 24, 26))
    hole = (8, 8, 9)
    for x, z in ((-50.0, 99.0), (50.0, 99.0), (-98.0, 20.0), (98.0, 20.0), (-44.0, 18.0), (44.0, 18.0)):
        s.circle(x, z, 1.7, hole)
    for side in (-1, 1):                                   # the accessories' T slots
        x = side * 31.0
        s.rect(x - 1.4, 64.0, x + 1.4, 71.0, hole)
        s.rect(x - 4.0, 70.0, x + 4.0, 72.4, hole)
    s.circle(0.0, 38.0, 1.7, C["gold"])
    s.circle(0.0, 38.0, 0.7, shade(C["gold"], -0.5))
    s.text("CARTRIDGE", "arial.ttf", 1.6, 0.0, 93.6, shade(C["shell"], 0.2))
    s.line([(-3.0, 91.6), (0.0, 89.8), (3.0, 91.6)], shade(C["shell"], 0.2), 0.3)
    s.rect(-L.NOTCH["x"], L.NOTCH["z"], L.NOTCH["x"], L.HEIGHT, C["dark"])
    return s.image()


def top():
    """The top edge from above, its back at the region's top: y back from the face plays z's part."""
    s = Sheet(L.REGIONS["top"][2:], (-L.WIDTH / 2, L.WIDTH / 2, 0.0, L.DEPTH), C["shell"])
    ink = shade(C["shell"], 0.24)
    x0, x1, y0, y1 = L.POWER["recess"]
    s.rect(x0, y0, x1, y1, C["dark"], r=0.6)
    s.text("POWER", "arial.ttf", 1.5, (x0 + x1) / 2, y0 - 2.6, ink)
    x, y, r = L.JACKS["dc"]
    s.circle(x, y, r + 0.6, shade(C["shell"], -0.4))
    s.text("DC 9V", "arial.ttf", 1.4, x - 9.0, y, ink)
    x, y, r = L.JACKS["phone"]
    s.circle(x, y, r + 0.6, shade(C["shell"], -0.4))
    s.text("PHONE", "arial.ttf", 1.4, x, y - 5.4, ink)
    x, y, w, h = L.JACKS["ext"]
    s.rect(x - w / 2 - 0.4, y - h / 2 - 0.4, x + w / 2 + 0.4, y + h / 2 + 0.4, C["dark"], r=0.5)
    s.text("EXT.", "arial.ttf", 1.4, x, y - 5.0, ink)
    v = L.VOLUME
    s.rect(v["x"] - v["r"] - 1.2, v["y"][0] - 1.0, v["x"] + v["r"] + 1.2, v["y"][1] + 1.0, C["dark"], r=0.6)
    s.text("VOLUME", "arial.ttf", 1.4, v["x"] + 1.0, v["y"][0] - 3.4, ink)
    s.rect(-L.NOTCH["x"], L.NOTCH["y"], L.NOTCH["x"], L.DEPTH, C["dark"])
    return s.image()


# ---- The cartridge's label side --------------------------------------------------------------------------------------

def gg_mark(s, x, z, cap, ink=WHITE):
    """GAME GEAR in one line with its three ovals before it, its left end (as the face is seen) at x."""
    dx = -1.0 if s.mirror else 1.0
    for k, (_, colour) in enumerate(OVALS):
        s.ellipse(x + dx * (cap * 0.42 + k * cap * 0.95), z, cap * 0.32, cap * 0.46, colour, degrees=-25.0)
    s.text("GAME GEAR", "ariblk.ttf", cap, x + dx * cap * 3.1, z, ink, anchor="l", shear=0.12, stretch=0.92)


def cart_label(game):
    c = L.CART
    w, h = c["width"], c["height"]
    s = Sheet(L.REGIONS["cart"][2:], (-w / 2, w / 2, 0.0, h), C["cart"], mirror=True)
    g0, g1, gz0, gz1 = c["grip"]
    for k in range(3):                                     # the grip's ridges
        z = gz1 - 1.6 - 1.7 * k
        s.line([(-16.0, z), (16.0, z)], shade(C["cart"], -0.5), 0.45)
        s.line([(-16.0, z - 0.45), (16.0, z - 0.45)], shade(C["cart"], 0.15), 0.25)
    x0, x1, z0, z1 = c["label"]
    r_top, r_bottom = c["label_r"]
    s.rect(x0, z0, x1, z1, (18, 18, 20), r=r_bottom)
    s.rect(x0, z1 - 2 * r_top, x1, z1, (18, 18, 20), r=r_top)
    band = z1 - 7.0
    art = game.keyart
    aw = art.width
    crop = art.crop((0, round(aw * 0.18), aw, round(aw * 0.18 + aw * (band - z0 - 0.6) / (x1 - x0 - 1.2))))
    (a, b), (cc, d) = s.p(x1 - 0.6, band - 0.3), s.p(x0 + 0.6, z0 + 0.6)
    box = [round(min(a, cc)), round(min(b, d)), round(max(a, cc)), round(max(b, d))]
    s.img.paste(ImageOps.fit(crop, (box[2] - box[0], box[3] - box[1]), Image.LANCZOS), (box[0], box[1]))
    logo = game.logo
    k = min((box[2] - box[0]) * 0.74 / logo.width, (box[3] - box[1]) * 0.42 / logo.height)
    logo = logo.resize((round(logo.width * k), round(logo.height * k)), Image.LANCZOS)
    s.img.alpha_composite(logo, (round((box[0] + box[2] - logo.width) / 2), round(box[1] + (box[3] - box[1]) * 0.05)))
    s.rect(x0 + 0.6, band, x1 - 0.6, z1 - 0.6, (14, 14, 16), r=r_top - 0.6)
    gg_mark(s, x1 - 3.2, (band + z1) / 2 - 0.2, 2.6)       # seen from its label side, its left is the cartridge's +x
    s.text(game.publisher.upper(), "arialbd.ttf", 1.5, x0 + 9.0, (band + z1) / 2 - 0.2, (190, 190, 196))
    sx, sz, sw, sh = c["sega"]                            # SEGA, moulded in its frame
    moulded = shade(C["cart"], 0.12)
    s.rect(sx - sw / 2, sz - sh / 2, sx + sw / 2, sz + sh / 2, moulded, r=sh / 2)
    s.rect(sx - sw / 2 + 0.6, sz - sh / 2 + 0.6, sx + sw / 2 - 0.6, sz + sh / 2 - 0.6, C["cart"], r=sh / 2 - 0.6)
    s.text("SEGA", "ariblk.ttf", 3.6, sx, sz, moulded, stretch=1.25)
    return s.image()


def print_atlas(game, out):
    atlas = Image.new("RGB", (L.ATLAS, L.ATLAS), C["shell"])
    paste(atlas, L.REGIONS["face"], face())
    paste(atlas, L.REGIONS["back"], back())
    paste(atlas, L.REGIONS["top"], top())
    paste(atlas, L.REGIONS["cart"], cart_label(game))
    swatch_blocks(atlas)
    atlas.save(out, optimize=True)


# ---- The lens --------------------------------------------------------------------------------------------------------

def lens_sheet():
    return Sheet(L.LENS_PX, L.LENS, C["dark"], ss=3)


def sega_logo(s, x, z, cap):
    s.text("SEGA", "ariblk.ttf", cap, x, z, WHITE, stretch=0.88, inline=(30, 31, 34))


def lens_base():
    """The lens switched off: the black acrylic and its printing, the LCD's frame, the LCD itself grey."""
    s = lens_sheet()
    s.poly(L.rounded(*L.PANEL, segments=12), (30, 31, 34))
    s.poly(L.rounded(*L.PANEL, inset=0.45, segments=12), C["dark"])
    for x, colour in OVALS:
        s.ellipse(x, 95.6, 1.75, 2.7, colour, degrees=-25.0)
    s.text("GAME", "ariblk.ttf", 3.85, -60.9, 89.4, WHITE, anchor="l", shear=0.1, stretch=0.74)
    s.text("GEAR", "ariblk.ttf", 3.85, -57.3, 84.85, WHITE, anchor="l", shear=0.1, stretch=0.74)
    x, z, r = L.LED
    s.circle(x, z, r + 0.35, (40, 40, 44))
    s.circle(x, z, r, (44, 14, 10))
    s.circle(x - 0.35, z + 0.35, 0.3, (120, 70, 64))
    s.text("POWER", "arial.ttf", 1.15, x, 74.75, (204, 204, 204))
    sega_logo(s, 52.4, 91.2, 4.3)
    for line, z in (("PORTABLE", 87.1), ("VIDEO GAME", 84.3), ("SYSTEM", 81.4)):
        s.text(line, "arial.ttf", 1.6, 44.6, z, C["teal"], anchor="l")
    # The LCD's frame: grey, flat, then its bevel down to the window.
    ox0, ox1, oz0, oz1 = L.FRAME["outer"]
    wx0, wx1, wz0, wz1 = L.FRAME["window"]
    bevel = L.FRAME["bevel"]
    s.rect(ox0, oz0, ox1, oz1, C["frame"], r=1.2)
    bx0, bx1, bz0, bz1 = wx0 - bevel, wx1 + bevel, wz0 - bevel, wz1 + bevel
    s.poly([(bx0, bz1), (bx1, bz1), (wx1, wz1), (wx0, wz1)], shade(C["frame"], -0.22))   # the top, in shadow
    s.poly([(bx0, bz0), (wx0, wz0), (wx1, wz0), (bx1, bz0)], shade(C["frame"], 0.3))    # the bottom, catching light
    s.poly([(bx0, bz0), (bx0, bz1), (wx0, wz1), (wx0, wz0)], shade(C["frame"], -0.1))
    s.poly([(bx1, bz0), (wx1, wz0), (wx1, wz1), (bx1, bz1)], shade(C["frame"], 0.12))
    s.rect(wx0, wz0, wx1, wz1, C["lcd_off"])
    img = s.image()
    return img


def window_box():
    """The LCD's window in the video's pixels (x0, y0, x1, y1)."""
    x0, x1, z0, z1 = L.FRAME["window"]
    lx0, lx1, lz0, lz1 = L.LENS
    w, h = L.LENS_PX
    return (round((x0 - lx0) / (lx1 - lx0) * w), round((lz1 - z1) / (lz1 - lz0) * h),
            round((x1 - lx0) / (lx1 - lx0) * w), round((lz1 - z0) / (lz1 - lz0) * h))


def led_glow():
    """The power light lit, and its glow on the acrylic round it: an RGBA layer the size of the video."""
    s = Sheet(L.LENS_PX, L.LENS, (0, 0, 0), ss=3)
    s.img = Image.new("RGBA", s.img.size, (255, 60, 40, 0))
    s.draw = ImageDraw.Draw(s.img)
    x, z, r = L.LED
    s.ellipse(x, z, r * 3.2, r * 3.2, (255, 60, 40, 70))
    s.img = s.img.filter(ImageFilter.GaussianBlur(r * 1.6 * s.sz))
    s.draw = ImageDraw.Draw(s.img)
    s.circle(x, z, r, (255, 64, 40, 255))
    s.circle(x - 0.3, z + 0.3, r * 0.45, (255, 200, 170, 255))
    return s.img.resize(L.LENS_PX, Image.LANCZOS)


def sheen():
    """A faint gleam across the acrylic, over everything under it."""
    w, h = L.LENS_PX
    layer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(layer).polygon([(w * 0.08, 0), (w * 0.34, 0), (w * 0.2, h), (-w * 0.06, h)], fill=16)
    return layer.filter(ImageFilter.GaussianBlur(w * 0.03))


class Lens:
    """The lens's video frames: the lens switched off, with the LCD's picture, the backlight and the light over it."""

    def __init__(self):
        self.base = lens_base()
        self.window = window_box()
        self.glow = led_glow()
        self.gleam = sheen()
        self.white = Image.new("RGB", L.LENS_PX, (255, 255, 255))

    def frame(self, lcd=None, backlight=0.0, light=0.0):
        """lcd: the LCD's 160 x 144 picture as it shows (or None for black); backlight and light: 0 (off) to 1."""
        img = self.base.copy()
        if backlight > 0:
            x0, y0, x1, y1 = self.window
            black = mix(C["lcd_off"], (12, 14, 22), backlight)
            img.paste(black, (x0, y0, x1, y1))
            if lcd is not None:
                big = lcd.resize((L.LCD_PX[2], L.LCD_PX[3]), Image.NEAREST).filter(ImageFilter.GaussianBlur(0.4))
                if backlight < 1:
                    big = Image.blend(Image.new("RGB", big.size, black), big, backlight)
                img.paste(big, L.LCD_PX[:2])
        if light > 0:
            glow = self.glow.copy()
            glow.putalpha(glow.getchannel("A").point(lambda a: round(a * light)))
            img = img.convert("RGBA")
            img.alpha_composite(glow)
            img = img.convert("RGB")
        return Image.composite(self.white, img, self.gleam)


# ---- The Game Gear's screens -----------------------------------------------------------------------------------------
# Everything here is at the LCD's 160 x 144. Its pixels are a fifth wider than they're tall, so pictures are cut to
# 4:3 before they're squeezed into it, and shapes drawn in it are drawn a fifth narrower.

W, H = L.LCD
ASPECT = 1.2


def gg_colours(img):
    """Each channel to the nearest of the Game Gear's 16 levels."""
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    return Image.fromarray((np.round(a / 17) * 17).clip(0, 255).astype(np.uint8))


def reduced(img, colours):
    """A picture in the Game Gear's colours, at most `colours` of them, no dithering (the palette that covers the
    picture's colours best, so its greys and the moon's shades survive beside the greens)."""
    img = gg_colours(img).quantize(colours, Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE)
    return gg_colours(img.convert("RGB"))


def painted_out(painting):
    """The game's painting with its own hero and knives painted out: each column carried down from the band above them
    (the bamboo and the sky run straight up and down), so the ninja drawn over it is the only one."""
    a = np.asarray(painting.convert("RGB")).copy()
    for (x0, x1), (y0, y1), (b0, b1) in (((200, 350), (148, 254), (96, 146)), ((340, 442), (176, 236), (120, 172))):
        for y in range(y0, y1):
            a[y, x0:x1] = a[b0 + (y - y0) % (b1 - b0), x0:x1]
    return Image.fromarray(a)


class Screens:
    """The made-up game's screens: its publisher's splash, its title, its play."""

    VIEW = (50.0, 420.0)        # the painting's rows the play shows (its ground, the moon, the canopy over the score)

    def __init__(self, made_up):
        stem, system = L.MADE_UP
        self.game = Game(stem, made_up, system)
        self.font = self.game.screens          # the made-up games' 5 x 7 bitmap font: font.text(...)
        field = painted_out(Image.open(self.game.painting))
        top, bottom = self.VIEW
        scale = H / (bottom - top)              # the LCD's rows a painting's pixel
        self.scale = scale
        width = round(field.width * scale / ASPECT)
        strip = field.crop((0, top, field.width, bottom)).resize((width, H), Image.LANCZOS)
        self.strip = reduced(strip, 30)
        art = self.game.keyart
        ah = round(art.width * 3 / 4)
        title = art.crop((0, round(art.height * 0.16), art.width, round(art.height * 0.16) + ah))
        self.title_art = reduced(title.resize((W, H), Image.LANCZOS).point(lambda v: round(v * 0.82)), 24)
        logo = self.game.logo
        lw = 138
        lh = round(lw * ASPECT * logo.height / logo.width)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        alpha = logo.getchannel("A").point(lambda a: 255 if a > 120 else 0)
        self.logo = reduced(logo.convert("RGB"), 14)
        self.logo.putalpha(alpha)

    # The ground under the ninja, in the painting's rows, along its width.
    @staticmethod
    def ground(px):
        return 335.0 if px < 228 else 396.0 if px < 460 else 372.0

    def text(self, img, x, y, s, colour, shadow="#000000"):
        a = np.asarray(img).copy()
        self.font.text(a, x, y, s, colour, shadow=shadow)
        return Image.fromarray(a)

    def splash(self, t):
        """The made-up publisher's splash, t frames in: its letters drop in one by one, a glint crosses them, then
        PRESENTS."""
        img = Image.new("RGB", (W, H), (0, 0, 0))
        name = self.game.publisher.upper()
        big = 8                                  # drawn at 8 times, then reduced to whole pixels
        f = ImageFont.truetype(FONTS + "ariblk.ttf", 22 * big)
        widths = [f.getlength(name[:k]) / ASPECT for k in range(len(name) + 1)]
        x0 = (W * big - widths[-1]) / 2
        layer = Image.new("RGBA", (W * big, H * big), (255, 255, 255, 0))
        top, bottom = np.array([120.0, 230.0, 255.0]), np.array([30.0, 80.0, 220.0])
        for k, ch in enumerate(name):
            u = (t - 2 * k) / 6
            if u < 0:
                continue
            e = back_out(min(1.0, u), 1.6)
            y = round((50 - 44 * (1 - e)) * big)
            letter = Image.new("L", (round(f.getlength(ch)) + 4 * big, 30 * big), 0)
            ImageDraw.Draw(letter).text((2 * big, 0), ch, font=f, fill=255)
            letter = letter.resize((max(1, round(letter.width / ASPECT)), letter.height), Image.LANCZOS)
            grad = np.linspace(0.0, 1.0, letter.height)[:, None, None]
            colour = np.broadcast_to(top * (1 - grad) + bottom * grad, (letter.height, letter.width, 3))
            fill = Image.fromarray(np.dstack([colour.astype(np.uint8), np.asarray(letter)]), "RGBA")
            outline = Image.new("RGBA", letter.size, (255, 255, 255, 0))
            outline.putalpha(letter.filter(ImageFilter.MaxFilter(2 * big + 1)))
            spot = (round(x0 + widths[k] - 2 * big / ASPECT), y - 2 * big)
            layer.alpha_composite(outline, spot)
            layer.alpha_composite(fill, spot)
        if 18 <= t < 28:                         # the glint, across the letters only
            band = Image.new("L", layer.size, 0)
            gx = (t - 18) / 10 * (W * big * 1.4) - W * big * 0.2
            ImageDraw.Draw(band).polygon([(gx, 0), (gx + 9 * big, 0), (gx - 16 * big, H * big),
                                          (gx - 25 * big, H * big)], fill=255)
            glint = Image.new("RGBA", layer.size, (255, 255, 255, 0))
            glint.putalpha(ImageChops.multiply(band, layer.getchannel("A")))
            layer.alpha_composite(glint)
        small = layer.resize((W, H), Image.BOX)
        img.paste(gg_colours(small.convert("RGB")), (0, 0), small.getchannel("A").point(lambda a: 255 if a > 100 else 0))
        if t >= 22 and not 24 <= t < 26:
            img = self.text(img, (W - 8 * 7) // 2, 92, "PRESENTS", "#9AA4B8", shadow=None)
        return img

    def title(self, t, pressed=None):
        """The title, t frames in: the key art, embers rising over it, the logo, PRESS START BUTTON blinking (fast once
        START has been pressed, pressed frames before)."""
        img = self.title_art.copy()
        d = ImageDraw.Draw(img)
        rng = random.Random(1991)
        for _ in range(26):                      # embers, drifting up
            x0, y0, speed = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 1.4)
            y = (y0 - speed * t) % H
            x = x0 + 2.5 * math.sin(t * 0.15 + y0)
            d.point((round(x) % W, round(y)), fill=(255, 170, 34) if rng.random() < 0.6 else (255, 238, 102))
        img.paste(self.logo, (round((W - self.logo.width) / 2), 4), self.logo)
        blink = (t % 4) < 2 if pressed is not None else (t % 20) < 13
        if blink:
            img = self.text(img, (W - 18 * 7) // 2, 104, "PRESS START BUTTON", "#FFFFFF")
        line = self.game.year + " " + self.game.publisher.upper()
        return self.text(img, (W - len(line) * 7) // 2, 128, line, "#BBBBBB")

    def ninja(self, pose, phase):
        """The ninja facing right, its feet's middle at the bottom middle of its picture: pose "stand", "run" (phase
        0 to 1 through a stride), "jump" (phase 0 to 1 through the leap) or "throw"; drawn at 8 times in shapes, then
        reduced to whole pixels in four colours."""
        k = 8
        w, h = 34, 44
        img = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        suit, lit, red, skin = (34, 34, 85), (102, 119, 204), (238, 34, 34), (238, 204, 153)

        def p(x, y):                                     # display units from the feet (y up), squeezed into LCD pixels
            return ((w / 2 + x / ASPECT) * k, (h - 1 - y) * k)

        def limb(a, b, width, colour):
            d.line([p(*a), p(*b)], fill=colour, width=round(width * k))
            for q in (a, b):
                x, y = p(*q)
                r = width * k / 2
                d.ellipse([x - r, y - r, x + r, y + r], fill=colour)

        def leg(hip, thigh, shin, colour):
            knee = (hip[0] + 9 * math.sin(math.radians(thigh)), hip[1] - 9 * math.cos(math.radians(thigh)))
            foot = (knee[0] + 9 * math.sin(math.radians(shin)), knee[1] - 9 * math.cos(math.radians(shin)))
            limb(hip, knee, 4.2, colour)
            limb(knee, foot, 3.6, colour)
            d.polygon([p(foot[0] - 1.5, foot[1] - 0.5), p(foot[0] + 3.6, foot[1] - 0.5), p(foot[0] + 3.0, foot[1] + 1.6),
                       p(foot[0] - 1.5, foot[1] + 1.6)], fill=colour)

        def arm(shoulder, upper, fore, colour):
            elbow = (shoulder[0] + 6.5 * math.sin(math.radians(upper)), shoulder[1] - 6.5 * math.cos(math.radians(upper)))
            hand = (elbow[0] + 6 * math.sin(math.radians(fore)), elbow[1] - 6 * math.cos(math.radians(fore)))
            limb(shoulder, elbow, 3.2, colour)
            limb(elbow, hand, 2.8, colour)
            return hand

        lift, lean = 0.0, 8.0
        if pose == "run":
            s = math.sin(2 * math.pi * phase)
            c = math.cos(2 * math.pi * phase)
            legs = [(32 * s, 32 * s - 50 * max(0.0, -c) - 12), (-32 * s, -32 * s - 50 * max(0.0, c) - 12)]
            arms = [(-38 * s + 10, -38 * s + 80), (38 * s + 10, 38 * s + 80)]
            lift = 1.2 * abs(c)
            lean = 14.0
        elif pose == "jump":
            tuck = math.sin(math.pi * min(1.0, phase * 1.4))
            legs = [(65 * tuck, -30 * tuck), (-30 * tuck, -100 * tuck)]   # a knee up in front, the far leg trailing
            arms = [(-60, 20), (120, 160)]
            lean = 10.0 + 10 * tuck
        elif pose == "throw":
            legs = [(28, 10), (-30, -40)]
            arms = [(95, 92), (-40, 20)]                                   # the near arm thrown forward
            lean = 16.0
        else:
            legs = [(8, 0), (-8, 0)]
            arms = [(-10, 30), (20, 60)]
        hip = (0.0, 19.0 + lift)
        tilt = math.radians(lean)
        neck = (hip[0] + 11 * math.sin(tilt), hip[1] + 11 * math.cos(tilt))
        head = (neck[0] + 3.4 * math.sin(tilt), neck[1] + 4.6)
        # The scarf, streaming back from the neck in a wave.
        wave = [(neck[0] - 1.5 - 1.9 * j, neck[1] - 0.4 + 0.6 * j / 3 + 1.6 * math.sin(phase * 2 * math.pi * 2 + j * 0.9))
                for j in range(9)]
        d.polygon([p(x, y + 1.3) for x, y in wave] + [p(x, y - 1.0) for x, y in reversed(wave)], fill=red)
        leg(hip, legs[1][0], legs[1][1], suit)              # the far leg and arm, then the body, then the near ones
        arm((neck[0] - 0.5, neck[1] - 1.0), arms[1][0], arms[1][1], suit)
        limb(hip, neck, 7.0, suit)
        limb((hip[0] + 1.8, hip[1] + 1.0), (neck[0] + 1.8, neck[1] - 1.0), 2.2, lit)
        d.line([p(hip[0] - 3.2, hip[1] + 0.6), p(hip[0] + 3.4, hip[1] + 0.6)], fill=red, width=round(1.8 * k))
        leg(hip, legs[0][0], legs[0][1], suit)
        hand = arm((neck[0] + 0.5, neck[1] - 1.2), arms[0][0], arms[0][1], suit)
        x, y = p(*head)
        r = 4.3 * k
        d.ellipse([x - r / ASPECT, y - r, x + r / ASPECT, y + r], fill=suit)
        d.rectangle([p(head[0] + 0.4, head[1] + 1.0)[0], p(head[0] + 0.4, head[1] + 1.0)[1],
                     p(head[0] + 4.2, head[1] - 0.6)[0], p(head[0] + 4.2, head[1] - 0.6)[1]], fill=skin)
        d.rectangle([p(head[0] + 2.0, head[1] + 0.6)[0], p(head[0] + 2.0, head[1] + 0.6)[1],
                     p(head[0] + 3.0, head[1] - 0.2)[0], p(head[0] + 3.0, head[1] - 0.2)[1]], fill=(0, 0, 0))
        small = img.resize((w, h), Image.BOX)
        alpha = small.getchannel("A").point(lambda a: 255 if a > 110 else 0)
        palette = Image.new("P", (1, 1))
        flat = [c for colour in (suit, lit, red, skin, (0, 0, 0)) for c in colour]
        palette.putpalette(flat + flat[:3] * (256 - 5))
        sprite = gg_colours(small.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB"))
        sprite.putalpha(alpha)
        return sprite, (round(w / 2 + (hand[0]) / ASPECT), round(h - 1 - hand[1]))


def kunai():
    """A throwing knife, flying right: its blade, its ring and its red tassel."""
    img = Image.new("RGBA", (9, 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(4, 1), (8, 1)], fill=(221, 221, 238))
    d.point((8, 1), fill=(255, 255, 255))
    d.line([(2, 1), (3, 1)], fill=(68, 68, 85))
    d.point((1, 0), fill=(221, 34, 34))
    d.point((0, 2), fill=(221, 34, 34))
    return img


def spark(t):
    """A knife striking home, t frames in (0 to 5): a star of light opening and fading."""
    img = Image.new("RGBA", (13, 11), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = 1 + t
    colour = (255, 255, 255) if t < 2 else (255, 238, 102) if t < 4 else (255, 136, 34)
    d.line([(6 - r, 5), (6 + r, 5)], fill=colour)
    d.line([(6, 5 - r), (6, 5 + r)], fill=colour)
    if t >= 1:
        q = max(1, r - 2)
        d.line([(6 - q, 5 - q), (6 + q, 5 + q)], fill=colour)
        d.line([(6 - q, 5 + q), (6 + q, 5 - q)], fill=colour)
    return img


def lens_still(out):
    Lens().frame().save(out, optimize=True)


if __name__ == "__main__":
    made_up, folder = (os.path.abspath(a) for a in sys.argv[1:3])
    os.makedirs(folder, exist_ok=True)
    stem, system = L.MADE_UP
    print_atlas(Game(stem, made_up, system), os.path.join(folder, "game_gear_print.png"))
    lens_still(os.path.join(folder, "game_gear_lens.png"))
    print("Game Gear: print and lens")
