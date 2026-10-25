"""The Pokémon mini's printing and screens (pokemini_print.png), for the console theme's model (pokemini.py).

One image, laid out as pokemini_layout.REGIONS says: the front half's face (the frosted clear plastic, its screws, the
board's edge, the wells and rings showing faintly through it, POWER and RESET), the black oval (the Nintendo badge,
Pokémon mini), the LCD five ways, drawn as its 96 x 64 pixels (the clock, Odyssey's title, two moments of its play and
the bump that shakes it), the cartridge's label, the D-pad's arrows, and swatches. Run it with the system Python
(Pillow):

    python tools/console-models/pokemini_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pokemini_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CLEAR = rgb(L.COLOURS["clear"])
WHITE = (240, 240, 242)
YELLOW = (250, 210, 40)

# ---- The LCD: 96 x 64 pixels, a few glyphs, sprites ------------------------------------------------------------------

GLYPHS = {   # 3 x 5
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"], "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"], ":": ["0", "1", "0", "1", "0"], " ": ["000"] * 5,
    "O": ["111", "101", "101", "101", "111"], "D": ["110", "101", "101", "101", "110"],
    "Y": ["101", "101", "010", "010", "010"], "S": ["111", "100", "111", "001", "111"],
    "E": ["111", "100", "110", "100", "111"], "M": ["101", "111", "111", "101", "101"],
    "I": ["111", "010", "010", "010", "111"], "N": ["110", "101", "101", "101", "101"],
    "P": ["111", "101", "111", "100", "100"], "U": ["101", "101", "101", "101", "111"],
    "H": ["101", "101", "111", "101", "101"], "A": ["111", "101", "111", "101", "101"],
    "B": ["110", "101", "110", "101", "110"], "!": ["1", "1", "1", "0", "1"],
}
SHIP = ["110000000000", "011100000000", "011111110000", "111111111110", "011111110000", "011100000000",
        "110000000000"]
ROCK = ["00111100", "01111110", "11101111", "11111111", "11111011", "01111110", "00111100"]


def lcd(draw_fn, inverted=False):
    """The LCD as 96 x 64 pixels: draw_fn(put) puts pixels (x, y, tone: 1 ink, 2 half tone); then scaled into its
    window with a margin, the pixels' faint grid showing."""
    pixels = {}

    def put(x, y, tone=1):
        if 0 <= x < 96 and 0 <= y < 64:
            pixels[(x, y)] = tone

    draw_fn(put)
    w, h = L.SCREEN_PX
    bg, ink, shade = rgb(L.COLOURS["lcd"]), rgb(L.COLOURS["ink"]), rgb(L.COLOURS["shade"])
    if inverted:
        bg, ink = ink, bg
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    s = 2
    x0, y0 = (w - 96 * s) // 2, (h - 64 * s) // 2
    ghost = tuple(round(c * 0.96) for c in bg)
    for y in range(64):
        for x in range(96):
            tone = pixels.get((x, y), 0)
            colour = ink if tone == 1 else shade if tone == 2 else ghost
            d.rectangle([x0 + x * s, y0 + y * s, x0 + x * s + s - 1, y0 + y * s + s - 1], fill=colour)
    return img.filter(ImageFilter.GaussianBlur(0.35))


def text(put, s, x, y, scale=1):
    for c in s:
        rows = GLYPHS[c]
        for j, row in enumerate(rows):
            for i, bit in enumerate(row):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            put(x + i * scale + dx, y + j * scale + dy)
        x += (len(rows[0]) + 1) * scale


def width(s, scale=1):
    return sum((len(GLYPHS[c][0]) + 1) * scale for c in s) - scale


def sprite(put, rows, x, y, tone=1):
    for j, row in enumerate(rows):
        for i, bit in enumerate(row):
            if bit == "1":
                put(x + i, y + j, tone)


def stars(put, seed):
    for k in range(14):
        put((k * 29 + seed * 13) % 96, (k * 17 + seed * 7) % 44 + 10)


def planet(put, cx, cy, r):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - 2 * r, cx + 2 * r + 1):
            d = ((x - cx) / r) ** 2 + ((y - cy) / r) ** 2
            if d <= 1.0:
                put(x, y, 2 if d < 0.8 else 1)
            elif abs(((x - cx) / (1.9 * r)) ** 2 + ((y - cy) / (0.42 * r)) ** 2 - 1.0) < 0.12:
                put(x, y, 1)


def clock_screen(put):
    text(put, "ODYSSEY", (96 - width("ODYSSEY")) // 2, 3)
    t = "12:00"
    text(put, t, (96 - width(t, 3)) // 2, 18, 3)
    sprite(put, SHIP, 10, 46)
    planet(put, 74, 50, 6)


def title_screen(put):
    text(put, "ODYSSEY", (96 - width("ODYSSEY", 2)) // 2, 4, 2)
    text(put, "MINI", (96 - width("MINI")) // 2, 18)
    stars(put, 1)
    sprite(put, SHIP, 20, 30)
    planet(put, 68, 34, 7)
    text(put, "PUSH A", (96 - width("PUSH A")) // 2, 54)


def game_screen(frame):
    def draw(put):
        text(put, "0120" if frame == 0 else "0140", 70, 2)
        for x in range(96):
            put(x, 9)
        stars(put, 2 + frame)
        planet(put, 72, 50, 6)
        sy = 28 if frame == 0 else 22
        sprite(put, SHIP, 8, sy)
        rx = 70 if frame == 0 else 60
        sprite(put, ROCK, rx, 18)
        sprite(put, ROCK, rx + 10, 34)
        if frame == 1:
            for k in range(3):
                for i in range(3):
                    put(24 + k * 8 + i, sy + 3)
    return draw


def hit_screen(put):
    text(put, "BUMP!", (96 - width("BUMP!", 2)) // 2, 10, 2)
    sprite(put, SHIP, 42, 32)
    for k in range(8):
        put(36 + k * 3, 30 - (k % 2) * 3)
        put(36 + k * 3, 42 + (k % 2) * 3)


# ---- The face, the oval, the label, the D-pad ------------------------------------------------------------------------

def face():
    """The front half's face, from in front: x from 30 mm left of its middle, z down from its top (74)."""
    reg = Region(L.REGIONS["face"], 60.0, L.HEIGHT, CLEAR)

    def at(x, z):
        return x + 30.0, L.HEIGHT - z

    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    for y in range(layer.size[1]):
        t = y / layer.size[1]
        d.line([(0, y), (layer.size[0], y)], fill=(255, 255, 255, round(40 * (1 - t))))
    reg.over(layer)
    faint = (150, 168, 186)
    reg.rect_(*at(-26.0, 69.0), *at(26.5, 6.0), None, r=4.0, outline=faint, width=0.5)
    for x, z in ((-23.5, 66.5), (21.0, 67.0), (-24.0, 15.0), (23.5, 8.5)):
        reg.circle(*at(x, z), 2.4, (170, 186, 202), outline=faint, width=0.5)
        reg.circle(*at(x, z), 0.9, (126, 140, 156))
    (dx, dz), well = L.DPAD["at"], L.DPAD["well"]
    reg.circle(*at(dx, dz), well, (176, 192, 208), outline=faint, width=0.5)
    for name in ("a", "b"):
        x, z = L.BUTTONS[name]
        reg.circle(*at(x, z), L.BUTTONS["r"] + 1.2, (176, 192, 208), outline=faint, width=0.5)
    (px, pz), ring = L.POWER["at"], L.POWER["ring"]
    reg.circle(*at(px, pz), ring, (172, 188, 204), outline=faint, width=0.5)
    reg.text("POWER", "arialbd.ttf", 1.5, *at(px, pz + 4.6), (110, 122, 136))
    reg.text("RESET", "arialbd.ttf", 1.5, *at(px, pz - 5.4), (110, 122, 136))
    reg.circle(*at(*L.RESET["at"]), L.RESET["r"], (40, 46, 54))
    (z0, z1) = L.C["z"]
    reg.rect_(*at(25.6, z1), *at(27.4, z0), tuple((a + b) // 2 for a, b in zip(rgb(L.COLOURS["case"]), CLEAR)), r=0.8)
    for k in range(6):
        reg.circle(*at(14.0 + 2.2 * (k % 3), 9.6 + 2.2 * (k // 3)), 0.55, (120, 134, 150))
    return reg


def oval():
    """The black oval, its box's top left at the oval's left and top: the badge, the LCD's frame, the name."""
    (ox, oz), (rx, rz) = L.OVAL["at"], L.OVAL["r"]
    reg = Region(L.REGIONS["oval"], 2 * rx, 2 * rz, CLEAR)

    def at(x, z):
        return x - (ox - rx), (oz + rz) - z

    reg.draw.ellipse(reg.box(0.0, 0.0, 2 * rx, 2 * rz), fill=(18, 18, 20))
    (lx, lz), (lw, lh) = L.LCD["at"], L.LCD["size"]
    reg.rect_(*at(lx - lw / 2, lz + lh / 2), *at(lx + lw / 2, lz - lh / 2), rgb(L.COLOURS["lcd"]))   # the LCD, blank
    (bx, bz), (bw, bh) = L.BADGE["at"], L.BADGE["size"]
    reg.rect_(*at(bx - bw / 2, bz + bh / 2), *at(bx + bw / 2, bz - bh / 2), None, r=bh / 2, outline=WHITE, width=0.3)
    reg.text("Nintendo", "arialbd.ttf", 1.9, *at(bx, bz), WHITE)
    (nx, nz), nw = L.NAME["at"], L.NAME["width"]
    f = ImageFont.truetype(FONTS + "arialbd.ttf", 100)
    first, second = f.getlength("Pokémon "), f.getlength("mini")
    size = 3.0 * nw / ((first + second) / 100 * 3.0 * 1.04)   # the size that makes the pair nw wide
    x0 = nx - nw / 2
    reg.text("Pokémon", "arialbd.ttf", size, *at(x0, nz), WHITE, anchor="lm")
    reg.text("mini", "arialbd.ttf", size, *at(x0 + first / 100 * size * 1.04, nz), YELLOW, anchor="lm")
    return reg


def cart():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["cart"], lw, lh, (20, 20, 26))
    art = space((520, 380)).convert("RGB")
    ship(ImageDraw.Draw(art), 150, 220, 3.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(0.0, 0.0, lw, lh)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 4.2, (246, 246, 248))
    reg.text("Pokémon", "arialbd.ttf", 2.2, 1.2, 2.1, (30, 60, 150), anchor="lm")
    reg.text("mini", "arialbd.ttf", 2.2, 11.0, 2.1, (230, 170, 20), anchor="lm")
    reg.text("ODYSSEY", "ariblk.ttf", 3.6, lw / 2, 9.0, (255, 214, 70))
    return reg


def dpad():
    s = L.DPAD["size"]
    reg = Region(L.REGIONS["dpad"], s, s, rgb(L.COLOURS["key"]))
    dark = (22, 66, 128)
    c, a = s / 2, 1.3
    reg.poly([(c, 1.0), (c - a, 1.0 + a * 1.2), (c + a, 1.0 + a * 1.2)], dark)
    reg.poly([(c, s - 1.0), (c - a, s - 1.0 - a * 1.2), (c + a, s - 1.0 - a * 1.2)], dark)
    reg.poly([(1.0, c), (1.0 + a * 1.2, c - a), (1.0 + a * 1.2, c + a)], dark)
    reg.poly([(s - 1.0, c), (s - 1.0 - a * 1.2, c - a), (s - 1.0 - a * 1.2, c + a)], dark)
    reg.circle(c, c, 1.6, (40, 92, 160))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CLEAR)
    for reg in (face(), oval(), cart(), dpad()):
        reg.paste(image)
    for name, draw_fn, inverted in (("clock", clock_screen, False), ("title", title_screen, False),
                                    ("game_1", game_screen(0), False), ("game_2", game_screen(1), False),
                                    ("hit", hit_screen, True)):
        x, y, w, h = L.REGIONS[name]
        image.paste(lcd(draw_fn, inverted), (x, y))
    d = ImageDraw.Draw(image)
    colours = dict(clear=CLEAR, case=rgb(L.COLOURS["case"]), dark=(16, 16, 18), grey=rgb(L.COLOURS["grey"]),
                   cart=(200, 205, 212))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "pokemini_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
