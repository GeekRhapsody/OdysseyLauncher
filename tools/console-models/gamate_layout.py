"""The Gamate card's measurements, shared by gamate_print.py (which draws its printing and screens) and gamate.py (which
builds it). Plain Python: Blender's Python imports it too.

Bit Corporation's Gamate (1990), the common dark grey one: 165 x 91 x 28 mm, measured with its parts on 1200 dpi scans
of its face and edges (0.1187 mm a pixel at the face scan's 1600 px); its card 54.0 x 87.3 x 3.5 mm; its screen 160 x
152 pixels. Millimetres in handheld.py's frame: x from its middle (left to right), z up from its bottom edge, y back
from its face.

Its face: the grips' outline (OUTLINE: its corners rounded, the bottom ones more), and the screen section (SECTION)
standing proud of it and above its top edge; the black bezel on the section, its red frame line, DOT MATRIX LCD and
GAMATE® round the LCD. The left grip: the speaker's 6 x 7 holes, the yellow D-pad disc in its well; the right grip:
SELECT and START, red pills slanting in their wells, A and B yellow in their diagonal band. On the top edge: the ON·OFF
switch at the right end, the CONTRAST wheel on the section, the card's slot behind it (the card slides down into the
back, its label to the back, its top end flush).

Two textures: the print (ATLAS square, REGIONS: `face` from the front, `label` the card's, and swatches) and the screens
(MEDIA_REGIONS: the start-up screen, a made-up game's title and two moments of it, dark on the LCD's pale green). A
region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 165.0, 86.0, 28.0
HALF = WIDTH / 2


def _arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def outline():
    """The grips' outline (x, z), anticlockwise from the bottom edge's left end."""
    top, bottom = 16.0, 24.0
    return (_arc(HALF - bottom, bottom, bottom, -90.0, 0.0, 8) + _arc(HALF - top, HEIGHT - top, top, 0.0, 90.0, 6)
            + _arc(-HALF + top, HEIGHT - top, top, 90.0, 180.0, 6) + _arc(-HALF + bottom, bottom, bottom, 180.0, 270.0, 8))


SECTION = dict(rect=(-37.4, 37.4, 9.5, 90.8), r=8.0, proud=2.6)
SPAN = (-HALF, HALF, 0.0, 91.0)                            # the face region's x and z
BEZEL = dict(rect=(-33.3, 33.3, 15.4, 87.6), r=4.0)
FRAME = dict(rect=(-31.0, 31.0, 21.0, 84.0))
SCREEN = dict(size=(52.0, 48.7), at=(0.6, 54.6), pixels=(160, 152))
DPAD = dict(at=(-55.8, 35.3), r=13.0, well=15.0)
SPEAKER = dict(x=(-64.0, -46.9), z=(55.8, 76.0), cols=6, rows=7, r=0.95)
PILLS = dict(select=(49.9, 65.3), start=(63.5, 65.3), size=(6.5, 3.5), slant=45.0)
BUTTONS = dict(a=(62.1, 38.3), b=(50.4, 27.9), r=4.65, band=(30.0, 13.0))
SWITCH = dict(at=(62.0, 14.0), size=(9.0, 5.0, 3.0), travel=5.0)          # x, y on the top edge; its knob
WHEEL = dict(at=(-20.0, 7.0), r=7.0, width=5.0)                           # CONTRAST, in the section's top
CARD = dict(size=(54.0, 3.5, 87.3), y=20.0)                               # width, thickness, height; its middle's y

PALETTE = ["#1E2814", "#46562A", "#7E9050", "#B8C886"]     # dark on the LCD's pale green, darkest first
MADE_UP = ("Sandstorm Lancer (Europe)", "megadrive")

COLOURS = dict(body="#444552", yellow="#EED901", red="#BD2C18", bezel="#060307", olive="#454719", card="#3A4446",
               dark="#16161A", knob="#2A2A30")

REGIONS = dict(face=(0, 0, 990, 546), label=(0, 554, 216, 349))
SWATCHES = {name: (240 + 32 * (k % 8), 570 + 32 * (k // 8)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(boot=(0, 0, 320, 304), title=(328, 0, 320, 304), game1=(656, 0, 320, 304),
                     game2=(0, 312, 320, 304))

FPS = 30
LENGTH = 240                 # 8 s
