"""The Sega 32X's printing (sega32x_print.png), for the console theme's model (sega32x.py).

One image, laid out as sega32x_layout.REGIONS says: the badge on the slope (the European one: its silver outline,
MEGA DRIVE, 32X and the SEGA tab), the vents' slits on the ends, the flaps' ribbed ends, the cartridge's label (a
made-up game, Odyssey: its art, the yellow corner marks, the MEGA DRIVE 32X band with the SEGA tab), and swatches; the
case's colour round them. Run it with the system Python (Pillow):

    python tools/console-models/sega32x_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sega32x_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
SHELL = rgb(L.COLOURS["shell"])
SILVER = (214, 217, 222)
WHITE = (240, 240, 242)
YELLOW = (255, 214, 70)
BLUE = (64, 112, 236)


def fitted(reg, text, font, x0, y0, x1, y1, fill, shear=0.0, variation=None, stroke=None):
    """text stretched to fill the box (x0, y0)-(x1, y1), its tops leaning right by shear (of its height); stroke, if
    given, is (width in mm, colour) round its letters."""
    f = ImageFont.truetype(FONTS + font, 200)
    if variation:
        f.set_variation_by_name(variation)
    sw = round(stroke[0] * 200 / max(1e-6, y1 - y0)) if stroke else 0
    size = (round(f.getlength(text)) + 80 + 2 * sw, 320 + 2 * sw)
    masks = []
    for width in ((sw, 0) if stroke else (0,)):
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).text((40 + sw, 160 + sw), text, font=f, fill=255, anchor="lm", stroke_width=width,
                                  stroke_fill=255)
        masks.append(mask)
    box = masks[0].getbbox()
    a, b, c, e = reg.box(x0, y0, x1, y1)
    w, h = max(1, round(c - a)), max(1, round(e - b))
    lean = round(abs(shear) * h)
    for mask, colour in zip(masks, ((stroke[1], fill) if stroke else (fill,))):
        m = mask.crop(box).resize((w - lean, h), Image.LANCZOS)
        if shear:
            wide = Image.new("L", (w, h), 0)
            wide.paste(m, (0, 0))
            m = wide.transform((w, h), Image.AFFINE, (1, shear, -shear * h, 0, 1, 0), resample=Image.BICUBIC)
        reg.img.paste(Image.new("RGBA", m.size, tuple(colour) + (255,)), (round(a), round(b)), m)


# ---- The badge -------------------------------------------------------------------------------------------------------

def badge():
    """The slope round the badge, seen along its normal: x across BADGE_AREA's u, down from its top v."""
    (u0, u1), (v0, v1) = L.BADGE_AREA["u"], L.BADGE_AREA["v"]
    reg = Region(L.REGIONS["badge"], u1 - u0, v1 - v0, SHELL)
    bx, bv = L.BADGE["at"]
    bw, bh = L.BADGE["size"]
    tip, bottom, (tab_top, tab_h) = L.BADGE["tip"], L.BADGE["bottom"], L.BADGE["tab"]

    def at(u, w):
        """The badge's own (u across from its middle, w up from its bottom), as fractions of its half width and its
        height, in the region's units."""
        return (bx + u * bw / 2 - u0, v1 - (bv - bh / 2 + w * bh))

    # The outline: the top an arc through the tips and the top's middle, the lower edges in to the flat bottom.
    half = bw / 2
    centre = (bh ** 2 - tip ** 2 - half ** 2) / (2 * (bh - tip))        # the arc's centre, w in millimetres
    r = bh - centre
    a0 = math.degrees(math.atan2(tip - centre, half))
    outline = [at(r * math.cos(math.radians(a)) / half, (centre + r * math.sin(math.radians(a))) / bh)
               for a in [a0 + (180 - 2 * a0) * k / 40 for k in range(41)]]
    outline += [at(-bottom / half, 0.0), at(bottom / half, 0.0)]

    # Its face: a dark warm grey, darker towards the bottom, inside a silver line.
    layer = reg.layer()
    face = Image.new("RGBA", layer.size)
    fd = ImageDraw.Draw(face)
    _, top_y = reg.p(*at(0.0, bh))
    _, bottom_y = reg.p(*at(0.0, 0.0))
    for y in range(layer.size[1]):
        t = min(1.0, max(0.0, (y - top_y) / max(1.0, bottom_y - top_y)))
        fd.line([(0, y), (layer.size[0], y)], fill=(round(66 - 46 * t), round(60 - 41 * t), round(56 - 37 * t), 255))
    mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(mask).polygon([reg.p(x, y) for x, y in outline], fill=255)
    layer.paste(face, (0, 0), mask)
    reg.over(layer)
    reg.line(outline + outline[:1], SILVER, 1.0)

    # The SEGA tab: a dark trapezoid in a silver line, standing on the badge's bottom.
    tab = [at(-tab_top / half, tab_h / bh), at(tab_top / half, tab_h / bh), at(bottom / half, 0.0),
           at(-bottom / half, 0.0)]
    reg.poly(tab, (16, 16, 18))
    reg.line(tab + tab[:1], SILVER, 0.8)
    x0, y0 = at(-0.21, 0.24)
    x1, y1 = at(0.21, 0.074)
    fitted(reg, "SEGA", "ariblk.ttf", x0, y0, x1, y1, WHITE, shear=0.12)

    # MEGA DRIVE over 32X, leaning like the Mega Drive's own.
    x0, y0 = at(-0.5, 0.84)
    x1, y1 = at(0.5, 0.705)
    fitted(reg, "MEGA DRIVE", "bahnschrift.ttf", x0, y0, x1, y1, WHITE, shear=0.3, variation="Bold")
    x0, y0 = at(-0.443, 0.674)
    x1, y1 = at(0.513, 0.379)
    fitted(reg, "32X", "ariblk.ttf", x0, y0, x1, y1, WHITE, shear=0.22, stroke=(0.5, (24, 22, 22)))
    return reg


# ---- The vents and the flaps -----------------------------------------------------------------------------------------

def vents():
    """An end seen along x: y across (-40 to 40), z up (60 at the top)."""
    reg = Region(L.REGIONS["vents"], 80.0, 50.0, SHELL)
    (y0, y1), n, (z0, z1) = L.VENTS["y"], L.VENTS["count"], L.VENTS["z"]
    for k in range(n):
        y = y0 + (y1 - y0) * k / (n - 1)
        reg.rect_(y + 40.0 - 1.1, 60.0 - z1, y + 40.0 + 1.1, 60.0 - z0, rgb(L.COLOURS["slot"]), r=1.1)
    return reg


def flap():
    """A flap's top: its length across, its width down; the ribs at its ends."""
    length, width = L.FLAP["length"], L.FLAP["width"]
    reg = Region(L.REGIONS["flap"], length, width, rgb(L.COLOURS["flap"]))
    for end in (0.0, length):
        for k in range(4):
            x = 3.5 + 4.6 * k if end == 0.0 else length - 3.5 - 4.6 * k
            reg.rect_(x - 0.7, 0.0, x + 0.7, width, (70, 71, 75))
            reg.rect_(x + 0.7, 0.0, x + 1.2, width, (18, 18, 20))
        x = 21.0 if end == 0.0 else length - 21.0
        reg.rect_(x - 0.4, 0.0, x + 0.4, width, (16, 16, 18))
    return reg


# ---- The cartridge's label -------------------------------------------------------------------------------------------

def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (14, 14, 18))
    art = space((800, 460)).convert("RGB")
    ship(ImageDraw.Draw(art), 260, 210, 3.6, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 0.0, lw, lh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))

    # The frame, its yellow corner marks, the game's name.
    border = 1.4
    for x0, y0, x1, y1 in ((0, 0, lw, border), (0, lh - border, lw, lh), (0, 0, border, lh), (lw - border, 0, lw, lh)):
        reg.rect_(x0, y0, x1, y1, (12, 12, 16))
    arm, t, inset = 7.0, 0.7, 2.2
    for sx, sy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        cx = inset if sx == 0 else lw - inset
        cy = inset if sy == 0 else lh - 13.6
        dx, dy = (1, 1) if (sx, sy) == (0, 0) else (-1, 1) if sy == 0 else (1, -1) if sx == 0 else (-1, -1)
        reg.rect_(min(cx, cx + dx * arm), min(cy, cy + dy * t), max(cx, cx + dx * arm), max(cy, cy + dy * t), YELLOW)
        reg.rect_(min(cx, cx + dx * t), min(cy, cy + dy * arm), max(cx, cx + dx * t), max(cy, cy + dy * arm), YELLOW)
    fitted(reg, "ODYSSEY", "ariblk.ttf", 33.0, 4.6, 74.0, 11.0, YELLOW, stroke=(0.5, (40, 18, 60)))

    # The band: MEGA DRIVE over a blue 32X, the SEGA tab at its left.
    reg.rect_(0.0, lh - 12.0, lw, lh, (10, 10, 14))
    reg.rect_(0.0, lh - 12.0, lw, lh - 11.6, SILVER)
    reg.rect_(2.4, lh - 11.0, 8.4, lh - 1.2, (28, 46, 150))
    layer = Image.new("RGBA", (400, 120), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((200, 60), "SEGA", font=ImageFont.truetype(FONTS + "ariblk.ttf", 90),
                                fill=WHITE + (255,), anchor="mm")
    layer = layer.crop(layer.getbbox()).rotate(90, expand=True)
    a, b, c, e = reg.box(3.6, lh - 10.0, 7.2, lh - 2.2)
    reg.img.alpha_composite(layer.resize((round(c - a), round(e - b)), Image.LANCZOS), (round(a), round(b)))
    fitted(reg, "MEGA DRIVE", "bahnschrift.ttf", 11.0, lh - 10.6, 62.0, lh - 6.4, WHITE, shear=0.3, variation="Bold",
           stroke=(0.3, (90, 96, 110)))
    fitted(reg, "32X", "ariblk.ttf", 40.0, lh - 6.0, 62.0, lh - 1.0, BLUE, shear=0.22, stroke=(0.3, (220, 228, 255)))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (badge(), vents(), flap(), label()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=rgb(L.COLOURS[name]))
    path = os.path.join(out, "sega32x_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
