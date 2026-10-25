"""The PlayStation 4's measurements, shared by ps4_print.py (which draws its printing) and ps4.py (which builds it).
Plain Python: Blender's Python imports it too.

The first PlayStation 4 (CUH-1000, 2013), 275 mm wide, 305 deep and 53 high (Sony's figures), and its DualShock 4, a
made-up game, Odyssey, on the disc. Millimetres: x from its middle (left to right), y back from the front's foot, z up
from the table. Its side is a parallelogram, the front set back at the top and the back overhanging the cables (as
Sony's designers described it); the rest was measured from Evan-Amos's photographs on Wikimedia Commons (from the front
left and right, the back left and right, and standing with its controller), scaled by its width; the DualShock 4 from
the layout drawing of it on Commons, scaled by its 162 mm.

The console: two decks, a deep slit between them all round; the upper deck in two parts, the glossy one on the left
(SONY on its front, the PlayStation mark at its back corner) and the matte one (PS4 on its front), the light bar in the
groove between them, the disc slot in the slit (under the glossy part and on under the matte one), the two USB ports
beside it; the back a grille of vents. The DualShock 4: its outline, the two stick housings below the touchpad, the
d-pad and the face buttons in their circles, SHARE, OPTIONS, the speaker, the PS button, the light bar along its top
edge.

One texture (ATLAS square, REGIONS): `top` (the console from above: x across, y down from the back), `front` and `back`
(the faces' printing, x across, z down from the top), `pad` (the DualShock 4 from above: x across, y down from its top
edge), `disc` (the disc's label), and swatches. A region is (x, y, width, height) in pixels."""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 275.0, 305.0, 53.0
SLANT = math.tan(math.radians(13.0))           # the front and back lean back by this much per mm of height
LOWER = 17.0                                    # the lower deck's top
SLIT = dict(z=(17.0, 22.0), depth=7.0)          # the slit between the decks and how far it's set in
GLOSS = 92.0                                    # the glossy part's width, from the left end
GROOVE = 3.0                                    # the groove between the parts, where the light bar shines
EDGE = 1.6                                      # the decks' edges' rounding

DISC_SLOT = dict(x=(-131.0, -7.0))              # in the slit, under the glossy part and on under the matte one
USB = dict(x=[4.0, 20.0], size=(13.0, 4.6))     # in the slit, right of the disc slot

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2, out=140.0)   # out: how far in front of its seat it waits

# The DualShock 4, from above (x across from its middle, y up from its grips' ends), traced from the layout drawing.
PAD_RIGHT = [(0.0, 36.5), (15.8, 35.8), (21.2, 32.8), (39.6, 32.1), (41.5, 26.9), (43.8, 20.3), (46.6, 12.1),
             (49.3, 6.9), (52.9, 3.2), (56.9, 1.0), (61.0, 0.0), (66.8, 0.3), (71.1, 1.8), (74.5, 4.0), (77.4, 6.9),
             (79.5, 10.6), (80.7, 14.3), (81.0, 17.3), (80.4, 24.7), (79.6, 32.1), (79.0, 37.3), (77.7, 45.4),
             (76.4, 52.8), (75.0, 59.5), (73.4, 66.2), (71.7, 72.8), (69.5, 80.2), (67.2, 85.4), (64.5, 89.8),
             (61.7, 94.3), (58.4, 96.5), (0.0, 96.5)]
PAD = dict(at=(82.0, -128.0), turn=-12.0, height=24.0)          # in front of the matte part, clear of the disc
DPAD = dict(at=(-50.4, 72.1), ring=18.8, span=29.0, arm=8.6, height=2.2)
FACE = dict(triangle=(51.0, 84.2), circle=(63.0, 72.4), cross=(51.0, 60.6), square=(39.0, 72.4), ring=18.8, r=5.0,
            height=2.6, press=1.6)
TOUCHPAD = dict(x=(-26.7, 27.2), y=(66.7, 95.7), r=3.0, height=1.0)
STICKS = dict(left=(-26.1, 50.3), right=(26.1, 50.3), housing=15.7, cap=9.5, height=(8.0, 13.0), tilt=18.0)
SMALL = dict(share=(-33.0, 88.0), options=(33.3, 88.0), size=(5.0, 9.0), ps=(0.0, 49.2), ps_r=4.0, speaker=(0.0, 58.6))
LIGHT_BAR = dict(x=(-28.0, 28.0), z=(9.0, 17.0))  # along its top edge, facing away from the player

COLOURS = dict(gloss="#09090B", matte="#1B1C1F", pad="#141518", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 440, 488), front=(448, 0, 576, 111), back=(448, 119, 576, 111), pad=(448, 238, 486, 300),
               disc=(0, 496, 256, 256))
SWATCHES = dict(gloss=(296, 520), matte=(328, 520), pad=(360, 520), slit=(392, 520), dark=(424, 520), blue=(296, 552),
                white=(328, 552), grey=(360, 552), green=(392, 552), red=(424, 552), pink=(456, 552), sky=(488, 552))

FPS = 30
LENGTH = 240                 # 8 s
