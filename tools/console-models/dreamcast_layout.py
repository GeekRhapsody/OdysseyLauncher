"""The Dreamcast card's measurements, shared by dreamcast_print.py (which draws its printing) and dreamcast.py (which
builds it). Plain Python: Blender's Python imports it too.

The Sega Dreamcast (1998), the European one (its swirl blue), 190 mm wide, 196 deep and 76 high (the Science Museum
Group's 75 x 190 x 195; others give 190 x 195.8 x 75.5 to 78), its controller (147 wide, 152 long: dimensions.com's
figures) in front of it at its left with a VMU in its slot, a GD-ROM with a made-up game, Odyssey, going under its lid.
Millimetres: x from its middle (left to right), y back from its front, z up from the table. Measured from Evan-Amos's
photographs on Wikimedia Commons (from the front left and right, the back right, with its controller; the controller
with and without its VMU).

The console: its body (the front face over the base set in, the top rising a little to the back), the ports' panel sunk
into its front with A B C D (PANEL, PORTS), the vents in its right side (VENTS); on its top POWER and OPEN in the front
corners (BUTTONS), the power light by POWER, and the round lid over the disc's well, hinged at its back (LID, WELL), the
arrow at its front. The controller (PAD): its outline (the grips reaching towards the player, the cable between them),
the VMU in its slot (its screen, SCREEN), the analogue stick, the D-pad, A B X Y, START.

One texture (ATLAS square, REGIONS): `top` (the console from above: the swirl and Dreamcast on the lid, its arrow, the
creases, POWER and OPEN), `front` (the front: SEGA, A B C D, the ports), `pad` (the controller from above: the swirl,
the VMU's face round its screen, the letters), the VMU's screens (`vmu_off`, `vmu_on`), `disc` (the GD-ROM's label), and
swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH = 190.0, 196.0
TOP = (68.0, 76.0)                # the top's height at the front and at the back
BASE = dict(inset=5.0, height=9.0)                         # the base, set in under the body
PANEL = dict(x=(-80.0, 50.0), z=(14.0, 46.0), depth=3.0)
PORTS = dict(x=[-66.0, -36.0, -6.0, 24.0], z=24.0, size=(16.0, 13.0), depth=10.0)
VENTS = dict(y=(10.0, 60.0), z=(16.0, 50.0), count=7)
BUTTONS = dict(power=(-72.0, 24.0), open=(72.0, 24.0), r=10.0, light=(-54.0, 12.0))
LID = dict(at=(0.0, 112.0), r=76.0, thickness=4.0, open=-62.0)
WELL = dict(r=66.0, depth=24.0)
ARROW = [(-14.0, 50.0), (14.0, 50.0), (0.0, 30.0)]          # the lid's arrow, at its front (plan)

DISC = dict(r=60.0, hole=7.5, thickness=1.6, above=60.0)

# The controller: its outline's points (x across, y away from the player) round from the top's left, smoothed; its
# height; the VMU's slot and its screen (middle, w, h); the stick (middle, base's and cap's radii), the D-pad (middle,
# arm's length and width), A B X Y (the diamond's middle, its reach, the buttons' radius), START (middle, size); where
# it lies (x, y) and its turn.
PAD = dict(points=[(-60.0, 60.0), (-32.0, 72.0), (0.0, 76.0), (32.0, 72.0), (60.0, 60.0), (72.0, 34.0), (74.0, 0.0),
                   (70.0, -32.0), (66.0, -62.0), (56.0, -76.0), (42.0, -74.0), (33.0, -56.0), (16.0, -40.0),
                   (0.0, -36.0), (-16.0, -40.0), (-33.0, -56.0), (-42.0, -74.0), (-56.0, -76.0), (-66.0, -62.0),
                   (-70.0, -32.0), (-74.0, 0.0), (-72.0, 34.0)],
           height=26.0, slot=((0.0, 24.0), 46.0, 60.0), screen=((0.0, 30.0), 34.0, 25.0),
           stick=((-46.0, 36.0), 13.0, 9.5), dpad=((-38.0, -12.0), 13.0, 8.0), abxy=((46.0, 6.0), 13.0, 5.5),
           start=((0.0, -20.0), 9.0), at=(-150.0, -104.0, 10.0))

COLOURS = dict(case="#EEEDEA", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 520, 536), front=(0, 544, 520, 208), pad=(528, 0, 296, 304), vmu_off=(832, 0, 136, 100),
               vmu_on=(832, 108, 136, 100), disc=(528, 312, 300, 300))
SWATCHES = dict(case=(560, 640), dark=(592, 640), button=(624, 640), lit=(656, 640), off=(688, 640), disc=(720, 640),
                cable=(752, 640), red=(560, 672), blue=(592, 672), yellow=(624, 672), green=(656, 672), grey=(688, 672))

FPS = 30
LENGTH = 240                 # 8 s


def top_z(y):
    """The top's height at y."""
    return TOP[0] + (TOP[1] - TOP[0]) * y / DEPTH
