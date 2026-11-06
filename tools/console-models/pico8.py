"""The console theme's PICO-8 system model (godot/themes/console/models/systems/pico8.glb): the sparkle of PICO-8's
logo in voxels.

PICO-8 is a fantasy console with no hardware, so its card is its emblem made solid (pico8_layout.py): the sparkle of
its logo, a cube a pixel, one deep. Only the faces with nothing beside them are made, each in one colour of PICO-8's
palette by the way it faces (the front and back the pixel's, the top and bottom its first shade, the sides its second),
as the owner's reference image, a voxel render of the sparkle, shades them. The colours are one texture, the palette
(a block a colour, made here), each face's corners at its colour's middle: one material for nine colours and their
shades.

A node tree: a root (the emblem cards' turn to a three-quarter view, emblems.py's TILT_YAW and TILT_PITCH: the right
side towards the viewer, the top tipped a little; then the model spec's fit: standing on y = 0, centred, the largest
side 1 m) holding the sparkle, its origin on its upright axis at its foot.

The `focused` clip (4 s, looping) turns it steadily once round that axis, so the loop has no seam.

One material and one texture, within the system model budget. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/pico8.py -- godot/themes/console/models/systems/pico8.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pico8_layout as L  # noqa: E402
from clip import Pose, key  # noqa: E402
from emblems import TILT_PITCH, TILT_YAW  # noqa: E402
from mega_drive_cartridge import export, material, new_object, triangles  # noqa: E402

ROUGHNESS = 0.5

# A cube's faces: the neighbour (rows down, columns right) that covers it, if any; the colour it takes (0 the pixel's,
# 1 its top's shade, 2 its sides'); and its corners as steps along x, y and z from the cube's front bottom left, wound
# to face out.
FACES = [(None, 0, ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),        # front
         (None, 0, ((1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1))),        # back
         ((-1, 0), 1, ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),     # top
         ((1, 0), 1, ((0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0))),      # bottom
         ((0, 1), 2, ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),      # right
         ((0, -1), 2, ((0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)))]     # left


def palette():
    """PICO-8's palette as an image, a block a colour; packed, so the export writes its pixels as they are."""
    colours = [tuple(int(c[k:k + 2], 16) / 255 for k in (1, 3, 5)) + (1.0,) for c in L.PALETTE.values()]
    w, h = L.COLUMNS * L.BLOCK, len(colours) // L.COLUMNS * L.BLOCK
    image = bpy.data.images.new("pico8_palette", w, h)
    pixels = []
    for y in range(h - 1, -1, -1):                     # Blender's rows go up from the bottom
        for x in range(w):
            pixels += colours[y // L.BLOCK * L.COLUMNS + x // L.BLOCK]
    image.pixels = pixels
    image.pack()
    return image


def sparkle(mat):
    """The sparkle, its front facing -y, its origin on its upright axis at its foot: a cube a pixel, only the faces
    with nothing beside them, each at its colour's middle in the palette."""
    pixels = {(r, c): int(ch, 16) for r, row in enumerate(L.SPARKLE) for c, ch in enumerate(row) if ch != "."}
    rows, columns, v = len(L.SPARKLE), len(L.SPARKLE[0]), L.VOXEL
    order = list(L.PALETTE)
    blocks_down = len(order) // L.COLUMNS
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    for (r, c), colour in pixels.items():
        x0, y0, z0 = (c - columns / 2) * v, -v / 2, (rows - 1 - r) * v
        for beside, shade, corners in FACES:
            if beside and (r + beside[0], c + beside[1]) in pixels:
                continue
            block = order.index(L.SHADES[colour][shade - 1] if shade else colour)
            at = ((block % L.COLUMNS + 0.5) / L.COLUMNS, 1 - (block // L.COLUMNS + 0.5) / blocks_down)
            face = bm.faces.new([bm.verts.new((x0 + a * v, y0 + b * v, z0 + d * v)) for a, b, d in corners])
            for loop in face.loops:
                loop[uv].uv = at
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=v / 100)
    return new_object("pico8", bm, mat)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def timeline(f):
    return {"pico8": Pose(spin=360.0 * f / L.LENGTH)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    image = palette()
    logo = sparkle(material("voxels", "#FFFFFF", ROUGHNESS, image))

    root = bpy.data.objects.new("pico8_root", None)
    scene.collection.objects.link(root)
    logo.parent = root
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in logo.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", {"pico8": logo}, timeline, L.LENGTH)
    print(f"PICO-8: {triangles(logo.data)} triangles, {len(logo.data.materials)} material, one {image.size[0]} x "
          f"{image.size[1]} texture, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root, logo], out, animations=True)


if __name__ == "__main__":
    main()
