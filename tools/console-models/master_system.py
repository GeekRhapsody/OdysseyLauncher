"""The console theme's Master System model (godot/themes/console/models/systems/mastersystem.glb): the first Sega
Master System and its Control Pad.

Built in Blender from the real console's proportions (master_system_layout.py has the measurements, taken from
photographs). The console is its side outline extruded across its width (the front band, the bevel, the hood's top
rising to the ridge, the back's slope), its ends sloped in above the slab and ribbed below it; the red panel is sunk
into the hood's right part, sloping more gently, with the cartridge slot at its back; POWER's recess, the ports' recess
and the card slot are cut into the front band. RESET and PAUSE stand on the panel, POWER in its recess, and the dust
flap closes the slot. The Control Pad lies in front of the console's left end: its body, the raised block at its back
right, the D-pad in its well and the two buttons. The printing is one texture drawn by master_system_print.py (the top
seen from above, planar-mapped onto every face facing up; the front band seen from in front; the cartridge's label; the
pad's top; and swatches).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting in the slot, shrunk to nothing), the dust flap (on its hinge), POWER, PAUSE, the
D-pad and the pad's two buttons.

The `focused` clip (8 s, looping) plays a game: the cartridge drops into the slot, the flap swinging down out of its
way, and POWER goes in; the D-pad rocks and the buttons are pressed, PAUSE twice; then POWER again, and the cartridge
comes out and goes, the flap swinging shut.

Five materials (case, dark, button, cart, print) and one texture, within the system model budget. Run from the
repo root:

    python tools/console-models/master_system_print.py artifacts/mastersystem
    blender -b --factory-startup --python tools/console-models/master_system.py -- artifacts/mastersystem godot/themes/console/models/systems/mastersystem.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import master_system_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.45, dark=0.8, button=0.5, cart=0.5, print=0.45)
FRONT_H = L.BAND["bevel"][1]


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, FRONT_H)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, FRONT_H - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


# ---- The console -----------------------------------------------------------------------------------------------------

PANEL_SLOPE = math.atan2(L.PANEL["z"][1] - L.PANEL["z"][0], L.PANEL["y"][1] - L.PANEL["y"][0])
PANEL_FRAME = Matrix.Translation((0.0, L.PANEL["y"][0], L.PANEL["z"][0])) @ Matrix.Rotation(PANEL_SLOPE, 4, "X")


def panel_y(y):
    """The panel's (y, z) frame: the distance along its slope of the point over y."""
    return (y - L.PANEL["y"][0]) / math.cos(PANEL_SLOPE)


def console(m):
    """The console: the body with its ends sloped and ribbed, the panel's recess, the slot and the front band's
    recesses cut, its top and front printed."""
    body = prism_x("mastersystem", L.profile(), -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 1.5, segments=2)
    top, inset = L.ENDS["top"], L.ENDS["inset"]
    reach = inset * (L.HEIGHT + 10.0 - top) / (L.HEIGHT - top)
    for side in (-1, 1):                                  # the hood's ends, sloping in from the slab's ends
        e = side * L.WIDTH / 2
        outline = [(e, top), (e + side * 20.0, top), (e + side * 20.0, L.HEIGHT + 10.0), (e - side * reach, L.HEIGHT + 10.0)]
        cutter = solid("end", [[(x, y, z) for x, z in outline] for y in (-5.0, L.DEPTH + 5.0)], m["case"])
        boolean(body, cutter)
    r = L.RIBS
    boolean(body, join([box("rib", x0, x1, 10.0, L.DEPTH - 10.0, z - r["width"] / 2, z + r["width"] / 2, m["dark"])
                        for z in r["z"] for x0, x1 in ((L.WIDTH / 2 - r["depth"], L.WIDTH / 2 + 5.0),
                                                        (-L.WIDTH / 2 - 5.0, -L.WIDTH / 2 + r["depth"]))], "ribs"))
    (x0, x1), (y0, y1), (z0, z1) = L.PANEL["x"], L.PANEL["y"], L.PANEL["z"]
    boolean(body, prism_x("panel", [(y0, z0), (y1, z1), (y1, L.HEIGHT + 20.0), (y0, L.HEIGHT + 20.0)], x0, x1,
                          m["case"]))
    s = L.SLOT
    boolean(body, box("slot", *s["x"], *s["y"], s["bottom"], L.HEIGHT + 10.0, m["dark"]))
    p = L.POWER
    boolean(body, box("power_well", p["x"][0] - 1.0, p["x"][1] + 1.0, -5.0, 4.0, p["z"][0] - 1.0, p["z"][1] + 1.0,
                      m["dark"]))
    q = L.PORTS
    boolean(body, box("ports", *q["x"], -5.0, q["depth"], q["z"][0] - 6.0, q["z"][1], m["dark"]))
    c = L.CARD
    boolean(body, box("card", *c["x"], -5.0, c["depth"], c["z"][0] - 6.0, c["z"][1], m["dark"]))
    paint(body, m["print"], top_uv, lambda cc, n, name: n.z > 0.5 and name == "case")
    paint(body, m["print"], front_uv, lambda cc, n, name: n.y < -0.9 and cc.z < FRONT_H and cc.y < 12.0)
    return body


def panel_button(name, x0, x1, m):
    """A button on the red panel, standing off its slope."""
    (a, b), h = L.BUTTONS["y"], L.BUTTONS["height"]
    s0, s1 = panel_y(a), panel_y(b)
    button = solid(name, [[PANEL_FRAME @ Vector((x, s, z)) for x, s in ((x0, s0), (x1, s0), (x1, s1), (x0, s1))]
                          for z in (-1.0, h)], m["button"])
    bevel(button, 0.5, segments=1)
    return button


def power_button(m):
    p = L.POWER
    button = box("power", p["x"][0], p["x"][1], -p["out"], 4.0, p["z"][0], p["z"][1], m["button"])
    bevel(button, 0.6, segments=1)
    return button


def flap(m):
    """The slot's dust flap, its origin on its hinge just behind the slot's front edge: it hangs there, out of the
    cartridge's way, once swung down."""
    (x0, x1), (y0, y1) = L.SLOT["x"], L.SLOT["y"]
    plate = box("flap", x0 + 1.0, x1 - 1.0, y0 + 0.1, y1 - 0.4, L.SLOT["flap"] - 0.8, L.SLOT["flap"], m["print"])
    paint(plate, m["print"], swatch("grey"), lambda c, n, name: True)
    hinge = Vector((0.0, y0 + 0.9, L.SLOT["flap"]))
    plate.data.transform(Matrix.Translation(-hinge))
    return plate, hinge


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, its front (-y) towards the player: the shell, three grooves
    under the label, the label."""
    w, t, h = L.CART["size"]
    lw, lh = L.CART["label"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["cart"])
    bevel(shell, 1.0, segments=2)
    grooves = [box("groove", -w / 2 - 1.0, w / 2 + 1.0, -t / 2 - 1.0, -t / 2 + 0.5, z - 0.4, z + 0.4, m["dark"])
               for z in (h - lh - 6.0, h - lh - 8.0, h - lh - 10.0)]
    boolean(shell, join(grooves, "grooves"))
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    x0, x1, z0, z1 = -lw / 2, lw / 2, h - 2.5 - lh, h - 2.5
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]                  # wound to face -y
    face = bm.faces.new([bm.verts.new((x, -t / 2 - 0.12, z)) for x, z in corners])
    label_uv = atlas_uv(L.REGIONS["label"], lw, lh)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = label_uv(x - x0, z1 - z)
    sticker = new_object("label", bm, m["print"])
    return join([shell, sticker], "cartridge")


# ---- The Control Pad -------------------------------------------------------------------------------------------------

def pad_frame():
    (px, py), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def pad(m):
    """The pad's body, at its place: the lower body, the raised block, the D-pad's well, its top printed."""
    w, d, h = L.PAD["size"]
    b = L.PAD["block"]
    body = solid("pad", [[(x, y, z) for x, y in rounded(0.0, 0.0, w, d, 4.0, 3)] for z in (0.0, h - b["height"])],
                 m["case"])
    boolean(body, box("block", *b["x"], *b["y"], h - b["height"] - 1.0, h, m["case"]), "UNION")
    bevel(body, 1.2, segments=2)
    x0, x1, y0, y1 = L.PAD["well"]
    boolean(body, box("well", x0, x1, y0, y1, h - b["height"] - 2.0, h, m["case"]))
    top = atlas_uv(L.REGIONS["pad"], w, d)
    paint(body, m["print"], lambda co: top(co.x + w / 2, d / 2 - co.y), lambda c, n, name: n.z > 0.9)
    body.data.transform(pad_frame())
    return body


def pad_parts(m):
    """The D-pad and the two buttons, each its middle at its origin, and where each goes."""
    w, d, h = L.PAD["size"]
    top = h - L.PAD["block"]["height"]
    x0, x1, y0, y1 = L.PAD["well"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s, dh = L.PAD["dpad"]["size"], L.PAD["dpad"]["height"]
    ring = rounded(0.0, 0.0, s, s, 6.0, 3)
    dpad = solid("dpad", [[(x, y, z) for x, y in ring] for z in (-1.0, dh - 1.5)]
                 + [[(x * 0.9, y * 0.9, dh) for x, y in ring]], m["button"])
    bevel(dpad, 0.6, segments=1)
    parts = [("dpad", dpad, Vector((cx, cy, top - 2.0)))]
    b = L.PAD["buttons"]
    for k, x in enumerate(b["x"]):
        disc = [(b["r"] * math.cos(2 * math.pi * j / 20), b["r"] * math.sin(2 * math.pi * j / 20)) for j in range(20)]
        button = solid(f"button{k + 1}", [[(xx, yy, z) for xx, yy in disc] for z in (-1.5, b["height"])], m["button"])
        bevel(button, 0.6, segments=1)
        parts.append((f"button{k + 1}", button, Vector((x, b["y"], top))))
    frame = pad_frame()
    for _, part, _ in parts:
        part.data.transform(Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z"))
    return [(name, part, frame @ where) for name, part, where in parts]


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def rock(f, f0, f1):
    """The D-pad held over from f0 to f1: over in three frames, back in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f1, f1 + 4)))


ROCKS = [(62, 72, 0.0, 9.0), (78, 88, 0.0, 9.0), (96, 104, 9.0, 0.0), (136, 148, 0.0, -9.0)]   # f0, f1, pitch, roll
PRESSES = dict(button1=(110, 120, 156), button2=(128,), pause=(170, 182), power=(42, 196))


def timeline(f):
    # The cartridge: appears over its slot, drops in with a bump; later rises out and goes.
    if f < 6 or f >= 224:
        cart = Pose(scale=HIDDEN)
    elif f < 18:
        cart = Pose(z=70.0, scale=appear(f, 6, 16))
    elif f < 30:
        cart = Pose(z=70.0 * (1 - ease_in(phase(f, 18, 30))))
    elif f < 204:
        cart = Pose(squash=0.05 * math.sin(math.pi * phase(f, 30, 36)))
    else:
        cart = Pose(z=70.0 * ease_out(phase(f, 204, 216)), scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 224))))

    # The flap swings down as the cartridge comes, and back up once it's gone.
    swing = -80.0 * smooth(phase(f, 20, 25)) * (1 - smooth(phase(f, 214, 222)))
    poses = {"cartridge": cart, "flap": Pose(pitch=swing)}

    pitch = roll = 0.0
    for f0, f1, p, r in ROCKS:
        t = rock(f, f0, f1)
        pitch, roll = pitch + p * t, roll + r * t
    poses["dpad"] = Pose(pitch=pitch, roll=roll)
    for name, frames in PRESSES.items():
        d = max(tap(f, f0) for f0 in frames)
        if name == "power":
            poses[name] = Pose(y=2.0 * d)
        elif name == "pause":
            n = (PANEL_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0)))
            poses[name] = Pose(x=n.x * 1.6 * d, y=n.y * 1.6 * d, z=n.z * 1.6 * d)
        else:
            poses[name] = Pose(z=-2.0 * d)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "master_system_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    reset = panel_button("reset", *L.BUTTONS["reset"], m)
    whole = join([console(m), reset, pad(m)], "mastersystem")
    pause = panel_button("pause", *L.BUTTONS["pause"], m)
    power = power_button(m)
    cover, hinge = flap(m)
    cart = cartridge(m)
    parts = pad_parts(m)
    for obj in [whole, pause, power, cart] + [part for _, part, _ in parts]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("mastersystem_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    seat = Vector(((L.SLOT["x"][0] + L.SLOT["x"][1]) / 2, L.SLOT["y"][0] + 1.0 + L.CART["size"][1] / 2,
                   L.HEIGHT - 1.0 - L.CART["inserted"]))
    for part, where in [(cover, hinge), (cart, seat)] + [(part, where) for _, part, where in parts]:
        part.parent = whole
        part.location = where
    for part in (pause, power):
        part.parent = whole
    nodes = {"cartridge": cart, "flap": cover, "pause": pause, "power": power, **{name: part for name, part, _ in parts}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, pause, power, cover, cart] + [part for _, part, _ in parts]
    print(f"Master System: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
