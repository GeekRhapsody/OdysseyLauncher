"""The console theme's Game.com system model (godot/themes/console/models/systems/gamecom.glb): Tiger's Game.com,
standing up.

Built in Blender with handheld.py's pieces (gamecom_layout.py has the measurements, from Wikipedia and photographs): the
shell from its face's outline, its edges rounded, cut for the screen's sloping bezel, the D-pad's well, the speaker's
holes, the stylus's groove and the two cartridge slots in its right end; the silver pills round A B and C D and the
function strip standing on its face; the screens on the bezel's floor. The printing is two textures drawn by
gamecom_print.py (the face, a cartridge's label, swatches; the screens).

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting in slot 1, shrunk to
nothing), ON/OFF, the screens (each shrunk to nothing until it's shown), the D-pad, A, B, C, D and the stylus.

The `focused` clip (8 s, looping) plays a game: the cartridge (a made-up game) appears beside the right end, turns once
to show its label and slides into slot 1; ON/OFF, the start-up screen, the menu; the stylus lifts out of its groove and
taps GAME, and goes back; the game's title, and the game played on the D-pad and the buttons; then ON/OFF again and the
cartridge slides out and goes.

Three materials (case, glass, dark) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/gamecom_print.py artifacts/made-up-games artifacts/gamecom
    blender -b --factory-startup --python tools/console-models/gamecom.py -- artifacts/gamecom godot/themes/console/models/systems/gamecom.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamecom_layout as L  # noqa: E402
import handheld as H  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: its right end (the cartridge slots) comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.5, glass=0.3, dark=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
SCREENS = ("boot", "menu", "title", "game1", "game2")
GROOVE_Y = 1.0               # the stylus's axis, behind the face


def rect_ring(x0, x1, z0, z1, r, y):
    return [(x, y, z) for x, z in rounded((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, r, 4)]


def shell(m):
    part = H.body("gamecom", L.outline(), L.DEPTH, m["case"], front=2.5, back=4.0)
    x0, x1, z0, z1 = L.BEZEL["rect"]
    fw, fh = L.BEZEL["floor"]
    cx, cz = L.SCREEN["at"]
    cuts = [solid("bezel", [rect_ring(x0, x1, z0, z1, L.BEZEL["r"], -1.0),
                            rect_ring(cx - fw / 2, cx + fw / 2, cz - fh / 2, cz + fh / 2, 1.0, L.BEZEL["depth"])],
                  m["case"]),
            plate("well", H.circle(*L.DPAD["at"], L.DPAD["well"], 36), -1.0, 2.0, m["case"])]
    sx0, sx1 = L.STYLUS["x"]
    g = L.STYLUS["groove"]
    groove = [(x, GROOVE_Y + g * math.cos(2 * math.pi * k / 16), L.STYLUS["z"] + g * math.sin(2 * math.pi * k / 16))
              for x in (sx0 - 3.0, sx1 + 3.0) for k in range(16)]
    cuts.append(solid("groove", [groove[:16], groove[16:]], m["case"]))
    boolean(part, join(cuts, "cuts"))
    sp = L.SPEAKER
    (sxm, szm), (sw, sh) = sp["at"], sp["size"]
    holes = [plate("hole", H.circle(sxm - sw / 2 + sw * (i + 0.5 * (j % 2)) / sp["cols"], szm - sh / 2 + sh * j / (sp["rows"] - 1),
                                    sp["r"], 8), -2.0, 2.0, m["dark"])
             for j in range(sp["rows"]) for i in range(sp["cols"] - (j % 2))]
    slots = [box("slot", L.HALF - 4.0, L.HALF + 3.0, L.CART["y"] - L.CART["size"][1] / 2 - 0.6,
                 L.CART["y"] + L.CART["size"][1] / 2 + 0.6, s["z"][0] - 0.5, s["z"][1] + 0.5, m["dark"]) for s in L.SLOTS]
    boolean(part, join(holes + slots, "holes"))
    coloured(part, m["case"], ATLAS, "back")
    paint(part, m["case"], ATLAS.swatch("silver"), lambda c, n, kind: kind == "case" and abs(n.y) < 0.9 and c.z > 41.0)
    paint(part, m["case"], ATLAS.swatch("band"), lambda c, n, kind: kind == "case" and abs(n.y) < 0.9 and c.z <= 41.0)
    paint(part, m["case"], FACE, lambda c, n, kind: kind == "case" and (n.y < -0.9 or (n.y < -0.3 and c.y > 0.3)))
    return part


def silver_plates(m):
    out = []
    pl, pw = L.BUTTONS["pill"]
    for a, b in (("a", "b"), ("c", "d")):
        (ax, az), (bx, bz) = L.BUTTONS[a], L.BUTTONS[b]
        pill = plate("pill", H.stadium((ax + bx) / 2, (az + bz) / 2, pl, pw, L.BUTTONS["slant"]), -1.2, 0.5, m["case"])
        bevel(pill, 0.6, segments=2, angle=50)
        out.append(H.paint_face(coloured(pill, m["case"], ATLAS, "silver"), m["case"], FACE))
    (mx, mz), (px, pz) = L.STRIP["menu"], L.STRIP["pause"]
    lw, lh = L.STRIP["plate"]
    angle = math.degrees(math.atan2(pz - mz, px - mx))
    strip = plate("strip", H.stadium((mx + px) / 2, (mz + pz) / 2, lw, lh, angle), -0.8, 0.5, m["case"])
    bevel(strip, 0.5, segments=2, angle=50)
    out.append(H.paint_face(coloured(strip, m["case"], ATLAS, "silver"), m["case"], FACE))
    w, h = L.STRIP["size"]
    for name in ("menu", "sound", "pause"):
        cap = plate(name, H.stadium(*L.STRIP[name], w, h), -2.0, 0.0, m["case"])
        bevel(cap, 0.5, segments=2, angle=50)
        out.append(coloured(cap, m["case"], ATLAS, "teal"))
    ring = plate("ring", H.circle(*L.POWER["at"], L.POWER["ring"], 24), -0.8, 0.5, m["case"])
    out.append(coloured(ring, m["case"], ATLAS, "silver"))
    return out


def dome(name, r, h, m, swatch, at):
    part = lathe(name, [(0.0, -1.5), (r, -1.5), (r, h * 0.45)] + [(r * math.cos(math.pi / 2 * k / 4),
                                                                    h * 0.45 + h * 0.55 * math.sin(math.pi / 2 * k / 4))
                                                                   for k in range(1, 5)], m["case"], 24)
    part.data.transform(Matrix.Translation((at[0], 0.0, at[1])) @ Matrix.Rotation(math.radians(90.0), 4, "X"))
    coloured(part, m["case"], ATLAS, swatch)
    H.paint_face(part, m["case"], FACE, lambda c, n, kind: n.y < -0.5)
    part.data.transform(Matrix.Translation((-at[0], 0.0, -at[1])))
    return part


def dpad(m):
    x, z = L.DPAD["at"]
    part = plate("dpad", H.cross(x, z, L.DPAD["arm"], L.DPAD["half"]), -1.4, 2.0, m["case"])
    bevel(part, 0.8, segments=2, angle=50)
    coloured(part, m["case"], ATLAS, "button")
    H.paint_face(part, m["case"], FACE)
    part.data.transform(Matrix.Translation((-x, 0.0, -z)))
    return part


def stylus(m):
    """The stylus, its middle at its origin, lying along x, its tip at the left."""
    (x0, x1), r = L.STYLUS["x"], L.STYLUS["r"]
    mid = (x0 + x1) / 2
    profile = [(x0, 0.2), (x0 + 3.0, 1.0), (x0 + 26.0, 2.8), (-18.0, 3.1), (-17.0, r), (2.0, r), (3.0, 3.0),
               (x1 - 8.0, 2.6), (x1 - 2.0, 3.0), (x1, 2.4)]
    rings = [[(x - mid, r_ * math.cos(2 * math.pi * k / 16), L.STYLUS["z"] + r_ * math.sin(2 * math.pi * k / 16))
              for k in range(16)] for x, r_ in profile]
    part = solid("stylus", rings, m["case"])
    coloured(part, m["case"], ATLAS, "stylus")
    part.data.transform(Matrix.Translation((mid, GROOVE_Y, 0.0)))
    H.paint_face(part, m["case"], FACE, lambda c, n, kind: n.y < -0.6 and -17.0 < c.x < 2.0)
    at = Vector((mid, GROOVE_Y, L.STYLUS["z"]))
    part.data.transform(Matrix.Translation(-at))
    return part, at


def cartridge(m):
    """A cartridge, its label to the back, its middle at its origin, going in along -x."""
    length, t, w = L.CART["size"]
    part = box("cartridge", -length / 2, length / 2, -t / 2, t / 2, -w / 2, w / 2, m["case"])
    bevel(part, 0.8, segments=2)
    uv = ATLAS.uv("label", w, length)
    coloured(part, m["case"], ATLAS, "cart")
    paint(part, m["case"], lambda co: uv(w / 2 - co.z, length / 2 - co.x), lambda c, n, kind: n.y > 0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 62.0                   # how far right of its seat the cartridge waits: wholly out of its slot
TOUCH = Vector((23.5, -32.8, 60.0))   # the stylus's move from its groove to its tip on the menu's GAME, turned SPIN
SPIN = -35.0


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 50 <= f < 74:
        return "boot"
    if 74 <= f < 98:
        return "menu"
    if 98 <= f < 116:
        return "title"
    if 116 <= f < 190:
        return "game1" if ((f - 116) // 8) % 2 == 0 else "game2"
    return None


def stylus_pose(f):
    if f < 62 or f >= 120:
        return Pose()
    lift = smooth(phase(f, 62, 66)) * (1 - smooth(phase(f, 114, 120)))           # out of the groove and back in
    go = smooth(phase(f, 66, 80)) * (1 - smooth(phase(f, 100, 114)))             # to the screen and back
    hover = TOUCH + Vector((0.0, -3.0 + 3.0 * tap(f, 86, 3), 0.0))               # a tap on GAME
    away = Vector((0.0, -8.0 * lift, 0.0)) * (1 - go) + hover * go
    return Pose(*away, spin=SPIN * go)


def timeline(f):
    if f < 6 or f >= 226:
        cart = Pose(scale=HIDDEN)
    elif f < 16:
        cart = Pose(x=OUT, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 15)))
    elif f < 30:
        cart = Pose(x=OUT, z=4.0 * math.sin(math.pi * phase(f, 16, 30)), spin=360.0 * smooth(phase(f, 16, 30)))
    elif f < 198:
        cart = Pose(x=OUT * (1 - smooth(phase(f, 30, 42))))
    elif f < 214:
        cart = Pose(x=OUT * smooth(phase(f, 198, 210)))
    else:
        lift = ease_in(phase(f, 214, 226))
        cart = Pose(x=OUT, z=20.0 * lift, scale=max(HIDDEN, 1 - lift))
    poses = showing_poses(SCREENS, showing, f)
    poses.update({"cartridge": cart, "power": Pose(y=1.2 * max(tap(f, 46, 3), tap(f, 190, 3))), "stylus": stylus_pose(f)})
    for name, frames in (("button_a", (128, 152, 176)), ("button_b", (140, 164)), ("button_c", (134,)),
                         ("button_d", (158,))):
        poses[name] = Pose(y=1.4 * max(tap(f, f0) for f0 in frames))
    t = phase(f, 120, 186)
    wave = math.sin(math.pi * t)
    poses["dpad"] = Pose(pitch=6.0 * math.sin(2 * math.pi * 4 * t) * wave, spin=6.0 * math.sin(2 * math.pi * 3 * t + 0.8)
                         * wave)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", dark=L.COLOURS["ink"]), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "gamecom_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "gamecom_media.png"))))

    whole = smoothed(join([shell(m)] + silver_plates(m), "gamecom"), 40.0)
    pen, pen_at = stylus(m)
    length, t, w = L.CART["size"]
    seat = Vector((L.HALF - length / 2 - 0.5, L.CART["y"], sum(L.SLOTS[0]["z"]) / 2))
    parts = {"cartridge": (smoothed(cartridge(m)), seat), "stylus": (smoothed(pen, 50.0), pen_at),
             "power": (smoothed(dome("power", L.POWER["r"], 2.4, m, "teal", L.POWER["at"]), 50.0),
                       Vector((L.POWER["at"][0], -0.6, L.POWER["at"][1]))),
             "dpad": (smoothed(dpad(m), 40.0), Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1])))}
    for name in ("a", "b", "c", "d"):
        x, z = L.BUTTONS[name]
        parts["button_" + name] = (smoothed(dome("button_" + name, L.BUTTONS["r"], 3.2, m, "button", (x, z)), 50.0),
                                   Vector((x, -1.0, z)))
    fw, fh = L.SCREEN["size"]
    sx, sz = L.SCREEN["at"]
    parts.update(H.screens(SCREENS, fw, fh, MEDIA, m["glass"], (sx, L.BEZEL["depth"] - 0.05, sz)))
    finish("gamecom", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Game.com")


if __name__ == "__main__":
    main()
