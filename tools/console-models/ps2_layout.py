"""The PlayStation 2's measurements, shared by ps2_print.py (which draws its printing) and ps2.py (which builds it).
Plain Python: Blender's Python imports it too.

The black launch model (the SCPH-30000s and 50000s), lying flat: 301 x 182 x 78 mm. Millimetres: x from its middle
(left to right), y back from its front edge, z up from the table. The rest was measured from photographs on Wikimedia
Commons (Evan-Amos's views from both front corners), scaled by its width.

Two parts: the upper body, its front a stack of fins (five grooves across it), holding on the left the memory card
slots and controller ports, in the middle the disc tray's door (the PlayStation mark on it), on the right the power
and eject buttons, SONY up the end; and under it the base, set back, with the fan's grille and the blue panel of USB
and i.LINK ports.

Two textures. `print` (ATLAS square, REGIONS): `top` (the top seen from above: the PS2 logo and PlayStation 2, reading
from the back as they do when it stands, the formats' marks along the front), `front` (the upper body's front seen from
in front: the slots, ports, buttons, the mark on the tray's door, SONY) and `base` (the base's front: the grille, the
blue panel), and swatches. `disc` (DISC_ATLAS): the DVD's label side (a made-up game, Odyssey) and its silver side.
"""

ATLAS = 1024
DISC_ATLAS = (1024, 512)

WIDTH, DEPTH, HEIGHT = 301.0, 182.0, 78.0
BASE = dict(x=(-150.0, 118.0), y=14.0, height=21.0)               # under the upper body, set back at its front
GROOVES = [28.0 + 9.4 * k for k in range(5)]                      # the fins' grooves across the front, z
GROOVE = (1.8, 2.5)                                               # each one's height and depth
TRAY = dict(x=(-12.0, 124.0), z=(39.0, 55.0), depth=150.0, travel=118.0)   # its door in the front; how far it comes out
WELL = dict(x=56.0, y=72.0, r=61.0, depth=1.6)                    # the disc's place in the tray, its middle
BUTTONS = dict(power=(136.0, 67.0), eject=(136.0, 48.0), size=(11.0, 8.0, 1.6))   # their middles (x, z); w, h, out
LIGHTS = dict(power=(136.0, 72.5), eject=(136.0, 53.5), size=(3.0, 1.2))          # each light above its button

DISC = dict(r=60.0, hole=7.5, thickness=1.2)

COLOURS = dict(case="#17171A", dark="#0A0A0C")

REGIONS = dict(top=(0, 0, 1024, 619), front=(0, 624, 1024, 197), base=(0, 826, 1024, 80))
SWATCHES = dict(green=(16, 940), dark=(48, 940), blue=(80, 940))   # each a 24 x 24 block's middle
DISC_REGIONS = dict(label=(0, 0, 512, 512), data=(512, 0, 512, 512))

FPS = 30
LENGTH = 240                 # 8 s
