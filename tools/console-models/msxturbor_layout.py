"""The MSX turbo R card's measurements, shared by msxturbor_print.py (which draws its printing) and msxturbor.py (which
builds it). Plain Python: Blender's Python imports it too.

Panasonic's FS-A1GT (1991), an MSX turbo R, mid grey. No maker's figure was found; it is about 395 x 258 x 80 mm, scaled
by its keys' 19.05 mm pitch in a photograph of it from above (its legends readable), the rest measured from photographs
of it from each end, from behind and in front. Millimetres: x from its middle (left to right), y back from its front
edge, z up from the table.

Its side outline (PROFILE): the keyboard's deck rising gently from the thin front edge to the glossy black band, which
slopes up to the rear block's rounded nose and flat top, a comb of grooves along its back edge. The keys stand in wells in
the deck (the JIS layout, in msx2.py's manner: KEYS, in units U from KEYS_X0, in rows from the function keys' at the back
to the space bar's at the front; RETURN an L; the MSX VIEW badge in the bottom row's place at the left; the numeric
keypad at the right, its top row level with the function keys', the cursor keys round a square under it, reaching in
front of the bottom row), the letters and digits light grey, the rest mid grey. The black band (BAND) is a strip of its
own on the slope, a little proud of it and past the ends: ribbed along its upper half; along its lower half the A1GT
logo, the autofire button, its rate slider, the built-in software switch, RESET, PCM, MIDI, MIC and the six lights
(power, CAPS, kana, PAUSE, R800 mode, FDD IN USE) over their names. On the rear block's top: DOUBLE SLOTS and slot 1's
lid, PERSONAL COMPUTER FS-A1GT, the MSX turbo R mark and the rest, FDD at the right end; the 3.5-inch drive in the right
end, its slot running back from the band's foot, the joystick ports under it and in the deck's end; Panasonic on the
deck's front.

One texture (ATLAS square, REGIONS): `top` (the whole top seen from above: the key tops and legends, the deck's and the
rear block's printing; planar-mapped onto every face facing up), `band` (the black band, along its slope), `disk_top`
and `disk_bottom` (the 3.5-inch disk's sides: a made-up game), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

from msx2_layout import inset

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 395.0, 258.0, 80.0
HALF = WIDTH / 2

DECK = ((5.0, 23.0), (168.0, 42.0))                        # the deck's top: its front and back edges (y, z)
SLOPE = math.atan2(DECK[1][1] - DECK[0][1], DECK[1][0] - DECK[0][0])
BAND = ((170.0, 44.0), (199.0, 72.0))                      # the band's slope: its foot and its top (y, z)
BAND_SLOPE = math.atan2(BAND[1][1] - BAND[0][1], BAND[1][0] - BAND[0][0])
BAND_LENGTH = math.hypot(BAND[1][0] - BAND[0][0], BAND[1][1] - BAND[0][1])
BAND_PROUD = 1.5                                           # the black strip's face off the slope
BAND_PAST = 0.8                                            # how far it runs past each end
PROFILE = [(3.0, 0.0), (DEPTH, 0.0), (DEPTH, HEIGHT - 3.0), (DEPTH - 3.0, HEIGHT), (212.0, HEIGHT), (205.0, 79.0),
           (201.0, 76.0), BAND[1], BAND[0], DECK[1], DECK[0], (0.0, 19.0), (0.0, 4.0)]
FINS = dict(y=(245.0, DEPTH + 1.0), count=30, width=4.0, depth=6.0)   # the grooves along the rear block's back edge


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return DECK[0][0] + s * c - h * k, DECK[0][1] + s * k + h * c


def band_point(b, h):
    """The model's (y, z) of the point b up the band's slope from its foot and h off it."""
    c, k = math.cos(BAND_SLOPE), math.sin(BAND_SLOPE)
    return BAND[0][0] + b * c - h * k, BAND[0][1] + b * k + h * c


# The keyboard: KEYS_X0 is the main block's left edge (ESC's), U a key's pitch, GAP between two keys. A key stands from
# the well's floor (WELL below the deck) to its top, KEY_HEIGHT above the deck, tapering by KEY_INSET on every side.
U, GAP = 19.05, 1.0
KEYS_X0 = -188.0
ROW_S = {5: 30.2, 4: 30.2 + U, 3: 30.2 + 2 * U, 2: 30.2 + 3 * U, 1: 30.2 + 4 * U}   # each row's front edge
FROW = (30.2 + 5 * U + 2.0, 14.0)                          # the function keys' row: its front edge and depth
PAD_TOP = -1                                               # the keypad's top row: level with the function keys'
WELL, KEY_HEIGHT, KEY_INSET = 3.0, 9.0, 2.2


def kx(u):
    return KEYS_X0 + u * U


def row_span(row):
    """A row's front and back edges, s up the deck."""
    if row == 0:
        return FROW[0], FROW[0] + FROW[1]
    if row == PAD_TOP:
        return ROW_S[1] + U + GAP, ROW_S[1] + 2 * U + GAP
    return ROW_S[row], ROW_S[row] + U


def key_rect(xu, row, wu):
    """A key's base, (x0, s0, x1, s1) in the slope's frame."""
    s0, s1 = row_span(row)
    return kx(xu) + GAP / 2, s0 + GAP / 2, kx(xu + wu) - GAP / 2, s1 - GAP / 2


def _row(names, x0, row, colour, widths=None):
    out, x = [], x0
    for k, name in enumerate(names):
        w = widths[k] if widths else 1.0
        out.append((name, x, row, w, colour))
        x += w
    return out


F = 1.32                     # the function row's pitch
PAD_X = 15.25                # the keypad's left edge

# (legend, x in units, row, width in units, "light" or "dark"). RETURN is an L over rows 2 and 3 (RETURN below).
KEYS = (
    _row(["F6/F1", "F7/F2", "F8/F3", "F9/F4", "F10/F5"], 0.52, 0, "dark", [F] * 5)
    + [("STOP", 7.46, 0, F, "dark"), ("CLS/HOME", 7.46 + 1.36, 0, F, "dark")]
    + _row(["SELECT", "INS", "DEL"], 10.45, 0, "dark", [F] * 3)
    + [("ESC", 0.0, 1, 1.0, "dark")] + _row(list("1234567890") + ["-", "^", "¥"], 1.0, 1, "light")
    + [("BS", 14.0, 1, 1.0, "dark")]
    + [("TAB", 0.0, 2, 1.5, "dark")] + _row(list("QWERTYUIOP") + ["@", "["], 1.5, 2, "light")
    + [("CTRL", 0.0, 3, 1.75, "dark")] + _row(list("ASDFGHJKL") + [";", ":", "]"], 1.75, 3, "light")
    + [("SHIFT", 0.0, 4, 2.25, "dark")] + _row(list("ZXCVBNM") + [",", ".", "/", "_"], 2.25, 4, "light")
    + [("SHIFT", 13.25, 4, 1.75, "dark")]
    + _row(["CAPS", "GRAPH", "取消"], 1.8, 5, "dark") + [("SPACE", 4.8, 5, 5.3, "light")]
    + _row(["実行", "かな", "PAUSE"], 10.1, 5, "dark", [2.0, 1.1, 1.6])
    + [(legend, PAD_X + (k % 4), [PAD_TOP, 1, 2, 3][k // 4], 1.0, "dark") for k, legend in
       enumerate(["7", "8", "9", "/", "4", "5", "6", "*", "1", "2", "3", "-", "0", ".", ",", "+"])]
)
RETURN = dict(top=(13.5, 15.0), bottom=(13.75, 15.0))      # its two rows' x, in units
BADGE = (0.1, 1.7)                                         # the MSX VIEW badge, in the bottom row's place: its x in units


def return_outline():
    """RETURN's base, an (x, s) outline anticlockwise from its front left corner: the wider part on row 2, the narrower
    on row 3 under it."""
    (a, b), (c, _) = RETURN["top"], RETURN["bottom"]
    g = GAP / 2
    s3, s2, s1 = ROW_S[3] + g, ROW_S[2] + g, ROW_S[2] + U - g
    return [(kx(c) + g, s3), (kx(b) - g, s3), (kx(b) - g, s1), (kx(a) + g, s1), (kx(a) + g, s2), (kx(c) + g, s2)]


# The cursor keys under the keypad, reaching in front of the bottom row: a well, and in it four wedges round a square.
CURSOR = dict(well=(kx(PAD_X) - 0.8, kx(PAD_X + 4.0) + 0.8, 16.0, 67.0), outer=(74.0, 46.0), inner=(20.0, 14.0),
              gap=1.4, height=8.0)


def cursor_middle():
    x0, x1, s0, s1 = CURSOR["well"]
    return (x0 + x1) / 2, (s0 + s1) / 2


def cursor_outline(name):
    """A cursor key's base, an (x, s) outline: the wedge between the cluster's outline and the square, on its side,
    moved in to open the gaps along the diagonals (msx2_layout.py's)."""
    cx, cs = cursor_middle()
    (ow, od), (iw, idp) = CURSOR["outer"], CURSOR["inner"]
    outer = [(cx - ow / 2, cs - od / 2), (cx + ow / 2, cs - od / 2), (cx + ow / 2, cs + od / 2), (cx - ow / 2, cs + od / 2)]
    inner = [(cx - iw / 2, cs - idp / 2), (cx + iw / 2, cs - idp / 2), (cx + iw / 2, cs + idp / 2),
             (cx - iw / 2, cs + idp / 2)]
    k = {"down": 0, "right": 1, "up": 2, "left": 3}[name]
    return inset([outer[k], outer[(k + 1) % 4], inner[(k + 1) % 4], inner[k]], CURSOR["gap"] / 2)


def wells():
    """The wells the keys stand in, each an (x, s) outline: the main block (round the badge), the function keys', the
    keypad's and the cursor keys'."""
    m = 0.8
    s5, s4, top = ROW_S[5], ROW_S[4], ROW_S[1] + U
    x0, x1, c0, c1 = CURSOR["well"]
    f0, f1 = FROW[0] - m, FROW[0] + FROW[1] + m
    p0, p1 = row_span(3)[0] - m, row_span(PAD_TOP)[1] + m
    badge = kx(BADGE[1]) + m
    return [[(badge, s5 - m), (kx(15.0) + m, s5 - m), (kx(15.0) + m, top + m), (kx(0.0) - m, top + m),
             (kx(0.0) - m, s4 - m), (badge, s4 - m)],
            [(kx(0.52) - m, f0), (kx(10.45 + 3 * F) + m, f0), (kx(10.45 + 3 * F) + m, f1), (kx(0.52) - m, f1)],
            [(kx(PAD_X) - m, p0), (kx(PAD_X + 4.0) + m, p0), (kx(PAD_X + 4.0) + m, p1), (kx(PAD_X) - m, p1)],
            [(x0, c0), (x1, c0), (x1, c1), (x0, c1)]]


# The rear block's top, in the model's plan (x, y): slot 1's lid, a little proud, and the notch in front of it.
LID = dict(x=(-94.5, 15.5), y=(216.0, 236.0), thickness=1.4)
NOTCH = dict(x=(-48.0, -34.0), y=(210.0, 216.0))
# The band, along its slope (x across, b up it from its foot): the autofire rate slider (its knob at the left end, off,
# at rest), RESET, the lights (each over its name's box, at its left).
SLIDER = dict(x=(-104.0, -68.0), b=(4.0, 11.0), knob=6.0)
RESET = dict(x=(-3.5, 0.8), b=(6.0, 20.0), height=1.8)
LIGHTS = dict(x=[88.0 + 15.0 * k for k in range(6)], b=12.5, size=(2.4, 1.6), label=(13.0, 5.0, 9.5), at=-3.5)
LIGHT_NAMES = ("電源", "CAPS", "かな", "PAUSE", "高速モード", "FDD IN USE")   # power, CAPS, kana, PAUSE, R800, FDD
RIBS = dict(b=(22.0, 39.0), count=26)                      # the band's upper half

# The right end: the drive's slot, its eject button, the joystick ports (one in the deck's end, one under the slot).
# (y, z) on the end.
DRIVE_SLOT = dict(y=(164.0, 256.0), z=(33.0, 37.0))
EJECT = dict(y=(238.0, 250.0), z=(26.0, 31.0), out=1.6)
PORTS = [dict(y=(90.0, 112.0), z=(9.0, 19.0)), dict(y=(222.0, 244.0), z=(9.0, 19.0))]

# The disk: a 3.5-inch disk, lying flat, its shutter's end in first (towards -x); SEAT its middle in the drive.
DISK = dict(size=(90.0, 94.0), thickness=3.3)
SEAT = (HALF - DISK["size"][1] / 2 - 3.0, (DRIVE_SLOT["y"][0] + DRIVE_SLOT["y"][1]) / 2,
        (DRIVE_SLOT["z"][0] + DRIVE_SLOT["z"][1]) / 2)

COLOURS = dict(case="#5C6166", band="#1F201E", key_light="#D7D6D3", key_dark="#9FA19A", black="#141416",
               blue="#5A6397", gold="#B39A63", teal="#3E9497", lavender="#C9C8E4")

REGIONS = dict(top=(0, 0, 1024, 669), band=(0, 676, 1024, 104), disk_top=(0, 788, 180, 188),
               disk_bottom=(188, 788, 180, 188))
SWATCHES = dict(red=(408, 804), green=(440, 804), black=(472, 804), band=(504, 804), case=(536, 804),
                key_light=(568, 804))

FPS = 30
LENGTH = 240                 # 8 s
