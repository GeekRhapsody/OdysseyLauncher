"""The Commodore CDTV card's measurements, shared by cdtv_print.py (which draws its printing) and cdtv.py (which builds
it). Plain Python: Blender's Python imports it too.

The Commodore CDTV (1991), 430 mm wide, 330 deep and 95 high on its 15 mm silver feet (a 1993 review's figures), its
remote controller in front of it, a CD caddy with a made-up game, Odyssey, going into its slot. Millimetres: x from its
middle (left to right), y back from its front, z up from the table. The front's layout was measured from photographs on
Wikimedia Commons (one straight on, under a 1084 monitor; one from the front left; its controls close up; the remote),
scaled by its width; the review gives the front's order from left to right.

The case: black, a box on four silver feet (FEET), the front's foot a recessed strip (STRIP) under a ledge with the
small buttons; the top's back half a vent grille (VENTS). On the front, from the left: the power switch over the
headphone jack (POWER, JACK), the green LED, the caddy's panel (PANEL) with the slot (SLOT) and the eject button under
its right end (EJECT), the yellow LED, the infrared window (IR), the cyan display (DISPLAY: the clock, then the track
and its time), the play and stop buttons, the volume rocker, and Commodore CDTV over them. The remote (REMOTE): a long
black slab, the D-pad on its left end, A and B on its right, the keys between (KEYS).

One texture (ATLAS square, REGIONS): `front` (the front: its panels, labels and buttons' faces), `vents` (the top's
grille), `remote` (the remote from above), `caddy` (the caddy's top: the disc through its window), the display's faces
(`clock`, `time_0` to `time_3`), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 430.0, 330.0, 95.0
FEET = dict(height=15.0, r=16.0, x=180.0, y=(40.0, 290.0))
STRIP = dict(z=(FEET["height"], 27.0), depth=3.0)
VENTS = dict(y=(200.0, 310.0), x=(-180.0, 180.0))

POWER = dict(x=(-207.0, -184.0), z=(65.0, 75.0))
JACK = dict(at=(-196.0, 42.0), r=4.0)
LEDS = dict(green=(-173.0, 69.0), yellow=(-29.0, 69.0), r=1.6)
PANEL = dict(x=(-169.0, -35.0), z=(27.0, 79.0))
SLOT = dict(x=(-164.0, -36.0), z=(52.0, 62.0), depth=170.0)
EJECT = dict(x=(-58.0, -40.0), z=(39.0, 47.0), depth=2.5)
IR = dict(x=(-21.0, 8.0), z=(43.0, 57.0))
DISPLAY = dict(x=(15.0, 77.0), z=(43.0, 57.0))
PLAY = dict(x=(85.0, 119.0), z=(50.0, 61.0))
STOP = dict(x=(85.0, 119.0), z=(36.0, 47.0))
VOLUME = dict(x=(125.0, 201.0), z=(36.0, 61.0))
LOGO = dict(x=(110.0, 205.0), z=(70.0, 88.0))
SMALL = dict(x=[(85.0, 101.0), (103.0, 119.0), (140.0, 165.0), (170.0, 195.0)], z=(19.0, 24.0),
             names=["◄◄", "►►", "CD/TV", "RESET"])

# The caddy: w, length (going in), t; how far out of the slot its front end stays when it is in; how far out it waits.
CADDY = dict(size=(124.0, 155.0, 8.6), proud=2.0, out=165.0, window=(112.0, 124.0), disc=60.0)

# The remote: length, depth, height; where its middle lies (x, y) and its turn; its end sections' length; the D-pad
# (its middle along the left end, its arms' reach and width), A and B (their middles, radius), the keys (their size).
REMOTE = dict(size=(216.0, 70.0, 20.0), at=(-40.0, -62.0, -5.0), ends=36.0, pad=(-90.0, 4.0, 13.0, 8.0),
              a=(82.0, -2.0), b=(98.0, 6.0), r=6.0, key=(11.0, 6.0))
# The keys on the remote's middle (their middles, from its middle): the number pad (1 2 3 ESCAPE, 4 5 6 0, 7 8 9
# ENTER), the CD keys (GENLOCK CD/TV POWER, REW PLAY FF), STOP, and the volume pair; POWER is red.
KEYS = ([(-58.0 + 16.5 * c, 20.0 - 11.0 * r) for r in range(3) for c in range(4)]
        + [(10.0 + 15.0 * c, 20.0 - 11.0 * r) for r in range(2) for c in range(3)]
        + [(25.0, -13.0), (58.0, 9.0), (58.0, -4.0)])
KEY_NAMES = ["1", "2", "3", "ESCAPE", "4", "5", "6", "0", "7", "8", "9", "ENTER", "GENLOCK", "CD/TV", "POWER", "REW",
             "PLAY/PAUSE", "FF", "STOP", "▲", "▼"]

COLOURS = dict(case="#1C1C1E", print="#FFFFFF")

REGIONS = dict(front=(0, 0, 1024, 192), vents=(0, 200, 1024, 316), remote=(0, 524, 648, 210),
               caddy=(656, 524, 248, 310), clock=(0, 744, 248, 56), time_0=(256, 744, 248, 56),
               time_1=(0, 808, 248, 56), time_2=(256, 808, 248, 56), time_3=(0, 872, 248, 56))
SWATCHES = dict(case=(912, 880), silver=(944, 880), dark=(976, 880), key=(1008, 880), red=(912, 912),
                green=(944, 912), yellow=(976, 912), remote=(1008, 912), caddy=(912, 944), off=(944, 944))

FPS = 30
LENGTH = 240                 # 8 s
