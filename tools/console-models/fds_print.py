"""The Famicom Disk System's printing, for the console theme's Famicom Disk System model (tools/console-models/fds.py).

Draws its atlas, its regions as fds_layout.py places them, each in millimetres as the model's planar UVs map it: the
set seen from above (the Famicom's front deck with POWER, EJECT and RESET and the warnings beside them, the RAM
adapter's top with Nintendo's badge, FAMILY COMPUTER DISK SYSTEM and HVC-023, its grooves); the Famicom's front slope
(FAMILY COMPUTER on the red band); the drive's front (Nintendo HVC-022 FAMILY COMPUTER DISK SYSTEM, the grooved ends,
the operating lamp's box, イジェクト); the two controllers' faces (the gold plates, the D-pads, SELECT and START on I,
VOLUME and the microphone on II, B and A); the disk card's two sides (a made-up game, Odyssey, side A and side B);
and the swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/fds_print.py <out folder>

It writes fds_print.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fds_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

RED = rgb(L.COLOURS["red"])
WHITE = rgb(L.COLOURS["white"])
DARK = rgb(L.COLOURS["dark"])
YELLOW = rgb(L.COLOURS["yellow"])
GOLD = (196, 168, 112)
GOLD_TEXT = (218, 196, 140)
TOP_DEPTH = 250.0           # the top region's depth: the drive's front to the adapter's back
JP = "msgothic.ttc"


def slanted(reg, text, font, size, x, y, fill, shear=0.22, anchor="mm"):
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(x, y), text, font=f, fill=fill + (255,), anchor=anchor)
    yc = reg.p(0, y)[1]
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, shear, -shear * yc, 0, 1, 0)))


def nintendo(reg, x, y, size, fill, box=None):
    """Nintendo's name in its racetrack outline (or on a filled one, box)."""
    w, h = size * 3.6, size * 1.25
    if box is not None:
        reg.rect_(x - w / 2, y - h / 2, x + w / 2, y + h / 2, box, r=h / 2)
    reg.rect_(x - w / 2, y - h / 2, x + w / 2, y + h / 2, None, r=h / 2, outline=fill, width=size * 0.09)
    reg.text("Nintendo", "arialbd.ttf", size * 0.82, x, y + size * 0.03, fill)


# ---- The set from above ------------------------------------------------------------------------------------------------

def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, TOP_DEPTH, RED)
    fy = L.FAMICOM["y"]

    def at(x, y):
        """A point of the Famicom (x, y from its front) in the region's millimetres."""
        return x + L.WIDTH / 2, TOP_DEPTH - (y + fy)
    reg.rect_(*at(-74.0, 220.0), *at(74.0, 0.0), WHITE)
    grey = shade(WHITE, -0.22)
    for x, y, words in ((-33.0, 52.0, "POWER"), (37.0, 42.0, "RESET")):
        reg.rect_(*at(x - 15.0, y + 11.0), *at(x + 15.0, y - 11.0), shade(WHITE, -0.04), r=1.0)
        reg.text(words, "arialbd.ttf", 2.4, *at(x - 14.0 if x < 0 else x + 14.0, y + 13.0), grey,
                 anchor="lm" if x < 0 else "rm")
    reg.text("EJECT", "arialbd.ttf", 2.4, *at(0.0, 50.0), grey)
    for x, y, lines in ((-32.0, 80.0, ("●カセットを抜き", "差しする時は、", "必ず本体の電源を", "切ってください。")),
                        (36.0, 70.0, ("●リセットスイッチ", "を押すと、それまで", "記憶されていた", "得点が消去されます。"))):
        reg.rect_(*at(x - 13.0, y + 12.0), *at(x + 13.0, y - 8.0), WHITE, outline=(80, 80, 80), width=0.25)
        for k, line in enumerate(lines):
            reg.text(line, JP, 2.2, *at(x - 12.0, y + 9.5 - 3.0 * k), (60, 60, 60), anchor="lm")
        ax, ay = at(x, y - 12.0)
        reg.poly([(ax - 4.0, ay - 2.0), (ax + 4.0, ay - 2.0), (ax, ay + 2.5)], (120, 120, 120))
        reg.poly([(ax - 2.6, ay - 1.4), (ax + 2.6, ay - 1.4), (ax, ay + 1.4)], WHITE)

    # The RAM adapter: black, its grooves at each end, Nintendo's badge, its names.
    (ax0, ax1), (ay0, ay1) = L.ADAPTER["x"], L.ADAPTER["y"]
    reg.rect_(*at(ax0, ay1), *at(ax1, ay0), DARK)
    for k in range(L.ADAPTER["grooves"]):
        for y in (ay0 + 5.0 + 3.0 * k, ay1 - 5.0 - 3.0 * k):
            reg.line([at(ax0 + 2.0, y), at(ax1 - 2.0, y)], (44, 44, 48), 0.9)
    reg.rect_(*at(8.0, 182.0), *at(52.0, 170.0), (230, 230, 230))
    reg.text("Nintendo", "arialbd.ttf", 6.4, *at(30.0, 176.0), DARK)
    slanted(reg, "FAMILY COMPUTER  DISK  SYSTEM", "arial.ttf", 2.6, *at(16.0, 160.0), (220, 220, 222), shear=0.0)
    reg.rect_(*at(30.0, 154.5), *at(52.0, 149.5), (220, 220, 222))
    reg.text("HVC-023", "arialbd.ttf", 3.4, *at(41.0, 152.0), DARK)
    return reg


def band():
    length = L.slope_length()
    reg = Region(L.REGIONS["band"], L.WIDTH, length, WHITE)
    # The band runs up the slope: b from the slope's top (0) down to its foot (length).
    reg.rect_(0.0, length * 0.32, L.WIDTH - 22.0, length * 0.92, RED)
    for y in (length * 0.2, length * 0.96):
        reg.line([(6.0, y), (L.WIDTH - 2.0, y)], GOLD_TEXT, 0.5)
    slanted(reg, "FAMILY COMPUTER", "arialbd.ttf", 10.0, 70.0, length * 0.6, GOLD_TEXT, shear=0.24)
    reg.text("™", "arial.ttf", 4.0, 118.0, length * 0.42, GOLD_TEXT)
    slanted(reg, "Nintendo®", "arialbd.ttf", 4.0, 122.0, length * 0.82, GOLD_TEXT, shear=0.2)
    return reg


def drive():
    reg = Region(L.REGIONS["drive"], L.WIDTH, L.DRIVE["height"], RED)

    def at(x, z):
        return x + L.WIDTH / 2, L.DRIVE["height"] - z
    (px0, px1), (pz0, pz1) = L.PANEL["x"], L.PANEL["z"]
    reg.rect_(*at(px0, pz1), *at(px1, pz0), DARK)
    for x0, x1, z0, z1 in ((px0, px0 + 10.0, pz0, pz1), (px1 - 22.0, px1, pz0, pz0 + 18.0)):
        for k in range(int((z1 - z0) / 2.4)):                 # the grooved ends
            z = z0 + 1.2 + 2.4 * k
            reg.line([at(x0 + 1.0, z), at(x1 - 1.0, z)], (40, 40, 44), 0.9)
    lx, lz, _ = L.LAMP
    reg.rect_(*at(px1 - 22.0, lz + 8.0), *at(px1 - 1.0, lz - 6.0), (20, 20, 22), outline=(44, 44, 48), width=0.4)
    reg.circle(*at(lx, lz), L.LAMP[2], (70, 16, 16))
    reg.text("◀作動中", JP, 3.0, *at(lx + 3.0, lz), (220, 220, 220), anchor="lm")
    reg.text("Nintendo", "arialbd.ttf", 5.4, *at(-48.0, 30.0), (240, 240, 240), anchor="lm")
    reg.rect_(*at(-48.0, 25.0), *at(-31.0, 20.6), (240, 240, 240))
    reg.text("HVC-022", "arialbd.ttf", 3.6, *at(-39.5, 22.8), DARK)
    reg.text("FAMILY COMPUTER  DISK  SYSTEM", "arial.ttf", 2.8, *at(-28.0, 14.0), (230, 230, 230), anchor="lm")
    reg.text("イジェクト", JP, 2.6, *at(17.5, 26.0), (230, 230, 230))
    return reg


# ---- The controllers ---------------------------------------------------------------------------------------------------

PAD_W, PAD_H = 128.0, 50.0


def pad_face(region, number):
    """A controller's face, its cable's end to the left: the red border, the gold plate, the D-pad, the buttons."""
    reg = Region(region, PAD_W, PAD_H, RED)
    reg.rect_(4.0, 13.0 if number == 1 else 4.0, PAD_W - 4.0, PAD_H - 4.0, GOLD)
    if number == 1:
        reg.rect_(4.0, 4.0, 52.0, 13.0, GOLD)
    for y in (PAD_H - 9.0, PAD_H - 7.6):
        reg.line([(6.0, y), (PAD_W - 6.0, y)], (120, 30, 30), 0.35)
    reg.rect_(8.0, 7.0 if number == 2 else 15.0, 14.0, 13.0 if number == 2 else 21.0, DARK)
    reg.text("I" if number == 1 else "II", "timesbd.ttf", 4.2, 11.0, 10.0 if number == 2 else 18.0, GOLD)
    cx, cy, s, a = 22.0, 33.0, 20.0, 6.5                   # the D-pad: its middle, its span, its arm
    reg.rect_(cx - a / 2, cy - s / 2, cx + a / 2, cy + s / 2, (24, 24, 26), r=0.8)
    reg.rect_(cx - s / 2, cy - a / 2, cx + s / 2, cy + a / 2, (24, 24, 26), r=0.8)
    reg.circle(cx, cy, 1.2, (44, 44, 48))
    if number == 1:
        reg.rect_(44.0, 28.0, 76.0, 38.0, RED, r=5.0)
        for x in (52.0, 68.0):
            reg.rect_(x - 5.0, 31.5, x + 5.0, 34.5, (24, 24, 26), r=1.5)
        reg.text("SELECT", "arialbd.ttf", 2.4, 52.0, 25.0, (60, 30, 30))
        reg.text("START", "arialbd.ttf", 2.4, 68.0, 25.0, (60, 30, 30))
    else:
        reg.rect_(32.0, 20.0, 44.0, 22.4, (30, 30, 32))
        reg.rect_(32.5, 19.0, 35.5, 23.4, (60, 60, 64))
        reg.poly([(46.0, 25.0), (56.0, 19.5), (56.0, 25.0)], (60, 30, 30))
        reg.text("VOLUME", "arialbd.ttf", 2.2, 60.0, 22.0, (60, 30, 30), anchor="lm")
        reg.rect_(72.0, 6.0, 92.0, 20.0, RED, r=1.0)
        for i in range(6):
            for j in range(4):
                reg.circle(74.2 + 3.1 * i, 8.2 + 3.2 * j, 0.6, shade(RED, -0.4))
        reg.text("MIC.", "arialbd.ttf", 2.2, 82.0, 24.0, (60, 30, 30))
    for x, name in ((98.0, "B"), (114.0, "A")):
        reg.circle(x, 34.0, 6.2, (40, 20, 20))
        reg.circle(x, 34.0, 5.2, (24, 24, 26))
        reg.circle(x - 1.5, 32.5, 1.6, (70, 70, 74))
        reg.rect_(x - 2.4, 22.0, x + 2.4, 26.4, RED, r=1.0)
        reg.text(name, "arialbd.ttf", 3.2, x, 24.2, GOLD_TEXT)
    return reg


# ---- The disk card -----------------------------------------------------------------------------------------------------

def disk_side(region, side):
    """One side of the disk card, its window's end at the top: the yellow shell, the window, the hub, the label (side
    A's or B's), NINTENDO raised along its foot."""
    w, h = L.DISK["size"]
    reg = Region(region, w, h, YELLOW)
    reg.rect_(1.0, 1.0, w - 1.0, h - 1.0, shade(YELLOW, 0.05), r=1.5)
    reg.rect_(w / 2 - 4.5, 6.0, w / 2 + 3.0, 30.0, (110, 104, 92))       # the window, the disk showing
    reg.circle(w / 2, 40.0, 7.5, (90, 86, 80))
    reg.circle(w / 2, 40.0, 6.2, (232, 228, 218))
    reg.circle(w / 2, 40.0, 1.6, (180, 176, 168))
    reg.rect_(6.0, 50.0, w - 6.0, h - 13.0, (250, 248, 240), r=1.0)
    art = space((560, 220))
    d = ImageDraw.Draw(art)
    ship(d, 160, 120, 2.4, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(7.0, 51.0, w - 7.0, h - 20.0)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text("ODYSSEY", "ariblk.ttf", 6.2, w / 2, 56.5, (255, 214, 70))
    reg.rect_(6.0, h - 20.0, w - 6.0, h - 13.0, (206, 34, 40))
    reg.text(f"SIDE {side}", "arialbd.ttf", 4.6, w / 2, h - 16.5, (255, 250, 236))
    reg.rect_(8.0, 9.0, 16.0, 17.0, (206, 34, 40) if side == "A" else (36, 80, 190), r=1.0)
    reg.text(side, "arialbd.ttf", 5.2, 12.0, 13.2, (255, 255, 255))
    for (dx, dy), colour in (((-0.3, -0.3), shade(YELLOW, 0.25)), ((0.4, 0.4), shade(YELLOW, -0.25)),
                             ((0.0, 0.0), shade(YELLOW, 0.02))):
        reg.text("NINTENDO", "ariblk.ttf", 7.2, w / 2 + dx, h - 6.0 + dy, colour)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), RED)
    for reg in (top(), band(), drive(), pad_face(L.REGIONS["pad1"], 1), pad_face(L.REGIONS["pad2"], 2),
                disk_side(L.REGIONS["side_a"], "A"), disk_side(L.REGIONS["side_b"], "B")):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", RED), ("white", WHITE), ("dark", DARK), ("base", rgb(L.COLOURS["base"])),
                         ("yellow", YELLOW), ("lit", (255, 40, 30)), ("lamp_off", (70, 16, 16)), ("gold", GOLD)):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "fds_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
