"""The console theme's Amstrad GX4000 system model (godot/themes/console/models/systems/gx4000.glb): the GX4000 and its
controller.

Built in Blender (gx4000_layout.py has the measurements, taken from photographs). The body is lofted through
cross-sections along its width, each following the plan's curved front: the front's vertical face, the slope up to the
crest, the flat top, the back; the top lower towards the ends, the ends rounded off, the corners drawn in. The rails are
half-ellipses swept along the top, their backs domed; the round pads stand at their fronts; the cartridge slot is cut
into the body and the switch's slot into the right rail. The controller is its outline given its depth, its edges
rounded, the hood raised at its back; its cord runs to the left joystick port. The printing is one texture
(gx4000_print.py's), projected from above onto the top and from in front onto the front face.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting over the slot, shrunk to nothing), the slot's two flaps (each on its hinge), the power
switch, the power light (shrunk to nothing while it's off), PAUSE, and the controller's D-pad and buttons.

The `focused` clip (8 s, looping): the cartridge appears over the slot and drops in, pushing the flaps down; the switch
slides on and the light lights; the game's played on the D-pad, 1 and 2, PAUSE pressed and pressed again; then the
switch goes off and the cartridge rises out, the flaps springing shut behind it, and goes.

Two materials (body, gloss) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/gx4000_print.py artifacts/gx4000
    blender -b --factory-startup --python tools/console-models/gx4000.py -- artifacts/gx4000 godot/themes/console/models/systems/gx4000.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gx4000_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
RINGS = 49
ROUGHNESS = dict(body=0.5, gloss=0.3)


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def table(points, x):
    """Linear interpolation in a table of (x, value), x from the first to the last."""
    x = min(max(x, points[0][0]), points[-1][0])
    for (x0, v0), (x1, v1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def arc(cy, cz, r, a0, a1, n):
    angles = [math.radians(a0 + (a1 - a0) * k / n) for k in range(n)]
    return [(cy + r * math.cos(a), cz + r * math.sin(a)) for a in angles]


def bezier(p0, p1, p2, p3, n):
    out = []
    for k in range(n):
        t = k / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def curve(p0, p1, p2, p3, n):
    """A cubic Bezier's n + 1 points, in 3D."""
    p0, p1, p2, p3 = (Vector(p) for p in (p0, p1, p2, p3))
    return [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / n for k in range(n + 1)]]


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def top_height(x):
    return table(L.TOP_HEIGHT, abs(x))


def front_y(x):
    return table(L.FRONT_CURVE, abs(x))


# ---- The console -----------------------------------------------------------------------------------------------------

def section(x):
    """The body's cross-section at x, (y, z) points round from the front face's foot: up the face, the slope, the top,
    the back and the underside."""
    yf, h = front_y(x), top_height(x)
    crest = L.CREST * h / L.TOP_HEIGHT[0][1]
    face = min(L.FACE, crest - 6.0)
    rb, rk = L.ROUND["bottom"], L.ROUND["back"]
    base = L.FEET
    points = [(yf, base + rb), (yf, (base + rb + face) / 2)]
    points += bezier((yf, face), (yf + 0.5, face + 6.0), (yf + L.SLOPE * 0.55, crest), (yf + L.SLOPE, crest), 8)
    points += bezier((yf + L.SLOPE, crest), (yf + L.SLOPE + 20.0, crest + (h - crest) * 0.6), (96.0, h), (110.0, h), 6)
    points += [(110.0, h), (140.0, h)] + arc(L.DEPTH - rk, h - rk, rk, 90.0, 0.0, 4)
    points += [(L.DEPTH, h - rk), (L.DEPTH, (h - rk + base + rb) / 2)]
    points += arc(L.DEPTH - rb, base + rb, rb, 0.0, -90.0, 3) + [(110.0, base), (60.0, base)]
    points += arc(yf + rb, base + rb, rb, -90.0, -180.0, 3)
    return points


def drawn_in(r, x):
    e = min(r, max(0.0, abs(x) - (L.WIDTH / 2 - r)))
    return r - math.sqrt(r * r - e * e)


def body(m):
    """The body lofted along x, drawn in round the plan's corners and the ends' bottom edges, capped at the ends."""
    rings = []
    for k in range(RINGS):
        x = L.WIDTH / 2 * math.sin(math.pi / 2 * (2 * k / (RINGS - 1) - 1))
        dp, db = drawn_in(L.ROUND["plan"], x), drawn_in(L.ROUND["bottom"], x)
        yf = front_y(x)
        span = L.DEPTH - yf
        ring = []
        for y, z in section(x):
            t = (y - yf) / span                                      # 0 at the front, 1 at the back
            ring.append((x, yf + dp + (y - yf) * (span - 2 * dp) / span if 0 <= t <= 1 else y,
                         z + db * (1 - (z - L.FEET) / max(1.0, top_height(x) - L.FEET))))
        rings.append(ring)
    bm = bmesh.new()
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(verts, verts[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])
    ends = [bm.faces.new(verts[0]), bm.faces.new(list(reversed(verts[-1])))]
    bmesh.ops.triangulate(bm, faces=ends, quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object("gx4000", bm, m["body"])


def rail(m, side):
    """A rail: a half-ellipse swept from its front end back, its back domed; sunk into the top."""
    cx, half, rise, (y0, y1) = side * L.RAILS["x"], L.RAILS["half"], L.RAILS["rise"], L.RAILS["y"]
    base = top_height(L.RAILS["x"]) - 8.0
    tall = rise + 8.0
    rings = []
    steps = [y0 + (y1 - 24.0 - y0) * k / 10 for k in range(11)] + [y1 - 24.0 + 24.0 * math.sin(math.pi / 2 * k / 6)
                                                                    for k in range(1, 7)]
    for y in steps:
        s = 1.0 if y <= y1 - 24.0 else math.sqrt(max(0.02, 1 - ((y - (y1 - 24.0)) / 24.0) ** 2))
        ring = [(cx + half * s * math.cos(math.radians(a)), y, base + tall * s * math.sin(math.radians(a)))
                for a in range(0, 181, 12)]
        ring += [(cx - half * s, y, base - 6.0), (cx + half * s, y, base - 6.0)]
        rings.append(ring)
    part = solid("rail", rings, m["body"])
    return part


def console(m):
    """The body, the rails (the switch's slot in the right one), the pads, the slot cut into the body, the feet;
    printed from above and from in front."""
    shell = body(m)
    (sx, sy), (sl, sw) = L.SLOT["at"], L.SLOT["size"]
    top = top_height(sx)
    boolean(shell, solid("slot", [[(x, y, z) for x, y in rounded(sx, sy, sl, sw, 3.0, 3)]
                                  for z in (top - L.SLOT["depth"], top + 10.0)], m["body"]))
    rails = [rail(m, -1), rail(m, 1)]
    (wx0, wx1), (wy0, wy1) = L.SWITCH["x"], L.SWITCH["y"]
    for part in (shell, rails[1]):
        boolean(part, box("switch_slot", wx0, wx1, wy0, wy1, top - 4.0, top + 20.0, m["body"]))
    pads = []
    for side in (-1, 1):
        x, y = side * L.RAILS["x"], L.PADS["y"]
        z = top_height(L.RAILS["x"]) - 1.0
        pad = solid("pad", [[(px, py, pz) for px, py in circle(x, y, L.PADS["r"], 40)] for pz in (18.0, z)], m["body"])
        bevel(pad, 1.0, segments=2)
        pads.append(pad)
    feet = [box("foot", x - 10.0, x + 10.0, y - 8.0, y + 8.0, 0.0, L.FEET + 1.0, m["body"])
            for x in (-90.0, 90.0) for y in (45.0, 160.0)]
    whole = join([shell] + rails + pads + feet, "gx4000")

    paint(whole, m["body"], swatch("body"), lambda c, n, name: True)
    above = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
    paint(whole, m["body"], lambda co: above(co.x + L.WIDTH / 2, L.DEPTH - co.y), lambda c, n, name: n.z > 0.35)
    ahead = atlas_uv(L.REGIONS["front"], L.WIDTH, 36.0)
    paint(whole, m["body"], lambda co: ahead(co.x + L.WIDTH / 2, 36.0 - co.z),
          lambda c, n, name: n.y < -0.6 and n.z <= 0.35 and c.y < 40.0)
    inside = lambda c: abs(c.x - sx) < sl / 2 + 0.5 and abs(c.y - sy) < sw / 2 + 0.5 and c.z < top - 0.5   # noqa: E731
    paint(whole, m["body"], swatch("grey"), lambda c, n, name: inside(c))
    paint(whole, m["body"], swatch("dark"),
          lambda c, n, name: (wx0 - 0.5 < c.x < wx1 + 0.5 and wy0 - 0.5 < c.y < wy1 + 0.5 and c.z < top + 7.0)
          or (inside(c) and c.z < top - L.SLOT["depth"] + 0.5))
    return whole


# ---- The moving parts ------------------------------------------------------------------------------------------------

def switch(m):
    """The pink switch, its middle at its origin."""
    (x0, x1), (y0, y1), h = L.SWITCH["x"], L.SWITCH["y"], L.SWITCH["height"]
    part = box("power", -(x1 - x0) / 2 + 0.8, (x1 - x0) / 2 - 0.8, -5.0, 5.0, -h, h, m["gloss"])
    bevel(part, 0.8, segments=1)
    paint(part, m["gloss"], swatch("pink"), lambda c, n, name: True)
    return part, Vector(((x0 + x1) / 2, y1 - 10.0, top_height(L.RAILS["x"]) + L.RAILS["rise"] - 2.0))   # off: back


def light(m):
    (x, y), (w, d) = L.LIGHT["at"], L.LIGHT["size"]
    part = box("power_light", -w / 2, w / 2, -d / 2, d / 2, -0.3, 0.3, m["gloss"])
    paint(part, m["gloss"], swatch("lit"), lambda c, n, name: True)
    return part, Vector((x, y, top_height(L.RAILS["x"]) - 0.6))


def pause(m):
    """PAUSE: a thin disc on the right pad's middle, its print the pad's."""
    x, y, r = L.RAILS["x"], L.PADS["y"], L.PADS["r"] - 3.0
    z = top_height(L.RAILS["x"]) - 1.0
    part = solid("pause", [[(px, py, pz) for px, py in circle(0.0, 0.0, r, 32)] for pz in (-2.0, 0.6)], m["body"])
    above = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
    paint(part, m["body"], swatch("body"), lambda c, n, name: True)
    paint(part, m["body"], lambda co: above(co.x + x + L.WIDTH / 2, L.DEPTH - (co.y + y)), lambda c, n, name: n.z > 0.9)
    return part, Vector((x, y, z))


def flap(m, side):
    """One of the slot's flaps, its origin on its hinge (the slot's front edge, side -1, or its back edge, side 1),
    reaching to the middle, drooping a little."""
    (sx, sy), (sl, sw), f = L.SLOT["at"], L.SLOT["size"], L.FLAPS
    reach = sw / 2 - 0.3
    y0, y1 = (0.0, reach) if side < 0 else (-reach, 0.0)
    part = box("flap", -sl / 2 + 1.0, sl / 2 - 1.0, y0, y1, -f["thickness"], 0.0, m["body"])
    paint(part, m["body"], swatch("grey"), lambda c, n, name: True)
    part.data.transform(Matrix.Rotation(math.radians(f["droop"] * side), 4, "X"))
    return part, Vector((sx, sy + side * sw / 2, top_height(sx) - f["sunk"]))


def cartridge(m):
    """The cartridge, its foot's middle at its origin, its label to the front (-y)."""
    w, t, h = L.CART["size"]
    part = solid("cartridge", [[(x, y, z) for x, z in rounded(0.0, h / 2, w, h, 4.0, 3)] for y in (-t / 2, t / 2)],
                 m["body"])
    bevel(part, 1.2, segments=2)
    paint(part, m["body"], swatch("grey"), lambda c, n, name: True)
    lw, lh = L.CART["label"]
    corners = ((-lw / 2, h - 4.0 - lh), (lw / 2, h - 4.0 - lh), (lw / 2, h - 4.0), (-lw / 2, h - 4.0))
    label = solid("label", [[(x, y, z) for x, z in corners] for y in (-t / 2 - 0.15, -t / 2 + 0.5)], m["gloss"])
    face = atlas_uv(L.REGIONS["cart"], lw, lh)
    paint(label, m["gloss"], swatch("grey"), lambda c, n, name: True)
    paint(label, m["gloss"], lambda co: face(co.x + lw / 2, h - 4.0 - co.z), lambda c, n, name: n.y < -0.9)
    return join([part, label], "cartridge")


# ---- The controller --------------------------------------------------------------------------------------------------

def pad_outline():
    """The controller's outline from above, its front-left corner rounded wider; y back from its front edge."""
    pw, pd, _ = L.PAD["size"]
    r, big = L.PAD["r"], L.PAD["corner"]
    points = []
    for (cx, cy, rr, a0) in ((pw / 2 - r, pd - r, r, 0), (-pw / 2 + r, pd - r, r, 90), (-pw / 2 + big, big, big, 180),
                             (pw / 2 - r, r, r, 270)):
        angles = [math.radians(a0 + 90 * k / 6) for k in range(7)]
        points += [(cx + rr * math.cos(a), cy + rr * math.sin(a)) for a in angles]
    return points


def pad_frame():
    (x, y), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def controller(m):
    """The controller in the console's frame: its body and hood, printed; its D-pad and buttons, each with where its
    node goes."""
    pw, pd, ph = L.PAD["size"]
    shell = solid("controller", [[(x, y, z) for x, y in pad_outline()] for z in (0.0, ph)], m["body"])
    bevel(shell, 3.0, segments=3)
    (hx0, hx1), (hy0, hy1), hh, point = L.HOOD["x"], L.HOOD["y"], L.HOOD["height"], L.HOOD["point"]
    hood = solid("hood", [[(x, y, z) for x, y in ((hx1, hy1), (hx0, hy1), (hx0, hy0 + point), ((hx0 + hx1) / 2, hy0),
                                                  (hx1, hy0 + point))] for z in (ph - 1.0, ph + hh)], m["body"])
    bevel(hood, 2.0, segments=2)
    whole = join([shell, hood], "controller")
    paint(whole, m["body"], swatch("body"), lambda c, n, name: True)
    face = atlas_uv(L.REGIONS["pad"], pw, pd)
    paint(whole, m["body"], lambda co: face(co.x + pw / 2, pd - co.y), lambda c, n, name: n.z > 0.9 and c.z < ph + 0.5)
    to_world = pad_frame()
    whole.data.transform(to_world)
    turn = Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z")
    nodes = {}
    d = L.DPAD
    h, w = d["size"] / 2, d["arm"] / 2
    cross = [(w, -h), (w, -w), (h, -w), (h, w), (w, w), (w, h), (-w, h), (-w, w), (-h, w), (-h, -w), (-w, -w), (-w, -h)]
    dpad = solid("dpad", [[(x, y, z) for x, y in cross] for z in (-1.5, d["height"])], m["body"])
    bevel(dpad, 0.8, segments=1)
    paint(dpad, m["body"], swatch("grey"), lambda c, n, name: True)
    dpad.data.transform(turn)
    nodes["dpad"] = (dpad, to_world @ Vector((d["at"][0], d["at"][1], ph)))
    for k, (bx, by) in enumerate(L.BUTTONS["at"]):
        button = solid(f"button_{k + 1}", [[(x, y, z) for x, y in circle(0.0, 0.0, L.BUTTONS["r"], 24)]
                                            for z in (-1.5, L.BUTTONS["height"])], m["gloss"])
        bevel(button, 1.2, segments=2)
        paint(button, m["gloss"], swatch("red"), lambda c, n, name: True)
        nodes[f"button_{k + 1}"] = (button, to_world @ Vector((bx, by, ph)))
    start = to_world @ Vector(((hx0 + hx1) / 2, pd + 1.0, ph - 4.0))
    (jx, jz), _ = L.PORTS["joy_1"]
    end = Vector((jx, front_y(jx) - 1.0, jz))
    cord = tube(curve(start, start + Vector((0.0, 40.0, 0.0)), end + Vector((0.0, -50.0, -10.0)), end, 24), 2.6, m)
    return whole, cord, nodes


def tube(points, r, m, sides=8):
    bm = bmesh.new()
    rings = []
    normal = Vector((0.0, 0.0, 1.0))
    n = len(points) - 1
    for k, p in enumerate(points):
        tangent = (points[min(k + 1, n)] - points[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(2 * math.pi * j / sides)
                                        + binormal * math.sin(2 * math.pi * j / sides)) * r) for j in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            bm.faces.new([a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cord = new_object("cord", bm, m["body"])
    paint(cord, m["body"], swatch("body"), lambda c, n, name: True)
    return cord


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    above = L.CART["above"]
    if f < 6 or f >= 222:
        cart = Pose(scale=HIDDEN)
    elif f < 14:
        cart = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 6, 13))))
    elif f < 24:
        cart = Pose(z=above + 2.0 * math.sin(2 * math.pi * phase(f, 14, 24)))
    elif f < 36:
        cart = Pose(z=above * (1 - ease_in(phase(f, 24, 36))))
    elif f < 196:
        cart = Pose(z=-2.5 * math.sin(math.pi * phase(f, 36, 44)))
    elif f < 212:
        cart = Pose(z=above * ease_out(phase(f, 196, 212)))
    else:
        cart = Pose(z=above, scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    on = smooth(phase(f, 46, 51)) * (1 - smooth(phase(f, 186, 191)))
    if f < 31:
        swing = 0.0
    elif f < 201:
        swing = smooth(phase(f, 31, 34))
    else:
        swing = 1.0 - back_out(phase(f, 201, 210))
    swing *= L.FLAPS["open"] - L.FLAPS["droop"]
    t = phase(f, 58, 172)
    k = math.sin(math.pi * t)
    return {"cartridge": cart, "power": Pose(y=-L.SWITCH["travel"] * on),
            "flap_front": Pose(pitch=-swing), "flap_back": Pose(pitch=swing),
            "power_light": Pose() if 50 <= f < 188 else Pose(scale=HIDDEN),
            "pause": Pose(z=-1.4 * max(tap(f, 118), tap(f, 146))),
            "dpad": Pose(pitch=10.0 * k * math.sin(2 * math.pi * 3.0 * t),
                         roll=10.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "button_1": Pose(z=-L.BUTTONS["press"] * max(tap(f, f0) for f0 in (64, 84, 104, 130, 160))),
            "button_2": Pose(z=-L.BUTTONS["press"] * max(tap(f, f0) for f0 in (74, 94, 136, 166)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "gx4000_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    body_ = console(m)
    pad_body, cord, pad_nodes = controller(m)
    whole = join([body_, pad_body, cord], "gx4000")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("gx4000_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    parts = {"power": switch(m), "power_light": light(m), "pause": pause(m), "flap_front": flap(m, -1),
             "flap_back": flap(m, 1)}
    cart = cartridge(m)
    (sx, sy) = L.SLOT["at"]
    parts["cartridge"] = (cart, Vector((sx, sy, top_height(sx) - L.CART["seat"])))
    parts.update(pad_nodes)
    nodes = {}
    for name, (part, where) in parts.items():
        for p in part.data.polygons:
            p.use_smooth = True
        part.data.set_sharp_from_angle(angle=math.radians(35))
        part.parent = whole
        part.location = where
        nodes[name] = part

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"GX4000: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
