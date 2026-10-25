"""The Nintendo 64's measurements, shared by n64_print.py (which draws its printing) and n64.py (which builds it).
Plain Python: Blender's Python imports it too.

The Nintendo 64 (1996), 260 x 190 x 73 mm (Nintendo's figures), and its controller, 160 x 153 mm. Millimetres: x from
the console's middle (left to right), y back from its front edge, z up from the table. The rest was measured from
Evan-Amos's photographs on Wikimedia Commons (the console from each corner and with its controller, the controller
from above, a cartridge), scaled by the console's width; the controller's outline was traced from its photograph from
above.

The console: a base with a round pod at each corner, the front pods standing proud, the four controller ports and the
NINTENDO 64 window in its flat front, the power light under the window; on it the upper shell, its top a plateau with
POWER (a slider) at its left, the memory expansion's lid in its middle and RESET at its right; and on the plateau the
hump running to the back, the vent's slots across its front slope, the cartridge slot (its two dust flaps) behind
them, Nintendo's name behind the slot. The controller lies to the console's left, its three prongs towards the player.

One texture (ATLAS square, REGIONS): `top` (the console seen from above: the plateau's and the hump's printing;
planar-mapped onto every face facing up), `front` (the front face: the window, the ports' rims), `pad` (the
controller's top: its greys, the D-pad's dish, the stick's well, the C buttons' diamond, Nintendo's name), `label`
(the cartridge's: a made-up game, Odyssey), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 260.0, 190.0, 73.0
FOOT = 3.0                                                 # the dark band the console stands on
BASE = dict(front=14.0, back=186.0, x=124.0, z=29.0, r=14.0)   # the base's plan (its front flat) and its top
PODS = dict(front=(103.0, 25.0, 27.0, 24.0, 28.0), back=(103.0, 164.0, 25.0, 22.0, 26.0))   # x, y, rx, ry, height
SHELL = [(29.0, 118.0, 20.0, 184.0), (50.0, 112.0, 24.0, 180.0), (58.0, 103.0, 31.0, 174.0)]   # z, x, y0, y1
PLATEAU = 58.0
HUMP = dict(back=(96.0, 176.0), front=(62.0, 92.0), tip=74.0, base=56.0, top=HEIGHT, inset=7.0)
SLOT = dict(x=(-59.0, 59.0), y=(114.0, 133.0), bottom=36.0, flap=HEIGHT - 2.5)
VENT = dict(count=17, x=(-48.0, 48.0), y=(88.0, 104.0), width=2.6, depth=6.0)
LOGO_Y = 150.0                                             # Nintendo's name, behind the slot

POWER = dict(at=(-80.0, 48.0), well=(18.0, 32.0), knob=(14.0, 15.0, 3.0), travel=9.0)   # well w, d; knob w, d, h
RESET = dict(at=(80.0, 46.0), size=(16.0, 26.0, 3.0))
LID = dict(at=(0.0, 44.0), size=(66.0, 36.0, 1.6))
PORTS = dict(x=(-74.0, -38.0, 38.0, 74.0), z=14.0, size=(26.0, 16.0, 3.0))
WINDOW = dict(x=(-22.0, 22.0), z=(6.0, 27.0))
LIGHT = (0.0, 4.4, (6.0, 2.4))                             # the power light: x, z, its size

CART = dict(size=(116.0, 18.0, 75.0), arch=9.0, label=(92.0, 52.0), inserted=34.0)   # w, t, h (at its ends); its top's
                                                                                     # rise; the label's size

# The controller: its outline traced from above (its right half, from the back's middle round to the middle prong's
# tip; mirrored for the left), y from the middle prong's tip; it lies at PAD["at"], turned PAD["turn"] degrees.
PAD_OUTLINE = [(0.0, 154.6), (11.9, 154.6), (26.1, 151.2), (30.3, 149.1), (32.8, 143.7), (54.5, 140.4), (64.1, 135.8),
               (64.5, 133.3), (71.6, 125.3), (75.4, 116.6), (76.2, 103.6), (79.6, 86.1), (80.0, 70.2), (77.1, 48.9),
               (73.7, 38.4), (67.5, 33.4), (62.5, 33.8), (58.3, 38.0), (47.0, 76.4), (44.9, 77.7), (32.4, 76.9),
               (25.3, 72.3), (23.6, 69.3), (14.4, 20.5), (8.6, 5.8), (4.8, 1.7), (0.0, 0.0)]
PAD = dict(at=(-232.0, 64.0), turn=18.0, thickness=24.0, length=154.6,
           dpad=(-49.2, 111.3, 27.0, 9.2), dish=16.6, start=(0.6, 106.4, 6.1),
           a=(42.7, 96.8, 6.4), b=(30.9, 106.9, 6.4),
           c=[(54.6, 123.7), (44.9, 116.6), (64.1, 116.4), (54.8, 106.8)], c_r=4.4,
           stick=(1.3, 73.1), well=16.6, gate=11.5, cap=8.7, logo=(0.4, 139.3, 35.0, 8.3),
           shoulders=[(-60.0, 136.0), (60.0, 136.0)])

COLOURS = dict(case="#38383B", controller="#BCBCBC", dark="#151517", cart="#858688", grey="#A9AAAC",
               shoulder="#6F6F72", well="#4B4B4E")

REGIONS = dict(top=(0, 0, 640, 468), front=(0, 476, 640, 100), pad=(648, 0, 376, 364), label=(648, 372, 376, 212))
SWATCHES = dict(grey=(16, 600), red=(48, 600), blue=(80, 600), green=(112, 600), yellow=(144, 600), lit=(176, 600),
                dark=(208, 600), well=(240, 600), shoulder=(272, 600), cap=(304, 600), dpad=(336, 600))

FPS = 30
LENGTH = 240                 # 8 s
