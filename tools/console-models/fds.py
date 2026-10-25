"""The console theme's Famicom Disk System model (godot/themes/console/models/systems/fds.glb): a Famicom with its RAM
adapter, sitting on its Disk System drive, a disk card going in.

Built in Blender from the real machines' proportions (fds_layout.py has the measurements, taken from photographs). The
drive is a rounded red box, the seam cut round it, the black panel, the slot's bay and the slot (deep enough for the
whole card) cut into its front. The Famicom on it: the dark red base; the white shell, its side outline extruded
across its width (the front slope, the front deck, the step, the back deck); the EJECT lever, POWER and RESET on the
front deck; the RAM adapter lying on the back deck; the two controllers standing in their docks down its sides. The
printing is one texture drawn by fds_print.py (the set from above, planar-mapped onto every face facing up; the front
slope along it; the drive's front; the controllers' faces; the disk card's two sides; swatches).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side, with controller II,
towards the viewer, the top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m)
holding the set; the set holding the disk card (waiting in the slot, shrunk to nothing), the eject button, the
operating lamp (shrunk to nothing) and POWER.

The `focused` clip (8 s, looping) plays a two-sided game: POWER slides on; the card slides into the drive, side A up,
and the lamp flickers while it reads; the eject button goes in, the card pops out, turns over in the air and goes back
in, side B up, and the lamp flickers again; then it's ejected and goes, and POWER slides off.

Five materials (red, white, dark, base, print) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/fds_print.py artifacts/fds
    blender -b --factory-startup --python tools/console-models/fds.py -- artifacts/fds godot/themes/console/models/systems/fds.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fds_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -30.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 24.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(red=0.45, white=0.5, dark=0.5, base=0.55, print=0.45)
TOP_DEPTH = 250.0    # the top region's depth (fds_print.py's)
FY, FZ = L.FAMICOM["y"], L.FAMICOM["z"]


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, TOP_DEPTH)
DRIVE_FACE = atlas_uv(L.REGIONS["drive"], L.WIDTH, L.DRIVE["height"])


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, TOP_DEPTH - co.y)


def drive_uv(co):
    return DRIVE_FACE(co.x + L.WIDTH / 2, L.DRIVE["height"] - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


# ---- The drive -------------------------------------------------------------------------------------------------------

def drive(m):
    """The drive: the box, the seam round it, its front's panel, bay and slot; its front and top printed."""
    w, d, h = L.WIDTH, L.DRIVE["depth"], L.DRIVE["height"]
    shell = box("fds", -w / 2, w / 2, 0.0, d, 0.0, h, m["red"])
    bevel(shell, L.DRIVE["r"], segments=3)
    s = L.DRIVE["seam"]
    ring = box("seam", -w / 2 - 5.0, w / 2 + 5.0, -5.0, d + 5.0, s - 0.6, s + 0.6, m["base"])
    boolean(ring, box("inner", -w / 2 + 0.9, w / 2 - 0.9, 0.9, d - 0.9, s - 2.0, s + 2.0, m["base"]))
    boolean(shell, ring)
    p, b, sl = L.PANEL, L.BAY, L.SLOT
    boolean(shell, box("panel", *p["x"], -5.0, p["depth"], *p["z"], m["dark"]))
    boolean(shell, box("bay", *b["x"], -5.0, p["depth"] + b["depth"], *b["z"], m["dark"]))
    boolean(shell, box("slot", *sl["x"], -5.0, sl["depth"], *sl["z"], m["dark"]))
    paint(shell, m["print"], drive_uv, lambda c, n, name: n.y < -0.9 and c.y < p["depth"] + 0.3)
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and c.z > h - 0.5)
    return shell


def eject_button(m):
    e = L.EJECT
    face = L.PANEL["depth"]
    button = painted(box("eject", *e["x"], face - e["out"], face + 2.0, *e["z"], m["print"]), m, "yellow")
    bevel(button, 0.6, segments=1)
    return button


def lamp(m):
    """The operating lamp lit: a disc just over the printed one, its middle at its origin."""
    x, z, r = L.LAMP
    y = L.PANEL["depth"] - 0.15
    bm = bmesh.new()
    ring = [bm.verts.new((r * 1.2 * math.cos(2 * math.pi * k / 12), 0.0, r * 1.2 * math.sin(2 * math.pi * k / 12)))
            for k in range(12)]
    bm.faces.new(ring)                                     # wound to face -y
    lit = painted(new_object("lamp", bm, m["print"]), m, "lit")
    return lit, Vector((x, y, z))


# ---- The Famicom -----------------------------------------------------------------------------------------------------

def place(obj):
    """Moves a part built in the Famicom's frame (y from its front, z from its foot) to its place on the drive."""
    obj.data.transform(Matrix.Translation((0.0, FY, FZ)))
    return obj


def band_uv():
    """The front slope's UVs: across it, and down it from its top."""
    (y0, z0), (y1, z1) = L.SLOPE
    length = L.slope_length()
    uv = atlas_uv(L.REGIONS["band"], L.WIDTH, length)

    def of(co):
        y, z = co.y - FY, co.z - FZ
        s = ((y - y1) * (y0 - y1) + (z - z1) * (z0 - z1)) / length
        return uv(co.x + L.WIDTH / 2, s)
    return of


def on_slope(c, n):
    (y0, z0), (y1, z1) = L.SLOPE
    return n.y < -0.4 and n.z > 0.4 and z0 - 0.5 < c.z - FZ < z1 + 0.5 and c.y - FY < y1 + 0.5


def famicom(m):
    """The Famicom: the base, the shell, the EJECT lever, RESET, the RAM adapter, the controllers; printed."""
    b = L.BASE
    base = place(box("base", -b["x"], b["x"], 2.0, 218.0, 0.0, b["height"], m["base"]))
    bevel(base, 1.5, segments=2)
    shell = place(prism_x("famicom", L.shell_profile(), -74.0, 74.0, m["white"]))
    bevel(shell, 1.5, segments=2)
    paint(shell, m["print"], band_uv(), lambda c, n, name: on_slope(c, n))
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.5 and not on_slope(c, n))

    lv = L.LEVER
    lever = place(prism_x("lever", [(lv["y"][0], 35.0), (lv["y"][1], 37.0), (lv["y"][1], 52.0),
                                    (lv["y"][1] - 9.0, lv["top"]), (lv["y"][0] + 7.0, lv["top"])],
                          *lv["x"], m["red"]))
    bevel(lever, 1.0, segments=2)
    rx, ry = L.RESET["at"]
    rw, rd, rh = L.RESET["size"]
    reset = place(box("reset", rx - rw / 2, rx + rw / 2, ry - rd / 2, ry + rd / 2, 34.0, 36.0 + rh, m["red"]))
    bevel(reset, 0.8, segments=1)
    a = L.ADAPTER
    adapter = place(box("adapter", *a["x"], *a["y"], 43.0, a["top"], m["dark"]))
    bevel(adapter, 2.0, segments=2)
    paint(adapter, m["print"], top_uv, lambda c, n, name: n.z > 0.9)
    t = L.TAB
    tab = place(box("tab", *t["x"], -t["out"], 3.0, *t["z"], m["red"]))
    bevel(tab, 0.8, segments=1)

    c = L.CONTROLLERS
    pads = []
    for side, region in ((-1, "pad1"), (1, "pad2")):
        x0, x1 = (c["x"][0], c["x"][1]) if side > 0 else (-c["x"][1], -c["x"][0])
        pad = place(box("controller", x0, x1, *c["y"], *c["z"], m["red"]))
        bevel(pad, 3.0, segments=2)
        face = atlas_uv(L.REGIONS[region], c["y"][1] - c["y"][0], c["z"][1] - c["z"][0])
        (y0, y1), (z0, z1) = c["y"], c["z"]
        if side > 0:                                       # seen from the right: the front to the left
            uv = (lambda f: lambda co: f(co.y - FY - y0, z1 - (co.z - FZ)))(face)
        else:                                              # seen from the left: the front to the right
            uv = (lambda f: lambda co: f(y1 - (co.y - FY), z1 - (co.z - FZ)))(face)
        paint(pad, m["print"], uv, lambda cc, n, name, s=side: n.x * s > 0.9)
        pads.append(pad)
    return [base, shell, lever, reset, adapter, tab] + pads


def power_slider(m):
    px, py = L.POWER["at"]
    w, d, h = L.POWER["size"]
    slider = box("power", -w / 2, w / 2, -d / 2, d / 2, -1.5, h - 1.5, m["red"])
    bevel(slider, 0.8, segments=1)
    deck_z = 34.0 + (py - L.DECK[0][0]) / (L.DECK[1][0] - L.DECK[0][0]) * 3.0
    return slider, Vector((px, py + FY, deck_z + FZ))


# ---- The disk card ---------------------------------------------------------------------------------------------------

def disk(m):
    """The disk card, its middle at its origin, lying flat, its window's end towards +y (into the slot), side A up."""
    (w, l), t = L.DISK["size"], L.DISK["thickness"]
    card = box("disk", -w / 2, w / 2, -l / 2, l / 2, -t / 2, t / 2, m["print"])
    bevel(card, 0.5, segments=1)
    side_a = atlas_uv(L.REGIONS["side_a"], w, l)
    side_b = atlas_uv(L.REGIONS["side_b"], w, l)
    paint(card, m["print"], lambda co: side_a(co.x + w / 2, l / 2 - co.y), lambda c, n, name: n.z > 0.9)
    paint(card, m["print"], lambda co: side_b(w / 2 - co.x, l / 2 - co.y), lambda c, n, name: n.z < -0.9)
    paint(card, m["print"], swatch("yellow"), lambda c, n, name: abs(n.z) <= 0.9)
    return card


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 100.0          # how far in front of its seat the card waits: wholly out of the slot


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def card(f):
    if f < 10 or f >= 226:
        return Pose(scale=HIDDEN)
    if f < 20:
        return Pose(y=-OUT, scale=appear(f, 10, 18))
    if f < 102:
        return Pose(y=-OUT * (1 - smooth(phase(f, 20, 36))))
    if f < 110:
        return Pose(y=-30.0 * back_out(phase(f, 102, 108)))
    if f < 118:                                            # out, and up
        t = smooth(phase(f, 110, 118))
        return Pose(y=-30.0 - (OUT - 30.0) * t, z=30.0 * t)
    if f < 136:                                            # turned over in the air: side B up
        return Pose(y=-OUT, z=30.0, roll=180.0 * smooth(phase(f, 118, 136)))
    if f < 144:
        return Pose(y=-OUT, z=30.0 * (1 - smooth(phase(f, 136, 144))), roll=180.0)
    if f < 206:
        return Pose(y=-OUT * (1 - smooth(phase(f, 144, 160))), roll=180.0)
    if f < 214:
        return Pose(y=-30.0 * back_out(phase(f, 206, 212)), roll=180.0)
    t = ease_out(phase(f, 214, 222))
    return Pose(y=-30.0 - 40.0 * t, z=30.0 * t, roll=180.0, scale=max(HIDDEN, 1 - ease_in(phase(f, 218, 226))))


def timeline(f):
    reading = (38 <= f < 92 or 162 <= f < 198) and (f // 3) % 5 != 4
    press = max(smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 4, f0 + 7))) for f0 in (100, 204))
    on = smooth(phase(f, 4, 8)) * (1 - smooth(phase(f, 230, 234)))
    return {"disk": card(f), "lamp": Pose() if reading else Pose(scale=HIDDEN), "eject": Pose(y=2.0 * press),
            "power": Pose(x=L.POWER["travel"] * on)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "fds_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join([drive(m)] + famicom(m), "fds")
    button = eject_button(m)
    lit, lit_at = lamp(m)
    slider, slider_at = power_slider(m)
    card_ = disk(m)
    for obj in [whole, button, slider, card_]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(40))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("fds_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    sl = L.SLOT
    (w, length), t = L.DISK["size"], L.DISK["thickness"]
    seat = Vector(((sl["x"][0] + sl["x"][1]) / 2, -L.DISK["inside"] + length / 2, (sl["z"][0] + sl["z"][1]) / 2))
    for part, where in ((lit, lit_at), (slider, slider_at), (card_, seat)):
        part.parent = whole
        part.location = where
    button.parent = whole
    nodes = {"disk": card_, "lamp": lit, "eject": button, "power": slider}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, button, lit, slider, card_]
    print(f"FDS: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
