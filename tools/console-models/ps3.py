"""The console theme's PlayStation 3 system model (godot/themes/console/models/systems/ps3.glb): the original
PlayStation 3 and its DualShock 3.

Built in Blender from the real console's proportions (ps3_layout.py has the measurements, taken from photographs). The
shell is its arched section extruded from its front face to its back, glossy, its edges rounded, the Blu-ray slot cut
into its front; the matte plinth stands under it, set in. The DualShock 3 is its outline lofted up, its edges rounded,
the two discs on it, the d-pad's four arrows, the face buttons, SELECT, START and the PS button, the sticks standing in
their housings. The printing is one texture drawn by ps3_print.py: the shell's top and front and the plinth's front
(planar-mapped onto their faces), the controller's top, the Blu-ray's label, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the top
tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set holding
the disc (waiting in the drive, shrunk to nothing), the lit power light (shrunk to nothing) and the controller; the
controller holding its sticks, cross, the PS button and its first player light.

The `focused` clip (8 s, looping) plays a disc: the Blu-ray is pushed into the slot and the drive takes it; the power
light turns green; the PS button is pressed and the first light comes on; the game is played on the sticks and cross,
then steered by tilting the controller, as the Sixaxis's motion sensing did. Then the disc is ejected and taken away.

Four materials (case, plinth, key, print) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/ps3_print.py artifacts/ps3
    blender -b --factory-startup --python tools/console-models/ps3.py -- artifacts/ps3 godot/themes/console/models/systems/ps3.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps3_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 24.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.12, plinth=0.6, key=0.45, print=0.25)
P = L.PAD
PAD_W = 2 * max(x for x, _ in L.PAD_RIGHT)
PAD_D = max(y for _, y in L.PAD_RIGHT)


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT)
PAD_TOP = atlas_uv(L.REGIONS["pad"], PAD_W, PAD_D)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def upright(name, points, z0, z1, mat):
    """A solid from an (x, y) plan, from z0 up to z1."""
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


def disc_points(cx, cy, r, n=28):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The shell (its top and front printed, the slot cut into it) and the plinth under it."""
    section = L.shell_section()
    shell = solid("ps3", [[(x, y, z) for x, z in section] for y in (0.0, L.DEPTH)], m["case"])
    bevel(shell, 3.0, segments=2)
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    boolean(shell, box("slot", sx0, sx1, -5.0, L.SLOT["depth"], sz0, sz1, m["plinth"]))
    paint(shell, m["print"], lambda co: TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y),
          lambda c, n, name: n.z > 0.35 and name == "case")
    paint(shell, m["print"], lambda co: FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z),
          lambda c, n, name: n.y < -0.9 and c.y < 1.0 and name == "case")
    (px0, px1), (py0, py1), ph = L.PLINTH["x"], L.PLINTH["y"], L.PLINTH["height"]
    plinth = box("plinth", px0, px1, py0, py1, 0.0, ph, m["plinth"])
    bevel(plinth, 1.5, segments=2)
    face = atlas_uv(L.REGIONS["plinth"], px1 - px0, ph)
    paint(plinth, m["print"], lambda co: face(co.x - px0, ph - co.z), lambda c, n, name: n.y < -0.9 and c.y < py0 + 0.5)
    return [shell, plinth]


def power_light(m):
    lx, lz = L.LIGHT["at"]
    lw, lh = L.LIGHT["size"]
    part = painted(box("power_light", -lw / 2 - 0.2, lw / 2 + 0.2, -0.3, 0.2, -lh / 2 - 0.2, lh / 2 + 0.2, m["print"]),
                   m, "green")
    return part, Vector((lx, 0.0, lz))


def disc(m):
    """The Blu-ray, its middle at its origin, lying flat: a ring, its label on its top."""
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


# ---- The DualShock 3 -------------------------------------------------------------------------------------------------

def pad_uv(co):
    return PAD_TOP(co.x + PAD_W / 2, PAD_D - co.y)


def arrow(cx, cy, angle, length, width):
    """A d-pad arrow's plan: a rectangle pointing out from the middle at angle, its inner end pointed."""
    c, s = math.cos(angle), math.sin(angle)
    inner, outer, half = 3.0, 3.0 + length, width / 2
    local = [(inner, 0.0), (inner + half, -half), (outer, -half), (outer, half), (inner + half, half)]
    return [(cx + c * u - s * v, cy + s * u + c * v) for u, v in local]


def controller(m):
    """The DualShock 3 in its own frame (its grips' ends at y = 0, the table): its body, the discs, the d-pad, the
    face buttons but cross, SELECT, START, the stick housings; the sticks, cross, the PS button and the first light
    apart, each its foot's middle at its origin."""
    h = P["height"]
    outline = L.PAD_RIGHT + [(-x, y) for x, y in reversed(L.PAD_RIGHT[1:-1])]
    body = solid("controller", [[(x, y, z) for x, y in inset(outline, k)] for k, z in
                                ((2.0, 0.0), (0.0, 3.5), (0.0, h - 5.0), (2.4, h - 1.0), (4.0, h))], m["key"])
    for p in body.data.polygons:
        p.use_smooth = True
    paint(body, m["print"], pad_uv, lambda c, n, name: n.z > 0.95)
    parts = [body]
    for name in ("left", "right"):
        cx, cy = L.DISCS[name]
        rim = upright("disc_" + name, disc_points(cx, cy, L.DISCS["r"], 36), h - 1.0, h + L.DISCS["height"], m["key"])
        bevel(rim, 1.0, segments=2)
        paint(rim, m["print"], pad_uv, lambda c, n, _name: n.z > 0.95)
        parts.append(rim)
    top = h + L.DISCS["height"]
    dx, dy = L.DPAD["at"]
    for k in range(4):
        a = math.radians(90 * k)
        key_ = upright("arrow", arrow(dx, dy, a, L.DPAD["span"] / 2 - 3.0, L.DPAD["arm"]), top - 1.0,
                       top + L.DPAD["height"], m["key"])
        bevel(key_, 0.6, segments=1)
        parts.append(key_)
    for name in ("triangle", "circle", "square"):
        b = upright(name, disc_points(*L.FACE[name], L.FACE["r"], 24), top - 1.0, top + L.FACE["height"], m["key"])
        bevel(b, 1.0, segments=2)
        paint(b, m["print"], pad_uv, lambda c, n, _name: n.z > 0.95)
        parts.append(b)
    sw, sh = L.SMALL["size"]
    sx, sy = L.SMALL["select"]
    select = upright("select", [(sx + a, sy + b) for a, b in rounded(0.0, 0.0, sw, sh, 0.8, 2)], h - 1.0, h + 1.4,
                     m["key"])
    tx, ty = L.SMALL["start"]
    start = upright("start", [(tx - sw / 2, ty - sh / 2), (tx + sw / 2, ty), (tx - sw / 2, ty + sh / 2)], h - 1.0, h + 1.4,
                    m["key"])
    parts += [select, start]
    for name in ("left", "right"):
        hx, hy = L.STICKS[name]
        housing = upright("housing", disc_points(hx, hy, L.STICKS["housing"], 32), h - 1.0, h + 2.5, m["key"])
        bevel(housing, 1.2, segments=2)
        boolean(housing, upright("hole", disc_points(hx, hy, L.STICKS["housing"] - 2.5, 28), h, h + 5.0, m["key"]))
        parts.append(housing)
    shell = join(parts, "controller")

    moving = {}
    for name in ("left", "right"):
        (r0, r1), (z0, z1) = (5.0, L.STICKS["cap"]), L.STICKS["height"]
        shaft = upright("shaft", disc_points(0.0, 0.0, r0, 20), -2.0, z0, m["key"])
        cap = solid("cap", [[(x, y, z) for x, y in disc_points(0.0, 0.0, r1 * k, 32)] for k, z in
                            ((0.85, z0 - 0.5), (1.0, z0 + 1.0), (1.0, z1 - 1.5), (0.9, z1))], m["key"])
        stick = join([shaft, cap], name + "_stick")
        moving[name + "_stick"] = (stick, Vector((*L.STICKS[name], h)))
    cross = upright("cross", disc_points(0.0, 0.0, L.FACE["r"], 24), -1.0, L.FACE["height"], m["key"])
    bevel(cross, 1.0, segments=2)
    cx, cy = L.FACE["cross"]
    paint(cross, m["print"], lambda co: pad_uv(Vector((co.x + cx, co.y + cy, co.z))), lambda c, n, _name: n.z > 0.95)
    moving["cross"] = (cross, Vector((cx, cy, top)))
    ps = upright("ps", disc_points(0.0, 0.0, L.SMALL["ps_r"], 24), -1.0, 1.6, m["key"])
    bevel(ps, 0.8, segments=2)
    px, py = L.SMALL["ps"]
    paint(ps, m["print"], lambda co: pad_uv(Vector((co.x + px, co.y + py, co.z))), lambda c, n, _name: n.z > 0.95)
    moving["ps"] = (ps, Vector((px, py, h)))
    light = painted(box("light", -1.0, 1.0, -0.6, 0.6, -0.2, 0.3, m["print"]), m, "lit")
    moving["light_1"] = (light, Vector((L.LIGHTS["x"][0], L.LIGHTS["y"], h - 1.2)))
    return shell, moving


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 64.0           # how far in front of the slot the disc waits: its back edge at the slot


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    seat_y = L.SEAT[1]
    wait = -OUT - seat_y                                  # the disc's offset from its seat while it waits outside
    if f < 8 or f >= 228:
        dsk = Pose(scale=HIDDEN)
    elif f < 18:
        dsk = Pose(y=wait, scale=appear(f, 8, 18))
    elif f < 32:
        dsk = Pose(y=wait + 34.0 * smooth(phase(f, 18, 32)))         # pushed in by hand, a third of the way
    elif f < 42:
        dsk = Pose(y=(wait + 34.0) * (1 - ease_in(phase(f, 32, 42))))   # the drive takes it
    elif f < 196:
        dsk = Pose()
    elif f < 210:
        dsk = Pose(y=(wait + 40.0) * ease_out(phase(f, 196, 206)))     # ejected, half out
    else:
        lift = ease_in(phase(f, 214, 228))
        dsk = Pose(y=wait + 40.0 - 60.0 * smooth(phase(f, 210, 220)), z=30.0 * lift, scale=max(HIDDEN, 1 - lift))
    t = phase(f, 66, 138)
    k = math.sin(math.pi * t)
    steer = math.sin(math.pi * phase(f, 140, 190))
    tilt = 18.0 * steer * math.sin(2 * math.pi * 1.5 * phase(f, 140, 190))
    return {"disc": dsk, "power_light": Pose() if f >= 44 else Pose(scale=HIDDEN),
            "controller": Pose(roll=tilt, z=6.0 * steer),
            "ps": Pose(z=-1.2 * tap(f, 50)), "light_1": Pose() if 56 <= f else Pose(scale=HIDDEN),
            "left_stick": Pose(pitch=16.0 * k * math.sin(2 * math.pi * 2.0 * t), roll=16.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "right_stick": Pose(roll=14.0 * k * math.sin(2 * math.pi * 3.0 * t)),
            "cross": Pose(z=-1.6 * max(tap(f, f0) for f0 in (80, 96, 112, 128, 160, 176)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "ps3_print.png"))
    m = {n: material(n, L.COLOURS[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join(console(m), "ps3")
    lit, lit_at = power_light(m)
    bluray = disc(m)
    pad, moving = controller(m)
    for obj in [whole, bluray, pad] + [p for p, _ in moving.values()]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("ps3_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    for part, where in ((lit, lit_at), (bluray, Vector(L.SEAT))):
        part.parent = whole
        part.location = where
    (px, py), turn = P["at"], math.radians(P["turn"])
    pad.parent = whole
    pad.location = (px, py, 0.0)
    pad.rotation_euler = (0.0, 0.0, turn)
    for part, where in moving.values():
        part.parent = pad
        part.location = where
    nodes = {"disc": bluray, "power_light": lit, "controller": pad, **{n: p for n, (p, _) in moving.items()}}

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
    meshes = [whole, lit, bluray, pad] + [p for p, _ in moving.values()]
    print(f"PlayStation 3: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
