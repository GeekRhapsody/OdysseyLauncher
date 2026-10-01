"""Converts one Wavefront OBJ to a launcher-ready GLB. Run by tools/convert-obj.ps1 inside Blender:

    blender --background --factory-startup --python obj_to_glb.py -- <in.obj> <out.glb> [--height=<metres>]

Material names are kept, so an OBJ material named `cover` is still a slot. The export settings are
the ones in docs/THEMING.md section 9: glTF Binary, +Y Up, Custom Properties on, no Draco.
"""
import sys
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, dst = args[0], args[1]
height = 0.0
for a in args[2:]:
    if a.startswith("--height="):
        height = float(a.split("=", 1)[1])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=src)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    print("obj_to_glb: no mesh in " + src)
    sys.exit(3)

# Join into one object so the origin and scale are set once.
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active

# Optional: scale to a height in metres (the launcher refits sizes, so off by default).
if height > 0:
    bpy.context.view_layer.update()
    h = obj.dimensions.z
    if h > 0:
        obj.scale *= height / h

# Origin at the bottom centre, then apply all transforms.
bpy.context.view_layer.update()
corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
pivot = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
bpy.context.scene.cursor.location = pivot
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
obj.location = (0, 0, 0)
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
print("obj_to_glb: %d triangles, %d materials, %d images" % (tris, len(obj.data.materials), len(bpy.data.images)))

bpy.ops.export_scene.gltf(
    filepath=dst,
    export_format="GLB",
    use_selection=True,
    export_extras=True,
    export_yup=True,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_animations=False,
    export_draco_mesh_compression_enable=False,
)
