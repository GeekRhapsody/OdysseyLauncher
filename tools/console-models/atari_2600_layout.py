"""The Atari 2600's measurements, shared by atari_2600_print.py (which draws its printing) and atari_2600.py (which builds
it). Plain Python: Blender's Python imports it too.

The four-switch "woody" (1980), 343 x 229 x 89 mm, with its CX40 joystick. Millimetres: x from the console's middle
(left to right), y back from its front edge, z up from the table. The rest was measured from photographs on Wikimedia
Commons (Evan-Amos's view of the console with its joystick), scaled by its width.

Its side outline: the wood-grain strip across its front, the ribbed slope rising behind it to the raised control panel,
whose face slopes up to the flat top along the back. On the panel, in an orange outline: POWER and TV TYPE on the left,
the cartridge slot in the middle under VIDEO COMPUTER SYSTEM, GAME SELECT and GAME RESET on the right, each switch a
chrome lever in a slot. The joystick stands in front of the console's left end.

One texture (ATLAS square, REGIONS): `panel` (the control panel's face, seen square on: its outline, legends and the
switches' slots), `wood` (the front strip: the grain, ATARI), `label` (the cartridge's label: a made-up game, Odyssey)
and `stick` (the joystick's top: the orange ring, TOP), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 343.0, 229.0, 89.0
WOOD = dict(bottom=(2.0, 8.0), top=(13.0, 40.0))            # the strip's face: its bottom and top edges, (y, z)
SLOPE = ((16.0, 42.0), (118.0, 57.0))                       # the ribbed slope: from (y, z) to (y, z)
PANEL = ((124.0, 63.0), (196.0, 86.0))                      # the panel's face: its front and back edges, (y, z)
TOP = (222.0, HEIGHT)                                       # the flat top ends here, then the back rounds down
GROOVES = dict(count=17, width=2.4, depth=2.4)              # across the ribbed slope


def profile():
    """The side outline, (y, z), anticlockwise seen from the right end."""
    (ws, wz), (wt, wtz) = WOOD["bottom"], WOOD["top"]
    (s0, z0), (s1, z1) = SLOPE
    (p0, q0), (p1, q1) = PANEL
    return [(2.0, 0.0), (DEPTH - 2.0, 0.0), (DEPTH, 2.0), (DEPTH, HEIGHT - 6.0), (TOP[0], HEIGHT), (p1 + 3.0, HEIGHT),
            (p1, q1), (p0, q0), (p0 - 4.0, z1 + 2.0), (s1, z1), (s0, z0), (wt, wtz), (ws, wz), (0.0, 6.0), (0.0, 2.0)]


def frame(a, b):
    """The frame of a sloping face from (y, z) a to (y, z) b: its origin at a, its s axis up the slope, its normal."""
    (y0, z0), (y1, z1) = a, b
    length = math.hypot(y1 - y0, z1 - z0)
    angle = math.atan2(z1 - z0, y1 - y0)
    return (y0, z0), angle, length


PANEL_W = 312.0                                             # the panel's outlined area across, centred
SWITCHES = [("power", -128.0), ("tv_type", -96.0), ("game_select", 96.0), ("game_reset", 128.0)]
SWITCH = dict(s=36.0, slot=(6.0, 18.0), lever=(3.0, 13.0))  # their middle up the panel's face; the slot; the lever
CART_SLOT = dict(x=(-44.0, 44.0), s=(18.0, 42.0), depth=46.0)

CART = dict(width=80.0, height=105.0, thickness=21.0, label=(66.0, 72.0, 6.0))  # its label: w, h, from its top

STICK = dict(at=(-196.0, -38.0), base=(80.0, 80.0, 34.0), shaft=(8.0, 66.0), button=(118.0, 10.0))
# the joystick: its middle; its base w, d, h; the shaft's radius and height; the button's angle (degrees from +x
# round its top) and radius.

COLOURS = dict(case="#1E1E21", dark="#0C0C0E", chrome="#C9CCD1", orange="#E5762A")

REGIONS = dict(panel=(0, 0, 1024, 240), wood=(0, 248, 1024, 100), label=(0, 356, 300, 330), stick=(312, 356, 300, 300))
SWATCHES = dict(red=(640, 372), dark=(672, 372), wood=(704, 372))

FPS = 30
LENGTH = 240                 # 8 s
