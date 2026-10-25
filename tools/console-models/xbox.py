"""The console theme's Xbox system model (godot/themes/console/models/systems/xbox.glb): the original Xbox and its
Controller S.

Built in Blender from the real console's proportions (xbox_layout.py has the measurements, taken from photographs). The
body is a big box, its edges rounded; the two side wedges between the X's arms are cut out of its top and filled with
fins stepping down to its sides; the jewel's ring is cut into the middle of its top and the jewel stands in it; the
middle section of its front stands proud, the tray's bay cut into it. The tray is its front and the platform behind it,
the DVD's well in its top; the eject and power buttons stand under it. The Controller S is its outline lofted up, its
edges rounded, the stick housings, the d-pad and the buttons on it. The printing is one texture drawn by
xbox_print.py: the console's top and front, the controller's top (planar-mapped onto their faces), the DVD's label, and
swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the tray (and on it the DVD, shrunk to nothing), the eject and power buttons, the power button's lit ring
(shrunk to nothing) and the controller; the controller holding its sticks, its d-pad and A, B, X and Y.

The `focused` clip (8 s, looping) plays a disc: power is pressed and its ring lights green; eject, and the tray slides
out; the DVD drops onto it spinning and settles; the tray goes back in; the game is played on the sticks, the d-pad and
the coloured buttons. Then eject again: the tray comes out, the DVD rises and goes, the tray goes back in.

Four materials (case, key, print, dark) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/xbox_print.py artifacts/xbox
    blender -b --factory-startup --python tools/console-models/xbox.py -- artifacts/xbox godot/themes/console/models/systems/xbox.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xbox_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, key=0.4, print=0.4, dark=0.7)
W, D, H = L.WIDTH, L.DEPTH, L.HEIGHT
PAD_W = 2 * max(x for x, _ in L.PAD_RIGHT)
PAD_D = max(y for _, y in L.PAD_RIGHT)


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], W, D)
FRONT = atlas_uv(L.REGIONS["front"], W, H)
PAD_TOP = atlas_uv(L.REGIONS["pad"], PAD_W, PAD_D)


def top_uv(co):
    return TOP(co.x + W / 2, D - co.y)


def front_uv(co):
    return FRONT(co.x + W / 2, H - co.z)


def pad_uv(co):
    return PAD_TOP(co.x + PAD_W / 2, PAD_D - co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def upright(name, points, z0, z1, mat):
    """A solid from an (x, y) plan, from z0 up to z1."""
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


def facing(name, points, y0, y1, mat):
    """A solid from an (x, z) outline on the front, from y0 back to y1."""
    return solid(name, [[(x, y, z) for x, z in points] for y in (y0, y1)], mat)


def circle(cx, cy, r, n=32):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def wedge(side):
    """A side wedge's plan, anticlockwise: its base along the side, its apex towards the jewel."""
    (y0, y1), apex = L.WEDGE["base"], L.WEDGE["apex"]
    x_side = side * (W / 2 + 5.0)
    points = [(x_side, y0 - 6.0), (x_side, y1 + 6.0), (side * apex, L.JEWEL["at"][1])]
    return points if side < 0 else list(reversed(points))


def fin_top(x):
    """The fins' top at x: from the top at the wedge's apex down to the sides' top edge."""
    t = (abs(x) - L.WEDGE["apex"]) / (W / 2 - L.WEDGE["apex"])
    return H + (L.SIDE_TOP - H) * min(max(t, 0.0), 1.0)


def body(m):
    """The body: its box, the side wedges cut out and finned, the jewel's ring, the proud middle section with the
    tray's bay; its top and front printed."""
    shell = box("xbox", -W / 2, W / 2, 0.0, D, L.FEET, H, m["case"])
    bevel(shell, 3.0, segments=2)
    for side in (-1, 1):
        boolean(shell, upright("wedge", wedge(side), L.WEDGE["floor"], H + 10.0, m["dark"]))
    (jx, jy) = L.JEWEL["at"]
    boolean(shell, upright("ring", circle(jx, jy, L.JEWEL["ring"], 48), H - 2.5, H + 5.0, m["dark"]))
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and c.z > H - 0.5 and name == "case")
    paint(shell, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < 0.5 and name == "case")
    parts = [shell]
    (y0, y1), apex, pitch, fin = L.WEDGE["base"], L.WEDGE["apex"], L.WEDGE["pitch"], L.WEDGE["fin"]
    for side in (-1, 1):
        x = apex + pitch / 2
        while x < W / 2 - 1.0:
            t = (x - apex) / (W / 2 - apex)
            ya, yb = y0 + (L.JEWEL["at"][1] - y0) * (1 - t), y1 - (y1 - L.JEWEL["at"][1]) * (1 - t)
            if yb - ya > 6.0:
                xs = sorted((side * (x - fin / 2), side * (x + fin / 2)))
                part = box("fin", xs[0], xs[1], ya + 2.0, yb - 2.0, L.WEDGE["floor"] - 1.0, fin_top(x), m["case"])
                parts.append(part)
            x += pitch
    (mx0, mx1), proud, top = L.MIDDLE["x"], L.MIDDLE["proud"], L.MIDDLE["top"]
    middle = box("middle", mx0, mx1, -proud, 4.0, L.FEET, top, m["case"])
    bevel(middle, 1.5, segments=2)
    paint(middle, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
    t = L.TRAY
    for part in (shell, middle):                        # the bay through each before they're joined (they overlap)
        boolean(part, box("bay", t["x"][0], t["x"][1], -proud - 5.0, t["depth"], t["z"][0], t["z"][1], m["dark"]))
    parts.append(middle)
    whole = join(parts, "xbox")
    jewel = upright("jewel", circle(jx, jy, L.JEWEL["r"], 48), H - 3.0, H + L.JEWEL["height"], m["print"])
    bevel(jewel, 1.2, segments=2)
    paint(jewel, m["print"], top_uv, lambda c, n, name: n.z > 0.9)
    paint(jewel, m["print"], swatch("green"), lambda c, n, name: n.z <= 0.9)
    return [whole, jewel]


def tray(m):
    """The tray, in its bay: its front (printed like the middle section), the platform behind it with the DVD's
    well."""
    t, proud = L.TRAY, L.MIDDLE["proud"]
    (x0, x1), (z0, z1) = t["x"], t["z"]
    front = box("tray", x0 + 0.5, x1 - 0.5, -proud - 0.5, -proud + 3.0, z0 + 0.5, z1 - 0.5, m["case"])
    bevel(front, 0.8, segments=1)
    paint(front, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
    platform = box("platform", x0 + 1.0, x1 - 1.0, -proud + 3.0, t["depth"] - 4.0, z0 + 1.0, z0 + 6.0, m["dark"])
    wl = L.WELL
    boolean(platform, upright("well", circle(0.0, -proud + wl["y"], wl["r"], 48), z0 + 6.0 - wl["depth"], z0 + 20.0,
                              m["dark"]))
    return join([front, platform], "tray")


def button(name, r, height, m, mat):
    """A round button standing out of the front, its middle at its origin."""
    part = facing(name, circle(0.0, 0.0, r, 28), -height, 1.0, mat)
    bevel(part, 0.8, segments=2)
    return part


def disc(m):
    """The DVD, its middle at its origin, lying flat: a ring, its label on its top."""
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
    part = new_object("disc", bm, m["print"])
    dm = L.DISC["diameter"]
    face = atlas_uv(L.REGIONS["disc"], dm, dm)
    paint(part, m["print"], lambda co: face(co.x + dm / 2, dm / 2 - co.y), lambda c, n_, name: n_.z > 0.9)
    paint(part, m["print"], swatch("silver"), lambda c, n_, name: n_.z <= 0.9)
    return part


# ---- The Controller S ------------------------------------------------------------------------------------------------

def controller(m):
    """The Controller S in its own frame (its grips' ends at y = 0, the table): its body, the jewel, BACK, START,
    black and white, the stick housings; the sticks, the d-pad, A, B, X and Y apart, each its foot's middle at its
    origin."""
    h0, h1 = L.PAD["height"]
    outline = L.PAD_RIGHT + [(-x, y) for x, y in reversed(L.PAD_RIGHT[1:-1])]
    body = solid("controller", [[(x, y, z) for x, y in inset(outline, k)] for k, z in
                                ((2.5, 0.0), (0.0, 4.0), (0.0, h0 - 6.0), (2.6, h0 - 1.5), (5.0, h0))], m["case"])
    for v in body.data.vertices:                             # its top rising to the far edge
        if v.co.z > 1.0:
            v.co.z += (h1 - h0) * v.co.y / PAD_D * (v.co.z / h0)
    for p in body.data.polygons:
        p.use_smooth = True
    paint(body, m["print"], pad_uv, lambda c, n, name: n.z > 0.95)
    parts = [body]

    def surface(y):
        return h0 + (h1 - h0) * y / PAD_D

    def nub(name, at, r, height, mat, n=24, side=None):
        """A round button or the jewel, its top printed, its side (when it's printed) a swatch's colour."""
        x, y = at
        part = upright(name, circle(x, y, r, n), surface(y) - 2.0, surface(y) + height, mat)
        bevel(part, min(1.0, r * 0.3), segments=2)
        paint(part, m["print"], pad_uv, lambda c, n_, _name: n_.z > 0.95)
        if side:
            paint(part, m["print"], swatch(side), lambda c, n_, _name: n_.z <= 0.95)
        return part
    parts.append(nub("jewel", L.CENTRE["at"], L.CENTRE["r"], 1.6, m["print"], 32, "dark"))
    for name in ("white", "black"):
        parts.append(nub(name, L.BLACK_WHITE[name], L.BLACK_WHITE["r"], L.BLACK_WHITE["height"], m["print"], 24,
                         name))
    for name in ("back", "start"):
        parts.append(nub(name, L.BACK_START[name], L.BACK_START["r"], 1.4, m["key"], 16))
    for stick in (L.LEFT_STICK, L.RIGHT_STICK):
        x, y = stick["at"]
        housing = upright("housing", circle(x, y, stick["r"][0], 32), surface(y) - 2.0, surface(y) + 3.0, m["key"])
        bevel(housing, 1.4, segments=2)
        boolean(housing, upright("hole", circle(x, y, stick["r"][0] - 3.0, 28), surface(y), surface(y) + 6.0, m["key"]))
        parts.append(housing)
    shell = join(parts, "controller")

    moving = {}
    for name, stick in (("left_stick", L.LEFT_STICK), ("right_stick", L.RIGHT_STICK)):
        r = stick["r"][1]
        shaft = upright("shaft", circle(0.0, 0.0, 5.0, 20), -2.0, stick["height"] - 3.0, m["key"])
        cap = solid("cap", [[(x, y, z) for x, y in circle(0.0, 0.0, r * k, 32)] for k, z in
                            ((0.85, stick["height"] - 4.0), (1.0, stick["height"] - 2.6), (1.0, stick["height"] - 0.6),
                             (0.8, stick["height"]))], m["key"])
        moving[name] = (join([shaft, cap], name), Vector((*stick["at"], surface(stick["at"][1]))))
    (dx, dy), size, arm = L.DPAD["at"], L.DPAD["size"], L.DPAD["arm"]
    s, a = size / 2, arm / 2
    cross = [(a, s), (-a, s), (-a, a), (-s, a), (-s, -a), (-a, -a), (-a, -s), (a, -s), (a, -a), (s, -a), (s, a), (a, a)]
    dpad = upright("dpad", cross, -2.0, L.DPAD["height"], m["key"])
    bevel(dpad, 1.0, segments=2)
    moving["dpad"] = (dpad, Vector((dx, dy, surface(dy))))
    (fx, fy), sp = L.FACE["at"], L.FACE["spacing"]
    for name, (ddx, ddy) in (("y", (0, 1)), ("x", (-1, 0)), ("b", (1, 0)), ("a", (0, -1))):
        bx, by = fx + ddx * sp, fy + ddy * sp
        part = upright(name, circle(0.0, 0.0, L.FACE["r"], 24), -2.0, L.FACE["height"], m["print"])
        bevel(part, 1.4, segments=2)
        paint(part, m["print"], lambda co, bx=bx, by=by: pad_uv(Vector((co.x + bx, co.y + by, 0.0))),
              lambda c, n_, _name: n_.z > 0.9)
        paint(part, m["print"], swatch(name), lambda c, n_, _name: n_.z <= 0.9)
        moving[name] = (part, Vector((bx, by, surface(by))))
    return shell, moving


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def slide(f, f0, f1):
    """The tray's way out: out between f0 and f0 + 15, back in from f1 - 16 to f1."""
    return -L.TRAY["travel"] * ease_out(phase(f, f0, f0 + 15)) * (1 - smooth(phase(f, f1 - 16, f1)))


DROP = 80.0


def timeline(f):
    if f < 28 or f >= 214:
        dvd = Pose(scale=HIDDEN)
    elif f < 36:
        dvd = Pose(z=DROP, scale=appear(f, 28, 36))
    elif f < 50:
        dvd = Pose(z=DROP * (1 - ease_in(phase(f, 36, 50))), spin=180.0 * phase(f, 36, 50))
    elif f < 186:
        dvd = Pose(spin=180.0 + 25.0 * math.sin(math.pi * phase(f, 50, 56)))
    else:
        dvd = Pose(z=DROP * ease_out(phase(f, 196, 206)), spin=180.0 + 720.0 * phase(f, 186, 214),
                   scale=max(HIDDEN, 1 - ease_in(phase(f, 204, 214))))
    t = phase(f, 90, 176)
    k = math.sin(math.pi * t)
    return {"tray": Pose(y=slide(f, 18, 76) if f < 150 else slide(f, 180, 226)), "disc": dvd,
            "eject": Pose(y=1.6 * max(tap(f, 14), tap(f, 176))), "power": Pose(y=1.4 * tap(f, 4)),
            "power_light": Pose() if f >= 8 else Pose(scale=HIDDEN),
            "left_stick": Pose(pitch=16.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=16.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "right_stick": Pose(roll=14.0 * k * math.sin(2 * math.pi * 2.5 * t)),
            "dpad": Pose(pitch=5.0 * k * math.sin(2 * math.pi * 1.5 * t)),
            "a": Pose(z=-1.8 * max(tap(f, f0) for f0 in (96, 116, 136, 160))),
            "b": Pose(z=-1.8 * max(tap(f, f0) for f0 in (106, 146))),
            "x": Pose(z=-1.8 * tap(f, 126)), "y": Pose(z=-1.8 * tap(f, 168))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "xbox_print.png"))
    colours = dict(L.COLOURS, dark="#08080A")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join(body(m), "xbox")
    drawer = tray(m)
    dvd = disc(m)
    eject = painted(button("eject", L.EJECT["r"], L.EJECT["height"], m, m["print"]), m, "silver")
    power = button("power", L.POWER["r"], L.POWER["height"], m, m["key"])
    ring = facing("power_light", [(x, z) for x, z in circle(0.0, 0.0, L.POWER["ring"], 28)], -0.4, 0.2, m["print"])
    boolean(ring, facing("hole", circle(0.0, 0.0, L.POWER["r"] + 0.2, 28), -5.0, 5.0, m["print"]))
    painted(ring, m, "green_lit")
    pad, moving = controller(m)
    for obj in [whole, drawer, dvd, eject, power, pad] + [p for p, _ in moving.values()]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("xbox_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    proud = L.MIDDLE["proud"]
    drawer.parent = whole
    dvd.parent = drawer
    dvd.location = (0.0, -proud + L.WELL["y"], L.TRAY["z"][0] + 6.0 - L.WELL["depth"] + L.DISC["thickness"] / 2 + 0.1)
    for part, (x, z) in ((eject, L.EJECT["at"]), (power, L.POWER["at"]), (ring, L.POWER["at"])):
        part.parent = whole
        part.location = (x, -proud, z)
    (px, py), turn = L.PAD["at"], math.radians(L.PAD["turn"])
    pad.parent = whole
    pad.location = (px, py, 0.0)
    pad.rotation_euler = (0.0, 0.0, turn)
    for part, where in moving.values():
        part.parent = pad
        part.location = where
    nodes = {"tray": drawer, "disc": dvd, "eject": eject, "power": power, "power_light": ring,
             **{n: p for n, (p, _) in moving.items()}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(turn, 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in pad.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, drawer, dvd, eject, power, ring, pad] + [p for p, _ in moving.values()]
    print(f"Xbox: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
