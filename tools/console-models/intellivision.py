"""The console theme's Intellivision system model (godot/themes/console/models/systems/intellivision.glb): Mattel's
Intellivision, its two controllers docked in its top.

Built in Blender (intellivision_layout.py has the measurements, taken from photographs). The body is its side profile
(the front leaning out to the top's edge) across its width, its edges rounded, the docks' band sunk into its top and the
cartridge slot cut into its right end; the controllers are rounded slabs lying in the band, their discs separate. The
printing is one texture (intellivision_print.py's), projected from above onto the tops and from in front onto the
front.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the console; the
console holding the cartridge (waiting off its right end, shrunk to nothing), the OFF-ON switch, the left controller
and the right one (holding its disc).

The `focused` clip (8 s, looping): the cartridge appears off the right end and slides into the slot; the switch goes to
ON; the right controller rises out of its dock and tips towards the viewer, its disc rocking as the game's played,
then settles back; the switch goes off and the cartridge slides out and goes.

Two materials (body, gloss) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/intellivision_print.py artifacts/intellivision
    blender -b --factory-startup --python tools/console-models/intellivision.py -- artifacts/intellivision godot/themes/console/models/systems/intellivision.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intellivision_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(body=0.45, gloss=0.3)
Z0 = L.FEET          # the body's underside, on its feet


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def upright(name, points, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.TOP)
PAD = atlas_uv(L.REGIONS["pad"], L.PAD["length"], L.PAD["width"])


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The body: its profile across its width, its edges rounded, the band and the slot cut in, the feet; printed."""
    half = L.WIDTH / 2
    body = prism_x("intellivision", [(y, Z0 + z) for y, z in L.PROFILE], -half, half, m["body"])
    bevel(body, 3.0, segments=2, angle=40)
    (b0, b1), depth = L.BAND["y"], L.BAND["depth"]
    boolean(body, box("band", -half + 10.0, half - 10.0, b0, b1, Z0 + L.TOP - depth, Z0 + L.TOP + 5.0, m["body"]))
    (s0, s1), (sz0, sz1) = L.SLOT["y"], L.SLOT["z"]
    boolean(body, box("slot", half - 130.0, half + 5.0, s0, s1, Z0 + sz0, Z0 + sz1, m["body"]))
    colour(body, m["body"], "body")
    paint(body, m["body"], lambda co: TOP(co.x + half, L.DEPTH - co.y),
          lambda c, n, kind: n.z > 0.9 and c.z > Z0 + L.TOP - depth - 0.5)
    paint(body, m["body"], lambda co: FRONT(co.x + half, Z0 + L.TOP - co.z),
          lambda c, n, kind: n.y < -0.5 and c.y < 12.0)
    paint(body, m["body"], swatch("slot"),
          lambda c, n, kind: c.x > half - 130.0 and s0 - 0.5 < c.y < s1 + 0.5 and Z0 + sz0 - 0.5 < c.z < Z0 + sz1 + 0.5)
    feet = [colour(upright("foot", circle(x, y, 9.0, 12), 0.0, Z0 + 1.0, m["body"]), m["body"], "dark")
            for x in (-160.0, 160.0) for y in (30.0, 200.0)]
    return join([body] + feet, "intellivision")


def switch(m):
    (sx, sy), (sw, sh) = L.SWITCH["at"], L.SWITCH["size"]
    part = box("power", -sw / 2 + 4.0, sw / 2 - 12.0, -sh / 2 + 1.0, sh / 2 - 1.0, -1.0, 3.0, m["gloss"])
    bevel(part, 0.8, segments=1)
    colour(part, m["gloss"], "gold")
    return part, Vector((sx - L.SWITCH["travel"] / 2, sy, Z0 + L.TOP))


# ---- A controller ----------------------------------------------------------------------------------------------------

def controller(m, name):
    """A controller in its own frame (x across it, y along it from its disc's end (-76) to its cord's (+76), z up from
    its underside): its body, the keypad's plate, the side buttons; its disc apart, with where its node goes."""
    p = L.PAD
    length, width, t = p["length"], p["width"], p["thickness"]
    body = upright(name, rounded(0.0, 0.0, width, length, 8.0, 4), 0.0, t, m["body"])
    bevel(body, 2.4, segments=2, angle=40)

    def uv(co):                                               # the region's u from the cord's end, v across
        return PAD(length / 2 - co.y, co.x + width / 2)
    colour(body, m["body"], "body")
    paint(body, m["body"], uv, lambda c, n, kind: n.z > 0.9)
    (u0, u1), (v0, v1) = L.KEYPAD["u"], L.KEYPAD["v"]
    plate = upright("keypad", rounded((v0 + v1) / 2, length / 2 - (u0 + u1) / 2, v1 - v0 + 4.0, u1 - u0 + 4.0, 4.0, 3),
                    t - 1.0, t + 1.2, m["gloss"])
    paint(plate, m["gloss"], uv, lambda c, n, kind: True)
    parts = [body, plate]
    (s0, s1), (sw, sh) = L.SIDE["u"], L.SIDE["size"]
    for side in (-1, 1):
        x0, x1 = sorted((side * (width / 2 - 0.5), side * (width / 2 - 0.5 + sh)))
        for su in (s0, s1):
            bump = box("side", x0, x1, length / 2 - su - sw / 2, length / 2 - su + sw / 2, t * 0.3, t * 0.75, m["body"])
            parts.append(colour(bump, m["body"], "dark"))
    whole = join(parts, name)
    du, r = L.DISC["u"], L.DISC["r"]
    disc = upright(name + "_disc", circle(0.0, 0.0, r, 32), -1.0, L.DISC["height"], m["gloss"])
    bevel(disc, 0.8, segments=2)
    colour(disc, m["gloss"], "metal")
    paint(disc, m["gloss"], lambda co: uv(Vector((co.x, co.y + length / 2 - du, co.z))), lambda c, n, kind: n.z > 0.9)
    return whole, disc, Vector((0.0, length / 2 - du, t))


def cartridge(m):
    """The cartridge, lying flat, its label up, its middle at its origin, pointing into the slot (-x)."""
    w, length, t = L.CART["size"]
    part = upright("cartridge", rounded(0.0, 0.0, length, w, 4.0, 3), -t / 2, t / 2, m["body"])
    bevel(part, 1.0, segments=2)
    colour(part, m["body"], "cart")
    lw, lh = L.CART["label"]
    label = atlas_uv(L.REGIONS["cart"], lw, lh)
    middle = 16.0                                             # the label's middle along it: towards the outer end
    paint(part, m["body"], lambda co: label(lw / 2 - co.y, middle + lh / 2 - co.x),
          lambda c, n, kind: n.z > 0.9 and abs(c.x - middle) < lh / 2 and abs(c.y) < lw / 2)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    out = L.CART["out"]
    if f < 6 or f >= 222:
        cart = Pose(x=out, scale=HIDDEN)
    elif f < 14:
        cart = Pose(x=out, scale=max(HIDDEN, back_out(phase(f, 6, 13))))
    elif f < 34:
        cart = Pose(x=out * (1 - smooth(phase(f, 14, 34))))
    elif f < 200:
        cart = Pose(x=-1.5 * math.sin(math.pi * phase(f, 34, 40)))
    elif f < 214:
        cart = Pose(x=out * smooth(phase(f, 200, 214)))
    else:
        cart = Pose(x=out, scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 222))))
    on = smooth(phase(f, 38, 43)) * (1 - smooth(phase(f, 192, 197)))
    lift = smooth(phase(f, 48, 66)) * (1 - smooth(phase(f, 170, 188)))
    t = phase(f, 70, 166)
    k = math.sin(math.pi * t)
    tilt = L.DISC["tilt"]
    return {"cartridge": cart, "power": Pose(x=L.SWITCH["travel"] * on),
            "right_pad": Pose(z=46.0 * lift + 3.0 * math.sin(math.pi * phase(f, 66, 74)), pitch=40.0 * lift,
                              roll=4.0 * k * math.sin(2 * math.pi * 2.0 * t)),
            "right_pad_disc": Pose(pitch=tilt * k * math.sin(2 * math.pi * 3.0 * t),
                                   roll=tilt * k * math.cos(2 * math.pi * 2.0 * t))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "intellivision_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    body = console(m)
    floor = Z0 + L.TOP - L.BAND["depth"]
    dx, dy = L.PAD["dock"]
    left, left_disc, left_disc_at = controller(m, "left_pad")
    left.data.transform(Matrix.Translation((dx, dy, floor)) @ Matrix.Rotation(math.radians(-90.0), 4, "Z"))
    left_disc.data.transform(Matrix.Translation(Vector((dx, dy, floor))
                                                + Matrix.Rotation(math.radians(-90.0), 3, "Z") @ left_disc_at))
    whole = join([body, left, left_disc], "intellivision")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("intellivision_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    right, right_disc, right_disc_at = controller(m, "right_pad")
    right.data.transform(Matrix.Rotation(math.radians(90.0), 4, "Z"))
    right_disc.data.transform(Matrix.Rotation(math.radians(90.0), 4, "Z"))
    lever, lever_at = switch(m)
    cart = cartridge(m)
    w, length, t = L.CART["size"]
    stick_out = 40.0
    cart_at = Vector((L.WIDTH / 2 + stick_out - length / 2, sum(L.SLOT["y"]) / 2, Z0 + sum(L.SLOT["z"]) / 2))
    nodes = {}
    for name, part, where, parent in (("right_pad", right, Vector((-dx, dy, floor)), whole),
                                      ("power", lever, lever_at, whole), ("cartridge", cart, cart_at, whole)):
        part.parent = parent
        part.location = where
        nodes[name] = part
    right_disc.parent = right
    right_disc.location = Matrix.Rotation(math.radians(90.0), 3, "Z") @ right_disc_at
    nodes["right_pad_disc"] = right_disc
    for part in nodes.values():
        for p in part.data.polygons:
            p.use_smooth = True
        part.data.set_sharp_from_angle(angle=math.radians(35))

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"Intellivision: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
