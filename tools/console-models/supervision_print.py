"""The Watara Supervision's printing and screens, for the console theme's Supervision model
(tools/console-models/supervision.py).

Draws its atlas, its regions as supervision_layout.py places them, each in millimetres as the model's planar UVs map it
(the screens in their pixels): the screen unit's front (the black bezel, HIGH QUALITY STEREO SOUND between its two
turquoise lines, WATARA, the switched-off LCD, the light); the controls' front (the D-pad's well, SELECT, PAUSE and
START, A and B, SUPERVISION and its triangle, the speaker's slots, the raised rim's line); the screens (the start-up
logo, the title of a made-up game, Odyssey, and a moment of its play, in the LCD's four greens); the cartridge's label;
and the swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/supervision_print.py <out folder>

It writes supervision_print.png there.
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import supervision_layout as L  # noqa: E402
from msx_layout import inset  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
TURQUOISE = rgb(L.COLOURS["turquoise"])
INK = (36, 36, 40)
LCD_OFF = (150, 160, 70)


def supervision_logo(reg, cx, cy, h, ink, accent):
    """SUPERVISION, its O's middle a triangle in the accent colour; h tall, its middle at (cx, cy)."""
    f = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(h * 1.32 * reg.sx)))
    w = reg.draw.textlength("SUPERVISION", font=f) / reg.sx
    x = cx - w / 2
    head = reg.draw.textlength("SUPERVISI", font=f) / reg.sx
    o = reg.draw.textlength("O", font=f) / reg.sx
    reg.draw.text(reg.p(x, cy), "SUPERVISI", font=f, fill=ink, anchor="lm")
    reg.draw.text(reg.p(x + head + o, cy), "N", font=f, fill=ink, anchor="lm")
    ox = x + head
    reg.draw.arc(reg.box(ox + o * 0.06, cy - h * 0.5, ox + o * 0.94, cy + h * 0.5), 200, 340, fill=ink,
                 width=reg.width(h * 0.17))
    reg.poly([(ox + o * 0.5, cy - h * 0.2), (ox + o * 0.88, cy + h * 0.5), (ox + o * 0.12, cy + h * 0.5)], accent)


# ---- The fronts --------------------------------------------------------------------------------------------------------

def screen_front():
    w, h, _ = L.UNIT["size"]
    reg = Region(L.REGIONS["screen_front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    (bx0, bx1), (bz0, bz1) = L.BEZEL["x"], L.BEZEL["z"]
    reg.rect_(*at(bx0, bz1), *at(bx1, bz0), (14, 14, 16), r=L.BEZEL["r"])
    (lx, lz), (lw, lh) = L.LCD["at"], L.LCD["size"]
    reg.rect_(*at(lx - lw / 2, lz + lh / 2), *at(lx + lw / 2, lz - lh / 2), LCD_OFF)
    ty = bz1 - 4.2
    reg.text("HIGH  QUALITY  STEREO  SOUND", "arialbi.ttf", 3.0, *at(lx, ty), TURQUOISE)
    reg.line([at(bx0 + 3.0, ty), at(lx - 25.0, ty)], TURQUOISE, 0.5)
    reg.line([at(lx + 25.0, ty), at(bx1 - 3.0, ty)], TURQUOISE, 0.5)
    reg.text("WATARA", "timesbi.ttf", 5.0, *at(bx0 + 4.0, bz0 + 4.8), TURQUOISE, anchor="lm")
    reg.line([at(bx0 + 4.0, bz0 + 2.0), at(bx0 + 24.0, bz0 + 2.0)], TURQUOISE, 0.35)
    reg.circle(*at(*L.LIGHT["at"]), L.LIGHT["r"], (70, 70, 74))
    return reg


def controls_front():
    w, h, _ = L.CONTROLS["size"]
    reg = Region(L.REGIONS["controls_front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    rim = [at(x, z) for x, z in inset(L.controls_outline(), 6.0)]   # the raised rim's line, inside the edge
    reg.line(rim + rim[:1], shade(CASE, -0.2), 0.5)
    (dx, dz), s = L.DPAD["at"], L.DPAD["size"] / 2 + 1.0
    reg.poly([at(dx, dz + s), at(dx + s, dz), at(dx, dz - s), at(dx - s, dz)], (8, 8, 10))
    for name, label, dz_ in (("select", "SELECT", -4.2), ("start", "START", -4.2)):
        x, z = L.SMALL[name]
        sw, sh = L.SMALL["size"]
        reg.rect_(*at(x - sw / 2 - 0.6, z + sh / 2 + 0.6), *at(x + sw / 2 + 0.6, z - sh / 2 - 0.6), shade(CASE, -0.35),
                  r=sh / 2)
        reg.text(label, "arialbd.ttf", 2.4, *at(x, z + dz_), INK)
    x, z = L.SMALL["start"]
    reg.text("PAUSE", "arialbd.ttf", 2.4, *at(x, z + 4.2), INK)
    for name in ("a", "b"):
        x, z = L.AB[name]
        reg.circle(*at(x, z), L.AB["r"] + 0.8, shade(CASE, -0.3))
        reg.text(name.upper(), "arialbd.ttf", 3.2, *at(x + (5.0 if name == "a" else -1.0), z - 9.5), INK)
    supervision_logo(reg, *at(*L.LOGO["at"]), L.LOGO["height"], INK, TURQUOISE)
    sx, sz = L.SPEAKER["at"]
    for k in range(3):
        reg.rect_(*at(sx - 7.0 + k * 1.2, sz + 3.2 - 2.4 * k), *at(sx + 7.0 + k * 1.2, sz + 2.4 - 2.4 * k), (40, 40, 44),
                  r=0.4)
    return reg


# ---- The screens -------------------------------------------------------------------------------------------------------

W, H = 320, 320                                      # 160 x 160, doubled


def boot():
    reg = Region((0, 0, W, H), W, H, (255, 255, 255))
    supervision_logo(reg, W / 2, H * 0.45, 26.0, (20, 20, 20), (90, 90, 90))
    reg.text("WATARA", "timesbi.ttf", 22.0, W / 2, H * 0.7, (60, 60, 60))
    return reg.img.convert("RGB")


def title():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 34), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 46), fill=(255, 214, 70), anchor="mt",
           stroke_width=2, stroke_fill=(120, 30, 10))
    ship(d, 90, 180, 2.2, "#FFFFFF", "#FFB23C")
    d.text((W / 2, 290), "PUSH START", font=ImageFont.truetype(FONTS + "arialbd.ttf", 20), fill=(255, 255, 255),
           anchor="mm")
    return img


def game():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    rng = random.Random(17)
    for _ in range(36):
        x, y = rng.randrange(W), rng.randrange(H)
        d.rectangle([x, y, x + 2, y + 2], fill=(255, 255, 255))
    ship(d, 70, 170, 1.8, "#FFFFFF", "#FFB23C")
    d.line([(108, 170), (200, 170)], fill=(255, 236, 80), width=4)
    for ax, ay, r in ((240, 160, 28), (284, 260, 16), (206, 66, 12)):
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(140, 96, 70), outline=(90, 60, 44), width=3)
    font = ImageFont.truetype(FONTS + "arialbd.ttf", 18)
    d.text((10, 18), "SCORE 001250", font=font, fill=(255, 255, 255), anchor="lm")
    return img


def greens(img):
    """A picture in the LCD's four greens."""
    g = ImageOps.grayscale(img).point(lambda v: min(3, v * 4 // 256))
    palette = [c for colour in L.GREENS for c in colour] + [0, 0, 0] * 252
    g = g.convert("P")
    g.putpalette(palette)
    return g.convert("RGB")


def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (236, 234, 228))
    art = space((640, 440)).convert("RGB")
    ship(ImageDraw.Draw(art), 220, 240, 3.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 0.0, lw, lh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 6.4, lw / 2, 6.0, (255, 214, 70))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (screen_front(), controls_front(), label()):
        reg.paste(image)
    for name, picture in (("boot", boot()), ("title", title()), ("game", game())):
        x, y, w, h = L.REGIONS[name]
        image.paste(greens(picture).resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(image)
    for name, colour in (("dark", (14, 14, 16)), ("turquoise", TURQUOISE), ("lcd", LCD_OFF), ("cart", CASE),
                         ("black", (8, 8, 10))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "supervision_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
