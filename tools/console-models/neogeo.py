"""The console theme's Neo Geo system model (godot/themes/console/models/systems/neogeo.glb): a Neo Geo AES and its
arcade stick.

Built in Blender from the real console's proportions (neogeo_layout.py has the measurements, taken from photographs).
The console is its side outline extruded across its width, a wedge rising from its low front to its tall back; the
racetrack is a stadium raised over the sloping top, its trough and the cartridge slot cut into it; the vents behind
it, RESET's dish, the controller ports and the memory card slot are cut too. The stick is a rounded wedge, the lever's
dish cut into it, the four buttons on their arc and SELECT and START standing on it. The printing is two textures
drawn by neogeo_print.py: the console from above (planar-mapped onto every face facing up) and its front, with
swatches; and the stick from above and the cartridge's label.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting in the slot, shrunk to nothing), POWER, RESET, and the stick's lever, its four buttons
and START.

The `focused` clip (8 s, looping) plays a fighting game: the cartridge drops into the slot, POWER slides on and START
is pressed; then the lever rolls down to forward and A goes in, a fireball's motion, twice, then a combo of B, C and D;
RESET; and POWER slides off and the cartridge comes out and goes.

Six materials (case, dark, button, cart, print, pad) and two textures, within the system model budget. Run from the
repo root:

    python tools/console-models/neogeo_print.py artifacts/neogeo
    blender -b --factory-startup --python tools/console-models/neogeo.py -- artifacts/neogeo godot/themes/console/models/systems/neogeo.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neogeo_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, dark=0.7, button=0.45, cart=0.5, print=0.55, pad=0.55)
PAD_W, PAD_D = L.PAD["size"]
CEILING = L.HEIGHT + 20.0    # above everything: cutters reach up to here


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.FRONT_H)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.FRONT_H - co.z)


def swatch(name, swatches=L.SWATCHES):
    x, y = swatches[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def on_top(name, outline, rise0, rise1, mat):
    """A solid from an (x, y) outline, from rise0 to rise1 over the sloping top (its faces planes parallel to it)."""
    return solid(name, [[(x, y, L.top_z(y) + r) for x, y in outline] for r in (rise0, rise1)], mat)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The console: the wedge, the racetrack raised on it, the trough, slot, vents, dish, ports and card slot cut;
    its top and front printed."""
    body = prism_x("neogeo", L.profile(), -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 2.0, segments=2)
    t = L.TRACK
    (x0, x1), (y0, y1) = t["x"], t["y"]
    outer = rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, (y1 - y0) / 2 - 0.1, 8)
    track = on_top("track", outer, -6.0, t["rise"], m["case"])
    bevel(track, 2.2, segments=3, angle=30)
    boolean(body, track, "UNION")
    b = t["band"]
    inner = rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 2 * b, y1 - y0 - 2 * b, (y1 - y0) / 2 - b - 0.1, 8)
    boolean(body, on_top("trough", inner, t["rise"] - t["trough"], t["rise"] + 20.0, m["case"]))
    s = L.SLOT
    boolean(body, box("slot", *s["x"], *s["y"], L.top_z(s["y"][1]) - s["depth"], CEILING, m["dark"]))
    v = L.VENTS
    boolean(body, join([on_top("vent", [(a, y - v["width"] / 2), (c, y - v["width"] / 2), (c, y + v["width"] / 2),
                                         (a, y + v["width"] / 2)], -v["depth"], 10.0, m["dark"])
                        for a, c in v["groups"] for y in v["y"]], "vents"))
    rx, ry = L.RESET["at"]
    boolean(body, on_top("dish", circle(rx, ry, L.RESET["dish"], 32), -2.5, 10.0, m["case"]))
    w, h = L.PORTS["size"]
    boolean(body, join([solid("port", [[(x + a, y, L.PORTS["z"] + c) for a, c in
                                        ((-w / 2, h / 2), (w / 2, h / 2), (w / 2 - 2.0, -h / 2), (-w / 2 + 2.0, -h / 2))]
                                       for y in (-5.0, L.PORTS["depth"])], m["dark"]) for x in L.PORTS["x"]], "ports"))
    c = L.CARD_SLOT
    boolean(body, box("card", *c["x"], -5.0, c["depth"], *c["z"], m["dark"]))
    paint(body, m["print"], top_uv, lambda cc, n, name: n.z > 0.5 and name == "case")
    paint(body, m["print"], front_uv, lambda cc, n, name: n.y < -0.9 and name == "case" and cc.y < 1.0)
    return body



def power_slider(m):
    (x0, x1), (z0, z1), out = L.POWER["x"], L.POWER["z"], L.POWER["out"]
    slider = box("power", -(x1 - x0) / 2 + 4.0, -(x1 - x0) / 2 + 10.0, -out, 1.0, -(z1 - z0) / 2, (z1 - z0) / 2,
                 m["button"])
    bevel(slider, 0.5, segments=1)
    return slider, Vector(((x0 + x1) / 2, 0.0, (z0 + z1) / 2))


def reset_button(m):
    rx, ry = L.RESET["at"]
    r, h = L.RESET["r"], L.RESET["height"]
    button = prism("reset", circle(0.0, 0.0, r, 24), -3.0, h, m["button"])
    bevel(button, 1.6, segments=2)
    return button, Vector((rx, ry, L.top_z(ry) - 2.5))


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, its label (-y) to the front: the shell, its raised middle,
    the ribs round its foot, the label."""
    w, t, h = L.CART["size"]
    tw, th = L.CART["tab"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["cart"])
    tab = box("tab", -tw / 2, tw / 2, -t / 2, t / 2, h - 2.0, h + th, m["cart"])
    shell = join([shell, tab], "cartridge")
    bevel(shell, 2.0, segments=2)
    ribs = [box("rib", -w / 2 - 1.0, w / 2 + 1.0, -t / 2 - 1.0, t / 2 + 1.0, z - 0.5, z + 0.5, m["dark"])
            for z in (6.0 + 4.0 * k for k in range(L.CART["ribs"]))]
    boolean(shell, join(ribs, "ribs"))
    lw, lh = L.CART["label"]
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    x0, x1, z0, z1 = -lw / 2, lw / 2, h + th - 4.0 - lh, h + th - 4.0
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]                  # wound to face -y
    face = bm.faces.new([bm.verts.new((x, -t / 2 - 0.12, z)) for x, z in corners])
    uv = atlas_uv(L.PAD_REGIONS["label"], lw, lh)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = uv(x - x0, z1 - z)
    sticker = new_object("label", bm, m["pad"])
    return join([shell, sticker], "cartridge")


# ---- The stick -------------------------------------------------------------------------------------------------------

def pad_frame():
    (px, py), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def pad_z(y):
    """The stick's top's height at y (from its middle): a wedge from its front up to its back."""
    h0, h1 = L.PAD["heights"]
    return h0 + (h1 - h0) * (y + PAD_D / 2) / PAD_D


def stick_body(m):
    """The stick's body at its place: a rounded wedge, the lever's dish cut into it, SELECT and START on it, its top
    printed."""
    p = L.PAD
    outline = rounded(0.0, 0.0, PAD_W, PAD_D, p["r"], 4)
    body = solid("stick", [[(x, y, 0.0) for x, y in outline], [(x, y, pad_z(y)) for x, y in outline]], m["pad"])
    bevel(body, 4.0, segments=3, angle=30)
    dx, dy, r = p["dish"]
    boolean(body, solid("dish", [[(x, y, pad_z(y) - 2.0) for x, y in circle(dx, dy, r, 40)],
                                 [(x, y, pad_z(y) + 10.0) for x, y in circle(dx, dy, r, 40)]], m["pad"]))
    top = atlas_uv(L.PAD_REGIONS["stick"], PAD_W, PAD_D)
    paint(body, m["pad"], lambda co: top(co.x + PAD_W / 2, PAD_D / 2 - co.y), lambda c, n, name: n.z > 0.8)
    paint(body, m["pad"], swatch("dark", L.PAD_SWATCHES), lambda c, n, name: n.z <= 0.8)
    parts = [body]
    sw, sh = p["small"]
    x, y = p["select"]
    select = solid("select", [[(x + a, y + b, pad_z(y + b) + dz) for a, b in rounded(0.0, 0.0, sw, sh, sh / 2 - 0.2, 3)]
                              for dz in (-1.0, 2.6)], m["button"])
    bevel(select, 0.8, segments=1)
    parts.append(select)
    for part in parts:
        part.data.transform(pad_frame())
    return parts


def stick_parts(m):
    """The lever, the four buttons and START, each its origin where it pivots or its middle, and where each goes."""
    p = L.PAD
    parts = []
    dx, dy, _ = p["dish"]
    w0, length = p["shaft"]
    shaft = prism("shaft", circle(0.0, 0.0, w0, 16), -2.0, length, m["dark"])
    ball = solid("ball", [[(p["ball"] * math.cos(math.radians(lat)) * math.cos(2 * math.pi * k / 20),
                            p["ball"] * math.cos(math.radians(lat)) * math.sin(2 * math.pi * k / 20),
                            length + p["ball"] * 0.8 + p["ball"] * math.sin(math.radians(lat)))
                           for k in range(20)] for lat in range(-80, 81, 20)], m["dark"])
    lever = join([shaft, ball], "lever")
    for poly in lever.data.polygons:
        poly.use_smooth = True
    parts.append(("lever", lever, Vector((dx, dy, pad_z(dy) - 2.0))))
    for k, (x, y) in enumerate(p["buttons"]):
        button = prism(f"button_{'abcd'[k]}", circle(0.0, 0.0, p["button_r"], 28), -3.0, 4.0, m["button"])
        bevel(button, 1.6, segments=2)
        parts.append((f"button_{'abcd'[k]}", button, Vector((x, y, pad_z(y)))))
    sw, sh = p["small"]
    x, y = p["start"]
    start = prism("start", rounded(0.0, 0.0, sw, sh, sh / 2 - 0.2, 3), -1.0, 2.6, m["button"])
    bevel(start, 0.8, segments=1)
    parts.append(("start", start, Vector((x, y, pad_z(y)))))
    frame = pad_frame()
    turn = Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z")
    placed = []
    for name, part, where in parts:
        part.data.transform(turn)
        placed.append((name, part, frame @ where))
    return placed


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


PRESSES = dict(start=(54,), button_a=(86, 120), button_b=(140, 152), button_c=(146, 158), button_d=(164,),
               reset=(182,))
FIREBALLS = (72, 106)        # each a quarter circle from down to forward, then A
TILT = 16.0                  # degrees the lever leans


def lever(f):
    """The lever: a quarter circle from down through down-forward to forward for each fireball; a waggle in the
    combo."""
    pitch = roll = 0.0
    for f0 in FIREBALLS:
        if f0 - 3 <= f < f0 + 16:
            t = phase(f, f0, f0 + 10)
            a = math.radians(-90.0 + 90.0 * smooth(t))              # from down (towards the player) round to right
            lean = TILT * smooth(phase(f, f0 - 3, f0)) * (1 - smooth(phase(f, f0 + 12, f0 + 16)))
            pitch, roll = -lean * math.sin(a), -lean * math.cos(a)
    if 136 <= f < 170:
        roll = -TILT * 0.7 * math.sin(2 * math.pi * (f - 136) / 11)
    return Pose(pitch=pitch, roll=roll)


def timeline(f):
    if f < 6 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=90.0, scale=appear(f, 6, 14))
    elif f < 30:
        cart = Pose(z=90.0 * (1 - ease_in(phase(f, 16, 30))))
    elif f < 206:
        cart = Pose(squash=0.04 * math.sin(math.pi * phase(f, 30, 36)))
    else:
        cart = Pose(z=90.0 * ease_out(phase(f, 206, 218)), scale=max(HIDDEN, 1 - ease_in(phase(f, 216, 226))))
    on = smooth(phase(f, 38, 44)) * (1 - smooth(phase(f, 196, 202)))
    poses = {"cartridge": cart, "power": Pose(x=L.POWER["travel"] * on), "lever": lever(f)}
    for name, frames in PRESSES.items():
        poses[name] = Pose(z=-(2.4 if name.startswith("button") else 1.6) * max(tap(f, f0) for f0 in frames))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "neogeo_print.png"))
    pad_image = bpy.data.images.load(os.path.join(images, "neogeo_pad.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", pad="#FFFFFF")
    textures = dict(print=printed, pad=pad_image)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    whole = join([console(m)] + stick_body(m), "neogeo")
    slider, slider_at = power_slider(m)
    reset, reset_at = reset_button(m)
    cart = cartridge(m)
    parts = stick_parts(m)
    for obj in [whole, slider, reset, cart] + [part for _, part, _ in parts if part.name != "lever"]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(40))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("neogeo_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    s = L.SLOT
    seat = Vector((0.0, (s["y"][0] + s["y"][1]) / 2, L.top_z((s["y"][0] + s["y"][1]) / 2) - L.CART["inserted"]))
    placed = [(slider, slider_at), (reset, reset_at), (cart, seat)] + [(part, where) for _, part, where in parts]
    for part, where in placed:
        part.parent = whole
        part.location = where
    nodes = {"cartridge": cart, "power": slider, "reset": reset, **{name: part for name, part, _ in parts}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, slider, reset, cart] + [part for _, part, _ in parts]
    print(f"Neo Geo: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
