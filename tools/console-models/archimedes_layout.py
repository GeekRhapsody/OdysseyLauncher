"""The Acorn Archimedes card's measurements, shared by archimedes_print.py (which draws its printing and screens) and
archimedes.py (which builds it). Plain Python: Blender's Python imports it too.

The BBC A3000 (1989), the Archimedes in one box, 490 mm wide, 340 deep and 85 high (measured from photographs on
Wikimedia Commons, scaled by its keys' 19.05 mm pitch: no published figures turned up), its three-button mouse at its
right, and an Acorn colour monitor behind it (350 wide, 320 high and 387 deep on its base: the AKF12's spec sheet), a
3.5-inch floppy with a made-up game, Odyssey, going into the drive in its right side. Millimetres: x from the A3000's
middle (left to right), y back from its front, z up from the table. Measured from photographs on Wikimedia Commons (from
the front and above, the front left, its back straight on; the mouse from above; others with their monitors).

The A3000: a cream wedge (PROFILE: the front, the keyboard's deck sloping up, the raised back block with its two vent
grilles, the back); its keys standing on the deck in the deck's frame (the function row's red F1 to F12, the main block,
the cursor keys, the keypad: KEYS, in units of U across and rows up the deck), the Acorn badge on the back block's front
face, the BBC badge at the keypad's head; the floppy drive in its right side (DRIVE). The mouse (MOUSE): its three
buttons across its front. The monitor (MONITOR): its case, its housing tapering behind, the bezel round the tube, the
Acorn badge, the power switch and its light, on its base.

Two textures (ATLAS square). `print` (REGIONS): `deck` (the A3000 from above: the keys' tops and legends, the grilles,
the BBC badge), `bezel` (the monitor's front), `badge` (the Acorn badge), `floppy` (the floppy's top), `mouse` (the
mouse from above), and swatches. `media` (MEDIA_REGIONS): the screens (`desktop`, `filer`, `game_1`, `game_2`: RISC OS's
desktop and its icon bar, the floppy's filer window with !Odyssey in it, the game full screen). A region is (x, y,
width, height) in pixels.
"""

import math

ATLAS = 1024
U = 19.05

WIDTH, DEPTH, HEIGHT = 490.0, 340.0, 85.0
FRONT = (10.0, 30.0)              # the deck's front edge (y, z)
DECK_BACK = (166.0, 54.0)         # its back edge, at the back block's foot
SLOPE = math.atan2(DECK_BACK[1] - FRONT[1], DECK_BACK[0] - FRONT[0])
BLOCK = 172.0                     # the back block's front face (y)
PROFILE = [                       # the side outline (y, z), round from the front's foot
    (4.0, 0.0), (DEPTH - 4.0, 0.0), (DEPTH, 4.0), (DEPTH, HEIGHT - 4.0), (DEPTH - 4.0, HEIGHT), (BLOCK + 4.0, HEIGHT),
    (BLOCK, HEIGHT - 4.0), (BLOCK, DECK_BACK[1] + 3.0), DECK_BACK, FRONT, (4.0, FRONT[1] - 1.0), (0.0, FRONT[1] - 4.0),
    (0.0, 4.0),
]
GRILLES = [dict(x=(-208.0, 50.0), y=(206.0, 330.0)), dict(x=(96.0, 236.0), y=(206.0, 330.0))]
BADGE = dict(x=(-232.0, -170.0), z=(64.0, 80.0))              # the Acorn badge, on the back block's front face

KEYS_X0, ROW1 = -219.0, 138.0     # the keys' left edge; the function row's middle (s)
KEY = dict(height=10.0, inset=2.2)
# Each key: (legend, x in units from KEYS_X0, width in units, row: 0 the function row, 1 to 5 the main rows (the
# number row first), its height in rows).
FUNCTION = [("Esc", 0.0, 1.0)] + [("F%d" % (k + 1), 2.0 + k + 0.5 * (k // 4), 1.0) for k in range(12)] + \
    [("Print", 15.5, 1.0), ("Scroll Lock", 16.5, 1.0), ("Break", 17.5, 1.0)]
MAIN = [
    [(c, 1.0) for c in "`1234567890-=£"] + [("←", 1.0)],
    [("Tab", 1.5)] + [(c, 1.0) for c in "QWERTYUIOP[]"] + [("\\", 1.5)],
    [("Ctrl", 1.75)] + [(c, 1.0) for c in "ASDFGHJKL;'"] + [("Return", 2.25)],
    [("Shift", 2.25)] + [(c, 1.0) for c in "ZXCVBNM,./"] + [("Shift", 2.75)],
    [("Caps Lock", 1.5), (None, 0.5), ("Alt", 1.5), (" ", 7.0), ("Alt", 1.5), (None, 1.5), ("Ctrl", 1.5)],
]
CURSOR = [("Insert", 15.5, 1), ("Home", 16.5, 1), ("Page Up", 17.5, 1), ("Delete", 15.5, 2), ("Copy", 16.5, 2),
          ("Page Down", 17.5, 2), ("↑", 16.5, 4), ("←", 15.5, 5), ("↓", 16.5, 5), ("→", 17.5, 5)]
KEYPAD = [("Num Lock", 19.0, 1, 1), ("/", 20.0, 1, 1), ("*", 21.0, 1, 1), ("#", 22.0, 1, 1), ("7", 19.0, 2, 1),
          ("8", 20.0, 2, 1), ("9", 21.0, 2, 1), ("-", 22.0, 2, 1), ("4", 19.0, 3, 1), ("5", 20.0, 3, 1),
          ("6", 21.0, 3, 1), ("+", 22.0, 3, 1), ("1", 19.0, 4, 1), ("2", 20.0, 4, 1), ("3", 21.0, 4, 1),
          ("Enter", 22.0, 4, 2), ("0", 19.0, 5, 1), (".", 21.0, 5, 1)]
BBC = dict(x=(19.0, 23.0))        # the BBC badge's span (units), in the function row

# The drive in the right side: its bezel (y, z); its slot (y0, y1, z0, z1); its eject button's middle (y, z) and size;
# its light (y, z).
DRIVE = dict(y=(194.0, 306.0), z=(56.0, 74.0), slot=(210.0, 302.0, 62.0, 67.0), button=(201.0, 66.0, 6.0),
             light=(201.0, 59.0))
FLOPPY = dict(size=(90.0, 94.0, 3.3), shutter=(46.0, 30.0), out=100.0)       # w, d, t; how far out of the slot it waits

MOUSE = dict(size=(60.0, 100.0, 34.0), at=(300.0, 112.0, -8.0), buttons=3)  # w, length, h; where it sits and its turn
# The monitor: its case; its front's middle (x, y); its base's radius and height. Its screen: the glass's size, its
# middle's height, its bulge; the opening round it (w, h, corners' radius) and how deep the glass sits in it.
MONITOR = dict(width=350.0, height=320.0, depth=387.0, at=(0.0, 380.0), base=(110.0, 28.0))
SCREEN = dict(size=(262.0, 200.0), z=196.0, bulge=6.0, frame=(282.0, 220.0, 12.0), depth=16.0)

COLOURS = dict(case="#E3DDCB", key="#C7C2B4", red="#D9472B", monitor="#DCD6C4", print="#FFFFFF")

REGIONS = dict(deck=(0, 0, 1024, 711), bezel=(0, 716, 330, 302), badge=(340, 716, 124, 32), floppy=(340, 756, 135, 141),
               mouse=(484, 756, 90, 150))
SWATCHES = dict(case=(600, 740), key=(632, 740), red=(664, 740), monitor=(696, 740), dark=(728, 740), light=(760, 740),
                lit=(792, 740), floppy=(824, 740), cord=(856, 740))
MEDIA_REGIONS = dict(desktop=(0, 0, 512, 410), filer=(512, 0, 512, 410), game_1=(0, 416, 512, 410),
                     game_2=(512, 416, 512, 410))

FPS = 30
LENGTH = 240                 # 8 s


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return FRONT[0] + s * c - h * k, FRONT[1] + s * k + h * c


def row_s(row):
    """The middle (s) of a row: 0 the function row, then the main rows, half a row apart from it."""
    return ROW1 - (row + 0.5 if row else 0.0) * U


def keys():
    """Every key: (legend, x0, x1, s0, s1), its extent across and up the deck."""
    out = [(legend, KEYS_X0 + x * U, KEYS_X0 + (x + w) * U, row_s(0) - U / 2, row_s(0) + U / 2)
           for legend, x, w in FUNCTION]
    for r, row in enumerate(MAIN):
        x = 0.0
        for legend, w in row:
            if legend is not None:
                out.append((legend, KEYS_X0 + x * U, KEYS_X0 + (x + w) * U, row_s(r + 1) - U / 2,
                            row_s(r + 1) + U / 2))
            x += w
    for legend, x, row in CURSOR:
        out.append((legend, KEYS_X0 + x * U, KEYS_X0 + (x + 1) * U, row_s(row) - U / 2, row_s(row) + U / 2))
    for legend, x, row, tall in KEYPAD:
        w = 2.0 if legend == "0" else 1.0
        out.append((legend, KEYS_X0 + x * U, KEYS_X0 + (x + w) * U, row_s(row + tall - 1) - U / 2,
                    row_s(row) + U / 2))
    return out
