"""The console theme's SuFami Turbo system model (godot/themes/console/models/systems/sufami.glb): Bandai's SuFami
Turbo standing in a Super Famicom's slot, two mini cartridges going into it.

Built in Blender, as sgb.py stands the Super Game Boy in the Super Nintendo. The console is snes.py's own Super Famicom
(its `sfc` kind), built by its functions; the adapter (sufami_layout.py has its measurements) is its plug, a cartridge's,
under its body, which widens as it rises, its sides leaning out, the two cradles cut into its top; its front printed. The
mini cartridges are boxes, their labels printed on their fronts, the grip's ribs across their tops. The printing is two
textures: snes_print.py's `sfc` (the console) and sufami_print.py's (the adapter's front, the labels), both drawn into
the same folder.

A node tree (card.finish()): the root holding the set (the console and the adapter in its slot); the set holding the two
mini cartridges (waiting over their cradles, shrunk to nothing), POWER's knob and the power light (shrunk to nothing
while it's off).

The `focused` clip (8 s, looping): cartridge A appears over the left cradle, turns once to show its label and drops in;
then B into the right one; POWER slides on and the light comes on; later POWER goes off, and the cartridges rise out and
go.

Six materials (the console's case, print, dark and cart; sufami, mini) and two textures, within the system model budget.
Run from the repo root:

    python tools/console-models/snes_print.py sfc artifacts/sufami
    python tools/console-models/sufami_print.py artifacts/made-up-games artifacts/sufami
    blender -b --factory-startup --python tools/console-models/sufami.py -- artifacts/sufami godot/themes/console/models/systems/sufami.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snes  # noqa: E402
import snes_layout as N  # noqa: E402
import sufami_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, finish, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, material  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 26.0    # degrees about the horizontal: the top tips up towards the viewer
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
FOOT = L.PLUG["height"]                    # the body's foot, over the plug
TOP = FOOT + L.BODY["height"]              # its top


def adapter(m):
    """The SuFami Turbo in its own frame (x across, z up from its plug's edge, its front facing -y): the plug, the body
    widening over it with the cradles cut into its top; its front printed."""
    p, b = L.PLUG, L.BODY
    plug = box("plug", -p["width"] / 2, p["width"] / 2, -p["thickness"] / 2, p["thickness"] / 2, 0.0, FOOT + 2.0,
               m["sufami"])
    bevel(plug, 1.0, segments=1, angle=40)
    (w0, d0), (w1, d1) = b["bottom"], b["top"]
    body = solid("sufami", [[(x, y, z) for x, y in rounded(0.0, 0.0, w, d, b["corner"], 4)]
                            for w, d, z in ((w0, d0, FOOT), (w1, d1, TOP))], m["sufami"])
    c = L.CRADLES
    for x in c["x"]:
        boolean(body, box("cradle", x - c["width"] / 2, x + c["width"] / 2, -c["depth"] / 2, c["depth"] / 2,
                          TOP - c["floor"], TOP + 5.0, m["sufami"]))
    dw, dd = L.DIP                                         # the top dipping between the cradles
    boolean(body, solid("dip", [[(x, y, z) for x, z in ((-dw / 2, TOP + 5.0), (-dw / 2 + 4.0, TOP - dd),
                                                         (dw / 2 - 4.0, TOP - dd), (dw / 2, TOP + 5.0))]
                                for y in (-40.0, 40.0)], m["sufami"]))
    bevel(body, 1.6, segments=2, angle=35)
    part = join([plug, body], "sufami")
    coloured(part, m["sufami"], ATLAS, "body")
    face = ATLAS.uv("front", w1, b["height"])
    paint(part, m["sufami"], lambda co: face(co.x + w1 / 2, TOP - co.z),
          lambda cc, n, name: n.y < -0.9 and cc.z > FOOT + 0.5)
    paint(part, m["sufami"], ATLAS.swatch("dark"),
          lambda cc, n, name: cc.z < TOP - 0.5 and abs(cc.y) < c["depth"] / 2 + 0.3 and n.z < 0.9
          and any(abs(cc.x - x) < c["width"] / 2 + 0.3 for x in c["x"]))
    return part


def mini(name, m):
    """A mini cartridge, its bottom's middle at its origin, its label facing -y: the shell, the grip's ribs across its
    top, the label."""
    k = L.MINI
    w, h, t = k["width"], k["height"], k["thickness"]
    shell = box("mini_" + name, -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["mini"])
    bevel(shell, 1.4, segments=2, angle=35)
    ribs = join([box("rib", -w / 2 + 6.0, w / 2 - 6.0, -t / 2 - 1.0, -t / 2 + 0.6, h - 3.0 - j * 1.6, h - 2.4 - j * 1.6,
                     m["mini"]) for j in range(3)], "ribs")
    boolean(shell, ribs)
    coloured(shell, m["mini"], ATLAS, "mini")
    paint(shell, m["mini"], ATLAS.swatch("grip"), lambda c, n, kind: c.z > h - 7.0 and n.y < -0.5)
    lw, lh, from_top = k["label"]
    z1 = h - from_top
    face = ATLAS.uv(name, lw, lh)
    paint(shell, m["mini"], lambda co: face(co.x + lw / 2, z1 - co.z),
          lambda c, n, kind: n.y < -0.9 and abs(c.x) < lw / 2 and z1 - lh < c.z < z1)
    return shell


# ---- The focused clip ------------------------------------------------------------------------------------------------

def dropping(f, f0):
    """A mini cartridge appearing at f0 over its cradle, turning once, dropping in; then rising out at 184 and going."""
    above = L.MINI["above"]
    if f < f0 or f >= 208:
        return Pose(z=above, scale=HIDDEN)
    if f < f0 + 8:
        return Pose(z=above, scale=max(HIDDEN, back_out(phase(f, f0, f0 + 7))))
    if f < f0 + 24:
        return Pose(z=above + 3.0 * math.sin(math.pi * phase(f, f0 + 8, f0 + 24)),
                    spin=360.0 * smooth(phase(f, f0 + 8, f0 + 24)))
    if f < f0 + 34:
        return Pose(z=above * (1 - ease_in(phase(f, f0 + 24, f0 + 34))))
    if f < 184:
        return Pose(z=1.4 * math.exp(-(f - f0 - 34) / 3.0) * abs(math.sin(math.pi * (f - f0 - 34) / 5.0)))
    if f < 198:
        return Pose(z=above * ease_out(phase(f, 184, 198)))
    return Pose(z=above, scale=max(HIDDEN, 1 - ease_in(phase(f, 198, 208))))


def timeline(f):
    on = smooth(phase(f, 86, 90)) * (1 - smooth(phase(f, 172, 176)))
    return {"mini_a": dropping(f, 6), "mini_b": dropping(f, 40), "power": Pose(y=N.POWER["travel"] * on),
            "power_light": Pose() if 90 <= f < 174 else Pose(scale=HIDDEN)}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    console_print = bpy.data.images.load(os.path.join(images, "sfc_print.png"))
    sufami_print = bpy.data.images.load(os.path.join(images, "sufami_print.png"))
    k = N.KINDS["sfc"]
    colours = dict(case=k["case"], print="#FFFFFF", dark=N.COLOURS["dark"], cart=N.COLOURS["cart"])
    m = {n: material(n, colours[n], r, console_print if n == "print" else None) for n, r in snes.ROUGHNESS.items()}
    m["sufami"] = material("sufami", "#FFFFFF", 0.55, sufami_print)
    m["mini"] = material("mini", "#FFFFFF", 0.5, sufami_print)

    seat = Vector((0.0, sum(N.SLOT["y"]) / 2, N.TOP + N.PANEL["height"] - L.PLUG["inserted"]))
    unit = adapter(m)
    unit.data.transform(Matrix.Translation(seat))
    whole = smoothed(join([snes.body(m), snes.eject(m), unit], "sufami"))
    slide = smoothed(snes.knob(m))
    lit, lit_at = snes.light(m)
    parts = {"power": (slide, Vector()), "power_light": (lit, lit_at)}
    for name, x in zip(("a", "b"), L.CRADLES["x"]):
        parts["mini_" + name] = (smoothed(mini(name, m)), seat + Vector((x, 0.0, TOP - L.MINI["seat"])))
    finish("sufami", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "SuFami Turbo")


if __name__ == "__main__":
    main()
