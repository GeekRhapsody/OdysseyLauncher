"""The console theme's Nintendo Switch system model (godot/themes/console/models/systems/switch.glb).

Built in Blender from the real console's proportions (239 x 102 x 14 mm with its Joy-Con; switch_layout.py has the
measurements): the tablet, its front and back edges rounded, the black glass and its dark grey rim printed on its
front (flush, and no glossier than the rest: a raised glass's edge caught the light, and a glossy one washed out the
screen), with the power and volume buttons, the vent and the game card flap along its top, and a rail down each side;
and the two Joy-Con, neon blue and neon red, their outer corners rounded and their backs rounded over, with their sticks,
the direction buttons, X, Y, A and B, minus, plus, capture and HOME, the L and R buttons round their tops and the ZL and
ZR triggers behind them, and a rail down their inner sides. The printing (the screen's start-up logo, the button
legends, the back's logo, vent and kickstand) is one texture, drawn by switch_print.py and projected onto the front
and the back.

The right Joy-Con is its own node. The `focused` clip (5 s, looping) slides it up its rail (RISE), as when it's taken
off, holds it there, then slides it back down and clicks it home.

The model is turned to a three-quarter view (TILT_YAW, TILT_PITCH: the right Joy-Con's end towards the viewer and the
face tipped back a little, as the console looks held in front of you), then fitted to the model spec (A7): standing on
y = 0, centred, the largest side 1 m. The right Joy-Con's mesh and its clip are turned and scaled the same way.

Six materials (body, print, rear, blue, red, buttons) and one 2048 x 2048 texture, within the system model
budget. Run from the repo root:

    python tools/console-models/switch_print.py artifacts/switch
    blender -b --factory-startup --python tools/console-models/switch.py -- artifacts/switch godot/themes/console/models/systems/switch.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_layout as L  # noqa: E402
from game_gear import ellipse, rectangle, rounded_polygon  # noqa: E402
from mega_drive_cartridge import export, material, triangles  # noqa: E402

TILT_YAW = -24.0   # degrees about the vertical: the right Joy-Con's end comes towards the viewer
TILT_PITCH = 12.0  # degrees about the horizontal: the face tips back

FRONT, BACK = -L.DEPTH / 2, L.DEPTH / 2   # Blender's front is -Y
OUTER = L.WIDTH / 2
INNER = L.TABLET - 1.0                    # the Joy-Con's inner side, 1 mm inside the tablet, so the seam is a fine groove
CORNERS = (17.0, 15.0)                    # the Joy-Con's outer corners' radii: bottom, top
RISE = 60.0                               # how far up its rail the right Joy-Con slides
FPS = 30
# The focused clip's keys: (frame, how far up its rail the right Joy-Con is, in mm).
KEYS = [(0, 0.0), (30, 0.0), (54, RISE), (84, RISE), (104, 0.0), (106, -0.8), (109, 0.0), (150, 0.0)]

MATERIALS = ["body", "print", "rear", "blue", "red", "buttons"]  # never "back": that's a media slot (A7)


def uv(x, z, back):
    """The planar projections of switch_print.png: the front in its top half, the back (mirrored) in its bottom half."""
    u = (x - L.PRINT_X[0]) / (L.PRINT_X[1] - L.PRINT_X[0])
    v = (z - L.PRINT_Z[0]) / (L.PRINT_Z[1] - L.PRINT_Z[0])
    return (1 - u, v / 2) if back else (u, 0.5 + v / 2)


class Model:
    """One mesh, built from lofts: rings of (x, z) outlines along y, joined by quads, closed by caps."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def loft(self, rings, bands, caps):
        """rings: [(outline, y)]; bands: a material per gap between rings; caps: (first ring's, last ring's) or None."""
        verts = [[self.bm.verts.new((x, y, z)) for x, z in outline] for outline, y in rings]
        for k, mat in enumerate(bands):
            a, b = verts[k], verts[k + 1]
            for j in range(len(a)):
                self.face([a[j], a[(j + 1) % len(a)], b[(j + 1) % len(b)], b[j]], mat, smooth=True)
        if caps[0]:
            self.face(verts[0], caps[0])
        if caps[1]:
            self.face(verts[-1], caps[1])

    def face(self, verts, mat, smooth=False):
        face = self.bm.faces.new(verts)
        face.material_index = MATERIALS.index(mat)
        face.smooth = smooth  # caps are flat, so their big polygons shade evenly
        for loop in face.loops:
            x, _, z = loop.vert.co
            loop[self.uv].uv = uv(x, z, mat == "rear")

    def block(self, x0, x1, y0, y1, z0, z1, mat):
        outline = [(x1, z0), (x1, z1), (x0, z1), (x0, z0)]
        self.loft([(outline, y0), (outline, y1)], [mat], (mat, mat))

    def rounded(self, outline_at, front, back, side, caps):
        """
        A slab from FRONT to BACK whose front and back edges are rounded over: outline_at(inset) is its outline,
        front and back (inset, depth) the roundings. caps: the front's and the back's materials.
        """
        rings = []
        for k in range(6):
            a = math.pi / 2 * (1 - k / 5)
            rings.append((outline_at(front[0] * (1 - math.cos(a))), FRONT + front[1] * (1 - math.sin(a))))
        for k in range(6):
            a = math.pi / 2 * k / 5
            rings.append((outline_at(back[0] * (1 - math.cos(a))), BACK - back[1] * (1 - math.sin(a))))
        self.loft(rings, [side] * (len(rings) - 1), caps)

    def button(self, outline_at, height, dome, top, side="buttons", rings=4):
        """A button standing out of the face: straight sides, then a dome; outline_at(inset) is its rim."""
        stack = [(outline_at(0), FRONT + 0.6), (outline_at(0), FRONT - height)]
        for k in range(1, rings + 1):
            a = math.pi / 2 * k / rings
            stack.append((outline_at(dome[0] * (1 - math.cos(a))), FRONT - height - dome[1] * math.sin(a)))
        self.loft(stack, [side] + [top] * rings, (side, top))


def tablet(model):
    corners = [(L.TABLET, 0), (L.TABLET, L.HEIGHT), (-L.TABLET, L.HEIGHT), (-L.TABLET, 0)]
    model.rounded(lambda i: rounded_polygon(corners, [1.5, 2.5, 2.5, 1.5], i, 6), (0.8, 0.8), (2.0, 2.6), "body",
                  ("print", "rear"))

    # Along the top: the power button and the volume buttons, the vent, the game card's flap.
    top = L.HEIGHT
    model.block(-70.5, -64.0, -1.7, 1.7, top - 0.6, top + 0.7, "buttons")
    model.block(-60.0, -53.2, -1.7, 1.7, top - 0.6, top + 0.7, "buttons")
    model.block(-52.4, -45.6, -1.7, 1.7, top - 0.6, top + 0.7, "buttons")
    model.block(-36.0, 22.0, -1.4, 1.4, top - 0.4, top + 0.12, "buttons")
    model.block(47.0, 73.0, -3.2, 3.2, top - 0.4, top + 0.25, "body")

    # The rails down its sides, hidden by the Joy-Con until one slides up.
    for side in (-1, 1):
        model.block(side * L.TABLET - 0.15, side * L.TABLET + 0.15, -2.6, 2.6, 1.0, top - 1.0, "buttons")


def joycon(model, side):
    """A Joy-Con: side -1 the left (blue), 1 the right (red)."""
    colour = "blue" if side < 0 else "red"
    bottom, top = CORNERS
    if side > 0:
        corners, radii = [(OUTER, 0), (OUTER, L.HEIGHT), (INNER, L.HEIGHT), (INNER, 0)], [bottom, top, 1.0, 1.0]
    else:
        corners, radii = [(-INNER, 0), (-INNER, L.HEIGHT), (-OUTER, L.HEIGHT), (-OUTER, 0)], [1.0, 1.0, top, bottom]
    model.rounded(lambda i: rounded_polygon(corners, radii, i, 12), (1.4, 1.4), (3.6, 4.6), colour, ("print", "rear"))

    # Its rail.
    model.block(side * (INNER - 0.2), side * (INNER + 0.1), -2.4, 2.4, 2.0, L.HEIGHT - 2.0, "buttons")

    # L or R round the top corner, ZL or ZR behind it.
    shoulder(model, side, FRONT + 1.7, -0.6, 0.7, 2.0, -5)
    shoulder(model, side, 0.4, BACK + 3.5, 1.0, 6.5, -15)

    # The stick.
    x, z = L.RIGHT_STICK if side > 0 else L.LEFT_STICK
    profile = [(9.2, 0.5), (9.2, -0.2), (8.7, -1.2), (7.6, -2.0), (5.8, -2.6), (3.4, -2.8), (3.2, -4.4), (6.4, -4.6),
               (7.6, -5.2), (L.STICK_R, -6.0), (L.STICK_R, -8.2), (7.5, -8.8), (6.6, -9.0), (5.0, -8.7), (2.5, -8.45)]
    model.loft([(ellipse(x, z, r, r, 0, 32), FRONT + y) for r, y in profile], ["buttons"] * (len(profile) - 1),
               ("buttons", "buttons"))

    # The four buttons, printed on top; then capture and minus, or HOME and plus.
    r = L.BUTTON_R
    for bx, bz in L.four(L.ABXY if side > 0 else L.DPAD):
        model.button(lambda i, bx=bx, bz=bz: ellipse(bx, bz, r - i, r - i, 0, 24), 1.0, (1.2, 0.7), "print")
    if side < 0:
        x, z = L.CAPTURE
        model.button(lambda i: rectangle(x, z, 6.0, 6.0, 1.2, i, 4), 0.6, (0.4, 0.2), "print")
        x, z = L.MINUS
        model.button(lambda i: rectangle(x, z, 5.4, 1.5, 0.6, i, 3), 0.9, (0.3, 0.2), "buttons")
    else:
        x, z = L.HOME
        model.button(lambda i: ellipse(x, z, L.HOME_R - i, L.HOME_R - i, 0, 24), 0.5, (0.8, 0.4), "print")
        x, z = L.PLUS
        for w, h in ((5.6, 1.6), (1.6, 5.6)):
            model.button(lambda i, w=w, h=h: rectangle(x, z, w, h, 0.6, i, 3), 0.9, (0.3, 0.2), "buttons")


def shoulder(model, side, y0, y1, out, depth, end):
    """
    A shoulder button from y0 to y1: a band along the Joy-Con's top and round its outer top corner (down to the angle
    end, in degrees), standing out by out and reaching depth into the body.
    """
    r = CORNERS[1]
    cx, cz = OUTER - r, L.HEIGHT - r
    angles = [90 + (end - 90) * k / 12 for k in range(13)]
    outer = [(L.TABLET + 1.5, L.HEIGHT + out)] + [(cx + (r + out) * math.cos(math.radians(a)),
                                                   cz + (r + out) * math.sin(math.radians(a))) for a in angles]
    inner = [(cx + (r - depth) * math.cos(math.radians(a)), cz + (r - depth) * math.sin(math.radians(a)))
             for a in reversed(angles)] + [(L.TABLET + 1.5, L.HEIGHT - depth)]
    outline = outer + inner
    if side < 0:
        outline = [(-x, z) for x, z in reversed(outline)]
    model.loft([(outline, y0), (outline, y1)], ["buttons"], ("buttons", "buttons"))


def finish(model, name, mats):
    """The model's mesh: normals outward, edges sharper than 35 degrees sharp, every material in MATERIALS' order."""
    bm = model.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(35):
            e.smooth = False
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for n in MATERIALS:
        mesh.materials.append(mats[n])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    image = bpy.data.images.load(os.path.join(images, "switch_print.png"))
    mats = {
        "body": material("body", "#2D2E32", 0.55),
        "print": material("print", "#FFFFFF", 0.5, image),
        "rear": material("rear", "#FFFFFF", 0.55, image),
        "blue": material("blue", "#00B9E4", 0.5),
        "red": material("red", "#FF4B55", 0.5),
        "buttons": material("buttons", "#232327", 0.35),
    }

    console = Model()
    tablet(console)
    joycon(console, -1)
    right = Model()
    joycon(right, 1)
    console, right = finish(console, "switch", mats), finish(right, "joycon_r", mats)

    # The three-quarter view, then the spec's fit (on y = 0, Blender's z; centred; the largest side 1 m) of the whole
    # console at rest, the right Joy-Con included.
    tilt = Matrix.Rotation(math.radians(TILT_YAW), 4, "Z") @ Matrix.Rotation(math.radians(-TILT_PITCH), 4, "X")
    points = [tilt @ v.co for v in console.data.vertices] + [tilt @ v.co for v in right.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    fit = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    whole = fit @ tilt
    console.data.transform(whole)

    # The right Joy-Con: its mesh about its middle, turned and scaled like the console's, its node moving along the
    # console's up.
    anchor = Vector(((INNER + OUTER) / 2, 0.0, L.HEIGHT / 2))
    right.data.transform(Matrix.Scale(1 / max(size), 4) @ tilt @ Matrix.Translation(-anchor))
    right.animation_data_create()
    for frame, rise in KEYS:
        right.location = whole @ (anchor + Vector((0.0, 0.0, rise)))
        right.keyframe_insert("location", frame=frame)
    right.animation_data.action.name = "focused"
    scene.frame_start, scene.frame_end = KEYS[0][0], KEYS[-1][0]
    scene.frame_set(0)

    tris = triangles(console.data) + triangles(right.data)
    print(f"Switch: {tris} triangles ({triangles(right.data)} the right Joy-Con), {len(MATERIALS)} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([console, right], out, animations=True)


main()
