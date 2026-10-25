"""The Neo Geo Pockets' printing and screens, for the console theme's Neo Geo Pocket models
(tools/console-models/neogeo_pocket.py).

Draws one atlas per handheld, its regions as neogeo_pocket_layout.py places them, each in millimetres as the model's
planar UVs map it (the screens in their pixels): the front from in front (the case's colour, the Pocket's carbon dots,
the bezel with the Color's printing and COLOR, the switched-off screen, NEOGEO POCKET, POWER, OPTION, A and B, the
light's ring and its line to POWER, the ring's notches under the stick, the speaker's holes, the arc behind A and B,
SNK); the screens (the start-up logo, the title of a made-up game, Odyssey, and a moment of its play; the Pocket's in its
own four greys); the cartridge's label; and the swatches small parts take their colour from. Run it with the system
Python (Pillow):

    python tools/console-models/neogeo_pocket_print.py <out folder>

It writes ngpc_print.png and ngp_print.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neogeo_pocket_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

ORANGE = (226, 96, 40)
BEZEL = (16, 16, 18)
GREYS = [(44, 48, 42), (92, 98, 88), (142, 148, 136), (190, 196, 182)]   # the Pocket's four, darkest first


def pocket_logo(reg, cx, cy, h, ink):
    """NEOGEO POCKET, h tall, its middle at (cx, cy): the P an orange brush stroke with three dashes over it."""
    f = ImageFont.truetype(FONTS + "arial.ttf", max(1, round(h * reg.sx)))
    left, right = "NEOGEO", "OCKET"
    wl = reg.draw.textlength(left, font=f) / reg.sx
    wr = reg.draw.textlength(right, font=f) / reg.sx
    p = h * 0.9
    total = wl + p + wr
    x = cx - total / 2
    reg.draw.text(reg.p(x, cy), left, font=f, fill=ink, anchor="lm")
    px = x + wl + p * 0.35
    reg.line([(px, cy + h * 0.55), (px, cy - h * 0.55)], ORANGE, h * 0.16)               # the P's stem
    reg.draw.arc(reg.box(px - p * 0.05, cy - h * 0.6, px + p * 0.62, cy + h * 0.05), -100, 120, fill=ORANGE,
                 width=reg.width(h * 0.16))
    for k in range(3):                                                                   # the dashes over it
        a = math.radians(-70 + 25 * k)
        reg.line([(px + p * 0.45 + math.cos(a) * h * 0.55, cy - h * 0.55 + math.sin(a) * h * 0.55),
                  (px + p * 0.45 + math.cos(a) * h * 0.9, cy - h * 0.55 + math.sin(a) * h * 0.9)], ORANGE, h * 0.1)
    reg.draw.text(reg.p(x + wl + p, cy), right, font=f, fill=ink, anchor="lm")


# ---- The front ---------------------------------------------------------------------------------------------------------

def front(kind):
    m = L.MODELS[kind]
    w, h, _ = m["size"]
    case = rgb(m["colours"]["case"])
    reg = Region(L.REGIONS["front"], w, h, case)

    def at(x, z):
        return x + w / 2, h - z
    if m["carbon"]:                                          # the carbon pattern: rows of dots, staggered
        pitch = 1.25
        for j in range(int(h / pitch) + 2):
            for i in range(int(w / pitch) + 2):
                x = i * pitch + (pitch / 2 if j % 2 else 0.0) - w / 2
                reg.circle(*at(x, j * pitch), 0.4, shade(case, -0.35))
    else:                                                    # the Color's pearly sheen, a band across its middle
        sheen = reg.layer()
        ImageDraw.Draw(sheen).polygon([reg.p(*at(-w / 2, h * 0.55)), reg.p(*at(w / 2, h * 0.8)),
                                       reg.p(*at(w / 2, h * 0.6)), reg.p(*at(-w / 2, h * 0.35))],
                                      fill=(255, 255, 255, 18))
        reg.over(sheen)
    ink = m["ink"]
    if not m["carbon"]:                                      # the arc behind A and B
        (ax, az), (bx, bz) = m["a"]["at"], m["b"]["at"]
        mx, mz = (ax + bx) / 2, (az + bz) / 2
        reg.draw.arc(reg.box(*at(mx - 18.0, mz + 18.0), *at(mx + 24.0, mz - 24.0)), 205, 325,
                     fill=shade(case, 0.07), width=reg.width(6.0))
    (bx, bz), (bw, bh) = m["bezel"]["at"], m["bezel"]["size"]
    reg.rect_(*at(bx - bw / 2, bz + bh / 2), *at(bx + bw / 2, bz - bh / 2), BEZEL, r=m["bezel"]["r"])
    (lx, lz), (lw, lh) = m["lcd"]["at"], m["lcd"]["size"]
    reg.rect_(*at(lx - lw / 2 - 2.5, lz + lh / 2 + 2.5), *at(lx + lw / 2 + 2.5, lz - lh / 2 - 2.5), (24, 24, 26))
    reg.rect_(*at(lx - lw / 2, lz + lh / 2), *at(lx + lw / 2, lz - lh / 2), m["lcd_off"])
    if m["color_text"]:
        tx, tz = bx - bw / 2 + 3.0, bz + bh / 2 - 2.6
        reg.text("NEOGEOPOCKET COLOR /Color High Reflective TFT Liquid Crystal Display", "arialbd.ttf", 1.0,
                 *at(tx, tz), (150, 150, 156), anchor="lm")
        reg.text("Display 2.6 inches type / Pixel Format 160 X 152 / Pixel Pitch 0.3 X 0.3mm", "arialbd.ttf", 1.0,
                 *at(tx, tz - 1.4), (150, 150, 156), anchor="lm")
        x = bx + 16.5
        for c in "COLOR":
            reg.text(c, "arialbi.ttf", 3.2, *at(x, tz - 0.8), ORANGE)
            x += 3.3
    lgx, lgz = m["logo"]
    reg.rect_(*at(lgx - 13.0, lgz + 1.9), *at(lgx + 13.0, lgz - 1.9), (8, 8, 9))
    pocket_logo(reg, *at(lgx, lgz), 2.0, (226, 226, 230))

    (px, pz), (pw, ph) = m["power"]["at"], m["power"]["size"]
    reg.rect_(*at(px - pw / 2 - 0.7, pz + ph / 2 + 0.7), *at(px + pw / 2 + 0.7, pz - ph / 2 - 0.7), shade(case, -0.4),
              r=ph / 2 + 0.7)
    reg.text("POWER", "arial.ttf", 2.7, *at(*m["power_label"]), ink)
    (gx, gz), gr = m["light"]["at"], m["light"]["r"]
    reg.line([at(px + pw / 2 + 0.7, pz), at(gx - gr - 0.6, gz)], ink, 0.35)
    reg.circle(*at(gx, gz), gr + 0.6, shade(case, -0.3))
    reg.circle(*at(gx, gz), gr, (70, 20, 16))
    (sx, sz), (r0, r1) = m["stick"]["at"], m["stick"]["ring"]
    reg.circle(*at(sx, sz), r0 + 0.6, shade(case, -0.25))
    for k in range(8):                                        # the ring's notches
        a = math.radians(45 * k + 22.5)
        c, s = math.cos(a), math.sin(a)
        reg.line([at(sx + c * (r0 - 2.0), sz + s * (r0 - 2.0)), at(sx + c * (r0 + 0.5), sz + s * (r0 + 0.5))],
                 shade(case, -0.45), 0.8)
    spx, spz = m["speaker"]
    for j in range(4):
        for i in range(4 if j % 2 == 0 else 3):
            hx = spx - 4.5 + 3.0 * i + (1.5 if j % 2 else 0.0)
            reg.circle(*at(hx, spz + 4.2 - 2.8 * j), 0.65, (10, 10, 11))
    (ox, oz), orr = m["option"]["at"], m["option"]["r"]
    reg.circle(*at(ox, oz), orr + 0.7, shade(case, -0.4))
    reg.text("OPTION", "arial.ttf", 2.7, *at(*m["option_label"]), ink)
    for name in ("a", "b"):
        b = m[name]
        reg.circle(*at(*b["at"]), max(b["r"], b["ring"]) + 0.7, shade(case, -0.45))
        reg.text(name.upper(), "arial.ttf", 3.6, *at(*m[name + "_label"]), ink)
    for x in m["dimples"]["x"]:
        for z in m["dimples"]["z"]:
            reg.circle(*at(x, z), 0.75, shade(case, -0.2))
    snx, snz = m["snk"]
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round(4.6 * reg.sx)))
    reg.draw.text(reg.p(*at(snx + 0.15, snz - 0.15)), "SNK", font=f, fill=shade(case, -0.3), anchor="mm")
    reg.draw.text(reg.p(*at(snx, snz)), "SNK", font=f, fill=shade(case, 0.1), anchor="mm")
    return reg


# ---- The screens -------------------------------------------------------------------------------------------------------

W, H = 320, 304


def boot(colour):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    reg = Region((0, 0, W, H), W, H, (255, 255, 255))
    pocket_logo(reg, W / 2, H * 0.44, 30.0, (30, 30, 34))
    if colour:
        x = W / 2 - 52.0
        for c, ink in zip("COLOR", ((230, 40, 40), (250, 160, 30), (60, 170, 70), (40, 110, 220), (150, 70, 200))):
            reg.text(c, "ariblk.ttf", 22.0, x, H * 0.62, ink)
            x += 26.0
    reg.text("SNK", "ariblk.ttf", 16.0, W / 2, H * 0.84, (40, 40, 160) if colour else (30, 30, 34))
    img.paste(reg.img.convert("RGB").resize((W, H), Image.LANCZOS), (0, 0))
    return img


def title():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 30), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 44), fill=(255, 214, 70), anchor="mt",
           stroke_width=2, stroke_fill=(120, 30, 10))
    ship(d, 90, 170, 2.2, "#FFFFFF", "#FFB23C")
    d.text((W / 2, 276), "PUSH A BUTTON", font=ImageFont.truetype(FONTS + "arialbd.ttf", 18), fill=(255, 255, 255),
           anchor="mm")
    return img


def game():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    rng = random.Random(13)
    for _ in range(36):
        x, y = rng.randrange(W), rng.randrange(H)
        d.rectangle([x, y, x + 1, y + 1], fill=(255, 255, 255))
    ship(d, 70, 160, 1.7, "#FFFFFF", "#FFB23C")
    d.line([(106, 160), (200, 160)], fill=(255, 236, 80), width=3)
    for ax, ay, r in ((240, 150, 26), (285, 240, 15), (200, 60, 12)):
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(140, 96, 70), outline=(90, 60, 44), width=2)
    font = ImageFont.truetype(FONTS + "arialbd.ttf", 15)
    d.text((8, 14), "SCORE 001250", font=font, fill=(255, 255, 255), anchor="lm")
    d.text((W - 8, 14), "x3", font=font, fill=(255, 214, 70), anchor="rm")
    return img


def grey(img):
    """A picture in the Pocket's own four greys."""
    g = ImageOps.grayscale(img).point(lambda v: min(3, v * 4 // 256))
    palette = Image.new("P", (1, 1))
    palette.putpalette([c for colour in GREYS for c in colour] + [0, 0, 0] * 252)
    g = g.convert("P")
    g.putpalette(palette.getpalette())
    return g.convert("RGB")


# ---- The cartridge's label -------------------------------------------------------------------------------------------

def label(kind):
    lw, lh = L.CART_LABEL
    reg = Region(L.REGIONS["cart"], lw, lh, (236, 234, 228))
    art = space((640, 420)).convert("RGB")
    ship(ImageDraw.Draw(art), 210, 230, 3.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(1.5, 7.0, lw - 1.5, lh - 1.5)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 6.5, (20, 20, 24))
    reg.text("ODYSSEY", "ariblk.ttf", 3.8, 11.0, 3.3, (255, 214, 70))
    pocket_logo(reg, lw - 11.0, 3.3, 1.6, (230, 230, 234))
    return reg


def atlas(kind, out):
    m = L.MODELS[kind]
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(m["colours"]["case"]))
    for reg in (front(kind), label(kind)):
        reg.paste(image)
    colour = kind == "ngpc"
    for name, picture in (("boot", boot(colour)), ("title", title()), ("game", game())):
        x, y, w, h = L.REGIONS[name]
        image.paste((picture if colour else grey(picture)).resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(image)
    for name, c in (("red", (255, 50, 40)), ("dark", BEZEL), ("clear", rgb(m["colours"]["ring"])),
                    ("key", rgb(m["colours"]["key"])), ("cart", (40, 40, 44)), ("lit", (255, 70, 40))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=c)
    path = os.path.join(out, f"{kind}_print.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    for kind in L.MODELS:
        atlas(kind, out)


if __name__ == "__main__":
    main(sys.argv[1])
