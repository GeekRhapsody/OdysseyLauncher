"""The console theme's Atari Lynx system model (godot/themes/console/models/systems/atarilynx.glb): a Lynx II.

Built in Blender from the real handheld's proportions (lynx_layout.py has the measurements, taken from photographs).
The body is its front outline lofted back, its edges rounded, the grips' bulges behind its ends; the grips stand a
little proud of the glossy middle, the D-pad's well and the wells of the two pairs of A and B cut into them. The
window's cover, the six buttons beside it, the D-pad and A and B stand on the front; the game card's slot is cut into
the top at the back. The printing is one texture drawn by lynx_print.py: the front (planar-mapped onto the faces facing
forward: the grips, the middle, the window's surround and the switched-off screen, the logos and the names), the
screens, the card's label, and swatches.

A node tree: a root (the turn to a three-quarter view, TILT: its left end towards the viewer and its face tipped up;
then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the console, its origin at its
foot's middle; the console holding the game card (waiting in its slot, shrunk to nothing), ON and OFF, OPTION 2 and
PAUSE (FLIP), the top pair's A and the foot pair's A and B, the D-pad, and three screens (the title of a made-up game,
Odyssey; a moment of its play; the same turned over), shrunk to nothing, so they ride along when the console moves.

The `focused` clip (8 s, looping) plays a game and uses the Lynx's own trick: the card hovers over the console showing
its label, turns round and drops into the slot; ON, and the title comes up; A, and the game; then FLIP turns the picture
over and the console hops and turns over with it, its D-pad now at the right, and the game is played on the other pair
of A and B; FLIP again, and it hops back. Then OFF, and the card rises out and goes.

Four materials (case, key, glass, print) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/lynx_print.py artifacts/lynx
    blender -b --factory-startup --python tools/console-models/lynx.py -- artifacts/lynx godot/themes/console/models/systems/atarilynx.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lynx_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT = (20.0, 10.0)       # degrees: yaw (left end nearer), pitch (face up)
ROUGHNESS = dict(case=0.6, key=0.3, glass=0.35, print=0.5)
W, H, D = L.WIDTH, L.HEIGHT, L.DEPTH
MID = H / 2               # the layout's z = 0, in the console's frame (z up from its foot)


# ---- UVs and outlines ------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


FRONT = atlas_uv(L.REGIONS["front"], W, H)


def front_uv(co):
    return FRONT(co.x + W / 2, H - co.z)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def outline():
    """The front outline, anticlockwise (x, z) in the console's frame."""
    right = L.RIGHT_HALF
    points = right + [(-x, z) for x, z in reversed(right[1:-1])]
    return [(x, z + MID) for x, z in reversed(points)]


def clip_x(points, x0, keep_right):
    """A convex outline clipped to x >= x0 (keep_right) or x <= x0."""
    def inside(p):
        return p[0] >= x0 if keep_right else p[0] <= x0
    out = []
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        if inside(p):
            out.append(p)
        if inside(p) != inside(q):
            t = (x0 - p[0]) / (q[0] - p[0])
            out.append((x0, p[1] + t * (q[1] - p[1])))
    return out


def plate(name, points, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1 (y back from the front face)."""
    return solid(name, [[(x, y, z) for x, z in points] for y in (y0, y1)], mat)


def facing_front(c, n, name):
    return n.y < -0.9


# ---- The console -----------------------------------------------------------------------------------------------------

def body(m):
    """The body, its grips, the bulges behind them; the wells cut into the grips, the slot into the top; its front
    printed."""
    shape = outline()
    shell = plate("atarilynx", shape, 0.0, D, m["case"])
    bevel(shell, 3.0, segments=2)
    (cx0, cx1) = (-L.CARD["size"][0] / 2 - 1.0, L.CARD["size"][0] / 2 + 1.0)
    boolean(shell, box("slot", cx0, cx1, L.CARD["y"] - L.CARD["size"][2] / 2 - 0.5, L.CARD["y"] + L.CARD["size"][2] / 2 + 0.5,
                       H - L.CARD["size"][1] - 2.0, H + 5.0, m["key"]))
    boolean(shell, box("recess", -31.0, 31.0, D - 2.5, D + 5.0, H - 22.0, H + 5.0, m["case"]))
    paint(shell, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and name == "case")
    parts = [shell]
    for side in (-1, 1):
        grip = plate("grip", clip_x(shape, side * L.GRIP_X, side > 0), -L.PROUD, 1.5, m["case"])
        bevel(grip, 1.4, segments=2)
        bulge_outline = clip_x(shape, side * L.BULGE["x"], side > 0)
        rings = [[(x, D - 3.0, z) for x, z in bulge_outline],
                 [(x, D + L.BULGE["depth"] * 0.6, z) for x, z in inset(bulge_outline, 3.0)],
                 [(x, D + L.BULGE["depth"], z) for x, z in inset(bulge_outline, 11.0)]]
        bulge = solid("bulge", rings, m["case"])
        parts += [grip, bulge]
    grips = join(parts[1::2], "grips")
    (dx, dz), size, arm, well = L.DPAD["at"], L.DPAD["size"], L.DPAD["arm"], L.DPAD["well"]
    boolean(grips, plate("dpad_well", cross(dx, dz + MID, size + 2.0, arm + 2.0), -L.PROUD - 5.0, -L.PROUD + well,
                         m["key"]))
    a = L.AB
    for pair, turn in ((a["top"], a["turn"][0]), (a["bottom"], a["turn"][1])):
        for x, z in pair:
            boolean(grips, plate("ab_well", square(x, z + MID, a["well"], turn, 2.0), -L.PROUD - 5.0, -L.PROUD + 1.2,
                                 m["key"]))
    paint(grips, m["print"], front_uv, lambda c, n, name: n.y < -0.9 and name == "case")
    bulges = parts[2::2]
    return [shell, grips] + bulges


def cross(cx, cz, size, arm):
    """A plus sign's outline, anticlockwise, its middle at (cx, cz)."""
    s, a = size / 2, arm / 2
    points = [(a, s), (-a, s), (-a, a), (-s, a), (-s, -a), (-a, -a), (-a, -s), (a, -s), (a, -a), (s, -a), (s, a), (a, a)]
    return [(cx + x, cz + z) for x, z in points]


def square(cx, cz, size, turn, r):
    """A rounded square's outline, anticlockwise, its middle at (cx, cz), turned by turn degrees."""
    c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    return [(cx + c * x - s * z, cz + s * x + c * z) for x, z in rounded(0.0, 0.0, size, size, r, 3)]


def window(m):
    (wx, wz), (ww, wh) = L.WINDOW["at"], L.WINDOW["size"]
    part = plate("window", rounded(wx, wz + MID, ww, wh, L.WINDOW["corner"], 5), -L.WINDOW["height"], 0.5, m["glass"])
    bevel(part, 1.2, segments=2)
    paint(part, m["glass"], front_uv, facing_front)
    paint(part, m["glass"], swatch("key"), lambda c, n, name: n.y >= -0.9)
    return part


def side_button(name, x, z, m):
    """A button beside the window, its middle at its origin (it is pressed into the front)."""
    w, h = L.LEFT_BUTTONS["size"]
    part = plate(name, rounded(0.0, 0.0, w, h, 1.8, 3), -L.LEFT_BUTTONS["height"], 0.5, m["key"])
    bevel(part, 0.7, segments=1)
    return part, Vector((x, 0.0, z + MID))


def dpad(m):
    """The D-pad, its middle at its origin, standing out of its well."""
    size, arm, h = L.DPAD["size"], L.DPAD["arm"], L.DPAD["height"]
    part = plate("dpad", cross(0.0, 0.0, size, arm), -L.PROUD - h, -L.PROUD + L.DPAD["well"] + 0.5, m["key"])
    bevel(part, 1.0, segments=2)
    (dx, dz) = L.DPAD["at"]
    return part, Vector((dx, 0.0, dz + MID))


def ab_button(name, turn, m):
    """A or B, its middle at its origin: a rounded square, its top domed."""
    a = L.AB
    size, h = a["size"], a["height"]
    rings = [[(x, y, z) for x, z in square(0.0, 0.0, size * k, turn, 3.0 * k)] for k, y in
             ((1.0, -L.PROUD + 1.0), (1.0, -L.PROUD - h * 0.6), (0.82, -L.PROUD - h * 0.92), (0.5, -L.PROUD - h))]
    part = solid(name, rings, m["key"])
    return part


# ---- The card and the screens ----------------------------------------------------------------------------------------

def card(m):
    """The game card, its foot's middle at its origin, standing in the slot, its label facing back."""
    w, h, t = L.CARD["size"]
    shell = box("card", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(shell, 0.8, segments=1)
    lip = box("lip", -w / 2 + 6.0, w / 2 - 6.0, -t / 2 - 0.8, t / 2 + 0.8, h - L.CARD["lip"], h, m["case"])
    bevel(lip, 0.6, segments=1)
    shell = join([shell, lip], "card")
    face = atlas_uv(L.REGIONS["card"], w, h)
    paint(shell, m["print"], lambda co: face(w / 2 - co.x, h - co.z), lambda c, n, name: n.y > 0.9 and c.y > t / 2 - 0.1)
    return shell


def screen(m, name):
    sw, sh = L.SCREEN["size"]
    return curved(name, sw, sh, 0.0, atlas_uv(L.REGIONS[name], 1.0, 1.0), m["glass"], nu=1, nv=1)


# ---- The focused clip ------------------------------------------------------------------------------------------------

HOVER = 72.0              # how far above its seat the card hovers: clear of the top


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def turned(degrees, lift):
    """The console turned by degrees about its line of sight, moved so it still stands on the floor, centred, lift
    above it."""
    t = math.radians(degrees)
    s, c = math.sin(t), math.cos(t)
    stand = W / 2 * abs(s) + H / 2 * abs(c)
    return Pose(x=-H / 2 * s, z=stand - H / 2 * c + lift, roll=degrees)


def timeline(f):
    # The card: it hovers showing its label, turns round and drops into the slot; later it rises out and goes.
    if f < 6 or f >= 226:
        crd = Pose(scale=HIDDEN)
    elif f < 14:
        crd = Pose(z=HOVER, spin=180.0, scale=appear(f, 6, 14))
    elif f < 30:
        crd = Pose(z=HOVER + 2.0 * math.sin(2 * math.pi * phase(f, 14, 30)), spin=180.0)
    elif f < 42:
        crd = Pose(z=HOVER + 6.0 * math.sin(math.pi * phase(f, 30, 42)), spin=180.0 + 180.0 * smooth(phase(f, 30, 42)))
    elif f < 52:
        crd = Pose(z=HOVER * (1 - ease_in(phase(f, 42, 52))), spin=360.0)
    elif f < 212:
        crd = Pose(spin=360.0)
    else:
        crd = Pose(z=HOVER * ease_out(phase(f, 212, 222)), spin=360.0, scale=max(HIDDEN, 1 - ease_in(phase(f, 218, 226))))

    # The console: it hops and turns over with FLIP, and back.
    if f < 108:
        console = Pose()
    elif f < 134:
        t = phase(f, 108, 134)
        console = turned(180.0 * smooth(t), 26.0 * math.sin(math.pi * t))
    elif f < 176:
        console = turned(180.0, 0.0)
    elif f < 202:
        t = phase(f, 176, 202)
        console = turned(180.0 + 180.0 * smooth(t), 26.0 * math.sin(math.pi * t))
    else:
        console = Pose(roll=360.0)

    def shown(name, f0, f1, *more):
        spans = [(f0, f1)] + list(zip(more[::2], more[1::2]))
        for a, b in spans:
            if a <= f < b:
                grow = min(1.0, (f - a + 1) / 4.0) if name == "title" else 1.0
                fade = 1.0 if name != "game" or b != 208 else min(1.0, (b - f) / 4.0)
                return Pose(axes=(1.0, 1.0, max(HIDDEN, grow * fade)))
        return Pose(scale=HIDDEN)
    flip = max(tap(f, 100), tap(f, 168))
    play = phase(f, 136, 168)
    rock = math.sin(math.pi * play)
    return {"card": crd, "console": console,
            "title": shown("title", 60, 88), "game": shown("game", 88, 104, 172, 208),
            "game_flipped": shown("game_flipped", 104, 172),
            "on": Pose(y=1.5 * tap(f, 56)), "off": Pose(y=1.5 * tap(f, 204)),
            "pause": Pose(y=1.5 * flip), "option2": Pose(y=1.5 * flip),
            "a_top": Pose(y=1.5 * tap(f, 84)),
            "a_bottom": Pose(y=1.5 * max(tap(f, f0) for f0 in (140, 156))),
            "b_bottom": Pose(y=1.5 * max(tap(f, f0) for f0 in (148, 162))),
            "dpad": Pose(pitch=7.0 * rock * math.sin(2 * math.pi * 2.0 * play),
                         spin=7.0 * rock * math.cos(2 * math.pi * 3.0 * play))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "lynx_print.png"))
    m = {n: material(n, L.COLOURS[n], r, printed if n in ("print", "glass") else None) for n, r in ROUGHNESS.items()}

    static = body(m) + [window(m)]
    moving = {}
    names = (("on", "off", "backlight"), ("option1", "pause", "option2"))
    for column, row_names in zip((L.LEFT_BUTTONS, L.RIGHT_BUTTONS), names):
        for name, z in zip(row_names, column["z"]):
            part, where = side_button(name, column["x"], z, m)
            if name in ("on", "off", "pause", "option2"):
                moving[name] = (part, where)
            else:
                part.data.transform(Matrix.Translation(where))
                static.append(part)
    for pair, turn, which in ((L.AB["top"], L.AB["turn"][0], "top"), (L.AB["bottom"], L.AB["turn"][1], "bottom")):
        for (x, z), letter in zip(pair, ("b", "a")):
            name = f"{letter}_{which}"
            part = ab_button(name, turn, m)
            where = Vector((x, 0.0, z + MID))
            if name in ("a_top", "a_bottom", "b_bottom"):
                moving[name] = (part, where)
            else:
                part.data.transform(Matrix.Translation(where))
                static.append(part)
    moving["dpad"] = dpad(m)
    console = join(static, "console")
    crd = card(m)
    (sx, sz) = L.SCREEN["at"]
    screens = {name: (screen(m, name), Vector((sx, -L.WINDOW["height"] - 0.15 - 0.1 * k, sz + MID)))
               for k, name in enumerate(("title", "game", "game_flipped"))}
    for obj in [console, crd] + [p for p, _ in moving.values()]:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the console; the console its parts at their places.
    root = bpy.data.objects.new("atarilynx_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    w, h, t = L.CARD["size"]
    seat = Vector((0.0, L.CARD["y"], H - h))
    placed = [(crd, seat)] + list(moving.values()) + list(screens.values())
    for part, where in placed:
        part.parent = console
        part.location = where
    nodes = {"console": console, "card": crd, **{n: p for n, (p, _) in moving.items()},
             **{n: p for n, (p, _) in screens.items()}}

    # The three-quarter view, then the spec's fit of the console at rest, as the root's transform.
    yaw, pitch = TILT
    tilt = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
    points = [tilt @ v.co for v in console.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [console, crd] + [p for p, _ in moving.values()] + [p for p, _ in screens.values()]
    print(f"Lynx: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(console.data)} the console), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
