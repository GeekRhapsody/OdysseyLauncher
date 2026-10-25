"""The console theme's GameCube system model (godot/themes/console/models/systems/gc.glb): an indigo GameCube, its
handle round the back, and its controller.

Built in Blender from the real console's proportions (gamecube_layout.py has the measurements, taken from
photographs). The console is a cube rounded at its edges, the front panel joined onto its front; the seam near its
foot, the side vents' grids, the controller ports, the memory card slots, the lid's recess, the disc's well and the
buttons' sockets are cut into it. The lid lies in its recess on its own hinge; the handle is a half ring round the
back. The controller is its outline (traced from a photograph) lofted into a rounded slab, its sticks, buttons and
D-pad on it. The printing is two textures drawn by gamecube_print.py: the console from above (planar-mapped onto every
face facing up: the lid's window and logo, the buttons' names), the front panel, the controller's top and swatches;
and the mini disc's two sides.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer,
the top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the
set holding the lid (its origin on its hinge), the disc (waiting in its well, shrunk to nothing), POWER, OPEN, the
power light (shrunk to nothing), and the controller's stick, C stick, A and B.

The `focused` clip (8 s, looping) plays a game: OPEN goes in and the lid springs up; the disc drops onto the spindle
and the lid shuts; POWER goes in and the light comes on; the stick circles, the C stick flicks, A and B are pressed.
Then OPEN again: the lid springs up, the disc rises out and goes, the lid shuts, and POWER goes off.

Five materials (case, grey, dark, print, disc) and two textures, within the system model budget. Run from the repo
root:

    python tools/console-models/gamecube_print.py artifacts/gc
    blender -b --factory-startup --python tools/console-models/gamecube.py -- artifacts/gc godot/themes/console/models/systems/gc.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamecube_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.45, grey=0.55, dark=0.6, print=0.45, disc=0.2)
PAD_W = 150.0


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h, size=L.ATLAS):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / size, 1 - (ry + b / h * rh) / size)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def prism(name, outline, z0, z1, mat):
    """A solid from an (x, y) outline, from z0 to z1."""
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def disc_outline(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def cylinder_y(name, cx, cz, r, y0, y1, mat, n=20):
    """A cylinder along y, its axis at (cx, cz), from y0 to y1."""
    ring = [(cx + r * math.cos(2 * math.pi * k / n), cz + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return solid(name, [[(x, y, z) for x, z in ring] for y in (y0, y1)], mat)


# ---- The console -----------------------------------------------------------------------------------------------------

def body(m):
    """The cube and its front panel, cut for the seam, the vents, the ports and slots, the lid's recess, the disc's
    well and the buttons' sockets; its top and the panel printed."""
    w, d, h = L.WIDTH, L.DEPTH, L.HEIGHT
    cube = box("gc", -w / 2, w / 2, 0.0, d, 0.0, h, m["case"])
    bevel(cube, L.EDGE, segments=3)
    p = L.PANEL
    (x0, x1), (z0, z1) = p["x"], p["z"]
    face = [(x, z) for x, z in rounded((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, 6.0, 4)]
    panel = solid("panel", [[(x, y, z) for x, z in face] for y in (-p["out"], 6.0)], m["grey"])
    bevel(panel, 1.0, segments=2)
    boolean(cube, panel, "UNION")

    s = L.SEAM                              # round the cube's faces, passing behind the panel
    ring = box("seam", -w / 2 - 5.0, w / 2 + 5.0, -0.5, d + 5.0, s["z"] - 0.5, s["z"] + 0.5, m["dark"])
    boolean(ring, box("inner", -w / 2 + s["depth"], w / 2 - s["depth"], s["depth"], d - s["depth"], s["z"] - 2.0,
                      s["z"] + 2.0, m["dark"]))
    boolean(cube, ring)

    v = L.VENT
    holes = []
    for side in (-1, 1):
        for i in range(v["columns"]):
            for j in range(v["rows"]):
                y = v["y"] + (i - (v["columns"] - 1) / 2) * v["pitch"]
                z = v["z"] + (j - (v["rows"] - 1) / 2) * v["pitch"]
                x = side * w / 2
                holes.append(box("vent", x - v["depth"], x + v["depth"], y - v["hole"] / 2, y + v["hole"] / 2,
                                 z - v["hole"] / 2, z + v["hole"] / 2, m["dark"]))
    boolean(cube, join(holes, "vents"))
    boolean(cube, join([cylinder_y("port", x, L.PORTS["z"], L.PORTS["r"], -p["out"] - 3.0, L.PORTS["depth"], m["dark"])
                        for x in L.PORTS["x"]], "ports"))
    sw, sh = L.SLOTS["size"]
    boolean(cube, join([box("slot", x - sw / 2, x + sw / 2, -p["out"] - 3.0, 4.0, L.SLOTS["z"] - sh / 2,
                            L.SLOTS["z"] + sh / 2, m["dark"]) for x in L.SLOTS["x"]], "slots"))

    lid = L.LID
    (lx0, lx1), (ly0, ly1) = lid["x"], lid["y"]
    recess = [(x, y) for x, y in rounded(0.0, (ly0 + ly1) / 2, lx1 - lx0, ly1 - ly0, 4.0, 3)]
    cutter = prism("recess", recess, h - lid["thickness"], h + 5.0, m["case"])
    boolean(cutter, corners(m, 3.0))
    boolean(cube, cutter)
    wx, wy = L.WINDOW["at"]
    boolean(cube, prism("well", disc_outline(wx, wy, L.DISC["r"] + 3.0), h - 30.0, h - lid["thickness"] + 0.5,
                        m["dark"]))
    boolean(cube, join([prism("socket", disc_outline(x, y, r + 1.6), h - 1.6, h + 5.0, m["case"])
                        for x, y, r in L.BUTTONS.values()], "sockets"))

    paint(cube, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "case" and c.z > h - 2.0)
    pw, ph = x1 - x0, z1 - z0
    face_uv = atlas_uv(L.REGIONS["panel"], pw, ph)
    paint(cube, m["print"], lambda co: face_uv(co.x - x0, z1 - co.z),
          lambda c, n, name: n.y < -0.9 and name == "grey" and c.y < -p["out"] + 0.3)
    return cube


def handle(m):
    """The handle: a half ring round the back, a band standing on its edge, leaning back; its pivots on the sides."""
    cx, cy, cz = L.HANDLE["at"]
    r, bw, t = L.HANDLE["r"], L.HANDLE["width"], L.HANDLE["thickness"]
    rings = []
    for k in range(25):
        a = math.radians(180.0 * k / 24)
        out = Vector((math.cos(a), math.sin(a), 0.0))
        rings.append([Vector((0.0, 0.0, 0.0)) + out * rr + Vector((0.0, 0.0, dz)) for rr, dz in
                      ((r - t / 2, -bw / 2), (r + t / 2, -bw / 2), (r + t / 2, bw / 2), (r - t / 2, bw / 2))])
    band = solid("handle", rings, m["dark"])
    bevel(band, 1.5, segments=2)
    band.data.transform(Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(math.radians(L.HANDLE["tilt"]), 4, "X"))
    pivots = [cylinder_x("pivot", side * (L.WIDTH / 2), cy, cz, 7.0, side, m) for side in (-1, 1)]
    return [band] + pivots


def cylinder_x(name, x, y, z, r, side, m, n=16):
    ring = [(y + r * math.cos(2 * math.pi * k / n), z + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    part = solid(name, [[(xx, yy, zz) for yy, zz in ring] for xx in (x - side * 1.0, x + side * 3.0)], m["dark"])
    bevel(part, 0.8, segments=1)
    return part


def corners(m, gap):
    """The lid's corners cut round the buttons: a cylinder round each, gap wider than the button's socket."""
    return join([prism("corner", disc_outline(x, y, r + 1.6 + gap), L.HEIGHT - 20.0, L.HEIGHT + 10.0, m["case"])
                 for x, y, r in L.BUTTONS.values()], "corners")


def lid_part(m):
    """The lid, its origin on its hinge along the back: the slab in its recess, its top printed."""
    lid = L.LID
    (lx0, lx1), (ly0, ly1) = lid["x"], lid["y"]
    outline = [(x, y) for x, y in rounded(0.0, (ly0 + ly1) / 2, lx1 - lx0 - 0.8, ly1 - ly0 - 0.8, 3.6, 3)]
    slab = prism("lid", outline, L.HEIGHT - lid["thickness"] + 0.4, L.HEIGHT, m["case"])
    boolean(slab, corners(m, 3.4))
    bevel(slab, 0.8, segments=2)
    paint(slab, m["print"], top_uv, lambda c, n, name: n.z > 0.9)
    hinge = Vector((0.0, lid["hinge"][0], lid["hinge"][1]))
    slab.data.transform(Matrix.Translation(-hinge))
    return slab, hinge


def button(name, r, colour, m, height=2.4):
    part = painted(prism(name, disc_outline(0.0, 0.0, r), -2.0, height, m["print"]), m, colour)
    bevel(part, 0.8, segments=2)
    return part


def light(m):
    x = L.PORTS["x"][0]
    z = L.PORTS["z"] + L.PORTS["r"] + 13.0
    y = -L.PANEL["out"] - 0.2
    lit = painted(box("light", x - 1.2, x + 1.2, y - 0.3, y, z - 1.2, z + 1.2, m["print"]), m, "lit")
    lit.data.transform(Matrix.Translation((-x, -y, -z)))
    return lit, Vector((x, y, z))


def disc(m):
    """The mini disc, its middle at its origin, its label up."""
    r, t = L.DISC["r"], L.DISC["thickness"]
    part = prism("disc", disc_outline(0.0, 0.0, r, 40), -t / 2, t / 2, m["disc"])
    top = atlas_uv(L.DISC_REGIONS["label"], 2 * r, 2 * r, L.DISC_ATLAS)
    bottom = atlas_uv(L.DISC_REGIONS["data"], 2 * r, 2 * r, L.DISC_ATLAS)
    paint(part, m["disc"], lambda co: top(co.x + r, r - co.y), lambda c, n, name: n.z > 0.9)
    paint(part, m["disc"], lambda co: bottom(co.x + r, r + co.y), lambda c, n, name: n.z <= 0.9)
    return part


# ---- The controller --------------------------------------------------------------------------------------------------

def pad_outline():
    points = list(L.PAD_OUTLINE)
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    return points if area > 0 else list(reversed(points))


def pad_frame():
    """The controller's frame: its local (x, y), y from its grips' tips (towards the player)."""
    (px, py), turn = L.PAD["at"], L.PAD["turn"]
    return (Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
            @ Matrix.Translation((0.0, -L.PAD["length"] / 2, 0.0)))


def kidney(name, x, y, w, h, turn, m):
    outline = [(x + a * math.cos(math.radians(turn)) - b * math.sin(math.radians(turn)),
                y + a * math.sin(math.radians(turn)) + b * math.cos(math.radians(turn)))
               for a, b in rounded(0.0, 0.0, w, h, min(w, h) / 2 - 0.2, 4)]
    t = L.PAD["thickness"]
    part = painted(prism(name, outline, t - 3.0, t + 2.6, m["print"]), m, "white")
    bevel(part, 0.8, segments=2)
    return part


def controller(m):
    """The controller's body and its fixed parts (X, Y, START, the D-pad, the shoulders), at its place."""
    p = L.PAD
    t = p["thickness"]
    body = prism("controller", pad_outline(), 0.0, t, m["case"])
    bevel(body, 9.0, segments=5, angle=30)
    top = atlas_uv(L.REGIONS["pad"], PAD_W, p["length"])
    paint(body, m["print"], lambda co: top(co.x + PAD_W / 2, p["length"] - co.y), lambda c, n, name: n.z > 0.8)
    parts = [body, kidney("x", *p["x"], m), kidney("y", *p["y"], m)]
    sx, sy, sr = p["start"]
    start = button("start", sr, "white", m)
    start.data.transform(Matrix.Translation((sx, sy, t)))
    parts.append(start)
    dx, dy, span, arm = p["dpad"]
    cross = [(arm / 2, -span / 2), (arm / 2, -arm / 2), (span / 2, -arm / 2), (span / 2, arm / 2), (arm / 2, arm / 2),
             (arm / 2, span / 2), (-arm / 2, span / 2), (-arm / 2, arm / 2), (-span / 2, arm / 2), (-span / 2, -arm / 2),
             (-arm / 2, -arm / 2), (-arm / 2, -span / 2)]
    dpad = painted(prism("dpad", [(dx + x, dy + y) for x, y in cross], t - 3.0, t + 2.4, m["print"]), m, "white")
    bevel(dpad, 0.6, segments=1)
    parts.append(dpad)
    for side, colour in ((-1, "grey"), (1, "grey")):          # the shoulder buttons, L and R
        shoulder = painted(box("shoulder", side * 62.0 - 11.0, side * 62.0 + 11.0, 99.0, 108.0, t - 8.0, t - 1.0,
                               m["print"]), m, colour)
        bevel(shoulder, 2.5, segments=2)
        parts.append(shoulder)
    for part in parts:
        part.data.transform(pad_frame())
    return parts


def pad_parts(m):
    """The stick, the C stick, A and B, each its middle at its origin, and where each goes."""
    p = L.PAD
    t = p["thickness"]
    parts = []
    for name, (x, y, r), colour in (("a", p["a"], "green"), ("b", p["b"], "red")):
        parts.append((name, button(name, r, colour, m, 3.0), Vector((x, y, 0.0))))
    for name, (x, y), cap, colour in (("stick", p["stick"], p["cap"], "white"), ("c", p["c"], p["c_cap"], "yellow")):
        shaft = painted(prism("shaft", disc_outline(0.0, 0.0, 3.4, 16), -4.0, 6.0, m["print"]), m, "dark")
        top = painted(prism("cap", disc_outline(0.0, 0.0, cap, 24), 6.0, 10.0, m["print"]), m, colour)
        bevel(top, 1.4, segments=2)
        parts.append((name, join([shaft, top], name), Vector((x, y, 0.0))))
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


PRESSES = dict(open=(8, 184), power=(66, 228), a=(86, 100, 114, 150), b=(128,))


def lid_angle(f):
    open_ = L.LID["open"]
    if f < 50:
        return open_ * back_out(phase(f, 10, 22), 1.4)
    if f < 186:
        return open_ * (1 - smooth(phase(f, 50, 60))) + wobble(f, 60, 2.0, period=8.0, decay=3.0)
    if f < 216:
        return open_ * back_out(phase(f, 186, 198), 1.4)
    return open_ * (1 - smooth(phase(f, 216, 226))) + wobble(f, 226, 2.0, period=8.0, decay=3.0)


def timeline(f):
    # The disc: appears over the well, drops onto the spindle, spins; later rises out and goes.
    if f < 24 or f >= 214:
        spun = Pose(scale=HIDDEN)
    elif f < 34:
        spun = Pose(z=60.0, scale=appear(f, 24, 32))
    elif f < 46:
        spun = Pose(z=60.0 * (1 - ease_in(phase(f, 34, 46))))
    elif f < 200:
        spun = Pose(spin=-30.0 * (f - 46))
    else:
        spun = Pose(z=60.0 * ease_out(phase(f, 200, 208)), scale=max(HIDDEN, 1 - ease_in(phase(f, 206, 214))))

    on = 68 <= f < 230
    poses = {"lid": Pose(pitch=lid_angle(f)), "disc": spun, "light": Pose() if on else Pose(scale=HIDDEN)}
    for name, frames in PRESSES.items():
        d = max(tap(f, f0) for f0 in frames)
        poses[name] = Pose(z=-(1.4 if name in ("open", "power") else 2.0) * d)

    # The stick circles twice; the C stick flicks right and back.
    t = phase(f, 80, 140)
    lean = 18.0 * math.sin(math.pi * t)
    angle = 2 * math.pi * 2 * t
    poses["stick"] = Pose(pitch=lean * math.cos(angle), roll=lean * math.sin(angle))
    flick = math.sin(math.pi * phase(f, 158, 168)) * 18.0
    poses["c"] = Pose(roll=flick)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "gamecube_print.png"))
    discs = bpy.data.images.load(os.path.join(images, "gamecube_disc.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    textures = dict(print=printed, disc=discs)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    reset = button("reset", L.BUTTONS["reset"][2], "case", m)
    rx, ry, _ = L.BUTTONS["reset"]
    reset.data.transform(Matrix.Translation((rx, ry, L.HEIGHT - 1.0)))
    whole = join([body(m), reset] + handle(m) + controller(m), "gc")
    cover, hinge = lid_part(m)
    power, opener = button("power", L.BUTTONS["power"][2], "grey", m), button("open", L.BUTTONS["open"][2], "case", m)
    lit, lit_at = light(m)
    spinning = disc(m)
    sticks = pad_parts(m)
    for obj in [whole, cover, power, opener] + [part for _, part, _ in sticks]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(55))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("gc_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    px, py, _ = L.BUTTONS["power"]
    ox, oy, _ = L.BUTTONS["open"]
    placed = [(cover, hinge), (power, Vector((px, py, L.HEIGHT - 1.0))), (opener, Vector((ox, oy, L.HEIGHT - 1.0))),
              (lit, lit_at), (spinning, Vector(L.SPINDLE))] + [(part, where) for _, part, where in sticks]
    for part, where in placed:
        part.parent = whole
        part.location = where
    nodes = {"lid": cover, "power": power, "open": opener, "light": lit, "disc": spinning,
             **{name: part for name, part, _ in sticks}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, cover, power, opener, lit, spinning] + [part for _, part, _ in sticks]
    print(f"GameCube: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
