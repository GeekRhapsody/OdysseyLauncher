"""The Game.com card's measurements, shared by gamecom_print.py (which draws its printing and screens) and gamecom.py
(which builds it). Plain Python: Blender's Python imports it too.

Tiger's Game.com (1997), the first one: 190 x 108 x 19 mm (Wikipedia), its parts placed from a photograph of its face
square on (0.1206 mm a pixel against its width); its screen 200 x 160 in four greys under a touch screen; its cartridges
about 45 x 43 x 10 mm, two slots in its right end. Millimetres in handheld.py's frame: x from its middle (left to right),
z up from its bottom edge, y back from its face.

Its face: the silver upper panel over the charcoal lower band (BAND_TOP, rising a little under the function buttons);
game.com above the screen, sunk in its sloping bezel (BEZEL, the LCD at its floor); the speaker's holes and the D-pad in
its round well on the left; ON/OFF, A B and C D on their tilted silver pills and the MENU SOUND PAUSE strip on the
right; TIGER under the screen; the stylus half sunk in its groove along the band. The cartridges go into the right end,
their labels to the back.

Two textures: the print (ATLAS square, REGIONS: `face` from the front, `label` a cartridge's, and swatches) and the
screens (MEDIA_REGIONS: the start-up screen, the menu, a made-up game's title and two moments of it, the touch screen's
grid over each). A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 190.0, 108.0, 19.0
HALF = WIDTH / 2


def _arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def outline():
    top, bottom = 14.0, 10.0
    return (_arc(HALF - bottom, bottom, bottom, -90.0, 0.0, 6) + _arc(HALF - top, HEIGHT - top, top, 0.0, 90.0, 7)
            + _arc(-HALF + top, HEIGHT - top, top, 90.0, 180.0, 7) + _arc(-HALF + bottom, bottom, bottom, 180.0, 270.0, 6))


SPAN = (-HALF, HALF, 0.0, HEIGHT)
BAND_TOP = [(-HALF, 38.5), (40.0, 38.5), (60.0, 40.5), (HALF, 42.0)]     # the band's upper edge
BEZEL = dict(rect=(-45.5, 44.5, 39.5, 98.0), r=4.0, depth=2.6, floor=(68.0, 54.0))
SCREEN = dict(size=(66.0, 52.0), at=(-1.0, 68.7), pixels=(200, 160), grid=(12, 10))
DPAD = dict(at=(-66.0, 59.7), well=14.5, arm=10.0, half=3.6)
SPEAKER = dict(at=(-67.8, 89.2), size=(28.0, 15.0), cols=9, rows=5, r=0.7)
POWER = dict(at=(55.5, 91.7), r=3.0, ring=4.6)
BUTTONS = dict(a=(57.0, 69.6), b=(73.7, 74.8), c=(58.5, 54.9), d=(74.9, 59.7), r=4.75, pill=(30.0, 14.0), slant=18.0)
STRIP = dict(menu=(57.0, 40.4), sound=(69.7, 41.6), pause=(82.4, 42.8), size=(11.0, 2.6), plate=(42.0, 6.0))
STYLUS = dict(x=(-57.0, 61.0), z=21.7, r=3.5, groove=4.2)
LOGOS = dict(gamecom=(-1.4, 103.1), tiger=(-0.2, 36.8))
SLOTS = [dict(z=(57.0, 101.0)), dict(z=(9.0, 53.0))]      # in the right end: slot 1 above, slot 2 below
CART = dict(size=(43.0, 10.0, 45.0), y=9.5)               # its length in, thickness, width; its middle's y

PALETTE = ["#262A22", "#545A4A", "#848B74", "#B2BAA0"]     # the LCD's four greys, darkest first
MADE_UP = ("Titan Frame (Europe)", "megadrive")
MENU = ["GAME", "WEB", "CALC", "NOTES", "DATES", "CARDS"]

COLOURS = dict(silver="#C8C8C6", band="#46474B", back="#3D3F3F", teal="#3293A4", button="#46454A", lcd="#9AA38C",
               stylus="#36353A", ink="#202020", cart="#2A2A2C")

REGIONS = dict(face=(0, 0, 1007, 572), label=(0, 580, 225, 215))
SWATCHES = {name: (260 + 32 * (k % 9), 600 + 32 * (k // 9)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(boot=(0, 0, 400, 320), menu=(408, 0, 400, 320), title=(0, 328, 400, 320),
                     game1=(408, 328, 400, 320), game2=(0, 656, 400, 320))

FPS = 30
LENGTH = 240                 # 8 s
