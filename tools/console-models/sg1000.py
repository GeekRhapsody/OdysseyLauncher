"""The console theme's SG-1000 system model (godot/themes/console/models/systems/sg-1000.glb): Sega's SG-1000 and its
hard-wired SJ-200 joystick.

Built in Blender from the real console's proportions (sg1000_layout.py has the measurements, taken from photographs).
The console is its side outline extruded across its width, standing on its grey base: its front corners cut off in
plan, its top's ends chamfered down to the sides, the slot cut into the cartridge well's grey frame on the top's back
and the grilles' slats beside it, the second player's port into its right side; HOLD stands on the slope. The joystick
lies in front of its left end: its two-tone box, the stick in its round recess, a fire button on each side, the cable
from its top end to the console's left side, a strain relief at each end (plugs.grommet). The printing is one texture
drawn by sg1000_print.py (the top's slope in its own frame; the cartridge's label; the joystick's top; swatches).

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting over the slot, shrunk to
nothing), the power light (shrunk to nothing), HOLD, the stick and the two fire buttons.

The `focused` clip (8 s, looping) plays a game: the cartridge (a made-up game) appears over the well, turns once to
show its label and drops into the slot, and the power light comes on; the stick waggles and the fire buttons are
pressed, HOLD twice; then the light goes off and the cartridge rises out and goes.

Four materials (case, print, dark, cable) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/sg1000_print.py artifacts/made-up-games artifacts/sg1000
    blender -b --factory-startup --python tools/console-models/sg1000.py -- artifacts/sg1000 godot/themes/console/models/systems/sg-1000.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plugs  # noqa: E402
import sg1000_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, prism_x  # noqa: E402
from props import tube  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 28.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, print=0.45, dark=0.7, cable=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)

# The top's frame: x across, s up the slope from its front edge, h off it.
SLOPE_FRAME = Matrix.Translation((0.0, *L.FRONT)) @ Matrix.Rotation(L.SLOPE, 4, "X")
NORMAL = SLOPE_FRAME.to_3x3() @ Vector((0.0, 0.0, 1.0))
TOP = ATLAS.uv("top", L.WIDTH, L.TOP_LENGTH)


def top_uv(co):
    """A point on the top, by where it lies along the slope (the rounded edges' points kept on it)."""
    s = (co.y - L.FRONT[0]) * math.cos(L.SLOPE) + (co.z - L.FRONT[1]) * math.sin(L.SLOPE)
    return TOP(co.x + L.WIDTH / 2, L.TOP_LENGTH - min(L.TOP_LENGTH, max(0.0, s)))


def on_slope(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline on the top, from h0 to h1 off it."""
    return solid(name, [[SLOPE_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def rect(x0, x1, s0, s1):
    return [(x0, s0), (x1, s0), (x1, s1), (x0, s1)]


# ---- The console -----------------------------------------------------------------------------------------------------

def console(m):
    """The body on its base: the corners and the top's ends cut, the well, the slot, the grilles and the port; its top
    printed."""
    w, d, half = L.WIDTH, L.DEPTH, L.WIDTH / 2
    body = prism_x("sg1000", L.PROFILE, -half, half, m["case"])
    c = L.CORNER
    for side in (-1, 1):                                    # the front corners, cut off in plan
        cut = [(side * (half - c), -5.0), (side * (half + 5.0), -5.0), (side * (half + 5.0), c)]
        boolean(body, solid("corner", [[(x, y, z) for x, y in (cut if side > 0 else cut[::-1])]
                                       for z in (-5.0, 90.0)], m["case"]))
    e = L.ENDS
    for side in (-1, 1):                                    # the top's ends, chamfered down to the sides
        rings = []
        for y in (-5.0, d + 5.0):
            z = L.top_z(y)
            ring = [(side * (half - e["width"]), z), (side * (half + 5.0), z - e["drop"] * (e["width"] + 5.0)
                                                      / e["width"]), (side * (half + 5.0), z + 60.0),
                    (side * (half - e["width"]), z + 60.0)]
            rings.append([(x, y, zz) for x, zz in (ring if side > 0 else ring[::-1])])
        boolean(body, solid("end", rings, m["case"]))
    bevel(body, 2.0, segments=2, angle=30)
    well = on_slope("well", rounded(0.0, sum(L.WELL["s"]) / 2, L.WELL["x"][1] - L.WELL["x"][0],
                                    L.WELL["s"][1] - L.WELL["s"][0], 3.0, 3), -3.0, L.WELL["height"], m["case"])
    bevel(well, 1.0, segments=1, angle=30)
    boolean(body, well, "UNION")
    (x0, x1), (s0, s1) = L.SLOT["x"], L.SLOT["s"]
    (y0, _), (y1, top) = L.slope_point(s0), L.slope_point(s1, L.WELL["height"])
    boolean(body, box("slot", x0, x1, y0, y1, top - L.SLOT["depth"], top + 10.0, m["dark"]))
    g = L.GRILLES
    step = (g["s"][1] - g["s"][0]) / g["slats"]
    slats = []
    for side in (-1, 1):
        a, b = sorted((side * g["x"][0], side * g["x"][1]))
        for k in range(g["slats"]):
            s = g["s"][0] + (k + 0.5) * step
            slats.append(on_slope("slat", rect(a + 2.0, b - 2.0, s - step * 0.22, s + step * 0.22), -2.0, 5.0,
                                  m["case"]))
    boolean(body, join(slats, "slats"))
    p = L.PORT
    boolean(body, box("port", half - 6.0, half + 5.0, *p["y"], *p["z"], m["dark"]))
    coloured(body, m["print"], ATLAS, "case")
    paint(body, m["print"], top_uv, lambda c, n, name: n.dot(NORMAL) > 0.97 and c.z > L.FRONT[1] - 1.0)
    paint(body, m["print"], ATLAS.swatch("dark"),                  # the slot's walls (its floor is printed) and the port
          lambda c, n, name: (n.dot(NORMAL) < 0.9 and abs(c.x) < x1 + 0.3 and y0 - 0.3 < c.y < y1 + 0.3
                              and c.z < top - 0.5)
          or (c.x > half - 6.5 and p["y"][0] - 0.3 < c.y < p["y"][1] + 0.3 and p["z"][0] - 0.3 < c.z < p["z"][1] + 0.3))
    base = box("base", -half + 3.0, half - 3.0, 3.0, d - 3.0, 0.0, 4.0, m["print"])
    boolean(base, join([solid("corner", [[(x, y, z) for x, y in (
        [(side * (half - c - 3.0), -5.0), (side * (half + 5.0), -5.0), (side * (half + 5.0), c + 3.0)]
        if side > 0 else [(side * (half + 5.0), c + 3.0), (side * (half + 5.0), -5.0), (side * (half - c - 3.0), -5.0)])]
        for z in (-5.0, 10.0)], m["print"]) for side in (-1, 1)], "corners"))
    coloured(base, m["print"], ATLAS, "base")
    body.data.transform(Matrix.Translation((0.0, 0.0, 3.0)))
    return join([body, base], "sg1000")


def hold(m):
    """HOLD, standing off the slope, its origin at its foot's middle."""
    (x0, x1), (s0, s1) = L.HOLD["x"], L.HOLD["s"]
    button = on_slope("hold", rect(x0, x1, s0, s1), -1.0, L.HOLD["height"], m["print"])
    bevel(button, 0.6, segments=1, angle=30)
    coloured(button, m["print"], ATLAS, "red")
    at = SLOPE_FRAME @ Vector(((x0 + x1) / 2, (s0 + s1) / 2, 0.0)) + Vector((0.0, 0.0, 3.0))
    button.data.transform(Matrix.Translation(-at + Vector((0.0, 0.0, 3.0))))
    return button, at


def light(m):
    lw, lh = L.LIGHT["size"]
    lit = on_slope("power_light", rect(-lw / 2, lw / 2, L.LIGHT["s"] - lh / 2, L.LIGHT["s"] + lh / 2), -0.4, 0.25,
                   m["print"])
    coloured(lit, m["print"], ATLAS, "lit")
    at = SLOPE_FRAME @ Vector((0.0, L.LIGHT["s"], 0.0)) + Vector((0.0, 0.0, 3.0))
    lit.data.transform(Matrix.Translation(-at + Vector((0.0, 0.0, 3.0))))
    return lit, at


def cartridge(m):
    """The cartridge, its bottom's middle at its origin, its label facing the front."""
    w, t, h = L.CART["size"]
    lw, lh, from_top = L.CART["label"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["print"])
    bevel(shell, 1.5, segments=2, angle=30)
    grip = join([box("rib", -w / 2 - 1.0, w / 2 + 1.0, -t / 2 - 1.0, -t / 2 + 0.6, z, z + 1.0, m["print"])
                 for z in (h - lh - from_top - 7.0, h - lh - from_top - 10.0)], "ribs")
    boolean(shell, grip)
    coloured(shell, m["print"], ATLAS, "cart")
    face = ATLAS.uv("label", lw, lh)
    z1 = h - from_top
    paint(shell, m["print"], lambda co: face(co.x + lw / 2, z1 - co.z),
          lambda c, n, name: n.y < -0.9 and abs(c.x) < lw / 2 and z1 - lh < c.z < z1)
    return shell


# ---- The SJ-200 ------------------------------------------------------------------------------------------------------

def stick_frame():
    """The joystick's frame: its top end's middle at the origin, its length back along +y, turned."""
    (x, y), turn = L.STICK["at"], L.STICK["turn"]
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def joystick(m):
    """The joystick's box, at its place: the lower part and the lighter top, the top printed."""
    w, length, h0, h1 = L.STICK["size"]
    lower = solid("joystick", [[(x, y, z) for x, y in rounded(0.0, -length / 2, w, length, 4.0, 3)]
                               for z in (0.0, h0)], m["print"])
    upper = solid("joystick_top", [[(x, y, z) for x, y in rounded(0.0, -length / 2, w - 1.0, length - 1.0, 3.5, 3)]
                                   for z in (h0 - 0.5, h0 + h1)], m["print"])
    bevel(lower, 1.2, segments=2, angle=30)
    bevel(upper, 1.6, segments=2, angle=30)
    r = L.STICK["recess"]
    boolean(upper, solid("recess", [[(r["r"] * math.cos(2 * math.pi * k / 32), -r["v"] + r["r"] * math.sin(
        2 * math.pi * k / 32), z) for k in range(32)] for z in (h0 + h1 - 2.5, h0 + h1 + 5.0)], m["print"]))
    coloured(lower, m["print"], ATLAS, "stick_base")
    coloured(upper, m["print"], ATLAS, "stick_top")
    face = ATLAS.uv("stick", w, length)
    paint(upper, m["print"], lambda co: face(co.x + w / 2, -co.y), lambda c, n, name: n.z > 0.9)
    body = join([lower, upper], "joystick")
    body.data.transform(stick_frame())
    return body


def stick(m):
    """The stick: the shaft and its knob, its pivot at its origin."""
    sr, length = L.STICK["shaft"]
    k = L.STICK["knob"]
    shaft = solid("shaft", [[(sr * (1.0 - 0.25 * z / length) * math.cos(2 * math.pi * j / 14),
                              sr * (1.0 - 0.25 * z / length) * math.sin(2 * math.pi * j / 14), z) for j in range(14)]
                            for z in (-2.0, length)], m["dark"])
    knob = solid("knob", [[(k * math.cos(math.radians(lat)) * math.cos(2 * math.pi * j / 16),
                            k * math.cos(math.radians(lat)) * math.sin(2 * math.pi * j / 16),
                            length + k * 0.6 + k * math.sin(math.radians(lat))) for j in range(16)]
                          for lat in range(-70, 71, 20)], m["dark"])
    part = join([shaft, knob], "stick")
    coloured(part, m["print"], ATLAS, "black")
    return part


def fire_buttons(m):
    """The red fire buttons on the joystick's sides, each its origin at its face's middle, with where it goes."""
    w = L.STICK["size"][0]
    f = L.STICK["fire"]
    (v0, v1), (z0, z1), out = f["v"], f["z"], f["out"]
    frame = stick_frame()
    parts = {}
    for name, side in (("fire_left", -1), ("fire_right", 1)):
        button = box(name, *sorted((-side * 1.0, side * out)), -(v1 - v0) / 2, (v1 - v0) / 2, z0, z1, m["print"])
        bevel(button, 0.8, segments=1, angle=30)
        coloured(button, m["print"], ATLAS, "red")
        button.data.transform(Matrix.Rotation(math.radians(L.STICK["turn"]), 4, "Z"))
        parts[name] = (button, frame @ Vector((side * w / 2, -(v0 + v1) / 2, 0.0)))
    return parts


def cable(m):
    """The joystick's cable, from its top end round to the console's left side, a strain relief at each end."""
    frame = stick_frame()
    h = L.STICK["size"][2] + 2.0
    start = frame @ Vector((0.0, 0.0, h))
    out = frame.to_3x3() @ Vector((0.0, 1.0, 0.0))
    side = Vector((-L.WIDTH / 2 + 0.5, L.DEPTH - 26.0, 11.0))
    joy_parts, joy_end, joy_dir = plugs.place(*plugs.grommet(lambda o: coloured(o, m["print"], ATLAS, "stick_base"),
                                                             r=3.6), m["print"], start, out)
    con_parts, con_end, con_dir = plugs.place(*plugs.grommet(lambda o: coloured(o, m["print"], ATLAS, "base"),
                                                             r=4.0), m["print"], side, (-1.0, 0.0, 0.0))
    path = [joy_end, joy_end + joy_dir * 14.0, Vector((-142.0, 10.0, 2.2)), Vector((-140.0, 56.0, 2.2)),
            Vector((-120.0, 90.0, 2.6)), con_end + con_dir * 12.0 + Vector((0.0, 0.0, -4.0)), con_end + con_dir * 4.0,
            con_end]
    wire = tube("cable", curve(path, 5), 2.0, m["cable"], 10)
    return joy_parts + con_parts + [smoothed(wire, 50.0)]


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold_=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold_, f0 + 5 + hold_)))


ABOVE = 64.0                 # how far over its seat the cartridge appears


def timeline(f):
    if f < 6 or f >= 222:
        cart = Pose(z=ABOVE, scale=HIDDEN)
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
    poses = {"cartridge": cart, "power_light": Pose() if 48 <= f < 194 else Pose(scale=HIDDEN)}
    t = phase(f, 62, 176)
    wave = math.sin(math.pi * t)
    poses["stick"] = Pose(pitch=16.0 * math.sin(2 * math.pi * 4 * t) * wave, roll=18.0 * math.sin(2 * math.pi * 3 * t
                                                                                                 + 0.8) * wave)
    poses["fire_left"] = Pose(*(Matrix.Rotation(math.radians(L.STICK["turn"]), 3, "Z") @ Vector((1.6, 0.0, 0.0))
                                * max(tap(f, f0) for f0 in (72, 84, 112, 140))))
    poses["fire_right"] = Pose(*(Matrix.Rotation(math.radians(L.STICK["turn"]), 3, "Z") @ Vector((-1.6, 0.0, 0.0))
                                 * max(tap(f, f0) for f0 in (98, 126, 164))))
    poses["hold"] = Pose(*(-NORMAL * 1.6 * max(tap(f, 150), tap(f, 166))))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "sg1000_print.png"))
    m = materials(dict(case=L.COLOURS["case"], print="#FFFFFF", dark=L.COLOURS["dark"], cable="#1A1A1C"), ROUGHNESS,
                  dict(print=printed))

    whole = smoothed(join([console(m), joystick(m)] + cable(m), "sg1000"))
    button, button_at = hold(m)
    lit, lit_at = light(m)
    (x0, x1), (s0, s1) = L.SLOT["x"], L.SLOT["s"]
    y_mid, z_top = L.slope_point((s0 + s1) / 2, L.WELL["height"])
    seat = Vector(((x0 + x1) / 2, y_mid, z_top + 3.0 - L.CART["inserted"]))
    r = L.STICK["recess"]
    w, length, h0, h1 = L.STICK["size"]
    parts = {"cartridge": (smoothed(cartridge(m)), seat), "power_light": (lit, lit_at), "hold": (smoothed(button),
                                                                                              button_at),
             "stick": (smoothed(stick(m), 50.0), stick_frame() @ Vector((0.0, -r["v"], h0 + h1 - 2.5)))}
    parts.update({name: (smoothed(part), at) for name, (part, at) in fire_buttons(m).items()})
    finish("sg1000", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "SG-1000")


if __name__ == "__main__":
    main()
