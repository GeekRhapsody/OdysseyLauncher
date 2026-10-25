"""The Amstrad GX4000's printing (gx4000_print.png), for the console theme's model (gx4000.py).

One image, laid out as gx4000_layout.REGIONS says: the console's top from above (the louvres along the back, the lines
of its steps, the vents on the rails' inner sides, the wings' chevrons, the pads' symbols, AMSTRAD on the front slope),
its front face (the seam, the stereo jack, the joystick ports either side of the analogue one, the light gun's), the
controller from above (its raised border, the D-pad's dish, AMSTRAD, 1 and 2), the cartridge's label (a made-up game,
Odyssey), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/gx4000_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gx4000_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

BODY = rgb(L.COLOURS["body"])
GREY = rgb(L.COLOURS["grey"])
PINK = rgb(L.COLOURS["pink"])
DARK = rgb(L.COLOURS["dark"])
LINE = (196, 196, 191)
WHITE = (250, 250, 248)


def amstrad(reg, cx, cy, w, h):
    """AMSTRAD's logo, w x h about (cx, cy): white letters on a grey box, a pink stripe slanting behind them."""
    x0, y0 = cx - w / 2, cy - h / 2
    reg.rect_(x0, y0, x0 + w, y0 + h, (138, 141, 138))
    reg.poly([(x0 + w * 0.56, y0 + h), (x0 + w * 0.70, y0 + h), (x0 + w * 0.86, y0), (x0 + w * 0.72, y0)], PINK)
    f = ImageFont.truetype(FONTS + "bahnschrift.ttf", 200)
    f.set_variation_by_name("Bold")
    mask = Image.new("L", (round(f.getlength("AMSTRAD")) + 60, 280), 0)
    ImageDraw.Draw(mask).text((30, 140), "AMSTRAD", font=f, fill=255, anchor="lm")
    mask = mask.crop(mask.getbbox())
    a, b, c, d = reg.box(x0 + w * 0.06, y0 + h * 0.2, x0 + w * 0.94, y0 + h * 0.8)
    mask = mask.resize((max(1, round(c - a)), max(1, round(d - b))), Image.LANCZOS)
    lean = round(mask.height * 0.18)
    wide = Image.new("L", (mask.width + lean, mask.height), 0)
    wide.paste(mask, (0, 0))
    wide = wide.transform(wide.size, Image.AFFINE, (1, 0.18, -0.18 * mask.height, 0, 1, 0), resample=Image.BICUBIC)
    reg.img.paste(Image.new("RGBA", wide.size, WHITE + (255,)), (round(a), round(b)), wide)


# ---- The console -----------------------------------------------------------------------------------------------------

def top():
    """The console from above: x across (-125 at the left), y down from the back (184)."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, BODY)

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    # The louvres along the back, between the wings.
    for k in range(40):
        x = -96.0 + 4.8 * k
        reg.line([at(x, 183.0), at(x + 2.6, 172.0)], LINE, 1.1)
    # The steps' lines across the top, and the wings' chevrons.
    for y in (150.0, 128.0):
        reg.line([at(-48.0, y), at(48.0, y)], LINE, 0.5)
    for side in (-1, 1):
        x0 = side * (L.RAILS["x"] + L.RAILS["half"] + 1.0)
        x1 = side * 124.0
        for y in (142.0, 104.0):
            reg.line([at(x0, y), at((x0 + x1) / 2, y - 7.0), at(x1, y)], LINE, 0.6)
    # The vents on the rails' inner sides: the left rail's along its length, the right's behind the switch.
    rx, half = L.RAILS["x"], L.RAILS["half"]
    for k in range(8):
        y = 78.0 + 10.0 * k
        reg.rect_(*at(-rx + half - 9.5, y + 1.6), *at(-rx + half - 1.5, y - 1.6), DARK, r=0.8)
    for k in range(5):
        y = 108.0 + 11.0 * k
        reg.rect_(*at(rx - half + 1.5, y + 1.6), *at(rx - half + 9.5, y - 1.6), DARK, r=0.8)
    # The pads: the power symbol on the left, II on the right.
    py, pr = L.PADS["y"], L.PADS["r"]
    reg.circle(*at(-rx, py), pr, (222, 222, 217), outline=LINE, width=0.5)
    reg.circle(*at(rx, py), pr, (222, 222, 217), outline=LINE, width=0.5)
    reg.circle(*at(-rx, py + 8.0), 2.2, None, outline=(150, 150, 146), width=0.5)
    reg.line([at(-rx, py + 10.8), at(-rx, py + 8.4)], (150, 150, 146), 0.5)
    for dx in (-1.6, 1.6):
        reg.rect_(*at(rx + dx - 0.5, py - 2.0), *at(rx + dx + 0.5, py - 6.0), (150, 150, 146))
    # AMSTRAD on the front slope.
    (lx, ly), (lw, lh) = L.LOGO["at"], L.LOGO["size"]
    amstrad(reg, *at(lx, ly), lw, lh)
    return reg


def front():
    """The front face: x across (-125 at the left), z down from 36."""
    reg = Region(L.REGIONS["front"], L.WIDTH, 36.0, BODY)

    def at(x, z):
        return x + L.WIDTH / 2, 36.0 - z

    reg.line([at(-125.0, 15.2), at(125.0, 15.2)], LINE, 0.4)
    (jx, jz), jr = L.PORTS["jack"]
    reg.circle(*at(jx, jz), jr + 1.2, (205, 205, 200))
    reg.circle(*at(jx, jz), jr, (34, 34, 36))
    reg.circle(*at(jx, jz), jr * 0.45, (90, 90, 92))
    for name, pins in (("joy_1", (5, 4)), ("analogue", (8, 7)), ("joy_2", (5, 4))):
        (cx, cz), (w, h) = L.PORTS[name]
        shell = [at(cx - w / 2, cz + h / 2), at(cx + w / 2, cz + h / 2), at(cx + w / 2 - 2.0, cz - h / 2),
                 at(cx - w / 2 + 2.0, cz - h / 2)]
        reg.poly(shell, (176, 178, 180))
        inner = [at(cx - w / 2 + 1.6, cz + h / 2 - 1.4), at(cx + w / 2 - 1.6, cz + h / 2 - 1.4),
                 at(cx + w / 2 - 3.2, cz - h / 2 + 1.4), at(cx - w / 2 + 3.2, cz - h / 2 + 1.4)]
        reg.poly(inner, (30, 30, 32))
        for row, n in ((1.8, pins[0]), (-1.8, pins[1])):
            for k in range(n):
                x = cx - (n - 1) * 1.4 + 2.8 * k
                reg.circle(*at(x, cz + row), 0.5, (196, 168, 96))
    (gx, gz), (gw, gh) = L.PORTS["gun"]
    reg.rect_(*at(gx - gw / 2, gz + gh / 2), *at(gx + gw / 2, gz - gh / 2), (36, 36, 38))
    reg.rect_(*at(gx - gw / 2 + 2.4, gz + gh / 2 - 2.4), *at(gx + gw / 2 - 2.4, gz - gh / 2 + 3.6), (14, 14, 16))
    return reg


# ---- The controller and the cartridge --------------------------------------------------------------------------------

def pad():
    """The controller from above: x across (-64 at the left), y down from its back edge."""
    pw, pd, _ = L.PAD["size"]
    reg = Region(L.REGIONS["pad"], pw, pd, BODY)

    def at(x, y):
        return x + pw / 2, pd - y

    reg.rect_(*at(-pw / 2 + 4.0, pd - 4.0), *at(pw / 2 - 4.0, 4.0), None, r=5.0, outline=LINE, width=0.5)
    (dx, dy), dish = L.DPAD["at"], L.DPAD["dish"]
    reg.circle(*at(dx, dy), dish, (176, 177, 173), outline=(160, 160, 156), width=0.6)
    amstrad(reg, *at(-4.0, 17.0), 30.0, 12.0)
    for k, (bx, by) in enumerate(L.BUTTONS["at"]):
        reg.circle(*at(bx, by), L.BUTTONS["r"] + 1.6, (232, 232, 228), outline=LINE, width=0.4)
        reg.text(str(k + 1), "arialbd.ttf", 4.0, *at(bx, by - 11.0), (60, 60, 62))
    return reg


def cart():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["cart"], lw, lh, (24, 20, 40))
    art = space((560, 440)).convert("RGB")
    ship(ImageDraw.Draw(art), 170, 270, 3.4, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 0.0, lw, lh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 8.0, WHITE)
    reg.rect_(0.0, 8.0, lw, 9.0, PINK)
    reg.text("GX4000", "arialbd.ttf", 4.2, lw - 2.0, 4.0, (60, 60, 62), anchor="rm")
    reg.text("ODYSSEY", "ariblk.ttf", 7.4, lw / 2, 16.0, (255, 214, 70))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), BODY)
    for reg in (top(), front(), pad(), cart()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(body=BODY, grey=GREY, pink=PINK, red=rgb(L.COLOURS["red"]), dark=DARK, lit=(255, 60, 40))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "gx4000_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
