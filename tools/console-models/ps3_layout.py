"""The PlayStation 3 set's measurements, shared by ps3_print.py (which draws its printing) and ps3.py (which builds it).
Plain Python: Blender's Python imports it too.

The original PlayStation 3 (the CECHA01, 2006), lying flat, 325 x 274 x 98 mm (Wikipedia's figures). Millimetres: x
from its middle (left to right), y back from its front (the flap's and the lip's faces), z up from the table.

Its shape was measured from Evan-Amos's four corner photographs on Wikimedia Commons (Sony-PlayStation-3-CECHA01-
Console-FL, -FR, -BL and -BR) and the vertical one (PS3-Fat-Console-Vert): a solid built as ps3.py builds it and each
photograph's camera were fitted to the photographs' silhouettes together (each view's overlap 0.92 to 0.97), and the
side views in iFixit's teardown and hard drive guide, the left end straight on, show the profile's arc. Its top is a
hill from front to back, not an arch across: flat across its width, rising from the front edge (the chrome strip, 68
to 76 mm up) to its peak (96 mm, 132 mm back; the 98 mm is with its feet) and falling to the back edge (60 mm); its
left end flat down to the table (it stands on it upright), its right end, the vents', curving in underneath to the
base, 47 mm in. The front's features are placed from the vertical photograph, which sees the front nearly square: the
flap over its left half, the drive's chrome face over its right half with the slot and the PlayStation mark, the black
lip under the drive with the eject and power marks, the power light and SONY, the chrome strip along the top's front
edge, and the base's grille set back under them. The logo's letters were found on the top by casting their places in
both back photographs onto the fitted top (the two agree within 4 mm): PLAYSTATION 3 reads from the back to the front,
16 mm right of the middle, its letters' tops towards the right end.

One texture (ATLAS, REGIONS, SWATCHES): the console's faces and the Blu-ray's two sides. A region is (x, y, width,
height) in pixels, a swatch a block's middle.
"""

import math

# ---- The console ----------------------------------------------------------------------------------------------------

WIDTH, DEPTH = 325.0, 274.0
FACE = 6.0                    # the body's front, behind the flap and the lip, which stand out to y = 0
FRONT_Z, PEAK_Z, PEAK_Y, BACK_Z = 72.0, 96.0, 132.0, 60.0      # the top's hill
RISE, FALL = 2.6, 2.1         # its shape: z falls from the peak as these powers of the way to each edge
FRONT_ROUND, BACK_ROUND = 7.9, 4.0     # the top's front edge (the chrome strip wraps it) and back edge rounded
SHOULDER = 10.5               # the top rounding over into each end
UNDER = 29.5                  # the body's underside, over the base; the flap's and the lip's bottoms
RIGHT_TURN = dict(z=38.0, x=115.0)     # the right end curving in from z down to the base's corner at x on the table
BASE = dict(front=20.0, back=271.0, left=-WIDTH / 2)


def top_z(y):
    """The top's height y back from the front (the hill)."""
    y = min(max(y, FACE), DEPTH)
    if y <= PEAK_Y:
        return PEAK_Z - (PEAK_Z - FRONT_Z) * ((PEAK_Y - y) / (PEAK_Y - FACE)) ** RISE
    return PEAK_Z - (PEAK_Z - BACK_Z) * ((y - PEAK_Y) / (DEPTH - PEAK_Y)) ** FALL


def right_x(z):
    """The right end's x at height z: the wall down to RIGHT_TURN's z, then a quarter ellipse in to its x."""
    zt, xt = RIGHT_TURN["z"], RIGHT_TURN["x"]
    if z >= zt:
        return WIDTH / 2
    t = (zt - z) / zt
    return xt + (WIDTH / 2 - xt) * math.sqrt(max(0.0, 1 - t * t))


# The front, (x, z) on its faces. The flap stands out over the left half; its right end a wedge back to the body.
FLAP = dict(x=(-WIDTH / 2 + 0.6, -9.0), wedge=-2.0, top=59.0, dots=(-88.0, 32.5))
DRIVE = dict(x=(-2.0, 152.0), z=(46.0, 67.4))          # the chrome face, from under the chrome strip down to the lip
SLOT = dict(x=(1.8, 140.6), z=(59.5, 62.5), depth=12.0)
PS_MARK = dict(at=(72.0, 53.5), height=7.0)
LIP = dict(x=(-2.0, 160.0), top=46.0, nose=40.0)       # its top slopes from the drive down to its nose, at y = 0
EJECT = (70.0, 43.4)
POWER = (128.0, 43.4)
SONY = (149.0, 35.0)         # on the lip's face, reading along it as the logo does
LIGHT = dict(at=(121.0, 35.0), size=(3.0, 1.6))        # the power light's two bars on the lip's face
LOGO = dict(x=16.0, y=(51.0, 223.0), height=7.5)       # PLAYSTATION 3 on the top, reading from the back
FRONT_REGION = (28.0, 69.0)   # the front's printing covers this height, the front edge's curve starting above it

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2)
SEAT = (sum(SLOT["x"]) / 2, FACE + 70.0, sum(SLOT["z"]) / 2)   # the disc's middle once it's in

COLOURS = dict(gloss="#FFFFFF", matte="#FFFFFF", disc="#FFFFFF")
CASE = (16, 16, 19)           # the piano black, as printed

ATLAS = 1024
REGIONS = dict(top=(0, 0, 640, 540), front=(0, 548, 1024, 128), base=(0, 684, 1024, 86), right=(0, 778, 560, 200),
               left=(568, 778, 300, 108), back=(568, 894, 300, 72), strip=(648, 0, 376, 32),
               label=(648, 76, 230, 230), disc=(648, 312, 230, 230))
SWATCHES = dict(case=(664, 56), matte=(696, 56), under=(728, 56), chrome=(760, 56), slot=(792, 56), green=(824, 56),
                red=(856, 56), wedge=(888, 56), dim=(920, 56), silver=(952, 56))

FPS = 30
LENGTH = 150                 # 5 s
