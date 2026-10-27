"""The console theme's LCD games system model (godot/themes/console/models/systems/lcdgames.glb): a dedicated LCD
handheld in the classic shell of the late 1980s and 1990s (unbranded), standing up.

Built in Blender with handheld.py's pieces (lcdgames_layout.py has the measurements, from photographs): the white shell,
its edges rounded, the art panel sunk a little inside its rim; the blue bosses standing on its face, the red D-pad's
cross on one and the two action bars on the other, the grey small buttons on their strip, the speaker's grille; the
LCD's screens over its printed backdrop. The printing is two textures drawn by lcdgames_print.py (the face, swatches;
the LCD switched on).

A node tree (card.finish()): the root holding the set; the set holding ON/START, the screens (each shrunk to nothing
until it's shown), the D-pad and the two action bars.

The `focused` clip (8 s, looping): ON/START, and the made-up racing game plays on the LCD's segments, the player's car
moving between the lanes as the D-pad is pressed, the bars pressed; then OFF and the LCD shows its backdrop alone.

Three materials (case, glass, dark) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/lcdgames_print.py artifacts/made-up-games artifacts/lcdgames
    blender -b --factory-startup --python tools/console-models/lcdgames.py -- artifacts/lcdgames godot/themes/console/models/systems/lcdgames.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handheld as H  # noqa: E402
import lcdgames_layout as L  # noqa: E402
from amiga import rounded  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import Pose, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, boolean, join  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.45, glass=0.3, dark=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
SCREENS = ("seg1", "seg2", "seg3", "seg4")
SUNK = 1.0                   # the art panel, back from the rim


def shell(m):
    part = H.body("lcdgames", rounded(0.0, L.HEIGHT / 2, L.WIDTH, L.HEIGHT, L.CORNER, 5), L.DEPTH, m["case"],
                  front=2.5, back=4.0)
    boolean(part, plate("panel", L.PANEL, -2.0, SUNK, m["case"]))
    coloured(part, m["case"], ATLAS, "shell")
    H.paint_face(part, m["case"], FACE, lambda c, n, kind: n.y < -0.9 and kind == "case")
    return part


def bosses(m):
    out = []
    r, h = L.BOSSES["r"], L.BOSSES["height"]
    for name in ("left", "right"):
        boss = plate("boss", H.circle(*L.BOSSES[name], r, 40), -h, 0.5, m["case"])
        bevel(boss, 1.2, segments=2, angle=50)
        out.append(coloured(boss, m["case"], ATLAS, "boss"))
    gx, gz = L.GRILLE["at"]
    gw, gh = L.GRILLE["size"]
    grille = plate("grille", H.stadium(gx, gz, gw, gh), -1.0, 0.5, m["case"])
    bevel(grille, 0.8, segments=2, angle=50)
    boolean(grille, join([plate("slot", H.stadium(gx, gz - gh / 2 + gh * (k + 0.5) / L.GRILLE["slots"], gw - 8.0, 1.2),
                                -2.0, 0.2, m["dark"]) for k in range(L.GRILLE["slots"])], "slots"))
    out.append(coloured(grille, m["case"], ATLAS, "shell"))
    w, hh = L.SMALL["size"]
    for name, x in L.SMALL["names"][:-1]:
        b = plate("small", H.stadium(x, L.STRIP["z"] - 0.5, w, hh), -1.4, 0.4, m["case"])
        bevel(b, 0.6, segments=2, angle=50)
        out.append(coloured(b, m["case"], ATLAS, "grey"))
    return out


def start_button(m):
    w, h = L.SMALL["size"]
    name, x = L.SMALL["names"][-1]
    b = plate("start", H.stadium(0.0, 0.0, w, h), -1.4, 0.4, m["case"])
    bevel(b, 0.6, segments=2, angle=50)
    return coloured(b, m["case"], ATLAS, "grey"), Vector((x, 0.0, L.STRIP["z"] - 0.5))


def dpad(m):
    part = plate("dpad", H.cross(0.0, 0.0, L.CROSS["arm"], L.CROSS["half"]), -2.4, 0.4, m["case"])
    bevel(part, 0.8, segments=2, angle=50)
    x, z = L.BOSSES["left"]
    return coloured(part, m["case"], ATLAS, "red"), Vector((x, -L.BOSSES["height"], z))


def bars(m):
    out = {}
    w, h = L.BARS["size"]
    x, z = L.BOSSES["right"]
    for k, name in enumerate(("bar_a", "bar_b")):
        b = plate(name, H.stadium(0.0, 0.0, w, h, L.BARS["slant"]), -2.4, 0.4, m["case"])
        bevel(b, 0.8, segments=2, angle=50)
        out[name] = (coloured(b, m["case"], ATLAS, "red"),
                     Vector((x, -L.BOSSES["height"], z + (L.BARS["gap"] / 2) * (1 if k == 0 else -1))))
    return out


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 30 <= f < 200:
        return SCREENS[((f - 30) // 14) % 4]
    return None


def timeline(f):
    poses = showing_poses(SCREENS, showing, f)
    poses["start"] = Pose(y=1.0 * tap(f, 24, 3))
    rock = 0.0                                             # the D-pad left and right as the car changes lanes
    for k in range(12):
        f0 = 40 + 14 * k
        rock += (1 if k % 2 else -1) * tap(f, f0, 3)
    poses["dpad"] = Pose(spin=6.0 * rock)
    poses["bar_a"] = Pose(y=1.2 * max(tap(f, f0) for f0 in (60, 102, 144, 180)))
    poses["bar_b"] = Pose(y=1.2 * max(tap(f, f0) for f0 in (80, 124, 166)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", dark=L.COLOURS["ink"]), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "lcdgames_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "lcdgames_media.png"))))

    whole = smoothed(join([shell(m)] + bosses(m), "lcdgames"), 40.0)
    button, at = start_button(m)
    cross, cross_at = dpad(m)
    parts = {"start": (smoothed(button), at), "dpad": (smoothed(cross, 40.0), cross_at)}
    parts.update({name: (smoothed(part), place) for name, (part, place) in bars(m).items()})
    (lw, lh), (lx, lz) = L.LCD["size"], L.LCD["at"]
    parts.update(H.screens(SCREENS, lw, lh, MEDIA, m["glass"], (lx, SUNK - 0.02, lz)))
    finish("lcdgames", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "LCD games")


if __name__ == "__main__":
    main()
