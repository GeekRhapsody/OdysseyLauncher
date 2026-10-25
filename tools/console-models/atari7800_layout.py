"""The Atari 7800 set's measurements, shared by atari7800_print.py (which draws its printing) and atari7800.py (which
builds it). Plain Python: Blender's Python imports it too.

The Atari 7800 ProSystem (1986), the US model, 279 x 216 mm (the Computer History Museum's 11 x 8 1/2 inches), and its
ProLine joystick. Millimetres: x from its middle (left to right), y back from its front face, z up from the table. The
rest was measured from photographs on Wikimedia Commons (Evan-Amos's views of the console from the front left and right
and with its joystick, the joystick from the front left; a 7800 with a cartridge in it), scaled by its width.

The console: its side outline (PROFILE) extruded across its width, its edges rounded: the rounded front bumper, the
black strip of switches sloping down along the top's front edge (POWER and its light, PAUSE, SELECT and RESET, each a
key on the strip), the flat top; the brushed silver band across the top with ATARI 7800 PROSYSTEM and the rainbow line
crossing it, the cartridge slot behind the band, the vents along the back. The joystick: a long narrow base, its top
rising to the back, the silver plate on its front with ATARI and the rainbow, the stick on a black boot at its back,
the orange fire buttons on both sides.

One texture (ATLAS square, REGIONS): `top` (the console from above: the band, its logo and line, the strip and its
names, the vents' slots), `stick` (the joystick's plate: ATARI and its rainbow), `label` (the cartridge's: a made-up
game, Odyssey), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH = 279.0, 216.0
FEET = 4.0
TOP_Z = 64.0                                       # the flat top
# The side outline, (y, z), anticlockwise seen from the right: the bottom on its feet, the back, the flat top, the
# strip sloping down to the bumper, the bumper rounding to the bottom.
STRIP = ((14.0, 59.0), (36.0, TOP_Z))              # the strip's front and back edges, (y, z)
PROFILE = [(8.0, FEET), (DEPTH - 6.0, FEET), (DEPTH, 10.0), (DEPTH, 60.0), (DEPTH - 4.0, TOP_Z), STRIP[1], STRIP[0],
           (6.0, 55.5), (1.5, 47.0), (0.0, 35.0), (1.5, 22.0), (5.0, 12.0)]
STRIP_SLOPE = math.atan2(STRIP[1][1] - STRIP[0][1], STRIP[1][0] - STRIP[0][0])
STRIP_LENGTH = math.hypot(STRIP[1][1] - STRIP[0][1], STRIP[1][0] - STRIP[0][0])

KEYS = dict(power=-74.0, pause=-38.0, select=50.0, reset=88.0, s=11.3, size=(24.0, 8.0), height=1.2)   # middles' x
LIGHT = dict(x=-56.0, r=1.4)
BAND = dict(y=(96.0, 144.0))                       # the silver band across the top, back from the front face
LOGO = dict(x=-112.0, y=(106.0, 116.0))            # ATARI over 7800 PROSYSTEM: its left edge, their middles' y
RAINBOW = dict(y=(101.0, 138.0), width=0.9)        # the line across the band, from its left end to its right
SLOT = dict(x=(-44.0, 44.0), y=(150.0, 176.0), depth=50.0)
VENTS = dict(x=(-128.0, 128.0), y=(190.0, 206.0), pitch=7.0, width=3.0, depth=3.0)

# The cartridge: w x thickness x h, standing in the slot (its bottom seat_depth below the top), its label on its front.
CART = dict(size=(80.0, 22.0, 104.0), label=(66.0, 22.0), seat_depth=44.0)

# The joystick, in its own plan (x across, y back from its front end, its middle at the origin): its base, the plate,
# the stick's boot and shaft and knob, the fire buttons.
PAD = dict(at=(-196.0, -30.0), turn=22.0, size=(50.0, 156.0), height=(16.0, 30.0))
PLATE = dict(y=(-74.0, 12.0), inset=5.0)
STICK = dict(y=48.0, boot=(14.0, 8.0), shaft=(3.6, 52.0), knob=(10.5, 16.0))
FIRE = dict(y=(30.0, 56.0), z=(8.0, 22.0), out=4.0)

COLOURS = dict(case="#2A2B2E", key="#121214", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 1024, 793), stick=(0, 801, 520, 167), label=(528, 801, 300, 100))   # the stick's drawn
SWATCHES = dict(red=(856, 820), red_lit=(888, 820), dark=(920, 820), silver=(952, 820), orange=(984, 820),   # sideways
                knob=(856, 852))

FPS = 30
LENGTH = 240                 # 8 s
