"""The J2ME card's measurements, shared by j2me_print.py (which draws its printing and screens) and j2me.py (which
builds it). Plain Python: Blender's Python imports it too.

An unbranded keypad phone of the 2000s, the kind Java games were played on, after the Nokia 6230 (2003): 44 x 103 x 20
mm (GSMArena), its parts placed from a photograph of its face square on (0.071 mm a pixel); its screen 128 x 128 in
65,536 colours. Millimetres in handheld.py's frame: x from its middle (left to right), z up from its bottom edge, y back
from its face.

The dark shell, its sides showing either side of the silver front plate (PLATE: rounded at its top); on the plate the
raised earpiece badge (BADGE, blank) and the earpiece's slot over it, the screen's black window (WINDOW), the soft keys
either side under it with the navi key between them, the call and end keys under the soft keys, and the twelve keys
(KEYS: the outer columns' keys separate, the middle column's wider in their own inset column, its bright outline wrapping
round 0).

Two textures: the print (ATLAS square, REGIONS: `face` from the front, and swatches) and the screens (MEDIA_REGIONS: the
idle screen, the menu, the games list with a made-up game, its title and two moments of it). A region is (x, y, width,
height) in pixels.
"""

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 44.0, 103.0, 20.0
SPAN = (-WIDTH / 2, WIDTH / 2, 0.0, HEIGHT)
PLATE = dict(x=18.0, z=(3.0, 101.0), top=12.0, bottom=8.0, proud=0.8)
BADGE = dict(at=(0.0, 89.5), size=(16.0, 8.0), proud=1.6, slot=(0.0, 94.5))
WINDOW = dict(size=(31.0, 28.0), at=(0.0, 67.0))
SCREEN = dict(size=(27.0, 27.0), pixels=(128, 128))
OUTER = 14.5                  # the outer columns' middles
# The keys: (name, x, z, width, height, legend, mark).
KEYS = ([("soft_left", -OUTER, 46.0, 6.5, 5.0, "", "soft"), ("soft_right", OUTER, 46.0, 6.5, 5.0, "", "soft"),
         ("call", -OUTER, 40.0, 6.5, 5.0, "", "call"), ("end", OUTER, 40.0, 6.5, 5.0, "", "end"),
         ("navi", 0.0, 43.0, 11.0, 10.0, "", "navi")]
        + [(d, x, z, 6.5 if x else 11.0, 4.6, legend, "key") for z, row in
           ((33.0, (("1", "1\no.o"), ("2", "2\nabc"), ("3", "3\ndef"))), (27.5, (("4", "4\nghi"), ("5", "5\njkl"),
                                                                          ("6", "6\nmno"))),
            (22.0, (("7", "7\npqrs"), ("8", "8\ntuv"), ("9", "9\nwxyz"))), (16.5, (("*", "*\n+"), ("0", "0\n_"),
                                                                                ("#", "#\n⇧"))))
           for (d, legend), x in zip(row, (-OUTER, 0.0, OUTER))])
COLUMN = dict(x=6.6, z=(13.4, 49.5))                       # the middle column's inset panel
PLAYED = ("2", "4", "5", "6", "8", "soft_left", "navi")

MADE_UP = ("Top Corner '94 (Europe)", "megadrive")
MENU = ["Messages", "Contacts", "Log", "Settings", "Gallery", "Media", "Games", "Organiser", "Web"]

COLOURS = dict(shell="#2A2620", plate="#C8C2B8", key="#D2CDC4", ink="#1F2227", blue="#2A6FC9", green="#2E8B57",
               red="#C0282D", window="#100C10", line="#ECE8E0")

REGIONS = dict(face=(0, 0, 352, 824))
SWATCHES = {name: (380 + 32 * (k % 9), 20 + 32 * (k // 9)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(idle=(0, 0, 256, 256), menu=(264, 0, 256, 256), games=(528, 0, 256, 256), title=(0, 264, 256, 256),
                     game1=(264, 264, 256, 256), game2=(528, 264, 256, 256))

FPS = 30
LENGTH = 240                 # 8 s
