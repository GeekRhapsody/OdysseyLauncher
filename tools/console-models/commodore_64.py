"""The console theme's Commodore 64 system model (godot/themes/console/models/systems/c64.glb): a C64, the breadbin, a
Commodore 1541 disk drive beside its right end and a Commodore 1702 colour monitor behind it, the C64's start-up screen
on the monitor's glass.

Built in Blender from the real machines' measurements (commodore_64_layout.py has them, from Commodore's figures and
photographs). The breadbin is its side outline across its width, its wells cut into the deck, the recess in its right
end (the control ports, the power switch, the socket) and the cartridge and user ports in its back; its 66 keys stand in
their wells, each tapering to its top with its front sloping, as a Commodore keycap's does, its legends on its top and
its front (the PETSCII graphics, the colours' names), the four function keys in their own well; the power light on the
deck. The 1541 is its side outline across its width, rounded over at the front, the drive's brown bezel standing proud
of its front, the slot cut through both, the lever (its knob and its handle) and the red drive light. The 1702 is a box,
its dark bezel sunk into its front and the opening's walls sloping back to the curved glass, the power button standing
out of the strip under it, its feet, the tube's housing tapering behind. The printing is two textures drawn by
commodore_64_print.py (the computer from above, the keys' fronts, its right end and its sides' strip; the drive's front,
top and sides' strip, the floppy's two sides, the monitor's lower front and top) and the glass's still. The seams round
the computer's and the drive's bases are printed on those strips rather than cut: a groove a millimetre high breaks up
into dashes on screen.

The glass's material is `video`: while the card is focused (in the systems grid and on the system's details), the
launcher plays the theme's video for it there (godot/themes/console/videos/c64.mp4, drawn by commodore_64_video.py),
starting it again each time the clip loops (A6 Card videos); otherwise, and where there's no decoder, it shows its own
texture, the start-up screen.

A node tree (card.finish()): the root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the drive's end
towards the viewer, the top tipped up; then the model spec's fit) holding the set; the set holding the floppy (waiting
in the drive, shrunk to nothing), the drive's lever and its lit light (shrunk to nothing), the computer's power switch
and its lit power light, and the keys the clip presses.

The `focused` clip (10 s, looping; its timing is commodore_64_layout.py's, which the video follows frame for frame)
loads a game from disk: a floppy (a made-up game, Deep Fathom) appears in front of the drive tipped to show its label,
levels at the slot and slides in, and the lever turns down; LOAD"*",8,1 is typed, each key going down as its character
appears (SHIFT with 2 for the quotes), and RETURN; SEARCHING FOR *, the drive's light on, LOADING, then the loader
fills the screen with the game's picture a character cell at a time while the border flickers; f1 starts the game, the
space bar fires its torpedoes. Then the lever turns up, the floppy pops out and goes, and the switch goes off and on
again: the screen goes dark and comes back to the start-up screen.

Five materials (print, devices, key, dark, video; the case's colours come from the prints) and three textures, within
the system model budget. Run from the repo root:

    python tools/console-models/commodore_64_print.py artifacts/made-up-games artifacts/c64
    python tools/console-models/commodore_64_video.py artifacts/made-up-games godot/themes/console/videos/c64.mp4
    blender -b --factory-startup --python tools/console-models/commodore_64.py -- artifacts/c64 godot/themes/console/models/systems/c64.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commodore_64_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from card import finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, prism_x  # noqa: E402

TILT_YAW = -24.0     # degrees about the vertical: the drive's end comes towards the viewer
TILT_PITCH = 22.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.55, print=0.5, devices=0.5, key=0.5, dark=0.6, video=0.2)

# The deck's frame: x across, s up the slope from its front edge, h off it.
DECK = Matrix.Translation((0.0, *L.DECK_FRONT)) @ Matrix.Rotation(L.SLOPE, 4, "X")
PRESS = DECK.to_3x3() @ Vector((0.0, 0.0, -1.0))           # a key's travel, in the model's frame
PRESSED = ("l", "o", "a", "d", "lshift", "d2", "star", "comma", "d8", "d1", "return", "f1", "space")


def atlas_uv(rect, w, h):
    """A face drawn w x h (millimetres) into rect: (a, b) millimetres across it (a to the right, b down from its top)
    to UVs."""
    rx, ry, rw, rh = rect
    return lambda a, b: ((rx + a / w * rw) / L.ATLAS, 1 - (ry + b / h * rh) / L.ATLAS)


def swatch(where):
    x, y = where
    return lambda co: (x / L.ATLAS, 1 - y / L.ATLAS)


TOP = atlas_uv(L.REGIONS["top"], L.WIDTH, L.DEPTH)
SIDE = atlas_uv(L.REGIONS["side"], L.DEPTH, L.HEIGHT)


def top_uv(co):
    return TOP(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def seam_uv(rect, height):
    """A side's strip (its colour up its height, the seam's line in it): a point by its height alone."""
    x, y, w, h = rect
    return lambda co: ((x + w / 2) / L.ATLAS, 1 - (y + (height - co.z) / height * h) / L.ATLAS)


def on_deck(name, outline, h0, h1, mat):
    return solid(name, [[DECK @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def painted(obj, mat, where):
    """Every face of obj in mat, at a swatch."""
    paint(obj, mat, swatch(where), lambda c, n, name: True)
    return obj


# ---- The C64 ---------------------------------------------------------------------------------------------------------

def computer(m):
    """The breadbin: its outline across its width, the wells, the recess in its right end and the ports in its back
    cut; its top and its right end printed, and its other sides, the seam's line round them."""
    w = L.WIDTH
    body = prism_x("c64", L.profile(), -w / 2, w / 2, m["case"])
    bevel(body, 2.0, segments=2)
    boolean(body, join([on_deck("well", outline, -L.WELL, 16.0, m["dark"]) for outline in L.wells()], "wells"))
    r = L.RECESS
    boolean(body, box("recess", w / 2 - r["depth"], w / 2 + 5.0, *r["y"], *r["z"], m["dark"]))
    for p in (L.CART_PORT, L.USER_PORT):
        boolean(body, box("port", *p["x"], L.DEPTH - p["depth"], L.DEPTH + 5.0, *p["z"], m["dark"]))
    paint(body, m["print"], top_uv, lambda c, n, name: n.z > 0.5 and name == "case")
    floor = w / 2 - r["depth"]
    paint(body, m["print"], lambda co: SIDE(co.y, L.HEIGHT - co.z),
          lambda c, n, name: n.x > 0.9 and (name == "case" or abs(c.x - floor) < 0.2))
    paint(body, m["print"], seam_uv(L.REGIONS["seam"], L.HEIGHT), lambda c, n, name: name == "case")
    return body


def front_uv(cell, x0, x1):
    """A key's front, seen square on in the deck's frame: (x, h) to its cell, which spans its base's width and from
    the well's floor to its top."""
    cx, cy, cw, ch = cell
    span = L.KEY_HEIGHT + L.WELL
    return lambda co: ((cx + (co.x - x0) / (x1 - x0) * cw) / L.ATLAS,
                       1 - (cy + (L.KEY_HEIGHT - co.z) / span * ch) / L.ATLAS)


def key_solid(name, rect, m, cell, fkey=False):
    """A key in its well: straight up from the well's floor, then tapering to its top, its front sloping back further;
    its front printed (in the deck's frame), then its top (in the model's)."""
    x0, s0, x1, s1 = rect
    i, f, h = L.KEY_INSET, L.KEY_FRONT, L.KEY_HEIGHT

    def ring(side, front, back, z):
        return [(x0 + side, s0 + front, z), (x1 - side, s0 + front, z), (x1 - side, s1 - back, z),
                (x0 + side, s1 - back, z)]
    cap = solid(name, [ring(0.0, 0.0, 0.0, -L.WELL - 0.5), ring(0.3, 0.6, 0.3, 2.0), ring(i, f, i, h)], m["key"])
    bevel(cap, 0.7, segments=1, angle=30)
    if fkey:
        painted(cap, m["print"], L.SWATCHES["fkey"])
    if cell is not None:
        paint(cap, m["print"], front_uv(cell, x0, x1), lambda c, n, kind: n.y < -0.45 and n.z < 0.9)
    cap.data.transform(DECK)
    paint(cap, m["print"], top_uv, lambda c, n, kind: n.z > 0.9)
    return cap


def keys(m):
    """The keys in their wells: the ones the clip presses apart."""
    cells = L.front_cells()
    static, moving = [], {}
    made = [(name, L.key_rect(xu, row, wu), False) for name, xu, row, wu, _, _ in L.KEYS]
    made += [(name, L.fkey_rect(row), True) for name, row, _, _ in L.FKEYS]
    for name, rect, fkey in made:
        cap = key_solid("key_" + name, rect, m, cells.get(name), fkey)
        if name in PRESSED:
            moving["key_" + name] = cap
        else:
            static.append(cap)
    return static, moving


def power_light(m):
    """The power light lit: a dome over the printed one, its middle at its origin."""
    y, z = L.deck_point(L.POWER["light"][1], 0.0)
    r = L.POWER["r"]
    part = solid("power_light", [[(r * k * math.cos(2 * math.pi * i / 12), r * k * math.sin(2 * math.pi * i / 12), dz)
                                  for i in range(12)] for k, dz in ((1.0, -0.6), (1.0, 0.5), (0.5, 1.1))], m["print"])
    part.data.transform(Matrix.Rotation(L.SLOPE, 4, "X"))
    painted(part, m["print"], L.SWATCHES["lit"])
    return part, Vector((L.POWER["light"][0], y, z))


def rocker(m):
    """The power switch's rocker, standing out of the recess's floor, its middle at its origin (it rocks about y)."""
    (y0, y1), (z0, z1), out = L.PORTS["switch"], L.SWITCH["z"], L.SWITCH["out"]
    x = L.WIDTH / 2 - L.RECESS["depth"]
    part = box("rocker", x - 1.0, x + out, y0, y1, z0, z1, m["dark"])
    bevel(part, 0.6, segments=1)
    middle = Vector((x, (y0 + y1) / 2, (z0 + z1) / 2))
    part.data.transform(Matrix.Translation(-middle))
    return part, middle


# ---- The 1541 --------------------------------------------------------------------------------------------------------

D = L.DRIVE
DX0 = D["x0"]
DFRONT = atlas_uv(L.DEVICE_REGIONS["drive_front"], D["width"], D["height"])
DTOP = atlas_uv(L.DEVICE_REGIONS["drive_top"], D["width"], D["depth"])


def drive_front_uv(co):
    return DFRONT(co.x - DX0, D["height"] - co.z)


def drive(m):
    """The drive's shell: its outline across its width (the top rounded over at the front, the back's edge rounded a
    little) and the slot; its front and top printed, and its other sides, the seam's line round them."""
    h, d = D["height"], D["depth"]
    rb, rd = D["round"]
    front = [(rb * (1 - math.cos(math.radians(a))), h - rd * (1 - math.sin(math.radians(a))))
             for a in range(90, -1, -10)]
    back = [(d - 6.0 + 6.0 * math.sin(math.radians(a)), h - 6.0 + 6.0 * math.cos(math.radians(a)))
            for a in range(0, 91, 30)]
    profile = [(2.0, 0.0), (d - 2.0, 0.0), (d, 2.0)] + list(reversed(back)) + front + [(0.0, 2.0)]
    shell = prism_x("drive", profile, DX0, DX0 + D["width"], m["case"])
    bevel(shell, 1.5, segments=2)
    (s0, s1), (z0, z1) = L.SLOT["x"], L.SLOT["z"]
    boolean(shell, box("slot", DX0 + s0, DX0 + s1, -5.0, L.SLOT["depth"], z0, z1, m["dark"]))
    paint(shell, m["devices"], drive_front_uv, lambda c, n, name: n.y < -0.9 and name == "case")
    paint(shell, m["devices"], lambda co: DTOP(co.x - DX0, d - co.y), lambda c, n, name: n.z > 0.9 and name == "case")
    paint(shell, m["devices"], seam_uv(L.DEVICE_REGIONS["drive_seam"], h), lambda c, n, name: name == "case")
    return shell


def bezel(m):
    """The drive's bezel standing proud of its front, the slot cut through it; its face printed."""
    (x0, x1), (z0, z1), out = L.BEZEL["x"], L.BEZEL["z"], L.BEZEL["out"]
    part = box("bezel", DX0 + x0, DX0 + x1, -out, 1.0, z0, z1, m["devices"])
    bevel(part, 0.8, segments=2)
    (s0, s1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    boolean(part, box("slot", DX0 + s0, DX0 + s1, -5.0, 3.0, sz0, sz1, m["dark"]))
    painted(part, m["devices"], L.DEVICE_SWATCHES["bezel"])
    paint(part, m["devices"], drive_front_uv, lambda c, n, name: n.y < -0.9 and name == "devices")
    return part


def lever(m):
    """The lever, its pivot at its origin: the knob standing out of the bezel, the handle across its front, along the
    slot (open)."""
    r, out = L.LEVER["knob"], L.LEVER["out"]
    length, width, thick = L.LEVER["handle"]
    face = -L.BEZEL["out"]
    ring = [(r * math.cos(2 * math.pi * k / 16), r * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    knob = solid("knob", [[(x, y, z) for x, z in ring] for y in (face + 1.0, face - out)], m["devices"])
    bevel(knob, 0.8, segments=2, angle=50)
    painted(knob, m["devices"], L.DEVICE_SWATCHES["knob"])
    handle = box("handle", -1.0, length, face - out, face - out + thick, -width / 2, width / 2, m["devices"])
    bevel(handle, 0.9, segments=2)
    painted(handle, m["devices"], L.DEVICE_SWATCHES["handle"])
    part = join([knob, handle], "lever")
    part.data.transform(Matrix.Translation((0.0, -face, 0.0)))
    return part, Vector((DX0 + L.LEVER["x"], face, L.LEVER["z"]))


def drive_light(m):
    w, h = L.DRIVE_LIGHT["size"]
    part = box("drive_light", -w / 2, w / 2, -0.35, 0.2, -h / 2, h / 2, m["devices"])
    painted(part, m["devices"], L.DEVICE_SWATCHES["lit"])
    return part, Vector((DX0 + L.DRIVE_LIGHT["x"], -L.BEZEL["out"], L.DRIVE_LIGHT["z"]))


def floppy(m):
    """The 5.25-inch floppy, its middle at its origin, lying flat, its leading edge towards +y (into the drive), its
    label up at its trailing edge."""
    s, t = L.DISK["size"], L.DISK["thickness"]
    part = box("disk", -s / 2, s / 2, -s / 2, s / 2, -t / 2, t / 2, m["devices"])
    bevel(part, 0.35, segments=1)
    painted(part, m["devices"], L.DEVICE_SWATCHES["disk"])
    top = atlas_uv(L.DEVICE_REGIONS["floppy"], s, s)
    under = atlas_uv(L.DEVICE_REGIONS["floppy_under"], s, s)
    paint(part, m["devices"], lambda co: top(co.x + s / 2, s / 2 - co.y), lambda c, n, name: n.z > 0.9)
    paint(part, m["devices"], lambda co: under(s / 2 - co.x, s / 2 - co.y), lambda c, n, name: n.z < -0.9)
    return part


# ---- The 1702 --------------------------------------------------------------------------------------------------------

M = L.MONITOR


def monitor(m):
    """The 1702: its box, the bezel sunk into its front, the opening's walls sloping back to the glass, the power
    button, its feet and the tube's housing; its lower front and its top printed."""
    ax, ay = M["at"]
    w, h, d, feet = M["width"], M["height"], M["depth"], M["feet"]
    body = box("monitor", ax - w / 2, ax + w / 2, ay, ay + d, feet, h, m["case"])
    bevel(body, 3.0, segments=2)
    painted(body, m["devices"], L.DEVICE_SWATCHES["monitor"])
    b, o, g = M["bezel"], M["opening"], M["glass"]
    recess = box("recess", ax - b["x"], ax + b["x"], ay - 5.0, ay + b["recess"], *b["z"], m["dark"])
    boolean(body, recess)
    gw, gh = g["size"]
    oz = (o["z"][0] + o["z"][1]) / 2
    outer = rounded(ax, oz, 2 * o["x"], o["z"][1] - o["z"][0], o["r"], 5)
    edge = rounded(ax, g["z"], gw - 2.0, gh - 2.0, 10.0, 5)
    behind = rounded(ax, g["z"], gw - 30.0, gh - 30.0, 8.0, 5)
    face = ay + b["recess"]
    cutter = solid("opening", [[(x, face - 5.0, z) for x, z in outer], [(x, face, z) for x, z in outer],
                               [(x, face + g["back"], z) for x, z in edge],
                               [(x, face + g["back"] + 14.0, z) for x, z in behind]], m["dark"])
    boolean(body, cutter)
    left, top_z = ax - w / 2, 62.0
    lower = atlas_uv(L.DEVICE_REGIONS["monitor_front"], w, top_z)
    paint(body, m["devices"], lambda co: lower(co.x - left, top_z - co.z),
          lambda c, n, name: n.y < -0.9 and c.z < top_z and name == "devices")
    upper = atlas_uv(L.DEVICE_REGIONS["monitor_top"], w, d)
    paint(body, m["devices"], lambda co: upper(co.x - left, ay + d - co.y),
          lambda c, n, name: n.z > 0.9 and name == "devices")

    bt = M["button"]
    button = box("button", ax + bt["x"][0], ax + bt["x"][1], ay - bt["out"], ay + 1.0, *bt["z"], m["devices"])
    bevel(button, 0.7, segments=2)
    painted(button, m["devices"], L.DEVICE_SWATCHES["handle"])
    r = M["rear"]
    (fw, fh), (ew, eh) = r["size"], r["end"]
    mid = feet + (h - feet) * 0.52
    housing = solid("housing", [[(ax + x, y, z) for x, z in rounded(0.0, cz, cw, ch, cr, 4)]
                                for y, cz, cw, ch, cr in ((ay + d - 2.0, mid, fw, fh, 14.0),
                                                          (ay + d + r["depth"], mid + 10.0, ew, eh, 18.0))],
                    m["devices"])
    bevel(housing, 3.0, segments=2, angle=50)
    painted(housing, m["devices"], L.DEVICE_SWATCHES["rear"])
    pads = [box("foot", ax + fx - 14.0, ax + fx + 14.0, ay + fy - 10.0, ay + fy + 10.0, 0.0, feet + 1.0, m["dark"])
            for fx in (34.0 - w / 2, w / 2 - 34.0) for fy in (30.0, d - 30.0)]
    glass = curved("glass", gw, gh, g["bulge"], lambda a, bb: (a, 1 - bb), m["video"], 20, 15)
    glass.data.transform(Matrix.Translation((ax, face + g["back"], g["z"])))
    return [body, button, housing, glass] + pads


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    """A press at f0: down in three frames, held, back up in four."""
    return smooth(phase(f, f0, f0 + 3)) * (1 - smooth(phase(f, f0 + 3 + hold, f0 + 7 + hold)))


def presses():
    """The frames each key the clip presses goes down at: LOAD"*",8,1 typed, RETURN, f1, the space bar's shots."""
    typed = {"L": "l", "O": "o", "A": "a", "D": "d", '"': "d2", "*": "star", ",": "comma", "8": "d8", "1": "d1"}
    out = {}
    for k, ch in enumerate(L.COMMAND):
        out.setdefault(typed[ch], []).append(L.TYPED + k * L.PER_KEY)
    out["return"] = [L.RETURN]
    out["f1"] = [L.F1]
    out["space"] = list(L.FIRE)
    return out


PRESSES = presses()
SHIFTED = [L.TYPED + k * L.PER_KEY for k, ch in enumerate(L.COMMAND) if ch == '"']
OUT_Y, LIFT, TIP = 128.0, 58.0, 40.0       # where the floppy appears: in front of its seat, above it, tipped up
MOUTH = L.DISK["size"] + L.DISK["behind"] + L.BEZEL["out"] + 2.0   # its leading edge just outside the slot
POP = 45.0                                  # how far the spring pushes it out when the lever opens


def disk_pose(f):
    a, b, c, d, e = L.DISK_IN
    o0, o1, o2, o3 = L.DISK_OUT
    if f < a or f >= o3:
        return Pose(scale=HIDDEN)                              # in its seat, so the rest pose's bounds are the set's
    if f < b:
        return Pose(y=-OUT_Y, z=LIFT, pitch=TIP, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, a, b), 1.4))
    if f < c:
        return Pose(y=-OUT_Y, z=LIFT + 2.0 * math.sin(math.pi * phase(f, b, c)), pitch=TIP)
    if f < d:
        t = smooth(phase(f, c, d))
        return Pose(y=-OUT_Y + (OUT_Y - MOUTH) * t, z=LIFT * (1 - t), pitch=TIP * (1 - t))
    if f < e:
        return Pose(y=-MOUTH * (1 - smooth(phase(f, d, e))))
    if f < o0:
        return Pose(y=1.5 * math.sin(math.pi * phase(f, e, e + 4)))    # pushed home, and settles
    if f < o1:
        return Pose(y=-POP * back_out(phase(f, o0, o1), 1.6))
    if f < o2:
        t = smooth(phase(f, o1, o2))
        return Pose(y=-POP - (OUT_Y - POP) * t, z=LIFT * t, pitch=TIP * t)
    t = phase(f, o2, o3)
    return Pose(y=-OUT_Y, z=LIFT + 12.0 * ease_out(t), pitch=TIP, scale=max(HIDDEN, 1 - ease_in(t)))


def switched_on(f):
    """1 while the computer is on, 0 while it's off; the rocker takes two frames each way."""
    return 1 - smooth(phase(f, L.POWER_OFF, L.POWER_OFF + 2)) * (1 - smooth(phase(f, L.POWER_ON, L.POWER_ON + 2)))


def timeline(f):
    shut = back_out(phase(f, *L.LEVER_SHUT), 1.6) * (1 - smooth(phase(f, *L.LEVER_OPEN)))
    on = switched_on(f)
    reading = L.DRIVE_ON[0] <= f < L.DRIVE_ON[1] and f % 11 != 5
    poses = {"disk": disk_pose(f), "lever": Pose(roll=90.0 * shut),
             "drive_light": Pose() if reading else Pose(scale=HIDDEN),
             "power_light": Pose() if on > 0.5 else Pose(scale=HIDDEN),
             "rocker": Pose(roll=L.SWITCH["rock"] * (2 * on - 1))}
    for name, frames in PRESSES.items():
        d = L.PRESS * max(tap(f, f0) for f0 in frames)
        poses["key_" + name] = Pose(x=PRESS.x * d, y=PRESS.y * d, z=PRESS.z * d)
    held = max(smooth(phase(f, f0 - 3, f0)) * (1 - smooth(phase(f, f0 + 5, f0 + 8))) for f0 in SHIFTED)
    poses["key_lshift"] = Pose(x=PRESS.x * L.PRESS * held, y=PRESS.y * L.PRESS * held, z=PRESS.z * L.PRESS * held)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    load = lambda name: bpy.data.images.load(os.path.join(images, name))   # noqa: E731
    m = materials(dict(case=L.COLOURS["case"], print="#FFFFFF", devices="#FFFFFF", key=L.COLOURS["key"],
                       dark=L.COLOURS["dark"], video="#FFFFFF"), ROUGHNESS,
                  dict(print=load("c64_print.png"), devices=load("c64_devices.png"), video=load("c64_screen.png")))

    static, moving = keys(m)
    whole = smoothed(join([computer(m), drive(m), bezel(m)] + static + monitor(m), "c64"), 35.0)
    for part in moving.values():
        smoothed(part, 35.0)
    lit, lit_at = power_light(m)
    switch, switch_at = rocker(m)
    handle, pivot = lever(m)
    light, light_at = drive_light(m)
    s = L.DISK["size"]
    seat = Vector((DX0 + sum(L.SLOT["x"]) / 2, L.DISK["behind"] + s / 2, sum(L.SLOT["z"]) / 2))
    parts = {"disk": (smoothed(floppy(m), 40.0), seat), "lever": (smoothed(handle, 40.0), pivot),
             "drive_light": (light, light_at), "power_light": (lit, lit_at), "rocker": (smoothed(switch), switch_at)}
    parts.update({name: (obj, Vector()) for name, obj in moving.items()})
    finish("c64", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Commodore 64")


if __name__ == "__main__":
    main()
