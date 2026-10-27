"""The console theme's Android system model (godot/themes/console/models/systems/android.glb): an unbranded Android
phone of the 2020s on a desk stand.

Built in Blender with handheld.py's pieces (android_layout.py has the measurements, after the mid-range slabs): the
phone's slab, its glass face's edge rounded, its frame and its back; the three lenses' raised rings and the flash on its
back, the volume rocker and the power key on its right side, the punch hole in its screen; the screens on its glass.
The stand: a base, a lip in front of the phone and a back leaning behind it. The printing is two textures drawn by
android_print.py (the face, the back, swatches; the screens).

A node tree (card.finish()): the root holding the stand; the stand holding the phone (its middle at its origin), the
phone holding its screens (each shrunk to nothing until it's shown).

The `focused` clip (8 s, looping): the phone wakes to its lock screen, then its home screen of made-up apps; it turns
landscape on the stand for a made-up game's title and two moments of it, turns back to the home screen and goes dark.

Three materials (case, glass, metal) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/android_print.py artifacts/made-up-games artifacts/android
    blender -b --factory-startup --python tools/console-models/android.py -- artifacts/android godot/themes/console/models/systems/android.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import android_layout as L  # noqa: E402
import handheld as H  # noqa: E402
from amiga import rounded  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import Pose, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.35, glass=0.2, metal=0.25)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
BACK = H.back_uv(ATLAS, "back", L.SPAN)
SCREENS = ("lock", "home", "title", "game1", "game2")
FOOT = L.STAND["base"][2] + 0.6                            # the phone's bottom edge, on the stand
CENTRE = Vector((0.0, L.DEPTH / 2, L.HEIGHT / 2))          # the phone's middle, in its own frame


def phone(m):
    """The phone in its own frame (its bottom edge's middle on the face at the origin), moved to have its middle at
    its origin."""
    body = H.body("phone", rounded(0.0, L.HEIGHT / 2, L.WIDTH, L.HEIGHT, L.CORNER, 6), L.DEPTH, m["case"], front=1.0,
                  back=1.6, steps=2)
    coloured(body, m["case"], ATLAS, "frame")
    H.paint_face(body, m["case"], FACE)
    H.paint_face(body, m["case"], BACK, lambda c, n, kind: n.y > 0.9)
    parts = [body]
    for z in L.LENSES["z"]:
        r = L.LENSES["r"]
        ring = lathe("lens", [(L.LENSES["glass"], -0.4), (r, -0.4), (r, L.LENSES["proud"] - 0.3),
                              (r - 0.6, L.LENSES["proud"]), (L.LENSES["glass"] + 0.4, L.LENSES["proud"]),
                              (L.LENSES["glass"], L.LENSES["proud"] - 0.4), (0.0, L.LENSES["proud"] - 0.6)],
                     m["metal"], 32)
        ring.data.transform(Matrix.Translation((L.LENSES["x"], L.DEPTH, z)) @ Matrix.Rotation(math.radians(-90.0), 4, "X"))
        glass = lathe("lens_glass", [(0.0, L.LENSES["proud"] - 0.5), (L.LENSES["glass"], L.LENSES["proud"] - 0.5),
                                     (L.LENSES["glass"], L.LENSES["proud"] - 0.45), (0.0, L.LENSES["proud"] - 0.4)],
                      m["case"], 24)
        glass.data.transform(Matrix.Translation((L.LENSES["x"], L.DEPTH, z)) @ Matrix.Rotation(math.radians(-90.0), 4, "X"))
        parts += [ring, coloured(glass, m["case"], ATLAS, "lens")]
    for (z0, z1) in (L.KEYS["volume"], L.KEYS["power"]):
        key = box("key", L.WIDTH / 2 - 0.6, L.WIDTH / 2 + L.KEYS["proud"], L.DEPTH / 2 - L.KEYS["height"] / 2,
                  L.DEPTH / 2 + L.KEYS["height"] / 2, z0, z1, m["case"])
        bevel(key, 0.4, segments=1)
        parts.append(coloured(key, m["case"], ATLAS, "key"))
    punch = plate("punch", H.circle(*L.PUNCH["at"], L.PUNCH["r"], 20), -0.9, -0.2, m["case"])
    parts.append(coloured(punch, m["case"], ATLAS, "glass"))
    whole = join(parts, "phone")
    whole.data.transform(Matrix.Translation(-CENTRE))
    return smoothed(whole, 40.0)


def stand(m):
    """The stand: its base, the lip in front of the phone, the back leaning behind it."""
    bw, bd, bh = L.STAND["base"]
    base = box("stand", -bw / 2, bw / 2, -14.0, bd - 14.0, 0.0, bh, m["case"])
    bevel(base, 2.0, segments=2)
    lw, ld, lh = L.STAND["lip"]
    lip = box("lip", -lw / 2, lw / 2, -ld - 0.6, -0.6, bh - 0.5, bh + lh, m["case"])
    bevel(lip, 1.6, segments=2)
    rw, rd, rh = L.STAND["rest"]
    rest = box("rest", -rw / 2, rw / 2, 0.0, rd, 0.0, rh, m["case"])
    bevel(rest, 1.6, segments=2)
    rest.data.transform(Matrix.Translation((0.0, L.DEPTH + L.STAND["gap"], bh - 1.0))
                        @ Matrix.Rotation(math.radians(-L.STAND["lean"]), 4, "X"))
    return smoothed(coloured(join([base, lip, rest], "stand"), m["case"], ATLAS, "stand"), 40.0)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def showing(f):
    if 22 <= f < 52:
        return "lock"
    if 52 <= f < 90 or 186 <= f < 206:
        return "home"
    if 90 <= f < 108:
        return "title"
    if 108 <= f < 186:
        return "game1" if ((f - 108) // 10) % 2 == 0 else "game2"
    return None


def timeline(f):
    poses = showing_poses(SCREENS, showing, f)
    turn = smooth(phase(f, 90, 106)) * (1 - smooth(phase(f, 184, 200)))
    lift = math.sin(math.pi * phase(f, 90, 106)) + math.sin(math.pi * phase(f, 184, 200))
    poses["phone"] = Pose(z=-L.LANDSCAPE_DROP * turn + 14.0 * lift, y=-8.0 * lift, roll=-90.0 * turn)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", metal=L.COLOURS["metal"]), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "android_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "android_media.png"))))

    whole = stand(m)
    parts = {"phone": (phone(m), Vector((0.0, L.DEPTH / 2, FOOT + L.HEIGHT / 2)))}
    sw, sh = L.SCREEN["size"]
    sx, sz = L.SCREEN["at"]
    for name, (part, at) in H.screens(SCREENS, sw, sh, MEDIA, m["glass"], (sx, -0.05, sz)).items():
        parts[name] = (part, at - CENTRE, "phone")
    finish("android", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Android phone")


if __name__ == "__main__":
    main()
