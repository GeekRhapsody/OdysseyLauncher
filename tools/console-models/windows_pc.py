"""The console theme's Windows system model (godot/themes/console/models/systems/windows.glb): a gaming PC of the 2020s,
its monitor, keyboard and mouse.

Windows has no hardware of its own, so its card is the PC a game is played on now (windows_pc_layout.py has the
measurements): a black mid-tower left of a 27-inch monitor, a full-size mechanical keyboard in front of it and a gaming
mouse on the desk mat to its right.

The tower is a shell open at its left side (its glass panel isn't drawn: the launcher draws no transparency), its front
a frame round three 120 mm fans, on four feet. Inside, through the open side: the motherboard on the right panel, the
power supply's shroud along the floor, the graphics card across the case, its long lit side to the glass and its
backplate up, a tower cooler on the socket with its fan on the fins' front face, four lit memory sticks in front of it,
the front fans' backs and the exhaust fan in the back wall. Each fan is a frame (its lit ring printed round its hole)
and a rotor (its hub and lit blades printed on both faces) that spins. The monitor is a thin panel, its glass the
`video` material, its housing behind, on a column and a flat base. The keyboard is a wedge, its 104 keys floating over
the plate, each tapering to its top, the legends lit in a rainbow across the board and a glow round each switch on the
plate. The mouse is lofted from its outline, its top printed. The mat is a thin slab, its top printed, its edge lit.
The printing is three textures drawn by windows_pc_print.py: the tower's (`windows_case.png`), the desk's
(`windows_desk.png`) and the glass's still (`windows_screen.png`).

The glass's material is `video`: while the card is focused, the launcher plays the theme's video for it there
(godot/themes/console/videos/windows.mp4, drawn by windows_pc_video.py), starting it again each time the clip loops
(A6 Card videos); otherwise, and where there's no decoder, it shows its own texture, the desktop.

A node tree (card.finish()): the root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the left side
towards the viewer, so the tower's open side and its front both show; then the model spec's fit) holding the set; the
set holding the five fans' rotors, the mouse and the keys the clip presses.

The `focused` clip (12 s, looping; its timing is windows_pc_layout.py's, which the video follows frame for frame):
the fans spin all the while, whole turns in a loop; the mouse moves as the screen's pointer does (the pointer's path
scaled down to the mat, along the mouse's own axes) and dips at each click: the game's icon double-clicked, Continue
on its title, two spear thrusts, Quit to Desktop. W goes down and stays down while the hero runs, Shift while she
sprints, A and D as she steps aside, E as she takes the spoils, Esc for the pause menu.

Three materials (case, desk, video) and three textures, within the system model budget. Run from the repo root:

    python tools/console-models/windows_pc_print.py artifacts/made-up-games artifacts/windows-pc
    blender -b --factory-startup --python tools/console-models/windows_pc.py -- artifacts/windows-pc godot/themes/console/models/systems/windows.glb
    python tools/console-models/windows_pc_video.py artifacts/made-up-games godot/themes/console/videos/windows.mp4
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windows_pc_layout as L  # noqa: E402
from amiga import paint, rounded, solid  # noqa: E402
from card import Atlas, finish, materials, smoothed  # noqa: E402
from clip import Pose, phase, smooth  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, new_object, prism_x  # noqa: E402
from pointer_path import mouse_offset  # noqa: E402

TILT_YAW = 22.0      # degrees about the vertical: the left side (the tower) comes towards the viewer
TILT_PITCH = 15.0    # degrees about the horizontal: the top tips up towards the viewer
ROUGHNESS = dict(case=0.45, desk=0.55, video=0.5)

CASE = Atlas(L.CASE_ATLAS, L.CASE_REGIONS, L.CASE_SWATCH_AT)
DESK = Atlas(L.DESK_ATLAS, L.DESK_REGIONS, L.DESK_SWATCH_AT)


def swatched(obj, mat, atlas, name, keep=None):
    """obj's faces keep accepts (all, without keep) in mat, at the atlas's swatch name."""
    paint(obj, mat, atlas.swatch(name), keep or (lambda c, n, kind: True))
    return obj


# ---- The tower, in its own frame: x across from its open left side, y back from its front, z up from its feet -----

T = L.TOWER
TW, TD, TH, FEET, WALL = T["width"], T["depth"], T["height"], T["feet"], T["wall"]
TOP = FEET + TH


def tower_frame():
    """The tower's frame in the set's: turned about its middle, standing at TOWER["at"]."""
    ax, ay = T["at"]
    return (Matrix.Translation((ax, ay, 0.0)) @ Matrix.Rotation(math.radians(T["turn"]), 4, "Z")
            @ Matrix.Translation((-TW / 2, -TD / 2, 0.0)))


def shell(m):
    """The case: a box hollowed to its walls, open at its left side but for the glass's frame, the fans' opening in
    its front; its front, top and back printed, its other faces black."""
    body = box("tower", 0.0, TW, 0.0, TD, FEET, TOP, m["case"])
    bevel(body, 3.0, segments=2)
    swatched(body, m["case"], CASE, "case")
    # A cutter's faces come over with its UVs: the walls it leaves take its swatch.
    hollow = box("hollow", WALL, TW - WALL, WALL, TD - WALL, FEET + WALL, TOP - WALL, m["case"])
    boolean(body, swatched(hollow, m["case"], CASE, "inside"))
    g = T["glass"]
    boolean(body, swatched(box("glass", -5.0, WALL + 1.0, g, TD - g, FEET + g, TOP - g, m["case"]), m["case"], CASE,
                           "case"))
    o = L.FRONT_OPENING
    opening = box("opening", o["margin"], TW - o["margin"], -5.0, WALL + 1.0, FEET + o["z"][0], FEET + o["z"][1],
                  m["case"])
    boolean(body, swatched(opening, m["case"], CASE, "case"))
    front = CASE.uv("front", TW, TH)
    paint(body, m["case"], lambda co: front(co.x, TOP - co.z), lambda c, n, kind: n.y < -0.9 and c.y < 1.0)
    top = CASE.uv("top", TW, TD)
    paint(body, m["case"], lambda co: top(co.x, TD - co.y), lambda c, n, kind: n.z > 0.9 and c.z > TOP - 1.0)
    back = CASE.uv("back", TW, TH)
    paint(body, m["case"], lambda co: back(TW - co.x, TOP - co.z), lambda c, n, kind: n.y > 0.9 and c.y > TD - 1.0)
    swatched(body, m["case"], CASE, "inside",
             lambda c, n, kind: WALL - 0.5 < c.x < TW - WALL + 0.5 and WALL - 0.5 < c.y < TD - WALL + 0.5
             and FEET + WALL - 0.5 < c.z < TOP - WALL + 0.5)
    feet = [box("foot", x - 16.0, x + 16.0, y - 24.0, y + 24.0, 0.0, FEET + 1.0, m["case"])
            for x in (30.0, TW - 30.0) for y in (40.0, TD - 40.0)]
    for foot in feet:
        bevel(foot, 2.0, segments=2)
        swatched(foot, m["case"], CASE, "dark")
    return [body] + feet


def inside(m):
    """The parts seen through the open side: the motherboard, the shroud, the graphics card, the cooler's fins, the
    memory; each its face to the glass printed (and the card's backplate), the rest in its colour."""
    parts = []
    b = L.BOARD
    board = box("board", b["x"], TW - WALL, *b["y"], FEET + b["z"][0], FEET + b["z"][1], m["case"])
    swatched(board, m["case"], CASE, "pcb")
    face = CASE.uv("board", b["y"][1] - b["y"][0], b["z"][1] - b["z"][0])
    paint(board, m["case"], lambda co: face(b["y"][1] - co.y, FEET + b["z"][1] - co.z), lambda c, n, kind: n.x < -0.9)
    parts.append(board)

    s0 = L.SHROUD["y"]
    shroud = box("shroud", WALL, TW - WALL, s0, TD - WALL, FEET + WALL, FEET + L.SHROUD["z"], m["case"])
    bevel(shroud, 1.5, segments=1)
    swatched(shroud, m["case"], CASE, "shroud")
    side = CASE.uv("shroud", TD - WALL - s0, L.SHROUD["z"] - WALL)
    paint(shroud, m["case"], lambda co: side(TD - WALL - co.y, FEET + L.SHROUD["z"] - co.z),
          lambda c, n, kind: n.x < -0.9)
    parts.append(shroud)

    g = L.GPU
    gpu = box("gpu", *g["x"], *g["y"], FEET + g["z"][0], FEET + g["z"][1], m["case"])
    bevel(gpu, 1.2, segments=1)
    swatched(gpu, m["case"], CASE, "dark")
    gl, gh, gw = g["y"][1] - g["y"][0], g["z"][1] - g["z"][0], g["x"][1] - g["x"][0]
    gside = CASE.uv("gpu", gl, gh)
    paint(gpu, m["case"], lambda co: gside(g["y"][1] - co.y, FEET + g["z"][1] - co.z), lambda c, n, kind: n.x < -0.9)
    gtop = CASE.uv("gpu_top", gl, gw)
    paint(gpu, m["case"], lambda co: gtop(g["y"][1] - co.y, co.x - g["x"][0]), lambda c, n, kind: n.z > 0.9)
    parts.append(gpu)

    c = L.COOLER
    fins = box("fins", *c["x"], *c["y"], FEET + c["z"][0], FEET + c["z"][1], m["case"])
    bevel(fins, 1.0, segments=1)
    swatched(fins, m["case"], CASE, "fins")
    fl, fh = c["y"][1] - c["y"][0], c["z"][1] - c["z"][0]
    fend = CASE.uv("fins", fl, fh)
    paint(fins, m["case"], lambda co: fend(c["y"][1] - co.y, FEET + c["z"][1] - co.z), lambda c_, n, kind: n.x < -0.9)
    parts.append(fins)

    # The memory: each stick standing out of the board, its edge to the glass its light bar.
    r = L.RAM
    gap = (r["y"][1] - r["y"][0]) / r["sticks"]
    stick = CASE.uv("ram", gap * 0.7, r["z"][1] - r["z"][0])
    for k in range(r["sticks"]):
        y0 = r["y"][0] + k * gap
        ram = box("ram", *r["x"], y0, y0 + gap * 0.7, FEET + r["z"][0], FEET + r["z"][1], m["case"])
        swatched(ram, m["case"], CASE, "ram")
        paint(ram, m["case"], lambda co, y0=y0: stick(y0 + gap * 0.7 - co.y, FEET + r["z"][1] - co.z),
              lambda c_, n, kind: n.x < -0.9)
        parts.append(ram)
    return parts


def fan_frame(m, name):
    """A fan's frame, its middle at the origin, its face towards -y: a square with its round hole, its faces printed
    (the lit ring round the hole), its edges and the hole's walls dark."""
    s, d, hole = L.FAN["size"], L.FAN["depth"], L.FAN["hole"]
    frame = box(name, -s / 2, s / 2, -d / 2, d / 2, -s / 2, s / 2, m["case"])
    bevel(frame, 2.0, segments=1)
    swatched(frame, m["case"], CASE, "dark")
    cutter = solid("hole", [[(hole * math.cos(2 * math.pi * k / 32), y, hole * math.sin(2 * math.pi * k / 32))
                             for k in range(32)] for y in (-d, d)], m["case"])
    boolean(frame, cutter)
    swatched(frame, m["case"], CASE, "dark")
    face = CASE.uv("fan", s, s)
    paint(frame, m["case"], lambda co: face(co.x + s / 2, s / 2 - co.z), lambda c, n, kind: n.y < -0.9)
    paint(frame, m["case"], lambda co: face(s / 2 - co.x, s / 2 - co.z), lambda c, n, kind: n.y > 0.9)
    return frame


def rotor(m, name):
    """A fan's rotor, its middle at the origin, turning about y: a thin disc, its hub and lit blades printed on both
    faces (each as seen from its own side)."""
    r = L.FAN["rotor"]
    disc = solid(name, [[(r * math.cos(2 * math.pi * k / 28), y, r * math.sin(2 * math.pi * k / 28))
                         for k in range(28)] for y in (-1.2, 1.2)], m["case"])
    swatched(disc, m["case"], CASE, "dark")
    face = CASE.uv("blades", 2 * r, 2 * r)
    paint(disc, m["case"], lambda co: face(co.x + r, r - co.z), lambda c, n, kind: n.y < -0.9)
    paint(disc, m["case"], lambda co: face(r - co.x, r - co.z), lambda c, n, kind: n.y > 0.9)
    return disc


def fans(m):
    """Every fan in the tower's frame: [(frame, rotor, middle, turns)], each frame placed, each rotor at its middle."""
    out = []
    d = L.FAN["depth"]
    places = [((TW / 2, L.FRONT_FAN_Y + d / 2, FEET + z), 0.0, L.FAN_TURNS["front"], f"fan_front{k + 1}")
              for k, z in enumerate(L.FRONT_FANS)]
    rear = (L.REAR_FAN["x"], TD - WALL - d / 2, FEET + L.REAR_FAN["z"])
    places.append((rear, 180.0, L.FAN_TURNS["rear"], "fan_rear"))
    c = L.COOLER_FAN
    places.append(((c["x"], c["y"], FEET + c["z"]), 0.0, L.FAN_TURNS["cooler"], "fan_cooler"))
    for middle, facing, turns, name in places:
        frame = fan_frame(m, name + "_frame")
        spinner = rotor(m, name)
        turn = Matrix.Rotation(math.radians(facing), 4, "Z")
        frame.data.transform(Matrix.Translation(middle) @ turn)
        spinner.data.transform(turn)
        out.append((frame, spinner, Vector(middle), turns, facing))
    return out


def back_vent(m):
    """The exhaust fan's hole in the back wall, its walls dark."""
    hole = L.FAN["hole"]
    x, z = L.REAR_FAN["x"], FEET + L.REAR_FAN["z"]
    vent = solid("vent", [[(x + hole * math.cos(2 * math.pi * k / 32), y, z + hole * math.sin(2 * math.pi * k / 32))
                           for k in range(32)] for y in (TD - WALL - 2.0, TD + 5.0)], m["case"])
    return swatched(vent, m["case"], CASE, "dark")


# ---- The monitor -----------------------------------------------------------------------------------------------------

M = L.MONITOR


def monitor(m):
    """The panel (its bezel black, its chin printed), the glass, the housing behind it, the column and the base."""
    w, h, t, b = M["width"], M["height"], M["thick"], M["bottom"]
    panel = box("panel", -w / 2, w / 2, 0.0, t, b, b + h, m["desk"])
    bevel(panel, 2.5, segments=2)
    swatched(panel, m["desk"], DESK, "black")
    swatched(panel, m["desk"], DESK, "bezel", lambda c, n, kind: n.y < -0.9)
    # The chin's printing (a quad just proud of the panel, as the glass is).
    cw_, ch_ = w - 6.0, M["chin"] - 2.0
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    corners = [(-cw_ / 2, b + 1.0), (cw_ / 2, b + 1.0), (cw_ / 2, b + 1.0 + ch_), (-cw_ / 2, b + 1.0 + ch_)]
    face = bm.faces.new([bm.verts.new((x, -0.2, z)) for x, z in corners])
    chin = DESK.uv("chin", cw_, ch_)
    for loop, (x, z) in zip(face.loops, corners):
        loop[uv].uv = chin(x + cw_ / 2, b + 1.0 + ch_ - z)
    face.normal_update()
    if face.normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=[face])
    chin_face = new_object("chin", bm, m["desk"])
    hw, hh, hd = M["housing"]
    mid = b + h * 0.5
    housing = solid("housing", [[(x, y, z) for x, z in rounded(0.0, mid, ww, zh, rr, 5)]
                                for y, ww, zh, rr in ((t - 1.0, hw, hh, 24.0), (t + hd, hw - 70.0, hh - 60.0, 30.0))],
                    m["desk"])
    swatched(housing, m["desk"], DESK, "black")
    back = DESK.uv("back", hw, hh)
    paint(housing, m["desk"], lambda co: back(hw / 2 - co.x, mid + hh / 2 - co.z), lambda c, n, kind: n.y > 0.9)
    cw, cd = M["column"]
    cy = M["column_y"]
    column = box("column", -cw / 2, cw / 2, cy - cd / 2, cy + cd / 2, M["base"][2] - 1.0, b + h * 0.42, m["desk"])
    bevel(column, 4.0, segments=2)
    swatched(column, m["desk"], DESK, "stand")
    bw, bd, bt = M["base"]
    base = solid("base", [[(x, y, z) for x, y in rounded(0.0, M["base_y"], bww, bdd, rr, 6)]
                          for bww, bdd, rr, z in ((bw - 6.0, bd - 6.0, 30.0, 0.0), (bw, bd, 34.0, 3.0),
                                                  (bw - 10.0, bd - 10.0, 28.0, bt))], m["desk"])
    swatched(base, m["desk"], DESK, "stand")
    gw, gh = L.SCREEN_MM
    z0 = b + M["chin"]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    corners = [(-gw / 2, z0), (gw / 2, z0), (gw / 2, z0 + gh), (-gw / 2, z0 + gh)]
    face = bm.faces.new([bm.verts.new((x, -0.4, z)) for x, z in corners])     # wound to face -y, the viewer
    for loop, (x, z) in zip(face.loops, corners):
        loop[uv].uv = ((x + gw / 2) / gw, (z - z0) / gh)
    face.normal_update()
    if face.normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=[face])
    glass = new_object("glass", bm, m["video"])
    return [panel, chin_face, housing, column, base, glass]


# ---- The keyboard, in its deck's frame: x from its left edge, s up the plate from its front, h off the plate ---------

K = L.KEYBOARD
KX0 = K["at"][0] - K["width"] / 2
SLOPE = math.atan2(K["back"] - K["front"], K["depth"])
DECK = Matrix.Translation((KX0, K["at"][1], K["front"])) @ Matrix.Rotation(SLOPE, 4, "X")
DOWN = DECK.to_3x3() @ Vector((0.0, 0.0, -1.0))
KEYS_UV = DESK.uv("keys", K["width"], K["depth"])


def keys_uv(co):
    """A point on the deck (in the deck's frame) to the keys' region: seen from above, the back edge at the top."""
    return KEYS_UV(co.x, K["depth"] - co.y)


def keyboard_case(m):
    """The wedge, its top the plate, printed (the glow round each switch), its sides black."""
    body = prism_x("keyboard", [(0.0, 0.0), (K["depth"], 0.0), (K["depth"], K["back"]), (0.0, K["front"])],
                   KX0, KX0 + K["width"], m["desk"])
    bevel(body, 2.5, segments=2)
    swatched(body, m["desk"], DESK, "black")
    to_deck = DECK.inverted()
    paint(body, m["desk"], lambda co: keys_uv(to_deck @ co),
          lambda c, n, kind: (DECK.to_3x3().inverted() @ n).z > 0.99 and (to_deck @ c).z > -0.3)
    return body


def keycap(name, rect, m):
    """A key floating over the plate: from its base (lift above the plate) tapering to its top, its sides black and
    its top printed with its legend."""
    x0, y0, x1, y1 = rect
    cap = K["cap"]
    tw, td = cap["top"]
    lift, height = cap["lift"], cap["height"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    iw = (x1 - x0 - (cap["base"] - tw))
    idp = (y1 - y0 - (cap["base"] - td))
    ring = lambda w, d, h, dy=0.0: [(cx - w / 2, cy - d / 2 + dy, h), (cx + w / 2, cy - d / 2 + dy, h),  # noqa: E731
                                    (cx + w / 2, cy + d / 2 + dy, h), (cx - w / 2, cy + d / 2 + dy, h)]
    body = solid(name, [ring(x1 - x0, y1 - y0, lift), ring(x1 - x0 - 0.6, y1 - y0 - 0.6, lift + 1.6),
                        ring(iw, idp, lift + height, 0.8)], m["desk"])
    bevel(body, 0.6, segments=1, angle=30)
    swatched(body, m["desk"], DESK, "keycap")
    paint(body, m["desk"], keys_uv, lambda c, n, kind: n.z > 0.95 and c.z > lift + height - 0.4)
    body.data.transform(DECK)
    return body


def keys(m):
    """Every key on the deck: the ones the clip presses apart."""
    static, moving = [], {}
    for name, x, row, w, _legend, tall in L.KEYS:
        cap = keycap("key_" + name, L.key_rect(x, row, w, tall), m)
        if name in L.PRESSED:
            moving["key_" + name] = cap
        else:
            static.append(cap)
    return static, moving


# ---- The mouse and the mat -------------------------------------------------------------------------------------------

def mouse_outline(n=36):
    """The mouse from above, its middle at the origin, its buttons forward (+y): an egg, its back the wider."""
    w, length, _h = L.MOUSE["size"]
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        y = length / 2 * math.sin(a)
        x = w / 2 * math.cos(a) * (1.0 - 0.10 * math.sin(a)) * (1.0 - 0.06 * math.cos(2 * a))
        out.append((x, y))
    return out


def mouse(m):
    """The mouse lofted up its outline to a dome peaking behind its middle, its top printed (the buttons' split, the
    wheel's slot, the lit stripe and badge), its skirt black."""
    w, length, h = L.MOUSE["size"]
    rings = []
    for z, scale, lean in ((0.0, 0.93, 0.0), (2.5, 1.0, 0.0), (h * 0.45, 0.98, -2.0), (h * 0.72, 0.86, -6.0),
                           (h * 0.9, 0.62, -10.0), (h, 0.28, -13.0)):
        rings.append([(x * scale, y * scale + lean, z) for x, y in mouse_outline()])
    body = solid("mouse", rings, m["desk"])
    for p in body.data.polygons:
        p.use_smooth = True
    top = DESK.uv("mouse", w, length)
    paint(body, m["desk"], lambda co: top(co.x + w / 2, length / 2 - co.y), lambda c, n, kind: n.z > 0.35)
    swatched(body, m["desk"], DESK, "rubber", lambda c, n, kind: n.z <= 0.35)
    wheel = solid("wheel", [[(x, length * 0.30 + 7.5 * math.cos(2 * math.pi * k / 12), h * 0.80 + 7.5 * math.sin(
        2 * math.pi * k / 12)) for k in range(12)] for x in (-3.5, 3.5)], m["desk"])
    swatched(wheel, m["desk"], DESK, "grey")
    return join([body, wheel], "mouse")


def mat(m):
    x0, x1 = L.MAT["x"]
    y0, y1 = L.MAT["y"]
    slab = box("mat", x0, x1, y0, y1, 0.0, L.MAT["thick"], m["desk"])
    bevel(slab, 1.2, segments=1)
    swatched(slab, m["desk"], DESK, "lit")
    top = DESK.uv("mat", x1 - x0, y1 - y0)
    paint(slab, m["desk"], lambda co: top(co.x - x0, y1 - co.y), lambda c, n, kind: n.z > 0.9)
    return slab


# ---- The focused clip ------------------------------------------------------------------------------------------------

class Spin(Pose):
    """A pose turning degrees about an axis in the parent's frame (a fan's rotor about its own axis)."""

    def __init__(self, axis, degrees):
        super().__init__()
        self.axis, self.degrees = Vector(axis), degrees

    def rotation(self):
        return Quaternion(self.axis, math.radians(self.degrees))


def press(f, f0, f1=None):
    """A key or a button pressed at f0 (and held until f1): down in two frames, back up in three."""
    f1 = f0 + 2 if f1 is None else f1
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f1, f1 + 3)))


def timeline(f):
    poses = {}
    axis = Matrix.Rotation(math.radians(T["turn"]), 3, "Z") @ Vector((0.0, 1.0, 0.0))
    for name, turns, facing in FAN_SPINS:
        sign = -1.0 if facing else 1.0
        poses[name] = Spin(axis, sign * 360.0 * turns * f / L.LENGTH)
    x, y = mouse_offset(L.POINTER.at(f), L.REST, L.GAIN, L.MOUSE["turn"])
    click = max(press(f, f0, f0 + L.CLICK) for f0 in L.CLICKS)
    poses["mouse"] = Pose(x=x, y=y, z=-1.2 * click, squash=0.035 * click)
    for name in L.PRESSED:
        depth = K["press"] * max(press(f, f0, f1) for f0, f1 in L.KEY_PRESSES[name])
        d = DOWN * depth
        poses["key_" + name] = Pose(x=d.x, y=d.y, z=d.z)
    return poses


FAN_SPINS = []


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    load = lambda name: bpy.data.images.load(os.path.join(images, name))   # noqa: E731
    m = materials(dict(case="#FFFFFF", desk="#FFFFFF", video="#FFFFFF"), ROUGHNESS,
                  dict(case=load("windows_case.png"), desk=load("windows_desk.png"), video=load("windows_screen.png")))

    frame = tower_frame()
    tower = shell(m) + inside(m)
    spinners = {}
    for fan_frame_, spinner, middle, turns, facing in fans(m):
        tower.append(fan_frame_)
        spinners[spinner.name] = (smoothed(spinner, 30.0), frame @ middle)
        FAN_SPINS.append((spinner.name, turns, facing))
        spinner.data.transform(Matrix.Rotation(math.radians(T["turn"]), 4, "Z"))
    boolean(tower[0], back_vent(m))
    for part in tower:
        part.data.transform(frame)
    static, moving = keys(m)
    whole = smoothed(join(tower + monitor(m) + [keyboard_case(m)] + static + [mat(m)], "windows"), 35.0)
    for part in moving.values():
        smoothed(part, 35.0)
    rodent = smoothed(mouse(m), 50.0)
    rodent.data.transform(Matrix.Rotation(math.radians(L.MOUSE["turn"]), 4, "Z"))
    mx, my = L.MOUSE["at"]
    parts = dict(spinners)
    parts["mouse"] = (rodent, Vector((mx, my, L.MAT["thick"])))
    parts.update({name: (obj, Vector()) for name, obj in moving.items()})
    finish("windows", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Windows")


if __name__ == "__main__":
    main()
