"""The console theme's Atari ST system model (godot/themes/console/models/systems/atarist.glb): an Atari 520STFM, its
SC1224 monitor showing GEM's desktop, and its mouse.

Built in Blender from the real machines' proportions (atari_st_layout.py has the measurements, taken from
photographs). The computer is its side outline extruded across its width: the keyboard deck sloping up from the low
front edge, the band with the function keys on its face, the groove, the raised back; the keyboard's wells, the
diagonal ribs of the raised back's panel (each groove clipped to the panel), and the floppy drive's slot in its right
end are cut into it. Its 94 keys (the UK layout) stand in the wells, tapering to their printed tops; the ten function
keys are slanted blades on the band. The monitor is its front frame, the screen's opening sloping in to the curved
glass, and its body tapering behind; the mouse lies to the computer's right. The printing is two textures drawn by
atari_st_print.py: the computer seen from above (planar-mapped onto every face facing up: the key tops and legends, the
function keys, the badge, the lights), the monitor's badge, the mouse's back and swatches; and the screens and the
floppy.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end, with the drive,
towards the viewer, the top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m)
holding the set; the set holding the floppy (waiting in the drive, shrunk to nothing), the eject button, the lit drive
light, three screens over the glass (the floppy's window, black, and the title screen of a made-up game, Odyssey), and
the mouse, holding its left button. At rest the card is the set with GEM's desktop on the screen.

The `focused` clip (8 s, looping) loads a game: the floppy slides into the drive and the drive light flickers; the
mouse shuffles and double-clicks, and the floppy's window opens; it shuffles and double-clicks again on ODYSSEY.PRG,
the screen goes black while the drive reads, and Odyssey's title screen comes up. Then the desktop's back, the eject
button goes in and the floppy pops out and goes.

Seven materials (case, keys, monitor, dark, print, glass, disk) and two textures, within the system model budget. Run
from the repo root:

    python tools/console-models/atari_st_print.py artifacts/atarist
    blender -b --factory-startup --python tools/console-models/atari_st.py -- artifacts/atarist godot/themes/console/models/systems/atarist.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari_st_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end (the drive) comes towards the viewer
TILT_PITCH = 24.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.6, keys=0.55, monitor=0.6, dark=0.8, print=0.55, glass=0.2, disk=0.45)

# The deck's frame: x across, s up the slope from its front edge, h off it; and the band's.
DECK_FRAME = Matrix.Translation((0.0, L.DECK[0][0], L.DECK[0][1])) @ Matrix.Rotation(L.SLOPE, 4, "X")
BAND_FRAME = Matrix.Translation((0.0, L.BAND[0][0], L.BAND[0][1])) @ Matrix.Rotation(L.BAND_SLOPE, 4, "X")


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    """The computer seen from above."""
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(where):
    x, y = where
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def on_frame(name, frame, outline, h0, h1, mat):
    """A solid from an (x, s) outline in a sloping frame, from h0 to h1 off it."""
    return solid(name, [[frame @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def clip(poly, x0, x1, y0, y1):
    """A convex (x, y) polygon clipped to the rectangle x0..x1, y0..y1 (Sutherland and Hodgman)."""
    for axis, limit, keep_above in ((0, x0, True), (0, x1, False), (1, y0, True), (1, y1, False)):
        def inside(p):
            return p[axis] >= limit if keep_above else p[axis] <= limit
        out = []
        for i, p in enumerate(poly):
            q = poly[i - 1]
            if inside(p):
                if not inside(q):
                    t = (limit - q[axis]) / (p[axis] - q[axis])
                    out.append(tuple(q[k] + (p[k] - q[k]) * t for k in range(2)))
                out.append(p)
            elif inside(q):
                t = (limit - q[axis]) / (p[axis] - q[axis])
                out.append(tuple(q[k] + (p[k] - q[k]) * t for k in range(2)))
        poly = out
        if not poly:
            break
    return poly


def vent_grooves(m):
    """The raised back's ribbed panel: grooves running at 45 degrees (x - y constant along each), each clipped to the
    panel."""
    v = L.VENT
    (x0, x1), (y0, y1) = v["x"], v["y"]
    h = v["width"] / math.sqrt(2)                  # half a groove's extent along x, its width across it being v["width"]
    cutters = []
    c = x0 - y1
    while c < x1 - y0:
        strip = [(y0 + c - h, y0), (y0 + c + h, y0), (y1 + c + h, y1), (y1 + c - h, y1)]
        piece = clip(strip, x0, x1, y0, y1)
        if len(piece) >= 3:
            cutters.append(solid("rib", [[(x, y, z) for x, y in piece] for z in (L.HEIGHT - v["depth"], L.HEIGHT + 5.0)],
                                 m["case"]))
        c += v["pitch"] * math.sqrt(2)
    return join(cutters, "ribs")


def computer(m):
    """The 520STFM: the body cut for its wells, the groove, the ribs and the drive, its top printed."""
    body = prism_x("st", L.profile(), -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 1.8, segments=2)
    boolean(body, join([on_frame("well", DECK_FRAME, outline, -L.WELL, 14.0, m["dark"]) for outline in L.wells()],
                       "wells"))
    g0, g1, gd = L.GROOVE
    boolean(body, box("groove", -L.WIDTH / 2 - 5.0, L.WIDTH / 2 + 5.0, g0, g1, L.HEIGHT - gd, L.HEIGHT + 5.0, m["dark"]))
    boolean(body, vent_grooves(m))
    d = L.DRIVE
    edge = L.WIDTH / 2
    y0, y1, z0, z1 = d["slot"]
    boolean(body, box("slot", edge - d["depth"], edge + 5.0, y0, y1, z0, z1, m["dark"]))
    y0, y1, z0, z1 = d["bulge"]
    boolean(body, box("bulge", edge - 6.0, edge + 5.0, y0, y1, z0, z1, m["dark"]))
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.5 and name == "case")
    return body


def key_solid(name, outline, mat, m):
    """A key: from the well's floor up its sides, tapering to its printed top."""
    h = L.KEY_HEIGHT
    rings = [[(x, s, -L.WELL - 0.5) for x, s in outline], [(x, s, h - 4.5) for x, s in outline],
             [(x, s, h) for x, s in inset(outline, L.KEY_INSET)]]
    cap = solid(name, rings, mat)
    bevel(cap, 0.6, segments=1, angle=30)
    cap.data.transform(DECK_FRAME)
    paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
    return cap


def keys(m):
    """The keys in their wells, RETURN among them, and the function keys' blades on the band."""
    caps = []
    for name, xu, row, wu, _, *rest in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu, rest[0] if rest else 1)
        caps.append(key_solid(name, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], m["keys"], m))
    caps.append(key_solid("return", L.return_outline(), m["keys"], m))
    f = L.FKEYS
    for k in range(10):
        x0 = f["x0"] + k * f["width"]
        x1 = x0 + f["width"] - f["gap"]
        (s0, s1), lean = f["s"], f["lean"]
        blade = on_frame(f"f{k + 1}", BAND_FRAME, [(x0, s0), (x1, s0), (x1 + lean, s1), (x0 + lean, s1)], -1.0,
                         f["height"], m["case"])
        bevel(blade, 0.5, segments=1)
        paint(blade, m["print"], top_uv, lambda c, n, _name: n.z > 0.5)
        caps.append(blade)
    return caps


def eject_button(m):
    y0, y1, z0, z1, out = L.DRIVE["eject"]
    button = box("eject", L.WIDTH / 2 - 1.0, L.WIDTH / 2 + out, y0, y1, z0, z1, m["case"])
    bevel(button, 0.5, segments=1)
    return button


def drive_light(m):
    """The drive light lit: a bar just over the printed one on the band, its middle at its origin."""
    x, s = L.LIGHTS["drive"]
    w, d = L.LIGHTS["size"]
    lit = on_frame("drive_light", BAND_FRAME, [(x - w / 2 - 0.2, s - d / 2 - 0.2), (x + w / 2 + 0.2, s - d / 2 - 0.2),
                                               (x + w / 2 + 0.2, s + d / 2 + 0.2), (x - w / 2 - 0.2, s + d / 2 + 0.2)],
                   0.05, 0.3, m["print"])
    paint(lit, m["print"], swatch(L.PRINT_SWATCHES["lit"]), lambda c, n, name: True)
    middle = BAND_FRAME @ Vector((x, s, 0.2))
    lit.data.transform(Matrix.Translation(-middle))
    return lit, middle


# ---- The monitor -----------------------------------------------------------------------------------------------------

def monitor(m):
    """The SC1224, its front's middle at the origin, facing -y: the frame and its opening, the body tapering behind,
    the glass, the badge and the light. Moved to its place."""
    M = L.MONITOR
    w, h, fd = M["width"], M["height"], M["frame"]
    b = M["body"]
    back_w, back_h = b["back"]
    front = rounded(0.0, h / 2, w, h, 14.0, 4)
    inner = rounded(0.0, h / 2, w - 24.0, h - 20.0, 12.0, 4)
    rear = rounded(0.0, b["lift"] + back_h / 2, back_w, back_h, 12.0, 4)
    whole = solid("monitor", [[(x, y, z) for x, z in outline] for outline, y in
                              ((front, 0.0), (front, fd), (inner, fd), (rear, b["depth"]))], m["monitor"])
    bevel(whole, 2.0, segments=2)
    o = M["opening"]
    outer, inner = rounded(0.0, o["z"], *o["outer"]), rounded(0.0, o["z"], *o["inner"])
    boolean(whole, solid("opening", [[(x, y, z) for x, z in outline] for outline, y in
                                     ((outer, -10.0), (outer, 0.5), (inner, o["depth"]), (inner, o["depth"] + 1.0))],
                         m["monitor"]))

    gw, gh = M["glass"]["size"]
    glass = curved("glass", gw, gh, M["glass"]["bulge"], atlas_uv(L.MEDIA_REGIONS["desktop"], 1.0, 1.0), m["glass"])
    glass.data.transform(Matrix.Translation((0.0, o["depth"], o["z"])))

    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    (x0, x1), (z0, z1) = M["badge"]["x"], M["badge"]["z"]
    corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]                  # wound to face -y
    face = bm.faces.new([bm.verts.new((x, -0.15, z)) for x, z in corners])
    badge_uv = atlas_uv(L.PRINT_REGIONS["badge"], x1 - x0, z1 - z0)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = badge_uv(x - x0, z1 - z)
    badge = new_object("badge", bm, m["print"])
    lx, lz = M["light"]
    light = box("light", lx - 4.0, lx + 4.0, -0.6, 0.5, lz - 1.0, lz + 1.0, m["print"])
    paint(light, m["print"], swatch(L.PRINT_SWATCHES["green"]), lambda c, n, name: True)

    parts = [whole, glass, badge, light]
    at = Matrix.Translation((M["at"][0], M["at"][1], 0.0))
    for obj in parts:
        obj.data.transform(at)
    return parts


def screen(m, name, uv):
    """A screen over the glass, its middle at its origin (the clip opens and closes it about there)."""
    gw, gh = L.MONITOR["glass"]["size"]
    return curved(name, gw, gh, L.MONITOR["glass"]["bulge"], uv, m["glass"])


# ---- The mouse and the floppy ----------------------------------------------------------------------------------------

def mouse(m):
    """The mouse, its middle at its origin, its buttons towards +y: the body with the right button, and the left
    button apart (and where it sits)."""
    w, d, h = L.MOUSE["size"]
    b = L.MOUSE["buttons"]
    body = box("mouse", -w / 2, w / 2, -d / 2, d / 2, 0.0, h - 4.0, m["case"])
    right = box("right_button", 0.6, w / 2, d / 2 - b, d / 2, h - 6.0, h, m["case"])
    body = join([body, right], "mouse")
    bevel(body, 2.5, segments=2)
    top = atlas_uv(L.PRINT_REGIONS["mouse"], w, d)
    paint(body, m["print"], lambda co: top(co.x + w / 2, d / 2 - co.y), lambda c, n, name: n.z > 0.9)
    left = box("mouse_button", -w / 2, -0.6, -b / 2, b / 2, -2.0, 4.0, m["case"])
    bevel(left, 1.2, segments=2)
    paint(left, m["print"], lambda co: top(co.x + w / 2, b / 2 - co.y), lambda c, n, name: n.z > 0.9)
    return body, left, Vector((0.0, d / 2 - b / 2, h - 4.0))


def disk(m):
    """The floppy, its middle at its origin, its shutter's edge towards -x (into the drive), its label up."""
    l, w, t = L.DISK["length"], L.DISK["width"], L.DISK["thickness"]
    shell = box("floppy", -l / 2, l / 2, -w / 2, w / 2, -t / 2, t / 2, m["disk"])
    bevel(shell, 0.8, segments=2)
    top, bottom = atlas_uv(L.MEDIA_REGIONS["disk_top"], l, w), atlas_uv(L.MEDIA_REGIONS["disk_bottom"], l, w)
    paint(shell, m["disk"], lambda co: top(co.x + l / 2, w / 2 - co.y), lambda c, n, name: n.z > 0.9)
    paint(shell, m["disk"], lambda co: bottom(co.x + l / 2, w / 2 + co.y), lambda c, n, name: n.z < -0.9)
    paint(shell, m["disk"], swatch(L.MEDIA_SWATCHES["edge"]), lambda c, n, name: abs(n.z) <= 0.9)
    return shell


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def flat(v):
    """A screen squeezed to v of its height (switching on or off)."""
    return Pose(axes=(1.0, 1.0, max(HIDDEN, v)))


def tap(f, f0, hold=1):
    """A click at f0: down in two frames, held, back up in two."""
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 4 + hold)))


CLICKS = (58, 63, 92, 97)


def timeline(f):
    out = L.WIDTH / 2 + 24.0 + L.DISK["length"] / 2 - L.SEAT[0]    # the floppy's middle beside the drive

    # The floppy: appears beside the drive, slides in; later pops out and goes.
    if f < 8 or f >= 232:
        floppy = Pose(scale=HIDDEN)
    elif f < 18:
        floppy = Pose(x=out, scale=appear(f, 8, 16))
    elif f < 214:
        floppy = Pose(x=out * (1 - smooth(phase(f, 18, 34))))
    elif f < 222:
        floppy = Pose(x=40.0 * back_out(phase(f, 214, 220)))
    else:
        t = ease_in(phase(f, 222, 232))
        floppy = Pose(x=40.0 + 80.0 * t, z=24.0 * t, scale=max(HIDDEN, 1 - ease_in(phase(f, 226, 232))))

    # The drive light, while the drive reads: on, with a short blink every few frames.
    reading = 34 <= f < 48 or 70 <= f < 78 or 104 <= f < 150 or 214 <= f < 218
    light = Pose() if reading and (f // 4) % 4 != 3 else Pose(scale=HIDDEN)

    # The mouse: shuffles to the floppy's window and double-clicks, shuffles on and double-clicks ODYSSEY.PRG.
    shuffle_a = smooth(phase(f, 44, 56))
    shuffle_b = smooth(phase(f, 80, 90))
    back = smooth(phase(f, 196, 210))
    mouse = Pose(x=(7.0 * shuffle_a - 4.0 * shuffle_b) * (1 - back), y=(6.0 * shuffle_a - 5.0 * shuffle_b) * (1 - back))
    button = Pose(z=-1.6 * max(tap(f, f0) for f0 in CLICKS))

    # The screens: the window opens after the first double-click; black while the game loads; the title opening.
    window = Pose() if 66 <= f < 102 else Pose(scale=HIDDEN)
    black = Pose() if 102 <= f < 150 else Pose(scale=HIDDEN)
    if f < 148 or f >= 206:
        title = Pose(scale=HIDDEN)
    elif f < 154:
        title = flat(0.02 + 0.98 * ease_out(phase(f, 148, 154)))
    elif f < 200:
        title = Pose()
    else:
        title = flat(1 - ease_in(phase(f, 200, 206)))

    eject = 1.4 * smooth(phase(f, 210, 213)) * (1 - smooth(phase(f, 216, 220)))
    return {"floppy": floppy, "drive_light": light, "mouse": mouse, "mouse_button": button, "screen_window": window,
            "screen_black": black, "screen_title": title, "eject": Pose(x=-eject)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "atari_st_print.png"))
    media = bpy.data.images.load(os.path.join(images, "atari_st_media.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", glass="#FFFFFF", disk="#FFFFFF")
    textures = dict(print=printed, glass=media, disk=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    whole = join([computer(m)] + keys(m) + monitor(m), "atarist")
    eject = eject_button(m)
    lit, lit_at = drive_light(m)
    floppy = disk(m)
    rodent, button, button_at = mouse(m)
    unlit = swatch(L.MEDIA_SWATCHES["black"])(None)
    screens = {"screen_window": screen(m, "screen_window", atlas_uv(L.MEDIA_REGIONS["window"], 1.0, 1.0)),
               "screen_black": screen(m, "screen_black", lambda a, b: unlit),
               "screen_title": screen(m, "screen_title", atlas_uv(L.MEDIA_REGIONS["title"], 1.0, 1.0))}
    for obj in [whole, eject, floppy, rodent, button]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("atarist_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    M, o = L.MONITOR, L.MONITOR["opening"]
    glass_front = Vector((M["at"][0], M["at"][1] + o["depth"], o["z"]))
    mx, my = L.MOUSE["at"]
    placed = [(floppy, Vector(L.SEAT)), (lit, lit_at), (rodent, Vector((mx, my, 0.0)))]
    placed += [(part, glass_front + Vector((0.0, -0.5 - 0.4 * k, 0.0))) for k, part in enumerate(screens.values())]
    for part, where in placed:
        part.parent = whole
        part.location = where
    rodent.rotation_euler = (0.0, 0.0, math.radians(L.MOUSE["spin"]))
    eject.parent = whole
    button.parent = rodent
    button.location = button_at
    nodes = {"floppy": floppy, "drive_light": lit, "mouse": rodent, "mouse_button": button, "eject": eject, **screens}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((mx, my, 0.0)) @ Matrix.Rotation(math.radians(L.MOUSE["spin"]), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in rodent.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, eject, lit, floppy, rodent, button] + list(screens.values())
    print(f"Atari ST: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
