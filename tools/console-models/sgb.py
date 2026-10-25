"""The console theme's Super Game Boy system model (godot/themes/console/models/systems/sgb.glb): the Super Game Boy in
the European Super Nintendo's slot, a Game Boy cartridge going into it.

Built in Blender. The console is snes.py's own, built by its functions; the adapter (sgb_layout.py has its
measurements) is its outline given its thickness, the notch in its top and the Game Boy cartridge's slot below it, its
front printed, standing in the console's slot; the Game Boy cartridge is its outline (its corner cut) given its
thickness, its label printed. The printing is two textures: snes_print.py's (the console) and sgb_print.py's (the
adapter's front, the Game Boy cartridge's label), both drawn into the same folder.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set (the
console and the adapter in its slot); the set holding the Game Boy cartridge (waiting over the adapter, shrunk to
nothing), POWER's knob and the power light (shrunk to nothing while it's off).

The `focused` clip (8 s, looping): the Game Boy cartridge appears over the adapter, turns once to show its label and
drops into its slot; POWER slides on and the light comes on; later POWER goes off and the cartridge rises out and goes.

Six materials (the console's case, print, dark and cart; sgb, gb) and two textures, within the system model budget.
Run from the repo root:

    python tools/console-models/snes_print.py snes artifacts/sgb
    python tools/console-models/sgb_print.py artifacts/sgb
    blender -b --factory-startup --python tools/console-models/sgb.py -- artifacts/sgb godot/themes/console/models/systems/sgb.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgb_layout as L  # noqa: E402
import snes  # noqa: E402
import snes_layout as N  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def arc(cx, cz, r, a0, a1, n):
    """n + 1 points round an arc from a0 to a1 degrees."""
    angles = [math.radians(a0 + (a1 - a0) * k / n) for k in range(n + 1)]
    return [(cx + r * math.cos(a), cz + r * math.sin(a)) for a in angles]


def adapter(m):
    """The Super Game Boy in its own frame (x across, z up from its connector's edge, its front facing -y): its
    outline with the notch, the slot below the notch; its front printed."""
    w, h, t, r = L.SGB["width"], L.SGB["height"], L.SGB["thickness"], L.SGB["corner"]
    nw, nd, nr = L.NOTCH["width"], L.NOTCH["depth"], L.NOTCH["r"]
    floor = h - nd
    outline = [(-w / 2, 0.0), (w / 2, 0.0)] + arc(w / 2 - r, h - r, r, 0, 90, 4)
    outline += arc(nw / 2 + nr, h - nr, nr, 90, 180, 3)[:-1] + arc(nw / 2 - nr, floor + nr, nr, 0, -90, 3)
    outline += arc(-nw / 2 + nr, floor + nr, nr, -90, -180, 3) + arc(-nw / 2 - nr, h - nr, nr, 0, 90, 3)[1:]
    outline += arc(-w / 2 + r, h - r, r, 90, 180, 4)
    part = solid("sgb", [[(x, y, z) for x, z in outline] for y in (-t / 2, t / 2)], m["sgb"])
    sw, st, sd, sy = L.SLOT["width"], L.SLOT["thickness"], L.SLOT["depth"], L.SLOT["y"]
    boolean(part, box("slot", -sw / 2, sw / 2, sy - st / 2, sy + st / 2, floor - sd, floor + 5.0, m["sgb"]))
    bevel(part, 1.2, segments=2, angle=40)
    paint(part, m["sgb"], swatch("sgb"), lambda c, n, kind: True)
    face = atlas_uv(L.REGIONS["front"], w, h)
    paint(part, m["sgb"], lambda co: face(co.x + w / 2, h - co.z), lambda c, n, kind: n.y < -0.9)
    paint(part, m["sgb"], swatch("dark"),
          lambda c, n, kind: abs(c.x) < sw / 2 + 0.5 and abs(c.y - sy) < st / 2 + 0.5 and c.z < floor - 0.5)
    return part


def game_boy_cartridge(m):
    """The Game Boy cartridge, its bottom's middle at its origin, its label facing -y: its outline, the corner cut at
    the top right (seen from the label's side)."""
    w, h, t, cut = L.GB["width"], L.GB["height"], L.GB["thickness"], L.GB["cut"]
    outline = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h - cut), (w / 2 - cut, h), (-w / 2, h)]
    part = solid("game_boy_cartridge", [[(x, y, z) for x, z in outline] for y in (-t / 2, t / 2)], m["gb"])
    bevel(part, 0.8, segments=2, angle=40)
    paint(part, m["gb"], swatch("gb"), lambda c, n, kind: True)
    face = atlas_uv(L.REGIONS["gb"], w, h)
    paint(part, m["gb"], lambda co: face(co.x + w / 2, h - co.z), lambda c, n, kind: n.y < -0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

def timeline(f):
    above = L.GB["above"]
    if f < 8 or f >= 210:
        cart = Pose(z=above, scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 8, 15))))
    elif f < 34:
        cart = Pose(z=above + 3.0 * math.sin(math.pi * phase(f, 16, 34)), spin=360.0 * smooth(phase(f, 16, 34)))
    elif f < 46:
        cart = Pose(z=above * (1 - ease_in(phase(f, 34, 46))))
    elif f < 184:
        settle = 1.6 * math.exp(-(f - 46) / 3.0) * abs(math.sin(math.pi * (f - 46) / 5.0))
        cart = Pose(z=settle)
    elif f < 200:
        cart = Pose(z=above * ease_out(phase(f, 184, 200)))
    else:
        cart = Pose(z=above, scale=max(HIDDEN, 1 - ease_in(phase(f, 200, 210))))
    on = smooth(phase(f, 54, 58)) * (1 - smooth(phase(f, 172, 176)))
    return {"game_boy_cartridge": cart, "power": Pose(y=N.POWER["travel"] * on),
            "power_light": Pose() if 58 <= f < 174 else Pose(scale=HIDDEN)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    console_print = bpy.data.images.load(os.path.join(images, "snes_print.png"))
    sgb_print = bpy.data.images.load(os.path.join(images, "sgb_print.png"))
    k = N.KINDS["snes"]
    colours = dict(case=k["case"], print="#FFFFFF", dark=N.COLOURS["dark"], cart=N.COLOURS["cart"])
    m = {n: material(n, colours[n], r, console_print if n == "print" else None) for n, r in snes.ROUGHNESS.items()}
    m["sgb"] = material("sgb", "#FFFFFF", 0.5, sgb_print)
    m["gb"] = material("gb", "#FFFFFF", 0.45, sgb_print)

    seat = Vector((0.0, sum(N.SLOT["y"]) / 2, N.TOP + N.PANEL["height"] - L.SGB["inserted"]))
    unit = adapter(m)
    unit.data.transform(Matrix.Translation(seat))
    whole = join([snes.body(m), snes.eject(m), unit], "sgb")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))
    slide = snes.knob(m)
    lit, lit_at = snes.light(m)
    cart = game_boy_cartridge(m)
    for obj in (slide, cart):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("sgb_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    floor = L.SGB["height"] - L.NOTCH["depth"]
    cart_at = seat + Vector((0.0, L.SLOT["y"], floor - L.GB["seat"]))
    nodes = {"game_boy_cartridge": cart, "power": slide, "power_light": lit}
    for part, where in ((cart, cart_at), (slide, Vector()), (lit, lit_at)):
        part.parent = whole
        part.location = where

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"Super Game Boy: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
