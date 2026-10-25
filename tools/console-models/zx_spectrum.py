"""The console theme's ZX Spectrum system model (godot/themes/console/models/systems/zxspectrum.glb): a ZX Spectrum
48K plugged into a portable television, the copyright message on its screen.

Built in Blender from the real computer's proportions (zx_spectrum_layout.py has the measurements, taken from
photographs). The computer is its side outline extruded across its width: the thin front edge, the plate rising to the
rounded step, the hump across its back. Its 40 rubber keys stand on the plate in four rows, each a rounded block
rounding over to its printed top. Behind it stands the television, made up in the period's look: a silver case with
its tube's housing tapering behind, the black front sunk into it, the screen's opening sloping in to the curved
glass, the channel buttons, the volume knob and the power button standing out of the control strip, and a carrying
handle on top. The printing is two textures drawn by zx_spectrum_print.py: the computer's top seen from above
(planar-mapped onto every face facing up: the keywords, the key tops, the hump's names, the rainbow) and the
television's front; and the screens (the glass at rest shows the copyright message), the paper's states and the
border's stripes.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the keys the clip presses (J, SYMBOL SHIFT, P and ENTER) and, over the glass, the paper's states (the middle of
the screen) and the border's (round it), all shrunk to nothing at rest, so the card is the set with the copyright
message on the screen.

The `focused` clip (8 s, looping) loads a game from tape: J types LOAD, SYMBOL SHIFT and P twice type the quotes,
ENTER; the border flashes red and cyan with the pilot tone, blue and yellow as the header loads (Program: ODYSSEY),
red and cyan again, then blue and yellow as the loading screen arrives, a third at a time in the Spectrum's
interleaved lines, then its colours; the border goes black, and the game waits; then the screen resets to the
copyright message.

Six materials (case, print, key, tv, dark, glass) and two textures, within the system model budget. Run from the
repo root:

    python tools/console-models/zx_spectrum_print.py artifacts/zx
    blender -b --factory-startup --python tools/console-models/zx_spectrum.py -- artifacts/zx godot/themes/console/models/systems/zxspectrum.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zx_spectrum_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -28.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 22.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.5, print=0.45, key=0.75, tv=0.4, dark=0.6, glass=0.2)
TYPED = ("j", "symbol_shift", "p", "enter")
PRESS = 2.5          # how far a key goes down
GRID = (20, 16)      # the screen's cells across and down: the border is two cells deep all round


def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    """The computer's top seen from above."""
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(where):
    x, y = where
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


# ---- The computer ----------------------------------------------------------------------------------------------------

def computer(m):
    body = prism_x("spectrum", L.profile(), -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 1.2, segments=2)
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.9)
    return body


def keys(m):
    """The rubber keys, each a rounded block on the plate rounding over to its printed top: the ones the clip presses
    apart."""
    static, moving = [], {}
    h, r = L.KEY["height"], L.KEY["radius"]
    for k, (x0, y0, x1, y1) in L.keys_with_rects():
        cx, cy, w, d = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        base = L.plate_z(cy)
        rings = [[(x, y, base + z) for x, y in rounded(cx, cy, w - 2 * inset, d - 2 * inset, r - inset, 3)]
                 for inset, z in ((0.0, -0.6), (0.0, h - 1.3), (0.45, h - 0.4), (1.0, h))]
        cap = solid(k[0], rings, m["key"])
        paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.95)
        if k[0] in TYPED:
            moving[k[0]] = cap
        else:
            static.append(cap)
    return static, moving


# ---- The television --------------------------------------------------------------------------------------------------

def television(m, glass_material, glass_uv):
    """The television, its front's middle at the origin, facing -y: its case and housing, the black front with the
    screen's opening, the glass (glass_uv across it), the controls and the handle."""
    T = L.TV
    w, h, d = T["width"], T["height"], T["depth"]
    b, s = T["bezel"], T["screen"]
    case = box("tv", -w / 2, w / 2, 0.0, d * 0.62, 0.0, h, m["tv"])
    bevel(case, 8.0, segments=3)
    boolean(case, box("bezel", b["x"][0], b["x"][1], -5.0, b["depth"], b["z"][0], b["z"][1], m["tv"]))
    outer, inner = rounded(s["x"], s["z"], *s["opening"]), rounded(s["x"], s["z"], *s["inner"])
    boolean(case, solid("opening", [[(x, y, z) for x, z in outline] for outline, y in
                                    ((outer, -10.0), (outer, b["depth"] - 0.01), (inner, s["depth"]),
                                     (inner, s["depth"] + 1.0))], m["dark"]))
    front = atlas_uv(L.PRINT_REGIONS["tv"], w, h)
    paint(case, m["print"], lambda co: front(co.x + w / 2, h - co.z),
          lambda c, n, name: name == "tv" and n.y < -0.9 and abs(c.y - b["depth"]) < 0.3)
    paint(case, m["dark"], swatch(L.PRINT_SWATCHES["black"]),
          lambda c, n, name: name == "tv" and abs(n.y) < 0.5 and 0.2 < c.y < b["depth"] - 0.1
          and b["x"][0] - 0.5 < c.x < b["x"][1] + 0.5 and b["z"][0] - 0.5 < c.z < b["z"][1] + 0.5)

    # The tube's housing, tapering behind the case.
    housing = solid("housing", [[(x, y, z) for x, z in rounded(0.0, h * 0.5, hw, hh, r, 4)]
                                for y, hw, hh, r in ((d * 0.6, w - 26.0, h - 26.0, 18.0), (d, w * 0.62, h * 0.6, 24.0))],
                    m["tv"])
    bevel(housing, 4.0, segments=2, angle=50)

    parts = [case, housing]
    gw, gh = T["glass"]["size"]
    glass = curved("glass", gw, gh, T["glass"]["bulge"], glass_uv, glass_material)
    glass.data.transform(Matrix.Translation((s["x"], s["depth"], s["z"])))
    parts.append(glass)

    # The controls standing out of the black front: the channel buttons, the volume knob, the power button.
    bw, bh, out = T["button"]
    for bx, bz in T["buttons"]:
        button = box("button", bx - bw / 2, bx + bw / 2, b["depth"] - out, b["depth"] + 0.5, bz - bh / 2, bz + bh / 2,
                     m["tv"])
        bevel(button, 0.8, segments=1)
        parts.append(button)
    k = T["knob"]
    ring = [(k["x"] + k["r"] * math.cos(2 * math.pi * i / 24), k["z"] + k["r"] * math.sin(2 * math.pi * i / 24))
            for i in range(24)]
    knob = solid("knob", [[(x, y, z) for x, z in ring] for y in (b["depth"] + 0.5, b["depth"] - k["out"])], m["dark"])
    bevel(knob, 1.0, segments=2)
    parts.append(knob)
    p = T["power"]
    pw, ph, pout = p["size"]
    power = box("power", p["x"] - pw / 2, p["x"] + pw / 2, b["depth"] - pout, b["depth"] + 0.5, p["z"] - ph / 2,
                p["z"] + ph / 2, m["tv"])
    bevel(power, 1.0, segments=1)
    parts.append(power)

    # The handle: a bar across the top on two posts.
    hd = T["handle"]
    y0, y1 = hd["y"]
    for side in (-1, 1):
        post = box("post", side * hd["x"] - 5.0, side * hd["x"] + 5.0, y0 + 28.0, y0 + 42.0, h - 3.0,
                   h + hd["height"], m["tv"])
        bevel(post, 1.5, segments=1)
        parts.append(post)
    bar = box("bar", -hd["x"] - 6.0, hd["x"] + 6.0, y0 + 26.0, y0 + 44.0, h + hd["height"] - hd["thickness"],
              h + hd["height"], m["tv"])
    bevel(bar, 2.5, segments=2)
    parts.append(bar)

    at = Matrix.Translation((T["at"][0], T["at"][1], 0.0))
    for obj in parts:
        obj.data.transform(at)
    return parts


def screens(m):
    """The screen's states over the glass, each its middle at its origin: the paper's (the middle of the screen,
    PAPERS) and the border's (round it, BORDERS: a column of stripes stretched across)."""
    T = L.TV
    gw, gh = T["glass"]["size"]
    pw, ph = T["paper"]
    nu, nv = GRID
    i0, i1 = round(nu * (1 - pw) / 2), round(nu * (1 + pw) / 2)
    j0, j1 = round(nv * (1 - ph) / 2), round(nv * (1 + ph) / 2)

    def inside(i, j):
        return i0 <= i < i1 and j0 <= j < j1
    nodes = {}
    for k, name in enumerate(L.PAPERS):
        region = atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0)
        uv = lambda a, b, region=region: region((a - (1 - pw) / 2) / pw, (b - (1 - ph) / 2) / ph)
        nodes["paper_" + name] = (curved("paper_" + name, gw, gh, T["glass"]["bulge"], uv, m["glass"], nu, nv, inside),
                                  -0.6 - 0.06 * k)
    for k, name in enumerate(L.BORDERS):
        region = atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0)
        uv = lambda a, b, region=region: region(0.5, b)
        nodes["border_" + name] = (curved("border_" + name, gw, gh, T["glass"]["bulge"], uv, m["glass"], nu, nv,
                                          lambda i, j: not inside(i, j)), -0.4 - 0.03 * k)
    return nodes


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    """A key pressed at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def pressed(depth):
    return Pose(z=-PRESS * depth)


def timeline(f):
    poses = {"j": pressed(tap(f, 22)), "p": pressed(tap(f, 33) + tap(f, 41)), "enter": pressed(tap(f, 50)),
             "symbol_shift": pressed(smooth(phase(f, 30, 33)) * (1 - smooth(phase(f, 45, 49))))}

    # The paper: what's typed, then the header's name, the loading screen a third at a time, its colours.
    paper = None
    for name, f0, f1 in (("load", 24, 41), ("load2", 41, 54), ("blank", 54, 86), ("header", 86, 104),
                         ("third1", 104, 128), ("third2", 128, 152), ("mono", 152, 168), ("colour", 168, 226)):
        if f0 <= f < f1:
            paper = name
    for name in L.PAPERS:
        poses["paper_" + name] = Pose() if name == paper else Pose(scale=HIDDEN)
    if f >= 220 and paper == "colour":                             # the reset: the picture shrinks away
        poses["paper_colour"] = Pose(axes=(1.0, 1.0, max(HIDDEN, 1 - ease_in(phase(f, 220, 226)))))

    # The border: the pilot tone's broad stripes, the data's thin ones, flickering; black once the game is in.
    if 54 <= f < 80 or 86 <= f < 104:
        border = "pilot_a" if (f // 3) % 2 == 0 else "pilot_b"
    elif 80 <= f < 86 or 104 <= f < 180:
        border = "data_a" if (f // 2) % 2 == 0 else "data_b"
    elif 180 <= f < 226:
        border = "black"
    else:
        border = None
    for name in L.BORDERS:
        poses["border_" + name] = Pose() if name == border else Pose(scale=HIDDEN)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "zx_spectrum_print.png"))
    media = bpy.data.images.load(os.path.join(images, "zx_spectrum_media.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", glass="#FFFFFF", dark="#0A0A0B")
    textures = dict(print=printed, glass=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    static, moving = keys(m)
    glass_uv = atlas_uv(L.MEDIA_REGIONS["glass"], 1.0, 1.0)
    whole = join([computer(m)] + static + television(m, m["glass"], glass_uv), "zxspectrum")
    for obj in [whole] + list(moving.values()):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the keys and the screens.
    root = bpy.data.objects.new("zxspectrum_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    for part in moving.values():
        part.parent = whole
    s = L.TV["screen"]
    middle = Vector((L.TV["at"][0] + s["x"], L.TV["at"][1] + s["depth"], s["z"]))
    nodes = dict(moving)
    for name, (part, offset) in screens(m).items():
        part.parent = whole
        part.location = middle + Vector((0.0, offset, 0.0))
        nodes[name] = part

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"ZX Spectrum: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
