"""The console theme's Acorn Electron system model (godot/themes/console/models/systems/electron.glb): an Acorn
Electron with a Plus 1 on its back, in front of the portable television the ZX Spectrum's card has.

Built in Blender (electron_layout.py has the measurements, taken from photographs). The computer is its side outline (a
wedge, its top sloping up to the back) extruded across its width, the keys' opening cut into its top; its 56 keys stand
in the opening in the slope's frame, each tapering to its printed top. The Plus 1 is a box on its back, its two slots
cut into its top, the second under its cover. Behind it stands zx_spectrum.py's television. The printing is one texture
(electron_print.py's), planar-mapped from above onto every face facing up.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting over the first slot, shrunk to nothing), the first slot's cover (on its hinge), the
television's four screens (those not shown behind the glass) and the keys the clip presses.

The `focused` clip (8 s, looping): the cartridge appears over the Plus 1, turns to show its label and drops into the
first slot, the cover swinging down out of its way; CTRL and BREAK start it, its title comes up; SPACE, and the game's
played on Z, X and RETURN; BREAK brings the start-up screen back and the cartridge rises out and goes.

Four materials (case, tv, dark, glass) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/electron_print.py artifacts/electron
    blender -b --factory-startup --python tools/console-models/electron.py -- artifacts/electron godot/themes/console/models/systems/electron.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import electron_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from amiga import curved, paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, prism_x,  # noqa: E402
                                  triangles)
from zx_spectrum import television  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 20.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, tv=0.45, dark=0.7, glass=0.35)
MOVING = {"CTRL": "ctrl", "BREAK": "break", "RETURN": "return", "Z": "z", "X": "x", " ": "space"}
TOTAL_DEPTH = L.PLUS1["y"][1]


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, TOTAL_DEPTH)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, TOTAL_DEPTH - co.y)


def on_slope(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline in the slope's frame, from h0 to h1 off it."""
    return solid(name, [[(x, *L.top_point(s, h)) for x, s in outline] for h in (h0, h1)], mat)


# ---- The computer and the Plus 1 -------------------------------------------------------------------------------------

def computer(m):
    """The wedge, the keys' opening cut into its top, the Plus 1 on its back with its slots; printed from above."""
    half = L.WIDTH / 2
    body = prism_x("electron", L.profile(), -half, half, m["case"])
    bevel(body, 2.4, segments=2, angle=40)
    (ox0, ox1), (s0, s1), depth = L.OPENING["x"], L.OPENING["s"], L.OPENING["depth"]
    boolean(body, on_slope("opening", [(ox0, s0), (ox1, s0), (ox1, s1), (ox0, s1)], -depth, 20.0, m["case"]))
    (py0, py1), ph = L.PLUS1["y"], L.PLUS1["height"]
    plus1 = box("plus1", -half, half, py0 + 0.5, py1, 0.0, ph, m["case"])
    bevel(plus1, 2.4, segments=2, angle=40)
    (cx0, cx1), sd = L.PLUS1["x"], L.PLUS1["depth"]
    for sy0, sy1 in L.PLUS1["slots"]:
        boolean(plus1, box("slot", cx0, cx1, sy0, sy1, ph - sd, ph + 5.0, m["case"]))
    parts = [body, plus1]
    for part in parts:
        colour(part, m["case"], "case")
        paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.5)
        paint(part, m["case"], swatch("dark"),
              lambda c, n, kind: cx0 - 0.5 < c.x < cx1 + 0.5 and c.z < ph - 0.5 and c.y > py0
              and any(a - 0.5 < c.y < b + 0.5 for a, b in L.PLUS1["slots"]))
    sy0, sy1 = L.PLUS1["slots"][1]                              # the second slot's cover, shut
    cover = box("cover", cx0 + 0.4, cx1 - 0.4, sy0 + 0.4, sy1 - 0.4, ph - 2.0, ph - 0.4, m["case"])
    colour(cover, m["case"], "case")
    paint(cover, m["case"], top_uv, lambda c, n, kind: n.z > 0.9)
    return join(parts + [cover], "electron")


def keys(m):
    """The keys, each tapering from the opening's floor to its printed top in the slope's frame: those the clip presses
    apart (each its foot's middle at its origin, with where it goes), the rest joined."""
    fixed, moving = [], {}
    inset, h1 = L.KEY["inset"], L.KEY["height"] - L.OPENING["depth"]
    for legend, x0, x1, s in L.keys():
        foot = [(x0 + 0.6, s - 9.0), (x1 - 0.6, s - 9.0), (x1 - 0.6, s + 9.0), (x0 + 0.6, s + 9.0)]
        cap = [(x0 + inset, s - 9.5 + inset), (x1 - inset, s - 9.5 + inset), (x1 - inset, s + 9.5 - inset),
               (x0 + inset, s + 9.5 - inset)]
        h0 = -L.OPENING["depth"]
        part = solid("key", [[(x, *L.top_point(ss, h0)) for x, ss in foot],
                             [(x, *L.top_point(ss, h1)) for x, ss in cap]], m["case"])
        colour(part, m["case"], "key")
        paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.9)
        name = MOVING.get(legend)
        if name and name not in moving:
            y, z = L.top_point(s, h0)
            middle = Vector(((x0 + x1) / 2, y, z))
            part.data.transform(Matrix.Translation(-middle))
            moving[name] = (part, middle)
        else:
            fixed.append(part)
    return join(fixed, "keys"), moving


def cover(m):
    """The first slot's cover, its origin on its hinge along the slot's back edge, shut."""
    (cx0, cx1), ph = L.PLUS1["x"], L.PLUS1["height"]
    sy0, sy1 = L.PLUS1["slots"][0]
    part = box("cover_1", cx0 + 0.4, cx1 - 0.4, sy0 + 0.4, sy1 - 0.4, ph - 2.0, ph - 0.4, m["case"])
    colour(part, m["case"], "case")
    paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.9)
    hinge = Vector((0.0, sy1 - 0.4, ph - 1.2))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def cartridge(m):
    """The cartridge, its foot's middle at its origin, its label facing -y."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(part, 1.6, segments=2)
    colour(part, m["case"], "cart")
    lw, lh = L.CART["label"]
    face = atlas_uv(L.REGIONS["label"], lw, lh)
    z1 = h - 6.0
    paint(part, m["case"], lambda co: face(co.x + lw / 2, z1 - co.z),
          lambda c, n, kind: n.y < -0.9 and abs(c.x) < lw / 2 and z1 - lh < c.z < z1)
    return part


def screens(m):
    """The television's four screens (boot, title, game_1, game_2), each the glass's whole area."""
    gw, gh = SL.TV["glass"]["size"]
    out = {}
    for name in ("boot", "title", "game_1", "game_2"):
        out[name] = curved(name, gw, gh, SL.TV["glass"]["bulge"], atlas_uv(L.REGIONS[name], 1.0, 1.0), m["glass"])
    return out


# ---- The focused clip ------------------------------------------------------------------------------------------------

BEHIND = 3.0              # how far back a screen that isn't shown waits: behind the glass


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def shown(f):
    if f < 52 or f >= 188:
        return "boot"
    if f < 96:
        return "title"
    return "game_1" if ((f - 96) // 8) % 2 == 0 else "game_2"


def timeline(f):
    above = L.CART["above"]
    if f < 8 or f >= 214:
        cart = Pose(z=above, scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 8, 15))))
    elif f < 30:
        cart = Pose(z=above, spin=360.0 * smooth(phase(f, 16, 30)))
    elif f < 42:
        cart = Pose(z=above * (1 - ease_in(phase(f, 30, 42))))
    elif f < 194:
        cart = Pose(z=-1.6 * math.sin(math.pi * phase(f, 42, 48)))
    elif f < 206:
        cart = Pose(z=above * ease_out(phase(f, 194, 206)))
    else:
        cart = Pose(z=above, scale=max(HIDDEN, 1 - ease_in(phase(f, 206, 214))))
    swing = 92.0 * smooth(phase(f, 36, 41)) * (1 - smooth(phase(f, 202, 208)))
    poses = {"cartridge": cart, "cover": Pose(pitch=-swing)}
    for name in ("boot", "title", "game_1", "game_2"):
        poses[name] = Pose() if name == shown(f) else Pose(y=BEHIND)
    press = -2.4
    poses["ctrl"] = Pose(z=press * smooth(phase(f, 44, 47)) * (1 - smooth(phase(f, 52, 55))))
    poses["break"] = Pose(z=press * max(tap(f, 47), tap(f, 184)))
    poses["space"] = Pose(z=press * tap(f, 92))
    poses["z"] = Pose(z=press * max(tap(f, f0) for f0 in (104, 128, 152)))
    poses["x"] = Pose(z=press * max(tap(f, f0) for f0 in (116, 140, 164)))
    poses["return"] = Pose(z=press * max(tap(f, f0) for f0 in (110, 134, 160)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "electron_print.png"))
    m = {"case": material("case", L.COLOURS["print"], ROUGHNESS["case"], atlas),
         "tv": material("tv", SL.COLOURS["tv"], ROUGHNESS["tv"]),
         "dark": material("dark", L.COLOURS["dark"], ROUGHNESS["dark"]),
         "glass": material("glass", L.COLOURS["print"], ROUGHNESS["glass"], atlas)}
    m["print"] = m["case"]                                    # television() prints its front with the set's atlas

    fixed_keys, moving_keys = keys(m)
    tv = television(m, m["glass"], atlas_uv(L.REGIONS["boot"], 1.0, 1.0))
    shift = Matrix.Translation((L.TV_AT[0] - SL.TV["at"][0], L.TV_AT[1] - SL.TV["at"][1], 0.0))
    for part in tv:
        part.data.transform(shift)
    whole = join([computer(m), fixed_keys] + tv, "electron")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("electron_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    s = SL.TV["screen"]
    glass_front = Vector((L.TV_AT[0] + s["x"], L.TV_AT[1] + s["depth"] - 0.4, s["z"]))
    flap, hinge = cover(m)
    (cx0, cx1) = L.PLUS1["x"]
    sy0, sy1 = L.PLUS1["slots"][0]
    seat = Vector(((cx0 + cx1) / 2, (sy0 + sy1) / 2, L.PLUS1["height"] - L.CART["seat"]))
    parts = {"cartridge": (cartridge(m), seat), "cover": (flap, hinge)}
    parts.update({name: (part, glass_front) for name, part in screens(m).items()})
    parts.update(moving_keys)
    nodes = {}
    for name, (part, where) in parts.items():
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
    print(f"Electron: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
