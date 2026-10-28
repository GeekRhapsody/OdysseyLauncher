"""The console theme's Game Boy Advance system model (godot/themes/console/models/systems/gba.glb): Nintendo's indigo
Game Boy Advance, AGB-001, standing up.

Built in Blender with handheld.py's pieces (gba_layout.py has the measurements, from the BnF's photographs of an indigo
one, Evan-Amos's and dimensions.com's elevations): the main body from the face's outline traced from a photograph, 14.5
mm deep, its edges rounded; the back's middle swelling out to 24.5 mm behind it, lofted along its width (flat across
the battery cover and the cartridge's bay, curving away into the grips), the slot cut down into its top; the lens
standing a little off the face; the light grey D-pad, A and B, START and SELECT standing out of it; the grey caps round
the ends, swept along the outline, the L and R buttons their parts over the top corners, reaching back past the body;
the power switch's slider under the bottom edge's left end, the headphones' socket and the volume wheel under its
right, the link port in the top edge. The printing is gba_print.py's: the face, the back, the cartridge's two sides and
the buttons' tops in one atlas, projected square on.

The lens is the `video` material (A6 Card videos): while the card is focused the launcher plays the theme's video for
it there (godot/themes/console/videos/gba.mp4, drawn by gba_video.py), which shows the whole lens, its printing and the
screen, frame for frame with the clip, starting it again each time the clip loops; otherwise, and where there's no
decoder, the lens shows its own texture, the screen switched off.

A node tree (card.finish()): the root holding the set; the set holding the cartridge (waiting in its seat in the bay,
shrunk to nothing), the D-pad, A, B, START and SELECT, the L and R buttons (each turning about its inner end), the power
switch's slider and the POWER light (shrunk to nothing until it's on).

The `focused` clip (10 s, looping; its timing is gba_layout.py's, which the video follows) plays a game: a cartridge (a
made-up game, Kaleidrop) appears over the handheld showing its label, turns round, drops into the bay and settles; the
switch slides to ON and the light comes on; on the screen the start-up, then Kaleidrop's title, START, and a round of
play, its gems moved with the D-pad, turned with A and B and slammed down with R in step with the presses; the switch
slides to OFF, the light and the picture go, and the cartridge rises out and shrinks away.

Two materials (case, video) and two textures, within the system model budget. Run from the repo root:

    python tools/console-models/gba_print.py artifacts/made-up-games artifacts/gba
    python tools/console-models/gba_video.py artifacts/made-up-games godot/themes/console/videos/gba.mp4
    blender -b --factory-startup --python tools/console-models/gba.py -- artifacts/gba godot/themes/console/models/systems/gba.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gba_layout as L  # noqa: E402
import handheld as H  # noqa: E402
from amiga import paint, solid  # noqa: E402
from card import Atlas, coloured, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, ease_out, phase, smooth  # noqa: E402
from emblems import plate  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join  # noqa: E402
from props import lathe  # noqa: E402

TILT_YAW = -22.0     # degrees about the vertical: its right end comes towards the viewer
TILT_PITCH = 10.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(case=0.5, video=0.25)
ATLAS = Atlas(L.ATLAS, L.REGIONS, L.SWATCHES)
FACE = H.face_uv(ATLAS, "face", L.FACE_BOX)
BACK = H.back_uv(ATLAS, "back", L.FACE_BOX)


# ---- The body ------------------------------------------------------------------------------------------------------------

def body(m):
    part = H.body("gba", L.outline(), L.BODY_DEPTH, m["case"], front=L.FRONT_ROUND, back=L.BACK_ROUND, steps=3)
    coloured(part, m["case"], ATLAS, "case")
    paint(part, m["case"], FACE, lambda c, n, kind: n.y < -0.9)
    paint(part, m["case"], BACK, lambda c, n, kind: n.y > 0.9)
    return part


def swell(m):
    """The back's middle: cross-sections along x, each from inside the body back to swell_depth(x), its back corners
    rounded, from just above the bottom edge to swell_top(x); the slot cut down into its top."""
    rings = []
    front = L.BODY_DEPTH - 3.0
    xs = [-L.SWELL["end"] + 2.0 * k for k in range(int(L.SWELL["end"]) + 1)]
    for x in xs:
        depth = L.swell_depth(x)
        full = (depth - L.BODY_DEPTH + 1.0) / (L.DEPTH - L.BODY_DEPTH + 1.0)      # 1 across the middle, 0 at its ends
        z0 = L.bottom_z(x) + L.SWELL["bottom"] + 3.0 * (1.0 - full)
        z1 = L.swell_top(x) - 2.0 * (1.0 - full)
        rb = min(L.SWELL["back_round"], 0.45 * (depth - front), 0.45 * (z1 - z0))
        rt = min(L.SWELL["top_round"], 0.45 * (depth - front))
        section = [(front, z0)]
        section += [(depth - rb + rb * math.cos(a), z0 + rb + rb * math.sin(a))
                    for a in (math.radians(-90 + 90 * k / 5) for k in range(6))]
        section += [(depth - rt + rt * math.cos(a), z1 - rt + rt * math.sin(a))
                    for a in (math.radians(90 * k / 4) for k in range(5))]
        section += [(front, z1)]
        rings.append([(x, y, z) for y, z in section])
    part = solid("swell", rings, m["case"])
    y0, y1 = L.SLOT["y"]
    boolean(part, box("slot", -L.SLOT["x"], L.SLOT["x"], y0, y1, L.SLOT["z"], L.SWELL["top"] + 10.0, m["case"]))
    coloured(part, m["case"], ATLAS, "case")
    paint(part, m["case"], BACK, lambda c, n, kind: n.y > 0.5 and c.y > L.BODY_DEPTH + 0.5)
    paint(part, m["case"], ATLAS.swatch("slot"),
          lambda c, n, kind: abs(c.x) < L.SLOT["x"] + 0.05 and y0 - 0.05 < c.y < y1 + 0.05 and c.z > L.SLOT["z"] - 0.05
          and c.z < L.SWELL["top"] - 0.05)
    return part


def lens(m):
    """The lens, standing LENS_OUT off the face: its front the video's surface, mapped across the lens's box."""
    part = plate("lens", L.lens_outline(), -L.LENS_OUT, 0.6, m["case"])
    bevel(part, 0.25, segments=1, angle=40.0)
    coloured(part, m["case"], ATLAS, "lens")
    x0, x1, z0, z1 = L.LENS_BOX
    paint(part, m["video"], lambda co: ((co.x - x0) / (x1 - x0), (co.z - z0) / (z1 - z0)),
          lambda c, n, kind: n.y < -0.99)
    return part


def band(name, path, inside, out, y0, y1, rr, mat):
    """A band along path ((x, z) points on the face's outline, anticlockwise): its cross-section from `inside` the
    outline to `out` beyond it, y0 to y1 deep, its outer corners rounded rr."""
    section = [(-inside, y0)]
    section += [(out - rr + rr * math.cos(a), y0 + rr + rr * math.sin(a)) for a in (math.radians(-90 + 30 * k) for k in range(4))]
    section += [(out - rr + rr * math.cos(a), y1 - rr + rr * math.sin(a)) for a in (math.radians(30 * k) for k in range(4))]
    section += [(-inside, y1)]
    rings = []
    n = len(path)
    for i, (x, z) in enumerate(path):
        (ax, az), (bx, bz) = path[max(0, i - 1)], path[min(n - 1, i + 1)]
        length = math.hypot(bx - ax, bz - az)
        nx, nz = (bz - az) / length, -(bx - ax) / length       # outward, the outline running anticlockwise
        rings.append([(x + u * nx, y, z + u * nz) for u, y in section])
    return solid(name, rings, mat)


def end_paths():
    """The outline's part each end's grey cap runs along, anticlockwise: from the bottom edge (x = CAP start) up the end
    and over the top corner (to x = CAP end); the right end's, then the left's."""
    pts = L.outline(per=4)
    i0 = next(i for i, (x, z) in enumerate(pts) if x >= L.CAP["start"])
    i1 = next(i for i, (x, z) in enumerate(pts) if i > i0 and z > 40.0 and x <= L.CAP["end"])
    right = pts[i0:i1 + 1]
    left = [(-x, z) for x, z in reversed(right)]
    return right, left


def caps(m):
    """The grey caps round the ends (their parts below the shoulder buttons), and the L and R buttons."""
    c = L.CAP
    lower, shoulders = [], {}
    for side, path in zip((1, -1), end_paths()):
        low = [p for p in path if p[1] <= c["shoulder_z"] - c["gap"] / 2]
        high = [p for p in path if p[1] >= c["shoulder_z"] + c["gap"] / 2]
        cap = band("cap", low, c["inside"], c["out"], c["y"][0], c["y"][1], c["round"], m["case"])
        lower.append(coloured(cap, m["case"], ATLAS, "grey"))
        sh = band("shoulder", high, c["inside"], c["out"], c["shoulder_y"][0], c["shoulder_y"][1], c["round"], m["case"])
        coloured(sh, m["case"], ATLAS, "grey")
        x = side * L.CAP["end"]
        hinge = Vector((x, (c["shoulder_y"][0] + c["shoulder_y"][1]) / 2, L.top_z(x) - 1.0))
        sh.data.transform(Matrix.Translation(-hinge))
        shoulders["shoulder_r" if side > 0 else "shoulder_l"] = (smoothed(sh, 40.0), hinge)
    return lower, shoulders


# ---- The controls ----------------------------------------------------------------------------------------------------

def dome(name, r, height, m, top=None):
    """A round button facing the viewer, its foot's middle at its origin; top: its face's atlas region."""
    d = r * 0.3
    profile = [(0.0, -1.0), (r, -1.0), (r, height - d)]
    profile += [(r * math.cos(math.pi / 2 * k / 4), height - d + d * math.sin(math.pi / 2 * k / 4)) for k in range(1, 5)]
    part = lathe(name, profile, m["case"], 28)
    part.data.transform(Matrix.Rotation(math.radians(90.0), 4, "X"))
    coloured(part, m["case"], ATLAS, "grey")
    if top:
        uv = ATLAS.uv(top, 2 * r, 2 * r)
        paint(part, m["case"], lambda co: uv(co.x + r, r - co.z), lambda c, n, kind: n.y < -0.5)
    return smoothed(part, 50.0)


def dpad(m):
    d = L.DPAD
    part = plate("dpad", H.cross(0.0, 0.0, d["arm"], d["half"]), -d["height"], 1.0, m["case"])
    bevel(part, 0.8, segments=2, angle=50.0)
    coloured(part, m["case"], ATLAS, "grey")
    a = d["arm"]
    uv = ATLAS.uv("dpad", 2 * a, 2 * a)
    paint(part, m["case"], lambda co: uv(co.x + a, a - co.z), lambda c, n, kind: n.y < -0.9)
    return smoothed(part, 40.0)


def power_switch(m):
    """The slider under the bottom edge's left end, at OFF, its middle at its origin."""
    (x0, x1), (y0, y1) = L.POWER_SWITCH["x"], L.POWER_SWITCH["y"]
    z = L.bottom_z((x0 + x1) / 2)
    part = box("power", x0, x1, y0, y1, z - 1.0, z + 2.0, m["case"])
    bevel(part, 0.4, segments=2)
    coloured(part, m["case"], ATLAS, "black")
    at = Vector(((x0 + x1) / 2, (y0 + y1) / 2, z))
    part.data.transform(Matrix.Translation(-at))
    return smoothed(part), at


def edges(m):
    """What the edges carry: the link port in the top, the headphones' socket and the volume wheel in the bottom."""
    ex, (ey0, ey1) = L.EXT["x"], L.EXT["y"]
    parts = [box("ext", -ex, ex, ey0, ey1, L.HEIGHT - 1.5, L.HEIGHT + 0.25, m["case"])]
    z = L.bottom_z(36.0)
    parts.append(box("phones", 34.6, 37.4, 6.0, 8.8, z - 0.15, z + 2.0, m["case"]))
    z = L.bottom_z(52.0)
    wheel = box("volume", 49.0, 55.0, 5.2, 9.6, z - 0.8, z + 2.0, m["case"])
    bevel(wheel, 0.5, segments=2)
    parts.append(wheel)
    for part in parts:
        coloured(part, m["case"], ATLAS, "dark")
    return parts


def light(m):
    part = plate("power_light", H.circle(0.0, 0.0, L.LED["r"] + 0.1, 16), -0.3, 0.1, m["case"])
    return coloured(part, m["case"], ATLAS, "lit"), Vector((L.LED["at"][0], 0.0, L.LED["at"][1]))


def cartridge(m):
    """The cartridge standing on its contacts, its bottom's middle at its origin, its label to the back (+y)."""
    c = L.CART
    w, h, t = c["width"], c["height"], c["thickness"]
    sw, sh = c["step"]
    outline = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h - sh), (w / 2 - sw, h - sh), (w / 2 - sw, h),
               (-w / 2 + sw, h), (-w / 2 + sw, h - sh), (-w / 2, h - sh)]
    part = plate("cartridge", outline, -t / 2, t / 2, m["case"])
    bevel(part, 0.5, segments=2, angle=40.0)
    coloured(part, m["case"], ATLAS, "cart")
    label = ATLAS.uv("label", w, h)
    paint(part, m["case"], lambda co: label(w / 2 - co.x, h - co.z), lambda c_, n, kind: n.y > 0.9)
    plain = ATLAS.uv("plain", w, h)
    paint(part, m["case"], lambda co: plain(co.x + w / 2, h - co.z), lambda c_, n, kind: n.y < -0.9)
    return smoothed(part, 40.0)


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    """A press at f0: in over two frames, held, out over three."""
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def pressed(f, button):
    return max([tap(f, f0, hold) for f0, name, hold in L.INPUTS if name == button] + [0.0])


def timeline(f):
    c0, c1, c2, c3 = L.CART_IN
    o0, o1, o2 = L.CART_OUT
    if f < c0 or f >= o2:
        cart = Pose(scale=HIDDEN)                      # waiting in its seat
    elif f < c1:
        cart = Pose(z=L.HOVER, spin=180.0, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, c0, c1 - 1)))
    elif f < c2:
        cart = Pose(z=L.HOVER + 3.0 * math.sin(math.pi * phase(f, c1, c2)), spin=180.0 * (1 - smooth(phase(f, c1, c2))))
    elif f < c3:
        cart = Pose(z=L.HOVER * (1 - ease_in(phase(f, c2, c3))))
    elif f < o0:
        cart = Pose(z=1.0 * math.exp(-(f - c3) / 3.0) * abs(math.sin(math.pi * (f - c3) / 5.0)))
    elif f < o1:
        cart = Pose(z=L.HOVER * ease_out(phase(f, o0, o1)))
    else:                                              # gone two frames before it's back in its seat, unseen
        cart = Pose(z=L.HOVER, scale=max(HIDDEN, 1 - ease_in(phase(f, o1, o2 - 2))))
    on = smooth(phase(f, *L.POWER_ON)) * (1 - smooth(phase(f, *L.POWER_OFF)))
    lit = smooth(phase(f, L.POWER_ON[1], L.POWER_ON[1] + 3)) * (1 - smooth(phase(f, L.POWER_OFF[0] + 2, L.POWER_OFF[1])))
    return {
        "cartridge": cart,
        "power": Pose(x=L.POWER_SWITCH["travel"] * on),
        "power_light": Pose(scale=max(HIDDEN, lit)),
        "dpad": Pose(spin=-7.0 * pressed(f, "left") + 7.0 * pressed(f, "right"),
                     pitch=7.0 * pressed(f, "down") - 7.0 * pressed(f, "up")),
        "button_a": Pose(y=1.3 * pressed(f, "a")),
        "button_b": Pose(y=1.3 * pressed(f, "b")),
        "start": Pose(y=1.0 * tap(f, L.START, 3)),
        "select": Pose(),
        "shoulder_r": Pose(roll=2.5 * pressed(f, "r")),
        "shoulder_l": Pose(roll=-2.5 * pressed(f, "l")),
    }


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = L.FPS
    m = materials(dict(case="#FFFFFF", video="#FFFFFF"), ROUGHNESS,
                  dict(case=bpy.data.images.load(os.path.join(images, "gba_print.png")),
                       video=bpy.data.images.load(os.path.join(images, "gba_screen.png"))))

    lower, shoulders = caps(m)
    whole = join([smoothed(body(m), 40.0), smoothed(swell(m), 40.0), lens(m)] + [smoothed(c, 40.0) for c in lower]
                 + [smoothed(e) for e in edges(m)], "gba")
    switch, switch_at = power_switch(m)
    lit, lit_at = light(m)
    parts = {
        "cartridge": (cartridge(m), Vector(L.SEAT)),
        "dpad": (dpad(m), Vector((L.DPAD["at"][0], 0.0, L.DPAD["at"][1]))),
        "button_a": (dome("button_a", L.BUTTONS["r"], L.BUTTONS["height"], m, "btn_a"),
                     Vector((L.BUTTONS["a"][0], 0.0, L.BUTTONS["a"][1]))),
        "button_b": (dome("button_b", L.BUTTONS["r"], L.BUTTONS["height"], m, "btn_b"),
                     Vector((L.BUTTONS["b"][0], 0.0, L.BUTTONS["b"][1]))),
        "start": (dome("start", L.SMALL["r"], L.SMALL["height"], m), Vector((L.SMALL["start"][0], 0.0, L.SMALL["start"][1]))),
        "select": (dome("select", L.SMALL["r"], L.SMALL["height"], m),
                   Vector((L.SMALL["select"][0], 0.0, L.SMALL["select"][1]))),
        "power": (switch, switch_at),
        "power_light": (lit, lit_at),
    }
    parts.update(shoulders)
    finish("gba", whole, parts, timeline, L.LENGTH, TILT_YAW, TILT_PITCH, out, "Game Boy Advance")


if __name__ == "__main__":
    main()
