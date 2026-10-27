"""The console theme's Palm OS system model (godot/themes/console/models/systems/palm.glb): a PalmPilot, standing up,
its stylus in its silo.

Built in Blender with handheld.py's pieces (palm_layout.py has the measurements, from its makers' figures and
photographs): the charcoal shell, its edges rounded, cut for the glass window, the lower lip's step and the stylus's
silo down its right edge; the buttons, the scroll rocker's bars and the teal power key standing on its face; the screens
over the window's LCD; the stylus. The printing is two textures drawn by palm_print.py (the face, swatches; the
screens).

A node tree (card.finish()): the root holding the set; the set holding the power key, the screens (each shrunk to
nothing until it's shown) and the stylus.

The `focused` clip (8 s, looping): the power key, the application launcher; the stylus is drawn up out of its silo and
taps the made-up game among the applications: its title, and the game played with the stylus's taps; the stylus goes
back into its silo and the power key turns it off.

Three materials (case, glass, dark) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/palm_print.py artifacts/made-up-games artifacts/palm
    blender -b --factory-startup --python tools/console-models/palm.py -- artifacts/palm godot/themes/console/models/systems/palm.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handheld as H  # noqa: E402
import palm_layout as L  # noqa: E402
from amiga import rounded, solid  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: its right edge (the stylus) comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.55, glass=0.25, dark=0.5)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
SCREENS = ("launcher", "title", "game1", "game2")
GLASS = 0.8                  # the window's glass, back from the face


def shell(m):
    part = H.body("palm", rounded(0.0, L.HEIGHT / 2, L.WIDTH, L.HEIGHT, L.CORNER, 5), L.DEPTH, m["case"], front=2.0,
                  back=3.0)
    lip = [(x, L.LIP["middle"] + (L.LIP["ends"] - L.LIP["middle"]) * (x / L.HALF) ** 2)
           for x in [L.HALF + 2.0 - (L.WIDTH + 4.0) * k / 30 for k in range(31)]]
    x0, x1, z0, z1 = L.WINDOW["rect"]
    s = L.STYLUS
    silo = [(s["x"] + L.SILO["r"] * math.cos(2 * math.pi * k / 16), s["y"] + L.SILO["r"] * math.sin(2 * math.pi * k / 16))
            for k in range(16)]
    cuts = [plate("lip", [(-L.HALF - 2.0, -2.0), (L.HALF + 2.0, -2.0)] + lip, -2.0, L.LIP["step"], m["case"]),
            plate("window", rounded((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, L.WINDOW["r"], 3), -2.0, GLASS,
                  m["case"]),
            solid("silo", [[(x, y, z) for x, y in silo] for z in (L.HEIGHT - s["length"] - 2.0, L.HEIGHT + 5.0)],
                  m["dark"])]
    boolean(part, join(cuts, "cuts"))
    coloured(part, m["case"], ATLAS, "body")
    H.paint_face(part, m["case"], FACE, lambda c, n, kind: n.y < -0.9 and kind == "case")
    return part


def buttons(m):
    out = []
    z = L.BUTTONS["z"]
    for x, _ in L.BUTTONS["apps"]:
        r = L.BUTTONS["r"]
        b = lathe("button", [(0.0, -0.5), (r, -0.5), (r, 0.6), (r - 0.8, 1.5), (0.0, 1.7)], m["case"], 24)
        b.data.transform(Matrix.Translation((x, 0.0, z)) @ Matrix.Rotation(math.radians(90.0), 4, "X"))
        coloured(b, m["case"], ATLAS, "button")
        out.append(H.paint_face(b, m["case"], FACE, lambda c, n, kind: n.y < -0.5))
    rx, za, zb = L.BUTTONS["rocker"]
    w, h = L.BUTTONS["bar"]
    for zz in (za, zb):
        bar = plate("bar", H.stadium(rx, zz, w, h), -1.4, 0.4, m["case"])
        bevel(bar, 0.5, segments=2, angle=50)
        out.append(coloured(bar, m["case"], ATLAS, "button"))
    return out


def power(m):
    w, h = L.POWER["size"]
    x, z = L.POWER["at"]
    part = box("power", -w / 2, w / 2, -1.2, 3.0, -h / 2, h / 2, m["case"])
    bevel(part, 0.8, segments=2)
    return coloured(part, m["case"], ATLAS, "teal"), Vector((x, 0.0, z))


def stylus(m):
    """The stylus, its middle at its origin, standing; its tip at the bottom, its ribbed cap at the top."""
    s = L.STYLUS
    length, r = s["length"], s["r"]
    profile = [(0.0, 0.0), (0.5, 0.8), (1.6, 6.0), (r, 14.0), (r, length - s["cap"])]
    for k in range(4):
        z = length - s["cap"] + 2.0 * k
        profile += [(r + 0.25, z + 0.4), (r + 0.25, z + 1.4), (r, z + 1.8)]
    profile += [(r - 0.6, length), (0.0, length)]
    part = lathe("stylus", [(rr, z - length / 2) for rr, z in profile], m["case"], 16)
    return coloured(part, m["case"], ATLAS, "stylus")


# ---- The focused clip ------------------------------------------------------------------------------------------------

LEAN = 45.0                  # the stylus held leaning towards the viewer, its tip on the glass


def rest_centre():
    return Vector((L.STYLUS["x"], L.STYLUS["y"], L.HEIGHT + 1.0 - L.STYLUS["length"] / 2))


def touch(x, z, off=0.0):
    """The stylus's pose with its tip on the glass at (x, z) (off: drawn back that far)."""
    half = L.STYLUS["length"] / 2
    c = Vector((x, GLASS - 0.3 - off, z)) - Vector((0.0, half * math.sin(math.radians(LEAN)),
                                                     -half * math.cos(math.radians(LEAN))))
    return c - rest_centre(), LEAN


REST = (Vector(), 0.0)
OUT = (Vector((0.0, -6.0, L.STYLUS["length"] + 4.0)), 0.0)
T = L.TAPS
KEYS = ([(0, REST), (20, REST), (38, OUT), (52, touch(*T[0], 4.0)), (58, touch(*T[0])), (62, touch(*T[0], 4.0))]
        + [frame for k, f0 in ((1, 96), (2, 120), (3, 144))
           for frame in ((f0 - 4, touch(*T[k], 4.0)), (f0, touch(*T[k])), (f0 + 4, touch(*T[k], 4.0)))]
        + [(166, OUT), (184, REST), (240, REST)])


def stylus_pose(f):
    for (f0, (a, pa)), (f1, (b, pb)) in zip(KEYS, KEYS[1:]):
        if f0 <= f <= f1:
            t = smooth(phase(f, f0, f1))
            v = a.lerp(b, t)
            return Pose(*v, pitch=pa + (pb - pa) * t)
    return Pose()


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 12 <= f < 62:
        return "launcher"
    if 62 <= f < 96:
        return "title"
    if 96 <= f < 196:
        return "game1" if ((f - 96) // 24) % 2 == 0 else "game2"
    return None


def timeline(f):
    poses = showing_poses(SCREENS, showing, f)
    poses["power"] = Pose(y=1.0 * max(tap(f, 8, 3), tap(f, 192, 3)))
    poses["stylus"] = stylus_pose(f)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", dark="#141416"), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "palm_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "palm_media.png"))))

    whole = smoothed(join([shell(m)] + buttons(m), "palm"), 40.0)
    key, at = power(m)
    parts = {"power": (smoothed(key), at), "stylus": (smoothed(stylus(m), 50.0), rest_centre())}
    (lw, lh), (lx, lz) = L.WINDOW["lcd"], L.WINDOW["lcd_at"]
    parts.update(H.screens(SCREENS, lw, lh, MEDIA, m["glass"], (lx, GLASS - 0.02, lz)))
    finish("palm", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "PalmPilot")


if __name__ == "__main__":
    main()
