"""The Philips VG-8020's measurements, shared by msx_print.py (which draws its printing) and msx.py (which builds it).
Plain Python: Blender's Python imports it too.

The VG-8020/00 (1984), an MSX: 405 x 220 x 65 mm (the Museo degli Strumenti per il Calcolo's record, its power switch
included; the case is 401 mm across). Millimetres: x from its middle (left to right), y back from its front edge, z up
from the table. The rest was measured from photographs (the Home Computer Museum's views of it from above and in
front, valoroso.it's views of its ends and of its front's joystick ports, msx.org's view of its insides), scaled by
its width and by its keys' 19.05 mm pitch.

Three shells. The base, light grey, its lower band tapering in to the feet, the joystick ports in a recess in its front
at the left. The keyboard deck over it, dark grey: a low front edge, the top rising gently to the back. The raised back,
silver: PHILIPS, the memory's lettering and the MSX badge, the POWER and CAPS lights; its left part is a black lid,
hinged along its back edge, over the two cartridge slots. The power switch is a rocker in the right end.

The keyboard is the /00's (QWERTY). Its keys are laid out in units of U from the main block's left edge (KEYS_X0), in
rows from the front (row 5, the space bar's) to the back (row 1, the digits'), with the function keys behind them as
row 0. The deck is a plane at SLOPE: a key stands on it in the slope's frame (x across, s up the slope from the deck's
front edge, h off it), and deck_point() maps a point of that frame to the model's (y, z). The cursor keys are four
wedges round a square, in a well of their own at the right.

One texture (ATLAS square, REGIONS): `top` (the whole top seen from above: the key tops and their legends, the raised
back's printing and lights, the lid's VG-8020; planar-mapped onto every face facing up), `ports` (the joystick
recess's back face), `label` (the cartridge's: a made-up game, Odyssey), `rocker` (the power switch's face), and
swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 401.0, 220.0, 65.0

# The shells' side outlines, (y, z), anticlockwise seen from the right end.
SEAM = 22.0                                                # the base's top, where the deck and the raised back sit
DECK = ((3.0, 36.0), (143.0, 49.0))                        # the deck's top: its front and back edges
SLOPE = math.atan2(DECK[1][1] - DECK[0][1], DECK[1][0] - DECK[0][0])
BACK_Y = DECK[1][0]                                        # the raised back's front face
DECK_PROFILE = [(0.0, SEAM), (BACK_Y, SEAM), DECK[1], DECK[0], (0.0, 33.5)]
BACK_PROFILE = [(BACK_Y, SEAM), (DEPTH, SEAM), (DEPTH, HEIGHT - 4.0), (DEPTH - 4.0, HEIGHT), (BACK_Y + 2.0, HEIGHT),
                (BACK_Y, HEIGHT - 2.0)]
BASE = dict(band=11.0, inset=1.5, foot=(9.5, 7.0))         # the lower band's top; the base's inset; at its foot, the
                                                           # inset at the front and back, and at the ends


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return DECK[0][0] + s * c - h * k, DECK[0][1] + s * k + h * c


# The keyboard: KEYS_X0 is the main block's left edge, U a key's pitch, GAP between two keys. A key stands from the
# well's floor (WELL below the deck) to its top, KEY_HEIGHT above the deck, tapering by KEY_INSET on every side.
U, GAP = 19.05, 1.0
KEYS_X0 = -179.3
ROW_S = {5: 14.5, 4: 33.55, 3: 52.6, 2: 71.65, 1: 90.7}   # each row's front edge, up the slope
FROW = (111.0, 16.5)                                       # the function keys' row: its front edge and depth
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


# (name, x in units, row, width in units, "light" or "dark", legend): a legend's line break splits its upper and lower
# characters. RETURN is an inverted L over rows 2 and 3 (RETURN below).
KEYS = (
    [(name, 1.5 * k, 0, 1.5, "dark", legend) for k, (name, legend) in
     enumerate([("f1", "F1-6"), ("f2", "F2-7"), ("f3", "F3-8"), ("f4", "F4-9"), ("f5", "F5-10"), ("select", "SELECT"),
                ("stop", "STOP")])]
    + [("home", 15.7, 0, 1.0, "dark", "CLR\nHOME"), ("ins", 16.7, 0, 1.0, "dark", "INS"),
       ("del", 17.7, 0, 1.0, "dark", "DEL")]
    + [("esc", 0.0, 1, 1.0, "dark", "ESC")]
    + _row([f"d{k}" for k in "1234567890"] + ["minus", "equals", "backslash"], 1.0, 1, "light",
           ["!\n1", "@\n2", "#\n3", "$\n4", "%\n5", "^\n6", "&\n7", "*\n8", "(\n9", ")\n0", "_\n-", "+\n=", "|\n\\"])
    + [("bs", 14.0, 1, 1.0, "dark", "BS\n←")]
    + [("tab", 0.0, 2, 1.5, "dark", "TAB")]
    + _row(list("qwertyuiop") + ["lbracket", "rbracket"], 1.5, 2, "light", list("QWERTYUIOP") + ["{\n[", "}\n]"])
    + [("ctrl", 0.0, 3, 1.75, "dark", "CTRL")]
    + _row(list("asdfghjkl") + ["semicolon", "quote", "grave"], 1.75, 3, "light",
           list("ASDFGHJKL") + [":\n;", '"\n\'', "~\n`"])
    + [("lshift", 0.0, 4, 2.25, "dark", "↑")]
    + _row(list("zxcvbnm") + ["comma", "period", "slash"], 2.25, 4, "light", list("ZXCVBNM") + ["<\n,", ">\n.", "?\n/"])
    + [("rshift", 12.25, 4, 1.75, "dark", "↑"), ("dead", 14.0, 4, 1.0, "dark", "` ¨\n´ ^")]
    + [("caps", 2.25, 5, 1.0, "dark", "⇧"), ("grph", 3.25, 5, 1.0, "dark", "GRPH"),
       ("space", 4.25, 5, 8.0, "light", ""), ("code", 12.25, 5, 1.0, "dark", "CODE")]
)
RETURN = dict(top=(13.5, 15.0), bottom=(13.75, 15.0))      # its two rows' x, in units: row 2's part is the wider


def return_outline():
    """RETURN's base, an (x, s) outline anticlockwise from its front left corner."""
    (a, b), (c, _) = RETURN["top"], RETURN["bottom"]
    g = GAP / 2
    s3, s2, s1 = ROW_S[3] + g, ROW_S[2] + g, ROW_S[2] + U - g
    return [(kx(c) + g, s3), (kx(b) - g, s3), (kx(b) - g, s1), (kx(a) + g, s1), (kx(a) + g, s2), (kx(c) + g, s2)]


# The cursor keys: a well, and in it four wedges round a square (the square a dark plug), each wedge's outer edge on
# the cluster's outline.
CURSOR = dict(well=(117.2, 180.6, ROW_S[4], ROW_S[1]), outer=(59.0, 53.0), inner=(19.0, 17.0), gap=1.4, height=8.0)


def cursor_middle():
    x0, x1, s0, s1 = CURSOR["well"]
    return (x0 + x1) / 2, (s0 + s1) / 2


def inset(outline, d):
    """An anticlockwise outline moved in by d: each edge moved in along its normal, the corners where they meet."""
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
    """The wells the keys stand in, each an (x, s) outline: the main block (its bottom row short) with the function
    keys' row behind it, the editing keys, and the cursor keys'."""
    m = 1.0
    s5, s4, s1, f1 = ROW_S[5] - m, ROW_S[4], ROW_S[1] + U, FROW[0] + FROW[1] + m

    def rect(x0, x1, a, b):
        return [(x0, a), (x1, a), (x1, b), (x0, b)]
    x0, x1 = CURSOR["well"][:2]
    return [
        [(kx(2.25) - m, s5), (kx(13.25) + m, s5), (kx(13.25) + m, s4), (kx(15) + m, s4), (kx(15) + m, s1),
         (kx(10.5) + m, s1), (kx(10.5) + m, f1), (kx(0) - m, f1), (kx(0) - m, s4), (kx(2.25) - m, s4)],
        rect(kx(15.7) - m, kx(18.7) + m, FROW[0] - m, f1),
        rect(x0, x1, CURSOR["well"][2], CURSOR["well"][3]),
    ]


# The raised back's printing, in the top's (x, y): Philips's shield, PHILIPS, the memory's lettering and the MSX badge
# under it, the rule along to the lights, the lights' windows and their names.
SHIELD = dict(x=-150.5, y=209.0, height=9.0)
PHILIPS = dict(x=-9.8, y=210.0, height=6.2)                # its left edge, its middle, its capitals' height
LETTERING = dict(x=-9.3, y=(167.8, 163.9, 160.0), height=2.4, lines=("80K RAM", "32K ROM", "EXPANDABLE  SYSTEM"))
MSX_BADGE = dict(x=(-9.3, 2.5), y=(150.0, 155.0))
RULE = dict(x=(33.0, 149.0), y=157.6)
LIGHTS = dict(power=(163.9, 159.0), caps=(182.2, 159.0), size=(5.0, 2.2), names=155.3)

# The lid over the cartridge slots: across the raised back's top from its front face to its back edge, its front edge
# bent down over the front face to the deck. It turns about its hinge, along its back edge.
LID = dict(x=(-145.5, -13.9), thickness=3.0, flange=DECK[1][1] + 0.4, hinge=(DEPTH - 1.0, HEIGHT - 1.5), open=-104.0)
LID_PRINT = dict(x=-17.8, y=161.5, height=5.6, rule=(-141.3, 157.8), small=2.4, lines=(154.6, 151.2))

# The slots under it: two, one behind the other, each a cartridge's section; the floor between them under the lid.
SLOTS = dict(x=(-135.2, -24.2), y=[(153.6, 171.2), (172.7, 190.3)], floor=HEIGHT - 3.0, bottom=28.0)

# The cartridge: w x d x h, standing in the front slot (SEAT, its bottom's middle); its label on its front, beside
# the ribbed grip at its left.
CART = dict(size=(109.0, 17.0, 90.0), label=(86.0, 72.0), grip=(4.0, 18.0), ribs=7)
SEAT = ((SLOTS["x"][0] + SLOTS["x"][1]) / 2, (SLOTS["y"][0][0] + SLOTS["y"][0][1]) / 2, 30.0)

# The joystick ports in a recess in the base's front at the left; the power switch in the right end.
PORTS = dict(x=(-166.7, -89.2), z=(0.0, 19.0), depth=8.5, at=(-145.7, -111.1), port_z=13.0, port=(21.0, 10.0))
SWITCH = dict(y=(124.0, 142.0), z=(12.0, 27.0), out=3.0)

COLOURS = dict(base="#B4B2A9", deck="#2F3033", silver="#C5C6C4", key_light="#9A988E", key_dark="#3B3C40",
               black="#0E0E10", top_light="#A6A49A", top_dark="#46474C")

REGIONS = dict(top=(0, 0, 1024, 563), ports=(0, 572, 400, 98), label=(408, 572, 344, 288), rocker=(760, 572, 90, 75))
SWATCHES = dict(red=(784, 680), green=(816, 680), black=(848, 680), red_off=(880, 680), green_off=(912, 680))

FPS = 30
LENGTH = 240                 # 8 s
