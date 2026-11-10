"""The console theme's PlayStation system model (godot/themes/console/models/systems/psx.glb).

Built in Blender from the first model's measurements (psx_layout.py has them, from photographs): the grey body, its
corners rounded and its top's edges softened, on the bottom shell's lip; a pod at each end of its top, POWER, RESET and
the power light's slot in the left one, OPEN in the right, each button a cap in a well with a sloping lip; between the
pods the strip in front of the lid, flush with them, and the plate behind it, lower, gapped from them where the hinges
are; the round well the lid shuts into, cut into all three, with the drive's mechanism, its turntable and the laser's
lens on its sled on its floor; the middle's front face set back a little, with two openings, each a memory card slot
over a controller port; at the back, under the plate, the ports panel with its three jacks standing out, PARALLEL I/O
and AC IN in the pods' backs; and fins standing off both ends. The printing (the lid's marks, the buttons' legends, the
seams, the ports, the disc's two sides) is one texture, drawn by psx_print.py and projected onto the faces facing up,
the front and the back.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: its right end towards the viewer, its
top tipped up, as the Mega Drive's; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding
the console; the console holding the lid (hinged along its back edge), POWER, OPEN, the power light lit, and the disc
(Odyssey, a made-up game: its label, and the PlayStation's black data side). The disc waits on the turntable shrunk to
nothing and the light is shrunk to nothing, so at rest the card is the console with its lid shut.

The `focused` clip (8 s, looping) plays a game: OPEN goes down and the lid springs up; the disc drops in from above,
spinning and flipping over to flash its black side, and settles on the turntable; the lid shuts with a bounce, POWER
goes down and the power light comes on. Later POWER again and the light goes off; OPEN, the lid springs up, the disc
rises spinning and goes, and the lid shuts.

Four materials (case, print, dark, disc) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/psx_print.py artifacts/psx
    blender -b --factory-startup --python tools/console-models/psx.py -- artifacts/psx godot/themes/console/models/systems/psx.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psx_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import (  # noqa: E402
    apply_modifiers, bevel, boolean, box, export, join, material, new_object, triangles)

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, print=0.5, dark=0.7, disc=0.25)
OPEN = 75.0          # degrees the lid opens


def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.TOP)
BACK = atlas_uv(L.REGIONS["back"], L.WIDTH, L.TOP)
PORT = atlas_uv(L.REGIONS["port"], L.PORTS["width"], L.PORTS["z"][1] - L.PORTS["z"][0])


def top_uv(co):
    """The top seen from above."""
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def port_uv(co):
    """The back of the front opening it's in, seen from in front."""
    x = L.PORTS["x"][0] if co.x < 0 else L.PORTS["x"][1]
    return PORT(co.x - x + L.PORTS["width"] / 2, L.PORTS["z"][1] - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def circle(cx, cy, r, segments=40):
    return [(cx + r * math.cos(2 * math.pi * k / segments), cy + r * math.sin(2 * math.pi * k / segments))
            for k in range(segments)]


def cylinder(name, cx, cy, r, z0, z1, mat, segments=40):
    return solid(name, [[(x, y, z) for x, y in circle(cx, cy, r, segments)] for z in (z0, z1)], mat)


def ring_solid(name, r_out, r_in, z0, z1, mat, segments=48):
    """A flat ring (a disc with a hole), its middle at the origin, from z0 to z1."""
    bm = bmesh.new()
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments), z))
              for k in range(segments)] for r, z in ((r_out, z0), (r_out, z1), (r_in, z1), (r_in, z0))]
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new([a[k], a[j], b[j], b[k]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def two_tone(obj, mat, z0, z1):
    """Gives obj's faces whose middles are between the heights z0 and z1 the material mat (a cutter's faces pass their
    materials on to the faces they cut)."""
    mesh = obj.data
    mesh.materials.append(mat)
    for p in mesh.polygons:
        if z0 < p.center.z < z1:
            p.material_index = len(mesh.materials) - 1


# ---- The console -----------------------------------------------------------------------------------------------------

def hull(m):
    """The body on the bottom shell's lip, its top's edges rounded, the middle's front face set back."""
    body = solid("psx", [[(x, y, z) for x, y in rounded(0.0, L.DEPTH / 2, L.WIDTH, L.DEPTH, L.CORNER, 4)]
                         for z in (0.0, L.TOP)], m["case"])
    bevel(body, L.EDGE, segments=2)
    w, d = L.WIDTH + 2 * L.FINS["out"], L.DEPTH + 2 * L.BASE["front"]
    lip = solid("lip", [[(x, y, z) for x, y in rounded(0.0, L.DEPTH / 2, w, d, L.CORNER + 1.0, 4)]
                        for z in (0.0, L.BASE["height"])], m["case"])
    boolean(body, lip, "UNION")
    boolean(body, box("set_back", -L.POD, L.POD, -5.0, L.SET_BACK, -1.0, L.TOP + 5.0, m["case"]))
    return body


def top_section(body, m):
    """The plate behind the lid, its gaps to the pods, the lid's well and the mechanism's recess in its floor."""
    lx, ly = L.LID["x"], L.LID["y"]
    plate, inner = L.TOP - L.PLATE["drop"], L.POD - L.PLATE["gap"]
    boolean(body, box("plate", -L.POD, L.POD, ly, L.DEPTH + 5.0, plate, L.TOP + 5.0, m["case"]))
    boolean(body, box("plate_back", -inner, inner, L.PLATE["back"], L.DEPTH + 5.0, L.PLATE["under"], L.TOP + 5.0,
                      m["case"]))
    for side in (-1, 1):
        x0, x1 = sorted((side * inner, side * L.POD))
        boolean(body, box("hinge_gap", x0, x1, ly, L.DEPTH + 5.0, L.TOP - L.PLATE["gap_depth"], plate + 1.0,
                          m["dark"]))
    floor = L.WELL["floor"]
    well = solid("well", [[(x, y, z) for x, y in circle(lx, ly, L.WELL["r"], 96)]
                          for z in (floor, L.TOP - L.WELL["band"], L.TOP + 5.0)], m["case"])
    two_tone(well, m["dark"], L.TOP - L.WELL["band"], L.TOP + 10.0)
    boolean(body, well)
    outline = [(lx + x, ly + y) for x, y in L.MECHANISM["outline"]]
    boolean(body, solid("mechanism", [[(x, y, z) for x, y in outline]
                                      for z in (floor - L.MECHANISM["depth"], floor + 0.5)], m["dark"]))


def buttons_and_light(body, m):
    """The buttons' wells, each a lip sloping down to a dark gap round its cap, and the power light's slot."""
    g = L.BUTTON
    for name, (x, y, r, lip, drop) in L.BUTTONS.items():
        rings = [[(px, py, z) for px, py in circle(x, y, rr, 48)]
                 for rr, z in ((r + g["gap"], L.TOP - g["depth"]), (r + g["gap"], L.TOP - drop),
                               (r + lip, L.TOP + 0.01), (r + lip, L.TOP + 5.0))]
        well = solid(name + "_well", rings, m["case"])
        two_tone(well, m["dark"], -1.0, L.TOP - drop)
        boolean(body, well)
    led = L.LED
    boolean(body, box("led", led["x"] - led["width"] / 2, led["x"] + led["width"] / 2, -3.0, led["length"],
                      L.TOP - led["depth"], L.TOP + 5.0, m["dark"]))


def openings(body, m):
    """The front's two openings, the ports panel's recess under the plate, PARALLEL I/O's and AC IN's."""
    p = L.PORTS
    (z0, z1), c = p["z"], p["chamfer"]
    for x in p["x"]:
        # Its edge chamfered: c wider at the face, narrowing over the first c of its depth.
        steps = ((-5.0, c), (L.SET_BACK, c), (L.SET_BACK + c, 0.0), (L.SET_BACK + p["depth"], 0.0))
        rings = [[(px, y, pz) for px, pz in rounded(x, (z0 + z1) / 2, p["width"] + 2 * grow, z1 - z0 + 2 * grow,
                                                     p["corner"] + grow, 3)] for y, grow in steps]
        boolean(body, solid("port", rings, m["case"]))
    boolean(body, box("panel", -L.PANEL["x"], L.PANEL["x"], L.PANEL["face"], L.DEPTH + 5.0, *L.PANEL["z"], m["case"]))
    for hole in (L.PARALLEL, L.AC_IN):
        boolean(body, box("hole", *hole["x"], L.DEPTH - hole["depth"], L.DEPTH + 5.0, *hole["z"], m["case"]))


def paint_faces(body, m):
    """The print on the faces facing up (the top, not the well's floor), the front (its openings' backs apart) and the
    back."""
    plate = L.TOP - L.PLATE["drop"]
    front, port_back = L.SET_BACK + 1.0, L.SET_BACK + L.PORTS["depth"] + 1.0
    paint(body, m["print"], top_uv, lambda c, n, name: name == "case" and n.z > 0.9 and c.z > plate - 0.5)
    paint(body, m["print"], lambda co: FRONT(co.x + L.WIDTH / 2, L.TOP - co.z),
          lambda c, n, name: name == "case" and n.y < -0.9 and c.y < front)
    paint(body, m["print"], port_uv, lambda c, n, name: name == "case" and n.y < -0.9 and front <= c.y < port_back)
    paint(body, m["print"], lambda co: BACK(L.WIDTH / 2 - co.x, L.TOP - co.z),
          lambda c, n, name: name == "case" and n.y > 0.9 and c.y > L.PANEL["face"] - 5.0)


def drive(m):
    """On the well's floor: the turntable and its centring cap, and the laser's lens on its sled."""
    x, y = L.LID["x"], L.LID["y"]
    s, lens = L.SPINDLE, L.LENS
    bottom = L.WELL["floor"] - L.MECHANISM["depth"]
    hub = cylinder("turntable", x, y, s["r"], bottom - 0.1, s["top"], m["dark"])
    tip = cylinder("centre", x, y, s["cap"], s["top"] - 0.1, s["top"] + s["cap_height"], m["print"], 24)
    paint(tip, m["print"], swatch("metal"), lambda c, n, name: True)
    (ax, ay), (sw, sl) = lens["at"], lens["sled"]
    angle = math.atan2(ay, ax)
    sled = box("sled", -sl / 2, sl / 2, -sw / 2, sw / 2, bottom - 0.1, bottom + 3.0, m["print"])
    reach = Vector((math.cos(angle), math.sin(angle), 0.0)) * lens["reach"]
    sled.data.transform(Matrix.Translation(Vector((x, y, 0.0)) + reach) @ Matrix.Rotation(angle, 4, "Z"))
    paint(sled, m["print"], swatch("sled"), lambda c, n, name: True)
    glass = cylinder("lens", x + ax, y + ay, lens["r"], bottom + 2.9, bottom + 3.8, m["print"], 16)
    paint(glass, m["print"], swatch("lens"), lambda c, n, name: True)
    return [hub, tip, sled, glass]


def fins(m):
    """The vents: fins standing off both ends from the bottom shell's lip, their outer tops rounded."""
    f = L.FINS
    (z0, z1), cap = f["z"], f["cap"]
    inner, outer = L.WIDTH / 2 - 1.0, L.WIDTH / 2 + f["out"]
    arc = [(outer - cap + cap * math.cos(math.radians(a)), z1 - cap + cap * math.sin(math.radians(a)))
           for a in (30, 60)]
    profile = [(inner, z0), (outer, z0), (outer, z1 - cap)] + arc + [(outer - cap, z1), (inner, z1)]
    count, half = int((f["y"][1] - f["y"][0]) / f["pitch"]) + 1, f["width"] / 2
    bm = bmesh.new()
    for side in (-1, 1):
        for k in range(count):
            y = f["y"][0] + k * f["pitch"]
            sides = [[bm.verts.new((side * px, y + dy, pz)) for px, pz in profile] for dy in (-half, half)]
            bm.faces.new(sides[0])
            bm.faces.new(list(reversed(sides[1])))
            for i in range(len(profile)):
                j = (i + 1) % len(profile)
                bm.faces.new([sides[0][i], sides[0][j], sides[1][j], sides[1][i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object("fins", bm, m["case"])


def jacks(m):
    """AUDIO OUT's and VIDEO OUT's jacks, standing out of the ports panel: a metal shell, its coloured face, a hole."""
    j = L.JACKS
    along_y = Matrix.Rotation(math.radians(-90.0), 4, "X")       # a cylinder up z turned to point out of the back
    parts = []
    for colour, x in j["at"].items():
        at = Matrix.Translation((x, L.PANEL["face"] - 0.5, j["z"]))
        casing = cylinder("jack", 0.0, 0.0, j["r"], 0.0, j["length"], m["print"], 20)
        hole = cylinder("jack_hole", 0.0, 0.0, 1.4, j["length"] - 0.5, j["length"] + 0.3, m["print"], 12)
        for part in (casing, hole):
            part.data.transform(at @ along_y)
        paint(casing, m["print"], swatch("metal"), lambda c, n, name: True)
        paint(casing, m["print"], swatch(colour), lambda c, n, name: n.y > 0.9)
        paint(hole, m["print"], swatch("black"), lambda c, n, name: True)
        parts += [casing, hole]
    return parts


def body(m):
    console = hull(m)
    top_section(console, m)
    buttons_and_light(console, m)
    openings(console, m)
    paint_faces(console, m)
    return join([console, button(m, "reset"), fins(m)] + drive(m) + jacks(m), "psx")


def button(m, name):
    """A button's cap standing in its well, its top domed a little."""
    x, y, r = L.BUTTONS[name][:3]
    g = L.BUTTON
    rings = [[(px, py, z) for px, py in circle(x, y, r - inset, 40)]
             for inset, z in ((0.0, L.TOP - g["depth"] + 0.5), (0.0, L.TOP - g["edge"] - 0.3),
                              (0.35, L.TOP - g["edge"]), (r * 0.5, L.TOP + g["crown"] * 0.75),
                              (r * 0.85, L.TOP + g["crown"]))]
    cap = solid(name, rings, m["case"])
    paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
    return cap


def lid(m):
    """The lid, its origin on its hinge (the top of its back edge): a broad disc, its rim rounded and its top domed a
    little, the disc clamp under its middle."""
    x, y, r = L.LID["x"], L.LID["y"], L.LID["r"]
    base, rim, dome = L.LID["base"], L.LID["rim"], L.LID["dome"]
    rings = [[(px, py, z) for px, py in circle(x, y, r - inset, 96)]
             for inset, z in ((0.0, base), (0.0, rim - 1.4), (0.3, rim - 0.6), (0.9, rim - 0.15), (1.8, rim),
                              (r * 0.35, rim + dome * 0.6), (r * 0.7, rim + dome))]
    cover = solid("lid", rings, m["case"])
    paint(cover, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
    clamp = cylinder("clamp", x, y, L.CLAMP["r"], base - L.CLAMP["height"], base + 0.5, m["case"])
    cover = join([cover, clamp], "lid")
    hinge = Vector((x, y + r, rim))
    cover.data.transform(Matrix.Translation(-hinge))
    return cover, hinge


def disc(m):
    """The disc, its middle at its origin, its label up."""
    d = L.DISC
    size = 2 * d["r"]
    shell = ring_solid("disc", d["r"], d["hole"], -d["thickness"] / 2, d["thickness"] / 2, m["disc"])
    label, data = atlas_uv(L.REGIONS["label"], size, size), atlas_uv(L.REGIONS["data"], size, size)
    paint(shell, m["disc"], lambda co: label(co.x + d["r"], d["r"] - co.y), lambda c, n, name: n.z > 0.9)
    paint(shell, m["disc"], lambda co: data(co.x + d["r"], d["r"] + co.y), lambda c, n, name: n.z < -0.9)
    paint(shell, m["disc"], swatch("metal"), lambda c, n, name: abs(n.z) <= 0.9)
    return shell


def light(m):
    """The power light, lit, in its slot."""
    led = L.LED
    w, length = led["width"] - 0.6, led["length"] - 0.6
    lit = box("power_light", -w / 2, w / 2, -length / 2, length / 2, -0.6, 0.0, m["print"])
    paint(lit, m["print"], swatch("led"), lambda c, n, name: True)
    return lit, Vector((led["x"], led["length"] / 2, L.TOP - 1.0))


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 5, f0 + 9)))


def lid_angle(f, f0, f1):
    """Open between f0 (springing up) and f1 (shutting, with a bounce)."""
    opening = back_out(phase(f, f0, f0 + 12), 1.6) * (1 - ease_in(phase(f, f1 - 10, f1)))
    bounce = 4.0 * math.exp(-(f - f1) / 3.0) * abs(math.sin(math.pi * (f - f1) / 4.0)) if f >= f1 else 0.0
    return -(OPEN * opening + bounce)


def timeline(f):
    poses = {"open": Pose(z=-2.0 * (tap(f, 12) + tap(f, 170))), "power": Pose(z=-2.0 * (tap(f, 84) + tap(f, 160)))}
    poses["lid"] = Pose(pitch=lid_angle(f, 15, 80) if f < 160 else lid_angle(f, 173, 214))
    poses["power_light"] = Pose() if 87 <= f < 163 else Pose(scale=HIDDEN)

    # The disc: drops in spinning, flipping over once, settles on the turntable; later rises spinning and goes.
    high = 105.0
    if f < 22 or f >= 200:
        poses["disc"] = Pose(scale=HIDDEN)
    elif f < 30:
        poses["disc"] = Pose(z=high, spin=20.0 * (f - 22), scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 22, 30)))
    elif f < 62:
        t = phase(f, 30, 62)
        poses["disc"] = Pose(z=high * (1 - ease_in(t)), spin=160.0 + 900.0 * ease_out(t),
                             pitch=360.0 * smooth(phase(f, 32, 56)))
    elif f < 178:
        poses["disc"] = Pose(z=1.5 * math.exp(-(f - 62) / 3.0) * abs(math.sin(math.pi * (f - 62) / 5.0)))
    else:
        t = phase(f, 178, 200)
        poses["disc"] = Pose(z=80.0 * ease_out(t), spin=720.0 * ease_in(t),
                             scale=max(HIDDEN, 1 - ease_in(phase(f, 190, 200))))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "psx_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", disc="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n in ("print", "disc") else None) for n, r in ROUGHNESS.items()}

    console = body(m)
    cover, hinge = lid(m)
    power, opener = button(m, "power"), button(m, "open")
    lit, lit_at = light(m)
    platter = disc(m)
    for obj in (console, cover, power, opener):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))
    # The console's normals weighted by its faces' areas: smoothed into its rounded corners, its broad flat faces showed
    # a dark streak across them.
    console.modifiers.new("weighted", "WEIGHTED_NORMAL").keep_sharp = True
    apply_modifiers(console)

    root = bpy.data.objects.new("psx_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    origin = Vector((0.0, 0.0, 0.0))
    for part, where in ((cover, hinge), (lit, lit_at), (platter, Vector(L.SEAT)), (power, origin), (opener, origin)):
        part.parent = console
        part.location = where
    nodes = {"lid": cover, "power": power, "open": opener, "power_light": lit, "disc": platter}

    # The three-quarter view, then the spec's fit of the console and its lid at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in console.data.vertices] + [tilt @ (v.co + hinge) for v in cover.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [console, cover, power, opener, lit, platter]
    print(f"PlayStation: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(console.data)} the console), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
