"""The PlayStation Portable's measurements, shared by psp_print.py (which draws its printing) and psp.py (which builds
it). Plain Python: Blender's Python imports it too.

The PSP-1000 (2004) in piano black: 170 mm wide, 74 mm high and 23 mm deep. Millimetres, seen from the front: x from
the middle (left to right), z up from the bottom; the front is at y = FRONT, the back at y = BACK, and the UMD door
stands DOOR["out"] proud of the back. The rest was measured from photographs (Wikimedia Commons' Psp-front and Psp-top,
a white PSP-1000 straight on, at 7.13 px a millimetre; Evan-Amos's three-quarter view; a back view; a UMD's two
sides), scaled by the body.

The body's outline: each end is one arc of radius END_RADIUS about END_CENTRE (mirrored for the left), tangent to the
straight top and meeting the straight bottom in a small fillet. A silver band runs round the middle of its depth
between the black front and back shells, the shoulder buttons taking its place at the top corners.

Two textures. `print` (ATLAS x ATLAS, PRINT_REGIONS): `front` (the face: the speaker's dots, the switched-off screen,
the logos and legends, the buttons' tops and wells, the analogue nub) and `rear` (the back seen from behind: the empty
UMD bay under the door, the seams, the sticker), and a row of swatches for small parts. `media` (MEDIA_REGIONS):
`screen` (the XMB, the menu, with the UMD's game on it) and `screen_game` (the game's title screen), each the PSP's 480
x 272 pixels, a texel each; `umd` and `umd_rear` (the disc's label side and its other side, each as seen looking at
it); and `door` (the UMD door's outside, seen from behind). A region is (x, y, width, height) in pixels, and the box
of millimetres it covers, (x0, x1, z0, z1).
"""

import math

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 170.0, 74.0, 23.0
FRONT, BACK = -11.5, 10.5
END_RADIUS, END_CENTRE = 42.0, (43.0, 32.0)  # tangent to the top: END_CENTRE[1] + END_RADIUS == HEIGHT
FILLET = 4.0                                 # where an end meets the bottom

FRONT_ROUND = (1.6, 1.6)   # (inset, depth) of the rounding over the front's edge
BACK_ROUND = (5.0, 5.0)
BAND = (-3.8, 5.0)         # the silver band's depth, front to back
SHOULDER = dict(x=52.0, z=44.0)  # the band is a shoulder button where |x| and z are both beyond these

COLOURS = dict(case="#1C1C21", buttons="#202025", silver="#BFC3CA", shoulder="#D6DADF", umd="#ECEDEF")

SCREEN = dict(x=0.0, z=40.85, width=95.04, height=53.86)   # the LCD's lit area: 4.3 inches, 16:9
GLASS = dict(x=(-50.9, 50.9), z=(13.3, 68.4))               # the black glass over it
DPAD = dict(x=-68.0, z=42.5, well=13.6)
FACE = dict(x=68.0, z=43.0, reach=9.5, radius=4.6, well=15.6)
NUB = dict(x=-69.4, z=19.1, radius=6.0)
ROW_Z = 6.7  # the buttons along the bottom: (name, x, shape) with shape "shield" (11.5 x 4.4) or "oval" (5.8 x 4.8)
ROW = [("HOME", -51.0, "shield"), ("VOL-", -38.6, "oval"), ("VOL+", -27.0, "oval"),
       ("DISPLAY", 18.3, "oval"), ("SOUND", 26.7, "oval"), ("SELECT", 38.0, "shield"), ("START", 50.0, "shield")]
SPEAKERS = [(-60.2, 12.0), (60.2, 12.0)]  # the two slits by the screen's lower corners

DOOR = dict(x=(-36.5, 36.5), z=(7.5, 72.0), inner=-2.0, out=1.0, ring=(41.0, 27.4, 21.8))  # ring: z, outer, inner
UMD = dict(width=65.0, bottom=-32.0, radius=32.5, corner=5.0, thickness=4.2, disc=30.0)  # its middle the disc's

FACE_BUTTONS = [("triangle", 90.0), ("circle", 0.0), ("cross", 270.0), ("square", 180.0)]
DPAD_BUTTONS = [("up", 90.0), ("right", 0.0), ("down", 270.0), ("left", 180.0)]


def region(px, mm):
    return dict(px=px, mm=mm)


PRINT_REGIONS = dict(
    front=region((0, 0, 1024, 452), (-86.0, 86.0, -1.0, 75.0)),
    rear=region((0, 460, 1024, 452), (-86.0, 86.0, -1.0, 75.0)),
)
SWATCHES = dict(yellow=(16, 936), dark=(48, 936), metal=(80, 936))  # each a 24 x 24 block's middle, in pixels


def screen_box(width, height):
    return (-width / 2, width / 2, -height / 2, height / 2)


MEDIA_REGIONS = dict(
    screen=region((16, 16, 480, 272), screen_box(SCREEN["width"], SCREEN["height"])),
    screen_game=region((528, 16, 480, 272), screen_box(SCREEN["width"], SCREEN["height"])),
    umd=region((16, 304, 402, 396), (-33.5, 33.5, -33.0, 33.5)),
    door=region((434, 304, 450, 400), (-37.5, 37.5, 6.5, 73.0)),
    umd_rear=region((16, 716, 300, 296), (-33.5, 33.5, -33.0, 33.5)),
)


def arc(cx, cz, r, a0, a1, steps):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / steps), cz + r * math.sin(a0 + (a1 - a0) * k / steps))
            for k in range(steps + 1)]


def line(a, b, steps):
    """a to b, without b."""
    return [(a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps) for k in range(steps)]


def body_outline(inset=0.0, arc_steps=28, fillet_steps=6):
    """The body's outline moved in by inset (out, if negative), anticlockwise from the front: the same number of points
    at every inset, so outlines can be joined into rings."""
    r = END_RADIUS - inset
    cx, cz = END_CENTRE
    f = max(FILLET - inset, 0.4)
    bottom = inset
    fx = cx + math.sqrt((r - f) ** 2 - (bottom + f - cz) ** 2)  # the fillet's middle, on its circle and over the bottom
    meet = math.atan2(bottom + f - cz, fx - cx)                  # where the fillet meets the end's arc
    right = arc(fx, bottom + f, f, -math.pi / 2, meet, fillet_steps)[:-1] + arc(cx, cz, r, meet, math.pi / 2, arc_steps)
    left = [(-x, z) for x, z in reversed(right)]
    top_z = cz + r
    return (line((-fx, bottom), (fx, bottom), 30) + right[:-1] + line((cx, top_z), (-cx, top_z), 18) + left[:-1]
            + [left[-1]])


def umd_outline(inset=0.0, corner_steps=6, top_steps=36):
    """The UMD's outline about its disc's middle, anticlockwise from its label side: a flat bottom with rounded corners,
    straight sides, and a half circle over the top."""
    hw, r = UMD["width"] / 2 - inset, UMD["radius"] - inset
    c = max(UMD["corner"] - inset, 0.3)
    z0 = UMD["bottom"] + inset
    points = line((-hw + c, z0), (hw - c, z0), 10)
    points += arc(hw - c, z0 + c, c, -math.pi / 2, 0.0, corner_steps)[:-1]
    points += line((hw, z0 + c), (hw, 0.0), 6)
    points += arc(0.0, 0.0, r, 0.0, math.pi, top_steps)[:-1]
    points += line((-hw, 0.0), (-hw, z0 + c), 6)
    points += arc(-hw + c, z0 + c, c, math.pi, 3 * math.pi / 2, corner_steps)[:-1]
    return points


def pentagon(x, z, degrees, inset=0.0):
    """A D-pad button: a home plate pointing at the pad's middle, (x, z), from direction degrees. Corners
    anticlockwise, and their radii."""
    local = [(3.7, 0.0), (6.3, -4.3), (12.2, -4.3), (12.2, 4.3), (6.3, 4.3)]
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [(x + u * c - v * s, z + u * s + v * c) for u, v in local], [1.0, 1.3, 1.8, 1.8, 1.3]


def shield(x, z):
    """HOME, SELECT and START: a flat top, its bottom bowed. Corners anticlockwise, and their radii."""
    return [(x, z - 2.6), (x + 5.75, z - 0.9), (x + 5.75, z + 1.8), (x - 5.75, z + 1.8), (x - 5.75, z - 0.9)], \
        [7.0, 1.4, 1.1, 1.1, 1.4]


def face_centres():
    """Each face button: (name, x, z)."""
    return [(n, FACE["x"] + FACE["reach"] * math.cos(math.radians(a)), FACE["z"] + FACE["reach"] * math.sin(math.radians(a)))
            for n, a in FACE_BUTTONS]
