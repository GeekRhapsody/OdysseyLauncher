"""The Xbox set's printing, for the console theme's Xbox model (tools/console-models/xbox.py).

Draws its atlas, its regions as xbox_layout.py places them, each in millimetres as the model's planar UVs map it: the
console from above (the jewel, green with XBOX on it, its dark ring); its front (the XBOX plate, the four controller
ports and their numbers, the Compact Disc and Dolby Digital marks, Microsoft, the lid's seam, the tray's front); the
Controller S from above (its jewel with the X and XBOX, the letters on A, B, X and Y, BACK and START); the DVD's label
(a made-up game, Odyssey); and the swatches small parts take their colour from. Run it with the system Python
(Pillow):

    python tools/console-models/xbox_print.py <out folder>

It writes xbox_print.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xbox_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
GREEN = (110, 190, 40)
INK = (190, 190, 196)
COLOURS = dict(a=(110, 200, 70), b=(230, 90, 40), x=(80, 110, 230), y=(240, 200, 40), white=(230, 230, 230),
               black=(26, 26, 28))


def xbox_word(reg, cx, cy, h, ink):
    """XBOX in the wide, thin letters of the logo, h tall, its middle at (cx, cy)."""
    mask = Image.new("L", (1200, 260), 0)
    ImageDraw.Draw(mask).text((20, 130), "XBOX", font=ImageFont.truetype(FONTS + "arial.ttf", 220), fill=255,
                              anchor="lm")
    mask = mask.crop(mask.getbbox())
    w = h * 4.4
    x0, y0, x1, y1 = reg.box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    mask = mask.resize((max(1, round(x1 - x0)), max(1, round(y1 - y0))), Image.LANCZOS)
    reg.img.paste(Image.new("RGBA", mask.size, ink + (255,)), (round(x0), round(y0)), mask)


def x_mark(reg, cx, cy, s, colour):
    """The Xbox's X: two curved blades crossing, s across."""
    for sign in (-1, 1):
        points = []
        for k in range(13):
            t = -1 + 2 * k / 12
            w = 0.12 * s * (1 - abs(t) ** 2) + 0.02 * s
            points.append((cx + t * s / 2, cy + sign * t * s / 2 - w))
        for k in range(12, -1, -1):
            t = -1 + 2 * k / 12
            w = 0.12 * s * (1 - abs(t) ** 2) + 0.02 * s
            points.append((cx + t * s / 2, cy + sign * t * s / 2 + w))
        reg.poly(points, colour)


# ---- The console -----------------------------------------------------------------------------------------------------

def top():
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["top"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y
    (jx, jy), r = L.JEWEL["at"], L.JEWEL["r"]
    reg.circle(*at(jx, jy), L.JEWEL["ring"], (8, 8, 9))
    reg.circle(*at(jx, jy), r, GREEN)
    reg.circle(*at(jx - r * 0.25, jy + r * 0.3), r * 0.55, shade(GREEN, 0.12))
    reg.circle(*at(jx, jy), r, None, outline=shade(GREEN, -0.25), width=0.8)
    xbox_word(reg, *at(jx, jy), 6.0, (226, 240, 220))       # XBOX across the jewel, reading from the front
    return reg


def front():
    w, h = L.WIDTH, L.HEIGHT
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    reg.line([at(-w / 2, L.SEAM), at(w / 2, L.SEAM)], (6, 6, 7), 0.6)
    (px0, px1), (pz0, pz1) = L.PLATE["x"], L.PLATE["z"]
    reg.rect_(*at(px0, pz1), *at(px1, pz0), shade(CASE, 0.06), r=1.0)
    xbox_word(reg, *at((px0 + px1) / 2, (pz0 + pz1) / 2), 7.4, INK)
    pw, ph = L.PORTS["size"]
    for k, x in enumerate(L.PORTS["x"]):
        z = L.PORTS["z"]
        reg.rect_(*at(x - pw / 2, z + ph / 2), *at(x + pw / 2, z - ph / 2), (6, 6, 7), r=ph / 2)
        reg.rect_(*at(x - pw / 2 + 3.0, z + 2.0), *at(x + pw / 2 - 3.0, z - 2.0), (30, 30, 34), r=2.0)
        reg.circle(*at(x, L.PORTS["numbers"]), 3.4, shade(CASE, 0.08))
        reg.text(str(k + 1), "arialbd.ttf", 4.2, *at(x, L.PORTS["numbers"]), (8, 8, 9))
    reg.text("COMPACT", "arialbd.ttf", 1.6, *at(96.0, 56.0), INK)
    reg.text("disc", "arialbd.ttf", 4.2, *at(96.0, 52.0), INK)
    reg.rect_(*at(126.0, 57.0), *at(150.0, 49.0), None, outline=INK, width=0.3)
    reg.text("DOLBY", "arialbd.ttf", 2.2, *at(138.0, 54.5), INK)
    reg.text("DIGITAL", "arial.ttf", 1.8, *at(138.0, 51.0), INK)
    reg.text("Microsoft", "arialbi.ttf", 3.4, *at(140.0, 9.0), shade(CASE, 0.25))
    return reg


# ---- The controller ------------------------------------------------------------------------------------------------

def pad():
    w = 2 * max(x for x, _ in L.PAD_RIGHT)
    d = max(y for _, y in L.PAD_RIGHT)
    reg = Region(L.REGIONS["pad"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y
    (cx, cy), r = L.CENTRE["at"], L.CENTRE["r"]
    reg.circle(*at(cx, cy), r + 2.0, (8, 8, 9))
    reg.circle(*at(cx, cy), r, (14, 14, 16))
    x_mark(reg, *at(cx, cy + 3.0), r * 1.0, (120, 200, 40))
    xbox_word(reg, *at(cx, cy - 6.0), 2.4, (120, 200, 40))
    (dx, dy) = L.DPAD["at"]
    reg.circle(*at(dx, dy), L.DPAD["well"] + 1.0, (8, 8, 9))
    fx, fy = L.FACE["at"]
    reg.circle(*at(fx, fy), L.FACE["spacing"] + L.FACE["r"] + 1.0, (10, 10, 12))
    s = L.FACE["spacing"]
    for name, (dxx, dyy) in (("y", (0, 1)), ("x", (-1, 0)), ("b", (1, 0)), ("a", (0, -1))):
        bx, by = at(fx + dxx * s, fy + dyy * s)
        reg.circle(bx, by, L.FACE["r"], COLOURS[name])
        reg.text(name.upper(), "arialbd.ttf", 4.6, bx, by, shade(COLOURS[name], 0.35))
    for name in ("white", "black"):
        bx, by = at(*L.BLACK_WHITE[name])
        reg.circle(bx, by, L.BLACK_WHITE["r"] + 1.0, (8, 8, 9))
        reg.circle(bx, by, L.BLACK_WHITE["r"], COLOURS[name])
    for name in ("back", "start"):
        bx, by = at(*L.BACK_START[name])
        reg.circle(bx, by, L.BACK_START["r"], (10, 10, 12))
        reg.text(name.upper(), "arialbd.ttf", 2.2, bx - 1.0, by + 5.4, INK)
    return reg


def disc():
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (20, 20, 24))
    c = dm / 2
    art = space((600, 600)).convert("RGB")
    ship(ImageDraw.Draw(art), 180, 330, 4.0, "#FFFFFF", "#FFB23C")
    mask = Image.new("L", reg.img.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0), fill=255)
    md.ellipse(reg.box(c - 21.0, c - 21.0, c + 21.0, c + 21.0), fill=0)
    x0, y0, x1, y1 = reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.img.paste(layer, (0, 0), mask)
    reg.rect_(c - 58.0, c + 40.0, c + 58.0, c + 50.0, (110, 190, 40))                         # the green band
    xbox_word(reg, c, c + 45.0, 5.0, (255, 255, 255))
    reg.text("ODYSSEY", "ariblk.ttf", 11.0, c, c - 36.0, (255, 214, 70))
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("green", GREEN), ("green_lit", (140, 255, 90)), ("silver", (190, 192, 196)),
                         ("dark", (8, 8, 9)), ("a", COLOURS["a"]), ("b", COLOURS["b"]), ("x", COLOURS["x"]),
                         ("y", COLOURS["y"]), ("white", COLOURS["white"]), ("black", COLOURS["black"])):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "xbox_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
