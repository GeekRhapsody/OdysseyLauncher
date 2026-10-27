"""The console theme's Othello Multivision system model (godot/themes/console/models/systems/multivision.glb): Tsukuda
Original's Othello Multivision FG-1000.

Built in Blender from the real console's proportions (multivision_layout.py has the measurements, taken from
photographs). The cream shell is rings of its rounded outline in plan, its front edge chamfered, on the thin navy base;
cut into its top are the recessed panel, the vents and the slot (through the base too). In the recess stand the three
plates, on them the maroon keys (each tapering to its printed top), the joystick's dome and its stick with the ball on
it; the smoked flap lies over the slot. The printing is one texture drawn by multivision_print.py (the top from above;
the cartridge's face; swatches).

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting in the slot, shrunk to
nothing), the flap (hinged at its back edge), the stick, S-1, S-2 and PAUSE.

The `focused` clip (8 s, looping) plays a game: the cartridge (an SG-1000 cartridge, a made-up game on its label in the
manner of Tsukuda's) appears over the slot, turns once to show its label and drops in, pushing the flap down; the stick
waggles and S-1 and S-2, the fire buttons, are pressed, PAUSE twice; then the cartridge rises out and goes and the flap
springs shut.

Four materials (case, dark, smoked, stick) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/multivision_print.py artifacts/made-up-games artifacts/multivision
    blender -b --factory-startup --python tools/console-models/multivision.py -- artifacts/multivision godot/themes/console/models/systems/multivision.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multivision_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 32.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, dark=0.7, smoked=0.12, stick=0.35)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
TOP = ATLAS.uv("top", L.WIDTH, L.DEPTH)
TOP_Z = L.HEIGHT - L.RECESS["depth"] + L.PLATE_HEIGHT      # the plates' tops


def top_uv(co):
    return TOP(co.x + L.HALF, L.DEPTH - co.y)


def plan(x0, x1, y0, y1, r, z, segments=4):
    """A rounded rectangle in plan at height z."""
    return [(x, y, z) for x, y in rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, r, segments)]


def slab(name, rect, r, z0, z1, mat, segments=4):
    return solid(name, [plan(*rect, r, z, segments) for z in (z0, z1)], mat)


def printed(part, m, swatch):
    coloured(part, m["case"], ATLAS, swatch)
    paint(part, m["case"], top_uv, lambda c, n, name: n.z > 0.9)
    return part


# ---- The console -----------------------------------------------------------------------------------------------------

def slot_cut(m):
    x0, x1, y0, y1 = L.FLAP["rect"]
    return box("slot", x0, x1, y0, y1, L.CART["bottom"], L.HEIGHT + 5.0, m["dark"])


def shell(m):
    """The cream shell: its rounded outline, the front edge chamfered; the recess, the vents and the slot cut."""
    c = L.SHELL["corner"]
    cy, cz = L.SHELL["chamfer"]
    full = (-L.HALF, L.HALF, 0.0, L.DEPTH)
    part = solid("shell", [plan(*full, c, L.BASE - 0.5), plan(*full, c, L.HEIGHT - cz),
                           plan(-L.HALF, L.HALF, cy, L.DEPTH, c, L.HEIGHT)], m["case"])
    bevel(part, 1.0, segments=2)
    x0, x1, y0, y1 = L.RECESS["rect"]
    boolean(part, slab("recess", L.RECESS["rect"], L.RECESS["r"], L.HEIGHT - L.RECESS["depth"], L.HEIGHT + 5.0,
                       m["case"]))
    v = L.VENTS
    step = (v["x"][1] - v["x"][0]) / v["count"]
    boolean(part, join([box("vent", v["x"][0] + (k + 0.5) * step - v["width"] / 2,
                            v["x"][0] + (k + 0.5) * step + v["width"] / 2, *v["y"], L.HEIGHT - v["depth"],
                            L.HEIGHT + 5.0, m["case"]) for k in range(v["count"])], "vents"))
    boolean(part, slot_cut(m))
    paint(part, m["case"], ATLAS.swatch("cream"), lambda c, n, name: name == "case")
    paint(part, m["case"], top_uv, lambda c, n, name: name == "case" and n.z > 0.9)
    return part


def base(m):
    part = slab("base", (-L.HALF + 0.6, L.HALF - 0.6, 0.6, L.DEPTH - 0.6), L.SHELL["corner"] - 0.6, 0.0, L.BASE,
                m["case"])
    bevel(part, 0.8, segments=1)
    boolean(part, slot_cut(m))
    paint(part, m["case"], ATLAS.swatch("navy"), lambda c, n, name: name == "case")
    return part


def plates(m):
    z0 = L.HEIGHT - L.RECESS["depth"] - 0.5
    out = []
    for rect in L.PLATES.values():
        part = slab("plate", rect, L.PLATE_R, z0, TOP_Z, m["case"])
        bevel(part, 0.6, segments=1)
        out.append(printed(part, m, "cream"))
    return out


def key(m, x0, x1, y0, y1):
    """A key standing on its plate, tapering to its printed top."""
    h, i = L.KEY["height"], L.KEY["inset"]
    rings = [plan(x0, x1, y0, y1, 0.8, TOP_Z - 0.5, 2), plan(x0, x1, y0, y1, 0.8, TOP_Z + h - 1.2, 2),
             plan(x0 + i, x1 - i, y0 + i, y1 - i, 0.6, TOP_Z + h, 2)]
    return smoothed(printed(solid("key", rings, m["case"]), m, "maroon"), 40.0)


MOVING = {"S-1": "s1", "S-2": "s2", "PAUSE": "pause"}


def keys(m):
    fixed, moving = [], {}
    for legend, x0, x1, y0, y1 in L.KEYS:
        part = key(m, x0, x1, y0, y1)
        if legend in MOVING:
            moving[MOVING[legend]] = (part, Vector())
        else:
            fixed.append(part)
    return fixed, moving


def joystick(m):
    """The dome on its plate (fixed) and the stick with its ball (its origin at its pivot in the dome)."""
    s = L.STICK
    r, h = s["dome"]
    dome = lathe("dome", [(0.0, TOP_Z - 0.5), (r, TOP_Z - 0.5), (r, TOP_Z + 0.8), (r - 1.4, TOP_Z + h * 0.6),
                          (r - 4.0, TOP_Z + h * 0.92), (0.0, TOP_Z + h)], m["stick"], 32)
    dome.data.transform(Matrix.Translation((*s["at"], 0.0)))
    b = s["ball"]
    stick = lathe("stick", [(0.0, -3.0), (s["r"], -3.0), (s["r"], s["top"] - b * 0.6)]
                  + [(b * math.sin(math.pi * k / 8), s["top"] - b * math.cos(math.pi * k / 8)) for k in range(3, 9)],
                  m["stick"], 24)
    return smoothed(dome, 50.0), smoothed(stick, 50.0), Vector((*s["at"], TOP_Z + h - 2.0))


def flap(m):
    """The smoked flap, its origin on its hinge along its back edge."""
    x0, x1, y0, y1 = L.FLAP["rect"]
    part = box("flap", x0 + 0.4, x1 - 0.4, y0 - y1 + 0.4, 0.0, -L.FLAP["thickness"], 0.0, m["smoked"])
    bevel(part, 0.3, segments=1)
    return part, Vector((0.0, y1, L.HEIGHT))


def cartridge(m):
    """The SG-1000 cartridge, standing, its label to the front, its bottom's middle at its origin."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(part, 1.0, segments=2)
    face = ATLAS.uv("face", w, h)
    coloured(part, m["case"], ATLAS, "shell")
    paint(part, m["case"], lambda co: face(co.x + w / 2, h - co.z), lambda c, n, name: n.y < -0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

ABOVE = 46.0                 # how far over its seat the cartridge appears: wholly above the top


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
    # The flap: pushed down as the cartridge's bottom reaches the top, springing shut once it has left.
    down = smooth(phase(f, 36, 39)) * (1 - back_out(phase(f, 207, 212), 1.6))
    poses = {"cartridge": cart, "flap": Pose(pitch=-L.FLAP["open"] * down)}
    t = phase(f, 60, 170)
    wave = math.sin(math.pi * t)
    poses["stick"] = Pose(pitch=16.0 * math.sin(2 * math.pi * 4 * t) * wave,
                          roll=18.0 * math.sin(2 * math.pi * 3 * t + 0.8) * wave)
    poses["s1"] = Pose(z=-2.4 * max(tap(f, f0) for f0 in (70, 92, 118, 146)))
    poses["s2"] = Pose(z=-2.4 * max(tap(f, f0) for f0 in (82, 104, 132, 160)))
    poses["pause"] = Pose(z=-2.4 * max(tap(f, 176), tap(f, 186)))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    image = bpy.data.images.load(os.path.join(images, "multivision_print.png"))
    m = materials(dict(case="#FFFFFF", dark=L.COLOURS["black"], smoked=L.COLOURS["smoked"], stick=L.COLOURS["stick"]),
                  ROUGHNESS, dict(case=image))

    fixed, moving = keys(m)
    dome, stick, pivot = joystick(m)
    whole = smoothed(join([shell(m), base(m)] + plates(m) + fixed + [dome], "multivision"), 40.0)
    lid, hinge = flap(m)
    seat = Vector((0.0, sum(L.FLAP["rect"][2:]) / 2 - 1.4, L.CART["bottom"]))
    parts = {"cartridge": (smoothed(cartridge(m)), seat), "flap": (lid, hinge), "stick": (stick, pivot), **moving}
    finish("multivision", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Othello Multivision")


if __name__ == "__main__":
    main()
