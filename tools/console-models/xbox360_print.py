"""The Xbox 360's printing (xbox360_print.png), for the console theme's model (xbox360.py).

One image, laid out as xbox360_layout.REGIONS says: the console's top from above (the vents along its ends, XBOX 360),
the faceplate (the tray's silver front with XBOX 360, the eject mark, the IR window, MEMORY UNIT A and B, the sync
button, the power button's recess and the Ring of Light unlit, the USB door), the controller from above (the d-pad's
well, the sticks' housings, A, B, X and Y in their colours, the Guide button and its ring, BACK and START), the disc's
label (a made-up game, Odyssey), an end's grille, and swatches. Run it with the system Python (Pillow):

    python tools/console-models/xbox360_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xbox360_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

BODY = rgb(L.COLOURS["body"])
PLATE = rgb(L.COLOURS["plate"])
LINE = (206, 208, 206)
SILVER = (196, 199, 203)
GREEN = (100, 190, 40)


def xbox_ball(reg, cx, cy, r):
    """The Guide button: a silver ball with the green X sweeping across it."""
    reg.circle(cx, cy, r, (210, 213, 216))
    reg.circle(cx - r * 0.2, cy - r * 0.25, r * 0.7, (232, 234, 236))
    for sign in (-1, 1):
        reg.line([(cx - r * 0.62, cy - sign * r * 0.62), (cx + r * 0.62, cy + sign * r * 0.62)], GREEN, r * 0.34)


def rotated_text(reg, s, font, size, cx, cy, fill, degrees):
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    layer = Image.new("RGBA", (round(f.getlength(s)) + 20, round(size * reg.sx * 1.6) + 20), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((10, layer.height / 2), s, font=f, fill=fill, anchor="lm")
    layer = layer.rotate(degrees, expand=True, resample=Image.BICUBIC)
    x, y = reg.p(cx, cy)
    reg.img.alpha_composite(layer, (round(x - layer.width / 2), round(y - layer.height / 2)))


# ---- The console -----------------------------------------------------------------------------------------------------

def top():
    """The console from above: x across (-154.5 at the left), y down from the back."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, BODY)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    for side in (-1, 1):
        x0 = side * (L.WIDTH / 2 - 30.0)
        for i in range(5):
            for j in range(56):
                x = x0 + side * (i * 3.0 - 6.0) + (1.5 if j % 2 else 0.0)
                y = 28.0 + j * 3.6
                reg.circle(*at(x, y), 0.85, (160, 162, 164))
    rotated_text(reg, "XBOX 360", "bahnschrift.ttf", 13.0, *at(40.0, 150.0), (222, 223, 221, 255), 75)
    return reg


def front():
    """The faceplate: x across (-154.5 at the left), z down from the top (83)."""
    reg = Region(L.REGIONS["front"], L.WIDTH, L.HEIGHT, PLATE)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z

    (tx0, tx1), (tz0, tz1) = L.TRAY["x"], L.TRAY["z"]
    reg.rect_(*at(tx0, tz1), *at(tx1, tz0), SILVER, r=(tz1 - tz0) / 2)
    reg.rect_(*at(tx0 + 2.0, tz1 - 2.0), *at(tx1 - 2.0, tz1 - 4.0), (226, 228, 231), r=1.0)
    reg.text("XBOX 360", "bahnschrift.ttf", 6.0, *at(tx1 - 22.0, (tz0 + tz1) / 2), (150, 152, 156))
    (ex, ez), (ew, eh) = L.EJECT["at"], L.EJECT["size"]
    reg.rect_(*at(ex - ew / 2, ez + eh / 2), *at(ex + ew / 2, ez - eh / 2), (226, 227, 225), r=eh / 2)
    reg.poly([at(ex - 1.6, ez - 1.6), at(ex + 1.6, ez - 1.6), at(ex, ez + 1.4)], (150, 150, 150))
    (ix, iz), (iw, ih) = L.IR["at"], L.IR["size"]
    reg.rect_(*at(ix - iw / 2, iz + ih / 2), *at(ix + iw / 2, iz - ih / 2), (26, 26, 28), r=ih / 2)
    mw, mh = L.MEMORY["size"]
    for name, label in (("a", "Memory Unit A"), ("b", "Memory Unit B")):
        mx, mz = L.MEMORY[name]
        reg.rect_(*at(mx - mw / 2, mz + mh / 2), *at(mx + mw / 2, mz - mh / 2), (236, 236, 233), r=mh / 2, outline=LINE,
                  width=0.4)
        reg.text(label, "arial.ttf", 2.3, *at(mx, mz), (176, 178, 178))
    (sx, sz), sr = L.SYNC["at"], L.SYNC["r"]
    reg.circle(*at(sx, sz), sr, (238, 238, 235), outline=LINE, width=0.4)
    (px, pz) = L.POWER["at"]
    reg.circle(*at(px, pz), L.POWER["recess"], (228, 229, 226))
    reg.circle(*at(px, pz), L.POWER["ring"][1], (196, 198, 198))
    reg.circle(*at(px, pz), L.POWER["ring"][0], (228, 229, 226))
    for k in range(4):                                  # the Ring of Light's quadrants' gaps
        a = math.radians(45 + 90 * k)
        r0, r1 = L.POWER["ring"]
        reg.line([at(px + r0 * math.cos(a), pz + r0 * math.sin(a)), at(px + r1 * math.cos(a), pz + r1 * math.sin(a))],
                 (228, 229, 226), 1.0)
    reg.circle(*at(px, pz + 0.8), 3.4, None, outline=(160, 162, 162), width=0.6)        # the power mark
    reg.rect_(*at(px - 0.7, pz + 5.2), *at(px + 0.7, pz + 1.0), (228, 229, 226))
    reg.rect_(*at(px - 0.3, pz + 5.0), *at(px + 0.3, pz + 1.2), (160, 162, 162))
    (ux, uz), (uw, uh) = L.USB_DOOR["at"], L.USB_DOOR["size"]
    reg.rect_(*at(ux - uw / 2, uz + uh / 2), *at(ux + uw / 2, uz - uh / 2), (240, 240, 237), r=uw / 2, outline=LINE,
              width=0.5)
    for z in (44.0, 20.0):
        reg.circle(*at(104.0, z), 0.7, (190, 192, 192))
    return reg


def grille():
    """An end's grille as the end faces it: y across (its depth), z down from the top; dark grey, its dots in rows."""
    reg = Region(L.REGIONS["grille"], L.DEPTH, L.HEIGHT, (70, 72, 76))
    for j in range(int(L.HEIGHT / 3.0) + 1):
        for i in range(int(L.DEPTH / 3.4) + 1):
            reg.circle(1.0 + i * 3.4 + (1.7 if j % 2 else 0.0), 1.0 + j * 3.0, 1.0, (150, 154, 160))
    return reg


# ---- The controller and the disc -------------------------------------------------------------------------------------

def pad():
    """The controller from above: x across (-76.5 at the left), y down from its top edge (92)."""
    reg = Region(L.REGIONS["pad"], 153.0, 92.0, PLATE)

    def at(x, y):
        return x + 76.5, 92.0 - y

    for name in ("left", "right"):
        reg.circle(*at(*L.STICKS[name]), L.STICKS["housing"], (232, 233, 231), outline=LINE, width=0.5)
    reg.circle(*at(*L.DPAD["at"]), L.DPAD["r"] + 2.0, (228, 229, 227), outline=LINE, width=0.5)
    for name, colour, letter in (("a", (90, 190, 50), "A"), ("b", (220, 50, 40), "B"), ("x", (50, 110, 220), "X"),
                                 ("y", (245, 190, 30), "Y")):
        x, y = L.FACE[name]
        reg.circle(*at(x, y), L.FACE["r"], colour)
        reg.circle(*at(x - 1.2, y + 1.4), L.FACE["r"] * 0.55, tuple(min(255, c + 40) for c in colour))
        reg.text(letter, "arialbd.ttf", 4.6, *at(x, y), (250, 250, 250))
    gx, gy = L.GUIDE["at"]
    reg.circle(*at(gx, gy), L.GUIDE["ring"], (180, 184, 186))
    xbox_ball(reg, *at(gx, gy), L.GUIDE["r"])
    sw, sh = L.SMALL["size"]
    for name, direction in (("back", -1), ("start", 1)):
        x, y = L.SMALL[name]
        reg.rect_(*at(x - sw / 2, y + sh / 2), *at(x + sw / 2, y - sh / 2), (226, 227, 225), r=sh / 2, outline=LINE,
                  width=0.3)
        reg.poly([at(x + direction * 1.4, y), at(x - direction * 1.0, y + 1.1), at(x - direction * 1.0, y - 1.1)],
                 (150, 150, 152))
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
    band = Image.new("L", reg.img.size, 0)                          # the green band across its top
    ImageDraw.Draw(band).rectangle(reg.box(0.0, 0.0, dm, 22.0), fill=255)
    reg.img.paste((96, 180, 40, 255), (0, 0), Image.composite(band, Image.new("L", band.size, 0), mask))
    reg.text("XBOX 360", "bahnschrift.ttf", 6.0, c, 12.0, (250, 250, 250))
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.text("ODYSSEY", "ariblk.ttf", 10.0, c, c + 34.0, (255, 214, 70))
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BODY)
    for reg in (top(), front(), grille(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(body=BODY, plate=PLATE, grey=(82, 84, 88), silver=SILVER, dark=(24, 24, 26), green=(110, 230, 60),
                   green_dim=(70, 110, 60), hdd=(150, 153, 158), chrome=(218, 222, 226), shell=(170, 172, 174))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "xbox360_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
