"""The console theme's Sega Game Gear system model (godot/themes/console/models/systems/gamegear.glb).

Built in Blender from the real handheld's proportions (210 x 113 x 38 mm): a body with rounded ends and rounded front
and back edges, the raised face round the screen, the black screen panel, the grey screen frame and LCD, the D-pad,
START and the 1 and 2 buttons, the cartridge slot and the battery covers. The printing (logos, speaker grille, button
legends) is one texture, drawn by game_gear_print.py and projected onto the front. The model is turned to a
three-quarter view (TILT_YAW, TILT_PITCH: the D-pad end towards the viewer and the face tipped up, as the handheld
looks lying in front of you), then fitted to the model spec (A7): standing on y = 0, centred, the largest side 1 m.

Seven materials (case, print, panel, frame, screen, buttons, start) and one 2048 x 1024 texture, within the system
model budget. Run from the repo root:

    python tools/console-models/game_gear_print.py artifacts/gamegear_print.png
    blender -b --factory-startup --python tools/console-models/game_gear.py -- artifacts/gamegear_print.png godot/themes/console/models/systems/gamegear.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

TILT_YAW = 30.0    # degrees about the vertical: the D-pad end comes towards the viewer
TILT_PITCH = 16.0  # degrees about the horizontal: the face tips up, showing the lower edge

WIDTH, HEIGHT, DEPTH = 210.0, 113.0, 38.0
FRONT = -DEPTH / 2  # Blender's front is -Y
PANEL_CORNERS = [(56, 29), (65, 102.5), (-65, 102.5), (-56, 29)]  # as in game_gear_print.py


def srgb(hex_colour):
    """A #RRGGBB sRGB colour as Blender's linear RGBA."""
    def linear(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(linear(int(hex_colour[i:i + 2], 16)) for i in (1, 3, 5)) + (1.0,)


def rounded_polygon(corners, radii, inset=0.0, segments=10):
    """
    A convex polygon's outline (anticlockwise corners as seen from the front, (x, height) in mm) with each corner
    rounded by its radius, moved in by inset (the radii shrink with it). Every call gives the same number of points
    for the same corners, so outlines at several insets can be joined into rings.
    """
    n = len(corners)
    lines = []
    for i in range(n):
        (ax, av), (bx, bv) = corners[i], corners[(i + 1) % n]
        dx, dv = bx - ax, bv - av
        length = math.hypot(dx, dv)
        nx, nv = -dv / length, dx / length  # the inward normal of an anticlockwise edge
        lines.append(((ax + nx * inset, av + nv * inset), (dx / length, dv / length)))

    def meet(l1, l2):
        (p, d), (q, e) = l1, l2
        det = d[0] * -e[1] - d[1] * -e[0]
        t = ((q[0] - p[0]) * -e[1] - (q[1] - p[1]) * -e[0]) / det
        return p[0] + d[0] * t, p[1] + d[1] * t

    moved = [meet(lines[i - 1], lines[i]) for i in range(n)]
    points = []
    for i in range(n):
        cx, cv = moved[i]
        ax, av = moved[i - 1]
        bx, bv = moved[(i + 1) % n]
        ux, uv = ax - cx, av - cv
        wx, wv = bx - cx, bv - cv
        lu, lw = math.hypot(ux, uv), math.hypot(wx, wv)
        ux, uv, wx, wv = ux / lu, uv / lu, wx / lw, wv / lw
        half = math.acos(max(-1.0, min(1.0, ux * wx + uv * wv))) / 2
        r = max(radii[i] - inset, 0.05)
        t = r / math.tan(half)
        sx, sv = ux + wx, uv + wv
        ls = math.hypot(sx, sv)
        ox, ov = cx + sx / ls * r / math.sin(half), cv + sv / ls * r / math.sin(half)
        a1 = math.atan2(cv + uv * t - ov, cx + ux * t - ox)
        a2 = math.atan2(cv + wv * t - ov, cx + wx * t - ox)
        while a2 < a1:
            a2 += 2 * math.pi
        for k in range(segments + 1):
            a = a1 + (a2 - a1) * k / segments
            points.append((ox + r * math.cos(a), ov + r * math.sin(a)))
    return points


def rectangle(cx, cv, w, h, r, inset=0.0, segments=6):
    corners = [(cx + w / 2, cv - h / 2), (cx + w / 2, cv + h / 2), (cx - w / 2, cv + h / 2), (cx - w / 2, cv - h / 2)]
    return rounded_polygon(corners, [r] * 4, inset, segments)


def ellipse(cx, cv, rx, rv, degrees=0.0, segments=40):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    points = []
    for k in range(segments):
        a = 2 * math.pi * k / segments
        x, v = rx * math.cos(a), rv * math.sin(a)
        points.append((cx + x * c - v * s, cv + x * s + v * c))
    return points


class Model:
    """One mesh, built from lofts: rings of points joined by quads, closed by caps, each band with its material."""

    def __init__(self, materials):
        self.materials = materials
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def loft(self, rings, bands, caps):
        """
        rings: [(outline, y)], front to back or back to front; bands: a material per gap between rings;
        caps: (first ring's material or None, last ring's material or None).
        """
        verts = [[self.bm.verts.new((x, y, v)) for x, v in outline] for outline, y in rings]
        for k, material in enumerate(bands):
            a, b = verts[k], verts[k + 1]
            for j in range(len(a)):
                self.face([a[j], a[(j + 1) % len(a)], b[(j + 1) % len(b)], b[j]], material)
        if caps[0]:
            self.face(verts[0], caps[0])
        if caps[1]:
            self.face(verts[-1], caps[1])

    def face(self, verts, material):
        face = self.bm.faces.new(verts)
        face.material_index = self.materials.index(material)
        face.smooth = True
        for loop in face.loops:
            x, _, v = loop.vert.co
            loop[self.uv].uv = ((x + WIDTH / 2) / WIDTH, v / HEIGHT)

    def button(self, outline_at, base, height, dome, material, rings=5):
        """A button standing out of the face at depth base: straight sides, then a dome; outline_at(inset) is its rim."""
        stack = [(outline_at(0), base), (outline_at(0), base - height)]
        for k in range(1, rings + 1):
            a = math.pi / 2 * k / rings
            stack.append((outline_at(dome[0] * (1 - math.cos(a))), base - height - dome[1] * math.sin(a)))
        self.loft(stack, [material] * (len(stack) - 1), (material, material))


def build(model):
    # The body: the front outline, with its front edges rounded over (an elliptical quarter, so the face stays large)
    # and its back edges a little less.
    body_corners = [(WIDTH / 2, 0), (WIDTH / 2, HEIGHT), (-WIDTH / 2, HEIGHT), (-WIDTH / 2, 0)]
    body_radii = [38, 22, 22, 38]
    front_in, front_depth, back_in, back_depth = 6.5, 11.0, 5.0, 7.0
    rings = []
    for k in range(9):
        a = math.pi / 2 * (1 - k / 8)
        rings.append((rounded_polygon(body_corners, body_radii, front_in * (1 - math.cos(a)), 12),
                      FRONT + front_depth * (1 - math.sin(a))))
    for k in range(7):
        a = math.pi / 2 * k / 6
        rings.append((rounded_polygon(body_corners, body_radii, back_in * (1 - math.cos(a)), 12),
                      -FRONT - back_depth * (1 - math.sin(a))))
    model.loft(rings, ["case"] * (len(rings) - 1), ("print", "case"))

    # The raised face round the screen panel, with a chamfered edge; its top is printed (the panel shows through).
    face_corners = [(59.5, 25.8), (68.4, 105.6), (-68.4, 105.6), (-59.5, 25.8)]
    face_radii = [21, 8, 8, 21]
    model.loft([(rounded_polygon(face_corners, face_radii, 0, 10), FRONT + 1.0),
                (rounded_polygon(face_corners, face_radii, 0, 10), FRONT - 1.0),
                (rounded_polygon(face_corners, face_radii, 0.9, 10), FRONT - 1.7)],
               ["case", "case"], ("case", "print"))

    # The glossy black panel on it, and the screen: a grey frame bevelled down to the LCD.
    panel = lambda inset: rounded_polygon(PANEL_CORNERS, [18, 5, 5, 18], inset, 12)
    model.loft([(panel(0), FRONT - 1.5), (panel(0), FRONT - 1.9), (panel(0.3), FRONT - 2.05)],
               ["panel", "panel"], ("panel", "panel"))
    model.loft([(rectangle(0, 71.8, 77.5, 58.8, 3.5), FRONT - 1.9),
                (rectangle(0, 71.8, 77.5, 58.8, 3.5), FRONT - 2.75),
                (rectangle(0, 71.8, 77.5, 58.8, 3.5, 3.4), FRONT - 2.75),
                (rectangle(0, 71.8, 77.5, 58.8, 3.5, 4.6), FRONT - 2.15)],
               ["frame", "frame", "frame"], ("frame", "screen"))

    # The D-pad: a disc with a cross on it.
    base = FRONT + 0.5
    model.button(lambda i: ellipse(-79.3, 77.3, 11.4 - i, 11.4 - i), base, 2.6, (2.0, 0.9), "buttons")
    for w, h in ((19.5, 6.6), (6.6, 19.5)):
        model.loft([(rectangle(-79.3, 77.3, w, h, 1.4), FRONT - 2.4),
                    (rectangle(-79.3, 77.3, w, h, 1.4), FRONT - 3.4),
                    (rectangle(-79.3, 77.3, w, h, 1.4, 0.6), FRONT - 3.9)],
                   ["buttons", "buttons"], ("buttons", "buttons"))

    # START (a blue drop), then 1 and 2.
    model.button(lambda i: ellipse(72.7, 76.1, 3.7 - i, 4.9 - i, 28, 32), base, 2.3, (2.2, 1.2), "start")
    for x, v in ((68.1, 48.9), (85.8, 59.2)):
        model.button(lambda i, x=x, v=v: ellipse(x, v, 6.4 - i, 6.4 - i, 0, 32), base, 2.6, (3.2, 1.6), "buttons")

    # The battery covers on the back.
    for x in (-71.0, 71.0):
        cover = lambda inset, x=x: rectangle(x, 50, 40, 62, 3, inset)
        model.loft([(cover(0), -FRONT - 0.5), (cover(0), -FRONT + 0.4), (cover(0.5), -FRONT + 0.6)],
                   ["case", "case"], ("case", "case"))


def cartridge_slot(model):
    """The cartridge slot along the top, near the back: a dark strip just above the top (one face, facing up)."""
    top = [model.bm.verts.new((x, y, HEIGHT + 0.12)) for x, y in rectangle(0, 5.0, 68, 7, 1.5)]
    model.face(top, "buttons")


def material(name, colour, roughness, image=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(colour)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    if image is not None:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Linear"
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    print_png, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    image = bpy.data.images.load(print_png)

    materials = {
        "case": material("case", "#2F3034", 0.5),
        "print": material("print", "#FFFFFF", 0.5, image),
        "panel": material("panel", "#FFFFFF", 0.15, image),
        "frame": material("frame", "#6C6E72", 0.35),
        "screen": material("screen", "#3E4441", 0.08),
        "buttons": material("buttons", "#1B1B1E", 0.3),
        "start": material("start", "#2F64D6", 0.3),
    }
    names = list(materials)
    model = Model(names)
    build(model)
    bmesh.ops.recalc_face_normals(model.bm, faces=model.bm.faces)
    cartridge_slot(model)  # an open face: wound to face up, so after the closed parts' normals are made outward

    mesh = bpy.data.meshes.new("gamegear")
    model.bm.to_mesh(mesh)
    model.bm.free()
    for name in names:
        mesh.materials.append(materials[name])

    # The three-quarter view, then the spec's fit: on y = 0 (Blender's z), centred, the largest side 1 m.
    tilt = Matrix.Rotation(math.radians(TILT_YAW), 4, "Z") @ Matrix.Rotation(math.radians(-TILT_PITCH), 4, "X")
    mesh.transform(tilt)
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    size = hi - lo
    mesh.transform(Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    mesh.set_sharp_from_angle(angle=math.radians(35))

    obj = bpy.data.objects.new("gamegear", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    triangles = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print(f"Game Gear: {triangles} triangles, {len(names)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")

    bpy.ops.export_scene.gltf(
        filepath=out, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
        export_extras=False, export_animations=False, export_image_format="AUTO", export_cameras=False,
        export_lights=False)


if __name__ == "__main__":
    main()
