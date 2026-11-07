"""The console theme's Steam system model (godot/themes/console/models/systems/steam.glb): the first Steam Deck,
standing up.

Built in Blender from steam_deck_layout.py's measurements (it has their sources). The shell is lofted up the Deck
through slices across it, each the face's width at its height (the outline's corners) from the face round the ends and
their grips to the back: each grip at its full depth from GRIP_RISE to GRIP_TOP, its inner flank gentle at the bottom
and steep beside the back buttons, rounding over below (sweeping in with the outline at the bottom corners) and above,
into the notch under the trigger; the face's and the back's edges rounded over to the top and the bottom edge; the face
rolling back into each grip below its seam. At each top corner, the bumper (a strip round the corner) and the trigger
(what its outlines from the end, from behind and from above have in common, each finely divided, so it comes out
rounded). On the face stand the D-pad, A, B, X and Y, View, Menu, STEAM and the quick access button, each a solid domed
over; the trackpads, flat plates; the sticks' housings, and the sticks: a light grey dome, a shaft and a dished cap.
The glass is one flat face in front of the face. On the top edge, POWER and VOL - and +; on the back, the four grip
buttons. The printing is one texture drawn by steam_deck_print.py (the face, the back, the top and the bottom edge,
planar-mapped onto the faces that look their way; swatches for the rest), the screens another.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
face tipped up a little; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the deck,
which is picked up about its middle; the deck holding the sticks (each about its pivot behind the face), the right
trackpad, STEAM, A, the right trigger (about its pivot) and the screens, stacked in front of the glass, each shrunk to
nothing until it's shown.

The `focused` clip (6 s, looping; steam_deck_layout.py has its timing) picks the Deck up, wakes it with STEAM (the boot
screen, then the library, its first game chosen), launches the game with A and plays it on the sticks, the right
trackpad and the right trigger, rumbling once, then puts it to sleep and down.

Four materials (case, buttons, glass, media) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/steam_deck_print.py artifacts/made-up-games artifacts/steam_deck
    blender -b --factory-startup --python tools/console-models/steam_deck.py -- artifacts/steam_deck godot/themes/console/models/systems/steam.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import steam_deck_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas  # noqa: E402
from clip import Pose, key, phase, smooth  # noqa: E402
from devices import showing_poses, tap, taps  # noqa: E402
from handheld import circle, screens, stadium  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import boolean, export, join, material, new_object, prism_x, triangles  # noqa: E402
from saturn import inset  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end (A, B, X and Y) comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.62, buttons=0.45, glass=0.35, media=0.55)   # glossier, the key light washes the screen out
PIVOT = Vector((0.0, L.DEPTH / 2, L.HEIGHT / 2))   # the deck is picked up about its middle
PRESS = 0.8                                        # how far a button goes in
GLASS_Y = -0.3                                     # the glass in front of the face, the screens in front of it: apart
                                                   # enough not to fight for the same pixels at a card's size

ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
SCREENS = Atlas(L.SCREEN_SIZE, L.SCREENS)


def planar(region, flip=False):
    """UVs for the faces looking at a region's view: (x, z) for the face and the back (flip: seen from behind), (x, y)
    for the top edge (its back at the region's top) and the bottom edge (its face at the region's top)."""
    x0, x1, v0, v1 = L.SPANS[region]
    uv = ATLAS.uv(region, x1 - x0, v1 - v0)
    if region in ("front", "rear"):
        return lambda co: uv((x1 - co.x) if flip else (co.x - x0), v1 - co.z)
    if region == "top":
        return lambda co: uv(co.x - x0, v1 - co.y)
    return lambda co: uv(co.x - x0, co.y - v0)


FRONT, REAR, TOP, BOTTOM = planar("front"), planar("rear", True), planar("top"), planar("bottom")


def shade(obj, angle=38.0):
    """Smooth shading, edges sharper than angle kept sharp; caps (more than four corners) stay flat."""
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) <= 4
    obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


def at_origin(obj, where):
    """The part's mesh moved so that where (in the deck) is its origin: it moves from there."""
    obj.data.transform(Matrix.Translation(-Vector(where)))
    return obj, Vector(where)


def prism_y(name, outline, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1."""
    return solid(name, [[(x, y, z) for x, z in outline] for y in (y0, y1)], mat)


def along(points, n):
    """n points evenly along a polyline, both ends included."""
    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.dist(a, b))
    out, i = [], 0
    for k in range(n):
        s = lengths[-1] * k / (n - 1)
        while i < len(points) - 2 and lengths[i + 1] < s:
            i += 1
        t = (s - lengths[i]) / max(1e-9, lengths[i + 1] - lengths[i])
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


# ---- The shell -------------------------------------------------------------------------------------------------------

def half_width(z):
    """The face's outline: its half-width at height z (its corners quarter superellipses)."""
    for (a, b, n), dz in ((L.TOP_CORNER, z - (L.HEIGHT - L.TOP_CORNER[1])), (L.BOTTOM_CORNER, L.BOTTOM_CORNER[1] - z)):
        if dz > 0:
            t = min(1.0, dz / b)
            return L.HALF - a + a * (1 - t ** n) ** (1 / n)
    return L.HALF


def corner_point(t):
    """The top right corner's superellipse at parameter t (0 down the end, pi / 2 along the top)."""
    a, b, n = L.TOP_CORNER
    return (L.HALF - a + a * math.cos(t) ** (2 / n), L.HEIGHT - b + b * math.sin(t) ** (2 / n))


def grip_weight(z):
    """How far the grips stand out at height z: 0 (the back's depth) to 1 (their full depth), rounding over from the
    bottom edge, sinking to the notch under the trigger and into the trigger's piece."""
    r0, r1, power = L.GRIP_RISE
    if z < r1:
        return max(0.0, (z - r0) / (r1 - r0)) ** power
    t0, t1, notch, n0, n1 = L.GRIP_TOP
    t = phase(z, t0, t1)
    return (notch + (1 - notch) * math.sqrt(1 - t * t)) * (1 - smooth(phase(z, n0, n1)))


def seam_x(z, seam):
    """Where a seam (from its top along the outline down to the bottom edge) is across at height z."""
    for (xa, za), (xb, zb) in zip(seam, seam[1:]):
        if zb <= z <= za and za > zb:
            return xa + (xb - xa) * (za - z) / (za - zb)
    return seam[0][0]


# The right half of a slice at full width, in runs from the middle of the face round the end to the middle of the
# back. The face and its edge are the same at every height; the end with the grip (its flank from gentle to steep up
# the Deck), and the end without it, are blended by grip_weight(); the back runs from the flank's foot to the middle.
RUNS = dict(face=along([(0.0, 0.0), L.FRONT_EDGE[0]], 8), edge=along(L.FRONT_EDGE, 7))
_corner = [(L.HALF - L.BACK_CORNER + L.BACK_CORNER * math.cos(a), L.DEPTH - L.BACK_CORNER + L.BACK_CORNER * math.sin(a))
           for a in [math.pi / 2 * k / 6 for k in range(7)]]
GRIP_END, BARE_END = along(L.LOBE[:L.CREST + 1], 15), along([L.LOBE[0]] + _corner, 15)
STEEP, GENTLE = along(L.FLANK, 9), along(L.LOBE[L.CREST:], 9)


def right_half(z):
    """A slice's right half at height z (x, y): the face (rolled back into the grip below its seam), its edge, the end
    and the grip, the back to the middle; narrowed beyond SQUEEZE to the outline's width there."""
    w, s = grip_weight(z), smooth(phase(z, *L.STEEPEN))
    flank = [(gx + (sx - gx) * s, gy + (sy - gy) * s) for (sx, sy), (gx, gy) in zip(STEEP, GENTLE)]
    bare = BARE_END + along([BARE_END[-1], flank[-1]], len(flank))[1:]
    blend = [((1 - w) * bx + w * gx, (1 - w) * by + w * gy) for (bx, by), (gx, gy) in zip(bare, GRIP_END + flank[1:])]
    face = RUNS["face"] + RUNS["edge"][1:]
    back = along([flank[-1], (0.0, L.DEPTH)], 9)
    k = (half_width(z) - L.SQUEEZE) / (L.HALF - L.SQUEEZE)
    squeeze = [(x if x <= L.SQUEEZE else L.SQUEEZE + (x - L.SQUEEZE) * k, y) for x, y in face + blend[1:] + back[1:]]
    # Below the seam the face rolls back into the grip: nothing at the seam, ROLL where the edge's rounding starts.
    fade = 1 - smooth(phase(z, 64.0, 76.0))
    start = L.SQUEEZE + (L.FRONT_EDGE[0][0] - L.SQUEEZE) * k
    seam = seam_x(z, L.SEAM_FRONT)
    n_face, n_edge = len(RUNS["face"]), len(RUNS["edge"])
    roll, end = (L.ROLL * fade if seam < start else 0.0), L.FRONT_EDGE[-1][1]
    out = []
    for i, (x, y) in enumerate(squeeze):
        if i < n_face and roll:
            y += roll * min(1.0, max(0.0, (x - seam) / (start - seam))) ** 1.5
        elif i < n_face + n_edge - 1:
            y = roll + y * (end - roll) / end              # the edge from the rolled face to the end, as it was
        out.append((x, y))
    return out


def rounding(z, r):
    """How far an edge of radius r rounding over to the top or the bottom edge has come in at height z."""
    d = max(r - z, z - (L.HEIGHT - r))
    return r - math.sqrt(max(0.0, r * r - d * d)) if d > 0 else 0.0


def ring(z):
    """A whole slice at height z: both halves, its face and back edges rounded over near the top and the bottom."""
    half = right_half(z)
    loop = half + [(-x, y) for x, y in reversed(half)][1:-1]
    front, back = rounding(z, L.FRONT_ROUND), rounding(z, L.BACK_ROUND)
    out = []
    n = len(loop)
    for i, (x, y) in enumerate(loop):
        (xa, ya), (xb, yb) = loop[i - 1], loop[(i + 1) % n]
        tx, ty = xb - xa, yb - ya
        length = math.hypot(tx, ty) or 1.0
        nx, ny = ty / length, -tx / length          # outwards: the loop runs anticlockwise seen from above
        move = front * max(0.0, -ny) + back * max(0.0, ny)
        out.append((x - nx * move, y - ny * move, z))
    return out


SLICES = [0.0, 0.35, 1.0, 1.5, 2.2, 2.8, 3.6, 4.3, 5.5, 7.0, 8.8, 11.0, 13.5, 16.0, 19.0, 22.0, 26.0, 32.0, 42.0,
          54.0, 62.0, 68.0, 71.0, 74.0, 77.0, 80.0, 84.0, 89.0, 93.0, 95.0, 97.0, 100.0, 103.5, 107.0, 110.0, 112.1,
          113.6, 114.6, 115.4, 116.0, L.HEIGHT]


def shell(m):
    """The shell lofted through the slices, printed: the face, the back, the top and the bottom edge each from its
    region, the rest the case's colour."""
    obj = solid("deck", [ring(z) for z in SLICES], m["case"])
    edge = L.SPANS["top"][3] - 0.2             # the edges' regions end here: the grips' tops and bottoms are beyond
    paint(obj, m["case"], ATLAS.swatch("case"), lambda c, n, kind: True)
    paint(obj, m["case"], FRONT, lambda c, n, kind: n.y < -0.35)
    paint(obj, m["case"], REAR, lambda c, n, kind: n.y > 0.35)
    paint(obj, m["case"], TOP, lambda c, n, kind: n.z > 0.75 and c.y < edge)
    paint(obj, m["case"], BOTTOM, lambda c, n, kind: n.z < -0.75 and c.y < edge)
    return shade(obj)


# ---- The shoulders ---------------------------------------------------------------------------------------------------

def corner_band(side_z, inner, proud, inward=3.0):
    """The face's outline round the top right corner, from side_z on the end up round the corner and along the top to
    inner, as a band from inward inside it to outside it: proud = (how far, (x0, x1)), that far over the top edge and
    going flush round the corner from x0 to x1."""
    a, b, n = L.TOP_CORNER
    outward, (f0, f1) = proud
    t0 = math.asin(min(1.0, max(0.0, (side_z - (L.HEIGHT - b)) / b)) ** (n / 2))
    path = [corner_point(t0 + (math.pi / 2 - t0) * k / 12) for k in range(13)]
    path += [(x, L.HEIGHT) for x in [L.HALF - a - (L.HALF - a - inner) * k / 4 for k in range(1, 5)]]
    out, back = [], []
    for i, (x, z) in enumerate(path):
        (xa, za), (xb, zb) = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
        length = math.hypot(xb - xa, zb - za)
        nx, nz = (zb - za) / length, -(xb - xa) / length     # outwards: the path runs anticlockwise
        reach = outward * min(1.0, max(0.0, (f1 - x) / (f1 - f0)))
        out.append((x + nx * reach, z + nz * reach))
        back.append((x - nx * inward, z - nz * inward))
    return out + list(reversed(back))


def bumper(side, m):
    """R1 (side 1) or L1 (-1): a strip lying over the top corner, from the face's edge back to the trigger."""
    b = L.BUMPER
    band = corner_band(b["side_z"], b["inner"], (b["proud"], b["flush"]))
    plan = [(108.3, b["front"]), (153.0, b["front"]), (153.0, L.BUMPER_BACK[0][1] - 0.5), L.BUMPER_BACK[1],
            (110.5, 19.0), (106.5, 15.8), (104.6, 13.0), (104.8, 10.4), (106.2, 8.6)]
    part = prism_y("bumper", band, b["front"], 26.0, m["case"])
    boolean(part, prism_z("plan", plan, 80.0, 130.0, m["case"]), "INTERSECT")
    paint(part, m["case"], ATLAS.swatch("shoulder"), lambda c, n, kind: True)
    if side < 0:
        part.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
        part.data.flip_normals()
    return shade(part, 30.0)


def trigger(side, m):
    """R2 (side 1) or L2 (-1): what its profile from the end, its outline from behind (round the corner above where
    its ramp turns down) and the grip's outline behind the bumper from above have in common, each finely divided, so
    it comes out rounded. Its back takes the back's printing (its outline)."""
    profile = along(L.TRIGGER_PROFILE, 40) + L.TRIGGER_UNDER + [(15.0, L.TRIGGER_PROFILE[0][1])]
    part = prism_x("trigger", profile, 100.0, 155.0, m["case"])
    inner, outer = L.TRIGGER_BACK[7], L.TRIGGER_BACK[0]
    behind = along(L.TRIGGER_BACK[7:] + [outer], 40) + corner_band(outer[1], inner[0], L.TRIGGER_PROUD)[:17]
    boolean(part, prism_y("behind", behind, 0.0, 50.0, m["case"]), "INTERSECT")
    plan = [L.BUMPER_BACK[1], (L.HALF - 0.1, L.BUMPER_BACK[0][1])] + [p for p in L.LOBE[3:] if p[1] > 21.0]
    boolean(part, prism_z("plan", plan, 80.0, 130.0, m["case"]), "INTERSECT")
    if side < 0:
        part.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
        part.data.flip_normals()
    paint(part, m["case"], ATLAS.swatch("shoulder"), lambda c, n, kind: True)
    paint(part, m["case"], REAR, lambda c, n, kind: n.y > 0.35)
    return shade(part, 40.0)


# ---- The controls ----------------------------------------------------------------------------------------------------

def domed(name, outline_at, height, dome, mat, swatch="button", rings_=4, back=False):
    """A button standing out of the face (or the back): its foot inside, straight sides out to height, then a dome
    (inset, rise) over; outline_at(inset) its rim. Its top takes the face's (or the back's) printing, its sides a
    swatch."""
    s, y0 = (1.0, L.DEPTH) if back else (-1.0, 0.0)
    stack = [(outline_at(0.0), y0 - s * 0.6), (outline_at(0.0), y0 + s * height)]
    for k in range(1, rings_ + 1):
        a = math.pi / 2 * k / rings_
        stack.append((outline_at(dome[0] * (1 - math.cos(a))), y0 + s * (height + dome[1] * math.sin(a))))
    obj = solid(name, [[(x, y, z) for x, z in pts] for pts, y in stack], mat)
    paint(obj, mat, ATLAS.swatch(swatch), lambda c, n, kind: True)
    if back:
        paint(obj, mat, REAR, lambda c, n, kind: n.y > 0.35)
    else:
        paint(obj, mat, FRONT, lambda c, n, kind: n.y < -0.35)
    return shade(obj, 50.0)


def outline(points):
    """outline_at for a fixed outline: inset (mitred) as the dome rises."""
    return lambda d: inset(points, d) if d > 1e-6 else points


def stick(name, x, z, m):
    """A stick: its light grey dome rising out of the housing, the shaft, the cap with its rim rounded and its top
    dished; the cap's top takes the face's printing."""
    s = L.STICK
    c0, c1 = s["cap_y"]
    r, rise, h = s["dome"], s["dome_rise"], s["housing"]
    profile = [(r - 0.1, -h + 0.4), (r, -h), (r - 0.6, -h - rise * 0.45), (r - 1.8, -h - rise * 0.8),
               (r - 3.6, -h - rise * 0.98), (s["shaft"], -h - rise), (s["shaft"], -c0 + 0.2), (s["cap"] - 1.4, -c0),
               (s["cap"] - 0.3, -c0 - 0.3), (s["cap"], -c0 - 0.8), (s["cap"], -c1 + 0.6), (s["cap"] - 0.3, -c1 + 0.1),
               (s["cap"] - 1.0, -c1), (s["cap"] - 2.5, -c1 + s["dish"] * 0.6), (3.5, -c1 + s["dish"] * 0.9),
               (1.0, -c1 + s["dish"])]
    part = solid(name, [[(px, y, pz) for px, pz in circle(x, z, pr, 36)] for pr, y in profile], m["buttons"])
    paint(part, m["buttons"], ATLAS.swatch("dome"), lambda c, n, kind: True)
    paint(part, m["buttons"], ATLAS.swatch("cap"), lambda c, n, kind: c.y < -c0 + 0.3)
    paint(part, m["buttons"], FRONT, lambda c, n, kind: c.y < -c1 + 0.9 and n.y < -0.5)
    return shade(part, 50.0)


def housing(x, z, m):
    """A stick's housing: a low cone on the face, its top edge rounded."""
    s = L.STICK
    b, t, h = s["base"], s["top"], s["housing"]
    profile = [(b, 0.6), (b, 0.0), (b - 0.35, -0.6), (t + 1.4, -h + 0.5), (t + 0.5, -h + 0.05), (t, -h)]
    part = solid("housing", [[(px, y, pz) for px, pz in circle(x, z, pr, 40)] for pr, y in profile], m["buttons"])
    paint(part, m["buttons"], FRONT, lambda c, n, kind: True)
    return shade(part, 50.0)


def controls(m):
    """The buttons, pads and sticks: the still ones joined into the set; those the clip moves apart."""
    still, moving = [], {}
    d = L.DPAD
    for k, (w, h) in enumerate(((d["span"], d["arm"]), (d["arm"], d["span"]))):   # its arms, across a hair lower
        arm = rounded(d["x"], d["z"], w, h, 1.3, 3)
        still.append(domed("dpad", outline(arm), d["height"] - 0.75 + 0.15 * k, (0.8, 0.6), m["buttons"]))
    a = L.ABXY
    for name, degrees in L.FACE_BUTTONS:
        bx = a["x"] + a["reach"] * math.cos(math.radians(degrees))
        bz = a["z"] + a["reach"] * math.sin(math.radians(degrees))
        part = domed("face_" + name, lambda dd, bx=bx, bz=bz: circle(bx, bz, a["r"] - dd, 32), a["height"] - 0.7,
                     (1.2, 0.7), m["buttons"])
        if name == "a":
            moving["a"] = at_origin(part, (bx, 0.0, bz))
        else:
            still.append(part)
    for name, (px, pz, length, width) in L.PILLS.items():
        part = domed("pill_" + name, lambda dd, px=px, pz=pz, length=length, width=width:
                     stadium(px, pz, length - 2 * dd, width - 2 * dd, n=8), L.PILL_HEIGHT - 0.5, (0.7, 0.5),
                     m["buttons"])
        if name == "steam":
            moving["steam"] = at_origin(part, (px, 0.0, pz))
        else:
            still.append(part)
    p = L.PADS
    for side in ("left", "right"):
        px, pz = p[side]
        square = rounded(px, pz, p["size"], p["size"], p["r"], 4)
        part = domed("pad_" + side, outline(square), 0.15, (0.4, 0.15), m["case"], swatch="pad", rings_=2)
        if side == "right":
            moving["pad_right"] = at_origin(part, (px, 0.0, pz))
        else:
            still.append(part)
    for side, (sx, sz) in L.STICKS.items():
        still.append(housing(sx, sz, m))
        moving["stick_" + side] = at_origin(stick("stick_" + side, sx, sz, m), (sx, 6.0, sz))
    q = L.PADDLES
    for name in ("r4", "r5", "l4", "l5"):
        px, pz = q[name]
        square = rounded(px, pz, q["size"], q["size"], q["r"], 4)
        still.append(domed("paddle_" + name, outline(square), q["proud"] - 0.35, (0.8, 0.35), m["case"],
                           swatch="case", rings_=2, back=True))
    return still, moving


def top_buttons(m):
    """POWER and VOL - and +: short buttons standing on the top edge, their tops the top edge's printing."""
    t = L.TOP
    parts = []
    for x in (t["power"],) + t["volume"]:
        r, h = t["button_r"], t["button_height"]
        rings_ = [(r, -0.6), (r, h - 0.25), (r - 0.3, h - 0.03), (r - 0.7, h)]
        part = solid("top_button", [[(px, py, L.HEIGHT + dz) for px, py in circle(x, t["y"], rr, 28)]
                                    for rr, dz in rings_], m["buttons"])
        paint(part, m["buttons"], ATLAS.swatch("button"), lambda c, n, kind: True)
        paint(part, m["buttons"], TOP, lambda c, n, kind: n.z > 0.5)
        parts.append(shade(part, 50.0))
    return parts


def glass(m):
    """The glass round the display: one flat face just in front of the face, printed as the face is there."""
    g = L.GLASS
    corners = rounded(g["x"], g["z"], g["width"], g["height"], g["r"], 3)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new((x, GLASS_Y, z)) for x, z in corners])   # anticlockwise seen from the front: faces -y
    obj = new_object("glass", bm, m["glass"])
    paint(obj, m["glass"], FRONT, lambda c, n, kind: True)
    return obj


# ---- The clip --------------------------------------------------------------------------------------------------------

def showing(f):
    for f0, f1, name in L.SHOWING:
        if f0 <= f < f1:
            return name
    p0, p1 = L.PLAY
    if p0 <= f < p1:
        return "game1" if ((f - p0) // 8) % 2 == 0 else "game2"
    return None


def timeline(f):
    poses = showing_poses(("boot", "library", "game1", "game2"), showing, f)
    l0, l1, d0, d1 = L.LIFT
    up = smooth(phase(f, l0, l1)) * (1 - smooth(phase(f, d0, d1)))
    r0, r1 = L.RUMBLE
    shake = 1.6 * math.sin(f * 2.7) if r0 <= f < r1 else 0.0
    poses["deck"] = Pose(z=20.0 * up, pitch=-12.0 * up, roll=shake)
    poses["steam"] = Pose(y=PRESS * tap(f, L.WAKE))
    poses["a"] = Pose(y=PRESS * tap(f, L.LAUNCH))
    poses["pad_right"] = Pose(y=0.35 * taps(f, L.PAD_TAPS))
    poses["trigger_right"] = Pose(pitch=-L.TRIGGER_PULL * taps(f, L.TRIGGER_PULLS, hold=5))
    # The sticks play: each swings its cap about its pivot behind the face (spin across, pitch, negated, up).
    t = phase(f, *L.PLAY)
    wave = math.sin(math.pi * t)
    tilt = L.STICK["tilt"]
    poses["stick_left"] = Pose(spin=tilt * math.sin(2 * math.pi * 2 * t) * wave,
                               pitch=-tilt * 0.8 * math.sin(2 * math.pi * 3 * t) * wave)
    poses["stick_right"] = Pose(spin=tilt * 0.7 * math.sin(2 * math.pi * 3 * t + 1.0) * wave,
                                pitch=-tilt * 0.6 * math.sin(2 * math.pi * 2 * t) * wave)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def finish(whole, parts, out):
    """The node tree, keyed and fitted: the root (the turn and the fit) holds the deck, keyed about its middle, which
    holds the parts, each at its place in the deck."""
    scene = bpy.context.scene
    root = bpy.data.objects.new("steam_root", None)
    scene.collection.objects.link(root)
    whole.data.transform(Matrix.Translation(-PIVOT))
    whole.parent = root
    whole.location = PIVOT
    nodes = {"deck": whole}
    for name, (obj, where) in parts.items():
        obj.parent = whole
        obj.location = where - PIVOT
        nodes[name] = obj
    key("focused", nodes, timeline, L.LENGTH)
    bpy.context.view_layer.update()

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    meshes = list(nodes.values())
    points = [tilt @ (o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt
    textures = {node.image.name for o in meshes for mat in o.data.materials if mat.node_tree
                for node in mat.node_tree.nodes if node.type == "TEX_IMAGE" and node.image}
    print(f"Steam Deck: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, {len(textures)} textures, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "steam_deck_print.png"))
    shown = bpy.data.images.load(os.path.join(images, "steam_deck_screens.jpg"))
    textures = dict(case=printed, buttons=printed, glass=printed, media=shown)
    m = {n: material(n, "#FFFFFF", r, textures[n]) for n, r in ROUGHNESS.items()}

    still, moving = controls(m)
    shoulders = [bumper(side, m) for side in (1, -1)] + [trigger(-1, m)]
    whole = join([shell(m), glass(m)] + still + top_buttons(m) + shoulders, "deck")
    parts = dict(moving)
    s = L.SCREEN
    for name, (part, where) in screens(["boot", "library", "game1", "game2"], s["width"], s["height"], SCREENS,
                                       m["media"], (s["x"], GLASS_Y, s["z"]), step=0.25).items():
        parts[name] = (part, where)
    y, z = L.TRIGGER_PIVOT
    parts["trigger_right"] = at_origin(trigger(1, m), (132.0, y, z))
    finish(whole, parts, out)


if __name__ == "__main__":
    main()
