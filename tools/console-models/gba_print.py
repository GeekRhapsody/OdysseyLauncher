"""The Game Boy Advance's printing and its screen, for the console theme's Game Boy Advance card (gba.py). gba_layout.py
has the measurements and where each part is in the atlas.

Writes two images into a folder:
- gba_print.png: the face seen square on (the indigo plastic; the embossed Nintendo, the START and SELECT plates and
  POWER; the wells round the D-pad, A, B, START and SELECT; the light's window; the speaker's slots), the back seen
  from behind (the cartridge bay's panel, the sticker, the battery cover with its GAME BOY, the screws), the
  cartridge's two sides (a made-up game, Kaleidrop, on its label), the tops of A, B and the D-pad, and swatches.
- gba_screen.png: the lens with the screen switched off: the texture of the model's `video` material, shown while its
  video doesn't play, and the video's first and last frames.

The screen's drawing is shared with gba_video.py, which draws the card's video with it: the lens (lens()), its LCD
(lcd(): a reflective screen with no light of its own, so its black is a dark olive grey and its white a pale grey),
the start-up (boot()), and Kaleidrop (made up, from tools/made-up-games: its logo, its key art and its gems) with its
title (title()) and a round of play (play()): pairs of gems falling into a well, moved and turned by the clip's
presses (gba_layout.INPUTS), three of a colour in a row shattering.

Run it with the system Python (Pillow, numpy):

    python tools/console-models/gba_print.py artifacts/made-up-games artifacts/gba
"""

import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gba_layout as L  # noqa: E402

FONTS = "C:/Windows/Fonts/"
SS = 4                  # supersampling while drawing the atlas's regions


def rgb(hex_colour, scale=1.0):
    return tuple(max(0, min(255, round(int(hex_colour[i:i + 2], 16) * scale))) for i in (1, 3, 5))


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def font(name, px):
    return ImageFont.truetype(FONTS + name, max(1, round(px)))


C = {name: rgb(value) for name, value in L.COLOURS.items()}


# ---- A region of the atlas, drawn in millimetres ---------------------------------------------------------------------

class Canvas:
    """A region drawn in millimetres, x to the right and z up over box (x0, x1, z0, z1), supersampled, then pasted
    into the atlas with a margin of its own edge's pixels."""

    def __init__(self, rect, box, fill):
        self.rect, self.box = rect, box
        self.img = Image.new("RGBA", (rect[2] * SS, rect[3] * SS), fill + (255,))
        self.draw = ImageDraw.Draw(self.img)
        self.sx = rect[2] * SS / (box[1] - box[0])
        self.sz = rect[3] * SS / (box[3] - box[2])

    def p(self, x, z):
        return ((x - self.box[0]) * self.sx, (self.box[3] - z) * self.sz)

    def poly(self, points, fill, draw=None):
        (draw or self.draw).polygon([self.p(x, z) for x, z in points], fill=fill)

    def ellipse(self, x, z, rx, rz, fill=None, outline=None, width=0.0, draw=None):
        (x0, y0), (x1, y1) = self.p(x - rx, z + rz), self.p(x + rx, z - rz)
        (draw or self.draw).ellipse([x0, y0, x1, y1], fill=fill, outline=outline,
                                    width=max(1, round(width * self.sx)) if outline else 0)

    def line(self, points, fill, width, draw=None):
        (draw or self.draw).line([self.p(x, z) for x, z in points], fill=fill, width=max(1, round(width * self.sx)))

    def layer(self):
        return Image.new("RGBA", self.img.size, (0, 0, 0, 0))

    def over(self, layer):
        self.img.alpha_composite(layer)

    def text(self, s, name, size, x, z, fill, anchor="mm", stretch=1.0, slant=0.0, turn=0.0):
        """Text size mm high (the font's em), its anchor at (x, z); stretched wide, slanted (a shear, + leaning
        right) or turned (degrees anticlockwise)."""
        f = font(name, size * self.sz)
        box = f.getbbox(s)
        pad = round(size * self.sz)
        tile = Image.new("L", (box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad), 0)
        ImageDraw.Draw(tile).text((pad - box[0], pad - box[1]), s, font=f, fill=255)
        if stretch != 1.0:
            tile = tile.resize((round(tile.width * stretch), tile.height), Image.LANCZOS)
        if slant:
            k = math.tan(math.radians(slant))
            tile = tile.transform((tile.width + round(abs(k) * tile.height), tile.height), Image.AFFINE,
                                  (1, k, -k * tile.height if k > 0 else 0, 0, 1, 0), Image.BICUBIC)
        if turn:
            tile = tile.rotate(turn, Image.BICUBIC, expand=True)
        cx, cy = self.p(x, z)
        w, h = tile.size
        ox = {"l": cx - pad * stretch, "m": cx - w / 2, "r": cx - w + pad * stretch}[anchor[0]]
        layer = self.layer()
        layer.paste(Image.new("RGBA", tile.size, fill + (255,)), (round(ox), round(cy - h / 2)), tile)
        self.over(layer)

    def embossed(self, paint, base, light=0.12, shade=0.22, offset=0.12):
        """A moulded shape: paint(shifted, draw, colour) drawn in shadow down and right, in light up and left, then
        in base (a negative offset sinks it instead)."""
        for dx, dz, colour in ((offset, -offset, mix(base, (0, 0, 0), shade)),
                               (-offset, offset, mix(base, (255, 255, 255), light)), (0.0, 0.0, base)):
            layer = self.layer()
            paint(Shifted(self, dx, dz, layer), ImageDraw.Draw(layer), colour + (255,))
            self.over(layer)

    def paste(self, atlas):
        x, y, w, h = self.rect
        small = np.asarray(self.img.convert("RGB").resize((w, h), Image.LANCZOS))
        padded = Image.fromarray(np.pad(small, ((L.PAD, L.PAD), (L.PAD, L.PAD), (0, 0)), mode="edge"))
        atlas.paste(padded, (x - L.PAD, y - L.PAD))


class Shifted:
    """A canvas's drawing moved by (dx, dz) millimetres onto a layer, for embossed()."""

    def __init__(self, canvas, dx, dz, layer):
        self.c, self.dx, self.dz, self.layer = canvas, dx, dz, layer

    def poly(self, points, fill, draw):
        self.c.poly([(x + self.dx, z + self.dz) for x, z in points], fill, draw)

    def ellipse(self, x, z, rx, rz, fill=None, outline=None, width=0.0, draw=None):
        self.c.ellipse(x + self.dx, z + self.dz, rx, rz, fill, outline, width, draw)

    def line(self, points, fill, width, draw):
        self.c.line([(x + self.dx, z + self.dz) for x, z in points], fill, width, draw)

    def text(self, draw, s, name, size, x, z, fill, **kw):
        keep = self.c.img
        self.c.img = self.layer
        self.c.text(s, name, size, x + self.dx, z + self.dz, fill[:3], **kw)
        self.c.img = keep


# ---- Shapes -------------------------------------------------------------------------------------------------------------

def circle(x, z, r, n=48):
    return [(x + r * math.cos(2 * math.pi * k / n), z + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def stadium(x, z, length, width, degrees=0.0, n=10):
    r = width / 2
    half = length / 2 - r
    pts = [(half + r * math.cos(math.radians(-90 + 180 * k / n)), r * math.sin(math.radians(-90 + 180 * k / n)))
           for k in range(n + 1)]
    pts += [(-half + r * math.cos(math.radians(90 + 180 * k / n)), r * math.sin(math.radians(90 + 180 * k / n)))
            for k in range(n + 1)]
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [(x + px * c - pz * s, z + px * s + pz * c) for px, pz in pts]


def cross(x, z, arm, half):
    return [(x + arm, z - half), (x + arm, z + half), (x + half, z + half), (x + half, z + arm), (x - half, z + arm),
            (x - half, z + half), (x - arm, z + half), (x - arm, z - half), (x - half, z - half), (x - half, z - arm),
            (x + half, z - arm), (x + half, z - half)]


def rounded_rect(x0, z0, x1, z1, r, n=6):
    pts = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        pts += [(cx + r * math.cos(math.radians(a0 + 90 * k / n)), cz + r * math.sin(math.radians(a0 + 90 * k / n)))
                for k in range(n + 1)]
    return pts


# ---- The face ---------------------------------------------------------------------------------------------------------

def face(atlas):
    cv = Canvas(L.REGIONS["face"], L.FACE_BOX, C["case"])
    well = mix(C["case"], (8, 6, 30), 0.72)

    # The wells round the controls: a dark gap round each, a little wider than it.
    x, z = L.DPAD["at"]
    cv.poly(cross(x, z, L.DPAD["arm"] + 0.7, L.DPAD["half"] + 0.7), well + (255,))
    for key in ("a", "b"):
        bx, bz = L.BUTTONS[key]
        cv.ellipse(bx, bz, L.BUTTONS["r"] + 0.6, L.BUTTONS["r"] + 0.6, fill=well + (255,))
    for key in ("start", "select"):
        sx, sz = L.SMALL[key]
        cv.ellipse(sx, sz, L.SMALL["r"] + 0.5, L.SMALL["r"] + 0.5, fill=well + (255,))

    # START and SELECT's plates: slanting pills, their names moulded in them.
    w, h = L.PLATES["size"]
    for key, name in (("start", "START"), ("select", "SELECT")):
        px, pz = L.PLATES[key]
        pill = stadium(px, pz, w, h, L.PLATES["slant"])
        cv.embossed(lambda s, d, col, pill=pill: s.poly(pill, col, d), C["case"], light=0.18, shade=0.3, offset=0.16)
        cv.poly(stadium(px, pz, w - 0.6, h - 0.6, L.PLATES["slant"]), mix(C["case"], (0, 0, 0), 0.06) + (255,))
        cv.embossed(lambda s, d, col, px=px, pz=pz, name=name: s.text(d, name, "FRAHVIT.TTF", 2.5, px + 0.4, pz - 0.15,
                                                                       col, turn=L.PLATES["slant"]),
                    mix(C["case"], (255, 255, 255), 0.1), light=0.25, shade=0.35, offset=0.1)

    # Nintendo, moulded in its racetrack.
    nx, nz = L.NINTENDO["at"]
    nw, nh = L.NINTENDO["size"]
    track = stadium(nx, nz, nw, nh, 0.0, 16)
    inner = stadium(nx, nz, nw - 0.8, nh - 0.8, 0.0, 16)
    cv.embossed(lambda s, d, col: s.poly(track, col, d), C["case"], light=0.2, shade=0.3, offset=0.14)
    cv.poly(inner, C["case"] + (255,))
    cv.embossed(lambda s, d, col: s.text(d, "Nintendo", "ariblk.ttf", 3.1, nx, nz - 0.1, col, stretch=0.92),
                C["case"], light=0.22, shade=0.32, offset=0.12)

    # The POWER light's window, and its name.
    lx, lz = L.LED["at"]
    cv.ellipse(lx, lz, L.LED["r"] + 0.35, L.LED["r"] + 0.35, fill=well + (255,))
    cv.ellipse(lx, lz, L.LED["r"], L.LED["r"], fill=C["led_off"] + (255,))
    cv.embossed(lambda s, d, col: s.text(d, "POWER", "FRAHV.TTF", 2.1, lx + 2.3, lz - 0.05, col, anchor="lm",
                                         stretch=0.95), C["case"], light=0.2, shade=0.35, offset=0.1)

    # The speaker's slots, slanting.
    sw, sh = L.SPEAKER["size"]
    for x, z in L.SPEAKER["at"]:
        cv.poly(stadium(x + 0.12, z - 0.12, sw, sh + 0.25, L.SPEAKER["slant"]), mix(C["case"], (255, 255, 255), 0.18) + (255,))
        cv.poly(stadium(x, z, sw, sh, L.SPEAKER["slant"]), (14, 12, 30, 255))
    cv.paste(atlas)


# ---- The back -----------------------------------------------------------------------------------------------------------

def back(atlas):
    """The back seen from behind: u is -x, so its left is the console's right."""
    cv = Canvas(L.REGIONS["back"], L.FACE_BOX, C["case"])
    groove = mix(C["case"], (0, 0, 0), 0.45)
    # The cartridge bay's panel over the slot.
    cv.poly(rounded_rect(-27.5, 60.5, 27.5, 73.8, 1.2), mix(C["case"], (0, 0, 0), 0.08) + (255,))
    cv.line(rounded_rect(-27.5, 60.5, 27.5, 73.8, 1.2) + [rounded_rect(-27.5, 60.5, 27.5, 73.8, 1.2)[0]], groove + (255,), 0.25)
    # The battery cover, its latch, and GAME BOY moulded in it.
    cover = rounded_rect(-31.3, 1.5, 31.3, 45.2, 2.5)
    cv.line(cover + [cover[0]], groove + (255,), 0.35)
    cv.poly(rounded_rect(-7.0, 40.5, 7.0, 45.2, 0.8), mix(C["case"], (0, 0, 0), 0.12) + (255,))
    cv.poly(rounded_rect(-4.5, 43.0, 4.5, 44.4, 0.4), groove + (255,))
    cv.poly(rounded_rect(-20.0, 13.5, 20.0, 25.0, 1.5), mix(C["case"], (0, 0, 0), 0.05) + (255,))
    cv.embossed(lambda s, d, col: s.text(d, "GAME BOY", "FRAHVIT.TTF", 6.2, 0.0, 19.2, col, stretch=1.05),
                C["case"], light=0.2, shade=0.35, offset=0.18)
    # The sticker.
    cv.poly(rounded_rect(-37.0, 46.0, 37.0, 59.6, 0.6), C["sticker"] + (255,))
    ink = (214, 216, 220)
    cv.text("GAME BOY", "FRAHVIT.TTF", 2.1, -35.5, 57.6, ink, anchor="lm")
    cv.text("ADVANCE", "ariblk.ttf", 1.6, -24.2, 57.6, ink, anchor="lm", stretch=1.5)
    cv.text("MODEL NO. AGB-001", "arialbd.ttf", 1.55, -10.0, 57.6, ink, anchor="lm")
    cv.poly(rounded_rect(14.5, 55.8, 36.0, 59.2, 0.3), (232, 232, 234, 255))
    cv.text("AC10326571", "ariblk.ttf", 2.2, 25.2, 57.5, (40, 40, 44), stretch=0.9)
    for k, line in enumerate(("© 2001 Nintendo  Patents issued and pending.", "RATING: 3V = 0.6W  BATTERY: LR6 (AA) 1.5V x 2",
                              "MADE IN CHINA")):
        cv.text(line, "arial.ttf", 1.15, -35.5, 54.6 - 1.9 * k, ink, anchor="lm")
    cv.text("CE", "arialbd.ttf", 2.6, 19.0, 51.0, ink)
    cv.ellipse(27.5, 51.0, 3.0, 2.0, outline=ink + (255,), width=0.25)
    cv.text("AGB-EUR", "arialbd.ttf", 1.2, 35.5, 47.4, ink, anchor="r")
    # The screws: brass at the corners, dark holes between.
    for x, z, brass in ((37.0, 78.6, True), (-37.0, 78.6, True), (49.0, 67.7, False), (-49.0, 67.7, False),
                        (66.0, 23.0, True), (-66.0, 23.0, True)):
        cv.ellipse(x, z, 1.7, 1.7, fill=(20, 18, 40, 255))
        if brass:
            cv.ellipse(x, z, 1.25, 1.25, fill=(176, 146, 72, 255))
            cv.line([(x - 0.8, z), (x + 0.8, z)], (92, 72, 30, 255), 0.25)
            cv.line([(x, z - 0.8), (x, z + 0.8)], (92, 72, 30, 255), 0.25)
    cv.paste(atlas)


# ---- The cartridge ----------------------------------------------------------------------------------------------------

def cart_box():
    w, h = L.CART["width"], L.CART["height"]
    return (-w / 2, w / 2, 0.0, h)


def label_art(made_up):
    """The label's picture: Kaleidrop's key art with its logo, landscape."""
    root = os.path.join(made_up, "library", "media", L.MADE_UP[1])
    stem = L.MADE_UP[0]
    art = Image.open(os.path.join(made_up, "paintings", "kaleidrop", "keyart.png")).convert("RGB")
    logo = Image.open(os.path.join(root, "logos", stem + ".png")).convert("RGBA")
    return art, logo


def label(atlas, made_up):
    """The label side, as the cartridge stands with its contacts down: the moulded band with GAME BOY ADVANCE along its
    top, the label, the arrow under it."""
    cv = Canvas(L.REGIONS["label"], cart_box(), C["cart"])
    w, h = L.CART["width"], L.CART["height"]
    # The band at the top: a raised arc, GAME BOY ADVANCE moulded along it.
    arc = [(-w / 2 + 3.0, 27.6)] + [(x, 27.6 + 2.6 * (1 - (x / (w / 2 - 3.0)) ** 2)) for x in np.linspace(-w / 2 + 3, w / 2 - 3, 25)] \
        + [(w / 2 - 3.0, 27.6), (w / 2 - 3.0, 33.4), (-w / 2 + 3.0, 33.4)]
    cv.embossed(lambda s, d, col: s.poly(arc, col, d), C["cart"], light=0.15, shade=0.3, offset=0.15)
    cv.embossed(lambda s, d, col: s.text(d, "GAME BOY ADVANCE", "FRAHVIT.TTF", 2.0, 0.0, 31.6, col, stretch=1.1),
                C["cart"], light=0.18, shade=0.3, offset=0.08)
    # The arrow, pointing in.
    cv.embossed(lambda s, d, col: s.poly([(-3.0, 2.4), (3.0, 2.4), (0.0, 0.8)], col, d), C["cart"], light=0.2, shade=0.3)
    # The label: paper, the art, its top strip with GAME BOY ADVANCE.
    x0, x1, z0, z1 = L.LABEL["rect"]
    cv.poly(rounded_rect(x0 - 0.5, z0 - 0.5, x1 + 0.5, z1 + 0.5, L.LABEL["r"] + 0.4), mix(C["cart"], (0, 0, 0), 0.3) + (255,))
    cv.poly(rounded_rect(x0, z0, x1, z1, L.LABEL["r"]), C["label_paper"] + (255,))
    art, logo = label_art(made_up)
    ax0, ax1, az0, az1 = x0 + 0.7, x1 - 0.7, z0 + 0.7, z1 - 3.4
    (px0, py0), (px1, py1) = cv.p(ax0, az1), cv.p(ax1, az0)
    aw, ah = round(px1 - px0), round(py1 - py0)
    k = max(aw / art.width, ah / art.height)
    pic = art.resize((round(art.width * k), round(art.height * k)), Image.LANCZOS)
    left, top = (pic.width - aw) // 2, int((pic.height - ah) * 0.62)
    pic = pic.crop((left, top, left + aw, top + ah)).convert("RGBA")
    lw = round(aw * 0.84)
    lg = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    pic.alpha_composite(lg, ((aw - lw) // 2, round(ah * 0.07)))
    mask = Image.new("L", (aw, ah), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, aw - 1, ah - 1], radius=round(1.2 * cv.sx), fill=255)
    cv.img.paste(pic, (round(px0), round(py0)), mask)
    cv.text("GAME BOY", "FRAHVIT.TTF", 2.0, x0 + 1.2, z1 - 1.55, (38, 44, 120), anchor="lm")
    cv.text("ADVANCE", "ariblk.ttf", 1.4, x0 + 11.6, z1 - 1.55, (38, 44, 120), anchor="lm", stretch=1.5)
    cv.text("Velvet Comet", "arialbi.ttf", 1.5, x1 - 1.2, z1 - 1.55, (80, 80, 92), anchor="rm")
    cv.paste(atlas)


def plain(atlas):
    """The other side, as it's seen when the cartridge shows its back: a recessed panel, Nintendo moulded over it."""
    cv = Canvas(L.REGIONS["plain"], cart_box(), C["cart"])
    w, h = L.CART["width"], L.CART["height"]
    cv.embossed(lambda s, d, col: s.poly(rounded_rect(-w / 2 + 4.0, 3.5, w / 2 - 4.0, 27.5, 2.0), col, d),
                mix(C["cart"], (0, 0, 0), 0.06), light=0.15, shade=0.25, offset=-0.15)
    cv.embossed(lambda s, d, col: s.text(d, "Nintendo", "ariblk.ttf", 2.6, 0.0, 31.0, col), C["cart"], light=0.18, shade=0.3)
    cv.paste(atlas)


# ---- The buttons' tops ------------------------------------------------------------------------------------------------

def button_top(atlas, key, letter):
    r = L.BUTTONS["r"]
    cv = Canvas(L.REGIONS["btn_" + key], (-r, r, -r, r), C["grey"])
    cv.embossed(lambda s, d, col: s.text(d, letter, "FRAHV.TTF", 4.6, 0.1, -0.1, col), C["grey"], light=0.35, shade=0.22,
                offset=0.14)
    cv.paste(atlas)


def dpad_top(atlas):
    a = L.DPAD["arm"]
    cv = Canvas(L.REGIONS["dpad"], (-a, a, -a, a), C["grey"])
    tip = a - 2.2
    for turn in range(4):
        c, s = math.cos(math.pi / 2 * turn), math.sin(math.pi / 2 * turn)
        tri = [(tip + 0.9, 0.0), (tip - 0.5, 1.1), (tip - 0.5, -1.1)]
        pts = [(x * c - z * s, x * s + z * c) for x, z in tri]
        cv.embossed(lambda sh, d, col, pts=pts: sh.poly(pts, col, d), C["grey"], light=0.3, shade=0.18, offset=-0.1)
    cv.embossed(lambda sh, d, col: sh.ellipse(0.0, 0.0, 1.8, 1.8, fill=col, draw=d), C["grey"], light=0.3, shade=0.2,
                offset=-0.12)
    cv.paste(atlas)


def swatches(atlas):
    d = ImageDraw.Draw(atlas)
    for name, (x, y) in L.SWATCHES.items():
        colour = (0, 0, 0) if name == "black" else C[name]
        d.rectangle([x - 12, y - 12, x + 12, y + 12], fill=colour)


def print_atlas(made_up, out):
    atlas = Image.new("RGB", (L.ATLAS, L.ATLAS), C["case"])
    face(atlas)
    back(atlas)
    label(atlas, made_up)
    plain(atlas)
    button_top(atlas, "a", "A")
    button_top(atlas, "b", "B")
    dpad_top(atlas)
    swatches(atlas)
    atlas.save(out, optimize=True)


# ---- The lens and its LCD -----------------------------------------------------------------------------------------------

def lens():
    """The lens at VIDEO_PX, the screen's pixels left for lcd(): the dark plastic, a faint sheen, the LCD's border in
    the window, GAME BOY ADVANCE under it."""
    w, h = L.VIDEO_PX
    s = 4
    img = Image.new("RGB", (w * s, h * s), C["lens"])
    d = ImageDraw.Draw(img)
    # The window: the LCD's dark border round its pixels.
    ww, wh, wr = L.WINDOW
    cx, cz = L.SCREEN_CENTRE
    (x0, y0), (x1, y1) = L.lens_px(cx - ww / 2, cz + wh / 2), L.lens_px(cx + ww / 2, cz - wh / 2)
    d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=wr * L.PX_MM * s, fill=C["window"])
    # GAME BOY ADVANCE: GAME BOY heavy and slanting, ADVANCE wide and outlined, the pair centred under the window.
    ink = (214, 214, 220)
    tz = 15.4
    big = font("FRAHVIT.TTF", 4.1 * L.PX_MM * s)
    gw = d.textlength("GAME BOY", font=big)
    adv = Image.new("L", (round(30 * L.PX_MM * s), round(6 * L.PX_MM * s)), 0)
    ImageDraw.Draw(adv).text((adv.width * 0.02, adv.height / 2), "ADVANCE", font=font("ariblk.ttf", 2.75 * L.PX_MM * s),
                             fill=255, anchor="lm")
    adv = adv.crop(adv.getbbox())
    adv = adv.resize((round(adv.width * 1.38), adv.height), Image.LANCZOS)
    gap = 1.0 * L.PX_MM * s
    total = gw + gap + adv.width
    gx, gy = L.lens_px(0.0, tz)
    left = gx * s - total / 2
    d.text((left, gy * s), "GAME BOY", font=big, fill=ink, anchor="lm", stroke_width=round(0.22 * L.PX_MM * s),
           stroke_fill=(20, 20, 24))
    edge = adv.filter(ImageFilter.MaxFilter(5))
    ring = ImageChops.subtract(edge, adv.filter(ImageFilter.MinFilter(5)))
    ax = round(left + gw + gap)
    ay = round(gy * s - adv.height / 2 + 0.2 * L.PX_MM * s)
    img.paste(Image.new("RGB", edge.size, (20, 20, 24)), (ax, ay), edge)
    img.paste(Image.new("RGB", adv.size, mix(C["lens"], ink, 0.25)), (ax, ay), adv)
    img.paste(Image.new("RGB", ring.size, ink), (ax, ay), ring)
    img = img.resize((w, h), Image.LANCZOS)
    # A faint sheen across its upper left.
    sheen = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sheen).polygon([(-w * 0.1, h * 0.05), (w * 0.45, -h * 0.1), (w * 0.15, h * 0.75), (-w * 0.2, h * 0.9)],
                                  fill=10)
    sheen = sheen.filter(ImageFilter.GaussianBlur(w * 0.05))
    return Image.composite(Image.new("RGB", (w, h), (255, 255, 255)), img, sheen)


LCD_BLACK = np.array([24, 27, 24], np.float32)    # the LCD's darkest, switched on
LCD_WHITE = np.array([202, 206, 190], np.float32)  # its lightest: lit only by the room
LCD_OFF = np.array(C["lcd_off"], np.float32)


def lcd(content, level=1.0):
    """The screen's 240 x 160 picture as the LCD shows it, at VIDEO_SCALE: level 0 is the screen switched off, 1 on."""
    a = np.asarray(content.convert("RGB"), np.float32) / 255.0
    grey = a.mean(axis=2, keepdims=True)
    a = a * 0.88 + grey * 0.12                       # a reflective LCD's colours, a little washed
    on = LCD_BLACK + np.power(a, 1.12) * (LCD_WHITE - LCD_BLACK)
    out = LCD_OFF + (on - LCD_OFF) * level
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    return img.resize((L.SCREEN_PX[0] * L.VIDEO_SCALE, L.SCREEN_PX[1] * L.VIDEO_SCALE), Image.NEAREST)


def frame(base, content=None, level=0.0):
    """The lens with the screen showing content (None: switched off)."""
    out = base.copy()
    if content is None or level <= 0.0:
        shown = Image.new("RGB", (L.SCREEN_PX[0] * L.VIDEO_SCALE, L.SCREEN_PX[1] * L.VIDEO_SCALE), C["lcd_off"])
    else:
        shown = lcd(content, level)
    out.paste(shown, L.SCREEN_AT)
    return out


# ---- The start-up -----------------------------------------------------------------------------------------------------

def _supersampled(draw_fn, s=4):
    w, h = L.SCREEN_PX
    img = Image.new("RGB", (w * s, h * s), (255, 255, 255))
    draw_fn(img, ImageDraw.Draw(img), s)
    return img.resize((w, h), Image.LANCZOS)


GAME_BOY_BLUE = (36, 52, 196)


def boot(t):
    """The start-up, t frames after the screen lights: white; a light sweeps round and GAME BOY appears behind it,
    letter by letter; a shine runs over it; Nintendo comes in under it; everything goes to white."""
    letters = "GAME BOY"

    def draw(img, d, s):
        f = font("FRAHVIT.TTF", 30 * s)
        total = d.textlength(letters, font=f)
        x = 120 * s - total / 2
        y = 70 * s
        sweep = (t - 6) / 24.0                            # the light's progress over the letters
        for k, ch in enumerate(letters):
            cw = d.textlength(ch, font=f)
            appear = min(1.0, max(0.0, (sweep * (len(letters) + 2) - k) / 2.0))
            if ch != " " and appear > 0:
                colour = mix((255, 255, 255), GAME_BOY_BLUE, appear)
                d.text((x, y), ch, font=f, fill=colour, anchor="ls")
            x += cw
        # The light: a glowing ball on an ellipse round the letters, while they appear.
        if 4 <= t < 34:
            a = math.pi * (1.1 - 1.2 * min(1.0, (t - 4) / 28.0))
            bx, by = 120 + 92 * math.cos(a), 60 - 30 * math.sin(a)
            glow = Image.new("L", img.size, 0)
            ImageDraw.Draw(glow).ellipse([(bx - 9) * s, (by - 9) * s, (bx + 9) * s, (by + 9) * s], fill=255)
            glow = glow.filter(ImageFilter.GaussianBlur(5 * s))
            img.paste(Image.new("RGB", img.size, (150, 180, 255)), (0, 0), glow)
            d.ellipse([(bx - 3) * s, (by - 3) * s, (bx + 3) * s, (by + 3) * s], fill=(235, 245, 255))
        # The shine over the letters.
        if 32 <= t < 44:
            p = (t - 32) / 12.0
            band = Image.new("L", img.size, 0)
            cx = (20 + 200 * p) * s
            ImageDraw.Draw(band).polygon([(cx - 10 * s, 40 * s), (cx + 4 * s, 40 * s), (cx - 6 * s, 80 * s), (cx - 20 * s, 80 * s)],
                                         fill=150)
            mask = Image.new("L", img.size, 0)
            ImageDraw.Draw(mask).text((120 * s - total / 2, y), letters, font=f, fill=255, anchor="ls")
            band = ImageChops.multiply(band, mask)
            img.paste(Image.new("RGB", img.size, (210, 225, 255)), (0, 0), band)
        # Nintendo, in its racetrack, fading in.
        if t >= 38:
            fade = min(1.0, (t - 38) / 12.0)
            grey = mix((255, 255, 255), (120, 120, 126), fade)
            nf = font("ariblk.ttf", 11 * s)
            d.rounded_rectangle([88 * s, 103 * s, 152 * s, 121 * s], radius=9 * s, outline=grey, width=round(1.4 * s))
            d.text((120 * s, 112 * s), "Nintendo", font=nf, fill=grey, anchor="mm")
            d.text((155 * s, 104 * s), "®", font=font("arial.ttf", 6 * s), fill=grey, anchor="lm")

    img = _supersampled(draw)
    if t >= 58:                                         # to white, for the game
        img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), min(1.0, (t - 58) / 8.0))
    return img


# ---- Kaleidrop --------------------------------------------------------------------------------------------------------

GEM_COLOURS = {"R": (232, 40, 56), "O": (248, 136, 24), "Y": (248, 216, 40), "G": (48, 200, 80), "B": (40, 120, 248),
               "V": (168, 72, 232)}
GEM_SHAPES = {
    "R": None,
    "O": [(1, 1), (10, 1), (10, 10), (1, 10)],
    "Y": [(5.5, 0.5), (11, 10.5), (0, 10.5)],
    "G": [(5.5, 0), (11, 5.5), (5.5, 11), (0, 5.5)],
    "B": [(3, 0.5), (8, 0.5), (11, 5.5), (8, 10.5), (3, 10.5), (0, 5.5)],
    "V": [(3.5, 0.5), (7.5, 0.5), (10.5, 3.5), (10.5, 7.5), (7.5, 10.5), (3.5, 10.5), (0.5, 7.5), (0.5, 3.5)],
}
CELL = 12
WELL_AT = (24, 10)                 # the well's top-left cell's corner, in screen pixels
COLS, ROWS = 6, 12


def gem(kind, flash=False):
    """A 12 x 12 gem: its shape in a dark edge, its colour, a highlight."""
    colour = (255, 255, 255) if flash else GEM_COLOURS[kind]
    dark = mix(colour, (0, 0, 0), 0.55)
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    shape = GEM_SHAPES[kind]
    if shape is None:
        d.ellipse([0.5, 0.5, 11, 11], fill=dark)
        d.ellipse([1.5, 1.5, 10, 10], fill=colour)
    else:
        d.polygon(shape, fill=dark)
        inner = [(5.5 + (x - 5.5) * 0.74, 5.5 + (y - 5.5) * 0.74) for x, y in shape]
        d.polygon(inner, fill=colour)
    if not flash:
        light = mix(colour, (255, 255, 255), 0.65)
        d.rectangle([4, 3, 5, 4], fill=light)
        d.point((6, 3), fill=light)
    return img


_GEMS = {}


def gem_image(kind, flash=False):
    key = (kind, flash)
    if key not in _GEMS:
        _GEMS[key] = gem(kind, flash)
    return _GEMS[key]


SWIRL = [(30, 10, 66), (70, 20, 120), (128, 34, 168), (200, 56, 172), (246, 110, 196)]


def swirl(t):
    """Kaleidrop's backdrop: a kaleidoscope's swirl in its five purples, turning slowly."""
    w, h = L.SCREEN_PX
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xx - w / 2 + 0.5, yy - h / 2 + 0.5
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    v = 0.5 + 0.38 * np.sin(6 * th + r * 0.11 - t * 0.14) + 0.18 * np.sin(r * 0.07 - t * 0.09)
    v = v - np.clip((r - 60) / 140, 0, 0.5)
    levels = np.clip((v * len(SWIRL)).astype(int), 0, len(SWIRL) - 1)
    return Image.fromarray(np.array(SWIRL, np.uint8)[levels])


_SCREENS = []


def pixel_text(img, x, y, s, colour, shadow="#100820", scale=1):
    """The made-up games' bitmap font (tools/made-up-games/screens.py) on a 240 x 160 picture."""
    if not _SCREENS:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "made-up-games"))
        import screens
        _SCREENS.append(screens)
    a = np.array(img)
    _SCREENS[0].text(a, x, y, s, colour, shadow=shadow, scale=scale)
    return Image.fromarray(a)


def text_width(s, scale=1):
    return (len(s) * 7 - 1) * scale


_LOGO = {}


def game_logo(made_up, width):
    if width not in _LOGO:
        stem, system = L.MADE_UP
        logo = Image.open(os.path.join(made_up, "library", "media", system, "logos", stem + ".png")).convert("RGBA")
        _LOGO[width] = logo.resize((width, round(logo.height * width / logo.width)), Image.LANCZOS)
    return _LOGO[width]


def title(made_up, t, pressed=None):
    """Kaleidrop's title, t frames in: its logo over the swirl, gems hopping along under it, PRESS START blinking (or,
    pressed frames after START, flashing fast)."""
    img = swirl(t + 400).convert("RGBA")
    logo = game_logo(made_up, 210)
    img.alpha_composite(logo, ((240 - logo.width) // 2, 22))
    for k, kind in enumerate("ROYGBV"):
        x = (k * 40 + t * 1.5) % 260 - 20
        hop = abs(math.sin((t + k * 7) * math.pi / 14)) * 10
        img.alpha_composite(gem_image(kind), (round(x), round(96 - hop)))
    img = img.convert("RGB")
    blink = (t % 18) < 12 if pressed is None else (pressed // 2) % 2 == 0
    if blink:
        s = "PRESS START"
        img = pixel_text(img, (240 - text_width(s)) // 2, 124, s, "#FFF4C0")
    s = "2001 VELVET COMET"
    img = pixel_text(img, (240 - text_width(s)) // 2, 146, s, "#E8C8FF")
    return img


# The round of play, scripted to the clip's presses (gba_layout.INPUTS): two pairs fall; the first is moved left and
# turned, dropped, and its reds make three in a row with the board's; the second is turned the other way and slammed
# down, making three yellows.
BOARD = {(0, 11): "G", (1, 11): "B", (2, 11): "Y", (3, 11): "V", (4, 11): "O", (5, 11): "R",
         (2, 10): "R", (3, 10): "Y", (4, 10): "Y", (5, 10): "B",
         (3, 9): "G", (4, 9): "O", (5, 9): "V", (5, 8): "G"}
PAIRS = [("R", "R"), ("Y", "G"), ("B", "V")]     # (pivot, the gem turning round it)


def _pair_state(f):
    """The falling pair at frame f: (index, pivot col, pivot y px, the other's angle in degrees: 90 above, 0 right,
    180 left), or None between pairs."""
    g = L.GAME
    if g + 4 <= f < 207:
        col = 2 - (f >= 176) - (f >= 182)
        y = 12 + (f - (g + 4)) if f < 196 else min(120, 12 + (196 - (g + 4)) + 8 * (f - 196))
        slide = 0.0
        for f0 in (176, 182):
            if f0 <= f < f0 + 2:
                slide = (1 - (f - f0) / 2) * 1.0
        angle = 90 - 90 * min(1.0, max(0.0, (f - 188) / 3.0))
        return 0, col + slide, y, angle
    if 224 <= f < 243:
        y = 12 + (f - 224) if f < 236 else min(120, 12 + (236 - 224) + 14 * (f - 236))
        angle = 90 + 90 * min(1.0, max(0.0, (f - 230) / 3.0))
        return 1, 2, y, angle
    return None


def _board(f):
    """The settled gems at frame f, which of them flash, the sparkles, and the score."""
    board = dict(BOARD)
    flashing, sparkles = set(), []
    score = 0
    if f >= 207:
        board[(0, 10)], board[(1, 10)] = "R", "R"
        first = {(0, 10), (1, 10), (2, 10)}
        if f < 216:
            flashing = first if (f - 208) // 2 % 2 == 0 and f >= 208 else set()
        elif f < 222:
            sparkles += [(c, r, (f - 216) / 6.0) for c, r in first]
        if f >= 216:
            for cell in first:
                board.pop(cell, None)
        score = round(300 * min(1.0, max(0.0, (f - 216) / 10.0)))
    if f >= 243:
        board[(1, 10)], board[(2, 10)] = "G", "Y"
        second = {(2, 10), (3, 10), (4, 10)}
        if f < 252:
            flashing = second if (f - 244) // 2 % 2 == 0 and f >= 244 else set()
        elif f < 258:
            sparkles += [(c, r, (f - 252) / 6.0) for c, r in second]
        if f >= 252:
            for cell in second:
                board.pop(cell, None)
        score = 300 + round(450 * min(1.0, max(0.0, (f - 252) / 10.0)))
    falling = {}
    if f >= 258:                                       # the gems over the yellows drop into their places
        drop = min(1.0, (f - 258) / 4.0)
        for col in (3, 4):
            kind = board.pop((col, 9), None)
            if kind:
                if drop >= 1.0:
                    board[(col, 10)] = kind
                else:
                    falling[(col, 9 + drop)] = kind
    return board, flashing, sparkles, score, falling


def play(made_up, f):
    """The game at frame f (from L.GAME): the well, the falling pair, the NEXT box, the score."""
    img = swirl(f).convert("RGBA")
    d = ImageDraw.Draw(img)
    x0, y0 = WELL_AT
    gold, gold_dark = (236, 188, 64), (128, 84, 20)
    d.rectangle([x0 - 4, y0 - 4, x0 + COLS * CELL + 3, y0 + ROWS * CELL + 3], fill=gold_dark)
    d.rectangle([x0 - 3, y0 - 3, x0 + COLS * CELL + 2, y0 + ROWS * CELL + 2], fill=gold)
    d.rectangle([x0 - 1, y0 - 1, x0 + COLS * CELL, y0 + ROWS * CELL], fill=gold_dark)
    d.rectangle([x0, y0, x0 + COLS * CELL - 1, y0 + ROWS * CELL - 1], fill=(14, 12, 42))
    for c in range(1, COLS):
        d.line([(x0 + c * CELL, y0), (x0 + c * CELL, y0 + ROWS * CELL - 1)], fill=(26, 24, 70))
    for r in range(1, ROWS):
        d.line([(x0, y0 + r * CELL), (x0 + COLS * CELL - 1, y0 + r * CELL)], fill=(26, 24, 70))
    board, flashing, sparkles, score, falling = _board(f)
    for (c, r), kind in board.items():
        img.alpha_composite(gem_image(kind, (c, r) in flashing), (x0 + c * CELL, y0 + r * CELL))
    for (c, r), kind in falling.items():
        img.alpha_composite(gem_image(kind), (x0 + c * CELL, round(y0 + r * CELL)))
    state = _pair_state(f)
    if state:
        index, col, y, angle = state
        pivot, other = PAIRS[index]
        px, py = x0 + col * CELL, y0 + y
        img.alpha_composite(gem_image(pivot), (round(px), round(py)))
        a = math.radians(angle)
        img.alpha_composite(gem_image(other), (round(px + CELL * math.cos(a)), round(py - CELL * math.sin(a))))
    for c, r, t in sparkles:
        cx, cy = x0 + c * CELL + 6, y0 + r * CELL + 6
        reach = 2 + 9 * t
        bright = mix((255, 255, 255), (255, 200, 120), t)
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            sx, sy = cx + reach * math.cos(a), cy + reach * math.sin(a)
            d.line([(sx - 2, sy), (sx + 2, sy)], fill=bright)
            d.line([(sx, sy - 2), (sx, sy + 2)], fill=bright)
        if t < 0.5:
            d.rectangle([cx - 3, cy - 3, cx + 2, cy + 2], fill=(255, 255, 255))
    # NEXT: the pair after the falling one.
    nx, ny = 118, 22
    d.rectangle([nx - 3, ny - 3, nx + 28, ny + 34], fill=gold_dark)
    d.rectangle([nx - 2, ny - 2, nx + 27, ny + 33], fill=gold)
    d.rectangle([nx, ny, nx + 25, ny + 31], fill=(14, 12, 42))
    nxt = PAIRS[1] if f < 224 else PAIRS[2]
    img.alpha_composite(gem_image(nxt[1]), (nx + 7, ny + 4))
    img.alpha_composite(gem_image(nxt[0]), (nx + 7, ny + 16))
    img = img.convert("RGB")
    img = pixel_text(img, nx - 1, ny - 13, "NEXT", "#FFE070")
    img = pixel_text(img, 116, 76, "SCORE", "#FFE070")
    img = pixel_text(img, 116, 88, f"{score:06d}", "#FFFFFF")
    img = pixel_text(img, 116, 112, "LEVEL", "#FFE070")
    img = pixel_text(img, 116, 124, "03", "#FFFFFF")
    if f >= 252:
        img = pixel_text(img, 172, 124, "NICE!" if (f // 4) % 2 == 0 else "", "#A0FFB0")
    small = game_logo(made_up, 96)
    out = img.convert("RGBA")
    out.alpha_composite(small, (126, 140))
    return out.convert("RGB")


def main():
    made_up, folder = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(folder, exist_ok=True)
    print_atlas(made_up, os.path.join(folder, "gba_print.png"))
    frame(lens()).save(os.path.join(folder, "gba_screen.png"), optimize=True)
    print("Game Boy Advance: print and screen")


if __name__ == "__main__":
    main()
