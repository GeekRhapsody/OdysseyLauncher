"""The mouse pointer's path for the console theme's cards with a mouse and a screen that's a video (windows3x.py,
windows9x.py, windows_pc.py): one path that both the card's video (the pointer on the screen) and its clip (the mouse on
the table) follow, so they can't drift apart. Plain Python: Blender's Python imports it too. (Flash's card has the same
in flash_layout.py, which came first.)

A path is waypoints (frame, (x, y), whether it stops there), x and y in the screen's own units, y down. The pointer
moves through them on a cubic: easing into and out of its stops, and through the others along their neighbours (a
Catmull-Rom spline), so it never jerks. The mouse moves on the table as the pointer moves on the screen: its travel
from its rest is the pointer's over the gain (the screen's units for a millimetre), along the mouse's own axes, its
forward the screen's up, turned with it.
"""

import math


class Path:
    def __init__(self, waypoints):
        self.points = waypoints

    def _velocity(self, i):
        """The pointer's velocity at waypoint i, in units a frame: none where it stops, else along its neighbours."""
        _f, _p, stops = self.points[i]
        if stops or i in (0, len(self.points) - 1):
            return (0.0, 0.0)
        (fa, a, _), (fb, b, _) = self.points[i - 1], self.points[i + 1]
        return tuple((q - p) / (fb - fa) for p, q in zip(a, b))

    def at(self, f):
        """The pointer's tip at frame f."""
        points = self.points
        for i in range(len(points) - 1):
            (f0, p0, _), (f1, p1, _) = points[i], points[i + 1]
            if f0 <= f < f1:
                if p0 == p1:                                 # a hold
                    return p0
                t, span = (f - f0) / (f1 - f0), f1 - f0
                h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
                h01, h11 = 3 * t ** 2 - 2 * t ** 3, t ** 3 - t ** 2
                return tuple(h00 * a + h10 * span * va + h01 * b + h11 * span * vb
                             for a, b, va, vb in zip(p0, p1, self._velocity(i), self._velocity(i + 1)))
        return points[-1][1] if f >= points[-1][0] else points[0][1]


def mouse_offset(point, rest, gain, turn):
    """The mouse's offset from its rest (x, y in its set's millimetres, y away from the viewer) for the pointer at
    point: the pointer's travel from rest over gain, along the mouse's own axes (its forward the screen's up), turned
    turn degrees about the vertical with it."""
    dx, dy = (point[0] - rest[0]) / gain, -(point[1] - rest[1]) / gain
    t = math.radians(turn)
    return dx * math.cos(t) - dy * math.sin(t), dx * math.sin(t) + dy * math.cos(t)


def held(f, f0, frames):
    """Whether a button pressed at f0 and held for frames is down at frame f."""
    return f0 <= f < f0 + frames
