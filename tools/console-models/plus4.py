"""The console theme's Commodore Plus/4 system model (godot/themes/console/models/systems/plus4.glb): a Plus/4 and its
1531 Datassette in front of the portable television the ZX Spectrum's card has.

Built in Blender (plus4_layout.py has the measurements, taken from photographs). The Plus/4 is its side outline extruded
across its width, the cooling fins standing along its back block; its keys stand on the deck in the deck's frame, each
tapering to its printed top, the function keys lie on the chamfer and the cursor keys' diamond on the deck at the right.
The 1531 is a box round its plan's corners, the cassette's well cut into its top under the lid; the lid is a frame round
its window, hinged at its back; its six piano keys stand at its front, its cable runs to its mini-DIN plug in the
Plus/4's back (plugs.py's). Behind them stands zx_spectrum.py's television. The printing is two textures
(plus4_print.py's): `print`, projected from above onto the Plus/4, the 1531, the lid and the cassette's label (with the
television's front where its layout puts it); and `media`, the screens.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (on its hinge) and in it the cassette (waiting in front of it, shrunk to nothing), PLAY, STOP and EJECT,
the television's seven screens (those not shown behind the glass), and the keys the clip presses.

The `focused` clip (8 s, looping): EJECT, the lid swings up, the cassette slides into it and the lid shuts; LOAD and
RETURN, PRESS PLAY ON TAPE; PLAY goes down, SEARCHING, FOUND ODYSSEY, LOADING, the title, and the game played on the
cursor keys; then STOP, EJECT, the cassette slides out and goes, the lid shuts, and READY. is back.

Four materials (case, tv, dark, glass) and two 1024² textures, within the system model budget. Run from the repo root:

    python tools/console-models/plus4_print.py artifacts/plus4
    blender -b --factory-startup --python tools/console-models/plus4.py -- artifacts/plus4 godot/themes/console/models/systems/plus4.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plugs  # noqa: E402
import plus4_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from amiga import curved, paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)
from zx_spectrum import television  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 20.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, tv=0.45, dark=0.7, glass=0.35)
SCREENS = ("boot", "press", "search", "found", "title", "game_1", "game_2")
BEHIND = 3.0              # how far back a screen that isn't shown waits: behind the glass
TYPED = ("L", "O", "A", "D", "Return")
ARROW_KEYS = dict(up=(0.0, 1.0), down=(0.0, -1.0), left=(-1.0, 0.0), right=(1.0, 0.0))


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


TOP = atlas_uv(L.PRINT_REGIONS["top"], L.WIDTH, L.FINS["y"][1])
DECK_TOP = atlas_uv(L.PRINT_REGIONS["deck"], L.DECK["size"][0], L.DECK["size"][1])


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.FINS["y"][1] - co.y)


def on_deck(name, outline, h0, h1, mat, outline1=None):
    """A solid from an (x, s) outline in the deck's frame, from h0 off it to h1 (its top outline1, if given)."""
    top = outline1 or outline
    return solid(name, [[(x, *L.deck_point(s, h0)) for x, s in outline], [(x, *L.deck_point(s, h1)) for x, s in top]],
                 mat)


def plan_s(y):
    """How far up the deck from its front edge the deck is at y."""
    return (y - L.FRONT[0]) / math.cos(L.SLOPE)


# ---- The Plus/4 ------------------------------------------------------------------------------------------------------

def plus4(m):
    """The case and its fins, printed."""
    half = L.WIDTH / 2
    body = prism_x("plus4", L.PROFILE, -half, half, m["case"])
    bevel(body, 2.5, segments=2, angle=40)
    (fx0, fx1), (fy0, fy1), (fz0, fz1) = L.FINS["x"], L.FINS["y"], L.FINS["z"]
    n, t = L.FINS["count"], L.FINS["thickness"]
    pitch = (fx1 - fx0) / n
    outline = [(fy0, fz0), (fy1, fz0), (fy1, fz1 - 2.0), (fy1 - 2.0, fz1), (fy0, fz1)]
    fins = [prism_x("fin", outline, fx0 + (k + 0.5) * pitch - t / 2, fx0 + (k + 0.5) * pitch + t / 2, m["case"])
            for k in range(n)]
    whole = join([body] + fins, "plus4")
    colour(whole, m["case"], "case")
    paint(whole, m["case"], top_uv, lambda c, n_, kind: n_.z > 0.3)
    return whole


def keys(m):
    """The keys: the main block standing on the deck, the function keys on the chamfer, the cursor keys; those the clip
    presses apart (each its foot's middle at its origin, with where it goes), the rest joined."""
    fixed, moving = [], {}
    inset, top = L.KEY["inset"], L.KEY["height"]

    def lift(part, name, middle):
        part.data.transform(Matrix.Translation(-middle))
        moving[name] = (part, middle)

    for legend, x0, x1, s in L.keys():
        foot = [(x0 + 0.6, s - 9.0), (x1 - 0.6, s - 9.0), (x1 - 0.6, s + 9.0), (x0 + 0.6, s + 9.0)]
        cap = [(x0 + inset, s - 9.5 + inset), (x1 - inset, s - 9.5 + inset), (x1 - inset, s + 9.5 - inset),
               (x0 + inset, s + 9.5 - inset)]
        part = on_deck("key", foot, -1.0, top, m["case"], cap)
        colour(part, m["case"], "key")
        paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.85)
        if legend in TYPED and legend not in moving:
            lift(part, legend, Vector(((x0 + x1) / 2, *L.deck_point(s, -1.0))))
        else:
            fixed.append(part)

    (cy0, cz0), (cy1, cz1) = L.DECK_BACK, L.PROFILE[5]              # the chamfer, from its foot to its top
    along = Vector((0.0, cy1 - cy0, cz1 - cz0)).normalized()
    out = Vector((0.0, -along.z, along.y))
    w, (fy0, fy1) = L.FKEYS["width"], L.FKEYS["y"]
    for x in L.FKEYS["x"]:
        corners = [Vector((xx, cy0, cz0)) + along * ((yy - cy0) / along.y) for xx, yy in
                   ((x, fy0), (x + w, fy0), (x + w, fy1), (x, fy1))]
        part = solid("fkey", [[tuple(p + out * h) for p in corners] for h in (-0.5, 2.2)], m["case"])
        colour(part, m["case"], "fkey")
        paint(part, m["case"], top_uv, lambda c, n, kind: n.dot(out) > 0.9)
        fixed.append(part)

    (cx, cy), reach, (kw, kh) = L.CURSOR["at"], L.CURSOR["reach"], L.CURSOR["size"]
    for name, (dx, dy) in ARROW_KEYS.items():
        kx, s = cx + dx * reach, plan_s(cy + dy * reach)
        half = kh / 2 / math.cos(L.SLOPE)
        outline = [(kx - kw / 2, s - half), (kx + kw / 2, s - half), (kx + kw / 2, s + half), (kx - kw / 2, s + half)]
        part = on_deck(name, outline, -1.0, 6.0, m["case"])
        colour(part, m["case"], "key")
        paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.85)
        lift(part, name, Vector((kx, *L.deck_point(s, -1.0))))
    return join(fixed, "keys"), moving


# ---- The 1531 --------------------------------------------------------------------------------------------------------

def plan(w, d, r0, r1, segments=6):
    """A plan outline w x d from (0, 0), its left corners rounded r0, its right ones r1; anticlockwise."""
    points = []
    for (cx, cy, r, a0) in ((w - r1, r1, r1, -90), (w - r1, d - r1, r1, 0), (r0, d - r0, r0, 90), (r0, r0, r0, 180)):
        for k in range(segments + 1):
            a = math.radians(a0 + 90 * k / segments)
            points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return points


def datassette(m):
    """The 1531 in its own frame: the box, the well and the lid's recess cut in, printed; its fixed keys; and its lid
    (its origin on its hinge), PLAY, STOP and EJECT apart."""
    (w, d, h), (r0, r1) = L.DECK["size"], L.DECK["r"]
    body = solid("datassette", [[(x, y, z) for x, y in plan(w, d, r0, r1)] for z in (0.0, h)], m["case"])
    bevel(body, 2.0, segments=2, angle=40)
    (lx0, lx1), (ly0, ly1), t = L.LID["x"], L.LID["y"], L.LID["thickness"]
    boolean(body, box("well", lx0 + 2.0, lx1 - 2.0, ly0 + 2.0, ly1 - 2.0, 18.0, h + 1.0, m["case"]))
    boolean(body, box("recess", lx0, lx1, ly0, ly1, h - t, h + 1.0, m["case"]))
    colour(body, m["case"], "deck")
    paint(body, m["case"], lambda co: DECK_TOP(co.x, d - co.y), lambda c, n, kind: n.z > 0.9 and c.z > h - 0.5)
    paint(body, m["case"], swatch("black"),
          lambda c, n, kind: lx0 + 1.0 < c.x < lx1 - 1.0 and ly0 + 1.0 < c.y < ly1 - 1.0 and c.z < h - t - 0.5)

    fixed, moving = [body], {}
    (kx0, kx1), (ky0, ky1), kh = L.PIANO["x"], L.PIANO["y"], L.PIANO["height"]
    kw = (kx1 - kx0) / 6
    for k, name in enumerate(L.PIANO["names"]):
        x0, x1 = kx0 + k * kw + 0.4, kx0 + (k + 1) * kw - 0.4
        part = box(name, x0, x1, ky0 - 4.0, ky1 - 6.0, h - kh, h + 0.6, m["case"])
        bevel(part, 0.8, segments=1)
        colour(part, m["case"], "fkey")
        if name in ("PLAY", "STOP", "EJECT"):
            middle = Vector(((x0 + x1) / 2, ky0, h - kh))
            part.data.transform(Matrix.Translation(-middle))
            moving[name.lower()] = (part, middle)
        else:
            fixed.append(part)
    boolean(body, box("keys_slot", kx0 - 0.5, kx1 + 0.5, ky0 - 5.0, ky1 - 5.5, h - kh - 1.0, h + 1.0, m["case"]))

    lid = box("lid", lx0 + 0.5, lx1 - 0.5, ly0 + 0.5, ly1 - 0.5, h - t + 0.3, h, m["case"])
    boolean(lid, box("window", lx0 + 9.0, lx1 - 9.0, ly0 + 19.0, ly1 - 9.0, h - t - 1.0, h + 1.0, m["case"]))
    colour(lid, m["case"], "deck")
    paint(lid, m["case"], lambda co: DECK_TOP(co.x, d - co.y), lambda c, n, kind: n.z > 0.9)
    hinge = Vector(((lx0 + lx1) / 2, ly1 - 0.5, h))
    lid.data.transform(Matrix.Translation(-hinge))
    moving["lid"] = (lid, hinge)
    return join(fixed, "datassette"), moving


def cassette(m):
    """The cassette, lying flat, its middle at its origin: side A's label up, side B's down (the side the viewer sees
    while it slides into the open lid)."""
    w, d, t = L.CASSETTE["size"]
    part = box("cassette", -w / 2, w / 2, -d / 2, d / 2, -t / 2, t / 2, m["case"])
    bevel(part, 1.2, segments=2)
    colour(part, m["case"], "cassette")
    label = atlas_uv(L.PRINT_REGIONS["cassette"], w, d)
    paint(part, m["case"], lambda co: label(co.x + w / 2, d / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    paint(part, m["case"], lambda co: label(co.x + w / 2, d / 2 + co.y), lambda c, n, kind: n.z < -0.9)
    return part


def cable(m, points):
    """The Datassette's cable: a tube along the Bézier curve through four control points."""
    p0, p1, p2, p3 = (Vector(p) for p in points)
    path = [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in [k / 20 for k in range(21)]]
    bm = bmesh.new()
    rings, normal = [], Vector((0.0, 0.0, 1.0))
    for k, p in enumerate(path):
        tangent = (path[min(k + 1, 20)] - path[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * 2.2)
                      for a in [2 * math.pi * j / 8 for j in range(8)]])
    for a, b in zip(rings, rings[1:]):
        for j in range(8):
            bm.faces.new([a[j], a[(j + 1) % 8], b[(j + 1) % 8], b[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return colour(new_object("cable", bm, m["case"]), m["case"], "black")


def screens(m):
    """The television's seven screens, each the glass's whole area."""
    gw, gh = SL.TV["glass"]["size"]
    return {name: curved(name, gw, gh, SL.TV["glass"]["bulge"], atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0), m["glass"])
            for name in SCREENS}


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def shown(f):
    if f < 72 or f >= 176:
        return "boot"
    if f < 84:
        return "press"
    if f < 108:
        return "search"
    if f < 128:
        return "found"
    if f < 140:
        return "title"
    return "game_1" if ((f - 140) // 6) % 2 == 0 else "game_2"


def opening(f):
    if f < 10:
        return 0.0
    if f < 42:
        return back_out(phase(f, 10, 20), 1.4)
    if f < 180:
        return 1.0 - ease_in(phase(f, 42, 50))
    if f < 204:
        return back_out(phase(f, 180, 190), 1.4)
    return 1.0 - ease_in(phase(f, 204, 212))


def timeline(f):
    out = L.CASSETTE["above"]
    if f < 20 or f >= 202:
        tape = Pose(y=-out, scale=HIDDEN)
    elif f < 27:
        tape = Pose(y=-out, scale=max(HIDDEN, back_out(phase(f, 20, 27))))
    elif f < 190:
        tape = Pose(y=-out * (1 - smooth(phase(f, 27, 40))))
    else:
        tape = Pose(y=-out * ease_out(phase(f, 190, 198)), scale=max(HIDDEN, 1 - ease_in(phase(f, 196, 202))))
    press = -2.4
    poses = {"lid": Pose(pitch=L.LID["open"] * opening(f)), "cassette": tape,
             "eject": Pose(z=-3.0 * max(tap(f, 6), tap(f, 176))), "stop": Pose(z=-3.0 * tap(f, 170)),
             "play": Pose(z=-5.0 * smooth(phase(f, 80, 84)) * (1 - smooth(phase(f, 172, 176))))}
    for name in SCREENS:
        poses[name] = Pose() if name == shown(f) else Pose(y=BEHIND)
    for k, name in enumerate(TYPED):
        poses[name] = Pose(z=press * tap(f, 54 + 4 * k))
    for name, times in (("up", (144, 160)), ("down", (152,)), ("left", (148, 164)), ("right", (142, 156, 168))):
        poses[name] = Pose(z=press * max(tap(f, f0) for f0 in times))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    atlas = bpy.data.images.load(os.path.join(images, "plus4_print.png"))
    media = bpy.data.images.load(os.path.join(images, "plus4_media.png"))
    m = {"case": material("case", L.COLOURS["print"], ROUGHNESS["case"], atlas),
         "tv": material("tv", SL.COLOURS["tv"], ROUGHNESS["tv"]),
         "dark": material("dark", L.COLOURS["dark"], ROUGHNESS["dark"]),
         "glass": material("glass", L.COLOURS["print"], ROUGHNESS["glass"], media)}
    m["print"] = m["case"]                                    # television() prints its front with the set's atlas

    fixed_keys, moving = keys(m)
    deck, deck_parts = datassette(m)
    dx, dy = L.DECK["at"]
    place = Matrix.Translation((dx, dy, 0.0))
    deck.data.transform(place)
    for name, (part, where) in deck_parts.items():
        moving[name] = (part, place @ where)
    tv = television(m, m["glass"], atlas_uv(L.MEDIA_REGIONS["boot"], 1.0, 1.0))
    shift = Matrix.Translation((L.TV_AT[0] - SL.TV["at"][0], L.TV_AT[1] - SL.TV["at"][1], 0.0))
    for part in tv:
        part.data.transform(shift)
    w, d, _ = L.DECK["size"]
    black = (lambda o: colour(o, m["case"], "black"))
    relief, start, leaving = plugs.place(*plugs.grommet(black, 4.0), m["case"], (dx + 30.0, dy + d, 20.0),
                                         (0.0, 1.0, 0.0))
    plug, end, back = plugs.place(*plugs.din(black, black, 5.6), m["case"], (120.0, L.DEPTH, 14.0), (0.0, 1.0, 0.0))
    lead = cable(m, [start, start + leaving * 40.0 + Vector((0.0, 0.0, -16.0)), end + back * 30.0, end])
    whole = join([plus4(m), fixed_keys, deck, lead] + relief + plug + tv, "plus4")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("plus4_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    s = SL.TV["screen"]
    glass_front = Vector((L.TV_AT[0] + s["x"], L.TV_AT[1] + s["depth"] - 0.4, s["z"]))
    moving.update({name: (part, glass_front) for name, part in screens(m).items()})
    nodes = {}
    for name, (part, where) in moving.items():
        if name not in SCREENS:
            for p in part.data.polygons:
                p.use_smooth = True
            part.data.set_sharp_from_angle(angle=math.radians(35))
        part.parent = whole
        part.location = where
        nodes[name] = part
    (lx0, lx1), (ly0, ly1), t = L.LID["x"], L.LID["y"], L.LID["thickness"]
    tape = cassette(m)
    tape.parent = nodes["lid"]                                # it rides in the lid
    tape.location = Vector((0.0, (ly0 + 19.0 + ly1 - 9.0) / 2 - (ly1 - 0.5), -t - L.CASSETTE["size"][2] / 2 + 0.5))
    nodes["cassette"] = tape

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"Plus/4: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
