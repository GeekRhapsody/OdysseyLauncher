"""The Sega Master System's printing, for the console theme's Master System model (tools/console-models/master_system.py).

Draws its atlas, its regions as master_system_layout.py places them, each in millimetres as the model's planar UVs map
it: the console's top seen from above (the red stripe, SEGA MASTER SYSTEM/Power Base, the red panel with RESET and
PAUSE, CARTRIDGE INPUT and the diagram, the back slope's vent holes); its front band seen from in front (POWER's
label, CONTROL 1 and 2 over the ports, the card slot and CARD INPUT); the cartridge's label (a made-up game, Odyssey,
on the red grid); the Control Pad's top (CONTROL PAD, the D-pad's well, the SEGA mark, 1 START and 2); and the
swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/master_system_print.py <out folder>

It writes master_system_print.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import master_system_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
RED = rgb(L.COLOURS["red"])
GREY = rgb(L.COLOURS["grey"])
WHITE = (236, 236, 234)
INK = (14, 14, 15)


def sega(reg, x, y, size, fill, outline=None, anchor="lm"):
    """SEGA's mark: heavy, wide, slanted capitals (an outline round them if given)."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(size * reg.sx)))
    if outline is not None:
        d.text(reg.p(x, y), "SEGA", font=f, fill=outline + (255,), anchor=anchor, stroke_width=max(1, round(0.3 * reg.sx)),
               stroke_fill=outline + (255,))
    d.text(reg.p(x, y), "SEGA", font=f, fill=fill + (255,), anchor=anchor)
    yc = reg.p(0, y)[1]
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.2, -0.2 * yc, 0, 1, 0)))


def boxed(reg, text, x0, y0, x1, y1, fill, ink, size, outline=None):
    reg.rect_(x0, y0, x1, y1, fill, outline=outline, width=0.3)
    reg.text(text, "arial.ttf", size, (x0 + x1) / 2, (y0 + y1) / 2, ink)


# ---- The top ---------------------------------------------------------------------------------------------------------

def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    (px0, px1), (py0, py1) = L.PANEL["x"], L.PANEL["y"]

    # The red stripe along the hood's front edge, either side of the panel.
    for a, b in ((-L.WIDTH / 2, px0), (px1, L.WIDTH / 2)):
        reg.rect_(*at(a, 10.6), *at(b, 9.6), RED)
        reg.rect_(*at(a, 12.4), *at(b, 12.0), shade(CASE, 0.18))

    sega(reg, *at(-124.0, 55.0), 8.6, WHITE, outline=(120, 120, 124))
    reg.text("MASTER SYSTEM/Power Base", "times.ttf", 7.4, *at(-97.0, 54.4), WHITE, anchor="lm")

    # The red panel: RESET and PAUSE across its back, CARTRIDGE INPUT over them, the diagram, the hatching at its front.
    reg.rect_(*at(px0, py1), *at(px1, py0), RED)
    by0, by1 = L.BUTTONS["y"]
    for (a, b), label, lx in ((L.BUTTONS["reset"], "RESET", 0), (L.BUTTONS["pause"], "PAUSE", 1)):
        x0, x1 = (px0 + 2.0, (px0 + px1) / 2 - 1.0) if lx == 0 else ((px0 + px1) / 2 + 1.0, px1 - 2.0)
        reg.rect_(*at(x0, by1 + 1.6), *at(x1, by0 - 1.6), INK, r=0.6)
        tx = (b + x1) / 2 if lx == 0 else (x0 + a) / 2
        reg.text(label, "arial.ttf", 3.0, *at(tx, (by0 + by1) / 2), WHITE)
        reg.rect_(*at(a - 0.6, by1 + 0.6), *at(b + 0.6, by0 - 0.6), (40, 40, 42), r=0.5)
    reg.text("CARTRIDGE  INPUT  ▲", "seguisym.ttf", 2.8, *at((px0 + px1) / 2 + 4.0, py1 - 3.0), WHITE)

    def line(points, width=0.35):
        reg.line([at(x, y) for x, y in points], WHITE, width)
    line([(22.0, 82.0), (22.0, 46.0), (60.0, 46.0)])
    line([(60.0, 70.0), (60.0, 82.0), (72.0, 82.0)])
    line([(75.0, 58.0), (88.0, 58.0), (88.0, 66.0)])
    line([(88.0, 50.0), (88.0, 40.0), (75.0, 40.0)])
    line([(88.0, 58.0), (96.0, 58.0)])
    boxed(reg, "CARTRIDGE", *at(14.0, 88.0), *at(36.0, 84.0), WHITE, INK, 2.2)
    boxed(reg, "CARD", *at(18.0, 34.0), *at(34.0, 30.0), WHITE, INK, 2.2)
    boxed(reg, "CONTROL 1", *at(66.0, 86.0), *at(88.0, 80.0), RED, WHITE, 2.1, outline=WHITE)
    boxed(reg, "CONTROL 2", *at(66.0, 43.0), *at(88.0, 37.0), RED, WHITE, 2.1, outline=WHITE)
    boxed(reg, "TV SYSTEM", *at(94.0, 62.0), *at(114.0, 54.0), INK, WHITE, 2.1, outline=WHITE)
    tri = [at(27.0, 74.0), at(27.0, 50.0), at(70.0, 62.0)]
    reg.poly(tri, INK)
    reg.poly([at(52.0, 64.2), at(52.0, 59.8), at(62.0, 62.0)], (60, 170, 70))
    reg.text("POWER ON", "arial.ttf", 2.2, *at(37.0, 62.0), WHITE)
    for k in range(40):                                   # the hatching along its front edge
        x = px0 + 2.0 + k * 2.8
        if x + 2.0 > px1:
            break
        line([(x, py0 + 1.0), (x + 2.0, py0 + 5.0)], 0.45)

    # The back slope's vent holes, four rows of small squares, broken where the slot's frame stands.
    for row in range(4):
        y = L.RIDGE[1] + 5.0 + row * 7.0
        for k in range(64):
            x = -L.WIDTH / 2 + 18.0 + k * 5.2
            if x > L.WIDTH / 2 - 18.0:
                break
            if L.SLOT["x"][0] - 6.0 < x < L.SLOT["x"][1] + 4.0 and row < 2:
                continue
            reg.rect_(*at(x, y + 1.6), *at(x + 2.8, y - 1.6), (6, 6, 7))
    return reg


# ---- The front band --------------------------------------------------------------------------------------------------

FRONT_H = L.BAND["bevel"][1]       # the front region's height: the band from the table to the bevel's top


def front():
    reg = Region(L.REGIONS["front"], L.WIDTH, FRONT_H, CASE)

    def at(x, z):
        return x + L.WIDTH / 2, FRONT_H - z
    (a, b) = L.POWER["x"]
    boxed(reg, "POWER", *at(a, 27.0), *at(b, 23.6), RED, WHITE, 2.6)
    reg.poly([at((a + b) / 2 - 0.9, 22.9), at((a + b) / 2 + 0.9, 22.9), at((a + b) / 2, 21.9)], WHITE)
    for k, x in enumerate(L.PORTS["at"]):
        boxed(reg, f"CONTROL  {k + 1}", *at(x - 13.0, 26.6), *at(x + 13.0, 23.2), CASE, WHITE, 2.4, outline=WHITE)
        reg.poly([at(x - 0.9, 22.5), at(x + 0.9, 22.5), at(x, 21.5)], WHITE)
        w, h = L.PORTS["size"]
        cz = (L.PORTS["z"][0] + L.PORTS["z"][1]) / 2
        reg.rect_(*at(x - w / 2, cz + h / 2), *at(x + w / 2, cz - h / 2), (8, 8, 9), r=1.6)
        for j in range(5):
            reg.circle(*at(x - 5.6 + 2.8 * j, cz + 1.3), 0.5, (150, 130, 80))
        for j in range(4):
            reg.circle(*at(x - 4.2 + 2.8 * j, cz - 1.3), 0.5, (150, 130, 80))
    x0, x1, z0, z1 = L.CARD["slot"]
    reg.rect_(*at(x0, z1), *at(x1, z0), (6, 6, 7))
    boxed(reg, "CARD   INPUT", *at(L.CARD["x"][1] + 14.0, 26.6), *at(L.CARD["x"][1] + 40.0, 23.0), CASE, WHITE, 2.4,
          outline=WHITE)
    reg.poly([at(L.CARD["x"][1] + 11.5, 24.8), at(L.CARD["x"][1] + 13.0, 25.8), at(L.CARD["x"][1] + 13.0, 23.8)], WHITE)
    for k in range(4):                                    # the bars beside it, growing
        xx, h = L.CARD["x"][1] + 4.0 + k * 1.4, 0.6 + 0.45 * k
        reg.rect_(*at(xx, 24.8 + h / 2), *at(xx + 0.6, 24.8 - h / 2), WHITE)
    reg.rect_(*at(-L.WIDTH / 2, L.BAND["z"][1] + 0.2), *at(L.WIDTH / 2, L.BAND["z"][1] - 0.4), RED)
    return reg


# ---- The cartridge's label and the pad -------------------------------------------------------------------------------

def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (214, 62, 58))
    step = 4.3
    for k in range(int(lw / step) + 1):
        reg.line([(k * step, 0.0), (k * step, lh)], (112, 22, 24), 0.25)
    for k in range(int(lh / step) + 1):
        reg.line([(0.0, k * step), (lw, k * step)], (112, 22, 24), 0.25)
    reg.text("Odyssey", "timesbd.ttf", 11.0, 4.0, 9.0, (252, 248, 240), anchor="lm")
    reg.text("™", "times.ttf", 3.0, 45.0, 4.6, (252, 248, 240))
    sega(reg, lw - 24.0, lh - 6.0, 6.6, (252, 248, 240))
    return reg


def pad():
    w, d, _ = L.PAD["size"]
    reg = Region(L.REGIONS["pad"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d / 2 - y
    x0, x1, y0, y1 = L.PAD["well"]
    reg.rect_(*at(x0 - 3.0, y1 + 3.0), *at(x1 + 3.0, y0 - 3.0), INK, r=1.0)
    reg.rect_(*at(x0 - 2.0, y1 + 2.0), *at(x1 + 2.0, y0 - 2.0), RED, r=0.8)
    reg.rect_(*at(x0 - 1.6, y1 + 1.6), *at(x1 + 1.6, y0 - 1.6), INK, r=0.6)
    reg.rect_(*at(x0, y1), *at(x1, y0), GREY)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for corner in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        reg.line([at(*corner), at(cx + (corner[0] - cx) * 0.62, cy + (corner[1] - cy) * 0.62)], INK, 0.5)
    for dx, dy, glyph in ((0.0, 14.6, "▲"), (0.0, -14.6, "▼"), (-17.6, 0.0, "◀"), (17.6, 0.0, "▶")):
        reg.text(glyph, "seguisym.ttf", 2.0, *at(cx + dx, cy + dy), (220, 220, 220))
    reg.text("CONTROL PAD", "timesbd.ttf", 4.4, *at(cx, y1 + 5.6), WHITE)
    sx0, sx1, sy0, sy1 = L.PAD["stripes"]
    for k in range(13):
        x = sx0 + k * (sx1 - sx0) / 12
        reg.line([at(x, sy0), at(x, sy1)], (70, 70, 74), 0.45)
    sega(reg, *at((sx0 + sx1) / 2, (sy0 + sy1) / 2), 5.2, WHITE, anchor="mm")
    b = L.PAD["buttons"]
    for k, x in enumerate(b["x"]):
        reg.rect_(*at(x - 9.5, b["y"] + 9.0), *at(x + 9.5, b["y"] - 9.0), GREY, r=0.6)
        reg.rect_(*at(x - 9.5, b["y"] + 14.0), *at(x + 9.5, b["y"] + 10.2), RED)
        reg.text("1  START" if k == 0 else "2", "arialbd.ttf", 2.5, *at(x, b["y"] + 12.1), WHITE)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), label(), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name in ("dark", "grey", "red", "button"):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(L.COLOURS[name]))
    path = os.path.join(out, "master_system_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
