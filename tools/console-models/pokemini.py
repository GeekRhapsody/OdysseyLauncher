"""The console theme's Pokémon mini system model (godot/themes/console/models/systems/pokemini.glb): the Pokémon mini
in Wooper Blue.

Built in Blender from its traced outline (pokemini_layout.py has the measurements, taken from photographs): the front
half, frosted clear plastic, and the back half, solid blue, each the outline drawn smooth and given its depth, their
edges rounded; the black oval standing on the face, the cartridge slot cut into the back half's top. The printing is
one texture, drawn by pokemini_print.py: the face (its insides showing faintly through it), the oval, the LCD's
screens, the cartridge's label and the D-pad's arrows.

A small node tree: a root (the turn to a three-quarter view, TILT: its left end towards the viewer and its face tipped
up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the handheld, its origin at
its foot's middle; the handheld holding the D-pad, A, B, C, POWER, the cartridge (waiting over the slot, shrunk to
nothing) and the LCD's screens (all but the clock just behind the oval's face, so a swap never shows one shrinking:
at worst the LCD blinks blank), so they ride along when it moves.

The `focused` clip (8 s, looping): the cartridge hovers showing its label, turns round and drops into the slot; POWER,
and Odyssey's title; A, and the game's played on the D-pad and A; then the handheld's shaken (its shock sensor) and
bumps, rumbling; C, more play, and POWER again; the cartridge rises out and goes, and the clock comes back.

Four materials (clear, case, glass, grey) and one 1024² texture, within the system model budget. Run from the repo
root:

    python tools/console-models/pokemini_print.py artifacts/pokemini
    blender -b --factory-startup --python tools/console-models/pokemini.py -- artifacts/pokemini godot/themes/console/models/systems/pokemini.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pokemini_layout as L  # noqa: E402
from amiga import curved, paint, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402

TILT = (20.0, 10.0)       # degrees: yaw (left end nearer), pitch (face up)
ROUGHNESS = dict(clear=0.45, case=0.45, glass=0.6, grey=0.45)   # the flat face and oval catch the light: not too glossy


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def plate(name, points, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1 (y back from the face)."""
    return solid(name, [[(x, y, z) for x, z in points] for y in (y0, y1)], mat)


def disc(cx, cz, r, n=28):
    return [(cx + r * math.cos(2 * math.pi * k / n), cz + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def smooth_outline(points, steps=4):
    """The traced outline drawn smooth: a closed Catmull-Rom curve through its points."""
    out = []
    n = len(points)
    for i in range(n):
        p0, p1, p2, p3 = (Vector(points[(i + k) % n]) for k in (-1, 0, 1, 2))
        for s in range(steps):
            t = s / steps
            out.append(tuple(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3)))
    return out


def button(name, r, height, mat, dome=0.7, n=28):
    """A round button standing height out of the face, its top domed; its foot's middle at its origin."""
    rings = [[(x, y, z) for x, z in disc(0.0, 0.0, r * k, n)] for k, y in
             ((1.0, 1.0), (1.0, -height + dome), (0.82, -height + dome * 0.25), (0.45, -height))]
    return solid(name, rings, mat)


# ---- The handheld ----------------------------------------------------------------------------------------------------

def body(mats):
    """The two halves, the oval on the face and the slot in the back half's top; printed."""
    shape = smooth_outline(L.OUTLINE)
    face = atlas_uv(L.REGIONS["face"], 60.0, L.HEIGHT)
    front = plate("pokemini", shape, 0.0, L.SPLIT, mats["clear"])
    bevel(front, L.EDGE, segments=3)
    paint(front, mats["clear"], swatch("clear"), lambda c, n, name: True)
    paint(front, mats["clear"], lambda co: face(co.x + 30.0, L.HEIGHT - co.z), lambda c, n, name: n.y < -0.9)
    back = plate("back", shape, L.SPLIT, L.DEPTH, mats["case"])
    bevel(back, L.EDGE, segments=3)
    (sx0, sx1), (sy0, sy1) = L.SLOT["x"], L.SLOT["y"]
    boolean(back, box("slot", sx0, sx1, sy0, sy1, L.HEIGHT - L.SLOT["depth"], L.HEIGHT + 5.0, mats["glass"]))
    paint(back, mats["glass"], swatch("dark"), lambda c, n, name: name == "glass")

    (ox, oz), (rx, rz) = L.OVAL["at"], L.OVAL["r"]
    oval = plate("oval", [(ox + rx * math.cos(2 * math.pi * k / 64), oz + rz * math.sin(2 * math.pi * k / 64))
                          for k in range(64)], -L.OVAL["raised"], 0.3, mats["glass"])
    bevel(oval, 0.3, segments=1)
    print_oval = atlas_uv(L.REGIONS["oval"], 2 * rx, 2 * rz)
    paint(oval, mats["glass"], swatch("dark"), lambda c, n, name: True)
    paint(oval, mats["glass"], lambda co: print_oval(co.x - (ox - rx), (oz + rz) - co.z), lambda c, n, name: n.y < -0.9)
    return join([front, back, oval], "pokemini")


def dpad(mats):
    """The D-pad, a cross standing out of its well, its arrows printed on its top; its middle at its origin."""
    s, a = L.DPAD["size"], L.DPAD["arm"]
    h, w = s / 2, a / 2
    cross = [(w, -h), (w, -w), (h, -w), (h, w), (w, w), (w, h), (-w, h), (-w, w), (-h, w), (-h, -w), (-w, -w), (-w, -h)]
    part = plate("dpad", cross, -L.DPAD["height"], 0.5, mats["clear"])
    bevel(part, 0.5, segments=2)
    top = atlas_uv(L.REGIONS["dpad"], s, s)
    paint(part, mats["clear"], swatch("case"), lambda c, n, name: True)
    paint(part, mats["clear"], lambda co: top(co.x + h, h - co.z), lambda c, n, name: n.y < -0.9)
    return part


def c_button(mats):
    """C, a bar along the right side's upper part, leaning with it; its middle at its origin."""
    (z0, z1), width, out = L.C["z"], L.C["width"], L.C["out"]
    shape = smooth_outline(L.OUTLINE)
    side = [p for p in shape if p[0] > 0 and z0 - 4.0 < p[1] < z1 + 4.0]
    lo = min(side, key=lambda p: abs(p[1] - z0))
    hi = min(side, key=lambda p: abs(p[1] - z1))
    length = math.hypot(hi[0] - lo[0], hi[1] - lo[1])
    part = box("c", -1.5, out, -width / 2, width / 2, -length / 2, length / 2, mats["case"])
    bevel(part, 0.6, segments=2)
    lean = math.atan2(hi[0] - lo[0], hi[1] - lo[1])           # the side leans in as it rises
    part.data.transform(Matrix.Rotation(lean, 4, "Y"))
    return part, Vector(((lo[0] + hi[0]) / 2, L.SPLIT + 3.0, (lo[1] + hi[1]) / 2))


def cartridge(mats):
    """The cartridge, its foot's middle at its origin, its label on its back (+y)."""
    w, h, t = L.CART["size"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, mats["clear"])
    bevel(shell, 1.0, segments=2)
    paint(shell, mats["clear"], swatch("cart"), lambda c, n, name: True)
    lw, lh = L.CART["label"]
    label = box("label", -lw / 2, lw / 2, t / 2 - 0.2, t / 2 + 0.12, h - 2.5 - lh, h - 2.5, mats["clear"])
    face = atlas_uv(L.REGIONS["cart"], lw, lh)
    paint(label, mats["clear"], swatch("cart"), lambda c, n, name: True)
    paint(label, mats["clear"], lambda co: face(lw / 2 - co.x, h - 2.5 - co.z), lambda c, n, name: n.y > 0.9)
    return join([shell, label], "cartridge")


def screen(mats, name):
    lw, lh = L.LCD["size"]
    return curved(name, lw, lh, 0.0, atlas_uv(L.REGIONS[name], 1.0, 1.0), mats["glass"], nu=1, nv=1)


# ---- The focused clip ------------------------------------------------------------------------------------------------

HOVER = 40.0              # how far above its seat the cartridge hovers: clear of the top
BEHIND = 0.3              # how far back a screen that isn't shown goes: behind the oval's face
SCREENS = ("clock", "title", "game_1", "game_2", "hit")


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def lit(f):
    """Which screen the LCD shows at frame f."""
    if f < 61 or f >= 206:
        return "clock"
    if f < 92:
        return "title"
    if 156 <= f < 186:
        return "hit"
    return "game_1" if (f // 8) % 2 == 0 else "game_2"


def timeline(f):
    # The cartridge: it hovers showing its label, turns round and drops in; later it rises out and goes.
    if f < 6 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 14:
        cart = Pose(z=HOVER, spin=180.0, scale=appear(f, 6, 14))
    elif f < 28:
        cart = Pose(z=HOVER + 1.5 * math.sin(2 * math.pi * phase(f, 14, 28)), spin=180.0)
    elif f < 40:
        t = phase(f, 28, 40)
        cart = Pose(z=HOVER + 5.0 * math.sin(math.pi * t), spin=180.0 + 180.0 * smooth(t))
    elif f < 50:
        cart = Pose(z=HOVER * (1 - ease_in(phase(f, 40, 50))), spin=360.0)
    elif f < 210:
        cart = Pose(spin=360.0, squash=0.05 * math.sin(math.pi * phase(f, 50, 56)))
    else:
        cart = Pose(z=HOVER * ease_out(phase(f, 210, 220)), spin=360.0,
                    scale=max(HIDDEN, 1 - ease_in(phase(f, 216, 226))))

    # The handheld: shaken (rolled to and fro about its foot), then the bump's rumble.
    if 150 <= f < 166:
        t = phase(f, 150, 166)
        hand = Pose(roll=16.0 * math.sin(2 * math.pi * 2.0 * t) * math.sin(math.pi * t))
    elif 166 <= f < 184:
        k = 1 - phase(f, 166, 184)
        hand = Pose(x=0.6 * k * (1 if f % 2 else -1), z=0.35 * k * (1 if (f // 2) % 2 else -1))
    else:
        hand = Pose()

    # The D-pad rocks while the game's played; A fires; C once.
    t = phase(f, 94, 148)
    k = math.sin(math.pi * t)
    pad = Pose(pitch=9.0 * k * math.sin(2 * math.pi * 3.0 * t), roll=9.0 * k * math.cos(2 * math.pi * 2.0 * t))
    poses = {name: Pose() if name == lit(f) else Pose(y=BEHIND) for name in SCREENS}
    poses.update({"cartridge": cart, "pokemini": hand, "dpad": pad,
                  "power": Pose(y=0.8 * max(tap(f, 57), tap(f, 202))),
                  "a": Pose(y=1.2 * max(tap(f, f0) for f0 in (88, 104, 120, 136, 192))),
                  "b": Pose(y=1.2 * max(tap(f, f0) for f0 in (112, 140))),
                  "c": Pose(x=-0.9 * tap(f, 188, 4))})
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "pokemini_print.png"))
    mats = {"clear": material("clear", L.COLOURS["print"], ROUGHNESS["clear"], printed),
            "case": material("case", L.COLOURS["case"], ROUGHNESS["case"]),
            "glass": material("glass", L.COLOURS["glass"], ROUGHNESS["glass"], printed),
            "grey": material("grey", L.COLOURS["grey"], ROUGHNESS["grey"])}

    console = body(mats)
    parts = {"dpad": (dpad(mats), Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1]))), "c": c_button(mats)}
    (px, pz), pr = L.POWER["at"], L.POWER["r"]
    parts["power"] = (button("power", pr, L.POWER["height"], mats["grey"], 0.4, 20), Vector((px, 0.0, pz)))
    for name in ("a", "b"):
        x, z = L.BUTTONS[name]
        parts[name] = (button(name, L.BUTTONS["r"], L.BUTTONS["height"], mats["case"]), Vector((x, 0.0, z)))
    w, h, t = L.CART["size"]
    parts["cartridge"] = (cartridge(mats), Vector((0.0, sum(L.SLOT["y"]) / 2, L.HEIGHT + L.CART["out"] - h)))
    lx, lz = L.LCD["at"]
    for name in SCREENS:
        parts[name] = (screen(mats, name), Vector((lx, -L.OVAL["raised"] - 0.05, lz)))
    for obj in [console] + [p for p, _ in parts.values()]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the handheld; the handheld its parts at their places.
    root = bpy.data.objects.new("pokemini_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    for part, where in parts.values():
        part.parent = console
        part.location = where
    nodes = {"pokemini": console, **{n: p for n, (p, _) in parts.items()}}

    yaw, pitch = TILT
    tilt = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
    points = [tilt @ v.co for v in console.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [console] + [p for p, _ in parts.values()]
    print(f"Pokémon mini: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(console.data)} the body), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
