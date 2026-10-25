"""The console theme's Apple II system model (godot/themes/console/models/systems/apple2.glb): an Apple IIe, two Disk
II drives on its lid and a Monitor II on them, the IIe's banner on the screen while it looks for a disk.

Built in Blender from the real machines' proportions (apple2_layout.py has the measurements, taken from photographs).
The computer is its side outline extruded across its width, standing on its dark base plate: the low front edge
undercut beneath, the top sloping up to the flat top over its back two thirds; the keyboard's well and RESET's recess
are cut into the slope, and the comb of vent slots into each side. Its 64 keys (the US layout) stand in the well,
tapering to their printed tops, and the power light stands among them, lit. The drives are boxes, each with its front
panel sunk into its front, the slot and the finger recess cut into it, the door's lever standing over the slot, and
the vents in its sides. The monitor is its side outline extruded (its back sloping in at the top), the surround sunk
into its front and the opening sloping in to the curved glass, a seam down its control strip. The printing is two
textures drawn by apple2_print.py: the computer's top seen from above (planar-mapped onto every face facing up: the
key tops and legends, the badge, the lid's seams), the drives' panels and the monitor's strip, with swatches; and the
screens in green phosphor and the floppy.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right end towards the viewer, the
top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the set
holding the floppy, drive 1's door (on its hinge) and its lit IN USE light, the three screens over the glass (Odyssey's
title screen two and five eighths loaded, and whole), and Control and RESET. The floppy waits in drive 1 shrunk to
nothing, the light and the screens are shrunk to nothing, so at rest the card is the set with the banner on the
screen.

The `focused` clip (8 s, looping) boots a game: the floppy slides into drive 1 and its door turns down over it; IN
USE lights while the title screen arrives in hi-res's order, every eighth line first. Then Control and RESET go down
together, the banner's back, the door turns up and the floppy comes out and goes.

Seven materials (case, keys, bezel, dark, print, glass, disk) and two textures, within the system model budget. Run
from the repo root:

    python tools/console-models/apple2_print.py artifacts/apple2
    blender -b --factory-startup --python tools/console-models/apple2.py -- artifacts/apple2 godot/themes/console/models/systems/apple2.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apple2_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 20.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.6, keys=0.55, bezel=0.6, dark=0.7, print=0.5, glass=0.15, disk=0.5)
RESET_KEYS = ("control", "reset")
TOP_DEPTH = 250.0    # the top region's depth (apple2_print.py's): the top in front of the drives

# The top's frame: x across, s up the slope from the front edge, h off it.
SLOPE_FRAME = Matrix.Translation((0.0, L.TIP[0], L.TIP[1])) @ Matrix.Rotation(L.SLOPE, 4, "X")
PRESS = SLOPE_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.PRINT_REGIONS["top"], L.WIDTH, TOP_DEPTH)


def top_uv(co):
    """The computer's top in front of the drives, seen from above."""
    return TOP(co.x + L.WIDTH / 2, TOP_DEPTH - co.y)


def swatch(where):
    x, y = where
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def on_slope(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline on the slope, from h0 to h1 off it."""
    return solid(name, [[SLOPE_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def computer(m):
    """The IIe on its base plate: the body cut for the keyboard's well, RESET's recess and the side vents, its top
    printed."""
    outline = [(y, max(z, L.PLATE)) for y, z in L.profile()]
    body = prism_x("iie", outline, -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 2.0, segments=2)
    boolean(body, on_slope("well", L.well(), -L.WELL, 16.0, m["dark"]))
    x0, x1, s0, s1 = L.RESET["well"]
    boolean(body, on_slope("reset_well", [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], -5.0, 16.0, m["case"]))
    v, edge = L.VENTS, L.WIDTH / 2
    slots = [box("vent", x0, x1, y - v["width"] / 2, y + v["width"] / 2, *v["z"], m["dark"]) for y in v["y"]
             for x0, x1 in ((edge - v["inset"], edge + 5.0), (-edge - 5.0, -edge + v["inset"]))]
    boolean(body, join(slots, "vents"))
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.5 and name == "case" and c.y < TOP_DEPTH - 1.0
          and abs(c.x) < L.WIDTH / 2 - 0.5)
    plate = box("plate", -L.WIDTH / 2 + 3.0, L.WIDTH / 2 - 3.0, L.UNDERCUT[0] + 2.0, L.DEPTH - 3.0, 0.0, L.PLATE + 1.0,
                m["dark"])
    paint(plate, m["print"], swatch(L.PRINT_SWATCHES["plate"]), lambda c, n, name: True)
    return [body, plate]


def key_solid(name, rect, height, mat, m):
    """A key: from the well's floor up its sides, tapering to its printed top, height off the slope."""
    x0, s0, x1, s1 = rect

    def ring(d, h):
        return [(x0 + d, s0 + d, h), (x1 - d, s0 + d, h), (x1 - d, s1 - d, h), (x0 + d, s1 - d, h)]
    cap = solid(name, [ring(0.0, -L.WELL - 0.5), ring(0.0, height - 4.5), ring(L.KEY_INSET, height)], mat)
    bevel(cap, 0.6, segments=1, angle=30)
    cap.data.transform(SLOPE_FRAME)
    paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
    return cap


def keys(m):
    """The keys, standing in their well, the power light among them, and RESET in its recess: Control and RESET
    apart (the clip presses them)."""
    static, moving = [], {}
    for name, xu, row, wu, _ in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        outline = [(x0, s0), (x1, s0), (x1, s1), (x0, s1)]
        if name == "light":
            window = on_slope("light", outline, -L.WELL - 0.5, L.KEY_HEIGHT - 3.0, m["print"])
            bevel(window, 0.6, segments=1)
            paint(window, m["print"], top_uv, lambda c, n, _name: n.z > 0.9)
            paint(window, m["print"], swatch(L.PRINT_SWATCHES["bezel"]), lambda c, n, _name: n.z <= 0.9)
            static.append(window)
            continue
        cap = key_solid(name, (x0, s0, x1, s1), L.KEY_HEIGHT, m["keys"], m)
        if name in RESET_KEYS:
            moving[name] = cap
        else:
            static.append(cap)
    (x0, x1), (s0, s1) = L.RESET["x"], L.RESET["s"]
    moving["reset"] = key_solid("reset", (x0, s0, x1, s1), 6.0, m["keys"], m)
    return static, moving


def drive(m, n):
    """Disk II number n (1 the left), standing on the lid: the box, its panel sunk into its front and printed, the slot
    and the finger recess cut into it, the vents in its sides; drive 2's door, open, with it."""
    w, d, h = L.DRIVE["size"]
    cx, y0, z0 = L.DRIVE["at"][n - 1], L.DRIVE["front"], L.HEIGHT
    shell = box(f"drive{n}", cx - w / 2, cx + w / 2, y0, y0 + d, z0, z0 + h, m["case"])
    bevel(shell, 2.0, segments=2)
    pw, ph, sink = L.DRIVE["panel"]
    pz = L.PANEL_Z
    boolean(shell, box("panel", cx - pw / 2, cx + pw / 2, y0 - 5.0, y0 + sink, pz, pz + ph, m["case"]))
    s = L.DRIVE["slot"]
    boolean(shell, box("slot", cx + s["x"][0], cx + s["x"][1], y0 - 5.0, y0 + s["depth"],
                       pz + s["z"] - s["height"] / 2, pz + s["z"] + s["height"] / 2, m["dark"]))
    r = L.DRIVE["recess"]
    boolean(shell, box("recess", cx + r["x"][0], cx + r["x"][1], y0 - 5.0, y0 + sink + r["depth"], pz + r["z"][0],
                       pz + r["z"][1], m["dark"]))
    v = L.DRIVE["vents"]
    boolean(shell, join([box("vent", cx + side * w / 2 - 3.0, cx + side * w / 2 + 3.0, y0 + y - v["width"] / 2,
                             y0 + y + v["width"] / 2, z0 + v["z"][0], z0 + v["z"][1], m["dark"])
                         for side in (-1, 1) for y in v["y"]], "vents"))
    panel = atlas_uv(L.PRINT_REGIONS[f"drive{n}"], pw, ph)
    paint(shell, m["print"], lambda co: panel(co.x - (cx - pw / 2), pz + ph - co.z),
          lambda c, nn, name: nn.y < -0.9 and abs(c.y - (y0 + sink)) < 0.3 and name == "case")
    paint(shell, m["print"], swatch(L.PRINT_SWATCHES["drive"]),
          lambda c, nn, name: name == "case" and abs(c.x - cx) < pw / 2 + 0.1 and pz - 0.1 < c.z < pz + ph + 0.1
          and c.y < y0 + sink - 0.05 and abs(nn.y) < 0.5)
    return shell


def door(m, cx):
    """A drive's door: the lever standing over the slot, open; and its hinge, along the slot's top edge."""
    dd = L.DRIVE["door"]
    y0 = L.DRIVE["front"] + L.DRIVE["panel"][2]
    pz = L.PANEL_Z
    lever = box("door", cx + dd["x"][0], cx + dd["x"][1], y0 - dd["thickness"], y0 + 0.5, pz + dd["z"][0],
                pz + dd["z"][1], m["print"])
    bevel(lever, 0.8, segments=2)
    paint(lever, m["print"], swatch(L.PRINT_SWATCHES["dark"]), lambda c, n, name: True)
    return lever, Vector((cx, y0 - dd["thickness"] / 2, pz + L.DRIVE["slot"]["z"] + L.DRIVE["slot"]["height"] / 2))


def in_use(m):
    """Drive 1's IN USE light lit: a disc just over the printed one, its middle at its origin."""
    lx, lz, r = L.DRIVE["light"]
    y = L.DRIVE["front"] + L.DRIVE["panel"][2] - 0.15
    bm = bmesh.new()
    ring = [bm.verts.new((r * 1.1 * math.cos(2 * math.pi * k / 12), 0.0, r * 1.1 * math.sin(2 * math.pi * k / 12)))
            for k in range(12)]
    bm.faces.new(ring)                                     # wound to face -y
    lit = new_object("in_use", bm, m["print"])
    paint(lit, m["print"], swatch(L.PRINT_SWATCHES["lit"]), lambda c, n, name: True)
    return lit, Vector((L.DRIVE["at"][0] + lx, y, L.PANEL_Z + lz))


def monitor(m):
    """The Monitor II on the drives, its front's middle at MONITOR["at"]: the shell, the surround and the opening,
    the glass, the control strip's seam and face."""
    M = L.MONITOR
    w, b, o = M["width"], M["bezel"], M["opening"]
    shell = prism_x("monitor", M["profile"], -w / 2, w / 2, m["case"])
    bevel(shell, 3.0, segments=2)
    boolean(shell, box("surround", b["x"][0], b["x"][1], -5.0, b["depth"], b["z"][0], b["z"][1], m["bezel"]))
    outer, inner = rounded(o["x"], o["z"], *o["outer"]), rounded(o["x"], o["z"], *o["inner"])
    boolean(shell, solid("opening", [[(x, y, z) for x, z in outline] for outline, y in
                                     ((outer, -10.0), (outer, b["depth"] - 0.01), (inner, o["depth"]),
                                      (inner, o["depth"] + 1.0))], m["bezel"]))
    sx = w / 2 - M["strip"]
    boolean(shell, box("seam", sx - 0.6, sx + 0.6, -5.0, 1.2, -5.0, M["profile"][-1][1] + 5.0, m["dark"]))
    h = M["profile"][-1][1]
    face = atlas_uv(L.PRINT_REGIONS["strip"], M["strip"], h)
    paint(shell, m["print"], lambda co: face(co.x - sx, h - co.z),
          lambda c, n, name: n.y < -0.9 and c.x > sx + 0.6 and c.y < 0.5 and name == "case")

    gw, gh = M["glass"]["size"]
    glass = curved("glass", gw, gh, M["glass"]["bulge"], atlas_uv(L.MEDIA_REGIONS["banner"], 1.0, 1.0), m["glass"])
    glass.data.transform(Matrix.Translation((o["x"], o["depth"], o["z"])))
    parts = [shell, glass]
    at = Matrix.Translation((M["at"][0], M["at"][1], L.HEIGHT + L.DRIVE["size"][2]))
    for obj in parts:
        obj.data.transform(at)
    return parts


def screen(m, name, region):
    """A screen over the glass, its middle at its origin (the clip shows and hides it)."""
    gw, gh = L.MONITOR["glass"]["size"]
    return curved(name, gw, gh, L.MONITOR["glass"]["bulge"], atlas_uv(L.MEDIA_REGIONS[region], 1.0, 1.0), m["glass"])


def floppy(m):
    """The floppy, its middle at its origin, lying flat, the edge that goes in first towards +y, its label up."""
    s, t = L.DISK["size"], L.DISK["thickness"]
    jacket = box("floppy", -s / 2, s / 2, -s / 2, s / 2, -t / 2, t / 2, m["disk"])
    bevel(jacket, 0.5, segments=1)
    face = atlas_uv(L.MEDIA_REGIONS["disk"], s, s)
    paint(jacket, m["disk"], lambda co: face(co.x + s / 2, s / 2 - co.y), lambda c, n, name: n.z > 0.9)
    paint(jacket, m["disk"], swatch(L.MEDIA_SWATCHES["jacket"]), lambda c, n, name: n.z <= 0.9)
    return jacket


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


OUT = 175.0          # how far in front of its seat the floppy waits: wholly out of the drive


def timeline(f):
    # The floppy: appears in front of drive 1, slides in; later slides back out and goes.
    if f < 8 or f >= 214:
        disk = Pose(scale=HIDDEN)
    elif f < 18:
        disk = Pose(y=-OUT, scale=appear(f, 8, 16))
    elif f < 40:
        disk = Pose(y=-OUT * (1 - smooth(phase(f, 18, 40))))
    elif f < 188:
        disk = Pose()
    elif f < 206:
        disk = Pose(y=-OUT * ease_out(phase(f, 188, 206)))
    else:
        disk = Pose(y=-OUT, scale=max(HIDDEN, 1 - ease_in(phase(f, 206, 214))))

    # The door turns down over the slot once the floppy's in, and back up before it comes out.
    if f < 180:
        turn = 180.0 * smooth(phase(f, 42, 50))
    else:
        turn = 180.0 * (1 - smooth(phase(f, 180, 188)))

    # IN USE while the game loads, and again after RESET while the IIe looks for a disk.
    light = Pose() if 50 <= f < 98 or 168 <= f < 182 else Pose(scale=HIDDEN)

    # The title screen arrives a pass of hi-res lines at a time; RESET clears it back to the banner.
    def shown(f0, f1):
        return Pose() if f0 <= f < f1 else Pose(scale=HIDDEN)
    poses = {"floppy": disk, "door": Pose(pitch=turn), "in_use": light, "screen_pass2": shown(62, 74),
             "screen_pass5": shown(74, 86), "screen_title": shown(86, 166)}
    for k, name in enumerate(RESET_KEYS):                   # Control, then RESET, held, let go together
        d = 3.0 * smooth(phase(f, 156 + 4 * k, 159 + 4 * k)) * (1 - smooth(phase(f, 168, 172)))
        poses[name] = Pose(x=PRESS.x * d, y=PRESS.y * d, z=PRESS.z * d)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "apple2_print.png"))
    media = bpy.data.images.load(os.path.join(images, "apple2_media.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", glass="#FFFFFF", disk="#FFFFFF")
    textures = dict(print=printed, glass=media, disk=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    static, moving = keys(m)
    whole = join(computer(m) + static + [drive(m, 1), drive(m, 2), door(m, L.DRIVE["at"][1])[0]] + monitor(m), "apple2")
    lever, hinge = door(m, L.DRIVE["at"][0])
    lever.data.transform(Matrix.Translation(-hinge))
    lit, lit_at = in_use(m)
    disk = floppy(m)
    screens = {name: screen(m, "screen_" + name, name) for name in ("pass2", "pass5", "title")}
    for obj in [whole, lever, disk] + list(moving.values()):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("apple2_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    M, o = L.MONITOR, L.MONITOR["opening"]
    glass_front = Vector((M["at"][0] + o["x"], M["at"][1] + o["depth"], L.HEIGHT + L.DRIVE["size"][2] + o["z"]))
    placed = [(disk, Vector(L.SEAT)), (lever, hinge), (lit, lit_at)]
    placed += [(part, glass_front + Vector((0.0, -0.4 - 0.3 * k, 0.0))) for k, part in enumerate(screens.values())]
    for part, where in placed:
        part.parent = whole
        part.location = where
    for part in moving.values():
        part.parent = whole
    nodes = {"floppy": disk, "door": lever, "in_use": lit, **{"screen_" + k: v for k, v in screens.items()}, **moving}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, lever, lit, disk] + list(screens.values()) + list(moving.values())
    print(f"Apple II: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
