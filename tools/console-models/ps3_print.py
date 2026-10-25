"""The PlayStation 3 set's printing, for the console theme's PlayStation 3 model (tools/console-models/ps3.py).

Draws its atlas, its regions as ps3_layout.py places them, each in millimetres as the model's planar UVs map it: the
shell from above (the silver line along its front, PLAYSTATION 3 reading from the back); its front (the silver panel
with the slot, the PlayStation mark and the eject mark, the black flap and its three lights, the power mark, the
standby light, SONY); the plinth's front (the grille); the DualShock 3 from above (its discs' rims, the wells round the
d-pad and the face buttons, the symbols, SONY, SELECT, START, the PS mark, its player lights' numbers); the Blu-ray's
label (a made-up game, Odyssey); and the swatches small parts take their colour from. Run it with the system Python
(Pillow):

    python tools/console-models/ps3_print.py <out folder>

It writes ps3_print.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps3_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
SILVER = (196, 198, 202)
TEXT = (150, 152, 158)
SYMBOLS = dict(triangle=(60, 190, 160), circle=(226, 70, 78), cross=(126, 164, 226), square=(212, 108, 200))


def ps_mark(reg, cx, cy, h):
    """The PlayStation mark, h tall, its middle at (cx, cy): the red P standing, the S lying in yellow, green and
    blue."""
    w = h * 0.55
    reg.rect_(cx - w * 0.55, cy - h / 2, cx - w * 0.3, cy + h * 0.35, (226, 40, 40))           # the P's stem
    reg.draw.arc(reg.box(cx - w * 0.55, cy - h / 2, cx + w * 0.35, cy - h * 0.05), -90, 90, fill=(226, 40, 40),
                 width=reg.width(h * 0.13))
    for k, colour in enumerate(((246, 190, 30), (40, 170, 90), (50, 110, 210))):                # the S, lying
        y = cy + h * 0.12 + k * h * 0.11
        reg.poly([(cx - w * 0.9 + k * w * 0.3, y), (cx + w * 0.8 + k * w * 0.2, y), (cx + w * 0.7 + k * w * 0.2,
                  y + h * 0.1), (cx - w * 1.0 + k * w * 0.3, y + h * 0.1)], colour)


# ---- The shell -------------------------------------------------------------------------------------------------------

def top():
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["top"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y
    (y0, y1) = L.SILVER_LINE["y"]
    reg.rect_(*at(-w / 2, y1), *at(w / 2, y0), SILVER)
    lg = L.LOGO                                               # PLAYSTATION 3, drawn along, then turned to read from the back
    length, height = lg["y"][1] - lg["y"][0], lg["height"]
    text = Image.new("L", (2400, 200), 0)
    f = ImageFont.truetype(FONTS + "arial.ttf", 150)
    ImageDraw.Draw(text).text((20, 100), "P L A Y S T A T I O N   3", font=f, fill=255, anchor="lm")
    text = text.crop(text.getbbox()).rotate(-90, expand=True)
    x0, y0_, x1, y1_ = reg.box(*at(lg["x"] - height / 2, lg["y"][1]), *at(lg["x"] + height / 2, lg["y"][0]))
    text = text.resize((round(x1 - x0), round(y1_ - y0_)), Image.LANCZOS)
    reg.img.paste(Image.new("RGBA", text.size, TEXT + (255,)), (round(x0), round(y0_)), text)
    return reg


def front():
    w, h = L.WIDTH, L.HEIGHT
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    (fx0, fx1), (fz0, fz1) = L.FLAP["x"], L.FLAP["z"]
    (px0, px1), (pz0, pz1), slant = L.PANEL["x"], L.PANEL["z"], L.PANEL["slant"]
    reg.poly([at(fx0, fz0), at(px0 + slant, fz0), at(px0, fz1), at(fx0, fz1)], shade(CASE, 0.06))   # the flap
    reg.line([at(px0 + slant, fz0), at(px0, fz1)], (2, 2, 3), 0.6)
    for k in range(3):
        reg.circle(*at(L.FLAP["dots"][0] + 3.0 * k, L.FLAP["dots"][1]), 0.5, (70, 70, 74))
    panel = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))     # the silver panel: brighter along its middle
    pd = ImageDraw.Draw(panel)
    for k in range(40):
        z = pz0 + (pz1 - pz0) * k / 40
        t = abs(k / 40 - 0.55)
        c = round(232 - 110 * t)
        pd.rectangle(reg.box(*at(px0, z + (pz1 - pz0) / 40), *at(px1, z)), fill=(c, c, c + 4, 255))
    mask = Image.new("L", reg.img.size, 0)
    ImageDraw.Draw(mask).polygon([reg.p(*at(px0 + slant, pz0)), reg.p(*at(px1, pz0)), reg.p(*at(px1, pz1)),
                                  reg.p(*at(px0, pz1))], fill=255)
    reg.img.paste(panel, (0, 0), mask)
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    reg.rect_(*at(sx0, sz1), *at(sx1, sz0), (14, 14, 16), r=1.0)
    ps_mark(reg, *at(*L.PS_MARK["at"]), L.PS_MARK["height"])
    ex, ez = L.EJECT["at"]
    reg.poly([at(ex - 2.0, ez + 0.2), at(ex + 2.0, ez + 0.2), at(ex, ez + 2.4)], (60, 60, 64))
    reg.rect_(*at(ex - 2.0, ez - 0.4), *at(ex + 2.0, ez - 1.0), (60, 60, 64))
    reg.rect_(*at(ex + 3.4, ez + 2.0), *at(ex + 7.4, ez - 1.6), (30, 30, 34), r=0.6)           # the eject sensor
    reg.text("I/⏻", "seguisym.ttf", 3.6, *at(*L.POWER["at"]), (200, 200, 204))
    lx, lz = L.LIGHT["at"]
    lw, lh = L.LIGHT["size"]
    reg.rect_(*at(lx - lw / 2, lz + lh / 2), *at(lx + lw / 2, lz - lh / 2), (120, 20, 16))     # standby: red
    reg.text("SONY", "timesbd.ttf", 3.2, *at(*L.SONY), (200, 200, 204))
    return reg


def plinth():
    (x0, x1), h = L.PLINTH["x"], L.PLINTH["height"]
    w = x1 - x0
    reg = Region(L.REGIONS["plinth"], w, h, rgb(L.COLOURS["plinth"]))
    for j in range(5):                                        # the grille: a mesh of small square holes
        for i in range(int(w / 3.0)):
            x = 1.5 + i * 3.0
            z = 4.0 + j * 3.2
            reg.rect_(x, h - z - 2.2, x + 2.0, h - z, (6, 6, 7))
    return reg


# ---- The DualShock 3 -------------------------------------------------------------------------------------------------

def pad():
    xs = [x for x, _ in L.PAD_RIGHT]
    w, d = 2 * max(xs), max(y for _, y in L.PAD_RIGHT)
    reg = Region(L.REGIONS["pad"], w, d, rgb("#18181B"))

    def at(x, y):
        return x + w / 2, d - y
    for name in ("left", "right"):                            # the discs' rims
        cx, cy = L.DISCS[name]
        reg.circle(*at(cx, cy), L.DISCS["r"], (24, 24, 27), outline=(44, 44, 48), width=0.5)
    dx, dy = L.DPAD["at"]
    span, arm = L.DPAD["span"] + 3.0, L.DPAD["arm"] + 3.0
    for a, b in ((span / 2, arm / 2), (arm / 2, span / 2)):   # the wells round the d-pad and the face buttons
        reg.rect_(*at(dx - a, dy + b), *at(dx + a, dy - b), (10, 10, 12), r=1.5)
    fx, fy = L.DISCS["right"]
    for a, b in ((15.5, 8.0), (8.0, 15.5)):
        reg.rect_(*at(fx - a, fy + b), *at(fx + a, fy - b), (10, 10, 12), r=1.5)
    r = 3.0
    for name, colour in SYMBOLS.items():                      # the symbols on the face buttons' tops
        cx, cy = at(*L.FACE[name])
        reg.circle(cx, cy, L.FACE["r"], rgb(L.COLOURS["key"]))
        if name == "triangle":
            reg.line([(cx, cy - r), (cx + r * 0.9, cy + r * 0.6), (cx - r * 0.9, cy + r * 0.6), (cx, cy - r)], colour,
                     0.45)
        elif name == "circle":
            reg.circle(cx, cy, r * 0.85, outline=colour, width=0.45)
        elif name == "cross":
            reg.line([(cx - r * 0.75, cy - r * 0.75), (cx + r * 0.75, cy + r * 0.75)], colour, 0.45)
            reg.line([(cx - r * 0.75, cy + r * 0.75), (cx + r * 0.75, cy - r * 0.75)], colour, 0.45)
        else:
            reg.rect_(cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7, None, outline=colour, width=0.45)
    reg.text("SONY", "timesbd.ttf", 5.0, *at(-1.8, 80.0), (170, 170, 176))
    reg.text("SELECT", "arial.ttf", 2.4, *at(L.SMALL["select"][0], L.SMALL["select"][1] + 4.6), (190, 190, 196))
    reg.text("START", "arial.ttf", 2.4, *at(L.SMALL["start"][0], L.SMALL["start"][1] + 4.6), (190, 190, 196))
    px, py = at(*L.SMALL["ps"])
    reg.circle(px, py, L.SMALL["ps_r"], (20, 20, 22))
    reg.text("PS", "ariblk.ttf", 3.2, px, py, (200, 200, 206))
    for k, x in enumerate(L.LIGHTS["x"]):
        reg.text(str(k + 1), "arial.ttf", 1.6, *at(x, L.LIGHTS["y"] - 2.4), (120, 120, 126))
    return reg


def disc():
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (20, 20, 24))
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
    reg.rect_(c - 58.0, c - 58.0, c + 58.0, c - 46.0, (18, 18, 20))                           # the black band
    reg.text("ODYSSEY", "ariblk.ttf", 9.0, c, c - 34.0, (255, 214, 70))
    reg.text("BD", "arialbd.ttf", 4.0, c + 38.0, c - 30.0, (230, 230, 236))
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), plinth(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("silver", SILVER), ("green", (60, 230, 90)), ("red", (220, 40, 30)), ("dark", (8, 8, 10)),
                         ("key", rgb(L.COLOURS["key"])), ("lit", (255, 50, 40))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "ps3_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
