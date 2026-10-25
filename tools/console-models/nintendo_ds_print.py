"""The Nintendo DS family's printing and screens, for the console theme's models (tools/console-models/nintendo_ds.py).

Draws each kind's two atlases, their regions as nintendo_ds_layout.py places them. <kind>_print.png: the lower half's
face seen from above and the upper half's face seen square on, in millimetres as the model's planar UVs map them (the
screens' bezels and the switched-off screens under them, the D-pad, A, B, X and Y, START and SELECT, the speakers), and
the swatches small parts take their colour from. <kind>_media.png: the screens at the DS's 256 x 192 pixels (the
start-up screen and the menu with the game card's tile; then the game's title, TOUCH TO START, and that button pressed)
and the game card's label: a made-up game, Odyssey. Run it with the system Python (Pillow):

    python tools/console-models/nintendo_ds_print.py <kind> <out folder>

It writes <kind>_print.png and <kind>_media.png there (nds, n3ds).
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nintendo_ds_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

SCREEN_OFF = (52, 58, 56)


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def screen_bezel(reg, cx, cy, screen, bezel, colour):
    bw, bh, r = bezel
    reg.rect_(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2, colour, r=r)
    sw, sh = screen
    reg.rect_(cx - sw / 2, cy - sh / 2, cx + sw / 2, cy + sh / 2, SCREEN_OFF)


def lower(k):
    w, d = k["width"], k["depth"]
    face = rgb(k["face_colour"])
    legend = rgb(k["legend"])
    reg = Region(L.PRINT_REGIONS["lower"], w, d, face)

    def at(x, y):
        return x + w / 2, d - y
    s = k["screen"]
    if "panel" in k:                                   # the raised panel round the touch screen, its strip under it
        pw, ph, r = k["panel"]["size"]
        px, py = at(s["x"], k["panel"]["y"])
        reg.rect_(px - pw / 2 - 0.6, py - ph / 2 - 0.6, px + pw / 2 + 0.6, py + ph / 2 + 0.6, shade(face, -0.35), r=r)
        reg.rect_(px - pw / 2, py - ph / 2, px + pw / 2, py + ph / 2, shade(face, 0.05), r=r)
        for j, label in enumerate(k["strip"]):
            lx = px + (j - 1) * pw * 0.32
            reg.text(("\u2302 " if label == "HOME" else "") + label, "seguisym.ttf" if label == "HOME" else "arialbd.ttf",
                     2.6, lx, py + ph / 2 - 3.6, legend)
    screen_bezel(reg, *at(s["x"], s["y"]), s["size"], s["bezel"], rgb(k["dark"]))
    if "circle_pad" in k:
        c = k["circle_pad"]
        cx, cy = at(c["x"], c["y"])
        reg.circle(cx, cy, c["well"] + 0.8, shade(face, -0.45))
        reg.circle(cx, cy, c["well"], shade(face, -0.15))
        reg.circle(cx, cy, c["r"], rgb(k["pad"]))
        reg.circle(cx, cy, c["r"] - 1.2, shade(rgb(k["pad"]), 0.06))
    p = k["dpad"]
    cx, cy = at(p["x"], p["y"])
    length, width = p["arm"]
    reg.circle(cx, cy, length / 2 + 1.6, shade(face, -0.08))
    for horizontal in (True, False):
        a, b = (length / 2 + 0.6, width / 2 + 0.6) if horizontal else (width / 2 + 0.6, length / 2 + 0.6)
        reg.rect_(cx - a, cy - b, cx + a, cy + b, shade(face, -0.4), r=1.2)
    for horizontal in (True, False):
        a, b = (length / 2, width / 2) if horizontal else (width / 2, length / 2)
        reg.rect_(cx - a, cy - b, cx + a, cy + b, rgb(k["accent"]), r=1.0)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        reg.line([(cx + dx * 5.0 - dy * 1.0, cy + dy * 5.0 - dx * 1.0), (cx + dx * 7.0, cy + dy * 7.0)],
                 shade(rgb(k["accent"]), -0.3), 0.5)
    f = k["face"]
    for letter, dx, dy in (("A", 1, 0), ("B", 0, -1), ("X", 0, 1), ("Y", -1, 0)):
        bx, by = at(f["x"] + dx * f["reach"], f["y"] + dy * f["reach"])
        reg.circle(bx, by, f["r"] + 0.7, shade(face, -0.4))
        reg.circle(bx, by, f["r"], rgb(k["accent"]))
        reg.text(letter, "arialbd.ttf", 3.2, bx, by, legend)
    for name, x, y, r in k["small"]:
        bx, by = at(x, y)
        reg.circle(bx, by, r + 0.5, shade(face, -0.4))
        reg.circle(bx, by, r, rgb(k["accent"]))
        if name == "power":
            reg.text("\u23fb", "seguisym.ttf", 2.6, bx, by, legend)
        reg.text(name.upper(), "arialbd.ttf", 1.9 if name != "power" else 2.4, bx + r + 1.2, by, legend, anchor="lm")
    return reg


def upper(k):
    w, d = k["width"], k["depth"] - 2.0
    face = rgb(k["upper_colour"])
    reg = Region(L.PRINT_REGIONS["upper"], w, d, face)

    def at(x, y):
        return x + w / 2, d - y
    s = k["upper_screen"]
    screen_bezel(reg, *at(0.0, s["y"]), s["size"], s["bezel"], rgb(k["dark"]))
    dots = shade(face, -0.5) if sum(face) > 300 else (8, 8, 10)
    for sx, sy in k["speakers"]:
        for col, row in k["speaker_dots"]:
            reg.circle(*at(sx + col * 1.8, sy + row * 3.0), 0.75, dots)
    if "camera" in k:
        x, y, r = k["camera"]
        reg.circle(*at(x, y), r + 0.6, (60, 62, 66))
        reg.circle(*at(x, y), r, (18, 20, 26))
        reg.circle(*at(x - r * 0.3, y + r * 0.3), r * 0.3, (90, 96, 120))
    return reg


def print_atlas(k):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(k["colour"]))
    lower(k).paste(image)
    upper(k).paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("dark", rgb(k["dark"])), ("accent", rgb(k["accent"])), ("card", (122, 125, 130)),
                         ("pad", rgb(k.get("pad", k["accent"])))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    return image


# ---- The screens -----------------------------------------------------------------------------------------------------

def boot_upper(size):
    """The start-up screen's upper half: white, the console's name."""
    img = Image.new("RGB", (512, 384), (250, 250, 250))
    d = ImageDraw.Draw(img)
    d.text((256, 150), "Nintendo", font=font("arialbd.ttf", 44), fill=(150, 150, 154), anchor="mm")
    d.rounded_rectangle([196, 196, 252, 252], 8, outline=(60, 60, 64), width=6)
    d.rounded_rectangle([262, 196, 318, 252], 8, outline=(60, 60, 64), width=6)
    d.text((256, 300), "Odyssey Launcher", font=font("arial.ttf", 22), fill=(170, 170, 174), anchor="mm")
    return img.resize(size, Image.LANCZOS)


def home_upper(size):
    """The 3DS's HOME Menu, its upper screen: the chosen software's banner on a pale field."""
    w, h = size[0] * 2, size[1] * 2
    img = Image.new("RGB", (w, h), (236, 242, 248))
    d = ImageDraw.Draw(img)
    for y in range(0, h, 24):
        d.line([(0, y), (w, y)], fill=(224, 233, 243), width=3)
    banner = space((560, 300))
    db = ImageDraw.Draw(banner)
    ship(db, 170, 190, 2.2, "#FFFFFF", "#FFB23C")
    db.text((280, 80), "ODYSSEY", font=font("ariblk.ttf", 70), fill="#FFE45C", anchor="mm", stroke_width=4,
            stroke_fill="#5A1A08")
    d.rounded_rectangle([(w - 584) // 2, (h - 324) // 2, (w + 584) // 2, (h + 324) // 2], 18, fill=(255, 255, 255))
    img.paste(banner.convert("RGB"), ((w - 560) // 2, (h - 300) // 2))
    return img.resize(size, Image.LANCZOS)


def home_lower(size):
    """The 3DS's HOME Menu, its lower screen: rows of software icons, the game's chosen."""
    w, h = size[0] * 2, size[1] * 2
    img = Image.new("RGB", (w, h), (240, 244, 248))
    d = ImageDraw.Draw(img)
    for row in range(3):
        for col in range(4):
            x, y = 40 + col * 148, 50 + row * 136
            if row == 0 and col == 0:
                d.rounded_rectangle([x - 8, y - 8, x + 112, y + 112], 18, fill=(70, 170, 240))
                icon = space((96, 96))
                ship(ImageDraw.Draw(icon), 40, 48, 1.4, "#FFFFFF", "#FFB23C")
                img.paste(icon.convert("RGB"), (x + 4, y + 4))
            else:
                d.rounded_rectangle([x, y, x + 104, y + 104], 16, fill=(214, 222, 232))
    return img.resize(size, Image.LANCZOS)


def boot_lower(size):
    """The menu's lower half: the game card's tile, chosen, over the menu's pale lines."""
    img = Image.new("RGB", (512, 384), (238, 244, 250))
    d = ImageDraw.Draw(img)
    for y in range(0, 384, 16):
        d.line([(0, y), (512, y)], fill=(222, 232, 244), width=2)
    d.rounded_rectangle([56, 70, 456, 210], 18, fill=(255, 255, 255), outline=(60, 150, 230), width=8)
    icon = space((96, 96))
    ship(ImageDraw.Draw(icon), 40, 48, 1.4, "#FFFFFF", "#FFB23C")
    img.paste(icon, (84, 92))
    d.text((210, 122), "ODYSSEY", font=font("arialbd.ttf", 40), fill=(40, 40, 60), anchor="lm")
    d.text((210, 168), "Odyssey Launcher", font=font("arial.ttf", 22), fill=(110, 110, 130), anchor="lm")
    for k, label in enumerate(("PictoChat", "Download Play", "Settings")):
        x = 70 + k * 130
        d.rounded_rectangle([x, 260, x + 112, 330], 12, fill=(250, 252, 255), outline=(170, 196, 226), width=4)
        d.text((x + 56, 295), label, font=font("arial.ttf", 17), fill=(90, 110, 140), anchor="mm")
    return img.resize(size, Image.LANCZOS)


def game_upper(size):
    w, h = size[0] * 2, size[1] * 2
    img = space((w, h))
    d = ImageDraw.Draw(img)
    ship(d, w * 0.293, h * 0.651, 2.6, "#FFFFFF", "#FFB23C")
    d.text((w // 2, round(h * 0.22)), "ODYSSEY", font=font("ariblk.ttf", 70), fill="#FFE45C", anchor="mm",
           stroke_width=4, stroke_fill="#5A1A08")
    d.text((w // 2, round(h * 0.3646)), "A VOYAGE IN TWO SCREENS", font=font("arialbd.ttf", 20), fill="#E8E0FF",
           anchor="mm")
    return img.convert("RGB").resize(size, Image.LANCZOS)


def game_lower(size, pressed):
    w, h = size[0] * 2, size[1] * 2
    img = Image.new("RGB", (w, h), (22, 18, 64))
    d = ImageDraw.Draw(img)
    for k in range(60):
        x, y = (k * 7919) % w, (k * 104729 // 7) % h
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(150, 150, 230))
    box = [w // 2 - 160, h // 2 - 42, w // 2 + 160, h // 2 + 48]
    if pressed:
        d.rounded_rectangle([b + 4 for b in box], 24, fill=(255, 210, 90), outline=(255, 255, 255), width=6)
        d.text((w // 2 + 4, h // 2 + 7), "TOUCH TO START", font=font("arialbd.ttf", 34), fill=(70, 30, 10), anchor="mm")
    else:
        d.rounded_rectangle([box[0], box[1] + 8, box[2], box[3] + 8], 24, fill=(120, 60, 20))
        d.rounded_rectangle(box, 24, fill=(255, 180, 60), outline=(255, 240, 200), width=6)
        d.text((w // 2, h // 2 + 3), "TOUCH TO START", font=font("arialbd.ttf", 34), fill=(70, 30, 10), anchor="mm")
    d.text((w // 2, h - 54), "\u00a9 ODYSSEY LAUNCHER", font=font("arial.ttf", 20), fill=(170, 160, 230), anchor="mm")
    return img.resize(size, Image.LANCZOS)


def card_label(k):
    """The game card's face: its grey plastic, the console's name on its label's band, Odyssey's art."""
    c = L.CARD
    reg = Region(k["media"]["card"], c["width"], c["length"], (122, 125, 130))
    reg.rect_(2.5, 2.5, c["width"] - 2.5, c["length"] - 6.0, (238, 238, 240), r=1.2)
    art = space((640, 480))
    d = ImageDraw.Draw(art)
    ship(d, 200, 300, 2.6, "#FFFFFF", "#FFB23C")
    d.text((320, 120), "ODYSSEY", font=font("ariblk.ttf", 92), fill="#FFE45C", anchor="mm", stroke_width=5,
           stroke_fill="#5A1A08")
    x0, y0, x1, y1 = reg.box(3.5, 8.0, c["width"] - 3.5, c["length"] - 7.0)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.text(k["name"], "arialbd.ttf", 2.6, c["width"] / 2, 5.2, (40, 40, 44))
    for k in range(8):                                        # the contacts along its leading edge
        x = 5.0 + k * 3.5
        reg.rect_(x, c["length"] - 3.6, x + 2.2, c["length"] - 0.8, (200, 170, 90), r=0.3)
    return reg


def media_atlas(kind, k):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (20, 20, 22))
    upper_px, lower_px = k["screen_px"]
    menu = (home_upper(upper_px), home_lower(lower_px)) if kind == "n3ds" else (boot_upper(upper_px), boot_lower(lower_px))
    for name, img in (("boot_upper", menu[0]), ("boot_lower", menu[1]), ("game_upper", game_upper(upper_px)),
                      ("game_lower", game_lower(lower_px, False)), ("game_pressed", game_lower(lower_px, True))):
        x, y, _, _ = k["media"][name]
        image.paste(img, (x, y))
    card_label(k).paste(image)
    return image


def main(kind, out):
    k = L.KINDS[kind]
    os.makedirs(out, exist_ok=True)
    for name, image in ((f"{kind}_print.png", print_atlas(k)), (f"{kind}_media.png", media_atlas(kind, k))):
        path = os.path.join(out, name)
        image.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
