"""The Watara Supervision's measurements, shared by supervision_print.py (which draws its printing and screens) and
supervision.py (which builds it). Plain Python: Blender's Python imports it too.

The Supervision (1992), the original two-piece model: its controls below, its screen unit above, joined by a bellows
neck that lets the screen tilt; standing up facing the viewer, as the handheld models do. No maker's dimensions were
found, so its size is its screen's: 61 mm square (Wikipedia's figure) gives the screen unit 114 x 94 mm, the controls
100 x 79 mm and the neck 78 mm across, measured from photographs on Wikimedia Commons (Evan-Amos's views of it tilted,
flat and bent; a view of it upright; the Tietokonemuseo's, beside the later one-piece model). Millimetres: x from its
middle (left to right), y back from its front face, z up from its foot.

The controls: a D-shaped slab (its top corners tight, its bottom corners round), the black diamond D-pad at the left,
SELECT and START over the turquoise A and B at the right, SUPERVISION and its triangle, the speaker's slots, the raised
rim's line. The neck: black bellows, its ribs across it. The screen unit: a rounded box, its black bezel (HIGH QUALITY
STEREO SOUND between two turquoise lines along its top, WATARA at its bottom left), the yellow-green LCD in it; the
cartridge slides down into the slot at the top of its back.

One texture (ATLAS square, REGIONS): `screen_front` and `controls_front` (the two parts' fronts: the bezel, the
switched-off LCD, the names, the D-pad's cross, the rim and the speaker), the screens (`boot`, the start-up logo;
`title`, a made-up game, Odyssey; `game`, a moment of its play; all in the LCD's four greens), `label` (the cartridge's),
and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

CONTROLS = dict(size=(100.0, 79.0, 24.0), corners=(6.0, 36.0))   # w x h x depth; its top and bottom corners' radii
NECK = dict(z=(79.0, 94.0), width=78.0, depth=18.0, ribs=5)
UNIT = dict(size=(114.0, 94.0, 26.0), corner=10.0)                # the screen unit, its foot on the neck's top
UNIT_Z = NECK["z"][1]


def controls_outline():
    """The controls' front outline, anticlockwise (x, z): its top corners tight, its bottom corners round."""
    (w, h, _), (rt, rb) = CONTROLS["size"], CONTROLS["corners"]
    points = []
    for cx, cz, r, a0 in ((w / 2 - rt, h - rt, rt, 0), (-w / 2 + rt, h - rt, rt, 90), (-w / 2 + rb, rb, rb, 180),
                          (w / 2 - rb, rb, rb, 270)):
        for k in range(9):
            a = math.radians(a0 + 90 * k / 8)
            points.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return points


# The screen unit's front, (x, z) up from the unit's foot.
BEZEL = dict(x=(-48.4, 49.4), z=(13.1, 88.4), r=4.0)
LCD = dict(at=(1.4, 49.8), size=(60.8, 61.0))
LIGHT = dict(at=(38.5, 36.0), r=1.0)

# The controls' front, (x, z) up from the controls' foot.
DPAD = dict(at=(-21.5, 56.0), size=27.0, height=3.4)               # the diamond: its middle, corner to corner
AB = dict(b=(10.5, 48.4), a=(30.2, 56.7), r=6.6, height=3.2)
SMALL = dict(select=(3.3, 70.8), start=(21.9, 70.8), size=(12.0, 4.2), height=1.4)
LOGO = dict(at=(-13.2, 33.6), height=5.3)
SPEAKER = dict(at=(26.0, 30.0))

# The cartridge: w x h x thickness, its label on its back face; the slot in the unit's top at the back.
CART = dict(size=(55.0, 56.0, 8.0), label=(46.0, 32.0), protrudes=12.0)
SLOT = dict(y=(15.0, 24.0), x=(-28.5, 28.5))

COLOURS = dict(case="#8E8E91", key="#151517", turquoise="#58CDB8", glass="#FFFFFF", print="#FFFFFF")

SCREEN_PX = (256, 256)                               # 160 x 160, at 1.6
REGIONS = dict(screen_front=(0, 0, 560, 462), controls_front=(568, 0, 456, 360), boot=(0, 470) + SCREEN_PX,
               title=(264, 470) + SCREEN_PX, game=(528, 470) + SCREEN_PX, label=(792, 470, 224, 156))
SWATCHES = dict(dark=(808, 650), turquoise=(840, 650), lcd=(872, 650), cart=(904, 650), black=(936, 650))
GREENS = [(46, 56, 22), (92, 106, 42), (146, 160, 66), (190, 202, 104)]   # the LCD's four, darkest first

FPS = 30
LENGTH = 240                 # 8 s
