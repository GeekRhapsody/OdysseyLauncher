"""The console theme's object cards (godot/themes/console/models/systems/<card>.glb): for systems with no hardware of
their own, an object that stands for them.

Built in Blender, each card from its own function here (CARDS), turned (lathes), swept (tubes) and extruded with
emblems.py's helpers:
- `ags`: Adventure Game Studio's blue mug, tall and glossy, its tea bag's tag hanging over its side; the `focused`
  clip glides a pointing hand's cursor in, clicks on the mug, and the mug hops and spins round once.
- `chailove`: ChaiLove's cup of chai on its saucer, glazed in its logo's blues, a heart of foam on the tea; the clip
  stirs it with a spoon, the foam swirling away and coming back as a heart, steam curling up.
- `openbor`: a beat 'em up's oil drum, a blue dragon spray-painted on it (a painting, paintings.py's `openbor_drum`,
  at 1024 wide: devices_print.py's `openbor`);
  the clip has it jolt as if punched and its lid fly off, a roast chicken leaping out and dropping back in.
- `ports`: a small cargo ship on the sea, its crane holding a container with a gamepad on its side; the clip rocks
  it on the swell while the crane swings the container out over the side and back.
Every shape is made from simple geometry; no logo's artwork is traced.

A node tree: a root (the turn to a three-quarter view and the model spec's fit, as emblems.py's) holding the card's
parts, each moving part its own node. Plain materials (and the drum's painting), within the system model budget. Run
from the repo root:

    python tools/console-models/devices_print.py openbor artifacts/made-up-games artifacts/devices
    blender -b --factory-startup --python tools/console-models/props.py -- artifacts/devices <card> godot/themes/console/models/systems/<card>.glb

(The images folder is only read for OpenBOR's drum, `openbor_media.jpg`.)
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emblems_layout as E  # noqa: E402
from amiga import solid  # noqa: E402
from clip import HIDDEN, Pose, bump, ease_in, ease_out, hop, key, phase, smooth, wobble  # noqa: E402
from emblems import TILT_PITCH, TILT_YAW, about, ball, lettering, one_tone, plate, two_tone  # noqa: E402
from mega_drive_cartridge import bevel, box, export, join, material, triangles  # noqa: E402

FPS = 30


def lathe(name, profile, mat, n=40):
    """A solid turned about z through (r, z) points, its first and last rings capped."""
    return solid(name, [[(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), z) for k in range(n)]
                        for r, z in profile], mat)


def tube(name, path, r, mat, n=10):
    """A tube of radius r along a path of (x, y, z) points, capped at its ends."""
    rings = []
    for i, p in enumerate(path):
        p = Vector(p)
        a = Vector(path[max(0, i - 1)])
        b = Vector(path[min(len(path) - 1, i + 1)])
        along = (b - a).normalized()
        side = along.cross(Vector((0.0, 1.0, 0.0)))
        if side.length < 0.1:
            side = along.cross(Vector((1.0, 0.0, 0.0)))
        side.normalize()
        up = side.cross(along).normalized()
        rings.append([p + r * (math.cos(2 * math.pi * k / n) * side + math.sin(2 * math.pi * k / n) * up)
                      for k in range(n)])
    return solid(name, rings, mat)


def smooth_shaded(obj, angle=40.0):
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


# ---- AGS -------------------------------------------------------------------------------------------------------------

AGS_COLOURS = dict(mug="#1E2CB0", inside="#0E1460", tag="#E8C45A", string="#EEEAE0", ink="#5A3A10", hand="#F8F8F8",
                   outline="#141416")
HAND = [(0.0, 0.0), (30.0, 0.0), (33.0, 30.0), (16.0, 30.0), (16.0, 52.0), (11.0, 57.0), (6.0, 52.0), (6.0, 30.0),
        (-5.0, 22.0), (-5.0, 13.0), (0.0, 9.0)]


def ags(m):
    mug = lathe("mug", [(40.0, 0.0), (41.5, 4.0), (43.0, 108.0), (42.5, 112.0), (39.5, 112.0), (38.5, 108.0),
                        (37.0, 12.0)], m["mug"], 48)
    smooth_shaded(mug, 50.0)
    mug.data.materials.append(m["inside"])
    for p in mug.data.polygons:                           # the inside darker
        if math.hypot(p.center.x, p.center.y) < 38.9 and p.center.z > 11.0:
            p.material_index = 1
    handle = smooth_shaded(tube("handle", [(40.0 + 30.0 * math.sin(math.pi * t), 0.0, 92.0 - 62.0 * t)
                                           for t in [k / 16 for k in range(17)]], 7.5, m["mug"], 12))
    string = tube("string", [(-12.0, -36.0, 113.0), (-14.0, -42.0, 106.0), (-16.0, -44.5, 80.0)], 0.9, m["string"], 6)
    tag = box("tag", -30.0, -2.0, -47.0, -45.0, 48.0, 80.0, m["tag"])
    tag.data.transform(Matrix.Rotation(math.radians(-8.0), 4, "Y"))
    word, w, x0 = lettering("ags", "AGS", "ariblk.ttf", 10.0, 1.0, m["ink"])
    word.data.transform(Matrix.Translation((-16.0 - x0 - w / 2, -47.6, 58.0)))
    whole = join([mug, handle, string, tag, word], "mug")
    tip = (12.0, 92.0)                                    # where its fingertip clicks: the mug's front
    hand = plate("hand", E.ccw(E.moved(HAND, tip[0] - 11.0, tip[1] - 57.0)), -62.0, -58.0, m["hand"])
    rim = plate("hand_outline", E.ccw(E.moved([(x * 1.18 - 2.7, z * 1.1 - 2.6) for x, z in HAND], tip[0] - 11.0,
                                              tip[1] - 57.0)), -58.0, -56.0, m["outline"])
    cursor = join([one_tone(hand, m["hand"]), one_tone(rim, m["outline"])], "cursor")
    return {"mug": (whole, None), "cursor": (about(cursor, (tip[0], -60.0, tip[1])), None)}, [], ags_timeline, 150


def ags_timeline(f):
    glide = smooth(phase(f, 4, 34)) * (1 - smooth(phase(f, 120, 146)))
    seen = 1.0 if 4 <= f < 146 else 0.0
    away = 1.0 if 3 <= f < 147 else 0.0                   # at rest, hidden where it clicks (the launcher fits the
    click = bump(f, 36, 44) if 36 <= f < 44 else 0.0     # rest pose)
    poses = {"cursor": Pose(x=110.0 * (1 - glide) * away, z=(60.0 * (1 - glide) - 6.0 * click) * away,
                            scale=HIDDEN + (1 - HIDDEN) * seen * (0.4 + 0.6 * glide))}
    squash = 0.14 * smooth(phase(f, 44, 52)) * (1 - smooth(phase(f, 52, 55))) + wobble(f, 86, 0.16, 8.0, 4.0)
    poses["mug"] = Pose(z=hop(f, 52, 86, 70.0), spin=360.0 * smooth(phase(f, 54, 84)), squash=squash)
    return poses


# ---- ChaiLove --------------------------------------------------------------------------------------------------------

CHAI_COLOURS = dict(glaze="#25AAE1", pale="#AEE7FF", saucer="#166385", tea="#9A5A26", foam="#FFF4E4",
                    spoon="#C8CCD4", steam="#F4F8FA")


def chailove(m):
    saucer = lathe("saucer", [(0.5, 0.0), (50.0, 0.0), (78.0, 9.0), (80.0, 12.5), (76.0, 13.0), (50.0, 5.0),
                              (0.5, 5.0)], m["saucer"], 56)
    cup = lathe("cup", [(30.0, 5.0), (33.0, 8.0), (50.0, 50.0), (53.0, 57.0), (50.0, 58.0), (47.0, 53.0),
                        (29.0, 13.0)], m["glaze"], 56)
    cup.data.materials.append(m["pale"])
    for p in cup.data.polygons:                           # the cup's inside pale
        if p.normal.dot(Vector((p.center.x, p.center.y, 0.0)).normalized()) < -0.2:
            p.material_index = 1
    handle = tube("handle", [(46.0 + 22.0 * math.sin(math.pi * t), 0.0, 46.0 - 26.0 * t)
                             for t in [k / 12 for k in range(13)]], 5.0, m["glaze"], 10)
    base = join([smooth_shaded(saucer), smooth_shaded(cup, 50.0), smooth_shaded(handle)], "cup")
    tea = one_tone(plate("tea", E.circle(0.0, 0.0, 49.5, 48), -1.0, 1.0, m["tea"]), m["tea"])
    swirl = []
    for k in range(3):                                    # the stirred foam's swirl
        arc = [(r * math.cos(math.radians(a + 120.0 * k)), r * math.sin(math.radians(a + 120.0 * k)))
               for r, a in [(8.0 + 30.0 * t, 200.0 * t) for t in [i / 16 for i in range(17)]]]
        swirl.append(tube(f"swirl{k}", [(x, 0.0, z) for x, z in arc], 1.6, m["foam"], 6))
    foam = join([tea] + swirl, "tea")
    foam.data.transform(Matrix.Translation((0.0, 0.0, 53.0)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    heart = one_tone(plate("heart", E.heart(0.0, 0.0, 40.0), -1.0, 1.4, m["foam"]), m["foam"])
    heart.data.transform(Matrix.Translation((0.0, 0.0, 54.0)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    spoon_bowl = lathe("bowl", [(0.5, 0.0), (8.0, 2.0), (11.0, 5.0), (0.5, 3.0)], m["spoon"], 16)
    spoon_bowl.data.transform(Matrix.Scale(1.0, 4) @ Matrix.Diagonal((1.0, 1.4, 1.0, 1.0)))
    stem = tube("stem", [(0.0, 10.0, 4.0), (0.0, 40.0, 22.0), (0.0, 92.0, 52.0)], 2.4, m["spoon"], 8)
    spoon = join([spoon_bowl, stem], "spoon")
    spoon.data.transform(Matrix.Translation((0.0, 18.0, 40.0)))
    parts = {"cup": (base, None), "tea": (about(foam, (0.0, 0.0, 53.0)), "cup"),
             "heart": (about(heart, (0.0, 0.0, 54.0)), "cup"), "spoon": (about(smooth_shaded(spoon), (0.0, 0.0, 40.0)),
                                                                        "cup")}
    for k in range(3):                                    # steam: hidden in the tea till it rises
        x = (k - 1) * 18.0
        wisp = tube(f"steam{k}", [(x + 6.0 * math.sin(t * 5.0 + k), 0.0, 56.0 + 60.0 * t)
                                  for t in [i / 10 for i in range(11)]], 2.2, m["steam"], 6)
        parts[f"steam{k}"] = (about(smooth_shaded(wisp), (x, 0.0, 56.0)), None)
    return parts, [], chailove_timeline, 150


def chailove_timeline(f):
    stir = 720.0 * smooth(phase(f, 10, 74))
    poses = {"spoon": Pose(spin=stir, z=-4.0 * bump(f, 10, 74)), "tea": Pose(spin=stir * 0.6)}
    gone = smooth(phase(f, 12, 24)) * (1 - smooth(phase(f, 76, 92)))
    poses["heart"] = Pose(scale=HIDDEN + (1 - HIDDEN) * (1 - gone) * (1 + wobble(f, 92, 0.2, 8.0, 4.0)),
                          spin=90.0 * gone)
    for k in range(3):
        f0 = 20 + 14 * k
        t = phase(f, f0, f0 + 70)
        rise = bump(f, f0, f0 + 70) if f0 <= f < f0 + 70 else 0.0
        poses[f"steam{k}"] = Pose(z=30.0 * t, axes=(1.0, 1.0, 0.2 + 0.8 * rise),
                                  scale=HIDDEN + (1 - HIDDEN) * rise)
    return poses


# ---- OpenBOR ---------------------------------------------------------------------------------------------------------

DRUM = dict(r=60.0, height=170.0, hoops=(56.0, 114.0))
OPENBOR_COLOURS = dict(drum="#FFFFFF", rim="#3E4A58", chicken="#C8782C", crust="#8A4818", bone="#F2EAD8")


def drum_profile():
    r, h = DRUM["r"], DRUM["height"]
    points = [(r - 3.0, 0.0), (r, 3.0)]
    for z in DRUM["hoops"]:                               # the rolling hoops, standing proud
        points += [(r, z - 6.0), (r + 3.5, z - 3.0), (r + 3.5, z + 3.0), (r, z + 6.0)]
    return points + [(r, h - 4.0), (r + 2.5, h - 1.0), (r + 2.0, h + 1.0), (r - 2.0, h)]


def openbor(m):
    r, h = DRUM["r"], DRUM["height"]
    body = lathe("drum", drum_profile(), m["drum"], 48)
    for v_poly in body.data.polygons:
        v_poly.use_smooth = True
    uv = body.data.uv_layers.new(name="UVMap")
    for p in body.data.polygons:                          # the painting wrapped round it
        u_mid = (math.atan2(p.center.y, p.center.x) / (2 * math.pi)) % 1.0
        for li in p.loop_indices:
            co = body.data.vertices[body.data.loops[li].vertex_index].co
            u = (math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0
            if abs(u - u_mid) > 0.5:                     # a face across the seam keeps to one side of it
                u += 1.0 if u < u_mid else -1.0
            uv.data[li].uv = (u, min(1.0, max(0.0, co.z / h)))
    lid = lathe("lid", [(r + 1.0, 0.0), (r + 1.5, 6.0), (r - 4.0, 7.0), (0.5, 5.0)], m["rim"], 48)
    lid.data.transform(Matrix.Translation((0.0, 0.0, h - 2.0)))
    smooth_shaded(lid)
    meat = ball("chicken", 30.0, m["chicken"], 18)
    meat.data.transform(Matrix.Diagonal((1.3, 1.0, 0.72, 1.0)))
    legs = []
    for side in (-1, 1):
        leg = tube("leg", [(side * 26.0, -8.0, -4.0), (side * 40.0, -24.0, 6.0)], 10.0, m["crust"], 10)
        bone = ball("bone", 6.0, m["bone"], 10, (side * 44.0, -28.0, 9.0))
        legs += [smooth_shaded(leg), bone]
    chicken = join([meat] + legs, "chicken")
    chicken.data.transform(Matrix.Translation((0.0, 0.0, h - 40.0)))
    return {"drum": (about(body, (0.0, 0.0, 0.0)), None), "lid": (about(lid, (0.0, 0.0, h)), "drum"),
            "chicken": (about(chicken, (0.0, 0.0, h - 40.0)), "drum")}, [], openbor_timeline, 150


def openbor_timeline(f):
    hit = smooth(phase(f, 10, 13)) * (1 - smooth(phase(f, 13, 26)))
    poses = {"drum": Pose(y=30.0 * hit, pitch=10.0 * hit + wobble(f, 26, 4.0, 10.0, 6.0),
                          roll=wobble(f, 18, 3.0, 12.0, 6.0))}
    pop = phase(f, 30, 58)
    landed = smooth(phase(f, 92, 100))
    poses["lid"] = Pose(z=hop(f, 30, 96, 210.0) * (1 - landed), x=60.0 * math.sin(math.pi * phase(f, 30, 96)),
                        pitch=360.0 * smooth(phase(f, 30, 92)), squash=wobble(f, 98, 0.1, 6.0, 3.0))
    up = hop(f, 36, 92, 230.0)
    seen = 1.0 if 34 <= f < 94 else 0.0
    poses["chicken"] = Pose(z=up, spin=540.0 * smooth(phase(f, 36, 92)), scale=HIDDEN + (1 - HIDDEN) * seen)
    return poses


# ---- Ports -----------------------------------------------------------------------------------------------------------

PORTS_COLOURS = dict(hull="#163E66", stripe="#B83222", deck="#C8CCD2", bridge="#ECEEF0", window="#1E2A38",
                     crane="#F2B21E", box="#F49519", sea="#3F9FD8")


def hull_ring(x, length):
    """The hull's cross-section at x along it, as (y, z) points from its deck's port edge round under its keel to
    its starboard edge: the bow narrowing to its stem, the stern square."""
    t = (x + length / 2) / length                         # 0 at the stern, 1 at the bow
    beam = 34.0 * (1.0 if t < 0.62 else math.cos((t - 0.62) / 0.38 * math.pi / 2) ** 0.8) + 0.6
    depth = 30.0 - 6.0 * max(0.0, t - 0.8) / 0.2
    sheer = 4.0 * max(0.0, t - 0.7) / 0.3                 # the bow's deck rising
    points = []
    for k in range(9):
        a = math.pi * k / 8                               # round the bilge from one deck edge to the other
        y = beam * math.cos(a)
        z = -depth * math.sin(a) ** 0.6
        points.append((y, z + sheer if k in (0, 8) else z))
    return points


def ports(m):
    length = 300.0
    rings = []
    for i in range(25):
        x = -length / 2 + length * i / 24
        rings.append([(x, y, z) for y, z in hull_ring(x, length)])
    hull = solid("hull", rings, m["hull"])
    hull.data.materials.append(m["stripe"])
    hull.data.materials.append(m["deck"])
    for p in hull.data.polygons:
        if p.normal.z > 0.9:
            p.material_index = 2
        elif p.center.z < -14.0:
            p.material_index = 1
    bridge = box("bridge", -150.0, -112.0, -26.0, 26.0, 0.0, 46.0, m["bridge"])
    windows = box("windows", -112.3, -111.5, -22.0, 22.0, 32.0, 40.0, m["window"])
    funnel = box("funnel", -146.0, -130.0, -8.0, 8.0, 46.0, 62.0, m["stripe"])
    pedestal = box("pedestal", -6.0, 6.0, -6.0, 6.0, 0.0, 44.0, m["crane"])
    ship = join([hull, bridge, windows, funnel, pedestal], "ship")
    for p in ship.data.polygons:
        p.use_smooth = False
    boom = box("boom", 0.0, 100.0, -4.0, 4.0, -4.0, 4.0, m["crane"])
    boom.data.transform(Matrix.Translation((0.0, 0.0, 44.0)) @ Matrix.Rotation(math.radians(-28.0), 4, "Y"))
    tip = Vector((100.0 * math.cos(math.radians(28.0)), 0.0, 44.0 + 100.0 * math.sin(math.radians(28.0))))
    cable = box("cable", tip.x - 0.8, tip.x + 0.8, -0.8, 0.8, 34.0, tip.z, m["window"])
    crate = box("container", tip.x - 24.0, tip.x + 24.0, -14.0, 14.0, 6.0, 34.0, m["box"])
    pad = [box("pad", tip.x - 13.0, tip.x + 13.0, -14.6, -14.0, 13.0, 27.0, m["bridge"])]
    for dx, dz, w_, h_ in ((-6.0, 20.0, 6.0, 2.0), (-6.0, 20.0, 2.0, 6.0)):   # its gamepad: the d-pad, two buttons
        pad.append(box("dpad", tip.x + dx - w_ / 2, tip.x + dx + w_ / 2, -15.2, -14.6, dz - h_ / 2, dz + h_ / 2,
                       m["window"]))
    for dx, dz in ((5.0, 22.0), (9.0, 18.0)):
        pad.append(box("button", tip.x + dx - 1.4, tip.x + dx + 1.4, -15.2, -14.6, dz - 1.4, dz + 1.4, m["stripe"]))
    crane = join([boom, cable, crate] + pad, "crane")
    sea = plate("sea", E.circle(0.0, 0.0, 1.0, 40), -1.0, 1.0, m["sea"])
    sea.data.transform(Matrix.Translation((0.0, 0.0, -12.0)) @ Matrix.Diagonal((186.0, 66.0, 1.0, 1.0)) @
                       Matrix.Rotation(-math.pi / 2, 4, "X"))       # turned to lie flat, then stretched to an oval
    one_tone(sea, m["sea"])
    crests = []
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        crests.append(tube("crest", [(166.0 * math.cos(a + t * 0.4), 56.0 * math.sin(a + t * 0.4), -10.5)
                                     for t in [i / 6 for i in range(7)]], 2.0, m["bridge"], 6))
    ship.location = (0.0, 0.0, 0.0)
    return {"ship": (ship, None), "crane": (about(crane, (0.0, 0.0, 44.0)), "ship")}, [sea] + crests, ports_timeline, \
        150


def ports_timeline(f):
    swell = 2 * math.pi * f / 75.0
    poses = {"ship": Pose(z=3.0 * math.sin(swell), roll=3.0 * math.sin(swell + 0.8), pitch=1.5 * math.sin(swell * 2))}
    out = smooth(phase(f, 20, 60)) * (1 - smooth(phase(f, 96, 132)))
    poses["crane"] = Pose(spin=-95.0 * out, z=6.0 * bump(f, 20, 132), roll=wobble(f, 60, 4.0, 18.0, 10.0)
                          - wobble(f, 132, 3.0, 16.0, 8.0))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

CARDS = dict(ags=(ags, AGS_COLOURS), chailove=(chailove, CHAI_COLOURS), openbor=(openbor, OPENBOR_COLOURS),
             ports=(ports, PORTS_COLOURS))
HIDDEN_AT_REST = ("cursor", "steam", "chicken")
TILTS = dict(chailove=(TILT_YAW, 30.0))                  # a cup of chai is seen from above, its heart on the tea


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, card, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    build, colours = CARDS[card]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    m = {name: material(name, colour, 0.3) for name, colour in colours.items()}
    if card == "openbor":
        m["drum"] = material("drum", "#FFFFFF", 0.5, bpy.data.images.load(os.path.join(images, "openbor_media.jpg")))
    parts, statics, timeline, length = build(m)

    root = bpy.data.objects.new(card + "_root", None)
    scene.collection.objects.link(root)
    meshes = []
    if statics:
        base = join(statics, card + "_base") if len(statics) > 1 else statics[0]
        base.parent = root
        meshes.append(base)
    for name, (obj, parent) in parts.items():
        obj.name = name
        obj.parent = parts[parent][0] if parent else root
        if parent:
            obj.location = Vector(obj.location) - parts[parent][0].location
        meshes.append(obj)
    bpy.context.view_layer.update()

    yaw, pitch = TILTS.get(card, (TILT_YAW, TILT_PITCH))
    tilt = Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    points = []
    for obj in meshes:
        if obj.name.startswith(HIDDEN_AT_REST):
            continue
        points += [tilt @ (obj.matrix_world @ v.co) for v in obj.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt
    nodes = {name: obj for name, (obj, _) in parts.items()}
    key("focused", nodes, lambda f: {k: v for k, v in timeline(f).items() if k in nodes}, length)
    print(f"{card}: {sum(triangles(o.data) for o in meshes)} triangles, "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
