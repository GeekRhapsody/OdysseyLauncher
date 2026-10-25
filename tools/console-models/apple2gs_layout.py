"""The Apple IIGS set's measurements, shared by apple2gs_print.py (which draws its printing and screens) and apple2gs.py
(which builds it). Plain Python: Blender's Python imports it too.

The Apple IIGS (1986) in its platinum case, 290 x 349 x 115 mm (the Computer History Museum's 11 1/4 x 13 3/4 x 4 5/8
inches), its AppleColor RGB monitor on it (its screen 9 x 6 3/4 inches, the museum's), its Apple 3.5 Drive beside it
(121 x 210 x 56 mm, the museum's), and its ADB keyboard and mouse (57 x 95 x 36 mm; the museum's 2 1/4 x 3 3/4 x
1 1/2 inches) in front. Millimetres: x from the IIGS's middle (left to right), y back from its lip's front edge, z up
from the table. The rest was measured from photographs, scaled by the IIGS's width and the keys' standard pitch: on
Wikimedia Commons the set with its peripherals, the IIGS with its drive, the keyboard and mouse; on Deskthority the
keyboard from above and from its side.

The IIGS: a plinth with a sloping lip along its front (the power light at its right), the main box on it, Apple IIGS and
the rainbow apple at its front's left, grooves across its top from front to back and along its sides, and the seam
between its lid and its base rising along its sides to the back. The monitor: its deep front frame round the screen's
opening (the apple, the power switch), its housing behind (as far back as the IIGS goes, as photographs show it),
grooved along its sides and its top, three knobs in its right side. The drive: a low box, its slot high in its front
(the light at its left end, the eject button at its right, a label above it), its top grooved. The keyboard: a wedge,
the US layout's keys standing on it (KEYS: rows from the front, 5 the space bar's, to the back, 1 the digits'), a blank
column, the keypad at its right; a raised strip behind it with the apple and the power key. The mouse: a box rounded
at its back, its button at its front.

Two textures. `print` (ATLAS square, REGIONS): `keyboard` (the keyboard seen from above, its strip too: the key tops
and legends; mapped onto its faces facing up in its slope's frame), `front` (the IIGS's front face), `monitor` (the
monitor's front frame), `drive` (the drive's front), `mouse` (the mouse's top), and swatches. `media` (MEDIA_REGIONS):
the screens, each the glass's whole area (`check`, Check startup device! at rest; `boot`, GS/OS starting; `title` and
`game`, a made-up game, Odyssey), the disk's two sides. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

# -- The IIGS --------------------------------------------------------------------------------------------------------

WIDTH, DEPTH, HEIGHT = 290.0, 349.0, 115.0
PLINTH = dict(height=26.0, lip=34.0)          # the plinth; how far its lip runs in front of the main box
BOX = dict(y=(34.0, DEPTH), z=(22.0, HEIGHT), inset=0.5)
TOP_GROOVES = dict(count=30, width=2.6, depth=1.5, margin=12.0, y=(48.0, DEPTH - 8.0))
SIDE_GROOVES = dict(z=[98.0, 89.0, 80.0, 71.0], y=(60.0, DEPTH - 8.0), width=2.4, depth=1.4)
SEAM = dict(front=(BOX["y"][0], 26.0), back=(DEPTH, 60.0), width=1.6, depth=1.0)   # (y, z) where it starts and ends
LIGHT = (122.0, 14.0)                         # the power light on the lip: x, y

# -- The monitor -----------------------------------------------------------------------------------------------------

MONITOR = dict(width=290.0, height=270.0, frame=140.0, depth=306.0, back=(274.0, 258.0),   # the front frame (its depth);
                                                                                          # the housing behind it
               opening=dict(x=0.0, z=150.0, outer=(242.0, 196.0, 10.0), inner=(222.0, 172.0, 8.0), depth=22.0),
               glass=dict(size=(228.0, 176.0), bulge=7.0),
               switch=(118.0, 30.0), knobs=[193.0, 162.0, 141.0])   # the switch, x, z; the knobs in the right side, z
MONITOR_Y = BOX["y"][0] + 4.0                 # the monitor's front, on the IIGS

# -- The 3.5 drive ---------------------------------------------------------------------------------------------------

DRIVE = dict(size=(121.0, 210.0, 56.0), x=-WIDTH / 2 - 76.0, y=60.0, slot=(-47.0, 45.0, 36.5, 41.0),   # x0 x1 z0 z1
             eject=(48.0, 58.0, 36.0, 41.5), light=(-56.5, 38.75), label=(-59.0, -17.0, 43.0, 53.0))

# -- The keyboard and mouse ------------------------------------------------------------------------------------------

KEYBOARD = dict(width=380.0, depth=105.0, heights=(19.0, 29.0), at=(-20.0, -160.0))   # the case: its plan, its front
                                                                                    # and back heights, its middle
STRIP = dict(x=(-141.0, 136.0), depth=30.0, height=30.0)   # the raised strip behind the case
U, GAP = 19.05, 1.0
KEY_HEIGHT, KEY_INSET, WELL = 7.0, 2.0, 1.5
KEYS_X0 = -185.25                             # the main block's left edge, in the keyboard's frame (x from its middle)
ROW_S = {5: 6.0, 4: 6.0 + U, 3: 6.0 + 2 * U, 2: 6.0 + 3 * U, 1: 6.0 + 4 * U}   # each row's front edge, back from
                                                                               # the keyboard's front
PAD_U = 15.45                                 # the keypad's left edge, in units
BLANK = (14.5, PAD_U)                         # the blank column between the main block and the keypad, in units
POWER = dict(x=(-92.0, -54.0), s=(112.0, 128.0))   # the power key on the strip, s back from the keyboard's front
STRIP_APPLE = (-115.5, 120.0)


def kx(u):
    return KEYS_X0 + u * U


def key_rect(xu, row, wu, rows=1):
    """A key's base, (x0, s0, x1, s1) in the keyboard's frame (a tall key spans rows from row down)."""
    s0, s1 = ROW_S[row + rows - 1], ROW_S[row] + U
    return kx(xu) + GAP / 2, s0 + GAP / 2, kx(xu + wu) - GAP / 2, s1 - GAP / 2


def _row(names, x0, row, legends):
    return [(n, x0 + i, row, 1.0, legend) for i, (n, legend) in enumerate(zip(names, legends))]


# (name, x in units, row, width in units, legend[, rows]).
KEYS = (
    [("esc", 0.0, 1, 1.0, "esc")]
    + _row([f"d{k}" for k in "1234567890"] + ["minus", "equals"], 1.0, 1,
           ["!\n1", "@\n2", "#\n3", "$\n4", "%\n5", "^\n6", "&\n7", "*\n8", "(\n9", ")\n0", "_\n-", "+\n="])
    + [("delete", 13.0, 1, 1.5, "delete")]
    + [("tab", 0.0, 2, 1.5, "tab")]
    + _row(list("qwertyuiop") + ["lbracket", "rbracket"], 1.5, 2, list("QWERTYUIOP") + ["{\n[", "}\n]"])
    + [("control", 0.0, 3, 1.75, "control")]
    + _row(list("asdfghjkl") + ["semicolon", "quote"], 1.75, 3, list("ASDFGHJKL") + [":\n;", '"\n\''])
    + [("return", 12.75, 3, 1.75, "return"), ("return_top", 13.5, 2, 1.0, "")]
    + [("lshift", 0.0, 4, 2.25, "shift")]
    + _row(list("zxcvbnm") + ["comma", "period", "slash"], 2.25, 4, list("ZXCVBNM") + ["<\n,", ">\n.", "?\n/"])
    + [("rshift", 12.25, 4, 2.25, "shift")]
    + [("caps", 0.0, 5, 1.0, "caps\nlock"), ("option", 1.0, 5, 1.0, "option"), ("apple", 2.0, 5, 1.75, "⌘"),
       ("grave", 3.75, 5, 1.0, "~\n`"), ("space", 4.75, 5, 4.75, ""), ("backslash", 9.5, 5, 1.0, "|\n\\"),
       ("left", 10.5, 5, 1.0, "←"), ("right", 11.5, 5, 1.0, "→"), ("down", 12.5, 5, 1.0, "↓"),
       ("up", 13.5, 5, 1.0, "↑")]
    + _row(["clear", "np_eq", "np_slash", "np_star"], PAD_U, 1, ["clear", "=", "/", "*"])
    + _row(["np7", "np8", "np9", "np_plus"], PAD_U, 2, ["7", "8", "9", "+"])
    + _row(["np4", "np5", "np6", "np_minus"], PAD_U, 3, ["4", "5", "6", "−"])
    + _row(["np1", "np2", "np3"], PAD_U, 4, ["1", "2", "3"])
    + [("enter", PAD_U + 3.0, 4, 1.0, "enter", 2), ("np0", PAD_U, 5, 2.0, "0"), ("np_dot", PAD_U + 2.0, 5, 1.0, ".")]
)

MOUSE = dict(at=(240.0, -160.0), size=(57.0, 95.0, 36.0), button=36.0, turn=-6.0)

DISK = dict(size=(90.0, 94.0), thickness=3.3)   # a 3.5-inch disk: across, along (its shutter's end in first)

COLOURS = dict(case="#E2DED3", key="#DCD8CC", dark="#1A1A1C", glass="#FFFFFF", disk="#FFFFFF")

REGIONS = dict(keyboard=(0, 0, 1024, 364), front=(0, 376, 512, 164), monitor=(520, 376, 504, 469),
               drive=(0, 548, 300, 139), mouse=(312, 548, 120, 200))
SWATCHES = dict(green=(24, 732), dark=(88, 732), lit=(120, 732), case=(152, 732))

MEDIA_REGIONS = dict(check=(0, 0, 512, 395), boot=(512, 0, 512, 395), title=(0, 403, 512, 395),
                     game=(548, 670, 440, 340), disk_top=(512, 403, 248, 259), disk_bottom=(768, 403, 248, 259))
MEDIA_SWATCHES = dict(black=(24, 820), edge=(56, 820))

FPS = 30
LENGTH = 240                 # 8 s
