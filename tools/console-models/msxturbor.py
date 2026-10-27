"""The console theme's MSX turbo R system model (godot/themes/console/models/systems/msxturbor.glb): Panasonic's FS-A1GT.

Built in Blender from the real machine's proportions (msxturbor_layout.py has the measurements, taken from photographs),
in msx2.py's manner. The case is its side outline extruded across its width, cut for the keys' wells, the grooves along
its back edge, the drive's slot in its right end and the joystick ports; the glossy black band is a strip of its own on
its slope, a little proud of it and past its ends; slot 1's lid stands a little proud of the rear block's top. The keys
stand in the wells (the JIS layout), tapering to their printed tops, light grey or mid grey as the real ones; RETURN is
an inverted L, and the cursor keys four wedges round a square. The printing is one texture drawn by msxturbor_print.py:
the top seen from above (planar-mapped onto every face facing up: the key tops and legends, the badge and sticker, the
rear block's printing), the band along its slope (A1GT, the controls' names, the lights), the 3.5-inch disk (a made-up
game), and swatches.

A node tree (card.finish()): the root holding the set; the set holding the disk (waiting in the drive, shrunk to
nothing), the eject button, RESET and the autofire rate slider's knob on the band, the R800 and FDD IN USE lights (shrunk
to nothing) and the keys the clip presses.

The `focused` clip (8 s, looping) plays a game from a disk: the disk slides into the drive in the right end and FDD IN
USE flickers while it loads; the R800 light comes on with the game (the turbo R's fast processor), the cursor keys and
the space bar are played and the autofire slider is pushed up to fast and back. Then RESET, the R800 light goes off,
the eject button goes in and the disk pops out and goes.

Five materials (case, band, key_light, key_dark, black) and one texture, within the system model budget. Run from the
repo root:

    python tools/console-models/msxturbor_print.py artifacts/made-up-games artifacts/msxturbor
    blender -b --factory-startup --python tools/console-models/msxturbor.py -- artifacts/msxturbor godot/themes/console/models/systems/msxturbor.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msxturbor_layout as L  # noqa: E402
from amiga import paint, solid  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, prism_x  # noqa: E402

TILT_YAW = -25.0     # degrees about the vertical: the right end (the drive) comes towards the viewer
TILT_PITCH = 30.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, band=0.2, key_light=0.5, key_dark=0.5, black=0.4)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
TOP = ATLAS.uv("top", L.WIDTH, L.DEPTH)
BAND_UV = ATLAS.uv("band", L.WIDTH, L.BAND_LENGTH)
RIGHT = L.HALF

# The deck's frame: x across, s up the slope from the deck's front edge, h off it; the band's, b up it from its foot.
SLOPE_FRAME = Matrix.Translation((0.0, *L.DECK[0])) @ Matrix.Rotation(L.SLOPE, 4, "X")
BAND_FRAME = Matrix.Translation((0.0, *L.BAND[0])) @ Matrix.Rotation(L.BAND_SLOPE, 4, "X")
PRESS = SLOPE_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))   # a key's travel, in the model's frame
BAND_IN = BAND_FRAME.to_3x3() @ Vector((0.0, 0.0, -1.0))  # RESET's
BAND_NORMAL = -BAND_IN


# ---- UVs -------------------------------------------------------------------------------------------------------------

def top_uv(co):
    """The top seen from above."""
    return TOP(co.x + L.HALF, L.DEPTH - co.y)


def band_uv(co):
    """The band along its slope: b up it from its foot."""
    b = (co.y - L.BAND[0][0]) * math.cos(L.BAND_SLOPE) + (co.z - L.BAND[0][1]) * math.sin(L.BAND_SLOPE)
    return BAND_UV(co.x + L.HALF, L.BAND_LENGTH - b)


# ---- Geometry --------------------------------------------------------------------------------------------------------

def on_slope(name, outline, h0, h1, mat):
    """A solid from an (x, s) outline on the deck, from h0 to h1 off it."""
    return solid(name, [[SLOPE_FRAME @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def on_band(name, x0, x1, b0, b1, h0, h1, mat):
    """A block on the band: x0..x1 across it, b0..b1 up it, h0..h1 off its slope."""
    corners = ((x0, b0), (x1, b0), (x1, b1), (x0, b1))
    return solid(name, [[BAND_FRAME @ Vector((x, b, h)) for x, b in corners] for h in (h0, h1)], mat)


def case(m):
    """The case: its outline across its width, cut for the wells (black), the grooves along its back edge, the drive's
    slot and the joystick ports (black); its top printed, the rest its grey."""
    shell = prism_x("msxturbor", L.PROFILE, -L.HALF, L.HALF, m["case"])
    bevel(shell, 2.5, segments=2)
    boolean(shell, join([on_slope("well", outline, -L.WELL, 14.0, m["black"]) for outline in L.wells()], "wells"))
    f = L.FINS
    step = L.WIDTH / f["count"]
    boolean(shell, join([box("groove", -L.HALF + (k + 0.5) * step - f["width"] / 2,
                             -L.HALF + (k + 0.5) * step + f["width"] / 2, *f["y"], L.HEIGHT - f["depth"],
                             L.HEIGHT + 5.0, m["case"]) for k in range(f["count"])], "grooves"))
    (y0, y1), (z0, z1) = L.DRIVE_SLOT["y"], L.DRIVE_SLOT["z"]
    holes = [box("slot", RIGHT - 60.0, RIGHT + 5.0, y0, y1, z0, z1, m["black"])]
    holes += [box("port", RIGHT - 4.0, RIGHT + 5.0, *p["y"], *p["z"], m["black"]) for p in L.PORTS]
    boolean(shell, join(holes, "holes"))
    paint(shell, m["case"], ATLAS.swatch("case"), lambda c, n, name: name == "case")
    paint(shell, m["case"], top_uv, lambda c, n, name: name == "case" and n.z > 0.9)
    return shell


def band(m):
    """The black band: a strip on the slope, BAND_PROUD off it and BAND_PAST past each end; its face printed."""
    t, x = L.BAND_PROUD, L.HALF + L.BAND_PAST
    part = on_band("band", -x, x, 0.0, L.BAND_LENGTH, -0.5, t, m["band"])
    bevel(part, 0.5, segments=1)
    coloured(part, m["band"], ATLAS, "band")
    paint(part, m["band"], band_uv, lambda c, n, name: n.dot(BAND_NORMAL) > 0.95)
    return part


def lid(m):
    """Slot 1's lid, a little proud of the rear block's top."""
    (x0, x1), (y0, y1) = L.LID["x"], L.LID["y"]
    part = box("lid", x0, x1, y0, y1, L.HEIGHT - 0.5, L.HEIGHT + L.LID["thickness"], m["case"])
    bevel(part, 0.6, segments=1)
    coloured(part, m["case"], ATLAS, "case")
    paint(part, m["case"], top_uv, lambda c, n, name: n.z > 0.9)
    return part


def key_solid(name, outline, height, mat, m):
    """A key: from the well's floor up its sides, tapering to its printed top, height off the deck."""
    rings = [[(x, s, -L.WELL - 0.5) for x, s in outline], [(x, s, height - 4.5) for x, s in outline],
             [(x, s, height) for x, s in L.inset(outline, L.KEY_INSET)]]
    cap = solid(name, rings, mat)
    bevel(cap, 0.6, segments=1, angle=30)
    cap.data.transform(SLOPE_FRAME)
    paint(cap, m["case"], top_uv, lambda c, n, _name: n.z > 0.95)
    return cap


def keys(m):
    """The keys, standing in their wells: the cursor keys and the space bar apart (the clip plays them); the square in
    the cursor keys' middle."""
    static, moving = [], {}
    for text, xu, row, wu, colour in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        cap = key_solid("key", [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], L.KEY_HEIGHT, m["key_" + colour], m)
        if text == "SPACE":
            moving["space"] = cap
        else:
            static.append(cap)
    static.append(key_solid("return", L.return_outline(), L.KEY_HEIGHT, m["key_dark"], m))
    for name in ("up", "down", "left", "right"):
        moving[name] = key_solid(name, L.cursor_outline(name), L.CURSOR["height"], m["key_dark"], m)
    mx, ms = L.cursor_middle()
    iw, idp = L.CURSOR["inner"]
    square = L.inset([(mx - iw / 2, ms - idp / 2), (mx + iw / 2, ms - idp / 2), (mx + iw / 2, ms + idp / 2),
                      (mx - iw / 2, ms + idp / 2)], 0.6)
    plug = on_slope("plug", square, -L.WELL - 0.5, L.CURSOR["height"] - 2.0, m["case"])
    bevel(plug, 0.6, segments=1)
    static.append(coloured(plug, m["case"], ATLAS, "case"))
    return static, moving


def band_parts(m):
    """The autofire rate slider's knob (at its left end, off) and RESET, standing out of the band, in the model's
    frame."""
    (sx0, _), (sb0, sb1) = L.SLIDER["x"], L.SLIDER["b"]
    knob = on_band("knob", sx0 + 1.0, sx0 + 1.0 + L.SLIDER["knob"], sb0 + 0.8, sb1 - 0.8, 1.0, L.BAND_PROUD + 2.2,
                   m["key_dark"])
    bevel(knob, 0.5, segments=1)
    (rx0, rx1), (rb0, rb1) = L.RESET["x"], L.RESET["b"]
    reset = on_band("reset", rx0, rx1, rb0, rb1, 1.0, L.BAND_PROUD + L.RESET["height"], m["key_light"])
    bevel(reset, 0.5, segments=1)
    return {"knob": (smoothed(knob), Vector()), "reset": (smoothed(reset), Vector())}


def lights(m):
    """The lit R800 and FDD IN USE lights, each a glow just over its printed light, its middle at its origin."""
    parts = {}
    w, d = L.LIGHTS["size"]
    b = L.LIGHTS["b"]
    for name, k in (("r800_light", 4), ("fdd_light", 5)):
        x = L.LIGHTS["x"][k] + L.LIGHTS["at"]
        lit = on_band(name, x - w / 2 - 0.2, x + w / 2 + 0.2, b - d / 2 - 0.2, b + d / 2 + 0.2, L.BAND_PROUD + 0.05,
                      L.BAND_PROUD + 0.35, m["band"])
        coloured(lit, m["band"], ATLAS, "red")
        middle = BAND_FRAME @ Vector((x, b, L.BAND_PROUD + 0.2))
        lit.data.transform(Matrix.Translation(-middle))
        parts[name] = (lit, middle)
    return parts


def eject_button(m):
    (y0, y1), (z0, z1) = L.EJECT["y"], L.EJECT["z"]
    part = box("eject", RIGHT - 1.0, RIGHT + L.EJECT["out"], y0, y1, z0, z1, m["key_dark"])
    bevel(part, 0.5, segments=1)
    return part


def disk(m):
    """The 3.5-inch disk, its middle at its origin, lying flat, its shutter's end towards -x (into the drive)."""
    (w, length), t = L.DISK["size"], L.DISK["thickness"]
    part = box("disk", -length / 2, length / 2, -w / 2, w / 2, -t / 2, t / 2, m["case"])
    bevel(part, 0.6, segments=1)
    top = ATLAS.uv("disk_top", w, length)
    bottom = ATLAS.uv("disk_bottom", w, length)
    paint(part, m["case"], lambda co: top(co.y + w / 2, co.x + length / 2), lambda c, n, name: n.z > 0.9)
    paint(part, m["case"], lambda co: bottom(w / 2 - co.y, co.x + length / 2), lambda c, n, name: n.z < -0.9)
    paint(part, m["case"], ATLAS.swatch("black"), lambda c, n, name: abs(n.z) <= 0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

OUT = 100.0          # how far right of its seat the disk waits: wholly out of the drive
TRAVEL = L.SLIDER["x"][1] - L.SLIDER["x"][0] - L.SLIDER["knob"] - 2.0   # the knob's, from off to fast


def appear(f, f0, f1):
    return HIDDEN + (1 - HIDDEN) * back_out(phase(f, f0, f1)) if f >= f0 else HIDDEN


def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


PLAY = dict(right=(96, 104), up=(114,), left=(130, 138), down=(148,), space=(156, 164))


def timeline(f):
    # The disk: appears beside the drive, slides in; later pops out, is pulled clear and goes.
    if f < 6 or f >= 226:
        dsk = Pose(scale=HIDDEN)
    elif f < 16:
        dsk = Pose(x=OUT, scale=appear(f, 6, 14))
    elif f < 198:
        dsk = Pose(x=OUT * (1 - smooth(phase(f, 16, 30))))
    elif f < 210:
        dsk = Pose(x=34.0 * back_out(phase(f, 198, 204)))
    else:
        lift = ease_in(phase(f, 216, 226))
        dsk = Pose(x=34.0 + 66.0 * smooth(phase(f, 210, 218)), z=30.0 * lift, scale=max(HIDDEN, 1 - lift))

    reading = 32 <= f < 84 and (f // 3) % 4 != 3
    push = smooth(phase(f, 192, 195)) * (1 - smooth(phase(f, 198, 202)))
    reset = 1.2 * tap(f, 180, 3)
    rate = smooth(phase(f, 120, 128)) * (1 - smooth(phase(f, 170, 178)))
    poses = {"disk": dsk, "eject": Pose(x=-1.4 * push), "knob": Pose(x=TRAVEL * rate),
             "reset": Pose(x=BAND_IN.x * reset, y=BAND_IN.y * reset, z=BAND_IN.z * reset),
             "fdd_light": Pose() if reading else Pose(scale=HIDDEN),
             "r800_light": Pose() if 88 <= f < 183 else Pose(scale=HIDDEN)}
    for name, frames in PLAY.items():
        d = 2.8 * max(tap(f, f0) for f0 in frames)
        poses[name] = Pose(x=PRESS.x * d, y=PRESS.y * d, z=PRESS.z * d)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "msxturbor_print.png"))
    m = materials({n: L.COLOURS[n] for n in ROUGHNESS}, ROUGHNESS, dict(case=printed, band=printed))

    static, moving = keys(m)
    whole = smoothed(join([case(m), band(m), lid(m)] + static, "msxturbor"), 35.0)
    parts = {name: (smoothed(part), Vector()) for name, part in moving.items()}
    parts.update(band_parts(m))
    parts.update(lights(m))
    parts["eject"] = (smoothed(eject_button(m)), Vector())
    parts["disk"] = (smoothed(disk(m)), Vector(L.SEAT))
    finish("msxturbor", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "MSX turbo R")


if __name__ == "__main__":
    main()
