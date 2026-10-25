"""The console theme's TI-99/4A system model (godot/themes/console/models/systems/ti99.glb): the Texas Instruments
TI-99/4A and its two joysticks.

Built in Blender (ti99_layout.py has the measurements, taken from photographs). The aluminium is its side outline
extruded across its width; the keyboard surround and the module bay are sunk into the deck in the deck's frame, their
corners round, and the slot is the module's path diving under the back section, cut through the bay's floor and back
wall. It stands on the black base, the joystick port cut into the base's left side. The keys stand in the surround in
the deck's frame, each tapering to its printed top. The joysticks are each a tapering box, the stick near one end and
the orange fire bar at the other, their cables running to the port. The printing is one texture (ti99_print.py's),
projected from above onto the aluminium, the surround, the bay and the keys, and onto the module's top along it.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the module (waiting over the bay, shrunk to nothing), the power light (sunk into the strip while off), the 2
key, and the first joystick's stick and fire bar.

The `focused` clip (8 s, looping): the module comes down into the bay and slides into the slot; the power light comes
on; 2 (the module's game, not TI BASIC); the joystick's stick waggles and its fire bar presses; then the light goes out
and the module slides back out and goes.

Two materials (aluminium, plastic) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/ti99_print.py artifacts/ti99
    blender -b --factory-startup --python tools/console-models/ti99.py -- artifacts/ti99 godot/themes/console/models/systems/ti99.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ti99_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 24.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(alu=0.35, plastic=0.45)

DIVE = math.radians(L.MODULE["dive"])
ALONG = Vector((0.0, math.cos(DIVE), -math.sin(DIVE)))           # into the slot: back and down
FACE = Vector((0.0, math.sin(DIVE), math.cos(DIVE)))             # out of the module's top
NORMAL = Vector((0.0, -math.sin(L.SLOPE), math.cos(L.SLOPE)))    # out of the deck


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def plan_s(y):
    """How far up the deck from its front edge the deck's surface is at y."""
    return (y - L.FRONT[0]) / math.cos(L.SLOPE)


def deck_z(y):
    return L.FRONT[1] + (y - L.FRONT[0]) * math.tan(L.SLOPE)


def on_deck(name, outline, h0, h1, mat, outline1=None):
    """A solid from an (x, s) outline in the deck's frame, from h0 off it to h1 (its top outline1, if given)."""
    top = outline1 or outline
    return solid(name, [[(x, *L.deck_point(s, h0)) for x, s in outline], [(x, *L.deck_point(s, h1)) for x, s in top]],
                 mat)


def sunk(name, x, y, depth, r, mat):
    """A cutter for a round-cornered recess in the deck: its plan's x and y ranges, how deep."""
    (x0, x1), (s0, s1) = x, (plan_s(y[0]), plan_s(y[1]) - 0.01)
    outline = rounded((x0 + x1) / 2, (s0 + s1) / 2, x1 - x0, s1 - s0, r, 4)
    return on_deck(name, outline, -depth, 20.0, mat)


def module_point(along, across, depth):
    """A point of the module in its place: along its length from its top's front edge, across from its middle, depth
    under its top."""
    fy, fz = L.MODULE["front"]
    return Vector((sum(L.BAY["x"]) / 2 + across, fy, fz)) + ALONG * along - FACE * depth


def in_slot(c):
    """Whether a point is in the module's path."""
    w, length, t = L.MODULE["size"]
    g = L.MODULE["margin"] + 0.5
    d = c - module_point(0.0, 0.0, 0.0)
    a, depth = d.dot(ALONG), -d.dot(FACE)
    return L.MODULE["out"][0] - 5.5 < a < length + 5.5 and abs(c.x - sum(L.BAY["x"]) / 2) < w / 2 + g \
        and -g < depth < t + g


# ---- The computer ----------------------------------------------------------------------------------------------------

def aluminium(m):
    """The aluminium with the surround, the bay and the slot cut in; printed."""
    half = L.WIDTH / 2
    alu = prism_x("ti99", L.PROFILE, -half, half, m["alu"])
    bevel(alu, 1.5, segments=2, angle=40)
    boolean(alu, sunk("surround", L.SURROUND["x"], L.SURROUND["y"], L.SURROUND["depth"], L.SURROUND["r"], m["alu"]))
    boolean(alu, sunk("bay", L.BAY["x"], L.BAY["y"], L.BAY["depth"], 4.0, m["alu"]))
    w, length, t = L.MODULE["size"]
    g = L.MODULE["margin"]
    section = [(-w / 2 - g, -g), (w / 2 + g, -g), (w / 2 + g, t + g), (-w / 2 - g, t + g)]
    boolean(alu, solid("slot", [[tuple(module_point(a, x, d)) for x, d in section]
                                for a in (L.MODULE["out"][0] - 5.0, length + 5.0)], m["alu"]))
    colour(alu, m["alu"], "alu")
    paint(alu, m["alu"], top_uv, lambda c, n, kind: n.z > 0.3)

    def sunken(c, n):
        inside = any(x0 - 0.5 < c.x < x1 + 0.5 and y0 - 0.5 < c.y < y1 + 0.5
                     for (x0, x1), (y0, y1) in ((L.SURROUND["x"], L.SURROUND["y"]), (L.BAY["x"], L.BAY["y"])))
        return inside and n.z <= 0.3 and c.z < deck_z(c.y) - 0.3
    paint(alu, m["alu"], swatch("black"), lambda c, n, kind: sunken(c, n))
    paint(alu, m["alu"], swatch("dark"), lambda c, n, kind: in_slot(c) and c.z < deck_z(c.y) - L.BAY["depth"] + 0.5)
    return alu


def base(m):
    half = L.WIDTH / 2
    part = box("base", -half + 0.5, half - 0.5, 0.5, L.DEPTH - 0.5, 0.0, L.BASE + 0.5, m["plastic"])
    bevel(part, 1.5, segments=2)
    y, z = L.PORT["y"], L.PORT["z"]
    boolean(part, box("port", -half - 1.0, -half + 3.0, y - 11.0, y + 11.0, z - 5.0, z + 5.0, m["plastic"]))
    colour(part, m["plastic"], "black")
    paint(part, m["plastic"], swatch("dark"), lambda c, n, kind: c.x < -half + 3.5 and abs(c.y - y) < 11.5
          and abs(c.z - z) < 5.5)
    return part


def keys(m):
    """The keys, each tapering to its printed top: the 2 key apart (its foot's middle at its origin, with where it
    goes), the rest joined."""
    fixed, moving = [], {}
    inset, floor = L.KEY["inset"], -L.SURROUND["depth"]
    for legend, x0, x1, s in L.keys():
        foot = [(x0 + 0.5, s - 9.0), (x1 - 0.5, s - 9.0), (x1 - 0.5, s + 9.0), (x0 + 0.5, s + 9.0)]
        cap = [(x0 + inset, s - 9.5 + inset), (x1 - inset, s - 9.5 + inset), (x1 - inset, s + 9.5 - inset),
               (x0 + inset, s + 9.5 - inset)]
        part = on_deck("key", foot, floor - 1.0, L.KEY["height"], m["plastic"], cap)
        colour(part, m["plastic"], "key")
        paint(part, m["plastic"], top_uv, lambda c, n, kind: n.z > 0.85)
        if legend == "2":
            middle = Vector(((x0 + x1) / 2, *L.deck_point(s, floor - 1.0)))
            part.data.transform(Matrix.Translation(-middle))
            moving["two"] = (part, middle)
        else:
            fixed.append(part)
    lx, ly = L.STRIP["light"]
    ring = [(lx + 1.3 * math.cos(2 * math.pi * k / 12), plan_s(ly) + 1.3 * math.sin(2 * math.pi * k / 12))
            for k in range(12)]
    light = colour(on_deck("light", ring, floor - 1.1, floor - 0.2, m["plastic"]), m["plastic"], "light")
    middle = Vector((lx, *L.deck_point(plan_s(ly), floor)))
    light.data.transform(Matrix.Translation(-middle))
    moving["light"] = (light, middle)
    return join(fixed, "keys"), moving


def module(m):
    """The command module, its origin at its top's front edge's middle; its top printed along it."""
    w, length, t = L.MODULE["size"]
    origin = module_point(0.0, 0.0, 0.0)
    corners = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, length), (-w / 2, length)]
    part = solid("module", [[tuple(module_point(a, x, d)) for x, a in corners] for d in (t, 0.0)], m["plastic"])
    bevel(part, 1.0, segments=2)
    colour(part, m["plastic"], "module")
    label = atlas_uv(L.REGIONS["module"], w, length)

    def uv(co):
        d = co - origin
        return label(co.x - origin.x + w / 2, length - d.dot(ALONG))
    paint(part, m["plastic"], uv, lambda c, n, kind: n.dot(FACE) > 0.9)
    part.data.transform(Matrix.Translation(-origin))
    return part, origin


# ---- The joysticks and their cables ----------------------------------------------------------------------------------

def joystick(m, place, live):
    """One joystick at place (x, y, turn): its body, stick and fire bar; the stick and the bar apart when live (each
    with where it goes). Returns the joined parts, the moving ones and where its cable leaves it."""
    x, y, turn = place
    spin = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
    (fx, fy), (tx, ty), h = L.JOYSTICK["foot"], L.JOYSTICK["top"], L.JOYSTICK["height"]
    body = solid("joystick", [[(px, py, 0.0) for px, py in rounded(0.0, 0.0, fx, fy, 8.0, 4)],
                              [(px, py, h) for px, py in rounded(0.0, 0.0, tx, ty, 6.0, 4)]], m["plastic"])
    bevel(body, 1.5, segments=2)
    colour(body, m["plastic"], "black")
    (r0, r1), length = L.JOYSTICK["radius"], L.JOYSTICK["length"]
    stick = solid("stick", [[(r * math.cos(2 * math.pi * k / 16), r * math.sin(2 * math.pi * k / 16), z)
                             for k in range(16)] for r, z in ((r0 * 1.7, -1.0), (r0 * 1.7, 2.0), (r0, 5.0),
                                                              (r1, length - 3.0), (r1 * 0.7, length))], m["plastic"])
    colour(stick, m["plastic"], "black")
    bw, bl, bh = L.JOYSTICK["bar"]
    bar = box("fire", -bw / 2, bw / 2, -bl / 2, bl / 2, -1.0, bh, m["plastic"])
    bevel(bar, 1.0, segments=2)
    colour(bar, m["plastic"], "orange")
    body.data.transform(spin)
    turned = Matrix.Rotation(math.radians(turn), 4, "Z")
    parts, moving = [body], {}
    for name, part, (px, py) in (("shaft", stick, L.JOYSTICK["stick"]), ("fire", bar, L.JOYSTICK["button"])):
        part.data.transform(turned)
        where = spin @ Vector((px, py, h))
        if live:
            moving[name] = (part, where)
        else:
            part.data.transform(Matrix.Translation(where))
            parts.append(part)
    return join(parts, "joystick"), moving, spin @ Vector((-fx / 2 + 2.0, 0.0, h * 0.4))


def cord(name, m, points, radius=2.2):
    """A cable: a tube along the Bézier curve through four control points."""
    p0, p1, p2, p3 = (Vector(p) for p in points)
    path = [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / 24 for k in range(25)]]
    bm = bmesh.new()
    rings, normal = [], Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(path):
        tangent = (path[min(k + 1, 24)] - path[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * radius)
                      for a in [2 * math.pi * j / 8 for j in range(8)]])
    for a, b in zip(rings, rings[1:]):
        for j in range(8):
            bm.faces.new([a[j], a[(j + 1) % 8], b[(j + 1) % 8], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return colour(new_object(name, bm, m["plastic"]), m["plastic"], "black")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def slid(along, up, scale=1.0):
    """The module's pose: along the slot (into it positive) and up."""
    d = ALONG * along + Vector((0.0, 0.0, up))
    return Pose(x=d.x, y=d.y, z=d.z, scale=scale)


def timeline(f):
    out, up = L.MODULE["out"]
    if f < 10 or f >= 200:
        part = slid(out, up, HIDDEN)
    elif f < 18:
        part = slid(out, up, max(HIDDEN, back_out(phase(f, 10, 17))))
    elif f < 26:
        part = slid(out, up * (1 - ease_in(phase(f, 18, 26))))
    elif f < 182:
        part = slid(out * (1 - smooth(phase(f, 26, 38))), 0.0)
    elif f < 192:
        part = slid(out * smooth(phase(f, 182, 192)), 0.0)
    else:
        part = slid(out, up * ease_out(phase(f, 192, 200)), max(HIDDEN, 1 - ease_in(phase(f, 194, 200))))
    lit = NORMAL * (1.0 if 44 <= f < 178 else 0.0)
    pressed = -NORMAL * 2.0 * tap(f, 54)
    t = phase(f, 64, 168)
    k = math.sin(math.pi * t)
    return {"module": part, "light": Pose(x=lit.x, y=lit.y, z=lit.z), "two": Pose(x=pressed.x, y=pressed.y,
                                                                                      z=pressed.z),
            "shaft": Pose(pitch=20.0 * k * math.sin(2 * math.pi * 3.0 * t),
                          roll=20.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "fire": Pose(z=-2.0 * max(tap(f, f0) for f0 in (76, 96, 114, 132, 150)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "ti99_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    fixed_keys, moving = keys(m)
    parts = [aluminium(m), base(m), fixed_keys]
    port = Vector((-L.WIDTH / 2 + 2.0, L.PORT["y"], L.PORT["z"]))
    for k, place in enumerate(L.JOYSTICK["at"]):
        stick, live, exit_ = joystick(m, place, k == 0)
        moving.update(live)
        turn = math.radians(place[2])
        lead = exit_ + Vector((-40.0 * math.cos(turn), -40.0 * math.sin(turn), 0.0))
        parts += [stick, cord("cable", m, [exit_, (lead.x, lead.y, 2.2), (port.x - 45.0, port.y - 20.0 * k, 2.2),
                                           port])]
    whole = join(parts, "ti99")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("ti99_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    moving["module"] = module(m)
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
    print(f"TI-99/4A: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
