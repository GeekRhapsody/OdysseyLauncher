"""The Fairchild Channel F card's measurements, shared by channelf_print.py (which draws its printing) and channelf.py
(which builds it). Plain Python: Blender's Python imports it too.

The Fairchild Channel F (1976), the first one, 305 mm wide, 330 deep and 89 high (the Computer History Museum's 3.5 x 12
x 13 inches), its two controllers lying in front of it, a Videocart (the size of an 8-track tape, as they were made)
with a made-up game, Odyssey, going into its slot. Millimetres: x from its middle (left to right), y back from its
front, z up from the table. Measured from photographs on Wikimedia Commons (Evan-Amos's from the front left; one
straight down on it; others from the front and of its Videocarts).

The console: walnut sides and front, sloping in to its foot all round (SIDE), the black top between them (PROFILE): the
front panel sloping gently up to the lid, the lid over the controllers' compartment behind it, its glossy top with the
chrome strip (FAIRCHILD, VIDEO ENTERTAINMENT SYSTEM). On the panel: RESET and the keys 1 to 4 (KEYS), and at its right
the cartridge's door in the lid's front face (SLOT, DOOR, hinged along its top), the INSERT CARTRIDGE plate in front of
it and the Press to Eject bar (PLATE, EJECT). The controllers are the pistol grips, each with its knob on its neck at
one end (CONTROLLER), lying on their sides, their cables running to the console's left side.

One texture (ATLAS square, REGIONS): `panel` (the front panel from above: the keys' tops, TIME MODE HOLD START and the
rest, INSERT CARTRIDGE, Press to Eject), `strip` (the lid's chrome strip from above), `door` (the cartridge door's
ribbed face), `cart` (the Videocart's top: its label), `wood` (the walnut's grain), `grip` (a controller's ribbed side)
and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 305.0, 330.0, 89.0
SIDE = dict(foot=15.0, black=44.0)    # how far the walnut slopes in at the foot; the walnut's top at the front
PANEL = dict(front=(4.0, 47.0), back=(83.0, 52.0))      # the front panel's front and back edges (y, z)
LID = dict(y=85.0, top=HEIGHT)
PROFILE = [                           # the side outline (y, z), round from the front's foot
    (SIDE["foot"], 0.0), (DEPTH - SIDE["foot"], 0.0), (DEPTH, HEIGHT - 6.0), (DEPTH - 3.0, HEIGHT),
    (LID["y"] + 3.0, HEIGHT), (LID["y"], HEIGHT - 3.0), (LID["y"], PANEL["back"][1] + 2.0), PANEL["back"],
    PANEL["front"], (0.0, SIDE["black"]),
]
STRIP = dict(x=(-135.0, 136.0), y=(252.0, 276.0))

KEYS = dict(x=[-102.4, -81.1, -61.0, -42.1, -22.0], y=39.0, size=13.0, height=5.0,
            names=["RESET", "1", "2", "3", "4"])
SLOT = dict(x=(12.0, 118.0), z=(52.0, 78.0), depth=125.0)     # the mouth in the lid's front face; how far it runs back
DOOR = dict(inset=1.0, open=80.0)                               # its gap round the mouth; how far it swings in
PLATE = dict(x=(22.0, 108.0), y=(58.0, 82.0), height=2.0)
EJECT = dict(x=(27.0, 119.0), y=(18.0, 36.0), height=4.0)

# The Videocart: w, length, t; its front end's y when it is in; how far out in front of that it waits.
CART = dict(size=(102.0, 137.0, 22.0), front=45.0, out=110.0)
# The controllers: the grip's length, width and height; the neck's radius and length; the knob's width, height and
# thickness; where each lies (x, y of its grip's middle) and its turn (degrees).
CONTROLLER = dict(grip=(150.0, 42.0, 34.0), neck=(8.0, 12.0), knob=(46.0, 42.0, 18.0),
                  at=[(-118.0, -66.0, -16.0), (-80.0, -122.0, -22.0)])
PORT = dict(y=250.0, z=30.0)          # where the cables go into the console's left side

COLOURS = dict(black="#151517", wood="#5A3420", cart="#F2C230", print="#FFFFFF")

REGIONS = dict(panel=(0, 0, 800, 236), strip=(0, 244, 800, 62), door=(0, 314, 280, 70), cart=(0, 392, 206, 276),
               wood=(216, 392, 400, 160), grip=(216, 560, 400, 110))
SWATCHES = dict(black=(912, 400), wood=(944, 400), cream=(976, 400), yellow=(1008, 400), cart=(912, 432),
                chrome=(944, 432), dark=(976, 432), gloss=(1008, 432))

FPS = 30
LENGTH = 240                 # 8 s


def panel_z(y):
    """The front panel's height at y."""
    (y0, z0), (y1, z1) = PANEL["front"], PANEL["back"]
    return z0 + (y - y0) * (z1 - z0) / (y1 - y0)
