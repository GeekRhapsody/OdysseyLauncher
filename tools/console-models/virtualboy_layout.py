"""The Virtual Boy's measurements, shared by virtualboy_print.py (which draws its printing and screens) and
virtualboy.py (which builds it). Plain Python: Blender's Python imports it too.

The Virtual Boy (1995) on its stand, its controller standing on its grips beside it, a made-up game, Odyssey, on its
two red screens. The unit is 254 mm wide (the published 10 inches) and about 117 deep and 99 high, as measured from
Evan-Amos's photographs on Wikimedia Commons (from the visor's side and from below, straight on), scaled by its width;
the stand and the controller from his photographs of them, as near as their angles allow. Millimetres: x from the
middle (left to right), y back from the unit's front (its visor faces the back), z up from the table.

The unit: the red top shell (its front sloping back, VIRTUAL BOY on it, its lower edge rising over the middle where the
black below shows), the raised strip along its top with the grey slider, the black ears at its sides with their ribs,
the black underside; at the back the rubber eyecup round the two screens and the nose's cut-out. The stand: the head
the unit clips onto, its knob, the joint with the Nintendo plate, two legs splayed to their feet, each foot a wire V
on the table. The controller: its two lobes and the bar between them (a D-pad on each lobe, SELECT and START, B and A),
the horn grips, the battery pack between them, its cord to the unit's underside.

The unit's frame: x as the console's, y back from its front, z up from its underside, its origin at the stand's head.
One texture (ATLAS square, REGIONS): the unit's front (`front`, VIRTUAL BOY on the red), the battery pack's front
(`pack`), the stand's plate (`plate`), the controller's face (`face`: the lobes' legends), the screens (`title`,
`game_1`, `game_2`, each one eye's: the right's the same moved for the depth), and swatches. A region is (x, y, width,
height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 228.0, 117.0, 99.0             # the red body; the ears make the whole 254 wide
EARS = dict(x=(112.0, 127.0), y=(50.0, 112.0), z=(16.0, 69.0), ribs=5)
ROUND = dict(plan=16.0, top=10.0, bottom=6.0)
FRONT = dict(foot=(4.0, 4.0), top=(24.0, 89.0))       # the front's slope, (y, z) at its foot and its top
EDGE = dict(sides=24.0, middle=40.0, flat=38.0, slope=74.0)   # the red's lower edge: its height at the sides and
                                                      # over the middle (|x| < flat), sloping between
BACK_RED = 62.0                                       # down the back, the red ends here
STRIP = dict(x=(-52.0, 52.0), y=(14.0, 112.0), height=5.0)
SLIDER = dict(x=(-16.0, 16.0), y=(70.0, 100.0), height=3.0)   # the grey slider on the strip
LOGO = dict(x=(-100.0, -26.0), z=(48.0, 76.0), area=(-108.0, -18.0, 40.0, 84.0))   # VIRTUAL BOY on the front's
                                                      # left; its region (x0, x1, z0, z1) on the front

# The eyecup at the back: the rubber's outline (outer, inner) and how far it stands out, the screens inside it.
EYECUP = dict(outer=(174.0, 80.0, 18.0), inner=(140.0, 56.0, 14.0), at=(4.0, 44.0), out=26.0, nose=(36.0, 24.0))
SCREEN = dict(size=(48.0, 30.0), x=29.0, z=46.0, sunk=7.0)   # each eye's screen, from the back face

# The stand, in the console's frame: the unit's underside at HEAD's top.
HEAD = dict(size=(52.0, 46.0, 24.0), at=(0.0, 62.0), top=205.0)
KNOB = dict(at=(40.0, 181.0), r=11.0, length=18.0)
JOINT = dict(size=(64.0, 26.0, 34.0), z=140.0)
LEGS = dict(feet=[(-108.0, 26.0), (108.0, 98.0)], tip=125.0, r=3.2)   # each foot's (x, y); its V's arm reaches back

# The controller, standing on its grips, its face to the front: its own frame (x across, z up from its face's middle,
# y back from its face), then where it stands.
LOBES = dict(x=48.0, r=31.0, bar=(-22.0, 17.0), depth=22.0)
DPADS = dict(x=56.0, z=8.0, size=21.0, arm=6.6, height=3.0)
SELECT_START = dict(at=[(-30.0, -4.0), (-20.0, -14.0)], r=5.0, height=2.4)
B_A = dict(at=[(20.0, -12.0), (33.0, -5.0)], r=5.6, height=3.0)
PACK = dict(x=(-30.0, 30.0), y=(6.0, 40.0), z=(-58.0, -14.0))
GRIP = dict(path=[(70.0, 8.0, -8.0), (88.0, 9.0, -40.0), (88.0, 13.0, -88.0), (70.0, 17.0, -112.0)], r=(13.0, 11.0))
PAD = dict(at=(196.0, -36.0), turn=-28.0, lean=12.0)

COLOURS = dict(red="#C8161E", black="#141416", grey="#8C8E94", rubber="#1B1B1D", print="#FFFFFF", glow="#FF1E10")

SCREEN_PX = (264, 156)
REGIONS = dict(front=(0, 0, 450, 220), pack=(458, 0, 300, 220), plate=(766, 0, 196, 90), face=(0, 228, 512, 200),
               title=(0, 436) + SCREEN_PX, game_1=(272, 436) + SCREEN_PX, game_2=(544, 436) + SCREEN_PX)
SWATCHES = dict(red=(600, 300), black=(632, 300), grey=(664, 300), rubber=(696, 300), dark=(728, 300))

FPS = 30
LENGTH = 240                 # 8 s
