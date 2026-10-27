"""The console theme's ScummVM system model (godot/themes/console/models/systems/scummvm.glb): the green S of ScummVM's
icon, made solid.

ScummVM has no hardware: it's the engine its games run on, so its card is the S of its icon. Built in Blender
(scummvm_layout.py has the S's outline, traced from the icon): the outline extruded back from the face, the face's and
the back's edges rounded; the face (and the rounding) the icon's bright green, the sides the darker green of its
extrusion. It stands on its foot, facing the viewer.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped a little; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the S (its
origin at its foot's middle).

The `focused` clip (5 s, looping): the S jumps about. It crouches and jumps high, spinning once round; hops to the left,
leaning into it; hops over to the right; then jumps back to the middle in a forward somersault about its own middle.
It squashes before each jump, stretches as it leaves the floor, and squashes and wobbles as it lands.

Two materials (face, side) and no texture, within the system model budget. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/scummvm.py -- godot/themes/console/models/systems/scummvm.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scummvm_layout as L  # noqa: E402
from clip import Pose, hop, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, export, material, triangles  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: the top tips a little towards the viewer
HEIGHT = 100.0       # the S's height (scummvm_layout.OUTLINE's)

# The jumps: take-off and landing frames, how high (mm), and where to across (x, mm).
JUMPS = [(10, 34, 48.0, 0.0), (46, 62, 22.0, -38.0), (68, 84, 24.0, 38.0), (94, 124, 55.0, 0.0)]


def letter(m):
    """The S: its outline extruded DEPTH back from the face, the caps the face's green, the sides the dark; the face's
    and the back's edges rounded, the rounding the face's green. Its origin at its foot's middle."""
    bm = bmesh.new()
    front = [bm.verts.new((x, 0.0, z)) for x, z in L.OUTLINE]
    back = [bm.verts.new((x, L.DEPTH, z)) for x, z in L.OUTLINE]
    n = len(front)
    for face in (bm.faces.new(front), bm.faces.new(list(reversed(back)))):
        face.material_index = 0
    for i in range(n):
        bm.faces.new([front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]]).material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("scummvm")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(m["face"])
    mesh.materials.append(m["side"])
    obj = bpy.data.objects.new("scummvm", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bevel(obj, L.ROUND, segments=3, angle=30.0)
    for p in obj.data.polygons:
        p.material_index = 1 if abs(p.normal.y) < 0.3 else 0
        p.use_smooth = abs(p.normal.y) < 0.99           # the face and the back flat, so they light evenly
    obj.data.set_sharp_from_angle(angle=math.radians(30))
    obj.data.transform(Matrix.Translation((0.0, -L.DEPTH / 2, 0.0)))
    return obj


# ---- The focused clip ------------------------------------------------------------------------------------------------

def timeline(f):
    x = z = roll = squash = start = 0.0
    for k, (f0, f1, height, to) in enumerate(JUMPS):
        t = phase(f, f0, f1)
        x += (to - start) * smooth(t)
        z += hop(f, f0, f1, height)
        squash += 0.16 * smooth(phase(f, f0 - 6, f0)) * (1 - smooth(phase(f, f0, f0 + 2)))      # the crouch
        squash -= 0.12 * smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2, f0 + 9)))  # the stretch
        squash += wobble(f, f1, 0.18, period=8.0, decay=4.5)                                    # the landing
        if k in (1, 2):
            roll += (10.0 if to > start else -10.0) * math.sin(math.pi * t)                     # leaning into it
        start = to
    spin = 360.0 * smooth(phase(f, 11, 33))
    pitch = 360.0 * smooth(phase(f, 96, 122))
    # The somersault turns about the S's middle, not its foot.
    a = math.radians(pitch)
    y = HEIGHT / 2 * math.sin(a)
    z += HEIGHT / 2 * (1 - math.cos(a))
    return {"scummvm": Pose(x=x, y=y, z=z, spin=spin, roll=roll, pitch=pitch, squash=squash)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    m = {"face": material("face", L.COLOURS["face"], 0.35), "side": material("side", L.COLOURS["side"], 0.45)}
    s = letter(m)

    root = bpy.data.objects.new("scummvm_root", None)
    scene.collection.objects.link(root)
    s.parent = root
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in s.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", {"scummvm": s}, timeline, L.LENGTH)
    print(f"ScummVM: {triangles(s.data)} triangles, {len(s.data.materials)} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root, s], out, animations=True)


if __name__ == "__main__":
    main()
