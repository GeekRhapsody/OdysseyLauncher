"""The Mega-CD's and Sega CD's game cases' measurements, shared by sega_cd_case_print.py (their case texture) and
sega_cd_case.py (memory-card's megacd_case and segacd_case templates).

Two cases, one shape: a box with small rounded corners and a chamfer round its front and back, a clear lid over the
front insert, an opaque black tray behind it, the seam where the lid meets the base round the top, the opening side and
the bottom, and the inlay's one spine seen through the base's hinge side. Each kind (KINDS) gives its size and its
art's, taken from ScreenScraper's scans (the owner's Mega-CD library), so none of the art is cropped:

- megacd: the PAL Mega-CD case, the double jewel case European Mega-CD games came in (Sega Retro: "the jewel case quad
  variation, where one half would be used to store the often large multi-language instruction manuals"; sellers of
  originals and of reproductions call it a double jewel case). A CD jewel case's face, 142 x 125 mm, its front insert
  covering it nearly whole (an 801 x 680 scan), a 799 x 680 back and a 73 x 680 spine. The inlay is 118 mm high: the
  back scan's EAN-13 is 183 of its 680 pixels long, which at the barcode's nominal 31.35 mm makes the scan 116.5 mm
  high, a jewel case inlay's height (118). The depth isn't measured: it's the spine (12.7 mm at that height) and what a
  CD jewel case has round its own (10.4 mm less a 6.5 mm spine), 16.5 mm.
- segacd: the North American Sega CD long box, Sega's tall plastic case for Sega CD (and later Saturn) games: 144 x
  207 x 21 mm (20.7 x 14.4 x 2.1 cm on racketboy.com's forum, from an original); the inlay 201.6 mm high (an original
  back insert, 5 9/16 x 7 15/16 in, on Sega-16's forum), its 476 x 680 back scan 141.1 mm wide at that height, as the
  insert is; a 481 x 680 front and a 67 x 680 spine (19.9 mm). It's 21.5 mm deep here, within the forum's rounding, so
  the spine fits between the chamfers.

All in millimetres.
"""

# Each kind: the case's width, height and depth; the scans' sizes in pixels (front, back, spine); the inlay's height
# (the front insert's too).
KINDS = {
    "megacd": dict(size=(142.0, 125.0, 16.5), front=(801, 680), back=(799, 680), spine=(73, 680), inlay=118.0),
    "segacd": dict(size=(144.0, 207.0, 21.5), front=(481, 680), back=(476, 680), spine=(67, 680), inlay=201.6),
}

# The corners' radius, the chamfer round the front and the back, how far the spine's inlay sits in from the back face,
# and how far the seam's groove starts from the hinge side (the lid's knuckles take the rest).
CORNER = 1.0
CHAMFER = 0.6
BACK_RIM = 0.5
HINGE = 3.0

# Where the lid meets the base, round the top, the opening side and the bottom: its distance back from the front, and
# the groove's width and depth.
SEAM_Y = 3.0
SEAM = (0.4, 0.3)

# The plastic's colours (sRGB): the clear lid and base with the black tray behind them; the clear plastic's edges and
# rims, seen on edge, lighter, so the case's outline reads on a dark background; the seam's shadow; the black tray where
# it shows on its own (the hinge side round the spine).
COLOURS = {
    "clear": "#1E2024",
    "edge": "#6C727A",
    "seam": "#0B0C0E",
    "tray": "#141518",
}

# The case texture: a column of swatches, each a block a face takes its colour from by the UV at its middle.
SWATCHES = ("clear", "edge", "seam", "tray")
SWATCH_SIZE = 64
ATLAS = (SWATCH_SIZE, SWATCH_SIZE * len(SWATCHES))


def swatch_uv(name):
    """The UV (Blender's: v up from the image's bottom) at the middle of a swatch's block."""
    i = SWATCHES.index(name)
    return 0.5, 1 - (i * SWATCH_SIZE + SWATCH_SIZE / 2) / ATLAS[1]
