"""The console theme's Neo Geo CD system model (godot/themes/console/models/systems/neogeocd.glb): a Neo Geo CD
top-loader and its controller.

Built in Blender from the real console's proportions (neogeocd_layout.py has the measurements, taken from
photographs). The body is its rounded square plan lofted up on its feet, its edges rounded; the ribs are cut into its
sides towards the back, the ports into its front, the vent strip (its slats laid in it) into the top behind the deck.
The deck stands on the top, its front edge bowed forward, the CD's well and spindle in it under the lid; the lid lies
on the deck, hinged at its back; POWER stands at the front left. The controller is its dog-bone outline lofted up, its
top rounded, the stick standing in its ring, SELECT, START and the four coloured buttons on it. The printing is one
texture drawn by neogeocd_print.py: the top and the front (planar-mapped onto their faces), the controller's top, the
CD's label, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the lid (its origin on its hinge), the CD (waiting on the spindle, shrunk to nothing), POWER, the lit access
light (shrunk to nothing) and the controller; the controller holding its stick, A and B.

The `focused` clip (8 s, looping) plays a CD: the lid swings up, the CD drops onto the spindle and the lid shuts; POWER,
and the access light flickers on and on through the Neo Geo CD's long load; then the game is played on the stick, A
and B. Then the lid swings up again, the CD rises out and goes, and the lid shuts.

Three materials (case, key, print) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/neogeocd_print.py artifacts/neogeocd
    blender -b --factory-startup --python tools/console-models/neogeocd.py -- artifacts/neogeocd godot/themes/console/models/systems/neogeocd.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neogeocd_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, key=0.5, print=0.5)
DECK_TOP = L.BODY_TOP + L.DECK["height"]
LID_TOP = DECK_TOP + L.LID["height"]


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.BODY_TOP)
PAD_TOP = atlas_uv(L.REGIONS["pad"], 156.0, 76.0)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.BODY_TOP - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def upright(name, points, z0, z1, mat):
    """A solid from an (x, y) plan, from z0 up to z1."""
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


def disc_ring(name, r, z0, z1, mat, n=40, at=(0.0, 0.0)):
    return upright(name, [(at[0] + r * math.cos(2 * math.pi * k / n), at[1] + r * math.sin(2 * math.pi * k / n))
                          for k in range(n)], z0, z1, mat)


def facing_up(c, n, name):
    return n.z > 0.95


# ---- The console -----------------------------------------------------------------------------------------------------

def body(m):
    w, d = L.WIDTH, L.DEPTH
    plan = [(x, y + d / 2) for x, y in rounded(0.0, 0.0, w, d, L.CORNER, 6)]
    shell = upright("neogeocd", plan, L.FEET, L.BODY_TOP, m["case"])
    bevel(shell, 4.0, segments=2)
    r = L.RIBS
    for side in (-1, 1):
        x_face = side * w / 2
        a, b = (x_face - r["depth"], x_face + 5.0) if side > 0 else (x_face - 5.0, x_face + r["depth"])
        step = (r["y"][1] - r["y"][0]) / r["count"]
        boolean(shell, join([box("rib", a, b, r["y"][0] + k * step + (step - r["width"]) / 2,
                                 r["y"][0] + k * step + (step + r["width"]) / 2, *r["z"], m["case"])
                             for k in range(r["count"])], "ribs"))
    (z0, z1), pw, pd = L.PORTS["z"], L.PORTS["width"], L.PORTS["depth"]
    boolean(shell, join([box("port", x - pw / 2, x + pw / 2, -5.0, pd, z0, z1, m["key"]) for x in L.PORTS["x"]],
                        "ports"))
    (vx0, vx1), (vy0, vy1) = L.VENT["x"], L.VENT["y"]
    boolean(shell, box("vent", vx0, vx1, vy0, vy1, L.BODY_TOP - L.VENT["depth"], L.BODY_TOP + 5.0, m["key"]))
    paint(shell, m["print"], top_uv, lambda c, n, name: n.z > 0.95 and c.z > L.BODY_TOP - 0.5 and name == "case")
    paint(shell, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < 1.0)
    n = L.VENT["slats"]
    slats = [box("slat", vx0 + 2.0, vx1 - 2.0, vy0 + (vy1 - vy0) * (k + 0.5) / n - 2.6,
                 vy0 + (vy1 - vy0) * (k + 0.5) / n + 2.6, L.BODY_TOP - L.VENT["depth"] - 0.5, L.BODY_TOP - 1.0,
                 m["case"]) for k in range(n)]
    feet = [box("foot", x - 14.0, x + 14.0, y - 14.0, y + 14.0, 0.0, L.FEET + 1.0, m["key"])
            for x in (-110.0, 110.0) for y in (30.0, d - 30.0)]
    deck_plan = L.bowed(*L.DECK["x"], *L.DECK["y"], L.DECK["bow"])
    deck = upright("deck", list(reversed(deck_plan)), L.BODY_TOP - 1.0, DECK_TOP, m["case"])
    bevel(deck, 3.0, segments=2)
    (wx, wy), wr = L.WELL["at"], L.WELL["r"]
    boolean(deck, disc_ring("well", wr, DECK_TOP - L.WELL["depth"], DECK_TOP + 5.0, m["key"], 48, (wx, wy)))
    paint(deck, m["print"], top_uv, lambda c, n, name: n.z > 0.95 and c.z > DECK_TOP - 0.5)
    spindle = disc_ring("spindle", L.WELL["spindle"], DECK_TOP - L.WELL["depth"] - 0.5, DECK_TOP - L.WELL["depth"] + 4.0,
                        m["key"], 20, (wx, wy))
    return [shell, deck, spindle] + slats + feet


def lid(m):
    """The lid, its origin on its hinge (its back edge's top)."""
    plan = L.bowed(*L.LID["x"], *L.LID["y"], L.LID["bow"])
    part = upright("lid", list(reversed(plan)), DECK_TOP - 0.5, LID_TOP, m["case"])
    bevel(part, 2.5, segments=2)
    paint(part, m["print"], top_uv, lambda c, n, name: n.z > 0.95)
    hinge = Vector((0.0, L.LID["y"][1], LID_TOP))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def power(m):
    (px, py), r = L.POWER["at"], L.POWER["r"]
    part = disc_ring("power", r, L.BODY_TOP - 1.0, L.BODY_TOP + L.POWER["height"], m["key"], 32, (px, py))
    bevel(part, 1.0, segments=2)
    paint(part, m["print"], top_uv, lambda c, n, name: n.z > 0.95)
    paint(part, m["print"], swatch("grey"), lambda c, n, name: n.z <= 0.95)
    return part


def light(m):
    (lx, ly), r = L.LIGHT["at"], L.LIGHT["r"]
    part = disc_ring("light", r + 0.3, -0.2, 0.4, m["print"], 12)
    paint(part, m["print"], swatch("lit"), lambda c, n, name: True)
    return part, Vector((lx, ly, L.BODY_TOP))


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


# ---- The controller --------------------------------------------------------------------------------------------------

def controller(m):
    """The controller in its own frame (its plan's middle at the origin, the table): its body, the ring's well, SELECT,
    START, C and D; the stick, A and B apart, each its foot's middle at its origin."""
    h = L.PAD["height"]
    plan = L.PAD_OUTLINE
    rings = [[(x, y, z) for x, y in inset(plan, k)] for k, z in ((2.5, 0.0), (0.0, 3.5), (0.0, h - 5.0), (2.0, h - 1.5),
                                                                  (5.0, h))]
    body = solid("controller", rings, m["case"])
    for p in body.data.polygons:
        p.use_smooth = True
    (rx, ry), (r0, r1) = L.RING["at"], L.RING["r"]
    boolean(body, disc_ring("ring", r0 + 1.0, h - 2.0, h + 5.0, m["key"], 32, (rx, ry)))
    paint(body, m["print"], lambda co: PAD_TOP(co.x + 78.0, 38.0 - co.y), lambda c, n, name: n.z > 0.95 and name == "case")
    parts = [body]
    s = L.SMALL
    sw, sh = s["size"]
    for name in ("select", "start"):
        x, y = s[name]
        c, si = math.cos(math.radians(s["turn"])), math.sin(math.radians(s["turn"]))
        oval = [(x + c * u - si * v, y + si * u + c * v) for u, v in rounded(0.0, 0.0, sw, sh, sh / 2 - 0.01, 5)]
        part = upright(name, oval, h - 1.0, h + s["height"], m["key"])
        bevel(part, 0.6, segments=1)
        parts.append(part)
    face_r, face_h = L.FACE["r"], L.FACE["height"]
    colours = dict(a="red", b="yellow", c="green", d="blue")
    for name in ("c", "d"):
        part = disc_ring(name, face_r, h - 1.5, h + face_h, m["print"], 28, L.FACE[name])
        bevel(part, 1.2, segments=2)
        paint(part, m["print"], swatch(colours[name]), lambda c, n, _name: True)
        parts.append(part)
    shell = join(parts, "controller")
    buttons = {}
    for name in ("a", "b"):
        part = disc_ring(name, face_r, -1.5, face_h, m["print"], 28)
        bevel(part, 1.2, segments=2)
        paint(part, m["print"], swatch(colours[name]), lambda c, n, _name: True)
        buttons[name] = (part, Vector((*L.FACE[name], h)))
    (sr0, sr1), (sz0, sz1) = L.STICK["r"], L.STICK["height"]
    base = disc_ring("stick_base", sr0, -1.0, sz0, m["key"], 32)
    bevel(base, 1.5, segments=2)
    cap = disc_ring("stick_cap", sr1, sz0 - 1.0, sz1, m["key"], 28)
    bevel(cap, 2.5, segments=2)
    stick = join([base, cap], "stick")
    buttons["stick"] = (stick, Vector((rx, ry, h - 2.0)))
    return shell, buttons


# ---- The focused clip ------------------------------------------------------------------------------------------------

DROP = 80.0          # how far above the spindle the CD appears


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


OPEN = -78.0


def lid_angle(f):
    if f < 10:
        return 0.0
    if f < 44:
        return OPEN * back_out(phase(f, 10, 24), 1.2)
    if f < 64:
        return OPEN * (1 - smooth(phase(f, 44, 56))) + wobble(f, 56, 2.0, period=6.0, decay=4.0)
    if f < 198:
        return 0.0
    if f < 222:
        return OPEN * back_out(phase(f, 198, 210), 1.2)
    return OPEN * (1 - smooth(phase(f, 222, 234)))


def timeline(f):
    if f < 18 or f >= 220:
        cd = Pose(scale=HIDDEN)
    elif f < 26:
        cd = Pose(z=DROP, scale=appear(f, 18, 26))
    elif f < 40:
        cd = Pose(z=DROP * (1 - ease_in(phase(f, 26, 40))), spin=90.0 * phase(f, 26, 40))
    elif f < 206:
        cd = Pose(z=wobble(f, 40, 1.4, period=6.0, decay=5.0), spin=90.0)
    else:
        cd = Pose(z=DROP * ease_out(phase(f, 206, 216)), spin=90.0, scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 220))))
    reading = 66 <= f < 150 and (f * 7 // 5) % 5 != 0
    t = phase(f, 120, 194)
    k = math.sin(math.pi * t)
    return {"lid": Pose(pitch=lid_angle(f)), "disc": cd, "power": Pose(z=-2.0 * tap(f, 60)),
            "light": Pose() if reading else Pose(scale=HIDDEN),
            "stick": Pose(pitch=18.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=18.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "a": Pose(z=-2.4 * max(tap(f, f0) for f0 in (134, 156, 178))),
            "b": Pose(z=-2.4 * max(tap(f, f0) for f0 in (144, 166, 186)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "neogeocd_print.png"))
    m = {n: material(n, L.COLOURS[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join(body(m), "neogeocd")
    cover, hinge = lid(m)
    button = power(m)
    lit, lit_at = light(m)
    cd = disc(m)
    pad, buttons = controller(m)
    for obj in [whole, cover, button, cd] + [p for p, _ in buttons.values()]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))
    pad.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("neogeocd_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (wx, wy) = L.WELL["at"]
    seat = Vector((wx, wy, DECK_TOP - L.WELL["depth"] + 4.0 + L.DISC["thickness"] / 2))
    for part, where in ((cover, hinge), (cd, seat), (lit, lit_at)):
        part.parent = whole
        part.location = where
    button.parent = whole
    (px, py), turn = L.PAD["at"], math.radians(L.PAD["turn"])
    pad.parent = whole
    pad.location = (px, py, 0.0)
    pad.rotation_euler = (0.0, 0.0, turn)
    for part, where in buttons.values():
        part.parent = pad
        part.location = where
    nodes = {"lid": cover, "disc": cd, "power": button, "light": lit, **{n: p for n, (p, _) in buttons.items()}}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(turn, 4, "Z")
    points = ([tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in pad.data.vertices]
              + [tilt @ Matrix.Translation(hinge) @ v.co for v in cover.data.vertices])
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, cover, button, lit, cd, pad] + [p for p, _ in buttons.values()]
    print(f"Neo Geo CD: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
