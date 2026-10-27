"""The MSX turbo R card's printing (msxturbor_print.png), for the console theme's MSX turbo R model (msxturbor.py).

One image, laid out as msxturbor_layout.REGIONS says, each region in millimetres as the model's UVs map it: the whole top
seen from above (the keys' tops, light and mid grey, their legends and kana, the cursor keys' arrows, the MSX VIEW badge;
Panasonic on the deck's front; the rear block's printing: DOUBLE SLOTS and its warning by
slot 1's lid, PERSONAL COMPUTER FS-A1GT, the MSX turbo R mark, RAM512K VRAM128K and the built-in software, FDD moulded
at the right end), the black band along its slope (its ribs; A1GT, the autofire button and rate slider, the built-in
software switch, RESET, PCM, MIDI, MIC, the lights over their names, the power light lit), the 3.5-inch disk's sides (a
made-up game from tools/made-up-games: its key art and logo on the label), and swatches. Make the made-up games' library first
(tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/msxturbor_print.py artifacts/made-up-games <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msxturbor_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
BAND = rgb(L.COLOURS["band"])
INK = (24, 24, 26)
KANA = (60, 58, 56)
WHITE = (236, 236, 232)
GOLD = rgb(L.COLOURS["gold"])
LIT = (255, 60, 40)
UNLIT = (90, 30, 26)
GAME = ("Tidecaller Saga (Europe)", "megadrive")
# The JIS kana on the light keys, after their letters.
KANA_OF = dict(zip("1234567890-^¥QWERTYUIOP@[ASDFGHJKL;:]ZXCVBNM,./_",
                   "ぬふあうえおやゆよわほへーたていすかんなにらせ゛゜ちとしはきくまのりれけむつさそひこみもねるめろ"))


def top_point(x, y):
    """A point of the top (x from the middle, y back from the front) in the top region's millimetres."""
    return x + L.HALF, L.DEPTH - y


def slope_top(points, h=L.KEY_HEIGHT):
    """An (x, s) outline on the deck, raised h off it (to the keys' tops), in the top region's millimetres."""
    return [top_point(x, L.deck_point(s, h)[0]) for x, s in points]


def key_face(reg, outline, colour, h=L.KEY_HEIGHT):
    """A key's top, h off the deck; its box in the region."""
    fill = rgb(L.COLOURS["key_" + colour])
    top = slope_top(L.inset(outline, L.KEY_INSET), h)
    reg.poly(slope_top(L.inset(outline, L.KEY_INSET - 0.6), h), shade(fill, -0.08))
    reg.poly(top, fill)
    xs, ys = [p[0] for p in top], [p[1] for p in top]
    return min(xs), min(ys), max(xs), max(ys)


def legend(reg, text, colour, box):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if text == "SPACE":
        reg.text("SPACE", "arialbd.ttf", 2.4, cx, cy + 2.0, INK)
        return
    if colour == "light" and len(text) == 1:
        reg.text(text, "YuGothB.ttc" if not text.isascii() else "arial.ttf", 4.2, cx - 2.4, cy - 1.8, INK)
        reg.text(KANA_OF.get(text, ""), "YuGothB.ttc", 3.2, cx + 2.6, cy + 2.4, KANA)
        return
    if len(text) == 1:
        reg.text(text, "arial.ttf", 4.2, cx, cy, INK)
        return
    font = "YuGothB.ttc" if not text.isascii() else "arialbd.ttf"
    size = 2.8 if len(text) <= 4 else 2.4 if len(text) <= 5 else 2.0
    reg.text(text, font, size, cx, cy, INK)


def triangle(reg, cx, cy, direction, s):
    shape = [(0.0, -0.45), (0.5, 0.35), (-0.5, 0.35)]
    turn = {"up": 0, "right": 90, "down": 180, "left": 270}[direction]
    c, k = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    reg.poly([(cx + s * (x * c - y * k), cy + s * (x * k + y * c)) for x, y in shape], INK)


def moulded(reg, text, font, size, x, y):
    """Lettering moulded into the case: a shadow, a highlight, the case's grey between."""
    for d, colour in ((0.3, shade(CASE, -0.35)), (-0.3, shade(CASE, 0.25)), (0.0, shade(CASE, -0.05))):
        reg.text(text, font, size, x + d, y + d, colour, anchor="lm")


def keyboard(reg):
    for text, xu, row, wu, colour in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        box = key_face(reg, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], colour)
        legend(reg, text, colour, box)
    box = key_face(reg, L.return_outline(), "dark")
    reg.text("↵", "seguisym.ttf", 7.0, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2 - 1.0, INK)
    reg.text("RETURN", "arialbd.ttf", 2.0, (box[0] + box[2]) / 2, box[3] - 3.0, INK)
    for name in ("up", "down", "left", "right"):
        outline = L.cursor_outline(name)
        key_face(reg, outline, "dark", L.CURSOR["height"])
        cx = sum(x for x, _ in outline) / 4
        cs = sum(s for _, s in outline) / 4
        triangle(reg, *top_point(cx, L.deck_point(cs, L.CURSOR["height"])[0]), name, 5.0)
    # The MSX VIEW badge in the bottom row's place, on the deck.
    (u0, u1), (s0, s1) = L.BADGE, (L.ROW_S[5] + 1.0, L.ROW_S[5] + L.U - 1.0)
    ax, ay = top_point(L.kx(u0), L.deck_point(s1, 0.0)[0])
    bx, by = top_point(L.kx(u1), L.deck_point(s0, 0.0)[0])
    reg.rect_(ax, ay, bx, by, (20, 20, 22), r=1.0)
    reg.text("MSX", "ariblk.ttf", 4.2, ax + 2.0, (ay + by) / 2 - 1.2, WHITE, anchor="lm")
    reg.text("VIEW", "arialbd.ttf", 3.6, ax + 15.0, (ay + by) / 2 - 1.2, WHITE, anchor="lm")
    reg.text("MUSIC AND VISUAL", "arial.ttf", 1.6, ax + 2.0, (ay + by) / 2 + 3.4, WHITE, anchor="lm")




def rear_block(reg):
    """The rear block's top: DOUBLE SLOTS and its warning, slot 1's lid and notch, the model's printing, FDD."""
    reg.text("DOUBLE SLOTS", "arialbd.ttf", 2.6, *top_point(-136.0, 230.3), INK, anchor="lm")
    reg.text("②▶", "seguisym.ttf", 2.8, *top_point(-110.0, 230.3), INK, anchor="lm")
    reg.rect_(*top_point(-136.0, 227.5), *top_point(-130.0, 224.0), INK, r=0.3)
    reg.text("ご注意", "YuGothB.ttc", 1.4, *top_point(-133.0, 225.7), shade(CASE, 0.6))
    reg.text("カートリッジの抜き差しは電源", "YuGothB.ttc", 1.8, *top_point(-128.5, 226.4), INK, anchor="lm")
    reg.text("切の状態で行ってください。", "YuGothB.ttc", 1.8, *top_point(-128.5, 222.9), INK, anchor="lm")
    (lx0, lx1), (ly0, ly1) = L.LID["x"], L.LID["y"]
    reg.rect_(*top_point(lx0 - 1.0, ly1 + 1.0), *top_point(lx1 + 1.0, ly0 - 1.0), shade(CASE, -0.3), r=1.0)
    reg.rect_(*top_point(lx0, ly1), *top_point(lx1, ly0), shade(CASE, 0.04), r=0.8)
    (nx0, nx1), (ny0, ny1) = L.NOTCH["x"], L.NOTCH["y"]
    reg.rect_(*top_point(nx0, ny1), *top_point(nx1, ny0), shade(CASE, -0.3), r=2.0)
    reg.text("PERSONAL COMPUTER FS-A1GT", "arialbd.ttf", 3.0, *top_point(44.0, 227.4), INK, anchor="lm")
    reg.rect_(*top_point(44.0, 225.0), *top_point(56.0, 218.0), INK, r=0.5)
    reg.text("MSX", "ariblk.ttf", 3.0, *top_point(50.0, 222.6), WHITE)
    reg.text("turbo", "arialbd.ttf", 1.4, *top_point(50.0, 219.4), WHITE)
    reg.rect_(*top_point(56.8, 225.0), *top_point(63.4, 218.0), INK, r=0.5)
    reg.text("R", "ariblk.ttf", 5.4, *top_point(60.1, 221.4), WHITE)
    reg.text("RAM512K", "arialbd.ttf", 2.0, *top_point(65.0, 223.2), INK, anchor="lm")
    reg.text("VRAM128K", "arialbd.ttf", 2.0, *top_point(65.0, 219.6), INK, anchor="lm")
    for k, line in enumerate(("■ MIDI INTERFACE", "■ MSX VIEW SOFT", "■ COLOR WORD PROCESSOR")):
        reg.text(line, "arialbd.ttf", 1.9, *top_point(83.0, 225.0 - 3.5 * k), INK, anchor="lm")
    moulded(reg, "FDD", "arialbd.ttf", 8.0, *top_point(140.0, 221.0))
    moulded(reg, "▷", "seguisym.ttf", 8.0, *top_point(158.0, 221.0))


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, CASE)
    keyboard(reg)
    reg.text("Panasonic", "arialbd.ttf", 5.4, *top_point(-7.0, 17.5), GOLD)
    rear_block(reg)
    return reg


def band():
    """The black band along its slope: x across, b down from its top (BAND_LENGTH) to its foot."""
    w, h = L.WIDTH, L.BAND_LENGTH
    reg = Region(L.REGIONS["band"], w, h, BAND)

    def at(x, b):
        return x + L.HALF, h - b
    # The ribs along the upper half.
    (r0, r1), n = L.RIBS["b"], L.RIBS["count"]
    for k in range(n):
        x0, x1 = -L.HALF + w * k / n, -L.HALF + w * (k + 1) / n
        reg.rect_(*at(x0 + 0.7, r1), *at(x1 - 0.7, r0), shade(BAND, 0.14), r=1.2)
        reg.rect_(*at(x0 + 0.7, r1), *at(x1 - 0.7, r1 - 1.2), shade(BAND, 0.3), r=0.6)
    # A1GT: the A1 in blue italics, the GT in gold.
    reg.text("A1", "arialbi.ttf", 11.0, *at(-186.0, 11.5), rgb(L.COLOURS["blue"]), anchor="lm")
    f = ImageFont.truetype(FONTS + "ariblk.ttf", round(15.0 * reg.sx))
    reg.draw.text(reg.p(*at(-171.5, 11.5)), "GT", font=f, fill=shade(GOLD, -0.3), anchor="lm",
                  stroke_width=max(1, round(0.7 * reg.sx)), stroke_fill=GOLD)
    # The autofire button's light and the rate slider: its track, its scale.
    reg.circle(*at(-111.5, 16.0), 1.0, UNLIT)
    reg.text("連射", "YuGothB.ttc", 2.0, *at(-111.5, 8.0), WHITE)
    (sx0, sx1), (sb0, sb1) = L.SLIDER["x"], L.SLIDER["b"]
    reg.rect_(*at(sx0, sb1), *at(sx1, sb0), (8, 8, 8), r=0.8)
    reg.text("切", "YuGothB.ttc", 2.0, *at(sx0 + 2.5, sb1 + 4.0), WHITE)
    for k in range(8):
        x = sx0 + 6.0 + 2.0 * k
        reg.rect_(*at(x - 0.2, sb1 + 1.2 + 0.25 * k), *at(x + 0.2, sb1 + 1.0), WHITE)
    reg.text("遅い", "YuGothB.ttc", 2.0, *at(sx1 - 15.0, sb1 + 4.0), WHITE)
    reg.text("連射速度", "YuGothB.ttc", 2.0, *at(sx1 - 5.0, sb1 + 4.0), WHITE)
    # The built-in software switch, RESET's name and its button's place, the dark panel.
    reg.text("内蔵ソフト 入 切", "YuGothB.ttc", 2.0, *at(-37.0, 16.0), WHITE)
    reg.rect_(*at(-27.0, 11.0), *at(-16.3, 4.0), (8, 8, 8), r=0.6)
    reg.rect_(*at(-26.2, 10.2), *at(-22.0, 4.8), (96, 98, 100), r=0.4)
    reg.text("リセット", "YuGothB.ttc", 2.0, *at(-12.5, 16.0), WHITE)
    (rx0, rx1), (rb0, rb1) = L.RESET["x"], L.RESET["b"]
    reg.rect_(*at(rx0, rb1), *at(rx1, rb0), (150, 150, 146), r=0.4)
    reg.rect_(*at(3.2, 21.0), *at(15.6, 4.0), (6, 6, 6), r=0.6, outline=(70, 70, 70), width=0.3)
    # PCM, MIDI, MIC.
    reg.rect_(*at(21.0, 16.5), *at(25.5, 11.0), BAND, outline=WHITE, width=0.3)
    reg.text("♪", "seguisym.ttf", 3.6, *at(23.25, 13.8), WHITE)
    reg.text("PCM", "arial.ttf", 4.0, *at(26.0, 13.8), WHITE, anchor="lm")
    reg.text("MSX-MUSIC", "arial.ttf", 1.4, *at(31.0, 9.0), WHITE)
    reg.text("MIDI", "ariblk.ttf", 4.6, *at(52.0, 13.0), rgb(L.COLOURS["teal"]))
    reg.circle(*at(68.5, 15.0), 1.0, (4, 4, 4))
    reg.text("MIC", "arialbd.ttf", 1.8, *at(68.5, 10.0), WHITE)
    # The lights over their names: the power light lit.
    lw, lh = L.LIGHTS["size"]
    bw, b0, b1 = L.LIGHTS["label"]
    for k, (x, name) in enumerate(zip(L.LIGHTS["x"], L.LIGHT_NAMES)):
        reg.rect_(*at(x - bw / 2, b1), *at(x + bw / 2, b0), rgb(L.COLOURS["lavender"]), r=0.4)
        reg.text(name, "YuGothB.ttc" if not name.isascii() else "arialbd.ttf", 2.0 if len(name) <= 5 else 1.5,
                 *at(x, (b0 + b1) / 2), (40, 40, 90))
        lx, lb = x + L.LIGHTS["at"], L.LIGHTS["b"]
        if k == 0:
            reg.circle(*at(lx, lb), 2.2, (120, 30, 22))
        reg.rect_(*at(lx - lw / 2, lb + lh / 2), *at(lx + lw / 2, lb - lh / 2), LIT if k == 0 else UNLIT, r=0.5)
    return reg


def disk_side(made_up, back=False):
    w, length = L.DISK["size"]
    reg = Region(L.REGIONS["disk_bottom" if back else "disk_top"], w, length, (36, 38, 44))
    reg.rect_(18.0, 0.0, w - 18.0, 30.0, (178, 182, 186))
    reg.rect_(w / 2 + 4.0, 4.0, w / 2 + 14.0, 26.0, (40, 40, 44))
    if not back:                                           # the label: the game's key art, its logo over it
        game = S.made_up(*GAME, made_up)
        a, b, c, d = reg.box(6.0, 36.0, w - 6.0, length - 6.0)
        size = (round(c - a), round(d - b))
        label = ImageOps.fit(game.keyart, size, Image.LANCZOS, centering=(0.5, 0.35))
        logo = game.logo.copy()
        logo.thumbnail((round(size[0] * 0.86), round(size[1] * 0.4)), Image.LANCZOS)
        label.paste(logo, ((size[0] - logo.width) // 2, size[1] - logo.height - round(size[1] * 0.06)), logo)
        reg.img.paste(label, (round(a), round(b)))
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), band(), disk_side(made_up), disk_side(made_up, back=True)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(red=LIT, green=(80, 230, 90), black=(16, 16, 18), band=BAND, case=CASE,
                   key_light=rgb(L.COLOURS["key_light"]))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "msxturbor_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
