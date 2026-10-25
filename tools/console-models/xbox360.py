"""The console theme's Xbox 360 system model (godot/themes/console/models/systems/xbox360.glb): the first Xbox 360 in
white, lying flat, its controller resting on its top.

Built in Blender (xbox360_layout.py has the measurements, taken from photographs). The shell is lofted along its width
through rounded cross-sections, its top and underside drawn in towards the middle and its ends rounded; the grey grilles
bulge from its ends, the hard drive stands on the left one, the tray's bay is cut into the front. The controller is its
traced outline given its depth, its edges rounded, white above and grey below, the sticks' housings, the d-pad's well
and the Guide button on it. The printing is one texture (xbox360_print.py's), projected from above onto the tops, from
in front onto the faceplate, and from the side onto the grilles.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the tray (and on it the disc, shrunk to nothing), eject, power, the Ring of Light's four quadrants lit (shrunk
to nothing while it's off), and the controller's sticks, d-pad, A, B, X, Y and its ring's first quadrant lit.

The `focused` clip (8 s, looping): power is pressed and the Ring of Light comes on quadrant by quadrant, and the
controller's first; eject, and the tray slides out; the disc drops onto it, spinning, and the tray takes it in; the game
is played on the sticks, the d-pad, A, B, X and Y; then eject again: the tray comes out, the disc rises and goes, the
tray goes back in and the lights go off.

Three materials (body, gloss, disc) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/xbox360_print.py artifacts/xbox360
    blender -b --factory-startup --python tools/console-models/xbox360.py -- artifacts/xbox360 godot/themes/console/models/systems/xbox360.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xbox360_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
RINGS = 41
ROUGHNESS = dict(body=0.45, gloss=0.2, disc=0.2)
PAD_W, PAD_D = 153.0, 92.0


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT)
PAD_TOP = atlas_uv(L.REGIONS["pad"], PAD_W, PAD_D)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def upright(name, points, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


def facing(name, points, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1."""
    return solid(name, [[(x, y, z) for x, z in points] for y in (y0, y1)], mat)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


# ---- The console -----------------------------------------------------------------------------------------------------

def inhale(x):
    """How far the top and the underside are drawn in at x: most at the middle."""
    return L.INHALE * (1 - (2 * x / L.WIDTH) ** 2)


def drawn_in(r, x, half):
    e = min(r, max(0.0, abs(x) - (half - r)))
    return r - math.sqrt(r * r - e * e)


def shell(m):
    """The shell lofted along x through rounded (y, z) sections, drawn in round the ends and in at the middle."""
    half = L.WIDTH / 2
    rings = []
    for k in range(RINGS):
        x = half * math.sin(math.pi / 2 * (2 * k / (RINGS - 1) - 1))
        d = drawn_in(L.ROUND["ends"], x, half)
        dp = drawn_in(L.ROUND["plan"], x, half)
        z0, z1 = inhale(x) + d, L.HEIGHT - inhale(x) - d
        y0, y1 = dp, L.DEPTH - dp
        r = min(L.ROUND["front"], (z1 - z0) / 2 - 0.1)
        rings.append([(x, y, z) for y, z in rounded((y0 + y1) / 2, (z0 + z1) / 2, y1 - y0, z1 - z0, r, 4)])
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
    return new_object("xbox360", bm, m["body"])


def grille(m, side):
    """An end's grille: the end's section set in, bulging out."""
    g = L.GRILLE
    half = L.WIDTH / 2
    z0, z1 = inhale(half) + g["inset"] + 2.0, L.HEIGHT - inhale(half) - g["inset"] - 2.0
    y0, y1 = g["inset"] + 4.0, L.DEPTH - g["inset"] - 4.0

    def ring(k, x):
        return [(x, y, z) for y, z in rounded((y0 + y1) / 2, (z0 + z1) / 2, y1 - y0 - 2 * k, z1 - z0 - 2 * k,
                                              max(1.0, 10.0 - k), 4)]
    part = solid("grille", [ring(0.0, side * (half - 10.0)), ring(0.0, side * (half - 2.0)),
                            ring(3.0, side * (half + g["bulge"] * 0.8)), ring(9.0, side * (half + g["bulge"]))],
                 m["body"])
    dots = atlas_uv(L.REGIONS["grille"], L.DEPTH, L.HEIGHT)
    colour(part, m["body"], "grey")
    paint(part, m["body"], lambda co: dots(co.y, L.HEIGHT - co.z), lambda c, n, kind: abs(n.x) > 0.6)
    return part


def hard_drive(m):
    """The hard drive on the left end: a rounded grey box, its chrome sides."""
    h = L.HDD
    x0, x1 = -L.WIDTH / 2 - h["x"], -L.WIDTH / 2 + 1.0
    (y0, y1), (z0, z1) = h["y"], h["z"]
    part = solid("hdd", [[(x, y, z) for y, z in rounded((y0 + y1) / 2, (z0 + z1) / 2, y1 - y0, z1 - z0, h["r"], 5)]
                         for x in (x1, x0 + 3.0)]
                 + [[(x0, y, z) for y, z in rounded((y0 + y1) / 2, (z0 + z1) / 2, y1 - y0 - 6.0, z1 - z0 - 6.0,
                                                     h["r"] - 3.0, 5)]], m["gloss"])
    colour(part, m["gloss"], "chrome")
    paint(part, m["gloss"], swatch("hdd"), lambda c, n, kind: n.x < -0.8)
    return part


def body(m):
    """The shell (its faceplate, the tray's bay cut in), the grilles, the hard drive, the feet; printed."""
    part = shell(m)
    (tx0, tx1), (tz0, tz1) = L.TRAY["x"], L.TRAY["z"]
    boolean(part, box("bay", tx0 - 0.6, tx1 + 0.6, -10.0, L.TRAY["depth"], tz0 - 0.6, tz1 + 0.6, m["body"]))
    colour(part, m["body"], "body")
    paint(part, m["body"], lambda co: TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y), lambda c, n, kind: n.z > 0.8)
    paint(part, m["body"], swatch("plate"), lambda c, n, kind: c.y < L.FACEPLATE and n.z <= 0.8)
    paint(part, m["body"], lambda co: FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z),
          lambda c, n, kind: n.y < -0.9 and c.y < 1.0)
    paint(part, m["body"], swatch("dark"),
          lambda c, n, kind: tx0 - 1.0 < c.x < tx1 + 1.0 and tz0 - 1.0 < c.z < tz1 + 1.0
          and 0.5 < c.y < L.TRAY["depth"] + 1.0)
    feet = [colour(upright("foot", circle(x, y, 8.0, 12), -0.5, inhale(x) + 2.0, m["body"]), m["body"], "grey")
            for x in (-128.0, 128.0) for y in (40.0, 218.0)]
    return join([part, grille(m, -1), grille(m, 1), hard_drive(m)] + feet, "xbox360")


def tray(m):
    """The tray: its front (the silver strip) and the platform behind it with the disc's well; its origin at its
    front's middle."""
    (tx0, tx1), (tz0, tz1) = L.TRAY["x"], L.TRAY["z"]
    cx, cz = (tx0 + tx1) / 2, (tz0 + tz1) / 2
    front = facing("tray", rounded(0.0, 0.0, tx1 - tx0, tz1 - tz0, (tz1 - tz0) / 2 - 0.1, 5), -0.6, 4.0, m["gloss"])
    paint(front, m["gloss"], swatch("silver"), lambda c, n, kind: True)
    paint(front, m["gloss"], lambda co: FRONT(co.x + cx + L.WIDTH / 2, L.HEIGHT - (co.z + cz)),
          lambda c, n, kind: n.y < -0.9)
    platform = box("platform", -(tx1 - tx0) / 2 + 1.0, (tx1 - tx0) / 2 - 1.0, 4.0, 4.0 + 128.0, -2.0, 2.0, m["body"])
    boolean(platform, upright("well", circle(0.0, L.WELL["y"], L.WELL["r"], 48), 2.0 - L.WELL["depth"], 5.0, m["body"]))
    colour(platform, m["body"], "dark")
    return join([front, platform], "tray"), Vector((cx, 0.0, cz))


def disc(m):
    r, t = L.DISC["diameter"] / 2, L.DISC["thickness"]
    part = upright("disc", circle(0.0, 0.0, r, 48), -t / 2, t / 2, m["disc"])
    label = atlas_uv(L.REGIONS["disc"], 2 * r, 2 * r)
    colour(part, m["disc"], "silver")
    paint(part, m["disc"], lambda co: label(co.x + r, r - co.y), lambda c, n, kind: n.z > 0.9)
    return part


def quadrant(m, k):
    """One of the Ring of Light's quadrants, lit: a quarter of the ring, on the faceplate."""
    (r0, r1) = L.POWER["ring"]
    a0 = math.radians(135 - 90 * k - 4)               # a gap of 8 degrees between the quadrants
    a1 = math.radians(135 - 90 * k - 86)
    steps = [a0 + (a1 - a0) * j / 8 for j in range(9)]
    outline = [(r1 * math.cos(a), r1 * math.sin(a)) for a in steps] + \
              [(r0 * math.cos(a), r0 * math.sin(a)) for a in reversed(steps)]
    part = facing(f"ring_{k + 1}", outline, -0.5, 0.2, m["gloss"])
    return colour(part, m["gloss"], "green")


# ---- The controller --------------------------------------------------------------------------------------------------

def pad_uv(co):
    return PAD_TOP(co.x + PAD_W / 2, PAD_D - co.y)


def controller(m):
    """The controller in its own frame (its grips' ends at y = 0, the table at z = 0): its body (white above, grey
    below), the stick housings, the d-pad's well, the Guide button, BACK and START; the moving parts apart, each its
    foot's middle at its origin."""
    h, grey = L.PAD["height"], L.PAD["grey"]
    outline = L.PAD_RIGHT[:-1] + [(-x, y) for x, y in reversed(L.PAD_RIGHT[1:-1])]
    body_ = solid("controller", [[(x, y, z) for x, y in inset(outline, k)] for k, z in
                                 ((4.0, 0.0), (0.0, 6.0), (0.0, h - 7.0), (2.6, h - 1.4), (4.2, h))], m["body"])
    colour(body_, m["body"], "plate")
    paint(body_, m["body"], swatch("shell"), lambda c, n, kind: c.z < grey)
    paint(body_, m["body"], pad_uv, lambda c, n, kind: n.z > 0.95 and c.z > h - 0.5)
    parts = [body_]
    for name in ("left", "right"):
        hx, hy = L.STICKS[name]
        housing = upright("housing", circle(hx, hy, L.STICKS["housing"], 36), h - 4.0, h + 1.0, m["body"])
        bevel(housing, 1.4, segments=2)
        parts.append(housing)
    gx, gy = L.GUIDE["at"]
    guide = upright("guide", circle(gx, gy, L.GUIDE["r"], 28), h - 1.0, h + 1.8, m["gloss"])
    bevel(guide, 1.0, segments=2)
    sw, sh = L.SMALL["size"]
    smalls = [upright(name, rounded(*L.SMALL[name], sw, sh, sh / 2 - 0.05, 4), h - 1.0, h + 1.0, m["body"])
              for name in ("back", "start")]
    for part in parts[1:] + [guide] + smalls:
        paint(part, part.data.materials[0], swatch("plate"), lambda c, n, kind: True)
        paint(part, part.data.materials[0], pad_uv, lambda c, n, kind: n.z > 0.95)
    shell_ = join(parts + [guide] + smalls, "controller")

    moving = {}
    for name in ("left", "right"):
        r1, (z0, z1) = L.STICKS["cap"], L.STICKS["height"]
        shaft = upright("shaft", circle(0.0, 0.0, 4.5, 16), -2.0, z0, m["body"])
        cap = solid("cap", [[(x, y, z) for x, y in circle(0.0, 0.0, r1 * k, 28)] for k, z in
                            ((0.85, z0 - 0.5), (1.0, z0 + 0.8), (1.0, z1 - 1.6), (0.9, z1))], m["body"])
        stick = colour(join([shaft, cap], name + "_stick"), m["body"], "shell")
        moving[name + "_stick"] = (stick, Vector((*L.STICKS[name], h + 1.0)))
    d = L.DPAD
    dpad = upright("dpad", circle(0.0, 0.0, d["r"], 32), -1.0, d["height"], m["body"])
    bevel(dpad, 1.2, segments=2)
    moving["dpad"] = (colour(dpad, m["body"], "shell"), Vector((*d["at"], h)))
    for name in ("a", "b", "x", "y"):
        b = upright(name, circle(0.0, 0.0, L.FACE["r"], 24), -1.0, L.FACE["height"], m["gloss"])
        bevel(b, 1.2, segments=2)
        x, y = L.FACE[name]
        colour(b, m["gloss"], "plate")
        paint(b, m["gloss"], lambda co, x=x, y=y: pad_uv(Vector((co.x + x, co.y + y, co.z))),
              lambda c, n, kind: n.z > 0.95)
        moving[name] = (b, Vector((x, y, h)))
    r0, r1 = L.GUIDE["r"] + 0.2, L.GUIDE["ring"]
    steps = [math.radians(180 - 90 * j / 8 - 4) for j in range(9)]       # the top-left quadrant: player one
    lit = upright("pad_light", [(r1 * math.cos(a), r1 * math.sin(a)) for a in steps]
                  + [(r0 * math.cos(a), r0 * math.sin(a)) for a in reversed(steps)], -0.2, 0.4, m["gloss"])
    moving["pad_light"] = (colour(lit, m["gloss"], "green"), Vector((gx, gy, h)))
    return shell_, moving


def pad_frame():
    """The controller's frame to the console's: lying on the console's top, turned."""
    (x, y), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((x, y, L.HEIGHT - inhale(x) + 0.4)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


# ---- The focused clip ------------------------------------------------------------------------------------------------

DROP = 60.0               # how far above its seat the disc appears


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def slide(f, f0, f1):
    """The tray's way out: out between f0 and f0 + 15, back in from f1 - 16 to f1."""
    return -L.TRAY["travel"] * ease_out(phase(f, f0, f0 + 15)) * (1 - smooth(phase(f, f1 - 16, f1)))


def timeline(f):
    if f < 40 or f >= 214:
        dvd = Pose(scale=HIDDEN)
    elif f < 48:
        dvd = Pose(z=DROP, scale=max(HIDDEN, back_out(phase(f, 40, 47))))
    elif f < 60:
        dvd = Pose(z=DROP * (1 - ease_in(phase(f, 48, 60))), spin=180.0 * phase(f, 48, 60))
    elif f < 186:
        dvd = Pose(spin=180.0 + 25.0 * math.sin(math.pi * phase(f, 60, 66)))
    else:
        dvd = Pose(z=DROP * ease_out(phase(f, 196, 206)), spin=180.0 + 720.0 * phase(f, 186, 214),
                   scale=max(HIDDEN, 1 - ease_in(phase(f, 204, 214))))
    t = phase(f, 96, 178)
    k = math.sin(math.pi * t)
    poses = {"tray": Pose(y=slide(f, 26, 86) if f < 150 else slide(f, 180, 226)), "disc": dvd,
             "eject": Pose(y=1.4 * max(tap(f, 22), tap(f, 176))), "power": Pose(y=1.4 * tap(f, 4)),
             "pad_light": Pose() if 16 <= f < 232 else Pose(scale=HIDDEN),
             "left_stick": Pose(pitch=L.STICKS["tilt"] * k * math.sin(2 * math.pi * 3.0 * t),
                                roll=L.STICKS["tilt"] * k * math.cos(2 * math.pi * 2.0 * t)),
             "right_stick": Pose(roll=L.STICKS["tilt"] * 0.8 * k * math.sin(2 * math.pi * 2.5 * t)),
             "dpad": Pose(pitch=5.0 * k * math.sin(2 * math.pi * 1.5 * t)),
             "a": Pose(z=-L.FACE["press"] * max(tap(f, f0) for f0 in (102, 122, 142, 164))),
             "b": Pose(z=-L.FACE["press"] * max(tap(f, f0) for f0 in (112, 152))),
             "x": Pose(z=-L.FACE["press"] * tap(f, 132)), "y": Pose(z=-L.FACE["press"] * tap(f, 170))}
    for q in range(4):                                  # the Ring of Light: round, a quadrant at a time, then all on
        poses[f"ring_{q + 1}"] = Pose() if 8 + 2 * q <= f < 236 else Pose(scale=HIDDEN)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "xbox360_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    console = body(m)
    pad, pad_nodes = controller(m)
    to_world = pad_frame()
    pad.data.transform(to_world)
    whole = join([console, pad], "xbox360")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("xbox360_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    drawer, drawer_at = tray(m)
    parts = {"tray": (drawer, drawer_at)}
    (ex, ez), (ew, eh) = L.EJECT["at"], L.EJECT["size"]
    eject = facing("eject", rounded(0.0, 0.0, ew, eh, eh / 2 - 0.1, 4), -1.6, 0.5, m["body"])
    paint(eject, m["body"], swatch("plate"), lambda c, n, kind: True)
    paint(eject, m["body"], lambda co: FRONT(co.x + ex + L.WIDTH / 2, L.HEIGHT - (co.z + ez)),
          lambda c, n, kind: n.y < -0.9)
    parts["eject"] = (eject, Vector((ex, 0.0, ez)))
    (px, pz), pr = L.POWER["at"], L.POWER["r"]
    power = facing("power", circle(0.0, 0.0, pr, 32), -L.POWER["height"], 0.5, m["body"])
    bevel(power, 1.0, segments=2)
    paint(power, m["body"], swatch("plate"), lambda c, n, kind: True)
    paint(power, m["body"], lambda co: FRONT(co.x + px + L.WIDTH / 2, L.HEIGHT - (co.z + pz)),
          lambda c, n, kind: n.y < -0.9)
    parts["power"] = (power, Vector((px, 0.0, pz)))
    for q in range(4):
        parts[f"ring_{q + 1}"] = (quadrant(m, q), Vector((px, 0.0, pz)))
    turn = Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z")
    for name, (part, where) in pad_nodes.items():
        part.data.transform(turn)
        parts[name] = (part, to_world @ where)
    nodes = {}
    for name, (part, where) in parts.items():
        for p in part.data.polygons:
            p.use_smooth = True
        part.data.set_sharp_from_angle(angle=math.radians(35))
        part.parent = whole
        part.location = where
        nodes[name] = part
    dvd = disc(m)
    dvd.parent = drawer
    dvd.location = (0.0, 4.0 + L.WELL["y"], 2.0 - L.WELL["depth"] + L.DISC["thickness"] / 2 + 0.1)
    nodes["disc"] = dvd

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"Xbox 360: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
