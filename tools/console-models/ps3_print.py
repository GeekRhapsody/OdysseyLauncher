"""The PlayStation 3 set's printing, for the console theme's PlayStation 3 model (tools/console-models/ps3.py).

Draws its atlas, its regions as ps3_layout.py places them, each in millimetres as the model's planar UVs map it: the
top seen from above (PLAYSTATION 3, its letters built from strokes in the logo's squared, slanted manner, reading from
the back to the front); the front (the flap with its three lights, the drive's chrome face with the slot and the
PlayStation mark, the black lip with the eject and power marks, the power light and SONY); the base's front (its
grille); the right end (the two bands of vents following the top's arc and the row of format marks between them), the
left end (the hard disk's door, the vent slots) and the back (the ports); the chrome strip's sheen; the Blu-ray's two
sides (a made-up game, Odyssey); and the swatches small parts take their colour from. Run it with the system Python
(Pillow):

    python tools/console-models/ps3_print.py <out folder>

It writes ps3_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps3_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import shade  # noqa: E402
from windows_pc_print import FONTS, Region, mix  # noqa: E402

CASE = L.CASE
MATTE = (52, 52, 58)
VENT = (66, 66, 72)           # the right end's panel between its vents, catching the light
LOGO_GREY = (168, 170, 176)
MARK = (205, 205, 210)
TOP_Z = 100.0                 # the ends' and the back's regions run from here down to the table


# ---- Lettering -------------------------------------------------------------------------------------------------------

# PLAYSTATION 3's letters as strokes, in the logo's manner: squared, wide, slanted, rounded at the joints. A letter is
# (width, strokes) in units of its height, x to the right and y down.
GLYPHS = {
    "P": (1.35, [[(0, 1), (0, 0), (1.35, 0), (1.35, 0.56), (0, 0.56)]]),
    "L": (1.2, [[(0, 0), (0, 1), (1.2, 1)]]),
    "A": (1.4, [[(0, 1), (0.36, 0), (1.4, 0), (1.4, 1)], [(0.22, 0.6), (1.4, 0.6)]]),
    "Y": (1.35, [[(0, 0), (0, 0.46), (1.35, 0.46)], [(1.35, 0), (1.35, 1), (0.1, 1)]]),
    "S": (1.4, [[(1.4, 0), (0, 0), (0, 0.5), (1.4, 0.5), (1.4, 1), (0, 1)]]),
    "T": (1.4, [[(0, 0), (1.4, 0)], [(0.7, 0), (0.7, 1)]]),
    "I": (0.0, [[(0, 0), (0, 1)]]),
    "O": (1.4, [[(0, 0), (1.4, 0), (1.4, 1), (0, 1), (0, 0)]]),
    "N": (1.4, [[(0, 1), (0, 0), (1.4, 0), (1.4, 1)]]),
    "3": (1.4, [[(0, 0), (1.4, 0), (1.4, 1), (0, 1)], [(0.28, 0.5), (1.4, 0.5)]]),
}
STROKE = 0.2                  # the pen, in letter heights
SLANT = 0.24                  # how far a letter's top leans right, in letter heights


def lettering(text, height, length, colour, gap=0.55, space=1.15):
    """text in the logo's letters, height pixels tall, stretched along to length pixels: an RGBA strip."""
    pen = STROKE * height
    advance = []
    for ch in text:
        advance.append(space if ch == " " else GLYPHS[ch][0])
    units = sum(advance) + gap * (len(text) - 1) + SLANT + STROKE
    scale_x = length / (units * height)
    img = Image.new("RGBA", (round(length + 2 * pen), round(height + 2 * pen)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pen / 2 + pen / 2
    for ch, w in zip(text, advance):
        if ch != " ":
            for stroke in GLYPHS[ch][1]:
                pts = [(x + (px + SLANT * (1 - py)) * height * scale_x, pen + py * height * (1 - STROKE))
                       for px, py in stroke]
                d.line(pts, fill=colour, width=round(pen), joint="curve")
                for p in (pts[0], pts[-1]):
                    d.ellipse([p[0] - pen / 2, p[1] - pen / 2, p[0] + pen / 2, p[1] + pen / 2], fill=colour)
        x += (w + gap) * height * scale_x
    return img


def turned_text(text, font, size_px, colour, angle):
    """text set in a font and turned by angle degrees (anticlockwise), on a transparent ground."""
    f = ImageFont.truetype(FONTS + font, size_px)
    box = f.getbbox(text)
    img = Image.new("RGBA", (box[2] - box[0] + 8, box[3] - box[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((4 - box[0], 4 - box[1]), text, font=f, fill=colour)
    return img.rotate(angle, expand=True, resample=Image.BICUBIC)


def place(reg, img, cx, cy):
    """Pastes img with its middle at (cx, cy) millimetres in reg."""
    x, y = reg.p(cx, cy)
    reg.img.alpha_composite(img, (round(x - img.width / 2), round(y - img.height / 2)))


# ---- The console -----------------------------------------------------------------------------------------------------

def top():
    """The top from above, the front at the bottom: the case, and PLAYSTATION 3 reading from the back (the top) to
    the front, its letters' tops towards the right end."""
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["top"], w, d, CASE + (255,))
    lg = L.LOGO
    y0, y1 = lg["y"]
    strip = lettering("PLAYSTATION 3", lg["height"] * reg.sy, (y1 - y0) * reg.sy, LOGO_GREY + (255,))
    strip = strip.rotate(-90, expand=True, resample=Image.BICUBIC)
    place(reg, strip, lg["x"] + w / 2, d - (y0 + y1) / 2)
    return reg


def ps_mark(reg, cx, cy, h):
    """The PlayStation mark, h tall, its middle at (cx, cy): the red P standing over the S lying in yellow, green and
    blue, as the drive's face has it."""
    w = h * 0.95
    left, base = cx - w / 2, cy + h / 2
    for k, colour in enumerate(((246, 190, 30), (40, 168, 92), (48, 104, 206))):     # the S's three bands, lying
        y = base - h * 0.34 + k * h * 0.11
        reg.poly([(left + k * w * 0.1, y), (left + w * 0.82 + k * w * 0.06, y - h * 0.08),
                  (left + w + k * w * 0.02, y - h * 0.02), (left + w * 0.2 + k * w * 0.1, y + h * 0.1)], colour)
    red = (222, 36, 40)
    reg.poly([(cx - w * 0.16, cy - h / 2), (cx - w * 0.02, cy - h / 2), (cx - w * 0.02, base - h * 0.08),
              (cx - w * 0.16, base - h * 0.02)], red)                                     # the P's stem
    reg.poly([(cx - w * 0.02, cy - h / 2), (cx + w * 0.22, cy - h * 0.42), (cx + w * 0.3, cy - h * 0.22),
              (cx + w * 0.22, cy - h * 0.02), (cx - w * 0.02, cy + h * 0.06), (cx - w * 0.02, cy - h * 0.06),
              (cx + w * 0.12, cy - h * 0.12), (cx + w * 0.14, cy - h * 0.28), (cx - w * 0.02, cy - h * 0.34)], red)


def chrome(reg, x0, x1, z0, z1, at):
    """The drive's chrome face between z0 and z1: bright where it faces the light, darker towards its foot, as the
    photographs show it."""
    stops = [(0.0, (244, 245, 248)), (0.2, (255, 255, 255)), (0.5, (232, 234, 238)), (0.66, (170, 172, 180)),
             (0.82, (110, 112, 120)), (1.0, (150, 152, 160))]
    for k in range(48):
        t0, t1 = k / 48, (k + 1) / 48
        t = (t0 + t1) / 2
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if a <= t <= b:
                colour = mix(ca, cb, (t - a) / (b - a))
                break
        reg.rect_(*at(x0, z1 - (z1 - z0) * t0), *at(x1, z1 - (z1 - z0) * t1), colour)


def front():
    """The front, (x, z) as the viewer sees it: the flap, the band over it, the drive's chrome face, the lip."""
    w = L.WIDTH
    z_lo, z_hi = L.FRONT_REGION
    reg = Region(L.REGIONS["front"], w, z_hi - z_lo, CASE + (255,))

    def at(x, z):
        return x + w / 2, z_hi - z

    (fx0, fx1), ft = L.FLAP["x"], L.FLAP["top"]
    reg.rect_(*at(fx0, ft), *at(fx1, L.UNDER), shade(CASE, 0.04))                       # the flap's face
    reg.line([at(fx0, L.UNDER + 0.6), at(fx1, L.UNDER + 0.6)], (6, 6, 7), 0.5)
    dx, dz = L.FLAP["dots"]
    for k in range(3):
        reg.circle(*at(dx + (k - 1) * 2.6, dz), 0.45, (70, 72, 78))
    (dx0, dx1), (dz0, dz1) = L.DRIVE["x"], L.DRIVE["z"]
    chrome(reg, dx0, dx1, dz0, dz1, at)
    reg.poly([at(dx1 - 4.0, dz1), at(dx1, dz1), at(dx1, dz0), at(dx1 - 1.5, dz0)], (90, 92, 100))   # its end's bevel
    reg.line([at(dx0, dz1), at(dx1, dz1)], (30, 30, 34), 0.5)
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    reg.rect_(*at(sx0 - 1.2, sz1 + 1.0), *at(sx1 + 1.2, sz0 - 1.0), (120, 122, 128), r=1.4)  # the slot's chrome lip
    reg.rect_(*at(sx0, sz1), *at(sx1, sz0), (10, 10, 12), r=1.0)
    ps_mark(reg, *at(*L.PS_MARK["at"]), L.PS_MARK["height"])
    # The lip: its sloping top (from L.LIP's top down to its nose) carries the marks; its face, the light and SONY.
    ex, ez = L.EJECT
    reg.poly([at(ex - 2.0, ez - 0.2), at(ex + 2.0, ez - 0.2), at(ex, ez + 1.9)], MARK)
    reg.rect_(*at(ex - 2.0, ez - 0.8), *at(ex + 2.0, ez - 1.4), MARK)
    px, pz = L.POWER
    reg.text("I/", "arial.ttf", 3.0, *at(px - 2.4, pz), MARK)
    reg.circle(*at(px + 1.6, pz), 1.3, outline=MARK, width=0.45)
    reg.rect_(*at(px + 1.35, pz + 1.9), *at(px + 1.85, pz + 0.2), CASE)
    reg.rect_(*at(px + 1.38, pz + 1.7), *at(px + 1.82, pz + 0.1), MARK)
    sony = turned_text("SONY", "timesbd.ttf", round(2.8 * reg.sy), MARK + (255,), -90)
    place(reg, sony, *at(*L.SONY))
    lx, lz = L.LIGHT["at"]
    lw, lh = L.LIGHT["size"]
    for k in (-1, 1):                                                                      # the light's two bars: off
        reg.rect_(*at(lx + k * 0.9 - 0.35, lz + lh / 2), *at(lx + k * 0.9 + 0.35, lz - lh / 2), (96, 30, 26))
    reg.line([at(L.LIP["x"][0], L.LIP["nose"]), at(L.LIP["x"][1], L.LIP["nose"])], (40, 40, 44), 0.4)
    return reg


def base():
    """The base's front, set back under the flap and the lip: its grille of square holes."""
    w = L.WIDTH
    reg = Region(L.REGIONS["base"], w, L.UNDER, MATTE + (255,))

    def at(x, z):
        return x + w / 2, L.UNDER - z
    for j in range(7):
        z = 3.0 + j * 3.1
        x_end = L.right_x(z + 2.0) - 5.0
        x = -w / 2 + 6.0
        while x + 2.0 < x_end:
            reg.rect_(*at(x, z + 2.0), *at(x + 2.0, z), (5, 5, 6))
            x += 3.1
    return reg


def grille(reg, at, y0, y1, z_hi, z_lo, pitch=2.7, hole=1.6):
    """A band of square vent holes between z_lo(y) and z_hi(y), from y0 to y1."""
    y = y0
    while y < y1:
        z = z_lo(y) + 0.5
        while z + hole < z_hi(y) - 0.5:
            reg.rect_(*at(y, z + hole), *at(y + hole, z), (6, 6, 7))
            z += pitch
        y += pitch


def right():
    """The right end, seen from the right (the front at the left): the top's wrap following its arc, the two bands of
    vents and the row of format marks between them."""
    reg = Region(L.REGIONS["right"], 280.0, TOP_Z, VENT + (255,))

    def at(y, z):
        return y, TOP_Z - z
    cover = [at(y, L.top_z(y) - L.SHOULDER - 1.2) for y in range(0, 281, 4)]
    reg.poly([at(0, TOP_Z)] + cover + [at(280, TOP_Z)], CASE)                       # the top's glossy wrap
    reg.line(cover, (120, 122, 128), 0.6)                                            # its edge, catching the light
    t = L.top_z
    grille(reg, at, 14.0, 260.0, lambda y: t(y) - 14.0, lambda y: max(4.0, t(y) - 32.0))
    grille(reg, at, 18.0, 256.0, lambda y: t(y) - 39.0, lambda y: max(5.0, t(y) - 60.0))
    row = [at(y, t(y) - 35.5) for y in range(12, 265, 4)]
    reg.line(row, (44, 44, 50), 5.0)
    marks = ["Blu-ray Disc", "DVD", "CD", "SACD", "dts", "DOLBY", "Bluetooth", "HDMI"]
    for k, text in enumerate(marks):
        y = 40.0 + k * 26.0
        img = turned_text(text, "arialbd.ttf", round(2.3 * reg.sy), (120, 122, 128, 255),
                          math.degrees(math.atan2(t(y + 2) - t(y - 2), 4.0)))
        place(reg, img, *at(y, t(y) - 35.5))
    return reg


def left():
    """The left end, seen from the left (the back at the left): the top's wrap, the seam's two lines, the hard disk's
    door and the vent slots along the foot."""
    reg = Region(L.REGIONS["left"], 280.0, TOP_Z, MATTE + (255,))

    def at(y, z):
        return L.DEPTH - y, TOP_Z - z
    cover = [at(y, L.top_z(y) - 15.0) for y in range(0, 281, 4)]
    reg.poly([at(0, TOP_Z)] + cover + [at(280, TOP_Z)], CASE)
    reg.line(cover, (6, 6, 7), 0.7)
    reg.line([at(y, L.top_z(y) - 19.0) for y in range(10, 270, 4)], (8, 8, 9), 0.5)
    reg.rect_(*at(196.0, 36.0), *at(76.0, 14.0), (30, 30, 33), r=1.5, outline=(10, 10, 11), width=0.5)
    reg.rect_(*at(98.0, 30.0), *at(84.0, 24.0), (60, 62, 68), r=0.6)                   # the door's sticker
    for k in range(9):
        y = 36.0 + k * 24.0
        reg.rect_(*at(y + 9.0, 8.0), *at(y, 5.5), (5, 5, 6), r=0.6)
    return reg


def back():
    """The back, seen from behind (the right end at the left): the top's lip and the base's ports."""
    w = L.WIDTH
    reg = Region(L.REGIONS["back"], w, 62.0, MATTE + (255,))

    def at(x, z):
        return w / 2 - x, 62.0 - z
    reg.rect_(*at(w / 2, 62.0), *at(-w / 2, 46.0), CASE)
    reg.line([at(w / 2, 46.0), at(-w / 2, 46.0)], (6, 6, 7), 0.6)
    for x0 in range(110, 30, -6):                                         # the fan's outlet
        reg.rect_(*at(x0, 34.0), *at(x0 - 3.5, 8.0), (6, 6, 7))
    reg.rect_(*at(100.0, 40.0), *at(40.0, 35.0), (196, 198, 202))         # the serial label
    for x0, w0, h0 in ((18.0, 9.0, 3.0), (2.0, 8.0, 7.0), (-12.0, 5.0, 5.0), (-26.0, 10.0, 3.5)):
        reg.rect_(*at(x0, 30.0), *at(x0 - w0, 30.0 - h0), (8, 8, 9))      # HDMI, LAN, optical, AV multi out
    for x0 in range(-4, -60, -6):
        reg.rect_(*at(x0, 20.0), *at(x0 - 3.5, 8.0), (6, 6, 7))
    reg.rect_(*at(-118.0, 36.0), *at(-136.0, 12.0), (14, 14, 16), outline=(40, 40, 44), width=0.5)
    reg.rect_(*at(-122.0, 34.0), *at(-132.0, 28.0), (36, 36, 40))         # MAIN POWER
    reg.rect_(*at(-121.0, 24.0), *at(-133.0, 15.0), (4, 4, 5))            # AC IN
    return reg


def strip():
    """The chrome strip round the top's front edge, across its curve: from the top (the region's top) round to the
    front face (its foot)."""
    reg = Region(L.REGIONS["strip"], 1.0, 1.0, CASE + (255,))
    stops = [(0.0, (120, 122, 128)), (0.14, (208, 210, 216)), (0.3, (250, 251, 254)), (0.46, (238, 240, 244)),
             (0.6, (118, 120, 128)), (0.78, (196, 198, 204)), (1.0, (150, 152, 160))]
    for k in range(64):
        t = (k + 0.5) / 64
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if a <= t <= b:
                reg.rect_(0, k / 64, 1, (k + 1) / 64, mix(ca, cb, (t - a) / (b - a)))
                break
    return reg


# ---- The disc --------------------------------------------------------------------------------------------------------

def disc_side():
    """The Blu-ray's data side: silver with a violet sheen, the clear hub."""
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (180, 182, 190, 255))
    c = dm / 2
    for k in range(30, 0, -1):
        r = 58.0 * k / 30
        reg.circle(c, c, r, mix((150, 146, 176), (214, 216, 224), (k % 6) / 6))
    reg.circle(c, c, 22.0, (196, 198, 204))
    reg.circle(c, c, 16.5, (150, 156, 164))
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def label():
    """The Blu-ray's label: a made-up game, Odyssey."""
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["label"], dm, dm, (20, 20, 24, 255))
    c = dm / 2
    art = space((600, 600)).convert("RGB")
    ship(ImageDraw.Draw(art), 180, 330, 4.0, "#FFFFFF", "#FFB23C")
    mask = Image.new("L", reg.img.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0), fill=255)
    md.ellipse(reg.box(c - 21.0, c - 21.0, c + 21.0, c + 21.0), fill=0)
    x0, y0, x1, y1 = reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.img.paste(layer, (0, 0), mask)
    reg.rect_(c - 58.0, c - 58.0, c + 58.0, c - 46.0, (18, 18, 20))                     # the black band
    reg.text("ODYSSEY", "ariblk.ttf", 9.0, c, c - 34.0, (255, 214, 70))
    reg.text("BD", "arialbd.ttf", 4.0, c + 38.0, c - 30.0, (230, 230, 236))
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def swatches(image, places, colours):
    d = ImageDraw.Draw(image)
    for name, (x, y) in places.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), base(), right(), left(), back(), strip(), disc_side(), label()):
        reg.paste(image)
    swatches(image, L.SWATCHES, dict(case=CASE, matte=MATTE, under=(10, 10, 11), chrome=(214, 216, 222), slot=(8, 8, 9),
                                     green=(80, 240, 120), red=(200, 40, 30), wedge=(44, 44, 50), dim=(64, 64, 70),
                                     silver=(200, 202, 208)))
    path = os.path.join(out, "ps3_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
