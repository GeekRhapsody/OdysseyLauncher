"""The Intellivision's measurements, shared by intellivision_print.py (which draws its printing) and intellivision.py
(which builds it). Plain Python: Blender's Python imports it too.

Mattel's Intellivision (1979), the Master Component, 394 mm wide, 229 deep and 70 high (the 15.5 x 9 x 2.75 inches a
Georgia Tech archive records; a 40 x 24 x 7 cm listing agrees), its two controllers docked in its top, a made-up game,
Odyssey, on the cartridge. Millimetres: x from its middle (left to right), y back from its front, z up from the table.
The rest was measured from Evan-Amos's photographs on Wikimedia Commons (the console from the front left and right and
the back left and right, the set, a controller from above at an angle), scaled by its width.

The console: the dark brown body, the wood-grain front; on its top the gold strips (the back one; the front one with
MATTEL ELECTRONICS INTELLIVISION Intelligent Television, RESET and the OFF-ON switch), the middle band between them,
sunk in, where the controllers dock (the left one's disc at the left end, the right one's at the right, their keypads
inwards) either side of the vents; the cartridge slot in its right end. A controller: its body, the keypad of twelve
keys (1 to 9, clear, 0, enter) in its gold frame, the gold disc, the side buttons.

One texture (ATLAS square, REGIONS): `top` (the console from above: x across, y down from the back), `front` (its
front: x across, z down from the top), `pad` (a controller from above: x along it from its keypad's end, y across),
`cart` (the cartridge's label), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 394.0, 229.0, 64.0       # the body; its feet make up the 70
FEET = 6.0
# The side profile, (y, z above the feet), round from the front's foot: the front leaning out to the top's edge.
PROFILE = [(10.0, 0.0), (219.0, 0.0), (229.0, 8.0), (229.0, 52.0), (222.0, 58.0), (8.0, 58.0), (0.0, 50.0),
           (2.0, 14.0)]
TOP = 58.0
STRIPS = dict(front=(14.0, 76.0), back=(156.0, 212.0))   # the gold strips' y spans
BAND = dict(y=(82.0, 150.0), depth=5.0)                 # the docks' band, sunk in
VENTS = dict(x=(-34.0, 34.0))
SLOT = dict(y=(70.0, 160.0), z=(16.0, 30.0))             # the cartridge slot in the right end (z above the feet)
SWITCH = dict(at=(124.0, 34.0), size=(26.0, 9.0), travel=12.0)   # the OFF-ON switch on the front strip (x, y)
RESET = dict(at=(96.0, 52.0), size=(30.0, 7.0))

# A controller: its size, and its parts along it from its keypad's end (u) and across it (v, from its middle).
PAD = dict(length=152.0, width=62.0, thickness=18.0, dock=(-110.0, 112.0))   # docked: the left one's middle (x, y)
KEYPAD = dict(u=(12.0, 82.0), v=(-24.0, 24.0), keys=(3, 4), key=13.0)
DISC = dict(u=118.0, r=19.0, height=2.4, tilt=8.0)
SIDE = dict(u=(30.0, 60.0), size=(14.0, 3.0))

CART = dict(size=(64.0, 116.0, 13.0), out=80.0, label=(54.0, 70.0))   # w, length, t; how far out it waits

COLOURS = dict(body="#3B2D25", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 788, 458), front=(0, 466, 788, 128), pad=(0, 602, 608, 248), cart=(616, 602, 216, 280))
SWATCHES = dict(body=(820, 40), gold=(852, 40), wood=(884, 40), dark=(916, 40), key=(948, 40), metal=(980, 40),
                cart=(820, 72), slot=(852, 72))

FPS = 30
LENGTH = 240                 # 8 s
