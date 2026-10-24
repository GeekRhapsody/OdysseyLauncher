"""The Amiga 500 and its Commodore 1084S monitor: the measurements shared by amiga_print.py (which draws their printing)
and amiga.py (which builds them). Plain Python: Blender's Python imports it too.

Millimetres. The computer: x from its middle (left to right), y back from its front edge, z up from the table. It's
474 x 330 x 62 mm: a wedge whose keyboard deck rises from a low front edge to a step, behind which the raised back
(the AMIGA lettering, nine vent grooves) rounds over into the comb of fins along its back edge, with the floppy drive
in its right end. The monitor stands behind it, its front MONITOR["at"]: 357 x 330 mm, its hood shortened from the
real 378 mm to 302 (the launcher fits a card's largest side, so the set's depth would draw it smaller than the other
cards). The rest was measured from photographs on Wikimedia Commons (front views of the set, a top view, views of each
end and of the back, and a 1084S from the side), scaled by the computer's width.

The keyboard is the UK one. Its keys are laid out in units of U from the main block's left edge (KEYS_X0) and in rows
from the front (row 5, the space bar's) to the back (row 1, the digits'), with the function keys behind them as row 0.
The deck is a plane at SLOPE: a key stands on it in the slope's frame (x across, s up the slope from the deck's front
edge, h off it), and deck_point() maps a point of that frame to the model's (y, z).

Two textures. `print` (ATLAS square, PRINT_REGIONS): `top` (the computer's top seen from above: the key tops and their
legends, the badge and lights, the AMIGA lettering; planar-mapped onto every face facing up) and `badge` (the
monitor's), and swatches for plain parts. `media` (MEDIA_REGIONS): `kickstart` (the glass at rest: Kickstart 1.3's
hand holding a disk) and `title` (the game's title screen), each the glass's whole width and height with the raster
in its middle, drawn at the Amiga's 320 x 256 pixels; `disk_top` and `disk_bottom` (the floppy's two sides, as seen
looking at each, its shutter to the left); and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

# -- The computer ----------------------------------------------------------------------------------------------------

WIDTH, DEPTH = 474.0, 330.0
DECK = ((6.0, 23.0), (179.0, 39.0))     # the keyboard deck's front and back edges, (y, z)
SLOPE = math.atan2(DECK[1][1] - DECK[0][1], DECK[1][0] - DECK[0][0])
TOP_Z = 61.5                            # the raised back's top
STEP_Y = 186.0                          # where the step up from the deck meets it
FINS = dict(y=300.0, z=44.0)            # the top rounds over from y to the back edge, down to z there


def profile():
    """The computer's side outline, (y, z), anticlockwise seen from its right end."""
    fy, fz = FINS["y"], FINS["z"]
    back = [(fy + (DEPTH - fy) * math.sin(math.radians(a)), fz + (TOP_Z - fz) * math.cos(math.radians(a)))
            for a in range(90, -1, -10)]
    front = [(6.0 - 6.0 * math.sin(math.radians(a)), 17.0 + 6.0 * math.cos(math.radians(a))) for a in range(0, 91, 15)]
    return ([(2.5, 0.0), (DEPTH - 2.5, 0.0), (DEPTH, 2.5)] + back + [(STEP_Y, TOP_Z), DECK[1], DECK[0]]
            + front[1:] + [(0.0, 2.5)])


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return DECK[0][0] + s * c - h * k, DECK[0][1] + s * k + h * c


GROOVES = dict(x=(-211.0, 181.0), y=[222.0 + 8.4 * k for k in range(9)], width=2.4, depth=2.0)
FIN_GAPS = dict(x=[-228.0 + 5.6 * k for k in range(82)], width=2.6, y=(297.0, 340.0), z=(41.0, 70.0))
DRIVE = dict(recess=(190.0, 300.0, 22.0, 48.0, 1.2),   # the drive's panel in the right end: y0, y1, z0, z1, depth
             slot=(197.0, 293.0, 31.5, 38.5, 22.0),
             eject=(276.0, 290.0, 24.5, 29.0, 2.0))    # the eject button, standing out of the panel

# The keyboard: KEYS_X0 is the main block's left edge, U a key's pitch, GAP between two keys. A key stands from the
# well's floor (WELL below the deck) to its top, KEY_HEIGHT above the deck, tapering by KEY_INSET on every side.
U, GAP = 18.2, 0.9
KEYS_X0 = -220.5
ROW_S = {5: 20.0, 4: 38.2, 3: 56.4, 2: 74.6, 1: 92.8}  # each row's front edge, up the slope
FROW = (117.5, 16.0)                                   # the function keys' row: its front edge and depth
WELL, KEY_HEIGHT, KEY_INSET = 3.0, 9.0, 2.2


def kx(u):
    return KEYS_X0 + u * U


def key_rect(xu, row, wu, rows=1):
    """A key's base, (x0, s0, x1, s1) in the slope's frame."""
    if row == 0:
        s0, s1 = FROW[0], FROW[0] + FROW[1]
    else:
        s0, s1 = ROW_S[row + rows - 1], ROW_S[row] + U
    return kx(xu) + GAP / 2, s0 + GAP / 2, kx(xu + wu) - GAP / 2, s1 - GAP / 2


def _row(names, x0, row, colour, legends):
    return [(n, x0 + i, row, 1.0, colour, legend) for i, (n, legend) in enumerate(zip(names, legends))]


# (name, x in units, row, width in units, "light" or "dark", legend[, rows]): a legend's line break splits its upper and
# lower characters.
KEYS = (
    [("esc", 0.0, 0, 1.1, "dark", "Esc")]
    + [(f"f{k + 1}", 1.9 + 1.25 * k, 0, 1.25, "dark", f"F{k + 1}") for k in range(5)]
    + [(f"f{k + 6}", 8.65 + 1.25 * k, 0, 1.25, "dark", f"F{k + 6}") for k in range(5)]
    + [("grave", 0.0, 1, 1.5, "dark", "~\n`")]
    + _row([f"d{k}" for k in "1234567890"], 1.5, 1, "light", ["!\n1", '"\n2', "£\n3", "$\n4", "%\n5", "^\n6", "&\n7", "*\n8",
                                                              "(\n9", ")\n0"])
    + _row(["minus", "equals", "backslash"], 11.5, 1, "light", ["_\n-", "+\n=", "|\n\\"])
    + [("backspace", 14.5, 1, 1.5, "dark", "←")]
    + [("tab", 0.0, 2, 1.5, "dark", "⇥")]
    + _row(list("qwertyuiop"), 1.5, 2, "light", list("QWERTYUIOP"))
    + _row(["lbracket", "rbracket"], 11.5, 2, "light", ["{\n[", "}\n]"])
    + [("return_top", 13.6, 2, 2.4, "dark", "↵")]
    + [("ctrl", 0.0, 3, 1.0, "dark", "Ctrl"), ("caps", 1.0, 3, 1.0, "dark", "Caps\nLock")]
    + _row(list("asdfghjkl"), 2.0, 3, "light", list("ASDFGHJKL"))
    + _row(["semicolon", "quote", "hash"], 11.0, 3, "light", [":\n;", "@\n'", "~\n#"])
    + [("return_bottom", 14.1, 3, 1.9, "dark", "")]
    + [("lshift", 0.0, 4, 2.5, "dark", "⇧")]
    + _row(list("zxcvbnm"), 2.5, 4, "light", list("ZXCVBNM"))
    + _row(["comma", "period", "slash"], 9.5, 4, "light", ["<\n,", ">\n.", "?\n/"])
    + [("rshift", 12.5, 4, 3.5, "dark", "⇧")]
    + [("lalt", 0.4, 5, 1.4, "dark", "Alt"), ("lamiga", 1.8, 5, 1.4, "dark", "A"), ("space", 3.2, 5, 9.2, "light", ""),
       ("ramiga", 12.4, 5, 1.4, "dark", "A"), ("ralt", 13.8, 5, 1.4, "dark", "Alt")]
    + [("del", 16.4, 1, 1.5, "dark", "Del"), ("help", 17.9, 1, 1.5, "dark", "Help")]
    + [("up", 17.6, 3, 1.0, "light", "↑"), ("left", 16.6, 4, 1.0, "light", "←"), ("down", 17.6, 4, 1.0, "light", "↓"),
       ("right", 18.6, 4, 1.0, "light", "→")]
    + _row(["np_lpar", "np_rpar", "np_slash", "np_star"], 20.0, 1, "dark", ["(", ")", "/", "*"])
    + _row(["np7", "np8", "np9"], 20.0, 2, "light", ["7\nHome", "8\n↑", "9\nPg Up"])
    + [("np_minus", 23.0, 2, 1.0, "dark", "-")]
    + _row(["np4", "np5", "np6"], 20.0, 3, "light", ["4\n←", "5", "6\n→"])
    + [("np_plus", 23.0, 3, 1.0, "dark", "+")]
    + _row(["np1", "np2", "np3"], 20.0, 4, "light", ["1\nEnd", "2\n↓", "3\nPg Dn"])
    + [("np_enter", 23.0, 4, 1.0, "dark", "Enter", 2)]
    + [("np0", 20.0, 5, 2.0, "light", "0\nIns"), ("np_dot", 22.0, 5, 1.0, "light", ".\nDel")]
)


def wells():
    """The wells the keys stand in, each an (x, s) outline: the main block (its bottom row ends short), the function
    keys in three groups, Del and Help, the cursor keys' T, and the numeric pad."""
    m = 1.0
    s5, s4, s3, s1 = ROW_S[5] - m, ROW_S[4], ROW_S[3], ROW_S[1] + U + m
    f0, f1 = FROW[0] - m, FROW[0] + FROW[1] + m

    def rect(x0, x1, a, b):
        return [(x0, a), (x1, a), (x1, b), (x0, b)]
    return [
        [(kx(0) - m, s5), (kx(15.2) + m, s5), (kx(15.2) + m, s4), (kx(16) + m, s4), (kx(16) + m, s1), (kx(0) - m, s1)],
        rect(kx(0) - m, kx(1.1) + m, f0, f1),
        rect(kx(1.9) - m, kx(8.15) + m, f0, f1),
        rect(kx(8.65) - m, kx(14.9) + m, f0, f1),
        rect(kx(16.4) - m, kx(19.4) + m, ROW_S[1] - m, s1),
        [(kx(16.6) - m, s4 - m), (kx(19.6) + m, s4 - m), (kx(19.6) + m, s3), (kx(18.6) + m, s3),
         (kx(18.6) + m, ROW_S[3] + U + m), (kx(17.6) - m, ROW_S[3] + U + m), (kx(17.6) - m, s3), (kx(16.6) - m, s3)],
        rect(kx(20) - m, kx(24) + m, s5, s1),
    ]


# The printing on the deck, in the top's (x, y): the Commodore badge, and the power and drive lights' bars.
BADGE = dict(x=185.0, y=158.0, size=13.0)
LIGHTS = dict(x=(181.0, 196.0), power=133.5, drive=127.5, width=1.8)  # their bars' x, each one's y, their width
LETTERING = dict(x=186.0, y=201.0, height=13.5)                       # AMIGA: its right edge and middle

# -- The monitor -----------------------------------------------------------------------------------------------------

MONITOR = dict(
    at=(-8.0, 334.0),                   # its front's middle, in the computer's (x, y)
    width=357.0,
    # Its side outline, (y back from its front, z): the front's full height, a step, then the hood sloping down to
    # the back.
    profile=[(3.0, 0.0), (296.0, 0.0), (302.0, 6.0), (302.0, 236.0), (206.0, 314.0), (198.0, 314.0), (192.0, 330.0),
             (4.0, 330.0), (0.0, 326.0), (0.0, 3.0)],
    bezel=dict(x=170.5, z=(58.0, 322.0), depth=2.5),          # the bezel's panel, sunk into the front
    seams=(56.0, 8.0),                                        # the control flap's top and bottom, below it
    opening=dict(z=202.0, outer=(277.0, 196.0, 14.0), inner=(262.0, 186.0, 9.0), depth=18.5),
    glass=dict(size=(268.0, 192.0), bulge=7.0),               # the glass, from the opening's inner edge to its middle
    badge=dict(x=(-160.0, -98.0), z=(79.0, 91.0)),
    vents=dict(y=(184.0, 284.0), z=[24.0 + 6.0 * k for k in range(14)], height=2.6),  # the grilles in its sides
)

# -- The floppy disk -------------------------------------------------------------------------------------------------

DISK = dict(length=94.0, width=90.0, thickness=3.3)   # its shutter's edge first: length along x, width along y
SEAT = (WIDTH / 2 - DISK["length"] / 2 - 8.0, (DRIVE["slot"][0] + DRIVE["slot"][1]) / 2,
        (DRIVE["slot"][2] + DRIVE["slot"][3]) / 2)    # its middle, in the drive

# -- The atlases -----------------------------------------------------------------------------------------------------

COLOURS = dict(case="#D8D1BE", key_light="#DEDACC", key_dark="#A29D8E", top_light="#ECE9DE", top_dark="#B3AE9F",
               bezel="#C6BFAD", dark="#1B1A18", disk="#24439C")

PRINT_REGIONS = dict(top=(0, 0, 1024, 713), badge=(0, 722, 400, 78))
PRINT_SWATCHES = dict(bezel=(16, 836), lit=(48, 836), black=(80, 836))  # each a 24 x 24 block's middle, in pixels

SCREEN_PX = (640, 460)       # a screen's region, the glass's proportions
RASTER = (576, 432)          # the lit picture in its middle, 4:3; the Amiga's 320 x 256 pixels drawn into it
MEDIA_REGIONS = dict(kickstart=(0, 0) + SCREEN_PX, title=(0, 468) + SCREEN_PX, disk_top=(648, 0, 376, 360),
                     disk_bottom=(648, 368, 376, 360))
MEDIA_SWATCHES = dict(black=(664, 752), edge=(696, 752))

# -- The focused clip ------------------------------------------------------------------------------------------------

FPS = 30
LENGTH = 240                 # 8 s
