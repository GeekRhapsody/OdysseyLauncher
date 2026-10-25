"""The console theme's 3DO system model (godot/themes/console/models/systems/3do.glb): a Panasonic FZ-1 and its
controller.

Built in Blender from the real console's proportions (threedo_layout.py has the measurements, taken from
photographs). The body is a rounded box standing on a fluted pod at each corner (each pod a ring of grooves lofted up
its height); the raised plate on its top has its corners cut round the pods; the door's pocket is cut into the face
between the front pods, and the vents into its right side. POWER and OPEN/CLOSE are bronze tabs round the front pods.
The tray is the door with its plate and disc well behind it, hidden in the body until it slides out. The controller is
a dog-bone (two round lobes and the body between) lofted into a rounded slab, its D-pad, A, B and C, stop and
play/pause on it. The printing is two textures drawn by threedo_print.py: the console from above (planar-mapped onto
every face facing up: the plate's grain and embossing), the face between the front pods, the controller's top and
swatches; and the CD's two sides.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the tray (holding the CD, waiting in its well shrunk to nothing), POWER, OPEN/CLOSE, the READY and ACCESS
lights (shrunk to nothing), and the controller's D-pad, A, B and C.

The `focused` clip (8 s, looping) plays a game: POWER goes in and READY lights; OPEN/CLOSE goes in and the tray slides
out, the CD drops into its well, and OPEN/CLOSE again takes it in; ACCESS flickers while the game loads; the D-pad
rocks and A, B and C are pressed. Then the tray slides out, the CD lifts off and goes, the tray goes back, and POWER
goes off.

Five materials (case, dark, controller, print, disc) and two textures, within the system model budget. Run from the
repo root:

    python tools/console-models/threedo_print.py artifacts/3do
    blender -b --factory-startup --python tools/console-models/threedo.py -- artifacts/3do godot/themes/console/models/systems/3do.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import threedo_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.6, dark=0.3, controller=0.55, print=0.5, disc=0.2)
FRONT_W = L.FRONT["x"][1] - L.FRONT["x"][0]
FRONT_H = L.FRONT["z"][1]
PAD_W, PAD_D = L.PAD["size"]


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h, size=L.ATLAS):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / size, 1 - (ry + b / h * rh) / size)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], FRONT_W, FRONT_H)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x - L.FRONT["x"][0], FRONT_H - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def prism(name, outline, z0, z1, mat):
    """A solid from an (x, y) outline, from z0 to z1."""
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def pod(m, cx, cy):
    """A fluted pod: a ring of grooves lofted up its height, rounded in at its foot and its top."""
    r, n, f = L.POD["r"], L.POD["flutes"], L.POD["flute"]

    def ring(radius, z, fluted):
        points = []
        for k in range(2 * n):
            a = 2 * math.pi * (k + 0.5 * (k % 2)) / (2 * n)
            rr = radius - (f if fluted and k % 2 else 0.0)
            points.append((cx + rr * math.cos(a), cy + rr * math.sin(a), z))
        return points
    top = L.POD["top"]
    part = solid("pod", [ring(r - 2.5, 0.0, False), ring(r, 3.0, True), ring(r, top - 3.0, True),
                         ring(r - 2.0, top, False)], m["case"])
    for p in part.data.polygons:
        p.use_smooth = True
    return part


def body(m):
    """The body and its pods, the plate on top, cut for the door's pocket and the right side's vents; its top and
    the face between the front pods printed."""
    b = L.BODY
    (y0, y1), (z0, z1) = b["y"], b["z"]
    outline = rounded(0.0, (y0 + y1) / 2, 2 * b["x"], y1 - y0, b["r"], 3)
    box_ = prism("3do", outline, z0, z1, m["case"])
    bevel(box_, 1.5, segments=2)
    d = L.DOOR
    boolean(box_, box("pocket", d["x"][0] - 0.6, d["x"][1] + 0.6, y0 - 5.0, y0 + d["pocket"], d["z"][0] - 0.6,
                      d["z"][1] + 0.6, m["dark"]))
    v = L.VENTS
    slots = [box("vent", b["x"] - v["depth"], b["x"] + 5.0, y - v["width"] / 2, y + v["width"] / 2, *v["z"], m["dark"])
             for y in v["y"] if L.PODS[1][1] + L.POD["r"] + 4.0 < y < L.PODS[3][1] - L.POD["r"] - 4.0]
    boolean(box_, join(slots, "vents"))
    paint(box_, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and abs(c.y - y0) < 0.3 and name == "case"
          and abs(c.x) < L.FRONT["x"][1])

    p = L.PLATE
    (px0, px1), (py0, py1) = p["x"], p["y"]
    plate = prism("plate", rounded(0.0, (py0 + py1) / 2, px1 - px0, py1 - py0, p["r"], 4), z1 - 1.0, p["top"],
                  m["case"])
    boolean(plate, join([prism("cut", circle(x, y, L.POD["r"] + p["gap"], 32), z1 - 5.0, p["top"] + 5.0, m["case"])
                         for x, y in L.PODS], "cuts"))
    bevel(plate, 1.6, segments=2)
    parts = [box_, plate] + [pod(m, x, y) for x, y in L.PODS]
    whole = join(parts, "3do")
    paint(whole, m["print"], top_uv, lambda c, n, name: n.z > 0.5 and name == "case")
    return whole


def tab(m, name):
    """A bronze tab round a front pod (its origin at its middle), and where it goes."""
    index, z = L.TABS[name]
    cx, cy = L.PODS[index]
    r, out, h = L.POD["r"], L.TABS["out"], L.TABS["height"]
    a0, a1 = L.TABS["arc"]
    outer = [(cx + (r + out) * math.cos(math.radians(a0 + (a1 - a0) * k / 10)),
              cy + (r + out) * math.sin(math.radians(a0 + (a1 - a0) * k / 10))) for k in range(11)]
    inner = [(cx + (r - 1.5) * math.cos(math.radians(a1 - (a1 - a0) * k / 10)),
              cy + (r - 1.5) * math.sin(math.radians(a1 - (a1 - a0) * k / 10))) for k in range(11)]
    part = painted(prism(name, outer + inner, z, z + h, m["print"]), m, "bronze")
    bevel(part, 0.6, segments=1)
    middle = Vector((cx, cy - r - out / 2, z + h / 2))
    part.data.transform(Matrix.Translation(-middle))
    return part, middle


def light(m, name, colour):
    x, z = L.LIGHTS[name]
    w, h = L.LIGHTS["size"]
    y = L.FRONT_Y - 0.2
    part = painted(box(name, x - w / 2 - 0.2, x + w / 2 + 0.2, y - 0.3, y, z - h / 2 - 0.2, z + h / 2 + 0.2, m["print"]),
                   m, colour)
    middle = Vector((x, y - 0.15, z))
    part.data.transform(Matrix.Translation(-middle))
    return part, middle


def tray(m):
    """The tray, its origin at its door's middle: the door (its face printed) and the plate behind it with the
    disc's well; and where the CD's middle sits, in its frame."""
    d, t = L.DOOR, L.TRAY
    y0 = L.FRONT_Y
    door = box("tray", *d["x"], y0 - d["out"], y0 + 1.0, *d["z"], m["dark"])
    bevel(door, 0.5, segments=1)
    paint(door, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
    plate = box("plate", *t["x"], y0 + 1.0, y0 + 1.0 + t["depth"], *t["z"], m["dark"])
    wy, wr = t["well"]
    boolean(plate, prism("well", circle(0.0, y0 + wy, wr + 0.6, 40), t["z"][1] - 1.6, t["z"][1] + 2.0, m["dark"]))
    part = join([door, plate], "tray")
    middle = Vector((0.0, y0, (d["z"][0] + d["z"][1]) / 2))
    part.data.transform(Matrix.Translation(-middle))
    seat = Vector((0.0, y0 + wy, t["z"][1] - 1.6 + L.DISC["thickness"] / 2 + 0.1)) - middle
    return part, middle, seat


def disc(m):
    """The CD, its middle at its origin, its label up."""
    r, t = L.DISC["r"], L.DISC["thickness"]
    part = prism("disc", circle(0.0, 0.0, r, 48), -t / 2, t / 2, m["disc"])
    top = atlas_uv(L.DISC_REGIONS["label"], 2 * r, 2 * r, L.DISC_ATLAS)
    bottom = atlas_uv(L.DISC_REGIONS["data"], 2 * r, 2 * r, L.DISC_ATLAS)
    paint(part, m["disc"], lambda co: top(co.x + r, r - co.y), lambda c, n, name: n.z > 0.9)
    paint(part, m["disc"], lambda co: bottom(co.x + r, r + co.y), lambda c, n, name: n.z <= 0.9)
    return part


# ---- The controller --------------------------------------------------------------------------------------------------

def inside_pad(x, y):
    """Whether (x, y) is on the controller: in a lobe, or in its body between them."""
    for cx, cy, r in L.PAD["lobes"]:
        if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
            return True
    (left, _, _), (right, _, _) = L.PAD["lobes"]
    lo, hi = L.PAD["waist"]
    return left <= x <= right and lo <= y <= hi


def pad_outline(n=96):
    """The controller's outline, (x, y) anticlockwise: round its middle, the farthest point on it along each ray."""
    points = []
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        t = 100.0
        while t > 0.0 and not inside_pad(t * c, t * s):
            t -= 0.25
        points.append((t * c, t * s))
    return points


def pad_frame():
    (px, py), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def controller(m):
    """The controller's body and its fixed parts (stop, play/pause, the shoulders), at its place."""
    p = L.PAD
    t = p["thickness"]
    body = prism("controller", pad_outline(), 0.0, t, m["controller"])
    bevel(body, 8.0, segments=5, angle=30)
    top = atlas_uv(L.REGIONS["pad"], PAD_W, PAD_D)
    paint(body, m["print"], lambda co: top(co.x + PAD_W / 2, PAD_D / 2 - co.y), lambda c, n, name: n.z > 0.8)
    parts = [body]
    sw, sh = p["small"]
    for x, y in (p["stop"], p["play"]):
        small = painted(prism("small", [(x + a, y + b) for a, b in rounded(0.0, 0.0, sw, sh, sh / 2 - 0.1, 3)],
                              t - 3.0, t + 1.6, m["print"]), m, "beige")
        parts.append(small)
    for cx, cy, r in p["lobes"]:                           # the shoulder buttons along the lobes' backs
        shoulder = painted(box("shoulder", cx - 13.0, cx + 13.0, cy + r - 10.0, cy + r - 1.0, t - 9.0, t - 2.0,
                               m["print"]), m, "dark")
        bevel(shoulder, 2.0, segments=2)
        parts.append(shoulder)
    for part in parts:
        part.data.transform(pad_frame())
    return parts


def pad_parts(m):
    """The D-pad, A, B and C, each its middle at its origin, and where each goes."""
    p = L.PAD
    t = p["thickness"]
    dx, dy, span, arm = p["dpad"]
    cross = [(arm / 2, -span / 2), (arm / 2, -arm / 2), (span / 2, -arm / 2), (span / 2, arm / 2), (arm / 2, arm / 2),
             (arm / 2, span / 2), (-arm / 2, span / 2), (-arm / 2, arm / 2), (-span / 2, arm / 2), (-span / 2, -arm / 2),
             (-arm / 2, -arm / 2), (-arm / 2, -span / 2)]
    dpad = painted(prism("dpad", cross, -3.0, 2.4, m["print"]), m, "beige")
    bevel(dpad, 0.6, segments=1)
    parts = [("dpad", dpad, Vector((dx, dy, 0.0)))]
    for name, (x, y) in zip(("a", "b", "c"), p["abc"]):
        button = painted(prism(name, circle(0.0, 0.0, p["abc_r"], 20), -2.0, 3.0, m["print"]), m, "beige")
        bevel(button, 0.9, segments=2)
        parts.append((name, button, Vector((x, y, 0.0))))
    frame = pad_frame()
    turn = Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z")
    placed = []
    for name, part, where in parts:
        part.data.transform(turn)
        at = frame @ where
        placed.append((name, part, Vector((at.x, at.y, t))))
    return placed


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in two frames, held, back up in three."""
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


PRESSES = dict(power=(4, 228), open=(14, 58, 184), a=(128, 144, 168), b=(152,), c=(160, 176))
ROCKS = [(120, 128, 0.0, 9.0), (134, 142, 9.0, 0.0), (180, 188, 0.0, -9.0)]   # f0, f1, pitch, roll


def out(f):
    """How far the tray is out, 0 to 1."""
    if f < 60:
        return smooth(phase(f, 18, 34))
    if f < 186:
        return 1 - smooth(phase(f, 62, 78))
    if f < 218:
        return smooth(phase(f, 188, 204))
    return 1 - smooth(phase(f, 220, 234))


def timeline(f):
    poses = {"tray": Pose(y=-L.TRAY["travel"] * out(f))}

    # The CD: appears over the tray's well once it's out, drops in, rides in and out with it, lifts off and goes.
    if f < 36 or f >= 220:
        cd = Pose(scale=HIDDEN)
    elif f < 44:
        cd = Pose(z=50.0, scale=appear(f, 36, 42))
    elif f < 54:
        cd = Pose(z=50.0 * (1 - ease_in(phase(f, 44, 54))))
    elif f < 206:
        cd = Pose()
    else:
        cd = Pose(z=50.0 * ease_out(phase(f, 206, 214)), scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 220))))
    poses["disc"] = cd

    poses["ready"] = Pose() if 8 <= f < 232 else Pose(scale=HIDDEN)
    reading = (80 <= f < 118) and (f // 3) % 4 != 3
    poses["access"] = Pose() if reading else Pose(scale=HIDDEN)
    for name, frames in PRESSES.items():
        d = max(tap(f, f0) for f0 in frames)
        if name in ("power", "open"):
            poses[name] = Pose(y=1.4 * d)
        else:
            poses[name] = Pose(z=-1.8 * d)
    pitch = roll = 0.0
    for f0, f1, pa, ro in ROCKS:
        t = smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f1, f1 + 4)))
        pitch, roll = pitch + pa * t, roll + ro * t
    poses["dpad"] = Pose(pitch=pitch, roll=roll)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out_path = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "threedo_print.png"))
    discs = bpy.data.images.load(os.path.join(images, "threedo_disc.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    textures = dict(print=printed, disc=discs)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    whole = join([body(m)] + controller(m), "3do")
    drawer, drawer_at, seat = tray(m)
    cd = disc(m)
    tabs = {name: tab(m, name) for name in ("power", "open")}
    lights = {"ready": light(m, "ready", "green"), "access": light(m, "access", "amber")}
    buttons = pad_parts(m)
    for obj in [whole, drawer] + [part for part, _ in tabs.values()] + [part for _, part, _ in buttons]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(50))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("3do_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    placed = [(drawer, drawer_at)] + list(tabs.values()) + list(lights.values())
    placed += [(part, where) for _, part, where in buttons]
    for part, where in placed:
        part.parent = whole
        part.location = where
    cd.parent = drawer
    cd.location = seat
    nodes = {"tray": drawer, "disc": cd, **{name: part for name, (part, _) in tabs.items()},
             **{name: part for name, (part, _) in lights.items()}, **{name: part for name, part, _ in buttons}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, drawer, cd] + [part for part, _ in tabs.values()] + [part for part, _ in lights.values()]
    meshes += [part for _, part, _ in buttons]
    print(f"3DO: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out_path, animations=True)


if __name__ == "__main__":
    main()
