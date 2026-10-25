"""The Wii's measurements, shared by wii_print.py (which draws its printing) and wii.py (which builds it). Plain Python:
Blender's Python imports it too.

The Wii standing on its stand, 44 x 215.4 x 157 mm, its remote leaning against its right side. Millimetres: x from the
console's middle (left to right), y back from its front face, z up from the table. The rest was measured from
photographs on Wikimedia Commons (Evan-Amos's view of the console on its stand with the remote, a close view of its
front), scaled by its height.

The front: POWER (its light beside it), RESET, the SD card's flap and EJECT down its left, the disc slot down its right,
the Wii logo at its foot. The right side: a panel with Nintendo's name. The stand: a grey cradle under the front half,
and a round plate under the back half.

One texture (ATLAS square, REGIONS): `front` (the front face, seen from in front), `side` (the right side, seen from
the right with the front to the left), `remote` (the remote's face, top up), `label` and `data` (the disc's two sides:
a made-up game, Odyssey), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 44.0, 215.4, 157.0
LIFT = 14.0                      # how high the stand holds it
EDGE = 3.0                       # its edges' rounding

SLOT = dict(x=(5.5, 11.5), z=(18.0, 146.0), depth=24.0)            # the disc slot in the front
BUTTONS = dict(power=(-11.5, 140.0, (13.0, 7.0)), reset=(-11.5, 124.0, (13.0, 5.0)), eject=(-11.5, 22.0, (13.0, 6.0)))
LIGHT = (-16.5, 140.0, 1.2)                                         # the power light, beside POWER
FLAP = (-11.5, 82.0, (13.0, 34.0))                                  # the SD card's flap, printed
SIDE_PANEL = dict(y=(12.0, 206.0), z=(10.0, 150.0))                 # the panel in the right side

STAND = dict(cradle=(66.0, 96.0, 24.0), plate=(78.0, 3.0), colour="#A3A8AE")   # cradle w, d, h; plate radius, height

REMOTE = dict(size=(36.2, 148.0, 30.8), at=(68.0, 40.0), lean=-11.0)  # w, h, d; its foot; its lean, onto the side
DISC = dict(r=60.0, hole=7.5, thickness=1.2)

COLOURS = dict(case="#F3F3F1", front="#EAEAE7", dark="#121214", stand="#A3A8AE")

REGIONS = dict(front=(0, 0, 200, 714), side=(208, 0, 816, 595), remote=(208, 604, 110, 420),
               label=(330, 604, 300, 300), data=(640, 604, 200, 200))
SWATCHES = dict(glow=(864, 620), green=(896, 620), led=(928, 620), dark=(960, 620), white=(992, 620))

FPS = 30
LENGTH = 240                 # 8 s
