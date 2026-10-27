"""The Mega Duck card's measurements, shared by megaduck_print.py (which draws its printing and screens) and megaduck.py
(which builds it). Plain Python: Blender's Python imports it too.

Welback's Mega Duck WG-108 (1993), white: 97 x 155 x 32 mm and its 2.7-inch screen 51 x 48 mm at 160 x 144 (Wikipedia),
its cartridge 54 x 63 x 7 mm; the rest placed from photographs of its face from either side. Millimetres in handheld.py's
frame: x from its middle (left to right), z up from its bottom edge, y back from its face.

Its face (outline()): the upper part, round the screen, a little narrower than the lower, a gentle waist between; its
top corners rounded, the bottom right one much more than the left. On it: two moulded ridges above the slate bezel
(BEZEL: its labels, SUPER STEREO SOUND and HIGH RESOLUTION DOT MATRIX LCD in turquoise, the battery light), the LCD in it;
the turquoise D-pad and B and A, SELECT and START slanting in grey, Mega Duck lettered in slate, the speaker's slanting
slots, PHONES. The CONTRAST and VOL wheels in grey bezels stand out of its sides, the power knob slides along its top
edge's left end; the cartridge slides down into the bay at the top of its back, its label out to the back.

Two textures: the print (ATLAS square, REGIONS: `face` from the front, `back` from behind, `label` the cartridge's, and
swatches) and the screens (MEDIA_REGIONS: the start-up screen, a made-up game's title and two moments of it, in the LCD's
four blues on its green). A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, UPPER, HEIGHT, DEPTH = 97.0, 93.0, 155.0, 30.0


def _arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def _waist(x0, x1, z0, z1, n=6):
    """The side from (x0, z0) to (x1, z1), an S-curve."""
    return [(x0 + (x1 - x0) * (1 - math.cos(math.pi * k / n)) / 2, z0 + (z1 - z0) * k / n) for k in range(1, n)]


def outline():
    """The face's outline (x, z), anticlockwise from the bottom edge's left end."""
    lo, up = WIDTH / 2, UPPER / 2
    pts = _arc(lo - 22.0, 22.0, 22.0, -90.0, 0.0, 9)
    pts += [(lo, 60.0)] + _waist(lo, up, 60.0, 78.0) + [(up, 78.0)]
    pts += _arc(up - 8.0, HEIGHT - 8.0, 8.0, 0.0, 90.0, 5) + _arc(-up + 8.0, HEIGHT - 8.0, 8.0, 90.0, 180.0, 5)
    pts += [(-up, 78.0)] + _waist(-up, -lo, 78.0, 60.0) + [(-lo, 60.0)]
    pts += _arc(-lo + 12.0, 12.0, 12.0, 180.0, 270.0, 6)
    return pts


SPAN = (-WIDTH / 2, WIDTH / 2, 0.0, HEIGHT)                # the face's and back's regions: x and z
RIDGES = (146.5, 150.5)
BEZEL = dict(rect=(-35.0, 35.0, 73.0, 143.0), r=7.0, out=0.6)
SCREEN = dict(size=(51.0, 48.0), at=(0.0, 109.0), window=(54.0, 52.0), pixels=(160, 144))
DPAD = dict(at=(-25.0, 47.0), r=13.0, arm=11.5, half=3.4)
BUTTONS = dict(b=(16.0, 45.5), a=(34.0, 50.5), r=6.0)
PILLS = dict(select=(9.0, 29.0), start=(27.0, 31.5), size=(15.0, 4.0), slant=8.0)
SPEAKER = dict(at=[(14.0 + 6.4 * k, 13.0 + 1.0 * k) for k in range(5)], size=(14.0, 3.4), slant=62.0)
WHEELS = dict(z=(74.0, 98.0), y=(9.0, 25.0), out=3.4)
KNOB = dict(at=(-34.0, 12.0), size=(7.0, 6.0, 4.0), travel=6.0)
LIGHT = dict(at=(30.5, 103.0), r=1.2)
CART = dict(size=(54.0, 7.0, 63.0), out=10.0, bay=(28.0, 50.0))   # width, thickness, height; the bay's half width, depth

PALETTE = ["#22304E", "#3E5068", "#64786E", "#8AA27C"]     # the LCD's four blues on its green, darkest first
MADE_UP = ("Flipside Pinball (Europe)", "megadrive")

COLOURS = dict(shell="#E2E1E2", bezel="#424752", turquoise="#5FBABC", grey="#5E646A", lcd="#869E79", slate="#424752",
               dark="#1A1C20", lit="#FF3A2C", cart="#26282C")

REGIONS = dict(face=(0, 0, 388, 620), back=(396, 0, 194, 310), label=(396, 318, 216, 252))
SWATCHES = {name: (640 + 32 * (k % 8), 600 + 32 * (k // 8)) for k, name in
            enumerate(("shell", "bezel", "turquoise", "grey", "lcd", "dark", "lit", "cart"))}
MEDIA_REGIONS = dict(boot=(0, 0, 320, 288), title=(328, 0, 320, 288), game1=(656, 0, 320, 288),
                     game2=(0, 296, 320, 288))

FPS = 30
LENGTH = 240                 # 8 s
