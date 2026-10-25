"""The console theme's PlayStation system model (godot/themes/console/models/systems/psx.glb).

Built in Blender from the first model's proportions (psx_layout.py has the measurements, taken from photographs): the
grey body, its corners rounded and its top's edges softened; the channel sunk into its top between the blocks at its
ends; a raised strip along the back of its top; the recess in
its front for the controller ports and memory card slots; the ribbed vents in its right end; POWER, RESET and OPEN, each
a round button in its well; and under the lid the well the disc spins in, with its spindle and the laser's lens on its
sled. The printing (the lid's logos, the buttons' legends, the seams, the ports, the disc's two sides) is one texture,
drawn by psx_print.py and projected onto the faces facing up and the recess's back wall.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: its right end towards the viewer, its
top tipped up, as the Mega Drive's; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding
the console; the console holding the lid (hinged along its back edge), the OPEN button, the power light lit, and the
disc (Odyssey, a made-up game: its label, and the PlayStation's black data side). The disc waits on the spindle shrunk
to nothing and the light is shrunk to nothing, so at rest the card is the console with its lid shut.

The `focused` clip (8 s, looping) plays a game: OPEN goes down and the lid springs up; the disc drops in from above,
spinning and flipping over to flash its black side, and settles on the spindle; the lid shuts with a bounce and the
power light comes on. Later OPEN again: the lid springs up, the disc rises spinning and goes, and the lid shuts.

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
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, print=0.5, dark=0.7, disc=0.25)
OPEN = 75.0          # degrees the lid opens


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


# ---- The console -----------------------------------------------------------------------------------------------------

def body(m):
    shell = solid("psx", [[(x, y, z) for x, y in rounded(0.0, L.DEPTH / 2, L.WIDTH, L.DEPTH, L.CORNER, 4)]
                          for z in (0.0, L.TOP)], m["case"])
    bevel(shell, 2.5, segments=2)
    strip = box("strip", -L.WIDTH / 2 + 2.0, L.WIDTH / 2 - 2.0, L.BACK["y"], L.DEPTH - 2.0, L.TOP - 1.0,
                L.TOP + L.BACK["height"], m["case"])
    bevel(strip, 1.0, segments=1)
    boolean(shell, strip, "UNION")

    boolean(shell, box("channel", L.SEAMS[0], L.SEAMS[1], -5.0, L.BACK["y"], L.TOP - L.CHANNEL, L.TOP + 5.0,
                       m["case"]))
    (x0, x1), (z0, z1) = L.RECESS["x"], L.RECESS["z"]
    boolean(shell, box("recess", x0, x1, -5.0, L.RECESS["depth"], z0, z1, m["case"]))
    floor = L.TOP - L.CHANNEL - L.WELL["depth"]
    boolean(shell, cylinder("well", L.LID["x"], L.LID["y"], L.WELL["r"], floor, L.TOP + 5.0, m["dark"], 48))
    for name, (x, y, r) in L.BUTTONS.items():
        boolean(shell, cylinder(name + "_well", x, y, r + L.BUTTON["well"], L.TOP - 3.0, L.TOP + 5.0, m["dark"]))
    x, y, length, width = L.LED
    boolean(shell, box("led", x - length / 2, x + length / 2, y - width / 2, y + width / 2, L.TOP - 1.0, L.TOP + 5.0,
                       m["dark"]))
    r = L.RIBS
    boolean(shell, join([box("rib", L.WIDTH / 2 - r["depth"], L.WIDTH / 2 + 5.0, y - r["width"] / 2,
                             y + r["width"] / 2, *r["z"], m["dark"]) for y in r["y"]], "ribs"))

    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "case")
    front = atlas_uv(L.REGIONS["front"], x1 - x0, z1 - z0)
    paint(shell, m["print"], lambda co: front(co.x - x0, z1 - co.z),
          lambda c, n, name: name == "case" and n.y < -0.9 and abs(c.y - L.RECESS["depth"]) < 0.2)

    # In the well: the spindle, and the laser's sled with its lens.
    parts = [shell]
    spindle = cylinder("spindle", L.LID["x"], L.LID["y"], L.SPINDLE["r"], floor - 0.5, floor + L.SPINDLE["height"],
                       m["print"], 24)
    paint(spindle, m["print"], swatch("metal"), lambda c, n, name: True)
    sled_w, sled_l = L.LENS["sled"]
    lx = L.LID["x"] + L.LENS["x"]
    sled = box("sled", lx - sled_l / 2, lx + sled_l / 2, L.LID["y"] - sled_w / 2, L.LID["y"] + sled_w / 2,
               floor - 0.5, floor + 4.0, m["print"])
    paint(sled, m["print"], swatch("dark"), lambda c, n, name: True)
    lens = cylinder("lens", lx, L.LID["y"], L.LENS["r"], floor + 3.5, floor + 5.0, m["print"], 16)
    paint(lens, m["print"], swatch("lens"), lambda c, n, name: True)
    parts += [spindle, sled, lens]

    # POWER and RESET, standing in their wells.
    for name in ("power", "reset"):
        parts.append(button(m, name))
    return join(parts, "psx")


def button(m, name):
    x, y, r = L.BUTTONS[name]
    top = L.TOP + L.BUTTON["height"]
    rings = [[(px, py, z) for px, py in circle(x, y, r - inset, 32)]
             for inset, z in ((0.0, L.TOP - 3.5), (0.0, top - 0.8), (0.6, top - 0.2), (2.0, top))]
    cap = solid(name, rings, m["case"])
    paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
    return cap


def lid(m):
    """The lid, its origin on its hinge (the top of its back edge): a broad disc, domed a little."""
    x, y, r, t, dome = L.LID["x"], L.LID["y"], L.LID["r"], L.LID["thickness"], L.LID["dome"]
    base = L.TOP - L.CHANNEL
    rings = [[(px, py, base + z) for px, py in circle(x, y, r - inset, 64)]
             for inset, z in ((0.0, 0.0), (0.0, t - 0.6), (0.7, t), (r * 0.35, t + dome * 0.6), (r * 0.7, t + dome))]
    cap = solid("lid", rings, m["case"])
    paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
    hinge = Vector((x, y + r, base + t))
    cap.data.transform(Matrix.Translation(-hinge))
    return cap, hinge


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
    x, y, length, width = L.LED
    lit = box("power_light", -length / 2 + 0.3, length / 2 - 0.3, -width / 2 + 0.3, width / 2 - 0.3, -0.6, 0.0,
              m["print"])
    paint(lit, m["print"], swatch("led"), lambda c, n, name: True)
    return lit, Vector((x, y, L.TOP - 0.3))


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 5, f0 + 9)))


def lid_angle(f, f0, f1):
    """Open between f0 (springing up) and f1 (shutting, with a bounce)."""
    opening = back_out(phase(f, f0, f0 + 12), 1.6) * (1 - ease_in(phase(f, f1 - 10, f1)))
    bounce = 4.0 * math.exp(-(f - f1) / 3.0) * abs(math.sin(math.pi * (f - f1) / 4.0)) if f >= f1 else 0.0
    return -(OPEN * opening + bounce)


def timeline(f):
    poses = {"open": Pose(z=-2.0 * (tap(f, 12) + tap(f, 170)))}
    poses["lid"] = Pose(pitch=lid_angle(f, 15, 80) if f < 160 else lid_angle(f, 173, 214))
    poses["power_light"] = Pose() if 84 <= f < 172 else Pose(scale=HIDDEN)

    # The disc: drops in spinning, flipping over once, settles on the spindle; later rises spinning and goes.
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
    opener = button(m, "open")
    lit, lit_at = light(m)
    platter = disc(m)
    for obj in (console, cover, opener):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("psx_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    for part, where in ((cover, hinge), (lit, lit_at), (platter, Vector(L.SEAT)), (opener, Vector((0.0, 0.0, 0.0)))):
        part.parent = console
        part.location = where
    nodes = {"lid": cover, "open": opener, "power_light": lit, "disc": platter}

    # The three-quarter view, then the spec's fit of the console and its lid at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in console.data.vertices] + [tilt @ (v.co + hinge) for v in cover.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [console, cover, opener, lit, platter]
    print(f"PlayStation: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(console.data)} the console), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
