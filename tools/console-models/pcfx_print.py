"""The PC-FX's printing (pcfx_print.png), for the console theme's model (pcfx.py).

One image, laid out as pcfx_layout.REGIONS says: a side (the cap's louvres and seams, the ribbed band, the raised
panel's vents, the three grooves near the back), the top (the back piece's louvres, the seams, the groove along the lid,
the latch), the front (NEC PC-FX, the badge, the POWER and BUSY lights' windows, the expansion door with its dots and
PUSH OPEN, the controller ports 1 and 2, the Compact Disc mark), the drive's floor under the lid, the pad from above
(its raised panels, the d-pad's dish, NEC, MODE 1 and MODE 2, SELECT and RUN, I to VI), the CD's label (a made-up game,
Odyssey), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/pcfx_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcfx_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

BODY = rgb(L.COLOURS["body"])
LINE = (178, 178, 176)
SLOT = (120, 120, 120)
INK = (110, 110, 112)
PURPLE = (120, 60, 160)
YELLOW = (240, 196, 40)
RED = (200, 40, 50)


def badge(reg, cx, cy, size):
    """The PC-FX's badge: a rounded tile, the swirl over the stacked base."""
    h = size / 2
    reg.rect_(cx - h, cy - h, cx + h, cy + h, (246, 246, 244), r=size * 0.18, outline=(170, 170, 168), width=0.3)
    reg.poly([(cx - h * 0.6, cy + h * 0.25), (cx + h * 0.6, cy + h * 0.25), (cx + h * 0.6, cy + h * 0.6),
              (cx - h * 0.6, cy + h * 0.6)], PURPLE)
    reg.poly([(cx + h * 0.05, cy + h * 0.32), (cx + h * 0.6, cy + h * 0.32), (cx + h * 0.6, cy + h * 0.6),
              (cx + h * 0.05, cy + h * 0.6)], RED)
    for k, r in enumerate((0.55, 0.38, 0.22)):
        top, bottom = cy - h * r * 0.9 - h * 0.12, cy + h * r * 0.9 - h * 0.12
        reg.draw.arc(reg.box(cx - h * r, top, cx + h * r, bottom), 200, 520,
                     fill=(YELLOW, PURPLE, YELLOW)[k], width=reg.width(size * 0.07))


def louvres(reg, x0, y0, x1, y1, pitch, vertical=False):
    """Slots across a block between the corners (x0, y0) and (x1, y1): horizontal lines every pitch (or vertical
    ones)."""
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    if vertical:
        x = x0
        while x <= x1:
            reg.rect_(x - 0.6, y0, x + 0.6, y1, SLOT, r=0.5)
            x += pitch
    else:
        y = y0
        while y <= y1:
            reg.rect_(x0, y - 0.5, x1, y + 0.5, SLOT, r=0.5)
            y += pitch


# ---- The console -----------------------------------------------------------------------------------------------------

def side():
    """A side: y across from the front (0 at the left), z down from the top (244)."""
    reg = Region(L.REGIONS["side"], L.DEPTH, L.HEIGHT, BODY)

    def at(y, z):
        return y, L.HEIGHT - z

    # The cap: its seams, the back piece's louvres; the ribbed band under it.
    for y in (L.SEAMS["front"], L.SEAMS["back"]):
        reg.rect_(*at(y - 0.5, L.HEIGHT), *at(y + 0.5, L.CAP), (90, 90, 90))
    louvres(reg, *at(L.SEAMS["back"] + 8.0, 236.0), *at(L.DEPTH - 8.0, 216.0), 4.0)
    reg.rect_(*at(0.0, L.CAP + 0.6), *at(L.DEPTH, L.CAP - 0.6), (150, 150, 148))
    for k in range(int(L.DEPTH / 2.2)):
        reg.rect_(*at(1.0 + k * 2.2, L.CAP - 0.8), *at(1.8 + k * 2.2, L.CAP - 4.0), (196, 196, 194))
    # The main field's frame; the raised panel's vents; the grooves near the back.
    reg.rect_(*at(6.0, 180.0), *at(L.DEPTH - 6.0, 4.0), None, outline=LINE, width=0.5)
    (py0, py1), (pz0, pz1) = L.PANEL["y"], L.PANEL["z"]
    reg.rect_(*at(py0, pz1), *at(py1, pz0), None, outline=(160, 160, 158), width=0.6)
    my, mz = (py0 + py1) / 2, (pz0 + pz1) / 2
    for i in range(-6, 7):
        for j in range(-5, 6):
            reg.rect_(*at(my + i * 7.0 - 0.7, mz + j * 7.0 + 0.7), *at(my + i * 7.0 + 0.7, mz + j * 7.0 - 0.7), SLOT)
    for z in [mz + k * 6.0 for k in range(-6, 7)]:
        reg.rect_(*at(py0 + 6.0, z + 0.6), *at(py0 + 26.0, z - 0.6), SLOT, r=0.5)
        reg.rect_(*at(py1 - 26.0, z + 0.6), *at(py1 - 6.0, z - 0.6), SLOT, r=0.5)
    for y in [my + k * 7.0 for k in range(-5, 6)]:
        reg.rect_(*at(y - 0.7, pz1 - 6.0), *at(y + 0.7, pz1 - 22.0), SLOT, r=0.5)
        reg.rect_(*at(y - 0.7, pz0 + 22.0), *at(y + 0.7, pz0 + 6.0), SLOT, r=0.5)
    for y in (L.DEPTH - 41.0, L.DEPTH - 34.0, L.DEPTH - 27.0):
        reg.rect_(*at(y - 1.0, 160.0), *at(y + 1.0, 12.0), (150, 150, 148), r=1.0)
    return reg


def top():
    """The top from above: x across (-66 at the left), y down from the back (267)."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, BODY)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    for y in (L.SEAMS["front"], L.SEAMS["back"]):
        reg.rect_(*at(-L.WIDTH / 2, y + 0.6), *at(L.WIDTH / 2, y - 0.6), (90, 90, 90))
    reg.rect_(*at(-0.5, L.DEPTH), *at(0.5, L.SEAMS["back"]), (120, 120, 118))       # the back piece's seam
    reg.rect_(*at(-0.4, L.SEAMS["back"]), *at(0.4, L.SEAMS["front"]), (186, 186, 184))  # the groove along the lid
    for sign in (-1, 1):
        louvres(reg, *at(sign * 8.0, L.DEPTH - 8.0), *at(sign * 60.0, L.SEAMS["back"] + 8.0), 4.4)
    reg.rect_(*at(-4.0, 8.0), *at(4.0, 0.0), (40, 40, 42), r=1.0)                    # the latch
    return reg


def front():
    """The front: x across (-66 at the left), z down from the top (244)."""
    reg = Region(L.REGIONS["front"], L.WIDTH, L.HEIGHT, BODY)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z

    inner = L.PILLARS["inner"]
    reg.rect_(*at(-0.5, L.HEIGHT), *at(0.5, L.CAP), (120, 120, 118))
    reg.rect_(*at(-4.0, L.HEIGHT), *at(4.0, L.HEIGHT - 8.0), (40, 40, 42), r=1.0)   # the latch
    reg.rect_(*at(-inner, L.CAP), *at(inner, 6.0), (232, 232, 230))                   # the strip
    reg.text("NEC", "arialbd.ttf", 6.0, *at(0.0, L.LOGO["at"][1] + 7.0), INK)
    reg.text("PC·FX", "arialbd.ttf", 8.0, *at(0.0, L.LOGO["at"][1]), INK)
    badge(reg, *at(*L.BADGE["at"]), L.BADGE["size"])
    for name in ("power", "busy"):
        x, z = L.LIGHTS[name]
        w, h = L.LIGHTS["size"]
        reg.rect_(*at(x - w / 2, z + h / 2), *at(x + w / 2, z - h / 2), (40, 40, 42))
        reg.text(name.upper(), "arial.ttf", 2.0, *at(x, z + 3.0), INK)
    (d0, d1) = L.DOOR["z"]
    reg.rect_(*at(-inner + 2.0, d1), *at(inner - 2.0, d0), (226, 226, 224), outline=LINE, width=0.4)
    for i in range(3):
        for j in range(8):
            reg.rect_(*at(-14.0 + i * 7.0 - 0.6, d1 - 5.0 - j * 6.0 + 0.6),
                      *at(-14.0 + i * 7.0 + 0.6, d1 - 5.0 - j * 6.0 - 0.6), SLOT)
    reg.text("PUSH", "arialbd.ttf", 2.0, *at(15.0, d0 + 26.0), INK)
    reg.text("OPEN", "arialbd.ttf", 2.0, *at(15.0, d0 + 23.0), INK)
    (p0, p1) = L.PORTS["z"]
    reg.rect_(*at(-inner + 2.0, p1), *at(inner - 2.0, p0), (224, 224, 222), outline=LINE, width=0.4)
    pw, ph = L.PORTS["size"]
    for k, (x, z) in enumerate(L.PORTS["at"]):
        reg.rect_(*at(x - pw / 2, z + ph / 2), *at(x + pw / 2, z - ph / 2), (176, 178, 180), r=2.0)
        reg.rect_(*at(x - pw / 2 + 1.2, z + ph / 2 - 1.2), *at(x + pw / 2 - 1.2, z - ph / 2 + 1.2), (40, 40, 42), r=1.6)
        for row, n in ((1.4, 4), (-1.4, 4)):
            for i in range(n):
                reg.circle(*at(x - 4.5 + 3.0 * i, z + row), 0.5, (200, 176, 110))
        reg.text(str(k + 1), "arialbd.ttf", 2.6, *at(x + 13.0, z - 1.0), INK)
    reg.text("disc", "timesbd.ttf", 4.0, *at(46.0, 9.0), (176, 176, 174))
    reg.text("COMPACT", "arial.ttf", 1.4, *at(46.0, 12.4), (176, 176, 174))
    return reg


def drive():
    """The drive's floor under the lid, from above: x across, y down from its back."""
    w, d = 2 * L.DRIVE["half"][0], 2 * L.DRIVE["half"][1]
    reg = Region(L.REGIONS["drive"], w, d, (70, 72, 76))
    cx, cy = w / 2, d / 2
    reg.circle(cx, cy, 61.5, (92, 94, 98))
    reg.circle(cx, cy, 58.0, (78, 80, 84))
    reg.rect_(cx - 6.0, 4.0, cx + 6.0, cy - 12.0, (24, 24, 26), r=2.0)                # the laser's slot
    reg.rect_(cx - 3.0, 12.0, cx + 3.0, 24.0, (150, 150, 160), r=1.0)                   # the lens
    return reg


def pad():
    """The pad from above: x across (-84 at the left), y down from its top edge (74.8)."""
    reg = Region(L.REGIONS["pad"], 168.0, 74.8, BODY)

    def at(x, y):
        return x + 84.0, 74.8 - y

    for sign in (-1, 1):                                    # the raised panels on the lobes
        x = sign * 52.0
        reg.draw.rounded_rectangle(reg.box(*at(x - 30.0, 60.0), *at(x + 30.0, 6.0)), radius=14.0 * reg.sx,
                                   outline=(206, 206, 204), width=reg.width(0.6))
    (dx, dy), dish = L.DPAD["at"], L.DPAD["dish"]
    reg.circle(*at(dx, dy), dish, (150, 150, 152), outline=(110, 110, 112), width=0.5)
    reg.text("NEC", "arialbd.ttf", 3.6, *at(-0.4, 55.6), INK)
    for name, label in (("mode_1", "MODE 1"), ("mode_2", "MODE 2")):
        x, y = L.SWITCHES[name]
        sw, sh = L.SWITCHES["size"]
        reg.text(label, "arial.ttf", 2.4, *at(x, y + 4.4), INK)
        reg.text("A", "arial.ttf", 2.4, *at(x - 12.4, y), INK)
        reg.text("B", "arial.ttf", 2.4, *at(x + 12.4, y), INK)
        reg.rect_(*at(x - sw / 2, y + sh / 2), *at(x + sw / 2, y - sh / 2), (20, 20, 22), r=sh / 2)
        reg.circle(*at(x - sw / 4, y), sh / 2 - 0.3, (236, 236, 234))
    for name in ("select", "run"):
        x, y = L.SMALL[name]
        reg.text(name.upper(), "arial.ttf", 2.4, *at(x, y + 4.4), INK)
    reg.text("PC·FX", "arialbd.ttf", 3.0, *at(-2.9, 68.2), (210, 210, 208))
    for name in ("I", "II", "III", "IV", "V", "VI"):                 # the buttons' tops
        x, y = L.BUTTONS[name]
        reg.circle(*at(x, y), L.BUTTONS["r"], (168, 168, 170))
        reg.text(name, "timesbd.ttf", 5.0, *at(x, y), (120, 120, 122))
    return reg


def disc():
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (20, 20, 24))
    c = dm / 2
    art = space((600, 600)).convert("RGB")
    ship(ImageDraw.Draw(art), 190, 340, 4.0, "#FFFFFF", "#FFB23C")
    mask = Image.new("L", reg.img.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0), fill=255)
    md.ellipse(reg.box(c - 21.0, c - 21.0, c + 21.0, c + 21.0), fill=0)
    x0, y0, x1, y1 = reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.img.paste(layer, (0, 0), mask)
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.text("ODYSSEY", "ariblk.ttf", 10.0, c, c - 36.0, (255, 214, 70))
    reg.text("PC·FX", "arialbd.ttf", 6.0, c, c + 32.0, (236, 236, 240))
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BODY)
    for reg in (side(), top(), front(), drive(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(body=BODY, light=(238, 238, 236), grey=(168, 168, 170), dark=(70, 72, 76), green=(60, 230, 90),
                   amber=(255, 170, 30), key=(160, 160, 162), black=(18, 18, 20))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "pcfx_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
