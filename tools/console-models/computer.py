"""The console theme's computer cards (godot/themes/console/models/systems/<id>.glb): the IBM PC, PC-88, X1, X68000,
FM-7, FM Towns, MO5, TO8, SAM Coupé, Spectravideo, ADAM, TRS-80 Color Computer and TRS-80, each from its own
`<card>_layout.py` (computer_layout.py says what one holds), measured from the real machine.

Built in Blender: the blocks (boxes, side outlines across their width, upright plan outlines), their edges rounded, cut
for their slots and drives, their faces printed or plain; the keys, each a block tapering to its printed top, standing
in the keyboard's sloping frame; a CRT monitor or a television (its bezel, the tube's housing tapering behind it, the
screen's recess and the curved glass in it, the screens stacked in front of the glass, each shrunk to nothing until it
is shown); the media (a disk, a cassette, a cartridge, a CD), the moving parts (a tray, a lid, a latch), the lights
(each shrunk to nothing when off), the cables. The printing is two textures drawn by computer_print.py.

A node tree (card.finish()): the root holding the set; the set holding the media, the movers, the lights, the screens
and the keys the clip presses (the media may ride a mover).

The `focused` clip (8 s, looping), the card's own keyframes: the media goes in and the drive's light flickers while it
loads; the machine's loading screen, the made-up game's title, the game played on the keys; then the media comes out
and goes.

Within the system model budget (card.finish() prints the counts). Run from the repo root:

    python tools/console-models/computer_print.py <card> artifacts/made-up-games artifacts/computer
    blender -b --factory-startup --python tools/console-models/computer.py -- artifacts/computer <card> godot/themes/console/models/systems/<id>.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import computer_layout as C  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose  # noqa: E402
from devices import showing_poses  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, prism_x  # noqa: E402
from props import lathe, tube  # noqa: E402

ROUGHNESS = dict(case=0.5, glass=0.25, dark=0.7, cable=0.6)
SPEC = None
ATLAS = None
MEDIA = None


# ---- UVs -------------------------------------------------------------------------------------------------------------

def face_uv(name, b, face):
    w, h = C.face_size(b, face)
    uv = ATLAS.uv(name, w, h)
    return lambda co: uv(*C.face_ab(b, face, co.x, co.y, co.z))


FACE_TEST = dict(front=lambda n: n.y < -0.5 and abs(n.z) < 0.7, back=lambda n: n.y > 0.5 and abs(n.z) < 0.7,
                 top=lambda n: n.z > 0.5, left=lambda n: n.x < -0.7, right=lambda n: n.x > 0.7)


def print_faces(obj, m, b, faces, prefix):
    for face in C.FACES:
        if faces.get(face):
            paint(obj, m["case"], face_uv(f"{prefix}_{face}", b, face),
                  lambda c, n, kind, face=face: kind == "case" and FACE_TEST[face](n))


# ---- Blocks ----------------------------------------------------------------------------------------------------------

def shaped(name, shape, m, corner=0.0):
    kind = shape[0]
    if kind == "box":
        x0, x1, y0, y1, z0, z1 = shape[1:7]
        if corner:
            outline = rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, corner, 5)
            return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], m["case"])
        return box(name, x0, x1, y0, y1, z0, z1, m["case"])
    if kind == "profile":
        return prism_x(name, shape[3], shape[1], shape[2], m["case"])
    if kind == "lathe":
        part = lathe(name, shape[4], m["case"], 32)
        part.data.transform(Matrix.Translation(shape[1:4]))
        return part
    return solid(name, [[(x, y, z) for x, y in shape[1]] for z in (shape[2], shape[3])], m["case"])


def block(spec, k, m, prefix="b"):
    part = shaped(f"{prefix}{k}", spec["shape"], m, spec.get("corner", 0.0))
    if spec.get("round"):
        bevel(part, spec["round"], segments=2, angle=30.0)
    cuts = spec.get("cuts", ())
    if cuts:
        boolean(part, join([box("cut", *c, m["dark"]) for c in cuts], "cuts"))
    coloured(part, m["case"], ATLAS, spec.get("colour", "case"))
    print_faces(part, m, C.bounds(spec["shape"]), spec.get("faces", {}), f"{prefix}{k}")
    return part


# ---- The keyboard ----------------------------------------------------------------------------------------------------

def key_frame(kb):
    x, y, z = kb["origin"]
    return Matrix.Translation((0.0, y, z)) @ Matrix.Rotation(math.radians(kb["slope"]), 4, "X")


def keys(m):
    kb = getattr(SPEC, "KEYBOARD", None)
    if not kb:
        return [], {}
    frame = key_frame(kb)
    normal = frame.to_3x3() @ Vector((0.0, 0.0, 1.0))
    ex0, ex1, es0, es1 = C.keys_extent(kb)
    uv = ATLAS.uv("keys", ex1 - ex0, es1 - es0)
    inverse = frame.inverted()
    h, t = kb["height"], kb["taper"]
    fixed, moving = [], {}
    pressed = pressed_keys()
    for k, (legend, x0, x1, s0, s1, colour) in enumerate(C.key_rects(kb)):
        rings = [[(x0, s0, -2.0), (x1, s0, -2.0), (x1, s1, -2.0), (x0, s1, -2.0)],
                 [(x0, s0, h - 2.0), (x1, s0, h - 2.0), (x1, s1, h - 2.0), (x0, s1, h - 2.0)],
                 [(x0 + t, s0 + t, h), (x1 - t, s0 + t, h), (x1 - t, s1 - t, h), (x0 + t, s1 - t, h)]]
        part = solid("key", rings, m["case"])
        part.data.transform(frame)
        coloured(part, m["case"], ATLAS, colour)
        paint(part, m["case"], lambda co: (lambda q: uv(q.x - ex0, es1 - q.y))(inverse @ co),
              lambda c, n, kind: n.dot(normal) > 0.95)
        if k in pressed.values():
            middle = frame @ Vector(((x0 + x1) / 2, (s0 + s1) / 2, 0.0))
            part.data.transform(Matrix.Translation(-middle))
            moving[f"key_{k}"] = (smoothed(part, 40.0), middle)
        else:
            fixed.append(part)
    return fixed, moving


def pressed_keys():
    """The keys the clip presses, by legend: each its index among the keys (the first with that legend)."""
    legends = [r[0] for r in C.key_rects(SPEC.KEYBOARD)]
    return {legend: legends.index(legend) for legend in getattr(SPEC, "PRESS", {})}


def key_press(f):
    kb = SPEC.KEYBOARD
    down = key_frame(kb).to_3x3() @ Vector((0.0, 0.0, -2.6))
    poses = {}
    index = pressed_keys()
    for legend, frames in getattr(SPEC, "PRESS", {}).items():
        d = max((min(1.0, max(0.0, (f - f0) / 2.0)) * (1.0 - min(1.0, max(0.0, (f - f0 - 4) / 3.0)))
                 for f0 in frames), default=0.0)
        poses[f"key_{index[legend]}"] = Pose(*(down * d))
    return poses


# ---- The display -----------------------------------------------------------------------------------------------------

def rrect(cx, cz, w, h, r, y, n=4):
    return [(x, y, z) for x, z in rounded(cx, cz, w, h, r, n)]


def display(m):
    d = getattr(SPEC, "DISPLAY", None)
    if not d:
        return [], None
    x, y, z = d["at"]
    w, h, depth = d["size"]
    bw, bh, bd = d["back"]
    r = d.get("radius", 6.0)
    cz = z + h / 2
    bezel = solid("bezel", [rrect(x, cz, w, h, r, y), rrect(x, cz, w, h, r, y + depth)], m["case"])
    bevel(bezel, min(4.0, r / 2), segments=2, angle=30.0)
    gw, gh = d["glass"]
    gx, gz = d["glass_at"]
    cut = solid("recess", [rrect(x + gx, z + gz, gw + 2 * d.get("frame", 8.0), gh + 2 * d.get("frame", 8.0),
                                 d.get("corner", 14.0), y - 2.0),
                           rrect(x + gx, z + gz, gw + 4.0, gh + 4.0, d.get("corner", 14.0) / 2, y + d["recess"])],
                m["dark"])
    boolean(bezel, cut)
    coloured(bezel, m["case"], ATLAS, d.get("colour", "case"))
    b = (x - w / 2, x + w / 2, y, y + depth, z, z + h)
    if d.get("faces", {}).get("front"):
        uv = ATLAS.uv("display_front", w, h)
        paint(bezel, m["case"], lambda co: uv(co.x - b[0], b[5] - co.z),
              lambda c, n, kind: kind == "case" and n.y < -0.9)
    hz = z + h / 2 + d.get("back_dz", 0.0)
    housing = solid("housing", [rrect(x, cz, w - 12.0, h - 12.0, r, y + depth - 2.0),
                                rrect(x, hz, bw, bh, r, y + depth + bd)], m["case"])
    coloured(housing, m["case"], ATLAS, d.get("back_colour", d.get("colour", "case")))
    glass = curved("glass", gw, gh, d.get("bulge", 8.0), MEDIA.uv("boot", 1.0, 1.0), m["glass"], 12, 9)
    glass_at = Vector((x + gx, y + d["recess"] - 1.0, z + gz))
    glass.data.transform(Matrix.Translation(glass_at))
    return [bezel, housing, glass], glass_at


def screens(m, glass_at):
    d = SPEC.DISPLAY
    gw, gh = d["glass"]
    out = {}
    for k, name in enumerate(C.SCREENS[1:]):
        part = curved("screen_" + name, gw, gh, d.get("bulge", 8.0), MEDIA.uv(name, 1.0, 1.0), m["glass"], 12, 9)
        out["screen_" + name] = (part, glass_at + Vector((0.0, -0.12 * (k + 1), 0.0)))
    return out


# ---- Media, movers, lights, cables -----------------------------------------------------------------------------------

def media(m):
    spec = getattr(SPEC, "MEDIA", None)
    if not spec:
        return None
    w, d, t = spec["size"]
    if spec["kind"] == "disc":
        part = lathe("media", [(7.5, -t / 2), (w / 2, -t / 2), (w / 2, t / 2), (7.5, t / 2)], m["case"], 48)
    else:
        part = box("media", -w / 2, w / 2, -d / 2, d / 2, -t / 2, t / 2, m["case"])
        bevel(part, min(0.8, t / 4), segments=1)
    coloured(part, m["case"], ATLAS, spec.get("colour", "case"))
    if spec.get("label"):
        uv = ATLAS.uv("label", w, d)
        paint(part, m["case"], lambda co: uv(co.x + w / 2, d / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    rx, ry, rz = spec.get("turn", (0.0, 0.0, 0.0))
    part.data.transform(Matrix.Rotation(math.radians(rz), 4, "Z") @ Matrix.Rotation(math.radians(ry), 4, "Y")
                        @ Matrix.Rotation(math.radians(rx), 4, "X"))
    return smoothed(part, 40.0)


def movers(m):
    out = {}
    for k, spec in enumerate(getattr(SPEC, "MOVERS", ())):
        part = block(spec, k, m, prefix="m")
        origin = Vector(spec.get("origin", (0.0, 0.0, 0.0)))
        part.data.transform(Matrix.Translation(-origin))
        out[spec["name"]] = (smoothed(part, 35.0), origin)
    return out


LIGHT_FACE = dict(front=(Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0))),
                  top=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
                  right=(Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))),
                  left=(Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0))))


def lights(m):
    out = {}
    for spec in getattr(SPEC, "LIGHTS", ()):
        u, v, n = LIGHT_FACE[spec["face"]]
        w, h = spec["size"]
        corners = [u * a + v * b for a, b in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
        part = solid(spec["name"], [[c - n * 0.2 for c in corners], [c + n * 0.35 for c in corners]], m["case"])
        coloured(part, m["case"], ATLAS, spec["colour"])
        out[spec["name"]] = (part, Vector(spec["at"]))
    return out


def cables(m):
    out = []
    for spec in getattr(SPEC, "CABLES", ()):
        wire = tube("cable", curve(spec["points"], 5), spec.get("r", 2.0), m["case"], 10)
        out.append(smoothed(coloured(wire, m["case"], ATLAS, spec.get("colour", "cable")), 50.0))
    return out


# ---- The focused clip ------------------------------------------------------------------------------------------------

def pose(values):
    return Pose(**{k: v for k, v in values.items()})


def timeline(f):
    poses = showing_poses(C.SCREENS[1:], lambda g: C.showing(SPEC, g), f) if getattr(SPEC, "DISPLAY", None) else {}
    spec = getattr(SPEC, "MEDIA", None)
    if spec:
        values = C.keyed(spec["keys"], f)
        if values.get("scale", 1.0) < HIDDEN:
            values["scale"] = HIDDEN
        poses["media"] = pose(values)
    for mover in getattr(SPEC, "MOVERS", ()):
        poses[mover["name"]] = pose(C.keyed(mover["keys"], f))
    for light in getattr(SPEC, "LIGHTS", ()):
        poses[light["name"]] = Pose() if C.lit(light, f) else Pose(scale=HIDDEN)
    if getattr(SPEC, "KEYBOARD", None):
        poses.update(key_press(f))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    global SPEC, ATLAS, MEDIA
    args = sys.argv[sys.argv.index("--") + 1:]
    images, card, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    SPEC = C.load(card)
    ATLAS = Atlas(C.PRINT_ATLAS, C.pack(SPEC), C.swatches(SPEC))
    MEDIA = Atlas(C.MEDIA_ATLAS, C.media_regions())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", dark="#0C0C0E", cable="#1A1A1C"), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, f"{card}_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, f"{card}_media.png"))))

    solids = [block(spec, k, m) for k, spec in enumerate(SPEC.BLOCKS)]
    fixed, pressed = keys(m)
    shown, glass_at = display(m)
    whole = smoothed(join(solids + fixed + shown + cables(m), card), 35.0)
    parts = dict(pressed)
    parts.update(movers(m))
    parts.update(lights(m))
    item = media(m)
    if item is not None:
        holder = SPEC.MEDIA.get("rides")
        seat = Vector(SPEC.MEDIA["seat"])
        if holder:
            parts["media"] = (item, seat - parts[holder][1], holder)
        else:
            parts["media"] = (item, seat)
    if glass_at is not None:
        parts.update(screens(m, glass_at))
    finish(card, whole, parts, timeline, 240, SPEC.YAW, SPEC.PITCH, out, SPEC.NAME)


if __name__ == "__main__":
    main()
