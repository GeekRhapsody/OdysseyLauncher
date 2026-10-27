"""The console theme's Mega Duck system model (godot/themes/console/models/systems/megaduck.glb): Welback's Mega Duck
WG-108, standing up.

Built in Blender with handheld.py's pieces (megaduck_layout.py has the measurements, from Wikipedia and photographs):
the white shell from its face's outline, its edges rounded, cut for the speaker's slanting slots and the cartridge's bay
at the top of its back; the slate bezel standing a little off its face, the screens over its window; the turquoise D-pad
(its disc and cross) and B and A, SELECT and START, the CONTRAST and VOL wheels in their grey bezels out of its sides, the
power knob on its top edge. The printing is two textures drawn by megaduck_print.py (the face, the back, the
cartridge's label, swatches; the screens).

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting in the bay, shrunk to
nothing), the power knob, the battery light (shrunk to nothing), the screens (each shrunk to nothing until it's shown),
the D-pad, B, A and START.

The `focused` clip (8 s, looping) plays a game: the cartridge (a made-up game) appears over the handheld, turns once
to show its label and drops into the bay; the knob slides to ON and the light comes on; the start-up screen, the
game's title, START, and the game played on the D-pad, B and A; then OFF, and the cartridge rises out and goes.

Three materials (case, glass, dark) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/megaduck_print.py artifacts/made-up-games artifacts/megaduck
    blender -b --factory-startup --python tools/console-models/megaduck.py -- artifacts/megaduck godot/themes/console/models/systems/megaduck.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handheld as H  # noqa: E402
import megaduck_layout as L  # noqa: E402
from amiga import paint, rounded  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from devices import showing_poses  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: its right side comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.45, glass=0.3, dark=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
MEDIA = Atlas(L.ATLAS, L.MEDIA_REGIONS)
FACE = H.face_uv(ATLAS, "face", L.SPAN)
BACK = H.back_uv(ATLAS, "back", L.SPAN)
SCREENS = ("boot", "title", "game1", "game2")


def shell(m):
    part = H.body("megaduck", L.outline(), L.DEPTH, m["case"], front=3.0, back=5.0)
    w, h = L.SPEAKER["size"]
    boolean(part, join([plate("slot", H.stadium(x, z, w, h, L.SPEAKER["slant"]), -2.0, 1.4, m["dark"])
                        for x, z in L.SPEAKER["at"]], "slots"))
    bw, depth = L.CART["bay"]
    boolean(part, box("bay", -bw, bw, L.DEPTH - 9.0, L.DEPTH + 2.0, L.HEIGHT - depth, L.HEIGHT + 5.0, m["dark"]))
    coloured(part, m["case"], ATLAS, "shell")
    paint(part, m["case"], FACE, lambda c, n, kind: n.y < -0.9 and kind == "case")
    paint(part, m["case"], BACK, lambda c, n, kind: n.y > 0.9 and kind == "case")
    return part


def bezel(m):
    x0, x1, z0, z1 = L.BEZEL["rect"]
    part = plate("bezel", rounded((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, L.BEZEL["r"], 4), -L.BEZEL["out"],
                 0.6, m["case"])
    coloured(part, m["case"], ATLAS, "bezel")
    return H.paint_face(part, m["case"], FACE)


def wheels(m):
    out = []
    (z0, z1), (y0, y1) = L.WHEELS["z"], L.WHEELS["y"]
    side = L.UPPER / 2
    for sign in (-1, 1):
        a, b = sorted((sign * (side - 1.5), sign * (side + L.WHEELS["out"])))
        rim = box("wheel_bezel", a, b, y0, y1, z0, z1, m["case"])
        bevel(rim, 2.4, segments=3)
        coloured(rim, m["case"], ATLAS, "grey")
        a, b = sorted((sign * (side + L.WHEELS["out"] - 2.0), sign * (side + L.WHEELS["out"] + 0.6)))
        wheel = box("wheel", a, b, y0 + 4.0, y1 - 4.0, z0 + 4.0, z1 - 4.0, m["dark"])
        bevel(wheel, 1.2, segments=2)
        out += [rim, wheel]
    return out


def dome(name, r, h, m, swatch):
    """A round button facing the viewer, its foot's middle at its origin."""
    part = lathe(name, [(0.0, -1.5), (r, -1.5), (r, h * 0.5)] + [(r * math.cos(math.pi / 2 * k / 4),
                                                                   h * 0.5 + h * 0.5 * math.sin(math.pi / 2 * k / 4))
                                                                  for k in range(1, 5)], m["case"], 24)
    part.data.transform(Matrix.Rotation(math.radians(90.0), 4, "X"))
    return coloured(part, m["case"], ATLAS, swatch)


def dpad(m):
    d = L.DPAD
    base = plate("dpad_base", H.circle(0.0, 0.0, d["r"], 32), -1.4, 1.0, m["case"])
    bevel(base, 0.6, segments=2)
    arms = plate("dpad_cross", H.cross(0.0, 0.0, d["arm"], d["half"]), -3.6, -1.0, m["case"])
    bevel(arms, 1.2, segments=2, angle=50)
    return coloured(join([base, arms], "dpad"), m["case"], ATLAS, "turquoise")


def pill(name, m):
    w, h = L.PILLS["size"]
    part = plate(name, H.stadium(0.0, 0.0, w, h, L.PILLS["slant"]), -1.8, 0.8, m["case"])
    bevel(part, 0.8, segments=2, angle=50)
    return coloured(part, m["case"], ATLAS, "grey")


def knob(m):
    w, t, h = L.KNOB["size"]
    x, y = L.KNOB["at"]
    part = box("knob", x - w / 2, x + w / 2, y - t / 2, y + t / 2, L.HEIGHT - 2.0, L.HEIGHT + h, m["case"])
    bevel(part, 1.2, segments=2)
    return coloured(part, m["case"], ATLAS, "grey")


def light(m):
    part = plate("battery_light", H.circle(0.0, 0.0, L.LIGHT["r"] + 0.2, 12), -0.25, 0.1, m["case"])
    return coloured(part, m["case"], ATLAS, "lit"), Vector((L.LIGHT["at"][0], -L.BEZEL["out"], L.LIGHT["at"][1]))


def cartridge(m):
    """The cartridge, its label to the back, its bottom's middle at its origin."""
    w, t, h = L.CART["size"]
    part = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(part, 0.8, segments=2)
    uv = ATLAS.uv("label", w, h)
    coloured(part, m["case"], ATLAS, "cart")
    paint(part, m["case"], lambda co: uv(w / 2 - co.x, h - co.z), lambda c, n, kind: n.y > 0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

ABOVE = 72.0


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
        cart = Pose(scale=HIDDEN)
    elif f < 16:
        cart = Pose(z=ABOVE, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 15)))
    elif f < 32:
        cart = Pose(z=ABOVE + 6.0 * math.sin(math.pi * phase(f, 16, 32)), spin=360.0 * smooth(phase(f, 16, 32)))
    elif f < 44:
        cart = Pose(z=ABOVE * (1 - ease_in(phase(f, 32, 44))))
    elif f < 198:
        cart = Pose(z=1.2 * math.exp(-(f - 44) / 3.0) * abs(math.sin(math.pi * (f - 44) / 5.0)))
    elif f < 212:
        cart = Pose(z=ABOVE * ease_out(phase(f, 198, 212)))
    else:
        cart = Pose(z=ABOVE, scale=max(HIDDEN, 1 - ease_in(phase(f, 212, 222))))
    on = smooth(phase(f, 48, 52)) * (1 - smooth(phase(f, 186, 190)))
    poses = showing_poses(SCREENS, showing, f)
    poses.update({"cartridge": cart, "knob": Pose(x=L.KNOB["travel"] * on),
                  "battery_light": Pose() if 52 <= f < 188 else Pose(scale=HIDDEN),
                  "start": Pose(y=1.2 * tap(f, 98, 3)),
                  "button_b": Pose(y=1.4 * max(tap(f, f0) for f0 in (114, 138, 162))),
                  "button_a": Pose(y=1.4 * max(tap(f, f0) for f0 in (124, 148, 172)))})
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
                  dict(case=bpy.data.images.load(os.path.join(images, "megaduck_print.png")),
                       glass=bpy.data.images.load(os.path.join(images, "megaduck_media.png"))))

    select = pill("select", m)
    select.data.transform(Matrix.Translation((L.PILLS["select"][0], 0.0, L.PILLS["select"][1])))
    whole = smoothed(join([shell(m), bezel(m), select] + wheels(m), "megaduck"), 40.0)
    lit, lit_at = light(m)
    w, t, h = L.CART["size"]
    seat = Vector((0.0, L.DEPTH - 5.0, L.HEIGHT + L.CART["out"] - h))
    sx, sz = L.SCREEN["at"]
    parts = {"cartridge": (smoothed(cartridge(m)), seat), "knob": (smoothed(knob(m)), Vector()),
             "battery_light": (lit, lit_at),
             "dpad": (smoothed(dpad(m), 40.0), Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1]))),
             "button_b": (smoothed(dome("button_b", L.BUTTONS["r"], 3.6, m, "turquoise"), 50.0),
                          Vector((L.BUTTONS["b"][0], 0.0, L.BUTTONS["b"][1]))),
             "button_a": (smoothed(dome("button_a", L.BUTTONS["r"], 3.6, m, "turquoise"), 50.0),
                          Vector((L.BUTTONS["a"][0], 0.0, L.BUTTONS["a"][1]))),
             "start": (smoothed(pill("start", m)), Vector((L.PILLS["start"][0], 0.0, L.PILLS["start"][1])))}
    sw, sh = L.SCREEN["size"]
    parts.update(H.screens(SCREENS, sw, sh, MEDIA, m["glass"], (sx, -L.BEZEL["out"] - 0.05, sz)))
    finish("megaduck", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Mega Duck")


if __name__ == "__main__":
    main()
