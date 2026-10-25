"""The plugs at the ends of the console models' cables, so a cable going into a port ends in its real plug, and a cable
leaving a controller (or a hard-wired one leaving a console) in its strain relief.

Each plug is built in its own frame (millimetres): its face at y = 0, against the port; the part that goes into the
port, its nose, behind it (y < 0); its body and its strain relief out along +y; x across, z up. A builder returns the
plug and where its cable leaves it, (0, length, 0). place() then stands it on a port: at a point on the port's face, its
+y along the face's outward normal. The cable is the card's own, starting there and leaving along the normal.

The shapes, from photographs: `dreamcast` (the controller's light grey block, a seam a third of the way along, the
ribbed strain relief in the cable's lilac), `saturn` (the black controller plug, wide and flat), `dsub` (the 9-pin D
plug of Atari's joysticks and the Archimedes's mouse: its housing a D in section, tapering to the cable), `din` (the
round DIN plug of cassette leads), `modular` (the Macintosh keyboard's clear modular plug and its boot), `grommet` (a
strain relief where a cable leaves a controller or a hard-wired cable a console).
"""

import math

from mathutils import Matrix, Vector

from amiga import rounded, solid


def along(name, sections, mat):
    """A solid through sections along y: each (y, outline), the outline (x, z) points, all the same count."""
    return solid(name, [[(x, y, z) for x, z in outline] for y, outline in sections], mat)


def rect(w, h, r, segments=3):
    return rounded(0.0, 0.0, w, h, min(r, w / 2 - 0.01, h / 2 - 0.01), segments)


def circle(r, segments=16):
    return [(r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments))
            for k in range(segments)]


def ribbed(name, y0, rings, mat):
    """A round strain relief from y0: rings of (length, radius), ribbed or tapering."""
    sections, y = [], y0
    for length, r in rings:
        sections.append((y, circle(r)))
        y += length
    return along(name, sections, mat), y


def dreamcast(body, cable):
    """The Dreamcast controller's plug: body(obj) and cable(obj) colour its parts."""
    nose = along("nose", [(-6.0, rect(14.6, 10.6, 3.0)), (0.0, rect(14.6, 10.6, 3.0))], None)
    front = along("plug", [(0.0, rect(17.0, 13.0, 4.0)), (9.0, rect(17.0, 13.0, 4.0)), (9.0, rect(16.2, 12.2, 3.6)),
                           (10.0, rect(16.2, 12.2, 3.6)), (10.0, rect(17.4, 13.4, 4.2)), (25.0, rect(17.4, 13.4, 4.2)),
                           (30.0, rect(14.0, 11.0, 4.0))], None)
    relief, end = ribbed("relief", 29.0, [(2.0, 4.2), (1.0, 4.2), (1.0, 3.7), (1.0, 4.2), (2.0, 4.2), (1.0, 3.7),
                                          (1.0, 4.0), (2.0, 4.0), (1.0, 3.5), (3.0, 3.2), (0.0, 2.6)], None)
    return [(body, nose), (body, front), (cable, relief)], end


def saturn(body, cable):
    """The Saturn controller's plug: wide and flat, black."""
    nose = along("nose", [(-6.0, rect(23.0, 6.4, 1.5)), (0.0, rect(23.0, 6.4, 1.5))], None)
    shell = along("plug", [(0.0, rect(30.0, 12.0, 3.0)), (20.0, rect(30.0, 12.0, 3.0)), (28.0, rect(20.0, 10.0, 3.5))],
                  None)
    relief, end = ribbed("relief", 27.0, [(4.0, 4.2), (4.0, 3.8), (4.0, 3.2), (0.0, 2.6)], None)
    return [(body, nose), (body, shell), (cable, relief)], end


def d_outline(w_top, w_bottom, h, r):
    """A D-sub's section: a trapezoid, wider at the top, its corners rounded."""
    corners = [(-w_bottom / 2, -h / 2), (w_bottom / 2, -h / 2), (w_top / 2, h / 2), (-w_top / 2, h / 2)]
    out = []
    for i, c in enumerate(corners):
        p, q = Vector(corners[i - 1]), Vector(corners[(i + 1) % 4])
        v = Vector(c)
        a, b = v + (p - v).normalized() * r, v + (q - v).normalized() * r
        for k in range(4):                                  # a quadratic round from a to b about the corner
            t = k / 3
            out.append(tuple(a * (1 - t) ** 2 + v * 2 * t * (1 - t) + b * t * t))
    return out


def dsub(body, cable, h=15.0):
    """The 9-pin D plug of a joystick or a mouse: its housing a D in section, h high, tapering to the cable."""
    nose = along("nose", [(-6.0, d_outline(24.0, 20.0, 8.0, 2.0)), (0.0, d_outline(24.0, 20.0, 8.0, 2.0))], None)
    shell = along("plug", [(0.0, d_outline(33.0, 28.0, h, 3.0)), (16.0, d_outline(33.0, 28.0, h, 3.0)),
                           (28.0, d_outline(22.0, 19.0, h * 0.8, 3.5))], None)
    relief, end = ribbed("relief", 27.0, [(4.0, 4.0), (4.0, 3.5), (4.0, 3.0), (0.0, 2.6)], None)
    return [(body, nose), (body, shell), (cable, relief)], end


def din(body, cable, r=7.6):
    """A round DIN plug, r its grip's radius (7.6 a full-size DIN's, about 5.5 a mini-DIN's): its metal shell in the
    socket, its grip, its strain relief."""
    k = r / 7.6
    nose = along("nose", [(-8.0, circle(6.0 * k)), (0.0, circle(6.0 * k))], None)
    grip = along("plug", [(0.0, circle(7.6 * k)), (3.0, circle(7.6 * k)), (3.0, circle(7.0 * k)),
                          (5.0, circle(7.0 * k)), (5.0, circle(7.8 * k)), (20.0 * k, circle(7.8 * k)),
                          (26.0 * k, circle(5.4 * k))], None)
    relief, end = ribbed("relief", 26.0 * k - 1.0, [(5.0, max(3.0, 4.0 * k)), (5.0, 3.0), (0.0, 2.6)], None)
    return [(body, nose), (body, grip), (cable, relief)], end


def modular(body, cable):
    """A modular plug, most of it in the jack, its boot out of it."""
    plug = along("plug", [(-12.0, rect(9.6, 7.4, 1.0)), (2.0, rect(9.6, 7.4, 1.0)), (2.0, rect(10.6, 8.4, 1.4)),
                          (8.0, rect(8.0, 6.4, 1.6))], None)
    relief, end = ribbed("relief", 7.5, [(4.0, 3.2), (4.0, 2.6), (0.0, 2.2)], None)
    return [(body, plug), (cable, relief)], end


def grommet(cable, r=5.0):
    """A strain relief where a cable leaves a controller or a console, r its foot's radius."""
    relief, end = ribbed("grommet", -2.0, [(2.0, r), (4.0, r * 0.92), (6.0, r * 0.7), (4.0, r * 0.56), (0.0, 2.6)],
                         None)
    return [(cable, relief)], end


def place(parts, end, mat, at, normal, up=(0.0, 0.0, 1.0)):
    """Builds a plug's parts in mat (each coloured by its painter), stands them on a port (at, a point on its face;
    normal, the face's outward normal) and returns the objects and where the cable leaves, with its direction."""
    y = Vector(normal).normalized()
    z = Vector(up) - y * Vector(up).dot(y)
    if z.length < 1e-6:
        z = Vector((0.0, 1.0, 0.0)) - y * y.y
    z.normalize()
    x = y.cross(z)
    frame = Matrix(((x.x, y.x, z.x, at[0]), (x.y, y.y, z.y, at[1]), (x.z, y.z, z.z, at[2]), (0.0, 0.0, 0.0, 1.0)))
    out = []
    for paint_part, obj in parts:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        obj.data.transform(frame)
        paint_part(obj)
        out.append(obj)
    return out, frame @ Vector((0.0, end, 0.0)), y
