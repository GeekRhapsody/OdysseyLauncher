"""Painting helpers for the made-up games' logos and packaging: float RGB canvases (numpy, sRGB 0..1), masks,
gradients, shapes from SVG-style paths, blur, premultiplied RGBA layers and text."""

import math
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

FONTS = Path("C:/Windows/Fonts")


# Colour ------------------------------------------------------------------------------------------------------------

def rgb(colour):
    """'#RRGGBB', or a tuple of 0..255 ints or 0..1 floats, as a float32 array of three."""
    if isinstance(colour, str):
        c = colour.lstrip("#")
        return np.array([int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)
    c = np.asarray(colour, dtype=np.float32)
    return c / 255 if c.max() > 1.0 else c


def shade(colour, k):
    """Darker (k < 1) or lighter towards white (k > 1)."""
    c = rgb(colour)
    return c * k if k <= 1 else c + (1 - c) * (k - 1)


def ramp(t, stops):
    """The colour at t (any shape) along stops [(position, colour), ...]: t.shape + (3,)."""
    pos = np.array([p for p, _ in stops], dtype=np.float32)
    cols = np.stack([rgb(c) for _, c in stops])
    t = np.asarray(t, dtype=np.float32)
    return np.stack([np.interp(t, pos, cols[:, i]) for i in range(3)], axis=-1).astype(np.float32)


# Canvases and coordinates ------------------------------------------------------------------------------------------

def canvas(w, h, colour="#000000"):
    return np.broadcast_to(rgb(colour), (h, w, 3)).astype(np.float32).copy()


@lru_cache(maxsize=16)
def _grid(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx + 0.5, yy + 0.5


def coords(w, h):
    """Pixel-centre x and y arrays."""
    return _grid(w, h)


def linear(w, h, p0, p1, stops):
    """A gradient from p0 to p1 (pixels), clamped beyond them."""
    xx, yy = coords(w, h)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    t = ((xx - p0[0]) * dx + (yy - p0[1]) * dy) / max(dx * dx + dy * dy, 1e-6)
    return ramp(np.clip(t, 0, 1), stops)


def vertical(w, h, stops, top=0.0, bottom=None):
    return linear(w, h, (0, top), (0, h if bottom is None else bottom), stops)


def radial_t(w, h, centre, radius, squash=1.0):
    xx, yy = coords(w, h)
    return np.sqrt((xx - centre[0]) ** 2 + ((yy - centre[1]) / squash) ** 2) / radius


# Shapes ------------------------------------------------------------------------------------------------------------

_TOKEN = re.compile(r"[MmLlHhVvCcSsQqZz]|-?\d*\.?\d+(?:e-?\d+)?")


def path(d, steps=20):
    """An SVG path (M L H V C S Q Z, absolute or relative) as polygons: lists of (x, y)."""
    tokens = _TOKEN.findall(d)
    polys, cur = [], []
    x = y = 0.0
    sx = sy = 0.0
    last_ctrl = None
    cmd = None
    i = 0

    def num():
        nonlocal i
        v = float(tokens[i])
        i += 1
        return v

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if cur:
                    polys.append(cur)
                cur = []
                x, y = sx, sy
                continue
        rel = cmd.islower()
        c = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if c == "M":
            if cur:
                polys.append(cur)
            x, y = ox + num(), oy + num()
            sx, sy = x, y
            cur = [(x, y)]
            cmd = "l" if rel else "L"
            last_ctrl = None
        elif c == "L":
            x, y = ox + num(), oy + num()
            cur.append((x, y))
            last_ctrl = None
        elif c == "H":
            x = ox + num()
            cur.append((x, y))
            last_ctrl = None
        elif c == "V":
            y = (y if rel else 0.0) + num()
            cur.append((x, y))
            last_ctrl = None
        elif c in "CS":
            if c == "C":
                x1, y1 = ox + num(), oy + num()
            else:
                x1, y1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            x2, y2 = ox + num(), oy + num()
            x3, y3 = ox + num(), oy + num()
            for k in range(1, steps + 1):
                t = k / steps
                u = 1 - t
                cur.append((u ** 3 * x + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3 * x3,
                            u ** 3 * y + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t ** 3 * y3))
            last_ctrl = (x2, y2)
            x, y = x3, y3
        elif c == "Q":
            x1, y1 = ox + num(), oy + num()
            x2, y2 = ox + num(), oy + num()
            for k in range(1, steps + 1):
                t = k / steps
                u = 1 - t
                cur.append((u * u * x + 2 * u * t * x1 + t * t * x2, u * u * y + 2 * u * t * y1 + t * t * y2))
            x, y = x2, y2
            last_ctrl = None
    if cur:
        polys.append(cur)
    return polys


def xform(polys, scale=1.0, offset=(0.0, 0.0), rotate=0.0, mirror=False):
    """Scale (a number or (sx, sy)), mirror in x, rotate (degrees, about the origin), then move."""
    sx, sy = (scale, scale) if np.isscalar(scale) else scale
    c, s = math.cos(math.radians(rotate)), math.sin(math.radians(rotate))
    out = []
    for poly in polys:
        pts = []
        for px, py in poly:
            px, py = (-px if mirror else px) * sx, py * sy
            pts.append((px * c - py * s + offset[0], px * s + py * c + offset[1]))
        out.append(pts)
    return out


def _raster(w, h, bbox, ss, draw_fn):
    """Draws only inside bbox (pixels, clipped to the canvas) at ss times the size, then box-filters it down."""
    x0, y0 = max(int(math.floor(bbox[0])) - 1, 0), max(int(math.floor(bbox[1])) - 1, 0)
    x1, y1 = min(int(math.ceil(bbox[2])) + 1, w), min(int(math.ceil(bbox[3])) + 1, h)
    out = np.zeros((h, w), np.float32)
    if x0 >= x1 or y0 >= y1:
        return out
    img = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    draw_fn(ImageDraw.Draw(img), lambda px, py: ((px - x0) * ss, (py - y0) * ss))
    out[y0:y1, x0:x1] = np.asarray(img.resize((x1 - x0, y1 - y0), Image.BOX), dtype=np.float32) / 255
    return out


def mask(w, h, polys, ss=4):
    """Polygons (pixels) filled, anti-aliased by supersampling: a float mask."""
    pts = [p for poly in polys for p in poly]
    if not pts:
        return np.zeros((h, w), np.float32)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]

    def draw_fn(draw, to):
        for poly in polys:
            if len(poly) >= 3:
                draw.polygon([to(px, py) for px, py in poly], fill=255)

    return _raster(w, h, (min(xs), min(ys), max(xs), max(ys)), ss, draw_fn)


def ellipse(w, h, centre, radius, ss=4):
    rx, ry = (radius, radius) if np.isscalar(radius) else radius
    box = (centre[0] - rx, centre[1] - ry, centre[0] + rx, centre[1] + ry)

    def draw_fn(draw, to):
        draw.ellipse([*to(box[0], box[1]), *to(box[2], box[3])], fill=255)

    return _raster(w, h, box, ss, draw_fn)


def disc(w, h, centre, radius, feather=1.0):
    """A soft-edged disc, computed directly (no supersampling)."""
    return np.clip((radius - radial_t(w, h, centre, 1.0)) / feather + 0.5, 0, 1)


def lines(w, h, segments, width, ss=4):
    """Thick polylines: segments is a list of point lists."""
    pts = [p for seg in segments for p in seg]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]

    def draw_fn(draw, to):
        for seg in segments:
            draw.line([to(px, py) for px, py in seg], fill=255, width=max(1, int(width * ss)), joint="curve")

    return _raster(w, h, (min(xs) - width, min(ys) - width, max(xs) + width, max(ys) + width), ss, draw_fn)


# Filters -----------------------------------------------------------------------------------------------------------

def resize(a, w, h, resample=Image.BILINEAR):
    """A float array (2D or HxWxC) resized."""
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((w, h), resample), dtype=np.float32)
    return np.stack([resize(a[..., c], w, h, resample) for c in range(a.shape[2])], axis=-1)


def blur(a, sigma):
    """Gaussian blur; large radii are blurred at a lower resolution."""
    if sigma <= 0:
        return a
    h, w = a.shape[:2]
    if sigma > 8:
        f = sigma / 4
        sw, sh = max(int(w / f), 2), max(int(h / f), 2)
        small = resize(a, sw, sh, Image.BOX)
        small = ndimage.gaussian_filter(small, (4, 4) + ((0,) if a.ndim == 3 else ()))
        return resize(small, w, h, Image.BICUBIC)
    return ndimage.gaussian_filter(a, (sigma, sigma) + ((0,) if a.ndim == 3 else ()))


def dilate(m, r):
    """Grow a mask by r pixels, smoothly (distance transform)."""
    if r <= 0:
        return m
    d = ndimage.distance_transform_edt(m < 0.5)
    return np.maximum(m, np.clip(r + 0.5 - d, 0, 1))


def erode(m, r):
    return 1 - dilate(1 - m, r)


def shift(m, dx, dy):
    return ndimage.shift(m, (dy, dx) + ((0,) if m.ndim == 3 else ()), order=1, mode="constant", cval=0.0)


def star4(cx, cy, r, thin):
    """A four-pointed glint: two thin diamonds crossed, as polygons."""
    return [[(cx - r, cy), (cx, cy - thin), (cx + r, cy), (cx, cy + thin)],
            [(cx, cy - r), (cx + thin, cy), (cx, cy + r), (cx - thin, cy)]]


# Compositing (in place, on float RGB canvases) ---------------------------------------------------------------------

def _col(colour, a):
    if isinstance(colour, np.ndarray) and colour.ndim == 3:
        return colour
    return rgb(colour)[None, None, :] * np.ones_like(a[..., None])


def over(dst, colour, alpha, opacity=1.0):
    a = (np.clip(alpha, 0, 1) * opacity)[..., None]
    dst *= 1 - a
    dst += a * _col(colour, alpha)
    return dst


# RGBA layers (premultiplied) ---------------------------------------------------------------------------------------

def layer(w, h):
    return np.zeros((h, w, 4), np.float32)


def paint(lay, colour, alpha, opacity=1.0):
    """Paint colour (or an HxWx3 array) through alpha onto a premultiplied RGBA layer."""
    a = np.clip(alpha, 0, 1) * opacity
    lay[..., :3] = lay[..., :3] * (1 - a[..., None]) + _col(colour, a) * a[..., None]
    lay[..., 3] = lay[..., 3] * (1 - a) + a
    return lay


def composite(dst, lay, x=0, y=0, opacity=1.0):
    """A premultiplied RGBA layer over an RGB canvas (or another premultiplied layer) at (x, y), clipped to it."""
    h, w = lay.shape[:2]
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return dst
    src = lay[y0 - y:y1 - y, x0 - x:x1 - x] * opacity
    if dst.shape[2] == 4:
        dst[y0:y1, x0:x1] = src + dst[y0:y1, x0:x1] * (1 - src[..., 3:4])
    else:
        dst[y0:y1, x0:x1] = src[..., :3] + dst[y0:y1, x0:x1] * (1 - src[..., 3:4])
    return dst


def scale_layer(lay, w, h):
    return resize(lay, w, h, Image.LANCZOS).clip(0, None)


def rotate_layer(lay, degrees):
    """Rotated about its centre, the canvas grown to fit."""
    return np.stack([ndimage.rotate(lay[..., c], degrees, reshape=True, order=1) for c in range(4)], axis=-1)


def trim(lay, pad=0):
    a = lay[..., 3]
    ys, xs = np.nonzero(a > 1 / 255)
    if len(xs) == 0:
        return lay
    return lay[max(ys.min() - pad, 0):ys.max() + 1 + pad, max(xs.min() - pad, 0):xs.max() + 1 + pad]


# Text --------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=64)
def font(name, size):
    return ImageFont.truetype(str(FONTS / name), int(size))


def text_mask(text, name, size, tracking=0.0, italic=0.0, pad=None, stretch=1.0):
    """Text as a float mask with padding round it, letters spaced by tracking (a fraction of the size), sheared by
    italic (x per y) and stretched horizontally. Returns (mask, baseline y)."""
    f = font(name, size)
    pad = int(size * 0.6) if pad is None else pad
    ascent, descent = f.getmetrics()
    widths = [f.getlength(ch) for ch in text]
    total = sum(widths) + tracking * size * (len(text) - 1)
    w = int(total + 2 * pad + abs(italic) * (ascent + descent)) + 2
    h = int(ascent + descent + 2 * pad)
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    x = pad
    for ch, cw in zip(text, widths):
        draw.text((x, pad), ch, font=f, fill=255)
        x += cw + tracking * size
    m = np.asarray(img, dtype=np.float32) / 255
    baseline = pad + ascent
    if italic:
        # x' = x - italic * (y - baseline): shear about the baseline (positive leans right)
        m = ndimage.affine_transform(m, [[1, 0], [italic, 1]], offset=(0, -italic * baseline), order=1)
    if stretch != 1.0:
        m = resize(m, int(m.shape[1] * stretch), m.shape[0], Image.LANCZOS).clip(0, 1)
    return m, baseline


def tight(m, pad=0):
    ys, xs = np.nonzero(m > 1 / 255)
    if len(xs) == 0:
        return m, (0, 0)
    y0, x0 = max(ys.min() - pad, 0), max(xs.min() - pad, 0)
    return m[y0:ys.max() + 1 + pad, x0:xs.max() + 1 + pad], (x0, y0)


def draw_text(dst, text, name, size, xy, colour, anchor="la", opacity=1.0, shadow=None, stroke=0, stroke_colour=None):
    """Plain text straight onto an RGB canvas (Pillow anchors: 'la' left-ascender, 'mm' middle...)."""
    h, w = dst.shape[:2]
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).text(xy, text, font=font(name, size), fill=255, anchor=anchor, stroke_width=stroke)
    m = np.asarray(img, dtype=np.float32) / 255
    if stroke and stroke_colour is not None:
        inner = Image.new("L", (w, h), 0)
        ImageDraw.Draw(inner).text(xy, text, font=font(name, size), fill=255, anchor=anchor)
        mi = np.asarray(inner, dtype=np.float32) / 255
        if shadow:
            over(dst, shadow[0], shift(m, shadow[1], shadow[2]), opacity * 0.6)
        over(dst, stroke_colour, m, opacity)
        over(dst, colour, mi, opacity)
        return dst
    if shadow:
        over(dst, shadow[0], shift(m, shadow[1], shadow[2]), opacity * 0.6)
    return over(dst, colour, m, opacity)


def wrap(text, name, size, width):
    """Lines of text that fit width pixels."""
    f = font(name, size)
    out, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if f.getlength(trial) <= width or not line:
            line = trial
        else:
            out.append(line)
            line = word
    if line:
        out.append(line)
    return out


# Output ------------------------------------------------------------------------------------------------------------

def to_image(a, seed=0):
    """An RGB canvas as an 8-bit image, dithered so gradients don't band."""
    rng = np.random.default_rng(seed)
    a = a + (rng.random(a.shape[:2], dtype=np.float32)[..., None] - 0.5) / 255
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


def layer_image(lay):
    """A premultiplied RGBA layer as an 8-bit RGBA image."""
    a = np.clip(lay[..., 3:4], 0, 1)
    c = np.where(a > 1e-6, lay[..., :3] / np.maximum(a, 1e-6), 0)
    out = np.concatenate([np.clip(c, 0, 1), a], axis=-1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA")


def from_image(img):
    """An 8-bit image as a float RGB canvas, or a premultiplied layer if it has alpha."""
    if img.mode == "RGBA":
        a = np.asarray(img, dtype=np.float32) / 255
        a[..., :3] *= a[..., 3:4]
        return a
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255
