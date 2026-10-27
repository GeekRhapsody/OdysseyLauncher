"""The console theme's ZX Spectrum Next system model (godot/themes/console/models/systems/zxnext.glb): the ZX Spectrum
Next in front of the portable television the ZX Spectrum's card has.

Built in Blender (zxnext_layout.py has the measurements, taken from photographs). The computer is its side outline
through rings across its width, the right end's rings dropping round its radius; the SD slot is cut into its left end
and RESET, DRIVE and NMI stand out of it; the 58 chiclet keys stand on its top, each a rounded block (ENTER an L of two),
and the cover stands on the back edge. Behind it stands zx_spectrum.py's television. The printing is two textures
(zxnext_print.py's): `print`, projected from above onto the top and the keys, onto the right end (its stripes) and the
left end (with the television's front where its layout puts it); and `media`, the screens.

A node tree (card.finish()): the root holding the set; the set holding the television's four screens over the glass
(shrunk to nothing until shown), the keys the clip presses and RESET.

The `focused` clip (8 s, looping): at rest the start-up menu; ENTER opens the browser, the made-up game chosen, ENTER
again loads it: its title; SPACE, and the game played on the arrows and SPACE; then RESET, and the menu again.

Four materials (case, tv, dark, glass) and two 1024² textures, within the system model budget. Run from the repo root:

    python tools/console-models/zxnext_print.py artifacts/made-up-games artifacts/zxnext
    blender -b --factory-startup --python tools/console-models/zxnext.py -- artifacts/zxnext godot/themes/console/models/systems/zxnext.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zx_spectrum_layout as SL  # noqa: E402
import zxnext_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from zx_spectrum import television  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 32.0    # degrees about the horizontal: the top tips up towards the viewer, the thin Next to see
ROUGHNESS = dict(case=0.6, tv=0.45, dark=0.7, glass=0.35)
ATLAS = Atlas(L.ATLAS, L.PRINT_REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
SCREENS = ("browser", "title", "game1", "game2")
TOP = ATLAS.uv("top", L.WIDTH, L.DEPTH)
HALF = L.WIDTH / 2


def top_uv(co):
    return TOP(co.x + HALF, L.DEPTH - co.y)


# ---- The Next --------------------------------------------------------------------------------------------------------

def body(m):
    """The slab: its outline in rings across it, the right end's dropping round its radius; the SD slot cut; printed."""
    r = L.END["radius"]
    x0 = HALF - r
    rings = [(-HALF, 0.0)] + [(x0 + r * math.sin(math.radians(90.0 * k / L.END["steps"])),
                                r * (1 - math.cos(math.radians(90.0 * k / L.END["steps"]))))
                               for k in range(L.END["steps"] + 1)]
    part = solid("zxnext", [[(x, y, z if z <= 3.0 else max(3.0, z - drop)) for y, z in L.PROFILE]
                            for x, drop in rings], m["case"])
    bevel(part, 1.5, segments=2, angle=30)
    boolean(part, box("sd", -HALF - 5.0, -HALF + 14.0, *L.SD["y"], *L.SD["z"], m["dark"]))
    coloured(part, m["case"], ATLAS, "case")
    paint(part, m["case"], top_uv, lambda c, n, name: n.z > 0.9 and c.x < x0)
    end = ATLAS.uv("end", L.DEPTH, L.BACK[1])
    paint(part, m["case"], lambda co: end(L.DEPTH - co.y, L.BACK[1] - min(co.z, L.BACK[1])),
          lambda c, n, name: c.x > x0 - 0.5 and n.x > 0.15)
    left = ATLAS.uv("left", L.DEPTH, L.BACK[1])
    paint(part, m["case"], lambda co: left(co.y, L.BACK[1] - co.z), lambda c, n, name: n.x < -0.9)
    paint(part, m["case"], ATLAS.swatch("dark"), lambda c, n, name: name == "dark")
    b = L.BUNG
    bung = box("bung", *b["x"], *b["y"], L.top_z(b["y"][0]) - 1.0, L.top_z(b["y"][0]) + b["height"], m["case"])
    bevel(bung, 0.8, segments=1, angle=30)
    coloured(bung, m["case"], ATLAS, "dark")
    return [part, bung]


def key_solid(name, x0, x1, y0, y1, m):
    """A chiclet key standing on the top, rounded, tapering a little to its printed top."""
    g, inset, h = L.KEY["gap"] / 2, L.KEY["inset"], L.KEY["height"]
    z0 = L.top_z((y0 + y1) / 2) - 1.0
    foot = rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 2 * g, y1 - y0 - 2 * g, L.KEY["r"], 3)
    cap = rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 2 * g - 2 * inset, y1 - y0 - 2 * g - 2 * inset,
                  L.KEY["r"] - 0.6, 3)
    part = solid(name, [[(x, y, z0) for x, y in foot], [(x, y, z0 + 1.0 + h) for x, y in cap]], m["case"])
    coloured(part, m["case"], ATLAS, "key")
    paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.9)
    return part


MOVING = {"⇦": "key_left", "⇨": "key_right", " ": "key_space", "ENTER": "key_enter"}


def keys(m):
    """The keys: those the clip presses apart (each its foot's middle at its origin, with where it goes), the rest
    joined; ENTER's two parts one key."""
    fixed, moving, enter = [], {}, []
    for legend, x0, x1, y0, y1 in L.keys():
        if legend == "ENTER":
            enter.append(key_solid("enter", x0, x1, y0 - (L.KEY["gap"] if not enter else 0.0), y1, m))
            continue
        part = key_solid("key", x0, x1, y0, y1, m)
        name = MOVING.get(legend)
        if name and name not in moving:
            middle = Vector(((x0 + x1) / 2, (y0 + y1) / 2, L.top_z((y0 + y1) / 2) - 1.0))
            part.data.transform(Matrix.Translation(-middle))
            moving[name] = (smoothed(part, 40.0), middle)
        else:
            fixed.append(part)
    part = join(enter, "key_enter")
    middle = Vector((sum(v.co.x for v in part.data.vertices) / len(part.data.vertices),
                     sum(v.co.y for v in part.data.vertices) / len(part.data.vertices), 0.0))
    middle.z = L.top_z(middle.y) - 1.0
    part.data.transform(Matrix.Translation(-middle))
    moving["key_enter"] = (smoothed(part, 40.0), middle)
    return join(fixed, "keys"), moving


def buttons(m):
    """RESET, DRIVE and NMI standing out of the left end: DRIVE and NMI fixed, RESET apart (its origin at its foot)."""
    b = L.BUTTONS
    fixed, moving = [], {}
    for name in ("reset", "drive", "nmi"):
        y, _ = b[name]
        ring = [(y + b["r"] * math.cos(2 * math.pi * k / 16), b["z"] + b["r"] * math.sin(2 * math.pi * k / 16))
                for k in range(16)]
        part = solid(name, [[(x, yy, z) for yy, z in ring] for x in (-HALF + 1.0, -HALF - b["out"])], m["case"])
        bevel(part, 0.6, segments=1, angle=30)
        coloured(part, m["case"], ATLAS, name)
        if name == "reset":
            at = Vector((-HALF, y, b["z"]))
            part.data.transform(Matrix.Translation(-at))
            moving[name] = (smoothed(part, 40.0), at)
        else:
            fixed.append(part)
    return fixed, moving


def screens(m):
    """The television's screens, each the glass's whole area."""
    gw, gh = SL.TV["glass"]["size"]
    return {name: curved("screen_" + name, gw, gh, SL.TV["glass"]["bulge"], MEDIA.uv(name, 1.0, 1.0), m["glass"])
            for name in SCREENS}


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 24 <= f < 44:
        return "browser"
    if 44 <= f < 66:
        return "title"
    if 66 <= f < 184:
        return "game1" if ((f - 66) // 8) % 2 == 0 else "game2"
    return None


def timeline(f):
    poses = showing_poses(SCREENS, showing, f)
    press = -2.6
    for name, frames in (("key_enter", (20, 40)), ("key_space", (62, 92, 122, 160)), ("key_left", (74, 100, 134)),
                         ("key_right", (84, 112, 146, 170))):
        poses[name] = Pose(z=press * max(tap(f, f0) for f0 in frames))
    poses["reset"] = Pose(x=1.4 * tap(f, 182, 3))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case=L.COLOURS["print"], tv=SL.COLOURS["tv"], dark=L.COLOURS["dark"], glass=L.COLOURS["print"]),
                  ROUGHNESS, dict(case=bpy.data.images.load(os.path.join(images, "zxnext_print.png")),
                                  glass=bpy.data.images.load(os.path.join(images, "zxnext_media.png"))))
    m["print"] = m["case"]                                    # television() prints its front with the set's atlas

    fixed_keys, moving = keys(m)
    fixed_buttons, pressed = buttons(m)
    moving.update(pressed)
    tv = television(m, m["glass"], MEDIA.uv("menu", 1.0, 1.0))
    shift = Matrix.Translation((L.TV_AT[0] - SL.TV["at"][0], L.TV_AT[1] - SL.TV["at"][1], 0.0))
    for part in tv:
        part.data.transform(shift)
    whole = smoothed(join(body(m) + [fixed_keys] + fixed_buttons + tv, "zxnext"), 35.0)
    s = SL.TV["screen"]
    glass_front = Vector((L.TV_AT[0] + s["x"], L.TV_AT[1] + s["depth"] - 0.4, s["z"]))
    for k, (name, part) in enumerate(screens(m).items()):
        moving["screen_" + name] = (part, glass_front + Vector((0.0, -0.3 * k, 0.0)))
    finish("zxnext", whole, moving, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "ZX Spectrum Next")


if __name__ == "__main__":
    main()
