"""The console theme's ColecoVision system model (godot/themes/console/models/systems/colecovision.glb): the
ColecoVision, one controller in its bay and the other in front of it.

Built in Blender from the real console's proportions (colecovision_layout.py has the measurements, taken from
photographs). The console is a rounded black box: the controller bay, the cartridge panel, the slats, the power
switch's slot, RESET's recess and the cartridge slot are cut into its top, the silver band's recess into its front,
and the expansion interface's door stands out below it. Each controller is a slab with its knob (a joystick with an
aluminium cap on a collar), its twelve keys and a grey fire button down each side. The printing is one texture drawn
by colecovision_print.py (the console from above, planar-mapped onto every face facing up; its front; a controller's
top; the cartridge's label; swatches).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting in the slot, shrunk to nothing), the power switch, RESET, and the front controller's
knob, its key 1 and its fire button.

The `focused` clip (8 s, looping) plays a game: the cartridge drops into the slot, the switch slides ON; key 1 picks
the skill level, then the knob circles and the fire button goes in, again and again; RESET; then the switch slides
OFF and the cartridge comes out and goes.

Five materials (case, dark, key, cart, print) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/colecovision_print.py artifacts/colecovision
    blender -b --factory-startup --python tools/console-models/colecovision.py -- artifacts/colecovision godot/themes/console/models/systems/colecovision.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colecovision_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.6, dark=0.75, key=0.5, cart=0.5, print=0.5)
P = L.PAD


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT)
PAD_TOP = atlas_uv(L.REGIONS["pad"], P["length"], P["width"])


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z)


def pad_uv(co):
    """A controller's top, in its own frame (x along it from its middle, the knob's end at -x)."""
    return PAD_TOP(co.x + P["length"] / 2, P["width"] / 2 - co.y)


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
    """The console: the box, its top's and front's cuts, the expansion door; printed."""
    w, d, h = L.WIDTH, L.DEPTH, L.HEIGHT
    body = box("colecovision", -w / 2, w / 2, 0.0, d, 0.0, h, m["case"])
    bevel(body, L.EDGE, segments=2)
    b = L.BAY
    boolean(body, box("bay", *b["x"], *b["y"], h - b["depth"], h + 5.0, m["dark"]))
    p = L.PANEL
    boolean(body, box("panel", *p["x"], *p["y"], h - p["depth"], h + 5.0, m["case"]))
    grooves = []
    for s in L.SLATS:
        (x0, x1), (y0, y1) = s["x"], s["y"]
        step = (x1 - x0) / s["count"]
        for k in range(s["count"]):
            x = x0 + (k + 0.5) * step
            grooves.append(box("slat", x - step * 0.28, x + step * 0.28, y0, y1, h - 3.0, h + 5.0, m["dark"]))
    boolean(body, join(grooves, "slats"))
    sw = L.SWITCH
    boolean(body, box("switch_slot", *sw["x"], *sw["y"], h - 6.0, h + 5.0, m["dark"]))
    r = L.RESET
    boolean(body, box("reset_well", *r["x"], *r["y"], h - 3.0, h + 5.0, m["case"]))
    sl = L.SLOT
    boolean(body, box("slot", *sl["x"], *sl["y"], h - sl["depth"], h + 5.0, m["dark"]))
    bd = L.BAND
    boolean(body, box("band", -w / 2 + 8.0, w / 2 - 8.0, -5.0, bd["depth"], *bd["z"], m["case"]))
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "case" and c.z > h - 2.0)
    paint(body, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < bd["depth"] + 0.2 and name == "case")
    e = L.EXPANSION
    door = box("expansion", *e["x"], -e["out"], 2.0, *e["z"], m["case"])
    bevel(door, 1.5, segments=2)
    boolean(door, box("grip", (e["x"][0] + e["x"][1]) / 2 - 14.0, (e["x"][0] + e["x"][1]) / 2 + 14.0, -e["out"] - 2.0,
                      -e["out"] + 1.0, e["z"][0] + 3.0, e["z"][0] + 6.0, m["dark"]))
    return [body, door]


def switch_knob(m):
    (x0, x1), (y0, y1) = L.SWITCH["x"], L.SWITCH["y"]
    knob = box("switch", -(x1 - x0) / 2 + 1.0, (x1 - x0) / 2 - 1.0, -4.0, 4.0, -4.0, 3.0, m["case"])
    bevel(knob, 0.8, segments=1)
    return knob, Vector(((x0 + x1) / 2, y0 + 5.0, L.HEIGHT - 3.0))


def reset_button(m):
    (x0, x1), (y0, y1) = L.RESET["x"], L.RESET["y"]
    button = box("reset", -(x1 - x0) / 2 + 2.0, (x1 - x0) / 2 - 2.0, -(y1 - y0) / 2 + 2.0, (y1 - y0) / 2 - 2.0, -3.0,
                 1.5, m["case"])
    bevel(button, 1.2, segments=2)
    boolean(button, prism("dimple", circle(0.0, 0.0, 3.0, 16), 0.8, 3.0, m["dark"]))
    return button, Vector(((x0 + x1) / 2, (y0 + y1) / 2, L.HEIGHT - 1.0))


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, its label (-y) to the front, ribs down its sides."""
    w, t, h = L.CART["size"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["cart"])
    bevel(shell, 1.5, segments=2)
    ribs = [box("rib", side * w / 2 - 1.0, side * w / 2 + 1.0, -t / 2 - 1.0, t / 2 + 1.0, z - 0.6, z + 0.6, m["dark"])
            for side in (-1, 1) for z in (h - 8.0 - 4.0 * k for k in range(L.CART["ribs"]))]
    boolean(shell, join(ribs, "ribs"))
    lw, lh = L.CART["label"]
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    x0, x1, z0, z1 = -lw / 2, lw / 2, h - 5.0 - lh, h - 5.0
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]                  # wound to face -y
    face = bm.faces.new([bm.verts.new((x, -t / 2 - 0.12, z)) for x, z in corners])
    uv = atlas_uv(L.REGIONS["label"], lw, lh)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = uv(x - x0, z1 - z)
    sticker = new_object("label", bm, m["print"])
    return join([shell, sticker], "cartridge")


# ---- The controllers -------------------------------------------------------------------------------------------------

def key_rects():
    """The twelve keys' (name, middle along, middle across) in a controller's frame."""
    pitch_across, pitch_along, _, _ = P["keys"]
    names = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"]
    return [(names[row * 3 + col], P["first_row"] + row * pitch_along, (col - 1) * pitch_across)
            for row in range(4) for col in range(3)]


def a_key(name, m):
    """A key, its top's middle at its origin, its top printed."""
    _, _, w, h = P["keys"]
    part = box(f"key_{name}", -h / 2, h / 2, -w / 2, w / 2, -4.0, 0.0, m["key"])
    bevel(part, 0.8, segments=1)
    return part


def side_button(m, side):
    x, length, out = P["side"]
    w = P["width"]
    part = painted(box("fire", -length / 2, length / 2, -1.0, out, -3.0, 3.0, m["print"]), m, "grey")
    bevel(part, 0.6, segments=1)
    part.data.transform(Matrix.Rotation(math.radians(0 if side > 0 else 180), 4, "Z"))
    return part, Vector((x, side * w / 2, P["height"] * 0.5))


def knob(m):
    """The knob, its origin at its foot (it tilts about there): the shaft, the black cap and its aluminium top."""
    _, r, height = P["knob"]
    shaft = prism("shaft", circle(0.0, 0.0, r * 0.45, 16), -2.0, height * 0.5, m["case"])
    cap = prism("cap", circle(0.0, 0.0, r, 28), height * 0.45, height, m["case"])
    bevel(cap, 1.6, segments=2)
    top = painted(prism("cap_top", circle(0.0, 0.0, r * 0.8, 28), height - 0.5, height + 0.3, m["print"]), m,
                  "aluminium")
    return join([shaft, cap, top], "knob")


def controller(m, frame, moving):
    """A controller at frame: its body, collar and keys (the knob, key 1 and the fire button apart if moving, each
    with where it goes)."""
    length, width, height = P["length"], P["width"], P["height"]
    body = prism("controller", rounded(0.0, 0.0, length, width, 5.0, 3), 0.0, height, m["case"])
    bevel(body, 2.0, segments=2)
    kx, kr, _ = P["knob"]
    collar = prism("collar", circle(kx, 0.0, kr + 4.0, 28), height - 1.0, height + 4.0, m["case"])
    bevel(collar, 1.0, segments=1)
    paint(body, m["print"], pad_uv, lambda c, n, name: n.z > 0.9)
    paint(collar, m["print"], pad_uv, lambda c, n, name: n.z > 0.9)
    static = [body, collar]
    parts = {}
    for name, x, y in key_rects():
        cap = a_key(name, m)
        cap.data.transform(Matrix.Translation((x, y, height + 2.0)))
        paint(cap, m["print"], pad_uv, lambda c, n, _name: n.z > 0.9)
        if moving and name == "1":
            cap.data.transform(Matrix.Translation((-x, -y, -(height + 2.0))))
            parts["key_1"] = (cap, Vector((x, y, height + 2.0)))
        else:
            static.append(cap)
    stick = knob(m)
    for side in (-1, 1):
        button, at = side_button(m, side)
        if moving and side < 0:
            parts["fire"] = (button, at)
        else:
            button.data.transform(Matrix.Translation(at))
            static.append(button)
    if moving:
        parts["knob"] = (stick, Vector((kx, 0.0, height + 2.0)))
    else:
        stick.data.transform(Matrix.Translation((kx, 0.0, height + 2.0)))
        static.append(stick)
    for part in static:
        part.data.transform(frame)
    turn = frame.to_3x3().to_4x4()
    placed = {}
    for name, (part, at) in parts.items():
        part.data.transform(turn)
        placed[name] = (part, frame @ at)
    return static, placed


def pad_frame(spec, lift=0.0):
    (px, py), turn = spec["at"], spec["turn"]
    return Matrix.Translation((px, py, lift)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


FIRES = (92, 104, 116, 132, 148)
INWARD = Matrix.Rotation(math.radians(L.FREE_PAD["turn"]), 3, "Z") @ Vector((0.0, 1.0, 0.0))   # the fire button's travel


def timeline(f):
    if f < 6 or f >= 222:
        cart = Pose(scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=80.0, scale=appear(f, 6, 14))
    elif f < 28:
        cart = Pose(z=80.0 * (1 - ease_in(phase(f, 16, 28))))
    elif f < 204:
        cart = Pose(squash=0.04 * math.sin(math.pi * phase(f, 28, 34)))
    else:
        cart = Pose(z=80.0 * ease_out(phase(f, 204, 214)), scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    on = smooth(phase(f, 36, 42)) * (1 - smooth(phase(f, 192, 198)))
    t = phase(f, 78, 160)
    lean = 16.0 * math.sin(math.pi * t)
    angle = 2 * math.pi * 2.5 * t
    return {"cartridge": cart, "switch": Pose(y=L.SWITCH["travel"] * on), "reset": Pose(z=-1.5 * tap(f, 172)),
            "key_1": Pose(z=-1.8 * tap(f, 58)), "fire": Pose(*(INWARD * 1.4 * max(tap(f, f0) for f0 in FIRES))),
            "knob": Pose(pitch=lean * math.cos(angle), roll=lean * math.sin(angle))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "colecovision_print.png"))
    colours = dict(case=L.COLOURS["case"], dark=L.COLOURS["dark"], key=L.COLOURS["key"], cart=L.COLOURS["cart"],
                   print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    bay_static, _ = controller(m, pad_frame(L.BAY_PAD, L.HEIGHT - L.BAY["depth"]), moving=False)
    free_static, free_parts = controller(m, pad_frame(L.FREE_PAD), moving=True)
    whole = join(console(m) + bay_static + free_static, "colecovision")
    slider, slider_at = switch_knob(m)
    reset, reset_at = reset_button(m)
    cart = cartridge(m)
    for obj in [whole, slider, reset, cart] + [part for part, _ in free_parts.values()]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(40))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("colecovision_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    sl = L.SLOT
    seat = Vector(((sl["x"][0] + sl["x"][1]) / 2, (sl["y"][0] + sl["y"][1]) / 2, L.HEIGHT - L.CART["inserted"]))
    placed = [(slider, slider_at), (reset, reset_at), (cart, seat)] + list(free_parts.values())
    for part, where in placed:
        part.parent = whole
        part.location = where
    nodes = {"cartridge": cart, "switch": slider, "reset": reset, **{n: p for n, (p, _) in free_parts.items()}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, slider, reset, cart] + [part for part, _ in free_parts.values()]
    print(f"ColecoVision: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
