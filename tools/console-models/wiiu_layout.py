"""The Wii U set's measurements, shared by wiiu_print.py (which draws its printing and screens) and wiiu.py (which builds
it). Plain Python: Blender's Python imports it too.

The Wii U (2012) in black, lying down, 172 x 46 x 269 mm (Wikipedia's figures), and its GamePad, 255.4 x 133.4 x 41 mm
(Nintendo's, as Game Watch printed them), its 6.2-inch screen 16:9, standing in its cradle in front of it, the Wii U
Menu on its screen. Millimetres: x across (left to right), y back from the GamePad's foot, z up from the table. The rest
was measured from photographs on Wikimedia Commons (Evan-Amos's views of the console from the front left and the back
right, the console and the GamePad together, the GamePad from in front), scaled by the figures above.

The console: its section a rounded rectangle (CONSOLE["corner"]) extruded from its front to its back, its front face
(the disc slot across it, EJECT and POWER at its left with the power light, SYNC, the SD card's flap, Wii U), the
matte panel along its top, the grilles in its right side. The GamePad, in its own frame (u across, v up from its
middle, the face at w = 0 facing the player): its outline a rounded rectangle, its screen in a black bezel, the sticks
at its top corners, the d-pad and ABXY under them, + and -, HOME, TV CONTROL and POWER along its foot, the sensor bar
over the screen. The cradle: a low black stand holding it at LEAN degrees back from upright.

One texture (ATLAS square, REGIONS): `pad` (the GamePad's face: its black, the bezel, the sensor bar, the names and
Wii U), the GamePad's screens (`menu`, the Wii U Menu at rest; `menu_disc`, its first tile the disc's, a made-up game,
Odyssey; `title` and `game`, Odyssey's title and a moment of its play), `front` (the console's front face), `disc` (the
disc's label), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

# -- The console -----------------------------------------------------------------------------------------------------

CONSOLE = dict(size=(172.0, 269.0, 46.0), at=(40.0, 40.0), corner=15.0)   # w x d x h; its front's left corner (x, y):
                                                                           # behind the GamePad's back
CAP = 26.0                                       # the glossy caps' depth at the front and back; the matte panel between
SLOT = dict(x=(34.0, 160.0), z=(28.0, 31.0))     # on the front, x from its left edge, z up from its foot
FRONT_BUTTONS = dict(eject=(13.0, 30.5), power=(13.0, 13.0), r=5.6)     # x, z of each; their radius
POWER_LIGHT = (13.0, 22.0)
SYNC = (36.0, 12.0)
FLAP = dict(x=(48.0, 150.0), z=(5.0, 21.0))
GRILLES = [dict(y=(108.0, 150.0), z=(14.0, 32.0)), dict(y=(162.0, 222.0), z=(14.0, 32.0))]  # in its right side
GRILLE_GRID = (4, 3)                              # slots along, rows up

# -- The GamePad ---------------------------------------------------------------------------------------------------

PAD = dict(size=(255.4, 133.4), thickness=24.0, corner=40.0, at=(-62.0, 0.0, 15.0), lean=16.0)   # its foot's middle
SCREEN = dict(size=(137.3, 77.2), at=(0.0, 3.0), bezel=(149.0, 87.0))     # its middle, (u, v)
STICKS = dict(left=(-108.0, 41.0), right=(104.0, 41.0), r=9.0, well=12.5, height=9.0)
DPAD = dict(at=(-97.0, 11.0), size=24.0, arm=8.0, height=3.5)
ABXY = dict(at=(96.0, 11.0), spacing=11.0, r=4.6, height=3.5)            # A right, B down, X up, Y left
SMALL = dict(start=(85.0, -16.0), select=(85.0, -29.0), home=(-2.0, -53.0), tv=(54.0, -53.0), power=(67.0, -53.0),
             r=3.4, home_r=5.6, height=2.2)
SENSOR = dict(u=(-36.0, 36.0), v=60.0, height=7.6)

CRADLE = dict(size=(150.0, 62.0), base=8.0, back=(40.0, 10.0), lip=(16.0, 8.0))   # w x d; its base's height; the rest
                                                                                  # behind, the lip in front: h x d

# -- The disc ------------------------------------------------------------------------------------------------------

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2)

COLOURS = dict(case="#141416", glass="#FFFFFF", key="#1C1C1F", cradle="#0E0E10")

SCREEN_PX = (320, 180)
REGIONS = dict(pad=(0, 0, 1024, 535), menu=(0, 543) + SCREEN_PX, menu_disc=(328, 543) + SCREEN_PX,
               title=(656, 543) + SCREEN_PX, game=(0, 731) + SCREEN_PX, front=(328, 731, 344, 92),
               disc=(680, 731, 200, 200))
SWATCHES = dict(dark=(344, 852), blue=(376, 852), red=(408, 852), matte=(440, 852), silver=(472, 852), white=(504, 852))

FPS = 30
LENGTH = 240                 # 8 s
