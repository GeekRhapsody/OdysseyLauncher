"""The console theme's ZX81 system model (godot/themes/console/models/systems/zx81.glb): a ZX81 plugged into the
portable television the ZX Spectrum's card has, its inverse K cursor on the screen.

Built in Blender from the real computer's proportions (zx81_layout.py has the measurements, taken from photographs):
its side outline extruded across its width, the top sloping down to the ridge, and in front of the ridge, lower, the
flat membrane keyboard. Behind it stands zx_spectrum.py's television. The printing is two textures drawn by
zx81_print.py: the computer's top seen from above (planar-mapped onto every face facing up: the name, ZX81, the
membrane's keys and keywords) with the television's front; and the screens (the glass at rest shows the K cursor).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the keys the clip presses (J, SHIFT, P and NEW LINE: thin plates over the membrane, which dip and shrink a
little, showing the dark well printed under each) and, over the glass, the screens a game loads through, all shrunk to
nothing at rest.

The `focused` clip (8 s, looping) loads a game from tape: J types LOAD, SHIFT and P twice type the quotes, NEW LINE;
the screen fills with the black and white bands the ZX81 shows while it loads, flickering, then the game comes up in
its block graphics; then the screen resets to the K cursor.

Five materials (case, print, tv, dark, glass) and two textures, within the system model budget. Run from the repo
root:

    python tools/console-models/zx81_print.py artifacts/zx81
    blender -b --factory-startup --python tools/console-models/zx81.py -- artifacts/zx81 godot/themes/console/models/systems/zx81.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zx81_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, export, join, material, prism_x, triangles  # noqa: E402
from zx_spectrum import atlas_uv, television  # noqa: E402

TILT_YAW = -28.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 22.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, print=0.5, tv=0.4, dark=0.6, glass=0.2)
TYPED = ("j", "shift", "p", "newline")

TOP = atlas_uv(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    """The computer's top seen from above."""
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def computer(m):
    body = prism_x("zx81", L.profile(), -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 1.2, segments=2)
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.9)
    return body


def keys(m):
    """The keys the clip presses: each a thin plate over its place on the membrane, its middle at its origin."""
    parts = {}
    for k, (x0, y0, x1, y1) in L.keys_with_rects():
        if k[0] not in TYPED:
            continue
        outline = rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, L.KEY["radius"], 3)
        plate = solid(k[0], [[(x, y, L.membrane_z(y) + dz) for x, y in outline] for dz in (-0.4, 0.12)], m["print"])
        paint(plate, m["print"], top_uv, lambda c, n, _name: True)
        cy = (y0 + y1) / 2
        middle = Vector(((x0 + x1) / 2, cy, L.membrane_z(cy)))
        plate.data.transform(Matrix.Translation(-middle))
        parts[k[0]] = (plate, middle)
    return parts


def screens(m):
    """The screens a game loads through, each the whole glass, its middle at its origin."""
    gw, gh = SL.TV["glass"]["size"]
    return {name: curved("screen_" + name, gw, gh, SL.TV["glass"]["bulge"],
                         atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0), m["glass"], 20, 16)
            for name in L.SCREENS}


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def pressed(depth):
    """A membrane key pressed: down a little, shrinking a little into its printed well."""
    return Pose(z=-0.8 * depth, scale=1.0 - 0.06 * depth)


def timeline(f):
    poses = {"j": pressed(tap(f, 22)), "p": pressed(tap(f, 33) + tap(f, 41)), "newline": pressed(tap(f, 50)),
             "shift": pressed(smooth(phase(f, 30, 33)) * (1 - smooth(phase(f, 45, 49))))}
    shown = None
    for name, f0, f1 in (("load", 24, 41), ("load2", 41, 54), ("game", 150, 228)):
        if f0 <= f < f1:
            shown = name
    if 54 <= f < 150:
        shown = "bands_a" if (f // 3) % 2 == 0 else "bands_b"
    for name in L.SCREENS:
        poses["screen_" + name] = Pose() if name == shown else Pose(scale=HIDDEN)
    if f >= 222 and shown == "game":                              # the reset: the picture shrinks away
        poses["screen_game"] = Pose(axes=(1.0, 1.0, max(HIDDEN, 1 - ease_in(phase(f, 222, 228)))))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "zx81_print.png"))
    media = bpy.data.images.load(os.path.join(images, "zx81_media.png"))
    colours = dict(case=L.COLOURS["case"], print="#FFFFFF", tv=SL.COLOURS["tv"], dark="#0A0A0B", glass="#FFFFFF")
    textures = dict(print=printed, glass=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    glass_uv = atlas_uv(L.MEDIA_REGIONS["glass"], 1.0, 1.0)
    whole = join([computer(m)] + television(m, m["glass"], glass_uv), "zx81")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("zx81_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    nodes = {}
    for name, (plate, middle) in keys(m).items():
        plate.parent = whole
        plate.location = middle
        nodes[name] = plate
    s = SL.TV["screen"]
    middle = Vector((SL.TV["at"][0] + s["x"], SL.TV["at"][1] + s["depth"], s["z"]))
    for k, (name, part) in enumerate(screens(m).items()):
        part.parent = whole
        part.location = middle + Vector((0.0, -0.4 - 0.05 * k, 0.0))
        nodes["screen_" + name] = part

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"ZX81: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
