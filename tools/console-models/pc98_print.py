"""The PC-98 set's printing and screens, for the console theme's PC-98 model (tools/console-models/pc98.py).

Draws its two atlases, their regions as pc98_layout.py places them. pc98_print.png, each in millimetres as the model's
UVs map it: the keyboard from above (each key's top in its grey with its legend, the blank strip, NEC PC-9800 SERIES,
the CAPS and カナ lights' panel), the system unit's front (NEC PC-9801VM and PERSONAL COMPUTER, the brown band, the
grille, the drives' bezels with their slots, lights and numbers, POWER, RESET), the monitor's front (its black bezel,
NEC, the knobs' names, the power light), and the swatches small parts take their colour from. pc98_media.png: the
screens, each the glass's whole area (the start-up memory check; the title of a made-up game, Odyssey; a moment of its
play), and the 5.25-inch floppy's two sides. Run it with the system Python (Pillow):

    python tools/console-models/pc98_print.py <out folder>

It writes pc98_print.png and pc98_media.png there.
"""

import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc98_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
LIGHT_KEY = rgb(L.COLOURS["key_light"])
DARK_KEY = rgb(L.COLOURS["key_dark"])
INK = (64, 64, 70)
BROWN = (110, 86, 70)


def nec(reg, x, y, h, ink):
    """NEC, h tall, its left middle at (x, y)."""
    reg.text("NEC", "timesbi.ttf", h * 1.3, x, y, ink, anchor="lm")


# ---- The keyboard ------------------------------------------------------------------------------------------------------

def keyboard():
    w, d = L.KEYBOARD["width"], L.KEYBOARD["depth"]
    reg = Region(L.REGIONS["keyboard"], w, d, CASE)

    def at(x, s):
        return x + w / 2, d - s
    reg.rect_(*at(-196.0, 172.0), *at(70.0, 154.0), shade(CASE, 0.04), r=1.0)          # the blank strip
    nec(reg, *at(180.0, 167.0), 5.0, (60, 70, 140))
    reg.text("PC-9800 SERIES", "arialbd.ttf", 4.6, *at(210.0, 159.0), (60, 70, 140), anchor="rm")
    reg.rect_(*at(-215.0, 40.0), *at(-182.0, 22.0), (150, 160, 180), r=0.8)             # CAPS and カナ's lights
    reg.text("CAPS", "arial.ttf", 2.2, *at(-206.0, 35.0), (30, 30, 40), anchor="lm")
    reg.text("カナ", "msgothic.ttc", 2.2, *at(-206.0, 28.0), (30, 30, 40), anchor="lm")
    i = L.KEY_INSET
    for name, x_px, w_px, row, legend, *rest in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(x_px, w_px, row, rest[0] if rest else 1)
        fill = DARK_KEY if name in L.DARK_KEYS else LIGHT_KEY
        (ax, ay), (bx, by) = at(x0 + i, s1 - i), at(x1 - i, s0 + i)
        reg.rect_(ax - 0.5, ay - 0.5, bx + 0.5, by + 0.5, shade(fill, 0.05), r=1.2)
        if not legend:
            continue
        ink = (236, 236, 236) if name in L.DARK_KEYS else INK
        cx, cy = (ax + bx) / 2, (ay + by) / 2
        lines = legend.split("\n")
        if len(lines) == 2:
            for k, line in enumerate(lines):
                reg.text(line, "arial.ttf", 2.3, cx, cy - 1.6 + 3.2 * k, ink)
        elif len(legend) == 1:
            font = "seguisym.ttf" if not legend.isascii() else "arial.ttf"
            reg.text(legend, font, 3.6, cx, cy, ink)
        else:
            reg.text(legend, "msgothic.ttc" if not legend.isascii() else "arial.ttf", 2.6, cx, cy, ink)
    return reg


# ---- The system unit's front and the monitor's ---------------------------------------------------------------------

def front():
    w, h = L.WIDTH, L.HEIGHT - L.FEET
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, L.HEIGHT - z
    lx, lz = L.LOGO["at"]
    nec(reg, *at(lx, lz), 6.0, (40, 40, 44))
    reg.line([at(lx + 23.0, lz + 6.0), at(lx + 23.0, lz - 7.0)], (40, 40, 44), 0.6)
    reg.text("PC-9801", "arialbd.ttf", 10.0, *at(lx + 26.0, lz + 1.0), (40, 40, 44), anchor="lm")
    reg.text("PERSONAL COMPUTER", "arialbd.ttf", 2.8, *at(lx + 26.0, lz - 5.6), (40, 40, 44), anchor="lm")
    vm = Image.new("L", (400, 200), 0)                         # VM in striped letters
    ImageDraw.Draw(vm).text((10, 100), "VM", font=ImageFont.truetype(FONTS + "ariblk.ttf", 160), fill=255,
                            anchor="lm")
    vm = vm.crop(vm.getbbox())
    stripes = Image.new("L", vm.size, 0)
    sd = ImageDraw.Draw(stripes)
    for y in range(0, vm.height, 14):
        sd.rectangle([0, y, vm.width, y + 9], fill=255)
    vm = ImageChops.multiply(vm, stripes)
    x0, y0, x1, y1 = reg.box(*at(lx + 78.0, lz + 7.5), *at(lx + 106.0, lz - 7.5))
    vm = vm.resize((max(1, round(x1 - x0)), max(1, round(y1 - y0))), Image.LANCZOS)
    reg.img.paste(Image.new("RGBA", vm.size, (40, 40, 44, 255)), (round(x0), round(y0)), vm)

    (bz0, bz1), (sx0, sx1) = L.BAND["z"], L.BAND["slope_x"]
    gx0 = L.GRILLE["x"][0]
    reg.poly([at(gx0, bz1), at(sx0, bz1), at(sx1, bz1 + 10.0), at(sx1, bz0 + 10.0), at(sx0, bz0), at(gx0, bz0)], BROWN)
    reg.circle(*at(gx0 + 34.0, (bz0 + bz1) / 2), 1.0, (20, 80, 40))       # the power light
    (gx0, gx1), (gz0, gz1), n = L.GRILLE["x"], L.GRILLE["z"], L.GRILLE["slots"]
    for k in range(n):
        z = gz0 + (gz1 - gz0) * (k + 0.5) / n
        reg.rect_(*at(gx0, z + 1.1), *at(gx1, z - 1.1), shade(CASE, -0.3), r=0.8)

    (dx0, dx1) = L.DRIVES["x"]
    for k, (z0, z1) in enumerate(L.DRIVES["z"]):
        reg.rect_(*at(dx0 - 1.0, z1 + 1.0), *at(dx1 + 1.0, z0 - 1.0), shade(CASE, -0.25), r=1.0)
        reg.rect_(*at(dx0, z1), *at(dx1, z0), shade(CASE, 0.03), r=0.8)
        mx = (dx0 + dx1) / 2
        sx0, sx1, sz0, sz1 = L.DRIVES["slot"]
        reg.rect_(*at(mx + sx0, z0 + sz1), *at(mx + sx1, z0 + sz0), (30, 28, 26), r=0.6)
        lxx, lzz = L.DRIVES["light"]
        reg.rect_(*at(mx + lxx - 2.0, z0 + lzz + 1.2), *at(mx + lxx + 2.0, z0 + lzz - 1.2), (90, 20, 16))
        reg.text(str(k + 1), "arial.ttf", 4.0, *at(dx1 + 6.0, (z0 + z1) / 2), INK)
    (px0, px1), (pz0, pz1) = L.POWER["x"], L.POWER["z"]
    reg.rect_(*at(px0 - 1.0, pz1 + 1.0), *at(px1 + 1.0, pz0 - 1.0), shade(CASE, -0.3))
    reg.text("POWER", "arial.ttf", 2.4, *at((px0 + px1) / 2, pz0 - 3.0), INK)
    reg.rect_(*at(-196.0, 14.0), *at(-186.0, 9.0), (70, 66, 60))
    reg.text("RESET", "arial.ttf", 2.2, *at(-191.0, 7.0), INK)
    return reg


def bezel():
    M = L.MONITOR
    w, h = M["width"], M["height"]
    reg = Region(L.REGIONS["bezel"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    reg.rect_(*at(-w / 2 + 10.0, h - 10.0), *at(w / 2 - 10.0, 14.0), (26, 26, 28), r=6.0)
    nec(reg, *at(128.0, 296.0), 7.0, (236, 236, 236))
    reg.text("Color Display", "arial.ttf", 3.0, *at(130.0, 286.0), (200, 200, 200), anchor="lm")
    for (x, z), label in zip(M["knobs"], ("OFF·ON·VOL", "BRIGHT", "CONT")):
        reg.circle(*at(x, z), M["knob_r"] + 1.4, (14, 14, 15))
        reg.text(label, "arial.ttf", 2.6, *at(x, z + M["knob_r"] + 4.0), (210, 210, 210))
    reg.circle(*at(*M["light"]), 1.6, (60, 16, 14))
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (keyboard(), front(), bezel()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", (255, 50, 40)), ("red_off", (90, 20, 16)), ("green", (80, 240, 110)),
                         ("dark", rgb(L.COLOURS["dark"])), ("lever", (206, 200, 186)), ("brown", BROWN)):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "pc98_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -------------------------------------------------------------------------------------------------------

W, H = 640, 400                                      # the PC-98's screen


def memory():
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONTS + "consola.ttf", 18)
    lines = ["NEC PC-9801VM", "", "Memory    640KB  OK", "", "Drive 1:  reading..."]
    for k, line in enumerate(lines):
        d.text((24, 30 + 24 * k), line, font=font, fill=(240, 240, 240))
    d.rectangle([24, 30 + 24 * 6, 34, 30 + 24 * 6 + 16], fill=(240, 240, 240))
    return img


def title():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 40), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 84), fill=(255, 214, 70), anchor="mt",
           stroke_width=3, stroke_fill=(120, 30, 10))
    ship(d, 160, 240, 3.2, "#FFFFFF", "#FFB23C")
    d.text((W / 2, 360), "PUSH RETURN KEY", font=ImageFont.truetype(FONTS + "arialbd.ttf", 26), fill=(255, 255, 255),
           anchor="mm")
    return img


def game():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    rng = random.Random(19)
    for _ in range(50):
        x, y = rng.randrange(W), rng.randrange(H)
        d.rectangle([x, y, x + 2, y + 2], fill=(255, 255, 255))
    ship(d, 140, 210, 2.6, "#FFFFFF", "#FFB23C")
    d.line([(196, 210), (380, 210)], fill=(255, 236, 80), width=5)
    for ax, ay, r in ((470, 200, 44), (560, 320, 26), (420, 80, 20)):
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(140, 96, 70), outline=(90, 60, 44), width=3)
    font = ImageFont.truetype(FONTS + "consolab.ttf", 22)
    d.text((16, 20), "SCORE 001250", font=font, fill=(255, 255, 255), anchor="lm")
    d.text((W - 16, 20), "SHIP x3", font=font, fill=(255, 214, 70), anchor="rm")
    return img


def glass(picture):
    """A screen's region: the 640 x 400 raster (16:10) in the middle of the 4:3 tube's dark border."""
    w, h = L.SCREEN_PX
    image = Image.new("RGB", (w, h), (12, 12, 14))
    rw = round(w * 0.86)
    rh = round(rw * 400 / 640)
    image.paste(picture.resize((rw, rh), Image.LANCZOS), ((w - rw) // 2, (h - rh) // 2))
    return image


def disk_side(rect, label):
    """One side of the 5.25-inch floppy, seen looking at it, the end that goes in first at the top."""
    s = L.DISK["size"]
    jacket = (26, 26, 30)
    reg = Region(rect, s, s, jacket)
    reg.circle(s / 2, s / 2, 19.0, (60, 56, 50))                            # the hub's ring, its hole
    reg.circle(s / 2, s / 2, 14.0, (12, 12, 14))
    reg.rect_(s / 2 - 6.0, 6.0, s / 2 + 6.0, 40.0, (60, 56, 50), r=6.0)    # the read window, towards the drive
    reg.circle(s / 2 + 25.0, s / 2 - 8.0, 2.0, (12, 12, 14))               # the index hole
    if label:
        reg.rect_(10.0, s - 52.0, s - 10.0, s - 8.0, (240, 238, 228), r=1.0)
        art = space((640, 200)).convert("RGB")
        ship(ImageDraw.Draw(art), 160, 110, 2.6, "#FFFFFF", "#FFB23C")
        x0, y0, x1, y1 = reg.box(12.0, s - 46.0, s - 12.0, s - 10.0)
        reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
        reg.text("ODYSSEY", "ariblk.ttf", 7.0, s / 2, s - 40.0, (255, 214, 70))
        reg.text("PC-9801  DISK A", "arialbd.ttf", 3.6, s / 2, s - 15.0, (230, 230, 236))
    return reg


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (12, 12, 14))
    for name, picture in (("memory", memory()), ("title", title()), ("game", game())):
        x, y, _, _ = L.MEDIA_REGIONS[name]
        image.paste(glass(picture), (x, y))
    disk_side(L.MEDIA_REGIONS["disk_top"], True).paste(image)
    disk_side(L.MEDIA_REGIONS["disk_bottom"], False).paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", (12, 12, 14)), ("edge", (26, 26, 30))):
        x, y = L.MEDIA_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "pc98_media.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
