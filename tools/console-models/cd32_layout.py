"""The Amiga CD32's measurements, shared by cd32_print.py (which draws its printing) and cd32.py (which builds it).
Plain Python: Blender's Python imports it too.

The Amiga CD32 (1993), 305 x 213 mm (the Computer History Museum's 12 x 8 3/8 inches), and its pad, 184 x 80 mm, lying
in front of its left end. Millimetres: x from the console's middle (left to right), y back from its front, z up from
the table. The rest was measured from Evan-Amos's photographs on Wikimedia Commons (the console from its front
corners, with its lid open, with its pad, and the pad from above), scaled by the console's width; the pad's outline
was traced from its photograph from above (its cable cut away).

The console: a dark grey box on a recessed base, its front face (the control strip at the right: RESET, the two
lights, the volume slider, the headphone socket) rising to a slope (the AMIGA CD32 badge at the right), then the flat
top: at the left the lid over the CD well, hinged along its back, a round dome on it with 32bit printed and a smoked
window in its front half; at the right the vents' grooves and Commodore.

One texture (ATLAS square, REGIONS): `top` (the console seen from above: the lettering, the badge, the dome's
printing; planar-mapped onto every face facing up), `front` (the front face), `pad` (the pad's top), `disc` and
`data` (the CD's two sides: a made-up game, Odyssey), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 305.0, 213.0, 66.0
FOOT = dict(height=8.0, inset=6.0)                     # the recessed base under it
FRONT = ((0.0, 8.0), (4.0, 40.0))                      # the front face: its foot and its top, (y, z)
SLOPE = ((4.0, 40.0), (58.0, 62.0))                    # the slope up to the flat top
TOP_Z = HEIGHT                                         # the flat top, from the slope's top to the back


def profile():
    """The side outline, (y, z), anticlockwise seen from the right end."""
    (fy0, fz0), (fy1, fz1) = FRONT
    (_, _), (sy1, sz1) = SLOPE
    return [(fy0, fz0), (DEPTH, fz0), (DEPTH, TOP_Z - 3.0), (DEPTH - 3.0, TOP_Z), (sy1 + 6.0, TOP_Z), (sy1, sz1),
            (fy1, fz1)]


LID = dict(x=(-150.0, -4.0), y=(54.0, 209.0), thickness=6.0, open=-100.0)   # its plan; hinged along its back edge
DOME = dict(at=(-77.0, 131.0), r=70.0, rise=5.0)       # the round dome on the lid
WELL = dict(at=(-77.0, 131.0), r=62.0, depth=14.0)     # the CD's well under the lid
VENTS = dict(x=(14.0, 140.0), y=[96.0 + 6.0 * k for k in range(16)], width=3.0, depth=2.0)
RESET = dict(x=(30.0, 62.0), z=(18.0, 34.0), out=3.0)  # the RESET button, on the front face
LIGHTS = dict(power=(84.0, 30.0), access=(84.0, 22.0), size=(14.0, 2.4))   # x, z on the front face

DISC = dict(r=60.0, hole=7.5, thickness=1.2)
SPINDLE_Z = TOP_Z - WELL["depth"] + 3.0                # where the CD sits in the well

# The pad: its outline traced from above (y from its front edge, towards the player, back to the shoulder buttons;
# the U's opening at the back), lying at PAD["at"], turned PAD["turn"] degrees.
PAD_OUTLINE = [(0.0, 47.3), (38.7, 50.9), (39.7, 53.3), (34.5, 67.5), (34.5, 72.3), (36.4, 75.1), (40.7, 77.0),
               (41.6, 79.4), (70.1, 79.4), (71.6, 76.5), (75.8, 75.1), (80.1, 71.3), (83.4, 64.2), (89.1, 44.7),
               (92.0, 23.8), (89.6, 17.1), (85.8, 13.3), (75.4, 9.5), (39.7, 2.4), (2.1, 0.0), (-36.4, 1.9),
               (-80.1, 10.9), (-85.8, 13.3), (-89.6, 17.1), (-92.0, 27.1), (-88.2, 49.4), (-82.0, 68.5),
               (-76.8, 74.6), (-71.1, 76.5), (-70.1, 78.9), (-41.6, 78.9), (-37.8, 75.6), (-35.4, 72.7),
               (-34.9, 68.0), (-39.7, 53.7), (-38.7, 50.9)]
PAD = dict(at=(-110.0, -78.0), turn=8.0, thickness=26.0, length=80.4, width=184.0,
           dpad=(-65.4, 47.9, 13.4), buttons=dict(green=(53.6, 53.3, 5.9), yellow=(70.9, 58.8, 5.9),
                                                  red=(58.5, 36.0, 7.1), blue=(75.4, 40.9, 5.9)),
           pause=(22.8, 22.6, 23.8, 5.0), logo=(-19.8, 32.0, 46.0), band=26.0)

COLOURS = dict(case="#3A3B3E", dark="#141416", pad="#4A4B4F", disc="#FFFFFF")

REGIONS = dict(top=(0, 0, 1024, 715), front=(0, 723, 1024, 120), pad=(0, 851, 400, 173), disc=(408, 851, 172, 172),
               data=(588, 851, 172, 172))
SWATCHES = dict(dark=(784, 872), green=(816, 872), yellow=(848, 872), red=(880, 872), blue=(912, 872),
                lit=(944, 872), amber=(976, 872), grey=(784, 904), smoke=(816, 904))

FPS = 30
LENGTH = 240                 # 8 s
