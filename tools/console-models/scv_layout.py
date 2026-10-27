"""The Super Cassette Vision card's measurements, shared by scv_print.py (which draws its printing) and scv.py (which
builds it). Plain Python: Blender's Python imports it too.

Epoch's Super Cassette Vision (1984) and its two controllers. No published size was found; it is about 305 x 212 x 47
mm, scaled from its back panel's 8-pin DIN socket and phono jack, the rest measured from Evan-Amos's photographs on
Wikimedia Commons (the console from the front, above, the side, behind and with its flap open, and its controllers).
Millimetres: x from the console's middle (left to right), y back from its front, z up from the table.

The console: a low light grey wedge, the upper shell over the narrower base, the seam round its sides; the top flat over
its back two thirds, the smoked flap over the front third sloping down to the front lip, hinged along its back edge, the
compartment under it holding the two controllers lying in their beds. Across the top's middle the printed black panel,
the green stripe along its back edge (EPOCH TV GAME SYSTEM, SELECT): the logo, the cassette slot in its white frame (two
dust flaps meeting in its middle), POWER's slide, RESET and PAUSE, the 12-key SELECT pad; behind it the vents. A
cartridge (a made-up game) stands in the slot. Each controller is an upright light grey box, an orange cap at each top
corner (its two buttons), the stick in its round boss, the label band across it (1P brown, 2P blue).

One texture (ATLAS square, REGIONS): `top` (the console from above, planar-mapped onto every face facing up), `pad1` and
`pad2` (the controllers' faces), `cart` (the cartridge's label), and swatches. A region is (x, y, width, height) in
pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 305.0, 212.0, 47.0
HINGE = (84.0, HEIGHT)                       # the flap's back edge, its hinge (y, z)
LIP = (6.0, 21.0)                            # the flap's front edge rests over the lip (y, z)
PROFILE = [(4.0, 0.0), (DEPTH - 4.0, 0.0), (DEPTH, 5.0), (DEPTH, HEIGHT - 3.0), (DEPTH - 3.0, HEIGHT), HINGE,
           (LIP[0] + 2.0, LIP[1] - 1.0), (0.0, LIP[1] - 4.0), (0.0, 5.0)]
BASE_INSET = 3.0                              # the base is set in under the upper shell, below the seam
SEAM = 14.0
COMPARTMENT = dict(x=(-142.0, 142.0), y=(8.0, 82.0), floor=1.0)
FLAP = dict(x=(-149.0, 149.0), thickness=2.4, open=96.0)          # degrees it swings up and back

PANEL = dict(y=(86.0, 158.0), stripe=6.0)                          # the black panel; its green stripe at the back
SLOT = dict(x=(-128.0, -44.0), y=(94.0, 132.0), frame=4.0, depth=40.0)
SWITCH = dict(x=(14.0, 34.0), y=(138.0, 146.0), travel=9.0)        # POWER's slide: OFF at the left
RESET = dict(x=(14.0, 34.0), y=(118.0, 126.0), height=1.6)
PAUSE = dict(x=(14.0, 34.0), y=(100.0, 108.0), height=1.6)
KEYPAD = dict(x=(70.0, 128.0), y=(92.0, 150.0), cols=3, rows=4, key=(11.0, 8.0), height=1.4)
LEGENDS = [["7", "8", "9"], ["4", "5", "6"], ["1", "2", "3"], ["0", "CL", "EN"]]

CART = dict(size=(76.0, 18.0, 66.0), inserted=30.0, above=58.0)  # width, thickness, height; how deep it goes in

# A controller lying on its back in its bed across the compartment, its top end (the caps') towards the middle, its
# stick at the outer end (as they lie under the flap): its length (top end to foot), width, thickness (as flat as the
# flap's slope lets them be); the stick's boss, from its top end; the caps at its top corners; its middle (x, y).
PAD = dict(size=(95.0, 62.0, 18.0), boss=dict(v=60.0, r=13.0, height=2.0), stick=(3.6, 6.0), knob=5.5,
           caps=dict(v=16.0, width=20.0), at=[(-70.0, 51.0), (70.0, 51.0)])

COLOURS = dict(case="#D1D1CF", side="#C6C6C4", panel="#101211", green="#6EA843", smoked="#2A2B2D", frame="#E2E2E0",
               dark="#4A4B48", key="#5E5E5C", pad="#DADADA", orange="#D87936", stick="#474948", cord="#C8C8C6")

REGIONS = dict(top=(0, 0, 1024, 712), pad1=(0, 720, 240, 304), pad2=(248, 720, 240, 304), cart=(496, 720, 232, 202))
SWATCHES = {name: (760 + 32 * (k % 8), 744 + 32 * (k // 8)) for k, name in enumerate(
    ("case", "side", "smoked", "frame", "dark", "key", "pad", "orange", "stick", "cord", "black", "cart"))}

FPS = 30
LENGTH = 240                 # 8 s
