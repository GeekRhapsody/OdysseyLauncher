"""The console theme's Recently played card (godot/themes/console/models/systems/recently_played.glb): the bouncy alarm
clock of the Dreamcast's settings menu.

Made to match a capture of the menu (the owner's 10 s video, measured frame by frame): a round red clock, a drum with
rounded edges (RADIUS, its depth from BACK to LIP), its beige face sunk a little behind the rim, two thick square red
hands widening to their tips, with no cap over them, two golden domes for bells, each resting on the rim at one point
and tipped outwards (BELL_ANGLE from the top), and a stubby winding knob at three o'clock. Everything is built in units
of its radius.

The `focused` clip is the menu's: a one-second loop in which the clock rocks like a wheel. Its lean swings 30 degrees
either way in step with its travel (0.58 radii either side of the middle, about what rolling would give), so it rolls
back and forth, hopping as it goes: high on the way right (HOP), barely on the way back (HOP_BACK). It keeps its round
shape throughout (its outline in the capture is 0.97 as tall as it's wide in every frame). Meanwhile its hands scissor: they turn opposite ways, once a second each, crossing at twelve and at six; and
its bells pulse in turn, one growing as the other shrinks, PULSES times a second. The clip starts and ends at the middle of the roll back, upright, with the hands at ten to two: the rest pose.

A small node tree: a root (the turn towards the video's view, TILT: a little from the clock's right, its face just
tipped up so that from the grid's camera, which looks down on the cards, it's seen head on, as in the video; and the
model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the clock, its origin in its
middle, and the clock holding its hands (origins on the face's middle) and its bells (origins where they touch the
rim, so they grow and shrink from there).

The launcher fits every card's rest pose to 1 m on its largest side, so a round clock would come out as large as a
card can be. To draw it smaller (SIZE of that), the body carries two specks, triangles a hundred-thousandth of its size
facing away from the viewer (so they're culled), in front of it and behind it: they make its depth its largest side.

Three plain materials (red, cream, yellow), no textures, within the system model budget. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/alarm_clock.py -- godot/themes/console/models/systems/recently_played.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clip import Pose, key  # noqa: E402
from mega_drive_cartridge import export, material, triangles  # noqa: E402

RADIUS = 1.0
BACK, LIP, FACE = 0.28, -0.30, -0.24   # depths (y, the front towards -y): the back, the rim's front, the face
SEGMENTS = 64
BELL_ANGLE = 40.0                      # degrees from the top
BELL = dict(radius=0.46, height=0.34, depth=0.75)  # a dome; depth: its squeeze front to back
PULSES, PULSE = 4, 0.25                # the bells' pulses a second, and how far each grows and shrinks
SIZE = 0.85                            # the clock's largest side, as a share of the 1 m the launcher fits a card to
KNOB_ANGLE = 90.0                      # degrees clockwise from the top
HANDS = {                              # (angle clockwise from 12 at rest, length, half width at the middle and at the tip, depth)
    "minute": (-48.0, 0.62, 0.085, 0.125, -0.268),
    "hour": (48.0, 0.52, 0.085, 0.125, -0.250),
}
TILT = (-14.0, 4.0)                    # degrees: yaw (its right side nearer), pitch (its face up a little, against the grid camera's look down)
FPS, LENGTH = 60, 60                   # one second, keyed at 60 frames a second
LEAN, TRAVEL, HOP, HOP_BACK = 30.0, 0.58, 0.44, 0.1  # degrees; radii
COLOURS = dict(red="#D8332F", cream="#EADBB8", yellow="#E6B511")
ROUGHNESS = dict(red=0.45, cream=0.7, yellow=0.4)
NAMES = ["red", "cream", "yellow"]
MATS = {}


# ---- Geometry --------------------------------------------------------------------------------------------------------

def arc(cx, cy, r, a0, a1, steps):
    """Points on a circle about (cx, cy) in the (r, h) profile plane, from angle a0 to a1 in degrees."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps)))
            for i in range(steps + 1)]


def revolve(bm, profile, frame, segments=SEGMENTS):
    """
    Turns a profile about an axis: profile is a list of ((r, h), material) from one end of the axis to the other, the
    material that of the band to the next point; frame maps (r cos a, r sin a, h) to the model. Points on the axis
    (r = 0) close the ends.
    """
    rings = []
    for (r, h), _ in profile:
        if r < 1e-9:
            rings.append([bm.verts.new(frame @ Vector((0, 0, h)))] * segments)
        else:
            rings.append([bm.verts.new(frame @ Vector((r * math.cos(2 * math.pi * j / segments),
                                                       r * math.sin(2 * math.pi * j / segments), h)))
                          for j in range(segments)])
    for i in range(len(rings) - 1):
        a, b, mat = rings[i], rings[i + 1], NAMES.index(profile[i][1])
        for j in range(segments):
            k = (j + 1) % segments
            quad = [a[j], a[k], b[k], b[j]]
            quad = [v for n, v in enumerate(quad) if v not in quad[:n]]  # an end's fan
            face = bm.faces.new(quad)
            face.material_index = mat
            face.smooth = True


def body():
    """The drum, the face and the knob, the clock's middle at its origin."""
    bm = bmesh.new()
    axis = Matrix.Rotation(math.radians(90), 4, "X")  # (x, y, h) to (x, -h, y): h along -y, towards the front
    # The profile from the middle of the back, round the rim, then the face to its middle: h is -y.
    profile = [((0.0, -BACK), "red")]
    profile += [(p, "red") for p in arc(0.80, -BACK + 0.20, 0.20, -90, 0, 6)]
    profile += [(p, "red") for p in arc(0.84, -LIP - 0.16, 0.16, 0, 140, 10)]  # the rim's front, a fat round tube
    profile += [((0.70, -FACE), "cream"), ((0.45, -FACE), "cream"), ((0.0, -FACE), "cream")]
    revolve(bm, [((r * RADIUS, h), m) for (r, h), m in profile], axis)

    # The knob, a stubby cylinder out of the rim at three o'clock.
    knob = [((0.0, 0.9), "yellow"), ((0.14, 0.9), "yellow"), ((0.14, 1.13), "yellow"), ((0.115, 1.165), "yellow"), ((0.0, 1.17), "yellow")]
    revolve(bm, [((a * RADIUS, b * RADIUS), m) for (a, b), m in knob], Matrix.Rotation(math.radians(KNOB_ANGLE), 4, "Y"), 20)
    return finish("clock", bm, sharp=40)


def bell(name):
    """A bell, its origin the middle of its base, where it rests on the rim, its dome along +z: rounded over (a
    superellipse a little fuller than an ellipse), a little narrower front to back."""
    r, h = BELL["radius"], BELL["height"]
    cap = [((0.0, 0.0), "yellow"), ((r - 0.03, 0.0), "yellow")]
    cap += [((r * math.cos(a) ** 0.8, 0.03 + (h - 0.03) * math.sin(a) ** 0.8), "yellow")
            for a in (math.radians(d) for d in range(0, 91, 10))]
    bm = bmesh.new()
    revolve(bm, [((a * RADIUS, b * RADIUS), m) for (a, b), m in cap], Matrix.Diagonal((1.0, BELL["depth"], 1.0, 1.0)), 40)
    return finish(name, bm, sharp=40)


def specks(obj, points):
    """Adds a speck at each point (in obj's space): a triangle too small to see, facing +y (away from the viewer)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    e = 1e-5 * RADIUS
    for p in points:
        corners = [bm.verts.new(p + Vector(d)) for d in ((0, 0, 0), (0, 0, e), (e, 0, 0))]  # wound to face +y
        bm.faces.new(corners).material_index = NAMES.index("red")
    bm.to_mesh(obj.data)
    bm.free()


def hand(name):
    """A hand, its pivot at its origin, pointing up (+z), its front facing -y: a thick bar widening to its tip, its
    corners taken off."""
    _, length, w0, w1, _ = HANDS[name]
    tail, cut = 0.07 * RADIUS, 0.02 * RADIUS
    outline = [(w0, -tail + cut), (w1, length - cut), (w1 - cut, length), (-w1 + cut, length), (-w1, length - cut),
               (-w0, -tail + cut), (-w0 + cut, -tail), (w0 - cut, -tail)]
    bm = bmesh.new()
    front = [bm.verts.new((x, -0.008, z)) for x, z in outline]
    back = [bm.verts.new((x, 0.008, z)) for x, z in outline]
    faces = [list(reversed(front)), back]
    faces += [[front[j], front[(j + 1) % len(front)], back[(j + 1) % len(back)], back[j]] for j in range(len(front))]
    for f in faces:
        bm.faces.new(f).smooth = False
    return finish(name, bm, sharp=0)


def finish(name, bm, sharp):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(sharp):
            e.smooth = False
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for n in NAMES:
        mesh.materials.append(MATS[n])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ---- The focused clip ------------------------------------------------------------------------------------------------

def timeline(f):
    # The cycle's angle: 0 at the left end, 90 at the top of the hop, 180 at the right end; the clip starts at 270,
    # the middle of the roll back, where the clock stands upright.
    phi = 2 * math.pi * f / LENGTH + 1.5 * math.pi
    lean = -LEAN * math.cos(phi)
    x = -TRAVEL * RADIUS * math.cos(phi)
    hop = RADIUS * (HOP * max(0.0, math.sin(phi)) + HOP_BACK * max(0.0, -math.sin(phi)))
    turn = 360.0 * f / LENGTH
    pulse = PULSE * math.sin(2 * math.pi * PULSES * f / LENGTH)
    return {
        "bell_l": Pose(scale=1 + pulse),
        "bell_r": Pose(scale=1 - pulse),
        "clock": Pose(x=x, z=hop, roll=lean),
        "minute": Pose(roll=turn),
        "hour": Pose(roll=-turn),
    }


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    MATS.update({n: material(n, COLOURS[n], ROUGHNESS[n]) for n in NAMES})

    clock = body()
    clock.location = (0, 0, RADIUS)
    nodes = {"clock": clock}
    for name, (angle, _, _, _, depth) in HANDS.items():
        part = hand(name)
        part.parent = clock
        part.rotation_mode = "QUATERNION"
        part.rotation_quaternion = Quaternion((0, 1, 0), math.radians(angle))
        part.location = (0, depth, 0)
        nodes[name] = part
    for name, side in (("bell_l", -1), ("bell_r", 1)):
        part = bell(name)
        part.parent = clock
        angle = math.radians(side * BELL_ANGLE)
        part.rotation_mode = "QUATERNION"
        part.rotation_quaternion = Quaternion((0, 1, 0), angle)
        part.location = (RADIUS * math.sin(angle), 0, RADIUS * math.cos(angle))
        nodes[name] = part

    # The video's view, then the spec's fit of the clock at rest, as the root's transform.
    root = bpy.data.objects.new("recently_played_root", None)
    scene.collection.objects.link(root)
    clock.parent = root
    bpy.context.view_layer.update()
    yaw, pitch = TILT
    tilt = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
    meshes = [clock, nodes["minute"], nodes["hour"], nodes["bell_l"], nodes["bell_r"]]

    def bounds():
        points = [tilt @ o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
        return Vector([min(p[i] for p in points) for i in range(3)]), Vector([max(p[i] for p in points) for i in range(3)])

    # The specks in front and behind, so the depth is the largest side and the clock comes out at SIZE.
    lo, hi = bounds()
    visible = hi - lo
    middle, half = (lo + hi) / 2, max(visible.x, visible.z) / SIZE / 2
    local = (tilt @ clock.matrix_world).inverted()
    specks(clock, [local @ Vector((middle.x, middle.y + d, middle.z)) for d in (-half, half)])
    lo, hi = bounds()
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) @ tilt

    key("focused", nodes, timeline, LENGTH)
    print(f"Alarm clock: {sum(triangles(o.data) for o in meshes)} triangles, {len(NAMES)} materials, "
          f"size {visible.x:.2f} x {visible.y:.2f} x {visible.z:.2f} tilted, {size.y:.2f} deep with the specks, before the fit")
    export([root] + meshes, out, animations=True)


main()
