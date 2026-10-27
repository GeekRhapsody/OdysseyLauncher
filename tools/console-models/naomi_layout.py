"""NAOMI's card, a Sega candy cabinet running NAOMI: the measurements shared by naomi_print.py (which draws its printing
and screens) and naomi.py (which builds it). Plain Python: Blender's Python imports it too.

NAOMI is an arcade board; its games were played in cabinets, and in Japan most often in Sega's candy cabinets. The
card is one, 750 x 905 x 1445 mm (the New Astro City's figures in the Hard*Candy wiki), its shape measured from a
photograph of a New Astro City on Wikimedia Commons, its marquee NAOMI's. NAOMI 2 and NAOMI GD-ROM (KINDS) are the same
cabinet, each with its own marquee and start-up, and one of tools/made-up-games's arcade games on its screen.
Millimetres: x from its middle (left to right), y back from the control panel's front edge, z up from the floor.

Its side outline (PROFILE): the lower cabinet's front set back under the control panel; the control panel tipped a
little towards the player; the monitor's bezel sloping back from it; the speaker panel and the marquee over the
screen; the back. Faces on the bezel's slope are placed in its frame (x across, s up the slope from its foot, h out of
it towards the player).

Two textures. `print` (ATLAS square, REGIONS): `marquee` (NAOMI, lit), `speakers` (the speaker panel: two grilles and
a badge), `panel` (the control panel's overlay), `front` (the lower cabinet's front: the coin doors), and swatches.
`media` (MEDIA_REGIONS): the screens, 4:3 (`boot`, NAOMI's logo; `title`, a made-up game, Odyssey, CREDIT 1 and PRESS
START; `game1` and `game2`, two frames of play). A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 750.0, 905.0, 1445.0
BEZEL = ((300.0, 830.0), (500.0, 1290.0))                 # the bezel's slope: its foot and its top, (y, z)
SPEAKERS = ((455.0, 1340.0), (500.0, 1290.0))            # the speaker panel: its top and its foot
MARQUEE = ((480.0, 1445.0), (455.0, 1340.0))             # the marquee: its top and its foot
PANEL = ((0.0, 800.0), (282.0, 826.0))                   # the control panel's top: its front and back edges
PANEL_FRONT = 735.0                                      # its front face's foot
PANEL_DEPTH = 290.0                                      # its top's printed depth, back from its front edge
LOWER_Y = 190.0                                          # the lower cabinet's front


def profile():
    """The side outline, (y, z), anticlockwise seen from the right."""
    return [(LOWER_Y, 0.0), (DEPTH, 0.0), (DEPTH, 1150.0), (770.0, HEIGHT), MARQUEE[0], MARQUEE[1], SPEAKERS[1],
            BEZEL[0], PANEL[1], PANEL[0], (0.0, PANEL_FRONT), (LOWER_Y, 700.0)]


def bezel_angle():
    """The bezel's slope, in degrees from horizontal (the rotation about x that turns y up the slope)."""
    (y0, z0), (y1, z1) = BEZEL
    return math.degrees(math.atan2(z1 - z0, y1 - y0))


def bezel_length():
    (y0, z0), (y1, z1) = BEZEL
    return math.hypot(y1 - y0, z1 - z0)


SCREEN = dict(s=(26.0, 476.0), x=(-300.0, 300.0), depth=36.0,   # the screen's recess in the bezel
              glass=(560.0, 420.0), middle=251.0, bulge=14.0)   # the CRT's glass, its middle up the slope

# The control panel, in its frame (x across, v back from its front edge along its top).
STICKS = dict(p1=(-250.0, 112.0), p2=(110.0, 112.0), shaft=(5.0, 46.0), ball=17.0)
BUTTONS = dict(p1=[(-176.0, 96.0), (-136.0, 92.0), (-96.0, 96.0), (-176.0, 138.0), (-136.0, 134.0), (-96.0, 138.0)],
               p2=[(184.0, 96.0), (224.0, 92.0), (264.0, 96.0), (184.0, 138.0), (224.0, 134.0), (264.0, 138.0)],
               start=[(-30.0, 132.0), (30.0, 132.0)], r=12.0, height=8.0)
COIN = dict(at=(318.0, 214.0), plate=(44.0, 54.0), slot=(4.0, 26.0))   # the coin plate: its middle, w x d; the slot

# The lower cabinet's front: the two coin doors, the kick plate.
DOORS = dict(x=[(-300.0, -10.0), (10.0, 300.0)], z=(130.0, 640.0))
KICK = dict(z=(0.0, 60.0), out=4.0)

COLOURS = dict(case="#EDEBE4", dark="#121214", metal="#A9ACB0", glass="#FFFFFF", print="#FFFFFF")

REGIONS = dict(marquee=(0, 0, 1024, 158), speakers=(0, 166, 1024, 98), panel=(0, 272, 1024, 346),
               front=(0, 626, 560, 398))
SWATCHES = dict(green=(600, 650), pink=(632, 650), yellow=(664, 650), yellow_lit=(696, 650), black=(728, 650),
                metal=(760, 650), dark=(792, 650), coin=(824, 650), white=(856, 650))

SCREEN_PX = (480, 360)
MEDIA_REGIONS = dict(boot=(0, 0) + SCREEN_PX, title=(512, 0) + SCREEN_PX, game1=(0, 368) + SCREEN_PX,
                     game2=(512, 368) + SCREEN_PX)

# The cabinets: NAOMI's own (its screens drawn by naomi_print.py: a made-up game, Odyssey), and NAOMI 2's and NAOMI
# GD-ROM's, each with its own marquee and start-up and one of tools/made-up-games's games (its file's stem and system),
# their screens a picture (JPEG).
KINDS = {
    "naomi": dict(game=None),
    "naomi2": dict(game=("dustygul", "arcade")),
    "naomigd": dict(game=("Skylance (Europe)", "n64")),
}


def media_file(kind):
    return f"{kind}_media.{'png' if KINDS[kind]['game'] is None else 'jpg'}"

FPS = 30
LENGTH = 240                 # 8 s
