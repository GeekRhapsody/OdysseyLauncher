"""The made-up games' logos: transparent wordmarks in the styles of their eras' boxes, drawn from installed fonts and
primitives. Each is built as premultiplied RGBA layers (paint.py) at a large size, then trimmed. A logo is a dict from
games.toml: its style, title, optional subtitle and badge ("64", "'94"), and the style's options."""

import math

import numpy as np

import paint as P

S = 300           # the main word's font size in pixels


# Building blocks ---------------------------------------------------------------------------------------------------

def _span(m):
    """The rows the mask's ink spans."""
    ys = np.nonzero(m.max(axis=1) > 0.05)[0]
    return (int(ys.min()), int(ys.max()) + 1) if len(ys) else (0, m.shape[0])


def _cols(m):
    xs = np.nonzero(m.max(axis=0) > 0.05)[0]
    return (int(xs.min()), int(xs.max()) + 1) if len(xs) else (0, m.shape[1])


def _fill(m, stops, span=None):
    """A vertical gradient over the mask's own height (or span)."""
    h, w = m.shape
    t0, t1 = span or _span(m)
    return P.vertical(w, h, stops, top=t0, bottom=t1)


def _bevel(m, r, light=(-0.55, -0.83)):
    """A raised face's shading: highlight and shadow masks from the mask's edges, lit from light (towards it)."""
    gy, gx = np.gradient(P.blur(m, r))
    s = -(gx * light[0] + gy * light[1]) * r * 2.6
    return np.clip(s, 0, 1) * m, np.clip(-s, 0, 1) * m


def _mask_into(m, w, h, x, y):
    out = np.zeros((h, w), np.float32)
    mh, mw = m.shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + mw, w), min(y + mh, h)
    if x0 < x1 and y0 < y1:
        out[y0:y1, x0:x1] = m[y0 - y:y1 - y, x0 - x:x1 - x]
    return out


def _lines(title, longest=11):
    """A title split into two balanced lines when it is long and has several words."""
    words = title.split()
    if len(title) <= longest or len(words) < 2:
        return [title]
    best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def _word(lines, font, size, tracking=0.0, italic=0.0, stretch=1.0, leading=0.92):
    """One or two lines of text as a single mask, centred, with room round it."""
    masks = []
    for line in lines:
        m, _ = P.text_mask(line, font, size, tracking=tracking, italic=italic, stretch=stretch, pad=int(size * 0.2))
        masks.append(P.tight(m, 0)[0])
    w = max(m.shape[1] for m in masks) + int(size * 1.6)
    gap = int(size * (leading - 0.75))
    h = sum(m.shape[0] for m in masks) + gap * (len(masks) - 1) + int(size * 1.4)
    out = np.zeros((h, w), np.float32)
    y = int(size * 0.7)
    for m in masks:
        x = (w - m.shape[1]) // 2
        out[y:y + m.shape[0], x:x + m.shape[1]] = np.maximum(out[y:y + m.shape[0], x:x + m.shape[1]], m)
        y += m.shape[0] + gap
    return out


def _letters(text, font, size, tracking=0.0, sizes=None, place=None):
    """Each letter as its own mask on a shared canvas: sizes scales letters one by one, and place(i, x, total)
    returns a letter's (dx, dy, degrees) for arcs and bounces."""
    sizes = sizes or [1.0] * len(text)
    fonts = [P.font(font, size * k) for k in sizes]
    widths = [f.getlength(c) for f, c in zip(fonts, text)]
    total = sum(widths) + tracking * size * (len(text) - 1)
    pad = int(size * 0.9)
    w, h = int(total + 2 * pad), int(size * 2.6)
    base = int(h * 0.62)
    masks, x = [], pad
    for i, (c, cw) in enumerate(zip(text, widths)):
        lay = np.zeros((h, w), np.float32)
        if c != " ":
            m, b = P.text_mask(c, font, size * sizes[i], pad=int(size * 0.5))
            dx, dy, deg = place(i, x + cw / 2 - pad, total) if place else (0, 0, 0)
            mh, mw = m.shape
            if deg:
                m = P.rotate_layer(np.repeat(m[..., None], 4, axis=-1), deg)[..., 0]
            oy, ox = (m.shape[0] - mh) // 2, (m.shape[1] - mw) // 2
            lay = _mask_into(m, w, h, int(round(x - int(size * 0.5) + dx)) - ox, int(round(base - b + dy)) - oy)
        masks.append(lay)
        x += cw + tracking * size
    return masks, (w, h)


def _sparkle(lay, cx, cy, r, colour="#ffffff", strength=1.0):
    h, w = lay.shape[:2]
    m = P.blur(P.mask(w, h, P.star4(cx, cy, r, r * 0.07)), 0.8)
    core = P.disc(w, h, (cx, cy), r * 0.12, r * 0.08)
    P.paint(lay, colour, np.clip(m + P.blur(core, r * 0.15) * 1.5, 0, 1), strength)


def _grow(lay, below=0, right=0):
    """The layer on a bigger canvas: room added below and to the right."""
    h, w = lay.shape[:2]
    out = P.layer(w + right, h + below)
    out[:h, :w] = lay
    return out


def _badge(lay, text):
    """A badge ("64", "'94") on the logo's lower right: chunky italics in red and chrome, tilted."""
    lay = P.trim(lay, 4)
    m, _ = P.text_mask(text, "FRAHVIT.TTF", S * 0.9, italic=0.1, pad=int(S * 0.4))
    m = P.rotate_layer(np.repeat(m[..., None], 4, axis=-1), 8)[..., 0]
    m, _ = P.tight(m, int(S * 0.15))
    bh, bw = m.shape
    lay = _grow(lay, below=int(bh * 0.45), right=int(bw * 0.55))
    H, W = lay.shape[:2]
    face = _mask_into(m, W, H, W - bw, H - bh)
    badge = P.layer(W, H)
    P.paint(badge, "#000000", P.blur(P.dilate(face, S * 0.06), S * 0.05), 0.6)
    P.paint(badge, "#ffffff", P.dilate(face, S * 0.05))
    P.paint(badge, "#1a0408", P.dilate(face, S * 0.025))
    P.paint(badge, _fill(face, [(0, "#ffd6a0"), (0.4, "#ff3a2a"), (1, "#8a0612")]), face)
    hi, _ = _bevel(face, S * 0.02)
    P.paint(badge, "#ffffff", hi, 0.6)
    lay[:] = badge + lay * (1 - badge[..., 3:4])
    return lay


METALS = {
    "gold": [(0, "#fffbe0"), (0.22, "#ffe08a"), (0.5, "#dc9a2c"), (0.66, "#9a5c10"), (0.8, "#d29638"), (1, "#ffe39a")],
    "silver": [(0, "#ffffff"), (0.25, "#e4e8f0"), (0.5, "#98a2b4"), (0.66, "#4e5666"), (0.8, "#a8b0c0"), (1, "#f0f4fa")],
    "bronze": [(0, "#ffe8c8"), (0.22, "#f0b070"), (0.5, "#b06a2a"), (0.66, "#6a3410"), (0.8, "#b87a40"), (1, "#ffd8a8")],
    "jade": [(0, "#f0fff4"), (0.22, "#a8f0c0"), (0.5, "#2a9a5a"), (0.66, "#0e5a30"), (0.8, "#4ab478"), (1, "#d8ffe4")],
    "steel": [(0, "#f4f8ff"), (0.25, "#c8d4e4"), (0.5, "#6a7a90"), (0.62, "#2e3a4a"), (0.8, "#8a9ab0"), (1, "#e8f0fa")],
}
EDGES = {"gold": "#241004", "silver": "#141820", "bronze": "#1c0a02", "jade": "#04180c", "steel": "#2a0608"}


# Logo styles -------------------------------------------------------------------------------------------------------

def chrome_neon(title, subtitle=None, font="FRAHVIT.TTF", script="BRUSHSCI.TTF", outline="#ff2a6a", neon="#ff3aa8"):
    """An 80s racer's: the title in sheared heavy italics, chrome over a sunset, outlined in hot colour, with a neon
    script word across its lower right and speed lines behind it."""
    face = _word(_lines(title.upper(), 9), font, S, tracking=-0.01, italic=0.12)
    h, w = face.shape
    W, H = w + int(S * 1.2), h + int(S * 0.9)
    face = _mask_into(face, W, H, int(S * 0.5), int(S * 0.1))
    lay = P.layer(W, H)
    t0, t1 = _span(face)
    left, right = _cols(face)
    lines = []
    for fy, length in [(0.25, 1.4), (0.5, 1.0), (0.75, 1.6)]:
        y = t0 + (t1 - t0) * fy
        lines.append([(left - S * length, y - 4), (left + S * 0.3, y - S * 0.035), (left + S * 0.3, y + S * 0.035),
                      (left - S * length, y + 4)])
    speed = P.mask(W, H, lines)
    P.paint(lay, outline, speed * np.clip((np.arange(W)[None, :] - (left - S * 1.6)) / (S * 1.2), 0, 1))
    outer = P.dilate(face, S * 0.075)
    P.paint(lay, P.shade(outline, 0.25), P.blur(P.dilate(face, S * 0.11), S * 0.05), 0.85)
    P.paint(lay, _fill(outer, [(0, P.shade(outline, 1.4)), (0.5, outline), (1, P.shade(outline, 0.6))]), outer)
    P.paint(lay, "#0c0c26", P.dilate(face, S * 0.035))
    chrome = _fill(face, [(0, "#ffffff"), (0.16, "#dcefff"), (0.44, "#5a8ad8"), (0.5, "#16224e"), (0.53, "#ffe8c4"),
                          (0.74, "#ffae6a"), (1, "#8a4422")])
    P.paint(lay, chrome, face)
    hi, lo = _bevel(face, S * 0.03)
    P.paint(lay, "#ffffff", hi, 0.55)
    P.paint(lay, "#1a0a20", lo, 0.35)
    if subtitle:
        script_m, _ = P.text_mask(subtitle, script, S * 0.9, tracking=0.02, pad=int(S * 0.8))
        script_m = P.rotate_layer(np.repeat(script_m[..., None], 4, axis=-1), 7)[..., 0]
        script_m, _ = P.tight(script_m, int(S * 0.1))
        sh, sw = script_m.shape
        sm = _mask_into(script_m, W, H, int(right - sw * 0.93), int(t1 - sh * 0.42))
        P.paint(lay, neon, P.blur(P.dilate(sm, S * 0.02), S * 0.09), 0.9)
        P.paint(lay, P.shade(neon, 0.2), P.dilate(sm, S * 0.03), 0.9)
        P.paint(lay, neon, P.dilate(sm, S * 0.014))
        P.paint(lay, P.shade(neon, 1.85), P.erode(sm, S * 0.008))
        P.paint(lay, P.shade(neon, 1.3), P.blur(sm, S * 0.02), 0.5)
    _sparkle(lay, right - S * 0.35, t0 + S * 0.05, S * 0.32)
    _sparkle(lay, left + S * 0.6, t1 - S * 0.12, S * 0.2)
    return lay


def _emblem(kind, W, H, cx, base, size):
    """An emblem above a fantasy title: a sundered crown, a wave, a moon, a sword, a star or a cog."""
    if kind == "crown":
        outline = [(-0.52, 0.0), (-0.6, -0.48), (-0.42, -0.22), (-0.28, -0.6), (-0.15, -0.3), (0.0, -0.76), (0.15, -0.3),
                   (0.28, -0.6), (0.42, -0.22), (0.6, -0.48), (0.52, 0.0)]
        whole = P.mask(W, H, P.xform([outline, [(-0.54, 0.04), (0.54, 0.04), (0.54, -0.12), (-0.54, -0.12)]], size,
                                     (cx, base)))
        for jx, jy in [(-0.6, -0.5), (-0.28, -0.62), (0.0, -0.78), (0.28, -0.62), (0.6, -0.5)]:
            (px, py), = P.xform([[(jx, jy)]], size, (cx, base))[0]
            whole = np.maximum(whole, P.disc(W, H, (px, py), size * 0.055))
        # The crack runs down from the valley right of the middle spike, which stays whole.
        crack = [(0.15, -0.32), (0.2, -0.22), (0.12, -0.13), (0.18, -0.04), (0.13, 0.1)]
        left_side = P.mask(W, H, P.xform([[(0.15, -0.9)] + crack + [(-1.0, 0.1), (-1.0, -0.9)]], size, (cx, base)))
        gap = P.lines(W, H, P.xform([crack], size, (cx, base)), size * 0.024)
        left = whole * left_side * (1 - gap)
        right = P.shift(whole * (1 - left_side) * (1 - gap), size * 0.012, -size * 0.008)
        return np.clip(left + right, 0, 1)
    if kind == "wave":
        d = ("M -0.6 0 C -0.5 -0.3 -0.2 -0.62 0.15 -0.6 C 0.45 -0.58 0.55 -0.35 0.4 -0.22 C 0.32 -0.36 0.12 -0.4 0.0 -0.3 "
             "C -0.12 -0.2 -0.05 0 0.2 0 Z")
        return P.mask(W, H, P.xform(P.path(d), size, (cx, base)))
    if kind == "moon":
        r = size * 0.36
        c = (cx, base - r * 1.05)
        return np.clip(P.disc(W, H, c, r) - P.disc(W, H, (c[0] + r * 0.45, c[1] - r * 0.2), r * 0.85), 0, 1)
    if kind == "sword":
        blade = [(-0.035, -0.1), (0.035, -0.1), (0.035, -1.05), (0.0, -1.2), (-0.035, -1.05)]
        guard = [(-0.28, -0.08), (0.28, -0.08), (0.28, -0.0), (-0.28, 0.0)]
        grip = [(-0.03, 0.0), (0.03, 0.0), (0.03, 0.22), (-0.03, 0.22)]
        m = P.mask(W, H, P.xform([blade, guard, grip], size, (cx, base - size * 0.1)))
        return np.maximum(m, P.disc(W, H, (cx, base + size * 0.14), size * 0.05))
    if kind == "star":
        return P.mask(W, H, P.star4(cx, base - size * 0.42, size * 0.42, size * 0.12))
    if kind == "cog":
        r = size * 0.34
        c = (cx, base - r * 1.1)
        teeth = []
        for k in range(10):
            a = k / 10 * 2 * math.pi
            ca, sa = math.cos(a), math.sin(a)
            teeth.append([(c[0] + (r * 0.9) * ca - r * 0.14 * sa, c[1] + (r * 0.9) * sa + r * 0.14 * ca),
                          (c[0] + (r * 1.25) * ca - r * 0.1 * sa, c[1] + (r * 1.25) * sa + r * 0.1 * ca),
                          (c[0] + (r * 1.25) * ca + r * 0.1 * sa, c[1] + (r * 1.25) * sa - r * 0.1 * ca),
                          (c[0] + (r * 0.9) * ca + r * 0.14 * sa, c[1] + (r * 0.9) * sa - r * 0.14 * ca)])
        ring = np.clip(np.maximum(P.disc(W, H, c, r), P.mask(W, H, teeth)) - P.disc(W, H, c, r * 0.45), 0, 1)
        return ring
    if kind == "lotus":                                         # five pointed petals fanned over a shallow bowl
        petal = "M 0 0 Q 0.22 -0.4 0 -0.78 Q -0.22 -0.4 0 0 Z"
        polys = []
        for angle, length in ((-64, 0.74), (64, 0.74), (-32, 0.9), (32, 0.9), (0, 1.0)):
            polys += P.xform(P.path(petal), (size * length, size * length), (cx, base - size * 0.02), rotate=angle)
        petals = P.mask(W, H, polys)
        bowl = P.mask(W, H, P.path(f"M {cx - size * 0.42} {base - size * 0.1} Q {cx} {base + size * 0.12} "
                                   f"{cx + size * 0.42} {base - size * 0.1} L {cx + size * 0.36} {base - size * 0.02} "
                                   f"Q {cx} {base + size * 0.17} {cx - size * 0.36} {base - size * 0.02} Z"))
        return np.clip(petals + bowl, 0, 1)
    return np.zeros((H, W), np.float32)


def gold_serif(title, subtitle=None, font="PERTIBD.TTF", metal="gold", emblem="crown"):
    """A fantasy game's: titling capitals, each word's first letter taller, cast in bevelled metal with a dark edge, an
    emblem above and the subtitle in silver between ornaments."""
    lines = _lines(title.upper(), 11)
    masks = []
    for line in lines:
        sizes = []
        for k, c in enumerate(line):
            first = k == 0 or line[k - 1] == " "
            last = k == len(line) - 1 or line[k + 1] == " "
            sizes.append(1.22 if first or (last and len(lines) == 1 and " " not in line) else 1.0)
        ms, (w, h) = _letters(line, font, S, tracking=0.035, sizes=sizes)
        masks.append(P.tight(np.clip(sum(ms), 0, 1), 0)[0])
    lw = max(m.shape[1] for m in masks)
    W = lw + int(S * 1.4)
    top = int(S * (1.1 if emblem not in (None, "none") else 0.4))
    H = top + sum(m.shape[0] for m in masks) + int(S * 0.12) * (len(masks) - 1) + int(S * 1.1)
    face = np.zeros((H, W), np.float32)
    y = top
    for m in masks:
        x = (W - m.shape[1]) // 2
        face[y:y + m.shape[0], x:x + m.shape[1]] = np.maximum(face[y:y + m.shape[0], x:x + m.shape[1]], m)
        y += m.shape[0] + int(S * 0.12)
    lay = P.layer(W, H)
    t0, t1 = _span(face)
    left, right = _cols(face)
    mid = (left + right) / 2
    mark = _emblem(emblem, W, H, mid, t0 + S * 0.1, S * 0.95) * (1 - P.dilate(face, S * 0.03))
    shape = np.clip(face + mark, 0, 1)
    edge = EDGES.get(metal, "#241004")
    P.paint(lay, "#000000", P.blur(P.dilate(shape, S * 0.07), S * 0.07), 0.75)
    P.paint(lay, edge, P.dilate(shape, S * 0.045))
    P.paint(lay, METALS[metal][1][1], P.dilate(shape, S * 0.018))
    P.paint(lay, _fill(face, METALS[metal]), face)
    if mark.max() > 0:
        P.paint(lay, _fill(mark, METALS[metal]), mark)
    hi, lo = _bevel(shape, S * 0.025)
    P.paint(lay, "#ffffff", hi, 0.7)
    P.paint(lay, P.shade(edge, 2.0), lo, 0.55)
    for x in (left + S * 0.3, right - S * 0.45):
        _sparkle(lay, x, t0 + S * 0.1, S * 0.28)
    if subtitle:
        sub, _ = P.text_mask(subtitle.upper(), font if font != "BOD_PSTC.TTF" else "PERTIBD.TTF", S * 0.3, tracking=0.16,
                             pad=int(S * 0.2))
        sub, _ = P.tight(sub, int(S * 0.08))
        sh, sw = sub.shape
        sx, sy = int(mid - sw / 2), int(t1 + S * 0.06)
        sm = _mask_into(sub, W, H, sx, sy)
        orn = []
        for side in (-1, 1):
            x0 = mid + side * (sw / 2 + S * 0.05)
            x1 = mid + side * (sw / 2 + S * 0.75)
            yc = sy + sh / 2
            orn.append([(x0, yc - 2), (x1, yc - 1), (x1, yc + 1), (x0, yc + 2)])
            orn.append([(x0, yc), (x0 + side * S * 0.05, yc - S * 0.05), (x0 + side * S * 0.1, yc),
                        (x0 + side * S * 0.05, yc + S * 0.05)])
        om = P.mask(W, H, orn)
        allm = np.clip(sm + om, 0, 1)
        P.paint(lay, "#000000", P.blur(P.dilate(allm, S * 0.03), S * 0.03), 0.7)
        P.paint(lay, "#1a1006", P.dilate(allm, S * 0.016))
        P.paint(lay, _fill(sm, [(0, "#ffffff"), (1, "#a9b2cc")]), sm)
        P.paint(lay, _fill(om, METALS[metal][1:4]), om)
    return lay


STEELS = {
    "blue": ([(0, "#ffffff"), (0.32, "#b8d6ff"), (0.5, "#34548e"), (0.53, "#0c1530"), (0.57, "#7aaeff"), (1, "#eaf6ff")], "#22c4ff"),
    "teal": ([(0, "#ffffff"), (0.32, "#b8fff0"), (0.5, "#2a8a80"), (0.53, "#06302c"), (0.57, "#5ae0c8"), (1, "#e4fffa")], "#20ffd0"),
    "red": ([(0, "#ffffff"), (0.32, "#ffd0c8"), (0.5, "#a8342a"), (0.53, "#300806"), (0.57, "#ff8a6a"), (1, "#fff0ea")], "#ff4a2a"),
    "gold": ([(0, "#ffffff"), (0.32, "#fff0b8"), (0.5, "#b88a2a"), (0.53, "#3a2604"), (0.57, "#ffd060"), (1, "#fffae8")], "#ffb020"),
}


def steel_flare(title, subtitle=None, font="ERASBD.TTF", steel="blue"):
    """A science-fiction game's: the title wide and metallic with a cut across it and a coloured glow, the second word
    in hot italics beneath, a lens flare along it."""
    face = _word(_lines(title.upper(), 9), font, S, tracking=0.03, stretch=1.08)
    h, w = face.shape
    W, H = w + int(S * 0.6), h + int(S * (1.0 if subtitle else 0.2))
    face = _mask_into(face, W, H, int(S * 0.3), 0)
    t0, t1 = _span(face)
    rows = np.arange(H)[:, None].astype(np.float32)
    line_h = (t1 - t0) if (t1 - t0) < S * 1.3 else S
    cut = np.clip(np.abs(((rows - t0) % (line_h + S * 0.15)) - line_h * 0.66) - S * 0.012, 0, 1)
    face = face * cut
    stops, glow = STEELS[steel]
    lay = P.layer(W, H)
    P.paint(lay, glow, P.blur(P.dilate(face, S * 0.04), S * 0.09), 0.85)
    P.paint(lay, "#040814", P.dilate(face, S * 0.04))
    P.paint(lay, P.shade(glow, 1.6), P.dilate(face, S * 0.012))
    P.paint(lay, _fill(face, stops), face)
    hi, lo = _bevel(face, S * 0.02)
    P.paint(lay, "#ffffff", hi, 0.6)
    P.paint(lay, "#000010", lo, 0.4)
    left, right = _cols(face)
    if subtitle:
        sub, _ = P.text_mask(subtitle.upper(), "FRAHVIT.TTF", S * 0.62, tracking=0.22, italic=0.08, pad=int(S * 0.3))
        sub, _ = P.tight(sub, int(S * 0.1))
        sh, sw = sub.shape
        sm = _mask_into(sub, W, H, int(right - sw + S * 0.05), int(t1 - S * 0.02))
        P.paint(lay, "#ff5a10", P.blur(P.dilate(sm, S * 0.03), S * 0.06), 0.8)
        P.paint(lay, "#1a0404", P.dilate(sm, S * 0.032))
        P.paint(lay, _fill(sm, [(0, "#fff4a8"), (0.45, "#ff8a1a"), (1, "#c0101e")]), sm)
        hi, _ = _bevel(sm, S * 0.015)
        P.paint(lay, "#ffffff", hi, 0.5)
    fy = t0 + min(t1 - t0, S) * 0.36
    beam = np.exp(-((rows - fy) / (S * 0.008)) ** 2) * np.clip(1 - np.abs(np.arange(W)[None, :] - W * 0.45) / (W * 0.55), 0, 1)
    P.paint(lay, "#e8fbff", np.clip(beam * 1.5, 0, 1), 0.9)
    _sparkle(lay, left + (right - left) * 0.2, fy, S * 0.5, "#ffffff")
    return lay


GEM_COLOURS = ["#ff2d55", "#ff9500", "#ffd60a", "#34c759", "#32ade6", "#5856d6", "#af52de", "#ff2d92", "#ff6b3d"]


def _gem(w, h, cx, cy, r, colour):
    """A round brilliant seen from above, as facets: (mask, shaded colour layer)."""
    n = 8
    outer = [(cx + r * math.cos(2 * math.pi * (k + 0.5) / n), cy + r * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)]
    table = [(cx + r * 0.52 * math.cos(2 * math.pi * (k + 0.5) / n), cy + r * 0.52 * math.sin(2 * math.pi * (k + 0.5) / n))
             for k in range(n)]
    m = P.mask(w, h, [outer])
    col = np.zeros((h, w, 3), np.float32)
    base = P.rgb(colour)
    for k in range(n):
        facet = P.mask(w, h, [[outer[k], outer[(k + 1) % n], table[(k + 1) % n], table[k]]])
        light = 0.75 + 0.45 * math.cos(2 * math.pi * (k + 1) / n - math.radians(225))
        col += facet[..., None] * np.clip(base * light + (light - 1.0) * 0.3, 0, 1)
    tm = P.mask(w, h, [table])
    col = col * (1 - tm[..., None]) + tm[..., None] * np.clip(base * 1.15 + 0.12, 0, 1)
    return m, col


def candy_gems(title, subtitle=None, font="COOPBL.TTF", gem=True):
    """A puzzle game's: chunky rounded letters, each its own colour, bouncing on the line, glossy, with a white edge and
    a dark one round the whole word; an O becomes a cut gem."""
    lines = _lines(title.upper(), 10)
    layers = []
    colour_index = 0
    for line in lines:
        def place(i, x, total):
            return 0, -math.sin(i * 1.3) * S * 0.07, (4 if i % 2 else -4)

        masks, (W, H) = _letters(line, font, S, tracking=0.02, place=place)
        lay = P.layer(W, H)
        union = np.clip(sum(masks), 0, 1)
        P.paint(lay, "#000000", P.shift(P.blur(P.dilate(union, S * 0.07), S * 0.02), S * 0.03, S * 0.06), 0.4)
        P.paint(lay, "#2a0a4a", P.dilate(union, S * 0.07))
        P.paint(lay, "#ffffff", P.dilate(union, S * 0.035))
        for i, (c, m) in enumerate(zip(line, masks)):
            if c == " ":
                continue
            colour = GEM_COLOURS[colour_index % len(GEM_COLOURS)]
            colour_index += 1
            if c == "O" and gem:
                ys, xs = np.nonzero(m > 0.5)
                cx, cy = xs.mean(), ys.mean()
                r = (xs.max() - xs.min()) * 0.5
                P.paint(lay, "#ffffff", P.dilate(P.disc(W, H, (cx, cy), r), S * 0.035))
                gm, gc = _gem(W, H, cx, cy, r, colour)
                P.paint(lay, gc, gm)
                _sparkle(lay, cx - r * 0.35, cy - r * 0.4, r * 0.55)
                continue
            P.paint(lay, _fill(m, [(0, P.shade(colour, 1.45)), (0.45, colour), (1, P.shade(colour, 0.62))]), m)
            hi, lo = _bevel(m, S * 0.03)
            P.paint(lay, "#ffffff", hi, 0.45)
            P.paint(lay, "#200030", lo, 0.3)
            t0, t1 = _span(m)
            gloss = m * np.clip((t0 + (t1 - t0) * 0.42 - np.arange(H)[:, None]) / (S * 0.05), 0, 1)
            P.paint(lay, "#ffffff", P.erode(gloss, S * 0.035), 0.4)
        layers.append(P.trim(lay, 2))
    return _stack(layers)


def _stack(layers, gap=-0.05):
    """Layers one above another, centred."""
    if len(layers) == 1:
        return layers[0]
    W = max(l.shape[1] for l in layers)
    H = sum(l.shape[0] for l in layers) + int(S * gap) * (len(layers) - 1)
    out = P.layer(W, H)
    y = 0
    for l in layers:
        x = (W - l.shape[1]) // 2
        h = min(l.shape[0], H - y)
        sub = out[y:y + h, x:x + l.shape[1]]
        sub[:] = l[:h] + sub * (1 - l[:h, :, 3:4])
        y += l.shape[0] + int(S * gap)
    return out


FACES = {
    "green": ([(0, "#efffa8"), (0.4, "#8ee04a"), (1, "#2c962e")], [(0, "#1e7a26"), (1, "#0e4416")], "#0a2a0e"),
    "orange": ([(0, "#fff0a0"), (0.4, "#ffb02a"), (1, "#e05a10")], [(0, "#a83c08"), (1, "#5a1c02")], "#2a0c02"),
    "red": ([(0, "#ffd0c0"), (0.4, "#ff4a3a"), (1, "#b01020")], [(0, "#7a0a14"), (1, "#40040a")], "#200206"),
    "purple": ([(0, "#f4e0ff"), (0.4, "#b46aff"), (1, "#6a1ab0")], [(0, "#3e0a78"), (1, "#1e043c")], "#10021e"),
    "blue": ([(0, "#e0f4ff"), (0.4, "#4ab4ff"), (1, "#1a5ad8")], [(0, "#0e3a8a"), (1, "#061c48")], "#020a1e"),
    "ice": ([(0, "#ffffff"), (0.45, "#c8ecff"), (1, "#4aa0e8")], [(0, "#2a6ab0"), (1, "#123a70")], "#061a34"),
}
RIBBONS = {"red": [(0, "#ff8a5a"), (0.5, "#e8382a"), (1, "#a01c16")], "blue": [(0, "#7ac8ff"), (0.5, "#2a7ae8"), (1, "#1a3c9a")],
           "purple": [(0, "#d8a0ff"), (0.5, "#8a3ae8"), (1, "#4a1a9a")]}


def cartoon_arch(title, subtitle=None, font="SNAP____.TTF", face="green", ribbon="red", arch=1.0):
    """A mascot game's: playful letters on an arch, glossy, a white edge and a deep extrusion, the subtitle on a
    ribbon beneath."""
    def place(i, x, total):
        t = x / total - 0.5
        return 0, (t * t) * S * 1.4 * arch - S * 0.2 * arch, -t * 22 * arch

    masks, (W, H) = _letters(title, font, S, tracking=0.0, place=place)
    H2 = H + int(S * 0.9)
    union = np.zeros((H2, W), np.float32)
    union[:H] = np.clip(sum(masks), 0, 1)
    fill, ext_stops, dark = FACES[face]
    lay = P.layer(W, H2)
    ext = np.zeros_like(union)
    for k in range(1, 15):
        ext = np.maximum(ext, P.shift(union, S * 0.004 * k, S * 0.009 * k))
    whole = np.clip(ext + union, 0, 1)
    P.paint(lay, "#000000", P.blur(P.dilate(whole, S * 0.06), S * 0.05), 0.4)
    P.paint(lay, dark, P.dilate(whole, S * 0.045))
    P.paint(lay, _fill(ext, ext_stops), ext)
    P.paint(lay, "#ffffff", P.dilate(union, S * 0.03))
    P.paint(lay, _fill(union, fill), union)
    hi, lo = _bevel(union, S * 0.03)
    P.paint(lay, "#ffffff", hi, 0.55)
    P.paint(lay, dark, lo, 0.35)
    t0, t1 = _span(union)
    gloss = union * np.clip((t0 + (t1 - t0) * 0.38 - np.arange(H2)[:, None]) / (S * 0.06), 0, 1)
    P.paint(lay, "#ffffff", P.erode(gloss, S * 0.03), 0.35)
    if face == "ice":                                    # snow lying along the letters' tops
        snow = np.clip(union - P.shift(union, 0, -S * 0.05), 0, 1)
        P.paint(lay, "#ffffff", P.blur(P.dilate(snow, S * 0.02), 2), 0.95)
    left, right = _cols(union)
    if subtitle:
        mid = (left + right) / 2
        rw, rh = (right - left) * 0.42, S * 0.26
        ry = t1 + S * 0.08

        def arc_y(y, k):
            return y + ((k - 0.5) ** 2 - 0.25) * S * 0.25 * max(arch, 0.3)          # higher in the middle

        top = [(mid - rw + 2 * rw * k / 20, arc_y(ry, k / 20)) for k in range(21)]
        bottom = [(x, y + rh) for x, y in top[::-1]]
        band = P.mask(W, H2, [top + bottom])
        tails = P.mask(W, H2, [[(mid - rw + S * 0.1, ry + rh * 0.3), (mid - rw - S * 0.35, ry + rh * 0.3),
                                (mid - rw - S * 0.22, ry + rh * 0.8), (mid - rw - S * 0.35, ry + rh * 1.3),
                                (mid - rw + S * 0.1, ry + rh * 1.3)],
                               [(mid + rw - S * 0.1, ry + rh * 0.3), (mid + rw + S * 0.35, ry + rh * 0.3),
                                (mid + rw + S * 0.22, ry + rh * 0.8), (mid + rw + S * 0.35, ry + rh * 1.3),
                                (mid + rw - S * 0.1, ry + rh * 1.3)]])
        stops = RIBBONS[ribbon]
        both = np.clip(band + tails, 0, 1)
        P.paint(lay, "#000000", P.blur(P.dilate(both, S * 0.04), S * 0.04), 0.35)
        P.paint(lay, P.shade(stops[2][1], 0.4), P.dilate(both, S * 0.025))
        P.paint(lay, stops[2][1], tails)
        P.paint(lay, _fill(band, stops), band)
        sub, _ = P.text_mask(subtitle.upper(), "ERASBD.TTF", S * 0.2, tracking=0.12, pad=int(S * 0.1))
        sub, _ = P.tight(sub, 2)
        sh, sw = sub.shape
        sm = _mask_into(sub, W, H2, int(mid - sw / 2), int(arc_y(ry, 0.5) + (rh - sh) / 2))
        P.paint(lay, P.shade(stops[2][1], 0.4), P.dilate(sm, S * 0.015))
        P.paint(lay, "#ffffff", sm)
    return lay


def sports_block(title, subtitle=None, font="FRAHVIT.TTF", colours=("#ffffff", "#1d6cd8")):
    """A sports game's: heavy italic capitals in two tones, a white edge and a dark one, over a swoosh."""
    face = _word(_lines(title.upper(), 11), font, S, tracking=0.01, italic=0.14 if "FRAHVIT" not in font else 0.06)
    h, w = face.shape
    W, H = w + int(S * 0.8), h + int(S * 0.7)
    face = _mask_into(face, W, H, int(S * 0.4), int(S * 0.1))
    t0, t1 = _span(face)
    left, right = _cols(face)
    a, b = colours
    rows = np.arange(H)[:, None].astype(np.float32)
    lay = P.layer(W, H)
    swoosh_y = t1 + S * 0.12
    d = (f"M {left - S * 0.3} {swoosh_y} C {left + (right - left) * 0.3} {swoosh_y + S * 0.25} "
         f"{left + (right - left) * 0.75} {swoosh_y - S * 0.05} {right + S * 0.4} {swoosh_y - S * 0.45} "
         f"C {left + (right - left) * 0.75} {swoosh_y + S * 0.12} {left + (right - left) * 0.3} {swoosh_y + S * 0.4} "
         f"{left - S * 0.3} {swoosh_y} Z")
    swoosh = P.mask(W, H, P.path(d))
    P.paint(lay, "#000000", P.blur(P.dilate(np.clip(face + swoosh, 0, 1), S * 0.08), S * 0.05), 0.5)
    P.paint(lay, "#0a1020", P.dilate(swoosh, S * 0.03))
    P.paint(lay, _fill(swoosh, [(0, P.shade(b, 1.4)), (1, P.shade(b, 0.7))]), swoosh)
    P.paint(lay, "#0a1020", P.dilate(face, S * 0.075))
    P.paint(lay, "#ffffff", P.dilate(face, S * 0.045))
    P.paint(lay, "#0a1020", P.dilate(face, S * 0.02))
    line_h = min(t1 - t0, S * 1.1)
    split = ((rows - t0) % (line_h + S * 0.1)) > line_h * 0.6
    two_tone = np.where(split[..., None], P.rgb(b)[None, None, :] * np.ones((1, W, 1)),
                        _fill(face, [(0, P.shade(a, 1.2)), (0.6, a), (1, P.shade(a, 0.75))]))
    P.paint(lay, two_tone, face)
    hi, lo = _bevel(face, S * 0.02)
    P.paint(lay, "#ffffff", hi, 0.5)
    P.paint(lay, "#000000", lo, 0.3)
    return lay


def horror_drip(title, subtitle=None, font="CHILLER.TTF"):
    """A horror game's: bone-white letters bleeding from their lower edges, a cold glow behind, the subtitle in red."""
    face = _word([title.upper()], font, S * 1.15, tracking=0.04)
    h, w = face.shape
    W, H = w, h + int(S * (0.9 if subtitle else 0.5))
    face = _mask_into(face, W, H, 0, 0)
    t0, t1 = _span(face)
    rng = np.random.default_rng(len(title))
    drips = np.zeros((H, W), np.float32)
    bottom_edge = np.clip(face - P.shift(face, 0, -6), 0, 1)
    ys, xs = np.nonzero(bottom_edge > 0.5)
    for _ in range(18):
        k = rng.integers(0, len(xs))
        x, y = xs[k], ys[k]
        length = rng.uniform(0.15, 0.6) * S
        width = rng.uniform(0.025, 0.05) * S
        drips = np.maximum(drips, P.mask(W, H, [[(x - width, y - 4), (x + width, y - 4), (x + width * 0.6, y + length),
                                                 (x - width * 0.6, y + length)]]))
        drips = np.maximum(drips, P.disc(W, H, (x, y + length), width * 1.1))
    lay = P.layer(W, H)
    P.paint(lay, "#4aff9a", P.blur(P.dilate(face, S * 0.05), S * 0.12), 0.45)
    P.paint(lay, "#000000", P.dilate(np.clip(face + drips, 0, 1), S * 0.03))
    P.paint(lay, _fill(drips, [(0, "#a00010"), (1, "#5a0008")]), drips)
    P.paint(lay, _fill(face, [(0, "#ffffff"), (0.5, "#d8d4c4"), (1, "#8a8478")]), face)
    hi, lo = _bevel(face, S * 0.02)
    P.paint(lay, "#ffffff", hi, 0.4)
    P.paint(lay, "#2a0004", lo, 0.4)
    if subtitle:
        sub, _ = P.text_mask(subtitle.upper(), "TCCEB.TTF", S * 0.38, tracking=0.5, pad=int(S * 0.2))
        sub, _ = P.tight(sub, 2)
        sh, sw = sub.shape
        sm = _mask_into(sub, W, H, int((W - sw) / 2), int(t1 + S * 0.12))
        P.paint(lay, "#000000", P.dilate(sm, S * 0.02))
        P.paint(lay, _fill(sm, [(0, "#ff4040"), (1, "#8a0010")]), sm)
    return lay


PLATES = {"olive": ("#6a7040", "#2a2c14", "#ffd23a"), "sand": ("#c8a060", "#5a3c14", "#2a1406"),
          "mud": ("#7a5a3a", "#2a1a0c", "#ffd23a"), "steel": ("#8a94a0", "#2a3038", "#ffd23a")}


def stencil_plate(title, subtitle=None, plate="olive"):
    """A military or rally game's: stencilled capitals sprayed on a riveted metal plate."""
    lines = _lines(title.upper(), 10)
    face = _word(lines, "STENCIL.TTF", S, tracking=0.04, leading=0.9)
    face, _ = P.tight(face, 0)
    fh, fw = face.shape
    pad = int(S * 0.35)
    W, H = fw + 2 * pad + int(S * 0.4), fh + 2 * pad + int(S * 0.4)
    lay = P.layer(W, H)
    x0, y0 = int(S * 0.2), int(S * 0.2)
    pw, ph = W - 2 * x0, H - 2 * y0
    r = S * 0.12
    d = (f"M {x0 + r} {y0} H {x0 + pw - r} Q {x0 + pw} {y0} {x0 + pw} {y0 + r} V {y0 + ph - r} Q {x0 + pw} {y0 + ph} "
         f"{x0 + pw - r} {y0 + ph} H {x0 + r} Q {x0} {y0 + ph} {x0} {y0 + ph - r} V {y0 + r} Q {x0} {y0} {x0 + r} {y0} Z")
    plate_m = P.mask(W, H, P.path(d))
    body, edge, ink = PLATES[plate]
    P.paint(lay, "#000000", P.blur(P.dilate(plate_m, S * 0.05), S * 0.06), 0.6)
    P.paint(lay, edge, P.dilate(plate_m, S * 0.025))
    P.paint(lay, _fill(plate_m, [(0, P.shade(body, 1.35)), (0.5, body), (1, P.shade(body, 0.6))]), plate_m)
    hi, lo = _bevel(plate_m, S * 0.04)
    P.paint(lay, "#ffffff", hi, 0.35)
    P.paint(lay, "#000000", lo, 0.35)
    for cx, cy in [(x0 + S * 0.12, y0 + S * 0.12), (x0 + pw - S * 0.12, y0 + S * 0.12), (x0 + S * 0.12, y0 + ph - S * 0.12),
                   (x0 + pw - S * 0.12, y0 + ph - S * 0.12)]:
        rivet = P.disc(W, H, (cx, cy), S * 0.045)
        P.paint(lay, _fill(rivet, [(0, "#f0f0f0"), (1, "#404040")]), rivet)
    letters = _mask_into(face, W, H, (W - fw) // 2, (H - fh) // 2)
    wear = np.random.default_rng(len(title)).random((H, W)).astype(np.float32)
    wear = P.blur(wear, 2.0)
    chipped = letters * np.clip((wear - 0.42) * 12, 0, 1)
    P.paint(lay, "#000000", P.shift(chipped, S * 0.015, S * 0.02), 0.5)
    P.paint(lay, ink, chipped)
    return lay


FIRES = {
    "fire": ([(0, "#fffbd0"), (0.3, "#ffd23a"), (0.65, "#ff6a10"), (1, "#a80a0a")], "#ff5a10", "#1a0202"),
    "storm": ([(0, "#ffffff"), (0.3, "#c8f0ff"), (0.65, "#3aa0ff"), (1, "#1a2a9a")], "#3ac8ff", "#020818"),
    "graffiti": ([(0, "#fff0ff"), (0.3, "#ff7ae0"), (0.65, "#c82ab0"), (1, "#5a0a6a")], "#3affb0", "#12021a"),
}


def fire_brush(title, subtitle=None, font="HATTEN.TTF", colours="fire"):
    """An action game's: tall condensed capitals burning in their colours, flames licking up from them, the subtitle in
    white italics on a dark slash."""
    face = _word([title.upper()], font, S * 1.2, tracking=0.03, italic=0.08)
    h, w = face.shape
    W, H = w, h + int(S * (0.8 if subtitle else 0.2))
    face = _mask_into(face, W, H, 0, 0)
    stops, glow, dark = FIRES[colours]
    t0, t1 = _span(face)
    lay = P.layer(W, H)
    noise = P.blur(np.random.default_rng(len(title) + 3).random((H, W)).astype(np.float32), S * 0.04)
    noise = (noise - noise.min()) / max(noise.max() - noise.min(), 1e-6)
    tongues = np.zeros((H, W), np.float32)
    up = face.copy()
    for k in range(1, 12):
        up = np.maximum(up * 0.92, P.shift(up, 0, -S * 0.025))
        tongues = np.maximum(tongues, up)
    flames = np.clip(tongues - face, 0, 1) * np.clip((noise - 0.45) * 5, 0, 1)
    if colours != "fire":
        flames *= 0.0
    if colours == "storm":                                       # forked lightning striking the word, instead of flames
        left, right = _cols(face)
        bolts = []
        for x0, lean in ((left + (right - left) * 0.22, 1), (left + (right - left) * 0.74, -1)):
            pts, x, y = [], x0, t0 + S * 0.15
            for k in range(6):
                pts.append((x, y))
                x += lean * S * (0.1 if k % 2 else -0.04)
                y -= S * 0.11
            bolts.append(pts)
            bolts.append([pts[3], (pts[3][0] - lean * S * 0.12, pts[3][1] - S * 0.05), (pts[3][0] - lean * S * 0.16, pts[3][1] - S * 0.16)])
        bolt = P.lines(W, H, bolts, S * 0.035)
        P.paint(lay, glow, P.blur(P.dilate(bolt, S * 0.02), S * 0.06), 1.0)
        P.paint(lay, P.shade(glow, 1.6), bolt)
        P.paint(lay, "#ffffff", P.erode(bolt, S * 0.008))
    P.paint(lay, glow, P.blur(P.dilate(face, S * 0.05), S * 0.1), 0.8)
    P.paint(lay, _fill(flames, stops[1:]), flames, 0.9)
    P.paint(lay, dark, P.dilate(face, S * 0.04))
    P.paint(lay, _fill(face, stops), face)
    hi, lo = _bevel(face, S * 0.02)
    P.paint(lay, "#ffffff", hi, 0.5)
    P.paint(lay, dark, lo, 0.4)
    if subtitle:
        sub, _ = P.text_mask(subtitle.upper(), "FRAHVIT.TTF", S * 0.5, tracking=0.25, italic=0.1, pad=int(S * 0.2))
        sub, _ = P.tight(sub, 2)
        sh, sw = sub.shape
        sx, sy = int((W - sw) / 2), int(t1 + S * 0.08)
        slash = P.mask(W, H, [[(sx - S * 0.3, sy + sh + S * 0.08), (sx + sw + S * 0.15, sy + sh + S * 0.08),
                               (sx + sw + S * 0.35, sy - S * 0.08), (sx - S * 0.1, sy - S * 0.08)]])
        sm = _mask_into(sub, W, H, sx, sy)
        P.paint(lay, "#000000", P.blur(P.dilate(slash, S * 0.03), S * 0.03), 0.5)
        P.paint(lay, dark, slash)
        P.paint(lay, "#ffffff", sm)
    return lay


def arcade_pixel(title, subtitle=None, colours=("#ffe040", "#ff4020", "#a01070")):
    """An arcade game's: the title in big pixels, each a bevelled tile, in a sunset of colours."""
    from screens import _glyph, ADVANCE                             # the HUDs' bitmap font
    lines = _lines(title.upper(), 8)
    px = int(S * 0.16)
    rows_h = 7 * px
    W = max(len(l) for l in lines) * ADVANCE * px + 2 * S
    H = len(lines) * (rows_h + 2 * px) + 2 * S
    tiles = np.zeros((H, W), np.float32)
    for li, line in enumerate(lines):
        lw = len(line) * ADVANCE * px
        x0 = (W - lw) // 2
        y0 = S + li * (rows_h + 2 * px)
        for k, ch in enumerate(line):
            g = _glyph(ch)
            for gy, gx in zip(*np.nonzero(g)):
                x, y = x0 + (k * ADVANCE + gx) * px, y0 + gy * px
                tiles[y + 1:y + px - 1, x + 1:x + px - 1] = 1
    lay = P.layer(W, H)
    P.paint(lay, "#000000", P.shift(P.dilate(tiles, px * 0.5), px * 0.4, px * 0.5), 0.6)
    P.paint(lay, "#ffffff", P.dilate(tiles, px * 0.35))
    P.paint(lay, "#1a0420", P.dilate(tiles, px * 0.15))
    P.paint(lay, _fill(tiles, [(0, colours[0]), (0.5, colours[1]), (1, colours[2])]), tiles)
    hi, lo = _bevel(tiles, px * 0.18)
    P.paint(lay, "#ffffff", hi, 0.6)
    P.paint(lay, "#000000", lo, 0.4)
    return lay


def retro_flat(title, subtitle=None, font="SHOWG.TTF", face="#ff3a2a", edge="#ffe040", depth="#5a1408"):
    """An early-1980s marquee's: flat letters in one bright colour, no gradient, a thick outline in another, a black
    one round that, and a solid extrusion down and to the right."""
    face_m = _word(_lines(title.upper(), 9), font, S, tracking=0.04, leading=0.95)
    face_m = _mask_into(face_m, face_m.shape[1] + int(S * 0.4), face_m.shape[0] + int(S * 0.4), 0, 0)
    H, W = face_m.shape
    rim = P.dilate(face_m, S * 0.06)
    ext = np.zeros_like(rim)
    for k in range(1, 12):
        ext = np.maximum(ext, P.shift(rim, S * 0.008 * k, S * 0.011 * k))
    lay = P.layer(W, H)
    P.paint(lay, "#000000", P.dilate(np.clip(rim + ext, 0, 1), S * 0.035))
    P.paint(lay, depth, ext)
    P.paint(lay, edge, rim)
    P.paint(lay, "#000000", P.dilate(face_m, S * 0.012))
    P.paint(lay, face, face_m)
    shine = np.clip(face_m - P.shift(face_m, S * 0.02, S * 0.025), 0, 1)     # a thin white line along the top left
    P.paint(lay, "#ffffff", shine, 0.85)
    return lay


def modern_edge(title, subtitle=None, font="seguibl.ttf", accent="#ff2a6a"):
    """A 2010s fighting game's: heavy italics in brushed steel, split by a thin cut, their lower part in the accent
    colour, over a slash of it, with a glow and an angular crown over the middle."""
    face = _word([title.upper()], font, S, tracking=0.02, italic=0.18)
    h, w = face.shape
    W, H = w + int(S * 0.8), h + int(S * 0.9)
    face = _mask_into(face, W, H, int(S * 0.4), int(S * 0.5))
    t0, t1 = _span(face)
    left, right = _cols(face)
    rows = np.arange(H, dtype=np.float32)[:, None]
    split = t0 + (t1 - t0) * 0.6
    cut = np.clip(np.abs(rows - split) - S * 0.01, 0, 1)
    face = face * cut
    lay = P.layer(W, H)
    slash = P.mask(W, H, [[(left - S * 0.2, t1 + S * 0.08), (right + S * 0.4, t0 + S * 0.2), (right + S * 0.5, t0 + S * 0.32),
                           (left - S * 0.1, t1 + S * 0.2)]])
    P.paint(lay, accent, P.blur(slash, S * 0.03), 0.9)
    P.paint(lay, accent, P.blur(P.dilate(face, S * 0.05), S * 0.12), 0.8)
    P.paint(lay, "#06060a", P.dilate(face, S * 0.035))
    steel = _fill(face, [(0, "#ffffff"), (0.3, "#d8dce4"), (0.55, "#8a909c"), (0.6, "#ffffff"), (1, "#b8bcc8")])
    lower = np.clip((rows - split) / 2, 0, 1)
    P.paint(lay, steel, face * (1 - lower))
    P.paint(lay, _fill(face, [(0, P.shade(accent, 1.5)), (0.6, accent), (1, P.shade(accent, 0.55))]), face * lower)
    hi, lo = _bevel(face, S * 0.015)
    P.paint(lay, "#ffffff", hi, 0.6)
    P.paint(lay, "#000000", lo, 0.3)
    mid, cs = (left + right) / 2, S * 0.5                       # the crown: three sharp spikes on a band
    crown = P.mask(W, H, [[(mid - cs * 0.6, t0 - S * 0.08), (mid - cs * 0.7, t0 - cs * 0.62), (mid - cs * 0.3, t0 - cs * 0.3),
                           (mid, t0 - cs * 0.85), (mid + cs * 0.3, t0 - cs * 0.3), (mid + cs * 0.7, t0 - cs * 0.62),
                           (mid + cs * 0.6, t0 - S * 0.08)]])
    P.paint(lay, "#06060a", P.dilate(crown, S * 0.03))
    P.paint(lay, _fill(crown, [(0, P.shade(accent, 1.6)), (1, accent)]), crown)
    _sparkle(lay, right - S * 0.4, t0 + S * 0.05, S * 0.35)
    return lay


STYLES = dict(chrome_neon=chrome_neon, gold_serif=gold_serif, steel_flare=steel_flare, candy_gems=candy_gems,
              cartoon_arch=cartoon_arch, sports_block=sports_block, horror_drip=horror_drip, stencil_plate=stencil_plate,
              fire_brush=fire_brush, arcade_pixel=arcade_pixel, retro_flat=retro_flat, modern_edge=modern_edge)


def logo(spec):
    """A logo from its games.toml dict, as a trimmed premultiplied RGBA layer."""
    opts = {k: v for k, v in spec.items() if k not in ("style", "title", "subtitle", "badge", "place")}
    if "colours" in opts and isinstance(opts["colours"], list):
        opts["colours"] = tuple(opts["colours"])
    lay = STYLES[spec["style"]](spec["title"], spec.get("subtitle"), **opts)
    lay = P.trim(lay, 4)
    if spec.get("badge"):
        lay = P.trim(_badge(lay, spec["badge"]), 4)
    return lay
