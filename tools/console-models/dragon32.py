"""The console theme's Dragon 32 and Tano Dragon system models (godot/themes/console/models/systems/dragon32.glb and
tanodragon.glb): a Dragon 32, or the Tano Dragon (the same case in ivory, DRAGON By TANO on its badge), in front of the
portable television the ZX Spectrum's card has.

Built in Blender (dragon32_layout.py has the measurements, taken from photographs and the museums' figures). The
computer is its side outline extruded across its width; the keyboard's well is sunk into the slope in the slope's frame,
the ribs cut across the back block and the cartridge's slot into the right side. Its 53 keys stand in the well, each
tapering to its printed top. Behind it stands zx_spectrum.py's television. The printing is two textures
(dragon32_print.py's): `print`, projected from above onto the slope and the keys (with the television's front where its
layout puts it) and onto the cartridge's top; and `media`, the screens.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting outside the slot, shrunk to nothing), the television's four screens (those not shown
behind the glass), and the keys the clip presses.

The `focused` clip (8 s, looping): the cartridge slides into the slot in the right side and starts: the game's title
(the Dragon 32's Odyssey; the Tano Dragon's one of tools/made-up-games's); SPACE, and the game played on the arrow keys;
then the cartridge comes out, the Dragon starts again, OK.

Four materials (case, tv, dark, glass) and two 1024² textures, within the system model budget. Run from the repo root:

    python tools/console-models/dragon32_print.py dragon32 artifacts/made-up-games artifacts/dragon32
    blender -b --factory-startup --python tools/console-models/dragon32.py -- artifacts/dragon32 dragon32 godot/themes/console/models/systems/dragon32.glb

and the same with tanodragon.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dragon32_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402
from zx_spectrum import television  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 20.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, tv=0.45, dark=0.7, glass=0.35)
SCREENS = ("boot", "title", "game_1", "game_2")
BEHIND = 3.0              # how far back a screen that isn't shown waits: behind the glass
PRESSED = dict(up="↑", down="↓", left="←", right="→", space=" ")


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


TOP = atlas_uv(L.PRINT_REGIONS["top"], L.WIDTH, L.TOP)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.TOP - co.y)


def on_slope(name, outline, h0, h1, mat, outline1=None):
    """A solid from an (x, s) outline in the slope's frame, from h0 off it to h1 (its top outline1, if given)."""
    top = outline1 or outline
    return solid(name, [[(x, *L.slope_point(s, h0)) for x, s in outline], [(x, *L.slope_point(s, h1)) for x, s in top]],
                 mat)


# ---- The Dragon ------------------------------------------------------------------------------------------------------

def dragon(m):
    """The case: the well, the ribs and the slot cut in; printed."""
    half = L.WIDTH / 2
    body = prism_x("dragon32", L.PROFILE, -half, half, m["case"])
    bevel(body, 2.5, segments=2, angle=40)
    (wx0, wx1), (ws0, ws1), depth, r = L.WELL["x"], L.WELL["s"], L.WELL["depth"], L.WELL["r"]
    outline = rounded((wx0 + wx1) / 2, (ws0 + ws1) / 2, wx1 - wx0, ws1 - ws0, r, 4)
    boolean(body, on_slope("well", outline, -depth, 30.0, m["case"]))
    (ry0, ry1), n = L.RIBS["y"], L.RIBS["count"]
    for k in range(n):
        y = ry0 + (ry1 - ry0) * (k + 0.5) / n
        boolean(body, box("groove", -half + 8.0, half - 8.0, y - 1.5, y + 1.5, L.HEIGHT - 1.5, L.HEIGHT + 1.0,
                          m["case"]))
    (sy0, sy1), (sz0, sz1) = L.SLOT["y"], L.SLOT["z"]
    boolean(body, box("slot", half - L.SLOT["depth"], half + 1.0, sy0, sy1, sz0, sz1, m["case"]))
    colour(body, m["case"], "case")
    paint(body, m["case"], top_uv, lambda c, n_, kind: n_.z > 0.3 and c.y < L.TOP - 0.5)
    paint(body, m["case"], swatch("rib"),
          lambda c, n_, kind: ry0 - 1.0 < c.y < ry1 + 1.0 and c.z > L.HEIGHT - 2.0 and n_.z < 0.9)
    paint(body, m["case"], swatch("dark"),
          lambda c, n_, kind: c.x < half - 0.5 and sy0 - 0.5 < c.y < sy1 + 0.5 and sz0 - 0.5 < c.z < sz1 + 0.5)
    return body


def keys(m):
    """The keys, standing in the well, each tapering to its printed top; those the clip presses apart (each its foot's
    middle at its origin, with where it goes), the rest joined."""
    fixed, moving = [], {}
    inset, top, floor = L.KEY["inset"], L.KEY["height"], -L.WELL["depth"]
    for legend, x0, x1, s in L.keys():
        foot = [(x0 + 0.6, s - 9.0), (x1 - 0.6, s - 9.0), (x1 - 0.6, s + 9.0), (x0 + 0.6, s + 9.0)]
        cap = [(x0 + inset, s - 9.5 + inset), (x1 - inset, s - 9.5 + inset), (x1 - inset, s + 9.5 - inset),
               (x0 + inset, s + 9.5 - inset)]
        part = on_slope("key", foot, floor - 1.0, top, m["case"], cap)
        colour(part, m["case"], "key")
        paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.85)
        name = next((k for k, v in PRESSED.items() if v == legend and k not in moving), None)
        if name:
            middle = Vector(((x0 + x1) / 2, *L.slope_point(s, floor - 1.0)))
            part.data.transform(Matrix.Translation(-middle))
            moving[name] = (part, middle)
        else:
            fixed.append(part)
    return join(fixed, "keys"), moving


def cartridge(m):
    """The cartridge, its end going in (along -x) at its origin's x, its middle across and its foot's middle; its label
    up."""
    length, w, t = L.CART["size"]
    part = box("cartridge", 0.0, length, -w / 2, w / 2, -t / 2, t / 2, m["case"])
    bevel(part, 1.6, segments=2)
    colour(part, m["case"], "cart")
    face = atlas_uv(L.PRINT_REGIONS["cartridge"], w, length)
    paint(part, m["case"], lambda co: face(co.y + w / 2, length - co.x), lambda c, n, kind: n.z > 0.9)
    return part


def screens(m):
    """The television's four screens, each the glass's whole area."""
    gw, gh = SL.TV["glass"]["size"]
    return {name: curved(name, gw, gh, SL.TV["glass"]["bulge"], atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0), m["glass"])
            for name in SCREENS}


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def shown(f):
    if f < 40 or f >= 178:
        return "boot"
    if f < 62:
        return "title"
    return "game_1" if ((f - 62) // 6) % 2 == 0 else "game_2"


def timeline(f):
    out = L.CART["out"]
    if f < 10 or f >= 194:
        cart = Pose(x=out, scale=HIDDEN)
    elif f < 17:
        cart = Pose(x=out, scale=max(HIDDEN, back_out(phase(f, 10, 17))))
    elif f < 172:
        cart = Pose(x=out * (1 - smooth(phase(f, 17, 34))))
    elif f < 186:
        cart = Pose(x=out * smooth(phase(f, 172, 186)))
    else:
        cart = Pose(x=out, scale=max(HIDDEN, 1 - ease_in(phase(f, 186, 194))))
    poses = {"cartridge": cart}
    for name in SCREENS:
        poses[name] = Pose() if name == shown(f) else Pose(y=BEHIND)
    press = -2.6
    poses["space"] = Pose(z=press * tap(f, 56))
    for name, times in (("up", (70, 98, 126, 154)), ("down", (84, 140)), ("left", (78, 112, 146)),
                        ("right", (90, 104, 132, 160))):
        poses[name] = Pose(z=press * max(tap(f, f0) for f0 in times))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, kind, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    m = {"case": material("case", L.COLOURS["print"], ROUGHNESS["case"],
                          bpy.data.images.load(os.path.join(images, f"{kind}_print.png"))),
         "tv": material("tv", SL.COLOURS["tv"], ROUGHNESS["tv"]),
         "dark": material("dark", L.COLOURS["dark"], ROUGHNESS["dark"]),
         "glass": material("glass", L.COLOURS["print"], ROUGHNESS["glass"],
                           bpy.data.images.load(os.path.join(images, f"{kind}_media.png")))}
    m["print"] = m["case"]                                    # television() prints its front with the set's atlas

    fixed_keys, moving = keys(m)
    tv = television(m, m["glass"], atlas_uv(L.MEDIA_REGIONS["boot"], 1.0, 1.0))
    shift = Matrix.Translation((L.TV_AT[0] - SL.TV["at"][0], L.TV_AT[1] - SL.TV["at"][1], 0.0))
    for part in tv:
        part.data.transform(shift)
    whole = join([dragon(m), fixed_keys] + tv, kind)
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new(kind + "_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (sy0, sy1), (sz0, sz1) = L.SLOT["y"], L.SLOT["z"]
    seat = Vector((L.WIDTH / 2 + L.CART["proud"] - L.CART["size"][0], (sy0 + sy1) / 2, (sz0 + sz1) / 2))
    moving["cartridge"] = (cartridge(m), seat)
    s = SL.TV["screen"]
    glass_front = Vector((L.TV_AT[0] + s["x"], L.TV_AT[1] + s["depth"] - 0.4, s["z"]))
    moving.update({name: (part, glass_front) for name, part in screens(m).items()})
    nodes = {}
    for name, (part, where) in moving.items():
        if name not in SCREENS:
            for p in part.data.polygons:
                p.use_smooth = True
            part.data.set_sharp_from_angle(angle=math.radians(35))
        part.parent = whole
        part.location = where
        nodes[name] = part

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"{kind}: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
