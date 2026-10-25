"""The Philips VG-8020's printing, for the console theme's MSX model (tools/console-models/msx.py).

Draws its atlas, its regions as msx_layout.py places them, each in millimetres as the model's planar UVs map it: the
whole top seen from above (each key's top in its colour with its legend, the cursor keys' red arrows, the raised
back's silver with Philips's shield, PHILIPS, the memory's lettering, the MSX badge, the rule and the lights' windows,
and the black lid with VG-8020 HOME COMPUTER in red); the joystick recess's back face (its two ports, HAND CONTROL);
the cartridge's label (a made-up game, Odyssey); the power switch's face; and the swatches small parts take their
colour from. Run it with the system Python (Pillow):

    python tools/console-models/msx_print.py <out folder>

It writes msx_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msx_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

DECK = rgb(L.COLOURS["deck"])
SILVER = rgb(L.COLOURS["silver"])
BLACK = rgb(L.COLOURS["black"])
RED = (226, 44, 44)
ARROW = (232, 52, 40)
INK = (34, 34, 36)
DARK_LEGEND = (36, 36, 38)
LIGHT_LEGEND = (236, 236, 232)


def top_point(x, y):
    """A point of the top (x from the middle, y back from the front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


def slope_top(points, h=L.KEY_HEIGHT):
    """An (x, s) outline on the deck, raised h off it (to the keys' tops), in the top region's millimetres."""
    return [top_point(x, L.deck_point(s, h)[0]) for x, s in points]


# ---- The keys ----------------------------------------------------------------------------------------------------------

def key_face(reg, outline, colour, h=L.KEY_HEIGHT):
    """A key's top, h off the deck: its colour, a slightly lighter middle (the dished face)."""
    fill = rgb(L.COLOURS["top_light" if colour == "light" else "top_dark"])
    top = slope_top(L.inset(outline, L.KEY_INSET), h)
    reg.poly(slope_top(L.inset(outline, L.KEY_INSET - 0.6), h), fill)
    reg.poly(slope_top(L.inset(outline, L.KEY_INSET + 1.0), h), shade(fill, 0.06))
    xs, ys = [p[0] for p in top], [p[1] for p in top]
    return min(xs), min(ys), max(xs), max(ys)


def legend(reg, name, text, colour, box):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ink = DARK_LEGEND if colour == "light" else LIGHT_LEGEND
    lines = text.split("\n")
    if colour == "light":
        if len(lines) == 1:
            reg.text(text, "arial.ttf", 4.6, cx, cy + 0.2, ink)
        else:
            for k, line in enumerate(lines):
                reg.text(line, "arial.ttf", 3.0, cx, cy - 2.1 + 4.2 * k, ink)
        return
    font = "seguisym.ttf" if not text.isascii() else "arial.ttf"
    if text in ("↑", "⇧"):
        reg.text(text, "seguisym.ttf", 4.4, cx, cy, ink)
        if text == "⇧":
            reg.circle(cx, cy, 2.9, outline=ink, width=0.35)
        return
    size = 2.5 if max(len(line) for line in lines) > 3 else 2.8
    if name in ("f1", "f2", "f3", "f4", "f5", "select", "stop"):
        size = 2.9
    for k, line in enumerate(lines):
        reg.text(line, "seguisym.ttf" if not line.isascii() else font, size,
                 cx, cy + (k - (len(lines) - 1) / 2) * (size + 0.9), ink)


def arrow(reg, cx, cy, direction, s):
    """A cursor key's red arrow: a broad head on a short stem, pointing its way, s long."""
    shape = [(0.0, -0.5), (0.5, 0.02), (0.2, 0.02), (0.2, 0.5), (-0.2, 0.5), (-0.2, 0.02), (-0.5, 0.02)]   # up
    turn = {"up": 0, "right": 90, "down": 180, "left": 270}[direction]
    c, k = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    reg.poly([(cx + s * (x * c - y * k), cy + s * (x * k + y * c)) for x, y in shape], ARROW)


def keys(reg):
    for name, xu, row, wu, colour, text in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        box = key_face(reg, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], colour)
        if text:
            legend(reg, name, text, colour, box)
    x0, y0, x1, y1 = key_face(reg, L.return_outline(), "dark")
    lx = (L.kx(L.RETURN["bottom"][0]) + L.kx(L.RETURN["bottom"][1])) / 2
    _, ly = top_point(0.0, L.deck_point(L.ROW_S[3] + L.U * 0.5, L.KEY_HEIGHT)[0])
    reg.text("RETURN", "arial.ttf", 2.4, top_point(lx, 0.0)[0], ly - 1.6, LIGHT_LEGEND)
    reg.text("↵", "seguisym.ttf", 4.0, top_point(lx, 0.0)[0], ly + 1.8, LIGHT_LEGEND)

    # The cursor keys round their square, the square a dark plug.
    for name in ("up", "down", "left", "right"):
        outline = L.cursor_outline(name)
        key_face(reg, outline, "dark", L.CURSOR["height"])
        cx = sum(x for x, _ in outline) / 4
        cs = sum(s for _, s in outline) / 4
        ax, ay = top_point(cx, L.deck_point(cs, L.CURSOR["height"])[0])
        arrow(reg, ax, ay, name, 5.4)
    mx, ms = L.cursor_middle()
    iw, idp = L.CURSOR["inner"]
    square = [(mx - iw / 2, ms - idp / 2), (mx + iw / 2, ms - idp / 2), (mx + iw / 2, ms + idp / 2),
              (mx - iw / 2, ms + idp / 2)]
    reg.poly(slope_top(L.inset(square, 1.4), L.CURSOR["height"] - 2.0), shade(DECK, 0.05))


# ---- The raised back -------------------------------------------------------------------------------------------------

def shield(reg, x, y, h, colour):
    """Philips's shield, h tall, its middle at (x, y): its outline, three waves across it, four stars round them."""
    w = h * 0.78
    top, bottom = y - h / 2, y + h / 2
    outline = [(x - w / 2, top), (x + w / 2, top), (x + w / 2, y + 0.05 * h)]
    for k in range(9):
        a = math.radians(k * 22.5)
        outline.append((x + w / 2 * math.cos(a), y + 0.05 * h + (bottom - y - 0.05 * h) * math.sin(a)))
    reg.line(outline + [(x - w / 2, top)], colour, 0.32)
    for k in range(3):
        wy = y - 0.1 * h + k * 0.17 * h
        reg.line([(x - w * 0.42 + w * 0.84 * t / 12, wy + 0.05 * h * math.sin(t / 12 * 2 * math.pi)) for t in range(13)],
                 colour, 0.28)
    for sx, sy in ((-0.22, -0.3), (0.22, -0.3), (-0.2, 0.3), (0.2, 0.3)):
        reg.circle(x + sx * w, y + sy * h, 0.05 * h, colour)


def msx_badge(reg, x0, y0, x1, y1):
    """The MSX badge: the letters in white, in a black box with a fine white rim."""
    reg.rect_(x0, y0, x1, y1, (20, 20, 22), r=0.3)
    reg.rect_(x0 + 0.35, y0 + 0.35, x1 - 0.35, y1 - 0.35, (20, 20, 22), r=0.2, outline=(236, 236, 236), width=0.2)
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONTS + "ariblk.ttf", max(1, round((y1 - y0) * 0.86 * reg.sx)))
    d.text(reg.p((x0 + x1) / 2, (y0 + y1) / 2 + 0.1), "MSX", font=f, fill=(240, 240, 240, 255), anchor="mm")
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.18, -0.18 * reg.p(0, (y0 + y1) / 2)[1], 0, 1, 0)))


def window(reg, x, y, colour):
    w, d = L.LIGHTS["size"]
    reg.rect_(x - w / 2 - 0.3, y - d / 2 - 0.3, x + w / 2 + 0.3, y + d / 2 + 0.3, shade(SILVER, -0.45), r=0.3)
    reg.rect_(x - w / 2, y - d / 2, x + w / 2, y + d / 2, colour, r=0.2)


def raised_back(reg):
    (bx0, by), (bx1, _) = top_point(-L.WIDTH / 2, L.DEPTH), top_point(L.WIDTH / 2, 0.0)
    _, by1 = top_point(0.0, L.BACK_Y)
    reg.rect_(bx0, by, bx1, by1, SILVER)
    for k in range(60):                                   # a faint brushed grain along it
        y = by + (by1 - by) * (k + 0.5) / 60
        reg.line([(bx0, y), (bx1, y)], shade(SILVER, 0.05 if k % 2 else -0.04), 0.25)

    shield(reg, *top_point(L.SHIELD["x"], L.SHIELD["y"]), L.SHIELD["height"], (126, 128, 130))
    px, py = top_point(L.PHILIPS["x"], L.PHILIPS["y"])
    reg.text("PHILIPS", "arialbd.ttf", L.PHILIPS["height"] * 1.38, px, py, INK, anchor="lm")
    for line, y in zip(L.LETTERING["lines"], L.LETTERING["y"]):
        lx, ly = top_point(L.LETTERING["x"], y)
        reg.text(line, "arial.ttf", L.LETTERING["height"] * 1.3, lx, ly, INK, anchor="lm")
    (mx0, my0), (mx1, my1) = top_point(L.MSX_BADGE["x"][0], L.MSX_BADGE["y"][1]), top_point(L.MSX_BADGE["x"][1],
                                                                                              L.MSX_BADGE["y"][0])
    msx_badge(reg, mx0, my0, mx1, my1)
    (rx0, ry), (rx1, _) = top_point(L.RULE["x"][0], L.RULE["y"]), top_point(L.RULE["x"][1], L.RULE["y"])
    reg.line([(rx0, ry), (rx1, ry)], INK, 0.3)
    for name, colour in (("power", (92, 24, 22)), ("caps", (24, 70, 32))):
        x, y = top_point(*L.LIGHTS[name])
        window(reg, x, y, colour)
        reg.text(name.upper(), "arial.ttf", 1.9, x, top_point(0.0, L.LIGHTS["names"])[1], INK)

    # The lid: black, VG-8020 HOME COMPUTER in red at its front right, a red rule along under it.
    (lx0, ly0), (lx1, ly1) = top_point(L.LID["x"][0], L.DEPTH), top_point(L.LID["x"][1], L.BACK_Y)
    reg.rect_(lx0, ly0, lx1, ly1, BLACK)
    sheen = reg.layer()
    ImageDraw.Draw(sheen).polygon([reg.p(lx0 + 10, ly0), reg.p(lx0 + 40, ly0), reg.p(lx0 + 22, ly1), reg.p(lx0 - 8, ly1)],
                                  fill=(255, 255, 255, 14))
    reg.over(sheen)
    p = L.LID_PRINT
    tx, ty = top_point(p["x"], p["y"])
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(p["height"] * 1.38 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(tx, ty), "VG-8020", font=f, fill=RED + (255,), anchor="rm")
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.16, -0.16 * reg.p(0, ty)[1], 0, 1, 0)))
    (ax, ay), (cx, _) = top_point(p["rule"][0], p["rule"][1]), top_point(p["x"], p["rule"][1])
    reg.line([(ax, ay), (cx, ay)], RED, 0.35)
    for word, y in zip(("HOME", "COMPUTER"), p["lines"]):
        reg.text(word, "arial.ttf", p["small"] * 1.3, tx, top_point(0.0, y)[1], RED, anchor="rm")


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, DECK)
    raised_back(reg)
    keys(reg)
    return reg


# ---- The joystick ports, the label, the switch -------------------------------------------------------------------------

def ports():
    (x0, x1), (z0, z1) = L.PORTS["x"], L.PORTS["z"]
    w, h = x1 - x0, z1 - z0
    base = rgb(L.COLOURS["base"])
    reg = Region(L.REGIONS["ports"], w, h, shade(base, -0.08))
    pw, ph = L.PORTS["port"]
    cy = z1 - L.PORTS["port_z"]
    for k, x in enumerate(L.PORTS["at"]):
        cx = x - x0
        reg.rect_(cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2, (30, 30, 32), r=0.6)
        shell = [(cx - 8.2, cy - 3.6), (cx + 8.2, cy - 3.6), (cx + 6.9, cy + 3.6), (cx - 6.9, cy + 3.6)]
        reg.poly(shell, (96, 96, 100))
        reg.poly([(px + (0.6 if px < cx else -0.6), py + (0.5 if py < cy else -0.5)) for px, py in shell], (14, 14, 16))
        for j in range(5):
            reg.circle(cx - 5.4 + 2.7 * j, cy - 1.3, 0.55, (176, 160, 110))
        for j in range(4):
            reg.circle(cx - 4.05 + 2.7 * j, cy + 1.4, 0.55, (176, 160, 110))
        reg.text(str(k + 1), "arial.ttf", 2.6, cx - 16.0 if k == 0 else cx + 16.0, h - 4.0, shade(base, -0.45))
    reg.text("HAND CONTROL", "arial.ttf", 2.6, w / 2, h - 4.0, shade(base, -0.45))
    return reg


def label():
    lw, lh = L.CART["label"]
    reg = Region(L.REGIONS["label"], lw, lh, (244, 242, 236))
    art = space((660, 520))
    d = ImageDraw.Draw(art)
    ship(d, 230, 300, 3.2, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(2.0, 16.0, lw - 2.0, lh - 2.0)
    reg.img.paste(art.convert("RGB").resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(0.0, 0.0, lw, 14.0, (206, 34, 40))
    reg.text("ODYSSEY", "arialbi.ttf", 9.6, lw / 2, 7.4, (255, 250, 236))
    msx_badge(reg, lw - 16.0, lh - 9.0, lw - 4.0, lh - 4.0)
    reg.text("ROM", "arialbd.ttf", 3.2, 6.0, lh - 6.5, (255, 255, 255), anchor="lm")
    return reg


def rocker():
    w, h = L.SWITCH["y"][1] - L.SWITCH["y"][0], L.SWITCH["z"][1] - L.SWITCH["z"][0]
    reg = Region(L.REGIONS["rocker"], w, h, (14, 14, 16))
    reg.rect_(1.6, 1.6, w - 1.6, h - 1.6, (30, 30, 33), r=0.8)
    reg.rect_(w / 2 - 0.15, 2.0, w / 2 + 0.15, h - 2.0, (10, 10, 12))
    reg.circle(4.0, h / 2, 1.2, outline=(214, 214, 214), width=0.35)
    reg.rect_(w - 4.2, h / 2 - 1.4, w - 3.8, h / 2 + 1.4, (214, 214, 214))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), DECK)
    for reg in (top(), ports(), label(), rocker()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", (255, 64, 48)), ("green", (96, 255, 120)), ("black", BLACK), ("red_off", (92, 24, 22)),
                         ("green_off", (24, 70, 32))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "msx_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
