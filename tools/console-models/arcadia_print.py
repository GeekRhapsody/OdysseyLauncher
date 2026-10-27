"""The Arcadia 2001 card's printing (arcadia_print.png), for the console theme's Arcadia 2001 model (arcadia.py).

One image, laid out as arcadia_layout.REGIONS says, each region in millimetres as the model's UVs map it: the console
from above (the bays' floors; the centre block's ribbed grille, the strip of buttons with RESET, SELECT, OPTION, START
and POWER over them, the silver panel with ARCADIA-2001, the red, green and blue bars, BY Emerson and POWER ON, the
slot's frame), the walnut band, the two controllers' faces (the silver strip, the keypad's twelve keys, the joystick's
recess and spun-metal disc, LEFT or RIGHT HAND CONTROLLER on the black strip at the foot), the cartridge's blue label and
its title end (a made-up game from tools/made-up-games, its title in the Arcadia's rainbow letters), and swatches. Run
it with the system Python (Pillow):

    python tools/console-models/arcadia_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcadia_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region, gradient  # noqa: E402

C = {name: rgb(colour) for name, colour in L.COLOURS.items()}
INK = (18, 16, 16)
BARS = [(214, 40, 40), (40, 170, 70), (40, 90, 210)]
TITLE = "NEBULA SWARM"                    # the made-up game on the cartridge (tools/made-up-games's nebswarm)
RAINBOW = [(236, 52, 48), (246, 140, 30), (248, 214, 40), (60, 190, 80), (50, 140, 230), (150, 80, 200)]


def lettered(reg, text, font, size, x, y, fill, anchor="mm", lean=0.0):
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    d.text(reg.p(x, y), text, font=f, fill=fill + (255,), anchor=anchor)
    if lean:
        yc = reg.p(0, y)[1]
        layer = layer.transform(layer.size, Image.AFFINE, (1, lean, -lean * yc, 0, 1, 0))
    reg.over(layer)


def bars(reg, x, y, h):
    """The three slanted bars, red, green and blue, h tall, from x."""
    for k, colour in enumerate(BARS):
        x0 = x + k * h * 0.55
        reg.poly([(x0 + h * 0.3, y - h / 2), (x0 + h * 0.62, y - h / 2), (x0 + h * 0.32, y + h / 2),
                  (x0, y + h / 2)], colour)


def emerson(reg, x, y, h, ink):
    """Emerson's mark, h tall, its left edge's middle at (x, y): an E in a circle, then the name."""
    reg.circle(x + h / 2, y, h / 2, None, outline=ink, width=h * 0.1)
    reg.text("E", "timesbd.ttf", h * 0.75, x + h / 2, y, ink)
    reg.text("Emerson", "timesbi.ttf", h * 0.95, x + h * 1.25, y, ink, anchor="lm")


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, C["shell"])

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y

    def on_slope(x, s):
        return at(x, L.slope_point(s)[0])
    half = L.BLOCK["x"]
    for side in (-1, 1):                                       # the bays' floors
        x0, x1 = sorted((side * half, side * (L.WIDTH / 2 - L.RIM["width"])))
        reg.rect_(*at(x0, L.WEDGE["y"][0]), *at(x1, L.RIM["width"]), C["floor"])
    g = L.GRILLE                                               # the grille: its recess, its ribs
    reg.rect_(*on_slope(g["x"][0], g["s"][1]), *on_slope(g["x"][1], g["s"][0]), C["dark"], r=1.0)
    for k in range(g["ribs"]):
        x = g["x"][0] + (g["x"][1] - g["x"][0]) * (k + 0.5) / g["ribs"]
        reg.rect_(*on_slope(x - 0.7, g["s"][1] - 1.0), *on_slope(x + 0.7, g["s"][0] + 1.0), shade(C["dark"], 0.25))
    b = L.BUTTONS                                              # the buttons' strip and their names
    reg.rect_(*on_slope(-56.0, b["s"][1]), *on_slope(56.0, b["s"][0]), C["dark"], r=1.5)
    mid = (b["s"][0] + b["s"][1]) / 2
    for x in b["x"]:
        reg.circle(*on_slope(x, mid), b["r"] + 0.8, shade(C["dark"], -0.3))
    p = L.PANEL                                                # the silver panel, the buttons' names along its foot
    a, top_y = on_slope(p["x"][0], p["s"][1])
    c, bottom_y = on_slope(p["x"][1], b["s"][1] + 0.5)
    silver = gradient((round((c - a) * reg.sx), round((bottom_y - top_y) * reg.sy)),
                      [(0.0, shade(C["silver"], 0.25)), (0.5, C["silver"]), (1.0, shade(C["silver"], 0.12))])
    reg.img.paste(silver, (round(a * reg.sx), round(top_y * reg.sy)))
    for x, word in zip(b["x"] + (sum(b["power"]) / 2,), ("RESET", "SELECT", "OPTION", "START", "POWER")):
        reg.text(word, "arialbd.ttf", 2.4, *on_slope(x, b["s"][1] + 2.6), INK)
    lettered(reg, "ARCADIA-2001", "ariblk.ttf", 7.6, *on_slope(-30.0, 90.0), INK, anchor="lm", lean=0.15)
    reg.text("™", "arial.ttf", 2.4, *on_slope(29.0, 92.0), INK)
    bars(reg, *on_slope(-30.0, 80.0), 5.0)
    reg.text("BY", "arialbd.ttf", 2.4, *on_slope(-12.0, 80.0), INK)
    emerson(reg, *on_slope(-7.0, 80.0), 4.0, INK)
    lx, ly = on_slope(L.LIGHT["x"], L.LIGHT["s"])
    reg.circle(lx, ly, L.LIGHT["r"] + 0.8, INK)
    reg.circle(lx, ly, L.LIGHT["r"], (110, 40, 44))
    reg.text("POWER ON", "arialbd.ttf", 2.0, lx, ly + 5.0, INK)
    (x0, x1), (y0, y1) = L.SLOT["x"], L.SLOT["y"]             # the slot's frame and opening
    f = L.SLOT["frame"]
    reg.rect_(*at(x0 - f, y1 + f), *at(x1 + f, y0 - f), shade(C["shell"], -0.2), r=2.0)
    reg.rect_(*at(x0, y1), *at(x1, y0), (14, 12, 12), r=1.0)
    return reg


def grain(reg, w, h, colour, seed=2001, count=None, along=True):
    """Vinyl walnut's grain over a region w x h (millimetres): streaks running along it (across it if not along)."""
    rng = random.Random(seed)
    for _ in range(count or round(w * h / 125)):
        a = rng.uniform(0.5, (h if along else w) - 0.5)
        b0 = rng.uniform(-50.0, w if along else h)
        length = rng.uniform(60.0, 260.0)
        wave = rng.uniform(4.0, 9.0)
        pts = [(b0 + t * length, a + 0.35 * math.sin(t * wave)) for t in [k / 12 for k in range(13)]]
        reg.line(pts if along else [(y, x) for x, y in pts], shade(colour, rng.choice((-0.25, -0.18, 0.08))),
                 rng.uniform(0.12, 0.3))


def wood():
    """The walnut band: grain running along it."""
    w, h = 1000.0, 15.0
    reg = Region(L.REGIONS["wood"], w, h, C["wood"])
    grain(reg, w, h, C["wood"], count=120)
    return reg


def controller(name):
    """A controller's face from above: x across, v down from its top end (the keypad's) to its foot."""
    length, w, _ = L.PAD["size"]
    p = L.PAD
    reg = Region(L.REGIONS[name], w, length, C["shell"])
    s0, s1 = p["strip"]
    reg.rect_(3.0, s0, w - 3.0, s1, C["silver"], r=1.0)
    bars(reg, 7.0, (s0 + s1) / 2, 7.0)
    lettered(reg, "ARCADIA-2001", "ariblk.ttf", 5.0, 21.0, (s0 + s1) / 2, INK, anchor="lm", lean=0.15)
    v0, v1, inset, _ = p["window"]
    reg.rect_(inset, v0, w - inset, v1, C["champagne"], r=1.5)
    legends = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "clear", "0", "enter"]
    for k, legend in enumerate(legends):
        cx = w / 2 + p["keys"]["cols"][k % 3]
        cy = p["keys"]["rows"][k // 3]
        reg.circle(cx, cy, p["keys"]["r"], shade(C["champagne"], 0.12), outline=INK, width=0.7)
        reg.text(legend, "arial.ttf", 2.6 if len(legend) > 1 else 5.0, cx, cy, INK)
    d = p["disc"]
    reg.circle(w / 2, d["v"], d["recess"], shade(C["shell"], -0.35))
    for k in range(12):                                       # the spun metal's rings
        r = d["r"] * (1 - k / 12)
        reg.circle(w / 2, d["v"], r, shade(C["disc"], 0.1 if k % 2 else -0.1))
    f0, f1 = p["foot"]
    reg.rect_(2.0, f0, w - 2.0, f1 - 1.0, (14, 13, 13), r=1.0)
    reg.text(("LEFT" if name == "left" else "RIGHT") + " HAND CONTROLLER", "arialbd.ttf", 3.0, w / 2, (f0 + f1) / 2 - 0.5,
             (200, 200, 196))
    return reg


def cartridge():
    """The cartridge's face: the blue label."""
    w, _, h = L.CART["size"]
    reg = Region(L.REGIONS["cart"], w, h, C["cart"])
    reg.rect_(5.0, 5.0, w - 5.0, h - 5.0, C["label"])
    white = (240, 244, 248)
    reg.text("VIDEO GAME CARTRIDGE", "arialbd.ttf", 6.2, w / 2, 13.0, white)
    reg.text("FOR USE ONLY WITH THE", "arial.ttf", 2.6, w / 2, 19.0, white)
    lettered(reg, "ARCADIA-2001", "ariblk.ttf", 5.0, w / 2, 24.5, white)
    bars(reg, w / 2 - 22.0, 30.5, 4.0)
    emerson(reg, w / 2 - 4.0, 30.5, 3.2, white)
    reg.text("ONE OR TWO PLAYERS", "arialbd.ttf", 3.6, w / 2, 39.0, white)
    for k, line in enumerate(("Waves of alien swarms dive at your ship", "Shoot the leaders for bonus points",
                              "Six speeds, three ships", "Joystick moves, either button fires")):
        reg.text("• " + line, "arial.ttf", 2.7, w / 2, 47.0 + k * 6.0, white)
    reg.text("Cartridge No. 7", "arial.ttf", 2.4, 9.0, h - 10.0, white, anchor="lm")
    reg.text(TITLE, "arialbd.ttf", 2.4, 9.0, h - 7.0, white, anchor="lm")
    reg.text("MADE IN HONG KONG", "arial.ttf", 2.2, w - 9.0, h - 7.0, white, anchor="rm")
    return reg


def cartridge_end():
    """The cartridge's title end, black, the title in rainbow letters, each split across into two colours."""
    w, t, _ = L.CART["size"]
    reg = Region(L.REGIONS["cart_end"], w, t, C["cart"])
    reg.rect_(6.0, 4.0, w - 6.0, t - 4.0, (10, 10, 12), r=2.0)
    f = ImageFont.truetype(FONTS + "ariblk.ttf", round(10.0 * reg.sx))
    total = f.getlength(TITLE) / reg.sx
    x = (w - total) / 2
    for k, ch in enumerate(TITLE):
        top_, bottom = RAINBOW[k % len(RAINBOW)], RAINBOW[(k + 2) % len(RAINBOW)]
        layer = reg.layer()
        ImageDraw.Draw(layer).text(reg.p(x, t / 2), ch, font=f, fill=(255, 255, 255, 255), anchor="lm")
        mask = layer.getchannel("A")
        split = Image.new("RGBA", layer.size, top_ + (255,))
        ImageDraw.Draw(split).polygon([(0, layer.height), (layer.width, layer.height),
                                       (layer.width, layer.height * 0.35), (0, layer.height * 0.65)],
                                      fill=bottom + (255,))
        split.putalpha(mask)
        reg.over(split)
        x += f.getlength(ch) / reg.sx
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["shell"])
    for reg in (top(), wood(), controller("left"), controller("right"), cartridge(), cartridge_end()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(C, black=(10, 10, 12))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "arcadia_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
