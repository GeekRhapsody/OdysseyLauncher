"""The made-up games' screenshots at their systems' native resolutions: a Codex painting of the game's screen cut (or
padded) to the screen's shape, scaled to its pixels and brought to the console's palette, then the game's HUD drawn
over it in a bitmap font, since painted text comes out garbled."""

import math

import numpy as np
from PIL import Image

import paint as P

NATIVE = {"megadrive": (320, 224), "snes": (256, 224), "n64": (320, 240), "arcade": (320, 224), "arcade_v": (224, 288),
          "arcade8": (256, 224), "arcade8_v": (224, 288), "arcade3d": (640, 480), "arcade_hd": (1280, 720)}

# The shape a look's screen was shown at, where its pixels weren't square.
DISPLAY = {"arcade8": (4, 3), "arcade8_v": (3, 4)}

# An early-1980s board's 3-3-2 colour: eight levels of red and of green, four of blue.
LEVELS_332 = [np.array([0, 36, 73, 109, 146, 182, 219, 255], np.float32)] * 2 + [np.array([0, 85, 170, 255], np.float32)]

# The Mega Drive's DAC levels, per 3-bit channel; the SNES has 5 bits a channel, linear.
MD_LEVELS = np.array([0, 52, 87, 116, 144, 172, 206, 255], np.float32)

# A 5 x 7 font, drawn bold (each row ORed with itself a pixel to the right) in 7-pixel cells.
_GLYPHS = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####", "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.####", "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.", "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", "N": "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.", "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#", "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.", "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.", "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####", "3": "#####|...#.|..#..|...#.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.", "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    ":": ".....|.##..|.##..|.....|.##..|.##..|.....", ".": ".....|.....|.....|.....|.....|.##..|.##..",
    ",": ".....|.....|.....|.....|.##..|..#..|.#...", "!": "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..", "-": ".....|.....|.....|#####|.....|.....|.....",
    "/": "....#|...#.|...#.|..#..|.#...|.#...|#....", "'": "..#..|..#..|.#...|.....|.....|.....|.....",
    "+": ".....|..#..|..#..|#####|..#..|..#..|.....", " ": ".....|.....|.....|.....|.....|.....|.....",
}
ADVANCE = 7


def _glyph(ch):
    rows = _GLYPHS.get(ch, _GLYPHS["?"]).split("|")
    g = np.array([[c == "#" for c in r] + [False, False] for r in rows], bool)
    # Bold: each pixel doubled to the right, except into a one-pixel gap (so M and W keep their strokes apart).
    gap = ~g[:, 1:-1] & g[:, 2:]
    grow = g[:, :-2] & ~gap
    g[:, 1:-1] |= grow
    return g[:, :-1]


def text_width(s, scale=1):
    return (len(s) * ADVANCE - 1) * scale


def text(img, x, y, s, colour, shadow="#000000", scale=1, outline=False):
    """Bitmap text on a uint8 RGB array at native resolution: a drop shadow, or a full outline."""
    col = (P.rgb(colour) * 255).astype(np.uint8)
    sh = (P.rgb(shadow) * 255).astype(np.uint8) if shadow else None
    H, W = img.shape[:2]

    def stamp(px, py, colour_):
        for k, ch in enumerate(s.upper()):
            g = np.kron(_glyph(ch), np.ones((scale, scale), bool))
            ys, xs = np.nonzero(g)
            ys, xs = ys + py, xs + px + k * ADVANCE * scale
            ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
            img[ys[ok], xs[ok]] = colour_

    if sh is not None:
        offsets = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy] if outline else [(scale, scale)]
        for dx, dy in offsets:
            stamp(x + dx, y + dy, sh)
    stamp(x, y, col)
    return img


def wrap(s, width):
    """Words in lines of at most width pixels of bitmap text."""
    lines, line = [], ""
    for word in s.split():
        trial = f"{line} {word}".strip()
        if text_width(trial) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


# Paintings to screens ----------------------------------------------------------------------------------------------

def _shape(img, w, h, fit, focus):
    """The painting brought to w:h: cut round focus, or (fit = "pad") widened by mirroring its edges."""
    aw, ah = img.size
    target = w / h
    if fit == "pad":
        a = np.asarray(img)
        if aw / ah < target:
            extra = int(round(ah * target)) - aw
            a = np.pad(a, ((0, 0), (extra // 2, extra - extra // 2), (0, 0)), mode="reflect")
        else:
            extra = int(round(aw / target)) - ah
            a = np.pad(a, ((extra // 2, extra - extra // 2), (0, 0), (0, 0)), mode="reflect")
        return Image.fromarray(a)
    cw, ch = (int(round(ah * target)), ah) if aw / ah > target else (aw, int(round(aw / target)))
    x, y = int((aw - cw) * focus[0]), int((ah - ch) * focus[1])
    return img.crop((x, y, x + cw, y + ch))


def native(painting, system, look, fit="crop", focus=(0.5, 0.5)):
    """A painting of a game's screen at its look's (or its system's) resolution and in its palette, as a uint8 RGB
    array."""
    w, h = NATIVE.get(look) or NATIVE[system]
    img = painting.convert("RGB")
    if img.size != (w, h):
        # An 8-bit board's pixels weren't square: its picture was shown 4:3 (3:4 on its side), so the painting, which
        # is what the monitor showed, is cut to that and squeezed into the board's pixels.
        sw, sh = DISPLAY.get(look, (w, h))
        img = _shape(img, sw, sh, fit, focus).resize((w, h), Image.BOX)
    a = np.asarray(img, dtype=np.float32)
    if look.startswith("arcade8"):
        # 3-3-2 colour, then at most 16 colours on screen, snapped back to the 3-3-2 levels.
        def snap(x):
            return np.stack([LEVELS_332[c][np.abs(x[..., c, None] - LEVELS_332[c]).argmin(axis=-1)] for c in range(3)], -1)

        img = Image.fromarray(snap(a).astype(np.uint8)).quantize(16, Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        return snap(np.asarray(img.convert("RGB"), dtype=np.float32)).astype(np.uint8)
    if look in ("arcade3d", "arcade_hd"):
        return np.asarray(img).copy()                            # 3D boards of the late 1990s on: 24-bit colour
    if system == "megadrive":
        # Each channel to the nearest of the console's eight levels, then at most 61 colours on screen.
        a = MD_LEVELS[np.abs(a[..., None] - MD_LEVELS).argmin(axis=-1)]
        img = Image.fromarray(a.astype(np.uint8)).quantize(61, Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        return np.asarray(img.convert("RGB")).copy()
    if system in ("snes", "arcade"):
        a = np.round(a / 255 * 31) * 255 / 31
        img = Image.fromarray(a.astype(np.uint8)).quantize(192, Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        return np.asarray(img.convert("RGB")).copy()
    # The N64: its 16-bit frame buffer, dithered, as it went to the screen.
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 - 0.5
    d = np.tile(bayer, (h // 4 + 1, w // 4 + 1))[:h, :w, None] * (255 / 31)
    return np.clip(np.round((a + d) / 255 * 31) * 255 / 31, 0, 255).astype(np.uint8)


# HUDs --------------------------------------------------------------------------------------------------------------

def _window(img, x0, y0, x1, y1):
    """A role-playing game's message window: a blue gradient, a white border, cut corners."""
    grad = P.ramp(np.linspace(0, 1, y1 - y0)[:, None], [(0, "#3a3ad0"), (1, "#0a0a5c")]) * 255
    img[y0:y1, x0:x1] = grad.astype(np.uint8)
    white, dark = np.array([236, 236, 248], np.uint8), np.array([16, 16, 40], np.uint8)
    for (ya, yb, xa, xb), c in [((y0, y0 + 1, x0, x1), dark), ((y1 - 1, y1, x0, x1), dark), ((y0, y1, x0, x0 + 1), dark),
                                ((y0, y1, x1 - 1, x1), dark), ((y0 + 1, y0 + 3, x0 + 1, x1 - 1), white),
                                ((y1 - 3, y1 - 1, x0 + 1, x1 - 1), white), ((y0 + 1, y1 - 1, x0 + 1, x0 + 3), white),
                                ((y0 + 1, y1 - 1, x1 - 3, x1 - 1), white)]:
        img[ya:yb, xa:xb] = c
    for cx, cy in [(x0, y0), (x1 - 1, y0), (x0, y1 - 1), (x1 - 1, y1 - 1)]:
        img[cy, cx] = 0


def _unit(img):
    """The HUD's pixel size: 1 on a screen of up to 359 lines, 2 at 480, 3 at 720."""
    return max(1, round(img.shape[0] / 240))


def _bar(img, x, y, w, fill, height=7):
    """A health bar: a dark frame, filled yellow to red from the left."""
    k = max(1, height // 7)
    img[y:y + height, x:x + w] = (16, 16, 24)
    inner = int((w - 2 * k) * fill)
    ramp = P.ramp(np.linspace(0, 1, max(inner, 1))[None, :], [(0, "#ff3a20"), (1, "#ffe040")])[0] * 255
    img[y + k:y + height - k, x + k:x + k + inner] = ramp.astype(np.uint8)
    img[y + k:y + 2 * k, x + k:x + k + inner] = np.minimum(ramp.astype(np.int32) + 60, 255).astype(np.uint8)


def _items(img, items):
    """HUD items from games.toml: [text, place, colour, scale]; "BAR n" draws a bar n full. Places tl tc tr bl bc br
    are the screen's corners and edges; tl2 tc2 tr2 bl2 bc2 br2 a row further in. Sizes grow with the screen."""
    h, w = img.shape[:2]
    u = _unit(img)
    for item in items:
        s, place = item[0], item[1]
        colour = item[2] if len(item) > 2 else "#ffffff"
        scale = (item[3] if len(item) > 3 else 1) * u
        row2 = place.endswith("2")
        edge = place[0]
        across = place[1]
        bar = s.startswith("BAR ")
        width = int(w * 0.3) if bar else text_width(s, scale)
        height = 7 * u if bar else 7 * scale
        x = {"l": 8 * u, "c": (w - width) // 2, "r": w - 8 * u - width}[across]
        y = (5 + (11 if row2 else 0)) * u if edge == "t" else (h - (6 + (11 if row2 else 0)) * u - height)
        if bar:
            _bar(img, x, y, width, float(s[4:]), height)
        else:
            text(img, x, y, s, colour, outline=scale > u, shadow="#000000")


def _versus(img, spec):
    """A 3D fighting game's HUD: the two health bars along the top, their remaining health towards the timer between
    them, the fighters' names and their rounds won, and a combo's hits. Chunky and bitmapped on a screen under 600
    lines (the late 1990s); slanted, smooth and in a typeface on an HD one (the 2010s)."""
    h, w = img.shape[:2]
    names = spec.get("names", ["P1", "P2"])
    health = spec.get("health", [1.0, 1.0])
    timer = str(spec.get("timer", "99"))
    rounds = spec.get("rounds", [0, 0])
    combo = spec.get("combo")
    if h < 600:
        u = _unit(img)
        y0, bh = int(h * 0.05), 8 * u
        for side in (0, 1):
            x0, x1 = (int(w * 0.05), int(w * 0.43)) if side == 0 else (int(w * 0.57), int(w * 0.95))
            img[y0 - u:y0 + bh + u, x0 - u:x1 + u] = (230, 230, 240)
            img[y0:y0 + bh, x0:x1] = (24, 8, 40)
            length = int((x1 - x0) * health[side])
            lost = int((x1 - x0) * 0.08)
            if side == 0:                                       # the left bar's health runs from the timer outwards
                img[y0:y0 + bh, max(x0, x1 - length - lost):x1 - length] = (200, 20, 20)
                img[y0:y0 + bh, x1 - length:x1] = (255, 208, 0)
                img[y0:y0 + 2 * u, x1 - length:x1] = (255, 244, 160)
            else:
                img[y0:y0 + bh, x0 + length:min(x1, x0 + length + lost)] = (200, 20, 20)
                img[y0:y0 + bh, x0:x0 + length] = (255, 208, 0)
                img[y0:y0 + 2 * u, x0:x0 + length] = (255, 244, 160)
            name = names[side].upper()
            nx = x0 if side == 0 else x1 - text_width(name, u)
            text(img, nx, y0 + bh + 4 * u, name, "#ffffff", scale=u)
            for k in range(2):                                  # rounds won, by the timer
                cx = (x1 - 6 * u - k * 9 * u) if side == 0 else (x0 + 6 * u + k * 9 * u)
                cy = y0 + bh + 8 * u
                colour = (255, 208, 0) if k < rounds[side] else (70, 60, 90)
                img[cy - 3 * u:cy + 3 * u, cx - 3 * u:cx + 3 * u] = colour
        ts = 2 * u                                              # the timer's digits
        text(img, (w - text_width(timer, ts)) // 2, y0 - 2 * u, timer, "#ffe040", "#400000", scale=ts, outline=True)
        if combo:
            text(img, int(w * 0.06), int(h * 0.36), combo, "#ffe040", "#a01010", scale=u + 1, outline=True)
        return img
    # An HD screen: drawn smooth on a float canvas.
    canvas = img.astype(np.float32) / 255
    y0, bh, slant = h * 0.05, h * 0.032, h * 0.018
    xx, _ = P.coords(w, h)
    for side in (0, 1):
        x0, x1 = (w * 0.04, w * 0.445) if side == 0 else (w * 0.555, w * 0.96)
        if side == 0:
            poly = [(x0 + slant, y0), (x1, y0), (x1 - slant, y0 + bh), (x0, y0 + bh)]
        else:
            poly = [(x0, y0), (x1 - slant, y0), (x1, y0 + bh), (x0 + slant, y0 + bh)]
        frame = P.mask(w, h, [[(px + (-1 if px < (x0 + x1) / 2 else 1) * h * 0.006, py + (-1 if py == y0 else 1) * h * 0.006)
                                for px, py in poly]])
        P.over(canvas, "#05060c", frame, 0.75)
        bar = P.mask(w, h, [poly])
        P.over(canvas, "#1a1430", bar)
        length = (x1 - x0) * health[side]
        lost = (x1 - x0) * 0.09
        if side == 0:
            keep = np.clip(xx - (x1 - length), 0, 1)
            gone = np.clip(xx - (x1 - length - lost), 0, 1) - keep
        else:
            keep = np.clip(x0 + length - xx, 0, 1)
            gone = np.clip(x0 + length + lost - xx, 0, 1) - keep
        P.over(canvas, "#ff4a3a", bar * gone)
        P.over(canvas, P.vertical(w, h, [(0, "#fff2a0"), (0.5, "#ffc21a"), (1, "#ff7a10")], top=y0, bottom=y0 + bh), bar * keep)
        P.over(canvas, "#ffffff", bar * np.clip((y0 + bh * 0.3 - P.coords(w, h)[1]) / 2 + 0.5, 0, 1), 0.3)
        P.over(canvas, "#ffffff", np.clip(P.dilate(bar, 1.5) - bar, 0, 1), 0.7)
        name = names[side].upper()
        nx, anchor = (x0 + slant, "la") if side == 0 else (x1 - slant, "ra")
        P.draw_text(canvas, name, "TCCEB.TTF", h * 0.042, (nx, y0 + bh + h * 0.012), "#ffffff", anchor=anchor,
                    shadow=("#000000", 2, 2))
        for k in range(2):                                      # rounds won: diamonds by the timer
            cx = (x1 - h * 0.03 - k * h * 0.036) if side == 0 else (x0 + h * 0.03 + k * h * 0.036)
            cy = y0 + bh + h * 0.03
            r = h * 0.012
            gem = P.mask(w, h, [[(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]])
            P.over(canvas, "#05060c", P.dilate(gem, 1.5))
            P.over(canvas, "#ffcc33" if k < rounds[side] else "#3a3450", gem)
    cx, cy, r = w / 2, y0 + bh * 0.6, h * 0.058
    hexagon = [(cx + r * np.cos(np.pi / 3 * k + np.pi / 6), cy + r * np.sin(np.pi / 3 * k + np.pi / 6)) for k in range(6)]
    P.over(canvas, "#05060c", P.mask(w, h, [hexagon]), 0.85)
    P.over(canvas, "#ffcc33", np.clip(P.dilate(P.mask(w, h, [hexagon]), 2) - P.mask(w, h, [hexagon]), 0, 1))
    P.draw_text(canvas, timer, "TCCEB.TTF", h * 0.07, (cx, cy), "#ffffff", anchor="mm")
    if combo:
        P.draw_text(canvas, combo, "FRAHVIT.TTF", h * 0.08, (w * 0.05, h * 0.3), "#ffd23a", anchor="la", stroke=4,
                    stroke_colour="#5a0a08", shadow=("#000000", 4, 4))
    for side in (0, 1):                                         # super meters, bottom corners
        x0 = w * 0.04 if side == 0 else w * 0.96 - w * 0.2
        y = h * 0.92
        for k in range(3):
            seg = P.mask(w, h, [[(x0 + k * w * 0.068 + h * 0.01, y), (x0 + (k + 1) * w * 0.068 - h * 0.004, y),
                                 (x0 + (k + 1) * w * 0.068 - h * 0.014, y + h * 0.02), (x0 + k * w * 0.068, y + h * 0.02)]])
            full = k < spec.get("meters", [2, 1])[side]
            P.over(canvas, "#05060c", P.dilate(seg, 1.5), 0.8)
            P.over(canvas, "#30e0ff" if full else "#1a2a3a", seg)
        label = f"LV {spec.get('meters', [2, 1])[side]}"
        lx, anchor = (x0, "lb") if side == 0 else (x0 + w * 0.2, "rb")
        P.draw_text(canvas, label, "TCCEB.TTF", h * 0.032, (lx, y - h * 0.006), "#9ff4ff", anchor=anchor, shadow=("#000000", 2, 2))
    img[:] = (np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8)
    return img


def _hearts(img, full, total):
    heart = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."]
    for n in range(total):
        for y, row in enumerate(heart):
            for x, c in enumerate(row):
                if c == "#":
                    img[7 + y, 8 + n * 10 + x] = (230, 40, 50) if n < full else (70, 50, 60)
        for y, row in enumerate(heart):                        # a dark rim
            for x, c in enumerate(row):
                if c == "." and any(0 <= y + dy < len(heart) and 0 <= x + dx < 7 and heart[y + dy][x + dx] == "#"
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    img[7 + y, 8 + n * 10 + x] = (20, 10, 14)


def hud(img, kind, game):
    h, w = img.shape[:2]
    if kind == "text":
        _items(img, game.get("hud_items", []))
    elif kind == "versus":
        _versus(img, game.get("versus", {}))
    elif kind == "hearts":
        _hearts(img, 3, 5)
        text(img, w - 8 - text_width("X028"), 7, "X028", "#80ff90", outline=True)
    elif kind == "dialogue":
        lines = wrap(game.get("dialogue", ""), w - 36)
        top = h - 12 - 14 * len(lines) - 8
        _window(img, 6, top, w - 6, h - 6)
        for k, line in enumerate(lines):
            text(img, 16, top + 10 + k * 14, line, "#ffffff", "#101030")
        cx, cy = w - 18, h - 14                                    # the "more" cursor
        for k in range(4):
            img[cy + k, cx - 3 + k:cx + 4 - k] = (255, 255, 255)
    elif kind == "racer":
        text(img, 8, 4, "SCORE", "#ffd040")
        text(img, 8, 13, "0012840", "#ffffff")
        text(img, w // 2 - text_width("TIME") // 2, 3, "TIME", "#ffd040")
        text(img, w // 2 - text_width("58", 2) // 2, 12, "58", "#ff8a20", "#200000", scale=2, outline=True)
        text(img, w - 8 - text_width("LAP 2/3"), 4, "LAP 2/3", "#ffffff")
        text(img, w - 8 - text_width("POS 3RD"), 13, "POS 3RD", "#40e0ff")
        for k in range(12):                                         # the rev counter
            colour = (64, 224, 96) if k < 7 else (255, 208, 64) if k < 10 else (255, 64, 48)
            x = w - 92 + k * 7
            img[h - 29 - k:h - 26, x:x + 5] = colour if k < 10 else (90, 40, 40)
        text(img, w - 8 - text_width("214 KM/H"), h - 18, "214 KM/H", "#ffffff")
    elif kind == "shooter":
        text(img, 8, 6, "1P 0024500", "#ffffff")
        text(img, w // 2 - text_width("HI 0050000") // 2 + 20, 6, "HI 0050000", "#ffd040")
        ship = ["..##......", ".#####....", "#########.", ".#####....", "..##......"]
        for n in range(3):
            for y, row in enumerate(ship):
                for x, c in enumerate(row):
                    if c == "#":
                        img[7 + y, w - 48 + n * 13 + x] = (220, 230, 255) if y != 2 else (80, 160, 255)
        text(img, 8, 16, "SPEED", "#40e0ff")
        for k in range(4):
            img[17:22, 46 + k * 6:50 + k * 6] = (64, 224, 255) if k < 3 else (40, 60, 90)
    elif kind == "puzzle":
        # Kaleidrop's square painting, padded out to the screen: its wells and next frames, where the padding put them.
        x0 = (w - h) // 2
        text(img, x0 + int(0.07 * h), int(0.04 * h), "1P 012340", "#ffffff", "#300840")
        text(img, x0 + int(0.6 * h), int(0.04 * h), "2P 008870", "#ffffff", "#300840")
        text(img, w // 2 - text_width("NEXT") // 2, int(0.16 * h), "NEXT", "#ffe040", "#300840", outline=True)
    elif kind == "flower":
        # Health: a flower of six petals, four still lit; lives; seeds.
        canvas = img.astype(np.float32) / 255
        cx, cy = 26, 24
        for k in range(6):
            a = -math.pi / 2 + k * math.pi / 3
            petal = P.disc(w, h, (cx + math.cos(a) * 9, cy + math.sin(a) * 9), 6.5)
            P.over(canvas, "#1a1a1a", P.dilate(petal, 1.2))
            P.over(canvas, "#ffd23a" if k < 4 else "#5a5a64", petal)
        P.over(canvas, "#1a1a1a", P.disc(w, h, (cx, cy), 7.5))
        P.over(canvas, "#ff8a2a", P.disc(w, h, (cx, cy), 6))
        seed_m = P.ellipse(w, h, (w - 78, 22), (6, 8.5))
        P.over(canvas, "#3a2a00", P.dilate(seed_m, 1.2))
        P.over(canvas, P.vertical(w, h, [(0, "#fff3a0"), (1, "#d08a10")], top=13, bottom=31), seed_m)
        head = P.disc(w, h, (52, 46), 6)
        P.over(canvas, "#0a2a10", P.dilate(head, 1.2))
        P.over(canvas, "#7ad83a", head)
        img[:] = (np.clip(canvas, 0, 1) * 255).astype(np.uint8)
        text(img, 62, 42, "X3", "#ffffff", "#103010", outline=True)
        text(img, w - 66, 15, "X047", "#ffffff", "#3a2a00", scale=2, outline=True)
    return img


def screenshot(game, painting, system, look):
    """A game's screenshot: its painting at the native resolution, in the console's palette, with its HUD."""
    focus = tuple(game.get("crop", {}).get("screen", (0.5, 0.5)))
    img = native(painting, system, look, game.get("screen_fit", "crop"), focus)
    hud(img, game.get("hud", "none"), game)
    return Image.fromarray(img)
