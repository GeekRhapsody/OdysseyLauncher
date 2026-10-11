"""The console theme's DOS, Windows 3.x and Windows 9x system models (godot/themes/console/models/systems/
dos.glb, windows3x.glb, windows9x.glb): a beige PC of each one's era and its CRT monitor.

- dos: a late-80s 386 desktop (460 x 420 x 150 mm), its 5.25 and 3.5-inch floppy drives on the right, the badge,
  turbo display, lights, buttons and keylock on the left; on it a 14-inch VGA monitor with knobs under its screen.
- windows3x: an early-90s 486 desktop (440 x 410 x 140 mm) with a 5.25-inch floppy, a caddy-loading CD-ROM and a
  3.5-inch floppy; on it a 14-inch SVGA monitor.
- windows9x: a late-90s mini tower (190 x 430 x 420 mm) with a tray-loading CD-ROM, a blank bay and a 3.5-inch floppy;
  to its right, on the desk, a 15-inch monitor with on-screen menu buttons.

The case is a cover behind a front bezel, on four feet; the drives' bezels, the buttons, the keylock and the knobs
stand off their faces, printed on their fronts. The CRT is a bezel whose screen opening slopes in to curved glass,
the tube's housing tapering behind it to a smaller back, on a tilt-and-swivel stand. The printing is two textures per
set drawn by retro_pc_print.py: the faces in one atlas (retro_pc_layout.py has the faces, their parts and the atlas's
regions), the glass in the other.

Like the Windows set, each is seen level (not tipped towards the viewer like the consoles), turned (the set's yaw) so
its left side shows, and fitted to the model spec (A7): standing on y = 0, centred, the largest side 1 m. No clips.
The focused card sways further the same way (up to 0.6 rad), so the 9x tower stands on the monitor's left: the sway
brings it forward, where on the right the monitor would hide it.

Six materials (case, bezel, monitor, stand, print, screen) and two textures, within the system model budget. Run from
the repo root:

    python tools/console-models/retro_pc_print.py artifacts/retro-pc
    blender -b --factory-startup --python tools/console-models/retro_pc.py -- artifacts/retro-pc dos godot/themes/console/models/systems/dos.glb
    blender -b --factory-startup --python tools/console-models/retro_pc.py -- artifacts/retro-pc windows3x godot/themes/console/models/systems/windows3x.glb
    blender -b --factory-startup --python tools/console-models/retro_pc.py -- artifacts/retro-pc windows9x godot/themes/console/models/systems/windows9x.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retro_pc_layout as L  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

BEZEL_DEPTH = 22.0          # the case's front bezel
STAND = 34.0                # the monitor's bezel stands this high on its stand
GLASS_BACK = 15.0           # the glass's edge, behind the bezel's front; the opening's slope ends just behind it
BULGE = 7.0                 # the glass's curve: its middle this much in front of its edge
ROUND = ("knob", "keylock")


class Face:
    """
    A printed face: region (atlas pixels) drawn at w x h mm, its top left at origin, x along right and y down (along
    -up), facing out (right x up).
    """

    def __init__(self, region, w, h, origin, right, up):
        self.region, self.w, self.h = region, w, h
        self.origin, self.right, self.up = Vector(origin), Vector(right), Vector(up)
        self.out = self.right.cross(self.up)

    def point(self, x, y, out=0.0):
        return self.origin + self.right * x - self.up * y + self.out * out

    def uv(self, x, y):
        rx, ry, rw, rh = self.region
        return ((rx + x / self.w * rw) / L.ATLAS, 1 - (ry + y / self.h * rh) / L.ATLAS)


def printed(name, face, outline, out, mat):
    """A flat polygon on face, outline in its (x, y) mm, out mm off it, printed from its region."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    f = bm.faces.new([bm.verts.new(face.point(x, y, out)) for x, y in outline])
    for loop, (x, y) in zip(f.loops, outline):
        loop[uv].uv = face.uv(x, y)
    f.normal_update()
    if f.normal.dot(face.out) < 0:
        bmesh.ops.reverse_faces(bm, faces=[f])
    return new_object(name, bm, mat)


def rect(x0, y0, x1, y1):
    return [(x0, y1), (x1, y1), (x1, y0), (x0, y0)]


def circle(cx, cy, r, segments=24):
    return [(cx + r * math.cos(2 * math.pi * k / segments), cy - r * math.sin(2 * math.pi * k / segments))
            for k in range(segments)]


def rounded(cx, cy, w, h, r, segments=4):
    """A rounded rectangle's outline, w x h centred on (cx, cy), anticlockwise from its right side."""
    points = []
    for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for k in range(segments + 1):
            a = math.radians(a0 + 90 * k / segments)
            points.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return points


def loft(name, rings, mat, caps=True):
    """A solid through rings of 3D points (each the same count, in the same order), capped at both ends."""
    bm = bmesh.new()
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(verts, verts[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])
    if caps:
        bm.faces.new(verts[0])
        bm.faces.new(list(reversed(verts[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def standing_part(face, kind, x, y, w, h, depth, m, plain):
    """A part standing off face, its sides plain and its front printed, as one object."""
    outline = circle(x + w / 2, y + h / 2, w / 2) if kind in ROUND else rect(x, y, x + w, y + h)
    body = loft(kind, [[face.point(px, py, -0.5) for px, py in outline],
                       [face.point(px, py, depth) for px, py in outline]], m[plain])
    edge = min(0.8, depth / 3, w / 6)
    bevel(body, edge, segments=2)
    inset = (circle(x + w / 2, y + h / 2, w / 2 - edge) if kind in ROUND
             else rect(x + edge, y + edge, x + w - edge, y + h - edge))
    return [body, printed(kind + "_print", face, inset, depth + 0.2, m["print"])]


def printed_face(face, parts, area, m, plain):
    """The face's printing over area (x0, y0, x1, y1: inside its bevelled edges), and its standing parts."""
    objects = [printed("print", face, rect(*area), 0.25, m["print"])]
    for kind, x, y, w, h, depth, _text in parts:
        if depth:
            objects += standing_part(face, kind, x, y, w, h, depth, m, plain)
    return objects


def case(spec, m):
    """The case, its front facing -Y on y = 0, centred on x = 0, standing on z = 0."""
    c = spec["case"]
    w, d, h, feet = c["width"], c["depth"], c["height"], c["feet"]
    tower = c["kind"] == "tower"
    edge = 6.0 if tower else 4.0
    cover = box("cover", -w / 2 + 1, w / 2 - 1, BEZEL_DEPTH - 2, d, feet, h - 1, m["case"])
    bevel(cover, 3.0, segments=3)
    front = box("bezel", -w / 2, w / 2, 0, BEZEL_DEPTH, feet, h, m["bezel"])
    bevel(front, edge, segments=3)
    parts = [cover, front]
    fx, fy = (w / 2 - 22, d / 2 - 40) if tower else (w / 2 - 40, d / 2 - 50)
    for x in (-fx, fx):
        for y in (-fy, fy):
            foot = box("foot", x - 16, x + 16, d / 2 + y - 20, d / 2 + y + 20, 0, feet + 1, m["stand"])
            bevel(foot, 2.0)
            parts.append(foot)

    regions = spec["atlas"]
    face = Face(regions["front"], w, h - feet, (-w / 2, 0, h), (1, 0, 0), (0, 0, 1))
    parts += printed_face(face, c["front"], (edge, edge, w - edge, h - feet - edge), m, "bezel")
    back = Face(regions["back"], w, h - feet, (w / 2 - 1, d, h - 1), (-1, 0, 0), (0, 0, 1))
    back.w, back.h = w - 2, h - feet - 1
    parts.append(printed("back", back, rect(3, 3, back.w - 3, back.h - 3), 0.25, m["print"]))
    return join(parts, "case")


def monitor(spec, m):
    """The monitor, its bezel's front facing -Y on y = 0, centred on x = 0, standing on z = 0."""
    mon = spec["monitor"]
    w, h, depth, tube = mon["width"], mon["height"], mon["depth"], mon["tube"]
    bottom, mid = STAND, STAND + mon["screen_z"]
    front = box("bezel", -w / 2, w / 2, 0, depth, bottom, bottom + h, m["monitor"])
    bevel(front, 7.0, segments=3)

    # The opening, sloping in from the bezel's front to the glass.
    (ow, oh), (iw, ih) = mon["opening"], mon["inner"]
    outer = [(x, z) for x, z in rounded(0, mid, ow, oh, 12)]
    inner = [(x, z) for x, z in rounded(0, mid, iw, ih, 7)]
    cutter = loft("opening", [[(x, -10, z) for x, z in outer], [(x, 0, z) for x, z in outer],
                              [(x, GLASS_BACK + 2, z) for x, z in inner]], m["monitor"])
    boolean(front, cutter)

    # The glass: a gently curved grid in front of the opening's floor, a little larger than the opening's back, so its
    # edge is inside the slope's walls.
    gw, gh = mon["glass"]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    nu, nv = 20, 16
    grid = [[bm.verts.new((gw * (i / nu - 0.5), GLASS_BACK - BULGE * (1 - (2 * i / nu - 1) ** 2) * (1 - (2 * j / nv - 1) ** 2),
                           mid + gh * (j / nv - 0.5))) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / nu, b / nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:                                   # it faces the viewer (-Y)
        if f.normal.y > 0:
            bmesh.ops.reverse_faces(bm, faces=[f])
    glass = new_object("glass", bm, m["screen"])

    # The tube's housing: straight sides a little way back, then tapering to its back, which sits higher.
    def ring(y, rw, rh, r, cz):
        return [(x, y, z) for x, z in rounded(0, cz, rw, rh, r, segments=6)]
    rings = [ring(depth - 2, w - 28, h - 28, 20, bottom + h / 2),
             ring(depth + tube * 0.22, w - 40, h - 40, 24, bottom + h / 2 + 2),
             ring(depth + tube, w * 0.5, h * 0.46, 30, bottom + h * 0.58)]
    housing = loft("housing", rings, m["monitor"])
    bevel(housing, 4.0, segments=2, angle=50)

    # The vents on the housing's sloping top (between the straight parts of the last two rings' top edges), and the
    # label on its back.
    hw1, ztop1, y1 = (w - 40) / 2 - 24, bottom + h / 2 + 2 + (h - 40) / 2, depth + tube * 0.22
    hw2, ztop2, y2 = w * 0.25 - 30, bottom + h * 0.58 + h * 0.23, depth + tube
    def on_top(t, s):
        """A point on the top, t across (0..1, left to right), s back from the middle ring to the back."""
        y, z, hw = y1 + (y2 - y1) * s, ztop1 + (ztop2 - ztop1) * s, hw1 + (hw2 - hw1) * s
        return Vector((-hw + 2 * hw * t, y, z))
    slope = Vector((0, y2 - y1, ztop2 - ztop1)).normalized()
    normal = Vector((1, 0, 0)).cross(slope).normalized()
    if normal.z < 0:
        normal = -normal
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rx, ry, rw, rh = spec["atlas"]["vents"]
    n = 6
    patch = [[bm.verts.new(on_top(0.12 + 0.76 * i / n, 0.12 + 0.6 * j / n) + normal * 0.3) for i in range(n + 1)]
             for j in range(n + 1)]
    for j in range(n):
        for i in range(n):
            f = bm.faces.new([patch[j][i], patch[j][i + 1], patch[j + 1][i + 1], patch[j + 1][i]])
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = ((rx + rw * a / n) / L.ATLAS, 1 - (ry + rh * b / n) / L.ATLAS)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.dot(normal) < 0:
            bmesh.ops.reverse_faces(bm, faces=[f])
    vents = new_object("vents", bm, m["print"])

    bw, bh = w * 0.5 - 16, h * 0.46 - 16
    back_z = bottom + h * 0.58
    label = Face(spec["atlas"]["label"], bw, bh, (bw / 2, depth + tube, back_z + bh / 2), (-1, 0, 0), (0, 0, 1))
    back = printed("label", label, rect(0, 0, bw, bh), 0.3, m["print"])

    # The stand: a round foot under the tube's front, its swivel narrowing up into the bezel and the housing (whose
    # underside rises behind the bezel).
    r = min(w, depth + tube) * 0.34
    cy = depth + tube * 0.18
    def disc(rr, z):
        return [(rr * math.cos(2 * math.pi * k / 40), cy + rr * math.sin(2 * math.pi * k / 40), z) for k in range(40)]
    stand = loft("stand", [disc(r, 0), disc(r, 7), disc(r * 0.86, 13), disc(r * 0.6, 17), disc(r * 0.52, bottom + 26)],
                 m["stand"])
    bevel(stand, 1.5, segments=2, angle=30)

    # The band under the screen (inside the bezel's rounded sides and bottom), and its knobs and buttons.
    strip = Face(spec["atlas"]["strip"], w, mon["strip"], (-w / 2, 0, bottom + mon["strip"]), (1, 0, 0), (0, 0, 1))
    band = printed_face(strip, mon["parts"], (8, 0, w - 8, mon["strip"] - 8), m, "monitor")
    return join([front, glass, housing, vents, back, stand] + band, "monitor")


def placed(obj, at, yaw=0.0):
    obj.data.transform(Matrix.Translation(at) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))
    return obj


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, set_id, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    spec = L.SETS[set_id]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    c, mon = spec["case"], spec["monitor"]
    m = {
        "case": material("case", c["colour"], 0.55),
        "bezel": material("bezel", c["bezel_colour"], 0.55),
        "monitor": material("monitor", mon["colour"], 0.55),
        "stand": material("stand", c["colour"], 0.6),
        "print": material("print", "#FFFFFF", 0.55, bpy.data.images.load(os.path.join(images, f"{set_id}_print.png"))),
        "screen": material("screen", "#FFFFFF", 0.25, bpy.data.images.load(os.path.join(images, f"{set_id}_screen.png"))),
    }
    pc, crt = case(spec, m), monitor(spec, m)
    if spec["place"] == "stacked":                   # the monitor on the case, a little back from its front
        placed(crt, (0, 28, c["height"]))
    else:                                            # the tower on the left, a little back, the monitor to its right
        placed(pc, (-c["width"] / 2 - 25, 40, 0))
        placed(crt, (mon["width"] / 2 + 25, 0, 0))
    pc = join([pc, crt], set_id)
    mesh = pc.data
    mesh.transform(Matrix.Rotation(math.radians(spec["yaw"]), 4, "Z"))
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(35))

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"{set_id}: {triangles(mesh)} triangles, {len(mesh.materials)} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm before the fit")
    export([pc], out)


main()
