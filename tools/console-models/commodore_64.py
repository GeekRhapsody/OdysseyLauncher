"""The console theme's Commodore 64 system model (godot/themes/console/models/systems/c64.glb).

Made from a third-party Blender model (CC Attribution) of a Commodore 64 with its 1702 monitor, 1541 drive, joystick
and power supply, of which only the computer (the "breadbin", 64k triangles and three 4096² texture sets) is kept. Its
geometry, UVs and base colour maps are the source's, simplified while keeping its outline and printing:

- Faces that can't be seen from outside (the inside of the case, the hidden sides of keys and parts pressed against
  others) are removed: a face stays if any of RAYS rays cast from points over it, across its hemisphere, escapes the
  model, and faces that fail are tried again with RETRY_RAYS rays, so the insides of ports, seen through a small
  opening, are kept. A face seen only from behind is turned round.
- The rest is collapsed to TARGET triangles, the open edges (the source's parts are separate shells) held in place,
  and its normals weighted by face area, so flat faces stay flat next to long triangles.
- Only the base colour maps are kept, scaled down to TEXTURE_SIZE (every model's textures are drawn at most 1024
  pixels on their longer side, docs/THEMING.md section 7), in plain materials with the original roughness.

The computer is turned to a three-quarter view like the Mega Drive's (TILT_YAW, TILT_PITCH: its right end, with the
control ports and power socket, towards the viewer, and its top tipped up), then fitted to the model spec (A7):
standing on y = 0, centred, the largest side 1 m. No clips.

Three materials (details, keyboard, body) and three textures, within the system model budget. The source (the .blend
and its textures folder, not in the repository) is the commodore-64 folder at the repo root. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/commodore_64.py -- "commodore-64/source/commodore 64 (blend 3_6).blend" commodore-64/textures godot/themes/console/models/systems/c64.glb
"""

import math
import os
import random
import sys
import tempfile

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mega_drive_cartridge import export, material, triangles  # noqa: E402

SOURCE_OBJECT = "commodore 64"
TILT_YAW = -25.0     # degrees about the vertical: the right end (the ports) comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
RAYS, RETRY_RAYS = 48, 768
TARGET = 24000        # triangles after the collapse
TEXTURE_SIZE = 1024

# The source's materials: (our name, its base colour texture's file name prefix, roughness).
MATERIALS = {
    "computer_details": ("details", "commodore64_details_BaseColor", 0.5),
    "computer_keyboard": ("keyboard", "commodore64_keyboard_BaseColor", 0.55),
    "computer_main_body": ("body", "commodore64_main_body_BaseColor", 0.6),
}


def hemisphere(normal, count, rng):
    """count directions over the hemisphere around normal, cosine weighted."""
    t = normal.orthogonal().normalized()
    b = normal.cross(t)
    for _ in range(count):
        u, v = rng.random(), rng.random()
        r, phi = math.sqrt(u), 2 * math.pi * v
        yield (t * (r * math.cos(phi)) + b * (r * math.sin(phi)) + normal * math.sqrt(max(0.0, 1 - u))).normalized()


def remove_hidden(bm):
    """
    Deletes the faces no ray from outside can reach, and turns round the ones seen only from behind (a few of the
    source's faces face inwards, which the launcher, culling back faces, wouldn't draw).
    """
    tree = BVHTree.FromBMesh(bm)
    rng = random.Random(64)
    lo = Vector([min(v.co[a] for v in bm.verts) for a in range(3)])
    hi = Vector([max(v.co[a] for v in bm.verts) for a in range(3)])
    reach = (hi - lo).length * 2
    eps = (hi - lo).length * 1e-5

    def visible(face, count, side):
        n = face.normal * side
        if n.length < 0.5:
            return True
        # The rays start from points over the whole face, not just its centre: a long triangle's centre can be under
        # a foot while the rest of it is in plain view.
        corners = [v.co for v in face.verts]
        centre = sum(corners, Vector()) / len(corners)
        starts = [centre + n * eps] + [c * 0.8 + centre * 0.2 + n * eps for c in corners]
        for i, d in enumerate(hemisphere(n, count, rng)):
            if tree.ray_cast(starts[i % len(starts)], d, reach)[0] is None:
                return True
        return False

    unseen = [f for f in bm.faces if not visible(f, RAYS, 1)]
    unseen = [f for f in unseen if not visible(f, RETRY_RAYS, 1)]
    behind = [f for f in unseen if visible(f, RAYS, -1) or visible(f, RETRY_RAYS, -1)]
    flipped = set(behind)
    hidden = [f for f in unseen if f not in flipped]
    bmesh.ops.reverse_faces(bm, faces=behind)
    bmesh.ops.delete(bm, geom=hidden, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    return len(hidden), len(behind)


def simplify(obj):
    mesh = obj.data
    before = triangles(mesh)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    hidden, flipped = remove_hidden(bm)
    boundary = [v.index for v in bm.verts if v.is_boundary]
    bm.to_mesh(mesh)
    bm.free()
    visible = triangles(mesh)

    # Open edges (the source's parts are separate shells, and the removal opens more) are kept where they are: the
    # collapse would otherwise pull them across the faces next to them and open holes.
    group = obj.vertex_groups.new(name="collapse")
    group.add(range(len(mesh.vertices)), 1.0, "REPLACE")
    group.add(boundary, 0.0, "REPLACE")
    decimate = obj.modifiers.new("decimate", "DECIMATE")
    decimate.decimate_type = "COLLAPSE"
    decimate.ratio = min(1.0, TARGET / visible)
    decimate.use_collapse_triangulate = True
    decimate.vertex_group = group.name
    decimate.vertex_group_factor = 1000.0
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    print(f"Commodore 64: {before} triangles, {hidden} hidden removed, {flipped} turned round, {visible} left, "
          f"{triangles(mesh)} after the collapse")


def scaled_texture(textures, prefix, folder):
    name = next(f for f in sorted(os.listdir(textures)) if f.startswith(prefix))
    image = bpy.data.images.load(os.path.join(textures, name))
    image.scale(TEXTURE_SIZE, TEXTURE_SIZE)
    path = os.path.join(folder, prefix + ".jpg")
    image.filepath_raw = path
    image.file_format = "JPEG"
    bpy.context.scene.render.image_settings.quality = 90
    image.save(filepath=path, quality=90)
    return bpy.data.images.load(path)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    source, textures, out = (os.path.abspath(a) for a in args[:3])
    bpy.ops.wm.open_mainfile(filepath=source)
    obj = bpy.data.objects[SOURCE_OBJECT]
    for other in list(bpy.data.objects):
        if other is not obj:
            bpy.data.objects.remove(other)
    obj.modifiers.clear()
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    if obj.data.has_custom_normals:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.mesh.customdata_custom_splitnormals_clear()

    simplify(obj)

    with tempfile.TemporaryDirectory() as folder:
        mesh = obj.data
        for i, old in enumerate(mesh.materials):
            name, prefix, roughness = MATERIALS[old.name]
            mesh.materials[i] = material(name, "#FFFFFF", roughness, scaled_texture(textures, prefix, folder))
        for p in mesh.polygons:
            p.use_smooth = True
        mesh.set_sharp_from_angle(angle=math.radians(35))
        # The collapse leaves long triangles from flat faces to rounded edges, whose smooth normals would shade the
        # flat faces: weighting each vertex's normal by its faces' areas keeps them flat.
        weighted = obj.modifiers.new("normals", "WEIGHTED_NORMAL")
        weighted.mode = "FACE_AREA"
        weighted.keep_sharp = True
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=weighted.name)

        # The three-quarter view, then the spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
        mesh.transform(Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z"))
        lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
        hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
        size = hi - lo
        mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
        obj.name = mesh.name = "c64"
        print(f"Commodore 64: {triangles(mesh)} triangles, {len(mesh.materials)} materials")
        export([obj], out)


main()
