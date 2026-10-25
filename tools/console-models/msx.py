"""The console theme's MSX system model (godot/themes/console/models/systems/msx1.glb): a Philips VG-8020.

Built in Blender from the real machine's proportions (msx_layout.py has the measurements, taken from photographs).
Three shells: the light grey base, lofted from its feet in to the seam, the joystick recess cut into its front; the
keyboard deck, its side outline extruded across its width, cut for its wells; and the silver raised back, its outline
extruded too, cut for the lid's seat and the two cartridge slots under it. The keys stand in the wells (the /00's
QWERTY layout), tapering to their printed tops, light grey or dark grey as the real ones; RETURN is an inverted L, and
the cursor keys four wedges round a dark square. The power switch is a rocker in a bezel in the right end. The printing
is one texture drawn by msx_print.py: the top seen from above (planar-mapped onto every face facing up: the key tops
and legends, the raised back's lettering and lights, the lid's VG-8020), the joystick ports, the cartridge's label (a
made-up game, Odyssey), the switch's face, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (its origin on its hinge), the cartridge (waiting in its slot, shrunk to nothing), the lit POWER and
CAPS lights (shrunk to nothing), the power switch's rocker and the keys the clip presses.

The `focused` clip (8 s, looping) plays a game: the lid flips up and back, the cartridge drops into the front slot,
the switch rocks on and POWER lights; the cursor keys and the space bar are played, CAPS goes on and off. Then the
switch rocks off, the cartridge comes out and goes, and the lid shuts.

Seven materials (base, deck, silver, key_light, key_dark, black, print) and one texture, within the system model
budget. Run from the repo root:

    python tools/console-models/msx_print.py artifacts/msx
    blender -b --factory-startup --python tools/console-models/msx.py -- artifacts/msx godot/themes/console/models/systems/msx1.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msx_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(base=0.6, deck=0.55, silver=0.4, key_light=0.5, key_dark=0.5, black=0.3, print=0.45)
PLAYED = ("up", "down", "left", "right", "space", "caps")

# The deck's frame: x across, s up the slope from the deck's front edge, h off it.
SLOPE_FRAME = Matrix.Translation((0.0, L.DECK[0][0], L.DECK[0][1])) @ Matrix.Rotation(L.SLOPE, 4, "X")
PRESS = SLOPE_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    """The top seen from above."""
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def plan(w, d, r, z, inset_front, inset_side, segments=4):
    """A rounded rectangle at height z: the case's plan, in by inset_front at the front and back and inset_side at
    the ends, anticlockwise seen from above."""
    x0, x1, y0, y1 = -w / 2 + inset_side, w / 2 - inset_side, inset_front, d - inset_front
    points = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for k in range(segments + 1):
            a = math.radians(a0 + 90 * k / segments)
            points.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    return points


def on_slope(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline on the deck, from h0 to h1 off it."""
    return solid(name, [[SLOPE_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def base(m):
    """The base: lofted from its feet up the tapering lower band to the seam, the joystick recess in its front."""
    i, (ff, fs) = L.BASE["inset"], L.BASE["foot"]
    shell = solid("base", [plan(L.WIDTH, L.DEPTH, 4.0, 0.0, ff, fs), plan(L.WIDTH, L.DEPTH, 4.0, L.BASE["band"], i, i),
                           plan(L.WIDTH, L.DEPTH, 4.0, L.SEAM, i, i)], m["base"])
    (x0, x1), (z0, z1), depth = L.PORTS["x"], L.PORTS["z"], L.PORTS["depth"]
    face = i + depth
    boolean(shell, box("recess", x0, x1, -5.0, face, z0 - 2.0, z1, m["base"]))
    ports = atlas_uv(L.REGIONS["ports"], x1 - x0, z1 - z0)
    paint(shell, m["print"], lambda co: ports(co.x - x0, z1 - co.z),
          lambda c, n, name: n.y < -0.9 and abs(c.y - face) < 0.2 and x0 < c.x < x1)
    return shell


def deck(m):
    """The keyboard deck: its outline across the case, the wells cut into its top, the power switch's bezel."""
    shell = prism_x("deck", L.DECK_PROFILE, -L.WIDTH / 2, L.WIDTH / 2, m["deck"])
    bevel(shell, 1.6, segments=2)
    boolean(shell, join([on_slope("well", outline, -L.WELL, 14.0, m["black"]) for outline in L.wells()], "wells"))
    (y0, y1), (z0, z1) = L.SWITCH["y"], L.SWITCH["z"]
    bezel = box("bezel", L.WIDTH / 2 - 1.0, L.WIDTH / 2 + L.SWITCH["out"], y0, y1, z0, z1, m["black"])
    bevel(bezel, 0.5, segments=1)
    return [shell, bezel]


def raised_back(m):
    """The silver raised back: its outline across the case, the lid's seat and the two slots cut into it, its top
    printed."""
    shell = prism_x("back", L.BACK_PROFILE, -L.WIDTH / 2, L.WIDTH / 2, m["silver"])
    bevel(shell, 1.2, segments=2)
    (x0, x1), t = L.LID["x"], L.LID["thickness"]
    end = L.DEPTH - 4.0
    boolean(shell, box("seat", x0, x1, L.BACK_Y - 5.0, end, L.HEIGHT - t, L.HEIGHT + 5.0, m["black"]))
    boolean(shell, box("seat_front", x0, x1, L.BACK_Y - 5.0, L.BACK_Y + t, L.LID["flange"], L.HEIGHT, m["black"]))
    (sx0, sx1) = L.SLOTS["x"]
    boolean(shell, join([box("slot", sx0, sx1, y0, y1, L.SLOTS["bottom"], L.HEIGHT, m["black"])
                         for y0, y1 in L.SLOTS["y"]], "slots"))
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "silver" and c.z > L.HEIGHT - 0.5)
    return shell


def lid(m):
    """The lid, its origin on its hinge: a plate over the seat, its front edge bent down over the front face, its
    top printed."""
    (x0, x1), t = L.LID["x"], L.LID["thickness"]
    x0, x1 = x0 + 0.4, x1 - 0.4
    end = L.DEPTH - 4.0
    plate = box("lid", x0, x1, L.BACK_Y + 0.3, end - 0.4, L.HEIGHT - t + 0.3, L.HEIGHT, m["black"])
    flange = box("lid_flange", x0, x1, L.BACK_Y, L.BACK_Y + t, L.LID["flange"] + 0.4, L.HEIGHT, m["black"])
    shell = join([plate, flange], "lid")
    bevel(shell, 0.7, segments=2)
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and c.z > L.HEIGHT - 0.5)
    hinge = Vector((0.0, L.LID["hinge"][0], L.LID["hinge"][1]))
    shell.data.transform(Matrix.Translation(-hinge))
    return shell, hinge


def key_solid(name, outline, height, mat, m):
    """A key: from the well's floor up its sides, tapering to its printed top, height off the deck."""
    rings = [[(x, s, -L.WELL - 0.5) for x, s in outline], [(x, s, height - 4.5) for x, s in outline],
             [(x, s, height) for x, s in L.inset(outline, L.KEY_INSET)]]
    cap = solid(name, rings, mat)
    bevel(cap, 0.6, segments=1, angle=30)
    cap.data.transform(SLOPE_FRAME)
    paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.95)
    return cap


def keys(m):
    """The keys, standing in their wells: the cursor keys, the space bar and CAPS apart (the clip plays them)."""
    static, moving = [], {}
    for name, xu, row, wu, colour, _ in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        cap = key_solid(name, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], L.KEY_HEIGHT, m["key_" + colour], m)
        if name in PLAYED:
            moving[name] = cap
        else:
            static.append(cap)
    static.append(key_solid("return", L.return_outline(), L.KEY_HEIGHT, m["key_dark"], m))
    for name in ("up", "down", "left", "right"):
        moving[name] = key_solid(name, L.cursor_outline(name), L.CURSOR["height"], m["key_dark"], m)
    mx, ms = L.cursor_middle()
    iw, idp = L.CURSOR["inner"]
    square = L.inset([(mx - iw / 2, ms - idp / 2), (mx + iw / 2, ms - idp / 2), (mx + iw / 2, ms + idp / 2),
                      (mx - iw / 2, ms + idp / 2)], 0.6)
    plug = on_slope("plug", square, -L.WELL - 0.5, L.CURSOR["height"] - 2.0, m["deck"])
    bevel(plug, 0.6, segments=1)
    paint(plug, m["print"], top_uv, lambda c, n, _name: n.z > 0.95)
    static.append(plug)
    return static, moving


def lights(m):
    """The lit POWER and CAPS lights: each a window's glow just over its printed window, its middle at its origin."""
    parts = {}
    w, d = L.LIGHTS["size"]
    for name, colour in (("power", "red"), ("caps", "green")):
        x, y = L.LIGHTS[name]
        lit = box(name + "_light", x - w / 2 - 0.2, x + w / 2 + 0.2, y - d / 2 - 0.2, y + d / 2 + 0.2, L.HEIGHT + 0.05,
                  L.HEIGHT + 0.35, m["print"])
        paint(lit, m["print"], swatch(colour), lambda c, n, _name: True)
        middle = Vector((x, y, L.HEIGHT + 0.2))
        lit.data.transform(Matrix.Translation(-middle))
        parts[name + "_light"] = (lit, middle)
    return parts


def rocker(m):
    """The power switch's rocker, standing out of its bezel, its middle at its origin (it rocks about the
    vertical)."""
    (y0, y1), (z0, z1), out = L.SWITCH["y"], L.SWITCH["z"], L.SWITCH["out"]
    x = L.WIDTH / 2 + out
    part = box("rocker", x - 2.0, x + 0.9, y0 + 1.6, y1 - 1.6, z0 + 1.6, z1 - 1.6, m["black"])
    bevel(part, 0.4, segments=1)
    face = atlas_uv(L.REGIONS["rocker"], y1 - y0, z1 - z0)
    paint(part, m["print"], lambda co: face(co.y - y0, z1 - co.z), lambda c, n, name: n.x > 0.9)
    middle = Vector((x, (y0 + y1) / 2, (z0 + z1) / 2))
    part.data.transform(Matrix.Translation(-middle))
    return part, middle


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, its front (-y) towards the keyboard: the shell, the ribbed
    grip at its left, the label beside it."""
    w, d, h = L.CART["size"]
    lw, lh = L.CART["label"]
    shell = box("cartridge", -w / 2, w / 2, -d / 2, d / 2, 0.0, h, m["deck"])
    bevel(shell, 1.2, segments=2)
    lx1 = w / 2 - 3.0
    lx0, lz1 = lx1 - lw, h - 3.0
    lz0 = lz1 - lh
    g0, g1 = -w / 2 + L.CART["grip"][0], -w / 2 + L.CART["grip"][1]
    ribs = [box("rib", g0, g1, -d / 2 - 0.8, -d / 2 + 0.2, z - 0.7, z + 0.7, m["deck"])
            for z in (h - 12.0 - 5.0 * k for k in range(L.CART["ribs"]))]

    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    corners = [(lx0, lz0), (lx1, lz0), (lx1, lz1), (lx0, lz1)]                # wound to face -y
    face = bm.faces.new([bm.verts.new((x, -d / 2 - 0.12, z)) for x, z in corners])
    label_uv = atlas_uv(L.REGIONS["label"], lw, lh)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = label_uv(x - lx0, lz1 - z)
    sticker = new_object("label", bm, m["print"])
    return join([shell, sticker] + ribs, "cartridge")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


PLAY = dict(right=(70, 82), up=(94,), left=(106, 118), down=(130,), space=(142, 150, 158), caps=(168, 180))


def timeline(f):
    # The lid flips up and back, stays up while the game's in, and shuts once the cartridge has gone.
    if f < 214:
        swing = L.LID["open"] * back_out(phase(f, 10, 26), 1.2)
    else:
        swing = L.LID["open"] * (1 - smooth(phase(f, 214, 230))) + wobble(f, 230, 3.0, period=8.0, decay=3.0)
    lid = Pose(pitch=swing)

    # The cartridge: appears over its slot, drops in with a bump; later rises out and goes.
    if f < 24 or f >= 212:
        cart = Pose(scale=HIDDEN)
    elif f < 34:
        cart = Pose(z=70.0, scale=appear(f, 24, 32))
    elif f < 46:
        cart = Pose(z=70.0 * (1 - ease_in(phase(f, 34, 46))))
    elif f < 196:
        cart = Pose(squash=0.05 * math.sin(math.pi * phase(f, 46, 52)))
    else:
        cart = Pose(z=70.0 * ease_out(phase(f, 196, 206)), scale=max(HIDDEN, 1 - ease_in(phase(f, 204, 212))))

    on = smooth(phase(f, 54, 58)) * (1 - smooth(phase(f, 188, 192)))
    caps_on = 171 <= f < 183
    poses = {"lid": lid, "cartridge": cart, "rocker": Pose(spin=-7.0 + 14.0 * on),
             "power_light": Pose() if 58 <= f < 190 else Pose(scale=HIDDEN),
             "caps_light": Pose() if caps_on else Pose(scale=HIDDEN)}
    for name, frames in PLAY.items():
        d = 2.8 * max(tap(f, f0) for f0 in frames)
        poses[name] = Pose(x=PRESS.x * d, y=PRESS.y * d, z=PRESS.z * d)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "msx_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    static, moving = keys(m)
    whole = join([base(m), raised_back(m)] + deck(m) + static, "msx")
    cover, hinge = lid(m)
    cart = cartridge(m)
    switch, switch_at = rocker(m)
    lit = lights(m)
    for obj in [whole, cover, cart, switch] + list(moving.values()):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("msx_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    placed = [(cover, hinge), (cart, Vector(L.SEAT)), (switch, switch_at)] + list(lit.values())
    for part, where in placed:
        part.parent = whole
        part.location = where
    for part in moving.values():
        part.parent = whole
    nodes = {"lid": cover, "cartridge": cart, "rocker": switch, **{name: part for name, (part, _) in lit.items()},
             **moving}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, cover, cart, switch] + [part for part, _ in lit.values()] + list(moving.values())
    print(f"MSX: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
