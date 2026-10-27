"""The console theme's SuperGrafx system model (godot/themes/console/models/systems/supergrafx.glb): NEC's PC Engine
SuperGrafx, a HuCard and its pad.

Built in Blender from the real console's proportions (supergrafx_layout.py has the measurements, taken from
photographs), in pc_engine.py's style: the wings' base, three pipes on each wing ending in their round caps, a block at
the back of each wing (POWER's green slider in the left one's well), the spine down the middle with its ribs, its bolts
and the HuCard's channel behind its strip (the slot running on under the strip, a finger notch at the channel's back),
and the rear block behind it, the expansion connector in its back; the pad's socket in the base's front. The pad and
the HuCard are pc_engine.py's own (the pad moved to lie in front of the SuperGrafx, the card turned to go in forwards),
their print where pc_engine_layout.py puts it; the pad's cable runs to the socket, a DIN plug on its end (plugs.din).
The printing is one texture drawn by supergrafx_print.py.

A node tree (card.finish()): the root holding the set; the set holding the HuCard (waiting over the channel, shrunk to
nothing), POWER, the lock tab and the pad's D-pad, II, I and RUN.

The `focused` clip (8 s, looping) plays a game: the HuCard (a made-up game) appears over the channel, turns once to show
its face, drops in and slides forwards under the strip; POWER slides on, pushing the green tab over the card's corner;
RUN, then the D-pad rocks and II and I are pressed in bursts; then POWER slides off, the tab draws back, and the card
slides out, rises and goes.

Five materials (case, pad, dark, print, cable) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/supergrafx_print.py artifacts/made-up-games artifacts/supergrafx
    blender -b --factory-startup --python tools/console-models/supergrafx.py -- artifacts/supergrafx godot/themes/console/models/systems/supergrafx.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc_engine  # noqa: E402
import pc_engine_layout as P  # noqa: E402
import plugs  # noqa: E402
import supergrafx_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, prism_x  # noqa: E402
from props import tube  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, pad=0.5, dark=0.6, print=0.5, cable=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
TOP = ATLAS.uv("top", L.WIDTH, L.DEPTH)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def prism(name, outline, z0, z1, mat):
    return solid(name, [[(x, y, z) for x, y in outline] for z in (z0, z1)], mat)


def disc(name, x, y, r, z0, z1, mat, n=24):
    return prism(name, [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n))
                        for k in range(n)], z0, z1, mat)


# ---- The console -----------------------------------------------------------------------------------------------------

def wings(m):
    """The base under the wings with the pad's socket, the pipes and their caps, the blocks at the back, POWER's
    well."""
    w = L.WINGS
    base = prism("wings", rounded(0.0, w["depth"] / 2, L.WIDTH, w["depth"], w["corner"], 3), 0.0, w["height"],
                 m["case"])
    bevel(base, 2.5, segments=2, angle=40)
    sx, sz, sr = L.SOCKET["x"], L.SOCKET["z"], L.SOCKET["r"]
    boolean(base, solid("socket", [[(sx + sr * math.cos(2 * math.pi * k / 20), y, sz + sr * math.sin(2 * math.pi * k / 20))
                                    for k in range(20)] for y in (-5.0, 8.0)], m["dark"]))
    parts = [base]
    r = L.RAILS
    for side in (-1, 1):
        for y in r["y"]:
            x0, x1 = sorted((side * r["x"][0], side * r["x"][1]))
            rail = box("rail", x0, x1, y - r["width"] / 2, y + r["width"] / 2, w["height"] - 1.0,
                       w["height"] + r["height"], m["case"])
            bevel(rail, 1.6, segments=2, angle=40)
            px, pr, ph = r["pad"]
            cap = disc("rail_cap", side * px, y, pr, w["height"] - 1.0, w["height"] + ph, m["case"])
            bevel(cap, 2.0, segments=2, angle=40)
            parts += [rail, cap]
    b = L.BLOCKS
    for side in (-1, 1):
        x0, x1 = sorted((side * b["x"][0], side * b["x"][1]))
        block = prism("block", rounded((x0 + x1) / 2, sum(b["y"]) / 2, x1 - x0, b["y"][1] - b["y"][0], 6.0, 3), 0.0,
                      b["height"], m["case"])
        bevel(block, 3.0, segments=2, angle=40)
        if side < 0:
            (px0, px1), (py0, py1) = L.POWER["x"], L.POWER["y"]
            boolean(block, box("well", px0 - 1.0, px1 + L.POWER["travel"] + 1.0, py0, py1, b["height"] - 3.0,
                               b["height"] + 5.0, m["dark"]))
        parts.append(block)
    return parts


def spine(m):
    """The spine with its ribs, bolts, the HuCard's channel, its notch and the slot under the strip; the rear block
    behind it."""
    s = L.SPINE
    body = box("spine", -s["x"], s["x"], s["y"][0], s["y"][1], 0.0, s["height"], m["case"])
    bevel(body, 3.0, segments=2, angle=40)
    r = L.RIBS
    grooves = []
    for side in (-1, 1):
        for k in range(r["count"]):
            x = side * (r["x"][0] + (r["x"][1] - r["x"][0]) * (k + 0.5) / r["count"])
            grooves.append(box("rib", x - r["width"] / 2, x + r["width"] / 2, r["y"][0], r["y"][1],
                               s["height"] - r["depth"], s["height"] + 5.0, m["case"]))
    boolean(body, join(grooves, "grooves"))
    c = L.CHANNEL
    boolean(body, box("channel", *c["x"], c["y"][0], c["y"][1], c["floor"], 80.0, m["case"]))
    n0, n1, nz = c["notch"]
    boolean(body, box("notch", c["x"][0] + 8.0, c["x"][1] - 8.0, n0 - 1.0, n1 + 1.0, nz, 80.0, m["case"]))
    sl = L.SLOT
    boolean(body, box("slot", *sl["x"], *sl["y"], *sl["z"], m["dark"]))
    (tx0, tx1), (ty0, ty1) = L.TAB["x"], L.TAB["y"]
    boolean(body, box("tab_well", tx0 - 1.0, tx1 + L.TAB["travel"] + 1.0, ty0 - 1.0, ty1 + 1.0, s["height"] - 2.0,
                      s["height"] + 5.0, m["dark"]))
    t = L.TOWER                                            # the rear block, cut on its own: the two touch face to face
    tower = prism_x("tower", [(t["y"][0], 0.0), (t["y"][1], 0.0), (t["y"][1], t["height"][1]),
                              (t["y"][0], t["height"][0])], *t["x"], m["case"])
    bevel(tower, 3.0, segments=2, angle=40)
    cn = L.CONNECTOR
    boolean(tower, box("connector", *cn["x"], t["y"][1] - 6.0, t["y"][1] + 5.0, *cn["z"], m["dark"]))
    bolts = [disc("bolt", x, y, L.SCREWS["r"], s["height"] - 1.0, s["height"] + 1.0, m["case"], 16)
             for x, y in L.SCREWS["at"]]
    return [body, tower] + bolts


def console(m):
    whole = join(wings(m) + spine(m), "supergrafx")
    coloured(whole, m["print"], ATLAS, "case")
    paint(whole, m["print"], top_uv, lambda c, n, name: n.z > 0.9)
    front = ATLAS.uv("front", L.WIDTH, L.WINGS["height"])
    paint(whole, m["print"], lambda co: front(co.x + L.WIDTH / 2, L.WINGS["height"] - co.z),
          lambda c, n, name: n.y < -0.9 and c.y < 0.3 and c.z < L.WINGS["height"] and abs(c.x) > L.SPINE["x"])
    paint(whole, m["print"], ATLAS.swatch("dark"), lambda c, n, name: name == "dark" and n.z < 0.9)
    return whole


def power_slider(m):
    """POWER, its middle at its origin, at OFF (the left of its well)."""
    (x0, x1), (y0, y1) = L.POWER["x"], L.POWER["y"]
    slider = box("power", -(x1 - x0) / 2, (x1 - x0) / 2, -(y1 - y0) / 2 + 1.0, (y1 - y0) / 2 - 1.0, -3.0, 2.0,
                 m["print"])
    grip = box("grip", -1.5, 1.5, -(y1 - y0) / 2 + 2.0, (y1 - y0) / 2 - 2.0, 1.5, 4.0, m["print"])
    part = join([slider, grip], "power")
    bevel(part, 0.5, segments=1)
    coloured(part, m["print"], ATLAS, "green")
    return part, Vector(((x0 + x1) / 2, (y0 + y1) / 2, L.BLOCKS["height"]))


def lock_tab(m):
    """The green tab that POWER pushes over the card's corner, its middle at its origin."""
    (x0, x1), (y0, y1) = L.TAB["x"], L.TAB["y"]
    tab = box("tab", -(x1 - x0) / 2, (x1 - x0) / 2, -(y1 - y0) / 2, (y1 - y0) / 2, -2.0, 1.2, m["print"])
    bevel(tab, 0.4, segments=1)
    coloured(tab, m["print"], ATLAS, "green")
    return tab, Vector(((x0 + x1) / 2, (y0 + y1) / 2, L.CHANNEL["floor"] + P.CARD["thickness"] + 0.8))


def hucard(m):
    """pc_engine.py's HuCard turned half round: its contacts' end forwards (into the slot under the strip), its face up
    (its print, turned half round to suit, reads from the front)."""
    card = pc_engine.hucard(m)
    card.data.transform(Matrix.Rotation(math.pi, 4, "Z"))
    return card


def pad_shift():
    return Matrix.Translation((L.PAD_AT[0] - P.PAD["at"][0], L.PAD_AT[1] - P.PAD["at"][1], 0.0))


def cable(m):
    """The pad's cable from its dome to the socket in the base's front, its DIN plug."""
    turn = Matrix.Rotation(math.radians(P.PAD["turn"]), 4, "Z")
    frame = Matrix.Translation((*L.PAD_AT, 0.0)) @ turn
    dome = P.PAD["dome"]
    start = frame @ Vector((0.0, dome["y"] + dome["r"] - 4.0, P.PAD["size"][2] + 1.0))
    out = turn.to_3x3() @ Vector((0.0, 1.0, 0.0))
    at = Vector((L.SOCKET["x"], 0.0, L.SOCKET["z"]))
    plug, end, direction = plugs.place(*plugs.din(lambda o: coloured(o, m["print"], ATLAS, "grey"),
                                                  lambda o: coloured(o, m["print"], ATLAS, "dark")), m["print"],
                                       at, (0.0, -1.0, 0.0))
    path = [start, start + out * 10.0 + Vector((0.0, 0.0, -6.0)), Vector((L.PAD_AT[0] + 30.0, -42.0, 2.8)),
            end + direction * 20.0 + Vector((0.0, 0.0, -7.0)), end + direction * 6.0, end]
    return plug + [smoothed(tube("cable", curve(path, 6), 2.5, m["cable"], 10), 50.0)]


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


PRESSES = dict(run=(72,), ii=(92, 98, 104, 130, 156), i=(112, 118, 124, 144, 150, 164))
ROCKS = [(80, 90, 0.0, 9.0), (108, 118, 0.0, -9.0), (134, 144, 9.0, 0.0), (158, 168, 0.0, 9.0)]


def timeline(f):
    back, drop = L.CARD["slide"], L.CARD["drop"]
    if f < 6 or f >= 214:
        card = Pose(y=back, z=drop, scale=HIDDEN)
    elif f < 14:
        card = Pose(y=back, z=drop, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 14)))
    elif f < 30:
        card = Pose(y=back, z=drop + 5.0 * math.sin(math.pi * phase(f, 14, 30)), spin=360.0 * smooth(phase(f, 14, 30)))
    elif f < 40:
        card = Pose(y=back, z=drop * (1 - ease_in(phase(f, 30, 40))))
    elif f < 186:
        card = Pose(y=back * (1 - smooth(phase(f, 42, 54))))
    elif f < 196:
        card = Pose(y=back * smooth(phase(f, 186, 196)))
    elif f < 206:
        card = Pose(y=back, z=drop * ease_out(phase(f, 196, 206)))
    else:
        card = Pose(y=back, z=drop, scale=max(HIDDEN, 1 - ease_in(phase(f, 206, 214))))
    on = smooth(phase(f, 58, 64)) * (1 - smooth(phase(f, 176, 182)))
    lock = smooth(phase(f, 61, 67)) * (1 - smooth(phase(f, 174, 180)))
    poses = {"hucard": card, "power": Pose(x=L.POWER["travel"] * on), "tab": Pose(x=L.TAB["travel"] * lock)}
    for name, frames in PRESSES.items():
        poses[name] = Pose(z=-1.8 * max(tap(f, f0) for f0 in frames))
    pitch = roll = 0.0
    for f0, f1, pa, ro in ROCKS:
        t = smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f1, f1 + 4)))
        pitch, roll = pitch + pa * t, roll + ro * t
    poses["dpad"] = Pose(pitch=pitch, roll=roll)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "supergrafx_print.png"))
    m = materials(dict(case=L.COLOURS["case"], pad=L.COLOURS["pad"], dark=L.COLOURS["dark"], print="#FFFFFF",
                       cable="#1C1C1F"), ROUGHNESS, dict(print=printed))

    pad_body = pc_engine.pad(m)
    for part in pad_body:
        part.data.transform(pad_shift())
    whole = smoothed(join([console(m)] + pad_body + cable(m), "supergrafx"), 40.0)
    slider, slider_at = power_slider(m)
    tab, tab_at = lock_tab(m)
    parts = {"hucard": (smoothed(hucard(m), 40.0), Vector(L.SEAT)), "power": (smoothed(slider, 40.0), slider_at),
             "tab": (smoothed(tab, 40.0), tab_at)}
    for name, part, where in pc_engine.pad_parts(m):
        parts[name] = (smoothed(part, 40.0), pad_shift() @ where)
    finish("supergrafx", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "SuperGrafx")


if __name__ == "__main__":
    main()
