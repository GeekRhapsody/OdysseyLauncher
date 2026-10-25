"""The console theme's Atari 5200 system model (godot/themes/console/models/systems/atari5200.glb): an Atari 5200, the
four-port model, and its controller.

Built in Blender from the real console's proportions (atari5200_layout.py has the measurements, taken from
photographs). The console is its side outline extruded across its width (the top sloping up from the front face to the
back, the undercut along its sides), a narrower block under its back; the vents and the cartridge slot are cut into its
top, the ports' panel and the ports into its front face; the brushed band lies on the top, POWER ON/OFF stands beside
it. The controller is a wedge tapering to its front, the stick's well and the keypad's panel cut into its top, the keys,
START, PAUSE and RESET on it, the red fire buttons in its sides, the stick in its rubber boot. The printing is one
texture drawn by atari5200_print.py: the top along its slope, the front face, the controller's top (planar-mapped onto
their faces), the cartridge's label, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the cartridge (waiting in its slot, shrunk to nothing), POWER ON/OFF, the lit power light (shrunk to nothing),
and the controller; the controller holding its stick, START and a fire button.

The `focused` clip (8 s, looping) plays a cartridge: it drops into the slot, POWER goes in and the light comes on; START
is pressed and the game is played on the stick and the fire button. Then POWER again, the light goes out, and the
cartridge rises out and goes.

Four materials (case, key, black, print) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/atari5200_print.py artifacts/atari5200
    blender -b --factory-startup --python tools/console-models/atari5200.py -- artifacts/atari5200 godot/themes/console/models/systems/atari5200.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari5200_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.45, key=0.5, black=0.7, print=0.45)

# The top's frame: x across, s up the slope from its front edge, h off it.
TOP_FRAME = Matrix.Translation((0.0, L.TOP[0][0], L.TOP[0][1])) @ Matrix.Rotation(L.SLOPE, 4, "X")
UP = TOP_FRAME.to_3x3() @ Vector((0.0, 0.0, 1.0))      # out of the top, in the model's frame
P = L.PAD
# The controller's top frame: x across, y back from its front end, h off its sloping top; its origin at its front end.
PAD_SLOPE = math.atan2(P["height"][1] - P["height"][0], P["length"])
PAD_TOP = Matrix.Translation((0.0, -P["length"] / 2, P["height"][0])) @ Matrix.Rotation(PAD_SLOPE, 4, "X")


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.TOP_LENGTH)
FRONT = atlas_uv(L.REGIONS["front"], L.WIDTH, L.TOP[0][1])
PAD_FACE = atlas_uv(L.REGIONS["pad"], P["width"][1], P["length"])
TOP_INVERSE = TOP_FRAME.inverted()
PAD_INVERSE = PAD_TOP.inverted()


def top_uv(co):
    local = TOP_INVERSE @ co
    return TOP(local.x + L.WIDTH / 2, L.TOP_LENGTH - local.y)


def front_uv(co):
    return FRONT(co.x + L.WIDTH / 2, L.TOP[0][1] - co.z)


def pad_uv(co):
    local = PAD_INVERSE @ co
    return PAD_FACE(local.x + P["width"][1] / 2, P["length"] - local.y)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def on_frame(frame, name, outline, h0, h1, mat):
    """A solid from an (x, s) outline in a frame, from h0 to h1 off it."""
    return solid(name, [[frame @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def rect(x0, x1, s0, s1):
    return [(x0, s0), (x1, s0), (x1, s1), (x0, s1)]


def facing_up(c, n, name):
    return n.dot(UP) > 0.97 and name == "case"


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The console: its outline extruded, the block under its back, the vents, the slot, the ports' panel and the
    ports cut into it; its top and front printed; the brushed band on its top."""
    w = L.WIDTH
    shell = prism_x("atari5200", L.PROFILE, -w / 2, w / 2, m["case"])
    bevel(shell, 1.5, segments=2)
    v = L.FRONT_VENTS
    slots = []
    x = v["x"][0] + v["pitch"] / 2
    while x < v["x"][1]:
        slots.append(on_frame(TOP_FRAME, "vent", rect(x - v["width"] / 2, x + v["width"] / 2, *v["s"]), -v["depth"], 5.0,
                              m["black"]))
        x += v["pitch"]
    for block in L.SLOT_VENTS:
        x = block["x"][0] + v["pitch"] / 2
        while x < block["x"][1]:
            slots.append(on_frame(TOP_FRAME, "vent", rect(x - v["width"] / 2, x + v["width"] / 2, *L.SLOT_VENT_S),
                                  -v["depth"], 5.0, m["black"]))
            x += v["pitch"]
    boolean(shell, join(slots, "vents"))
    (sx0, sx1), (ss0, ss1) = L.SLOT["x"], L.SLOT["s"]
    boolean(shell, on_frame(TOP_FRAME, "slot", rect(sx0, sx1, ss0, ss1), -L.SLOT["depth"], 5.0, m["black"]))
    (px0, px1), (pz0, pz1) = L.PORT_PANEL["x"], L.PORT_PANEL["z"]
    boolean(shell, box("panel", px0, px1, -5.0, L.PORT_PANEL["depth"], pz0, pz1, m["case"]))
    pw, ph = L.PORTS["size"]
    z = L.PORTS["z"]
    boolean(shell, join([box("port", x - pw / 2 + 1.0, x + pw / 2 - 1.0, -5.0, L.PORT_PANEL["depth"] + 4.0, z - ph / 2 + 1.0,
                             z + ph / 2 - 1.0, m["black"]) for x in L.PORTS["x"]], "ports"))
    paint(shell, m["print"], top_uv, facing_up)
    paint(shell, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and c.y < 8.0)
    (bx0, bx1), (by0, by1) = L.BLOCK["x"], L.BLOCK["y"]
    # Its top rises into the slab's underside at the back, and stays under the sloping top at its front.
    block = prism_x("block", [(by0, 0.0), (by1, 0.0), (by1, L.UNDER + 0.5), (by0, L.UNDER - 0.5)], bx0, bx1, m["case"])
    bevel(block, 1.5, segments=2)

    (sx0, sx1), (ss0, ss1), r = L.SILVER["x"], L.SILVER["s"], L.SILVER["raised"]
    band = on_frame(TOP_FRAME, "band", rect(sx0 + 1.6, sx1, ss0, ss1), -0.5, r, m["print"])
    paint(band, m["print"], top_uv, lambda c, n, name: n.dot(UP) > 0.97)
    paint(band, m["print"], swatch("silver"), lambda c, n, name: n.dot(UP) <= 0.97)
    return [shell, block, band]


def power(m):
    (x0, x1), (s0, s1) = L.POWER["x"], L.POWER["s"]
    part = on_frame(TOP_FRAME, "power", rect(x0, x1, s0, s1), -1.5, L.POWER["height"], m["key"])
    bevel(part, 0.8, segments=2)
    paint(part, m["print"], top_uv, lambda c, n, name: n.dot(UP) > 0.97)
    return part


def light(m):
    """The lit power light, its middle at its origin."""
    r = L.LIGHT["r"]
    ring = [(r * math.cos(2 * math.pi * k / 16), r * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    part = solid("light", [[(x, y, h) for x, y in ring] for h in (-0.2, 0.3)], m["print"])
    paint(part, m["print"], swatch("red_lit"), lambda c, n, name: True)
    middle = TOP_FRAME @ Vector((L.LIGHT["x"], L.LIGHT["s"], 0.0))
    part.data.transform(TOP_FRAME.to_3x3().to_4x4())
    return part, middle


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, standing up out of the top: its shell, the grooves along its
    ends, its label on its front."""
    w, d, h = L.CART["size"]
    lw, lh = L.CART["label"]
    shell = box("cartridge", -w / 2, w / 2, -d / 2, d / 2, 0.0, h, m["black"])
    bevel(shell, 1.5, segments=2)
    pitch = (h - 16.0) / L.CART["ribs"]
    for side in (-1, 1):
        a, b = (w / 2 - 2.0, w / 2 + 5.0) if side > 0 else (-w / 2 - 5.0, -w / 2 + 2.0)
        boolean(shell, join([box("groove", a, b, -d / 2 - 1.0, d / 2 + 1.0, 8.0 + k * pitch, 8.0 + k * pitch + pitch / 2,
                                 m["black"]) for k in range(L.CART["ribs"])], "grooves"))
    z1 = h - 8.0
    decal = box("label", -lw / 2, lw / 2, -d / 2 - 0.2, -d / 2 + 0.3, z1 - lh, z1, m["print"])
    face = atlas_uv(L.REGIONS["label"], lw, lh)
    paint(decal, m["print"], lambda co: face(co.x + lw / 2, z1 - co.z), lambda c, n, name: n.y < -0.9)
    paint(decal, m["print"], swatch("silver"), lambda c, n, name: n.y >= -0.9)
    part = join([shell, decal], "cartridge")
    part.data.transform(TOP_FRAME.to_3x3().to_4x4())
    return part


# ---- The controller --------------------------------------------------------------------------------------------------

def outline():
    """The controller's plan, anticlockwise from its front left: its front end narrower, its corners rounded."""
    (w0, w1), length = P["width"], P["length"]
    r = 7.0
    corners = [(-w0 / 2, 0.0), (w0 / 2, 0.0), (w1 / 2, length), (-w1 / 2, length)]
    points = []
    for k, (cx, cy) in enumerate(corners):
        a0 = (225 + 90 * k) % 360
        ox = cx + (r if cx < 0 else -r)
        oy = cy + (r if cy < length / 2 else -r)
        for j in range(4):
            a = math.radians(a0 - 45 + 90 * j / 3)
            points.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return points


def controller(m):
    """The controller in its own frame (its plan's middle at the origin, the table): its wedge, the stick's well and
    the keypad's panel cut into its top, the keys and the buttons; the stick, START and the right fire button apart."""
    (h0, h1), length = P["height"], P["length"]
    plan = outline()
    rings = [[(x, y - length / 2, 0.0) for x, y in plan],
             [(x, y - length / 2, h0 + (h1 - h0) * y / length) for x, y in plan]]
    body = solid("controller", rings, m["case"])
    bevel(body, 2.5, segments=2)
    wy, wr = L.WELL["y"], L.WELL["r"]
    well = [(wr * math.cos(2 * math.pi * k / 32), wy + wr * math.sin(2 * math.pi * k / 32)) for k in range(32)]
    boolean(body, on_frame(PAD_TOP, "well", well, -L.WELL["depth"], 5.0, m["black"]))
    (ky0, ky1), (kx0, kx1) = L.KEYPAD["y"], L.KEYPAD["x"]
    kw, kd = L.KEYPAD["key"]
    boolean(body, on_frame(PAD_TOP, "keypad", rect(kx0 - kw / 2 - 3.0, kx1 + kw / 2 + 3.0, ky0 - 2.0, ky1 + 2.0), -1.5,
                           5.0, m["black"]))
    (by0, by1) = L.TOP_BUTTONS["y"]
    boolean(body, on_frame(PAD_TOP, "strip", rect(-32.0, 32.0, by0 - 1.5, by1 + 1.5), -1.5, 5.0, m["black"]))
    paint(body, m["print"], pad_uv, lambda c, n, name: n.z > 0.95 and name == "case")
    parts = [body]
    rows, cols = L.KEYPAD["rows"], L.KEYPAD["cols"]
    for i in range(rows):
        for j in range(cols):
            x = kx0 + (kx1 - kx0) * j / (cols - 1)
            y = ky1 - kd / 2 - (ky1 - ky0 - kd) * i / (rows - 1)
            k = on_frame(PAD_TOP, "key", rect(x - kw / 2, x + kw / 2, y - kd / 2, y + kd / 2), -1.5, L.KEYPAD["height"],
                         m["key"])
            bevel(k, 0.6, segments=1)
            parts.append(k)
    for x0, x1 in L.TOP_BUTTONS["x"][1:]:
        b = on_frame(PAD_TOP, "button", rect(x0, x1, by0, by1), -1.5, L.TOP_BUTTONS["height"], m["key"])
        bevel(b, 0.4, segments=1)
        parts.append(b)
    for part in parts[1:]:
        paint(part, m["print"], pad_uv, lambda c, n, name: n.z > 0.95)
    (fz0, fz1), out = L.FIRE["z"], L.FIRE["out"]
    for side in (-1, 1):
        for y0, y1 in L.FIRE["y"]:
            if side > 0 and (y0, y1) == L.FIRE["y"][1]:
                continue                                       # the clip's: apart
            parts.append(fire_button(side, y0, y1, fz0, fz1, out, m))
    shell = join(parts, "controller")

    (x0, x1) = L.TOP_BUTTONS["x"][0]
    start = on_frame(PAD_TOP, "start", rect(x0, x1, by0, by1), -1.5, L.TOP_BUTTONS["height"], m["key"])
    bevel(start, 0.4, segments=1)
    paint(start, m["print"], pad_uv, lambda c, n, name: n.z > 0.95)
    y0, y1 = L.FIRE["y"][1]
    fire = fire_button(1, y0, y1, fz0, fz1, out, m)
    return shell, start, fire, stick(m)


def fire_button(side, y0, y1, z0, z1, out, m):
    """A red fire button standing out of the controller's side (side -1 the left, 1 the right)."""
    (w0, w1), length = P["width"], P["length"]
    half = (w0 + (w1 - w0) * ((y0 + y1) / 2) / length) / 2
    a, b = (half - 1.0, half + out) if side > 0 else (-half - out, -half + 1.0)
    part = box("fire", a, b, y0 - length / 2, y1 - length / 2, z0, z1, m["print"])
    bevel(part, 0.6, segments=1)
    paint(part, m["print"], swatch("red"), lambda c, n, name: True)
    return part


def stick(m):
    """The stick, its foot's middle at its origin: the rubber boot, the shaft tapering up, its domed top."""
    (b0, b1), (r0, r1), length = L.STICK["boot"], L.STICK["r"], L.STICK["length"]

    def ring(r, z, n=24):
        return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), z) for k in range(n)]
    boot = solid("boot", [ring(b0, -1.0), ring(b0 * 0.85, 4.0), ring(b1 + 1.0, 9.0), ring(b1, 11.0)], m["black"])
    shaft = solid("shaft", [ring(r0, 8.0), ring(r1, 8.0 + length), ring(r1 * 0.8, 10.0 + length),
                            ring(r1 * 0.4, 11.0 + length)], m["key"])
    for p in shaft.data.polygons:
        p.use_smooth = True
    return join([boot, shaft], "stick")


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


RISE = 90.0          # how far up its slot the cartridge appears


def along(d):
    """A Pose moving d along the slot (out of the top)."""
    return dict(x=UP.x * d, y=UP.y * d, z=UP.z * d)


def timeline(f):
    if f < 6 or f >= 228:
        cart = Pose(scale=HIDDEN)
    elif f < 16:
        cart = Pose(**along(RISE), scale=appear(f, 6, 14))
    elif f < 28:
        cart = Pose(**along(RISE * (1 - ease_in(phase(f, 16, 28)))))
    elif f < 206:
        cart = Pose(squash=0.04 * math.sin(math.pi * phase(f, 28, 34)))
    else:
        cart = Pose(**along(RISE * ease_out(phase(f, 206, 218))), scale=max(HIDDEN, 1 - ease_in(phase(f, 216, 228))))
    press = max(tap(f, 36), tap(f, 198))
    t = phase(f, 64, 186)
    k = math.sin(math.pi * t)
    return {"cartridge": cart, "power": Pose(**along(-2.0 * press)),
            "power_light": Pose() if 40 <= f < 200 else Pose(scale=HIDDEN),
            "start": Pose(z=-1.4 * tap(f, 52)),
            "stick": Pose(pitch=20.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=20.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "fire": Pose(x=-2.0 * max(tap(f, f0) for f0 in (84, 104, 124, 144, 164)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "atari5200_print.png"))
    colours = dict(L.COLOURS)
    m = {n: material(n, colours[n], r, printed if n == "print" else None) for n, r in ROUGHNESS.items()}

    whole = join(console(m), "atari5200")
    button = power(m)
    lit, lit_at = light(m)
    cart = cartridge(m)
    pad, start, fire, joystick = controller(m)
    for obj in [whole, button, cart, pad, start, fire, joystick]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("atari5200_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    (sx0, sx1), (ss0, ss1) = L.SLOT["x"], L.SLOT["s"]
    seat = TOP_FRAME @ Vector(((sx0 + sx1) / 2, (ss0 + ss1) / 2, -L.CART["seat_depth"]))
    for part, where in ((cart, seat), (lit, lit_at)):
        part.parent = whole
        part.location = where
    button.parent = whole
    (px, py), turn = P["at"], math.radians(P["turn"])
    pad.parent = whole
    pad.location = (px, py, 0.0)
    pad.rotation_euler = (0.0, 0.0, turn)
    stick_at = PAD_TOP @ Vector((0.0, L.WELL["y"], -L.WELL["depth"]))
    joystick.parent = pad
    joystick.location = stick_at
    for part in (start, fire):
        part.parent = pad
    nodes = {"cartridge": cart, "power": button, "power_light": lit, "start": start, "stick": joystick, "fire": fire}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    rest = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(turn, 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices] + [tilt @ rest @ v.co for v in pad.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, button, lit, cart, pad, start, fire, joystick]
    print(f"Atari 5200: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
