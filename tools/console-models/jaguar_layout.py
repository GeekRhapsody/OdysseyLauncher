"""The Atari Jaguar set's measurements, shared by jaguar_print.py (which draws its printing) and jaguar.py (which builds
it). Plain Python: Blender's Python imports it too.

Two cards, one per system: `atarijaguar` (the Jaguar, 1993, and its controller) and `atarijaguarcd` (the same with the
Jaguar CD on it, 1995). The Jaguar is 241 x 254 mm (the Computer History Museum's 9 1/2 x 10 inches), about 64 mm high
at its fins (an Atari FAQ's 2 1/2 inches). Millimetres: x from its middle (left to right), y back from its front face
(the nose's), z up from the table. The rest was measured from Evan-Amos's photographs on Wikimedia Commons (the Jaguar
with its controller, from the back right; the controller from above; the Jaguar CD on the Jaguar, alone, and open),
scaled by the Jaguar's width.

The Jaguar: a low, pillowed body; the round nose at its front (the red power button on it, 64-BIT INTERACTIVE
MULTIMEDIA SYSTEM and Atari's logo round it); the shallow dish in the middle of its top; the cartridge slot's raised
frame at the back between the two ribbed wings; JAGUAR in red script at the top left. The controller: its wide outline
(PAD_OUTLINE, traced from the photograph from above), the D-pad in its ring at the top left, PAUSE and OPTION, the red A,
B and C on a diagonal, the twelve keys of the keypad on the plate below, the ridges by the cable. The Jaguar CD: its
plan a rounded stadium, the lid (the clear crescent window, JAGUAR CD) hinged at its back, COMPACT DIGITAL MEDIA PLAYER,
its own cartridge slot raised at its back.

One texture per card (ATLAS square, REGIONS): `top` (the Jaguar from above: JAGUAR, the dish's rim, the nose's
printing, the slot's frame), `pad` (the controller from above), `cd` (the Jaguar CD from above: the lid, its window and
logo, CLOSE HERE, its printing), `disc` (the CD's label: a made-up game, Odyssey), `label` (the cartridge's), and
swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH = 241.0, 254.0
BODY = dict(y=(22.0, DEPTH), corner=24.0, rings=[(0.0, 0.0), (0.0, 20.0), (7.0, 36.0), (26.0, 45.0)])  # (inset, z)
NOSE = dict(x=78.0, y=(0.0, 58.0), height=38.0, top=31.0)      # a half-ellipse: its half-width, its span, heights
POWER = dict(at=(0.0, 22.0), size=(22.0, 11.0), height=2.5)
DISH = dict(at=(10.0, 112.0), r=64.0, depth=2.0)
FRAME = dict(x=(-78.0, 78.0), y=(176.0, 246.0), top=52.0)        # the slot's raised frame
SLOT = dict(x=(-58.0, 58.0), y=(196.0, 226.0), depth=40.0)
WINGS = dict(x=(84.0, 120.0), y=(165.0, 250.0), top=(50.0, 30.0), ribs=7, rib=(3.0, 4.0))   # inner, outer top z
LOGO = dict(at=(-66.0, 62.0), size=(60.0, 16.0))

# The cartridge: w x thickness x h, standing in the slot (its bottom seat_depth below the frame's top), its label on
# its front.
CART = dict(size=(110.0, 26.0, 86.0), label=(90.0, 46.0), seat_depth=34.0)

# The controller, in its own plan (x across, y back from its front edge, its middle at the origin).
PAD_OUTLINE = [(0.0, 0.0), (71.8, 0.4), (77.3, 12.9), (81.2, 28.8), (82.5, 58.4), (75.2, 90.7), (69.6, 100.5),
               (61.4, 109.1), (51.6, 115.2), (35.2, 119.0), (28.4, 122.9), (0.0, 124.6), (-28.8, 122.9),
               (-35.2, 119.0), (-48.6, 116.4), (-60.2, 110.0), (-67.0, 103.6), (-75.2, 90.2), (-79.9, 73.0),
               (-82.1, 59.3), (-82.1, 37.8), (-77.8, 15.5), (-71.3, 0.4)]
PAD = dict(at=(-196.0, -60.0), turn=12.0, height=(20.0, 30.0))   # its front's and back's heights
PAD_D = 124.6
DPAD = dict(at=(-49.0, 85.0), ring=18.0, size=24.0, arm=9.0, height=3.0)
ABC = dict(a=(57.0, 98.0), b=(42.0, 83.0), c=(25.0, 69.0), size=(16.0, 13.0), turn=-35.0, height=3.4)
SMALL = dict(pause=(-15.0, 72.0), option=(0.0, 72.0), size=(11.0, 5.5), turn=55.0, height=1.6)
KEYPAD = dict(x=(-28.0, 28.0), y=(14.0, 48.0), key=(13.0, 5.4), plate=(-40.0, 40.0, 4.0, 58.0), height=1.6)

# The Jaguar CD: its plan (a semicircle at the front, straight sides back), its heights; the lid (its hinge at its
# back); the slot's frame at its back.
CD = dict(r=88.0, at=118.0, back=(-76.0, 76.0, 246.0), foot=44.0, top=72.0)   # the round front, the back section
LID = dict(r=78.0, back=172.0, height=4.0)                      # its round front (same middle), its back edge
CD_FRAME = dict(x=(-76.0, 76.0), y=(184.0, 246.0), top=86.0)
CD_SLOT = dict(x=(-58.0, 58.0), y=(196.0, 226.0), depth=40.0)
DISC = dict(diameter=120.0, hole=15.0, thickness=1.2, well=4.0)   # the well under the lid, round the disc

COLOURS = dict(case="#1E1E21", key="#141416", red="#C8302A", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 486, 512), pad=(494, 0, 530, 400), cd=(0, 520, 400, 446), disc=(494, 408, 256, 256),
               label=(758, 408, 266, 136))
SWATCHES = dict(red=(774, 568), dark=(806, 568), grey=(838, 568), silver=(870, 568), window=(902, 568),
                lit=(934, 568))

FPS = 30
LENGTH = 240                 # 8 s
