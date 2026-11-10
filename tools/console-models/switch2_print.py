"""The Nintendo Switch 2's printing and screens, for the console theme's Switch 2 model (switch2.py) and its video
(switch2_video.py). switch2_layout.py has the measurements and where each part is in the atlases.

Writes three images into a folder:
- switch2_print.png: the face seen square on, with both Joy-Con 2 (the console's frame round the black glass; the
  Joy-Con 2's faces, the seams between them and the console and round L and R; the buttons' tops and their legends:
  X, A, B and Y, the direction buttons' arrows, + and -, HOME's house, C, the capture button's circle; the sticks'
  caps and their notches); the top edge seen from above (POWER, VOLUME - and +, the microphones, a screw, the three
  vents, USB-C, the headphone jack and its mark, the GAME CARD flap); the bottom edge seen from below (the speakers'
  grilles, USB-C, the holes and the screws); and the swatches small parts take their colour from.
- switch2_rear.png: the back seen from behind (the console's back: the Nintendo Switch 2 logo in a lighter grey, the
  kickstand's recess, a made-up label, the screws; the Joy-Con 2's backs: Nintendo's name in its oval, the release
  buttons); each Joy-Con 2's inner side (its tongue in blue or red: SL and SR, the mouse sensor, the connector, the
  SYNC button); the console's ends (the channels' floors in blue and red, their connectors); and swatches.
- switch2_screen.png: the glass with the LCD switched off: the still of the model's `video` material, and the first
  and last frame of the card's video.

The screens the video shows are drawn here too, laid out in the LCD's own 1920 x 1080 pixels at five sixths of them
(twice the video's picture), then halved: the HOME Menu as Nintendo's basic white theme lays it out (drawn anew:
made-up software, made-up icons, no Nintendo artwork), its mouse cursor (a black arrow, as in Nintendo's own
screenshot), the game's title and its street. The game is made up (no real game's art): Dusty Gulch, Ninebolt's
light-gun game from tools/made-up-games (its logo from the made-up games' library), remade in HD for this card: its key
art, its empty street, its outlaws and its props painted by Codex (paintings.py: sw2_gulch_keyart, sw2_gulch_street,
sw2_gulch_outlaws, sw2_gulch_props), the figures cut out of their green (psvita_print.poses()) and placed in the
street, the barrel, the window's railing and the porch in front of them cut back out of the street's painting.

Make the made-up games' library and the paintings first (tools/made-up-games/README.md; paintings.py), then run it
with the system Python (Pillow, numpy, scipy):

    python tools/console-models/switch2_print.py artifacts/made-up-games artifacts/switch2
"""

import math
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch2_layout as L  # noqa: E402
from arcade_print import painting  # noqa: E402
from psp_print import Canvas, font, paste_region, rgb  # noqa: E402
from psvita_print import poses  # noqa: E402

C = L.COLOURS
WHITE = (255, 255, 255)


def jc(side, u, z):
    """A point on a Joy-Con 2's face, u out from its inner edge: on the right one (side 1) or the left (-1)."""
    return side * (L.HALF + u), z


def offset_line(points, d):
    """A polyline moved d to its left (inwards, for an outline running anticlockwise)."""
    out = []
    for i, (x, z) in enumerate(points):
        (xa, za), (xb, zb) = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
        length = math.hypot(xb - xa, zb - za) or 1.0
        out.append((x - (zb - za) / length * d, z + (xb - xa) / length * d))
    return out


def outline(side):
    return [jc(side, u, z) for u, z in L.joycon_outline()]


def shoulder_line(side, inset=1.0):
    """The seam round R (or L): the outline from SHOULDER_FROM's second point (down the outer side) round the top to
    its first, moved inwards."""
    u0, z1 = L.SHOULDER_FROM
    run = [p for p in L.joycon_outline() if p[1] >= z1 and p[0] >= u0 - 0.01]
    return [jc(side, u, z) for u, z in offset_line(run, inset)]


# ---- The face ----------------------------------------------------------------------------------------------------------

def stick_cap(c, x, z):
    """A stick's cap seen from the front: dark, its rim a little lighter, four notches round its dish."""
    s = L.STICK
    c.circle(x, z, s["cap"] + 0.15, rgb(C["cap"], 0.8))
    c.circle(x, z, s["cap"], rgb("#2E3033"))
    c.circle(x, z, s["cap"] - 0.9, rgb(C["cap"]))
    c.circle(x, z, s["cap"] - 2.4, rgb(C["cap"], 0.92))
    for a in (0, 90, 180, 270):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        c.line([(x + 5.2 * ca, z + 5.2 * sa), (x + 6.3 * ca, z + 6.3 * sa)], 0.35, rgb("#44474C"))


def face_button(c, x, z, r=None):
    r = r or L.ABXY["r"]
    c.circle(x, z, r + 0.12, rgb(C["seam"]))
    c.circle(x, z, r, rgb(C["button"]))
    c.circle(x, z - 0.25, r - 0.6, rgb(C["button"], 1.08))


def triangle(c, x, z, degrees, size, fill):
    pts = []
    for k in range(3):
        a = math.radians(degrees + 120 * k)
        pts.append((x + size * math.cos(a), z + size * math.sin(a)))
    c.polygon(pts, fill)


def house(c, x, z, s, fill, ground):
    c.polygon([(x - 1.5 * s, z - 1.3 * s), (x + 1.5 * s, z - 1.3 * s), (x + 1.5 * s, z + 0.3 * s), (x, z + 1.65 * s),
               (x - 1.5 * s, z + 0.3 * s)], fill)
    c.rounded(x - 0.42 * s, x + 0.42 * s, z - 1.3 * s, z - 0.25 * s, 0.1, ground)


def joycon_face(c, side):
    """A Joy-Con 2's face: its body, the seams, and the tops of its buttons and its stick."""
    c.polygon(outline(side), rgb(C["body"]))
    c.line([(side * L.HALF, 0.2), (side * L.HALF, L.JOYCON["height"] - 0.2)], 0.45, rgb(C["seam"]))
    c.line(shoulder_line(side), 0.32, rgb(C["seam"]))
    stick = L.STICK_R if side > 0 else L.STICK_L
    x, z = jc(side, *stick)
    c.circle(x, z, L.STICK["ring"][1], rgb(C["ring_coral" if side > 0 else "ring_blue"]))
    c.circle(x, z, L.STICK["ring"][0], rgb(C["cap"], 0.7))
    stick_cap(c, x, z)
    legend = rgb(C["legend"])
    if side > 0:
        a = L.ABXY
        for name, degrees in L.FACE_BUTTONS:
            bx, bz = jc(side, a["centre"][0] + a["reach"] * math.cos(math.radians(degrees)),
                        a["centre"][1] + a["reach"] * math.sin(math.radians(degrees)))
            face_button(c, bx, bz)
            c.text(name.upper(), "segoeui.ttf", 3.1, bx, bz, legend)
        p = L.PLUS
        px, pz = jc(side, *p["at"])
        for w, h in ((p["length"], p["width"]), (p["width"], p["length"])):
            c.rounded(px - w / 2 - 0.12, px + w / 2 + 0.12, pz - h / 2 - 0.12, pz + h / 2 + 0.12, 0.35, rgb(C["seam"]))
        for w, h in ((p["length"], p["width"]), (p["width"], p["length"])):
            c.rounded(px - w / 2, px + w / 2, pz - h / 2, pz + h / 2, 0.3, rgb(C["button"]))
        hx, hz = jc(side, *L.HOME["at"])
        face_button(c, hx, hz, L.HOME["r"])
        house(c, hx, hz, 0.95, rgb("#111214"), rgb(C["button"]))
        cb = L.C_BUTTON
        bx, bz = jc(side, *cb["at"])
        h = cb["size"] / 2
        c.rounded(bx - h - 0.12, bx + h + 0.12, bz - h - 0.12, bz + h + 0.12, cb["r"], rgb(C["seam"]))
        c.rounded(bx - h, bx + h, bz - h, bz + h, cb["r"], rgb(C["button"]))
        c.text("C", "segoeuib.ttf", 2.9, bx, bz, rgb("#111214"))
        return
    d = L.DPAD
    for name, degrees in L.FACE_BUTTONS:
        a = math.radians(degrees)
        bx, bz = jc(side, d["centre"][0] + d["reach"] * math.cos(a), d["centre"][1] + d["reach"] * math.sin(a))
        face_button(c, bx, bz)
        out = {"x": 90.0, "b": 270.0, "a": 180.0, "y": 0.0}[name]     # mirrored: "a" (out) points left on the left
        triangle(c, bx, bz, out, 1.25, rgb("#111214"))
    m = L.MINUS
    mx, mz = jc(side, *m["at"])
    c.rounded(mx - m["length"] / 2 - 0.12, mx + m["length"] / 2 + 0.12, mz - m["width"] / 2 - 0.12,
              mz + m["width"] / 2 + 0.12, 0.35, rgb(C["seam"]))
    c.rounded(mx - m["length"] / 2, mx + m["length"] / 2, mz - m["width"] / 2, mz + m["width"] / 2, 0.3, rgb(C["button"]))
    cp = L.CAPTURE
    bx, bz = jc(side, *cp["at"])
    h = cp["size"] / 2
    c.rounded(bx - h - 0.12, bx + h + 0.12, bz - h - 0.12, bz + h + 0.12, cp["r"], rgb(C["seam"]))
    c.rounded(bx - h, bx + h, bz - h, bz + h, cp["r"], rgb(C["button"]))
    c.ring(bx, bz, 2.05, 0.3, rgb("#1B1C1E"))
    c.circle(bx, bz, 1.9, rgb(C["button"], 0.9))


def front():
    c = Canvas(L.PRINT_REGIONS["front"]["mm"], rgb(C["body"]))
    c.rounded(-L.HALF, L.HALF, 0.0, L.HEIGHT, L.CORNER, rgb(C["case"]))
    g, s = L.GLASS, L.SCREEN
    c.rounded(-g["width"] / 2, g["width"] / 2, g["z"] - g["height"] / 2, g["z"] + g["height"] / 2, g["r"], rgb(C["glass"]))
    c.rounded(-s["width"] / 2, s["width"] / 2, s["z"] - s["height"] / 2, s["z"] + s["height"] / 2, 0.3, rgb("#0C0D0F"))
    for side in (1, -1):
        joycon_face(c, side)
    return c


# ---- The edges ---------------------------------------------------------------------------------------------------------

def pill(c, x0, x1, y, h, fill):
    c.rounded(x0, x1, y - h / 2, y + h / 2, h / 2 - 0.01, fill)


def screw(c, x, y, r):
    c.circle(x, y, r, rgb("#2B2D30"))
    c.circle(x, y, r * 0.75, rgb("#35373A"))
    c.line([(x - r * 0.5, y), (x + r * 0.5, y)], r * 0.22, rgb("#1A1B1D"))
    c.line([(x, y - r * 0.5), (x, y + r * 0.5)], r * 0.22, rgb("#1A1B1D"))


def usb(c, x0, x1, y, h):
    pill(c, x0 - 0.7, x1 + 0.7, y, h + 1.4, rgb(C["case"], 1.12))
    pill(c, x0, x1, y, h, rgb(C["port"]))
    pill(c, x0 + 1.6, x1 - 1.6, y, h * 0.3, rgb("#2E3033"))


def top():
    t = L.TOP
    c = Canvas(L.PRINT_REGIONS["top"]["mm"], rgb(C["case"]))
    y = t["button_y"]
    legend = rgb(C["legend"])
    pill(c, t["power"][0] - 0.3, t["power"][1] + 0.3, y, t["button_w"] + 0.6, rgb(C["seam"]))
    pill(c, t["power"][0], t["power"][1], y, t["button_w"], rgb(C["button"]))
    px = sum(t["power"]) / 2
    c.draw.arc([*c.p(px - 0.95, y + 0.95), *c.p(px + 0.95, y - 0.95)], -50, 230, fill=legend, width=round(0.22 * c.s))
    c.line([(px, y + 0.25), (px, y + 1.15)], 0.22, legend)
    pill(c, t["volume"][0] - 0.3, t["volume"][1] + 0.3, y, t["button_w"] + 0.6, rgb(C["seam"]))
    pill(c, t["volume"][0], t["volume"][1], y, t["button_w"], rgb(C["button"]))
    mid = sum(t["volume"]) / 2
    c.line([(mid, y - 1.2), (mid, y + 1.2)], 0.3, rgb(C["seam"]))
    c.line([(t["minus"] - 0.9, y), (t["minus"] + 0.9, y)], 0.25, legend)
    c.line([(t["plus"] - 0.9, y), (t["plus"] + 0.9, y)], 0.25, legend)
    c.line([(t["plus"], y - 0.9), (t["plus"], y + 0.9)], 0.25, legend)
    c.text("VOLUME", "segoeui.ttf", 1.35, mid, y + 3.4, legend, spacing=0.12)
    mx, mr = t["mic"]
    c.circle(mx, y, mr, rgb("#26282B"))
    c.circle(mx, y, mr * 0.55, rgb("#141517"))
    screw(c, t["screw"][0], y, t["screw"][1])
    for x0, x1 in t["vents"]:
        pill(c, x0, x1, sum(t["vent_y"]) / 2, t["vent_y"][1] - t["vent_y"][0], rgb(C["vent"]))
        xs = x0 + 1.2
        while xs < x1 - 1.0:
            c.line([(xs, t["vent_y"][0] + 0.6), (xs, t["vent_y"][1] - 0.6)], 0.18, rgb("#25272A"))
            xs += 0.55
    usb(c, t["usb"][0], t["usb"][1], y, t["usb_h"])
    jx, jr = t["jack"]
    c.circle(jx, y, jr + 0.5, rgb(C["case"], 1.12))
    c.circle(jx, y, jr, rgb(C["port"]))
    c.circle(jx, y, jr * 0.45, rgb("#2A2C2F"))
    hy = y + 3.5
    c.draw.arc([*c.p(jx - 0.9, hy + 0.9), *c.p(jx + 0.9, hy - 0.9)], 180, 360, fill=legend, width=round(0.22 * c.s))
    c.rounded(jx - 1.0, jx - 0.55, hy - 0.7, hy, 0.15, legend)
    c.rounded(jx + 0.55, jx + 1.0, hy - 0.7, hy, 0.15, legend)
    x0, x1 = t["card"]
    y0, y1 = t["card_y"]
    c.rounded(x0 - 0.2, x1 + 0.2, y0 - 0.2, y1 + 0.2, 1.2, rgb(C["seam"]))
    c.rounded(x0, x1, y0, y1, 1.0, rgb(C["case"], 1.05))
    c.text("GAME CARD", "segoeui.ttf", 1.3, (x0 + x1) / 2, y1 - 1.6, legend, spacing=0.1)
    pill(c, t["slit"] - 0.4, t["slit"] + 0.4, y, 2.0, rgb(C["port"]))
    return c


def bottom():
    b = L.BOTTOM
    x0, x1, y0, y1 = L.PRINT_REGIONS["bottom"]["mm"]
    c = Canvas((x0, x1, -y1, -y0), rgb(C["case"]))       # drawn at (x, -y): the face at the top
    y = -6.9
    s0, s1 = b["speaker_y"]
    for sign in (-1, 1):
        a0, a1 = sorted((sign * b["speakers"][0], sign * b["speakers"][1]))
        c.rounded(a0, a1, -s1, -s0, 1.2, rgb(C["vent"]))
        for row in range(4):
            yy = -s0 - 1.0 - row * 1.6
            xx = a0 + 1.2 + (0.8 if row % 2 else 0.0)
            while xx < a1 - 1.0:
                c.circle(xx, yy, 0.55, rgb("#24262A"))
                xx += 1.6
        c.line([(a0 + 0.6, -s1 + 0.5), (a1 - 0.6, -s1 + 0.5)], 0.25, rgb("#2E3033"))
    usb(c, b["usb"][0], b["usb"][1], y, b["usb_h"])
    for sign in (-1, 1):
        c.circle(sign * b["holes"], y, b["hole_r"] + 0.45, rgb(C["case"], 1.1))
        c.circle(sign * b["holes"], y, b["hole_r"], rgb("#1A1B1D"))
        screw(c, sign * b["screws"], y, b["screw_r"])
    c.rounded(b["notch"][0], b["notch"][1], -13.6, -10.6, 0.6, rgb(C["port"]))
    return c


# ---- The back ----------------------------------------------------------------------------------------------------------

def switch2_logo(c, x, z, width, fill, ground):
    """The Nintendo Switch 2 logo in its manner: the emblem (two Joy-Con, one drawn in outline with its dot high, one
    filled with its dot low), the 2, and NINTENDO SWITCH under them, width wide, its middle at (x, z)."""
    k = width / 62.0                                        # the logo's own millimetres, from the screen's start-up
    top = z + 28.5 * k
    def r(a, b):
        return x + (a - 31.0) * k, top - b * k
    lx0, lz0 = r(0.0, 0.0)
    lx1, lz1 = r(15.0, 33.0)
    c.rounded(lx0, lx1, lz1, lz0, [0.6 * k, 0.6 * k, 7.0 * k, 7.0 * k], fill)       # its outer corners round
    c.rounded(lx0 + 3.4 * k, lx1 - 3.4 * k, lz1 + 3.4 * k, lz0 - 3.4 * k, [0.3 * k, 0.3 * k, 4.0 * k, 4.0 * k], ground)
    c.circle(*r(8.0, 10.0), 3.0 * k, fill)
    rx0, rz0 = r(18.0, 0.0)
    rx1, rz1 = r(32.0, 33.0)
    c.rounded(rx0, rx1, rz1, rz0, [7.0 * k, 7.0 * k, 0.6 * k, 0.6 * k], fill)
    c.circle(*r(25.0, 18.5), 3.0 * k, ground)
    c.text("2", "seguibl.ttf", 31.0 * k, r(48.5, 16.5)[0], r(48.5, 16.5)[1], fill)
    c.text("NINTENDO", "seguisb.ttf", 5.0 * k, x, top - 41.0 * k, fill, spacing=3.1 * k)
    c.text("SWITCH", "seguibl.ttf", 10.5 * k, x, top - 51.5 * k, fill, spacing=0.6 * k)


def racetrack(c, x, z, length, fill):
    """Nintendo's name in its oval, along z (as the Joy-Con 2's backs have it)."""
    w = length * 0.27
    layer = Canvas((-length / 2, length / 2, -w / 2, w / 2), (0, 0, 0, 0), c.s)
    layer.rounded(-length / 2, length / 2, -w / 2, w / 2, w / 2 - 0.01, fill)
    layer.rounded(-length / 2 + 0.45, length / 2 - 0.45, -w / 2 + 0.45, w / 2 - 0.45, w / 2 - 0.46, (0, 0, 0, 0))
    layer.text("Nintendo", "arialbd.ttf", w * 0.5, 0.0, 0.0, fill)
    turned = layer.img.rotate(-90, expand=True, resample=Image.BICUBIC)        # read from the top down
    a, b = c.p(x - w / 2, z + length / 2)
    c.img.alpha_composite(turned, (round(a), round(b)))


def rear():
    """The back seen from behind: drawn with its x the face's negated (rx), the logo reading the right way round."""
    c = Canvas(L.REAR_REGIONS["rear"]["mm"], rgb(C["rear"]))
    def rx(points):
        return [(-x, z) for x, z in points]
    c.rounded(-L.HALF, L.HALF, 0.0, L.HEIGHT, L.CORNER, rgb(C["rear"]))
    k = L.KICKSTAND
    for sign in (-1, 1):
        a0, a1 = sorted((sign * (k["legs"][0] - 0.5), sign * (k["legs"][1] + 0.5)))
        c.rounded(a0, a1, 1.0, k["hinge_z"] + 2.0, 1.0, rgb("#2F3235"))
    c.rounded(-k["legs"][1] - 0.5, k["legs"][1] + 0.5, 0.8, k["bar"] + 1.3, 1.0, rgb("#2F3235"))
    switch2_logo(c, 0.0, 57.0, 40.0, rgb(C["logo"]), rgb(C["rear"]))
    lx0, lx1 = -31.0, -9.0                                  # a made-up label: its barcode and its lines
    c.rounded(lx0, lx1, 2.6, 9.2, 0.4, rgb("#858A91"))
    rnd = random.Random(2)
    x = lx0 + 1.2
    while x < lx1 - 1.0:
        w = rnd.choice((0.15, 0.25, 0.4))
        c.rounded(x, x + w, 5.4, 8.4, 0.01, rgb("#1D1E20"))
        x += w + rnd.choice((0.15, 0.25, 0.35))
    for line_z in (4.6, 3.6):
        c.line([(lx0 + 1.2, line_z), (lx1 - 1.2, line_z)], 0.3, rgb("#4A4E54"))
    for sx, sz in ((93.5, 109.0), (-93.5, 109.0), (93.5, 8.0), (-93.5, 8.0)):
        screw(c, sx, sz, 1.0)
    for side in (1, -1):
        c.polygon(rx(outline(side)), rgb(C["rear"]))
        c.line([(-side * L.HALF, 0.2), (-side * L.HALF, L.JOYCON["height"] - 0.2)], 0.45, rgb(C["seam"]))
        racetrack(c, -side * (L.HALF + 6.0), 71.5, 19.0, rgb("#2A2C2F"))
        r = L.RELEASE
        x = -side * (L.HALF + r["u"])
        c.rounded(x - r["width"] / 2, x + r["width"] / 2, r["z"] - r["height"] / 2, r["z"] + r["height"] / 2, r["r"],
                  rgb(C["button"]))
        for n_, line_z in enumerate((40.0, 37.6, 35.2, 32.8)):              # the regulatory marks, as faint lines
            reach = 9.0 if n_ % 2 else 12.0
            c.line([(-side * (L.HALF + 4.0), line_z), (-side * (L.HALF + 4.0 + reach), line_z)], 0.5, rgb("#2F3134"))
    return c


def tongue_side(side):
    """A Joy-Con 2's inner side seen from the console: z along it, y down it (drawn at (z, -y))."""
    z0, z1, y0, y1 = L.REAR_REGIONS["side_r" if side > 0 else "side_l"]["mm"]
    c = Canvas((z0, z1, -y1, -y0), rgb(C["body"]))
    accent = C["coral" if side > 0 else "blue"]
    t = L.TONGUE
    c.polygon([(b, -a) for a, b in L.stadium(t["y"][0], t["y"][1], t["z"][0], t["z"][1])], rgb(accent))
    p = L.TONGUE_PARTS
    y0p, y1p = p["pad_y"]
    upper, lower = ("SR", "SL") if side > 0 else ("SL", "SR")
    for (a, b), name in ((p["shoulder_pad"], upper), (p["lower_pad"], lower)):
        c.rounded(a - 0.2, b + 0.2, -y1p - 0.2, -y0p + 0.2, 1.3, rgb(accent, 0.8))
        c.rounded(a, b, -y1p, -y0p, 1.1, rgb(accent, 1.04))
        c.text(name, "segoeui.ttf", 1.6, (a + b) / 2, -(y0p + y1p) / 2, rgb(accent, 0.72), degrees=90)
    a, b = p["sensor"]
    c.rounded(a, b, -8.8, -5.0, 0.7, rgb("#151618"))
    c.circle(a + 1.3, -6.9, 0.7, rgb("#2A2C30"))
    c.circle(b - 1.3, -6.9, 0.7, rgb("#2A2C30"))
    a, b = L.CONNECTOR["z"]
    c.rounded(a, b, -L.CONNECTOR["y"][1], -L.CONNECTOR["y"][0], 0.3, rgb("#0D0D0E"))
    zz = a + 0.6
    while zz < b - 0.5:
        c.line([(zz, -6.3), (zz, -7.6)], 0.25, rgb(C["pin"]))
        zz += 1.05
    z, r = p["pin"]
    c.circle(z, -6.9, 3.0, rgb(accent, 0.9))
    c.circle(z, -6.9, r, rgb(accent, 1.08))
    a, b = p["sync"]
    c.rounded(a, b, -8.6, -5.2, 1.6, rgb(accent, 0.86))
    z, r = p["top_pad"]
    c.circle(z, -6.9, r + 0.9, rgb(accent, 0.86))
    c.circle(z, -6.9, r, rgb(accent, 1.05))
    for z in (113.0, 3.0):
        screw(c, z, -7.0, 0.9)
    return c


def end(side):
    """The console's end, seen from outside: z along it, y down it (drawn at (z, -y)): the channel's floor."""
    z0, z1, y0, y1 = L.REAR_REGIONS["end_r" if side > 0 else "end_l"]["mm"]
    c = Canvas((z0, z1, -y1, -y0), rgb(C["case"]))
    ch = L.CHANNEL
    accent = C["coral" if side > 0 else "blue"]
    c.polygon([(b, -a) for a, b in L.stadium(ch["y"][0] - 0.5, ch["y"][1] + 0.5, ch["z"][0] - 0.5, ch["z"][1] + 0.5)],
              rgb("#1E2022"))
    c.polygon([(b, -a) for a, b in L.stadium(ch["y"][0], ch["y"][1], ch["z"][0], ch["z"][1])], rgb(accent))
    a, b = L.CONNECTOR["z"]
    c.rounded(a, b, -L.CONNECTOR["y"][1], -L.CONNECTOR["y"][0], 0.3, rgb("#0D0D0E"))
    zz = a + 0.6
    while zz < b - 0.5:
        c.line([(zz, -6.3), (zz, -7.6)], 0.25, rgb(C["pin"]))
        zz += 1.05
    return c


def swatches(image, places, names):
    d = ImageDraw.Draw(image)
    for name in names:
        x, y = places[name]
        d.rectangle([x - 11, y - 11, x + 11, y + 11], fill=rgb(C[name])[:3])


def print_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(C["case"])[:3])
    for name, draw in (("front", front), ("top", top), ("bottom", bottom)):
        paste_region(image, L.PRINT_REGIONS[name]["px"], draw())
    swatches(image, L.SWATCHES, L.SWATCHES)
    return image


def rear_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(C["rear"])[:3])
    paste_region(image, L.REAR_REGIONS["rear"]["px"], rear())
    for side, a, b in ((1, "side_r", "end_r"), (-1, "side_l", "end_l")):
        paste_region(image, L.REAR_REGIONS[a]["px"], tongue_side(side))
        paste_region(image, L.REAR_REGIONS[b]["px"], end(side))
    swatches(image, L.REAR_SWATCHES, L.REAR_SWATCHES)
    return image


# ---- The glass ----------------------------------------------------------------------------------------------------------

LCD_OFF = (12, 13, 15)
_CACHE = {}


def sheen(size, strength):
    """The glass's reflection: a soft diagonal band of light, the same on every frame."""
    w, h = size
    band = Image.new("L", size, 0)
    ImageDraw.Draw(band).polygon([(w * 0.12, 0), (w * 0.36, 0), (w * 0.22, h), (-w * 0.02, h)], fill=255)
    return band.filter(ImageFilter.GaussianBlur(w * 0.06)).point(lambda v: round(v * strength))


def glass(lcd=None):
    """The video's frame, VIDEO_PX: the glass's black round the LCD, which shows lcd (LCD_PX) or is switched off."""
    if "sheen" not in _CACHE:
        _CACHE["sheen"] = sheen(L.VIDEO_PX, 0.045)
    frame = Image.new("RGB", L.VIDEO_PX, rgb(C["glass"])[:3])
    frame.paste(lcd.convert("RGB") if lcd is not None else Image.new("RGB", L.LCD_PX, LCD_OFF), L.LCD_AT)
    return Image.composite(Image.new("RGB", L.VIDEO_PX, WHITE), frame, _CACHE["sheen"])


def still():
    return glass()


# ---- The screens ------------------------------------------------------------------------------------------------------
# Drawn at W2 x H2, five sixths of the LCD's 1920 x 1080 (twice the video's picture), then halved; n() turns the LCD's
# pixels into the drawing's.

W2, H2 = 2 * L.LCD_PX[0], 2 * L.LCD_PX[1]
K = W2 / L.NATIVE[0]
HOME_BG = (235, 235, 235)
INK = (45, 46, 49)
HOVER = (40, 196, 228)


def n(v):
    return v * K


def ui(px, weight="segoeui.ttf"):
    return font(weight, n(px))


def half(img):
    return img.convert("RGB").resize(L.LCD_PX, Image.LANCZOS)


def fit(img, size, centre=(0.5, 0.5)):
    return ImageOps.fit(img.convert("RGB"), (round(size[0]), round(size[1])), Image.LANCZOS, centering=centre)


def rounded_mask(size, r):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=r, fill=255)
    return mask


class Library:
    """The made-up games the HOME Menu shows: their logos and their key art (tools/made-up-games's library and
    paintings), and Dusty Gulch's HD key art (paintings.py)."""

    def __init__(self, made_up_dir):
        root = Path(made_up_dir)
        stem, system = L.MADE_UP
        self.logo = Image.open(root / "library" / "media" / system / "logos" / f"{stem}.png").convert("RGBA")
        self.keyart = painting("sw2_gulch_keyart").convert("RGB")
        self.others = [(Image.open(root / "library" / "media" / s / "logos" / f"{logo}.png").convert("RGBA"),
                        Image.open(root / "paintings" / folder / "keyart.png").convert("RGB"))
                       for s, logo, folder in L.SOFTWARE]

    def icon(self, art, logo, size, centre=(0.5, 0.5)):
        """A software icon: its key art square, its logo across its lower part."""
        img = fit(art, (size, size), centre).convert("RGBA")
        w = size * 0.84
        lg = logo.resize((round(w), max(1, round(logo.height * w / logo.width))), Image.LANCZOS)
        if lg.height > size * 0.4:
            lg = logo.resize((max(1, round(logo.width * size * 0.4 / logo.height)), round(size * 0.4)), Image.LANCZOS)
        shadow = Image.new("RGBA", lg.size, (0, 0, 0, 0))
        shadow.putalpha(lg.getchannel("A").filter(ImageFilter.GaussianBlur(size * 0.012)).point(lambda v: v * 0.6))
        at = (round((size - lg.width) / 2), round(size * 0.94 - lg.height))
        img.alpha_composite(shadow, (at[0], at[1] + round(size * 0.008)))
        img.alpha_composite(lg, at)
        return img


def user_icon(img, x, y, r):
    d = ImageDraw.Draw(img)
    d.ellipse([x - r - n(3), y - r - n(3), x + r + n(3), y + r + n(3)], fill=WHITE)
    d.ellipse([x - r, y - r, x + r, y + r], fill=(236, 120, 52))
    star = [(x + r * 0.62 * (1 if k % 2 == 0 else 0.42) * math.cos(math.radians(-90 + 36 * k)),
             y + r * 0.62 * (1 if k % 2 == 0 else 0.42) * math.sin(math.radians(-90 + 36 * k))) for k in range(10)]
    d.polygon(star, fill=WHITE)


def status(img):
    """The top bar's right: the time, Wi-Fi and the battery."""
    d = ImageDraw.Draw(img)
    f = ui(36, "segoeui.ttf")
    d.text((n(1700), n(107)), "10:24", font=f, fill=INK, anchor="rm")
    cx, cy = n(1752), n(118)
    for k, r in enumerate((n(26), n(17), n(8))):
        d.arc([cx - r, cy - r, cx + r, cy + r], 225, 315, fill=INK, width=round(n(5)))
    d.ellipse([cx - n(3.5), cy - n(6), cx + n(3.5), cy + n(1)], fill=INK)
    bx, by = n(1790), n(94)
    d.rounded_rectangle([bx, by, bx + n(48), by + n(26)], radius=n(5), outline=INK, width=round(n(3)))
    d.rectangle([bx + n(48), by + n(8), bx + n(52), by + n(18)], fill=INK)
    d.rounded_rectangle([bx + n(5), by + n(5), bx + n(38), by + n(21)], radius=n(2), fill=INK)


ICONS = [((228, 40, 36), "globe"), ((240, 140, 30), "chat"), ((86, 170, 70), "news"), ((222, 60, 50), "bag"),
         ((52, 110, 200), "album"), ((42, 170, 180), "share"), ((120, 122, 128), "pad"), ((120, 122, 128), "card"),
         ((120, 122, 128), "gear"), ((120, 122, 128), "power")]


def glyph(d, kind, x, y, s, colour):
    """A made-up icon for the HOME Menu's bar, s its half-size."""
    w = max(1, round(s * 0.16))
    if kind == "globe":
        d.ellipse([x - s * 1.25, y - s * 1.25, x + s * 1.25, y + s * 1.25], fill=colour)
        d.ellipse([x - s * 0.7, y - s * 0.7, x + s * 0.7, y + s * 0.7], outline=WHITE, width=w)
        d.line([(x - s * 0.7, y), (x + s * 0.7, y)], fill=WHITE, width=w)
        d.ellipse([x - s * 0.3, y - s * 0.7, x + s * 0.3, y + s * 0.7], outline=WHITE, width=w)
    elif kind == "chat":
        d.rounded_rectangle([x - s * 0.8, y - s * 0.75, x + s * 0.8, y + s * 0.55],
                            radius=s * 0.25, outline=colour, width=w)
        d.polygon([(x - s * 0.4, y + s * 0.5), (x - s * 0.1, y + s * 0.5), (x - s * 0.45, y + s * 0.9)], fill=colour)
        for k in (-1, 0, 1):
            d.ellipse([x + k * s * 0.38 - s * 0.1, y - s * 0.2, x + k * s * 0.38 + s * 0.1, y], fill=colour)
    elif kind == "news":
        d.rounded_rectangle([x - s * 0.7, y - s * 0.8, x + s * 0.7, y + s * 0.8], radius=s * 0.12, outline=colour, width=w)
        for k in range(4):
            yy = y - s * 0.45 + k * s * 0.3
            d.line([(x - s * 0.4, yy), (x + s * (0.4 if k else 0.1), yy)], fill=colour, width=w)
    elif kind == "bag":
        d.rounded_rectangle([x - s * 0.75, y - s * 0.35, x + s * 0.75, y + s * 0.8],
                            radius=s * 0.1, outline=colour, width=w)
        d.arc([x - s * 0.38, y - s * 0.85, x + s * 0.38, y + s * 0.1], 180, 360, fill=colour, width=w)
    elif kind == "album":
        d.rounded_rectangle([x - s * 0.8, y - s * 0.65, x + s * 0.8, y + s * 0.65],
                            radius=s * 0.12, outline=colour, width=w)
        d.line([(x - s * 0.6, y + s * 0.45), (x - s * 0.15, y - s * 0.1), (x + s * 0.15, y + s * 0.2), (x + s * 0.35, y),
                (x + s * 0.6, y + s * 0.45)], fill=colour, width=w)
    elif kind == "share":
        for k in range(3):
            yy = y - s * 0.5 + k * s * 0.45
            d.rounded_rectangle([x - s * 0.8 + k * s * 0.1, yy, x + s * 0.8 - k * s * 0.1, yy + s * 0.28],
                                radius=s * 0.1, outline=colour, width=w)
    elif kind == "pad":
        d.rounded_rectangle([x - s * 0.8, y - s * 0.4, x + s * 0.8, y + s * 0.4], radius=s * 0.4, outline=colour, width=w)
        d.ellipse([x - s * 0.5, y - s * 0.12, x - s * 0.26, y + s * 0.12], fill=colour)
        d.ellipse([x + s * 0.26, y - s * 0.12, x + s * 0.5, y + s * 0.12], fill=colour)
    elif kind == "card":
        d.rounded_rectangle([x - s * 0.55, y - s * 0.8, x + s * 0.55, y + s * 0.8],
                            radius=s * 0.15, outline=colour, width=w)
        d.line([(x - s * 0.25, y + s * 0.5), (x + s * 0.25, y + s * 0.5)], fill=colour, width=w)
    elif kind == "gear":
        for k in range(8):
            a = math.radians(22.5 * 2 * k)
            d.line([(x + s * 0.55 * math.cos(a), y + s * 0.55 * math.sin(a)),
                    (x + s * 0.85 * math.cos(a), y + s * 0.85 * math.sin(a))], fill=colour, width=round(w * 1.6))
        d.ellipse([x - s * 0.6, y - s * 0.6, x + s * 0.6, y + s * 0.6], outline=colour, width=w)
        d.ellipse([x - s * 0.25, y - s * 0.25, x + s * 0.25, y + s * 0.25], outline=colour, width=w)
    else:
        d.arc([x - s * 0.7, y - s * 0.7, x + s * 0.7, y + s * 0.7], -60, 240, fill=colour, width=w)
        d.line([(x, y - s * 0.85), (x, y - s * 0.15)], fill=colour, width=w)


class Home:
    """The HOME Menu, basic white: the user's icon, the time, the software's tiles (Dusty Gulch first), the icons'
    bar, the controllers and A's hint."""

    def __init__(self, library):
        self.library = library
        size = round(n(L.TILES["size"]))
        self.tiles = [library.icon(library.keyart, library.logo, size, (0.36, 0.5))]
        self.tiles += [library.icon(art, logo, size) for logo, art in library.others]
        self.base = self.draw()

    def draw(self):
        img = Image.new("RGBA", (W2, H2), HOME_BG + (255,))
        user_icon(img, n(107), n(107), n(44))
        status(img)
        t = L.TILES
        size = round(n(t["size"]))
        mask = rounded_mask((size, size), round(n(t["r"])))
        shadow = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([20, 24, size + 20, size + 24], radius=n(t["r"]), fill=(0, 0, 0, 40))
        shadow = shadow.filter(ImageFilter.GaussianBlur(8))
        for k, tile in enumerate(self.tiles):
            x, y = round(n(t["x"] + k * (t["size"] + t["gap"]))), round(n(t["y"]))
            img.alpha_composite(shadow, (x - 20, y - 20))
            img.paste(tile, (x, y), mask)
        b = L.ICON_BAR
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([n(b["x0"]), n(b["y0"]), n(b["x1"]), n(b["y1"])], radius=n((b["y1"] - b["y0"]) / 2),
                            fill=(250, 250, 250))
        step = (b["x1"] - b["x0"]) / b["icons"]
        for k, (colour, kind) in enumerate(ICONS):
            glyph(d, kind, n(b["x0"] + step * (k + 0.5)), n((b["y0"] + b["y1"]) / 2), n(34), colour)
        d.line([(n(56), n(985)), (n(1864), n(985))], fill=(214, 214, 214), width=round(n(2)))
        for k, colour in enumerate(((44, 46, 50), (44, 46, 50))):
            x0 = n(60 + k * 30)
            d.rounded_rectangle([x0, n(1010), x0 + n(26), n(1058)], radius=n(10), fill=colour)
        d.ellipse([n(1716), n(1016), n(1752), n(1052)], fill=(140, 142, 146))
        d.text((n(1734), n(1034)), "A", font=ui(24, "segoeuib.ttf"), fill=WHITE, anchor="mm")
        d.text((n(1766), n(1034)), "Start", font=ui(30), fill=(140, 142, 146), anchor="lm")
        return img

    def frame(self, hover=0.0, pressed=0.0, glow=0.0):
        """The HOME Menu, the game's tile highlighted (hover, 0 to 1: its title and its frame; glow pulses the frame)
        and pressed (0 to 1, shrinking it a little)."""
        img = self.base.copy()
        if hover <= 0:
            return img
        t = L.TILES
        d = ImageDraw.Draw(img)
        x0, y0 = n(t["x"]), n(t["y"])
        size = n(t["size"])
        if pressed > 0:
            s = 1 - 0.05 * pressed
            tile = self.tiles[0].resize((round(size * s), round(size * s)), Image.LANCZOS)
            d.rectangle([x0 - n(14), y0 - n(14), x0 + size + n(14), y0 + size + n(14)], fill=HOME_BG)
            mask = rounded_mask(tile.size, round(n(t["r"]) * s))
            off = round(size * (1 - s) / 2)
            img.paste(tile, (round(x0) + off, round(y0) + off), mask)
            size *= s
            x0 += off
            y0 += off
        a = round(255 * min(1.0, hover))
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        width = n(7) * (1 + 0.25 * glow)
        ld.rounded_rectangle([x0 - n(10), y0 - n(10), x0 + size + n(10), y0 + size + n(10)], radius=n(t["r"] + 8),
                             outline=HOVER + (a,), width=round(width))
        ld.text((n(t["x"] + 6), n(t["y"] - 34)), "Dusty Gulch", font=ui(34, "segoeui.ttf"), fill=INK + (a,), anchor="lm")
        img.alpha_composite(layer)
        return img


def arrow(img, x, y, alpha=1.0):
    """The HOME Menu's mouse cursor: a black arrow outlined in white, its tip at (x, y) in the drawing's pixels."""
    s = n(1.35)
    shape = [(0, 0), (0, 25), (6, 19.5), (10.5, 29), (15, 27), (10.6, 17.8), (18.5, 17.8)]
    pts = [(x + px * s, y + py * s) for px, py in shape]
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.polygon([(px + n(2), py + n(3)) for px, py in pts], fill=(0, 0, 0, round(70 * alpha)))
    layer = layer.filter(ImageFilter.GaussianBlur(n(2)))
    d = ImageDraw.Draw(layer)
    d.polygon(pts, fill=(0, 0, 0, round(255 * alpha)), outline=(255, 255, 255, round(255 * alpha)), width=round(n(2.2)))
    img.alpha_composite(layer)


def sights(img, x, y, alpha=1.0, kick=0.0):
    """The game's sights at (x, y): a gold ring and its ticks, outlined in dark brown; kick opens them after a shot."""
    if alpha <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = n(34) * (1 + 0.35 * kick)
    for colour, width in (((60, 30, 12), n(11)), ((255, 214, 92), n(5.5))):
        c = colour + (round(255 * alpha),)
        d.ellipse([x - r, y - r, x + r, y + r], outline=c, width=round(width))
        for a in (0, 90, 180, 270):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            d.line([(x + ca * r * 0.45, y + sa * r * 0.45), (x + ca * r * 1.45, y + sa * r * 1.45)], fill=c,
                   width=round(width))
        d.ellipse([x - width * 0.6, y - width * 0.6, x + width * 0.6, y + width * 0.6], fill=c)
    img.alpha_composite(layer)


def outlined_text(img, s, face, x, y, fill, line, width, anchor="mm", alpha=1.0):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((x, y), s, font=face, fill=fill + (round(255 * alpha),), anchor=anchor, stroke_width=round(width),
           stroke_fill=line + (round(255 * alpha),))
    img.alpha_composite(layer)


def title(library, prompt=True, fade=1.0):
    """Dusty Gulch's title: its key art, its logo in the sky, SHOOT TO START."""
    if "title" not in _CACHE:
        art = library.keyart
        img = fit(art, (W2, H2), (0.5, 0.0)).convert("RGBA")
        w = W2 * 0.6
        logo = library.logo.resize((round(w), round(library.logo.height * w / library.logo.width)), Image.LANCZOS)
        glow = Image.new("RGBA", logo.size, (60, 20, 0, 0))
        glow.putalpha(logo.getchannel("A").filter(ImageFilter.GaussianBlur(n(10))).point(lambda v: v * 0.7))
        at = (round((W2 - logo.width) / 2), round(n(110)))
        img.alpha_composite(glow, at)
        img.alpha_composite(logo, at)
        outlined_text(img, "© 2026 NINEBOLT", ui(26, "ROCKEB.TTF"), W2 / 2, n(1040), (255, 236, 200), (70, 28, 8), n(3))
        _CACHE["title"] = img
    img = _CACHE["title"].copy()
    if prompt:
        outlined_text(img, "SHOOT TO START", ui(64, "ROCKEB.TTF"), n(L.START_AT[0]), n(L.START_AT[1]),
                      (255, 226, 120), (80, 30, 6), n(6))
    if fade < 1:
        img = Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, fade)
    return img


def muzzle(img, x, y, age):
    """A shot's flash at the sights, age frames after the click: a white-hot star bursting and fading."""
    if not 0 <= age < 4:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = n(46) * (0.8 + 0.25 * age)
    a = round(255 * (1 - age / 4))
    pts = []
    for k in range(16):
        rr = r * (1.0 if k % 2 == 0 else 0.42)
        ang = math.radians(11.25 * 2 * k + 7)
        pts.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
    d.polygon(pts, fill=(255, 210, 90, a))
    d.ellipse([x - r * 0.35, y - r * 0.35, x + r * 0.35, y + r * 0.35], fill=(255, 255, 235, a))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(n(1.5))))


class Street:
    """The game: the street painted by Codex (its 16:9 part, STREET in the layout's painting pixels), the outlaws and
    the bottles cut out of their green and placed in it, the barrel, the window's railing and the porch in front of
    them cut back out of the painting; the score, the six shots left, STAGE CLEAR."""

    def __init__(self):
        x0, y0, x1, y1 = L.STREET["crop"]
        self.s = W2 / (x1 - x0)
        self.origin = (x0, y0)
        self.base = painting("sw2_gulch_street").convert("RGBA").crop(L.STREET["crop"]).resize((W2, H2), Image.LANCZOS)
        outlaws = poses(painting("sw2_gulch_outlaws"))
        props = poses(painting("sw2_gulch_props"))
        self.figures = dict(burly=outlaws[0:2], skinny=outlaws[2:4], brown=props[0], blue=props[1], shatter=props[2])
        self.fronts = {name: self.front(spec["front"]) for name, spec in L.STREET["targets"].items()
                       if spec.get("front")}

    def at(self, x, y):
        """The painting's pixel (x, y) in the drawing."""
        return (x - self.origin[0]) * self.s, (y - self.origin[1]) * self.s

    def front(self, shapes):
        """What's in front of a target: the painting under shapes (polygons and ellipses in its pixels), cut out."""
        mask = Image.new("L", (W2, H2), 0)
        d = ImageDraw.Draw(mask)
        for kind, pts in shapes:
            if kind == "poly":
                d.polygon([self.at(*p) for p in pts], fill=255)
            else:
                (ax, ay), (bx, by) = self.at(*pts[0]), self.at(*pts[1])
                d.ellipse([ax, ay, bx, by], fill=255)
        layer = self.base.copy()
        layer.putalpha(mask.filter(ImageFilter.GaussianBlur(1.2)))
        return layer

    def place(self, img, pose, x, bottom, height, dy=0.0, scale=1.0, alpha=1.0, clip=None):
        """A cut-out figure, its foot (its lowest row) centred at the painting's (x, bottom), height painting pixels
        tall, moved dy painting pixels down; clip (x0, y0, x1, y1), in the painting's pixels, keeps it inside."""
        src = pose["img"]
        h = height * self.s * scale
        w = src.width * h / src.height
        fig = src.resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)
        if alpha < 1:
            fig.putalpha(fig.getchannel("A").point(lambda v: round(v * alpha)))
        cx, cy = self.at(x, bottom + dy)
        hip = pose["hip"] / src.width * w
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        layer.alpha_composite(fig, (round(cx - hip), round(cy - h)))
        if clip:
            (ax, ay), (bx, by) = self.at(*clip[:2]), self.at(*clip[2:])
            keep = Image.new("L", img.size, 0)
            ImageDraw.Draw(keep).rectangle([ax, ay, bx, by], fill=255)
            layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", img.size, 0), keep))
        img.alpha_composite(layer)

    def outlaw(self, img, name, f, shot):
        """An outlaw: rising into view before his shot, aiming; hit, thrown back and sinking out of sight."""
        spec = L.STREET["targets"][name]
        aim, hit = self.figures[spec["who"]]
        rise = spec["rise"]
        appear = shot - spec["early"]
        if f < appear:
            return
        x, bottom, height = spec["at"]
        if f < shot:
            t = min(1.0, (f - appear) / 5)
            self.place(img, aim, x, bottom, height, dy=rise * (1 - t * t * (3 - 2 * t)), clip=spec.get("clip"))
            return
        t = (f - shot) / 9
        if t >= 1:
            return
        self.place(img, hit, x, bottom, height, dy=rise * t * t, scale=1 - 0.12 * t, alpha=1 - max(0.0, t - 0.6) / 0.4,
                   clip=spec.get("clip"))

    def bottle(self, img, name, f, shot):
        spec = L.STREET["targets"][name]
        x, bottom, height = spec["at"]
        if f < shot:
            self.place(img, self.figures[spec["who"]], x, bottom, height)
            return
        t = (f - shot) / 8
        if t < 1:
            self.place(img, self.figures["shatter"], x + 6, bottom + 10, height * (1.5 + 0.5 * t), alpha=1 - t)

    def frame(self, f):
        """The street at frame f: (the picture, the score)."""
        img = self.base.copy()
        score = 0
        for shot, _aim, name in L.TARGETS:
            kind = L.STREET["targets"][name]
            if kind["who"] in ("brown", "blue"):
                self.bottle(img, name, f, shot)
            else:
                self.outlaw(img, name, f, shot)
                if name in self.fronts:
                    img.alpha_composite(self.fronts[name])
            if f >= shot + 2:
                score += kind["points"]
            if 0 <= f - shot < 14:
                age = (f - shot) / 14
                ax, ay = _aim
                outlined_text(img, f"+{kind['points']}", ui(44, "ROCKEB.TTF"), n(ax), n(ay) - n(60) - n(50) * age,
                              (255, 230, 120), (90, 32, 6), n(4), alpha=1 - age * age)
        self.hud(img, f, score)
        return img

    def hud(self, img, f, score):
        outlined_text(img, f"1P {score:06d}", ui(52, "ROCKEB.TTF"), n(64), n(64), (255, 236, 196), (78, 30, 8), n(5),
                      anchor="lm")
        left = 6 - sum(1 for shot, _a, _n in L.TARGETS if f >= shot)
        d = ImageDraw.Draw(img)
        for k in range(6):
            x, y = n(1830 - k * 44), n(1010)
            colour = (232, 186, 74) if k < left else (70, 52, 40)
            d.rounded_rectangle([x - n(11), y - n(34), x + n(11), y + n(30)], radius=n(10), fill=(60, 28, 10))
            d.rounded_rectangle([x - n(7), y - n(30), x + n(7), y + n(26)], radius=n(7), fill=colour)
        last = L.TARGETS[-1][0]
        if f >= last + 10:
            t = min(1.0, (f - last - 10) / 8)
            outlined_text(img, "STAGE CLEAR!", ui(110 * (0.7 + 0.3 * t), "ROCKEB.TTF"), W2 / 2, n(470),
                          (255, 220, 96), (90, 28, 4), n(8), alpha=t)


# ---- Main ---------------------------------------------------------------------------------------------------------------

def main(made_up_dir, out):
    os.makedirs(out, exist_ok=True)
    print_atlas().save(os.path.join(out, "switch2_print.png"))
    rear_atlas().save(os.path.join(out, "switch2_rear.png"))
    still().save(os.path.join(out, "switch2_screen.png"))
    library = Library(made_up_dir)
    home = Home(library)
    half(home.frame(1.0, glow=0.5)).save(os.path.join(out, "check_home.png"))
    half(title(library)).save(os.path.join(out, "check_title.png"))
    street = Street()
    for f in (186, 206, 230, 262):
        half(street.frame(f)).save(os.path.join(out, f"check_street_{f}.png"))
    print(f"Switch 2: {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
