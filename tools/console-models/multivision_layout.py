"""The Othello Multivision card's measurements, shared by multivision_print.py (which draws its printing) and
multivision.py (which builds it). Plain Python: Blender's Python imports it too.

Tsukuda Original's Othello Multivision FG-1000 (1983), an SG-1000 made under licence with Othello built in. No maker's
figure was found; it is about 263 x 156 x 40 mm, scaled from the SG-1000 cartridge (82.8 mm wide, measured on 1200 dpi
scans) standing in its slot in a photograph, and the parts placed from a photograph of it from straight above.
Millimetres: x from its middle (left to right), y back from its front edge, z up from the table.

A cream shell (SHELL: its outline in plan, its corners rounded, its front edge chamfered) on a thin navy base. Its top:
Othello Multivision in navy at the back left, the slot under its smoked, glossy flap (FLAP: flush with the top, hinged
at its back edge; a cartridge pushes it down), the vents' slots at the back right; in front, a large panel recessed a
step (RECESS), and in it three plates standing up: the keys' (the maroon keys: 0 and 9 tall at the ends, A to H, 1 to 8,
S-1 and S-2), PAUSE's, and the joystick's (the dome, the short stick and its ball). Tsukuda Original moulded at the
front right.

One texture (ATLAS square, REGIONS): `top` (the shell's top seen from above, planar-mapped onto every face facing up:
the logo, the keys' tops and legends, the joystick plate's arrows), `face` (the cartridge's face, its label on it: a made-up game) and
swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 263.0, 156.0, 40.0
HALF = WIDTH / 2
BASE = 12.0                  # the navy base's top
SHELL = dict(corner=6.0, chamfer=(4.0, 4.0))               # the corners' radius in plan; the front edge's chamfer

# Rectangles (x0, x1, y0, y1) in plan.
RECESS = dict(rect=(-113.6, 111.7, 9.0, 107.6), r=6.0, depth=2.0)
PLATES = dict(keys=(-103.5, 60.0, 27.6, 99.6), pause=(62.5, 103.0, 73.5, 99.6), joystick=(62.5, 103.0, 29.7, 71.4))
PLATE_HEIGHT, PLATE_R = 1.5, 3.0                           # above the recess's floor
FLAP = dict(rect=(-44.5, 44.5, 121.3, 146.1), thickness=1.2, open=-84.0)
VENTS = dict(x=(54.8, 111.7), y=(127.6, 153.0), count=12, width=2.4, depth=3.0)


def column(k):
    """The middle of the keys' column k (A and 1 are 0; the tall 0 is -1, the tall 9 is 8)."""
    return -74.0 + 15.28 * k


KEY = dict(w=11.0, height=4.0, inset=0.9)
# The keys: (legend, x0, x1, y0, y1).
KEYS = ([("0\n✱", column(-1) - 5.5, column(-1) + 5.5, 65.5, 88.6), ("9\n#", column(8) - 5.5, column(8) + 5.5, 65.5, 88.6)]
        + [(c, column(k) - 5.5, column(k) + 5.5, 76.0, 88.6) for k, c in enumerate("ABCDEFGH")]
        + [(c, column(k) - 5.5, column(k) + 5.5, 59.2, 72.2) for k, c in enumerate("12345678")]
        + [("S-1", -74.0, -32.1, 38.5, 49.3), ("S-2", -12.1, 29.1, 38.5, 49.3), ("PAUSE", 68.5, 95.9, 80.3, 88.3)])
STICK = dict(at=(83.6, 50.6), dome=(12.5, 6.0), r=3.4, top=21.0, ball=5.0)

# The cartridge: an SG-1000 cartridge, standing in the slot, its label to the front; its label on its face.
CART = dict(size=(82.8, 18.8, 112.0), bottom=2.0, label=(72.0, 92.0, 4.0))   # the label's width, height, top margin

COLOURS = dict(cream="#E7E7DD", navy="#393F4F", maroon="#813236", logo="#19387B", stick="#204360", black="#141416",
               smoked="#0A0B0C", shell="#202022")

REGIONS = dict(top=(0, 0, 1024, 607), face=(0, 615, 298, 403))
SWATCHES = dict(cream=(326, 632), navy=(358, 632), maroon=(390, 632), stick=(422, 632), shell=(454, 632),
                black=(486, 632))

FPS = 30
LENGTH = 240                 # 8 s
