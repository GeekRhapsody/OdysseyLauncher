"""The console theme's Acorn Archimedes system model (godot/themes/console/models/systems/archimedes.glb): a BBC A3000,
its three-button mouse and an Acorn colour monitor.

Built in Blender (archimedes_layout.py has the measurements, taken from photographs). The A3000 is its side outline
extruded across its width, the drive's slot cut into its right side; its 103 keys stand on the deck in the deck's frame,
each tapering to its printed top; the Acorn badge sits on the back block's front face. The mouse is a rounded box, its
select button apart. The monitor is a box, its housing tapering behind, the screen's opening cut into its front, on its
base; the tube's faces are curved screens sitting in the opening. The printing is two textures (archimedes_print.py's):
`print`, projected from above onto the A3000, its keys, the mouse and the floppy, and from in front onto the badge and
the monitor; and `media`, the screens.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the floppy (waiting outside the drive, shrunk to nothing), the drive's eject button and lit light, the tube's
four faces (those not shown behind the glass), the mouse and its select button, and the keys the clip presses.

The `focused` clip (8 s, looping): the floppy slides into the drive, its light flickering; the mouse clicks the drive's
icon and the filer window opens; a double click on !Odyssey, and the game plays on the cursor keys; Escape, the desktop
again, and the eject button: the floppy comes out and goes.

Two materials (case, glass) and two 1024² textures, within the system model budget. Run from the repo root:

    python tools/console-models/archimedes_print.py artifacts/archimedes
    blender -b --factory-startup --python tools/console-models/archimedes.py -- artifacts/archimedes godot/themes/console/models/systems/archimedes.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archimedes_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 20.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, glass=0.3)
SCREENS = ("desktop", "filer", "game_1", "game_2")
BEHIND = 3.0              # how far back a screen that isn't shown waits: behind the glass
ARROWS = dict(up="↑", left="←", down="↓", right="→")


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


DECK = atlas_uv(L.REGIONS["deck"], L.WIDTH, L.DEPTH)


def deck_uv(co):
    return DECK(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def on_deck(name, outline, h0, h1, mat, outline1=None):
    """A solid from an (x, s) outline in the deck's frame, from h0 off it to h1 (its top outline1, if given)."""
    top = outline1 or outline
    return solid(name, [[(x, *L.deck_point(s, h0)) for x, s in outline], [(x, *L.deck_point(s, h1)) for x, s in top]],
                 mat)


# ---- The A3000 -------------------------------------------------------------------------------------------------------

def a3000(m):
    """The case, the drive's slot cut into its right side, printed; the badge on its back block's front face."""
    half = L.WIDTH / 2
    body = prism_x("archimedes", L.PROFILE, -half, half, m["case"])
    bevel(body, 3.0, segments=2, angle=40)
    y0, y1, z0, z1 = L.DRIVE["slot"]
    boolean(body, box("slot", half - 40.0, half + 1.0, y0, y1, z0, z1, m["case"]))
    by, bz, bs = L.DRIVE["button"]
    boolean(body, box("button_hole", half - 4.0, half + 1.0, by - bs / 2, by + bs / 2, bz - bs / 2, bz + bs / 2,
                      m["case"]))
    colour(body, m["case"], "case")
    paint(body, m["case"], deck_uv, lambda c, n, kind: n.z > 0.3)
    (dy0, dy1), (dz0, dz1) = L.DRIVE["y"], L.DRIVE["z"]
    paint(body, m["case"], swatch("key"), lambda c, n, kind: n.x > 0.9 and dy0 < c.y < dy1 and dz0 < c.z < dz1)
    paint(body, m["case"], swatch("dark"), lambda c, n, kind: c.x < half - 0.5 and (
        y0 - 0.5 < c.y < y1 + 0.5 and z0 - 0.5 < c.z < z1 + 0.5
        or by - bs / 2 - 0.5 < c.y < by + bs / 2 + 0.5 and bz - bs / 2 - 0.5 < c.z < bz + bs / 2 + 0.5))
    (bx0, bx1), (bz0, bz1) = L.BADGE["x"], L.BADGE["z"]
    plate = box("badge", bx0, bx1, L.BLOCK - 0.8, L.BLOCK + 0.5, bz0, bz1, m["case"])
    colour(plate, m["case"], "case")
    face = atlas_uv(L.REGIONS["badge"], bx1 - bx0, bz1 - bz0)
    paint(plate, m["case"], lambda co: face(co.x - bx0, bz1 - co.z), lambda c, n, kind: n.y < -0.9)
    return join([body, plate], "archimedes")


def keys(m):
    """The keys, each tapering to its printed top; Escape and the cursor keys apart (each its foot's middle at its
    origin, with where it goes), the rest joined."""
    fixed, moving = [], {}
    inset, top = L.KEY["inset"], L.KEY["height"]
    cursor_x0 = L.KEYS_X0 + 15.5 * L.U - 0.1
    for legend, x0, x1, s0, s1 in L.keys():
        foot = [(x0 + 0.6, s0 + 0.5), (x1 - 0.6, s0 + 0.5), (x1 - 0.6, s1 - 0.5), (x0 + 0.6, s1 - 0.5)]
        cap = [(x0 + inset, s0 + inset - 0.5), (x1 - inset, s0 + inset - 0.5), (x1 - inset, s1 - inset + 0.5),
               (x0 + inset, s1 - inset + 0.5)]
        part = on_deck("key", foot, -1.0, top, m["case"], cap)
        red = legend[0] == "F" and legend[1:].isdigit()
        colour(part, m["case"], "red" if red else "key")
        paint(part, m["case"], deck_uv, lambda c, n, kind: n.z > 0.85)
        name = "escape" if legend == "Esc" else next((k for k, v in ARROWS.items() if v == legend and x0 > cursor_x0),
                                                     None)
        if name:
            middle = Vector(((x0 + x1) / 2, *L.deck_point((s0 + s1) / 2, -1.0)))
            part.data.transform(Matrix.Translation(-middle))
            moving[name] = (part, middle)
        else:
            fixed.append(part)
    return join(fixed, "keys"), moving


def drive_parts(m):
    """The drive's eject button and its lit light, each its front's middle at its origin, with where it goes."""
    half = L.WIDTH / 2
    by, bz, bs = L.DRIVE["button"]
    button = box("eject", -3.0, 0.0, -bs / 2 + 0.4, bs / 2 - 0.4, -bs / 2 + 0.4, bs / 2 - 0.4, m["case"])
    colour(button, m["case"], "key")
    ly, lz = L.DRIVE["light"]
    light = box("light", -0.4, 0.0, -1.6, 1.6, -0.8, 0.8, m["case"])
    colour(light, m["case"], "lit")
    return {"eject": (button, Vector((half + 0.6, by, bz))), "light": (light, Vector((half + 0.3, ly, lz)))}


def floppy(m):
    """The floppy, lying flat, its shutter's edge (going in first, along -x) at its origin, its label up."""
    w, d, t = L.FLOPPY["size"]
    part = box("floppy", 0.0, d, -w / 2, w / 2, -t / 2, t / 2, m["case"])
    colour(part, m["case"], "floppy")
    face = atlas_uv(L.REGIONS["floppy"], w, d)
    paint(part, m["case"], lambda co: face(co.y + w / 2, co.x), lambda c, n, kind: n.z > 0.9)
    return part


def mouse(m):
    """The mouse and its select button, each its foot's middle at its origin, turned as it lies; and where it sits."""
    w, length, h = L.MOUSE["size"]
    body = solid("mouse", [[(x, y, 0.0) for x, y in rounded(0.0, 0.0, w, length, 8.0, 3)],
                           [(x, y, h - 4.0) for x, y in rounded(0.0, -2.0, w - 8.0, length - 12.0, 6.0, 3)]],
                 m["case"])
    bevel(body, 3.0, segments=3)
    colour(body, m["case"], "case")
    face = atlas_uv(L.REGIONS["mouse"], w, length)
    paint(body, m["case"], lambda co: face(co.x + w / 2, length / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    bw = (w - 12.0) / 3
    button = box("select", -w / 2 + 6.0 + 1.2, -w / 2 + 6.0 + bw - 1.2, length / 2 - 34.0, length / 2 - 8.0, h - 5.0,
                 h - 2.6, m["case"])
    colour(button, m["case"], "key")
    x, y, turn = L.MOUSE["at"]
    for part in (body, button):
        part.data.transform(Matrix.Rotation(math.radians(turn), 4, "Z"))
    return body, button, Vector((x, y, 0.0))


# ---- The monitor -----------------------------------------------------------------------------------------------------

def monitor(m):
    """The monitor at its place: the base, the case with the screen's opening, its housing tapering behind, printed; the
    glass (the desktop on it)."""
    M, S = L.MONITOR, L.SCREEN
    w, h, d = M["width"], M["height"], M["depth"]
    (mx, my), (br, bh) = M["at"], M["base"]
    ring = [(mx + br * math.cos(2 * math.pi * k / 32), my + d * 0.45 + br * math.sin(2 * math.pi * k / 32))
            for k in range(32)]
    base = solid("base", [[(x, y, z) for x, y in ring] for z in (0.0, bh)], m["case"])
    colour(base, m["case"], "monitor")
    case = box("monitor", mx - w / 2, mx + w / 2, my, my + 90.0, bh, bh + h, m["case"])
    bevel(case, 6.0, segments=3)
    fw, fh, r = S["frame"]
    gw, gh = S["size"]
    opening = rounded(mx, S["z"], fw, fh, r, 4)
    inner = rounded(mx, S["z"], gw + 6.0, gh + 6.0, r * 0.6, 4)
    boolean(case, solid("opening", [[(x, y, z) for x, z in ring] for ring, y in
                                    ((opening, my - 10.0), (opening, my + 0.01), (inner, my + S["depth"]),
                                     (inner, my + S["depth"] + 1.0))], m["case"]))
    colour(case, m["case"], "monitor")
    face = atlas_uv(L.REGIONS["bezel"], w, h)
    paint(case, m["case"], lambda co: face(co.x - mx + w / 2, bh + h - co.z),
          lambda c, n, kind: n.y < -0.9 and c.y < my + 0.5)
    paint(case, m["case"], swatch("dark"),
          lambda c, n, kind: my + 0.5 < c.y < my + S["depth"] + 0.5 and abs(c.x - mx) < fw / 2 + 0.5)
    housing = solid("housing", [[(mx + x, y, z) for x, z in rounded(0.0, bh + h * 0.52, hw, hh, rr, 4)]
                                for y, hw, hh, rr in ((my + 86.0, w - 24.0, h - 24.0, 16.0),
                                                      (my + d, w * 0.6, h * 0.62, 24.0))], m["case"])
    bevel(housing, 4.0, segments=2, angle=50)
    colour(housing, m["case"], "monitor")
    glass = curved("glass", gw, gh, S["bulge"], atlas_uv(L.MEDIA_REGIONS["desktop"], 1.0, 1.0), m["glass"])
    glass.data.transform(Matrix.Translation((mx, my + S["depth"], S["z"])))
    return [base, case, housing, glass]


def screens(m):
    gw, gh = L.SCREEN["size"]
    return {name: curved(name, gw, gh, L.SCREEN["bulge"], atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0), m["glass"])
            for name in SCREENS}


def cable(m, points):
    """The mouse's cable: a tube along the Bézier curve through four control points."""
    p0, p1, p2, p3 = (Vector(p) for p in points)
    path = [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / 20 for k in range(21)]]
    bm = bmesh.new()
    rings, normal = [], Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(path):
        tangent = (path[min(k + 1, 20)] - path[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * 1.8)
                      for a in [2 * math.pi * j / 6 for j in range(6)]])
    for a, b in zip(rings, rings[1:]):
        for j in range(6):
            bm.faces.new([a[j], a[(j + 1) % 6], b[(j + 1) % 6], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return colour(new_object("cable", bm, m["case"]), m["case"], "cord")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def shown(f):
    if f < 52 or f >= 174:
        return "desktop"
    if f < 84:
        return "filer"
    return "game_1" if ((f - 84) // 6) % 2 == 0 else "game_2"


def glide(f):
    """The mouse's offset: to the drive's icon, to !Odyssey, and back."""
    a = smooth(phase(f, 38, 48))
    b = smooth(phase(f, 58, 70))
    back = smooth(phase(f, 176, 196))
    return (-14.0 * a + 10.0 * b) * (1 - back), (-12.0 * a + 16.0 * b) * (1 - back)


def timeline(f):
    out = L.FLOPPY["out"]
    if f < 10 or f >= 198:
        disk = Pose(x=out, scale=HIDDEN)
    elif f < 17:
        disk = Pose(x=out, scale=max(HIDDEN, back_out(phase(f, 10, 17))))
    elif f < 178:
        disk = Pose(x=out * (1 - smooth(phase(f, 17, 34))))
    elif f < 190:
        disk = Pose(x=out * smooth(phase(f, 178, 190)))
    else:
        disk = Pose(x=out, scale=max(HIDDEN, 1 - ease_in(phase(f, 192, 198))))
    reading = 34 <= f < 60 and (f // 3) % 3 != 2 or 178 <= f < 184
    mx, my = glide(f)
    click = max(tap(f, 48, 1), tap(f, 72, 1), tap(f, 77, 1))
    poses = {"floppy": disk, "eject": Pose(x=-2.0 * tap(f, 174)), "light": Pose() if reading else Pose(x=-1.0),
             "mouse": Pose(x=mx, y=my), "select": Pose(x=mx, y=my, z=-1.2 * click),
             "escape": Pose(z=-2.4 * tap(f, 168))}
    for name in SCREENS:
        poses[name] = Pose() if name == shown(f) else Pose(y=BEHIND)
    for name, times in (("up", (92, 120, 148)), ("left", (100, 132)), ("right", (108, 140, 156)), ("down", (116,))):
        poses[name] = Pose(z=-2.4 * max(tap(f, f0) for f0 in times))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    m = {"case": material("case", L.COLOURS["print"], ROUGHNESS["case"],
                          bpy.data.images.load(os.path.join(images, "archimedes_print.png"))),
         "glass": material("glass", L.COLOURS["print"], ROUGHNESS["glass"],
                           bpy.data.images.load(os.path.join(images, "archimedes_media.png")))}

    fixed_keys, moving = keys(m)
    moving.update(drive_parts(m))
    body, button, at = mouse(m)
    moving.update({"mouse": (body, at), "select": (button, at)})
    turn = math.radians(L.MOUSE["at"][2])
    front = at + Vector((-math.sin(turn), math.cos(turn), 0.0)) * (L.MOUSE["size"][1] / 2 - 2.0)
    lead = cable(m, [(front.x, front.y, 10.0), (front.x, front.y + 50.0, 1.8), (L.WIDTH / 2 + 20.0, L.DEPTH, 1.8),
                     (L.WIDTH / 2 - 30.0, L.DEPTH + 1.0, 30.0)])
    whole = join([a3000(m), fixed_keys, lead] + monitor(m), "archimedes")
    for p in whole.data.polygons:
        p.use_smooth = p.area < 400.0                     # the big flat faces flat
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("archimedes_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    y0, y1, z0, z1 = L.DRIVE["slot"]
    moving["floppy"] = (floppy(m), Vector((L.WIDTH / 2 + 3.0 - L.FLOPPY["size"][1], (y0 + y1) / 2, (z0 + z1) / 2)))
    (mx, my), S = L.MONITOR["at"], L.SCREEN
    glass_front = Vector((mx, my + S["depth"] - 0.4, S["z"]))
    moving.update({name: (part, glass_front) for name, part in screens(m).items()})
    nodes = {}
    for name, (part, where) in moving.items():
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
    print(f"Archimedes: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
