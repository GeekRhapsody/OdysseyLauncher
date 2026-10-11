"""The console theme's Amstrad CPC system model (godot/themes/console/models/systems/amstradcpc.glb): a CPC 464 and its
CTM644 colour monitor, showing BASIC's boot screen.

Built from the owner's photographs (amstrad_cpc_layout.py has the measurements): the keyboard unit, a wedge rising
to a ridge with vent teeth along it; its keys standing off the slope, tapering to their printed tops (dark, with the
green, red and blue ones where the 464 has them), the cursor keys round COPY and the numeric pad on the right of the
main keys; and at its right end the datacorder: its six keys in a slot at the front, the printed panel behind them,
the door with a window over the well, the cassette's spindles and the head in the well, and a slide switch. Behind
it stands the monitor: a bezel whose screen opening slopes in to curved glass, a lid with a handle recess, and the
tube's housing tapering behind. The printing is two textures drawn by amstrad_cpc_print.py: the slope seen square on
(planar-mapped onto the keys' tops, the door and the slope itself), a cassette's two labels, a hub and the monitor's
band in one atlas; and the glass showing the boot screen.

The glass's material is `video`: while the card is focused, the launcher plays the theme's video for it there
(godot/themes/console/videos/amstradcpc.mp4, drawn by amstrad_cpc_video.py), starting it again each time the clip
loops (A6 Card videos); otherwise, and where there's no decoder, it shows its own texture, the boot screen.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the datacorder's end towards the
viewer, the top tipped up a little; then the model spec's fit: standing on y = 0, centred, the largest side 1 m)
holding the set, the datacorder's door (its origin on its hinge, along its back edge), the PLAY and STOP/EJECT keys and
the big ENTER key. The door holds a cassette, which holds its two hubs. The cassette is shrunk to nothing at rest, so
the card is the computer with its door shut and the well empty.

The `focused` clip (9 s, looping; its timing is amstrad_cpc_layout.py's, which the video follows) loads a game from
tape: STOP/EJECT pops the door open, a cassette appears in front of it and slides into it, and the door shuts. The
grid's camera looks at a card level with it, so it sees the card from TILT_PITCH above: under that, an open door turns
its top away, and the cassette in it shows its bottom, which is printed with its side B label (the door opens
DOOR_OPEN, wider than the real one's, so the label faces the viewer). RUN" is typed on the screen; PLAY goes down and
stays down, ENTER is pressed, and the hubs turn while the screen loads the game. STOP/EJECT again: PLAY pops up, the
door opens, the cassette slides out and vanishes, the door shuts, and the computer resets to its boot screen.

Seven materials (case, print, video, key, green, red, blue) and two textures, within the system model budget. Run
from the repo root:

    python tools/console-models/amstrad_cpc_print.py artifacts/cpc
    blender -b --factory-startup --python tools/console-models/amstrad_cpc.py -- artifacts/cpc godot/themes/console/models/systems/amstradcpc.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amstrad_cpc_layout as L  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end (the datacorder) comes towards the viewer
TILT_PITCH = 20.0    # degrees about the horizontal: the top tips up towards the viewer
DOOR_OPEN = 48.0     # degrees: wider than the real door's, so the cassette's side B shows under it from the grid's view
SLIDE = 58.0         # how far in front of its seat in the door the cassette appears, along the door
PRESS = (4.0, 4.5, 3.5)  # how far STOP/EJECT, PLAY and ENTER go down

# The slope's frame: x from the unit's left end, s up the slope from its front edge, h off it.
SLOPE_FRAME = Matrix.Translation((-L.WIDTH / 2, 0, L.FRONT)) @ Matrix.Rotation(L.SLOPE, 4, "X")
DOWN = (Matrix.Rotation(L.SLOPE, 4, "X").to_3x3() @ Vector((0, 0, -1)))  # a key's travel, in the model's frame


def region_uv(region, w, h, flip=True):
    """(x, y) mm on a face drawn w x h into region -> atlas UVs; y counts up from the face's bottom (its front)."""
    rx, ry, rw, rh = L.REGIONS[region]

    def uv(x, y):
        down = (h - y) if flip else y
        return ((rx + x / w * rw) / L.ATLAS, 1 - (ry + down / h * rh) / L.ATLAS)
    return uv


TOP_UV = region_uv("top", L.WIDTH, L.SLOPE_LENGTH)


def print_up(obj, to_frame, uv_of, mat, keep, facing=1.0):
    """
    Prints the faces facing up (facing -1: down) in a frame (to_frame maps the mesh into it) that keep(centre)
    accepts: they take mat and the planar projection uv_of(x, y) of their corners.
    """
    mesh = obj.data
    names = [m.name for m in mesh.materials]
    if mat.name not in names:
        mesh.materials.append(mat)
        names.append(mat.name)
    index = names.index(mat.name)
    uv = mesh.uv_layers.active or mesh.uv_layers.new(name="UVMap")
    turn = to_frame.to_3x3()
    for p in mesh.polygons:
        if (turn @ p.normal).normalized().z * facing > 0.999 and keep(to_frame @ p.center):
            p.material_index = index
            for li in p.loop_indices:
                co = to_frame @ mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv = uv_of(co.x, co.y)


def loft(name, rings, mat, bottom=True):
    """A solid through rings of 3D points (each the same count, in the same order), capped at its top end."""
    bm = bmesh.new()
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(verts, verts[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])
    if bottom:
        bm.faces.new(verts[0])
    bm.faces.new(list(reversed(verts[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def rounded(cx, cy, w, h, r, segments=4):
    """A rounded rectangle's outline, w x h centred on (cx, cy), anticlockwise from its right side."""
    points = []
    for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for k in range(segments + 1):
            a = math.radians(a0 + 90 * k / segments)
            points.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return points


def disc(name, cx, cy, r, z0, z1, mat, segments=20):
    return loft(name, [[(cx + r * math.cos(2 * math.pi * k / segments), cy + r * math.sin(2 * math.pi * k / segments), z)
                        for k in range(segments)] for z in (z0, z1)], mat)


def on_slope(obj):
    obj.data.transform(SLOPE_FRAME)
    return obj


# -- The keyboard unit -----------------------------------------------------------------------------------------------

def key_solid(name, x0, s0, x1, s1, height, inset, mat, m, sink=1.0):
    """A key on the slope (in the slope's frame): its base x0..x1, s0..s1, tapering to its printed top."""
    rect = lambda d, h: [(x0 + d, s0 + d, h), (x1 - d, s0 + d, h), (x1 - d, s1 - d, h), (x0 + d, s1 - d, h)]
    body = loft(name, [rect(0, -sink), rect(inset, height)], mat, bottom=False)
    bevel(body, min(0.7, (x1 - x0 - 2 * inset) / 6), segments=1, angle=30)
    print_up(body, Matrix.Identity(4), TOP_UV, m["print"], lambda c: c.z > height - 0.3)
    return body


def keys(m):
    """The keyboard's keys, on the slope: the ones the clip moves (ENTER) apart."""
    static, moving = [], {}
    solids = []
    for name, x, row, w, rows, colour, _text in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(x, row, w, rows)
        solids.append(key_solid(name, x0, s0, x1, s1, L.KEY_HEIGHT, L.TOP_INSET, m[colour], m))
    left, pitch, width, front, back, height = L.DECK_KEY
    for k, (name, colour, _text) in enumerate(L.DECK_KEYS):
        x0 = left + k * pitch
        solids.append(key_solid(name, x0, front, x0 + width, back, height, 0.8, m[colour], m, sink=L.SLOT[4] - 1))
    for obj in solids:
        on_slope(obj)
        if obj.name in ("enter", "play", "eject"):
            moving[obj.name] = obj
        else:
            static.append(obj)
    return static, moving


def unit(m):
    """The keyboard unit: the wedge, cut for the well and the datacorder's keys, its top printed; the vent teeth."""
    profile = [(0, 0), (L.DEPTH, 0), (L.DEPTH, L.RIDGE), (L.SLOPE_TO, L.RIDGE), (L.SLOPE_TO, L.BACK), (0, L.FRONT)]
    body = prism_x("unit", profile, -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 2.5, segments=2)
    x0, s0, x1, s1, depth = L.WELL
    boolean(body, on_slope(box("well", x0, x1, s0, s1, -depth, 8, m["key"])))
    x0, s0, x1, s1, depth = L.SLOT
    boolean(body, on_slope(box("slot", x0, x1, s0, s1, -depth, 8, m["key"])))
    print_up(body, SLOPE_FRAME.inverted(), TOP_UV, m["print"], lambda c: abs(c.z) < 0.3 and c.y < L.SLOPE_LENGTH)

    parts = [body]
    x = -L.WIDTH / 2 + 14
    while x < L.WIDTH / 2 - 14:
        parts.append(box("tooth", x - 1.2, x + 1.2, L.SLOPE_TO + 4, L.DEPTH - 3, L.RIDGE - 0.5, L.RIDGE + 3.2, m["case"]))
        x += 5.2

    # In the well: the spindles the hubs go on, and the head, then the slide switch behind the door.
    cx, cs = (L.WELL[0] + L.WELL[2]) / 2, L.DOOR[3] - 37.0 + L.SPINDLES[1]
    hub_white = region_uv("hub", 2 * L.HUB, 2 * L.HUB)(L.HUB * 0.2, L.HUB * 1.0)
    for side in (-1, 1):
        spindle = disc("spindle", cx + side * L.SPINDLES[0], cs, 2.6, -L.WELL[4] - 0.5, -14.0, m["print"], segments=10)
        for loop in spindle.data.uv_layers.new(name="UVMap").data:
            loop.uv = hub_white
        parts.append(on_slope(spindle))
    parts.append(on_slope(box("head", cx - 7, cx + 7, L.WELL[1], L.WELL[1] + 5, -L.WELL[4] - 0.5, -9.0, m["red"])))
    x0, s0, x1, s1, height = L.SLIDER
    slider = box("slider", x0 + 9, x0 + 16, s0 + 1, s1 - 1, -1, height, m["key"])
    bevel(slider, 0.8, segments=1)
    parts.append(on_slope(slider))
    return parts


# -- The datacorder's door and the cassette --------------------------------------------------------------------------

def door(m):
    """The door in its own frame: the slope's axes, its origin on the hinge (the middle of its back edge)."""
    x0, s0, x1, s1, thick = L.DOOR
    plate = box("door", x0, x1, s0, s1, 0.2, 0.2 + thick, m["case"])
    bevel(plate, 1.0, segments=2)
    wx0, ws0, wx1, ws1 = L.WINDOW
    boolean(plate, box("window", wx0, wx1, ws0, ws1, -5, 8, m["case"]))
    print_up(plate, Matrix.Identity(4), TOP_UV, m["print"], lambda c: c.z > thick)
    hinge = Vector(((x0 + x1) / 2, s1, 0))
    plate.data.transform(Matrix.Translation(-hinge))
    plate.location = SLOPE_FRAME @ hinge
    plate.rotation_mode = "QUATERNION"
    plate.rotation_quaternion = Quaternion((1, 0, 0), L.SLOPE)
    return plate


def cassette(m):
    """A cassette in its own frame (its middle at the origin, its label up, its tape's edge towards -y), and its hubs."""
    w, d, t = L.CASSETTE
    shell = box("cassette", -w / 2, w / 2, -d / 2, d / 2, -t / 2, t / 2, m["key"])
    bevel(shell, 1.0, segments=2)
    label = region_uv("cassette", w, d)
    print_up(shell, Matrix.Identity(4), lambda x, y: label(x + w / 2, y + d / 2), m["print"], lambda c: c.z > t / 2 - 0.1)
    # Side B, seen from below as the open door shows it: the tape's edge at the image's top.
    label_b = region_uv("cassette_b", w, d)
    print_up(shell, Matrix.Identity(4), lambda x, y: label_b(x + w / 2, d / 2 - y), m["print"],
             lambda c: c.z < -t / 2 + 0.1, facing=-1.0)
    hubs = []
    face = region_uv("hub", 2 * L.HUB, 2 * L.HUB)
    for side, name in ((-1, "hub_l"), (1, "hub_r")):
        hub = disc(name, 0, 0, L.HUB, -0.3, 0.35, m["print"])
        uv = hub.data.uv_layers.new(name="UVMap")
        for loop in hub.data.loops:
            co = hub.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = face(co.x + L.HUB, co.y + L.HUB)
        hub.parent = shell
        hub.location = (side * L.SPINDLES[0], d / 2 - L.HUBS_FROM_TOP, t / 2)
        hubs.append(hub)
    return shell, hubs


# -- The monitor -----------------------------------------------------------------------------------------------------

def glass(mon, mat):
    """The curved glass, its texture (the still, or the video's frames) across the whole of it."""
    gw, gh = L.GLASS
    mid = mon["screen_z"]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    nu, nv = 16, 12
    grid = [[bm.verts.new((gw * (i / nu - 0.5),
                           mon["glass_back"] - mon["bulge"] * (1 - (2 * i / nu - 1) ** 2) * (1 - (2 * j / nv - 1) ** 2),
                           mid + gh * (j / nv - 0.5))) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / nu, b / nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:                                   # it faces the viewer (-Y)
        if f.normal.y > 0:
            bmesh.ops.reverse_faces(bm, faces=[f])
    return new_object("glass", bm, mat)


def monitor(m):
    """The CTM644, its bezel's front facing -Y on y = 0, centred on x = 0, standing on z = 0."""
    mon = L.MONITOR
    w, h, depth, bz = mon["width"], mon["height"], mon["depth"], mon["bezel"]
    mid = mon["screen_z"]
    front = box("bezel", -w / 2, w / 2, 0, bz, 0, h, m["case"])
    bevel(front, 6.0, segments=3)
    (ow, oh), (iw, ih) = mon["opening"], mon["inner"]
    outer, inner = rounded(0, mid, ow, oh, 16), rounded(0, mid, iw, ih, 9)
    cutter = loft("opening", [[(x, -10, z) for x, z in outer], [(x, 0, z) for x, z in outer],
                              [(x, mon["glass_back"] + 2, z) for x, z in inner]], m["key"])
    boolean(front, cutter)

    # The lid on top, a handle's recess in the middle of its front.
    lid = box("lid", -w / 2 + 10, w / 2 - 10, 5, bz + 90, h - 2, h + 5, m["case"])
    bevel(lid, 2.0, segments=2)
    boolean(lid, box("handle", -78, 78, 0, 30, h + 2.5, h + 12, m["case"]))

    def ring(y, rw, rh, r, cz):
        return [(x, y, z) for x, z in rounded(0, cz, rw, rh, r, segments=5)]
    housing = loft("housing", [ring(bz - 2, w - 10, h - 10, 14, h / 2), ring(bz + 120, w - 18, h - 18, 16, h / 2),
                               ring(depth, w * 0.64, h * 0.6, 26, h * 0.56)], m["case"])
    bevel(housing, 4.0, segments=2, angle=50)

    # The band under the opening: the brand and the power switch.
    b0, bh = mon["strip"]
    sw = w - 16
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    corners = [(0, 0), (sw, 0), (sw, bh), (0, bh)]
    f = bm.faces.new([bm.verts.new((-sw / 2 + x, -0.3, b0 + z)) for x, z in corners])
    strip_uv = region_uv("strip", sw, bh)
    for loop, (x, z) in zip(f.loops, corners):
        loop[uv].uv = strip_uv(x, z)
    f.normal_update()
    if f.normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=[f])
    strip = new_object("strip", bm, m["print"])

    parts = [front, lid, housing, strip, glass(mon, m["video"])]
    at = Matrix.Translation((mon["at"][0], mon["at"][1], 0))
    for obj in parts:
        obj.data.transform(at)
    return parts


# -- The clip --------------------------------------------------------------------------------------------------------

def tap(f, f0):
    """A key pressed at f0: down in three frames, held for two, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 5, f0 + 9)))


def pressed(depth):
    d = DOWN * depth
    return Pose(x=d.x, y=d.y, z=d.z)


def timeline(f):
    poses = {}
    first, second = L.EJECT
    poses["eject"] = pressed(PRESS[0] * (tap(f, first) + tap(f, second)))
    poses["play"] = pressed(PRESS[1] * smooth(phase(f, L.PLAY, L.PLAY + 3)) * (1 - smooth(phase(f, second + 2, second + 6))))
    poses["enter"] = pressed(PRESS[2] * tap(f, L.ENTER))

    # The door pops open (overshooting), shuts with a little bounce, and again to take the tape out.
    opening = (back_out(phase(f, first + 3, first + 15)) * (1 - ease_in(phase(f, L.DOOR_SHUT - 14, L.DOOR_SHUT)))
               + back_out(phase(f, second + 4, second + 16)) * (1 - ease_in(phase(f, 246, 258))))
    bounce = sum(3.0 * math.exp(-(f - f0) / 3.0) * abs(math.sin(math.pi * (f - f0) / 4.0)) for f0 in (L.DOOR_SHUT, 258) if f >= f0)
    poses["door"] = Pose(pitch=-(DOOR_OPEN * opening + bounce))

    # The cassette appears in front of the open door, slides in, and later slides back out and vanishes.
    grow = back_out(phase(f, 26, 34)) * (1 - smooth(phase(f, 240, 247)))
    if f < 26 or f > 247:                            # at rest, hidden in its seat
        slide = 0.0
    else:
        slide = SLIDE * ((1 - ease_out(phase(f, 34, 60))) if f < 120 else ease_in(phase(f, 220, 240)))
    poses["cassette"] = Pose(y=-slide, z=1.5 * slide / SLIDE, scale=max(HIDDEN, grow))
    turn = 1440.0 * smooth(phase(f, L.ENTER + 4, second - 2))   # four turns of the hubs while the game loads
    poses["hub_l"] = poses["hub_r"] = Pose(spin=turn)
    return poses


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    m = {
        "case": material("case", "#3A3C3F", 0.6),
        "print": material("print", "#FFFFFF", 0.55, bpy.data.images.load(os.path.join(images, "cpc_print.png"))),
        # The glass: the launcher plays the card's video on the material named video (A6 Card videos).
        "video": material("video", "#FFFFFF", 0.2, bpy.data.images.load(os.path.join(images, "cpc_screen.png"))),
        "key": material("key", "#1D1E21", 0.5),
        "green": material("green", "#2F9C44", 0.45),
        "red": material("red", "#C6281F", 0.45),
        "blue": material("blue", "#2C56AE", 0.45),
    }
    m["dark"] = m["key"]                             # the layout's dark keys
    static, moving = keys(m)
    computer = join(unit(m) + static + monitor(m), "amstradcpc")
    lid = door(m)
    tape, hubs = cassette(m)
    tape.parent = lid
    tape.location = (0, -37.0, -7.5)                 # in the well, under the door
    nodes = {"door": lid, "cassette": tape, "hub_l": hubs[0], "hub_r": hubs[1], **moving}
    for obj in [computer, lid] + list(moving.values()):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))
    for obj in [tape] + hubs:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    root = bpy.data.objects.new("amstradcpc_root", None)
    scene.collection.objects.link(root)
    for obj in [computer, lid] + list(moving.values()):
        obj.parent = root
    bpy.context.view_layer.update()
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in computer.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [computer, lid, tape] + hubs + list(moving.values())
    materials = {mat.name for obj in meshes for mat in obj.data.materials}
    print(f"Amstrad CPC: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(computer.data)} the set), "
          f"{len(materials)} materials, size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


main()
