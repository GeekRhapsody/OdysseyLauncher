"""Flash's card's screens and printing, for the console theme's Flash model (tools/console-models/flash.py).

Draws its atlas, its regions as flash_layout.py places them: the screens, each a browser window of the 2000s filling
the glass (its blue title bar, its menus, the address bar, the page with a Flash game in it, the status bar), the game
in its states (the preloader's splash with the Flash logo, its bar filling; Odyssey's title, the pointer on PLAY; two
frames of play; the right-click menu ending in About Adobe Flash Player); the brand plate under the screen; the mouse's
top; and the swatches small parts take their colour from. Odyssey and the site it's on (odyssey.example, a domain kept
for examples) are made up. Run it with the system Python (Pillow):

    python tools/console-models/flash_print.py <out folder>

It writes flash_print.png there.
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flash_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, gradient  # noqa: E402

SS = 3                       # the screens drawn this many times larger, then resampled
W, H = L.SCREEN_PX
MOVIE = (40, 74, 360, 290)   # the Flash movie in the page: x0, y0, x1, y1


def font(name, size):
    return ImageFont.truetype(FONTS + name, max(1, round(size * SS)))


def box(x0, y0, x1, y1):
    return [x0 * SS, y0 * SS, x1 * SS, y1 * SS]


def flash_logo(img, cx, cy, s):
    """The Flash Player's logo, s across, its middle at (cx, cy): the red square, the white f."""
    d = ImageDraw.Draw(img)
    tile = gradient((round(s * SS), round(s * SS)), [(0.0, (236, 32, 36)), (1.0, (150, 18, 24))])
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.width - 1, tile.height - 1], radius=round(s * 0.08 * SS),
                                           fill=255)
    img.paste(tile, (round((cx - s / 2) * SS), round((cy - s / 2) * SS)), mask)
    d.polygon([((cx - s / 2 + x * s) * SS, (cy - s / 2 + y * s) * SS) for x, y in L.F_LOGO], fill=(255, 255, 255))


def pointer(d, x, y, hand=False):
    """The mouse pointer, its tip at (x, y): the arrow, or the hand over a link."""
    if hand:
        pts = [(0, 0), (2, -1), (3, 0), (3, 5), (5, 4), (7, 5), (9, 5), (11, 7), (11, 13), (9, 16), (3, 16), (0, 10),
               (-2, 7), (-1, 6), (0, 7)]
    else:
        pts = [(0, 0), (0, 15), (4, 11), (7, 17), (9, 16), (6, 10), (11, 10)]
    d.polygon([((x + a) * SS, (y + b) * SS) for a, b in pts], fill=(255, 255, 255), outline=(0, 0, 0),
              width=max(1, SS // 2))


def browser():
    """The browser window: the title bar, menus, address bar, the page round the movie, the status bar."""
    img = Image.new("RGB", (W * SS, H * SS), (236, 233, 216))
    d = ImageDraw.Draw(img)
    bar = gradient((W * SS, 18 * SS), [(0.0, (0, 88, 238)), (0.15, (61, 149, 255)), (0.5, (0, 84, 227)),
                                       (1.0, (0, 70, 206))])
    img.paste(bar.convert("RGB"), (0, 0))
    d.text((6 * SS, 9 * SS), "Odyssey - Play it now! - Odyssey Navigator", font=font("tahomabd.ttf", 7.5),
           fill=(255, 255, 255), anchor="lm")
    for k, colour in enumerate(((0, 84, 227), (0, 84, 227), (224, 76, 48))):
        x = W - 46 + k * 15
        d.rounded_rectangle(box(x, 3, x + 13, 15), radius=2 * SS, fill=colour, outline=(255, 255, 255),
                            width=max(1, SS // 2))
    d.line(box(W - 43, 12, W - 37, 12), fill=(255, 255, 255), width=SS)
    d.rectangle(box(W - 28, 6, W - 21, 12), outline=(255, 255, 255), width=SS)
    d.line(box(W - 13, 6, W - 7, 12), fill=(255, 255, 255), width=SS)
    d.line(box(W - 13, 12, W - 7, 6), fill=(255, 255, 255), width=SS)
    for k, word in enumerate(("File", "Edit", "View", "Favorites", "Tools", "Help")):
        d.text(((6 + [0, 22, 44, 68, 108, 136][k]) * SS, 25 * SS), word, font=font("tahoma.ttf", 7.0),
               fill=(0, 0, 0), anchor="lm")
    d.line(box(0, 32, W, 32), fill=(172, 168, 153), width=SS)
    d.text((6 * SS, 41 * SS), "Address", font=font("tahoma.ttf", 7.0), fill=(80, 80, 80), anchor="lm")
    d.rectangle(box(40, 35, W - 40, 47), fill=(255, 255, 255), outline=(127, 157, 185), width=SS)
    d.text((44 * SS, 41 * SS), "http://odyssey.example/arcade/odyssey.swf", font=font("tahoma.ttf", 7.0),
           fill=(0, 0, 0), anchor="lm")
    d.rounded_rectangle(box(W - 34, 35, W - 6, 47), radius=2 * SS, fill=(60, 170, 60))
    d.text(((W - 20) * SS, 41 * SS), "Go", font=font("tahomabd.ttf", 7.0), fill=(255, 255, 255), anchor="mm")
    page = gradient((W * SS, (H - 64) * SS), [(0.0, (26, 34, 70)), (1.0, (10, 12, 30))])
    img.paste(page.convert("RGB"), (0, 50 * SS))
    d.text((W / 2 * SS, 62 * SS), "ODYSSEY ARCADE  ·  FREE ONLINE GAMES", font=font("verdanab.ttf", 7.0),
           fill=(255, 196, 60), anchor="mm")
    d.rectangle(box(0, H - 14, W, H), fill=(236, 233, 216))
    d.line(box(0, H - 14, W, H - 14), fill=(172, 168, 153), width=SS)
    d.text((6 * SS, (H - 7) * SS), "Done", font=font("tahoma.ttf", 7.0), fill=(0, 0, 0), anchor="lm")
    d.text(((W - 8) * SS, (H - 7) * SS), "Internet", font=font("tahoma.ttf", 7.0), fill=(0, 0, 0), anchor="rm")
    return img


def movie_space(seed=0):
    """Odyssey's backdrop in the movie's area."""
    x0, y0, x1, y1 = MOVIE
    art = space(((x1 - x0) * SS, (y1 - y0) * SS))
    rng = random.Random(seed)
    d = ImageDraw.Draw(art)
    for _ in range(30):
        x, y = rng.randrange(art.width), rng.randrange(art.height)
        d.ellipse([x - SS, y - SS, x + SS, y + SS], fill=(255, 255, 255, 255))
    return art.convert("RGB")


def screen(state):
    img = browser()
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = MOVIE
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if state in ("rest", "load"):
        d.rectangle(box(x0, y0, x1, y1), fill=(16, 16, 18))
        flash_logo(img, cx, cy - 20, 92)
        d.text((cx * SS, (cy + 44) * SS), "Loading...", font=font("verdana.ttf", 8.0), fill=(220, 220, 220),
               anchor="mm")
        d.rectangle(box(cx - 80, cy + 56, cx + 80, cy + 64), outline=(200, 200, 200), width=SS)
        if state == "load":
            d.rectangle(box(cx - 78, cy + 58, cx - 78 + 156 * 0.7, cy + 62), fill=(236, 40, 40))
            d.text(((cx + 92) * SS, (cy + 60) * SS), "70%", font=font("verdana.ttf", 7.0), fill=(220, 220, 220),
                   anchor="lm")
    else:
        img.paste(movie_space(1 if state == "game2" else 0), (x0 * SS, y0 * SS))
        if state == "title":
            d.text((cx * SS, (y0 + 52) * SS), "ODYSSEY", font=font("ariblk.ttf", 34.0), fill=(255, 214, 70),
                   anchor="mm", stroke_width=SS * 2, stroke_fill=(120, 30, 10))
            ship(d, (cx - 60) * SS, (cy + 20) * SS, 1.8 * SS, "#FFFFFF", "#FFB23C")
            d.rounded_rectangle(box(cx - 40, cy + 50, cx + 40, cy + 74), radius=6 * SS, fill=(240, 120, 30),
                                outline=(255, 230, 160), width=SS)
            d.text((cx * SS, (cy + 62) * SS), "PLAY", font=font("ariblk.ttf", 12.0), fill=(255, 255, 255),
                   anchor="mm")
            pointer(d, cx + 14, cy + 62, hand=True)
        else:
            frame = 0 if state in ("game1", "menu") else 1
            sx = cx - 90 + frame * 12
            ship(d, sx * SS, (cy + 10) * SS, 1.5 * SS, "#FFFFFF", "#FFB23C")
            d.line(box(sx + 26, cy + 10, sx + 96 + frame * 30, cy + 10), fill=(255, 236, 80), width=2 * SS)
            for ax, ay, r in ((cx + 60, cy + 10 - frame * 4, 16), (cx + 110, cy - 50, 12), (cx + 20, cy + 60, 10)):
                if frame == 1 and ax == cx + 60:
                    for k in range(14):                        # it bursts
                        a, b = random.Random(k).uniform(-18, 18), random.Random(k + 40).uniform(-18, 18)
                        d.ellipse(box(ax + a - 2, ay + b - 2, ax + a + 2, ay + b + 2), fill=(255, 200, 60))
                    continue
                d.ellipse(box(ax - r, ay - r, ax + r, ay + r), fill=(140, 96, 70), outline=(90, 60, 44), width=SS)
                d.ellipse(box(ax - r * 0.4, ay - r * 0.5, ax, ay - r * 0.1), fill=(170, 124, 96))
            d.text(((x0 + 8) * SS, (y0 + 10) * SS), f"SCORE {1200 + frame * 250:06d}", font=font("verdanab.ttf", 8.0),
                   fill=(255, 255, 255), anchor="lm")
            if state == "menu":
                mx, my = cx + 30, cy - 40
                items = ["Zoom In", "Zoom Out", "Show All", "Quality", "", "Settings...", "Global Settings...", "",
                         "About Adobe Flash Player 10..."]
                heights = [6 if not item else 15 for item in items]
                width = 150
                d.rectangle(box(mx + 3, my + 3, mx + width + 3, my + sum(heights) + 7), fill=(30, 30, 30))
                d.rectangle(box(mx, my, mx + width, my + sum(heights) + 4), fill=(245, 245, 245),
                            outline=(130, 130, 130), width=SS)
                y = my + 2
                for item, h in zip(items, heights):
                    if not item:
                        d.line(box(mx + 4, y + 3, mx + width - 4, y + 3), fill=(190, 190, 190), width=SS)
                    else:
                        if item.startswith("About"):
                            d.rectangle(box(mx + 2, y, mx + width - 2, y + h), fill=(49, 106, 197))
                        d.text(((mx + 14) * SS, (y + h / 2) * SS), item, font=font("tahoma.ttf", 7.0),
                               fill=(255, 255, 255) if item.startswith("About") else (0, 0, 0), anchor="lm")
                        if item == "Quality":
                            d.text(((mx + width - 8) * SS, (y + h / 2) * SS), "▸", font=font("seguisym.ttf", 7.0),
                                   fill=(0, 0, 0), anchor="mm")
                    y += h
                pointer(d, mx + 60, my + sum(heights) - 4)
            else:
                pointer(d, cx + 30, cy - 40)
    return img.resize(L.SCREEN_PX, Image.LANCZOS)


def plate():
    x, y, w, h = L.REGIONS["plate"]
    img = Image.new("RGB", (w * SS, h * SS), rgb(L.COLOURS["silver"]))
    d = ImageDraw.Draw(img)
    d.text((w / 2 * SS, h / 2 * SS), "ODYSSEY", font=font("arialbd.ttf", 22.0), fill=(70, 72, 78), anchor="mm")
    return img.resize((w, h), Image.LANCZOS)


def mouse_top():
    x, y, w, h = L.REGIONS["mouse"]
    img = Image.new("RGB", (w * SS, h * SS), rgb(L.COLOURS["mouse"]))
    d = ImageDraw.Draw(img)
    split = L.MOUSE["split"] / L.MOUSE["size"][1] * h
    d.line(box(0, split, w, split), fill=(110, 112, 118), width=SS)
    d.line(box(w / 2, 0, w / 2, split), fill=(110, 112, 118), width=SS)
    d.rounded_rectangle(box(w / 2 - 6, split * 0.25, w / 2 + 6, split * 0.75), radius=5 * SS, fill=(60, 62, 66))
    return img.resize((w, h), Image.LANCZOS)


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (10, 10, 12))
    for state in ("rest", "load", "title", "game1", "game2", "menu"):
        x, y, _, _ = L.REGIONS[state]
        image.paste(screen(state), (x, y))
    for name, art in (("plate", plate()), ("mouse", mouse_top())):
        x, y, _, _ = L.REGIONS[name]
        image.paste(art, (x, y))
    d = ImageDraw.Draw(image)
    for name, colour in (("silver", rgb(L.COLOURS["silver"])), ("black", rgb(L.COLOURS["black"])),
                         ("blue", (70, 160, 255)), ("grey", rgb(L.COLOURS["mouse"]))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "flash_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
