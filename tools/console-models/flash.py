"""The console theme's Flash system model (godot/themes/console/models/systems/flash.glb): a 2000s LCD monitor playing
a Flash game in a browser, and its mouse.

Flash has no hardware (flash_layout.py): its card is a silver 17-inch LCD on its oval foot, the browser filling its
screen, and a mouse beside it. The panel is its bezel (the screen's recess cut into its front) and the housing behind
it; the neck rises from the foot to the housing; the buttons and the blue power light sit along the bezel's lower lip,
the brand plate in its middle. The mouse is lofted from its outline, domed, its top printed. The printing is one
texture drawn by flash_print.py: the screens, the plate, the mouse's top and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH; then the model spec's fit: standing on
y = 0, centred, the largest side 1 m) holding the set; the set holding the screens over the glass (the preloader's
bar filling, Odyssey's title, two frames of play, the right-click menu), shrunk to nothing, so at rest the card shows
the preloader's splash with the Flash logo; and the mouse.

The `focused` clip (8 s, looping) plays it: the preloader's bar fills, Odyssey's title comes up, the mouse moves and
clicks PLAY (it dips under the finger), two frames of play take turns, a right click brings up the menu ending in About
Adobe Flash Player, and the page loads again.

Four materials (silver, black, glass, mouse) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/flash_print.py artifacts/flash
    blender -b --factory-startup --python tools/console-models/flash.py -- artifacts/flash godot/themes/console/models/systems/flash.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flash_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: the top tips back a little
ROUGHNESS = dict(silver=0.35, black=0.5, glass=0.15, mouse=0.4)
STATES = ("load", "title", "game1", "game2", "menu")


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, _name: True)
    return obj


def ellipse(cx, cy, rx, ry, n=32):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The monitor -----------------------------------------------------------------------------------------------------

GLASS_Z = L.PANEL["bottom"] + L.PANEL["lip"] + L.GLASS[1] / 2     # the glass's middle's height


def monitor(m):
    """The panel (the bezel, the screen's recess, the housing behind), the neck, the foot, the buttons, the light, the
    plate; the glass at rest."""
    p = L.PANEL
    w, h, b = p["width"], p["height"], p["bottom"]
    bezel = solid("flash", [[(x, y, z) for x, z in rounded(0.0, b + h / 2, w, h, 10.0, 4)] for y in (0.0, 22.0)],
                  m["silver"])
    bevel(bezel, 2.0, segments=2)
    gw, gh = L.GLASS
    boolean(bezel, box("recess", -gw / 2 - 1.0, gw / 2 + 1.0, -5.0, 3.0, GLASS_Z - gh / 2 - 1.0, GLASS_Z + gh / 2 + 1.0,
                       m["black"]))
    housing = solid("housing", [[(x, y, z) for x, z in rounded(0.0, b + h * 0.55, wd, hd, 18.0, 4)] for y, wd, hd in
                                ((20.0, w - 30.0, h - 40.0), (p["depth"], w * 0.62, h * 0.55))], m["silver"])
    bevel(housing, 3.0, segments=2, angle=50)
    s = L.STAND
    nw, nd = s["neck"]
    neck = box("neck", -nw / 2, nw / 2, s["neck_y"] - nd / 2, s["neck_y"] + nd / 2, 4.0, b + s["top"], m["silver"])
    bevel(neck, 4.0, segments=2)
    bw, bd, bh = s["base"]
    foot = solid("foot", [[(x, y, z) for x, y in ellipse(0.0, s["base_y"], rx, ry, 48)] for rx, ry, z in
                          ((bw / 2 - 4.0, bd / 2 - 4.0, 0.0), (bw / 2, bd / 2, 4.0), (bw / 2 - 10.0, bd / 2 - 10.0, bh))],
                 m["silver"])
    parts = [bezel, housing, neck, foot]
    bx, bz = L.BUTTONS["x"], b + 12.0
    for x in bx:
        button = box("button", x - 4.0, x + 4.0, -1.2, 1.0, bz - 1.5, bz + 1.5, m["black"])
        parts.append(button)
    lx, lz, lr = L.LED
    led = solid("led", [[(x, y, z) for x, z in ellipse(lx, b + 12.0, lr, lr, 12)] for y in (-1.0, 1.0)], m["black"])
    parts.append(painted(led, m["glass"], "blue"))

    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    pw, ph = 60.0, 9.0
    corners = [(-pw / 2, b + 7.5), (pw / 2, b + 7.5), (pw / 2, b + 7.5 + ph), (-pw / 2, b + 7.5 + ph)]   # facing -y
    face = bm.faces.new([bm.verts.new((x, -0.15, z)) for x, z in corners])
    uv = atlas_uv(L.REGIONS["plate"], pw, ph)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = uv(x + pw / 2, b + 7.5 + ph - z)
    parts.append(new_object("plate", bm, m["glass"]))

    glass = curved("glass", gw, gh, 0.0, atlas_uv(L.REGIONS["rest"], 1.0, 1.0), m["glass"], 8, 6)
    glass.data.transform(Matrix.Translation((0.0, 2.6, GLASS_Z)))
    parts.append(glass)
    return parts


def screens(m):
    gw, gh = L.GLASS
    return {name: curved("screen_" + name, gw, gh, 0.0, atlas_uv(L.REGIONS[name], 1.0, 1.0), m["glass"], 8, 6)
            for name in STATES}


# ---- The mouse -------------------------------------------------------------------------------------------------------

def mouse(m):
    """The mouse, its middle at its origin, its buttons towards +y: an egg lofted up to a dome, its top printed (the
    buttons' seams, the wheel)."""
    w, length, h = L.MOUSE["size"]
    rings = []
    for z, scale in ((0.0, 0.94), (3.0, 1.0), (h * 0.55, 0.97), (h * 0.8, 0.84), (h * 0.95, 0.6), (h, 0.3)):
        rings.append([(x * scale, y * scale + (1 - scale) * 6.0, z) for x, y in egg(w, length)])
    body = solid("mouse", rings, m["mouse"])
    for poly in body.data.polygons:
        poly.use_smooth = True
    top = atlas_uv(L.REGIONS["mouse"], w, length)
    paint(body, m["mouse"], lambda co: top(co.x + w / 2, length / 2 - co.y), lambda c, n, name: n.z > 0.3)
    paint(body, m["mouse"], swatch("grey"), lambda c, n, name: n.z <= 0.3)
    return body


def egg(w, length, n=32):
    """The mouse's outline: an egg, wider at the back (-y)."""
    points = []
    for k in range(n):
        a = 2 * math.pi * k / n
        y = length / 2 * math.sin(a)
        x = w / 2 * math.cos(a) * (1.0 - 0.12 * math.sin(a))
        points.append((x, y))
    return points


# ---- The focused clip ------------------------------------------------------------------------------------------------

def timeline(f):
    shown = None
    if 30 <= f < 60:
        shown = "load"
    elif 60 <= f < 100:
        shown = "title"
    elif 100 <= f < 164:
        shown = "game1" if ((f - 100) // 8) % 2 == 0 else "game2"
    elif 164 <= f < 206:
        shown = "menu"
    poses = {"screen_" + name: Pose() if name == shown else Pose(scale=HIDDEN) for name in STATES}
    glide = smooth(phase(f, 66, 88)) * (1 - smooth(phase(f, 206, 230)))
    nudge = smooth(phase(f, 150, 162)) * (1 - smooth(phase(f, 206, 230)))
    poses["mouse"] = Pose(x=10.0 * glide, y=8.0 * glide - 6.0 * nudge)
    click = max(smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 4, f0 + 7))) for f0 in (92, 160))
    poses["mouse"].offset.z -= 1.2 * click                    # a click: the mouse dips under the finger
    poses["mouse"].squash = 0.04 * click
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "flash_print.png"))
    colours = dict(L.COLOURS)
    textures = dict(glass=printed, mouse=printed)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    whole = join(monitor(m), "flash")
    for poly in whole.data.polygons:
        poly.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(40))
    glass = screens(m)
    rodent = mouse(m)

    root = bpy.data.objects.new("flash_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    for k, part in enumerate(glass.values()):
        part.parent = whole
        part.location = Vector((0.0, 2.2 - 0.25 * k, GLASS_Z))
    mx, my = L.MOUSE["at"]
    rodent.parent = whole
    rodent.location = Vector((mx, my, 0.0))
    rodent.rotation_euler = (0.0, 0.0, math.radians(L.MOUSE["turn"]))
    nodes = {**{"screen_" + k: v for k, v in glass.items()}, "mouse": rodent}

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((mx, my, 0.0)) @ Matrix.Rotation(math.radians(L.MOUSE["turn"]), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in rodent.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, rodent] + list(glass.values())
    print(f"Flash: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
