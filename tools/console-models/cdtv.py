"""The console theme's Commodore CDTV system model (godot/themes/console/models/systems/cdtv.glb): the CDTV and its
remote controller.

Built in Blender (cdtv_layout.py has the measurements, taken from a period review and photographs). The case is a box on
four silver feet, the front's foot a strip recessed under a ledge, the slot and the eject button's hole cut into the
front; the display's faces and the LEDs sit on the front. The remote is a slab, its keys standing on its middle, the
D-pad on its left end and A and B on its right. The printing is one texture (cdtv_print.py's), projected from in front
onto the front and the display, and from above onto the top's grille, the remote and the caddy.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the caddy (waiting in front of the slot, shrunk to nothing), the eject button, the two LEDs and the display's
five faces (each lit one in front of the front face, the rest inside the case), and the remote's D-pad, A and B.

The `focused` clip (8 s, looping): the caddy slides into the slot; the green LED comes on, the yellow one flickers while
the disc is read, and the clock gives way to track 01, its time counting; the D-pad rocks and A and B fire; then the
eject button, the caddy slides out and goes, and the clock is back.

Three materials (case, remote, caddy) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/cdtv_print.py artifacts/cdtv
    blender -b --factory-startup --python tools/console-models/cdtv.py -- artifacts/cdtv godot/themes/console/models/systems/cdtv.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdtv_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 24.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.45, remote=0.5, caddy=0.35)
FACES = ("clock", "time_0", "time_1", "time_2", "time_3")
LIT, DARK = -0.3, 1.0     # where a lit face or LED sits (y): in front of the front face; and an unlit one, inside


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT - L.FEET["height"])
VENTS = atlas_uv(L.REGIONS["vents"], L.WIDTH, 130.0)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z)


def disc(name, x, y, z0, z1, r, mat, segments=24):
    ring = [(x + r * math.cos(2 * math.pi * k / segments), y + r * math.sin(2 * math.pi * k / segments))
            for k in range(segments)]
    return solid(name, [[(px, py, z) for px, py in ring] for z in (z0, z1)], mat)


# ---- The CDTV --------------------------------------------------------------------------------------------------------

def case(m):
    """The case, the strip, the slot and the eject button's hole cut in; the feet; printed."""
    half, foot = L.WIDTH / 2, L.FEET["height"]
    body = box("cdtv", -half, half, 0.0, L.DEPTH, foot, L.HEIGHT, m["case"])
    bevel(body, 1.5, segments=2)
    z0, z1 = L.STRIP["z"]
    boolean(body, box("strip", -half - 1.0, half + 1.0, -1.0, L.STRIP["depth"], z0 - 1.0, z1, m["case"]))
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    boolean(body, box("slot", sx0, sx1, -1.0, L.SLOT["depth"], sz0, sz1, m["case"]))
    (ex0, ex1), (ez0, ez1) = L.EJECT["x"], L.EJECT["z"]
    boolean(body, box("eject_hole", ex0, ex1, -1.0, L.EJECT["depth"], ez0, ez1, m["case"]))
    colour(body, m["case"], "case")
    paint(body, m["case"], front_uv, lambda c, n, kind: n.y < -0.9)
    paint(body, m["case"], lambda co: VENTS(co.x + half, 320.0 - co.y), lambda c, n, kind: n.z > 0.9 and c.y > 190.0)

    def inside(c):
        """In the slot or the eject button's hole."""
        return (sx0 - 0.5 < c.x < sx1 + 0.5 and sz0 - 0.5 < c.z < sz1 + 0.5
                or ex0 - 0.5 < c.x < ex1 + 0.5 and ez0 - 0.5 < c.z < ez1 + 0.5)
    paint(body, m["case"], swatch("dark"), lambda c, n, kind: c.y > 0.5 and inside(c))
    feet = [colour(disc("foot", side * L.FEET["x"], y, 0.0, foot + 1.0, L.FEET["r"], m["case"]), m["case"], "silver")
            for side in (-1, 1) for y in L.FEET["y"]]
    return join([body] + feet, "cdtv")


def face(m, name):
    """One of the display's faces, facing the viewer, its middle at its origin."""
    (x0, x1), (z0, z1) = L.DISPLAY["x"], L.DISPLAY["z"]
    w, h = x1 - x0, z1 - z0
    part = box(name, -w / 2, w / 2, -0.1, 0.1, -h / 2, h / 2, m["case"])
    colour(part, m["case"], "dark")
    uv = atlas_uv(L.REGIONS[name], w, h)
    paint(part, m["case"], lambda co: uv(co.x + w / 2, h / 2 - co.z), lambda c, n, kind: n.y < -0.9)
    return part


def led(m, name):
    r = L.LEDS["r"]
    part = disc(name, 0.0, 0.0, -0.1, 0.1, r, m["case"], 12)
    part.data.transform(Matrix.Rotation(math.radians(90.0), 4, "X"))
    return colour(part, m["case"], name)


def eject(m):
    """The eject button, its front's middle at its origin."""
    (ex0, ex1), (ez0, ez1) = L.EJECT["x"], L.EJECT["z"]
    w, h = ex1 - ex0 - 1.0, ez1 - ez0 - 1.0
    part = box("eject", -w / 2, w / 2, 0.0, 3.0, -h / 2, h / 2, m["case"])
    bevel(part, 0.5, segments=1)
    return colour(part, m["case"], "key")


def caddy(m):
    """The caddy, lying flat, its leading edge's middle at its origin, its top printed (the disc through its window)."""
    w, length, t = L.CADDY["size"]
    part = box("caddy", -w / 2, w / 2, -length, 0.0, -t / 2, t / 2, m["caddy"])
    bevel(part, 1.2, segments=2)
    colour(part, m["caddy"], "caddy")
    top = atlas_uv(L.REGIONS["caddy"], w, length)
    paint(part, m["caddy"], lambda co: top(co.x + w / 2, -co.y), lambda c, n, kind: n.z > 0.9)
    return part


# ---- The remote ------------------------------------------------------------------------------------------------------

def remote(m):
    """The remote at its place: the slab, its keys; the D-pad, A and B apart (each with where it goes)."""
    length, depth, height = L.REMOTE["size"]
    x, y, turn = L.REMOTE["at"]
    place = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
    slab = solid("remote", [[(px, py, 0.0) for px, py in rounded(0.0, 0.0, length, depth, 10.0, 4)],
                            [(px, py, height) for px, py in rounded(0.0, 0.0, length - 4.0, depth - 4.0, 8.0, 4)]],
                 m["remote"])
    bevel(slab, 1.5, segments=2)
    colour(slab, m["remote"], "remote")
    top = atlas_uv(L.REGIONS["remote"], length, depth)
    paint(slab, m["remote"], lambda co: top(co.x + length / 2, depth / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    parts = [slab]
    kw, kh = L.REMOTE["key"]
    for (kx, ky), name in zip(L.KEYS, L.KEY_NAMES):
        part = box("key", kx - kw / 2, kx + kw / 2, ky - kh / 2, ky + kh / 2, height - 1.0, height + 2.2, m["remote"])
        bevel(part, 0.6, segments=1)
        parts.append(colour(part, m["remote"], "red" if name == "POWER" else "key"))
    whole = join(parts, "remote")
    whole.data.transform(place)

    px, py, reach, arm = L.REMOTE["pad"]
    cross = join([box("arm", -reach, reach, -arm / 2, arm / 2, -1.0, 4.0, m["remote"]),
                  box("arm", -arm / 2, arm / 2, -reach, reach, -1.0, 4.0, m["remote"])], "pad")
    bevel(cross, 1.2, segments=2, angle=30)
    colour(cross, m["remote"], "remote")
    moving = {"pad": (cross, place @ Vector((px, py, height)))}
    for name in ("a", "b"):
        bx, by = L.REMOTE[name]
        part = disc(name, 0.0, 0.0, -1.0, 3.0, L.REMOTE["r"], m["remote"], 20)
        bevel(part, 0.8, segments=2)
        moving[name] = (colour(part, m["remote"], "remote"), place @ Vector((bx, by, height)))
    for part, _ in moving.values():
        part.data.transform(Matrix.Rotation(math.radians(turn), 4, "Z"))
    return whole, moving


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def shown(f):
    if f < 60 or f >= 176:
        return "clock"
    return "time_%d" % min(3, (f - 60) // 30)


def timeline(f):
    out, up = L.CADDY["out"], 30.0
    if f < 10 or f >= 198:
        disk = Pose(y=-out, z=up, scale=HIDDEN)
    elif f < 17:
        disk = Pose(y=-out, z=up, scale=max(HIDDEN, back_out(phase(f, 10, 17))))
    elif f < 24:
        disk = Pose(y=-out, z=up * (1 - ease_in(phase(f, 17, 24))))
    elif f < 176:
        disk = Pose(y=-out * (1 - smooth(phase(f, 24, 42))))
    elif f < 190:
        disk = Pose(y=-out * smooth(phase(f, 176, 190)))
    else:
        disk = Pose(y=-out, z=up * ease_out(phase(f, 190, 198)), scale=max(HIDDEN, 1 - ease_in(phase(f, 194, 198))))
    poses = {"caddy": disk, "eject": Pose(y=1.8 * tap(f, 170))}
    for name in FACES:
        poses[name] = Pose() if name == shown(f) else Pose(y=DARK - LIT)
    playing = 44 <= f < 174
    reading = 46 <= f < 90 and (f // 3) % 3 != 2
    poses["green"] = Pose() if playing else Pose(y=DARK - LIT)
    poses["yellow"] = Pose() if reading else Pose(y=DARK - LIT)
    t = phase(f, 70, 168)
    k = math.sin(math.pi * t)
    poses["pad"] = Pose(pitch=7.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=7.0 * k * math.cos(2 * math.pi * 2.0 * t))
    poses["a"] = Pose(z=-1.8 * max(tap(f, f0) for f0 in (84, 104, 124, 144)))
    poses["b"] = Pose(z=-1.8 * max(tap(f, f0) for f0 in (96, 136, 156)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "cdtv_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    controller, moving = remote(m)
    whole = join([case(m), controller], "cdtv")
    for p in whole.data.polygons:
        p.use_smooth = p.area < 400.0                     # the big flat faces flat
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("cdtv_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    w, length, _ = L.CADDY["size"]
    moving["caddy"] = (caddy(m), Vector(((sx0 + sx1) / 2, length - L.CADDY["proud"], (sz0 + sz1) / 2)))
    (ex0, ex1), (ez0, ez1) = L.EJECT["x"], L.EJECT["z"]
    moving["eject"] = (eject(m), Vector(((ex0 + ex1) / 2, -1.0, (ez0 + ez1) / 2)))
    (dx0, dx1), (dz0, dz1) = L.DISPLAY["x"], L.DISPLAY["z"]
    for name in FACES:
        moving[name] = (face(m, name), Vector(((dx0 + dx1) / 2, LIT, (dz0 + dz1) / 2)))
    for name in ("green", "yellow"):
        lx, lz = L.LEDS[name]
        moving[name] = (led(m, name), Vector((lx, LIT, lz)))
    nodes = {}
    for name, (part, where) in moving.items():
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
    print(f"CDTV: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
