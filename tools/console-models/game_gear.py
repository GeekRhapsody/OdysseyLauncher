"""The console theme's Sega Game Gear system model (godot/themes/console/models/systems/gamegear.glb): the black Game
Gear, standing up.

Built in Blender from the real handheld's size and Evan-Amos's photographs of it (game_gear_layout.py has the
measurements): the shell from its face's outline lofted back, its front and back edges rounded, the seam where its two
halves meet run round its sides; the glossy island sunk into its face between the matt grips and reaching up over its
top edge, the lens set into it (one sheet of black acrylic: the printing, the power light and the LCD's grey frame round
its window); the D-pad (a disc, its cross standing on it) in its well and the speaker's 36 holes in the left grip; START
(a blue drop on the island's edge) and the 1 and 2 buttons in their wells in the right grip; on the top edge the VOLUME
wheel, the PHONE, EXT and DC 9V sockets, the red POWER switch in its recess, and at the back the notch the cartridge
slides down into; the battery covers on the back. The printing is one texture drawn by game_gear_print.py (the face,
the back, the top edge, the cartridge's label side, swatches); the lens is the card's `video` material, its still the
Game Gear switched off.

A node tree (card.finish()): the root holding the set; the set holding the cartridge (a made-up game, waiting in the
notch, shrunk to nothing), the POWER switch, the D-pad, START, 1 and 2.

The `focused` clip (9.5 s, looping; its timing is game_gear_layout.py's, which the video follows) plays a game: the
cartridge grows in over the notch with its label to the viewer, turns round and drops in, and settles; POWER slides
on, and the lens's video takes over: the power light and the backlight come on, a made-up publisher's splash, the
game's title; START, and the game: the D-pad held right while the ninja runs, 2 for each knife, 1 for each leap. Then
POWER slides off, the screen goes dark, and the cartridge rises out of the notch and goes.

Three materials (case, gloss, video) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/game_gear_print.py artifacts/made-up-games artifacts/gamegear
    python tools/console-models/game_gear_video.py artifacts/made-up-games godot/themes/console/videos/gamegear.mp4
    blender -b --factory-startup --python tools/console-models/game_gear.py -- artifacts/gamegear godot/themes/console/models/systems/gamegear.glb
"""

import math
import os
import sys

# ---- Outlines other cards use (switch.py and wonderswan.py import these three) ---------------------------------------


def rounded_polygon(corners, radii, inset=0.0, segments=10):
    """
    A convex polygon's outline (anticlockwise corners as seen from the front, (x, height) in mm) with each corner
    rounded by its radius, moved in by inset (the radii shrink with it). Every call gives the same number of points
    for the same corners, so outlines at several insets can be joined into rings.
    """
    n = len(corners)
    lines = []
    for i in range(n):
        (ax, av), (bx, bv) = corners[i], corners[(i + 1) % n]
        dx, dv = bx - ax, bv - av
        length = math.hypot(dx, dv)
        nx, nv = -dv / length, dx / length  # the inward normal of an anticlockwise edge
        lines.append(((ax + nx * inset, av + nv * inset), (dx / length, dv / length)))

    def meet(l1, l2):
        (p, d), (q, e) = l1, l2
        det = d[0] * -e[1] - d[1] * -e[0]
        t = ((q[0] - p[0]) * -e[1] - (q[1] - p[1]) * -e[0]) / det
        return p[0] + d[0] * t, p[1] + d[1] * t

    moved = [meet(lines[i - 1], lines[i]) for i in range(n)]
    points = []
    for i in range(n):
        cx, cv = moved[i]
        ax, av = moved[i - 1]
        bx, bv = moved[(i + 1) % n]
        ux, uv = ax - cx, av - cv
        wx, wv = bx - cx, bv - cv
        lu, lw = math.hypot(ux, uv), math.hypot(wx, wv)
        ux, uv, wx, wv = ux / lu, uv / lu, wx / lw, wv / lw
        half = math.acos(max(-1.0, min(1.0, ux * wx + uv * wv))) / 2
        r = max(radii[i] - inset, 0.05)
        t = r / math.tan(half)
        sx, sv = ux + wx, uv + wv
        ls = math.hypot(sx, sv)
        ox, ov = cx + sx / ls * r / math.sin(half), cv + sv / ls * r / math.sin(half)
        a1 = math.atan2(cv + uv * t - ov, cx + ux * t - ox)
        a2 = math.atan2(cv + wv * t - ov, cx + wx * t - ox)
        while a2 < a1:
            a2 += 2 * math.pi
        for k in range(segments + 1):
            a = a1 + (a2 - a1) * k / segments
            points.append((ox + r * math.cos(a), ov + r * math.sin(a)))
    return points


def rectangle(cx, cv, w, h, r, inset=0.0, segments=6):
    corners = [(cx + w / 2, cv - h / 2), (cx + w / 2, cv + h / 2), (cx - w / 2, cv + h / 2), (cx - w / 2, cv - h / 2)]
    return rounded_polygon(corners, [r] * 4, inset, segments)


def ellipse(cx, cv, rx, rv, degrees=0.0, segments=40):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    points = []
    for k in range(segments):
        a = 2 * math.pi * k / segments
        x, v = rx * math.cos(a), rv * math.sin(a)
        points.append((cx + x * c - v * s, cv + x * s + v * c))
    return points


# ---- The Game Gear ---------------------------------------------------------------------------------------------------

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_gear_layout as L  # noqa: E402
import handheld as H  # noqa: E402
from amiga import paint, solid  # noqa: E402
from card import Atlas, finish, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, material  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: its right end (POWER, START, 1 and 2) comes towards the viewer
TILT_PITCH = 14.0    # degrees about the horizontal: seen a little from above, its top edge and the notch in view
ROUGHNESS = dict(case=0.55, gloss=0.28, video=0.22)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
FACE = H.face_uv(ATLAS, "face", (-L.WIDTH / 2, L.WIDTH / 2, 0.0, L.HEIGHT))
BACK = H.back_uv(ATLAS, "back", (-L.WIDTH / 2, L.WIDTH / 2, 0.0, L.HEIGHT))
TOP_REGION = ATLAS.uv("top", L.WIDTH, L.DEPTH)
CART_SIDE = H.back_uv(ATLAS, "cart", (-L.CART["width"] / 2, L.CART["width"] / 2, 0.0, L.CART["height"]))
HOVER = 72.0         # how far over its seat the cartridge appears: its foot just clear of the top edge


def top_uv(co):
    """The top edge seen from above, its back at the region's top."""
    return TOP_REGION(co.x + L.WIDTH / 2, L.DEPTH - co.y)


def lens_uv(co):
    """The lens's video across its frame (LENS), upright."""
    x0, x1, z0, z1 = L.LENS
    return (co.x - x0) / (x1 - x0), (co.z - z0) / (z1 - z0)


def front(c, n, kind):
    return n.y < -0.9


def shaded(obj, angle=40.0):
    """Smooth, but the big flat faces flat (their long triangles would bend the light), and edges past angle sharp."""
    for p in obj.data.polygons:
        n = p.normal
        p.use_smooth = not (abs(n.y) > 0.995 or abs(n.z) > 0.995)
    obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


# ---- The shell -------------------------------------------------------------------------------------------------------

def rings(grow=0.0, back_by=0.0, steps=4):
    """The shell's rings (y, inset) front to back: the face's edge rounded, the seam's groove, the back's edge rounded;
    grow pushes the outline out, back_by moves it all back."""
    f, b = L.FRONT_ROUND, L.BACK_ROUND
    out = []
    for k in range(steps + 1):
        a = math.pi / 2 * k / steps
        out.append((f * (1 - math.cos(a)), f * (1 - math.sin(a))))
    y, w, d = L.SEAM
    out += [(y - w / 2 - 0.15, 0.0), (y - w / 2, d), (y + w / 2, d), (y + w / 2 + 0.15, 0.0)]
    for k in range(steps + 1):
        a = math.pi / 2 * k / steps
        out.append((L.DEPTH - b + b * math.sin(a), b * (1 - math.cos(a))))
    return [[(x, y + back_by, z) for x, z in L.rounded(*L.OUTLINE, inset=inset - grow, segments=10)]
            for y, inset in out]


def shell(m):
    body = solid("gamegear", rings(), m["case"])

    # The island: within its outline, the face is the shell moved back ISLAND_DEPTH (so it follows the top edge's
    # rounding over the top); its floor and walls glossy.
    island = plate("island", L.rounded(*L.ISLAND, segments=12), -6.0, 14.0, m["gloss"])
    boolean(island, solid("behind", rings(grow=0.3, back_by=L.ISLAND_DEPTH), m["gloss"]))
    boolean(body, island)

    # The wells, the speaker's holes, the sockets, the POWER switch's recess, the cartridge's notch and the slots in
    # the bottom edge: their insides dark.
    cuts = [plate("dpad_well", H.circle(*L.DPAD["at"], L.DPAD["well"], 48), -3.0, 1.2, m["dark"])]
    for name in ("one", "two"):
        cuts.append(plate("button_well", H.circle(*L.BUTTONS[name], L.BUTTONS["well"], 32), -3.0, 1.0, m["dark"]))
    sp = L.SPEAKER
    for z, count in sp["rows"]:
        for i in range(count):
            x = sp["x"] + (i - (count - 1) / 2) * sp["pitch"]
            cuts.append(plate("hole", H.circle(x, z, sp["r"], 8), -3.0, 3.0, m["dark"]))
    x0, x1, y0, y1 = L.POWER["recess"]
    cuts.append(box("power_recess", x0, x1, y0, y1, L.HEIGHT - 2.2, L.HEIGHT + 5.0, m["dark"]))
    for name in ("dc", "phone"):
        x, y, r = L.JACKS[name]
        socket = lathe("socket", [(0.0, -3.0), (r, -3.0), (r, 6.0), (0.0, 6.0)], m["dark"], 16)
        socket.data.transform(Matrix.Translation((x, y, L.HEIGHT)))
        cuts.append(socket)
    x, y, w, h = L.JACKS["ext"]
    cuts.append(box("ext", x - w / 2, x + w / 2, y - h / 2, y + h / 2, L.HEIGHT - 2.5, L.HEIGHT + 5.0, m["dark"]))
    v = L.VOLUME
    cuts.append(box("volume_slot", v["x"] - v["r"] - 0.8, v["x"] + v["r"] + 0.8, v["y"][0] - 0.6, v["y"][1] + 0.6,
                    L.HEIGHT - 6.0, L.HEIGHT + 5.0, m["dark"]))
    n = L.NOTCH
    cuts.append(box("notch", -n["x"], n["x"], n["y"], L.DEPTH + 5.0, n["z"], L.HEIGHT + 5.0, m["dark"]))
    fw, fy, fd = L.FEET["size"]
    for side in (-1, 1):
        x = side * L.FEET["x"]
        cuts.append(box("foot_slot", x - fw / 2, x + fw / 2, fy, fy + 6.0, -5.0, fd, m["dark"]))
    boolean(body, join(cuts, "cuts"))

    # The battery covers, a little proud of the back.
    w, h = L.COVERS["size"]
    z = L.COVERS["z"]
    covers = []
    for side in (-1, 1):
        x = side * L.COVERS["x"]
        corners = [(x + w / 2, z - h / 2), (x + w / 2, z + h / 2), (x - w / 2, z + h / 2), (x - w / 2, z - h / 2)]
        covers.append(plate("cover", L.rounded(corners, [L.COVERS["r"]] * 4, segments=4), L.DEPTH - 0.6,
                            L.DEPTH + L.COVERS["out"], m["case"]))
    for cover in covers:
        bevel(cover, 0.3, segments=1)
    body = join([body] + covers, "gamegear")

    # The printing: the matt faces from their projections, the island's floor from the face's, the cuts dark.
    shell_swatch, band, dark = ATLAS.swatch("shell"), ATLAS.swatch("band"), ATLAS.swatch("dark")
    paint(body, m["case"], shell_swatch, lambda c, n, kind: kind == "case")
    paint(body, m["case"], FACE, lambda c, n, kind: kind == "case" and n.y < -0.9)
    paint(body, m["case"], BACK, lambda c, n, kind: kind == "case" and n.y > 0.9)
    paint(body, m["case"], top_uv, lambda c, n, kind: kind == "case" and n.z > 0.9 and c.z > L.HEIGHT - 3.0)
    paint(body, m["gloss"], band, lambda c, n, kind: kind == "gloss")
    paint(body, m["gloss"], FACE, lambda c, n, kind: kind == "gloss" and n.y < -0.9)
    paint(body, m["case"], FACE, lambda c, n, kind: kind == "dark" and n.y < -0.9)
    paint(body, m["case"], top_uv, lambda c, n, kind: kind == "dark" and n.z > 0.9 and c.z > L.NOTCH["z"] - 1.0)
    paint(body, m["case"], dark, lambda c, n, kind: kind == "dark")
    return body


def lens(m):
    """The lens: black acrylic set into the island, its face the video."""
    part = plate("lens", L.rounded(*L.PANEL, segments=12), L.PANEL_FACE, L.PANEL_FACE + 1.8, m["gloss"])
    paint(part, m["gloss"], ATLAS.swatch("dark"), lambda c, n, kind: True)
    paint(part, m["video"], lens_uv, front)
    return part


def volume(m):
    v = L.VOLUME
    wheel = lathe("volume", [(0.0, v["y"][0]), (v["r"], v["y"][0]), (v["r"], v["y"][1]), (0.0, v["y"][1])], m["case"], 24)
    # The lathe turns about z; turned, the wheel's axis runs front to back, its rim standing out of the top.
    wheel.data.transform(Matrix.Translation((v["x"], 0.0, L.HEIGHT - v["r"] + v["out"])) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    paint(wheel, m["case"], ATLAS.swatch("wheel"), lambda c, n, kind: True)
    return wheel


# ---- The moving parts ------------------------------------------------------------------------------------------------

def dpad(m):
    """The D-pad, its middle at its origin on the face: the disc, its cross standing on it."""
    x, z = L.DPAD["at"]
    disc = plate("dpad_disc", H.circle(x, z, L.DPAD["r"], 48), -1.6, 1.1, m["gloss"])
    bevel(disc, 0.7, segments=2)
    arm, half = L.DPAD["arm"], L.DPAD["half"]
    arms = [plate("dpad_arm", [(x + px, z + pz) for px, pz in H.stadium(0.0, 0.0, 2 * arm, 2 * half, deg, 4)], -2.7, -1.2,
                  m["gloss"]) for deg in (0.0, 90.0)]
    for a in arms:
        bevel(a, 0.6, segments=2, angle=50)
    part = join([disc] + arms, "dpad")
    paint(part, m["gloss"], ATLAS.swatch("black"), lambda c, n, kind: True)
    paint(part, m["gloss"], FACE, front)
    part.data.transform(Matrix.Translation((-x, 0.0, -z)))
    return part


def dome(name, at, r, h, m):
    """A round button facing the viewer, its middle on the face at its origin."""
    part = lathe(name, [(0.0, -1.0), (r, -1.0), (r, h * 0.45)] + [(r * math.cos(math.pi / 2 * k / 5),
                                                                    h * 0.45 + h * 0.55 * math.sin(math.pi / 2 * k / 5))
                                                                   for k in range(1, 6)], m["gloss"], 32)
    part.data.transform(Matrix.Translation((at[0], 0.0, at[1])) @ Matrix.Rotation(math.radians(90.0), 4, "X"))
    paint(part, m["gloss"], ATLAS.swatch("black"), lambda c, n, kind: True)
    paint(part, m["gloss"], FACE, lambda c, n, kind: n.y < -0.85)
    part.data.transform(Matrix.Translation((-at[0], 0.0, -at[1])))
    return part


def start(m):
    """START, the blue drop on the island's edge, its straight side's middle at its origin."""
    part = plate("start", L.drop(), -2.0, 0.8, m["gloss"])
    bevel(part, 0.8, segments=2, angle=50)
    paint(part, m["gloss"], ATLAS.swatch("blue"), lambda c, n, kind: True)
    paint(part, m["gloss"], FACE, front)
    x, z = L.START["at"]
    part.data.transform(Matrix.Translation((-x, 0.0, -z)))
    return part


def power(m):
    """The POWER switch's red knob, at OFF, its middle at its origin."""
    w, t, h = L.POWER["knob"]
    part = box("power", -w / 2, w / 2, -t / 2, t / 2, -h / 2, h / 2, m["case"])
    bevel(part, 0.5, segments=2)
    paint(part, m["case"], ATLAS.swatch("red"), lambda c, n, kind: True)
    return part


def cartridge(m):
    """The cartridge, its foot's middle at its origin, its label side +y: the body, the label's recess, the grip's U."""
    c = L.CART
    w, h, t, rib = c["width"], c["height"], c["thick"], c["rib"]
    body = box("cartridge", -w / 2, w / 2, -t / 2, t / 2, 0.0, h, m["case"])
    bevel(body, 0.8, segments=2)
    x0, x1, z0, z1 = c["label"]
    r_top, r_bottom = c["label_r"]
    label = L.rounded([(x1, z0), (x1, z1), (x0, z1), (x0, z0)], [r_bottom, r_top, r_top, r_bottom], segments=6)
    boolean(body, plate("label", label, t / 2 - 0.4, t / 2 + 3.0, m["case"]))
    g0, g1, gz0, gz1 = c["grip"]
    leg = c["leg"]
    grip = [box("grip", g0, g1, t / 2 - 0.5, t / 2 + rib, gz0, gz1, m["case"]),
            box("grip_left", g0, g0 + leg, t / 2 - 0.5, t / 2 + rib, c["legs_to"], gz0 + 0.5, m["case"]),
            box("grip_right", g1 - leg, g1, t / 2 - 0.5, t / 2 + rib, c["legs_to"], gz0 + 0.5, m["case"])]
    for part in grip:
        bevel(part, 0.5, segments=2)
    part = join([body] + grip, "cartridge")
    paint(part, m["case"], ATLAS.swatch("cart"), lambda c_, n, kind: True)
    paint(part, m["case"], CART_SIDE, lambda c_, n, kind: n.y > 0.9)
    return part


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def timeline(f):
    a, b, c, d = L.CART_IN
    out, gone, vanish = L.CART_OUT
    turn = b + 8                                           # it shows its label a moment, then turns round
    if f < a or f >= vanish:
        cart = Pose(scale=HIDDEN)
    elif f < b:
        cart = Pose(z=HOVER, spin=180.0, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, a, b)))
    elif f < c:
        t = smooth(phase(f, turn, c))
        cart = Pose(z=HOVER + 4.0 * math.sin(math.pi * phase(f, b, c)), spin=180.0 * (1 - t))
    elif f < d:
        cart = Pose(z=HOVER * (1 - ease_in(phase(f, c, d))))
    elif f < out:
        cart = Pose(z=1.4 * math.exp(-(f - d) / 3.0) * abs(math.sin(math.pi * (f - d) / 5.0)))
    elif f < gone:
        cart = Pose(z=HOVER * ease_out(phase(f, out, gone)))
    else:
        cart = Pose(z=HOVER, scale=max(HIDDEN, 1 - ease_in(phase(f, gone, vanish))))
    on = smooth(phase(f, L.ON, L.ON + 4)) * (1 - smooth(phase(f, L.OFF, L.OFF + 4)))
    held = smooth(phase(f, L.RUN - 2, L.RUN + 1)) * (1 - smooth(phase(f, L.PLAY[1] - 4, L.PLAY[1] - 1)))
    return {"cartridge": cart, "power": Pose(x=L.POWER["travel"] * on),
            "start": Pose(y=1.3 * tap(f, L.START_PRESS, 3)),
            "button_1": Pose(y=1.5 * max(tap(f, f0) for f0 in L.JUMPS)),
            "button_2": Pose(y=1.5 * max(tap(f, f0) for f0 in L.THROWS)),
            "dpad": Pose(spin=7.0 * held, pitch=-1.5 * held * math.sin(f * 0.35))}


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    printed = bpy.data.images.load(os.path.join(images, "game_gear_print.png"))
    still = bpy.data.images.load(os.path.join(images, "game_gear_lens.png"))
    m = dict(case=material("case", "#FFFFFF", ROUGHNESS["case"], printed),
             gloss=material("gloss", "#FFFFFF", ROUGHNESS["gloss"], printed),
             # The lens: the launcher plays the card's video on the material named video (A6 Card videos).
             video=material("video", "#FFFFFF", ROUGHNESS["video"], still),
             # The cuts' insides until they're painted (shell()): unused after that, so it isn't exported.
             dark=material("dark", "#101012", 0.6))

    whole = shaded(join([shell(m), lens(m), volume(m)], "gamegear"))
    c = L.CART
    parts = {"cartridge": (shaded(cartridge(m)), Vector(c["seat"])),
             "power": (shaded(power(m)), Vector((L.POWER["off"], (L.POWER["recess"][2] + L.POWER["recess"][3]) / 2,
                                                 L.HEIGHT - 2.2 + L.POWER["knob"][2] / 2 + 0.6))),
             "dpad": (shaded(dpad(m)), Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1]))),
             "start": (shaded(start(m)), Vector((L.START["at"][0], 0.0, L.START["at"][1]))),
             "button_1": (smoothed(dome("button_1", L.BUTTONS["one"], L.BUTTONS["r"], 3.2, m), 50.0),
                          Vector((L.BUTTONS["one"][0], 0.0, L.BUTTONS["one"][1]))),
             "button_2": (smoothed(dome("button_2", L.BUTTONS["two"], L.BUTTONS["r"], 3.2, m), 50.0),
                          Vector((L.BUTTONS["two"][0], 0.0, L.BUTTONS["two"][1])))}
    finish("gamegear", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Game Gear")


if __name__ == "__main__":
    main()
