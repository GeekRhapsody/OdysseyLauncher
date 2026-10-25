"""The Magnavox Odyssey² set's measurements, shared by odyssey2_print.py (which draws its printing) and odyssey2.py
(which builds it). Plain Python: Blender's Python imports it too.

The Odyssey² (1978; the Philips Videopac G7000 in Europe, the same case), 343 x 333 mm (the Tempe History Museum's 13
1/2 x 13 1/8 inches), its top rising to about 74 mm at its back, and its two joysticks. Millimetres: x from its middle
(left to right), y back from its front edge, z up from the table. The rest was measured from photographs on Wikimedia
Commons (Evan-Amos's views of it from the front left and right and with its joysticks, the Videopac's keyboard from
above, the Videopac from in front), scaled by its width and the keyboard's 19.05 mm pitch.

The case: a black body, and the silver top over it (its side outline, TOP, extruded across its width): the keyboard
sloping gently up from the front edge, the top rising behind it to the flat back. The membrane keyboard in its black
panel, sunk into the slope; the cartridge slot's black panel sunk into the back (the slot, the stripes, MAGNAVOX and
the red POWER key); ODYSSEY² MICROPROCESSOR at the back left. The joysticks: black boxes, a raised plate on each, the
stick in its ring, the red ACTION button at its back left corner.

One texture (ATLAS square, REGIONS): `keyboard` (the keyboard's panel from above: its boxes, NUMERIC, FUNCTION,
INPUT, RESET and ALPHA, the keys and their legends, SPACE and its stripes), `back` (the slot's panel from above: its
stripes, MAGNAVOX, POWER), `logo` (ODYSSEY² MICROPROCESSOR on the silver), `label` (the cartridge's: a made-up game,
Odyssey), `stick` (a joystick's plate: ACTION), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH = 343.0, 333.0
TOP = [(0.0, 32.0), (180.0, 44.0), (205.0, 50.0), (225.0, 64.0), (240.0, 71.0), (325.0, 74.0), (DEPTH, 70.0)]
SHELL = 8.0                                       # the silver top's thickness; the black body under it
BODY_INSET = 1.5                                  # the black body's sides and front, in from the silver's

# The keyboard's panel, sunk SINK into the slope (its frame: x across, s up the slope from the front edge's top).
SLOPE = math.atan2(TOP[1][1] - TOP[0][1], TOP[1][0] - TOP[0][0])
KEYBOARD = dict(x=(-97.0, 113.5), s=(22.0, 166.5), sink=2.0, corner=5.0)
U = 19.05

# The keys, in the panel's own plan (x from its left edge, s down from its back edge, millimetres, measured from the
# Videopac's keyboard from above): each row's first key's middle, its keys' legends a pitch U apart; a key KEY wide and
# deep; the space bar and its stripes; the boxes round the rows.
KEY = (15.5, 8.3)
ROWS = [dict(x=19.0, s=18.6, keys=list("0123456789")),
        dict(x=19.0, s=39.6, keys=["+", "−", "×", "÷", "=", "YES", "NO", "CLEAR", "ENTER", "△"]),
        dict(x=17.5, s=69.6, keys=list("QWERTYUIOP")),
        dict(x=26.8, s=87.7, keys=list("ASDFGHJKL")),
        dict(x=36.1, s=106.3, keys=list("ZXCVBNM") + ["·", "?"])]
SPACE = dict(x=(76.4, 131.0), s=(122.0, 130.0), stripes=[(6.2, 74.3), (132.0, 202.0)])
BOXES = dict(x=(7.2, 201.2), numeric=(8.3, 25.8), function=(29.9, 47.5), alpha=(59.9, 138.3))

# The slot's panel, sunk into the back; the slot through it; the POWER key standing in it.
BACK = dict(x=(-105.0, 155.0), y=(262.0, 306.0), sink=3.0)
SLOT = dict(x=(-50.0, 36.0), y=(277.0, 292.0), depth=48.0)
POWER = dict(x=(96.0, 110.0), y=(282.0, 292.0), height=5.0)
LOGO = dict(x=(-166.0, -110.0), y=(272.0, 304.0))

# The cartridge: w x d x h, standing in the slot (SEAT, its bottom's middle); its label on its front.
CART = dict(size=(82.0, 13.0, 80.0), label=(66.0, 44.0), depth=40.0)

# The joysticks: each a box (w x d x h), its plate on it, the stick (its ring, its shaft, its knob), ACTION; where
# each stands, turned.
STICK = dict(box=(78.0, 92.0, 30.0), plate=(64.0, 72.0, 3.0), ring=12.0, shaft=(3.6, 44.0), knob=6.0,
             action=(-22.0, 32.0, 18.0, 8.0, 3.0))   # the button's middle (from the box's middle), w x d, its height
STICKS = [dict(at=(-240.0, -30.0), turn=14.0), dict(at=(-134.0, -112.0), turn=4.0)]

COLOURS = dict(silver="#AEB0B4", body="#1E1E20", black="#111113", red="#D22C2C", print="#FFFFFF")

REGIONS = dict(keyboard=(0, 0, 1024, 703), back=(0, 711, 1024, 173), logo=(0, 892, 240, 132),
               label=(248, 892, 200, 132), stick=(456, 892, 112, 126))
SWATCHES = dict(red=(640, 908), red_lit=(672, 908), black=(704, 908), silver=(736, 908), body=(768, 908))

FPS = 30
LENGTH = 240                 # 8 s
