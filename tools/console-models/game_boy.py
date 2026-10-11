"""The console theme's Game Boy, Game Boy Color and Game Boy Advance system models
(godot/themes/console/models/systems/gb.glb, gbc.glb and gba.glb).

Built in Blender from the real handhelds' proportions (game_boy_layout.py has the measurements): the grey DMG-01 with
its magenta A and B and its volume and contrast wheels, a teal Game Boy Color with its black lens and battery bulge,
and an indigo Game Boy Advance with its grey shoulder buttons. Each body is its front outline lofted back, its front
and back edges rounded over, with the D-pad, the buttons, the power switch, the cartridge slot along the top at the
back and the battery cover; the printing (the screen's surround, the switched-off screen, the legends, the wells, the
speaker) is one 1024 x 1024 texture, drawn by game_boy_print.py and projected onto the front.

Each is a small node tree: a root (the three-quarter view and the model spec's fit) holding the console, and the
console holding its cartridge, its screen switched on and its power light lit, so they ride along when the console
moves. At rest the three children are shrunk to nothing inside the console, so it stands with its screen off and no
cartridge, and the rest pose's bounds are the console's. The `focused` clip (7 s, looping) brings a cartridge in, a
little differently on each:

- Game Boy: the cartridge pops up above the console showing its label, wiggles, turns round, and drops into the slot;
  the console squashes under it and springs back; the battery light comes on and the Nintendo logo scrolls down the
  screen, then the console hops for joy. Then the light goes out and the cartridge jumps out, spins and vanishes.
- Game Boy Color: the cartridge pops up, turns round and drops, but bonks off the top, wobbles, lines itself up and
  slides in with a click; the console shimmies, the light comes on and the screen switches on.
- Game Boy Advance: the cartridge swoops in from the right in a barrel roll, dips into the slot, the console nods,
  the light comes on and the start-up screen zooms in; then the console hops. The cartridge leaves to the left.

The model is turned to a three-quarter view (TILT: its left end towards the viewer and its face tipped up, as the
handhelds look lying in front of you), then fitted to the model spec (A7): standing on y = 0, centred, the largest side
1 m. The turn and the fit are the root's transform, so the clip moves its parts in millimetres.

Five or six materials and one texture each, within the system model budget. Run from the repo root:

    python tools/console-models/game_boy_print.py artifacts/gameboys
    blender -b --factory-startup --python tools/console-models/game_boy.py -- artifacts/gameboys gb godot/themes/console/models/systems/gb.glb

and the same with gbc and gba.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_boy_layout as L  # noqa: E402
from game_gear import ellipse, rectangle, rounded_polygon  # noqa: E402
from mega_drive_cartridge import export, material, triangles  # noqa: E402

TILT = {"gb": (20.0, 10.0), "gbc": (20.0, 10.0), "gba": (24.0, 14.0)}  # degrees: yaw (left end nearer), pitch (face up)
FPS = 30
LENGTH = 210              # the focused clip's frames
HIDDEN = 0.001            # the scale of a part that isn't there
MATERIALS = {             # never "back" or "label": those are media slots (A7)
    "gb": ["case", "print", "dark", "ab", "rubber", "cart"],
    "gbc": ["case", "print", "dark", "rubber", "cart"],
    "gba": ["case", "print", "light", "dark", "cart"],
}
ROUGHNESS = dict(case=0.55, print=0.55, dark=0.4, ab=0.35, rubber=0.7, light=0.45, cart=0.5)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def at(outline, y):
    """An (x, z) outline at depth y."""
    return [(x, y, z) for x, z in outline]


def region_uv(m, name, mirror=False, dz=0.0, grow=0.0):
    """The planar projection of a point (x, z in millimetres) into the atlas region name; mirror for a face seen from
    behind (+y). dz moves the mesh's z back to the region's; grow maps a slightly larger box, so the face samples
    inside its region."""
    x, y, w, h = m["regions"][name]["px"]
    x0, x1, z0, z1 = m["regions"][name]["mm"]
    x0, x1, z0, z1 = x0 - grow, x1 + grow, z0 - grow, z1 + grow

    def uv(co):
        cx = -co.x if mirror else co.x
        return ((x + (cx - x0) / (x1 - x0) * w) / L.ATLAS, 1 - (y + (z1 - co.z - dz) / (z1 - z0) * h) / L.ATLAS)
    return uv


class Model:
    """One mesh, built from lofts: rings of points joined by quads, closed by caps."""

    def __init__(self, names):
        self.names = names
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def face(self, verts, mat, smooth=False, uv=None):
        face = self.bm.faces.new(verts)
        face.material_index = self.names.index(mat)
        face.smooth = smooth  # caps are flat, so their big polygons shade evenly
        if uv is not None:
            for loop in face.loops:
                loop[self.uv].uv = uv(loop.vert.co)
        return face

    def loft(self, rings, bands, caps, uvs=(None, None)):
        """rings: lists of points; bands: a material per gap between rings; caps: (first ring's, last ring's) or None."""
        verts = [[self.bm.verts.new(p) for p in ring] for ring in rings]
        for k, mat in enumerate(bands):
            a, b = verts[k], verts[k + 1]
            for j in range(len(a)):
                self.face([a[j], a[(j + 1) % len(a)], b[(j + 1) % len(b)], b[j]], mat, smooth=True)
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

    def button(self, outline_at, front, height, dome, mat, rings=4):
        """A button standing out of the face: straight sides, then a dome; outline_at(inset) is its rim."""
        stack = [at(outline_at(0), front + 0.6), at(outline_at(0), front - height)]
        for k in range(1, rings + 1):
            a = math.pi / 2 * k / rings
            stack.append(at(outline_at(dome[0] * (1 - math.cos(a))), front - height - dome[1] * math.sin(a)))
        self.loft(stack, [mat] * (len(stack) - 1), (mat, mat))

    def block(self, x0, x1, y0, y1, z0, z1, mat):
        outline = [(x1, z0), (x1, z1), (x0, z1), (x0, z0)]
        self.loft([at(outline, y0), at(outline, y1)], [mat], (mat, mat))

    def wheel(self, x0, x1, y, z, r, mat, segments=24):
        """A thumbwheel standing out of a side: a disc whose axis is along x, from x0 (inside) to x1, its outer edge
        rounded."""
        ring = lambda x, rr: [(x, y + rr * math.cos(2 * math.pi * k / segments), z + rr * math.sin(2 * math.pi * k / segments))
                              for k in range(segments)]
        edge = x1 - math.copysign(0.5, x1 - x0)
        self.loft([ring(x0, r), ring(edge, r), ring(x1, r - 0.5)], [mat, mat], (mat, mat))

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
        for n in self.names:
            mesh.materials.append(mats[n])
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        return obj


def pill(x, z, length, width, degrees, inset):
    """A stadium's outline, turned anticlockwise by degrees about its centre."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [(x + u * c - v * s, z + u * s + v * c) for u, v in rectangle(0, 0, length, width, width * 0.48, inset, 6)]


def body(model, m):
    w, h, d = m["width"], m["height"], m["depth"]
    corners = [(w / 2, 0), (w / 2, h), (-w / 2, h), (-w / 2, 0)]
    model.slab(lambda i: rounded_polygon(corners, m["corners"], i, 12), -d / 2, d / 2, m["front_round"], m["back_round"],
               "case", ("print", "case"), (region_uv(m, "front"), None))


def dpad(model, m, mat):
    x, z, length, width = m["dpad"]
    for w, h in ((length, width), (width, length)):
        model.button(lambda i, w=w, h=h: rectangle(x, z, w, h, 1.2, i, 4), -m["depth"] / 2, 2.4, (0.7, 0.5), mat)


def round_buttons(model, m, mat, height, dome):
    for _, x, z, r in m["buttons"]:
        model.button(lambda i, x=x, z=z, r=r: ellipse(x, z, r - i, r - i, 0, 28), -m["depth"] / 2, height, dome, mat)


def slot(model, m, mat):
    """The cartridge slot's opening along the top: a dark strip just above it."""
    (x0, x1), (y0, y1) = m["slot"]["x"], m["slot"]["y"]
    model.block(x0, x1, y0, y1, m["height"] - 1.0, m["height"] + 0.15, mat)


def back_cover(model, m, x, z, w, h, r, out):
    """A battery cover (or the GBC's battery bulge) standing out of the back."""
    back = m["depth"] / 2
    outline = lambda i: rectangle(x, z, w, h, r, i, 6)
    model.loft([at(outline(0), back - 0.8), at(outline(0), back + out * 0.5), at(outline(min(out * 0.6, r * 0.6)), back + out)],
               ["case", "case"], ("case", "case"))


def shoulder(model, m, side):
    """The GBA's L or R: a band along the top and round the top outer corner, standing out of it."""
    w, h = m["width"], m["height"]
    r = m["corners"][1]
    cx, cz = w / 2 - r, h - r
    out, depth = 1.3, 3.5
    angles = [90 + (8 - 90) * k / 12 for k in range(13)]
    start = cx - 15.0
    outer = [(start, h + out)] + [(cx + (r + out) * math.cos(math.radians(a)), cz + (r + out) * math.sin(math.radians(a)))
                                   for a in angles]
    inner = [(cx + (r - depth) * math.cos(math.radians(a)), cz + (r - depth) * math.sin(math.radians(a)))
             for a in reversed(angles)] + [(start, h - depth)]
    outline = outer + inner
    if side < 0:
        outline = [(-x, z) for x, z in reversed(outline)]
    y0, y1 = -m["depth"] / 2 + 6.0, m["depth"] / 2 - 3.0
    model.loft([at(outline, y0), at(outline, y1)], ["light"], ("light", "light"))


def build_gb(model, m):
    body(model, m)
    front, w, h = -m["depth"] / 2, m["width"], m["height"]
    dpad(model, m, "dark")
    round_buttons(model, m, "ab", 2.0, (2.2, 1.2))
    length, width, degrees = m["pill"]
    for _, x, z in m["pills"]:
        model.button(lambda i, x=x, z=z: pill(x, z, length, width, degrees, i), front, 1.1, (0.6, 0.4), "rubber")
    slot(model, m, "dark")
    model.block(-36.0, -28.0, front + 3.0, front + 9.0, h - 0.5, h + 1.4, "case")    # the power switch
    model.wheel(w / 2 - 2.0, w / 2 + 1.2, 1.0, 100.0, 6.5, "rubber")                  # volume
    model.wheel(-w / 2 + 2.0, -w / 2 - 1.2, 1.0, 118.0, 6.5, "rubber")                # contrast
    back_cover(model, m, 0.0, 34.0, 62.0, 52.0, 3.0, 0.8)


def build_gbc(model, m):
    body(model, m)
    front, h = -m["depth"] / 2, m["height"]
    dpad(model, m, "dark")
    round_buttons(model, m, "dark", 1.8, (1.8, 0.9))
    length, width, degrees = m["pill"]
    for _, x, z in m["pills"]:
        model.button(lambda i, x=x, z=z: pill(x, z, length, width, degrees, i), front, 1.0, (0.5, 0.4), "rubber")
    slot(model, m, "dark")
    model.block(-33.0, -24.0, front + 4.0, front + 9.5, h - 0.5, h + 1.4, "case")    # the power switch
    back_cover(model, m, 0.0, 33.0, 56.0, 50.0, 8.0, 4.5)                             # the batteries' bulge


def build_gba(model, m):
    body(model, m)
    front = -m["depth"] / 2
    dpad(model, m, "light")
    round_buttons(model, m, "light", 1.8, (1.8, 1.0))
    for _, x, z in m["small_buttons"]:
        model.button(lambda i, x=x, z=z: ellipse(x, z, 2.3 - i, 2.3 - i, 0, 20), front, 0.9, (0.6, 0.4), "light")
    slot(model, m, "dark")
    shoulder(model, m, 1)
    shoulder(model, m, -1)
    back_cover(model, m, 0.0, 22.0, 50.0, 30.0, 3.0, 0.8)


BUILDERS = {"gb": build_gb, "gbc": build_gbc, "gba": build_gba}


def cartridge(m, names, mats):
    """The cartridge, its middle at its origin, its label side facing +y (the console's back), as it goes in."""
    c = m["cart"]
    hw, h, t = c["width"] / 2, c["height"], c["thickness"]
    if c["kind"] == "dmg":
        # Seen from its label side: the corner cut at the top right.
        corners, radii = [(hw, 0), (hw, h - 4.5), (hw - 4.5, h), (-hw, h), (-hw, 0)], [1.2, 0.6, 0.6, 1.5, 1.2]
    else:
        corners, radii = [(hw, 0), (hw, h), (-hw, h), (-hw, 0)], [1.5, 7.0, 7.0, 1.5]
    mirrored = [(-x, z) for x, z in reversed(corners)]
    radii = list(reversed(radii))
    outline = lambda i: [(x, z - h / 2) for x, z in rounded_polygon(mirrored, radii, i, 8)]
    model = Model(names)
    model.slab(outline, -t / 2, t / 2, (0.6, 0.6), (0.6, 0.6), "cart", ("print", "print"),
               (region_uv(m, "cart_rear", dz=h / 2), region_uv(m, "cart", mirror=True, dz=h / 2)))
    return model.finish("cartridge", mats)


def quad(m, names, mats, name, width, height, grow):
    """A flat face (width x height, facing the front) showing the atlas region name: the screen switched on, the
    light lit. Its middle is its origin."""
    model = Model(names)
    w, h = width / 2, height / 2
    verts = [model.bm.verts.new(p) for p in ((-w, 0, -h), (w, 0, -h), (w, 0, h), (-w, 0, h))]  # wound to face -y
    model.face(verts, "print", uv=region_uv(m, name, grow=grow))
    return model.finish(name, mats, outward=False)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def phase(f, f0, f1):
    return min(1.0, max(0.0, (f - f0) / (f1 - f0)))


def smooth(t):
    return t * t * (3 - 2 * t)


def ease_in(t):
    return t * t


def ease_out(t):
    return 1 - (1 - t) ** 2


def back_out(t, s=2.2):
    """Overshoots, then settles at 1."""
    t -= 1
    return 1 + t * t * ((s + 1) * t + s)


def back_in(t, s=1.7):
    """Pulls back a little, then goes."""
    return t * t * ((s + 1) * t - s)


def wobble(f, f0, amount, period=10.0, decay=7.0):
    """A damped spring from frame f0: squash (positive) first, then stretch, dying away."""
    t = f - f0
    return 0.0 if t < 0 else amount * math.exp(-t / decay) * math.sin(2 * math.pi * t / period)


def hop(f, f0, f1, height):
    t = phase(f, f0, f1)
    return height * 4 * t * (1 - t)


def appear(f, f0, f1):
    """A part popping in from nothing between f0 and f1."""
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def vanish(f, f0, f1):
    return 1 - (1 - HIDDEN) * back_in(phase(f, f0, f1)) if f < f1 else HIDDEN


class Pose:
    """One part's pose: where it is (millimetres from its rest place), its turns (degrees: spin about its vertical,
    roll about the line of sight, pitch about the horizontal) and its scale (uniform, with a squash along its vertical)."""

    def __init__(self, x=0.0, z=0.0, spin=0.0, roll=0.0, pitch=0.0, scale=1.0, squash=0.0, flat=1.0):
        self.x, self.z, self.spin, self.roll, self.pitch = x, z, spin, roll, pitch
        self.scale, self.squash, self.flat = scale, squash, flat

    def rotation(self):
        q = Quaternion((0, 0, 1), math.radians(self.spin))
        q = Quaternion((0, 1, 0), math.radians(self.roll)) @ q
        return Quaternion((1, 0, 0), math.radians(self.pitch)) @ q

    def scales(self):
        k, s = self.squash, self.scale
        return Vector((s * (1 + k / 2), s * (1 + k / 2), s * (1 - k) * self.flat))


def timeline_gb(f, c):
    hover, top = c["hover"], c["hover"] + 8.0

    # The cartridge.
    if f == 0 or f >= 197:
        cart = Pose(scale=HIDDEN)
    elif f < 8:
        cart = Pose(z=hover, spin=180, scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=hover, spin=180, scale=appear(f, 8, 16))
    elif f < 44:
        t = (f - 16) / 28
        cart = Pose(z=hover + 2.5 * math.sin(2 * math.pi * t * 2), spin=180,
                    roll=11 * math.sin(2 * math.pi * t * 3) * math.sin(math.pi * t))
    elif f < 60:
        t = smooth(phase(f, 44, 60))
        cart = Pose(z=hover + 8.0 * t, spin=180 + 180 * t)
    elif f < 70:
        t = ease_in(phase(f, 60, 70))
        cart = Pose(z=top * (1 - t), spin=360, squash=-0.1 * t)
    elif f < 178:
        cart = Pose(spin=360)
    elif f < 188:
        t = phase(f, 178, 188)
        cart = Pose(z=(hover + 14) * ease_out(t), spin=360 + 360 * smooth(t), squash=-0.08 * math.sin(math.pi * t))
    elif f < 196:
        cart = Pose(z=hover + 14 + 4 * phase(f, 188, 195), spin=720, scale=vanish(f, 188, 195))
    else:
        cart = Pose(z=hover + 18, spin=720, scale=HIDDEN)

    # The console: squashed by the cartridge landing; a hop for joy once the logo is down.
    squash = wobble(f, 70, 0.12) + 0.07 * math.sin(math.pi * phase(f, 122, 128)) + wobble(f, 146, 0.09)
    console = Pose(z=hop(f, 128, 146, 10.0), squash=squash)

    # The battery light, and the Nintendo logo scrolling down the screen to its middle.
    led = Pose(scale=appear(f, 74, 80) if f < 176 else HIDDEN)
    if f < 78 or f >= 178:
        logo = Pose(scale=HIDDEN)
    elif f < 80:
        logo = Pose(z=c["logo_top"], scale=HIDDEN)
    elif f < 174:
        logo = Pose(z=c["logo_top"] * (1 - phase(f, 80, 124)))
    else:
        logo = Pose(flat=max(HIDDEN, 1 - phase(f, 174, 178)))
    return {"cartridge": cart, "console": console, "led": led, "screen": logo}


def timeline_gbc(f, c):
    hover, bonk = c["hover"], c["bonk"]

    if f == 0 or f >= 197:
        cart = Pose(scale=HIDDEN)
    elif f < 6:
        cart = Pose(z=hover, spin=180, roll=-12, scale=HIDDEN)
    elif f < 14:
        cart = Pose(z=hover, spin=180, roll=-12, scale=appear(f, 6, 14))
    elif f < 30:
        t = (f - 14) / 16
        cart = Pose(z=hover + 2.0 * math.sin(2 * math.pi * t), spin=180, roll=-12 * math.cos(2 * math.pi * t))
    elif f < 40:
        t = smooth(phase(f, 30, 40))
        cart = Pose(z=hover, spin=180 + 180 * t, roll=-12 * (1 - t))
    elif f < 48:
        t = ease_in(phase(f, 40, 48))
        cart = Pose(z=hover - (hover - bonk) * t, spin=360, squash=-0.08 * t)
    elif f < 60:
        # Bonk: it doesn't go in, bounces off the top with a puzzled tilt.
        t = phase(f, 48, 60)
        cart = Pose(z=bonk + 12.0 * math.sin(math.pi * t), spin=360, roll=16 * math.sin(math.pi * t),
                    squash=wobble(f, 48, 0.12, 8, 5))
    elif f < 72:
        # Lining itself up: a wiggle at the slot's mouth.
        t = phase(f, 60, 72)
        cart = Pose(z=bonk, spin=360 + 8 * math.sin(2 * math.pi * t * 2) * (1 - t),
                    roll=7 * math.sin(2 * math.pi * t * 3) * (1 - t))
    elif f < 80:
        cart = Pose(z=bonk + (-1.5 - bonk) * ease_in(phase(f, 72, 80)), spin=360)
    elif f < 84:
        cart = Pose(z=-1.5 * (1 - smooth(phase(f, 80, 84))), spin=360)
    elif f < 178:
        cart = Pose(spin=360)
    elif f < 188:
        t = phase(f, 178, 188)
        cart = Pose(z=(hover + 6) * ease_out(t), spin=360 + 360 * smooth(t), roll=-14 * math.sin(math.pi * t))
    elif f < 196:
        cart = Pose(z=hover + 6 + 4 * phase(f, 188, 195), spin=720, scale=vanish(f, 188, 195))
    else:
        cart = Pose(z=hover + 10, spin=720, scale=HIDDEN)

    # The console: a bump at the bonk and the click, then a happy shimmy.
    t = phase(f, 84, 112)
    shimmy = 11 * math.sin(2 * math.pi * t * 3) * (1 - t) if 84 <= f < 112 else 0.0
    console = Pose(spin=shimmy, squash=wobble(f, 48, 0.05, 8, 5) + wobble(f, 80, 0.06, 8, 5))

    led = Pose(scale=appear(f, 88, 94) if f < 174 else HIDDEN)
    if f < 90 or f >= 176:
        screen = Pose(scale=HIDDEN)
    elif f < 98:
        screen = Pose(flat=0.02 + 0.98 * ease_out(phase(f, 90, 98)), squash=-0.06 * math.sin(math.pi * phase(f, 90, 98)))
    elif f < 170:
        screen = Pose()
    else:
        screen = Pose(flat=max(HIDDEN, 1 - 0.98 * ease_in(phase(f, 170, 175))))
    return {"cartridge": cart, "console": console, "led": led, "screen": screen}


def timeline_gba(f, c):
    hover, start_x, start_z = c["hover"], 62.0, c["hover"] + 16.0

    if f == 0 or f >= 197:
        cart = Pose(scale=HIDDEN)
    elif f < 6:
        cart = Pose(x=start_x, z=start_z, spin=180, scale=HIDDEN)
    elif f < 14:
        cart = Pose(x=start_x, z=start_z, spin=180, scale=appear(f, 6, 14))
    elif f < 44:
        # A swoop to above the slot, in a barrel roll.
        t = smooth(phase(f, 14, 44))
        cart = Pose(x=start_x * (1 - t), z=hover + 16 * (1 - t) + 14 * math.sin(math.pi * t), spin=180 + 540 * t,
                    roll=-24 * math.sin(math.pi * t))
    elif f < 52:
        cart = Pose(z=hover + 2.5 * math.sin(math.pi * phase(f, 44, 52)), spin=720)
    elif f < 60:
        cart = Pose(z=hover + (-1.2 - hover) * ease_in(phase(f, 52, 60)), spin=720, squash=-0.08 * phase(f, 52, 60))
    elif f < 64:
        cart = Pose(z=-1.2 * (1 - smooth(phase(f, 60, 64))), spin=720)
    elif f < 178:
        cart = Pose(spin=720)
    elif f < 188:
        t = phase(f, 178, 188)
        cart = Pose(x=-32 * smooth(t), z=(hover + 10) * ease_out(t), spin=720 + 360 * smooth(t), roll=22 * math.sin(math.pi * t))
    elif f < 196:
        t = phase(f, 188, 195)
        cart = Pose(x=-32 - 10 * t, z=hover + 10 + 3 * t, spin=1080, scale=vanish(f, 188, 195))
    else:
        cart = Pose(x=-42, z=hover + 13, spin=1080, scale=HIDDEN)

    # The console: a nod once it's in, and a hop when the screen's up.
    t = phase(f, 64, 92)
    nod = 8 * math.sin(2 * math.pi * t * 2) * (1 - t) if 64 <= f < 92 else 0.0
    squash = wobble(f, 60, 0.07) + 0.06 * math.sin(math.pi * phase(f, 112, 118)) + wobble(f, 136, 0.08)
    console = Pose(z=hop(f, 118, 136, 8.0), pitch=nod, squash=squash)

    led = Pose(scale=appear(f, 66, 72) if f < 174 else HIDDEN)
    if f < 72 or f >= 176:
        screen = Pose(scale=HIDDEN)
    elif f < 84:
        t = phase(f, 72, 84)
        screen = Pose(scale=max(HIDDEN, back_out(t, 1.6)), roll=-30 * (1 - ease_out(t)))
    elif f < 170:
        screen = Pose()
    else:
        screen = Pose(flat=max(HIDDEN, 1 - 0.98 * ease_in(phase(f, 170, 175))))
    return {"cartridge": cart, "console": console, "led": led, "screen": screen}


TIMELINES = {"gb": timeline_gb, "gbc": timeline_gbc, "gba": timeline_gba}


def animate(kind, nodes, rests, context):
    """Keys every frame of the focused clip: one action, a slot per part, so it exports as one clip."""
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    action = bpy.data.actions.new("focused")
    for obj in nodes.values():
        obj.rotation_mode = "QUATERNION"
        obj.animation_data_create()
        obj.animation_data.action = action
        if obj.animation_data.action_slot is None:
            obj.animation_data.action_slot = action.slots.new(id_type="OBJECT", name=obj.name)
    last = {}
    for f in range(LENGTH + 1):
        for name, pose in TIMELINES[kind](f, context).items():
            obj = nodes[name]
            obj.location = rests[name] + Vector((pose.x, 0.0, pose.z))
            q = pose.rotation()
            if name in last and last[name].dot(q) < 0:
                q.negate()
            last[name] = q
            obj.rotation_quaternion = q
            obj.scale = pose.scales()
            for path in ("location", "rotation_quaternion", "scale"):
                obj.keyframe_insert(path, frame=f)


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, kind, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    m = L.MODELS[kind]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    image = bpy.data.images.load(os.path.join(images, f"{kind}_print.png"))
    names = MATERIALS[kind]
    colours = dict(m["colours"], print="#FFFFFF")
    mats = {n: material(n, colours[n], ROUGHNESS[n], image if n == "print" else None) for n in names}

    model = Model(names)
    BUILDERS[kind](model, m)
    console = model.finish(kind, mats)
    cart = cartridge(m, names, mats)
    front = -m["depth"] / 2
    (sx0, sx1), (sz0, sz1) = m["screen"]["x"], m["screen"]["z"]
    if kind == "gb":
        x0, x1, z0, z1 = m["regions"]["screen"]["mm"]
        screen = quad(m, names, mats, "screen", x1 - x0, z1 - z0, 0.3)
        screen_at = Vector(((sx0 + sx1) / 2, front - 0.25, (sz0 + sz1) / 2 + 3.0))
    else:
        screen = quad(m, names, mats, "screen", sx1 - sx0, sz1 - sz0, 0.3)
        screen_at = Vector(((sx0 + sx1) / 2, front - 0.25, (sz0 + sz1) / 2))
    led = quad(m, names, mats, "led", 5.0, 5.0, 0.0)

    # The node tree: root (the view and the fit), console, and its parts at their rest places.
    c = m["cart"]
    seat = Vector((0.0, c["y"], m["height"] + c["protrudes"] - c["height"] / 2))
    rests = {"console": Vector(), "cartridge": seat, "screen": screen_at,
             "led": Vector((m["led"][0], front - 0.3, m["led"][1]))}
    root = bpy.data.objects.new(f"{kind}_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    for part in (cart, screen, led):
        part.parent = console
    nodes = {"console": console, "cartridge": cart, "screen": screen, "led": led}

    # The three-quarter view, then the spec's fit (on y = 0, Blender's z; centred; the largest side 1 m) of the console
    # at rest, as the root's transform.
    yaw, pitch = TILT[kind]
    tilt = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
    points = [tilt @ v.co for v in console.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    fit = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    root.matrix_world = fit @ tilt

    bonk = c["height"] - c["protrudes"]  # how far above its seat the cartridge's bottom meets the top
    context = {"hover": bonk + (5.0 if kind == "gb" else 10.0 if kind == "gbc" else 6.0), "bonk": bonk,
               "logo_top": sz1 - 2.5 - screen_at.z - 0.6}
    animate(kind, nodes, rests, context)
    scene.frame_start, scene.frame_end = 0, LENGTH
    scene.frame_set(0)

    meshes = [console, cart, screen, led]
    tris = sum(triangles(o.data) for o in meshes)
    print(f"{m['name']}: {tris} triangles ({triangles(cart.data)} the cartridge), {len(names)} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


main()
