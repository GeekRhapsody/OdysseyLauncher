"""Windows' own bitmap fonts (C:/Windows/Fonts/*.fon) read and drawn pixel for pixel, for the console theme's PC cards'
screens (dos_screens.py, windows3x_screens.py, windows9x_screens.py): DOS's text mode in Terminal, the OEM font with
code page 437's box-drawing characters, and Windows 3.x's and 9x's System and MS Sans Serif, the fonts their menus,
title bars and icons were set in. Run with the system Python (Pillow).

A .fon file is a 16-bit Windows executable holding FNT resources, one a size (Microsoft's Windows 3.0 font format:
a header, a table of each character's width and offset, then the glyphs a byte column at a time, each column a byte
wide and the glyph's height tall). Text is given as str: in an OEM font (charset 255), each character is encoded in
code page 437, so "╔═╗" draws the box-drawing glyphs; in the others, in code page 1252.
"""

import struct
from functools import lru_cache

from PIL import Image

FONTS = "C:/Windows/Fonts/"

# Code page 437's graphics in its first 32 codes, which Python's codec reads as control characters.
GRAPHICS = {ch: k + 1 for k, ch in enumerate("\u263a\u263b\u2665\u2666\u2663\u2660\u2022\u25d8\u25cb\u25d9\u2642"
                                              "\u2640\u266a\u266b\u263c\u25ba\u25c4\u2195\u203c\u00b6\u00a7\u25ac"
                                              "\u21a8\u2191\u2193\u2192\u2190\u221f\u2194\u25b2\u25bc")}


class Font:
    """One size of a bitmap font: its glyphs as 1-bit Pillow images, each its own width, all the font's height."""

    def __init__(self, data):
        version = struct.unpack_from("<H", data, 0)[0]
        self.ascent = struct.unpack_from("<H", data, 0x4A)[0]
        self.charset = data[0x55]
        width, self.height = struct.unpack_from("<HH", data, 0x56)
        self.first, last, default = data[0x5F], data[0x60], data[0x61]
        self.default = default + self.first
        table, entry = (0x76, 4) if version < 0x300 else (0x94, 6)
        self.glyphs = {}
        for k in range(last - self.first + 1):
            p = table + k * entry
            w = struct.unpack_from("<H", data, p)[0]
            offset = struct.unpack_from("<H" if entry == 4 else "<I", data, p + 2)[0]
            self.glyphs[self.first + k] = self._glyph(data, offset, w)
        self.fixed = width or None

    def _glyph(self, data, offset, w):
        img = Image.new("1", (max(w, 1), self.height), 0)
        px = img.load()
        for col in range((w + 7) // 8):
            for y in range(self.height):
                byte = data[offset + col * self.height + y]
                for bit in range(8):
                    x = col * 8 + bit
                    if x < w and byte & (0x80 >> bit):
                        px[x, y] = 1
        return img

    def codes(self, text):
        if self.charset != 255:
            return text.encode("cp1252", errors="replace")
        return bytes(GRAPHICS.get(ch) or ch.encode("cp437", errors="replace")[0] for ch in text)

    def width(self, text):
        return sum(self.glyphs.get(c, self.glyphs[self.default]).width for c in self.codes(text))

    def draw(self, img, x, y, text, ink, bold=False):
        """Draws text on img (any mode Pillow pastes into) with its top left at (x, y) in pixels, in ink; bold
        doubles each stroke a pixel to the right, as Windows emboldens a raster font. Returns the x after it."""
        for c in self.codes(text):
            glyph = self.glyphs.get(c, self.glyphs[self.default])
            img.paste(ink, (x, y), glyph)
            if bold:
                img.paste(ink, (x + 1, y), glyph)
            x += glyph.width + (1 if bold else 0)
        return x


def _resources(data):
    """The FNT resources of a .fon file (an NE executable's RT_FONT resources)."""
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    table = ne + struct.unpack_from("<H", data, ne + 0x24)[0]
    shift = struct.unpack_from("<H", data, table)[0]
    p, out = table + 2, []
    while True:
        kind, count = struct.unpack_from("<HH", data, p)
        p += 8
        if kind == 0:
            return out
        for _ in range(count):
            offset, length = struct.unpack_from("<HH", data, p)
            p += 12
            if kind == 0x8008:
                out.append(data[offset << shift:(offset + length) << shift])


@lru_cache(maxsize=None)
def font(file, height, width=None):
    """The size of a .fon file's font height pixels tall (and width wide, for a fixed font with several widths)."""
    with open(FONTS + file, "rb") as f:
        data = f.read()
    for resource in _resources(data):
        candidate = Font(resource)
        if candidate.height == height and (width is None or candidate.fixed == width):
            return candidate
    raise ValueError(f"{file} has no {width or ''}x{height} font")


def terminal(width=10, height=20):
    """DOS's text-mode font: Terminal, code page 437 (8514oem.fon's 10 x 20, cga80woa.fon's 8 x 8, vgaoem.fon's
    8 x 12)."""
    file = {(10, 20): "8514oem.fon", (8, 8): "cga80woa.fon", (8, 12): "vgaoem.fon"}[(width, height)]
    return font(file, height, width)


def system():
    """Windows 3.x's System font, bold and proportional, 16 pixels tall: its title bars and menus."""
    return font("vgasys.fon", 16)


def sans(height=13):
    """MS Sans Serif, 13 pixels tall (8 points at 96 dots an inch): Windows 3.1's icon titles and dialogs, Windows
    9x's whole interface."""
    return font("sserife.fon", height)
