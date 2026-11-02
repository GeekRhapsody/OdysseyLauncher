"""The PAL Dreamcast jewel case's measurements, shared by dreamcast_jewel_case_print.py (its case texture) and
dreamcast_jewel_case.py (memory-card's dreamcast_jewel_case template).

PAL Dreamcast games came in a jewel case of a CD case's face, 142 x 125 mm, but nearly twice as deep, with an opaque
blue tray whose hinge band runs down the front's left, "Dreamcast" moulded into a rounded panel on it (read from the
bottom up), the booklet under the clear lid to its right. The inlay behind the tray has one spine, on the hinge side.
Its references: photographs of PAL cases on The Dreamcast Junkyard (one empty, showing the tray and the band; two
closed, straight on), for the band, its panel and lettering; the owner's reference pictures (a photograph of a closed
case straight on, a studio render of one at three-quarters), for the colours; and 300 dpi scans of PAL inserts
(Maddog's, on the Internet Archive), for their real size: a 120.2 x 119.5 mm booklet and a 151.7 x 118.6 mm inlay.

The art's faces are ScreenScraper's scans' proportions, so none of it is cropped: a 640 x 640 front (the booklet),
and a 784 x 680 back and an 87 x 680 spine (the inlay, cut at its fold), the inlay 118.6 mm high. The depth isn't
measured: it's the inlay's spine (15.2 mm) and what a CD jewel case has round its own (10.4 mm less a 6.5 mm spine),
19 mm. All in millimetres.
"""

# The case, seen from the front: its width, height and depth, its corners' radius, and the chamfer round its front and
# back.
WIDTH, HEIGHT, DEPTH = 142.0, 125.0, 19.0
CORNER = 1.0
CHAMFER = 0.6

# The scans' sizes in pixels.
FRONT_SCAN = (640, 640)
BACK_SCAN = (784, 680)
SPINE_SCAN = (87, 680)

# The booklet under the lid: square, as its scan is, with its left edge in from the case's left edge.
COVER = 120.0
COVER_LEFT = 18.4

# The inlay: as high as the PAL scans say, its back and spine as wide as ScreenScraper's say at that height. The back
# is centred on the case's back; the spine starts a rim in from the back edge.
INLAY_HEIGHT = 118.6
BACK_WIDTH = INLAY_HEIGHT * BACK_SCAN[0] / BACK_SCAN[1]     # 136.7
SPINE_WIDTH = INLAY_HEIGHT * SPINE_SCAN[0] / SPINE_SCAN[1]  # 15.2
BACK_RIM = 1.0

# The tray's hinge band: a pocket in the front, the lid standing proud of it, between the clear wall at the case's
# left edge and the lid's edge, and between the lid's hinge knuckles at its ends.
BAND_LEFT, BAND_RIGHT = 1.2, 13.5           # from the case's left edge
BAND_BOTTOM, BAND_TOP = 1.5, HEIGHT - 1.5
BAND_STEP = 1.0                             # how far the lid stands proud of the band

# The panel moulded into the band and its lettering, in the band's own millimetres from its top-left corner: the
# panel's middle (across, and down from the band's top), its width, its length and its corners' radius; the lettering's
# length (Dreamcast and its trademark sign) and font.
PANEL_X, PANEL_Y = 6.15, 58.6
PANEL_W, PANEL_L, PANEL_R = 9.0, 38.0, 2.0
LETTERING = 28.5
FONT = "segoeui.ttf"

# Where the lid meets the base, round the top, the opening side and the bottom: its distance back from the front, and
# the groove's width and depth.
SEAM_Y = 3.0
SEAM = (0.4, 0.3)

# The plastic's colours (sRGB): the tray's strong blue; the clear lid and base with the tray behind them, a darker,
# greyer blue; the clear plastic's edges and rims, seen on edge; the seam's shadow; the moulded panel and the
# lettering. Rendered, the band comes out as the owner's photograph has it, about hue 217 and saturation 0.7, between
# the photograph and the studio render in brightness, and the lid round the booklet darker and greyer, as the
# photograph's is.
COLOURS = {
    "band": "#1B417A",
    "clear": "#485A78",
    "edge": "#A9B6C0",
    "seam": "#26334A",
    "panel": "#193D73",
    "ink": "#0D1726",
}

# The case texture: the band's pocket floor down the left (BAND_RIGHT - BAND_LEFT across, BAND_TOP - BAND_BOTTOM
# down), padded with the band's blue, then a column of swatches, each a block a face takes its colour from by the UV at
# its middle.
ATLAS = (256, 1024)
BAND_PIXELS = round((BAND_RIGHT - BAND_LEFT) / (BAND_TOP - BAND_BOTTOM) * ATLAS[1])  # 103: the band's proportions
SWATCH_X, SWATCH_SIZE = 128, 128
SWATCHES = ("band", "clear", "edge", "seam")


def swatch_uv(name):
    """The UV (Blender's: v up from the image's bottom) at the middle of a swatch's block."""
    i = SWATCHES.index(name)
    return ((SWATCH_X + SWATCH_SIZE / 2) / ATLAS[0], 1 - (i * SWATCH_SIZE + SWATCH_SIZE / 2) / ATLAS[1])
