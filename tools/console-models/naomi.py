"""The console theme's NAOMI system model (godot/themes/console/models/systems/naomi.glb): a Sega candy cabinet running
NAOMI.

NAOMI is an arcade board, played in cabinets (naomi_layout.py): its card is a white candy cabinet, NAOMI on its marquee.
The cabinet is its side outline extruded across its width; the screen's recess is cut into the bezel's slope (its black
surround), the CRT's curved glass set in it. The control panel's top carries its overlay, the two joysticks (ball tops),
the buttons and the coin plate; the lower cabinet's front its coin doors, the kick plate at its foot. The printing is two
textures drawn by naomi_print.py: the marquee, the speaker panel, the control panel's overlay, the lower front and
swatches; and the screens.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, a
little from above; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the set; the
set holding the screens over the glass (the game's title, two frames of play), shrunk to nothing so at rest the glass
shows NAOMI's logo, the coin (waiting over the coin slot, shrunk to nothing), the 1P stick, two of its buttons and the
1P START button with its light.

The `focused` clip (8 s, looping) plays a credit: a coin drops into the slot, CREDIT 1 and PRESS START come up with
START flashing; START is pressed and the game plays, the stick waggling and the buttons firing; then back to the logo.

Six materials (case, dark, metal, print, glass, button) and two textures, within the system model budget. Run from the
repo root:

    python tools/console-models/naomi_print.py artifacts/naomi
    blender -b --factory-startup --python tools/console-models/naomi.py -- artifacts/naomi godot/themes/console/models/systems/naomi.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import naomi_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -28.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.45, dark=0.6, metal=0.3, print=0.4, glass=0.1, button=0.35)

# The bezel's frame (x across, s up the slope from its foot, h out of it) and the control panel's (x, v back along its
# top from its front edge, h up out of it).
BEZEL_FRAME = Matrix.Translation((0.0, *L.BEZEL[0])) @ Matrix.Rotation(math.radians(L.bezel_angle()), 4, "X")
PANEL_ANGLE = math.atan2(L.PANEL[1][1] - L.PANEL[0][1], L.PANEL[1][0] - L.PANEL[0][0])
PANEL_FRAME = Matrix.Translation((0.0, *L.PANEL[0])) @ Matrix.Rotation(PANEL_ANGLE, 4, "X")
GLASS_TURN = Matrix.Rotation(math.radians(L.bezel_angle() - 90.0), 4, "X")   # a screen facing -y onto the slope


def atlas_uv(region, w, h):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


def painted(obj, m, name):
    paint(obj, m["print"], swatch(name), lambda c, n, _name: True)
    return obj


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def in_frame(name, frame, outline, h0, h1, mat):
    """A solid from an (x, s) outline in a frame, from h0 to h1 off it."""
    return solid(name, [[frame @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def slanted_uv(region, top, foot, width):
    """UVs for a sloping face from top to foot ((y, z) each), width across: a, across from the left; b, down it."""
    (y0, z0), (y1, z1) = top, foot
    length = math.hypot(y1 - y0, z1 - z0)
    uv = atlas_uv(region, width, length)

    def of(co):
        b = ((co.y - y0) * (y1 - y0) + (co.z - z0) * (z1 - z0)) / length
        return uv(co.x + width / 2, b)
    return of


# ---- The cabinet -----------------------------------------------------------------------------------------------------

def cabinet(m):
    """The cabinet: its outline across its width, the screen's recess, the printed faces."""
    w = L.WIDTH
    body = prism_x("naomi", L.profile(), -w / 2, w / 2, m["case"])
    bevel(body, 8.0, segments=3)
    s = L.SCREEN
    (x0, x1), (s0, s1) = s["x"], s["s"]
    recess = in_frame("recess", BEZEL_FRAME, rounded(0.0, (s0 + s1) / 2, x1 - x0, s1 - s0, 16.0, 4), -s["depth"],
                      30.0, m["dark"])
    boolean(body, recess)
    # The bezel's black surround: the slope's face round the recess.
    surround = in_frame("surround", BEZEL_FRAME, rounded(0.0, L.bezel_length() / 2, w - 70.0, L.bezel_length() - 10.0,
                                                         20.0, 4), -1.0, 1.5, m["dark"])
    boolean(surround, in_frame("hole", BEZEL_FRAME, rounded(0.0, (s0 + s1) / 2, x1 - x0, s1 - s0, 16.0, 4), -5.0,
                               5.0, m["dark"]))
    width = w - 50.0
    paint(body, m["print"], slanted_uv(L.REGIONS["marquee"], *L.MARQUEE, width),
          lambda c, n, name: name == "case" and n.y < -0.5 and c.z > L.MARQUEE[1][1] - 1.0 and abs(c.x) < width / 2)
    paint(body, m["print"], slanted_uv(L.REGIONS["speakers"], *L.SPEAKERS, width),
          lambda c, n, name: name == "case" and n.y < -0.4 and n.z < 0.0 and L.SPEAKERS[1][1] - 1.0 < c.z
          < L.SPEAKERS[0][1] + 1.0 and abs(c.x) < width / 2)
    panel = atlas_uv(L.REGIONS["panel"], w, L.PANEL_DEPTH)
    paint(body, m["print"], lambda co: panel(co.x + w / 2, L.PANEL_DEPTH - co.y),
          lambda c, n, name: name == "case" and n.z > 0.9 and c.z < 840.0)
    front = atlas_uv(L.REGIONS["front"], w, 700.0)
    paint(body, m["print"], lambda co: front(co.x + w / 2, 700.0 - co.z),
          lambda c, n, name: name == "case" and n.y < -0.9 and c.z < 700.0 and abs(c.y - L.LOWER_Y) < 1.0)
    k = L.KICK
    kick = box("kick", -w / 2 + 6.0, w / 2 - 6.0, L.LOWER_Y - k["out"], L.LOWER_Y + 2.0, *k["z"], m["metal"])
    glass = curved("glass", *s["glass"], s["bulge"], atlas_uv(L.MEDIA_REGIONS["boot"], 1.0, 1.0), m["glass"], 12, 9)
    glass.data.transform(Matrix.Translation(BEZEL_FRAME @ Vector((0.0, s["middle"], -s["depth"] + 16.0))) @ GLASS_TURN)
    return [body, surround, kick, glass]


def controls(m):
    """The control panel's fixed parts: the 2P stick, the buttons but the ones the clip presses, 2P START, the coin
    plate."""
    parts = []
    b = L.BUTTONS
    for k, (x, v) in enumerate(b["p1"]):
        if k in (0, 1):
            continue
        parts.append(button("p1", x, v, "green", m))
    for x, v in b["p2"]:
        parts.append(button("p2", x, v, "pink", m))
    parts.append(button("start2", *b["start"][1], "yellow", m))
    shaft, ball = stick(m)
    paint(ball, m["print"], swatch("pink"), lambda c, n, name: True)
    for part in (shaft, ball):
        part.data.transform(PANEL_FRAME @ Matrix.Translation((*L.STICKS["p2"], 0.0)))
        parts.append(part)
    cx, cv = L.COIN["at"]
    pw, pd = L.COIN["plate"]
    plate = painted(in_frame("coin_plate", PANEL_FRAME, rounded(cx, cv, pw, pd, 5.0, 3), -1.0, 4.0, m["print"]), m,
                    "metal")
    sw, sd = L.COIN["slot"]
    boolean(plate, in_frame("slot", PANEL_FRAME, [(cx - sw / 2, cv - sd / 2), (cx + sw / 2, cv - sd / 2),
                                                  (cx + sw / 2, cv + sd / 2), (cx - sw / 2, cv + sd / 2)], 1.0, 8.0,
                            m["dark"]))
    parts.append(plate)
    return parts


def button(name, x, v, colour, m):
    r, h = L.BUTTONS["r"], L.BUTTONS["height"]
    part = painted(in_frame(name, PANEL_FRAME, circle(x, v, r, 24), -2.0, h, m["print"]), m, colour)
    bevel(part, 1.6, segments=2)
    return part


def stick(m):
    """A joystick, its foot at its origin: the shaft and the ball top."""
    r, length = L.STICKS["shaft"]
    shaft = solid("shaft", [[(x, y, z) for x, y in circle(0.0, 0.0, r, 12)] for z in (-2.0, length)], m["dark"])
    br = L.STICKS["ball"]
    ball = solid("ball", [[(br * math.cos(math.radians(lat)) * math.cos(2 * math.pi * k / 20),
                            br * math.cos(math.radians(lat)) * math.sin(2 * math.pi * k / 20),
                            length + br * 0.8 + br * math.sin(math.radians(lat))) for k in range(20)]
                          for lat in range(-80, 81, 20)], m["button"])
    for poly in ball.data.polygons:
        poly.use_smooth = True
    return shaft, ball


# ---- The moving parts ------------------------------------------------------------------------------------------------

def moving(m):
    """The 1P stick, its first two buttons, 1P START and its light, the coin; each its origin where it moves from."""
    parts = {}
    shaft, ball = stick(m)
    lever = join([shaft, ball], "stick")
    paint(lever, m["print"], swatch("green"), lambda c, n, name: name == "button")
    turn = PANEL_FRAME.to_3x3().to_4x4()
    lever.data.transform(turn)
    parts["stick"] = (lever, PANEL_FRAME @ Vector((*L.STICKS["p1"], 0.0)))
    for k in (0, 1):
        x, v = L.BUTTONS["p1"][k]
        b = button(f"button{k + 1}", 0.0, 0.0, "green", m)
        b.data.transform(Matrix.Translation(-(PANEL_FRAME @ Vector((0.0, 0.0, 0.0)))))
        parts[f"button{k + 1}"] = (b, PANEL_FRAME @ Vector((x, v, 0.0)))
    x, v = L.BUTTONS["start"][0]
    start = button("start", 0.0, 0.0, "yellow", m)
    start.data.transform(Matrix.Translation(-(PANEL_FRAME @ Vector((0.0, 0.0, 0.0)))))
    parts["start"] = (start, PANEL_FRAME @ Vector((x, v, 0.0)))
    lit = button("start_light", 0.0, 0.0, "yellow_lit", m)
    lit.data.transform(Matrix.Translation(-(PANEL_FRAME @ Vector((0.0, 0.0, 0.0)))))
    lit.data.transform(Matrix.Scale(1.04, 4))
    parts["start_light"] = (lit, PANEL_FRAME @ Vector((x, v, 0.4)))
    coin = painted(solid("coin", [[(xx, yy, zz) for xx, zz in circle(0.0, 0.0, 11.0, 20)] for yy in (-1.0, 1.0)],
                         m["print"]), m, "coin")
    coin.data.transform(Matrix.Rotation(math.radians(90.0), 4, "Z"))     # on edge, along the slot
    cx, cv = L.COIN["at"]
    parts["coin"] = (coin, PANEL_FRAME @ Vector((cx, cv, 4.0)))
    return parts


def screens(m):
    s = L.SCREEN
    out = {}
    for k, name in enumerate(("title", "game1", "game2")):
        part = curved("screen_" + name, *s["glass"], s["bulge"], atlas_uv(L.MEDIA_REGIONS[name], 1.0, 1.0),
                      m["glass"], 12, 9)
        part.data.transform(GLASS_TURN)
        out["screen_" + name] = (part, BEZEL_FRAME @ Vector((0.0, s["middle"], -s["depth"] + 16.6 + 0.3 * k)))
    return out


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


PRESS = PANEL_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))


def timeline(f):
    poses = {}
    if f < 8 or f >= 29:
        poses["coin"] = Pose(scale=HIDDEN)
    elif f < 16:
        poses["coin"] = Pose(z=60.0, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 8, 14)))
    else:                                                  # it drops into the slot
        poses["coin"] = Pose(z=60.0 - 76.0 * ease_in(phase(f, 16, 28)))
    shown = None
    if 30 <= f < 64:
        shown = "title"
    elif 64 <= f < 200:
        shown = "game1" if ((f - 64) // 7) % 2 == 0 else "game2"
    for name in ("title", "game1", "game2"):
        poses["screen_" + name] = Pose() if name == shown else Pose(scale=HIDDEN)
    flash = 30 <= f < 60 and (f // 6) % 2 == 0
    poses["start_light"] = Pose() if flash else Pose(scale=HIDDEN)
    poses["start"] = Pose(*(PRESS * 3.0 * tap(f, 58)))
    for k, frames in ((1, (80, 96, 112, 140, 168)), (2, (88, 120, 150, 176))):
        poses[f"button{k}"] = Pose(*(PRESS * 3.0 * max(tap(f, f0) for f0 in frames)))
    t = phase(f, 70, 190)
    poses["stick"] = Pose(pitch=14.0 * math.sin(2 * math.pi * 3 * t) * math.sin(math.pi * t),
                          roll=18.0 * math.sin(2 * math.pi * 5 * t) * math.sin(math.pi * t))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "naomi_print.png"))
    media = bpy.data.images.load(os.path.join(images, "naomi_media.png"))
    colours = dict(L.COLOURS, button="#1A1A1C")
    textures = dict(print=printed, glass=media)
    m = {n: material(n, colours[n], r, textures.get(n)) for n, r in ROUGHNESS.items()}

    whole = join(cabinet(m) + controls(m), "naomi")
    for poly in whole.data.polygons:
        poly.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))
    parts = moving(m)
    parts.update(screens(m))

    root = bpy.data.objects.new("naomi_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    for name, (part, where) in parts.items():
        part.parent = whole
        part.location = where
    nodes = {name: part for name, (part, _) in parts.items()}

    tilt = Matrix.Rotation(math.radians(TILT_PITCH), 4, "X") @ Matrix.Rotation(math.radians(TILT_YAW), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    key("focused", nodes, timeline, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"NAOMI: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + meshes, out, animations=True)


if __name__ == "__main__":
    main()
