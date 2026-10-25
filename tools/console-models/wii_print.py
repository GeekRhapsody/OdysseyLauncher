"""The Wii's printing, for the console theme's Wii model (tools/console-models/wii.py).

Draws its atlas, its regions as wii_layout.py places them, each in millimetres as the model's planar UVs map it: the
front (the buttons' legends, the power light in standby red, the SD card's flap, the Wii logo); the right side (its
panel and Nintendo's name); the remote's face (POWER, the D-pad's place, A, minus, HOME and plus, the speaker's holes,
1 and 2, the player lights, Wii); the disc's label side (a made-up game, Odyssey, under the Wii logo) and its other
side; and the swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/wii_print.py <out folder>

It writes wii_print.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wii_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

GREY = (150, 152, 156)


def wii_logo(reg, x, y, size, colour):
    """The Wii logo: a W and two i's, size tall, its middle at (x, y)."""
    reg.text("Wii", "arialbd.ttf", size * 1.25, x, y, colour)


def front():
    w, h = L.WIDTH, L.HEIGHT
    reg = Region(L.REGIONS["front"], w, h, rgb(L.COLOURS["front"]))

    def at(x, z):
        return x + w / 2, h - z
    for name, (x, z, (bw, bh)) in L.BUTTONS.items():
        a, b = at(x - bw / 2, z + bh / 2)
        c, e = at(x + bw / 2, z - bh / 2)
        reg.rect_(a - 0.5, b - 0.5, c + 0.5, e + 0.5, shade(rgb(L.COLOURS["front"]), -0.15), r=1.0)
        reg.rect_(a, b, c, e, (250, 250, 248), r=0.8)
        label = {"power": "POWER", "reset": "RESET", "eject": "EJECT"}[name]
        ly = e + 2.6 if name != "eject" else b - 2.6
        reg.text(label, "arial.ttf", 2.4, (a + c) / 2, ly, GREY)
        if name == "power":
            reg.text("⏻", "seguisym.ttf", 3.6, (a + c) / 2 + 1.5, (b + e) / 2, GREY)
        if name == "eject":
            reg.text("⏏", "seguisym.ttf", 3.2, (a + c) / 2, (b + e) / 2, GREY)
    x, z, r = L.LIGHT
    reg.circle(*at(x, z), r, (200, 40, 30))                            # standby: red
    x, z, (fw, fh) = L.FLAP
    a, b = at(x - fw / 2, z + fh / 2)
    c, e = at(x + fw / 2, z - fh / 2)
    reg.rect_(a, b, c, e, shade(rgb(L.COLOURS["front"]), -0.12), r=1.0)
    reg.rect_(a + 0.4, b + 0.4, c - 0.4, e - 0.4, rgb(L.COLOURS["front"]), r=0.8)
    wii_logo(reg, *at(-6.0, 7.5), 5.0, GREY)
    return reg


def side():
    """The right side, seen from the right: the front at the left, the back at the right."""
    d, h = L.DEPTH, L.HEIGHT
    reg = Region(L.REGIONS["side"], d, h, rgb(L.COLOURS["case"]))

    def at(y, z):
        return y, h - z
    p = L.SIDE_PANEL
    a, b = at(p["y"][0], p["z"][1])
    c, e = at(p["y"][1], p["z"][0])
    reg.rect_(a - 0.5, b - 0.5, c + 0.5, e + 0.5, shade(rgb(L.COLOURS["case"]), -0.1), r=2.0)
    reg.rect_(a, b, c, e, shade(rgb(L.COLOURS["case"]), 0.03), r=1.6)
    # Nintendo's name in its rounded box, top right; the graphics chip's mark, top left.
    x, y = c - 26.0, b + 9.0
    reg.rect_(x - 14.0, y - 4.0, x + 14.0, y + 4.0, shade(rgb(L.COLOURS["case"]), -0.08), r=4.0)
    reg.rect_(x - 13.4, y - 3.4, x + 13.4, y + 3.4, shade(rgb(L.COLOURS["case"]), 0.03), r=3.4)
    reg.text("Nintendo", "arialbd.ttf", 4.2, x, y, shade(rgb(L.COLOURS["case"]), -0.12))
    reg.rect_(a + 8.0, b + 5.0, a + 18.0, b + 13.0, shade(rgb(L.COLOURS["case"]), -0.06), r=0.5)
    reg.text("ATI", "arialbi.ttf", 3.0, a + 13.0, b + 9.0, shade(rgb(L.COLOURS["case"]), -0.2))
    return reg


def remote():
    """The remote's face, its top up."""
    w, h, _ = L.REMOTE["size"]
    reg = Region(L.REGIONS["remote"], w, h, (246, 246, 244))
    cx = w / 2
    reg.circle(cx - 8.0, 8.0, 3.0, (235, 235, 233))
    reg.circle(cx - 8.0, 8.0, 2.4, (250, 250, 248))
    reg.text("⏻", "seguisym.ttf", 3.0, cx - 8.0, 8.0, (220, 40, 40))
    reg.text("POWER", "arial.ttf", 1.6, cx - 8.0, 12.6, GREY)
    for k, (dx, label) in enumerate(((-8.0, "−"), (0.0, "⌂"), (8.0, "+"))):
        reg.circle(cx + dx, 72.0, 2.8, (232, 232, 230))
        reg.circle(cx + dx, 72.0, 2.3, (250, 250, 248))
        reg.text(label, "seguisym.ttf", 2.8, cx + dx, 72.0, (40, 150, 230) if dx == 0 else GREY)
    reg.text("HOME", "arial.ttf", 1.6, cx, 76.5, GREY)
    for row in range(5):                                                 # the speaker's holes
        for col in range(4 if row % 2 else 3):
            reg.circle(cx - 3.0 + col * 2.0 - (1.0 if row % 2 else 0.0), 84.0 + row * 2.0, 0.45, (60, 60, 64))
    for k, label in enumerate(("1", "2")):
        y = 108.0 + k * 11.0
        reg.circle(cx, y, 4.2, (232, 232, 230))
        reg.circle(cx, y, 3.6, (250, 250, 248))
        reg.text(label, "arial.ttf", 3.6, cx, y, GREY)
    for k in range(4):                                                   # the player lights, off
        reg.rect_(cx - 7.5 + k * 5.0, 131.0, cx - 6.0 + k * 5.0, 132.5, (70, 72, 78))
    reg.text("Wii", "arialbd.ttf", 7.0, cx, 140.5, GREY)
    return reg


def label():
    size = 2 * L.DISC["r"]
    reg = Region(L.REGIONS["label"], size, size, (0, 0, 0))
    c = size / 2
    reg.circle(c, c, c, (248, 248, 246))
    art = space((640, 300))
    d = ImageDraw.Draw(art)
    ship(d, 160, 190, 2.2, "#FFFFFF", "#FFB23C")
    d.text((380, 120), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 92), fill="#FFE45C", anchor="mm",
           stroke_width=5, stroke_fill="#5A1A08")
    x0, y0, x1, y1 = reg.box(c - 44.0, c + 14.0, c + 44.0, c + 14.0 + 88.0 * 300 / 640)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    wii_logo(reg, c, c - 30.0, 9.0, (60, 120, 200))
    reg.circle(c, c, 16.0, (230, 232, 236))
    reg.circle(c, c, L.DISC["hole"], (30, 30, 32))
    mask = Image.new("L", reg.img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, reg.img.size[0] - 1, reg.img.size[1] - 1], fill=255)
    reg.img.putalpha(mask)
    return reg


def data_side():
    size = 2 * L.DISC["r"]
    reg = Region(L.REGIONS["data"], size, size, (0, 0, 0))
    c = size / 2
    reg.circle(c, c, c, (200, 204, 214))
    sheen = reg.layer()
    ds = ImageDraw.Draw(sheen)
    for k, colour in enumerate(((255, 90, 90), (255, 210, 90), (90, 255, 140), (90, 160, 255), (200, 110, 255))):
        ds.arc(reg.box(c - 52 + k * 4, c - 52 + k * 4, c + 52 - k * 4, c + 52 - k * 4), 200, 260,
               fill=colour + (110,), width=round(3 * reg.sx))
    reg.over(sheen.filter(ImageFilter.GaussianBlur(2 * reg.sx)))
    reg.circle(c, c, 16.0, (170, 176, 186))
    reg.circle(c, c, L.DISC["hole"], (30, 30, 32))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["case"]))
    for reg in (front(), side(), remote(), label(), data_side()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("glow", (80, 190, 255)), ("green", (70, 230, 90)), ("led", (90, 170, 255)),
                         ("dark", rgb(L.COLOURS["dark"])), ("white", (246, 246, 244))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "wii_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
