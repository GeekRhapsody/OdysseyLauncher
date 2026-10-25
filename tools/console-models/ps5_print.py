"""The PlayStation 5's printing (ps5_print.png), for the console theme's model (ps5.py).

One image, laid out as ps5_layout.REGIONS says: the core's front (the USB ports, the power and eject buttons' marks,
the disc slot, the grooves of the light strips), a panel's outer face (the PlayStation mark near its top), the DualSense
from above (its white wings round the black middle, the touchpad, the d-pad's arrows, the face buttons' symbols, the
speaker, the PS button's mark, the mute button, Create and Options), the disc's label (a made-up game, Odyssey), and
swatches. Run it with the system Python (Pillow):

    python tools/console-models/ps5_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps5_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

WHITE = rgb(L.COLOURS["white"])
GLOSS = (10, 10, 12)
BLACK = (24, 24, 27)
GREY = (150, 152, 158)


def mark(reg, cx, cy, h, colour, ground):
    """A PlayStation-style mark h tall about (cx, cy): the upright P (its hole the ground's colour) and the flattened S
    lying under it."""
    w = h * 0.55
    reg.poly([(cx - w * 0.18, cy + h * 0.32), (cx - w * 0.18, cy - h * 0.5), (cx + w * 0.3, cy - h * 0.38),
              (cx + w * 0.42, cy - h * 0.18), (cx + w * 0.3, cy), (cx + w * 0.04, cy + h * 0.06),
              (cx + w * 0.04, cy + h * 0.42)], colour)
    reg.poly([(cx + w * 0.04, cy - h * 0.34), (cx + w * 0.22, cy - h * 0.28), (cx + w * 0.22, cy - h * 0.1),
              (cx + w * 0.04, cy - h * 0.06)], ground)
    reg.poly([(cx - w * 0.9, cy + h * 0.28), (cx - w * 0.3, cy + h * 0.1), (cx - w * 0.22, cy + h * 0.24),
              (cx - w * 0.7, cy + h * 0.4)], colour)
    reg.poly([(cx + w * 0.12, cy + h * 0.16), (cx + w * 0.9, cy + h * 0.2), (cx + w * 0.8, cy + h * 0.36),
              (cx + w * 0.12, cy + h * 0.48)], colour)


# ---- The console -----------------------------------------------------------------------------------------------------

def front():
    """The core's front: x across (-36 at the left), z down from its top (392 above the table)."""
    h = L.CORE["half"]
    z0, z1 = L.CORE["z"]
    reg = Region(L.REGIONS["front"], 2 * h, z1 - z0, GLOSS)

    def at(x, z):
        return x + h, z1 - z

    for side in (-1, 1):                                       # the light strips' grooves
        x = side * L.LIGHTS["x"]
        reg.rect_(*at(x - 0.8, L.LIGHTS["z"][1]), *at(x + 0.8, L.LIGHTS["z"][0]), (40, 40, 46))
    sx, (s0, s1), sw = L.SLOT["x"], L.SLOT["z"], L.SLOT["width"]
    reg.rect_(*at(sx - sw / 2, s1), *at(sx + sw / 2, s0), (2, 2, 3), r=sw / 2)
    for name in ("a", "c"):
        x, z = L.USB[name]
        w, hh = L.USB["size"]
        if name == "c":
            w, hh = 9.0, 3.4
        corner = hh / 2 if name == "c" else 0.6
        reg.rect_(*at(x - w / 2, z + hh / 2), *at(x + w / 2, z - hh / 2), (60, 62, 68), r=corner)
        reg.rect_(*at(x - w / 2 + 1.0, z + hh / 2 - 1.0), *at(x + w / 2 - 1.0, z - hh / 2 + 1.0), (4, 4, 6),
                  r=hh / 4 if name == "c" else 0.3)
    for name in ("power", "eject"):
        x, z = L.BUTTONS[name]
        w, hh = L.BUTTONS["size"]
        reg.rect_(*at(x - w / 2, z + hh / 2), *at(x + w / 2, z - hh / 2), (30, 30, 34), r=hh / 2)
    return reg


def panel():
    """A panel's outer face: y across from the front, z down from the top (390 above the console's foot)."""
    reg = Region(L.REGIONS["panel"], L.DEPTH, L.HEIGHT, WHITE)
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    for y in range(layer.size[1]):                                # a soft sheen down the face
        t = y / layer.size[1]
        d.line([(0, y), (layer.size[0], y)], fill=(255, 255, 255, round(40 * (1 - t))))
    reg.over(layer)
    mark(reg, L.LOGO["y"], L.HEIGHT - L.LOGO["z"], L.LOGO["size"], (214, 214, 212), WHITE)
    return reg


# ---- The DualSense and the disc --------------------------------------------------------------------------------------

def pad():
    """The DualSense from above: x across (-80 at the left), y down from its top edge (106)."""
    reg = Region(L.REGIONS["pad"], 160.0, 106.0, WHITE)

    def at(x, y):
        return x + 80.0, 106.0 - y

    # The black middle: between the wings' inner curves, from under the touchpad down to the bottom.
    middle = [at(-29.0, 80.0), at(-40.0, 62.0), at(-44.0, 46.0), at(-38.0, 41.4), at(38.0, 41.4), at(44.0, 46.0),
              at(40.0, 62.0), at(31.0, 80.0)]
    reg.poly(middle, BLACK)
    (tx0, tx1), (ty0, ty1), tr = L.TOUCHPAD["x"], L.TOUCHPAD["y"], L.TOUCHPAD["r"]
    reg.rect_(*at(tx0, ty1), *at(tx1, ty0), (236, 236, 234), r=tr)
    for side, x in ((-1, tx0), (1, tx1)):                         # the light bar's strips along its sides, unlit
        reg.line([at(x - side * 0.6, ty1 - 2.0), at(x - side * 0.6 - side * 1.5, ty0 + 4.0)], (190, 196, 206), 1.0)
    dx, dy = L.DPAD["at"]
    for k, (ux, uy) in enumerate(((0, 1), (1, 0), (0, -1), (-1, 0))):
        cx, cy = dx + ux * 8.6, dy + uy * 8.6
        reg.poly([at(cx + ux * 1.6, cy + uy * 1.6), at(cx - uy * 1.3 - ux * 0.6, cy + ux * 1.3 - uy * 0.6),
                  at(cx + uy * 1.3 - ux * 0.6, cy - ux * 1.3 - uy * 0.6)], GREY)
    for name in ("triangle", "circle", "cross", "square"):
        x, y = L.FACE[name]
        reg.circle(*at(x, y), L.FACE["r"], (214, 216, 220))
        if name == "triangle":
            reg.line([at(x, y + 2.6), at(x + 2.5, y - 1.6), at(x - 2.5, y - 1.6), at(x, y + 2.6)], GREY, 0.45)
        elif name == "circle":
            reg.circle(*at(x, y), 2.3, None, outline=GREY, width=0.45)
        elif name == "cross":
            reg.line([at(x - 2.1, y - 2.1), at(x + 2.1, y + 2.1)], GREY, 0.45)
            reg.line([at(x - 2.1, y + 2.1), at(x + 2.1, y - 2.1)], GREY, 0.45)
        else:
            reg.rect_(*at(x - 2.1, y + 2.1), *at(x + 2.1, y - 2.1), None, outline=GREY, width=0.45)
    sx, sy = L.SMALL["speaker"]
    for row, n in ((1.4, 5), (-1.4, 4)):
        for k in range(n):
            reg.circle(*at(sx - (n - 1) * 1.5 + 3.0 * k, sy + row), 0.55, (4, 4, 6))
    px, py = L.SMALL["ps"]
    mark(reg, *at(px, py), 6.0, (60, 62, 68), BLACK)
    mx, my = L.SMALL["mute"]
    reg.rect_(*at(mx - 3.8, my + 1.2), *at(mx + 3.8, my - 1.2), (200, 202, 206), r=1.2)
    for name in ("create", "options"):
        x, y = L.SMALL[name]
        w, h = L.SMALL["size"]
        reg.rect_(*at(x - w / 2, y + h / 2), *at(x + w / 2, y - h / 2), (226, 226, 224), r=w / 2)
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
    band = Image.new("L", reg.img.size, 0)                          # the blue band across its top
    ImageDraw.Draw(band).rectangle(reg.box(0.0, 0.0, dm, 22.0), fill=255)
    reg.img.paste((20, 70, 180, 255), (0, 0), Image.composite(band, Image.new("L", band.size, 0), mask))
    reg.text("PS5", "bahnschrift.ttf", 6.0, c, 12.0, (250, 250, 250))
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.text("ODYSSEY", "ariblk.ttf", 10.0, c, c + 34.0, (255, 214, 70))
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), WHITE)
    for reg in (front(), panel(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(white=WHITE, black=BLACK, gloss=GLOSS, blue=(40, 110, 255), light=(236, 240, 255), grey=(70, 72, 78),
                   clear=(196, 200, 208), stand=(20, 20, 22), dark=(4, 4, 6))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "ps5_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
