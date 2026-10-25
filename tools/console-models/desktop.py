"""The console theme's Desktop Apps system model (godot/themes/console/models/systems/desktop.glb): an unbranded
laptop, open, its screen showing a made-up desktop of shortcuts.

Built in Blender (desktop_layout.py has the measurements). Desktop Apps is the shortcuts on the user's desktop, so it
has no hardware of its own: the card is a laptop, as Flash's is a monitor and PICO-8's its cartridge. The base is its
rounded slab with the keyboard's well and the touchpad sunk into it, its top printed; the lid is built upright and
turned back on its hinge, the bezel round the screen. The printing is one texture (desktop_print.py's).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the base; the base
holding the lid (at its hinge); the lid holding, in the screen's plane, the cursor, the Odyssey shortcut selected
(waiting inside the lid) and the game's window (shrunk to nothing), the window its three screens (those not shown a
little behind the one that is, so a swap never shows one shrinking).

The `focused` clip (8 s, looping): the cursor glides to the Odyssey shortcut and double-clicks it, and it's selected;
the game's window zooms open from it: the title, then the game; the cursor goes to the window's close button and
clicks, the window closes and the cursor goes back.

Two materials (body, screen) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/desktop_print.py artifacts/desktop
    blender -b --factory-startup --python tools/console-models/desktop.py -- artifacts/desktop godot/themes/console/models/systems/desktop.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desktop_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 16.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(body=0.4, screen=0.55)       # a matte screen: a glossy one washed the desktop out
SW, SH = L.SCREEN["size"]


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


def flat(name, w, h, uv, mat):
    """A flat quad facing -y, w x h about its origin (x across, z up); uv(a, b) for a across from its left and b down
    from its top, 0 to 1."""
    part = solid(name, [[(x, y, z) for x, z in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
                        for y in (0.0, 0.05)], mat)
    paint(part, mat, lambda co: uv(co.x / w + 0.5, 0.5 - co.z / h), lambda c, n, kind: n.y < -0.9)
    paint(part, mat, swatch("black"), lambda c, n, kind: n.y >= -0.9)
    return part


def region_uv(name):
    rx, ry, rw, rh = L.REGIONS[name]
    return lambda a, b: ((rx + a * rw) / L.ATLAS, 1 - (ry + b * rh) / L.ATLAS)


def on_screen(u, v):
    """A point (u across from the screen's middle, v up from its bottom) in the lid's frame."""
    return Vector((u, 0.0, L.SCREEN["bottom"] + v))


# ---- The laptop ------------------------------------------------------------------------------------------------------

def base(m):
    """The base: its slab, the keyboard's well and the touchpad sunk in, the hinge, the feet; its top printed."""
    slab = solid("desktop", [[(x, y, z) for x, y in rounded(0.0, L.DEPTH / 2, L.WIDTH, L.DEPTH, L.ROUND["plan"], 5)]
                             for z in (0.0, L.BASE)], m["body"])
    bevel(slab, L.ROUND["edge"], segments=2, angle=40)
    (wx0, wx1), (wy0, wy1) = L.WELL["x"], L.WELL["y"]
    boolean(slab, box("well", wx0, wx1, wy0, wy1, L.BASE - L.WELL["depth"], L.BASE + 5.0, m["body"]))
    (tx0, tx1), (ty0, ty1) = L.TOUCHPAD["x"], L.TOUCHPAD["y"]
    pad = rounded((tx0 + tx1) / 2, (ty0 + ty1) / 2, tx1 - tx0, ty1 - ty0, 4.0, 3)
    boolean(slab, solid("touchpad", [[(x, y, z) for x, y in pad] for z in (L.BASE - L.TOUCHPAD["depth"], L.BASE + 5.0)],
                        m["body"]))
    colour(slab, m["body"], "body")
    top = atlas_uv(L.REGIONS["keyboard"], L.WIDTH, L.DEPTH)
    paint(slab, m["body"], lambda co: top(co.x + L.WIDTH / 2, L.DEPTH - co.y), lambda c, n, kind: n.z > 0.9)
    hy, hz = L.LID["hinge"]
    hinge = solid("hinge", [[(x, hy + 4.2 * math.cos(a), hz + 4.2 * math.sin(a)) for a in
                             [2 * math.pi * k / 12 for k in range(12)]] for x in (-150.0, 150.0)], m["body"])
    colour(hinge, m["body"], "hinge")
    feet = [colour(solid("foot", [[(x + 6.0 * math.cos(a), y + 6.0 * math.sin(a), z) for a in
                                   [2 * math.pi * k / 10 for k in range(10)]] for z in (-1.0, 0.5)], m["body"]),
                   m["body"], "black") for x in (-150.0, 150.0) for y in (22.0, 216.0)]
    return join([slab, hinge] + feet, "desktop")


def lid(m):
    """The lid, built upright in its own frame (its hinge's line at the origin, its screen facing -y): its shell, the
    bezel, the screen at rest."""
    w, h, t = L.LID["width"], L.LID["height"], L.LID["thickness"]
    shell = solid("lid", [[(x, y, z) for x, z in rounded(0.0, h / 2, w, h, L.ROUND["plan"], 5)] for y in (0.0, t)],
                  m["body"])
    bevel(shell, 1.6, segments=2, angle=40)
    colour(shell, m["body"], "lid")
    paint(shell, m["screen"], swatch("bezel"), lambda c, n, kind: n.y < -0.9)
    screen = flat("screen", SW, SH, region_uv("desktop"), m["screen"])
    screen.data.transform(Matrix.Translation(on_screen(0.0, SH / 2) + Vector((0.0, -0.1, 0.0))))
    return join([shell, screen], "lid")


def cursor(m):
    """The mouse pointer, its tip at its origin, white with a black edge, facing -y."""
    s = L.CURSOR["size"] / 12.0
    arrow = [(0.0, 0.0), (0.0, -12.0), (3.0, -9.2), (5.2, -14.0), (7.0, -13.2), (4.8, -8.6), (8.6, -8.6)]

    def shape(name, grow, y0, y1, mat_name):
        cx, cz = 3.0, -8.0
        pts = [((x - cx) * grow + cx, (z - cz) * grow + cz) for x, z in arrow]
        part = solid(name, [[(x * s, y, z * s) for x, z in pts] for y in (y0, y1)], m["screen"])
        return colour(part, m["screen"], mat_name)
    return join([shape("cursor", 1.0, -0.2, 0.0, "white"), shape("cursor_edge", 1.22, 0.05, 0.25, "black")], "cursor")


# ---- The focused clip ------------------------------------------------------------------------------------------------

REST = L.CURSOR["rest"]
ICON = (L.ICONS["x"] + 2.0, L.ICONS["top"] - 2.0)       # where the cursor clicks the Odyssey shortcut
CLOSE = L.WINDOW["close"]
FRONT = -1.0              # how far in front of the screen the shown things stand; the hidden ones stay just behind them


def glide(f, f0, f1, a, b):
    t = smooth(phase(f, f0, f1))
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def click(f, f0):
    return 0.18 * math.sin(math.pi * phase(f, f0, f0 + 4))


def showing(f):
    if f < 92 or f >= 184:
        return "title"
    return "game_1" if ((f - 92) // 8) % 2 == 0 else "game_2"


def timeline(f):
    if f < 40:
        u, v = glide(f, 8, 34, REST, ICON)
    elif f < 150:
        u, v = ICON
    elif f < 198:
        u, v = glide(f, 150, 176, ICON, CLOSE)
    else:
        u, v = glide(f, 198, 226, CLOSE, REST)
    press = max(click(f, 38), click(f, 45), click(f, 180))
    rest = on_screen(*REST)
    here = on_screen(u, v)
    poses = {"cursor": Pose(x=here.x - rest.x, z=here.z - rest.z, scale=1.0 - press)}
    poses["selected"] = Pose(y=FRONT - 0.5) if 38 <= f < 52 else Pose()
    # The window: from the shortcut to its place, growing; later shrinking away.
    (wu, wv) = L.WINDOW["at"]
    iu, iv = L.ICONS["x"], L.ICONS["top"]
    if f < 50 or f >= 196:
        win = Pose(scale=HIDDEN)
    elif f < 62:
        t = smooth(phase(f, 50, 62))                    # no overshoot: it would spill past the screen's edge
        win = Pose(x=(iu - wu) * (1 - t), z=(iv - wv) * (1 - t), scale=max(HIDDEN, 0.08 + 0.92 * t))
    elif f < 184:
        win = Pose()
    else:
        win = Pose(scale=max(HIDDEN, 1.0 - ease_in(phase(f, 184, 196))))
    poses["window"] = win
    lit = showing(f)
    for name in ("title", "game_1", "game_2"):
        poses[name] = Pose() if name == lit else Pose(y=0.6)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "desktop_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    laptop = base(m)
    cover = lid(m)
    for obj in (laptop, cover):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("desktop_root", None)
    scene.collection.objects.link(root)
    laptop.parent = root
    hy, hz = L.LID["hinge"]
    cover.parent = laptop
    cover.location = (0.0, hy, hz)
    cover.rotation_euler = (math.radians(-(L.LID["open"] - 90.0)), 0.0, 0.0)

    pointer = cursor(m)
    pointer.parent = cover
    pointer.location = on_screen(*REST) + Vector((0.0, FRONT - 1.0, 0.0))
    u0, v0, u1, v1 = (L.ICONS["x"] - 14.0, L.ICONS["top"] - L.ICONS["size"] / 2 - 8.5, L.ICONS["x"] + 14.0,
                      L.ICONS["top"] + L.ICONS["size"] / 2 + 1.5)
    chosen = flat("selected", u1 - u0, v1 - v0, region_uv("selected"), m["screen"])
    chosen.parent = cover
    chosen.location = on_screen((u0 + u1) / 2, (v0 + v1) / 2) + Vector((0.0, 0.4, 0.0))   # waiting inside the lid
    window = bpy.data.objects.new("window", None)
    scene.collection.objects.link(window)
    window.parent = cover
    window.location = on_screen(*L.WINDOW["at"]) + Vector((0.0, FRONT, 0.0))
    nodes = {"cursor": pointer, "selected": chosen, "window": window}
    ww, wh = L.WINDOW["size"]
    for name in ("title", "game_1", "game_2"):
        part = flat(name, ww, wh, region_uv(name), m["screen"])
        part.parent = window
        part.location = (0.0, 0.0, 0.0)
        nodes[name] = part

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    bpy.context.view_layer.update()
    lid_world = Matrix.Translation((0.0, hy, hz)) @ Matrix.Rotation(math.radians(-(L.LID["open"] - 90.0)), 4, "X")
    points = [tilt @ v.co for v in laptop.data.vertices] + [tilt @ lid_world @ v.co for v in cover.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [laptop, cover, pointer, chosen] + [nodes[n] for n in ("title", "game_1", "game_2")]
    print(f"Desktop Apps: {sum(triangles(o.data) for o in meshes)} triangles, "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root, window] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
