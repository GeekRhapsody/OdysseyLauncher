"""The console theme's Sega Saturn system model (godot/themes/console/models/systems/saturn.glb): the black Model 1
Saturn and its control pad.

Built in Blender (saturn_layout.py has the measurements, taken from photographs and published figures). The console is
its side outline extruded across its width and cut round its plan's corners; the ports' band is cut back under the brow,
the ports into it, the CD's well and the slot into its top and the vents into its right side. POWER, OPEN and RESET
stand on the top's front band, the ACCESS light between them; the lid is a dome over the well, hinged at its back, the
spindle standing in the well. The pad is its smoothed outline raised and rounded, the D-pad's disc and the buttons
standing on it, L and R on its top edge, its cable running to its plug in the first port (plugs.py's). The printing is
one texture (saturn_print.py's), projected from above onto the top, the lid, the pad and the CD, and from in front onto
the front.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (on its hinge), the CD (waiting over the well, shrunk to nothing), POWER, OPEN and RESET, the ACCESS
light (sunk while off), and the pad's D-pad, A, B, C and START.

The `focused` clip (8 s, looping): OPEN, the lid swings up, the CD comes down onto the spindle and the lid shuts; POWER,
the ACCESS light flickers while the CD is read; START, and the D-pad rocks while A, B and C fire; then OPEN again, the
CD rises out and goes, and the lid shuts.

Two materials (case, disc) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/saturn_print.py artifacts/saturn
    blender -b --factory-startup --python tools/console-models/saturn.py -- artifacts/saturn godot/themes/console/models/systems/saturn.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plugs  # noqa: E402
import saturn_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.35, disc=0.2)
SINK = 1.2                # how far an unlit light sinks below the top


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
PAD = atlas_uv(L.REGIONS["pad"], 160.0, 100.0)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def disc(name, x, y, r, z0, z1, mat, segments=32, squash=1.0):
    ring = [(x + r * math.cos(2 * math.pi * k / segments), y + squash * r * math.sin(2 * math.pi * k / segments))
            for k in range(segments)]
    return solid(name, [[(px, py, z) for px, py in ring] for z in (z0, z1)], mat)


def smooth_outline(points, per=5):
    """A closed outline through points, smoothed by a Catmull-Rom spline (per points to each span)."""
    out, n = [], len(points)
    for i in range(n):
        p0, p1, p2, p3 = (Vector(points[(i + k) % n]) for k in (-1, 0, 1, 2))
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    return out


def inset(outline, d):
    """A closed outline moved d inwards (its corners mitred), whichever way round it runs."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:                                           # clockwise: its left, where the normals point, is outside
        d = -d
    out, n = [], len(outline)
    for i in range(n):
        p0, p1, p2 = (Vector(outline[(i + k) % n]) for k in (-1, 0, 1))
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))
        bis = (n0 + n1).normalized()
        out.append(tuple(p1 + bis * (d / max(0.3, bis.dot(n0)))))
    return out


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The case with the band, the ports, the well, the lid's seat, the slot and the vents cut in; printed; its feet."""
    half = L.WIDTH / 2
    body = prism_x("saturn", L.PROFILE, -half - 1.0, half + 1.0, m["case"])
    plan = rounded(0.0, L.DEPTH / 2, L.WIDTH, L.DEPTH, L.CORNER, 5)
    boolean(body, prism_z("plan", plan, -1.0, L.HEIGHT + 10.0, m["case"]), "INTERSECT")
    bevel(body, 2.0, segments=2, angle=40)
    (bx0, bx1), (by0, by1), (bz0, bz1) = L.BAND["x"], L.BAND["y"], L.BAND["z"]
    boolean(body, box("band", bx0, bx1, by0, by1, bz0, bz1, m["case"]))
    (pw, ph), pz = L.PORTS["size"], L.PORTS["z"]
    for x in L.PORTS["x"]:
        boolean(body, box("port", x - pw / 2, x + pw / 2, by1 - 1.0, by1 + 6.0, pz - ph / 2, pz + ph / 2, m["case"]))
    seat = inset(L.lid_outline(16), -1.0)
    boolean(body, prism_z("seat", seat, L.HEIGHT - 2.0, L.HEIGHT + 5.0, m["case"]))
    (wx, wy), wr = L.WELL["at"], L.WELL["r"]
    boolean(body, disc("well", wx, wy, wr, L.HEIGHT - L.WELL["depth"], L.HEIGHT, m["case"], 48))
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    boolean(body, box("slot", sx0, sx1, sy0, sy1, L.HEIGHT - L.SLOT["depth"], L.HEIGHT + 5.0, m["case"]))
    (vy0, vy1), (vz0, vz1), n = L.VENTS["y"], L.VENTS["z"], L.VENTS["count"]
    for k in range(n):
        y = vy0 + (vy1 - vy0) * (k + 0.5) / n
        boolean(body, box("vent", half - 3.0, half + 2.0, y - 2.2, y + 2.2, vz0, vz1, m["case"]))
    colour(body, m["case"], "case")
    paint(body, m["case"], top_uv, lambda c, n_, kind: n_.z > 0.5 and c.z > L.HEIGHT - 2.5)
    paint(body, m["case"], lambda co: FRONT(co.x + half, L.HEIGHT - co.z), lambda c, n_, kind: n_.y < -0.9)

    def dark(c, n):
        """In the well, or in a vent."""
        return (math.hypot(c.x - wx, c.y - wy) < wr + 0.5 and c.z < L.HEIGHT - 2.5
                or half - 3.5 < c.x and vy0 - 1.0 < c.y < vy1 + 1.0 and vz0 - 0.5 < c.z < vz1 + 0.5 and n.x < 0.9)
    paint(body, m["case"], swatch("dark"), lambda c, n_, kind: dark(c, n_))
    spindle = disc("spindle", wx, wy, 7.0, L.HEIGHT - L.WELL["depth"] - 1.0, L.HEIGHT - L.WELL["depth"] + 9.0,
                   m["case"], 20)
    colour(spindle, m["case"], "button")
    feet = [colour(disc("foot", side * (half - 30.0), y, 0.0, L.FEET + 1.0, 9.0, m["case"], 16), m["case"], "dark")
            for side in (-1, 1) for y in (30.0, L.DEPTH - 30.0)]
    return join([body, spindle] + feet, "saturn")


def buttons(m):
    """POWER, OPEN and RESET, each its foot's middle at its origin, with where it goes; and the ACCESS light."""
    z = L.HEIGHT
    out = {}
    (px, py, pw, pd) = L.BUTTONS["power"]
    power = disc("power", 0.0, 0.0, pw / 2, -1.0, 2.5, m["case"], 28, squash=pd / pw)
    (ox, oy, ow, od) = L.BUTTONS["open"]
    opener = box("open", -ow / 2, ow / 2, -od / 2, od / 2, -1.0, 2.2, m["case"])
    bevel(opener, 1.0, segments=2)
    (rx, ry, rr) = L.BUTTONS["reset"]
    reset = disc("reset", 0.0, 0.0, rr, -1.0, 2.2, m["case"], 24)
    for name, part, (x, y) in (("power", power, (px, py)), ("open", opener, (ox, oy)), ("reset", reset, (rx, ry))):
        colour(part, m["case"], "button")
        paint(part, m["case"], lambda co, x=x, y=y: top_uv(Vector((co.x + x, co.y + y, 0.0))),
              lambda c, n, kind: n.z > 0.9)
        out[name] = (part, Vector((x, y, z)))
    ax, ay = L.BUTTONS["access"]
    for name, tone in (("access", "lit"), ("access_off", "off")):
        part = disc(name, 0.0, 0.0, 1.8, -0.4, 0.3, m["case"], 12)
        colour(part, m["case"], tone)
        out[name] = (part, Vector((ax, ay, z)))
    return out


def lid(m):
    """The lid: a dome over the well, printed on top, its origin on its hinge along its back edge."""
    outline = L.lid_outline(16)
    part = solid("lid", [[(x, y, z) for x, y in ring] for ring, z in
                         ((outline, L.HEIGHT - 1.6), (outline, L.HEIGHT + 2.0),
                          (inset(outline, L.LID["inset"]), L.HEIGHT + L.LID["height"]))], m["case"])
    bevel(part, 2.0, segments=3, angle=30)
    colour(part, m["case"], "case")
    paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.2)
    hinge = Vector((0.0, L.LID["back"], L.HEIGHT))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def compact_disc(m):
    """The CD, its middle at its origin, its label up."""
    r, t = L.DISC["r"], L.DISC["thickness"]
    part = disc("cd", 0.0, 0.0, r, -t / 2, t / 2, m["disc"], 64)
    colour(part, m["disc"], "disc")
    face = atlas_uv(L.REGIONS["disc"], 2 * r, 2 * r)
    paint(part, m["disc"], lambda co: face(co.x + r, r - co.y), lambda c, n, kind: n.z > 0.9)
    return part


# ---- The pad ---------------------------------------------------------------------------------------------------------

def pad(m):
    """The pad at its place: the body with L, R, X, Y, Z and the cable's sleeve; the D-pad, A, B, C and START apart."""
    P = L.PAD
    x, y, turn = P["at"]
    place = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
    outline = smooth_outline(P["points"])
    h = P["height"]
    # A rounded profile: the outline's inset at each height, fullest a third of the way up.
    profile = ((0.0, 5.0), (0.12, 1.8), (0.3, 0.0), (0.55, 0.4), (0.78, 2.2), (0.92, 4.4), (1.0, 6.5))
    body = solid("pad", [[(px, py, h * z) for px, py in (inset(outline, d) if d else outline)] for z, d in profile],
                 m["case"])
    colour(body, m["case"], "pad")

    def pad_uv(co):
        return PAD(co.x + 80.0, 50.0 - co.y)
    paint(body, m["case"], pad_uv, lambda c, n, kind: n.z > 0.85)
    parts = [body]
    for side in (-1, 1):                                    # L and R on the top edge
        shoulder = box("shoulder", side * 40.0 - 12.0, side * 40.0 + 12.0, 37.0, 44.0, h * 0.4, h - 3.0, m["case"])
        bevel(shoulder, 1.5, segments=2)
        parts.append(colour(shoulder, m["case"], "button"))
    for (bx, by) in P["xyz"]:
        button = disc("xyz", bx, by, P["xyz_r"], h - 1.0, h + 2.4, m["case"], 20)
        colour(button, m["case"], "button")
        paint(button, m["case"], pad_uv, lambda c, n, kind: n.z > 0.9)
        parts.append(button)
    sleeve = disc("sleeve", 0.0, 46.0, 4.0, 4.0, 14.0, m["case"], 12)
    sleeve.data.transform(Matrix.Translation((0.0, 46.0, 9.0)) @ Matrix.Rotation(math.radians(90.0), 4, "X")
                          @ Matrix.Translation((0.0, -46.0, -9.0)))
    parts.append(colour(sleeve, m["case"], "cable"))
    whole = join(parts, "pad")
    whole.data.transform(place)

    moving = {}
    (dx, dy), dr = P["dpad"]
    dpad = solid("dpad", [[(dx + r * math.cos(2 * math.pi * k / 32), dy + r * math.sin(2 * math.pi * k / 32), z)
                           for k in range(32)] for r, z in ((dr, -1.0), (dr, 1.6), (dr * 0.8, 3.4))], m["case"])
    colour(dpad, m["case"], "button")
    paint(dpad, m["case"], pad_uv, lambda c, n, kind: n.z > 0.5)
    dpad.data.transform(Matrix.Translation((-dx, -dy, 0.0)))
    moving["dpad"] = (dpad, place @ Vector((dx, dy, h)))
    for name, (bx, by) in zip(("a", "b", "c"), P["abc"]):
        button = disc(name, bx, by, P["abc_r"], -1.0, 3.2, m["case"], 24)
        colour(button, m["case"], "button")
        paint(button, m["case"], pad_uv, lambda c, n, kind: n.z > 0.9)
        button.data.transform(Matrix.Translation((-bx, -by, 0.0)))
        moving[name] = (button, place @ Vector((bx, by, h)))
    (sx, sy), (sw, sh) = P["start"]
    start = disc("start", sx, sy, sw / 2, -1.0, 1.6, m["case"], 20, squash=sh / sw)
    colour(start, m["case"], "button")
    start.data.transform(Matrix.Translation((-sx, -sy, 0.0)))
    moving["start"] = (start, place @ Vector((sx, sy, h)))
    for part, _ in moving.values():
        part.data.transform(Matrix.Rotation(math.radians(turn), 4, "Z"))
    return whole, moving, place @ Vector((0.0, 46.0 + 10.0, 9.0))


def cable(m, points):
    """The pad's cable: a tube along the Bézier curve through four control points."""
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
    return colour(new_object("cable", bm, m["case"]), m["case"], "cable")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def opening(f):
    if f < 10:
        return 0.0
    if f < 44:
        return back_out(phase(f, 10, 22), 1.4)
    if f < 176:
        return 1.0 - ease_in(phase(f, 44, 54))
    if f < 206:
        return back_out(phase(f, 176, 188), 1.4)
    return 1.0 - ease_in(phase(f, 206, 214))


def timeline(f):
    above = L.DISC["above"]
    if f < 22 or f >= 200:
        cd = Pose(z=above, scale=HIDDEN)
    elif f < 29:
        cd = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 22, 29))))
    elif f < 186:
        cd = Pose(z=above * (1 - ease_in(phase(f, 29, 40))), spin=-360.0 * max(0.0, phase(f, 62, 172)) * 8.0)
    else:
        cd = Pose(z=above * ease_out(phase(f, 186, 196)), scale=max(HIDDEN, 1 - ease_in(phase(f, 194, 200))))
    reading = 62 <= f < 100 and (f // 3) % 3 != 2 or 104 <= f < 168 and (f // 9) % 4 == 0
    t = phase(f, 106, 168)
    k = math.sin(math.pi * t)
    return {"lid": Pose(pitch=L.LID["open"] * opening(f)), "cd": cd,
            "open": Pose(z=-1.6 * max(tap(f, 7), tap(f, 173))), "power": Pose(z=-1.8 * tap(f, 58)),
            "reset": Pose(), "access": Pose() if reading else Pose(z=-SINK),
            "access_off": Pose(z=-SINK) if reading else Pose(),
            "start": Pose(z=-1.2 * tap(f, 102)),
            "dpad": Pose(pitch=8.0 * k * math.sin(2 * math.pi * 3.0 * t),
                         roll=8.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "a": Pose(z=-2.0 * max(tap(f, f0) for f0 in (112, 136, 158))),
            "b": Pose(z=-2.0 * max(tap(f, f0) for f0 in (120, 146))),
            "c": Pose(z=-2.0 * max(tap(f, f0) for f0 in (128, 152)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "saturn_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    body, moving, sleeve = pad(m)
    black = (lambda o: colour(o, m["case"], "cable"))
    port = Vector((L.PORTS["x"][0], L.BAND["y"][1], L.PORTS["z"]))
    plug, end, back = plugs.place(*plugs.saturn(black, black), m["case"], port, (0.0, -1.0, 0.0))
    lead = cable(m, [sleeve, sleeve + Vector((0.0, 40.0, -6.0)), end + back * 45.0, end])
    whole = join([console(m), body, lead] + plug, "saturn")
    for p in whole.data.polygons:
        p.use_smooth = p.area < 400.0                     # the big flat faces flat
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("saturn_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    moving.update(buttons(m))
    moving["lid"] = lid(m)
    (wx, wy) = L.WELL["at"]
    moving["cd"] = (compact_disc(m), Vector((wx, wy, L.HEIGHT - L.WELL["depth"] + 9.0 + L.DISC["thickness"] / 2)))
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
    print(f"Saturn: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
