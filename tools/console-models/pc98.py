"""The console theme's PC-98 system model (godot/themes/console/models/systems/pc98.glb): an NEC PC-9801VM, its colour
monitor on it, its keyboard in front.

Built in Blender from the real machines' proportions (pc98_layout.py has the measurements, taken from photographs).
The system unit is a box on its feet, its edges rounded, its front printed; the two drives' bezels stand on its front,
their slots cut through them, each with its turning lever, POWER below them. The monitor stands on it: its front frame,
the screen's opening sloping in to the curved glass, its housing behind, the three knobs down its right. The keyboard
is a wedge, its keys standing on it, tapering to their printed tops. The printing is two textures drawn by
pc98_print.py: the keyboard's top, the system unit's and the monitor's fronts and swatches; and the screens and the
floppy.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the 5.25-inch floppy (waiting in drive 1, shrunk to nothing), drive 1's lever and lit light, POWER, three
screens over the glass (the memory check, the title of a made-up game, Odyssey, and a moment of its play), shrunk to
nothing, and RETURN.

The `focused` clip (8 s, looping) boots a game from a floppy: the floppy slides into drive 1 and its lever turns down
to shut it; POWER, and the light flickers while the memory check and then the title come up; RETURN is pressed and
the game plays.
Then the lever turns back up, the floppy pops out and goes, and the screen is dark again.

Seven materials (case, key, key_dark, dark, print, glass, disk) and two textures, within the system model budget.
Run from the repo root:

    python tools/console-models/pc98_print.py artifacts/pc98
    blender -b --factory-startup --python tools/console-models/pc98.py -- artifacts/pc98 godot/themes/console/models/systems/pc98.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc98_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 20.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, key=0.5, key_dark=0.5, dark=0.7, print=0.5, glass=0.15, disk=0.4)
K = L.KEYBOARD
KB_SLOPE = math.atan2(K["heights"][1] - K["heights"][0], K["depth"])
KB_FRONT = K["at"][1] - K["depth"] / 2
KB_FRAME = Matrix.Translation((K["at"][0], KB_FRONT, K["heights"][0])) @ Matrix.Rotation(KB_SLOPE, 4, "X")
PRESS = KB_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame
M = L.MONITOR
MON_Z = L.HEIGHT + M["stand"]                           # the monitor's bezel's foot


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


KB_TOP = atlas_uv(L.REGIONS["keyboard"], K["width"], K["depth"])
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.HEIGHT - L.FEET)


def key_uv(co):
    """The keyboard seen from above, in its slope's frame."""
    local = KB_FRAME.inverted() @ co
    return KB_TOP(local.x + K["width"] / 2, K["depth"] - local.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.HEIGHT - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


# ---- The system unit -------------------------------------------------------------------------------------------------

def system_unit(m):
    """The system unit: its box on its feet, its front printed; the drives' bezels with their slots, drive 2's lever."""
    w, d = L.WIDTH, L.DEPTH
    shell = box("pc98", -w / 2, w / 2, 0.0, d, L.FEET, L.HEIGHT, m["case"])
    bevel(shell, 3.0, segments=2)
    paint(shell, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < 1.0)
    feet = [box("foot", x - 15.0, x + 15.0, y - 12.0, y + 12.0, 0.0, L.FEET + 1.0, m["dark"])
            for x in (-170.0, 170.0) for y in (30.0, d - 30.0)]
    parts = [shell] + feet
    (dx0, dx1) = L.DRIVES["x"]
    mx = (dx0 + dx1) / 2
    sx0, sx1, sz0, sz1 = L.DRIVES["slot"]
    for k, (z0, z1) in enumerate(L.DRIVES["z"]):
        bezel = box("bezel", dx0, dx1, -1.5, 1.0, z0, z1, m["case"])
        bevel(bezel, 0.8, segments=1)
        paint(bezel, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
        boolean(bezel, box("slot", mx + sx0, mx + sx1, -5.0, 5.0, z0 + sz0, z0 + sz1, m["dark"]))
        parts.append(bezel)
        if k == 1:
            lever, where = drive_lever(m, z0)
            lever.data.transform(Matrix.Translation(where))
            parts.append(lever)
    boolean(shell, box("slot_back", mx + sx0, mx + sx1, -5.0, 60.0, L.DRIVES["z"][0][0] + sz0,
                       L.DRIVES["z"][0][0] + sz1, m["dark"]))
    return parts


def drive_lever(m, z0):
    """A drive's turning lever, its pivot at its origin, lying across the slot to the left (open)."""
    px, pz, length, width, out = L.DRIVES["lever"]
    mx = sum(L.DRIVES["x"]) / 2
    part = box("lever", -length + width / 2, width / 2, -out, -1.0, -width / 2, width / 2, m["print"])
    bevel(part, 1.2, segments=2)
    painted(part, m, "lever")
    return part, Vector((mx + px, 0.0, z0 + pz))


def drive_light(m):
    lx, lz = L.DRIVES["light"]
    mx = sum(L.DRIVES["x"]) / 2
    z0 = L.DRIVES["z"][0][0]
    part = painted(box("drive_light", -2.2, 2.2, -0.4, 0.3, -1.4, 1.4, m["print"]), m, "red")
    return part, Vector((mx + lx, -1.5, z0 + lz))


def power(m):
    (x0, x1), (z0, z1) = L.POWER["x"], L.POWER["z"]
    part = box("power", x0, x1, -L.POWER["out"], 1.0, z0, z1, m["print"])
    bevel(part, 0.8, segments=1)
    painted(part, m, "brown")
    return part


def disk(m):
    """The 5.25-inch floppy, its middle at its origin, lying flat, the end that goes in first towards +y."""
    s, t = L.DISK["size"], L.DISK["thickness"]
    part = box("disk", -s / 2, s / 2, -s / 2, s / 2, -t / 2, t / 2, m["disk"])
    top = atlas_uv(L.MEDIA_REGIONS["disk_top"], s, s, )
    bottom = atlas_uv(L.MEDIA_REGIONS["disk_bottom"], s, s)
    paint(part, m["disk"], lambda co: top(co.x + s / 2, s / 2 - co.y), lambda c, n, name: n.z > 0.9)
    paint(part, m["disk"], lambda co: bottom(s / 2 - co.x, s / 2 - co.y), lambda c, n, name: n.z < -0.9)
    x, y = L.MEDIA_SWATCHES["edge"]
    paint(part, m["disk"], lambda co: (x / L.ATLAS, 1 - y / L.ATLAS), lambda c, n, name: abs(n.z) <= 0.9)
    return part


# ---- The monitor -----------------------------------------------------------------------------------------------------

def monitor(m):
    w, h, f = M["width"], M["height"], M["frame"]
    y0, z0 = M["y"], MON_Z
    stand = box("stand", -110.0, 110.0, y0 + 20.0, y0 + 200.0, L.HEIGHT - 1.0, z0 + 2.0, m["case"])
    bevel(stand, 3.0, segments=2)
    frame = solid("monitor", [[(x, y0 + y, z0 + z) for x, z in rounded(0.0, h / 2, w, h, 12.0, 4)] for y in (0.0, f)],
                  m["case"])
    bevel(frame, 4.0, segments=2)
    o = M["opening"]
    outer, inner = rounded(o["x"], o["z"], *o["outer"]), rounded(o["x"], o["z"], *o["inner"])
    boolean(frame, solid("opening", [[(x, y0 + y, z0 + z) for x, z in outline] for outline, y in
                                     ((outer, -10.0), (outer, 0.5), (inner, o["depth"]), (inner, o["depth"] + 1.0))],
                         m["dark"]))                    # the opening's walls are the black bezel's
    face = atlas_uv(L.REGIONS["bezel"], w, h)
    paint(frame, m["print"], lambda co: face(co.x + w / 2, h - (co.z - z0)), lambda c, n, name: n.y < -0.9 and
          c.y < y0 + 0.5)
    bw, bh = M["back"]
    y1, y2 = y0 + f - 2.0, y0 + M["depth"]
    housing = solid("housing", [[(x, y, z0 + z) for x, z in rounded(0.0, h / 2, bw * k, bh * k, 20.0 * k, 4)] for k, y
                                in ((1.0, y1), (0.96, y1 + 100.0), (0.62, y2))], m["case"])
    knobs = []
    for x, z in M["knobs"]:
        r = M["knob_r"]
        knob = solid("knob", [[(x + r * k * math.cos(2 * math.pi * j / 24), y0 + y, z0 + z + r * k *
                                math.sin(2 * math.pi * j / 24)) for j in range(24)] for k, y in
                              ((1.0, 1.0), (1.0, -8.0), (0.85, -10.0))], m["dark"])
        knobs.append(knob)
    gw, gh = M["glass"]
    glass = curved("glass", gw, gh, M["bulge"], lambda a, b: swatch_media("black"), m["glass"])
    glass.data.transform(Matrix.Translation((o["x"], y0 + o["depth"], z0 + o["z"])))
    return [stand, frame, housing, glass] + knobs


def swatch_media(name):
    x, y = L.MEDIA_SWATCHES[name]
    return (x / L.ATLAS, 1 - y / L.ATLAS)


def screen(m, name):
    gw, gh = M["glass"]
    return curved("screen_" + name, gw, gh, M["bulge"], atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0), m["glass"])


# ---- The keyboard ----------------------------------------------------------------------------------------------------

def on_keyboard(name, outline, h0, h1, mat, top=None):
    """A solid from an (x, s) outline on the keyboard's slope, from h0 to h1 off it; top, if given, the outline of its
    top at h1 (a key's, tapering to it)."""
    rings = [[(x, s, h0) for x, s in outline], [(x, s, h1 - 2.5 if top else h1) for x, s in outline]]
    if top:
        rings.append([(x, s, h1) for x, s in top])
    return solid(name, [[KB_FRAME @ Vector(p) for p in ring] for ring in rings], mat)


def keyboard(m):
    """The keyboard: its wedge, its keys (RETURN apart: the clip presses it)."""
    w, d = K["width"], K["depth"]
    (h0, h1), cx = K["heights"], K["at"][0]
    body = prism_x("keyboard", [(KB_FRONT, 0.0), (KB_FRONT + d, 0.0), (KB_FRONT + d, h1), (KB_FRONT, h0)], cx - w / 2,
                   cx + w / 2, m["case"])
    bevel(body, 2.5, segments=2)
    paint(body, m["print"], key_uv, lambda c, n, name: n.z > 0.9)
    static, enter = [body], None
    for name, x_px, w_px, row, _, *rest in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(x_px, w_px, row, rest[0] if rest else 1)
        outline = [(x0, s0), (x1, s0), (x1, s1), (x0, s1)]
        mat = m["key_dark"] if name in L.DARK_KEYS else m["key"]
        cap = on_keyboard(name, outline, -L.WELL, L.KEY_HEIGHT, mat, inset(outline, L.KEY_INSET))
        bevel(cap, 0.5, segments=1, angle=30)
        paint(cap, m["print"], key_uv, lambda c, n, _name: n.z > 0.9)
        if name == "return":
            enter = cap
        else:
            static.append(cap)
    return static, enter


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 150.0          # how far in front of its seat the floppy waits: wholly out of the drive


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    if f < 6 or f >= 226:
        dsk = Pose(scale=HIDDEN)
    elif f < 16:
        dsk = Pose(y=-OUT, scale=appear(f, 6, 14))
    elif f < 198:
        dsk = Pose(y=-OUT * (1 - smooth(phase(f, 16, 30))))
    elif f < 212:
        dsk = Pose(y=-50.0 * back_out(phase(f, 198, 204)))
    else:
        lift = ease_in(phase(f, 216, 226))
        dsk = Pose(y=-50.0 - 80.0 * smooth(phase(f, 210, 218)), z=26.0 * lift, scale=max(HIDDEN, 1 - lift))
    shut = smooth(phase(f, 32, 38)) * (1 - smooth(phase(f, 190, 196)))
    reading = (40 <= f < 90 or 182 <= f < 188) and (f // 3) % 4 != 3
    shown = "memory" if 44 <= f < 76 else "title" if 76 <= f < 116 else "game" if 116 <= f < 196 else None
    press = smooth(phase(f, 108, 111)) * (1 - smooth(phase(f, 114, 118)))
    poses = {"disk": dsk, "lever": Pose(roll=-90.0 * shut), "drive_light": Pose() if reading else Pose(scale=HIDDEN),
             "power": Pose(y=2.0 * tap(f, 40)),
             "return": Pose(x=PRESS.x * 2.6 * press, y=PRESS.y * 2.6 * press, z=PRESS.z * 2.6 * press)}
    for name in ("memory", "title", "game"):
        poses["screen_" + name] = Pose() if shown == name else Pose(scale=HIDDEN)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "pc98_print.png"))
    media = bpy.data.images.load(os.path.join(images, "pc98_media.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", key=L.COLOURS["key_light"])
    textures = dict(print=printed, glass=media, disk=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    static, enter = keyboard(m)
    whole = join(system_unit(m) + monitor(m) + static, "pc98")
    lever, lever_at = drive_lever(m, L.DRIVES["z"][0][0])
    lit, lit_at = drive_light(m)
    button = power(m)
    floppy = disk(m)
    screens = {"screen_" + name: screen(m, name) for name in ("memory", "title", "game")}
    for obj in [whole, lever, button, floppy, enter]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("pc98_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    o = M["opening"]
    glass_front = Vector((o["x"], M["y"] + o["depth"], MON_Z + o["z"]))
    sx0, sx1, sz0, sz1 = L.DRIVES["slot"]
    mx = sum(L.DRIVES["x"]) / 2
    seat = Vector((mx + (sx0 + sx1) / 2, L.DISK["size"] / 2 + 4.0, L.DRIVES["z"][0][0] + (sz0 + sz1) / 2))
    placed = [(lever, lever_at), (lit, lit_at), (floppy, seat)]
    placed += [(part, glass_front + Vector((0.0, -0.4 - 0.3 * k, 0.0))) for k, part in enumerate(screens.values())]
    for part, where in placed:
        part.parent = whole
        part.location = where
    for part in (button, enter):
        part.parent = whole
    nodes = {"disk": floppy, "lever": lever, "drive_light": lit, "power": button, "return": enter, **screens}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, lever, lit, button, floppy, enter] + list(screens.values())
    print(f"PC-98: {sum(triangles(o_.data) for o_ in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o_ in meshes for mat in o_.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
