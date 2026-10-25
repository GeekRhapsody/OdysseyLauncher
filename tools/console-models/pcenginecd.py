"""The console theme's PC Engine CD system model (godot/themes/console/models/systems/pcenginecd.glb): a PC Engine Duo,
the PC Engine with the Super CD-ROM² built in, and its pad.

Built in Blender from the real console's proportions (pcenginecd_layout.py has the measurements, taken from
photographs). The body is a flat box, its edges rounded, the fine ribs cut into its sides, the fins into its top at
the left, POWER's slot and the pad's socket into its front, the CD's well under the lid into its top; the left panel
and the lid stand on it, the HuCard's door and its tab on the front strip, POWER's knob, the LOCK slider and OPEN with
it. The pad is a rounded slab with the cable's dome along its back, the D-pad, II and I, SELECT and RUN on it, as the
PC Engine model's. The printing is one texture drawn by pcenginecd_print.py: the top and the front (planar-mapped onto
their faces), the pad's top, the CD's label, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (its origin on its hinge), the CD (waiting on the spindle, shrunk to nothing), OPEN, POWER's knob, the
lit BUSY light (shrunk to nothing) and the pad's D-pad, II, I and RUN.

The `focused` clip (8 s, looping) plays a CD: OPEN is pressed and the lid springs up; the CD drops onto the spindle and
the lid is pushed shut; POWER slides on and BUSY flickers while it loads; RUN, and the game is played on the D-pad and
II and I in turbo bursts. Then POWER slides off, OPEN, the CD rises out and goes, and the lid shuts.

Three materials (case, key, print) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/pcenginecd_print.py artifacts/pcenginecd
    blender -b --factory-startup --python tools/console-models/pcenginecd.py -- artifacts/pcenginecd godot/themes/console/models/systems/pcenginecd.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcenginecd_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.6, key=0.5, print=0.55)
FEET = 2.0
PW, PD, PH = L.PAD["size"]


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.BASE_TOP)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.BASE_TOP - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def facing_up(c, n, name):
    return n.z > 0.95


# ---- The Duo ---------------------------------------------------------------------------------------------------------

def body(m):
    w, d = L.WIDTH, L.DEPTH
    shell = box("pcenginecd", -w / 2, w / 2, 0.0, d, FEET, L.BASE_TOP, m["case"])
    bevel(shell, L.EDGE, segments=2)
    r = L.RIBS
    for side in (-1, 1):
        x_face = side * w / 2
        a, b = (x_face - r["depth"], x_face + 5.0) if side > 0 else (x_face - 5.0, x_face + r["depth"])
        cuts, y = [], r["y"][0]
        while y + r["width"] < r["y"][1]:
            cuts.append(box("rib", a, b, y, y + r["width"], *r["z"], m["case"]))
            y += r["pitch"]
        boolean(shell, join(cuts, "ribs"))
    f = L.FINS
    boolean(shell, join([box("fin", x - f["width"] / 2, x + f["width"] / 2, *f["y"], L.BASE_TOP - f["depth"],
                             L.BASE_TOP + 5.0, m["key"]) for x in f["x"]], "fins"))
    (px0, px1), (pz0, pz1) = L.POWER["x"], L.POWER["z"]
    boolean(shell, box("power_slot", px0, px1, -5.0, 6.0, pz0, pz1, m["key"]))
    port = circle(L.PAD_PORT["x"], L.PAD_PORT["z"], L.PAD_PORT["r"], 20)
    boolean(shell, solid("pad_port", [[(x, y, z) for x, z in port] for y in (-5.0, 8.0)], m["key"]))
    (wx, wy), wr = L.WELL["at"], L.WELL["r"]
    boolean(shell, prism("well", circle(wx, wy, wr, 48), L.BASE_TOP - L.WELL["depth"], L.BASE_TOP + 5.0, m["key"]))
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.95 and c.z > L.BASE_TOP - 0.5 and name == "case")
    paint(shell, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < 1.0 and name == "case")
    spindle = prism("spindle", circle(wx, wy, L.WELL["spindle"], 20), L.BASE_TOP - L.WELL["depth"] - 0.5,
                    L.BASE_TOP - L.WELL["depth"] + 4.0, m["key"])
    (lx0, lx1), (ly0, ly1) = L.LEFT_PANEL["x"], L.LEFT_PANEL["y"]
    panel = box("panel", lx0, lx1, ly0, ly1, L.BASE_TOP - 1.0, L.PANEL_TOP, m["case"])
    bevel(panel, 2.5, segments=2)
    paint(panel, m["print"], top_uv, facing_up)
    (dx0, dx1), (dy0, dy1) = L.DOOR["x"], L.DOOR["y"]
    door = box("door", dx0, dx1, dy0, dy1 - 0.5, L.BASE_TOP - 0.5, L.BASE_TOP + L.DOOR["height"], m["case"])
    bevel(door, 0.8, segments=1)
    tx0, tx1, tz0, tz1 = L.DOOR["tab"]
    tab = box("tab", tx0, tx1, -1.5, 2.0, tz0, tz1, m["case"])
    bevel(tab, 0.6, segments=1)
    paint(door, m["print"], top_uv, facing_up)
    paint(tab, m["print"], front_uv, lambda c, n, name: n.y < -0.9)
    (kx0, kx1), ky = L.LOCK["x"], L.LOCK["y"]
    lock = painted(box("lock", kx0, kx1, ky - 2.0, ky + 2.0, L.BASE_TOP - 0.5, L.BASE_TOP + L.LOCK["height"],
                       m["print"]), m, "lavender")
    return [shell, spindle, panel, door, tab, lock]


def lid(m):
    """The lid, its origin on its hinge (its back edge's top)."""
    (x0, x1), (y0, y1) = L.LID["x"], L.LID["y"]
    part = box("lid", x0, x1, y0, y1, L.BASE_TOP - 0.5, L.PANEL_TOP, m["case"])
    bevel(part, 2.5, segments=2)
    paint(part, m["print"], top_uv, facing_up)
    hinge = Vector((0.0, y1, L.PANEL_TOP))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def open_button(m):
    (ox, oy), r = L.OPEN["at"], L.OPEN["r"]
    part = painted(prism("open", circle(ox, oy, r, 28), L.BASE_TOP - 1.0, L.BASE_TOP + L.OPEN["height"], m["print"]),
                   m, "lavender")
    bevel(part, 1.0, segments=2)
    return part


def power_knob(m):
    """POWER's knob in its slot, at OFF; its middle at its origin."""
    (px0, px1), (pz0, pz1), k = L.POWER["x"], L.POWER["z"], L.POWER["knob"]
    part = painted(box("power", -k / 2, k / 2, -L.POWER["out"], 4.0, -(pz1 - pz0) / 2 + 0.6, (pz1 - pz0) / 2 - 0.6,
                       m["print"]), m, "teal")
    bevel(part, 0.6, segments=1)
    return part, Vector((px0 + k / 2 + 0.6, 0.0, (pz0 + pz1) / 2))


def busy_light(m):
    (bx0, bx1), by = L.BUSY["x"], L.BUSY["y"]
    part = painted(box("busy", -(bx1 - bx0) / 2, (bx1 - bx0) / 2, -1.0, 1.0, -0.2, 0.3, m["print"]), m, "lit")
    return part, Vector(((bx0 + bx1) / 2, by, L.BASE_TOP))


def disc(m):
    """The CD, its middle at its origin, lying flat: a ring, its label on its top."""
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
    dm = L.DISC["diameter"]
    face = atlas_uv(L.REGIONS["disc"], dm, dm)
    paint(part, m["print"], lambda co: face(co.x + dm / 2, dm / 2 - co.y), lambda c, n_, name: n_.z > 0.9)
    paint(part, m["print"], swatch("silver"), lambda c, n_, name: n_.z <= 0.9)
    return part


# ---- The pad ---------------------------------------------------------------------------------------------------------

def pad(m):
    """The pad in its own frame (its plan's middle at the origin, the table): its body, the dome, SELECT; the D-pad,
    II, I and RUN apart, each its middle at its origin."""
    p = L.PAD
    body = prism("pad", rounded(0.0, 0.0, PW, PD, p["r"], 4), 0.0, PH, m["case"])
    bevel(body, 3.0, segments=3)
    top = atlas_uv(L.REGIONS["pad"], PW, PD)
    paint(body, m["print"], lambda co: top(co.x + PW / 2, PD / 2 - co.y), lambda c, n, name: n.z > 0.9)
    dm = p["dome"]
    half = [(dm["r"] * math.cos(math.pi * (1 + k / 16)), dm["y"] + dm["r"] * math.sin(math.pi * (1 + k / 16)))
            for k in range(17)]
    dome = prism("dome", half, PH - 1.0, PH + dm["height"], m["case"])
    bevel(dome, 1.8, segments=3)
    pw, ph = p["pill"]
    x, y = p["select"]
    select = painted(prism("select", [(x + a, y + b) for a, b in rounded(0.0, 0.0, pw, ph, ph / 2 - 0.1, 3)],
                           PH - 1.0, PH + 1.4, m["print"]), m, "grey")
    shell = join([body, dome, select], "pad")
    dx, dy, span, arm = p["dpad"]
    cross = [(arm / 2, -span / 2), (arm / 2, -arm / 2), (span / 2, -arm / 2), (span / 2, arm / 2), (arm / 2, arm / 2),
             (arm / 2, span / 2), (-arm / 2, span / 2), (-arm / 2, arm / 2), (-span / 2, arm / 2), (-span / 2, -arm / 2),
             (-arm / 2, -arm / 2), (-arm / 2, -span / 2)]
    dpad = painted(prism("dpad", cross, -2.0, 2.6, m["print"]), m, "grey")
    bevel(dpad, 0.6, segments=1)
    parts = {"dpad": (dpad, Vector((dx, dy, PH)))}
    for name in ("ii", "i"):
        bx, by = p[name]
        button = painted(prism(name, circle(0.0, 0.0, p["button_r"], 24), -2.0, 2.6, m["print"]), m, "grey")
        bevel(button, 1.0, segments=2)
        parts[name] = (button, Vector((bx, by, PH)))
    run = painted(prism("run", rounded(0.0, 0.0, pw, ph, ph / 2 - 0.1, 3), -1.0, 1.4, m["print"]), m, "grey")
    parts["run"] = (run, Vector((*p["run"], PH)))
    return shell, parts


# ---- The focused clip ------------------------------------------------------------------------------------------------

DROP = 80.0          # how far above the spindle the CD appears
OPEN = -76.0


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def lid_angle(f):
    if f < 12:
        return 0.0
    if f < 46:
        return OPEN * back_out(phase(f, 12, 24), 1.4)
    if f < 64:
        return OPEN * (1 - smooth(phase(f, 46, 56))) + wobble(f, 56, 2.0, period=6.0, decay=4.0)
    if f < 204:
        return 0.0
    if f < 224:
        return OPEN * back_out(phase(f, 204, 216), 1.4)
    return OPEN * (1 - smooth(phase(f, 224, 236)))


def timeline(f):
    if f < 20 or f >= 222:
        cd = Pose(scale=HIDDEN)
    elif f < 28:
        cd = Pose(z=DROP, scale=appear(f, 20, 28))
    elif f < 42:
        cd = Pose(z=DROP * (1 - ease_in(phase(f, 28, 42))), spin=90.0 * phase(f, 28, 42))
    elif f < 210:
        cd = Pose(z=wobble(f, 42, 1.4, period=6.0, decay=5.0), spin=90.0)
    else:
        cd = Pose(z=DROP * ease_out(phase(f, 210, 218)), spin=90.0, scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 222))))
    on = smooth(phase(f, 62, 68)) * (1 - smooth(phase(f, 194, 200)))
    loading = 70 <= f < 116 and (f * 3 // 4) % 3 != 0
    t = phase(f, 124, 190)
    k = math.sin(math.pi * t)
    turbo = 128 <= f < 188 and f % 6 < 3
    return {"lid": Pose(pitch=lid_angle(f)), "disc": cd, "open": Pose(z=-1.6 * max(tap(f, 8), tap(f, 200))),
            "power": Pose(x=L.POWER["travel"] * on), "busy": Pose() if loading else Pose(scale=HIDDEN),
            "run": Pose(z=-1.0 * tap(f, 118)),
            "dpad": Pose(pitch=8.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=8.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "ii": Pose(z=-1.6 if turbo and f < 158 else 0.0), "i": Pose(z=-1.6 if turbo and f >= 152 else 0.0)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "pcenginecd_print.png"))
    m = {n: material(n, L.COLOURS[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join(body(m), "pcenginecd")
    cover, hinge = lid(m)
    opener = open_button(m)
    knob, knob_at = power_knob(m)
    lit, lit_at = busy_light(m)
    cd = disc(m)
    pad_shell, pad_parts = pad(m)
    for obj in [whole, cover, opener, knob, cd, pad_shell] + [p for p, _ in pad_parts.values()]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("pcenginecd_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (wx, wy) = L.WELL["at"]
    seat = Vector((wx, wy, L.BASE_TOP - L.WELL["depth"] + 4.0 + L.DISC["thickness"] / 2))
    for part, where in ((cover, hinge), (cd, seat), (knob, knob_at), (lit, lit_at)):
        part.parent = whole
        part.location = where
    opener.parent = whole
    (px, py), turn = L.PAD["at"], math.radians(L.PAD["turn"])
    pad_shell.parent = whole
    pad_shell.location = (px, py, 0.0)
    pad_shell.rotation_euler = (0.0, 0.0, turn)
    for part, where in pad_parts.values():
        part.parent = pad_shell
        part.location = where
    nodes = {"lid": cover, "disc": cd, "open": opener, "power": knob, "busy": lit,
             **{n: p for n, (p, _) in pad_parts.items()}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(turn, 4, "Z")
    points = ([tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in pad_shell.data.vertices]
              + [tilt @ Matrix.Translation(hinge) @ v.co for v in cover.data.vertices])
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, cover, opener, knob, lit, cd, pad_shell] + [p for p, _ in pad_parts.values()]
    print(f"PC Engine Duo: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
