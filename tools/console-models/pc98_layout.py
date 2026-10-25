"""The PC-98 set's measurements, shared by pc98_print.py (which draws its printing and screens) and pc98.py (which builds
it). Plain Python: Blender's Python imports it too.

An NEC PC-9801VM (1985), the PC-98 most played, its colour monitor on it and its keyboard in front. Millimetres: x from
the system unit's middle (left to right), y back from its front face, z up from the table. The system unit's front was
measured from a photograph of a VM on Wikimedia Commons, scaled by its two 5.25-inch drives' bezels (146 x 41.3 mm
each, the drives' standard): 420 mm across, 130 mm high; its depth is the VM11's that followed it, 335 mm (Impress's
retro-PC column). The keyboard was measured from a photograph of a PC-9800 series keyboard on Wikimedia Commons, scaled
by its keys' 19.05 mm pitch (437 x 180 mm); the monitor follows the NEC display in a photograph of a PC-9801 set there
(its black bezel, its knobs at the right), 14 inches.

The system unit: its front (NEC PC-9801VM and PERSONAL COMPUTER at the top left, the brown band sloping down to the
grille, the two drives at the right, each its bezel, its slot, its turning lever and its light; POWER at the bottom
right). The monitor: its beige housing, its black bezel round the screen's opening, NEC at its top right, three knobs
down its right. The keyboard (KEYS, measured: each key's middle, its width, its row): the function keys, the main block,
the tall RETURN, the editing keys and the keypad, in two greys; NEC PC-9800 SERIES at its back right.

Two textures. `print` (ATLAS square, REGIONS): `keyboard` (the keyboard from above: the key tops and their legends),
`front` (the system unit's front), `bezel` (the monitor's front), and swatches. `media` (MEDIA_REGIONS): the screens,
each the glass's whole area (`memory`, the start-up memory check; `title` and `game`, a made-up game, Odyssey), the
5.25-inch floppy's two sides. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 420.0, 335.0, 130.0
FEET = 6.0
FRONT_Z = (FEET, HEIGHT)                            # the front face, above the feet
DRIVES = dict(x=(43.0, 189.0), z=[(80.0, 121.3), (38.0, 79.3)], slot=(-66.0, 66.0, 18.0, 22.0),   # each bezel; the
              lever=(52.0, 31.0, 30.0, 7.0, 4.0), light=(-58.0, 34.0))   # slot, the lever (pivot x, z; length, width,
                                                                         # out) and the light, in the bezel's frame
LOGO = dict(at=(-196.0, 103.0), height=11.0)        # its left edge, its middle
GRILLE = dict(x=(-196.0, 34.0), z=(20.0, 64.0), slots=13)
BAND = dict(z=(66.0, 74.0), slope_x=(-10.0, 34.0))  # the brown band over the grille, sloping up at its right end
POWER = dict(x=(176.0, 196.0), z=(12.0, 30.0), out=3.0)

# The monitor: its front bezel (w x h, its foot raised on its stand), the opening and the glass, its housing.
MONITOR = dict(width=350.0, height=320.0, stand=14.0, frame=28.0, depth=290.0, back=(300.0, 270.0), y=22.0,
               opening=dict(x=-20.0, z=176.0, outer=(270.0, 212.0, 14.0), inner=(250.0, 192.0, 10.0), depth=22.0),
               glass=(256.0, 198.0), bulge=7.0, knobs=[(144.0, 236.0), (144.0, 196.0), (144.0, 156.0)], knob_r=9.0,
               light=(144.0, 270.0))

# The keyboard: its plan (w x d, its middle), its front and back heights. Keys as measured from the photograph: each
# (name, x of its middle and width in the photograph's pixels, row, legend[, rows]); PX_MM pixels a millimetre, the
# keyboard's left edge at PX0.
KEYBOARD = dict(width=437.0, depth=180.0, heights=(24.0, 34.0), at=(-6.0, -128.0))
PX_MM, PX0 = 4.3, 20.0
ROW_S = {0: 140.5, 1: 111.4, 2: 91.2, 3: 71.4, 4: 51.4, 5: 31.6}   # each row's middle, back from the keyboard's front
KEY_DEPTH = {0: 15.0}                                              # the function row's keys are shallower
KEY, GAP = 17.0, 1.6
KEY_HEIGHT, KEY_INSET, WELL = 7.0, 2.0, 1.5
_F = [("stop", 98, 80, "STOP"), ("copy", 200, 80, "COPY")] + \
     [(f"f{k + 1}", 300 + 105 * k, 95, f"f·{k + 1}") for k in range(5)] + \
     [(f"f{k + 6}", 840 + 107 * k, 95, f"f·{k + 6}") for k in range(5)] + \
     [(f"vf{k + 1}", 1408 + 105 * k, 95, f"vf·{k + 1}") for k in range(5)]
_R1 = [("esc", 93, 78, "ESC")] + [(f"d{c}", 178 + 82.5 * k, 76, c) for k, c in enumerate("1234567890-^¥")] + \
      [("bs", 1305, 92, "BS"), ("ins", 1400, 76, "INS"), ("del", 1485, 76, "DEL"), ("home", 1592, 76, "HOME\nCLR"),
       ("help", 1675, 76, "HELP"), ("np_minus", 1757, 76, "−"), ("np_slash", 1840, 76, "/")]
_R2 = [("tab", 117, 118, "TAB")] + [(c.lower(), 225 + 82.5 * k, 76, c) for k, c in enumerate("QWERTYUIOP@[")] + \
      [("rollup", 1400, 76, "ROLL\nUP"), ("rolldown", 1485, 76, "ROLL\nDOWN")] + \
      [(f"np{c}", 1592 + 82.5 * k, 76, c) for k, c in enumerate("789")] + [("np_star", 1840, 76, "*")]
_R3 = [("ctrl", 85, 76, "CTRL"), ("caps", 167, 76, "CAPS")] + \
      [(f"k{c}", 250 + 82.5 * k, 76, c) for k, c in enumerate("ASDFGHJKL;:]")] + [("up", 1442, 160, "↑")] + \
      [(f"np{c}", 1592 + 82.5 * k, 76, c) for k, c in enumerate("456")] + [("np_plus", 1840, 76, "+")]
_R4 = [("lshift", 150, 190, "SHIFT")] + [(f"k{c}", 290 + 82.5 * k, 76, c) for k, c in enumerate("ZXCVBNM,./_")] + \
      [("rshift", 1270, 160, "SHIFT"), ("left", 1400, 76, "←"), ("right", 1485, 76, "→")] + \
      [(f"np{c}", 1592 + 82.5 * k, 76, c) for k, c in enumerate("123")] + [("np_eq", 1840, 76, "=")]
_R5 = [("kana", 250, 76, "カナ"), ("grph", 330, 76, "GRPH"), ("nfer", 433, 108, "NFER"), ("space", 775, 545, ""),
       ("xfer", 1120, 108, "XFER"), ("down", 1442, 160, "↓"), ("np0", 1592, 76, "0"), ("np_comma", 1675, 76, ","),
       ("np_dot", 1757, 76, "."), ("np_enter", 1840, 76, "↵")]
KEYS = ([(n, x, w, 0, legend) for n, x, w, legend in _F] + [(n, x, w, 1, legend) for n, x, w, legend in _R1]
        + [(n, x, w, 2, legend) for n, x, w, legend in _R2] + [(n, x, w, 3, legend) for n, x, w, legend in _R3]
        + [(n, x, w, 4, legend) for n, x, w, legend in _R4] + [(n, x, w, 5, legend) for n, x, w, legend in _R5]
        + [("return", 1290, 100, 2, "↲", 2)])
DARK_KEYS = {"stop", "copy", "esc", "bs", "tab", "ctrl", "caps", "lshift", "rshift", "kana", "grph", "nfer", "xfer",
             "return", "ins", "del", "rollup", "rolldown", "up", "down", "left", "right", "home", "help", "np_minus",
             "np_slash", "np_star", "np_plus", "np_eq", "np_enter"} | {f"f{k}" for k in range(1, 11)} | \
            {f"vf{k}" for k in range(1, 6)}


def key_rect(x_px, w_px, row, rows=1):
    """A key's base, (x0, s0, x1, s1) in the keyboard's frame (x from its middle, s up from its front edge)."""
    xm = (x_px - PX0) / PX_MM - KEYBOARD["width"] / 2
    w = w_px / PX_MM - GAP
    d = KEY_DEPTH.get(row, KEY)
    s0 = ROW_S[row + rows - 1] - d / 2
    s1 = ROW_S[row] + d / 2
    return xm - w / 2, s0, xm + w / 2, s1


# The 5.25-inch floppy: its size, its thickness; where it sits in drive 1 (its middle).
DISK = dict(size=133.0, thickness=2.0)

COLOURS = dict(case="#DDD5BF", key_light="#D6D1C3", key_dark="#8E918E", dark="#1A1A1C", glass="#FFFFFF",
               disk="#FFFFFF")

REGIONS = dict(keyboard=(0, 0, 1024, 422), front=(0, 430, 1024, 302), bezel=(0, 740, 310, 284))
SWATCHES = dict(red=(340, 760), red_off=(372, 760), green=(404, 760), dark=(436, 760), lever=(468, 760),
                brown=(500, 760))

SCREEN_PX = (512, 395)
MEDIA_REGIONS = dict(memory=(0, 0) + SCREEN_PX, title=(512, 0) + SCREEN_PX, game=(0, 403) + SCREEN_PX,
                     disk_top=(512, 403, 248, 248), disk_bottom=(768, 403, 248, 248))
MEDIA_SWATCHES = dict(black=(24, 820), edge=(56, 820))

FPS = 30
LENGTH = 240                 # 8 s
