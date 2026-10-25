"""The Oric card's measurements, shared by oric_print.py (which draws its printing and screens) and oric.py (which
builds it). Plain Python: Blender's Python imports it too.

The Oric Atmos (1984), 280 mm wide, 172 deep and 36 high (a listing's 280 x 175 x 52, the Oric-1's 280 x 178), an
unbranded cassette recorder of the period at its right (the Oric loaded from any), in front of the portable television
the ZX Spectrum's card has (zx_spectrum.py's, its front's middle at TV_AT), a cassette with a made-up game, Odyssey,
going into the recorder. Millimetres: x from the Atmos's middle (left to right), y back from its front, z up from the
table. Measured from photographs on Wikimedia Commons (one straight down on it, its depth corrected for its slight
angle; others from the front left and right), scaled by its width: its keys' pitch comes out at U, a little under the
usual 19.05.

The Atmos: a red base (BASE) under a black shell (PROFILE: the front, the ledge, the deck rising a little to the back
block, its top), the keyboard's well cut into the deck (WELL), the grille's plateau raised on the back block's left
(PLATEAU, its right end slanting), the ORIC ATMOS 48K badge at the back block's right (BADGE). Its keys stand in the
well (ROWS: their left edges, their legends and widths in U; RED, the red ones). The recorder (RECORDER): a black box,
its silver top with the cassette's lid (LID, hinged at its back), the six piano keys at its front (PIANO), the speaker's
slots and the counter at its right.

One texture `print` (ATLAS square, PRINT_REGIONS): `top` (the Atmos from above: the keys' tops and legends, the grille's
holes, the badge, the ports' names along the back), `recorder` (its top), `cassette` (its label), and swatches; the
television's front where zx_spectrum_layout.py's PRINT_REGIONS["tv"] puts it and its swatches where its PRINT_SWATCHES
do, as television() maps them. One `media` (MEDIA_REGIONS): the screens, the Oric's 240 x 224 in its black border
(Ready, CLOAD"" and Searching, Loading ODYSSEY, the title, two moments of the game). A region is (x, y, width, height)
in pixels.
"""

import math

ATLAS = 1024
U = 18.65                         # the keys' pitch, as measured

WIDTH, DEPTH, HEIGHT = 280.0, 172.0, 36.0
BASE = 7.0                        # the red base's top
FRONT = (19.0, 23.0)              # the deck's front edge (y, z)
DECK_BACK = (134.0, 31.0)         # its back edge, at the back block's foot
SLOPE = math.atan2(DECK_BACK[1] - FRONT[1], DECK_BACK[0] - FRONT[0])
PROFILE = [                       # the shell's side outline (y, z), round from its front's foot
    (0.0, BASE), (DEPTH, BASE), (DEPTH, HEIGHT - 3.0), (DEPTH - 3.0, HEIGHT), (138.0, HEIGHT), DECK_BACK, FRONT,
    (3.0, 22.0), (0.0, 19.0),
]
WELL = dict(x=(-133.0, 134.0), s=(0.5, 106.0), depth=5.0, r=3.0)        # in the deck's frame
PLATEAU = [(-136.0, 124.0), (-36.0, 124.0), (-18.0, 140.0), (-136.0, 140.0)]   # in plan
BADGE = dict(x=(82.0, 116.0), y=(152.0, 170.0))
GRILLE = dict(x=(-118.0, -34.0), y=(129.0, 168.0), columns=15, rows=6)
PORTS = ["POWER", "EXPANSION", "PRINTER", "TAPE", "RGB", "MIDI"]

ROW1 = 110.9                      # the digits' row's middle (plan y)
ROW_PITCH = 19.1                  # the rows' spacing (plan)
KEY = dict(height=11.0, inset=2.2)
ROWS = [
    (-120.0, [(c, 1.0) for c in "1234567890-=\\"]),
    (-131.0, [("ESC", 1.0)] + [(c, 1.0) for c in "QWERTYUIOP[]"] + [("DEL", 1.0)]),
    (-128.2, [("CTRL", 1.0)] + [(c, 1.0) for c in "ASDFGHJKL;'"] + [("RETURN", 1.75)]),
    (-127.4, [("SHIFT", 1.46)] + [(c, 1.0) for c in "ZXCVBNM,./"] + [("SHIFT", 1.75)]),
    (-118.8, [("\u2190", 1.0), ("\u2193", 1.0), (" ", 8.3), ("\u2191", 1.0), ("\u2192", 1.0), ("FUNCT", 1.0)]),
]
SHIFTED = dict(zip("1234567890-=\\[];',./", "!@#$%^&*()\u00a3+|{}:\"<>?"))
RED = ("ESC", "DEL", "CTRL", "RETURN", "SHIFT", "\u2190", "\u2193", "\u2191", "\u2192", "FUNCT")

# The recorder: its front left corner (x, y); w, d, h; its corners' radius. Its parts are in its own frame: x from its
# left, y back from its front, z up.
RECORDER = dict(at=(158.0, 0.0), size=(210.0, 150.0, 46.0), r=8.0)
PLATE = dict(x=(8.0, 202.0), y=(4.0, 146.0))                # the silver top plate
LID = dict(x=(14.0, 128.0), y=(46.0, 128.0), thickness=6.0, open=-62.0)
PIANO = dict(x=(14.0, 128.0), y=(4.0, 34.0), height=8.0, names=["REC", "PLAY", "REW", "F.FWD", "STOP/EJ", "PAUSE"])
SPEAKER = dict(x=(148.0, 196.0), y=(44.0, 138.0), count=10)
COUNTER = dict(x=(150.0, 190.0), y=(12.0, 28.0))
CASSETTE = dict(size=(100.0, 63.0, 12.0), out=80.0)        # w, d, t (lying flat); how far out of the lid it waits

TV_AT = (0.0, 214.0)              # the television's front's middle

COLOURS = dict(shell="#16161A", base="#C8281E", key="#1C1C1F", red="#E0352A", recorder="#1E1E21", print="#FFFFFF",
               dark="#0A0A0B")

PRINT_REGIONS = dict(top=(0, 0, 1024, 629), recorder=(632, 636, 312, 222), cassette=(520, 904, 160, 101))
SWATCHES = dict(shell=(712, 924), base=(744, 924), key=(776, 924), red=(808, 924), recorder=(840, 924),
                silver=(872, 924), black=(904, 924), cassette=(936, 924), lit=(712, 956))
MEDIA_REGIONS = dict(boot=(0, 0, 320, 246), search=(336, 0, 320, 246), loading=(672, 0, 320, 246),
                     title=(0, 256, 320, 246), game_1=(336, 256, 320, 246), game_2=(672, 256, 320, 246))
ORIC_PX = (240, 224)

FPS = 30
LENGTH = 240                 # 8 s


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return FRONT[0] + s * c - h * k, FRONT[1] + s * k + h * c


def plan_s(y):
    """How far up the deck from its front edge the point over y is."""
    return (y - FRONT[0]) / math.cos(SLOPE)


def keys():
    """Every key: (legend, x0, x1, y), y its row's middle in plan; the rows from the back to the front."""
    out = []
    for r, (x, row) in enumerate(ROWS):
        y = ROW1 - r * ROW_PITCH
        for legend, width in row:
            out.append((legend, x, x + width * U, y))
            x += width * U
    return out
