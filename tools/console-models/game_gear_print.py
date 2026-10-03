"""The Game Gear's front printing, for the console theme's model (tools/console-models/game_gear.py).

Draws the front face in millimetres, as the model's planar UVs map it (x -105..105 left to right, height 0..113 bottom
to top): the body colour, the black screen panel with the GAME GEAR and SEGA marks, the speaker grille, the shadows
round the buttons, and the START and 1/2 markings. Run it with the system Python (Pillow):

    python tools/console-models/game_gear_print.py <out.png>
"""

import math
import sys

from PIL import Image, ImageDraw, ImageFont

WIDTH_MM, HEIGHT_MM = 210.0, 113.0
SCALE = 20  # pixels per millimetre while drawing; the result is resampled to OUT
OUT = (2048, 1024)
FONTS = "C:/Windows/Fonts/"

BODY = "#2F3034"
PANEL = "#0D0D10"
RECESS = "#222327"
GRILLE = "#121214"
WHITE = "#EEEEEE"
GREEN = "#1E9E74"
LEGEND = "#AEB1B5"

# The screen panel's corners (bottom right, top right, top left, bottom left) and radii; game_gear.py uses the same.
PANEL_CORNERS = [(56, 29), (65, 102.5), (-65, 102.5), (-56, 29)]


def px(x, v):
    """A point in millimetres (x from the centre, v up from the bottom) as canvas pixels."""
    return ((x + WIDTH_MM / 2) * SCALE, (HEIGHT_MM - v) * SCALE)


def circle(draw, x, v, r, fill):
    cx, cy = px(x, v)
    draw.ellipse([cx - r * SCALE, cy - r * SCALE, cx + r * SCALE, cy + r * SCALE], fill=fill)


def ellipse(canvas, x, v, rx, rv, degrees, fill):
    """An ellipse turned anticlockwise by degrees, drawn on its own layer and pasted."""
    size = int(2 * max(rx, rv) * SCALE) + 8
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(
        [size / 2 - rx * SCALE, size / 2 - rv * SCALE, size / 2 + rx * SCALE, size / 2 + rv * SCALE], fill=fill)
    layer = layer.rotate(degrees, resample=Image.BICUBIC)
    cx, cy = px(x, v)
    canvas.alpha_composite(layer, (int(cx - size / 2), int(cy - size / 2)))


def text(canvas, s, font, cap_mm, x, v, fill, anchor="left", shear=0.0, degrees=0.0, stretch=1.0):
    """Text whose capitals are cap_mm high, its left edge (or centre) at x and its middle at v."""
    probe = ImageFont.truetype(FONTS + font, 200)
    left, top, right, bottom = probe.getbbox("H")
    size = int(200 * cap_mm * SCALE / (bottom - top))
    face = ImageFont.truetype(FONTS + font, size)
    left, top, right, bottom = face.getbbox(s)
    pad = size
    layer = Image.new("RGBA", (right - left + 2 * pad, bottom - top + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((pad - left, pad - top), s, font=face, fill=fill)
    if stretch != 1.0:
        layer = layer.resize((int(layer.width * stretch), layer.height), Image.LANCZOS)
    if shear:
        # Leans the tops to the right (italic), about the layer's middle.
        layer = layer.transform(layer.size, Image.AFFINE, (1, shear, -shear * layer.height / 2, 0, 1, 0), resample=Image.BICUBIC)
    if degrees:
        layer = layer.rotate(degrees, resample=Image.BICUBIC, expand=True)
    box = layer.getbbox()
    layer = layer.crop(box)
    cx, cy = px(x, v)
    left_px = cx - layer.width / 2 if anchor == "centre" else cx
    canvas.alpha_composite(layer, (int(left_px), int(cy - layer.height / 2)))


def rounded_polygon(corners, radii, segments=12):
    """A convex polygon's outline (anticlockwise corners, in mm) with each corner rounded by its radius."""
    points = []
    n = len(corners)
    for i in range(n):
        cx, cv = corners[i]
        ax, av = corners[i - 1]
        bx, bv = corners[(i + 1) % n]
        ux, uv = ax - cx, av - cv
        wx, wv = bx - cx, bv - cv
        lu, lw = math.hypot(ux, uv), math.hypot(wx, wv)
        ux, uv, wx, wv = ux / lu, uv / lu, wx / lw, wv / lw
        half = math.acos(max(-1.0, min(1.0, ux * wx + uv * wv))) / 2
        r = radii[i]
        t = r / math.tan(half)
        bx_, bv_ = ux + wx, uv + wv
        lb = math.hypot(bx_, bv_)
        ox, ov = cx + bx_ / lb * r / math.sin(half), cv + bv_ / lb * r / math.sin(half)
        p1 = (cx + ux * t - ox, cv + uv * t - ov)
        p2 = (cx + wx * t - ox, cv + wv * t - ov)
        a1, a2 = math.atan2(p1[1], p1[0]), math.atan2(p2[1], p2[0])
        while a2 < a1:
            a2 += 2 * math.pi
        for k in range(segments + 1):
            a = a1 + (a2 - a1) * k / segments
            points.append((ox + r * math.cos(a), ov + r * math.sin(a)))
    return points


def main(out):
    canvas = Image.new("RGBA", (int(WIDTH_MM * SCALE), int(HEIGHT_MM * SCALE)), BODY)
    draw = ImageDraw.Draw(canvas)

    # The screen panel, 0.4 mm larger than its model all round so its edges never show the body colour.
    grown = [(x + math.copysign(0.4, x), v + (0.4 if v > 60 else -0.4)) for x, v in PANEL_CORNERS]
    draw.polygon([px(x, v) for x, v in rounded_polygon(grown, [18.4, 5.4, 5.4, 18.4], 24)], fill=PANEL)

    # GAME GEAR: three coloured ovals over a heavy italic name, the power light beneath it.
    for x, colour in ((-53.2, "#D8232A"), (-48.8, "#109A6E"), (-44.4, "#1F63D2")):
        ellipse(canvas, x, 98.6, 1.55, 2.4, -14, colour)
    text(canvas, "GAME", "ariblk.ttf", 4.3, -58.6, 92.0, WHITE, shear=0.22, stretch=0.92)
    text(canvas, "GEAR", "ariblk.ttf", 4.3, -56.8, 86.6, WHITE, shear=0.22, stretch=0.92)
    circle(draw, -49.4, 81.6, 1.1, "#2A2A2E")
    circle(draw, -49.7, 81.9, 0.4, "#55575C")
    text(canvas, "POWER", "arialbd.ttf", 1.15, -49.4, 78.2, "#C8C8C8", anchor="centre")

    # SEGA, and PORTABLE VIDEO GAME SYSTEM in green beneath it.
    text(canvas, "SEGA", "ariblk.ttf", 4.0, 43.6, 80.8, WHITE, stretch=1.08)
    for line, v in (("PORTABLE", 76.6), ("VIDEO GAME", 73.8), ("SYSTEM", 71.0)):
        text(canvas, line, "arial.ttf", 1.75, 43.8, v, GREEN)

    # The D-pad's well and the speaker grille, left.
    circle(draw, -79.3, 77.3, 13.6, RECESS)
    for row in range(-4, 5):
        for col in range(-6, 7):
            x = -77.3 + col * 2.35 + (1.175 if row % 2 else 0)
            v = 34.4 + row * 2.05
            if ((x + 77.3) / 12.8) ** 2 + ((v - 34.4) / 9.2) ** 2 <= 1:
                circle(draw, x, v, 0.68, GRILLE)

    # START, and the 1 and 2 buttons with their bracket, right.
    ellipse(canvas, 72.7, 76.1, 4.6, 5.9, 28, RECESS)
    text(canvas, "START", "arialbd.ttf", 2.3, 79.0, 76.4, WHITE)
    circle(draw, 68.1, 48.9, 7.8, RECESS)
    circle(draw, 85.8, 59.2, 7.8, RECESS)
    bracket = [(64.6, 55.2), (65.8, 59.6), (81.0, 68.6), (85.4, 66.6)]
    draw.line([px(x, v) for x, v in bracket], fill=LEGEND, width=int(0.45 * SCALE), joint="curve")
    text(canvas, "1", "arialbd.ttf", 2.2, 62.0, 52.4, LEGEND, degrees=28)
    text(canvas, "2", "arialbd.ttf", 2.2, 87.4, 64.2, LEGEND, degrees=28)

    canvas.convert("RGB").resize(OUT, Image.LANCZOS).save(out, optimize=True)


if __name__ == "__main__":
    main(sys.argv[1])
