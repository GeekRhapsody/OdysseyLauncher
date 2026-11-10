"""The PlayStation's measurements, shared by psx_print.py (which draws its printing) and psx.py (which builds it).
Plain Python: Blender's Python imports it too.

The first model (the PAL SCPH-1002). Millimetres: x from its middle (left to right), y back from its front edge, z up
from the table. Its top is 270 x 188 mm, 56 mm off the table; its vents stand off each end. The top was measured from
the-liberator.net's photograph of a SCPH-1002 from above, its plane rectified to millimetres from its fitted edges (the
lid's outline comes out round to 0.4%, and POWER and OPEN mirror each other to 0.2 mm); the rest from its photographs
from behind and with the lid open, iFixit's teardown's front views and Evan-Amos's photographs on Wikimedia Commons.

Its top is a pod at each end (POWER, RESET and the power light on the left, OPEN on the right) and the middle between
them: in front, a strip flush with the pods, its front face set back a little; behind, a plate below the pods, gapped
from them where the lid's hinges are. The lid, a broad disc standing a little proud, shuts into a round well cut into
all three; under it the well's floor, the drive's mechanism, its spindle and the laser's lens on its sled. In the
middle's front face, two openings, each a memory card slot over a controller port; in its back, under the plate, the
ports panel, with PARALLEL I/O in the right pod's back and AC IN in the left's. Fins stand off both ends.

One texture (ATLAS square, REGIONS): `top` (the top seen from above, planar-mapped onto every face facing up: the lid's
SONY and PlayStation marks, its grip dots, the buttons' legends, the seams, the groove to OPEN, the compact disc mark),
`front` and `back` (the faces facing the front and the back, each seen straight on: the ports' numbers; the back's
ports and their names), `port` (the back of each front opening), `label` (the disc's label side, a made-up game,
Odyssey) and `data` (its other side, black, as the PlayStation's discs are), and swatches for small parts. A region is
(x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, TOP = 270.0, 188.0, 56.0
CORNER = 5.0                     # the body's corners, seen from above
EDGE = 2.5                       # the rounding of its top's edges

POD = 65.0                       # the pods' inner sides, x = -POD and POD; the strip in front meets them at a seam
SET_BACK = 2.0                   # how far the middle's front face is set back from the pods'
PLATE = dict(drop=3.0, gap=2.0, gap_depth=14.0, back=186.0, under=48.0)  # behind the lid: below the pods; its gaps
#                                  to them, and how deep they go; its back edge; the ports panel's recess reaches `under`
LID = dict(x=0.0, y=94.5, r=84.6, base=TOP - 3.0, rim=TOP + 0.5, dome=1.0)    # its middle, its underside, its rim's top
CLAMP = dict(r=16.0, height=2.5)                                 # the disc clamp under its middle
WELL = dict(r=85.6, floor=TOP - 16.0, band=4.0)  # the well it shuts into; the well's floor; the dark band round its rim
MECHANISM = dict(depth=1.5, outline=[(-57.5, 17.5), (-57.5, 45.0), (-49.0, 62.0), (-33.0, 70.0), (-17.0, 67.0),
                                     (-9.7, 57.5), (2.0, 67.5), (21.4, 65.0), (33.0, 42.5), (33.0, 17.5),
                                     (21.4, -7.5), (-9.7, -25.0), (-37.0, -12.5)])   # about the spindle, sunk
SPINDLE = dict(r=11.5, top=TOP - 9.5, cap=3.6, cap_height=1.4)   # the turntable at the lid's middle; its centring cap
LENS = dict(at=(-16.6, 18.8), r=2.4, sled=(14.0, 30.0), reach=33.0)   # about the spindle; its sled's size, and its
#                                  middle's distance out from the spindle, on the line through the lens

# x, y, the cap's radius, its well's lip (how much wider than the cap the well is at the top) and the lip's drop.
BUTTONS = dict(power=(-100.0, 28.7, 18.0, 2.8, 2.0), reset=(-108.4, 68.8, 8.3, 1.7, 1.2),
               open=(100.0, 28.7, 18.0, 2.8, 2.0))
BUTTON = dict(gap=0.6, depth=6.0, edge=0.6, crown=0.3)    # round each cap; its edge below the top, its middle above
LED = dict(x=-100.0, width=2.8, length=6.2, depth=4.0)           # the power light's slot, back from the front edge
GROOVE = 0.7                                              # from the lid's well to OPEN's, on the line between them
DOTS = dict(r=(74.5, 80.0), angles=(-25.6, -29.3, -33.1, -36.9), size=1.1)   # the lid's grip, about its middle

PORTS = dict(x=(-33.5, 33.5), width=47.0, z=(8.0, 36.0), depth=3.0, corner=3.0, chamfer=1.0)   # the front openings
FINS = dict(y=(12.0, 176.0), pitch=4.2, width=2.2, out=2.5, z=(3.0, 50.0), cap=2.5)   # the vents, along each end
BASE = dict(height=3.0, front=0.6)    # the bottom shell's lip: it reaches the fins at the ends, `front` proud elsewhere

PARALLEL = dict(x=(67.0, 126.0), z=(6.0, 28.0), depth=5.0)       # in the right pod's back
AC_IN = dict(x=(-106.0, -83.0), z=(7.0, 21.0), depth=4.0)        # in the left pod's back
PANEL = dict(face=182.0, x=61.0, z=(4.0, PLATE["under"]))       # the ports panel, under the plate
JACKS = dict(z=15.0, r=4.2, length=6.0, at=dict(red=28.9, white=13.4, yellow=-7.2))   # AUDIO OUT R, L, VIDEO OUT

DISC = dict(r=60.0, hole=7.5, thickness=1.2)
SEAT = (LID["x"], LID["y"], SPINDLE["top"] + DISC["thickness"] / 2)      # on the turntable

COLOURS = dict(case="#A7A8AA", dark="#1E1F22")

REGIONS = dict(top=(0, 0, 1024, 713), front=(0, 720, 512, 106), back=(0, 832, 512, 106), port=(520, 720, 220, 131),
               label=(748, 720, 270, 270), data=(520, 857, 160, 160))
SWATCHES = dict(led=(16, 960), dark=(48, 960), lens=(80, 960), metal=(112, 960), red=(144, 960), white=(176, 960),
                yellow=(208, 960), black=(240, 960), sled=(272, 960))   # each a 24 x 24 block's middle

FPS = 30
LENGTH = 240                 # 8 s
