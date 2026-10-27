"""The Game Master card's measurements, shared by gmaster_print.py (which draws its printing and screens) and gmaster.py
(which builds it). Plain Python: Blender's Python imports it too.

Hartung's Game Master (1990), slate grey: 170 x 97 x 33 mm (Wikipedia), its parts placed from a photograph of its face
square on (0.108 mm a pixel against its width), its back from photographs of it; its LCD 64 x 64 dots. Millimetres in
handheld.py's frame: x from its middle (left to right), z up from its bottom edge, y back from its face.

Its face (OUTLINE: a rounded rectangle): the glossy black band (BAND: its outline, standing proud: a visor along the top
edge ending in a tab over each wing, sweeping down round the screen, its left side a long diagonal) and the silver
surround on it (SURROUND: the orange line round the LCD, GAME MASTER under it); the speaker's 16 holes and the D-pad on
the left wing, START and SELECT, A and B on the right, the two mould seams. Its back: a lobe over each battery bay and the
recessed middle, the cartridge's slot at its top (the cartridge goes in from the top edge, its label out of the back).

Two textures: the print (ATLAS square, REGIONS: `face` from the front, `label` the cartridge's, and swatches) and the
screens (MEDIA_REGIONS: the start-up screen, a made-up game's title and two moments of it, in the LCD's dark dots on its
pale grey-green). A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 170.0, 97.0, 26.0
HALF = WIDTH / 2
LOBES = dict(x=(24.0, 81.0), z=(8.0, 90.0), depth=7.0)    # the battery lobes on the back


def _arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def outline():
    top, bottom = 10.0, 14.0
    return (_arc(HALF - bottom, bottom, bottom, -90.0, 0.0, 7) + _arc(HALF - top, HEIGHT - top, top, 0.0, 90.0, 5)
            + _arc(-HALF + top, HEIGHT - top, top, 90.0, 180.0, 5) + _arc(-HALF + bottom, bottom, bottom, 180.0, 270.0, 7))


SPAN = (-HALF, HALF, 0.0, HEIGHT)
BAND = dict(outline=[(-80.0, 96.6), (-81.6, 93.0), (-81.6, 87.5), (-59.0, 86.0), (-45.0, 15.0), (-40.0, 12.5),
                     (37.0, 12.5), (43.5, 16.0), (45.5, 80.0), (47.5, 84.0), (69.0, 84.5), (71.0, 88.0), (69.0, 96.6)],
            proud=2.4)
SURROUND = dict(rect=(-38.6, 39.2, 18.9, 89.1), r=8.0, proud=0.8)
LINE = dict(rect=(-29.0, 30.0, 25.0, 83.0))
SCREEN = dict(size=(41.6, 43.2), at=(1.7, 52.9), pixels=(64, 64))
DPAD = dict(at=(-65.6, 22.7), arm=11.0, half=4.6)
SPEAKER = dict(rows=[(-73.7, 71.8), (-75.6, 67.8), (-73.7, 63.9), (-71.8, 59.9)], pitch=4.1, count=4, r=0.95)
BUTTONS = dict(a=(54.9, 19.2), b=(71.9, 28.9), r=5.5, start=(57.0, 54.0), select=(68.9, 58.5), small=2.8)
SEAMS = [[(-60.0, 86.0), (-56.0, 60.0), (-52.0, 30.0), (-46.0, 3.0)], [(33.0, 0.5), (55.0, 15.0), (78.0, 33.0),
                                                                        (85.0, 37.0)]]
CART = dict(size=(45.0, 6.0, 50.0), out=3.0)              # width, thickness, height; how far its top shows

PALETTE = ["#3A403E", "#B4BEB4"]                           # the LCD's dark dots on its pale grey-green
MADE_UP = ("Gravel Kings (Europe)", "megadrive")

COLOURS = dict(body="#737F82", band="#222021", surround="#CDCFD3", orange="#BA5430", lcd="#89928D", button="#C2CBCC",
               dark="#101112", cart="#6E787C")

REGIONS = dict(face=(0, 0, 1020, 582), label=(0, 590, 270, 300))
SWATCHES = {name: (300 + 32 * (k % 8), 610 + 32 * (k // 8)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(boot=(0, 0, 320, 320), title=(328, 0, 320, 320), game1=(656, 0, 320, 320),
                     game2=(0, 328, 320, 320))

FPS = 30
LENGTH = 240                 # 8 s
