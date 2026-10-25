"""The console theme's PICO-8 system model (godot/themes/console/models/systems/pico8.glb): PICO-8's cartridge made
solid, its label a screen.

PICO-8 is a fantasy console with no hardware; what it shows the world is its cartridge image (pico8_layout.py). The
cartridge is its outline extruded through its thickness in three slices (the middle one a little smaller all round, the
seam between the halves), its corners cut in pixel steps, its face and back printed by pico8_print.py, and its label a
screen over the face's window. The printing is two textures: the face, the back and swatches; and the label's
screens.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH; then the model spec's fit: standing on
y = 0, centred, the largest side 1 m) holding the cartridge; the cartridge holding the label's four screens over its
label (booting's noise, PICO-8's logo, and two frames of Odyssey being played), shrunk to nothing, so at rest the card
is the cartridge with Odyssey's title screen on its label.

The `focused` clip (8 s, looping) boots it: the cartridge crouches, hops and spins round once, and lands; its label
flickers into noise, PICO-8's logo comes up, and Odyssey plays, two frames turn about; then the title screen's back.

Three materials (case, print, screen) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/pico8_print.py artifacts/pico8
    blender -b --factory-startup --python tools/console-models/pico8.py -- artifacts/pico8 godot/themes/console/models/systems/pico8.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pico8_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, hop, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, export, join, material, new_object, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right edge comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: the face tips back a little
ROUGHNESS = dict(case=0.6, print=0.55, screen=0.3)
SCREENS = ("noise", "boot", "game1", "game2")


def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.PRINT_SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def point(u, v):
    """A cartridge pixel's corner (u right, v down from the top left) in the model's (x, z), the face's middle at
    x = 0."""
    return u * L.PX - L.WIDTH / 2, L.HEIGHT - v * L.PX


def outline():
    """The cartridge's outline in cartridge pixels, (u, v), round from its top edge: each corner a staircase of STEP
    pixel steps, the bottom right's the diagonal."""
    w, h, s = L.CART_PX[0], L.CART_PX[1], L.STEP
    tl, tr, bl, ch = (L.CORNERS[k] for k in ("top_left", "top_right", "bottom_left", "chamfer"))
    pts = [(tl * s, 0), (w - tr * s, 0)]
    for k in range(tr):
        pts += [(w - (tr - k) * s, (k + 1) * s), (w - (tr - k - 1) * s, (k + 1) * s)]
    pts.append((w, h - ch * s))
    for k in range(ch):
        pts += [(w - (k + 1) * s, h - (ch - k) * s), (w - (k + 1) * s, h - (ch - k - 1) * s)]
    for k in range(bl):
        pts += [((bl - k) * s, h - (k + 1) * s), ((bl - k - 1) * s, h - (k + 1) * s)]
    for k in range(tl - 1, -1, -1):
        pts += [(0, (k + 1) * s), ((tl - k) * s, (k + 1) * s)]
    clean = []
    for p in pts:                                  # drop repeats and points in the middle of a straight run
        if clean and p == clean[-1]:
            continue
        clean.append(p)
    out = []
    n = len(clean)
    for i, p in enumerate(clean):
        a, b = clean[i - 1], clean[(i + 1) % n]
        if (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0]) != 0:
            out.append(p)
    return out


def cartridge(m):
    """The cartridge, its middle at the origin's (x, y), standing on z = 0: three slices through its thickness, the
    middle one in a little (the seam); its face and back printed, its edges grey."""
    shape = [point(u, v) for u, v in outline()]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(shape, shape[1:] + shape[:1]))
    if area < 0:
        shape = list(reversed(shape))
    seam = inset(shape, L.SEAM)
    t, g = L.THICKNESS, 0.7
    slices = [(shape, -t / 2, -g), (seam, -g - 0.01, g + 0.01), (shape, g, t / 2)]
    parts = []
    for ring, y0, y1 in slices:
        part = solid("cart", [[(x, y, z) for x, z in ring] for y in (y0, y1)], m["case"])
        bevel(part, 0.25, segments=1)
        parts.append(part)
    cart = join(parts, "pico8")
    front = atlas_uv(L.PRINT_REGIONS["front"], L.WIDTH, L.HEIGHT)
    back = atlas_uv(L.PRINT_REGIONS["back"], L.WIDTH, L.HEIGHT)
    paint(cart, m["print"], lambda co: front(co.x + L.WIDTH / 2, L.HEIGHT - co.z),
          lambda c, n, name: n.y < -0.9 and c.y < -t / 2 + 0.1)
    paint(cart, m["print"], lambda co: back(L.WIDTH / 2 - co.x, L.HEIGHT - co.z),
          lambda c, n, name: n.y > 0.9 and c.y > t / 2 - 0.1)
    paint(cart, m["print"], swatch("edge"), lambda c, n, name: name == "case" and abs(c.y) > 0.75)
    paint(cart, m["print"], swatch("seam"), lambda c, n, name: name == "case")
    return cart


def screen(m, name, depth):
    """A screen over the label's window, its middle at its origin, facing -y."""
    u, v, w, h = L.LABEL
    (x0, z1), (x1, z0) = point(u, v), point(u + w, v + h)
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]                  # wound to face -y
    face = bm.faces.new([bm.verts.new((x - cx, 0.0, z - cz)) for x, z in corners])
    uv = atlas_uv(L.MEDIA_REGIONS[name], x1 - x0, z1 - z0)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = uv(x - x0, z1 - z)
    part = new_object("screen_" + name, bm, m["screen"])
    return part, Vector((cx, -L.THICKNESS / 2 - depth, cz))


# ---- The focused clip ------------------------------------------------------------------------------------------------

def timeline(f):
    # The cartridge crouches, hops and spins round once, lands with a wobble.
    crouch = 0.08 * smooth(phase(f, 12, 22)) * (1 - smooth(phase(f, 22, 26)))
    landing = wobble(f, 48, 0.07, period=9.0, decay=6.0)
    cart = Pose(z=hop(f, 24, 48, 24.0), spin=360.0 * smooth(phase(f, 24, 48)), squash=crouch + max(0.0, landing))

    # The label: noise, PICO-8's logo, then the game, two frames turn about; then the title screen again.
    shown = {name: False for name in SCREENS}
    if 50 <= f < 58:
        shown["noise"] = True
    elif 58 <= f < 92:
        shown["boot"] = True
    elif 92 <= f < 196:
        shown["game1" if ((f - 92) // 8) % 2 == 0 else "game2"] = True
    poses = {"pico8": cart}
    for name in SCREENS:
        poses["screen_" + name] = Pose() if shown[name] else Pose(scale=HIDDEN)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "pico8_print.png"))
    media = bpy.data.images.load(os.path.join(images, "pico8_media.png"))
    colours = dict(case=L.COLOURS["body"], print="#FFFFFF", screen="#FFFFFF")
    textures = dict(print=printed, screen=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    label, label_at = screen(m, "label", 0.05)
    label.data.transform(Matrix.Translation(label_at))
    cart = join([cartridge(m), label], "pico8")
    for p in cart.data.polygons:
        p.use_smooth = True
    cart.data.set_sharp_from_angle(angle=math.radians(35))
    screens = [screen(m, name, 0.1 + 0.05 * k) for k, name in enumerate(SCREENS)]

    root = bpy.data.objects.new("pico8_root", None)
    scene.collection.objects.link(root)
    cart.parent = root
    for part, where in screens:
        part.parent = cart
        part.location = where
    nodes = {"pico8": cart, **{part.name: part for part, _ in screens}}

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in cart.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [cart] + [part for part, _ in screens]
    print(f"PICO-8: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(cart.data)} the cartridge), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
