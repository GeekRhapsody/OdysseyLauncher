"""The Neo Geo AES's measurements, shared by neogeo_print.py (which draws its printing) and neogeo.py (which builds it).
Plain Python: Blender's Python imports it too.

The Neo Geo AES (1990), 325 x 237 x 60 mm, and its arcade stick, 280 x 190 mm (both as Wikipedia gives them), the stick in front of the console's left end.
Millimetres: x from the console's middle (left to right), y back from its front, z up from the table. The rest was
measured from Evan-Amos's photographs on Wikimedia Commons (the console from each corner and with its stick, the stick
from each corner, a cartridge), scaled by the console's width; the cartridge is scaled by the slot it fits.

The console is a wedge: a low front face (the POWER slider, the two controller ports, PHONES and VOLUME, the memory
card slot), the top sloping up to the tall back. On the top, a raised racetrack runs round the cartridge slot near the
back, three groups of vents behind it; RESET sits in a round dish at the front left; NEO-GEO's gold lettering on the
panel in front of the slot. The stick lies in front of the console's left end: a wedge too, the ball-topped lever in
its dish at the left, the four buttons on their arc at the right, SELECT and START behind them.

Two textures. `print` (ATLAS square, REGIONS): `top` (the console seen from above: the lettering, the panels' seams,
the dish, the vents' frame; planar-mapped onto every face facing up), `front` (its front face), and swatches. `pad`
(PAD_REGIONS): `stick` (the stick seen from above: SNK, the dish, the buttons' arc, PAD A to D, SELECT and START,
NEO-GEO), `label` (the cartridge's: a made-up game, Odyssey), and swatches. A region is (x, y, width, height) in
pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 325.0, 237.0, 60.0
FRONT_H = 22.0                                     # the front face's height
TOP_FRONT, TOP_BACK = (5.0, 26.0), (222.0, 56.0)   # the sloping top's front and back edges, (y, z)


def top_z(y):
    """The sloping top's height at y."""
    (y0, z0), (y1, z1) = TOP_FRONT, TOP_BACK
    return z0 + (z1 - z0) * (y - y0) / (y1 - y0)


def profile():
    """The side outline, (y, z), anticlockwise seen from the right end."""
    return [(2.0, 0.0), (DEPTH - 2.0, 0.0), (DEPTH, 2.0), (DEPTH, HEIGHT - 4.0), (DEPTH - 4.0, HEIGHT), TOP_BACK,
            TOP_FRONT, (1.5, FRONT_H + 2.5), (0.0, FRONT_H), (0.0, 2.0)]


# The racetrack: a stadium raised RISE over the top, its band BAND wide round a trough; the slot in the trough.
TRACK = dict(x=(-116.0, 116.0), y=(118.0, 196.0), rise=5.0, band=20.0, trough=3.0)
SLOT = dict(x=(-96.0, 96.0), y=(146.0, 180.0), depth=60.0)
VENTS = dict(groups=[(-104.0, -42.0), (-31.0, 31.0), (42.0, 104.0)], y=[203.0 + 4.6 * k for k in range(4)],
             width=2.2, depth=3.0)
RESET = dict(at=(-128.0, 52.0), dish=13.0, r=7.0, height=4.0)
POWER = dict(x=(-150.0, -132.0), z=(5.0, 15.0), out=2.0, travel=7.0)
PORTS = dict(x=(-95.0, 28.0), z=11.0, size=(26.0, 9.0), depth=6.0)
CARD_SLOT = dict(x=(70.0, 148.0), z=(4.0, 7.0), depth=40.0)

# The cartridge: w x thickness x h, its middle raised TAB over its shoulders; its label on its front; the ribs round its
# foot; how far it goes into the slot.
CART = dict(size=(186.0, 30.0, 150.0), tab=(100.0, 8.0), label=(92.0, 84.0), ribs=7, inserted=62.0)

# The stick: its plan w x d, a wedge from FRONT_HEIGHT to BACK_HEIGHT; at PAD_AT, turned PAD_TURN degrees.
PAD = dict(size=(280.0, 190.0), heights=(30.0, 46.0), r=16.0, at=(-140.0, -122.0), turn=10.0,
           dish=(-72.0, 30.0, 34.0), ball=13.0, shaft=(4.0, 34.0),        # the dish: x, y (from the middle), radius
           buttons=[(18.0, -12.0), (48.0, 2.0), (78.0, 10.0), (108.0, 12.0)], button_r=11.0,
           select=(20.0, 58.0), start=(56.0, 50.0), small=(14.0, 8.0))

COLOURS = dict(case="#1C1C1E", dark="#0B0B0C", button="#45464C", cart="#1E1E20", label="#B9BABD")

REGIONS = dict(top=(0, 0, 1024, 747), front=(0, 756, 1024, 70))
SWATCHES = dict(dark=(24, 856), button=(56, 856), gold=(88, 856), lit=(120, 856), case=(152, 856))
PAD_REGIONS = dict(stick=(0, 0, 1024, 695), label=(0, 704, 400, 316))
PAD_SWATCHES = dict(dark=(424, 728), button=(456, 728), ball=(488, 728))

FPS = 30
LENGTH = 240                 # 8 s
