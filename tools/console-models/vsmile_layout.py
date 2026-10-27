"""The V.Smile card's measurements, shared by vsmile_print.py (which draws its printing) and vsmile.py (which builds it).
Plain Python: Blender's Python imports it too.

VTech's V.Smile TV Learning System (2004, the first model, 6122), orange with its periwinkle band and feet, and its
controller. No maker's figure was found; a seller's measurement gives about 203 x 190 x 89 mm, which the Smartridge
(about 74 x 87 x 12 mm, from its edge connector's pitch) and the photographs bear out. Millimetres: x from its middle
(left to right), y back from its front, z up from the table.

The console: a puffy body, its plan a squircle with lobes at its corners (outline()), its sides rounding over into its
top (PROFILE), standing on four round feet; on its top the smoked purple lid over the storage (LID), RESTART at its front
left, and the slot, a pocket cut into the top's front edge (POCKET), the Smartridge standing in it half out. The
periwinkle band round the front, its wavy upper edge, carries vtech, PLAYER 1 and 2 over the controller ports, the
V.SMILE logo and ON (a sun) over OFF (a moon) in their silver bezel.

The controller: the periwinkle pad, its four coloured buttons on its toes, the ENTER disc in its silver ring, HELP, EXIT
and ABC at its left; joined at its right to the orange joystick base, the stick's neck and its periwinkle ball.

One texture (ATLAS square, REGIONS): `top` (the console from above: the lid's ripples and logo, RESTART), `front` (the
console from the front, projected onto every face looking forwards: the band and its printing), `face` (the
Smartridge's face: a made-up game on its label), `pad` (the controller from above, in its own frame), and swatches. A
region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

A, B = 102.5, 95.0           # the squircle's half width and half depth
MIDDLE = (0.0, 96.0)         # its middle in plan
LOBES = 3.0                  # the lobes' and dips' depth


def outline(inset=0.0, n=96):
    """The body's plan, (x, y) anticlockwise from its right: a squircle, out at its corners and in at its sides' middles,
    brought in by inset towards its middle."""
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        c, s = math.cos(t), math.sin(t)
        x, y = A * math.copysign(abs(c) ** 0.5, c), B * math.copysign(abs(s) ** 0.5, s)
        r = math.hypot(x, y)
        d = -LOBES * math.cos(4 * t) - inset
        out.append((MIDDLE[0] + x * (r + d) / r, MIDDLE[1] + y * (r + d) / r))
    return out


def front_y(x):
    """The body's front at x (its full outline), y."""
    pts = [p for p in outline() if p[1] < MIDDLE[1]]
    best = min(range(len(pts) - 1), key=lambda i: abs((pts[i][0] + pts[i + 1][0]) / 2 - x))
    (x0, y0), (x1, y1) = pts[best], pts[best + 1]
    t = 0.0 if x1 == x0 else min(1.0, max(0.0, (x - x0) / (x1 - x0)))
    return y0 + (y1 - y0) * t


FOOT = dict(at=[(-70.0, 34.0), (70.0, 34.0), (-70.0, 160.0), (70.0, 160.0)], r=(18.0, 13.0), height=16.0)
PROFILE = [(14.0, 8.0), (16.0, 3.5), (19.0, 1.0), (24.0, 0.0), (66.0, 0.0), (74.0, 1.5), (79.0, 4.5), (82.0, 9.0)]
TOP = PROFILE[-1][0]
BAND_TOP = 50.0              # the band's wavy upper edge, about

POCKET = dict(x=42.0, y=(-6.0, 40.0), floor=44.0)
LID = dict(rect=(-64.0, 64.0, 74.0, 176.0), r=18.0, dome=(2.6, 3.6))
RESTART = dict(at=(-74.0, 48.0), r=9.0, height=2.6)
ON_OFF = dict(x=82.0, z=(38.0, 26.0), r=5.0, bezel=(8.0, 14.0))   # the ON and OFF buttons' heights on the band
PORTS = dict(x=(-64.0, -46.0), z=30.0, r=4.6)

# The Smartridge: width, thickness, height (its wavy top edge's crests); it stands in the pocket, its label forwards.
CART = dict(size=(74.0, 12.0, 87.0), at=(0.0, 20.0), scallop=2.6)

# The controller, in its own frame (the pad's middle at the origin, the joystick to its right, the cord from its top);
# placed at AT, turned TURN degrees.
PAD = dict(r=50.0, height=26.0, toes=[(126.0, "red"), (104.0, "yellow"), (80.0, "blue"), (58.0, "green")],
           toe_at=46.0, toe_r=12.0, button_r=8.0, enter=(26.0, 31.0), small=[(-40.0, 8.0), (-42.0, -8.0), (-36.0, -22.0)],
           stick=(88.0, 0.0, 38.0), bridge=22.0, neck=(7.0, 30.0), ball=13.0, at=(-160.0, -96.0), turn=18.0)
PAD_SPAN = (-64.0, 132.0, -64.0, 70.0)                     # the pad region's x and y

COLOURS = dict(orange="#F7931E", band="#6E74C0", lid="#5E2A55", restart="#FE6B3B", silver="#C9CBD2", blue="#3A63C8",
               red="#D8322E", yellow="#F8CF2A", green="#3BB04E", purple="#9A8FD8", dark="#20202A", cord="#9C9CD8",
               white="#FFFFFF")

REGIONS = dict(top=(0, 0, 704, 640), front=(0, 648, 704, 272), face=(712, 0, 237, 294), pad=(712, 302, 304, 208))
TOP_SPAN = (-110.0, 110.0, 0.0, 200.0)                     # the top region's x and y
FRONT_SPAN = (-110.0, 110.0, 0.0, 85.0)                    # the front region's x and z
SWATCHES = {name: (728 + 32 * (k % 9), 532 + 32 * (k // 9)) for k, name in
            enumerate(("orange", "band", "lid", "restart", "silver", "blue", "red", "yellow", "green", "purple", "dark",
                       "cord", "white"))}

FPS = 30
LENGTH = 240                 # 8 s
