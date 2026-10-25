"""The Panasonic FZ-1's printing, for the console theme's 3DO model (tools/console-models/threedo.py).

Draws its two atlases, their regions as threedo_layout.py places them, each in millimetres as the model's planar UVs
map it. threedo_print.png: the console seen from above (the plate's grain, Panasonic embossed, R.E.A.L. and 3DO
INTERACTIVE MULTIPLAYER outlined); the face between its front pods (the door with Panasonic in gold, READY and the 3DO
mark, R.E.A.L. FZ-1, ACCESS, the compact disc mark, the CONTROLLER port, the lights' windows off); the controller's top
(the D-pad's dish, Panasonic, the 3DO mark, the stop and play/pause marks, PHONES and VOL); and the swatches small parts
take their colour from. threedo_disc.png: the CD's label side (a made-up game, Odyssey, with the 3DO mark) and its
shiny side. Run it with the system Python (Pillow):

    python tools/console-models/threedo_print.py <out folder>

It writes threedo_print.png and threedo_disc.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import threedo_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
PLATE = shade(CASE, 0.06)
GOLD = (214, 192, 122)
GREY_TEXT = (150, 150, 152)
BRONZE = (138, 116, 92)
BEIGE = (184, 170, 146)


def mark_3do(reg, x, y, h, colour=True, ink=(230, 230, 230), box=(14, 14, 16)):
    """The 3DO mark, h tall, its top middle at (x, y): the red diamond, the blue cushion, the yellow ball and its
    shadow over 3DO in a black box (or all in one ink, the console's small version)."""
    s = h / 10.0
    red, blue, yellow = ((230, 30, 30), (20, 20, 160), (250, 220, 30)) if colour else (ink, ink, ink)
    reg.poly([(x, y), (x + 1.5 * s, y + 1.5 * s), (x, y + 3.0 * s), (x - 1.5 * s, y + 1.5 * s)], red)
    cushion = []
    for k in range(17):
        a = 2 * math.pi * k / 16
        r = 1.0 + 0.08 * math.cos(4 * a)
        cushion.append((x + 1.45 * s * r * math.cos(a), y + 4.05 * s + 1.0 * s * r * math.sin(a)))
    reg.poly(cushion, blue)
    reg.circle(x, y + 6.25 * s, 1.2 * s, yellow)
    reg.rect_(x - 1.6 * s, y + 7.55 * s, x + 1.6 * s, y + 7.85 * s, (110, 110, 110) if colour else ink)
    reg.rect_(x - 2.4 * s, y + 8.2 * s, x + 2.4 * s, y + 10.0 * s, box)
    reg.text("3DO", "timesbd.ttf", 1.55 * s, x, y + 9.1 * s, (255, 255, 255) if colour else ink)


def cd_mark(reg, x, y, h, ink):
    """The compact disc mark, h tall, its middle at (x, y): COMPACT over disc over DIGITAL AUDIO."""
    reg.text("COMPACT", "arialbd.ttf", h * 0.16, x + h * 0.25, y - h * 0.36, ink)
    reg.text("disc", "arialbd.ttf", h * 0.62, x, y + h * 0.02, ink)
    reg.text("DIGITAL AUDIO", "arialbd.ttf", h * 0.13, x, y + h * 0.4, ink)


def emboss(reg, text, font, size, x, y, base, light=0.18, dark=-0.45, depth=0.6):
    """Raised lettering: lit along its upper left, shadowed along its lower right, the face in the base colour."""
    for (dx, dy), colour in (((-depth, -depth), shade(base, light)), ((depth, depth), shade(base, dark)),
                             ((0.0, 0.0), shade(base, -0.06))):
        reg.text(text, font, size, x + dx, y + dy, colour)


# ---- The console -------------------------------------------------------------------------------------------------------

def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    (x0, x1), (y0, y1) = L.PLATE["x"], L.PLATE["y"]
    reg.rect_(*at(x0, y1), *at(x1, y0), PLATE, r=L.PLATE["r"])
    rng = random.Random(3)
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    for _ in range(26000):                                   # the plate's sandy grain
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        v = rng.choice([shade(PLATE, 0.12), shade(PLATE, -0.15)])
        d.point(reg.p(*at(x, y)), fill=v + (140,))
    reg.over(layer)
    emboss(reg, "Panasonic", "ariblk.ttf", 30.0, *at(0.0, 150.0), PLATE)
    reg.text("R·E·A·L", "arial.ttf", 9.0, *at(14.0, 122.0), GREY_TEXT)
    reg.line([at(-26.0, 115.0), at(52.0, 115.0)], GREY_TEXT, 0.4)
    reg.text("3DO INTERACTIVE MULTIPLAYER", "arial.ttf", 3.4, *at(14.0, 111.0), GREY_TEXT)
    return reg


FRONT_W = L.FRONT["x"][1] - L.FRONT["x"][0]
FRONT_H = L.FRONT["z"][1]


def front():
    reg = Region(L.REGIONS["front"], FRONT_W, FRONT_H, CASE)

    def at(x, z):
        return x - L.FRONT["x"][0], FRONT_H - z
    (dx0, dx1), (dz0, dz1) = L.DOOR["x"], L.DOOR["z"]
    reg.rect_(*at(dx0, dz1), *at(dx1, dz0), rgb(L.COLOURS["dark"]))
    reg.rect_(*at(dx0 + 0.6, dz1 - 0.6), *at(dx1 - 0.6, dz1 - 1.6), (34, 34, 38))      # its top edge's sheen
    reg.text("Panasonic", "arialbd.ttf", 7.4, *at(0.0, (dz0 + dz1) / 2 - 1.5), GOLD)
    reg.text("R·E·A·L", "arial.ttf", 4.0, *at(2.0, 33.0), GREY_TEXT)
    reg.line([at(-28.0, 30.4), at(32.0, 30.4)], GREY_TEXT, 0.3)
    reg.text("3DO INTERACTIVE MULTIPLAYER", "arial.ttf", 2.6, *at(2.0, 28.4), GREY_TEXT)
    reg.line([at(-28.0, 26.4), at(32.0, 26.4)], GREY_TEXT, 0.3)
    reg.text("FZ-1", "arial.ttf", 2.8, *at(2.0, 23.6), GREY_TEXT)
    w, h = L.LIGHTS["size"]
    for name, colour in (("ready", (30, 70, 34)), ("access", (80, 52, 18))):
        x, z = L.LIGHTS[name]
        reg.rect_(*at(x - w / 2, z + h / 2), *at(x + w / 2, z - h / 2), colour, r=0.5)
        reg.text(name.upper(), "arial.ttf", 2.8, *at(x, z + 4.0), GREY_TEXT)
    mark_3do(reg, *at(-62.0, 28.0), 13.0, colour=False, ink=(200, 200, 200), box=(40, 40, 44))
    cd_mark(reg, *at(62.0, 21.0), 9.0, GREY_TEXT)
    reg.rect_(*at(14.0, 16.0), *at(30.0, 10.0), (14, 14, 16), r=1.0)          # the CONTROLLER port
    for k in range(5):
        reg.circle(*at(16.5 + 2.75 * k, 14.0), 0.45, (150, 130, 80))
    for k in range(4):
        reg.circle(*at(17.9 + 2.75 * k, 12.0), 0.45, (150, 130, 80))
    reg.text("CONTROLLER", "arialbd.ttf", 2.2, *at(44.0, 13.0), shade(CASE, 0.25))
    return reg


def pad():
    w, d = L.PAD["size"]
    reg = Region(L.REGIONS["pad"], w, d, rgb(L.COLOURS["controller"]))
    p = L.PAD

    def at(x, y):
        return x + w / 2, d / 2 - y
    base = rgb(L.COLOURS["controller"])
    dx, dy, _, _ = p["dpad"]
    reg.circle(*at(dx, dy), p["dish"] + 2.0, shade(base, 0.25))
    reg.circle(*at(dx, dy), p["dish"], shade(base, -0.35))
    for k, glyph in enumerate(("▷▷", "◁◁")):              # the fast-forward and rewind marks round the dish
        a = math.radians(55 if k == 0 else 235)
        reg.text(glyph, "seguisym.ttf", 2.4, *at(dx + 21.0 * math.cos(a), dy + 21.0 * math.sin(a)),
                 shade(base, 0.45))
    for (x, y), name in zip(p["abc"], "ABC"):
        reg.circle(*at(x, y), p["abc_r"] + 1.0, shade(base, -0.25))
        reg.text(name, "arialbd.ttf", 3.6, *at(x - 9.5, y - 2.0), shade(base, 0.55))
    sw, sh = p["small"]
    for (x, y), glyph in ((p["stop"], "■"), (p["play"], "►/II")):
        reg.rect_(*at(x - sw / 2 - 0.8, y + sh / 2 + 0.8), *at(x + sw / 2 + 0.8, y - sh / 2 - 0.8), shade(base, -0.25),
                  r=sh / 2 + 0.8)
        reg.text(glyph, "seguisym.ttf", 2.6, *at(x, y + 5.0), shade(base, 0.55))
    reg.text("Panasonic", "arialbd.ttf", 5.6, *at(*p["logo"]), (226, 226, 230))
    mark_3do(reg, *at(0.0, -6.0), 9.0, colour=False, ink=(200, 200, 204), box=shade(base, -0.4))
    reg.text("PHONES", "arialbd.ttf", 2.2, *at(-20.0, -26.0), shade(base, 0.5))
    reg.text("VOL ◢", "seguisym.ttf", 2.2, *at(18.0, -26.0), shade(base, 0.5))
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("bronze", BRONZE), ("beige", BEIGE), ("green", (110, 255, 120)), ("amber", (255, 170, 40)),
                         ("dark", rgb(L.COLOURS["dark"])), ("plate", PLATE), ("green_off", (30, 70, 34)),
                         ("amber_off", (80, 52, 18))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "threedo_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The disc --------------------------------------------------------------------------------------------------------

def disc_side(region, label):
    r = L.DISC["r"]
    reg = Region(region, 2 * r, 2 * r, (40, 40, 44))
    c = r
    if label:
        art = space((700, 700))
        d = ImageDraw.Draw(art)
        ship(d, 230, 300, 4.0, "#FFFFFF", "#FFB23C")
        x0, y0, x1, y1 = reg.box(0.0, 0.0, 2 * r, 2 * r)
        reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (0, 0))
        reg.text("ODYSSEY", "ariblk.ttf", 15.0, c, c - 34.0, (255, 214, 70))
        reg.rect_(0.0, c + 18.0, 2 * r, 2 * r, (14, 14, 16))
        mark_3do(reg, c - 30.0, c + 24.0, 22.0)
        reg.text("INTERACTIVE MULTIPLAYER", "arialbd.ttf", 3.4, c + 14.0, c + 34.0, (220, 220, 224))
    else:
        for k in range(60):                                  # the shiny side: silver, a faint rainbow sheen
            t = k / 60
            colour = (round(196 + 22 * math.sin(6.3 * t)), round(198 + 22 * math.sin(6.3 * t + 2.1)),
                      round(204 + 22 * math.sin(6.3 * t + 4.2)))
            reg.circle(c, c, r * (1 - t * 0.8), colour)
    reg.circle(c, c, 17.0, (205, 208, 214))
    reg.circle(c, c, L.DISC["hole"], (30, 30, 34))
    mask = Image.new("L", reg.img.size, 0)
    ImageDraw.Draw(mask).ellipse(reg.box(0.0, 0.0, 2 * r, 2 * r), fill=255)
    out = Image.new("RGBA", reg.img.size, (190, 192, 198, 255))
    out.paste(reg.img, (0, 0), mask)
    reg.img = out
    return reg


def disc_atlas(out):
    image = Image.new("RGB", (L.DISC_ATLAS, L.DISC_ATLAS), (190, 192, 198))
    disc_side(L.DISC_REGIONS["label"], True).paste(image)
    disc_side(L.DISC_REGIONS["data"], False).paste(image)
    path = os.path.join(out, "threedo_disc.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    disc_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
