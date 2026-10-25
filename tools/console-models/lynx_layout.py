"""The Atari Lynx II's measurements, shared by lynx_print.py (which draws its printing and screens) and lynx.py (which
builds it). Plain Python: Blender's Python imports it too.

The Lynx II (1991), 235 x 108 x 51 mm (the figures Retro Isle and Atari Gamer give; its grips' bulges at the back
included), standing up facing the viewer as the handheld models do. Millimetres: x from its middle (left to right), y
back from its front face, z up from its middle. The rest was measured from Evan-Amos's photographs on Wikimedia Commons
(the Lynx II from in front, flat, which gives the front's layout, and from the back, the top, the bottom and at an
angle), scaled by its width.

The body: its front outline (OUTLINE: a long rounded shape, its ends bulging), lofted back, the grips' bulges behind
its ends; the grips at the ends a little proud of the glossy middle. On the front: the screen's window in the middle,
the LYNX logo over it and ATARI under it; ON, OFF and BACKLIGHT at its left, OPTION 1, PAUSE and OPTION 2 at its right;
the D-pad in the left grip; two pairs of A and B in the right grip, one at its top and one at its foot (for playing it
the other way up); the speaker's slots between them. The game card slides down into the slot at the top of its back.

One texture (ATLAS square, REGIONS): `front` (the front from in front: the grips, the middle, the window's surround and
the switched-off screen, the logos, the buttons' names and their brackets, the speaker, the D-pad's well), the screens
(`title`, a made-up game, Odyssey; `game`, a moment of its play; `game_flipped`, the same turned over, as FLIP shows it),
`card` (the game card's label), and swatches. A region is (x, y, width, height) in pixels.
"""

WIDTH, HEIGHT, DEPTH = 235.0, 108.0, 33.0        # the body; the grips' bulges reach BULGE further back
BULGE = dict(x=74.0, depth=17.0)                 # the bulges: from |x| = 74 to the ends

# The front outline's right half, from the top's middle round to the bottom's (x, z); the left half mirrors it.
RIGHT_HALF = [(0.0, 54.0), (60.0, 54.0), (90.0, 54.0), (100.0, 53.0), (106.0, 50.2), (110.5, 44.5), (113.6, 36.0),
              (115.8, 24.0), (117.1, 12.0), (117.5, 0.0), (117.1, -12.0), (115.8, -24.0), (113.6, -36.0),
              (110.5, -44.5), (106.0, -50.2), (100.0, -53.0), (90.0, -54.0), (60.0, -54.0), (0.0, -54.0)]
GRIP_X = 59.4                                    # the grips: from |x| = GRIP_X out, PROUD in front of the middle
PROUD = 1.8

SCREEN = dict(at=(0.5, 0.5), size=(75.0, 47.0))                 # the LCD: its middle (x, z), w x h
WINDOW = dict(at=(0.6, 0.6), size=(93.5, 68.0), corner=8.0, height=2.6)   # the window's cover, standing proud
LEFT_BUTTONS = dict(x=-55.6, z=[16.9, 1.0, -15.4], size=(7.6, 10.6), height=2.6)   # ON, OFF, BACKLIGHT
RIGHT_BUTTONS = dict(x=57.7, z=[17.1, 0.7, -15.4], size=(7.6, 10.6), height=2.6)   # OPTION 1, PAUSE, OPTION 2
DPAD = dict(at=(-90.9, 0.6), size=31.0, arm=10.6, height=3.6, well=1.4)
AB = dict(top=[(72.6, 36.9), (91.9, 41.8)], bottom=[(73.3, -35.6), (92.7, -41.0)], turn=(14.2, -15.6),   # B, A
          well=16.0, size=12.4, height=3.0)
LYNX = dict(at=(3.2, 41.9), width=47.0, height=5.6)
LIGHT = dict(at=(-49.0, 42.8), r=1.4)
ATARI = dict(at=(1.3, -39.7), height=3.6)
SPEAKER = dict(x=(84.0, 109.0), z=(-27.0, 27.0), count=6)
GROOVES = dict(x=(-71.5, -67.6), z=(-21.0, 21.0))

# The game card: w x h x thickness; its seat in the slot at the back's top (its middle's y; its top flush with the
# body's top).
CARD = dict(size=(52.0, 65.0, 4.5), y=DEPTH - 4.0, lip=6.0)

COLOURS = dict(case="#28282B", key="#131315", glass="#FFFFFF", print="#FFFFFF")

ATLAS = 1024
SCREEN_PX = (320, 200)
REGIONS = dict(front=(0, 0, 1024, 472), title=(0, 480) + SCREEN_PX, game=(328, 480) + SCREEN_PX,
               game_flipped=(656, 480) + SCREEN_PX, card=(0, 688, 208, 260))
SWATCHES = dict(case=(240, 712), key=(272, 712), red=(304, 712), lcd=(336, 712), card=(368, 712))

FPS = 30
LENGTH = 240                 # 8 s
