"""The PlayStation 2's printing, for the console theme's PlayStation 2 model (tools/console-models/ps2.py).

Draws its two atlases, their regions as ps2_layout.py places them, each in millimetres as the model's planar UVs map it.
ps2_print.png: the top seen from above (the PS2 logo and PlayStation 2, turned to read from the back as they do when
it stands, the formats' marks along the front); the upper body's front seen from in front (the memory card slots and
controller ports, MagicGate, the PlayStation mark on the tray's door, the power and eject buttons' legends, SONY up the
end); the base's front (the fan's grille, the blue panel of ports); and the swatches small parts take their colour
from. ps2_disc.png: the DVD's label side (a made-up game, Odyssey) and its silver side. Run it with the system Python
(Pillow):

    python tools/console-models/ps2_print.py <out folder>

It writes ps2_print.png and ps2_disc.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps2_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from psx_print import ps_logo  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region, gradient  # noqa: E402

CASE = rgb(L.COLOURS["case"])
GREY = (120, 122, 132)


def ps2_logo(size):
    """The PS2 logo, upright (letters about size pixels high): P, S and 2 as squared lines graded from pale blue to
    violet, PlayStation 2 under them. Returns an RGBA image."""
    s = size
    w = int(s * 3.6)
    img = Image.new("L", (w, int(s * 1.7)), 0)
    d = ImageDraw.Draw(img)
    lw = max(2, int(s * 0.07))
    gw, gap = s * 0.9, s * 0.25
    for k, letter in enumerate("PS2"):
        x0, y0 = k * (gw + gap) + lw, lw
        x1, y1, ym = x0 + gw, y0 + s, y0 + s / 2
        if letter == "P":
            path = [(x0, y1), (x0, y0), (x1, y0), (x1, ym), (x0 + gw * 0.25, ym)]
        elif letter == "S":
            path = [(x1, y0), (x0, y0), (x0, ym), (x1, ym), (x1, y1), (x0, y1)]
        else:
            path = [(x0, y0), (x1, y0), (x1, ym), (x0, ym), (x0, y1), (x1, y1)]
        d.line(path, fill=255, width=lw, joint="curve")
    colour = gradient((w, img.height), [(0.0, (160, 205, 250)), (0.5, (110, 140, 230)), (1.0, (130, 100, 220))])
    colour.putalpha(img)
    text = Image.new("RGBA", (w, int(s * 0.5)), (0, 0, 0, 0))
    ImageDraw.Draw(text).text((lw, 0), "PlayStation 2", font=ImageFont.truetype(FONTS + "arialbi.ttf", int(s * 0.32)),
                              fill=(14, 14, 16, 255))
    out = Image.new("RGBA", (w, img.height + text.height), (0, 0, 0, 0))
    out.alpha_composite(colour, (0, 0))
    out.alpha_composite(text, (0, int(s * 1.25)))
    return out


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)
    logo = ps2_logo(400).rotate(-90, expand=True)                  # reading from the back, as when it stands
    x0, y0, x1, y1 = reg.box(L.WIDTH / 2 - 35.0, 18.0, L.WIDTH / 2 + 45.0, 18.0 + 80.0 * logo.height / logo.width)
    sized = logo.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS)
    reg.img.alpha_composite(sized, (round(x0), round(y0)))
    for k, mark in enumerate(("COMPACT disc", "DVD", "DVD VIDEO")):
        reg.text(mark, "arialbd.ttf", 3.0, L.WIDTH / 2 + 60.0 + k * 22.0, L.DEPTH - 8.0, shade(CASE, 0.25))
    return reg


def front():
    """The upper body's front, seen from in front: x to the right, z up (from the base's top)."""
    w, z0 = L.WIDTH, L.BASE["height"]
    h = L.HEIGHT - z0
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, L.HEIGHT - z
    for k, x in enumerate((-98.0, -44.0)):
        reg.rect_(*at(x - 23.0, 66.0), *at(x + 23.0, 61.0), (6, 6, 8), r=0.8)       # the memory card slot
        reg.text(str(k + 1), "arial.ttf", 2.6, *at(x, 69.0), GREY)
        reg.text("MEMORY CARD", "arial.ttf", 2.2, *at(x, 58.6), GREY)
        reg.rect_(*at(x - 21.0, 52.0), *at(x + 21.0, 45.0), (8, 8, 10), r=2.5)      # the controller port
        for j in range(9):
            reg.circle(*at(x - 16.0 + j * 4.0 + (1.0 if j > 5 else 0.0) - (1.0 if j < 3 else 0.0), 48.5), 0.9,
                       (40, 40, 44))
    reg.text("MagicGate", "arialbd.ttf", 2.6, *at(-71.0, 69.0), GREY)
    ps_logo(reg, *at(76.0, 43.0), 7.0)
    for name, glyph, colour in (("power", "⏻", (70, 210, 190)), ("eject", "⏏", (90, 140, 255))):
        x, z = L.BUTTONS[name]
        bw, bh, _ = L.BUTTONS["size"]
        reg.rect_(*at(x - bw / 2, z + bh / 2), *at(x + bw / 2, z - bh / 2), shade(CASE, 0.12), r=1.0)
        reg.text(glyph, "seguisym.ttf", 3.6, *at(x, z + 0.8), colour)
        if name == "power":
            reg.text("RESET", "arial.ttf", 1.8, *at(x, z - 2.4), colour)
        lx, lz = L.LIGHTS[name]
        lw, lh = L.LIGHTS["size"]
        lit = (255, 60, 40) if name == "power" else (60, 120, 255)                 # standby red; the tray light blue
        reg.rect_(*at(lx - lw / 2, lz + lh / 2), *at(lx + lw / 2, lz - lh / 2), lit, r=0.4)
    layer = reg.layer()
    font = ImageFont.truetype(FONTS + "timesbd.ttf", round(4.6 * reg.sx))
    text = Image.new("RGBA", (round(30 * reg.sx), round(7 * reg.sx)), (0, 0, 0, 0))
    ImageDraw.Draw(text).text((text.width / 2, text.height / 2), "SONY", font=font, fill=(200, 202, 208, 255),
                              anchor="mm")
    text = text.rotate(-90, expand=True)
    x, y = reg.p(*at(146.5, 58.0))
    layer.alpha_composite(text, (round(x - text.width / 2), round(y - text.height / 2)))
    reg.over(layer)
    return reg


def base():
    """The base's front: x to the right, z up."""
    (x0, x1), h = L.BASE["x"], L.BASE["height"]
    reg = Region(L.REGIONS["base"], x1 - x0, h, shade(CASE, -0.2))

    def at(x, z):
        return x - x0, h - z
    for row in range(5):                                          # the fan's grille
        z = 4.0 + row * 3.2
        x = -98.0
        while x < 108.0:
            reg.rect_(*at(x, z + 2.2), *at(x + 11.0, z), (3, 3, 4))
            x += 13.0
    reg.rect_(*at(-147.0, 19.0), *at(-113.0, 2.0), (46, 92, 200), r=0.8)          # the blue panel of ports
    for z in (5.5, 12.5):
        reg.rect_(*at(-144.0, z + 3.0), *at(-132.0, z - 1.0), (16, 16, 20), r=0.4)
        reg.rect_(*at(-142.5, z + 1.6), *at(-133.5, z + 0.4), (200, 200, 205))
    reg.rect_(*at(-126.0, 16.0), *at(-120.0, 12.0), (16, 16, 20), r=0.4)
    reg.text("USB", "arialbd.ttf", 2.2, *at(-125.0, 6.0), (220, 230, 255))
    return reg


def disc_atlas():
    image = Image.new("RGB", L.DISC_ATLAS, (0, 0, 0))
    size = 2 * L.DISC["r"]
    label = Region(L.DISC_REGIONS["label"], size, size, (0, 0, 0))
    art = space((960, 960))
    d = ImageDraw.Draw(art)
    ship(d, 250, 600, 3.6, "#FFFFFF", "#FFB23C")
    d.text((480, 230), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 120), fill="#FFE45C", anchor="mm",
           stroke_width=6, stroke_fill="#5A1A08")
    d.text((480, 330), "PlayStation 2", font=ImageFont.truetype(FONTS + "arialbi.ttf", 40), fill="#E8E0FF", anchor="mm")
    d.text((480, 770), "SLES-50186", font=ImageFont.truetype(FONTS + "arialbd.ttf", 34), fill="#D8D0F0", anchor="mm")
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 959, 959], fill=255)
    art.putalpha(mask)
    sized = art.resize(label.img.size, Image.LANCZOS)
    label.img.paste(sized, (0, 0), sized)
    c = size / 2
    label.circle(c, c, 22.0, (225, 228, 232))
    label.circle(c, c, 18.0, (190, 194, 200))
    label.circle(c, c, L.DISC["hole"], (30, 30, 32))
    label.paste(image)

    data = Region(L.DISC_REGIONS["data"], size, size, (0, 0, 0))
    data.circle(c, c, c, (196, 200, 210))
    sheen = data.layer()
    ds = ImageDraw.Draw(sheen)
    for k, colour in enumerate(((255, 90, 90), (255, 210, 90), (90, 255, 140), (90, 160, 255), (200, 110, 255))):
        ds.arc(data.box(c - 52 + k * 4, c - 52 + k * 4, c + 52 - k * 4, c + 52 - k * 4), 200, 260,
               fill=colour + (110,), width=round(3 * data.sx))
    data.over(sheen.filter(ImageFilter.GaussianBlur(2 * data.sx)))
    data.circle(c, c, 22.0, (170, 176, 186))
    data.circle(c, c, 17.0, (140, 146, 156))
    data.circle(c, c, L.DISC["hole"], (30, 30, 32))
    data.paste(image)
    return image


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), base()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("green", (60, 255, 110)), ("dark", rgb(L.COLOURS["dark"])), ("blue", (46, 92, 200))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    for name, img in (("ps2_print.png", image), ("ps2_disc.png", disc_atlas())):
        path = os.path.join(out, name)
        img.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1])
