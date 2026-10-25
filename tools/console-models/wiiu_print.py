"""The Wii U set's printing and screens, for the console theme's Wii U model (tools/console-models/wiiu.py).

Draws its atlas, its regions as wiiu_layout.py places them, each in millimetres as the model's planar UVs map it (the
screens in their pixels): the GamePad's face (its black, the screen's bezel, the sensor bar and its camera, the
sticks' wells, the buttons' names, the speakers, Wii U); the GamePad's screens (the Wii U Menu, its tiles on their
light ground; the menu with the disc's tile showing a made-up game, Odyssey, chosen; Odyssey's title; a moment of its
play); the console's front (EJECT and POWER, the power light lit blue, SYNC, the SD card's flap, Wii U); the disc's
label; and the swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/wiiu_print.py <out folder>

It writes wiiu_print.png there.
"""

import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiiu_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
NAME = (150, 150, 156)
BLUE = (64, 170, 255)


def wiiu_logo(reg, x, y, h, ink, ground):
    """Wii U: Wii in rounded letters, and the U cut out of a rounded square; h tall, its left middle at (x, y)."""
    f = ImageFont.truetype(FONTS + "segoeuib.ttf", max(1, round(h * 1.25 * reg.sx)))
    reg.draw.text(reg.p(x, y), "Wii", font=f, fill=ink, anchor="lm")
    w = reg.draw.textlength("Wii", font=f) / reg.sx
    s = x + w + h * 0.12
    reg.rect_(s, y - h * 0.48, s + h * 0.96, y + h * 0.48, ink, r=h * 0.22)
    reg.rect_(s + h * 0.24, y - h * 0.48, s + h * 0.72, y + h * 0.22, ground, r=h * 0.2)


# ---- The GamePad's face ------------------------------------------------------------------------------------------------

def pad():
    (w, h) = L.PAD["size"]
    reg = Region(L.REGIONS["pad"], w, h, CASE)

    def at(u, v):
        return u + w / 2, h / 2 - v
    (bw, bh), (su, sv) = L.SCREEN["bezel"], L.SCREEN["at"]
    reg.rect_(*at(su - bw / 2, sv + bh / 2), *at(su + bw / 2, sv - bh / 2), (8, 8, 10), r=2.0,
              outline=shade(CASE, 0.12), width=0.4)
    (u0, u1), v = L.SENSOR["u"], L.SENSOR["v"]
    reg.rect_(*at(u0, v + L.SENSOR["height"] / 2), *at(u1, v - L.SENSOR["height"] / 2), (6, 6, 8),
              r=L.SENSOR["height"] / 2)
    reg.circle(*at(0.0, v), 2.2, (40, 40, 46), outline=(70, 70, 78), width=0.3)
    for name in ("left", "right"):                                       # the sticks' wells
        reg.circle(*at(*L.STICKS[name]), L.STICKS["well"], shade(CASE, -0.4), outline=shade(CASE, 0.1), width=0.3)
    s = L.SMALL
    for label, key, dv in (("START", "start", -5.0), ("SELECT", "select", -5.0), ("HOME", "home", -7.6),
                           ("CONTROL", "tv", -5.4), ("POWER", "power", -5.4)):
        reg.text(label, "arial.ttf", 2.2, *at(s[key][0], s[key][1] + dv), NAME)
    reg.circle(*at(s["home"][0] - 15.5, s["home"][1]), 0.5, NAME)               # MIC
    reg.text("MIC", "arial.ttf", 2.2, *at(s["home"][0] - 15.5, s["home"][1] - 7.6), NAME)
    reg.circle(*at(s["tv"][0] - 13.5, s["tv"][1]), 0.6, (60, 60, 64))           # BATTERY
    reg.text("BATTERY", "arial.ttf", 2.2, *at(s["tv"][0] - 13.5, s["tv"][1] - 5.4), NAME)
    for u in (-87.0, 87.0):                                              # the speakers
        reg.rect_(*at(u - 2.0, -52.4), *at(u + 2.0, -53.6), (4, 4, 6), r=0.6)
    wiiu_logo(reg, *at(-73.0, -53.0), 6.4, (176, 176, 182), CASE)
    reg.rect_(*at(-103.0, -20.5), *at(-91.0, -27.5), None, r=1.4, outline=(140, 140, 146), width=0.35)

    # The buttons' tops, where their planar UVs fall: ABXY's letters, the d-pad's lines, + and -, HOME, TV, POWER.
    key, glyph = rgb(L.COLOURS["key"]), (214, 214, 220)
    (au, av), sp = L.ABXY["at"], L.ABXY["spacing"]
    for letter, du, dv in (("A", 1, 0), ("B", 0, -1), ("X", 0, 1), ("Y", -1, 0)):
        x, y = at(au + du * sp, av + dv * sp)
        reg.circle(x, y, L.ABXY["r"], key)
        reg.text(letter, "arial.ttf", 3.6, x, y + 0.1, glyph)
    (du, dv), size, arm = L.DPAD["at"], L.DPAD["size"], L.DPAD["arm"]
    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        reg.line([at(du + sx * (size / 2 - 2.0), dv + sy * (size / 2 - 2.0)),
                  at(du + sx * (size / 2 - 5.5), dv + sy * (size / 2 - 5.5))], (120, 120, 126), 0.5)
    for name, text, colour in (("start", "+", glyph), ("select", "−", glyph), ("power", "⏻", (230, 50, 60))):
        x, y = at(*s[name])
        reg.circle(x, y, s["r"], key)
        reg.text(text, "seguisym.ttf", 3.4, x, y, colour)
    hx, hy = at(*s["home"])
    reg.circle(hx, hy, s["home_r"], key, outline=(110, 110, 116), width=0.4)
    reg.poly([(hx - 2.4, hy - 0.2), (hx, hy - 2.4), (hx + 2.4, hy - 0.2), (hx + 1.6, hy - 0.2), (hx + 1.6, hy + 2.0),
              (hx - 1.6, hy + 2.0), (hx - 1.6, hy - 0.2)], glyph)
    tx, ty = at(*s["tv"])
    reg.rect_(tx - s["r"], ty - s["r"], tx + s["r"], ty + s["r"], key, r=0.8)
    reg.text("TV", "arialbd.ttf", 2.8, tx, ty, BLUE)
    return reg


# ---- The screens -------------------------------------------------------------------------------------------------------

W, H = 854, 480                                      # the GamePad's screen, FWVGA


def tile_art(d, x0, y0, x1, y1, k):
    """A menu tile's picture: a few made-up channels' simple glyphs, each its own colours."""
    rng = random.Random(k)
    palette = [((90, 180, 250), (255, 255, 255)), ((250, 170, 60), (255, 244, 220)), ((120, 200, 110), (240, 255, 236)),
               ((230, 90, 120), (255, 236, 240)), ((150, 120, 220), (244, 238, 255)), ((60, 190, 190), (230, 255, 255))]
    bg, fg = palette[k % len(palette)]
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=bg)
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 0.22
    shape = rng.choice(["circle", "square", "triangle"])
    if shape == "circle":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fg)
    elif shape == "square":
        d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=r * 0.3, fill=fg)
    else:
        d.polygon([(cx, cy - r), (cx + r, cy + r * 0.8), (cx - r, cy + r * 0.8)], fill=fg)


def menu(chosen):
    """The Wii U Menu: its tiles on their light ground, the first tile the disc's (empty, or the game's, chosen)."""
    img = Image.new("RGB", (W, H), (236, 236, 240))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(244 - 22 * t), int(244 - 22 * t), int(248 - 18 * t)))
    d.rectangle([0, 0, W, 54], fill=(250, 250, 252))
    d.line([(0, 54), (W, 54)], fill=(200, 200, 208), width=2)
    for k in range(4):                                               # the top bar's buttons
        d.rounded_rectangle([24 + 70 * k, 10, 82 + 70 * k, 44], radius=12, fill=(214, 216, 224))
    d.ellipse([W - 64, 8, W - 24, 48], fill=(130, 190, 240))
    tw, th, gx, gy = 130, 110, 22, 22
    x0, y0 = (W - (5 * tw + 4 * gx)) / 2, 84
    for row in range(3):
        for col in range(5):
            x, y = x0 + col * (tw + gx), y0 + row * (th + gy)
            k = row * 5 + col
            if k == 0:
                d.rounded_rectangle([x, y, x + tw, y + th], radius=14, fill=(250, 250, 252),
                                    outline=(200, 200, 208), width=2)
                if chosen:
                    art = space((tw - 12, th - 12)).convert("RGB")
                    ship(ImageDraw.Draw(art), 40, 60, 1.6, "#FFFFFF", "#FFB23C")
                    img.paste(art, (round(x + 6), round(y + 6)))
                    d.text((x + tw / 2, y + 22), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 17),
                           fill=(255, 214, 70), anchor="mm")
                    d.rounded_rectangle([x - 6, y - 6, x + tw + 6, y + th + 6], radius=18, outline=(40, 160, 255),
                                        width=6)
                else:
                    cx, cy = x + tw / 2, y + th / 2
                    d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=(214, 216, 222))
                    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(250, 250, 252))
            else:
                tile_art(d, x, y, x + tw, y + th, k)
    return img


def title():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 52), "ODYSSEY", font=ImageFont.truetype(FONTS + "ariblk.ttf", 104), fill=(255, 214, 70),
           anchor="mt", stroke_width=5, stroke_fill=(120, 30, 10))
    ship(d, 250, 290, 4.6, "#FFFFFF", "#FFB23C")
    d.text((W / 2, 428), "PRESS A TO START", font=ImageFont.truetype(FONTS + "arialbd.ttf", 34),
           fill=(255, 255, 255), anchor="mm")
    return img


def game():
    img = space((W, H)).convert("RGB")
    d = ImageDraw.Draw(img)
    rng = random.Random(7)
    for _ in range(40):
        x, y = rng.randrange(W), rng.randrange(H)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 255))
    ship(d, 210, 260, 3.4, "#FFFFFF", "#FFB23C")
    d.line([(280, 260), (520, 260)], fill=(255, 236, 80), width=6)
    for ax, ay, r in ((620, 250, 52), (760, 400, 34), (560, 110, 28)):
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(140, 96, 70), outline=(90, 60, 44), width=4)
    font = ImageFont.truetype(FONTS + "arialbd.ttf", 30)
    d.text((24, 30), "SCORE 001250", font=font, fill=(255, 255, 255), anchor="lm")
    d.text((W - 24, 30), "SHIPS 3", font=font, fill=(255, 214, 70), anchor="rm")
    return img


# ---- The console's front, the disc -------------------------------------------------------------------------------------

def front():
    w, d, h = L.CONSOLE["size"]
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x, h - z
    r = L.FRONT_BUTTONS["r"]
    for name in ("eject", "power"):
        reg.circle(*at(*L.FRONT_BUTTONS[name]), r + 0.7, shade(CASE, -0.4))
    ex, ez = L.FRONT_BUTTONS["eject"]
    reg.text("DISC", "arial.ttf", 1.9, *at(ex, ez + r + 2.4), NAME)
    reg.text("EJECT", "arial.ttf", 1.9, *at(ex, ez - r - 2.2), NAME)
    px, pz = L.FRONT_BUTTONS["power"]
    reg.text("POWER", "arial.ttf", 1.9, *at(px, pz - r - 2.2), NAME)
    reg.circle(*at(*L.POWER_LIGHT), 0.8, BLUE)
    sx, sz = L.SYNC
    reg.circle(*at(sx, sz), 2.2, shade(CASE, -0.4))
    reg.text("SYNC", "arial.ttf", 1.9, *at(sx, sz - 4.6), NAME)
    (fx0, fx1), (fz0, fz1) = L.FLAP["x"], L.FLAP["z"]
    reg.rect_(*at(fx0, fz1), *at(fx1, fz0), None, r=1.0, outline=shade(CASE, -0.5), width=0.5)
    wiiu_logo(reg, *at(w - 24.0, 8.0), 5.0, (176, 176, 182), CASE)
    return reg


def disc():
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (238, 238, 242))
    c = dm / 2
    art = space((600, 360)).convert("RGB")
    ship(ImageDraw.Draw(art), 200, 210, 3.6, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(4.0, 6.0, dm - 4.0, c - 6.0)
    mask = Image.new("L", reg.img.size, 0)
    ImageDraw.Draw(mask).ellipse(reg.box(1.0, 1.0, dm - 1.0, dm - 1.0), fill=255)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    reg.img.alpha_composite(layer)
    reg.circle(c, c, 22.0, (210, 212, 218))
    reg.text("ODYSSEY", "ariblk.ttf", 11.0, c, 22.0, (255, 214, 70))
    wiiu_logo(reg, c - 14.0, c + 34.0, 9.0, (40, 160, 220), (238, 238, 242))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (pad(), front(), disc()):
        reg.paste(image)
    for name, picture in (("menu", menu(False)), ("menu_disc", menu(True)), ("title", title()), ("game", game())):
        x, y, w, h = L.REGIONS[name]
        image.paste(picture.resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(image)
    for name, colour in (("dark", (8, 8, 10)), ("blue", BLUE), ("red", (230, 40, 50)), ("matte", (34, 34, 37)),
                         ("silver", (200, 204, 210)), ("white", (244, 244, 246))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "wiiu_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
