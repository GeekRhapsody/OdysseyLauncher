"""The console theme's PC Engine system model (godot/themes/console/models/systems/pcengine.glb): the white PC Engine,
a HuCard and its pad.

Built in Blender from the real console's proportions (pc_engine_layout.py has the measurements, taken from
photographs). The console is a rounded white box, the seam cut round it, the HuCard's channel cut into the middle of
its top from the front edge back to the slot (deep enough for the whole card), the thumb scoop at the channel's front
and the pad's socket in its front. The green POWER slider stands in its front at the left. The pad is a rounded slab
with the cable's dome along its back, its D-pad, II and I, SELECT and RUN on it. The printing is one texture drawn by
pc_engine_print.py (the console from above, planar-mapped onto every face facing up; its front; the HuCard's face; the
pad's top; swatches).

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the HuCard (waiting in the slot, shrunk to nothing), POWER, and the pad's D-pad, II, I and RUN.

The `focused` clip (8 s, looping) plays a game: the HuCard slides along the channel into the slot and POWER slides on
(on the real one, it locks the card in); RUN is pressed; the D-pad rocks and II and I are pressed in bursts; then POWER
slides off and the HuCard comes out and goes.

Four materials (case, pad, dark, print) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/pc_engine_print.py artifacts/pcengine
    blender -b --factory-startup --python tools/console-models/pc_engine.py -- artifacts/pcengine godot/themes/console/models/systems/pcengine.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc_engine_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, pad=0.5, dark=0.6, print=0.5)
PAD_W, PAD_D, PAD_H = L.PAD["size"]


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The console: the box, the seam, the channel and its scoop, the slot, the socket; its top and front printed."""
    w, d, h = L.WIDTH, L.DEPTH, L.HEIGHT
    body = box("pcengine", -w / 2, w / 2, 0.0, d, 0.0, h, m["case"])
    bevel(body, L.EDGE, segments=3)
    ring = box("seam", -w / 2 - 5.0, w / 2 + 5.0, -5.0, d + 5.0, L.SEAM - 0.5, L.SEAM + 0.5, m["dark"])
    boolean(ring, box("inner", -w / 2 + 0.8, w / 2 - 0.8, 0.8, d - 0.8, L.SEAM - 2.0, L.SEAM + 2.0, m["dark"]))
    boolean(body, ring)
    c = L.CHANNEL
    boolean(body, box("channel", *c["x"], -5.0, c["y"][1], c["floor"], h + 5.0, m["case"]))
    s = L.SCOOP
    boolean(body, prism("scoop", circle(0.0, s["y"], s["r"], 32), s["floor"], c["floor"] + 0.5, m["case"]))
    sl = L.SLOT
    boolean(body, box("slot", *sl["x"], c["y"][1] - 6.0, sl["y"][1], *sl["z"], m["dark"]))
    px, pz, r = L.PORT["x"], L.PORT["z"], L.PORT["r"]
    socket = solid("socket", [[(px + r * math.cos(2 * math.pi * k / 20), y, pz + r * math.sin(2 * math.pi * k / 20))
                               for k in range(20)] for y in (-5.0, 3.0)], m["dark"])
    boolean(body, socket)
    paint(body, m["print"], top_uv, lambda cc, n, name: n.z > 0.5 and name == "case")
    paint(body, m["print"], front_uv, lambda cc, n, name: n.y < -0.9 and name == "case" and cc.y < 0.5)
    return body


def power_slider(m):
    """POWER, its middle at its origin, at OFF (the left of its travel)."""
    (x0, x1), (z0, z1), out = L.POWER["x"], L.POWER["z"], L.POWER["out"]
    slider = painted(box("power", -(x1 - x0) / 2, (x1 - x0) / 2, -out, 2.0, -(z1 - z0) / 2, (z1 - z0) / 2,
                         m["print"]), m, "green")
    grip = painted(box("grip", -2.0, 2.0, -out - 1.6, -out + 0.5, -(z1 - z0) / 2 + 1.0, (z1 - z0) / 2 - 1.0,
                       m["print"]), m, "green")
    part = join([slider, grip], "power")
    bevel(part, 0.5, segments=1)
    return part, Vector(((x0 + x1) / 2, 0.0, (z0 + z1) / 2))


def hucard(m):
    """The HuCard, its middle at its origin, lying flat, its contacts' end towards +y (into the slot), its face up."""
    (w, length), t = L.CARD["size"], L.CARD["thickness"]
    card = box("hucard", -w / 2, w / 2, -length / 2, length / 2, -t / 2, t / 2, m["print"])
    bevel(card, 0.6, segments=1)
    face = atlas_uv(L.REGIONS["card"], w, length)
    paint(card, m["print"], lambda co: face(co.x + w / 2, length / 2 - co.y), lambda c, n, name: n.z > 0.9)
    paint(card, m["print"], swatch("white"), lambda c, n, name: n.z <= 0.9)
    return card


# ---- The pad ---------------------------------------------------------------------------------------------------------

def pad_frame():
    (px, py), turn = L.PAD["at"], L.PAD["turn"]
    return Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def pad(m):
    """The pad's body, its dome, SELECT and the fixed parts, at its place; its top printed."""
    p = L.PAD
    body = prism("pad", rounded(0.0, 0.0, PAD_W, PAD_D, p["r"], 4), 0.0, PAD_H, m["pad"])
    bevel(body, 3.0, segments=3)
    top = atlas_uv(L.REGIONS["pad"], PAD_W, PAD_D)
    paint(body, m["print"], lambda co: top(co.x + PAD_W / 2, PAD_D / 2 - co.y), lambda c, n, name: n.z > 0.9)
    dm = p["dome"]
    half = [(dm["r"] * math.cos(math.pi * (1 + k / 16)), dm["y"] + dm["r"] * math.sin(math.pi * (1 + k / 16)))
            for k in range(17)]                            # the half inside the pad, from its left round to its right
    dome = prism("dome", half, PAD_H - 1.0, PAD_H + dm["height"], m["pad"])
    bevel(dome, 1.8, segments=3)
    pw, ph = p["pill"]
    x, y = p["select"]
    select = painted(prism("select", [(x + a, y + b) for a, b in rounded(0.0, 0.0, pw, ph, ph / 2 - 0.1, 3)],
                           PAD_H - 1.0, PAD_H + 1.4, m["print"]), m, "white")
    parts = [body, dome, select]
    for part in parts:
        part.data.transform(pad_frame())
    return parts


def pad_parts(m):
    """The D-pad, II, I and RUN, each its middle at its origin, and where each goes."""
    p = L.PAD
    dx, dy, span, arm = p["dpad"]
    cross = [(arm / 2, -span / 2), (arm / 2, -arm / 2), (span / 2, -arm / 2), (span / 2, arm / 2), (arm / 2, arm / 2),
             (arm / 2, span / 2), (-arm / 2, span / 2), (-arm / 2, arm / 2), (-span / 2, arm / 2), (-span / 2, -arm / 2),
             (-arm / 2, -arm / 2), (-arm / 2, -span / 2)]
    dpad = painted(prism("dpad", cross, -2.0, 2.6, m["print"]), m, "grey")
    bevel(dpad, 0.6, segments=1)
    parts = [("dpad", dpad, Vector((dx, dy, 0.0)))]
    for name in ("ii", "i"):
        x, y = p[name]
        button = painted(prism(name, circle(0.0, 0.0, p["button_r"], 24), -2.0, 2.6, m["print"]), m, "grey")
        bevel(button, 1.0, segments=2)
        parts.append((name, button, Vector((x, y, 0.0))))
    pw, ph = p["pill"]
    run = painted(prism("run", rounded(0.0, 0.0, pw, ph, ph / 2 - 0.1, 3), -1.0, 1.4, m["print"]), m, "white")
    parts.append(("run", run, Vector((*p["run"], 0.0))))
    frame = pad_frame()
    turn = Matrix.Rotation(math.radians(L.PAD["turn"]), 4, "Z")
    placed = []
    for name, part, where in parts:
        part.data.transform(turn)
        at = frame @ where
        placed.append((name, part, Vector((at.x, at.y, PAD_H))))
    return placed


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 92.0           # how far in front of its seat the card waits: wholly out of the channel


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


PRESSES = dict(run=(52,), ii=(78, 84, 90, 120, 150), i=(100, 106, 112, 134, 140, 158))
ROCKS = [(64, 74, 0.0, 9.0), (96, 108, 0.0, -9.0), (126, 136, 9.0, 0.0), (150, 160, 0.0, 9.0)]


def timeline(f):
    if f < 6 or f >= 214:
        card = Pose(scale=HIDDEN)
    elif f < 16:
        card = Pose(y=-OUT, z=10.0, scale=appear(f, 6, 14))
    elif f < 22:
        card = Pose(y=-OUT, z=10.0 * (1 - smooth(phase(f, 16, 22))))
    elif f < 184:
        card = Pose(y=-OUT * (1 - smooth(phase(f, 22, 38))))
    elif f < 200:
        card = Pose(y=-OUT * smooth(phase(f, 184, 200)))
    else:
        t = ease_out(phase(f, 200, 208))
        card = Pose(y=-OUT, z=24.0 * t, scale=max(HIDDEN, 1 - ease_in(phase(f, 204, 214))))
    on = smooth(phase(f, 42, 48)) * (1 - smooth(phase(f, 172, 178)))
    poses = {"hucard": card, "power": Pose(x=L.POWER["travel"] * on)}
    for name, frames in PRESSES.items():
        poses[name] = Pose(z=-1.8 * max(tap(f, f0) for f0 in frames))
    pitch = roll = 0.0
    for f0, f1, pa, ro in ROCKS:
        t = smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f1, f1 + 4)))
        pitch, roll = pitch + pa * t, roll + ro * t
    poses["dpad"] = Pose(pitch=pitch, roll=roll)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "pc_engine_print.png"))
    colours = dict(case=L.COLOURS["case"], pad=L.COLOURS["pad"], dark=L.COLOURS["dark"], print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join([console(m)] + pad(m), "pcengine")
    slider, slider_at = power_slider(m)
    card_ = hucard(m)
    buttons = pad_parts(m)
    for obj in [whole, slider, card_] + [part for _, part, _ in buttons]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(40))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("pcengine_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    for part, where in [(slider, slider_at), (card_, Vector(L.SEAT))] + [(part, where) for _, part, where in buttons]:
        part.parent = whole
        part.location = where
    nodes = {"hucard": card_, "power": slider, **{name: part for name, part, _ in buttons}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, slider, card_] + [part for _, part, _ in buttons]
    print(f"PC Engine: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
