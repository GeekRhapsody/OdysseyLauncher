"""The Super Game Boy card's measurements, shared by sgb_print.py (which draws the adapter's front and the Game Boy
cartridge's label) and sgb.py (which builds it). Plain Python: Blender's Python imports it too.

The Super Game Boy (1994) in the European Super Nintendo's slot, a Game Boy cartridge (a made-up game, Odyssey) going
into its top: the console is snes.py's own. The adapter is 134 mm wide and 118 high (the 5.28 x 4.65 inches a listing
gives) and 20 thick, like a Super Nintendo cartridge; the rest was measured from photographs of a European one and of
Evan-Amos's of the American one on Wikimedia Commons, scaled by its width. Millimetres: the adapter's own frame is x
across from its middle, z up from its connector's edge, y back from its middle; the Game Boy cartridge's the same.

The adapter: its outline (the top corners rounded, the notch in the middle of its top where the Game Boy cartridge goes
in, the slot below it), its front printed: the Nintendo emblem under the notch, the label (Super GAME BOY, the SUPER NES
mark), the grip below, the side ridges.

One texture (ATLAS square, REGIONS): `front` (the adapter's front: x across, z down from its top), `gb` (the Game Boy
cartridge's front, its label), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

SGB = dict(width=134.0, height=118.0, thickness=20.0, corner=8.0, inserted=42.0)
NOTCH = dict(width=66.0, depth=22.0, r=6.0)          # the notch in its top
SLOT = dict(width=59.0, thickness=9.4, depth=36.0, y=-1.5)   # the Game Boy cartridge's slot below the notch's floor
EMBLEM = dict(z=88.0, size=(30.0, 7.0))              # the Nintendo emblem, z of its middle
LABEL = dict(z=(48.0, 78.0), width=96.0)             # the label's band
GRIP = dict(z=(8.0, 40.0), width=72.0)               # the grip's panel below

GB = dict(width=57.0, height=65.0, thickness=8.0, cut=4.5, seat=30.0, above=72.0)   # seat: how far below the
                                                     # notch's floor its bottom goes; above: how far over it it appears

REGIONS = dict(front=(0, 0, 536, 472), gb=(544, 0, 228, 260))
SWATCHES = dict(sgb=(800, 40), gb=(832, 40), dark=(864, 40))
COLOURS = dict(sgb="#BDBDC1", gb="#9A9AA0")

FPS = 30
LENGTH = 240                 # 8 s
