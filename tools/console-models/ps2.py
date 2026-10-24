"""The console theme's PlayStation 2 system model (godot/themes/console/models/systems/ps2.glb).

Built in Blender from the black launch model's proportions (ps2_layout.py has the measurements, taken from
photographs), lying flat: the upper body, its front a stack of fins (five grooves cut across it), the disc tray in its
door in the middle of the front, the power and eject buttons standing out at its right end; and under it the base, set
back at its front. The printing (the top's PS2 logo and the formats' marks; the front's slots, ports, legends, the mark
on the tray's door, the lights and SONY; the base's grille and blue panel) is one texture, drawn by ps2_print.py and
projected onto the top and the fronts; the DVD's two sides are a second.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: its right end towards the viewer, its
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the console; the
console holding the tray (which holds the DVD: Odyssey, a made-up game), the eject button and the power light lit
green. The DVD waits on the tray shrunk to nothing and the light is shrunk to nothing, so at rest the card is the
console in standby, its tray shut.

The `focused` clip (8 s, looping) plays a game: eject goes in and the tray slides out; the DVD drops onto it spinning
and settles; the tray slides back in and the power light turns from red to green. Later eject again: the tray comes
out, the DVD rises spinning and goes, and the tray goes back in.

Four materials (case, print, dark, disc) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/ps2_print.py artifacts/ps2
    blender -b --factory-startup --python tools/console-models/ps2.py -- artifacts/ps2 godot/themes/console/models/systems/ps2.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps2_layout as L  # noqa: E402
from amiga import paint  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402
from psx import cylinder, ring_solid  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 25.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.42, print=0.42, dark=0.7, disc=0.25)


def atlas_uv(region, w, h, size=(L.ATLAS, L.ATLAS)):
    """A face drawn w x h into region: (a, b) across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / size[0], 1 - (ry + b / h * rh) / size[1])


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT - L.BASE["height"])


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def grooves(m, x0, x1):
    """The fins' grooves across a front from x0 to x1."""
    g, depth = L.GROOVE
    return join([box("groove", x0, x1, -1.0, depth, z - g / 2, z + g / 2, m["dark"]) for z in L.GROOVES], "grooves")


def body(m):
    w, z0 = L.WIDTH, L.BASE["height"]
    upper = box("ps2", -w / 2, w / 2, 0.0, L.DEPTH, z0, L.HEIGHT, m["case"])
    bevel(upper, 1.5, segments=2)
    boolean(upper, grooves(m, -w / 2 + 1.5, w / 2 - 1.5))
    t = L.TRAY
    boolean(upper, box("tray_bay", *t["x"], -1.0, t["depth"], *t["z"], m["dark"]))
    paint(upper, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "case")
    paint(upper, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < 0.5 and name == "case")

    (x0, x1), y0, h = L.BASE["x"], L.BASE["y"], L.BASE["height"]
    under = box("base", x0, x1, y0, L.DEPTH - 6.0, 0.0, h + 1.0, m["case"])
    bevel(under, 1.0, segments=1)
    base = atlas_uv(L.REGIONS["base"], x1 - x0, h)
    paint(under, m["print"], lambda co: base(co.x - x0, h - co.z),
          lambda c, n, name: n.y < -0.9 and abs(c.y - y0) < 0.5)

    bw, bh, out = L.BUTTONS["size"]
    x, z = L.BUTTONS["power"]
    power = box("power", x - bw / 2, x + bw / 2, -out, 0.5, z - bh / 2, z + bh / 2, m["case"])
    bevel(power, 0.5, segments=1)
    paint(power, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
    return join([upper, under, power], "ps2")


def eject(m):
    bw, bh, out = L.BUTTONS["size"]
    x, z = L.BUTTONS["eject"]
    button = box("eject", x - bw / 2, x + bw / 2, -out, 0.5, z - bh / 2, z + bh / 2, m["case"])
    bevel(button, 0.5, segments=1)
    paint(button, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
    return button


def tray(m):
    """The tray, in its bay: its door's front printed and grooved like the fins, the DVD's well in its top."""
    t, wl = L.TRAY, L.WELL
    (x0, x1), (z0, z1) = t["x"], t["z"]
    slab = box("tray", x0 + 0.5, x1 - 0.5, 0.3, t["depth"] - 2.0, z0 + 0.4, z1 - 0.4, m["case"])
    boolean(slab, grooves(m, x0, x1))
    boolean(slab, cylinder("well", wl["x"], wl["y"], wl["r"], z1 - 0.4 - wl["depth"], z1 + 2.0, m["dark"], 48))
    paint(slab, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < 0.8 and name == "case")
    return slab


def disc(m):
    """The DVD, its middle at its origin, its label up."""
    d = L.DISC
    size = 2 * d["r"]
    shell = ring_solid("dvd", d["r"], d["hole"], -d["thickness"] / 2, d["thickness"] / 2, m["disc"])
    label = atlas_uv(L.DISC_REGIONS["label"], size, size, L.DISC_ATLAS)
    data = atlas_uv(L.DISC_REGIONS["data"], size, size, L.DISC_ATLAS)
    paint(shell, m["disc"], lambda co: label(co.x + d["r"], d["r"] - co.y), lambda c, n, name: n.z > 0.9)
    paint(shell, m["disc"], lambda co: data(co.x + d["r"], d["r"] + co.y), lambda c, n, name: n.z <= 0.9)
    return shell


def light(m):
    lw, lh = L.LIGHTS["size"]
    x, z = L.LIGHTS["power"]
    lit = box("power_light", -lw / 2 - 0.2, lw / 2 + 0.2, -0.3, 0.0, -lh / 2 - 0.2, lh / 2 + 0.2, m["print"])
    paint(lit, m["print"], swatch("green"), lambda c, n, name: True)
    return lit, Vector((x, -0.05, z))


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 5, f0 + 9)))


def slide(f, f0, f1):
    """The tray's way out: out between f0 and f0 + 15, back in from f1 - 16 to f1."""
    return -L.TRAY["travel"] * ease_out(phase(f, f0, f0 + 15)) * (1 - smooth(phase(f, f1 - 16, f1)))


def timeline(f):
    poses = {"eject": Pose(y=1.2 * (tap(f, 12) + tap(f, 170)))}
    poses["tray"] = Pose(y=slide(f, 15, 78) if f < 160 else slide(f, 173, 214))
    poses["power_light"] = Pose() if 80 <= f < 172 else Pose(scale=HIDDEN)
    high = 90.0
    if f < 24 or f >= 200:
        poses["dvd"] = Pose(scale=HIDDEN)
    elif f < 32:
        poses["dvd"] = Pose(z=high, spin=25.0 * (f - 24), scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 24, 32)))
    elif f < 58:
        t = phase(f, 32, 58)
        poses["dvd"] = Pose(z=high * (1 - ease_in(t)), spin=200.0 + 1000.0 * ease_out(t))
    elif f < 184:
        poses["dvd"] = Pose(z=1.5 * math.exp(-(f - 58) / 3.0) * abs(math.sin(math.pi * (f - 58) / 5.0)))
    else:
        t = phase(f, 184, 200)
        poses["dvd"] = Pose(z=70.0 * ease_out(t), spin=720.0 * ease_in(t),
                            scale=max(HIDDEN, 1 - ease_in(phase(f, 192, 200))))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "ps2_print.png"))
    discs = bpy.data.images.load(os.path.join(images, "ps2_disc.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", disc="#FFFFFF")
    textures = dict(print=printed, disc=discs)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    console, door, button = body(m), tray(m), eject(m)
    lit, lit_at = light(m)
    dvd = disc(m)
    for obj in (console, door, button):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("ps2_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    for part in (door, button, lit):
        part.parent = console
    lit.location = lit_at
    dvd.parent = door
    wl = L.WELL
    dvd.location = (wl["x"], wl["y"], L.TRAY["z"][1] - 0.4 - wl["depth"] + L.DISC["thickness"] / 2 + 0.1)
    nodes = {"tray": door, "eject": button, "power_light": lit, "dvd": dvd}

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in console.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [console, door, button, lit, dvd]
    print(f"PlayStation 2: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(console.data)} the console), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
