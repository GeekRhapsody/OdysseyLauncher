"""The CreatiVision card's printing (crvision_print.png), for the console theme's CreatiVision model (crvision.py).

One image, laid out as crvision_layout.REGIONS says, each region in millimetres as the model's UVs map it: the console
from above (the deck's vents, the OFF/ON slide's well and its words, RESET, CREATIVISION embossed, the rainbow badge; the
compartment's trays and divider), the controllers' tops (the joystick's well and knurled ring; the keypad's window in
its frame, the cream and tan keys and their legends), an end's woodgrain panel, the cartridge's label (a made-up game
from tools/made-up-games: its box art under the CREATIVISION band), and swatches. Make the made-up games' library first
(tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/crvision_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crvision_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from arcadia_print import grain  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(colour) for name, colour in L.COLOURS.items()}
INK = (20, 18, 16)
DIGIT = (110, 30, 24)
STRIPES = [(219, 88, 68), (171, 229, 109), (98, 172, 228)]
GAME = ("Puck Rush (Europe)", "megadrive")


def badge(reg, x0, y0, x1, y1):
    """The rainbow badge: a rounded rectangle of three slanted stripes, red, green and blue."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    w = x1 - x0
    for k, colour in enumerate(STRIPES):
        a = x0 + w * k / 3
        d.polygon([reg.p(a - 3.0, y1), reg.p(a + w / 3 + 1.0, y1), reg.p(a + w / 3 + 4.0, y0), reg.p(a, y0)],
                  fill=colour + (255,))
    mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(reg.box(x0, y0, x1, y1), radius=2.0 * reg.sx, fill=255)
    layer.putalpha(Image.composite(layer.getchannel("A"), mask, mask))
    reg.over(layer)


def embossed(reg, text, x, y, size):
    """Moulded lettering, no paint: a lit edge above, a shadow below, the plastic's own black between."""
    f = ImageFont.truetype(FONTS + "ariblki.ttf" if os.path.exists(FONTS + "ariblki.ttf") else FONTS + "ariblk.ttf",
                           max(1, round(size * reg.sx)))
    for dy, colour in ((-0.35, shade(C["top"], 0.22)), (0.35, shade(C["top"], -0.45)), (0.0, C["top"])):
        layer = reg.layer()
        ImageDraw.Draw(layer).text(reg.p(x, y + dy), text, font=f, fill=colour + (255,), anchor="mm")
        yc = reg.p(0, y)[1]
        reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.2, -0.2 * yc, 0, 1, 0)))


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, C["top"])

    def at(x, y):
        return x + L.WIDTH / 2, L.DEPTH - y
    half = L.WIDTH / 2 - L.POST
    (t0, t1), d = L.TRAYS["y"], L.TRAYS["divider"]
    reg.rect_(*at(-half, t1), *at(half, t0), C["deep"])
    reg.rect_(*at(-d / 2, t1), *at(d / 2, t0), C["case"])
    v = L.VENTS
    for k in range(v["count"]):
        x = v["x"][0] + (v["x"][1] - v["x"][0]) * (k + 0.5) / v["count"]
        reg.rect_(*at(x - 1.6, v["y"][1]), *at(x + 1.6, v["y"][0]), (12, 12, 12), r=0.8)
    sw = L.SWITCH
    reg.rect_(*at(sw["x"][0], sw["y"][1]), *at(sw["x"][1], sw["y"][0]), (14, 14, 14), r=1.0)
    reg.text("OFF", "arialbd.ttf", 2.6, *at(sw["x"][0] + 3.0, sw["y"][0] - 3.4), shade(C["top"], 0.4))
    reg.text("ON", "arialbd.ttf", 2.6, *at(sw["x"][1] - 3.0, sw["y"][0] - 3.4), shade(C["top"], 0.4))
    rs = L.RESET
    reg.text("RESET", "arialbd.ttf", 2.6, *at(sum(rs["x"]) / 2, rs["y"][0] - 3.4), shade(C["top"], 0.4))
    embossed(reg, "CREATIVISION", *at(L.NAME["x"], L.NAME["y"]), L.NAME["height"])
    (bx0, bx1), (by0, by1) = L.BADGE["x"], L.BADGE["y"]
    badge(reg, *at(bx0, by1), *at(bx1, by0))
    return reg


def controller(name):
    """A controller's top: x along it (the model's left end at the region's left), y across (its back at the top)."""
    length, w, _ = L.PAD["size"]
    reg = Region(L.REGIONS[name], length, w, C["case"])
    left = name == "left"                             # the left controller's joystick is at its left end
    well = L.PAD["well"]
    jx = well["u"] if left else length - well["u"]
    reg.circle(jx, w / 2, well["r"] + 1.5, shade(C["case"], -0.35))
    reg.circle(jx, w / 2, well["r"], C["deep"])
    a, b, inset = L.PAD["window"]
    x0, x1 = (length - b, length - a) if left else (a, b)
    reg.rect_(x0 - 1.5, inset - 1.5, x1 + 1.5, w - inset + 1.5, (8, 8, 8), r=2.0)
    reg.rect_(x0, inset, x1, w - inset, (36, 30, 24), r=1.0)
    cols, rows = L.PAD["keys"]
    kw, kh = L.PAD["key"]
    for r, row in enumerate(L.LEGENDS[name]):
        for c, legend in enumerate(row):
            cx = x0 + (x1 - x0) * (c + 0.5) / cols
            cy = inset + (w - 2 * inset) * (r + 0.5) / rows
            special = len(legend) > 1 or not legend.isalpha()
            reg.rect_(cx - kw / 2 + 0.4, cy - kh / 2 + 0.4, cx + kw / 2 - 0.4, cy + kh / 2 - 0.4,
                      C["cream"] if special else C["tan"], r=1.2)
            size = 2.4 if len(legend) > 2 else 4.6
            colour = DIGIT if legend.isdigit() else INK
            reg.text(legend, "seguisym.ttf" if legend in "←→" else "arialbd.ttf", size, cx, cy, colour)
    return reg


def end():
    """An end's woodgrain panel: y along it, z down from its top."""
    (y0, y1), (z0, z1) = L.PANEL["y"], L.PANEL["z"]
    reg = Region(L.REGIONS["end"], y1 - y0, z1 - z0, C["wood"])
    grain(reg, y1 - y0, z1 - z0, C["wood"], seed=1981)
    return reg


def cartridge(made_up):
    """The cartridge's label, its top: x along it (its outer end at the right), y across."""
    length, w, _ = L.CART["size"]
    lw, lh = length - 14.0, w - 8.0
    reg = Region(L.REGIONS["cart"], lw, lh, (236, 232, 222))
    reg.rect_(0.0, 0.0, lw, 9.0, (24, 24, 26))
    badge(reg, 3.0, 2.0, 14.0, 7.0)
    reg.text("CREATIVISION", "ariblk.ttf", 4.6, 17.0, 4.5, (240, 240, 240), anchor="lm")
    art = S.cover(*GAME, made_up)
    a, b, c, d = reg.box(2.0, 10.5, lw - 2.0, lh - 2.0)
    reg.img.paste(ImageOps.fit(art, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.35)),
                  (round(a), round(b)))
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["case"])
    for reg in (top(), controller("left"), controller("right"), end(), cartridge(made_up)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(C, black=(10, 10, 10), red=(160, 30, 30))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "crvision_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
