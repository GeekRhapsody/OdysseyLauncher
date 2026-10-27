"""The Dragon 32 card's measurements, shared by dragon32_print.py (which draws its printing and screens) and dragon32.py
(which builds it). Plain Python: Blender's Python imports it too.

The Dragon 32 (1982), 325 mm wide, 378 deep and 96 high (the museums' 322 to 325 x 375 to 380 x 90 to 98), in front of
the portable television the ZX Spectrum's card has (zx_spectrum.py's, its front's middle at TV_AT), a ROM cartridge with
a made-up game, Odyssey, going into the slot in its right side. Millimetres: x from its middle (left to right), y back
from its front, z up from the table. Measured from photographs on Wikimedia Commons (from above, which its keys' 19.05
mm pitch scales; its sides and back straight on; others from the front).

The computer: a beige wedge (PROFILE: the front, the slope up to the raised back block, its top, the chamfer to the
back); the keyboard's well sunk into the slope (WELL), its black keys standing in it in the slope's frame (KEYS, in
units of U across and rows up the slope); the DRAGON 32 badge on the slope behind them (BADGE), the ribs across the back
block's front (RIBS, grooves); the cartridge's slot in the right side (SLOT).

One texture `print` (ATLAS square, PRINT_REGIONS): `top` (the Dragon's front TOP millimetres from above: the keys' tops
and legends, the badge), `cartridge` (its label), and swatches; the television's front where zx_spectrum_layout.py's
PRINT_REGIONS["tv"] puts it and its swatches where its PRINT_SWATCHES do, as television() maps them. One `media`
(MEDIA_REGIONS): the screens, the VDG's 256 x 192 in its black border (the start-up screen in black on green, the game's
title, two moments of the game). A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024
U = 19.05

WIDTH, DEPTH, HEIGHT = 325.0, 378.0, 96.0
FRONT = (3.0, 41.0)               # the slope's front edge (y, z)
SLOPE_BACK = (165.0, 89.0)        # its back edge, at the back block's step
SLOPE = math.atan2(SLOPE_BACK[1] - FRONT[1], SLOPE_BACK[0] - FRONT[0])
PROFILE = [                       # the side outline (y, z), round from the front's foot
    (4.0, 0.0), (DEPTH - 4.0, 0.0), (DEPTH, 4.0), (DEPTH, 56.0), (DEPTH - 2.0, 60.0), (347.0, HEIGHT),
    (172.0, HEIGHT), (168.0, 92.0), SLOPE_BACK, FRONT, (0.0, FRONT[1] - 3.0), (0.0, 4.0),
]
WELL = dict(x=(-154.0, 154.0), s=(22.0, 132.0), depth=4.0, r=6.0)     # the keyboard's well, in the slope's frame
BADGE = dict(x=(-143.0, 22.0), s=(146.0, 160.0))
RIBS = dict(y=(178.0, 250.0), count=6)

KEYS_X0, ROW1 = -119.0, 113.0     # row 1's left edge; its middle (s)
KEY = dict(height=12.0, inset=2.4)
ROWS = [
    (0.0, [(c, 1.0) for c in "1234567890:-"] + [("BREAK", 1.0)]),
    (-0.75, [("↑", 1.0)] + [(c, 1.0) for c in "QWERTYUIOP@"] + [("←", 1.0), ("→", 1.0)]),
    (-0.5, [("↓", 1.0)] + [(c, 1.0) for c in "ASDFGHJKL;"] + [("ENTER", 2.0), ("CLEAR", 1.0)]),
    (-0.6, [("SHIFT", 1.5)] + [(c, 1.0) for c in "ZXCVBNM,./"] + [("SHIFT", 1.75)]),
    (1.95, [(" ", 8.4)]),
]
SHIFTED = dict(zip("1234567890:-", "!\"#$%&'()0*="))

SLOT = dict(y=(98.0, 181.0), z=(12.0, 31.0), depth=96.0)    # the cartridge's slot in the right side
# The cartridge: its length going in (x), its width (y) and thickness (z); how far out it waits; how much of it stands
# out of the slot when it is in.
CART = dict(size=(92.0, 80.0, 17.0), out=100.0, proud=4.0)

TV_AT = (0.0, 400.0)              # the television's front's middle

COLOURS = dict(case="#D9CDAE", key="#232325", print="#FFFFFF", dark="#0A0A0B")

# The machines built from it: the Dragon 32, and the Tano Dragon (the Dragon 64 Tano Corporation made in New Orleans
# for America), the same case in its own colours with its own badge, its screens one of tools/made-up-games's games in
# the VDG's colours (game: its file's stem and system).
KINDS = {
    "dragon32": dict(case=COLOURS["case"], key=COLOURS["key"], legend="#ECECE6", game=None),
    "tanodragon": dict(case="#E2DCC8", key="#2A2627", legend="#ECECE6", game=("Ghoulish Gus (Europe)", "megadrive")),
}

TOP = 175.0                       # how far back the top's region reaches (y): the slope, its keys and the badge
PRINT_REGIONS = dict(top=(0, 0, 1024, 551), cartridge=(620, 600, 200, 174))
SWATCHES = dict(case=(852, 620), key=(884, 620), dark=(916, 620), cart=(948, 620), rib=(852, 652))
MEDIA_REGIONS = dict(boot=(0, 0, 320, 246), title=(336, 0, 320, 246), game_1=(672, 0, 320, 246),
                     game_2=(0, 256, 320, 246))
VDG_PX = (256, 192)

FPS = 30
LENGTH = 240                 # 8 s


def slope_point(s, h):
    """The model's (y, z) of the point s up the slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return FRONT[0] + s * c - h * k, FRONT[1] + s * k + h * c


def keys():
    """Every key: (legend, x0, x1, s), s its row's middle up the slope; the rows from the back to the front."""
    out = []
    for r, (offset, row) in enumerate(ROWS):
        x = KEYS_X0 + offset * U
        s = ROW1 - r * U
        for legend, width in row:
            out.append((legend, x, x + width * U, s))
            x += width * U
    return out
