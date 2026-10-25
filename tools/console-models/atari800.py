"""The console theme's Atari 800 system model (godot/themes/console/models/systems/atari800.glb): the Atari 800 and its
CX40 joystick.

Built in Blender (atari800_layout.py has the measurements, taken from photographs). The shell is its side outline
extruded across its width, its top's ends chamfered down to the sides; the lid is the shell's piece over the bay,
hollowed, a hair smaller than the hole it leaves; the bay is cut under it, the slots into the bay's floor, and the
vents' recess into the top behind it, its fins standing in it. The shell stands on the ports' block and two feet. The
keys stand on the deck in its frame, each tapering to its printed top, the function keys in their column at the right,
the power light under them. The CX40 is atari_2600.py's, its cord running from its strain relief to its 9-pin plug in
port 1 (plugs.py's). The printing is one texture (atari800_print.py's), projected from above onto the deck and the keys,
and from in front onto the lid's face, the ports and the bay's back wall.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (on its hinge along its back edge), the cartridge (waiting over the left slot, shrunk to nothing),
OPTION and START, and the joystick's shaft and button.

The `focused` clip (8 s, looping): the lid swings up, the cartridge drops into the left slot and the lid shuts; OPTION
and START; the joystick's shaft waggles and its button fires; then the lid swings up again, the cartridge rises out and
goes, and the lid shuts.

Four materials (case, keys, joystick, cart) and one 1024² texture, within the system model budget. Run from the repo
root:

    python tools/console-models/atari800_print.py artifacts/atari800
    blender -b --factory-startup --python tools/console-models/atari800.py -- artifacts/atari800 godot/themes/console/models/systems/atari800.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari800_layout as L  # noqa: E402
import plugs  # noqa: E402
import atari_2600  # noqa: E402
import atari_2600_layout as AL  # noqa: E402
from amiga import paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive import prism_y  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 24.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, keys=0.4, cart=0.45)
MOVING = ("option", "start")


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


DECK = atlas_uv(L.REGIONS["deck"], L.WIDTH, L.DECK_BACK[0])
BADGE = atlas_uv(L.REGIONS["badge"], L.LID["x"][1] - L.LID["x"][0], L.HEIGHT - L.DECK_BACK[1])
PORTS = atlas_uv(L.REGIONS["ports"], L.PORTS["block"][1] - L.PORTS["block"][0], L.BASE)
PLATE = atlas_uv(L.REGIONS["plate"], L.BAY["x"][1] - L.BAY["x"][0], L.DECK_BACK[1] - L.BAY["floor"])


def deck_uv(co):
    return DECK(co.x + L.WIDTH / 2, L.DECK_BACK[0] - co.y)


def on_deck(name, outline, h0, h1, mat, outline1=None):
    """A solid from an (x, s) outline in the deck's frame, from h0 off it to h1 (its top outline1, if given)."""
    top = outline1 or outline
    return solid(name, [[(x, *L.deck_point(s, h0)) for x, s in outline], [(x, *L.deck_point(s, h1)) for x, s in top]],
                 mat)


def duplicate(obj, name):
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name = copy.data.name = name
    bpy.context.scene.collection.objects.link(copy)
    return copy


# ---- The computer ----------------------------------------------------------------------------------------------------

def shell(m):
    """The side outline across the width, the top's ends chamfered down to the sides."""
    half = L.WIDTH / 2
    body = prism_x("atari800", L.PROFILE, -half, half, m["case"])
    cx, cz = L.CHEEK["x"], L.CHEEK["z"]
    fall = (L.HEIGHT - cz) / (half - cx)            # the chamfer's drop per millimetre across
    side, inner = cz - 10.0 * fall, L.HEIGHT + 20.0 * fall
    ends = [(-half - 10.0, -5.0), (half + 10.0, -5.0), (half + 10.0, side), (cx - 20.0, inner), (-cx + 20.0, inner),
            (-half - 10.0, side)]
    boolean(body, prism_y("ends", ends, -10.0, L.DEPTH + 10.0, m["case"]), "INTERSECT")
    bevel(body, 2.5, segments=2, angle=40)
    return body


def fins(m, outline):
    """The vents' fins across their width, each the outline (y, z) extruded across its thickness, joined."""
    (x0, x1), count, fin = L.VENTS["x"], L.VENTS["count"], L.VENTS["fin"]
    pitch = (x1 - x0) / count
    parts = [prism_x("fin", outline, x0 + k * pitch + (pitch - fin) / 2, x0 + k * pitch + (pitch + fin) / 2, m["case"])
             for k in range(count)]
    return colour(join(parts, "fins"), m["case"], "case")


def recessed(name, obj, m, x, outline):
    """Cuts the vents' recess (the outline's floor, up through the top) into obj and paints its floor darker; returns
    the fins to stand in it."""
    (x0, x1), depth = x, L.VENTS["depth"]
    ya, yb = min(y for y, z in outline), max(y for y, z in outline)
    floor = outline[:len(outline) // 2]
    boolean(obj, prism_x(name, floor + [(floor[-1][0], L.HEIGHT + 20.0), (floor[0][0], L.HEIGHT + 20.0)], x0, x1,
                         m["case"]))
    paint(obj, m["case"], swatch("vent"),
          lambda c, n, kind: n.z > 0.3 and x0 - 0.5 < c.x < x1 + 0.5 and ya - 0.5 < c.y < yb + 0.5
          and L.top_z(c.y) - depth - 0.5 < c.z < L.top_z(c.y) - 1.0)
    return fins(m, outline)


def lid(body, m):
    """The lid: the shell's piece over the bay, hollowed (its face and sides LID["wall"] thick, its top LID["top"]), the
    vents' recess cut into its top and their fins in it, its origin on its hinge along its back edge; its face
    printed."""
    (x0, x1), (y0, y1), t, gap = L.LID["x"], L.LID["y"], L.LID["wall"], L.LID["gap"]
    part = duplicate(body, "lid")
    boolean(part, box("lid_box", x0 + gap, x1 - gap, y0, y1 - gap, L.DECK_BACK[1] + gap, L.HEIGHT + 20.0, m["case"]),
            "INTERSECT")
    low, high = L.DECK_BACK[1] - 10.0, L.HEIGHT - L.LID["top"]
    hollow = [(L.face_y(low, t), low), (y1 + 5.0, low), (y1 + 5.0, high), (L.face_y(high, t), high)]
    boolean(part, prism_x("hollow", hollow, x0 + gap + t, x1 - gap - t, m["case"]))
    colour(part, m["case"], "case")
    paint(part, m["case"], lambda co: BADGE(co.x - x0, L.HEIGHT - co.z), lambda c, n, kind: n.y < -0.8 and n.z > 0.2)
    (vy0, vy1), depth = L.VENTS["lid"], L.VENTS["depth"]
    outline = [(vy0, L.HEIGHT - depth), (vy1, L.HEIGHT - depth), (vy1, L.HEIGHT), (vy0, L.HEIGHT)]
    part = join([part, recessed("lid_recess", part, m, L.VENTS["x"], outline)], "lid")
    hinge = Vector((0.0, y1 - gap, L.HEIGHT))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def vents(body, m):
    """The vents behind the lid: their recess cut into the top and its fall, and the fins standing in it, their tops
    flush with the top."""
    (y0, y1), depth = L.VENTS["y"], L.VENTS["depth"]
    fy = L.PROFILE[7][0]                                     # where the fall starts
    outline = [(y0, L.top_z(y0) - depth), (fy, L.top_z(fy) - depth), (y1, L.top_z(y1) - depth),
               (y1, L.top_z(y1)), (fy, L.top_z(fy)), (y0, L.top_z(y0))]
    return recessed("recess", body, m, L.VENTS["x"], outline)


def computer(m):
    """The shell with the lid's hole, the bay, the slots and the vents' recess cut in; the ports' block and the feet
    under it; printed. Returns it and the lid."""
    body = shell(m)
    flap = lid(body, m)
    (x0, x1), (y0, y1) = L.LID["x"], L.LID["y"]
    boolean(body, box("lid_hole", x0, x1, y0, y1, L.DECK_BACK[1], L.HEIGHT + 20.0, m["case"]))
    (bx0, bx1), (by0, by1), floor = L.BAY["x"], L.BAY["y"], L.BAY["floor"]
    boolean(body, box("bay", bx0, bx1, by0, by1, floor, L.HEIGHT, m["case"]))
    (sy0, sy1) = L.SLOTS["y"]
    for name in ("left", "right"):
        sx0, sx1 = L.SLOTS[name]
        boolean(body, box("slot", sx0, sx1, sy0, sy1, L.SLOTS["floor"], floor + 1.0, m["case"]))

    colour(body, m["case"], "case")
    paint(body, m["case"], deck_uv, lambda c, n, kind: n.z > 0.3 and c.y < L.DECK_BACK[0] - 0.3)
    paint(body, m["case"], swatch("metal"),
          lambda c, n, kind: bx0 - 0.5 < c.x < bx1 + 0.5 and by0 - 0.5 < c.y < by1 + 0.5
          and floor - 0.5 < c.z < L.DECK_BACK[1])
    paint(body, m["case"], lambda co: PLATE(co.x - bx0, L.DECK_BACK[1] - co.z),
          lambda c, n, kind: n.y < -0.9 and abs(c.y - by1) < 0.6 and floor < c.z < L.DECK_BACK[1] and bx0 < c.x < bx1)
    paint(body, m["case"], swatch("dark"),
          lambda c, n, kind: c.z < floor - 0.5 and sy0 - 0.5 < c.y < sy1 + 0.5
          and any(a - 0.5 < c.x < b + 0.5 for a, b in (L.SLOTS["left"], L.SLOTS["right"])))
    grille = vents(body, m)

    (px0, px1), (py0, py1) = L.PORTS["block"], L.PORTS["y"]
    lean = (py1 - py0) / L.BASE
    block = prism_x("ports", [(py1, 0.0), (150.0, 0.0), (150.0, L.BASE + 4.0), (py0 - 4.0 * lean, L.BASE + 4.0)],
                    px0, px1, m["case"])
    colour(block, m["case"], "case")
    paint(block, m["case"], lambda co: PORTS(co.x - px0, L.BASE - co.z), lambda c, n, kind: n.y < -0.8)
    fx, (fy0, fy1), fs = L.FEET["x"], L.FEET["y"], L.FEET["size"]
    feet = [colour(box("foot", side * fx - fs / 2, side * fx + fs / 2, fy0, fy1, 0.0, L.BASE + 2.0, m["case"]),
                   m["case"], "dark") for side in (-1, 1)]
    return join([body, grille, block] + feet, "atari800"), flap


def keys(m):
    """The keys: the main block, the function keys and the power light, each tapering to its printed top; OPTION and
    START apart (each its foot's middle at its origin, with where it goes), the rest joined."""
    fixed, moving = [], {}
    inset = L.KEY["inset"]

    def make(name, x0, x1, s, half, tone, top=L.KEY["height"]):
        foot = [(x0 + 0.6, s - half), (x1 - 0.6, s - half), (x1 - 0.6, s + half), (x0 + 0.6, s + half)]
        cap = [(x0 + inset, s - half - 0.5 + inset), (x1 - inset, s - half - 0.5 + inset),
               (x1 - inset, s + half + 0.5 - inset), (x0 + inset, s + half + 0.5 - inset)]
        part = on_deck(name, foot, -1.0, top, m["keys"], cap)
        colour(part, m["keys"], tone)
        paint(part, m["keys"], deck_uv, lambda c, n, kind: n.z > 0.85)
        return part

    for legend, x0, x1, s in L.keys():
        fixed.append(make("key", x0, x1, s, 9.0, "key"))
    fx0, fx1 = L.FUNCTION["x"]
    for legend, s, name in L.FUNCTION["keys"]:
        part = make(name, fx0, fx1, s, 8.5, name)
        if name in MOVING:
            y, z = L.deck_point(s, -1.0)
            middle = Vector(((fx0 + fx1) / 2, y, z))
            part.data.transform(Matrix.Translation(-middle))
            moving[name] = (part, middle)
        else:
            fixed.append(part)
    fixed.append(make("light", fx0, fx1, L.LIGHT["s"], L.LIGHT["half"], "light", L.LIGHT["height"]))
    return join(fixed, "keys"), moving


def cartridge(m):
    """The cartridge, its foot's middle at its origin, its label facing -y."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["cart"])
    bevel(part, 1.6, segments=2)
    colour(part, m["cart"], "cart")
    face = atlas_uv(L.REGIONS["cart"], w, h)
    paint(part, m["cart"], lambda co: face(co.x + w / 2, h - co.z), lambda c, n, kind: n.y < -0.9)
    return part


def cord(m, points):
    """The joystick's cord: a tube along the Bézier curve through four control points."""
    p0, p1, p2, p3 = (Vector(p) for p in points)
    path = [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / 24 for k in range(25)]]
    bm = bmesh.new()
    rings, normal = [], Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(path):
        tangent = (path[min(k + 1, 24)] - path[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * 2.4)
                      for a in [2 * math.pi * j / 8 for j in range(8)]])
    for a, b in zip(rings, rings[1:]):
        for j in range(8):
            bm.faces.new([a[j], a[(j + 1) % 8], b[(j + 1) % 8], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return colour(new_object("cord", bm, m["keys"]), m["keys"], "black")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def opening(f):
    if f < 6:
        return 0.0
    if f < 44:
        return back_out(phase(f, 6, 18), 1.4)
    if f < 176:
        return 1.0 - ease_in(phase(f, 44, 54))
    if f < 204:
        return back_out(phase(f, 176, 188), 1.4)
    return 1.0 - ease_in(phase(f, 204, 214))


def timeline(f):
    above = L.CART["above"]
    if f < 18 or f >= 200:
        cart = Pose(z=above, scale=HIDDEN)
    elif f < 26:
        cart = Pose(z=above, scale=max(HIDDEN, back_out(phase(f, 18, 25))))
    elif f < 38:
        cart = Pose(z=above * (1 - ease_in(phase(f, 26, 38))))
    elif f < 186:
        cart = Pose(z=-1.5 * math.sin(math.pi * phase(f, 38, 44)))
    else:
        cart = Pose(z=above * ease_out(phase(f, 186, 196)), scale=max(HIDDEN, 1 - ease_in(phase(f, 194, 200))))
    t = phase(f, 66, 168)
    k = math.sin(math.pi * t)
    press = -2.2
    return {"lid": Pose(pitch=L.LID["open"] * opening(f)), "cartridge": cart,
            "option": Pose(z=press * tap(f, 58)), "start": Pose(z=press * tap(f, 62)),
            "shaft": Pose(pitch=18.0 * k * math.sin(2 * math.pi * 3.0 * t),
                          roll=18.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "fire": Pose(z=-2.0 * max(tap(f, f0) for f0 in (78, 98, 116, 134, 152)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "atari800_print.png"))
    m = {name: material(name, L.COLOURS["print"], r, atlas) for name, r in ROUGHNESS.items()}

    body, (flap, hinge) = computer(m)
    fixed_keys, moving_keys = keys(m)
    base, (shaft, shaft_at), (button, button_at) = atari_2600.joystick(
        {"case": material("joystick", "#18181B", 0.5), "print": m["keys"]})
    sx, sy = AL.STICK["at"]
    jx, jy = L.JOYSTICK["at"]
    move = Matrix.Translation((jx - sx, jy - sy, 0.0))
    base.data.transform(move)
    shaft_at, button_at = move @ shaft_at, move @ button_at
    w, d, h = AL.STICK["base"]
    black = (lambda o: colour(o, m["keys"], "black"))
    relief, start, leaving = plugs.place(*plugs.grommet(black, 4.0), m["keys"], (jx, jy + d / 2 - 1.0, h * 0.4),
                                         (0.0, 1.0, 0.0))
    (py0, py1), z = L.PORTS["y"], 6.5                           # the plug's middle: it rests on the table
    port = Vector((L.PORTS["x"][0], py1 - z * (py1 - py0) / L.BASE, z))
    plug, end, back = plugs.place(*plugs.dsub(black, black, 13.0), m["keys"], port, (0.0, -1.0, 0.0))
    wire = cord(m, [start, start + leaving * 30.0 + Vector((0.0, 0.0, -10.0)), end + back * 30.0, end])
    whole = join([body, fixed_keys, base, wire] + relief + plug, "atari800")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("atari800_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    parts = {"lid": (flap, hinge), "cartridge": (cartridge(m), Vector(L.SEAT)), "shaft": (shaft, shaft_at),
             "fire": (button, button_at)}
    parts.update(moving_keys)
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
    print(f"Atari 800: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
