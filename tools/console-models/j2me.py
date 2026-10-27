"""The console theme's J2ME system model (godot/themes/console/models/systems/j2me.glb): an unbranded keypad phone of
the 2000s, standing up.

Built in Blender with handheld.py's pieces (j2me_layout.py has the measurements, after the Nokia 6230): the dark shell,
its edges rounded; the silver front plate standing on its face, the blank earpiece badge raised on the plate; the keys,
each a rounded plate standing on it, printed; the screens on the window. The printing is two textures drawn by
j2me_print.py (the face, swatches; the screens).

A node tree (card.finish()): the root holding the set; the set holding the screens (each shrunk to nothing until it's
shown) and the keys the clip presses.

The `focused` clip (8 s, looping): the idle screen; Menu (the left soft key), the navi key to Games, the made-up game's
title, 5 to start it, and the game played on 2, 4, 6, 8 and 5; then the screen goes dark.

Three materials (case, glass, dark) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/j2me_print.py artifacts/made-up-games artifacts/j2me
    blender -b --factory-startup --python tools/console-models/j2me.py -- artifacts/j2me godot/themes/console/models/systems/j2me.glb
"""

import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handheld as H  # noqa: E402
import j2me_layout as L  # noqa: E402
from amiga import rounded  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import Pose, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, join  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.4, glass=0.25, dark=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
SCREENS = ("idle", "menu", "games", "title", "game1", "game2")


def plate_outline():
    p = L.PLATE
    z0, z1 = p["z"]
    return rounded(0.0, (z0 + z1) / 2, 2 * p["x"], z1 - z0, p["top"], 6)


def shell(m):
    body = H.body("j2me", rounded(0.0, L.HEIGHT / 2, L.WIDTH, L.HEIGHT, 9.0, 6), L.DEPTH, m["case"], front=4.0,
                  back=5.0)
    coloured(body, m["case"], ATLAS, "shell")
    H.paint_face(body, m["case"], FACE)
    front = plate("plate", plate_outline(), -L.PLATE["proud"], 0.5, m["case"])
    bevel(front, 0.5, segments=2, angle=50)
    coloured(front, m["case"], ATLAS, "plate")
    H.paint_face(front, m["case"], FACE)
    (bw, bh), (bx, bz) = L.BADGE["size"], L.BADGE["at"]
    badge = plate("badge", rounded(bx, bz, bw, bh, 3.0, 4), -L.BADGE["proud"], 0.0, m["case"])
    bevel(badge, 0.8, segments=2, angle=50)
    coloured(badge, m["case"], ATLAS, "plate")
    return [body, front, badge]


def key(name, x, z, w, h, m):
    part = plate("key_" + name, rounded(0.0, 0.0, w, h, 1.0, 3), -L.PLATE["proud"] - 1.4, -0.2, m["case"])
    bevel(part, 0.5, segments=2, angle=50)
    coloured(part, m["case"], ATLAS, "key")
    part.data.transform(Matrix.Translation((x, 0.0, z)))
    H.paint_face(part, m["case"], FACE)
    part.data.transform(Matrix.Translation((-x, 0.0, -z)))
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 12 <= f < 40:
        return "idle"
    if 40 <= f < 62:
        return "menu"
    if 62 <= f < 84:
        return "games"
    if 84 <= f < 104:
        return "title"
    if 104 <= f < 200:
        return "game1" if ((f - 104) // 10) % 2 == 0 else "game2"
    return None


PRESSES = {"soft_left": (36,), "navi": (56, 78), "5": (100, 132, 168), "2": (112, 150), "4": (120, 176),
           "6": (140, 184), "8": (158,)}


def timeline(f):
    poses = showing_poses(SCREENS, showing, f)
    for name, frames in PRESSES.items():
        poses["key_" + name] = Pose(y=1.0 * max(tap(f, f0) for f0 in frames))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", dark="#141416"), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "j2me_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "j2me_media.png"))))

    fixed, parts = [], {}
    for name, x, z, w, h, _, _ in L.KEYS:
        part = smoothed(key(name, x, z, w, h, m), 40.0)
        if name in L.PLAYED:
            parts["key_" + name] = (part, Vector((x, 0.0, z)))
        else:
            part.data.transform(Matrix.Translation((x, 0.0, z)))
            fixed.append(part)
    whole = smoothed(join(shell(m) + fixed, "j2me"), 40.0)
    sw, sh = L.SCREEN["size"]
    wx, wz = L.WINDOW["at"]
    parts.update(H.screens(SCREENS, sw, sh, MEDIA, m["glass"], (wx, -L.PLATE["proud"] - 0.02, wz)))
    finish("j2me", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "J2ME phone")


if __name__ == "__main__":
    main()
