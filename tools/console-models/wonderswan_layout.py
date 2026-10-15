"""The WonderSwans' measurements, shared by wonderswan_print.py (which draws their printing) and wonderswan.py (which
builds them). Plain Python: Blender's Python imports it too.

Two handhelds, one per system: `wonderswan` (Bandai's WonderSwan, 1999, in Skeleton Green) and `wonderswancolor` (the
WonderSwan Color, 2000, in Crystal Blue). Both are 74.3 mm high and 24.3 mm deep; the WonderSwan is 121 mm wide, the
Color 128. Millimetres, seen from the front: x from the middle (left to right), z up from the bottom; the front is at
y = -depth / 2. The rest was measured from photographs (Wikimedia Commons' WonderSwan-Black-Left, WonderSwan-Color-
Blue-Left and WonderSwan-Color-Back-wBattery, ES-DE's front views, and a cartridge in its slot), scaled by the body.

The body's outline is a rounded rectangle (corners' radii: bottom right, top right, top left, bottom left) whose bottom
right of `lift_x` is raised by `lift`: the grip at the left end hangs lower than the rest, in an S along the bottom.

The buttons are the WonderSwans' own: two diamonds of four (Y above X) at the left end, and A and B at the right, the
right and lower petals of a third diamond, so the machine can be turned on its end for games played upright. A petal
is a rounded triangle pointing at its diamond's middle, `petal` (from the middle to its own, its width, its depth) the
same on all three. SOUND and START (and the Color's POWER) are pills below the screen.

Each has one ATLAS x ATLAS print texture of named regions, each a face's planar projection: `front` (the body's front:
its colour, the screen's surround, the screen switched off, the legends, the buttons' wells and tops, the speaker),
`rear` (the back, seen from behind: the empty cartridge slot, the sticker), `cart` and `cart_rear` (the cartridge's
label side and its other side, each as seen looking at it), `screen` (the start-up screen) and `screen_v` (a game
played upright, drawn turned a quarter clockwise, so it reads upright once the console is turned on its end). The
screens are 224 x 144 pixels, the WonderSwan's own, one texel each. A region is (x, y, width, height) in pixels, and
the box of millimetres it covers, (x0, x1, z0, z1).

The cartridge goes into the back, label outwards, sliding down from the top: `x` is its middle, its top `protrudes`
above the console's top, and its contacts are the narrower `contacts` millimetres at its bottom.
"""

import math

ATLAS = 1024


def region(px, mm):
    return dict(px=px, mm=mm)


def screen_box(x, z, width, height):
    return (x - width / 2, x + width / 2, z - height / 2, z + height / 2)


MODELS = {
    "wonderswan": dict(
        name="WonderSwan",
        width=121.0, height=74.3, depth=24.3,
        corners=[14.0, 14.0, 12.0, 16.0],
        lift=2.5, lift_x=(-4.0, 16.0),
        front_round=(1.5, 1.5), back_round=(4.0, 4.0),
        colours=dict(case="#45B3A2", buttons="#E4E2DA", dark="#24282A", cart="#2C2E33"),
        bezel=dict(x=(-26.9, 39.0), top=(67.9, 64.3), bottom=7.7, tab=dict(x=(-26.9, 8.0), bottom=4.4),
                   colour="#C3C7CE"),
        glass=dict(x=(-24.0, 34.0), z=(17.7, 56.3), colour="#7F8676"),
        screen=dict(x=5.0, z=37.0, width=54.0, height=34.6, colour="#A3AA92"),
        clusters=dict(Y=(-45.0, 54.5), X=(-45.0, 15.9), AB=(45.5, 19.3)),
        petal=(6.6, 7.8, 6.4),
        pills=[("SOUND", -13.0, 7.0), ("START", -1.5, 7.0)],
        pill=(7.4, 3.2),
        speaker=(48.2, 59.4, 7.2),
        cart=dict(x=-7.0, width=55.0, height=38.0, thickness=6.0, contacts=6.0, protrudes=0.5),
        regions=dict(
            front=region((0, 0, 1024, 636), (-61.5, 61.5, -1.0, 75.3)),
            rear=region((0, 644, 480, 298), (-61.5, 61.5, -1.0, 75.3)),
            cart=region((488, 644, 290, 203), (-28.5, 28.5, -1.0, 39.0)),
            cart_rear=region((488, 855, 184, 128), (-28.5, 28.5, -1.0, 39.0)),
            screen=region((788, 648, 224, 144), screen_box(0.0, 0.0, 54.0, 34.6)),
            screen_v=region((788, 800, 224, 144), screen_box(0.0, 0.0, 54.0, 34.6)),
        ),
    ),
    "wonderswancolor": dict(
        name="WonderSwan Color",
        width=128.0, height=74.3, depth=24.3,
        corners=[14.0, 14.0, 13.0, 16.0],
        lift=3.0, lift_x=(-6.0, 18.0),
        front_round=(1.5, 1.5), back_round=(4.0, 4.0),
        colours=dict(case="#2F6FD6", buttons="#F1ECDF", power="#E8502E", dark="#1E2130", cart="#2C2E33"),
        bezel=dict(x=(-33.1, 43.3), top=(72.6, 72.6), bottom=13.8, tab=dict(x=(-33.1, 9.6), bottom=9.4),
                   colour="#EDEEF0"),
        glass=dict(x=(-27.7, 35.5), z=(21.0, 62.6), colour="#24252E"),
        screen=dict(x=3.9, z=41.8, width=60.0, height=38.5, colour="#3B3A55"),
        clusters=dict(Y=(-49.7, 59.4), X=(-49.7, 24.2), AB=(49.6, 25.6)),
        petal=(6.6, 7.6, 6.6),
        disc=10.8,
        pills=[("SOUND", -20.9, 11.2), ("START", -9.1, 11.2)],
        pill=(7.6, 3.6),
        power=(3.6, 11.0, 8.6, 4.2),
        speaker=(51.0, 60.6, 7.6),
        cart=dict(x=-7.0, width=55.0, height=38.0, thickness=6.0, contacts=6.0, protrudes=0.5),
        regions=dict(
            front=region((0, 0, 1024, 601), (-65.0, 65.0, -1.0, 75.3)),
            rear=region((0, 644, 480, 282), (-65.0, 65.0, -1.0, 75.3)),
            cart=region((488, 644, 290, 203), (-28.5, 28.5, -1.0, 39.0)),
            cart_rear=region((488, 855, 184, 128), (-28.5, 28.5, -1.0, 39.0)),
            screen=region((788, 648, 224, 144), screen_box(0.0, 0.0, 60.0, 38.5)),
            screen_v=region((788, 800, 224, 144), screen_box(0.0, 0.0, 60.0, 38.5)),
        ),
    ),
}

# Each diamond's petals: name suffix and direction (degrees anticlockwise from the right) from its middle. The A and B
# diamond has only its right (A) and lower (B) petals.
PETALS = [("1", 90.0), ("2", 0.0), ("3", 270.0), ("4", 180.0)]
AB = [("A", 0.0), ("B", 270.0)]


def petal_centres(m):
    """Every petal on the front: (label, x, z, direction in degrees)."""
    reach = m["petal"][0]
    out = []
    for cluster in ("Y", "X"):
        cx, cz = m["clusters"][cluster]
        for suffix, a in PETALS:
            out.append((cluster + suffix, cx + reach * math.cos(math.radians(a)), cz + reach * math.sin(math.radians(a)), a))
    cx, cz = m["clusters"]["AB"]
    for name, a in AB:
        out.append((name, cx + reach * math.cos(math.radians(a)), cz + reach * math.sin(math.radians(a)), a))
    return out


def petal_corners(m, x, z, degrees):
    """A petal's outline corners, anticlockwise, and their radii: its tip towards the diamond's middle, its outer edge
    bowed out."""
    _, width, depth = m["petal"]
    hw, hd = width / 2, depth / 2
    local = [(-hd, 0.0), (hd - 0.9, -hw), (hd, 0.0), (hd - 0.9, hw)]
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [(x + u * c - v * s, z + u * s + v * c) for u, v in local], [1.3, 1.6, 7.0, 1.6]


def outline_lift(m, x, z):
    """How far the body's outline at (x, z) is raised: the lift, fading in along x over lift_x and out towards the top."""
    x0, x1 = m["lift_x"]
    t = min(1.0, max(0.0, (x - x0) / (x1 - x0)))
    return m["lift"] * t * t * (3 - 2 * t) * max(0.0, 1 - z / m["height"])
