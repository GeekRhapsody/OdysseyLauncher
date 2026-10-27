"""The pieces the console theme's later cards share (sufami.py, supergrafx.py, sg1000.py and those after them): an
atlas's UVs, the materials, a part's smoothing, and the node tree's fit, clip and export. Blender's Python.

A card is a node tree: a root (the turn to a three-quarter view, then the model spec's fit: standing on y = 0, centred,
the largest side 1 m) holding the set (the parts that never move, joined into one) and the moving parts, each its own
node at its place in the set (or in another moving part, which it rides). The fit is the launcher's: every vertex of the
rest pose, frame 0 of the `focused` clip, a part shrunk to nothing included (as a point at its origin), so the card's
largest side comes out at 1 m.
"""

import math

import bpy
from mathutils import Matrix, Vector

from amiga import paint
from clip import key
from mega_drive_cartridge import export, material, triangles


class Atlas:
    """A texture's layout: its size, its regions ((x, y, width, height) in pixels) and its swatches (each a block's
    middle, (x, y) in pixels)."""

    def __init__(self, size, regions, swatches=None):
        self.size, self.regions, self.swatches = size, regions, swatches or {}

    def uv(self, region, w, h):
        """A face drawn w x h into a region: (a, b) across it (a to the right, b down from its top) to UVs."""
        rx, ry, rw, rh = self.regions[region]
        return lambda a, b: ((rx + a / w * rw) / self.size, 1 - (ry + b / h * rh) / self.size)

    def swatch(self, name):
        x, y = self.swatches[name]
        return lambda co: (x / self.size, 1 - y / self.size)


def coloured(obj, mat, atlas, name):
    """Every face of obj in mat, at the atlas's swatch `name`."""
    paint(obj, mat, atlas.swatch(name), lambda c, n, kind: True)
    return obj


def curve(points, n=6):
    """A smooth path through points (a Catmull-Rom spline, n steps a span), for a cable to follow."""
    p = [Vector(points[0])] + [Vector(q) for q in points] + [Vector(points[-1])]
    out = []
    for i in range(1, len(p) - 2):
        a, b, c, d = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t ** 3))
    out.append(p[-2])
    return [tuple(q) for q in out]


def smoothed(obj, angle=35.0):
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


def materials(colours, roughness, textures=None):
    """The card's materials, by name: each its colour and roughness, and its texture if textures has one."""
    textures = textures or {}
    return {n: material(n, colours[n], r, textures.get(n)) for n, r in roughness.items()}


def finish(name, whole, parts, timeline, length, yaw, pitch, out, label):
    """Builds the card's node tree, keys its `focused` clip and exports it. whole: the set. parts: {name: (object,
    place)} or {name: (object, place, holder)}, each moving part, its origin where it moves from, placed in the set
    (or in the holder, another of the parts). timeline(f) gives the parts' poses over length frames. The root turns the
    card to the three-quarter view (yaw degrees about the vertical, then pitch about the horizontal) and fits its rest
    pose."""
    scene = bpy.context.scene
    root = bpy.data.objects.new(name + "_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    nodes = {}
    for part, spec in parts.items():
        obj, where = spec[0], spec[1]
        obj.parent = parts[spec[2]][0] if len(spec) > 2 else whole
        obj.location = where
        nodes[part] = obj
    key("focused", nodes, timeline, length)
    bpy.context.view_layer.update()

    tilt = Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    meshes = [whole] + list(nodes.values())
    points = [tilt @ (o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt
    textures = {node.image.name for o in meshes for mat in o.data.materials if mat.node_tree
                for node in mat.node_tree.nodes if node.type == "TEX_IMAGE" and node.image}
    print(f"{label}: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, {len(textures)} textures, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)
