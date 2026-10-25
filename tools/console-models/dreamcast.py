"""The console theme's Dreamcast system model (godot/themes/console/models/systems/dreamcast.glb): the European
Dreamcast and its controller with a VMU in its slot.

Built in Blender (dreamcast_layout.py has the measurements, taken from photographs and published figures). The body is
its side outline (its top rising a little to the back) extruded across its width and cut round its plan's corners,
standing on its base set in under it; the ports' panel is sunk into its front, the ports into the panel, the disc's well
into its top under the lid and the vents into its right side; POWER and OPEN stand in its top's front corners, the power
light by POWER. The lid is a disc lying on the top, hinged at its back, the spindle standing in the well. The controller
is its smoothed outline with a rounded profile, the stick, the D-pad, A B X Y and START standing on it, the VMU's screen
in its slot, its cable running from between its grips to port A. The printing is one texture (dreamcast_print.py's),
projected from above onto the top, the lid, the controller and the GD-ROM, and from in front onto the front.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (on its hinge), the GD-ROM (waiting over the well, shrunk to nothing), POWER and OPEN, the power light
(lit and unlit, swapped by depth), the VMU's screens (blank and lit, swapped by depth), and the controller's stick, A
and X.

The `focused` clip (8 s, looping): OPEN, the lid swings up, the GD-ROM comes down onto the spindle and the lid shuts;
POWER, the light comes on and the VMU shows the game's ship; the stick turns while A and X fire; then POWER again, OPEN,
the GD-ROM rises out and goes, and the lid shuts.

Two materials (case, disc) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/dreamcast_print.py artifacts/dreamcast
    blender -b --factory-startup --python tools/console-models/dreamcast.py -- artifacts/dreamcast godot/themes/console/models/systems/dreamcast.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dreamcast_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)
from saturn import disc, inset, smooth_outline  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.45, disc=0.2)
SINK = 1.0                # how far an unshown light or screen sinks


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
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.TOP[0])
PAD = atlas_uv(L.REGIONS["pad"], 160.0, 160.0)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def pad_uv(co):
    return PAD(co.x + 80.0, 80.0 - co.y)


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The body with the panel, the ports, the well and the vents cut in, on its base; printed."""
    half, b = L.WIDTH / 2, L.BASE
    body = prism_x("dreamcast", [(0.0, b["height"]), (L.DEPTH, b["height"]), (L.DEPTH, L.TOP[1]), (0.0, L.TOP[0])],
                   -half - 1.0, half + 1.0, m["case"])
    boolean(body, prism_z("plan", rounded(0.0, L.DEPTH / 2, L.WIDTH, L.DEPTH, 10.0, 4), 0.0, L.TOP[1] + 5.0,
                          m["case"]), "INTERSECT")
    bevel(body, 3.0, segments=3, angle=30)
    (px0, px1), (pz0, pz1) = L.PANEL["x"], L.PANEL["z"]
    boolean(body, box("panel", px0, px1, -2.0, L.PANEL["depth"], pz0, pz1, m["case"]))
    (pw, ph), pz = L.PORTS["size"], L.PORTS["z"]
    for x in L.PORTS["x"]:
        boolean(body, box("port", x - pw / 2, x + pw / 2, L.PANEL["depth"] - 1.0, L.PANEL["depth"] + L.PORTS["depth"],
                          pz - ph / 2, pz + ph / 2, m["case"]))
    (lx, ly) = L.LID["at"]
    boolean(body, disc("well", lx, ly, L.WELL["r"], L.TOP[0] - L.WELL["depth"], L.TOP[1] + 5.0, m["case"], 48))
    (vy0, vy1), (vz0, vz1), n = L.VENTS["y"], L.VENTS["z"], L.VENTS["count"]
    for k in range(n):
        y = vy0 + (vy1 - vy0) * (k + 0.5) / n
        boolean(body, box("vent", half - 3.0, half + 2.0, y - 2.0, y + 2.0, vz0, vz1, m["case"]))
    colour(body, m["case"], "case")
    paint(body, m["case"], top_uv, lambda c, n_, kind: n_.z > 0.5 and c.z > L.TOP[0] - 2.5)
    paint(body, m["case"], lambda co: FRONT(co.x + half, L.TOP[0] - co.z), lambda c, n_, kind: n_.y < -0.9)

    def dark(c, n_):
        """In the well, a port or a vent."""
        return (math.hypot(c.x - lx, c.y - ly) < L.WELL["r"] + 0.5 and c.z < L.TOP[0] - 2.5
                or c.y > L.PANEL["depth"] + 0.5 and pz - ph / 2 - 0.5 < c.z < pz + ph / 2 + 0.5 and c.y < 20.0
                or half - 3.5 < c.x and vy0 - 1.0 < c.y < vy1 + 1.0 and vz0 - 0.5 < c.z < vz1 + 0.5 and n_.x < 0.9)
    paint(body, m["case"], swatch("dark"), lambda c, n_, kind: dark(c, n_))
    base = box("base", -half + b["inset"], half - b["inset"], b["inset"], L.DEPTH - b["inset"], 0.0, b["height"] + 1.0,
               m["case"])
    bevel(base, 2.0, segments=2)
    colour(base, m["case"], "grey")
    spindle = disc("spindle", lx, ly, 7.0, L.TOP[0] - L.WELL["depth"] - 1.0, L.TOP[0] - L.WELL["depth"] + 8.0,
                   m["case"], 20)
    colour(spindle, m["case"], "grey")
    return join([body, base, spindle], "dreamcast")


def buttons(m):
    """POWER and OPEN, each its foot's middle at its origin, with where it goes; and the power light, lit and unlit."""
    out = {}
    for name in ("power", "open"):
        x, y = L.BUTTONS[name]
        part = disc(name, 0.0, 0.0, L.BUTTONS["r"], -1.5, 2.4, m["case"], 28)
        bevel(part, 1.0, segments=2)
        colour(part, m["case"], "button")
        paint(part, m["case"], lambda co, x=x, y=y: top_uv(Vector((co.x + x, co.y + y, 0.0))),
              lambda c, n, kind: n.z > 0.9)
        out[name] = (part, Vector((x, y, L.top_z(y))))
    lx, ly = L.BUTTONS["light"]
    for name, tone in (("light", "lit"), ("light_off", "off")):
        part = disc(name, 0.0, 0.0, 1.6, -0.4, 0.3, m["case"], 12)
        out[name] = (colour(part, m["case"], tone), Vector((lx, ly, L.top_z(ly))))
    return out


def lid(m):
    """The lid: a disc lying on the top, printed, its origin on its hinge at its back."""
    (lx, ly), r = L.LID["at"], L.LID["r"]
    ring = [(lx + r * math.cos(2 * math.pi * k / 64), ly + r * math.sin(2 * math.pi * k / 64)) for k in range(64)]
    top = [(lx + (r - 3.0) * math.cos(2 * math.pi * k / 64), ly + (r - 3.0) * math.sin(2 * math.pi * k / 64))
           for k in range(64)]
    part = solid("lid", [[(x, y, L.top_z(y) - L.LID["thickness"]) for x, y in ring],
                         [(x, y, L.top_z(y) + 0.6) for x, y in ring], [(x, y, L.top_z(y) + 1.6) for x, y in top]],
                 m["case"])
    colour(part, m["case"], "case")
    paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.5)
    hinge = Vector((lx, ly + r, L.top_z(ly + r) + 1.0))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def gd_rom(m):
    """The GD-ROM, its middle at its origin, its label up."""
    r, t = L.DISC["r"], L.DISC["thickness"]
    part = disc("gd_rom", 0.0, 0.0, r, -t / 2, t / 2, m["disc"], 64)
    colour(part, m["disc"], "disc")
    face = atlas_uv(L.REGIONS["disc"], 2 * r, 2 * r)
    paint(part, m["disc"], lambda co: face(co.x + r, r - co.y), lambda c, n, kind: n.z > 0.9)
    return part


# ---- The controller --------------------------------------------------------------------------------------------------

def controller(m):
    """The controller at its place: the body, the D-pad, B, Y, START and the VMU's face; the stick, A, X and the VMU's
    screens apart (each with where it goes). Returns them and where its cable leaves it."""
    P = L.PAD
    x, y, turn = P["at"]
    place = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
    spin = Matrix.Rotation(math.radians(turn), 4, "Z")
    outline = smooth_outline(P["points"])
    h = P["height"]
    # A rounded profile, its top easing into the flat so the print's edge does not crease.
    profile = ((0.0, 5.0), (0.12, 1.8), (0.3, 0.0), (0.55, 0.4), (0.78, 2.0), (0.9, 3.4), (0.96, 4.8), (0.99, 6.0),
               (1.0, 7.4))
    body = solid("controller", [[(px, py, h * z) for px, py in (inset(outline, d) if d else outline)]
                                for z, d in profile], m["case"])
    colour(body, m["case"], "case")
    paint(body, m["case"], pad_uv, lambda c, n, kind: n.z > 0.85)
    parts = [body]
    (dx, dy), reach, width = P["dpad"]
    for w, d in ((reach * 2, width), (width, reach * 2)):
        arm = box("dpad", dx - w / 2, dx + w / 2, dy - d / 2, dy + d / 2, h - 2.0, h + 3.0, m["case"])
        bevel(arm, 1.0, segments=2)
        parts.append(colour(arm, m["case"], "grey"))
    (cx, cy), reach, br = P["abxy"]
    moving = {}
    for name, (ox, oy), tone in (("a", (0, -1), "red"), ("b", (1, 0), "blue"), ("x", (-1, 0), "yellow"),
                                 ("y", (0, 1), "green")):
        bx, by = cx + ox * reach, cy + oy * reach
        button = disc(name, 0.0, 0.0, br, -1.0, 3.6, m["case"], 20)
        colour(button, m["case"], tone)
        if name in ("a", "x"):
            moving[name] = (button, place @ Vector((bx, by, h)))
        else:
            button.data.transform(Matrix.Translation((bx, by, h)))
            parts.append(button)
    (tx, ty), ts = P["start"]
    start = solid("start", [[(tx - ts / 2, ty - ts * 0.4, z), (tx + ts / 2, ty - ts * 0.4, z), (tx, ty + ts * 0.5, z)]
                            for z in (h - 1.0, h + 2.0)], m["case"])
    parts.append(colour(start, m["case"], "grey"))
    (sx, sy), sw, sh = P["slot"]
    vmu = box("vmu", sx - sw / 2 + 3.0, sx + sw / 2 - 3.0, sy - sh / 2 + 3.0, sy + sh / 2 - 3.0, h - 2.0, h + 1.4,
              m["case"])
    bevel(vmu, 2.0, segments=2)
    colour(vmu, m["case"], "case")
    paint(vmu, m["case"], pad_uv, lambda c, n, kind: n.z > 0.9)
    parts.append(vmu)
    whole = join(parts, "controller")
    whole.data.transform(place)

    (scx, scy), scw, sch = P["screen"]
    for name in ("vmu_off", "vmu_on"):
        face = atlas_uv(L.REGIONS[name], scw, sch)
        screen = box(name, -scw / 2, scw / 2, -sch / 2, sch / 2, -0.3, 0.3, m["case"])
        colour(screen, m["case"], "grey")
        paint(screen, m["case"], lambda co, face=face: face(co.x + scw / 2, sch / 2 - co.y),
              lambda c, n, kind: n.z > 0.9)
        moving[name] = (screen, place @ Vector((scx, scy, h + 1.5)))
    (stx, sty), base_r, cap_r = P["stick"]
    stick = solid("stick", [[(r * math.cos(2 * math.pi * k / 24), r * math.sin(2 * math.pi * k / 24), z)
                             for k in range(24)] for r, z in ((4.0, -1.0), (4.0, 6.0), (cap_r, 7.0), (cap_r, 10.0),
                                                              (cap_r - 2.0, 9.2))], m["case"])
    colour(stick, m["case"], "grey")
    socket = disc("socket", stx, sty, base_r, h - 1.0, h + 1.0, m["case"], 24)
    colour(socket, m["case"], "grey")
    socket.data.transform(place)
    moving["stick"] = (stick, place @ Vector((stx, sty, h + 1.0)))
    for part, _ in moving.values():
        part.data.transform(spin)
    return join([whole, socket], "controller"), moving, place @ Vector((0.0, -38.0, h * 0.4))


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
    return colour(new_object("cable", bm, m["case"]), m["case"], "cable")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def opening(f):
    if f < 10:
        return 0.0
    if f < 42:
        return back_out(phase(f, 10, 20), 1.4)
    if f < 176:
        return 1.0 - ease_in(phase(f, 42, 50))
    if f < 204:
        return back_out(phase(f, 176, 186), 1.4)
    return 1.0 - ease_in(phase(f, 204, 212))


def timeline(f):
    above = L.DISC["above"]
    if f < 20 or f >= 200:
        gd = Pose(z=above, scale=HIDDEN)
    elif f < 27:
        gd = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 20, 27))))
    elif f < 186:
        gd = Pose(z=above * (1 - ease_in(phase(f, 27, 38))), spin=-360.0 * 8.0 * phase(f, 58, 166))
    else:
        gd = Pose(z=above * ease_out(phase(f, 186, 196)), scale=max(HIDDEN, 1 - ease_in(phase(f, 194, 200))))
    on = 56 <= f < 168
    playing = 60 <= f < 168
    t = phase(f, 70, 164)
    k = math.sin(math.pi * t)
    return {"lid": Pose(pitch=L.LID["open"] * opening(f)), "gd_rom": gd,
            "open": Pose(z=-1.8 * max(tap(f, 7), tap(f, 173))), "power": Pose(z=-1.8 * max(tap(f, 54), tap(f, 166))),
            "light": Pose() if on else Pose(z=-SINK), "light_off": Pose(z=-SINK) if on else Pose(),
            "vmu_on": Pose() if playing else Pose(z=-SINK), "vmu_off": Pose(z=-SINK) if playing else Pose(),
            "stick": Pose(pitch=16.0 * k * math.sin(2 * math.pi * 3.0 * t),
                          roll=16.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "a": Pose(z=-2.0 * max(tap(f, f0) for f0 in (78, 102, 126, 150))),
            "x": Pose(z=-2.0 * max(tap(f, f0) for f0 in (90, 114, 138, 158)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "dreamcast_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    body, moving, exit_ = controller(m)
    port = Vector((L.PORTS["x"][0], L.PANEL["depth"] + 1.0, L.PORTS["z"]))
    lead = cable(m, [exit_, exit_ + Vector((0.0, -40.0, -6.0)), (port.x - 30.0, -60.0, 2.4), port])
    whole = join([console(m), body, lead], "dreamcast")
    for p in whole.data.polygons:
        p.use_smooth = p.area < 400.0                     # the big flat faces flat
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("dreamcast_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    moving.update(buttons(m))
    moving["lid"] = lid(m)
    (lx, ly) = L.LID["at"]
    moving["gd_rom"] = (gd_rom(m), Vector((lx, ly, L.TOP[0] - L.WELL["depth"] + 8.0 + L.DISC["thickness"] / 2)))
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
    print(f"Dreamcast: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
