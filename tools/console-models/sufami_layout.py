"""The SuFami Turbo card's measurements, shared by sufami_print.py (which draws the adapter's front and the mini
cartridges' labels) and sufami.py (which builds it). Plain Python: Blender's Python imports it too.

Bandai's SuFami Turbo (1996) standing in a Super Famicom's slot (snes.py's console, its `sfc` kind), two of its mini
cartridges (made-up games) going into its top. The adapter's plug is a Super Famicom cartridge's (135 mm wide, 20
thick); above the slot it widens into its body, its sides leaning out, the recessed band across its front carrying SUFAMI
TURBO and its emblem, two cradles in its top, A on the left and B on the right, each holding a mini cartridge upright,
the top dipping between them.
No published size was found; it is about 160 x 40 x 110 mm, its mini cartridges 63 x 70 x 11, about 55 per cent of each
showing over its cradle, measured from photographs (one of it on its own from the front, others in a Super Famicom and
with its cartridges round it), scaled by its plug's width. Millimetres: the adapter's own frame is x across from its middle, z up from its plug's
edge, y back from its middle; a mini cartridge's the same.

One texture (ATLAS square, REGIONS): `front` (the body's front: x across, z down from its top), `a` and `b` (the mini
cartridges' labels), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

PLUG = dict(width=135.0, thickness=20.0, height=50.0, inserted=46.0)      # the part in the Super Famicom's slot
BODY = dict(bottom=(144.0, 36.0), top=(160.0, 44.0), height=56.0, corner=5.0)   # over it: w x d at its foot and top
BAND = dict(x=62.0, z=(9.0, 29.0), depth=1.4)                             # the recessed band: half its width, from
                                                                          # the body's foot (z up)
CRADLES = dict(x=(-38.5, 38.5), width=66.0, depth=14.0, floor=36.0)      # the two cradles: their middles, how deep
DIP = (10.0, 7.0)                                                         # the top's dip between them: width, depth
MINI = dict(width=63.0, height=70.0, thickness=11.0, label=(54.0, 40.0, 7.0), grip=4.0, seat=31.5, above=60.0)
#  a mini cartridge: its label (width, height, from its top); the grip's ribs across its top; how far it goes into its
#  cradle; how far over it it appears

REGIONS = dict(front=(0, 0, 640, 196), a=(0, 208, 300, 244), b=(320, 208, 300, 244))
SWATCHES = dict(body=(680, 40), dark=(712, 40), mini=(744, 40), grip=(776, 40))
COLOURS = dict(body="#8F8D8A", band="#4E4D50", mini="#D9D6CE")

FPS = 30
LENGTH = 240                 # 8 s
