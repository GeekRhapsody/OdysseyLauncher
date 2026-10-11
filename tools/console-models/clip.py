"""Easing curves and keying for the console theme's procedural clips (power_star.py, alarm_clock.py).

A clip is a function of the frame giving each animated node's pose; key() samples it on every frame into one action,
a slot per node, so the exporter writes it as one clip named after the action (docs/THEMING.md section 8). Frame 0
must be the rest pose: it's what the exported nodes keep, and what an unfocused card shows.
"""

import math

import bpy
from mathutils import Quaternion, Vector

HIDDEN = 0.001  # the scale of a part that isn't there


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
    """A damped spring from frame f0: amount first, then the other way, dying away."""
    t = f - f0
    return 0.0 if t < 0 else amount * math.exp(-t / decay) * math.sin(2 * math.pi * t / period)


def hop(f, f0, f1, height):
    """A parabola from f0 to f1, height at its top."""
    t = phase(f, f0, f1)
    return height * 4 * t * (1 - t)


def bump(f, f0, f1):
    """0 outside f0..f1, rising smoothly to 1 at the middle and back."""
    t = phase(f, f0, f1)
    return math.sin(math.pi * t) ** 2


class Pose:
    """One node's pose against its rest: an offset (x right, z up, y away from the viewer, in the node's parent's
    units), turns in degrees (spin about the vertical, roll about the line of sight, pitch about the horizontal, applied
    in that order after its rest rotation) and a scale (uniform, a squash along its vertical keeping its volume, and a
    free factor per axis)."""

    def __init__(self, x=0.0, y=0.0, z=0.0, spin=0.0, roll=0.0, pitch=0.0, scale=1.0, squash=0.0, axes=(1.0, 1.0, 1.0)):
        self.offset = Vector((x, y, z))
        self.spin, self.roll, self.pitch = spin, roll, pitch
        self.scale, self.squash, self.axes = scale, squash, axes

    def rotation(self):
        q = Quaternion((0, 0, 1), math.radians(self.spin))
        q = Quaternion((0, 1, 0), math.radians(self.roll)) @ q
        return Quaternion((1, 0, 0), math.radians(self.pitch)) @ q

    def scales(self):
        k, s = self.squash, self.scale
        return Vector((s * (1 + k / 2) * self.axes[0], s * (1 + k / 2) * self.axes[1], s * (1 - k) * self.axes[2]))


def key(name, nodes, timeline, length):
    """
    Keys every frame of a clip: nodes maps a part's name to its object, whose current transform is its rest;
    timeline(f) maps part names to Poses. Rotations are applied after the rest rotation, in the parent's axes.
    """
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    action = bpy.data.actions.new(name)
    rests = {}
    for part, obj in nodes.items():
        obj.rotation_mode = "QUATERNION"
        rests[part] = (obj.location.copy(), obj.rotation_quaternion.copy(), obj.scale.copy())
        obj.animation_data_create()
        obj.animation_data.action = action
        if obj.animation_data.action_slot is None:
            obj.animation_data.action_slot = action.slots.new(id_type="OBJECT", name=obj.name)
    last = {}
    for f in range(length + 1):
        poses = timeline(f)
        for part, obj in nodes.items():
            location, rotation, scale = rests[part]
            pose = poses.get(part, Pose())
            obj.location = location + pose.offset
            q = pose.rotation() @ rotation
            if part in last and last[part].dot(q) < 0:
                q.negate()
            last[part] = q
            obj.rotation_quaternion = q
            obj.scale = Vector([a * b for a, b in zip(scale, pose.scales())])
            for path in ("location", "rotation_quaternion", "scale"):
                obj.keyframe_insert(path, frame=f)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 0, length
    scene.frame_set(0)
