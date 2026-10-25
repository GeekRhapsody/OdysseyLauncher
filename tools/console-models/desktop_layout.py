"""The Desktop Apps card's measurements, shared by desktop_print.py (which draws its printing and screens) and
desktop.py (which builds it). Plain Python: Blender's Python imports it too.

Desktop Apps is the shortcuts on the user's desktop, so it has no hardware of its own: the card is an unbranded
15.6-inch laptop, open, its screen showing a made-up desktop of shortcuts (each icon with its shortcut arrow), one of
them a made-up game, Odyssey. A laptop rather than a tower, so it isn't Windows' card. Millimetres: x from its middle
(left to right), y back from the base's front edge, z up from the table; the lid's own frame is x across, z up the lid
from its hinge, y back from the screen's face.

The base: its slab, the keyboard sunk into it, the touchpad, the speaker grilles beside the keyboard. The lid: open
LID["open"] degrees from the base, the bezel round the screen.

One texture (ATLAS square, REGIONS): `desktop` (the screen at rest), `title`, `game_1` and `game_2` (the game's window,
three ways: its title bar and its content), `selected` (the Odyssey shortcut selected), `keyboard` (the base from
above), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, BASE = 356.0, 240.0, 17.0
ROUND = dict(plan=9.0, edge=2.0)
WELL = dict(x=(-140.0, 140.0), y=(96.0, 222.0), depth=0.8)      # the keyboard's well
TOUCHPAD = dict(x=(-58.0, 58.0), y=(12.0, 84.0), depth=0.5)
LID = dict(width=356.0, height=232.0, thickness=6.0, open=112.0, hinge=(234.0, 17.0))   # the hinge: (y, z) on the base
SCREEN = dict(size=(344.0, 193.5), bottom=27.0)                  # the screen's size and how far up the lid it starts

# On the screen (u across from its middle, v up from its bottom): the shortcuts' column, the game's window.
ICONS = dict(x=-156.0, top=178.0, pitch=30.0, size=18.0)        # the first icon's middle, the spacing, its size
ODYSSEY = 0                                                       # the game's shortcut is the first
WINDOW = dict(at=(14.0, 104.0), size=(232.0, 145.0), close=(122.0, 172.5))   # its middle; its close button
CURSOR = dict(rest=(52.0, 62.0), size=12.0)

COLOURS = dict(body="#6B6E74", print="#FFFFFF")

REGIONS = dict(desktop=(0, 0, 640, 360), selected=(648, 0, 64, 64), title=(0, 368, 320, 200),
               game_1=(328, 368, 320, 200), game_2=(656, 368, 320, 200), keyboard=(0, 576, 640, 432))
SWATCHES = dict(body=(760, 40), dark=(792, 40), black=(824, 40), white=(856, 40), bezel=(888, 40), hinge=(920, 40),
                key=(952, 40), lid=(984, 40))

FPS = 30
LENGTH = 240                 # 8 s
