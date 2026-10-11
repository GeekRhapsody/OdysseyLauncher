"""The console theme's Recently played card (godot/themes/console/models/systems/recently_played.glb): the bouncy alarm
clock of the Dreamcast's settings menu.

A round red clock, a drum with rounded edges (RADIUS, its depth from BACK to LIP), its cream face sunk behind a lip,
with two red hands (ten past ten-ish, as in the menu), a red cap over them, two yellow bells on top tipped outwards
(BELL_ANGLE from the top) and a yellow winding knob on its right. Everything is built in units of its radius.

The `focused` clip (6 s, looping) is the menu's bounce, made bigger: the clock hops three times, squashing before each
hop and on each landing, stretching in the air and leaning into each hop, its bells flapping behind; then its alarm
goes off, the clock rattling and its bells ringing while its hands spin round (the minute hand twice, the hour hand
once, so they're back where they were); then it takes a big hop with a full turn and lands with a wobble, back at
rest as the clip comes round.

A small node tree: a root (the turn towards a three-quarter view, TILT, and the model spec's fit: standing on y = 0,
centred, the largest side 1 m) holding the clock, its origin at the bottom of its rim so it squashes onto the floor,
and the clock holding its bells (origins at their bases) and hands (origins on the face's middle). The rest pose's
bounds are the clock's.

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
from clip import Pose, bump, hop, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import export, material, triangles  # noqa: E402

RADIUS = 1.0
BACK, LIP, FACE = 0.28, -0.30, -0.24   # depths (y, the front towards -y): the back, the lip's top, the face
SEGMENTS = 64
BELL_ANGLE = 42.0                      # degrees from the top
HANDS = {                              # (angle clockwise from 12, length, half width at the middle and at the tip, depth)
    "hour": (-62.0, 0.40, 0.065, 0.055, -0.252),
    "minute": (68.0, 0.54, 0.055, 0.045, -0.267),
}
KNOB_ANGLE = 78.0                      # degrees clockwise from the top
TILT = (-16.0, 10.0)                   # degrees: yaw (its right side nearer), pitch (its face up)
FPS, LENGTH = 30, 180
COLOURS = dict(red="#D8252B", cream="#F0E3C4", yellow="#F4B41C")
ROUGHNESS = dict(red=0.4, cream=0.65, yellow=0.4)
NAMES = ["red", "cream", "yellow"]


# ---- Geometry --------------------------------------------------------------------------------------------------------

def arc(cx, cy, r, a0, a1, steps):
    """Points on a circle about (cx, cy) in the (r, y) profile plane, from angle a0 to a1 in degrees."""
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


def disc_frame(depth):
    """The frame for a revolve about the clock's own axis (its depth, y), h along -y from depth."""
    return Matrix.Translation((0, depth, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")


def body():
    """The drum, the face, the cap and the knob, the clock's middle at (0, 0, RADIUS) so its origin is its bottom."""
    bm = bmesh.new()
    r = RADIUS
    # The profile from the middle of the back, round the rim and the lip, then the face to its middle: h is -y.
    profile = [((0.0, -BACK), "red")]
    profile += [(p, "red") for p in arc(0.80, -BACK + 0.20, 0.20, -90, 0, 6)]
    profile += [(p, "red") for p in arc(0.82, -LIP - 0.18, 0.18, 0, 90, 6)]
    profile += [((0.76, -LIP), "red"), ((0.74, -LIP - 0.02), "red"), ((0.73, -FACE), "cream"),
                ((0.45, -FACE), "cream"), ((0.0, -FACE), "cream")]
    centre = Matrix.Translation((0, 0, r))
    revolve(bm, [((p[0] * r, p[1]), m) for p, m in profile], centre @ Matrix.Rotation(math.radians(90), 4, "X"))
    # The cap over the hands' middle.
    cap = [((0.0, 0.25), "red"), ((0.075, 0.25), "red"), ((0.075, 0.285), "red"), ((0.06, 0.298), "red"), ((0.0, 0.3), "red")]
    revolve(bm, cap, centre @ Matrix.Rotation(math.radians(90), 4, "X"), 24)
    # The knob, standing out of the rim on the right.
    knob = Matrix.Rotation(math.radians(KNOB_ANGLE), 4, "Y")
    stem = [((0.0, 0.9), "yellow"), ((0.055, 0.9), "yellow"), ((0.055, 1.08), "yellow"), ((0.1, 1.09), "yellow"),
            ((0.1, 1.15), "yellow"), ((0.08, 1.17), "yellow"), ((0.0, 1.17), "yellow")]
    revolve(bm, [((a * r, b * r), m) for (a, b), m in stem], centre @ knob, 20)
    return finish("clock", bm, sharp=40)


def bell():
    """A bell, its base's middle at its origin, its dome along +z: a cap with a flared lip, on a short neck."""
    bm = bmesh.new()
    profile = [((0.0, -0.16), "yellow"), ((0.055, -0.16), "yellow"), ((0.055, 0.0), "yellow"), ((0.27, 0.0), "yellow"),
               ((0.33, 0.015), "yellow"), ((0.335, 0.05), "yellow")]
    profile += [((0.30 * math.sin(math.radians(a)), 0.05 + 0.25 * math.cos(math.radians(a))), "yellow")
                for a in range(80, -1, -10)]
    revolve(bm, [((a * RADIUS, b * RADIUS), m) for (a, b), m in profile], Matrix.Identity(4), 32)
    return finish("bell", bm, sharp=50)


def hand(name):
    """A hand, its pivot at its origin, pointing up (+z), its front facing -y: a tapered bar rounded at both ends."""
    _, length, w0, w1, _ = HANDS[name]
    bm = bmesh.new()
    tail = 0.08 * RADIUS
    outline = [(w1 * math.cos(math.radians(a)), length + w1 * math.sin(math.radians(a))) for a in range(0, 181, 15)]
    outline += [(w0 * math.cos(math.radians(a)), -tail + w0 * math.sin(math.radians(a))) for a in range(180, 361, 15)]
    front = [bm.verts.new((x, -0.008, z)) for x, z in outline]
    back = [bm.verts.new((x, 0.008, z)) for x, z in outline]
    faces = [list(reversed(front)), back]
    faces += [[front[j], front[(j + 1) % len(front)], back[(j + 1) % len(back)], back[j]] for j in range(len(front))]
    for f in faces:
        face = bm.faces.new(f)
        face.smooth = False
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

HOPS = [(8, 24, 0.42), (30, 46, 0.38), (52, 68, 0.34)]  # (take-off, landing, height in radii)
ALARM = (80, 134)
LEAP = (146, 168, 0.75)


def timeline(f):
    z = squash = roll = spin = flap = 0.0
    x = 0.0
    for i, (f0, f1, height) in enumerate(HOPS):
        z += hop(f, f0, f1, height)
        squash += 0.16 * bump(f, f0 - 6, f0 + 1) - 0.14 * bump(f, f0, f0 + 10) + wobble(f, f1, 0.2, 9, 5)
        roll += (7 if i % 2 == 0 else -7) * bump(f, f0, f1)
        flap += -10 * bump(f, f0, f0 + 8) + wobble(f, f1 + 1, 20, 8, 5)

    # The alarm: the clock rattles (a quick rock and a jitter off the floor), the bells ring, the hands spin.
    a0, a1 = ALARM
    ringing = smooth(phase(f, a0, a0 + 4)) * (1 - smooth(phase(f, a1 - 6, a1)))
    t = f - a0
    roll += 4.5 * math.sin(2 * math.pi * t / 4) * ringing
    x += 0.025 * math.sin(2 * math.pi * t / 4 + 1.3) * ringing
    z += 0.035 * abs(math.sin(math.pi * t / 4)) * ringing
    squash += 0.04 * math.sin(2 * math.pi * t / 8) * ringing
    ring = 14 * math.sin(2 * math.pi * t / 3) * ringing
    turn = smooth(phase(f, a0 + 2, a1 - 2))

    # The big leap with a full turn, and a wobble that has died away when the clip comes round.
    l0, l1, height = LEAP
    settle = 1 - smooth(phase(f, LENGTH - 10, LENGTH))
    z += hop(f, l0, l1, height)
    spin += 360 * smooth(phase(f, l0, l1))
    squash += 0.2 * bump(f, l0 - 8, l0 + 1) - 0.16 * bump(f, l0, l0 + 12) + wobble(f, l1, 0.22, 9, 4.5) * settle
    flap += -12 * bump(f, l0, l0 + 10) + wobble(f, l1 + 1, 24, 8, 4.5) * settle

    return {
        "clock": Pose(x=x, z=z, spin=spin, roll=roll, squash=squash),
        "bell_l": Pose(roll=-flap + ring),
        "bell_r": Pose(roll=flap - ring),
        "minute": Pose(roll=720 * turn),
        "hour": Pose(roll=360 * turn),
    }


# ---- Main ------------------------------------------------------------------------------------------------------------

MATS = {}


def main():
    out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    MATS.update({n: material(n, COLOURS[n], ROUGHNESS[n]) for n in NAMES})

    clock = body()
    nodes = {"clock": clock}
    centre = Vector((0, 0, RADIUS))
    for name, side in (("bell_l", -1), ("bell_r", 1)):
        part = bell()
        part.name = part.data.name = name
        part.parent = clock
        tilt = Quaternion((0, 1, 0), math.radians(side * BELL_ANGLE))
        part.rotation_mode = "QUATERNION"
        part.rotation_quaternion = tilt
        part.location = centre + tilt @ Vector((0, 0.02, 1.04 * RADIUS))
        nodes[name] = part
    for name, (angle, _, _, _, depth) in HANDS.items():
        part = hand(name)
        part.parent = clock
        part.rotation_mode = "QUATERNION"
        part.rotation_quaternion = Quaternion((0, 1, 0), math.radians(angle))
        part.location = centre + Vector((0, depth, 0))
        nodes[name] = part

    # The three-quarter view, then the spec's fit of the clock at rest, as the root's transform.
    root = bpy.data.objects.new("recently_played_root", None)
    scene.collection.objects.link(root)
    clock.parent = root
    bpy.context.view_layer.update()
    yaw, pitch = TILT
    tilt = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
    meshes = [clock, nodes["bell_l"], nodes["bell_r"], nodes["hour"], nodes["minute"]]
    points = [tilt @ o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) @ tilt

    key("focused", nodes, timeline, LENGTH)
    print(f"Alarm clock: {sum(triangles(o.data) for o in meshes)} triangles, {len(NAMES)} materials, "
          f"size {size.x:.2f} x {size.y:.2f} x {size.z:.2f} tilted, before the fit")
    export([root] + meshes, out, animations=True)


main()
