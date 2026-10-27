"""The ZX Spectrum Next card's measurements, shared by zxnext_print.py (which draws its printing and screens) and
zxnext.py (which builds it). Plain Python: Blender's Python imports it too.

The ZX Spectrum Next (the cased machine of 2020, Rick Dickinson's design) in front of the portable television the ZX
Spectrum's card has (zx_spectrum.py's, its front's middle at TV_AT). No published size was found; it is about 312 x 125
x 25 mm, scaled from its VGA socket's screw posts (25 mm apart) in a photograph of its back, the rest measured from
photographs of it from above (its legends readable), from each end, from behind and beside a 48K. Millimetres: x from
its middle (left to right), y back from its front, z up from the table.

The computer: a thin black slab, its top rising a little to the back from the rounded front lip, its right end rounded
over; 58 chiclet keys in five rows (KEYS, in key units U of KEY_PITCH from the keyboard's left edge, each row from the
back); the plain panel right of the keys carrying the rows on as five bands, the four grooves between them holding the
stripes (red, yellow, green, cyan from the back), which run over the rounded end; sinclair moulded at the back left with
ZX Spectrum Next in red under it, the vents along the back edge; RESET (red), DRIVE (green), the SD slot and NMI
(yellow) in the left end; JOY 1 and JOY 2 under the front lip.

Two textures. `print` (ATLAS square, PRINT_REGIONS): `top` (the Next from above, planar-mapped onto every face facing up:
the keys' tops and legends, the logo, the bands and stripes, the vents), `end` (the right end, its stripes) and `left`
(the left end: its buttons' and the slot's names); the television's front where zx_spectrum_layout.PRINT_REGIONS puts it
and its swatches where its PRINT_SWATCHES do, as television() maps them. `media` (MEDIA_REGIONS): the screens, the
border round the paper (the start-up menu, the browser with the game chosen, the game's title, two moments of it).
"""

import math

ATLAS = 1024

WIDTH, DEPTH = 312.0, 125.0
FRONT = (8.0, 19.0)              # the top's front edge (y, z), over the rounded lip
BACK = (DEPTH, 23.0)             # its back edge
PROFILE = [(3.0, 0.0), (DEPTH - 2.0, 0.0), (DEPTH, 2.0), BACK, FRONT, (2.0, 16.0), (0.0, 11.0), (0.0, 3.0)]
END = dict(radius=22.0, steps=8)                 # the right end rounded over

KEY_PITCH = 17.4
KEYS_X0 = -146.0                 # the keyboard's left edge
ROW_FRONT = 11.0                 # the front row's front edge
KEY = dict(gap=1.8, height=4.5, inset=1.0, r=3.0)
# Each row from the back: (legend, width in U); a key's legends are its main one and its keyword (SMALL).
KEYS = [
    [("BREAK", 1), ("EDIT", 1)] + [(c, 1) for c in "1234567890"] + [("DELETE", 1.5)],
    [("TRUE VIDEO", 1.25), ("INV VIDEO", 1)] + [(c, 1) for c in "QWERTYUIOP"] + [("ENTER", 1.25)],
    [("CAPS LOCK", 1.5), ("GRAPH", 1)] + [(c, 1) for c in "ASDFGHJKL"] + [("ENTER", 2.0)],
    [("CAPS SHIFT", 2.0), ("EXTEND MODE", 1)] + [(c, 1) for c in "ZXCVBNM"] + [("⇧", 1), ("CAPS SHIFT", 2.5)],
    [("SYMBOL SHIFT", 1.5), (";", 1), ('"', 1), (",", 1), (".", 1), (" ", 3.5), ("⇦", 1), ("⇩", 1), ("⇨", 1),
     ("SYMBOL SHIFT", 1.5)],
]
KEYWORDS = dict(zip("1234567890QWERTYUIOPASDFGHJKLZXCVBNM", (
    "DEF FN", "FN", "LINE", "OPEN #", "CLOSE #", "MOVE", "ERASE", "POINT", "CAT", "FORMAT",
    "PLOT", "DRAW", "REM", "RUN", "RAND", "RETURN", "IF", "INPUT", "POKE", "PRINT",
    "NEW", "SAVE", "DIM", "FOR", "GOTO", "GOSUB", "LOAD", "LIST", "LET",
    "COPY", "CLEAR", "CONT", "CLS", "BORDER", "NEXT", "PAUSE")))
COLOUR_KEYS = dict(zip("1234567890", ("BLUE", "RED", "MAGENTA", "GREEN", "CYAN", "YELLOW", "WHITE", "", "", "BLACK")))

PANEL = dict(x=(KEYS_X0 + 13.5 * KEY_PITCH + 3.0, WIDTH / 2))   # the plain panel right of the keys, its bands
STRIPES = ["#D9383F", "#E8C23A", "#6DBE45", "#2FB5E3"]             # in its grooves, from the back
LOGO = dict(x=-146.0, y=110.0)                                    # sinclair, its left end's baseline
VENTS = dict(x=(14.0, 100.0), y=(112.0, 120.0), count=22)
BUNG = dict(x=(0.0, 12.0), y=(116.0, DEPTH), height=3.0)          # the cover on the back edge
BUTTONS = dict(reset=(26.0, "#D02828"), drive=(44.0, "#2FA454"), nmi=(96.0, "#E8C23A"), z=12.0, r=3.4, out=1.6)
SD = dict(y=(58.0, 84.0), z=(9.0, 12.0))                          # the SD slot in the left end

TV_AT = (0.0, 140.0)             # the television's front's middle

COLOURS = dict(case="#1F2126", key="#2B2C30", legend="#E6E6E6", red="#D23B2A", print="#FFFFFF", dark="#0A0A0B")

PRINT_REGIONS = dict(top=(0, 0, 1024, 410), end=(0, 420, 500, 100), left=(520, 420, 500, 100))
SWATCHES = dict(case=(664, 600), key=(696, 600), dark=(728, 600), reset=(760, 600), drive=(792, 600), nmi=(824, 600))

SCREEN_PX = (320, 256)           # the glass: the border round the Next's 256 x 192 paper
PAPER = (256, 192)
MEDIA_REGIONS = dict(menu=(0, 0, 320, 256), browser=(336, 0, 320, 256), title=(672, 0, 320, 256),
                     game1=(0, 272, 320, 256), game2=(336, 272, 320, 256))

FPS = 30
LENGTH = 240                 # 8 s


def top_z(y):
    """The top's height at y."""
    (y0, z0), (y1, z1) = FRONT, BACK
    return z0 + (z1 - z0) * (y - y0) / (y1 - y0)


def keys():
    """Every key: (legend, x0, x1, y0, y1), its rows from the back; ENTER's two parts are one key, an L (two
    rectangles with the same legend)."""
    out = []
    for r, row in enumerate(KEYS):
        x = KEYS_X0
        y1 = ROW_FRONT + (len(KEYS) - r) * KEY_PITCH
        for legend, w in row:
            out.append((legend, x, x + w * KEY_PITCH, y1 - KEY_PITCH, y1))
            x += w * KEY_PITCH
    return out


SLOPE = math.atan2(BACK[1] - FRONT[1], BACK[0] - FRONT[0])
