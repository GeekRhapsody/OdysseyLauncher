"""The Commodore CDTV card's printing (cdtv_print.png), for the console theme's model (cdtv.py).

One image, laid out as cdtv_layout.REGIONS says: the front (the power switch and the headphone jack, the LEDs, the
caddy's panel with the Compact Disc mark, the infrared window, the play, stop and volume buttons' faces, Commodore CDTV,
the small buttons' labels on the strip), the top's vent grille, the remote from above (its frame, its name, the keys'
labels, the end sections' ribs), the caddy's top (a made-up game, Odyssey, through its window), the display's faces (the
clock, then the track and its time, in cyan), and swatches. Run it with the system Python (Pillow):

    python tools/console-models/cdtv_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdtv_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
PANEL = (36, 36, 39)
GREY = (150, 150, 152)
WHITE = (226, 226, 222)
GOLD = (214, 176, 96)
CYAN = (80, 220, 255)
KEY = (128, 126, 122)


def shade(colour, k):
    return tuple(max(0, min(255, round(c * (1 + k)))) for c in colour)


def chicken_head(reg, x, y, h, ink):
    """Commodore's mark, h tall, its middle at (x, y): the C, and the flag's two halves in its mouth."""
    r = h / 2
    reg.circle(x, y, r, ink)
    reg.circle(x + 0.12 * h, y, r * 0.58, CASE)
    reg.rect_(x + 0.05 * h, y - 0.36 * h, x + 0.6 * h, y + 0.36 * h, CASE)
    reg.poly([(x + 0.12 * h, y - 0.05 * h), (x + 0.5 * h, y - 0.05 * h), (x + 0.5 * h, y - 0.3 * h)], ink)
    reg.poly([(x + 0.12 * h, y + 0.05 * h), (x + 0.5 * h, y + 0.05 * h), (x + 0.5 * h, y + 0.3 * h)], (190, 40, 40))


def compact_disc(reg, x, y, h, ink):
    """The Compact Disc mark, h tall, its middle at (x, y)."""
    reg.text("COMPACT", "arialbd.ttf", h * 0.22, x, y - h * 0.34, ink)
    reg.text("disc", "ariblk.ttf", h * 0.62, x, y + h * 0.14, ink)
    reg.line([(x - h * 0.9, y - h * 0.5), (x + h * 0.9, y - h * 0.5)], ink, h * 0.05)


def front():
    """The front: x across (-WIDTH/2 at the left), z down from its top."""
    reg = Region(L.REGIONS["front"], L.WIDTH, L.HEIGHT - L.FEET["height"], CASE)

    def at(x, z):
        return x + L.WIDTH / 2, L.HEIGHT - z

    z0, z1 = L.STRIP["z"]
    reg.rect_(*at(-L.WIDTH / 2, z1), *at(L.WIDTH / 2, z0), shade(CASE, -0.25))
    reg.line([at(-L.WIDTH / 2, z1 - 0.3), at(L.WIDTH / 2, z1 - 0.3)], shade(CASE, 0.6), 0.4)
    for (x0, x1), name in zip(L.SMALL["x"], L.SMALL["names"]):
        za, zb = L.SMALL["z"]
        reg.rect_(*at(x0, zb), *at(x1, za), shade(CASE, 0.25), r=0.6)
        reg.text(name, "seguisym.ttf" if "◄" in name or "►" in name else "arialbd.ttf", 2.4,
                 *at((x0 + x1) / 2, zb + 2.0), GREY)

    (px0, px1), (pz0, pz1) = L.POWER["x"], L.POWER["z"]
    reg.rect_(*at(px0, pz1), *at(px1, pz0), shade(CASE, 0.35), r=1.0)
    reg.rect_(*at(px0 + 1.5, pz1 - 1.5), *at(px0 + 9.0, pz0 + 1.5), shade(CASE, 0.6), r=0.6)
    reg.text("POWER", "arialbd.ttf", 2.2, *at((px0 + px1) / 2, pz1 + 2.6), GREY)
    jx, jz = L.JACK["at"]
    reg.circle(*at(jx, jz), L.JACK["r"] + 1.2, shade(CASE, 0.5))
    reg.circle(*at(jx, jz), L.JACK["r"], (6, 6, 6))
    reg.text("∩", "seguisym.ttf", 3.0, *at(jx, jz + 7.0), GREY)
    for name in ("green", "yellow"):
        lx, lz = L.LEDS[name]
        reg.circle(*at(lx, lz), L.LEDS["r"], (40, 60, 40) if name == "green" else (70, 60, 30))

    (cx0, cx1), (cz0, cz1) = L.PANEL["x"], L.PANEL["z"]
    reg.rect_(*at(cx0, cz1), *at(cx1, cz0), PANEL, r=1.0)
    compact_disc(reg, *at((cx0 + cx1) / 2, cz1 - 9.0), 9.0, GREY)
    (sx0, sx1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    reg.rect_(*at(sx0, sz1), *at(sx1, sz0), (6, 6, 6))
    (ex0, ex1), (ez0, ez1) = L.EJECT["x"], L.EJECT["z"]
    reg.rect_(*at(ex0 - 1.0, ez1 + 1.0), *at(ex1 + 1.0, ez0 - 1.0), (10, 10, 10), r=0.8)

    (ix0, ix1), (iz0, iz1) = L.IR["x"], L.IR["z"]
    reg.rect_(*at(ix0, iz1), *at(ix1, iz0), (32, 8, 10), r=1.0)
    reg.text("CD", "arialbd.ttf", 2.6, *at(ix0 + 7.0, (iz0 + iz1) / 2), (110, 40, 40))
    (dx0, dx1), (dz0, dz1) = L.DISPLAY["x"], L.DISPLAY["z"]
    reg.rect_(*at(dx0 - 1.0, dz1 + 1.0), *at(dx1 + 1.0, dz0 - 1.0), (8, 10, 12), r=1.0)

    for box, label in ((L.PLAY, "► ❘❘"), (L.STOP, "■")):
        (bx0, bx1), (bz0, bz1) = box["x"], box["z"]
        reg.rect_(*at(bx0, bz1), *at(bx1, bz0), shade(CASE, 0.3), r=1.0)
        reg.text(label, "seguisym.ttf", 4.0, *at((bx0 + bx1) / 2, (bz0 + bz1) / 2),
                 (200, 50, 40) if label == "■" else WHITE)
    (vx0, vx1), (vz0, vz1) = L.VOLUME["x"], L.VOLUME["z"]
    reg.rect_(*at(vx0, vz1), *at(vx1, vz0), shade(CASE, 0.3), r=1.0)
    mid = (vx0 + vx1) / 2
    reg.line([at(mid + 4.0, vz1), at(mid - 4.0, vz0)], shade(CASE, -0.4), 0.8)
    reg.text("▼ DOWN", "seguisym.ttf", 3.2, *at(vx0 + 16.0, vz1 - 6.0), WHITE)
    reg.text("UP ▲", "seguisym.ttf", 3.2, *at(vx1 - 14.0, vz1 - 6.0), WHITE)
    reg.text("∩ VOLUME", "seguisym.ttf", 2.8, *at(mid, vz1 + 3.0), GREY)

    (lx0, lx1), (lz0, lz1) = L.LOGO["x"], L.LOGO["z"]
    chicken_head(reg, *at(lx0 + 6.0, lz1 - 5.0), 8.0, GOLD)
    reg.text("Commodore", "arialbd.ttf", 9.0, *at(lx0 + 12.0, lz1 - 5.0), WHITE, anchor="lm")
    reg.text("CDTV", "arial.ttf", 7.0, *at(lx1 - 2.0, lz0 + 3.5), GREY, anchor="rm")
    return reg


def vents():
    """The top's back from above: x across, y down from the back edge; the grille's rows of slots."""
    y0, y1 = 190.0, 320.0
    reg = Region(L.REGIONS["vents"], L.WIDTH, y1 - y0, CASE)

    def at(x, y):
        return x + L.WIDTH / 2, y1 - y

    (vx0, vx1), (vy0, vy1) = L.VENTS["x"], L.VENTS["y"]
    rows, cols = 6, 36
    for r in range(rows):
        for c in range(cols):
            x = vx0 + (vx1 - vx0) * (c + 0.5) / cols
            y = vy0 + (vy1 - vy0) * (r + 0.5) / rows
            reg.rect_(*at(x - 2.2, y + 6.0), *at(x + 2.2, y - 6.0), (6, 6, 7), r=1.6)
    return reg


def remote():
    """The remote from above: x along it (-length/2 at the left), y down from its back edge."""
    length, depth, _ = L.REMOTE["size"]
    reg = Region(L.REGIONS["remote"], length, depth, (30, 30, 34))

    def at(x, y):
        return x + length / 2, depth / 2 - y

    ends = L.REMOTE["ends"]
    for side in (-1, 1):                                    # the end sections' ribs
        x0 = side * (length / 2 - ends)
        for k in range(4):
            y = depth / 2 - 6.0 - 3.0 * k
            reg.line([at(min(x0, side * length / 2 - side * 4.0), y), at(max(x0, side * length / 2 - side * 4.0), y)],
                     (14, 14, 16), 0.9)
        reg.line([at(x0, depth / 2), at(x0 + side * 4.0, -depth / 2)], (14, 14, 16), 1.2)
    w = length / 2 - ends - 4.0
    reg.rect_(*at(-w, depth / 2 - 5.0), *at(w, -depth / 2 + 5.0), None, r=1.5, outline=(70, 70, 76), width=0.4)
    chicken_head(reg, *at(-w + 7.0, 27.0), 5.0, WHITE)
    reg.text("Commodore", "arialbd.ttf", 5.0, *at(-w + 11.0, 27.0), WHITE, anchor="lm")
    reg.text("CDTV REMOTE CONTROLLER", "arial.ttf", 2.6, *at(-w + 46.0, 27.0), WHITE, anchor="lm")
    compact_disc(reg, *at(w - 8.0, 27.0), 6.0, WHITE)
    kw, kh = L.REMOTE["key"]
    for (x, y), name in zip(L.KEYS, L.KEY_NAMES):
        reg.text(name, "seguisym.ttf" if name in ("▲", "▼") else "arial.ttf",
                 2.4 if len(name) > 1 else 2.8, *at(x, y + kh / 2 + 2.0), WHITE)
        reg.rect_(*at(x - kw / 2, y + kh / 2), *at(x + kw / 2, y - kh / 2), (200, 40, 36) if name == "POWER" else KEY,
                  r=0.8)
    for name, (x, y) in (("A", L.REMOTE["a"]), ("B", L.REMOTE["b"])):
        reg.text(name, "arialbd.ttf", 3.0, *at(x, y + L.REMOTE["r"] + 3.0), WHITE)
    return reg


def caddy():
    """The caddy's top: x across, y down from its leading edge (the end going in) to its trailing edge."""
    w, length, _ = L.CADDY["size"]
    reg = Region(L.REGIONS["caddy"], w, length, (24, 24, 26))
    ww, wl = L.CADDY["window"]
    cx, cy = w / 2, 10.0 + wl / 2
    r = L.CADDY["disc"]
    disc = reg.layer()                                      # the disc, seen through the window: clipped to it
    d = ImageDraw.Draw(disc)
    d.ellipse(reg.box(cx - r, cy - r, cx + r, cy + r), fill=(176, 180, 186, 255))
    art = space((480, 480)).convert("RGB")
    ship(ImageDraw.Draw(art), 130, 300, 2.4, "#FFFFFF", "#FFB23C")
    ring = Image.new("L", art.size, 0)
    ImageDraw.Draw(ring).ellipse([16, 16, 464, 464], fill=255)
    ImageDraw.Draw(ring).ellipse([196, 196, 284, 284], fill=0)
    x0, y0, x1, y1 = reg.box(cx - r + 3.0, cy - r + 3.0, cx + r - 3.0, cy + r - 3.0)
    size = (round(x1 - x0), round(y1 - y0))
    disc.paste(art.resize(size, Image.LANCZOS).convert("RGBA"), (round(x0), round(y0)),
               ring.resize(size, Image.LANCZOS))
    d.ellipse(reg.box(cx - 7.5, cy - 7.5, cx + 7.5, cy + 7.5), fill=(200, 204, 208, 255))
    d.ellipse(reg.box(cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5), fill=(30, 30, 34, 255))
    window = Image.new("L", disc.size, 0)
    ImageDraw.Draw(window).rounded_rectangle(reg.box(cx - ww / 2, cy - wl / 2, cx + ww / 2, cy + wl / 2),
                                             radius=4.0 * reg.sx, fill=255)
    disc.putalpha(Image.composite(disc.getchannel("A"), window, window))
    reg.rect_(cx - ww / 2, cy - wl / 2, cx + ww / 2, cy + wl / 2, (50, 54, 60), r=4.0)
    reg.over(disc)
    reg.text("ODYSSEY", "ariblk.ttf", 7.0, cx, cy - 30.0, (255, 214, 70))
    reg.rect_(cx - ww / 2, cy - wl / 2, cx + ww / 2, cy + wl / 2, None, r=4.0, outline=(90, 94, 100), width=0.8)
    reg.rect_(12.0, length - 22.0, w - 12.0, length - 8.0, (230, 228, 220), r=1.0)
    reg.text("CDTV", "arialbd.ttf", 5.0, w / 2, length - 15.0, (40, 40, 44))
    return reg


SEGMENTS = dict(a=((0.1, 0.0), (0.9, 0.0)), b=((1.0, 0.1), (1.0, 0.45)), c=((1.0, 0.55), (1.0, 0.9)),
                d=((0.1, 1.0), (0.9, 1.0)), e=((0.0, 0.55), (0.0, 0.9)), f=((0.0, 0.1), (0.0, 0.45)),
                g=((0.1, 0.5), (0.9, 0.5)))
DIGITS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc",
          "8": "abcdefg", "9": "abcdfg"}


def display(text):
    """One of the display's faces: seven-segment digits in cyan, its colon a pair of dots."""
    (x0, x1), (z0, z1) = L.DISPLAY["x"], L.DISPLAY["z"]
    w, h = x1 - x0, z1 - z0
    region = {"12:00": "clock"}.get(text, "time_" + text[-1])
    reg = Region(L.REGIONS[region], w, h, (8, 10, 12))
    dw, dh, x = 4.4, 8.0, 3.0
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    for c in text:
        if c == ":":
            for y in (h / 2 - 1.6, h / 2 + 1.6):
                d.ellipse(reg.box(x + 0.2, y - 0.5, x + 1.2, y + 0.5), fill=CYAN + (255,))
            x += 2.4
            continue
        if c == " ":
            x += 4.0
            continue
        for seg in DIGITS[c]:
            (ax, ay), (bx, by) = SEGMENTS[seg]
            d.line([reg.p(x + ax * dw, (h - dh) / 2 + ay * dh), reg.p(x + bx * dw, (h - dh) / 2 + by * dh)],
                   fill=CYAN + (255,), width=reg.width(0.9))
        x += dw + 2.4
    glow = layer.filter(ImageFilter.GaussianBlur(reg.width(0.6)))
    reg.over(glow)
    reg.over(layer)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (front(), vents(), remote(), caddy(), display("12:00"), display("01 00:00"), display("01 00:01"),
                display("01 00:02"), display("01 00:03")):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, silver=(196, 198, 200), dark=(6, 6, 6), key=KEY, red=(200, 40, 36), green=(90, 255, 90),
                   yellow=(255, 210, 60), remote=(30, 30, 34), caddy=(24, 24, 26), off=(30, 34, 30))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "cdtv_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
