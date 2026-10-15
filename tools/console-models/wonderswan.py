"""The console theme's WonderSwan and WonderSwan Color system models
(godot/themes/console/models/systems/wonderswan.glb and wonderswancolor.glb).

Built in Blender from the real handhelds' proportions (wonderswan_layout.py has the measurements, taken from
photographs): a Skeleton Green WonderSwan with its silver screen surround and off-white buttons, and a Crystal Blue
WonderSwan Color with its white lens, its buttons on raised discs and its orange POWER button. Each body is its front
outline (the grip at the left end hanging a little lower than the rest) lofted back, its front and back edges rounded
over, with the two diamonds of four buttons at the left end, A and B at the right, SOUND and START (and POWER) below the
screen, the cartridge slot's opening along the top at the back, and the battery cover on the back; the printing (the
surround, the switched-off screen, the legends, the speaker, the buttons' tops, what shows through the clear plastic,
and the back) is one 1024 x 1024 texture, drawn by wonderswan_print.py and projected onto the front and the back.

Each is a small node tree: a root (the three-quarter view and the model spec's fit) holding the console, and the
console holding its cartridge (Odyssey, a made-up game) and two screens switched on, the start-up screen and a game
played upright, so they ride along when the console moves. At rest the three children are shrunk to nothing inside
the console, so it stands with its screen off and no cartridge, and the rest pose's bounds are the console's. The
`focused` clip (7 s, looping) plays a game, a little differently on each, and both turn the console on its end, as
the WonderSwan's own vertical games do (its buttons are laid out for it):

- WonderSwan: the cartridge pops up above the console showing its label, wiggles, somersaults backwards turning its
  label to the slot, and drops into the back; the console squashes under it, the start-up screen comes on; the console
  crouches and hops onto its end, the upright game on its screen, rocks to the game for a while, and hops back. Then
  the screen goes off and the cartridge jumps out, spins and vanishes.
- WonderSwan Color: the cartridge swoops in from the right on a barrel roll and clicks in, the console shimmies and the
  start-up screen zooms in; then it leaps up in a full twirl and lands on its end, bounces to the game three times and
  turns back with a flourish; the cartridge leaves to the left.

The model is turned to a three-quarter view (TILT: its left end towards the viewer and its face tipped up, as the
handhelds look lying in front of you), then fitted to the model spec (A7): standing on y = 0, centred, the largest side
1 m. The turn and the fit are the root's transform, so the clip moves its parts in millimetres.

Five or six materials and one texture each, within the system model budget. Run from the repo root:

    python tools/console-models/wonderswan_print.py artifacts/wonderswans
    blender -b --factory-startup --python tools/console-models/wonderswan.py -- artifacts/wonderswans wonderswan godot/themes/console/models/systems/wonderswan.glb

and the same with wonderswancolor.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wonderswan_layout as L  # noqa: E402
from clip import HIDDEN, Pose, back_in, back_out, bump, ease_in, ease_out, hop, key, phase, smooth, wobble  # noqa: E402
from game_gear import ellipse, rectangle, rounded_polygon  # noqa: E402
from mega_drive_cartridge import export, material, triangles  # noqa: E402

TILT = {"wonderswan": (20.0, 10.0), "wonderswancolor": (20.0, 10.0)}  # degrees: yaw (left end nearer), pitch (face up)
FPS = 30
LENGTH = 210              # the focused clip's frames
MATERIALS = {             # never "back" or "label": those are media slots (A7)
    "wonderswan": ["case", "print", "buttons", "dark", "cart"],
    "wonderswancolor": ["case", "print", "buttons", "power", "dark", "cart"],
}
ROUGHNESS = dict(case=0.5, print=0.55, buttons=0.6, power=0.5, dark=0.5, cart=0.45)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def at(outline, y):
    """An (x, z) outline at depth y."""
    return [(x, y, z) for x, z in outline]


def region_uv(m, name, mirror=False, dz=0.0):
    """The planar projection of a point (x, z in millimetres) into the atlas region name; mirror for a face seen from
    behind (+y). dz moves the mesh's z back to the region's."""
    x, y, w, h = m["regions"][name]["px"]
    x0, x1, z0, z1 = m["regions"][name]["mm"]

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

    def button(self, outline_at, front, height, dome, side, top=None, uv=None, rings=4):
        """A button standing out of the face at depth front: straight sides, then a dome; outline_at(inset) is its rim.
        Its top is the material top (the side's if None), projected through uv."""
        stack = [at(outline_at(0), front + 0.6), at(outline_at(0), front - height)]
        for k in range(1, rings + 1):
            a = math.pi / 2 * k / rings
            stack.append(at(outline_at(dome[0] * (1 - math.cos(a))), front - height - dome[1] * math.sin(a)))
        self.loft(stack, [side] * (len(stack) - 1), (side, top or side), (None, uv))

    def block(self, x0, x1, y0, y1, z0, z1, mat):
        outline = [(x1, z0), (x1, z1), (x0, z1), (x0, z0)]
        self.loft([at(outline, y0), at(outline, y1)], [mat], (mat, mat))

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


def densify(points, counts):
    """The outline with its i-th side cut into counts[i] pieces."""
    out = []
    for i, (ax, az) in enumerate(points):
        bx, bz = points[(i + 1) % len(points)]
        for k in range(counts[i]):
            t = k / counts[i]
            out.append((ax + (bx - ax) * t, az + (bz - az) * t))
    return out


def body_outline(m):
    """outline_at(inset) for the body: the rounded rectangle, its long sides cut fine, the right of its bottom raised."""
    w, h = m["width"], m["height"]
    corners = [(w / 2, 0), (w / 2, h), (-w / 2, h), (-w / 2, 0)]
    base = rounded_polygon(corners, m["corners"], 0.0, 12)
    counts = []
    for i, (ax, az) in enumerate(base):
        bx, bz = base[(i + 1) % len(base)]
        counts.append(max(1, round(math.hypot(bx - ax, bz - az) / 3.0)))
    return lambda inset: [(x, z + L.outline_lift(m, x, z)) for x, z in
                          densify(rounded_polygon(corners, m["corners"], inset, 12), counts)]


def body(model, m):
    d = m["depth"]
    model.slab(body_outline(m), -d / 2, d / 2, m["front_round"], m["back_round"], "case", ("print", "print"),
               (region_uv(m, "front"), region_uv(m, "rear", mirror=True)))


def petals(model, m, base):
    """Every petal, standing out of base (the face, or the Color's discs), its top the front's printing."""
    front_uv = region_uv(m, "front")
    for _, x, z, a in L.petal_centres(m):
        corners, radii = L.petal_corners(m, x, z, a)
        lift = base(x, z)
        model.button(lambda i, c=corners, r=radii: rounded_polygon(c, r, i, 6), lift, 1.5, (0.7, 0.6), "buttons",
                     "print", front_uv)


def pills(model, m):
    front, front_uv = -m["depth"] / 2, region_uv(m, "front")
    length, width = m["pill"]
    for _, x, z in m["pills"]:
        model.button(lambda i, x=x, z=z: rectangle(x, z, length, width, width * 0.48, i, 6), front, 1.0, (0.5, 0.4),
                     "buttons", "print", front_uv)
    if "power" in m:
        x, z, length, width = m["power"]
        model.button(lambda i: rectangle(x, z, length, width, width * 0.48, i, 6), front, 1.1, (0.5, 0.4),
                     "power", "print", front_uv)


def slot(model, m):
    """The cartridge slot's opening along the top, at the back: a dark block meeting the back's printed slot."""
    c, h, back = m["cart"], m["height"], m["depth"] / 2
    model.block(c["x"] - c["width"] / 2 - 0.5, c["x"] + c["width"] / 2 + 0.5, back - c["thickness"] - 0.8, back - 0.2,
                h - 6.0, h + 0.15, "dark")


def battery_cover(model, m):
    """The battery cover standing out of the back, below the slot: an AA lies across under it."""
    back = m["depth"] / 2
    outline = lambda i: rectangle(m["cart"]["x"], 16.0, 60.0, 20.0, 4.0, i, 6)
    model.loft([at(outline(0), back - 0.8), at(outline(0), back + 1.2), at(outline(1.4), back + 2.2)],
               ["case", "case"], ("case", "case"))


def build_wonderswan(model, m):
    body(model, m)
    front = -m["depth"] / 2
    petals(model, m, lambda x, z: front)
    pills(model, m)
    slot(model, m)
    model.block(-m["width"] / 2 - 1.0, -m["width"] / 2 + 2.0, -2.6, 2.6, 31.0, 40.0, "dark")  # the power switch
    battery_cover(model, m)


def build_wonderswancolor(model, m):
    body(model, m)
    front, front_uv = -m["depth"] / 2, region_uv(m, "front")
    r = m["disc"]
    for cluster in ("Y", "X"):
        cx, cz = m["clusters"][cluster]
        model.button(lambda i, cx=cx, cz=cz: ellipse(cx, cz, r - i, r - i, 0, 48), front, 0.7, (0.4, 0.3), "case",
                     "print", front_uv, rings=2)
    on_disc = lambda x, z: front - (1.0 if x < 0 else 0.0)
    petals(model, m, on_disc)
    pills(model, m)
    slot(model, m)
    battery_cover(model, m)


BUILDERS = {"wonderswan": build_wonderswan, "wonderswancolor": build_wonderswancolor}


def cartridge(m, names, mats):
    """The cartridge, its middle at its origin, its label side facing +y (the console's back), as it goes in."""
    c = m["cart"]
    hw, h, t = c["width"] / 2, c["height"], c["thickness"]
    corners = [(hw - 2.4, 0), (hw, c["contacts"]), (hw, h), (-hw, h), (-hw, c["contacts"]), (-hw + 2.4, 0)]
    radii = [0.4, 0.8, 1.6, 1.6, 0.8, 0.4]
    outline = lambda i: [(x, z - h / 2) for x, z in rounded_polygon(corners, radii, i, 6)]
    model = Model(names)
    model.slab(outline, -t / 2, t / 2, (0.6, 0.6), (0.6, 0.6), "cart", ("print", "print"),
               (region_uv(m, "cart_rear", dz=h / 2), region_uv(m, "cart", mirror=True, dz=h / 2)))
    return model.finish("cartridge", mats)


def quad(m, names, mats, name):
    """A flat face facing the front, showing the atlas region name (a screen switched on), its middle at its origin."""
    model = Model(names)
    x0, x1, z0, z1 = m["regions"][name]["mm"]
    verts = [model.bm.verts.new(p) for p in ((x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1))]  # wound to face -y
    model.face(verts, "print", uv=region_uv(m, name))
    return model.finish(name, mats, outward=False)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    """A part popping in from nothing between f0 and f1."""
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def vanish(f, f0, f1):
    return 1 - (1 - HIDDEN) * back_in(phase(f, f0, f1)) if f < f1 else HIDDEN


def flat(v):
    """A screen squeezed to v of its height (switching on or off)."""
    return Pose(axes=(1.0, 1.0, max(HIDDEN, v)))


def on_end(m, degrees, lift=0.0, **kw):
    """The console turned by degrees about its line of sight (negative: its left end down), moved so it still stands
    on the floor, centred, lift above it."""
    t = math.radians(degrees)
    s, c = math.sin(t), math.cos(t)
    w, h = m["width"], m["height"]
    stand = w / 2 * abs(s) + h / 2 * abs(c)
    return Pose(x=-h / 2 * s, z=stand - h / 2 * c + lift, roll=degrees, **kw)


def timeline_wonderswan(f, m, c):
    hover = c["hover"]

    # The cartridge: it pops up, wiggles, somersaults backwards turning its label to the slot, and drops in.
    if f == 0 or f >= 197:
        cart = Pose(scale=HIDDEN)
    elif f < 6:
        cart = Pose(z=hover, spin=180, scale=HIDDEN)
    elif f < 14:
        cart = Pose(z=hover, spin=180, scale=appear(f, 6, 14))
    elif f < 34:
        t = (f - 14) / 20
        cart = Pose(z=hover + 2.0 * math.sin(2 * math.pi * t), spin=180,
                    roll=9 * math.sin(2 * math.pi * t * 2) * math.sin(math.pi * t))
    elif f < 52:
        t = smooth(phase(f, 34, 52))
        cart = Pose(z=hover + 12.0 * math.sin(math.pi * t), spin=180 + 180 * t, pitch=-360 * t)
    elif f < 58:
        cart = Pose(z=hover + 1.5 * math.sin(math.pi * phase(f, 52, 58)), spin=360)
    elif f < 66:
        t = ease_in(phase(f, 58, 66))
        cart = Pose(z=hover * (1 - t), spin=360, squash=-0.1 * t)
    elif f < 186:
        cart = Pose(spin=360)
    elif f < 192:
        t = phase(f, 186, 192)
        cart = Pose(z=(hover + 10) * ease_out(t), spin=360 + 360 * smooth(t), squash=-0.08 * math.sin(math.pi * t))
    elif f < 197:
        cart = Pose(z=hover + 10 + 4 * phase(f, 192, 197), spin=720, scale=vanish(f, 192, 196))
    else:
        cart = Pose(scale=HIDDEN)

    # The console: squashed by the cartridge landing; a crouch, a hop onto its end, rocking to the game, a hop back.
    if f < 116:
        console = Pose(squash=wobble(f, 66, 0.1))
    elif f < 122:
        console = Pose(squash=0.09 * math.sin(math.pi * phase(f, 116, 122)))
    elif f < 142:
        console = on_end(m, -90 * back_out(phase(f, 122, 142), 1.4), hop(f, 122, 140, 16.0))
    elif f < 168:
        console = on_end(m, -90 + wobble(f, 140, 7.0, 12, 6) + 5 * math.sin(2 * math.pi * (f - 146) / 11) * bump(f, 146, 166))
    elif f < 186:
        console = on_end(m, -90 * (1 - smooth(phase(f, 168, 184))), hop(f, 168, 184, 10.0))
    else:
        console = Pose(squash=wobble(f, 184, 0.08))

    # The screens: the start-up screen, then the upright game while the console is on its end.
    if f < 72 or f >= 130:
        boot = Pose(scale=HIDDEN)
    elif f < 80:
        boot = flat(0.02 + 0.98 * ease_out(phase(f, 72, 80)))
    elif f < 124:
        boot = Pose()
    else:
        boot = flat(1 - ease_in(phase(f, 124, 130)))
    if f < 132 or f >= 174:
        game = Pose(scale=HIDDEN)
    elif f < 140:
        game = flat(0.02 + 0.98 * ease_out(phase(f, 132, 140)))
    elif f < 168:
        game = Pose()
    else:
        game = flat(1 - ease_in(phase(f, 168, 174)))
    return {"cartridge": cart, "console": console, "screen": boot, "screen_v": game}


def timeline_wonderswancolor(f, m, c):
    hover, start_x, start_z = c["hover"], 70.0, c["hover"] + 18.0

    # The cartridge: a swoop in from the right on a barrel roll, a dip, and a click into the slot.
    if f == 0 or f >= 197:
        cart = Pose(scale=HIDDEN)
    elif f < 6:
        cart = Pose(x=start_x, z=start_z, spin=180, scale=HIDDEN)
    elif f < 14:
        cart = Pose(x=start_x, z=start_z, spin=180, scale=appear(f, 6, 14))
    elif f < 44:
        t = smooth(phase(f, 14, 44))
        cart = Pose(x=start_x * (1 - t), z=hover + 18 * (1 - t) + 12 * math.sin(math.pi * t), spin=180 + 540 * t,
                    roll=-26 * math.sin(math.pi * t))
    elif f < 52:
        cart = Pose(z=hover + 2.5 * math.sin(math.pi * phase(f, 44, 52)), spin=720)
    elif f < 60:
        cart = Pose(z=hover * (1 - ease_in(phase(f, 52, 60))) - 1.2 * phase(f, 52, 60), spin=720,
                    squash=-0.08 * phase(f, 52, 60))
    elif f < 64:
        cart = Pose(z=-1.2 * (1 - smooth(phase(f, 60, 64))), spin=720)
    elif f < 186:
        cart = Pose(spin=720)
    elif f < 194:
        t = phase(f, 186, 194)
        cart = Pose(x=-34 * smooth(t), z=(hover + 10) * ease_out(t), spin=720 + 360 * smooth(t),
                    roll=22 * math.sin(math.pi * t))
    elif f < 197:
        t = phase(f, 194, 197)
        cart = Pose(x=-34 - 8 * t, z=hover + 10 + 3 * t, spin=1080, scale=vanish(f, 192, 197))
    else:
        cart = Pose(scale=HIDDEN)

    # The console: a shimmy at the click; a crouch, a leap in a full twirl onto its end, three bounces to the game,
    # and a turn back with a flourish.
    if f < 64:
        console = Pose(squash=wobble(f, 60, 0.06, 8, 5))
    elif f < 118:
        t = phase(f, 64, 92)
        console = Pose(spin=10 * math.sin(2 * math.pi * t * 3) * (1 - t) if f < 92 else 0.0,
                       squash=wobble(f, 60, 0.06, 8, 5))
    elif f < 124:
        console = Pose(squash=0.1 * math.sin(math.pi * phase(f, 118, 124)))
    elif f < 150:
        console = on_end(m, -450 * smooth(phase(f, 124, 148)), hop(f, 124, 148, 26.0))
    elif f < 170:
        bounce = hop(f, 152, 158, 4.0) + hop(f, 158, 164, 4.0) + hop(f, 164, 170, 4.0)
        console = on_end(m, -450 + wobble(f, 148, 8.0, 10, 5), bounce)
    elif f < 188:
        console = on_end(m, -450 + 90 * back_out(phase(f, 170, 186), 1.8), hop(f, 170, 182, 8.0))
    else:
        console = on_end(m, -360, 0.0, squash=wobble(f, 186, 0.07, 8, 5))

    # The screens: the start-up screen zooms in; the upright game comes on in the twirl.
    if f < 70 or f >= 128:
        boot = Pose(scale=HIDDEN)
    elif f < 82:
        boot = Pose(scale=max(HIDDEN, back_out(phase(f, 70, 82), 1.6)))
    elif f < 122:
        boot = Pose()
    else:
        boot = flat(1 - ease_in(phase(f, 122, 128)))
    if f < 130 or f >= 176:
        game = Pose(scale=HIDDEN)
    elif f < 140:
        game = Pose(scale=max(HIDDEN, back_out(phase(f, 130, 140), 1.6)))
    elif f < 170:
        game = Pose()
    else:
        game = flat(1 - ease_in(phase(f, 170, 176)))
    return {"cartridge": cart, "console": console, "screen": boot, "screen_v": game}


TIMELINES = {"wonderswan": timeline_wonderswan, "wonderswancolor": timeline_wonderswancolor}


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
    screen = quad(m, names, mats, "screen")
    upright = quad(m, names, mats, "screen_v")

    # The node tree: root (the view and the fit), console, and its parts at their rest places, shrunk to nothing.
    c, s = m["cart"], m["screen"]
    front, back = -m["depth"] / 2, m["depth"] / 2
    screen_at = Vector((s["x"], front - 0.25, s["z"]))
    rests = {
        "cartridge": Vector((c["x"], back - c["thickness"] / 2 + 0.4, m["height"] + c["protrudes"] - c["height"] / 2)),
        "screen": screen_at,
        "screen_v": screen_at + Vector((0.0, -0.05, 0.0)),
    }
    root = bpy.data.objects.new(f"{kind}_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    for name, part in (("cartridge", cart), ("screen", screen), ("screen_v", upright)):
        part.parent = console
        part.location = rests[name]
    nodes = {"console": console, "cartridge": cart, "screen": screen, "screen_v": upright}

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
    context = {"hover": bonk + 6.0}
    key("focused", nodes, lambda f: TIMELINES[kind](f, m, context), LENGTH)

    meshes = [console, cart, screen, upright]
    tris = sum(triangles(o.data) for o in meshes)
    print(f"{m['name']}: {tris} triangles ({triangles(cart.data)} the cartridge), {len(names)} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


main()
