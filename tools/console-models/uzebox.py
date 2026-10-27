"""The console theme's Uzebox system model (godot/themes/console/models/systems/uzebox.glb): the Uzebox V1.2 kit's board
and an SNES-style pad.

The Uzebox is open hardware with no case of its own, so its card is the board most Uzeboxes are: built in Blender from
the kit (uzebox_layout.py places every part from a photograph of it from above). The red board stands on four nylon
standoffs, printed with its silk screen and traces; on it stand its parts, each a simple solid: the SNES ports (their
stadium-shaped shrouds overhanging the front edge, the plug's socket cut into them), LED1, RESET and POWER, the 40-pin
microcontroller on its legs, the crystal, the video encoder, the regulator, the capacitors and resistors, the DC jack,
S-Video, the yellow and red RCA jacks, the blue ISP header, the SD card's socket and the EXT header's pins. The pad (an
unbranded SNES-style one) lies at the board's left: its dog-bone outline through a rounded profile, the D-pad, A B X Y, SELECT and
START, its shoulder buttons; its cable to SNES P1, the plug in the port. The printing is one texture drawn by
uzebox_print.py (the board from above; the SD card's label; the pad from above; swatches).

A node tree (card.finish()): the root holding the set; the set holding the SD card (waiting in its socket, shrunk to
nothing), POWER's and RESET's caps, LED1 lit (shrunk to nothing), and the pad's D-pad, A, B, X, Y and START.

The `focused` clip (8 s, looping) plays a game from the SD card: the card slides into its socket; POWER, and LED1 comes
on; START, then the D-pad and the buttons are played; RESET, POWER again and the light goes off; the card is pushed,
springs out and goes.

Four materials (case, metal, dark, cable) and one texture, within the system model budget. Run from the repo root:

    python tools/console-models/uzebox_print.py artifacts/uzebox
    blender -b --factory-startup --python tools/console-models/uzebox.py -- artifacts/uzebox godot/themes/console/models/systems/uzebox.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plugs  # noqa: E402
import uzebox_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe, tube  # noqa: E402
from saturn import inset, smooth_outline  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical
TILT_PITCH = 36.0    # degrees about the horizontal: the board tips up towards the viewer
ROUGHNESS = dict(case=0.45, metal=0.25, dark=0.5, cable=0.6)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
BOARD = ATLAS.uv("board", L.WIDTH, L.DEPTH)
P = L.PAD
PAD_FRAME = Matrix.Translation((*P["at"], 0.0)) @ Matrix.Rotation(math.radians(P["turn"]), 4, "Z")
PAD_UV = ATLAS.uv("pad", L.PAD_SPAN[1] - L.PAD_SPAN[0], L.PAD_SPAN[3] - L.PAD_SPAN[2])
T = L.TOP


def board_uv(co):
    return BOARD(co.x + L.HALF, L.DEPTH - co.y)


def pad_uv(co):
    return PAD_UV(co.x - L.PAD_SPAN[0], L.PAD_SPAN[3] - co.y)


def part_box(name, rect, mat, z0=T, m=None, swatch=None):
    x0, x1, y0, y1, h = rect
    part = box(name, x0, x1, y0, y1, z0, z0 + h, mat)
    if swatch:
        coloured(part, m["case"], ATLAS, swatch)
    return part


def _moved(obj, x, y):
    obj.data.transform(Matrix.Translation((x, y, 0.0)))
    return obj


# ---- The board -------------------------------------------------------------------------------------------------------

def board(m):
    part = box("board", -L.HALF, L.HALF, 0.0, L.DEPTH, L.STANDOFF["height"], T, m["case"])
    bevel(part, 0.3, segments=1)
    for x, y in L.STANDOFF["at"]:
        boolean(part, solid("hole", [[(x + 1.6 * math.cos(2 * math.pi * k / 12), y + 1.6 * math.sin(2 * math.pi * k / 12), z)
                                      for k in range(12)] for z in (0.0, T + 2.0)], m["dark"]))
    coloured(part, m["case"], ATLAS, "board")
    paint(part, m["case"], board_uv, lambda c, n, kind: n.z > 0.9 and kind == "case")
    parts = [part]
    r = L.STANDOFF["r"]
    for x, y in L.STANDOFF["at"]:
        stand = lathe("standoff", [(0.0, 0.0), (r, 0.0), (r, L.STANDOFF["height"]), (1.0, L.STANDOFF["height"]),
                                   (1.0, T + 1.2), (2.4, T + 1.2), (2.4, T + 2.4), (0.0, T + 2.4)], m["case"], 12)
        parts.append(coloured(_moved(stand, x, y), m["case"], ATLAS, "nylon"))
    return parts


def ports(m):
    """The SNES ports: a stadium-shaped shroud overhanging the front edge, the plug's socket cut into its face; the pin
    block behind it."""
    out = []
    y0, y1 = L.PORTS["y"]
    h = L.PORTS["height"]
    sw, sh, sd = L.PORTS["socket"]
    for x0, x1 in (L.PORTS["p1"], L.PORTS["p2"]):
        cx = (x0 + x1) / 2
        section = rounded(cx, T + h / 2, x1 - x0, h, h / 2 - 0.2, 6)
        shroud = solid("port", [[(x, y, z) for x, z in section] for y in (y0, y1 - 3.0)], m["dark"])
        socket = rounded(cx, T + h / 2, sw, sh, 3.0, 4)
        boolean(shroud, solid("socket", [[(x, y, z) for x, z in socket] for y in (y0 - 2.0, y0 + sd)], m["dark"]))
        out += [shroud, box("pins", x0 + 2.0, x1 - 2.0, y1 - 3.0, y1, T, T + 4.0, m["dark"])]
    return out


def chip(name, rect, legs, pitch, leg, m):
    """A chip: its black body, its legs along its long sides."""
    x0, x1, y0, y1, h = rect
    parts = [box(name, x0, x1, y0, y1, T + 0.8, T + h, m["dark"])]
    first = (x0 + x1) / 2 - pitch * (legs - 1) / 2
    for k in range(legs):
        x = first + pitch * k
        for y in (y0 - leg, y1):
            parts.append(box("leg", x - 0.25, x + 0.25, y, y + leg, T, T + h * 0.6, m["metal"]))
    return parts


def parts_on_board(m):
    out = ports(m)
    out += chip("mcu", L.MCU, 20, 2.54, 1.0, m)
    out += chip("encoder", L.ENCODER, 8, 1.27, 0.9, m)
    x0, x1, y0, y1, h = L.CRYSTAL
    crystal = solid("crystal", [[(x, y, z) for x, y in rounded((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0,
                                                               (y1 - y0) / 2 - 0.1, 5)] for z in (T, T + h)], m["metal"])
    out.append(crystal)
    out.append(part_box("regulator", L.REGULATOR["body"], m["dark"]))
    out.append(part_box("tab", L.REGULATOR["tab"], m["metal"]))
    out.append(part_box("dc", L.DC, m["dark"]))
    out.append(part_box("svideo", L.SVIDEO, m["metal"]))
    ry0, ry1 = L.RCA["y"]
    for name in ("video", "audio"):
        x0, x1, colour = L.RCA[name]
        housing = part_box("rca", (x0, x1, ry0, ry1, L.RCA["height"]), m["case"], m=m, swatch=colour)
        br, bl = L.RCA["barrel"]
        cx, cz = (x0 + x1) / 2, T + L.RCA["height"] / 2
        barrel = solid("barrel", [[(cx + br * math.cos(2 * math.pi * k / 16), y, cz + br * math.sin(2 * math.pi * k / 16))
                                   for k in range(16)] for y in (ry1 - 0.5, ry1 + bl)], m["metal"])
        out += [housing, barrel]
    isp = part_box("isp", L.ISP, m["case"], m=m, swatch="blue")
    x0, x1, y0, y1, h = L.ISP
    boolean(isp, box("well", x0 + 1.2, x1 - 1.2, y0 + 1.2, y1 - 1.2, T + 2.0, T + h + 2.0, m["dark"]))
    out.append(isp)
    sx0, sx1, sy0, sy1, sh = L.SD["socket"]
    out.append(part_box("socket", L.SD["socket"], m["metal"]))
    ex0, ex1 = L.EXT["x"]
    ey0, ey1 = L.EXT["y"]
    out.append(box("ext", ex0, ex1, ey0, ey1, T, T + L.EXT["height"], m["dark"]))
    for k in range(L.EXT["pins"]):
        y = ey0 + 1.3 + 2.54 * k
        for x in (ex0 + 1.3, ex1 - 1.3):
            out.append(coloured(box("pin", x - 0.32, x + 0.32, y - 0.32, y + 0.32, T, T + L.EXT["pin"], m["case"]),
                                m["case"], ATLAS, "gold"))
    for x, y, r, h in L.CAPS:
        can = lathe("cap", [(0.0, T), (r, T), (r, T + h - 0.6), (r - 0.4, T + h), (0.0, T + h)], m["dark"], 18)
        top = lathe("lid", [(0.0, T + h - 0.1), (r - 0.5, T + h - 0.1), (r - 0.5, T + h + 0.05), (0.0, T + h + 0.05)],
                    m["metal"], 18)
        out += [_moved(can, x, y), _moved(top, x, y)]
    for x, y, along_y in L.RESISTORS:
        rings = [(1.1 * math.cos(2 * math.pi * k / 8), 1.1 * math.sin(2 * math.pi * k / 8)) for k in range(8)]
        if along_y:
            res = solid("resistor", [[(x + a, y + d, T + 1.4 + b) for a, b in rings] for d in (-3.0, 3.0)], m["case"])
        else:
            res = solid("resistor", [[(x + d, y + a, T + 1.4 + b) for a, b in rings] for d in (-3.0, 3.0)], m["case"])
        out.append(coloured(res, m["case"], ATLAS, "blue"))
    for name in ("reset", "power"):
        x, y = L.BUTTONS[name]
        s = L.BUTTONS["size"] / 2
        out.append(box("switch", x - s, x + s, y - s, y + s, T, T + L.BUTTONS["height"], m["dark"]))
    lx, ly = L.LED["at"]
    led = lathe("led", led_profile(L.LED["r"]), m["case"], 18)
    out.append(coloured(_moved(led, lx, ly), m["case"], ATLAS, "green_off"))
    return out


def led_profile(r, grow=0.0):
    h = L.LED["height"]
    return ([(0.0, T), (r + 0.4 + grow, T + 0.2), (r + 0.4 + grow, T + 1.2), (r + grow, T + 1.2), (r + grow, T + h - r)]
            + [(r * math.cos(math.pi / 2 * k / 4) + grow, T + h - r + r * math.sin(math.pi / 2 * k / 4))
               for k in range(1, 5)] + [(0.0, T + h + grow)])


def caps_and_light(m):
    parts = {}
    for name in ("reset", "power"):
        x, y = L.BUTTONS[name]
        cap = lathe(name, [(0.0, -1.0), (L.BUTTONS["cap"], -1.0), (L.BUTTONS["cap"], 1.0), (0.0, 1.2)], m["case"], 14)
        parts[name] = (coloured(cap, m["case"], ATLAS, "white"), Vector((x, y, T + L.BUTTONS["height"])))
    lx, ly = L.LED["at"]
    lit = lathe("led_lit", led_profile(L.LED["r"], 0.12), m["case"], 18)
    lit.data.transform(Matrix.Translation((0.0, 0.0, -T)))
    parts["led"] = (coloured(lit, m["case"], ATLAS, "green"), Vector((lx, ly, T)))
    return parts


def sd_card(m):
    """The SD card, label up, its contacts' end towards the socket, its middle at its origin."""
    w, length, t = L.SD["card"]
    part = box("card", -w / 2, w / 2, -length / 2, length / 2, -t / 2, t / 2, m["case"])
    bevel(part, 0.4, segments=1)
    label = ATLAS.uv("card", w, length)
    coloured(part, m["case"], ATLAS, "sd")
    paint(part, m["case"], lambda co: label(co.x + w / 2, length / 2 - co.y), lambda c, n, kind: n.z > 0.9)
    return part


# ---- The pad ---------------------------------------------------------------------------------------------------------

def pad(m):
    outline = smooth_outline(P["points"])
    h = P["height"]
    profile = ((0.0, 4.5), (0.12, 1.6), (0.3, 0.0), (0.55, 0.4), (0.8, 2.2), (0.93, 4.2), (1.0, 6.0))
    body = solid("pad", [[(px, py, h * z) for px, py in (inset(outline, d) if d else outline)] for z, d in profile],
                 m["case"])
    coloured(body, m["case"], ATLAS, "pad")
    paint(body, m["case"], pad_uv, lambda c, n, kind: n.z > 0.85)
    parts = [body]
    sx, sy = P["shoulders"]
    for side in (-1, 1):
        shoulder = box("shoulder", side * sx - 13.0, side * sx + 13.0, sy, sy + 6.0, h * 0.35, h * 0.85, m["case"])
        bevel(shoulder, 1.6, segments=2)
        parts.append(coloured(shoulder, m["case"], ATLAS, "pad_dark"))
    parts.append(pill(m, P["select"], h))

    moving = {}
    dx, dy, arm, half = P["dpad"]
    cross = [(arm, -half), (arm, half), (half, half), (half, arm), (-half, arm), (-half, half), (-arm, half),
             (-arm, -half), (-half, -half), (-half, -arm), (half, -arm), (half, -half)]
    dpad = solid("dpad", [[(x, y, z) for x, y in (inset(cross, d) if d else cross)]
                          for z, d in ((-1.5, 0.0), (2.2, 0.0), (3.0, 0.5))], m["case"])
    moving["dpad"] = (coloured(dpad, m["case"], ATLAS, "black"), Vector((dx, dy, h - 1.0)))
    for name, (bx, by) in P["buttons"].items():
        r = P["button_r"]
        b = lathe(name, [(0.0, -1.5), (r, -1.5), (r, 1.4), (r * 0.82, 2.4), (0.0, 2.7)], m["case"], 20)
        moving["pad_" + name] = (coloured(b, m["case"], ATLAS, name), Vector((bx, by, h - 1.4)))
    start = pill(m, (0.0, 0.0), 0.0)
    moving["start"] = (start, Vector((*P["start"], h)))
    return join(parts, "pad"), moving


def pill(m, at, z):
    w, d = P["pill"]
    x, y = at
    outline = [(x + px * math.cos(math.radians(P["slant"])) - py * math.sin(math.radians(P["slant"])),
                y + px * math.sin(math.radians(P["slant"])) + py * math.cos(math.radians(P["slant"])))
               for px, py in rounded(0.0, 0.0, w, d, d / 2 - 0.01, 4)]
    part = solid("pill", [[(px, py, z + dz) for px, py in outline] for dz in (-1.0, 1.0)], m["case"])
    return coloured(part, m["case"], ATLAS, "pad_dark")


def cable(m):
    """The pad's cable from its top to SNES P1, its plug in the port's socket."""
    start = PAD_FRAME @ Vector((0.0, P["points"][0][1] - 1.0, P["height"] * 0.5))
    out = PAD_FRAME.to_3x3() @ Vector((0.0, 1.0, 0.0))
    pad_parts, pad_end, pad_dir = plugs.place(*plugs.grommet(lambda o: coloured(o, m["case"], ATLAS, "pad"), r=3.6),
                                              m["case"], start, out)
    sw, sh, sd = L.PORTS["socket"]
    body = plugs.along("plug", [(-sd + 0.5, plugs.rect(sw - 0.6, sh - 0.6, 2.8)), (0.0, plugs.rect(sw - 0.6, sh - 0.6, 2.8)),
                                (0.0, plugs.rect(sw + 2.0, sh + 3.0, 4.0)), (20.0, plugs.rect(sw, sh + 2.0, 4.0)),
                                (26.0, plugs.rect(12.0, 8.0, 3.5))], None)
    relief, end = plugs.ribbed("relief", 25.0, [(5.0, 3.6), (5.0, 3.0), (0.0, 2.6)], None)
    port = Vector((sum(L.PORTS["p1"]) / 2, L.PORTS["y"][0], T + L.PORTS["height"] / 2))
    con_parts, con_end, con_dir = plugs.place([(lambda o: coloured(o, m["case"], ATLAS, "plug"), body),
                                               (lambda o: coloured(o, m["case"], ATLAS, "plug"), relief)], end,
                                              m["case"], port, (0.0, -1.0, 0.0))
    path = [pad_end, pad_end + pad_dir * 10.0, Vector((-66.0, 30.0, 2.4)), Vector((-64.0, -24.0, 2.4)),
            Vector((-46.0, -52.0, 2.4)), con_end + con_dir * 12.0 + Vector((0.0, 0.0, -8.0)), con_end + con_dir * 4.0,
            con_end]
    wire = tube("cable", curve(path, 5), 2.0, m["cable"], 10)
    return pad_parts + con_parts + [smoothed(wire, 50.0)]


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 30.0                   # how far behind its seat the SD card waits: wholly out of its socket


def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def timeline(f):
    if f < 6 or f >= 228:
        card = Pose(scale=HIDDEN)
    elif f < 16:
        card = Pose(y=OUT, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 6, 15)))
    elif f < 200:
        card = Pose(y=OUT * (1 - smooth(phase(f, 16, 30))) - 1.6 * tap(f, 30, 1))
    elif f < 212:                                          # push, and it springs out
        card = Pose(y=-1.6 * smooth(phase(f, 200, 203)) + 13.6 * back_out(phase(f, 203, 210)) * (f >= 203))
    else:
        lift = ease_in(phase(f, 218, 228))
        card = Pose(y=12.0 + (OUT - 12.0) * smooth(phase(f, 212, 220)), z=24.0 * lift, scale=max(HIDDEN, 1 - lift))
    poses = {"sd_card": card, "power": Pose(z=-1.0 * max(tap(f, 40), tap(f, 190))), "reset": Pose(z=-1.0 * tap(f, 178)),
             "led": Pose() if (44 <= f < 192 and not 180 <= f < 184) else Pose(scale=HIDDEN),
             "start": Pose(z=-1.2 * tap(f, 58, 3))}
    t = phase(f, 70, 168)
    wave = math.sin(math.pi * t)
    poses["dpad"] = Pose(pitch=8.0 * math.sin(2 * math.pi * 4 * t) * wave, roll=8.0 * math.sin(2 * math.pi * 3 * t + 0.8)
                         * wave)
    for name, frames in (("pad_b", (78, 104, 136, 160)), ("pad_a", (90, 120, 150)), ("pad_y", (98, 128)),
                         ("pad_x", (112, 144))):
        poses[name] = Pose(z=-1.6 * max(tap(f, f0) for f0 in frames))
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    image = bpy.data.images.load(os.path.join(images, "uzebox_print.png"))
    m = materials(dict(case="#FFFFFF", metal=L.COLOURS["metal"], dark=L.COLOURS["black"], cable=L.COLOURS["cable"]),
                  ROUGHNESS, dict(case=image))

    controller, pad_moving = pad(m)
    controller.data.transform(PAD_FRAME)
    whole = smoothed(join(board(m) + parts_on_board(m) + [controller] + cable(m), "uzebox"), 40.0)
    sx0, sx1, sy0, sy1, sh = L.SD["socket"]
    w, length, t = L.SD["card"]
    seat = Vector(((sx0 + sx1) / 2, L.DEPTH + L.SD["out"] - length / 2, T + sh / 2))
    parts = {"sd_card": (smoothed(sd_card(m)), seat)}
    for name, (part, at) in caps_and_light(m).items():
        parts[name] = (smoothed(part, 50.0), at)
    turn = PAD_FRAME.to_3x3().to_4x4()
    for name, (part, at) in pad_moving.items():
        part.data.transform(turn)
        parts[name] = (smoothed(part, 50.0), PAD_FRAME @ at)
    finish("uzebox", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Uzebox")


if __name__ == "__main__":
    main()
