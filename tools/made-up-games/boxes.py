"""The made-up games' packaging: each system's cover, back, spine and cartridge label, laid out as its PAL boxes were,
with made-up marks in place of the real ones (a "16-BIT" plate where a Mega Drive box has its logo, a gold seal with no
words, the publisher's own mark where the console maker's goes). Sizes are twice ScreenScraper's scans, so the art fits
the box templates' faces exactly (godot/src/Tools/BoxTemplateGenerator.cs, tools/console-models/mega_drive_clamshell.py).

The designs follow the owner's PAL box scans:
- Mega Drive "classic": black bands across the top (a chrome plate in the middle) and the foot ("16-BIT CARTRIDGE" on
  the left, the publisher on the right). "sidebar": a blue band down the left with big vertical letters. The backs are
  black with a blue band down the right and a blue strip across the top.
- SNES: an L of black down the left and along the foot: a red tag at the top, a red italic wordmark over "PAL VERSION",
  the publisher, and a gold seal. The backs and top spines are black.
- N64: a black band down the right: a white badge with a cube, the accessories' icons, a gold seal and "PAL VERSION".
  The backs are colourful, with a white box of warnings."""

import math
import zlib

import numpy as np
from PIL import Image

import paint as P

# Per system: the front, back and spine sizes (the spine's long side runs along the box's height for a side spine,
# along its width for a top one) and the label's.
FORMATS = {
    "megadrive": dict(cover=(968, 1360), back=(962, 1360), spine=(162, 1360), label=(1036, 700)),
    "snes": dict(cover=(1360, 994), back=(1360, 994), spine=(1360, 194), label=(1120, 700)),
    "n64": dict(cover=(1360, 994), back=(1360, 994), spine=(1360, 194), label=(1085, 700)),
}

HEAD = "GOTHICB.TTF"     # Century Gothic Bold: the era's geometric sans, for headings
BODY = "GOTHIC.TTF"
MD_BLUE = [(0, "#3a72d8"), (0.5, "#1c4aa8"), (1, "#0e3484")]
RED = "#e0262a"


# Cutting and placing ----------------------------------------------------------------------------------------------

def crop(art, w, h, focus=(0.5, 0.5)):
    """The painting cut to w:h round focus (fractions of the spare width and height), then scaled to w x h."""
    aw, ah = art.size
    target = w / h
    cw, ch = (int(round(ah * target)), ah) if aw / ah > target else (aw, int(round(aw / target)))
    x = int((aw - cw) * focus[0])
    y = int((ah - ch) * focus[1])
    return P.from_image(art.crop((x, y, x + cw, y + ch)).resize((w, h), Image.LANCZOS))


def fit_layer(lay, max_w, max_h):
    """A layer shrunk to fit inside max_w x max_h, keeping its shape (never enlarged)."""
    h, w = lay.shape[:2]
    k = min(max_w / w, max_h / h, 1.0)
    return P.scale_layer(lay, max(1, int(w * k)), max(1, int(h * k)))


def put(dst, lay, cx, cy, anchor="mm"):
    """Composite a layer by an anchor: l/m/r across, t/m/b down."""
    h, w = lay.shape[:2]
    x = {"l": cx, "m": cx - w / 2, "r": cx - w}[anchor[0]]
    y = {"t": cy, "m": cy - h / 2, "b": cy - h}[anchor[1]]
    return P.composite(dst, lay, int(round(x)), int(round(y)))


def rotate90(lay, clockwise=True):
    return np.ascontiguousarray(np.rot90(lay, -1 if clockwise else 1))


def text_layer(text, font, size, colour, tracking=0.0, italic=0.0, stretch=1.0, outline=None):
    """Text as a trimmed layer, optionally outlined."""
    m, _ = P.text_mask(text, font, size, tracking=tracking, italic=italic, stretch=stretch, pad=int(size * 0.4))
    m, _ = P.tight(m, int(size * 0.08) + (int(outline[1]) if outline else 0))
    lay = P.layer(m.shape[1], m.shape[0])
    if outline:
        P.paint(lay, outline[0], P.dilate(m, outline[1]))
    P.paint(lay, colour, m)
    return lay


def _vgrad(w, h, stops):
    return P.vertical(w, h, stops)


def _hgrad(w, h, stops):
    return P.linear(w, h, (0, 0), (w, 0), stops)


# Made-up marks ----------------------------------------------------------------------------------------------------

def age_badge(size, age):
    """A made-up age rating: the age on a white rounded square in a black frame (no real board's design)."""
    lay = P.layer(size, size)
    r = size * 0.16
    outer = P.mask(size, size, P.path(f"M {r} 0 H {size - r} Q {size} 0 {size} {r} V {size - r} Q {size} {size} {size - r} "
                                      f"{size} H {r} Q 0 {size} 0 {size - r} V {r} Q 0 0 {r} 0 Z"))
    P.paint(lay, "#111111", outer)
    inner = P.erode(outer, size * 0.06)
    P.paint(lay, "#ffffff", inner)
    canvas = P.canvas(size, size)
    P.draw_text(canvas, f"{age}+", "ariblk.ttf", size * 0.46, (size / 2, size * 0.43), "#ffffff", anchor="mm")
    P.draw_text(canvas, "AGES", "arialbd.ttf", size * 0.15, (size / 2, size * 0.77), "#ffffff", anchor="mm")
    P.paint(lay, "#111111", canvas[..., 0] * inner)
    return lay


def chrome_plate(width, text="16-BIT"):
    """The Mega Drive band's plate, made up: a chrome stadium with the words in black."""
    h = int(width * 0.15)
    lay = P.layer(width, h)
    pill = np.maximum(P.disc(width, h, (h / 2, h / 2), h / 2), P.disc(width, h, (width - h / 2, h / 2), h / 2))
    pill[:, int(h / 2):int(width - h / 2)] = 1.0
    pill = pill * P.mask(width, h, [[(0, 0), (width, 0), (width, h), (0, h)]])
    P.paint(lay, "#202024", pill)
    inner = P.erode(pill, h * 0.08)
    P.paint(lay, _vgrad(width, h, [(0, "#ffffff"), (0.45, "#c8ccd4"), (0.55, "#7a808c"), (1, "#e8eaee")]), inner)
    words = text_layer(text, "ERASBD.TTF", h * 0.62, "#0a0a0c", tracking=0.18, stretch=1.35)
    words = fit_layer(words, width * 0.8, h * 0.7)
    put(lay, words, width / 2, h / 2)
    return lay


def seal(size):
    """A round gold seal with a star and rings, and no words."""
    lay = P.layer(size, size)
    c = (size / 2, size / 2)
    outer = P.disc(size, size, c, size * 0.48)
    P.paint(lay, "#3a2604", outer)
    P.paint(lay, _vgrad(size, size, [(0, "#fff0b0"), (0.5, "#d8a030"), (1, "#8a5a10")]), P.disc(size, size, c, size * 0.45))
    for r in (0.38, 0.33):
        ring = np.clip(P.disc(size, size, c, size * r) - P.disc(size, size, c, size * (r - 0.012)), 0, 1)
        P.paint(lay, "#6a4408", ring)
    P.paint(lay, "#fff6d0", P.mask(size, size, P.star4(c[0], c[1], size * 0.22, size * 0.07)))
    ticks = []
    for k in range(24):
        a = k / 24 * 2 * math.pi
        ticks.append([(c[0] + math.cos(a) * size * 0.4, c[1] + math.sin(a) * size * 0.4),
                      (c[0] + math.cos(a + 0.06) * size * 0.44, c[1] + math.sin(a + 0.06) * size * 0.44),
                      (c[0] + math.cos(a + 0.12) * size * 0.4, c[1] + math.sin(a + 0.12) * size * 0.4)])
    P.paint(lay, "#6a4408", P.mask(size, size, ticks))
    return lay


def cube_badge(size):
    """The N64 band's badge, made up: a white rounded square with a grey cube and a red "64"."""
    lay = P.layer(size, size)
    r = size * 0.12
    sq = P.mask(size, size, P.path(f"M {r} 0 H {size - r} Q {size} 0 {size} {r} V {size - r} Q {size} {size} {size - r} "
                                   f"{size} H {r} Q 0 {size} 0 {size - r} V {r} Q 0 0 {r} 0 Z"))
    P.paint(lay, "#f4f4f4", sq)
    cx, cy, s = size / 2, size * 0.4, size * 0.24
    top = [(cx, cy - s), (cx + s * 0.87, cy - s * 0.5), (cx, cy), (cx - s * 0.87, cy - s * 0.5)]
    left = [(cx - s * 0.87, cy - s * 0.5), (cx, cy), (cx, cy + s), (cx - s * 0.87, cy + s * 0.5)]
    right = [(cx, cy), (cx + s * 0.87, cy - s * 0.5), (cx + s * 0.87, cy + s * 0.5), (cx, cy + s)]
    for poly, colour in ((top, "#d0d4dc"), (left, "#8a909c"), (right, "#5a606c")):
        P.paint(lay, colour, P.mask(size, size, [poly]))
    words = fit_layer(text_layer("64", "FRAHVIT.TTF", size * 0.3, RED, italic=0.08), size * 0.6, size * 0.24)
    put(lay, words, size / 2, size * 0.83)
    return lay


def icons(width):
    """The N64 band's accessory icons, made up: a pad, a pak and the number of players."""
    h = int(width * 0.36)
    out = []
    pad = P.layer(width, h)
    body = P.mask(width, h, P.path(f"M {width * 0.2} {h * 0.3} H {width * 0.8} Q {width * 0.95} {h * 0.3} {width * 0.9} {h * 0.75} "
                                   f"Q {width * 0.82} {h * 0.95} {width * 0.68} {h * 0.62} H {width * 0.32} Q {width * 0.18} "
                                   f"{h * 0.95} {width * 0.1} {h * 0.75} Q {width * 0.05} {h * 0.3} {width * 0.2} {h * 0.3} Z"))
    P.paint(pad, "#9aa0aa", body)
    out.append(pad)
    pak = P.layer(width, h)
    P.paint(pak, "#9aa0aa", P.mask(width, h, [[(width * 0.3, h * 0.15), (width * 0.7, h * 0.15), (width * 0.7, h * 0.85),
                                                (width * 0.3, h * 0.85)]]))
    for k in range(3):
        y = h * (0.3 + k * 0.17)
        P.paint(pak, "#2a2c30", P.mask(width, h, [[(width * 0.36, y), (width * 0.64, y), (width * 0.64, y + h * 0.06),
                                                   (width * 0.36, y + h * 0.06)]]))
    out.append(pak)
    return out


def publisher_mark(name, height, colour="#ffffff"):
    """A made-up publisher's mark: a small emblem drawn from primitives and its name."""
    h = int(height)
    e = h
    fonts = {"Moonquill": "PERTIBD.TTF", "Arcwave": "ERASBD.TTF", "Velvet Comet": "COOPBL.TTF", "Quayside": "BRITANIC.TTF",
             "Brightmoor": "GOTHICB.TTF", "Zephyrix": "AGENCYB.TTF"}
    word = name if name == "Velvet Comet" else name.upper()
    wm, _ = P.text_mask(word, fonts.get(name, HEAD), h * 0.62, tracking=0.06, pad=int(h * 0.2))
    wm, _ = P.tight(wm, 1)
    ww = wm.shape[1]
    W = e + int(h * 0.25) + ww
    lay = P.layer(W, h)
    em = np.zeros((h, W), np.float32)
    c = e / 2
    if name == "Moonquill":
        em = np.clip(P.disc(W, h, (c, c), e * 0.46) - P.disc(W, h, (c + e * 0.2, c - e * 0.1), e * 0.4), 0, 1)
        em = np.maximum(em, P.mask(W, h, P.path(f"M {e * 0.62} {e * 0.92} C {e * 0.66} {e * 0.6} {e * 0.82} {e * 0.3} "
                                                f"{e * 0.98} {e * 0.08} C {e * 0.86} {e * 0.4} {e * 0.76} {e * 0.66} "
                                                f"{e * 0.66} {e * 0.92} Z")))
    elif name == "Arcwave":
        ring = np.clip(P.disc(W, h, (c, c), e * 0.48) - P.disc(W, h, (c, c), e * 0.38), 0, 1)
        wave = P.mask(W, h, P.path(f"M {e * 0.14} {e * 0.6} C {e * 0.32} {e * 0.36} {e * 0.5} {e * 0.84} {e * 0.86} {e * 0.5} "
                                   f"L {e * 0.86} {e * 0.64} C {e * 0.5} {e * 0.98} {e * 0.32} {e * 0.5} {e * 0.14} {e * 0.74} Z"))
        em = np.maximum(ring, wave)
    elif name == "Velvet Comet":
        em = np.maximum(P.disc(W, h, (e * 0.68, e * 0.34), e * 0.2),
                        P.mask(W, h, [[(e * 0.56, e * 0.24), (e * 0.02, e * 0.98), (e * 0.78, e * 0.46)]]))
    elif name == "Quayside":                          # a sail over a hull
        em = P.mask(W, h, [[(e * 0.5, e * 0.04), (e * 0.5, e * 0.7), (e * 0.1, e * 0.7)],
                           [(e * 0.56, e * 0.2), (e * 0.9, e * 0.7), (e * 0.56, e * 0.7)],
                           [(e * 0.04, e * 0.76), (e * 0.96, e * 0.76), (e * 0.8, e * 0.96), (e * 0.2, e * 0.96)]])
    elif name == "Brightmoor":                        # a sun rising over a hill
        em = np.clip(P.disc(W, h, (c, e * 0.62), e * 0.3) - P.mask(W, h, [[(0, e * 0.62), (e, e * 0.62), (e, e), (0, e)]]), 0, 1)
        rays = [[(c, e * 0.62), (c + math.cos(a) * e * 0.48 - math.sin(a) * e * 0.03, e * 0.62 - math.sin(a) * e * 0.48 - math.cos(a) * e * 0.03),
                 (c + math.cos(a) * e * 0.48 + math.sin(a) * e * 0.03, e * 0.62 - math.sin(a) * e * 0.48 + math.cos(a) * e * 0.03)]
                for a in [math.pi * k / 6 for k in range(1, 6)]]
        em = np.maximum(em, P.mask(W, h, rays) * (1 - P.disc(W, h, (c, e * 0.62), e * 0.36)))
        em = np.maximum(em, P.mask(W, h, [[(0, e * 0.72), (e, e * 0.72), (e, e * 0.82), (0, e * 0.82)]]))
    else:                                             # Zephyrix: a split diamond
        em = P.mask(W, h, [[(c, e * 0.04), (e * 0.94, c), (c, c)], [(c, e * 0.96), (e * 0.06, c), (c, c)],
                           [(e * 0.06, c - e * 0.04), (c - e * 0.06, e * 0.1), (c - e * 0.06, c - e * 0.04)],
                           [(e * 0.94, c + e * 0.04), (c + e * 0.06, e * 0.9), (c + e * 0.06, c + e * 0.04)]])
    P.paint(lay, colour, em)
    word_m = np.zeros((h, W), np.float32)
    y0 = (h - wm.shape[0]) // 2
    word_m[max(y0, 0):max(y0, 0) + min(wm.shape[0], h), e + int(h * 0.25):e + int(h * 0.25) + ww] = wm[:h]
    P.paint(lay, colour, word_m)
    return lay


def barcode(w, h, seed):
    """A barcode-like block: random bars and digits on white. Not a real code: its digits don't check out."""
    rng = np.random.default_rng(seed)
    canvas = P.canvas(w, h, "#ffffff")
    x = w * 0.08
    while x < w * 0.92:
        bw = rng.choice([1, 1, 2, 3]) * w / 190
        if rng.random() < 0.55:
            canvas[int(h * 0.06):int(h * 0.78), int(x):int(x + bw)] = 0.05
        x += bw + rng.choice([1, 2]) * w / 190
    digits = "5 0" + "".join(str(d) for d in rng.integers(0, 10, 4)) + " " + "".join(str(d) for d in rng.integers(0, 10, 6))
    P.draw_text(canvas, digits, "OCRAEXT.TTF", h * 0.16, (w / 2, h * 0.9), "#111111", anchor="mm")
    return canvas


def players_text(players):
    return f"{players} PLAYER" + ("" if players == "1" else "S")


# Fronts ------------------------------------------------------------------------------------------------------------

def _logo_on_art(dst, logo, area, place="top"):
    """The logo over the art, along its top or bottom, as large as fits."""
    x0, y0, x1, y1 = area
    w, h = x1 - x0, y1 - y0
    lay = fit_layer(logo, w * 0.86, h * (0.3 if w < h else 0.36))
    if place == "bottom":
        return put(dst, lay, (x0 + x1) / 2, y1 - h * 0.05, "mb")
    return put(dst, lay, (x0 + x1) / 2, y0 + h * 0.035, "mt")


def cover(game, art, logo):
    system = game["system"]
    w, h = FORMATS[system]["cover"]
    out = P.canvas(w, h)
    focus = tuple(game.get("crop", {}).get("cover", (0.5, 0.5)))
    badge = int(min(w, h) * 0.07)
    if system == "megadrive" and game.get("dress", "classic") == "sidebar":
        band = int(w * 0.15)
        out[:, band:] = crop(art, w - band, h, focus)
        out[:, :band] = _hgrad(band, h, [(0, "#14408e"), (0.6, "#2a62c8"), (1, "#1c4aa8")])
        out[:, band - 4:band] = P.rgb("#9ac0ff")
        words = rotate90(text_layer("SIXTEEN BIT", "ERASBD.TTF", band * 0.6, "#ffffff", tracking=0.08, stretch=1.1), False)
        put(out, fit_layer(words, band * 0.7, h * 0.72), band / 2, h * 0.42)
        put(out, fit_layer(publisher_mark(game["publisher"], band * 0.3), band * 0.84, band * 0.3), band / 2, h - band * 0.45)
        area = (band, 0, w, h)
    elif system == "megadrive":
        top, foot = int(h * 0.085), int(h * 0.085)
        out[top:h - foot] = crop(art, w, h - top - foot, focus)
        put(out, chrome_plate(int(w * 0.5)), w / 2, top / 2)
        put(out, text_layer("16-BIT CARTRIDGE", "ariblk.ttf", foot * 0.3, "#ffffff"), w * 0.04, h - foot * 0.6, "lm")
        put(out, text_layer("FOR USE WITH 16-BIT VIDEO GAME SYSTEMS", "arial.ttf", foot * 0.1, "#c8c8c8"), w * 0.04,
            h - foot * 0.28, "lm")
        put(out, fit_layer(publisher_mark(game["publisher"], foot * 0.32), w * 0.3, foot * 0.32), w * 0.96, h - foot / 2, "rm")
        area = (0, top, w, h - foot)
    elif system == "snes":
        left, foot = int(w * 0.16), int(h * 0.19)
        out[:h - foot, left:] = crop(art, w - left, h - foot, focus)
        tag = P.layer(int(left * 0.7), int(h * 0.055))
        th, tw = tag.shape[:2]
        P.paint(tag, RED, P.mask(tw, th, P.path(f"M {th / 2} 0 H {tw - th / 2} Q {tw} 0 {tw} {th / 2} Q {tw} {th} {tw - th / 2} "
                                                f"{th} H {th / 2} Q 0 {th} 0 {th / 2} Q 0 0 {th / 2} 0 Z")))
        put(tag, fit_layer(text_layer("16-BIT", "arialbd.ttf", th * 0.6, "#ffffff"), tw * 0.8, th * 0.7), tw / 2, th / 2)
        put(out, tag, left * 0.12, h * 0.03, "lt")
        put(out, _pad_pictogram(int(left * 0.62)), left / 2, (h - foot) * 0.5)
        put(out, age_badge(badge, game["age"]), left / 2, h - foot - badge * 0.3, "mb")
        put(out, text_layer("16-BIT", "FRAHVIT.TTF", foot * 0.42, RED, italic=0.12, outline=("#5a0608", 3)), w * 0.03,
            h - foot * 0.6, "lm")
        put(out, text_layer("PAL VERSION", "arialbd.ttf", foot * 0.1, "#ffffff", tracking=0.1), w * 0.035, h - foot * 0.2, "lm")
        put(out, fit_layer(publisher_mark(game["publisher"], foot * 0.26), w * 0.32, foot * 0.3), w * 0.56, h - foot / 2)
        put(out, seal(int(foot * 0.72)), w - foot * 0.55, h - foot / 2)
        area = (left, 0, w, h - foot)
    else:                                                      # n64: a black band down the right
        band = int(w * 0.14)
        out[:, :w - band] = crop(art, w - band, h, focus)
        bx = w - band / 2
        put(out, cube_badge(int(band * 0.74)), bx, h * 0.025, "mt")
        y = h * 0.025 + band * 0.74 + h * 0.05
        for icon in icons(int(band * 0.6)):
            put(out, icon, bx, y, "mt")
            y += icon.shape[0] + h * 0.02
        put(out, text_layer("1-4", "arialbd.ttf", band * 0.14, "#9aa0aa"), bx, y + h * 0.01, "mt")
        put(out, seal(int(band * 0.56)), bx, h * 0.8)
        put(out, text_layer("PAL VERSION", "arialbd.ttf", band * 0.085, "#ffffff", tracking=0.08), bx, h * 0.955)
        area = (0, 0, w - band, h)
    _logo_on_art(out, logo, area, game.get("logo_place", "top"))
    if system in ("megadrive", "n64"):
        x0, y0, x1, y1 = area
        put(out, age_badge(badge, game["age"]), x0 + badge * 0.35, y1 - badge * 0.35, "lb")
    return out


def _pad_pictogram(width):
    """The SNES band's emblem, made up: a game pad drawn in greys."""
    h = int(width * 0.46)
    lay = P.layer(width, h)
    r = h / 2
    body = np.maximum(P.disc(width, h, (r, r), r), P.disc(width, h, (width - r, r), r))
    body[:, int(r):int(width - r)] = np.maximum(body[:, int(r):int(width - r)], 1.0)
    P.paint(lay, "#b8bcc4", body)
    cx, cy, s = r, r, r * 0.55
    P.paint(lay, "#3a3c42", P.mask(width, h, [[(cx - s, cy - s * 0.3), (cx + s, cy - s * 0.3), (cx + s, cy + s * 0.3),
                                                (cx - s, cy + s * 0.3)], [(cx - s * 0.3, cy - s), (cx + s * 0.3, cy - s),
                                                                          (cx + s * 0.3, cy + s), (cx - s * 0.3, cy + s)]]))
    for dx, dy in ((0.0, -0.4), (0.4, 0.0), (-0.4, 0.0), (0.0, 0.4)):
        P.paint(lay, "#6a6e78", P.disc(width, h, (width - r + dx * r, r + dy * r), r * 0.2))
    return lay


# Backs -------------------------------------------------------------------------------------------------------------

def _text_block(dst, lines, font, size, x, y, colour, leading=1.3, shadow=True):
    for k, line in enumerate(lines):
        P.draw_text(dst, line, font, size, (x, y + k * size * leading), colour, anchor="la",
                    shadow=("#000000", size * 0.06, size * 0.06) if shadow else None)
    return y + len(lines) * size * leading


def _framed(dst, img, x, y, w, border, colour="#ffffff"):
    """A picture scaled to width w with a border round it; returns its bottom."""
    ih, iw = img.shape[:2]
    h = int(w * ih / iw)
    pic = P.resize(img, int(w), h, Image.LANCZOS)
    dst[int(y) - border:int(y) + h + border, int(x) - border:int(x) + int(w) + border] = P.rgb(colour)
    dst[int(y):int(y) + h, int(x):int(x) + int(w)] = pic
    return y + h + border


def _copy_lines(game, size, width):
    """The description's and the features' lines at a font size, and their heights."""
    desc = P.wrap(game["description"], BODY, size, width)
    feats = [P.wrap(f, HEAD, size, width - size * 1.3) for f in game["features"]]
    return desc, feats, len(desc) * size * 1.3, sum(len(f) for f in feats) * size * 1.25


def _fit_size(game, size, width, height, parts=("desc", "feats")):
    """The largest font size, up to size, at which the chosen parts of the copy fit in height."""
    while size > 9:
        desc, feats, dh, fh = _copy_lines(game, size, width)
        total = (dh if "desc" in parts else 0) + (fh + (size * 0.8 if "desc" in parts else 0) if "feats" in parts else 0)
        if total <= height:
            break
        size *= 0.95
    return size


def _features(dst, feats, size, x, y, colour="#f2f2f4"):
    for lines in feats:
        P.draw_text(dst, "▶", "seguisym.ttf", size * 0.8, (x, y + size * 0.12), "#ffcc33", anchor="la")
        y = _text_block(dst, lines, HEAD, size, x + size * 1.3, y, colour, leading=1.25)
    return y


def back(game, art, logo, shot):
    """The back: the logo, the screenshot, the description and features, and along the foot the age badge, the
    publisher's mark, a barcode and the small print (which says the game is made up)."""
    system = game["system"]
    w, h = FORMATS[system]["back"]
    out = P.canvas(w, h)
    shot_img = P.from_image(shot)
    unit = min(w, h)
    margin = unit * 0.05
    year = game["released"][:4]
    if system == "megadrive":
        band, strip = int(w * 0.12), int(h * 0.045)
        out[:] = P.rgb("#050506")
        out[:, w - band:] = _hgrad(band, h, [(0, "#1c4aa8"), (0.4, "#2a62c8"), (1, "#14408e")])
        out[:, w - band:w - band + 4] = P.rgb("#9ac0ff")
        out[:strip] = _vgrad(w, strip, MD_BLUE)
        words = rotate90(text_layer("SIXTEEN BIT", "ERASBD.TTF", band * 0.6, "#ffffff", tracking=0.08, stretch=1.1), False)
        put(out, fit_layer(words, band * 0.7, h * 0.7), w - band / 2, h * 0.55)
        box = text_layer(players_text(game["players"]), "arialbd.ttf", strip * 0.42, "#ffffff", tracking=0.06)
        bh, bw = box.shape[:2]
        frame = P.layer(bw + int(strip * 0.4), int(strip * 0.72))
        fh, fw = frame.shape[:2]
        P.paint(frame, "#ffffff", np.clip(P.mask(fw, fh, [[(0, 0), (fw, 0), (fw, fh), (0, fh)]]) -
                                          P.mask(fw, fh, [[(2, 2), (fw - 2, 2), (fw - 2, fh - 2), (2, fh - 2)]]), 0, 1))
        put(frame, box, fw / 2, fh / 2)
        put(out, frame, margin, strip / 2, "lm")
        put(out, fit_layer(publisher_mark(game["publisher"], strip * 0.5), w * 0.3, strip * 0.5), w - band - margin, strip / 2, "rm")
        x0, x1, top, bottom = margin, w - band - margin, strip, h
    elif system == "snes":
        out[:] = P.rgb("#030303")
        x0, x1, top, bottom = margin, w - margin, 0, h
    else:
        bg = crop(art, w, h, (0.5, 0.5))
        out[:] = P.blur(bg, unit * 0.012) * 0.5 + P.rgb("#0a0a14") * 0.5
        x0, x1, top, bottom = margin, w - margin, 0, h
    foot = int(h * 0.12)
    body_bottom = bottom - foot - margin * 0.3
    if w < h:
        lay = fit_layer(logo, (x1 - x0) * 0.8, h * 0.1)
        put(out, lay, (x0 + x1) / 2, top + margin * 0.6, "mt")
        y = top + margin * 0.6 + lay.shape[0] + margin * 0.5
        shot_w = (x1 - x0) * 0.82
        y = _framed(out, shot_img, (x0 + x1 - shot_w) / 2, y, shot_w, 4) + margin * 0.55
        width = x1 - x0
        size = _fit_size(game, unit * 0.03, width, body_bottom - y)
        desc, feats, _, _ = _copy_lines(game, size, width)
        y = _text_block(out, desc, BODY, size, x0, y, "#f2f2f4") + size * 0.8
        _features(out, feats, size, x0, y)
    else:
        if system == "n64":
            # The warnings box, top left, as the PAL N64 backs have, then the logo under it.
            iw, ih = int(w * 0.3), int(h * 0.13)
            box = P.canvas(iw, ih, "#ffffff")
            P.draw_text(box, "IMPORTANT", "ariblk.ttf", ih * 0.15, (iw * 0.04, ih * 0.08), "#000000")
            lines = P.wrap("Please read the instruction booklet before you play, and keep it for reference. This game "
                           "pak is made up and holds no game.", "arial.ttf", ih * 0.11, iw * 0.92)
            for k, line in enumerate(lines):
                P.draw_text(box, line, "arial.ttf", ih * 0.11, (iw * 0.04, ih * 0.32 + k * ih * 0.14), "#202020")
            out[int(margin * 0.6):int(margin * 0.6) + ih, int(x0):int(x0) + iw] = box
            y = margin * 0.6 + ih + margin * 0.35
            lay = fit_layer(logo, w * 0.4, h * 0.16)
            put(out, lay, x0 + w * 0.2, y, "mt")
            y += lay.shape[0] + margin * 0.35
        else:
            lay = fit_layer(logo, w * 0.4, h * 0.19)
            put(out, lay, x0 + w * 0.2, top + margin * 0.7, "mt")
            y = top + margin * 0.7 + lay.shape[0] + margin * 0.45
        col_w = w * 0.42
        size = _fit_size(game, unit * 0.031, col_w, body_bottom - y, parts=("desc",))
        desc, _, _, _ = _copy_lines(game, size, col_w)
        _text_block(out, desc, BODY, size, x0, y, "#f2f2f4")
        shot_w = w * 0.46
        sx = x1 - shot_w
        sy = _framed(out, shot_img, sx, top + margin * 0.8, shot_w, 4) + margin * 0.45
        fsize = _fit_size(game, size, shot_w, body_bottom - sy, parts=("feats",))
        _, feats, _, _ = _copy_lines(game, fsize, shot_w)
        _features(out, feats, fsize, sx, sy)
    # Along the foot: the age badge, the publisher's mark, a barcode, a seal (Nintendo's systems) and the small print.
    badge = int(foot * 0.5)
    fy = bottom - foot * 0.58
    put(out, age_badge(badge, game["age"]), x0, fy, "lm")
    put(out, fit_layer(publisher_mark(game["publisher"], badge * 0.42), w * 0.3, badge * 0.42), x0 + badge * 1.35, fy, "lm")
    bw, bh = int(foot * 1.4), int(foot * 0.6)
    bx, by = int(x1 - bw), int(fy - bh / 2)
    out[by:by + bh, bx:bx + bw] = barcode(bw, bh, zlib.crc32(game["id"].encode()))
    if system != "megadrive":
        put(out, seal(int(foot * 0.55)), bx - foot * 0.45, fy)
    small = (f"© {year} {game['publisher']}. Developed by {game['developer']}. "
             f"A made-up game, drawn for Odyssey Launcher: it doesn't exist.")
    if system != "megadrive":
        small += "  PAL VERSION"
    P.draw_text(out, small, BODY, unit * 0.0135, ((x0 + x1) / 2, bottom - foot * 0.12), "#9a9aa4", anchor="mm")
    return out


# Spines ------------------------------------------------------------------------------------------------------------

def spine(game, art, logo):
    system = game["system"]
    w, h = FORMATS[system]["spine"]
    out = P.canvas(w, h)
    if system == "megadrive":                                 # a side spine, read top to bottom
        sidebar = game.get("dress", "classic") == "sidebar"
        if sidebar:
            out[:] = _hgrad(w, h, [(0, "#14408e"), (0.5, "#2a62c8"), (1, "#14408e")])
            put(out, rotate90(fit_layer(text_layer("SIXTEEN BIT", "ERASBD.TTF", w * 0.5, "#ffffff", tracking=0.08,
                                                   stretch=1.1), h * 0.2, w * 0.5)), w / 2, h - w * 0.25, "mb")
        else:
            out[:] = P.rgb("#050506")
            put(out, rotate90(chrome_plate(int(h * 0.22))), w / 2, h - w * 0.2, "mb")
        put(out, rotate90(fit_layer(publisher_mark(game["publisher"], w * 0.32), h * 0.16, w * 0.4)), w / 2, w * 0.2, "mt")
        lay = rotate90(fit_layer(logo, h * 0.5, w * 0.84))
        put(out, lay, w / 2, h * 0.46)
        return out
    # A top spine: left to right, the front at the image's foot.
    if system == "snes":
        out[:] = P.rgb("#040404")
        put(out, fit_layer(publisher_mark(game["publisher"], h * 0.3), w * 0.16, h * 0.32), w * 0.02, h / 2, "lm")
        put(out, fit_layer(text_layer("16-BIT", "FRAHVIT.TTF", h * 0.42, RED, italic=0.12, outline=("#5a0608", 2)),
                           w * 0.12, h * 0.5), w * 0.98, h / 2, "rm")
    else:
        out[:] = P.rgb("#040404")
        out[h - int(h * 0.05):] = P.rgb(RED)
        put(out, fit_layer(publisher_mark(game["publisher"], h * 0.3), w * 0.16, h * 0.32), w * 0.02, h / 2, "lm")
        put(out, cube_badge(int(h * 0.78)), w * 0.985, h / 2, "rm")
    lay = fit_layer(logo, w * 0.6, h * 0.84)
    put(out, lay, w / 2, h / 2)
    return out


# Labels ------------------------------------------------------------------------------------------------------------

def label(game, art, logo):
    system = game["system"]
    w, h = FORMATS[system]["label"]
    out = P.canvas(w, h)
    focus = tuple(game.get("crop", {}).get("label", (0.5, 0.5)))
    if system == "megadrive":
        band = int(h * 0.15)
        out[band:] = crop(art, w, h - band, focus)
        put(out, chrome_plate(int(w * 0.46)), w / 2, band / 2)
        area = (0, band, w, h)
    elif system == "snes":
        foot = int(h * 0.17)
        out[:h - foot] = crop(art, w, h - foot, focus)
        put(out, text_layer("16-BIT", "FRAHVIT.TTF", foot * 0.5, RED, italic=0.12, outline=("#5a0608", 2)), w * 0.04,
            h - foot * 0.55, "lm")
        put(out, text_layer("PAL VERSION", "arialbd.ttf", foot * 0.16, "#ffffff", tracking=0.1), w * 0.96, h - foot / 2, "rm")
        area = (0, 0, w, h - foot)
    else:
        foot = int(h * 0.16)
        out[:h - foot] = crop(art, w, h - foot, focus)
        out[h - foot:h - foot + int(h * 0.012)] = P.rgb(RED)
        put(out, cube_badge(int(foot * 0.8)), w * 0.03, h - foot / 2, "lm")
        put(out, text_layer("PAL VERSION", "arialbd.ttf", foot * 0.16, "#ffffff", tracking=0.1), w * 0.96, h - foot / 2, "rm")
        area = (0, 0, w, h - foot)
    x0, y0, x1, y1 = area
    lay = fit_layer(logo, (x1 - x0) * 0.8, (y1 - y0) * 0.42)
    put(out, lay, (x0 + x1) / 2, y0 + (y1 - y0) * 0.06, "mt")
    return out
