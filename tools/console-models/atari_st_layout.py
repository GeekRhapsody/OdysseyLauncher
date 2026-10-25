"""The Atari 520STFM, its SC1224 monitor and its mouse: the measurements shared by atari_st_print.py (which draws their
printing) and atari_st.py (which builds them). Plain Python: Blender's Python imports it too.

Millimetres: x from the computer's middle (left to right), y back from its front edge, z up from the table. The
computer is 478 x 290 x 62 mm: the keyboard deck sloping up from the low front edge, the band behind it with the ten
function keys on its sloping face and the badge at its right, then, past a groove, the raised back, its top a panel of
diagonal ribs, the floppy drive in its right end. The monitor stands behind it, its front MONITOR["at"], 356 x 279 mm,
its body cut from about 350 mm deep to 236 (the launcher fits a card's largest side). The mouse lies to the
computer's right. Measured from photographs: the Bibliotheque nationale de France's set of a 520ST (from above, each
side, the back), Evan-Amos's 1040STF with an SC1224 on Wikimedia Commons, and two SC1224s side by side; scaled by the
keys' 19.05 mm pitch and the SC1224's 279 mm height (the Computer History Museum's record).

The keyboard is the UK one. Its keys are laid out in units of U from the main block's left edge (KEYS_X0), in rows
from the front (row 5, the space bar's) to the back (row 1, the digits'). The deck is a plane at SLOPE: a key stands on
it in the slope's frame (x across, s up the slope from the deck's front edge, h off it), and deck_point() maps a point
of that frame to the model's (y, z). The function keys stand on the band's face, a plane of its own (band_point()).

Two textures. `print` (ATLAS square, PRINT_REGIONS): `top` (the computer seen from above: the key tops and legends, the
function keys, the badge and the lights; planar-mapped onto every face facing up), `badge` (the monitor's: ATARI and
SC1224), `mouse` (its back), and swatches. `media` (MEDIA_REGIONS): the screens, each the glass's whole width and
height with the ST's 320 x 200 in its middle (`desktop`, the glass at rest: GEM's desktop with its two floppy disks and
the trash; `window`, the floppy's window open over it, ODYSSEY.PRG chosen; `title`, the title screen of a made-up game,
Odyssey), and the floppy's two sides. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

# -- The computer ----------------------------------------------------------------------------------------------------

WIDTH, DEPTH, HEIGHT = 478.0, 290.0, 62.0
DECK = ((5.0, 27.0), (112.0, 40.0))     # the deck's front and back edges, (y, z)
SLOPE = math.atan2(DECK[1][1] - DECK[0][1], DECK[1][0] - DECK[0][0])
BAND = ((114.0, 45.0), (150.0, 60.0))   # the band's face: its front (bottom) and back (top) edges, (y, z)
GROOVE = (152.0, 157.0, 3.0)            # between the band and the raised back: y0, y1, depth
FOOT = 3.0                              # the dark foot band under the case


def profile():
    """The computer's side outline, (y, z), anticlockwise seen from its right end."""
    (fy, fz), (by, bz) = BAND
    return [(3.0, 0.0), (DEPTH - 3.0, 0.0), (DEPTH, 3.0), (DEPTH, HEIGHT - 5.0), (DEPTH - 5.0, HEIGHT),
            (by + 2.0, HEIGHT), (by, bz), (fy, fz), (DECK[1][0], DECK[1][1]), DECK[0], (0.0, DECK[0][1] - 4.0),
            (0.0, 3.0)]


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return DECK[0][0] + s * c - h * k, DECK[0][1] + s * k + h * c


BAND_SLOPE = math.atan2(BAND[1][1] - BAND[0][1], BAND[1][0] - BAND[0][0])


def band_point(s, h):
    """The model's (y, z) of the point s up the band's face from its bottom edge and h off it."""
    c, k = math.cos(BAND_SLOPE), math.sin(BAND_SLOPE)
    return BAND[0][0] + s * c - h * k, BAND[0][1] + s * k + h * c


VENT = dict(x=(-226.0, 226.0), y=(165.0, 283.0), depth=1.6, pitch=7.6, width=3.4)   # the ribbed panel on the top
DRIVE = dict(slot=(176.0, 268.0, 28.0, 33.0), bulge=(205.0, 239.0, 26.0, 37.0), depth=30.0,  # y0, y1, z0, z1
             eject=(252.0, 264.0, 15.0, 21.0, 1.6))                                         # ... and how far out

# The keyboard: KEYS_X0 is the main block's left edge, U a key's pitch, GAP between two keys. A key stands from the
# well's floor (WELL below the deck) to its top, KEY_HEIGHT above the deck, tapering by KEY_INSET on every side.
U, GAP = 19.05, 1.0
KEYS_X0 = -222.0
ROW_S = {5: 11.0, 4: 30.05, 3: 49.1, 2: 68.15, 1: 87.2}   # each row's front edge, up the slope
WELL, KEY_HEIGHT, KEY_INSET = 3.0, 9.5, 2.2
CURSOR_U, PAD_U = 15.9, 19.2                              # where the cursor block and the keypad start, in units


def kx(u):
    return KEYS_X0 + u * U


def key_rect(xu, row, wu, rows=1):
    """A key's base, (x0, s0, x1, s1) in the slope's frame (a tall key spans rows from row down)."""
    s0, s1 = ROW_S[row + rows - 1], ROW_S[row] + U
    return kx(xu) + GAP / 2, s0 + GAP / 2, kx(xu + wu) - GAP / 2, s1 - GAP / 2


def _row(names, x0, row, legends):
    return [(n, x0 + i, row, 1.0, legend) for i, (n, legend) in enumerate(zip(names, legends))]


# (name, x in units, row, width in units, legend[, rows]): a legend's line break splits its upper and lower characters.
# RETURN is an L over rows 2 and 3, its foot the wider (RETURN below).
KEYS = (
    [("esc", 0.0, 1, 1.0, "Esc")]
    + _row([f"d{k}" for k in "1234567890"] + ["minus", "equals", "grave"], 1.0, 1,
           ["!\n1", '"\n2', "£\n3", "$\n4", "%\n5", "^\n6", "&\n7", "*\n8", "(\n9", ")\n0", "_\n-", "+\n=", "~\n`"])
    + [("backspace", 14.0, 1, 1.5, "Backspace")]
    + [("tab", 0.0, 2, 1.5, "Tab")]
    + _row(list("qwertyuiop") + ["lbracket", "rbracket"], 1.5, 2, list("QWERTYUIOP") + ["{\n[", "}\n]"])
    + [("delete", 14.5, 2, 1.0, "Delete")]
    + [("control", 0.0, 3, 1.75, "Control")]
    + _row(list("asdfghjkl") + ["semicolon", "quote"], 1.75, 3, list("ASDFGHJKL") + [":\n;", "@\n'"])
    + [("hash", 14.5, 3, 1.0, "~\n#")]
    + [("lshift", 0.0, 4, 1.25, "Shift")]
    + _row(["backslash"] + list("zxcvbnm") + ["comma", "period", "slash"], 1.25, 4,
           ["|\n\\"] + list("ZXCVBNM") + ["<\n,", ">\n.", "?\n/"])
    + [("rshift", 12.25, 4, 1.75, "Shift")]
    + [("alternate", 1.5, 5, 1.5, "Alternate"), ("space", 3.0, 5, 8.75, ""), ("caps", 11.75, 5, 1.5, "CapsLock")]
    + [("help", CURSOR_U, 1, 1.5, "Help"), ("undo", CURSOR_U + 1.5, 1, 1.5, "Undo")]
    + _row(["insert", "up", "home"], CURSOR_U, 2, ["Insert", "↑", "Clr\nHome"])
    + _row(["left", "down", "right"], CURSOR_U, 3, ["←", "↓", "→"])
    + _row(["np_lpar", "np_rpar", "np_slash", "np_star"], PAD_U, 1, ["(", ")", "/", "*"])
    + _row(["np7", "np8", "np9", "np_minus"], PAD_U, 2, ["7", "8", "9", "-"])
    + _row(["np4", "np5", "np6", "np_plus"], PAD_U, 3, ["4", "5", "6", "+"])
    + _row(["np1", "np2", "np3"], PAD_U, 4, ["1", "2", "3"])
    + [("np_enter", PAD_U + 3.0, 4, 1.0, "Enter", 2), ("np0", PAD_U, 5, 2.0, "0"), ("np_dot", PAD_U + 2.0, 5, 1.0, ".")]
)
RETURN = dict(top=(13.5, 14.5), foot=(12.75, 14.5))       # its two rows' x, in units: row 3's foot the wider


def return_outline():
    """RETURN's base, an (x, s) outline anticlockwise from its foot's front left corner."""
    (a, b), (c, _) = RETURN["top"], RETURN["foot"]
    g = GAP / 2
    s3, s2, s1 = ROW_S[3] + g, ROW_S[2] + g, ROW_S[2] + U - g
    return [(kx(c) + g, s3), (kx(b) - g, s3), (kx(b) - g, s1), (kx(a) + g, s1), (kx(a) + g, s2), (kx(c) + g, s2)]


def wells():
    """The wells the keys stand in, each an (x, s) outline: the main block (its bottom row starting in, ending short),
    the cursor block, and the keypad."""
    m = 1.2
    s5, s4, s3, s1 = ROW_S[5] - m, ROW_S[4], ROW_S[3], ROW_S[1] + U + m

    def rect(x0, x1, a, b):
        return [(x0, a), (x1, a), (x1, b), (x0, b)]
    return [
        [(kx(1.5) - m, s5), (kx(13.25) + m, s5), (kx(13.25) + m, s4 - m), (kx(14.0) + m, s4 - m), (kx(14.0) + m, s3 - m),
         (kx(15.5) + m, s3 - m), (kx(15.5) + m, s1), (kx(0) - m, s1), (kx(0) - m, s4 - m), (kx(1.5) - m, s4 - m)],
        rect(kx(CURSOR_U) - m, kx(CURSOR_U + 3.0) + m, ROW_S[3] - m, s1),
        rect(kx(PAD_U) - m, kx(PAD_U + 4.0) + m, s5, s1),
    ]


# The function keys: ten slanted blades on the band's face, F1's left edge at FKEYS["x0"], each `width` across and
# leaning `lean` to the right at its top.
FKEYS = dict(x0=-216.0, width=31.4, gap=1.4, s=(5.0, 30.0), height=2.4, lean=9.0)
BADGE = dict(x=(117.0, 221.0), s=(17.0, 28.0))          # ATARI 520STFM on the band's face, right of the keys
LIGHTS = dict(drive=(200.0, 9.0), power=(-211.0, 4.0), size=(9.0, 1.6))  # x and s on the band (drive), the deck (power)

# -- The monitor -----------------------------------------------------------------------------------------------------

MONITOR = dict(
    at=(0.0, 300.0),                    # its front's middle, in the computer's (x, y)
    width=356.0, height=279.0, frame=36.0,                      # the front frame's size and depth
    body=dict(back=(270.0, 196.0), depth=236.0, lift=30.0),     # the body: its back's width and height; the whole
                                                                # monitor's depth; how high its back's bottom is
    opening=dict(z=130.0, outer=(282.0, 214.0, 16.0), inner=(266.0, 199.0, 10.0), depth=22.0),
    glass=dict(size=(268.0, 201.0), bulge=7.0),
    badge=dict(x=(-150.0, -36.0), z=(9.0, 21.0)), light=(118.0, 15.0),
)

# -- The mouse and the floppy ----------------------------------------------------------------------------------------

MOUSE = dict(at=(290.0, 74.0), size=(64.0, 100.0, 30.0), buttons=36.0, spin=-8.0)   # its middle; w, d, h; turned
DISK = dict(length=94.0, width=90.0, thickness=3.3)
SEAT = (WIDTH / 2 - DISK["length"] / 2 - 10.0, (DRIVE["slot"][0] + DRIVE["slot"][1]) / 2,
        (DRIVE["slot"][2] + DRIVE["slot"][3]) / 2)

# -- The atlases -----------------------------------------------------------------------------------------------------

COLOURS = dict(case="#B2AA95", keys="#CFC8B2", top_keys="#DCD6C2", vent="#9A9381", monitor="#B4BAB2", dark="#24231F",
               disk="#3C3E44")

PRINT_REGIONS = dict(top=(0, 0, 1024, 632), badge=(0, 640, 400, 44), mouse=(408, 640, 160, 250))
PRINT_SWATCHES = dict(lit=(600, 664), off=(632, 664), green=(664, 664), dark=(696, 664), vent=(728, 664),
                      monitor=(760, 664))

SCREEN_PX = (640, 480)       # a screen's region, the glass's proportions
RASTER = (576, 400)          # the lit picture in its middle; the ST's 320 x 200 drawn into it
MEDIA_REGIONS = dict(desktop=(0, 0) + SCREEN_PX, window=(0, 488) + SCREEN_PX, title=(648, 0, 376, 282),
                     disk_top=(648, 290, 376, 360), disk_bottom=(648, 658, 376, 360))
MEDIA_SWATCHES = dict(black=(24, 996), edge=(56, 996))

# -- The focused clip ------------------------------------------------------------------------------------------------

FPS = 30
LENGTH = 240                 # 8 s
