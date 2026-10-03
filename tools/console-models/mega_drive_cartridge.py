"""The console theme's Mega Drive cartridge template (godot/themes/console/models/templates/megadrive_cartridge.glb).

A Japanese and European Mega Drive cartridge, 110 x 86 mm: thin (12 mm) where it goes into the console, thicker (19 mm)
above, with the rounded top and the notches in its sides. The label sits in a recess between raised side bands, as
on the real cartridge: the game's art above, and below it the label's own band (the grid and the MEGA DRIVE logo under
the grey border, from mega_drive_label.png), cut along the border's curve. The art is the `cover` slot (the box art,
centre-cropped to the window, else the launcher's title card); the band is a plain textured material. It faces the
front, upright, fitted to the model spec (A7): standing on y = 0, centred, the largest side 1 m.

Four materials (case, cover, band, pcb) and one texture, within the game template budget. mega_drive.py builds the
same cartridge, with the whole label, for the console's focused clip. Run from the repo root:

    python tools/console-models/mega_drive_print.py artifacts/megadrive
    blender -b --factory-startup --python tools/console-models/mega_drive_cartridge.py -- artifacts/megadrive godot/themes/console/models/templates/megadrive_cartridge.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

WIDTH = 110.0
HEIGHT = 86.0
FRONT = -6.0                    # the front (label) face; Blender's front is -Y
LOWER_BACK, UPPER_BACK = 6.0, 13.0  # the back: thin below, thick above
RECESS = (43.0, 12.0, 1.0)      # the label's recess: half its width, its bottom, its depth
LABEL_WIDTH = 80.0              # the label (600 x 500 pixels) and where its bottom is
LABEL_PX = 7.5                  # label pixels per millimetre
LABEL_BOTTOM = 15.5
BAND_TOP = 356                  # the band image's first row (as in mega_drive_print.py)
WINDOW_BOTTOM = 393.5           # the row where the art window's straight sides end (the border's top at the sides)


def border_top(x):
    """The row where the label's grey border starts, at column x (as mega_drive_print.py has it)."""
    return 393.5 - 27.5 * math.exp(-((x - 300) / 62) ** 2)


def srgb(hex_colour):
    """A #RRGGBB sRGB colour as Blender's linear RGBA."""
    def linear(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(linear(int(hex_colour[i:i + 2], 16)) for i in (1, 3, 5)) + (1.0,)


def material(name, colour, roughness, image=None, aspect=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(colour)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    if image is not None:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Linear"
        tex.extension = "EXTEND"
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if aspect is not None:
        m["aspect"] = aspect  # extras.aspect: the slot face's width over its height (A7)
    return m


def new_object(name, bm, mat):
    """A mesh object from a bmesh, every face in one material, linked to the scene."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def box(name, x0, x1, y0, y1, z0, z1, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    return new_object(name, bm, mat)


def prism_x(name, profile, x0, x1, mat):
    """A solid from a (y, z) outline, extruded along x from x0 to x1."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in profile]
    b = [bm.verts.new((x1, y, z)) for y, z in profile]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(len(profile)):
        j = (i + 1) % len(profile)
        bm.faces.new([a[i], b[i], b[j], a[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def arc(cy, cz, r, a0, a1, segments):
    """Points round an arc in the (y, z) plane, from angle a0 to a1 (degrees), both ends included."""
    return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * k / segments)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / segments))) for k in range(segments + 1)]


def apply_modifiers(obj):
    """Applies an object's modifiers, keeping its materials."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
    obj.modifiers.clear()
    old = obj.data
    obj.data = mesh
    bpy.data.meshes.remove(old)


def boolean(obj, cutter, operation="DIFFERENCE"):
    """Cuts (or joins, or intersects) cutter into obj; the faces the cutter makes keep its material. Removes cutter."""
    m = obj.modifiers.new("boolean", "BOOLEAN")
    m.operation = operation
    m.object = cutter
    m.solver = "EXACT"
    m.material_mode = "TRANSFER"
    apply_modifiers(obj)
    bpy.data.objects.remove(cutter)


def bevel(obj, width, segments=2, angle=40.0):
    m = obj.modifiers.new("bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.harden_normals = False
    apply_modifiers(obj)


def join(objects, name):
    """Joins objects into the first, renamed."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        if not o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")  # so the join keeps the textured parts' UVs
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = name
    return obj


def faces_from_grid(bm, uv_layer, columns, rows_at, z_of, uv_of, mat_index):
    """Quads across the label: for each column pair, from rows_at(x)[0] up to rows_at(x)[1], label pixels."""
    for k in range(len(columns) - 1):
        quad = []
        for x, which in ((columns[k], 0), (columns[k + 1], 0), (columns[k + 1], 1), (columns[k], 1)):
            row = rows_at(x)[which]
            quad.append((x, row))
        verts = [bm.verts.new((-LABEL_WIDTH / 2 + x / LABEL_PX, FRONT + RECESS[2] - 0.05, z_of(row))) for x, row in quad]
        face = bm.faces.new(verts)
        face.material_index = mat_index
        for loop, (x, row) in zip(face.loops, quad):
            loop[uv_layer].uv = uv_of(x, row)


def build(mats, whole_label):
    """
    The cartridge in millimetres, standing on its connector edge at the origin, its label facing -Y. mats: case,
    pcb, and either label (whole_label: the whole label on one face) or cover and band (the template's art window
    and the label's band).
    """
    # The body: a side outline extruded across the width, its edges softened.
    transition = [(LOWER_BACK + (UPPER_BACK - LOWER_BACK) * (1 - math.cos(math.pi * k / 6)) / 2, 40.0 + 12.0 * k / 6)
                  for k in range(7)]
    profile = [(FRONT, 0.0)] + [(LOWER_BACK, 0.0)] + transition + arc(UPPER_BACK - 9.0, HEIGHT - 9.0, 9.0, 0, 90, 8)[1:] \
        + arc(FRONT + 3.0, HEIGHT - 3.0, 3.0, 90, 180, 4)
    body = prism_x("cartridge", profile, -WIDTH / 2, WIDTH / 2, mats["case"])
    bevel(body, 1.0)

    # The notches in its sides, and the label's recess between the side bands.
    for side in (-1, 1):
        boolean(body, box("notch", side * (WIDTH / 2 - 2.6), side * (WIDTH / 2 + 5), -20, 20, 16.0, 26.0, mats["case"]))
    half, bottom, depth = RECESS
    boolean(body, box("recess", -half, half, FRONT - 5, FRONT + depth, bottom, HEIGHT + 5, mats["case"]))

    # The connector's gold edge, just showing under the shell.
    pcb = box("pcb", -46.0, 46.0, -2.5, 2.5, -1.2, 1.0, mats["pcb"])

    # The label, just in front of the recess's floor.
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    z_of = lambda row: LABEL_BOTTOM + (500 - row) / LABEL_PX
    if whole_label:
        faces_from_grid(bm, uv, [0, 600], lambda x: (500, 0), z_of, lambda x, row: (x / 600, (500 - row) / 500), 0)
        label = new_object("label", bm, mats["label"])
    else:
        columns = [k * 25 for k in range(25)]
        faces_from_grid(bm, uv, columns, lambda x: (500, border_top(x)), z_of,
                        lambda x, row: (x / 600, (500 - row) / (500 - BAND_TOP)), 1)
        faces_from_grid(bm, uv, columns, lambda x: (border_top(x), 0), z_of,
                        lambda x, row: (x / 600, (WINDOW_BOTTOM - row) / WINDOW_BOTTOM), 0)
        mesh = bpy.data.meshes.new("label")
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(mats["cover"])
        mesh.materials.append(mats["band"])
        label = bpy.data.objects.new("label", mesh)
        bpy.context.scene.collection.objects.link(label)

    cart = join([body, pcb, label], "cartridge")
    for p in cart.data.polygons:
        p.use_smooth = True
    cart.data.set_sharp_from_angle(angle=math.radians(35))
    return cart


def triangles(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.polygons)


def export(objects, out, animations=False):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=out, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
        export_extras=True, export_animations=animations, export_image_format="AUTO", export_cameras=False,
        export_lights=False)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    band = bpy.data.images.load(os.path.join(images, "megadrive_band.png"))

    mats = {
        "case": material("case", "#18181B", 0.45),
        "cover": material("cover", "#FFFFFF", 0.4, aspect=round(600 / WINDOW_BOTTOM, 4)),
        "band": material("band", "#FFFFFF", 0.4, band),
        "pcb": material("pcb", "#B8924A", 0.35),
    }
    cart = build(mats, whole_label=False)

    # The spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    mesh = cart.data
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    print(f"Mega Drive cartridge: {triangles(mesh)} triangles, {len(mesh.materials)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm")
    export([cart], out)


if __name__ == "__main__":
    main()
