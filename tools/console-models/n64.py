"""The console theme's Nintendo 64 system model (godot/themes/console/models/systems/n64.glb): the console and its
controller.

Built in Blender from the real console's proportions (n64_layout.py has the measurements, taken from photographs).
The console is lofted: the base (its foot band, its flat front) with a round pod at each corner; on it the upper shell,
sloping in to its plateau; and the hump, joined onto the plateau and running to the back, cut for the cartridge slot
and the vent's slots in front of it. POWER's well and RESET's recess are cut into the plateau, the memory expansion's
lid stands on it, and the four controller ports stand out of the front. The controller is its outline (traced from a
photograph) lofted into a rounded slab, its buttons, D-pad and stick on it. The printing is one texture drawn by
n64_print.py (the console from above, planar-mapped onto every face facing up; its front; the controller's top; the
cartridge's label; and swatches).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting in the slot, shrunk to nothing), the slot's two dust flaps (each on its hinge), POWER's
knob, RESET, the power light (shrunk to nothing), and the controller's stick, A, B and START.

The `focused` clip (8 s, looping) plays a game: the cartridge drops into the slot, the flaps swinging down out of its
way; POWER slides on and the light comes on; the stick swings round and A, B and START are pressed; RESET goes in.
Then POWER slides off, and the cartridge comes out and goes, the flaps swinging shut.

Five materials (case, controller, dark, cart, print) and one texture, within the system model budget. Run from the
repo root:

    python tools/console-models/n64_print.py artifacts/n64
    blender -b --factory-startup --python tools/console-models/n64.py -- artifacts/n64 godot/themes/console/models/systems/n64.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n64_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, controller=0.5, dark=0.8, cart=0.55, print=0.5)
FRONT_H = 36.0
PAD_W = 160.0


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
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


# ---- Shapes ----------------------------------------------------------------------------------------------------------

def plan(x, y0, y1, r, z, segments=4):
    """A rounded rectangle at height z, x from -x to x and y from y0 to y1, anticlockwise seen from above."""
    points = []
    for cx, cy, a0 in ((x - r, y1 - r, 0), (-x + r, y1 - r, 90), (-x + r, y0 + r, 180), (x - r, y0 + r, 270)):
        for k in range(segments + 1):
            a = math.radians(a0 + 90 * k / segments)
            points.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    return points


def ellipse(cx, cy, rx, ry, z, n=24):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n), z) for k in range(n)]


def prism(name, outline, z0, z1, mat):
    """A solid from an (x, y) outline, from z0 to z1."""
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def hump_plan():
    """The hump's plan, (x, y) anticlockwise from above: its back edge, its sides narrowing to the front, the front's
    round end."""
    (bx, by), (fx, fy), tip = L.HUMP["back"], L.HUMP["front"], L.HUMP["tip"]
    front = [(-fx * math.cos(math.radians(a)), fy - (fy - tip) * math.sin(math.radians(a))) for a in range(0, 181, 15)]
    return [(bx, by), (-bx, by)] + front


# ---- The console -----------------------------------------------------------------------------------------------------

def base(m):
    """The base and its pods, its front printed (the window, the ports' faces)."""
    b = L.BASE
    lower = solid("n64", [plan(b["x"] - 4.0, b["front"] + 4.0, b["back"] - 4.0, b["r"], 0.0),
                          plan(b["x"] - 4.0, b["front"] + 4.0, b["back"] - 4.0, b["r"], L.FOOT),
                          plan(b["x"], b["front"], b["back"], b["r"], L.FOOT + 0.01),
                          plan(b["x"], b["front"], b["back"], b["r"], b["z"])], m["case"])
    bevel(lower, 2.0, segments=2)
    paint(lower, m["dark"], swatch("dark"), lambda c, n, name: c.z < L.FOOT - 0.2)
    pods = []
    for x, y, rx, ry, h in (L.PODS["front"], L.PODS["back"]):
        for side in (-1, 1):
            pod = solid("pod", [ellipse(side * x, y, rx - 3.0, ry - 3.0, 0.0), ellipse(side * x, y, rx, ry, 4.0),
                                ellipse(side * x, y, rx, ry, h - 4.0), ellipse(side * x, y, rx - 4.0, ry - 4.0, h)],
                        m["case"])
            for p in pod.data.polygons:
                p.use_smooth = True
            pods.append(pod)
    whole = join([lower] + pods, "base")
    paint(whole, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and abs(c.x) < 80.0 and name == "case")
    return whole


def shell(m):
    """The upper shell and the hump on it, cut for the slot, the vents, POWER's well and RESET's recess; its top
    printed."""
    rings = [plan(x, y0, y1, 20.0, z) for z, x, y0, y1 in L.SHELL]
    rings[0] = [(x, y, z - 2.0) for x, y, z in rings[0]]
    upper = solid("shell", rings, m["case"])
    bevel(upper, 3.0, segments=2)
    h = L.HUMP
    outline = hump_plan()
    hump = solid("hump", [[(x, y, h["base"]) for x, y in outline], [(x, y, h["top"] - 3.0) for x, y in outline],
                          [(x, y, h["top"]) for x, y in inset(outline, h["inset"])]], m["case"])
    boolean(upper, hump, "UNION")
    s = L.SLOT
    boolean(upper, box("slot", *s["x"], *s["y"], s["bottom"], L.HEIGHT + 10.0, m["dark"]))
    v = L.VENT
    step = (v["x"][1] - v["x"][0]) / (v["count"] - 1)
    boolean(upper, join([box("vent", v["x"][0] + k * step - v["width"] / 2, v["x"][0] + k * step + v["width"] / 2,
                             *v["y"], L.HEIGHT - v["depth"], L.HEIGHT + 5.0, m["dark"]) for k in range(v["count"])],
                        "vents"))
    px, py = L.POWER["at"]
    ww, wd = L.POWER["well"]
    boolean(upper, prism("well", [(px + x, py + y) for x, y in rounded(0.0, 0.0, ww, wd, ww / 2 - 0.5, 4)],
                         L.PLATEAU - 6.0, L.PLATEAU + 10.0, m["dark"]))
    rx, ry = L.RESET["at"]
    rw, rd, _ = L.RESET["size"]
    boolean(upper, prism("reset_well", [(rx + x, ry + y) for x, y in rounded(0.0, 0.0, rw + 2.0, rd + 2.0, rw / 2, 4)],
                         L.PLATEAU - 2.0, L.PLATEAU + 10.0, m["case"]))
    paint(upper, m["print"], top_uv, lambda c, n, name: n.z > 0.5 and name == "case")
    lx, ly = L.LID["at"]
    lw, ld, lh = L.LID["size"]
    lid = prism("lid", [(lx + x, ly + y) for x, y in rounded(0.0, 0.0, lw, ld, 4.0, 3)], L.PLATEAU - 1.0,
                L.PLATEAU + lh, m["case"])
    bevel(lid, 0.6, segments=1)
    paint(lid, m["print"], top_uv, lambda c, n, name: n.z > 0.5)
    return [upper, lid]


def ports(m):
    """The four controller ports, standing out of the front; their faces printed (the grey rim, the three holes)."""
    w, h, out = L.PORTS["size"]
    parts = []
    for x in L.PORTS["x"]:
        ring = [(x + a, z) for a, z in rounded(0.0, L.PORTS["z"], w, h, h / 2 - 0.5, 4)]
        port = solid("port", [[(a, y, z) for a, z in ring] for y in (L.BASE["front"] - out, L.BASE["front"] + 1.0)],
                     m["print"])
        bevel(port, 0.8, segments=1)
        paint(port, m["print"], swatch("grey"), lambda c, n, name: True)
        paint(port, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
        parts.append(port)
    return parts


def flaps(m):
    """The slot's two dust flaps, each its origin on its hinge along the slot's front or back edge."""
    (x0, x1), (y0, y1) = L.SLOT["x"], L.SLOT["y"]
    middle, top = (y0 + y1) / 2, L.SLOT["flap"]
    parts = {}
    for name, a, b, hinge_y in (("flap_front", y0 + 0.3, middle - 0.15, y0), ("flap_back", middle + 0.15, y1 - 0.3, y1)):
        flap = painted(box(name, x0 + 3.0, x1 - 3.0, a, b, top - 1.2, top, m["print"]), m, "grey")
        hinge = Vector((0.0, hinge_y, top - 0.6))
        flap.data.transform(Matrix.Translation(-hinge))
        parts[name] = (flap, hinge)
    return parts


def power_knob(m):
    """POWER's knob, its middle at its origin, resting at OFF (the front of its well)."""
    w, d, h = L.POWER["knob"]
    knob = solid("power", [[(x, y, z) for x, y in rounded(0.0, 0.0, w, d, w / 2 - 0.5, 4)] for z in (-6.0, h)],
                 m["case"])
    bevel(knob, 0.8, segments=1)
    for k in range(4):                                       # its grip's ridges
        ridge = box("ridge", -w / 2 + 1.5, w / 2 - 1.5, -4.5 + 3.0 * k - 0.4, -4.5 + 3.0 * k + 0.4, h - 0.5, h + 0.8,
                    m["case"])
        knob = join([knob, ridge], "power")
    px, py = L.POWER["at"]
    return knob, Vector((px, py - L.POWER["travel"] / 2, L.PLATEAU))


def reset_button(m):
    w, d, h = L.RESET["size"]
    button = solid("reset", [[(x, y, z) for x, y in rounded(0.0, 0.0, w, d, w / 2 - 0.5, 4)] for z in (-3.0, h - 1.0)],
                   m["case"])
    bevel(button, 1.2, segments=2)
    rx, ry = L.RESET["at"]
    return button, Vector((rx, ry, L.PLATEAU - 1.0))


def power_light(m):
    lx, lz, (lw, lh) = L.LIGHT
    y = L.BASE["front"] - 0.2
    lit = painted(box("light", lx - lw / 2 - 0.2, lx + lw / 2 + 0.2, y - 0.3, y, lz - lh / 2 - 0.2, lz + lh / 2 + 0.2,
                      m["print"]), m, "lit")
    middle = Vector((lx, y - 0.15, lz))
    lit.data.transform(Matrix.Translation(-middle))
    return lit, middle


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, its label (-y) to the front: its arched top, the label."""
    w, t, h = L.CART["size"]
    lw, lh = L.CART["label"]
    outline = [(-w / 2, 0.0), (w / 2, 0.0)] + [(w / 2 * math.cos(math.radians(a)), h + L.CART["arch"] *
                                                math.sin(math.radians(a))) for a in range(0, 181, 15)]
    cart = solid("cartridge", [[(x, y, z) for x, z in outline] for y in (-t / 2, t / 2)], m["cart"])
    bevel(cart, 1.5, segments=2)
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    x0, x1, z0, z1 = -lw / 2, lw / 2, h - 6.0 - lh, h - 6.0
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]                  # wound to face -y
    face = bm.faces.new([bm.verts.new((x, -t / 2 - 0.12, z)) for x, z in corners])
    uv = atlas_uv(L.REGIONS["label"], lw, lh)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = uv(x - x0, z1 - z)
    sticker = new_object("label", bm, m["print"])
    return join([cart, sticker], "cartridge")


# ---- The controller --------------------------------------------------------------------------------------------------

def pad_outline():
    """The controller's whole outline, (x, y) anticlockwise from above, y from its middle prong's tip."""
    right = L.PAD_OUTLINE
    left = [(-x, y) for x, y in reversed(right[1:-1])]
    points = right + left
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    return points if area > 0 else list(reversed(points))


def pad_frame():
    """The controller's frame: its local (x, y) (y from its middle prong's tip, the prongs towards the player)."""
    (px, py), turn = L.PAD["at"], L.PAD["turn"]
    return (Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
            @ Matrix.Translation((0.0, -L.PAD["length"] / 2, 0.0)))


def controller(m):
    """The controller's body and its fixed buttons, at its place."""
    p = L.PAD
    t = p["thickness"]
    outline = pad_outline()
    body = prism("controller", outline, 0.0, t, m["controller"])
    bevel(body, 5.5, segments=4, angle=30)
    top = atlas_uv(L.REGIONS["pad"], PAD_W, p["length"])
    paint(body, m["print"], lambda co: top(co.x + PAD_W / 2, p["length"] - co.y), lambda c, n, name: n.z > 0.8)
    parts = [body]
    dx, dy, span, arm = p["dpad"]
    cross = [(arm / 2, -span / 2), (arm / 2, -arm / 2), (span / 2, -arm / 2), (span / 2, arm / 2), (arm / 2, arm / 2),
             (arm / 2, span / 2), (-arm / 2, span / 2), (-arm / 2, arm / 2), (-span / 2, arm / 2), (-span / 2, -arm / 2),
             (-arm / 2, -arm / 2), (-arm / 2, -span / 2)]
    dpad = painted(prism("dpad", [(dx + x, dy + y) for x, y in cross], t - 3.0, t + 2.6, m["print"]), m, "dpad")
    bevel(dpad, 0.6, segments=1)
    parts.append(dpad)
    for x, y in p["c"]:
        parts.append(button("c", x, y, p["c_r"], m, "yellow"))
    for part in parts:
        part.data.transform(pad_frame())
    return parts


def button(name, x, y, r, m, colour, height=3.2):
    disc = [(x + r * math.cos(2 * math.pi * k / 20), y + r * math.sin(2 * math.pi * k / 20)) for k in range(20)]
    part = painted(prism(name, disc, L.PAD["thickness"] - 3.0, L.PAD["thickness"] + height, m["print"]), m, colour)
    bevel(part, 0.8, segments=2)
    return part


def pad_parts(m):
    """The stick, A, B and START, each its middle at its origin, and where each goes."""
    p = L.PAD
    t = p["thickness"]
    parts = []
    for name, (x, y, r), colour in (("a", p["a"], "blue"), ("b", p["b"], "green"), ("start", p["start"], "red")):
        part = button(name, 0.0, 0.0, r, m, colour)
        part.data.transform(Matrix.Translation((0.0, 0.0, -t)))
        parts.append((name, part, Vector((x, y, 0.0))))
    sx, sy = p["stick"]
    shaft = painted(prism("shaft", [(3.2 * math.cos(2 * math.pi * k / 16), 3.2 * math.sin(2 * math.pi * k / 16))
                                    for k in range(16)], t - 4.0, t + 6.0, m["print"]), m, "well")
    cap = painted(prism("cap", [(p["cap"] * math.cos(2 * math.pi * k / 24), p["cap"] * math.sin(2 * math.pi * k / 24))
                                for k in range(24)], t + 6.0, t + 10.0, m["print"]), m, "cap")
    bevel(cap, 1.4, segments=2)
    stick = join([shaft, cap], "stick")
    stick.data.transform(Matrix.Translation((0.0, 0.0, -t)))
    parts.append(("stick", stick, Vector((sx, sy, 0.0))))
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


PRESSES = dict(a=(78, 96, 104, 140), b=(118, 124), start=(60, 168), reset=(176,))


def timeline(f):
    # The cartridge: appears over the slot, drops in with a bump; later rises out and goes.
    if f < 6 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=80.0, scale=appear(f, 6, 14))
    elif f < 28:
        cart = Pose(z=80.0 * (1 - ease_in(phase(f, 16, 28))))
    elif f < 206:
        cart = Pose(squash=0.05 * math.sin(math.pi * phase(f, 28, 34)))
    else:
        cart = Pose(z=80.0 * ease_out(phase(f, 206, 218)), scale=max(HIDDEN, 1 - ease_in(phase(f, 216, 226))))

    swing = 85.0 * smooth(phase(f, 18, 23)) * (1 - smooth(phase(f, 216, 224)))
    on = smooth(phase(f, 36, 42)) * (1 - smooth(phase(f, 196, 202)))
    poses = {"cartridge": cart, "flap_front": Pose(pitch=-swing), "flap_back": Pose(pitch=swing),
             "power": Pose(y=L.POWER["travel"] * on), "light": Pose() if on > 0.5 else Pose(scale=HIDDEN)}

    # The stick swings round a circle and back, then flicks.
    t = phase(f, 50, 130)
    lean = 16.0 * math.sin(math.pi * t) + 12.0 * math.sin(math.pi * phase(f, 146, 160))
    angle = 2 * math.pi * 2 * t
    poses["stick"] = Pose(pitch=lean * math.cos(angle), roll=lean * math.sin(angle))
    for name, frames in PRESSES.items():
        d = max(tap(f, f0) for f0 in frames)
        poses[name] = Pose(z=-(2.4 if name == "reset" else 2.0) * d)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "n64_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join([base(m)] + shell(m) + ports(m) + controller(m), "n64")
    knob, knob_at = power_knob(m)
    reset, reset_at = reset_button(m)
    lit, lit_at = power_light(m)
    cart = cartridge(m)
    hinged = flaps(m)
    buttons = pad_parts(m)
    for obj in [whole, knob, reset, cart] + [part for _, part, _ in buttons]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(55))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("n64_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    seat = Vector((0.0, (L.SLOT["y"][0] + L.SLOT["y"][1]) / 2, L.HEIGHT - L.CART["inserted"]))
    placed = [(knob, knob_at), (reset, reset_at), (lit, lit_at), (cart, seat)] + list(hinged.values())
    placed += [(part, where) for _, part, where in buttons]
    for part, where in placed:
        part.parent = whole
        part.location = where
    nodes = {"cartridge": cart, "power": knob, "reset": reset, "light": lit,
             **{name: part for name, (part, _) in hinged.items()}, **{name: part for name, part, _ in buttons}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, knob, reset, lit, cart] + [part for part, _ in hinged.values()] + [part for _, part, _ in buttons]
    print(f"N64: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
