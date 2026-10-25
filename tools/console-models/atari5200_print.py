"""The Atari 5200 set's printing, for the console theme's Atari 5200 model (tools/console-models/atari5200.py).

Draws its atlas, its regions as atari5200_layout.py places them, each in millimetres as the model's planar UVs map it:
the console's top seen from above along its slope (the brushed band with Atari's logo, ATARI 5200 and its rainbow line,
POWER ON/OFF, the light's window, the vents' slots, the lid's seam); the front face (the ports' panel, the four
ports and their numbers); the controller's top (the keypad's yellow legends, the ATARI 5200 strip, START, PAUSE and
RESET, the stick's well); the cartridge's label (a made-up game, Odyssey, in the style of the 5200's labels); and the
swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/atari5200_print.py <out folder>

It writes atari5200_print.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atari5200_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
SILVER = rgb(L.COLOURS["silver"])
SLOT_INK = (8, 8, 9)
RAINBOW = [(226, 64, 40), (240, 140, 36), (232, 210, 60), (90, 180, 70), (50, 120, 200)]
ORANGE = (230, 110, 50)
YELLOW = (240, 200, 40)


def fuji(reg, cx, cy, h, ink):
    """Atari's logo, h tall, its middle at (cx, cy): the middle bar, and the two outer bars flaring out at their feet."""
    t = h * 0.15
    reg.rect_(cx - t / 2, cy - h / 2, cx + t / 2, cy + h / 2, ink)
    for side in (-1, 1):
        x0 = cx + side * (t / 2 + h * 0.06)
        x1 = x0 + side * t
        foot0, foot1 = cx + side * h * 0.34, cx + side * h * 0.56
        reg.poly([(x0, cy - h / 2), (x1, cy - h / 2), (x1, cy - h * 0.05), (x1 + side * h * 0.06, cy + h * 0.2),
                  (foot1, cy + h / 2), (foot0, cy + h / 2), (x0 + side * h * 0.03, cy + h * 0.22),
                  (x0, cy - h * 0.02)], ink)


def rainbow_line(reg, x0, x1, y, width):
    n = len(RAINBOW)
    for k, colour in enumerate(RAINBOW):
        reg.rect_(x0 + (x1 - x0) * k / n, y - width / 2, x0 + (x1 - x0) * (k + 1) / n, y + width / 2, colour)


def brand(reg, x, y, h, ink, rainbow=True):
    """Atari's logo, ATARI and 5200, h tall, its left middle at (x, y), the rainbow line under the words."""
    fuji(reg, x + h * 0.45, y, h, ink)
    f = ImageFont.truetype(FONTS + "arialbi.ttf", max(1, round(h * 1.0 * reg.sx)))
    reg.draw.text(reg.p(x + h * 1.2, y + h * 0.06), "ATARI", font=f, fill=ink, anchor="lm")
    width = reg.draw.textlength("ATARI", font=f) / reg.sx
    reg.draw.text(reg.p(x + h * 1.2 + width + h * 0.8, y + h * 0.06), "5200", font=f, fill=ink, anchor="lm")
    if rainbow:
        rainbow_line(reg, x + h * 1.2, x + h * 1.2 + width + h * 0.8 + width * 0.95, y + h * 0.72, h * 0.12)


# ---- The console's top -------------------------------------------------------------------------------------------------

def top():
    w, d = L.WIDTH, L.TOP_LENGTH
    reg = Region(L.REGIONS["top"], w, d, CASE)

    def at(x, s):
        return x + w / 2, d - s

    def vents(x0, x1, s0, s1, pitch, width):
        x = x0 + pitch / 2
        while x < x1:
            reg.rect_(*at(x - width / 2, s1), *at(x + width / 2, s0), SLOT_INK)
            x += pitch
    v = L.FRONT_VENTS
    vents(*v["x"], *v["s"], v["pitch"], v["width"])
    for block in L.SLOT_VENTS:
        vents(*block["x"], *L.SLOT_VENT_S, v["pitch"], v["width"])
    (sx0, sx1), (ss0, ss1) = L.SILVER["x"], L.SILVER["s"]
    reg.rect_(*at(sx0, ss1), *at(sx1, ss0), SILVER)
    for k in range(90):                                        # the brushed grain along it
        s = ss0 + (ss1 - ss0) * (k + 0.5) / 90
        reg.line([at(sx0, s), at(sx1, s)], shade(SILVER, 0.05 if k % 3 else -0.05), 0.2)
    brand(reg, *at(sx0 + 30.0, ss0 + 26.0), 9.0, (108, 110, 114))
    (px0, px1), (ps0, ps1) = L.POWER["x"], L.POWER["s"]
    reg.rect_(*at(px0 - 1.0, ps1 + 1.0), *at(px1 + 1.0, ps0 - 1.0), SLOT_INK)
    reg.rect_(*at(px0, ps1), *at(px1, ps0), shade(CASE, 0.06))
    reg.text("POWER ON/OFF", "arialbd.ttf", 2.6, *at((px0 + px1) / 2, ps1 - 4.0), ORANGE)
    lx, ls, lr = L.LIGHT["x"], L.LIGHT["s"], L.LIGHT["r"]
    reg.circle(*at(lx, ls), lr + 0.6, SLOT_INK)
    reg.circle(*at(lx, ls), lr, (60, 16, 14))
    (cx0, cx1), (cs0, cs1) = L.SLOT["x"], L.SLOT["s"]
    reg.rect_(*at(cx0 - 3.0, cs1 + 3.0), *at(cx1 + 3.0, cs0 - 3.0), shade(CASE, -0.3), r=2.0)
    reg.rect_(*at(cx0, cs1), *at(cx1, cs0), SLOT_INK)
    ls0 = L.LID["s"][0]
    reg.line([at(-w / 2, ls0), at(w / 2, ls0)], SLOT_INK, 0.6)              # the lid's seam
    reg.line([at(-w / 2, ls0 + 0.8), at(w / 2, ls0 + 0.8)], shade(CASE, 0.12), 0.3)
    return reg


# ---- The front face ----------------------------------------------------------------------------------------------------

def front():
    w, h = L.WIDTH, L.TOP[0][1]
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    (px0, px1), (pz0, pz1) = L.PORT_PANEL["x"], L.PORT_PANEL["z"]
    reg.rect_(*at(px0, pz1), *at(px1, pz0), shade(CASE, -0.25), r=1.0)
    pw, ph = L.PORTS["size"]
    for k, x in enumerate(L.PORTS["x"]):
        z = L.PORTS["z"]
        reg.rect_(*at(x - pw / 2, z + ph / 2), *at(x + pw / 2, z - ph / 2), (12, 12, 13), r=1.2)
        reg.rect_(*at(x - pw / 2 + 3.0, z + ph / 2 - 2.5), *at(x + pw / 2 - 3.0, z - ph / 2 + 2.5), (40, 40, 42), r=0.8)
        for j in range(8):
            reg.circle(*at(x - 10.5 + 3.0 * j, z + 1.4), 0.45, (180, 160, 100))
        for j in range(7):
            reg.circle(*at(x - 9.0 + 3.0 * j, z - 1.4), 0.45, (180, 160, 100))
        reg.text(str(k + 1), "arialbd.ttf", 2.6, *at(x - pw / 2 - 3.6, z), shade(CASE, 0.22))
    for x in range(-180, 181, 5):                               # the base's vents, under the face
        reg.rect_(*at(x - 1.1, L.BASE_VENTS["z"][1]), *at(x + 1.1, L.BASE_VENTS["z"][0]), SLOT_INK)
    return reg


# ---- The controller's top ----------------------------------------------------------------------------------------------

def pad():
    length, (w0, w1) = L.PAD["length"], L.PAD["width"]
    w = w1
    reg = Region(L.REGIONS["pad"], w, length, CASE)

    def at(x, y):
        return x + w / 2, length - y
    (ky0, ky1), (kx0, kx1) = L.KEYPAD["y"], L.KEYPAD["x"]
    reg.rect_(*at(kx0 - 5.0, ky1 + 3.0), *at(kx1 + 5.0, ky0 - 3.0), (14, 14, 15), r=2.0)
    legends = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"]
    kw, kd = L.KEYPAD["key"]
    rows, cols = L.KEYPAD["rows"], L.KEYPAD["cols"]
    for i in range(rows):
        for j in range(cols):
            x = kx0 + (kx1 - kx0) * j / (cols - 1)
            y = ky1 - kd / 2 - (ky1 - ky0 - kd) * i / (rows - 1)
            reg.rect_(*at(x - kw / 2, y + kd / 2), *at(x + kw / 2, y - kd / 2), rgb(L.COLOURS["key"]), r=1.0)
            reg.text(legends[i * cols + j], "arialbd.ttf", 6.0, *at(x, y), YELLOW)
    (sy0, sy1) = L.STRIP["y"]
    reg.rect_(*at(-w / 2, sy1), *at(w / 2, sy0), (186, 188, 192))
    for k in range(14):
        y = sy0 + (sy1 - sy0) * (k + 0.5) / 14
        reg.line([at(-w / 2, y), at(w / 2, y)], (200, 202, 206) if k % 2 else (172, 174, 178), 0.25)
    brand(reg, *at(-26.0, (sy0 + sy1) / 2 + 0.6), 5.4, (120, 122, 126))
    wy, wr = L.WELL["y"], L.WELL["r"]
    reg.circle(*at(0.0, wy), wr + 1.0, (10, 10, 11))
    reg.circle(*at(0.0, wy), wr - 3.0, (24, 24, 26))
    (by0, by1) = L.TOP_BUTTONS["y"]
    for (x0, x1), (label, ink) in zip(L.TOP_BUTTONS["x"], (("START", (70, 200, 90)), ("PAUSE", YELLOW),
                                                          ("RESET", (226, 60, 50)))):
        reg.rect_(*at(x0 - 0.8, by1 + 0.8), *at(x1 + 0.8, by0 - 0.8), (8, 8, 9))
        reg.rect_(*at(x0, by1), *at(x1, by0), (30, 30, 32))
        reg.text(label, "arialbi.ttf", 2.8, *at((x0 + x1) / 2, (by0 + by1) / 2), ink)
    return reg


# ---- The cartridge's label -------------------------------------------------------------------------------------------

def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (206, 208, 212))
    for k in range(60):                                       # the label's brushed silver
        y = lh * (k + 0.5) / 60
        reg.line([(0.0, y), (lw, y)], (214, 216, 220) if k % 2 else (198, 200, 204), 0.3)
    reg.text("ODYSSEY", "arialbi.ttf", 13.0, lw / 2 - 2.0, 10.0, (52, 104, 190))
    for k, colour in enumerate(RAINBOW):                      # the rainbow sweeping into the blue band
        reg.poly([(0.0, 18.5 + k * 0.9), (lw * 0.5, 20.0 + k * 0.9), (lw * 0.5, 20.9 + k * 0.9), (0.0, 19.4 + k * 0.9)],
                 colour)
    reg.rect_(0.0, 22.6, lw, 29.0, (52, 104, 190))
    reg.text("SPACE ADVENTURE", "arialbd.ttf", 3.6, lw / 2, 25.8, (255, 255, 255))
    art = space((640, 300)).convert("RGB")
    ship(ImageDraw.Draw(art), 220, 150, 3.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 29.0, lw, lh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), label()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", rgb(L.COLOURS["red"])), ("red_lit", (255, 70, 50)), ("black", rgb(L.COLOURS["black"])),
                         ("case", CASE), ("silver", SILVER), ("yellow", YELLOW)):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "atari5200_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
