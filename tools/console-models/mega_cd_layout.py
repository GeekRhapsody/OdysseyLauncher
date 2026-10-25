"""The Mega-CD's measurements, shared by mega_cd_print.py (which draws its printing) and mega_cd.py (which builds it).
Plain Python: Blender's Python imports it too.

The first Mega-CD (1991) with mega_drive.py's Mega Drive sitting on it. Millimetres in the Mega Drive's frame: x from
the middle (left to right), y back from the middle (the fronts at -y), z up from the table. The Mega-CD is 268 x 230 x 64
mm, its feet included, measured from photographs on Wikimedia Commons (Evan-Amos's views of the Mega-CD alone and with
its Mega Drive, and two views of the set from the front and the front right), scaled by the Mega Drive's 280 mm width.

The Mega-CD: a black box on four feet, a glossy panel sunk into its front (the tray's door with MEGA-CD at the left,
SEGA under it; the READY, compact disc and ACCESS panel at the right, the four lights' legends under it), and the
connecting block on its right end, rising beside the Mega Drive. The Mega Drive sits on its top, its front over the
Mega-CD's.

One texture (ATLAS square, REGIONS): `front` (the Mega-CD's front panel, seen from in front), `door` (the tray's door),
`disc` and `data` (the CD's two sides: a made-up game, Odyssey), and swatches; the Mega Drive keeps mega_drive_print.py's
own. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 268.0, 230.0, 64.0
FOOT = 6.0
FRONT_Y = -DEPTH / 2                                      # the Mega-CD's front
PANEL = dict(x=(-126.0, 126.0), z=(15.0, 56.0), depth=2.0)   # the glossy panel, sunk into the front
DOOR = dict(x=(-118.0, -8.0), z=(29.0, 47.0), out=1.0)    # the tray's door, in the panel
TRAY = dict(depth=150.0, z=(30.0, 35.0), travel=118.0, well=(78.0, 60.5))   # its plate; how far it comes out; the
                                                                            # disc's well (back from the door, radius)
LIGHTS = dict(ready=(46.0, 39.0), access=(104.0, 39.0), size=(22.0, 7.0))   # x, z of each pill on the panel
BLOCK = dict(x=(130.0, 172.0), y=(-56.0, 104.0), top=108.0, inner=142.0)    # the connecting block; above the
                                                                           # Mega-CD's top it stands clear of x
MD_LIFT = HEIGHT                                          # the Mega Drive stands on the Mega-CD's top
MD_BACK = 4.0                                             # and a little back from its front

DISC = dict(r=60.0, hole=7.5, thickness=1.2)

COLOURS = dict(case="#151517", gloss="#09090A", disc="#FFFFFF")

REGIONS = dict(front=(0, 0, 1024, 168), door=(0, 176, 512, 84), disc=(0, 268, 256, 256), data=(264, 268, 256, 256))
SWATCHES = dict(green=(552, 296), red=(584, 296), dark=(616, 296), grey=(648, 296))

FPS = 30
LENGTH = 240                 # 8 s
