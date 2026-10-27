"""The pieces the console theme's handheld cards share (megaduck.py, gamate.py and the handhelds and phones after them): a
device standing up and facing the viewer, its face in the (x, z) plane at y = 0, its back at y = depth. Blender's
Python.

body() makes its shell from the face's outline, its edges rounded; plate() (emblems.py's) a button or a part standing
out of the face; screens() its screens, stacked in front of its window, each shrunk to nothing until it's shown
(devices.showing_poses() swaps them). Every part is painted with an Atlas's regions (card.py).
"""

import math

from mathutils import Matrix, Vector

from amiga import curved, paint, solid
from saturn import inset

__all__ = ["body", "circle", "cross", "pill", "screens", "face_uv", "paint_face", "stadium"]


def circle(x, z, r, n=24):
    return [(x + r * math.cos(2 * math.pi * k / n), z + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def cross(x, z, arm, half):
    return [(x + arm, z - half), (x + arm, z + half), (x + half, z + half), (x + half, z + arm), (x - half, z + arm),
            (x - half, z + half), (x - arm, z + half), (x - arm, z - half), (x - half, z - half), (x - half, z - arm),
            (x + half, z - arm), (x + half, z - half)]


def stadium(x, z, length, width, degrees=0.0, n=6):
    """A pill's outline, its middle at (x, z), turned degrees anticlockwise."""
    r = width / 2
    half = length / 2 - r
    pts = [(half + r * math.cos(math.radians(-90 + 180 * k / n)), r * math.sin(math.radians(-90 + 180 * k / n)))
           for k in range(n + 1)]
    pts += [(-half + r * math.cos(math.radians(90 + 180 * k / n)), r * math.sin(math.radians(90 + 180 * k / n)))
            for k in range(n + 1)]
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [(x + px * c - pz * s, z + px * s + pz * c) for px, pz in pts]


pill = stadium


def body(name, outline, depth, mat, front=3.0, back=4.0, steps=3):
    """The shell: the face's outline (x, z) through the depth (y), its front and back edges rounded (quarter circles
    of radius front and back, in steps)."""
    rings = []                                             # (y, inset)
    for k in range(steps + 1):
        a = math.pi / 2 * k / steps
        rings.append((front * (1 - math.cos(a)), front * (1 - math.sin(a))))
    for k in range(steps + 1):
        a = math.pi / 2 * k / steps
        rings.append((depth - back + back * math.sin(a), back * (1 - math.cos(a))))
    return solid(name, [[(x, y, z) for x, z in (inset(outline, d) if d > 1e-6 else outline)] for y, d in rings], mat)


def face_uv(atlas, region, span):
    """UVs for a face seen from the front: span = (x0, x1, z0, z1) of the region, (x, z) to UVs."""
    x0, x1, z0, z1 = span
    uv = atlas.uv(region, x1 - x0, z1 - z0)
    return lambda co: uv(co.x - x0, z1 - co.z)


def back_uv(atlas, region, span):
    """UVs for the back, seen from behind (its left the device's right)."""
    x0, x1, z0, z1 = span
    uv = atlas.uv(region, x1 - x0, z1 - z0)
    return lambda co: uv(x1 - co.x, z1 - co.z)


def paint_face(obj, mat, uv, keep=lambda c, n, kind: n.y < -0.9):
    paint(obj, mat, uv, keep)
    return obj


def screens(names, w, h, atlas, mat, at, bulge=0.0, step=0.12):
    """Screens stacked in front of a window whose middle is at `at` (on the face), each its own region of the atlas, the
    later in front: {"screen_" + name: (object, place)}."""
    out = {}
    for k, name in enumerate(names):
        uv = atlas.uv(name, 1.0, 1.0)
        part = curved("screen_" + name, w, h, bulge, uv, mat, 8, 6)
        out["screen_" + name] = (part, Vector(at) + Vector((0.0, -step * (k + 1), 0.0)))
    return out


def turned(obj, about, degrees, axis="Y"):
    """Turns obj's mesh about a point (for a slanting button)."""
    obj.data.transform(Matrix.Translation(about) @ Matrix.Rotation(math.radians(degrees), 4, axis)
                       @ Matrix.Translation(-Vector(about)))
    return obj
