"""The Acorn Electron card's measurements, shared by electron_print.py (which draws its printing and screens) and
electron.py (which builds it). Plain Python: Blender's Python imports it too.

The Acorn Electron (1983), 340 mm wide, 160 deep and 65 high (a retro computing database's figures), a Plus 1 on its
back (340 x 90 x 50, as the period's pages give it) with a ROM cartridge going into its slot, in front of the portable
television the ZX Spectrum's card has (zx_spectrum.py's, its front's middle at TV_AT). Millimetres: x from the
computer's middle (left to right), y back from its front, z up from the table. The rest was measured from photographs of
Electrons on Wikimedia Commons (from above with a Plus 1 on, from the front corners), scaled by its width and by its
keys' 19.05 mm pitch.

The computer: a wedge, its top sloping up from the front to the back; the keys (the UK layout) standing in the opening
in its top, the dark band behind them (its grid of lines, acorn electron and the green acorn). The Plus 1: a box on its
back, the two cartridge slots in its top's right half, each under a hinged cover.

The keys are laid out in units of U from the back row's left edge (KEYS_X0), in rows from the back (the digits') to the
front (the space bar's). The top is a plane at SLOPE: a key stands on it in the slope's frame (x across, s up the slope
from its front edge, h off it), and top_point() maps a point of that frame to the model's (y, z).

One texture (ATLAS square, REGIONS): `top` (the computer and the Plus 1 seen from above: the key tops and legends, the
band; planar-mapped onto every face facing up), `label` (the cartridge's), the screens (`boot`, `title`, `game_1`,
`game_2`), and swatches; the television's front drawn where zx_spectrum_layout.py's PRINT_REGIONS["tv"] puts it and its
swatches where its PRINT_SWATCHES do, as television() maps them. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024
U = 19.05

WIDTH, DEPTH = 340.0, 160.0
FRONT = (8.0, 26.0)              # the top's front edge (y, z)
BACK = (154.0, 62.0)             # where the top meets the back's rounding
SLOPE = math.atan2(BACK[1] - FRONT[1], BACK[0] - FRONT[0])
OPENING = dict(x=(-160.0, 152.0), s=(6.0, 116.0), depth=5.0)     # the keys' opening in the top
BAND = dict(s=(118.0, 148.0))    # the dark band behind the keys
KEYS_X0, KEY_ROW1 = -146.0, 104.0   # the back row's left edge; its middle (s)
KEY = dict(height=12.0, inset=2.6)  # a key's height off the opening's floor; how far its top is drawn in
ROWS = [
    (0.0, [("ESCAPE", 1.0)] + [(c, 1.0) for c in "1234567890=^\\"] + [("BREAK", 1.0)]),
    (0.5, [("CAPS LK", 1.25)] + [(c, 1.0) for c in "QWERTYUIOP£_"] + [("COPY", 1.0)]),
    (0.75, [("CTRL", 1.25)] + [(c, 1.0) for c in "ASDFGHJKL;:"] + [("RETURN", 1.75)]),
    (0.9, [("SHIFT", 1.6)] + [(c, 1.0) for c in "ZXCVBNM,./"] + [("SHIFT", 1.25), ("DELETE", 1.0)]),
    (3.0, [(" ", 7.5)]),
]

PLUS1 = dict(y=(160.0, 250.0), height=52.0, slots=[(176.0, 192.0), (212.0, 228.0)], x=(28.0, 152.0), depth=34.0)
CART = dict(size=(104.0, 15.0, 78.0), seat=34.0, label=(80.0, 52.0), above=70.0)   # w, t, h; how deep it sits;
                                                                                   # how far over it it appears
TV_AT = (0.0, 262.0)             # the television's front's middle

COLOURS = dict(case="#E4DCC6", key="#ECE6D4", band="#3B4038", dark="#0A0A0B", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 850, 625), label=(858, 0, 160, 104), boot=(828, 796, 192, 148), title=(632, 640, 192, 148),
               game_1=(828, 640, 192, 148), game_2=(632, 796, 192, 148))
SWATCHES = dict(case=(872, 140), key=(904, 140), band=(936, 140), dark=(968, 140), cart=(872, 172), lit=(904, 172))

FPS = 30
LENGTH = 240                 # 8 s


def top_point(s, h):
    """The model's (y, z) of the point s up the top's slope from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return FRONT[0] + s * c - h * k, FRONT[1] + s * k + h * c


def profile():
    """The computer's side outline, (y, z), round from its front's foot: the front, the slope, the back rounding over
    and down, the underside."""
    by, bz = BACK
    back = [(by + (DEPTH - by) * math.sin(math.radians(a)), bz - 6.0 + 6.0 * math.cos(math.radians(a)))
            for a in range(0, 91, 15)]
    return [(2.0, 0.0), (DEPTH - 2.0, 0.0), (DEPTH, 2.0)] + list(reversed(back)) + [FRONT, (0.0, FRONT[1] - 4.0),
                                                                                    (0.0, 2.0)]


def keys():
    """Every key: (legend, x0, x1, s), s its row's middle up the slope; the rows from the back to the front."""
    out = []
    for r, (offset, row) in enumerate(ROWS):
        x = KEYS_X0 + offset * U
        s = KEY_ROW1 - r * U
        for legend, width in row:
            out.append((legend, x, x + width * U, s))
            x += width * U
    return out
