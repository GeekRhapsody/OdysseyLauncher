"""The console theme's Vectrex system model (godot/themes/console/models/systems/vectrex.glb): Milton Bradley's
Vectrex with its controller in front of it.

Built in Blender (vectrex_layout.py has the measurements, taken from photographs). The console is its side profile
(the hood's leaning face, the rounded lid, the front box's back, the tube housing's falling top, the back and the
underside) at the base's width, with the front box standing proud of it at its sides; the hood's recess is cut into the
face, narrowing back to the bezel, the tube's face in front of it; the bay is cut into the base under the hood, the
cartridge slot into its right side. The controller lies on the table in front, its coiled cord running up into the
bay's port. Two textures drawn by vectrex_print.py: the printing (the controller's face, the bay's back wall, the
cartridge's label, the lid's strip and swatches) and the glass's still.

The tube's glass is the material `video`: while the card is focused, the launcher plays the theme's video for it there
(godot/themes/console/videos/vectrex.mp4, drawn by vectrex_video.py, the game's overlay sliding in and out in it),
starting it again each time the clip loops (A6 Card videos); otherwise, and where there's no decoder, it shows its own
texture: the power-on screen, VECTREX drawn in lines.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the console and
the controller; the console holding the cartridge (waiting shrunk to nothing), the controller its joystick (its origin
at its pivot) and its four buttons.

The `focused` clip (8 s, looping; its timing is vectrex_layout.py's, which the video follows): a cartridge slides into
the side; while the video plays the game, the joystick rocks, button 1 fires and button 4 raises the shield; then the
cartridge comes out again.

Four materials (case, key, metal, video) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/vectrex_print.py artifacts/vectrex
    blender -b --factory-startup --python tools/console-models/vectrex.py -- artifacts/vectrex godot/themes/console/models/systems/vectrex.glb
    python tools/console-models/vectrex_video.py godot/themes/console/videos/vectrex.mp4
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
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth, wobble  # noqa: E402
from mega_drive import prism_y, prism_z  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)

TILT_YAW = -28.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: the top tips up towards the viewer

ROUGHNESS = dict(case=0.55, key=0.35, metal=0.3, video=0.35)

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

def cartridge_pose(f):
    """The cartridge: appears out to the right, slides in, a nudge; later out again and gone."""
    travel = L.CART["travel"]
    if f < L.CART_SHOW[0] or f >= L.CART_GONE[1]:
        return Pose(scale=HIDDEN)
    if f < L.CART_IN[0]:
        return Pose(x=travel, scale=max(HIDDEN, back_out(phase(f, *L.CART_SHOW))))
    if f < L.CART_IN[1]:
        return Pose(x=travel * (1 - smooth(phase(f, *L.CART_IN))))
    if f < L.CART_OUT[0]:
        return Pose(x=wobble(f, L.CART_IN[1], -2.0, period=8.0, decay=4.0))
    if f < L.CART_OUT[1]:
        return Pose(x=travel * smooth(phase(f, *L.CART_OUT)))
    return Pose(x=travel, scale=max(HIDDEN, 1 - ease_in(phase(f, *L.CART_GONE))))


def timeline(f):
    """The clip at frame f. The controller: the joystick rocks while the game plays (the video's ship follows it);
    button 1 fires the bolts, button 4 raises the shield."""
    roll, pitch = L.stick(f)
    poses = {"cartridge": cartridge_pose(f), "joystick": Pose(roll=roll, pitch=pitch)}
    for k in range(1, 5):
        poses[f"button_{k}"] = Pose()
    for name, starts in (("button_1", L.SHOTS), ("button_4", L.SHIELDS)):
        down = max(L.pressed(f, f0) for f0 in starts)
        if down > 0.0:
            poses[name] = Pose(z=-L.BUTTONS["press"] * down)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out_path = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "vectrex_print.png"))
    still = bpy.data.images.load(os.path.join(images, "vectrex_screen.png"))
    m = {
        "case": material("case", L.COLOURS["print"], ROUGHNESS["case"], atlas),
        "key": material("key", L.COLOURS["key"], ROUGHNESS["key"]),
        "metal": material("metal", L.COLOURS["silver"], ROUGHNESS["metal"]),
        "video": material("video", L.COLOURS["glass"], ROUGHNESS["video"], still),
    }

    body = console(m)
    pad, pad_nodes = controller(m)
    # The tube's glass: the launcher plays the card's video on the material named video (A6 Card videos), UVs 0 to 1,
    # upright.
    tw, th = L.TUBE["size"]
    glass = curved("glass", tw, th, L.TUBE["bulge"], lambda a, b: (a, 1 - b), m["video"], 16, 14)
    glass.data.transform(Matrix.Translation(front(0.0, L.TUBE["v"] + th / 2, L.TUBE["w"])) @ FACE)
    fixed = join([body, pad, cord(m), glass], "vectrex")
    (fw, fh, fv), depth = L.HOOD["front"], L.HOOD["depth"]
    video = [mat.name for mat in fixed.data.materials].index("video")
    for p in fixed.data.polygons:
        u, v, w = on_face(p.center)
        hood = 0.3 < w < depth + 0.5 and abs(u) < fw / 2 + 1.0 and fv - 1.0 < v < fv + fh + 1.0
        p.use_smooth = p.material_index == video or not hood
    fixed.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("vectrex_root", None)
    scene.collection.objects.link(root)
    fixed.parent = root
    nodes = {}
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
