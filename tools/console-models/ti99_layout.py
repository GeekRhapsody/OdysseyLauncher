"""The TI-99/4A card's measurements, shared by ti99_print.py (which draws its printing) and ti99.py (which builds it).
Plain Python: Blender's Python imports it too.

The Texas Instruments TI-99/4A (1981), the silver and black one, 381 mm wide, 259 deep and 71 high (a listing's 381 x 71
x 259), its two joysticks (the Wired Remote Controllers) in front of it at its left, a command module with a made-up
game, Odyssey, going into its slot. Millimetres: x from its middle (left to right), y back from its front, z up from the
table. Measured from photographs on Wikimedia Commons (one straight down on it, which its 19.05 mm key pitch confirms;
from the front left and right, with a module in, with the joysticks), the profile from the three-quarter ones.

The computer: a black base, the aluminium over it (PROFILE: the front's lip, the deck sloping up to a step, the raised
back section with its vents, falling at the back). In the deck: the black keyboard surround (SURROUND), its keys
standing in it, the strip with DEL INS ERASE ... QUIT and the power light over them; the black module bay at the right
(BAY), its floor parallel to the deck, the slot at its back diving under the back section, where the module lies, its
front standing out of it (MODULE). The joystick port is in the base's left side (PORT).

The keys are laid out in units of U from KEYS_X0, in rows from the back (the digits') to the front (the space bar's).
The deck is a plane at SLOPE: a key stands on it in the deck's frame (x across, s up the slope from its front edge, h
off it), and deck_point() maps a point of that frame to the model's (y, z).

One texture (ATLAS square, REGIONS): `top` (the aluminium from above, brushed: the vents, the logo, TI-99/4A, the
surround with the strip and the keys' tops and legends, the bay with Solid State Software), `module` (the module's top:
its label) and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024
U = 19.05

WIDTH, DEPTH, HEIGHT = 381.0, 259.0, 71.0
BASE = 20.0                      # the black base's top, the aluminium's foot
FRONT = (4.0, 33.0)              # the deck's front edge (y, z)
STEP = (186.0, 60.0)             # its back edge, at the step's foot
SLOPE = math.atan2(STEP[1] - FRONT[1], STEP[0] - FRONT[0])
PROFILE = [                      # the aluminium's side outline (y, z), round from its front foot
    (0.0, BASE), (DEPTH, BASE), (DEPTH, 65.0), (DEPTH - 4.0, HEIGHT), (190.0, HEIGHT), (187.0, 68.0), STEP, FRONT,
    (1.0, 31.5), (0.0, 29.0),
]

SURROUND = dict(x=(-177.6, 55.9), y=(5.5, 125.3), depth=2.5, r=5.0)
STRIP = dict(x=(-173.6, 49.7), y=(111.0, 121.8), light=(38.6, 118.8))
KEYS_X0, ROW1 = -173.2, 95.8     # the back row's left edge; its middle (s)
KEY = dict(height=10.0, inset=2.4)
ROWS = [
    (0.0, [(c, 1.0) for c in "1234567890="]),
    (0.5, [(c, 1.0) for c in "QWERTYUIOP/"]),
    (0.75, [(c, 1.0) for c in "ASDFGHJKL;"] + [("ENTER", 1.0)]),
    (0.0, [("SHIFT", 1.25)] + [(c, 1.0) for c in "ZXCVBNM,."] + [("SHIFT", 1.5)]),
    (0.0, [("ALPHA LOCK", 1.25), ("CTRL", 1.0), (None, 0.27), (" ", 7.5), (None, 0.22), ("FCTN", 1.0)]),
]
SHIFTED = dict(zip("1234567890=", "!@#$%^&*()+"))
OVERLAY = ["DEL", "INS", "ERASE", "CLEAR", "BEGIN", "PROC'D", "AID", "REDO", "BACK", "", "QUIT"]

BAY = dict(x=(63.5, 179.2), y=(5.0, STEP[0]), depth=10.0, landing=(128.0, 164.0), label=((73.0, 160.0), (14.5, 22.0)))
# The module: w, length, thickness; where its top's front edge is when it is in (y, z); how steeply it and the slot dive
# down to the back (degrees); how far back from its place (along the slot) and up it waits; the slot's margin round it.
MODULE = dict(size=(100.0, 85.0, 15.0), front=(150.0, 62.0), dive=15.0, out=(-55.0, 40.0), margin=1.5)
VENTS = dict(x=(65.1, 178.3), y=(200.8, 251.4), count=7, width=3.0)
LOGO = dict(at=(-168.0, 135.5), model=(8.8, 138.4))
PORT = dict(y=120.0, z=10.0)                                         # the joystick port in the base's left side

# The joysticks: their bodies' foot and top, height; the stick's place on the body, its foot's and top's radius, length;
# the fire button's place and size; where each stands and its turn.
JOYSTICK = dict(foot=(100.0, 72.0), top=(80.0, 52.0), height=22.0, stick=(-18.0, 0.0), radius=(6.0, 3.6), length=58.0,
                button=(31.0, 0.0), bar=(12.0, 40.0, 5.0), at=[(-150.0, -78.0, 8.0), (-40.0, -92.0, -6.0)])

COLOURS = dict(alu="#C9CACB", key="#1E1E20", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 1024, 696), module=(0, 704, 200, 170))
SWATCHES = dict(alu=(912, 720), black=(944, 720), key=(976, 720), dark=(1008, 720), orange=(912, 752),
                light=(944, 752), module=(976, 752))

FPS = 30
LENGTH = 240                 # 8 s


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return FRONT[0] + s * c - h * k, FRONT[1] + s * k + h * c


def keys():
    """Every key: (legend, x0, x1, s), s its row's middle up the deck; the rows from the back to the front. A gap in a
    row is None."""
    out = []
    for r, (offset, row) in enumerate(ROWS):
        x = KEYS_X0 + offset * U
        s = ROW1 - r * U
        for legend, width in row:
            if legend is not None:
                out.append((legend, x, x + width * U, s))
            x += width * U
    return out
