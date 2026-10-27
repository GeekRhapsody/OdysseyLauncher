"""The console theme's Gamate system model (godot/themes/console/models/systems/gamate.glb): Bit Corporation's Gamate,
standing up.

Built in Blender with handheld.py's pieces (gamate_layout.py has the measurements, from scans of it): the dark grey
shell from its grips' outline, its edges rounded, cut for the speaker's holes, the D-pad's well, the band round A and B,
SELECT's and START's wells and the card's slot in its top edge; the screen section standing proud of its face and above
its top edge, the black bezel on it, the screens over its window; the yellow D-pad disc and A and B, the red pills, the
CONTRAST wheel and the ON·OFF knob. The printing is two textures drawn by gamate_print.py (the face, the card's label,
swatches; the screens).

A node tree (card.finish()): the root holding the set; the set holding the card (waiting in its slot, shrunk to
nothing), the ON·OFF knob, the screens (each shrunk to nothing until it's shown), the D-pad, A, B and START.

The `focused` clip (8 s, looping) plays a game: the card (a made-up game) appears over the handheld, turns once to show
its label and slides down into the back; the knob slides to ON; the start-up screen, the game's title, START, and the
game played on the D-pad, A and B; then OFF, and the card rises out and goes.

Three materials (case, glass, dark) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/gamate_print.py artifacts/made-up-games artifacts/gamate
    blender -b --factory-startup --python tools/console-models/gamate.py -- artifacts/gamate godot/themes/console/models/systems/gamate.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamate_layout as L  # noqa: E402
import handheld as H  # noqa: E402
from amiga import paint, rounded  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -20.0     # degrees about the vertical: its right end comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.6, glass=0.3, dark=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
SCREENS = ("boot", "title", "game1", "game2")


def shell(m):
    part = H.body("gamate", L.outline(), L.DEPTH, m["case"], front=3.0, back=6.0)
    sp = L.SPEAKER
    holes = []
    for i in range(sp["cols"]):
        for j in range(sp["rows"]):
            x = sp["x"][0] + (sp["x"][1] - sp["x"][0]) * i / (sp["cols"] - 1)
            z = sp["z"][0] + (sp["z"][1] - sp["z"][0]) * j / (sp["rows"] - 1)
            holes.append(plate("hole", H.circle(x, z, sp["r"], 8), -2.0, 2.0, m["dark"]))
    boolean(part, join(holes, "holes"))
    wells = [plate("well", H.circle(*L.DPAD["at"], L.DPAD["well"], 32), -2.0, 1.0, m["case"])]
    bl, bw = L.BUTTONS["band"]
    (ax, az), (bx, bz) = L.BUTTONS["a"], L.BUTTONS["b"]
    wells.append(plate("band", H.stadium((ax + bx) / 2, (az + bz) / 2, bl, bw, 45.0), -2.0, 0.8, m["case"]))
    pw, ph = L.PILLS["size"]
    for name in ("select", "start"):
        wells.append(plate("pill_well", H.stadium(*L.PILLS[name], pw + 3.0, ph + 3.0, L.PILLS["slant"]), -2.0, 0.8,
                           m["case"]))
    boolean(part, join(wells, "wells"))
    cw, ct, _ = L.CARD["size"]
    boolean(part, box("slot", -cw / 2 - 0.6, cw / 2 + 0.6, L.CARD["y"] - ct / 2 - 0.5, L.CARD["y"] + ct / 2 + 0.5,
                      2.0, L.SECTION["rect"][3] + 5.0, m["dark"]))
    coloured(part, m["case"], ATLAS, "body")
    paint(part, m["case"], FACE, lambda c, n, kind: n.y < -0.9 and kind == "case")
    return part


def section(m):
    """The screen section, proud of the face and above the top edge; the card's slot and the wheel's recess cut."""
    x0, x1, z0, z1 = L.SECTION["rect"]
    part = plate("section", rounded((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, L.SECTION["r"], 5),
                 -L.SECTION["proud"], L.DEPTH - 3.0, m["case"])
    bevel(part, 2.0, segments=2)
    cw, ct, _ = L.CARD["size"]
    boolean(part, box("slot", -cw / 2 - 0.6, cw / 2 + 0.6, L.CARD["y"] - ct / 2 - 0.5, L.CARD["y"] + ct / 2 + 0.5,
                      2.0, z1 + 5.0, m["dark"]))
    wx, wy = L.WHEEL["at"]
    boolean(part, box("wheel_recess", wx - L.WHEEL["r"] - 1.0, wx + L.WHEEL["r"] + 1.0, wy - L.WHEEL["width"] / 2 - 1.0,
                      wy + L.WHEEL["width"] / 2 + 1.0, z1 - 3.0, z1 + 5.0, m["dark"]))
    coloured(part, m["case"], ATLAS, "body")
    paint(part, m["case"], FACE, lambda c, n, kind: n.y < -0.9 and kind == "case")
    x0, x1, z0, z1 = L.BEZEL["rect"]
    bez = plate("bezel", rounded((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, L.BEZEL["r"], 4),
                -L.SECTION["proud"] - 0.5, -L.SECTION["proud"] + 1.0, m["case"])
    coloured(bez, m["case"], ATLAS, "bezel")
    H.paint_face(bez, m["case"], FACE)
    wx, wy = L.WHEEL["at"]
    wheel = lathe("wheel", [(0.0, -L.WHEEL["width"] / 2), (L.WHEEL["r"], -L.WHEEL["width"] / 2),
                            (L.WHEEL["r"], L.WHEEL["width"] / 2), (0.0, L.WHEEL["width"] / 2)], m["dark"], 20)
    wheel.data.transform(Matrix.Translation((wx, wy, L.SECTION["rect"][3] - 4.5)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    return [part, bez, wheel]


def dome(name, r, h, m, swatch):
    part = lathe(name, [(0.0, -1.5), (r, -1.5), (r, h * 0.5)] + [(r * math.cos(math.pi / 2 * k / 4),
                                                                   h * 0.5 + h * 0.5 * math.sin(math.pi / 2 * k / 4))
                                                                  for k in range(1, 5)], m["case"], 24)
    part.data.transform(Matrix.Rotation(math.radians(90.0), 4, "X"))
    return coloured(part, m["case"], ATLAS, swatch)


def dpad(m):
    x, z = L.DPAD["at"]
    part = plate("dpad", H.circle(x, z, L.DPAD["r"], 40), -3.4, 1.0, m["case"])
    bevel(part, 1.0, segments=2)
    coloured(part, m["case"], ATLAS, "yellow")
    H.paint_face(part, m["case"], FACE)
    part.data.transform(Matrix.Translation((-x, 0.0, -z)))
    return part


def pill(name, m):
    w, h = L.PILLS["size"]
    part = plate(name, H.stadium(0.0, 0.0, w, h, L.PILLS["slant"]), -2.0, 0.8, m["case"])
    bevel(part, 0.6, segments=2, angle=50)
    return coloured(part, m["case"], ATLAS, "red")


def knob(m):
    w, t, h = L.SWITCH["size"]
    x, y = L.SWITCH["at"]
    part = box("knob", x - w / 2, x + w / 2, y - t / 2, y + t / 2, L.HEIGHT - 2.0, L.HEIGHT + h, m["case"])
    bevel(part, 1.0, segments=2)
    return coloured(part, m["case"], ATLAS, "knob")


def card(m):
    """The card, its label to the back, its bottom's middle at its origin."""
    w, t, h = L.CARD["size"]
    part = box("card", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(part, 0.6, segments=2)
    uv = ATLAS.uv("label", w, h)
    coloured(part, m["case"], ATLAS, "card")
    paint(part, m["case"], lambda co: uv(w / 2 - co.x, h - co.z), lambda c, n, kind: n.y > 0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

ABOVE = 96.0                 # how far over its seat the card appears: wholly over the handheld


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 54 <= f < 84:
        return "boot"
    if 84 <= f < 104:
        return "title"
    if 104 <= f < 186:
        return "game1" if ((f - 104) // 8) % 2 == 0 else "game2"
    return None


def timeline(f):
    if f < 6 or f >= 222:
        crd = Pose(scale=HIDDEN)
    elif f < 16:
        crd = Pose(z=ABOVE, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 15)))
    elif f < 32:
        crd = Pose(z=ABOVE + 6.0 * math.sin(math.pi * phase(f, 16, 32)), spin=360.0 * smooth(phase(f, 16, 32)))
    elif f < 44:
        crd = Pose(z=ABOVE * (1 - ease_in(phase(f, 32, 44))))
    elif f < 198:
        crd = Pose(z=1.0 * math.exp(-(f - 44) / 3.0) * abs(math.sin(math.pi * (f - 44) / 5.0)))
    elif f < 212:
        crd = Pose(z=ABOVE * ease_out(phase(f, 198, 212)))
    else:
        crd = Pose(z=ABOVE, scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    on = smooth(phase(f, 48, 52)) * (1 - smooth(phase(f, 186, 190)))
    poses = showing_poses(SCREENS, showing, f)
    poses.update({"card": crd, "knob": Pose(x=L.SWITCH["travel"] * on), "start": Pose(y=1.0 * tap(f, 98, 3)),
                  "button_a": Pose(y=1.4 * max(tap(f, f0) for f0 in (116, 140, 164))),
                  "button_b": Pose(y=1.4 * max(tap(f, f0) for f0 in (126, 150, 174)))})
    t = phase(f, 106, 182)
    wave = math.sin(math.pi * t)
    poses["dpad"] = Pose(pitch=7.0 * math.sin(2 * math.pi * 4 * t) * wave, spin=7.0 * math.sin(2 * math.pi * 3 * t + 0.8)
                         * wave)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", glass="#FFFFFF", dark=L.COLOURS["dark"]), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "gamate_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "gamate_media.png"))))

    select = pill("select", m)
    select.data.transform(Matrix.Translation((L.PILLS["select"][0], 0.0, L.PILLS["select"][1])))
    whole = smoothed(join([shell(m), select] + section(m), "gamate"), 40.0)
    w, t, h = L.CARD["size"]
    seat = Vector((0.0, L.CARD["y"], L.SECTION["rect"][3] - h))
    parts = {"card": (smoothed(card(m)), seat), "knob": (smoothed(knob(m)), Vector()),
             "dpad": (smoothed(dpad(m), 40.0), Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1]))),
             "button_a": (smoothed(dome("button_a", L.BUTTONS["r"], 3.4, m, "yellow"), 50.0),
                          Vector((L.BUTTONS["a"][0], 0.0, L.BUTTONS["a"][1]))),
             "button_b": (smoothed(dome("button_b", L.BUTTONS["r"], 3.4, m, "yellow"), 50.0),
                          Vector((L.BUTTONS["b"][0], 0.0, L.BUTTONS["b"][1]))),
             "start": (smoothed(pill("start", m)), Vector((L.PILLS["start"][0], 0.0, L.PILLS["start"][1])))}
    sw, sh = L.SCREEN["size"]
    sx, sz = L.SCREEN["at"]
    parts.update(H.screens(SCREENS, sw, sh, MEDIA, m["glass"], (sx, -L.SECTION["proud"] - 0.55, sz)))
    finish("gamate", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Gamate")


if __name__ == "__main__":
    main()
