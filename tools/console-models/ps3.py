"""The console theme's PlayStation 3 system model (godot/themes/console/models/systems/ps3.glb): the original
PlayStation 3.

Built in Blender from the real console's shape (ps3_layout.py has the measurements and how they were taken). The body is
lofted from front to back through its sections: flat across its width, its top a hill from the front edge (the chrome
strip wraps the rounded edge) up to its peak and down to the back, rounded over into each end; the left end flat, the
right end curving in underneath to the base; the slot cut into the drive's face. The base stands under it, set back from
the front. The flap stands out of the front's left half, its right end a wedge back to the body; the lip stands out
under the drive, its top sloping, its nose square. The printing is one texture drawn by ps3_print.py: the top, front,
base, ends and back, planar-mapped onto their faces; the chrome strip mapped round its curve; the disc's two sides; and
swatches.

A node tree (card.finish()): the root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards
the viewer, the top tipped up; then the fit) holding the set; the set holding the disc (waiting in the drive, shrunk to
nothing) and the lit power light (shrunk to nothing).

The `focused` clip (5 s, looping) plays a disc: the Blu-ray is pushed into the slot and the drive takes it, and the
power light turns green, as a disc put in switches the console on; then the disc is ejected and taken away.

Three materials (gloss, matte, disc) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/ps3_print.py artifacts/ps3
    blender -b --factory-startup --python tools/console-models/ps3.py -- artifacts/ps3 godot/themes/console/models/systems/ps3.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps3_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, new_object  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 35.0    # degrees about the horizontal: the top tips up towards the viewer, its logo clear of the crest
ROUGHNESS = dict(gloss=0.16, matte=0.7, disc=0.25)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
W, D = L.WIDTH, L.DEPTH
TOP_Z = 100.0                 # where the ends' and the back's regions start (ps3_print.py)


# ---- UVs -------------------------------------------------------------------------------------------------------------

TOP = ATLAS.uv("top", W, D)
FRONT = ATLAS.uv("front", W, L.FRONT_REGION[1] - L.FRONT_REGION[0])
BASE_FRONT = ATLAS.uv("base", W, L.UNDER)
RIGHT = ATLAS.uv("right", 280.0, TOP_Z)
LEFT = ATLAS.uv("left", 280.0, TOP_Z)
BACK = ATLAS.uv("back", W, 62.0)
STRIP = ATLAS.uv("strip", 1.0, 1.0)


def top_uv(co):
    return TOP(co.x + W / 2, D - co.y)


def front_uv(co):
    return FRONT(co.x + W / 2, L.FRONT_REGION[1] - co.z)


def right_uv(co):
    return RIGHT(co.y, TOP_Z - co.z)


def left_uv(co):
    return LEFT(D - co.y, TOP_Z - co.z)


def back_uv(co):
    return BACK(W / 2 - co.x, 62.0 - co.z)


# ---- The console -----------------------------------------------------------------------------------------------------

def section(zt, floor=L.UNDER):
    """The body's section with its top at zt, anticlockwise seen from the front: up the left end, over the shoulder,
    across, over the other shoulder, down the right end and in underneath, back along the underside."""
    r = L.SHOULDER
    pts = [(-W / 2, floor)]
    for k in range(9):
        a = math.radians(180 - 90 * k / 8)
        pts.append((-W / 2 + r + r * math.cos(a), zt - r + r * math.sin(a)))
    for k in range(9):
        a = math.radians(90 - 90 * k / 8)
        pts.append((W / 2 - r + r * math.cos(a), zt - r + r * math.sin(a)))
    zt_, steps = L.RIGHT_TURN["z"], 7
    for k in range(steps + 1):
        z = zt_ - (zt_ - floor) * k / steps
        pts.append((L.right_x(z), z))
    return pts


def body_rings():
    """The rings the body is lofted through, front to back: (y, the top's height there, the front rounding's angle or
    None). The front edge is a quarter circle round the chrome strip, the back edge a smaller one."""
    rings = []
    rf, rb = L.FRONT_ROUND, L.BACK_ROUND
    cz = L.top_z(L.FACE + rf) - rf
    for k in range(9):
        a = math.radians(90 * k / 8)
        rings.append((L.FACE + rf * (1 - math.cos(a)), cz + rf * math.sin(a), k / 8))
    y0, y1 = L.FACE + rf, D - rb
    n = 44
    for k in range(1, n):
        y = y0 + (y1 - y0) * k / n
        rings.append((y, L.top_z(y), None))
    cb = L.top_z(D - rb) - rb
    for k in range(6):
        a = math.radians(90 * k / 5)
        rings.append((D - rb + rb * math.sin(a), cb + rb * math.cos(a), None))
    return rings, cz


def body(m):
    """The body: lofted through its sections, the slot cut into the drive's face; printed."""
    rings, cz = body_rings()
    part = solid("ps3", [[(x, y, z) for x, z in section(zt)] for y, zt, _ in rings], m["gloss"])
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    boolean(part, box("slot", sx0, sx1, L.FACE - 3.0, L.FACE + L.SLOT["depth"], sz0, sz1, m["gloss"]))
    coloured(part, m["gloss"], ATLAS, "case")
    yc = L.FACE + L.FRONT_ROUND

    def strip_uv(co):
        # The chrome strip round the front edge: across its width, and round its curve from the top to the front.
        ang = math.atan2(co.z - cz, yc - co.y)
        return STRIP((co.x + W / 2) / W, 1 - min(1.0, max(0.0, ang / (math.pi / 2))))
    paint(part, m["gloss"], top_uv, lambda c, n, name: n.z > 0.35 and c.y > yc - 0.5)
    paint(part, m["gloss"], strip_uv, lambda c, n, name: c.y < yc + 0.2 and c.z > cz - 0.3 and n.y < -0.02
          and n.z > -0.2)
    paint(part, m["gloss"], front_uv, lambda c, n, name: n.y < -0.9 and c.z < cz + 0.2)
    paint(part, m["gloss"], right_uv, lambda c, n, name: n.x > 0.35)
    paint(part, m["gloss"], left_uv, lambda c, n, name: n.x < -0.35)
    paint(part, m["gloss"], back_uv, lambda c, n, name: n.y > 0.5)
    paint(part, m["gloss"], ATLAS.swatch("under"), lambda c, n, name: n.z < -0.5)
    paint(part, m["gloss"], ATLAS.swatch("slot"), lambda c, n, name: sx0 - 0.1 < c.x < sx1 + 0.1
          and sz0 - 0.1 < c.z < sz1 + 0.1 and c.y > L.FACE + 0.1)
    return part


def base(m):
    """The base under the body, set back from the front: the right end's curve carried down to the table."""
    pts = [(L.BASE["left"], 0.0)]
    zt, steps = L.RIGHT_TURN["z"], 10
    ellipse = [(L.right_x(z), z) for z in (L.UNDER * k / steps for k in range(steps + 1))]
    pts += ellipse + [(L.BASE["left"], L.UNDER)]
    part = solid("base", [[(x, y, z) for x, z in pts] for y in (L.BASE["front"], L.BASE["back"])], m["matte"])
    coloured(part, m["matte"], ATLAS, "matte")
    paint(part, m["matte"], lambda co: BASE_FRONT(co.x + W / 2, L.UNDER - co.z), lambda c, n, name: n.y < -0.9)
    paint(part, m["matte"], right_uv, lambda c, n, name: n.x > 0.35)
    paint(part, m["matte"], left_uv, lambda c, n, name: n.x < -0.35)
    paint(part, m["matte"], back_uv, lambda c, n, name: n.y > 0.5)
    paint(part, m["matte"], ATLAS.swatch("under"), lambda c, n, name: n.z < -0.5)
    return part


def flap(m):
    """The flap over the card slots, standing out of the front's left half; its right end a wedge back to the body."""
    (x0, x1), top = L.FLAP["x"], L.FLAP["top"]
    u, f = L.UNDER, L.FACE + 0.5

    def profile(x, back, drop):
        return [(x, back, u + drop), (x, f, u + drop), (x, f, top - drop), (x, back + 0.7, top - drop),
                (x, back, top - drop - 0.7)]
    part = solid("flap", [profile(x0, 0.0, 0.0), profile(x1, 0.0, 0.0), profile(L.FLAP["wedge"], L.FACE - 0.6, 2.0)],
                 m["gloss"])
    bevel(part, 0.6, segments=1, angle=40)
    coloured(part, m["gloss"], ATLAS, "case")
    paint(part, m["gloss"], front_uv, lambda c, n, name: n.y < -0.9)
    paint(part, m["gloss"], ATLAS.swatch("wedge"), lambda c, n, name: c.x > x1 + 0.2 and n.y > -0.9 and n.x > 0.2)
    return part


def lip(m):
    """The lip under the drive: its top sloping down from the drive's face to its nose, its face square."""
    (x0, x1), u = L.LIP["x"], L.UNDER
    prof = [(0.0, u), (L.FACE + 0.5, u), (L.FACE + 0.5, L.LIP["top"]), (0.9, L.LIP["nose"] + 0.6),
            (0.0, L.LIP["nose"])]
    part = solid("lip", [[(x, y, z) for y, z in prof] for x in (x0, x1)], m["gloss"])
    bevel(part, 0.5, segments=1, angle=40)
    coloured(part, m["gloss"], ATLAS, "case")
    paint(part, m["gloss"], front_uv, lambda c, n, name: n.y < -0.3 and n.z > -0.3)
    return part


def power_light(m):
    """The power light lit green: its two bars on the lip's face."""
    lx, lz = L.LIGHT["at"]
    lw, lh = L.LIGHT["size"]
    bars = [box("bar", k * 0.9 - 0.4, k * 0.9 + 0.4, -0.25, 0.3, -lh / 2, lh / 2, m["gloss"]) for k in (-1, 1)]
    part = coloured(join(bars, "power_light"), m["gloss"], ATLAS, "green")
    return part, Vector((lx, 0.0, lz))


def disc(m):
    """The Blu-ray, its middle at its origin, lying flat: a ring, its label on its top, its data side under it."""
    ro, ri, t = L.DISC["diameter"] / 2, L.DISC["hole"] / 2, L.DISC["thickness"]
    n = 64
    bm = bmesh.new()
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), z)) for k in range(n)]
             for r, z in ((ro, -t / 2), (ro, t / 2), (ri, t / 2), (ri, -t / 2))]
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new([a[k], a[j], b[j], b[k]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    part = new_object("disc", bm, m["disc"])
    dm = L.DISC["diameter"]
    label = ATLAS.uv("label", dm, dm)
    data = ATLAS.uv("disc", dm, dm)
    coloured(part, m["disc"], ATLAS, "silver")
    paint(part, m["disc"], lambda co: label(co.x + dm / 2, dm / 2 - co.y), lambda c, n_, name: n_.z > 0.9)
    paint(part, m["disc"], lambda co: data(co.x + dm / 2, dm / 2 + co.y), lambda c, n_, name: n_.z < -0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def timeline(f):
    seat_y = L.SEAT[1]
    r = L.DISC["diameter"] / 2
    wait = (L.FACE - r - 2.0) - seat_y                    # the disc's offset from its seat while it waits outside
    if f < 8 or f >= 138:
        dsk = Pose(scale=HIDDEN)
    elif f < 18:
        dsk = Pose(y=wait, scale=appear(f, 8, 18))
    elif f < 32:
        dsk = Pose(y=wait + 34.0 * smooth(phase(f, 18, 32)))           # pushed in by hand, a third of the way
    elif f < 42:
        dsk = Pose(y=(wait + 34.0) * (1 - ease_in(phase(f, 32, 42))))   # the drive takes it
    elif f < 106:
        dsk = Pose()
    elif f < 120:
        dsk = Pose(y=(wait + 40.0) * ease_out(phase(f, 106, 116)))     # ejected, half out
    else:
        lift = ease_in(phase(f, 124, 138))
        dsk = Pose(y=wait + 40.0 - 60.0 * smooth(phase(f, 120, 130)), z=30.0 * lift, scale=max(HIDDEN, 1 - lift))
    return {"disc": dsk, "power_light": Pose() if f >= 44 else Pose(scale=HIDDEN)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "ps3_print.png"))
    m = materials(L.COLOURS, ROUGHNESS, {name: printed for name in ROUGHNESS})

    whole = join([smoothed(body(m)), smoothed(base(m)), smoothed(flap(m)), smoothed(lip(m))], "ps3")
    lit, lit_at = power_light(m)
    parts = {"disc": (smoothed(disc(m)), Vector(L.SEAT)), "power_light": (smoothed(lit), lit_at)}
    finish("ps3", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "PlayStation 3")


if __name__ == "__main__":
    main()
