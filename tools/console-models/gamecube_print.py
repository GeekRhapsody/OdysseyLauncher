"""The Nintendo GameCube's printing, for the console theme's GameCube model (tools/console-models/gamecube.py).

Draws its two atlases, their regions as gamecube_layout.py places them, each in millimetres as the model's planar UVs
map it. gamecube_print.png: the console seen from above (the lid's seam, its black window with NINTENDO GAMECUBE, the
buttons' sockets and names, Nintendo's name); the front panel seen from in front (the ports' rims and their dots, the
memory card slots and their names); the controller's top (the sticks' rims and gates, START/PAUSE, the logo); and the
swatches small parts take their colour from. gamecube_disc.png: the mini disc's label side (a made-up game, Odyssey)
and its shiny side. Run it with the system Python (Pillow):

    python tools/console-models/gamecube_print.py <out folder>

It writes gamecube_print.png and gamecube_disc.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamecube_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
GREY = rgb(L.COLOURS["grey"])
LOGO_GREY = (200, 202, 206)


def logo(reg, cx, cy, w, colour):
    """NINTENDO over GAMECUBE, w across, its middle at (cx, cy)."""
    reg.text("N I N T E N D O", "arialbd.ttf", w * 0.105, cx, cy - w * 0.1, colour)
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(w * 0.2 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(cx, cy + w * 0.06), "GAMECUBE", font=f, fill=colour + (255,), anchor="mm")
    reg.over(layer)


def octagon(cx, cy, r, turn=22.5):
    return [(cx + r * math.cos(math.radians(turn + 45 * k)), cy + r * math.sin(math.radians(turn + 45 * k)))
            for k in range(8)]


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    (x0, x1), (y0, y1) = L.LID["x"], L.LID["y"]
    reg.rect_(*at(x0, y1), *at(x1, y0), None, r=4.0, outline=shade(CASE, -0.35), width=0.5)
    for name, (x, y, r) in L.BUTTONS.items():
        reg.circle(*at(x, y), r + 1.6, shade(CASE, -0.12))
        reg.circle(*at(x, y), r + 1.6, None, outline=shade(CASE, -0.35), width=0.4)
        label = name.upper()
        lx = x + (12.0 if x < 0 else -12.0)
        reg.text(label, "arial.ttf", 2.2, *at(lx, y + (6.0 if y < 80 else -6.0)), shade(CASE, -0.3))
    wx, wy = L.WINDOW["at"]
    reg.circle(*at(wx, wy), L.WINDOW["r"], rgb(L.COLOURS["dark"]))
    logo(reg, *at(wx, wy), 40.0, LOGO_GREY)
    nx, ny = 44.0, 146.0
    reg.rect_(*at(nx - 14.0, ny + 3.0), *at(nx + 14.0, ny - 3.0), None, r=3.0, outline=shade(CASE, 0.18), width=0.35)
    reg.text("Nintendo", "arialbd.ttf", 3.6, *at(nx, ny), shade(CASE, 0.18))
    return reg


def panel():
    (x0, x1), (z0, z1) = L.PANEL["x"], L.PANEL["z"]
    w, h = x1 - x0, z1 - z0
    reg = Region(L.REGIONS["panel"], w, h, GREY)

    def at(x, z):
        return x - x0, z1 - z
    for k, x in enumerate(L.PORTS["x"]):
        reg.circle(*at(x, L.PORTS["z"]), L.PORTS["r"] + 2.4, shade(GREY, -0.08))
        for j in range(k + 1):
            reg.circle(*at(x - (k * 2.0) / 2 + 2.0 * j, L.PORTS["z"] + L.PORTS["r"] + 6.0), 0.55, shade(GREY, -0.4))
    sw, sh = L.SLOTS["size"]
    for name, x in zip(("SLOT-A", "SLOT-B"), L.SLOTS["x"]):
        z = L.SLOTS["z"]
        reg.rect_(*at(x - sw / 2 - 2.0, z + sh / 2 + 2.0), *at(x + sw / 2 + 2.0, z - sh / 2 - 2.0), shade(GREY, -0.05),
                  r=1.5, outline=shade(GREY, -0.3), width=0.35)
        reg.rect_(*at(x - sw / 2, z + sh / 2), *at(x + sw / 2, z - sh / 2), shade(GREY, -0.5), r=0.8)
        reg.text(name, "arial.ttf", 2.6, *at(x, z - sh / 2 - 5.0), shade(GREY, -0.35))
    reg.circle(*at(L.PORTS["x"][0], L.PORTS["z"] + L.PORTS["r"] + 13.0), 0.9, (40, 80, 50))   # the power light, off
    return reg


def pad():
    w, length = 150.0, L.PAD["length"]
    reg = Region(L.REGIONS["pad"], w, length, CASE)
    p = L.PAD

    def at(x, y):
        return x + w / 2, length - y
    sx, sy = p["stick"]
    reg.circle(*at(sx, sy), p["rim"], shade(CASE, -0.12))
    reg.circle(*at(sx, sy), p["rim"] - 2.0, shade(CASE, 0.04))
    reg.poly([at(x, y) for x, y in octagon(sx, sy, p["gate"])], shade(CASE, -0.3))
    cx, cy = p["c"]
    reg.circle(*at(cx, cy), p["c_gate"] + 2.5, shade(CASE, -0.08))
    reg.poly([at(x, y) for x, y in octagon(cx, cy, p["c_gate"])], (226, 160, 20))
    ax, ay, ar = p["a"]
    reg.circle(*at(ax, ay), ar + 2.0, shade(CASE, -0.1))
    dx, dy, span, _ = p["dpad"]
    reg.circle(*at(dx, dy), span / 2 + 2.5, shade(CASE, -0.08))
    reg.text("START/PAUSE", "arialbd.ttf", 2.3, *at(p["start"][0], p["start"][1] + 7.0), shade(CASE, -0.3))
    logo(reg, *at(*p["logo"]), 36.0, (214, 214, 222))
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), panel(), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("grey", GREY), ("dark", rgb(L.COLOURS["dark"])), ("green", (40, 186, 150)),
                         ("red", (214, 30, 40)), ("yellow", (250, 190, 30)), ("white", (226, 226, 230)),
                         ("case", CASE), ("lit", (90, 255, 140))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "gamecube_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The disc --------------------------------------------------------------------------------------------------------

def disc_side(region, label):
    x, y, w, h = region
    r = L.DISC["r"]
    reg = Region(region, 2 * r, 2 * r, (40, 40, 44))
    c = r
    if label:
        art = space((600, 600))
        d = ImageDraw.Draw(art)
        ship(d, 220, 250, 3.6, "#FFFFFF", "#FFB23C")
        x0, y0, x1, y1 = reg.box(0.0, 0.0, 2 * r, 2 * r)
        reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (0, 0))
        reg.rect_(0.0, c + 10.0, 2 * r, 2 * r, (18, 18, 20))
        reg.text("ODYSSEY", "ariblk.ttf", 9.0, c, c - 22.0, (255, 214, 70))
        logo(reg, c, c + 20.0, 26.0, (220, 220, 226))
    else:
        for k in range(60):                                  # the shiny side: silver, a faint rainbow sheen
            t = k / 60
            colour = (round(196 + 22 * math.sin(6.3 * t)), round(198 + 22 * math.sin(6.3 * t + 2.1)),
                      round(204 + 22 * math.sin(6.3 * t + 4.2)))
            reg.circle(c, c, r * (1 - t * 0.8), colour)
    reg.circle(c, c, 11.0, (205, 208, 214))
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
    path = os.path.join(out, "gamecube_disc.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    disc_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
