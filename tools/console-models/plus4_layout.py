"""The Commodore Plus/4 card's measurements, shared by plus4_print.py (which draws its printing and screens) and
plus4.py (which builds it). Plain Python: Blender's Python imports it too.

The Commodore Plus/4 (1984), 336 mm wide, 206 deep and 60 high (a museum's 335 x 205 x 57 mm, which its 19.05 mm key
pitch confirms in a photograph straight down on it), its 1531 Datassette at its right (205 x 172 x 46, measured from a
photograph of one straight down, scaled by its piano keys), in front of the portable television the ZX Spectrum's card
has (zx_spectrum.py's, its front's middle at TV_AT), a cassette with a made-up game, Odyssey, going into the Datassette.
Millimetres: x from the Plus/4's middle (left to right), y back from its front, z up from the table. Measured from
photographs on Wikimedia Commons (straight down on it, its sides and back straight on, from the front left; the 1531
straight down and from the front).

The Plus/4: a dark wedge (PROFILE: the front's rim, the keyboard's deck sloping up, the chamfer to the raised back
block, the back), the cooling fins along the back block, overhanging the back (FINS); its keys (cream) standing on the
deck in the deck's frame, the four function keys flat on the chamfer, the cursor keys' diamond at the right; the
Commodore logo, its rainbow and plus/4 on the back block. The 1531 (DECK): a black box, its top's left two thirds a
silver plate with the cassette's lid (LID, hinged along its back edge) and the six piano keys at its front (PIANO), the
counter at its right.

The keys are laid out in units of U from KEYS_X0, in rows from the back (the digits') to the front (the space bar's).
The deck is a plane at SLOPE: a key stands on it in the deck's frame (x across, s up the slope from its front edge, h
off it), and deck_point() maps a point of that frame to the model's (y, z).

Two textures. `print` (ATLAS square, PRINT_REGIONS): `top` (the Plus/4 from above: the keys' tops and legends, the logo,
the fins' dark), `deck` (the 1531 from above: the plate, the lid's window, the keys' names, the counter), `cassette`
(its label), and swatches; the television's front where zx_spectrum_layout.py's PRINT_REGIONS["tv"] puts it and its
swatches where its PRINT_SWATCHES do, as television() maps them. `media` (MEDIA_REGIONS): the screens, the TED's 320 x
200 picture in its border (the start-up screen, PRESS PLAY ON TAPE, SEARCHING, FOUND ODYSSEY, the title, two moments of
the game). A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024
U = 19.05

WIDTH, DEPTH = 336.0, 196.0       # the case; the fins overhang its back to FINS["y"][1]
FRONT = (14.0, 17.0)              # the deck's front edge (y, z)
DECK_BACK = (126.0, 43.0)         # its back edge, at the chamfer's foot
SLOPE = math.atan2(DECK_BACK[1] - FRONT[1], DECK_BACK[0] - FRONT[0])
PROFILE = [                       # the case's side outline (y, z), round from the front's foot
    (5.0, 3.0), (DEPTH - 4.0, 3.0), (DEPTH, 7.0), (DEPTH, 52.0), (DEPTH - 4.0, 56.0), (140.0, 56.0), DECK_BACK,
    FRONT, (6.0, 21.0), (1.0, 19.5), (0.0, 16.0), (0.0, 8.0),
]
FINS = dict(x=(-145.0, 141.0), y=(157.0, 206.0), z=(50.0, 60.0), count=46, thickness=2.4)
LOGO = dict(x=(-134.0, 12.0), y=(142.0, 154.0))
FKEYS = dict(x=[-135.6, -97.6, -59.8, -20.7], width=31.5, y=(127.5, 135.0),
             names=["F1/F4", "F2/F5", "F3/F6", "HELP/F7"])
LIGHT = dict(at=(-135.6, 24.0), size=(5.0, 2.0))            # the power light, at the deck's front left

KEYS_X0, ROW1 = -155.0, 98.0      # the back row's left edge; its middle (s)
KEY = dict(height=10.0, inset=2.4)
ROWS = [
    (0.0, [("Esc", 1.0)] + [(c, 1.0) for c in "1234567890+-="] + [("Clear Home", 1.0), ("Inst Del", 1.0)]),
    (0.0, [("Control", 1.5)] + [(c, 1.0) for c in "QWERTYUIOP@£*"] + [("Control", 1.5)]),
    (0.0, [("Run Stop", 1.0), ("Shift Lock", 1.0)] + [(c, 1.0) for c in "ASDFGHJKL[]"] + [("Return", 2.0)]),
    (0.0, [("C=", 1.0), ("Shift", 1.5)] + [(c, 1.0) for c in "ZXCVBNM,./"] + [("Shift", 1.5)]),
    (3.4, [(" ", 9.2)]),
]
# The cursor keys' diamond: its middle (x, y in plan); its keys' offset from it; their size.
CURSOR = dict(at=(134.0, 40.0), reach=12.0, size=(11.0, 11.0))

# The 1531: its front left corner (x, y); w, d, h; its corners' radii (left, right). Its parts below are in its own
# frame: x from its left, y back from its front, z up.
DECK = dict(at=(186.0, 10.0), size=(205.0, 172.0, 46.0), r=(14.0, 34.0))
PLATE = dict(x=(10.0, 142.0), y=(4.0, 160.0))               # the silver plate
LID = dict(x=(22.0, 130.0), y=(52.0, 140.0), thickness=6.0, open=-62.0)    # the cassette's lid, hinged at its back
PIANO = dict(x=(14.0, 138.0), y=(4.0, 38.0), height=8.0, names=["RECORD", "PLAY", "REWIND", "F.FWD", "STOP", "EJECT"])
COUNTER = dict(x=(152.0, 186.0), y=(96.0, 112.0))
CASSETTE = dict(size=(100.0, 63.0, 12.0), above=80.0)       # w, d, t (lying flat); how far out of the lid it waits

TV_AT = (-30.0, 232.0)            # the television's front's middle

COLOURS = dict(case="#2A2A2D", key="#E6E1D2", fkey="#A9A9A6", deck="#1E1E20", print="#FFFFFF", dark="#0A0A0B")

PRINT_REGIONS = dict(top=(0, 0, 1024, 628), deck=(632, 636, 312, 262), cassette=(520, 904, 160, 101))
SWATCHES = dict(case=(712, 924), key=(744, 924), fkey=(776, 924), deck=(808, 924), silver=(840, 924), black=(872, 924),
                lit=(904, 924), cassette=(936, 924), tape=(712, 956))
MEDIA_REGIONS = dict(boot=(0, 0, 320, 246), press=(336, 0, 320, 246), search=(672, 0, 320, 246),
                     found=(0, 256, 320, 246), title=(336, 256, 320, 246), game_1=(672, 256, 320, 246),
                     game_2=(0, 512, 320, 246))
TED_PX = (320, 200)

FPS = 30
LENGTH = 240                 # 8 s


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return FRONT[0] + s * c - h * k, FRONT[1] + s * k + h * c


def keys():
    """Every key: (legend, x0, x1, s), s its row's middle up the deck; the rows from the back to the front."""
    out = []
    for r, (offset, row) in enumerate(ROWS):
        x = KEYS_X0 + offset * U
        s = ROW1 - r * U
        for legend, width in row:
            out.append((legend, x, x + width * U, s))
            x += width * U
    return out
