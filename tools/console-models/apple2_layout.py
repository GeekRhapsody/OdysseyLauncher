"""The Apple IIe, its two Disk II drives and its Monitor II: the measurements shared by apple2_print.py (which draws
their printing) and apple2.py (which builds them). Plain Python: Blender's Python imports it too.

Millimetres: x from the computer's middle (left to right), y back from its front edge, z up from the table. The IIe is
392 x 448 x 108 mm: a wedge whose sloping top runs from its low front edge (undercut beneath) up to the flat top over
its back two thirds, the keyboard in a well in the slope, RESET in a recess of its own at its right, the lid's front
sloping down to the keyboard with the apple //e badge on it, and a comb of vent slots in each side. On its lid stand
the two Disk II drives side by side, and on them the Monitor II, its depth cut from about 330 mm to 262 (the launcher
fits a card's largest side, so the set's depth would draw it smaller than the other cards). Measured from photographs:
the Bibliotheque nationale de France's set of an IIe and its drive (from above, in front, each side, the drive from
above), a front view of the set on Wikimedia Commons, and close views of the US keyboard; scaled by the keys' 19.05 mm
pitch.

The keyboard is the US one. Its keys are laid out in units of U from the main block's left edge (KEYS_X0), in rows
from the front (row 5, the space bar's) to the back (row 1, the digits'). The top slopes at SLOPE: a key stands on it
in the slope's frame (x across, s up the slope from the front edge, h off it), and slope_point() maps a point of that
frame to the model's (y, z).

Two textures. `print` (ATLAS square, PRINT_REGIONS): `top` (the computer's top in front of the drives seen from
above: the key tops and legends, the power light, the badge; planar-mapped onto every face facing up), `drive1` and
`drive2` (the drives' front panels), `strip` (the monitor's control strip), and swatches. `media` (MEDIA_REGIONS):
the screens, each the glass's whole width and height, green on black (`banner`, the screen at rest: Apple //e at its
top; `pass2` and `pass5`, Odyssey's title screen part loaded, the hi-res lines in the order they arrive; `title`, the
whole of it), the floppy's label side, and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

# -- The computer ----------------------------------------------------------------------------------------------------

WIDTH, DEPTH, HEIGHT = 392.0, 448.0, 108.0
TIP = (0.0, 53.0)                     # the front edge's top
FLAT_Y = 247.0                        # where the sloping top meets the flat top
SLOPE = math.atan2(HEIGHT - TIP[1], FLAT_Y - TIP[0])
UNDERCUT = (52.0, 4.0)                # the undercut runs back from under the front edge to here, (y, z)
PLATE = 4.0                           # the dark base plate under it


def profile():
    """The computer's side outline, (y, z), anticlockwise seen from its right end."""
    return [(UNDERCUT[0] + 4.0, 0.0), (DEPTH - 3.0, 0.0), (DEPTH, 3.0), (DEPTH, HEIGHT - 4.0), (DEPTH - 4.0, HEIGHT),
            (FLAT_Y, HEIGHT), (TIP[0] + 2.0, TIP[1] + 0.45), (TIP[0], TIP[1] - 2.0), UNDERCUT]


def slope_point(s, h):
    """The model's (y, z) of the point s up the top's slope from the front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return TIP[0] + s * c - h * k, TIP[1] + s * k + h * c


SEAMS = dict(lid_front=139.0, lid_fold=243.0, lid_x=154.3)   # the lid's front edge and fold, along y; its sides, x
BADGE = dict(x=(-141.5, -53.1), split=-79.8, y=(168.4, 192.0))  # apple and //e, side by side, on the lid's slope
VENTS = dict(y=[252.0 + 10.6 * k for k in range(18)], width=4.2, z=(66.0, HEIGHT + 5.0), inset=12.0)

# The keyboard: KEYS_X0 is the main block's left edge, U a key's pitch, GAP between two keys. A key stands from the
# well's floor (WELL below the top) to its top, KEY_HEIGHT above it, tapering by KEY_INSET on every side.
U, GAP = 19.05, 1.0
KEYS_X0 = -140.0
ROW_S = {5: 19.5, 4: 38.55, 3: 57.6, 2: 76.65, 1: 95.7}    # each row's front edge, up the slope
WELL, KEY_HEIGHT, KEY_INSET = 4.0, 10.0, 2.4
RESET = dict(x=(141.9, 158.3), s=(93.6, 108.9), well=(138.5, 161.7, 90.5, 112.0))


def kx(u):
    return KEYS_X0 + u * U


def key_rect(xu, row, wu):
    """A key's base, (x0, s0, x1, s1) in the slope's frame."""
    s0, s1 = ROW_S[row], ROW_S[row] + U
    return kx(xu) + GAP / 2, s0 + GAP / 2, kx(xu + wu) - GAP / 2, s1 - GAP / 2


def _row(names, x0, row, legends):
    return [(n, x0 + i, row, 1.0, legend) for i, (n, legend) in enumerate(zip(names, legends))]


# (name, x in units, row, width in units, legend): a legend's line break splits its upper and lower characters. The
# power light stands in the bottom row like a key, lit.
KEYS = (
    [("esc", 0.0, 1, 1.0, "Esc")]
    + _row([f"d{k}" for k in "1234567890"] + ["minus", "equals"], 1.0, 1,
           ["!\n1", "@\n2", "#\n3", "$\n4", "%\n5", "^\n6", "&\n7", "*\n8", "(\n9", ")\n0", "_\n-", "+\n="])
    + [("delete", 13.0, 1, 1.5, "Delete")]
    + [("tab", 0.0, 2, 1.5, "Tab")]
    + _row(list("qwertyuiop") + ["lbracket", "rbracket", "backslash"], 1.5, 2,
           list("QWERTYUIOP") + ["{\n[", "}\n]", "|\n\\"])
    + [("control", 0.0, 3, 1.75, "Control")]
    + _row(list("asdfghjkl") + ["semicolon", "quote"], 1.75, 3, list("ASDFGHJKL") + [":\n;", '"\n\''])
    + [("return", 12.75, 3, 1.75, "Return")]
    + [("lshift", 0.0, 4, 2.25, "Shift")]
    + _row(list("zxcvbnm") + ["comma", "period", "slash"], 2.25, 4, list("ZXCVBNM") + ["<\n,", ">\n.", "?\n/"])
    + [("rshift", 12.25, 4, 2.25, "Shift")]
    + [("caps", 0.0, 5, 1.25, "Caps\nLock"), ("grave", 1.25, 5, 1.0, "~\n`"), ("light", 2.25, 5, 1.0, ""),
       ("open_apple", 3.25, 5, 1.0, "open"), ("space", 4.25, 5, 5.25, ""), ("solid_apple", 9.5, 5, 1.0, "solid")]
    + _row(["left", "right", "down", "up"], 10.5, 5, ["←", "→", "↓", "↑"])
)


def well():
    """The keyboard's well, an (x, s) outline."""
    m = 1.6
    s5, s1 = ROW_S[5] - m, ROW_S[1] + U + m
    return [(kx(0) - m, s5), (kx(14.5) + m, s5), (kx(14.5) + m, s1), (kx(0) - m, s1)]


# -- The Disk II drives ----------------------------------------------------------------------------------------------

DRIVE = dict(size=(155.0, 222.0, 87.0), at=(-102.5, 102.5), front=244.0,
             panel=(147.0, 79.0, 1.5),       # the front panel: w, h (centred), how far it's sunk into the front
             slot=dict(z=40.0, height=3.2, x=(-64.0, 64.0), depth=150.0),  # z from the panel's bottom
             door=dict(x=(-17.5, 17.5), z=(42.0, 66.0), thickness=4.5),   # the lever over the slot, open (up)
             recess=dict(x=(-16.5, 16.5), z=(12.0, 37.0), depth=6.0),     # the finger recess under the slot
             light=(-43.0, 14.5, 1.6),       # IN USE's light: its x, z from the panel's bottom, radius
             vents=dict(y=[150.0 + 6.5 * k for k in range(9)], width=2.6, z=(55.0, 92.0)))
PANEL_Z = HEIGHT + (DRIVE["size"][2] - DRIVE["panel"][1]) / 2   # the panels' bottom edge

# -- The monitor -----------------------------------------------------------------------------------------------------

MONITOR = dict(
    at=(0.0, 238.0),                 # its front's middle, in the computer's (x, y), standing on the drives
    width=396.0,
    profile=[(0.0, 0.0), (262.0, 0.0), (262.0, 236.0), (230.0, 292.0), (0.0, 292.0)],   # (y back, z)
    strip=39.0,                      # the control strip down its right side, its width
    bezel=dict(x=(-178.0, 144.0), z=(20.0, 256.0), depth=3.0),   # the screen's surround, sunk into the front
    opening=dict(x=-17.0, z=138.0, outer=(300.0, 214.0, 14.0), inner=(268.0, 196.0, 10.0), depth=24.0),
    glass=dict(size=(264.0, 192.0), bulge=8.0),
)

# -- The floppy ------------------------------------------------------------------------------------------------------

DISK = dict(size=133.0, thickness=1.6)                # a 5.25-inch floppy in its jacket
SEAT = (DRIVE["at"][0], DRIVE["front"] + 8.0 + DISK["size"] / 2, PANEL_Z + DRIVE["slot"]["z"])   # its middle, in

# -- The atlases -----------------------------------------------------------------------------------------------------

COLOURS = dict(case="#E3DCC4", keys="#A39E8F", bezel="#C5BCA6", dark="#2A2826", top_keys="#AEA99A",
               drive="#29292B", plate="#5B544A")

PRINT_REGIONS = dict(top=(0, 0, 1024, 653), drive1=(0, 661, 400, 225), drive2=(408, 661, 400, 225),
                     strip=(816, 661, 80, 363))
PRINT_SWATCHES = dict(bezel=(920, 680), dark=(952, 680), lit=(984, 680), plate=(920, 712), green=(952, 712),
                      drive=(984, 712))

SCREEN_PX = (504, 380)       # a screen's region, the glass's proportions
RASTER = (448, 336)          # the lit picture in its middle, 4:3; the Apple's 280 x 192 drawn into it
MEDIA_REGIONS = dict(banner=(0, 0) + SCREEN_PX, pass2=(512, 0) + SCREEN_PX, pass5=(0, 388) + SCREEN_PX,
                     title=(512, 388) + SCREEN_PX, disk=(0, 776, 240, 240))
MEDIA_SWATCHES = dict(black=(272, 800), jacket=(304, 800))

# -- The focused clip ------------------------------------------------------------------------------------------------

FPS = 30
LENGTH = 240                 # 8 s
