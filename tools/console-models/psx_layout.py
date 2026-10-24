"""The PlayStation's measurements, shared by psx_print.py (which draws its printing) and psx.py (which builds it).
Plain Python: Blender's Python imports it too.

The first model (the PAL SCPH-1002), 270 x 188 x 60 mm, in its grey. Millimetres: x from its middle (left to right), y
back from its front edge, z up from the table. The rest was measured from photographs on Wikimedia Commons (Evan-Amos's
three-quarter views, a view from behind of two models side by side), scaled by its width.

Its top is a channel between a block at each end: on the left block POWER and RESET, on the right OPEN, each a round
button in a round well; in the channel the lid, a broad disc hinged at its back over the well the disc spins in; a
raised strip along the back. In the middle of its front, under the lid, a recess holds the controller ports
and the memory card slots. The right end is ribbed with vents.

One texture (ATLAS square, REGIONS): `top` (the top seen from above, planar-mapped onto every face facing up: the
lid's SONY and PlayStation logos, the buttons' legends, the seams), `front` (the recess's back wall: the ports, the
slots and their numbers), `label` (the disc's label side, a made-up game, Odyssey) and `data` (its other side, black,
as the PlayStation's discs are), and swatches for small parts. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, TOP = 270.0, 188.0, 56.0
CORNER = 7.0                     # the body's corners, seen from above

CHANNEL = 3.0                                                    # how far the channel is sunk below the blocks
LID = dict(x=8.0, y=92.0, r=74.0, thickness=3.0, dome=1.2)       # its middle; it stands on the channel's floor
WELL = dict(r=66.0, depth=19.0)                                  # under it, the well the disc spins in
SPINDLE = dict(r=8.5, height=11.0)
LENS = dict(x=-40.0, sled=(14.0, 34.0), r=2.6)                   # the laser's lens on its sled, left of the spindle
BUTTONS = dict(power=(-104.0, 54.0, 15.5), reset=(-110.0, 108.0, 8.5), open=(106.0, 30.0, 15.5))  # x, y, radius
BUTTON = dict(well=1.8, height=2.4)                              # a well this much wider round each; how far it stands
LED = (-104.0, 15.0, 7.0, 2.4)                                   # the power light's slot: x, y, length, width
SEAMS = (-74.0, 82.0)                                            # the channel's sides, x
BACK = dict(y=168.0, height=2.0)                                 # the raised strip along the back
RECESS = dict(x=(-58.0, 62.0), depth=11.0, z=(7.0, 40.0))        # the ports' recess in the front
RIBS = dict(y=[20.0 + 4.2 * k for k in range(36)], width=2.0, z=(8.0, 48.0), depth=3.0)  # the right end's vents

DISC = dict(r=60.0, hole=7.5, thickness=1.2)
SEAT = (LID["x"], LID["y"], TOP - CHANNEL - WELL["depth"] + SPINDLE["height"] + DISC["thickness"] / 2)  # on the spindle

COLOURS = dict(case="#A7A8AA", dark="#1E1F22")

REGIONS = dict(top=(0, 0, 1024, 713), front=(0, 722, 512, 145), label=(528, 722, 290, 290), data=(830, 722, 190, 190))
SWATCHES = dict(led=(16, 900), dark=(48, 900), lens=(80, 900), metal=(112, 900))  # each a 24 x 24 block's middle

FPS = 30
LENGTH = 240                 # 8 s
