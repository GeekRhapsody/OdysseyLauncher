"""The console theme's PlayStation Vita system model (godot/themes/console/models/systems/psvita.glb): the first PS
Vita, the PCH-1000 in black, standing up.

Built in Blender from the real handheld's measurements (psvita_layout.py has them, and their sources): the body is its
face's outline (a straight top and bottom, each end half an ellipse) lofted back through its depth: the glossy panel,
its edge rounded over; the gunmetal frame round the edge; the matte back shell, rounded over broadly to the back's
flat. The shoulder buttons' corners are chrome at every depth, and a hole goes through each bottom corner, the frame
looping round it; the sticks' recesses are cut into the face. On the face stand the D-pad's four arms, the four face
buttons, the PS button, SELECT and START, each a solid domed over, and the two sticks, each a dished cap on a short neck
rising out of its recess; the screen's glass is one flat face over the face's printing. On the top edge, POWER and VOL
- and +; on the back, the rear camera's pod. The printing is two textures drawn by psvita_print.py, the face and the
edges in one atlas, the back in another; the glass has its own, the OLED switched off.

The glass's material is `video`: while the card is focused, the launcher plays the theme's video for it there
(godot/themes/console/videos/psvita.mp4, drawn by psvita_video.py), starting it again each time the clip loops (A6 Card
videos); otherwise, and where there's no decoder, it shows its own texture, the screen switched off.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
face tipped up a little; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the
console, which leans about its middle; the console holding the PS button (and its lit top, shrunk to nothing while it's
dark, riding it), START, SQUARE, TRIANGLE and CIRCLE, the left stick (about its pivot behind the face) and POWER.

The `focused` clip (11 s, looping; its timing is psvita_layout.py's, which the video follows) plays a game with no
cartridge or disc to put in, the Vita's way: the PS button wakes it and lights blue; a finger peels the lock screen
away, taps the game's bubble on the home screen and Start on its LiveArea's gate; START at the title; the fight: the
left stick walks Juno in, the console leaning with it, SQUARE, TRIANGLE and CIRCLE land a combo, VOLT is touched on the
screen and the console jolts with the finisher, K.O.; the PS button goes back to the LiveArea, which a finger peels
away to close the game; POWER puts it to sleep.

Six materials (case, frame, chrome, buttons, rear, video) and three textures, within the system model budget. Run from
the repo root:

    python tools/console-models/psvita_print.py artifacts/made-up-games artifacts/psvita
    python tools/console-models/psvita_video.py artifacts/made-up-games godot/themes/console/videos/psvita.mp4
    blender -b --factory-startup --python tools/console-models/psvita.py -- artifacts/psvita godot/themes/console/models/systems/psvita.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psvita_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import boolean, export, join, material, new_object, triangles  # noqa: E402
from saturn import inset  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end (the face buttons) comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.2, frame=0.4, chrome=0.16, buttons=0.28, rear=0.72, video=0.5)
PIVOT = Vector((0.0, L.DEPTH / 2, L.MID))   # the console leans about its middle
PRESS = 0.7                                 # how far a button goes in


# ---- UVs ---------------------------------------------------------------------------------------------------------------

def region_uv(regions, name, mirror=False, depth=None, about=(0.0, 0.0)):
    """A planar projection into an atlas region: (x, z) in millimetres to UVs (less about, for a region drawn about a
    part's middle); mirror for a face seen from behind; depth "top" for the top edge seen from above (its back at the
    region's top), "bottom" for the bottom edge seen from below (its face at the region's top)."""
    px, py, pw, ph = regions[name]["px"]
    x0, x1, z0, z1 = regions[name]["mm"]

    def uv(co):
        x = (-co.x if mirror else co.x) - about[0]
        if depth == "top":
            down = (z1 - co.y) / (z1 - z0)
        elif depth == "bottom":
            down = (co.y - z0) / (z1 - z0)
        else:
            down = (z1 - (co.z - about[1])) / (z1 - z0)
        return (px + (x - x0) / (x1 - x0) * pw) / L.ATLAS, 1 - (py + down * ph) / L.ATLAS
    return uv


FRONT = region_uv(L.PRINT_REGIONS, "front")
TOP = region_uv(L.PRINT_REGIONS, "top", depth="top")
BOTTOM = region_uv(L.PRINT_REGIONS, "bottom", depth="bottom")
LIT = region_uv(L.PRINT_REGIONS, "lit", about=(L.PS["x"], L.PS["z"]))
REAR = region_uv(L.REAR_REGIONS, "rear", mirror=True)


def swatch(name, swatches=L.SWATCHES):
    x, y = swatches[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def shade(obj, angle=35.0):
    """Smooth shading, edges sharper than angle kept sharp; flat faces (caps) stay flat."""
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) <= 4
    obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


def circle(x, z, r, n=28):
    return [(x + r * math.cos(2 * math.pi * k / n), z + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def at_origin(obj, where):
    """The part's mesh moved so that where (in the set) is its origin: it moves from there."""
    obj.data.transform(Matrix.Translation(-Vector(where)))
    return obj, Vector(where)


def prism_y(name, outline, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1."""
    return solid(name, [[(x, y, z) for x, z in outline] for y in (y0, y1)], mat)


# ---- The body ----------------------------------------------------------------------------------------------------------

def rings():
    """The body's rings, front to back: (y, inset, what the band after it is)."""
    out = []
    r = L.FRONT_ROUND
    for k in range(4):
        a = math.pi / 2 * k / 3
        out.append((r * (1 - math.cos(a)), r * (1 - math.sin(a)), "front"))
    b0, b1 = L.BAND
    out += [(b0 - 0.12, 0.0, "front"), (b0, 0.2, "groove"), (b0 + 0.12, 0.0, "band"), (b1 - 0.12, 0.0, "band"),
            (b1, 0.2, "groove"), (b1 + 0.12, 0.0, "back")]
    y0 = b1 + 0.12
    for k in range(1, 9):                                   # the back shell rounding over to its flat
        a = math.pi / 2 * k / 8
        out.append((y0 + (L.DEPTH - y0) * math.sin(a), L.BACK_INSET * (1 - math.cos(a)), "back"))
    return out


def body(m):
    """The shell from the face's outline through its depth, each band of faces its material, the sticks' recesses cut
    into it; and its corners, pieces of their own (corners())."""
    spec = rings()
    bm = bmesh.new()
    loops = [[bm.verts.new((x, y, z)) for x, z in L.body_outline(d)] for y, d, _ in spec]
    kinds = []
    for (a, b), (_, _, kind) in zip(zip(loops, loops[1:]), spec):
        n = len(a)
        for j in range(n):
            bm.faces.new([a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]])
            kinds.append(kind)
    bm.faces.new(loops[0])
    bm.faces.new(list(reversed(loops[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    kinds += ["front_cap", "back_cap"]                      # the faces keep the order they were made in
    obj = new_object("psvita", bm, m["case"])
    mesh = obj.data
    for mat in (m["frame"], m["chrome"], m["rear"]):
        mesh.materials.append(mat)
    names = [mt.name for mt in mesh.materials]
    uv = mesh.uv_layers.new(name="UVMap")
    for p, kind in zip(mesh.polygons, kinds):
        c, n = p.center, p.normal
        if kind == "front_cap":
            mat, uv_of = "case", FRONT
        elif kind == "back_cap":
            mat, uv_of = "rear", REAR
        elif kind == "front":
            mat, uv_of = "case", swatch("case")
        elif kind == "groove":
            mat, uv_of = "case", swatch("dark")
        elif kind == "band":
            mat, uv_of = "frame", (TOP if n.z > 0.7 else BOTTOM if n.z < -0.7 else swatch("frame"))
        else:
            mat, uv_of = "rear", (REAR if n.y > 0.3 else swatch("rear", L.REAR_SWATCHES))
        p.material_index = names.index(m[mat].name)
        for li in p.loop_indices:
            uv.data[li].uv = uv_of(mesh.vertices[mesh.loops[li].vertex_index].co)
    shade(obj)
    recesses(obj, m)
    return [obj] + corners(obj, m)


def corners(obj, m):
    """The corners cut out of the body as pieces of their own, so their edges follow their outlines rather than the
    body's faces: at the top, the shoulder buttons' chrome (its face the printed crescent, its top the printed pill);
    at the bottom, the frame's loops, each with its hole through it."""
    def cut(region):
        piece = obj.copy()
        piece.data = obj.data.copy()
        bpy.context.scene.collection.objects.link(piece)
        boolean(piece, prism_y("region", region, -2.0, L.DEPTH + 2.0, m["frame"]), "INTERSECT")
        boolean(obj, prism_y("region", region, -2.0, L.DEPTH + 2.0, m["frame"]))
        return piece

    pieces = []
    for side in (-1, 1):
        shoulder = cut(L.shoulder_region(side))
        paint(shoulder, m["chrome"], swatch("chrome"), lambda c, n, kind: True)
        paint(shoulder, m["chrome"], FRONT, lambda c, n, kind: n.y < -0.9 and c.y < 0.05)
        paint(shoulder, m["chrome"], TOP, lambda c, n, kind: n.z > 0.7 and c.y > L.BAND[0])
        loop = cut(L.notch_region(side))
        boolean(loop, prism_y("hole", L.hole_outline(side), -2.0, L.DEPTH + 2.0, m["frame"]))
        paint(loop, m["frame"], swatch("frame"), lambda c, n, kind: True)
        pieces += [shade(shoulder), shade(loop)]
    return pieces


def recesses(obj, m):
    """The sticks' recesses cut into the face, their floors the face's printing."""
    depth = L.STICK["recess"]
    r = L.STICK["bezel"] - 0.45
    cutters = [prism_y("recess", circle(x, z, r, 40), -2.0, depth, m["case"]) for x, z in L.STICKS.values()]
    boolean(obj, join(cutters, "recesses"))
    paint(obj, m["case"], FRONT, lambda c, n, kind: n.y < -0.9 and abs(c.y - depth) < 0.05)
    paint(obj, m["case"], swatch("dark"), lambda c, n, kind: 0.01 < c.y < depth - 0.01 and abs(n.y) < 0.5
          and any(math.hypot(c.x - x, c.z - z) < r + 0.3 for x, z in L.STICKS.values()))


# ---- The controls --------------------------------------------------------------------------------------------------------

def button(name, outline_at, height, dome, m, rings_=4, top=FRONT, mat="buttons"):
    """A button standing out of the face: its foot inside it, straight sides out to height, then a dome (inset, rise)
    over; outline_at(inset) its rim. The faces turned to the viewer take top's printing (its symbol)."""
    stack = [(outline_at(0.0), 0.6), (outline_at(0.0), -height)]
    for k in range(1, rings_ + 1):
        a = math.pi / 2 * k / rings_
        stack.append((outline_at(dome[0] * (1 - math.cos(a))), -height - dome[1] * math.sin(a)))
    obj = solid(name, [[(x, y, z) for x, z in pts] for pts, y in stack], m[mat])
    paint(obj, m[mat], top, lambda c, n, kind: n.y < -0.35)
    paint(obj, m[mat], swatch("buttons"), lambda c, n, kind: n.y >= -0.35)
    return shade(obj, 50.0)


def oval(x, z, half):
    return lambda d: [(x + (half[0] - d) * math.cos(2 * math.pi * k / 36), z + (half[1] - d) * math.sin(2 * math.pi * k / 36))
                      for k in range(36)]


def controls(m):
    """The buttons and sticks: the still ones joined into the set; those the clip moves apart."""
    still, moving = [], {}
    for name, a in L.DPAD_BUTTONS:
        corners, radii = L.dpad_arm(a)
        rim = L.rounded_polygon(corners, radii, 6)
        still.append(button("dpad_" + name, lambda d, rim=rim: inset(rim, d) if d > 1e-6 else rim, 1.1, (0.7, 0.45), m))
    r = L.FACE["radius"]
    for name, x, z in L.face_centres():
        part = button("face_" + name, lambda d, x=x, z=z: circle(x, z, r - d, 32), 1.2, (1.4, 0.6), m)
        if name in L.PUNCHES:
            moving[name] = at_origin(part, (x, 0.0, z))
        else:
            still.append(part)
    x, z = L.PS["x"], L.PS["z"]
    moving["ps"] = at_origin(button("ps", oval(x, z, L.PS["half"]), 0.9, (1.2, 0.45), m), (x, 0.0, z))
    lit = button("ps_lit", oval(x, z, (L.PS["half"][0] + 0.1, L.PS["half"][1] + 0.1)), 0.98, (1.25, 0.5), m, top=LIT)
    moving["ps_lit"] = at_origin(lit, (x, 0.0, z)) + ("ps",)
    for name in ("SELECT", "START"):
        x, z = L.SMALL[name]
        part = button("row_" + name.lower(), oval(x, z, L.SMALL["half"]), 0.6, (0.6, 0.25), m, rings_=3)
        if name == "START":
            moving["start"] = at_origin(part, (x, 0.0, z))
        else:
            still.append(part)
    for side, (x, z) in L.STICKS.items():
        part = stick("stick_" + side, x, z, m)
        if side == "left":
            moving["stick_l"] = at_origin(part, (x, L.STICK["pivot"], z))
        else:
            still.append(part)
    return still, moving


def stick(name, x, z, m):
    """A stick: a short neck rising out of its recess to a cap, its rim rounded and its top dished; the top takes the
    face's printing where the stick rests."""
    s = L.STICK
    profile = [(s["neck"], s["recess"] + 0.1), (s["neck"], -1.9), (3.6, -2.05), (s["cap"] - 0.2, -2.2), (s["cap"], -2.5),
               (s["cap"], -3.25), (s["cap"] - 0.15, -3.5), (s["cap"] - 0.5, -s["top"]), (3.5, -s["top"] + 0.12),
               (2.2, -s["top"] + 0.24), (0.9, -s["top"] + 0.28)]
    part = solid(name, [[(px, y, pz) for px, pz in circle(x, z, r, 36)] for r, y in profile], m["buttons"])
    paint(part, m["buttons"], FRONT, lambda c, n, kind: n.y < -0.35)
    paint(part, m["buttons"], swatch("buttons"), lambda c, n, kind: n.y >= -0.35)
    return shade(part, 50.0)


def top_edge(m):
    """POWER (apart: the clip presses it) and VOL - and + (in the set), standing on the top edge, their tops the top
    edge's printing."""
    def round_button(name, x, y, r, height):
        rings_ = [(r, -0.6), (r, height - 0.25), (r - 0.25, height - 0.05), (r - 0.6, height)]
        part = solid(name, [[(px, py, L.HEIGHT + h) for px, py in circle(x, y, rr, 28)] for rr, h in rings_], m["frame"])
        paint(part, m["frame"], TOP, lambda c, n, kind: n.z > 0.5)
        paint(part, m["frame"], swatch("buttons"), lambda c, n, kind: n.z <= 0.5)
        return shade(part, 50.0)

    p, t = L.POWER, L.TOP
    power = at_origin(round_button("power", p["x"], p["y"], p["r"], p["height"]), (p["x"], p["y"], L.HEIGHT))
    y = sum(t["housing_y"]) / 2
    volume = [round_button("vol", x, y, L.VOLUME["r"], L.VOLUME["height"]) for x in (t["minus"], t["plus"])]
    return power, volume


def pod(m):
    """The rear camera's pod on the back's rounded top: a stadium standing out of the shell, its back printed."""
    p = L.POD
    outline = L.stadium(-p["half_width"], p["half_width"], *p["z"], n=10)
    part = solid("pod", [[(x, y, z) for x, z in inset(outline, d)] for d, y in
                         ((0.0, p["y"][0]), (0.0, p["y"][1] - 0.5), (0.25, p["y"][1] - 0.12), (0.6, p["y"][1]))], m["rear"])
    paint(part, m["rear"], REAR, lambda c, n, kind: n.y > 0.5)
    paint(part, m["rear"], swatch("pod", L.REAR_SWATCHES), lambda c, n, kind: n.y <= 0.5)
    return shade(part, 45.0)


def screen(m):
    """The glass: one flat face over the face's printing, the video's whole frame across it."""
    (x0, x1), (z0, z1) = L.GLASS["x"], L.GLASS["z"]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]          # anticlockwise seen from the front: it faces -y
    face = bm.faces.new([bm.verts.new((x, -0.04, z)) for x, z in corners])
    for loop, (x, z) in zip(face.loops, corners):
        loop[uv].uv = ((x - x0) / (x1 - x0), (z - z0) / (z1 - z0))
    return new_object("glass", bm, m["video"])


# ---- The clip --------------------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    """A button pressed at f0: in over two frames, held, out over three."""
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def jolt(f, f0, degrees, period=7.0, decay=5.0):
    """A damped shake from f0."""
    return 0.0 if f < f0 else degrees * math.exp(-(f - f0) / decay) * math.sin(2 * math.pi * (f - f0) / period)


def timeline(f):
    poses = {}
    # The console leans the way the stick pushes, the right end down as Juno walks in; it jolts as the finisher lands
    # and again at the K.O.
    sx, sz = L.stick(f)
    hit = L.VOLT[0] + 4
    poses["console"] = Pose(roll=2.6 * sx, pitch=jolt(f, hit, 2.2) + jolt(f, L.KO, 1.4), spin=jolt(f, hit, -1.2, 9.0))
    # The PS button wakes it (lighting blue) and later pauses the game; START at the title; the combo.
    poses["ps"] = Pose(y=PRESS * max(tap(f, L.WAKE), tap(f, L.PS_PAUSE)))
    poses["ps_lit"] = Pose() if L.LIT[0] <= f < L.LIT[1] else Pose(scale=HIDDEN)
    poses["start"] = Pose(y=PRESS * 0.8 * tap(f, L.START, 3))
    for name, f0 in L.PUNCHES.items():
        poses[name] = Pose(y=PRESS * tap(f, f0))
    # The left stick tilts about its pivot: spin swings its cap to the right, pitch (negated) up.
    tilt = L.STICK["tilt"]
    poses["stick_l"] = Pose(spin=tilt * sx, pitch=-tilt * sz)
    # POWER, pressed into the top edge: standby.
    poses["power"] = Pose(z=-L.POWER["travel"] * tap(f, L.POWER_OFF, 3))
    return poses


# ---- Main --------------------------------------------------------------------------------------------------------------

def finish(whole, parts, out):
    """card.finish(), but the set leans too: the root holds the console, keyed about its middle, which holds the parts
    (each at its place in the set, or in another part it rides). The root turns the card to the three-quarter view and
    fits its rest pose."""
    scene = bpy.context.scene
    root = bpy.data.objects.new("psvita_root", None)
    scene.collection.objects.link(root)
    whole.data.transform(Matrix.Translation(-PIVOT))
    whole.parent = root
    whole.location = PIVOT
    nodes = {"console": whole}
    for name, spec in parts.items():
        obj, where = spec[0], spec[1]
        holder = parts[spec[2]][0] if len(spec) > 2 else whole
        obj.parent = holder
        obj.location = where - PIVOT if holder is whole else where - parts[spec[2]][1]
        nodes[name] = obj
    key("focused", nodes, timeline, L.LENGTH)
    bpy.context.view_layer.update()

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    meshes = list(nodes.values())
    points = [tilt @ (o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt
    textures = {node.image.name for o in meshes for mat in o.data.materials if mat.node_tree
                for node in mat.node_tree.nodes if node.type == "TEX_IMAGE" and node.image}
    print(f"PS Vita: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, {len(textures)} textures, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "psvita_print.png"))
    back = bpy.data.images.load(os.path.join(images, "psvita_rear.png"))
    still = bpy.data.images.load(os.path.join(images, "psvita_screen.png"))
    textures = dict(case=printed, frame=printed, chrome=printed, buttons=printed, rear=back, video=still)
    m = {n: material(n, "#FFFFFF", r, textures[n]) for n, r in ROUGHNESS.items()}

    still_parts, moving = controls(m)
    power, volume = top_edge(m)
    whole = join(body(m) + still_parts + volume + [pod(m), screen(m)], "psvita")
    parts = dict(moving)
    parts["power"] = power
    finish(whole, parts, out)


if __name__ == "__main__":
    main()
