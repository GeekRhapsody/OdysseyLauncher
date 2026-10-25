"""The console theme's Sega 32X system model (godot/themes/console/models/systems/sega32x.glb): the Mega Drive 32X
plugged into the first Mega Drive.

Built in Blender (sega32x_layout.py has the measurements, taken from photographs). The 32X's cap is lofted through
cross-sections along its length: the underside, the upright back, the flat top, the slope falling to the wave, the
groove and the matte lip bulging out under it, each section lower towards the ends (and the wave higher), and drawn in
round the plan's corners and the ends' edges. The island is joined onto its top, with the recess and the slot's
opening cut into it; the neck and the plug stand under it. The Mega Drive is mega_drive.py's own, built by its build().
The printing is two textures: sega32x_print.py's (the badge, the vents, the flaps' ribs, the cartridge's label,
swatches) and mega_drive_print.py's (the Mega Drive's top), both drawn into the same folder. The cartridge is the 32X's
own shell, from a photograph of one in Chromagi's catalogue of Sega's games.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the Mega Drive; the
Mega Drive holding the 32X (its origin at the plug's foot, in the slot); the 32X holding its two dust flaps (each on its
hinge) and the cartridge (waiting over its slot, shrunk to nothing).

The `focused` clip (8 s, looping): the 32X crouches, hops off the Mega Drive, turns once round in the air and drops
back into the slot with a squash; a cartridge appears over its own slot and falls in, pushing the flaps down, and seats
with a push; later it rises out, the flaps spring shut behind it, and it goes.

Seven materials (the Mega Drive's print, gloss, dark and reset; case, shell, pcb) and two textures, within the system
model budget. Run from the repo root:

    python tools/console-models/mega_drive_print.py artifacts/sega32x
    python tools/console-models/sega32x_print.py artifacts/sega32x
    blender -b --factory-startup --python tools/console-models/sega32x.py -- artifacts/sega32x godot/themes/console/models/systems/sega32x.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sega32x_layout as L  # noqa: E402
from amiga import paint, rounded  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, hop, key, phase, smooth, wobble  # noqa: E402
from mega_drive import build as mega_drive, prism_y, prism_z, stadium  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
RINGS = 45           # the cap's cross-sections, closer together towards the ends
FOOT = -(L.NECK["height"] + L.PLUG["height"])   # the plug's foot, the 32X's origin, below the cap's underside

ROUGHNESS = dict(case=0.6, shell=0.2)


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


# ---- The cap's cross-sections ----------------------------------------------------------------------------------------

def line(p0, p1, n):
    """n points from p0 towards p1, not including p1."""
    return [(p0[0] + (p1[0] - p0[0]) * k / n, p0[1] + (p1[1] - p0[1]) * k / n) for k in range(n)]


def arc(cy, cz, r, a0, a1, n):
    return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n)]


def bezier(p0, p1, p2, p3, n):
    out = []
    for k in range(n):
        t = k / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def top_height(x):
    return L.TOP - L.TOP_FALL * (x / (L.WIDTH / 2)) ** 2


def crease_height(x):
    c = L.CREASE
    return c["mid"] + (c["ends"] - c["mid"]) * smooth(phase(abs(x), c["flat"], c["rise"]))


def section(x):
    """The cap's cross-section at x, before its ends are drawn in: (y, z) points from the lip's foot back along the
    underside, up the back, forward over the top, down the slope to the wave, through the groove and round the lip;
    and each point's part ("case" or "shell") for the faces from it to the next."""
    h, zc = top_height(x), crease_height(x)
    yb, yf, yc, s = L.DEPTH / 2, -L.DEPTH / 2, L.CREASE["y"], L.SLOPE
    foot, rnd, wall = L.BACK["foot"], L.BACK["round"], L.BACK["wall"]
    under, lip, step = L.LIP["under"], L.LIP["z"], L.LIP["step"]
    parts = [
        ("case", line((under, 0.0), (yb - foot, 0.0), 8)),
        ("case", arc(yb - foot, foot, foot, -90, 0, 3)),
        ("case", line((yb, foot), (yb, h - wall), 5)),
        ("shell", arc(yb - rnd, h - wall, rnd, 0, 90, 6)),
        ("shell", line((yb - rnd, h), (s, h), 10)),
        ("shell", bezier((s, h), (s - 0.5 * (s - yc), h), (yc + 0.12 * (s - yc), zc + 0.45 * (h - zc)), (yc, zc), 10)),
        ("shell", [(yc, zc)]),
        ("case", [(yc - 1.0, zc - 1.6)]),
        ("case", bezier((yc - step, zc + 0.4), (yc - step - 4.0, zc + 0.4), (yf, lip + 0.55 * (zc - lip)), (yf, lip),
                        8)),
        ("case", bezier((yf, lip), (yf, lip * 0.45), (under - 3.5, 0.0), (under, 0.0), 5)),
    ]
    return [p for _, points in parts for p in points], [kind for kind, points in parts for _ in points]


def drawn_in(r, x):
    """How far a corner of radius r draws the cap in at x."""
    e = min(r, max(0.0, abs(x) - (L.WIDTH / 2 - r)))
    return r - math.sqrt(r * r - e * e)


def cap(m):
    """The cap: the cross-sections lofted along x, drawn in round the plan's corners and the ends' top and bottom
    edges, capped flat at the ends."""
    rings, kinds = [], None
    for k in range(RINGS):
        x = L.WIDTH / 2 * math.sin(math.pi / 2 * (2 * k / (RINGS - 1) - 1))
        points, kinds = section(x)
        h = top_height(x)
        dy, dt, db = (drawn_in(L.ROUND[name], x) for name in ("plan", "top", "bottom"))
        rings.append([(x, y * (L.DEPTH / 2 - dy) / (L.DEPTH / 2), db + z * (h - dt - db) / h) for y, z in points])
    bm = bmesh.new()
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(verts, verts[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]]).material_index = 0 if kinds[i] == "case" else 1
    ends = [bm.faces.new(verts[0]), bm.faces.new(list(reversed(verts[-1])))]
    bmesh.ops.triangulate(bm, faces=ends, quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = new_object("sega32x", bm, m["case"])
    body.data.materials.append(m["shell"])
    return body


# ---- The 32X ---------------------------------------------------------------------------------------------------------

def badge_frame():
    """The slope's frame for the badge: its origin on the wave at the middle, v up the slope's chord, n out of it."""
    origin = Vector((0.0, L.CREASE["y"], L.CREASE["mid"]))
    v = Vector((0.0, L.SLOPE - L.CREASE["y"], L.TOP - L.CREASE["mid"])).normalized()
    return origin, v, Vector((1.0, 0.0, 0.0)).cross(v)


def thirty_two_x(m):
    """The 32X in its own frame (the cap's underside at z = 0): the cap with the island, the recess and the slot; the
    badge and the vents printed; the neck and the plug under it."""
    body = cap(m)
    ix, iy = L.ISLAND["at"]
    il, iw = L.ISLAND["size"]
    island_top = L.TOP + L.ISLAND["height"]
    island = prism_z("island", stadium(ix, iy, il, iw, 12), L.TOP - 8.0, island_top, m["shell"])
    bevel(island, 1.6, segments=2, angle=40)
    boolean(body, island, "UNION")
    rl, rw = L.RECESS["size"]
    floor = island_top - L.RECESS["depth"]
    boolean(body, prism_z("recess", stadium(ix, iy, rl, rw, 10), floor, island_top + 10.0, m["case"]))
    sl, sw = L.SLOT["size"]
    boolean(body, prism_z("opening", rounded(ix, iy, sl, sw, 3.0, 3), L.SLOT["floor"], island_top + 10.0, m["dark"]))

    # The printing: the case's colour everywhere, then the recess, the badge on the slope and the vents on the ends.
    for name in ("case", "shell"):
        paint(body, m[name], swatch(name), lambda c, n, kind, name=name: kind == name)
    paint(body, m["case"], swatch("recess"),
          lambda c, n, name: name != "dark" and abs(c.x - ix) < rl / 2 + 0.5 and abs(c.y - iy) < rw / 2 + 0.5
          and floor - 0.5 < c.z < island_top - 0.5)
    origin, up, out = badge_frame()
    (u0, u1), (v0, v1) = L.BADGE_AREA["u"], L.BADGE_AREA["v"]
    slope = atlas_uv(L.REGIONS["badge"], u1 - u0, v1 - v0)
    paint(body, m["shell"], lambda co: slope(co.x - u0, v1 - (co - origin).dot(up)),
          lambda c, n, name: name == "shell" and abs(c.x) < u1 and c.y < L.SLOPE + 3.0 and n.dot(out) > 0.2
          and v0 < (c - origin).dot(up) < v1)
    ends = atlas_uv(L.REGIONS["vents"], 80.0, 50.0)
    paint(body, m["shell"], lambda co: ends(co.y + 40.0, 60.0 - co.z),
          lambda c, n, name: name == "shell" and abs(c.x) > L.VENTS["x"] and abs(n.x) > 0.3)

    # The neck and the plug, its two metal windows and the connector's edge.
    nl, nw = L.NECK["size"]
    neck = prism_z("neck", stadium(0.0, 0.0, nl, nw, 10), -L.NECK["height"], 0.8, m["case"])
    bevel(neck, 1.5, segments=2)
    pl, pw = L.PLUG["size"]
    plug = prism_z("plug", rounded(0.0, 0.0, pl, pw, 5.0, 3), FOOT, -L.NECK["height"] + 0.5, m["case"])
    bevel(plug, 0.8, segments=1)
    parts = [neck, plug]
    for part in parts:
        paint(part, m["case"], swatch("case"), lambda c, n, name: True)
    ww, wh = L.PLUG["window"]
    for x in L.PLUG["windows"]:
        window = box("window", x - ww / 2, x + ww / 2, -pw / 2 - 0.3, -pw / 2 + 0.5, FOOT + 6.0, FOOT + 6.0 + wh,
                     m["case"])
        paint(window, m["case"], swatch("silver"), lambda c, n, name: True)
        parts.append(window)
    parts.append(box("edge", -pl / 2 + 6.0, pl / 2 - 6.0, -0.8, 0.8, FOOT - 1.5, FOOT + 0.5, m["pcb"]))
    return join([body] + parts, "sega32x")


def flap(m, side):
    """A dust flap, its origin on its hinge (the opening's front edge, side -1, or its back edge, side 1), drooping
    towards the middle."""
    f = L.FLAP
    length, width, t = f["length"], f["width"], f["thickness"]
    y0, y1 = (0.0, width) if side < 0 else (-width, 0.0)
    part = box("flap", -length / 2, length / 2, y0, y1, -t, 0.0, m["case"])
    paint(part, m["case"], swatch("flap"), lambda c, n, name: True)
    ribs = atlas_uv(L.REGIONS["flap"], length, width)
    paint(part, m["case"], lambda co: ribs(co.x + length / 2, abs(co.y)), lambda c, n, name: n.z > 0.9)
    part.data.transform(Matrix.Rotation(math.radians(f["droop"] * side), 4, "X"))
    hinge = Vector((L.ISLAND["at"][0], L.ISLAND["at"][1] + side * L.SLOT["size"][1] / 2,
                    L.TOP + L.ISLAND["height"] - L.RECESS["depth"] - 0.4))
    return part, hinge


def cartridge(m):
    """The 32X's cartridge, standing on its connector's edge at the origin, its label to the front (-y)."""
    c = L.CART
    w, h, t, r = c["width"], c["height"], c["thickness"], c["corner"]
    outline = [(-w / 2, 0.0), (w / 2, 0.0)] + arc(w / 2 - r, h - r, r, 0, 90, 4) + [(w / 2 - r, h)] \
        + arc(-w / 2 + r, h - r, r, 90, 180, 4) + [(-w / 2, h - r)]
    shell = prism_y("cartridge", outline, -t / 2, t / 2, m["case"])
    bevel(shell, 1.0, segments=2)
    lw, lh = c["label"]
    z0 = c["label_z"]
    boolean(shell, box("recess", -lw / 2 - 0.8, lw / 2 + 0.8, -t / 2 - 2.0, -t / 2 + 0.8, z0 - 0.8, z0 + lh + 0.8,
                       m["case"]))
    paint(shell, m["case"], swatch("cart"), lambda co, n, name: True)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    corners = [(-lw / 2, z0), (lw / 2, z0), (lw / 2, z0 + lh), (-lw / 2, z0 + lh)]
    face = bm.faces.new([bm.verts.new((x, -t / 2 + 0.75, z)) for x, z in corners])
    print_uv = atlas_uv(L.REGIONS["label"], lw, lh)
    for loop, (x, z) in zip(face.loops, corners):
        loop[uv].uv = print_uv(x + lw / 2, z0 + lh - z)
    label = new_object("cart_print", bm, m["case"])
    edge = box("edge", -46.0, 46.0, -1.0, 1.0, -1.5, 0.5, m["pcb"])
    part = join([shell, label, edge], "cartridge")
    for p in part.data.polygons:
        p.use_smooth = True
    part.data.set_sharp_from_angle(angle=math.radians(35))
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

def flaps_open(f):
    if f < 73:
        return 0.0
    if f < 189:
        return smooth(phase(f, 73, 76))
    return 1.0 - back_out(phase(f, 189, 198))


def timeline(f):
    # The hop: a crouch, up and once round, down into the slot and a squash.
    if f < 12:
        squash = 0.08 * smooth(phase(f, 6, 12))
    elif f < 14:
        squash = 0.08 - 0.14 * smooth(phase(f, 12, 14))
    elif f < 36:
        squash = -0.06 * (1 - smooth(phase(f, 14, 26)))
    else:
        squash = wobble(f, 36, 0.09, period=10.0, decay=6.0)
    x32 = Pose(z=hop(f, 12, 36, 48.0), spin=360.0 * smooth(phase(f, 14, 34)), squash=squash)

    # The cartridge: appears over the slot, falls in, a push; later out, and gone.
    above = L.CART["above"]
    if f < 50 or f >= 210:
        cart = Pose(scale=HIDDEN)
    elif f < 60:
        cart = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 50, 57))))
    elif f < 78:
        cart = Pose(z=above * (1 - ease_in(phase(f, 60, 78))))
    elif f < 186:
        cart = Pose(z=-2.5 * math.sin(math.pi * phase(f, 78, 86)))
    elif f < 202:
        cart = Pose(z=above * ease_out(phase(f, 186, 202)))
    else:
        cart = Pose(z=above, scale=max(HIDDEN, 1 - ease_in(phase(f, 202, 210))))
    swing = (L.FLAP["open"] - L.FLAP["droop"]) * flaps_open(f)
    return {"sega32x": x32, "cartridge": cart, "flap_front": Pose(pitch=-swing), "flap_back": Pose(pitch=swing)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out_path = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    md_print = bpy.data.images.load(os.path.join(images, "megadrive_print.png"))
    x_print = bpy.data.images.load(os.path.join(images, "sega32x_print.png"))
    m = {
        "print": material("print", "#FFFFFF", 0.55, md_print),
        "gloss": material("gloss", "#FFFFFF", 0.18, md_print),
        "dark": material("dark", "#060607", 0.9),
        "reset": material("reset", "#C4C5BC", 0.5),
        "case": material("case", L.COLOURS["print"], ROUGHNESS["case"], x_print),
        "shell": material("shell", L.COLOURS["print"], ROUGHNESS["shell"], x_print),
        "pcb": material("pcb", "#B8924A", 0.35),
    }

    md = mega_drive(m)
    x32 = thirty_two_x(m)
    x32.data.transform(Matrix.Translation((0.0, 0.0, -FOOT)))
    for part in (x32,):
        for p in part.data.polygons:
            p.use_smooth = True
        part.data.set_sharp_from_angle(angle=math.radians(35))
    flaps = {name: flap(m, side) for name, side in (("flap_front", -1), ("flap_back", 1))}
    cart = cartridge(m)

    root = bpy.data.objects.new("sega32x_root", None)
    scene.collection.objects.link(root)
    md.parent = root
    sx, sy = L.ON_MEGA_DRIVE["slot"]
    x32.parent = md
    x32.location = (sx, sy, L.ON_MEGA_DRIVE["plug_bottom"])
    for name, (part, hinge) in flaps.items():
        part.name = part.data.name = name
        part.parent = x32
        part.location = hinge - Vector((0.0, 0.0, FOOT))
    cart.parent = x32
    cart.location = (L.ISLAND["at"][0], L.ISLAND["at"][1], L.TOP + L.ISLAND["height"] - L.CART["seat"] - FOOT)
    nodes = {"sega32x": x32, "cartridge": cart, **{name: part for name, (part, _) in flaps.items()}}

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    place = Matrix.Translation(x32.location)
    points = [tilt @ v.co for v in md.data.vertices] + [tilt @ place @ v.co for v in x32.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [md, x32, cart] + [part for part, _ in flaps.values()]
    print(f"Sega 32X: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(md.data)} the Mega Drive, "
          f"{triangles(x32.data)} the 32X, {triangles(cart.data)} the cartridge), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out_path, animations=True)


if __name__ == "__main__":
    main()
