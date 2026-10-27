"""The Android card's printing and screens (android_print.png, android_media.png), for the console theme's Android model
(android.py).

`android_print.png`, laid out as android_layout.REGIONS says, each region in millimetres as the model's UVs map it: the
face (the black glass, the frame's thin rim round it), the back (graphite, the lenses' bases, unbranded) and swatches.
`android_media.png`: the screens at the phone's shape: the lock screen, the home screen of made-up apps (a made-up game
among them, its icon from its painting), and the game's title and two moments of it (tools/made-up-games), these three
drawn turned a quarter so they stand upright when the phone is turned landscape. Make the made-up games' library first
(tools/made-up-games/README.md), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/android_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import android_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
WHITE = (250, 250, 252)
ICONS = [(66, 133, 244), (52, 168, 83), (90, 90, 96), (234, 67, 53), (250, 120, 40), (60, 180, 160), (200, 60, 70),
         (40, 40, 50), (240, 180, 40), (80, 150, 240), (110, 80, 200)]


def font(size, bold=False):
    return ImageFont.truetype(FONTS + ("segoeuib.ttf" if bold else "segoeui.ttf"), size)


def wallpaper(size):
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(round(30 + 60 * t), round(40 + 20 * t), round(110 + 60 * (1 - t))))
    for k in range(5):                                     # soft circles of light
        d.ellipse([w * (0.1 + 0.18 * k) - 40, h * (0.2 + 0.13 * k) - 40, w * (0.1 + 0.18 * k) + 40,
                   h * (0.2 + 0.13 * k) + 40], outline=(120, 110, 200), width=2)
    return img


def status(img):
    d = ImageDraw.Draw(img)
    d.text((12, 10), "10:24", font=font(11, True), fill=WHITE, anchor="lm")
    d.rectangle([img.width - 26, 6, img.width - 10, 14], outline=WHITE, width=1)
    d.rectangle([img.width - 24, 8, img.width - 14, 12], fill=WHITE)


def lock():
    img = wallpaper(L.SCREEN["pixels"])
    d = ImageDraw.Draw(img)
    status(img)
    d.text((img.width / 2, 110), "10:24", font=font(60, True), fill=WHITE, anchor="mm")
    d.text((img.width / 2, 152), "Tuesday 27 October", font=font(13), fill=WHITE, anchor="mm")
    d.rounded_rectangle([img.width / 2 - 8, img.height - 70, img.width / 2 + 8, img.height - 56], radius=3, fill=WHITE)
    d.arc([img.width / 2 - 6, img.height - 80, img.width / 2 + 6, img.height - 64], 180, 360, fill=WHITE, width=2)
    d.text((img.width / 2, img.height - 38), "Swipe up to unlock", font=font(11), fill=WHITE, anchor="mm")
    return img


def home(game):
    img = wallpaper(L.SCREEN["pixels"])
    d = ImageDraw.Draw(img)
    status(img)
    d.rounded_rectangle([14, 34, img.width - 14, 58], radius=12, fill=(240, 240, 245))
    d.text((30, 46), "Search", font=font(11), fill=(110, 110, 120), anchor="lm")
    icon = ImageOps.fit(game.keyart, (40, 40), Image.LANCZOS)
    mask = Image.new("L", (40, 40), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 39, 39], radius=10, fill=255)
    for k, name in enumerate(L.APPS):
        cx, cy = 34 + 56 * (k % 4), 100 + 70 * (k // 4)
        if name == L.APPS[-1]:
            img.paste(icon, (cx - 20, cy - 20), mask)
        else:
            d.rounded_rectangle([cx - 20, cy - 20, cx + 20, cy + 20], radius=10, fill=ICONS[k % len(ICONS)])
            d.text((cx, cy), name[0], font=font(18, True), fill=WHITE, anchor="mm")
        d.text((cx, cy + 30), name, font=font(9), fill=WHITE, anchor="mm")
    for k in range(4):                                     # the dock
        cx = 34 + 56 * k
        d.rounded_rectangle([cx - 20, img.height - 84, cx + 20, img.height - 44], radius=10, fill=ICONS[k + 3])
    d.rounded_rectangle([img.width / 2 - 36, img.height - 14, img.width / 2 + 36, img.height - 10], radius=2,
                        fill=WHITE)
    return img


def turned(img):
    """A landscape screen, turned to stand upright when the phone is turned landscape (its top to the right)."""
    return img.rotate(-90, expand=True)


def screens(game):
    w, h = L.SCREEN["pixels"]
    title = S.title(game, (h, w), prompt="TAP TO PLAY")
    game1, game2 = S.play(game, (h, w))
    return dict(lock=lock(), home=home(game), title=turned(title), game1=turned(game1), game2=turned(game2))


def face():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["glass"])
    reg.rect_(0.0, 0.0, x1 - x0, z1 - z0, None, outline=C["frame"], width=0.6)
    return reg


def back():
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["back"], x1 - x0, z1 - z0, C["back"])

    def at(x, z):                                          # seen from behind: the phone's right at the left
        return x1 - x, z1 - z
    for z in L.LENSES["z"]:
        reg.circle(*at(L.LENSES["x"], z), L.LENSES["r"] + 0.6, shade(C["back"], -0.2))
    reg.circle(*at(*L.FLASH["at"]), L.FLASH["r"] + 0.4, shade(C["back"], -0.3))
    reg.circle(*at(*L.FLASH["at"]), L.FLASH["r"], C["flash"])
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["glass"])
    for reg in (face(), back()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "android_print.png"), optimize=True)
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    for name, img in screens(game).items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.convert("RGB").resize((w, h), Image.LANCZOS), (x, y))
    media.save(os.path.join(out, "android_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
