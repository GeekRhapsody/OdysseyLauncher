"""The Super Nintendo's printing, for the console theme's model (tools/console-models/snes.py).

Draws its atlas, its regions as snes_layout.py places them, each in millimetres as the model's planar UVs map it: the
top seen from above (the dark panel, the slot's dust flaps, POWER's well and its ON and OFF, EJECT, RESET, the four
coloured dots, the name and the power light's slot in front of the panel); the ports' recess seen from in front (the two
controller ports and their numbers); the cartridge's label (a made-up game, Odyssey, under the console's name); and the
swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/snes_print.py <kind> <out folder>

It writes <kind>_print.png there (snes).
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snes_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

INK = (52, 54, 60)
DOTS = [((0, 92, 190), -1, -1), ((214, 38, 44), 1, -1), ((0, 160, 72), -1, 1), ((244, 198, 0), 1, 1)]


def top_point(x, y):
    """A point of the top (x from the middle, y back from the front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


def nintendo(reg, k, x, y, size, colour):
    """Nintendo's name in its rounded box, size tall, its left edge's middle at (x, y)."""
    font = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(size * 0.62 * reg.sx)))
    width = font.getlength("Nintendo") / reg.sx + size * 0.7
    reg.rect_(x, y - size / 2, x + width, y + size / 2, colour, r=size / 2)
    reg.rect_(x + 0.35, y - size / 2 + 0.35, x + width - 0.35, y + size / 2 - 0.35, rgb(k["case"]), r=size / 2 - 0.35)
    reg.draw.text(reg.p(x + width / 2, y), "Nintendo", font=font, fill=colour, anchor="mm")
    return width


def dots(reg, k, x, y, r):
    reg.circle(x, y, r + 0.5, shade(rgb(k["panel"]), -0.2))
    reg.circle(x, y, r, (210, 210, 214))
    for colour, dx, dy in DOTS:
        reg.circle(x + dx * r * 0.4, y + dy * r * 0.3, r * 0.27, colour)


def top(k):
    case, panel = rgb(k["case"]), rgb(k["panel"])
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, case)
    p = L.PANEL
    (x0, y0), (x1, y1) = top_point(-p["x"], p["y"][1]), top_point(p["x"], p["y"][0])
    reg.rect_(x0, y0, x1, y1, panel, r=p["r"])

    # The slot's dust flaps, meeting along its middle, with the reminder printed across them.
    s = L.SLOT
    (sx0, sy0), (sx1, sy1) = top_point(-s["x"], s["y"][1]), top_point(s["x"], s["y"][0])
    reg.rect_(sx0 - 1.0, sy0 - 1.0, sx1 + 1.0, sy1 + 1.0, shade(panel, -0.25), r=(sy1 - sy0) / 2 + 1.0)
    reg.rect_(sx0, sy0, sx1, sy1, rgb(L.COLOURS["flap"]), r=(sy1 - sy0) / 2)
    reg.rect_(sx0 + 6.0, (sy0 + sy1) / 2 - 0.25, sx1 - 6.0, (sy0 + sy1) / 2 + 0.25, (40, 40, 44))
    reg.text(k["slot_text"], "arial.ttf", 2.0, (sx0 + sx1) / 2, (sy0 + sy1) / 2 - 3.4, shade(panel, 0.25))
    for x in (sx0 + 5.0, sx1 - 5.0):
        reg.rect_(x - 0.5, sy0 + 3.0, x + 0.5, sy1 - 3.0, (40, 40, 44))

    # POWER's well (ON and OFF beside it), EJECT, RESET's well.
    w = L.POWER
    (a, b), (c, e) = top_point(w["x"][0], w["y"][1]), top_point(w["x"][1], w["y"][0])
    reg.rect_(a - 1.0, b - 1.0, c + 1.0, e + 1.0, (236, 236, 238), r=2.5)
    reg.rect_(a, b, c, e, (88, 88, 92), r=2.0)
    reg.text("POWER", "arialbd.ttf", 2.8, (a + c) / 2, e - 3.2, (236, 236, 238))
    reg.text("ON", "arial.ttf", 2.0, a - 5.0, b + 4.0, shade(panel, -0.25))
    reg.text("OFF", "arial.ttf", 2.0, a - 5.0, b + 8.0, shade(panel, -0.25))
    button = L.EJECT
    (a, b), (c, e) = top_point(button["x"][0], button["y"][1]), top_point(button["x"][1], button["y"][0])
    reg.rect_(a, b, c, e, shade(panel, 0.12), r=3.0)
    reg.text("EJECT", "arial.ttf", 3.0, (a + c) / 2, (b + e) / 2 + 2.0, shade(panel, 0.32))
    button = L.RESET
    (a, b), (c, e) = top_point(button["x"][0], button["y"][1]), top_point(button["x"][1], button["y"][0])
    reg.rect_(a - 1.0, b - 1.0, c + 1.0, e + 1.0, (236, 236, 238), r=2.5)
    reg.rect_(a, b, c, e, (92, 92, 96), r=2.0)
    reg.text("RESET", "arialbd.ttf", 2.8, (a + c) / 2, e - 3.4, (236, 236, 238))
    dots(reg, k, *top_point(L.DOTS[0], L.DOTS[1]), L.DOTS[2])

    # In front of the panel: the name, and the power light's slot under POWER.
    x, y = top_point(-80.0, 46.0)
    nintendo(reg, k, x, y, 5.0, INK)
    for line, size, dy in k["name"]:
        reg.text(line, "arialbi.ttf", size, x, y + dy, INK, anchor="lm")
    lx, ly = top_point(L.LED[0], L.LED[1])
    reg.text("POWER", "arial.ttf", 1.8, lx, ly - 4.0, shade(case, -0.3))
    reg.rect_(lx - L.LED[2] / 2, ly - L.LED[3] / 2, lx + L.LED[2] / 2, ly + L.LED[3] / 2, (70, 40, 40), r=1.0)
    return reg


def front(k):
    """The ports' recess, seen from in front: x to the right, z up."""
    w, (z0, z1) = 2 * L.PORTS["x"], L.PORTS["z"]
    h = z1 - z0
    reg = Region(L.REGIONS["front"], w, h, shade(rgb(k["case"]), -0.06))
    for n, cx in enumerate((-36.0, 36.0)):
        x = cx + L.PORTS["x"]
        reg.rect_(x - 18.0, h / 2 - 6.0, x + 18.0, h / 2 + 6.0, shade(rgb(k["case"]), -0.3), r=5.0)
        reg.rect_(x - 16.5, h / 2 - 4.5, x + 16.5, h / 2 + 4.5, (196, 196, 200), r=4.0)
        for j in range(7):
            reg.circle(x - 13.0 + j * (26.0 / 6) + (1.2 if j > 3 else 0.0), h / 2, 1.3, (44, 44, 48))
        reg.rect_(x + 2.2, h / 2 - 4.5, x + 2.8, h / 2 + 4.5, shade(rgb(k["case"]), -0.3))
        nx = 6.0 if n == 0 else w - 6.0
        reg.circle(nx, h / 2, 3.4, shade(rgb(k["case"]), -0.1))
        reg.text(str(n + 1), "arialbd.ttf", 3.6, nx, h / 2, shade(rgb(k["case"]), -0.32))
    return reg


def label(k):
    """The cartridge's label: the console's name across its top band, Odyssey's art, its title."""
    lw, lh, _ = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (230, 230, 232))
    art = space((1080, 760))
    d = ImageDraw.Draw(art)
    ship(d, 330, 470, 3.4, "#FFFFFF", "#FFB23C")
    d.text((540, 150), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 150), fill="#FFE45C", anchor="mm",
           stroke_width=7, stroke_fill="#5A1A08")
    x0, y0, x1, y1 = reg.box(3.0, 11.0, lw - 3.0, lh - 3.0)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 9.5, (64, 64, 70))
    dots(reg, k, 6.5, 4.8, 3.6)
    reg.text(k["label"], "arialbi.ttf", 4.0, 13.0, 4.8, (240, 240, 242), anchor="lm")
    return reg


def main(kind, out):
    k = dict(L.KINDS[kind], **TEXTS[kind])
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(k["case"]))
    for reg in (top(k), front(k), label(k)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("led", (255, 52, 40)), ("dark", rgb(L.COLOURS["dark"])), ("flap", rgb(L.COLOURS["flap"]))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, f"{kind}_print.png")
    image.save(path, optimize=True)
    print(path)


# Each kind's words: the name in front of the panel (line, size, offset), the slot's reminder, the label's band.
TEXTS = {
    "snes": dict(name=[("SUPER NINTENDO", 7.0, 7.5), ("ENTERTAINMENT SYSTEM", 3.2, 13.0)], slot_text="PAL VERSION",
                 label="SUPER NINTENDO"),
}

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
