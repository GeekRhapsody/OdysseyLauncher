"""The Atari XE Game System card's measurements, shared by xegs_print.py (which draws its printing) and xegs.py (which
builds it). Plain Python: Blender's Python imports it too.

The Atari XE Game System (1987), 312 mm wide, 212 deep and 53 high (59 over its ribs), with its keyboard in front of it
(333 x 146 x 18) and the CX40 joystick it came with, in its beige, at its right (atari_2600.py's), a made-up game,
Odyssey, on the cartridge. Millimetres: x from the console's middle (left to right), y back from its front, z up from
the table. Measured from Evan-Amos's photographs on Wikimedia Commons (from above, the front, the front right, the back
straight on, the right side, with its keyboard, with its joystick) and from a museum's two, scaled by the keyboard's
19.05 mm key pitch.

The console: a base (BASE) under a shell that overhangs it all round; the shell's front is a strip (STRIP: the ATARI
logo in relief, START, SELECT, OPTION and RESET), a groove behind it. On the shell's top: the ribs (RIBS) filling the
triangle at the back left, its long side running from the back to the left side near the front; the funnel along that
side (FUNNEL), a ramp down to its floor in front, the cartridge slot (SLOT) in its floor, the cartridge standing in it
along the ribs, its label to the front right; the raised triangle the power button stands on (PLINTH, POWER), between
the ribs and the strip. The two joystick ports are in notches in the base's right side (PORTS).

The keyboard: a slab, its keys standing in a well (in rows from the back, Esc's, to the front, the space bar's, in units
of U from KEYS_X0, in its own frame: x across, v back from its front edge), the round HELP button behind them. Its cable
runs to the console's left side.

One texture (ATLAS square, REGIONS): `keys` (the keyboard from above: the keys' tops and legends), `strip` (the strip
from above: the logo, the buttons' tops and names), `cart` (the cartridge's front, its label), `power` and `help` (those
buttons' tops), and swatches; the joystick's top drawn where atari_2600_layout.REGIONS["stick"] puts it and its red
where its SWATCHES["red"] does, as atari_2600.joystick() maps them. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024
U = 19.05

WIDTH, DEPTH, HEIGHT = 312.0, 212.0, 52.6      # the shell; HEIGHT its top
BASE = dict(inset=10.0, height=26.2)           # how far in from the shell's edges; its top (the shell's underside)
STRIP = dict(y=(0.0, 50.0), groove=2.5, depth=3.0)
# The ribs: the triangle's corner at the back left, where its long side meets the back (x) and the left side (y); the
# ridges along it: their count and pitch, their foot's and top's width and their height.
RIBS = dict(back=-6.0, left=58.0, count=19, pitch=5.45, foot=4.4, top=1.4, height=6.0, rim=2.0)
PLINTH = dict(points=[(-103.0, 110.0), (-154.0, 56.0), (-54.0, 56.0)], height=2.0)
POWER = dict(at=(-105.0, 80.0), r=13.0, height=3.0, led=(5.0, -4.5))     # the LED's offset from its middle
BUTTONS = dict(x=[23.0, 57.0, 91.0, 125.0], y=25.0, r=13.5, height=3.0,
               names=["Start", "Select", "Option", "Reset"])
# The funnel and the slot lie along the ribs' long side (t along it from its end at the left side, s out from it towards
# the front right: along()): the funnel's length, how deep its floor is, the ramp from its floor up to the top in front;
# the slot in its floor, down to SLOT["floor"].
FUNNEL = dict(t=(122.0, 208.0), depth=14.0, ramp=(30.0, 62.0))
SLOT = dict(t=(130.0, 206.0), s=(6.0, 28.0), floor=6.0)
PORTS = dict(y=[115.0, 155.0], width=36.0, depth=10.0, z=(4.0, 22.0))    # notches in the base's right side

KEYBOARD = dict(size=(333.0, 146.0, 18.0), y0=-164.0)        # w, d, h; where its front edge is (y)
WELL = dict(x=(-135.0, 154.75), v=(14.0, 113.5), depth=6.0)  # the keys' well, in the keyboard's frame
HELP = dict(at=(-36.0, 128.6), r=14.0, height=4.0)
KEYS_X0, ROW1 = -133.0, 101.5    # the rows' left edge; the back row's middle (v)
KEY = dict(height=9.0, inset=2.4)                              # off the well's floor; how far in its top is
ROWS = [
    (0.0, [("Esc", 1.0)] + [(c, 1.0) for c in "1234567890"] + [("Clear", 1.0), ("Insert", 1.0), ("Delete", 1.0),
                                                             ("Break", 1.0)]),
    (0.0, [("Tab", 1.5)] + [(c, 1.0) for c in "QWERTYUIOP-="] + [("Return", 1.5)]),
    (0.0, [("Control", 1.75)] + [(c, 1.0) for c in "ASDFGHJKL;+*"] + [("Caps", 1.25)]),
    (0.0, [("Shift", 2.25)] + [(c, 1.0) for c in "ZXCVBNM,./"] + [("Shift", 1.75), ("◪", 1.0)]),
    (2.85, [(" ", 9.4)]),
]

CART = dict(size=(70.0, 18.0, 88.0), label=(56.0, 46.0), top=6.0, above=80.0)
JOYSTICK = dict(at=(232.0, 30.0))        # where the CX40's middle stands

COLOURS = dict(case="#BDBBAE", key="#E8E6DC", print="#FFFFFF")

REGIONS = dict(keys=(0, 0, 800, 352), strip=(0, 664, 780, 125), cart=(660, 360, 168, 211), power=(840, 360, 72, 72),
               help=(840, 440, 72, 72))
SWATCHES = dict(case=(912, 600), dark=(944, 600), well=(976, 600), key=(1008, 600), start=(912, 632),
                select=(944, 632), option=(976, 632), reset=(1008, 632), power=(912, 696), help=(944, 696),
                cart=(976, 696), black=(1008, 696), joy=(912, 728), led=(944, 728))

FPS = 30
LENGTH = 240                 # 8 s


_A, _B = (RIBS["back"], DEPTH), (-WIDTH / 2, RIBS["left"])        # the ribs' long side's ends
_LENGTH = math.hypot(_A[0] - _B[0], _A[1] - _B[1])
ALONG = ((_A[0] - _B[0]) / _LENGTH, (_A[1] - _B[1]) / _LENGTH)
ANGLE = math.degrees(math.atan2(ALONG[1], ALONG[0]))                # the slot's turn about the vertical


def along(t, s):
    """The point (x, y) t along the ribs' long side from its end at the left side and s out from it, towards the front
    right."""
    return _B[0] + ALONG[0] * t + ALONG[1] * s, _B[1] + ALONG[1] * t - ALONG[0] * s


def frame(x, y):
    """along()'s inverse: (t, s) of the point (x, y)."""
    dx, dy = x - _B[0], y - _B[1]
    return dx * ALONG[0] + dy * ALONG[1], dx * ALONG[1] - dy * ALONG[0]


SEAT = (*along(sum(SLOT["t"]) / 2, sum(SLOT["s"]) / 2), SLOT["floor"] + 2.0)    # the cartridge's foot's middle


def keys():
    """Every key: (legend, x0, x1, v), v its row's middle in the keyboard's frame; the rows from the back to the
    front."""
    out = []
    for r, (offset, row) in enumerate(ROWS):
        x = KEYS_X0 + offset * U
        v = ROW1 - r * U
        for legend, width in row:
            out.append((legend, x, x + width * U, v))
            x += width * U
    return out
