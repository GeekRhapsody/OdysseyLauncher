"""The Macintosh card's measurements, shared by macintosh_print.py (which draws its printing and screens) and
macintosh.py (which builds it). Plain Python: Blender's Python imports it too.

The original Apple Macintosh (1984), 244 mm wide, 281 deep and 345 high (13.6 x 9.6 x 10.9 inches), its keyboard (340 x
149, LACMA's figures for one) and mouse (98 x 64 x 38) in front of it, a 3.5-inch floppy with a made-up game, Odyssey,
going into its drive. Millimetres: x from its middle (left to right), y back from the front face's foot, z up from the
table. Measured from the drawings of its housing's design patent (US D285,687: from the front, the side, above and
behind) and from photographs on Wikimedia Commons.

The case: its side outline (PROFILE: the front face leaning back, the top rising a little towards it, the chamfer at the
back's top, the chin set back under the front face), the handle cut into the back of its top, the vents in its sides'
foot. In the front face (FACE: its own frame, u across, v up it, w out of it): the screen's sunk frame and the tube's
face in it (SCREEN), the floppy slot (SLOT) and the finger recess at its right end, the rainbow Apple. The keyboard
(KEYBOARD) is a slab, its keys standing on its sloping top; the mouse (MOUSE) a box, its button across the front of its
top. The keyboard's coiled cord runs to the chin's front, the mouse's cable round the right to the back.

One texture (ATLAS square, REGIONS): `keys` (the keyboard from above: the keys' tops and legends), the screens (`disk`
the question mark asking for a disk, `happy` the happy Mac, `welcome` Welcome to Macintosh., `game` the game in its
window), `floppy` (the floppy's top: its shutter and label), `mouse` (the mouse from above), `apple` (the rainbow Apple)
and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024
U = 19.05

WIDTH, DEPTH, HEIGHT = 244.0, 280.7, 345.0
LEAN = math.radians(7.9)          # the front face's lean back from the vertical
FOOT = 69.7                       # the front face's foot (z), where the chin starts under it
PROFILE = [                       # the side outline (y, z), round from the front face's foot
    (0.0, FOOT), (28.0, 66.3), (37.0, 60.0), (37.0, 0.0), (DEPTH, 0.0), (DEPTH, 280.7), (256.8, 328.4),
    (42.0, HEIGHT - 2.0), (37.8, 342.0),
]
HANDLE = dict(x=45.0, y=175.0, z=318.0)          # the handle's half width; where it starts (y); its floor
VENTS = dict(y=(99.5, 258.8), z=[38.0, 44.5, 51.0, 57.5, 64.0], height=2.6, depth=1.6)   # in the sides

SCREEN = dict(frame=(200.0, 161.5, 12.0), glass=(184.4, 149.1, 8.0), v=172.6, depth=14.0, bulge=4.0)   # w, h, r
SLOT = dict(u=(-39.5, 60.8), v=(36.6, 43.4), depth=100.0)
NOTCH = dict(u=(58.1, 101.4), v=(20.2, 64.0), depth=5.0, r=4.0)          # the finger recess at the slot's end
APPLE = dict(u=(-100.3, -84.0), v=(17.6, 35.5))
JACK = (79.0, 27.0)               # the keyboard's jack in the chin's front (x, z)

KEYBOARD = dict(size=(340.0, 149.0), height=(32.0, 46.0), at=(-14.0, -36.0))   # w, d; front and back; its back edge
KEYS_X0, ROW1 = -142.9, 116.0     # in the keyboard's frame: x from its middle, v from its front edge
KEY = dict(height=8.0, inset=2.2)
ROWS = [
    (0.0, [(c, 1.0) for c in "`1234567890-="] + [("Backspace", 2.0)]),
    (0.0, [("Tab", 1.5)] + [(c, 1.0) for c in "QWERTYUIOP[]"] + [("\\", 1.5)]),
    (0.0, [("Caps Lock", 1.75)] + [(c, 1.0) for c in "ASDFGHJKL;'"] + [("Return", 2.25)]),
    (0.0, [("Shift", 2.25)] + [(c, 1.0) for c in "ZXCVBNM,./"] + [("Shift", 2.75)]),
    (0.0, [("Option", 1.5), ("⌘", 1.5), (" ", 9.0), ("Enter", 1.5), ("Option", 1.5)]),
]

# The mouse: w, length, h; how much of its length the button takes; where its middle sits (x, y) and its turn.
MOUSE = dict(size=(64.0, 98.0, 38.0), button=0.42, at=(196.0, -92.0, -6.0))
# The floppy: w, d, t; the shutter's width and depth; how far out of the slot it waits.
FLOPPY = dict(size=(90.0, 94.0, 3.3), shutter=(46.0, 30.0), out=70.0)

COLOURS = dict(case="#D6CEBA", key="#B9B19C", print="#FFFFFF")

REGIONS = dict(keys=(0, 0, 680, 298), disk=(0, 306, 256, 206), happy=(264, 306, 256, 206),
               welcome=(528, 306, 256, 206), game=(0, 520, 256, 206), floppy=(264, 520, 180, 188),
               mouse=(452, 520, 128, 196), apple=(588, 520, 48, 54))
SWATCHES = dict(case=(912, 760), key=(944, 760), dark=(976, 760), tube=(1008, 760), floppy=(912, 792),
                shutter=(944, 792), cord=(976, 792), legend=(1008, 792))

FPS = 30
LENGTH = 240                 # 8 s


def face_point(u, v, w):
    """The model's point u across the front face from its middle, v up it from its foot and w out of it."""
    s, c = math.sin(LEAN), math.cos(LEAN)
    return u, v * s - w * c, FOOT + v * c + w * s


def keys():
    """Every key: (legend, x0, x1, v), v its row's middle in the keyboard's frame; the rows from the back to the
    front."""
    out = []
    for r, (offset, row) in enumerate(ROWS):
        x = KEYS_X0 + offset * U
        v = ROW1 - r * U
        for legend, width in row:
            out.append((legend, x, x + width * U, v))
            x += width * U
    return out
