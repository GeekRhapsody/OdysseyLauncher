"""The Super Cassette Vision card's printing (scv_print.png), for the console theme's Super Cassette Vision model
(scv.py).

One image, laid out as scv_layout.REGIONS says, each region in millimetres as the model's UVs map it: the console from
above (the black panel and its green stripe with EPOCH TV GAME SYSTEM and SELECT; Super Cassette Vision and its orange
rule; the cassette slot's white frame, its two dust flaps and CASSETTE; the dark grey panel with CASSETTE GAME MASTER
COMPONENT and ANALOG-RGB 128 SPRITES; POWER's OFF and ON, RESET and PAUSE in their white frames; the SELECT pad's keys
and legends; the vents and the speaker's grille; the smoked flap and the black band along its hinge), the controllers'
faces (the stick's boss, the label band: 1P brown, 2P blue), the cartridge's label (a made-up game from
tools/made-up-games: its box art under the Super Cassette Vision band), and swatches. Make the made-up games' library
first (tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/scv_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scv_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(colour) for name, colour in L.COLOURS.items()}
WHITE = (240, 240, 238)
ORANGE = (224, 90, 40)
GAME = ("Kickflip City (Europe)", "megadrive")


def slanted(reg, text, font, size, x, y, fill, outline=None, anchor="lm", lean=0.2):
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    extra = dict(stroke_width=max(1, round(0.35 * reg.sx)), stroke_fill=outline + (255,)) if outline else {}
    d.text(reg.p(x, y), text, font=f, fill=fill + (255,), anchor=anchor, **extra)
    yc = reg.p(0, y)[1]
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, lean, -lean * yc, 0, 1, 0)))


def logo(reg, x, y, size):
    """Super in orange, outlined, then Cassette Vision in white script; the orange rule under them."""
    slanted(reg, "Super", "arialbi.ttf", size * 0.55, x, y + size * 0.1, ORANGE, outline=WHITE)
    slanted(reg, "Cassette Vision", "segoescb.ttf", size, x + size * 1.55, y, WHITE)
    reg.rect_(x, y + size * 0.62, x + size * 6.4, y + size * 0.7, ORANGE)


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, C["case"])

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    # The vents along the back edge, the speaker's grille at the back left.
    for k in range(5):
        y = L.DEPTH - 6.0 - k * 2.6
        reg.rect_(*at(-140.0, y + 0.5), *at(140.0, y - 0.5), shade(C["case"], -0.12))
    for j in range(5):
        for i in range(9):
            reg.rect_(*at(-140.0 + i * 5.0, 192.0 - j * 4.2), *at(-137.5 + i * 5.0, 190.0 - j * 4.2),
                      shade(C["case"], -0.3), r=0.5)
    # The black panel and its green stripe.
    (y0, y1), st = L.PANEL["y"], L.PANEL["stripe"]
    reg.rect_(*at(-142.0, y1), *at(142.0, y0), C["panel"])
    reg.rect_(*at(-142.0, y1), *at(142.0, y1 - st), C["green"])
    reg.text("EPOCH TV GAME SYSTEM", "arialbd.ttf", 3.2, *at(-138.0, y1 - st / 2), (16, 16, 16), anchor="lm")
    reg.text("SELECT", "arialbd.ttf", 3.2, *at(sum(L.KEYPAD["x"]) / 2, y1 - st / 2), (16, 16, 16))
    logo(reg, *at(-126.0, 144.0), 9.0)
    # The slot's frame, its two flaps meeting in its middle; CASSETTE under it.
    (sx0, sx1), (sy0, sy1), f = L.SLOT["x"], L.SLOT["y"], L.SLOT["frame"]
    reg.rect_(*at(sx0 - f, sy1 + f), *at(sx1 + f, sy0 - f), C["frame"], r=1.5)
    reg.rect_(*at(sx0, sy1), *at(sx1, sy0), C["dark"])
    reg.rect_(*at(sx0 + 1.0, (sy0 + sy1) / 2 + 0.3), *at(sx1 - 1.0, (sy0 + sy1) / 2 - 0.3), (20, 20, 20))
    reg.text("CASSETTE", "arialbd.ttf", 2.6, *at((sx0 + sx1) / 2, sy0 - f - 2.6), WHITE)
    reg.rect_(*at(-36.0, 138.0), *at(6.0, 94.0), C["dark"])
    for k, line in enumerate(("CASSETTE GAME", "MASTER", "COMPONENT")):
        reg.text(line, "arialbd.ttf", 2.8, *at(-15.0, 130.0 - k * 4.2), WHITE)
    for k, line in enumerate(("ANALOG-RGB", "128 SPRITES")):
        reg.text(line, "arialbd.ttf", 2.6, *at(-15.0, 112.0 - k * 4.0), ORANGE)
    # POWER, RESET and PAUSE: their white frames and words.
    for name, box_ in (("POWER", L.SWITCH), ("RESET", L.RESET), ("PAUSE", L.PAUSE)):
        (x0, x1), (b0, b1) = box_["x"], box_["y"]
        reg.rect_(*at(x0 - 1.5, b1 + 1.5), *at(x1 + 1.5 + (L.SWITCH["travel"] if name == "POWER" else 0.0), b0 - 1.5),
                  C["frame"], r=1.0)
        reg.rect_(*at(x0, b1), *at(x1 + (L.SWITCH["travel"] if name == "POWER" else 0.0), b0), C["key"])
        reg.text(name, "arialbd.ttf", 2.4, *at(x0 - 2.0, (b0 + b1) / 2), WHITE, anchor="rm")
    reg.text("OFF", "arialbd.ttf", 2.2, *at(L.SWITCH["x"][0] + 4.0, L.SWITCH["y"][0] - 3.0), WHITE)
    reg.text("ON", "arialbd.ttf", 2.2, *at(L.SWITCH["x"][1] + L.SWITCH["travel"] - 4.0, L.SWITCH["y"][0] - 3.0), WHITE)
    # The SELECT pad: its off-white surround, its keys and their legends.
    k = L.KEYPAD
    (kx0, kx1), (ky0, ky1) = k["x"], k["y"]
    reg.rect_(*at(kx0, ky1), *at(kx1, ky0), (210, 210, 203), r=2.0)
    kw, kh = k["key"]
    for r, row in enumerate(L.LEGENDS):
        for c, legend in enumerate(row):
            cx = kx0 + (kx1 - kx0) * (c + 0.5) / k["cols"]
            cy = ky1 - (ky1 - ky0) * (r + 0.5) / k["rows"]
            reg.rect_(*at(cx - kw / 2, cy + kh / 2), *at(cx + kw / 2, cy - kh / 2), C["key"], r=1.0)
            reg.text(legend, "arialbd.ttf", 3.0 if len(legend) > 1 else 4.2, *at(cx, cy), WHITE)
    # The smoked flap from above, the glossy black band along its hinge.
    reg.rect_(*at(-150.0, L.HINGE[0]), *at(150.0, L.LIP[0]), C["smoked"])
    reg.rect_(*at(-150.0, L.HINGE[0]), *at(150.0, L.HINGE[0] - 7.0), (16, 16, 16))
    return reg


def controller(name):
    """A controller's face: x across, v down from its top end (the caps') to its foot."""
    length, w, _ = L.PAD["size"]
    reg = Region(L.REGIONS[name], w, length, C["pad"])
    b = L.PAD["boss"]
    reg.circle(w / 2, b["v"], b["r"] + 1.2, shade(C["pad"], -0.18))
    reg.circle(w / 2, b["v"], b["r"], shade(C["pad"], 0.06))
    colour = (174, 110, 80) if name == "pad1" else (99, 146, 201)
    band = [(0.0, 34.0), (w, 20.0), (w, 34.0), (0.0, 48.0)]          # the label band under the caps, rising across
    reg.poly(band, colour)
    reg.poly([(0.0, 40.0), (w, 26.0), (w, 31.0), (0.0, 45.0)], (16, 16, 16))
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "arialbd.ttf", round(3.4 * reg.sx))
    ImageDraw.Draw(layer).text(reg.p(w / 2, 30.0), "CONTROLLER", font=f, fill=(250, 250, 250, 255), anchor="mm")
    small = ImageFont.truetype(FONTS + "segoescb.ttf", round(3.0 * reg.sx))
    ImageDraw.Draw(layer).text(reg.p(w / 2, 33.8), "Super Cassette Vision", font=small, fill=(250, 250, 250, 255),
                               anchor="mm")
    reg.over(layer.rotate(12.3, center=reg.p(w / 2, 32.0)))
    reg.text("1P" if name == "pad1" else "2P", "arialbd.ttf", 5.0, w - 8.0, length - 8.0, colour)
    return reg


def cartridge(made_up):
    """The cartridge's front: the band with the logo, the made-up game's box art."""
    w, _, h = L.CART["size"]
    reg = Region(L.REGIONS["cart"], w, h, (28, 120, 200))
    reg.rect_(0.0, 0.0, w, 10.0, C["panel"])
    logo(reg, 5.0, 4.2, 4.4)
    art = S.cover(*GAME, made_up)
    a, b, c, d = reg.box(3.0, 12.0, w - 3.0, h - 3.0)
    reg.img.paste(ImageOps.fit(art, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.3)),
                  (round(a), round(b)))
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["case"])
    for reg in (top(), controller("pad1"), controller("pad2"), cartridge(made_up)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(C, black=(14, 14, 14), cart=(28, 120, 200))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "scv_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
