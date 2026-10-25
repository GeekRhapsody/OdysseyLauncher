"""The console theme's Virtual Boy system model (godot/themes/console/models/systems/virtualboy.glb): the Virtual Boy
on its stand, its controller standing on its grips beside it.

Built in Blender (virtualboy_layout.py has the measurements, taken from photographs). The unit is lofted through
cross-sections along its width (its front sloping back, the top, the back, the underside), each drawn in round the
plan's corners and the ends' edges, the red shell's lower edge rising over the middle of the front; the black ears, the
raised strip and its grey slider, and the rubber eyecup round the two screens are their own parts. The stand: the head,
its knob, the joint with the Nintendo plate, two legs to their wire feet. The controller: its outline (two lobes and
the bar between them) given its depth, the D-pads, SELECT, START, B, A, the battery pack, and the grips swept round
their curves; its cord runs to the unit's underside. The printing is one texture (virtualboy_print.py's).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the stand and the
controller; the stand holding the unit (its origin on the stand's head, where it turns); the unit holding its screens
(the title and two frames of the game for each eye; those not lit wait behind the window's floor, so a swap never
shows a screen shrinking); the controller holding its D-pads and buttons.

The `focused` clip (8 s, looping): the unit turns round on its stand to look at the viewer, Odyssey's title lights in
its eyes and the game plays (the ship over a grid running into the distance) while the D-pad rocks and A fires; then
it turns back.

Four materials (body, screen, grey, rubber) and one 1024² texture, within the system model budget. Run from the repo
root:

    python tools/console-models/virtualboy_print.py artifacts/virtualboy
    blender -b --factory-startup --python tools/console-models/virtualboy.py -- artifacts/virtualboy godot/themes/console/models/systems/virtualboy.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import virtualboy_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import Pose, key, phase, smooth  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -30.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 14.0    # degrees about the horizontal: the top tips up towards the viewer
RINGS = 41
ROUGHNESS = dict(body=0.35, screen=0.3, grey=0.4, rubber=0.85)


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def coloured(obj, m, name):
    paint(obj, m["body"], swatch(name), lambda c, n, kind: True)


def arc(cy, cz, r, a0, a1, n):
    angles = [math.radians(a0 + (a1 - a0) * k / n) for k in range(n)]
    return [(cy + r * math.cos(a), cz + r * math.sin(a)) for a in angles]


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def tube(name, points, radius, mat, sides=10, caps=True):
    """A tube through points (a list of Vectors), radius a number or a function of 0..1 along it."""
    bm = bmesh.new()
    rings = []
    normal = Vector((0.0, 0.0, 1.0)) if abs((points[-1] - points[0]).normalized().z) < 0.9 else Vector((1.0, 0.0, 0.0))
    n = len(points) - 1
    for k, p in enumerate(points):
        tangent = (points[min(k + 1, n)] - points[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        r = radius(k / n) if callable(radius) else radius
        around = [2 * math.pi * j / sides for j in range(sides)]
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * r) for a in around])
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            bm.faces.new([a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]])
    if caps:
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def bezier(points, n):
    p0, p1, p2, p3 = (Vector(p) for p in points)
    out = []
    for k in range(n + 1):
        t = k / n
        out.append(p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3)
    return out


# ---- The unit --------------------------------------------------------------------------------------------------------

def edge_height(x):
    """The red shell's lower edge on the front: low at the sides, rising over the middle."""
    e = L.EDGE
    return e["sides"] + (e["middle"] - e["sides"]) * (1 - smooth(phase(abs(x), e["flat"], e["slope"])))


def section(x):
    """The unit's cross-section at x: (y, z) points from the front's foot up the front, over the top, down the back and
    along the underside; and each point's colour for the faces from it to the next."""
    (fy, fz), (ty, tz) = L.FRONT["foot"], L.FRONT["top"]
    h, d = L.HEIGHT, L.DEPTH
    ze = edge_height(x)
    ye = fy + (ty - fy) * (ze - fz) / (tz - fz)
    parts = [("black", [(fy, fz), (fy + (ye - fy) * 0.5, fz + (ze - fz) * 0.5)]),
             ("red", [(ye, ze), (fy + (ty - fy) * 0.62, fz + (tz - fz) * 0.62), (ty, tz)]),
             ("red", arc(ty + 10.0 - 10.0 * math.cos(math.radians(10)), h - 10.0, 10.0, 170.0, 90.0, 4)),
             ("red", [(30.0, h), (60.0, h), (90.0, h)] + arc(d - 7.0, h - 7.0, 7.0, 90.0, 0.0, 3)),
             ("red", [(d, h - 7.0), (d, (h - 7.0 + L.BACK_RED) / 2)]),
             ("black", [(d, L.BACK_RED), (d, 30.0)] + arc(d - 6.0, 6.0, 6.0, 0.0, -90.0, 3)),
             ("black", [(d - 6.0, 0.0), (60.0, 0.0), (10.0, 0.0)])]
    points = [p for _, pts in parts for p in pts]
    kinds = [kind for kind, pts in parts for _ in pts]
    return points, kinds


def drawn_in(r, x):
    e = min(r, max(0.0, abs(x) - (L.WIDTH / 2 - r)))
    return r - math.sqrt(r * r - e * e)


def body(m):
    """The red shell and the black below it, lofted along x."""
    rings, kinds = [], None
    for k in range(RINGS):
        x = L.WIDTH / 2 * math.sin(math.pi / 2 * (2 * k / (RINGS - 1) - 1))
        points, kinds = section(x)
        dy, dt, db = (drawn_in(L.ROUND[name], x) for name in ("plan", "top", "bottom"))
        mid = L.DEPTH / 2
        rings.append([(x, mid + (y - mid) * (mid - dy) / mid, db + z * (L.HEIGHT - dt - db) / L.HEIGHT)
                      for y, z in points])
    bm = bmesh.new()
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(verts, verts[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]]).material_index = 0 if kinds[i] == "red" else 1
    ends = [bm.faces.new(verts[0]), bm.faces.new(list(reversed(verts[-1])))]
    for face in ends:
        face.material_index = 1
    bmesh.ops.triangulate(bm, faces=ends, quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    shell = new_object("virtualboy", bm, m["body"])
    shell.data.materials.append(m["grey"])           # a placeholder slot, so the black faces can be told apart
    return shell


def unit(m):
    """The unit in its own frame: the shell, the windows for the screens, the ears, the strip and its slider, the
    eyecup; printed and coloured."""
    shell = body(m)
    sx, (sw, sh), sz, sunk = L.SCREEN["x"], L.SCREEN["size"], L.SCREEN["z"], L.SCREEN["sunk"]
    for side in (-1, 1):
        boolean(shell, box("window", side * sx - sw / 2 - 1.0, side * sx + sw / 2 + 1.0, L.DEPTH - sunk - 2.0,
                           L.DEPTH + 5.0, sz - sh / 2 - 1.0, sz + sh / 2 + 1.0, m["rubber"]))
    paint(shell, m["body"], swatch("red"), lambda c, n, kind: kind == "body")
    paint(shell, m["body"], swatch("black"), lambda c, n, kind: kind == "grey")
    paint(shell, m["body"], swatch("dark"), lambda c, n, kind: kind == "rubber")
    x0, x1, z0, z1 = L.LOGO["area"]
    logo = atlas_uv(L.REGIONS["front"], x1 - x0, z1 - z0)
    (lx0, lx1), (lz0, lz1) = L.LOGO["x"], L.LOGO["z"]
    paint(shell, m["body"], lambda co: logo(co.x - x0, z1 - co.z),
          lambda c, n, kind: n.y < -0.5 and lx0 < c.x < lx1 and lz0 < c.z < lz1)
    shell.data.materials.pop(index=1)                # the placeholder, unused now

    parts = [shell]
    (ex0, ex1), (ey0, ey1), (ez0, ez1) = L.EARS["x"], L.EARS["y"], L.EARS["z"]
    for side in (-1, 1):
        ear = box("ear", side * ex0, side * ex1, ey0, ey1, ez0, ez1, m["body"])
        bevel(ear, 3.0, segments=2)
        coloured(ear, m, "black")
        parts.append(ear)
        for k in range(L.EARS["ribs"]):
            z = ez0 + 10.0 + k * (ez1 - ez0 - 20.0) / (L.EARS["ribs"] - 1)
            rib = box("rib", side * (ex1 - 0.5), side * (ex1 + 1.2), ey0 + 12.0, ey1 - 10.0, z - 1.2, z + 1.2,
                      m["body"])
            coloured(rib, m, "black")
            parts.append(rib)
    (stx0, stx1), (sty0, sty1) = L.STRIP["x"], L.STRIP["y"]
    strip = box("strip", stx0, stx1, sty0, sty1, L.HEIGHT - 4.0, L.HEIGHT + L.STRIP["height"], m["body"])
    bevel(strip, 2.0, segments=2)
    coloured(strip, m, "red")
    (slx0, slx1), (sly0, sly1) = L.SLIDER["x"], L.SLIDER["y"]
    top = L.HEIGHT + L.STRIP["height"]
    slider = box("slider", slx0, slx1, sly0, sly1, top - 1.0, top + L.SLIDER["height"], m["grey"])
    bevel(slider, 1.0, segments=1)
    parts += [strip, slider]

    (ow, oh, orr), (iw, ih, ir) = L.EYECUP["outer"], L.EYECUP["inner"]
    cx, cz = L.EYECUP["at"]
    cup = solid("eyecup", [[(x, y, z) for x, z in rounded(cx, cz, ow, oh, orr, 5)]
                           for y in (L.DEPTH - 2.0, L.DEPTH + L.EYECUP["out"])], m["rubber"])
    boolean(cup, solid("hole", [[(x, y, z) for x, z in rounded(cx, cz, iw, ih, ir, 5)]
                                for y in (L.DEPTH - 5.0, L.DEPTH + L.EYECUP["out"] + 5.0)], m["rubber"]))
    nw, nh = L.EYECUP["nose"]
    boolean(cup, box("nose", cx - nw / 2, cx + nw / 2, L.DEPTH - 5.0, L.DEPTH + L.EYECUP["out"] + 5.0,
                     cz - oh / 2 - 5.0, cz - oh / 2 + nh, m["rubber"]))
    bevel(cup, 3.0, segments=2)
    parts.append(cup)
    return join(parts, "virtualboy")


def screens(m):
    """Each eye's three screens (title, game_1, game_2), facing the back from inside its window; and where each goes."""
    sx, (sw, sh), sz, sunk = L.SCREEN["x"], L.SCREEN["size"], L.SCREEN["z"], L.SCREEN["sunk"]
    out = {}
    for side, eye in ((-1, "left"), (1, "right")):
        for name in ("title", "game_1", "game_2"):
            rx, ry, rw, rh = L.REGIONS[name]
            shift = 6.0 / rw if side > 0 else 0.0     # the right eye's picture a little to the left: its depth
            part = curved(f"{eye}_{name}", sw, sh, 0.0,
                          lambda a, b, rx=rx, ry=ry, rw=rw, rh=rh, s=shift: (
                              (rx + min(1.0, a + s) * rw) / L.ATLAS, 1 - (ry + b * rh) / L.ATLAS), m["screen"], 1, 1)
            part.data.transform(Matrix.Rotation(math.pi, 4, "Z"))     # it faces the back
            out[f"{eye}_{name}"] = (part, Vector((side * sx, L.DEPTH - sunk - 2.0 + 0.4, sz)))   # just off the floor
    return out


# ---- The stand and the controller ------------------------------------------------------------------------------------

def stand(m):
    """The stand in the console's frame: the head the unit sits on, the knob, the joint and its plate, the legs and
    their feet."""
    (hw, hd, hh), (hx, hy), top = L.HEAD["size"], L.HEAD["at"], L.HEAD["top"]
    head = box("stand", hx - hw / 2, hx + hw / 2, hy - hd / 2, hy + hd / 2, top - hh, top, m["body"])
    bevel(head, 2.0, segments=2)
    (kx, kz), kr, kl = L.KNOB["at"], L.KNOB["r"], L.KNOB["length"]
    knob = solid("knob", [[(x, hy + kr * math.cos(a), kz + kr * math.sin(a))
                           for a in [2 * math.pi * j / 16 for j in range(16)]] for x in (hw / 2 - 1.0, hw / 2 + kl)],
                 m["body"])
    bevel(knob, 1.5, segments=1)
    (jw, jd, jh), jz = L.JOINT["size"], L.JOINT["z"]
    neck = box("neck", -8.0, 8.0, hy - 8.0, hy + 8.0, jz + jh / 2 - 2.0, top - hh + 1.0, m["body"])
    joint = box("joint", -jw / 2, jw / 2, hy - jd / 2, hy + jd / 2, jz - jh / 2, jz + jh / 2, m["body"])
    bevel(joint, 6.0, segments=3)
    parts = [head, knob, neck, joint]
    for part in parts:
        coloured(part, m, "black")
    plate = atlas_uv(L.REGIONS["plate"], jw, jh - 4.0)
    paint(joint, m["body"], lambda co: plate(co.x + jw / 2, jz + jh / 2 - 2.0 - co.z),
          lambda c, n, kind: n.y < -0.9)
    r = L.LEGS["r"]
    for fx, fy in L.LEGS["feet"]:
        hip = Vector((fx * 0.12, hy, jz - jh / 2 + 4.0))
        foot = Vector((fx, fy, r))
        leg = tube("leg", [hip + (foot - hip) * (k / 12) for k in range(13)], r, m["body"], 8)
        tip = Vector((fx + math.copysign(14.0, fx), fy + L.LEGS["tip"], r + 2.0))
        arm = tube("arm", [foot + (tip - foot) * (k / 8) for k in range(9)], r, m["body"], 8)
        cap = tube("cap", [tip, tip + (tip - foot).normalized() * 16.0], r + 2.4, m["rubber"], 10)
        for part in (leg, arm):
            coloured(part, m, "black")
        parts += [leg, arm, cap]
    return join(parts, "stand")


def face_outline():
    """The controller's face: the two lobes and the bar between them, anticlockwise."""
    lx, r = L.LOBES["x"], L.LOBES["r"]
    zb, zt = L.LOBES["bar"]
    top = math.degrees(math.atan2(zt, math.sqrt(r * r - zt * zt)))       # where the bar's edges meet the left lobe
    bottom = math.degrees(math.atan2(zb, math.sqrt(r * r - zb * zb)))

    def lobe(cx, a0, a1):
        return [(cx + r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
                for a in [a0 + (a1 - a0) * k / 28 for k in range(29)]]
    return lobe(-lx, top, 360.0 + bottom) + lobe(lx, 180.0 - bottom, 540.0 - top)


def cross(s, a):
    h, w = s / 2, a / 2
    return [(w, -h), (w, -w), (h, -w), (h, w), (w, w), (w, h), (-w, h), (-w, w), (-h, w), (-h, -w), (-w, -w), (-w, -h)]


def controller(m):
    """The controller in its own frame (x across, y back from its face, z up from its face's middle): its body, the
    pack and the grips; its D-pads and buttons, each with where its node goes."""
    depth = L.LOBES["depth"]
    shape = face_outline()
    shell = solid("controller", [[(x, y, z) for x, z in shape] for y in (0.0, depth)], m["body"])
    bevel(shell, 3.0, segments=2)
    coloured(shell, m, "black")
    face = atlas_uv(L.REGIONS["face"], 160.0, 64.0)
    paint(shell, m["body"], lambda co: face(co.x + 80.0, 32.0 - co.z), lambda c, n, kind: n.y < -0.9)
    (px0, px1), (py0, py1), (pz0, pz1) = L.PACK["x"], L.PACK["y"], L.PACK["z"]
    pack = box("pack", px0, px1, py0, py1, pz0, pz1, m["body"])
    bevel(pack, 2.0, segments=2)
    coloured(pack, m, "black")
    label = atlas_uv(L.REGIONS["pack"], px1 - px0, pz1 - pz0)
    paint(pack, m["body"], lambda co: label(co.x - px0, pz1 - co.z), lambda c, n, kind: n.y < -0.9)
    parts = [shell, pack]
    r0, r1 = L.GRIP["r"]
    for side in (-1, 1):
        path = bezier([(side * x, y, z) for x, y, z in L.GRIP["path"]], 18)
        grip = tube("grip", path, lambda t: r0 + (r1 - r0) * t, m["body"], 14)
        coloured(grip, m, "black")
        parts.append(grip)
    body = join(parts, "controller")
    nodes = {}
    d = L.DPADS
    for side, name in ((-1, "dpad_left"), (1, "dpad_right")):
        pad = solid(name, [[(x, y, z) for x, z in cross(d["size"], d["arm"])] for y in (-d["height"], 1.0)], m["body"])
        bevel(pad, 0.6, segments=1)
        coloured(pad, m, "black")
        nodes[name] = (pad, Vector((side * d["x"], 0.0, d["z"])))
    for k, (x, z) in enumerate(L.SELECT_START["at"]):
        b = solid(("select", "start")[k], [[(px, y, pz) for px, pz in circle(0.0, 0.0, L.SELECT_START["r"], 18)]
                                            for y in (-L.SELECT_START["height"], 1.0)], m["grey"])
        bevel(b, 0.8, segments=1)
        nodes[("select", "start")[k]] = (b, Vector((x, 0.0, z)))
    for k, (x, z) in enumerate(L.B_A["at"]):
        b = solid(("b", "a")[k], [[(px, y, pz) for px, pz in circle(0.0, 0.0, L.B_A["r"], 18)]
                                  for y in (-L.B_A["height"], 1.0)], m["body"])
        bevel(b, 1.0, segments=1)
        coloured(b, m, "red")
        nodes[("b", "a")[k]] = (b, Vector((x, 0.0, z)))
    return body, nodes


def pad_frame():
    """The controller's frame to the console's: standing on its grips' ends, leaning back, turned."""
    (x, y), turn, lean = L.PAD["at"], L.PAD["turn"], L.PAD["lean"]
    feet = -L.GRIP["path"][-1][2] + L.GRIP["r"][1]
    return (Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
            @ Matrix.Rotation(math.radians(-lean), 4, "X") @ Matrix.Translation((0.0, 0.0, feet)))


# ---- The focused clip ------------------------------------------------------------------------------------------------

SCREENS = ("title", "game_1", "game_2")
SINK = 1.0                # how far back a screen that isn't lit waits: behind its window's floor


def lit(f):
    if f < 56 or f >= 176:
        return "title"
    return "game_1" if ((f - 56) // 6) % 2 == 0 else "game_2"


def timeline(f):
    turn = 180.0 * smooth(phase(f, 16, 46)) * (1 - smooth(phase(f, 176, 206)))
    nod = 6.0 * math.sin(math.pi * phase(f, 44, 58)) - 6.0 * math.sin(math.pi * phase(f, 204, 216))
    poses = {"virtualboy": Pose(spin=turn, pitch=nod)}
    for eye in ("left", "right"):
        for name in SCREENS:
            poses[f"{eye}_{name}"] = Pose() if name == lit(f) else Pose(y=-SINK)
    t = phase(f, 60, 170)
    k = math.sin(math.pi * t)
    poses["dpad_left"] = Pose(roll=8.0 * k * math.sin(2 * math.pi * 4.0 * t),
                              pitch=8.0 * k * math.cos(2 * math.pi * 3.0 * t))
    poses["dpad_right"] = Pose()
    press = lambda f0: smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 5, f0 + 9)))   # noqa: E731
    poses["a"] = Pose(y=2.0 * max(press(f0) for f0 in (64, 88, 112, 136, 160)))
    poses["b"] = Pose(y=2.0 * max(press(f0) for f0 in (100, 148)))
    poses["select"] = Pose()
    poses["start"] = Pose(y=1.6 * press(50))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "virtualboy_print.png"))
    m = {"body": material("body", L.COLOURS["print"], ROUGHNESS["body"], atlas),
         "screen": material("screen", L.COLOURS["print"], ROUGHNESS["screen"], atlas),
         "grey": material("grey", L.COLOURS["grey"], ROUGHNESS["grey"]),
         "rubber": material("rubber", L.COLOURS["rubber"], ROUGHNESS["rubber"])}

    head = Vector((L.HEAD["at"][0], L.HEAD["at"][1], L.HEAD["top"]))
    box_ = unit(m)
    box_.data.transform(Matrix.Translation((-head.x, -head.y, 0.0)))   # its origin over the head, where it turns
    eye_nodes = screens(m)
    holder = stand(m)
    pad_body, pad_nodes = controller(m)
    to_world = pad_frame()
    pad_body.data.transform(to_world)
    cord_start = to_world @ Vector((0.0, 12.0, L.LOBES["bar"][1] - 2.0))
    cord_end = Vector((70.0, 96.0, L.HEAD["top"] + 2.0))
    cord = tube("cord", bezier([cord_start, cord_start + Vector((-10.0, 30.0, 60.0)),
                                cord_end + Vector((10.0, -20.0, -90.0)), cord_end], 30), 2.0, m["body"], 8)
    coloured(cord, m, "black")
    fixed = join([holder, pad_body, cord], "stand")
    for obj in [fixed, box_] + [p for p, _ in list(eye_nodes.values()) + list(pad_nodes.values())]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("virtualboy_root", None)
    scene.collection.objects.link(root)
    fixed.parent = root
    box_.parent = fixed
    box_.location = head
    nodes = {"virtualboy": box_}
    for name, (part, where) in eye_nodes.items():
        part.parent = box_
        part.location = where - Vector((head.x, head.y, 0.0))
        nodes[name] = part
    turn = Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z") @ Matrix.Rotation(math.radians(-L.PAD["lean"]), 4, "X")
    for name, (part, where) in pad_nodes.items():
        part.data.transform(turn)
        part.parent = fixed
        part.location = to_world @ where
        nodes[name] = part

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in fixed.data.vertices] + [tilt @ (v.co + head) for v in box_.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [fixed] + list(nodes.values())
    print(f"Virtual Boy: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(box_.data)} the unit), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
