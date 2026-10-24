"""The Super Nintendo's measurements, shared by snes_print.py (which draws its printing) and snes.py (which builds it).
Plain Python: Blender's Python imports it too.

The PAL Super Nintendo, which is the Super Famicom's shape (200 x 242 x 72 mm) with its own name on it. Millimetres: x
from its middle (left to right), y back from its front edge, z up from the table. The rest was measured from
photographs on Wikimedia Commons (Evan-Amos's Super Famicom from the front left and right, a PAL console), scaled by
its width.

The body's corners are rounded seen from above, and its top's edges rounded over; a crease runs round its sides where
the shells meet. On the top stands a darker panel: the cartridge slot across it, POWER (a slide switch in a well),
EJECT (a broad flat button) and RESET (a square button in a well) in front of the slot, the four coloured dots behind
its right end. In front of the panel the name and the power light; in the front face, a long rounded recess holds the
two controller ports.

One texture (ATLAS square, REGIONS): `top` (the top seen from above, planar-mapped onto every face facing up: the panel,
the buttons' legends, the slot's flaps, the dots, the name), `front` (the ports' recess, seen from in front) and `label`
(the cartridge's label: a made-up game, Odyssey), and swatches for small parts. A region is (x, y, width, height) in
pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, TOP = 200.0, 242.0, 66.0
CORNER = 18.0                    # the body's corners, seen from above
EDGE = 7.0                       # the top's edges rounded over
CREASE = 24.0                    # the shells' seam round the sides

PANEL = dict(x=86.0, y=(64.0, 210.0), r=9.0, height=2.5)          # the dark panel: its half width, front and back
SLOT = dict(x=72.0, y=(150.0, 172.0), depth=46.0)                 # the cartridge slot: half its length, its sides
POWER = dict(x=(-76.0, -50.0), y=(80.0, 104.0), knob=(16.0, 10.0, 6.0), travel=9.0)  # its well; the knob, its travel
EJECT = dict(x=(-32.0, 18.0), y=(76.0, 100.0), height=2.6)
RESET = dict(x=(38.0, 62.0), y=(74.0, 98.0), height=2.2)
DOTS = (66.0, 192.0, 9.5)                                         # the coloured dots' circle: x, y, radius
LED = (60.0, 30.0, 6.0, 2.2)                                      # the power light: x, y, length, width
PORTS = dict(x=78.0, z=(12.0, 40.0), depth=3.0)                   # the ports' recess in the front

CART = dict(width=135.0, height=90.0, arch=6.0, thickness=20.0,   # the cartridge, its top arched
            label=(108.0, 74.0, 8.0), inserted=42.0)              # its label (width, height, from its top); how deep

KINDS = {
    "snes": dict(name="PAL", case="#D4D4D6", panel="#A9A9AD"),
}

COLOURS = dict(cart="#8E8E93", dark="#2A2A2E", flap="#5C5C61")

REGIONS = dict(top=(0, 0, 700, 847), front=(712, 0, 312, 62), label=(712, 72, 312, 214))
SWATCHES = dict(led=(728, 312), dark=(760, 312), flap=(792, 312))  # each a 24 x 24 block's middle

FPS = 30
LENGTH = 240                 # 8 s
