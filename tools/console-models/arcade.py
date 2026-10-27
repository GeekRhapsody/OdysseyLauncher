"""The console theme's arcade cards (godot/themes/console/models/systems/<card>.glb): a cabinet typical of each arcade
board, its marquee (or its POP sign, or its control panel's front) naming the board, a made-up game on its screen.

Built in Blender from arcade_layout.py's measurements (CABINETS, CARDS). An upright's two side panels are their side
outline extruded across their thickness, edged with T-moulding (their edge faces) and printed with the side art, the
body between them its own outline, its front faces set back between the panels; a candy cabinet's body is one outline
across its whole width, its edges rounded and its sides printed. The body's front faces carry their printing: the
marquee, lit; the speaker panel; the bezel's slope, the monitor's recess cut into it and a CRT's curved glass set in
it, its art round the screen; the lower front, its doors. Boxes stand on the top (a marquee's lightbox, speakers, a POP
sign), their fronts printed. The control panel is a box standing out in front, its plan's front corners cut or
rounded, its top printed and its front carrying a strip, the sticks (a shaft and a ball top) and the buttons standing
on it. The coin goes into a coin door on the lower front (its entries' slots lit red, the coin returns) or a coin
plate on the control panel. The printing is three textures drawn by arcade_print.py: the print (the marquee, the
speakers, the bezel's art, the panel's overlay, the lower front, a POP sign, the panel's strip, swatches), the side
art, and the screens.

A node tree: a root (the turn to a three-quarter view, TILT_YAW and TILT_PITCH: the right side towards the viewer, a
little from above; then the model spec's fit: standing on y = 0, centred, the largest side 1 m) holding the cabinet; the
cabinet holding the screens over the glass (the game's title, two frames of play), shrunk to nothing so at rest the
glass shows the board starting up, the coin (waiting by its slot, shrunk to nothing), the 1P stick, two of its buttons
and 1P START with its light.

The `focused` clip (8 s, looping) plays a credit: a coin goes into the slot; the title comes up with CREDIT 1 and
START flashing; START is pressed and the game plays, the stick waggling and the buttons firing; then back to the
board's start-up screen.

Run from the repo root, the made-up games' library made first (tools/made-up-games/README.md):

    python tools/console-models/arcade_print.py <card> artifacts/made-up-games artifacts/arcade
    blender -b --factory-startup --python tools/console-models/arcade.py -- artifacts/arcade <card> godot/themes/console/models/systems/<card>.glb
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcade_layout as L  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from clip import HIDDEN, Pose, back_out, ease_in, key, phase, smooth  # noqa: E402
from mega_drive import prism_z  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, export, join, material, prism_x, triangles  # noqa: E402

TILT_YAW = -28.0     # degrees about the vertical: the right side comes towards the viewer
TILT_PITCH = 12.0    # degrees about the horizontal: seen a little from above
ROUGHNESS = dict(print=0.45, side=0.4, glass=0.1, gloss=0.25, dark=0.7)


def atlas_uv(region, w, h, size=L.PRINT_ATLAS):
    rx, ry, rw, rh = region
    return lambda a, b: ((rx + a / w * rw) / size, 1 - (ry + b / h * rh) / size)


def swatch(name):
    x, y = L.SWATCHES[name]
    return lambda co: (x / L.PRINT_ATLAS, 1 - y / L.PRINT_ATLAS)


def painted(obj, m, name, mat="print"):
    paint(obj, m[mat], swatch(name), lambda c, n, _name: True)
    return obj


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def slope_frame(foot, top):
    """A face's frame on its slope: the origin at its foot, x across, s up the slope to its top, h out of it."""
    (y0, z0), (y1, z1) = foot, top
    return Matrix.Translation((0.0, y0, z0)) @ Matrix.Rotation(math.atan2(z1 - z0, y1 - y0), 4, "X")


def in_frame(name, frame, outline, h0, h1, mat):
    """A solid from an (x, s) outline in a frame, from h0 to h1 off it."""
    return solid(name, [[frame @ Vector((x, s, h)) for x, s in outline] for h in (h0, h1)], mat)


def span_uv(region, span, width):
    """UVs for a face along a span ((top), (foot), each (y, z)), width across: across from its left; down it."""
    (y0, z0), (y1, z1) = span
    length = math.hypot(y1 - y0, z1 - z0)
    uv = atlas_uv(region, width, length)

    def of(co):
        b = ((co.y - y0) * (y1 - y0) + (co.z - z0) * (z1 - z0)) / length
        return uv(co.x + width / 2, b)
    return of


def on_span(c, n, span, slack=2.0):
    """Whether a face (its centre c, its normal n) lies on a span ((y, z) to (y, z)), not a side."""
    (y0, z0), (y1, z1) = span
    dy, dz = y1 - y0, z1 - z0
    length = math.hypot(dy, dz)
    along = ((c.y - y0) * dy + (c.z - z0) * dz) / length
    off = abs((c.y - y0) * dz - (c.z - z0) * dy) / length
    return -slack < along < length + slack and off < slack and abs(n.x) < 0.5


# ---- The cabinet -----------------------------------------------------------------------------------------------------

def cabinet(m, cab, card):
    """The body and its printed faces, the screen's recess, the side panels or printed sides, the kick plate, the CRT's
    glass. Returns the parts and the bezel's frame."""
    w = L.inner_width(cab)
    candy = cab["kind"] in ("candy", "driver")
    half = w / 2 - (0.0 if candy else 0.5)
    body = prism_x("cabinet", cab["body"], -half, half, m["print"])
    if candy:
        bevel(body, cab.get("round", 10.0), segments=3, angle=30.0)
    bezel_frame = slope_frame(*cab["bezel"])
    (x0, x1), (s0, s1) = L.recess(cab, card)
    s = cab["screen"]
    recess = in_frame("recess", bezel_frame, rounded(0.0, (s0 + s1) / 2, x1 - x0, s1 - s0, 14.0, 4), -s["depth"],
                      60.0, m["dark"])
    boolean(body, recess)
    if "screen2" in cab:                                   # a twin-monitor cabinet's top monitor
        s2 = cab["screen2"]
        frame2 = slope_frame(*s2["span"])
        gw2, gh2 = s2["glass"]
        m2 = s2["margin"]
        boolean(body, in_frame("recess2", frame2, rounded(0.0, s2["middle"], gw2 + 2 * m2, gh2 + 2 * m2, 10.0, 4),
                               -s2["depth"], 60.0, m["dark"]))
    paint(body, m["print"], swatch("case"), lambda c, n, kind: kind != "dark")
    for name in ("marquee", "speakers"):
        if name in cab:
            span = cab[name]
            paint(body, m["gloss" if name == "marquee" else "print"], span_uv(L.PRINT_REGIONS[name], span, w),
                  lambda c, n, kind, span=span: kind != "dark" and on_span(c, n, span))
    foot, top = cab["bezel"]
    paint(body, m["print"], span_uv(L.PRINT_REGIONS["bezel"], (top, foot), w),
          lambda c, n, kind: kind != "dark" and on_span(c, n, (foot, top)))
    for span, name in cab.get("spans", ()):
        paint(body, m["print"], swatch(name), lambda c, n, kind, span=span: kind != "dark" and on_span(c, n, span))
    lower = cab["lower"]
    lz = lower[1][1]
    front = atlas_uv(L.PRINT_REGIONS["front"], w, lz)
    paint(body, m["print"], lambda co: front(co.x + w / 2, lz - co.z),
          lambda c, n, kind: kind != "dark" and on_span(c, n, lower))
    lo_y, hi_y, hi_z = L.side_bounds(cab)

    def side_uv(co):
        return ((co.y - lo_y) / (hi_y - lo_y), co.z / hi_z)
    parts = [body]
    if candy:
        paint(body, m["side"], side_uv, lambda c, n, kind: kind != "dark" and abs(n.x) > 0.9)
    else:
        t = cab["side"]
        for sign in (-1, 1):
            a, b = sorted((sign * w / 2, sign * (w / 2 + t)))
            panel = prism_x("side", cab["outline"], a, b, m["side"])
            bevel(panel, 4.0, segments=2, angle=30.0)
            painted(panel, m, "moulding")
            paint(panel, m["side"], side_uv, lambda c, n, kind, sign=sign: n.x * sign > 0.9)
            paint(panel, m["print"], swatch("case"), lambda c, n, kind, sign=sign: n.x * sign < -0.9)
            parts.append(panel)

    ly = lower[0][0]
    k0, k1 = cab["kick"]
    parts.append(painted(box("kick", -w / 2 + 2.0, w / 2 - 2.0, ly - 3.0, ly + 1.0, k0, k1, m["print"]), m, "kick"))
    gw, gh = L.glass(cab, card)
    glass = curved("glass", gw, gh, s["bulge"], media_uv("boot"), m["glass"], 12, 9)
    glass.data.transform(Matrix.Translation(bezel_frame @ Vector((0.0, s["middle"], -s["depth"] + 16.0))) @
                         glass_turn(cab))
    parts.append(glass)
    if "screen2" in cab:
        menu = curved("glass2", gw2, gh2, s2["bulge"], media_uv("menu"), m["glass"], 10, 8)
        menu.data.transform(Matrix.Translation(frame2 @ Vector((0.0, s2["middle"], -s2["depth"] + 12.0))) @
                            glass_turn(cab, s2["span"]))
        parts.append(menu)
    return parts, bezel_frame


def glass_turn(cab, span=None):
    """A screen facing -y, turned onto the bezel's slope (or another span's)."""
    (y0, z0), (y1, z1) = span or cab["bezel"]
    return Matrix.Rotation(math.atan2(z1 - z0, y1 - y0) - math.pi / 2, 4, "X")


def media_uv(name):
    x, y, w, h = MEDIA[name]
    mw, mh = MEDIA["size"]
    return lambda a, b: ((x + a * w) / mw, 1 - (y + b * h) / mh)


def tops(m, cab):
    """The boxes standing on the cabinet, their fronts printed: a marquee's lightbox, speakers (one print across them
    all), a POP sign."""
    parts = []
    for k, t in enumerate(cab.get("tops", ())):
        (x0, x1), (y0, y1), (z0, z1) = t["x"], t["y"], t["z"]
        part = box(f"top{k}", x0, x1, y0, y1, z0, z1, m["print"])
        if t.get("r"):
            bevel(part, t["r"], segments=2, angle=30.0)
        painted(part, m, t.get("colour", "case"))
        face = t.get("face")
        if face == "speakers":
            uv = atlas_uv(L.PRINT_REGIONS[face], cab["width"], z1 - z0)
            paint(part, m["print"], lambda co, z1=z1, uv=uv: uv(co.x + cab["width"] / 2, z1 - co.z),
                  lambda c, n, kind: n.y < -0.9)
        elif face:
            uv = atlas_uv(L.PRINT_REGIONS[face], x1 - x0, z1 - z0)
            paint(part, m["gloss" if face == "marquee" else "print"],
                  lambda co, x0=x0, z1=z1, uv=uv: uv(co.x - x0, z1 - co.z), lambda c, n, kind: n.y < -0.9)
        parts.append(part)
    return parts


# ---- The control panel -----------------------------------------------------------------------------------------------

def plan(p, depth):
    """The control panel's plan (x, y), anticlockwise from above: its front corners cut, or rounded."""
    w = p["width"]
    back = [(w / 2 + 1.0, depth), (-w / 2 - 1.0, depth)]
    if "round" in p:
        r = p["round"]
        front = []
        for cx, a0 in ((-w / 2 + r, 180.0), (w / 2 - r, 270.0)):
            front += [(cx + r * math.cos(math.radians(a0 + 90.0 * k / 8)),
                       r + r * math.sin(math.radians(a0 + 90.0 * k / 8))) for k in range(9)]
        return back + front
    c = p["corner"]
    return back + [(-w / 2 - 1.0, c), (-w / 2 + c, -1.0), (w / 2 - c, -1.0), (w / 2 + 1.0, c)]


def control_panel(m, cab):
    """The control panel's box: its side profile across its width, its plan's front corners cut or rounded; its top
    printed, its front a strip."""
    p = cab["panel"]
    (y0, z0), (y1, z1) = p["top"]
    profile = [(y0, p["front"]), (y1 + 40.0, p["front"] + 30.0), (y1 + 40.0, z1), (y1, z1), (y0, z0)]
    w = p["width"]
    part = prism_x("panel", profile, -w / 2, w / 2, m["print"])
    boolean(part, prism_z("plan", plan(p, y1 + 50.0), p["front"] - 10.0, z1 + 10.0, m["print"]), "INTERSECT")
    bevel(part, 3.0, segments=2, angle=30.0)
    painted(part, m, "panel_edge")
    frame = panel_frame(cab)
    d = p["back"]
    uv = atlas_uv(L.PRINT_REGIONS["panel"], w, d)
    inv = frame.inverted()
    up = frame.to_3x3() @ Vector((0, 0, 1))
    paint(part, m["print"], lambda co: (lambda q: uv(q.x + w / 2, d - q.y))(inv @ co),
          lambda c, n, kind: up.dot(n) > 0.95)
    if p.get("strip"):
        sh = z0 - p["front"]
        strip = atlas_uv(L.PRINT_REGIONS["strip"], w, sh)
        paint(part, m["print"], lambda co: strip(co.x + w / 2, z0 - co.z),
              lambda c, n, kind: n.y < -0.2 and n.z < 0.5 and p["front"] + 1.0 < c.z < z0 - 1.0)
    return part


def panel_frame(cab):
    (y0, z0), (y1, z1) = cab["panel"]["top"]
    return Matrix.Translation((0.0, y0, z0)) @ Matrix.Rotation(math.atan2(z1 - z0, y1 - y0), 4, "X")


def button(name, x, v, colour, m, cab, frame):
    r, h = cab["button"]["r"], cab["button"]["height"]
    part = in_frame(name, frame, circle(x, v, r, 24), -2.0, h, m["gloss"])
    bevel(part, 1.6, segments=2)
    return painted(part, m, colour, "gloss")


def stick(m, cab):
    """A joystick, its foot at its origin: the shaft and the ball top."""
    r, length = cab["sticks"]["shaft"]
    shaft = painted(solid("shaft", [[(x, y, z) for x, y in circle(0.0, 0.0, r, 12)] for z in (-2.0, length)],
                          m["gloss"]), m, "stick", "gloss")
    br = cab["sticks"]["ball"]
    ball = solid("ball", [[(br * math.cos(math.radians(lat)) * math.cos(2 * math.pi * k / 20),
                            br * math.cos(math.radians(lat)) * math.sin(2 * math.pi * k / 20),
                            length + br * 0.8 + br * math.sin(math.radians(lat))) for k in range(20)]
                          for lat in range(-80, 81, 20)], m["gloss"])
    for poly in ball.data.polygons:
        poly.use_smooth = True
    return shaft, ball


def button_colours(card):
    n = card.get("n_buttons", 6)
    return {6: ["b1", "b1", "b1", "b2", "b2", "b2"], 4: ["b1", "b2", "b3", "b1"], 3: ["b1", "b2", "b3"],
            2: ["b1", "b2"], 1: ["b1"]}[n]


def controls(m, cab, card):
    """The control panel's fixed parts: 1P's buttons but the two the clip presses, 2P's stick, buttons and START."""
    frame = panel_frame(cab)
    colours = button_colours(card)
    parts = []
    for player, spots in L.buttons(cab, card).items():
        for k, (x, v) in enumerate(spots):
            if player == "p1" and k in (0, 1):
                continue
            parts.append(button(player, x, v, colours[k], m, cab, frame))
    for x, v in cab["start"][1:]:
        parts.append(button("start2", x, v, "start", m, cab, frame))
    for x, v in cab.get("more_buttons", ()):                # a second fire button, the other side of the stick
        parts.append(button("more", x, v, colours[0], m, cab, frame))
    for k, (x, v) in enumerate(cab.get("views", ())):       # a driving cabinet's view buttons
        parts.append(button("view", x, v, ("b1", "b2", "b3", "b4")[k % 4], m, cab, frame))
    if "p2" in cab.get("sticks", {}):
        shaft, ball = stick(m, cab)
        paint(ball, m["gloss"], swatch("ball2"), lambda c, n, name: True)
        for part in (shaft, ball):
            part.data.transform(frame @ Matrix.Translation((*cab["sticks"]["p2"], 0.0)))
            parts.append(part)
    return parts


def coin_door(m, cab):
    """The coin door on the lower front: the metal door, its coin entries (their slots lit red) and the coin returns.
    Returns the parts and where the left slot is."""
    c = cab["coin"]
    ly = cab["lower"][0][0]
    (x0, x1), (z0, z1) = c["x"], c["z"]
    door = box("coin_door", x0, x1, ly - 5.0, ly + 1.0, z0, z1, m["print"])
    bevel(door, 2.0, segments=2)
    painted(door, m, "metal")
    parts = [door]
    slot = None
    entries = (0.3, 0.7) if x1 - x0 > 180.0 else (0.5,)
    for k, f in enumerate(entries):
        cx = x0 + (x1 - x0) * f
        ez = z1 - 90.0
        entry = box("entry", cx - 22.0, cx + 22.0, ly - 12.0, ly - 4.0, ez - 40.0, ez + 40.0, m["print"])
        bevel(entry, 1.5, segments=1)
        painted(entry, m, "black")
        lit = painted(box("slot", cx - 4.0, cx + 4.0, ly - 12.6, ly - 11.9, ez - 26.0, ez + 26.0, m["gloss"]), m,
                      "red_lit", "gloss")
        ret = painted(box("return", cx - 18.0, cx + 18.0, ly - 9.0, ly - 4.0, ez - 120.0, ez - 80.0, m["print"]), m,
                      "black")
        parts += [entry, lit, ret]
        if k == 0:
            slot = Vector((cx, ly - 13.0, ez))
    return parts, slot


def coin_plate(m, cab):
    """The coin plate on the control panel: a metal plate, its slot. Returns it and where the slot is."""
    c = cab["coin"]
    frame = panel_frame(cab)
    cx, cv = c["at"]
    pw, pd = c["plate"]
    plate = painted(in_frame("coin_plate", frame, rounded(cx, cv, pw, pd, 5.0, 3), -1.0, 4.0, m["print"]), m, "metal")
    sw, sd = c["slot"]
    boolean(plate, in_frame("slot", frame, [(cx - sw / 2, cv - sd / 2), (cx + sw / 2, cv - sd / 2),
                                            (cx + sw / 2, cv + sd / 2), (cx - sw / 2, cv + sd / 2)], 1.0, 8.0,
                            m["dark"]))
    return [plate], frame @ Vector((cx, cv, 4.0))


# ---- A driving cabinet -----------------------------------------------------------------------------------------------

def seat_and_base(m, cab):
    """A driving cabinet's base, the seat on its own base (its cushion; its back leaning back, its decal on its back,
    bolsters at its sides if it is a bucket seat), the pedals."""
    b = cab["base"]
    (y0, y1), (z0, z1), w = b["y"], b["z"], b["width"]
    base = box("base", -w / 2, w / 2, y0, y1, z0, z1, m["print"])
    bevel(base, 4.0, segments=2, angle=30.0)
    painted(base, m, "base")
    st = cab["seat"]
    sw = st["width"]
    sy0, sy1, sz0, sz1 = st["base"]
    seat_base = box("seat_base", -sw / 2 + 20.0, sw / 2 - 20.0, sy0, sy1, sz0, sz1, m["print"])
    bevel(seat_base, 6.0, segments=2, angle=30.0)
    painted(seat_base, m, "base")
    cy0, cy1, cz0, cz1 = st["cushion"]
    cushion = box("cushion", -sw / 2 + 30.0, sw / 2 - 30.0, cy0, cy1, cz0, cz1, m["print"])
    bevel(cushion, 28.0, segments=3, angle=30.0)
    painted(cushion, m, "seat2")
    by, bz0, bz1, t, tilt = st["back"]
    h = bz1 - bz0
    back = box("seat_back", -sw / 2, sw / 2, -t / 2, t / 2, 0.0, h, m["print"])
    if st.get("bolsters"):                                 # a bucket seat's high sides
        for sign in (-1, 1):
            a, c = sorted((sign * (sw / 2 - 50.0), sign * sw / 2))
            back = join([back, box("bolster", a, c, -t / 2, t / 2 + 150.0, h * 0.08, h * 0.86, m["print"])],
                        "seat_back")
    bevel(back, 22.0, segments=3, angle=30.0)
    painted(back, m, "seat")
    paint(back, m["print"], swatch("seat2"), lambda c, n, kind: n.y > 0.9 and abs(c.x) < sw / 2 - 52.0)
    decal = atlas_uv(L.PRINT_REGIONS["pop"], sw, h)
    paint(back, m["print"], lambda co: decal(co.x + sw / 2, h - co.z), lambda c, n, kind: n.y < -0.9)
    back.data.transform(Matrix.Translation((0.0, by, bz0)) @ Matrix.Rotation(math.radians(tilt), 4, "X"))
    parts = [base, seat_base, cushion, back]
    for x, y in cab["pedals"]:
        pedal = painted(box("pedal", x - 34.0, x + 34.0, -6.0, 6.0, 0.0, 120.0, m["print"]), m, "pedal")
        pedal.data.transform(Matrix.Translation((0.0, y, z1)) @ Matrix.Rotation(math.radians(-50.0), 4, "X"))
        parts.append(pedal)
    return parts


def wheel(m, cab):
    """The steering wheel about its hub, facing -y: the rim, its spokes, the hub, the column behind it."""
    wl = cab["wheel"]
    bpy.ops.mesh.primitive_torus_add(major_radius=wl["r"], minor_radius=wl["tube"], major_segments=28,
                                     minor_segments=8)
    rim = bpy.context.active_object
    rim.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))     # its axis along y, the rim upright
    rim.data.materials.append(m["print"])
    parts = [painted(rim, m, "rubber")]
    for a in wl["spokes"]:
        spoke = painted(box("spoke", wl["hub_r"] - 10.0, wl["r"] - 4.0, -7.0, 7.0, -15.0, 15.0, m["print"]), m,
                        "chrome")
        spoke.data.transform(Matrix.Rotation(math.radians(-a), 4, "Y"))
        parts.append(spoke)
    hub = solid("hub", [[(x, y, z) for x, z in circle(0.0, 0.0, wl["hub_r"], 20)] for y in (-14.0, 10.0)], m["print"])
    parts.append(painted(hub, m, "b1"))
    column = solid("column", [[(x, y, z) for x, z in circle(0.0, 0.0, 22.0, 12)] for y in (8.0, 190.0)], m["print"])
    parts.append(painted(column, m, "rubber"))
    part = join(parts, "wheel")
    for poly in part.data.polygons:
        poly.use_smooth = True
    return part


def shifter(m, cab):
    """The shifter, its foot at its origin: the lever and its knob."""
    length = cab["shifter"]["length"]
    lever = painted(solid("lever", [[(x, y, z) for x, y in circle(0.0, 0.0, 7.0, 10)] for z in (-2.0, length)],
                          m["print"]), m, "chrome")
    knob = solid("knob", [[(24.0 * math.cos(math.radians(lat)) * math.cos(2 * math.pi * k / 16),
                            24.0 * math.cos(math.radians(lat)) * math.sin(2 * math.pi * k / 16),
                            length + 20.0 + 24.0 * math.sin(math.radians(lat))) for k in range(16)]
                          for lat in range(-75, 76, 25)], m["print"])
    part = join([lever, painted(knob, m, "rubber")], "shifter")
    for poly in part.data.polygons:
        poly.use_smooth = True
    return part


# ---- The moving parts ------------------------------------------------------------------------------------------------

def moving(m, cab, card, slot):
    """The 1P stick, its first two buttons, 1P START and its light, the coin; each its origin where it moves from."""
    frame = panel_frame(cab)
    parts = {}
    origin = frame @ Vector((0.0, 0.0, 0.0))
    if "sticks" in cab:
        shaft, ball = stick(m, cab)
        lever = join([shaft, ball], "stick")
        paint(lever, m["gloss"], swatch("ball1"), lambda c, n, name: c.z > cab["sticks"]["shaft"][1] - 1.0)
        lever.data.transform(frame.to_3x3().to_4x4())
        parts["stick"] = (lever, frame @ Vector((*cab["sticks"]["p1"], 0.0)))
    if "shifter" in cab:
        lever = shifter(m, cab)
        lever.data.transform(frame.to_3x3().to_4x4())
        parts["shifter"] = (lever, frame @ Vector((*cab["shifter"]["at"], 0.0)))
    colours = button_colours(card)
    spots = L.buttons(cab, card).get("p1", [])
    for k in (0, 1):
        if k >= len(spots):
            continue
        x, v = spots[k]
        b = button(f"button{k + 1}", 0.0, 0.0, colours[k], m, cab, frame)
        b.data.transform(Matrix.Translation(-origin))
        parts[f"button{k + 1}"] = (b, frame @ Vector((x, v, 0.0)))
    x, v = cab["start"][0]
    start = button("start", 0.0, 0.0, "start", m, cab, frame)
    start.data.transform(Matrix.Translation(-origin))
    parts["start"] = (start, frame @ Vector((x, v, 0.0)))
    lit = button("start_light", 0.0, 0.0, "start_lit", m, cab, frame)
    lit.data.transform(Matrix.Translation(-origin))
    lit.data.transform(Matrix.Scale(1.04, 4))
    parts["start_light"] = (lit, frame @ Vector((x, v, 0.4)))
    coin = painted(solid("coin", [[(xx, yy, zz) for xx, zz in circle(0.0, 0.0, 11.0, 20)] for yy in (-1.0, 1.0)],
                         m["print"]), m, "coin")
    coin.data.transform(Matrix.Rotation(math.radians(90.0), 4, "Z"))     # on edge, its face across the slot
    parts["coin"] = (coin, slot)
    return parts


def screens(m, cab, card, bezel_frame):
    s = cab["screen"]
    gw, gh = L.glass(cab, card)
    out = {}
    for k, name in enumerate(("title", "game1", "game2")):
        part = curved("screen_" + name, gw, gh, s["bulge"], media_uv(name), m["glass"], 12, 9)
        part.data.transform(glass_turn(cab))
        out["screen_" + name] = (part, bezel_frame @ Vector((0.0, s["middle"], -s["depth"] + 16.6 + 0.3 * k)))
    if "screen2" in cab:                                   # the top monitor's second screen: the game chosen
        s2 = cab["screen2"]
        part = curved("screen2_menu2", *s2["glass"], s2["bulge"], media_uv("menu2"), m["glass"], 10, 8)
        part.data.transform(glass_turn(cab, s2["span"]))
        out["screen2_menu2"] = (part, slope_frame(*s2["span"]) @ Vector((0.0, s2["middle"], -s2["depth"] + 12.6)))
    return out


# ---- The focused clip ------------------------------------------------------------------------------------------------

def tap(f, f0, hold=2):
    return smooth(phase(f, f0, f0 + 2)) * (1 - smooth(phase(f, f0 + 2 + hold, f0 + 5 + hold)))


def showing(f):
    """The screen shown at frame f: the title, then two frames of play in turn; None for the start-up's."""
    if 30 <= f < 64:
        return "title"
    if 64 <= f < 200:
        return "game1" if ((f - 64) // 7) % 2 == 0 else "game2"
    return None


def timeline(press, plate, f):
    poses = {}
    if f < 8 or f >= 30:
        poses["coin"] = Pose(scale=HIDDEN)
    elif plate:                                            # it drops into the plate's slot
        t = back_out(phase(f, 8, 14))
        poses["coin"] = (Pose(z=40.0, scale=HIDDEN + (1 - HIDDEN) * t) if f < 16 else
                         Pose(z=40.0 - 52.0 * ease_in(phase(f, 16, 26))))
    elif f < 16:
        poses["coin"] = Pose(y=-40.0, scale=HIDDEN + (1 - HIDDEN) * back_out(phase(f, 8, 14)))
    else:                                                  # it slides into the door's slot
        poses["coin"] = Pose(y=-40.0 + 52.0 * ease_in(phase(f, 16, 28)))
    # A screen stays up a frame after the next comes up: shrunk to hide, a screen sinks behind the CRT's bulge, so
    # between two keys (the app draws the clip at 60 fps) the start-up would show through.
    on = (showing(f), showing(f - 1))
    for name in ("title", "game1", "game2"):
        poses["screen_" + name] = Pose() if name in on else Pose(scale=HIDDEN)
    flash = 30 <= f < 60 and (f // 6) % 2 == 0
    poses["start_light"] = Pose() if flash else Pose(scale=HIDDEN)
    poses["start"] = Pose(*(press * 3.0 * tap(f, 58)))
    for k, frames in ((1, (80, 96, 112, 140, 168)), (2, (88, 120, 150, 176))):
        poses[f"button{k}"] = Pose(*(press * 3.0 * max(tap(f, f0) for f0 in frames)))
    t = phase(f, 70, 190)
    poses["stick"] = Pose(pitch=14.0 * math.sin(2 * math.pi * 3 * t) * math.sin(math.pi * t),
                          roll=18.0 * math.sin(2 * math.pi * 5 * t) * math.sin(math.pi * t))
    poses["wheel"] = Pose(roll=70.0 * math.sin(2 * math.pi * 2 * t) * math.sin(math.pi * t))     # round the bends
    poses["shifter"] = Pose(pitch=-16.0 * (smooth(phase(f, 86, 91)) - smooth(phase(f, 168, 173))))  # up a gear, down
    poses["screen2_menu2"] = Pose() if 30 <= f < 200 else Pose(scale=HIDDEN)
    return poses


# ---- Main ------------------------------------------------------------------------------------------------------------

MEDIA = {}


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, card_id, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    card = dict(L.CARDS[card_id], id=card_id)
    cab = L.CABINETS[card["cabinet"]]
    MEDIA.update(L.media_regions(card), size=L.media_size(card))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = L.FPS
    files = dict(print=f"{card_id}_print.png", side=f"{card_id}_side.jpg", media=f"{card_id}_media.jpg")
    textures = {name: bpy.data.images.load(os.path.join(images, files[kind]))
                for name, kind in (("print", "print"), ("gloss", "print"), ("side", "side"), ("glass", "media"))}
    m = {name: material(name, "#060607" if name == "dark" else "#FFFFFF", r, textures.get(name))
         for name, r in ROUGHNESS.items()}

    parts, bezel_frame = cabinet(m, cab, card)
    plate = cab["coin"]["kind"] == "plate"
    coin, slot = coin_plate(m, cab) if plate else coin_door(m, cab)
    seat = seat_and_base(m, cab) if cab["kind"] == "driver" else []
    whole = join(parts + tops(m, cab) + [control_panel(m, cab)] + controls(m, cab, card) + coin + seat, card_id)
    for poly in whole.data.polygons:
        poly.use_smooth = True
    whole.data.set_sharp_from_angle(angle=math.radians(35))
    nodes_parts = moving(m, cab, card, slot)
    nodes_parts.update(screens(m, cab, card, bezel_frame))

    root = bpy.data.objects.new(card_id + "_root", None)
    scene.collection.objects.link(root)
    whole.parent = root
    for name, (part, where) in nodes_parts.items():
        part.parent = whole
        part.location = where
    nodes = {name: part for name, (part, _) in nodes_parts.items()}
    holders = []
    if "wheel" in cab:                                     # the wheel turns about its column, held at its tilt
        column = bpy.data.objects.new("wheel_column", None)
        scene.collection.objects.link(column)
        column.parent = whole
        column.location = cab["wheel"]["hub"]
        column.rotation_euler = (math.radians(-cab["wheel"]["tilt"]), 0.0, 0.0)
        nodes["wheel"] = wheel(m, cab)
        nodes["wheel"].parent = column
        holders.append(column)

    yaw, pitch = cab.get("yaw", TILT_YAW), cab.get("pitch", TILT_PITCH)
    tilt = Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    points = [tilt @ v.co for v in whole.data.vertices]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    size = hi - lo
    root.matrix_world = Matrix.Scale(1 / max(size), 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2,
                                                                             -lo.z)) @ tilt

    press = panel_frame(cab).to_3x3() @ Vector((0.0, 0.0, -1.0))
    key("focused", nodes, lambda f: {k: v for k, v in timeline(press, plate, f).items() if k in nodes}, L.LENGTH)
    meshes = [whole] + list(nodes.values())
    print(f"{card_id}: {sum(triangles(o.data) for o in meshes)} triangles ({triangles(whole.data)} the set), "
          f"{len({mat.name for o in meshes for mat in o.data.materials})} materials, "
          f"size {size.x:.1f} x {size.y:.1f} x {size.z:.1f} mm tilted, before the fit")
    export([root] + holders + meshes, out, animations=True)


if __name__ == "__main__":
    main()
