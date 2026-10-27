"""The Uzebox card's printing (uzebox_print.png), for the console theme's Uzebox model (uzebox.py).

One image, laid out as uzebox_layout.REGIONS says, each region in millimetres as the model's UVs map it: the board from
above (its red solder mask, darker traces and vias, gold pads and mounting holes, the white silk screen: SNES P1 and P2,
LED1, RESET, POWER, MCU, IC3, EXT and its pins' names, 7-12VDC, VIDEO, AUDIO, ISP, MIDI IN, Uzebox V1.2 and the
UZEBOX logo in outline letters; the small ceramic capacitors and the diode, too small to build), the SD card's label, the
pad from above (the D-pad's well, the dish round A B X Y and their letters, SELECT and START: unbranded), and swatches.
Run it with the system Python (Pillow):

    python tools/console-models/uzebox_print.py <out folder>
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uzebox_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
SILK = C["silk"]


def rotated_text(reg, text, font, size, x, y, fill, angle):
    """Text turned angle degrees anticlockwise, its middle at (x, y)."""
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    l, t, r, b = f.getbbox(text)
    tile = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((4 - l, 4 - t), text, font=f, fill=fill)
    tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    px, py = reg.p(x, y)
    reg.img.alpha_composite(tile, (round(px - tile.width / 2), round(py - tile.height / 2)))


def board():
    reg = Region(L.REGIONS["board"], L.WIDTH, L.DEPTH, C["board"])

    def at(x, y):
        return x + L.HALF, L.DEPTH - y

    rnd = random.Random(1291)
    trace = shade(C["board"], -0.12)
    for _ in range(46):                                    # traces: runs along x and y, turning once
        x0, y0 = rnd.uniform(-46, 46), rnd.uniform(4, 77)
        x1, y1 = x0 + rnd.uniform(-30, 30), y0 + rnd.uniform(-25, 25)
        reg.line([at(x0, y0), at(x1, y0), at(x1, max(3.0, min(78.0, y1)))], trace, 0.5)
    for _ in range(28):
        reg.circle(*at(rnd.uniform(-46, 46), rnd.uniform(4, 77)), 0.5, shade(C["board"], -0.3))
    for x, y in L.STANDOFF["at"]:                          # the mounting holes
        reg.circle(*at(x, y), 3.0, C["gold"])
        reg.circle(*at(x, y), 1.7, (30, 20, 18))
    for x0, x1 in (L.PORTS["p1"], L.PORTS["p2"]):          # the ports' pins' pads
        for k in range(7):
            reg.circle(*at(x0 + 3.0 + (x1 - x0 - 6.0) * k / 6, 3.4), 1.0, C["gold"])
    x0, x1, y0, y1, _ = L.MCU
    for k in range(20):                                    # the MCU's pads, showing past its ends
        for y in (y0 - 1.2, y1 + 1.2):
            reg.circle(*at(x0 + 1.5 + k * 2.54, y), 0.7, C["gold"])
    # The silk screen.
    reg.text("SNES  P1", "arialbd.ttf", 2.2, *at(sum(L.PORTS["p1"]) / 2, 6.6), SILK)
    reg.text("SNES  P2", "arialbd.ttf", 2.2, *at(sum(L.PORTS["p2"]) / 2, 6.6), SILK)
    reg.text("LED1", "arialbd.ttf", 2.0, *at(L.LED["at"][0], 7.2), SILK)
    for name in ("reset", "power"):
        x, y = L.BUTTONS[name]
        reg.text(name.upper(), "arialbd.ttf", 2.2, *at(x, y + 5.2), SILK)
        reg.rect_(*at(x - 4.0, y + 4.0), *at(x + 4.0, y - 4.0), None, outline=SILK, width=0.3)
    rotated_text(reg, "MCU", "arialbd.ttf", 2.6, *at(x0 - 2.6, (y0 + y1) / 2), SILK, 90)
    reg.rect_(*at(x0 - 1.0, y1 + 2.4), *at(x1 + 1.0, y0 - 2.4), None, outline=SILK, width=0.3)
    reg.rect_(*at(25.5, 29.0), *at(32.0, 25.0), None, outline=SILK, width=0.3)
    reg.text("IC3", "arialbd.ttf", 2.0, *at(28.75, 27.0), SILK)
    ex0, ex1 = L.EXT["x"]
    ey0, ey1 = L.EXT["y"]
    reg.text("1  EXT", "arialbd.ttf", 2.0, *at((ex0 + ex1) / 2, ey1 + 2.0), SILK)
    for k, (left, right) in enumerate(zip(("VCC", "PD5", "PD3", "PA7", "PA6", "PA5", "PA4", "GND"),
                                          ("PB2", "PB1", "TX", "RX", "RESET", "SCK", "MOSI", "MISO"))):
        y = ey0 + 1.3 + 2.54 * k
        reg.text(left, "arialbd.ttf", 1.5, *at(ex0 - 0.8, y), SILK, anchor="rm")
        reg.text(right, "arialbd.ttf", 1.5, *at(ex1 + 0.8, y), SILK, anchor="lm")
        for x in (ex0 + 1.3, ex1 - 1.3):
            reg.circle(*at(x, y), 0.6, C["gold"])
    rotated_text(reg, "7-12VDC", "arialbd.ttf", 1.8, *at(-48.6, 72.0), SILK, 90)
    reg.text("VIDEO", "arialbd.ttf", 1.6, *at(sum(L.RCA["video"][:2]) / 2, 66.4), SILK)
    reg.text("AUDIO", "arialbd.ttf", 1.6, *at(sum(L.RCA["audio"][:2]) / 2, 66.4), SILK)
    reg.text("ISP", "arialbd.ttf", 1.8, *at(10.9, 71.6), SILK)
    reg.rect_(*at(36.0, 40.0), *at(48.0, 22.0), None, outline=SILK, width=0.3)
    rotated_text(reg, "MIDI IN", "arialbd.ttf", 2.0, *at(46.0, 31.0), SILK, 90)
    for k in range(5):
        reg.circle(*at(39.0 + (k % 2) * 3.0, 24.0 + 3.6 * k), 0.8, C["gold"])
    rotated_text(reg, "Uzebox V1.2", "arialbd.ttf", 2.6, *at(46.6, 16.0), SILK, 90)
    rotated_text(reg, "http://uzebox.org", "arial.ttf", 1.8, *at(48.6, 16.0), SILK, 90)
    reg.text("Y70129", "arialbd.ttf", 1.6, *at(39.0, 9.8), SILK)
    f = ImageFont.truetype(FONTS + "ariblk.ttf", round(6.6 * reg.sx))
    logo = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    ImageDraw.Draw(logo).text(reg.p(*at(-0.5, 11.4)), "UZEBOX", font=f, fill=C["board"] + (255,), anchor="mm",
                              stroke_width=max(1, round(0.35 * reg.sx)), stroke_fill=SILK + (255,))
    lean = 0.25
    yc = reg.p(0, 11.4)[1]
    reg.over(logo.transform(logo.size, Image.AFFINE, (1, lean, -lean * (reg.img.height - yc), 0, 1, 0)))
    reg.text("™", "arial.ttf", 1.8, *at(18.6, 13.6), SILK)
    # The small parts: the ceramic capacitors, the diode.
    for x, y in ((-44.0, 41.0), (-40.6, 41.0), (2.0, 59.5), (2.0, 61.8), (2.0, 64.1), (2.0, 66.4), (-4.4, 17.6),
                 (11.6, 17.6), (-8.2, 42.0), (-27.0, 21.0)):
        reg.rect_(*at(x - 1.6, y + 1.0), *at(x + 1.6, y - 1.0), (232, 168, 40), r=0.8)
    reg.rect_(*at(34.0, 19.0), *at(38.0, 17.4), (20, 20, 22))
    reg.rect_(*at(37.0, 19.0), *at(37.6, 17.4), (200, 200, 200))
    return reg


def card():
    w, length, _ = L.SD["card"]
    reg = Region(L.REGIONS["card"], w, length, C["sd"])
    reg.rect_(1.5, 1.5, w - 1.5, 21.0, C["white"], r=1.0)
    reg.text("Memory Card", "arialbd.ttf", 3.0, w / 2, 9.0, (30, 30, 34))
    reg.text("2GB", "ariblk.ttf", 4.6, w / 2, 15.6, C["sd"])
    for k in range(9):                                    # the contacts, at the end that goes in first
        reg.rect_(2.0 + 2.3 * k, length - 4.0, 3.5 + 2.3 * k, length - 0.6, C["gold"])
    return reg


def pad():
    x0, x1, y0, y1 = L.PAD_SPAN
    reg = Region(L.REGIONS["pad"], x1 - x0, y1 - y0, C["pad"])
    P = L.PAD

    def at(x, y):
        return x - x0, y1 - y

    dx, dy, _, _ = P["dpad"]
    reg.circle(*at(dx, dy), 15.0, shade(C["pad"], -0.12))
    layer = reg.layer()                                    # the dish round the face buttons, slanting
    d = ImageDraw.Draw(layer)
    cx, cy = reg.p(*at(44.0, 0.0))
    d.ellipse([cx - 22.0 * reg.sx, cy - 13.0 * reg.sy, cx + 22.0 * reg.sx, cy + 13.0 * reg.sy],
              fill=shade(C["pad"], -0.18) + (255,))
    reg.over(layer.rotate(30, center=(cx, cy), resample=Image.BICUBIC))
    for name, (bx, by) in P["buttons"].items():
        ox, oy = {"a": (0.0, -8.4), "b": (-7.4, -5.4), "x": (7.4, 5.4), "y": (0.0, 8.4)}[name]
        reg.text(name.upper(), "arialbd.ttf", 3.0, *at(bx + ox, by + oy), (90, 90, 96))
    for name in ("select", "start"):
        sx, sy = P[name]
        rotated_text(reg, name.upper(), "arialbd.ttf", 2.0, *at(sx - 2.4, sy - 4.4), (90, 90, 96), P["slant"])
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["board"])
    for reg in (board(), card(), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    path = os.path.join(out, "uzebox_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
