"""The Philips VG-8235's measurements, shared by msx2_print.py (which draws its printing) and msx2.py (which builds it).
Plain Python: Blender's Python imports it too.

The VG-8235 (1986), an MSX2, anthracite: its keyboard in front, the main unit behind it with the 3.5-inch drive in
its right end. No maker's dimensions were found (a seller's listing gives 43 x 30 x 10 cm), so the plan was measured
from photographs (msx.org's views of it from above, from the right and from behind, the Home Computer Museum's from
in front, Wikimedia Commons's from above and in front), scaled by its keys' 19.05 mm pitch: the keyboard 418 x 158 mm,
the main unit 384 x 127 mm. The heights are estimated from the views from in front and from the right. Millimetres: x
from its middle (left to right), y back from the keyboard's front edge, z up from the table.

The keyboard: its side outline (KB_PROFILE) extruded across its width, its corners rounded in plan; its front lip
over the set-back base, the handle's groove along its front, the deck rising gently to the back, gunmetal grey, the
ribbed grips at its ends, a LOCK slider at each end. The keys stand in wells (the /00's QWERTY layout, as the MSX1
model's VG-8020): the light grey letters and digits, the dark grey modifiers, the function and editing keys in a row
behind them, RETURN an inverted L, the four cursor keys round a square at the right, black with salmon arrows. A key
stands on the deck in the slope's frame (x across, s up the slope from the deck's front edge, h off it); deck_point()
maps a point of that frame to the model's (y, z).

The main unit: its side outline (MAIN_PROFILE) extruded across its width, darker; its top's vents at both ends, the
band along its front (RESET, the POWER, CAPS and FDD BUSY lights, the front cartridge slot's cover, PHILIPS), VG-8235,
the memory's lettering, the MSX2 badge and New Media Systems at its right. Its right end: the drive's black bezel, its
slot, its eject button and its light, and the two joystick ports under it.

One texture (ATLAS square, REGIONS): `top` (the whole top seen from above: the key tops and legends, the deck's grips
and LOCK labels, the main unit's printing and lights; planar-mapped onto every face facing up), `end` (the main unit's
right end: the joystick ports under the bezel), `disk_top` and `disk_bottom` (the 3.5-inch disk's sides: a made-up
game, Odyssey), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 418.0, 283.0, 70.0

# The keyboard's side outline, (y, z), anticlockwise seen from the right end: the base set back under the front lip,
# the deck rising from the lip to the main unit.
DECK = ((2.0, 30.0), (158.0, 42.0))                        # the deck's top: its front and back edges
SLOPE = math.atan2(DECK[1][1] - DECK[0][1], DECK[1][0] - DECK[0][0])
KB_PROFILE = [(5.0, 0.0), (DECK[1][0], 0.0), DECK[1], DECK[0], (0.0, 28.0), (0.0, 21.0), (5.0, 19.0)]
KB = dict(width=WIDTH, corner=14.0)

# The main unit: its outline across x0..x1, its top's front edge rounded.
MAIN = dict(x=(-192.0, 192.0), y=(156.0, DEPTH))
MAIN_PROFILE = [(MAIN["y"][0], 0.0), (DEPTH, 0.0), (DEPTH, HEIGHT - 3.0), (DEPTH - 3.0, HEIGHT),
                (MAIN["y"][0] + 5.0, HEIGHT), (MAIN["y"][0], HEIGHT - 5.0)]


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return DECK[0][0] + s * c - h * k, DECK[0][1] + s * k + h * c


# The keyboard: KEYS_X0 is the main block's left edge (ESC's), U a key's pitch, GAP between two keys. A key stands from
# the well's floor (WELL below the deck) to its top, KEY_HEIGHT above the deck, tapering by KEY_INSET on every side.
U, GAP = 19.05, 1.0
KEYS_X0 = -175.0
ROW_S = {5: 26.0, 4: 26.0 + U, 3: 26.0 + 2 * U, 2: 26.0 + 3 * U, 1: 26.0 + 4 * U}   # each row's front edge
FROW = (129.8, 13.3)                                       # the function keys' row: its front edge and depth
WELL, KEY_HEIGHT, KEY_INSET = 3.0, 9.5, 2.3


def kx(u):
    return KEYS_X0 + u * U


def key_rect(xu, row, wu):
    """A key's base, (x0, s0, x1, s1) in the slope's frame."""
    if row == 0:
        s0, s1 = FROW[0], FROW[0] + FROW[1]
    else:
        s0, s1 = ROW_S[row], ROW_S[row] + U
    return kx(xu) + GAP / 2, s0 + GAP / 2, kx(xu + wu) - GAP / 2, s1 - GAP / 2


def _row(names, x0, row, colour, legends):
    return [(n, x0 + i, row, 1.0, colour, legend) for i, (n, legend) in enumerate(zip(names, legends))]


FKEYS = (0.1, 1.34)                                        # the function keys: the first's x and their pitch, in units
EDIT = (8.4, 1.33, 1.25)                                   # the editing keys: the first's x, their pitch, their width

# (name, x in units, row, width in units, "light" or "dark", legend): a legend's line break splits its upper and lower
# characters. RETURN is an inverted L over rows 2 and 3 (RETURN below).
KEYS = (
    [(name, FKEYS[0] + FKEYS[1] * k, 0, FKEYS[1], "light", legend) for k, (name, legend) in
     enumerate([("f1", "F1-6"), ("f2", "F2-7"), ("f3", "F3-8"), ("f4", "F4-9"), ("f5", "F5-10")])]
    + [(name, EDIT[0] + EDIT[1] * k, 0, EDIT[2], "light", legend) for k, (name, legend) in
       enumerate([("select", "SELECT"), ("stop", "STOP"), ("home", "CLR HOME"), ("ins", "INS"), ("del", "DEL")])]
    + [("esc", 0.0, 1, 1.0, "dark", "ESC")]
    + _row([f"d{k}" for k in "1234567890"] + ["minus", "equals", "backslash"], 1.0, 1, "light",
           ["!\n1", "@\n2", "#\n3", "$\n4", "%\n5", "^\n6", "&\n7", "*\n8", "(\n9", ")\n0", "_\n-", "+\n=", "|\n\\"])
    + [("bs", 14.0, 1, 1.0, "dark", "BS\n←")]
    + [("tab", -0.1, 2, 1.6, "dark", "TAB")]
    + _row(list("qwertyuiop") + ["lbracket", "rbracket"], 1.5, 2, "light", list("QWERTYUIOP") + ["{\n[", "}\n]"])
    + [("ctrl", -0.2, 3, 1.95, "dark", "CTRL")]
    + _row(list("asdfghjkl") + ["semicolon", "quote", "grave"], 1.75, 3, "light",
           list("ASDFGHJKL") + [":\n;", '"\n\'', "~\n`"])
    + [("lshift", -0.3, 4, 2.3, "dark", "↑")]
    + _row(list("zxcvbnm") + ["comma", "period", "slash"], 2.0, 4, "light", list("ZXCVBNM") + ["<\n,", ">\n.", "?\n/"])
    + [("rshift", 12.0, 4, 2.0, "dark", "↑"), ("dead", 14.0, 4, 1.0, "dark", "` ¨\n´ ^")]
    + [("caps", 2.0, 5, 1.0, "dark", "⇧"), ("grph", 3.0, 5, 1.0, "dark", "GRPH"),
       ("space", 4.0, 5, 8.25, "light", ""), ("code", 12.25, 5, 1.0, "dark", "CODE")]
)
RETURN = dict(top=(14.0, 15.0), bottom=(13.75, 15.0))      # its two rows' x, in units: row 3's part is the wider


def return_outline():
    """RETURN's base, an (x, s) outline anticlockwise from its front left corner."""
    (a, b), (c, _) = RETURN["top"], RETURN["bottom"]
    g = GAP / 2
    s3, s2, s1 = ROW_S[3] + g, ROW_S[2] + g, ROW_S[2] + U - g
    return [(kx(c) + g, s3), (kx(b) - g, s3), (kx(b) - g, s1), (kx(a) + g, s1), (kx(a) + g, s2), (kx(c) + g, s2)]


# The cursor keys: a square well, and in it four wedges round a square (the square a dark plug), each wedge's outer
# edge on the cluster's outline.
CURSOR = dict(well=(126.0, 189.0, 42.5, 102.8), outer=(61.0, 58.3), inner=(20.0, 18.0), gap=1.4, height=8.5)


def cursor_middle():
    x0, x1, s0, s1 = CURSOR["well"]
    return (x0 + x1) / 2, (s0 + s1) / 2


def inset(outline, d):
    """A closed outline moved in by d, whichever way round it runs: each edge moved in along its normal, the corners
    where they meet."""
    if sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, list(outline[1:]) + [outline[0]])) < 0:
        d = -d                                           # clockwise: its left, where the normals point, is outside
    n = len(outline)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % n]
        length = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / length, (x1 - x0) / length
        lines.append(((x0 + nx * d, y0 + ny * d), (x1 - x0, y1 - y0)))
    points = []
    for i in range(n):
        (p, r), (q, s) = lines[i - 1], lines[i]
        t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / (r[0] * s[1] - r[1] * s[0])
        points.append((p[0] + r[0] * t, p[1] + r[1] * t))
    return points


def cursor_outline(name):
    """A cursor key's base, an (x, s) outline anticlockwise: the wedge between the cluster's outline and the square,
    on its side, moved in to open the gaps along the diagonals."""
    cx, cs = cursor_middle()
    (ow, od), (iw, idp) = CURSOR["outer"], CURSOR["inner"]
    outer = [(cx - ow / 2, cs - od / 2), (cx + ow / 2, cs - od / 2), (cx + ow / 2, cs + od / 2), (cx - ow / 2, cs + od / 2)]
    inner = [(cx - iw / 2, cs - idp / 2), (cx + iw / 2, cs - idp / 2), (cx + iw / 2, cs + idp / 2),
             (cx - iw / 2, cs + idp / 2)]
    k = {"down": 0, "right": 1, "up": 2, "left": 3}[name]
    return inset([outer[k], outer[(k + 1) % 4], inner[(k + 1) % 4], inner[k]], CURSOR["gap"] / 2)


def wells():
    """The wells the keys stand in, each an (x, s) outline: the main block (stepped at its left, its bottom row short),
    the function keys', the editing keys', and the cursor keys'."""
    m = 0.8
    s5, s4, s3, s2, s1, top = ROW_S[5], ROW_S[4], ROW_S[3], ROW_S[2], ROW_S[1], ROW_S[1] + U

    def rect(x0, x1, a, b):
        return [(x0, a), (x1, a), (x1, b), (x0, b)]
    x0, x1, c0, c1 = CURSOR["well"]
    f0, f1 = FROW[0] - m, FROW[0] + FROW[1] + m
    return [
        [(kx(2.0) - m, s5 - m), (kx(13.25) + m, s5 - m), (kx(13.25) + m, s4), (kx(15.0) + m, s4),
         (kx(15.0) + m, top + m), (kx(0.0) - m, top + m), (kx(0.0) - m, s1), (kx(-0.1) - m, s1), (kx(-0.1) - m, s2),
         (kx(-0.2) - m, s2), (kx(-0.2) - m, s3), (kx(-0.3) - m, s3), (kx(-0.3) - m, s4), (kx(2.0) - m, s4)],
        rect(kx(FKEYS[0]) - m, kx(FKEYS[0] + 5 * FKEYS[1]) + m, f0, f1),
        rect(kx(EDIT[0]) - m, kx(EDIT[0] + 4 * EDIT[1] + EDIT[2]) + m, f0, f1),
        rect(x0, x1, c0, c1),
    ]


# The deck's ends: the ribbed grips and the LOCK sliders (each a slot, its knob at the slot's front), in the slope's
# frame; the handle's groove along the front, in the model's plan (x, y).
GRIPS = dict(x=[(-208.0, -184.0), (192.0, 208.0)], s=(42.0, 98.0), pitch=1.6)
LOCKS = dict(x=[(-193.9, -182.2), (191.0, 202.7)], s=(103.0, 122.0), knob=8.0, label=125.5)
HANDLE = dict(x=(-59.4, 65.3), y=(3.0, 21.0), floor=26.5)

# The main unit's top, in the model's plan (x, y): the vents, the band's seam, RESET, the lights, the cartridge
# slot's cover, the PHILIPS plate, and the printing at its right.
VENTS = [dict(x=(-154.3, -97.7), count=16), dict(x=(78.4, 105.2), count=8)]
VENT_Y, VENT_WIDTH, VENT_DEPTH = (215.0, 279.0), 1.9, 2.0
BAND = 204.8                                               # the seam behind the band along the front
RESET = dict(x=(-182.6, -159.0), y=(183.6, 197.8), height=1.6)
LIGHTS = dict(power=(-148.8, 192.4), caps=(-136.2, 192.4), fdd=(-125.2, 192.4), size=(7.9, 4.6), names=199.5)
CART_COVER = dict(x=(-81.9, 26.6), y=(182.0, 199.4))
PHILIPS = dict(x=(131.3, 171.2), y=(188.4, 196.2))
MODEL = dict(x=114.6, y=265.6, height=6.0)                 # VG-8235: its left edge, its middle, its height
LETTERING = dict(x=114.8, y=(259.6, 256.9, 254.2), height=1.9,
                 lines=("64K ROM", "256K RAM", "360K DISK DRIVE CAPACITY"))
MSX_BADGE = dict(x=(116.2, 126.6), y=(243.6, 248.3))
SHIELD = dict(x=170.4, y=264.0, height=9.0)
PUZZLE = dict(x=(150.8, 166.5), y=(215.0, 231.0))
NMS = dict(x=179.0, y=211.3, height=4.6)                   # New Media Systems: its right edge, its middle, its height

# The right end: the drive's bezel (proud of the end by BEZEL["out"]), its slot, eject button and light; the joystick
# ports under it. (y, z) on the end.
BEZEL = dict(y=(163.0, 277.0), z=(20.0, 64.0), out=0.6)
SLOT = dict(y=(167.0, 263.0), z=(36.5, 41.0))
EJECT = dict(y=(170.0, 186.0), z=(27.0, 32.0), out=2.0)
DRIVE_LIGHT = dict(y=(264.0, 271.0), z=(56.5, 59.0))
PORTS = dict(y=[(181.0, 203.0), (225.0, 247.0)], z=(5.0, 16.0))

# The disk: a 3.5-inch disk, lying flat, its shutter's end in first (towards -x); SEAT its middle in the drive.
DISK = dict(size=(90.0, 94.0), thickness=3.3)
SEAT = (MAIN["x"][1] - DISK["size"][1] / 2 - 4.0, (SLOT["y"][0] + SLOT["y"][1]) / 2, (SLOT["z"][0] + SLOT["z"][1]) / 2)

COLOURS = dict(case="#3C3D40", deck="#6C6D71", key_light="#ABA594", key_dark="#3E3F42", black="#141416",
               top_light="#B4AE9D", top_dark="#46474A")

REGIONS = dict(top=(0, 0, 1024, 693), end=(0, 701, 312, 172), disk_top=(320, 701, 180, 188),
               disk_bottom=(508, 701, 180, 188))
SWATCHES = dict(red=(720, 716), green=(752, 716), amber=(784, 716), black=(816, 716), red_off=(848, 716))

FPS = 30
LENGTH = 240                 # 8 s
