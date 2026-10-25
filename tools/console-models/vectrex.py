"""The console theme's Vectrex system model (godot/themes/console/models/systems/vectrex.glb): Milton Bradley's
Vectrex with its controller in front of it.

Built in Blender (vectrex_layout.py has the measurements, taken from photographs). The console is its side profile
(the hood's leaning face, the rounded lid, the front box's back, the tube housing's falling top, the back and the
underside) at the base's width, with the front box standing proud of it at its sides; the hood's recess is cut into the
face, narrowing back to the bezel, the tube's face in front of it; the bay is cut into the base under the hood, the
cartridge slot into its right side. The controller lies on the table in front, its coiled cord running up into the
bay's port. The printing is one texture (vectrex_print.py's): the tube lit four ways, the overlay, the controller's
face, the bay's back wall, the cartridge's label and the lid's strip.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the console and
the controller; the console holding the tube's faces (the power-on screen and the game's three frames; those not lit
wait behind the bezel, so a swap never shows one shrinking: at worst the dark tube in front of them blinks), the
overlay and the cartridge (both waiting shrunk to nothing), the controller its joystick (its origin at its pivot) and
its four buttons.

The `focused` clip (8 s, looping): a cartridge slides into the side, the overlay comes in and settles over the tube,
the screen flickers on and the game plays (the score climbing, the ship moving and firing, a rock bursting) while the
joystick rocks and the buttons press; then the screen goes dark, the overlay comes back out and the cartridge too, and
the power-on screen returns.

Four materials (case, screen, key, metal) and one 1024² texture, within the system model budget. Run from the repo
root:

    python tools/console-models/vectrex_print.py artifacts/vectrex
    blender -b --factory-startup --python tools/console-models/vectrex.py -- artifacts/vectrex godot/themes/console/models/systems/vectrex.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vectrex_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive import prism_y, prism_z  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)

TILT_YAW = -28.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: the top tips up towards the viewer

ROUGHNESS = dict(case=0.55, screen=0.35, key=0.35, metal=0.3)

T = math.radians(L.FRONT_TILT)
ORIGIN = Vector((0.0, 0.0, L.HOOD_BOTTOM))
EU, EV, EW = Vector((1.0, 0.0, 0.0)), Vector((0.0, math.sin(T), math.cos(T))), Vector((0.0, math.cos(T), -math.sin(T)))
FACE = Matrix(((EU.x, EW.x, EV.x, 0.0), (EU.y, EW.y, EV.y, 0.0), (EU.z, EW.z, EV.z, 0.0), (0.0, 0.0, 0.0, 1.0)))


def front(u, v, w):
    """The front face's (u across, v up the face from the hood's underside, w into the box) in the console's frame."""
    return ORIGIN + EU * u + EV * v + EW * w


def on_face(p):
    """A point's (u, v, w) on the front face."""
    d = p - ORIGIN
    return d.dot(EU), d.dot(EV), d.dot(EW)


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def arc(cy, cz, r, a0, a1, n):
    """n points round an arc from a0 towards a1 (degrees), not including a1."""
    angles = [math.radians(a0 + (a1 - a0) * k / n) for k in range(n)]
    return [(cy + r * math.cos(a), cz + r * math.sin(a)) for a in angles]


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def hood_top(grow):
    """The leaning face and the lid's rounded front edge, grown by `grow` outward: points (y, z) from the hood's
    underside up to the top."""
    r = L.TOP_FRONT["r"]
    top = L.HEIGHT - 1.0 + grow
    y0 = -grow / math.cos(T)                 # the face, moved forward
    yc = y0 + (r + (top - r - L.HOOD_BOTTOM) * math.sin(T)) / math.cos(T)
    return [(y0, L.HOOD_BOTTOM - grow)] + arc(yc, top - r, r, 180.0 - L.FRONT_TILT, 90.0, 6) + [(yc, top)]


def profile():
    """The whole console's side profile, round from the hood's underside at its front."""
    tb, h = L.TOP_BACK, L.HOUSING
    points = hood_top(0.0) + L.PROFILE_TOP
    points += arc(tb["at"] - tb["r"], L.PROFILE_TOP[-1][1] - tb["r"], tb["r"], 90.0, 0.0, 4)
    points += [(tb["at"], L.PROFILE_TOP[-1][1] - tb["r"]), (tb["at"], h["front"]), (h["y"], h["back"])]
    rb, rf = L.BACK["r"], L.BASE["r"]
    points += [(L.DEPTH - 3.0, h["back"] - 4.0)] + arc(L.DEPTH - 3.0 - rb, L.FEET + rb, rb, 0.0, -90.0, 5)
    points += [(L.DEPTH - 3.0 - rb, L.FEET)] + arc(L.BASE["front"] + rf, L.FEET + rf, rf, -90.0, -180.0, 5)
    points += [(L.BASE["front"], L.FEET + rf), (L.BASE["front"], L.HOOD_BOTTOM)]
    return points


def proud():
    """The front box's profile, a hair bigger than the console's where they meet: from the hood's underside up the
    face, over the lid to the seam, down the seam."""
    points = hood_top(0.03)
    return points + [(L.SEAM, points[-1][1]), (L.SEAM, L.HOOD_BOTTOM - 0.03)]


def hood_ring(w, size, v0, r):
    width, height = size
    return [front(u, v, w) for u, v in rounded(0.0, v0 + height / 2, width, height, r, 4)]


def console(m):
    """The console: the profile at the base's width and the proud front box, the hood's recess, the bay, the
    cartridge slot, its frame and the feet; printed."""
    half = L.BASE["half"]
    body = prism_x("vectrex", profile(), -half, half, m["case"])
    box_ = prism_x("front_box", proud(), -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    boolean(body, box_, "UNION")
    bevel(body, 1.2, segments=2, angle=40)

    hd = L.HOOD
    (fw, fh, fv), (bw, bh, bv) = hd["front"], hd["back"]
    rings = [hood_ring(-8.0, (fw, fh), fv, hd["r"][0]), hood_ring(0.0, (fw, fh), fv, hd["r"][0]),
             hood_ring(hd["depth"], (bw, bh), bv, hd["r"][1])]
    boolean(body, solid("hood", rings, m["case"]))
    (bx0, bx1), (bz0, bz1) = L.BAY["x"], L.BAY["z"]
    bay_back = L.BASE["front"] + L.BAY["depth"]
    boolean(body, box("bay", bx0, bx1, L.BASE["front"] - 10.0, bay_back, bz0, bz1, m["case"]))
    (sy0, sy1), (sz0, sz1) = L.SLOT["y"], L.SLOT["z"]
    boolean(body, box("slot", half - 75.0, half + 10.0, sy0, sy1, sz0, sz1, m["case"]))
    (u0, u1), (v0, v1) = L.STRIP["u"], L.STRIP["v"]
    sunk = L.STRIP["depth"]
    boolean(body, solid("strip", [[front(u, v, w) for u, v in ((u1, v0), (u1, v1), (u0, v1), (u0, v0))]
                                  for w in (-5.0, sunk)], m["case"]))

    # The printing: the case's colour, then the hood's walls and the bezel, the lid's strip, the bay's back wall.
    paint(body, m["case"], swatch("case"), lambda c, n, name: True)

    def in_hood(c):
        u, v, w = on_face(c)
        return 0.3 < w < hd["depth"] + 0.5 and abs(u) < fw / 2 + 1.0 and fv - 1.0 < v < fv + fh + 1.0

    paint(body, m["case"], swatch("hood"), lambda c, n, name: in_hood(c))
    paint(body, m["case"], swatch("bezel"), lambda c, n, name: in_hood(c) and on_face(c)[2] > hd["depth"] - 0.3)
    strip = atlas_uv(L.REGIONS["strip"], u1 - u0, v1 - v0)
    paint(body, m["case"], lambda co: strip(on_face(co)[0] - u0, v1 - on_face(co)[1]),
          lambda c, n, name: n.dot(-EW) > 0.95 and abs(on_face(c)[2] - sunk) < 0.2 and v0 < on_face(c)[1] < v1)
    wall = atlas_uv(L.REGIONS["bay"], bx1 - bx0, bz1 - bz0)
    paint(body, m["case"], lambda co: wall(co.x - bx0, bz1 - co.z),
          lambda c, n, name: n.y < -0.9 and abs(c.y - bay_back) < 0.5)
    paint(body, m["case"], swatch("dark"),
          lambda c, n, name: c.x > half - 75.0 and sy0 - 0.5 < c.y < sy1 + 0.5 and sz0 - 0.5 < c.z < sz1 + 0.5
          and c.x < half - 0.5)

    # The slot's frame, standing out of the right side; RESET and the volume knob in the bay; the feet.
    f = L.SLOT["frame"]
    frame = prism_x("frame", rounded((sy0 + sy1) / 2, (sz0 + sz1) / 2, sy1 - sy0 + 2 * f, sz1 - sz0 + 2 * f, 5.0, 3),
                    half - 0.5, half + L.SLOT["lip"], m["case"])
    boolean(frame, prism_x("hole", rounded((sy0 + sy1) / 2, (sz0 + sz1) / 2, sy1 - sy0, sz1 - sz0, 2.0, 3),
                           half - 2.0, half + 5.0, m["case"]))
    bevel(frame, 0.6, segments=1)
    paint(frame, m["case"], swatch("hood"), lambda c, n, name: True)
    parts = [frame]
    for name, spec in (("reset", L.RESET), ("volume", L.VOLUME)):
        (x, z), r, h = spec["at"], spec["r"], spec["height"]
        knob = prism_y(name, circle(x, z, r, 20), bay_back - h, bay_back + 0.5, m["key"])
        bevel(knob, 0.6, segments=1)
        parts.append(knob)
    for x in (-85.0, 85.0):
        for y in (45.0, 255.0):
            foot = prism_z("foot", circle(x, y, 10.0, 16), 0.0, L.FEET + 0.5, m["key"])
            parts.append(foot)
    return join([body] + parts, "vectrex")


def screen(m, name, region):
    """One of the tube's faces (or the overlay, flat): its node at its middle, facing the viewer."""
    tw, th = L.TUBE["size"]
    rx, ry, rw, rh = L.REGIONS[region]
    flat = name == "overlay"
    part = curved(name, tw, th, 0.0 if flat else L.TUBE["bulge"],
                  lambda a, b: ((rx + a * rw) / L.ATLAS, 1 - (ry + b * rh) / L.ATLAS), m["screen"], 16, 14)
    part.data.transform(FACE)
    w = L.OVERLAY["w"] if flat else L.HOOD["depth"] - 0.4
    return part, front(0.0, L.TUBE["v"] + th / 2, w)


def dark_tube(m):
    """The tube's face dark, standing just behind the lit faces, in front of those waiting behind the bezel."""
    tw, th = L.TUBE["size"]
    part = curved("tube", tw, th, L.TUBE["bulge"], lambda a, b: swatch("dark")(None), m["screen"], 16, 14)
    part.data.transform(FACE)
    part.data.transform(Matrix.Translation(front(0.0, L.TUBE["v"] + th / 2, L.HOOD["depth"] - 0.15)))
    return part


# ---- The controller --------------------------------------------------------------------------------------------------

def pad_frame():
    """The controller's frame: its own (x along it, y back from its front edge, z up) to the console's."""
    pw, pd, _ = L.PAD["size"]
    x, y = L.PAD["at"]
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z") @ \
        Matrix.Translation((0.0, -pd / 2, 0.0))


def controller(m):
    """The controller's box (its face printed, the notch for the cord), the joystick's ring; its joystick and buttons,
    each with where its node goes."""
    pw, pd, ph = L.PAD["size"]
    body = prism_z("pad", rounded(0.0, pd / 2, pw, pd, L.PAD["r"], 4), 0.0, ph, m["case"])
    bevel(body, 1.6, segments=2)
    nx, (nw, nd) = L.NOTCH["x"], L.NOTCH["size"]
    boolean(body, box("notch", nx - nw / 2, nx + nw / 2, pd - nd, pd + 5.0, ph - 10.0, ph + 5.0, m["case"]))
    paint(body, m["case"], swatch("key"), lambda c, n, name: True)
    face = atlas_uv(L.REGIONS["pad"], pw, pd)
    paint(body, m["case"], lambda co: face(co.x + pw / 2, pd - co.y), lambda c, n, name: n.z > 0.9 and c.z > ph - 0.5)
    s = L.STICK
    sx, sy = s["at"]
    ring = prism_z("ring", circle(sx, sy, s["ring"], 28), ph - 0.5, ph + 2.5, m["key"])
    bevel(ring, 0.8, segments=1)
    fixed = join([body, ring], "controller")

    stick = prism_z("stick", circle(0.0, 0.0, s["r"], 12), -2.0, s["height"], m["metal"])
    kr, kh = s["knob"]
    knob = prism_z("knob", circle(0.0, 0.0, kr, 16), s["height"] - 2.0, s["height"] - 2.0 + kh, m["metal"])
    bevel(knob, 1.2, segments=2)
    stick = join([stick, knob], "joystick")
    to_world = pad_frame()
    nodes = {"joystick": (stick, to_world @ Vector((sx, sy, ph + 2.5)))}
    b = L.BUTTONS
    for k, x in enumerate(b["x"]):
        button = prism_z(f"button_{k + 1}", circle(0.0, 0.0, b["r"], 20), -2.0, b["height"], m["key"])
        bevel(button, 1.0, segments=2)
        nodes[f"button_{k + 1}"] = (button, to_world @ Vector((x, b["y"], ph)))
    fixed.data.transform(to_world)
    turn = Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z")
    for part, _ in nodes.values():
        part.data.transform(turn)
    return fixed, nodes


def coil(m, path, length):
    """The coiled cord: a wire wound round a path (a function of 0..1), a tube along the helix."""
    c = L.CORD
    turns = length / c["pitch"]
    n = int(turns * 8)
    pts = [Vector(path(k / n)) for k in range(n + 1)]
    helix = []
    normal = Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(pts):
        tangent = (pts[min(k + 1, n)] - pts[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        a = 2 * math.pi * turns * k / n
        helix.append(p + (normal * math.cos(a) + binormal * math.sin(a)) * c["r"])
    bm = bmesh.new()
    sides = 5
    rings = []
    normal = Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(helix):
        tangent = (helix[min(k + 1, n)] - helix[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        around = [2 * math.pi * j / sides for j in range(sides)]
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * c["wire"]) for a in around])
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            bm.faces.new([a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cord = new_object("cord", bm, m["key"])
    for p in cord.data.polygons:
        p.use_smooth = True
    return cord


def cord(m):
    """From the notch in the controller's back edge, over the table and up into the bay's port."""
    pw, pd, ph = L.PAD["size"]
    start = pad_frame() @ Vector((L.NOTCH["x"], pd - 4.0, ph - 6.0))
    px, pz = L.PORT["at"]
    end = Vector((px, L.BASE["front"] + L.BAY["depth"] - 2.0, pz))
    c1 = start + Vector((6.0, 30.0, -12.0))
    c2 = end + Vector((-6.0, -60.0, -40.0))

    def path(t):
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        return start * a + c1 * b + c2 * c + end * d

    length = sum((Vector(path((k + 1) / 200)) - Vector(path(k / 200))).length for k in range(200))
    return coil(m, path, length)


def cartridge(m):
    """The cartridge, its middle at the origin, lying flat (its label on top) and pointing into the slot (-x)."""
    c = L.CART
    length, width, t = c["length"], c["width"], c["thickness"]
    part = prism_z("cartridge", rounded(0.0, 0.0, length, width, 3.0, 3), -t / 2, t / 2, m["case"])
    bevel(part, 1.0, segments=2)
    paint(part, m["case"], swatch("key"), lambda co, n, name: True)
    label = atlas_uv(L.REGIONS["cart"], length, width)
    paint(part, m["case"], lambda co: label(co.x + length / 2, width / 2 - co.y),
          lambda co, n, name: n.z > 0.9 and co.z > t / 2 - 0.5)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

BEHIND = 6.0                 # how far back the tube's faces that aren't lit wait: behind the bezel
GAME = [(64, "game_1"), (67, "game_1"), (80, "game_2"), (93, "game_3"), (106, "game_1"), (119, "game_2"),
        (132, "game_3"), (145, "game_1"), (158, "game_2")]


def showing(f):
    """Which of the tube's faces is lit at frame f: the power-on screen, or the game's frames from 64 to 171 (but for
    the flicker as it comes on, when the overlay shows the tube dark)."""
    if f < 64 or f >= 171:
        return "logo"
    if 65 <= f < 67:
        return "overlay"
    name = "logo"
    for start, frame in GAME:
        if f >= start:
            name = frame
    return name


def timeline(f):
    lit = showing(f)
    back = EW * BEHIND
    poses = {name: Pose() if name == lit else Pose(x=back.x, y=back.y, z=back.z)
             for name in ("logo", "game_1", "game_2", "game_3")}

    # The cartridge: appears out to the right, slides in, a nudge; later out again and gone.
    travel = L.CART["travel"]
    if f < 12 or f >= 220:
        poses["cartridge"] = Pose(scale=HIDDEN)
    elif f < 18:
        poses["cartridge"] = Pose(x=travel, scale=max(HIDDEN, back_out(phase(f, 12, 17))))
    elif f < 36:
        poses["cartridge"] = Pose(x=travel * (1 - smooth(phase(f, 18, 36))))
    elif f < 196:
        poses["cartridge"] = Pose(x=wobble(f, 36, -2.0, period=8.0, decay=4.0))
    elif f < 214:
        poses["cartridge"] = Pose(x=travel * smooth(phase(f, 196, 214)))
    else:
        poses["cartridge"] = Pose(x=travel, scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 220))))

    # The overlay: comes in from in front of the hood and settles; it shows only while the tube's dark.
    out = -EW * L.OVERLAY["out"]
    if f < 44 or f >= 196:
        poses["overlay"] = Pose(scale=HIDDEN)
    elif f < 64:
        k = 1 - smooth(phase(f, 48, 62))
        poses["overlay"] = Pose(x=out.x * k, y=out.y * k, z=out.z * k, scale=max(HIDDEN, back_out(phase(f, 44, 49))))
    elif f < 171:
        poses["overlay"] = Pose() if lit == "overlay" else Pose(scale=HIDDEN)
    else:
        k = ease_in(phase(f, 176, 190))
        poses["overlay"] = Pose(x=out.x * k, y=out.y * k, z=out.z * k,
                                scale=max(HIDDEN, 1 - ease_in(phase(f, 188, 196))))

    # The controller: the joystick rocks while the game plays; button 1 fires with the shots, 4 now and then.
    playing = 67 <= f < 171
    t = (f - 67) / 30.0
    tilt = L.STICK["tilt"] * smooth(phase(f, 67, 74)) * (1 - smooth(phase(f, 164, 171))) if playing else 0.0
    poses["joystick"] = Pose(roll=tilt * math.sin(2 * math.pi * 0.9 * t),
                             pitch=0.5 * tilt * math.sin(2 * math.pi * 1.7 * t))
    for k in range(1, 5):
        poses[f"button_{k}"] = Pose()
    for start in (80, 119, 158):
        if start <= f < start + 5:
            poses["button_1"] = Pose(z=-L.BUTTONS["press"] * math.sin(math.pi * phase(f, start, start + 5)))
    for start in (100, 139):
        if start <= f < start + 5:
            poses["button_4"] = Pose(z=-L.BUTTONS["press"] * math.sin(math.pi * phase(f, start, start + 5)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out_path = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "vectrex_print.png"))
    m = {
        "case": material("case", L.COLOURS["print"], ROUGHNESS["case"], atlas),
        "screen": material("screen", L.COLOURS["glass"], ROUGHNESS["screen"], atlas),
        "key": material("key", L.COLOURS["key"], ROUGHNESS["key"]),
        "metal": material("metal", L.COLOURS["silver"], ROUGHNESS["metal"]),
    }

    body = console(m)
    pad, pad_nodes = controller(m)
    fixed = join([body, pad, cord(m), dark_tube(m)], "vectrex")
    (fw, fh, fv), depth = L.HOOD["front"], L.HOOD["depth"]
    glass = [mat.name for mat in fixed.data.materials].index("screen")
    for p in fixed.data.polygons:
        u, v, w = on_face(p.center)
        hood = 0.3 < w < depth + 0.5 and abs(u) < fw / 2 + 1.0 and fv - 1.0 < v < fv + fh + 1.0
        p.use_smooth = p.material_index == glass or not hood
    fixed.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("vectrex_root", None)
    scene.collection.objects.link(root)
    fixed.parent = root
    nodes = {}
    for name in ("logo", "game_1", "game_2", "game_3", "overlay"):
        part, where = screen(m, name, name)
        part.parent = fixed
        part.location = where
        nodes[name] = part
    cart = cartridge(m)
    cart.parent = fixed
    c = L.CART
    cart.location = (L.BASE["half"] + c["out"] - c["length"] / 2, sum(L.SLOT["y"]) / 2, sum(L.SLOT["z"]) / 2)
    nodes["cartridge"] = cart
    for name, (part, where) in pad_nodes.items():
        part.parent = fixed
        part.location = where
        nodes[name] = part

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in fixed.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [fixed] + list(nodes.values())
    print(f"Vectrex: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(fixed.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out_path, animations=True)


if __name__ == "__main__":
    main()
