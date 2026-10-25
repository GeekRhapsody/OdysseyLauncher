"""The Game & Watch's measurements, shared by gameandwatch_print.py (which draws its printing and screens) and
gameandwatch.py (which builds it). Plain Python: Blender's Python imports it too.

A Game & Watch Multi Screen (1982) in the brown and cream of Donkey Kong II, open on the table, a made-up game on its
two screens: Odyssey. Each half is 122 x 74 mm and 12.5 mm thick (the Digital Game Museum's 4 3/4 x 3 x 1 inches for
the closed handheld). Millimetres: x from its middle (left to right), y back from the lower half's front edge, z up from
the table; on each half's face, u across from its middle and v from its front edge (the lower half's) or from the hinge
(the upper half's). The rest was measured from photographs of a Donkey Kong II on Wikimedia Commons (from above, from in
front, open at an angle), scaled by its width.

The lower half: its brown body, its face cream with the brown panels at its sides: GAME & WATCH and the D-pad
(CONTROLLER) at the left, GAME A, GAME B and TIME with ALARM and ACL, and JUMP at the right; the screen in the middle,
the Nintendo plate under it. The upper half, hinged at the lower half's back edge, open: its face cream, the title
plate over its screen, the raised panels at its sides, four screws; the ribbon between the halves.

One texture (ATLAS square, REGIONS): `lower` and `upper` (the two faces, each with its screen at rest: the clock on the
lower one), the screens while the game's played (`lower_1` to `lower_3`, `upper_1` to `upper_3`: an LCD's black
segments over its printed backdrop), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HALF = 122.0, 74.0, 12.5               # each half: w x d, its thickness
OPEN = -115.0                                         # the upper half's angle from shut, about the hinge

# The lower half's face, (u, v): v from its front edge.
LOWER_LCD = dict(at=(-1.0, 39.0), size=(54.0, 35.0))
DPAD = dict(at=(-46.0, 23.0), size=16.0, arm=5.6, height=2.6)
SMALL = dict(game_a=(41.5, 63.0), game_b=(41.5, 54.5), time=(41.5, 46.0), size=(7.4, 3.4), height=1.6)
LIGHTS = dict(alarm=(49.5, 58.0), acl=(49.5, 50.5))
JUMP = dict(at=(43.5, 23.0), r=4.8, height=2.4)
BADGE = dict(at=(-46.0, 57.0), size=(14.0, 10.0))
NINTENDO = dict(at=(-1.0, 12.0), size=(31.0, 6.0))
PANELS = dict(left=(-58.0, -33.0), right=(33.0, 58.0))   # the brown side panels, u

# The upper half's face, (u, v): v from the hinge.
UPPER_LCD = dict(at=(0.2, 34.6), size=(56.0, 37.0))
TITLE = dict(at=(0.0, 61.0), size=(31.0, 6.0))
SCREWS = [(-30.0, 59.0), (30.0, 59.0), (-43.0, 10.0), (43.0, 10.0)]
SIDE = dict(left=(-56.0, -34.0), right=(34.0, 56.0), v=(4.0, 70.0))   # the raised side panels

COLOURS = dict(case="#6A3424", key="#141416", glass="#FFFFFF", print="#FFFFFF")

SCREEN_PX = (184, 120)
REGIONS = dict(lower=(0, 0, 640, 388), upper=(0, 396, 640, 388),
               lower_1=(648, 0) + SCREEN_PX, lower_2=(840, 0) + SCREEN_PX, lower_3=(648, 128) + SCREEN_PX,
               upper_1=(840, 128) + SCREEN_PX, upper_2=(648, 256) + SCREEN_PX, upper_3=(840, 256) + SCREEN_PX)
SWATCHES = dict(brown=(664, 400), cream=(696, 400), dark=(728, 400), lit=(760, 400), metal=(792, 400))

FPS = 30
LENGTH = 240                 # 8 s
