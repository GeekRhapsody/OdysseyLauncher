"""The NES card's measurements, shared by nes_print.py (which draws its printing) and nes.py (which builds it). Plain
Python: Blender's Python imports it too.

The Nintendo Entertainment System (1985), the front-loading NES-001, 256 mm wide, 203 deep and 90 high (the museums' 255
to 257 by 200 to 203 by 90 to 95), its controller (123.4 x 53.2 x 17.5: iFixit's figures) in front of it at its left, a
cartridge (120 x 133 x 17) with a made-up game, Odyssey, going in through its door. Millimetres: x from its middle (left
to right), y back from its front, z up from the table. Measured from Evan-Amos's photographs on Wikimedia Commons (from
the front left and right, the back right, the set with its controller; the controller from both sides and its dog-bone
cousin flat on; a cartridge).

The console: the light grey upper body over the darker base, its sides sloping in to the foot (BASE); in the upper
body's front, the door (DOOR, hinged along its top, flipping up and out till it stands over the top, its face up) over
the cartridge's chamber (CHAMBER); under it, on the base's front, POWER and RESET and the red light (BUTTONS, LIGHT);
the band (BAND) across the top from the front to the back, black at its ends and ribbed between (RIBS), down the front
round the two ports (PORTS). The controller (PAD): a grey slab, its black face with the cross, SELECT and START in their
grey stripes, B and A in red.

One texture (ATLAS square, REGIONS): `top` (the console from above: the band's black ends, the ribs' shadows, the upper
body's edges), `front` (its front: Nintendo ENTERTAINMENT SYSTEM on the door, POWER and RESET, the band, 1 and 2), `pad`
(the controller from above: its face, SELECT and START, B and A, Nintendo), `cart` (the cartridge's top: its ribs and
its label), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 256.0, 203.0, 90.0
BASE = dict(top=32.0, slope=8.0, back=8.0)        # the base's top; how far its sides slope in at the foot; at the back
DOOR = dict(x=(-96.0, 36.0), z=(38.0, 80.0), gap=1.2, open=-105.0)   # how far it flips up (degrees)
CHAMBER = dict(depth=150.0)                        # how far back the chamber runs behind the door
BUTTONS = dict(power=(-86.0, 17.0), reset=(-58.0, 17.0), size=(24.0, 10.0, 3.0))   # middles (x, z); w, h, out
LIGHT = dict(at=(-104.0, 19.0), size=4.0)
BAND = dict(x=(41.0, 79.0), front=30.0, back=26.0)  # across the top: black for front and back from its ends
RIBS = dict(y=(36.0, 172.0), count=16, width=3.0, height=1.2)
PORTS = dict(x=[50.0, 70.0], z=(7.0, 27.0), width=13.0, depth=12.0)

# The cartridge: w, length, t; where its front end's middle sits when it is in; how far it slides; how far it presses
# down.
CART = dict(size=(120.0, 133.0, 17.0), seat=(-30.0, 8.0, 46.0), out=150.0, down=12.0)

# The controller: w, d, h; its face's inset; the cross (middle, arm's length and width); SELECT and START (middles,
# size); B and A (middles, radius); where it lies (x, y) and its turn.
PAD = dict(size=(123.4, 53.2, 17.5), face=4.0, cross=((-41.0, -3.0), 11.0, 7.4), pills=[(-8.0, -6.0), (9.0, -6.0)],
           pill=(9.0, 3.8), ba=[(30.0, -6.0), (45.0, -6.0)], ba_r=5.2, at=(-120.0, -90.0, 6.0))

COLOURS = dict(case="#CFCDCA", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 608, 482), front=(0, 490, 608, 214), pad=(616, 0, 300, 130), cart=(616, 138, 240, 266))
SWATCHES = dict(case=(640, 440), base=(672, 440), black=(704, 440), dark=(736, 440), red=(768, 440), lit=(800, 440),
                off=(832, 440), cart=(864, 440), grey=(640, 472), rubber=(672, 472))

FPS = 30
LENGTH = 240                 # 8 s
