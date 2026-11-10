"""The PlayStation's printing, for the console theme's PlayStation model (tools/console-models/psx.py).

Draws its atlas, its regions as psx_layout.py places them, each in millimetres as the model's planar UVs map it: the top
seen from above (the lid's SONY and PlayStation marks and its grip dots, the buttons' caps and legends, the seams where
the strip in front of the lid meets the pods, the groove from the lid to OPEN, the compact disc mark on the plate); the
front (the ports' numbers) and the back (its ports and their names), each seen straight on; the back of each front
opening (the memory card slot over the controller port); the disc's label side (a made-up game, Odyssey) and its black
data side; and the swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/psx_print.py <out folder>

It writes psx_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psx_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
INK = (35, 38, 48)
CAP = (156, 157, 164)             # the buttons' caps: a little darker than the case, and bluer
SEAM = shade(CASE, -0.32)

# The PlayStation mark, traced from its artwork in its own units (900 x 698, y down): the P, and the S lying flat in two
# halves either side of the P's stem, each a band folded round a slot that opens towards the stem. Two straight lines
# stripe the S: yellow below the first, teal between them, blue above the second.
MARK = (900.0, 698.0)
P = [(335, 0), (430, 22), (530, 50), (600, 75), (650, 110), (685, 160), (703, 230), (700, 300), (680, 350), (645, 388),
     (600, 405), (568, 402), (540, 392), (540, 165), (532, 135), (512, 120), (493, 127), (485, 150), (485, 695),
     (335, 655)]
S_LEFT = [(307.5, 394), (67.5, 479), (40, 489), (18, 502), (4, 518), (0, 535), (6, 552), (25, 568), (60, 584),
          (110, 597), (170, 606), (235, 610), (307.5, 609), (307.5, 532.5), (272.5, 545), (235, 561), (200, 567.5),
          (165, 566), (140, 561), (133, 552), (138, 544), (165, 532), (192.5, 520), (307.5, 477.5)]
S_RIGHT = [(510.6, 460), (545.6, 448.9), (601, 435), (678.9, 430.6), (751, 437.8), (823, 460), (873, 487.8),
           (898, 515.6), (890, 537.8), (867.8, 557.2), (831.7, 571.1), (767.8, 593.3), (701, 616.7), (606.7, 652.8),
           (510.6, 686.1), (510.6, 601.7), (601.1, 571.1), (701.1, 533.3), (762.2, 507.2), (767.8, 498.9),
           (766.1, 493.3), (751.1, 483.3), (712.2, 481.1), (673.3, 487.8), (617.8, 508.9), (510.6, 548.9)]
STRIPES = (((67.5, 479.0), 0.32, (253, 185, 19)), ((510.6, 479.4), 0.286, (0, 180, 157)))   # a point, the slope, below
RED, BLUE = (237, 28, 36), (55, 119, 188)


def at(x, y):
    """A point of the top (x from the middle, y back from the front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


def fit_text(reg, s, font, x0, y0, w, h, fill):
    """s in font, its ink stretched to fill w x h, its top left at (x0, y0)."""
    f = ImageFont.truetype(FONTS + font, 240)
    mask = Image.new("L", (round(f.getlength(s)) + 120, 400), 0)
    ImageDraw.Draw(mask).text((60, 60), s, font=f, fill=255)
    mask = mask.crop(mask.getbbox())
    size = (max(1, round(w * reg.sx)), max(1, round(h * reg.sy)))
    layer = reg.layer()
    layer.paste(Image.new("RGBA", size, fill + (255,)), (round(x0 * reg.sx), round(y0 * reg.sy)),
                mask.resize(size, Image.LANCZOS))
    reg.over(layer)


def ps_mark(reg, x0, y0, w, h):
    """The PlayStation mark stretched to w x h, its top left at (x0, y0)."""
    kx, ky = w / MARK[0], h / MARK[1]

    def pts(points):
        return [reg.p(x0 + x * kx, y0 + y * ky) for x, y in points]

    s_mask = Image.new("L", reg.img.size, 0)
    for half in (S_LEFT, S_RIGHT):
        ImageDraw.Draw(s_mask).polygon(pts(half), fill=255)
    stripes = Image.new("RGBA", reg.img.size, BLUE + (255,))
    for (px, py), slope, colour in reversed(STRIPES):
        edge = [(x, py + slope * (x - px)) for x in (-100.0, MARK[0] + 100)]
        ImageDraw.Draw(stripes).polygon(pts(edge + [(MARK[0] + 100, MARK[1] + 100), (-100.0, MARK[1] + 100)]),
                                        fill=colour + (255,))
    layer = reg.layer()
    layer.paste(stripes, (0, 0), s_mask)
    ImageDraw.Draw(layer).polygon(pts(P), fill=RED + (255,))
    reg.over(layer)


def cap(reg, name, colour, size):
    """A button's cap seen from above, its legend across it."""
    x, y, r = L.BUTTONS[name][:3]
    cx, cy = at(x, y)
    reg.circle(cx, cy, r + 0.2, CAP)
    reg.text(name.upper(), "arial.ttf", size, cx, cy, colour)


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)
    lx, ly = L.LID["x"], L.LID["y"]
    # The seams where the strip in front of the lid meets the pods, from the front to the lid's well.
    reach = ly - math.sqrt(L.WELL["r"] ** 2 - L.POD ** 2) + 1.0
    for x in (-L.POD, L.POD):
        reg.rect_(*at(x - 0.2, reach), *at(x + 0.2, L.SET_BACK), SEAM)
    # The lid: SONY at its back, the PlayStation marks at its front, the grip dots by its rim towards OPEN.
    reg.circle(*at(lx, ly), L.LID["r"], shade(CASE, 0.03))
    fit_text(reg, "SONY", "BOOKOSB.TTF", *at(-16.7, 147.3), 33.5, 5.3, INK)
    ps_mark(reg, *at(-10.2, 70.2), 20.4, 15.0)
    fit_text(reg, "PlayStation", "seguisb.ttf", *at(-14.2, 54.5), 28.4, 5.7, INK)
    for r in L.DOTS["r"]:
        for a in L.DOTS["angles"]:
            dx, dy = at(lx + r * math.cos(math.radians(a)), ly + r * math.sin(math.radians(a)))
            reg.circle(dx + 0.12, dy + 0.12, L.DOTS["size"] / 2, shade(CASE, -0.2))
            reg.circle(dx, dy, L.DOTS["size"] / 2, shade(CASE, 0.3))
    # The groove from the lid's well to OPEN's, on the line between their middles.
    ox, oy = L.BUTTONS["open"][:2]
    d = math.hypot(ox - lx, oy - ly)
    ux, uy = (ox - lx) / d, (oy - ly) / d
    lip = L.BUTTONS["open"][2] + L.BUTTONS["open"][3]
    ends = [at(lx + ux * t, ly + uy * t) for t in (L.WELL["r"] - 0.5, d - lip + 0.3)]
    reg.line(ends, SEAM, L.GROOVE)
    reg.line([(x + 0.35, y + 0.35) for x, y in ends], shade(CASE, 0.2), 0.25)
    # The buttons' caps, and the compact disc mark on the plate behind the lid.
    for name, colour, size in (("power", (60, 190, 180), 4.9), ("reset", INK, 3.0), ("open", (100, 160, 225), 4.75)):
        cap(reg, name, colour, size)
    mark = shade(CASE, 0.3)
    reg.text("COMPACT", "arialbd.ttf", 1.4, *at(53.3, 178.4), mark)
    reg.text("disc", "timesbi.ttf", 2.6, *at(53.3, 176.4), mark)
    reg.text("DIGITAL DATA", "arialbd.ttf", 0.95, *at(53.3, 174.5), mark)
    return reg


def front():
    """Every face facing the front, seen straight on: x to the right, z up. Its openings' backs are `port`."""
    reg = Region(L.REGIONS["front"], L.WIDTH, L.TOP, CASE)
    z1 = L.PORTS["z"][1]
    for k, x in enumerate(L.PORTS["x"]):
        reg.text(str(k + 1), "arial.ttf", 8.0, x + L.WIDTH / 2, L.TOP - (z1 + 5.5), INK)
    return reg


def port():
    """The back of a front opening, seen from in front: the memory card slot, its name on its back under the shadow of
    its top edge; a bar; the controller port, its socket's dark outline round three blocks of three pins."""
    w, h = L.PORTS["width"], L.PORTS["z"][1] - L.PORTS["z"][0]
    reg = Region(L.REGIONS["port"], w, h, shade(CASE, -0.04))
    reg.rect_(3.5, 2.5, w - 3.5, 9.5, shade(CASE, 0.06))
    reg.rect_(3.5, 2.5, w - 3.5, 3.6, shade(CASE, -0.45))
    for x in (6.0, w - 6.0):
        reg.rect_(x - 0.2, 3.6, x + 0.2, 9.0, shade(CASE, -0.25))
    reg.text("MEMORY CARD", "arial.ttf", 2.7, w / 2, 6.6, INK)
    reg.rect_(3.5, 9.5, w - 3.5, 10.1, shade(CASE, -0.2))
    reg.rect_(4.5, 13.5, w - 4.5, 25.5, (40, 41, 45), r=2.5)
    for k in range(3):
        cx = w / 2 + (k - 1) * 11.6
        reg.rect_(cx - 5.3, 16.6, cx + 5.3, 22.4, (186, 187, 190), r=1.5)
        for j in (-1, 0, 1):
            reg.circle(cx + j * 3.0, 19.5, 0.6, (50, 52, 56))
    return reg


def back():
    """Every face facing the back, seen from behind: the console's right end at the left, z up."""
    reg = Region(L.REGIONS["back"], L.WIDTH, L.TOP, CASE)

    def b(x, z):
        return L.WIDTH / 2 - x, L.TOP - z
    small = shade(CASE, -0.55)
    z0, z1 = L.PANEL["z"]
    reg.rect_(*b(L.PANEL["x"], z1), *b(-L.PANEL["x"], z0), shade(CASE, -0.08))
    # PARALLEL I/O, in the right pod's back.
    (x0, x1), (pz0, pz1) = L.PARALLEL["x"], L.PARALLEL["z"]
    reg.rect_(*b(x1, pz1), *b(x0, pz0), shade(CASE, -0.15))
    reg.rect_(*b(x1 - 4.0, pz1 - 5.0), *b(x0 + 4.0, pz0 + 6.0), (30, 31, 34), r=1.0)
    reg.rect_(*b(x1 - 6.0, pz1 - 8.5), *b(x0 + 6.0, pz0 + 9.5), (176, 180, 186))
    reg.text("PARALLEL I/O", "arial.ttf", 2.6, *b((x0 + x1) / 2, pz1 + 3.0), small)
    # The ports panel: SERIAL I/O, AUDIO OUT (the jacks themselves are parts), RFU DC OUT, VIDEO OUT, AV MULTI OUT.
    jz = L.JACKS["z"]
    reg.rect_(*b(55.5, jz + 3.5), *b(37.5, jz - 3.5), (34, 35, 38), r=0.8)
    reg.rect_(*b(53.5, jz + 1.2), *b(39.5, jz - 1.2), (150, 152, 156))
    reg.text("SERIAL I/O", "arial.ttf", 2.2, *b(46.5, jz + 6.5), small)
    for name, x in L.JACKS["at"].items():
        reg.circle(*b(x, jz), L.JACKS["r"] + 1.2, shade(CASE, -0.3))
    reg.text("AUDIO OUT", "arial.ttf", 2.2, *b(21.2, jz + 9.6), small)
    reg.text("R", "arial.ttf", 2.2, *b(L.JACKS["at"]["red"], jz + 6.5), small)
    reg.text("L(MONO)", "arial.ttf", 1.8, *b(L.JACKS["at"]["white"], jz + 6.5), small)
    reg.circle(*b(3.1, jz), 2.2, (30, 31, 34))
    reg.circle(*b(3.1, jz), 0.8, (176, 180, 186))
    reg.text("RFU DC OUT", "arial.ttf", 1.4, *b(3.1, jz + 9.6), small)
    reg.text("VIDEO OUT", "arial.ttf", 2.2, *b(L.JACKS["at"]["yellow"] - 2.0, jz + 6.5), small)
    reg.rect_(*b(-31.0, jz + 4.0), *b(-54.5, jz - 4.0), (34, 35, 38), r=1.0)
    reg.rect_(*b(-33.0, jz + 1.4), *b(-52.5, jz - 1.4), (150, 152, 156))
    reg.text("AV MULTI OUT", "arial.ttf", 2.2, *b(-42.7, jz + 7.0), small)
    # AC IN, in the left pod's back: the figure-8 socket and its two pins.
    (ax0, ax1), (az0, az1) = L.AC_IN["x"], L.AC_IN["z"]
    reg.rect_(*b(ax1, az1), *b(ax0, az0), shade(CASE, -0.15))
    cx, cz = (ax0 + ax1) / 2, (az0 + az1) / 2
    for dx in (-4.5, 4.5):
        reg.circle(*b(cx + dx, cz), 4.3, (30, 31, 34))
    reg.rect_(*b(cx + 4.5, cz + 3.0), *b(cx - 4.5, cz - 3.0), (30, 31, 34))
    for dx in (-4.5, 4.5):
        reg.circle(*b(cx + dx, cz), 1.2, (176, 180, 186))
    reg.text("~ AC IN", "arial.ttf", 2.6, *b(cx, az1 + 3.5), small)
    return reg


def label():
    """The disc's label side, seen looking at it: Odyssey's art, its title, the hole and its clear ring."""
    size = 2 * L.DISC["r"]
    art = space((960, 960))
    d = ImageDraw.Draw(art)
    ship(d, 250, 600, 3.6, "#FFFFFF", "#FFB23C")
    d.text((480, 230), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 120), fill="#FFE45C", anchor="mm",
           stroke_width=6, stroke_fill="#5A1A08")
    d.text((480, 760), "SCES-01986", font=ImageFont.truetype(FONTS + "arialbd.ttf", 34), fill="#D8D0F0", anchor="mm")
    reg = Region(L.REGIONS["label"], size, size, (0, 0, 0))
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 959, 959], fill=255)
    art.putalpha(mask)
    reg.img.paste(art.resize(reg.img.size, Image.LANCZOS), (0, 0), art.resize(reg.img.size, Image.LANCZOS))
    c = size / 2
    reg.circle(c, c, 22.0, (225, 228, 232))
    reg.circle(c, c, 18.0, (190, 194, 200))
    reg.circle(c, c, L.DISC["hole"], (30, 30, 32))
    ps_mark(reg, c - 17.0, c - 3.5, 9.0, 7.0)
    return reg


def data_side():
    """The disc's other side: black, a faint rainbow where the light catches it, the clear ring round the hole."""
    size = 2 * L.DISC["r"]
    reg = Region(L.REGIONS["data"], size, size, (0, 0, 0))
    c = size / 2
    reg.circle(c, c, c, (22, 22, 26))
    sheen = reg.layer()
    d = ImageDraw.Draw(sheen)
    for k, colour in enumerate(((255, 90, 90), (255, 210, 90), (90, 255, 140), (90, 160, 255), (200, 110, 255))):
        d.arc(reg.box(c - 50 + k * 4, c - 50 + k * 4, c + 50 - k * 4, c + 50 - k * 4), 200, 250, fill=colour + (90,),
              width=round(3 * reg.sx))
    reg.over(sheen.filter(ImageFilter.GaussianBlur(2 * reg.sx)))
    reg.circle(c, c, 22.0, (150, 156, 164))
    reg.circle(c, c, 17.0, (120, 124, 130))
    reg.circle(c, c, L.DISC["hole"], (30, 30, 32))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), back(), port(), label(), data_side()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("led", (90, 255, 120)), ("dark", rgb(L.COLOURS["dark"])), ("lens", (70, 120, 255)),
                         ("metal", (190, 194, 200)), ("red", (205, 40, 40)), ("white", (232, 232, 228)),
                         ("yellow", (240, 200, 40)), ("black", (14, 14, 16)), ("sled", (58, 60, 64))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "psx_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
