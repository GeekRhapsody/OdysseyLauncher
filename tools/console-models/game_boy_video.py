"""The console theme's Game Boy and Game Boy Color cards' videos (godot/themes/console/videos/gb.mp4 and gbc.mp4): each
card's lens through its focused clip, which the launcher plays on the card's `video` material, starting it again each
time the clip loops (A6 Card videos).

It follows the clip (game_boy.py) frame for frame, by game_boy_layout.py's TIMING and MOVES: the LCD switched off while
the cartridge goes in; the power light and the LCD coming on as the switch reaches ON; the hardware's start-up; the
made-up game's title, PUSH START blinking until START is pressed; the game played, the D-pad and the buttons moving it
in step with the model's; the picture fading as the switch goes OFF, which is also the first frame, so the loop is
seamless.

- Game Boy: the logo scrolls down to the middle of the blank LCD and stops; Kaleidrop, a made-up puzzle game, in the
  DMG's four greens at 160 x 144, its LCD slow to change (each frame keeps some of the last, as the DMG's smears) with
  its pixels' faint shadow: a pair of jewels falls, steps left twice, is cycled with A and dropped with down; it lands
  beside two of its kind, the three flash and shatter, and the score rolls up; the next pair falls.
- Game Boy Color: its start-up (the GAME BOY letters coming in one by one in a flash of colour, Nintendo under them);
  Ghoulish Gus, a made-up platform game, in the Color's 15-bit colour: Gus floats through a haunted funfair as it
  scrolls, says boo with A and darts ahead with B, the score and the boos counting up.

The games' art is tools/made-up-games's (their paintings, logos and key art): no real game's. Each frame is the lens
as game_boy_print.Lens composes it, encoded by card_video.py. Run from the repo root (Pillow, numpy, scipy; ffmpeg on
the PATH):

    python tools/console-models/game_boy_video.py artifacts/made-up-games gb godot/themes/console/videos/gb.mp4

and the same with gbc and gbc.mp4.
"""

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_boy_layout as L  # noqa: E402
import game_boy_print as P  # noqa: E402
from card_video import encode  # noqa: E402

W, H = 160, 144                                # the LCD's pixels


def phase(f, f0, f1):
    return min(1.0, max(0.0, (f - f0) / (f1 - f0)))


def hexes(colours):
    return np.array([P.rgb(c)[:3] for c in colours], np.float32)


BRACKETS = {"(": "...#.|..#..|.#...|.#...|.#...|..#..|...#.", ")": ".#...|..#..|...#.|...#.|...#.|..#..|.#..."}


def glyph_text(s):
    """Text in the made-up games' 5 x 7 bitmap font (tools/made-up-games/screens.py), with brackets, as a bool array."""
    import screens
    if not s:
        return np.zeros((7, 1), bool)

    def cell(ch):
        if ch in BRACKETS:
            rows = BRACKETS[ch].split("|")
            return np.array([[c == "#" for c in r] + [False] for r in rows], bool)
        return screens._glyph(ch)
    cells = [cell(ch) for ch in s.upper()]
    out = np.zeros((7, len(s) * screens.ADVANCE), bool)
    for k, g in enumerate(cells):
        out[:, k * screens.ADVANCE:k * screens.ADVANCE + g.shape[1]] |= g
    return out[:, :-1]


def stamp(canvas, mask, x, y, value):
    """Sets canvas to value where mask is set, mask's top left at (x, y), clipped."""
    h, w = mask.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(canvas.shape[1], x + w), min(canvas.shape[0], y + h)
    if x0 >= x1 or y0 >= y1:
        return
    sub = mask[y0 - y:y1 - y, x0 - x:x1 - x]
    canvas[y0:y1, x0:x1][sub] = value


def rendered(s, font, height, threshold=110, italic=0.0):
    """Text drawn small, as the LCD's pixels: rendered big, cut to its ink, scaled to height rows and thresholded."""
    big = ImageFont.truetype(P.FONTS + font, 200)
    left, top, right, bottom = big.getbbox(s)
    img = Image.new("L", (right - left + 60, bottom - top + 40), 0)
    ImageDraw.Draw(img).text((30 - left, 20 - top), s, font=big, fill=255)
    if italic:
        img = img.transform(img.size, Image.AFFINE, (1, italic, -italic * img.height / 2, 0, 1, 0), Image.BICUBIC)
    img = img.crop(img.getbbox())
    w = max(1, round(img.width * height / img.height))
    return np.asarray(img.resize((w, height), Image.BOX)) > threshold


# ---- The Game Boy: the DMG's start-up and Kaleidrop --------------------------------------------------------------------

def dmg_logo():
    """The start-up logo: Nintendo in 48 x 8 pixels, each doubled, and the (R) beside it."""
    logo = rendered("Nintendo", "arialbd.ttf", 8, threshold=120)
    small = np.zeros((8, 48), bool)
    w = min(48, logo.shape[1])
    small[:, (48 - w) // 2:(48 - w) // 2 + w] = logo[:, :w]
    big = np.kron(small, np.ones((2, 2), bool))
    mark = np.zeros((8, 8), bool)
    yy, xx = np.mgrid[0:8, 0:8]
    ring = (xx - 3.5) ** 2 + (yy - 3.5) ** 2
    mark[(ring <= 12.5) & (ring >= 6.0)] = True
    mark[2:6, 3] = True
    mark[2, 3:5] = mark[3, 5] = mark[4, 3:5] = mark[5, 5] = True
    return big, mark


# The jewels: 8 x 8 tiles in the four shades (0 the lightest), "." showing what's behind.
JEWELS = [
    ["...33...", "..3003..", ".301103.", "30111103", ".311113.", "..3113..", "...33...", "........"],   # a diamond
    ["..3333..", ".322223.", "32022223", "32222223", "32222223", ".322223.", "..3333..", "........"],   # an orb
    ["33333333", "31111113", "31333313", "31300313", "31300313", "31333313", "31111113", "33333333"],   # a block
    ["...33...", "...33...", "..3113..", "..3013..", ".311113.", ".311113.", "32222223", "33333333"],   # a pyramid
]


def tile(rows):
    out = np.full((8, 8), -1, np.int8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                out[y, x] = int(ch)
    return out


TILES = [tile(t) for t in JEWELS]


def put_tile(canvas, t, x, y, invert=False):
    h, w = t.shape
    sub = canvas[y:y + h, x:x + w]
    m = t[:sub.shape[0], :sub.shape[1]] >= 0
    vals = t[:sub.shape[0], :sub.shape[1]]
    sub[m] = (3 - vals[m]) if invert else vals[m]


class Kaleidrop:
    """Kaleidrop on the DMG: its title, and a moment of play (frames after `play`), as shade arrays."""

    COLS, ROWS = 6, 14
    WELL = (16, 16)                         # the well's top left, in pixels
    GRID = [[2, 1, 3, 0, 2, 1], [3, 0, 1, 2, 1, 3], [1, 2, 0, 3, 0, 2], [0, 0, None, 1, 2, None],
            [2, None, None, 0, None, None]]

    def __init__(self, game):
        self.game = game
        self.logo = self.logo_shades()
        self.back = self.backdrop()

    def logo_shades(self):
        """The game's title lettered in pixels, as a Game Boy title was drawn: chunky letters in the darkest shade, a
        lit line along their tops, a light edge parting them from their shadow two pixels down and to the right."""
        height = 18
        a = rendered(self.game.title.upper(), "ariblk.ttf", height, threshold=128)
        while a.shape[1] > W - 20:                     # fitted inside the screen, its shadow and edge included
            height -= 1
            a = rendered(self.game.title.upper(), "ariblk.ttf", height, threshold=128)
        h, w = a.shape
        out = np.full((h + 4, w + 4), -1, np.int8)
        body = np.zeros(out.shape, bool)
        body[1:h + 1, 1:w + 1] = a
        shadow = np.roll(np.roll(body, 2, 0), 2, 1)
        edge = ndimage.binary_dilation(body, iterations=1)
        out[shadow] = 2
        out[edge & ~body] = 0
        out[body] = 3
        lit = body & ~np.roll(body, 1, 0)
        out[lit & body] = 1
        return out

    def backdrop(self):
        """Behind the well: the light shade, dotted."""
        yy, xx = np.mgrid[0:H, 0:W]
        return np.where((xx % 4 == 0) & (yy % 4 == 0), 2, 1).astype(np.int8)

    def text(self, canvas, s, x, y, value, shadow=None):
        g = glyph_text(s)
        if shadow is not None:
            stamp(canvas, g, x + 1, y + 1, shadow)
        stamp(canvas, g, x, y, value)

    # -- The title -------------------------------------------------------------------------------------------------
    def title(self, t, prompt):
        """The title screen t frames in; prompt: PUSH START shown."""
        c = np.zeros((H, W), np.int8)
        # Rows of jewels drifting along the top and the bottom.
        shift = (t // 2) % 8
        for row, y, way in ((0, 2, 1), (1, H - 10, -1)):
            for k in range(-1, 21):
                put_tile(c, TILES[(k + row * 2) % 4], k * 8 + way * shift, y)
        lh, lw = self.logo.shape
        ly = 22
        sub = c[ly:ly + lh, (W - lw) // 2:(W - lw) // 2 + lw]
        m = self.logo >= 0
        sub[m] = self.logo[m]
        # A row of big jewels under the title, bobbing in turn.
        for k in range(4):
            big = np.kron(TILES[k], np.ones((2, 2), np.int8))
            bob = int(round(2 * math.sin((t + k * 6) * 2 * math.pi / 24)))
            x = 28 + k * 28
            put_tile(c, big, x, 58 + bob)
        if prompt:
            self.text(c, "PUSH START", (W - 69) // 2, 94, 3, shadow=1)
        self.text(c, "(C)" + self.game.year + " VELVET COMET", (W - 139) // 2, 118, 2)
        return c

    # -- Play ------------------------------------------------------------------------------------------------------
    def well(self, c, grid, flash=None, fall=None):
        """The well and its jewels; flash: cells drawn inverted; fall: {col: (from_row, offset in pixels)}."""
        x0, y0 = self.WELL
        c[y0 - 4:y0 + self.ROWS * 8 + 4, x0 - 4:x0 + self.COLS * 8 + 4] = 3
        c[y0 - 3:y0 + self.ROWS * 8 + 3, x0 - 3:x0 + self.COLS * 8 + 3] = 2
        c[y0 - 1:y0 + self.ROWS * 8 + 1, x0 - 1:x0 + self.COLS * 8 + 1] = 3
        c[y0:y0 + self.ROWS * 8, x0:x0 + self.COLS * 8] = 0
        for r, row in enumerate(grid):
            for col, kind in enumerate(row):
                if kind is None:
                    continue
                dy = 0
                if fall and col in fall and r >= fall[col][0]:
                    dy = fall[col][1]
                y = y0 + (self.ROWS - 1 - r) * 8 + dy
                put_tile(c, TILES[kind], x0 + col * 8, y, invert=bool(flash and (r, col) in flash))

    def panel(self, c, nxt, score, chain):
        x = 76
        c[12:52, x:x + 40] = 3
        c[13:51, x + 1:x + 39] = 0
        self.text(c, "NEXT", x + 7, 16, 3)
        put_tile(c, TILES[nxt[0]], x + 16, 28)
        put_tile(c, TILES[nxt[1]], x + 16, 36)
        self.text(c, "SCORE", x, 60, 3, shadow=1)
        c[70:82, x - 2:W - 4] = 0
        self.text(c, "%06d" % score, x + 1, 72, 3)
        self.text(c, "LEVEL", x, 90, 3, shadow=1)
        self.text(c, "03", x + 1, 100, 3)
        if chain:
            c[112:130, x - 2:W - 4] = 3
            self.text(c, "CHAIN", x + 2, 113, 0)
            self.text(c, "X1", x + 2, 121, 0)

    def play(self, p):
        """The game p frames after `play`."""
        moves = L.MOVES["gb"]
        c = self.back.copy()
        grid = [list(row) for row in self.GRID] + [[None] * self.COLS for _ in range(self.ROWS - len(self.GRID))]
        pair = [0, 1]                            # top, bottom
        nxt = (3, 2)
        score, chain, flash, fall = 12340, False, None, None
        a_press, b_press = moves["a"][0], moves["b"][0]
        if p < 6:
            col, row = None, None
            nxt = (0, 1)
        elif p < 34:
            col = 4 - sum(1 for f0, _ in moves["left"] if p >= f0)
            down_at = moves["down"][0][0]
            row = 12 - (min(p, down_at - 1) - 6) // 5
            if p >= down_at:
                row = max(3, row - (p - down_at + 1))
            if p >= a_press:
                pair = [1, 0]
        else:
            col, row = None, None
            grid[3][2], grid[4][2] = 0, 1           # the pair landed: a diamond under an orb
            if p < 48:
                if p >= 36 and ((p - 36) // 3) % 2 == 0:
                    flash = {(3, 0), (3, 1), (3, 2)}
            else:
                grid[3][0], grid[3][1], grid[3][2] = grid[4][0], None, grid[4][2]
                grid[4][0] = grid[4][2] = None
                if p < 52:
                    fall = {0: (3, -8 + 2 * (p - 48)), 2: (3, -8 + 2 * (p - 48))}
                score = 12340 + int(round(300 * phase(p, 50, 58)))
                chain = p < 62
            if p >= 54:
                nxt = (1, 3)
                col, row = 4, 12 - (p - 54) // 5
                pair = [3, 2] if p < b_press else [2, 3]
        self.well(c, grid, flash, fall)
        if col is not None:
            x0, y0 = self.WELL
            for k, kind in enumerate(pair):       # the top jewel, then the bottom one
                r = row + 1 - k
                if r < self.ROWS:
                    put_tile(c, TILES[kind], x0 + col * 8, y0 + (self.ROWS - 1 - r) * 8)
        self.panel(c, nxt, score, chain)
        return c


class DmgScreen:
    """The Game Boy's LCD through the clip: shade arrays to colours, the LCD's smear and its pixels' shadow."""

    def __init__(self, game):
        self.game = Kaleidrop(game)
        self.logo, self.mark = dmg_logo()
        self.palette = hexes(P.DMG_SHADES)
        self.off = np.array(P.rgb(P.DMG_OFF)[:3], np.float32)
        self.shown = None

    def shades(self, f):
        """The picture's shades at frame f (None: the LCD blank), and the palette's fade (0 normal, 3 white)."""
        T = L.TIMING["gb"]
        if f < T["boot"][0]:
            return None, 0
        if f < T["handover"]:
            c = np.zeros((H, W), np.int8)
            y = int(round(-16 + 80 * phase(f, *T["boot"])))
            stamp(c, self.logo, 32, y, 3)
            stamp(c, self.mark, 130, y, 3)
            return c, 0
        if f < T["title"]:
            return None, 0
        if f < T["play"]:
            t = f - T["title"]
            if f < T["start"]:
                prompt = t % 24 < 16
            else:
                prompt = ((f - T["start"]) // 2) % 2 == 0
            fade = max(0, 3 - t // 2) if t < 6 else (min(3, (f - (T["play"] - 6)) // 2 + 1) if f >= T["play"] - 6 else 0)
            return self.game.title(t, prompt), fade
        p = f - T["play"]
        fade = max(0, 3 - p // 2) if p < 6 else 0
        return self.game.play(min(p, T["switch_off"][1] - T["play"])), fade

    def colours(self, f):
        """The LCD's colours at frame f, and how dark each pixel is driven (0 to 1: none while it's off)."""
        T = L.TIMING["gb"]
        if f < T["power"] or f >= T["lcd_off"][1]:
            return np.broadcast_to(self.off, (H, W, 3)).copy(), np.zeros((H, W), np.float32)
        shades, fade = self.shades(f)
        if shades is None:
            shades = np.zeros((H, W), np.int8)
        idx = np.clip(shades.astype(np.int16) - fade, 0, 3)
        img = self.palette[idx]
        on = phase(f, T["power"], T["power"] + 3)
        fading = phase(f, *T["lcd_off"])
        k = on * (1 - fading)
        return self.off + (img - self.off) * k, idx.astype(np.float32) / 3 * k

    def frame(self, f):
        target, ink = self.colours(f)
        if self.shown is None or f == 0:
            self.shown, self.ink = target, ink
        else:
            self.shown = self.shown + (target - self.shown) * 0.62     # the DMG's slow LCD
            self.ink = self.ink + (ink - self.ink) * 0.62
        # The driven pixels' faint shadow on the reflector behind them, a pixel down and to the right.
        shadow = np.zeros_like(self.ink)
        shadow[1:, 1:] = self.ink[:-1, :-1]
        out = self.shown * (1 - 0.13 * shadow[..., None])
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    def led(self, f):
        T = L.TIMING["gb"]
        return phase(f, T["power"], T["power"] + 4) * (1 - phase(f, T["switch_off"][1], T["switch_off"][1] + 4))


# ---- The Game Boy Color: its start-up and Ghoulish Gus -----------------------------------------------------------------

def gbc_colour(img):
    """A picture in the Color's 15-bit colour, as its LCD shows it: five bits a channel, a little washed out."""
    a = np.asarray(img.convert("RGB"), np.float32)
    a = np.round(a / 255 * 31) * 255 / 31
    grey = a.mean(axis=2, keepdims=True)
    a = grey + (a - grey) * 0.9
    return 18 + a * 0.9


def laplace_fill(a, mask, iterations=400):
    """Fills the masked pixels of an image (float array) smoothly from their surroundings."""
    out = a.copy()
    out[mask] = a[~mask].mean(axis=0)
    for _ in range(iterations):
        avg = (np.roll(out, 1, 0) + np.roll(out, -1, 0) + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 4
        out[mask] = avg[mask]
    return out


class GhoulishGus:
    """Ghoulish Gus on the Color: its title, and a moment of play, as RGB pictures at 160 x 144."""

    BOX = (176, 100, 296, 202)          # Gus in the painting (766 x 510): x0, y0, x1, y1
    CROP = (60, 470)                    # the rows of the painting the playfield shows

    def __init__(self, game):
        self.game = game
        painting = Image.open(game.painting).convert("RGB")
        self.painting = painting
        a = np.asarray(painting, np.float32)
        x0, y0, x1, y1 = self.BOX
        box = a[y0:y1, x0:x1]
        border = np.concatenate([box[0], box[-1], box[:, 0], box[:, -1]])
        sky = np.median(border, axis=0)
        rough = np.abs(box - sky).sum(axis=2) > 70
        rough = ndimage.binary_dilation(rough, iterations=2)
        filled = laplace_fill(box, rough)
        mask = np.abs(box - filled).sum(axis=2) > 45
        mask = ndimage.binary_closing(mask, iterations=1)
        mask = ndimage.binary_fill_holes(mask)
        lab, n = ndimage.label(mask)
        if n > 1:
            sizes = ndimage.sum(mask, lab, range(1, n + 1))
            mask = lab == (1 + int(np.argmax(sizes)))
        clean = a.copy()
        clean[y0:y1, x0:x1] = laplace_fill(box, ndimage.binary_dilation(mask, iterations=2))
        top, bottom = self.CROP
        k = H / (bottom - top)
        self.k = k
        field = Image.fromarray(clean[top:bottom].clip(0, 255).astype(np.uint8))
        field = field.resize((round(field.width * k), H), Image.LANCZOS)
        self.field = field.quantize(48, Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
        # Gus, cut out: his box at the playfield's scale, transparent round him.
        sprite = Image.fromarray(box.astype(np.uint8)).convert("RGBA")
        sprite.putalpha(Image.fromarray((mask * 255).astype(np.uint8)))
        size = (round(sprite.width * k), round(sprite.height * k))
        alpha = sprite.getchannel("A").resize(size, Image.BOX).point(lambda v: 255 if v > 120 else 0)
        colour = sprite.convert("RGB").resize(size, Image.LANCZOS).quantize(10, dither=Image.Dither.NONE).convert("RGB")
        self.gus = colour.convert("RGBA")
        self.gus.putalpha(alpha)
        logo = game.logo
        w = 150
        self.logo = logo.resize((w, max(1, round(logo.height * w / logo.width))), Image.LANCZOS)
        back = ImageOps.fit(painting, (W, H), Image.LANCZOS, centering=(0.4, 0.5))
        self.title_back = Image.eval(back.filter(ImageFilter.GaussianBlur(1.2)), lambda v: int(v * 0.5))

    def text(self, img, s, x, y, colour, shadow=(16, 8, 32)):
        a = np.asarray(img).copy()
        g = glyph_text(s)
        if shadow is not None:
            stamp(a, g, x + 1, y + 1, shadow)
        stamp(a, g, x, y, colour)
        return Image.fromarray(a)

    def title(self, t, prompt):
        img = self.title_back.copy().convert("RGBA")
        bob = int(round(2 * math.sin(t * 2 * math.pi / 30)))
        img.alpha_composite(self.logo, ((W - self.logo.width) // 2, 14 + bob))
        img = img.convert("RGB")
        if prompt:
            img = self.text(img, "PRESS START", (W - 76) // 2, 98, (255, 255, 255))
        img = self.text(img, "(C)" + self.game.year + " VELVET COMET", (W - 139) // 2, 124, (190, 170, 230))
        return img

    def play(self, p):
        moves = L.MOVES["gbc"]
        cam = min(self.field.width - W, p)
        img = self.field.crop((cam, 0, cam + W, H)).convert("RGBA")
        boo = sum(1 for f0 in moves["a"] if p >= f0 + 4)
        # Gus floats, drifting ahead as the funfair scrolls; B darts him forward; A says boo.
        dart = sum(10 * math.sin(math.pi * phase(p, f0, f0 + 10)) for f0 in moves["b"])
        x = 22 + 0.18 * p + dart
        y = 20 + 5 * math.sin(p * 2 * math.pi / 34)
        puff = max([math.sin(math.pi * phase(p, f0, f0 + 9)) for f0 in moves["a"]] + [0.0])
        gus = self.gus
        if puff > 0:
            gus = gus.resize((round(gus.width * (1 + 0.22 * puff)), round(gus.height * (1 + 0.22 * puff))), Image.NEAREST)
        img.alpha_composite(gus, (int(round(x - (gus.width - self.gus.width) / 2)),
                                  int(round(y - (gus.height - self.gus.height) / 2))))
        img = img.convert("RGB")
        for f0 in moves["a"]:
            if f0 + 2 <= p < f0 + 14:
                img = self.text(img, "BOO!", int(x + self.gus.width + 2), int(y + 4), (255, 236, 120), shadow=(60, 20, 70))
        img = self.text(img, "BOO %02d" % (7 + boo), 4, 3, (176, 255, 128))
        score = 2300 + 100 * (p // 16) + 50 * boo
        img = self.text(img, "SCORE %06d" % score, W - 4 - 83, 3, (255, 255, 255))
        return img


class GbcScreen:
    """The Game Boy Color's LCD through the clip."""

    def __init__(self, game):
        self.game = GhoulishGus(game)
        self.off = np.array(P.rgb(L.MODELS["gbc"]["colours"]["lcd_off"])[:3], np.float32)
        self.white = np.array([234, 234, 226], np.float32)
        self.shown = None
        letters = "GAME BOY"
        big = ImageFont.truetype(P.FONTS + "GOTHICBI.TTF", 200)
        full = rendered(letters, "GOTHICBI.TTF", 16, italic=0.0)
        self.word = full
        # Each letter's columns in the word: by the font's advances, scaled to the rendered width.
        total = big.getlength(letters)
        scale = full.shape[1] / total
        self.letters = []
        for k, ch in enumerate(letters):
            if ch == " ":
                continue
            a0, a1 = big.getlength(letters[:k]) * scale, big.getlength(letters[:k + 1]) * scale
            self.letters.append((int(math.floor(a0)), int(math.ceil(a1))))
        self.nintendo = rendered("Nintendo", "arialbd.ttf", 9, threshold=120)

    def boot(self, f):
        """The Color's start-up at frame f (from `boot`)."""
        T = L.TIMING["gbc"]
        img = np.broadcast_to(np.array([248, 248, 248], np.float32), (H, W, 3)).copy()
        t = f - T["boot"][0]
        word = self.word
        wh, ww = word.shape
        x0, y0 = (W - ww) // 2, 52
        flashes = [(232, 33, 58), (244, 194, 28), (45, 184, 74), (47, 108, 224), (155, 63, 216)]
        navy = np.array([30, 42, 140], np.float32)
        # A ring of colours swells behind the word as the letters come in.
        yy, xx = np.mgrid[0:H, 0:W]
        if t >= 0:
            r = 6 + 2.6 * t
            fade = 0.75 * (1 - phase(t, 16, 30))
            d = np.hypot(xx - W / 2, (yy - (y0 + wh / 2)) * 1.4)
            for k, col in enumerate(flashes):
                band = (d > r - 6 * (k + 1)) & (d <= r - 6 * k)
                img[band] = img[band] + (np.array(col, np.float32) - img[band]) * 0.55 * fade
        for k, (a, b) in enumerate(self.letters):
            start = 3 * k
            if t < start:
                continue
            settle = phase(t, start + 2, start + 9)
            flash = np.array(flashes[k % len(flashes)], np.float32)
            colour = flash + (navy - flash) * settle
            mask = np.zeros((H, W), bool)
            sub = word[:, a:b]
            mask[y0:y0 + wh, x0 + a:x0 + b] = sub
            bounce = int(round(-3 * math.sin(math.pi * phase(t, start, start + 6))))
            mask = np.roll(mask, bounce, axis=0)
            img[mask] = colour
        if t >= 30:
            k = phase(t, 30, 40)
            nh, nw = self.nintendo.shape
            mask = np.zeros((H, W), bool)
            mask[86:86 + nh, (W - nw) // 2:(W - nw) // 2 + nw] = self.nintendo
            img[mask] = img[mask] + (np.array([120, 120, 132], np.float32) - img[mask]) * k
        return img

    def colours(self, f):
        T = L.TIMING["gbc"]
        if f < T["power"] or f >= T["lcd_off"][1]:
            return np.broadcast_to(self.off, (H, W, 3)).copy()
        on = phase(f, T["power"], T["power"] + 4)
        if f < T["boot"][0]:
            pic = np.broadcast_to(np.array([248, 248, 248], np.float32), (H, W, 3)).copy()
        elif f < T["handover"]:
            pic = self.boot(f)
            pic = pic + (248 - pic) * phase(f, T["handover"] - 8, T["handover"])
        elif f < T["title"]:
            pic = np.broadcast_to(np.array([248, 248, 248], np.float32), (H, W, 3)).copy()
        elif f < T["play"]:
            t = f - T["title"]
            prompt = t % 24 < 16 if f < T["start"] else ((f - T["start"]) // 2) % 2 == 0
            pic = np.asarray(self.game.title(t, prompt), np.float32)
            white = 1 - phase(t, 0, 6) + phase(f, T["play"] - 6, T["play"])
            pic = pic + (248 - pic) * min(1.0, white)
        else:
            p = min(f - T["play"], T["switch_off"][1] - T["play"])
            pic = np.asarray(self.game.play(p), np.float32)
            pic = pic + (248 - pic) * (1 - phase(f, T["play"], T["play"] + 6))
        pic = gbc_colour(Image.fromarray(np.clip(pic, 0, 255).astype(np.uint8)))
        k = on * (1 - phase(f, *T["lcd_off"]))
        return self.off + (pic - self.off) * k

    def frame(self, f):
        target = self.colours(f)
        if self.shown is None or f == 0:
            self.shown = target
        else:
            self.shown = self.shown + (target - self.shown) * 0.85
        return Image.fromarray(np.clip(self.shown, 0, 255).astype(np.uint8))

    def led(self, f):
        T = L.TIMING["gbc"]
        return phase(f, T["power"], T["power"] + 4) * (1 - phase(f, T["switch_off"][1], T["switch_off"][1] + 4))


def frames(kind, made_up_dir):
    game = P.made_up(made_up_dir, kind)
    screen = DmgScreen(game) if kind == "gb" else GbcScreen(game)
    lens = P.Lens(kind)
    for f in range(L.LENGTH):
        yield lens.frame(screen.frame(f), screen.led(f))


def main():
    made_up_dir, kind, out = os.path.abspath(sys.argv[1]), sys.argv[2], os.path.abspath(sys.argv[3])
    encode(out, L.MODELS[kind]["video"], L.FPS, frames(kind, made_up_dir), L.MODELS[kind]["name"])


if __name__ == "__main__":
    main()
