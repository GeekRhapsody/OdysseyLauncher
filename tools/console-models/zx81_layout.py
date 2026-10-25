"""The ZX81's measurements, shared by zx81_print.py (which draws its printing and screens) and zx81.py (which builds
it). Plain Python: Blender's Python imports it too.

The ZX81 (1981), 167 x 175 x 40 mm, in front of the made-up portable television the ZX Spectrum's card has
(zx_spectrum_layout.py's TV, built by zx_spectrum.py). Millimetres: x from its middle (left to right), y back from its
front edge, z up from the table. The rest was measured from photographs on Wikimedia Commons (Evan-Amos's three-quarter
view, the keyboard straight on), scaled by its width.

A black wedge: its top slopes down from the back to a ridge across its width, and in front of the ridge, lower, the
flat membrane keyboard: 40 keys printed on it in four rows, each a pale grey rounded square with its letter, its red
symbol and the keywords round it.

Two textures. `print` (ATLAS square, PRINT_REGIONS): `top` (the top seen from above, planar-mapped onto every face facing
up: the embossed name, ZX81, the membrane), the television's front at zx_spectrum_layout's `tv` region (drawn by
zx_spectrum_print.py), and its swatches at zx_spectrum_layout's places. `media` (MEDIA_REGIONS): the screen at rest (the
inverse K cursor on white) and the screens a game loads through, each the whole screen, 320 x 256 pixels with its
white border: LOAD, LOAD "", the loading's bands twice, and the game.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 167.0, 175.0, 40.0
RIDGE = (62.0, 24.0, 69.0, 33.0)   # the ridge: the membrane meets it at (y, z); its top reaches the top at (y, z)
FRONT_Z = 16.0                     # the membrane's front edge


def profile():
    """The side outline, (y, z), anticlockwise seen from the right end: the bottom, the back, the top sloping down to
    the ridge, the ridge's rounded nose down to the membrane, the membrane sloping down to the front edge."""
    y0, z0, y1, z1 = RIDGE
    nose = [(y1 - (y1 - y0) * math.cos(math.radians(a)), z0 + (z1 - z0) * math.sin(math.radians(a)))
            for a in range(90, -1, -15)]
    return ([(2.0, 0.0), (DEPTH - 2.0, 0.0), (DEPTH, 2.0), (DEPTH, HEIGHT - 1.0), (DEPTH - 1.0, HEIGHT)] + nose
            + [(3.0, FRONT_Z + 1.0), (0.0, FRONT_Z - 2.0), (0.0, 2.0)])


def membrane_z(y):
    """The membrane's height at y."""
    return FRONT_Z + 1.0 + (RIDGE[1] - FRONT_Z - 1.0) * (y - 3.0) / (RIDGE[0] - 3.0)


KEY = dict(width=12.6, depth=9.0, radius=1.6)
PITCH = 15.0
ROWS = {1: 46.5, 2: 32.5, 3: 18.5, 4: 4.5}            # each row's keys' front edge, y: the keywords between
KEY_X = {1: -76.0, 2: -71.0, 3: -68.5, 4: -61.0}      # each row's first key's left edge, x (the shift key aside)
SHIFT = (-79.5, 14.0)                                 # the SHIFT key's left edge and width

# (name, row, letter, the red symbol on it, the word above it, the word below it)
KEYS = (
    [(f"d{c}", 1, c, red, "", "") for c, red in zip("1234567890", ["EDIT", "AND", "THEN", "TO", "←", "↓", "↑", "→",
                                                                   "GRAPHICS", "RUBOUT"])]
    + [(c.lower(), 2, c, red, up, down) for c, red, up, down in zip(
        "QWERTYUIOP", ['""', "OR", "STEP", "<=", "<>", ">=", "$", "(", ")", '"'],
        ["PLOT", "UNPLOT", "REM", "RUN", "RAND", "RETURN", "IF", "INPUT", "POKE", "PRINT"],
        ["SIN", "COS", "TAN", "INT", "RND", "STR$", "CHR$", "CODE", "PEEK", "TAB"])]
    + [(c.lower(), 3, c, red, up, down) for c, red, up, down in zip(
        "ASDFGHJKL", ["STOP", "LPRINT", "SLOW", "FAST", "LLIST", "**", "-", "+", "="],
        ["NEW", "SAVE", "DIM", "FOR", "GOTO", "GOSUB", "LOAD", "LIST", "LET"],
        ["ARCSIN", "ARCCOS", "ARCTAN", "SGN", "ABS", "SQR", "VAL", "LEN", "USR"])]
    + [("newline", 3, "NEW\nLINE", "FUNCTION", "", "")]
    + [("shift", 4, "SHIFT", "", "", "")]
    + [(c.lower(), 4, c, red, up, down) for c, red, up, down in zip(
        "ZXCVBNM", [":", ";", "?", "/", "*", "<", ">"], ["COPY", "CLEAR", "CONT", "CLS", "SCROLL", "NEXT", "PAUSE"],
        ["LN", "EXP", "AT", "", "IN KEY$", "NOT", "π"])]
    + [("stop", 4, ".", ",", "", ""), ("space", 4, "SPACE", "£", "BREAK", "")]
)


def keys_with_rects():
    """Each key with its footprint, (x0, y0, x1, y1)."""
    out, counts = [], {}
    for k in KEYS:
        name, row = k[0], k[1]
        if name == "shift":
            x0, w = SHIFT
        else:
            index = counts.get(row, 0)
            counts[row] = index + 1
            x0, w = KEY_X[row] + index * PITCH, KEY["width"]
        out.append((k, (x0, ROWS[row], x0 + w, ROWS[row] + KEY["depth"])))
    return out


MEMBRANE = (-81.5, 81.5, 3.0, 59.0)   # the keyboard's printed panel: x0, x1, y0, y1

# The printing on the top: the embossed name across the back, ZX81 in red.
NAME = dict(x=-74.0, y=158.0, height=13.0)
MODEL = dict(x=-60.0, y=96.0, height=8.0)

COLOURS = dict(case="#232325", membrane="#1A1A1C", key="#D9D9D6")

PRINT_REGIONS = dict(top=(0, 0, 600, 630))     # the television's front and the swatches are zx_spectrum_layout's

SCREENS = ["load", "load2", "bands_a", "bands_b", "game"]
MEDIA_REGIONS = dict(glass=(0, 0, 320, 256), load=(336, 0, 320, 256), load2=(672, 0, 320, 256),
                     bands_a=(0, 272, 320, 256), bands_b=(336, 272, 320, 256), game=(672, 272, 320, 256))

FPS = 30
LENGTH = 240                 # 8 s
