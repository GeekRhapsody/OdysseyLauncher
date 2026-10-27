"""The console theme's Symbian system model (godot/themes/console/models/systems/symbian.glb): an unbranded two-way
slider phone of the late 2000s, standing up.

Built in Blender with handheld.py's pieces (symbian_layout.py has the measurements, after the Nokia N95): two halves,
each a slab with rounded edges: the back half (its front printed with the keypad and the media keys, its back plum with
the camera's silver ring) and the face in front of it (silver: the navi cluster's chrome ring and five-way key standing
on it, the screens on its window). The printing is two textures drawn by symbian_print.py (the face, the keypad, the
back, swatches; the screens).

A node tree (card.finish()): the root holding the back half; the back half holding the face (sliding up and down on it),
the face holding the screens (each shrunk to nothing until it's shown).

The `focused` clip (8 s, looping): the standby screen, the menu with a made-up game among its icons; the face slides up
to show the keypad, the game's title, and the game played; the face slides back down, the standby screen, and dark.

Three materials (case, glass, metal) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/symbian_print.py artifacts/made-up-games artifacts/symbian
    blender -b --factory-startup --python tools/console-models/symbian.py -- artifacts/symbian godot/themes/console/models/systems/symbian.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handheld as H  # noqa: E402
import symbian_layout as L  # noqa: E402
from amiga import rounded  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import Pose, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.4, glass=0.25, metal=0.25)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
KEYPAD = H.face_uv(ATLAS, "keypad", L.SPAN)
BACK = H.back_uv(ATLAS, "back", L.SPAN)
SCREENS = ("standby", "menu", "title", "game1", "game2")


def outline():
    return rounded(0.0, L.HEIGHT / 2, L.WIDTH, L.HEIGHT, L.CORNER, 6)


def back_half(m):
    part = H.body("symbian", outline(), L.DEPTH - L.FACE_DEPTH, m["case"], front=0.6, back=3.0)
    part.data.transform(Matrix.Translation((0.0, L.FACE_DEPTH + 0.2, 0.0)))
    coloured(part, m["case"], ATLAS, "plum")
    H.paint_face(part, m["case"], KEYPAD)
    H.paint_face(part, m["case"], BACK, lambda c, n, kind: n.y > 0.9)
    x, z = L.LENS["at"]
    r = L.LENS["r"]
    ring = lathe("lens", [(r - 3.0, -0.3), (r, -0.3), (r, L.LENS["proud"] - 0.4), (r - 0.6, L.LENS["proud"]),
                          (r - 2.4, L.LENS["proud"]), (r - 3.0, L.LENS["proud"] - 0.6), (0.0, L.LENS["proud"] - 0.8)],
                 m["metal"], 32)
    ring.data.transform(Matrix.Translation((x, L.DEPTH, z)) @ Matrix.Rotation(math.radians(-90.0), 4, "X"))
    return smoothed(join([part, ring], "symbian"), 40.0)


def face(m):
    part = H.body("face", outline(), L.FACE_DEPTH, m["case"], front=2.5, back=0.6)
    coloured(part, m["case"], ATLAS, "plum")
    H.paint_face(part, m["case"], FACE)
    (nx, nz), (nw, nh) = L.NAVI["at"], L.NAVI["size"]
    ring = plate("navi", rounded(nx, nz, nw, nh, 6.0, 5), -0.6, 0.4, m["case"])
    bevel(ring, 0.4, segments=1, angle=50)
    coloured(ring, m["case"], ATLAS, "chrome")
    H.paint_face(ring, m["case"], FACE)
    p = L.NAVI["pad"]
    pad = plate("pad", rounded(nx, nz, p, p, 3.0, 4), -1.6, 0.0, m["case"])
    bevel(pad, 0.6, segments=2, angle=50)
    coloured(pad, m["case"], ATLAS, "key")
    centre = plate("centre", rounded(nx, nz, L.NAVI["centre"], L.NAVI["centre"], 1.2, 3), -2.2, -1.0, m["case"])
    bevel(centre, 0.3, segments=1, angle=50)
    coloured(centre, m["case"], ATLAS, "chrome")
    return smoothed(join([part, ring, pad, centre], "face"), 40.0)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def showing(f):
    if 16 <= f < 50 or 196 <= f < 214:
        return "standby"
    if 50 <= f < 88:
        return "menu"
    if 88 <= f < 110:
        return "title"
    if 110 <= f < 196:
        return "game1" if ((f - 110) // 10) % 2 == 0 else "game2"
    return None


def timeline(f):
    poses = showing_poses(SCREENS, showing, f)
    up = smooth(phase(f, 80, 90)) * (1 - smooth(phase(f, 184, 194)))
    poses["face"] = Pose(z=L.SLIDE * up)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", metal=L.COLOURS["chrome"]), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "symbian_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "symbian_media.png"))))

    whole = back_half(m)
    parts = {"face": (face(m), Vector())}
    sw, sh = L.SCREEN["size"]
    wx, wz = L.WINDOW["at"]
    for name, (part, at) in H.screens(SCREENS, sw, sh, MEDIA, m["glass"], (wx, -0.05, wz)).items():
        parts[name] = (part, at, "face")
    finish("symbian", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Symbian phone")


if __name__ == "__main__":
    main()
