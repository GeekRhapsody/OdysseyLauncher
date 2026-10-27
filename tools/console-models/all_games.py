"""The console theme's All games card (godot/themes/console/models/systems/all_games.glb): an untidy pile of game boxes.

All games has no hardware: it's every game, so its card is a pile of them, made-up games from tools/made-up-games's
library (no real game's art). Built in Blender from the base theme's own templates (memory-card's models/templates/: the
Mega Drive case, the Super Nintendo box and the N64's box), each imported, scaled back to its real size, the faces of
its slots (cover, back, spine) mapped onto its game's art in the two packed textures (all_games_print.py's), the rest
its case's colour (the Mega Drive's black, the boxes' dark flaps), and leant, turned and laid where all_games_layout.py
says: five stacked flat, each turned against the one under it, one leaning against the stack's right side, two on the
table in front of it and at its left. The materials aren't named after slots (cover, back, spine), which on a system
card would show the system's own art.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH; then the model spec's fit: standing on
y = 0, centred, the largest side 1 m) holding the pile; the pile holding the case on top (its origin at its middle) and,
through a node turned as it is, the N64 box leaning on the right (its origin on its bottom front edge).

The `focused` clip (5 s, looping): the top case crouches, hops off the pile, turning end over end, and lands back on it
with a squash; later the leaning box slips, tips forward till it nearly falls, and drops back against the pile with a
bounce.

Four materials (art, backs, case, shell) and two textures, within the system model budget. Run from the repo root, the
made-up games' library made first (tools/made-up-games/README.md):

    python tools/console-models/all_games_print.py artifacts/made-up-games/library artifacts/all_games
    blender -b --factory-startup --python tools/console-models/all_games.py -- artifacts/all_games godot/themes/console/models/systems/all_games.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import all_games_layout as L  # noqa: E402
from clip import Pose, hop, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import export, join, material, triangles  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.normpath(os.path.join(HERE, "..", "..", "godot", "themes", "memory-card", "models", "templates"))
TILT_YAW = -22.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 32.0    # degrees about the horizontal: the top tips up towards the viewer
TOP, LEANING = "halcyon_strike", "budling"      # the boxes the clip moves


def bounds(points):
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    return lo, hi


def template(system):
    """A system's template, imported: one mesh in millimetres, as it stands in the spec (on z = 0, its cover to -y)."""
    name, side = L.TEMPLATES[system]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(TEMPLATES, name))
    new = [o for o in bpy.data.objects if o not in before]
    obj = next(o for o in new if o.type == "MESH")
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    obj.data.transform(world)
    for o in new:
        if o is not obj:
            bpy.data.objects.remove(o)
    lo, hi = bounds([v.co for v in obj.data.vertices])
    obj.data.transform(Matrix.Scale(side / max(hi - lo), 4))
    return obj


def dress(obj, box, m):
    """Gives a template's faces the pile's materials: its slots' faces (cover, back, spine) its game's art in the
    textures, their UVs (0 to 1 across each face, upright) mapped into the art's region; the rest its case's colour."""
    mesh = obj.data
    kinds = [mat.name.split(".")[0] for mat in mesh.materials]
    was = [p.material_index for p in mesh.polygons]
    mesh.materials.clear()
    case = m["shell"] if box["system"] == "megadrive" else m["case"]
    for mat in (m["art"], m["backs"], case):
        mesh.materials.append(mat)
    uv = mesh.uv_layers[0]
    aw, ah = L.ATLAS_SIZE
    regions = L.REGIONS[box["name"]]
    for p, index in zip(mesh.polygons, was):
        if kinds[index] not in regions:
            p.material_index = 2
            continue
        atlas, (x, y, w, h) = regions[kinds[index]]
        p.material_index = 0 if atlas == "art" else 1
        for li in p.loop_indices:
            u, v = uv.data[li].uv
            uv.data[li].uv = ((x + u * w) / aw, 1 - (y + (1 - v) * h) / ah)
    obj.name = mesh.name = box["name"]


def place(obj, box):
    """Leans a box back (or lays it down) and turns it, then sets the middle of its footprint at (x, y) and its
    underside at z. Returns the turn."""
    turn = Matrix.Rotation(math.radians(box["yaw"]), 4, "Z") @ Matrix.Rotation(math.radians(box["pitch"]), 4, "X")
    obj.data.transform(turn)
    lo, hi = bounds([v.co for v in obj.data.vertices])
    x, y, z = box["at"]
    obj.data.transform(Matrix.Translation((x - (lo.x + hi.x) / 2, y - (lo.y + hi.y) / 2, z - lo.z)))
    return turn


# ---- The focused clip ------------------------------------------------------------------------------------------------

def timeline(f):
    # The top case: a crouch, a hop end over end, a landing with a squash.
    if f < 12:
        squash = 0.12 * smooth(phase(f, 4, 12))
    elif f < 16:
        squash = 0.12 - 0.22 * smooth(phase(f, 12, 16))
    elif f < 40:
        squash = -0.1 * (1 - smooth(phase(f, 16, 30)))
    else:
        squash = wobble(f, 40, 0.14, period=8.0, decay=5.0)
    top = Pose(z=hop(f, 14, 40, 95.0), pitch=360.0 * smooth(phase(f, 15, 38)), squash=squash)

    # The leaning box: slips, tips forward till it nearly falls, drops back against the pile and bounces.
    if f < 106:
        tip = 9.0 * math.sin(math.pi * smooth(phase(f, 80, 106)))
    else:
        tip = 1.6 * math.exp(-(f - 106) / 5.0) * abs(math.sin(2 * math.pi * (f - 106) / 9.0))
    return {TOP: top, LEANING: Pose(pitch=tip)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    m = {
        "art": material("art", "#FFFFFF", 0.45, bpy.data.images.load(os.path.join(images, "all_games_art.jpg"))),
        "backs": material("backs", "#FFFFFF", 0.45, bpy.data.images.load(os.path.join(images, "all_games_backs.jpg"))),
        "case": material("case", "#1C1C20", 0.6),
        "shell": material("shell", "#0F0F11", 0.3),
    }

    boxes, turns = {}, {}
    for box in L.BOXES:
        obj = template(box["system"])
        dress(obj, box, m)
        turns[box["name"]] = place(obj, box)
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))
        boxes[box["name"]] = obj

    # The top case moves about its middle; the leaning box about its bottom front edge, in a node turned as it is.
    top = boxes.pop(TOP)
    lo, hi = bounds([v.co for v in top.data.vertices])
    middle = (lo + hi) / 2
    top.data.transform(Matrix.Translation(-middle))
    leaning = boxes.pop(LEANING)
    turn = turns[LEANING]
    facing = (turn @ Vector((0.0, -1.0, 0.0, 0.0))).to_3d()
    lo, hi = bounds([v.co for v in leaning.data.vertices])
    bottom = [v.co for v in leaning.data.vertices if v.co.z < lo.z + 0.5]
    reach = max(v.dot(facing) for v in bottom)
    edge = [v for v in bottom if v.dot(facing) > reach - 0.5]
    pivot = Vector((sum(v.x for v in edge) / len(edge), sum(v.y for v in edge) / len(edge), lo.z))
    yaw = Matrix.Rotation(math.radians(next(b["yaw"] for b in L.BOXES if b["name"] == LEANING)), 4, "Z")
    leaning.data.transform(yaw.inverted() @ Matrix.Translation(-pivot))

    pile = join(list(boxes.values()), "all_games")
    root = bpy.data.objects.new("all_games_root", None)
    scene.collection.objects.link(root)
    pile.parent = root
    top.parent = pile
    top.location = middle
    stand = bpy.data.objects.new("budling_turn", None)
    scene.collection.objects.link(stand)
    stand.parent = pile
    stand.matrix_basis = Matrix.Translation(pivot) @ yaw
    leaning.parent = stand

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in pile.data.vertices] + [tilt @ (v.co + middle) for v in top.data.vertices] \
        + [tilt @ (Matrix.Translation(pivot) @ yaw @ v.co) for v in leaning.data.vertices]
    lo, hi = bounds(points)
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", {TOP: top, LEANING: leaning}, timeline, L.LENGTH)
    meshes = [pile, top, leaning]
    print(f"All games: {sum(triangles(o.data) for o in meshes)} triangles, "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root, stand] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
