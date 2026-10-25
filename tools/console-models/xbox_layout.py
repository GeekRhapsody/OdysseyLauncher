"""The Xbox set's measurements, shared by xbox_print.py (which draws its printing) and xbox.py (which builds it). Plain
Python: Blender's Python imports it too.

The original Xbox (2001), 324 x 265 mm (the figure an encyclopaedia entry gives, 12.8 x 10.4 inches; others give 320 x
260), about 96 mm high at its top, and its Controller S. Millimetres: x from its middle (left to right), y back from
its front face, z up from the table. The rest was measured from Evan-Amos's photographs on Wikimedia Commons (the Xbox
from the front left, the back right and with its controller; the Controller S from above), scaled by its width.

The console: a big black box, its top flat but for the two side wedges between the X's arms, ribbed fins stepping down
to its sides; the green jewel in the middle of the X (XBOX on it); the front in three sections: the left (the XBOX
plate along its top, controller ports 1 and 2), the middle (the disc tray's front, standing a little proud, and under
it the eject and power buttons), the right (ports 3 and 4, the Compact Disc and Dolby Digital marks, Microsoft). The
tray slides out of the middle section. The Controller S: its outline, the left stick high and the d-pad low at the
left, the jewel at the middle, the right stick low and the coloured A, B, X and Y high at the right, black and white
under them, BACK and START at the left edge.

One texture (ATLAS square, REGIONS): `top` (the console from above: the jewel, the X's outline), `front` (its front:
the plate, the ports and their numbers, the marks, the seams), `pad` (the Controller S from above: the jewel, the
letters, the d-pad's well), `disc` (the DVD's label: a made-up game, Odyssey), and swatches. A region is (x, y, width,
height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 324.0, 265.0, 96.0
FEET = 5.0
SIDE_TOP = 68.0                                     # the sides' top edge: the fins step down to it
WEDGE = dict(apex=56.0, base=(16.0, DEPTH - 16.0), floor=58.0, pitch=7.0, fin=3.4)   # the side wedges: the apex's
                                                    # |x|; the base's y span at the side; the floor; the fins
JEWEL = dict(at=(0.0, 138.0), r=30.0, ring=36.0, height=1.6)
SEAM = 66.0                                         # the lid's seam across the front

# The front's sections, (x, z): the middle one stands PROUD in front of the others.
MIDDLE = dict(x=(-42.0, 42.0), proud=7.0, top=74.0)
TRAY = dict(x=(-38.0, 38.0), z=(50.0, 70.0), depth=150.0, travel=118.0)   # its front on the middle section; the bay
WELL = dict(y=75.0, r=61.0, depth=1.6)              # the disc's place on the tray, back from its front
EJECT = dict(at=(0.0, 38.0), r=6.8, height=2.4)
POWER = dict(at=(0.0, 20.0), r=5.0, height=2.0, ring=6.4)
PLATE = dict(x=(-150.0, -60.0), z=(68.0, 84.0))     # the XBOX plate on the left section
PORTS = dict(x=[-122.0, -78.0, 78.0, 122.0], z=24.0, size=(26.0, 13.0), numbers=40.0)

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2)

# The Controller S, in its own plan (x across, y forward from its grips' ends, its origin there).
PAD_RIGHT = [(0.0, 34.0), (16.0, 33.0), (28.0, 27.0), (36.0, 16.0), (44.0, 4.0), (54.0, 0.0), (64.0, 1.0),
             (72.0, 8.0), (77.0, 22.0), (78.5, 44.0), (77.0, 66.0), (72.0, 84.0), (64.0, 97.0), (52.0, 106.0),
             (38.0, 110.0), (20.0, 109.0), (0.0, 104.0)]
PAD = dict(at=(-226.0, -104.0), turn=14.0, height=(26.0, 34.0))   # its grips' and its far edge's heights
LEFT_STICK = dict(at=(-44.0, 82.0), r=(14.5, 11.0), height=12.0)  # its housing's and its cap's radii
RIGHT_STICK = dict(at=(14.0, 50.0), r=(14.5, 11.0), height=12.0)
DPAD = dict(at=(-28.0, 55.0), well=14.5, size=22.0, arm=7.6, height=2.6)
CENTRE = dict(at=(0.0, 79.0), r=13.0)               # the jewel
FACE = dict(at=(43.0, 71.0), spacing=12.0, r=5.4, height=3.0)   # Y up, X left, B right, A down
BLACK_WHITE = dict(white=(40.0, 38.0), black=(54.0, 46.0), r=5.4, height=2.4)
BACK_START = dict(back=(-58.0, 68.0), start=(-53.0, 57.0), r=3.6)

COLOURS = dict(case="#16171A", key="#202124", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 512, 419), front=(520, 0, 504, 149), pad=(520, 157, 504, 355), disc=(0, 427, 256, 256))
SWATCHES = dict(green=(280, 540), green_lit=(312, 540), silver=(344, 540), dark=(376, 540), a=(408, 540),
                b=(440, 540), x=(472, 540), y=(504, 540), white=(536, 540), black=(568, 540))

FPS = 30
LENGTH = 240                 # 8 s
