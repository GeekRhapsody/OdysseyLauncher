"""The Neo Geo CD set's measurements, shared by neogeocd_print.py (which draws its printing) and neogeocd.py (which builds
it). Plain Python: Blender's Python imports it too.

The Neo Geo CD top-loader (1994), 285 x 285 x 95 mm (Neo Geo CD World's figures), and its controller. Millimetres: x
from its middle (left to right), y back from its front face, z up from the table. The rest was measured from
Evan-Amos's photographs on Wikimedia Commons (the console from the front left and right and from the back right, with
its controller; the controller from the front left and right), scaled by its width.

The body: its plan a rounded square, on low feet; the sides ribbed towards the back; the two controller ports in the
front. On the top: the raised deck (its front edge bowed forward), the CD lid on it (hinged at its back, SNK NEO·GEO CD
on it), the CD's well and spindle under the lid, the vent strip behind the deck, POWER at the front left, the access
light at the front right. The controller: a dog-bone pad, the short stick in its ring at its left, SELECT and START, A,
B, C and D (red, yellow, green and blue) at its right.

One texture (ATLAS square, REGIONS): `top` (the console's top from above: the deck, the lid's printing, the vent
strip, POWER's name), `front` (the front face: the ports and their numbers), `pad` (the controller's top: the ring's
arrows, SNK NEO·GEO, SELECT, START and the letters), `disc` (the CD's label: a made-up game, Odyssey), and swatches. A
region is (x, y, width, height) in pixels.
"""

WIDTH, DEPTH, HEIGHT = 285.0, 285.0, 95.0
FEET = 3.0                                        # the body stands on feet this high
BODY_TOP = 80.0                                   # the body's top, the deck and the lid standing on it
CORNER = 24.0                                     # the plan's corners

# The deck: its plan (x0, x1, y0 at its corners, y1), its front edge bowed forward by BOW at its middle; its height.
DECK = dict(x=(-112.0, 112.0), y=(46.0, 232.0), bow=24.0, corner=16.0, height=7.0)
LID = dict(x=(-86.0, 86.0), y=(58.0, 226.0), bow=20.0, corner=12.0, height=6.0)


def bowed(x0, x1, y0, y1, bow, steps=24):
    """The deck's or the lid's plan as (x, y) points, anticlockwise: its front edge bowed forward by bow."""
    points = [(x0, y1), (x0, y0)]
    for k in range(1, steps):
        x = x0 + (x1 - x0) * k / steps
        t = (2 * x - (x0 + x1)) / (x1 - x0)
        points.append((x, y0 - bow * (1 - t * t)))
    return points + [(x1, y0), (x1, y1)]


WELL = dict(at=(0.0, 148.0), r=63.0, depth=6.0, spindle=7.0)
VENT = dict(x=(-82.0, 82.0), y=(236.0, 280.0), depth=4.0, slats=5)
POWER = dict(at=(-108.0, 24.0), r=12.5, height=3.5)
LIGHT = dict(at=(46.0, 22.0), r=1.5)
PORTS = dict(x=[-64.0, 94.0], z=(18.0, 31.0), width=34.0, depth=6.0)
RIBS = dict(y=(118.0, 276.0), count=6, width=9.0, depth=3.5, z=(14.0, 74.0))

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2)

# The controller in its own plan (x across, y away from the player, its middle at the origin): its outline, its
# height; the stick's ring and the stick; SELECT and START; A, B, C and D.
PAD_OUTLINE = [(-21.0, 33.0), (-34.0, 37.4), (-48.0, 37.2), (-61.0, 32.0), (-71.0, 22.0), (-77.0, 8.0), (-77.5, -6.0),
               (-73.0, -20.0), (-64.0, -30.5), (-51.0, -36.6), (-36.0, -37.6), (-21.0, -33.0), (0.0, -27.0),
               (24.0, -31.0), (38.0, -35.4), (52.0, -35.0), (64.0, -30.0), (73.5, -20.0), (77.8, -6.0), (77.0, 8.0),
               (72.0, 21.0), (62.0, 30.5), (48.0, 35.6), (34.0, 35.6), (24.0, 31.0), (0.0, 27.0)]
PAD = dict(at=(-192.0, -62.0), turn=-14.0, height=22.0)
RING = dict(at=(-42.0, 2.0), r=(17.0, 26.0), height=1.2)
STICK = dict(r=(15.0, 11.0), height=(5.0, 15.0))         # its base and its cap: radius, top
SMALL = dict(select=(-4.0, 9.0), start=(-9.0, -11.0), size=(13.0, 6.0), turn=18.0, height=2.0)
FACE = dict(c=(13.0, 9.0), d=(36.0, 13.0), a=(15.0, -13.0), b=(38.0, -9.0), r=8.4, height=3.6)

COLOURS = dict(case="#18181A", key="#2A2A2D", print="#FFFFFF")

ATLAS = 1024
REGIONS = dict(top=(0, 0, 640, 640), front=(0, 648, 1024, 260), pad=(648, 0, 376, 184), disc=(648, 192, 256, 256))
SWATCHES = dict(grey=(920, 220), red=(952, 220), yellow=(984, 220), green=(920, 252), blue=(952, 252),
                lit=(984, 252), dark=(920, 284), silver=(952, 284))

FPS = 30
LENGTH = 240                 # 8 s
