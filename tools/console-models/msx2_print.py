"""The Philips VG-8235's printing, for the console theme's MSX2 model (tools/console-models/msx2.py).

Draws its atlas, its regions as msx2_layout.py places them, each in millimetres as the model's planar UVs map it: the
whole top seen from above (each key's top in its colour with its legend, the cursor keys' salmon triangles, the deck's
ribbed grips, LOCK slots and labels and the handle's groove; the main unit's anthracite with RESET, the lights'
windows and names, the cartridge slot's cover, PHILIPS, VG-8235, the memory's lettering, the MSX2 badge, Philips's
shield and New Media Systems with its puzzle piece); the main unit's right end (the joystick ports under the drive's
bezel); the 3.5-inch disk's two sides (a made-up game, Odyssey); and the swatches small parts take their colour from.
Run it with the system Python (Pillow):

    python tools/console-models/msx2_print.py <out folder>

It writes msx2_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msx2_layout as L  # noqa: E402
from msx_print import msx_badge, shield  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

DECK = rgb(L.COLOURS["deck"])
CASE = rgb(L.COLOURS["case"])
BLACK = rgb(L.COLOURS["black"])
SALMON = (236, 128, 104)
WHITE = (232, 232, 228)
DARK_LEGEND = (40, 40, 42)
LIGHT_LEGEND = (236, 236, 232)


def top_point(x, y):
    """A point of the top (x from the middle, y back from the front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


def slope_top(points, h=L.KEY_HEIGHT):
    """An (x, s) outline on the deck, raised h off it (to the keys' tops), in the top region's millimetres."""
    return [top_point(x, L.deck_point(s, h)[0]) for x, s in points]


def rect_top(reg, x0, y0, x1, y1, fill, r=0.0, **extra):
    """A rectangle of the top, given by its plan corners."""
    (a, b), (c, d) = top_point(x0, y1), top_point(x1, y0)
    reg.rect_(a, b, c, d, fill, r=r, **extra)


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
    if name in ("f1", "f2", "f3", "f4", "f5", "select", "stop", "home", "ins", "del"):
        reg.text(text, "arial.ttf", 2.6, cx, cy, ink)
        return
    if colour == "light":
        if len(lines) == 1:
            reg.text(text, "arial.ttf", 4.6, cx, cy + 0.2, ink)
        else:
            for k, line in enumerate(lines):
                reg.text(line, "arial.ttf", 3.0, cx, cy - 2.1 + 4.2 * k, ink)
        return
    if text in ("↑", "⇧"):
        reg.text(text, "seguisym.ttf", 4.4, cx, cy, ink)
        if text == "⇧":
            reg.circle(cx, cy, 2.9, outline=ink, width=0.35)
        return
    size = 2.5 if max(len(line) for line in lines) > 3 else 2.8
    for k, line in enumerate(lines):
        reg.text(line, "seguisym.ttf" if not line.isascii() else "arial.ttf", size,
                 cx, cy + (k - (len(lines) - 1) / 2) * (size + 0.9), ink)


def triangle(reg, cx, cy, direction, s):
    """A cursor key's salmon triangle, outlined, pointing its way, s across."""
    shape = [(0.0, -0.45), (0.5, 0.35), (-0.5, 0.35)]                       # up
    turn = {"up": 0, "right": 90, "down": 180, "left": 270}[direction]
    c, k = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    points = [(cx + s * (x * c - y * k), cy + s * (x * k + y * c)) for x, y in shape]
    reg.line(points + points[:1], SALMON, 0.55)


def keys(reg):
    for name, xu, row, wu, colour, text in L.KEYS:
        x0, s0, x1, s1 = L.key_rect(xu, row, wu)
        box = key_face(reg, [(x0, s0), (x1, s0), (x1, s1), (x0, s1)], colour)
        if text:
            legend(reg, name, text, colour, box)
    key_face(reg, L.return_outline(), "dark")
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
        triangle(reg, ax, ay, name, 6.0)
    mx, ms = L.cursor_middle()
    iw, idp = L.CURSOR["inner"]
    square = [(mx - iw / 2, ms - idp / 2), (mx + iw / 2, ms - idp / 2), (mx + iw / 2, ms + idp / 2),
              (mx - iw / 2, ms + idp / 2)]
    reg.poly(slope_top(L.inset(square, 1.4), L.CURSOR["height"] - 2.0), shade(BLACK, 0.12))


# ---- The deck ----------------------------------------------------------------------------------------------------------

def deck(reg):
    (s0, s1) = L.GRIPS["s"]
    for x0, x1 in L.GRIPS["x"]:                              # the grips: fine ribs across them
        s = s0
        while s < s1:
            pts = slope_top([(x0, s), (x1, s), (x1, s + L.GRIPS["pitch"] / 2), (x0, s + L.GRIPS["pitch"] / 2)], 0.0)
            reg.poly(pts, shade(DECK, -0.22))
            s += L.GRIPS["pitch"]
    (ls0, ls1) = L.LOCKS["s"]
    for x0, x1 in L.LOCKS["x"]:                              # the LOCK slots, and their names over them
        reg.poly(slope_top([(x0, ls0), (x1, ls0), (x1, ls1), (x0, ls1)], 0.0), BLACK)
        tx, ty = top_point((x0 + x1) / 2, L.deck_point(L.LOCKS["label"], 0.0)[0])
        reg.text("LOCK", "arial.ttf", 2.2, tx, ty, SALMON)
    (hx0, hx1), (hy0, hy1) = L.HANDLE["x"], L.HANDLE["y"]   # the handle's groove: a brighter sheen along it
    (a, b), (c, d) = top_point(hx0, hy1), top_point(hx1, hy0)
    reg.rect_(a, b, c, d, shade(DECK, 0.12), r=(hy1 - hy0) / 2)
    reg.rect_(a + 4.0, b + (d - b) * 0.55, c - 4.0, b + (d - b) * 0.75, shade(DECK, 0.3), r=1.0)


# ---- The main unit -------------------------------------------------------------------------------------------------

def puzzle(reg, x0, y0, x1, y1, colour):
    """New Media Systems's puzzle piece: a square with a knob up and a knob right, and a notch at its left."""
    w, h = x1 - x0, y1 - y0
    reg.rect_(x0, y0 + h * 0.3, x0 + w * 0.72, y1, colour)
    reg.circle(x0 + w * 0.36, y0 + h * 0.2, h * 0.17, colour)
    reg.circle(x0 + w * 0.84, y0 + h * 0.62, h * 0.17, colour)
    reg.rect_(x0 + w * 0.6, y0 + h * 0.52, x0 + w * 0.8, y0 + h * 0.72, colour)
    reg.circle(x0 + w * 0.0, y0 + h * 0.66, h * 0.13, rgb(L.COLOURS["case"]))


def main_unit(reg):
    (x0, x1), (y0, y1) = L.MAIN["x"], L.MAIN["y"]
    rect_top(reg, x0, y0, x1, y1, CASE)
    (ax, ay), (bx, _) = top_point(x0 + 2.0, L.BAND), top_point(x1 - 2.0, L.BAND)
    reg.line([(ax, ay), (bx, ay)], shade(CASE, -0.35), 0.5)                      # the band's seam
    reg.line([(ax, ay + 0.5), (bx, ay + 0.5)], shade(CASE, 0.12), 0.3)

    (rx0, rx1), (ry0, ry1) = L.RESET["x"], L.RESET["y"]
    rect_top(reg, rx0 - 0.6, ry0 - 0.6, rx1 + 0.6, ry1 + 0.6, shade(CASE, -0.3), r=1.0)
    tx, ty = top_point((rx0 + rx1) / 2, L.LIGHTS["names"])
    reg.text("RESET", "arial.ttf", 1.9, tx, ty, WHITE)
    w, d = L.LIGHTS["size"]
    for name, label, colour in (("power", "POWER", (255, 70, 52)), ("caps", "CAPS", (30, 70, 36)),
                                ("fdd", "FDD BUSY", (96, 56, 20))):
        x, y = L.LIGHTS[name]
        rect_top(reg, x - w / 2 - 0.4, y - d / 2 - 0.4, x + w / 2 + 0.4, y + d / 2 + 0.4, shade(CASE, -0.4), r=0.4)
        rect_top(reg, x - w / 2, y - d / 2, x + w / 2, y + d / 2, colour, r=0.3)
        tx, ty = top_point(x, L.LIGHTS["names"])
        reg.text(label, "arial.ttf", 1.7, tx, ty, WHITE)

    (cx0, cx1), (cy0, cy1) = L.CART_COVER["x"], L.CART_COVER["y"]                # the front slot's cover
    rect_top(reg, cx0, cy0, cx1, cy1, shade(CASE, -0.14), r=0.8, outline=shade(CASE, -0.4), width=0.4)
    (mx, my) = top_point(cx0 + 9.0, (cy0 + cy1) / 2)
    reg.line([(mx - 5.0, my + 2.0), (mx - 5.0, my - 2.0), (mx - 1.0, my + 1.0), (mx + 3.0, my - 2.0),
              (mx + 3.0, my + 2.0)], shade(CASE, -0.45), 0.4)

    (px0, px1), (py0, py1) = L.PHILIPS["x"], L.PHILIPS["y"]                      # PHILIPS, in its dark plate
    rect_top(reg, px0, py0, px1, py1, shade(CASE, -0.4), r=0.5)
    tx, ty = top_point((px0 + px1) / 2, (py0 + py1) / 2)
    reg.text("PHILIPS", "arialbd.ttf", (py1 - py0) * 0.95, tx, ty + 0.2, (178, 178, 180))

    layer = reg.layer()                                      # VG-8235, slanted
    f = ImageFont.truetype(FONTS + "arialbi.ttf", max(1, round(L.MODEL["height"] * 1.38 * reg.sx)))
    mx, my = top_point(L.MODEL["x"], L.MODEL["y"])
    ImageDraw.Draw(layer).text(reg.p(mx, my), "VG-8235", font=f, fill=WHITE + (255,), anchor="lm")
    reg.over(layer)
    for line, y in zip(L.LETTERING["lines"], L.LETTERING["y"]):
        lx, ly = top_point(L.LETTERING["x"], y)
        reg.text(line, "arial.ttf", L.LETTERING["height"] * 1.3, lx, ly, WHITE, anchor="lm")
    (bx0, by0), (bx1, by1) = top_point(L.MSX_BADGE["x"][0], L.MSX_BADGE["y"][1]), top_point(L.MSX_BADGE["x"][1],
                                                                                              L.MSX_BADGE["y"][0])
    msx_badge(reg, bx0, by0, bx1, by1)
    reg.text("2", "arialbd.ttf", 3.8, bx1 + 1.6, by1 - 0.6, WHITE)
    shield(reg, *top_point(L.SHIELD["x"], L.SHIELD["y"]), L.SHIELD["height"], (150, 150, 152))
    (zx0, zy0), (zx1, zy1) = top_point(L.PUZZLE["x"][0], L.PUZZLE["y"][1]), top_point(L.PUZZLE["x"][1],
                                                                                        L.PUZZLE["y"][0])
    puzzle(reg, zx0, zy0, zx1, zy1, SALMON)
    nx, ny = top_point(L.NMS["x"], L.NMS["y"])
    reg.text("New Media Systems", "timesbd.ttf", L.NMS["height"] * 1.35, nx, ny, SALMON, anchor="rm")


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, DECK)
    deck(reg)
    main_unit(reg)
    keys(reg)
    return reg


# ---- The right end, the disk -------------------------------------------------------------------------------------------

def end():
    """The main unit's right end, seen from the right: the front at its left; the joystick ports under the bezel."""
    (y0, y1) = L.MAIN["y"]
    w, h = y1 - y0, L.HEIGHT
    reg = Region(L.REGIONS["end"], w, h, CASE)
    z0, z1 = L.PORTS["z"]
    for k, (a, b) in enumerate(L.PORTS["y"]):
        cx, cy = (a + b) / 2 - y0, h - (z0 + z1) / 2
        reg.rect_(a - y0, h - z1, b - y0, h - z0, shade(CASE, -0.35), r=0.8)
        shell = [(cx - 8.2, cy - 3.4), (cx + 8.2, cy - 3.4), (cx + 6.9, cy + 3.4), (cx - 6.9, cy + 3.4)]
        reg.poly(shell, (110, 110, 114))
        reg.poly([(px + (0.6 if px < cx else -0.6), py + (0.5 if py < cy else -0.5)) for px, py in shell], (14, 14, 16))
        for j in range(5):
            reg.circle(cx - 5.4 + 2.7 * j, cy - 1.3, 0.5, (176, 160, 110))
        for j in range(4):
            reg.circle(cx - 4.05 + 2.7 * j, cy + 1.4, 0.5, (176, 160, 110))
        reg.text(str(k + 1), "arial.ttf", 2.2, cx, h - z0 + 2.4, WHITE)
    return reg


def disk_side(rect, label):
    """One side of the 3.5-inch disk, seen looking at it, its shutter's end at the top."""
    w, l = L.DISK["size"]
    blue = (36, 40, 48)
    reg = Region(rect, w, l, blue)
    reg.rect_(0.0, 0.0, w, l, shade(blue, 0.06), r=2.0)
    reg.rect_(26.0, 0.0, 64.0, 36.0, (200, 204, 210))               # the shutter
    reg.rect_(36.0, 6.0, 54.0, 26.0, (40, 38, 44), r=1.5)
    reg.rect_(37.5, 7.5, 52.5, 24.5, (92, 64, 44), r=1.0)
    if label:
        reg.rect_(8.0, 40.0, w - 8.0, l - 6.0, (244, 242, 234), r=1.2)
        art = space((640, 300)).convert("RGB")
        da = ImageDraw.Draw(art)
        ship(da, 200, 160, 3.0, "#FFFFFF", "#FFB23C")
        x0, y0, x1, y1 = reg.box(10.0, 42.0, w - 10.0, l - 22.0)
        reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
        reg.text("ODYSSEY", "ariblk.ttf", 8.0, w / 2, 50.0, (255, 214, 70))
        msx_badge(reg, 12.0, l - 16.0, 26.0, l - 10.0)
        reg.text("2", "arialbd.ttf", 4.6, 28.6, l - 13.0, (40, 40, 60))
        reg.text("DISK 1", "arialbd.ttf", 3.8, w - 12.0, l - 13.0, (40, 40, 60), anchor="rm")
    else:
        reg.circle(w / 2, l * 0.6, 12.0, (176, 180, 186))
        reg.circle(w / 2, l * 0.6, 3.0, (30, 30, 34))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), DECK)
    for reg in (top(), end(), disk_side(L.REGIONS["disk_top"], True), disk_side(L.REGIONS["disk_bottom"], False)):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("red", (255, 64, 48)), ("green", (96, 255, 120)), ("amber", (255, 170, 50)),
                         ("black", BLACK), ("red_off", (92, 24, 22))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "msx2_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
