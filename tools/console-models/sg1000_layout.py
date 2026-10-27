"""The SG-1000 card's measurements, shared by sg1000_print.py (which draws its printing) and sg1000.py (which builds
it). Plain Python: Blender's Python imports it too.

Sega's SG-1000 (1983) and its hard-wired SJ-200 joystick. No published size was found; the console is about 195 x 120 x
45 mm, scaled from a cartridge's 44-pin edge (22 pads a side at 2.54 mm: the shell 67 mm wide), which its slot fits
with room to spare; the rest was measured from photographs (Evan-Amos's of the console from each corner and with its
joystick on Wikimedia Commons, one from above and in front, one of the joystick from above, one with a cartridge in).
Millimetres: x from the console's middle (left to right), y back from its front edge, z up from the table.

The console: a low white wedge on its grey base, its top one plane rising from the rounded front edge to the back, its
front corners cut off in plan and the top's ends chamfered down to the sides; at the top's back the grey cartridge well,
the slot across its middle, between two grilles; across the slope the label, its ends angled (SEGA on brushed silver,
the red stripe, the blue band with SG-1000 and Computer Video Game, power on), the power light under it and HOLD (the
pause button, red) at the front right; the second player's port in the right side. The joystick lies in front of the
console's left end, its cable from its top end to the console's left side: a long grey box, a red fire button on each
side near its top end, the black stick standing in its round gate in its lower half, the black band with SEGA and the
white one with SJ-200 at its top end.

One texture (ATLAS square, REGIONS): `top` (the top's slope in its own frame: x across, s up the slope from its front
edge; the label, the grilles' shading, power on and hold), `label` (the cartridge's: a made-up game), `stick` (the
joystick's top), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH = 195.0, 120.0
FRONT = (3.0, 16.0)            # the top's front edge (y, z), above the front's rounded lip
BACK = (DEPTH - 4.0, 41.0)     # its back edge
SLOPE = math.atan2(BACK[1] - FRONT[1], BACK[0] - FRONT[0])
TOP_LENGTH = math.hypot(BACK[0] - FRONT[0], BACK[1] - FRONT[1])
PROFILE = [(2.0, 0.0), (DEPTH - 2.0, 0.0), (DEPTH, 2.0), (DEPTH, BACK[1] - 3.0), BACK, FRONT, (0.0, FRONT[1] - 4.0),
           (0.0, 2.0)]
CORNER = 16.0                  # the front corners cut off in plan
ENDS = dict(width=13.0, drop=8.0)    # the top's ends chamfered: how far in it starts, how far it falls at the side

WELL = dict(x=(-42.5, 42.5), s=(60.0, 110.0), height=3.0)          # the cartridge well's grey frame, on the slope
SLOT = dict(x=(-34.5, 34.5), s=(75.5, 95.0), depth=30.0)           # the slot inside it
GRILLES = dict(x=(50.0, 86.0), s=(66.0, 108.0), slats=5)           # each side's, its slats across
LABEL = dict(x=(86.0, 80.0), s=(25.0, 57.0))                        # the label: half its width at its front and back
HOLD = dict(x=(42.0, 60.0), s=(5.0, 14.0), height=1.8)             # HOLD, the pause button
LIGHT = dict(x=0.0, s=19.0, size=(3.2, 1.2))                       # the power light, under power on
PORT = dict(y=(88.0, 104.0), z=(12.0, 20.0))                        # the second player's port in the right side

# The cartridge: width, thickness, height; its label (width, height, from its top); how deep it goes in (about two
# thirds of it stands out).
CART = dict(size=(67.0, 17.0, 90.0), label=(58.0, 54.0, 5.0), inserted=26.0)

# The SJ-200: its top end's middle, its turn (degrees, its top end pointing back), its size (width, length, the lower
# and upper parts' heights); from its top end: the stick's gate and the stick, the fire buttons, the two bands.
STICK = dict(at=(-112.0, -16.0), turn=55.0, size=(43.0, 85.0, 14.0, 11.0),
             recess=dict(v=56.0, r=12.0, ring=15.5), shaft=(3.4, 24.0), knob=5.6,
             fire=dict(v=(10.0, 27.0), z=(4.0, 17.0), out=2.5), strip=(2.0, 13.0), band=(13.0, 18.0))

COLOURS = dict(case="#EBEAE8", base="#A6A8A9", grey="#91908B", dark="#4A4B4D", black="#141416", red="#E6340F",
               blue="#1046A8", stick_top="#6C6B67", stick_base="#5E5D59")

# The top's region has room under it: its front edge, seen at a slant, is drawn from small mipmaps, which would take in
# the colours of a region next to it.
REGIONS = dict(top=(0, 0, 1024, 608), label=(0, 660, 300, 280), stick=(320, 660, 200, 352))
SWATCHES = {name: (620 + 32 * (k % 12), 800 + 32 * (k // 12)) for k, name in enumerate(
    ("case", "base", "grey", "dark", "black", "red", "lit", "stick_top", "stick_base", "cart"))}

FPS = 30
LENGTH = 240                 # 8 s


def top_z(y):
    """The top's height at y."""
    return FRONT[1] + (y - FRONT[0]) * math.tan(SLOPE)


def slope_point(s, h=0.0):
    """The model's (y, z) of the point s up the top from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return FRONT[0] + s * c - h * k, FRONT[1] + s * k + h * c
