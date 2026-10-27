"""The Casio PV-1000 card's printing (pv1000_print.png), for the console theme's PV-1000 model (pv1000.py).

One image, laid out as pv1000_layout.REGIONS says, each region in millimetres as the model's UVs map it: the console's
top seen from above (the slot's light lip, ▲ and USE GAME PACK GPA-100 SERIES in its recess; PV-1000 in outlined aqua
over its dot screen and CASIO in white at the front right; the power light and POWER), the game pack's label (a made-up
arcade game from tools/made-up-games, ported as the PV-1000's games were: CASIO, its painting and logo on the blue, the
red band, its catalogue number and the warning on the white panel) and its end label (the logo, the series number), the
joystick's top in its own frame (START, SELECT, the label plate, CASIO TJ-1, the emblem), and swatches. Make the
made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/pv1000_print.py artifacts/made-up-games <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pv1000_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
JOY = rgb(L.COLOURS["joy"])
AQUA = rgb(L.COLOURS["aqua"])
BLUE = rgb(L.COLOURS["blue"])
WHITE = (236, 242, 250)
INK = (20, 20, 24)
GAME = ("musemyhm", "arcade")            # a made-up arcade game of 1982, ported as the PV-1000's games were
NUMBER = "GPA-120"                       # past the real series' numbers


def top_point(x, y):
    return x + L.HALF, L.DEPTH - y


def outlined(reg, text, font, size, x, y, fill, ink, stroke, anchor="rs"):
    f = ImageFont.truetype(FONTS + font, max(1, round(size * reg.sx)))
    reg.draw.text(reg.p(x, y), text, font=f, fill=fill, anchor=anchor, stroke_width=max(1, round(stroke * reg.sx)),
                  stroke_fill=ink)


def top():
    """The console's top: x across, y down from its back edge to its front."""
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)
    s = L.SLOT
    w, o0, o1 = s["opening"]
    reg.rect_(*top_point(-s["x"], s["y"][1]), *top_point(s["x"], o1), rgb(L.COLOURS["lip"]))
    reg.rect_(*top_point(-s["x"] + 1.0, s["y"][1] - 0.4), *top_point(s["x"] - 1.0, s["y"][1] - 1.0),
              shade(rgb(L.COLOURS["lip"]), 0.35))
    reg.text("▲", "seguisym.ttf", 1.8, *top_point(0.0, o0 - 1.6), WHITE)
    reg.text("USE GAME PACK GPA-100 SERIES", "arialbd.ttf", 2.0, *top_point(0.0, s["y"][0] + 2.6), WHITE)
    # PV-1000 over its dot screen, CASIO under it.
    outlined(reg, "PV-1000", "arial.ttf", 12.6, *top_point(118.0, 30.0), CASE, AQUA, 0.32)
    for row in range(3):
        for k in range(26):
            reg.circle(*top_point(64.0 + 1.25 * k, 24.6 - 1.15 * row), 0.32, AQUA)
    reg.text("CASIO", "ariblk.ttf", 6.6, *top_point(118.0, 17.6), WHITE, anchor="rs")
    reg.circle(*top_point(L.LIGHT["x"], L.LIGHT["y"]), L.LIGHT["r"], (70, 20, 24))
    reg.text("POWER", "arialbd.ttf", 1.7, *top_point(L.LIGHT["x"], L.LIGHT["y"] - 3.4), WHITE)
    return reg


def logo_fit(game, w, h):
    k = min(w / game.logo.width, h / game.logo.height)
    return game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)


def cart_front(game):
    """The game pack's face: x across, y down from its top end."""
    cw, ch, _ = L.CART["size"]
    reg = Region(L.REGIONS["cart_front"], cw, ch, rgb(L.COLOURS["cart"]))
    reg.rect_(2.0, 1.0, cw - 2.0, ch - 1.5, BLUE)
    reg.text("CASIO", "ariblk.ttf", 5.2, cw / 2, 5.0, WHITE)
    a, b, c, d = reg.box(4.0, 9.0, cw - 4.0, 41.0)
    reg.img.paste(ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.4)),
                  (round(a), round(b)))
    logo = logo_fit(game, (c - a) * 0.84, (d - b) * 0.42)
    reg.img.alpha_composite(logo, (round((a + c - logo.width) / 2), round(b + (d - b) * 0.05)))
    reg.text(f"© {game.year} {game.publisher.upper()}", "arialbd.ttf", 1.6, cw - 5.0, 43.0, WHITE, anchor="rm")
    reg.rect_(2.0, 44.6, cw - 2.0, 50.2, (243, 0, 0))
    reg.text("PV-1000専用ゲームカートリッジ", "YuGothB.ttc", 3.0, 8.0, 47.4, WHITE, anchor="lm")
    reg.rect_(cw - 24.0, 44.6, cw - 2.0, 55.0, WHITE)
    reg.text("手 前", "YuGothB.ttc", 3.6, cw - 13.0, 48.2, (243, 0, 0))
    reg.rect_(2.0, 50.2, cw - 24.0, ch - 1.5, WHITE)
    reg.rect_(cw - 24.0, 55.0, cw - 2.0, ch - 1.5, WHITE)
    reg.text(NUMBER, "ariblk.ttf", 3.4, cw / 2 - 12.0, 53.4, INK)
    reg.text("ご注意…PV-1000にはPV-1000専用ゲーム・カートリッジを使用してください。", "YuGothB.ttc", 1.7, 6.0, 59.6,
             INK, anchor="lm")
    reg.text("故障の原因となりますので、電源を切ってから抜き差ししてください。", "YuGothB.ttc", 1.7, 6.0, 62.6,
             INK, anchor="lm")
    return reg


def cart_top(game):
    """The game pack's top end, the end label seen above the slot: x across, y down from its back edge."""
    cw, _, t = L.CART["size"]
    reg = Region(L.REGIONS["cart_top"], cw, t, rgb(L.COLOURS["cart"]))
    reg.rect_(3.0, 1.2, cw - 3.0, t - 1.2, BLUE)
    a, b, c, d = reg.box(6.0, 2.2, cw - 22.0, t - 2.2)
    logo = logo_fit(game, c - a, d - b)
    reg.img.alpha_composite(logo, (round((a + c - logo.width) / 2), round((b + d - logo.height) / 2)))
    reg.rect_(cw - 17.0, 3.2, cw - 7.0, t - 3.2, WHITE, outline=INK, width=0.4)
    reg.text("20", "ariblk.ttf", 6.0, cw - 12.0, t / 2, (243, 0, 0))
    return reg


def joy_top():
    """The joystick's top in its own frame: x across, y from the stick's end (-r) to the flat end."""
    r = L.JOY["r"]
    reg = Region(L.REGIONS["joy_top"], 2 * r, L.JOY["length"], JOY)

    def at(x, y):
        return x + r, y + r
    for name, (x, y) in (("start", L.BUTTONS["start"]), ("select", L.BUTTONS["select"])):
        reg.circle(*at(x, y), L.BUTTONS["r"] + 1.0, shade(JOY, -0.3))
        reg.text(name.upper(), "arialbd.ttf", 1.8, *at(x, y - L.BUTTONS["r"] - 3.0), WHITE)
    px, (py0, py1) = L.PLATE["x"], L.PLATE["y"]
    reg.rect_(*at(-px, py0), *at(px, py1), rgb(L.COLOURS["plate"]), r=0.6)
    reg.text("CASIO  TJ-1", "arialbd.ttf", 2.6, *at(4.0, py1 + 3.4), WHITE)
    cx, cy = at(-23.0, (py0 + py1) / 2)                     # the emblem: a starburst, an 8 in it
    for k in range(8):
        a = math.pi * k / 4
        reg.line([(cx + 1.4 * math.cos(a), cy + 1.4 * math.sin(a)), (cx + 3.6 * math.cos(a), cy + 3.6 * math.sin(a))],
                 WHITE, 0.6)
    reg.text("8", "arialbd.ttf", 2.0, cx, cy, WHITE)
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*GAME, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), cart_front(game), cart_top(game), joy_top()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, joy=JOY, red=rgb(L.COLOURS["red"]), lit=(255, 52, 40), plate=rgb(L.COLOURS["plate"]),
                   lip=rgb(L.COLOURS["lip"]), cart=rgb(L.COLOURS["cart"]), button=rgb(L.COLOURS["button"]),
                   metal=(138, 141, 146))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "pv1000_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
