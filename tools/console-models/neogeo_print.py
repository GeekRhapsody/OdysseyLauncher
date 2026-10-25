"""The Neo Geo AES's printing, for the console theme's Neo Geo model (tools/console-models/neogeo.py).

Draws its two atlases, their regions as neogeo_layout.py places them, each in millimetres as the model's planar UVs
map it. neogeo_print.png: the console seen from above (SNK, the gold NEO-GEO with MAX 330 MEGA, PRO-GEAR SPEC and
ADVANCED ENTERTAINMENT SYSTEM, the panels' seams, RESET and POWER ON-OFF, MEMORY CARD IN, the slits at the back
corners) and its front face (the controller ports, PHONES, VOLUME), with the swatches small parts take their colour
from. neogeo_pad.png: the stick seen from above (SNK, the lever's dish, the dark arc behind the buttons, PAD A to D,
SELECT and START, NEO-GEO) and the cartridge's label (a made-up game, Odyssey), with swatches. Run it with the system
Python (Pillow):

    python tools/console-models/neogeo_print.py <out folder>

It writes neogeo_print.png and neogeo_pad.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neogeo_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
GOLD = (176, 156, 104)
WHITE = (226, 226, 226)
SEAM = shade(CASE, -0.45)


def slanted(reg, text, font, size, x, y, fill, shear=0.2, anchor="mm"):
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(x, y), text, font=f, fill=fill + (255,), anchor=anchor)
    yc = reg.p(0, y)[1]
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, shear, -shear * yc, 0, 1, 0)))


def neo_geo(reg, x, y, size):
    """NEO-GEO's lettering, its middle at (x, y), size tall: the gold name, MAX 330 MEGA, PRO-GEAR SPEC, ADVANCED
    ENTERTAINMENT SYSTEM."""
    reg.text("NEO·GEO", "times.ttf", size * 1.5, x, y, GOLD)
    slanted(reg, "MAX 330 MEGA", "ariblk.ttf", size * 0.38, x + size * 0.6, y + size * 0.95, WHITE)
    reg.text("PRO–GEAR SPEC", "arial.ttf", size * 0.38, x + size * 0.6, y + size * 1.45, WHITE)
    reg.text("ADVANCED ENTERTAINMENT SYSTEM", "arial.ttf", size * 0.38, x + size * 0.6, y + size * 1.95, WHITE)


def snk(reg, x, y, size, fill=WHITE):
    slanted(reg, "SNK", "ariblk.ttf", size, x, y, fill, shear=0.25)


# ---- The console -------------------------------------------------------------------------------------------------------

def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    # The panels' seams: the corner panel at the front left, the middle panel, the memory card's panel.
    for (x0, y0), (x1, y1) in (((-112.0, 0.0), (-112.0, 66.0)), ((-112.0, 66.0), (-152.0, 70.0)),
                               ((-84.0, 0.0), (-72.0, L.TRACK["y"][0])), ((70.0, 0.0), (64.0, L.TRACK["y"][0])),
                               ((82.0, 0.0), (82.0, 100.0)), ((82.0, 100.0), (162.0, 104.0))):
        reg.line([at(x0, y0), at(x1, y1)], SEAM, 0.45)
    rx, ry = L.RESET["at"]
    reg.circle(*at(rx, ry), L.RESET["dish"], shade(CASE, -0.08))
    reg.circle(*at(rx, ry), L.RESET["dish"], None, outline=SEAM, width=0.4)
    reg.text("RESET", "arial.ttf", 2.8, *at(rx - 12.0, ry - 17.0), WHITE)
    reg.text("POWER", "arial.ttf", 2.8, *at(-140.0, 26.0), WHITE)
    reg.text("ON–OFF", "arial.ttf", 2.8, *at(-140.0, 22.0), WHITE)
    neo_geo(reg, *at(4.0, 76.0), 7.0)
    reg.text("MEMORY CARD IN", "arial.ttf", 2.8, *at(118.0, 30.0), WHITE)
    mx, my = at(118.0, 25.5)
    reg.poly([(mx - 1.6, my - 1.2), (mx + 1.6, my - 1.2), (mx, my + 1.4)], WHITE)
    snk(reg, *at(-142.0, 214.0), 6.4)
    for x0 in (-158.0, 120.0):                               # the slits at the back corners
        for k in range(9):
            x = x0 + k * 4.2
            reg.rect_(*at(x, 233.0), *at(x + 1.8, 226.0), (8, 8, 9), r=0.6)
    return reg


def front():
    reg = Region(L.REGIONS["front"], L.WIDTH, L.FRONT_H, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, L.FRONT_H - z
    (x0, x1), (z0, z1) = L.POWER["x"], L.POWER["z"]
    reg.rect_(*at(x0 - 1.5, z1 + 1.5), *at(x1 + 1.5, z0 - 1.5), (10, 10, 11), r=1.0)
    w, h = L.PORTS["size"]
    for k, x in enumerate(L.PORTS["x"]):
        z = L.PORTS["z"]
        reg.poly([at(x - w / 2, z + h / 2), at(x + w / 2, z + h / 2), at(x + w / 2 - 2.0, z - h / 2),
                  at(x - w / 2 + 2.0, z - h / 2)], (8, 8, 9))
        for j in range(8):
            reg.rect_(*at(x - 9.0 + 2.6 * j, z + 1.2), *at(x - 8.0 + 2.6 * j, z - 1.2), (120, 104, 70))
        reg.text("CONTROLLER", "arial.ttf", 1.8, *at(x, z - h / 2 - 2.0), shade(CASE, 0.3))
        reg.text(str(k + 1), "arial.ttf", 2.4, *at(x + w / 2 + 4.0, z + 3.0), shade(CASE, 0.3))
    reg.circle(*at(-45.0, 11.0), 1.8, (8, 8, 9))
    reg.text("PHONES", "arial.ttf", 1.9, *at(-45.0, 16.0), shade(CASE, 0.3))
    reg.rect_(*at(-28.0, 9.5), *at(2.0, 8.0), (8, 8, 9))
    reg.rect_(*at(-3.0, 11.0), *at(-1.0, 6.5), (200, 200, 200))
    reg.text("VOLUME", "arial.ttf", 1.9, *at(-13.0, 13.0), shade(CASE, 0.3))
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("dark", rgb(L.COLOURS["dark"])), ("button", rgb(L.COLOURS["button"])), ("gold", GOLD),
                         ("lit", (255, 60, 40)), ("case", CASE)):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "neogeo_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The stick and the label -------------------------------------------------------------------------------------------

def stick():
    w, d = L.PAD["size"]
    reg = Region(L.PAD_REGIONS["stick"], w, d, CASE)
    p = L.PAD

    def at(x, y):
        return x + w / 2, d / 2 - y
    dx, dy, r = p["dish"]
    reg.circle(*at(dx, dy), r, shade(CASE, 0.05))
    reg.circle(*at(dx, dy), r, None, outline=shade(CASE, -0.4), width=0.5)
    # The dark arc behind the buttons: a band through them.
    layer = reg.layer()
    dl = ImageDraw.Draw(layer)
    pts = [at(x, y) for x, y in p["buttons"]]
    dl.line([reg.p(*q) for q in pts], fill=shade(CASE, -0.4) + (255,), width=round(2 * (p["button_r"] + 4.0) * reg.sx),
            joint="curve")
    for q in (pts[0], pts[-1]):
        dl.ellipse(reg.box(q[0] - p["button_r"] - 4.0, q[1] - p["button_r"] - 4.0, q[0] + p["button_r"] + 4.0,
                           q[1] + p["button_r"] + 4.0), fill=shade(CASE, -0.4) + (255,))
    reg.over(layer)
    for (x, y), name in zip(p["buttons"], "ABCD"):
        reg.text(f"PAD {name}", "arial.ttf", 3.0, *at(x - 6.0, y + p["button_r"] + 6.0), WHITE)
    for (x, y), name in ((p["select"], "SELECT"), (p["start"], "START")):
        reg.text(name, "arial.ttf", 3.0, *at(x, y - p["small"][1] / 2 - 4.0), WHITE)
    snk(reg, *at(-108.0, 76.0), 8.0)
    neo_geo(reg, *at(-4.0, -42.0), 8.0)
    return reg


def label():
    lw, lh = L.CART["label"]
    reg = Region(L.PAD_REGIONS["label"], lw, lh, (20, 20, 22))
    art = space((700, 640))
    d = ImageDraw.Draw(art)
    ship(d, 260, 380, 4.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 14.0, lw, lh)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 14.0, (12, 12, 14))
    reg.text("NEO·GEO", "times.ttf", 9.0, lw / 2, 7.4, GOLD)
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(15.0 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(lw / 2, 30.0), "ODYSSEY", font=f, fill=(255, 196, 40, 255), anchor="mm",
                               stroke_width=max(1, round(1.0 * reg.sx)), stroke_fill=(120, 30, 10, 255))
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.25, -0.25 * reg.p(0, 30.0)[1], 0, 1, 0)))
    reg.rect_(0.0, lh - 9.0, lw, lh, (12, 12, 14))
    reg.text("MAX 330 MEGA  ·  PRO-GEAR SPEC", "arialbd.ttf", 3.6, lw / 2, lh - 4.5, WHITE)
    return reg


def pad_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (stick(), label()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("dark", rgb(L.COLOURS["dark"])), ("button", rgb(L.COLOURS["button"])),
                         ("ball", (30, 30, 34))):
        x, y = L.PAD_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "neogeo_pad.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    pad_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
