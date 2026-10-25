"""The console theme's VIC-20 system model (godot/themes/console/models/systems/vic20.glb): a Commodore VIC-20 in front
of the portable television the ZX Spectrum's card has, its start-up screen on it.

Built in Blender from the real machine's proportions (vic20_layout.py has the measurements, taken from photographs).
The breadbin is its side outline extruded across its width (the front rounding into the top, the top sloping up, the
back rounding down), the seam cut round it, the keyboard's wells cut into its top and the expansion port into its back.
Its 66 keys (the UK layout) stand in the main well, tapering to their printed tops, and the four function keys in
theirs; the power switch is a rocker in its right end. Behind it stands zx_spectrum.py's television. The printing is
two textures drawn by vic20_print.py: the computer's top seen from above (planar-mapped onto every face facing up: the
key tops and legends, the badge, the power light, the ribs), the cartridge's label and the television's front, with
swatches; and the glass's screens.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting in the expansion port, shrunk to nothing), the power switch's rocker, the lit power
light, two screens over the glass (black, and the title screen of a made-up game, Odyssey), and the keys the clip
presses. At rest the card is the set switched on, READY. on the screen.

The `focused` clip (8 s, looping) plays a cartridge the way the VIC-20 wants it: the switch goes off, the light and the
picture with it; the cartridge comes down behind it and slides into the expansion port; the switch goes on and Odyssey's
title comes up; f1 starts it, Z, X and the space bar play it. Then off again, the cartridge comes out and goes, and on:
READY.

Seven materials (case, key, tan, print, tv, dark, glass) and two textures, within the system model budget. Run from
the repo root:

    python tools/console-models/vic20_print.py artifacts/vic20
    blender -b --factory-startup --python tools/console-models/vic20.py -- artifacts/vic20 godot/themes/console/models/systems/vic20.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vic20_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from amiga import curved, paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402
from zx_spectrum import atlas_uv, television  # noqa: E402

TILT_YAW = -26.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 24.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, key=0.5, tan=0.5, print=0.5, tv=0.4, dark=0.6, glass=0.2)
PLAYED = ("f1", "z", "x", "space")

# The top's frame: x across, s up the slope from its front edge, h off it.
SLOPE_FRAME = Matrix.Translation((0.0, *L.FRONT["top"])) @ Matrix.Rotation(L.SLOPE, 4, "X")
PRESS = SLOPE_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame

TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def on_slope(name, outline, h0, h1, mat):
    return solid(name, [[SLOPE_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


# ---- The computer ----------------------------------------------------------------------------------------------------

def computer(m):
    """The breadbin: its outline across its width, the seam, the wells and the expansion port cut; its top printed."""
    w = L.WIDTH
    body = prism_x("vic20", L.profile(), -w / 2, w / 2, m["case"])
    bevel(body, 2.0, segments=2)
    ring = box("seam", -w / 2 - 5.0, w / 2 + 5.0, -5.0, L.DEPTH + 5.0, L.SEAM - 0.5, L.SEAM + 0.5, m["dark"])
    boolean(ring, box("inner", -w / 2 + 0.9, w / 2 - 0.9, 0.9, L.DEPTH - 0.9, L.SEAM - 2.0, L.SEAM + 2.0, m["dark"]))
    boolean(body, ring)
    boolean(body, join([on_slope("well", outline, -L.WELL, 16.0, m["dark"]) for outline in L.wells()], "wells"))
    p = L.PORT
    boolean(body, box("port", *p["x"], L.DEPTH - p["depth"], L.DEPTH + 5.0, *p["z"], m["dark"]))
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.5 and name == "case")
    return body


def key_solid(name, outline, mat, m):
    """A key: from the well's floor up its sides, tapering to its printed top."""
    h = L.KEY_HEIGHT
    rings = [[(x, s, -L.WELL - 0.5) for x, s in outline], [(x, s, h - 5.0) for x, s in outline],
             [(x, s, h) for x, s in inset(outline, L.KEY_INSET)]]
    cap = solid(name, rings, mat)
    bevel(cap, 0.7, segments=1, angle=30)
    cap.data.transform(SLOPE_FRAME)
    paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
    return cap


def keys(m):
    """The keys in their wells: the ones the clip presses apart."""
    static, moving = [], {}
    for name, xu, row, wu, colour, _ in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        cap = key_solid(name, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], m["key"], m)
        if name in PLAYED:
            moving[name] = cap
        else:
            static.append(cap)
    for name, row, _ in L.FKEYS:
        x0, s0 = L.FKEYS_X + L.GAP / 2, L.ROW_S[row] + L.GAP / 2
        x1, s1 = L.FKEYS_X + L.FKEY_W * L.U - L.GAP / 2, L.ROW_S[row] + L.U - L.GAP / 2
        cap = key_solid(name, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], m["tan"], m)
        if name in PLAYED:
            moving[name] = cap
        else:
            static.append(cap)
    return static, moving


def rocker(m):
    """The power switch's rocker, standing out of the right end, its middle at its origin (it rocks about y)."""
    (y0, y1), (z0, z1), out = L.SWITCH["y"], L.SWITCH["z"], L.SWITCH["out"]
    x = L.WIDTH / 2
    part = box("rocker", x - 2.0, x + out, y0, y1, z0, z1, m["dark"])
    bevel(part, 0.6, segments=1)
    middle = Vector((x, (y0 + y1) / 2, (z0 + z1) / 2))
    part.data.transform(Matrix.Translation(-middle))
    return part, middle


def light(m):
    """The power light lit: a dome just over the printed one, its middle at its origin."""
    y, z = L.top_point(L.LIGHT["s"], 0.0)
    r = L.LIGHT["r"]
    part = solid("light", [[(r * k * math.cos(2 * math.pi * i / 12), r * k * math.sin(2 * math.pi * i / 12), dz)
                            for i in range(12)] for k, dz in ((1.0, -0.6), (1.0, 0.5), (0.5, 1.1))], m["print"])
    part.data.transform(Matrix.Rotation(L.SLOPE, 4, "X"))
    paint(part, m["print"], swatch("lit"), lambda c, n, name: True)
    return part, Vector((L.LIGHT["x"], y, z))


def cartridge(m):
    """The cartridge, its middle at its origin, lying flat, its connector's edge towards -y (into the port), its
    label up, reading from the front."""
    (w, d, h), (ew, eo, et) = L.CART["size"], L.CART["edge"]
    case = box("cartridge", -w / 2, w / 2, -d / 2, d / 2, -h / 2, h / 2, m["print"])
    bevel(case, 1.5, segments=2)
    paint(case, m["print"], swatch("cart"), lambda c, n, name: True)
    lw, ld = L.CART["label"]
    label_uv = atlas_uv(L.REGIONS["label"], lw, ld)
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    corners = [(-lw / 2, -ld / 2), (lw / 2, -ld / 2), (lw / 2, ld / 2), (-lw / 2, ld / 2)]   # wound to face +z
    face = bm.faces.new([bm.verts.new((x, y, h / 2 + 0.12)) for x, y in corners])
    for loop, (x, y) in zip(face.loops, corners):
        loop[layer].uv = label_uv(x + lw / 2, ld / 2 - y)
    sticker = new_object("label", bm, m["print"])
    edge = box("edge", -ew / 2, ew / 2, -d / 2 - eo, -d / 2 + 1.0, -et / 2, et / 2, m["print"])
    paint(edge, m["print"], swatch("dark"), lambda c, n, name: True)
    return join([case, sticker, edge], "cartridge")


def screens(m):
    """The glass's other screens, each its middle at its origin: black (off) and the game's title."""
    gw, gh = SL.TV["glass"]["size"]
    media = {"black": lambda a, b: atlas_uv(L.MEDIA_REGIONS["black"], 1.0, 1.0)(0.5, 0.5),
             "title": atlas_uv(L.MEDIA_REGIONS["title"], 1.0, 1.0)}
    return {name: curved("screen_" + name, gw, gh, SL.TV["glass"]["bulge"], uv, m["glass"], 20, 16)
            for name, uv in media.items()}


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


PRESSES = dict(f1=(84,), z=(108, 124, 140, 156), x=(116, 132, 148), space=(100, 164))
BACK, DROP = 20.0, 70.0   # how far behind its seat the cartridge waits (clear of the television), and how high


def on(f):
    """Whether the computer is switched on: off from 14 to 56 (the cartridge goes in), and from 176 to 216."""
    return not (14 <= f < 56 or 176 <= f < 216)


def timeline(f):
    # The cartridge: comes down behind the port and slides in; later slides out, rises and goes.
    if f < 20 or f >= 210:
        cart = Pose(scale=HIDDEN)
    elif f < 30:
        cart = Pose(y=BACK, z=DROP, scale=appear(f, 20, 28))
    elif f < 38:
        cart = Pose(y=BACK, z=DROP * (1 - smooth(phase(f, 30, 38))))
    elif f < 184:
        cart = Pose(y=BACK * (1 - smooth(phase(f, 38, 50))))
    elif f < 196:
        cart = Pose(y=BACK * smooth(phase(f, 184, 196)))
    else:
        t = ease_out(phase(f, 196, 204))
        cart = Pose(y=BACK, z=DROP * t, scale=max(HIDDEN, 1 - ease_in(phase(f, 202, 210))))

    switched = 1.0 if on(f) else 0.0
    poses = {"cartridge": cart, "rocker": Pose(roll=-10.0 + 20.0 * switched),
             "light": Pose() if switched else Pose(scale=HIDDEN),
             "screen_black": Pose() if 14 <= f < 62 or 176 <= f < 220 else Pose(scale=HIDDEN),
             "screen_title": Pose() if 62 <= f < 176 else Pose(scale=HIDDEN)}
    for name, frames in PRESSES.items():
        d = 3.0 * max(tap(f, f0) for f0 in frames)
        poses[name] = Pose(x=PRESS.x * d, y=PRESS.y * d, z=PRESS.z * d)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "vic20_print.png"))
    media = bpy.data.images.load(os.path.join(images, "vic20_media.png"))
    colours = dict(case=L.COLOURS["case"], key=L.COLOURS["key"], tan=L.COLOURS["tan"], print="#FFFFFF",
                   tv=SL.COLOURS["tv"], dark="#0A0A0B", glass="#FFFFFF")
    textures = dict(print=printed, glass=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    static, moving = keys(m)
    tv = television(m, m["glass"], atlas_uv(L.MEDIA_REGIONS["boot"], 1.0, 1.0))
    shift = Matrix.Translation((L.TV_AT[0] - SL.TV["at"][0], L.TV_AT[1] - SL.TV["at"][1], 0.0))
    for part in tv:
        part.data.transform(shift)
    whole = join([computer(m)] + static + tv, "vic20")
    switch, switch_at = rocker(m)
    lit, lit_at = light(m)
    cart = cartridge(m)
    glass = screens(m)
    for obj in [whole, switch, cart] + list(moving.values()):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("vic20_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (w, d, h), p = L.CART["size"], L.PORT
    seat = Vector(((p["x"][0] + p["x"][1]) / 2, L.DEPTH + d / 2, (p["z"][0] + p["z"][1]) / 2))
    s = SL.TV["screen"]
    glass_front = Vector((L.TV_AT[0] + s["x"], L.TV_AT[1] + s["depth"], s["z"]))
    placed = [(switch, switch_at), (lit, lit_at), (cart, seat)]
    placed += [(part, glass_front + Vector((0.0, -0.4 - 0.1 * k, 0.0))) for k, part in enumerate(glass.values())]
    for part, where in placed:
        part.parent = whole
        part.location = where
    for part in moving.values():
        part.parent = whole
    nodes = {"cartridge": cart, "rocker": switch, "light": lit, **{"screen_" + k: v for k, v in glass.items()},
             **moving}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p_[i] for p_ in points) for i in range(3)])
    hi = Vector([max(p_[i] for p_ in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, switch, lit, cart] + list(glass.values()) + list(moving.values())
    print(f"VIC-20: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
