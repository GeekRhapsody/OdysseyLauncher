"""The console theme's N-Gage system model (godot/themes/console/models/systems/ngage.glb): Nokia's N-Gage, the first
one, standing up.

Built in Blender with handheld.py's pieces (ngage_layout.py has the measurements, from Nokia's figures and photographs):
the shell from its outline (smoothed: the straight top, the rounded ends, the deep curve under), its edges rounded, its
back rounded more; the black bezel standing a little off its face, the screens over its window; the D-pad's disc, every
key a rounded plate turned as it fans round the screen, the power key on the top edge. The printing is two textures
drawn by ngage_print.py (the face, the back, swatches; the screens).

A node tree (card.finish()): the root holding the set; the set holding the power key, the screens (each shrunk to
nothing until it's shown), the D-pad and the keys the game is played on (2, 5, 7, 8).

The `focused` clip (8 s, looping): the power key, NOKIA's start-up, the games menu, the made-up game's title, 5 to start
it, and the game played on the D-pad, 5 and 7; then the power key again and the screen goes dark.

Three materials (case, glass, metal) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/ngage_print.py artifacts/made-up-games artifacts/ngage
    blender -b --factory-startup --python tools/console-models/ngage.py -- artifacts/ngage godot/themes/console/models/systems/ngage.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handheld as H  # noqa: E402
import ngage_layout as L  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, join  # noqa: E402
from props import lathe  # noqa: E402
from saturn import smooth_outline  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.45, glass=0.3, metal=0.3)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
BACK = H.back_uv(ATLAS, "back", L.SPAN)
SCREENS = ("boot", "menu", "title", "game1", "game2")


def shell(m):
    part = H.body("ngage", smooth_outline(L.OUTLINE, 4), L.DEPTH, m["case"], front=3.0, back=7.0)
    coloured(part, m["case"], ATLAS, "frame")
    paint_back = lambda c, n, kind: n.y > 0.5                                         # noqa: E731
    H.paint_face(part, m["case"], BACK, paint_back)
    H.paint_face(part, m["case"], FACE)
    return part


def bezel(m):
    part = plate("bezel", L.bezel_outline(), -0.5, 0.4, m["case"])
    bevel(part, 0.3, segments=1, angle=50)
    coloured(part, m["case"], ATLAS, "bezel")
    return H.paint_face(part, m["case"], FACE)


def key(name, kx, kz, w, h, turn, m):
    part = plate("key_" + name, L.turned_rect(0.0, 0.0, w, h, turn), -1.8, 0.4, m["case"])
    bevel(part, 0.6, segments=2, angle=50)
    coloured(part, m["case"], ATLAS, "key")
    part.data.transform(Matrix.Translation((kx, 0.0, kz)))
    H.paint_face(part, m["case"], FACE)
    part.data.transform(Matrix.Translation((-kx, 0.0, -kz)))
    return part


def dpad(m):
    x, z = L.DPAD["at"]
    r = L.DPAD["r"]
    part = lathe("dpad", [(0.0, -0.5), (r, -0.5), (r, 1.2), (r - 1.2, 2.0), (0.0, 2.3)], m["case"], 40)
    part.data.transform(Matrix.Translation((x, 0.0, z)) @ Matrix.Rotation(math.radians(90.0), 4, "X"))
    coloured(part, m["case"], ATLAS, "disc")
    H.paint_face(part, m["case"], FACE, lambda c, n, kind: n.y < -0.4)
    part.data.transform(Matrix.Translation((-x, 0.0, -z)))
    return part


def power(m):
    x, y = L.POWER["at"]
    part = lathe("power", [(0.0, -0.5), (L.POWER["r"], -0.5), (L.POWER["r"], 0.6), (L.POWER["r"] - 0.6, 1.2),
                           (0.0, 1.3)], m["metal"], 20)
    return part, Vector((x, y, L.HEIGHT - 0.6))


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 26 <= f < 58:
        return "boot"
    if 58 <= f < 84:
        return "menu"
    if 84 <= f < 102:
        return "title"
    if 102 <= f < 196:
        return "game1" if ((f - 102) // 8) % 2 == 0 else "game2"
    return None


PRESSES = {"5": (98, 124, 148, 172), "7": (114, 138, 162, 184), "2": (76,), "8": (68,)}


def timeline(f):
    poses = showing_poses(SCREENS, showing, f)
    poses["power"] = Pose(z=-0.8 * max(tap(f, 18, 4), tap(f, 194, 4)))
    for name, frames in PRESSES.items():
        poses["key_" + name] = Pose(y=1.2 * max(tap(f, f0) for f0 in frames))
    t = phase(f, 104, 190)
    wave = math.sin(math.pi * t)
    poses["dpad"] = Pose(pitch=7.0 * math.sin(2 * math.pi * 4 * t) * wave, spin=7.0 * math.sin(2 * math.pi * 3 * t + 0.8)
                         * wave)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", metal="#9A9CA0"), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "ngage_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "ngage_media.png"))))

    fixed, parts = [], {}
    for name, kx, kz, w, h, turn, _ in L.KEYS:
        part = smoothed(key(name, kx, kz, w, h, turn, m), 40.0)
        if name in L.PLAYED:
            parts["key_" + name] = (part, Vector((kx, 0.0, kz)))
        else:
            part.data.transform(Matrix.Translation((kx, 0.0, kz)))
            fixed.append(part)
    whole = smoothed(join([shell(m), bezel(m)] + fixed, "ngage"), 40.0)
    button, at = power(m)
    parts["power"] = (smoothed(button, 50.0), at)
    parts["dpad"] = (smoothed(dpad(m), 40.0), Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1])))
    sw, sh = L.SCREEN["size"]
    sx, sz = L.SCREEN["at"]
    parts.update(H.screens(SCREENS, sw, sh, MEDIA, m["glass"], (sx, -0.55, sz)))
    finish("ngage", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "N-Gage")


if __name__ == "__main__":
    main()
