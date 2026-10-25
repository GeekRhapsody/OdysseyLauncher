"""The Atari 5200 set's measurements, shared by atari5200_print.py (which draws its printing) and atari5200.py (which
builds it). Plain Python: Blender's Python imports it too.

The Atari 5200 (1982), the four-port model, 387 x 337 x 108 mm (the Computer History Museum's 15 1/4 x 13 1/4 x 4 1/4
inches), and its controller, 67 mm across (the museum's 2 5/8 inches). Millimetres: x from its middle (left to right),
y back from its front face, z up from the table. The rest was measured from Evan-Amos's photographs on Wikimedia Commons
(the console from the front left and right, with a cartridge, from the back right and behind, with its storage lid
open, with its controller; the controller from above and from the front left; the cartridge), scaled by its width.

The console: a slab, its top sloping up from the front face to the back (TOP), the front face holding the four
controller ports, the vented base under it set back; at the back the slab overhangs, a narrower block (BLOCK) under
it. The top, front to back, along its slope (s): a plain band with the power light at its right, a row of vents, the
brushed band with ATARI 5200 at its left and POWER ON/OFF beside its right end, the slot band (the cartridge slot
between two blocks of vents), and the storage compartment's lid. The controller: a wedge tapering to its front, the
stick in its well at the back, START, PAUSE and RESET along its back edge, the fire buttons in its sides, the keypad's
twelve keys in front of the ATARI 5200 strip.

One texture (ATLAS square, REGIONS): `top` (the console's top seen from above along its slope: the bands, the logo,
POWER ON/OFF, the light's window, the lid's seam), `front` (the front face: the ports' panel), `pad` (the controller's
top: the keypad's legends, the strip, START, PAUSE and RESET), `label` (the cartridge's: a made-up game, Odyssey), and
swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 387.0, 337.0, 108.0
TOP = ((0.0, 46.0), (DEPTH, HEIGHT))               # the top's front and back edges, (y, z)
SLOPE = math.atan2(TOP[1][1] - TOP[0][1], TOP[1][0] - TOP[0][0])
TOP_LENGTH = math.hypot(TOP[1][1] - TOP[0][1], TOP[1][0] - TOP[0][0])
UNDER = 72.0                                       # the slab's underside at the back
PROFILE = [(8.0, 0.0), (148.0, 0.0), (228.0, UNDER), (DEPTH, UNDER), (DEPTH, HEIGHT - 3.0), (DEPTH - 3.0, HEIGHT),
           (2.0, TOP[0][1] + 0.5), (0.0, TOP[0][1] - 2.0), (0.0, 14.0), (6.0, 12.0), (6.0, 2.0)]
BLOCK = dict(x=(-112.0, 112.0), y=(140.0, 328.0))  # the narrower block under the slab's back
BASE_VENTS = dict(z=(3.5, 10.5), x=(-180.0, 180.0), pitch=5.0, width=2.2)   # in the base's front, under the front face

# The top's bands, s along the slope from its front edge.
FRONT_VENTS = dict(s=(90.0, 102.0), x=(-186.0, 186.0), pitch=5.0, width=2.2, depth=2.0)
SILVER = dict(s=(110.0, 186.0), x=(-193.5, 141.0), raised=0.6)
POWER = dict(x=(149.0, 182.0), s=(112.0, 134.0), height=3.0)
LIGHT = dict(x=171.0, s=70.0, r=3.2)
SLOT_BAND = dict(s=(186.0, 262.0))
SLOT_VENTS = [dict(x=(-186.0, -66.0)), dict(x=(66.0, 186.0))]
SLOT_VENT_S = (194.0, 254.0)
SLOT = dict(x=(-58.0, 58.0), s=(206.0, 238.0), depth=56.0)
LID = dict(s=(262.0, TOP_LENGTH))

# The front face: the ports' panel, recessed, and the four ports in it (each its middle's x).
PORT_PANEL = dict(x=(-112.0, 98.0), z=(17.0, 41.0), depth=2.0)
PORTS = dict(x=[-84.0, -33.0, 19.0, 71.0], z=29.0, size=(33.0, 12.0))

# The cartridge: w x d x h, standing in the slot (its bottom DROP below the top), its label on its front.
CART = dict(size=(104.0, 21.0, 112.0), label=(84.0, 64.0), ribs=13, seat_depth=50.0)

# The controller in its own plan (x across, y back from its front end): a trapezoid, its back end wider; its height at
# each end; the stick's well and the stick; the keypad's keys; START, PAUSE and RESET; the fire buttons in its sides.
PAD = dict(length=170.0, width=(58.0, 67.0), height=(22.0, 30.0), at=(-218.0, -96.0), turn=-22.0)
WELL = dict(y=128.0, r=21.0, depth=4.0)
STICK = dict(r=(9.0, 7.0), length=46.0, boot=(15.0, 6.0))      # the shaft's foot and top radii, its length; the boot
KEYPAD = dict(y=(16.0, 90.0), x=(-15.5, 15.5), rows=4, cols=3, key=(11.0, 10.0), height=2.5)
STRIP = dict(y=(95.0, 104.0))
TOP_BUTTONS = dict(y=(157.0, 167.0), x=[(-30.0, -12.0), (-9.0, 9.0), (12.0, 30.0)], height=1.8)   # START, PAUSE, RESET
FIRE = dict(y=[(120.0, 138.0), (141.0, 159.0)], z=(10.0, 20.0), out=3.0)   # two on each side

COLOURS = dict(case="#1E1E20", silver="#8E9094", black="#0D0D0F", key="#262628", red="#D23A2A", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 800, 710), front=(0, 718, 1024, 116), pad=(808, 0, 216, 540),
               label=(0, 842, 240, 182))
SWATCHES = dict(red=(840, 572), red_lit=(872, 572), black=(904, 572), case=(936, 572), silver=(968, 572),
                yellow=(1000, 572))

FPS = 30
LENGTH = 240                 # 8 s
