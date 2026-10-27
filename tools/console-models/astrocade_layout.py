"""The Bally Astrocade card's measurements, shared by astrocade_print.py (which draws its printing) and astrocade.py
(which builds it). Plain Python: Blender's Python imports it too.

The Bally Astrocade (the Bally Professional Arcade, 1978), 381 x 273 x 121 mm (the Computer History Museum's record), and
one of its pistol-grip controllers. Millimetres: x from the console's middle (left to right), y back from its front, z up
from the table. The rest was measured from photographs (Evan-Amos's from the front left and of a controller on Wikimedia
Commons, one square from above, which the width scales; others of its storage bin, its back and its keypad).

The console: a black plinth under it; walnut side panels, trapezoids, their front edges sloping up to the smoked cover's
top; between them the walnut band across the front, the black deck sloping up from it (the keypad's champagne plate
with its 24 keys, the cassette well with INSERT CASSETTE on its back lip, RESET and EJECT under it), the smoked cover
over the storage bin (its front face upright, the badge on it: Bally on silver, arcade on red; the launcher draws no
transparency, so the cover is opaque, as it looks over the dark bin), the back black. A thin gold line edges the deck
and the panels. The controller stands at the console's right: a pistol grip, its trigger under the head, the copper
knob on top (a stick that turns as a paddle), its cable to the console's back. A Videocade (the cassette-sized
cartridge, label up) slides back under the well's lip.

One texture (ATLAS square, REGIONS): `deck` (the slope in its own frame: x across, s up it), `panel` (a side panel's
face: y along, z up), `front` (the walnut band), `badge` (the cover's front face), `grip` (the controller's sides), `cart`
(the Videocade's label), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 381.0, 273.0, 121.0
PLINTH = dict(height=8.0, inset=8.0)
PANEL = dict(thickness=12.0, outline=[(0.0, 8.0), (DEPTH, 8.0), (DEPTH - 17.0, HEIGHT), (150.0, HEIGHT),
                                       (0.0, 40.0)])              # a side panel's outline (y, z)
INNER = WIDTH / 2 - PANEL["thickness"]                             # the body's half width, between the panels
BAND = 38.0                                                        # the walnut band's top
DECK = ((4.0, BAND), (146.0, 95.0))                                # the deck's slope: its front and back edges (y, z)
COVER = dict(y=(146.0, 250.0), lip=(258.0, 110.0))                 # the cover: its front face and top, its back lip
BODY_PROFILE = [(2.0, PLINTH["height"]), (262.0, PLINTH["height"]), (262.0, 104.0), COVER["lip"],
                (COVER["y"][1], HEIGHT), (COVER["y"][0], HEIGHT), DECK[1], DECK[0], (2.0, BAND - 2.0)]

KEYPAD = dict(x=(-118.0, -52.0), s=(14.0, 112.0), cols=4, rows=6, key=(11.0, 6.0), height=1.6, plate=0.8)
LEGENDS = ["C", "↑", "↓", "%", "MR", "MS", "CH", "÷", "7", "8", "9", "X", "4", "5", "6", "–", "1", "2", "3", "+",
           "CE", "0", ".", "="]


def keys():
    """The keypad's keys, (legend, x, s): rows from the back (C, ↑, ↓, %) to the front (CE, 0, ., =)."""
    k = KEYPAD
    (x0, x1), (s0, s1) = k["x"], k["s"]
    out = []
    for i, legend in enumerate(LEGENDS):
        col, row = i % k["cols"], i // k["cols"]
        out.append((legend, x0 + (x1 - x0) * (col + 0.5) / k["cols"], s1 - (s1 - s0) * (row + 0.5) / k["rows"] - 2.5))
    return out

WELL = dict(x=(-36.0, 74.0), s=(30.0, 112.0), depth=16.0, lip=(100.0, 112.0))   # the cassette well, its lip at the back
KEYS = dict(reset=(-26.0, -8.0), eject=(30.0, 58.0), s=(18.0, 28.0), height=2.0)  # RESET and EJECT under the well
BADGE = dict(x=(40.0, 150.0), z=(100.0, 118.0))                     # on the cover's front face

VIDEOCADE = dict(size=(100.0, 64.0, 13.0), label=(84.0, 48.0))      # width, length (back along the well), thickness
SEAT_S = 72.0                                                        # its middle up the well's floor, slid home

# The controller standing at the console's right, its side outline (v front to back, z up from its foot), its width;
# the trigger, the knob's shaft and knob; its place (its foot's middle) and turn (degrees).
GRIP = dict(outline=[(12.0, 0.0), (62.0, 0.0), (66.0, 22.0), (64.0, 52.0), (59.0, 82.0), (55.0, 102.0), (50.0, 114.0),
                     (38.0, 123.0), (22.0, 125.0), (9.0, 119.0), (2.0, 107.0), (0.0, 96.0), (5.0, 88.0), (19.0, 84.0),
                     (23.0, 62.0), (21.0, 32.0)],
            width=34.0, trigger=((8.0, 20.0), (70.0, 84.0)), shaft=(24.0, 4.0, 5.0), knob=(8.5, 16.0),
            at=(252.0, 40.0), turn=-62.0, cable=(30.0, 4.0))

def deck_point(s, h=0.0):
    """The model's (y, z) of the point s up the deck from its front edge and h off it."""
    (y0, z0), (y1, z1) = DECK
    a = math.atan2(z1 - z0, y1 - y0)
    return y0 + s * math.cos(a) - h * math.sin(a), z0 + s * math.sin(a) + h * math.cos(a)


DECK_ANGLE = math.atan2(DECK[1][1] - DECK[0][1], DECK[1][0] - DECK[0][0])
DECK_LENGTH = math.hypot(DECK[1][0] - DECK[0][0], DECK[1][1] - DECK[0][1])

COLOURS = dict(wood="#5A3B24", black="#2E2E2E", deck="#323232", smoked="#2A2522", gold="#C9B570", plate="#CABBA0",
               key="#575558", grip="#1E1E1E", knob="#A36732", shell="#312F32", label="#E4D4BA")

REGIONS = dict(deck=(0, 0, 1024, 488), panel=(0, 496, 512, 224), front=(520, 496, 504, 56), badge=(520, 560, 504, 40),
               grip=(0, 728, 256, 160), cart=(264, 728, 280, 160))
SWATCHES = {name: (568 + 32 * (k % 14), 744 + 32 * (k // 14)) for k, name in enumerate(
    ("black", "deck", "smoked", "gold", "plate", "key", "grip", "knob", "shell", "lit", "wood"))}

FPS = 30
LENGTH = 240                 # 8 s
