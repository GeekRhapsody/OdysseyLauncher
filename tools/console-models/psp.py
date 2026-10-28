"""The console theme's PlayStation Portable system model (godot/themes/console/models/systems/psp.glb): a piano-black
PSP-1000, standing up.

Built in Blender from the real handheld's measurements (psp_layout.py has them, and their sources): the body is its
face's outline (each end one broad arc) lofted back through its depth: the glossy front shell, its edge rounded over;
the seam; the silver band standing a quarter millimetre proud, the clear shoulder buttons L and R in its place at the
top corners; the matte back shell, its edge rounded over a lot; the bay, a recess the door's shape, cut into the back.
On the face stand the D-pad's four buttons, the analogue nub, the four face buttons and the bottom row (HOME, VOL - +,
the display and sound buttons, SELECT and START), each a solid domed over; the screen's glass is one flat face over
the face's printing. In the band: the POWER/HOLD switch on the right end and the OPEN latch on the top edge. On the
back: the UMD door, a panel standing a millimetre proud, hinged along its bottom edge, and the UMD (a made-up game).
The printing is three textures drawn by psp_print.py: the face, the back and the top edge in one atlas; the UMD's
two sides and the door's outside in a second; and the glass's own, the screen switched off.

The glass's material is `video`: while the card is focused, the launcher plays the theme's video for it there
(godot/themes/console/videos/psp.mp4, drawn by psp_video.py), starting it again each time the clip loops (A6 Card
videos); otherwise, and where there's no decoder, it shows its own texture, the screen switched off.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
face tipped up a little; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the
console, which turns about its middle; the console holding CROSS, START, the nub, the POWER switch, the OPEN latch,
the power light (shrunk to nothing while it's off) and the door (its origin on its hinge), the door holding the UMD,
which waits in its seat shrunk to nothing, so the rest pose is the console alone, its door shut.

The `focused` clip (10 s, looping; its timing is psp_layout.py's, which the video follows) plays a game: the console
turns round on the spot to show its back; OPEN slides towards R and the door springs open; the UMD appears over it,
its label out, and slides down into it; the door shuts on it and the latch springs back; the console turns back to its
face; POWER slides up and springs back, the power light comes on and the screen with it (the start-up, the XMB); CROSS
chooses the game; START at its title; the nub steers the ship and CROSS fires, five times; POWER is held up, the screen
goes off and the light out. The UMD stays in, and is shrunk away once the door has shut on it.

Seven materials (case, rear, buttons, silver, clear, media, video) and three textures, within the system model budget.
Run from the repo root:

    python tools/console-models/psp_print.py artifacts/made-up-games artifacts/psp
    python tools/console-models/psp_video.py artifacts/made-up-games godot/themes/console/videos/psp.mp4
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
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402
from saturn import inset  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end (the face buttons, POWER) comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.42, rear=0.7, buttons=0.38, silver=0.48, clear=0.38, media=0.45, video=0.5)
PIVOT = Vector((0.0, L.BACK / 2, 0.0))   # the console turns about its middle
PRESS = 0.8                              # how far a button goes in


# ---- UVs ---------------------------------------------------------------------------------------------------------------

def region_uv(regions, name, mirror=False, depth=False):
    """A planar projection into an atlas region: (x, z) (or (x, y) with depth, for the top edge) in millimetres to UVs;
    mirror for a face seen from behind."""
    px, py, pw, ph = regions[name]["px"]
    x0, x1, z0, z1 = regions[name]["mm"]

    def uv(co):
        x = -co.x if mirror else co.x
        z = co.y if depth else co.z
        return (px + (x - x0) / (x1 - x0) * pw) / L.ATLAS, 1 - (py + (z1 - z) / (z1 - z0) * ph) / L.ATLAS
    return uv


FRONT = region_uv(L.PRINT_REGIONS, "front")
REAR = region_uv(L.PRINT_REGIONS, "rear", mirror=True)
TOP = region_uv(L.PRINT_REGIONS, "top", depth=True)


def swatch(name, swatches=L.SWATCHES):
    x, y = swatches[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def smoother(t):
    """Smootherstep: no jolt where it starts or stops."""
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (6 * t - 15) + 10)


def shade(obj, angle=35.0):
    """Smooth shading, edges sharper than angle kept sharp; flat faces (caps) stay flat."""
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) <= 4
    obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


# ---- The body ----------------------------------------------------------------------------------------------------------

def rings():
    """The body's rings, front to back: (y, inset, what the band after it is)."""
    out = []
    r = L.FRONT_ROUND
    for k in range(4):
        a = math.pi / 2 * k / 3
        out.append((r * (1 - math.cos(a)), r * (1 - math.sin(a)), "front"))
    b0, b1 = L.BAND
    out += [(L.SEAM - 0.25, 0.0, "front"), (L.SEAM, 0.35, "groove"), (b0 - 0.05, 0.35, "groove"),
            (b0, -L.BAND_OUT + 0.12, "band"), (b0 + 0.25, -L.BAND_OUT, "band"), (b1 - 0.25, -L.BAND_OUT, "band"),
            (b1, -L.BAND_OUT + 0.12, "groove"), (b1 + 0.05, 0.35, "groove"), (b1 + 0.3, 0.0, "back")]
    r = L.BACK_ROUND
    out.append((L.BACK - r, 0.0, "back"))
    for k in range(1, 5):
        a = math.pi / 2 * k / 4
        out.append((L.BACK - r + r * math.sin(a), r * (1 - math.cos(a)), "back"))
    return out


def body(m):
    """The shell from the face's outline through its depth: one closed solid, each band of faces its own material."""
    spec = rings()
    bm = bmesh.new()
    loops = [[bm.verts.new((x, y, z)) for x, z in L.body_outline(d)] for y, d, _ in spec]
    kinds = []
    for (a, b), (_, _, kind) in zip(zip(loops, loops[1:]), spec):
        n = len(a)
        for j in range(n):
            bm.faces.new([a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]])
            kinds.append(kind)
    bm.faces.new(loops[0])
    bm.faces.new(list(reversed(loops[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    kinds += ["front_cap", "back_cap"]                      # the faces keep the order they were made in
    obj = new_object("psp", bm, m["case"])
    mesh = obj.data
    # Each face's material and UVs by the band it's in.
    for mat in (m["rear"], m["silver"], m["clear"]):
        mesh.materials.append(mat)
    names = [mt.name for mt in mesh.materials]
    uv = mesh.uv_layers.new(name="UVMap")
    for p, kind in zip(mesh.polygons, kinds):
        c, n = p.center, p.normal
        up = n.z > 0.85 and abs(c.x) < L.SHOULDER["x"]
        if kind == "front_cap":
            mat, uv_of = "case", FRONT
        elif kind == "back_cap":
            mat, uv_of = "rear", REAR
        elif kind == "band":
            if abs(c.x) > L.SHOULDER["x"] and c.z > L.SHOULDER["z"]:
                mat, uv_of = "clear", None
            elif up:
                mat, uv_of = "case", TOP
            else:
                mat, uv_of = "silver", None
        elif up:
            mat, uv_of = ("rear" if kind == "back" else "case"), TOP
        else:
            mat, uv_of = {"front": ("case", swatch("case")), "groove": ("case", swatch("dark")),
                          "back": ("rear", swatch("rear"))}[kind]
        p.material_index = names.index(m[mat].name)
        for li in p.loop_indices:
            uv.data[li].uv = uv_of(mesh.vertices[mesh.loops[li].vertex_index].co) if uv_of else (0.0, 0.0)
    shade(obj)
    # The bay under the door: a recess its shape, its floor the back's printing.
    depth = L.BAY["depth"]
    cutter = solid("bay", [[(x, y, z) for x, z in L.door_outline(L.BAY["inset"])] for y in (L.BACK - depth, L.BACK + 3.0)],
                   m["rear"])
    boolean(obj, cutter)
    paint(obj, m["rear"], REAR, lambda c, n, kind: n.y > 0.9 and abs(c.y - (L.BACK - depth)) < 0.05)
    paint(obj, m["rear"], swatch("dark"),
          lambda c, n, kind: L.BACK - depth + 0.05 < c.y < L.BACK - 0.01 and abs(n.y) < 0.5 and kind == "rear")
    return obj


# ---- The controls --------------------------------------------------------------------------------------------------------

def button(name, outline_at, height, dome, m, rings_=4, top=None):
    """A button standing out of the face: its foot inside it, straight sides out to height, then a dome (inset, rise)
    over; outline_at(inset) its rim. The faces turned to the viewer take the face's printing (its top, its symbol)."""
    stack = [(outline_at(0.0), 0.6), (outline_at(0.0), -height)]
    for k in range(1, rings_ + 1):
        a = math.pi / 2 * k / rings_
        stack.append((outline_at(dome[0] * (1 - math.cos(a))), -height - dome[1] * math.sin(a)))
    obj = solid(name, [[(x, y, z) for x, z in pts] for pts, y in stack], m["buttons"])
    paint(obj, m["buttons"], top or FRONT, lambda c, n, kind: n.y < -0.35)
    paint(obj, m["buttons"], swatch("case"), lambda c, n, kind: n.y >= -0.35)
    return shade(obj, 50.0)


def circle(x, z, r, n=28):
    return [(x + r * math.cos(2 * math.pi * k / n), z + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def at_origin(obj, where):
    """The part's mesh moved so that where (in the set) is its origin: it moves from there."""
    obj.data.transform(Matrix.Translation(-Vector(where)))
    return obj, Vector(where)


def controls(m):
    """The buttons: the still ones joined into the set; CROSS, START and the nub, which the clip moves, apart."""
    still, moving = [], {}
    cx, cz = L.DPAD["x"], L.DPAD["z"]
    for name, a in L.DPAD_BUTTONS:
        corners, radii = L.pentagon(cx, cz, a)
        rim = L.rounded_polygon(corners, radii, 6)
        still.append(button("dpad_" + name, lambda d, rim=rim: inset(rim, d) if d > 1e-6 else rim, 1.3, (0.8, 0.5), m))
    r = L.FACE["radius"]
    for name, x, z in L.face_centres():
        part = button("face_" + name, lambda d, x=x, z=z: circle(x, z, r - d, 32), 1.4, (1.5, 0.7), m)
        if name == "cross":
            moving["cross"] = at_origin(part, (x, 0.0, z))
        else:
            still.append(part)
    x, z, r = L.NUB["x"], L.NUB["z"], L.NUB["radius"]
    nub = solid("nub", [[(px, y, pz) for px, pz in circle(x, z, rr, 32)] for rr, y in
                        ((r, 0.6), (r, -1.3), (r - 0.4, -1.75), (r - 1.1, -1.95))], m["buttons"])
    paint(nub, m["buttons"], FRONT, lambda c, n, kind: n.y < -0.35)
    paint(nub, m["buttons"], swatch("case"), lambda c, n, kind: n.y >= -0.35)
    moving["nub"] = at_origin(shade(nub, 50.0), (x, 0.0, z))
    for name, x, shape in L.ROW:
        if shape == "shield":
            corners, radii = L.shield(x, L.ROW_Z)
            rim = L.rounded_polygon(corners, radii, 5)
            outline = lambda d, rim=rim: inset(rim, d) if d > 1e-6 else rim
        else:
            outline = lambda d, x=x: [(x + (2.9 - d) * math.cos(2 * math.pi * k / 24),
                                       L.ROW_Z + (2.4 - d) * math.sin(2 * math.pi * k / 24)) for k in range(24)]
        part = button("row_" + name.lower(), outline, 0.6, (0.5, 0.3), m, rings_=3)
        if name == "START":
            moving["start"] = at_origin(part, (x, 0.0, L.ROW_Z))
        else:
            still.append(part)
    return still, moving


def power_switch(m):
    """The POWER/HOLD switch in the band on the right end: a ribbed silver slide, its origin where it rests."""
    z0, z1 = L.POWER["z"]
    zm = (z0 + z1) / 2
    xe = L.end_x(zm, -L.BAND_OUT)
    cx, cz = L.END_CENTRE
    out = Vector((xe - cx, 0.0, zm - cz)).normalized()       # the end's outward normal there
    along = Vector((-out.z, 0.0, out.x))                       # up the end, as the switch slides
    ym = (L.BAND[0] + L.BAND[1]) / 2
    part = box("power", -(z1 - z0) / 2, (z1 - z0) / 2, -1.5, 1.5, -0.6, 1.0, m["silver"])
    bevel(part, 0.5, segments=2)
    for k in range(4):                                       # its grip's ribs
        rib = box("rib", -2.4 + k * 1.6 - 0.25, -2.4 + k * 1.6 + 0.25, -1.3, 1.3, 0.9, 1.4, m["silver"])
        part = join([part, rib], "power")
    frame = Matrix(((along.x, 0.0, out.x, 0.0), (0.0, 1.0, 0.0, 0.0), (along.z, 0.0, out.z, 0.0), (0, 0, 0, 1)))
    part.data.transform(frame)
    return shade(part, 40.0), Vector((xe, ym, zm)), along


def latch(m):
    """The OPEN latch on the top edge, its top printed as it rests (the top region draws it), its origin where it
    rests."""
    x0, x1 = L.LATCH["x"]
    ym = (L.BAND[0] + L.BAND[1]) / 2
    part = box("latch", x0, x1, ym - 1.5, ym + 1.5, L.HEIGHT - 0.6, L.HEIGHT + 0.7, m["case"])
    bevel(part, 0.4, segments=2)
    paint(part, m["case"], TOP, lambda c, n, kind: n.z > 0.5)
    paint(part, m["case"], swatch("silver"), lambda c, n, kind: n.z <= 0.5)
    return at_origin(shade(part, 40.0), ((x0 + x1) / 2, ym, L.HEIGHT))


def light(m):
    """The POWER light lit: a green dot on the face, shrunk to nothing while the PSP is off."""
    x, z = L.LIGHTS["power"]
    part = solid("power_light", [[(px, y, pz) for px, pz in circle(0.0, 0.0, L.LIGHTS["r"] + 0.1, 12)] for y in (-0.08, 0.3)],
                 m["case"])
    paint(part, m["case"], swatch("lit"), lambda c, n, kind: True)
    return part, Vector((x, 0.0, z))


def edges(m):
    """What stands on the ends and the bottom: the WLAN switch (left end) and the yellow DC IN (under the right end)."""
    parts = []
    z0, z1 = L.WLAN["z"]
    zm = (z0 + z1) / 2
    xe = L.end_x(zm, -L.BAND_OUT)
    ym = (L.BAND[0] + L.BAND[1]) / 2
    wlan = box("wlan", -xe - 1.0, -xe + 0.6, ym - 1.2, ym + 1.2, z0, z1, m["silver"])
    bevel(wlan, 0.4, segments=2)
    parts.append(wlan)
    x0, x1 = L.DC_IN["x"]
    plug = box("dc_in", x0, x1, ym - 2.4, ym + 2.4, -0.5, 0.6, m["case"])
    paint(plug, m["case"], swatch("yellow"), lambda c, n, kind: True)
    parts.append(plug)
    return parts


def screen(m):
    """The glass: one flat face over the face's printing, the video's whole frame across it."""
    (x0, x1), (z0, z1) = L.GLASS["x"], L.GLASS["z"]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]          # anticlockwise seen from the front: it faces -y
    face = bm.faces.new([bm.verts.new((x, -0.04, z)) for x, z in corners])
    for loop, (x, z) in zip(face.loops, corners):
        loop[uv].uv = ((x - x0) / (x1 - x0), (z - z0) / (z1 - z0))
    return new_object("glass", bm, m["video"])


# ---- The door and the UMD ------------------------------------------------------------------------------------------------

MEDIA = {name: region_uv(L.MEDIA_REGIONS, name) for name in L.MEDIA_REGIONS}


def door(m):
    """The UMD door, its origin on its hinge (its outside's bottom edge): a panel standing a millimetre proud of the
    back, its outside's edge rounded over, its outside the media atlas's door, the rest dark."""
    y0, y1 = L.BACK - L.DOOR["thick"] / 2, L.BACK + L.DOOR["thick"] / 2
    r = 0.7
    stack = [(L.door_outline(0.0), y0), (L.door_outline(0.0), y1 - r)]
    for k in range(1, 4):
        a = math.pi / 2 * k / 3
        stack.append((L.door_outline(r * (1 - math.cos(a))), y1 - r + r * math.sin(a)))
    part = solid("door", [[(x, y, z) for x, z in pts] for pts, y in stack], m["media"])
    paint(part, m["media"], region_uv(L.MEDIA_REGIONS, "door", mirror=True), lambda c, n, kind: n.y > 0.9 and c.y > y1 - 0.01)
    paint(part, m["media"], swatch("inside", L.MEDIA_SWATCHES), lambda c, n, kind: not (n.y > 0.9 and c.y > y1 - 0.01))
    for p in part.data.polygons:
        p.use_smooth = not (abs(p.normal.y) > 0.99)
    part.data.set_sharp_from_angle(angle=math.radians(40))
    return at_origin(part, (0.0, y1, L.DOOR["z"][0]))


def umd(m):
    """The UMD, its disc's middle at its origin, its label facing +y (the back, outwards), as it goes into the door."""
    t = L.UMD["thickness"]
    r = 0.5
    stack = [(L.umd_outline(r), -t / 2)]
    for k in range(1, 3):
        a = math.pi / 2 * k / 2
        stack.append((L.umd_outline(r * (1 - math.sin(a))), -t / 2 + r * (1 - math.cos(a))))
    for k in range(0, 3):
        a = math.pi / 2 * k / 2
        stack.append((L.umd_outline(r * (1 - math.cos(a))), t / 2 - r + r * math.sin(a)))
    part = solid("umd", [[(x, y, z) for x, z in pts] for pts, y in stack], m["media"])
    paint(part, m["media"], region_uv(L.MEDIA_REGIONS, "umd", mirror=True), lambda c, n, kind: n.y > 0.9)
    paint(part, m["media"], MEDIA["umd_rear"], lambda c, n, kind: n.y < -0.9)
    paint(part, m["media"], swatch("edge", L.MEDIA_SWATCHES), lambda c, n, kind: abs(n.y) <= 0.9)
    for p in part.data.polygons:
        p.use_smooth = abs(p.normal.y) < 0.99
    part.data.set_sharp_from_angle(angle=math.radians(40))
    return part


# ---- The clip --------------------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    """A button pressed at f0: in over two frames, held, out over three."""
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def slide_up(f, f0, hold):
    """The POWER switch pushed up at f0, held for hold frames, then let go: it springs back."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - ease_out(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f, c):
    poses = {}
    # The console turns round on the spot to show its back, and back again once the UMD is in.
    poses["console"] = Pose(spin=180.0 * smoother(phase(f, *L.TURN_OUT)) * (1 - smoother(phase(f, *L.TURN_BACK))))

    # OPEN slides towards R, the door springs open; it shuts on the UMD with a little bounce, and the latch springs back.
    shut = L.DOOR_SHUT[1]
    poses["latch"] = Pose(x=L.LATCH["travel"] * smooth(phase(f, *L.LATCH_OPEN)) * (1 - ease_out(phase(f, shut, shut + 4))))
    opening = back_out(phase(f, *L.DOOR_OPEN), 1.5) * (1 - ease_in(phase(f, *L.DOOR_SHUT)))
    bounce = 2.5 * math.exp(-(f - shut) / 2.5) * abs(math.sin(math.pi * (f - shut) / 4.0)) if f >= shut else 0.0
    poses["door"] = Pose(pitch=L.OPEN * opening - bounce)

    # The UMD, in the door's frame: it appears over the open door, its label out, slides down into it and seats; once
    # the door has shut on it, it's inside the console, and goes.
    lift = c["lift"]
    s0, s1 = L.UMD_SHOWN
    d0, d1 = L.UMD_SLIDE
    if f < s0 or f >= shut + 4:
        disc = Pose(scale=HIDDEN)
    elif f < s1:
        disc = Pose(y=1.5, z=lift, scale=max(HIDDEN, back_out(phase(f, s0, s1), 1.6)))
    elif f < d0:
        disc = Pose(y=1.5, z=lift + 1.2 * math.sin(math.pi * phase(f, s1, d0)))
    elif f < d1:
        t = smoother(phase(f, d0, d1))
        disc = Pose(y=1.5 * (1 - t), z=lift * (1 - t))
    else:
        disc = Pose(z=-0.7 * math.sin(math.pi * phase(f, d1, d1 + 4)))
    poses["umd"] = disc

    # POWER: pushed up and let go to switch on; held up to switch off. The light while it's on.
    up = max(slide_up(f, L.POWER_ON, 2), slide_up(f, L.POWER_OFF, 7))
    poses["power"] = Pose(x=c["along"].x * L.POWER["travel"] * up, z=c["along"].z * L.POWER["travel"] * up)
    poses["power_light"] = Pose() if L.POWER_ON + 2 <= f < L.LIGHT_OFF else Pose(scale=HIDDEN)

    # CROSS chooses the game and fires; START at the title; the nub steers.
    poses["cross"] = Pose(y=PRESS * max(tap(f, f0) for f0 in (L.CROSS,) + L.FIRE))
    poses["start"] = Pose(y=PRESS * 0.8 * tap(f, L.START, 3))
    sx, sz = L.steer(f)
    poses["nub"] = Pose(x=L.NUB["travel"] * sx, z=L.NUB["travel"] * sz)
    return poses


# ---- Main --------------------------------------------------------------------------------------------------------------

def finish(whole, parts, timeline_, out):
    """card.finish(), but the set turns too: the root holds the console, keyed about its middle, which holds the parts
    (each at its place in the set, or in another part it rides). The root turns the card to the three-quarter view and
    fits its rest pose."""
    scene = bpy.context.scene
    root = bpy.data.objects.new("psp_root", None)
    scene.collection.objects.link(root)
    whole.data.transform(Matrix.Translation(-PIVOT))
    whole.parent = root
    whole.location = PIVOT
    nodes = {"console": whole}
    for name, spec in parts.items():
        obj, where = spec[0], spec[1]
        holder = parts[spec[2]][0] if len(spec) > 2 else whole
        obj.parent = holder
        obj.location = where - PIVOT if holder is whole else where
        nodes[name] = obj
    key("focused", nodes, timeline_, L.LENGTH)
    bpy.context.view_layer.update()

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    meshes = list(nodes.values())
    points = [tilt @ (o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt
    textures = {node.image.name for o in meshes for mat in o.data.materials if mat.node_tree
                for node in mat.node_tree.nodes if node.type == "TEX_IMAGE" and node.image}
    print(f"PSP: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set, "
          f"{triangles(parts['umd'][0].data)} the UMD, {triangles(parts['door'][0].data)} the door), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, {len(textures)} textures, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "psp_print.png"))
    media = bpy.data.images.load(os.path.join(images, "psp_media.png"))
    still = bpy.data.images.load(os.path.join(images, "psp_screen.png"))
    colours = dict(case="#FFFFFF", rear="#FFFFFF", buttons="#FFFFFF", silver=L.COLOURS["silver"],
                   clear=L.COLOURS["clear"], media="#FFFFFF", video="#FFFFFF")
    textures = dict(case=printed, rear=printed, buttons=printed, media=media, video=still)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    still_parts, moving = controls(m)
    whole = join([body(m)] + still_parts + edges(m) + [screen(m)], "psp")
    switch, switch_at, along = power_switch(m)
    lit, lit_at = light(m)
    lid, hinge = door(m)
    disc = umd(m)
    seat = Vector((0.0, -L.DOOR["thick"] - L.UMD["thickness"] / 2,
                   L.UMD_SEAT - L.UMD["bottom"]))                 # in the door's frame: against its inside
    parts = {name: spec for name, spec in moving.items()}
    parts.update({"power": (switch, switch_at), "latch": latch(m), "power_light": (lit, lit_at), "door": (lid, hinge),
                  "umd": (disc, seat, "door")})
    # The UMD hovers with its flat edge 3 mm over the open door's top edge.
    lift = (L.DOOR["z"][1] - L.DOOR["z"][0]) + 3.0 - L.UMD_SEAT
    context = dict(lift=lift, along=along)
    finish(whole, parts, lambda f: timeline(f, context), out)


if __name__ == "__main__":
    main()
