"""The console theme's Macintosh system model (godot/themes/console/models/systems/macintosh.glb): the original Apple
Macintosh, its keyboard and its mouse.

Built in Blender (macintosh_layout.py has the measurements, taken from its housing's design patent and photographs). The
case is its side outline extruded across its width; the screen's sunk frame, the floppy slot and its finger recess are
cut into the front face in the face's frame, the handle into the back of the top, the vents into the sides' foot. The
tube's faces are curved screens sitting in the frame; the rainbow Apple a badge on the face. The keyboard is a slab, its
keys standing on its sloping top, its coiled cord sagging to the chin's front; the mouse a rounded box, its button a
plate across the front of its top, its cable running round the case's right to the back. The printing and the screens
are one texture (macintosh_print.py's), projected from above onto the keys, the mouse and the floppy, and onto the badge
and the screens along the face.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the floppy (waiting in front of the slot, shrunk to nothing), the tube's four faces (each in its frame, those
not shown a hair behind the one shown), the mouse and its button.

The `focused` clip (8 s, looping): the floppy slides into the drive; the question mark gives way to the happy Mac, then
Welcome to Macintosh., then the game in its window, the mouse moving and clicking; then the floppy comes out of the
drive and goes, and the question mark is back.

Four materials (case, keys, screen, floppy) and one 1024² texture, within the system model budget. Run from the repo
root:

    python tools/console-models/macintosh_print.py artifacts/macintosh
    blender -b --factory-startup --python tools/console-models/macintosh.py -- artifacts/macintosh godot/themes/console/models/systems/macintosh.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import macintosh_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 16.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, keys=0.45, screen=0.3, floppy=0.4)
OUT = Vector(L.face_point(0.0, 0.0, 1.0)) - Vector(L.face_point(0.0, 0.0, 0.0))     # out of the front face
UP = Vector(L.face_point(0.0, 1.0, 0.0)) - Vector(L.face_point(0.0, 0.0, 0.0))      # up it
BEHIND = 1.5              # how far back the tube's faces not shown wait
SCREENS = ("disk", "happy", "welcome", "game")


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


def on_face(name, outline, w0, w1, mat, outline1=None):
    """A solid from a (u, v) outline in the front face's frame, from w0 out of it to w1 (its outline there outline1)."""
    top = outline1 or outline
    return solid(name, [[L.face_point(u, v, w0) for u, v in outline], [L.face_point(u, v, w1) for u, v in top]], mat)


def rect(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def face_frame(c):
    """A point's (u, v, w) in the front face's frame."""
    d = c - Vector(L.face_point(0.0, 0.0, 0.0))
    return c.x, d.dot(UP), d.dot(OUT)


# ---- The case --------------------------------------------------------------------------------------------------------

def case(m):
    """The case with the screen's frame, the slot, its finger recess, the handle and the vents cut in; painted."""
    half = L.WIDTH / 2
    body = prism_x("macintosh", L.PROFILE, -half, half, m["case"])
    bevel(body, 4.0, segments=3, angle=30)
    (fw, fh, fr), (gw, gh, gr), sv, depth = L.SCREEN["frame"], L.SCREEN["glass"], L.SCREEN["v"], L.SCREEN["depth"]
    rim = rounded(0.0, sv, fw, fh, fr, 4)
    tube = rounded(0.0, sv, gw, gh, gr, 4)
    boolean(body, solid("frame", [[L.face_point(u, v, w) for u, v in ring] for ring, w in
                                  ((tube, -depth), (rim, 0.0), (rim, 8.0))], m["case"]))
    (u0, u1), (v0, v1) = L.SLOT["u"], L.SLOT["v"]
    boolean(body, on_face("slot", rect(u0, u1, v0, v1), -L.SLOT["depth"], 5.0, m["case"]))
    (nu0, nu1), (nv0, nv1) = L.NOTCH["u"], L.NOTCH["v"]
    notch = rounded((nu0 + nu1) / 2, (nv0 + nv1) / 2, nu1 - nu0, nv1 - nv0, L.NOTCH["r"], 3)
    boolean(body, on_face("notch", notch, -L.NOTCH["depth"], 5.0, m["case"]))
    hx, hy, hz = L.HANDLE["x"], L.HANDLE["y"], L.HANDLE["z"]
    boolean(body, box("handle", -hx, hx, hy, L.DEPTH + 10.0, hz, L.HEIGHT + 10.0, m["case"]))
    (vy0, vy1), vh, vd = L.VENTS["y"], L.VENTS["height"], L.VENTS["depth"]
    for z in L.VENTS["z"]:
        for side in (-1, 1):
            boolean(body, box("vent", side * half - vd, side * half + vd, vy0, vy1, z - vh / 2, z + vh / 2, m["case"]))
    colour(body, m["case"], "case")
    paint(body, m["case"], swatch("tube"), lambda c, n, kind: -depth - 0.5 < face_frame(c)[2] < -depth + 0.5
          and abs(c.x) < gw / 2 + 1.0 and abs(face_frame(c)[1] - sv) < gh / 2 + 1.0)
    paint(body, m["case"], swatch("dark"), lambda c, n, kind: u0 - 0.5 < c.x < u1 + 0.5
          and v0 - 0.5 < face_frame(c)[1] < v1 + 0.5 and face_frame(c)[2] < -L.NOTCH["depth"] - 0.5)
    paint(body, m["case"], swatch("dark"), lambda c, n, kind: abs(abs(c.x) - half) < vd + 0.3 and vy0 - 0.5 < c.y
          < vy1 + 0.5 and any(abs(c.z - z) < vh / 2 + 0.3 for z in L.VENTS["z"]) and abs(n.x) < 0.9)
    (au0, au1), (av0, av1) = L.APPLE["u"], L.APPLE["v"]
    badge = on_face("apple", rect(au0, au1, av0, av1), -0.5, 0.5, m["case"])
    colour(badge, m["case"], "case")
    face = atlas_uv(L.REGIONS["apple"], au1 - au0, av1 - av0)
    paint(badge, m["case"], lambda co: face(co.x - au0, av1 - face_frame(co)[1]),
          lambda c, n, kind: n.dot(OUT) > 0.9)
    return join([body, badge], "macintosh")


def screen(m, name):
    """One of the tube's faces, its middle at its origin, facing out of the front face."""
    gw, gh, _ = L.SCREEN["glass"]
    rx, ry, rw, rh = L.REGIONS[name]
    part = curved(name, gw, gh, L.SCREEN["bulge"], lambda a, b: ((rx + a * rw) / L.ATLAS, 1 - (ry + b * rh) / L.ATLAS),
                  m["screen"], 16, 12)
    part.data.transform(Matrix.Rotation(-L.LEAN, 4, "X"))
    return part


# ---- The keyboard, the mouse, the floppy, the cords ------------------------------------------------------------------

def keyboard(m):
    """The keyboard: the slab and its keys, at its place."""
    w, d = L.KEYBOARD["size"]
    hf, hb = L.KEYBOARD["height"]
    slope = math.atan2(hb - hf, d)
    c, k = math.cos(slope), math.sin(slope)

    def deck(s, h):
        return s * c - h * k, hf + s * k + h * c
    slab = prism_x("keyboard", [(0.0, 0.0), (d, 0.0), (d, hb), (0.0, hf)], -w / 2, w / 2, m["case"])
    bevel(slab, 3.0, segments=3, angle=30)
    colour(slab, m["case"], "case")
    face = atlas_uv(L.REGIONS["keys"], w, d)
    parts, inset = [slab], L.KEY["inset"]
    for legend, x0, x1, s in L.keys():
        foot = [(x0 + 0.5, s - 9.0), (x1 - 0.5, s - 9.0), (x1 - 0.5, s + 9.0), (x0 + 0.5, s + 9.0)]
        cap = [(x0 + inset, s - 9.5 + inset), (x1 - inset, s - 9.5 + inset), (x1 - inset, s + 9.5 - inset),
               (x0 + inset, s + 9.5 - inset)]
        part = solid("key", [[(x, *deck(v, -1.0)) for x, v in foot], [(x, *deck(v, L.KEY["height"])) for x, v in cap]],
                     m["keys"])
        colour(part, m["keys"], "key")
        paint(part, m["keys"], lambda co: face(co.x + w / 2, d - co.y), lambda c_, n, kind: n.z > 0.9)
        parts.append(part)
    whole = join(parts, "keyboard")
    x, y = L.KEYBOARD["at"]
    whole.data.transform(Matrix.Translation((x, y - d, 0.0)))
    return whole


def mouse(m):
    """The mouse and its button, each its foot's middle at its origin, its front (the button, the cable) to +y; and
    where its middle sits."""
    w, length, h = L.MOUSE["size"]
    body = solid("mouse", [[(x, y, 0.0) for x, y in rounded(0.0, 0.0, w, length, 6.0, 3)],
                           [(x, y, h) for x, y in rounded(0.0, 0.0, w - 6.0, length - 6.0, 4.0, 3)]], m["case"])
    bevel(body, 2.5, segments=3)
    colour(body, m["case"], "case")
    face = atlas_uv(L.REGIONS["mouse"], w, length)
    paint(body, m["case"], lambda co: face(co.x + w / 2, length / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    span = length * L.MOUSE["button"]
    button = box("button", -w / 2 + 6.0, w / 2 - 6.0, length / 2 - span, length / 2 - 4.0, h - 1.0, h + 0.8, m["case"])
    bevel(button, 0.6, segments=1)
    colour(button, m["case"], "case")
    paint(button, m["case"], lambda co: face(co.x + w / 2, length / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    x, y, turn = L.MOUSE["at"]
    for part in (body, button):
        part.data.transform(Matrix.Rotation(math.radians(turn), 4, "Z"))
    return body, button, Vector((x, y, 0.0))


def floppy(m):
    """The floppy, its back edge's middle at its origin, lying in the slot's plane, its shutter going in first."""
    w, d, t = L.FLOPPY["size"]
    part = box("floppy", -w / 2, w / 2, 0.0, d, -t / 2, t / 2, m["floppy"])
    colour(part, m["floppy"], "floppy")
    top = atlas_uv(L.REGIONS["floppy"], w, d)
    paint(part, m["floppy"], lambda co: top(co.x + w / 2, d - co.y), lambda c, n, kind: n.z > 0.9)
    frame = Matrix(((1.0, 0.0, 0.0, 0.0), (0.0, -OUT.y, UP.y, 0.0), (0.0, -OUT.z, UP.z, 0.0), (0.0, 0.0, 0.0, 1.0)))
    part.data.transform(frame)                           # +y going in (against the face), +z up the face
    return part


def tube(name, m, path, radius, tone):
    """A cable: a tube along a path of points."""
    bm = bmesh.new()
    rings, normal = [], Vector((0.0, 0.0, 1.0))
    n = len(path)
    for k, p in enumerate(path):
        tangent = (path[min(k + 1, n - 1)] - path[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent))
        if normal.length < 1e-6:
            normal = Vector((1.0, 0.0, 0.0))
        normal.normalize()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * radius)
                      for a in [2 * math.pi * j / 6 for j in range(6)]])
    for a, b in zip(rings, rings[1:]):
        for j in range(6):
            bm.faces.new([a[j], a[(j + 1) % 6], b[(j + 1) % 6], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return colour(new_object(name, bm, m["case"]), m["case"], tone)


def bezier(points, count):
    p0, p1, p2, p3 = (Vector(p) for p in points)
    return [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / (count - 1) for k in range(count)]]


def coiled(points, turns, radius):
    """A coiled cord's path: a helix wound round the Bézier curve through four control points."""
    centre = bezier(points, turns * 10 + 1)
    out, normal = [], Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(centre):
        tangent = (centre[min(k + 1, len(centre) - 1)] - centre[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        a = 2 * math.pi * k / 10
        fade = min(1.0, k / 10, (len(centre) - 1 - k) / 10)     # straight where it plugs in
        out.append(p + (normal * math.cos(a) + binormal * math.sin(a)) * radius * fade)
    return out


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def shown(f):
    if f < 36 or f >= 178:
        return "disk"
    if f < 64:
        return "happy"
    if f < 92:
        return "welcome"
    return "game"


def timeline(f):
    far = L.FLOPPY["size"][1] + L.FLOPPY["out"]
    if f < 10 or f >= 198:
        out, scale = far, HIDDEN
    elif f < 16:
        out, scale = far, max(HIDDEN, back_out(phase(f, 10, 16)))
    elif f < 176:
        out, scale = far * (1 - smooth(phase(f, 16, 32))), 1.0
    elif f < 186:
        out, scale = 40.0 * smooth(phase(f, 176, 186)), 1.0
    else:
        out, scale = 40.0 + (far - 40.0) * smooth(phase(f, 186, 196)), max(HIDDEN, 1 - ease_in(phase(f, 192, 198)))
    d = OUT * out
    poses = {"floppy": Pose(x=d.x, y=d.y, z=d.z, scale=scale)}
    behind = -OUT * BEHIND
    for name in SCREENS:
        poses[name] = Pose() if name == shown(f) else Pose(x=behind.x, y=behind.y, z=behind.z)
    t = phase(f, 96, 170)
    k = math.sin(math.pi * t)
    mx, my = 14.0 * k * math.sin(2 * math.pi * 1.5 * t), 9.0 * k * math.sin(2 * math.pi * 2.5 * t)
    poses["mouse"] = Pose(x=mx, y=my)
    poses["button"] = Pose(x=mx, y=my, z=-0.8 * max(tap(f, f0, 1) for f0 in (112, 134, 154)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "macintosh_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    body, button, at = mouse(m)
    kw, kd = L.KEYBOARD["size"]
    kx, ky = L.KEYBOARD["at"]
    jx, jz = L.JACK
    chin = L.PROFILE[2][0]
    cord = tube("keyboard_cord", m, coiled([(kx + 80.0, ky - 2.0, 20.0), (kx + 85.0, ky + 20.0, 6.0),
                                            (jx, chin - 30.0, 6.0), (jx, chin + 1.0, jz)], 9, 3.2), 1.2, "cord")
    turn = math.radians(L.MOUSE["at"][2])
    front = at + Vector((-math.sin(turn), math.cos(turn), 0.0)) * (L.MOUSE["size"][1] / 2 - 2.0)
    cable = tube("mouse_cable", m, bezier([(front.x, front.y, 12.0), (front.x, front.y + 40.0, 2.4),
                                           (L.WIDTH / 2 + 30.0, 150.0, 2.4), (L.WIDTH / 2 - 20.0, L.DEPTH + 1.0, 30.0)],
                                          30), 1.6, "cord")
    whole = join([case(m), keyboard(m), cord, cable], "macintosh")
    for p in whole.data.polygons:
        p.use_smooth = p.area < 400.0                     # the big flat faces flat: no streaks across the sides
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("macintosh_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (u0, u1), (v0, v1) = L.SLOT["u"], L.SLOT["v"]
    glass = L.face_point(0.0, L.SCREEN["v"], -L.SCREEN["depth"] + 0.6)
    parts = {"floppy": (floppy(m), Vector(L.face_point((u0 + u1) / 2, (v0 + v1) / 2, -2.0))), "mouse": (body, at),
             "button": (button, at)}
    for name in SCREENS:
        parts[name] = (screen(m, name), Vector(glass))
    nodes = {}
    for name, (part, where) in parts.items():
        if name not in SCREENS:
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
    print(f"Macintosh: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
