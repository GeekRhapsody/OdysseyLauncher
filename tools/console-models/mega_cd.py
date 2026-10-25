"""The console theme's Mega-CD system model (godot/themes/console/models/systems/segacd.glb): the first Mega-CD with
the Mega Drive sitting on it.

Built in Blender (mega_cd_layout.py has the measurements, taken from photographs). The Mega-CD is a rounded black box
on four feet, the glossy panel sunk into its front, the tray's opening behind the door, and the connecting block on its
right end rising beside the Mega Drive; the Mega Drive is mega_drive.py's own, built by its build() and set on top.
The tray is the door (MEGA-CD on it) and the plate behind it with the CD's well, hidden in the box until it slides
out. The printing is two textures: mega_cd_print.py's (the front panel, the door, the CD's two sides, swatches) and
mega_drive_print.py's (the Mega Drive's top), both drawn into the same folder.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the tray (holding the CD, waiting in its well shrunk to nothing) and the READY and ACCESS lights (shrunk to
nothing).

The `focused` clip (8 s, looping) plays a CD: the tray slides out, the CD drops into its well, the tray takes it in;
READY lights and ACCESS flickers while it loads; later the tray slides out again, the CD lifts off and goes, and the
tray goes back.

Seven materials (the Mega Drive's print, gloss, dark and reset; case, cd_print, disc) and two textures, within the
system model budget. Run from the repo root:

    python tools/console-models/mega_drive_print.py artifacts/segacd
    python tools/console-models/mega_cd_print.py artifacts/segacd
    blender -b --factory-startup --python tools/console-models/mega_cd.py -- artifacts/segacd godot/themes/console/models/systems/segacd.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mega_cd_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive import build as mega_drive  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def mega_cd(m):
    """The Mega-CD: the box on its feet, the front panel's recess and the tray's opening, the connecting block; its
    front printed."""
    w, d = L.WIDTH, L.DEPTH
    body = prism("segacd", rounded(0.0, 0.0, w, d, 10.0, 4), L.FOOT, L.HEIGHT, m["case"])
    bevel(body, 3.0, segments=2)
    b = L.BLOCK
    lower = box("block", b["x"][0], b["x"][1], *b["y"], L.FOOT + 2.0, L.HEIGHT, m["case"])
    upper = box("block_top", b["inner"], b["x"][1], *b["y"], L.HEIGHT - 2.0, b["top"], m["case"])
    block = join([lower, upper], "block")
    boolean(body, block, "UNION")
    bevel(body, 1.5, segments=1, angle=50)
    p = L.PANEL
    (x0, x1), (z0, z1) = p["x"], p["z"]
    face = rounded((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, (z1 - z0) / 2 - 0.1, 6)
    boolean(body, solid("panel", [[(x, y, z) for x, z in face] for y in (L.FRONT_Y - 5.0, L.FRONT_Y + p["depth"])],
                        m["gloss"]))
    dr = L.DOOR
    boolean(body, box("opening", dr["x"][0] - 0.5, dr["x"][1] + 0.5, L.FRONT_Y - 5.0, L.FRONT_Y + L.TRAY["depth"] + 10.0,
                      dr["z"][0] - 0.5, dr["z"][1] + 0.5, m["gloss"]))
    front = atlas_uv(L.REGIONS["front"], x1 - x0, z1 - z0)
    paint(body, m["cd_print"], lambda co: front(co.x - x0, z1 - co.z),
          lambda c, n, name: n.y < -0.9 and abs(c.y - (L.FRONT_Y + p["depth"])) < 0.3)
    feet = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            foot = prism("foot", rounded(sx * (w / 2 - 34.0), sy * (d / 2 - 30.0), 52.0, 40.0, 10.0, 3), 0.0,
                         L.FOOT + 1.0, m["case"])
            feet.append(foot)
    return join([body] + feet, "segacd")


def tray(m):
    """The tray, its origin at its door's middle: the door (MEGA-CD on it) and the plate behind it with the CD's well;
    and where the CD's middle sits, in its frame."""
    dr, t = L.DOOR, L.TRAY
    door = box("tray", *dr["x"], L.FRONT_Y + L.PANEL["depth"] - dr["out"], L.FRONT_Y + L.PANEL["depth"] + 2.0,
               *dr["z"], m["case"])
    bevel(door, 0.6, segments=1)
    face = atlas_uv(L.REGIONS["door"], dr["x"][1] - dr["x"][0], dr["z"][1] - dr["z"][0])
    paint(door, m["cd_print"], lambda co: face(co.x - dr["x"][0], dr["z"][1] - co.z), lambda c, n, name: n.y < -0.9)
    y0 = L.FRONT_Y + L.PANEL["depth"] + 2.0
    plate = box("plate", dr["x"][0] + 1.0, dr["x"][1] - 1.0, y0, y0 + t["depth"], *t["z"], m["gloss"])
    wy, wr = t["well"]
    cx = (dr["x"][0] + dr["x"][1]) / 2
    boolean(plate, prism("well", circle(cx, y0 + wy, wr + 0.6, 48), t["z"][1] - 1.6, t["z"][1] + 2.0, m["gloss"]))
    paint(plate, m["cd_print"], swatch("dark"), lambda c, n, name: True)
    part = join([door, plate], "tray")
    middle = Vector((cx, L.FRONT_Y + L.PANEL["depth"], (dr["z"][0] + dr["z"][1]) / 2))
    part.data.transform(Matrix.Translation(-middle))
    seat = Vector((cx, y0 + wy, t["z"][1] - 1.6 + L.DISC["thickness"] / 2 + 0.1)) - middle
    return part, middle, seat


def disc(m):
    r, t = L.DISC["r"], L.DISC["thickness"]
    part = prism("disc", circle(0.0, 0.0, r, 48), -t / 2, t / 2, m["disc"])
    top = atlas_uv(L.REGIONS["disc"], 2 * r, 2 * r)
    bottom = atlas_uv(L.REGIONS["data"], 2 * r, 2 * r)
    paint(part, m["disc"], lambda co: top(co.x + r, r - co.y), lambda c, n, name: n.z > 0.9)
    paint(part, m["disc"], lambda co: bottom(co.x + r, r + co.y), lambda c, n, name: n.z <= 0.9)
    return part


def light(m, name, colour):
    x, z = L.LIGHTS[name]
    pw, ph = L.LIGHTS["size"]
    y = L.FRONT_Y + L.PANEL["depth"] - 0.25
    part = box(name, x - pw / 2 + 2.0, x + pw / 2 - 2.0, y - 0.3, y, z - ph / 2 - 2.2, z - ph / 2 - 0.8, m["cd_print"])
    paint(part, m["cd_print"], swatch(colour), lambda c, n, _name: True)
    middle = Vector((x, y - 0.15, z - ph / 2 - 1.5))       # a lit bar under its legend
    part.data.transform(Matrix.Translation(-middle))
    return part, middle


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def out(f):
    if f < 60:
        return smooth(phase(f, 8, 26))
    if f < 186:
        return 1 - smooth(phase(f, 44, 60))
    if f < 218:
        return smooth(phase(f, 188, 204))
    return 1 - smooth(phase(f, 220, 236))


def timeline(f):
    if f < 26 or f >= 218:
        cd = Pose(scale=HIDDEN)
    elif f < 32:
        cd = Pose(z=50.0, scale=appear(f, 26, 31))
    elif f < 42:
        cd = Pose(z=50.0 * (1 - ease_in(phase(f, 32, 42))))
    elif f < 206:
        cd = Pose()
    else:
        cd = Pose(z=50.0 * ease_out(phase(f, 206, 212)), scale=max(HIDDEN, 1 - ease_in(phase(f, 210, 218))))
    reading = (64 <= f < 120 or 150 <= f < 160) and (f // 3) % 4 != 3
    return {"tray": Pose(y=-L.TRAY["travel"] * out(f)), "disc": cd,
            "ready": Pose() if 62 <= f < 186 else Pose(scale=HIDDEN), "access": Pose() if reading else Pose(scale=HIDDEN)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out_path = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    md_print = bpy.data.images.load(os.path.join(images, "megadrive_print.png"))
    cd_print = bpy.data.images.load(os.path.join(images, "mega_cd_print.png"))
    m = {
        "print": material("print", "#FFFFFF", 0.55, md_print),
        "gloss": material("gloss", "#FFFFFF", 0.18, md_print),
        "dark": material("dark", "#060607", 0.9),
        "reset": material("reset", "#C4C5BC", 0.5),
        "case": material("case", L.COLOURS["case"], 0.5),
        "cd_print": material("cd_print", "#FFFFFF", 0.25, cd_print),
        "disc": material("disc", "#FFFFFF", 0.2, cd_print),
    }
    m_cd = dict(m, gloss=m["cd_print"])                     # the Mega-CD's glossy parts take the panel's printing

    md = mega_drive(m)
    md.data.transform(Matrix.Translation((0.0, L.MD_BACK, L.MD_LIFT)))
    base = mega_cd(m_cd)
    paint(base, m["cd_print"], swatch("dark"), lambda c, n, name: name == "cd_print" and abs(n.y) < 0.5)
    whole = join([base, md], "segacd")
    for poly in whole.data.polygons:
        poly.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))
    drawer, drawer_at, seat = tray(m_cd)
    cd = disc(m)
    lights = {"ready": light(m, "ready", "green"), "access": light(m, "access", "red")}

    root = bpy.data.objects.new("segacd_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    drawer.parent = whole
    drawer.location = drawer_at
    cd.parent = drawer
    cd.location = seat
    for part, where in lights.values():
        part.parent = whole
        part.location = where
    nodes = {"tray": drawer, "disc": cd, **{name: part for name, (part, _) in lights.items()}}

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, drawer, cd] + [part for part, _ in lights.values()]
    print(f"Mega-CD: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out_path, animations=True)


if __name__ == "__main__":
    main()
