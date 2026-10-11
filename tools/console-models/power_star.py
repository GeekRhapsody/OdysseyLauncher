"""The console theme's Favourites card (godot/themes/console/models/systems/favourites.glb): Super Mario 64's Power Star.

A plump five-pointed star in gold: its outline's tips at OUTER, its inner corners at INNER, and each face rising from a
thin rim (EDGE) to a rounded peak in the middle (PEAK), with a ridge along each arm and a fold between arms, front and
back. At rest it's a plain star: its eyes (black, glossy, a white glint each) are shrunk to nothing inside it.

The `focused` clip (8 s, looping) wakes it up: the eyes open, the star hops for joy, looks left and right, blinks,
does the Power Star's spin (two turns about its vertical), blinks twice, wiggles side to side, and closes its eyes as
the clip comes round, so the loop starts and ends on the plain star. The grid's own lift and grow come on top.

A small node tree: a root (the turn towards a three-quarter view, TILT, and the model spec's fit: standing on y = 0,
centred, the largest side 1 m) holding the star, its origin in its middle, and the star holding its eyes, so they
ride along. The rest pose's bounds are the star's.

Three plain materials (gold, eye, glint), no textures, within the system model budget. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/power_star.py -- godot/themes/console/models/systems/favourites.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clip import HIDDEN, Pose, back_in, back_out, bump, hop, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import export, material, triangles  # noqa: E402

OUTER, INNER = 1.0, 0.5         # the tips' and the inner corners' distance from the middle
PEAK, EDGE = 0.40, 0.05         # each face's height over the middle plane: in the middle, and at the rim
BULGE = 1.5                     # how the faces round over: 1 is a pyramid, more stays high longer
STEPS = 12                      # rings from the middle to the rim
EYE = dict(x=0.165, z=0.04, width=0.09, height=0.2, depth=0.075, sink=0.037)  # half sizes
GLINT = dict(x=-0.35, z=0.42, width=0.32, height=0.34, depth=0.25)             # on the eye, as fractions of its sizes
TILT = (22.0, 6.0)              # degrees: yaw (its left arm nearer), pitch (its face up)
FPS, LENGTH = 30, 240
COLOURS = dict(gold="#F7C51E", eye="#0B0B0E", glint="#FFFFFF")
ROUGHNESS = dict(gold=0.22, eye=0.12, glint=0.3)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def corner(k):
    """The outline's corner k (even: a tip, odd: an inner corner), anticlockwise from the top tip, as (x, z)."""
    a = math.radians(90 + 36 * k)
    r = OUTER if k % 2 == 0 else INNER
    return r * math.cos(a), r * math.sin(a)


def height(t):
    """A face's height over the middle plane at the fraction t of the way from the middle to the rim."""
    return EDGE + (PEAK - EDGE) * (1 - t ** BULGE)


def star(mats):
    """The star, its middle at its origin, its front facing -y (glTF's +z)."""
    bm = bmesh.new()
    rings = {}
    for side in (-1, 1):  # -1 the front (-y), 1 the back
        apex = bm.verts.new((0.0, side * PEAK, 0.0))
        ring = [[apex] * 10]
        for i in range(1, STEPS + 1):
            t = i / STEPS
            ring.append([bm.verts.new((t * x, side * height(t), t * z)) for x, z in map(corner, range(10))])
        for i in range(STEPS):
            a, b = ring[i], ring[i + 1]
            for k in range(10):
                j = (k + 1) % 10
                quad = [a[k], b[k], b[j], a[j]] if i else [a[k], b[k], b[j]]
                face = bm.faces.new(quad if side > 0 else list(reversed(quad)))
                face.smooth = True
        rings[side] = ring[-1]
    for k in range(10):  # the rim, front to back
        j = (k + 1) % 10
        face = bm.faces.new([rings[-1][k], rings[-1][j], rings[1][j], rings[1][k]])
        face.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:  # the ridges and folds between arms stay crisp; the faces round over smoothly
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(20):
            e.smooth = False
    return finish("star", bm, [mats["gold"]])


def ellipsoid(bm, centre, radii, mat_index, segments=24, rings=12):
    """An ellipsoid (radii along x, y, z), its poles on z."""
    verts = [[bm.verts.new((centre[0] + radii[0] * math.sin(math.pi * i / rings) * math.cos(2 * math.pi * j / segments),
                            centre[1] + radii[1] * math.sin(math.pi * i / rings) * math.sin(2 * math.pi * j / segments),
                            centre[2] + radii[2] * math.cos(math.pi * i / rings)))
              for j in range(segments)] for i in range(1, rings)]
    top, bottom = bm.verts.new((centre[0], centre[1], centre[2] + radii[2])), bm.verts.new((centre[0], centre[1], centre[2] - radii[2]))
    faces = [[top, verts[0][(j + 1) % segments], verts[0][j]] for j in range(segments)]
    faces += [[bottom, verts[-1][j], verts[-1][(j + 1) % segments]] for j in range(segments)]
    for i in range(rings - 2):
        a, b = verts[i], verts[i + 1]
        faces += [[a[j], a[(j + 1) % segments], b[(j + 1) % segments], b[j]] for j in range(segments)]
    for f in faces:
        face = bm.faces.new(f)
        face.material_index = mat_index
        face.smooth = True


def eye(name, mats):
    """An eye, its middle at its origin, looking along -y: a flattened black ellipsoid and a glint on its upper left."""
    bm = bmesh.new()
    w, h, d = EYE["width"], EYE["height"], EYE["depth"]
    ellipsoid(bm, (0, 0, 0), (w, d, h), 0)
    gx, gz = GLINT["x"], GLINT["z"]
    front = -d * math.sqrt(max(0.0, 1 - gx * gx - gz * gz))
    ellipsoid(bm, (gx * w, front + d * 0.12, gz * h), (GLINT["width"] * w, GLINT["depth"] * d, GLINT["height"] * h), 1, 16, 8)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(name, bm, [mats["eye"], mats["glint"]])


def finish(name, bm, materials):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def on_surface(tree, x, z):
    """Where the star's front is at (x, z), and its normal there."""
    hit, normal, _, _ = tree.ray_cast(Vector((x, -2 * PEAK, z)), Vector((0, 1, 0)))
    return hit, normal


# ---- The focused clip ------------------------------------------------------------------------------------------------

BLINKS = [(66, 1.0), (150, 1.0), (160, 1.0)]  # (frame, how far they shut)


def lids(f):
    """How open the eyes are (1 open, 0 shut): they open at the start, blink, and shut as the clip comes round."""
    opening = back_out(phase(f, 3, 13), 1.6)
    closing = 1 - smooth(phase(f, 226, 234))
    open_ = min(opening, closing)
    for f0, depth in BLINKS:
        open_ *= 1 - depth * (smooth(phase(f, f0, f0 + 3)) - smooth(phase(f, f0 + 4, f0 + 8)))
    return max(open_, 0.0)


def eyes_width(f):
    """The eyes' width (1 their size): they appear just before they open and go just after they shut."""
    return HIDDEN + (1 - HIDDEN) * min(back_out(phase(f, 0, 6)), 1 - back_in(phase(f, 234, 240)))


def timeline(f):
    # A hop for joy once the eyes are open: down a little first, a stretch on the way up, a squash on landing.
    z = hop(f, 18, 34, 0.32) + hop(f, 182, 194, 0.12) + hop(f, 196, 208, 0.12)
    squash = 0.12 * bump(f, 13, 19) - 0.10 * bump(f, 18, 30) + wobble(f, 34, 0.14, 9, 6)
    squash += wobble(f, 194, 0.06, 8, 4) + wobble(f, 208, 0.08, 8, 5)
    # Looking left, then right (a turn of the head with a lean into it).
    look = 26 * (smooth(phase(f, 42, 50)) - 2 * smooth(phase(f, 56, 64)) + smooth(phase(f, 72, 80)))
    lean = 0.25 * look
    # The Power Star's spin: two turns, speeding up and slowing down, rising a little as it goes.
    turns = smooth(phase(f, 88, 144))
    spin = look + 720 * turns
    z += 0.12 * bump(f, 88, 148)
    # A wiggle: rocking side to side, the arms swinging.
    rock = 12 * math.sin(2 * math.pi * (f - 168) / 14) * bump(f, 168, 224) if 168 <= f <= 224 else 0.0
    open_, width = lids(f), eyes_width(f)
    eyes = Pose(axes=(width, width, max(open_, HIDDEN) * width))
    return {"star": Pose(z=z, spin=spin, roll=lean + rock, squash=squash), "eye_l": eyes, "eye_r": eyes}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    mats = {n: material(n, COLOURS[n], ROUGHNESS[n]) for n in COLOURS}

    body = star(mats)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    tree = BVHTree.FromBMesh(bm)
    bm.free()

    # The eyes sit sunk into the front, turned to face along its normal there.
    nodes = {"star": body}
    for name, side in (("eye_l", -1), ("eye_r", 1)):
        part = eye(name, mats)
        hit, normal = on_surface(tree, side * EYE["x"], EYE["z"])
        part.parent = body
        part.location = hit - normal * (EYE["depth"] - EYE["sink"])
        part.rotation_mode = "QUATERNION"
        part.rotation_quaternion = Vector((0, -1, 0)).rotation_difference(normal)
        nodes[name] = part

    # The three-quarter view, then the spec's fit of the star at rest, as the root's transform.
    root = bpy.data.objects.new("favourites_root", None)
    scene.collection.objects.link(root)
    body.parent = root
    yaw, pitch = TILT
    tilt = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
    points = [tilt @ v.co for v in body.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) @ tilt

    key("focused", nodes, timeline, LENGTH)
    meshes = [body, nodes["eye_l"], nodes["eye_r"]]
    print(f"Power Star: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(body.data)} the star), "
          f"{len(mats)} materials, size {size.x:.2f} x {size.y:.2f} x {size.z:.2f} tilted, before the fit")
    export([root] + meshes, out, animations=True)


main()
