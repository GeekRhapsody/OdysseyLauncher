"""The console theme's Game Master system model (godot/themes/console/models/systems/gmaster.glb): Hartung's Game
Master, standing up.

Built in Blender with handheld.py's pieces (gmaster_layout.py has the measurements, from Wikipedia and photographs): the
slate grey shell from its face's outline, its edges rounded, cut for the speaker's holes and the cartridge's slot in its
top edge, a lobe over each battery bay on its back; the glossy black band standing proud of its face (a visor along the
top edge, round the screen), the silver surround on it, the screens over its window; the D-pad, START and SELECT, A and
B in silver-grey. The printing is two textures drawn by gmaster_print.py (the face, the cartridge's label, swatches; the
screens).

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting in its slot, shrunk to
nothing), the screens (each shrunk to nothing until it's shown), the D-pad, A, B and START.

The `focused` clip (8 s, looping) plays a game: the cartridge (a made-up game) appears over the handheld, turns once to
show its label and drops into the slot in its back; the start-up screen, the game's title, START, and the game played
on the D-pad, A and B; then the screen goes blank and the cartridge rises out and goes.

Four materials (case, band, glass, dark) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/gmaster_print.py artifacts/made-up-games artifacts/gmaster
    blender -b --factory-startup --python tools/console-models/gmaster.py -- artifacts/gmaster godot/themes/console/models/systems/gmaster.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gmaster_layout as L  # noqa: E402
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
ROUGHNESS = dict(case=0.55, band=0.15, glass=0.3, dark=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
SCREENS = ("boot", "title", "game1", "game2")


def shell(m):
    part = H.body("gmaster", L.outline(), L.DEPTH, m["case"], front=3.0, back=4.0)
    sp = L.SPEAKER
    holes = [plate("hole", H.circle(x0 + sp["pitch"] * k, z, sp["r"], 8), -2.0, 2.0, m["dark"])
             for x0, z in sp["rows"] for k in range(sp["count"])]
    boolean(part, join(holes, "holes"))
    cw, ct, _ = L.CART["size"]
    boolean(part, box("slot", -cw / 2 - 0.6, cw / 2 + 0.6, L.DEPTH - ct - 2.0, L.DEPTH + 1.0, L.HEIGHT - 52.0,
                      L.HEIGHT + 5.0, m["dark"]))
    coloured(part, m["case"], ATLAS, "body")
    paint(part, m["case"], FACE, lambda c, n, kind: n.y < -0.9 and kind == "case")
    lobes = []
    (x0, x1), (z0, z1) = L.LOBES["x"], L.LOBES["z"]
    for sign in (-1, 1):
        a, b = sorted((sign * x0, sign * x1))
        lobe = box("lobe", a, b, L.DEPTH - 3.0, L.DEPTH + L.LOBES["depth"], z0, z1, m["case"])
        bevel(lobe, 4.0, segments=3)
        lobes.append(coloured(lobe, m["case"], ATLAS, "body"))
    return [part] + lobes


def band(m):
    part = plate("band", L.BAND["outline"], -L.BAND["proud"], 1.0, m["band"])
    bevel(part, 0.8, segments=2, angle=50)
    coloured(part, m["band"], ATLAS, "band")
    sx0, sx1, sz0, sz1 = L.SURROUND["rect"]
    surround = plate("surround", rounded((sx0 + sx1) / 2, (sz0 + sz1) / 2, sx1 - sx0, sz1 - sz0, L.SURROUND["r"], 4),
                     -L.BAND["proud"] - L.SURROUND["proud"], -L.BAND["proud"] + 0.5, m["case"])
    coloured(surround, m["case"], ATLAS, "surround")
    H.paint_face(surround, m["case"], FACE)
    return [part, surround]


def dome(name, r, h, m, swatch):
    part = lathe(name, [(0.0, -1.5), (r, -1.5), (r, h * 0.45)] + [(r * math.cos(math.pi / 2 * k / 4),
                                                                    h * 0.45 + h * 0.55 * math.sin(math.pi / 2 * k / 4))
                                                                   for k in range(1, 5)], m["case"], 24)
    part.data.transform(Matrix.Rotation(math.radians(90.0), 4, "X"))
    return coloured(part, m["case"], ATLAS, swatch)


def dpad(m):
    x, z = L.DPAD["at"]
    part = plate("dpad", H.cross(x, z, L.DPAD["arm"], L.DPAD["half"]), -3.0, 1.0, m["case"])
    bevel(part, 0.8, segments=2, angle=50)
    coloured(part, m["case"], ATLAS, "button")
    H.paint_face(part, m["case"], FACE)
    part.data.transform(Matrix.Translation((-x, 0.0, -z)))
    return part


def cartridge(m):
    """The cartridge, its label out of the back, its bottom's middle at its origin."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(part, 0.8, segments=2)
    uv = ATLAS.uv("label", w, h)
    coloured(part, m["case"], ATLAS, "cart")
    paint(part, m["case"], lambda co: uv(w / 2 - co.x, h - co.z), lambda c, n, kind: n.y > 0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

ABOVE = 64.0


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    if 50 <= f < 80:
        return "boot"
    if 80 <= f < 102:
        return "title"
    if 102 <= f < 188:
        return "game1" if ((f - 102) // 8) % 2 == 0 else "game2"
    return None


def timeline(f):
    if f < 6 or f >= 222:
        cart = Pose(scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=ABOVE, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 15)))
    elif f < 32:
        cart = Pose(z=ABOVE + 6.0 * math.sin(math.pi * phase(f, 16, 32)), spin=360.0 * smooth(phase(f, 16, 32)))
    elif f < 44:
        cart = Pose(z=ABOVE * (1 - ease_in(phase(f, 32, 44))))
    elif f < 198:
        cart = Pose(z=1.0 * math.exp(-(f - 44) / 3.0) * abs(math.sin(math.pi * (f - 44) / 5.0)))
    elif f < 212:
        cart = Pose(z=ABOVE * ease_out(phase(f, 198, 212)))
    else:
        cart = Pose(z=ABOVE, scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    poses = showing_poses(SCREENS, showing, f)
    poses.update({"cartridge": cart, "start": Pose(y=1.0 * tap(f, 96, 3)),
                  "button_a": Pose(y=1.4 * max(tap(f, f0) for f0 in (114, 138, 162))),
                  "button_b": Pose(y=1.4 * max(tap(f, f0) for f0 in (124, 148, 172)))})
    t = phase(f, 104, 184)
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
    printed = bpy.data.images.load(os.path.join(images, "gmaster_print.png"))
    m = materials(dict(case="#FFFFFF", band="#FFFFFF", glass="#FFFFFF", dark=L.COLOURS["dark"]), ROUGHNESS,
                  dict(case=printed, band=printed, glass=bpy.data.images.load(os.path.join(images, "gmaster_media.png"))))

    select = dome("select", L.BUTTONS["small"], 2.4, m, "button")
    select.data.transform(Matrix.Translation((L.BUTTONS["select"][0], 0.0, L.BUTTONS["select"][1])))
    whole = smoothed(join(shell(m) + band(m) + [select], "gmaster"), 40.0)
    w, t, h = L.CART["size"]
    seat = Vector((0.0, L.DEPTH - t / 2 - 1.5, L.HEIGHT + L.CART["out"] - h))
    parts = {"cartridge": (smoothed(cartridge(m)), seat),
             "dpad": (smoothed(dpad(m), 40.0), Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1]))),
             "button_a": (smoothed(dome("button_a", L.BUTTONS["r"], 4.0, m, "button"), 50.0),
                          Vector((L.BUTTONS["a"][0], 0.0, L.BUTTONS["a"][1]))),
             "button_b": (smoothed(dome("button_b", L.BUTTONS["r"], 4.0, m, "button"), 50.0),
                          Vector((L.BUTTONS["b"][0], 0.0, L.BUTTONS["b"][1]))),
             "start": (smoothed(dome("start", L.BUTTONS["small"], 2.4, m, "button"), 50.0),
                       Vector((L.BUTTONS["start"][0], 0.0, L.BUTTONS["start"][1])))}
    sw, sh = L.SCREEN["size"]
    sx, sz = L.SCREEN["at"]
    parts.update(H.screens(SCREENS, sw, sh, MEDIA, m["glass"],
                           (sx, -L.BAND["proud"] - L.SURROUND["proud"] - 0.05, sz)))
    finish("gmaster", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Game Master")


if __name__ == "__main__":
    main()
