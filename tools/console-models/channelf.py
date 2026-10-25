"""The console theme's Fairchild Channel F system model (godot/themes/console/models/systems/channelf.glb): the Channel
F and its two controllers.

Built in Blender (channelf_layout.py has the measurements, taken from photographs). The console is its side outline
extruded across its width and cut to its sides sloping in to the foot: walnut on the sides and the front's plinth, black
on top; the slot is cut into the lid's front face and runs back under the lid, its door hinged along its top. The keys,
the INSERT CARTRIDGE plate and the eject bar stand on the front panel, the chrome strip on the lid. The controllers are
each a rounded grip, a neck and a knob, lying on their sides, their cables wired into the console's left side, each
through a strain relief at both ends (plugs.py's). The printing is one texture (channelf_print.py's), projected from
above onto the panel, its keys, the plate, the bar, the strip and the Videocart, from in front onto the door, and along
the walnut and the grips.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the Videocart (waiting in front of the slot, shrunk to nothing), the door, RESET and 1, the eject bar, and the
first controller's knob.

The `focused` clip (8 s, looping): the Videocart comes down in front of the slot and slides in, pushing the door in;
RESET, then 1 (hockey); the first controller's knob tilts and pushes; then Press to Eject, the Videocart slides back
out, the door shuts behind it, and it goes.

Three materials (plastic, walnut, cart) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/channelf_print.py artifacts/channelf
    blender -b --factory-startup --python tools/console-models/channelf.py -- artifacts/channelf godot/themes/console/models/systems/channelf.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import channelf_layout as L  # noqa: E402
import plugs  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive import prism_y  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(plastic=0.3, walnut=0.5, cart=0.45)


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


PANEL = atlas_uv(L.REGIONS["panel"], L.WIDTH, L.LID["y"])
WOOD = atlas_uv(L.REGIONS["wood"], L.DEPTH, L.HEIGHT)


def panel_uv(co):
    return PANEL(co.x + L.WIDTH / 2, L.LID["y"] - co.y)


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The walnut and the black: the side outline, its sides sloping in to the foot, the slot cut in; printed."""
    half, foot = L.WIDTH / 2, L.SIDE["foot"]
    body = prism_x("channelf", L.PROFILE, -half - 1.0, half + 1.0, m["plastic"])
    lean = foot / L.HEIGHT                                    # how far the sides slope in, per millimetre down
    sides = [(-half + foot + lean, -1.0), (half - foot - lean, -1.0), (half + 6.0 * lean, L.HEIGHT + 6.0),
             (-half - 6.0 * lean, L.HEIGHT + 6.0)]
    boolean(body, prism_y("sides", sides, -10.0, L.DEPTH + 10.0, m["plastic"]), "INTERSECT")
    bevel(body, 2.0, segments=2, angle=40)
    (x0, x1), (z0, z1) = L.SLOT["x"], L.SLOT["z"]
    boolean(body, box("slot", x0, x1, L.LID["y"] - 5.0, L.LID["y"] + L.SLOT["depth"], z0, z1, m["plastic"]))
    colour(body, m["plastic"], "black")
    paint(body, m["plastic"], panel_uv, lambda c, n, kind: n.z > 0.5 and c.y < L.LID["y"] - 0.5)
    paint(body, m["plastic"], swatch("gloss"), lambda c, n, kind: n.z > 0.5 and c.y > L.LID["y"] - 0.5)
    paint(body, m["walnut"], lambda co: WOOD(co.y, L.HEIGHT - co.z), lambda c, n, kind: abs(n.x) > 0.5)
    paint(body, m["walnut"], lambda co: WOOD(co.x + half + 10.0, L.HEIGHT - co.z),
          lambda c, n, kind: n.y < -0.5 and c.z < L.SIDE["black"] - 0.5)
    paint(body, m["plastic"], swatch("dark"),
          lambda c, n, kind: x0 - 0.5 < c.x < x1 + 0.5 and c.y > L.LID["y"] - 0.5 and z0 - 0.5 < c.z < z1 + 0.5)
    return body


def fittings(m):
    """On the panel: the keys, the plate, the eject bar; on the lid: the chrome strip. RESET, 1 and the bar apart (each
    its foot's middle at its origin, with where it goes); the rest joined."""
    fixed, moving = [], {}
    k, y = L.KEYS["size"] / 2, L.KEYS["y"]
    for x, name in zip(L.KEYS["x"], L.KEYS["names"]):
        z = L.panel_z(y)
        part = box("key", x - k, x + k, y - k, y + k, z - 1.0, z + L.KEYS["height"], m["plastic"])
        bevel(part, 1.0, segments=2)
        colour(part, m["plastic"], "yellow" if name == "RESET" else "cream")
        paint(part, m["plastic"], panel_uv, lambda c, n, kind: n.z > 0.9)
        if name in ("RESET", "1"):
            middle = Vector((x, y, z - 1.0))
            part.data.transform(Matrix.Translation(-middle))
            moving["reset" if name == "RESET" else "one"] = (part, middle)
        else:
            fixed.append(part)
    (px0, px1), (py0, py1), h = L.PLATE["x"], L.PLATE["y"], L.PLATE["height"]
    plate = prism_x("plate", [(py0, L.panel_z(py0) - 1.0), (py1, L.panel_z(py1) - 1.0), (py1, L.panel_z(py1) + h),
                              (py0, L.panel_z(py0) + h)], px0, px1, m["plastic"])
    bevel(plate, 0.6, segments=1)
    colour(plate, m["plastic"], "black")
    paint(plate, m["plastic"], panel_uv, lambda c, n, kind: n.z > 0.9)
    fixed.append(plate)
    (ex0, ex1), (ey0, ey1) = L.EJECT["x"], L.EJECT["y"]
    z = L.panel_z((ey0 + ey1) / 2)
    bar = box("eject", ex0, ex1, ey0, ey1, z - 1.0, z + L.EJECT["height"], m["plastic"])
    bevel(bar, 1.0, segments=2)
    colour(bar, m["plastic"], "black")
    paint(bar, m["plastic"], panel_uv, lambda c, n, kind: n.z > 0.9)
    middle = Vector(((ex0 + ex1) / 2, (ey0 + ey1) / 2, z - 1.0))
    bar.data.transform(Matrix.Translation(-middle))
    moving["eject"] = (bar, middle)
    (sx0, sx1), (sy0, sy1) = L.STRIP["x"], L.STRIP["y"]
    strip = box("strip", sx0, sx1, sy0, sy1, L.HEIGHT - 1.0, L.HEIGHT + 1.5, m["plastic"])
    bevel(strip, 0.8, segments=2)
    colour(strip, m["plastic"], "black")
    face = atlas_uv(L.REGIONS["strip"], L.WIDTH, sy1 - sy0)
    paint(strip, m["plastic"], lambda co: face(co.x + L.WIDTH / 2, sy1 - co.y), lambda c, n, kind: n.z > 0.9)
    fixed.append(strip)
    return fixed, moving


def door(m):
    """The cartridge door, its origin on its hinge along its top; its face ribbed."""
    (x0, x1), (z0, z1), g = L.SLOT["x"], L.SLOT["z"], L.DOOR["inset"]
    y = L.LID["y"] + 2.0
    part = box("door", x0 + g, x1 - g, y, y + 2.0, z0 + g, z1 - g, m["plastic"])
    colour(part, m["plastic"], "black")
    face = atlas_uv(L.REGIONS["door"], x1 - x0, z1 - z0)
    paint(part, m["plastic"], lambda co: face(co.x - x0, z1 - co.z), lambda c, n, kind: n.y < -0.9)
    hinge = Vector(((x0 + x1) / 2, y + 1.0, z1 - g))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def videocart(m):
    """The Videocart, its origin at its front end's foot, its label on its top."""
    w, length, t = L.CART["size"]
    part = box("videocart", -w / 2, w / 2, 0.0, length, 0.0, t, m["cart"])
    bevel(part, 2.0, segments=2)
    colour(part, m["cart"], "cart")
    face = atlas_uv(L.REGIONS["cart"], w, length)
    paint(part, m["cart"], lambda co: face(co.x + w / 2, length - co.y), lambda c, n, kind: n.z > 0.9)
    return part


# ---- The controllers -------------------------------------------------------------------------------------------------

def controller(m, place, live):
    """One controller lying on its side at place (x, y, turn): the grip, the neck and the knob at its +x end; the neck
    and the knob apart when live (with where they go). Returns the joined parts, the moving ones, and where its cable
    leaves it."""
    x, y, turn = place
    spin = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
    length, width, height = L.CONTROLLER["grip"]
    grip = box("grip", -length / 2, length / 2, -width / 2, width / 2, 0.0, height, m["plastic"])
    bevel(grip, 7.0, segments=4)
    colour(grip, m["plastic"], "black")
    face = atlas_uv(L.REGIONS["grip"], length, height)
    paint(grip, m["plastic"], lambda co: face(co.x + length / 2, height - co.z), lambda c, n, kind: abs(n.y) > 0.8)
    r, neck_length = L.CONTROLLER["neck"]
    kw, kh, kt = L.CONTROLLER["knob"]
    # The neck, then the knob flaring from it like a mushroom's cap, its section an oval kw by kh.
    shape = [(-2.0, r), (neck_length, r), (neck_length + 0.2 * kt, 0.55), (neck_length + 0.45 * kt, 0.9),
             (neck_length + 0.75 * kt, 1.0), (neck_length + 0.92 * kt, 0.85), (neck_length + kt, 0.5)]
    rings = []
    for a, size in shape:
        ry, rz = (size, size) if size > 1.5 else (size * kw / 2, size * kh / 2)
        rings.append([(a, ry * math.cos(2 * math.pi * k / 20), rz * math.sin(2 * math.pi * k / 20)) for k in range(20)])
    head = colour(solid("knob", rings, m["plastic"]), m["plastic"], "black")
    head.data.transform(Matrix.Rotation(math.radians(turn), 4, "Z"))
    where = spin @ Vector((length / 2, 0.0, height / 2))
    grip.data.transform(spin)
    parts, moving = [grip], {}
    if live:
        moving["knob"] = (head, where)
    else:
        head.data.transform(Matrix.Translation(where))
        parts.append(head)
    return join(parts, "controller"), moving, spin @ Vector((-length / 2 + 3.0, 0.0, height / 2))


def cable(name, m, points, radius=2.2):
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


def timeline(f):
    out, up = L.CART["out"], 30.0
    if f < 10 or f >= 200:
        cart = Pose(y=-out, z=up, scale=HIDDEN)
    elif f < 17:
        cart = Pose(y=-out, z=up, scale=max(HIDDEN, back_out(phase(f, 10, 17))))
    elif f < 24:
        cart = Pose(y=-out, z=up * (1 - ease_in(phase(f, 17, 24))))
    elif f < 178:
        cart = Pose(y=-out * (1 - smooth(phase(f, 24, 40))))
    elif f < 190:
        cart = Pose(y=-out * smooth(phase(f, 178, 190)))
    else:
        cart = Pose(y=-out, z=up * ease_out(phase(f, 190, 198)), scale=max(HIDDEN, 1 - ease_in(phase(f, 194, 200))))
    opened = smooth(phase(f, 25, 30)) * (1 - smooth(phase(f, 188, 194)))
    t = phase(f, 62, 168)
    k = math.sin(math.pi * t)
    turn = math.radians(L.CONTROLLER["at"][0][2])
    push = 4.0 * k * math.sin(2 * math.pi * 2.0 * t)
    return {"videocart": cart, "door": Pose(pitch=L.DOOR["open"] * opened),
            "reset": Pose(z=-2.0 * tap(f, 46)), "one": Pose(z=-2.0 * tap(f, 54)), "eject": Pose(z=-2.0 * tap(f, 172)),
            "knob": Pose(x=push * math.cos(turn), y=push * math.sin(turn),
                         spin=22.0 * k * math.sin(2 * math.pi * 3.0 * t))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "channelf_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    parts, moving = fittings(m)
    parts.append(console(m))
    black = (lambda o: colour(o, m["plastic"], "black"))
    side = Vector((-L.HEIGHT, 0.0, -L.SIDE["foot"])).normalized()          # out of the left side, leaning in
    for k, place in enumerate(L.CONTROLLER["at"]):
        grip, live, exit_ = controller(m, place, k == 0)
        moving.update(live)
        turn = math.radians(place[2])
        relief, start, leaving = plugs.place(*plugs.grommet(black, 4.2), m["plastic"], exit_,
                                             (-math.cos(turn), -math.sin(turn), 0.0))
        z, y = L.PORT["z"], L.PORT["y"] - 26.0 * k                         # the controllers are wired in
        entry = Vector((-L.WIDTH / 2 + L.SIDE["foot"] * (1 - z / L.HEIGHT), y, z))
        sleeve, end, back = plugs.place(*plugs.grommet(black, 4.6), m["plastic"], entry, side)
        parts += [grip, cable("cable", m, [start, start + leaving * 50.0 + Vector((0.0, 0.0, -10.0)),
                                           end + back * 60.0 + Vector((0.0, 0.0, -20.0)), end])] + relief + sleeve
    whole = join(parts, "channelf")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("channelf_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (x0, x1), (z0, _) = L.SLOT["x"], L.SLOT["z"]
    moving["videocart"] = (videocart(m), Vector(((x0 + x1) / 2, L.CART["front"], z0 + 1.0)))
    moving["door"] = door(m)
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
    print(f"Channel F: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
