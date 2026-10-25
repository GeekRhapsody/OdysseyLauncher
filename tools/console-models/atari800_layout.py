"""The Atari 800 card's measurements, shared by atari800_print.py (which draws its printing) and atari800.py (which
builds it). Plain Python: Blender's Python imports it too.

The Atari 800 (1979), 400 mm wide, 318 deep and 124 high (a listing's 15.75 x 12.5 inches; the side photograph's
height), its CX40 joystick in front of it (atari_2600.py's), a made-up game, Odyssey, on the cartridge. Millimetres: x
from its middle (left to right), y back from its front, z up from the table. The rest was measured from Evan-Amos's
photographs on Wikimedia Commons (from the front left and right, the back right, the right side straight on, opened) and
another from the front left, scaled by its depth and by its keys' 19.05 mm pitch.

The computer: a shell standing BASE off the table on the joystick ports' block (under its front) and two feet; its side
outline (PROFILE) the front, the keyboard deck sloping up, the upper housing's sloping front face, its top flat then
falling to the back; the top's ends chamfered down to the sides (CHEEK). The keys (dark brown) stand on the deck, the
function keys (SYSTEM RESET, OPTION, SELECT, START) in a column at its right, the power light under them. The lid is the
housing's front face (the ATARI 800 plate on it) and the front of its top, from the left chamfer to short of the right
end, hinged along its back edge (LID); under it the metal cartridge bay (BAY), its two slots (LEFT and RIGHT CARTRIDGE)
in its floor. The vents run over the lid's top and on behind it, over the top and its fall: fins in recesses (VENTS).
The four joystick ports are in the front of the block under the front (PORTS).

The keys are laid out in units of U from KEYS_X0, in rows from the back (ESC's) to the front (the space bar's). The deck
is a plane at SLOPE: a key stands on it in the deck's frame (x across, s up the slope from its front edge, h off it),
and deck_point() maps a point of that frame to the model's (y, z).

One texture (ATLAS square, REGIONS): `deck` (the deck from above: the keys' tops and legends, the function keys', the
power light's), `badge` (the lid's front face from in front: the ATARI 800 plate), `ports` (the block's front), `plate`
(the bay's back wall, its LEFT CARTRIDGE / RIGHT CARTRIDGE plate), `cart` (the cartridge's front, its label), and
swatches; the joystick's top drawn where atari_2600_layout.REGIONS["stick"] puts it and its red where its
SWATCHES["red"] does, as atari_2600.joystick() maps them. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024
U = 19.05

WIDTH, DEPTH, HEIGHT = 400.0, 318.0, 123.6
BASE = 10.0                      # the shell's underside off the table
FRONT = (10.0, 51.1)             # the deck's front edge (y, z)
DECK_BACK = (139.0, 78.7)        # where the deck meets the housing's front face
SLOPE = math.atan2(DECK_BACK[1] - FRONT[1], DECK_BACK[0] - FRONT[0])
TOP_FRONT = 157.0                # the housing's front face's top edge (y)
PROFILE = [                      # the side outline (y, z), round from the front's foot
    (18.0, BASE), (305.0, BASE), (313.0, 14.0), (317.0, 22.0), (318.0, 32.0), (313.5, 102.0), (310.0, 105.6),
    (264.0, HEIGHT), (TOP_FRONT, HEIGHT), DECK_BACK, FRONT, (6.4, 48.8), (3.4, 45.6), (1.2, 42.0), (0.0, 38.0),
    (0.0, 30.0), (2.6, 26.9), (4.7, 23.3), (6.9, 19.7), (9.3, 16.0), (13.0, 12.6),
]
CHEEK = dict(x=140.0, z=109.0)   # the top's chamfer: from x to the side, down to z there

KEYS_X0, ROW1 = -176.8, 118.4    # the back row's left edge, less its offset; its middle (s)
KEY = dict(height=11.0, inset=2.6)
ROWS = [
    (0.25, [("ESC", 1.0)] + [(c, 1.0) for c in "1234567890"] + [("CLEAR", 1.0), ("INSERT", 1.0), ("DELETE", 1.0),
                                                              ("BREAK", 1.0)]),
    (0.0, [("TAB", 1.5)] + [(c, 1.0) for c in "QWERTYUIOP-="] + [("RETURN", 1.5)]),
    (0.0, [("CTRL", 1.75)] + [(c, 1.0) for c in "ASDFGHJKL;+*"] + [("CAPS", 1.25)]),
    (-0.25, [("SHIFT", 2.25)] + [(c, 1.0) for c in "ZXCVBNM,./"] + [("ATARI", 1.0), ("SHIFT", 1.75)]),
    (2.0, [(" ", 9.0)]),
]
FUNCTION = dict(x=(124.0, 156.0), keys=[("SYSTEM RESET", ROW1 + 2.0, "reset"), ("OPTION", ROW1 - U + 2.0, "option"),
                                        ("SELECT", ROW1 - 2 * U + 2.0, "select"),
                                        ("START", ROW1 - 3 * U + 2.0, "start")])
LIGHT = dict(s=ROW1 - 4 * U + 4.0, half=6.0, height=6.0)     # the power light, under START

# The lid: the hole it fills (x, y; its hinge along the back); its face's and sides' thickness, its top's; the gap
# round it; how far it opens (degrees).
LID = dict(x=(-140.0, 115.0), y=(120.0, 200.0), wall=3.0, top=6.0, gap=1.0, open=-115.0)
BAY = dict(x=(-125.0, 100.0), y=(141.0, 197.0), floor=55.0)
SLOTS = dict(left=(-107.0, -30.0), right=(5.0, 82.0), y=(160.0, 180.0), floor=22.0)
# The vents: across (x); behind the lid (y) and on its top (lid); the recess's depth; the fins' count and thickness.
VENTS = dict(x=(-136.0, 111.0), y=(202.0, 306.0), lid=(161.0, 196.0), depth=5.0, count=72, fin=1.8)
BADGE = dict(fuji=(-134.0, -112.0), plate=(-109.0, -8.0), z=(92.0, 118.0))    # on the lid's face
PORTS = dict(block=(-108.0, 60.0), y=(36.0, 40.0), x=[-86.0, -53.0, 4.0, 37.0], z=5.0, size=(20.0, 6.0))
FEET = dict(x=170.0, y=(280.0, 300.0), size=24.0)

# The cartridge: w, t, h; its label, and how far below its top; how far over its seat it appears.
CART = dict(size=(70.0, 18.0, 88.0), label=(56.0, 46.0), top=6.0, above=80.0)
SEAT = ((SLOTS["left"][0] + SLOTS["left"][1]) / 2, sum(SLOTS["y"]) / 2, SLOTS["floor"] + 2.0)  # its foot's middle
JOYSTICK = dict(at=(-120.0, -112.0))     # where the CX40's middle stands

COLOURS = dict(case="#D9D0B8", key="#3E3530", print="#FFFFFF")

REGIONS = dict(deck=(0, 0, 1000, 348), badge=(0, 664, 640, 112), ports=(0, 784, 504, 30), plate=(0, 824, 563, 60),
               cart=(664, 380, 210, 264))
SWATCHES = dict(case=(912, 680), key=(944, 680), dark=(976, 680), reset=(1008, 680), option=(912, 712),
                select=(944, 712), start=(976, 712), metal=(1008, 712), cart=(912, 744), black=(944, 744),
                light=(976, 744), vent=(1008, 744))

FPS = 30
LENGTH = 240                 # 8 s


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return FRONT[0] + s * c - h * k, FRONT[1] + s * k + h * c


def face_y(z, inset=0.0):
    """Where the housing's front face is at height z (y), or the line inset into the lid from it."""
    (y0, z0), (y1, z1) = DECK_BACK, (TOP_FRONT, HEIGHT)
    length = math.hypot(y1 - y0, z1 - z0)
    ny, nz = (z1 - z0) / length, -(y1 - y0) / length       # into the lid
    y0, z0 = y0 + ny * inset, z0 + nz * inset
    return y0 + (z - z0) * (y1 - y0) / (z1 - z0)


def top_z(y):
    """The top's height at y: flat, then falling to the back."""
    (fy, fz), (by, bz) = PROFILE[7], PROFILE[6]
    return fz if y <= fy else fz - (y - fy) * (fz - bz) / (by - fy)


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
