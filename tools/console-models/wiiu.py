"""The console theme's Wii U system model (godot/themes/console/models/systems/wiiu.glb): the Wii U in black, lying down,
and its GamePad standing in its cradle in front of it, the Wii U Menu on its screen.

Built in Blender from the real machines' proportions (wiiu_layout.py has the measurements). The console is its
rounded section extruded from front to back, the disc slot and the grilles cut into it, the matte panel along its top,
EJECT, POWER and SYNC standing on its front. The GamePad is its rounded outline extruded to its thickness, its edges
rounded, the d-pad, the buttons and the sticks standing on its face, the screen a glass over its bezel. The cradle is
a black base, a lip holding the GamePad's foot and a rest behind it. The printing is one texture drawn by
wiiu_print.py: the GamePad's face and the console's front (planar-mapped onto their faces and the buttons' tops), the
GamePad's screens, the disc's label, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the disc (waiting in the console, shrunk to nothing), EJECT, and the GamePad; the GamePad holding its sticks, A
and B, and three screens over its glass (the menu with the disc's tile chosen, Odyssey's title, a moment of its play),
shrunk to nothing.

The `focused` clip (8 s, looping) plays a disc: the disc slides into the console and its tile comes up on the menu; A
starts it, the title comes up, A again and the game is played on the sticks, A and B. Then EJECT, the disc slides out
and goes, and the menu is back.

Five materials (case, key, cradle, glass, print) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/wiiu_print.py artifacts/wiiu
    blender -b --factory-startup --python tools/console-models/wiiu.py -- artifacts/wiiu godot/themes/console/models/systems/wiiu.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiiu_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 16.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.22, key=0.4, cradle=0.6, glass=0.1, print=0.35)

(CW, CD, CH), (CX, CY) = L.CONSOLE["size"], L.CONSOLE["at"]
PW, PH = L.PAD["size"]
LEAN = math.radians(L.PAD["lean"])
# The GamePad's frame: its middle at the origin, u across (x), w back from its face (y), v up (z); its foot's front
# edge on PAD["at"], leaning back.
PAD_FRAME = (Matrix.Translation(L.PAD["at"]) @ Matrix.Rotation(-LEAN, 4, "X")
             @ Matrix.Translation((0.0, 0.0, PH / 2)))


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


PAD_FACE = atlas_uv(L.REGIONS["pad"], PW, PH)


def pad_uv(co):
    """The GamePad's face seen from in front, in its own frame."""
    return PAD_FACE(co.x + PW / 2, PH / 2 - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def cylinder(name, r, z0, z1, mat, segments=24):
    """A cylinder about the y axis (pointing out of a face towards -y), from y = z0 to z1."""
    ring = [(r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments)) for k in
            range(segments)]
    return solid(name, [[(x, y, z) for x, z in ring] for y in (z0, z1)], mat)


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The console: its section extruded front to back, the slot and the grilles cut into it, the matte panel on its
    top, its front printed; EJECT apart (the clip presses it)."""
    section = rounded(CX + CW / 2, CH / 2, CW, CH, L.CONSOLE["corner"], 6)
    shell = solid("wiiu", [[(x, y, z) for x, z in section] for y in (CY, CY + CD)], m["case"])
    bevel(shell, 1.6, segments=2)
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    boolean(shell, box("slot", CX + sx0, CX + sx1, CY - 5.0, CY + 70.0, sz0, sz1, m["key"]))
    cols, rows = L.GRILLE_GRID
    for g in L.GRILLES:
        (y0, y1), (z0, z1) = g["y"], g["z"]
        dy, dz = (y1 - y0) / cols, (z1 - z0) / rows
        boolean(shell, join([box("grille", CX + CW - 1.5, CX + CW + 5.0, CY + y0 + i * dy + 1.0, CY + y0 + (i + 1) * dy - 1.0,
                                 z0 + j * dz + 1.0, z0 + (j + 1) * dz - 1.0, m["key"])
                             for i in range(cols) for j in range(rows)], "grilles"))
    face = atlas_uv(L.REGIONS["front"], CW, CH)
    paint(shell, m["print"], lambda co: face(co.x - CX, CH - co.z),
          lambda c, n, name: n.y < -0.9 and c.y < CY + 0.5 and name == "case")
    c = L.CONSOLE["corner"]
    panel = box("panel", CX + c + 1.0, CX + CW - c - 1.0, CY + L.CAP, CY + CD - L.CAP, CH - 0.5, CH + 0.25, m["print"])
    paint(panel, m["print"], swatch("matte"), lambda c_, n, name: True)
    parts = [shell, panel]
    r = L.FRONT_BUTTONS["r"]
    px, pz = L.FRONT_BUTTONS["power"]
    power = cylinder("power", r, CY - 1.2, CY + 1.0, m["key"])
    power.data.transform(Matrix.Translation((CX + px, 0.0, pz)))
    sx, sz = L.SYNC
    sync = cylinder("sync", 2.0, CY - 0.8, CY + 1.0, m["key"], 16)
    sync.data.transform(Matrix.Translation((CX + sx, 0.0, sz)))
    for part in (power, sync):
        bevel(part, 0.4, segments=1)
        parts.append(part)
    ex, ez = L.FRONT_BUTTONS["eject"]
    eject = cylinder("eject", r, CY - 1.2, CY + 1.0, m["key"])
    bevel(eject, 0.4, segments=1)
    eject.data.transform(Matrix.Translation((CX + ex, 0.0, ez)))
    return parts, eject


def cradle(m):
    """The cradle: its base, the lip holding the GamePad's foot, the rest behind it along the GamePad's back."""
    (w, d), h = L.CRADLE["size"], L.CRADLE["base"]
    px, _, pz = L.PAD["at"]
    t = L.PAD["thickness"]
    base = box("cradle", px - w / 2, px + w / 2, -22.0, d - 22.0, 0.0, h, m["cradle"])
    bevel(base, 2.0, segments=2)
    lip = box("lip", px - w / 2 + 10.0, px + w / 2 - 10.0, -9.0, -1.0, 0.0, pz + 4.0, m["cradle"])
    bevel(lip, 1.5, segments=2)
    c, s = math.cos(LEAN), math.sin(LEAN)
    foot = (t * c + 0.5, pz - t * s)                         # the GamePad's back at its foot, and up it to v = 40
    top = (foot[0] + 40.0 * s, foot[1] + 40.0 * c)
    rest = prism_x("rest", [(foot[0], h - 1.0), (d - 22.0, h - 1.0), (d - 22.0, top[1] - 16.0), (top[0] + 2.0, top[1]),
                            top], px - w / 2 + 18.0, px + w / 2 - 18.0, m["cradle"])
    bevel(rest, 1.5, segments=2)
    return [base, lip, rest]


def disc(m):
    """The disc, its middle at its origin, lying flat: a ring, its label on its top."""
    ro, ri, t = L.DISC["diameter"] / 2, L.DISC["hole"] / 2, L.DISC["thickness"]
    n = 64
    bm = bmesh.new()
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), z)) for k in range(n)]
             for r, z in ((ro, -t / 2), (ro, t / 2), (ri, t / 2), (ri, -t / 2))]
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new([a[k], a[j], b[j], b[k]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    part = new_object("disc", bm, m["print"])
    d = L.DISC["diameter"]
    top = atlas_uv(L.REGIONS["disc"], d, d)
    paint(part, m["print"], lambda co: top(co.x + d / 2, d / 2 - co.y), lambda c, n_, name: n_.z > 0.9)
    paint(part, m["print"], swatch("silver"), lambda c, n_, name: n_.z <= 0.9)
    return part


# ---- The GamePad -----------------------------------------------------------------------------------------------------

def gamepad(m):
    """The GamePad in its own frame: its body, the d-pad and the buttons on its face, the screen's glass; the sticks,
    A and B apart (the clip plays them), each its foot's middle at its origin."""
    outline = rounded(0.0, 0.0, PW, PH, L.PAD["corner"], 8)
    body = solid("gamepad", [[(x, w, z) for x, z in outline] for w in (0.0, L.PAD["thickness"])], m["case"])
    bevel(body, 6.0, segments=3)
    paint(body, m["print"], pad_uv, lambda c, n, name: n.y < -0.9 and c.y < 0.5)
    parts = [body]
    (du, dv), size, arm, dh = L.DPAD["at"], L.DPAD["size"], L.DPAD["arm"], L.DPAD["height"]
    cross = join([box("dpad", du - size / 2, du + size / 2, -dh, 1.0, dv - arm / 2, dv + arm / 2, m["key"]),
                  box("dpad_v", du - arm / 2, du + arm / 2, -dh, 1.0, dv - size / 2, dv + size / 2, m["key"])], "dpad")
    parts.append(cross)
    (au, av), sp, r = L.ABXY["at"], L.ABXY["spacing"], L.ABXY["r"]
    s = L.SMALL
    small = [(au, av + sp, r), (au - sp, av, r)] + [(s[k][0], s[k][1], s["r"]) for k in ("start", "select", "tv", "power")]
    small.append((s["home"][0], s["home"][1], s["home_r"]))
    for k, (u, v, rr) in enumerate(small):
        part = cylinder(f"key_{k}", rr, -L.ABXY["height"] if rr == r else -s["height"], 1.0, m["key"])
        bevel(part, 0.6, segments=1)
        part.data.transform(Matrix.Translation((u, 0.0, v)))
        parts.append(part)
    for part in parts[1:]:
        paint(part, m["print"], pad_uv, lambda c, n, name: n.y < -0.9)
    (sw, sh), (su, sv) = L.SCREEN["size"], L.SCREEN["at"]
    glass = curved("glass", sw, sh, 0.0, atlas_uv(L.REGIONS["menu"], 1.0, 1.0), m["glass"], nu=1, nv=1)
    glass.data.transform(Matrix.Translation((su, -0.2, sv)))
    parts.append(glass)
    shell = join(parts, "gamepad")

    moving = {}
    for name, (u, v) in (("a", (au + sp, av)), ("b", (au, av - sp))):
        part = cylinder(name, r, -L.ABXY["height"], 1.0, m["key"])
        bevel(part, 0.6, segments=1)
        part.data.transform(Matrix.Translation((u, 0.0, v)))
        paint(part, m["print"], pad_uv, lambda c, n, _name: n.y < -0.9)
        part.data.transform(Matrix.Translation((-u, 0.0, -v)))
        moving[name] = (part, Vector((u, 0.0, v)))
    st = L.STICKS
    for name in ("left", "right"):
        u, v = st[name]
        stem = cylinder("stem", 3.2, -st["height"] + 2.0, 2.0, m["key"], 16)
        cap = cylinder("cap", st["r"], -st["height"], -st["height"] + 3.4, m["key"], 28)
        bevel(cap, 1.2, segments=2)
        part = join([stem, cap], name + "_stick")
        moving[name + "_stick"] = (part, Vector((u, 0.0, v)))
    screens = {}
    for k, name in enumerate(("menu_disc", "title", "game")):
        screens[name] = (curved(name, sw, sh, 0.0, atlas_uv(L.REGIONS[name], 1.0, 1.0), m["glass"], nu=1, nv=1),
                         Vector((su, -0.4 - 0.2 * k, sv)))
    return shell, moving, screens


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 130.0          # how far in front of its seat the disc waits: wholly out of the console


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    if f < 8 or f >= 222:
        dsk = Pose(scale=HIDDEN)
    elif f < 20:
        dsk = Pose(y=-OUT, scale=appear(f, 8, 16))
    elif f < 196:
        dsk = Pose(y=-OUT * (1 - smooth(phase(f, 20, 34))))
    elif f < 208:
        dsk = Pose(y=-46.0 * back_out(phase(f, 196, 202)))
    else:
        lift = ease_in(phase(f, 212, 222))
        dsk = Pose(y=-46.0 - 80.0 * smooth(phase(f, 206, 216)), z=24.0 * lift, scale=max(HIDDEN, 1 - lift))
    shown = ("menu_disc" if 36 <= f < 68 or 188 <= f < 196 else "title" if 68 <= f < 98 else
             "game" if 98 <= f < 188 else None)
    poses = {"disc": dsk, "eject": Pose(y=1.0 * tap(f, 190))}
    for name in ("menu_disc", "title", "game"):
        poses[name] = Pose() if shown == name else Pose(scale=HIDDEN)
    poses["a"] = Pose(y=1.8 * max(tap(f, f0) for f0 in (60, 92, 122, 164)))
    poses["b"] = Pose(y=1.8 * max(tap(f, f0) for f0 in (140, 176)))
    t = phase(f, 104, 184)
    k = math.sin(math.pi * t)
    poses["left_stick"] = Pose(spin=18.0 * k * math.sin(2 * math.pi * 2.0 * t),
                               pitch=18.0 * k * math.cos(2 * math.pi * 2.0 * t))
    poses["right_stick"] = Pose(spin=-12.0 * k * math.sin(2 * math.pi * 3.0 * t))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "wiiu_print.png"))
    colours = dict(L.COLOURS, print="#FFFFFF")
    m = {n: material(n, colours[n], r, printed if n in ("print", "glass") else None) for n, r in ROUGHNESS.items()}

    parts, eject = console(m)
    whole = join(parts + cradle(m), "wiiu")
    platter = disc(m)
    shell, moving, screens = gamepad(m)
    for obj in [whole, eject, platter, shell] + [p for p, _ in moving.values()]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("wiiu_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    seat = Vector((CX + (sx0 + sx1) / 2, CY + L.DISC["diameter"] / 2 + 4.0, (sz0 + sz1) / 2))
    platter.parent = whole
    platter.location = seat
    eject.parent = whole
    shell.parent = whole
    shell.matrix_parent_inverse = Matrix.Identity(4)
    shell.matrix_basis = PAD_FRAME
    for name, (part, where) in list(moving.items()) + list(screens.items()):
        part.parent = shell
        part.location = where
    nodes = {"disc": platter, "eject": eject, **{n: p for n, (p, _) in moving.items()},
             **{n: p for n, (p, _) in screens.items()}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ PAD_FRAME @ v.co for v in shell.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, eject, platter, shell] + [p for p, _ in moving.values()] + [p for p, _ in screens.values()]
    print(f"Wii U: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
