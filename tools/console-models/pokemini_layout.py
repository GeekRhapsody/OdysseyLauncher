"""The Pokémon mini's measurements, shared by pokemini_print.py (which draws its printing and screens) and pokemini.py
(which builds it). Plain Python: Blender's Python imports it too.

The Pokémon mini (2001) in Wooper Blue, 58 mm wide, 74 high and 23 thick (Wikipedia's figures), a made-up game, Odyssey,
in it. Millimetres: x from its middle (left to right), y back from its face, z up from its foot. Its outline was traced
from a photograph of a Wooper Blue one on Wikimedia Commons, cut out (round from its right side, anticlockwise), and the
face measured from it, scaled by its width; the controls' places from the drawing of them in a game's manual (Pokémon
Pinball mini's) (C along the right side, POWER between the D-pad and B, RESET under it) and the cartridge's place from
the Pokémon mini developers' notes (it slots in at the top of the back).

The body: its outline, the front half clear (frosted, its insides showing faintly), the back half solid blue; on the
face the black oval with the Nintendo badge over the LCD and Pokémon mini under it, the D-pad in its well, POWER in its
ring, A and B; C along the right side; the cartridge in the slot at the top of the back.

One texture (ATLAS square, REGIONS): `face` (the front half's face), `oval`, the LCD five ways (`clock`, the rest; then
`title`, `game_1`, `game_2` and `hit`, drawn as the LCD's 96 x 64 pixels), the cartridge's label (`cart`), the D-pad's
top (`dpad`), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 58.0, 74.0, 23.0
SPLIT = 10.0                     # the clear front half's thickness

# Traced every 10 degrees round the middle, from its right side anticlockwise: (x, z).
OUTLINE = [(29.0, 36.6), (28.5, 41.5), (28.1, 46.5), (27.4, 52.0), (26.6, 58.3), (25.4, 66.0), (20.5, 71.3),
           (13.4, 73.4), (6.2, 73.8), (-0.8, 74.0), (-7.8, 73.8), (-15.0, 73.5), (-21.9, 71.0), (-26.2, 65.1),
           (-27.6, 57.8), (-28.5, 51.7), (-29.1, 46.3), (-29.4, 41.4), (-29.5, 36.6), (-29.5, 31.8), (-29.1, 26.8),
           (-28.9, 21.3), (-27.2, 15.8), (-23.3, 11.4), (-17.5, 9.3), (-11.8, 8.2), (-6.2, 7.6), (-0.8, 6.7),
           (5.1, 5.1), (12.6, 1.9), (21.3, 0.6), (27.6, 4.7), (28.8, 13.2), (29.5, 20.2), (29.6, 26.2), (29.3, 31.6)]
EDGE = 2.4                       # the edges' rounding

# The face, (x, z).
OVAL = dict(at=(-5.4, 48.4), r=(20.0, 16.3), raised=0.5)
LCD = dict(at=(-4.85, 48.35), size=(26.7, 19.7))
BADGE = dict(at=(-4.7, 61.4), size=(10.8, 2.9))
NAME = dict(at=(-5.0, 36.3), width=18.5)
DPAD = dict(at=(-18.2, 24.0), size=13.4, arm=4.6, height=2.2, well=8.4)
POWER = dict(at=(-5.05, 24.0), r=1.6, ring=3.3, height=1.0)
RESET = dict(at=(-5.05, 14.6), r=0.6)
BUTTONS = dict(b=(3.5, 19.65), a=(12.6, 25.8), r=3.4, height=2.0)
C = dict(z=(50.0, 70.0), width=2.8, out=1.2)          # along the right side, its middle in the depth
SLOT = dict(x=(-16.0, 16.0), y=(13.5, 19.5), depth=24.0)   # the cartridge slot in the back half's top

CART = dict(size=(31.0, 28.0, 5.0), out=5.0, label=(26.0, 19.0))   # w, h, t; how far it stands out of the top

COLOURS = dict(case="#2F74C0", key="#2F74C0", grey="#9C9EA4", clear="#B9CADB", glass="#FFFFFF", print="#FFFFFF",
               lcd="#A9B5A3", ink="#26302A", shade="#6E7A6C")

SCREEN_PX = (216, 160)
REGIONS = dict(face=(0, 0, 400, 494), oval=(408, 0, 400, 326), clock=(0, 520) + SCREEN_PX, title=(216, 520) + SCREEN_PX,
               game_1=(432, 520) + SCREEN_PX, game_2=(648, 520) + SCREEN_PX, hit=(0, 688) + SCREEN_PX,
               cart=(224, 688, 208, 152), dpad=(440, 688, 120, 120))
SWATCHES = dict(clear=(840, 360), case=(872, 360), dark=(904, 360), grey=(936, 360), cart=(968, 360))

FPS = 30
LENGTH = 240                 # 8 s
