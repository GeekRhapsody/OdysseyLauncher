"""The Sega 32X's measurements, shared by sega32x_print.py (which draws its printing) and sega32x.py (which builds it).
Plain Python: Blender's Python imports it too.

The Mega Drive 32X (1994, the European one), 210 x 110 mm and 100 mm high with its plug (Wikipedia's figures), on the
first Mega Drive (mega_drive.py's), and a 32X cartridge with a made-up game, Odyssey. Millimetres: x from its middle
(left to right), y back from its middle (front -55, back 55), z up from the cap's underside (the neck and the plug below
it). The rest was measured from Evan-Amos's photographs on Wikimedia Commons (from the front left, the back, below and
opened) and photographs of European ones on a Mega Drive (Commons), scaled by its width.

The cap: a rounded box, its back nearly upright, its top flat behind and sloping down at the front; the slope's glossy
shell ends in a wave (low in the middle, rising to the ends) over the matte lip that bulges out at the bottom of the
front. On the top: the island, a raised stadium round the cartridge slot's recess, the slot's two dust flaps meeting in
the middle; the badge on the slope in front (MEGA DRIVE, 32X, the SEGA tab); vents on the top's corners at the ends.
Under the cap: the neck (a stadium) and the plug that goes into the Mega Drive's slot. The cartridge (the 32X's own
shell, as in every region; only the labels differ) faces the front, its label the European ones' layout.

One texture (ATLAS square, REGIONS): `badge` (the slope, seen along its normal: across BADGE_AREA's u, up its v),
`vents` (the ends, seen along x: y across, z up), `flap` (the flaps' tops), `label` (the cartridge's), and swatches. A
region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH = 210.0, 110.0
TOP = 56.0                       # the top at the middle; it falls TOP_FALL towards the ends
TOP_FALL = 3.0
ROUND = dict(plan=28.0, top=22.0, bottom=8.0)        # the corners: in the plan, the ends' top and bottom edges
BACK = dict(wall=16.0, round=16.0, foot=4.0)         # the back's upright wall ends `wall` below the top
SLOPE = -11.0                    # where the top starts falling to the front
CREASE = dict(y=-44.0, mid=22.0, ends=46.0, flat=20.0, rise=100.0)   # the wave between the slope and the lip:
                                                     # level to |x| = flat, rising to `ends` at |x| = rise
LIP = dict(z=11.0, under=-48.0, step=4.0)   # the lip's most forward point (at the front), where it meets the
                                             # underside, how far its rolled top stands out of the groove

ISLAND = dict(at=(0.0, 12.0), size=(172.0, 54.0), height=6.0)      # its top TOP + height
RECESS = dict(size=(152.0, 36.0), depth=7.0)
SLOT = dict(size=(136.0, 23.0), floor=30.0)          # the opening through the recess's floor, down to the floor
FLAP = dict(length=132.0, width=11.0, thickness=1.6, droop=12.0, open=82.0)   # each flap, hinged at the opening's edge

# The badge, on the slope: its centre (x, height up the slope from the crease at the middle), its size, the outline's
# points (from its middle: the tips, the bottom's ends) and the SEGA tab's top corners.
BADGE = dict(at=(0.0, 21.0), size=(90.0, 36.0), tip=14.4, bottom=17.1, tab=(14.1, 11.6))
BADGE_AREA = dict(u=(-64.0, 64.0), v=(-6.0, 45.0))   # the badge region's extent on the slope
VENTS = dict(y=(-17.0, 17.0), count=7, z=(30.0, 52.0), x=88.0)   # the slits' span, from |x| on the ends

NECK = dict(size=(136.0, 64.0), height=15.0)
PLUG = dict(size=(100.0, 16.0), height=22.0, windows=[-19.0, 19.0], window=(24.0, 8.0))

# The cartridge: its front (x across, z up from its connector edge), its thickness, the label on its front.
CART = dict(width=113.0, height=75.0, thickness=18.0, corner=6.0, label=(80.0, 46.0), label_z=22.0, seat=22.0,
            above=52.0)          # it goes `seat` below the island's top; it appears `above` its seat

# Where it stands on the Mega Drive (mega_drive.py's coordinates): its plug over the slot, the plug's bottom in it.
ON_MEGA_DRIVE = dict(slot=(34.0, 37.0), plug_bottom=41.0)

COLOURS = dict(case="#1C1D20", shell="#111214", recess="#141517", slot="#08080A", flap="#202124", silver="#C9CDD3",
               cart="#18181A", print="#FFFFFF")     # black, as the Mega Drive under it

REGIONS = dict(badge=(0, 0, 640, 255), vents=(648, 0, 376, 235), label=(0, 264, 640, 368), flap=(0, 640, 1024, 82))
SWATCHES = dict(case=(680, 280), shell=(712, 280), recess=(744, 280), slot=(776, 280), flap=(808, 280),
                silver=(840, 280), cart=(872, 280))

FPS = 30
LENGTH = 240                 # 8 s
