"""The console theme's Super A'Can system model (godot/themes/console/models/systems/supracan.glb): Funtech's Super A'Can
and its controller.

Built in Blender from the real console's proportions (supracan_layout.py has the measurements, from Funtech's manual, a
1200 dpi scan of its top and photographs). The body is its rounded outline in plan, cut for the vents, the slot and
the controller ports' tunnel; on its top stand the slot's housing (the flap's recess cut into it between its two curved
ridges) and the button panel (POWER's well cut into it), with the power light at its left; the tunnel housing stands
out of the front's foot, a block out of each side, the right one's opening showing the expansion's edge connector. The
controller lies in front of the console's left side: its dog-bone outline through a rounded profile, the D-pad, the
four coloured buttons, SELECT and START, the shoulder buttons; its cable to port 1, a 9-pin plug in it (plugs.dsub).
The printing is one texture drawn by supracan_print.py (the console from above; the cartridge's face; the controller
from above; swatches).

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting in the slot, shrunk to
nothing), the flap (hinged at its back edge), POWER's knob, EJECT, RESET, the power light (shrunk to nothing), and the
controller's D-pad, Y, X, B, A and START.

The `focused` clip (8 s, looping) plays a game: the cartridge (a made-up game) appears over the slot, turns once to show
its label and drops in, pushing the flap down; POWER slides on and the light comes on; START, then the D-pad and the
four buttons are played; RESET, POWER off, then EJECT pushes the cartridge up and it rises out and goes, the flap
springing shut.

Four materials (case, dark, metal, cable) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/supracan_print.py artifacts/made-up-games artifacts/supracan
    blender -b --factory-startup --python tools/console-models/supracan.py -- artifacts/supracan godot/themes/console/models/systems/supracan.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plugs  # noqa: E402
import supracan_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import tube  # noqa: E402
from saturn import disc, inset, smooth_outline  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the right side (the expansion block) comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, dark=0.7, metal=0.3, cable=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
TOP = ATLAS.uv("top", L.TOP_X[1] - L.TOP_X[0], L.TOP_Y[1] - L.TOP_Y[0])
PAD_UV = ATLAS.uv("pad", L.PAD_SPAN[1] - L.PAD_SPAN[0], L.PAD_SPAN[3] - L.PAD_SPAN[2])
P = L.PAD
PAD_FRAME = Matrix.Translation((*P["at"], 0.0)) @ Matrix.Rotation(math.radians(P["turn"]), 4, "Z")


def top_uv(co):
    return TOP(co.x - L.TOP_X[0], L.TOP_Y[1] - co.y)


def pad_uv(co):
    return PAD_UV(co.x - L.PAD_SPAN[0], L.PAD_SPAN[3] - co.y)


def printed(part, m, name="case"):
    paint(part, m["case"], ATLAS.swatch(name), lambda c, n, kind: kind == "case")
    paint(part, m["case"], top_uv, lambda c, n, kind: kind == "case" and n.z > 0.9)
    return part


def plate(name, rect, z0, z1, mat, r=None):
    x0, x1, y0, y1 = rect
    if r is None:
        return box(name, x0, x1, y0, y1, z0, z1, mat)
    outline = rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, r, 4)
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


# ---- The console -----------------------------------------------------------------------------------------------------

def opening(m):
    x0, x1, y0, y1 = L.FLAP["rect"]
    return box("opening", x0 + 0.3, x1 - 0.3, y0 + 0.2, y1 - 0.2, 8.0, L.HOUSING["top"] + 6.0, m["dark"])


def tunnel(m):
    x0, x1, back, z0, z1 = L.TUNNEL["recess"]
    return box("tunnel", x0, x1, L.TUNNEL["block"][2] - 2.0, back, z0, z1, m["case"])


def body(m):
    """The body: its rounded outline, cut for the vents, the slot, the tunnel and the ports."""
    part = plate("body", (-L.HALF, L.HALF, 0.0, L.DEPTH), 0.0, L.HEIGHT, m["case"], L.CORNER)
    bevel(part, 2.0, segments=2)
    v = L.VENTS
    step = (v["x"][1] - v["x"][0]) / v["count"]
    boolean(part, join([box("vent", v["x"][0] + (k + 0.5) * step - v["width"] / 2,
                            v["x"][0] + (k + 0.5) * step + v["width"] / 2, *v["y"], L.HEIGHT - v["depth"],
                            L.HEIGHT + 5.0, m["case"]) for k in range(v["count"])], "vents"))
    boolean(part, opening(m))
    boolean(part, tunnel(m))
    w, h = L.PORTS["size"]
    back = L.TUNNEL["recess"][2]
    boolean(part, join([box("port", x - w / 2, x + w / 2, back - 1.0, back + 6.0, L.PORTS["z"] - h / 2,
                            L.PORTS["z"] + h / 2, m["dark"]) for x in L.PORTS["x"]], "ports"))
    return printed(part, m)


def housing(m):
    """The slot's housing: the flap's recess and the opening cut; its two curved ridges."""
    t = L.HOUSING["top"]
    part = plate("housing", L.HOUSING["rect"], L.HEIGHT - 1.0, t, m["case"])
    bevel(part, 1.0, segments=2)
    boolean(part, plate("recess", L.FLAP["rect"], t - L.FLAP["depth"], t + 5.0, m["case"], 2.0))
    boolean(part, opening(m))
    parts = [printed(part, m)]
    r = L.RIDGES
    for y in r["y"]:
        xs = [-r["x"] + 2 * r["x"] * k / 16 for k in range(17)]

        def line(dy, x_in=0.0):
            return [(x * (1 - x_in / r["x"]), y + r["sag"] * (1 - (x / r["x"]) ** 2) + dy) for x in xs]
        w = r["width"] / 2
        rings = []
        for z, d, x_in in ((t - 0.5, 0.0, 0.0), (t + r["height"] * 0.6, 0.0, 0.0), (t + r["height"], 0.7, 1.0)):
            outline = line(-w + d, x_in) + list(reversed(line(w - d, x_in)))
            rings.append([(x, yy, z) for x, yy in outline])
        parts.append(printed(solid("ridge", rings, m["case"]), m))
    return parts


def panel(m):
    p = L.PANEL
    part = plate("panel", p["rect"], L.HEIGHT - 1.0, p["top"], m["case"])
    bevel(part, 1.0, segments=2)
    boolean(part, plate("well", L.POWER["well"], p["top"] - 1.6, p["top"] + 5.0, m["case"], 0.8))
    return printed(part, m)


def tunnel_block(m):
    x0, x1, y0, y1, z1 = L.TUNNEL["block"]
    part = box("block", x0, x1, y0, y1, 0.0, z1, m["case"])
    bevel(part, 1.2, segments=2)
    boolean(part, tunnel(m))
    return printed(part, m)


def side_blocks(m):
    s = L.SIDES
    out = []
    for side in (-1, 1):
        a, b = sorted((side * (L.HALF - 2.0), side * (L.HALF + s["out"])))
        part = box("side", a, b, *s["y"], *s["z"], m["case"])
        bevel(part, 1.5, segments=2)
        if side > 0:                                       # the expansion's opening, its edge connector in it
            y0, y1, z0, z1, depth = s["opening"]
            boolean(part, box("opening", L.HALF + s["out"] - depth, L.HALF + s["out"] + 2.0, y0, y1, z0, z1, m["dark"]))
            edge = box("edge", L.HALF + s["out"] - depth - 0.5, L.HALF + s["out"] - depth + 2.5, y0 + 4.0, y1 - 4.0,
                       (z0 + z1) / 2 - 1.5, (z0 + z1) / 2 + 1.5, m["metal"])
            out.append(edge)
        out.append(printed(part, m))
    return out


def knob(m):
    x0, x1, y0, _ = L.POWER["well"]
    part = box("power", x0 + 1.2, x1 - 1.2, y0 + 1.0, y0 + 1.0 + L.POWER["knob"], L.PANEL["top"] - 1.4,
               L.PANEL["top"] + 1.6, m["case"])
    bevel(part, 0.8, segments=2)
    for k in range(3):                                     # its grip's ridges
        rib = box("rib", x0 + 2.4, x1 - 2.4, y0 + 4.0 + 2.2 * k, y0 + 4.8 + 2.2 * k, L.PANEL["top"] + 1.4,
                  L.PANEL["top"] + 2.2, m["case"])
        part = join([part, rib], "power")
    return coloured(part, m["case"], ATLAS, "case")


def button(m, rect, name):
    part = plate(name, rect, L.PANEL["top"] - 1.0, L.PANEL["top"] + L.BUTTON_HEIGHT, m["case"])
    bevel(part, 0.8, segments=2)
    return printed(part, m)


def light(m):
    w, h = L.LIGHT["size"]
    part = plate("power_light", (-w / 2, w / 2, -h / 2, h / 2), -0.6, 0.35, m["case"], 1.2)
    coloured(part, m["case"], ATLAS, "lit")
    return part, Vector((L.LIGHT["x"], L.LIGHT["y"], L.HEIGHT))


def flap(m):
    """The flap in its recess, printed; its origin on its hinge along its back edge."""
    x0, x1, y0, y1 = L.FLAP["rect"]
    t = L.HOUSING["top"] - L.FLAP["depth"] + L.FLAP["thickness"]
    part = plate("flap", (x0 + 0.5, x1 - 0.5, y0 + 0.5, y1 - 0.3), t - L.FLAP["thickness"], t, m["case"], 1.6)
    bevel(part, 0.3, segments=1)
    printed(part, m, "flap")
    hinge = Vector((0.0, y1 - 0.3, t))
    part.data.transform(Matrix.Translation(-hinge))
    return part, hinge


def cartridge(m):
    """The cartridge, standing, its face to the front, its bottom's middle at its origin."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(part, 1.2, segments=2)
    face = ATLAS.uv("face", w, h)
    coloured(part, m["case"], ATLAS, "cart")
    paint(part, m["case"], lambda co: face(co.x + w / 2, h - co.z), lambda c, n, kind: n.y < -0.9)
    return part


# ---- The controller --------------------------------------------------------------------------------------------------

def pad(m):
    """The controller in its own frame: the body (its rounded profile, the shoulder buttons), and the parts that move."""
    outline = smooth_outline(P["points"])
    h = P["height"]
    profile = ((0.0, 5.0), (0.12, 1.8), (0.3, 0.0), (0.55, 0.4), (0.78, 2.2), (0.92, 4.2), (1.0, 6.2))
    body_ = solid("pad", [[(px, py, h * z) for px, py in (inset(outline, d) if d else outline)] for z, d in profile],
                  m["case"])
    coloured(body_, m["case"], ATLAS, "pad")
    paint(body_, m["case"], pad_uv, lambda c, n, kind: n.z > 0.85)
    parts = [body_]
    sx, sy = P["shoulders"]
    for side in (-1, 1):
        shoulder = box("shoulder", side * sx - 8.0, side * sx + 8.0, sy, sy + 7.0, h * 0.35, h * 0.8, m["case"])
        bevel(shoulder, 1.6, segments=2)
        parts.append(coloured(shoulder, m["case"], ATLAS, "lavender"))
    select = pill(m, P["select"])
    parts.append(select)

    moving = {}
    dx, dy, arm, half = P["dpad"]
    cross = [(arm, -half), (arm, half), (half, half), (half, arm), (-half, arm), (-half, half), (-arm, half),
             (-arm, -half), (-half, -half), (-half, -arm), (half, -arm), (half, -half)]
    dpad = solid("dpad", [[(x, y, z) for x, y in (inset(cross, d) if d else cross)]
                          for z, d in ((-1.5, 0.0), (2.4, 0.0), (3.4, 0.6))], m["case"])
    moving["dpad"] = (coloured(dpad, m["case"], ATLAS, "lavender"), Vector((dx, dy, h - 1.0)))
    for name, (bx, by) in P["buttons"].items():
        b = solid(name, [[(P["button_r"] * math.cos(2 * math.pi * k / 20), P["button_r"] * math.sin(2 * math.pi * k / 20),
                           z) for k in range(20)] for z in (-1.5, 1.8)]
                  + [[(0.8 * P["button_r"] * math.cos(2 * math.pi * k / 20),
                       0.8 * P["button_r"] * math.sin(2 * math.pi * k / 20), 2.6) for k in range(20)]], m["case"])
        swatch = {"y": "red", "x": "green", "b": "yellow", "a": "blue"}[name]
        moving["pad_" + name] = (coloured(b, m["case"], ATLAS, swatch), Vector((bx, by, h - 1.0)))
    start = pill(m, (0.0, 0.0))
    start.data.transform(Matrix.Translation((0.0, 0.0, -h)))
    moving["start"] = (start, Vector((*P["start"], h)))
    return join(parts, "pad"), moving


def pill(m, at):
    w, d = P["pill"]
    x, y = at
    outline = rounded(x, y, w, d, d / 2 - 0.01, 4)
    part = solid("pill", [[(px, py, z) for px, py in outline] for z in (P["height"] - 1.0, P["height"] + 1.2)], m["case"])
    return coloured(part, m["case"], ATLAS, "black")


def cable(m):
    """The controller's cable from its top to port 1, a 9-pin plug in the port."""
    start = PAD_FRAME @ Vector((0.0, P["points"][0][1] - 1.0, P["height"] * 0.55))
    out = PAD_FRAME.to_3x3() @ Vector((0.0, 1.0, 0.0))
    pad_parts, pad_end, pad_dir = plugs.place(*plugs.grommet(lambda o: coloured(o, m["case"], ATLAS, "pad"), r=3.6),
                                              m["case"], start, out)
    port = Vector((L.PORTS["x"][0], L.TUNNEL["recess"][2], L.PORTS["z"]))
    con_parts, con_end, con_dir = plugs.place(*plugs.dsub(lambda o: o, lambda o: o), m["cable"], port, (0.0, -1.0, 0.0))
    path = [pad_end, pad_end + pad_dir * 12.0, Vector((-140.0, -28.0, 2.4)), Vector((-104.0, -22.0, 2.4)),
            Vector((-62.0, -24.0, 2.4)), con_end + con_dir * 10.0 + Vector((0.0, 0.0, -4.0)), con_end + con_dir * 3.0,
            con_end]
    wire = tube("cable", curve(path, 5), 2.0, m["cable"], 10)
    return pad_parts + con_parts + [smoothed(wire, 50.0)]


# ---- The focused clip ------------------------------------------------------------------------------------------------

ABOVE = 52.0                 # how far over its seat the cartridge appears: wholly over the housing


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
    down = smooth(phase(f, 35, 38)) * (1 - back_out(phase(f, 208, 213), 1.6))
    on = smooth(phase(f, 50, 54)) * (1 - smooth(phase(f, 186, 190)))
    poses = {"cartridge": cart, "flap": Pose(pitch=L.FLAP["open"] * down), "power": Pose(y=L.POWER["travel"] * on),
             "power_light": Pose() if 54 <= f < 189 else Pose(scale=HIDDEN),
             "eject": Pose(z=-1.8 * tap(f, 194, 3)), "reset": Pose(z=-1.8 * tap(f, 176, 3)),
             "start": Pose(z=-1.2 * tap(f, 62, 3))}
    t = phase(f, 72, 170)
    wave = math.sin(math.pi * t)
    poses["dpad"] = Pose(pitch=8.0 * math.sin(2 * math.pi * 4 * t) * wave, roll=8.0 * math.sin(2 * math.pi * 3 * t + 0.8)
                         * wave)
    for name, frames in (("pad_y", (80, 120, 150)), ("pad_b", (90, 106, 140, 162)), ("pad_a", (98, 128)),
                         ("pad_x", (112, 156))):
        poses[name] = Pose(z=-1.8 * max(tap(f, f0) for f0 in frames))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    image = bpy.data.images.load(os.path.join(images, "supracan_print.png"))
    m = materials(dict(case="#FFFFFF", dark=L.COLOURS["dark"], metal=L.COLOURS["metal"], cable=L.COLOURS["cable"]),
                  ROUGHNESS, dict(case=image))

    controller, pad_moving = pad(m)
    controller.data.transform(PAD_FRAME)
    whole = smoothed(join([body(m), panel(m), tunnel_block(m)] + housing(m) + side_blocks(m) + [controller]
                          + cable(m), "supracan"), 40.0)
    lid, hinge = flap(m)
    lit, lit_at = light(m)
    seat = Vector((0.0, sum(L.FLAP["rect"][2:]) / 2, L.HOUSING["top"] + L.CART["out"] - L.CART["size"][2]))
    parts = {"cartridge": (smoothed(cartridge(m)), seat), "flap": (lid, hinge), "power": (smoothed(knob(m)), Vector()),
             "eject": (smoothed(button(m, L.EJECT["rect"], "eject")), Vector()),
             "reset": (smoothed(button(m, L.RESET["rect"], "reset")), Vector()), "power_light": (lit, lit_at)}
    turn = PAD_FRAME.to_3x3().to_4x4()
    for name, (part, at) in pad_moving.items():
        part.data.transform(turn)
        parts[name] = (smoothed(part), PAD_FRAME @ at)
    finish("supracan", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Super A'Can")


if __name__ == "__main__":
    main()
