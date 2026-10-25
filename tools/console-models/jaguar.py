"""The console theme's Atari Jaguar and Jaguar CD system models (godot/themes/console/models/systems/atarijaguar.glb and
atarijaguarcd.glb): the Jaguar and its controller, and the same with the Jaguar CD on it.

Built in Blender from the real console's proportions (jaguar_layout.py has the measurements, taken from photographs).
The Jaguar's body is its rounded plan lofted up into a low pillow; its round nose is lofted on its front, the dish
recessed into its top, the slot's frame raised at its back with the slot through it, the two ribbed wings beside the
frame; the red power button stands on the nose. The controller is its outline lofted up, its edges rounded, the D-pad
in its ring, PAUSE and OPTION, the red A, B and C, the keypad's keys on their plate. The Jaguar CD is its plan (its
round front, its back section) lofted up on the Jaguar's top, the well for the disc under its lid, its own slot's frame
raised at its back. The printing is one texture drawn by jaguar_print.py: the Jaguar, the controller and the Jaguar CD
from above (planar-mapped onto the faces facing up), the CD's and the cartridge's labels, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the power button, the lit power light (shrunk to nothing) and the controller (holding its D-pad and A, B and
C); and either the cartridge (waiting in its slot, shrunk to nothing) or, on the Jaguar CD, the lid (its origin on its
hinge) and the disc (waiting in the well, shrunk to nothing).

The `focused` clip (8 s, looping) plays a game: the cartridge drops into the slot (or the Jaguar CD's lid swings up, the
disc drops in and the lid shuts); the power button is pressed and its light comes on; the game is played on the D-pad,
A, B and C. Then the power button again, and the cartridge rises out and goes (or the lid swings up, the disc goes, and
the lid shuts).

Four materials (case, key, red, print) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/jaguar_print.py artifacts/jaguar
    blender -b --factory-startup --python tools/console-models/jaguar.py -- artifacts/jaguar atarijaguar godot/themes/console/models/systems/atarijaguar.glb

and the same with atarijaguarcd.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jaguar_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.6, key=0.5, red=0.4, print=0.55)
PAD_W = 2 * max(x for x, _ in L.PAD_OUTLINE)


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
PAD_TOP = atlas_uv(L.REGIONS["pad"], PAD_W, L.PAD_D)
CD_Y0 = L.CD["at"] - L.CD["r"]
CD_TOP = atlas_uv(L.REGIONS["cd"], 2 * L.CD["r"], L.CD["back"][2] - CD_Y0)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def cd_uv(co):
    return CD_TOP(co.x + L.CD["r"], L.CD["back"][2] - co.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def upright(name, points, z0, z1, mat):
    """A solid from an (x, y) plan, from z0 up to z1."""
    return solid(name, [[(x, y, z) for x, y in points] for z in (z0, z1)], mat)


def circle(cx, cy, r, n=32):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def facing_up(c, n, name):
    return n.z > 0.85


# ---- The Jaguar ------------------------------------------------------------------------------------------------------

def jaguar(m):
    """The Jaguar: its body, the nose, the frame and the wings; the dish and the slot cut into them; its top
    printed."""
    (y0, y1), corner = L.BODY["y"], L.BODY["corner"]
    rings = [[(x, y, z) for x, y in rounded(0.0, (y0 + y1) / 2, L.WIDTH - 2 * k, y1 - y0 - 2 * k, corner - k * 0.6, 6)]
             for k, z in L.BODY["rings"]]                 # each ring smaller (and its corners tighter) to the top
    body = solid("atarijaguar", rings, m["case"])
    for p in body.data.polygons:
        p.use_smooth = True
    (dx, dy), r = L.DISH["at"], L.DISH["r"]
    top_z = L.BODY["rings"][-1][1]
    boolean(body, upright("dish", circle(dx, dy, r, 48), top_z - L.DISH["depth"], top_z + 20.0, m["case"]))

    n = L.NOSE
    half = [(n["x"] * math.cos(math.radians(a)), n["y"][1] - (n["y"][1] - n["y"][0]) * math.sin(math.radians(a)))
            for a in range(0, 181, 10)]
    nose = solid("nose", [[(x * k, n["y"][1] - (n["y"][1] - y) * k, z) for x, y in half] for k, z in
                          ((1.0, 0.0), (1.0, n["top"] - 10.0), (0.94, n["top"]), (0.7, n["height"]))], m["case"])
    for p in nose.data.polygons:
        p.use_smooth = True

    (fx0, fx1), (fy0, fy1) = L.FRAME["x"], L.FRAME["y"]
    frame = box("frame", fx0, fx1, fy0, fy1, top_z - 10.0, L.FRAME["top"], m["case"])
    bevel(frame, 3.0, segments=2)
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    w = L.WINGS
    wings = []
    for side in (-1, 1):
        a, b = side * w["x"][0], side * w["x"][1]
        z_in, z_out = w["top"]
        profile = [(w["y"][0], 0.0), (w["y"][1], 0.0), (w["y"][1], z_in), (w["y"][0] + 10.0, z_in)]
        wing = prism_x("wing", profile, min(a, b), max(a, b), m["case"])
        # its top slopes down to its outer edge
        for v in wing.data.vertices:
            if v.co.z > 1.0:
                t = (abs(v.co.x) - w["x"][0]) / (w["x"][1] - w["x"][0])
                v.co.z = z_in + (z_out - z_in) * t
        bevel(wing, 1.5, segments=2)
        pitch, (rib_w, rib_d) = (w["y"][1] - w["y"][0] - 14.0) / w["ribs"], w["rib"]
        cuts = [box("rib", min(a, b) - 5.0, max(a, b) + 5.0, w["y"][0] + 12.0 + k * pitch,
                    w["y"][0] + 12.0 + k * pitch + rib_w, -1.0, 80.0, m["key"]) for k in range(w["ribs"])]
        groove = join(cuts, "ribs")
        for v in groove.data.vertices:                  # each groove's floor follows the sloping top, rib_d under it
            if v.co.z < 0.0:
                t = (abs(v.co.x) - w["x"][0]) / (w["x"][1] - w["x"][0])
                v.co.z = (z_in + (z_out - z_in) * max(0.0, min(1.0, t))) - rib_d
        boolean(wing, groove)
        wings.append(wing)
    for part in (body, frame):                          # the slot through each (overlapping, they're cut apart)
        boolean(part, box("slot", sx0, sx1, sy0, sy1, L.FRAME["top"] - L.SLOT["depth"], L.FRAME["top"] + 5.0, m["key"]))
    whole = join([body, nose, frame] + wings, "atarijaguar")
    paint(whole, m["print"], top_uv, lambda c, n, name: n.z > 0.6 and name == "case")
    return whole


def power(m):
    (px, py), (pw, ph) = L.POWER["at"], L.POWER["size"]
    oval = [(pw / 2 * math.cos(2 * math.pi * k / 24), ph / 2 * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    part = solid("power", [[(x, y, z) for x, y in oval] for z in (-1.0, L.POWER["height"])], m["red"])
    bevel(part, 1.4, segments=2)
    return part, Vector((px, py, L.NOSE["height"] - 0.6))


def power_light(m):
    (px, py) = L.POWER["at"]
    part = painted(upright("power_light", circle(0.0, 0.0, 1.4, 12), -0.2, 0.3, m["print"]), m, "lit")
    return part, Vector((px, py - 9.0, L.NOSE["height"] - 1.6))


def cartridge(m):
    """The cartridge, its bottom's middle at its origin: its shell, its label on its front (-y)."""
    w, t, h = L.CART["size"]
    lw, lh = L.CART["label"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(shell, 2.0, segments=2)
    grip = box("grip", -w / 2 + 6.0, w / 2 - 6.0, -t / 2 - 1.0, t / 2 + 1.0, h - 10.0, h, m["case"])
    bevel(grip, 1.4, segments=2)
    z1 = h - 13.0
    decal = box("label", -lw / 2, lw / 2, -t / 2 - 0.2, -t / 2 + 0.3, z1 - lh, z1, m["print"])
    face = atlas_uv(L.REGIONS["label"], lw, lh)
    paint(decal, m["print"], lambda co: face(co.x + lw / 2, z1 - co.z), lambda c, n, name: n.y < -0.9)
    paint(decal, m["print"], swatch("dark"), lambda c, n, name: n.y >= -0.9)
    return join([shell, grip, decal], "cartridge")


# ---- The Jaguar CD ---------------------------------------------------------------------------------------------------

def cd_plan():
    """The Jaguar CD's plan, anticlockwise: its round front, then its back section."""
    r, cy = L.CD["r"], L.CD["at"]
    bx0, bx1, by = L.CD["back"]
    points = [(r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(180, 361, 6)]
    x_side = r
    y_side = cy + 30.0
    points += [(x_side, y_side), (bx1, y_side + 26.0), (bx1, by), (bx0, by), (bx0, y_side + 26.0), (-x_side, y_side)]
    return points


def jaguar_cd(m):
    """The Jaguar CD on the Jaguar's top: its body (the well cut into it, its own slot's frame at its back)."""
    foot, top = L.CD["foot"], L.CD["top"]
    plan = cd_plan()
    body = solid("jaguarcd", [[(x, y, z) for x, y in inset(plan, k)] for k, z in
                              ((2.0, foot), (0.0, foot + 6.0), (0.0, top - 3.0), (2.5, top))], m["case"])
    for p in body.data.polygons:
        p.use_smooth = True
    r, cy = L.LID["r"], L.CD["at"]
    boolean(body, upright("well", circle(0.0, cy, L.DISC["diameter"] / 2 + L.DISC["well"], 48),
                          top - 8.0, top + 10.0, m["key"]))
    (fx0, fx1), (fy0, fy1) = L.CD_FRAME["x"], L.CD_FRAME["y"]
    frame = box("cd_frame", fx0, fx1, fy0, fy1, top - 6.0, L.CD_FRAME["top"], m["case"])
    bevel(frame, 3.0, segments=2)
    (sx0, sx1), (sy0, sy1) = L.CD_SLOT["x"], L.CD_SLOT["y"]
    for part in (body, frame):
        boolean(part, box("cd_slot", sx0, sx1, sy0, sy1, L.CD_FRAME["top"] - L.CD_SLOT["depth"],
                          L.CD_FRAME["top"] + 5.0, m["key"]))
    whole = join([body, frame], "jaguarcd")
    paint(whole, m["print"], cd_uv, lambda c, n, name: n.z > 0.85 and name == "case")
    spindle = upright("spindle", circle(0.0, cy, 7.0, 20), top - 9.0, top - 4.0, m["key"])
    return [whole, spindle]


def lid(m):
    """The Jaguar CD's lid, its origin on its hinge (its back edge's top)."""
    r, cy, back = L.LID["r"], L.CD["at"], L.LID["back"]
    top, h = L.CD["top"], L.LID["height"]
    plan = [(r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(180, 361, 6)]
    plan += [(r, back), (-r, back)]
    part = solid("lid", [[(x, y, z) for x, y in inset(plan, k)] for k, z in ((0.0, top - 0.5), (0.0, top + h - 1.5),
                                                                              (1.5, top + h))], m["case"])
    bevel(part, 1.0, segments=2)
    paint(part, m["print"], cd_uv, lambda c, n, name: n.z > 0.85)
    hinge = Vector((0.0, back, top + h))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


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
    """The controller in its own frame (its front edge's middle at the origin, the table): its body, PAUSE, OPTION and
    the keypad; the D-pad, A, B and C apart, each its foot's middle at its origin."""
    h0, h1 = L.PAD["height"]
    outline = L.PAD_OUTLINE
    rings = [[(x, y, z) for x, y in inset(outline, k)] for k, z in ((2.5, 0.0), (0.0, 4.0), (0.0, h0 - 5.0),
                                                                     (2.5, h0 - 1.0), (5.0, h0))]
    body = solid("controller", rings, m["case"])
    # its top rises to the back
    for v in body.data.vertices:
        if v.co.z > 1.0:
            v.co.z += (h1 - h0) * v.co.y / L.PAD_D * (v.co.z / h0)
    for p in body.data.polygons:
        p.use_smooth = True
    paint(body, m["print"], lambda co: PAD_TOP(co.x + PAD_W / 2, L.PAD_D - co.y), facing_up)
    parts = [body]

    def surface(y):
        return h0 + (h1 - h0) * y / L.PAD_D

    sw, sh = L.SMALL["size"]
    for name in ("pause", "option"):
        x, y = L.SMALL[name]
        c, s = math.cos(math.radians(L.SMALL["turn"])), math.sin(math.radians(L.SMALL["turn"]))
        pill = [(x + c * u - s * v, y + s * u + c * v) for u, v in rounded(0.0, 0.0, sw, sh, sh / 2 - 0.01, 4)]
        part = upright(name, pill, surface(y) - 1.0, surface(y) + L.SMALL["height"], m["key"])
        bevel(part, 0.5, segments=1)
        parts.append(part)
    (kx0, kx1), (ky0, ky1), (kw, kh) = L.KEYPAD["x"], L.KEYPAD["y"], L.KEYPAD["key"]
    for i in range(4):
        for j in range(3):
            x = kx0 + (kx1 - kx0) * j / 2
            y = ky1 - (ky1 - ky0) * i / 3
            k = upright("key", [(x + a, y + b) for a, b in rounded(0.0, 0.0, kw, kh, kh / 2 - 0.01, 4)],
                        surface(y) - 1.0, surface(y) + L.KEYPAD["height"], m["key"])
            bevel(k, 0.5, segments=1)
            parts.append(k)
    shell = join(parts, "controller")

    moving = {}
    (dx, dy), size, arm = L.DPAD["at"], L.DPAD["size"], L.DPAD["arm"]
    s, a = size / 2, arm / 2
    cross = [(a, s), (-a, s), (-a, a), (-s, a), (-s, -a), (-a, -a), (-a, -s), (a, -s), (a, -a), (s, -a), (s, a), (a, a)]
    pad = upright("dpad", cross, -2.0, L.DPAD["height"], m["key"])
    bevel(pad, 0.8, segments=1)
    moving["dpad"] = (pad, Vector((dx, dy, surface(dy))))
    bw, bh = L.ABC["size"]
    c, si = math.cos(math.radians(L.ABC["turn"])), math.sin(math.radians(L.ABC["turn"]))
    for name in ("a", "b", "c"):
        x, y = L.ABC[name]
        shape = [(c * u - si * v, si * u + c * v) for u, v in rounded(0.0, 0.0, bw, bh, 3.0, 3)]
        part = upright(name, shape, -2.0, L.ABC["height"], m["red"])
        bevel(part, 1.0, segments=2)
        moving[name] = (part, Vector((x, y, surface(y))))
    return shell, moving


# ---- The focused clips -----------------------------------------------------------------------------------------------

DROP = 96.0


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def playing(f):
    """The power button, its light and the controller, the same on both."""
    t = phase(f, 80, 190)
    k = math.sin(math.pi * t)
    return {"power": Pose(z=-1.6 * max(tap(f, 60), tap(f, 196))),
            "power_light": Pose() if 64 <= f < 200 else Pose(scale=HIDDEN),
            "dpad": Pose(pitch=8.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=8.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "a": Pose(z=-2.0 * max(tap(f, f0) for f0 in (96, 124, 152, 176))),
            "b": Pose(z=-2.0 * max(tap(f, f0) for f0 in (108, 140, 168))),
            "c": Pose(z=-2.0 * max(tap(f, f0) for f0 in (116, 160)))}


def timeline_jaguar(f):
    if f < 8 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 18:
        cart = Pose(z=DROP, scale=appear(f, 8, 16))
    elif f < 32:
        cart = Pose(z=DROP * (1 - ease_in(phase(f, 18, 32))))
    elif f < 206:
        cart = Pose(squash=0.05 * math.sin(math.pi * phase(f, 32, 38)))
    else:
        cart = Pose(z=DROP * ease_out(phase(f, 206, 218)), scale=max(HIDDEN, 1 - ease_in(phase(f, 214, 226))))
    return {"cartridge": cart, **playing(f)}


OPEN = -70.0


def lid_angle(f):
    if f < 10:
        return 0.0
    if f < 42:
        return OPEN * back_out(phase(f, 10, 22), 1.2)
    if f < 60:
        return OPEN * (1 - smooth(phase(f, 42, 52))) + wobble(f, 52, 2.0, period=6.0, decay=4.0)
    if f < 202:
        return 0.0
    if f < 224:
        return OPEN * back_out(phase(f, 202, 212), 1.2)
    return OPEN * (1 - smooth(phase(f, 224, 236)))


def timeline_cd(f):
    if f < 16 or f >= 222:
        cd = Pose(scale=HIDDEN)
    elif f < 24:
        cd = Pose(z=80.0, scale=appear(f, 16, 24))
    elif f < 38:
        cd = Pose(z=80.0 * (1 - ease_in(phase(f, 24, 38))), spin=90.0 * phase(f, 24, 38))
    elif f < 208:
        cd = Pose(z=wobble(f, 38, 1.2, period=6.0, decay=5.0), spin=90.0 + 720.0 * smooth(phase(f, 66, 190)))
    else:
        cd = Pose(z=70.0 * ease_out(phase(f, 208, 216)), spin=810.0, scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    return {"lid": Pose(pitch=lid_angle(f)), "disc": cd, **playing(f)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, kind, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "jaguar_print.png"))
    m = {n: material(n, L.COLOURS[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    parts = [jaguar(m)]
    button, button_at = power(m)
    lit, lit_at = power_light(m)
    pad, moving = controller(m)
    if kind == "atarijaguarcd":
        parts += jaguar_cd(m)
        cover, hinge = lid(m)
        media = disc(m)
        seat = Vector((0.0, L.CD["at"], L.CD["top"] - 9.0 + 5.0 + L.DISC["thickness"] / 2 + 0.1))
        extra = [(cover, hinge), (media, seat)]
        nodes = {"lid": cover, "disc": media}
        timeline = timeline_cd
    else:
        cart = cartridge(m)
        seat = Vector((0.0, sum(L.SLOT["y"]) / 2, L.FRAME["top"] - L.CART["seat_depth"]))
        extra = [(cart, seat)]
        nodes = {"cartridge": cart}
        timeline = timeline_jaguar
    whole = join(parts, kind)
    for obj in [whole, button, pad] + [p for p, _ in extra] + [p for p, _ in moving.values()]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new(f"{kind}_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    for part, where in [(button, button_at), (lit, lit_at)] + extra:
        part.parent = whole
        part.location = where
    (px, py), turn = L.PAD["at"], math.radians(L.PAD["turn"])
    pad.parent = whole
    pad.location = (px, py, 0.0)
    pad.rotation_euler = (0.0, 0.0, turn)
    for part, where in moving.values():
        part.parent = pad
        part.location = where
    nodes.update({"power": button, "power_light": lit, **{n: p for n, (p, _) in moving.items()}})

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(turn, 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in pad.data.vertices]
    if kind == "atarijaguarcd":
        points += [tilt @ Matrix.Translation(hinge) @ v.co for v in cover.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, button, lit, pad] + [p for p, _ in extra] + [p for p, _ in moving.values()]
    print(f"{kind}: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
