"""The console theme's PlayStation Portable system model (godot/themes/console/models/systems/psp.glb).

Built in Blender from the real handheld's proportions (psp_layout.py has the measurements, taken from photographs): a
piano-black PSP-1000. The body is its front outline (each end one broad arc) lofted back: the front's edge rounded a
little, the back's a lot, and a silver band round the middle of its depth, the clear grey shoulder buttons taking its
place at the top corners. On the front stand the D-pad's four buttons, the analogue nub, the four face buttons and the
row along the bottom (HOME, the volume, the display and sound buttons, SELECT and START); on the top the IR window and
the USB port, on the ends the WLAN and POWER switches, under the right end the yellow DC IN plug. The printing (the
face, the switched-off screen, the legends, the speaker's dots, the buttons' tops, and the back with the UMD bay under
its door) is one 1024 x 1024 texture, drawn by psp_print.py and projected onto the front and the back; the screens,
the UMD and the door's outside are a second.

It's a small node tree: a root (the three-quarter view and the model spec's fit) holding the console, and the console
holding the UMD door (hinged along its bottom edge, on the back), the door holding the UMD (Odyssey, a made-up game),
and the two screens switched on, the XMB and the game's title screen. At rest the UMD and the screens are shrunk to
nothing inside the console, so it stands with its screen off and its door shut, and the rest pose's bounds are the
console's and its door's. The `focused` clip (7 s, looping) plays a game: the console hops round to show its back, the
door springs open, the UMD rolls in on its edge like a wheel, rocks to a stop and slides down into the door, which
snaps shut; the console hops round to the front again, the XMB comes on with the game at the top of its list, then the
game's title screen, and the screen goes off.

The model is turned to a three-quarter view (TILT: its left end towards the viewer and its face tipped up, as the
handheld looks lying in front of you), then fitted to the model spec (A7): standing on y = 0, centred, the largest side
1 m. The turn and the fit are the root's transform, so the clip moves its parts in millimetres.

Eight materials and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/psp_print.py artifacts/psp
    blender -b --factory-startup --python tools/console-models/psp.py -- artifacts/psp godot/themes/console/models/systems/psp.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psp_layout as L  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, hop, key, phase, smooth, wobble  # noqa: E402
from game_gear import ellipse, rounded_polygon  # noqa: E402
from mega_drive_cartridge import export, material, triangles  # noqa: E402

TILT = (20.0, 10.0)       # degrees: yaw (left end nearer), pitch (face up)
FPS = 30
LENGTH = 210              # the focused clip's frames
MATERIALS = ["case", "print", "rear", "buttons", "silver", "shoulder", "media", "umd"]  # never a media slot's name (A7)
ROUGHNESS = dict(case=0.45, print=0.45, rear=0.6, buttons=0.45, silver=0.3, shoulder=0.3, media=0.45, umd=0.5)
OPEN = 42.0               # degrees the UMD door opens


# ---- Geometry --------------------------------------------------------------------------------------------------------

def at(outline, y):
    """An (x, z) outline at depth y."""
    return [(x, y, z) for x, z in outline]


def region_uv(regions, name, mirror=False):
    """The planar projection of a point (x, z in millimetres) into the atlas region name; mirror for a face seen from
    behind (+y)."""
    x, y, w, h = regions[name]["px"]
    x0, x1, z0, z1 = regions[name]["mm"]

    def uv(co):
        cx = -co.x if mirror else co.x
        return ((x + (cx - x0) / (x1 - x0) * w) / L.ATLAS, 1 - (y + (z1 - co.z) / (z1 - z0) * h) / L.ATLAS)
    return uv


def swatch(name):
    """Every point to the middle of one of the print atlas's swatches: a small part's plain colour."""
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


class Model:
    """One mesh, built from lofts: rings of points joined by quads, closed by caps."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def face(self, verts, mat, smooth=False, uv=None):
        face = self.bm.faces.new(verts)
        face.material_index = MATERIALS.index(mat)
        face.smooth = smooth  # caps are flat, so their big polygons shade evenly
        if uv is not None:
            for loop in face.loops:
                loop[self.uv].uv = uv(loop.vert.co)
        return face

    def loft(self, rings, bands, caps, uvs=(None, None), band_uv=None):
        """rings: lists of points; bands: per gap between rings, a material or a function of a quad's middle (x, z)
        giving one; caps: (first ring's, last ring's) or None."""
        verts = [[self.bm.verts.new(p) for p in ring] for ring in rings]
        for k, mat in enumerate(bands):
            a, b = verts[k], verts[k + 1]
            for j in range(len(a)):
                quad = [a[j], a[(j + 1) % len(a)], b[(j + 1) % len(b)], b[j]]
                m = mat
                if callable(mat):
                    m = mat(sum(v.co.x for v in quad) / 4, sum(v.co.z for v in quad) / 4)
                self.face(quad, m, smooth=True, uv=band_uv)
        if caps[0]:
            self.face(verts[0], caps[0], uv=uvs[0])
        if caps[1]:
            self.face(verts[-1], caps[1], uv=uvs[1])

    def slab(self, outline_at, front, back, front_round, back_round, side, caps, uvs=(None, None), steps=5):
        """A solid from front to back whose front and back edges are rounded over: outline_at(inset) is its outline,
        front_round and back_round (inset, depth) the roundings."""
        rings = []
        for k in range(steps + 1):
            a = math.pi / 2 * (1 - k / steps)
            rings.append(at(outline_at(front_round[0] * (1 - math.cos(a))), front + front_round[1] * (1 - math.sin(a))))
        for k in range(steps + 1):
            a = math.pi / 2 * k / steps
            rings.append(at(outline_at(back_round[0] * (1 - math.cos(a))), back - back_round[1] * (1 - math.sin(a))))
        self.loft(rings, [side] * (len(rings) - 1), caps, uvs)

    def button(self, outline_at, front, height, dome, side, top, uv, rings=4):
        """A button standing out of the face at depth front: straight sides, then a dome; outline_at(inset) is its rim.
        Its top is the material top, projected through uv."""
        stack = [at(outline_at(0), front + 0.6), at(outline_at(0), front - height)]
        for k in range(1, rings + 1):
            a = math.pi / 2 * k / rings
            stack.append(at(outline_at(dome[0] * (1 - math.cos(a))), front - height - dome[1] * math.sin(a)))
        self.loft(stack, [side] * (len(stack) - 1), (side, top), (None, uv))

    def block(self, x0, x1, y0, y1, z0, z1, mat, uv=None):
        outline = [(x1, z0), (x1, z1), (x0, z1), (x0, z0)]
        self.loft([at(outline, y0), at(outline, y1)], [mat], (mat, mat), (uv, uv), band_uv=uv)

    def finish(self, name, mats, outward=True):
        """The mesh object: normals outward (for closed solids), edges sharper than 35 degrees sharp."""
        bm = self.bm
        if outward:
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


def band_material(x, z):
    """The silver band, or a shoulder button at the top corners."""
    return "shoulder" if abs(x) > L.SHOULDER["x"] and z > L.SHOULDER["z"] else "silver"


def body(model):
    """The body: the front's edge rounded over, the silver band standing a quarter millimetre proud round the middle,
    the back's edge rounded over a lot."""
    rings, bands = [], []
    fi, fd = L.FRONT_ROUND
    bi, bd = L.BACK_ROUND
    steps = 5
    for k in range(steps + 1):
        a = math.pi / 2 * (1 - k / steps)
        rings.append(at(L.body_outline(fi * (1 - math.cos(a))), L.FRONT + fd * (1 - math.sin(a))))
    b0, b1 = L.BAND
    rings += [at(L.body_outline(0), b0 - 0.2), at(L.body_outline(-0.25), b0), at(L.body_outline(-0.25), b1),
              at(L.body_outline(0), b1 + 0.2)]
    for k in range(steps + 1):
        a = math.pi / 2 * k / steps
        rings.append(at(L.body_outline(bi * (1 - math.cos(a))), L.BACK - bd * (1 - math.sin(a))))
    bands = ["case"] * (steps + 1) + [band_material] * 3 + ["case"] * (steps + 1)
    model.loft(rings, bands, ("print", "rear"),
               (region_uv(L.PRINT_REGIONS, "front"), region_uv(L.PRINT_REGIONS, "rear", mirror=True)))


def controls(model):
    front, uv = L.FRONT, region_uv(L.PRINT_REGIONS, "front")
    cx, cz = L.DPAD["x"], L.DPAD["z"]
    for _, a in L.DPAD_BUTTONS:
        corners, radii = L.pentagon(cx, cz, a)
        model.button(lambda i, c=corners, r=radii: rounded_polygon(c, r, i, 6), front, 1.3, (0.8, 0.5), "buttons",
                     "print", uv)
    r = L.FACE["radius"]
    for _, x, z in L.face_centres():
        model.button(lambda i, x=x, z=z: ellipse(x, z, r - i, r - i, 0, 32), front, 1.4, (1.4, 0.6), "buttons",
                     "print", uv)
    x, z, r = L.NUB["x"], L.NUB["z"], L.NUB["radius"]
    model.button(lambda i: ellipse(x, z, r - i, r - i, 0, 32), front, 1.6, (1.0, 0.25), "buttons", "print", uv,
                 rings=3)
    for _, x, shape in L.ROW:
        if shape == "shield":
            corners, radii = L.shield(x, L.ROW_Z)
            outline = lambda i, c=corners, r=radii: rounded_polygon(c, r, i, 5)
        else:
            outline = lambda i, x=x: ellipse(x, L.ROW_Z, 2.9 - i, 2.4 - i, 0, 24)
        model.button(outline, front, 0.6, (0.5, 0.3), "buttons", "print", uv, rings=3)


def edges(model):
    """What stands on the top, the ends and the bottom: the IR window and the USB port; the WLAN and POWER switches;
    the DC IN plug, yellow."""
    top = L.HEIGHT + 0.25
    model.block(-48.8, -36.5, -3.0, 4.2, top - 0.6, top + 0.35, "buttons")
    model.block(-4.0, 4.0, -1.4, 3.0, top - 0.6, top + 0.3, "buttons")
    end = L.WIDTH / 2 + 0.25
    model.block(-end - 0.6, -end + 0.6, -1.8, 3.2, 27.0, 33.0, "buttons")
    model.block(end - 0.6, end + 0.6, -1.8, 3.2, 17.0, 26.0, "buttons")
    model.block(62.0, 68.0, -3.4, 1.6, -0.55, 0.6, "print", swatch("yellow"))


def door(mats):
    """The UMD door, its origin on its hinge (its outside's bottom edge): a panel standing proud of the back, its
    outside the media atlas's door, its inside dark."""
    (x0, x1), (z0, z1) = L.DOOR["x"], L.DOOR["z"]
    corners = [(x1, z0), (x1, z1), (x0, z1), (x0, z0)]
    outline = lambda i: rounded_polygon(corners, [2.0, 4.0, 4.0, 2.0], i, 6)
    model = Model()
    model.slab(outline, L.BACK + L.DOOR["inner"], L.BACK + L.DOOR["out"], (0.3, 0.3), (1.0, 0.8), "case",
               ("buttons", "media"), (None, region_uv(L.MEDIA_REGIONS, "door", mirror=True)), steps=4)
    hinge = Vector((0.0, L.BACK + L.DOOR["out"], z0))
    for v in model.bm.verts:
        v.co -= hinge
    return model.finish("umd_door", mats), hinge


def umd(mats):
    """The UMD, its disc's middle at its origin, its label facing +y (the console's back), as it goes in."""
    t = L.UMD["thickness"]
    model = Model()
    model.slab(L.umd_outline, -t / 2, t / 2, (0.5, 0.5), (0.5, 0.5), "umd", ("media", "media"),
               (region_uv(L.MEDIA_REGIONS, "umd_rear"), region_uv(L.MEDIA_REGIONS, "umd", mirror=True)), steps=3)
    return model.finish("umd", mats)


def quad(mats, name):
    """A flat face facing the front, showing the media region name (a screen switched on), its middle at its origin."""
    model = Model()
    x0, x1, z0, z1 = L.MEDIA_REGIONS[name]["mm"]
    verts = [model.bm.verts.new(p) for p in ((x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1))]  # wound to face -y
    model.face(verts, "media", uv=region_uv(L.MEDIA_REGIONS, name))
    return model.finish(name, mats, outward=False)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    """A part popping in from nothing between f0 and f1."""
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def flat(v):
    """A screen squeezed to v of its height (switching on or off)."""
    return Pose(axes=(1.0, 1.0, max(HIDDEN, v)))


def timeline(f, c):
    hover, start = c["hover"], c["start"]

    # The console: a hop round to its back, a squash as the door snaps shut, a hop round to its front.
    if f < 8:
        console = Pose()
    elif f < 36:
        console = Pose(z=hop(f, 8, 32, 12.0), spin=180 * back_out(phase(f, 8, 32), 1.3))
    elif f < 104:
        console = Pose(spin=180, squash=wobble(f, 100, 0.06, 8, 5))
    elif f < 134:
        console = Pose(z=hop(f, 104, 128, 12.0), spin=180 + 180 * back_out(phase(f, 104, 128), 1.3),
                       squash=wobble(f, 100, 0.06, 8, 5))
    else:
        console = Pose(spin=360, squash=wobble(f, 128, 0.05, 8, 5))

    # The door: springs open, waits for the UMD, snaps shut.
    if f < 36 or f >= 100:
        lid = Pose()
    elif f < 48:
        lid = Pose(pitch=-OPEN * back_out(phase(f, 36, 48), 1.8))
    elif f < 92:
        lid = Pose(pitch=-OPEN)
    else:
        lid = Pose(pitch=-OPEN * (1 - ease_in(phase(f, 92, 100))))

    # The UMD, in the door's frame: it rolls in from the viewer's right like a wheel (two turns, anticlockwise as the
    # viewer sees it), rocks to a stop upright over the door, and slides down into it; once the door is shut it's
    # inside the console, and goes.
    if f == 0 or f >= 101:
        disc = Pose(scale=HIDDEN)  # in its seat, so the rest pose's bounds are the console's
    elif f < 44:
        disc = Pose(x=start, z=hover, scale=HIDDEN)
    elif f < 74:
        t = ease_out(phase(f, 44, 74))
        disc = Pose(x=start * (1 - t), z=hover + hop(f, 44, 56, 6.0), roll=720 * t, scale=appear(f, 44, 52))
    elif f < 84:
        disc = Pose(z=hover, roll=wobble(f, 74, -9.0, 10, 4))
    elif f < 92:
        disc = Pose(z=hover * (1 - ease_in(phase(f, 84, 92))))
    else:
        disc = Pose(z=-0.6 * math.sin(math.pi * phase(f, 92, 96)) if f < 96 else 0.0)

    # The screens: the XMB, then the game's title screen zooming in.
    if f < 136 or f >= 172:
        xmb = Pose(scale=HIDDEN)
    elif f < 144:
        xmb = flat(0.02 + 0.98 * ease_out(phase(f, 136, 144)))
    elif f < 166:
        xmb = Pose()
    else:
        xmb = flat(1 - ease_in(phase(f, 166, 172)))
    if f < 170 or f >= 202:
        game = Pose(scale=HIDDEN)
    elif f < 180:
        game = Pose(scale=max(HIDDEN, back_out(phase(f, 170, 180), 1.6)))
    elif f < 196:
        game = Pose()
    else:
        game = flat(1 - ease_in(phase(f, 196, 202)))
    return {"console": console, "umd_door": lid, "umd": disc, "screen": xmb, "screen_game": game}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    printed = bpy.data.images.load(os.path.join(images, "psp_print.png"))
    media = bpy.data.images.load(os.path.join(images, "psp_media.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", rear="#FFFFFF", media="#FFFFFF")
    textures = dict(print=printed, rear=printed, media=media)
    mats = {n: material(n, colours[n], ROUGHNESS[n], textures.get(n)) for n in MATERIALS}

    model = Model()
    body(model)
    controls(model)
    edges(model)
    console = model.finish("psp", mats)
    lid, hinge = door(mats)
    disc = umd(mats)
    screen = quad(mats, "screen")
    game = quad(mats, "screen_game")

    # The node tree: root (the view and the fit), console, its door holding the UMD, and the screens, at their rest
    # places; the UMD and the screens shrunk to nothing.
    s = L.SCREEN
    screen_at = Vector((s["x"], L.FRONT - 0.25, s["z"]))
    seat = Vector((0.0, L.DOOR["inner"] - L.DOOR["out"] - 0.8 - L.UMD["thickness"] / 2, 1.2 - L.UMD["bottom"]))
    root = bpy.data.objects.new("psp_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    for part, parent, where in ((lid, console, hinge), (screen, console, screen_at),
                                (game, console, screen_at + Vector((0.0, -0.05, 0.0))), (disc, lid, seat)):
        part.parent = parent
        part.location = where
    nodes = {"console": console, "umd_door": lid, "umd": disc, "screen": screen, "screen_game": game}

    # The three-quarter view, then the spec's fit (on y = 0, Blender's z; centred; the largest side 1 m) of the console
    # and its door at rest, as the root's transform.
    yaw, pitch = TILT
    tilt = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
    points = [tilt @ v.co for v in console.data.vertices] + [tilt @ (v.co + hinge) for v in lid.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    fit = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    root.matrix_world = fit @ tilt

    # The UMD's bottom clears the open door's top edge by 3 mm while it hovers; it starts past the console's right end
    # (seen from behind: -x, the door's frame being the console's).
    door_height = L.DOOR["z"][1] - L.DOOR["z"][0]
    context = {"hover": door_height - (seat.z + L.UMD["bottom"]) + 3.0, "start": -100.0}
    key("focused", nodes, lambda f: timeline(f, context), LENGTH)

    meshes = [console, lid, disc, screen, game]
    tris = sum(triangles(o.data) for o in meshes)
    print(f"PSP: {tris} triangles ({triangles(disc.data)} the UMD, {triangles(lid.data)} the door), "
          f"{len(MATERIALS)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


main()
