"""The console theme's Watara Supervision system model (godot/themes/console/models/systems/supervision.glb): the
original two-piece Supervision, its screen on its bellows neck.

Built in Blender from the real handheld's proportions (supervision_layout.py has the measurements, taken from
photographs). The controls are their D-shaped outline lofted back, their edges rounded, the D-pad, A, B, SELECT and
START standing on their front; the neck is black bellows, its ribs lofted up from the controls' top; the screen unit
is a rounded box, its bezel's glass standing a little proud, the cartridge's slot cut into its top at the back. The
printing is one texture drawn by supervision_print.py: the two fronts (planar-mapped onto the faces facing forward),
the screens, the cartridge's label, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT: its left end towards the viewer and its face tipped up;
then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the controls, their origin at their
foot's middle; the controls holding the D-pad, A and B and the screen unit (its origin on the neck's top, where it
tilts); the screen unit holding the cartridge (waiting in its slot, shrunk to nothing) and three screens (the start-up
logo, Odyssey's title, a moment of its play), shrunk to nothing.

The `focused` clip (8 s, looping) plays a game and shows off the Supervision's tilting screen: the cartridge hovers over
the screen unit showing its label, turns round and drops into its slot; the logo comes up, then the title, START, the
game; the screen tilts back on its neck while the game is played on the D-pad, A and B, and tilts up again. Then the
screen goes off and the cartridge rises out and goes.

Five materials (case, key, black, glass, print) and one texture, within the system model budget. Run from the repo
root:

    python tools/console-models/supervision_print.py artifacts/supervision
    blender -b --factory-startup --python tools/console-models/supervision.py -- artifacts/supervision godot/themes/console/models/systems/supervision.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import supervision_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT = (20.0, 10.0)       # degrees: yaw (left end nearer), pitch (face up)
ROUGHNESS = dict(case=0.55, key=0.35, black=0.6, glass=0.45, print=0.5)
CW, CH, CD = L.CONTROLS["size"]
UW, UH, UD = L.UNIT["size"]


# ---- UVs and shapes --------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


CONTROLS_FRONT = atlas_uv(L.REGIONS["controls_front"], CW, CH)
SCREEN_FRONT = atlas_uv(L.REGIONS["screen_front"], UW, UH)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def plate(name, points, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1 (y back from the front face)."""
    return solid(name, [[(x, y, z) for x, z in points] for y in (y0, y1)], mat)


def disc(cx, cz, r, n=28):
    return [(cx + r * math.cos(2 * math.pi * k / n), cz + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def button(name, r, height, mat, n=28):
    """A round button standing height out of the front, its top domed; its foot's middle at its origin."""
    rings = [[(x, y, z) for x, z in disc(0.0, 0.0, r * k, n)] for k, y in
             ((1.0, 1.0), (1.0, -height + 0.9), (0.8, -height + 0.2), (0.45, -height))]
    return solid(name, rings, mat)


# ---- The controls and the neck ---------------------------------------------------------------------------------------

def controls(m):
    """The controls: their slab (its front printed), SELECT and START, and the neck on their top."""
    shell = plate("supervision", L.controls_outline(), 0.0, CD, m["case"])
    bevel(shell, 3.0, segments=3)
    paint(shell, m["print"], lambda co: CONTROLS_FRONT(co.x + CW / 2, CH - co.z), lambda c, n, name: n.y < -0.9)
    parts = [shell]
    sw, sh = L.SMALL["size"]
    for name in ("select", "start"):
        x, z = L.SMALL[name]
        pill = plate(name, [(x + a, z + b) for a, b in rounded(0.0, 0.0, sw, sh, sh / 2 - 0.01, 5)], -L.SMALL["height"],
                     1.0, m["black"])
        bevel(pill, 0.5, segments=1)
        parts.append(pill)
    (z0, z1), nw, nd, ribs = L.NECK["z"], L.NECK["width"], L.NECK["depth"], L.NECK["ribs"]
    y0 = (CD - nd) / 2
    rings = []
    for k in range(2 * ribs + 1):
        z = z0 - 1.0 + (z1 - z0 + 2.0) * k / (2 * ribs)
        k_in = 0.0 if k % 2 == 0 else 1.6
        rings.append([(x, y, z) for x, y in rounded(0.0, y0 + nd / 2, nw - 2 * k_in, nd - 2 * k_in, 5.0 - k_in * 0.5, 4)])
    neck = solid("neck", rings, m["black"])
    parts.append(neck)
    return join(parts, "supervision")


def dpad(m):
    """The D-pad, its middle at its origin: a diamond, its edges rounded, a cross grooved into it."""
    s = L.DPAD["size"] / 2
    diamond = [(0.0, s), (-s, 0.0), (0.0, -s), (s, 0.0)]
    part = plate("dpad", diamond, -L.DPAD["height"], 1.0, m["black"])
    bevel(part, 1.6, segments=2)
    for a in (0.0, math.pi / 2):
        c, si = math.cos(a), math.sin(a)
        groove = plate("groove", [(c * u - si * v, si * u + c * v) for u, v in
                                  ((-s * 0.8, -0.5), (s * 0.8, -0.5), (s * 0.8, 0.5), (-s * 0.8, 0.5))],
                       -L.DPAD["height"] - 2.0, -L.DPAD["height"] + 0.5, m["black"])
        boolean(part, groove)
    return part, Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1]))


# ---- The screen unit -------------------------------------------------------------------------------------------------

def screen_unit(m):
    """The screen unit in its own frame (its foot's middle at the origin, on the neck's top): its box (its front
    printed, the cartridge's slot cut into its top), the bezel's glass."""
    shape = rounded(0.0, UH / 2, UW, UH, L.UNIT["corner"], 5)
    shell = plate("screen_unit", shape, 0.0, UD, m["case"])
    bevel(shell, 3.0, segments=3)
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    w, h, t = L.CART["size"]
    boolean(shell, box("slot", sx0, sx1, sy0, sy1, UH - (h - L.CART["protrudes"]) - 1.0, UH + 5.0, m["black"]))
    paint(shell, m["print"], lambda co: SCREEN_FRONT(co.x + UW / 2, UH - co.z), lambda c, n, name: n.y < -0.9 and
          name == "case")
    (bx0, bx1), (bz0, bz1) = L.BEZEL["x"], L.BEZEL["z"]
    glass = plate("bezel", rounded((bx0 + bx1) / 2, (bz0 + bz1) / 2, bx1 - bx0, bz1 - bz0, L.BEZEL["r"], 4), -0.8, 0.5,
                  m["print"])
    paint(glass, m["print"], lambda co: SCREEN_FRONT(co.x + UW / 2, UH - co.z), lambda c, n, name: n.y < -0.9)
    paint(glass, m["print"], swatch("dark"), lambda c, n, name: n.y >= -0.9)
    return join([shell, glass], "screen_unit")


def cartridge(m):
    """The cartridge, its foot's middle at its origin: grey, its label on its back (+y), its contacts at its foot."""
    w, h, t = L.CART["size"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 6.0, h, m["print"])
    bevel(shell, 1.0, segments=2)
    painted(shell, m, "cart")
    grip = painted(box("grip", -w / 2 + 2.0, w / 2 - 2.0, -t / 2 - 0.6, t / 2 + 0.6, h - 9.0, h - 1.0, m["print"]), m,
                   "cart")
    bevel(grip, 0.6, segments=1)
    contacts = painted(box("contacts", -w / 2 + 3.0, w / 2 - 3.0, -t / 2 + 2.6, t / 2 - 2.6, 0.0, 7.0, m["print"]), m,
                       "black")
    lw, lh = L.CART["label"]
    z1 = h - 11.0
    label = box("label", -lw / 2, lw / 2, t / 2 - 0.2, t / 2 + 0.15, z1 - lh, z1, m["print"])
    face = atlas_uv(L.REGIONS["label"], lw, lh)
    paint(label, m["print"], lambda co: face(lw / 2 - co.x, z1 - co.z), lambda c, n, name: n.y > 0.9)
    paint(label, m["print"], swatch("cart"), lambda c, n, name: n.y <= 0.9)
    return join([shell, grip, contacts, label], "cartridge")


def screen(m, name):
    lw, lh = L.LCD["size"]
    return curved(name, lw, lh, 0.0, atlas_uv(L.REGIONS[name], 1.0, 1.0), m["glass"], nu=1, nv=1)


# ---- The focused clip ------------------------------------------------------------------------------------------------

HOVER = 60.0              # how far above its seat the cartridge hovers: clear of the top


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    if f < 6 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 14:
        cart = Pose(z=HOVER, spin=180.0, scale=appear(f, 6, 14))
    elif f < 30:
        cart = Pose(z=HOVER + 2.0 * math.sin(2 * math.pi * phase(f, 14, 30)), spin=180.0)
    elif f < 42:
        t = phase(f, 30, 42)
        cart = Pose(z=HOVER + 6.0 * math.sin(math.pi * t), spin=180.0 + 180.0 * smooth(t))
    elif f < 52:
        cart = Pose(z=HOVER * (1 - ease_in(phase(f, 42, 52))), spin=360.0)
    elif f < 212:
        cart = Pose(spin=360.0)
    else:
        cart = Pose(z=HOVER * ease_out(phase(f, 212, 222)), spin=360.0, scale=max(HIDDEN, 1 - ease_in(phase(f, 218, 226))))

    def shown(f0, f1):
        if f0 <= f < f1:
            return Pose(axes=(1.0, 1.0, max(HIDDEN, min(1.0, (f - f0 + 1) / 4.0))))
        return Pose(scale=HIDDEN)
    tilt = -32.0 * smooth(phase(f, 112, 128)) * (1 - smooth(phase(f, 172, 190)))
    t = phase(f, 128, 172)
    k = math.sin(math.pi * t)
    return {"cartridge": cart, "screen_unit": Pose(pitch=tilt),
            "boot": shown(56, 84), "title": shown(84, 104), "game": shown(104, 204),
            "dpad": Pose(pitch=6.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=6.0 * k * math.cos(2 * math.pi * 2.0 * t)),
            "a": Pose(y=1.6 * max(tap(f, f0) for f0 in (100, 132, 150, 166))),
            "b": Pose(y=1.6 * max(tap(f, f0) for f0 in (140, 158)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "supervision_print.png"))
    colours = dict(L.COLOURS, black="#141416")
    m = {n: material(n, colours[n], r, printed if n in ("print", "glass") else None) for n, r in ROUGHNESS.items()}

    body = controls(m)
    pad, pad_at = dpad(m)
    buttons = {}
    for name in ("a", "b"):
        part = button(name, L.AB["r"], L.AB["height"], m["print"])
        painted(part, m, "turquoise")
        buttons[name] = (part, Vector((L.AB[name][0], 0.0, L.AB[name][1])))
    unit = screen_unit(m)
    cart = cartridge(m)
    (lx, lz) = L.LCD["at"]
    screens = {name: (screen(m, name), Vector((lx, -0.9 - 0.05 * k, lz))) for k, name in
               enumerate(("boot", "title", "game"))}
    for obj in [body, pad, unit, cart] + [p for p, _ in buttons.values()]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the controls; they hold their buttons and the screen unit,
    # which holds the cartridge and the screens.
    root = bpy.data.objects.new("supervision_root", None)
    scene.collection.objects.link(root)
    body.parent = root
    for part, where in [(pad, pad_at)] + list(buttons.values()):
        part.parent = body
        part.location = where
    unit.parent = body
    unit.location = (0.0, 0.0, L.UNIT_Z)
    w, h, t = L.CART["size"]
    seat = Vector((0.0, sum(L.SLOT["y"]) / 2, UH + L.CART["protrudes"] - h))
    for part, where in [(cart, seat)] + list(screens.values()):
        part.parent = unit
        part.location = where
    nodes = {"dpad": pad, "screen_unit": unit, "cartridge": cart, **{n: p for n, (p, _) in buttons.items()},
             **{n: p for n, (p, _) in screens.items()}}

    # The three-quarter view, then the spec's fit of the console at rest, as the root's transform.
    yaw, pitch = TILT
    tilt = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
    lift = Matrix.Translation((0.0, 0.0, L.UNIT_Z))
    points = [tilt @ v.co for v in body.data.vertices] + [tilt @ lift @ v.co for v in unit.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [body, pad, unit, cart] + [p for p, _ in buttons.values()] + [p for p, _ in screens.values()]
    print(f"Supervision: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(body.data)} the controls), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
