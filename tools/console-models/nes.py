"""The console theme's NES system model (godot/themes/console/models/systems/nes.glb): the front-loading Nintendo
Entertainment System and its controller.

Built in Blender (nes_layout.py has the measurements, taken from photographs and published figures). The base is a solid
from its top's outline down to its foot's, its sides and back sloping in; the upper body is a box on it, the door's
recess (up to the top), the slot its top plate lies in and the cartridge's chamber cut into its front, the ribs standing
in the band across its top; the ports are cut into the base's front, POWER and RESET stand out of it by the red light.
The door is an L-shaped flap: its face in the recess and its top plate in the top, turned from one profile with its
outer corner rounded as the body's edges are, triangles closing its ends, a rod with a pin at each end along the top
plate's back edge, which it pivots on. The controller is a slab, its cross, SELECT and START, B and A standing on its
printed face, its cable running from its strain relief to its plug in port 1 (plugs.py's). The printing is one texture
(nes_print.py's), projected from above onto the top, the controller and the cartridge, and from in front onto the front
and the door.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the door (on its pivot), the cartridge (waiting in front of the door, shrunk to nothing), POWER and RESET, the
red light (lit and unlit, swapped by depth), and the controller's cross, START, B and A.

The `focused` clip (8 s, looping), the NES's way: the door flips up and over on its pivot until its top plate stands up
and its face lies over it, face up; the cartridge slides in under it and is pressed down, the door shuts; POWER goes in
and the light comes on; START, then the cross rocks while B and A fire; RESET; POWER again and the light goes out; the
door flips up again, the cartridge comes up, slides out and goes, and the door shuts.

Two materials (case, cart) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/nes_print.py artifacts/nes
    blender -b --factory-startup --python tools/console-models/nes.py -- artifacts/nes godot/themes/console/models/systems/nes.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nes_layout as L  # noqa: E402
import plugs  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, cart=0.5)
SINK = 1.0                # how far an unlit light sinks


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
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT)
PAD = atlas_uv(L.REGIONS["pad"], L.PAD["size"][0], L.PAD["size"][1])


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z)


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The base and the upper body, the door's recess, the chamber, the ports cut in, the ribs on the band; printed."""
    half, b = L.WIDTH / 2, L.BASE
    foot = [(-half + b["slope"], 0.0), (half - b["slope"], 0.0), (half - b["slope"], L.DEPTH - b["back"]),
            (-half + b["slope"], L.DEPTH - b["back"])]
    head = [(-half, 0.0), (half, 0.0), (half, L.DEPTH), (-half, L.DEPTH)]
    base = solid("base", [[(x, y, 0.0) for x, y in foot], [(x, y, b["top"] + 1.0) for x, y in head]], m["case"])
    (pz0, pz1), pw = L.PORTS["z"], L.PORTS["width"]
    for x in L.PORTS["x"]:
        boolean(base, box("port", x - pw / 2, x + pw / 2, -1.0, L.PORTS["depth"], pz0, pz1, m["case"]))
    colour(base, m["case"], "base")
    paint(base, m["case"], front_uv, lambda c, n, kind: n.y < -0.9)
    paint(base, m["case"], swatch("dark"), lambda c, n, kind: c.y > 0.5 and pz0 - 0.5 < c.z < pz1 + 0.5
          and any(abs(c.x - x) < pw / 2 + 0.5 for x in L.PORTS["x"]))
    upper = box("upper", -half, half, 0.0, L.DEPTH, b["top"], L.HEIGHT, m["case"])
    bevel(upper, 3.0, segments=3)
    (dx0, dx1), (dz0, dz1), t = L.DOOR["x"], L.DOOR["z"], L.DOOR["top"]
    ceiling = L.CHAMBER["top"]
    boolean(upper, box("door_recess", dx0, dx1, -1.0, 2.5, dz0, dz1 + 1.0, m["case"]))
    boolean(upper, box("door_top", dx0, dx1, -1.0, t, ceiling - 2.0, dz1 + 1.0, m["case"]))
    boolean(upper, box("chamber", dx0 + 2.0, dx1 - 2.0, 0.0, L.CHAMBER["depth"], b["top"] + 2.0, ceiling, m["case"]))
    colour(upper, m["case"], "case")
    paint(upper, m["case"], top_uv, lambda c, n, kind: n.z > 0.9 and c.z > L.HEIGHT - 0.5)
    paint(upper, m["case"], front_uv, lambda c, n, kind: n.y < -0.9 and c.y < 0.5)
    paint(upper, m["case"], swatch("dark"), lambda c, n, kind: dx0 - 0.5 < c.x < dx1 + 0.5
          and 2.0 < c.y < L.CHAMBER["depth"] + 1.0 and c.z < L.HEIGHT - 0.5)
    (bx0, bx1), (ry0, ry1), n, w = L.BAND["x"], L.RIBS["y"], L.RIBS["count"], L.RIBS["width"]
    ribs = []
    for k in range(n):
        y = ry0 + (ry1 - ry0) * (k + 0.5) / n
        rib = box("rib", bx0 + 1.0, bx1 - 1.0, y - w / 2, y + w / 2, L.HEIGHT - 0.5, L.HEIGHT + L.RIBS["height"],
                  m["case"])
        ribs.append(colour(rib, m["case"], "grey"))
    feet = [colour(box("foot", side * 100.0 - 8.0, side * 100.0 + 8.0, y - 8.0, y + 8.0, -0.5, 1.0, m["case"]),
                   m["case"], "dark") for side in (-1, 1) for y in (30.0, 170.0)]
    return join([base, upper] + ribs + feet, "nes")


def buttons(m):
    """POWER and RESET, each its back's middle at its origin, with where it goes; the red light, lit and unlit."""
    w, h, out = L.BUTTONS["size"]
    parts = {}
    for name in ("power", "reset"):
        x, z = L.BUTTONS[name]
        part = box(name, -w / 2, w / 2, -out, 1.0, -h / 2, h / 2, m["case"])
        bevel(part, 0.8, segments=1)
        colour(part, m["case"], "base")
        paint(part, m["case"], lambda co, x=x, z=z: front_uv(Vector((co.x + x, 0.0, co.z + z))),
              lambda c, n, kind: n.y < -0.9)
        parts[name] = (part, Vector((x, 0.0, z)))
    lx, lz = L.LIGHT["at"]
    s = L.LIGHT["size"]
    for name, tone in (("light", "lit"), ("light_off", "off")):
        part = box(name, -s / 2, s / 2, -0.4, 0.4, -s / 2, s / 2, m["case"])
        parts[name] = (colour(part, m["case"], tone), Vector((lx, 0.0, lz)))
    return parts


def door(m):
    """The door, an L-shaped flap: its face and its top plate from one (y, z) profile, the outer corner between them
    rounded as the body's edges are; the triangles closing its ends; the rod along the top plate's back edge, a pin out
    of each end. The face printed from in front, the top plate from above. Its origin on its pivot, the rod's axis."""
    (dx0, dx1), (dz0, dz1), g, t = L.DOOR["x"], L.DOOR["z"], L.DOOR["gap"], L.DOOR["top"]
    x0, x1 = dx0 + g, dx1 - g
    front, inner, top, under, r = 0.2, 2.4, dz1 - 0.2, dz1 - 2.2, 3.0
    corner = [(front + r + r * math.cos(math.radians(a)), top - r + r * math.sin(math.radians(a)))
              for a in range(180, 89, -15)]
    profile = [(front, dz0 + g)] + corner + [(t - g, top), (t - g, under), (inner, under), (inner, dz0 + g)]
    plate = prism_x("door", profile, x0, x1, m["case"])
    ends = [solid("door_end", [[(x, y, z) for y, z in ((inner, under), (inner, dz0 + g + 6.0), (t - g - 3.0, under))]
                               for x in (xa, xa + 1.4)], m["case"]) for xa in (x0 + 1.0, x1 - 2.4)]
    pivot = Vector(((dx0 + dx1) / 2, t - g - 1.2, dz1 - 1.2))
    ring = [(pivot.y + 1.3 * math.cos(2 * math.pi * k / 12), pivot.z + 1.3 * math.sin(2 * math.pi * k / 12))
            for k in range(12)]
    rod = solid("door_rod", [[(x, y, z) for y, z in ring] for x in (x0 - 2.0, x1 + 2.0)], m["case"])
    part = join([plate] + ends + [rod], "door")
    colour(part, m["case"], "case")
    paint(part, m["case"], front_uv, lambda c, n, kind: n.y < -0.9 and c.y < 0.5)
    paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.9 and c.z > top - 0.5)
    part.data.transform(Matrix.Translation(-pivot))
    return part, pivot


def cartridge(m):
    """The cartridge, lying flat, its front end's middle at its origin, its label up at its front end."""
    w, length, t = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, 0.0, length, -t / 2, t / 2, m["cart"])
    bevel(part, 1.4, segments=2)
    colour(part, m["cart"], "cart")
    face = atlas_uv(L.REGIONS["cart"], w, length)
    paint(part, m["cart"], lambda co: face(co.x + w / 2, co.y), lambda c, n, kind: n.z > 0.9)
    return part


# ---- The controller --------------------------------------------------------------------------------------------------

def controller(m):
    """The controller at its place: the slab; the cross, START, B and A apart (each with where it goes). Returns them,
    and where its cable leaves it and which way."""
    (w, d, h), P = L.PAD["size"], L.PAD
    x, y, turn = P["at"]
    spin = Matrix.Rotation(math.radians(turn), 4, "Z")
    place = Matrix.Translation((x, y, 0.0)) @ spin
    slab = solid("controller", [[(px, py, z) for px, py in rounded(0.0, 0.0, w - 1.0, d - 1.0, 3.0, 3)]
                                for z in (0.0, h)], m["case"])
    bevel(slab, 1.6, segments=2)
    colour(slab, m["case"], "case")
    paint(slab, m["case"], lambda co: PAD(co.x + w / 2, d / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    pill = box("select", -P["pill"][0] / 2, P["pill"][0] / 2, -P["pill"][1] / 2, P["pill"][1] / 2, h - 1.0, h + 1.2,
               m["case"])
    bevel(pill, 1.6, segments=3)
    sx, sy = P["pills"][0]
    pill.data.transform(Matrix.Translation((sx, sy, 0.0)))
    colour(pill, m["case"], "rubber")
    slab = join([slab, pill], "controller")
    slab.data.transform(place)

    moving = {}
    (cx, cy), arm, width = P["cross"]
    cross = join([box("arm", -arm, arm, -width / 2, width / 2, -1.0, 2.6, m["case"]),
                  box("arm", -width / 2, width / 2, -arm, arm, -1.0, 2.6, m["case"])], "cross")
    bevel(cross, 0.8, segments=2, angle=30)
    colour(cross, m["case"], "black")
    moving["cross"] = (cross, place @ Vector((cx, cy, h)))
    start = box("start", -P["pill"][0] / 2, P["pill"][0] / 2, -P["pill"][1] / 2, P["pill"][1] / 2, -1.0, 1.2,
                m["case"])
    bevel(start, 1.6, segments=3)
    colour(start, m["case"], "rubber")
    tx, ty = P["pills"][1]
    moving["start"] = (start, place @ Vector((tx, ty, h)))
    for name, (bx, by) in zip(("b", "a"), P["ba"]):
        ring = [(P["ba_r"] * math.cos(2 * math.pi * k / 20), P["ba_r"] * math.sin(2 * math.pi * k / 20))
                for k in range(20)]
        button = solid(name, [[(px, py, z) for px, py in ring] for z in (-1.0, 2.8)], m["case"])
        bevel(button, 0.8, segments=2)
        colour(button, m["case"], "red")
        moving[name] = (button, place @ Vector((bx, by, h)))
    for part, _ in moving.values():
        part.data.transform(spin)
    exit_ = (place @ Vector((18.0, d / 2 - 1.0, h * 0.5)), spin @ Vector((0.0, 1.0, 0.0)))
    return slab, moving, exit_


def cable(m, points):
    """The controller's cable: a tube along the Bézier curve through four control points."""
    p0, p1, p2, p3 = (Vector(p) for p in points)
    path = [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / 24 for k in range(25)]]
    bm = bmesh.new()
    rings, normal = [], Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(path):
        tangent = (path[min(k + 1, 24)] - path[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * 2.4)
                      for a in [2 * math.pi * j / 8 for j in range(8)]])
    for a, b in zip(rings, rings[1:]):
        for j in range(8):
            bm.faces.new([a[j], a[(j + 1) % 8], b[(j + 1) % 8], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return colour(new_object("cable", bm, m["case"]), m["case"], "black")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def opening(f):
    if f < 6:
        return 0.0
    if f < 46:
        return smooth(phase(f, 6, 16))
    if f < 176:
        return 1.0 - ease_in(phase(f, 46, 54))
    if f < 206:
        return smooth(phase(f, 176, 184))
    return 1.0 - ease_in(phase(f, 206, 214))


def timeline(f):
    out, down = L.CART["out"], L.CART["down"]
    if f < 14 or f >= 206:
        cart = Pose(y=-out, z=down, scale=HIDDEN)
    elif f < 20:
        cart = Pose(y=-out, z=down, scale=max(HIDDEN, back_out(phase(f, 14, 20))))
    elif f < 36:
        cart = Pose(y=-out * (1 - smooth(phase(f, 20, 36))), z=down)
    elif f < 184:
        cart = Pose(z=down * (1 - ease_in(phase(f, 36, 42))))
    elif f < 190:
        cart = Pose(z=down * ease_out(phase(f, 184, 190)))
    else:
        cart = Pose(y=-out * smooth(phase(f, 190, 202)), z=down, scale=max(HIDDEN, 1 - ease_in(phase(f, 200, 206))))
    on = 60 <= f < 172
    held = smooth(phase(f, 56, 60)) * (1 - smooth(phase(f, 170, 174)))        # POWER latches in while on
    t = phase(f, 70, 162)
    k = math.sin(math.pi * t)
    return {"door": Pose(pitch=L.DOOR["open"] * opening(f)), "cartridge": cart,
            "power": Pose(y=2.4 * held), "reset": Pose(y=2.4 * tap(f, 164)),
            "light": Pose() if on else Pose(y=SINK), "light_off": Pose(y=SINK) if on else Pose(),
            "start": Pose(z=-1.0 * tap(f, 64)),
            "cross": Pose(pitch=7.0 * k * math.sin(2 * math.pi * 3.0 * t),
                          roll=7.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "b": Pose(z=-1.8 * max(tap(f, f0) for f0 in (78, 102, 126, 150))),
            "a": Pose(z=-1.8 * max(tap(f, f0) for f0 in (90, 114, 138, 156)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "nes_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    pad, moving, (exit_at, exit_dir) = controller(m)
    black = (lambda o: colour(o, m["case"], "black"))
    relief, start, leaving = plugs.place(*plugs.grommet(black, 3.6), m["case"], exit_at, exit_dir)
    port = Vector((L.PORTS["x"][0], 0.0, sum(L.PORTS["z"]) / 2))
    plug, end, back = plugs.place(*plugs.nes(black, black), m["case"], port, (0.0, -1.0, 0.0))
    lead = cable(m, [start, start + leaving * 40.0 + Vector((0.0, 0.0, -6.0)), end + back * 50.0, end])
    whole = join([console(m), pad, lead] + relief + plug, "nes")
    for p in whole.data.polygons:
        p.use_smooth = p.area < 400.0                     # the big flat faces flat
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("nes_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    moving.update(buttons(m))
    moving["door"] = door(m)
    moving["cartridge"] = (cartridge(m), Vector(L.CART["seat"]))
    nodes = {}
    for name, (part, where) in moving.items():
        for p in part.data.polygons:
            p.use_smooth = p.area < 400.0                 # the door's and the cartridge's big faces flat
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
    print(f"NES: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
