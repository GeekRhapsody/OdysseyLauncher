"""The PC Engine's measurements, shared by pc_engine_print.py (which draws its printing) and pc_engine.py (which builds
it). Plain Python: Blender's Python imports it too.

The PC Engine (PI-TG001, 1987), 140 x 140 x 38 mm, its HuCard (credit-card sized, 54 x 85 mm) and its PI-PD001 pad.
Millimetres: x from the console's middle (left to right), y back from its front, z up from the table. The rest was
measured from Evan-Amos's photographs on Wikimedia Commons (the console from each corner and with its pad), scaled by
its width.

The console: a white box, a seam round it near its foot; in the middle of its top the HuCard's channel, running back
from the front edge to the slot under the logo's bridge, a thumb scoop at its front; grilles on the top's front
corners; AC ADAPTER and AV SWITCH outlined on its back corners; the green POWER slider in its front at the left and the
pad's socket at the right. The pad lies to its left.

One texture (ATLAS square, REGIONS): `top` (the console seen from above: the logo, the grilles, the outlines; planar-
mapped onto every face facing up), `front` (its front face), `card` (the HuCard's face: the contacts' end, a made-up
game's label, Odyssey), `pad` (the pad's top), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 140.0, 140.0, 38.0
EDGE = 5.0
SEAM = 11.0                                                  # the seam round it, its height
CHANNEL = dict(x=(-31.0, 31.0), y=(0.0, 60.0), floor=31.5)   # the HuCard's channel in the top
SCOOP = dict(y=6.0, r=17.0, floor=27.0)                      # the thumb scoop at its front
SLOT = dict(x=(-28.5, 28.5), y=(56.0, 122.0), z=(31.5, 34.5))   # the slot under the bridge, deep enough for the card
POWER = dict(x=(-58.0, -46.0), z=(7.0, 21.0), out=3.0, travel=6.0)
PORT = dict(x=46.0, z=17.0, r=5.5)                           # the pad's socket, in the front

CARD = dict(size=(54.0, 85.0), thickness=2.4, inside=34.0)   # w, length; its front edge's y once in
SEAT = (0.0, CARD["inside"] + CARD["size"][1] / 2, CHANNEL["floor"] + CARD["thickness"] / 2 + 0.05)

PAD = dict(at=(-150.0, 10.0), turn=8.0, size=(132.0, 64.0, 21.0), r=10.0,
           dome=dict(r=24.0, y=32.0, height=3.5),            # the cable's dome, its middle at the pad's back edge
           plate=(-60.0, 60.0, -27.0, 22.0),                 # the face plate: x0, x1, y0, y1
           dpad=(-41.0, -10.0, 24.0, 8.4), select=(-12.0, -15.0), run=(8.0, -15.0), pill=(11.0, 4.6),
           ii=(32.0, -3.0), i=(49.0, -3.0), button_r=7.6)

COLOURS = dict(case="#E7E7E3", plate="#5A5B5F", green="#2FA454", dark="#1A1A1C", pad="#E3E3DF")

REGIONS = dict(top=(0, 0, 512, 512), front=(520, 0, 504, 140), card=(520, 148, 200, 312), pad=(0, 520, 512, 252))
SWATCHES = dict(green=(744, 168), grey=(776, 168), dark=(808, 168), red=(840, 168), white=(872, 168))

FPS = 30
LENGTH = 240                 # 8 s
