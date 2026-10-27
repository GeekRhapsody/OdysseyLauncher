"""The console theme's emblem cards (godot/themes/console/models/systems/<card>.glb): for systems with no hardware of
their own, their emblem made solid.

Built in Blender from emblems_layout.py's shapes, each card from its own function here (CARDS):
- `doom`: Doom's four letters in steel, their faces rust red; the `focused` clip jolts each back in turn, as a
  shotgun's blast would, its face glowing ember orange a moment, then all four at once.
- `quake`: Quake's rune in rusted iron, its nail driven into a stone; the clip pulls it out, turns it round in the air
  and slams it back, the stone shaking, dust puffing and a crack glowing in it a moment.
- `easyrpg`: EasyRPG's three curling arms on their disc, a medallion; the clip springs it up spinning, as an item got
  in a role-playing game, sparkles round it, and lands it.
- `solarus`: Solarus's sun on its purple disc, a steel sword across it; the clip draws the sword out, spins it and
  plunges it back, the sun flaring.
- `lutro`: Lutro's disc, split purple and green, its heart raised on it; the clip beats the heart twice and turns the
  disc round to its back, where a moon goes once round a navy planet, and back.
- `mugen`: M.U.G.E.N's letters on an arena's floor, bobbing as fighters do; the clip has the M throw a ball of energy
  at the N, which reels from the hit.
- `mess`: MESS's slanted letters among a mess of cartridges, a floppy disk, a cassette and a calculator; the clip hops
  them one by one onto a tidy pile, then they tumble back into a mess.
Each shape is drawn from simple geometry or set in a font (emblems_layout.py), not traced from a logo's artwork.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH; then the model spec's fit: standing on
y = 0, centred, the largest side 1 m) holding the card's parts, each moving part its own node, its origin where it
turns. Plain materials, no texture, within the system model budget. Run from the repo root:

    blender -b --factory-startup --python tools/console-models/emblems.py -- <card> godot/themes/console/models/systems/<card>.glb
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emblems_layout as L  # noqa: E402
from clip import HIDDEN, Pose, back_out, bump, ease_in, ease_out, hop, key, phase, smooth, wobble  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, new_object, triangles  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: the top tips a little towards the viewer
FONTS = "C:/Windows/Fonts/"


# ---- Shapes ----------------------------------------------------------------------------------------------------------

def plate(name, outline, y0, y1, mat, holes=()):
    """An (x, z) outline from y0 (its face, towards the viewer) back to y1, its holes cut through it."""
    bm = bmesh.new()
    front = [bm.verts.new((x, y0, z)) for x, z in outline]
    back = [bm.verts.new((x, y1, z)) for x, z in outline]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(outline)
    for i in range(n):
        bm.faces.new([front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = new_object(name, bm, mat)
    for hole in holes:
        boolean(obj, plate("hole", hole, y0 - 5.0, y1 + 5.0, mat))
    return obj


def two_tone(obj, face, side, smooth_sides=True):
    """The faces towards the viewer and away the face's material, the rest the side's; the face flat-shaded so it
    lights evenly."""
    mesh = obj.data
    mesh.materials.clear()
    mesh.materials.append(face)
    mesh.materials.append(side)
    for p in mesh.polygons:
        p.material_index = 0 if abs(p.normal.y) > 0.3 else 1
        p.use_smooth = smooth_sides and abs(p.normal.y) < 0.99
    mesh.set_sharp_from_angle(angle=math.radians(30))
    return obj


def one_tone(obj, mat, smooth_all=False):
    mesh = obj.data
    mesh.materials.clear()
    mesh.materials.append(mat)
    for p in mesh.polygons:
        p.material_index = 0
        p.use_smooth = smooth_all
    if smooth_all:
        mesh.set_sharp_from_angle(angle=math.radians(40))
    return obj


def disc(name, r, y0, y1, mat, n=48, cx=0.0, cz=0.0):
    """A disc facing the viewer, its middle at (cx, cz)."""
    return plate(name, L.circle(cx, cz, r, n), y0, y1, mat)


def ball(name, r, mat, n=16, centre=(0.0, 0.0, 0.0)):
    from amiga import solid
    cx, cy, cz = centre
    obj = solid(name, [[(cx + r * math.cos(math.radians(lat)) * math.cos(2 * math.pi * k / n),
                         cy + r * math.cos(math.radians(lat)) * math.sin(2 * math.pi * k / n),
                         cz + r * math.sin(math.radians(lat))) for k in range(n)]
                       for lat in range(-80, 81, 20)], mat)
    return one_tone(obj, mat, smooth_all=True)


def star(cx, cz, r, points=4, inner=0.32):
    return [(cx + (r if k % 2 == 0 else r * inner) * math.cos(math.pi * k / points + math.pi / 2),
             cz + (r if k % 2 == 0 else r * inner) * math.sin(math.pi * k / points + math.pi / 2))
            for k in range(points * 2)]


def lettering(name, text, font, size, depth, mat, stretch=1.0, shear=0.0):
    """Text set in a font, facing the viewer (-y), its baseline at z = 0 from x = 0, depth thick; and its width."""
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = text
    curve.font = bpy.data.fonts.load(FONTS + font, check_existing=True)
    curve.size = size
    curve.extrude = depth / 2
    curve.bevel_depth = 1.2
    curve.bevel_resolution = 2
    curve.resolution_u = 6
    curve.shear = shear
    holder = bpy.data.objects.new(name + "_curve", curve)
    bpy.context.scene.collection.objects.link(holder)
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(holder.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(holder)
    mesh.transform(Matrix.Rotation(math.pi / 2, 4, "X") @ Matrix.Scale(stretch, 4, (1.0, 0.0, 0.0)))
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.clear()
    mesh.materials.append(mat)
    xs = [v.co.x for v in mesh.vertices]
    return obj, (max(xs) - min(xs) if xs else 0.0), (min(xs) if xs else 0.0)


def about(obj, origin):
    """The object's mesh moved so that origin is its origin; placed back there."""
    obj.data.transform(Matrix.Translation(-Vector(origin)))
    obj.location = origin
    return obj


# ---- Doom ------------------------------------------------------------------------------------------------------------

def doom(m):
    parts = {}
    for k, ((outline, holes), x) in enumerate(zip(L.DOOM_LETTERS, L.DOOM_X)):
        shape, cut = L.moved(outline, x, 0.0), [L.moved(h, x, 0.0) for h in holes]
        letter = plate(f"letter{k}", L.ccw(shape), 0.0, L.DOOM_DEPTH, m["face"], [L.ccw(h) for h in cut])
        bevel(letter, 2.5, segments=2, angle=30.0)
        two_tone(letter, m["face"], m["side"])
        xs = [p[0] for p in shape]
        middle = ((min(xs) + max(xs)) / 2, L.DOOM_DEPTH / 2, 0.0)
        parts[f"letter{k}"] = (about(letter, middle), None)
        ember = plate(f"ember{k}", L.ccw(shape), -1.6, -0.4, m["ember"], [L.ccw(h) for h in cut])
        one_tone(ember, m["ember"])
        parts[f"ember{k}"] = (about(ember, (middle[0], -1.0, 40.0)), f"letter{k}")
    return parts, [], doom_timeline, 150


def doom_timeline(f):
    poses = {}
    for k in range(4):
        jolts = (20 + 12 * k, 96)
        kick = max(smooth(phase(f, j, j + 2)) * (1 - smooth(phase(f, j + 2, j + 14))) for j in jolts)
        settle = sum(wobble(f, j + 14, 0.25, period=9.0, decay=5.0) for j in jolts)
        poses[f"letter{k}"] = Pose(y=24.0 * kick, pitch=-9.0 * kick + 4.0 * settle)
        hot = max(1 - smooth(phase(f, j + 2, j + 22)) if f >= j else 0.0 for j in jolts)
        poses[f"ember{k}"] = Pose(scale=HIDDEN + (1 - HIDDEN) * hot)
    return poses


# ---- Quake -----------------------------------------------------------------------------------------------------------

def quake(m):
    half = L.QUAKE_DEPTH / 2
    rune = plate("rune", L.quake_crescent(), -half, half, m["face"])
    boolean(rune, plate("nail", L.ccw(L.QUAKE_NAIL), -half - 2.0, half + 2.0, m["face"]), "UNION")
    bevel(rune, 1.6, segments=2, angle=30.0)
    two_tone(rune, m["face"], m["side"])
    s = L.QUAKE_SLAB
    stone = box("stone", *s["x"], *s["y"], *s["z"], m["stone"])
    bevel(stone, 5.0, segments=2, angle=30.0)
    one_tone(stone, m["stone"])
    top = s["z"][1]
    crack = plate("crack", L.ccw([(-70.0, 0.0), (-40.0, 6.0), (-22.0, -4.0), (0.0, 3.0), (24.0, -6.0), (46.0, 4.0),
                                  (72.0, -2.0), (72.0, 4.0), (46.0, 10.0), (24.0, 0.0), (0.0, 9.0), (-22.0, 2.0),
                                  (-40.0, 12.0), (-70.0, 6.0)]), -0.6, 0.6, m["crack"])
    crack.data.transform(Matrix.Translation((0.0, 0.0, top + 0.5)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    one_tone(crack, m["crack"])
    parts = {"rune": (rune, None), "stone": (about(stone, (0.0, 0.0, s["z"][0])), None),
             "crack": (about(crack, (0.0, 0.0, top + 0.5)), "stone")}
    for k in range(6):
        a = 2 * math.pi * (k + 0.5) / 6
        at = (34.0 * math.cos(a), 24.0 * math.sin(a), top + 6.0)
        parts[f"dust{k}"] = (about(ball(f"dust{k}", 9.0, m["dust"], 10, at), at), None)
    return parts, [], quake_timeline, 150


def quake_timeline(f):
    rise = smooth(phase(f, 10, 40))
    slam = ease_in(phase(f, 84, 92))
    z = 96.0 * rise * (1 - slam) + wobble(f, 92, -6.0, period=8.0, decay=4.0)
    poses = {"rune": Pose(z=z, spin=360.0 * smooth(phase(f, 42, 80)), squash=wobble(f, 92, 0.12, 7.0, 4.0))}
    shake = math.exp(-max(0.0, f - 92) / 6.0) * (f >= 92)
    poses["stone"] = Pose(x=4.0 * shake * math.sin(f * 2.3), y=2.0 * shake * math.cos(f * 3.1))
    glow = smooth(phase(f, 92, 94)) * (1 - smooth(phase(f, 112, 132)))
    poses["crack"] = Pose(scale=HIDDEN + (1 - HIDDEN) * glow)
    for k in range(6):
        t = phase(f, 92, 118)
        a = 2 * math.pi * (k + 0.5) / 6
        out = ease_out(t) * 40.0
        size = (bump(f, 92, 118) if 92 <= f < 118 else 0.0)
        poses[f"dust{k}"] = Pose(x=out * math.cos(a), y=out * math.sin(a) * 0.7, z=14.0 * ease_out(t),
                                 scale=HIDDEN + (1 - HIDDEN) * size)
    return poses


# ---- EasyRPG ---------------------------------------------------------------------------------------------------------

def easyrpg(m):
    r = L.EASYRPG_DISC
    face = disc("disc", r, -7.0, 7.0, m["disc"], 64)
    bevel(face, 2.0, segments=2, angle=30.0)
    one_tone(face, m["disc"], smooth_all=True)
    rim = plate("rim", L.circle(0.0, 0.0, r + 5.0, 64), -9.0, 9.0, m["rim"], [L.circle(0.0, 0.0, r - 1.0, 64)])
    bevel(rim, 2.0, segments=2, angle=30.0)
    one_tone(rim, m["rim"], smooth_all=True)
    arms = plate("arms", L.easyrpg_arm(0), -15.0, -6.0, m["arm"])
    for k in (1, 2):
        boolean(arms, plate(f"arm{k}", L.easyrpg_arm(k), -15.0, -6.0, m["arm"]), "UNION")
    bevel(arms, 1.6, segments=2, angle=30.0)
    two_tone(arms, m["arm"], m["arm_side"])
    medallion = join([face, rim, arms], "medallion")
    for p in medallion.data.polygons:
        p.use_smooth = abs(p.normal.y) < 0.99
    medallion.data.transform(Matrix.Translation((0.0, 0.0, r + 5.0)))
    parts = {"medallion": (about(medallion, (0.0, 0.0, r + 5.0)), None)}
    for k in range(5):                                    # waiting in the medallion's middle till they twinkle
        z = r + 5.0
        spark = one_tone(plate(f"spark{k}", L.ccw(star(0.0, z, 9.0)), -21.0, -19.0, m["spark"]), m["spark"])
        parts[f"spark{k}"] = (about(spark, (0.0, -20.0, z)), None)
    return parts, [], easyrpg_timeline, 150


def easyrpg_timeline(f):
    up = smooth(phase(f, 14, 40)) * (1 - ease_in(phase(f, 96, 112)))
    squash = (0.14 * smooth(phase(f, 4, 14)) * (1 - smooth(phase(f, 14, 17)))
              + wobble(f, 112, 0.16, period=8.0, decay=4.0))
    poses = {"medallion": Pose(z=110.0 * up, spin=720.0 * smooth(phase(f, 16, 92)), squash=squash)}
    for k in range(5):                                    # round the medallion as it hangs in the air; at rest,
        f0 = 34 + 9 * k                                   # hidden in its middle (the launcher fits the rest pose)
        twinkle = bump(f, f0, f0 + 26) if f0 <= f < f0 + 26 else 0.0
        out = 1.0 if f0 - 1 <= f < f0 + 27 else 0.0
        a = 2 * math.pi * k / 5 + 0.4
        poses[f"spark{k}"] = Pose(x=95.0 * math.cos(a) * out, z=(110.0 + 80.0 * math.sin(a)) * out,
                                  roll=90.0 * phase(f, f0, f0 + 26), scale=HIDDEN + (1 - HIDDEN) * twinkle)
    return poses


# ---- Solarus ---------------------------------------------------------------------------------------------------------

def sword(m):
    """The sword along +x from its point, lying flat facing the viewer: the blade, the guard, the grip, the pommel."""
    s = L.SWORD
    length, width = s["blade"]
    blade = plate("blade", L.ccw([(0.0, 0.0), (14.0, width / 2), (length, width / 2), (length, -width / 2),
                                  (14.0, -width / 2)]), -2.5, 2.5, m["blade"])
    span, depth = s["guard"]
    guard = plate("guard", L.ccw(L.arc(length + 2.0, 0.0, span / 2, -70.0, 70.0, 16)
                                 + L.arc(length + 2.0 + depth, 0.0, span / 2 - 4.0, 66.0, -66.0, 16)), -4.0, 4.0,
                  m["hilt"])
    grip = plate("grip", L.ccw([(length + 4.0, -4.5), (length + 4.0 + s["grip"], -4.5),
                                (length + 4.0 + s["grip"], 4.5), (length + 4.0, 4.5)]), -4.5, 4.5, m["hilt"])
    pommel = ball("pommel", s["pommel"], m["hilt"], 14, (length + 6.0 + s["grip"] + s["pommel"] * 0.7, 0.0, 0.0))
    part = join([blade, guard, grip, pommel], "sword")
    bevel(part, 0.8, segments=1, angle=30.0)
    return part


def solarus(m):
    back = disc("disc", L.SOLARUS_DISC, 0.0, 12.0, m["disc"], 64)
    bevel(back, 2.0, segments=2, angle=30.0)
    two_tone(back, m["disc"], m["disc_side"])
    sun = plate("sun", L.solarus_sun(), -14.0, 0.5, m["sun"])
    bevel(sun, 2.0, segments=2, angle=30.0)
    two_tone(sun, m["sun"], m["sun_side"])
    lift = L.SOLARUS_DISC + 4.0
    emblem = join([back, sun], "emblem")
    emblem.data.transform(Matrix.Translation((0.0, 0.0, lift)))
    glow = one_tone(plate("glow", L.solarus_sun(), -15.2, -14.6, m["glow"]), m["glow"])
    glow.data.transform(Matrix.Translation((0.0, 0.0, lift)))
    blade = sword(m)
    s = L.SWORD
    a = math.radians(s["angle"])
    middle = s["blade"][0] * 0.6
    blade.data.transform(Matrix.Translation((-middle, 0.0, 0.0)))
    blade.data.transform(Matrix.Rotation(-a, 4, "Y"))
    px, pz = s["point"]
    centre = (px + middle * math.cos(a), -20.0, lift + pz + middle * math.sin(a))
    parts = {"emblem": (about(emblem, (0.0, 0.0, lift)), None), "glow": (about(glow, (0.0, -15.0, lift)), "emblem"),
             "sword": (blade, None)}
    blade.location = centre
    return parts, [], solarus_timeline, 150


def solarus_timeline(f):
    a = math.radians(L.SWORD["angle"])
    out = 76.0 * smooth(phase(f, 10, 36)) * (1 - ease_in(phase(f, 74, 84)))
    poses = {"sword": Pose(x=out * math.cos(a), z=out * math.sin(a), y=-30.0 * bump(f, 10, 84),
                           pitch=0.0, roll=-360.0 * smooth(phase(f, 38, 70)))}
    flare = smooth(phase(f, 84, 88)) * (1 - smooth(phase(f, 100, 124)))
    poses["glow"] = Pose(scale=HIDDEN + (1 - HIDDEN) * flare)
    poses["emblem"] = Pose(z=10.0 * flare + wobble(f, 84, 3.0, period=9.0, decay=5.0))
    return poses


# ---- Lutro -----------------------------------------------------------------------------------------------------------

def lutro(m):
    r, split = L.LUTRO_DISC, L.LUTRO_SPLIT
    halves = []
    for name, a0 in (("purple", split), ("green", split + 180.0)):
        half = plate(name, L.ccw(L.arc(0.0, 0.0, r, a0, a0 + 180.0, 40)), -6.0, 6.0, m[name])
        bevel(half, 1.6, segments=2, angle=30.0)
        halves.append(two_tone(half, m[name], m["side"]))
    planet = one_tone(disc("planet", r * 0.62, 5.6, 7.0, m["navy"], 48), m["navy"])
    body = join(halves + [planet], "disc")
    for p in body.data.polygons:
        p.use_smooth = abs(p.normal.y) < 0.99
    shape = plate("heart", L.heart(0.0, 0.0, 52.0), -13.0, -5.0, m["heart"])
    bevel(shape, 2.4, segments=3, angle=30.0)
    one_tone(shape, m["heart"], smooth_all=True)
    moon = ball("moon", 8.0, m["moon"], 14)
    parts = {"disc": (body, None), "heart": (shape, "disc"), "moon": (moon, "disc")}
    body.location = (0.0, 0.0, r + 2.0)
    shape.location = (0.0, 0.0, r + 2.0)
    moon.location = (0.0, 14.0, r + 2.0 + r * 0.62 + 14.0)
    return parts, [], lutro_timeline, 150


def lutro_timeline(f):
    beat = max(bump(f, f0, f0 + 8) if f0 <= f < f0 + 8 else 0.0 for f0 in (8, 22))
    turn = 180.0 * smooth(phase(f, 38, 58)) * (1 - smooth(phase(f, 116, 136)))
    poses = {"heart": Pose(scale=1 + 0.18 * beat), "disc": Pose(spin=turn, z=hop(f, 38, 58, 14.0) + hop(f, 116, 136,
                                                                                                         14.0))}
    t = phase(f, 62, 110)
    a = 2 * math.pi * t
    ring = L.LUTRO_DISC * 0.62 + 14.0
    poses["moon"] = Pose(x=ring * math.sin(a), z=ring * (math.cos(a) - 1.0))
    return poses


# ---- M.U.G.E.N -------------------------------------------------------------------------------------------------------

def mugen(m):
    t = L.MUGEN
    parts, statics = {}, []
    x = 0.0
    width = {}
    for k, ch in enumerate(t["text"]):
        letter, w, x0 = lettering(f"ch{k}", ch, t["font"], t["size"], t["depth"], m["face"], stretch=t["stretch"])
        letter.data.transform(Matrix.Translation((x - x0, 0.0, 0.0)))
        two_tone(letter, m["face"], m["side"])
        width[k] = (x, x + w)
        if ch == ".":
            statics.append(letter)
        else:
            parts[f"letter{k}"] = (about(letter, (x + w / 2, 0.0, 0.0)), None)
        x += w + (8.0 if ch != "." else 6.0)
    total = x
    for name, (obj, _) in parts.items():
        obj.location.x -= total / 2
    for obj in statics:
        obj.data.transform(Matrix.Translation((-total / 2, 0.0, 0.0)))
    from amiga import rounded
    stage = rounded(0.0, 0.0, total + 40.0, 110.0, 40.0, 6)
    floor = plate("floor", stage, -5.0, 5.0, m["floor"])
    floor.data.transform(Matrix.Translation((0.0, 0.0, -5.0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    ring = plate("ring", rounded(0.0, 0.0, total + 24.0, 94.0, 32.0, 6), -0.6, 0.6, m["ring"],
                 [rounded(0.0, 0.0, total + 16.0, 86.0, 28.0, 6)])
    ring.data.transform(Matrix.Translation((0.0, 0.0, 0.4)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    statics += [one_tone(floor, m["floor"]), one_tone(ring, m["ring"])]
    first, last = min(parts), max(parts, key=lambda n: int(n[6:]))
    start = parts[first][0].location
    end = parts[last][0].location
    at = (start.x + 50.0, -30.0, 60.0)
    energy = ball("energy", 18.0, m["ball"], 16, at)
    hit = one_tone(plate("hit", L.ccw(star(end.x - 30.0, 60.0, 40.0, 6, 0.4)), -41.0, -39.0, m["spark"]),
                   m["spark"])
    parts["energy"] = (about(energy, at), None)
    parts["hit"] = (about(hit, (end.x - 30.0, -40.0, 60.0)), None)
    MUGEN_ENDS.update(first=first, last=last, run=end.x - start.x - 80.0)
    # A fighting game's HUD over the stage: each fighter's health bar in its frame, the timer between them.
    h = L.MUGEN_HUD
    z0, z1, length, gap = h["z"], h["z"] + h["height"], h["bar"], h["gap"]
    for side in (-1, 1):
        x0, x1 = sorted((side * gap / 2, side * (gap / 2 + length)))
        frame = plate("frame", L.ccw([(x0 - 4.0, z0 - 4.0), (x1 + 4.0, z0 - 4.0), (x1 + 4.0, z1 + 4.0),
                                      (x0 - 4.0, z1 + 4.0)]), 0.0, 6.0, m["floor"])
        statics.append(one_tone(frame, m["floor"]))
        fill = one_tone(plate("bar", L.ccw([(x0, z0), (x1, z0), (x1, z1), (x0, z1)]), -2.0, 0.5, m["bar"]), m["bar"])
        inner = side * gap / 2
        parts["bar_right" if side > 0 else "bar_left"] = (about(fill, (inner, -1.0, z0)), None)
    timer, w, x0 = lettering("timer", "99", "ariblk.ttf", 30.0, 8.0, m["face"])
    timer.data.transform(Matrix.Translation((-x0 - w / 2, 2.0, z0 - 6.0)))
    statics.append(two_tone(timer, m["face"], m["side"]))
    return parts, statics, mugen_timeline, 150


MUGEN_ENDS = {}


def mugen_timeline(f):
    poses = {}
    live = smooth(phase(f, 0, 12)) * (1 - smooth(phase(f, 136, 150)))
    names = sorted((n for n in ("letter0", "letter2", "letter4", "letter6", "letter8")), key=lambda n: int(n[6:]))
    for k, name in enumerate(names):
        poses[name] = Pose(z=6.0 * live * (1 + math.sin(2 * math.pi * f / 30.0 + k * 1.3)) / 2,
                           roll=3.0 * live * math.sin(2 * math.pi * f / 30.0 + k * 1.3))
    first, last = MUGEN_ENDS["first"], MUGEN_ENDS["last"]
    wind = smooth(phase(f, 40, 52)) * (1 - smooth(phase(f, 52, 56)))
    poses[first] = Pose(z=poses[first].offset.z, roll=12.0 * wind - 10.0 * bump(f, 52, 64))
    t = phase(f, 54, 76)
    poses["energy"] = Pose(x=MUGEN_ENDS["run"] * ease_in(t), z=10.0 * math.sin(math.pi * t),
                           spin=720.0 * t, scale=HIDDEN + (1 - HIDDEN) * (1.0 if 54 <= f < 77 else 0.0))
    struck = smooth(phase(f, 76, 80)) * (1 - smooth(phase(f, 90, 110)))
    poses[last] = Pose(x=16.0 * struck, roll=-14.0 * struck, z=poses[last].offset.z)
    poses["hit"] = Pose(roll=40.0 * phase(f, 76, 88), scale=HIDDEN + (1 - HIDDEN) * (bump(f, 76, 90) if 76 <= f < 90
                                                                                     else 0.0))
    lost = 0.35 * smooth(phase(f, 78, 92)) * (1 - smooth(phase(f, 134, 150)))   # the N's health, refilled to loop
    poses["bar_right"] = Pose(axes=(1.0 - lost, 1.0, 1.0))
    return poses


# ---- MESS ------------------------------------------------------------------------------------------------------------

# The mess: each thing's size (w, d, h), where it lies messily (x, y, its turn about the vertical) and the tidy pile
# it hops onto (its place in the pile, from the bottom).
CLUTTER = [("cassette", (100.0, 63.0, 12.0)), ("floppy", (90.0, 94.0, 3.4)), ("calculator", (70.0, 120.0, 12.0)),
           ("cart1", (60.0, 66.0, 14.0)), ("cart2", (54.0, 70.0, 12.0)), ("card", (40.0, 30.0, 4.0))]
MESSY = [(-125.0, -80.0, 25.0), (-15.0, -112.0, -35.0), (92.0, -88.0, 60.0), (168.0, -36.0, -20.0),
         (-196.0, -34.0, 75.0), (40.0, -50.0, 12.0)]
PILE = (238.0, -70.0)


def mess(m):
    t = L.MESS
    word, w, x0 = lettering("mess", t["text"], t["font"], t["size"], t["depth"], m["face"], shear=t["shear"])
    word.data.transform(Matrix.Translation((-x0 - w / 2, 30.0, 0.0)))
    two_tone(word, m["face"], m["side"])
    parts = {}
    for (name, (w_, d, h)), (x, y, turn) in zip(CLUTTER, MESSY):
        thing = clutter_thing(name, w_, d, h, m)
        thing.data.transform(Matrix.Rotation(math.radians(turn), 4, "Z"))
        thing.location = (x, y, 0.0)
        parts[name] = (thing, None)
    return parts, [word], mess_timeline, 180


def clutter_thing(name, w, d, h, m):
    """One thing of the mess, lying flat, its origin at its bottom's middle."""
    kind = name.rstrip("12")
    body = box(name, -w / 2, w / 2, -d / 2, d / 2, 0.0, h, m[{"cassette": "cassette", "floppy": "floppy",
                                                                "calculator": "calc", "cart": "cart",
                                                                "card": "cart"}[kind]])
    bevel(body, min(2.0, h / 3), segments=2, angle=30.0)
    extras = []
    if kind == "cassette":
        extras.append(box("sticker", -w * 0.4, w * 0.4, -d * 0.4, d * 0.2, h, h + 0.6, m["metal"]))
    elif kind == "floppy":
        extras.append(box("shutter", -w * 0.2, w * 0.2, d * 0.1, d / 2, h, h + 0.5, m["metal"]))
    elif kind == "calculator":
        extras.append(box("display", -w * 0.38, w * 0.38, d * 0.22, d * 0.42, h, h + 0.6, m["cassette"]))
        for i in range(4):
            for j in range(4):
                extras.append(box("key", -w * 0.36 + i * w * 0.19, -w * 0.36 + i * w * 0.19 + w * 0.14,
                                  -d * 0.4 + j * d * 0.14, -d * 0.4 + j * d * 0.14 + d * 0.1, h, h + 1.6,
                                  m["cassette"]))
    elif kind in ("cart", "card"):
        extras.append(box("sticker", -w * 0.38, w * 0.38, -d * 0.36, d * 0.3, h, h + 0.5, m["sticker"]))
    part = join([body] + extras, name)
    for p in part.data.polygons:
        p.use_smooth = False
    return part


def mess_timeline(f):
    poses = {}
    floor = 0.0
    heights = [h for _, (_, _, h) in CLUTTER]
    for k, ((name, _), (x, y, turn)) in enumerate(zip(CLUTTER, MESSY)):
        f0 = 10 + 12 * k
        go = smooth(phase(f, f0, f0 + 14))
        back = smooth(phase(f, 128 + 3 * k, 150 + 3 * k))
        tidy = go * (1 - back)
        px, py = PILE
        dx, dy = (px - x) * tidy, (py - y) * tidy
        z = (floor + 2.0 * k) * tidy + hop(f, f0, f0 + 14, 70.0) + hop(f, 128 + 3 * k, 150 + 3 * k, 40.0)
        z += wobble(f, 150 + 3 * k, 3.0, period=7.0, decay=3.0)
        poses[name] = Pose(x=dx, y=dy, z=z, spin=-turn * tidy + 20.0 * (k % 2 - 0.5) * back * (1 - back) * 4,
                           pitch=25.0 * math.sin(math.pi * phase(f, 128 + 3 * k, 150 + 3 * k)))
        floor += heights[k]
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

CARDS = dict(doom=(doom, L.DOOM_COLOURS), quake=(quake, L.QUAKE_COLOURS), easyrpg=(easyrpg, L.EASYRPG_COLOURS),
             solarus=(solarus, L.SOLARUS_COLOURS), lutro=(lutro, L.LUTRO_COLOURS), mugen=(mugen, L.MUGEN_COLOURS),
             mess=(mess, L.MESS_COLOURS))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    card, out = args[0], os.path.abspath(args[1])
    build, colours = CARDS[card]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    m = {name: material(name, colour, 0.4) for name, colour in colours.items()}
    parts, statics, timeline, length = build(m)

    root = bpy.data.objects.new(card + "_root", None)
    scene.collection.objects.link(root)
    meshes = []
    if statics:
        base = join(statics, card) if len(statics) > 1 else statics[0]
        base.name = card
        base.parent = root
        meshes.append(base)
    for name, (obj, parent) in parts.items():
        obj.name = name
        obj.parent = parts[parent][0] if parent else root
        if parent:                                         # its place relative to its parent's origin
            obj.location = Vector(obj.location) - parts[parent][0].location
        meshes.append(obj)
    bpy.context.view_layer.update()

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = []
    for obj in meshes:
        if obj.name.startswith(("ember", "glow", "crack", "dust", "spark", "energy", "hit")):
            continue                                        # hidden at rest
        world = obj.matrix_world
        points += [tilt @ (world @ v.co) for v in obj.data.vertices]
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
