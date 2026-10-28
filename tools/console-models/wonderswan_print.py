"""The WonderSwans' printing, for the console theme's models (tools/console-models/wonderswan.py).

Draws each handheld's print atlas, its regions as wonderswan_layout.py places them, each in millimetres as the model's
planar UVs map it: the front (the body's colour with what shows through its clear plastic, the screen's surround, the
switched-off screen, the legends, the buttons' wells and tops, the speaker), the back (the empty cartridge slot, the
screws, the sticker), the cartridge's label side (a made-up game, Odyssey) and its other side, the start-up screen,
and a game played upright, drawn a quarter turn clockwise. The screens are drawn at the WonderSwan's 224 x 144 pixels
and pasted one texel a pixel. Run it with the system Python (Pillow):

    python tools/console-models/wonderswan_print.py <out folder>

It writes wonderswan_print.png and wonderswancolor_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wonderswan_layout as L  # noqa: E402
from game_boy_print import FONTS, SCALE, Face, rgb, rounded_polygon  # noqa: E402

LCD = ["#A3AA92", "#79806C", "#4D5345", "#262A20"]  # the WonderSwan's four shades, lightest first
INK = "#3E434B"


def grown(corners, centre, amount):
    """Corners moved away from centre by amount (millimetres)."""
    cx, cz = centre
    out = []
    for x, z in corners:
        d = math.hypot(x - cx, z - cz)
        out.append((x + (x - cx) / d * amount, z + (z - cz) / d * amount))
    return out


def petal_outline(m, x, z, degrees, grow=0.0):
    corners, radii = L.petal_corners(m, x, z, degrees)
    if grow:
        corners = grown(corners, (x, z), grow)
        radii = [r + grow * 0.6 for r in radii]
    return rounded_polygon(corners, radii, 12)


def screw(face, x, z, colour, r=1.6):
    face.circle(x, z, r, rgb(colour, 0.78))
    face.circle(x, z, r * 0.62, rgb(colour, 0.62))
    face.line(x - r * 0.45, z, x + r * 0.45, z, 0.25, rgb(colour, 0.9))
    face.line(x, z - r * 0.45, x, z + r * 0.45, 0.25, rgb(colour, 0.9))


def insides(face, m, kind):
    """What shows through the clear plastic, faintly: the board's edge, screw posts, the speaker's magnet, a few holes."""
    case = m["colours"]["case"]
    w, h = m["width"], m["height"]
    face.rounded(-w / 2 + 9.0, w / 2 - 9.0, 6.0, h - 6.0, 6.0, rgb(case, 0.95))
    face.rounded(-w / 2 + 10.0, w / 2 - 10.0, 7.0, h - 7.0, 5.0, rgb(case))
    for x, z in ((-w / 2 + 6.5, 6.5), (-w / 2 + 6.5, h - 7.0), (w / 2 - 7.0, 8.5), (w / 2 - 7.0, h - 8.0),
                 (-30.0, 36.0), (40.0, 36.0)):
        face.circle(x, z, 2.2, rgb(case, 0.88))
        face.circle(x, z, 1.1, rgb(case, 1.08))
    for k in range(5):
        face.circle(42.0 + 2.2 * (k % 2), 30.0 + k * 2.6, 0.55, rgb(case, 0.82))
    for cluster in ("Y", "X"):
        cx, cz = m["clusters"][cluster]
        face.circle(cx, cz, 10.8, rgb(case, 0.93))
        face.circle(cx, cz, 2.2, rgb(case, 0.85))
    if kind == "wonderswancolor":
        for z in range(4):
            for x in range(3):
                face.circle(46.0 + x * 2.0, 40.0 + z * 2.0, 0.45, rgb(case, 0.8))


def bezel(face, m):
    b = m["bezel"]
    (x0, x1), (top_left, top_right), bottom, tab = b["x"], b["top"], b["bottom"], b["tab"]
    colour = b["colour"]
    face.polygon(rounded_polygon([(x1, bottom), (x1, top_right), (x0, top_left), (x0, bottom)], [3.5, 3.5, 3.5, 3.5], 12),
                 rgb(colour))
    (tx0, tx1) = tab["x"]
    face.polygon(rounded_polygon([(tx1, tab["bottom"]), (tx1 + 3.0, bottom + 6.0), (tx0, bottom + 6.0), (tx0, tab["bottom"])],
                                 [3.0, 0.3, 0.3, 3.0], 10), rgb(colour))
    # A soft sheen along the top, as the silver catches the light.
    if colour == "#C3C7CE":
        for k in range(10):
            z = top_right - 1.0 - k * 0.5
            face.line(x0 + 4.0, z + (top_left - top_right) * 0.5, x1 - 4.0, z, 0.5, rgb(colour, 1.06 - k * 0.006))


def glass(face, m):
    g, s = m["glass"], m["screen"]
    (x0, x1), (z0, z1) = g["x"], g["z"]
    face.rounded(x0, x1, z0, z1, 1.6, rgb(g["colour"]))
    sx0, sx1, sz0, sz1 = L.screen_box(s["x"], s["z"], s["width"], s["height"])
    face.rounded(sx0 - 0.5, sx1 + 0.5, sz0 - 0.5, sz1 + 0.5, 0.4, rgb(s["colour"], 0.9))
    face.rounded(sx0, sx1, sz0, sz1, 0.3, rgb(s["colour"]))


def diagonal_legend(face, name, x, z, colour, degrees=-52.0, cap=1.25):
    """SOUND, START, POWER: a word slanting down to the right with a line under it, ending at (x, z)."""
    a = math.radians(degrees)
    length = 7.5
    sx, sz = x - length * math.cos(a), z - length * math.sin(a)
    face.line(sx, sz, x, z, 0.28, colour)
    nx, nz = -math.sin(a), math.cos(a)  # the side the word sits on, above the line
    mx, mz = (sx + x) / 2 + nx * 1.1, (sz + z) / 2 + nz * 1.1
    face.text(name, "arialbd.ttf", cap, mx, mz, colour, anchor="centre", degrees=degrees)


def speaker_ws(face, m):
    x, z, r = m["speaker"]
    case = m["colours"]["case"]
    face.circle(x, z, r + 0.6, rgb(case, 0.82))
    face.circle(x, z, r, rgb(case, 0.9))
    face.circle(x, z, r * 0.62, rgb(case, 0.74))
    face.circle(x, z, r * 0.3, rgb(case, 0.66))
    for k in range(6):
        zz = z - 3.75 + k * 1.5
        face.line(x + 2.2, zz, x + r + 2.6, zz, 0.6, rgb(case, 0.55))


def speaker_wsc(face, m):
    x, z, r = m["speaker"]
    case = m["colours"]["case"]
    face.circle(x, z, r + 0.7, rgb(case, 0.8))
    face.circle(x, z, r, rgb(case, 1.12))
    for k, shade in enumerate((1.02, 0.94, 0.86)):
        face.ring(x, z, r * (0.85 - 0.22 * k), 0.35, rgb(case, shade))
    face.circle(x, z, r * 0.25, rgb(case, 0.78))


def buttons(face, m, kind):
    """The petals' wells and tops (their tops are this texture, projected onto the buttons), with the Color's legends."""
    case, top = m["colours"]["case"], m["colours"]["buttons"]
    petals = L.petal_centres(m)
    if kind == "wonderswancolor":
        top = "#C9D8E8"
        for cluster in ("Y", "X"):
            cx, cz = m["clusters"][cluster]
            face.circle(cx, cz, m["disc"] + 0.5, rgb(case, 0.8))
            face.circle(cx, cz, m["disc"], rgb(case, 1.16))
            face.circle(cx, cz, m["disc"] - 1.0, rgb(case, 1.24))
        # A and B share a well along the diagonal between them.
        reach = m["petal"][0]
        cx, cz = m["clusters"]["AB"]
        face.pill(cx + reach / 2, cz - reach / 2, 2 * reach + 10.5, 10.5, 45.0, rgb(case, 0.8))
        face.pill(cx + reach / 2, cz - reach / 2, 2 * reach + 9.5, 9.5, 45.0, rgb(case, 1.14))
    for name, x, z, a in petals:
        face.polygon(petal_outline(m, x, z, a, 0.7), rgb(case, 0.62))
    for name, x, z, a in petals:
        face.polygon(petal_outline(m, x, z, a), rgb(top))
        if kind == "wonderswancolor":
            lx, lz = x + 0.5 * math.cos(math.radians(a)), z + 0.5 * math.sin(math.radians(a))
            face.text(name, "arialbd.ttf", 1.55, lx, lz, "#2B4C86", anchor="centre", stretch=0.95)

    # The diamonds' letters beside them on the WonderSwan.
    if kind == "wonderswan":
        for cluster, dx, dz in (("Y", -9.5, -9.0), ("X", -9.5, -9.0)):
            cx, cz = m["clusters"][cluster]
            face.text(cluster, "arialbd.ttf", 1.6, cx + dx, cz + dz, rgb(case, 0.55), anchor="centre")
        cx, cz = m["clusters"]["AB"]
        face.text("A", "arialbd.ttf", 1.6, cx + 6.6, cz + 6.2, rgb(case, 0.55), anchor="centre")
        face.text("B", "arialbd.ttf", 1.6, cx - 6.4, cz - 6.6, rgb(case, 0.55), anchor="centre")


def pills(face, m, kind):
    length, width = m["pill"]
    bez = m["bezel"]["colour"]
    for name, x, z in m["pills"]:
        face.pill(x, z, length + 1.6, width + 1.6, 0.0, rgb(bez, 0.72))
        face.pill(x, z, length, width, 0.0, rgb(m["colours"]["buttons"]))
        diagonal_legend(face, name, x - length / 2 + 0.6, z + width / 2 + 1.4, INK if kind == "wonderswan" else "#9A9DA6")
    if kind == "wonderswancolor":
        x, z, length, width = m["power"]
        face.pill(x, z, length + 1.8, width + 1.8, 0.0, rgb(m["colours"]["dark"]))
        face.pill(x, z, length, width, 0.0, rgb(m["colours"]["power"]))
        diagonal_legend(face, "POWER", x - length / 2 + 0.6, z + width / 2 + 1.6, "#2F7FD8")


def front_wonderswan(m):
    face = Face(m["regions"]["front"]["mm"], rgb(m["colours"]["case"]))
    insides(face, m, "wonderswan")
    bezel(face, m)
    glass(face, m)
    face.text("WonderSwan", "arialbi.ttf", 2.5, 19.5, 60.6, INK, anchor="centre", shear=0.18, stretch=1.05)
    speaker_ws(face, m)
    buttons(face, m, "wonderswan")
    pills(face, m, "wonderswan")
    return face


def front_wonderswancolor(m):
    face = Face(m["regions"]["front"]["mm"], rgb(m["colours"]["case"]))
    insides(face, m, "wonderswancolor")
    bezel(face, m)
    glass(face, m)
    face.text("WonderSwan", "arialbi.ttf", 2.0, -12.6, 69.8, "#8A8E97", anchor="centre", shear=0.18, stretch=1.05)
    face.text("Color", "arialbi.ttf", 3.6, -12.6, 65.6, "#1590C8", anchor="centre", shear=0.1, stretch=1.1)
    speaker_wsc(face, m)
    buttons(face, m, "wonderswancolor")
    pills(face, m, "wonderswancolor")
    return face


# ---- The back --------------------------------------------------------------------------------------------------------

def rear(m, kind):
    """The back, seen from behind (x is the front's, negated): the empty slot the cartridge slides into from the top,
    the board and screws through the plastic, the sticker."""
    case = m["colours"]["case"]
    face = Face(m["regions"]["rear"]["mm"], rgb(case))
    w, h = m["width"], m["height"]
    c = m["cart"]
    cx = -c["x"]
    face.rounded(-w / 2 + 8.0, w / 2 - 8.0, 5.0, h - 5.0, 6.0, rgb(case, 0.92))
    face.rounded(-w / 2 + 9.0, w / 2 - 9.0, 6.0, h - 6.0, 5.0, rgb(case, 0.97))
    for x, z in ((-w / 2 + 6.5, 6.5), (-w / 2 + 6.5, h - 7.0), (w / 2 - 7.0, 8.5), (w / 2 - 7.0, h - 8.0),
                 (cx - c["width"] / 2 - 5.0, h - 22.0), (cx + c["width"] / 2 + 5.0, h - 22.0)):
        screw(face, x, z, case)

    # The slot: open at the top, the board's green and its connector at the bottom.
    x0, x1, z0 = cx - c["width"] / 2 - 1.0, cx + c["width"] / 2 + 1.0, h - c["height"] - 1.5
    face.rounded(x0 - 0.8, x1 + 0.8, z0 - 0.8, h + 2.0, 2.0, rgb(case, 0.7))
    face.rounded(x0, x1, z0, h + 2.0, 1.5, rgb("#22282A"))
    face.rounded(x0 + 3.0, x1 - 3.0, z0 + 7.0, h - 4.0, 1.0, rgb("#2E4A36"))
    for k in range(5):
        face.rounded(x0 + 6.0 + k * 9.0, x0 + 12.0 + k * 9.0, z0 + 12.0 + (k % 2) * 6, z0 + 18.0 + (k % 2) * 6, 0.4,
                     rgb("#1A1C1E"))
    face.rounded(x0 + 3.0, x1 - 3.0, z0 + 1.0, z0 + 5.0, 0.5, rgb("#3A3A3A"))
    for k in range(24):
        x = x0 + 4.5 + k * (x1 - x0 - 9.0) / 23
        face.line(x, z0 + 1.6, x, z0 + 4.4, 0.6, rgb("#C9A54A"))

    # The sticker below it, and the battery cover's RELEASE arrow.
    face.rounded(cx - 24.0, cx + 16.0, z0 - 8.0, z0 - 1.5, 0.4, rgb("#F2F2EE"))
    face.rounded(cx - 23.0, cx - 17.5, z0 - 7.2, z0 - 2.3, 0.2, rgb("#101010"))
    face.text("BAN", "arialbd.ttf", 1.4, cx - 20.25, z0 - 3.6, "#F2F2EE", anchor="centre")
    face.text("DAI", "arialbd.ttf", 1.4, cx - 20.25, z0 - 5.9, "#F2F2EE", anchor="centre")
    model = "WSC-001" if kind == "wonderswancolor" else "WS-001"
    face.text(f"©BANDAI {1999 if kind == 'wonderswan' else 2000}   BATTERY LR6(AA)×1", "arial.ttf", 0.9,
              cx - 16.0, z0 - 3.3, "#303030")
    face.text(f"MODEL No.{model}   MADE IN JAPAN", "arial.ttf", 0.9, cx - 16.0, z0 - 5.9, "#303030")
    face.text("←RELEASE", "arialbd.ttf", 1.1, cx - 12.0, 3.4, rgb(case, 0.62), anchor="centre")
    return face


# ---- The cartridge ---------------------------------------------------------------------------------------------------

def emblem(draw, cx, cy, r, colours, width):
    """The WonderSwan's swan: a ring with a swirl curling into it, in pixels on a PIL draw."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colours[0], width=width)
    draw.arc([cx - r * 0.62, cy - r * 0.75, cx + r * 0.62, cy + r * 0.5], 200, 520, fill=colours[1 % len(colours)],
             width=width)
    draw.ellipse([cx - r * 0.18 + r * 0.3, cy - r * 0.45 - r * 0.18, cx + r * 0.18 + r * 0.3, cy - r * 0.45 + r * 0.18],
                 fill=colours[-1])


def cart_label_side(m, kind):
    """The label side, seen looking at it (wonderswan.py mirrors it onto the cartridge's +y face)."""
    colour = m["colours"]["cart"]
    face = Face(m["regions"]["cart"]["mm"], rgb(colour))
    c = m["cart"]
    hw, height, contacts = c["width"] / 2, c["height"], c["contacts"]

    # The smoky body: a little lighter where it's thin, the grip slot along the top.
    face.rounded(-hw + 0.8, hw - 0.8, contacts + 0.5, height - 0.8, 1.2, rgb(colour, 1.18))
    face.rounded(-11.0, 11.0, height - 3.2, height - 1.6, 0.8, rgb(colour, 0.7))

    # The contacts: the board's edge, gold strips.
    face.rounded(-hw + 2.4, hw - 2.4, 0.0, contacts + 0.3, 0.3, rgb("#3F7A4E"))
    for k in range(48):
        x = -hw + 3.4 + k * (2 * hw - 6.8) / 47
        face.line(x, 0.6, x, contacts - 0.6, 0.55, rgb("#D9B356"))

    # The label: a picture from the made-up game, its title, the swan, BANDAI.
    x0, x1, z0, z1 = -hw + 3.0, hw - 3.0, contacts + 2.2, height - 4.8
    face.rounded(x0, x1, z0, z1, 0.8, rgb("#F3F3EE"))
    picture = Image.new("RGBA", (96, 40))
    d = ImageDraw.Draw(picture)
    if kind == "wonderswan":
        for y in range(40):
            d.line([(0, y), (96, y)], fill=(250 - y * 2, 190 - y * 2, 120 + y, 255))
        d.ellipse([60, 8, 80, 28], fill="#FFE9A8")
        d.rectangle([0, 28, 96, 40], fill="#2B5E9C")
        for k in range(4):
            d.line([(54 - k * 6, 30 + k * 2), (86 + k * 4, 30 + k * 2)], fill="#FFE9A8")
        d.polygon([(18, 18), (30, 12), (26, 18), (40, 16), (24, 22)], fill="#FFFFFF")
    else:
        for y in range(40):
            d.line([(0, y), (96, y)], fill=(40 + y * 3, 30 + y, 110 + y * 2, 255))
        for x, y in ((6, 4), (20, 9), (34, 3), (50, 6), (70, 2), (88, 8), (12, 15), (80, 16)):
            d.point((x, y), fill="#FFFFFF")
        d.ellipse([58, 10, 88, 40], fill="#F27A3B")
        d.arc([46, 18, 100, 32], 160, 380, fill="#E8E0FF", width=2)
        d.polygon([(14, 30), (30, 14), (34, 18), (20, 34)], fill="#E6ECF6")
        d.polygon([(14, 30), (20, 34), (8, 38)], fill="#FFB23C")
    pz1 = z1 - 0.7
    pz0 = z0 + 6.0
    face.paste(picture, -2.0, x1 - 0.7, pz0, pz1, Image.NEAREST)
    face.text("ODYSSEY", "ariblk.ttf", 3.0, -12.0, (pz0 + pz1) / 2 + 2.2, "#1B1F4A", anchor="centre", shear=0.15)
    face.text("SWAN OF THE STARS" if kind == "wonderswan" else "COLOR VOYAGE", "arialbd.ttf", 0.95, -12.0,
              (pz0 + pz1) / 2 - 1.6, "#1B1F4A", anchor="centre")
    layer = Image.new("RGBA", (64, 64))
    emblem(ImageDraw.Draw(layer), 32, 32, 26, ["#E83A2E", "#E83A2E", "#E83A2E"], 7)
    face.paste(layer, x0 + 1.0, x0 + 5.0, pz1 - 4.6, pz1 - 0.6)
    face.text("SWJ-ODY01" if kind == "wonderswan" else "SWJ-ODY01C", "arialbd.ttf", 0.9, -12.0, z0 + 3.6, "#303030",
              anchor="centre")
    face.text("©ODYSSEY LAUNCHER   MADE IN JAPAN", "arial.ttf", 0.75, -6.0, z0 + 1.6, "#505050", anchor="centre")
    face.rounded(x1 - 7.5, x1 - 1.0, z0 + 0.8, z0 + 5.4, 0.3, rgb("#D7261F"))
    face.text("BAN", "arialbd.ttf", 1.3, x1 - 4.25, z0 + 4.0, "#FFFFFF", anchor="centre")
    face.text("DAI", "arialbd.ttf", 1.3, x1 - 4.25, z0 + 2.0, "#FFFFFF", anchor="centre")
    return face


def cart_rear(m):
    """The other side, towards the console's front: the screw, WonderSwan moulded in, the arrow."""
    colour = m["colours"]["cart"]
    face = Face(m["regions"]["cart_rear"]["mm"], rgb(colour))
    c = m["cart"]
    hw, height, contacts = c["width"] / 2, c["height"], c["contacts"]
    face.rounded(-hw + 0.8, hw - 0.8, contacts + 0.5, height - 0.8, 1.2, rgb(colour, 1.12))
    face.rounded(-hw + 2.4, hw - 2.4, 0.0, contacts + 0.3, 0.3, rgb("#2F5A3B"))
    screw(face, 0.0, height * 0.5, colour, 2.0)
    face.text("WonderSwan", "arialbi.ttf", 2.2, 0.0, height * 0.8, rgb(colour, 1.6), anchor="centre", shear=0.15)
    face.polygon([(-2.4, contacts + 6.0), (2.4, contacts + 6.0), (0.0, contacts + 3.4)], rgb(colour, 1.6))
    return face


# ---- The screens -----------------------------------------------------------------------------------------------------

def pixel_text(img, s, font, cap_px, x, y, fill, threshold=100, anchor="centre"):
    """Text in whole pixels: rendered at the screen's size, its edges thresholded; (x, y) its centre, or left middle."""
    probe = ImageFont.truetype(FONTS + font, 200)
    left, top, right, bottom = probe.getbbox("H")
    size = max(6, round(200 * cap_px / (bottom - top)))
    f = ImageFont.truetype(FONTS + font, size)
    left, top, right, bottom = f.getbbox(s)
    layer = Image.new("L", (right - left + 2, bottom - top + 2), 0)
    ImageDraw.Draw(layer).text((1 - left, 1 - top), s, font=f, fill=255)
    mask = layer.point(lambda a: 255 if a > threshold else 0)
    ox = round(x - layer.width / 2) if anchor == "centre" else round(x)
    img.paste(Image.new("RGBA", layer.size, fill), (ox, round(y - layer.height / 2)), mask)


def boot_screen(kind):
    """The start-up screen, 224 x 144: the swan and the name."""
    if kind == "wonderswan":
        img = Image.new("RGBA", (224, 144), LCD[0])
        d = ImageDraw.Draw(img)
        emblem(d, 112, 50, 24, [LCD[3], LCD[2], LCD[3]], 5)
        pixel_text(img, "WonderSwan", "arialbi.ttf", 13, 112, 96, LCD[3])
        pixel_text(img, "BANDAI", "arialbd.ttf", 6, 112, 124, LCD[2])
    else:
        img = Image.new("RGBA", (224, 144), "#F5F7FB")
        d = ImageDraw.Draw(img)
        for k, colour in enumerate(("#E8213A", "#F48A1C", "#F4C21C", "#2DB84A", "#2F6CE0")):
            r = 26 - k * 3
            d.arc([112 - r, 46 - r, 112 + r, 46 + r], 200 + k * 22, 200 + k * 22 + 250, fill=colour, width=3)
        d.ellipse([118, 30, 128, 40], fill="#2F6CE0")
        pixel_text(img, "WonderSwan", "arialbi.ttf", 11, 112, 90, "#6A6E78")
        pixel_text(img, "Color", "arialbi.ttf", 15, 112, 112, "#1E9FD4")
        pixel_text(img, "BANDAI", "arialbd.ttf", 6, 112, 133, "#9A9EA8")
    return img


def upright_game(kind):
    """A game played upright (144 x 224, then turned a quarter clockwise): Odyssey, a made-up shooter."""
    img = Image.new("RGBA", (144, 224))
    d = ImageDraw.Draw(img)
    if kind == "wonderswan":
        bg, star, mid, ink = LCD[0], LCD[2], LCD[1], LCD[3]
        d.rectangle([0, 0, 144, 224], fill=bg)
    else:
        for y in range(224):
            t = y / 224
            d.line([(0, y), (144, y)], fill=(int(18 + 50 * t), int(14 + 20 * t), int(60 + 70 * t), 255))
        star, mid, ink = "#FFFFFF", "#F27A3B", "#FFE45C"
    for x, y in ((12, 40), (40, 70), (100, 52), (130, 90), (24, 120), (70, 104), (118, 150), (8, 180), (60, 160),
                 (136, 30), (88, 196), (30, 210)):
        d.rectangle([x, y, x + 1, y + 1], fill=star)
    # A planet, three enemies, the player's swan-winged ship and its shot.
    d.ellipse([88, 60, 132, 104], fill=mid)
    d.arc([76, 74, 144, 90], 160, 380, fill=ink if kind == "wonderswan" else "#E8E0FF", width=2)
    for x, y in ((30, 70), (62, 92), (44, 120)):
        d.polygon([(x, y), (x + 10, y), (x + 5, y + 8)], fill=ink if kind == "wonderswan" else "#7CF0A0")
        d.rectangle([x + 3, y - 3, x + 7, y], fill=ink if kind == "wonderswan" else "#7CF0A0")
    sx, sy = 66, 182
    ship = "#FFFFFF" if kind == "wonderswancolor" else ink
    d.polygon([(sx, sy - 14), (sx + 5, sy), (sx - 5, sy)], fill=ship)
    d.polygon([(sx - 5, sy - 4), (sx - 16, sy + 4), (sx - 4, sy + 2)], fill=ship)
    d.polygon([(sx + 5, sy - 4), (sx + 16, sy + 4), (sx + 4, sy + 2)], fill=ship)
    d.rectangle([sx - 1, sy - 26, sx + 1, sy - 20], fill=ink)
    d.rectangle([sx - 1, sy - 40, sx + 1, sy - 34], fill=ink)
    d.rectangle([sx - 2, sy + 1, sx + 2, sy + 4], fill="#FF8A3C" if kind == "wonderswancolor" else mid)
    pixel_text(img, "SCORE 004190", "arialbd.ttf", 6, 4, 8, ink, anchor="left")
    pixel_text(img, "ODYSSEY", "ariblk.ttf", 11, 72, 28, ink)
    return img.rotate(-90, expand=True)


def screen_face(m, image):
    """A screen's region: the image itself, a texel a pixel (its region is 224 x 144)."""
    face = Face((0, 1, 0, 1), (0, 0, 0, 255))
    face.img = image
    return face


FRONTS = {"wonderswan": front_wonderswan, "wonderswancolor": front_wonderswancolor}


def atlas(kind):
    m = L.MODELS[kind]
    image = Image.new("RGBA", (L.ATLAS, L.ATLAS), rgb(m["colours"]["case"]))
    faces = {
        "front": FRONTS[kind](m),
        "rear": rear(m, kind),
        "cart": cart_label_side(m, kind),
        "cart_rear": cart_rear(m),
        "screen": screen_face(m, boot_screen(kind)),
        "screen_v": screen_face(m, upright_game(kind)),
    }
    for name, face in faces.items():
        # Each region bleeds 4 pixels into the gap round it, so filtering and mipmaps at its edges see its own colours.
        x, y, w, h = m["regions"][name]["px"]
        smooth = name not in ("screen", "screen_v")
        region = face.img.resize((w, h), Image.LANCZOS if smooth else Image.NEAREST)
        image.paste(region.resize((w + 8, h + 8), Image.NEAREST), (x - 4, y - 4))
        image.paste(region, (x, y))
    return image.convert("RGB")


def main(out):
    os.makedirs(out, exist_ok=True)
    for kind in L.MODELS:
        path = os.path.join(out, f"{kind}_print.png")
        atlas(kind).save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1])
