"""The emblem cards' shapes: for systems with no hardware of their own, their emblem made solid (emblems.py). Plain
Python: Blender's Python imports it too.

Doom's four letters, blocky, their bottoms cut into points; Quake's rune (a crescent, open at the top, and a nail
through it); EasyRPG's three curling arms on their disc; Solarus's sun (a disc cut off at the bottom) and the sword
across it; Lutro's disc, split on its diagonal, and its heart; M.U.G.E.N's and MESS's letters are set in a font
(emblems.py). Every shape is drawn here from simple geometry, not traced from a logo's artwork. Millimetres: x across
(left to right), z up; each outline anticlockwise, seen from the front (-y).
"""

import math

FPS = 30


def ccw(points):
    """The outline anticlockwise (x right, z up)."""
    area = sum(x0 * z1 - x1 * z0 for (x0, z0), (x1, z1) in zip(points, points[1:] + points[:1]))
    return list(points) if area > 0 else list(reversed(points))


def circle(cx, cz, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * k / n), cz + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def arc(cx, cz, r, a0, a1, n):
    """Points along an arc, from angle a0 to a1 (degrees, anticlockwise from +x), both ends included."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def turned(points, degrees, about=(0.0, 0.0)):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    ox, oz = about
    return [(ox + (x - ox) * c - (z - oz) * s, oz + (x - ox) * s + (z - oz) * c) for x, z in points]


def moved(points, dx, dz):
    return [(x + dx, z + dz) for x, z in points]


# ---- Doom ------------------------------------------------------------------------------------------------------------

# Its letters (outline, holes), each set from its own left at the baseline, its top at 100: a D whose stem runs down to
# a point, two Os whose bottoms come to a point in the middle, an M whose outer legs do.
DOOM_LETTERS = [
    ([(0.0, 100.0), (0.0, -24.0), (56.0, 0.0), (78.0, 22.0), (78.0, 82.0), (60.0, 100.0)],
     [[(22.0, 80.0), (50.0, 80.0), (56.0, 74.0), (56.0, 30.0), (46.0, 20.0), (22.0, 20.0)]]),
    ([(0.0, 100.0), (0.0, 12.0), (36.0, -22.0), (72.0, 12.0), (72.0, 100.0)],
     [[(21.0, 80.0), (21.0, 26.0), (36.0, 12.0), (51.0, 26.0), (51.0, 80.0)]]),
    ([(0.0, 100.0), (0.0, 12.0), (36.0, -22.0), (72.0, 12.0), (72.0, 100.0)],
     [[(21.0, 80.0), (21.0, 26.0), (36.0, 12.0), (51.0, 26.0), (51.0, 80.0)]]),
    ([(0.0, 100.0), (30.0, 100.0), (49.0, 62.0), (68.0, 100.0), (98.0, 100.0), (98.0, -28.0), (78.0, -6.0),
      (78.0, 56.0), (49.0, 8.0), (20.0, 56.0), (20.0, -6.0), (0.0, -28.0)], []),
]
DOOM_X = [0.0, 88.0, 170.0, 252.0]          # each letter's left
DOOM_DEPTH = 46.0
DOOM_COLOURS = dict(face="#B8421C", side="#6E7278", ember="#FFB040", floor="#2A2A2E")

# ---- Quake -----------------------------------------------------------------------------------------------------------

QUAKE_RING = dict(outer=(0.0, 60.0, 58.0), inner=(0.0, 72.0, 46.0), opening=(62.0, 118.0))   # (cx, cz, r), degrees


def quake_crescent():
    """The crescent: the outer circle round from its right horn's tip to its left's, back by the inner one; the
    inner circle sits high, so the ring is thick at the bottom and thin at its horns."""
    (ox, oz, orad), (ix, iz, irad) = QUAKE_RING["outer"], QUAKE_RING["inner"]
    a_right, a_left = QUAKE_RING["opening"]
    outer = arc(ox, oz, orad, a_right, a_left - 360.0, 56)
    inner = arc(ix, iz, irad, a_left - 360.0 + 4.0, a_right - 4.0, 52)
    return ccw(outer + inner)


QUAKE_NAIL = [(-17.0, 66.0), (17.0, 66.0), (17.0, 60.0), (6.0, 57.0), (6.0, -8.0), (0.0, -46.0), (-6.0, -8.0),
              (-6.0, 57.0), (-17.0, 60.0)]
QUAKE_DEPTH = 22.0
QUAKE_SLAB = dict(x=(-96.0, 96.0), y=(-50.0, 50.0), z=(-90.0, -24.0))   # the stone it's driven into
QUAKE_COLOURS = dict(face="#9A6428", side="#5A3A1A", stone="#6E6B66", stone2="#4E4C48", crack="#FF7A20",
                     dust="#B8B2A6")

# ---- EasyRPG ---------------------------------------------------------------------------------------------------------

EASYRPG_DISC = 62.0


def easyrpg_arm(k):
    """One of the three arms: a band spiralling out from near the middle to the rim, narrow at its inner end and
    widening as it goes, its ends round; turned by k thirds."""
    n = 40
    centre = []
    for i in range(n + 1):
        t = i / n
        r = 12.0 + 39.0 * t
        a = math.radians(120.0 * k + 190.0 * (1 - t))
        centre.append((r * math.cos(a), r * math.sin(a), 3.5 + 5.5 * t))       # (x, z, half its width)
    left, right = [], []
    for i, (x, z, w) in enumerate(centre):
        x0, z0, _ = centre[max(0, i - 1)]
        x1, z1, _ = centre[min(n, i + 1)]
        dx, dz = x1 - x0, z1 - z0
        length = math.hypot(dx, dz)
        nx, nz = -dz / length, dx / length
        left.append((x + nx * w, z + nz * w))
        right.append((x - nx * w, z - nz * w))
    (x0, z0, w0), (x1, z1, w1) = centre[0], centre[-1]
    a_end = math.degrees(math.atan2(left[-1][1] - z1, left[-1][0] - x1))
    a_start = math.degrees(math.atan2(right[0][1] - z0, right[0][0] - x0))
    return ccw(left + arc(x1, z1, w1, a_end, a_end - 180.0, 8)[1:-1] + right[::-1]
               + arc(x0, z0, w0, a_start, a_start - 180.0, 8)[1:-1])


EASYRPG_COLOURS = dict(disc="#D8EDCA", rim="#42632D", arm="#5A9A3A", arm_side="#3E6A28", spark="#FFF4A0")

# ---- Solarus ---------------------------------------------------------------------------------------------------------

SOLARUS_SUN = dict(r=52.0, cut=-22.0)         # the sun's disc, cut off flat at z = cut
SOLARUS_DISC = 66.0


def solarus_sun():
    r, cut = SOLARUS_SUN["r"], SOLARUS_SUN["cut"]
    a = math.degrees(math.asin(cut / r))
    return ccw(arc(0.0, 0.0, r, a, 180.0 - a, 64))


# The sword, along its own +u from its point: the blade's length and width, the guard's span and depth, the grip's
# length, the pommel's radius; lying across the sun at 45 degrees, its point low at the left.
SWORD = dict(blade=(96.0, 12.0), guard=(46.0, 7.0), grip=18.0, pommel=8.0, angle=45.0, point=(-46.0, -36.0))
SOLARUS_COLOURS = dict(sun="#FFAB00", sun_side="#E07000", disc="#4A2C94", disc_side="#2E1B66", blade="#D6DAE2",
                       hilt="#2E1B66", glow="#FFE070")

# ---- Lutro -----------------------------------------------------------------------------------------------------------

LUTRO_DISC = 60.0
LUTRO_SPLIT = 40.0                            # the split's angle (degrees): from the lower left to the upper right


def heart(cx, cz, size, n=24):
    """A heart's outline, size tall, its middle at (cx, cz)."""
    points = []
    for k in range(n * 2):
        t = math.pi * 2 * k / (n * 2)
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        points.append((cx + x * size / 32.0, cz + (z + 2.5) * size / 32.0))
    return ccw(points)


LUTRO_COLOURS = dict(purple="#94477D", green="#6B9942", heart="#FFFFFF", navy="#101C80", moon="#F2F2F2",
                     side="#3A2A44")

# ---- M.U.G.E.N and MESS ----------------------------------------------------------------------------------------------

MUGEN = dict(text="M.U.G.E.N", font="ariblk.ttf", size=100.0, stretch=1.25, depth=26.0)
MUGEN_COLOURS = dict(face="#D8E6F8", side="#7C8598", floor="#2E2E38", ring="#4A4A58", ball="#5AC8FF",
                     spark="#FFF6C0", bar="#F6C820")
MUGEN_HUD = dict(z=150.0, height=18.0, bar=180.0, gap=70.0)   # the health bars over the stage: their foot, height,
                                                               # each one's length, the gap for the timer between
MESS = dict(text="MESS", font="impact.ttf", size=170.0, shear=0.32, depth=36.0)
MESS_COLOURS = dict(face="#FFA428", side="#B8620E", cart="#5C5E66", sticker="#E8D44A", floppy="#2E58B8",
                    metal="#C8CCD2", cassette="#1E1E22", calc="#D8D0B8")
