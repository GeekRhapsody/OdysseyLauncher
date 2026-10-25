"""The PlayStation 4's printing (ps4_print.png), for the console theme's model (ps4.py).

One image, laid out as ps4_layout.REGIONS says: the console's top from above (the glossy and the matte parts, the
groove, the PlayStation mark), its front (SONY, PS4, the slit with the disc slot and the USB ports, the touch buttons'
marks) and its back (the vents), the DualShock 4 from above (the circles of the d-pad and the face buttons, their
coloured symbols, the touchpad, SHARE and OPTIONS, the speaker, the PS button's mark), the disc's label (a made-up game,
Odyssey), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/ps4_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps4_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

GLOSS = rgb(L.COLOURS["gloss"])
MATTE = rgb(L.COLOURS["matte"])
PAD = rgb(L.COLOURS["pad"])
SLIT = (6, 6, 7)
INK = (122, 124, 130)
SILVER = (196, 198, 204)


def mark(reg, cx, cy, h, colour):
    """A PlayStation-style mark h tall about (cx, cy): the upright P and the flattened S lying under it."""
    w = h * 0.55
    reg.poly([(cx - w * 0.18, cy + h * 0.32), (cx - w * 0.18, cy - h * 0.5), (cx + w * 0.3, cy - h * 0.38),
              (cx + w * 0.42, cy - h * 0.18), (cx + w * 0.3, cy), (cx + w * 0.04, cy + h * 0.06),
              (cx + w * 0.04, cy + h * 0.42)], colour)
    reg.poly([(cx + w * 0.04, cy - h * 0.34), (cx + w * 0.22, cy - h * 0.28), (cx + w * 0.22, cy - h * 0.1),
              (cx + w * 0.04, cy - h * 0.06)], GLOSS)
    reg.poly([(cx - w * 0.9, cy + h * 0.28), (cx - w * 0.3, cy + h * 0.1), (cx - w * 0.22, cy + h * 0.24),
              (cx - w * 0.7, cy + h * 0.4)], colour)
    reg.poly([(cx + w * 0.12, cy + h * 0.16), (cx + w * 0.9, cy + h * 0.2), (cx + w * 0.8, cy + h * 0.36),
              (cx + w * 0.12, cy + h * 0.48)], colour)


# ---- The console -----------------------------------------------------------------------------------------------------

def top():
    """The console from above: x across (-137.5 at the left), y down from the back."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, MATTE)
    split = L.GLOSS
    reg.rect_(0.0, 0.0, split, L.DEPTH, GLOSS)
    reg.rect_(split, 0.0, split + L.GROOVE, L.DEPTH, SLIT)
    mark(reg, split - 14.0, 22.0, 13.0, INK)
    return reg


def front():
    """The front's printing: x across, z down from the top (53)."""
    reg = Region(L.REGIONS["front"], L.WIDTH, L.HEIGHT, MATTE)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z

    split = -L.WIDTH / 2 + L.GLOSS
    (s0, s1) = L.SLIT["z"]
    reg.rect_(*at(-L.WIDTH / 2, L.HEIGHT), *at(split, s1), GLOSS)
    reg.rect_(*at(split, L.HEIGHT), *at(split + L.GROOVE, 0.0), SLIT)
    reg.rect_(*at(-L.WIDTH / 2, s1), *at(L.WIDTH / 2, s0), SLIT)
    (d0, d1) = L.DISC_SLOT["x"]
    reg.rect_(*at(d0, s1 - 1.6), *at(d1, s0 + 1.6), (24, 24, 26))
    reg.rect_(*at(d0, s1 - 2.3), *at(d1, s1 - 2.6), (60, 60, 64))
    for x in L.USB["x"]:
        w, h = L.USB["size"]
        reg.rect_(*at(x - w / 2, (s0 + s1) / 2 + h / 2), *at(x + w / 2, (s0 + s1) / 2 - h / 2), SILVER)
        mid = (s0 + s1) / 2
        reg.rect_(*at(x - w / 2 + 1.2, mid + h / 2 - 1.2), *at(x + w / 2 - 1.2, mid - 0.2), (30, 30, 34))
    reg.text("SONY", "timesbd.ttf", 5.0, *at(-L.WIDTH / 2 + 22.0, 37.0), INK)
    reg.text("PS4", "bahnschrift.ttf", 8.0, *at(L.WIDTH / 2 - 26.0, 37.0), (40, 41, 45))
    for z, symbol in ((44.0, "power"), (12.0, "eject")):           # the touch buttons' marks either side of the groove
        x = split + L.GROOVE / 2
        if symbol == "power":
            reg.circle(*at(x, z), 1.0, None, outline=INK, width=0.25)
        else:
            reg.poly([at(x - 1.0, z - 0.2), at(x + 1.0, z - 0.2), at(x, z + 1.0)], INK)
    return reg


def back():
    """The back's vents: x across, z down from the top."""
    reg = Region(L.REGIONS["back"], L.WIDTH, L.HEIGHT, MATTE)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z

    for (z0, z1) in ((4.0, 14.0), (27.0, 48.0)):
        for k in range(26):
            x = -L.WIDTH / 2 + 8.0 + 10.2 * k
            reg.rect_(*at(x, z1), *at(x + 7.0, z0), SLIT, r=0.8)
    reg.rect_(*at(-L.WIDTH / 2, L.SLIT["z"][1]), *at(L.WIDTH / 2, L.SLIT["z"][0]), SLIT)
    return reg


# ---- The DualShock 4 and the disc ------------------------------------------------------------------------------------

def pad():
    """The DualShock 4 from above: x across (-81 at the left), y down from its top edge (100)."""
    reg = Region(L.REGIONS["pad"], 162.0, 100.0, PAD)

    def at(x, y):
        return x + 81.0, 100.0 - y

    grey = (44, 46, 52)
    for name in ("dpad", "face"):
        cx, cy = L.DPAD["at"] if name == "dpad" else (51.0, 72.4)
        reg.circle(*at(cx, cy), L.DPAD["ring"], (24, 25, 29), outline=grey, width=0.6)
    for name in ("left", "right"):
        reg.circle(*at(*L.STICKS[name]), L.STICKS["housing"], None, outline=grey, width=0.6)
    (tx0, tx1), (ty0, ty1) = L.TOUCHPAD["x"], L.TOUCHPAD["y"]
    reg.rect_(*at(tx0, ty1), *at(tx1, ty0), (28, 29, 33), r=L.TOUCHPAD["r"])
    for i in range(36):
        for j in range(16):
            reg.circle(*at(tx0 + 2.0 + i * 1.44, ty0 + 2.0 + j * 1.66), 0.22, (52, 54, 60))
    for name, colour in (("triangle", (90, 200, 160)), ("circle", (236, 96, 100)), ("cross", (120, 160, 236)),
                         ("square", (226, 140, 200))):
        x, y = L.FACE[name]
        reg.circle(*at(x, y), L.FACE["r"], (30, 31, 35))
        if name == "triangle":
            reg.line([at(x, y + 2.7), at(x + 2.6, y - 1.7), at(x - 2.6, y - 1.7), at(x, y + 2.7)], colour, 0.5)
        elif name == "circle":
            reg.circle(*at(x, y), 2.4, None, outline=colour, width=0.5)
        elif name == "cross":
            reg.line([at(x - 2.2, y - 2.2), at(x + 2.2, y + 2.2)], colour, 0.5)
            reg.line([at(x - 2.2, y + 2.2), at(x + 2.2, y - 2.2)], colour, 0.5)
        else:
            reg.rect_(*at(x - 2.2, y + 2.2), *at(x + 2.2, y - 2.2), None, outline=colour, width=0.5)
    reg.text("SHARE", "arialbd.ttf", 2.2, *at(L.SMALL["share"][0], 95.0), (150, 152, 158))
    reg.text("OPTIONS", "arialbd.ttf", 2.2, *at(L.SMALL["options"][0], 95.0), (150, 152, 158))
    sx, sy = L.SMALL["speaker"]
    for row, n in ((2.0, 5), (0.0, 4), (-2.0, 3)):
        for k in range(n):
            reg.circle(*at(sx - (n - 1) * 1.45 + 2.9 * k, sy + row), 0.6, (8, 8, 10))
    px, py = L.SMALL["ps"]
    reg.circle(*at(px, py), L.SMALL["ps_r"], (30, 31, 35))
    mark(reg, *at(px, py), 5.0, (190, 192, 198))
    return reg


def disc():
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (20, 20, 24))
    c = dm / 2
    art = space((600, 600)).convert("RGB")
    ship(ImageDraw.Draw(art), 200, 330, 4.0, "#FFFFFF", "#FFB23C")
    mask = Image.new("L", reg.img.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0), fill=255)
    md.ellipse(reg.box(c - 21.0, c - 21.0, c + 21.0, c + 21.0), fill=0)
    x0, y0, x1, y1 = reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.img.paste(layer, (0, 0), mask)
    band = Image.new("L", reg.img.size, 0)                           # the blue PS4 band down its left side
    ImageDraw.Draw(band).rectangle(reg.box(0.0, 0.0, 22.0, dm), fill=255)
    reg.img.paste((14, 64, 160, 255), (0, 0), Image.composite(band, Image.new("L", band.size, 0), mask))
    reg.text("PS4", "bahnschrift.ttf", 6.0, 11.0, c, (240, 240, 244))
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.text("ODYSSEY", "ariblk.ttf", 10.0, c + 6.0, c - 36.0, (255, 214, 70))
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), MATTE)
    for reg in (top(), front(), back(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(gloss=GLOSS, matte=MATTE, pad=PAD, slit=SLIT, dark=(30, 31, 35), blue=(40, 110, 255),
                   white=(232, 234, 240), grey=(66, 68, 74), green=(90, 200, 160), red=(236, 96, 100),
                   pink=(226, 140, 200), sky=(120, 160, 236))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "ps4_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
