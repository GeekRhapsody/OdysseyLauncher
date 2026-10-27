"""The console theme's V.Smile system model (godot/themes/console/models/systems/vsmile.glb): VTech's V.Smile TV Learning
System and its controller.

Built in Blender from the real console's proportions (vsmile_layout.py has the measurements, from photographs). The
body is rings of its lobed squircle outline, brought in at its foot and its top so that its sides round over, cut for
the pocket at its top's front edge; it stands on four round feet; the smoked lid is a low dome on its top, RESTART
stands at the front left, ON stands out of the band. The Smartridge is its wavy-topped outline made solid. The
controller lies in front of the console: the pad (its outline the circle with its toes, through a rounded profile), the
coloured domes on the toes, ENTER in its silver ring; the joystick base (its outline ribbed) joined to it, the stick's
neck and ball; its cord to PLAYER 1, a mini-DIN plug in the port (plugs.din). The printing is one texture drawn by
vsmile_print.py (the console from above and from the front; the Smartridge's face; the controller from above;
swatches).

A node tree (card.finish()): the root holding the set; the set holding the Smartridge (waiting in the pocket, shrunk to
nothing), ON, and the controller's stick, ENTER and its four coloured buttons.

The `focused` clip (8 s, looping) plays a game: the Smartridge (a made-up game) appears over the pocket, turns once to
show its label and drops in; ON is pressed; ENTER, then the stick is played and the coloured buttons pressed in turn,
ENTER again; then the Smartridge rises out and goes.

Three materials (case, lid, cord) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/vsmile_print.py artifacts/made-up-games artifacts/vsmile
    blender -b --factory-startup --python tools/console-models/vsmile.py -- artifacts/vsmile godot/themes/console/models/systems/vsmile.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plugs  # noqa: E402
import vsmile_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe, tube  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.35, lid=0.12, cord=0.5)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
P = L.PAD
PAD_FRAME = Matrix.Translation((*P["at"], 0.0)) @ Matrix.Rotation(math.radians(P["turn"]), 4, "Z")


def span_uv(region, span):
    x0, x1, y0, y1 = span
    uv = ATLAS.uv(region, x1 - x0, y1 - y0)
    return lambda a, b: uv(a - x0, y1 - b)


TOP = span_uv("top", L.TOP_SPAN)
FRONT = span_uv("front", L.FRONT_SPAN)
PAD_UV = span_uv("pad", L.PAD_SPAN)


def top_uv(co):
    return TOP(co.x, co.y)


def front_uv(co):
    return FRONT(co.x, co.z)


def pad_uv(co):
    return PAD_UV(co.x, co.y)


# ---- The console -----------------------------------------------------------------------------------------------------

def in_pocket(c):
    p = L.POCKET
    return abs(c.x) < p["x"] + 0.5 and c.y > p["y"][0] and c.z > p["floor"] - 0.5


def body(m):
    """The body: its outline's rings up its rounded sides; the pocket cut into its top's front edge; the band and the
    top printed."""
    part = solid("vsmile", [[(x, y, z) for x, y in L.outline(d)] for z, d in L.PROFILE], m["case"])
    p = L.POCKET
    boolean(part, box("pocket", -p["x"], p["x"], *p["y"], p["floor"], L.TOP + 10.0, m["case"]))
    coloured(part, m["case"], ATLAS, "orange")
    paint(part, m["case"], front_uv, lambda c, n, kind: n.y < -0.3 and n.z < 0.9 and not in_pocket(c))
    paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.9)
    paint(part, m["case"], ATLAS.swatch("band"), lambda c, n, kind: n.z < -0.9)
    return part


def feet(m):
    r0, r1 = L.FOOT["r"]
    h = L.FOOT["height"]
    out = []
    for x, y in L.FOOT["at"]:
        foot = lathe("foot", [(0.0, 0.0), (r0 - 1.0, 0.0), (r0, 1.5), (r0 - 2.0, 5.0), (r1, 10.0), (r1 - 0.5, h),
                              (0.0, h)], m["case"], 28)
        foot.data.transform(Matrix.Translation((x, y, 0.0)))
        out.append(coloured(smoothed(foot, 50.0), m["case"], ATLAS, "band"))
    return out


def lid(m):
    """The smoked lid, a low dome over the storage, printed with its ripples."""
    x0, x1, y0, y1 = L.LID["rect"]
    r = L.LID["r"]
    dz, din = L.LID["dome"]
    rings = []
    for z, d in ((L.TOP - 0.5, 0.0), (L.TOP + dz * 0.7, 0.8), (L.TOP + dz, din)):
        rings.append([(x, y, z) for x, y in rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 2 * d, y1 - y0 - 2 * d,
                                                    r - d, 6)])
    part = solid("lid", rings, m["lid"])
    paint(part, m["lid"], top_uv, lambda c, n, kind: True)
    return smoothed(part, 30.0)


def restart(m):
    x, y = L.RESTART["at"]
    part = lathe("restart", [(0.0, L.TOP - 0.6), (L.RESTART["r"], L.TOP - 0.6),
                             (L.RESTART["r"], L.TOP + L.RESTART["height"] - 0.8),
                             (L.RESTART["r"] - 1.0, L.TOP + L.RESTART["height"]), (0.0, L.TOP + L.RESTART["height"])],
                 m["case"], 24)
    part.data.transform(Matrix.Translation((x, y, 0.0)))
    coloured(part, m["case"], ATLAS, "restart")
    paint(part, m["case"], top_uv, lambda c, n, kind: n.z > 0.9)
    return part


def on_button(m):
    """ON, standing out of the band, its middle at its origin, printed from the front."""
    x, z = L.ON_OFF["x"], L.ON_OFF["z"][0]
    y = L.front_y(x)
    r = L.ON_OFF["r"]
    ring = [(x + r * math.cos(2 * math.pi * k / 20), z + r * math.sin(2 * math.pi * k / 20)) for k in range(20)]
    part = solid("on", [[(px, yy, pz) for px, pz in ring] for yy in (y + 2.0, y - 1.6)], m["case"])
    coloured(part, m["case"], ATLAS, "blue")
    paint(part, m["case"], front_uv, lambda c, n, kind: n.y < -0.9)
    at = Vector((x, y, z))
    part.data.transform(Matrix.Translation(-at))
    return part, at


def smartridge(m):
    """The Smartridge: its outline (the wavy top's three scallops, the narrower tongue) made solid, standing, its face
    to the front, its bottom's middle at its origin."""
    w, t, h = L.CART["size"]
    top = [(w / 2 - w * k / 24, h - L.CART["scallop"] + L.CART["scallop"] * (0.5 + 0.5 * math.cos(6 * math.pi * k / 24)))
           for k in range(25)]
    shape = [(-w / 2 + 7.0, 0.0), (w / 2 - 7.0, 0.0), (w / 2 - 7.0, 6.0), (w / 2, 9.0)] + top + [(-w / 2, 9.0),
                                                                                              (-w / 2 + 7.0, 6.0)]
    part = solid("smartridge", [[(x, y, z) for x, z in shape] for y in (-t / 2, t / 2)], m["case"])
    bevel(part, 0.8, segments=2, angle=50)
    face = ATLAS.uv("face", w, h + 3.0)
    coloured(part, m["case"], ATLAS, "purple")
    paint(part, m["case"], lambda co: face(co.x + w / 2, h + 3.0 - co.z), lambda c, n, kind: n.y < -0.9)
    return part


# ---- The controller --------------------------------------------------------------------------------------------------

def pad_outline(n=96):
    """The pad's plan: its round body and its four toes, each ray's furthest crossing."""
    out = []
    toes = [(P["toe_at"] * math.cos(math.radians(a)), P["toe_at"] * math.sin(math.radians(a))) for a, _ in P["toes"]]
    for k in range(n):
        t = 2 * math.pi * k / n
        u = (math.cos(t), math.sin(t))
        r = P["r"]
        for cx, cy in toes:
            b = cx * u[0] + cy * u[1]
            disc = P["toe_r"] ** 2 - (cx * cx + cy * cy - b * b)
            if disc > 0:
                r = max(r, b + math.sqrt(disc))
        out.append((r * u[0], r * u[1]))
    return out


def profiled(name, outline, h, mat, profile=((0.0, 4.0), (0.08, 1.0), (0.25, 0.0), (0.75, 0.0), (0.9, 2.5),
                                            (1.0, 6.0))):
    def moved(d):
        return [(x - d * x / math.hypot(x, y), y - d * y / math.hypot(x, y)) for x, y in outline]
    return solid(name, [[(x, y, h * z) for x, y in moved(d)] for z, d in profile], mat)


def controller(m):
    """The controller in its own frame: the pad, the joystick base and the bridge, the coloured domes' places; the
    moving parts apart."""
    h = P["height"]
    pad = profiled("pad", pad_outline(), h, m["case"])
    coloured(pad, m["case"], ATLAS, "band")
    paint(pad, m["case"], pad_uv, lambda c, n, kind: n.z > 0.9)
    sx, sy, sr = P["stick"]
    ribbed = [(sr * (1.0 if k % 2 else 0.975) * math.cos(2 * math.pi * k / 72),
               sr * (1.0 if k % 2 else 0.975) * math.sin(2 * math.pi * k / 72)) for k in range(72)]
    base = profiled("base", ribbed, h - 4.0, m["case"], ((0.0, 3.0), (0.12, 0.0), (0.7, 0.0), (0.88, 4.0), (1.0, 12.0)))
    base.data.transform(Matrix.Translation((sx, sy, 0.0)))
    coloured(base, m["case"], ATLAS, "orange")
    paint(base, m["case"], pad_uv, lambda c, n, kind: n.z > 0.9)
    bridge = box("bridge", 34.0, sx - sr + 6.0, -P["bridge"], P["bridge"], 2.0, h - 9.0, m["case"])
    bevel(bridge, 3.0, segments=2)
    coloured(bridge, m["case"], ATLAS, "orange")
    ring = lathe("ring", [(0.0, h - 1.5), (P["enter"][1], h - 1.5), (P["enter"][1], h + 0.6),
                          (P["enter"][0] + 0.5, h + 1.0), (0.0, h + 1.0)], m["case"], 40)
    coloured(ring, m["case"], ATLAS, "silver")
    parts = [pad, base, bridge, ring]
    for (x, y), _ in zip(P["small"], range(3)):
        b = lathe("small", [(0.0, h - 1.0), (4.6, h - 1.0), (4.6, h + 0.8), (3.8, h + 1.4), (0.0, h + 1.4)], m["case"],
                  20)
        b.data.transform(Matrix.Translation((x, y, 0.0)))
        coloured(b, m["case"], ATLAS, "band")
        paint(b, m["case"], pad_uv, lambda c, n, kind: n.z > 0.9)
        parts.append(b)

    moving = {}
    enter = lathe("enter", [(0.0, -1.0), (P["enter"][0], -1.0), (P["enter"][0], 2.0), (P["enter"][0] - 1.5, 3.2),
                            (0.0, 3.6)], m["case"], 40)
    coloured(enter, m["case"], ATLAS, "orange")
    enter.data.transform(Matrix.Translation((0.0, 0.0, h)))
    paint(enter, m["case"], pad_uv, lambda c, n, kind: n.z > 0.6)
    enter.data.transform(Matrix.Translation((0.0, 0.0, -h)))
    moving["enter"] = (enter, Vector((0.0, 0.0, h)))
    for a, colour in P["toes"]:
        x, y = P["toe_at"] * math.cos(math.radians(a)), P["toe_at"] * math.sin(math.radians(a))
        r = P["button_r"]
        dome = lathe(colour, [(0.0, -2.0), (r, -2.0), (r, 1.0)] + [(r * math.cos(math.pi / 2 * k / 5),
                                                                       1.0 + 4.0 * math.sin(math.pi / 2 * k / 5))
                                                                      for k in range(1, 6)], m["case"], 24)
        moving["toe_" + colour] = (coloured(dome, m["case"], ATLAS, colour), Vector((x, y, h - 1.0)))
    nr, nh = P["neck"]
    stick = lathe("stick", [(0.0, -4.0), (nr + 3.0, -4.0), (nr, 3.0), (nr, nh)], m["case"], 24)
    coloured(stick, m["case"], ATLAS, "orange")
    ball = lathe("ball", [(P["ball"] * math.sin(math.pi * k / 10), nh + P["ball"] * (0.85 - math.cos(math.pi * k / 10)))
                          for k in range(11)], m["case"], 24)
    coloured(ball, m["case"], ATLAS, "band")
    moving["stick"] = (join([stick, ball], "stick"), Vector((sx, sy, h - 6.0)))
    return join(parts, "controller"), moving


def cord(m):
    """The controller's cord from the pad's top to PLAYER 1, a mini-DIN plug in the port."""
    start = PAD_FRAME @ Vector((0.0, 53.0, P["height"] * 0.5))   # between the two middle toes
    out = PAD_FRAME.to_3x3() @ Vector((0.0, 1.0, 0.0))
    pad_parts, pad_end, pad_dir = plugs.place(*plugs.grommet(lambda o: o, r=3.4), m["cord"], start, out)
    x = L.PORTS["x"][0]
    port = Vector((x, L.front_y(x), L.PORTS["z"]))
    con_parts, con_end, con_dir = plugs.place(*plugs.din(lambda o: o, lambda o: o, r=5.5), m["cord"], port,
                                              (0.0, -1.0, 0.0))
    path = [pad_end, pad_end + pad_dir * 10.0, Vector((-100.0, -36.0, 2.4)), Vector((-82.0, -20.0, 2.4)),
            con_end + con_dir * 10.0 + Vector((0.0, 0.0, -8.0)), con_end + con_dir * 3.0, con_end]
    wire = tube("cord", curve(path, 5), 2.0, m["cord"], 10)
    return pad_parts + con_parts + [smoothed(wire, 50.0)]


# ---- The focused clip ------------------------------------------------------------------------------------------------

ABOVE = 52.0                 # how far over its seat the Smartridge appears: wholly over the top


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def timeline(f):
    if f < 6 or f >= 222:
        cart = Pose(scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=ABOVE, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 15)))
    elif f < 32:
        cart = Pose(z=ABOVE + 6.0 * math.sin(math.pi * phase(f, 16, 32)), spin=360.0 * smooth(phase(f, 16, 32)))
    elif f < 44:
        cart = Pose(z=ABOVE * (1 - ease_in(phase(f, 32, 44))))
    elif f < 198:
        cart = Pose(z=1.4 * math.exp(-(f - 44) / 3.0) * abs(math.sin(math.pi * (f - 44) / 5.0)))
    elif f < 212:
        cart = Pose(z=ABOVE * ease_out(phase(f, 198, 212)))
    else:
        cart = Pose(z=ABOVE, scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    poses = {"smartridge": cart, "on": Pose(y=1.4 * tap(f, 50, 3)), "enter": Pose(z=-2.0 * max(tap(f, 62, 3),
                                                                                                tap(f, 176, 3)))}
    t = phase(f, 74, 168)
    wave = math.sin(math.pi * t)
    poses["stick"] = Pose(pitch=18.0 * math.sin(2 * math.pi * 3 * t) * wave,
                          roll=20.0 * math.sin(2 * math.pi * 2 * t + 0.8) * wave)
    for k, (_, colour) in enumerate(P["toes"]):
        poses["toe_" + colour] = Pose(z=-2.2 * max(tap(f, 84 + 18 * k), tap(f, 156 - 6 * k)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    image = bpy.data.images.load(os.path.join(images, "vsmile_print.png"))
    m = materials(dict(case="#FFFFFF", lid="#FFFFFF", cord=L.COLOURS["cord"]), ROUGHNESS, dict(case=image, lid=image))

    pad, pad_moving = controller(m)
    pad.data.transform(PAD_FRAME)
    whole = smoothed(join([body(m), lid(m), restart(m), pad] + feet(m) + cord(m), "vsmile"), 40.0)
    button, button_at = on_button(m)
    seat = Vector((*L.CART["at"], L.POCKET["floor"]))
    parts = {"smartridge": (smoothed(smartridge(m)), seat), "on": (button, button_at)}
    turn = PAD_FRAME.to_3x3().to_4x4()
    for name, (part, at) in pad_moving.items():
        part.data.transform(turn)
        parts[name] = (smoothed(part, 50.0), PAD_FRAME @ at)
    finish("vsmile", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "V.Smile")


if __name__ == "__main__":
    main()
