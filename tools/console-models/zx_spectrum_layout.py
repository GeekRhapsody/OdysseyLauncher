"""The ZX Spectrum 48K and the portable television it's plugged into: the measurements shared by
zx_spectrum_print.py (which draws their printing and the screens) and zx_spectrum.py (which builds them). Plain
Python: Blender's Python imports it too.

Millimetres. The computer: x from its middle (left to right), y back from its front edge, z up from the table. It's 233
x 144 x 30 mm: a thin black wedge, its keyboard plate rising from the front edge to a rounded step, behind which the
hump runs across its back. Its 40 rubber keys stand through the plate in four rows. The rest was measured from
photographs on Wikimedia Commons (Bill Bertram's three-quarter view, a shallow-angle view and the underside), scaled by
its width.

The television is a made-up 1980s portable (the Odyssey brand, as the retro PCs'), silver with a black front: the
screen on the left, a strip of controls on the right, a carrying handle on top. It stands behind the computer, its
front's middle TV["at"], its depth shortened as the Amiga's monitor's is (the launcher fits a card's largest side).

The keys: a row's keys from KEY_X (the left edge of its first key, in millimetres from the computer's left end) at the
row's PITCH; a key's x, width and row are its own where it isn't the row's. A row's y is its keys' front edge.

Two textures. `print` (ATLAS square, PRINT_REGIONS): `top` (the computer's top seen from above, planar-mapped onto
every face facing up: the plate's legends, the key tops, the hump's names, the rainbow) and `tv` (the television's
front: the bezel, its badge and the controls' legends), and swatches. `media` (MEDIA_REGIONS): `glass` (the screen at
rest, the border and the paper: the copyright message, 320 x 256 pixels), each paper state (256 x 192, the Spectrum's
own pixels), and each border state (a column of the border's stripes, 16 x 256: the stripes run across the screen).
"""

import math

ATLAS = 1024

# -- The computer ----------------------------------------------------------------------------------------------------

WIDTH, DEPTH, HEIGHT = 233.0, 144.0, 30.0
FRONT_Z = 14.0                  # the plate's front edge
STEP = (98.0, 19.5, 106.0)      # the plate rises to z at y; the step's rounded nose reaches the hump's top at the third
HUMP_Z = 29.5


def profile():
    """The computer's side outline, (y, z), anticlockwise seen from its right end: the bottom, the back, the hump, the
    step's rounded nose down to the plate, the plate sloping down to the rounded front edge."""
    y0, z0, y1 = STEP
    nose = [(y1 - (y1 - y0) * math.cos(math.radians(a)), z0 + (HUMP_Z - z0) * math.sin(math.radians(a)))
            for a in range(90, -1, -15)]
    front = [(3.0 - 3.0 * math.sin(math.radians(a)), FRONT_Z - 3.0 + 3.0 * math.cos(math.radians(a)))
             for a in range(0, 91, 30)]
    return ([(2.0, 0.0), (DEPTH - 2.0, 0.0), (DEPTH, 2.0), (DEPTH, HUMP_Z - 1.0), (DEPTH - 1.0, HUMP_Z)] + nose
            + front + [(0.0, 2.0)])


def plate_z(y):
    """The plate's height at y, in front of the step."""
    return FRONT_Z + (STEP[1] - FRONT_Z) * y / STEP[0]


KEY = dict(width=14.0, depth=12.0, height=4.0, radius=2.0)
PITCH = 19.0
ROWS = {1: 72.0, 2: 52.5, 3: 33.0, 4: 13.5}             # each row's keys' front edge, y
KEY_X = {1: 24.0, 2: 33.5, 3: 38.25, 4: 43.0}

# (name, row, its letter or legend, its keyword on the key, the plate's green word above it, the red word below it)
KEYS = (
    [(f"d{c}", 1, c, "", word, red) for c, word, red in zip("1234567890",
        ["EDIT", "CAPS LOCK", "TRUE VIDEO", "INV. VIDEO", "←", "↓", "↑", "→", "GRAPHICS", "DELETE"],
        ["DEF FN", "FN", "LINE", "OPEN #", "CLOSE #", "MOVE", "ERASE", "POINT", "CAT", "FORMAT"])]
    + [(c.lower(), 2, c, kw, green, red) for c, kw, green, red in zip("QWERTYUIOP",
        ["PLOT", "DRAW", "REM", "RUN", "RAND", "RETURN", "IF", "INPUT", "POKE", "PRINT"],
        ["SIN", "COS", "TAN", "INT", "RND", "STR $", "CHR $", "CODE", "PEEK", "TAB"],
        ["ASN", "ACS", "ATN", "VERIFY", "MERGE", "[", "]", "IN", "OUT", "©"])]
    + [(c.lower(), 3, c, kw, green, red) for c, kw, green, red in zip("ASDFGHJKL",
        ["NEW", "SAVE", "DIM", "FOR", "GOTO", "GOSUB", "LOAD", "LIST", "LET"],
        ["READ", "RESTORE", "DATA", "SGN", "ABS", "SQR", "VAL", "LEN", "USR"],
        ["~", "|", "\\", "{", "}", "CIRCLE", "VAL $", "SCREEN $", "ATTR"])]
    + [("enter", 3, "ENTER", "", "", "")]
    + [("caps_shift", 4, "CAPS\nSHIFT", "", "", "")]
    + [(c.lower(), 4, c, kw, green, red) for c, kw, green, red in zip("ZXCVBNM",
        ["COPY", "CLEAR", "CONT", "CLS", "BORDER", "NEXT", "PAUSE"],
        ["LN", "EXP", "L PRINT", "L LIST", "BIN", "IN KEY $", "PI"],
        ["BEEP", "INK", "PAPER", "FLASH", "BRIGHT", "OVER", "INVERSE"])]
    + [("symbol_shift", 4, "SYMBOL\nSHIFT", "", "", ""), ("space", 4, "BREAK\nSPACE", "", "", "")]
)
COLOUR_NAMES = ["BLUE", "RED", "MAGENTA", "GREEN", "CYAN", "YELLOW", "WHITE", "", "", "BLACK"]  # above the digits
WIDE = {"enter": (205.0, 18.0), "caps_shift": (19.5, 19.0), "symbol_shift": (176.0, 16.0), "space": (197.0, 24.5)}


def key_rect(name, row, index):
    """A key's footprint, (x0, y0, x1, y1): index is its place in its row."""
    x, w = WIDE.get(name, (KEY_X[row] + index * PITCH, KEY["width"]))
    x0 = x - WIDTH / 2
    return x0, ROWS[row], x0 + w, ROWS[row] + KEY["depth"]


def keys_with_rects():
    """Each key with its footprint."""
    out, counts = [], {}
    for k in KEYS:
        row = k[1]
        index = counts.get(row, 0)
        if k[0] not in WIDE:
            counts[row] = index + 1
        out.append((k, key_rect(k[0], row, index)))
    return out


RAINBOW = dict(colours=["#D8231F", "#F2C81F", "#25A646", "#1E9FD8"], width=5.2, front_x=58.0, slope=0.9)
# The stripes: each from the front edge at front_x (plus its place), rising to the right end: y = slope * (x - start).

# -- The television --------------------------------------------------------------------------------------------------

TV = dict(
    at=(0.0, 158.0),             # its front's middle, in the computer's (x, y)
    width=300.0, height=262.0, depth=210.0,
    bezel=dict(x=(-142.0, 142.0), z=(14.0, 247.0), depth=3.0),    # the black front, sunk into the silver case
    screen=dict(x=-34.0, z=135.0, opening=(209.0, 160.0, 14.0), inner=(198.0, 151.0, 9.0), depth=14.0),
    glass=dict(size=(203.0, 156.0), bulge=7.0),
    paper=(256.0 / 320.0, 192.0 / 256.0),                        # the paper's share of the screen, across and down
    controls=dict(x=(86.0, 135.0)),                              # the control strip, right of the screen
    knob=dict(x=111.0, z=56.0, r=10.0, out=8.0),
    buttons=[(99.0 + 23.5 * (k % 2), 151.0 - 17.0 * (k // 2)) for k in range(6)],  # the channel buttons' middles
    button=(16.0, 11.0, 3.0),
    power=dict(x=111.0, z=31.0, size=(22.0, 9.0, 3.2)),
    handle=dict(x=106.0, y=(63.0, 135.0), height=20.0, thickness=7.0),
)

# -- The atlases -----------------------------------------------------------------------------------------------------

COLOURS = dict(case="#16161A", plate="#0C0C0E", key="#5A6E74", tv="#AEB2B8", bezel="#1A1A1D", handle="#C7CBD0")

PRINT_REGIONS = dict(top=(0, 0, 1024, 633), tv=(0, 640, 512, 384))
PRINT_SWATCHES = dict(black=(536, 664), silver=(568, 664), red=(600, 664))

GLASS_PX = (320, 256)
PAPERS = ["load", "load2", "blank", "header", "third1", "third2", "mono", "colour"]
BORDERS = ["pilot_a", "pilot_b", "data_a", "data_b", "black"]
MEDIA_REGIONS = dict(glass=(0, 0, 320, 256),
                     **{name: (336 + 264 * (k % 2) if k < 2 else 264 * ((k - 2) % 3),
                               0 if k < 2 else 264 + 200 * ((k - 2) // 3), 256, 192) for k, name in enumerate(PAPERS)},
                     **{name: (880 + 24 * k, 0, 16, 256) for k, name in enumerate(BORDERS)})

# -- The focused clip ------------------------------------------------------------------------------------------------

FPS = 30
LENGTH = 240                 # 8 s
