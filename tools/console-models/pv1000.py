"""The console theme's PV-1000 system model (godot/themes/console/models/systems/pv1000.glb): Casio's PV-1000 and its
TJ-1 joystick.

Built in Blender from the real console's proportions (pv1000_layout.py has the measurements, taken from photographs).
The console is three solids: the slab, its front corners rounded in plan, cut for the slot's opening, the sockets'
recessed strip and the two sockets in its front, the power switch's oval recess in its right end; the raised deck on it,
rings of its half-ellipse outline down its wall and round its concave fillet, cut for the slot's recess and opening; and
the back strip, the back block with its coves falling to the slab at its ends, corrugated by ribs standing over an inset
core. The TJ-1 lies in front of the console's left end: its base, ribbed round its sides (every other point of its
outline set in), chamfered to its printed top; the domed collar and the tall ribbed stick (turned), the red button on
it; START and SELECT; its cord to the left socket, a mini-DIN plug in it (plugs.din). The printing is one texture drawn
by pv1000_print.py (the console's top from above; the game pack's labels; the joystick's top; swatches).

A node tree (card.finish()): the root holding the set; the set holding the game pack (waiting in the slot, shrunk to
nothing), the power switch's rocker, the power light (shrunk to nothing), the stick and the red button on it, START.

The `focused` clip (8 s, looping) plays a game: the game pack (a made-up game) appears over the slot, turns once to show
its label and drops into the slot; the rocker goes over and the power light comes on; START, then the stick waggles and
the red button is pressed; then the rocker goes back, the light goes off and the game pack rises out and goes.

Three materials (case, dark, cable) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/pv1000_print.py artifacts/made-up-games artifacts/pv1000
    blender -b --factory-startup --python tools/console-models/pv1000.py -- artifacts/pv1000 godot/themes/console/models/systems/pv1000.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plugs  # noqa: E402
import pv1000_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe, tube  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end (the power switch) comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, dark=0.7, cable=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
TOP = ATLAS.uv("top", L.WIDTH, L.DEPTH)
JOY_UV = ATLAS.uv("joy_top", 2 * L.JOY["r"], L.JOY["length"])
JOY_FRAME = Matrix.Translation((*L.JOY["at"], 0.0)) @ Matrix.Rotation(math.radians(L.JOY["turn"]), 4, "Z")


def top_uv(co):
    return TOP(co.x + L.HALF, L.DEPTH - co.y)


# ---- The console -----------------------------------------------------------------------------------------------------

def slab(m):
    """The slab: its front corners rounded in plan, its back square (the back strip stands behind it); cut for the
    sockets' strip and the sockets, the switch's recess and the slot's opening."""
    r = L.CORNER
    back = L.DECK["back"]
    outline = ([(L.HALF, back)]
               + [(L.HALF - r + r * math.cos(math.radians(-90.0 * k / 6)), r + r * math.sin(math.radians(-90.0 * k / 6)))
                  for k in range(7)]
               + [(-L.HALF + r + r * math.cos(math.radians(-90.0 - 90.0 * k / 6)),
                   r + r * math.sin(math.radians(-90.0 - 90.0 * k / 6))) for k in range(7)]
               + [(-L.HALF, back)])
    part = solid("slab", [[(x, y, z) for x, y in outline] for z in (0.0, L.SLAB)], m["case"])
    bevel(part, 1.2, segments=2)
    st = L.STRIP
    boolean(part, box("strip", -st["x"], st["x"], -2.0, st["depth"], *st["z"], m["case"]))
    sockets = [solid("socket", [[(x + L.SOCKETS["r"] * math.cos(2 * math.pi * k / 16), y,
                                  L.SOCKETS["z"] + L.SOCKETS["r"] * math.sin(2 * math.pi * k / 16)) for k in range(16)]
                                for y in (-2.0, 14.0)], m["dark"]) for x in L.SOCKETS["x"]]
    boolean(part, join(sockets, "sockets"))
    sw = L.SWITCH
    oval = rounded(sum(sw["y"]) / 2, sum(sw["z"]) / 2, sw["y"][1] - sw["y"][0], sw["z"][1] - sw["z"][0],
                   (sw["z"][1] - sw["z"][0]) / 2 - 0.01, 6)
    boolean(part, solid("oval", [[(x, y, z) for y, z in oval] for x in (L.HALF - sw["depth"], L.HALF + 3.0)],
                        m["case"]))
    boolean(part, opening(m))
    paint(part, m["case"], ATLAS.swatch("case"), lambda c, n, name: name == "case")
    paint(part, m["case"], top_uv, lambda c, n, name: name == "case" and n.z > 0.9)
    return part


def opening(m):
    w, y0, y1 = L.SLOT["opening"]
    return box("opening", -w, w, y0, y1, 2.0, L.TOP + 6.0, m["dark"])


def deck(m):
    """The raised deck: its half-ellipse outline's rings down its wall and round its fillet; the slot's recess and
    opening cut into it."""
    rings = [[(x, y, z) for x, y in L.deck_ring(d)] for d, z in L.DECK_PROFILE]
    part = solid("deck", rings, m["case"])
    s = L.SLOT
    boolean(part, box("recess", -s["x"], s["x"], *s["y"], L.TOP - s["depth"], L.TOP + 5.0, m["case"]))
    boolean(part, opening(m))
    paint(part, m["case"], ATLAS.swatch("case"), lambda c, n, name: name == "case")
    paint(part, m["case"], top_uv, lambda c, n, name: name == "case" and n.z > 0.9)
    return part


def back_strip(m):
    """The back strip: an inset core and the ribs standing over it, each its section across its slice."""
    def prism(name, outline, y0, y1):
        return solid(name, [[(x, y, z) for x, z in outline] for y in (y0, y1)], m["case"])
    rb = L.RIBS
    grooves = [(rb["y0"] + k * rb["pitch"], rb["y0"] + k * rb["pitch"] + rb["groove"]) for k in range(rb["count"])]
    edges = [L.BACK["y0"]] + [y for g in grooves for y in g] + [L.DEPTH]
    parts = [prism("core", L.back_outline(rb["depth"]), L.BACK["y0"] + 0.5, L.DEPTH - 0.5)]
    parts += [prism("rib", L.back_outline(), edges[2 * k], edges[2 * k + 1]) for k in range(len(edges) // 2)]
    for part in parts:
        coloured(part, m["case"], ATLAS, "case")
        paint(part, m["case"], top_uv, lambda c, n, name: n.z > 0.9)
    return parts


def rocker(m):
    """The power switch's rocker, standing out of its oval recess, its middle at its origin."""
    w, h, out = L.SWITCH["rocker"]
    part = box("rocker", -1.0, out, -w / 2, w / 2, -h / 2, h / 2, m["dark"])
    bevel(part, 0.8, segments=2)
    at = Vector((L.HALF - L.SWITCH["depth"], sum(L.SWITCH["y"]) / 2, sum(L.SWITCH["z"]) / 2))
    return part, at


def light(m):
    part = solid("power_light", [[(L.LIGHT["r"] * math.cos(2 * math.pi * k / 12), L.LIGHT["r"] * math.sin(2 * math.pi * k / 12),
                                   z) for k in range(12)] for z in (-0.2, 0.25)], m["case"])
    coloured(part, m["case"], ATLAS, "lit")
    return part, Vector((L.LIGHT["x"], L.LIGHT["y"], L.SLAB))


def cartridge(m):
    """The game pack, standing, its label to the front, its bottom's middle at its origin."""
    w, h, t = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(part, 0.8, segments=2)
    front = ATLAS.uv("cart_front", w, h)
    end = ATLAS.uv("cart_top", w, t)
    coloured(part, m["case"], ATLAS, "cart")
    paint(part, m["case"], lambda co: front(co.x + w / 2, h - co.z), lambda c, n, name: n.y < -0.9)
    paint(part, m["case"], lambda co: end(co.x + w / 2, t / 2 - co.y), lambda c, n, name: n.z > 0.9)
    return part


# ---- The joystick ----------------------------------------------------------------------------------------------------

def joy_outline():
    """The base's outline, (point, normal) pairs about 2.5 mm apart, anticlockwise: its right side, the flat end's
    rounded corners, its left side, the half disc round the stick's end."""
    r, c = L.JOY["r"], L.JOY["corner"]
    end = L.JOY["length"] - r
    out = []

    def line(a, b, n):
        steps = max(1, round((Vector(b) - Vector(a)).length / 2.5))
        out.extend((Vector(a).lerp(Vector(b), k / steps), Vector(n)) for k in range(steps))

    def arc(cx, cy, rad, a0, a1):
        steps = max(2, round(abs(math.radians(a1 - a0)) * rad / 2.5))
        for k in range(steps):
            a = math.radians(a0 + (a1 - a0) * k / steps)
            out.append((Vector((cx + rad * math.cos(a), cy + rad * math.sin(a))), Vector((math.cos(a), math.sin(a)))))
    line((r, 0.0), (r, end - c), (1.0, 0.0))
    arc(r - c, end - c, c, 0.0, 90.0)
    line((r - c, end), (-r + c, end), (0.0, 1.0))
    arc(-r + c, end - c, c, 90.0, 180.0)
    line((-r, end - c), (-r, 0.0), (-1.0, 0.0))
    arc(0.0, 0.0, r, 180.0, 360.0)
    return out


def joy_base(m):
    """The base: its sides ribbed (every other point set in, but along the flat end), chamfered to its top."""
    j = L.JOY
    outline = joy_outline()
    end = j["length"] - j["r"] - j["corner"]

    def ring(z, inset, ribbed):
        return [(p.x - n.x * (inset + (j["ribs"] if ribbed and k % 2 and p.y < end else 0.0)),
                 p.y - n.y * (inset + (j["ribs"] if ribbed and k % 2 and p.y < end else 0.0)), z)
                for k, (p, n) in enumerate(outline)]
    part = solid("joystick", [ring(0.0, 0.6, False), ring(1.0, 0.0, True), ring(j["height"] - j["chamfer"], 0.0, True),
                              ring(j["height"], j["chamfer"], False)], m["case"])
    coloured(part, m["case"], ATLAS, "joy")
    paint(part, m["case"], lambda co: JOY_UV(co.x + j["r"], co.y + j["r"]), lambda c, n, name: n.z > 0.95)
    collar = lathe("collar", [(0.0, j["height"] - 1.0)] + list(L.STICK["collar"]) + [(0.0, L.STICK["collar"][-1][1])],
                   m["case"], 28)
    coloured(collar, m["case"], ATLAS, "joy")
    select = button(m, L.BUTTONS["select"])
    return [part, smoothed(collar, 50.0), select]


def button(m, at):
    x, y = at
    b = L.BUTTONS
    part = lathe("button", [(0.0, L.JOY["height"] - 1.0), (b["r"], L.JOY["height"] - 1.0),
                            (b["r"], L.JOY["height"] + b["height"] - 0.6), (b["r"] - 0.6, L.JOY["height"] + b["height"]),
                            (0.0, L.JOY["height"] + b["height"])], m["case"], 20)
    part.data.transform(Matrix.Translation((x, y, 0.0)))
    return coloured(part, m["case"], ATLAS, "button")


def stick(m):
    """The stick, ribbed all the way up, its rounded top; its origin at its pivot in the collar."""
    s = L.STICK
    z0, z1 = s["z"]
    profile = [(0.0, z0 - 6.0), (s["r"] - 1.0, z0 - 6.0)]
    z = z0
    while z < z1 - 0.01:
        profile += [(s["r"], z), (s["r"] - s["rib"], z + s["pitch"] / 2)]
        z += s["pitch"]
    profile += [(s["r"], z1), (s["r"] - 1.2, z1 + 2.4), (s["r"] - 4.0, z1 + 3.6), (0.0, z1 + 3.8)]
    part = lathe("stick", profile, m["case"], 20)
    coloured(part, m["case"], ATLAS, "joy")
    pivot = s["collar"][0][1] + 6.0
    part.data.transform(Matrix.Translation((0.0, 0.0, -pivot)))
    return part, pivot


def red_button(m):
    r, h = L.STICK["button"]
    part = lathe("fire", [(0.0, -1.0), (r, -1.0), (r, h - 1.6), (r - 1.6, h), (0.0, h)], m["case"], 20)
    return coloured(part, m["case"], ATLAS, "red")


def cable(m):
    """The joystick's cord, from its flat end to the left socket, a mini-DIN plug in it."""
    j = L.JOY
    start = JOY_FRAME @ Vector((6.0, j["length"] - j["r"], 9.0))
    out = JOY_FRAME.to_3x3() @ Vector((0.0, 1.0, 0.0))
    joy_parts, joy_end, joy_dir = plugs.place(*plugs.grommet(lambda o: coloured(o, m["case"], ATLAS, "joy"), r=3.6),
                                              m["case"], start, out)
    socket = Vector((L.SOCKETS["x"][0], 0.0, L.SOCKETS["z"]))
    con_parts, con_end, con_dir = plugs.place(*plugs.din(lambda o: o, lambda o: o, r=5.5), m["cable"], socket,
                                              (0.0, -1.0, 0.0))
    path = [joy_end, joy_end + joy_dir * 10.0, Vector((-52.0, -10.0, 2.4)), Vector((-40.0, -34.0, 2.4)),
            Vector((-22.0, -40.0, 3.0)), con_end + con_dir * 8.0 + Vector((0.0, 0.0, -2.0)), con_end + con_dir * 2.0,
            con_end]
    wire = tube("cord", curve(path, 5), 1.9, m["cable"], 10)
    return joy_parts + con_parts + [smoothed(wire, 50.0)]


# ---- The focused clip ------------------------------------------------------------------------------------------------

ABOVE = 72.0                 # how far over its seat the game pack appears


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
    on = smooth(phase(f, 50, 53)) * (1 - smooth(phase(f, 188, 191)))
    poses = {"cartridge": cart, "rocker": Pose(spin=2 * L.SWITCH["turn"] * on),
             "power_light": Pose() if 52 <= f < 190 else Pose(scale=HIDDEN),
             "start": Pose(z=-1.8 * tap(f, 58, 3))}
    t = phase(f, 66, 176)
    wave = math.sin(math.pi * t)
    poses["stick"] = Pose(pitch=14.0 * math.sin(2 * math.pi * 4 * t) * wave,
                          roll=16.0 * math.sin(2 * math.pi * 3 * t + 0.8) * wave)
    poses["fire"] = Pose(z=-2.6 * max(tap(f, f0) for f0 in (76, 88, 116, 142, 164)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "pv1000_print.png"))
    m = materials(dict(case="#FFFFFF", dark=L.COLOURS["black"], cable=L.COLOURS["cable"]), ROUGHNESS,
                  dict(case=printed))

    joy = joy_base(m)
    for part in joy:
        part.data.transform(JOY_FRAME)
    whole = smoothed(join([slab(m), deck(m)] + back_strip(m) + joy + cable(m), "pv1000"), 40.0)
    switch, switch_at = rocker(m)
    lit, lit_at = light(m)
    rod, pivot = stick(m)
    fire = red_button(m)
    start = button(m, L.BUTTONS["start"])
    for part in (rod, fire, start):
        part.data.transform(JOY_FRAME.to_3x3().to_4x4())
    start.data.transform(Matrix.Translation(JOY_FRAME.translation))
    seat = Vector((0.0, sum(L.SLOT["opening"][1:]) / 2, L.TOP + L.CART["out"] - L.CART["size"][1]))
    parts = {"cartridge": (smoothed(cartridge(m)), seat), "rocker": (smoothed(switch), switch_at),
             "power_light": (lit, lit_at), "start": (smoothed(start), Vector()),
             "stick": (smoothed(rod, 50.0), JOY_FRAME @ Vector((0.0, 0.0, pivot))),
             "fire": (smoothed(fire), Vector((0.0, 0.0, L.STICK["z"][1] + 3.8 - pivot)), "stick")}
    finish("pv1000", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "PV-1000")


if __name__ == "__main__":
    main()
