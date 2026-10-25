"""The Sega Saturn card's measurements, shared by saturn_print.py (which draws its printing) and saturn.py (which builds
it). Plain Python: Blender's Python imports it too.

The Sega Saturn (1994), the black Model 1 of Europe and America, 260 mm wide, 230 deep and 70 high (dimensions.com's 260
x 230; the museums give 254 to 260 by 225 to 230), its black control pad (the Mk II, the one the Japanese Saturn came
with) in front of it at its left, a CD with a made-up game, Odyssey, going under its lid. Millimetres: x from its middle
(left to right), y back from its front, z up from the table. Measured from Evan-Amos's photographs on Wikimedia Commons
(from the front left, with each pad, from the back right) and others.

The console: its side outline (PROFILE: the lower front, the brow leaning over it, the top, the back) cut round its
plan's corners (CORNER); the ports' band recessed under the brow (BAND), the two ports in it (PORTS); the top's front
band with POWER (an oval), OPEN (a bar), the ACCESS light and RESET (round: BUTTONS); the CD lid, a dome over the CD's
well, hinged at its back (LID, WELL); the cartridge slot's flap behind it (SLOT); the vents in the right side (VENTS).
The pad: its outline (PAD: two lobes, the cable's bump at the top, the front concave), the D-pad's disc on the left, A B
C and X Y Z on the right, START in the middle, L and R on its top edge.

One texture (ATLAS square, REGIONS): `top` (the console from above: the lid's planet and SEGA SATURN, its two sweeps,
the front band's names, SEGA, CARTRIDGE INPUT), `front` (the front: the ports' band, CONTROL 1 and 2), `pad` (the pad
from above: SEGA SATURN, START, the buttons' letters), `disc` (the CD's label), and swatches. A region is (x, y, width,
height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 260.0, 230.0, 66.0
FEET = 3.0
PROFILE = [                       # the side outline (y, z), round from the front's foot
    (10.0, FEET), (DEPTH - 4.0, FEET), (DEPTH, FEET + 4.0), (DEPTH, HEIGHT - 6.0), (DEPTH - 6.0, HEIGHT),
    (14.0, HEIGHT), (4.0, HEIGHT - 6.0), (0.0, 50.0), (0.0, 34.0), (6.0, 30.0), (8.0, FEET + 2.0),
]
CORNER = 16.0                     # the plan's corners' radius
BAND = dict(x=(-62.0, 50.0), y=(-1.0, 9.0), z=(FEET + 2.0, 30.0))     # the ports' band, cut back under the brow
PORTS = dict(x=[-28.0, 17.0], z=17.0, size=(28.0, 9.0))
BUTTONS = dict(power=(-88.0, 24.0, 26.0, 10.0), open=(-6.0, 22.0, 40.0, 9.0), reset=(78.0, 20.0, 9.0),
               access=(46.0, 22.0))  # POWER, OPEN: middle (x, y), w, d; RESET: middle and radius; ACCESS: middle
# The CD lid: its front's middle and its back (y); its half widths at the front and back; its dome's height and how
# far in its top is from its foot; how far it opens (degrees).
LID = dict(front=55.0, back=206.0, x=(88.0, 72.0), height=8.0, inset=10.0, open=-72.0)
WELL = dict(at=(0.0, 132.0), r=64.0, depth=26.0)
SLOT = dict(x=(-62.0, 62.0), y=(210.0, 224.0), depth=4.0)
VENTS = dict(y=(40.0, 150.0), z=(30.0, 54.0), count=9)

DISC = dict(r=60.0, hole=7.5, thickness=1.6, above=60.0)     # the CD; how far above the well it appears

# The pad: its outline's points (x across, y away from the player) round from its top left, smoothed; its height; the
# D-pad (middle, radius); A B C and X Y Z (middles, radius); START (middle, size); where it lies (x, y) and its turn.
PAD = dict(points=[(-62.0, 33.0), (-38.0, 42.0), (-14.0, 41.0), (0.0, 46.0), (14.0, 41.0), (38.0, 42.0), (62.0, 33.0),
                   (74.0, 10.0), (71.0, -20.0), (57.0, -41.0), (38.0, -46.0), (21.0, -34.0), (0.0, -24.0),
                   (-21.0, -34.0), (-38.0, -46.0), (-57.0, -41.0), (-71.0, -20.0), (-74.0, 10.0)],
           height=24.0, dpad=((-42.0, 2.0), 17.0), abc=[(26.0, -12.0), (43.0, -7.0), (60.0, -9.0)], abc_r=7.0,
           xyz=[(22.0, 9.0), (38.0, 14.0), (54.0, 13.0)], xyz_r=5.2, start=((0.0, -9.0), (11.0, 6.0)),
           at=(-160.0, -96.0, 12.0))

COLOURS = dict(case="#18181A", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 640, 566), front=(0, 576, 640, 160), pad=(648, 0, 376, 236), disc=(648, 244, 300, 300))
SWATCHES = dict(case=(680, 600), dark=(712, 600), button=(744, 600), lit=(776, 600), off=(808, 600), disc=(840, 600),
                pad=(680, 632), cable=(712, 632))

FPS = 30
LENGTH = 240                 # 8 s


def lid_outline(segments=10):
    """The lid's plan (x, y), anticlockwise: its front an arc bulging forward, its sides narrowing to its back."""
    (fx, bx), front, back = LID["x"], LID["front"], LID["back"]
    side = front + 16.0                                  # where the front's arc meets the sides
    arc = [(-fx + 2 * fx * k / segments, side - 16.0 * math.cos(math.pi * (k / segments - 0.5)))
           for k in range(segments + 1)]
    return arc + [(bx, back), (-bx, back)]
