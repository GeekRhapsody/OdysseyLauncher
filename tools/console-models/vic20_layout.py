"""The Commodore VIC-20's measurements, shared by vic20_print.py (which draws its printing) and vic20.py (which builds
it). Plain Python: Blender's Python imports it too.

The VIC-20 (1981), 403 x 204 x 72 mm (Carleton University's and Museum Wales's records), a cartridge in its expansion
port, behind it zx_spectrum.py's portable television (TV, its front's middle at TV_AT). Millimetres: x from the
computer's middle (left to right), y back from its front, z up from the table. The rest was measured from
Evan-Amos's photographs on Wikimedia Commons (the computer from its front corners) and the Tietokonemuseo's (with its
cartridges and datasette), scaled by its width and by its keys' 19.05 mm pitch.

The breadbin: its rounded front rising from the seam, the top sloping up to the back, which rounds over; the keyboard
in its well, the function keys in a well of their own at the right; the badge (commodore and the gold VIC 20 plate) at
the top left, the power light at the top right, ribs along the back. The power switch is a rocker in its right end,
the expansion port an opening in its back at the left.

The keys are laid out in units of U from the main block's left edge (KEYS_X0), in rows from the front (row 5, the
space bar's) to the back (row 1, the digits'). The top is a plane at SLOPE: a key stands on it in the slope's frame (x
across, s up the slope from its front edge, h off it), and top_point() maps a point of that frame to the model's
(y, z).

Two textures. `print` (ATLAS square, REGIONS): `top` (the computer seen from above: the key tops and legends, the
badge, the power light, the ribs; planar-mapped onto every face facing up), `label` (the cartridge's: a made-up game,
Odyssey), and swatches; the television's front is drawn where zx_spectrum_layout.py's PRINT_REGIONS["tv"] puts it,
and its swatches where its PRINT_SWATCHES do, as television() maps them. `media` (MEDIA_REGIONS): the glass's screens
(`boot`, at rest: CBM BASIC V2 and READY.; `title`, the game's), each the glass's whole area, the border round the
VIC's 176 x 184 pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 403.0, 204.0, 72.0
SEAM = 12.0                                  # the seam round it, between the base and the top
FRONT = dict(top=(12.0, 50.0), r=12.0)       # the top's front edge (y, z), rounded down into the front face
BACK = (186.0, HEIGHT)                       # where the top meets the back's rounding
SLOPE = math.atan2(BACK[1] - FRONT["top"][1], BACK[0] - FRONT["top"][0])


def profile():
    """The side outline, (y, z), anticlockwise seen from its right end: the front face, its rounding into the top, the
    top sloping up, the back rounding down."""
    (fy, fz), r = FRONT["top"], FRONT["r"]
    front = [(fy + r * math.cos(math.radians(a)), fz - r + r * math.sin(math.radians(a))) for a in range(90, 181, 15)]
    by, bz = BACK
    back = [(by + (DEPTH - by) * math.sin(math.radians(a)), bz - 10.0 + 10.0 * math.cos(math.radians(a)))
            for a in range(0, 91, 15)]
    return [(3.0, 0.0), (DEPTH - 3.0, 0.0), (DEPTH, 3.0)] + list(reversed(back)) + front + [(0.0, 3.0)]


def top_point(s, h):
    """The model's (y, z) of the point s up the top's slope from its front edge and h off it."""
    (fy, fz) = FRONT["top"]
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return fy + s * c - h * k, fz + s * k + h * c


# The keyboard: KEYS_X0 is the main block's left edge, U a key's pitch, GAP between two keys. A key stands from the
# well's floor (WELL below the top) to its top, KEY_HEIGHT above it, tapering by KEY_INSET on every side.
U, GAP = 19.05, 1.0
KEYS_X0 = -186.0
ROW_S = {5: 4.0, 4: 23.05, 3: 42.1, 2: 61.15, 1: 80.2}      # each row's front edge, up the slope
WELL, KEY_HEIGHT, KEY_INSET = 4.0, 10.0, 2.6
FKEYS_X = 138.0                                             # the function keys' left edge
FKEY_W = 1.5                                                # their width, in units


def kx(u):
    return KEYS_X0 + u * U


def key_rect(xu, row, wu):
    """A key's base, (x0, s0, x1, s1) in the slope's frame."""
    s0, s1 = ROW_S[row], ROW_S[row] + U
    return kx(xu) + GAP / 2, s0 + GAP / 2, kx(xu + wu) - GAP / 2, s1 - GAP / 2


def _row(names, x0, row, legends):
    return [(n, x0 + i, row, 1.0, "brown", legend) for i, (n, legend) in enumerate(zip(names, legends))]


# (name, x in units, row, width in units, "brown" or "tan", legend): a legend's line breaks split its upper and lower
# parts.
KEYS = (
    _row(["arrow"] + [f"d{k}" for k in "1234567890"] + ["plus", "minus", "pound", "home", "del"], 0.0, 1,
         ["←", "!\n1\nBLK", '"\n2\nWHT', "#\n3\nRED", "$\n4\nCYN", "%\n5\nPUR", "&\n6\nGRN", "'\n7\nBLU", "(\n8\nYEL",
          ")\n9\nRVS ON", "0\nRVS OFF", "+", "−", "£", "CLR\nHOME", "INST\nDEL"])
    + [("ctrl", 0.0, 2, 1.5, "brown", "CTRL")]
    + _row(list("qwertyuiop") + ["at", "star", "up"], 1.5, 2, list("QWERTYUIOP") + ["@", "*", "↑\nπ"])
    + [("restore", 14.5, 2, 1.5, "brown", "RESTORE")]
    + [("stop", 0.0, 3, 1.0, "brown", "RUN\nSTOP"), ("lock", 1.0, 3, 1.0, "brown", "SHIFT\nLOCK")]
    + _row(list("asdfghjkl") + ["colon", "semicolon", "equals"], 2.0, 3, list("ASDFGHJKL") + ["[\n:", "]\n;", "="])
    + [("return", 14.0, 3, 2.0, "brown", "RETURN")]
    + [("cbm", 0.0, 4, 1.0, "brown", "C="), ("lshift", 1.0, 4, 1.5, "brown", "SHIFT")]
    + _row(list("zxcvbnm") + ["comma", "period", "slash"], 2.5, 4, list("ZXCVBNM") + ["<\n,", ">\n.", "?\n/"])
    + [("rshift", 12.5, 4, 1.5, "brown", "SHIFT"), ("crsr_v", 14.0, 4, 1.0, "brown", "↑\nCRSR\n↓"),
       ("crsr_h", 15.0, 4, 1.0, "brown", "←\nCRSR\n→")]
    + [("space", 3.0, 5, 9.0, "brown", "")]
)
FKEYS = [(f"f{2 * k + 1}", row, f"f {2 * k + 1}\nf {2 * k + 2}") for k, row in enumerate((1, 2, 3, 4))]


def wells():
    """The wells the keys stand in, each an (x, s) outline: the main block (its front row only the space bar) and the
    function keys'."""
    m = 1.2
    s5, s4, s1 = ROW_S[5] - m, ROW_S[4] - m, ROW_S[1] + U + m

    def rect(x0, x1, a, b):
        return [(x0, a), (x1, a), (x1, b), (x0, b)]
    return [
        [(kx(3.0) - m, s5), (kx(12.0) + m, s5), (kx(12.0) + m, s4), (kx(16.0) + m, s4), (kx(16.0) + m, s1),
         (kx(0.0) - m, s1), (kx(0.0) - m, s4), (kx(3.0) - m, s4)],
        rect(FKEYS_X - m, FKEYS_X + FKEY_W * U + m, ROW_S[4] - m, s1),
    ]


# The top's printing behind the keys: the badge, the power light, the ribs.
BADGE = dict(x=(-186.0, -40.0), s=(112.0, 122.0), plate=(-92.0, -40.0))
LIGHT = dict(x=152.0, s=114.0, r=1.8)
RIBS = dict(s=[132.0 + 4.0 * k for k in range(7)])          # along the top's back, up the slope

PORT = dict(x=(-172.0, -82.0), z=(18.0, 30.0), depth=24.0)   # the expansion port in its back
SWITCH = dict(y=(150.0, 168.0), z=(28.0, 40.0), out=2.5)     # the power switch's rocker, in its right end
CART = dict(size=(132.0, 92.0, 17.0), edge=(88.0, 9.0, 1.6), label=(110.0, 66.0))   # w, d, h; its connector's edge
                                                                                   # w, out, thick; its label w, d

TV_AT = (0.0, 318.0)                                         # the television's front's middle, in the computer's (x, y)

COLOURS = dict(case="#E9E2CB", key="#4A382D", tan="#C49A62", dark="#141416", cart="#EFEBE0")

REGIONS = dict(top=(0, 0, 1024, 520), label=(640, 640, 330, 200))
SWATCHES = dict(red=(536, 600), lit=(568, 600), dark=(600, 600), cart=(632, 600), key=(664, 600), tan=(696, 600))

SCREEN_PX = (406, 312)        # a screen's region, the glass's proportions (two pixels a millimetre)
VIC_PX = (176, 184)           # the VIC's picture, its 22 x 23 characters, in the middle of its border
MEDIA_REGIONS = dict(boot=(0, 0) + SCREEN_PX, title=(0, 320) + SCREEN_PX, black=(416, 0, 32, 32))

FPS = 30
LENGTH = 240                  # 8 s
