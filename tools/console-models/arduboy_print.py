"""The Arduboy card's printing and screens (arduboy_print.png, arduboy_media.png), for the console theme's Arduboy model
(arduboy.py).

`arduboy_print.png`, laid out as arduboy_layout.REGIONS says, each region in millimetres as the model's UVs map it: the
face, the white board as it shows through the clear plate (its traces, the parts on it: the microcontroller turned on
its corner, the row under the OLED, the OLED's flex, the USB socket's pads, the reset button and lights; ARDUBOY in gold
slanting over A and B; the brass screws; the plate's edge round it all), the back (brushed aluminium, ARDUBOY and its
marks) and swatches. `arduboy_media.png`: the screens at the OLED's 128 x 64, white on black: the start-up logo, a
made-up game's title (tools/made-up-games) and two moments of it. Make the made-up games' library first
(tools/made-up-games/README.md), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/arduboy_print.py artifacts/made-up-games <out folder>
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arduboy_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from uzebox_print import rotated_text  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}


def face():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["board"])

    def at(x, z):
        return x - x0, z1 - z

    rnd = random.Random(2016)
    trace = shade(C["board"], -0.08)
    for _ in range(40):
        xa, za = rnd.uniform(-24, 24), rnd.uniform(4, 80)
        xb, zb = xa + rnd.uniform(-14, 14), za + rnd.uniform(-14, 14)
        reg.line([at(xa, za), at(xb, za), at(xb, max(3.0, min(82.0, zb)))], trace, 0.25)
    gx, gz = L.OLED["at"]
    reg.rect_(*at(-6.0, gz - 11.0), *at(6.0, gz - 14.0), (196, 120, 40))           # the OLED's flex
    for k in range(5):                                                         # the row of parts under it
        reg.rect_(*at(-12.0 + 6.0 * k - 1.4, 51.5), *at(-12.0 + 6.0 * k + 1.4, 50.0), C["chip"])
    layer = reg.layer()                                                        # the microcontroller, on its corner
    d = ImageDraw.Draw(layer)
    cx, cz = at(13.0, 19.0)
    s = 3.6
    d.polygon([reg.p(cx, cz - s * 1.41), reg.p(cx + s * 1.41, cz), reg.p(cx, cz + s * 1.41), reg.p(cx - s * 1.41, cz)],
              fill=C["chip"] + (255,))
    reg.over(layer)
    for x, z in ((-20.0, 18.0), (-17.0, 18.0), (2.0, 12.0), (6.0, 12.0), (20.0, 26.0), (-4.0, 44.0)):
        reg.rect_(*at(x - 1.0, z + 0.6), *at(x + 1.0, z - 0.6), C["chip"])
    for k in range(6):                                                         # the USB socket's pads
        reg.rect_(*at(-3.0 + 1.2 * k - 0.3, 3.0), *at(-3.0 + 1.2 * k + 0.3, 1.0), C["gold"])
    reg.rect_(*at(-20.0, 10.0), *at(-16.0, 7.0), C["chip"], r=0.5)            # the reset button
    reg.circle(*at(-12.0, 8.5), 0.7, (60, 200, 90))
    rotated_text(reg, "ARDUBOY", "ariblk.ttf", 3.0, *at(13.5, 46.5), C["gold"], 25)
    for x, z in L.SCREWS:
        reg.circle(*at(x, z), 2.2, C["brass"])
        reg.circle(*at(x, z), 1.0, shade(C["brass"], -0.3))
    reg.rect_(0.0, 0.0, x1 - x0, z1 - z0, None, outline=C["plate"], width=0.8)
    return reg


def back():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["back"], x1 - x0, z1 - z0, C["aluminium"])
    rnd = random.Random(55)
    for k in range(200):                                                       # brushed
        z = rnd.uniform(0, z1)
        reg.line([(0.0, z), (x1 - x0, z)], shade(C["aluminium"], rnd.uniform(-0.05, 0.05)), 0.12)
    ink = shade(C["aluminium"], -0.2)
    reg.text("ARDUBOY", "ariblk.ttf", 4.0, (x1 - x0) / 2, 60.0, ink)
    reg.text("CE   FCC   ♻", "seguisym.ttf", 2.6, (x1 - x0) / 2, 68.0, ink)
    reg.text("Made in China", "arial.ttf", 2.0, (x1 - x0) / 2, 73.0, ink)
    for x, z in L.SCREWS:
        reg.circle(-x - x0, z1 - z, 2.0, shade(C["aluminium"], -0.25))
    return reg


def mono(img, size):
    """A picture on the OLED: its contrast stretched, then dithered to white on black."""
    grey = ImageOps.autocontrast(ImageOps.fit(img.convert("RGB"), size, Image.LANCZOS).convert("L"), cutoff=2)
    bits = grey.convert("1")
    return Image.merge("RGB", [bits.convert("L").point(lambda v, c=c: ink_of(v, c)) for c in range(3)])


def ink_of(v, channel):
    on, off = rgb(L.PALETTE[-1]), rgb(L.PALETTE[0])
    return on[channel] if v else off[channel]


def screens(game):
    size = L.OLED["pixels"]
    ink, paper = rgb(L.PALETTE[-1]), rgb(L.PALETTE[0])
    boot = Image.new("RGB", size, paper)
    d = ImageDraw.Draw(boot)
    d.fontmode = "1"
    d.text((64, 26), "ARDUBOY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 16), fill=ink, anchor="mm")
    title = mono(S.title(game, size, prompt="", ink=ink), size)
    game1, game2 = (mono(frame, size) for frame in S.play(game, size))
    return dict(boot=boot, title=title, game1=game1, game2=game2)


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["board"])
    for reg in (face(), back()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "arduboy_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.PALETTE[0]))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.convert("RGB").resize((w, h), Image.NEAREST), (x, y))
    media.save(os.path.join(out, "arduboy_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
