"""The console theme's Nintendo DS system model (godot/themes/console/models/systems/nds.glb).

Built in Blender from the DS Lite's proportions (nintendo_ds_layout.py has the measurements, taken from photographs), open
on the table: the lower half, its plan's outline lofted up through the rounding of its edges, with the D-pad, A, B, X
and Y, START and SELECT standing out of its face, slot-1 and the stylus's silo in its back face, and the hinge along its
back; the upper half, built the same way and tipped up about the hinge. The printing (the faces: the screens' bezels,
the switched-off screens, the buttons' tops and legends, the speakers) is one texture, drawn by nintendo_ds_print.py
and projected onto each half's face; the screens and the game card's label are a second.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: its right end towards the viewer, its
face tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the console; the
console holding the game card (Odyssey, a made-up game), the stylus, and the screens switched on (the start-up screen
and the menu, then the game's title, TOUCH TO START and that button pressed). The card and the stylus wait in their
places shrunk to nothing and the screens are shrunk to nothing, so at rest the card is the console open, its screens
off.

The `focused` clip (8 s, looping) plays a game: the card pops up high above the console, showing its label, turns flat
and slides into slot-1 behind the upper half; both screens come on, the start-up screen and the menu, then the game; the
stylus slides out of its silo, flies over the upper half and taps TOUCH TO START twice, and flies back in; then the
screens go off and the card pops out and goes.

Five materials (case, print, dark, media, accent) and two textures, within the system model budget. Run from the repo
root:

    python tools/console-models/nintendo_ds_print.py nds artifacts/nds
    blender -b --factory-startup --python tools/console-models/nintendo_ds.py -- artifacts/nds nds godot/themes/console/models/systems/nds.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nintendo_ds_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 25.0    # degrees about the horizontal: the face tips up towards the viewer
ROUGHNESS = dict(case=0.25, print=0.25, dark=0.5, media=0.3, accent=0.35)


def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def rounded_slab(name, w, d, cy, z0, z1, corner, edge, mat, steps=3):
    """A slab w x d about (0, cy) from z0 to z1, its corners rounded seen from above and its top and bottom edges
    rounded over by edge."""
    rings = []
    for k in range(steps + 1):
        a = math.pi / 2 * (1 - k / steps)
        inset = edge * (1 - math.cos(a))
        rings.append([(x, y, z0 + edge * (1 - math.sin(a))) for x, y in
                      rounded(0.0, cy, w - 2 * inset, d - 2 * inset, corner - inset, 4)])
    for k in range(steps + 1):
        a = math.pi / 2 * k / steps
        inset = edge * (1 - math.cos(a))
        rings.append([(x, y, z1 - edge * (1 - math.sin(a))) for x, y in
                      rounded(0.0, cy, w - 2 * inset, d - 2 * inset, corner - inset, 4)])
    return solid(name, rings, mat)


def quad(name, x0, x1, y0, y1, z, uv, mat):
    """A flat face facing up, (x0..x1, y0..y1) at z, its UVs uv(a, b) with a and b from 0 to 1 (b down)."""
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]                    # wound to face up
    face = bm.faces.new([bm.verts.new((x, y, z)) for x, y in corners])
    for loop, (x, y) in zip(face.loops, corners):
        loop[layer].uv = uv((x - x0) / (x1 - x0), (y1 - y) / (y1 - y0))
    return new_object(name, bm, mat)


# ---- The console -----------------------------------------------------------------------------------------------------

def lower_half(k, m):
    w, d, h = k["width"], k["depth"], k["lower"]
    shell = rounded_slab("nds", w, d, d / 2, 0.0, h, k["corner"], k["edge"], m["case"])
    (x0, x1), (z0, z1) = k["slot"]["x"], k["slot"]["z"]
    boolean(shell, box("slot", x0, x1, d - 12.0, d + 5.0, z0, z1, m["dark"]))
    s = k["stylus"]
    silo = [(s["x"] + (s["r"] + 0.4) * math.cos(2 * math.pi * j / 16), s["z"] + (s["r"] + 0.4) * math.sin(2 * math.pi * j / 16))
            for j in range(16)]
    boolean(shell, solid("silo", [[(x, y, z) for x, z in silo] for y in (d - 30.0, d + 5.0)], m["dark"]))
    face = atlas_uv(L.PRINT_REGIONS["lower"], w, d)
    paint(shell, m["print"], lambda co: face(co.x + w / 2, d - co.y), lambda c, n, name: n.z > 0.9 and name == "case")

    parts = [shell]
    p = k["dpad"]
    length, width = p["arm"]
    for horizontal in (True, False):
        a, b = (length / 2, width / 2) if horizontal else (width / 2, length / 2)
        arm = box("dpad", p["x"] - a, p["x"] + a, p["y"] - b, p["y"] + b, h - 1.0, h + p["height"], m["accent"])
        bevel(arm, 0.5, segments=1)
        parts.append(arm)
    f = k["face"]
    for dx, dy in ((1, 0), (0, -1), (0, 1), (-1, 0)):
        x, y = f["x"] + dx * f["reach"], f["y"] + dy * f["reach"]
        parts.append(button(x, y, f["r"], h, f["height"], m))
    for _, x, y, r in k["small"]:
        parts.append(button(x, y, r, h, 0.8, m))
    for part in parts[1:]:
        paint(part, m["print"], lambda co: face(co.x + w / 2, d - co.y), lambda c, n, name: n.z > 0.9)

    # The hinge along the back edge.
    hg = k["hinge"]
    ring = [(hg["r"] * math.cos(2 * math.pi * j / 24), hg["r"] * math.sin(2 * math.pi * j / 24)) for j in range(24)]
    hinge = solid("hinge", [[(x, hg["y"] + a, hg["z"] + b) for a, b in ring] for x in (-hg["x"], hg["x"])], m["case"])
    parts.append(hinge)
    return parts


def button(x, y, r, base, height, m):
    rings = [[(x + (r - inset) * math.cos(2 * math.pi * j / 24), y + (r - inset) * math.sin(2 * math.pi * j / 24),
               base + z) for j in range(24)] for inset, z in ((0.0, -1.0), (0.0, height - 0.4), (0.5, height))]
    return solid("button", rings, m["accent"])


def upper_half(k, m):
    """The upper half, tipped up about the hinge: built flat with its face up and its hinge edge along y = 0, then
    turned and moved onto the hinge. Returns its parts and the transform that places them."""
    w, d, t = k["width"], k["depth"] - 2.0, k["upper"]
    shell = rounded_slab("upper", w, d, d / 2, -t, 0.0, k["corner"], k["edge"], m["case"])
    face = atlas_uv(L.PRINT_REGIONS["upper"], w, d)
    paint(shell, m["print"], lambda co: face(co.x + w / 2, d - co.y), lambda c, n, name: n.z > 0.9)
    hg = k["hinge"]
    place = (Matrix.Translation((0.0, hg["y"] - hg["r"] * 0.2, hg["z"] + hg["r"] * 0.6))
             @ Matrix.Rotation(math.radians(k["open"]), 4, "X") @ Matrix.Translation((0.0, -1.0, 0.0)))
    shell.data.transform(place)
    return shell, place


def screens(k, m):
    """The screens switched on: each a face just over its screen, its middle at its origin, and where it goes."""
    out = {}
    s = k["screen"]
    sw, sh = s["size"]
    for name in ("boot_lower", "game_lower", "game_pressed"):
        uv = atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0)
        out[name] = (quad("screen_" + name, -sw / 2, sw / 2, -sh / 2, sh / 2, 0.0, uv, m["media"]),
                     Matrix.Translation((s["x"], s["y"], k["lower"] + 0.06)))
    u = k["upper_screen"]
    uw, uh = u["size"]
    hg = k["hinge"]
    place = (Matrix.Translation((0.0, hg["y"] - hg["r"] * 0.2, hg["z"] + hg["r"] * 0.6))
             @ Matrix.Rotation(math.radians(k["open"]), 4, "X") @ Matrix.Translation((0.0, -1.0 + u["y"], 0.06)))
    for name in ("boot_upper", "game_upper"):
        uv = atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0)
        out[name] = (quad("screen_" + name, -uw / 2, uw / 2, -uh / 2, uh / 2, 0.0, uv, m["media"]), place)
    return out


def card(m):
    """The game card, its middle at its origin, lying flat with its label up and its contacts' edge towards -y."""
    c = L.CARD
    w, l, t = c["width"], c["length"], c["thickness"]
    shell = box("card", -w / 2, w / 2, -l / 2, l / 2, -t / 2, t / 2, m["media"])
    bevel(shell, 0.6, segments=1)
    label = atlas_uv(L.MEDIA_REGIONS["card"], w, l)
    paint(shell, m["media"], lambda co: label(co.x + w / 2, l / 2 - co.y), lambda c_, n, name: n.z > 0.9)
    paint(shell, m["print"], swatch("card"), lambda c_, n, name: n.z <= 0.9)
    return shell


def stylus(k, m):
    """The stylus, its middle at its origin, lying along y with its tip towards -y."""
    s = k["stylus"]
    r, half = s["r"], s["length"] / 2
    rings = [[(rr * math.cos(2 * math.pi * j / 12), y, rr * math.sin(2 * math.pi * j / 12)) for j in range(12)]
             for rr, y in ((0.4, -half), (r * 0.7, -half + 5.0), (r, -half + 9.0), (r, half - 1.0), (r * 0.8, half))]
    return solid("stylus", rings, m["accent"])


# ---- The focused clip ------------------------------------------------------------------------------------------------

def shown(f, f0, f1):
    """A screen on between f0 and f1, opening and closing about its middle."""
    if f < f0 or f >= f1:
        return Pose(scale=HIDDEN)
    v = min(ease_out(phase(f, f0, f0 + 4)), 1 - ease_in(phase(f, f1 - 4, f1)))
    return Pose(axes=(1.0, max(HIDDEN, v), 1.0))


def timeline(f, c):
    poses = {}
    # The card: pops up high above, label to the viewer, turns flat behind the console and slides into slot-1; at the
    # end it pops out and goes.
    behind, high = 45.0, c["high"]
    if f < 10 or f >= 222:
        poses["card"] = Pose(scale=HIDDEN)
    elif f < 26:
        poses["card"] = Pose(y=behind - 20.0, z=high, pitch=90.0, spin=12.0 * math.sin(f / 2.0),
                             scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 10, 18)))
    elif f < 48:
        t = smooth(phase(f, 26, 48))
        poses["card"] = Pose(y=behind - 20.0 + 20.0 * t, z=high * (1 - t), pitch=90.0 * (1 - t), spin=360.0 * t)
    elif f < 204:
        poses["card"] = Pose(y=behind * (1 - ease_in(phase(f, 48, 58))))
    else:
        t = phase(f, 204, 222)
        poses["card"] = Pose(y=24.0 * back_out(phase(f, 204, 210)) + 30.0 * t, z=60.0 * ease_in(t),
                             scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 222))))

    # The screens: the start-up screen and the menu, then the game; TOUCH TO START pressed at each tap.
    poses["screen_boot_upper"] = shown(f, 62, 98)
    poses["screen_boot_lower"] = shown(f, 62, 98)
    poses["screen_game_upper"] = shown(f, 98, 202)
    tapped = 146 <= f < 151 or 156 <= f < 162
    poses["screen_game_lower"] = shown(f, 98, 202) if not tapped else Pose(scale=HIDDEN)
    poses["screen_game_pressed"] = Pose() if tapped else Pose(scale=HIDDEN)

    # The stylus: out of its silo backwards, up over the upper half, down onto TOUCH TO START twice, and home.
    out, over_y, over_x, touch = c["out"], c["over_y"], c["over_x"], c["touch"]
    if f < 110 or f >= 198:
        poses["stylus"] = Pose(scale=HIDDEN)
    elif f < 122:
        poses["stylus"] = Pose(y=out * ease_out(phase(f, 110, 122)), scale=HIDDEN + (1 - HIDDEN) * phase(f, 110, 112))
    elif f < 140:
        t = smooth(phase(f, 122, 140))
        poses["stylus"] = Pose(x=over_x * t, y=out + (over_y - out) * t, z=high * math.sin(math.pi * t) + touch * t + 14.0 * t,
                               pitch=72.0 * t)
    elif f < 166:
        dips = (1 - smooth(phase(f, 140, 146))) * 14.0 + (smooth(phase(f, 150, 153)) - smooth(phase(f, 153, 156))) * 9.0
        dips += smooth(phase(f, 160, 166)) * 14.0
        poses["stylus"] = Pose(x=over_x, y=over_y, z=touch + dips, pitch=72.0)
    else:
        t = smooth(phase(f, 166, 188))
        z = touch + 14.0 + (high - touch - 14.0) * math.sin(math.pi * t) - (touch + 14.0) * t
        poses["stylus"] = Pose(x=over_x * (1 - t), y=over_y + (out - over_y) * t, z=z, pitch=72.0 * (1 - t))
        if f >= 188:
            poses["stylus"] = Pose(y=out * (1 - ease_in(phase(f, 188, 198))))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, kind, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    k = L.KINDS[kind]
    printed = bpy.data.images.load(os.path.join(images, f"{kind}_print.png"))
    media = bpy.data.images.load(os.path.join(images, f"{kind}_media.png"))
    colours = dict(case=k["colour"], print="#FFFFFF", dark=k["dark"], media="#FFFFFF", accent=k["accent"])
    textures = dict(print=printed, media=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    lid, _ = upper_half(k, m)
    console = join(lower_half(k, m) + [lid], kind)
    for p in console.data.polygons:
        p.use_smooth = True
    console.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new(kind + "_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    nodes = {}
    for name, (part, place) in screens(k, m).items():
        part.parent = console
        part.matrix_basis = place
        nodes["screen_" + name] = part
    d = k["depth"]
    playing = card(m)
    playing.parent = console
    playing.location = (0.0, d - L.CARD["length"] / 2 - 1.0, sum(k["slot"]["z"]) / 2)
    pen = stylus(k, m)
    pen.parent = console
    s = k["stylus"]
    pen.location = (s["x"], d - s["length"] / 2 - 1.0, s["z"])
    nodes["card"], nodes["stylus"] = playing, pen

    # The three-quarter view, then the spec's fit of the console at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in console.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    # The stylus's flight, in its own place's offsets: back out of its silo, over the lower screen's button.
    sc = k["screen"]
    context = dict(high=95.0, out=s["length"] + 6.0, over_y=sc["y"] + 2.0 - pen.location.y,
                   over_x=sc["x"] + 4.0 - s["x"], touch=k["lower"] + s["length"] / 2 * math.sin(math.radians(72.0))
                   - s["z"] + 0.6)
    key("focused", nodes, lambda f: timeline(f, context), L.LENGTH)
    meshes = [console] + list(nodes.values())
    print(f"Nintendo DS ({kind}): {sum(triangles(o.data) for o in meshes)} triangles ({triangles(console.data)} the "
          f"console), {len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
