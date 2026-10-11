"""The Amstrad CPC 464's measurements, shared by amstrad_cpc_print.py (which draws its printing) and amstrad_cpc.py
(which builds it). Plain Python: Blender's Python imports it too.

Millimetres throughout, measured from the owner's photographs (the computer and its CTM644 colour monitor from the
front, and the datacorder's door open) and the computer's published size (about 572 x 168 x 70 mm).

The keyboard unit is a wedge: its front FRONT high, its top sloping up to SLOPE_TO (plan) at BACK high, then a ridge
RIDGE high with a row of vent teeth along it. Everything on the top is placed in the slope's own frame: x from the
unit's left end (0 to WIDTH), s up the slope from its front edge (0 to SLOPE_LENGTH), h off the slope. The print
atlas's `top` region is the slope seen square on, its back edge at the top: the keys' tops, the door's and the
datacorder's panel are all printed from it.
"""

import math

WIDTH, DEPTH = 572.0, 168.0
FRONT, BACK, RIDGE = 38.0, 56.0, 61.0
SLOPE_TO = 148.0                                  # where the slope meets the ridge's step (plan)
SLOPE = math.atan2(BACK - FRONT, SLOPE_TO)        # radians
SLOPE_LENGTH = math.hypot(SLOPE_TO, BACK - FRONT)

ATLAS = 2048
REGIONS = {
    "top": (0, 0, 2048, 534),        # the slope, WIDTH x SLOPE_LENGTH
    "cassette": (0, 544, 1024, 651),  # the cassette's top, CASSETTE[0] x CASSETTE[1]
    "hub": (1040, 544, 192, 192),     # a hub, its diameter HUB * 2
    "strip": (1040, 752, 1008, 82),   # the monitor's bezel under the screen, MONITOR strip
    "cassette_b": (0, 1210, 1024, 651),  # its bottom (side B), the tape's edge at the top
}
SCREEN_PX = (1024, 780)               # the glass's still (the boot screen), the video material's texture
VIDEO_PX = (640, 488)                 # the video's frames: the glass's proportions, even sides for H.264's 4:2:0

# The focused clip's timing, in frames at FPS, which the video (amstrad_cpc_video.py) follows frame for frame: it's as
# long as the clip, and the launcher restarts it when the clip loops.
FPS = 30
LENGTH = 270
EJECT = (12, 200)      # STOP/EJECT pressed: the door pops open to load, then to take the tape out
DOOR_SHUT = 80         # the door has shut on the cassette
PLAY = 104             # PLAY goes down (and stays down until the second eject)
ENTER = 112            # ENTER: "any key"
RESET = 250            # the cassette is out: the computer resets to its boot screen

# -- The keyboard ----------------------------------------------------------------------------------------------------
U = 19.0                              # the key pitch
GAP = 1.4                             # between neighbouring keys' bases
X0 = 47.0                             # ESC's left edge
KEY_HEIGHT = 9.0                      # a key's top above the slope
TOP_INSET = 2.4                       # a key's top inside its base, each side
ROWS = {r: 21.0 + (5 - r) * U for r in range(-1, 6)}  # each row's middle, up the slope: 5 is the space bar's

DIGITS = ["!\n1", '"\n2', "#\n3", "$\n4", "%\n5", "&\n6", "'\n7", "(\n8", ")\n9", "_\n0", "=\n-", "£\n^"]
QWERTY = list("QWERTYUIOP") + ["|\n@", "{\n["]
ASDF = list("ASDFGHJKL") + ["*\n:", "+\n;", "}\n]"]
ZXCV = list("ZXCVBNM") + ["<\n,", ">\n.", "?\n/", "`\n\\"]


def _keys():
    """(name, x in keys from X0, row, width in keys, rows tall, colour, legend: its lines, top first)."""
    keys = [("esc", 0, 1, 1, 1, "red", "ESC")]
    keys += [(f"k{t[-1]}", 1 + i, 1, 1, 1, "dark", t) for i, t in enumerate(DIGITS)]
    keys += [("clr", 13, 1, 1, 1, "dark", "CLR"), ("del", 14, 1, 1.25, 1, "green", "DEL")]
    keys += [("tab", -0.25, 2, 1.5, 1, "green", "TAB")]
    keys += [(f"k{t[-1]}", 1.25 + i, 2, 1, 1, "dark", t) for i, t in enumerate(QWERTY)]
    keys += [("enter", 13.25, 3, 2, 2, "blue", "ENTER")]
    keys += [("caps", -0.5, 3, 1.75, 1, "green", "CAPS\nLOCK")]
    keys += [(f"k{t[-1]}", 1.25 + i, 3, 1, 1, "dark", t) for i, t in enumerate(ASDF)]
    keys += [("shift_l", -0.6, 4, 2.25, 1, "green", "SHIFT")]
    keys += [(f"k{t[-1]}", 1.65 + i, 4, 1, 1, "dark", t) for i, t in enumerate(ZXCV)]
    keys += [("shift_r", 12.65, 4, 2.6, 1, "green", "SHIFT")]
    keys += [("space", 2.6, 5, 9.3, 1, "dark", ""), ("ctrl", 12.15, 5, 1.1, 1, "green", "CTRL")]
    # The cursor keys round COPY, behind the numeric pad, which lines up with rows 2 to 5.
    c = (16.25, 17.3, 18.35)
    keys += [("up", c[1], -1, 1, 1, "dark", "↑"), ("left", c[0], 0, 1, 1, "dark", "←"),
             ("copy", c[1], 0, 1, 1, "green", "COPY"), ("right", c[2], 0, 1, 1, "dark", "→"),
             ("down", c[1], 1, 1, 1, "dark", "↓")]
    pad = [["7", "8", "9"], ["4", "5", "6"], ["1", "2", "3"], ["0", ".", "ENTER"]]
    for r, row in enumerate(pad):
        for i, t in enumerate(row):
            keys.append((f"f{t}" if t != "ENTER" else "small_enter", c[i], 2 + r, 1, 1,
                         "blue" if t == "ENTER" else "dark", t))
    return keys


KEYS = _keys()


def key_rect(x, row, w, rows):
    """A key's base on the slope: (x0, s0, x1, s1)."""
    x0 = X0 + x * U + GAP / 2
    s1 = ROWS[row - rows + 1] + U / 2 - GAP / 2      # rows tall keys reach back over the rows behind
    return x0, ROWS[row] - U / 2 + GAP / 2, x0 + w * U - GAP, s1


NAVY = (30.0, 6.0, 344.0, 128.0)                 # the navy panel round the main keys: x0, s0, x1, s1
PAD = (352.0, 6.0, 418.0, 89.0)               # the numeric pad's dark surround

# -- The datacorder --------------------------------------------------------------------------------------------------
DECK = (421.0, 2.0, 555.0, 146.0)                # its area on the slope, outlined
DECK_KEYS = [("rec", "red", "REC"), ("play", "dark", "PLAY"), ("rew", "dark", "REW"),
             ("ffwd", "dark", "F.FWD"), ("eject", "dark", "STOP\nEJECT"), ("pause", "dark", "PAUSE")]
DECK_KEY = (430.0, 19.4, 18.2, 5.0, 19.0, 7.0)   # first key's left, pitch, width, front, back (s), height
SLOT = (427.0, 2.5, 549.0, 22.5, 14.0)           # the keys' slot: x0, s0, x1, s1, depth
PANEL = (424.0, 23.5, 552.0, 52.5)               # the printed panel between the keys and the door
DOOR = (423.0, 54.0, 551.0, 128.0, 3.0)          # the door: x0, s0, x1, s1 (its hinge), thickness
WINDOW = (436.0, 86.0, 538.0, 123.0)             # the hole in the door over the cassette
WELL = (425.0, 56.0, 549.0, 126.0, 19.0)         # the well under the door: x0, s0, x1, s1, depth
SPINDLES = (21.25, 1.9)                          # the reels' spindles, from the cassette's middle: x either way, s
SLIDER = (433.0, 133.0, 458.0, 141.0, 3.0)       # the slide switch behind the door

CASSETTE = (100.4, 63.8, 12.0)                   # a compact cassette: width, depth, thickness
HUB = 6.4                                        # a hub's radius
HUBS_FROM_TOP = 30.0                             # the hubs' middles, from the label's top (the cassette's back)

# -- The monitor (a CTM644), in the model's frame: front facing -Y, centred on its own x ------------------------------
MONITOR = dict(
    width=370.0, height=340.0, bezel=60.0, depth=330.0,
    opening=(332.0, 290.0),    # the screen's opening at the bezel's front
    inner=(286.0, 216.0),      # narrowing to this where it meets the glass
    screen_z=178.0,            # the screen's middle above the desk
    glass_back=36.0,           # the glass's edge, behind the bezel's front
    bulge=6.0,                 # the glass's middle this much in front of its edge
    strip=(18.0, 26.0),        # the printed band under the opening: its bottom and its height above the bezel's
    at=(-12.0, DEPTH + 14.0),  # where its front's middle stands, behind the keyboard
)
GLASS = (MONITOR["inner"][0] + 8.0, MONITOR["inner"][1] + 8.0)
RASTER = MONITOR["inner"]      # the lit raster: the glass but its hidden edge
PAPER = (0.80, 0.74)           # the CPC's paper (40 x 25 characters) inside its border, as fractions of the raster
