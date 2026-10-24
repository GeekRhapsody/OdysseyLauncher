"""The console theme's Amiga system model (godot/themes/console/models/systems/amiga.glb): an Amiga 500 and its
Commodore 1084S monitor, Kickstart 1.3 asking for a disk.

Built in Blender from the real machines' proportions (amiga_layout.py has the measurements, taken from photographs).
The computer is its side outline extruded across its width: the keyboard deck rising from the low front edge, the step,
the raised back rounding over at the back edge; nine vent grooves are cut across the raised back and the gaps of the
comb of fins along its back edge, the keyboard's wells into the deck, and the drive's panel and slot into its right
end. Its 96 keys (the UK layout) stand in the wells, tapering to their printed tops, off-white or grey as the real
ones. Behind it stands the monitor: its side outline extruded (the hood sloping down behind), the bezel's panel sunk
into its front, the screen's opening sloping in to the curved glass, its badge, the seams of the control flap under
it, and a grille in each side. The printing is two textures drawn by amiga_print.py: the computer's top seen from above
(planar-mapped onto every face facing up: the key tops and legends, the badge, the lights, the AMIGA lettering) with
the monitor's badge and the swatches its bezel and the lit drive light take; and the screens (the glass at rest shows
Kickstart 1.3's hand holding a disk), the floppy's two sides and their swatches.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the drive's end towards the viewer,
the top tipped up; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the
set holding the floppy, the eject button, the lit drive light, two screens over the glass (black, and the title screen
of a made-up game, Odyssey) and the Ctrl and Amiga keys. The floppy waits in the drive shrunk to nothing, the light and
the screens are shrunk to nothing, so at rest the card is the set with Kickstart's hand on the screen.

The `focused` clip (8 s, looping) loads a game: the floppy pops up beside the drive, flips over and slides in; the
drive light flickers while the screen goes black, then Odyssey's title screen comes up. Ctrl and both Amiga keys go
down together (the Amiga's reset), the hand is back, the eject button is pressed and the floppy pops out and goes.

Seven materials (case, print, key_light, key_dark, dark, glass, disk) and two textures, within the system model
budget. Run from the repo root:

    python tools/console-models/amiga_print.py artifacts/amiga
    blender -b --factory-startup --python tools/console-models/amiga.py -- artifacts/amiga godot/themes/console/models/systems/amiga.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amiga_layout as L  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, prism_x, triangles  # noqa: E402

TILT_YAW = -30.0     # degrees about the vertical: the right end (the drive) comes towards the viewer
TILT_PITCH = 25.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, print=0.55, key_light=0.5, key_dark=0.5, dark=0.8, glass=0.2, disk=0.4)
RESET_KEYS = ("ctrl", "lamiga", "ramiga")

# The deck's frame: x across, s up the slope from the deck's front edge, h off it.
SLOPE_FRAME = Matrix.Translation((0.0, L.DECK[0][0], L.DECK[0][1])) @ Matrix.Rotation(L.SLOPE, 4, "X")
PRESS = SLOPE_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame


# ---- UVs -------------------------------------------------------------------------------------------------------------

def atlas_uv(region, w, h):
    """A face drawn w x h into region: (a, b) millimetres across it (a to the right, b down from its top) to UVs."""
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


TOP = atlas_uv(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH)


def top_uv(co):
    """The computer's top seen from above."""
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def swatch(where):
    x, y = where
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def paint(obj, mat, uv_of, keep):
    """Gives the faces keep(centre, normal, material name) accepts the material mat and the UVs uv_of(corner)."""
    mesh = obj.data
    names = [m.name for m in mesh.materials]
    if mat.name not in names:
        mesh.materials.append(mat)
        names.append(mat.name)
    index = names.index(mat.name)
    uv = mesh.uv_layers.active or mesh.uv_layers.new(name="UVMap")
    for p in mesh.polygons:
        if keep(p.center, p.normal, names[p.material_index]):
            p.material_index = index
            for li in p.loop_indices:
                uv.data[li].uv = uv_of(mesh.vertices[mesh.loops[li].vertex_index].co)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def solid(name, rings, mat):
    """A solid through rings of 3D points (each the same count, in the same order), capped at both ends."""
    bm = bmesh.new()
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(verts, verts[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])
    bm.faces.new(verts[0])
    bm.faces.new(list(reversed(verts[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def on_slope(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline on the deck, from h0 to h1 off it."""
    return solid(name, [[SLOPE_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def rounded(cx, cz, w, h, r, segments=5):
    """A rounded rectangle's outline in (x, z), w x h centred on (cx, cz), anticlockwise from its right side."""
    points = []
    for qx, qz, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oz = cx + qx * (w / 2 - r), cz + qz * (h / 2 - r)
        for k in range(segments + 1):
            a = math.radians(a0 + 90 * k / segments)
            points.append((ox + r * math.cos(a), oz + r * math.sin(a)))
    return points


def curved(name, w, h, bulge, uv, mat, nu=16, nv=12, keep=None):
    """A screen facing the viewer (-y), w x h about its origin, its middle bulging bulge towards the viewer; uv(a, b)
    gives the UV of the point a across from its left and b down from its top (both 0 to 1). keep(i, j), if given,
    says which of its nu x nv cells to make (a part of the screen)."""
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    grid = [[bm.verts.new((w * (i / nu - 0.5), -bulge * (1 - (2 * i / nu - 1) ** 2) * (1 - (2 * j / nv - 1) ** 2),
                           h * (0.5 - j / nv))) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            if keep is not None and not keep(i, j):
                continue
            corners = ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))       # wound to face -y
            face = bm.faces.new([grid[b][a] for a, b in corners])
            face.smooth = True
            for loop, (a, b) in zip(face.loops, corners):
                loop[layer].uv = uv(a / nu, b / nv)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    return new_object(name, bm, mat)


def computer(m):
    """The Amiga 500: the body cut for its wells, grooves, fins and drive, its top printed."""
    body = prism_x("a500", L.profile(), -L.WIDTH / 2, L.WIDTH / 2, m["case"])
    bevel(body, 1.6, segments=2)
    boolean(body, join([on_slope("well", outline, -L.WELL, 12.0, m["dark"]) for outline in L.wells()], "wells"))
    g = L.GROOVES
    boolean(body, join([box("groove", g["x"][0], g["x"][1], y - g["width"] / 2, y + g["width"] / 2,
                            L.TOP_Z - g["depth"], L.TOP_Z + 5.0, m["key_dark"]) for y in g["y"]], "grooves"))
    f = L.FIN_GAPS
    boolean(body, join([box("gap", x - f["width"] / 2, x + f["width"] / 2, *f["y"], *f["z"], m["key_dark"])
                        for x in f["x"]], "gaps"))
    y0, y1, z0, z1, depth = L.DRIVE["recess"]
    boolean(body, box("panel", L.WIDTH / 2 - depth, L.WIDTH / 2 + 5.0, y0, y1, z0, z1, m["case"]))
    y0, y1, z0, z1, depth = L.DRIVE["slot"]
    boolean(body, box("slot", L.WIDTH / 2 - depth, L.WIDTH / 2 + 5.0, y0, y1, z0, z1, m["dark"]))
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.9 and name == "case")
    return body


def keys(m):
    """The keys, standing in their wells and tapering to their printed tops: Ctrl and the Amiga keys apart (the clip
    presses them)."""
    static, moving = [], {}
    h, inset = L.KEY_HEIGHT, L.KEY_INSET
    for k in L.KEYS:
        name, xu, row, wu, colour = k[:5]
        x0, s0, x1, s1 = L.key_rect(xu, row, wu, k[6] if len(k) > 6 else 1)

        def rect(d, z):
            return [(x0 + d, s0 + d, z), (x1 - d, s0 + d, z), (x1 - d, s1 - d, z), (x0 + d, s1 - d, z)]
        cap = solid(name, [rect(0.0, -L.WELL - 0.5), rect(0.0, h - 4.5), rect(inset, h)], m["key_" + colour])
        bevel(cap, 0.6, segments=1, angle=30)
        cap.data.transform(SLOPE_FRAME)
        paint(cap, m["print"], top_uv, lambda c, n, _name: n.z > 0.95)
        if name in RESET_KEYS:
            moving[name] = cap
        else:
            static.append(cap)
    return static, moving


def monitor(m):
    """The 1084S, its front's middle at the origin, facing -y: the shell, the bezel and the opening, the glass, the
    badge, the flap's seams, the side grilles."""
    M = L.MONITOR
    w, b, o = M["width"], M["bezel"], M["opening"]
    shell = prism_x("monitor", M["profile"], -w / 2, w / 2, m["case"])
    bevel(shell, 2.5, segments=2)
    boolean(shell, box("bezel", -b["x"], b["x"], -5.0, b["depth"], b["z"][0], b["z"][1], m["case"]))
    boolean(shell, join([box("seam", -w / 2 + 7.0, w / 2 - 7.0, -5.0, 0.8, z - 0.6, z + 0.6, m["dark"])
                         for z in M["seams"]], "seams"))
    outer, inner = rounded(0.0, o["z"], *o["outer"]), rounded(0.0, o["z"], *o["inner"])
    boolean(shell, solid("opening", [[(x, y, z) for x, z in outline] for outline, y in
                                     ((outer, -10.0), (outer, b["depth"] - 0.01), (inner, o["depth"]),
                                      (inner, o["depth"] + 1.0))], m["case"]))
    v = M["vents"]
    boolean(shell, join([box("vent", side * w / 2 - 2.0, side * w / 2 + 2.0, *v["y"], z - v["height"] / 2,
                             z + v["height"] / 2, m["dark"]) for side in (-1, 1) for z in v["z"]], "vents"))

    # The bezel's face and the opening's walls are the bezel's colour; the gap round the panel is dark.
    def bezel(c, n, name):
        inside = abs(c.x) < b["x"] + 0.01 and b["z"][0] - 0.01 < c.z < b["z"][1] + 0.01 and c.y > 0.3
        return name == "case" and inside and not (abs(n.y) < 0.5 and c.y < b["depth"] - 0.1)
    paint(shell, m["print"], swatch(L.PRINT_SWATCHES["bezel"]), bezel)
    paint(shell, m["dark"], swatch(L.PRINT_SWATCHES["black"]),
          lambda c, n, name: name == "case" and abs(n.y) < 0.5 and 0.3 < c.y < b["depth"] - 0.1
          and abs(c.x) < b["x"] + 0.5 and b["z"][0] - 0.5 < c.z < b["z"][1] + 0.5)

    gw, gh = M["glass"]["size"]
    region = atlas_uv(L.MEDIA_REGIONS["kickstart"], 1.0, 1.0)
    glass = curved("glass", gw, gh, M["glass"]["bulge"], region, m["glass"])
    glass.data.transform(Matrix.Translation((0.0, o["depth"], o["z"])))

    bm = bmesh.new()
    layer = bm.loops.layers.uv.new("UVMap")
    (x0, x1), (z0, z1) = M["badge"]["x"], M["badge"]["z"]
    corners = [(x0, z0), (x0, z1), (x1, z1), (x1, z0)]                  # wound to face -y
    face = bm.faces.new([bm.verts.new((x, b["depth"] - 0.15, z)) for x, z in corners])
    badge_uv = atlas_uv(L.PRINT_REGIONS["badge"], x1 - x0, z1 - z0)
    for loop, (x, z) in zip(face.loops, corners):
        loop[layer].uv = badge_uv(x - x0, z1 - z)
    badge = new_object("badge", bm, m["print"])

    parts = [shell, glass, badge]
    at = Matrix.Translation((M["at"][0], M["at"][1], 0.0))
    for obj in parts:
        obj.data.transform(at)
    return parts


def screen(m, name, uv):
    """A screen switched on over the glass, its middle at its origin (the clip opens and closes it about there)."""
    gw, gh = L.MONITOR["glass"]["size"]
    return curved(name, gw, gh, L.MONITOR["glass"]["bulge"], uv, m["glass"])


def disk(m):
    """The floppy, its middle at its origin, its shutter's edge towards -x (into the drive), its label up."""
    l, w, t = L.DISK["length"], L.DISK["width"], L.DISK["thickness"]
    shell = box("disk", -l / 2, l / 2, -w / 2, w / 2, -t / 2, t / 2, m["disk"])
    bevel(shell, 0.8, segments=2)
    top, bottom = atlas_uv(L.MEDIA_REGIONS["disk_top"], l, w), atlas_uv(L.MEDIA_REGIONS["disk_bottom"], l, w)
    paint(shell, m["disk"], lambda co: top(co.x + l / 2, w / 2 - co.y), lambda c, n, name: n.z > 0.9)
    paint(shell, m["disk"], lambda co: bottom(co.x + l / 2, w / 2 + co.y), lambda c, n, name: n.z < -0.9)
    paint(shell, m["disk"], swatch(L.MEDIA_SWATCHES["edge"]), lambda c, n, name: abs(n.z) <= 0.9)
    return shell


def drive_light(m):
    """The drive light lit: a bar just over the printed one, its middle at its origin."""
    x0, x1 = L.LIGHTS["x"]
    w = L.LIGHTS["width"] + 0.4
    s = (L.LIGHTS["drive"] - L.DECK[0][0]) / math.cos(L.SLOPE)
    lit = on_slope("drive_light", [(x0 - 0.2, s - w / 2), (x1 + 0.2, s - w / 2), (x1 + 0.2, s + w / 2),
                                   (x0 - 0.2, s + w / 2)], 0.05, 0.25, m["print"])
    paint(lit, m["print"], swatch(L.PRINT_SWATCHES["lit"]), lambda c, n, name: True)
    middle = SLOPE_FRAME @ Vector(((x0 + x1) / 2, s, 0.15))
    lit.data.transform(Matrix.Translation(-middle))
    return lit, middle


def eject_button(m):
    y0, y1, z0, z1, out = L.DRIVE["eject"]
    face = L.WIDTH / 2 - L.DRIVE["recess"][4]
    button = box("eject", face - 1.0, face + out, y0, y1, z0, z1, m["case"])
    bevel(button, 0.6, segments=1)
    return button


# ---- The focused clip ------------------------------------------------------------------------------------------------

def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def flat(v):
    """A screen squeezed to v of its height (switching on or off)."""
    return Pose(axes=(1.0, 1.0, max(HIDDEN, v)))


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def timeline(f):
    out = L.WIDTH / 2 + 22.0 + L.DISK["length"] / 2 - L.SEAT[0]   # the floppy's middle beside the drive: 22 mm out

    # The floppy: pops up beside the drive, flips over coming down to the slot, slides in; later pops out and goes.
    if f < 14 or f >= 228:
        floppy = Pose(scale=HIDDEN)
    elif f < 24:
        floppy = Pose(x=out, z=50.0, scale=appear(f, 14, 22))
    elif f < 44:
        t = smooth(phase(f, 24, 44))
        floppy = Pose(x=out - 30.0 * t, z=50.0 * (1 - t), pitch=360.0 * t)
    elif f < 198:
        floppy = Pose(x=(out - 30.0) * (1 - smooth(phase(f, 44, 58))))
    elif f < 214:
        floppy = Pose(x=40.0 * back_out(phase(f, 198, 206)))
    else:
        t = ease_in(phase(f, 214, 228))
        floppy = Pose(x=40.0 + 80.0 * t, z=30.0 * t, scale=max(HIDDEN, 1 - ease_in(phase(f, 220, 228))))

    # The drive light, while the disk is read: on, with a short blink every few frames.
    reading = 60 <= f < 112 or 200 <= f < 206
    light = Pose() if reading and (f // 5) % 5 != 3 else Pose(scale=HIDDEN)

    # The screens: black while the game loads, its title screen opening; the reset blacks it out, and the hand's back.
    black = Pose() if 62 <= f < 102 or 184 <= f < 194 else Pose(scale=HIDDEN)
    if f < 100 or f >= 188:
        title = Pose(scale=HIDDEN)
    elif f < 106:
        title = flat(0.02 + 0.98 * ease_out(phase(f, 100, 106)))
    elif f < 182:
        title = Pose()
    else:
        title = flat(1 - ease_in(phase(f, 182, 188)))

    poses = {"floppy": floppy, "drive_light": light, "screen_black": black, "screen_title": title,
             "eject": Pose(x=-1.5 * tap(f, 196))}
    for k, name in enumerate(RESET_KEYS):                         # Ctrl, then each Amiga key, held, let go together
        d = 3.0 * smooth(phase(f, 170 + 3 * k, 173 + 3 * k)) * (1 - smooth(phase(f, 186, 190)))
        poses[name] = Pose(x=PRESS.x * d, y=PRESS.y * d, z=PRESS.z * d)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "amiga_print.png"))
    media = bpy.data.images.load(os.path.join(images, "amiga_media.png"))
    colours = dict(L.COLOURS, print="#FFFFFF", glass="#FFFFFF", disk="#FFFFFF")
    textures = dict(print=printed, glass=media, disk=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    static, moving = keys(m)
    whole = join([computer(m)] + static + monitor(m), "amiga")
    eject = eject_button(m)
    lit, lit_at = drive_light(m)
    floppy = disk(m)
    unlit = swatch(L.MEDIA_SWATCHES["black"])(None)
    black = screen(m, "screen_black", lambda a, b: unlit)
    title = screen(m, "screen_title", atlas_uv(L.MEDIA_REGIONS["title"], 1.0, 1.0))
    for obj in [whole, eject, floppy] + list(moving.values()):
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    # The node tree: the root (the view and the fit) holds the set; the set holds the moving parts at their places.
    root = bpy.data.objects.new("amiga_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    o, M = L.MONITOR["opening"], L.MONITOR
    glass_front = Vector((M["at"][0], M["at"][1] + o["depth"], o["z"]))
    for part, where in ((floppy, Vector(L.SEAT)), (lit, lit_at), (black, glass_front + Vector((0.0, -0.5, 0.0))),
                        (title, glass_front + Vector((0.0, -1.0, 0.0)))):
        part.parent = whole
        part.location = where
    for part in [eject] + list(moving.values()):
        part.parent = whole
    nodes = {"floppy": floppy, "drive_light": lit, "screen_black": black, "screen_title": title, "eject": eject,
             **moving}

    # The three-quarter view, then the spec's fit of the set at rest, as the root's transform.
    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole, eject, lit, floppy, black, title] + list(moving.values())
    print(f"Amiga: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
