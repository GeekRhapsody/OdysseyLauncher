"""The Nintendo 64's printing, for the console theme's Nintendo 64 model (tools/console-models/n64.py).

Draws its atlas, its regions as n64_layout.py places them, each in millimetres as the model's planar UVs map it: the
console seen from above (POWER's well with OFF and ON, RESET, the memory expansion's lid, Nintendo's name behind the
slot); its front face (the NINTENDO 64 window with the cube N, the power light off); the controller's top (its body's
grey, the D-pad's dish, the stick's well and gate, the C buttons' diamond, the dark shoulders, Nintendo's name); the
cartridge's label (a made-up game, Odyssey); and the swatches small parts take their colour from. Run it with the
system Python (Pillow):

    python tools/console-models/n64_print.py <out folder>

It writes n64_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n64_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
PAD = rgb(L.COLOURS["controller"])
CUBE = dict(green=(0, 150, 60), blue=(0, 70, 190), red=(220, 30, 40), yellow=(250, 200, 0))


def embossed(reg, text, cx, cy, w, h, base, font="arialbd.ttf"):
    """Nintendo's name raised in an oval: lit along its top, shadowed along its bottom."""
    for (dx, dy), colour in (((0.0, -0.25), shade(base, 0.22)), ((0.0, 0.25), shade(base, -0.3)), ((0, 0), base)):
        reg.rect_(cx - w / 2 + dx, cy - h / 2 + dy, cx + w / 2 + dx, cy + h / 2 + dy, None, r=h / 2, outline=colour,
                  width=0.35)
        reg.text(text, font, h * 0.62, cx + dx, cy + dy, colour)


def cube_n(reg, x, y, s):
    """The cube N, s tall, its top left at (x, y): two pillars and the diagonal, green faces with blue sides, yellow
    and red tops."""
    d = s * 0.18                                  # the blocks' depth, drawn up and to the right
    w = s * 0.3
    for px in (x, x + s * 0.62):
        reg.poly([(px, y + d), (px + w, y + d), (px + w, y + s), (px, y + s)], CUBE["green"])
        reg.poly([(px + w, y + d), (px + w + d, y), (px + w + d, y + s - d), (px + w, y + s)], CUBE["blue"])
        reg.poly([(px, y + d), (px + d, y), (px + w + d, y), (px + w, y + d)], CUBE["yellow"])
    reg.poly([(x + w, y + d), (x + s * 0.62, y + s * 0.62), (x + s * 0.62, y + s), (x + w, y + s * 0.42)], CUBE["red"])


# ---- The console -------------------------------------------------------------------------------------------------------

def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    px, py = L.POWER["at"]
    ww, wd = L.POWER["well"]
    reg.rect_(*at(px - ww / 2, py + wd / 2), *at(px + ww / 2, py - wd / 2), shade(CASE, -0.35), r=ww / 2)
    reg.text("POWER", "arialbd.ttf", 2.6, *at(px + ww / 2 + 3.5, py), shade(CASE, 0.3))
    for k, word in enumerate(("OFF", "ON")):
        reg.text(word, "arial.ttf", 2.2, *at(px - ww / 2 - 6.0, py + 5.0 - k * 9.0), shade(CASE, 0.3))
    rx, ry = L.RESET["at"]
    reg.text("RESET", "arialbd.ttf", 2.6, *at(rx, ry - L.RESET["size"][1] / 2 - 4.0), shade(CASE, 0.3))
    lx, ly = L.LID["at"]
    lw, ld, _ = L.LID["size"]
    reg.text("MEMORY EXPANSION", "arialbd.ttf", 2.4, *at(lx, ly - ld / 2 + 4.0), shade(CASE, 0.25))
    for k in range(4):
        reg.circle(*at(lx - 6.0 + 4.0 * k, ly + 8.0), 0.5, shade(CASE, 0.3))
    reg.rect_(*at(lx - 5.0, ly + ld / 2 - 1.0), *at(lx + 5.0, ly + ld / 2 - 5.0), shade(CASE, -0.2), r=1.0)
    embossed(reg, "Nintendo", *at(0.0, L.LOGO_Y), 34.0, 7.5, shade(CASE, 0.06))
    return reg


FRONT_H = 36.0


def front():
    reg = Region(L.REGIONS["front"], L.WIDTH, FRONT_H, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, FRONT_H - z
    (x0, x1), (z0, z1) = L.WINDOW["x"], L.WINDOW["z"]
    reg.rect_(*at(x0, z1), *at(x1, z0), (10, 10, 12), r=4.0)
    reg.text("NINTENDO", "arialbd.ttf", 4.2, *at(-3.0, z1 - 4.4), (230, 230, 232))
    reg.text("64", "arialbd.ttf", 2.6, *at(14.5, z1 - 3.0), (230, 230, 232))
    cx, cz = 0.0, z0 + 7.0
    tx, ty = at(cx - 5.5, cz + 5.5)
    cube_n(reg, tx, ty, 11.0)
    lx, lz, (lw, lh) = L.LIGHT
    reg.rect_(*at(lx - lw / 2, lz + lh / 2), *at(lx + lw / 2, lz - lh / 2), (70, 16, 14), r=lh / 2)
    grey = rgb(L.COLOURS["grey"])
    pw, ph, _ = L.PORTS["size"]
    for x in L.PORTS["x"]:                                  # the ports' faces: the grey rim, the socket, three holes
        z = L.PORTS["z"]
        reg.rect_(*at(x - pw / 2, z + ph / 2), *at(x + pw / 2, z - ph / 2), grey, r=ph / 2)
        reg.rect_(*at(x - pw / 2 + 4.0, z + ph / 2 - 3.5), *at(x + pw / 2 - 4.0, z - ph / 2 + 3.5), shade(grey, 0.12),
                  r=ph / 2 - 3.5, outline=shade(grey, -0.35), width=0.4)
        for k in (-1, 0, 1):
            reg.circle(*at(x + 4.2 * k, z), 1.0, (40, 40, 44))
    return reg


# ---- The controller ----------------------------------------------------------------------------------------------------

def pad():
    w, length = 160.0, L.PAD["length"]
    reg = Region(L.REGIONS["pad"], w, length, PAD)
    p = L.PAD

    def at(x, y):
        return x + w / 2, length - y
    for side in (-1, 1):                                     # the shoulders' dark grey at the back corners
        reg.poly([at(side * x, y) for x, y in ((33.5, 146.0), (54.5, 142.0), (66.0, 136.0), (66.0, 128.0),
                                                (58.0, 128.5), (36.0, 136.0))], rgb(L.COLOURS["shoulder"]))
    dx, dy, _, _ = p["dpad"]
    reg.circle(*at(dx, dy), p["dish"], shade(PAD, 0.06))
    sx, sy = p["stick"]
    reg.circle(*at(sx, sy), p["well"], rgb(L.COLOURS["well"]))
    gate = [at(sx + p["gate"] * math.cos(math.radians(22.5 + 45 * k)), sy + p["gate"] * math.sin(math.radians(22.5 + 45 * k)))
            for k in range(8)]
    reg.poly(gate, shade(rgb(L.COLOURS["well"]), -0.25))
    cx = sum(x for x, _ in p["c"]) / 4
    cy = sum(y for _, y in p["c"]) / 4
    diamond = [at(cx, cy + 12.0), at(cx + 13.0, cy), at(cx, cy - 12.0), at(cx - 13.0, cy)]
    reg.poly(diamond, shade(PAD, 0.07))
    reg.text("C", "timesbd.ttf", 4.0, *at(cx + 0.5, cy), shade(PAD, -0.2))
    (bx, by, _), (ax, ay, _) = p["b"], p["a"]
    reg.line([at(bx, by), at(ax, ay)], shade(PAD, -0.12), 2.6)
    lx, ly, lw, lh = p["logo"]
    embossed(reg, "Nintendo", *at(lx, ly), lw, lh, shade(PAD, -0.02))
    return reg


def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (20, 14, 40))
    art = space((736, 416))
    d = ImageDraw.Draw(art)
    ship(d, 250, 250, 3.4, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 0.0, lw, lh)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (0, 0))
    reg.rect_(0.0, 0.0, lw, 11.0, (16, 16, 18))
    cube_n(reg, 2.5, 1.5, 8.0)
    reg.text("NINTENDO64", "arialbd.ttf", 4.0, 13.0, 5.6, (240, 240, 240), anchor="lm")
    reg.text("ODYSSEY", "ariblk.ttf", 10.0, lw / 2, 19.0, (255, 214, 70))
    reg.rect_(0.0, lh - 5.0, lw, lh, (16, 16, 18))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), label()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("grey", rgb(L.COLOURS["grey"])), ("red", (200, 50, 36)), ("blue", (36, 60, 190)),
                         ("green", (40, 140, 60)), ("yellow", (240, 200, 30)), ("lit", (255, 40, 30)),
                         ("dark", rgb(L.COLOURS["dark"])), ("well", rgb(L.COLOURS["well"])),
                         ("shoulder", rgb(L.COLOURS["shoulder"])), ("cap", (222, 222, 222)),
                         ("dpad", (88, 88, 92))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "n64_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
