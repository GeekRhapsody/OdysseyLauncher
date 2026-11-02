"""Flash's card's printing, its screen's still and the screens of its video, for the console theme's Flash model
(tools/console-models/flash.py); its video (flash_video.py) draws its frames with the screens here. flash_layout.py has
the measurements, the screen's layout and the clip's timing.

Writes two images into a folder:
- flash_print.png: the brand plate under the screen, the mouse's top and the swatches small parts take their colour
  from, the regions as flash_layout.py places them.
- flash_screen.png: the glass, VIDEO_PX: the browser with the preloader at 0% and the pointer on Go, the `video`
  material's texture: the video's first and last frame.

The screens are a browser window of the 2000s filling the glass (its blue title bar, its menus, the address bar with
Go, the page with the Flash movie in it, the status bar), drawn in the screen's units (flash_layout.SCREEN) at SS times
the video's size, then resampled. In the movie: the preloader's splash with the Flash Player's logo and its bar
(preloader()); Odyssey's title, its name dropping in, the ship sliding in and PLAY popping up, lit under the pointer
and pressed (title()); the game (Game: the ship following the mouse, a bolt for each click, the rocks they hit, the
score, the backdrop scrolling). Over it, the right-click menu ending in About Adobe Flash Player (menu()), and the
pointer: an arrow, a hand over PLAY, and the arrow with an hourglass while a page loads. Odyssey and the site it's on
(odyssey.example, a domain kept for examples) are made up. Run it with the system Python (Pillow):

    python tools/console-models/flash_print.py <out folder>
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flash_layout as L  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import FONTS, gradient  # noqa: E402

SS = 3                                   # the screens drawn this many times larger, then resampled
W, H = L.SCREEN
K = L.VIDEO_PX[0] / W * SS               # pixels a screen unit, while drawing
MX0, MY0, MX1, MY1 = L.MOVIE
MW, MH = MX1 - MX0, MY1 - MY0            # the movie's size; drawn in its own units, from its top left
CX, CY = MW / 2, MH / 2
BLACK = (16, 16, 18)                     # the movie's background before the game draws
SHIP = 1.5                               # the game's ship's scale
NOSE = 16 * SHIP                         # its nose, ahead of its middle: the nose follows the pointer
STATUS = "Opening page http://odyssey.example/arcade/odyssey.swf..."

ARROW = [(0, 0), (0, 15), (4, 11), (7, 17), (9, 16), (6, 10), (11, 10)]
HAND = [(-1.4, 0.6), (-0.8, -0.2), (0.8, -0.2), (1.4, 0.6), (1.4, 5.6), (2.0, 5.0), (3.6, 5.0), (4.2, 5.8),
        (4.8, 5.6), (6.2, 5.6), (6.8, 6.4), (7.4, 6.4), (8.6, 6.6), (9.2, 7.6), (9.2, 11.2), (8.4, 13.6),
        (7.6, 15.6), (-1.0, 15.6), (-2.6, 13.0), (-4.8, 10.0), (-5.2, 9.0), (-4.6, 8.2), (-3.4, 8.2), (-1.4, 10.2)]
KNUCKLES = [(1.4, 5.6, 9.0), (4.2, 5.8, 9.2), (6.8, 6.4, 9.4)]   # the folded fingers' seams: x, from, to

_fonts = {}


def font(name, size):
    key = (name, max(1, round(size * K)))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONTS + name, key[1])
    return _fonts[key]


def box(x0, y0, x1, y1):
    return [x0 * K, y0 * K, x1 * K, y1 * K]


def px(units):
    """A line's width in pixels, for a width in units."""
    return max(1, round(units * K))


def phase(f, f0, f1):
    return min(1.0, max(0.0, (f - f0) / (f1 - f0)))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def back_out(t, s=2.2):
    """Overshoots, then settles at 1."""
    t -= 1
    return 1 + t * t * ((s + 1) * t + s)


def bounce(t):
    """Falls to 1 and bounces on it, smaller each time: the tween every Flash game's title dropped in with."""
    for edge, back, rest in ((1 / 2.75, 0.0, 0.0), (2 / 2.75, 1.5 / 2.75, 0.75), (2.5 / 2.75, 2.25 / 2.75, 0.9375)):
        if t < edge:
            t -= back
            return 7.5625 * t * t + rest
    t -= 2.625 / 2.75
    return 7.5625 * t * t + 0.984375


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def faded(img, t):
    """img faded towards black: t 1 shows it, 0 is black."""
    return img if t >= 1.0 else Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, max(0.0, t))


def canvas(colour=BLACK):
    """The movie's image, and something to draw on it with (blending what has alpha)."""
    img = Image.new("RGB", (round(MW * K), round(MH * K)), colour)
    return img, ImageDraw.Draw(img, "RGBA")


# ---- The browser -----------------------------------------------------------------------------------------------------

_browsers = {}


def browser(status="Done", progress=None, go_down=False, blank=False):
    """The browser window round the page (white while a page loads: blank): the title bar, the menus, the address bar
    and Go (pressed: go_down), the status bar (its text, and how far a page has loaded while it loads: progress)."""
    key = (status, progress, go_down, blank)
    if key in _browsers:
        return _browsers[key]
    img = Image.new("RGB", (round(W * K), round(H * K)), (236, 233, 216))
    d = ImageDraw.Draw(img)
    bar = gradient((round(W * K), round(18 * K)), [(0.0, (0, 88, 238)), (0.15, (61, 149, 255)), (0.5, (0, 84, 227)),
                                                  (1.0, (0, 70, 206))])
    img.paste(bar.convert("RGB"), (0, 0))
    d.text((6 * K, 9 * K), "Odyssey - Play it now! - Odyssey Navigator", font=font("tahomabd.ttf", 7.5),
           fill=(255, 255, 255), anchor="lm")
    for k, colour in enumerate(((0, 84, 227), (0, 84, 227), (224, 76, 48))):
        x = W - 46 + k * 15
        d.rounded_rectangle(box(x, 3, x + 13, 15), radius=2 * K, fill=colour, outline=(255, 255, 255), width=px(0.35))
    d.line(box(W - 43, 12, W - 37, 12), fill=(255, 255, 255), width=px(1))
    d.rectangle(box(W - 28, 6, W - 21, 12), outline=(255, 255, 255), width=px(1))
    d.line(box(W - 13, 6, W - 7, 12), fill=(255, 255, 255), width=px(1))
    d.line(box(W - 13, 12, W - 7, 6), fill=(255, 255, 255), width=px(1))
    for k, word in enumerate(("File", "Edit", "View", "Favorites", "Tools", "Help")):
        d.text(((6 + [0, 22, 44, 68, 108, 136][k]) * K, 25 * K), word, font=font("tahoma.ttf", 7.0), fill=(0, 0, 0),
               anchor="lm")
    d.line(box(0, 32, W, 32), fill=(172, 168, 153), width=px(1))
    d.text((6 * K, 41 * K), "Address", font=font("tahoma.ttf", 7.0), fill=(80, 80, 80), anchor="lm")
    d.rectangle(box(40, 35, W - 40, 47), fill=(255, 255, 255), outline=(127, 157, 185), width=px(1))
    d.text((44 * K, 41 * K), "http://odyssey.example/arcade/odyssey.swf", font=font("tahoma.ttf", 7.0),
           fill=(0, 0, 0), anchor="lm")
    gx0, gy0, gx1, gy1 = L.GO
    d.rounded_rectangle(box(gx0, gy0, gx1, gy1), radius=2 * K, fill=(38, 128, 38) if go_down else (60, 170, 60))
    nudge = 0.6 if go_down else 0.0
    d.text((((gx0 + gx1) / 2 + nudge) * K, ((gy0 + gy1) / 2 + nudge) * K), "Go", font=font("tahomabd.ttf", 7.0),
           fill=(255, 255, 255), anchor="mm")
    if blank:
        d.rectangle(box(0, 50, W, H - 14), fill=(255, 255, 255))
    else:
        page = gradient((round(W * K), round((H - 64) * K)), [(0.0, (26, 34, 70)), (1.0, (10, 12, 30))])
        img.paste(page.convert("RGB"), (0, round(50 * K)))
        d.text((W / 2 * K, 62 * K), "ODYSSEY ARCADE  ·  FREE ONLINE GAMES", font=font("verdanab.ttf", 7.0),
               fill=(255, 196, 60), anchor="mm")
    d.rectangle(box(0, H - 14, W, H), fill=(236, 233, 216))
    d.line(box(0, H - 14, W, H - 14), fill=(172, 168, 153), width=px(1))
    d.text((6 * K, (H - 7) * K), status, font=font("tahoma.ttf", 7.0), fill=(0, 0, 0), anchor="lm")
    if progress is not None:                 # the progress panel: green blocks filling it
        x0, x1 = W - 128, W - 62
        d.rectangle(box(x0, H - 11, x1, H - 3), fill=(255, 255, 255), outline=(172, 168, 153), width=px(0.5))
        x = x0 + 1.5
        while x + 4 <= x0 + 1.5 + (x1 - x0 - 3) * progress:
            d.rectangle(box(x, H - 9.5, x + 4, H - 4.5), fill=(49, 182, 49))
            x += 5
    d.text(((W - 8) * K, (H - 7) * K), "Internet", font=font("tahoma.ttf", 7.0), fill=(0, 0, 0), anchor="rm")
    _browsers[key] = img
    return img


def draw_pointer(d, x, y, hand=False, busy=False):
    """The mouse pointer, its tip at (x, y): the arrow, the hand over a button, or the arrow with an hourglass beside
    it while a page loads."""
    d.polygon([((x + a) * K, (y + b) * K) for a, b in (HAND if hand else ARROW)], fill=(255, 255, 255),
              outline=(0, 0, 0), width=px(0.6))
    if hand:
        for kx, k0, k1 in KNUCKLES:
            d.line(box(x + kx, y + k0, x + kx, y + k1), fill=(0, 0, 0), width=px(0.5))
    if busy:
        hx, hy = x + 10.5, y + 11.0
        for top, bottom in ((hy, hy + 3.6), (hy + 7.2, hy + 3.6)):
            d.polygon([((hx - 2.6) * K, top * K), ((hx + 2.6) * K, top * K), (hx * K, bottom * K)],
                      fill=(236, 230, 210), outline=(0, 0, 0), width=px(0.45))
        d.line(box(hx - 3.0, hy, hx + 3.0, hy), fill=(0, 0, 0), width=px(0.8))
        d.line(box(hx - 3.0, hy + 7.2, hx + 3.0, hy + 7.2), fill=(0, 0, 0), width=px(0.8))


def screen(movie, cursor=None, menu_layer=None, status="Done", progress=None, go_down=False, blank=False):
    """A frame of the glass, VIDEO_PX: the browser round the movie (its image at K, or None), the right-click menu over
    it (a layer the screen's size, or None), and the pointer over everything (x, y, hand, busy; or None)."""
    img = browser(status, progress, go_down, blank).copy()
    if movie is not None and not blank:
        img.paste(movie, (round(MX0 * K), round(MY0 * K)))
    if menu_layer is not None:
        img = img.convert("RGBA")
        img.alpha_composite(menu_layer)
        img = img.convert("RGB")
    if cursor is not None:
        draw_pointer(ImageDraw.Draw(img), *cursor)
    return img.resize(L.VIDEO_PX, Image.LANCZOS)


# ---- The preloader ---------------------------------------------------------------------------------------------------

def flash_logo(img, cx, cy, s):
    """The Flash Player's logo, s across, its middle at (cx, cy): the red square, the white f."""
    tile = gradient((round(s * K), round(s * K)), [(0.0, (236, 32, 36)), (1.0, (150, 18, 24))])
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.width - 1, tile.height - 1], radius=round(s * 0.08 * K),
                                           fill=255)
    img.paste(tile, (round((cx - s / 2) * K), round((cy - s / 2) * K)), mask)
    ImageDraw.Draw(img).polygon([((cx - s / 2 + x * s) * K, (cy - s / 2 + y * s) * K) for x, y in L.F_LOGO],
                                fill=(255, 255, 255))


def preloader(progress):
    """The preloader: the Flash Player's logo over Loading..., its bar filled to progress (0 to 1), and the percent."""
    img, d = canvas()
    flash_logo(img, CX, CY - 20, 92)
    d.text((CX * K, (CY + 44) * K), "Loading...", font=font("verdana.ttf", 8.0), fill=(220, 220, 220), anchor="mm")
    d.rectangle(box(CX - 80, CY + 56, CX + 80, CY + 64), outline=(200, 200, 200), width=px(1))
    if progress > 0:
        d.rectangle(box(CX - 78, CY + 58, CX - 78 + 156 * progress, CY + 62), fill=(236, 40, 40))
    d.text(((CX + 92) * K, (CY + 60) * K), f"{round(progress * 100)}%", font=font("verdana.ttf", 7.0),
           fill=(220, 220, 220), anchor="lm")
    return img


# ---- Odyssey's sky, ship and rocks -----------------------------------------------------------------------------------

class Backdrop:
    """Odyssey's sky in the movie, as psp_print.space() paints it (deep violet, stars, an orange ringed planet in front
    of them), its layers scrolling left at their own speeds: the stars at three depths, the planet slowest."""

    def __init__(self, seed=3):
        self.sky = gradient((round(MW * K), round(MH * K)), [(0.0, (16, 10, 48)), (1.0, (60, 26, 118))]).convert("RGB")
        rng = random.Random(seed)
        self.stars = [(rng.uniform(0, MW), rng.uniform(0, MH), rng.choice((1, 1, 1, 2, 2, 3)),
                       rng.uniform(0, 2 * math.pi)) for _ in range(72)]

    def draw(self, scroll, planet_x, t):
        """The sky with its stars scrolled scroll units a depth, the planet's middle at planet_x, the stars twinkling
        at t seconds. Returns the image and something to draw on it with."""
        img = self.sky.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, depth, twinkle in self.stars:
            x = (x - scroll * depth) % (MW + 4) - 2
            r = 0.45 + 0.3 * depth
            v = (0.55 + 0.15 * depth) * (0.8 + 0.2 * math.sin(twinkle + t * 5.0))
            d.ellipse(box(x - r, y - r, x + r, y + r), fill=(round(200 * v + 40), round(200 * v + 40), 255))
        r, py = MH * 0.42, MH * 0.62
        d.ellipse(box(planet_x - r, py - r, planet_x + r, py + r), fill=rgb("#F27A3B"))
        d.ellipse(box(planet_x - r * 0.82, py - r * 0.95, planet_x + r * 0.7, py + r * 0.5), fill=rgb("#F79A55"))
        d.arc(box(planet_x - r * 1.7, py - r * 0.35, planet_x + r * 1.7, py + r * 0.35), 160, 380,
              fill=rgb("#F2E6FF"), width=px(3.3))
        return img, d


def draw_ship(d, x, y, s, angle=0.0, flame=10.0):
    """psp_print.ship()'s ship pointing right, its middle at (x, y), turned angle degrees (its nose up for more),
    its engine's flame flame long."""
    c, sn = math.cos(math.radians(angle)), math.sin(math.radians(angle))

    def at(a, b):
        return (x + (a * c + b * sn) * s) * K, (y + (-a * sn + b * c) * s) * K
    for shape in ([(16, 0), (-8, -7), (-4, 0), (-8, 7)], [(-2, -3), (-14, -13), (-9, -2)],
                  [(-2, 3), (-14, 13), (-9, 2)]):
        d.polygon([at(a, b) for a, b in shape], fill=(255, 255, 255))
    d.polygon([at(-5, -2.5), at(-5 - flame, 0), at(-5, 2.5)], fill=rgb("#FFB23C"))


class Rock:
    """A rock, lumpy and cratered, turning as it drifts left: at `at` on frame `frame`, speed units a frame left and
    drift down."""

    def __init__(self, rng, r, at, frame, speed, drift):
        self.r, self.at, self.frame, self.speed, self.drift = r, at, frame, speed, drift
        self.spin = rng.uniform(1.5, 4.0) * rng.choice((-1, 1))      # degrees a frame
        self.turn = rng.uniform(0, 360)
        self.shape = [(2 * math.pi * k / 11, r * rng.uniform(0.84, 1.16)) for k in range(11)]
        self.craters = [(rng.uniform(0, 2 * math.pi), r * rng.uniform(0.2, 0.55), r * rng.uniform(0.14, 0.24))
                        for _ in range(3)]

    def where(self, f):
        return self.at[0] + self.speed * (self.frame - f), self.at[1] + self.drift * (self.frame - f)

    def draw(self, d, f):
        x, y = self.where(f)
        x, y, r = x - MX0, y - MY0, self.r
        a = math.radians(self.turn + self.spin * f)
        d.polygon([((x + q * math.cos(t + a)) * K, (y + q * math.sin(t + a)) * K) for t, q in self.shape],
                  fill=(140, 96, 70), outline=(90, 60, 44), width=px(1))
        d.ellipse(box(x - r * 0.62, y - r * 0.6, x - r * 0.02, y - r * 0.08), fill=(166, 120, 92))   # lit, top left
        for t, q, s in self.craters:
            cx, cy = x + q * math.cos(t + a), y + q * math.sin(t + a)
            d.ellipse(box(cx - s, cy - s, cx + s, cy + s), fill=(110, 74, 54))


# ---- Odyssey's title -------------------------------------------------------------------------------------------------

def title(back, n, hover=0.0, down=False):
    """Odyssey's title n frames in: the sky drifting, the name dropping in and bouncing, the ship sliding in and
    bobbing, PLAY popping up and breathing, lit by hover (0 to 1) and pressed while down."""
    img, d = back.draw(0.3 * n, MW * 0.74, n / L.FPS)
    drop = 1 - bounce(phase(n, 4, 22))
    d.text((CX * K, (52 - 84 * drop) * K), "ODYSSEY", font=font("ariblk.ttf", 34.0), fill=(255, 214, 70),
           anchor="mm", stroke_width=px(2), stroke_fill=(120, 30, 10))
    slide = 1 - back_out(phase(n, 8, 26))
    draw_ship(d, CX - 60 - 150 * slide, CY + 20 + 2.2 * math.sin(2 * math.pi * n / 42), 1.8,
              flame=10 + 2.5 * math.sin(n * 1.9))
    if n >= 20:
        if n < 28:
            s = back_out(phase(n, 20, 28))
        else:
            s = 1 + 0.03 * math.sin(2 * math.pi * (n - 28) / 26) * (1 - hover) + 0.05 * hover
        fill = mix((240, 120, 30), (255, 152, 52), hover)
        if down:
            s, fill = 0.96, (205, 95, 20)
        bx, by = (L.PLAY[0] + L.PLAY[2]) / 2 - MX0, (L.PLAY[1] + L.PLAY[3]) / 2 - MY0
        hw, hh = (L.PLAY[2] - L.PLAY[0]) / 2 * s, (L.PLAY[3] - L.PLAY[1]) / 2 * s
        d.rounded_rectangle(box(bx - hw, by - hh, bx + hw, by + hh), radius=6 * s * K, fill=fill,
                            outline=(255, 230, 160), width=px(1))
        nudge = 0.5 if down else 0.0
        d.text(((bx + nudge) * K, (by + nudge) * K), "PLAY", font=font("ariblk.ttf", 12.0 * s), fill=(255, 255, 255),
               anchor="mm")
    return img


# ---- The game --------------------------------------------------------------------------------------------------------

class Game:
    """Odyssey played in the movie, from L.GAME to L.FREEZE: the ship's nose following the pointer (eased each frame,
    from beyond the movie's left edge), its bolts (one a click, from its nose), the rocks they hit, each placed where
    its bolt meets it, bursting into sparks and pieces with their points, the score counting up, a far rock drifting
    by over the bolts' paths, the sky scrolling. The mouse's pointer is hidden, as games hid it."""

    FOLLOW = 0.3            # how much of its way to the pointer the ship goes each frame
    BOLT = (14.0, 14.0)     # a bolt's speed (units a frame) and its length
    FLIGHTS = (8, 10, 7, 8)  # each bolt's frames from its click to its hit, so the rocks are hit here and there
    BURST = 18              # frames a burst lasts
    POINTS = 250            # a rock's

    def __init__(self):
        self.back = Backdrop(seed=5)
        self.ship = {}
        x, y = MX0 - 30.0, L.pointer(L.GAME)[1]
        for f in range(L.GAME, L.FREEZE + 1):
            tx, ty = L.pointer(f)
            x += (tx - NOSE - x) * self.FOLLOW
            y += (ty - y) * self.FOLLOW
            self.ship[f] = (x, y)
        rng = random.Random(11)
        speed, length = self.BOLT
        self.bolts, self.rocks = [], []
        for fired, frames in zip(L.SHOTS, self.FLIGHTS):
            sx, sy = self.ship[fired]
            r = rng.uniform(10.0, 13.5)
            hit = fired + frames
            self.bolts.append((fired, hit, sx + NOSE, sy))
            self.rocks.append(Rock(rng, r, (sx + NOSE + speed * frames + length + r * 0.3, sy), hit,
                                   speed=rng.uniform(1.8, 2.5), drift=rng.uniform(-0.2, 0.2)))
        self.far = Rock(rng, 16.0, (MX0 + 268.0, MY0 + 26.0), L.GAME, speed=0.8, drift=-0.03)
        self.sparks = [[(rng.uniform(0, 2 * math.pi), rng.uniform(1.4, 3.4)) for _ in range(16)] for _ in L.SHOTS]
        self.pieces = [[(rng.uniform(0, 2 * math.pi), rng.uniform(0.9, 1.8)) for _ in range(4)] for _ in L.SHOTS]

    def score(self, f):
        """The score shown at frame f: each rock's points counting up over 8 frames from its hit."""
        shown = sum(self.POINTS * phase(f, rock.frame, rock.frame + 8) for rock in self.rocks)
        return int(shown) // 10 * 10

    def frame(self, f):
        """The movie at frame f (from L.GAME to L.FREEZE)."""
        img, d = self.back.draw(1.1 * (f - L.GAME), MW * 0.74 - 0.22 * (f - L.GAME), f / L.FPS)
        self.far.draw(d, f)
        speed, length = self.BOLT
        for k, rock in enumerate(self.rocks):
            age = f - rock.frame
            if age < 0:
                if rock.where(f)[0] - rock.r * 1.2 < MX1:
                    rock.draw(d, f)
            elif age < self.BURST:
                self.burst(d, k, rock, age)
        for fired, hit, x0, y in self.bolts:
            if fired <= f < hit:
                tail = x0 + speed * (f - fired) - MX0
                d.line(box(tail, y - MY0, tail + length, y - MY0), fill=(80, 220, 255, 120), width=px(4))
                d.line(box(tail, y - MY0, tail + length, y - MY0), fill=(230, 255, 255), width=px(1.6))
        x, y = self.ship[f]
        last_x, last_y = self.ship.get(f - 1, (x, y))       # its nose up as it climbs, its flame longer as it speeds up
        draw_ship(d, x - MX0, y - MY0, SHIP, angle=max(-16.0, min(16.0, -(y - last_y) * 2.2)),
                  flame=10 + 3 * math.sin(f * 1.7) + max(0.0, x - last_x) * 0.8)
        d.text((8 * K, 10 * K), f"SCORE {self.score(f):06d}", font=font("verdanab.ttf", 8.0), fill=(255, 255, 255),
               anchor="lm")
        for k in range(3):
            draw_ship(d, MW - 12 - k * 14, 10, 0.45, flame=6)
        return img

    def burst(self, d, k, rock, age):
        """Rock k bursting, age frames after its bolt hit it: a flash, sparks flying out and fading, pieces of it
        tumbling away, its points rising."""
        x, y = rock.where(rock.frame)
        x, y = x - MX0, y - MY0
        t = age / self.BURST
        if age < 7:
            q = age / 7
            r = rock.r * (0.7 + 1.3 * q)
            d.ellipse(box(x - r, y - r, x + r, y + r), fill=(255, 244, 200, round(230 * (1 - q) ** 1.5)))
        for a, v in self.sparks[k]:
            reach = v * 7 * (1 - math.exp(-age / 7))
            r = 2.0 * (1 - t) + 0.3
            sx, sy = x + reach * math.cos(a), y + reach * math.sin(a)
            d.ellipse(box(sx - r, sy - r, sx + r, sy + r), fill=mix((255, 236, 140), (255, 110, 40), t) +
                      (round(255 * (1 - t * t)),))
        fade = round(255 * (1 - max(0.0, age - 8) / (self.BURST - 8)))
        for a, v in self.pieces[k]:
            reach = v * age
            cx, cy = x + reach * math.cos(a), y + reach * math.sin(a)
            r = rock.r * 0.3
            turn = a + age * 0.3
            d.polygon([((cx + r * math.cos(turn + j * 2.1)) * K, (cy + r * math.sin(turn + j * 2.1)) * K)
                       for j in range(3)], fill=(140, 96, 70, fade))
        d.text((x * K, (y - rock.r - 3 - 0.7 * age) * K), f"+{self.POINTS}", font=font("verdanab.ttf", 7.0),
               fill=(255, 230, 90, fade), anchor="mm", stroke_width=px(0.8), stroke_fill=(70, 20, 10, fade))


# ---- The right-click menu --------------------------------------------------------------------------------------------

def menu(highlight=None, alpha=1.0):
    """The Flash Player's right-click menu, its top left at L.MENU_AT, as a layer the screen's size: its shadow, its
    items and separators, highlight (an item, or None) lit as the pointer is on it; alpha fades it in."""
    mx, my = L.MENU_AT
    layer = Image.new("RGBA", (round(W * K), round(H * K)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    width, height = L.MENU_WIDTH, L.menu_height()
    d.rectangle(box(mx + 3, my + 3, mx + width + 3, my + height + 3), fill=(0, 0, 0, 90))
    d.rectangle(box(mx, my, mx + width, my + height), fill=(245, 245, 245, 255), outline=(130, 130, 130, 255),
                width=px(1))
    for item, top, bottom in L.menu_rows(mx, my):
        middle = (top + bottom) / 2
        if not item:
            d.line(box(mx + 4, middle, mx + width - 4, middle), fill=(190, 190, 190, 255), width=px(1))
            continue
        lit = item == highlight
        if lit:
            d.rectangle(box(mx + 2, top, mx + width - 2, bottom), fill=(49, 106, 197, 255))
        ink = (255, 255, 255, 255) if lit else (0, 0, 0, 255)
        d.text(((mx + 14) * K, middle * K), item, font=font("tahoma.ttf", 7.0), fill=ink, anchor="lm")
        if item == "Quality":
            d.text(((mx + width - 8) * K, middle * K), "▸", font=font("seguisym.ttf", 7.0), fill=ink, anchor="mm")
    if alpha < 1.0:
        layer.putalpha(layer.getchannel("A").point(lambda a: round(a * alpha)))
    return layer


def menu_item(x, y):
    """The menu's item under the pointer's tip at (x, y), or None (outside it, or on a separator)."""
    mx, my = L.MENU_AT
    if not (mx < x < mx + L.MENU_WIDTH and my < y < my + L.menu_height()):
        return None
    return next((item or None for item, top, bottom in L.menu_rows(mx, my) if top <= y < bottom), None)


# ---- The still and the printing --------------------------------------------------------------------------------------

def still():
    """The page just loaded from Go: the preloader at 0% and the pointer on Go. The video's first and last frame."""
    return screen(preloader(0.0), cursor=L.REST + (False, False))


def plate():
    x, y, w, h = L.REGIONS["plate"]
    img = Image.new("RGB", (w * SS, h * SS), rgb(L.COLOURS["silver"]))
    ImageDraw.Draw(img).text((w / 2 * SS, h / 2 * SS), "ODYSSEY", fill=(70, 72, 78), anchor="mm",
                             font=ImageFont.truetype(FONTS + "arialbd.ttf", 22 * SS))
    return img.resize((w, h), Image.LANCZOS)


def mouse_top():
    x, y, w, h = L.REGIONS["mouse"]
    img = Image.new("RGB", (w * SS, h * SS), rgb(L.COLOURS["mouse"]))
    d = ImageDraw.Draw(img)
    split = L.MOUSE["split"] / L.MOUSE["size"][1] * h
    d.line([0, split * SS, w * SS, split * SS], fill=(110, 112, 118), width=SS)
    d.line([w / 2 * SS, 0, w / 2 * SS, split * SS], fill=(110, 112, 118), width=SS)
    d.rounded_rectangle([(w / 2 - 6) * SS, split * 0.25 * SS, (w / 2 + 6) * SS, split * 0.75 * SS], radius=5 * SS,
                        fill=(60, 62, 66))
    return img.resize((w, h), Image.LANCZOS)


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (10, 10, 12))
    for name, art in (("plate", plate()), ("mouse", mouse_top())):
        x, y, _, _ = L.REGIONS[name]
        image.paste(art, (x, y))
    d = ImageDraw.Draw(image)
    for name, colour in (("silver", rgb(L.COLOURS["silver"])), ("black", rgb(L.COLOURS["black"])),
                         ("blue", (70, 160, 255)), ("grey", rgb(L.COLOURS["mouse"]))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    for name, img in (("flash_print.png", image), ("flash_screen.png", still())):
        path = os.path.join(out, name)
        img.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1])
