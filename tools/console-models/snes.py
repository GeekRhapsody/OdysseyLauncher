"""The console theme's Super Nintendo and Satellaview system models (godot/themes/console/models/systems/snes.glb and
satellaview.glb).

Built in Blender from the PAL console's proportions (snes_layout.py has the measurements, taken from photographs): the
light grey body, its corners rounded seen from above and its top's edges rounded over, the shells' seam round its
sides; the darker panel standing on its top, with the cartridge slot across it (its two dust flaps closed over it),
POWER's slide in its well, EJECT, and RESET in its well; the power light's slot in front of the panel; and the long
rounded recess in its front with the controller ports. The printing (the panel, the legends, the coloured dots, the
name, the ports, the cartridge's label) is one texture, drawn by snes_print.py and projected onto the faces facing up
and the ports' recess. The Satellaview's Super Famicom stands on the receiver (BASE in snes_layout.py), its front panel
sunk into its front with the name and the lights, and its cartridge carries the memory pack in its top.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: its right end towards the viewer, its
top tipped up, as the Mega Drive's; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding
the console; the console holding the dust flaps (each hinged along the slot's edge), POWER's knob, EJECT, the power
light lit and the cartridge (Odyssey, a made-up game). The cartridge waits in the slot shrunk to nothing and the light
is shrunk to nothing, so at rest the card is the console with its slot shut.

The `focused` clip (8 s, looping) plays a game: the cartridge pops up above the slot, turns once to show its label and
drops in, the flaps swinging down out of its way; POWER slides on and the light comes on. Later POWER goes off, EJECT
goes down, the cartridge jumps up and goes, and the flaps swing shut. On the Satellaview the receiver's ACCESS light
flickers while it's on, as it does taking a broadcast.

Four materials (case, print, dark, cart) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/snes_print.py snes artifacts/snes
    blender -b --factory-startup --python tools/console-models/snes.py -- artifacts/snes snes godot/themes/console/models/systems/snes.glb

and the same with satellaview.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snes_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, print=0.5, dark=0.7, cart=0.5)
FLAP_OPEN = 80.0     # degrees each dust flap swings down


def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    """The top seen from above."""
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def stadium(cx, cy, half, r, segments=10):
    """A slot's outline: half its length either side of (cx, cy), r its round ends' radius."""
    points = []
    for end, a0 in ((cx + half - r, -90), (cx - half + r, 90)):
        for k in range(segments + 1):
            a = math.radians(a0 + 180 * k / segments)
            points.append((end + r * math.cos(a), cy + r * math.sin(a)))
    return points


def tube(name, outer, inner, z0, z1, mat):
    """A closed ring, outer and inner outlines (the same count of points) from z0 to z1."""
    bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for x, y in outline] for outline, z in ((outer, z0), (outer, z1), (inner, z1),
                                                                              (inner, z0))]
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for k in range(len(a)):
            j = (k + 1) % len(a)
            bm.faces.new([a[k], a[j], b[j], b[k]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


# ---- The console -----------------------------------------------------------------------------------------------------

def body(m):
    plan = lambda grow: rounded(0.0, L.DEPTH / 2, L.WIDTH + 2 * grow, L.DEPTH + 2 * grow, L.CORNER + grow, 6)
    shell = prism("snes", plan(0.0), 0.0, L.TOP, m["case"])
    bevel(shell, L.EDGE, segments=4, angle=50)
    boolean(shell, tube("crease", plan(4.0), plan(-0.8), L.CREASE - 0.6, L.CREASE + 0.6, m["dark"]))

    p = L.PANEL
    top = L.TOP + p["height"]
    panel = prism("panel", rounded(0.0, sum(p["y"]) / 2, 2 * p["x"], p["y"][1] - p["y"][0], p["r"], 4), L.TOP - 1.0,
                  top, m["case"])
    bevel(panel, 1.2, segments=2)
    boolean(shell, panel, "UNION")

    s = L.SLOT
    boolean(shell, prism("slot", stadium(0.0, sum(s["y"]) / 2, s["x"], (s["y"][1] - s["y"][0]) / 2),
                         top - s["depth"], top + 5.0, m["dark"]))
    for well in (L.POWER, L.RESET):
        boolean(shell, box("well", *well["x"], *well["y"], top - 3.5, top + 5.0, m["dark"]))
    x, y, length, width = L.LED
    boolean(shell, box("led", x - length / 2, x + length / 2, y - width / 2, y + width / 2, L.TOP - 1.0, L.TOP + 5.0,
                       m["dark"]))
    (z0, z1), half = L.PORTS["z"], L.PORTS["x"]
    ports = solid("ports", [[(x, y, z) for x, z in stadium(0.0, (z0 + z1) / 2, half, (z1 - z0) / 2)]
                            for y in (-5.0, L.PORTS["depth"])], m["case"])
    boolean(shell, ports)

    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "case")
    front = atlas_uv(L.REGIONS["front"], 2 * half, z1 - z0)
    paint(shell, m["print"], lambda co: front(co.x + half, z1 - co.z),
          lambda c, n, name: name == "case" and n.y < -0.9 and abs(c.y - L.PORTS["depth"]) < 0.2)
    paint(shell, m["print"], swatch("flap"), lambda c, n, name: name == "dark" and abs(c.z - L.CREASE) < 1.0)

    reset = L.RESET
    button = box("reset", reset["x"][0] + 1.2, reset["x"][1] - 1.2, reset["y"][0] + 1.2, reset["y"][1] - 1.2,
                 top - 3.5, top + reset["height"], m["case"])
    bevel(button, 1.0, segments=2)
    paint(button, m["print"], top_uv, lambda c, n, name: n.z > 0.9)
    return join([shell, button], "snes")


def flaps(m):
    """The slot's two dust flaps, each its origin on its hinge along the slot's front or back edge."""
    s = L.SLOT
    top = L.TOP + L.PANEL["height"]
    y0, y1 = s["y"]
    middle = (y0 + y1) / 2
    parts = {}
    for name, a, b, hinge_y in (("flap_front", y0 + 0.4, middle - 0.15, y0), ("flap_back", middle + 0.15, y1 - 0.4, y1)):
        flap = box(name, -s["x"] + 6.0, s["x"] - 6.0, a, b, top - 2.2, top - 0.8, m["print"])
        paint(flap, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
        paint(flap, m["print"], swatch("flap"), lambda c, n, _name: n.z <= 0.9)
        hinge = Vector((0.0, hinge_y, top - 1.5))
        flap.data.transform(Matrix.Translation(-hinge))
        parts[name] = (flap, hinge)
    return parts


def knob(m):
    """POWER's knob, off: at the front of its well, its top sloping up to a ridge at its back."""
    w = L.POWER
    kw, kd, kh = w["knob"]
    cx, y0 = sum(w["x"]) / 2, w["y"][0] + 2.5
    top = L.TOP + L.PANEL["height"]
    profile = [(y0, top - 3.0), (y0 + kd, top - 3.0), (y0 + kd, top + kh - 3.0), (y0 + kd - 2.0, top + kh - 2.6),
               (y0, top + 0.5)]
    grip = solid("power", [[(x, y, z) for y, z in profile] for x in (cx - kw / 2, cx + kw / 2)], m["dark"])
    bevel(grip, 0.6, segments=1)
    return grip


def eject(m):
    k = L.EJECT
    top = L.TOP + L.PANEL["height"]
    button = solid("eject", [[(x, y, z) for x, y in rounded(sum(k["x"]) / 2, sum(k["y"]) / 2, k["x"][1] - k["x"][0],
                                                           k["y"][1] - k["y"][0], 3.0, 3)]
                             for z in (top - 1.0, top + k["height"])], m["case"])
    bevel(button, 1.0, segments=2)
    paint(button, m["print"], top_uv, lambda c, n, name: n.z > 0.9)
    return button


def light(m):
    x, y, length, width = L.LED
    lit = box("power_light", -length / 2 + 0.3, length / 2 - 0.3, -width / 2 + 0.3, width / 2 - 0.3, -0.6, 0.0,
              m["print"])
    paint(lit, m["print"], swatch("led"), lambda c, n, name: True)
    return lit, Vector((x, y, L.TOP - 0.3))


def receiver(k, m):
    """The Satellaview under the console: a box of its footprint, its front panel sunk into its front and printed."""
    b = k["base"]
    shell = prism("receiver", rounded(0.0, L.DEPTH / 2, L.WIDTH - 2.0, L.DEPTH - 4.0, b["corner"], 6), 0.0,
                  b["height"] + 1.0, m["case"])
    bevel(shell, 3.0, segments=3, angle=50)
    pw, ph, r = b["panel"]
    z0, sunk = (b["height"] - ph) / 2, 2.0 + b["depth"]   # the panel's bottom; its face, behind the box's front at y = 2
    boolean(shell, solid("panel", [[(x, y, z) for x, z in rounded(0.0, z0 + ph / 2, pw, ph, r, 4)]
                                   for y in (-5.0, sunk)], m["case"]))
    front = atlas_uv(L.REGIONS["base"], pw, ph)
    paint(shell, m["print"], lambda co: front(co.x + pw / 2, z0 + ph - co.z),
          lambda c, n, name: n.y < -0.9 and abs(c.y - sunk) < 0.2)
    lw = 2.0
    x, _ = b["lights"]["access"]
    lit = box("access_light", -lw / 2, lw / 2, -0.3, 0.0, -3.5, 3.5, m["print"])
    paint(lit, m["print"], swatch("access"), lambda c, n, name: True)
    return shell, lit, Vector((x, sunk - 0.05, z0 + ph / 2 + 0.5))


def cartridge(m, pack=False):
    """The cartridge, standing on its connector's edge with its middle at its origin, its label facing the front; the
    Satellaview's carries the memory pack standing in its top."""
    c = L.CART
    w, h, t = c["width"], c["height"], c["thickness"]
    outline = [(w / 2, 0.0)] + [(w / 2 - 6.0 + 6.0 * math.cos(math.radians(a)), h - 6.0 + 6.0 * math.sin(math.radians(a)))
                                for a in range(0, 91, 15)]
    outline += [(x, h + c["arch"] * (1 - (x / (w / 2 - 6.0)) ** 2)) for x in (30.0, 0.0, -30.0)]
    outline += [(-w / 2 + 6.0 - 6.0 * math.cos(math.radians(a)), h - 6.0 + 6.0 * math.sin(math.radians(a)))
                for a in range(90, -1, -15)] + [(-w / 2, 0.0)]
    shell = solid("cartridge", [[(x, y, z) for x, z in outline] for y in (-t / 2, t / 2)], m["cart"])
    bevel(shell, 1.5, segments=2)
    lw, lh, from_top = c["label"]
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    z1 = h - from_top
    corners = [(-lw / 2, z1 - lh), (lw / 2, z1 - lh), (lw / 2, z1), (-lw / 2, z1)]       # wound to face -y
    face = bm.faces.new([bm.verts.new((x, -t / 2 - 0.2, z)) for x, z in corners])
    uv = atlas_uv(L.REGIONS["label"], lw, lh)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = uv(x + lw / 2, z1 - z)
    label = new_object("label", bm, m["print"])
    parts = [shell, label]
    if pack:
        p = L.MEMORY_PACK
        top = h + c["arch"]
        stick = box("pack", -p["width"] / 2, p["width"] / 2, -p["thickness"] / 2, p["thickness"] / 2, top - 8.0,
                    top - 8.0 + p["height"], m["cart"])
        bevel(stick, 1.0, segments=1)
        face = atlas_uv(L.REGIONS["pack"], p["width"], p["height"])
        paint(stick, m["print"], lambda co: face(co.x + p["width"] / 2, top - 8.0 + p["height"] - co.z),
              lambda c_, n, name: n.y < -0.9)
        parts.append(stick)
    cart = join(parts, "cartridge")
    cart.data.transform(Matrix.Translation((0.0, 0.0, -h / 2)))
    return cart


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 5, f0 + 9)))


def timeline(f):
    above = L.CART["inserted"] + 55.0
    # The cartridge: pops up above the slot, turns once to show its label, drops in; later jumps out and goes.
    if f < 12 or f >= 210:
        cart = Pose(scale=HIDDEN)
    elif f < 22:
        cart = Pose(z=above + 12.0, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 12, 22)))
    elif f < 40:
        t = smooth(phase(f, 22, 40))
        cart = Pose(z=above + 12.0 * (1 - t), spin=360.0 * t)
    elif f < 176:
        t = ease_in(phase(f, 40, 54))
        settle = 2.0 * math.exp(-(f - 54) / 3.0) * abs(math.sin(math.pi * (f - 54) / 5.0)) if f >= 54 else 0.0
        cart = Pose(z=above * (1 - t) + settle)
    elif f < 194:
        cart = Pose(z=30.0 * back_out(phase(f, 178, 186), 1.8))
    else:
        t = ease_in(phase(f, 194, 210))
        cart = Pose(z=30.0 + 70.0 * t, spin=-180.0 * t, scale=max(HIDDEN, 1 - ease_in(phase(f, 202, 210))))

    # The flaps swing down as the cartridge comes, and shut once it's gone.
    swing = FLAP_OPEN * smooth(phase(f, 38, 44)) * (1 - smooth(phase(f, 198, 206)))
    poses = {"cartridge": cart, "flap_front": Pose(pitch=-swing), "flap_back": Pose(pitch=swing)}
    on = smooth(phase(f, 60, 64)) * (1 - smooth(phase(f, 168, 172)))
    poses["power"] = Pose(y=L.POWER["travel"] * on)
    poses["power_light"] = Pose() if 64 <= f < 170 else Pose(scale=HIDDEN)
    poses["eject"] = Pose(z=-2.2 * tap(f, 176))
    taking = 72 <= f < 160 and (f // 4) % 3 != 2                # the receiver's ACCESS light, taking a broadcast
    poses["access_light"] = Pose() if taking else Pose(scale=HIDDEN)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, kind, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, f"{kind}_print.png"))
    k = L.KINDS[kind]
    colours = dict(case=k["case"], print="#FFFFFF", dark=L.COLOURS["dark"], cart=L.COLOURS["cart"])
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    console = body(m)
    lit, lit_at = light(m)
    slide, button, cart = knob(m), eject(m), cartridge(m, pack="base" in k)
    lift = Vector((0.0, 0.0, k["base"]["height"] if "base" in k else 0.0))
    extra = {}
    if "base" in k:                                    # the Super Famicom stands on the receiver
        console.data.transform(Matrix.Translation(lift))
        under, access, access_at = receiver(k, m)
        console = join([console, under], "satellaview")
        extra["access_light"] = (access, access_at)
    for obj in (console, slide, button, cart):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new(kind + "_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    seat = Vector((0.0, sum(L.SLOT["y"]) / 2, L.TOP + L.PANEL["height"] - L.CART["inserted"] + L.CART["height"] / 2))
    nodes = {"power": slide, "eject": button, "power_light": lit, "cartridge": cart}
    for part, where in ((lit, lit_at), (cart, seat), (slide, Vector()), (button, Vector())):
        part.parent = console
        part.location = where + lift
    for name, (flap, hinge) in flaps(m).items():
        flap.parent = console
        flap.location = hinge + lift
        nodes[name] = flap
    for name, (part, where) in extra.items():
        part.parent = console
        part.location = where
        nodes[name] = part

    # The three-quarter view, then the spec's fit of the console at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in console.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [console] + list(nodes.values())
    print(f"Super Nintendo ({kind}): {sum(triangles(o.data) for o in meshes)} triangles "
          f"({triangles(console.data)} the console), {len({mat.name for o in meshes for mat in o.data.materials})} "
          f"materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
