"""The CreatiVision card's measurements, shared by crvision_print.py (which draws its printing) and crvision.py (which
builds it). Plain Python: Blender's Python imports it too.

VTech's CreatiVision (1981) and its two controllers. No published size was found; it is about 330 x 225 x 70 mm, scaled
from the 40-pin chip (52.6 mm) on its board in a photograph of it opened, the rest measured from Evan-Amos's photographs
on Wikimedia Commons (the console from each side, with its controllers docked and out). Some show the Dick Smith
Wizzard's sticker on it; the card is the CreatiVision's own. Millimetres: x from the console's middle (left to right), y
back from its front, z up from the table.

The console: a flat box of textured black, its four corners black posts, the woodgrain panels on its two ends between
them; the raised deck over its back (the vents along its back edge, the OFF/ON slide and RESET at its left, CREATIVISION
embossed in its middle, the rainbow badge at its right); the compartment in front of the deck, a step lower, its two
trays either side of the divider, each controller docked in its own, the keypads meeting in the middle so the two read
as one keyboard, the joysticks at the ends. The cartridge slot stands proud of the right end's foot; a cartridge goes in
flat, from the right. Each controller is a slab: its keypad (24 keys under a clear window in a raised frame: cream
numbers and specials, tan letters) and its joystick (a short knob, a knurled ring round its top) in its round well, a
fire button on its edge, its coiled cord to the socket in its tray's back wall.

One texture (ATLAS square, REGIONS): `top` (the console from above, planar-mapped onto every face facing up), `end` (an
end's woodgrain panel), `left` and `right` (the controllers' tops), `cart` (the cartridge's label: a made-up game), and
swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 330.0, 225.0, 70.0
POST = 10.0                                   # the corner posts
PANEL = dict(y=(POST, DEPTH - POST), z=(4.0, HEIGHT - 6.0), thickness=2.0)   # the woodgrain panels on the ends
FRONT_TOP = 44.0                              # the front wall's top, before the compartment
TRAYS = dict(y=(10.0, 100.0), floor=40.0, divider=6.0)                       # the compartment: front, back; floor
DECK = 100.0                                  # the deck's front edge: from there back the top is HEIGHT
VENTS = dict(x=(-140.0, 140.0), y=(206.0, 218.0), count=32)
SWITCH = dict(x=(-138.0, -116.0), y=(176.0, 186.0), travel=8.0, knob=(6.0, 6.0, 4.0))   # OFF to ON
RESET = dict(x=(-108.0, -88.0), y=(174.0, 186.0), height=2.0)
NAME = dict(x=0.0, y=170.0, height=12.0)      # CREATIVISION, embossed
BADGE = dict(x=(116.0, 146.0), y=(166.0, 180.0))
SLOT = dict(y=(78.0, 146.0), z=(8.0, 23.0), frame=7.0, out=6.0)   # in the right end, at its foot

# The controllers: each docked in its tray, x from its outer end, its middle's y; length, width, thickness; the
# joystick's well (from its outer end) and the knob; the keypad's window (from its inner end) and keys.
PAD = dict(size=(150.0, 68.0, 24.0), y=55.0, well=dict(u=26.0, r=19.0), knob=(11.0, 18.0),
           window=(6.0, 102.0, 5.0), keys=(6, 4), key=(13.0, 10.0), fire=(68.0, 84.0))
CART = dict(size=(102.0, 66.0, 13.0), out=30.0)          # length (along x), width, thickness; how far it stands out

LEGENDS = {
    "left": [["1", "2", "3", "4", "5", "6"], ["CNT'L", "Q", "W", "E", "R", "T"], ["←", "A", "S", "D", "F", "G"],
             ["SHIFT", "Z", "X", "C", "V", "B"]],
    "right": [["7", "8", "9", "0", ":", "-"], ["Y", "U", "I", "O", "P", "RET'N"], ["H", "J", "K", "L", ";", "→"],
              ["N", "M", ",", ".", "/", "SPACE"]],
}

COLOURS = dict(case="#2E2E2D", top="#3E3E3C", deep="#222222", wood="#7D5C31", cream="#EECD9A", tan="#B17C53",
               knob="#2A2A2A", ring="#8E8E8E", cord="#141414", cart="#202022")

REGIONS = dict(top=(0, 0, 1024, 640), left=(0, 648, 508, 232), right=(516, 648, 508, 232), end=(0, 888, 640, 136),
               cart=(648, 888, 160, 136))
SWATCHES = {name: (836 + 32 * (k % 6), 904 + 32 * (k // 6)) for k, name in enumerate(
    ("case", "top", "deep", "knob", "ring", "cream", "cart", "black", "red"))}

FPS = 30
LENGTH = 240                 # 8 s
