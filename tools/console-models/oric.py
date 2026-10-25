"""The console theme's Oric system model (godot/themes/console/models/systems/oric.glb): an Oric Atmos and a cassette
recorder in front of the portable television the ZX Spectrum's card has.

Built in Blender (oric_layout.py has the measurements, taken from photographs and a listing). The Atmos is a red base
under the black shell, the shell its side outline extruded across its width; the keyboard's well is cut into the deck in
the deck's frame and the grille's plateau stands on the back block's left; its keys stand in the well, each tapering to
its printed top. The recorder is a box round its plan's corners, the cassette's well cut into its top under the lid; the
lid is a frame round its window, hinged at its back; its six piano keys stand at its front, its cable runs to the
Atmos's back. Behind them stands zx_spectrum.py's television. The printing is two textures (oric_print.py's): `print`,
projected from above onto the Atmos, the recorder, the lid and the cassette's label (with the television's front where
its layout puts it); and `media`, the screens.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (on its hinge) and in it the cassette (waiting in front of it, shrunk to nothing), PLAY and STOP/EJ, the
television's six screens (those not shown behind the glass), and the keys the clip presses.

The `focused` clip (8 s, looping): STOP/EJ, the lid swings up, the cassette slides into it and the lid shuts; CLOAD""
and RETURN, Searching; PLAY goes down, Loading ODYSSEY, the title, SPACE, and the game played on the arrow keys; then
STOP/EJ twice, the cassette slides out and goes, the lid shuts, and Ready is back.

Four materials (case, tv, dark, glass) and two 1024² textures, within the system model budget. Run from the repo root:

    python tools/console-models/oric_print.py artifacts/oric
    blender -b --factory-startup --python tools/console-models/oric.py -- artifacts/oric godot/themes/console/models/systems/oric.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oric_layout as L  # noqa: E402
import zx_spectrum_layout as SL  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import (bevel, boolean, box, export, join, material, new_object, prism_x,  # noqa: E402
                                  triangles)
from zx_spectrum import television  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 20.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.45, tv=0.45, dark=0.7, glass=0.35)
SCREENS = ("boot", "search", "loading", "title", "game_1", "game_2")
BEHIND = 3.0              # how far back a screen that isn't shown waits: behind the glass
PRESSED = dict(c="C", l="L", o="O", a="A", d="D", quote="'", shift="SHIFT", enter="RETURN", space=" ",
               left="←", down="↓", up="↑", right="→")


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def colour(obj, mat, name):
    paint(obj, mat, swatch(name), lambda c, n, kind: True)
    return obj


TOP = atlas_uv(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH)
DECK_TOP = atlas_uv(L.PRINT_REGIONS["recorder"], L.RECORDER["size"][0], L.RECORDER["size"][1])


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def on_deck(name, outline, h0, h1, mat, outline1=None):
    """A solid from an (x, s) outline in the deck's frame, from h0 off it to h1 (its top outline1, if given)."""
    top = outline1 or outline
    return solid(name, [[(x, *L.deck_point(s, h0)) for x, s in outline], [(x, *L.deck_point(s, h1)) for x, s in top]],
                 mat)


# ---- The Atmos -------------------------------------------------------------------------------------------------------

def atmos(m):
    """The red base, the black shell with the well cut in and the grille's plateau; printed."""
    half = L.WIDTH / 2
    base = solid("base", [[(x, y, z) for x, y in rounded(0.0, L.DEPTH / 2, L.WIDTH, L.DEPTH, 6.0, 4)]
                          for z in (0.0, L.BASE + 1.0)], m["case"])
    bevel(base, 1.0, segments=1)
    colour(base, m["case"], "base")
    shell = prism_x("oric", L.PROFILE, -half, half, m["case"])
    bevel(shell, 2.5, segments=2, angle=40)
    (wx0, wx1), (ws0, ws1), depth, r = L.WELL["x"], L.WELL["s"], L.WELL["depth"], L.WELL["r"]
    boolean(shell, on_deck("well", rounded((wx0 + wx1) / 2, (ws0 + ws1) / 2, wx1 - wx0, ws1 - ws0, r, 3), -depth,
                           20.0, m["case"]))
    plateau = prism_z("plateau", L.PLATEAU, L.DECK_BACK[1] - 4.0, L.HEIGHT, m["case"])
    bevel(plateau, 1.0, segments=1)
    shell = join([shell, plateau], "oric")
    colour(shell, m["case"], "shell")
    paint(shell, m["case"], top_uv, lambda c, n, kind: n.z > 0.3)
    return join([base, shell], "oric")


def keys(m):
    """The keys, standing in the well, each tapering to its printed top; those the clip presses apart (each its foot's
    middle at its origin, with where it goes), the rest joined."""
    fixed, moving = [], {}
    inset, depth = L.KEY["inset"], L.WELL["depth"]
    top = L.KEY["height"] - depth
    for legend, x0, x1, y in L.keys():
        s = L.plan_s(y)
        foot = [(x0 + 0.6, s - 9.0), (x1 - 0.6, s - 9.0), (x1 - 0.6, s + 9.0), (x0 + 0.6, s + 9.0)]
        cap = [(x0 + inset, s - 9.5 + inset), (x1 - inset, s - 9.5 + inset), (x1 - inset, s + 9.5 - inset),
               (x0 + inset, s + 9.5 - inset)]
        part = on_deck("key", foot, -depth - 1.0, top, m["case"], cap)
        colour(part, m["case"], "red" if legend in L.RED else "key")
        paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.85)
        name = next((k for k, v in PRESSED.items() if v == legend and k not in moving), None)
        if name:
            middle = Vector(((x0 + x1) / 2, *L.deck_point(s, -depth - 1.0)))
            part.data.transform(Matrix.Translation(-middle))
            moving[name] = (part, middle)
        else:
            fixed.append(part)
    return join(fixed, "keys"), moving


# ---- The recorder ----------------------------------------------------------------------------------------------------

def recorder(m):
    """The recorder in its own frame: the box, the well and the lid's recess cut in, printed; its fixed keys; and its
    lid (its origin on its hinge), PLAY and STOP/EJ apart."""
    (w, d, h), r = L.RECORDER["size"], L.RECORDER["r"]
    body = solid("recorder", [[(x, y, z) for x, y in rounded(w / 2, d / 2, w, d, r, 4)] for z in (0.0, h)], m["case"])
    bevel(body, 2.0, segments=2, angle=40)
    (lx0, lx1), (ly0, ly1), t = L.LID["x"], L.LID["y"], L.LID["thickness"]
    boolean(body, box("well", lx0 + 2.0, lx1 - 2.0, ly0 + 2.0, ly1 - 2.0, 16.0, h + 1.0, m["case"]))
    boolean(body, box("recess", lx0, lx1, ly0, ly1, h - t, h + 1.0, m["case"]))
    (kx0, kx1), (ky0, ky1), kh = L.PIANO["x"], L.PIANO["y"], L.PIANO["height"]
    boolean(body, box("keys_slot", kx0 - 0.5, kx1 + 0.5, ky0 - 5.0, ky1 - 5.5, h - kh - 1.0, h + 1.0, m["case"]))
    colour(body, m["case"], "recorder")
    paint(body, m["case"], lambda co: DECK_TOP(co.x, d - co.y), lambda c, n, kind: n.z > 0.9 and c.z > h - 0.5)
    paint(body, m["case"], swatch("black"),
          lambda c, n, kind: lx0 + 1.0 < c.x < lx1 - 1.0 and ly0 + 1.0 < c.y < ly1 - 1.0 and c.z < h - t - 0.5)

    fixed, moving = [body], {}
    kw = (kx1 - kx0) / 6
    for k, name in enumerate(L.PIANO["names"]):
        x0, x1 = kx0 + k * kw + 0.4, kx0 + (k + 1) * kw - 0.4
        part = box(name, x0, x1, ky0 - 4.0, ky1 - 6.0, h - kh, h + 0.6, m["case"])
        bevel(part, 0.8, segments=1)
        colour(part, m["case"], "silver")
        if name in ("PLAY", "STOP/EJ"):
            middle = Vector(((x0 + x1) / 2, ky0, h - kh))
            part.data.transform(Matrix.Translation(-middle))
            moving["play" if name == "PLAY" else "stop"] = (part, middle)
        else:
            fixed.append(part)

    lid = box("lid", lx0 + 0.5, lx1 - 0.5, ly0 + 0.5, ly1 - 0.5, h - t + 0.3, h, m["case"])
    boolean(lid, box("window", lx0 + 9.0, lx1 - 9.0, ly0 + 15.0, ly1 - 9.0, h - t - 1.0, h + 1.0, m["case"]))
    colour(lid, m["case"], "recorder")
    paint(lid, m["case"], lambda co: DECK_TOP(co.x, d - co.y), lambda c, n, kind: n.z > 0.9)
    hinge = Vector(((lx0 + lx1) / 2, ly1 - 0.5, h))
    lid.data.transform(Matrix.Translation(-hinge))
    moving["lid"] = (lid, hinge)
    return join(fixed, "recorder"), moving


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
    """The recorder's cable: a tube along the Bézier curve through four control points."""
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
    """The television's six screens, each the glass's whole area."""
    gw, gh = SL.TV["glass"]["size"]
    return {name: curved(name, gw, gh, SL.TV["glass"]["bulge"], atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0), m["glass"])
            for name in SCREENS}


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def shown(f):
    if f < 80 or f >= 174:
        return "boot"
    if f < 100:
        return "search"
    if f < 124:
        return "loading"
    if f < 134:
        return "title"
    return "game_1" if ((f - 134) // 6) % 2 == 0 else "game_2"


def opening(f):
    if f < 10:
        return 0.0
    if f < 36:
        return back_out(phase(f, 10, 20), 1.4)
    if f < 180:
        return 1.0 - ease_in(phase(f, 36, 44))
    if f < 204:
        return back_out(phase(f, 180, 190), 1.4)
    return 1.0 - ease_in(phase(f, 204, 212))


def timeline(f):
    out = L.CASSETTE["out"]
    if f < 18 or f >= 202:
        tape = Pose(y=-out, scale=HIDDEN)
    elif f < 24:
        tape = Pose(y=-out, scale=max(HIDDEN, back_out(phase(f, 18, 24))))
    elif f < 190:
        tape = Pose(y=-out * (1 - smooth(phase(f, 24, 34))))
    else:
        tape = Pose(y=-out * ease_out(phase(f, 190, 198)), scale=max(HIDDEN, 1 - ease_in(phase(f, 196, 202))))
    press = -2.4
    poses = {"lid": Pose(pitch=L.LID["open"] * opening(f)), "cassette": tape,
             "stop": Pose(z=-3.0 * max(tap(f, 6), tap(f, 170), tap(f, 176))),
             "play": Pose(z=-5.0 * smooth(phase(f, 82, 86)) * (1 - smooth(phase(f, 170, 174))))}
    for name in SCREENS:
        poses[name] = Pose() if name == shown(f) else Pose(y=BEHIND)
    taps = dict(c=(48,), l=(52,), o=(56,), a=(60,), d=(64,), quote=(68, 72), enter=(78,), space=(130,),
                up=(140, 156), down=(148,), left=(144, 164), right=(136, 152, 160))
    for name, times in taps.items():
        poses[name] = Pose(z=press * max(tap(f, f0) for f0 in times))
    poses["shift"] = Pose(z=press * smooth(phase(f, 66, 68)) * (1 - smooth(phase(f, 75, 77))))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    m = {"case": material("case", L.COLOURS["print"], ROUGHNESS["case"],
                          bpy.data.images.load(os.path.join(images, "oric_print.png"))),
         "tv": material("tv", SL.COLOURS["tv"], ROUGHNESS["tv"]),
         "dark": material("dark", L.COLOURS["dark"], ROUGHNESS["dark"]),
         "glass": material("glass", L.COLOURS["print"], ROUGHNESS["glass"],
                           bpy.data.images.load(os.path.join(images, "oric_media.png")))}
    m["print"] = m["case"]                                    # television() prints its front with the set's atlas

    fixed_keys, moving = keys(m)
    deck, deck_parts = recorder(m)
    rx, ry = L.RECORDER["at"]
    place = Matrix.Translation((rx, ry, 0.0))
    deck.data.transform(place)
    for name, (part, where) in deck_parts.items():
        moving[name] = (part, place @ where)
    tv = television(m, m["glass"], atlas_uv(L.MEDIA_REGIONS["boot"], 1.0, 1.0))
    shift = Matrix.Translation((L.TV_AT[0] - SL.TV["at"][0], L.TV_AT[1] - SL.TV["at"][1], 0.0))
    for part in tv:
        part.data.transform(shift)
    w, d, _ = L.RECORDER["size"]
    lead = cable(m, [(rx + 30.0, ry + d - 1.0, 20.0), (rx + 30.0, ry + d + 30.0, 2.2), (27.0, L.DEPTH + 30.0, 2.2),
                     (27.0, L.DEPTH - 1.0, 20.0)])
    whole = join([atmos(m), fixed_keys, deck, lead] + tv, "oric")
    for p in whole.data.polygons:
        p.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))

    root = bpy.data.objects.new("oric_root", None)
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
    tape.location = Vector((0.0, (ly0 + 15.0 + ly1 - 9.0) / 2 - (ly1 - 0.5), -t - L.CASSETTE["size"][2] / 2 + 0.5))
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
    print(f"Oric: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
