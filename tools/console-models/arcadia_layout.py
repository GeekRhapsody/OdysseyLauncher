"""The Arcadia 2001 card's measurements, shared by arcadia_print.py (which draws its printing) and arcadia.py (which
builds it). Plain Python: Blender's Python imports it too.

Emerson's Arcadia 2001 (1982) and its two controllers. The console is 292 mm wide, 175 deep and 76 high (Video Games
magazine, December 1982: "11½ by seven inches and three inches deep"); the rest was measured from photographs (Evan-
Amos's of the console and a controller on Wikimedia Commons, one of the console square from above, which its width
scales). Millimetres: x from the console's middle (left to right), y back from its front, z up from the table.

The console: a dark shell on a walnut plinth band; a low controller bay either side, its floor flat, a wedge rising at
its back; the centre block between them, its top sloping up from the front (the ribbed grille, the strip of buttons:
RESET, SELECT, OPTION, START and the wider POWER; the silver panel with ARCADIA-2001, the three bars, BY Emerson and
the POWER ON light) to the raised back with the cartridge slot across its top. Each controller lies in its bay, its
keypad end to the back: a silver strip, the keypad's window (twelve round keys on a champagne face), the raised block
with the joystick's spun-metal disc in its round recess and the stick standing on it, LEFT (or RIGHT) HAND CONTROLLER on
the black strip at its foot, a red fire button on each long side; its coiled cord leaves the console's back and comes
over the wedge into its top corner. The cartridge goes in upright, its title end up.

One texture (ATLAS square, REGIONS): `top` (the console from above, planar-mapped onto every face facing up), `wood`
(the plinth's walnut, round its sides), `left` and `right` (the controllers' faces from above), `cart` (the cartridge's
face: its blue label) and `cart_end` (its title end), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 292.0, 175.0, 76.0
PLINTH = 15.0                            # the walnut band's top
CORNER = 8.0                             # the corners, in plan
FLOOR = 32.0                             # the bays' floor
RIM = dict(width=4.0, height=3.0)        # the bays' low rims along the ends and the front
WEDGE = dict(y=(158.0, DEPTH), height=24.0)   # the wedge at the back of each bay, rising over the floor

BLOCK = dict(x=63.0)                     # the centre block's half width
# The centre block's side outline (y, z): the slope from the front up to the step, the raised back with the slot.
SLOPE = ((4.0, 40.0), (104.0, 62.0))     # the slope: its front and back edges
BLOCK_PROFILE = [(0.0, PLINTH), (DEPTH, PLINTH), (DEPTH, HEIGHT - 4.0), (DEPTH - 4.0, HEIGHT), (114.0, HEIGHT),
                 (108.0, HEIGHT - 4.0), SLOPE[1], SLOPE[0], (0.0, 36.0)]
GRILLE = dict(x=(-52.0, 52.0), s=(4.0, 34.0), ribs=30, depth=2.0)     # along the slope from its front edge
BUTTONS = dict(s=(38.0, 52.0), depth=3.0, x=(-44.0, -22.0, 0.0, 22.0), r=7.0, power=(37.0, 50.0), height=3.0)
PANEL = dict(x=(-56.0, 56.0), s=(55.0, 101.0))                         # the silver panel
LIGHT = dict(x=42.0, s=92.0, r=2.2)                                    # POWER ON's light
SLOT = dict(x=(-51.0, 51.0), y=(132.0, 156.0), depth=50.0, frame=3.0)  # in the raised back's top

# The controllers: their middles, each lying keypad end to the back; length, width, height; the regions along it, from
# its top end (the keypad's end): the label strip, the keypad's window and keys, the joystick's block and disc.
PAD = dict(x=(-105.0, 105.0), y=82.0, size=(152.0, 68.0, 18.0), corner=8.0,
           strip=(4.0, 17.0), window=(19.0, 80.0, 5.0, 2.0),           # from, to its top end; inset from its sides; deep
           keys=dict(cols=(-17.0, 0.0, 17.0), rows=(29.0, 44.0, 59.0, 74.0), r=6.2),
           block=(84.0, 144.0, 3.0), disc=dict(v=113.0, r=19.0, recess=22.0, depth=3.0), stick=(3.6, 24.0), knob=4.6,
           fire=dict(v=(54.0, 70.0), z=(5.0, 13.0), out=2.5), foot=(144.0, 152.0))
CORD = dict(r=1.3, coil=4.0, pitch=3.6, out=(80.0, 22.0))   # the coiled cords: the wire, the coil, where they leave
                                                            # the console's back (x either side, z)

CART = dict(size=(97.0, 22.0, 101.0), inserted=62.0, above=60.0)      # width, thickness, height; how deep it goes in

COLOURS = dict(shell="#3A3533", floor="#4A4544", wood="#6A5143", silver="#979892", gold="#C5BA9C", dark="#2A2624",
               champagne="#9B957B", disc="#B8AE94", stick="#2E2922", red="#941322", cart="#2B282B", label="#05598F",
               light="#FF3A30", cord="#2A2624")

REGIONS = dict(top=(0, 0, 1024, 614), wood=(0, 622, 1024, 56), left=(0, 686, 160, 338), right=(176, 686, 160, 338),
               cart=(352, 686, 232, 242), cart_end=(352, 936, 232, 56))
SWATCHES = {name: (616 + 32 * (k % 12), 712 + 32 * (k // 12)) for k, name in enumerate(
    ("shell", "floor", "gold", "dark", "champagne", "disc", "stick", "red", "cart", "silver", "light", "black"))}

FPS = 30
LENGTH = 240                 # 8 s


def slope_point(s, h=0.0):
    """The model's (y, z) of the point s up the centre block's slope from its front edge and h off it."""
    (y0, z0), (y1, z1) = SLOPE
    a = math.atan2(z1 - z0, y1 - y0)
    return y0 + s * math.cos(a) - h * math.sin(a), z0 + s * math.sin(a) + h * math.cos(a)


SLOPE_ANGLE = math.atan2(SLOPE[1][1] - SLOPE[0][1], SLOPE[1][0] - SLOPE[0][0])
SLOPE_LENGTH = math.hypot(SLOPE[1][0] - SLOPE[0][0], SLOPE[1][1] - SLOPE[0][1])
