"""The console theme's Neo Geo Pocket Color and Neo Geo Pocket system models
(godot/themes/console/models/systems/ngpc.glb and ngp.glb).

Built in Blender from the real handhelds' proportions (neogeo_pocket_layout.py has the measurements, taken from
photographs): the Neo Geo Pocket Color in Platinum Blue, and the Neo Geo Pocket, its monochrome forerunner, in carbon
black. Each body is its front outline lofted back, its edges rounded, the back plate behind it with the cartridge's
recess cut into its top and the finger rest into its foot. The screen's bezel stands on the front, the notched ring
round the stick, POWER, OPTION, A and B (the Color's in clear rings) and the dimples on it. The printing is one texture
each, drawn by neogeo_pocket_print.py: the front (planar-mapped onto the faces facing forward), the screens, the
cartridge's label, and swatches.

Each is a small node tree: a root (the turn to a three-quarter view, TILT: its left end towards the viewer and its face
tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the console, its origin
at its foot's middle; the console holding the cartridge (waiting in its recess, shrunk to nothing), POWER, the lit power
light, the stick, A and B, and three screens (the start-up logo, Odyssey's title, a moment of its play), shrunk to
nothing, so they ride along when the console moves.

The `focused` clip (8 s, looping) plays a game: the cartridge hovers over the console showing its label, turns round
and drops into its recess; POWER, the light, the start-up logo and the title; A, and the game is played on the clicky
stick, A and B; then a special move, the stick swept round a quarter and A, and the console hops with it. Then POWER
again, and the cartridge rises out and goes.

Five materials (case, key, ring, glass, print) and one texture each, within the system model budget. Run from the repo
root:

    python tools/console-models/neogeo_pocket_print.py artifacts/neogeo_pocket
    blender -b --factory-startup --python tools/console-models/neogeo_pocket.py -- artifacts/neogeo_pocket ngpc godot/themes/console/models/systems/ngpc.glb

and the same with ngp.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neogeo_pocket_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, hop, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, triangles  # noqa: E402
from msx_layout import inset  # noqa: E402

TILT = (20.0, 10.0)       # degrees: yaw (left end nearer), pitch (face up)
ROUGHNESS = dict(case=0.35, key=0.3, ring=0.15, glass=0.4, print=0.45)


# ---- UVs and shapes --------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def plate(name, points, y0, y1, mat):
    """A solid from an (x, z) outline, from y0 to y1 (y back from the front face)."""
    return solid(name, [[(x, y, z) for x, z in points] for y in (y0, y1)], mat)


def disc(cx, cz, r, n=28):
    return [(cx + r * math.cos(2 * math.pi * k / n), cz + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def button(name, r, height, mat, dome=0.8, n=28):
    """A round button standing height out of the front, its top domed; its foot's middle at its origin."""
    rings = [[(x, y, z) for x, z in disc(0.0, 0.0, r * k, n)] for k, y in
             ((1.0, 1.0), (1.0, -height + dome), (0.82, -height + dome * 0.25), (0.45, -height))]
    return solid(name, rings, mat)


# ---- The console -----------------------------------------------------------------------------------------------------

def body(m, mats):
    """The body: its slab, the back plate with the recesses, the bezel, the stick's ring, the rings round A and B,
    OPTION and the dimples; its front printed."""
    w, h, _ = m["size"]
    slab, g = m["slab"], m["grips"]
    face = atlas_uv(L.REGIONS["front"], w, h)

    def front_uv(co):
        return face(co.x + w / 2, h - co.z)
    shape = L.outline(m)
    shell = plate("console", shape, 0.0, slab, mats["case"])
    bevel(shell, 2.6, segments=3)
    paint(shell, mats["print"], front_uv, lambda c, n, name: n.y < -0.9)
    rings = [[(x, slab - 1.0, z) for x, z in shape],
             [(x, slab + g["depth"] * 0.6, z) for x, z in inset(shape, 1.2)],
             [(x, slab + g["depth"], z) for x, z in inset(shape, 4.0)]]
    back = solid("back", rings, mats["case"])
    (rx0, rx1), (rz0, _) = m["recess"]["x"], m["recess"]["z"]
    boolean(back, box("recess", rx0, rx1, slab - 0.5, slab + g["depth"] + 5.0, rz0, h + 5.0, mats["case"]))
    boolean(back, box("rest", -22.0, 22.0, slab + 2.0, slab + g["depth"] + 5.0, -5.0, 13.0, mats["case"]))
    (bx, bz), (bw, bh) = m["bezel"]["at"], m["bezel"]["size"]
    bezel = plate("bezel", rounded(bx, bz, bw, bh, m["bezel"]["r"], 3), -0.6, 0.5, mats["glass"])
    bevel(bezel, 0.4, segments=1)
    paint(bezel, mats["glass"], front_uv, lambda c, n, name: n.y < -0.9)
    paint(bezel, mats["glass"], swatch("dark"), lambda c, n, name: n.y >= -0.9)
    (sx, sz), (r0, r1) = m["stick"]["at"], m["stick"]["ring"]
    ring = solid("ring", [[(x, y, z) for x, z in disc(sx, sz, r, 40)] for r, y in ((r0, 1.0), (r0, -1.0),
                                                                                    (r0 - 0.8, -1.8))], mats["ring"])
    boolean(ring, plate("ring_hole", disc(sx, sz, r1, 32), -5.0, 5.0, mats["ring"]))
    parts = [shell, back, bezel, ring]
    for name in ("a", "b"):
        b = m[name]
        if b["ring"]:
            ax, az = b["at"]
            clear = plate(name + "_ring", disc(ax, az, b["ring"], 32), -1.2, 1.0, mats["ring"])
            boolean(clear, plate("hole", disc(ax, az, b["r"] + 0.3, 28), -5.0, 5.0, mats["ring"]))
            parts.append(clear)
    (ox, oz), orr = m["option"]["at"], m["option"]["r"]
    option = button("option", orr, 1.4, mats["key"], 0.5, 20)
    option.data.transform(Matrix.Translation((ox, 0.0, oz)))
    parts.append(option)
    for x in m["dimples"]["x"]:
        for z in m["dimples"]["z"]:
            dimple = button("dimple", 0.8, 0.45, mats["case"], 0.3, 10)
            dimple.data.transform(Matrix.Translation((x, 0.0, z)))
            parts.append(dimple)
    return join(parts, "console")


def power(m, mats):
    (px, pz), (pw, ph) = m["power"]["at"], m["power"]["size"]
    part = plate("power", rounded(0.0, 0.0, pw, ph, ph / 2 - 0.01, 5), -1.6, 1.0, mats["key"])
    bevel(part, 0.5, segments=1)
    return part, Vector((px, 0.0, pz))


def light(m, mats):
    (gx, gz), r = m["light"]["at"], m["light"]["r"]
    part = plate("power_light", disc(0.0, 0.0, r + 0.1, 14), -0.25, 0.1, mats["print"])
    paint(part, mats["print"], swatch("lit"), lambda c, n, name: True)
    return part, Vector((gx, 0.0, gz))


def stick(m, mats):
    """The stick, its foot's middle at its origin: its cap, and the Color's square nub on it."""
    r = m["stick"]["cap"]
    cap = solid("stick", [[(x, y, z) for x, z in disc(0.0, 0.0, r * k, 28)] for k, y in
                          ((1.0, 1.0), (1.0, -3.6), (0.9, -4.6), (0.55, -5.0))], mats["key"])
    if m["stick"]["nub"]:
        nub = plate("nub", rounded(0.0, 0.0, 2.6, 2.6, 0.5, 2), -5.6, -4.6, mats["ring"])
        cap = join([cap, nub], "stick")
    sx, sz = m["stick"]["at"]
    return cap, Vector((sx, 0.0, sz))


def cartridge(m, mats):
    """The cartridge, its foot's middle at its origin, its label on its back (+y)."""
    w, h, t = m["cart"]["size"]
    shell = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, mats["print"])
    bevel(shell, 1.0, segments=2)
    paint(shell, mats["print"], swatch("cart"), lambda c, n, name: True)
    lw, lh = L.CART_LABEL
    label = box("label", -lw / 2, lw / 2, t / 2 - 0.2, t / 2 + 0.15, h - 3.0 - lh, h - 3.0, mats["print"])
    face = atlas_uv(L.REGIONS["cart"], lw, lh)
    paint(label, mats["print"], lambda co: face(lw / 2 - co.x, h - 3.0 - co.z), lambda c, n, name: n.y > 0.9)
    paint(label, mats["print"], swatch("cart"), lambda c, n, name: n.y <= 0.9)
    grip = [box("ridge", -w / 2 + 6.0, w / 2 - 6.0, -t / 2 - 0.5, t / 2 + 0.5, h - 1.6 - 2.2 * k, h - 0.8 - 2.2 * k,
                mats["print"]) for k in range(1)]
    for part in grip:
        paint(part, mats["print"], swatch("cart"), lambda c, n, name: True)
    return join([shell, label] + grip, "cartridge")


def screen(m, mats, name):
    lw, lh = m["lcd"]["size"]
    return curved(name, lw, lh, 0.0, atlas_uv(L.REGIONS[name], 1.0, 1.0), mats["glass"], nu=1, nv=1)


# ---- The focused clip ------------------------------------------------------------------------------------------------

HOVER = 56.0              # how far above its seat the cartridge hovers: clear of the top


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    # The cartridge: it hovers showing its label, turns round and drops in; later it rises out and goes.
    if f < 6 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 14:
        cart = Pose(z=HOVER, spin=180.0, scale=appear(f, 6, 14))
    elif f < 30:
        cart = Pose(z=HOVER + 2.0 * math.sin(2 * math.pi * phase(f, 14, 30)), spin=180.0)
    elif f < 42:
        t = phase(f, 30, 42)
        cart = Pose(z=HOVER + 7.0 * math.sin(math.pi * t), spin=180.0 + 180.0 * smooth(t))
    elif f < 52:
        cart = Pose(z=HOVER * (1 - ease_in(phase(f, 42, 52))), spin=360.0)
    elif f < 210:
        cart = Pose(spin=360.0, squash=0.05 * math.sin(math.pi * phase(f, 52, 58)))
    else:
        cart = Pose(z=HOVER * ease_out(phase(f, 210, 220)), spin=360.0, scale=max(HIDDEN, 1 - ease_in(phase(f, 216, 226))))

    # The screens: the start-up logo grows in, the title, the game; all off once POWER's pressed again.
    def shown(f0, f1):
        if f0 <= f < f1:
            return Pose(axes=(1.0, 1.0, max(HIDDEN, min(1.0, (f - f0 + 1) / 4.0))))
        return Pose(scale=HIDDEN)

    # The stick: circles while the game's played, then the special move's quarter-circle forward.
    t = phase(f, 120, 150)
    k = math.sin(math.pi * t)
    if 120 <= f < 150:
        stick = Pose(pitch=14.0 * k * math.sin(2 * math.pi * 2.0 * t), roll=14.0 * k * math.cos(2 * math.pi * 2.0 * t))
    elif 150 <= f < 162:
        a = math.radians(-90.0 + 90.0 * smooth(phase(f, 150, 158)))       # down, then round to forward
        e = math.sin(math.pi * phase(f, 150, 162))
        stick = Pose(pitch=-16.0 * e * math.sin(a), roll=16.0 * e * math.cos(a))
    else:
        stick = Pose()
    jump = hop(f, 160, 176, 16.0)
    console = Pose(z=jump, squash=-0.05 * math.sin(math.pi * phase(f, 160, 166)) + 0.06 * math.sin(math.pi * phase(f, 175, 181)))
    lit = 60 <= f < 200
    return {"cartridge": cart, "console": console,
            "boot": shown(60, 92), "title": shown(92, 118), "game": shown(118, 198),
            "power": Pose(y=1.2 * max(tap(f, 56), tap(f, 196))), "power_light": Pose() if lit else Pose(scale=HIDDEN),
            "stick": stick, "a": Pose(y=1.4 * max(tap(f, f0) for f0 in (112, 128, 140, 158))),
            "b": Pose(y=1.4 * max(tap(f, f0) for f0 in (134, 146, 182)))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, kind, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    m = L.MODELS[kind]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, f"{kind}_print.png"))
    mats = {n: material(n, m["colours"][n], r, printed if n in ("print", "glass") else None)
            for n, r in ROUGHNESS.items()}

    console = body(m, mats)
    parts = {"power": power(m, mats), "power_light": light(m, mats), "stick": stick(m, mats)}
    for name in ("a", "b"):
        b = m[name]
        parts[name] = (button(name, b["r"], 2.4, mats["key"]), Vector((*b["at"][:1], 0.0, b["at"][1])))
    w, h, _ = m["size"]
    ct = m["cart"]["size"][2]
    parts["cartridge"] = (cartridge(m, mats), Vector((0.0, m["slab"] + ct / 2 + 0.3,
                                                       h + m["cart"]["protrudes"] - m["cart"]["size"][1])))
    (lx, lz) = m["lcd"]["at"]
    for k, name in enumerate(("boot", "title", "game")):
        parts[name] = (screen(m, mats, name), Vector((lx, -0.7 - 0.05 * k, lz)))
    for obj in [console] + [p for p, _ in parts.values()]:
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the console; the console its parts at their places.
    root = bpy.data.objects.new(f"{kind}_root", None)
    scene.collection.objects.link(root)
    console.parent = root
    for part, where in parts.values():
        part.parent = console
        part.location = where
    nodes = {"console": console, **{n: p for n, (p, _) in parts.items()}}

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
    meshes = [console] + [p for p, _ in parts.values()]
    print(f"{m['name']}: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(console.data)} the console), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
