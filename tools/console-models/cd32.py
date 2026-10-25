"""The console theme's Amiga CD32 system model (godot/themes/console/models/systems/amigacd32.glb): the CD32 and its
pad.

Built in Blender from the real console's proportions (cd32_layout.py has the measurements, taken from photographs).
The console is its side outline extruded across its width on a recessed base; the lid's seat, the CD's well under it
and the vents' grooves are cut into its top. The lid is a slab on its own hinge, the round dome on it; RESET stands on
the front face, the power light lit beside it. The pad is its traced outline lofted into a rounded slab, its D-pad,
its four coloured buttons, the play/pause bar and its shoulder buttons on it. The printing is one texture drawn by
cd32_print.py (the console from above, planar-mapped onto every face facing up; its front face; the pad's top; the
CD's two sides; swatches).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (its origin on its hinge), the CD (waiting in its well, shrunk to nothing), the CD light (shrunk to
nothing), and the pad's D-pad and its four buttons.

The `focused` clip (8 s, looping) plays a CD: the lid swings up, the CD drops into the well and the lid shuts; the CD
light flickers while it loads; the D-pad rocks and the red, blue, green and yellow buttons are pressed; then the lid
swings up again, the CD lifts out and goes, and the lid shuts.

Five materials (case, dark, pad, print, disc) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/cd32_print.py artifacts/amigacd32
    blender -b --factory-startup --python tools/console-models/cd32.py -- artifacts/amigacd32 godot/themes/console/models/systems/amigacd32.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd32_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, dark=0.7, pad=0.55, print=0.5, disc=0.2)
FRONT_H = L.FRONT[1][1]


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, FRONT_H)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, FRONT_H - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The console: the body on its base, the lid's seat, the well and the vents cut; RESET and the power light; its top
    and front printed."""
    w, d = L.WIDTH, L.DEPTH
    i = L.FOOT["inset"]
    base = box("base", -w / 2 + i, w / 2 - i, i, d - i, 0.0, L.FOOT["height"] + 1.0, m["dark"])
    body = prism_x("amigacd32", L.profile(), -w / 2, w / 2, m["case"])
    bevel(body, 2.0, segments=2)
    (x0, x1), (y0, y1), t = L.LID["x"], L.LID["y"], L.LID["thickness"]
    boolean(body, box("seat", x0, x1, y0, y1 + 10.0, L.TOP_Z - t, L.TOP_Z + 10.0, m["case"]))
    (wx, wy), wr = L.WELL["at"], L.WELL["r"]
    boolean(body, prism("well", circle(wx, wy, wr, 48), L.TOP_Z - t - L.WELL["depth"], L.TOP_Z, m["dark"]))
    v = L.VENTS
    boolean(body, join([box("vent", *v["x"], y - v["width"] / 2, y + v["width"] / 2, L.TOP_Z - v["depth"],
                            L.TOP_Z + 5.0, m["dark"]) for y in v["y"]], "vents"))
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.3 and name == "case")
    paint(body, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and name == "case")
    spindle = prism("spindle", circle(wx, wy, 8.0, 20), L.TOP_Z - t - L.WELL["depth"], L.SPINDLE_Z, m["dark"])
    (rx0, rx1), (rz0, rz1), out = L.RESET["x"], L.RESET["z"], L.RESET["out"]
    reset = solid("reset", [[(x, y, z) for x, z in rounded((rx0 + rx1) / 2, (rz0 + rz1) / 2, rx1 - rx0, rz1 - rz0,
                                                            (rz1 - rz0) / 2 - 0.2, 4)]
                            for y in (1.0, -out)], m["case"])
    bevel(reset, 0.8, segments=1)
    px, pz = L.LIGHTS["power"]
    lw, lh = L.LIGHTS["size"]
    power = painted(box("power_light", px - lw / 2, px + lw / 2, -0.4, 0.5, pz - lh / 2, pz + lh / 2, m["print"]), m,
                    "lit")
    return [base, body, spindle, reset, power]


def lid(m):
    """The lid, its origin on its hinge along its back edge: the slab and its dome, its top printed."""
    (x0, x1), (y0, y1), t = L.LID["x"], L.LID["y"], L.LID["thickness"]
    slab = box("lid", x0 + 0.5, x1 - 0.5, y0 + 0.5, y1, L.TOP_Z - t + 0.4, L.TOP_Z, m["case"])
    (dx, dy), r = L.DOME["at"], L.DOME["r"]
    dome = solid("dome", [[(x, y, z) for x, y in circle(dx, dy, rr, 64)] for rr, z in
                          ((r, L.TOP_Z - 1.0), (r, L.TOP_Z + L.DOME["rise"] - 1.5), (r - 2.0, L.TOP_Z + L.DOME["rise"]))],
                 m["case"])
    part = join([slab, dome], "lid")
    bevel(part, 0.8, segments=2, angle=50)
    paint(part, m["print"], top_uv, lambda c, n, name: n.z > 0.5)
    hinge = Vector((0.0, y1, L.TOP_Z - t / 2))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def access_light(m):
    x, z = L.LIGHTS["access"]
    w, h = L.LIGHTS["size"]
    part = painted(box("access", -w / 2, w / 2, -0.6, 0.4, -h / 2, h / 2, m["print"]), m, "amber")
    return part, Vector((x, 0.0, z))


def disc(m):
    r, t = L.DISC["r"], L.DISC["thickness"]
    part = prism("disc", circle(0.0, 0.0, r, 48), -t / 2, t / 2, m["disc"])
    top = atlas_uv(L.REGIONS["disc"], 2 * r, 2 * r)
    bottom = atlas_uv(L.REGIONS["data"], 2 * r, 2 * r)
    paint(part, m["disc"], lambda co: top(co.x + r, r - co.y), lambda c, n, name: n.z > 0.9)
    paint(part, m["disc"], lambda co: bottom(co.x + r, r + co.y), lambda c, n, name: n.z <= 0.9)
    return part


# ---- The pad ---------------------------------------------------------------------------------------------------------

def pad_frame():
    """The pad's frame: its local (x, y), y from its front edge back; its middle at PAD["at"]."""
    (px, py), turn = L.PAD["at"], L.PAD["turn"]
    return (Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
            @ Matrix.Translation((0.0, -L.PAD["length"] / 2, 0.0)))


def pad_outline():
    points = list(L.PAD_OUTLINE)
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    return points if area > 0 else list(reversed(points))


def pad(m):
    """The pad's body and its fixed parts (the play/pause bar, the shoulder buttons), at its place."""
    p = L.PAD
    t = p["thickness"]
    body = prism("pad", pad_outline(), 0.0, t, m["pad"])
    bevel(body, 6.0, segments=4, angle=30)
    top = atlas_uv(L.REGIONS["pad"], p["width"], p["length"])
    paint(body, m["print"], lambda co: top(co.x + p["width"] / 2, p["length"] - co.y), lambda c, n, name: n.z > 0.8)
    paint(body, m["print"], swatch("grey"), lambda c, n, name: n.z <= 0.8)
    x, y, w, h = p["pause"]
    bar = painted(prism("pause", rounded(x, y, w, h, h / 2 - 0.1, 3), t - 2.0, t + 1.2, m["print"]), m, "dark")
    parts = [body, bar]
    for side in (-1, 1):
        shoulder = painted(box("shoulder", side * 56.0 - 13.0, side * 56.0 + 13.0, 76.0, 82.0, t - 10.0, t - 3.0,
                               m["print"]), m, "dark")
        bevel(shoulder, 1.5, segments=1)
        parts.append(shoulder)
    for part in parts:
        part.data.transform(pad_frame())
    return parts


def pad_parts(m):
    """The D-pad and the four buttons, each its middle at its origin, and where each goes."""
    p = L.PAD
    t = p["thickness"]
    dx, dy, r = p["dpad"]
    dpad = painted(prism("dpad", circle(0.0, 0.0, r, 32), -2.0, 2.4, m["print"]), m, "dark")
    bumps = [painted(prism("bump", circle(r * 0.62 * math.cos(a), r * 0.62 * math.sin(a), 1.3, 10), 2.0, 3.2,
                           m["print"]), m, "dark") for a in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    dpad = join([dpad] + bumps, "dpad")
    parts = [("dpad", dpad, Vector((dx, dy, 0.0)))]
    for name, (x, y, br) in p["buttons"].items():
        button = painted(prism(name, circle(0.0, 0.0, br, 24), -2.0, 3.2, m["print"]), m, name)
        bevel(button, 1.0, segments=2)
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
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


PRESSES = dict(red=(110, 130, 158), blue=(118, 142), green=(150, 166), yellow=(136, 172))
ROCKS = [(96, 106, 0.0, 9.0), (122, 132, 9.0, 0.0), (150, 160, 0.0, -9.0)]


def lid_angle(f):
    open_ = L.LID["open"]
    if f < 186:
        return (open_ * back_out(phase(f, 8, 22), 1.3) * (1 - smooth(phase(f, 48, 60)))
                + wobble(f, 60, 2.0, period=8.0, decay=3.0))
    return (open_ * back_out(phase(f, 186, 198), 1.3) * (1 - smooth(phase(f, 214, 226)))
            + wobble(f, 226, 2.0, period=8.0, decay=3.0))


def timeline(f):
    if f < 22 or f >= 212:
        cd = Pose(scale=HIDDEN)
    elif f < 30:
        cd = Pose(z=60.0, scale=appear(f, 22, 28))
    elif f < 42:
        cd = Pose(z=60.0 * (1 - ease_in(phase(f, 30, 42))))
    elif f < 198:
        cd = Pose()
    else:
        cd = Pose(z=60.0 * ease_out(phase(f, 198, 206)), scale=max(HIDDEN, 1 - ease_in(phase(f, 204, 212))))
    reading = 62 <= f < 98 and (f // 3) % 4 != 3
    poses = {"lid": Pose(pitch=lid_angle(f)), "disc": cd, "access": Pose() if reading else Pose(scale=HIDDEN)}
    for name, frames in PRESSES.items():
        poses[name] = Pose(z=-2.0 * max(tap(f, f0) for f0 in frames))
    pitch = roll = 0.0
    for f0, f1, pa, ro in ROCKS:
        t = smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f1, f1 + 4)))
        pitch, roll = pitch + pa * t, roll + ro * t
    poses["dpad"] = Pose(pitch=pitch, roll=roll)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "cd32_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    textures = dict(print=printed, disc=printed)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    whole = join(console(m) + pad(m), "amigacd32")
    cover, hinge = lid(m)
    light, light_at = access_light(m)
    cd = disc(m)
    buttons = pad_parts(m)
    for obj in [whole, cover] + [part for _, part, _ in buttons]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(40))

    root = bpy.data.objects.new("amigacd32_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (wx, wy) = L.WELL["at"]
    seat = Vector((wx, wy, L.SPINDLE_Z + L.DISC["thickness"] / 2))
    placed = [(cover, hinge), (light, light_at), (cd, seat)] + [(part, where) for _, part, where in buttons]
    for part, where in placed:
        part.parent = whole
        part.location = where
    nodes = {"lid": cover, "access": light, "disc": cd, **{name: part for name, part, _ in buttons}}

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, cover, light, cd] + [part for _, part, _ in buttons]
    print(f"CD32: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
