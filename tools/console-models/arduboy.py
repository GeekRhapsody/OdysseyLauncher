"""The console theme's Arduboy system model (godot/themes/console/models/systems/arduboy.glb): the Arduboy, standing up.

Built in Blender with handheld.py's pieces (arduboy_layout.py has the measurements, from photographs): the credit-card
slab, its edges rounded, its face printed with the white board as it shows through the clear plate, its edge
grey-green, white and aluminium by its layers, its back brushed aluminium; the OLED's black glass and the screens in it,
the four black D-pad keys, A and B in red, the brass screws' heads, the power slide on the top edge. The printing is two
textures drawn by arduboy_print.py (the face, the back, swatches; the screens).

A node tree (card.finish()): the root holding the set; the set holding the power slide, the screens (each shrunk to
nothing until it's shown), the D-pad's keys, A and B.

The `focused` clip (8 s, looping): the slide goes over, the ARDUBOY logo comes up on the screen, a made-up
game's title, and the game played on the D-pad, A and B; then the slide goes back and the screen goes dark.

Three materials (case, glass, metal) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/arduboy_print.py artifacts/made-up-games artifacts/arduboy
    blender -b --factory-startup --python tools/console-models/arduboy.py -- artifacts/arduboy godot/themes/console/models/systems/arduboy.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arduboy_layout as L  # noqa: E402
import handheld as H  # noqa: E402
from amiga import paint, rounded  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical
TILT_PITCH = 14.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.2, glass=0.25, metal=0.35)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
BACK = H.back_uv(ATLAS, "back", L.SPAN)
SCREENS = ("boot", "title", "game1", "game2")


def slab(m):
    outline = rounded(0.0, L.HEIGHT / 2, L.WIDTH, L.HEIGHT, L.CORNER, 5)
    part = H.body("arduboy", outline, L.DEPTH, m["case"], front=1.2, back=0.6, steps=2)
    coloured(part, m["case"], ATLAS, "board")
    paint(part, m["case"], ATLAS.swatch("plate"), lambda c, n, kind: n.y <= 0.9 and c.y < L.LAYERS["plate"])
    paint(part, m["case"], ATLAS.swatch("aluminium"), lambda c, n, kind: n.y <= 0.9 and c.y > L.LAYERS["board"])
    paint(part, m["case"], FACE, lambda c, n, kind: n.y < -0.9)
    paint(part, m["case"], BACK, lambda c, n, kind: n.y > 0.9)
    return part


def oled(m):
    w, h = L.OLED["glass"]
    x, z = L.OLED["at"]
    part = plate("oled", rounded(x, z, w, h, 1.0, 2), -0.35, 0.2, m["case"])
    return coloured(part, m["case"], ATLAS, "glass")


def screws(m):
    out = []
    for x, z in L.SCREWS:
        head = lathe("screw", [(0.0, -0.1), (1.9, -0.1), (1.9, 0.4), (1.5, 0.8), (0.0, 0.9)], m["metal"], 16)
        head.data.transform(Matrix.Translation((x, 0.0, z)) @ Matrix.Rotation(math.radians(90.0), 4, "X"))
        out.append(head)
    return out


def key(name, m):
    k = L.DPAD["key"]
    part = plate(name, rounded(0.0, 0.0, k, k, 1.8, 3), -1.6, 0.3, m["case"])
    bevel(part, 0.6, segments=2, angle=50)
    return coloured(part, m["case"], ATLAS, "black")


def button(name, m):
    r = L.BUTTONS["r"]
    part = lathe(name, [(0.0, -0.3), (r, -0.3), (r, 0.6), (r * 0.85, 1.4), (0.0, 1.7)], m["case"], 24)
    part.data.transform(Matrix.Rotation(math.radians(90.0), 4, "X"))
    return coloured(part, m["case"], ATLAS, "red")


def slide(m):
    w, t, h = L.SWITCH["size"]
    x, y = L.SWITCH["at"]
    part = box("slide", x - w / 2, x + w / 2, y - t / 2, y + t / 2, L.HEIGHT - 0.5, L.HEIGHT + h, m["case"])
    bevel(part, 0.5, segments=2)
    return coloured(part, m["case"], ATLAS, "black")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 30 <= f < 82:
        return "boot"
    if 82 <= f < 104:
        return "title"
    if 104 <= f < 196:
        return "game1" if ((f - 104) // 8) % 2 == 0 else "game2"
    return None


KEYS = dict(up=(0.0, 1.0), down=(0.0, -1.0), left=(-1.0, 0.0), right=(1.0, 0.0))
PRESSES = dict(up=(112, 150), down=(126, 170), left=(118, 160), right=(132, 142, 178), button_a=(98, 138, 166),
               button_b=(108, 154, 184))


def timeline(f):
    on = smooth(phase(f, 20, 26)) * (1 - smooth(phase(f, 198, 204)))
    poses = showing_poses(SCREENS, showing, f)
    poses["slide"] = Pose(x=L.SWITCH["travel"] * on)
    for name, frames in PRESSES.items():
        poses[name] = Pose(y=1.0 * max(tap(f, f0) for f0 in frames))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", metal=L.COLOURS["brass"]), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "arduboy_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "arduboy_media.png"))))

    whole = smoothed(join([slab(m), oled(m)] + screws(m), "arduboy"), 40.0)
    dx, dz = L.DPAD["at"]
    parts = {"slide": (smoothed(slide(m)), Vector())}
    for name, (ux, uz) in KEYS.items():
        parts[name] = (smoothed(key(name, m), 40.0), Vector((dx + ux * L.DPAD["pitch"], 0.0, dz + uz * L.DPAD["pitch"])))
    for name in ("a", "b"):
        x, z = L.BUTTONS[name]
        parts["button_" + name] = (smoothed(button("button_" + name, m), 50.0), Vector((x, 0.0, z)))
    sw, sh = L.OLED["screen"]
    x, z = L.OLED["at"]
    parts.update(H.screens(SCREENS, sw, sh, MEDIA, m["glass"], (x, -0.4, z + 1.0)))
    finish("arduboy", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Arduboy")


if __name__ == "__main__":
    main()
