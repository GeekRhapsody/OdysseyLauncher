"""The Neo Geo Pockets' measurements, shared by neogeo_pocket_print.py (which draws their printing and screens) and
neogeo_pocket.py (which builds them). Plain Python: Blender's Python imports it too.

Two handhelds, one per system: `ngpc` (SNK's Neo Geo Pocket Color, 1999, in Platinum Blue), 130 x 80 x 30 mm, and `ngp`
(the Neo Geo Pocket, 1998, its monochrome forerunner, in carbon black), 122 x 74 x 24 mm (Wikipedia's figures). Both
stand up facing the viewer, as the handheld models do. Millimetres: x from the middle (left to right), y back from the
front face, z up from the bottom. The rest was measured from Evan-Amos's photographs on Wikimedia Commons (each from in
front, flat, which gives the front's layout; the Color from the front left and from behind; the Pocket's edges),
scaled by each body's width.

The body: the front outline (its top corners tight, its bottom corners round), lofted back to SLAB, its edges rounded;
behind it the two grips (the battery compartment in the left one), the cartridge's recess between them at the top. On
the front: the screen's dark bezel, the stick in its notched ring at the left (the "clicky" microswitched stick), POWER
and its light over it, the speaker's holes under it; A and B on a curve at the right, OPTION over them, the dimples
under them; SNK under the screen. The cartridge slides down into the recess at the top of the back, its label facing
out.

Each has one texture (ATLAS square, REGIONS): `front` (the front from in front: the case's colour, the bezel with its
printing and the switched-off screen, NEOGEO POCKET, the names, the light's ring, the speaker's holes, the ring's
notches, SNK), the screens (`boot`, the Pocket's start-up logo; `title`, a made-up game, Odyssey; `game`, a moment of
its play), the cartridge's label, and swatches. A region is (x, y, width, height) in pixels. The Pocket's screens are
its own four greys.
"""

import math

ATLAS = 1024

MODELS = {
    "ngpc": dict(
        name="Neo Geo Pocket Color", size=(130.0, 80.0, 30.0), slab=19.0, corners=(3.0, 13.0),   # top, bottom radii
        bezel=dict(at=(0.2, 44.6), size=(64.4, 63.7), r=2.0), lcd=dict(at=(0.2, 43.2), size=(48.3, 45.7)),
        logo=(0.0, 15.0), color_text=True,
        power=dict(at=(-54.1, 66.7), size=(8.8, 4.2)), power_label=(-54.3, 72.1), light=dict(at=(-41.6, 66.3), r=1.2),
        stick=dict(at=(-47.2, 47.3), ring=(11.3, 8.5), cap=5.3, nub=True), speaker=(-46.6, 22.0),
        option=dict(at=(53.1, 71.8), r=2.8), option_label=(43.1, 72.0),
        a=dict(at=(40.3, 46.2), r=3.9, ring=5.0), b=dict(at=(53.0, 56.1), r=3.9, ring=5.0),
        a_label=(36.8, 58.2), b_label=(47.0, 64.8),
        dimples=dict(x=(38.9, 47.0, 55.1), z=(29.6, 22.2, 14.5)), snk=(0.4, 6.4),
        grips=dict(x=29.0, depth=8.5), recess=dict(x=(-28.5, 28.5), z=(54.0, 80.0)),
        cart=dict(size=(52.0, 40.0, 8.0), protrudes=5.0),
        colours=dict(case="#8C93B4", key="#1A1A1E", ring="#B9C0D8", glass="#FFFFFF", print="#FFFFFF"),
        lcd_off=(118, 122, 118), ink=(70, 76, 104), carbon=False),
    "ngp": dict(
        name="Neo Geo Pocket", size=(122.0, 74.0, 24.0), slab=16.0, corners=(3.0, 12.0),
        bezel=dict(at=(0.0, 43.1), size=(59.6, 56.6), r=2.0), lcd=dict(at=(-0.3, 43.1), size=(49.7, 46.1)),
        logo=(0.0, 15.8), color_text=False,
        power=dict(at=(-50.4, 65.2), size=(9.5, 4.0)), power_label=(-49.9, 70.1), light=dict(at=(-37.7, 65.2), r=1.4),
        stick=dict(at=(-43.0, 46.7), ring=(11.2, 7.9), cap=5.6, nub=False), speaker=(-43.0, 21.7),
        option=dict(at=(52.6, 65.5), r=2.6), option_label=(42.3, 65.5),
        a=dict(at=(39.2, 42.1), r=4.5, ring=0.0), b=dict(at=(51.5, 51.0), r=4.5, ring=0.0),
        a_label=(39.2, 50.4), b_label=(51.5, 58.9),
        dimples=dict(x=(36.7, 44.9, 53.1), z=(29.3, 20.7, 12.5)), snk=(-0.5, 7.6),
        grips=dict(x=27.0, depth=7.0), recess=dict(x=(-26.5, 26.5), z=(50.0, 74.0)),
        cart=dict(size=(50.0, 38.0, 7.0), protrudes=5.0),
        colours=dict(case="#2E3036", key="#141416", ring="#3E4148", glass="#FFFFFF", print="#FFFFFF"),
        lcd_off=(108, 114, 104), ink=(86, 88, 96), carbon=True),
}

def outline(m):
    """A handheld's front outline, anticlockwise (x, z), its top corners tight and its bottom corners round."""
    (w, h, _), (rt, rb) = m["size"], m["corners"]
    points = []
    for cx, cz, r, a0 in ((w / 2 - rt, h - rt, rt, 0), (-w / 2 + rt, h - rt, rt, 90), (-w / 2 + rb, rb, rb, 180),
                          (w / 2 - rb, rb, rb, 270)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            points.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return points


SCREEN_PX = (256, 243)                               # 160 x 152, at 1.6
REGIONS = dict(front=(0, 0, 1024, 630), boot=(0, 638) + SCREEN_PX, title=(264, 638) + SCREEN_PX,
               game=(528, 638) + SCREEN_PX, cart=(792, 638, 224, 146))
SWATCHES = dict(red=(808, 808), dark=(840, 808), clear=(872, 808), key=(904, 808), cart=(936, 808), lit=(968, 808))
CART_LABEL = (44.0, 28.7)                             # the label on the cartridge's back, w x h

FPS = 30
LENGTH = 240                 # 8 s
