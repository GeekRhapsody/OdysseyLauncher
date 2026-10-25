"""The console theme's 64DD system model (godot/themes/console/models/systems/n64dd.glb): the Nintendo 64 standing on
its 64DD, its controller in front.

Built in Blender. The console and the controller are n64.py's own, built by its functions and lifted onto the drive;
the drive (n64dd_layout.py has its measurements) is the console's base's shape grown taller, its corner pods running its
full height, the panel sunk into its front between them with the disk's slot cut into it. The printing is two textures:
n64_print.py's (the console and the controller) and n64dd_print.py's (the drive's front, the disk's label), both drawn
into the same folder.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the disk (waiting in front of its slot, shrunk to nothing), EJECT, the console's POWER knob and its light
(shrunk to nothing while it's off), and the controller's stick, A, B and START.

The `focused` clip (8 s, looping): the disk appears in front of the drive and slides into its slot; POWER slides on and
the light comes on; the stick swings round and A, B and START are pressed; then EJECT, the disk slides back out and
goes, and POWER goes off.

Seven materials (the console's case, controller, dark, cart and print; the drive's dd and disk) and two textures, within
the system model budget. Run from the repo root:

    python tools/console-models/n64_print.py artifacts/n64dd
    python tools/console-models/n64dd_print.py artifacts/n64dd
    blender -b --factory-startup --python tools/console-models/n64dd.py -- artifacts/n64dd godot/themes/console/models/systems/n64dd.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n64  # noqa: E402
import n64_layout as N  # noqa: E402
import n64dd_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer
PRESSES = dict(a=(84, 102, 110, 146), b=(124, 130), start=(66, 168))


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The drive -------------------------------------------------------------------------------------------------------

def drive(m):
    """The 64DD: its base, its pods, the panel sunk into its front and the slot cut into the panel; printed."""
    b, h = L.BASE, L.HEIGHT
    lower = solid("n64dd", [n64.plan(b["x"] - 4.0, b["front"] + 4.0, b["back"] - 4.0, b["r"], 0.0),
                            n64.plan(b["x"] - 4.0, b["front"] + 4.0, b["back"] - 4.0, b["r"], L.FOOT),
                            n64.plan(b["x"], b["front"], b["back"], b["r"], L.FOOT + 0.01),
                            n64.plan(b["x"], b["front"], b["back"], b["r"], h)], m["dd"])
    bevel(lower, 2.0, segments=2)
    pods = []
    for x, y, rx, ry in (L.PODS["front"], L.PODS["back"]):
        for side in (-1, 1):
            pods.append(solid("pod", [n64.ellipse(side * x, y, rx - 3.0, ry - 3.0, 0.0),
                                      n64.ellipse(side * x, y, rx, ry, 4.0), n64.ellipse(side * x, y, rx, ry, h - 4.0),
                                      n64.ellipse(side * x, y, rx - 4.0, ry - 4.0, h)], m["dd"]))
    (x0, x1), (z0, z1), depth = L.RECESS["x"], L.RECESS["z"], L.RECESS["depth"]
    (s0, s1), (t0, t1) = L.SLOT["x"], L.SLOT["z"]
    # Cut before the pods join it: a boolean on a join of overlapping meshes can lose faces.
    boolean(lower, box("recess", x0, x1, b["front"] - 30.0, b["front"] + depth, z0, z1, m["dd"]))
    boolean(lower, box("slot", s0, s1, b["front"] - 5.0, b["front"] + 120.0, t0, t1, m["dd"]))
    body = join([lower] + pods, "n64dd")
    colour(body, m["dd"], "case")
    face = atlas_uv(L.REGIONS["front"], 2 * b["x"], h)
    paint(body, m["dd"], lambda co: face(co.x + b["x"], h - co.z), lambda c, n, kind: n.y < -0.9 and c.y < 40.0)
    paint(body, m["dd"], swatch("dark"),
          lambda c, n, kind: s0 - 0.5 < c.x < s1 + 0.5 and t0 - 0.5 < c.z < t1 + 0.5 and c.y > b["front"] + depth - 0.5)
    paint(body, m["dd"], swatch("dark"), lambda c, n, kind: c.z < L.FOOT - 0.2)
    return body


def eject(m):
    (ex, ez), r = L.EJECT["at"], L.EJECT["r"]
    part = solid("eject", [[(x, y, z) for x, z in circle(0.0, 0.0, r, 20)] for y in (-2.4, 1.0)], m["dd"])
    bevel(part, 0.8, segments=1)
    colour(part, m["dd"], "button")
    return part, Vector((ex, L.BASE["front"] + L.RECESS["depth"], ez))


def disk(m):
    """The disk, lying flat, its middle at its origin, its label up, going in along +y; and its seat in the drive."""
    w, d, t = L.DISK["size"]
    part = solid("disk", [[(x, y, z) for x, y in rounded(0.0, 0.0, w, d, 4.0, 3)] for z in (-t / 2, t / 2)], m["disk"])
    bevel(part, 1.0, segments=2)
    colour(part, m["disk"], "disk")
    label = atlas_uv(L.REGIONS["disk"], w, d)
    paint(part, m["disk"], lambda co: label(co.x + w / 2, d / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    seat = Vector((sum(L.SLOT["x"]) / 2, L.BASE["front"] + d / 2 + 8.0, sum(L.SLOT["z"]) / 2))
    return part, seat


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    out = L.DISK["out"]
    if f < 6 or f >= 222:
        cd = Pose(y=-out, scale=HIDDEN)
    elif f < 14:
        cd = Pose(y=-out, scale=max(HIDDEN, back_out(phase(f, 6, 13))))
    elif f < 20:
        cd = Pose(y=-out, z=2.0 * math.sin(2 * math.pi * phase(f, 14, 20)))
    elif f < 36:
        cd = Pose(y=-out * (1 - smooth(phase(f, 20, 36))))
    elif f < 194:
        cd = Pose(y=1.6 * math.sin(math.pi * phase(f, 36, 42)))
    elif f < 210:
        cd = Pose(y=-out * ease_out(phase(f, 194, 210)))
    else:
        cd = Pose(y=-out, z=10.0 * ease_out(phase(f, 210, 222)), scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 222))))
    on = smooth(phase(f, 42, 48)) * (1 - smooth(phase(f, 200, 206)))
    poses = {"disk": cd, "eject": Pose(y=L.EJECT["press"] * tap(f, 188)), "power": Pose(y=N.POWER["travel"] * on),
             "light": Pose() if on > 0.5 else Pose(scale=HIDDEN)}
    t = phase(f, 56, 136)
    lean = 16.0 * math.sin(math.pi * t) + 12.0 * math.sin(math.pi * phase(f, 150, 164))
    angle = 2 * math.pi * 2 * t
    poses["stick"] = Pose(pitch=lean * math.cos(angle), roll=lean * math.sin(angle))
    for name, frames in PRESSES.items():
        poses[name] = Pose(z=-2.0 * max(tap(f, f0) for f0 in frames))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    console_print = bpy.data.images.load(os.path.join(images, "n64_print.png"))
    drive_print = bpy.data.images.load(os.path.join(images, "n64dd_print.png"))
    colours = dict(N.COLOURS, print="#FFFFFF")
    m = {n: material(n, colours[n], r, console_print if n == "print" else None) for n, r in n64.ROUGHNESS.items()}
    m["dd"] = material("dd", "#FFFFFF", 0.55, drive_print)
    m["disk"] = material("disk", "#FFFFFF", 0.45, drive_print)

    lift = Matrix.Translation((0.0, 0.0, L.HEIGHT))
    console = [n64.base(m)] + n64.shell(m) + n64.ports(m)
    for part in console:
        part.data.transform(lift)
    flaps = []
    for part, hinge in n64.flaps(m).values():                 # shut: part of the set here
        part.data.transform(lift @ Matrix.Translation(hinge))
        flaps.append(part)
    reset, reset_at = n64.reset_button(m)
    reset.data.transform(lift @ Matrix.Translation(reset_at))
    whole = join([drive(m)] + console + flaps + [reset] + n64.controller(m), "n64dd")
    knob, knob_at = n64.power_knob(m)
    lit, lit_at = n64.power_light(m)
    buttons = n64.pad_parts(m)
    button, button_at = eject(m)
    cd, seat = disk(m)
    for obj in [whole, knob, button, cd] + [part for _, part, _ in buttons]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(55))

    root = bpy.data.objects.new("n64dd_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    up = Vector((0.0, 0.0, L.HEIGHT))
    placed = {"power": (knob, knob_at + up), "light": (lit, lit_at + up), "eject": (button, button_at),
              "disk": (cd, seat)}
    placed.update({name: (part, where) for name, part, where in buttons})
    nodes = {}
    for name, (part, where) in placed.items():
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
    print(f"64DD: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
