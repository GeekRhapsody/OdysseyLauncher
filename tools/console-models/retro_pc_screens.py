"""The pieces the retro PC cards' screens share (dos_screens.py, windows3x_screens.py, windows9x_screens.py), which
their print script draws their stills with and their video script their frames: DOS's text mode, VGA's 256-colour
pictures, the paintings' sprites cut out of their green, and the CRT's glass round a raster. Run with the system Python
(Pillow, numpy).

The text mode is 80 x 25 cells in VGA's 16 colours, each cell drawn in Terminal's 10 x 20 code page 437 glyphs (its
box-drawing characters joining across cells), 800 x 500, then fitted to the 640 x 480 raster as a VGA monitor fits its
400 lines. A VGA game's 320 x 200 picture is mapped to one fixed palette of 256 colours (no colours wandering between
frames), its pixels doubled, then its lines stretched to the raster. The glass is the raster on the tube's unlit grey,
its light blooming a little, darker towards its corners, and a faint sheen over it.
"""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import raster_fonts as R
import retro_pc_layout as K

PAINTINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "artifacts", "console-paintings")

# VGA's 16 text colours, by their names' indices.
COLOURS = [(0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170), (170, 0, 0), (170, 0, 170), (170, 85, 0),
           (170, 170, 170), (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255), (255, 85, 85),
           (255, 85, 255), (255, 255, 85), (255, 255, 255)]
(BLACK, BLUE, GREEN, CYAN, RED, MAGENTA, BROWN, GREY, DARK_GREY, LIGHT_BLUE, LIGHT_GREEN, LIGHT_CYAN, LIGHT_RED,
 LIGHT_MAGENTA, YELLOW, WHITE) = range(16)
DOUBLE = dict(h="═", v="║", tl="╔", tr="╗", bl="╚", br="╝")
SINGLE = dict(h="─", v="│", tl="┌", tr="┐", bl="└", br="┘")


class TextScreen:
    """An 80 x 25 text screen: each cell a character and its two colours (indices into COLOURS), and the cursor."""

    COLS, ROWS = 80, 25
    CELL = (10, 20)

    def __init__(self, fg=GREY, bg=BLACK):
        self.cells = [[[" ", fg, bg] for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.cursor = None                                # (col, row), drawn when set

    def put(self, col, row, text, fg, bg=None):
        for k, ch in enumerate(text):
            if 0 <= col + k < self.COLS and 0 <= row < self.ROWS:
                cell = self.cells[row][col + k]
                cell[0], cell[1] = ch, fg
                if bg is not None:
                    cell[2] = bg

    def fill(self, col0, row0, col1, row1, fg, bg, ch=" "):
        for row in range(row0, row1 + 1):
            self.put(col0, row, ch * (col1 - col0 + 1), fg, bg)

    def frame(self, col0, row0, col1, row1, fg, bg, lines=DOUBLE, title=None, title_colours=None):
        """A box of lines round col0..col1, row0..row1 (filled with bg), its title centred in its top edge."""
        self.fill(col0, row0, col1, row1, fg, bg)
        self.put(col0, row0, lines["tl"] + lines["h"] * (col1 - col0 - 1) + lines["tr"], fg, bg)
        self.put(col0, row1, lines["bl"] + lines["h"] * (col1 - col0 - 1) + lines["br"], fg, bg)
        for row in range(row0 + 1, row1):
            self.put(col0, row, lines["v"], fg, bg)
            self.put(col1, row, lines["v"], fg, bg)
        if title:
            tf, tb = title_colours or (fg, bg)
            self.put((col0 + col1 + 1) // 2 - len(title) // 2, row0, title, tf, tb)

    def image(self):
        """The screen drawn, 800 x 500."""
        cw, ch = self.CELL
        img = Image.new("RGB", (self.COLS * cw, self.ROWS * ch))
        d = ImageDraw.Draw(img)
        font = R.terminal(cw, ch)
        for row, cells in enumerate(self.cells):
            for col, (char, fg, bg) in enumerate(cells):
                if bg != BLACK:
                    d.rectangle([col * cw, row * ch, col * cw + cw - 1, row * ch + ch - 1], fill=COLOURS[bg])
                if char != " ":
                    font.draw(img, col * cw, row * ch, char, COLOURS[fg])
        if self.cursor is not None:                       # VGA's cursor: two lines at the foot of its cell
            col, row = self.cursor
            fg = COLOURS[self.cells[row][col][1]]
            d.rectangle([col * cw, row * ch + ch - 4, col * cw + cw - 1, row * ch + ch - 2], fill=fg)
        return img

    def raster(self):
        return self.image().resize(K.RASTER_PX, Image.LANCZOS)


def vga(picture):
    """A VGA game's 320 x 200 picture on the 640 x 480 raster: its pixels doubled, its 400 lines stretched to 480."""
    return picture.resize((640, 400), Image.NEAREST).resize(K.RASTER_PX, Image.BILINEAR)


def palette_of(images, colours=256):
    """One fixed palette (a "P" image) for a game's pictures: the colours of these, median-cut."""
    w = sum(i.width for i in images)
    h = max(i.height for i in images)
    sample = Image.new("RGB", (w, h))
    x = 0
    for img in images:
        sample.paste(img.convert("RGB"), (x, 0))
        x += img.width
    return sample.quantize(colours, method=Image.Quantize.MEDIANCUT)


def to_palette(img, palette):
    """img in the palette's colours, each pixel its nearest (no dithering: the colours stay put frame to frame)."""
    return img.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB")


def faded(img, t):
    """The picture as a palette fade leaves it: every colour scaled towards black (t 1 shows it, 0 is black)."""
    if t >= 1.0:
        return img
    t = max(0.0, t)
    return img.point(lambda v: int(v * t))


def keyed(img):
    """A painting on flat green, its green made transparent and its spill pulled down."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    top = np.maximum(r, b)
    green = (g > top + 60) & (g > 120)
    edge = (g > top + 18) & ~green
    out = np.dstack([r, np.where(green | edge, np.minimum(g, top + 8), g), b,
                     np.where(green, 0, np.where(edge, 170, 255))]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def painting(name):
    return Image.open(os.path.join(PAINTINGS, name + ".png")).convert("RGB")


def sprites(name):
    """A 2 x 2 sheet of sprites on green, cut out: [top left, top right, bottom left, bottom right], each cropped to
    what it shows."""
    sheet = keyed(painting(name))
    w, h = sheet.width // 2, sheet.height // 2
    out = []
    for qy in (0, 1):
        for qx in (0, 1):
            cell = sheet.crop((qx * w, qy * h, qx * w + w, qy * h + h))
            alpha = cell.getchannel("A").point(lambda v: 255 if v > 200 else 0)
            out.append(cell.crop(alpha.getbbox()))
    return out


def scaled(img, width):
    """img at width pixels wide (its proportions kept)."""
    return img.resize((max(1, round(width)), max(1, round(img.height * width / img.width))), Image.LANCZOS)


class Glass:
    """The CRT's glass, GLASS_PX, round a 640 x 480 raster."""

    def __init__(self):
        w, h = K.GLASS_PX
        self.base = Image.new("RGB", (w, h), (24, 26, 27))
        yy, xx = np.mgrid[0:h, 0:w]
        nx, ny = (xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)
        vignette = 1.0 - 0.22 * np.clip(nx * nx * 0.9 + ny * ny, 0, 1.6) ** 1.6
        self.vignette = vignette[..., None]
        sheen = np.clip(1.0 - np.hypot(nx + 0.55, ny + 0.62) / 0.9, 0, 1) ** 2 * 26.0
        self.sheen = sheen[..., None]

    def __call__(self, raster, brightness=1.0):
        img = self.base.copy()
        if raster is not None:
            if brightness < 1.0:
                raster = raster.point(lambda v: int(v * brightness))
            img.paste(raster, K.RASTER_AT)
            glow = img.filter(ImageFilter.GaussianBlur(3.0))
            img = Image.blend(img, Image.fromarray(np.maximum(np.asarray(img), np.asarray(glow))), 0.5)
        a = np.asarray(img).astype(np.float32) * self.vignette + self.sheen
        return Image.fromarray(a.clip(0, 255).astype(np.uint8))
