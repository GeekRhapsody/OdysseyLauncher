"""The made-up games' packaging for the PlayStation, the Dreamcast and the PSP: each system's cover, back, spine and
disc label, laid out as its PAL boxes were, with made-up marks in place of the real ones (a "32-BIT" word where a
PlayStation box has its logo, an emblem of the module's own where the console maker's goes). boxes.py has the other
systems, the shared helpers and every system's sizes (FORMATS); make_games.py picks this module for these three.

The designs follow the owner's PAL box scans:
- PlayStation: the art over a black foot with the platform word across it, and a black emblem square with a white PAL
  tag in the top left. The back is the art darkened, with a black strip down its right (the emblem, the small print, a
  disc mark, an orange notice and the barcode) and a white strip across its foot. The spine is black, the emblem at
  the top and the title in white capitals down it, the catalogue number at its foot.
- Dreamcast: a pale blue band across the top, the platform word in blue on its left and a blue emblem square on its
  right, the art under it. The back is the art darkened over a blue foot (the age badge, the publisher, an orange
  notice, the small print and the barcode). The spine is blue, the emblem at the top, the title in white capitals down
  it, the catalogue number at its foot.
- PSP: a thin black band across the top, the platform word in light grey on its left, the art under it. The back is
  the art darkened over a row of yellow icons and a white foot (the small print and the barcode). The spine is black at
  the top (the emblem, the platform word) and the foot (a pad), white between, the title in black down it.
- Labels: each a round disc, as boxes.disc draws the PS2's, with its own platform word and band."""

import zlib

import numpy as np

import boxes as B
import paint as P

WORDS = {"psx": "32-BIT", "dreamcast": "128-BIT", "psp": "PORTABLE"}
DC_BLUE = "#1a4fb0"
NOTICE = "#f08a1c"
SMALL = "A made-up game, drawn for Odyssey Launcher: it doesn't exist."


def _small_print(game):
    return f"© {game['released'][:4]} {game['publisher']}. Developed by {game['developer']}. {SMALL}"


def _emblem(size, colour="#ffffff", back="#050506", word=None):
    """The made-up emblem square: a disc mark on a plain square, the platform word under it when there's room."""
    lay = P.layer(size, size)
    P.paint(lay, back, np.ones((size, size), np.float32))
    mark = B.disc_mark(int(size * (0.5 if word else 0.66)), colour)
    B.put(lay, mark, size / 2, size * (0.38 if word else 0.5))
    if word:
        words = B.fit_layer(B.text_layer(word, "GOTHICB.TTF", size * 0.2, colour), size * 0.84, size * 0.2)
        B.put(lay, words, size / 2, size * 0.82)
    return lay


def _tag(width, text="PAL", colour="#ffffff", ink="#050506"):
    """A small tag with a word on it (the PlayStation's PAL tag)."""
    h = int(width * 0.32)
    lay = P.layer(width, h)
    P.paint(lay, colour, np.ones((h, width), np.float32))
    words = B.fit_layer(B.text_layer(text, "arialbd.ttf", h * 0.7, ink, tracking=0.1), width * 0.8, h * 0.7)
    B.put(lay, words, width / 2, h / 2)
    return lay


def _notice(w, h):
    """An orange notice box of small print, as the PAL backs' health warning is (made-up words)."""
    box = P.canvas(int(w), int(h), NOTICE)
    P.draw_text(box, "PLEASE NOTE", "ariblk.ttf", h * 0.16, (w / 2, h * 0.16), "#ffffff", anchor="mm")
    words = "Take a break of a few minutes every hour, and play in a well-lit room."
    lines = P.wrap(words, "arial.ttf", h * 0.1, w * 0.88)
    for k, line in enumerate(lines[:5]):
        P.draw_text(box, line, "arial.ttf", h * 0.1, (w / 2, h * 0.36 + k * h * 0.13), "#ffffff", anchor="mm")
    return box


def _corners(out, game, area, badge):
    """The age badge in the art's lower left corner and the publisher's mark in its lower right."""
    x0, _, x1, y1 = area
    B.put(out, B.age_badge(badge, game["age"]), x0 + badge * 0.35, y1 - badge * 0.35, "lb")
    mark = B.fit_layer(B.publisher_mark(game["publisher"], badge * 0.36), (x1 - x0) * 0.32, badge * 0.4)
    B.put(out, B.haloed(mark, badge * 0.12), x1 - badge * 0.2, y1 - badge * 0.2, "rb")


def _art_back(art, w, h):
    unit = min(w, h)
    return P.blur(B.crop(art, w, h, (0.5, 0.5)), unit * 0.012) * 0.4 + P.rgb("#05060c") * 0.6


def _title_down(out, game, top, bottom, colour, font="HATTEN.TTF"):
    """The title in capitals down a side spine, read top to bottom, between top and bottom."""
    h, w = out.shape[:2]
    title = B.text_layer(game["title"].upper(), font, w * 0.6, colour, tracking=0.04)
    length = bottom - top
    B.put(out, B.rotate90(B.fit_layer(title, length * 0.92, w * 0.66)), w / 2, top + length * 0.04, "mt")


# Fronts ------------------------------------------------------------------------------------------------------------

def cover(game, art, logo):
    system = game["system"]
    w, h = B.FORMATS[system]["cover"]
    out = P.canvas(w, h)
    focus = tuple(game.get("crop", {}).get("cover", (0.5, 0.5)))
    badge = int(min(w, h) * 0.07)
    if system == "psx":                                       # a black foot with the platform word, an emblem top left
        foot = int(h * 0.14)
        out[:h - foot] = B.crop(art, w, h - foot, focus)
        word = B.text_layer(WORDS[system], "ERASDEMI.TTF", foot * 0.62, "#ffffff", tracking=0.04)
        B.put(out, B.fit_layer(word, w * 0.6, foot * 0.62), w * 0.6, h - foot / 2)
        square = int(w * 0.1)
        B.put(out, _emblem(square), w * 0.025, h * 0.02, "lt")
        B.put(out, _tag(int(square * 0.8)), w * 0.025 + square / 2, h * 0.02 + square + square * 0.06, "mt")
        area = (w * 0.025 + square, 0, w, h - foot)
        corners = (0, 0, w, h - foot)
    elif system == "dreamcast":                               # a pale blue band across the top
        band = int(h * 0.13)
        out[band:] = B.crop(art, w, h - band, focus)
        out[:band] = B._vgrad(w, band, [(0, "#eef3fb"), (0.6, "#c8d6ee"), (1, "#a4bce4")])
        out[band - 6:band] = P.rgb(DC_BLUE)
        word = B.text_layer(WORDS[system], "ARLRDBD.TTF", band * 0.62, DC_BLUE, tracking=0.02)
        B.put(out, B.fit_layer(word, w * 0.62, band * 0.62), w * 0.035, band / 2, "lm")
        B.put(out, _emblem(int(band * 0.78), "#ffffff", DC_BLUE), w * 0.965, band / 2, "rm")
        area = corners = (0, band, w, h)
    else:                                                     # psp: a thin black band across the top
        band = int(h * 0.055)
        out[band:] = B.crop(art, w, h - band, focus)
        out[:band] = P.rgb("#050506")
        word = B.text_layer(WORDS[system], "GOTHIC.TTF", band * 0.5, "#c8c8cc", tracking=0.3)
        B.put(out, B.fit_layer(word, w * 0.5, band * 0.5), w * 0.04, band / 2, "lm")
        B.put(out, B.disc_mark(int(band * 0.6)), w * 0.96, band / 2, "rm")
        area = corners = (0, band, w, h)
    B._logo_on_art(out, logo, area, game.get("logo_place", "top"))
    _corners(out, game, corners, badge)
    return out


# Backs -------------------------------------------------------------------------------------------------------------

def back(game, art, logo, shot):
    """The back: the logo, the screenshot, the description and features (boxes.body), and each system's own strips."""
    system = game["system"]
    w, h = B.FORMATS[system]["back"]
    out = _art_back(art, w, h)
    margin = min(w, h) * 0.05
    shot_img = P.from_image(shot)
    if system == "psx":
        strip, white = int(w * 0.17), int(h * 0.04)
        B.body(out, game, logo, shot_img, (margin, 0, w - strip - margin, h - white - h * 0.12), margin)
        _psx_back(out, game, strip, white, margin)
    elif system == "dreamcast":
        foot = int(h * 0.17)
        B.body(out, game, logo, shot_img, (margin, 0, w - margin, h - foot - margin * 0.3), margin)
        _dreamcast_foot(out, game, foot, margin)
    else:
        white, icons = int(h * 0.12), int(h * 0.07)
        B.body(out, game, logo, shot_img, (margin, 0, w - margin, h - white - icons - margin * 0.3), margin)
        _psp_foot(out, game, white, icons, margin)
    return out


def _psx_back(out, game, strip, white, margin):
    """A PlayStation back's black strip down the right, its age badge and publisher, and the white strip at its foot."""
    h, w = out.shape[:2]
    x0 = w - strip
    out[:, x0:] = P.rgb("#050506")
    pad = strip * 0.1
    square = int(strip * 0.5)
    B.put(out, _emblem(square, "#ffffff", "#050506", WORDS["psx"]), x0 + strip / 2, pad, "mt")
    y = pad + square + pad
    size = strip * 0.045
    small = _small_print(game) + " For home use only on the made-up 32-BIT system."
    lines = P.wrap(small, B.BODY, size, strip - 2 * pad)
    for line in lines[:12]:
        P.draw_text(out, line, B.BODY, size, (x0 + pad, y), "#c8c8cc")
        y += size * 1.35
    B.put(out, B.disc_mark(int(strip * 0.34)), x0 + strip / 2, y + pad, "mt")
    y += pad + strip * 0.34 + pad * 0.5
    P.draw_text(out, "CD-ROM", "arialbd.ttf", strip * 0.08, (x0 + strip / 2, y), "#ffffff", anchor="mt")
    nh = int(strip * 0.62)
    ny = int(h - white - pad - strip * 0.45 - pad - nh)
    out[ny:ny + nh, int(x0 + pad):int(x0 + pad) + int(strip - 2 * pad)] = _notice(strip - 2 * pad, nh)
    bw, bh = int(strip - 2 * pad), int(strip * 0.45)
    by = int(h - white - pad - bh)
    out[by:by + bh, int(x0 + pad):int(x0 + pad) + bw] = B.barcode(bw, bh, zlib.crc32(game["id"].encode()))
    badge = int(h * 0.07)
    fy = h - white - h * 0.06
    B.put(out, B.age_badge(badge, game["age"]), margin, fy, "lm")
    mark = B.fit_layer(B.publisher_mark(game["publisher"], badge * 0.42), w * 0.3, badge * 0.42)
    B.put(out, mark, margin + badge * 1.35, fy, "lm")
    out[h - white:] = P.rgb("#f6f6f4")
    support = f"{B.players_text(game['players'])}  •  MEMORY CARD: 1 BLOCK  •  ANALOGUE CONTROL  •  PAL"
    P.draw_text(out, support, "arialbd.ttf", white * 0.42, (margin, h - white / 2), "#202024", anchor="lm")


def _dreamcast_foot(out, game, foot, margin):
    """A Dreamcast back's blue foot: the age badge, the publisher, an orange notice, the small print and the barcode."""
    h, w = out.shape[:2]
    top = h - foot
    out[top:] = B._vgrad(w, foot, [(0, "#3a66c8"), (1, "#1a3c94")])
    out[top:top + 5] = P.rgb("#a4bce4")
    badge = int(foot * 0.5)
    fy = top + foot * 0.42
    B.put(out, B.age_badge(badge, game["age"]), margin, fy, "lm")
    mark = B.fit_layer(B.publisher_mark(game["publisher"], badge * 0.42), w * 0.22, badge * 0.42)
    B.put(out, mark, margin + badge * 1.35, fy, "lm")
    nw, nh = int(foot * 1.5), int(foot * 0.66)
    nx = int(w * 0.52)
    out[int(fy - nh / 2):int(fy - nh / 2) + nh, nx:nx + nw] = _notice(nw, nh)
    bw, bh = int(foot * 1.4), int(foot * 0.6)
    bx, by = int(w - margin - bw), int(fy - bh / 2)
    out[by:by + bh, bx:bx + bw] = B.barcode(bw, bh, zlib.crc32(game["id"].encode()))
    P.draw_text(out, _small_print(game) + "  PAL", B.BODY, foot * 0.08, (w / 2, h - foot * 0.1), "#d8e2f4", anchor="mm")


def _psp_foot(out, game, white, icons, margin):
    """A PSP back's row of yellow icons over the art, the age badge and publisher beside them, and its white foot."""
    h, w = out.shape[:2]
    y0 = h - white - icons
    size = icons * 0.62
    x = margin
    for word in (B.players_text(game["players"]), "WIRELESS", "SAVE 320 KB"):
        tw = int(icons * 1.5)
        box = P.canvas(tw, int(size), "#ffcc1c")
        lines = P.wrap(word, "arialbd.ttf", size * 0.24, tw * 0.86)
        for k, line in enumerate(lines[:2]):
            P.draw_text(box, line, "arialbd.ttf", size * 0.24, (tw / 2, size * (0.34 + k * 0.32)), "#111111",
                        anchor="mm")
        out[int(y0 + (icons - size) / 2):int(y0 + (icons - size) / 2) + int(size), int(x):int(x) + tw] = box
        x += tw + icons * 0.12
    B.put(out, B.age_badge(int(size), game["age"]), w - margin, y0 + icons / 2, "rm")
    mark = B.fit_layer(B.publisher_mark(game["publisher"], size * 0.4), w * 0.3, size * 0.4)
    B.put(out, B.haloed(mark, size * 0.1), w - margin - size * 1.2, y0 + icons / 2, "rm")
    out[h - white:] = P.rgb("#f6f6f4")
    bw, bh = int(white * 1.5), int(white * 0.7)
    out[h - white + (white - bh) // 2:h - white + (white - bh) // 2 + bh, int(w - margin - bw):int(w - margin)] = \
        B.barcode(bw, bh, zlib.crc32(game["id"].encode()))
    B.put(out, B.disc_mark(int(white * 0.42), "#202024"), margin, h - white / 2, "lm")
    text_size = white * 0.1
    lines = P.wrap(_small_print(game) + " Only for the made-up PORTABLE system in PAL territories.", B.BODY, text_size,
                   w - 2 * margin - bw - white * 0.7)
    for k, line in enumerate(lines[:6]):
        y = h - white * 0.86 + k * text_size * 1.35
        P.draw_text(out, line, B.BODY, text_size, (margin + white * 0.6, y), "#3a3a40")


# Spines ------------------------------------------------------------------------------------------------------------

def spine(game, art, logo):
    """A side spine, read top to bottom: the emblem at the top, the title down it, the catalogue number at the foot."""
    system = game["system"]
    w, h = B.FORMATS[system]["spine"]
    out = P.canvas(w, h)
    number = B.catalogue(game)
    if system == "psx":
        out[:] = P.rgb("#050506")
        square = int(w * 0.84)
        B.put(out, _emblem(square, "#ffffff", "#050506", WORDS[system]), w / 2, w * 0.08, "mt")
        B.put(out, _tag(int(square * 0.8)), w / 2, w * 0.08 + square + w * 0.04, "mt")
        _title_down(out, game, h * 0.17, h * 0.86, "#ffffff")
        for k, part in enumerate(number.split(" ")):
            P.draw_text(out, part, "arialbd.ttf", w * 0.2, (w / 2, h - w * 0.5 + k * w * 0.24), "#ffffff", anchor="mm")
    elif system == "dreamcast":
        out[:] = B._hgrad(w, h, [(0, "#2c50b8"), (0.5, "#3a62c8"), (1, "#2c50b8")])
        B.put(out, B.disc_mark(int(w * 0.6)), w / 2, w * 0.12, "mt")
        word = B.text_layer(WORDS[system], "ARLRDBD.TTF", w * 0.2, "#ffffff")
        B.put(out, B.fit_layer(word, w * 0.84, w * 0.2), w / 2, w * 0.86, "mt")
        _title_down(out, game, h * 0.17, h * 0.92, "#ffffff")
        P.draw_text(out, number, "arial.ttf", w * 0.1, (w / 2, h - w * 0.2), "#e4ecf8", anchor="mm")
    else:                                                     # psp: black at the top and the foot, white between
        top, foot = int(h * 0.28), int(h * 0.08)
        out[:] = P.rgb("#f6f6f4")
        out[:top] = P.rgb("#050506")
        out[h - foot:] = P.rgb("#050506")
        B.put(out, B.disc_mark(int(w * 0.56)), w / 2, w * 0.14, "mt")
        word = B.rotate90(B.fit_layer(B.wordmark(w * 0.5, "#c8c8cc", WORDS[system]), top * 0.62, w * 0.5))
        B.put(out, word, w / 2, top - w * 0.2, "mb")
        _title_down(out, game, top, h - foot, "#0a0a0c", "AGENCYB.TTF")
        B.put(out, B._pad_pictogram(int(w * 0.6)), w / 2, h - foot * 0.62)
        P.draw_text(out, "DISC", "arialbd.ttf", w * 0.16, (w / 2, h - foot * 0.22), "#ffffff", anchor="mm")
    return out


# Labels ------------------------------------------------------------------------------------------------------------

def disc(game, art, logo):
    band = {"psx": "#050506", "dreamcast": DC_BLUE, "psp": "#050506"}[game["system"]]
    return B.disc(game, art, logo, WORDS[game["system"]], band)
