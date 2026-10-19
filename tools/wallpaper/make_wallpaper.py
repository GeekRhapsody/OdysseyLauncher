"""Draws the gaming wallpapers in wallpapers/: a dark grey background packed with black gaming icons.

Every icon is drawn here from primitives (no logos or traced artwork): 61 designs, from controllers and hardware to
pixel art and game items. Each icon is a mask in a 100x100 box: 'w' layers add shape, 'b' layers cut it away, in order.

The layout is made at 1920x1080: each icon's silhouette is rendered once, then the icons are packed biggest first on an
occupancy grid (an FFT convolution finds every free spot), at random sizes and tilts, with no design repeated near
itself. The same layout is then rendered at 1080p, 1440p and 4K (at twice the size, downsampled), with a radial vignette
and a light grain. Seeded: the same seed gives the same wallpapers on every run (seed 7 made the ones in wallpapers/).

Needs numpy, scipy and Pillow, and ImageMagick (magick) with its librsvg delegate. Run from the repo root:

    python tools/wallpaper/make_wallpaper.py [--seed=<n>] [--out=<folder>]

--out defaults to wallpapers/. The SVG and intermediate renders go to artifacts/wallpaper/.
"""
import argparse
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy.signal import fftconvolve

REPO = Path(__file__).resolve().parents[2]
W, H = 1920, 1080
# The layout is made at 1920x1080 and rendered at each of these sizes.
OUTPUTS = [(1920, 1080, "1080p"), (2560, 1440, "1440p"), (3840, 2160, "4k")]
WORK = REPO / "artifacts" / "wallpaper"
SVG = WORK / "wallpaper.svg"
SEED = 7
FONT = "font-family=\"Arial Black, Arial, sans-serif\" font-weight=\"900\""


def S(d, w, cap="round"):
    return (f'<path d="{d}" fill="none" stroke="currentColor" stroke-width="{w}" '
            f'stroke-linecap="{cap}" stroke-linejoin="round"/>')


def P(d):
    return f'<path d="{d}"/>'


def R(x, y, w, h, rx=0, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" {extra}/>'


def C(cx, cy, r):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'


def E(cx, cy, rx, ry):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/>'


def T(x, y, s, txt):
    return f'<text x="{x}" y="{y}" font-size="{s}" {FONT} text-anchor="middle">{txt}</text>'


def cross(cx, cy, span, arm, rx=1.5):
    h = span / 2
    a = arm / 2
    return R(cx - a, cy - h, arm, span, rx) + R(cx - h, cy - a, span, arm, rx)


def star_pts(cx, cy, ro, ri, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = math.radians(rot + i * 180 / n)
        pts.append(f"{cx + r * math.cos(a):.2f},{cy + r * math.sin(a):.2f}")
    return f'<polygon points="{" ".join(pts)}"/>'


def pixels(rows, box=88):
    """Pixel art as one path (no seams), centred in the 100 box."""
    n_r, n_c = len(rows), max(len(r) for r in rows)
    c = box / max(n_r, n_c)
    ox, oy = 50 - n_c * c / 2, 50 - n_r * c / 2
    d = []
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            if row[i] == "#":
                k = i
                while k < len(row) and row[k] == "#":
                    k += 1
                d.append(f"M{ox + i * c:.2f} {oy + j * c:.2f}h{(k - i) * c:.2f}v{c:.2f}h{-(k - i) * c:.2f}z")
                i = k
            else:
                i += 1
    return f'<path d="{"".join(d)}"/>'


def tetromino(cells):
    cs, gap = 25, 2.5
    cols = max(c for c, _ in cells) + 1
    rows = max(r for _, r in cells) + 1
    ox, oy = 50 - cols * cs / 2, 50 - rows * cs / 2
    w = "".join(R(ox + c * cs + gap / 2, oy + r * cs + gap / 2, cs - gap, cs - gap, 2) for c, r in cells)
    b = "".join(S(f"M{ox + c * cs + 7} {oy + r * cs + cs - 7} L{ox + c * cs + 7} {oy + r * cs + 7} "
                  f"L{ox + c * cs + cs - 7} {oy + r * cs + 7}", 2.5) for c, r in cells)
    return [("w", w), ("b", b)]


SIZE = {'sym_triangle': 0.72, 'sym_circle': 0.72, 'sym_cross': 0.68, 'sym_square': 0.68,
        'wasd': 1.12, 'pad8bit': 1.08, 'healthbar': 1.08, 'power': 0.85, 'coin': 0.85, 'disc': 0.9,
        'qblock': 0.85, 'brick': 0.85, 'medkit': 0.9, 'floppy': 0.9, 'star': 0.9}

# name -> (layers, collision radius in box units, max rotation in degrees)
ICONS = {}


def icon(name, rad=48, rot=30):
    def deco(fn):
        ICONS[name] = (fn(), rad, rot)
        return fn
    return deco


@icon("gamepad")
def _():
    body = P("M30 28 C20 28 14 32 11 42 L5 66 C3 76 8 82 15 82 C21 82 25 78 29 72 L33 66 L67 66 "
             "L71 72 C75 78 79 82 85 82 C92 82 97 76 95 66 L89 42 C86 32 80 28 70 28 Z")
    cuts = cross(27, 45, 19, 6.5) + C(73, 37.5, 3.6) + C(73, 52.5, 3.6) + C(65.5, 45, 3.6) + C(80.5, 45, 3.6)
    cuts += C(40, 57, 6.5) + C(60, 57, 6.5) + R(45, 37, 4, 3, 1.5) + R(51, 37, 4, 3, 1.5)
    return [("w", body), ("b", cuts), ("w", C(40, 57, 3.8) + C(60, 57, 3.8))]


@icon("pad8bit", rad=50)
def _():
    cuts = cross(24, 50, 22, 7) + R(39, 53, 9, 4, 2) + R(51, 53, 9, 4, 2) + C(70, 55, 5.5) + C(83, 55, 5.5)
    cuts += R(39, 37, 22, 3) + R(39, 43, 22, 3)
    return [("w", R(5, 30, 90, 40, 4)), ("b", cuts)]


@icon("pad16bit", rad=50)
def _():
    w = C(26, 50, 22) + C(74, 50, 22) + R(26, 28, 48, 44)
    cuts = cross(26, 50, 23, 7.5) + C(74, 38.5, 5) + C(74, 61.5, 5) + C(62.5, 50, 5) + C(85.5, 50, 5)
    cuts += R(40, 54, 8, 3.5, 1.75, 'transform="rotate(-30 44 56)"') + R(51, 54, 8, 3.5, 1.75, 'transform="rotate(-30 55 56)"')
    return [("w", w), ("b", cuts)]


@icon("pad64")
def _():
    body = P("M8 30 Q8 20 18 20 L82 20 Q92 20 92 30 L92 44 Q90 54 84 58 L80 84 Q78 90 72 88 L66 62 "
             "L58 60 L56 86 Q50 92 44 86 L42 60 L34 62 L28 88 Q22 90 20 84 L16 58 Q10 54 8 44 Z")
    cuts = cross(22, 37, 15, 5) + C(50, 44, 6) + C(74, 31, 3.4) + C(80, 38, 3.4) + C(74, 45, 3.4) + C(68, 38, 3.4)
    return [("w", body), ("b", cuts), ("w", C(50, 44, 3.5))]


@icon("joystick")
def _():
    w = P("M14 74 L86 74 L80 92 L20 92 Z") + R(12, 64, 76, 12, 3) + R(46, 30, 8, 38) + C(50, 24, 17)
    w += R(66, 56, 14, 8, 3)
    return [("w", w), ("b", C(43, 17, 4.5) + R(14, 74, 72, 2.5))]


@icon("handheld")
def _():
    body = P("M22 4 L78 4 Q82 4 82 8 L82 80 Q82 96 66 96 L22 96 Q18 96 18 92 L18 8 Q18 4 22 4 Z")
    cuts = R(25, 11, 50, 40, 3) + cross(33, 68, 17, 5.5) + C(68, 63, 4.6) + C(58.5, 71, 4.6)
    cuts += R(38, 85, 8, 3, 1.5) + R(50, 85, 8, 3, 1.5)
    cuts += S("M64 90 L74 80", 2) + S("M69 92 L77 84", 2) + S("M60 88 L70 78", 2)
    return [("w", body), ("b", cuts), ("w", R(31, 16, 38, 30, 1)), ("b", C(28, 30, 1.6))]


@icon("arcade")
def _():
    body = P("M24 4 L76 4 L76 14 L72 14 L72 46 L84 58 L84 64 L76 64 L76 96 L24 96 L24 64 L16 64 "
             "L16 58 L28 46 L28 14 L24 14 Z")
    cuts = R(30, 7, 40, 5, 1) + R(32, 17, 36, 26, 2) + C(34, 56, 2.6) + C(51, 56, 2.4) + C(59, 56, 2.4)
    cuts += C(67, 56, 2.4) + R(43, 74, 4, 9, 1) + R(53, 74, 4, 9, 1) + R(16, 61, 68, 1.8)
    return [("w", body), ("b", cuts)]


@icon("cartridge")
def _():
    body = P("M18 4 L82 4 Q86 4 86 8 L86 86 L80 86 L80 96 L20 96 L20 86 L14 86 L14 8 Q14 4 18 4 Z")
    cuts = R(24, 22, 52, 44, 2) + R(28, 9, 44, 2.2) + R(28, 14, 44, 2.2)
    cuts += "".join(R(25 + i * 7, 88, 3.5, 8) for i in range(7))
    return [("w", body), ("b", cuts), ("w", R(30, 28, 40, 7, 1) + star_pts(50, 50, 9, 4))]


@icon("floppy", rad=56)
def _():
    body = P("M14 6 L78 6 L94 22 L94 90 Q94 94 90 94 L10 94 Q6 94 6 90 L6 10 Q6 6 10 6 Z")
    return [("w", body), ("b", R(26, 6, 46, 30)), ("w", R(29, 6, 40, 27)), ("b", R(56, 11, 8, 18, 1)),
            ("b", R(18, 50, 64, 40, 3)), ("w", R(24, 60, 52, 3) + R(24, 70, 52, 3) + R(24, 80, 36, 3))]


@icon("disc")
def _():
    cuts = C(50, 50, 14) + S("M50 14 A36 36 0 0 1 84 38", 3.5) + S("M50 22 A28 28 0 0 1 76 40", 2.5)
    return [("w", C(50, 50, 45)), ("b", cuts), ("w", C(50, 50, 10.5)), ("b", C(50, 50, 5))]


@icon("heart", rot=12)
def _():
    rows = ["..###.###..", ".#########.", "###########", "###########", "###########",
            ".#########.", "..#######..", "...#####...", "....###....", ".....#....."]
    hl = ["...........", "..#........", ".##........", ".#.........", "...........",
          "...........", "...........", "...........", "...........", "..........."]
    return [("w", pixels(rows)), ("b", pixels(hl))]


@icon("alien", rot=12)
def _():
    rows = ["....####....", "..########..", ".##########.", "###..##..###", "############",
            "..###..###..", ".##.####.##.", "##........##"]
    return [("w", pixels(rows))]


@icon("mushroom", rot=12)
def _():
    rows = ["....####....", "..########..", ".##########.", ".##########.", "############",
            "############", "############", ".##########.", "...######...", "...######...",
            "...######...", "....####...."]
    spots = ["............", ".....##.....", "....####....", ".#..####..#.", "##...##...##",
             "##........##", "............", "............", "............", "....#..#....",
             "....#..#....", "............"]
    return [("w", pixels(rows)), ("b", pixels(spots))]


@icon("coin")
def _():
    return [("w", C(50, 50, 42)), ("b", S("M50 15 A35 35 0 1 1 49.9 15", 3) + R(45, 28, 10, 44, 4))]


@icon("star")
def _():
    s = star_pts(50, 54, 47, 20)
    return [("w", s + s.replace("<polygon", '<polygon fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"'))]


@icon("sword")
def _():
    w = P("M50 3 L57 13 L57 64 L43 64 L43 13 Z") + R(27, 63, 46, 8, 3) + R(46, 70, 8, 18) + C(50, 92, 5.5)
    return [("w", w), ("b", R(49, 15, 2, 44, 1) + R(46, 74, 8, 1.6) + R(46, 79, 8, 1.6) + R(46, 84, 8, 1.6))]


@icon("shield")
def _():
    body = P("M50 4 L88 15 L88 46 Q88 78 50 96 Q12 78 12 46 L12 15 Z")
    inner = S("M50 12 L81 21 L81 46 Q81 72 50 88 Q19 72 19 46 L19 21 Z", 3)
    return [("w", body), ("b", inner + R(45, 22, 10, 58) + R(24, 38, 52, 10))]


@icon("potion")
def _():
    w = R(41, 14, 18, 24) + C(50, 65, 31) + R(39, 4, 22, 11, 2) + R(37, 14, 26, 5, 2)
    cuts = S("M22 60 Q36 53 50 60 Q64 67 78 60", 3) + C(40, 74, 4.5) + C(59, 80, 3.2) + C(53, 69, 2.2)
    cuts += S("M30 46 A26 26 0 0 1 40 38", 3)
    return [("w", w), ("b", cuts)]


@icon("key")
def _():
    w = C(26, 50, 21) + R(44, 45, 50, 10, 2) + R(74, 54, 7, 15, 1) + R(85, 54, 7, 10, 1)
    return [("w", w), ("b", C(26, 50, 9))]


@icon("skull")
def _():
    body = P("M50 6 C26 6 12 23 12 44 C12 56 18 64 27 69 L27 84 Q27 92 34 92 L66 92 Q73 92 73 84 "
             "L73 69 C82 64 88 56 88 44 C88 23 74 6 50 6 Z")
    cuts = E(35, 46, 10, 11.5) + E(65, 46, 10, 11.5) + P("M50 58 L44 69 L56 69 Z")
    cuts += R(40, 78, 3.5, 14) + R(48.25, 78, 3.5, 14) + R(56.5, 78, 3.5, 14)
    return [("w", body), ("b", cuts)]


@icon("crown")
def _():
    w = P("M10 34 L28 58 L50 22 L72 58 L90 34 L82 78 L18 78 Z") + R(18, 81, 64, 11, 2)
    w += C(10, 30, 6.5) + C(50, 17, 6.5) + C(90, 30, 6.5)
    return [("w", w), ("b", C(50, 63, 5.5) + C(32, 67, 3.8) + C(68, 67, 3.8))]


@icon("gem")
def _():
    body = P("M28 12 L72 12 L94 38 L50 92 L6 38 Z")
    cuts = S("M7 38 L93 38", 2.5) + S("M28 12 L38 38 L50 90", 2.5) + S("M72 12 L62 38 L50 90", 2.5)
    cuts += S("M38 38 L50 12 L62 38", 2.5)
    return [("w", body), ("b", cuts)]


@icon("bomb")
def _():
    w = C(44, 60, 33) + R(52, 20, 17, 15, 2, 'transform="rotate(40 60 27)"')
    w += S("M64 21 Q70 9 82 11", 4) + star_pts(87, 10, 9, 4, n=6)
    return [("w", w), ("b", S("M23 54 A22 22 0 0 1 36 37", 5))]


@icon("ghost")
def _():
    body = P("M14 92 L14 46 C14 23 30 8 50 8 C70 8 86 23 86 46 L86 92 L74 81 L62 92 L50 81 L38 92 L26 81 Z")
    return [("w", body), ("b", E(37, 43, 9, 11) + E(63, 43, 9, 11)), ("w", C(40, 47, 4.5) + C(66, 47, 4.5))]


@icon("chomper")
def _():
    return [("w", P("M50 50 L88.1 28 A44 44 0 1 0 88.1 72 Z")), ("b", C(52, 25, 5.5))]


@icon("tet_t", rot=45)
def _():
    return tetromino([(0, 0), (1, 0), (2, 0), (1, 1)])


@icon("tet_s", rot=45)
def _():
    return tetromino([(1, 0), (2, 0), (0, 1), (1, 1)])


@icon("tet_l", rot=45)
def _():
    return tetromino([(0, 0), (0, 1), (0, 2), (1, 2)])


@icon("sym_triangle", rad=44, rot=20)
def _():
    return [("w", S("M50 12 L90 82 L10 82 Z", 9))]


@icon("sym_circle", rad=44)
def _():
    return [("w", S("M50 14 A36 36 0 1 1 49.9 14", 9))]


@icon("sym_cross", rad=44, rot=15)
def _():
    return [("w", S("M18 18 L82 82", 10) + S("M82 18 L18 82", 10))]


@icon("sym_square", rad=52, rot=15)
def _():
    return [("w", S("M17 17 H83 V83 H17 Z", 9))]


@icon("face_buttons", rot=10)
def _():
    w = C(50, 17, 15.5) + C(17, 50, 15.5) + C(83, 50, 15.5) + C(50, 83, 15.5)
    cuts = S("M50 9 L57 21 L43 21 Z", 2.8) + S("M83 43 A7 7 0 1 1 82.9 43", 2.8)
    cuts += S("M44 77 L56 89", 2.8) + S("M56 77 L44 89", 2.8) + S("M11 44 H23 V56 H11 Z", 2.8)
    return [("w", w), ("b", cuts)]


@icon("dpad", rad=52)
def _():
    w = R(36, 6, 28, 88, 5) + R(6, 36, 88, 28, 5)
    cuts = C(50, 50, 8) + P("M50 13 L43 24 L57 24 Z") + P("M50 87 L43 76 L57 76 Z")
    cuts += P("M13 50 L24 43 L24 57 Z") + P("M87 50 L76 43 L76 57 Z")
    return [("w", w), ("b", cuts)]


@icon("ab_buttons", rot=15)
def _():
    g = 'transform="rotate(-25 50 50)"'
    return [("w", f'<g {g}>{R(2, 29, 96, 42, 21)}</g>'),
            ("b", f'<g {g}>{C(26, 50, 17)}{C(74, 50, 17)}</g>'),
            ("w", f'<g {g}>{C(26, 50, 13.5)}{C(74, 50, 13.5)}</g>'),
            ("b", f'<g {g}>{T(26, 58, 21, "B")}{T(74, 58, 21, "A")}</g>')]


@icon("healthbar", rot=20)
def _():
    w = cross(14, 50, 20, 7, 1) + R(30, 34, 66, 32, 6)
    return [("w", w), ("b", R(35, 39, 56, 22, 3)),
            ("w", R(38.5, 42, 10, 16, 1) + R(51, 42, 10, 16, 1) + R(63.5, 42, 10, 16, 1))]


@icon("crosshair")
def _():
    w = S("M50 16 A34 34 0 1 1 49.9 16", 6) + S("M50 4 L50 32", 6) + S("M50 68 L50 96", 6)
    w += S("M4 50 L32 50", 6) + S("M68 50 L96 50", 6) + C(50, 50, 5)
    return [("w", w)]


@icon("trophy")
def _():
    w = P("M26 8 L74 8 L74 34 C74 52 62 62 50 62 C38 62 26 52 26 34 Z")
    w += S("M27 17 L15 17 Q10 17 10 24 Q10 41 29 45", 6) + S("M73 17 L85 17 Q90 17 90 24 Q90 41 71 45", 6)
    w += R(45, 60, 10, 15) + R(31, 74, 38, 8, 2) + R(24, 83, 52, 11, 2)
    return [("w", w), ("b", star_pts(50, 33, 12, 5))]


@icon("d20")
def _():
    hexa = [(50, 4), (90, 27), (90, 73), (50, 96), (10, 73), (10, 27)]
    tri = [(50, 28), (74, 68), (26, 68)]
    pts = " ".join(f"{x},{y}" for x, y in hexa)
    lines = [(hexa[0], tri[0]), (hexa[5], tri[0]), (hexa[1], tri[0]), (hexa[5], tri[2]), (hexa[4], tri[2]),
             (hexa[3], tri[2]), (hexa[3], tri[1]), (hexa[1], tri[1]), (hexa[2], tri[1]),
             (tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])]
    cuts = "".join(S(f"M{a[0]} {a[1]} L{b[0]} {b[1]}", 2.5) for a, b in lines)
    return [("w", f'<polygon points="{pts}"/>'), ("b", cuts + T(50, 61, 15, "20"))]


@icon("wasd", rad=54, rot=15)
def _():
    keys = [(50, 27, "W"), (22, 63, "A"), (50, 63, "S"), (78, 63, "D")]
    w = "".join(R(x - 13, y - 13, 26, 26, 4) for x, y, _ in keys)
    b = "".join(T(x, y + 6, 16, k) + R(x - 9, y - 9, 18, 18, 2.5, 'fill="none" stroke="currentColor" stroke-width="1.5"')
                for x, y, k in keys)
    return [("w", w), ("b", b)]


@icon("mouse")
def _():
    body = P("M50 4 C29 4 20 19 20 40 L20 66 C20 85 33 96 50 96 C67 96 80 85 80 66 L80 40 C80 19 71 4 50 4 Z")
    cuts = S("M50 6 L50 42", 3, cap="butt") + S("M20 42 L80 42", 3, cap="butt") + R(44.5, 15, 11, 20, 5.5)
    cuts += R(20, 50, 3, 12, 1)
    return [("w", body), ("b", cuts), ("w", R(47.5, 18, 5, 14, 2.5))]


@icon("headset")
def _():
    w = S("M17 58 L17 46 A33 33 0 0 1 83 46 L83 58", 8) + R(7, 50, 21, 34, 8) + R(72, 50, 21, 34, 8)
    w += S("M15 80 Q18 95 40 93", 4) + C(42, 93, 4.5)
    return [("w", w), ("b", R(22, 55, 3, 24, 1.5) + R(75, 55, 3, 24, 1.5))]


@icon("vr")
def _():
    w = R(8, 30, 84, 42, 12) + R(1, 43, 9, 16, 3) + R(90, 43, 9, 16, 3)
    cuts = P("M38 72 Q50 56 62 72 Z") + R(14, 36, 72, 28, 8, 'fill="none" stroke="currentColor" stroke-width="2.5"')
    return [("w", w), ("b", cuts)]


@icon("cursor", rot=25)
def _():
    w = P("M22 4 L22 82 L40 66 L52 92 L64 86 L52 61 L76 61 Z")
    return [("w", w), ("b", S("M28 18 L28 66 L40 55 L52 80", 2.5))]


@icon("power")
def _():
    return [("w", S("M30.5 26.1 A34 34 0 1 0 69.5 26.1", 9) + S("M50 8 L50 48", 9))]


@icon("hourglass")
def _():
    w = R(18, 4, 64, 11, 3) + R(18, 85, 64, 11, 3)
    w += P("M24 15 L76 15 Q76 38 56 50 Q76 62 76 85 L24 85 Q24 62 44 50 Q24 38 24 15 Z")
    inner = P("M31 19 L69 19 Q69 38 53 50 Q69 62 69 81 L31 81 Q31 62 47 50 Q31 38 31 19 Z")
    sand = P("M36 31 L64 31 Q60 40 50 46 Q40 40 36 31 Z") + P("M31 81 L69 81 Q66 66 50 62 Q34 66 31 81 Z")
    return [("w", w), ("b", inner), ("w", sand + R(49, 45, 2, 18))]


@icon("oneup", rot=20)
def _():
    return [("w", R(5, 25, 90, 50, 9)), ("b", T(50, 62, 32, "1UP"))]


@icon("axe")
def _():
    w = R(45, 8, 9, 88, 3) + P("M53 12 C77 8 92 20 94 46 C82 41 66 43 53 50 Z") + P("M46 20 L28 27 L46 34 Z")
    return [("w", w), ("b", S("M60 17 C76 15 86 23 88 37", 2.5))]


@icon("bow")
def _():
    w = S("M30 5 Q88 50 30 95", 7) + S("M30 5 L30 95", 2) + S("M12 50 L82 50", 4)
    w += P("M96 50 L80 41 L80 59 Z") + P("M6 41 L18 50 L6 59 L10 50 Z") + P("M13 41 L25 50 L13 59 L17 50 Z")
    return [("w", w)]


@icon("ship", rot=12)
def _():
    rows = ["......##......", ".....####.....", ".....####.....", "....######....", "....##..##....",
            ".#..######..#.", ".#.########.#.", "##############", "##############", "###.######.###",
            "##...####...##", "#.....##.....#"]
    return [("w", pixels(rows))]


@icon("lightning")
def _():
    return [("w", P("M60 3 L18 56 L45 56 L36 97 L82 39 L54 39 L68 3 Z"))]


@icon("chest")
def _():
    w = P("M8 40 L8 30 Q8 11 50 11 Q92 11 92 30 L92 40 Z") + R(8, 44, 84, 48, 3)
    cuts = R(41, 35, 18, 21, 3) + R(22, 13, 4, 79) + R(74, 13, 4, 79)
    return [("w", w), ("b", cuts), ("w", R(44, 38, 12, 15, 2)), ("b", C(50, 43, 2.6) + R(49, 43, 2, 7))]


@icon("cherry")
def _():
    w = C(29, 72, 19) + C(69, 76, 19) + S("M29 56 Q38 30 62 12", 4) + S("M69 60 Q66 34 62 12", 4)
    w += P("M62 12 Q78 2 92 16 Q76 25 62 12 Z")
    return [("w", w), ("b", C(22, 65, 4.5) + C(62, 69, 4.5))]


@icon("flag")
def _():
    sq = 76 / 6
    cuts = "".join(R(16 + c * sq, 10 + r * sq * 44 / (3 * sq), sq, 44 / 3)
                   for r in range(3) for c in range(6) if (r + c) % 2)
    return [("w", R(8, 4, 7, 92, 2) + R(16, 10, 76, 44)), ("b", cuts)]


@icon("wheel")
def _():
    w = S("M50 9 A41 41 0 1 1 49.9 9", 9)
    w += P("M10 44 Q50 34 90 44 L90 58 Q65 58 57 68 L57 92 L43 92 L43 68 Q35 58 10 58 Z")
    return [("w", w), ("b", C(50, 51, 6))]


@icon("medkit", rad=54)
def _():
    w = R(6, 22, 88, 68, 8) + S("M35 22 L35 11 L65 11 L65 22", 6, cap="butt")
    return [("w", w), ("b", R(44, 34, 12, 44) + R(28, 50, 44, 12))]


@icon("grenade")
def _():
    w = E(50, 61, 28, 33) + R(40, 18, 20, 13, 2) + P("M57 20 L77 23 L74 54 L66 47 Z")
    w += S("M34 11 A8 8 0 1 1 33.9 11", 4)
    cuts = S("M23 52 L77 52", 3) + S("M25 71 L75 71", 3) + S("M50 31 L50 93", 3)
    return [("w", w), ("b", cuts)]


@icon("ufo")
def _():
    w = P("M30 46 Q30 16 50 16 Q70 16 70 46 Z") + E(50, 52, 46, 14) + P("M38 64 L62 64 L80 96 L20 96 Z")
    cuts = C(23, 52, 3.5) + C(37, 56, 3.5) + C(50, 57.5, 3.5) + C(63, 56, 3.5) + C(77, 52, 3.5)
    cuts += S("M38 32 A14 14 0 0 1 46 23", 3) + R(10, 72, 80, 3) + R(10, 83, 80, 3)
    return [("w", w), ("b", cuts)]


@icon("crt", rad=52)
def _():
    w = R(6, 22, 88, 64, 8) + S("M50 22 L30 4", 3) + S("M50 22 L70 4", 3) + R(16, 85, 11, 9, 1) + R(73, 85, 11, 9, 1)
    cuts = R(13, 29, 59, 50, 9) + C(83, 39, 4.2) + C(83, 53, 4.2)
    cuts += R(78, 63, 10, 2) + R(78, 67.5, 10, 2) + R(78, 72, 10, 2)
    return [("w", w), ("b", cuts)]


@icon("qblock", rad=58, rot=15)
def _():
    cuts = C(16, 16, 3.5) + C(84, 16, 3.5) + C(16, 84, 3.5) + C(84, 84, 3.5) + T(50, 73, 62, "?")
    return [("w", R(6, 6, 88, 88, 7)), ("b", cuts)]


@icon("brick", rad=58, rot=15)
def _():
    cuts = "".join(R(6, y, 88, 3) for y in (27, 49, 71))
    for row, y in enumerate((6, 30, 52, 74)):
        xs = (36, 66) if row % 2 == 0 else (21, 51, 81)
        cuts += "".join(R(x, y, 3, 21 if row else 21) for x in xs)
    return [("w", R(6, 6, 88, 88, 3)), ("b", cuts)]


def build_defs():
    out = []
    for name, (layers, _, _) in ICONS.items():
        body = "".join(f'<g color="{"#fff" if k == "w" else "#000"}" fill="currentColor">{svg}</g>'
                       for k, svg in layers)
        out.append(f'<mask id="m_{name}" maskUnits="userSpaceOnUse" x="-10" y="-10" width="120" height="120">'
                   f'{body}</mask>')
    return "\n".join(out)


def silhouettes(defs):
    """Each icon's shape (120x120 box units at 2 px a unit), as a boolean array, for packing."""
    tmp = SVG.with_name("sil")
    tmp.mkdir(exist_ok=True)
    out = {}
    for name in ICONS:
        f = tmp / f"{name}.svg"
        f.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="-10 -10 120 120">'
                     f'<defs>{defs}</defs><rect x="-10" y="-10" width="120" height="120" fill="#000"/>'
                     f'<rect x="-10" y="-10" width="120" height="120" fill="#fff" mask="url(#m_{name})"/></svg>',
                     encoding="utf-8")
        png = f.with_suffix(".png")
        subprocess.run(["magick", str(f), "-colorspace", "gray", str(png)], check=True)
        out[name] = Image.open(png).convert("L")
    return out


def place(rng, sils):
    """Greedy packing on a quarter-resolution occupancy grid, biggest icons first."""
    q, pad = 4, 60
    gw, gh = (W + 2 * pad) // q, (H + 2 * pad) // q
    grid = np.zeros((gh, gw), bool)
    gap_cells = 2  # about 8-10 px between icons
    placed = []
    counts = {n: 0 for n in ICONS}
    size, size_min = 195.0, 66.0
    fails = 0
    while size >= size_min:
        name = min(ICONS, key=lambda n: (counts[n], rng.random()))
        _, _, rot = ICONS[name]
        angle = rng.uniform(-rot, rot)
        s = size * rng.uniform(0.9, 1.1) * SIZE.get(name, 1.0)
        px = max(4, int(round(s * 1.2 / q)))  # the 120-unit box
        m = sils[name].resize((px, px), Image.BILINEAR).rotate(-angle, resample=Image.BILINEAR, expand=True)
        m = m.point(lambda v: 255 if v > 40 else 0)
        m = m.filter(ImageFilter.MaxFilter(gap_cells * 2 + 1))
        a = np.asarray(m) > 0
        mh, mw = a.shape
        ok = False
        hits = fftconvolve(grid.astype(np.float32), a[::-1, ::-1].astype(np.float32), mode="valid")
        free = np.argwhere(hits < 0.5)
        if len(free):
            rng_np = np.random.default_rng(rng.randrange(1 << 30))
            for gy, gx in free[rng_np.permutation(len(free))[:200]]:
                cx = (gx + mw / 2) * q - pad
                cy = (gy + mh / 2) * q - pad
                if any(n == name and math.hypot(cx - x, cy - y) < 480 for x, y, _, _, n in placed):
                    continue
                ok = True
                break
        if ok:
            grid[gy:gy + mh, gx:gx + mw] |= a
            placed.append((cx, cy, s, angle, name))
            counts[name] += 1
            fails = 0
        else:
            fails += 1
            if fails > 10:
                size *= 0.965
                fails = 0
    return placed


def render(svg_path, out_w, out_h, out, seed):
    """Renders the layout at twice the output size, downsamples, then adds grain."""
    big = svg_path.with_name(f"render_{out_h}.png")
    subprocess.run(["magick", "-density", str(96 * 2 * out_w / W), str(svg_path), str(big)], check=True)
    img = Image.open(big).convert("RGB").resize((out_w, out_h), Image.LANCZOS)
    arr = np.asarray(img).astype(np.float32)
    grain = np.random.default_rng(seed).normal(0, 2.2, (out_h, out_w, 1))
    arr = np.clip(arr + grain, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(out, optimize=True)
    print(f"-> {out}")


def main():
    ap = argparse.ArgumentParser(description="Draws the gaming wallpapers.")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=Path, default=REPO / "wallpapers")
    args = ap.parse_args()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    defs = build_defs()
    placed = place(rng, silhouettes(defs))
    uses = []
    for x, y, s, a, name in placed:
        uses.append(f'<g transform="translate({x:.1f} {y:.1f}) rotate({a:.1f}) scale({s / 100:.3f}) translate(-50 -50)">'
                    f'<rect x="-10" y="-10" width="120" height="120" fill="#070707" mask="url(#m_{name})"/></g>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<radialGradient id="bg" cx="50%" cy="45%" r="75%">
  <stop offset="0" stop-color="#3a3a3a"/><stop offset="0.6" stop-color="#2c2c2c"/><stop offset="1" stop-color="#1a1a1a"/>
</radialGradient>
{defs}
</defs>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
{chr(10).join(uses)}
</svg>'''
    SVG.write_text(svg, encoding="utf-8")
    for out_w, out_h, label in OUTPUTS:
        render(SVG, out_w, out_h, out_dir / f"gaming-wallpaper-{label}.png", args.seed)
    print(f"{len(placed)} icons, {len(ICONS)} designs")


if __name__ == "__main__":
    main()
