"""The console theme's Apple IIGS system model (godot/themes/console/models/systems/apple2gs.glb): an Apple IIGS, its
AppleColor RGB monitor on it, its Apple 3.5 Drive beside it, its keyboard and mouse in front, Check startup device! on
the screen.

Built in Blender from the real machines' proportions (apple2gs_layout.py has the measurements, taken from photographs).
The IIGS is its plinth (the lip sloping along its front) and its main box, grooved across its top and along its sides,
the seam between its lid and its base rising along its sides. The monitor's deep front frame stands on it, the screen's
opening sloping in to the curved glass, its housing behind, grooved along its sides and top, three knobs in its right
side. The drive is a low box, its slot cut high in its front, its top grooved. The keyboard is a wedge, its keys
standing on it, tapering to their printed tops, a blank column between the main block and the keypad, the raised
strip behind with the power key; the mouse a box domed towards its back. The printing is two textures drawn by
apple2gs_print.py: the keyboard's top, the IIGS's, the monitor's and the drive's fronts, the mouse's top and swatches;
and the screens and the disk.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the 3.5-inch disk (waiting in the drive, shrunk to nothing), the drive's eject button and its lit light, three
screens over the glass (GS/OS starting, and the title screen and a moment of play of a made-up game, Odyssey), shrunk
to nothing, and RETURN.

The `focused` clip (8 s, looping) boots a game: the disk slides into the drive and its light flickers; GS/OS starts
and Odyssey's title comes up; RETURN is pressed and the game starts; then the eject button goes in, the disk pops out
and goes, and Check startup device! is back.

Six materials (case, key, dark, print, glass, disk) and two textures, within the system model budget. Run from the
repo root:

    python tools/console-models/apple2gs_print.py artifacts/apple2gs
    blender -b --factory-startup --python tools/console-models/apple2gs.py -- artifacts/apple2gs godot/themes/console/models/systems/apple2gs.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apple2gs_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 22.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, key=0.5, dark=0.7, print=0.5, glass=0.15, disk=0.4)

# The keyboard's frame: x across from its middle, s up its slope from its front edge, h off it.
K = L.KEYBOARD
KB_SLOPE = math.atan2(K["heights"][1] - K["heights"][0], K["depth"])
KB_FRONT = K["at"][1] - K["depth"] / 2
KB_FRAME = Matrix.Translation((K["at"][0], KB_FRONT, K["heights"][0])) @ Matrix.Rotation(KB_SLOPE, 4, "X")
PRESS = KB_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame

# The lip's frame: x across, s up its slope from its front edge, h off it.
LIP = ((2.0, 13.0), (L.PLINTH["lip"], L.PLINTH["height"]))
LIP_SLOPE = math.atan2(LIP[1][1] - LIP[0][1], LIP[1][0] - LIP[0][0])
LIP_FRAME = Matrix.Translation((0.0, LIP[0][0], LIP[0][1])) @ Matrix.Rotation(LIP_SLOPE, 4, "X")


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


KB_TOP = atlas_uv(L.REGIONS["keyboard"], K["width"], K["depth"] + L.STRIP["depth"])


def key_uv(co):
    """The keyboard seen from above, in its slope's frame: its keys' tops, the blank column."""
    local = KB_FRAME.inverted() @ co
    return KB_TOP(local.x + K["width"] / 2, K["depth"] + L.STRIP["depth"] - local.y)


def flat_uv(co):
    """The keyboard seen from above, flat: the strip and the power key."""
    return KB_TOP(co.x - K["at"][0] + K["width"] / 2, K["depth"] + L.STRIP["depth"] - (co.y - KB_FRONT))


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def grooves_y(name, x0, x1, count, y0, y1, z_top, width, depth, mat):
    """Grooves across a top, running from front to back: count of them between x0 and x1."""
    step = (x1 - x0) / count
    return join([box(name, x0 + (k + 0.5) * step - width / 2, x0 + (k + 0.5) * step + width / 2, y0, y1,
                     z_top - depth, z_top + 5.0, mat) for k in range(count)], name)


def grooves_x(name, x_face, side, zs, y0, y1, width, depth, mat):
    """Grooves along a side face at x_face (side -1 the left, 1 the right), at heights zs."""
    a, b = (x_face - depth, x_face + 5.0) if side > 0 else (x_face - 5.0, x_face + depth)
    return join([box(name, a, b, y0, y1, z - width / 2, z + width / 2, mat) for z in zs], name)


# ---- The IIGS --------------------------------------------------------------------------------------------------------

def computer(m):
    w, d = L.WIDTH, L.DEPTH
    p = L.PLINTH
    plinth = prism_x("apple2gs", [(2.0, 0.0), (d - 2.0, 0.0), (d, 2.0), (d, p["height"]), LIP[1], LIP[0],
                                  (0.0, 11.0), (0.0, 2.0)], -w / 2, w / 2, m["case"])
    bevel(plinth, 1.5, segments=2)
    b = L.BOX
    x_face = w / 2 - b["inset"]
    body = box("box", -x_face, x_face, *b["y"], *b["z"], m["case"])
    bevel(body, 3.0, segments=2)
    g = L.TOP_GROOVES
    boolean(body, grooves_y("top", -w / 2 + g["margin"], w / 2 - g["margin"], g["count"], *g["y"], L.HEIGHT,
                            g["width"], g["depth"], m["case"]))
    s = L.SIDE_GROOVES
    for side in (-1, 1):
        boolean(body, grooves_x("side", side * x_face, side, s["z"], *s["y"], s["width"], s["depth"], m["case"]))
    seam = L.SEAM
    (ya, za), (yb, zb) = seam["front"], seam["back"]
    half = seam["width"] / 2
    for side in (-1, 1):                        # the seam between the lid and the base, rising to the back
        a, c = (x_face - seam["depth"], w / 2 + 5.0) if side > 0 else (-w / 2 - 5.0, -x_face + seam["depth"])
        boolean(body, prism_x("seam", [(ya - 5.0, za - half), (yb + 5.0, zb - half), (yb + 5.0, zb + half),
                                       (ya - 5.0, za + half)], a, c, m["case"]))
    front = atlas_uv(L.REGIONS["front"], w, b["z"][1] - b["z"][0])
    paint(body, m["print"], lambda co: front(co.x + w / 2, b["z"][1] - co.z),
          lambda c, n, name: n.y < -0.9 and abs(c.y - b["y"][0]) < 0.5)
    lx, ly = L.LIGHT
    s = (ly - LIP[0][0]) / math.cos(LIP_SLOPE)
    light = solid("light", [[LIP_FRAME @ Vector((x, t, h)) for x, t in
                             ((lx + 0.8, s - 4.0), (lx + 0.8, s + 4.0), (lx - 0.8, s + 4.0), (lx - 0.8, s - 4.0))]
                            for h in (-0.6, 0.4)], m["print"])
    return [plinth, body, painted(light, m, "green")]


# ---- The monitor -----------------------------------------------------------------------------------------------------

def monitor(m):
    M = L.MONITOR
    w, h, f = M["width"], M["height"], M["frame"]
    y0, z0 = L.MONITOR_Y, L.HEIGHT
    frame = solid("monitor", [[(x, y0 + y, z0 + z) for x, z in rounded(0.0, h / 2, w, h, 10.0, 4)] for y in (0.0, f)],
                  m["case"])
    bevel(frame, 4.0, segments=2)
    o = M["opening"]
    outer, inner = rounded(o["x"], o["z"], *o["outer"]), rounded(o["x"], o["z"], *o["inner"])
    boolean(frame, solid("opening", [[(x, y0 + y, z0 + z) for x, z in outline] for outline, y in
                                     ((outer, -10.0), (outer, 0.5), (inner, o["depth"]), (inner, o["depth"] + 1.0))],
                         m["case"]))
    face = atlas_uv(L.REGIONS["monitor"], w, h)
    paint(frame, m["print"], lambda co: face(co.x + w / 2, h - (co.z - z0)),
          lambda c, n, name: n.y < -0.9 and c.y < y0 + 0.5)
    bw, bh = M["back"]
    y1, y2, top = y0 + f - 2.0, y0 + M["depth"], z0 + 2.0 + bh
    housing = box("housing", -bw / 2, bw / 2, y1, y2, z0 + 2.0, top, m["case"])
    bevel(housing, 4.0, segments=2)
    boolean(housing, grooves_y("top", -bw / 2 + 14.0, bw / 2 - 14.0, 20, y1 + 10.0, y2 - 10.0, top, 2.6, 1.5,
                               m["case"]))
    for side in (-1, 1):
        boolean(housing, grooves_x("side", side * bw / 2, side, [z0 + 18.0 + 9.5 * k for k in range(25)],
                                   y1 + 10.0, y2 - 8.0, 2.6, 1.5, m["case"]))
    for z in M["knobs"]:                        # the knobs' recesses in the right side, and their tabs
        boolean(housing, box("recess", bw / 2 - 3.0, bw / 2 + 5.0, y1 + 12.0, y1 + 34.0, z0 + z - 3.5, z0 + z + 3.5,
                             m["dark"]))
    tabs = [box("knob", bw / 2 - 3.5, bw / 2 - 0.6, y1 + 17.0, y1 + 25.0, z0 + z - 2.6, z0 + z + 2.6, m["case"])
            for z in M["knobs"]]
    gw, gh = M["glass"]["size"]
    glass = curved("glass", gw, gh, M["glass"]["bulge"], atlas_uv(L.MEDIA_REGIONS["check"], 1.0, 1.0), m["glass"])
    glass.data.transform(Matrix.Translation((o["x"], y0 + o["depth"], z0 + o["z"])))
    return [frame, housing, glass] + tabs


def screen(m, name):
    gw, gh = L.MONITOR["glass"]["size"]
    return curved("screen_" + name, gw, gh, L.MONITOR["glass"]["bulge"],
                  atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0), m["glass"])


# ---- The drive -------------------------------------------------------------------------------------------------------

def drive(m):
    (w, d, h), dx, dy = L.DRIVE["size"], L.DRIVE["x"], L.DRIVE["y"]
    shell = box("drive", dx - w / 2, dx + w / 2, dy, dy + d, 0.0, h, m["case"])
    bevel(shell, 2.5, segments=2)
    x0, x1, z0, z1 = L.DRIVE["slot"]
    boolean(shell, box("slot", dx + x0, dx + x1, dy - 5.0, dy + 100.0, z0, z1, m["dark"]))
    boolean(shell, grooves_y("top", dx - w / 2 + 8.0, dx + w / 2 - 8.0, 10, dy + 20.0, dy + d - 8.0, h, 3.0, 1.4,
                             m["case"]))
    face = atlas_uv(L.REGIONS["drive"], w, h)
    paint(shell, m["print"], lambda co: face(co.x - (dx - w / 2), h - co.z),
          lambda c, n, name: n.y < -0.9 and c.y < dy + 0.5 and name == "case")
    return shell


def eject_button(m):
    ex0, ex1, ez0, ez1 = L.DRIVE["eject"]
    dx, dy = L.DRIVE["x"], L.DRIVE["y"]
    return box("eject", dx + ex0, dx + ex1, dy - 1.0, dy + 3.0, ez0, ez1, m["case"])


def drive_light(m):
    lx, lz = L.DRIVE["light"]
    lit = painted(box("drive_light", -2.5, 2.5, -0.4, 0.4, -0.8, 0.8, m["print"]), m, "lit")
    return lit, Vector((L.DRIVE["x"] + lx, L.DRIVE["y"], lz))


def disk(m):
    """The 3.5-inch disk, its middle at its origin, lying flat, its shutter's end towards +y (into the drive)."""
    (w, length), t = L.DISK["size"], L.DISK["thickness"]
    part = box("disk", -w / 2, w / 2, -length / 2, length / 2, -t / 2, t / 2, m["disk"])
    bevel(part, 0.6, segments=1)
    top = atlas_uv(L.MEDIA_REGIONS["disk_top"], w, length)
    bottom = atlas_uv(L.MEDIA_REGIONS["disk_bottom"], w, length)
    paint(part, m["disk"], lambda co: top(co.x + w / 2, length / 2 - co.y), lambda c, n, name: n.z > 0.9)
    paint(part, m["disk"], lambda co: bottom(w / 2 - co.x, length / 2 - co.y), lambda c, n, name: n.z < -0.9)
    x, y = L.MEDIA_SWATCHES["edge"]
    paint(part, m["disk"], lambda co: (x / L.ATLAS, 1 - y / L.ATLAS), lambda c, n, name: abs(n.z) <= 0.9)
    return part


# ---- The keyboard and mouse ------------------------------------------------------------------------------------------

def on_keyboard(name, outline, h0, h1, mat, top=None):
    """A solid from an (x, s) outline on the keyboard's slope, from h0 to h1 off it; top, if given, the outline of its
    top at h1 (a key's, tapering to it)."""
    rings = [[(x, s, h0) for x, s in outline], [(x, s, h1 - 2.5 if top else h1) for x, s in outline]]
    if top:
        rings.append([(x, s, h1) for x, s in top])
    return solid(name, [[KB_FRAME @ Vector(p) for p in ring] for ring in rings], mat)


def keyboard(m):
    """The keyboard: its wedge, the strip behind it, its keys (RETURN apart: the clip presses it)."""
    w, d = K["width"], K["depth"]
    (h0, h1), cx = K["heights"], K["at"][0]
    body = prism_x("keyboard", [(KB_FRONT, 0.0), (KB_FRONT + d, 0.0), (KB_FRONT + d, h1), (KB_FRONT, h0)], cx - w / 2,
                   cx + w / 2, m["case"])
    bevel(body, 2.0, segments=2)
    paint(body, m["print"], key_uv, lambda c, n, name: n.z > 0.9)
    (sx0, sx1), sd, sh = L.STRIP["x"], L.STRIP["depth"], L.STRIP["height"]
    strip = box("strip", cx + sx0, cx + sx1, KB_FRONT + d - 1.0, KB_FRONT + d + sd, 0.0, sh, m["case"])
    bevel(strip, 2.0, segments=2)
    paint(strip, m["print"], flat_uv, lambda c, n, name: n.z > 0.9)
    (px0, px1), (ps0, ps1) = L.POWER["x"], L.POWER["s"]
    rect = [(cx + px0 + L.GAP / 2, KB_FRONT + ps0), (cx + px1 - L.GAP / 2, KB_FRONT + ps0),
            (cx + px1 - L.GAP / 2, KB_FRONT + ps1), (cx + px0 + L.GAP / 2, KB_FRONT + ps1)]
    power = solid("power", [[(x, y, z) for x, y in outline] for outline, z in
                            ((rect, sh - 1.0), (rect, sh + 3.0), (inset(rect, L.KEY_INSET), sh + 5.0))], m["key"])
    bevel(power, 0.5, segments=1, angle=30)
    paint(power, m["print"], flat_uv, lambda c, n, name: n.z > 0.9)
    bx0, bx1 = L.kx(L.BLANK[0]) + L.GAP / 2, L.kx(L.BLANK[1]) - L.GAP / 2
    bs0, bs1 = L.ROW_S[5] + L.GAP / 2, L.ROW_S[1] + L.U - L.GAP / 2
    blank = on_keyboard("blank", [(bx0, bs0), (bx1, bs0), (bx1, bs1), (bx0, bs1)], -1.0, 2.5, m["case"])
    paint(blank, m["print"], key_uv, lambda c, n, name: n.z > 0.9)
    static, moving = [body, strip, power, blank], []
    for name, xu, row, wu, _, *rest in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu, rest[0] if rest else 1)
        outline = [(x0, s0), (x1, s0), (x1, s1), (x0, s1)]
        cap = on_keyboard(name, outline, -L.WELL, L.KEY_HEIGHT, m["key"], inset(outline, L.KEY_INSET))
        bevel(cap, 0.5, segments=1, angle=30)
        paint(cap, m["print"], key_uv, lambda c, n, _name: n.z > 0.9)
        (moving if name in ("return", "return_top") else static).append(cap)
    return static, join(moving, "return")


def mouse(m):
    w, d, h = L.MOUSE["size"]
    (mx, my), turn = L.MOUSE["at"], L.MOUSE["turn"]
    rings = [[(x, y, z) for x, y in rounded(0.0, 0.0, w * k, d * k, 12.0 * k, 4)] for k, z in
             ((0.96, 0.0), (1.0, 3.0), (1.0, h * 0.55), (0.92, h * 0.85), (0.72, h))]
    part = solid("mouse", rings, m["case"])
    for v in part.data.vertices:                # lower at its button's end (+y), domed towards its back
        v.co.z *= 0.78 - 0.22 * v.co.y / (d / 2)
    top = atlas_uv(L.REGIONS["mouse"], w, d)
    paint(part, m["print"], lambda co: top(co.x + w / 2, d / 2 - co.y), lambda c, n, name: n.z > 0.5)
    part.data.transform(Matrix.Translation((mx, my, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z"))
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 110.0          # how far in front of its seat the disk waits: wholly out of the drive


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def timeline(f):
    if f < 6 or f >= 226:
        dsk = Pose(scale=HIDDEN)
    elif f < 16:
        dsk = Pose(y=-OUT, scale=appear(f, 6, 14))
    elif f < 198:
        dsk = Pose(y=-OUT * (1 - smooth(phase(f, 16, 30))))
    elif f < 212:
        dsk = Pose(y=-40.0 * back_out(phase(f, 198, 204)))
    else:                                       # pulled clear of the slot, then up and away
        lift = ease_in(phase(f, 218, 226))
        dsk = Pose(y=-40.0 - 70.0 * smooth(phase(f, 212, 220)), z=30.0 * lift, scale=max(HIDDEN, 1 - lift))
    reading = (32 <= f < 84 or 196 <= f < 202) and (f // 3) % 4 != 3
    shown = "boot" if 36 <= f < 90 else "title" if 90 <= f < 132 else "game" if 132 <= f < 200 else None
    press = smooth(phase(f, 120, 123)) * (1 - smooth(phase(f, 126, 130)))
    push = smooth(phase(f, 192, 195)) * (1 - smooth(phase(f, 198, 202)))
    poses = {"disk": dsk, "drive_light": Pose() if reading else Pose(scale=HIDDEN),
             "return": Pose(x=PRESS.x * 2.6 * press, y=PRESS.y * 2.6 * press, z=PRESS.z * 2.6 * press),
             "eject": Pose(y=1.8 * push)}
    for name in ("boot", "title", "game"):
        poses["screen_" + name] = Pose() if shown == name else Pose(scale=HIDDEN)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "apple2gs_print.png"))
    media = bpy.data.images.load(os.path.join(images, "apple2gs_media.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    textures = dict(print=printed, glass=media, disk=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    static, enter = keyboard(m)
    whole = join(computer(m) + monitor(m) + [drive(m)] + static + [mouse(m)], "apple2gs")
    eject = eject_button(m)
    lit, lit_at = drive_light(m)
    floppy = disk(m)
    screens = {"screen_" + name: screen(m, name) for name in ("boot", "title", "game")}
    for obj in [whole, eject, enter, floppy]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("apple2gs_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    o = L.MONITOR["opening"]
    glass_front = Vector((o["x"], L.MONITOR_Y + o["depth"], L.HEIGHT + o["z"]))
    length, (x0, x1, z0, z1) = L.DISK["size"][1], L.DRIVE["slot"]
    seat = Vector((L.DRIVE["x"] + (x0 + x1) / 2, L.DRIVE["y"] + length / 2 + 4.0, (z0 + z1) / 2))
    placed = [(lit, lit_at), (floppy, seat)]
    placed += [(part, glass_front + Vector((0.0, -0.4 - 0.3 * k, 0.0))) for k, part in enumerate(screens.values())]
    for part, where in placed:
        part.parent = whole
        part.location = where
    eject.parent = whole
    enter.parent = whole
    nodes = {"disk": floppy, "drive_light": lit, "eject": eject, "return": enter, **screens}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, eject, enter, lit, floppy] + list(screens.values())
    print(f"Apple IIGS: {sum(triangles(o_.data) for o_ in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o_ in meshes for mat in o_.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
