"""The console theme's Atari XE Game System model (godot/themes/console/models/systems/atarixe.glb): the XE Game System,
its keyboard and its CX40 joystick.

Built in Blender (xegs_layout.py has the measurements, taken from photographs). The console is a base under a shell that
overhangs it, the shell's front a strip apart from the rest by a groove; the ribs are ridges along the long side of the
triangle at the back left, clipped to it; the funnel and the slot are cut along that side into the shell, the slot on
down into the base; the power button stands on its raised triangle, the four buttons in the strip. The keyboard is a
slab, its keys standing in the well cut into it, each tapering to its printed top, its cable running to its modular plug
in the console's left side. The CX40 is atari_2600.py's, in the XE Game System's beige, its cord running to its 9-pin
plug in the first port's notch in the console's right side (the plugs and strain reliefs are plugs.py's). The printing
is one texture (xegs_print.py's), projected from above onto the strip, the buttons and the keys, and from in front onto
the cartridge.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting over the slot, shrunk to nothing), the power button and its LED (sunk into it while the
console is off), START, and the joystick's shaft and button.

The `focused` clip (8 s, looping): the cartridge drops into the slot; POWER, its LED coming on; START; the joystick's
shaft waggles and its button fires; then POWER again, the LED going out, and the cartridge rises out and goes.

Three materials (case, keys, cart) and one 1024² texture, within the system model budget. Run from the repo root:

    python tools/console-models/xegs_print.py artifacts/xegs
    blender -b --factory-startup --python tools/console-models/xegs.py -- artifacts/xegs godot/themes/console/models/systems/atarixe.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari_2600  # noqa: E402
import atari_2600_layout as AL  # noqa: E402
import plugs  # noqa: E402
import xegs_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, keys=0.45, cart=0.45)


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


STRIP = atlas_uv(L.REGIONS["strip"], L.WIDTH, L.STRIP["y"][1] - L.STRIP["y"][0])
KEYS = atlas_uv(L.REGIONS["keys"], L.KEYBOARD["size"][0], L.KEYBOARD["size"][1])


def strip_uv(co):
    return STRIP(co.x + L.WIDTH / 2, L.STRIP["y"][1] - co.y)


def keys_uv(co):
    w, d, _ = L.KEYBOARD["size"]
    return KEYS(co.x + w / 2, d - (co.y - L.KEYBOARD["y0"]))


def disc(name, x, y, r, z0, z1, mat, segments=32):
    ring = [(x + r * math.cos(2 * math.pi * k / segments), y + r * math.sin(2 * math.pi * k / segments))
            for k in range(segments)]
    return solid(name, [[(px, py, z) for px, py in ring] for z in (z0, z1)], mat)


def button(name, region, x, y, r, z0, z1, mat, tone):
    """A round button: its sides its colour, its top printed (region, from above, its middle at (x, y))."""
    part = disc(name, x, y, r, z0, z1, mat)
    bevel(part, 0.8, segments=2)
    colour(part, mat, tone)
    if region == "strip":
        paint(part, mat, strip_uv, lambda c, n, kind: n.z > 0.9)
    else:
        top = atlas_uv(L.REGIONS[region], 2 * r, 2 * r)
        paint(part, mat, lambda co: top(co.x - x + r, y + r - co.y), lambda c, n, kind: n.z > 0.9)
    return part


# ---- The console -----------------------------------------------------------------------------------------------------

def ribs(m):
    """The ridges along the triangle's long side, each a trapezoid in section, clipped to the triangle; joined."""
    half, height, top = L.WIDTH / 2, L.RIBS["height"], L.HEIGHT
    a, b = Vector((L.RIBS["back"], L.DEPTH)), Vector((-half, L.RIBS["left"]))     # the long side's ends
    along = (a - b).normalized()
    inward = Vector((-along.y, along.x))                     # towards the corner at the back left
    length = (a - b).length
    foot, tip = L.RIBS["foot"], L.RIBS["top"]
    ridges = []
    for k in range(L.RIBS["count"]):
        d = L.RIBS["rim"] + foot / 2 + k * L.RIBS["pitch"]
        section = [(d - foot / 2, top - 0.5), (d + foot / 2, top - 0.5), (d + tip / 2, top + height),
                   (d - tip / 2, top + height)]
        ends = []
        for t in (-20.0, length + 20.0):
            p = b + along * t
            ends.append([(p.x + inward.x * s, p.y + inward.y * s, z) for s, z in section])
        ridges.append(solid("ridge", ends, m["case"]))
    part = join(ridges, "ribs")
    corner = [(-half + 2.0, L.DEPTH - 2.0), (b.x + 2.0, b.y + 2.0 * (a.y - b.y) / (a.x - b.x)),
              (a.x - 2.0 * (a.x - b.x) / (a.y - b.y), L.DEPTH - 2.0)]
    boolean(part, prism_z("triangle", corner, top - 1.0, top + height + 1.0, m["case"]), "INTERSECT")
    return colour(part, m["case"], "case")


def diagonal(name, t0, t1, section, m):
    """A solid along the ribs' long side from t0 to t1, its section (s, z) the same all along."""
    return solid(name, [[(*L.along(t, s), z) for s, z in section] for t in (t0, t1)], m["case"])


def funnel(m):
    """The cutter for the funnel: its floor, its back wall along the ribs, the ramp in front up to the top and on."""
    (t0, t1), (r0, r1), depth = L.FUNNEL["t"], L.FUNNEL["ramp"], L.FUNNEL["depth"]
    floor, rise = L.HEIGHT - depth, 10.0
    return diagonal("funnel", t0, t1, [(-0.5, floor), (r0, floor), (r1, L.HEIGHT),
                                       (r1 + rise * (r1 - r0) / depth, L.HEIGHT + rise), (-0.5, L.HEIGHT + rise)], m)


def slot(m):
    (t0, t1), (s0, s1) = L.SLOT["t"], L.SLOT["s"]
    floor, top = L.SLOT["floor"], L.HEIGHT - L.FUNNEL["depth"] + 1.0
    return diagonal("slot", t0, t1, [(s0, floor), (s1, floor), (s1, top), (s0, top)], m)


def in_slot(c):
    t, s = L.frame(c.x, c.y)
    (t0, t1), (s0, s1) = L.SLOT["t"], L.SLOT["s"]
    return t0 - 0.5 < t < t1 + 0.5 and s0 - 0.5 < s < s1 + 0.5


def console(m):
    """The base, the shell (the strip, the groove, the rest), the ribs, the funnel and the slot, the plinth and the
    buttons; printed. Returns it and the moving parts."""
    half, inset, z0 = L.WIDTH / 2, L.BASE["inset"], L.BASE["height"]
    base = box("base", -half + inset, half - inset, inset, L.DEPTH - inset, 0.0, z0 + 1.0, m["case"])
    bevel(base, 1.5, segments=2)
    w, d = L.PORTS["width"], L.PORTS["depth"]
    (pz0, pz1), side = L.PORTS["z"], half - inset
    for y in L.PORTS["y"]:
        boolean(base, box("notch", side - d, side + 1.0, y - w / 2, y + w / 2, pz0, pz1, m["case"]))
    boolean(base, slot(m))
    colour(base, m["case"], "case")
    paint(base, m["case"], swatch("dark"),
          lambda c, n, kind: n.x > 0.9 and abs(c.x - (side - d)) < 0.5 or in_slot(c))

    (sy0, sy1), groove = L.STRIP["y"], L.STRIP["groove"]
    strip = box("strip", -half, half, sy0, sy1, z0, L.HEIGHT, m["case"])
    bevel(strip, 3.0, segments=3)
    colour(strip, m["case"], "case")
    paint(strip, m["case"], strip_uv, lambda c, n, kind: n.z > 0.9)
    shell = box("shell", -half, half, sy1 + groove, L.DEPTH, z0, L.HEIGHT, m["case"])
    bevel(shell, 3.0, segments=3)
    filler = box("groove", -half + 1.0, half - 1.0, sy1 - 2.0, sy1 + groove + 2.0, z0, L.HEIGHT - L.STRIP["depth"],
                 m["case"])
    ridges = ribs(m)
    boolean(shell, funnel(m))
    boolean(shell, slot(m))
    colour(shell, m["case"], "case")
    paint(shell, m["case"], swatch("dark"),
          lambda c, n, kind: c.z < L.HEIGHT - L.FUNNEL["depth"] - 0.5 and in_slot(c))
    plinth = prism_z("plinth", L.PLINTH["points"], L.HEIGHT - 1.0, L.HEIGHT + L.PLINTH["height"], m["case"])
    bevel(plinth, 0.8, segments=2)
    colour(plinth, m["case"], "case")

    r, h = L.BUTTONS["r"], L.BUTTONS["height"]
    fixed, moving = [], {}
    for x, name in zip(L.BUTTONS["x"], L.BUTTONS["names"]):
        part = button(name.lower(), "strip", x, L.BUTTONS["y"], r, L.HEIGHT - 2.0, L.HEIGHT + h, m["keys"],
                      name.lower())
        if name == "Start":
            middle = Vector((x, L.BUTTONS["y"], L.HEIGHT))
            part.data.transform(Matrix.Translation(-middle))
            moving["start"] = (part, middle)
        else:
            fixed.append(part)
    (px, py), pr = L.POWER["at"], L.POWER["r"]
    low = L.HEIGHT + L.PLINTH["height"]
    power = button("power", "power", px, py, pr, low - 1.0, low + L.POWER["height"], m["keys"], "power")
    middle = Vector((px, py, low))
    power.data.transform(Matrix.Translation(-middle))
    moving["power"] = (power, middle)
    (dx, dy), top = L.POWER["led"], low + L.POWER["height"]
    led = colour(disc("led", 0.0, 0.0, 1.3, -1.0, 0.0, m["keys"], 16), m["keys"], "led")
    moving["led"] = (led, Vector((px + dx, py + dy, top - 0.2)))
    return join([base, strip, shell, filler, ridges, plinth] + fixed, "atarixe"), moving


# ---- The keyboard, the cartridge, the cords --------------------------------------------------------------------------

def keyboard(m):
    """The slab with its well, the keys standing in it, the HELP button; printed."""
    w, d, h = L.KEYBOARD["size"]
    y0 = L.KEYBOARD["y0"]
    (wx0, wx1), (wv0, wv1), deep = L.WELL["x"], L.WELL["v"], L.WELL["depth"]
    slab = box("keyboard", -w / 2, w / 2, y0, y0 + d, 0.0, h, m["case"])
    bevel(slab, 3.0, segments=3)
    boolean(slab, box("well", wx0, wx1, y0 + wv0, y0 + wv1, h - deep, h + 10.0, m["case"]))
    colour(slab, m["case"], "case")
    paint(slab, m["case"], swatch("well"),
          lambda c, n, kind: wx0 - 0.5 < c.x < wx1 + 0.5 and y0 + wv0 - 0.5 < c.y < y0 + wv1 + 0.5 and c.z < h - 0.5)
    parts = [slab]
    inset, floor = L.KEY["inset"], h - deep
    for legend, x0, x1, v in L.keys():
        y = y0 + v
        foot = [(x0 + 0.5, y - 9.0), (x1 - 0.5, y - 9.0), (x1 - 0.5, y + 9.0), (x0 + 0.5, y + 9.0)]
        cap = [(x0 + inset, y - 9.5 + inset), (x1 - inset, y - 9.5 + inset), (x1 - inset, y + 9.5 - inset),
               (x0 + inset, y + 9.5 - inset)]
        part = solid("key", [[(x, yy, floor - 1.0) for x, yy in foot],
                             [(x, yy, floor + L.KEY["height"]) for x, yy in cap]], m["keys"])
        colour(part, m["keys"], "key")
        paint(part, m["keys"], keys_uv, lambda c, n, kind: n.z > 0.9)
        parts.append(part)
    (hx, hv), hr = L.HELP["at"], L.HELP["r"]
    parts.append(button("help", "help", hx, y0 + hv, hr, h - 1.0, h + L.HELP["height"], m["keys"], "help"))
    return join(parts, "keyboard")


def cartridge(m):
    """The cartridge, its foot's middle at its origin, its label facing the front right, its width along the ribs."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["cart"])
    bevel(part, 1.6, segments=2)
    colour(part, m["cart"], "cart")
    face = atlas_uv(L.REGIONS["cart"], w, h)
    paint(part, m["cart"], lambda co: face(co.x + w / 2, h - co.z), lambda c, n, kind: n.y < -0.9)
    part.data.transform(Matrix.Rotation(math.radians(L.ANGLE), 4, "Z"))
    return part


def cord(name, m, tone, points, radius=2.4):
    """A cable: a tube along the Bézier curve through four control points."""
    p0, p1, p2, p3 = (Vector(p) for p in points)
    path = [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / 24 for k in range(25)]]
    bm = bmesh.new()
    rings, normal = [], Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(path):
        tangent = (path[min(k + 1, 24)] - path[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * radius)
                      for a in [2 * math.pi * j / 8 for j in range(8)]])
    for a, b in zip(rings, rings[1:]):
        for j in range(8):
            bm.faces.new([a[j], a[(j + 1) % 8], b[(j + 1) % 8], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return colour(new_object(name, bm, m["case"]), m["case"], tone)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    above = L.CART["above"]
    if f < 10 or f >= 200:
        cart = Pose(z=above, scale=HIDDEN)
    elif f < 18:
        cart = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 10, 17))))
    elif f < 30:
        cart = Pose(z=above * (1 - ease_in(phase(f, 18, 30))))
    elif f < 186:
        cart = Pose(z=-1.5 * math.sin(math.pi * phase(f, 30, 36)))
    else:
        cart = Pose(z=above * ease_out(phase(f, 186, 196)), scale=max(HIDDEN, 1 - ease_in(phase(f, 194, 200))))
    pressed = -2.0 * max(tap(f, 40), tap(f, 176))
    lit = 1.0 if 44 <= f < 180 else 0.0
    t = phase(f, 62, 168)
    k = math.sin(math.pi * t)
    return {"cartridge": cart, "power": Pose(z=pressed), "led": Pose(z=pressed + lit),
            "start": Pose(z=-2.0 * tap(f, 52)),
            "shaft": Pose(pitch=18.0 * k * math.sin(2 * math.pi * 3.0 * t),
                          roll=18.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "fire": Pose(z=-2.0 * max(tap(f, f0) for f0 in (76, 96, 114, 132, 150)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "xegs_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    body, moving = console(m)
    base, (shaft, shaft_at), (button_, button_at) = atari_2600.joystick({"case": m["case"], "print": m["case"]})
    paint(base, m["case"], swatch("joy"), lambda c, n, kind: n.z <= 0.9)
    colour(shaft, m["case"], "black")
    sx, sy = AL.STICK["at"]
    jx, jy = L.JOYSTICK["at"]
    move = Matrix.Translation((jx - sx, jy - sy, 0.0))
    base.data.transform(move)
    shaft_at, button_at = move @ shaft_at, move @ button_at
    w, d, h = AL.STICK["base"]
    joy, grey = (lambda o: colour(o, m["case"], "joy")), (lambda o: colour(o, m["case"], "case"))
    relief, start, leaving = plugs.place(*plugs.grommet(joy, 4.0), m["case"], (jx, jy + d / 2 - 1.0, h * 0.4),
                                         (0.0, 1.0, 0.0))
    side = L.WIDTH / 2 - L.BASE["inset"] - L.PORTS["depth"]
    port = Vector((side, L.PORTS["y"][0], sum(L.PORTS["z"]) / 2))
    plug, end, back = plugs.place(*plugs.dsub(joy, joy, 14.0), m["case"], port, (1.0, 0.0, 0.0))
    stick_cord = cord("joystick_cord", m, "joy", [start, start + leaving * 30.0 + Vector((0.0, 0.0, -10.0)),
                                                  end + back * 30.0, end])
    kw, kd, kh = L.KEYBOARD["size"]
    rear = L.KEYBOARD["y0"] + kd
    left = -L.WIDTH / 2 + L.BASE["inset"]
    k_relief, k_start, k_leaving = plugs.place(*plugs.grommet(grey, 4.0), m["case"],
                                               (-kw / 2 + 16.0, rear - 1.0, kh / 2), (0.0, 1.0, 0.0))
    jack, k_end, k_back = plugs.place(*plugs.modular(grey, grey), m["case"], (left, 60.0, L.BASE["height"] / 2),
                                      (-1.0, 0.0, 0.0))
    keyboard_cord = cord("keyboard_cord", m, "case", [k_start, k_start + k_leaving * 20.0, k_end + k_back * 30.0,
                                                      k_end], radius=2.4)
    whole = join([body, keyboard(m), base, stick_cord, keyboard_cord] + relief + plug + k_relief + jack, "atarixe")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("atarixe_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    parts = {"cartridge": (cartridge(m), Vector(L.SEAT)), "shaft": (shaft, shaft_at), "fire": (button_, button_at)}
    parts.update(moving)
    nodes = {}
    for name, (part, where) in parts.items():
        for p in part.data.polygons:
            p.use_smooth = True
        part.data.set_sharp_from_angle(angle=math.radians(35))
        part.parent = whole
        part.location = where
        nodes[name] = part

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"XE Game System: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
