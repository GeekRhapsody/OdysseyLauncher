"""The Bally Astrocade card's printing (astrocade_print.png), for the console theme's Astrocade model (astrocade.py).

One image, laid out as astrocade_layout.REGIONS says, each region in millimetres as the model's UVs map it: the deck in
its own frame (its gold edge; the keypad's champagne plate, its tan-gold right column and the 24 keys' legends; the
cassette well and INSERT ⇩ CASSETTE on its lip; RESET and EJECT in gold), a side panel's walnut with the gold line along
its front and top edges, the walnut band across the front, the cover's front face (smoked, the badge: Bally on silver,
PROFESSIONAL arcade on red, in a gold frame), the controller's knurled sides and its gold Bally roundel, the Videocade's
label (a made-up game from tools/made-up-games: its number and title in cyan, the series' stripe), and swatches. Run it
with the system Python (Pillow):

    python tools/console-models/astrocade_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import astrocade_layout as L  # noqa: E402
from arcadia_print import grain  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(colour) for name, colour in L.COLOURS.items()}
INK = (16, 16, 16)
GOLD = C["gold"]
CYAN = (37, 172, 170)
RED = (210, 6, 36)
GAME = ("2003", "HIVE HUSTLE")            # tools/made-up-games's hivehstl, as a Videocade


def deck():
    """The deck: x across (-INNER at the left), down from its back edge (s = DECK_LENGTH) to its front."""
    w, h = 2 * L.INNER, L.DECK_LENGTH
    reg = Region(L.REGIONS["deck"], w, h, C["deck"])

    def at(x, s):
        return x + w / 2, h - s
    reg.rect_(*at(-w / 2 + 3.0, h - 2.0), *at(w / 2 - 3.0, 2.0), None, outline=GOLD, width=0.6)
    k = L.KEYPAD
    (x0, x1), (s0, s1) = k["x"], k["s"]
    reg.rect_(*at(x0, s1), *at(x1, s0), C["plate"], r=1.0)
    col_w = (x1 - x0) / k["cols"]
    reg.rect_(*at(x1 - col_w + 1.0, s1 - (s1 - s0) / k["rows"]), *at(x1 - 1.5, s0 + 1.5), (187, 154, 91))
    reg.rect_(*at(x0 + 1.5, s1 - (s1 - s0) / k["rows"] + 1.0), *at(x1 - 1.5, s0 + 1.5), None, outline=INK, width=0.3)
    kw, kh = k["key"]
    for legend, x, s in L.keys():
        reg.text(legend, "seguisym.ttf" if legend in "↑↓÷–" else "arialbd.ttf", 3.2, *at(x, s + kh / 2 + 3.2), INK)
        reg.rect_(*at(x - kw / 2, s + kh / 2), *at(x + kw / 2, s - kh / 2), C["key"], r=0.8)
    (x0, x1), (s0, s1) = L.WELL["x"], L.WELL["s"]
    reg.rect_(*at(x0, s1), *at(x1, s0), (14, 14, 14), r=1.0)
    l0, l1 = L.WELL["lip"]
    reg.rect_(*at(x0, l1), *at(x1, l0), shade(C["deck"], 0.08), r=1.0)
    reg.text("INSERT ⇩ CASSETTE", "seguisym.ttf", 4.0, *at((x0 + x1) / 2, (l0 + l1) / 2), shade(C["deck"], 0.35))
    reg.circle(*at((x0 + x1) / 2, s0 + 4.0), 8.0, shade(C["deck"], -0.4))      # the finger notch at its front
    for name, (a, b) in (("RESET", L.KEYS["reset"]), ("EJECT", L.KEYS["eject"])):
        reg.rect_(*at(a, L.KEYS["s"][1]), *at(b, L.KEYS["s"][0]), (30, 31, 30), r=1.0)
        reg.text(name, "arialbd.ttf", 3.0, *at((a + b) / 2, sum(L.KEYS["s"]) / 2), GOLD)
    reg.circle(*at(-w / 2 + 16.0, 30.0), 2.0, (10, 10, 10))
    return reg


def panel():
    """A side panel's face, from outside: y along (0 at the front, at the region's left), z up (8 at its foot)."""
    w, h = L.DEPTH, L.HEIGHT - 8.0
    reg = Region(L.REGIONS["panel"], w, h, C["wood"])
    grain(reg, w, h, C["wood"], seed=1978)

    def at(y, z):
        return y, L.HEIGHT - z
    pts = L.PANEL["outline"]
    edge = [pts[4], pts[3], pts[2]]                         # the front edge up to the top, along the top to the back
    reg.line([at(y + 2.0 * (1 if k == 0 else 0), z - 2.0) for k, (y, z) in enumerate(edge)], GOLD, 0.8)
    return reg


def front():
    """The walnut band across the front: x across, z down from its top."""
    w, h = 2 * L.INNER, L.BAND - 8.0
    reg = Region(L.REGIONS["front"], w, h, C["wood"])
    grain(reg, w, h, C["wood"], seed=1977)
    reg.rect_(0.0, 0.8, w, 1.5, GOLD)
    return reg


def badge():
    """The cover's front face: x across, z down from its top (121); the badge right of its middle."""
    w, h = 2 * L.INNER, L.HEIGHT - L.DECK[1][1]
    reg = Region(L.REGIONS["badge"], w, h, C["smoked"])

    def at(x, z):
        return x + w / 2, L.HEIGHT - z
    (x0, x1), (z0, z1) = L.BADGE["x"], L.BADGE["z"]
    mid = x0 + (x1 - x0) * 0.38
    reg.rect_(*at(x0 - 1.0, z1 + 1.0), *at(x1 + 1.0, z0 - 1.0), GOLD, r=1.0)
    reg.rect_(*at(x0, z1), *at(mid, z0), (210, 211, 197))
    reg.rect_(*at(mid, z1), *at(x1, z0), (216, 8, 16))
    reg.text("Bally", "segoescb.ttf", 10.0, *at((x0 + mid) / 2, (z0 + z1) / 2), (150, 140, 110))
    reg.text("PROFESSIONAL", "arialbd.ttf", 2.2, *at((mid + x1) / 2, z1 - 2.6), (250, 250, 250))
    reg.text("arcade", "ariblk.ttf", 11.0, *at((mid + x1) / 2, (z0 + z1) / 2 - 1.2), (250, 250, 250))
    return reg


def grip():
    """The controller's sides: v front to back, z down from its top; knurled in diamonds, the roundel on its head."""
    w, h = 70.0, 124.0
    reg = Region(L.REGIONS["grip"], w, h, C["grip"])
    step = 2.2
    for k in range(-60, 60):                                # the knurling: two sets of fine diagonals
        reg.line([(k * step, 0.0), (k * step + h, h)], shade(C["grip"], 0.2), 0.25)
        reg.line([(k * step + h, 0.0), (k * step, h)], shade(C["grip"], 0.2), 0.25)
    reg.rect_(0.0, 0.0, w, 30.0, C["grip"])                 # the head is smooth
    reg.circle(36.0, 16.0, 7.0, (201, 169, 74))
    reg.circle(36.0, 16.0, 5.6, (20, 20, 20))
    reg.text("Bally", "segoescb.ttf", 3.6, 36.0, 16.0, (201, 169, 74))
    return reg


def cartridge():
    """The Videocade's label: Bally up its left edge in red, PROFESSIONAL videocade, the game's number and title in
    cyan, the series' stripe across the corner."""
    w, h = L.VIDEOCADE["label"]
    reg = Region(L.REGIONS["cart"], w, h, C["label"])
    f = ImageFont.truetype(FONTS + "segoescb.ttf", round(12.0 * reg.sx))
    box = f.getbbox("Bally")
    word = Image.new("RGBA", (box[2] - box[0] + 8, box[3] - box[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(word).text((4 - box[0], 4 - box[1]), "Bally", font=f, fill=RED + (255,))
    word = word.rotate(72, expand=True)
    cx, cy = reg.p(9.5, h / 2)
    reg.img.alpha_composite(word, (round(cx - word.width / 2), round(cy - word.height / 2)))
    reg.text("PROFESSIONAL", "arialbd.ttf", 3.0, 21.0, 6.0, INK, anchor="lm")
    reg.text("videocade", "ariblk.ttf", 11.0, 20.0, 15.0, INK, anchor="lm")
    reg.text(" ".join(GAME), "arialnb.ttf" if os.path.exists(FONTS + "arialnb.ttf") else "arialbd.ttf", 6.0, 21.0,
             27.0, CYAN, anchor="lm")
    reg.text("by Arcwave", "arialbd.ttf", 2.4, 21.0, 32.0, CYAN, anchor="lm")
    reg.poly([(40.0, h), (w, 26.0), (w, 34.0), (52.0, h)], CYAN)
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "arialbd.ttf", round(3.0 * reg.sx))
    ImageDraw.Draw(layer).text(reg.p(64.0, 39.0), "ACTION/SKILLS SERIES", font=f, fill=(255, 255, 255, 255),
                               anchor="mm")
    reg.over(layer.rotate(math.degrees(math.atan2(8.0, w - 46.0)), center=reg.p(64.0, 39.0)))
    reg.text("©ARCWAVE 1981 ALL RIGHTS RESERVED", "arial.ttf", 1.8, w - 2.0, h - 2.0, INK, anchor="rb")
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["black"])
    for reg in (deck(), panel(), front(), badge(), grip(), cartridge()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(C, lit=(255, 120, 60))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "astrocade_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
