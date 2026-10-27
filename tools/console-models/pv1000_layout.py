"""The Casio PV-1000 card's measurements, shared by pv1000_print.py (which draws its printing) and pv1000.py (which builds
it). Plain Python: Blender's Python imports it too.

Casio's PV-1000 (1983) and its TJ-1 joystick, all navy blue. No maker's figure was found. The game pack is 106.1 x 68.2 x
16.2 mm (measured on 600 dpi scans); the slot that takes it lies across the raised deck, whose top is 0.39 of the
console's width in a photograph of its front square on, so the console is about 290 x 178 x 50 mm, its depth and
heights from that photograph's and one of its right side's proportions. Millimetres: x from its middle (left to right),
y back from its front edge, z up from the table.

The console: a thin slab (SLAB high, its front corners rounded in plan); on it the raised deck (DECK), a half ellipse whose
straight edge is the back block's front, its wall falling straight and then into a concave fillet; the back block across
the back (BACK), as high as the deck in its middle, its ends sweeping down in concave coves to the slab's top, the whole
back strip corrugated by grooves across it (RIBS), down the coves and the ends. The slot (SLOT) in a recess across the
deck's back, a light lip along its back edge; the controller sockets in a recessed strip in the front face; the power
switch, a rocker, in an oval recess in the right end; the power light and POWER on the slab's top in front of the right
shoulder; PV-1000 and CASIO at the front right.

The TJ-1 (JOY): a base, its plan a half disc at the stick's end and a rounded rectangle at the other, its sides ribbed;
the tall ribbed stick on a domed collar, the red button on its top; START and SELECT and a label plate at the flat end,
the cord out of it to the left socket.

One texture (ATLAS square, REGIONS): `top` (the console's top seen from above, planar-mapped onto every face facing up),
`cart_front` and `cart_top` (the game pack's label and its end label: a made-up game), `joy_top` (the joystick's top in
its own frame, the stick's end at the origin), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH = 290.0, 178.0
HALF = WIDTH / 2
SLAB = 34.0                  # the slab's top
TOP = 50.0                   # the deck's and the back block's top
CORNER = 8.0                 # the front corners' radius in plan

# The deck: a half ellipse, its straight edge at y = back; its wall's profile (d out from the top's edge, z), from the
# top's rounded edge down the wall and round the fillet to the slab.
DECK = dict(a=57.0, b=60.0, back=130.0)
DECK_PROFILE = [(-1.0, TOP), (0.0, TOP - 1.0), (0.0, 44.0), (0.34, 41.4), (1.34, 39.0), (2.93, 36.9), (5.0, 35.3),
                (7.4, 34.3), (10.0, SLAB), (10.0, SLAB - 1.0)]

# The back block: from y0 to the back; its top's half width, and where its coves meet the slab.
BACK = dict(y0=130.0, top=57.0, foot=125.0, power=2.2)
RIBS = dict(y0=136.0, pitch=5.0, count=8, groove=2.0, depth=1.2)


def cove_z(x):
    """The back block's height at x: its top, then the cove falling to the slab (concave, its foot level)."""
    t = min(1.0, max(0.0, (abs(x) - BACK["top"]) / (BACK["foot"] - BACK["top"])))
    return SLAB + (TOP - SLAB) * (1 - t) ** BACK["power"]


def back_outline(inset=0.0):
    """The back strip's section (x, z), from its bottom left: the ends, the slab's top at the ends, the coves and the
    top; inset (a groove's depth) brings the ends in and the top down, the bottom kept."""
    ts = (1.0, 0.8, 0.62, 0.46, 0.32, 0.2, 0.1, 0.03, 0.0)
    right = [(BACK["top"] + t * (BACK["foot"] - BACK["top"]), 0.0) for t in ts]
    right = [(x, cove_z(x) - inset) for x, _ in right]
    left = [(-x, z) for x, z in reversed(right)]
    h = HALF - inset
    return ([(-h, 0.0), (h, 0.0), (h, SLAB - inset)] + right + left + [(-h, SLAB - inset)])


def deck_ring(d, n=24):
    """The deck's outline d out from its top's edge, (x, y) from its right end round the front to its left end."""
    a, b, y0 = DECK["a"], DECK["b"], DECK["back"]
    out = []
    for k in range(n + 1):
        t = math.pi * k / n
        x, y = a * math.cos(t), y0 - b * math.sin(t)
        nx, ny = math.cos(t) / a, -math.sin(t) / b
        length = math.hypot(nx, ny)
        out.append((x + d * nx / length, y + d * ny / length))
    return out


# The slot: its recess across the deck's back, and the opening in it; the lip along the recess's back edge.
SLOT = dict(x=56.5, y=(101.0, 129.2), depth=3.0, opening=(54.4, 109.5, 126.5))
# The front face: the sockets' recessed strip and the two sockets; the right end: the switch's oval recess, the rocker.
STRIP = dict(x=27.0, z=(6.0, 21.0), depth=2.5)
SOCKETS = dict(x=(-15.5, 15.5), z=13.0, r=4.8)
SWITCH = dict(y=(86.0, 124.0), z=(6.0, 24.0), depth=1.5, rocker=(14.0, 12.0, 3.0), turn=12.0)
LIGHT = dict(x=112.0, y=124.0, r=1.4)

# The game pack: width, height, thickness; it stands in the slot, its label to the front, OUT above the deck.
CART = dict(size=(106.1, 68.2, 16.2), out=22.0)

# The TJ-1: its frame's origin at the stick's end's middle, the flat end towards +y, placed at AT turned TURN degrees.
JOY = dict(r=32.5, length=100.0, corner=10.0, height=28.0, chamfer=3.0, ribs=0.9, at=(-104.0, -92.0), turn=-24.0)
STICK = dict(collar=((24.0, 26.0), (22.0, 31.0), (17.0, 35.0), (15.0, 37.0)), r=14.0, rib=1.0, pitch=3.2,
             z=(36.0, 112.0), button=(7.5, 4.5))
BUTTONS = dict(start=(9.0, 47.0), select=(-9.0, 47.0), r=5.0, height=2.5)
PLATE = dict(x=17.0, y=(53.0, 63.0))

COLOURS = dict(case="#3E5277", joy="#25324F", black="#141416", cable="#1A1A1C", aqua="#69C0B7", red="#BE303E",
               plate="#D3D3CF", lip="#9AA4B0", cart="#0E2556", blue="#2E64DA", button="#4D5E7E")

REGIONS = dict(top=(0, 0, 1024, 628), cart_front=(0, 636, 424, 273), cart_top=(0, 917, 424, 65),
               joy_top=(432, 636, 196, 302))
SWATCHES = dict(case=(660, 652), joy=(692, 652), red=(724, 652), lit=(756, 652), plate=(788, 652), lip=(820, 652),
                cart=(852, 652), button=(884, 652), metal=(916, 652))

FPS = 30
LENGTH = 240                 # 8 s
