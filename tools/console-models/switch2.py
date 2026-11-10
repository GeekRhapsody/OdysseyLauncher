"""The console theme's Nintendo Switch 2 system model (godot/themes/console/models/systems/switch2.glb): the Nintendo
Switch 2 with its Joy-Con 2, in tabletop mode, leaning back on its kickstand.

Built in Blender from switch2_layout.py's measurements (it has their sources). The console is its face's outline (a
rectangle, its corners rounded a little) lofted back through its depth, its face's edge and its back's rounded over,
a channel cut into each end for a Joy-Con 2's tongue, coloured inside (blue at the left, red at the right) round its
connector; on its top edge POWER and VOLUME; on its face the glass, one flat face just in front of it, and in front of
that the screen, the `video` material. Each Joy-Con 2 is its face's outline, traced from Nintendo's render, lofted back
the same way (its inner edge left square, to meet the console), the tongue standing out of its inner edge, the
trigger (ZR or ZL) behind its top outer corner (what its outline from behind and its profile from the side have in
common), the release button on its back, and on its face the stick (its cap, and the coloured ring round its foot),
X, A, B and Y or the direction buttons, + or -, HOME and C or the capture button, each standing out of it. The
kickstand is a U, two legs hinged on the back half-way up and a bar between their ends, turned open until the bar
rests on the table. The printing is two textures drawn by switch2_print.py (the face and the edges in one atlas; the
back, the Joy-Con 2's inner sides and the console's ends in another).

The screen is the `video` material: while the card is focused, the launcher plays the theme's video for it there
(godot/themes/console/videos/switch2.mp4, drawn by switch2_video.py), starting it again each time the clip loops (A6
Card videos); otherwise, and where there's no decoder, it shows its own texture, the screen switched off.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, seen
a little from above; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the console
(everything the clip doesn't move, leant back LEAN degrees on its kickstand), which rocks about where it rests on the
table; the console holding POWER and the right Joy-Con 2.

The `focused` clip (12 s, looping; its timing is switch2_layout.py's, which the video follows) uses a Joy-Con 2 as a
mouse, the Switch 2's own way: POWER wakes the console to the HOME Menu; the right Joy-Con 2's release button pushes it
a little out of its channel, and it's drawn out, turned onto its side and set down to the console's right, its
attachment side on the table and its face towards the console, where a hand's thumb would be; the cursor comes up on
the screen, and the Joy-Con 2 glides across the table as the cursor moves (the pointer's path, pointer_path.py, scaled
down to the table) and dips at each click: it clicks the made-up game's tile, Dusty Gulch, and shoots on its title and
at five targets in its street, the sights the cursor; then it's lifted (the sights go), turned back upright and
brought to the console's right end, and the magnets snap it home, the console jolting; POWER puts it to sleep.

Six materials (case, joycon, buttons, glass, rear, video) and three textures, within the system model budget. Run from
the repo root:

    python tools/console-models/switch2_print.py artifacts/made-up-games artifacts/switch2
    python tools/console-models/switch2_video.py artifacts/made-up-games godot/themes/console/videos/switch2.mp4
    blender -b --factory-startup --python tools/console-models/switch2.py -- artifacts/switch2 godot/themes/console/models/systems/switch2.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch2_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import Pose, key, phase, smooth, wobble  # noqa: E402
from devices import tap  # noqa: E402
from handheld import body, circle, cross, stadium  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402
from pointer_path import mouse_offset  # noqa: E402
from saturn import inset  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end (the Joy-Con 2 the clip takes off) towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.55, joycon=0.6, buttons=0.45, glass=0.5, rear=0.62, video=0.65)
GLASS_Y, VIDEO_Y = -0.3, -0.6   # the glass in front of the face, the screen in front of it: apart enough not to fight
                                # for the same pixels at a card's size
PIVOT_UPRIGHT = Vector((0.0, L.DEPTH - L.BACK_ROUND, L.BACK_ROUND))   # the back's bottom edge's rounding: it leans on it
PULL_OUT = 13.0                 # how far the Joy-Con 2 is drawn out, clear of the channel, before it's turned
J_CENTRE = Vector((L.JOYCON["width"] / 2, L.DEPTH / 2, L.JOYCON["height"] / 2))   # its middle, (u, y, z)

# ---- UVs ---------------------------------------------------------------------------------------------------------------

def region_uv(regions, name, kind):
    """A planar projection into an atlas region: the face's (x, z), the back's (-x, z), the top edge's (x, y) (its back
    at the region's top), the bottom edge's (x, y) (its face at the region's top), a side's or an end's (z, y)."""
    px, py, pw, ph = regions[name]["px"]
    a0, a1, b0, b1 = regions[name]["mm"]

    def uv(co):
        if kind == "front":
            a, down = co.x, (b1 - co.z) / (b1 - b0)
        elif kind == "rear":
            a, down = -co.x, (b1 - co.z) / (b1 - b0)
        elif kind == "top":
            a, down = co.x, (b1 - co.y) / (b1 - b0)
        elif kind == "bottom":
            a, down = co.x, (co.y - b0) / (b1 - b0)
        else:
            a, down = co.z, (co.y - b0) / (b1 - b0)
        return (px + (a - a0) / (a1 - a0) * pw) / L.ATLAS, 1 - (py + down * ph) / L.ATLAS
    return uv


FRONT = region_uv(L.PRINT_REGIONS, "front", "front")
TOP = region_uv(L.PRINT_REGIONS, "top", "top")
BOTTOM = region_uv(L.PRINT_REGIONS, "bottom", "bottom")
REAR = region_uv(L.REAR_REGIONS, "rear", "rear")
SIDE = {1: region_uv(L.REAR_REGIONS, "side_r", "side"), -1: region_uv(L.REAR_REGIONS, "side_l", "side")}
END = {1: region_uv(L.REAR_REGIONS, "end_r", "side"), -1: region_uv(L.REAR_REGIONS, "end_l", "side")}
ACCENT = {1: "coral", -1: "blue"}


def swatch(name, rear=False):
    x, y = (L.REAR_SWATCHES if rear else L.SWATCHES)[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def shade(obj, angle=35.0):
    """Smooth shading, edges sharper than angle kept sharp; caps (more than four corners) stay flat."""
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) <= 4
    obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


def jc(side, u, z):
    """A point on a Joy-Con 2's face, u out from its inner edge: on the right one (side 1) or the left (-1)."""
    return side * (L.HALF + u), z


def at_origin(obj, where):
    """The part's mesh moved so that where (in the set) is its origin: it moves from there."""
    obj.data.transform(Matrix.Translation(-Vector(where)))
    return obj, Vector(where)


def domed(name, rim, height, dome, mat, top_uv, side_uv, back=False, rings_=4):
    """A button standing out of the face (or the back): its foot inside, straight sides out to height, then a dome
    (inset, rise) over its rim. Its top takes top_uv's printing, its sides side_uv's."""
    s, y0 = (1.0, L.DEPTH) if back else (-1.0, 0.0)
    stack = [(rim, y0 - s * 0.6), (rim, y0 + s * height)]
    for k in range(1, rings_ + 1):
        a = math.pi / 2 * k / rings_
        stack.append((inset(rim, dome[0] * (1 - math.cos(a))), y0 + s * (height + dome[1] * math.sin(a))))
    obj = solid(name, [[(x, y, z) for x, z in pts] for pts, y in stack], mat)
    paint(obj, mat, side_uv, lambda c, n, kind: True)
    paint(obj, mat, top_uv, lambda c, n, kind: (n.y > 0.35) if back else (n.y < -0.35))
    return shade(obj, 50.0)


# ---- The console -------------------------------------------------------------------------------------------------------

def tablet(m):
    """The console: the face's outline lofted back, printed (the face, the edges, the back, the ends), the channels cut
    into its ends."""
    outline = L.rounded_rect(-L.HALF, L.HALF, 0.0, L.HEIGHT, L.CORNER, steps=4)
    obj = body("console", outline, L.DEPTH, m["case"], front=L.FRONT_ROUND, back=L.BACK_ROUND, steps=3)
    paint(obj, m["case"], swatch("case"), lambda c, n, kind: True)
    paint(obj, m["case"], FRONT, lambda c, n, kind: n.y < -0.5)
    paint(obj, m["case"], TOP, lambda c, n, kind: n.z > 0.6)
    paint(obj, m["case"], BOTTOM, lambda c, n, kind: n.z < -0.6)
    paint(obj, m["rear"], REAR, lambda c, n, kind: n.y > 0.5)
    for side in (1, -1):
        paint(obj, m["rear"], END[side], lambda c, n, kind, s=side: n.x * s > 0.6)
    ch = L.CHANNEL
    pts = L.stadium(ch["y"][0], ch["y"][1], ch["z"][0], ch["z"][1], n=12)
    for side in (1, -1):
        rings = [[(x, a, b) for a, b in pts] for x in (side * (L.HALF - ch["depth"]), side * (L.HALF + 2.0))]
        boolean(obj, solid("channel", rings, m["rear"]))
    for side in (1, -1):
        floor = L.HALF - ch["depth"]

        def inside(c, s=side):
            return (s * c.x > floor - 0.05 and ch["y"][0] - 0.05 < c.y < ch["y"][1] + 0.05
                    and ch["z"][0] - 0.05 < c.z < ch["z"][1] + 0.05)
        paint(obj, m["rear"], swatch(ACCENT[side], rear=True), lambda c, n, kind, f=inside: f(c) and abs(n.x) < 0.5)
        paint(obj, m["rear"], END[side], lambda c, n, kind, f=inside, s=side: f(c) and n.x * s > 0.9
              and abs(s * c.x - floor) < 0.05)
    return shade(obj)


def top_buttons(m):
    """POWER (apart: the clip presses it) and VOLUME (in the set): pills standing on the top edge, their tops the top
    edge's printing."""
    t = L.TOP

    def pill_button(name, x0, x1):
        rim = stadium((x0 + x1) / 2, t["button_y"], x1 - x0, t["button_w"], n=8)
        h = t["button_height"]
        stack = [(0.0, -0.6), (0.0, h - 0.2), (0.25, h - 0.05), (0.55, h)]
        part = solid(name, [[(x, y, L.HEIGHT + dz) for x, y in (inset(rim, d) if d > 1e-6 else rim)]
                            for d, dz in stack], m["buttons"])
        paint(part, m["buttons"], swatch("button"), lambda c, n, kind: True)
        paint(part, m["buttons"], TOP, lambda c, n, kind: n.z > 0.5)
        return shade(part, 50.0)
    return pill_button("power", *t["power"]), pill_button("volume", *t["volume"])


def glass(m):
    """The glass: one flat face just in front of the face, printed as the face is there."""
    g = L.GLASS
    corners = L.rounded_rect(-g["width"] / 2, g["width"] / 2, g["z"] - g["height"] / 2, g["z"] + g["height"] / 2, g["r"],
                             steps=3)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new((x, GLASS_Y, z)) for x, z in corners])   # anticlockwise seen from the front: faces -y
    obj = new_object("glass", bm, m["glass"])
    paint(obj, m["glass"], FRONT, lambda c, n, kind: True)
    return obj


def screen(m):
    """The screen: one flat face in front of the glass, the video's whole frame across it."""
    v = L.VIDEO
    x0, x1, z0, z1 = -v["width"] / 2, v["width"] / 2, v["z"] - v["height"] / 2, v["z"] + v["height"] / 2
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    face = bm.faces.new([bm.verts.new((x, VIDEO_Y, z)) for x, z in corners])
    for loop, (x, z) in zip(face.loops, corners):
        loop[uv].uv = ((x - x0) / (x1 - x0), (z - z0) / (z1 - z0))
    return new_object("screen", bm, m["video"])


# ---- The Joy-Con 2 ---------------------------------------------------------------------------------------------------

def shell(side, m):
    """A Joy-Con 2's shell: its outline lofted back through its depth, its outer edges rounded over at the face and at
    the back, its inner edge (where it meets the console) left nearly square; printed (the face, the back, the inner
    side), its edges a swatch."""
    f, b = L.JOYCON["front"], L.JOYCON["back"]
    base = L.joycon_outline(step=4.0)

    def at(d):
        moved = inset(base, d) if d > 1e-6 else base
        return [jc(side, 0.2 * d if u < 1e-6 else mu, mz) for (u, _z), (mu, mz) in zip(base, moved)]
    rings = [(f * (1 - math.cos(math.pi / 2 * k / 3)), f * (1 - math.sin(math.pi / 2 * k / 3))) for k in range(4)]
    rings += [(L.DEPTH - b + b * math.sin(math.pi / 2 * k / 4), b * (1 - math.cos(math.pi / 2 * k / 4))) for k in range(5)]
    obj = solid("shell", [[(x, y, z) for x, z in at(d)] for y, d in rings], m["joycon"])
    paint(obj, m["joycon"], swatch("edge"), lambda c, n, kind: True)
    paint(obj, m["joycon"], FRONT, lambda c, n, kind: n.y < -0.6)
    paint(obj, m["rear"], REAR, lambda c, n, kind: n.y > 0.6)
    paint(obj, m["rear"], SIDE[side], lambda c, n, kind: n.x * side < -0.8)
    return shade(obj)


def tongue(side, m):
    """The tongue standing out of the inner edge into the console's channel, in the Joy-Con 2's colour, its face (SL,
    SR, the mouse sensor, the connector) printed."""
    t = L.TONGUE
    pts = L.stadium(t["y"][0], t["y"][1], t["z"][0], t["z"][1], n=10)
    rings = [[(x, a, b) for a, b in pts] for x in (side * (L.HALF + 0.3), side * (L.HALF - t["depth"]))]
    part = solid("tongue", rings, m["rear"])
    paint(part, m["rear"], swatch(ACCENT[side], rear=True), lambda c, n, kind: True)
    paint(part, m["rear"], SIDE[side], lambda c, n, kind: n.x * side < -0.9)
    return part


def trigger(side, m):
    """ZR (or ZL): what the band round the top outer corner seen from behind (between the outline, a little proud of
    it, and TRIGGER_INNER) and its profile seen from the inner side (TRIGGER_LOBE) have in common."""
    outer = inset(L.joycon_outline(step=2.0), -L.TRIGGER_PROUD)
    u0, z0 = L.TRIGGER_INNER[1][0], L.TRIGGER_INNER[-1][1]
    band = [(u, z) for u, z in outer if z >= z0 and u >= u0] + L.TRIGGER_INNER[1:]
    part = solid("trigger", [[(side * (L.HALF + u), y, z) for u, z in band] for y in (6.0, 24.0)], m["buttons"])
    lobe = solid("lobe", [[(side * (L.HALF + u), y, z) for y, z in L.TRIGGER_LOBE] for u in (-1.0, 36.5)],
                 m["buttons"])
    boolean(part, lobe, "INTERSECT")
    paint(part, m["buttons"], swatch("button"), lambda c, n, kind: True)
    return shade(part, 30.0)


def release_button(side, m):
    r = L.RELEASE
    x = side * (L.HALF + r["u"])
    rim = L.rounded_rect(x - r["width"] / 2, x + r["width"] / 2, r["z"] - r["height"] / 2, r["z"] + r["height"] / 2,
                         r["r"], steps=4)
    return domed("release", rim, r["proud"] - 0.4, (0.9, 0.4), m["rear"], REAR, swatch("button", rear=True), back=True)


def stick(side, m):
    """The stick: the ring round its foot in the Joy-Con 2's colour; its dark dome rising inside the ring to the shaft,
    the cap, its rim rounded and its top dished, the top taking the face's printing."""
    x, z = jc(side, *(L.STICK_R if side > 0 else L.STICK_L))
    s = L.STICK
    r0, r1 = s["ring"]
    h = s["ring_height"]
    profile = [(r0, 0.5), (r0, -h + 0.35), (r0 + 0.25, -h), (r1 - 0.25, -h), (r1, -h + 0.35), (r1, 0.5)]
    ring = solid("ring", [[(px, y, pz) for px, pz in circle(x, z, r, 40)] for r, y in profile], m["buttons"])
    paint(ring, m["buttons"], swatch("ring_coral" if side > 0 else "ring_blue"), lambda c, n, kind: True)
    c0, c1 = s["cap_y"]
    cap, dish = s["cap"], s["dish"]
    profile = [(r0 - 0.15, 0.4), (r0 - 0.15, -0.5), (r0 - 0.8, -1.0), (6.0, -1.35), (4.4, -1.55), (s["shaft"], -1.75),
               (s["shaft"], -c0 + 0.1), (cap - 0.9, -c0), (cap - 0.25, -c0 - 0.2), (cap, -c0 - 0.6), (cap, -c1 + 0.45),
               (cap - 0.25, -c1 + 0.12), (cap - 0.9, -c1), (cap - 2.4, -c1 + dish * 0.6), (2.6, -c1 + dish * 0.92),
               (0.8, -c1 + dish)]
    part = solid("stick", [[(px, y, pz) for px, pz in circle(x, z, r, 36)] for r, y in profile], m["buttons"])
    paint(part, m["buttons"], swatch("cap"), lambda c, n, kind: True)
    paint(part, m["buttons"], FRONT, lambda c, n, kind: c.y < -c1 + 0.8 and n.y < -0.5)
    return [shade(ring, 50.0), shade(part, 50.0)]


def face_controls(side, m):
    """The face's buttons, each standing out of it, their tops the face's printing: X, A, B and Y or the direction
    buttons; + and HOME and C, or - and the capture button."""
    parts = []
    sides = swatch("button")
    group = L.ABXY if side > 0 else L.DPAD
    for _name, degrees in L.FACE_BUTTONS:
        a = math.radians(degrees)
        u0, z0 = group["centre"]
        x, z = jc(side, u0 + group["reach"] * math.cos(a), z0 + group["reach"] * math.sin(a))
        parts.append(domed("face", circle(x, z, group["r"], 32), group["height"] - 0.4, (0.9, 0.4), m["buttons"], FRONT,
                           sides))
    if side > 0:
        p = L.PLUS
        x, z = jc(side, *p["at"])
        parts.append(domed("plus", cross(x, z, p["length"] / 2, p["width"] / 2), p["height"] - 0.2, (0.2, 0.2),
                           m["buttons"], FRONT, sides, rings_=2))
        x, z = jc(side, *L.HOME["at"])
        parts.append(domed("home", circle(x, z, L.HOME["r"], 32), L.HOME["height"] - 0.25, (0.6, 0.25), m["buttons"],
                           FRONT, sides, rings_=3))
        square = L.C_BUTTON
    else:
        p = L.MINUS
        x, z = jc(side, *p["at"])
        parts.append(domed("minus", stadium(x, z, p["length"], p["width"], n=6), p["height"] - 0.2, (0.2, 0.2),
                           m["buttons"], FRONT, sides, rings_=2))
        square = L.CAPTURE
    x, z = jc(side, *square["at"])
    h = square["size"] / 2
    rim = L.rounded_rect(x - h, x + h, z - h, z + h, square["r"], steps=4)
    parts.append(domed("square", rim, square["height"] - 0.1, (0.3, 0.1), m["buttons"], FRONT, sides, rings_=2))
    return parts


def joycon(side, m):
    """A Joy-Con 2, attached (side 1 the right one, -1 the left), as one mesh."""
    parts = [shell(side, m), tongue(side, m), trigger(side, m), release_button(side, m)]
    parts += stick(side, m) + face_controls(side, m)
    return join(parts, "joycon_r" if side > 0 else "joycon_l")


# ---- The kickstand -----------------------------------------------------------------------------------------------------

def kickstand(m, opening):
    """The kickstand: its legs and bar shut against the back, turned open by opening degrees about the hinges; and the
    hinges' blocks on the back."""
    k = L.KICKSTAND
    t, w = k["thick"], k["bar"]
    x0, x1 = k["legs"]
    y0 = L.DEPTH + 0.05
    parts = [box("leg", min(s * x0, s * x1), max(s * x0, s * x1), y0, y0 + t, 0.8 + w / 2, k["hinge_z"] + 2.0, m["rear"])
             for s in (-1, 1)]
    parts.append(box("bar", -x1, x1, y0, y0 + t, 0.8, 0.8 + w, m["rear"]))
    stand = join(parts, "stand")
    bevel(stand, 0.6, segments=2)
    hinge = Matrix.Translation((0.0, k["hinge_y"], k["hinge_z"]))
    stand.data.transform(hinge @ Matrix.Rotation(math.radians(opening), 4, "X") @ hinge.inverted())
    blocks = [box("block", min(s * x0, s * x1), max(s * x0, s * x1), L.DEPTH - 0.3, L.DEPTH + 2.2, k["block"][0],
                  k["block"][1], m["rear"]) for s in (-1, 1)]
    whole = join([stand] + blocks, "kickstand")
    paint(whole, m["rear"], swatch("kickstand", rear=True), lambda c, n, kind: True)
    return shade(whole, 40.0)


def kickstand_opening(lean, lift):
    """How far the kickstand opens (degrees) for its bar to rest on the table, the console leant by lean and lifted by
    lift: the bar's corners, turned about the hinges, then leant."""
    k = L.KICKSTAND
    y0, t, w = L.DEPTH + 0.05, k["thick"], k["bar"]
    corners = [Vector((0.0, y, z)) for y in (y0, y0 + t) for z in (0.8, 0.8 + w)]
    hinge = Matrix.Translation((0.0, k["hinge_y"], k["hinge_z"]))

    def lowest(opening):
        turn = lean @ hinge @ Matrix.Rotation(math.radians(opening), 4, "X") @ hinge.inverted()
        return min((turn @ c).z for c in corners) + lift + 0.2      # the bevel takes about 0.2 off its corners

    lo, hi = L.LEAN, 89.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if lowest(mid) < 0 else (lo, mid)
    return (lo + hi) / 2


# ---- The clip ----------------------------------------------------------------------------------------------------------

class Turned(Pose):
    """A pose whose turn is a quaternion (in the parent's axes) rather than spin, roll and pitch."""

    def __init__(self, turn, **kw):
        super().__init__(**kw)
        self.turn = turn

    def rotation(self):
        return self.turn


Q_LEAN = Quaternion((1.0, 0.0, 0.0), math.radians(-L.LEAN))
# As a mouse: its attachment side down (its u up), its top away from the viewer (its z along y), its face to the left.
Q_MOUSE = Matrix(((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))).to_quaternion()
PLACES = {}                        # main() fills in where things are, once the console is leant on the table


def click(f):
    return max(tap(f, f0, hold=L.CLICK - 2) for f0 in L.CLICKS)


def on_table(f):
    """The Joy-Con 2's middle as a mouse at frame f: its rest on the table, moved as the pointer moves, dipping a
    millimetre at each click and settling after it lands."""
    dx, dy = mouse_offset(L.POINTER.at(f), L.REST, L.GAIN, 0.0)
    settle = max(0.0, wobble(f, L.CARRY[1], 0.9, period=6.0, decay=3.0))
    return PLACES["mouse"] + Vector((dx, dy, settle - click(f)))


def joycon_place(f):
    """The right Joy-Con 2's middle (in the set) and its turn (the set's axes, from upright) at frame f."""
    rest = PLACES["joycon"]
    out = rest + Vector((PULL_OUT, 0.0, 0.0))
    if f < L.RELEASE_PRESS:
        return rest, Q_LEAN
    if f < L.PULL[0]:                                     # the release button's pin pops it out a little
        pop = 1.2 * smooth(phase(f, L.RELEASE_PRESS, L.RELEASE_PRESS + 2)) + wobble(f, L.RELEASE_PRESS + 2, 0.35, 5.0, 2.5)
        return rest + Vector((pop, 0.0, 0.0)), Q_LEAN
    if f < L.PULL[1]:                                     # drawn straight out of the channel
        return rest + Vector((1.2 + (PULL_OUT - 1.2) * smooth(phase(f, *L.PULL)), 0.0, 0.0)), Q_LEAN
    if f < L.CARRY[1]:                                    # turned onto its side and set down
        t = phase(f, *L.CARRY)
        place = out.lerp(PLACES["mouse"], smooth(t)) + Vector((0.0, 0.0, 16.0 * math.sin(math.pi * t)))
        return place, Q_LEAN.slerp(Q_MOUSE, smooth(phase(f, L.CARRY[0] + 2, L.CARRY[1] - 5)))
    if f < L.LIFT[0]:
        return on_table(f), Q_MOUSE
    lifted = on_table(L.LIFT[0]) + Vector((0.0, 0.0, 10.0))
    if f < L.LIFT[1]:                                     # lifted off the table: no longer a mouse
        return on_table(L.LIFT[0]).lerp(lifted, smooth(phase(f, *L.LIFT))), Q_MOUSE
    if f < L.BACK[1]:                                     # turned back upright and brought to the console's end
        t = phase(f, *L.BACK)
        place = lifted.lerp(out, smooth(t)) + Vector((0.0, 0.0, 8.0 * math.sin(math.pi * t)))
        return place, Q_MOUSE.slerp(Q_LEAN, smooth(phase(f, L.BACK[0], L.BACK[1] - 3)))
    if f < L.SNAP[1]:                                     # in along its channel, and the magnets take it the last 3 mm
        a, b = L.SNAP
        x = PULL_OUT + (3.0 - PULL_OUT) * smooth(phase(f, a, b - 2)) if f < b - 2 else 3.0 * (1 - phase(f, b - 2, b)) ** 2
        return rest + Vector((x, 0.0, 0.0)), Q_LEAN
    return rest, Q_LEAN


def timeline(f):
    place, turn = joycon_place(f)
    poses = {"joycon_r": Turned(turn @ Q_LEAN.inverted(), **dict(zip("xyz", place - PLACES["joycon"])))}
    press = L.TOP["button_travel"] * max(tap(f, L.WAKE), tap(f, L.SLEEP))
    poses["power"] = Pose(**dict(zip("xyz", PLACES["down"] * press)))
    poses["console"] = Pose(x=wobble(f, L.SNAP[1], -0.4, 6.0, 3.0), roll=wobble(f, L.SNAP[1], 0.45, 7.0, 4.0))
    return poses


# ---- Main --------------------------------------------------------------------------------------------------------------

def seen(obj, tilt, frames):
    """obj's points (every fourth vertex) over frames: [(the point in the set, the point as the card is seen (tilt))]."""
    scene = bpy.context.scene
    points = [v.co.copy() for v in obj.data.vertices][::4]
    out = []
    for f in frames:
        scene.frame_set(f)
        world = obj.matrix_world.copy()
        out += [(world @ co, tilt @ (world @ co)) for co in points]
    scene.frame_set(0)
    return out


def clearance(points, edge):
    """How far right of the screen's right edge (edge: its bottom and top corners as the card is seen) the points
    keep, at their heights: negative if any is over the screen."""
    (bx, bz), (tx, tz) = edge
    gaps = [q.x - (bx + (tx - bx) * (q.z - bz) / (tz - bz)) for _p, q in points if bz <= q.z <= tz]
    return min(gaps) if gaps else math.inf


def speck(obj, point):
    """Adds a speck at point (in obj's space): a triangle too small to see, facing +y (away from the viewer), as
    alarm_clock.py's specks are, so the launcher's fit reaches it."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    e = 1e-3
    bm.faces.new([bm.verts.new(point + Vector(d)) for d in ((0, 0, 0), (0, 0, e), (e, 0, 0))])   # wound to face +y
    bm.to_mesh(obj.data)
    bm.free()


def finish(whole, parts, out):
    """card.finish(), but the set rocks too: the root holds the console, keyed about where it rests, which holds the
    parts. The root turns the card to the three-quarter view and fits its rest pose."""
    scene = bpy.context.scene
    root = bpy.data.objects.new("switch2_root", None)
    scene.collection.objects.link(root)
    pivot = PLACES["pivot"]
    whole.data.transform(Matrix.Translation(-pivot))
    whole.parent = root
    whole.location = pivot
    nodes = {"console": whole}
    for name, (obj, where) in parts.items():
        obj.parent = whole
        obj.location = where - pivot
        nodes[name] = obj
    key("focused", nodes, timeline, L.LENGTH)
    bpy.context.view_layer.update()

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    # As a mouse the Joy-Con 2 is beside the console, beyond its rest's bounds, which the launcher fits and the details
    # screen frames: a speck where it reaches farthest makes the rest's bounds take it in.
    mouse = nodes["joycon_r"]
    far, far_seen = max(seen(mouse, tilt, range(L.CARRY[0], L.BACK[1], 2)), key=lambda pq: pq[1].x)
    rest_x = max((tilt @ (o.matrix_world @ v.co)).x for o in nodes.values() for v in o.data.vertices)
    video = {k for k, mat in enumerate(whole.data.materials) if mat.name == "video"}
    corners = [tilt @ (whole.matrix_world @ whole.data.vertices[i].co) for p in whole.data.polygons
               if p.material_index in video for i in p.vertices]
    right = sorted(corners, key=lambda q: q.x)[-2:]                      # the screen's right edge, as it's seen
    edge = [(q.x, q.z) for q in sorted(right, key=lambda q: q.z)]
    gap = clearance(seen(mouse, tilt, range(L.CARRY[1], L.LIFT[0], 2)), edge)
    speck(whole, far - pivot)
    print(f"Switch 2: as a mouse the Joy-Con 2 reaches {far_seen.x - rest_x:+.1f} mm beyond the console's rest (a speck "
          f"takes it in), and keeps {gap:+.1f} mm right of the screen's edge, as the card is seen")
    meshes = list(nodes.values())
    points = [tilt @ (o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt
    textures = {node.image.name for o in meshes for mat in o.data.materials if mat.node_tree
                for node in mat.node_tree.nodes if node.type == "TEX_IMAGE" and node.image}
    print(f"Switch 2: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, {len(textures)} textures, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "switch2_print.png"))
    back = bpy.data.images.load(os.path.join(images, "switch2_rear.png"))
    still = bpy.data.images.load(os.path.join(images, "switch2_screen.png"))
    textures = dict(case=printed, joycon=printed, buttons=printed, glass=printed, rear=back, video=still)
    m = {n: material(n, "#FFFFFF", r, textures[n]) for n, r in ROUGHNESS.items()}

    power, volume = top_buttons(m)
    console = [tablet(m), glass(m), screen(m), volume, joycon(-1, m)]
    right = joycon(1, m)
    # Leant back on its kickstand: turned about the back's bottom edge's rounding, which then rests on the table.
    lean = (Matrix.Translation(PIVOT_UPRIGHT) @ Matrix.Rotation(math.radians(-L.LEAN), 4, "X")
            @ Matrix.Translation(-PIVOT_UPRIGHT))
    for obj in console + [right, power]:
        obj.data.transform(lean)
    lift = -min((v.co.z for obj in console + [right] for v in obj.data.vertices))
    stand = kickstand(m, kickstand_opening(lean, lift))
    stand.data.transform(lean)
    for obj in console + [right, power, stand]:
        obj.data.transform(Matrix.Translation((0.0, 0.0, lift)))
    up = Matrix.Translation((0.0, 0.0, lift)) @ lean
    PLACES["joycon"] = up @ Vector((L.HALF + J_CENTRE.x, J_CENTRE.y, J_CENTRE.z))
    PLACES["down"] = (lean.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
    PLACES["pivot"] = Vector((0.0, PIVOT_UPRIGHT.y, 0.0))
    # As a mouse, the Joy-Con 2's tongue on the table, its face's plane at MOUSE's x, its bottom end at its y.
    PLACES["mouse"] = Vector((L.MOUSE["face_x"] + J_CENTRE.y, L.MOUSE["front_y"] + J_CENTRE.z,
                              L.TONGUE["depth"] + J_CENTRE.x))
    whole = join(console + [stand], "switch2")
    parts = {"power": at_origin(power, up @ Vector(((L.TOP["power"][0] + L.TOP["power"][1]) / 2, L.TOP["button_y"],
                                                     L.HEIGHT))),
             "joycon_r": at_origin(right, PLACES["joycon"])}
    finish(whole, parts, out)


if __name__ == "__main__":
    main()
